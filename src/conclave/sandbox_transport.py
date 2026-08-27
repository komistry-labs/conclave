"""Increment 20B dormant, sandbox-only evidence-broker transport boundary."""

from __future__ import annotations

import base64
import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Literal, Protocol
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator

from .configuration import (
    EVIDENCE_CONTEXT,
    BrokerTransportProfile,
    IDMVerifierProfile,
    _canonical_reference,
    _digest_filename,
    _read_content_addressed,
    _safe_record_path,
    read_broker_profile,
    read_verifier_profile,
)
from .errors import IntegrityError, ValidationError
from .evidence import (
    EvidenceImportOutcome,
    EvidenceSigningRequest,
    IDMEvidenceVerifier,
    _safe_stored_record,
    import_evidence_envelope,
    resolve_stored_artifact,
    verified_workspace_id,
)
from .hashing import hash_bytes
from .identity import HashedRecord, TrustInputSet, read_record, seal_record, sha256_bytes, write_immutable_record
from .ledger import exclusive_lock, record_event
from .workspace import Workspace, utcnow

ENDPOINT_SCHEMA = "sandbox-broker-endpoint/0.1.0"
AUTHORIZATION_SCHEMA = "broker-egress-authorization/0.1.0"
ATTEMPT_SCHEMA = "sandbox-broker-attempt/0.1.0"
RECEIPT_SCHEMA = "sandbox-broker-transport-receipt/0.1.0"
REQUEST_MEDIA_TYPE = "application/vnd.conclave.evidence-request+json;version=1"
RESPONSE_MEDIA_TYPE = 'application/cose; cose-type="cose-sign1"'
MAX_REQUEST_BYTES = 8 * 1024 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_CREDENTIAL_BYTES = 8 * 1024
SAFE_ID = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
SAFE_PATH = re.compile(r"^/[A-Za-z0-9._~/-]+$")
REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


