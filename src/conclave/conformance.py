"""Increment 20D sandbox transport security/conformance evidence.

This module records public evidence; it does not run a transport, inspect a
credential, verify a signature, or confer authority.  A PASS record is only
representable when every frozen evidence class and control is present and
passing.  The evidence itself remains external and is bound by exact hashes.
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .errors import ValidationError
from .identity import (
    ClosedModel,
    HashedRecord,
    IDMImplementationPin,
    read_record,
    seal_record,
    write_immutable_record,
)
from .ledger import record_event
from .workspace import Workspace

CONFORMANCE_SCHEMA = "sandbox-broker-conformance-report/0.1.0"
STATUS = Literal["PASS", "FAIL", "NOT_RUN"]
REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
SHA256 = r"^sha256:[0-9a-f]{64}$"

REQUIRED_PROTOCOLS = ("20A", "20B", "20C", "20D")
REQUIRED_PLATFORMS = (
    ("windows", "3.12"),
    ("ubuntu", "3.13"),
    ("macos", "3.12"),
)
REQUIRED_REPORT_KINDS = ("PACKAGE", "SECRET_SCAN", "STATIC_SCAN", "TEST")
REQUIRED_CONTROLS = (
    "PATH_REFERENCE_SAFETY",
    "DNS_ADDRESS_SAFETY",
    "HTTPS_TLS_PROXY_REDIRECT_SAFETY",
    "TLS_AND_TRANSPORT_FAILURES",
    "CREDENTIAL_AND_ERROR_SECRECY",
    "RECORD_AND_RESPONSE_CANONICALITY",
    "CROSS_BINDING_AND_SUBSTITUTION",
    "TRUST_REVOCATION_AND_IDM_PIN",
    "INITIAL_SEND_AND_RECOVERY_CONCURRENCY",
    "PARTIAL_STATE_AND_RECONCILIATION",
    "AMBIGUOUS_REPLAY_CEILING",
    "SECRET_SENTINEL_ABSENCE",
    "LEGACY_DORMANT_COMPATIBILITY",
    "PROHIBITED_CAPABILITY_ABSENCE",
)


def _timestamp(value: str) -> str:
    from .identity import _validate_timestamp

    return _validate_timestamp(value)


def _stable_reasons(value: list[str]) -> list[str]:
    if value != sorted(set(value)) or any(REASON.fullmatch(item) is None for item in value):
        raise ValueError("reason codes must be unique sorted stable codes")
    return value


def _canonical_public_reference(value: str) -> str:
    """Allow only portable, relative POSIX evidence labels.

    References are identifiers, not paths opened by this module.  Keeping the
    grammar path-like and portable prevents a future consumer from treating a
    drive, UNC, ADS or traversal label as an ambient file capability.
    """
    if (
        not value
        or len(value) > 512
        or "\\" in value
        or ":" in value
        or value.startswith("/")
        or "\x00" in value
    ):
        raise ValueError("evidence reference must be canonical relative POSIX syntax")
    parts = PurePosixPath(value).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError("evidence reference must be canonical relative POSIX syntax")
    if PurePosixPath(*parts).as_posix() != value:
        raise ValueError("evidence reference must be canonical relative POSIX syntax")
    return value


class EvidenceReference(ClosedModel):
    reference: str
    content_hash: str = Field(pattern=SHA256)

    _reference = field_validator("reference")(_canonical_public_reference)


class ProtocolEvidence(EvidenceReference):
    increment: Literal["20A", "20B", "20C", "20D"]


class PlatformEvidence(ClosedModel):
    os: Literal["windows", "ubuntu", "macos"]
    python_version: Literal["3.12", "3.13"]
    test_suite_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    status: STATUS
    required_security_skips: int = Field(ge=0)
    report: EvidenceReference
    reason_codes: list[str]

    _reasons = field_validator("reason_codes")(_stable_reasons)

    @model_validator(mode="after")
    def status_is_honest(self) -> "PlatformEvidence":
        if self.status == "PASS" and (self.required_security_skips or self.reason_codes):
            raise ValueError("platform PASS cannot contain required skips or failure reasons")
        if self.status != "PASS" and not self.reason_codes:
            raise ValueError("non-PASS platform evidence requires a reason code")
        return self


class PackageEvidence(ClosedModel):
    kind: Literal["sdist", "wheel"]
    artifact: EvidenceReference
    inventory: EvidenceReference
    status: STATUS
    reason_codes: list[str]

    _reasons = field_validator("reason_codes")(_stable_reasons)

    @model_validator(mode="after")
    def status_is_honest(self) -> "PackageEvidence":
        if self.status == "PASS" and self.reason_codes:
            raise ValueError("package PASS cannot contain failure reasons")
        if self.status != "PASS" and not self.reason_codes:
            raise ValueError("non-PASS package evidence requires a reason code")
        return self


class MachineReport(EvidenceReference):
    kind: Literal["TEST", "PACKAGE", "STATIC_SCAN", "SECRET_SCAN", "CONFORMANCE"]
    status: STATUS
    reason_codes: list[str]

    _reasons = field_validator("reason_codes")(_stable_reasons)

    @model_validator(mode="after")
    def status_is_honest(self) -> "MachineReport":
        if self.status == "PASS" and self.reason_codes:
            raise ValueError("machine-report PASS cannot contain failure reasons")
        if self.status != "PASS" and not self.reason_codes:
            raise ValueError("non-PASS machine report requires a reason code")
        return self


class ControlFinding(ClosedModel):
    control_id: Literal[
        "PATH_REFERENCE_SAFETY",
        "DNS_ADDRESS_SAFETY",
        "HTTPS_TLS_PROXY_REDIRECT_SAFETY",
        "TLS_AND_TRANSPORT_FAILURES",
        "CREDENTIAL_AND_ERROR_SECRECY",
        "RECORD_AND_RESPONSE_CANONICALITY",
        "CROSS_BINDING_AND_SUBSTITUTION",
        "TRUST_REVOCATION_AND_IDM_PIN",
        "INITIAL_SEND_AND_RECOVERY_CONCURRENCY",
        "PARTIAL_STATE_AND_RECONCILIATION",
        "AMBIGUOUS_REPLAY_CEILING",
        "SECRET_SENTINEL_ABSENCE",
        "LEGACY_DORMANT_COMPATIBILITY",
        "PROHIBITED_CAPABILITY_ABSENCE",
    ]
    status: STATUS
    evidence: list[EvidenceReference] = Field(min_length=1)
    reason_codes: list[str]

    _reasons = field_validator("reason_codes")(_stable_reasons)

    @model_validator(mode="after")
    def status_is_honest(self) -> "ControlFinding":
        references = [item.reference for item in self.evidence]
        if references != sorted(set(references)):
            raise ValueError("finding evidence references must be unique and sorted")
        if self.status == "PASS" and self.reason_codes:
            raise ValueError("finding PASS cannot contain failure reasons")
        if self.status != "PASS" and not self.reason_codes:
            raise ValueError("non-PASS finding requires a reason code")
        return self


class SandboxBrokerConformanceReport(HashedRecord):
    profile: Literal["sandbox-broker-conformance-report"] = "sandbox-broker-conformance-report"
    schema_version: Literal["sandbox-broker-conformance-report/0.1.0"] = CONFORMANCE_SCHEMA
    conclave_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    conclave_tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    protocol_documents: list[ProtocolEvidence]
    idm_pin_document: EvidenceReference
    idm_implementation: IDMImplementationPin
    platform_evidence: list[PlatformEvidence]
    package_evidence: list[PackageEvidence]
    dependency_and_workflow_evidence: list[EvidenceReference] = Field(min_length=1)
    machine_reports: list[MachineReport]
    findings: list[ControlFinding]
    overall_status: Literal["PASS", "FAIL", "INCOMPLETE"]
    live_sandbox_exercised: Literal[False] = False
    production_ready: Literal[False] = False
    production_use_allowed: Literal[False] = False
    authority_effect: Literal["none"] = "none"
    decision_effect: Literal["none"] = "none"
    membership_effect: Literal["none"] = "none"
    action_execution_allowed: Literal[False] = False
    created_at: str
    time_source_classification: Literal["diagnostic-local"] = "diagnostic-local"

    _created = field_validator("created_at")(_timestamp)

    @model_validator(mode="after")
    def complete_and_consistent(self) -> "SandboxBrokerConformanceReport":
        if not self.idm_implementation.is_frozen_baseline():
            raise ValueError("conformance report must bind the frozen IDM implementation")
        if tuple(item.increment for item in self.protocol_documents) != REQUIRED_PROTOCOLS:
            raise ValueError("protocol evidence must contain ordered 20A through 20D exactly")
        if tuple((item.os, item.python_version) for item in self.platform_evidence) != REQUIRED_PLATFORMS:
            raise ValueError("platform evidence must contain the frozen matrix exactly")
        if tuple(item.kind for item in self.package_evidence) != ("sdist", "wheel"):
            raise ValueError("package evidence must contain ordered sdist and wheel exactly")
        kinds = {item.kind for item in self.machine_reports}
        if not set(REQUIRED_REPORT_KINDS).issubset(kinds):
            raise ValueError("required machine-report classes are missing")
        if tuple(item.control_id for item in self.findings) != REQUIRED_CONTROLS:
            raise ValueError("findings must contain the frozen control matrix exactly")
        dep_refs = [item.reference for item in self.dependency_and_workflow_evidence]
        if dep_refs != sorted(set(dep_refs)):
            raise ValueError("dependency/workflow evidence must be unique and sorted")
        machine_keys = [(item.kind, item.reference) for item in self.machine_reports]
        if machine_keys != sorted(set(machine_keys)):
            raise ValueError("machine reports must be unique and sorted by kind/reference")

        statuses = (
            [item.status for item in self.platform_evidence]
            + [item.status for item in self.package_evidence]
            + [item.status for item in self.machine_reports]
            + [item.status for item in self.findings]
        )
        expected = "FAIL" if "FAIL" in statuses else "INCOMPLETE" if "NOT_RUN" in statuses else "PASS"
        if self.overall_status != expected:
            raise ValueError(f"overall_status must be {expected} for the supplied evidence")
        return self


def create_conformance_report(
    ws: Workspace, data: dict, *, record_ledger: bool = True
) -> tuple[SandboxBrokerConformanceReport, Path, bool]:
    """Validate, seal and immutably retain one factual conformance report."""
    report = seal_record(SandboxBrokerConformanceReport, data)
    digest = report.content_hash.split(":", 1)[1]
    path, created = write_immutable_record(
        ws.signing_conformance_reports_dir / f"conformance-{digest}.json", report
    )
    if record_ledger:
        record_event(
            ws,
            event_type="sandbox_broker_conformance_report_recorded",
            actor="conclave",
            authority_level="system",
            subject_refs=[],
            artifact_hashes={"sandbox_broker_conformance_report": report.content_hash},
            payload={
                "status": report.overall_status,
                "report_reference": path.relative_to(ws.root).as_posix(),
                "production_ready": False,
                "production_use_allowed": False,
                "authority_effect": "none",
                "decision_effect": "none",
                "membership_effect": "none",
                "action_execution_allowed": False,
                "note": "factual conformance evidence only; no approval or production authority inferred",
            },
            occurred_at=report.created_at,
        )
    return report, path, created


def read_conformance_report(path: Path) -> SandboxBrokerConformanceReport:
    try:
        record = read_record(path, SandboxBrokerConformanceReport)
    except Exception as exc:
        raise ValidationError("CONFORMANCE_REPORT_INVALID") from exc
    expected = f"conformance-{record.content_hash.split(':', 1)[1]}.json"
    if path.name != expected:
        raise ValidationError("CONFORMANCE_REPORT_FILENAME_MISMATCH")
    return record
