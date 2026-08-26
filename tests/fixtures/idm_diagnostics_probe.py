"""Source-checkout-only, keyless Increment 20A diagnostics probe."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--diagnostics-probe", action="store_true")
    args = parser.parse_args()
    if not args.diagnostics_probe or os.environ.get("CONCLAVE_FIXTURE_DIAGNOSTICS") != "1":
        return 2

    root = Path(__file__).resolve().parents[2]
    pin_path = root / "policies" / "idm-reference-pin.json"
    if not pin_path.is_file() or not (root / "src" / "conclave").is_dir():
        return 3
    pin = json.loads(pin_path.read_text(encoding="utf-8"))
    report = {
        "classification": "fixture-only",
        "protocol": "conclave-fixture-diagnostics/0.1.0",
        "implementation": {
            "package": pin["package"],
            "version": pin["version"],
            "import_name": pin["import_name"],
            "commit": pin["commit"],
            "tree": pin["tree"],
            "wheel_filename": pin["wheel"]["filename"],
            "wheel_sha256": pin["wheel"]["sha256"],
            "source_archive_sha256": pin["source_archive_sha256"],
            "provisioning": pin["provisioning"],
            "classification": pin["classification"],
        },
    }
    print(json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
