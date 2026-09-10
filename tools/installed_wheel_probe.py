"""Install one wheel in a fresh environment and retain deterministic CLI proof."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import tempfile
import venv
import zipfile
from pathlib import Path

EXPECTED_VERSION = "conclave 0.8.0\nschema  task-packet/0.1.0"
MAX_WHEELHOUSE_FILES = 128
REQUIRED_PUBLICATION_MEMBERS = (
    "conclave/github_publication.py",
    "conclave/github_publication_engine.py",
    "conclave/github_publication_reconciliation.py",
    "conclave/github_publication_records.py",
)
FORBIDDEN_PUBLICATION_MEMBER_MARKERS = (
    "/tests/",
    "/test_",
    "/fixtures/",
    "fixture_transport",
    "response_cassette",
)
FORBIDDEN_PUBLICATION_SOURCE_MARKERS = (
    b"class FixtureTransport",
    b"class FixtureSequence",
    b"class Loopback",
    b"class PublicationResponse",
    b"responses: Sequence[PublicationResponse",
)

PUBLICATION_FIXTURE_PAYLOAD_B64 = "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"

EXTERNAL_PUBLICATION_PROBE = r"""
import base64
import json
import tempfile
import zlib
from pathlib import Path

from conclave import ledger
from conclave.github_foundation import (
    GitHubTransportResponse,
    RecordReference,
    write_durable_record,
)
from conclave.github_publication_engine import (
    FixtureTranscriptEntry,
    OfflinePublicationTranscript,
    PublicationStepAdmission,
    PublicationReceipt,
    RateBudgetObservation,
    TerminalArtifactInventory,
    build_exact_publication_dispatches,
    evaluate_governed_publication,
)
from conclave.github_publication_records import (
    AuthenticatedRateBudgetObservation,
    PublicationGovernanceChain,
)
from conclave.github_publication_reconciliation import (
    BlobReadProjection,
    FixtureReadTranscript,
    RetainedPublicationSubject,
    _hash_json,
    assemble_fixture_reconciliation,
    derive_expected_identity,
    fixture_read_request_hash,
    fixture_read_target,
    persist_fixture_reconciliation,
)
from conclave.identity import seal_record
from conclave.workspace import Workspace

PAYLOAD = json.loads(zlib.decompress(base64.b64decode("__PAYLOAD__")))


class Loopback:
    fixture_and_loopback_only = True

    def __init__(self, chain, artifacts, fail_at=None):
        self.chain = chain
        self.artifacts = artifacts
        self.fail_at = fail_at
        self.remaining = 40

    def response_for(self, dispatch):
        self.remaining -= 1
        expected = dispatch.expected_projection
        key = dispatch.operation_key
        if key == "repository.get":
            raw = {
                "id": expected["repository_id"],
                "owner": {"id": expected["account_id"]},
            }
        elif key in {"git_blob.create", "git_tree.create"}:
            raw = {"sha": expected["oid"]}
        elif key == "git_commit.create":
            raw = {
                "sha": expected["oid"],
                "tree": {"sha": expected["tree_oid"]},
                "parents": [{"sha": expected["parents"][0]}],
            }
        elif key in {"ref.get", "git_ref.create"}:
            raw = {
                "ref": expected["ref"],
                "object": {"sha": expected["oid"]},
            }
        elif key in {"matching_refs.list", "pull_requests.matching.list"}:
            raw = []
        elif key in {"pull_request.create", "pull_request.get"}:
            manifest = self.chain.manifest
            raw = {
                "number": 7,
                "title": self.artifacts[
                    manifest.pull_request_title.reference
                ].decode("utf-8"),
                "body": self.artifacts[
                    manifest.pull_request_body.reference
                ].decode("utf-8"),
                "head": {
                    "ref": manifest.head_ref.removeprefix("refs/heads/"),
                    "sha": manifest.proposal_commit_oid,
                    "repo": {"id": manifest.repository_id},
                },
                "base": {
                    "ref": manifest.base_ref.removeprefix("refs/heads/"),
                    "sha": manifest.base_commit_oid,
                    "repo": {"id": manifest.repository_id},
                },
            }
        else:
            raise RuntimeError("unexpected publication operation")
        status = 201 if key.endswith(".create") else 200
        response = GitHubTransportResponse(
            status=status,
            headers=(
                ("X-RateLimit-Remaining", str(self.remaining)),
                ("X-RateLimit-Limit", "5000"),
                ("X-RateLimit-Resource", "core"),
            ),
            body=json.dumps(
                raw, sort_keys=True, separators=(",", ":")
            ).encode("utf-8"),
        )
        if dispatch.ordinal == self.fail_at:
            return GitHubTransportResponse(
                status=response.status,
                headers=response.headers,
                body=b"not-json",
            )
        return response

    def transcript(self):
        dispatches = build_exact_publication_dispatches(
            self.chain.manifest,
            self.chain.repository_profile_record,
            self.artifacts,
        )
        return OfflinePublicationTranscript(
            entries=tuple(
                FixtureTranscriptEntry(
                    planned_request_hash=dispatch.request_hash,
                    response=self.response_for(dispatch),
                )
                for dispatch in dispatches
            )
        )


