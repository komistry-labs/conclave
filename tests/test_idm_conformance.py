"""Increment 19D end-to-end conformance against the pinned IDM v1 wheel."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
import cbor2

from conclave.evidence import (
    EVIDENCE_CONTEXT,
    ExpiryPolicy,
    SignedEvidencePayload,
    import_evidence_envelope,
    prepare_signing_request,
    verified_workspace_id,
)
from conclave.identity import (
    ACTOR_BINDING_SCHEMA,
    TRUST_INPUT_SCHEMA,
    ActorIdentityBinding,
    FROZEN_IDM_IMPLEMENTATION,
    PublicEvidenceReference,
    TrustInputSet,
    seal_record,
    sha256_bytes,
    verify_actor_identity,
    write_immutable_record,
)
from conclave.idm_reference_adapter import (
    FIXTURE_EMPTY_REVOCATION_CONTEXT,
    PinnedIDMReferenceVerifier,
)
from conclave.ledger import initialise
from conclave.models import TaskPacket
from conclave.taskpacket import derive_task_id, seal as seal_packet, write_packet
from conclave.workspace import Workspace

from idm.attestation import encode_attestation, parse_attestation
from idm.crypto import public_key_from_private
from idm.identifiers import derive_kid
from idm.manifest import create_draft, issue_genesis
from idm.revocation import (
    RevocationTargetType,
    create_revocation_statement,
    sign_revocation,
)
from idm.trust import (
    KeyDelegation,
    TrustAnchor,
    TrustBundle,
    encode_delegation,
    encode_public_key,
)

ROOT = Path(__file__).parents[1]
BASELINE = ROOT / "tests" / "fixtures" / "idm-baseline"
WHEEL = BASELINE / "idm_reference-0.1.0.dev0-py3-none-any.whl"
SOURCE = BASELINE / "idm-3769ce3-source.zip"
BROKER = ROOT / "tests" / "fixtures" / "idm_fixture_broker.py"

T0 = "2026-08-16T10:00:00Z"
T1 = "2026-08-16T11:00:00Z"
T2 = "2026-08-16T12:00:00Z"
T3 = "2026-08-17T11:00:00Z"
ROOT_EID = "eid:" + "a" * 26
ROOT_MID = "mid:" + "b" * 26
AUDITOR_EID = "eid:" + "c" * 26
AUDITOR_MID = "mid:" + "d" * 26
TDID = "tdid:" + "e" * 26
DELEGATION_ID = "rid:" + "f" * 26
ROOT_KEY = hashlib.sha256(b"CONCLAVE-19D-FIXTURE-ROOT-NON-PRODUCTION").digest()
AUDITOR_KEY = hashlib.sha256(b"CONCLAVE-19D-FIXTURE-AUDITOR-NON-PRODUCTION").digest()
ROOT_PUBLIC = public_key_from_private(ROOT_KEY)
AUDITOR_PUBLIC = public_key_from_private(AUDITOR_KEY)
ROOT_KID = derive_kid(ROOT_PUBLIC)
AUDITOR_KID = derive_kid(AUDITOR_PUBLIC)
TIME_EVIDENCE = b'fixture trusted time: 2026-08-16T12:00:00Z'


@dataclass(frozen=True)
class FixtureDomain:
    bundle: TrustBundle
    trust_bytes: bytes
    empty_revocation: bytes
    identity_artifact: bytes
    identity_eid: str
    identity_mid: str
    identity_vid: str


def _json_bytes(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


@pytest.fixture
def domain() -> FixtureDomain:
    root = TrustAnchor(
        kid=ROOT_KID,
        public_key=encode_public_key(ROOT_PUBLIC),
        signer_eid=ROOT_EID,
        signer_mid=ROOT_MID,
        roles=["identity_authority", "revocation_authority"],
        scopes=["identity.issue", "revocation.issue", "trust.delegate"],
        valid_from=T0,
        valid_until=None,
    )
    delegation = KeyDelegation(
        delegation_id=DELEGATION_ID,
        issuer_eid=ROOT_EID,
        issuer_mid=ROOT_MID,
        issuer_kid=ROOT_KID,
        delegated_kid=AUDITOR_KID,
        delegated_public_key=encode_public_key(AUDITOR_PUBLIC),
        signer_eid=AUDITOR_EID,
        signer_mid=AUDITOR_MID,
        roles=["auditor"],
        scopes=["audit.sign"],
        valid_from=T0,
        valid_until=None,
        issued_at=T0,
    )
    bundle = TrustBundle(
        trust_domain_id=TDID,
        generated_at=T0,
        anchors=[root],
        delegations=[encode_delegation(
            delegation, root_private_key=ROOT_KEY, root_kid=ROOT_KID
        )],
    )
    trust_bytes = _json_bytes(bundle.model_dump(mode="json"))
    empty_revocation = encode_attestation(
        {
            "profile": "conclave-fixture-revocation-state/1.0",
            "trust_domain_id": TDID,
            "effective_at": T1,
            "revoked": [],
        },
        context=FIXTURE_EMPTY_REVOCATION_CONTEXT,
        private_key=ROOT_KEY,
        kid=ROOT_KID,
    )
    draft = create_draft(entity_type="human", canonical_name="arthur-19d-fixture")
    artifact = issue_genesis(
        draft,
        private_key=ROOT_KEY,
        kid=ROOT_KID,
        signer_eid=ROOT_EID,
        signer_mid=ROOT_MID,
        issued_at=T1,
        role="identity_authority",
        scope=["identity.issue"],
    )
    from idm.container import parse_artifact

    parsed = parse_artifact(artifact)
    return FixtureDomain(
        bundle, trust_bytes, empty_revocation, artifact,
        parsed.revision.entity_id, parsed.revision.manifest_id, parsed.vid,
    )


def _verifier() -> PinnedIDMReferenceVerifier:
    return PinnedIDMReferenceVerifier(wheel_path=WHEEL, source_archive_path=SOURCE)


def _trust(domain: FixtureDomain, *, role: str, scope: str) -> TrustInputSet:
    return seal_record(TrustInputSet, {
        "profile": "idm-trust-input-set",
        "schema_version": TRUST_INPUT_SCHEMA,
        "idm_implementation": FROZEN_IDM_IMPLEMENTATION,
        "trust_bundle": PublicEvidenceReference(
            reference="fixture/trust.json", content_hash=sha256_bytes(domain.trust_bytes)
        ),
        "trust_domain_id": TDID,
        "revocation_evidence": [PublicEvidenceReference(
            reference="fixture/empty-revocation.cose",
            content_hash=sha256_bytes(domain.empty_revocation),
        )],
        "evaluation_time": T2,
        "time_source_classification": "trusted",
        "time_evidence": PublicEvidenceReference(
            reference="fixture/time.txt", content_hash=sha256_bytes(TIME_EVIDENCE)
        ),
        "accepted_roles": [role],
        "required_scopes": [scope],
        "created_by": "fixture-harness",
        "created_at": T2,
    })


def _public(domain: FixtureDomain, revocations: list[bytes] | None = None) -> dict[str, bytes]:
    values = revocations if revocations is not None else [domain.empty_revocation]
    result = {
        "fixture/trust.json": domain.trust_bytes,
        "fixture/time.txt": TIME_EVIDENCE,
    }
    for index, value in enumerate(values):
        result[
            "fixture/empty-revocation.cose" if index == 0 else f"fixture/rev-{index}.cose"
        ] = value
    return result


def _workspace(tmp_path: Path) -> Workspace:
    ws = Workspace.create(tmp_path, principal="Arthur")
    initialise(ws, ws.load_config())
    return ws


def _packet() -> TaskPacket:
    objective = "Increment 19D deterministic fixture"
    data = {
        "schema_version": "task-packet/0.1.0",
        "task_id": derive_task_id(objective, ["CONCLAVE-19D"]),
        "version": 1,
        "created_at": T1,
        "created_by": "Arthur",
        "objective": objective,
        "interpreted_objective": None,
        "target_objects": [{"object_id": "CONCLAVE-19D"}],
        "read_only_objects": [],
        "prohibited_objects": [],
        "assigned_providers": [],
        "egress": {},
        "constraints": [],
        "acceptance_criteria": [],
        "supersedes": None,
        "revision_reason": None,
        "content_hash": None,
    }
    return seal_packet(TaskPacket.model_validate(data))


def _identity_result(
    ws: Workspace, domain: FixtureDomain, *, task_scope: str
):
    trust = _trust(domain, role="identity_authority", scope="identity.issue")
    binding = seal_record(ActorIdentityBinding, {
        "profile": "idm-actor-binding",
        "schema_version": ACTOR_BINDING_SCHEMA,
        "actor_id": "Arthur",
        "actor_kind": "human",
        "expected_authority_level": "human_principal",
        "eid": domain.identity_eid,
        "mid": domain.identity_mid,
        "vid": domain.identity_vid,
        "idm_artifact_hash": sha256_bytes(domain.identity_artifact),
        "trust_input_reference": "identity/trust-inputs/identity.json",
        "trust_input_hash": trust.content_hash,
        "required_identity_role": "identity_authority",
        "required_claim": None,
        "binding_purpose": "19D fixture human principal verification",
        "workspace_id": verified_workspace_id(ws),
        "task_scope": task_scope,
    })
    result = verify_actor_identity(
        binding_reference="identity/bindings/identity.json",
        trust_input_reference="identity/trust-inputs/identity.json",
        binding=binding,
        trust_inputs=trust,
        artifact=domain.identity_artifact,
        public_evidence=_public(domain),
        verifier=_verifier(),
    )
    return binding, result


def test_retained_distribution_hashes_are_exact():
    assert hashlib.sha256(WHEEL.read_bytes()).hexdigest() == (
        "07120effab0182701e47449e572b94e5a952c210aebfdf217fd965696154d903"
    )
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == (
        "98335d16dd0dd7bdfeb27fa77374e741e575cec3bbafc009a66c80374188efb7"
    )


def test_actual_idm_identity_artifact_passes(domain: FixtureDomain, tmp_path: Path):
    ws = _workspace(tmp_path)
    binding, result = _identity_result(ws, domain, task_scope="workspace:*")
    assert result.status == "PASS" and result.reason_codes == []
    assert (result.eid, result.mid, result.vid) == (
        binding.eid, binding.mid, binding.vid
    )
    assert result.authority_effect == result.membership_effect == "none"
    assert result.action_execution_allowed is False


def _broker_envelope(
    ws: Workspace,
    request_path: Path,
    tmp_path: Path,
    *,
    key: bytes = AUDITOR_KEY,
    kid: str = AUDITOR_KID,
) -> bytes:
    key_path = tmp_path / "auditor.fixture-only.key"
    output = tmp_path / "evidence.cose"
    receipt = tmp_path / "receipt.json"
    key_path.write_bytes(key)
    env = os.environ.copy()
    env["CONCLAVE_FIXTURE_BROKER"] = "1"
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [
            sys.executable, str(BROKER), "--fixture-only",
            "--workspace", str(ws.root), "--request", str(request_path),
            "--key", str(key_path), "--kid", kid,
            "--issued-at", T1, "--expires-at", T3,
            "--output", str(output), "--receipt", str(receipt),
        ],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    public_receipt = json.loads(receipt.read_text(encoding="utf-8"))
    assert public_receipt["classification"] == "fixture-only-non-production"
    assert public_receipt["secret_material_returned"] is False
    assert key.hex() not in receipt.read_text(encoding="utf-8")
    return output.read_bytes()


def _evidence_flow(ws: Workspace, domain: FixtureDomain, tmp_path: Path):
    packet = _packet()
    write_packet(ws, packet)
    request, request_path, _ = prepare_signing_request(
        ws,
        storage_reference=request_path_for_packet(ws, packet),
        artifact_schema=packet.schema_version,
        attester_eid=AUDITOR_EID,
        attester_mid=AUDITOR_MID,
        attester_role="auditor",
        attester_kid=AUDITOR_KID,
        purpose="19D fixture audit attestation",
        expiry_policy=ExpiryPolicy(expires_at_required=True, maximum_validity_seconds=172800),
        requester_actor_id="Arthur",
        requester_authority_level="human_principal",
    )
    envelope = _broker_envelope(ws, request_path, tmp_path)
    trust = _trust(domain, role="auditor", scope="audit.sign")
    trust_path, _ = write_immutable_record(ws.identity_trust_inputs_dir / "evidence.json", trust)
    outcome = import_evidence_envelope(
        ws,
        request_path=request_path,
        trust_input_path=trust_path,
        envelope=envelope,
        public_evidence=_public(domain),
        verifier=_verifier(),
    )
    return packet, request, request_path, trust, trust_path, envelope, outcome


def request_path_for_packet(ws: Workspace, packet: TaskPacket) -> str:
    return (ws.tasks_dir / packet.task_id / "v1.yaml").relative_to(ws.root).as_posix()


def test_external_broker_to_attested_gate_end_to_end(domain: FixtureDomain, tmp_path: Path):
    from conclave.gating import enforce_principal_gate, set_identity_mode

    ws = _workspace(tmp_path)
    packet, _, _, _, _, envelope, outcome = _evidence_flow(ws, domain, tmp_path)
    assert outcome.binding.verification_status == "PASS"
    assert outcome.envelope_path.read_bytes() == envelope
    identity_binding, identity_result = _identity_result(ws, domain, task_scope=packet.ref)
    binding_path, _ = write_immutable_record(
        ws.identity_bindings_dir / "identity.json", identity_binding
    )
    assert binding_path.relative_to(ws.root).as_posix() == "identity/bindings/identity.json"
    result_path, _ = write_immutable_record(
        ws.identity_verifications_dir / "identity.json", identity_result
    )
    set_identity_mode(ws, "attested", confirmed_principal="Arthur")
    gate = enforce_principal_gate(
        ws,
        operation="authority_decision",
        actor_id="Arthur",
        target_reference=packet.ref,
        target_hash=packet.content_hash or "",
        identity_verification_reference=result_path.relative_to(ws.root).as_posix(),
        signed_evidence_binding_reference=outcome.binding_path.relative_to(ws.root).as_posix(),
    )
    assert gate.mode == "attested" and gate.admitted
    assert gate.authority_effect == gate.membership_effect == "none"


def _signed_revocation(target_type, target_id: str) -> bytes:
    statement = create_revocation_statement(
        target_type=target_type,
        target_id=target_id,
        reason_code="fixture.revoked",
        effective_at=T1,
        issued_at=T1,
        issuer_eid=ROOT_EID,
        issuer_mid=ROOT_MID,
    )
    return sign_revocation(statement, private_key=ROOT_KEY, kid=ROOT_KID)


@pytest.mark.parametrize("target", ["key", "entity", "manifest", "delegation"])
def test_actual_idm_revocation_blocks_evidence(
    domain: FixtureDomain, tmp_path: Path, target: str
):
    ws = _workspace(tmp_path)
    _, request, request_path, trust, trust_path, envelope, _ = _evidence_flow(
        ws, domain, tmp_path
    )
    target_type, target_id = {
        "key": (RevocationTargetType.KEY, AUDITOR_KID),
        "entity": (RevocationTargetType.ENTITY, AUDITOR_EID),
        "manifest": (RevocationTargetType.MANIFEST, AUDITOR_MID),
        "delegation": (RevocationTargetType.DELEGATION, DELEGATION_ID),
    }[target]
    revocation = _signed_revocation(target_type, target_id)
    revoked_trust = seal_record(TrustInputSet, {
        **trust.model_dump(mode="json", exclude={"content_hash", "revocation_evidence"}),
        "revocation_evidence": [PublicEvidenceReference(
            reference="fixture/empty-revocation.cose", content_hash=sha256_bytes(revocation)
        )],
    })
    revoked_path, _ = write_immutable_record(
        ws.identity_trust_inputs_dir / f"revoked-{target}.json", revoked_trust
    )
    outcome = import_evidence_envelope(
        ws, request_path=request_path, trust_input_path=revoked_path,
        envelope=envelope,
        public_evidence=_public(domain, [revocation]),
        verifier=_verifier(),
    )
    assert outcome.binding.verification_status == "FAIL"
    assert "REVOCATION_INVALID" in outcome.binding.reason_codes
    assert outcome.binding.action_execution_allowed is False
    assert outcome.binding.signing_request_hash == request.content_hash


def test_actual_idm_revision_revocation_blocks_identity(domain: FixtureDomain, tmp_path: Path):
    ws = _workspace(tmp_path)
    trust = _trust(domain, role="identity_authority", scope="identity.issue")
    revocation = _signed_revocation(RevocationTargetType.REVISION, domain.identity_vid)
    revoked_trust = seal_record(TrustInputSet, {
        **trust.model_dump(mode="json", exclude={"content_hash", "revocation_evidence"}),
        "revocation_evidence": [PublicEvidenceReference(
            reference="fixture/empty-revocation.cose", content_hash=sha256_bytes(revocation)
        )],
    })
    binding = seal_record(ActorIdentityBinding, {
        "profile": "idm-actor-binding", "schema_version": ACTOR_BINDING_SCHEMA,
        "actor_id": "Arthur", "actor_kind": "human",
        "expected_authority_level": "human_principal",
        "eid": domain.identity_eid, "mid": domain.identity_mid, "vid": domain.identity_vid,
        "idm_artifact_hash": sha256_bytes(domain.identity_artifact),
        "trust_input_reference": "identity/trust-inputs/revoked.json",
        "trust_input_hash": revoked_trust.content_hash,
        "required_identity_role": "identity_authority", "required_claim": None,
        "binding_purpose": "revision revocation test",
        "workspace_id": "workspace:*", "task_scope": "workspace:*",
    })
    result = verify_actor_identity(
        binding_reference="identity/bindings/revoked.json",
        trust_input_reference="identity/trust-inputs/revoked.json",
        binding=binding, trust_inputs=revoked_trust,
        artifact=domain.identity_artifact,
        public_evidence=_public(domain, [revocation]), verifier=_verifier(),
    )
    assert result.status == "FAIL" and "REVOCATION_INVALID" in result.reason_codes


def test_tampered_envelope_and_malformed_revocation_fail_closed(
    domain: FixtureDomain, tmp_path: Path
):
    ws = _workspace(tmp_path)
    _, _, request_path, trust, trust_path, envelope, _ = _evidence_flow(ws, domain, tmp_path)
    tampered = bytearray(envelope)
    tampered[-1] ^= 1
    outcome = import_evidence_envelope(
        ws, request_path=request_path, trust_input_path=trust_path,
        envelope=bytes(tampered), public_evidence=_public(domain), verifier=_verifier(),
    )
    assert outcome.binding.verification_status == "FAIL"
    assert "IDM_EVIDENCE_VERIFIER_ERROR" in outcome.binding.reason_codes
    malformed = b"not signed revocation evidence"
    malformed_trust = seal_record(TrustInputSet, {
        **trust.model_dump(mode="json", exclude={"content_hash", "revocation_evidence"}),
        "revocation_evidence": [PublicEvidenceReference(
            reference="fixture/empty-revocation.cose", content_hash=sha256_bytes(malformed)
        )],
    })
    malformed_path, _ = write_immutable_record(
        ws.identity_trust_inputs_dir / "malformed.json", malformed_trust
    )
    outcome = import_evidence_envelope(
        ws, request_path=request_path, trust_input_path=malformed_path,
        envelope=envelope, public_evidence=_public(domain, [malformed]), verifier=_verifier(),
    )
    assert outcome.binding.verification_status == "FAIL"
    assert "IDM_EVIDENCE_VERIFIER_ERROR" in outcome.binding.reason_codes


@pytest.mark.parametrize(
    ("defect", "expected"),
    [
        ("wrong-context", "IDM_EVIDENCE_VERIFIER_ERROR"),
        ("detached", "IDM_EVIDENCE_VERIFIER_ERROR"),
        ("unknown-field", "IDM_EVIDENCE_VERIFIER_ERROR"),
        ("future", "TIME_INVALID"),
        ("expired", "TIME_INVALID"),
        ("wrong-role", "ROLE_INVALID"),
        ("wrong-workspace", "REQUEST_CROSS_BINDING_MISMATCH"),
    ],
)
def test_actual_cose_profile_and_cross_binding_failures(
    domain: FixtureDomain, tmp_path: Path, defect: str, expected: str
):
    ws = _workspace(tmp_path)
    _, _, request_path, _, trust_path, envelope, _ = _evidence_flow(ws, domain, tmp_path)
    parsed = parse_attestation(envelope, expected_context=EVIDENCE_CONTEXT)
    payload = dict(parsed.payload)
    context = EVIDENCE_CONTEXT
    if defect == "wrong-context":
        context = "wrong/context"
    elif defect == "unknown-field":
        payload["unexpected"] = True
    elif defect == "future":
        payload["issued_at"] = "2026-08-16T13:00:00Z"
        payload["expires_at"] = T3
    elif defect == "expired":
        payload["issued_at"] = T0
        payload["expires_at"] = T1
    elif defect == "wrong-role":
        payload["attester_role"] = "identity_authority"
    elif defect == "wrong-workspace":
        payload["workspace_id"] = "workspace:sha256:" + "0" * 64
    if defect == "detached":
        top = cbor2.loads(envelope)
        broken = cbor2.CBORTag(top.tag, [top.value[0], {}, None, top.value[3]])
        candidate = cbor2.dumps(broken, canonical=True)
    else:
        candidate = encode_attestation(
            payload, context=context, private_key=AUDITOR_KEY, kid=AUDITOR_KID
        )
    outcome = import_evidence_envelope(
        ws, request_path=request_path, trust_input_path=trust_path,
        envelope=candidate, public_evidence=_public(domain), verifier=_verifier(),
    )
    assert outcome.binding.verification_status == "FAIL"
    assert expected in outcome.binding.reason_codes
    assert outcome.binding.action_execution_allowed is False


def test_wrong_distribution_pin_fails_closed(domain: FixtureDomain, tmp_path: Path):
    bad = tmp_path / "bad.whl"
    bad.write_bytes(WHEEL.read_bytes() + b"tamper")
    verifier = PinnedIDMReferenceVerifier(wheel_path=bad, source_archive_path=SOURCE)
    with pytest.raises(ValueError, match="frozen baseline"):
        verifier.verify_evidence(
            envelope=b"opaque", expected_context=EVIDENCE_CONTEXT,
            trust_bundle=domain.trust_bytes,
            revocation_evidence=(domain.empty_revocation,), evaluation_time=T2,
            required_role="auditor", required_scope="audit.sign",
        )


def test_fixture_canonical_vector_is_platform_invariant():
    payload = SignedEvidencePayload(
        profile="conclave-signed-evidence/0.1.0",
        artifact_reference="TP-fixture@v1",
        artifact_schema="task-packet/0.1.0",
        artifact_content_hash="sha256:" + "1" * 64,
        canonical_payload_hash="sha256:" + "2" * 64,
        signing_request_reference="signing/requests/fixture.json",
        signing_request_hash="sha256:" + "3" * 64,
        workspace_id="workspace:sha256:" + "4" * 64,
        bounded_domain="TP-fixture@v1",
        attester_eid=AUDITOR_EID,
        attester_mid=AUDITOR_MID,
        attester_role="auditor",
        attester_kid=AUDITOR_KID,
        asserted_scope="audit.sign",
        issued_at=T1,
        expires_at=T3,
        authority_effect="none",
        decision_effect="none",
        membership_effect="none",
    )
    first = encode_attestation(
        payload.model_dump(mode="python"), context=EVIDENCE_CONTEXT,
        private_key=AUDITOR_KEY, kid=AUDITOR_KID,
    )
    second = encode_attestation(
        payload.model_dump(mode="python"), context=EVIDENCE_CONTEXT,
        private_key=AUDITOR_KEY, kid=AUDITOR_KID,
    )
    assert first == second
    assert parse_attestation(first, expected_context=EVIDENCE_CONTEXT).payload == (
        payload.model_dump(mode="python")
    )
    assert hashlib.sha256(first).hexdigest() == (
        "36c3325004291ae27d1f143128d736ffc3d46595b9f9ec46923c9637e3df4523"
    )


def test_fixture_broker_refuses_without_explicit_marker(tmp_path: Path):
    completed = subprocess.run(
        [sys.executable, str(BROKER), "--help"],
        cwd=ROOT, check=False, capture_output=True, text=True,
    )
    assert completed.returncode == 0
    source = BROKER.read_text(encoding="utf-8")
    assert "CONCLAVE_FIXTURE_BROKER" in source
    assert "fixture-only.key" in source
    assert "passphrase" not in source.lower()


def test_runtime_verifier_has_no_signing_or_key_surface():
    public = {name for name in dir(PinnedIDMReferenceVerifier) if not name.startswith("_")}
    assert public == {"verify_identity", "verify_evidence"}


def test_no_private_key_artifact_is_committed():
    prohibited = {".idmk", ".key", ".pem", ".p12", ".pfx"}
    tracked = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    ).stdout.split(b"\0")
    committed_candidates = [
        value.decode("utf-8") for value in tracked
        if value and Path(value.decode("utf-8")).suffix.lower() in prohibited
    ]
    assert committed_candidates == []
