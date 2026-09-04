"""Install one wheel in a fresh environment and retain deterministic CLI proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import venv
from pathlib import Path

EXPECTED_VERSION = "conclave 0.8.0\nschema  task-packet/0.1.0"
MAX_WHEELHOUSE_FILES = 128


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


def build_report(wheel_hash: str, commands: list[dict]) -> dict:
    correct_shape = [item.get("name") for item in commands] == ["help", "version"]
    clean = correct_shape and all(
        item.get("returncode") == 0 and item.get("stderr") == "" for item in commands
    )
    version_ok = correct_shape and commands[1].get("stdout") == EXPECTED_VERSION
    help_ok = correct_shape and bool(commands[0].get("stdout"))
    return {
        "schema": "conclave-installed-wheel-probe/0.8.0",
        "status": "PASS" if clean and version_ok and help_ok else "FAIL",
        "wheel_sha256": wheel_hash,
        "commands": commands,
    }


def run_commands(executable: Path) -> list[dict]:
    specs = (
        ("help", ["conclave", "--help"], [str(executable), "--help"]),
        ("version", ["conclave", "version"], [str(executable), "version"]),
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
    wheelhouse = validate_wheelhouse(args.wheelhouse)
    with tempfile.TemporaryDirectory(prefix="conclave-r1-probe-") as folder:
        root = Path(folder)
        captured_dir = root / "captured-wheel"
        captured_dir.mkdir()
        captured_wheel = captured_dir / wheel.name
        captured_wheel.write_bytes(wheel_bytes)
        venv.EnvBuilder(with_pip=True, clear=True).create(root)
        python = root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        executable = root / (
            "Scripts/conclave.exe" if os.name == "nt" else "bin/conclave"
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
        commands = (
            run_commands(executable)
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
            ]
        )
    result = build_report(wheel_hash, commands)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
