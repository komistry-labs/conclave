"""Increment 20A immutable profiles and keyless fixture diagnostics.

This module stores public configuration only.  It has no credential lookup,
key, signing, identity-verification, network, or broker transport interface.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from .errors import IntegrityError, ValidationError
from .identity import ClosedModel, HashedRecord, read_record, seal_record, sha256_bytes, write_immutable_record
from .workspace import Workspace, utcnow

VERIFIER_PROFILE_SCHEMA = "idm-verifier-profile/0.1.0"
BROKER_PROFILE_SCHEMA = "broker-transport-profile/0.1.0"
DIAGNOSTICS_RESULT_SCHEMA = "diagnostics-result/0.1.0"
EVIDENCE_CONTEXT = "conclave-evidence/1.0"
FIXTURE_TRANSPORT = "fixture:conclave-19d-diagnostics"
FIXTURE_PROBE_PROTOCOL = "conclave-fixture-diagnostics/0.1.0"
FIXTURE_MARKER = "CONCLAVE_FIXTURE_DIAGNOSTICS"
MAX_PROBE_OUTPUT = 64 * 1024
PROFILE_ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
SANDBOX_TRANSPORT_RE = re.compile(r"^sandbox:[a-z][a-z0-9-]{0,63}$")
CREDENTIAL_RE = re.compile(r"^env:[A-Z][A-Z0-9_]{0,127}$")
REASON_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


class IDMImplementationIdentity(ClosedModel):
    package: Literal["idm-reference"] = "idm-reference"
    version: Literal["0.1.0.dev0"] = "0.1.0.dev0"
    import_name: Literal["idm"] = "idm"
    commit: Literal["3769ce3943c87e6a5a72bf94b0efdaa2b11c3bd2"]
    tree: Literal["425f650696a798c10f2a553781fee45e0950dc2a"]
    wheel_filename: Literal["idm_reference-0.1.0.dev0-py3-none-any.whl"]
    wheel_sha256: Literal["07120effab0182701e47449e572b94e5a952c210aebfdf217fd965696154d903"]
    source_archive_sha256: Literal["98335d16dd0dd7bdfeb27fa77374e741e575cec3bbafc009a66c80374188efb7"]
    provisioning: Literal["external-hash-verified"] = "external-hash-verified"
    classification: Literal["verification-dependency-pin-not-a-trust-anchor"] = (
        "verification-dependency-pin-not-a-trust-anchor"
    )


FROZEN_IMPLEMENTATION = IDMImplementationIdentity(
    commit="3769ce3943c87e6a5a72bf94b0efdaa2b11c3bd2",
    tree="425f650696a798c10f2a553781fee45e0950dc2a",
    wheel_filename="idm_reference-0.1.0.dev0-py3-none-any.whl",
    wheel_sha256="07120effab0182701e47449e572b94e5a952c210aebfdf217fd965696154d903",
    source_archive_sha256="98335d16dd0dd7bdfeb27fa77374e741e575cec3bbafc009a66c80374188efb7",
)


def _policy_pin_path() -> Path | None:
    candidates = (
        Path(__file__).resolve().parents[2] / "policies" / "idm-reference-pin.json",
        Path(__file__).resolve().with_name("policies") / "idm-reference-pin.json",
    )
    return next((path for path in candidates if path.is_file()), None)


def _implementation_from_policy() -> IDMImplementationIdentity:
    path = _policy_pin_path()
    if path is None:
        raise ValidationError("frozen IDM policy pin is unavailable")
    try:
        pin = json.loads(path.read_text(encoding="utf-8"))
        return IDMImplementationIdentity.model_validate({
            "package": pin["package"], "version": pin["version"],
            "import_name": pin["import_name"], "commit": pin["commit"],
            "tree": pin["tree"], "wheel_filename": pin["wheel"]["filename"],
            "wheel_sha256": pin["wheel"]["sha256"],
            "source_archive_sha256": pin["source_archive_sha256"],
            "provisioning": pin["provisioning"],
            "classification": pin["classification"],
        })
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValidationError("frozen IDM policy pin is malformed or mismatched") from exc


def _assert_policy_pin() -> None:
    if _implementation_from_policy() != FROZEN_IMPLEMENTATION:
        raise ValidationError("frozen IDM policy pin differs from the 20A baseline")


def implementation_pin_hash() -> str:
    _assert_policy_pin()
    path = _policy_pin_path()
    if path is None:  # guarded above; kept explicit for type and fail-closed clarity
        raise ValidationError("frozen IDM policy pin is unavailable")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError("frozen IDM policy pin is malformed") from exc
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False).encode("utf-8")
    return sha256_bytes(raw)


def _profile_id(value: str) -> str:
    if PROFILE_ID_RE.fullmatch(value) is None:
        raise ValueError("profile_id must use the frozen lowercase safe-label grammar")
    return value


def _timestamp(value: str) -> str:
    from .identity import _validate_timestamp
    return _validate_timestamp(value)


def _canonical_reference(value: str, prefix: tuple[str, ...]) -> str:
    if not value or "\\" in value or ":" in value or value.startswith(("/", "//")):
        raise ValueError("reference must be canonical workspace-relative POSIX syntax")
    pure = PurePosixPath(value)
    if pure.is_absolute() or pure.parts[:len(prefix)] != prefix:
        raise ValueError("reference is outside its allowlisted workspace area")
    if pure.as_posix() != value or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError("reference contains an unsafe path segment")
    return value


class IDMVerifierProfile(HashedRecord):
    profile: Literal["idm-verifier-profile"] = "idm-verifier-profile"
    schema_version: Literal["idm-verifier-profile/0.1.0"] = VERIFIER_PROFILE_SCHEMA
    profile_id: str
    implementation: IDMImplementationIdentity
    expected_trust_input_reference: str
    expected_trust_domain_id: str = Field(pattern=r"^tdid:[a-z2-7]{26}$")
    created_by: str = Field(min_length=1, max_length=256)
    created_at: str
    authority_effect: Literal["none"] = "none"
    decision_effect: Literal["none"] = "none"
    membership_effect: Literal["none"] = "none"
    action_execution_allowed: Literal[False] = False

    _valid_id = field_validator("profile_id")(_profile_id)
    _valid_time = field_validator("created_at")(_timestamp)

    @field_validator("expected_trust_input_reference")
    @classmethod
    def trust_reference(cls, value: str) -> str:
        return _canonical_reference(value, ("identity", "trust-inputs"))

    @model_validator(mode="after")
    def exact_pin(self) -> "IDMVerifierProfile":
        if self.implementation != FROZEN_IMPLEMENTATION:
            raise ValueError("verifier profile differs from the frozen IDM pin")
        return self


class BrokerTransportProfile(HashedRecord):
    profile: Literal["broker-transport-profile"] = "broker-transport-profile"
    schema_version: Literal["broker-transport-profile/0.1.0"] = BROKER_PROFILE_SCHEMA
    profile_id: str
    classification: Literal["fixture-only", "sandbox"]
    verifier_profile_reference: str
    verifier_profile_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    transport_identifier: str
    evidence_context: Literal["conclave-evidence/1.0"] = EVIDENCE_CONTEXT
    credential_reference: str
    created_by: str = Field(min_length=1, max_length=256)
    created_at: str
    authority_effect: Literal["none"] = "none"
    decision_effect: Literal["none"] = "none"
    membership_effect: Literal["none"] = "none"
    action_execution_allowed: Literal[False] = False

    _valid_id = field_validator("profile_id")(_profile_id)
    _valid_time = field_validator("created_at")(_timestamp)

    @field_validator("verifier_profile_reference")
    @classmethod
    def verifier_reference(cls, value: str) -> str:
        return _canonical_reference(value, ("identity", "verifier-profiles"))

    @model_validator(mode="after")
    def coherent_transport(self) -> "BrokerTransportProfile":
        if self.classification == "fixture-only":
            if self.transport_identifier != FIXTURE_TRANSPORT or self.credential_reference != "none":
                raise ValueError("fixture-only profile requires the fixed transport and no credential")
        elif SANDBOX_TRANSPORT_RE.fullmatch(self.transport_identifier) is None:
            raise ValueError("sandbox transport identifier is malformed")
        elif CREDENTIAL_RE.fullmatch(self.credential_reference) is None:
            raise ValueError("sandbox credential reference is malformed")
        return self


class FixtureProbeResult(ClosedModel):
    classification: Literal["fixture-only"]
    protocol: Literal["conclave-fixture-diagnostics/0.1.0"]
    implementation: IDMImplementationIdentity


class DiagnosticsResult(HashedRecord):
    profile: Literal["diagnostics-result"] = "diagnostics-result"
    schema_version: Literal["diagnostics-result/0.1.0"] = DIAGNOSTICS_RESULT_SCHEMA
    check_kind: Literal["fixture_broker_diagnostics"] = "fixture_broker_diagnostics"
    broker_profile_reference: str
    broker_profile_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    verifier_profile_reference: str
    verifier_profile_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    checked_implementation_pin_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    implementation: IDMImplementationIdentity
    status: Literal["PASS", "FAIL"]
    reason_codes: list[str]
    checked_at: str
    time_source_classification: Literal["diagnostic-local"] = "diagnostic-local"
    probe_result: FixtureProbeResult | None = None
    authority_effect: Literal["none"] = "none"
    decision_effect: Literal["none"] = "none"
    membership_effect: Literal["none"] = "none"
    action_execution_allowed: Literal[False] = False

    _valid_time = field_validator("checked_at")(_timestamp)

    @field_validator("broker_profile_reference")
    @classmethod
    def broker_reference(cls, value: str) -> str:
        return _canonical_reference(value, ("signing", "broker-profiles"))

    @field_validator("verifier_profile_reference")
    @classmethod
    def verifier_reference(cls, value: str) -> str:
        return _canonical_reference(value, ("identity", "verifier-profiles"))

    @field_validator("reason_codes")
    @classmethod
    def stable_reasons(cls, value: list[str]) -> list[str]:
        if value != sorted(set(value)) or any(REASON_RE.fullmatch(x) is None for x in value):
            raise ValueError("reason codes must be unique sorted stable codes")
        return value

    @model_validator(mode="after")
    def coherent_status(self) -> "DiagnosticsResult":
        if self.status == "PASS" and (self.reason_codes or self.probe_result is None):
            raise ValueError("PASS requires a probe result and no reasons")
        if self.status == "FAIL" and not self.reason_codes:
            raise ValueError("FAIL requires at least one reason")
        return self


def _record_reference(ws: Workspace, path: Path) -> str:
    return path.relative_to(ws.root).as_posix()


def _digest_filename(prefix: str, record: HashedRecord) -> str:
    return f"{prefix}-{record.content_hash.split(':', 1)[1]}.json"


def _read_content_addressed(path: Path, record_type: type[HashedRecord], prefix: str) -> HashedRecord:
    try:
        record = read_record(path, record_type)
    except Exception as exc:
        raise ValidationError("profile or diagnostics record is invalid") from exc
    if path.name != _digest_filename(prefix, record):
        raise IntegrityError("record filename does not match its content hash")
    return record


def _safe_record_path(ws: Workspace, reference: str, allowed: Path, prefix: tuple[str, ...]) -> Path:
    _canonical_reference(reference, prefix)
    relative = PurePosixPath(reference)
    candidate = ws.root.joinpath(*relative.parts)
    allowed_resolved = allowed.resolve()
    resolved = candidate.resolve()
    if resolved.parent != allowed_resolved or not resolved.is_relative_to(ws.root.resolve()):
        raise ValidationError("record reference is outside its allowlisted workspace area")
    current = ws.root
    for part in relative.parts:
        current = current / part
        try:
            info = current.lstat()
        except OSError as exc:
            raise ValidationError("profile record is unavailable") from exc
        attributes = getattr(info, "st_file_attributes", 0)
        if stat.S_ISLNK(info.st_mode) or attributes & 0x400:
            raise ValidationError("profile record path contains a symlink or reparse point")
    if not candidate.is_file():
        raise ValidationError("profile reference does not name a regular file")
    return candidate


def create_verifier_profile(
    ws: Workspace, *, profile_id: str, expected_trust_input_reference: str,
    expected_trust_domain_id: str, created_by: str, created_at: str | None = None,
) -> tuple[IDMVerifierProfile, Path, bool]:
    _assert_policy_pin()
    record = seal_record(IDMVerifierProfile, {
        "profile": "idm-verifier-profile", "schema_version": VERIFIER_PROFILE_SCHEMA,
        "profile_id": profile_id, "implementation": FROZEN_IMPLEMENTATION,
        "expected_trust_input_reference": expected_trust_input_reference,
        "expected_trust_domain_id": expected_trust_domain_id,
        "created_by": created_by, "created_at": created_at or utcnow(),
        "authority_effect": "none", "decision_effect": "none",
        "membership_effect": "none", "action_execution_allowed": False,
    })
    return record, *write_immutable_record(
        ws.identity_verifier_profiles_dir / _digest_filename("verifier", record), record
    )


def read_verifier_profile(ws: Workspace, reference: str) -> IDMVerifierProfile:
    _assert_policy_pin()
    path = _safe_record_path(ws, reference, ws.identity_verifier_profiles_dir,
                             ("identity", "verifier-profiles"))
    return _read_content_addressed(path, IDMVerifierProfile, "verifier")  # type: ignore[return-value]


def create_broker_profile(
    ws: Workspace, *, profile_id: str, classification: str,
    verifier_profile_reference: str, transport_identifier: str,
    credential_reference: str, created_by: str, created_at: str | None = None,
) -> tuple[BrokerTransportProfile, Path, bool]:
    verifier = read_verifier_profile(ws, verifier_profile_reference)
    record = seal_record(BrokerTransportProfile, {
        "profile": "broker-transport-profile", "schema_version": BROKER_PROFILE_SCHEMA,
        "profile_id": profile_id, "classification": classification,
        "verifier_profile_reference": verifier_profile_reference,
        "verifier_profile_hash": verifier.content_hash,
        "transport_identifier": transport_identifier, "evidence_context": EVIDENCE_CONTEXT,
        "credential_reference": credential_reference, "created_by": created_by,
        "created_at": created_at or utcnow(), "authority_effect": "none",
        "decision_effect": "none", "membership_effect": "none",
        "action_execution_allowed": False,
    })
    return record, *write_immutable_record(
        ws.signing_broker_profiles_dir / _digest_filename("broker", record), record
    )


def read_broker_profile(ws: Workspace, reference: str) -> BrokerTransportProfile:
    path = _safe_record_path(ws, reference, ws.signing_broker_profiles_dir,
                             ("signing", "broker-profiles"))
    record = _read_content_addressed(path, BrokerTransportProfile, "broker")
    verifier = read_verifier_profile(ws, record.verifier_profile_reference)
    if verifier.content_hash != record.verifier_profile_hash:
        raise IntegrityError("broker profile verifier-profile hash mismatch")
    return record


def _probe_path() -> Path | None:
    candidate = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "idm_diagnostics_probe.py"
    return candidate if candidate.is_file() else None


def _run_fixture_probe() -> tuple[FixtureProbeResult | None, list[str]]:
    probe = _probe_path()
    if probe is None:
        return None, ["FIXTURE_PROBE_UNAVAILABLE"]
    try:
        completed = subprocess.run(
            [sys.executable, str(probe), "--diagnostics-probe"],
            stdin=subprocess.DEVNULL, capture_output=True, check=False, timeout=10,
            env={FIXTURE_MARKER: "1", "PYTHONIOENCODING": "utf-8"},
        )
    except (OSError, subprocess.SubprocessError):
        return None, ["FIXTURE_PROBE_ERROR"]
    if len(completed.stdout) > MAX_PROBE_OUTPUT or len(completed.stderr) > MAX_PROBE_OUTPUT:
        return None, ["FIXTURE_PROBE_MALFORMED"]
    if completed.returncode != 0 or completed.stderr:
        return None, ["FIXTURE_PROBE_ERROR"]
    try:
        value = json.loads(completed.stdout.decode("utf-8"))
        result = FixtureProbeResult.model_validate(value)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
        return None, ["FIXTURE_PROBE_MALFORMED"]
    if result.implementation != FROZEN_IMPLEMENTATION:
        return None, ["FIXTURE_PROBE_PIN_MISMATCH"]
    return result, []


def run_broker_check(
    ws: Workspace, *, broker_profile_reference: str, checked_at: str | None = None,
) -> tuple[DiagnosticsResult, Path, bool]:
    broker = read_broker_profile(ws, broker_profile_reference)
    verifier = read_verifier_profile(ws, broker.verifier_profile_reference)
    reasons: list[str] = []
    probe_result: FixtureProbeResult | None = None
    if verifier.implementation != FROZEN_IMPLEMENTATION:
        reasons.append("IDM_PIN_MISMATCH")
    if broker.classification == "sandbox":
        reasons.append("SANDBOX_TRANSPORT_NOT_AUTHORIZED")
    else:
        probe_result, probe_reasons = _run_fixture_probe()
        reasons.extend(probe_reasons)
    reasons = sorted(set(reasons))
    record = seal_record(DiagnosticsResult, {
        "profile": "diagnostics-result", "schema_version": DIAGNOSTICS_RESULT_SCHEMA,
        "check_kind": "fixture_broker_diagnostics",
        "broker_profile_reference": broker_profile_reference,
        "broker_profile_hash": broker.content_hash,
        "verifier_profile_reference": broker.verifier_profile_reference,
        "verifier_profile_hash": verifier.content_hash,
        "checked_implementation_pin_hash": implementation_pin_hash(),
        "implementation": FROZEN_IMPLEMENTATION,
        "status": "FAIL" if reasons else "PASS", "reason_codes": reasons,
        "checked_at": checked_at or utcnow(),
        "time_source_classification": "diagnostic-local", "probe_result": probe_result,
        "authority_effect": "none", "decision_effect": "none",
        "membership_effect": "none", "action_execution_allowed": False,
    })
    return record, *write_immutable_record(
        ws.diagnostics_dir / _digest_filename("diagnostics", record), record
    )


def read_diagnostics_result(path: Path) -> DiagnosticsResult:
    return _read_content_addressed(Path(path), DiagnosticsResult, "diagnostics")  # type: ignore[return-value]


def diagnostics_event_fields(ws: Workspace, record: DiagnosticsResult, path: Path) -> dict[str, Any]:
    return {
        "event_type": "fixture_broker_diagnostics_recorded",
        "actor": "conclave", "authority_level": "system", "subject_refs": [],
        "artifact_hashes": {
            "diagnostics_result": record.content_hash,
            "broker_profile": record.broker_profile_hash,
            "verifier_profile": record.verifier_profile_hash,
        },
        "payload": {
            "diagnostics_reference": _record_reference(ws, path),
            "status": record.status, "reason_codes": record.reason_codes,
            "authority_effect": "none", "decision_effect": "none",
            "membership_effect": "none", "action_execution_allowed": False,
            "note": "fixture diagnostics only; no broker health, verification, signing, approval, authority or membership inferred",
        },
        "occurred_at": record.checked_at,
    }
