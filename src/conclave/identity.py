"""Increment 19A IDM identity-verification foundation.

CONCLAVE does not implement IDM, hold keys, or issue identities.  This module
defines the closed, immutable records at the CONCLAVE/IDM boundary and applies
fail-closed cross-binding rules to the result of a pinned public verifier.

The verifier is injected through :class:`IDMVerifier`.  That keeps private
material and signing operations outside this process and makes the accepted
IDM build identity an input that can be checked rather than an ambient fact.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Protocol, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from .errors import IntegrityError, ValidationError

TRUST_INPUT_SCHEMA = "idm-trust-input-set/0.1.0"
ACTOR_BINDING_SCHEMA = "idm-actor-binding/0.1.0"
VERIFICATION_RESULT_SCHEMA = "idm-verification-result/0.1.0"

IDM_BASELINE_COMMIT = "3769ce3943c87e6a5a72bf94b0efdaa2b11c3bd2"
IDM_BASELINE_TREE = "425f650696a798c10f2a553781fee45e0950dc2a"
IDM_BASELINE_WHEEL_SHA256 = (
    "07120effab0182701e47449e572b94e5a952c210aebfdf217fd965696154d903"
)
IDM_BASELINE_SOURCE_SHA256 = (
    "98335d16dd0dd7bdfeb27fa77374e741e575cec3bbafc009a66c80374188efb7"
)

PRIVATE_REFERENCE_MARKERS = (
    ".idmk",
    "private-key",
    "private_key",
    "passphrase",
    "recovery-secret",
    "recovery_secret",
    "bearer-token",
    "bearer_token",
    "/secrets/",
    "\\secrets\\",
    "/tokens/",
    "\\tokens\\",
    "/keys/",
    "\\keys\\",
    "/vault/",
    "\\vault\\",
    "offline-root",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(value: bytes) -> str:
    """Return a CONCLAVE-formatted SHA-256 hash for exact binary bytes."""

    return "sha256:" + hashlib.sha256(value).hexdigest()


def _body_hash(model: BaseModel) -> str:
    body = model.model_dump(mode="json", exclude={"content_hash"})
    return sha256_bytes(_canonical_json(body).encode("utf-8"))


def _validate_timestamp(value: str) -> str:
    # IDM v1 timestamps are UTC, second-precision RFC 3339 values.  Enforcing
    # their lexical form also makes ordering deterministic without repair.
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value) is None:
        raise ValueError("timestamp must be second-precision UTC RFC 3339 text")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError("timestamp is not a valid UTC calendar value") from exc
    return value


def _validate_sorted_unique(value: list[str]) -> list[str]:
    if not value:
        raise ValueError("list must not be empty")
    if value != sorted(set(value)):
        raise ValueError("entries must be unique and sorted")
    return value


class ClosedModel(BaseModel):
    """Strict immutable base for the Increment 19 boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class HashedRecord(ClosedModel):
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def content_hash_is_current(self, info: ValidationInfo) -> "HashedRecord":
        if isinstance(info.context, dict) and info.context.get("skip_content_hash") is True:
            return self
        if self.content_hash != _body_hash(self):
            raise ValueError("content_hash does not match the canonical record body")
        return self


class IDMImplementationPin(ClosedModel):
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    wheel_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_archive_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    def is_frozen_baseline(self) -> bool:
        return (
            self.commit == IDM_BASELINE_COMMIT
            and self.tree == IDM_BASELINE_TREE
            and self.wheel_sha256 == IDM_BASELINE_WHEEL_SHA256
            and self.source_archive_sha256 == IDM_BASELINE_SOURCE_SHA256
        )


FROZEN_IDM_IMPLEMENTATION = IDMImplementationPin(
    commit=IDM_BASELINE_COMMIT,
    tree=IDM_BASELINE_TREE,
    wheel_sha256=IDM_BASELINE_WHEEL_SHA256,
    source_archive_sha256=IDM_BASELINE_SOURCE_SHA256,
)


