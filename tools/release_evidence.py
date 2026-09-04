"""Deterministic, local-only v0.8.0 qualification evidence generators."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath

try:
    from tools.conformance_evidence import SCANNER_VERSION, secret_findings
except ModuleNotFoundError:  # direct ``python tools/release_evidence.py`` execution
    from conformance_evidence import SCANNER_VERSION, secret_findings

MAX_BUNDLE_MEMBERS = 256
MAX_BUNDLE_MEMBER_BYTES = 16 * 1024 * 1024
MAX_BUNDLE_BYTES = 128 * 1024 * 1024
PLATFORMS = {
    "windows-latest-py3.12",
    "ubuntu-latest-py3.12",
    "ubuntu-latest-py3.13",
    "macos-latest-py3.12",
}
SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
MANIFEST_NAME = "qualification-content-manifest.json"


def hash_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def hash_file(path: Path) -> str:
    return hash_bytes(path.read_bytes())


def encode(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write_json(path: Path, value: dict) -> None:
    path.write_bytes(encode(value))


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load_json_bytes(raw: bytes) -> dict:
    value = json.loads(
        raw,
        object_pairs_hook=_pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"invalid JSON constant: {value}")
        ),
    )
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def load_json(path: Path) -> dict:
    raw = path.read_bytes()
    if not raw or len(raw) > MAX_BUNDLE_MEMBER_BYTES:
        raise ValueError("JSON evidence is empty or oversized")
    return load_json_bytes(raw)


def _hash_record(value, label: str) -> None:
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("reference"), str)
        or not SHA.fullmatch(value.get("sha256", ""))
    ):
        raise ValueError(f"{label} must bind a reference and SHA-256")


def validate_content(value: dict) -> dict:
    if value.get("schema") != "conclave-v0.8.0-qualification-content/0.1.0":
        raise ValueError("qualification-content schema is invalid")
    if not COMMIT.fullmatch(value.get("release_commit", "")):
        raise ValueError("release commit must be a full Git SHA")
    _hash_record(value.get("protocol"), "protocol")
    _hash_record(value.get("release_notes"), "release notes")
    platforms = value.get("platforms")
    if (
        not isinstance(platforms, list)
        or {p.get("platform_id") for p in platforms if isinstance(p, dict)} != PLATFORMS
        or len(platforms) != len(PLATFORMS)
    ):
        raise ValueError("all four exact platform identities are required")
    for platform in platforms:
        if not all(
            isinstance(platform.get(k), str) and platform[k]
            for k in ("workflow_run_id", "job_id", "artifact_id")
        ):
            raise ValueError("platform workflow/job/artifact identities are required")
        _hash_record(platform.get("evidence_index"), "platform evidence index")
    packages = value.get("canonical_packages")
    if not isinstance(packages, dict) or set(packages) != {"wheel", "sdist"}:
        raise ValueError("canonical wheel and sdist are required")
    for label, package in packages.items():
        _hash_record(package, f"canonical {label}")
        _hash_record(
            package.get("member_scan_report"), f"canonical {label} member scan"
        )
    protection = value.get("protection")
    if not isinstance(protection, dict):
        raise ValueError("protection evidence is required")
    _hash_record(protection.get("snapshot"), "protection snapshot")
    _hash_record(protection.get("restoration"), "protection restoration")
    reports = value.get("qualification_reports")
    if not isinstance(reports, list) or not reports:
        raise ValueError("qualification report bindings are required")
    for report in reports:
        _hash_record(report, "qualification report")
    _hash_record(value.get("dependency_lock"), "dependency lock")
    members = value.get("bundle_members")
    if not isinstance(members, list) or not members:
        raise ValueError("bundle member bindings are required")
    for member in members:
        _hash_record(member, "bundle member")
    refs = [m["reference"] for m in members]
    if len(refs) != len(set(refs)):
        raise ValueError("bundle member references must be unique")
    required = {p["evidence_index"]["reference"] for p in platforms}
    required |= {
        protection["snapshot"]["reference"],
        protection["restoration"]["reference"],
        value["dependency_lock"]["reference"],
    }
    required |= {report["reference"] for report in reports}
    for package in packages.values():
        required |= {package["reference"], package["member_scan_report"]["reference"]}
    if not required.issubset(set(refs)):
        raise ValueError("all qualification evidence must be bound as bundle members")
    return value


def content_manifest(spec: dict) -> dict:
    value = dict(spec)
    value["schema"] = "conclave-v0.8.0-qualification-content/0.1.0"
    return validate_content(value)


def safe_name(name: str) -> str:
    if (
        not name
        or "\\" in name
        or "\x00" in name
        or name.startswith("/")
        or re.match(r"^[A-Za-z]:", name)
    ):
        raise ValueError(f"unsafe ZIP member name: {name!r}")
    path = PurePosixPath(name)
    if str(path) != name or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError(f"unsafe ZIP member name: {name!r}")
    return name


def create_bundle(manifest_path: Path, sources: dict[str, Path], output: Path) -> dict:
    manifest_raw = manifest_path.read_bytes()
    manifest = validate_content(load_json_bytes(manifest_raw))
    if MANIFEST_NAME in sources:
        raise ValueError("qualification-content manifest name is reserved")
    all_sources = {MANIFEST_NAME: manifest_path, **sources}
    if len(all_sources) > MAX_BUNDLE_MEMBERS:
        raise ValueError("bundle member-count limit exceeded")
    if output.resolve() in {p.resolve() for p in all_sources.values()}:
        raise ValueError("bundle cannot contain or overwrite itself")
    bound = {m["reference"]: m["sha256"] for m in manifest["bundle_members"]}
    if set(bound) != set(sources):
        raise ValueError("bundle sources do not match content-manifest bindings")
    total, exact = 0, {}
    for name, source in all_sources.items():
        safe_name(name)
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"bundle source is not a regular file: {source}")
        data = source.read_bytes()
        total += len(data)
        if len(data) > MAX_BUNDLE_MEMBER_BYTES or total > MAX_BUNDLE_BYTES:
            raise ValueError("bundle decompressed-size limit exceeded")
        if name != MANIFEST_NAME and hash_bytes(data) != bound[name]:
            raise ValueError(f"bundle source hash mismatch: {name}")
        exact[name] = data
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_STORED, allowZip64=False
    ) as archive:
        for name in sorted(all_sources):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, exact[name])
    return scan_bundle(output)


def _regular(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return mode == 0 or stat.S_IFMT(mode) == 0 or stat.S_ISREG(mode)


def scan_bundle(path: Path) -> dict:
    raw, inventory, data_by_name, findings, total = path.read_bytes(), [], {}, [], 0
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_BUNDLE_MEMBERS:
            raise ValueError("bundle member-count limit exceeded")
        seen = set()
        for info in infos:
            name = safe_name(info.filename)
            folded = name.casefold()
            if folded in seen:
                raise ValueError(f"duplicate ZIP member: {name}")
            seen.add(folded)
            if info.flag_bits & 1:
                raise ValueError(f"encrypted ZIP member: {name}")
            if info.is_dir() or not _regular(info):
                raise ValueError(f"non-regular ZIP member: {name}")
            if info.file_size > MAX_BUNDLE_MEMBER_BYTES:
                raise ValueError(f"oversized ZIP member: {name}")
            with archive.open(info) as stream:
                data = stream.read(MAX_BUNDLE_MEMBER_BYTES + 1)
            if len(data) != info.file_size or len(data) > MAX_BUNDLE_MEMBER_BYTES:
                raise ValueError(f"invalid ZIP member size: {name}")
            total += len(data)
            if total > MAX_BUNDLE_BYTES:
                raise ValueError("bundle aggregate decompressed-size limit exceeded")
            data_by_name[name] = data
            findings += secret_findings(name, data)
            inventory.append(
                {"reference": name, "sha256": hash_bytes(data), "bytes": len(data)}
            )
    if MANIFEST_NAME not in data_by_name:
        raise ValueError("qualification-content manifest is missing")
    manifest = validate_content(load_json_bytes(data_by_name[MANIFEST_NAME]))
    bound = {m["reference"]: m["sha256"] for m in manifest["bundle_members"]}
    if set(data_by_name) != {MANIFEST_NAME, *bound}:
        raise ValueError("bundle inventory does not match its content manifest")
    for name, expected in bound.items():
        if hash_bytes(data_by_name[name]) != expected:
            raise ValueError(f"bound bundle hash mismatch: {name}")
    package_hashes = {}
    for label, package in manifest["canonical_packages"].items():
        ref, expected = package["reference"], package["sha256"]
        if hash_bytes(data_by_name.get(ref, b"")) != expected:
            raise ValueError(f"canonical {label} hash mismatch")
        scan_ref, scan_hash = (
            package["member_scan_report"]["reference"],
            package["member_scan_report"]["sha256"],
        )
        if hash_bytes(data_by_name.get(scan_ref, b"")) != scan_hash:
            raise ValueError(f"canonical {label} scan-report hash mismatch")
        scan = load_json_bytes(data_by_name[scan_ref])
        if (
            scan.get("schema") != SCANNER_VERSION
            or scan.get("status") != "PASS"
            or scan.get("findings") != []
        ):
            raise ValueError(f"canonical {label} member scan did not pass")
        if {
            p.get("content_hash")
            for p in scan.get("packages", [])
            if p.get("name") == Path(ref).name
        } != {expected}:
            raise ValueError(f"canonical {label} member scan does not bind package")
        package_hashes[label] = expected
    return {
        "schema": "conclave-v0.8.0-bundle-scan/0.1.0",
        "status": "PASS" if not findings else "FAIL",
        "zip_sha256": hash_bytes(raw),
        "scanner_version": SCANNER_VERSION,
        "limits": {
            "members": MAX_BUNDLE_MEMBERS,
            "member_bytes": MAX_BUNDLE_MEMBER_BYTES,
            "aggregate_bytes": MAX_BUNDLE_BYTES,
        },
        "members": sorted(inventory, key=lambda item: item["reference"]),
        "canonical_package_hashes": package_hashes,
        "findings": sorted(set(findings)),
    }


def final_manifest(content: Path, bundle: Path, scan: Path, output: Path) -> dict:
    paths = {content.resolve(), bundle.resolve(), scan.resolve()}
    if output.resolve() in paths:
        raise ValueError("final manifest cannot reference or overwrite itself")
    content_value = validate_content(load_json(content))
    scan_value = load_json(scan)
    recomputed_scan = scan_bundle(bundle)
    embedded_content_hashes = {
        item["sha256"]
        for item in recomputed_scan["members"]
        if item["reference"] == MANIFEST_NAME
    }
    if (
        recomputed_scan["status"] != "PASS"
        or scan_value != recomputed_scan
        or scan.read_bytes() != encode(recomputed_scan)
        or embedded_content_hashes != {hash_file(content)}
    ):
        raise ValueError(
            "bundle scan or embedded content is not the exact deterministic PASS"
        )
    value = {
        "schema": "conclave-v0.8.0-r3-final-manifest/0.1.0",
        "release_commit": content_value["release_commit"],
        "qualification_content_manifest": {
            "reference": content.name,
            "sha256": hash_file(content),
        },
        "qualification_zip": {"reference": bundle.name, "sha256": hash_file(bundle)},
        "bundle_scan_report": {"reference": scan.name, "sha256": hash_file(scan)},
    }
    write_json(output, value)
    return value


def _source(value: str) -> tuple[str, Path]:
    name, separator, path = value.partition("=")
    if not separator:
        raise argparse.ArgumentTypeError("member must be NAME=PATH")
    return safe_name(name), Path(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    content = commands.add_parser("content")
    content.add_argument("--spec", type=Path, required=True)
    content.add_argument("--output", type=Path, required=True)
    bundle = commands.add_parser("bundle")
    bundle.add_argument("--manifest", type=Path, required=True)
    bundle.add_argument("--member", action="append", type=_source, default=[])
    bundle.add_argument("--output", type=Path, required=True)
    bundle.add_argument("--scan-output", type=Path, required=True)
    final = commands.add_parser("final")
    final.add_argument("--content", type=Path, required=True)
    final.add_argument("--bundle", type=Path, required=True)
    final.add_argument("--scan", type=Path, required=True)
    final.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "content":
        write_json(args.output, content_manifest(load_json(args.spec)))
        return 0
    if args.command == "bundle":
        sources = dict(args.member)
        if len(sources) != len(args.member):
            raise SystemExit("duplicate --member name")
        report = create_bundle(args.manifest, sources, args.output)
        write_json(args.scan_output, report)
        return 0 if report["status"] == "PASS" else 1
    final_manifest(args.content, args.bundle, args.scan, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
