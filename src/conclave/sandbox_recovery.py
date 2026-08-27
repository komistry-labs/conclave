"""Increment 20C explicit sandbox operator recovery and one-replay boundary."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .configuration import (
    _digest_filename,
    _read_content_addressed,
    _safe_record_path,
    read_broker_profile,
    read_verifier_profile,
)
from .errors import IntegrityError, ValidationError
from .evidence import EvidenceImportOutcome, IDMEvidenceVerifier, import_evidence_envelope, verified_workspace_id
from .identity import HashedRecord, seal_record, sha256_bytes, write_immutable_record
from .ledger import exclusive_lock, read_events, record_event
from .sandbox_transport import (
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_BYTES,
    REASON,
    RESPONSE_MEDIA_TYPE,
    BrokerEgressAuthorization,
    CredentialResolver,
    SandboxBrokerAttempt,
    SandboxBrokerTransport,
    SandboxBrokerTransportReceipt,
    SandboxTransportFailure,
    _artifact_bytes,
    _dt,
    _read_request,
    _read_trust,
    _reference,
    _timestamp,
    _validate_credential,
    _wire_body,
    read_broker_authorization,
    read_sandbox_attempt,
    read_sandbox_endpoint,
    read_sandbox_receipt,
)
from .workspace import Workspace, utcnow

RECOVERY_AUTHORIZATION_SCHEMA = "broker-recovery-authorization/0.1.0"
RECOVERY_ATTEMPT_SCHEMA = "sandbox-broker-recovery-attempt/0.1.0"
RECOVERY_DISPOSITION_SCHEMA = "broker-recovery-disposition/0.1.0"


def _stable_reasons(value: list[str]) -> list[str]:
    if value != sorted(set(value)) or any(REASON.fullmatch(item) is None for item in value):
        raise ValueError("reason codes must be unique sorted stable codes")
    return value


class BrokerRecoveryAuthorization(HashedRecord):
    profile: Literal["broker-recovery-authorization"] = "broker-recovery-authorization"
    schema_version: Literal["broker-recovery-authorization/0.1.0"] = RECOVERY_AUTHORIZATION_SCHEMA
    workspace_id: str = Field(min_length=1, max_length=256)
    authorized_principal: str = Field(min_length=1, max_length=256)
    original_endpoint_reference: str
    original_endpoint_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    original_broker_profile_reference: str
    original_broker_profile_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    original_verifier_profile_reference: str
    original_verifier_profile_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    original_trust_input_reference: str
    original_trust_input_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    original_signing_request_reference: str
    original_signing_request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    original_artifact_storage_reference: str
    original_artifact_schema: str
    original_artifact_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    original_canonical_payload_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    original_authorization_reference: str
    original_authorization_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    original_attempt_reference: str
    original_attempt_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    original_attempt_id: str = Field(pattern=r"^attempt:sha256:[0-9a-f]{64}$")
    original_receipt_reference: str | None = None
    original_receipt_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    original_outcome: Literal["MISSING_RECEIPT", "SENT_NO_RESPONSE"]
    original_request_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    original_request_body_bytes: int = Field(ge=1, le=MAX_REQUEST_BYTES)
    original_idempotency_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    original_idempotency_key_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    idempotency_algorithm: Literal["conclave-20b-attempt-digest-v1"] = "conclave-20b-attempt-digest-v1"
    action: Literal["ABANDON", "IDEMPOTENT_REPLAY"]
    purpose: str = Field(min_length=1, max_length=512)
    principal_confirmed_ambiguous_outcome: Literal[True] = True
    principal_reviewed_artifact_for_secrets: Literal[True] = True
    principal_acknowledged_replay_consequence: Literal[True] = True
    issued_at: str
    expires_at: str
    maximum_replays: Literal[0, 1]
    environment: Literal["sandbox"] = "sandbox"
    production_use_allowed: Literal[False] = False
    authority_effect: Literal["broker_recovery_only"] = "broker_recovery_only"
    decision_effect: Literal["none"] = "none"
    membership_effect: Literal["none"] = "none"
    action_execution_allowed: Literal[False] = False

    _issued = field_validator("issued_at")(_timestamp)
    _expires = field_validator("expires_at")(_timestamp)

    @model_validator(mode="after")
    def coherent(self) -> "BrokerRecoveryAuthorization":
        if _dt(self.expires_at) <= _dt(self.issued_at):
            raise ValueError("recovery authorization expiry must follow issuance")
        expected = 0 if self.action == "ABANDON" else 1
        if self.maximum_replays != expected:
            raise ValueError("maximum_replays does not match recovery action")
        if (self.original_receipt_reference is None) != (self.original_receipt_hash is None):
            raise ValueError("receipt reference and hash must both be present or absent")
        if self.original_outcome == "MISSING_RECEIPT" and self.original_receipt_reference is not None:
            raise ValueError("missing-receipt outcome cannot bind a receipt")
        if self.original_outcome == "SENT_NO_RESPONSE" and self.original_receipt_reference is None:
            raise ValueError("sent-no-response outcome must bind a receipt")
        return self


class SandboxBrokerRecoveryAttempt(HashedRecord):
    profile: Literal["sandbox-broker-recovery-attempt"] = "sandbox-broker-recovery-attempt"
    schema_version: Literal["sandbox-broker-recovery-attempt/0.1.0"] = RECOVERY_ATTEMPT_SCHEMA
    recovery_attempt_id: str = Field(pattern=r"^recovery:sha256:[0-9a-f]{64}$")
    recovery_authorization_reference: str
    recovery_authorization_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    original_attempt_reference: str
    original_attempt_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    original_attempt_id: str = Field(pattern=r"^attempt:sha256:[0-9a-f]{64}$")
    endpoint_reference: str
    endpoint_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    signing_request_reference: str
    signing_request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    request_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    request_body_bytes: int = Field(ge=1, le=MAX_REQUEST_BYTES)
    idempotency_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: str
    time_source_classification: Literal["diagnostic-local"] = "diagnostic-local"
    state: Literal["PREPARED"] = "PREPARED"
    maximum_transmissions: Literal[1] = 1
    authority_effect: Literal["none"] = "none"
    decision_effect: Literal["none"] = "none"
    membership_effect: Literal["none"] = "none"
    action_execution_allowed: Literal[False] = False

    _created = field_validator("created_at")(_timestamp)


class BrokerRecoveryDisposition(HashedRecord):
    profile: Literal["broker-recovery-disposition"] = "broker-recovery-disposition"
    schema_version: Literal["broker-recovery-disposition/0.1.0"] = RECOVERY_DISPOSITION_SCHEMA
    recovery_authorization_reference: str
    recovery_authorization_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    original_attempt_reference: str
    original_attempt_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    original_attempt_id: str = Field(pattern=r"^attempt:sha256:[0-9a-f]{64}$")
    original_receipt_reference: str | None = None
    original_receipt_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    action: Literal["ABANDON", "IDEMPOTENT_REPLAY"]
    recovery_attempt_reference: str | None = None
    recovery_attempt_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    outcome: Literal[
        "ABANDONED_WITHOUT_TRANSMISSION", "REPLAY_NOT_SENT",
        "REPLAY_SENT_NO_RESPONSE", "REPLAY_RESPONSE_REJECTED",
        "REPLAY_RESPONSE_ACCEPTED_FOR_VERIFICATION",
    ]
    reason_codes: list[str]
    request_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    request_body_bytes: int = Field(ge=1, le=MAX_REQUEST_BYTES)
    response_body_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    response_body_bytes: int | None = Field(default=None, ge=0, le=MAX_RESPONSE_BYTES + 1)
    http_status_class: Literal["none", "1xx", "2xx", "3xx", "4xx", "5xx"]
    envelope_storage_reference: str | None = None
    envelope_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    evidence_binding_reference: str | None = None
    evidence_binding_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    verification_status: Literal["NOT_RUN", "PASS", "FAIL"]
    credential_reference: str
    started_at: str
    finished_at: str
    time_source_classification: Literal["diagnostic-local"] = "diagnostic-local"
    authority_effect: Literal["none"] = "none"
    decision_effect: Literal["none"] = "none"
    membership_effect: Literal["none"] = "none"
    action_execution_allowed: Literal[False] = False

    _started = field_validator("started_at")(_timestamp)
    _finished = field_validator("finished_at")(_timestamp)
    _reasons = field_validator("reason_codes")(_stable_reasons)

    @model_validator(mode="after")
    def coherent(self) -> "BrokerRecoveryDisposition":
        paired_attempt = self.recovery_attempt_reference is not None and self.recovery_attempt_hash is not None
        if (self.recovery_attempt_reference is None) != (self.recovery_attempt_hash is None):
            raise ValueError("recovery attempt reference and hash must be paired")
        if self.action == "ABANDON" and (paired_attempt or self.outcome != "ABANDONED_WITHOUT_TRANSMISSION"):
            raise ValueError("abandonment cannot bind a replay attempt")
        if self.action == "IDEMPOTENT_REPLAY" and not paired_attempt:
            raise ValueError("replay disposition requires its durable attempt")
        return self


@dataclass(frozen=True)
class RecoveryExecutionOutcome:
    authorization: BrokerRecoveryAuthorization
    recovery_attempt: SandboxBrokerRecoveryAttempt | None
    recovery_attempt_path: Path | None
    disposition: BrokerRecoveryDisposition
    disposition_path: Path
    evidence: EvidenceImportOutcome | None


def _safe(path_ref: str, ws: Workspace, area: Path, parts: tuple[str, ...]) -> Path:
    return _safe_record_path(ws, path_ref, area, parts)


def read_recovery_authorization(ws: Workspace, reference: str) -> BrokerRecoveryAuthorization:
    path = _safe(reference, ws, ws.signing_broker_recovery_authorizations_dir,
                 ("signing", "broker-recovery-authorizations"))
    return _read_content_addressed(path, BrokerRecoveryAuthorization, "recovery-authorization")  # type: ignore[return-value]


def read_recovery_attempt(path: Path) -> SandboxBrokerRecoveryAttempt:
    return _read_content_addressed(path, SandboxBrokerRecoveryAttempt, "recovery-attempt")  # type: ignore[return-value]


def read_recovery_disposition(path: Path) -> BrokerRecoveryDisposition:
    return _read_content_addressed(path, BrokerRecoveryDisposition, "recovery-disposition")  # type: ignore[return-value]


def _load_original(ws: Workspace, attempt_reference: str) -> tuple[
    SandboxBrokerAttempt, Path, BrokerEgressAuthorization, object, object, Path, bytes
]:
    attempt_path = _safe(attempt_reference, ws, ws.signing_broker_attempts_dir,
                         ("signing", "broker-attempts"))
    attempt = read_sandbox_attempt(attempt_path)
    authorization = read_broker_authorization(ws, attempt.authorization_reference)
    endpoint = read_sandbox_endpoint(ws, attempt.endpoint_reference)
    broker = read_broker_profile(ws, attempt.broker_profile_reference)
    verifier_profile = read_verifier_profile(ws, attempt.verifier_profile_reference)
    request, request_path = _read_request(ws, attempt.signing_request_reference)
    trust, _ = _read_trust(ws, attempt.trust_input_reference)
    body = _wire_body(request, _artifact_bytes(ws, request))
    checks = (
        attempt.endpoint_hash == endpoint.content_hash,
        endpoint.broker_profile_reference == attempt.broker_profile_reference,
        endpoint.broker_profile_hash == broker.content_hash,
        attempt.broker_profile_hash == broker.content_hash,
        broker.verifier_profile_reference == attempt.verifier_profile_reference,
        broker.verifier_profile_hash == verifier_profile.content_hash,
        attempt.verifier_profile_hash == verifier_profile.content_hash,
        attempt.authorization_hash == authorization.content_hash,
        attempt.signing_request_hash == request.content_hash,
        attempt.trust_input_hash == trust.content_hash,
        attempt.request_body_hash == sha256_bytes(body),
        attempt.request_body_bytes == len(body),
        attempt.artifact_storage_reference == request.artifact_storage_reference,
        attempt.artifact_schema == request.artifact_schema,
        attempt.artifact_content_hash == request.artifact_content_hash,
        attempt.canonical_payload_hash == request.canonical_payload_hash,
        authorization.endpoint_reference == attempt.endpoint_reference,
        authorization.endpoint_hash == endpoint.content_hash,
        authorization.verifier_profile_reference == attempt.verifier_profile_reference,
        authorization.verifier_profile_hash == verifier_profile.content_hash,
        authorization.signing_request_reference == attempt.signing_request_reference,
        authorization.signing_request_hash == request.content_hash,
        authorization.trust_input_reference == attempt.trust_input_reference,
        authorization.trust_input_hash == trust.content_hash,
    )
    if not all(checks):
        raise IntegrityError("RECOVERY_ORIGINAL_BINDING_INVALID")
    return attempt, attempt_path, authorization, endpoint, request, request_path, body


def _receipts_for_attempt(ws: Workspace, attempt: SandboxBrokerAttempt) -> list[tuple[SandboxBrokerTransportReceipt, Path]]:
    matches: list[tuple[SandboxBrokerTransportReceipt, Path]] = []
    for path in sorted(ws.signing_broker_receipts_dir.glob("*.json")):
        try:
            receipt = read_sandbox_receipt(path)
        except Exception as exc:
            raise ValidationError("RECOVERY_RECEIPT_STORE_INVALID") from exc
        if receipt.attempt_id == attempt.attempt_id:
            if not all((
                receipt.attempt_hash == attempt.content_hash,
                receipt.attempt_reference.endswith(
                    "/" + _digest_filename("attempt", attempt)
                ),
                receipt.endpoint_reference == attempt.endpoint_reference,
                receipt.endpoint_hash == attempt.endpoint_hash,
                receipt.authorization_reference == attempt.authorization_reference,
                receipt.authorization_hash == attempt.authorization_hash,
                receipt.signing_request_reference == attempt.signing_request_reference,
                receipt.signing_request_hash == attempt.signing_request_hash,
                receipt.request_body_hash == attempt.request_body_hash,
                receipt.request_body_bytes == attempt.request_body_bytes,
            )):
                raise IntegrityError("RECOVERY_RECEIPT_BINDING_INVALID")
            matches.append((receipt, path))
    if len(matches) > 1:
        raise IntegrityError("RECOVERY_RECEIPT_CONFLICT")
    return matches


def _ledger_records_hash(ws: Workspace, event_types: set[str], artifact_hash: str) -> bool:
    return any(
        event.get("event_type") in event_types
        and artifact_hash in (event.get("artifact_hashes") or {}).values()
        for event in read_events(ws)
    )


def create_recovery_authorization(
    ws: Workspace, *, original_attempt_reference: str,
    original_receipt_reference: str | None, action: str, purpose: str,
    confirmed_principal: str, principal_confirmed_ambiguous_outcome: bool,
    principal_reviewed_artifact_for_secrets: bool,
    principal_acknowledged_replay_consequence: bool,
    issued_at: str, expires_at: str,
) -> tuple[BrokerRecoveryAuthorization, Path, bool]:
    workspace_id = verified_workspace_id(ws)
    principal = ws.load_config().get("principal")
    if not principal or confirmed_principal != principal:
        raise ValidationError("RECOVERY_PRINCIPAL_MISMATCH")
    if not all((principal_confirmed_ambiguous_outcome,
                principal_reviewed_artifact_for_secrets,
                principal_acknowledged_replay_consequence)):
        raise ValidationError("RECOVERY_CONFIRMATION_REQUIRED")
    if action not in {"ABANDON", "IDEMPOTENT_REPLAY"}:
        raise ValidationError("RECOVERY_ACTION_INVALID")
    attempt, attempt_path, original_auth, endpoint, _request, _request_path, body = _load_original(
        ws, original_attempt_reference
    )
    matches = _receipts_for_attempt(ws, attempt)
    receipt: SandboxBrokerTransportReceipt | None = None
    receipt_path: Path | None = None
    if original_receipt_reference is None:
        if matches:
            raise ValidationError("RECOVERY_RECEIPT_REFERENCE_REQUIRED")
        if _ledger_records_hash(
            ws, {"sandbox_broker_transport_attempt_recorded"}, attempt.content_hash
        ):
            raise ValidationError("RECOVERY_RECORDED_RECEIPT_MISSING")
    else:
        candidate = _safe(original_receipt_reference, ws, ws.signing_broker_receipts_dir,
                          ("signing", "broker-receipts"))
        if not matches or matches[0][1].resolve() != candidate.resolve():
            raise ValidationError("RECOVERY_RECEIPT_REFERENCE_MISMATCH")
        receipt, receipt_path = matches[0]
        if receipt.outcome != "SENT_NO_RESPONSE":
            raise ValidationError("RECOVERY_ORIGINAL_OUTCOME_INELIGIBLE")
    idempotency_key = attempt.attempt_id.rsplit(":", 1)[1]
    data = {
        "profile": "broker-recovery-authorization", "schema_version": RECOVERY_AUTHORIZATION_SCHEMA,
        "workspace_id": workspace_id, "authorized_principal": principal,
        "original_endpoint_reference": attempt.endpoint_reference,
        "original_endpoint_hash": attempt.endpoint_hash,
        "original_broker_profile_reference": attempt.broker_profile_reference,
        "original_broker_profile_hash": attempt.broker_profile_hash,
        "original_verifier_profile_reference": attempt.verifier_profile_reference,
        "original_verifier_profile_hash": attempt.verifier_profile_hash,
        "original_trust_input_reference": attempt.trust_input_reference,
        "original_trust_input_hash": attempt.trust_input_hash,
        "original_signing_request_reference": attempt.signing_request_reference,
        "original_signing_request_hash": attempt.signing_request_hash,
        "original_artifact_storage_reference": attempt.artifact_storage_reference,
        "original_artifact_schema": attempt.artifact_schema,
        "original_artifact_content_hash": attempt.artifact_content_hash,
        "original_canonical_payload_hash": attempt.canonical_payload_hash,
        "original_authorization_reference": attempt.authorization_reference,
        "original_authorization_hash": original_auth.content_hash,
        "original_attempt_reference": _reference(ws, attempt_path),
        "original_attempt_hash": attempt.content_hash, "original_attempt_id": attempt.attempt_id,
        "original_receipt_reference": _reference(ws, receipt_path) if receipt_path else None,
        "original_receipt_hash": receipt.content_hash if receipt else None,
        "original_outcome": "SENT_NO_RESPONSE" if receipt else "MISSING_RECEIPT",
        "original_request_body_hash": sha256_bytes(body), "original_request_body_bytes": len(body),
        "original_idempotency_key": idempotency_key,
        "original_idempotency_key_hash": sha256_bytes(idempotency_key.encode("ascii")),
        "idempotency_algorithm": "conclave-20b-attempt-digest-v1",
        "action": action, "purpose": purpose,
        "principal_confirmed_ambiguous_outcome": True,
        "principal_reviewed_artifact_for_secrets": True,
        "principal_acknowledged_replay_consequence": True,
        "issued_at": issued_at, "expires_at": expires_at,
        "maximum_replays": 0 if action == "ABANDON" else 1,
        "environment": "sandbox", "production_use_allowed": False,
        "authority_effect": "broker_recovery_only", "decision_effect": "none",
        "membership_effect": "none", "action_execution_allowed": False,
    }
    record = seal_record(BrokerRecoveryAuthorization, data)
    return record, *write_immutable_record(
        ws.signing_broker_recovery_authorizations_dir /
        _digest_filename("recovery-authorization", record), record
    )


def _scan_recovery_state(ws: Workspace, original_attempt_id: str) -> tuple[
    list[tuple[BrokerRecoveryAuthorization, Path]],
    list[tuple[SandboxBrokerRecoveryAttempt, Path]],
    list[tuple[BrokerRecoveryDisposition, Path]],
]:
    groups: list[list] = [[], [], []]
    specs = (
        (ws.signing_broker_recovery_authorizations_dir, read_recovery_authorization),
        (ws.signing_broker_recovery_attempts_dir, lambda _ws, ref: read_recovery_attempt(Path(ref))),
        (ws.signing_broker_recovery_dispositions_dir, lambda _ws, ref: read_recovery_disposition(Path(ref))),
    )
    for index, (area, reader) in enumerate(specs):
        for path in sorted(area.glob("*.json")):
            try:
                if index == 0:
                    record = reader(ws, _reference(ws, path))
                else:
                    record = reader(ws, str(path))
            except Exception as exc:
                raise ValidationError("RECOVERY_STORE_INVALID") from exc
            if record.original_attempt_id == original_attempt_id:
                groups[index].append((record, path))
    return groups[0], groups[1], groups[2]


def _disposition_data(
    *, authorization: BrokerRecoveryAuthorization,
    authorization_reference: str, recovery_attempt: SandboxBrokerRecoveryAttempt | None,
    recovery_attempt_path: Path | None, outcome: str, reasons: list[str],
    response: bytes | None, status_class: str, evidence: EvidenceImportOutcome | None,
    credential_reference: str, started_at: str, finished_at: str, ws: Workspace,
) -> dict:
    return {
        "profile": "broker-recovery-disposition", "schema_version": RECOVERY_DISPOSITION_SCHEMA,
        "recovery_authorization_reference": authorization_reference,
        "recovery_authorization_hash": authorization.content_hash,
        "original_attempt_reference": authorization.original_attempt_reference,
        "original_attempt_hash": authorization.original_attempt_hash,
        "original_attempt_id": authorization.original_attempt_id,
        "original_receipt_reference": authorization.original_receipt_reference,
        "original_receipt_hash": authorization.original_receipt_hash,
        "action": authorization.action,
        "recovery_attempt_reference": _reference(ws, recovery_attempt_path) if recovery_attempt_path else None,
        "recovery_attempt_hash": recovery_attempt.content_hash if recovery_attempt else None,
        "outcome": outcome, "reason_codes": sorted(set(reasons)),
        "request_body_hash": authorization.original_request_body_hash,
        "request_body_bytes": authorization.original_request_body_bytes,
        "response_body_hash": sha256_bytes(response) if response is not None else None,
        "response_body_bytes": len(response) if response is not None else None,
        "http_status_class": status_class,
        "envelope_storage_reference": _reference(ws, evidence.envelope_path) if evidence else None,
        "envelope_hash": evidence.binding.envelope_hash if evidence else None,
        "evidence_binding_reference": _reference(ws, evidence.binding_path) if evidence else None,
        "evidence_binding_hash": evidence.binding.content_hash if evidence else None,
        "verification_status": evidence.binding.verification_status if evidence else "NOT_RUN",
        "credential_reference": credential_reference,
        "started_at": started_at, "finished_at": finished_at,
        "time_source_classification": "diagnostic-local",
        "authority_effect": "none", "decision_effect": "none",
        "membership_effect": "none", "action_execution_allowed": False,
    }


def _record_disposition_event(ws: Workspace, disposition: BrokerRecoveryDisposition,
                              attempt: SandboxBrokerRecoveryAttempt | None, finished_at: str) -> None:
    event_type = ("sandbox_broker_recovery_abandoned" if disposition.action == "ABANDON"
                  else "sandbox_broker_recovery_attempt_recorded")
    hashes = {"broker_recovery_disposition": disposition.content_hash,
              "broker_recovery_authorization": disposition.recovery_authorization_hash,
              "original_sandbox_broker_attempt": disposition.original_attempt_hash}
    if attempt:
        hashes["sandbox_broker_recovery_attempt"] = attempt.content_hash
    record_event(
        ws, event_type=event_type, actor="conclave", authority_level="system",
        subject_refs=[], artifact_hashes=hashes,
        payload={"outcome": disposition.outcome, "reason_codes": disposition.reason_codes,
                 "authority_effect": "none", "decision_effect": "none",
                 "membership_effect": "none", "action_execution_allowed": False},
        occurred_at=finished_at,
    )


def execute_recovery(
    ws: Workspace, *, recovery_authorization_reference: str,
    transport: SandboxBrokerTransport, credential_resolver: CredentialResolver,
    public_evidence: dict[str, bytes], verifier: IDMEvidenceVerifier,
    now: str | None = None,
) -> RecoveryExecutionOutcome:
    workspace_id = verified_workspace_id(ws)
    authorization = read_recovery_authorization(ws, recovery_authorization_reference)
    current = now or utcnow()
    _timestamp(current)
    principal = ws.load_config().get("principal")
    if not all((authorization.workspace_id == workspace_id,
                authorization.authorized_principal == principal,
                _dt(authorization.issued_at) <= _dt(current) < _dt(authorization.expires_at))):
        raise ValidationError("RECOVERY_AUTHORIZATION_INVALID_OR_EXPIRED")
    original, _original_path, _original_auth, endpoint, _request, request_path, body = _load_original(
        ws, authorization.original_attempt_reference
    )
    if not all((original.content_hash == authorization.original_attempt_hash,
                original.attempt_id == authorization.original_attempt_id,
                original.endpoint_hash == authorization.original_endpoint_hash,
                original.request_body_hash == authorization.original_request_body_hash,
                body and sha256_bytes(body) == authorization.original_request_body_hash,
                len(body) == authorization.original_request_body_bytes,
                authorization.original_idempotency_key == original.attempt_id.rsplit(":", 1)[1],
                authorization.original_idempotency_key_hash ==
                sha256_bytes(authorization.original_idempotency_key.encode("ascii")))):
        raise IntegrityError("RECOVERY_AUTHORIZATION_BINDING_INVALID")
    matches = _receipts_for_attempt(ws, original)
    if authorization.original_outcome == "MISSING_RECEIPT":
        if matches:
            raise ValidationError("RECOVERY_STATE_CHANGED")
        if _ledger_records_hash(
            ws, {"sandbox_broker_transport_attempt_recorded"}, original.content_hash
        ):
            raise ValidationError("RECOVERY_RECORDED_RECEIPT_MISSING")
    else:
        if not matches or _reference(ws, matches[0][1]) != authorization.original_receipt_reference:
            raise ValidationError("RECOVERY_STATE_CHANGED")
        if matches[0][0].content_hash != authorization.original_receipt_hash or matches[0][0].outcome != "SENT_NO_RESPONSE":
            raise ValidationError("RECOVERY_STATE_CHANGED")

    digest = original.attempt_id.rsplit(":", 1)[1]
    lock_path = ws.signing_broker_recovery_attempts_dir / f"recovery-{digest}"
    with exclusive_lock(lock_path):
        authorizations, attempts, dispositions = _scan_recovery_state(ws, original.attempt_id)
        if len(authorizations) != 1 or authorizations[0][0].content_hash != authorization.content_hash:
            raise ValidationError("RECOVERY_AUTHORIZATION_CONFLICT")
        if dispositions:
            disposition, path = dispositions[0]
            if len(dispositions) == 1 and disposition.recovery_authorization_hash == authorization.content_hash:
                return RecoveryExecutionOutcome(authorization, attempts[0][0] if attempts else None,
                                                attempts[0][1] if attempts else None,
                                                disposition, path, None)
            raise ValidationError("RECOVERY_ALREADY_DISPOSED")
        if _ledger_records_hash(
            ws,
            {"sandbox_broker_recovery_abandoned", "sandbox_broker_recovery_attempt_recorded"},
            authorization.content_hash,
        ):
            raise ValidationError("RECOVERY_RECORDED_DISPOSITION_MISSING")
        if attempts:
            raise ValidationError("RECOVERY_OUTCOME_UNKNOWN")

        started_at = current
        if authorization.action == "ABANDON":
            finished_at = now or utcnow()
            data = _disposition_data(
                authorization=authorization,
                authorization_reference=recovery_authorization_reference,
                recovery_attempt=None, recovery_attempt_path=None,
                outcome="ABANDONED_WITHOUT_TRANSMISSION", reasons=[], response=None,
                status_class="none", evidence=None,
                credential_reference=endpoint.credential_reference,
                started_at=started_at, finished_at=finished_at, ws=ws,
            )
            disposition = seal_record(BrokerRecoveryDisposition, data)
            path, _ = write_immutable_record(
                ws.signing_broker_recovery_dispositions_dir /
                _digest_filename("recovery-disposition", disposition), disposition
            )
            _record_disposition_event(ws, disposition, None, finished_at)
            return RecoveryExecutionOutcome(authorization, None, None, disposition, path, None)

        recovery_id = "recovery:sha256:" + sha256_bytes(
            (authorization.content_hash + ":" + original.attempt_id).encode("ascii")
        ).split(":", 1)[1]
        recovery_attempt = seal_record(SandboxBrokerRecoveryAttempt, {
            "profile": "sandbox-broker-recovery-attempt", "schema_version": RECOVERY_ATTEMPT_SCHEMA,
            "recovery_attempt_id": recovery_id,
            "recovery_authorization_reference": recovery_authorization_reference,
            "recovery_authorization_hash": authorization.content_hash,
            "original_attempt_reference": authorization.original_attempt_reference,
            "original_attempt_hash": authorization.original_attempt_hash,
            "original_attempt_id": authorization.original_attempt_id,
            "endpoint_reference": authorization.original_endpoint_reference,
            "endpoint_hash": authorization.original_endpoint_hash,
            "signing_request_reference": authorization.original_signing_request_reference,
            "signing_request_hash": authorization.original_signing_request_hash,
            "request_body_hash": authorization.original_request_body_hash,
            "request_body_bytes": authorization.original_request_body_bytes,
            "idempotency_key": authorization.original_idempotency_key,
            "created_at": current, "time_source_classification": "diagnostic-local",
            "state": "PREPARED", "maximum_transmissions": 1,
            "authority_effect": "none", "decision_effect": "none",
            "membership_effect": "none", "action_execution_allowed": False,
        })
        recovery_attempt_path, _ = write_immutable_record(
            ws.signing_broker_recovery_attempts_dir /
            _digest_filename("recovery-attempt", recovery_attempt), recovery_attempt
        )
        response_bytes: bytes | None = None
        evidence: EvidenceImportOutcome | None = None
        status_class = "none"
        reasons: list[str] = []
        outcome = "REPLAY_NOT_SENT"
        phase = "credential"
        try:
            credential = _validate_credential(credential_resolver.resolve(endpoint.credential_reference))
            phase = "transport"
            response = transport.send(endpoint=endpoint, body=body, credential=credential,
                                      idempotency_key=authorization.original_idempotency_key)
            phase = "response"
            if type(response.status) is not int or not isinstance(response.content_type, str) or not isinstance(response.body, bytes):
                raise ValidationError("TRANSPORT_RESPONSE_INVALID")
            if len(response.body) > endpoint.maximum_response_bytes + 1:
                raise ValidationError("TRANSPORT_RESPONSE_BOUND_VIOLATION")
            response_bytes = response.body
            status_class = f"{response.status // 100}xx" if 100 <= response.status <= 599 else "none"
            if len(response.body) > endpoint.maximum_response_bytes:
                outcome, reasons = "REPLAY_RESPONSE_REJECTED", ["RESPONSE_TOO_LARGE"]
            elif not 200 <= response.status < 300:
                outcome, reasons = "REPLAY_RESPONSE_REJECTED", ["HTTP_RESPONSE_REJECTED"]
            elif response.content_type.lower() != RESPONSE_MEDIA_TYPE:
                outcome, reasons = "REPLAY_RESPONSE_REJECTED", ["RESPONSE_MEDIA_TYPE_INVALID"]
            elif not response.body:
                outcome, reasons = "REPLAY_RESPONSE_REJECTED", ["RESPONSE_EMPTY"]
            else:
                phase = "import"
                trust_path = _safe(authorization.original_trust_input_reference, ws,
                                   ws.identity_trust_inputs_dir, ("identity", "trust-inputs"))
                evidence = import_evidence_envelope(
                    ws, request_path=request_path, trust_input_path=trust_path,
                    envelope=response.body, public_evidence=public_evidence, verifier=verifier,
                )
                outcome = "REPLAY_RESPONSE_ACCEPTED_FOR_VERIFICATION"
                if evidence.binding.verification_status == "FAIL":
                    reasons.append("EVIDENCE_VERIFICATION_FAILED")
                if evidence.conflict:
                    reasons.append("EVIDENCE_CONFLICT_OBSERVED")
        except SandboxTransportFailure as exc:
            outcome = "REPLAY_SENT_NO_RESPONSE" if exc.sent else "REPLAY_NOT_SENT"
            reasons = [exc.code]
        except ValidationError as exc:
            if phase in {"response", "import"}:
                code = ("EVIDENCE_IMPORT_ERROR" if phase == "import" else
                        str(exc) if REASON.fullmatch(str(exc)) else "TRANSPORT_RESPONSE_INVALID")
                outcome = "REPLAY_RESPONSE_REJECTED"
            else:
                code = str(exc) if REASON.fullmatch(str(exc)) else "RECOVERY_PRECONDITION_FAILED"
            reasons = [code]
        except Exception:
            if phase == "credential":
                outcome, reasons = "REPLAY_NOT_SENT", ["CREDENTIAL_RESOLVER_ERROR"]
            elif phase == "transport":
                outcome, reasons = "REPLAY_SENT_NO_RESPONSE", ["TRANSPORT_ERROR"]
            else:
                outcome, reasons = "REPLAY_RESPONSE_REJECTED", ["EVIDENCE_IMPORT_ERROR"]
        finished_at = now or utcnow()
        data = _disposition_data(
            authorization=authorization, authorization_reference=recovery_authorization_reference,
            recovery_attempt=recovery_attempt, recovery_attempt_path=recovery_attempt_path,
            outcome=outcome, reasons=reasons, response=response_bytes,
            status_class=status_class, evidence=evidence,
            credential_reference=endpoint.credential_reference,
            started_at=started_at, finished_at=finished_at, ws=ws,
        )
        disposition = seal_record(BrokerRecoveryDisposition, data)
        disposition_path, _ = write_immutable_record(
            ws.signing_broker_recovery_dispositions_dir /
            _digest_filename("recovery-disposition", disposition), disposition
        )
        _record_disposition_event(ws, disposition, recovery_attempt, finished_at)
        return RecoveryExecutionOutcome(authorization, recovery_attempt, recovery_attempt_path,
                                        disposition, disposition_path, evidence)
