"""Fixture-only external IDM broker for Increment 19D conformance tests.

This file is outside the CONCLAVE package, is never installed as a command,
and refuses to run without two explicit fixture markers.  No key is logged or
returned; only the public COSE envelope and a hash-only receipt are written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from conclave.evidence import (
    EVIDENCE_CONTEXT,
    EvidenceSigningRequest,
    SignedEvidencePayload,
    resolve_stored_artifact,
)
from conclave.workspace import Workspace
from idm.attestation import encode_attestation


def _sha256(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-only", action="store_true")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--kid", required=True)
    parser.add_argument("--issued-at", required=True)
    parser.add_argument("--expires-at", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if not args.fixture_only or os.environ.get("CONCLAVE_FIXTURE_BROKER") != "1":
        raise SystemExit("fixture broker requires explicit fixture-only environment")
    if not args.key.name.endswith(".fixture-only.key"):
        raise SystemExit("fixture broker refuses a key without the fixture-only suffix")
    key = args.key.read_bytes()
    if len(key) != 32:
        raise SystemExit("fixture key must be one raw Ed25519 private key")
    request = EvidenceSigningRequest.model_validate_json(args.request.read_bytes())
    workspace = Workspace(args.workspace.resolve())
    artifact = resolve_stored_artifact(
        workspace,
        storage_reference=request.artifact_storage_reference,
        artifact_schema=request.artifact_schema,
    )
    if (
        artifact.reference != request.artifact_reference
        or artifact.content_hash != request.artifact_content_hash
        or artifact.payload_hash != request.canonical_payload_hash
        or list(artifact.provenance_chain) != request.provenance_chain
    ):
        raise SystemExit("fixture broker independently rejected artifact/request binding")
    request_reference = args.request.resolve().relative_to(workspace.root).as_posix()
    payload = SignedEvidencePayload(
        profile="conclave-signed-evidence/0.1.0",
        artifact_reference=request.artifact_reference,
        artifact_schema=request.artifact_schema,
        artifact_content_hash=request.artifact_content_hash,
        canonical_payload_hash=request.canonical_payload_hash,
        signing_request_reference=request_reference,
        signing_request_hash=request.content_hash,
        workspace_id=request.replay_domain.workspace_id,
        bounded_domain=request.replay_domain.bounded_domain,
        attester_eid=request.attester_eid,
        attester_mid=request.attester_mid,
        attester_role=request.attester_role,
        attester_kid=request.attester_kid,
        asserted_scope=request.required_scope,
        issued_at=args.issued_at,
        expires_at=args.expires_at,
        authority_effect="none",
        decision_effect="none",
        membership_effect="none",
    )
    envelope = encode_attestation(
        payload.model_dump(mode="python"),
        context=EVIDENCE_CONTEXT,
        private_key=key,
        kid=args.kid,
    )
    args.output.write_bytes(envelope)
    receipt = {
        "profile": "conclave-fixture-broker-receipt/1.0",
        "classification": "fixture-only-non-production",
        "request_hash": request.content_hash,
        "artifact_hash": request.artifact_content_hash,
        "envelope_hash": _sha256(envelope),
        "kid": args.kid,
        "secret_material_returned": False,
    }
    args.receipt.write_text(
        json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