def stored_inputs(root, chain, rate, artifacts):
    workspace = Workspace.create(root, principal="Arthur")
    ledger.initialise(workspace, workspace.load_config())
    store = workspace.root
    records = (
        (chain.manifest.repository_profile, chain.repository_profile_record),
        (chain.manifest.api_profile, chain.api_profile_record),
        (
            chain.manifest.repository_extension,
            chain.repository_extension_record,
        ),
        (chain.manifest.task_packet, chain.task_packet_record),
        (chain.manifest.handoff, chain.handoff_record),
        (chain.manifest.scope_review, chain.scope_review_record),
        (chain.manifest.base_observation, chain.base_identity_observation),
        (
            chain.base_tree_closure.source_observation,
            chain.recursive_tree_observation,
        ),
        (chain.manifest.base_tree_closure, chain.base_tree_closure),
        (chain.authorization.manifest, chain.manifest),
        (chain.authorization.rate_observation, rate),
        (chain.plan.authorization, chain.authorization),
        (chain.operation_intent.plan, chain.plan),
        (
            chain.publication_intent.operation_intent,
            chain.operation_intent,
        ),
        (
            chain.attempt_claim.publication_intent,
            chain.publication_intent,
        ),
        (
            chain.rate_source_observation_chain.provider_key_reference,
            chain.rate_source_observation_chain.provider_key_record,
        ),
        (
            chain.rate_source_observation_chain.observation_record.authorization,
            chain.rate_source_observation_chain.authorization_record,
        ),
        (
            chain.rate_source_observation_chain.observation_record.intent,
            chain.rate_source_observation_chain.intent_record,
        ),
        (
            chain.rate_source_observation_chain.observation_record.attempt_claim,
            chain.rate_source_observation_chain.attempt_claim_record,
        ),
        (
            chain.rate_source_observation_chain.observation_record.lease_evidence,
            chain.rate_source_observation_chain.lease_evidence_record,
        ),
        (rate.source_observation, chain.rate_source_observation_record),
        (
            chain.base_tree_closure.source_authorization,
            chain.source_authorization_record,
        ),
        (chain.base_tree_closure.source_intent, chain.source_intent_record),
        (
            chain.base_tree_closure.source_attempt_claim,
            chain.source_attempt_claim_record,
        ),
        (
            chain.base_tree_closure.source_lease_evidence,
            chain.source_lease_evidence_record,
        ),
        (
            chain.source_lease_evidence_record.credential_lease_evidence,
            chain.source_credential_lease_evidence_record,
        ),
        (chain.authorization.provider_key, chain.provider_key_record),
    )
    for reference, record in records:
        target = store.joinpath(*reference.reference.split("/"))
        write_durable_record(target, record)
    for evidence in (
        *chain.branch_rules_observation_chain,
        *chain.ruleset_observation_chain,
    ):
        for reference, record in (
            (evidence.provider_key_reference, evidence.provider_key_record),
            (evidence.observation_record.authorization, evidence.authorization_record),
            (evidence.observation_record.intent, evidence.intent_record),
            (evidence.observation_record.attempt_claim, evidence.attempt_claim_record),
            (evidence.observation_record.lease_evidence, evidence.lease_evidence_record),
            (evidence.observation_reference, evidence.observation_record),
        ):
            target = store.joinpath(*reference.reference.split("/"))
            write_durable_record(target, record)
    for reference, content in artifacts.items():
        target = root.joinpath(*reference.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return workspace


def run_one(root, chain, rate, artifacts, now, fail_at=None):
    workspace = stored_inputs(root, chain, rate, artifacts)
    transport = Loopback(chain, artifacts, fail_at=fail_at)
    transcript = transport.transcript()
    receipt = evaluate_governed_publication(
        governance=chain,
        rate_observation_record=rate,
        artifact_root=root,
        transcript=transcript,
        now=now,
        workspace=workspace,
        configured_principal="Arthur",
        lease_check_at=chain.lease_evidence.first_rate_check_at,
        first_dispatch_check_at=chain.lease_evidence.first_rate_check_at,
        monotonic_elapsed_milliseconds=0,
    )
    attempt_token = chain.attempt_claim.attempt_id.rsplit(":", 1)[-1]
    evidence = workspace.github_publication_fixture_evidence_dir / attempt_token
    reopened = PublicationReceipt.model_validate_json(
        (evidence / "receipt.json").read_bytes()
    )
    if reopened.content_hash != receipt.content_hash:
        raise RuntimeError("receipt readback mismatch")
    events = ledger.read_events(workspace)
    if (
        not events
        or events[-1]["event_type"] != "github_proposal_publication_fixture_verified"
        or events[-1]["artifact_hashes"]["receipt"] != receipt.content_hash
    ):
        raise RuntimeError("publication ledger evidence missing")
    return receipt, transport, evidence


chain = PublicationGovernanceChain.model_validate_json(
    json.dumps(PAYLOAD["chain"], separators=(",", ":"))
)
rate = AuthenticatedRateBudgetObservation.model_validate_json(
    json.dumps(PAYLOAD["rate"], separators=(",", ":"))
)
artifacts = {
    reference: base64.b64decode(content)
    for reference, content in PAYLOAD["artifacts"].items()
}
with tempfile.TemporaryDirectory(prefix="conclave-installed-publication-") as folder:
    root = Path(folder).resolve(strict=True)
    success, transport, evidence = run_one(
        root / "success", chain, rate, artifacts, PAYLOAD["now"]
    )
    if (
        not success.fixture_conformance_complete
        or not success.fixture_conformance_passed
        or success.fixture_pull_request_number != 7
        or success.live_publication_claimed
        or len(success.step_states) != 16
        or len(tuple(evidence.glob("admission-*.json"))) != 16
        or len(tuple(evidence.glob("result-*.json"))) != 16
    ):
        raise RuntimeError("complete publication transaction was not retained")

    ambiguous_root = root / "ambiguous"
    ambiguous, failed, failed_evidence = run_one(
        ambiguous_root, chain, rate, artifacts, PAYLOAD["now"], fail_at=2
    )
    if (
        ambiguous.fixture_conformance_complete
        or "MUTATION_OUTCOME_AMBIGUOUS" not in ambiguous.reason_codes
        or not (failed_evidence / "receipt.json").is_file()
    ):
        raise RuntimeError("ambiguous terminal publication was not retained")

    ambiguous_state = ambiguous.step_states[-1]
    admission = PublicationStepAdmission.model_validate_json(
        (failed_evidence / ambiguous_state.admission.reference).read_bytes()
    )
    receipt_reference = RecordReference(
        reference="receipt.json", content_hash=ambiguous.content_hash
    )
    terminal_inventory = seal_record(
        TerminalArtifactInventory,
        {
            "original_claim": chain.lease_evidence.attempt_claim,
            "last_step_record": ambiguous_state.admission,
            "receipt_present": True,
            "failure_capsule_present": False,
            "receipt": receipt_reference,
            "step_state_inventory_hash": _hash_json(
                [state.model_dump(mode="json") for state in ambiguous.step_states]
            ),
            "created_at": PAYLOAD["now"],
        },
    )
    terminal_reference = RecordReference(
        reference="terminal-inventory.json",
        content_hash=terminal_inventory.content_hash,
    )
    write_durable_record(
        failed_evidence / terminal_reference.reference,
        terminal_inventory,
    )
    retained = RetainedPublicationSubject(
        manifest=chain.manifest,
        manifest_reference=chain.authorization.manifest,
        plan=chain.plan,
        plan_reference=chain.operation_intent.plan,
        original_claim=chain.attempt_claim,
        original_claim_reference=admission.attempt_claim,
        original_lease=chain.lease_evidence,
        original_lease_reference=admission.lease_evidence,
        ambiguous_admission=admission,
        ambiguous_admission_reference=ambiguous_state.admission,
        original_step_states=ambiguous.step_states,
        base_tree_closure=chain.manifest.base_tree_closure,
        base_tree_source_observation=chain.base_tree_closure.source_observation,
        rate_observation=chain.authorization.rate_observation,
        terminal_inventory=terminal_reference,
        repository_profile=chain.manifest.repository_profile,
        api_profile=chain.manifest.api_profile,
        provider_key=chain.authorization.provider_key,
        provider_public_key_sha256=chain.authorization.provider_public_key_sha256,
    )
    first_file = chain.manifest.files[0]
    expected_identity = derive_expected_identity(
        manifest=retained.manifest,
        plan=retained.plan,
        admission=retained.ambiguous_admission,
        base_tree_closure=chain.base_tree_closure,
    )
    reconciliation_target = fixture_read_target(
        manifest=retained.manifest,
        read_operation_key="git_blob.get",
        expected=expected_identity,
    )
    reconciliation = assemble_fixture_reconciliation(
        retained=retained,
        record_store_directory=failed_evidence.parents[2],
        original_evidence_directory=failed_evidence,
        reconciliation_id="installed-wheel-reconciliation-1",
        authorized_principal="Arthur",
        issued_at=PAYLOAD["now"],
        expires_at="2026-09-10T00:10:00Z",
        created_at=PAYLOAD["now"],
        purpose="Classify the retained ambiguous blob publication.",
        foundation_evidence=chain.rate_source_observation_chain,
        read_evidence=FixtureReadTranscript(
            request_target=reconciliation_target,
            request_hash=fixture_read_request_hash(
                method="GET",
                target=reconciliation_target,
                expected_identity_digest=retained.ambiguous_admission.expected_identity,
            ),
            accepted_status=200,
            projection=BlobReadProjection(
                present=True,
                oid=first_file.blob_oid,
                content_sha256=first_file.content_sha256,
                byte_count=first_file.byte_count,
            ),
        ),
    )
    reconciliation_paths = persist_fixture_reconciliation(
        Workspace(ambiguous_root / ".conclave"), reconciliation
    )
    if (
        reconciliation.receipt.classification != "FIXTURE_MATCHED_PRESENT"
        or reconciliation.receipt.profile
        != "github-publication-fixture-reconciliation-receipt"
        or reconciliation.receipt.schema_version
        != "github-publication-fixture-reconciliation-receipt/0.3.0"
        or reconciliation.receipt.source_trust != "untrusted_fixture_transcript"
        or reconciliation.receipt.continuation_authorized
        or len(reconciliation_paths) != 8
    ):
        raise RuntimeError("installed reconciliation chain was not retained")

print("github-publication-probe-ok")
"""


def normalize(value: str) -> str:
    return "\n".join(
        line.rstrip()
        for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ).strip()


def command_record(
    name: str, argv: list[str], completed: subprocess.CompletedProcess[str]
) -> dict:
    return {
        "name": name,
        "command": argv,
        "returncode": completed.returncode,
        "stdout": normalize(completed.stdout),
        "stderr": normalize(completed.stderr),
    }


def inspect_wheel_inventory(wheel_bytes: bytes) -> dict:
    """Prove the installed artifact has runtime code but no test support."""

    try:
        with zipfile.ZipFile(io.BytesIO(wheel_bytes)) as archive:
            members = tuple(sorted(info.filename for info in archive.infolist()))
            source_bytes = {
                name: archive.read(name)
                for name in members
                if name.endswith(REQUIRED_PUBLICATION_MEMBERS)
            }
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError("wheel inventory is unreadable") from exc
    if len(members) != len(set(members)):
        raise ValueError("wheel inventory contains duplicate members")
    required = {
        suffix: tuple(name for name in members if name.endswith(suffix))
        for suffix in REQUIRED_PUBLICATION_MEMBERS
    }
    if any(len(matches) != 1 for matches in required.values()):
        raise ValueError("wheel inventory lacks the exact publication runtime")
    prohibited = tuple(
        name
        for name in members
        if any(
            marker in f"/{name.lower()}"
            for marker in FORBIDDEN_PUBLICATION_MEMBER_MARKERS
        )
    )
    if prohibited:
        raise ValueError("wheel inventory contains publication test support")
    if any(
        marker in source
        for source in source_bytes.values()
        for marker in FORBIDDEN_PUBLICATION_SOURCE_MARKERS
    ):
        raise ValueError("wheel publication runtime contains a fixture constructor")
    return {
        "member_count": len(members),
        "required_publication_members": {
            suffix: {
                "member": matches[0],
                "sha256": "sha256:"
                + hashlib.sha256(source_bytes[matches[0]]).hexdigest(),
            }
            for suffix, matches in required.items()
        },
        "prohibited_members": [],
    }


def build_report(
    wheel_hash: str, commands: list[dict], package_inventory: dict
) -> dict:
    correct_shape = [item.get("name") for item in commands] == [
        "help",
        "version",
        "github_publication_probe",
    ]
    clean = correct_shape and all(
        item.get("returncode") == 0 and item.get("stderr") == "" for item in commands
    )
    version_ok = correct_shape and commands[1].get("stdout") == EXPECTED_VERSION
    help_ok = correct_shape and bool(commands[0].get("stdout"))
    adapter_ok = (
        correct_shape and commands[2].get("stdout") == "github-publication-probe-ok"
    )
    inventory = package_inventory.get("required_publication_members", {})
    inventory_ok = (
        package_inventory.get("member_count", 0) > 0
        and set(inventory) == set(REQUIRED_PUBLICATION_MEMBERS)
        and package_inventory.get("prohibited_members") == []
        and all(
            isinstance(inventory[suffix], dict)
            and inventory[suffix].get("member", "").endswith(suffix)
            and isinstance(inventory[suffix].get("sha256"), str)
            and len(inventory[suffix]["sha256"]) == 71
            and inventory[suffix]["sha256"].startswith("sha256:")
            and all(
                character in "0123456789abcdef"
                for character in inventory[suffix]["sha256"][7:]
            )
            for suffix in REQUIRED_PUBLICATION_MEMBERS
        )
    )
    return {
        "schema": "conclave-installed-wheel-probe/0.8.0",
        "status": (
            "PASS"
            if clean and version_ok and help_ok and adapter_ok and inventory_ok
            else "FAIL"
        ),
        "wheel_sha256": wheel_hash,
        "package_inventory": package_inventory,
        "commands": commands,
    }


def prepare_publication_probe(root: Path) -> Path:
    """Stage test support beside, never inside, the installed wheel."""

    path = root / "external-publication-fixture.py"
    source = EXTERNAL_PUBLICATION_PROBE.replace(
        "__PAYLOAD__", PUBLICATION_FIXTURE_PAYLOAD_B64
    )
    path.write_text(source, encoding="utf-8", newline="\n")
    return path


def run_commands(executable: Path, publication_probe: Path) -> list[dict]:
    specs = (
        ("help", ["conclave", "--help"], [str(executable), "--help"]),
        ("version", ["conclave", "version"], [str(executable), "version"]),
        (
            "github_publication_probe",
            [
                "python",
                "-I",
                "external-publication-fixture.py",
            ],
            [
                str(executable.parent / "python.exe")
                if os.name == "nt"
                else str(executable.parent / "python"),
                "-I",
                str(publication_probe),
            ],
        ),
    )
    records = []
    for name, logical, actual in specs:
        completed = subprocess.run(actual, check=False, capture_output=True, text=True)
        records.append(command_record(name, logical, completed))
    return records


def validate_wheelhouse(path: Path) -> Path:
    if path.is_symlink():
        raise ValueError("wheelhouse must not be a symlink")
    resolved = path.resolve()
    if not resolved.is_dir():
        raise ValueError("wheelhouse must be an existing regular directory")
    entries = list(resolved.iterdir())
    if not entries or len(entries) > MAX_WHEELHOUSE_FILES:
        raise ValueError("wheelhouse is empty or exceeds the file-count limit")
    if any(entry.is_symlink() or not entry.is_file() for entry in entries):
        raise ValueError("wheelhouse may contain regular files only")
    if any(
        not (entry.name.endswith(".whl") or entry.name.endswith(".tar.gz"))
        for entry in entries
    ):
        raise ValueError("wheelhouse contains a non-package file")
    return resolved


def prepare_probe_environment(
    root: Path, wheel_name: str, wheel_bytes: bytes
) -> tuple[Path, Path, Path, Path]:
    """Create the clean environment before staging the immutable wheel copy."""
    # Windows runners can expose TEMP through an 8.3 alias (for example
    # RUNNER~1) while the virtual environment resolves to the long path.  Pin
    # the existing directory to its canonical spelling before venv creation so
    # every subsequent executable and fixture path names the same location.
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve(strict=True)
    venv.EnvBuilder(with_pip=True, clear=True).create(root)
    captured_dir = root / "captured-wheel"
    captured_dir.mkdir()
    captured_wheel = captured_dir / wheel_name
    captured_wheel.write_bytes(wheel_bytes)
    python = root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    executable = root / ("Scripts/conclave.exe" if os.name == "nt" else "bin/conclave")
    return root, captured_wheel, python, executable


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheelhouse", type=Path, required=True)
    args = parser.parse_args()
    if args.wheel.is_symlink():
        raise SystemExit("wheel must be a regular file, not a symlink")
    wheel = args.wheel.resolve()
    if not wheel.is_file() or wheel.suffix != ".whl":
        raise SystemExit("wheel must be one existing .whl file")
    wheel_bytes = wheel.read_bytes()
    wheel_hash = "sha256:" + hashlib.sha256(wheel_bytes).hexdigest()
    package_inventory = inspect_wheel_inventory(wheel_bytes)
    wheelhouse = validate_wheelhouse(args.wheelhouse)
    with tempfile.TemporaryDirectory(prefix="conclave-r1-probe-") as folder:
        root = Path(folder)
        root, captured_wheel, python, executable = prepare_probe_environment(
            root, wheel.name, wheel_bytes
        )
        install = [
            str(python),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--find-links",
            str(wheelhouse),
        ]
        install.append(str(captured_wheel))
        completed = subprocess.run(
            install, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        publication_probe = prepare_publication_probe(root)
        commands = (
            run_commands(executable, publication_probe)
            if completed.returncode == 0
            else [
                {
                    "name": "help",
                    "command": ["conclave", "--help"],
                    "returncode": completed.returncode,
                    "stdout": "",
                    "stderr": "wheel installation failed",
                },
                {
                    "name": "version",
                    "command": ["conclave", "version"],
                    "returncode": completed.returncode,
                    "stdout": "",
                    "stderr": "wheel installation failed",
                },
                {
                    "name": "github_publication_probe",
                    "command": [
                        "python",
                        "-I",
                        "external-publication-fixture.py",
                    ],
                    "returncode": completed.returncode,
                    "stdout": "",
                    "stderr": "wheel installation failed",
                },
            ]
        )
    result = build_report(wheel_hash, commands, package_inventory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
