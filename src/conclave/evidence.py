"""Increment 19B signing-request and signed-evidence import boundary.

This module prepares public requests and imports externally produced evidence.
It contains no signing, key, allocation, issuance, broker, or secret interface.
Cryptographic parsing is supplied by an explicitly configured verification-only
adapter and is never downgraded to signature-only or local acceptance.
"""

from __future__ import annotations

import base64
import hashlib
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Literal, Protocol

import yaml
from pydantic import Field, field_validator, model_validator

from .council import COUNCIL_SCHEMA_VERSION, CouncilReview, verify_council_content_hash
from .checkpoint import CHECKPOINT_SCHEMA, LedgerCheckpoint
from .errors import IntegrityError, ValidationError
from .hashing import hash_bytes
from .identity import (
    ClosedModel,
    FROZEN_IDM_IMPLEMENTATION,
    HashedRecord,
    IDMImplementationPin,
    PublicEvidenceReference,
    TrustInputSet,
    load_public_verification_inputs,
    read_record,
    seal_record,
    sha256_bytes,
    write_immutable_record,
)
from .ledger import (
    GENESIS_EVENT,
    exclusive_lock,
    read_events,
    record_event,
    verify as verify_ledger,
)
from .models import TaskPacket
from .providers import EGRESS_SCHEMA_VERSION, EgressPolicy, egress_policy_hash
from .synthesis import SYNTHESIS_SCHEMA_VERSION, SynthesisContinuationRecord
from .taskpacket import verify_content_hash
from .workspace import Workspace

