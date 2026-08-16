"""Increment 19B evidence-request/import security and compatibility tests."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError

from conclave import ledger
from conclave.errors import ValidationError
from conclave.evidence import (
    EVIDENCE_CONTEXT,
    EVIDENCE_SCOPE,
    EvidenceSigningRequest,
    EvidenceVerificationFindings,
    ExpiryPolicy,
    IDMEvidenceVerifierReport,
    SIGNED_PAYLOAD_PROFILE,
    SIGNING_REQUEST_SCHEMA,
    SignedEvidenceBinding,
    SignedEvidencePayload,
    derive_evidence_id,
    evidence_reliance_state,
    import_evidence_envelope,
    prepare_signing_request,
    resolve_stored_artifact,
    verified_workspace_id,
)
from conclave.identity import (
    FROZEN_IDM_IMPLEMENTATION,
    IDMImplementationPin,
    TrustInputSet,
    seal_record,
    sha256_bytes,
    write_immutable_record,
)
from conclave.taskpacket import build_packet, write_packet
from conclave.reconcile import reconcile
from conclave.workspace import Workspace

EID = "eid:" + "a" * 26
MID = "mid:" + "b" * 26
KID = "kid:sha256:" + "A" * 43
TDID = "tdid:" + "c" * 26
TRUST = b"public trust"
REVOCATION = b"signed current revocation state"
TIME = b"trusted time evidence"


def _public_ref(name, value):
    return {"reference": name, "content_hash": sha256_bytes(value)}


def _trust(ws, **changes):
    data = {
        "profile": "idm-trust-input-set",
        "schema_version": "idm-trust-input-set/0.1.0",
        "idm_implementation": FROZEN_IDM_IMPLEMENTATION,
        "trust_bundle": _public_ref("public/trust", TRUST),
        "trust_domain_id": TDID,
        "revocation_evidence": [_public_ref("public/revocation", REVOCATION)],
        "evaluation_time": "2026-08-16T12:00:00Z",
        "time_source_classification": "trusted",
        "time_evidence": _public_ref("public/time", TIME),
        "accepted_roles": ["audit_attester"],
        "required_scopes": ["audit.sign"],
        "created_by": "Arthur",
        "created_at": "2026-08-16T11:00:00Z",
    }
    data.update(changes)
    record = seal_record(TrustInputSet, data)
    path = ws.identity_trust_inputs_dir / (record.content_hash.split(":", 1)[1] + ".json")
    write_immutable_record(path, record)
    return record, path


@pytest.fixture
def prepared(tmp_path):
    ws = Workspace.create(tmp_path, principal="Arthur")
    packet = build_packet(
        objective="19B public evidence fixture",
        created_by="Arthur",
        target_objects=[{"object_id": "FIXTURE"}],
        assigned_providers=[{"provider": "claude", "role": "critic"}],
    )
    packet_path = write_packet(ws, packet)
    ledger.initialise(ws, ws.load_config())
    request, request_path, _ = prepare_signing_request(
        ws,
        storage_reference=packet_path.relative_to(ws.root).as_posix(),
        artifact_schema="task-packet/0.1.0",
        attester_eid=EID,
        attester_mid=MID,
        attester_role="audit_attester",
        attester_kid=KID,
        purpose="attest exact fixture bytes",
        expiry_policy=ExpiryPolicy(
            expires_at_required=True, maximum_validity_seconds=3600
        ),
        requester_actor_id="Arthur",
        requester_authority_level="human_principal",
    )
    trust, trust_path = _trust(ws)
    return ws, packet, packet_path, request, request_path, trust, trust_path


def _payload(ws, request, request_path, **changes):
    data = {
        "profile": SIGNED_PAYLOAD_PROFILE,
        "artifact_reference": request.artifact_reference,
        "artifact_schema": request.artifact_schema,
        "artifact_content_hash": request.artifact_content_hash,
        "canonical_payload_hash": request.canonical_payload_hash,
        "signing_request_reference": request_path.relative_to(ws.root).as_posix(),
        "signing_request_hash": request.content_hash,
        "workspace_id": request.replay_domain.workspace_id,
        "bounded_domain": request.replay_domain.bounded_domain,
        "attester_eid": request.attester_eid,
        "attester_mid": request.attester_mid,
        "attester_role": request.attester_role,
        "attester_kid": request.attester_kid,
        "asserted_scope": EVIDENCE_SCOPE,
        "issued_at": "2026-08-16T11:30:00Z",
        "expires_at": "2026-08-16T12:30:00Z",
        "authority_effect": "none",
        "decision_effect": "none",
        "membership_effect": "none",
    }
    data.update(changes)
    return SignedEvidencePayload.model_validate(data)


def _findings(**changes):
    data = {name: True for name in EvidenceVerificationFindings.model_fields}
    data.update(changes)
    return EvidenceVerificationFindings(**data)


class FixtureEvidenceVerifier:
    """Inert public report adapter: no key, sign, issue or allocation method."""

    def __init__(self, payload, **changes):
        self.payload = payload
        self.changes = changes
        self.calls = 0

    def verify_evidence(self, *, envelope, **_inputs):
        self.calls += 1
        data = {
            "implementation": FROZEN_IDM_IMPLEMENTATION,
            "evidence_id": derive_evidence_id(envelope),
            "context": EVIDENCE_CONTEXT,
            "trust_domain_id": TDID,
            "signer_kid": KID,
            "verified_roles": ["audit_attester"],
            "verified_scopes": ["audit.sign"],
            "payload": self.payload,
            "findings": _findings(),
            "reason_codes": [],
        }
        data.update(self.changes)
        return IDMEvidenceVerifierReport.model_validate(data)


def _import(prepared, *, envelope=b"inert public COSE fixture", verifier=None,
            evidence=None, trust_path=None):
    ws, _packet, _packet_path, request, request_path, _trust_record, default_trust = prepared
    verifier = verifier or FixtureEvidenceVerifier(_payload(ws, request, request_path))
    return import_evidence_envelope(
        ws,
        request_path=request_path,
        trust_input_path=trust_path or default_trust,
        envelope=envelope,
        public_evidence=evidence or {
            "public/trust": TRUST,
            "public/revocation": REVOCATION,
            "public/time": TIME,
        },
        verifier=verifier,
    )


def test_prepare_request_binds_verified_genesis_artifact_and_authority(prepared):
    ws, packet, packet_path, request, request_path, _trust_record, _trust_path = prepared
    assert request.schema_version == SIGNING_REQUEST_SCHEMA
    assert request.artifact_reference == packet.ref
    assert request.artifact_storage_reference == packet_path.relative_to(ws.root).as_posix()
    assert request.requested_context == EVIDENCE_CONTEXT
    assert request.required_scope == EVIDENCE_SCOPE
    assert request.replay_domain.workspace_id == verified_workspace_id(ws)
    assert request.replay_domain.bounded_domain == packet.ref
    assert request.authority_effect == request.decision_effect == request.membership_effect == "none"
    assert request.action_execution_allowed is False
    assert request_path.name == request.content_hash.split(":", 1)[1] + ".json"


def test_prepare_request_is_idempotent(prepared):
    ws, _packet, packet_path, first, _path, *_rest = prepared
    second, second_path, created = prepare_signing_request(
        ws, storage_reference=packet_path.relative_to(ws.root).as_posix(),
        artifact_schema="task-packet/0.1.0", attester_eid=EID, attester_mid=MID,
        attester_role="audit_attester", attester_kid=KID,
        purpose="attest exact fixture bytes",
        expiry_policy=ExpiryPolicy(expires_at_required=True, maximum_validity_seconds=3600),
        requester_actor_id="Arthur", requester_authority_level="human_principal",
    )
    assert not created and second == first and second_path.exists()


def test_request_requires_valid_ledger(tmp_path):
    ws = Workspace.create(tmp_path, principal="Arthur")
    with pytest.raises(ValidationError, match="valid workspace ledger"):
        verified_workspace_id(ws)


def test_wrong_human_requester_is_refused(prepared):
    ws, _packet, packet_path, *_rest = prepared
    with pytest.raises(ValidationError, match="configured human principal"):
        prepare_signing_request(
            ws, storage_reference=packet_path.relative_to(ws.root).as_posix(),
            artifact_schema="task-packet/0.1.0", attester_eid=EID, attester_mid=MID,
            attester_role="audit_attester", attester_kid=KID, purpose="x",
            expiry_policy=ExpiryPolicy(expires_at_required=False),
            requester_actor_id="provider", requester_authority_level="human_principal",
        )


def test_unknown_advisory_requester_is_refused(prepared):
    ws, _packet, packet_path, *_rest = prepared
    with pytest.raises(ValidationError, match="configured as advisory"):
        prepare_signing_request(
            ws, storage_reference=packet_path.relative_to(ws.root).as_posix(),
            artifact_schema="task-packet/0.1.0", attester_eid=EID, attester_mid=MID,
            attester_role="audit_attester", attester_kid=KID, purpose="x",
            expiry_policy=ExpiryPolicy(expires_at_required=False),
            requester_actor_id="unknown", requester_authority_level="advisory_agent",
        )


@pytest.mark.parametrize(
    "reference",
    ["../x", "/tmp/x", "C:/x", "tasks\\x", "a:b", "Tasks/x", "tasks/CON"],
)
def test_artifact_path_attacks_are_refused(prepared, reference):
    ws = prepared[0]
    with pytest.raises(ValidationError):
        resolve_stored_artifact(ws, storage_reference=reference,
                                artifact_schema="task-packet/0.1.0")


def test_unknown_artifact_schema_is_refused(prepared):
    with pytest.raises(ValidationError, match="not recognized"):
        resolve_stored_artifact(prepared[0], storage_reference="tasks/x/v1.yaml",
                                artifact_schema="natural-language/1")


def test_artifact_symlink_or_reparse_escape_is_refused(prepared, tmp_path):
    ws = prepared[0]
    outside = tmp_path / "outside.yaml"
    outside.write_text("not governed", encoding="utf-8")
    link = ws.tasks_dir / "escape.yaml"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable to this Windows test account")
    with pytest.raises(ValidationError, match="escapes|symlink|reparse"):
        resolve_stored_artifact(ws, storage_reference="tasks/escape.yaml",
                                artifact_schema="task-packet/0.1.0")


def test_tampered_artifact_is_refused_at_import(prepared):
    prepared[2].write_text("tampered", encoding="utf-8")
    with pytest.raises(ValidationError, match="native closed schema"):
        _import(prepared)


def test_valid_envelope_is_preserved_and_authority_neutral(prepared):
    outcome = _import(prepared)
    assert outcome.binding.verification_status == "PASS"
    assert outcome.envelope_path.read_bytes() == b"inert public COSE fixture"
    assert outcome.binding.authority_effect == "none"
    assert outcome.binding.decision_effect == "none"
    assert outcome.binding.membership_effect == "none"
    assert outcome.binding.action_execution_allowed is False
    assert ":" not in outcome.envelope_path.name and ":" not in outcome.binding_path.name
    assert evidence_reliance_state(prepared[0], prepared[3].content_hash) == "VERIFIED_NOT_GATED"


def test_identical_import_is_idempotent(prepared):
    first = _import(prepared)
    second = _import(prepared)
    assert not second.envelope_created and not second.binding_created
    assert first.binding == second.binding


def test_concurrent_identical_import_is_idempotent(prepared):
    def run(_index):
        return _import(prepared)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(run, range(2)))
    assert sum(item.envelope_created for item in outcomes) == 1
    assert sum(item.binding_created for item in outcomes) == 1
    assert outcomes[0].binding == outcomes[1].binding


@pytest.mark.parametrize(
    "envelope", [b"", b"x" * (1024 * 1024 + 1)], ids=["empty", "oversize"]
)
def test_envelope_size_is_bounded(prepared, envelope):
    with pytest.raises(ValidationError, match="size"):
        _import(prepared, envelope=envelope)


def test_missing_revocation_fails_without_calling_verifier(prepared):
    ws, _p, _pp, request, request_path, *_ = prepared
    verifier = FixtureEvidenceVerifier(_payload(ws, request, request_path))
    outcome = _import(prepared, verifier=verifier,
                      evidence={"public/trust": TRUST, "public/time": TIME})
    assert outcome.binding.verification_status == "FAIL"
    assert "REVOCATION_EVIDENCE_MISSING" in outcome.binding.reason_codes
    assert verifier.calls == 0


@pytest.mark.parametrize(
    "roles,scopes,code",
    [
        (["other"], ["audit.sign"], "ROLE_POLICY_MISMATCH"),
        (["audit_attester"], ["identity.issue"], "SCOPE_POLICY_MISMATCH"),
    ],
)
def test_trust_policy_must_authorize_requested_role_and_scope(prepared, roles, scopes, code):
    ws = prepared[0]
    _record, path = _trust(ws, accepted_roles=roles, required_scopes=scopes)
    outcome = _import(prepared, trust_path=path)
    assert code in outcome.binding.reason_codes


def test_verifier_exception_is_sanitized_and_opaque_bytes_do_not_conflict(prepared):
    class Explodes:
        def verify_evidence(self, **_inputs):
            raise RuntimeError("E:/offline-root/private.key secret")

    first = _import(prepared, envelope=b"opaque-1", verifier=Explodes())
    second = _import(prepared, envelope=b"opaque-2", verifier=Explodes())
    assert first.binding.reason_codes == ["IDM_EVIDENCE_VERIFIER_ERROR"]
    assert "private.key" not in json.dumps(first.binding.model_dump(mode="json"))
    assert not second.conflict
    assert evidence_reliance_state(prepared[0], prepared[3].content_hash) == "NOT_RELIABLE"


@pytest.mark.parametrize("finding", EvidenceVerificationFindings.model_fields)
def test_each_verification_finding_fails_closed(prepared, finding):
    ws, _p, _pp, request, request_path, *_ = prepared
    verifier = FixtureEvidenceVerifier(
        _payload(ws, request, request_path), findings=_findings(**{finding: False})
    )
    assert _import(prepared, verifier=verifier).binding.verification_status == "FAIL"


@pytest.mark.parametrize(
    "code",
    ["ENTITY_REVOKED", "LINEAGE_REVOKED", "REVISION_REVOKED", "KEY_REVOKED",
     "DELEGATION_REVOKED", "REVOCATION_STALE"],
)
def test_each_revocation_class_and_staleness_fails_closed(prepared, code):
    ws, _p, _pp, request, request_path, *_ = prepared
    verifier = FixtureEvidenceVerifier(
        _payload(ws, request, request_path),
        findings=_findings(revocation=False),
        reason_codes=[code],
    )
    outcome = _import(prepared, verifier=verifier)
    assert code in outcome.binding.reason_codes
    assert outcome.binding.verification_status == "FAIL"


@pytest.mark.parametrize(
    "field,value",
    [
        ("artifact_reference", "other"),
        ("artifact_content_hash", "sha256:" + "0" * 64),
        ("canonical_payload_hash", "sha256:" + "0" * 64),
        ("signing_request_hash", "sha256:" + "0" * 64),
        ("workspace_id", "workspace:sha256:" + "0" * 64),
        ("bounded_domain", "other-task"),
        ("attester_eid", "eid:" + "d" * 26),
        ("attester_mid", "mid:" + "e" * 26),
        ("attester_kid", "kid:sha256:" + "B" * 43),
    ],
)
def test_payload_substitution_fails_cross_binding(prepared, field, value):
    ws, _p, _pp, request, request_path, *_ = prepared
    verifier = FixtureEvidenceVerifier(_payload(ws, request, request_path, **{field: value}))
    outcome = _import(prepared, verifier=verifier)
    assert "REQUEST_CROSS_BINDING_MISMATCH" in outcome.binding.reason_codes
    assert not outcome.binding.request_binding_verified


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"context": "wrong"}, "CONTEXT_MISMATCH"),
        ({"trust_domain_id": "tdid:" + "d" * 26}, "TRUST_DOMAIN_MISMATCH"),
        ({"signer_kid": "kid:sha256:" + "B" * 43}, "KID_MISMATCH"),
        ({"verified_roles": ["other"]}, "ROLE_MISSING"),
        ({"verified_scopes": ["identity.issue"]}, "SCOPE_MISSING"),
    ],
)
def test_verifier_authorization_substitution_fails(prepared, changes, code):
    ws, _p, _pp, request, request_path, *_ = prepared
    outcome = _import(prepared, verifier=FixtureEvidenceVerifier(
        _payload(ws, request, request_path), **changes))
    assert code in outcome.binding.reason_codes


def test_unpinned_verifier_fails(prepared):
    ws, _p, _pp, request, request_path, *_ = prepared
    wrong = IDMImplementationPin(
        commit="0" * 40, tree=FROZEN_IDM_IMPLEMENTATION.tree,
        wheel_sha256=FROZEN_IDM_IMPLEMENTATION.wheel_sha256,
        source_archive_sha256=FROZEN_IDM_IMPLEMENTATION.source_archive_sha256,
    )
    result = _import(prepared, verifier=FixtureEvidenceVerifier(
        _payload(ws, request, request_path), implementation=wrong))
    assert "IDM_VERIFIER_BASELINE_MISMATCH" in result.binding.reason_codes


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"issued_at": "2026-08-16T12:01:00Z"}, "FUTURE_EVIDENCE"),
        ({"expires_at": "2026-08-16T11:59:59Z"}, "EXPIRED_EVIDENCE"),
        ({"expires_at": None}, "REQUIRED_EXPIRY_MISSING"),
    ],
)
def test_time_and_expiry_fail_closed(prepared, changes, code):
    ws, _p, _pp, request, request_path, *_ = prepared
    outcome = _import(prepared, verifier=FixtureEvidenceVerifier(
        _payload(ws, request, request_path, **changes)))
    assert code in outcome.binding.reason_codes


def test_distinct_verified_envelopes_are_preserved_and_block_reliance(prepared):
    ws, _p, _pp, request, request_path, *_ = prepared
    payload = _payload(ws, request, request_path)
    first = _import(prepared, envelope=b"envelope-one",
                    verifier=FixtureEvidenceVerifier(payload))
    second = _import(prepared, envelope=b"envelope-two",
                     verifier=FixtureEvidenceVerifier(payload))
    assert first.envelope_path.exists() and second.envelope_path.exists()
    assert first.envelope_path != second.envelope_path
    assert second.conflict
    assert evidence_reliance_state(ws, request.content_hash) == "BLOCKED_CONFLICT"
    retry = _import(prepared, envelope=b"envelope-one",
                    verifier=FixtureEvidenceVerifier(payload))
    assert not retry.binding_created and retry.conflict


def test_ledger_events_are_factual_system_evidence(prepared):
    _import(prepared)
    events = ledger.read_events(prepared[0])
    evidence_events = [e for e in events if e["event_type"].startswith("evidence_")
                       or e["event_type"] == "signed_evidence_binding_recorded"]
    assert evidence_events
    assert all(e["actor"] == "conclave" and e["authority_level"] == "system"
               for e in evidence_events)
    text = json.dumps(evidence_events).lower()
    assert '"approved"' not in text and '"membership_effect":"member"' not in text
    assert ledger.verify(prepared[0]).ok


def test_reconciliation_restores_existence_events_without_inferring_pass(prepared):
    ws = prepared[0]
    _import(prepared)
    original = ledger.read_events(ws)[:2]
    ws.ledger_path.write_text(
        "".join(ledger.canonical_json(event) + "\n" for event in original),
        encoding="utf-8",
    )
    report = reconcile(ws)
    assert report.ok
    types = {event["event_type"] for event in report.created}
    assert "evidence_signing_request_recorded" in types
    assert "evidence_envelope_preserved" in types
    assert "signed_evidence_binding_recorded" in types
    assert "evidence_conflict_observed" not in types
    text = json.dumps(report.created)
    assert '"verification_status"' not in text
    assert "PASS" not in text
    assert ledger.verify(ws).ok


def test_reconciliation_refuses_to_infer_orphan_envelope(prepared):
    outcome = _import(prepared)
    outcome.binding_path.unlink()
    report = reconcile(prepared[0])
    assert any("orphan envelope" in item.reason for item in report.unresolved)


def test_closed_schemas_reject_unknown_fields(prepared):
    request = prepared[3].model_dump(mode="json")
    request["unknown"] = True
    with pytest.raises(PydanticValidationError):
        EvidenceSigningRequest.model_validate(request)
    binding = _import(prepared).binding.model_dump(mode="json")
    binding["unknown"] = True
    with pytest.raises(PydanticValidationError):
        SignedEvidenceBinding.model_validate(binding)
    ws, _p, _pp, original, request_path, *_ = prepared
    payload = _payload(ws, original, request_path).model_dump(mode="json")
    payload["unknown"] = True
    with pytest.raises(PydanticValidationError):
        SignedEvidencePayload.model_validate(payload)
    report = FixtureEvidenceVerifier(_payload(ws, original, request_path)).verify_evidence(
        envelope=b"x"
    ).model_dump(mode="json")
    report["unknown"] = True
    with pytest.raises(PydanticValidationError):
        IDMEvidenceVerifierReport.model_validate(report)


def test_no_key_signing_or_allocation_surface_exists():
    import conclave.evidence as module

    forbidden = {"sign", "generate_key", "load_private_key", "allocate_identity", "issue"}
    assert forbidden.isdisjoint(set(dir(module)))