def _timestamp(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError("timestamp must be valid second-precision UTC RFC 3339") from exc
    return value


def _dt(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _safe_id(value: str) -> str:
    if SAFE_ID.fullmatch(value) is None:
        raise ValueError("identifier must use the frozen safe-label grammar")
    return value


def _safe_origin(value: str) -> str:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("sandbox origin is malformed") from exc
    host = parsed.hostname
    if (
        parsed.scheme != "https" or host is None or host != host.lower()
        or parsed.username is not None or parsed.password is not None
        or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
    ):
        raise ValueError("sandbox origin must be a canonical HTTPS origin")
    try:
        host.encode("ascii")
        ipaddress.ip_address(host)
    except UnicodeEncodeError as exc:
        raise ValueError("sandbox origin host must be ASCII") from exc
    except ValueError:
        pass
    else:
        raise ValueError("sandbox origin must not use an IP literal")
    labels = host.split(".")
    if (
        "*" in host
        or len(host) > 253
        or len(labels) < 2
        or any(
            not label or len(label) > 63
            or re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label) is None
            for label in labels
        )
        or port == 443
        or port is not None and not 1 <= port <= 65535
    ):
        raise ValueError("sandbox origin host or port is invalid")
    expected = f"https://{host}" + (f":{port}" if port is not None else "")
    if value.rstrip("/") != expected:
        raise ValueError("sandbox origin is not canonical")
    return expected


def _safe_request_path(value: str) -> str:
    segments = value.split("/")
    if (
        SAFE_PATH.fullmatch(value) is None
        or "//" in value
        or any(segment in {".", ".."} for segment in segments)
    ):
        raise ValueError("sandbox request path is not canonical")
    return value


class SandboxBrokerEndpoint(HashedRecord):
    profile: Literal["sandbox-broker-endpoint"] = "sandbox-broker-endpoint"
    schema_version: Literal["sandbox-broker-endpoint/0.1.0"] = ENDPOINT_SCHEMA
    endpoint_id: str
    broker_profile_reference: str
    broker_profile_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    origin: str
    request_path: str
    authentication_scheme: Literal["bearer-env-v1"] = "bearer-env-v1"
    credential_reference: str = Field(pattern=r"^env:[A-Z][A-Z0-9_]{0,127}$")
    tls_policy: Literal["system-ca-hostname-tls12-plus"] = "system-ca-hostname-tls12-plus"
    maximum_request_bytes: int = Field(ge=1, le=MAX_REQUEST_BYTES)
    maximum_response_bytes: int = Field(ge=1, le=MAX_RESPONSE_BYTES)
    connect_timeout_seconds: int = Field(ge=1, le=15)
    total_timeout_seconds: int = Field(ge=1, le=60)
    created_by: str = Field(min_length=1, max_length=256)
    created_at: str
    environment: Literal["sandbox"] = "sandbox"
    authority_effect: Literal["none"] = "none"
    decision_effect: Literal["none"] = "none"
    membership_effect: Literal["none"] = "none"
    action_execution_allowed: Literal[False] = False

    _id = field_validator("endpoint_id")(_safe_id)
    _origin = field_validator("origin")(_safe_origin)
    _path = field_validator("request_path")(_safe_request_path)
    _time = field_validator("created_at")(_timestamp)

    @field_validator("broker_profile_reference")
    @classmethod
    def broker_ref(cls, value: str) -> str:
        return _canonical_reference(value, ("signing", "broker-profiles"))


class BrokerEgressAuthorization(HashedRecord):
    profile: Literal["broker-egress-authorization"] = "broker-egress-authorization"
    schema_version: Literal["broker-egress-authorization/0.1.0"] = AUTHORIZATION_SCHEMA
    endpoint_reference: str
    endpoint_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    verifier_profile_reference: str
    verifier_profile_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    trust_input_reference: str
    trust_input_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    signing_request_reference: str
    signing_request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    artifact_storage_reference: str
    artifact_schema: str
    artifact_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    canonical_payload_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evidence_context: Literal["conclave-evidence/1.0"] = EVIDENCE_CONTEXT
    transmitted_classification: Literal["public", "internal"]
    principal_reviewed_for_secrets: Literal[True] = True
    purpose: str = Field(min_length=1, max_length=512)
    authorized_principal: str = Field(min_length=1, max_length=256)
    issued_at: str
    expires_at: str
    maximum_attempts: Literal[1] = 1
    environment: Literal["sandbox"] = "sandbox"
    production_use_allowed: Literal[False] = False
    authority_effect: Literal["broker_egress_only"] = "broker_egress_only"
    decision_effect: Literal["none"] = "none"
    membership_effect: Literal["none"] = "none"
    action_execution_allowed: Literal[False] = False

    _issued = field_validator("issued_at")(_timestamp)
    _expires = field_validator("expires_at")(_timestamp)

    @model_validator(mode="after")
    def ordered_times(self) -> "BrokerEgressAuthorization":
        if _dt(self.expires_at) <= _dt(self.issued_at):
            raise ValueError("authorization expiry must follow issuance")
        return self

    @field_validator("endpoint_reference")
    @classmethod
    def endpoint_ref(cls, value: str) -> str:
        return _canonical_reference(value, ("signing", "broker-endpoints"))

    @field_validator("verifier_profile_reference")
    @classmethod
    def verifier_ref(cls, value: str) -> str:
        return _canonical_reference(value, ("identity", "verifier-profiles"))

    @field_validator("trust_input_reference")
    @classmethod
    def trust_ref(cls, value: str) -> str:
        return _canonical_reference(value, ("identity", "trust-inputs"))

    @field_validator("signing_request_reference")
    @classmethod
    def request_ref(cls, value: str) -> str:
        return _canonical_reference(value, ("signing", "requests"))


class SandboxBrokerAttempt(HashedRecord):
    profile: Literal["sandbox-broker-attempt"] = "sandbox-broker-attempt"
    schema_version: Literal["sandbox-broker-attempt/0.1.0"] = ATTEMPT_SCHEMA
    attempt_id: str = Field(pattern=r"^attempt:sha256:[0-9a-f]{64}$")
    endpoint_reference: str
    endpoint_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    broker_profile_reference: str
    broker_profile_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    authorization_reference: str
    authorization_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    verifier_profile_reference: str
    verifier_profile_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    trust_input_reference: str
    trust_input_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    signing_request_reference: str
    signing_request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    artifact_storage_reference: str
    artifact_schema: str
    artifact_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    canonical_payload_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    request_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    request_body_bytes: int = Field(ge=1, le=MAX_REQUEST_BYTES)
    created_at: str
    time_source_classification: Literal["diagnostic-local"] = "diagnostic-local"
    state: Literal["PREPARED"] = "PREPARED"
    maximum_transmissions: Literal[1] = 1
    authority_effect: Literal["none"] = "none"
    decision_effect: Literal["none"] = "none"
    membership_effect: Literal["none"] = "none"
    action_execution_allowed: Literal[False] = False

    _time = field_validator("created_at")(_timestamp)


class SandboxBrokerTransportReceipt(HashedRecord):
    profile: Literal["sandbox-broker-transport-receipt"] = "sandbox-broker-transport-receipt"
    schema_version: Literal["sandbox-broker-transport-receipt/0.1.0"] = RECEIPT_SCHEMA
    attempt_reference: str
    attempt_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    attempt_id: str = Field(pattern=r"^attempt:sha256:[0-9a-f]{64}$")
    endpoint_reference: str
    endpoint_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    broker_profile_reference: str
    broker_profile_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    authorization_reference: str
    authorization_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    verifier_profile_reference: str
    verifier_profile_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    trust_input_reference: str
    trust_input_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    signing_request_reference: str
    signing_request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    artifact_storage_reference: str
    artifact_schema: str
    artifact_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    canonical_payload_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    started_at: str
    finished_at: str
    time_source_classification: Literal["diagnostic-local"] = "diagnostic-local"
    outcome: Literal["NOT_SENT", "SENT_NO_RESPONSE", "RESPONSE_REJECTED", "RESPONSE_ACCEPTED_FOR_VERIFICATION"]
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
    credential_reference: str = Field(pattern=r"^env:[A-Z][A-Z0-9_]{0,127}$")
    authority_effect: Literal["none"] = "none"
    decision_effect: Literal["none"] = "none"
    membership_effect: Literal["none"] = "none"
    action_execution_allowed: Literal[False] = False

    _started = field_validator("started_at")(_timestamp)
    _finished = field_validator("finished_at")(_timestamp)

    @field_validator("reason_codes")
    @classmethod
    def stable_reasons(cls, value: list[str]) -> list[str]:
        if value != sorted(set(value)) or any(REASON.fullmatch(item) is None for item in value):
            raise ValueError("reason codes must be unique sorted stable codes")
        return value


class CredentialResolver(Protocol):
    def resolve(self, selector: str) -> str: ...


class EnvironmentCredentialResolver:
    def resolve(self, selector: str) -> str:
        name = selector.removeprefix("env:")
        if selector != f"env:{name}" or re.fullmatch(r"[A-Z][A-Z0-9_]{0,127}", name) is None:
            raise ValidationError("CREDENTIAL_SELECTOR_INVALID")
        value = os.environ.get(name)
        if value is None:
            raise ValidationError("CREDENTIAL_MISSING")
        return _validate_credential(value)


def _validate_credential(value: str) -> str:
    try:
        encoded = value.encode("utf-8")
    except (AttributeError, UnicodeEncodeError) as exc:
        raise ValidationError("CREDENTIAL_MALFORMED") from exc
    if (
        not value or len(encoded) > MAX_CREDENTIAL_BYTES or value != value.strip()
        or any(ord(char) < 0x20 or ord(char) == 0x7F for char in value)
    ):
        raise ValidationError("CREDENTIAL_MALFORMED")
    return value


@dataclass(frozen=True)
class TransportResponse:
    status: int
    content_type: str
    body: bytes


class SandboxBrokerTransport(Protocol):
    def send(
        self, *, endpoint: SandboxBrokerEndpoint, body: bytes,
        credential: str, idempotency_key: str,
    ) -> TransportResponse: ...


class SandboxTransportFailure(Exception):
    def __init__(self, code: str, *, sent: bool):
        super().__init__(code)
        self.code = code
        self.sent = sent


def _public_addresses(host: str, port: int) -> list[str]:
    try:
        values = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise SandboxTransportFailure("DNS_RESOLUTION_FAILED", sent=False) from exc
    addresses = sorted({item[4][0] for item in values})
    if not addresses:
        raise SandboxTransportFailure("DNS_RESOLUTION_FAILED", sent=False)
    for value in addresses:
        try:
            address = ipaddress.ip_address(value)
        except ValueError as exc:
            raise SandboxTransportFailure("DNS_RESPONSE_INVALID", sent=False) from exc
        if (
            not address.is_global
            or address.is_multicast
            or address.is_unspecified
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
            or address.is_private
            or (
            isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None
            )
        ):
            raise SandboxTransportFailure("DESTINATION_ADDRESS_NOT_PUBLIC", sent=False)
    return addresses


class HttpsSandboxBrokerTransport:
    """One request, no redirect/proxy/cookie support, exact bounded response."""

    def send(
        self, *, endpoint: SandboxBrokerEndpoint, body: bytes,
        credential: str, idempotency_key: str,
    ) -> TransportResponse:
        parsed = urlsplit(endpoint.origin)
        host = parsed.hostname or ""
        port = parsed.port or 443
        address = _public_addresses(host, port)[0]
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        connection = http.client.HTTPSConnection(host, port, timeout=endpoint.total_timeout_seconds,
                                                  context=context)
        sent = False
        try:
            raw = socket.create_connection((address, port), timeout=endpoint.connect_timeout_seconds)
            connection.sock = context.wrap_socket(raw, server_hostname=host)
            connection.sock.settimeout(endpoint.total_timeout_seconds)
            headers = {
                "Content-Type": REQUEST_MEDIA_TYPE,
                "Accept": RESPONSE_MEDIA_TYPE,
                "Authorization": f"Bearer {credential}",
                "Idempotency-Key": idempotency_key,
                "User-Agent": "conclave-sandbox-transport/0.1",
            }
            sent = True
            connection.request("POST", endpoint.request_path, body=body, headers=headers)
            response = connection.getresponse()
            payload = response.read(endpoint.maximum_response_bytes + 1)
            return TransportResponse(
                status=response.status,
                content_type=response.getheader("Content-Type", ""),
                body=payload,
            )
        except ssl.SSLError as exc:
            raise SandboxTransportFailure("TLS_FAILURE", sent=sent) from exc
        except (TimeoutError, socket.timeout) as exc:
            raise SandboxTransportFailure("TRANSPORT_TIMEOUT", sent=sent) from exc
        except (OSError, http.client.HTTPException) as exc:
            raise SandboxTransportFailure("TRANSPORT_ERROR", sent=sent) from exc
        finally:
            connection.close()


@dataclass(frozen=True)
class SandboxExecutionOutcome:
    attempt: SandboxBrokerAttempt
    attempt_path: Path
    receipt: SandboxBrokerTransportReceipt
    receipt_path: Path
    evidence: EvidenceImportOutcome | None


def _reference(ws: Workspace, path: Path) -> str:
    return path.relative_to(ws.root).as_posix()


def _read_named(ws: Workspace, reference: str, area: Path, parts: tuple[str, ...],
                model: type[HashedRecord], prefix: str) -> HashedRecord:
    path = _safe_record_path(ws, reference, area, parts)
    return _read_content_addressed(path, model, prefix)


def create_sandbox_endpoint(
    ws: Workspace, *, endpoint_id: str, broker_profile_reference: str,
    origin: str, request_path: str, created_by: str,
    maximum_request_bytes: int = MAX_REQUEST_BYTES,
    maximum_response_bytes: int = MAX_RESPONSE_BYTES,
    connect_timeout_seconds: int = 10, total_timeout_seconds: int = 30,
    created_at: str | None = None,
) -> tuple[SandboxBrokerEndpoint, Path, bool]:
    broker = read_broker_profile(ws, broker_profile_reference)
    if broker.classification != "sandbox":
        raise ValidationError("endpoint requires a sandbox broker profile")
    record = seal_record(SandboxBrokerEndpoint, {
        "profile": "sandbox-broker-endpoint", "schema_version": ENDPOINT_SCHEMA,
        "endpoint_id": endpoint_id, "broker_profile_reference": broker_profile_reference,
        "broker_profile_hash": broker.content_hash, "origin": origin,
        "request_path": request_path, "authentication_scheme": "bearer-env-v1",
        "credential_reference": broker.credential_reference,
        "tls_policy": "system-ca-hostname-tls12-plus",
        "maximum_request_bytes": maximum_request_bytes,
        "maximum_response_bytes": maximum_response_bytes,
        "connect_timeout_seconds": connect_timeout_seconds,
        "total_timeout_seconds": total_timeout_seconds,
        "created_by": created_by, "created_at": created_at or utcnow(),
        "environment": "sandbox", "authority_effect": "none", "decision_effect": "none",
        "membership_effect": "none", "action_execution_allowed": False,
    })
    return record, *write_immutable_record(
        ws.signing_broker_endpoints_dir / _digest_filename("endpoint", record), record
    )


def read_sandbox_endpoint(ws: Workspace, reference: str) -> SandboxBrokerEndpoint:
    record = _read_named(ws, reference, ws.signing_broker_endpoints_dir,
                         ("signing", "broker-endpoints"), SandboxBrokerEndpoint, "endpoint")
    broker = read_broker_profile(ws, record.broker_profile_reference)
    if broker.content_hash != record.broker_profile_hash or broker.classification != "sandbox":
        raise IntegrityError("endpoint broker-profile binding mismatch")
    if broker.credential_reference != record.credential_reference:
        raise IntegrityError("endpoint credential-selector binding mismatch")
    return record  # type: ignore[return-value]


def _read_request(ws: Workspace, reference: str) -> tuple[EvidenceSigningRequest, Path]:
    path = _safe_record_path(ws, reference, ws.signing_requests_dir, ("signing", "requests"))
    return read_record(path, EvidenceSigningRequest), path


def _read_trust(ws: Workspace, reference: str) -> tuple[TrustInputSet, Path]:
    path = _safe_record_path(ws, reference, ws.identity_trust_inputs_dir,
                             ("identity", "trust-inputs"))
    return read_record(path, TrustInputSet), path


def create_broker_authorization(
    ws: Workspace, *, endpoint_reference: str, signing_request_reference: str,
    trust_input_reference: str, transmitted_classification: str, purpose: str,
    principal_reviewed_for_secrets: bool, confirmed_principal: str,
    issued_at: str, expires_at: str,
) -> tuple[BrokerEgressAuthorization, Path, bool]:
    verified_workspace_id(ws)
    principal = ws.load_config().get("principal")
    if not principal or confirmed_principal != principal:
        raise ValidationError("broker authorization requires the exact workspace principal")
    if principal_reviewed_for_secrets is not True:
        raise ValidationError("broker authorization requires explicit secret-review confirmation")
    endpoint = read_sandbox_endpoint(ws, endpoint_reference)
    broker = read_broker_profile(ws, endpoint.broker_profile_reference)
    verifier = read_verifier_profile(ws, broker.verifier_profile_reference)
    trust, _ = _read_trust(ws, trust_input_reference)
    if verifier.expected_trust_input_reference != trust_input_reference:
        raise ValidationError("verifier profile expected-trust reference mismatch")
    if not trust.idm_implementation.is_frozen_baseline() or trust.trust_domain_id != verifier.expected_trust_domain_id:
        raise ValidationError("trust input differs from verifier profile or frozen IDM baseline")
    request, _ = _read_request(ws, signing_request_reference)
    artifact = resolve_stored_artifact(
        ws, storage_reference=request.artifact_storage_reference,
        artifact_schema=request.artifact_schema,
    )
    if artifact.content_hash != request.artifact_content_hash or artifact.payload_hash != request.canonical_payload_hash:
        raise ValidationError("signing request artifact binding mismatch")
    record = seal_record(BrokerEgressAuthorization, {
        "profile": "broker-egress-authorization", "schema_version": AUTHORIZATION_SCHEMA,
        "endpoint_reference": endpoint_reference, "endpoint_hash": endpoint.content_hash,
        "verifier_profile_reference": broker.verifier_profile_reference,
        "verifier_profile_hash": verifier.content_hash,
        "trust_input_reference": trust_input_reference, "trust_input_hash": trust.content_hash,
        "signing_request_reference": signing_request_reference,
        "signing_request_hash": request.content_hash,
        "artifact_storage_reference": request.artifact_storage_reference,
        "artifact_schema": request.artifact_schema,
        "artifact_content_hash": request.artifact_content_hash,
        "canonical_payload_hash": request.canonical_payload_hash,
        "evidence_context": EVIDENCE_CONTEXT,
        "transmitted_classification": transmitted_classification,
        "principal_reviewed_for_secrets": principal_reviewed_for_secrets, "purpose": purpose,
        "authorized_principal": principal, "issued_at": issued_at, "expires_at": expires_at,
        "maximum_attempts": 1, "environment": "sandbox", "production_use_allowed": False,
        "authority_effect": "broker_egress_only", "decision_effect": "none",
        "membership_effect": "none", "action_execution_allowed": False,
    })
    return record, *write_immutable_record(
        ws.signing_broker_authorizations_dir / _digest_filename("authorization", record), record
    )


def read_broker_authorization(ws: Workspace, reference: str) -> BrokerEgressAuthorization:
    return _read_named(ws, reference, ws.signing_broker_authorizations_dir,
                       ("signing", "broker-authorizations"),
                       BrokerEgressAuthorization, "authorization")  # type: ignore[return-value]


def read_sandbox_attempt(path: Path) -> SandboxBrokerAttempt:
    return _read_content_addressed(path, SandboxBrokerAttempt, "attempt")  # type: ignore[return-value]


def read_sandbox_receipt(path: Path) -> SandboxBrokerTransportReceipt:
    return _read_content_addressed(path, SandboxBrokerTransportReceipt, "receipt")  # type: ignore[return-value]


def _artifact_bytes(ws: Workspace, request: EvidenceSigningRequest) -> bytes:
    artifact = resolve_stored_artifact(
        ws, storage_reference=request.artifact_storage_reference,
        artifact_schema=request.artifact_schema,
    )
    path = ws.root.joinpath(*PurePosixPath(request.artifact_storage_reference).parts)
    raw = path.read_bytes()
    if len(raw) < 1 or len(raw) > 4 * 1024 * 1024:
        raise ValidationError("artifact size is outside the evidence limit")
    if artifact.content_hash != request.artifact_content_hash or hash_bytes(raw) != request.canonical_payload_hash:
        raise ValidationError("artifact bytes do not match the signing request")
    return raw


def _wire_body(request: EvidenceSigningRequest, artifact: bytes) -> bytes:
    encoded = base64.urlsafe_b64encode(artifact).decode("ascii").rstrip("=")
    value = {
        "artifact_base64url": encoded,
        "artifact_bytes": len(artifact),
        "artifact_schema": request.artifact_schema,
        "artifact_sha256": sha256_bytes(artifact),
        "signing_request": request.model_dump(mode="json"),
    }
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _attempt_identity(endpoint: SandboxBrokerEndpoint, authorization: BrokerEgressAuthorization,
                      request: EvidenceSigningRequest, body: bytes) -> str:
    material = json.dumps({
        "endpoint_hash": endpoint.content_hash,
        "authorization_hash": authorization.content_hash,
        "signing_request_hash": request.content_hash,
        "request_body_hash": sha256_bytes(body),
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "attempt:sha256:" + sha256_bytes(material).split(":", 1)[1]


def _receipt_data(
    *, attempt: SandboxBrokerAttempt, attempt_ref: str, endpoint: SandboxBrokerEndpoint,
    authorization: BrokerEgressAuthorization, started_at: str, finished_at: str,
    outcome: str, reasons: list[str], status_class: str, response: bytes | None,
    evidence: EvidenceImportOutcome | None,
) -> dict:
    return {
        "profile": "sandbox-broker-transport-receipt", "schema_version": RECEIPT_SCHEMA,
        "attempt_reference": attempt_ref, "attempt_hash": attempt.content_hash,
        "attempt_id": attempt.attempt_id,
        "endpoint_reference": attempt.endpoint_reference, "endpoint_hash": endpoint.content_hash,
        "broker_profile_reference": attempt.broker_profile_reference,
        "broker_profile_hash": attempt.broker_profile_hash,
        "authorization_reference": attempt.authorization_reference,
        "authorization_hash": authorization.content_hash,
        "verifier_profile_reference": attempt.verifier_profile_reference,
        "verifier_profile_hash": attempt.verifier_profile_hash,
        "trust_input_reference": attempt.trust_input_reference,
        "trust_input_hash": attempt.trust_input_hash,
        "signing_request_reference": attempt.signing_request_reference,
        "signing_request_hash": attempt.signing_request_hash,
        "artifact_storage_reference": attempt.artifact_storage_reference,
        "artifact_schema": attempt.artifact_schema,
        "artifact_content_hash": attempt.artifact_content_hash,
        "canonical_payload_hash": attempt.canonical_payload_hash,
        "started_at": started_at, "finished_at": finished_at,
        "time_source_classification": "diagnostic-local", "outcome": outcome,
        "reason_codes": sorted(set(reasons)),
        "request_body_hash": attempt.request_body_hash,
        "request_body_bytes": attempt.request_body_bytes,
        "response_body_hash": sha256_bytes(response) if response is not None else None,
        "response_body_bytes": len(response) if response is not None else None,
        "http_status_class": status_class,
        "envelope_storage_reference": None,
        "envelope_hash": evidence.binding.envelope_hash if evidence else None,
        "evidence_binding_reference": None,
        "evidence_binding_hash": evidence.binding.content_hash if evidence else None,
        "verification_status": evidence.binding.verification_status if evidence else "NOT_RUN",
        "credential_reference": endpoint.credential_reference,
        "authority_effect": "none", "decision_effect": "none",
        "membership_effect": "none", "action_execution_allowed": False,
    }


def execute_sandbox_transport(
    ws: Workspace, *, endpoint_reference: str, authorization_reference: str,
    transport: SandboxBrokerTransport, credential_resolver: CredentialResolver,
    public_evidence: dict[str, bytes], verifier: IDMEvidenceVerifier,
    now: str | None = None,
) -> SandboxExecutionOutcome:
    verified_workspace_id(ws)
    endpoint = read_sandbox_endpoint(ws, endpoint_reference)
    broker = read_broker_profile(ws, endpoint.broker_profile_reference)
    verifier_profile = read_verifier_profile(ws, broker.verifier_profile_reference)
    authorization = read_broker_authorization(ws, authorization_reference)
    request, request_path = _read_request(ws, authorization.signing_request_reference)
    trust, trust_path = _read_trust(ws, authorization.trust_input_reference)
    current = now or utcnow()
    _timestamp(current)
    checks = (
        authorization.endpoint_reference == endpoint_reference,
        authorization.endpoint_hash == endpoint.content_hash,
        authorization.verifier_profile_reference == broker.verifier_profile_reference,
        authorization.verifier_profile_hash == verifier_profile.content_hash,
        authorization.trust_input_hash == trust.content_hash,
        verifier_profile.expected_trust_input_reference == authorization.trust_input_reference,
        verifier_profile.expected_trust_domain_id == trust.trust_domain_id,
        trust.idm_implementation.is_frozen_baseline(),
        authorization.signing_request_hash == request.content_hash,
        authorization.artifact_storage_reference == request.artifact_storage_reference,
        authorization.artifact_schema == request.artifact_schema,
        authorization.artifact_content_hash == request.artifact_content_hash,
        authorization.canonical_payload_hash == request.canonical_payload_hash,
        authorization.authorized_principal == ws.load_config().get("principal"),
        _dt(authorization.issued_at) <= _dt(current) < _dt(authorization.expires_at),
    )
    if not all(checks):
        raise ValidationError("sandbox transport authorization binding is invalid or expired")
    artifact = _artifact_bytes(ws, request)
    body = _wire_body(request, artifact)
    if len(body) > endpoint.maximum_request_bytes:
        raise ValidationError("sandbox request body exceeds endpoint limit")
    attempt_id = _attempt_identity(endpoint, authorization, request, body)
    digest = attempt_id.rsplit(":", 1)[1]
    lock_path = ws.signing_broker_attempts_dir / f"attempt-{digest}"
    with exclusive_lock(lock_path):
        for prior_path in ws.signing_broker_attempts_dir.glob("*.json"):
            try:
                prior = read_sandbox_attempt(prior_path)
            except Exception as exc:
                raise ValidationError("ATTEMPT_STORE_INVALID") from exc
            if prior.attempt_id == attempt_id:
                raise ValidationError("ATTEMPT_OUTCOME_UNKNOWN")
        attempt = seal_record(SandboxBrokerAttempt, {
            "profile": "sandbox-broker-attempt", "schema_version": ATTEMPT_SCHEMA,
            "attempt_id": attempt_id, "endpoint_reference": endpoint_reference,
            "endpoint_hash": endpoint.content_hash,
            "broker_profile_reference": endpoint.broker_profile_reference,
            "broker_profile_hash": broker.content_hash,
            "authorization_reference": authorization_reference,
            "authorization_hash": authorization.content_hash,
            "verifier_profile_reference": broker.verifier_profile_reference,
            "verifier_profile_hash": verifier_profile.content_hash,
            "trust_input_reference": authorization.trust_input_reference,
            "trust_input_hash": trust.content_hash,
            "signing_request_reference": authorization.signing_request_reference,
            "signing_request_hash": request.content_hash,
            "artifact_storage_reference": request.artifact_storage_reference,
            "artifact_schema": request.artifact_schema,
            "artifact_content_hash": request.artifact_content_hash,
            "canonical_payload_hash": request.canonical_payload_hash,
            "request_body_hash": sha256_bytes(body), "request_body_bytes": len(body),
            "created_at": current, "time_source_classification": "diagnostic-local",
            "state": "PREPARED", "maximum_transmissions": 1,
            "authority_effect": "none", "decision_effect": "none",
            "membership_effect": "none", "action_execution_allowed": False,
        })
        attempt_path = ws.signing_broker_attempts_dir / _digest_filename("attempt", attempt)
        write_immutable_record(attempt_path, attempt)
        started_at = current
        response_bytes: bytes | None = None
        evidence_outcome: EvidenceImportOutcome | None = None
        status_class = "none"
        reasons: list[str] = []
        outcome = "NOT_SENT"
        phase = "credential"
        try:
            credential = _validate_credential(
                credential_resolver.resolve(endpoint.credential_reference)
            )
            phase = "transport"
            response = transport.send(
                endpoint=endpoint, body=body, credential=credential,
                idempotency_key=digest,
            )
            phase = "response"
            if (
                type(response.status) is not int
                or not isinstance(response.content_type, str)
                or not isinstance(response.body, bytes)
            ):
                raise ValidationError("TRANSPORT_RESPONSE_INVALID")
            if len(response.body) > endpoint.maximum_response_bytes + 1:
                raise ValidationError("TRANSPORT_RESPONSE_BOUND_VIOLATION")
            response_bytes = response.body
            status_class = f"{response.status // 100}xx" if 100 <= response.status <= 599 else "none"
            if len(response.body) > endpoint.maximum_response_bytes:
                outcome, reasons = "RESPONSE_REJECTED", ["RESPONSE_TOO_LARGE"]
            elif not 200 <= response.status < 300:
                outcome, reasons = "RESPONSE_REJECTED", ["HTTP_RESPONSE_REJECTED"]
            elif response.content_type.lower() != RESPONSE_MEDIA_TYPE:
                outcome, reasons = "RESPONSE_REJECTED", ["RESPONSE_MEDIA_TYPE_INVALID"]
            elif not response.body:
                outcome, reasons = "RESPONSE_REJECTED", ["RESPONSE_EMPTY"]
            else:
                phase = "import"
                evidence_outcome = import_evidence_envelope(
                    ws, request_path=request_path, trust_input_path=trust_path,
                    envelope=response.body, public_evidence=public_evidence, verifier=verifier,
                )
                outcome = "RESPONSE_ACCEPTED_FOR_VERIFICATION"
                if evidence_outcome.binding.verification_status == "FAIL":
                    reasons.append("EVIDENCE_VERIFICATION_FAILED")
                if evidence_outcome.conflict:
                    reasons.append("EVIDENCE_CONFLICT_OBSERVED")
        except SandboxTransportFailure as exc:
            outcome = "SENT_NO_RESPONSE" if exc.sent else "NOT_SENT"
            reasons = [exc.code]
        except ValidationError as exc:
            if phase in {"response", "import"}:
                code = ("EVIDENCE_IMPORT_ERROR" if phase == "import"
                        else str(exc) if REASON.fullmatch(str(exc))
                        else "TRANSPORT_RESPONSE_INVALID")
                outcome = "RESPONSE_REJECTED"
            else:
                code = str(exc) if REASON.fullmatch(str(exc)) else "TRANSPORT_PRECONDITION_FAILED"
            reasons = [code]
        except Exception:
            if phase == "credential":
                outcome, reasons = "NOT_SENT", ["CREDENTIAL_RESOLVER_ERROR"]
            elif phase == "transport":
                outcome, reasons = "SENT_NO_RESPONSE", ["TRANSPORT_ERROR"]
            else:
                outcome, reasons = "RESPONSE_REJECTED", ["EVIDENCE_IMPORT_ERROR"]
        finished_at = now or utcnow()
        attempt_ref = _reference(ws, attempt_path)
        receipt_data = _receipt_data(
            attempt=attempt, attempt_ref=attempt_ref, endpoint=endpoint,
            authorization=authorization, started_at=started_at, finished_at=finished_at,
            outcome=outcome, reasons=reasons, status_class=status_class,
            response=response_bytes, evidence=evidence_outcome,
        )
        if evidence_outcome is not None:
            receipt_data["envelope_storage_reference"] = _reference(ws, evidence_outcome.envelope_path)
            receipt_data["evidence_binding_reference"] = _reference(ws, evidence_outcome.binding_path)
        receipt = seal_record(SandboxBrokerTransportReceipt, receipt_data)
        receipt_path, _ = write_immutable_record(
            ws.signing_broker_receipts_dir / _digest_filename("receipt", receipt), receipt
        )
        record_event(
            ws, event_type="sandbox_broker_transport_attempt_recorded",
            actor="conclave", authority_level="system", subject_refs=[],
            artifact_hashes={"sandbox_broker_attempt": attempt.content_hash,
                             "sandbox_broker_receipt": receipt.content_hash},
            payload={"outcome": receipt.outcome, "reason_codes": receipt.reason_codes,
                     "authority_effect": "none", "decision_effect": "none",
                     "membership_effect": "none", "action_execution_allowed": False},
            occurred_at=finished_at,
        )
        return SandboxExecutionOutcome(attempt, attempt_path, receipt, receipt_path,
                                       evidence_outcome)