SIGNING_REQUEST_SCHEMA = "evidence-signing-request/0.1.0"
SIGNED_PAYLOAD_PROFILE = "conclave-signed-evidence/0.1.0"
SIGNED_BINDING_SCHEMA = "signed-evidence-binding/0.1.0"
EVIDENCE_CONTEXT = "conclave-evidence/1.0"
EVIDENCE_SCOPE = "audit.sign"
MAX_ARTIFACT_BYTES = 4 * 1024 * 1024
MAX_ENVELOPE_BYTES = 1024 * 1024
REASON_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
WINDOWS_DEVICE_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def _timestamp(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError("timestamp must be valid second-precision UTC RFC 3339") from exc
    return value


def _dt(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def derive_evidence_id(envelope: bytes) -> str:
    digest = hashlib.sha256(envelope).digest()
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"evidence:sha256:{encoded}"


class ArtifactLink(ClosedModel):
    reference: str = Field(min_length=1, max_length=512)
    schema_version: str = Field(min_length=1, max_length=128)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class ExpiryPolicy(ClosedModel):
    expires_at_required: bool
    maximum_validity_seconds: int | None = Field(default=None, ge=1, le=31_536_000)

    @model_validator(mode="after")
    def coherent(self) -> "ExpiryPolicy":
        if self.expires_at_required and self.maximum_validity_seconds is None:
            raise ValueError("required expiry needs a maximum validity interval")
        return self


class ReplayDomain(ClosedModel):
    workspace_id: str = Field(pattern=r"^workspace:sha256:[0-9a-f]{64}$")
    bounded_domain: str = Field(min_length=1, max_length=512)


class ExecutionIdentity(ClosedModel):
    provider: str
    model: str
    transport: str
    adapter: str
    run_instance: str


class EvidenceSigningRequest(HashedRecord):
    profile: Literal["evidence-signing-request"] = "evidence-signing-request"
    schema_version: Literal["evidence-signing-request/0.1.0"] = SIGNING_REQUEST_SCHEMA
    artifact_reference: str
    artifact_storage_reference: str
    artifact_schema: str
    artifact_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    canonical_payload_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    provenance_chain: list[ArtifactLink]
    requested_context: Literal["conclave-evidence/1.0"] = EVIDENCE_CONTEXT
    attester_eid: str = Field(pattern=r"^eid:[a-z2-7]{26}$")
    attester_mid: str = Field(pattern=r"^mid:[a-z2-7]{26}$")
    attester_role: str = Field(min_length=1, max_length=128)
    attester_kid: str = Field(pattern=r"^kid:sha256:[A-Za-z0-9_-]{43}$")
    required_scope: Literal["audit.sign"] = EVIDENCE_SCOPE
    purpose: str = Field(min_length=1, max_length=512)
    expiry_policy: ExpiryPolicy
    replay_domain: ReplayDomain
    requester_actor_id: str = Field(min_length=1, max_length=256)
    requester_authority_level: Literal["human_principal", "advisory_agent", "system"]
    execution_identity: ExecutionIdentity | None = None
    authority_effect: Literal["none"] = "none"
    decision_effect: Literal["none"] = "none"
    membership_effect: Literal["none"] = "none"
    action_execution_allowed: Literal[False] = False

    @model_validator(mode="after")
    def has_chain(self) -> "EvidenceSigningRequest":
        if not self.provenance_chain:
            raise ValueError("provenance chain must not be empty")
        return self


class SignedEvidencePayload(ClosedModel):
    profile: Literal["conclave-signed-evidence/0.1.0"] = SIGNED_PAYLOAD_PROFILE
    artifact_reference: str
    artifact_schema: str
    artifact_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    canonical_payload_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    signing_request_reference: str
    signing_request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    workspace_id: str = Field(pattern=r"^workspace:sha256:[0-9a-f]{64}$")
    bounded_domain: str
    attester_eid: str = Field(pattern=r"^eid:[a-z2-7]{26}$")
    attester_mid: str = Field(pattern=r"^mid:[a-z2-7]{26}$")
    attester_role: str
    attester_kid: str = Field(pattern=r"^kid:sha256:[A-Za-z0-9_-]{43}$")
    asserted_scope: Literal["audit.sign"] = EVIDENCE_SCOPE
    issued_at: str
    expires_at: str | None = None
    authority_effect: Literal["none"] = "none"
    decision_effect: Literal["none"] = "none"
    membership_effect: Literal["none"] = "none"

    @field_validator("issued_at", "expires_at")
    @classmethod
    def valid_time(cls, value: str | None) -> str | None:
        return None if value is None else _timestamp(value)

    @model_validator(mode="after")
    def ordered_times(self) -> "SignedEvidencePayload":
        if self.expires_at is not None and self.expires_at < self.issued_at:
            raise ValueError("evidence expiry precedes issuance")
        return self


class EvidenceVerificationFindings(ClosedModel):
    attached_payload: bool
    canonical_cbor: bool
    context: bool
    trust: bool
    signature: bool
    delegation: bool
    role: bool
    scope: bool
    time: bool
    revocation: bool
    cross_binding: bool

    @classmethod
    def failed(cls) -> "EvidenceVerificationFindings":
        return cls(**{name: False for name in cls.model_fields})


class IDMEvidenceVerifierReport(ClosedModel):
    implementation: IDMImplementationPin
    evidence_id: str = Field(pattern=r"^evidence:sha256:[A-Za-z0-9_-]{43}$")
    context: str
    trust_domain_id: str = Field(pattern=r"^tdid:[a-z2-7]{26}$")
    signer_kid: str = Field(pattern=r"^kid:sha256:[A-Za-z0-9_-]{43}$")
    verified_roles: list[str]
    verified_scopes: list[str]
    payload: SignedEvidencePayload | None
    findings: EvidenceVerificationFindings
    reason_codes: list[str]

    @field_validator("verified_roles", "verified_scopes", "reason_codes")
    @classmethod
    def ordered(cls, value: list[str]) -> list[str]:
        if value != sorted(set(value)):
            raise ValueError("entries must be unique and sorted")
        return value

    @field_validator("reason_codes")
    @classmethod
    def reasons_are_stable(cls, value: list[str]) -> list[str]:
        if any(REASON_RE.fullmatch(item) is None for item in value):
            raise ValueError("reason codes must use stable uppercase syntax")
        return value


class SignedEvidenceBinding(HashedRecord):
    profile: Literal["signed-evidence-binding"] = "signed-evidence-binding"
    schema_version: Literal["signed-evidence-binding/0.1.0"] = SIGNED_BINDING_SCHEMA
    verification_status: Literal["PASS", "FAIL"]
    evidence_id: str = Field(pattern=r"^evidence:sha256:[A-Za-z0-9_-]{43}$")
    envelope_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    envelope_storage_reference: str
    signing_request_reference: str
    signing_request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    trust_input_reference: str
    trust_input_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    payload: SignedEvidencePayload | None
    findings: EvidenceVerificationFindings
    request_binding_verified: bool
    reason_codes: list[str]
    verifier_implementation: IDMImplementationPin
    conflict_observed_at_import: bool
    authority_effect: Literal["none"] = "none"
    decision_effect: Literal["none"] = "none"
    membership_effect: Literal["none"] = "none"
    action_execution_allowed: Literal[False] = False

    @field_validator("reason_codes")
    @classmethod
    def stable_reasons(cls, value: list[str]) -> list[str]:
        if value != sorted(set(value)) or any(REASON_RE.fullmatch(x) is None for x in value):
            raise ValueError("reason codes must be unique sorted stable codes")
        return value

    @model_validator(mode="after")
    def consistent(self) -> "SignedEvidenceBinding":
        if self.verification_status == "PASS" and (
            self.reason_codes or not all(self.findings.model_dump().values())
        ):
            raise ValueError("PASS requires all findings and no reasons")
        if self.verification_status == "FAIL" and not self.reason_codes:
            raise ValueError("FAIL requires a reason")
        return self


class IDMEvidenceVerifier(Protocol):
    def verify_evidence(
        self,
        *,
        envelope: bytes,
        expected_context: str,
        trust_bundle: bytes,
        revocation_evidence: tuple[bytes, ...],
        evaluation_time: str,
        required_role: str,
        required_scope: str,
    ) -> IDMEvidenceVerifierReport: ...


@dataclass(frozen=True)
class ResolvedArtifact:
    storage_reference: str
    reference: str
    schema: str
    content_hash: str
    payload_hash: str
    provenance_chain: tuple[ArtifactLink, ...]


@dataclass(frozen=True)
class EvidenceImportOutcome:
    binding: SignedEvidenceBinding
    binding_path: Path
    binding_created: bool
    envelope_path: Path
    envelope_created: bool
    conflict: bool


def verified_workspace_id(ws: Workspace) -> str:
    report = verify_ledger(ws)
    if not report.ok:
        raise ValidationError("19B requires an initialized, valid workspace ledger")
    events = read_events(ws)
    if not events or events[0].get("event_type") != GENESIS_EVENT:
        raise ValidationError("workspace ledger has no verified genesis")
    digest = events[0].get("entry_hash")
    if not isinstance(digest, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None:
        raise ValidationError("workspace genesis has no valid identity hash")
    return "workspace:" + digest


def _safe_relative_artifact(ws: Workspace, reference: str, allowed: Path) -> tuple[Path, bytes]:
    if "\\" in reference or ":" in reference or reference.startswith("/"):
        raise ValidationError("artifact storage reference is not canonical relative POSIX")
    pure = PurePosixPath(reference)
    if not reference or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValidationError("artifact storage reference contains traversal")
    if any(
        part.rstrip(" .") != part or part.split(".", 1)[0].upper() in WINDOWS_DEVICE_NAMES
        for part in pure.parts
    ):
        raise ValidationError("artifact storage reference is not portable")
    allowed_parts = allowed.relative_to(ws.root).parts
    if pure.parts[: len(allowed_parts)] != allowed_parts:
        raise ValidationError("artifact storage reference has a noncanonical case or area")
    candidate = ws.root.joinpath(*pure.parts)
    resolved_root = ws.root.resolve()
    resolved_allowed = allowed.resolve()
    resolved = candidate.resolve()
    if not resolved.is_relative_to(resolved_root) or not resolved.is_relative_to(resolved_allowed):
        raise ValidationError("artifact storage reference escapes its allowlisted area")
    current = ws.root
    for part in pure.parts:
        current = current / part
        try:
            attrs = getattr(current.lstat(), "st_file_attributes", 0)
        except OSError as exc:
            raise ValidationError("artifact is missing or unreadable") from exc
        if current.is_symlink() or attrs & 0x400:
            raise ValidationError("artifact path contains a symlink or reparse point")
    if not candidate.is_file():
        raise ValidationError("artifact is not a regular file")
    size = candidate.stat().st_size
    if size < 1 or size > MAX_ARTIFACT_BYTES:
        raise ValidationError("artifact size is outside the 19B limit")
    return candidate, candidate.read_bytes()


def _safe_stored_record(ws: Workspace, path: Path, allowed: Path, label: str) -> Path:
    path = Path(path)
    resolved_root = ws.root.resolve()
    resolved_allowed = allowed.resolve()
    resolved = path.resolve()
    if (
        not resolved_allowed.is_relative_to(resolved_root)
        or not resolved.is_relative_to(resolved_root)
        or resolved.parent != resolved_allowed
    ):
        raise ValidationError(f"{label} must be stored in this workspace")
    try:
        relative = path.absolute().relative_to(ws.root.absolute())
    except ValueError as exc:
        raise ValidationError(f"{label} must be stored in this workspace") from exc
    current = ws.root
    for part in relative.parts:
        current = current / part
        attrs = getattr(current.lstat(), "st_file_attributes", 0)
        if current.is_symlink() or attrs & 0x400:
            raise ValidationError(f"{label} path contains a symlink or reparse point")
    if not path.is_file():
        raise ValidationError(f"{label} is not a regular file")
    return path


def resolve_stored_artifact(
    ws: Workspace, *, storage_reference: str, artifact_schema: str
) -> ResolvedArtifact:
    if artifact_schema == EGRESS_SCHEMA_VERSION:
        _path, raw = _safe_relative_artifact(ws, storage_reference, ws.decisions_dir)
        try:
            policy = EgressPolicy.model_validate(yaml.safe_load(raw.decode("utf-8")))
        except Exception as exc:
            raise ValidationError("stored artifact failed its native closed schema") from exc
        if policy.schema_version != EGRESS_SCHEMA_VERSION:
            raise ValidationError("stored egress decision schema is unsupported")
        content_hash = egress_policy_hash(policy)
        return ResolvedArtifact(
            storage_reference=storage_reference,
            reference=policy.decision_ref,
            schema=artifact_schema,
            content_hash=content_hash,
            payload_hash=hash_bytes(raw),
            provenance_chain=(ArtifactLink(
                reference=policy.decision_ref,
                schema_version=artifact_schema,
                content_hash=content_hash,
            ),),
        )
    if artifact_schema == CHECKPOINT_SCHEMA:
        _path, raw = _safe_relative_artifact(ws, storage_reference, ws.ledger_dir)
        try:
            checkpoint = LedgerCheckpoint.model_validate_json(raw)
        except Exception as exc:
            raise ValidationError("stored checkpoint failed its native closed schema") from exc
        return ResolvedArtifact(
            storage_reference=storage_reference,
            reference=checkpoint.content_hash,
            schema=artifact_schema,
            content_hash=checkpoint.content_hash,
            payload_hash=hash_bytes(raw),
            provenance_chain=(ArtifactLink(
                reference=checkpoint.content_hash,
                schema_version=artifact_schema,
                content_hash=checkpoint.content_hash,
            ),),
        )
    loaders = {
        "task-packet/0.1.0": (ws.tasks_dir, TaskPacket, verify_content_hash, "task"),
        COUNCIL_SCHEMA_VERSION: (
            ws.council_dir,
            CouncilReview,
            verify_council_content_hash,
            "council",
        ),
        SYNTHESIS_SCHEMA_VERSION: (
            ws.synthesis_dir,
            SynthesisContinuationRecord,
            lambda _record: True,
            "synthesis",
        ),
    }
    if artifact_schema not in loaders:
        raise ValidationError("artifact schema is not recognized for 19B evidence")
    allowed, model, verifier, kind = loaders[artifact_schema]
    _path, raw = _safe_relative_artifact(ws, storage_reference, allowed)
    try:
        value = yaml.safe_load(raw.decode("utf-8"))
        record = model.model_validate(value)
    except Exception as exc:
        raise ValidationError("stored artifact failed its native closed schema") from exc
    if record.schema_version != artifact_schema or not verifier(record):
        raise ValidationError("stored artifact schema or content hash does not verify")
    if kind == "task":
        reference = record.ref
        chain = (ArtifactLink(reference=record.ref, schema_version=artifact_schema,
                              content_hash=record.content_hash),)
    elif kind == "council":
        reference = record.council_review_id
        chain = (
            ArtifactLink(reference=record.task_packet_ref, schema_version="task-packet/0.1.0",
                         content_hash=record.task_packet_hash),
            ArtifactLink(reference=reference, schema_version=artifact_schema,
                         content_hash=record.content_hash),
        )
    else:
        reference = record.continuation_id
        chain = (
            ArtifactLink(reference=record.packet_ref, schema_version="task-packet/0.1.0",
                         content_hash=record.task_packet_hash),
            ArtifactLink(reference=record.council_review_id,
                         schema_version=COUNCIL_SCHEMA_VERSION,
                         content_hash=record.council_review_hash),
            ArtifactLink(reference=reference, schema_version=artifact_schema,
                         content_hash=record.content_hash),
        )
    return ResolvedArtifact(
        storage_reference=storage_reference,
        reference=reference,
        schema=artifact_schema,
        content_hash=record.content_hash,
        payload_hash=hash_bytes(raw),
        provenance_chain=chain,
    )


def prepare_signing_request(
    ws: Workspace,
    *,
    storage_reference: str,
    artifact_schema: str,
    attester_eid: str,
    attester_mid: str,
    attester_role: str,
    attester_kid: str,
    purpose: str,
    expiry_policy: ExpiryPolicy,
    requester_actor_id: str,
    requester_authority_level: Literal["human_principal", "advisory_agent", "system"],
    execution_identity: ExecutionIdentity | None = None,
) -> tuple[EvidenceSigningRequest, Path, bool]:
    workspace_id = verified_workspace_id(ws)
    artifact = resolve_stored_artifact(
        ws, storage_reference=storage_reference, artifact_schema=artifact_schema
    )
    config = ws.load_config()
    if requester_authority_level == "human_principal" and requester_actor_id != config.get("principal"):
        raise ValidationError("requester is not the configured human principal")
    if requester_authority_level == "system" and requester_actor_id != "conclave":
        raise ValidationError("system signing requests must be proposed by conclave")
    if requester_authority_level == "advisory_agent":
        provider = (config.get("providers") or {}).get(requester_actor_id)
        if not provider or provider.get("authority_level") != "advisory":
            raise ValidationError("advisory requester is not configured as advisory")
    data = {
        "profile": "evidence-signing-request",
        "schema_version": SIGNING_REQUEST_SCHEMA,
        "artifact_reference": artifact.reference,
        "artifact_storage_reference": artifact.storage_reference,
        "artifact_schema": artifact.schema,
        "artifact_content_hash": artifact.content_hash,
        "canonical_payload_hash": artifact.payload_hash,
        "provenance_chain": list(artifact.provenance_chain),
        "requested_context": EVIDENCE_CONTEXT,
        "attester_eid": attester_eid,
        "attester_mid": attester_mid,
        "attester_role": attester_role,
        "attester_kid": attester_kid,
        "required_scope": EVIDENCE_SCOPE,
        "purpose": purpose,
        "expiry_policy": expiry_policy,
        "replay_domain": ReplayDomain(
            workspace_id=workspace_id,
            bounded_domain=artifact.provenance_chain[0].reference,
        ),
        "requester_actor_id": requester_actor_id,
        "requester_authority_level": requester_authority_level,
        "execution_identity": execution_identity,
        "authority_effect": "none",
        "decision_effect": "none",
        "membership_effect": "none",
        "action_execution_allowed": False,
    }
    request = seal_record(EvidenceSigningRequest, data)
    name = request.content_hash.split(":", 1)[1] + ".json"
    path, created = write_immutable_record(ws.signing_requests_dir / name, request)
    record_event(
        ws,
        event_type="evidence_signing_request_recorded",
        actor="conclave",
        authority_level="system",
        subject_refs=[request.artifact_reference],
        artifact_hashes={"evidence_signing_request": request.content_hash},
        payload={
            "request_file": path.relative_to(ws.root).as_posix(),
            "authority_effect": "none",
            "action_execution_allowed": False,
        },
    )
    return request, path, created


def _write_binary_once(path: Path, payload: bytes) -> tuple[Path, bool]:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        return path, True
    except FileExistsError:
        if path.read_bytes() != payload:
            raise IntegrityError("content-addressed envelope path contains different bytes")
        return path, False


def _request_binding_matches(
    payload: SignedEvidencePayload | None,
    request: EvidenceSigningRequest,
    request_reference: str,
) -> bool:
    return payload is not None and all(
        (
            payload.signing_request_reference == request_reference,
            payload.signing_request_hash == request.content_hash,
            payload.artifact_reference == request.artifact_reference,
            payload.artifact_schema == request.artifact_schema,
            payload.artifact_content_hash == request.artifact_content_hash,
            payload.canonical_payload_hash == request.canonical_payload_hash,
            payload.workspace_id == request.replay_domain.workspace_id,
            payload.bounded_domain == request.replay_domain.bounded_domain,
            payload.attester_eid == request.attester_eid,
            payload.attester_mid == request.attester_mid,
            payload.attester_role == request.attester_role,
            payload.attester_kid == request.attester_kid,
            payload.asserted_scope == request.required_scope,
        )
    )


def read_signed_binding(path: Path) -> SignedEvidenceBinding:
    return read_record(path, SignedEvidenceBinding)


def bindings_for_request(ws: Workspace, request_hash: str) -> list[SignedEvidenceBinding]:
    bindings = []
    for path in sorted(ws.signing_bindings_dir.glob("*.json")):
        value = read_signed_binding(path)
        if value.signing_request_hash == request_hash and value.request_binding_verified:
            bindings.append(value)
    return bindings


def import_evidence_envelope(
    ws: Workspace,
    *,
    request_path: Path,
    trust_input_path: Path,
    envelope: bytes,
    public_evidence: dict[str, bytes],
    verifier: IDMEvidenceVerifier,
) -> EvidenceImportOutcome:
    if not envelope or len(envelope) > MAX_ENVELOPE_BYTES:
        raise ValidationError("evidence envelope size is outside the 19B limit")
    verified_workspace_id(ws)
    request_path = _safe_stored_record(
        ws, Path(request_path), ws.signing_requests_dir, "signing request"
    )
    request = read_record(request_path, EvidenceSigningRequest)
    request_reference = request_path.relative_to(ws.root).as_posix()
    trust_input_path = _safe_stored_record(
        ws, Path(trust_input_path), ws.identity_trust_inputs_dir, "trust input set"
    )
    trust_inputs = read_record(trust_input_path, TrustInputSet)
    trust_input_reference = trust_input_path.relative_to(ws.root).as_posix()
    artifact = resolve_stored_artifact(
        ws,
        storage_reference=request.artifact_storage_reference,
        artifact_schema=request.artifact_schema,
    )
    reasons: list[str] = []
    if artifact.reference != request.artifact_reference or artifact.content_hash != request.artifact_content_hash:
        reasons.append("ARTIFACT_BINDING_MISMATCH")
    if artifact.payload_hash != request.canonical_payload_hash:
        reasons.append("CANONICAL_PAYLOAD_HASH_MISMATCH")
    if list(artifact.provenance_chain) != request.provenance_chain:
        reasons.append("PROVENANCE_CHAIN_MISMATCH")
    if request.replay_domain.workspace_id != verified_workspace_id(ws):
        reasons.append("WORKSPACE_REPLAY_MISMATCH")
    if request.replay_domain.bounded_domain != artifact.provenance_chain[0].reference:
        reasons.append("BOUNDED_DOMAIN_MISMATCH")
    if not trust_inputs.idm_implementation.is_frozen_baseline():
        reasons.append("IDM_BASELINE_MISMATCH")
    if request.attester_role not in trust_inputs.accepted_roles:
        reasons.append("ROLE_POLICY_MISMATCH")
    if EVIDENCE_SCOPE not in trust_inputs.required_scopes:
        reasons.append("SCOPE_POLICY_MISMATCH")
    trust_bytes, revocations, input_reasons = load_public_verification_inputs(
        trust_inputs, public_evidence
    )
    reasons.extend(input_reasons)

    report: IDMEvidenceVerifierReport | None = None
    if not reasons and trust_bytes is not None:
        try:
            report = verifier.verify_evidence(
                envelope=envelope,
                expected_context=EVIDENCE_CONTEXT,
                trust_bundle=trust_bytes,
                revocation_evidence=revocations,
                evaluation_time=trust_inputs.evaluation_time,
                required_role=request.attester_role,
                required_scope=EVIDENCE_SCOPE,
            )
        except Exception:
            reasons.append("IDM_EVIDENCE_VERIFIER_ERROR")

    findings = report.findings if report else EvidenceVerificationFindings.failed()
    payload = report.payload if report else None
    expected_evidence_id = derive_evidence_id(envelope)
    request_binding_verified = _request_binding_matches(payload, request, request_reference)
    if report:
        if not report.implementation.is_frozen_baseline():
            reasons.append("IDM_VERIFIER_BASELINE_MISMATCH")
        if report.evidence_id != expected_evidence_id:
            reasons.append("EVIDENCE_ID_MISMATCH")
        if report.context != EVIDENCE_CONTEXT:
            reasons.append("CONTEXT_MISMATCH")
        if report.trust_domain_id != trust_inputs.trust_domain_id:
            reasons.append("TRUST_DOMAIN_MISMATCH")
        if report.signer_kid != request.attester_kid:
            reasons.append("KID_MISMATCH")
        if request.attester_role not in report.verified_roles:
            reasons.append("ROLE_MISSING")
        if EVIDENCE_SCOPE not in report.verified_scopes:
            reasons.append("SCOPE_MISSING")
        if not request_binding_verified:
            reasons.append("REQUEST_CROSS_BINDING_MISMATCH")
        reasons.extend(report.reason_codes)
        finding_codes = {
            "attached_payload": "DETACHED_PAYLOAD",
            "canonical_cbor": "NONCANONICAL_CBOR",
            "context": "CONTEXT_INVALID",
            "trust": "TRUST_INVALID",
            "signature": "SIGNATURE_INVALID",
            "delegation": "DELEGATION_INVALID",
            "role": "ROLE_INVALID",
            "scope": "SCOPE_INVALID",
            "time": "TIME_INVALID",
            "revocation": "REVOCATION_INVALID",
            "cross_binding": "CROSS_BINDING_INVALID",
        }
        reasons.extend(code for name, code in finding_codes.items() if not getattr(findings, name))
        if payload:
            if payload.issued_at > trust_inputs.evaluation_time:
                reasons.append("FUTURE_EVIDENCE")
            if payload.expires_at is not None and payload.expires_at < trust_inputs.evaluation_time:
                reasons.append("EXPIRED_EVIDENCE")
            policy = request.expiry_policy
            if policy.expires_at_required and payload.expires_at is None:
                reasons.append("REQUIRED_EXPIRY_MISSING")
            if payload.expires_at and policy.maximum_validity_seconds is not None:
                if (_dt(payload.expires_at) - _dt(payload.issued_at)).total_seconds() > policy.maximum_validity_seconds:
                    reasons.append("EXPIRY_POLICY_EXCEEDED")

    envelope_hash = sha256_bytes(envelope)
    digest = envelope_hash.split(":", 1)[1]
    binding_digest = hashlib.sha256(
        (request.content_hash + "\0" + envelope_hash + "\0" + trust_inputs.content_hash).encode(
            "ascii"
        )
    ).hexdigest()
    lock_base = ws.signing_bindings_dir / (request.content_hash.split(":", 1)[1] + ".import")
    with exclusive_lock(lock_base):
        envelope_path, envelope_created = _write_binary_once(
            ws.signing_envelopes_dir / f"{digest}.cose", envelope
        )
        prior = bindings_for_request(ws, request.content_hash)
        conflict = request_binding_verified and any(
            item.envelope_hash != envelope_hash for item in prior
        )
        ordered = sorted(set(reasons))
        binding_path = ws.signing_bindings_dir / f"{binding_digest}.json"
        binding_data = {
                "profile": "signed-evidence-binding",
                "schema_version": SIGNED_BINDING_SCHEMA,
                "verification_status": "PASS" if not ordered else "FAIL",
                "evidence_id": expected_evidence_id,
                "envelope_hash": envelope_hash,
                "envelope_storage_reference": envelope_path.relative_to(ws.root).as_posix(),
                "signing_request_reference": request_reference,
                "signing_request_hash": request.content_hash,
                "trust_input_reference": trust_input_reference,
                "trust_input_hash": trust_inputs.content_hash,
                "payload": payload,
                "findings": findings,
                "request_binding_verified": request_binding_verified,
                "reason_codes": ordered,
                "verifier_implementation": report.implementation if report else FROZEN_IDM_IMPLEMENTATION,
                "conflict_observed_at_import": conflict,
                "authority_effect": "none",
                "decision_effect": "none",
                "membership_effect": "none",
                "action_execution_allowed": False,
            }
        if binding_path.exists():
            binding = read_signed_binding(binding_path)
            binding_created = False
        else:
            binding = seal_record(SignedEvidenceBinding, binding_data)
            binding_path, binding_created = write_immutable_record(binding_path, binding)

    neutral = {"authority_effect": "none", "action_execution_allowed": False}
    record_event(
        ws,
        event_type="evidence_envelope_preserved",
        actor="conclave", authority_level="system",
        subject_refs=[request.artifact_reference],
        artifact_hashes={"evidence_envelope": envelope_hash},
        payload={"envelope_file": envelope_path.relative_to(ws.root).as_posix(), **neutral},
    )
    record_event(
        ws,
        event_type="signed_evidence_binding_recorded",
        actor="conclave", authority_level="system",
        subject_refs=[request.artifact_reference],
        artifact_hashes={"signed_evidence_binding": binding.content_hash,
                         "evidence_envelope": envelope_hash,
                         "evidence_signing_request": request.content_hash},
        payload={"binding_file": binding_path.relative_to(ws.root).as_posix(), **neutral},
    )
    if conflict:
        related = sorted({envelope_hash, *(item.envelope_hash for item in prior)})
        record_event(
            ws,
            event_type="evidence_conflict_observed",
            actor="conclave", authority_level="system",
            subject_refs=[request.artifact_reference],
            artifact_hashes={"evidence_signing_request": request.content_hash},
            payload={"envelope_hashes": related, "reliance": "blocked", **neutral},
        )
    return EvidenceImportOutcome(
        binding=binding, binding_path=binding_path, binding_created=binding_created,
        envelope_path=envelope_path, envelope_created=envelope_created, conflict=conflict,
    )


def evidence_reliance_state(ws: Workspace, request_hash: str) -> str:
    values = bindings_for_request(ws, request_hash)
    hashes = {item.envelope_hash for item in values}
    if len(hashes) > 1:
        return "BLOCKED_CONFLICT"
    if len(values) == 1 and values[0].verification_status == "PASS":
        return "VERIFIED_NOT_GATED"
    return "NOT_RELIABLE"
