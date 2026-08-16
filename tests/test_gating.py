"""Increment 19C opt-in workflow-gating acceptance and negative tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from conclave.cli import app, evidence_app, identity_app
from conclave.checkpoint import (
    CHECKPOINT_SCHEMA,
    prepare_ledger_checkpoint,
    record_signed_checkpoint,
)
from conclave.council import CouncilReview, seal as seal_council, write_council
from conclave.decision import DecisionInstruction, record_decision
from conclave.errors import ValidationError
from conclave.evidence import (
    EVIDENCE_CONTEXT,
    EVIDENCE_SCOPE,
    SIGNED_BINDING_SCHEMA,
    SIGNED_PAYLOAD_PROFILE,
    EvidenceVerificationFindings,
    SignedEvidenceBinding,
    SignedEvidencePayload,
    resolve_stored_artifact,
    verified_workspace_id,
)
from conclave.gating import (
    enforce_principal_gate,
    identity_mode,
    import_actor_binding,
    record_evidence_receipt,
    set_identity_mode,
)
from conclave.identity import (
    ACTOR_BINDING_SCHEMA,
    VERIFICATION_RESULT_SCHEMA,
    ActorIdentityBinding,
    FROZEN_IDM_IMPLEMENTATION,
    IdentityVerificationResult,
    PublicEvidenceReference,
    VerificationFindings,
    seal_record,
    sha256_bytes,
    write_immutable_record,
)
from conclave.ledger import initialise, read_events, verify
from conclave.providers import EGRESS_SCHEMA_VERSION, read_egress_decision
from conclave.taskpacket import build_packet, write_packet
from conclave.workspace import Workspace

EID = "eid:" + "a" * 26
MID = "mid:" + "b" * 26
VID = "vid:sha256:" + "A" * 43
KID = "kid:sha256:" + "C" * 43
TDID = "tdid:" + "d" * 26


@pytest.fixture
def ws(tmp_path: Path) -> Workspace:
    value = Workspace.create(tmp_path, principal="Arthur")
    initialise(value, value.load_config())
    return value


def _identity_pass(
    ws: Workspace, target: str, *, actor: str = "Arthur", workspace_id: str | None = None
) -> tuple[str, IdentityVerificationResult]:
    binding = seal_record(ActorIdentityBinding, {
        "profile": "idm-actor-binding",
        "schema_version": ACTOR_BINDING_SCHEMA,
        "actor_id": actor,
        "actor_kind": "human",
        "expected_authority_level": "human_principal",
        "eid": EID,
        "mid": MID,
        "vid": VID,
        "idm_artifact_hash": sha256_bytes(b"fixture identity"),
        "trust_input_reference": "identity/trust-inputs/fixture.json",
        "trust_input_hash": sha256_bytes(b"fixture trust inputs"),
        "required_identity_role": "human_principal",
        "required_claim": None,
        "binding_purpose": "19C fixture gate",
        "workspace_id": workspace_id or verified_workspace_id(ws),
        "task_scope": target,
    })
    binding_name = binding.content_hash.split(":", 1)[1] + ".json"
    binding_path, _ = write_immutable_record(ws.identity_bindings_dir / binding_name, binding)
    binding_ref = binding_path.relative_to(ws.root).as_posix()
    findings = VerificationFindings(
        trust=True, signature=True, lineage=True, delegation=True, role=True,
        scope=True, time=True, revocation=True, actor_binding=True,
    )
    result = seal_record(IdentityVerificationResult, {
        "profile": "idm-verification-result",
        "schema_version": VERIFICATION_RESULT_SCHEMA,
        "status": "PASS",
        "actor_binding_reference": binding_ref,
        "actor_binding_hash": binding.content_hash,
        "eid": EID,
        "mid": MID,
        "vid": VID,
        "idm_artifact_hash": binding.idm_artifact_hash,
        "findings": findings,
        "verifier_implementation": FROZEN_IDM_IMPLEMENTATION,
        "evaluation_time": "2026-08-16T12:00:00Z",
        "time_source_classification": "trusted",
        "trust_bundle": PublicEvidenceReference(
            reference="public/fixture-trust.json", content_hash=sha256_bytes(b"trust")
        ),
        "revocation_evidence": [PublicEvidenceReference(
            reference="public/fixture-revocation.cose",
            content_hash=sha256_bytes(b"revocation"),
        )],
        "reason_codes": [],
        "authority_effect": "none",
        "membership_effect": "none",
        "action_execution_allowed": False,
    })
    result_name = result.content_hash.split(":", 1)[1] + ".json"
    result_path, _ = write_immutable_record(ws.identity_verifications_dir / result_name, result)
    return result_path.relative_to(ws.root).as_posix(), result


def _signed_binding(
    ws: Workspace,
    target: str,
    target_hash: str,
    *,
    request_hash: str | None = None,
    envelope_byte: bytes = b"a",
) -> tuple[str, SignedEvidenceBinding]:
    request_hash = request_hash or sha256_bytes(b"request")
    payload = SignedEvidencePayload(
        profile=SIGNED_PAYLOAD_PROFILE,
        artifact_reference=target,
        artifact_schema="council-review/0.1.0",
        artifact_content_hash=target_hash,
        canonical_payload_hash=sha256_bytes(b"payload"),
        signing_request_reference="signing/requests/fixture.json",
        signing_request_hash=request_hash,
        workspace_id=verified_workspace_id(ws),
        bounded_domain=target,
        attester_eid=EID,
        attester_mid=MID,
        attester_role="auditor",
        attester_kid=KID,
        asserted_scope=EVIDENCE_SCOPE,
        issued_at="2026-08-16T11:00:00Z",
        expires_at="2026-08-17T11:00:00Z",
        authority_effect="none",
        decision_effect="none",
        membership_effect="none",
    )
    findings = EvidenceVerificationFindings(
        attached_payload=True, canonical_cbor=True, context=True, trust=True,
        signature=True, delegation=True, role=True, scope=True, time=True,
        revocation=True, cross_binding=True,
    )
    envelope_hash = sha256_bytes(envelope_byte)
    binding = seal_record(SignedEvidenceBinding, {
        "profile": "signed-evidence-binding",
        "schema_version": SIGNED_BINDING_SCHEMA,
        "verification_status": "PASS",
        "evidence_id": "evidence:sha256:" + "A" * 43,
        "envelope_hash": envelope_hash,
        "envelope_storage_reference": "signing/envelopes/" + envelope_hash[7:] + ".cose",
        "signing_request_reference": "signing/requests/fixture.json",
        "signing_request_hash": request_hash,
        "trust_input_reference": "identity/trust-inputs/fixture.json",
        "trust_input_hash": sha256_bytes(b"trust input"),
        "payload": payload,
        "findings": findings,
        "request_binding_verified": True,
        "reason_codes": [],
        "verifier_implementation": FROZEN_IDM_IMPLEMENTATION,
        "conflict_observed_at_import": False,
        "authority_effect": "none",
        "decision_effect": "none",
        "membership_effect": "none",
        "action_execution_allowed": False,
    })
    name = binding.content_hash.split(":", 1)[1] + ".json"
    path, _ = write_immutable_record(ws.signing_bindings_dir / name, binding)
    return path.relative_to(ws.root).as_posix(), binding


def test_new_and_legacy_workspaces_are_local(tmp_path: Path):
    workspace = Workspace.create(tmp_path, principal="Arthur")
    assert identity_mode(workspace) == "local"
    config = workspace.load_config()
    config.pop("identity")
    workspace.config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    assert identity_mode(workspace) == "local"


def test_mode_strengthening_requires_principal_and_healthy_ledger(ws: Workspace, tmp_path: Path):
    with pytest.raises(ValidationError, match="principal confirmation"):
        set_identity_mode(ws, "verify", confirmed_principal="Claude")
    assert set_identity_mode(ws, "verify", confirmed_principal="Arthur") == ("verify", True)
    assert set_identity_mode(ws, "verify", confirmed_principal="Arthur") == ("verify", False)
    with pytest.raises(ValidationError, match="downgrade"):
        set_identity_mode(ws, "local", confirmed_principal="Arthur")
    uninitialised = Workspace.create(tmp_path / "other", principal="Arthur")
    with pytest.raises(ValidationError, match="initialized"):
        set_identity_mode(uninitialised, "verify", confirmed_principal="Arthur")


def test_local_gate_preserves_existing_behavior(ws: Workspace):
    outcome = enforce_principal_gate(
        ws, operation="authority_decision", actor_id="Arthur",
        target_reference="CR-fixture", target_hash=sha256_bytes(b"review"),
    )
    assert outcome.mode == "local" and outcome.admitted
    assert outcome.authority_effect == outcome.membership_effect == "none"


def test_verify_mode_requires_exact_principal_identity_pass(ws: Workspace):
    set_identity_mode(ws, "verify", confirmed_principal="Arthur")
    with pytest.raises(ValidationError, match="requires an identity verification"):
        enforce_principal_gate(
            ws, operation="authority_decision", actor_id="Arthur",
            target_reference="CR-fixture", target_hash=sha256_bytes(b"review"),
        )
    reference, result = _identity_pass(ws, "CR-fixture")
    outcome = enforce_principal_gate(
        ws, operation="authority_decision", actor_id="Arthur",
        target_reference="CR-fixture", target_hash=sha256_bytes(b"review"),
        identity_verification_reference=reference,
    )
    assert outcome.identity_verification_hash == result.content_hash
    assert outcome.signed_evidence_binding_hash is None


@pytest.mark.parametrize("defect", ["actor", "workspace", "scope"])
def test_verify_mode_rejects_cross_binding_substitution(ws: Workspace, defect: str):
    set_identity_mode(ws, "verify", confirmed_principal="Arthur")
    target = "CR-fixture"
    reference, _ = _identity_pass(
        ws,
        "other" if defect == "scope" else target,
        actor="Mallory" if defect == "actor" else "Arthur",
        workspace_id="workspace:sha256:" + "0" * 64 if defect == "workspace" else None,
    )
    with pytest.raises(ValidationError):
        enforce_principal_gate(
            ws, operation="authority_decision", actor_id="Arthur",
            target_reference=target, target_hash=sha256_bytes(b"review"),
            identity_verification_reference=reference,
        )


def test_gate_rejects_path_escape(ws: Workspace):
    set_identity_mode(ws, "verify", confirmed_principal="Arthur")
    with pytest.raises(ValidationError, match="canonical"):
        enforce_principal_gate(
            ws, operation="authority_decision", actor_id="Arthur",
            target_reference="CR-fixture", target_hash=sha256_bytes(b"review"),
            identity_verification_reference="..\\secret.json",
        )


def test_attested_mode_requires_one_exact_nonconflicting_binding(ws: Workspace):
    target, target_hash = "CR-fixture", sha256_bytes(b"review")
    identity_ref, _ = _identity_pass(ws, target)
    set_identity_mode(ws, "attested", confirmed_principal="Arthur")
    with pytest.raises(ValidationError, match="requires a signed evidence binding"):
        enforce_principal_gate(
            ws, operation="authority_decision", actor_id="Arthur",
            target_reference=target, target_hash=target_hash,
            identity_verification_reference=identity_ref,
        )
    binding_ref, binding = _signed_binding(ws, target, target_hash)
    outcome = enforce_principal_gate(
        ws, operation="authority_decision", actor_id="Arthur",
        target_reference=target, target_hash=target_hash,
        identity_verification_reference=identity_ref,
        signed_evidence_binding_reference=binding_ref,
    )
    assert outcome.signed_evidence_binding_hash == binding.content_hash
    _signed_binding(
        ws, target, target_hash,
        request_hash=binding.signing_request_hash, envelope_byte=b"different",
    )
    with pytest.raises(ValidationError, match="conflicting evidence"):
        enforce_principal_gate(
            ws, operation="authority_decision", actor_id="Arthur",
            target_reference=target, target_hash=target_hash,
            identity_verification_reference=identity_ref,
            signed_evidence_binding_reference=binding_ref,
        )


def test_attested_mode_rejects_wrong_target(ws: Workspace):
    identity_ref, _ = _identity_pass(ws, "CR-fixture")
    binding_ref, _ = _signed_binding(ws, "other", sha256_bytes(b"other"))
    set_identity_mode(ws, "attested", confirmed_principal="Arthur")
    with pytest.raises(ValidationError, match="does not bind"):
        enforce_principal_gate(
            ws, operation="authority_decision", actor_id="Arthur",
            target_reference="CR-fixture", target_hash=sha256_bytes(b"review"),
            identity_verification_reference=identity_ref,
            signed_evidence_binding_reference=binding_ref,
        )


def _council(ws: Workspace):
    packet = build_packet(
        objective="Review gated decision", created_by="Arthur",
        target_objects=[{"object_id": "RA-001"}], assigned_providers=[],
    )
    write_packet(ws, packet)
    review = seal_council(CouncilReview(
        council_review_id=f"CR-{packet.task_id}-v1-dec1510abc",
        task_packet_ref=packet.ref, task_packet_hash=packet.content_hash,
        created_at="2026-08-16T10:00:00Z",
        review_status="ready_for_human_review", human_decision_required=True,
    ))
    write_council(ws, review)
    instruction = DecisionInstruction(
        council_review_id=review.council_review_id,
        council_review_hash=review.content_hash,
        decision="approve", decided_by="Arthur", decided_at="2026-08-16T10:10:00Z",
        rationale="The bounded evidence is sufficient.", authorised_actions=[],
        authority_ref="Arthur confirmation",
    )
    return review, instruction


def test_authority_decision_gate_fails_before_artifact_write(ws: Workspace):
    review, instruction = _council(ws)
    set_identity_mode(ws, "verify", confirmed_principal="Arthur")
    with pytest.raises(ValidationError, match="requires an identity verification"):
        record_decision(ws, instruction, confirmed_principal="Arthur")
    assert not list(ws.decisions_dir.glob("*.yaml"))
    identity_ref, _ = _identity_pass(ws, review.council_review_id)
    outcome = record_decision(
        ws, instruction, confirmed_principal="Arthur",
        identity_verification_reference=identity_ref,
    )
    assert outcome.created
    event = read_events(ws)[-1]
    assert event["payload"]["identity_mode"] == "verify"
    assert event["payload"]["identity_authority_effect"] == "none"


def _egress_file(ws: Workspace) -> Path:
    path = ws.decisions_dir / "egress.yaml"
    path.write_text(yaml.safe_dump({
        "schema_version": EGRESS_SCHEMA_VERSION,
        "allowed": True,
        "transports": ["fixture"],
        "classifications": ["public"],
        "authority": "Arthur",
        "decision_ref": "D7-FIXTURE",
    }), encoding="utf-8")
    return path


def test_egress_decision_gate_and_evidence_resolver(ws: Workspace):
    path = _egress_file(ws)
    resolved = resolve_stored_artifact(
        ws,
        storage_reference=path.relative_to(ws.root).as_posix(),
        artifact_schema=EGRESS_SCHEMA_VERSION,
    )
    assert resolved.reference == "D7-FIXTURE"
    set_identity_mode(ws, "verify", confirmed_principal="Arthur")
    with pytest.raises(ValidationError, match="requires an identity verification"):
        read_egress_decision(path, principal="Arthur", workspace=ws)
    identity_ref, _ = _identity_pass(ws, "D7-FIXTURE")
    decision = read_egress_decision(
        path, principal="Arthur", workspace=ws,
        identity_verification_reference=identity_ref,
    )
    assert decision.allowed


def test_import_binding_is_claim_only_and_idempotent(ws: Workspace, tmp_path: Path):
    reference, result = _identity_pass(ws, "workspace:*")
    source = ws.root / result.actor_binding_reference
    first = import_actor_binding(ws, source, confirmed_principal="Arthur")
    second = import_actor_binding(ws, source, confirmed_principal="Arthur")
    assert first[1] == second[1] and not second[2]
    event = [e for e in read_events(ws) if e["event_type"] == "actor_identity_binding_imported"][-1]
    assert event["payload"]["claim_status"] == "awaiting-verification"
    assert event["payload"]["action_execution_allowed"] is False
    with pytest.raises(ValidationError, match="confirmation"):
        import_actor_binding(ws, source, confirmed_principal="Claude")
    assert reference.startswith("identity/verifications/")


def test_attested_receipt_is_factual_idempotent_and_authority_neutral(ws: Workspace):
    target, target_hash = "CR-fixture", sha256_bytes(b"review")
    identity_ref, _ = _identity_pass(ws, target)
    binding_ref, _ = _signed_binding(ws, target, target_hash)
    set_identity_mode(ws, "attested", confirmed_principal="Arthur")
    first = record_evidence_receipt(
        ws, signed_evidence_binding_reference=binding_ref,
        identity_verification_reference=identity_ref, confirmed_principal="Arthur",
    )
    second = record_evidence_receipt(
        ws, signed_evidence_binding_reference=binding_ref,
        identity_verification_reference=identity_ref, confirmed_principal="Arthur",
    )
    assert first[0]["event_id"] == second[0]["event_id"] and not second[1]
    assert first[0]["payload"]["decision_effect"] == "none"
    assert first[0]["payload"]["action_execution_allowed"] is False
    assert verify(ws).ok


def test_checkpoint_candidate_is_immutable_idempotent_and_resolvable(ws: Workspace):
    first = prepare_ledger_checkpoint(ws)
    second = prepare_ledger_checkpoint(ws)
    assert first[0].content_hash == second[0].content_hash
    assert first[1] == second[1] and not second[2]
    resolved = resolve_stored_artifact(
        ws,
        storage_reference=first[1].relative_to(ws.root).as_posix(),
        artifact_schema=CHECKPOINT_SCHEMA,
    )
    assert resolved.reference == first[0].content_hash
    assert resolved.content_hash == first[0].content_hash
    assert first[0].action_execution_allowed is False


def test_signed_checkpoint_requires_attested_mode_and_exact_evidence(ws: Workspace):
    checkpoint, path, _ = prepare_ledger_checkpoint(ws)
    reference = path.relative_to(ws.root).as_posix()
    identity_ref, _ = _identity_pass(ws, checkpoint.content_hash)
    binding_ref, _ = _signed_binding(ws, checkpoint.content_hash, checkpoint.content_hash)
    with pytest.raises(ValidationError, match="requires attested mode"):
        record_signed_checkpoint(
            ws, checkpoint_reference=reference,
            identity_verification_reference=identity_ref,
            signed_evidence_binding_reference=binding_ref,
            confirmed_principal="Arthur",
        )
    set_identity_mode(ws, "attested", confirmed_principal="Arthur")
    event, created = record_signed_checkpoint(
        ws, checkpoint_reference=reference,
        identity_verification_reference=identity_ref,
        signed_evidence_binding_reference=binding_ref,
        confirmed_principal="Arthur",
    )
    assert created and event["event_type"] == "signed_ledger_checkpoint_recorded"
    assert event["payload"]["authority_effect"] == "none"
    assert event["payload"]["action_execution_allowed"] is False
    retry = record_signed_checkpoint(
        ws, checkpoint_reference=reference,
        identity_verification_reference=identity_ref,
        signed_evidence_binding_reference=binding_ref,
        confirmed_principal="Arthur",
    )
    assert retry[0]["event_id"] == event["event_id"] and not retry[1]
    assert verify(ws).ok


def test_signed_checkpoint_rejects_wrong_confirmation_and_path(ws: Workspace):
    checkpoint, path, _ = prepare_ledger_checkpoint(ws)
    identity_ref, _ = _identity_pass(ws, checkpoint.content_hash)
    binding_ref, _ = _signed_binding(ws, checkpoint.content_hash, checkpoint.content_hash)
    set_identity_mode(ws, "attested", confirmed_principal="Arthur")
    with pytest.raises(ValidationError, match="confirmation"):
        record_signed_checkpoint(
            ws, checkpoint_reference=path.relative_to(ws.root).as_posix(),
            identity_verification_reference=identity_ref,
            signed_evidence_binding_reference=binding_ref,
            confirmed_principal="Claude",
        )
    with pytest.raises(ValidationError, match="canonical"):
        record_signed_checkpoint(
            ws, checkpoint_reference="..\\checkpoint.json",
            identity_verification_reference=identity_ref,
            signed_evidence_binding_reference=binding_ref,
            confirmed_principal="Arthur",
        )
    with pytest.raises(ValidationError, match="canonical"):
        record_signed_checkpoint(
            ws, checkpoint_reference="ledger/../ledger/" + path.name,
            identity_verification_reference=identity_ref,
            signed_evidence_binding_reference=binding_ref,
            confirmed_principal="Arthur",
        )


def test_cli_mode_change_is_interactive_and_no_silent_upgrade(ws: Workspace, monkeypatch):
    monkeypatch.setenv("CONCLAVE_HOME", str(ws.root))
    runner = CliRunner()
    refused = runner.invoke(app, ["identity", "set-mode", "verify"], input="Claude\n")
    assert refused.exit_code == 1 and identity_mode(ws) == "local"
    accepted = runner.invoke(app, ["identity", "set-mode", "verify"], input="Arthur\n")
    assert accepted.exit_code == 0 and identity_mode(ws) == "verify"
    assert runner.invoke(app, ["identity", "show-mode"]).output.strip() == "verify"


def test_no_signing_or_key_command_surface():
    root = CliRunner().invoke(app, ["--help"]).output.lower()
    assert "identity" in root and "evidence" in root
    names = {
        *(item.name for item in identity_app.registered_commands),
        *(item.name for item in evidence_app.registered_commands),
    }
    assert names == {"show-mode", "set-mode", "import-binding", "record-receipt"}
    assert not names.intersection({"allocate", "issue", "key", "sign", "membership"})
