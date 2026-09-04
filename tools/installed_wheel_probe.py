"""Install one built wheel in a fresh venv and record dormant CLI proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    wheel = args.wheel.resolve()
    with tempfile.TemporaryDirectory(prefix="conclave-20d-probe-") as folder:
        root = Path(folder)
        venv.EnvBuilder(with_pip=True, clear=True).create(root)
        python = root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run([str(python), "-m", "pip", "install", str(wheel)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        code = (
            "import json,subprocess,sys;"
            "p=subprocess.run([sys.executable,'-m','conclave.cli','--help'],capture_output=True,text=True);"
            "print(json.dumps({'returncode':p.returncode,'help_has_conclave':'CONCLAVE' in p.stdout.upper(),"
            "'stderr_empty':not bool(p.stderr.strip())},sort_keys=True))"
        )
        probe = subprocess.run([str(python), "-c", code], check=True, capture_output=True, text=True)
    result = json.loads(probe.stdout)
    result.update({"schema": "conclave-20d-installed-wheel-probe/0.1.0",
                   "wheel_sha256": "sha256:" + hashlib.sha256(wheel.read_bytes()).hexdigest(),
                   "status": "PASS" if result == {"returncode": 0, "help_has_conclave": True,
                                                    "stderr_empty": True} else "FAIL"})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n",
                           encoding="utf-8")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