class PublicEvidenceReference(ClosedModel):
    reference: str = Field(min_length=1, max_length=512)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("reference")
    @classmethod
    def public_reference_only(cls, value: str) -> str:
        normalized = value.lower()
        if any(marker in normalized for marker in PRIVATE_REFERENCE_MARKERS):
            raise ValueError("reference appears to identify prohibited private material")
        if Path(normalized).suffix in {".env", ".idmk", ".key", ".p12", ".pem", ".pfx"}:
            raise ValueError("reference appears to identify prohibited private material")
        return value


class TrustInputSet(HashedRecord):
    profile: Literal["idm-trust-input-set"] = "idm-trust-input-set"
    schema_version: Literal["idm-trust-input-set/0.1.0"] = TRUST_INPUT_SCHEMA
    idm_implementation: IDMImplementationPin
    trust_bundle: PublicEvidenceReference
    trust_domain_id: str = Field(pattern=r"^tdid:[a-z2-7]{26}$")
    revocation_evidence: list[PublicEvidenceReference] = Field(min_length=1)
    evaluation_time: str
    time_source_classification: Literal["trusted", "rehearsal-local-time"]
    time_evidence: PublicEvidenceReference
    accepted_roles: list[str] = Field(min_length=1)
    required_scopes: list[str] = Field(min_length=1)
    created_by: str = Field(min_length=1, max_length=256)
    created_at: str

    @field_validator("evaluation_time", "created_at")
    @classmethod
    def valid_time(cls, value: str) -> str:
        return _validate_timestamp(value)

    @field_validator("accepted_roles", "required_scopes")
    @classmethod
    def ordered_values(cls, value: list[str]) -> list[str]:
        return _validate_sorted_unique(value)

    @model_validator(mode="after")
    def unique_revocation_references(self) -> "TrustInputSet":
        refs = [item.reference for item in self.revocation_evidence]
        if refs != sorted(set(refs)):
            raise ValueError("revocation evidence references must be unique and sorted")
        return self


class ActorIdentityBinding(HashedRecord):
    profile: Literal["idm-actor-binding"] = "idm-actor-binding"
    schema_version: Literal["idm-actor-binding/0.1.0"] = ACTOR_BINDING_SCHEMA
    actor_id: str = Field(min_length=1, max_length=256)
    actor_kind: Literal["human", "advisory_agent", "system"]
    expected_authority_level: Literal["human_principal", "advisory_agent", "system"]
    eid: str = Field(pattern=r"^eid:[a-z2-7]{26}$")
    mid: str = Field(pattern=r"^mid:[a-z2-7]{26}$")
    vid: str = Field(pattern=r"^vid:sha256:[A-Za-z0-9_-]{43}$")
    idm_artifact_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    trust_input_reference: str = Field(min_length=1, max_length=512)
    trust_input_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    required_identity_role: str | None = Field(default=None, min_length=1, max_length=128)
    required_claim: str | None = Field(default=None, min_length=1, max_length=256)
    binding_purpose: str = Field(min_length=1, max_length=512)
    workspace_id: str = Field(min_length=1, max_length=256)
    task_scope: str = Field(min_length=1, max_length=512)

    @model_validator(mode="after")
    def actor_kind_matches_authority_ceiling(self) -> "ActorIdentityBinding":
        ceiling = {
            "human": "human_principal",
            "advisory_agent": "advisory_agent",
            "system": "system",
        }
        if self.expected_authority_level != ceiling[self.actor_kind]:
            raise ValueError("actor kind and configured authority ceiling disagree")
        return self


class VerificationFindings(ClosedModel):
    trust: bool
    signature: bool
    lineage: bool
    delegation: bool
    role: bool
    scope: bool
    time: bool
    revocation: bool
    actor_binding: bool

    @classmethod
    def failed(cls) -> "VerificationFindings":
        return cls(
            trust=False,
            signature=False,
            lineage=False,
            delegation=False,
            role=False,
            scope=False,
            time=False,
            revocation=False,
            actor_binding=False,
        )


class IDMVerifierReport(ClosedModel):
    """Normalized public output from the independently pinned IDM verifier."""

    implementation: IDMImplementationPin
    trusted: bool
    eid: str | None = Field(default=None, pattern=r"^eid:[a-z2-7]{26}$")
    mid: str | None = Field(default=None, pattern=r"^mid:[a-z2-7]{26}$")
    vid: str | None = Field(default=None, pattern=r"^vid:sha256:[A-Za-z0-9_-]{43}$")
    trust_domain_id: str | None = Field(default=None, pattern=r"^tdid:[a-z2-7]{26}$")
    verified_roles: list[str] = Field(default_factory=list)
    verified_scopes: list[str] = Field(default_factory=list)
    findings: VerificationFindings
    reason_codes: list[str] = Field(default_factory=list)

    @field_validator("verified_roles", "verified_scopes")
    @classmethod
    def ordered_values(cls, value: list[str]) -> list[str]:
        if value != sorted(set(value)):
            raise ValueError("entries must be unique and sorted")
        return value

    @field_validator("reason_codes")
    @classmethod
    def stable_reason_codes(cls, value: list[str]) -> list[str]:
        if value != sorted(set(value)):
            raise ValueError("reason codes must be unique and sorted")
        if any(re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", item) is None for item in value):
            raise ValueError("reason codes must use stable uppercase syntax")
        return value


class IdentityVerificationResult(HashedRecord):
    profile: Literal["idm-verification-result"] = "idm-verification-result"
    schema_version: Literal["idm-verification-result/0.1.0"] = VERIFICATION_RESULT_SCHEMA
    status: Literal["NOT_RUN", "PASS", "FAIL"]
    actor_binding_reference: str = Field(min_length=1, max_length=512)
    actor_binding_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    eid: str | None = Field(default=None, pattern=r"^eid:[a-z2-7]{26}$")
    mid: str | None = Field(default=None, pattern=r"^mid:[a-z2-7]{26}$")
    vid: str | None = Field(default=None, pattern=r"^vid:sha256:[A-Za-z0-9_-]{43}$")
    idm_artifact_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    findings: VerificationFindings
    verifier_implementation: IDMImplementationPin
    evaluation_time: str
    time_source_classification: Literal["trusted", "rehearsal-local-time"]
    trust_bundle: PublicEvidenceReference
    revocation_evidence: list[PublicEvidenceReference]
    reason_codes: list[str]
    authority_effect: Literal["none"] = "none"
    membership_effect: Literal["none"] = "none"
    action_execution_allowed: Literal[False] = False

    @field_validator("evaluation_time")
    @classmethod
    def valid_time(cls, value: str) -> str:
        return _validate_timestamp(value)

    @field_validator("reason_codes")
    @classmethod
    def ordered_reasons(cls, value: list[str]) -> list[str]:
        if value != sorted(set(value)):
            raise ValueError("reason codes must be unique and sorted")
        return value

    @model_validator(mode="after")
    def status_is_consistent(self) -> "IdentityVerificationResult":
        all_findings = all(self.findings.model_dump().values())
        if self.status == "PASS" and (self.reason_codes or not all_findings):
            raise ValueError("PASS requires every finding and no reason codes")
        if self.status == "FAIL" and not self.reason_codes:
            raise ValueError("FAIL requires at least one reason code")
        if self.status == "NOT_RUN" and not self.reason_codes:
            raise ValueError("NOT_RUN requires a reason code")
        return self


class IDMVerifier(Protocol):
    """Public verifier boundary; no private-key or signing method exists."""

    def verify_identity(
        self,
        *,
        artifact: bytes,
        trust_bundle: bytes,
        revocation_evidence: tuple[bytes, ...],
        evaluation_time: str,
        accepted_roles: tuple[str, ...],
        required_role: str | None,
        required_claim: str | None,
        required_scopes: tuple[str, ...],
    ) -> IDMVerifierReport: ...


RecordT = TypeVar("RecordT", bound=HashedRecord)


def seal_record(record_type: type[RecordT], data: dict[str, Any]) -> RecordT:
    """Create a hash-bound record without repairing or normalizing its inputs."""

    if "content_hash" in data:
        raise ValidationError("content_hash is computed by seal_record, not supplied")
    # Validate and materialize every nested closed model before hashing.  The
    # temporary syntactically valid hash is ignored only for this first pass;
    # the returned object goes through normal validation with the real hash.
    draft = record_type.model_validate(
        {**data, "content_hash": "sha256:" + "0" * 64},
        context={"skip_content_hash": True},
    )
    return record_type.model_validate({**data, "content_hash": _body_hash(draft)})


def _read_exact_inputs(
    trust_inputs: TrustInputSet,
    public_evidence: dict[str, bytes],
) -> tuple[bytes | None, tuple[bytes, ...], list[str]]:
    reasons: list[str] = []
    trust_bytes = public_evidence.get(trust_inputs.trust_bundle.reference)
    if trust_bytes is None:
        reasons.append("TRUST_BUNDLE_MISSING")
    elif sha256_bytes(trust_bytes) != trust_inputs.trust_bundle.content_hash:
        reasons.append("TRUST_BUNDLE_HASH_MISMATCH")

    revocations: list[bytes] = []
    for item in trust_inputs.revocation_evidence:
        value = public_evidence.get(item.reference)
        if value is None:
            reasons.append("REVOCATION_EVIDENCE_MISSING")
        elif sha256_bytes(value) != item.content_hash:
            reasons.append("REVOCATION_EVIDENCE_HASH_MISMATCH")
        else:
            revocations.append(value)

    time_bytes = public_evidence.get(trust_inputs.time_evidence.reference)
    if time_bytes is None:
        reasons.append("TIME_EVIDENCE_MISSING")
    elif sha256_bytes(time_bytes) != trust_inputs.time_evidence.content_hash:
        reasons.append("TIME_EVIDENCE_HASH_MISMATCH")
    if trust_inputs.time_source_classification != "trusted":
        reasons.append("UNTRUSTED_TIME")
    return trust_bytes, tuple(revocations), reasons


def verify_actor_identity(
    *,
    binding_reference: str,
    trust_input_reference: str,
    binding: ActorIdentityBinding,
    trust_inputs: TrustInputSet,
    artifact: bytes,
    public_evidence: dict[str, bytes],
    verifier: IDMVerifier,
) -> IdentityVerificationResult:
    """Verify one binding deterministically and fail closed on every mismatch."""

    reasons: list[str] = []
    report: IDMVerifierReport | None = None
    artifact_hash = sha256_bytes(artifact)

    if not trust_inputs.idm_implementation.is_frozen_baseline():
        reasons.append("IDM_BASELINE_MISMATCH")
    if binding.trust_input_hash != trust_inputs.content_hash:
        reasons.append("TRUST_INPUT_HASH_MISMATCH")
    if binding.trust_input_reference != trust_input_reference:
        reasons.append("TRUST_INPUT_REFERENCE_MISMATCH")
    if artifact_hash != binding.idm_artifact_hash:
        reasons.append("IDM_ARTIFACT_HASH_MISMATCH")

    trust_bytes, revocations, input_reasons = _read_exact_inputs(
        trust_inputs, public_evidence
    )
    reasons.extend(input_reasons)

    if not reasons and trust_bytes is not None:
        try:
            report = verifier.verify_identity(
                artifact=artifact,
                trust_bundle=trust_bytes,
                revocation_evidence=revocations,
                evaluation_time=trust_inputs.evaluation_time,
                accepted_roles=tuple(trust_inputs.accepted_roles),
                required_role=binding.required_identity_role,
                required_claim=binding.required_claim,
                required_scopes=tuple(trust_inputs.required_scopes),
            )
        except Exception:
            # Never expose an adapter exception: it may contain a path, token,
            # protected field, or library-specific non-deterministic text.
            reasons.append("IDM_VERIFIER_ERROR")

    findings = report.findings if report is not None else VerificationFindings.failed()
    if report is not None:
        if not report.implementation.is_frozen_baseline():
            reasons.append("IDM_VERIFIER_BASELINE_MISMATCH")
        if report.trust_domain_id != trust_inputs.trust_domain_id:
            reasons.append("TRUST_DOMAIN_MISMATCH")
        if not report.trusted or not findings.trust:
            reasons.append("IDM_UNTRUSTED")
        if report.eid != binding.eid:
            reasons.append("EID_MISMATCH")
        if report.mid != binding.mid:
            reasons.append("MID_MISMATCH")
        if report.vid != binding.vid:
            reasons.append("VID_MISMATCH")
        if not set(trust_inputs.accepted_roles).intersection(report.verified_roles):
            reasons.append("ROLE_NOT_ACCEPTED")
        if (
            binding.required_identity_role is not None
            and binding.required_identity_role not in report.verified_roles
        ):
            reasons.append("ROLE_MISSING")
        if not set(trust_inputs.required_scopes).issubset(report.verified_scopes):
            reasons.append("SCOPE_MISSING")
        reasons.extend(report.reason_codes)
        finding_codes = {
            "trust": "TRUST_INVALID",
            "signature": "SIGNATURE_INVALID",
            "lineage": "LINEAGE_INVALID",
            "delegation": "DELEGATION_INVALID",
            "role": "ROLE_INVALID",
            "scope": "SCOPE_INVALID",
            "time": "TIME_INVALID",
            "revocation": "REVOCATION_INVALID",
            "actor_binding": "ACTOR_BINDING_INVALID",
        }
        reasons.extend(
            code for name, code in finding_codes.items() if not getattr(findings, name)
        )

    ordered_reasons = sorted(set(reasons))
    result_data = {
        "profile": "idm-verification-result",
        "schema_version": VERIFICATION_RESULT_SCHEMA,
        "status": "PASS" if not ordered_reasons else "FAIL",
        "actor_binding_reference": binding_reference,
        "actor_binding_hash": binding.content_hash,
        "eid": report.eid if report is not None else None,
        "mid": report.mid if report is not None else None,
        "vid": report.vid if report is not None else None,
        "idm_artifact_hash": artifact_hash,
        "findings": findings,
        "verifier_implementation": (
            report.implementation if report is not None else trust_inputs.idm_implementation
        ),
        "evaluation_time": trust_inputs.evaluation_time,
        "time_source_classification": trust_inputs.time_source_classification,
        "trust_bundle": trust_inputs.trust_bundle,
        "revocation_evidence": trust_inputs.revocation_evidence,
        "reason_codes": ordered_reasons,
        "authority_effect": "none",
        "membership_effect": "none",
        "action_execution_allowed": False,
    }
    return seal_record(IdentityVerificationResult, result_data)


def write_immutable_record(path: Path, record: HashedRecord) -> tuple[Path, bool]:
    """Write a closed record once; identical retry is idempotent."""

    path = Path(path)
    payload = (
        json.dumps(record.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        return path, True
    except FileExistsError:
        if path.read_bytes() != payload:
            raise IntegrityError(f"refusing to overwrite conflicting identity record {path}")
        return path, False


def read_record(path: Path, record_type: type[RecordT]) -> RecordT:
    """Read one bounded JSON record and enforce its closed schema and hash."""

    raw = Path(path).read_bytes()
    if len(raw) > 1024 * 1024:
        raise ValidationError("identity record exceeds the 1 MiB limit")
    try:
        value = json.loads(raw.decode("utf-8"))
        return record_type.model_validate(value)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        raise ValidationError(f"invalid identity record {path}") from exc
