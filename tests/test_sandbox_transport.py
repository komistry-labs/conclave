"""Increment 20B sandbox-only transport acceptance and security tests."""

from __future__ import annotations

import json
import os
import socket
import ssl
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from pydantic import ValidationError as PydanticValidationError

from conclave import ledger
from conclave.configuration import (
    FROZEN_IMPLEMENTATION,
    create_broker_profile,
    create_verifier_profile,
)
from conclave.evidence import (
    EVIDENCE_CONTEXT,
    EVIDENCE_SCOPE,
    SIGNED_PAYLOAD_PROFILE,
    EvidenceVerificationFindings,
    ExpiryPolicy,
    IDMEvidenceVerifierReport,
    SignedEvidencePayload,
    derive_evidence_id,
    prepare_signing_request,
)
from conclave.errors import ValidationError
from conclave.identity import (
    FROZEN_IDM_IMPLEMENTATION,
    PublicEvidenceReference,
    TrustInputSet,
    seal_record,
    sha256_bytes,
    write_immutable_record,
)
from conclave.reconcile import reconcile
from conclave.sandbox_transport import (
    MAX_RESPONSE_BYTES,
    RESPONSE_MEDIA_TYPE,
    BrokerEgressAuthorization,
    EnvironmentCredentialResolver,
    HttpsSandboxBrokerTransport,
    SandboxBrokerEndpoint,
    SandboxTransportFailure,
    TransportResponse,
    _public_addresses,
    create_broker_authorization,
    create_sandbox_endpoint,
    execute_sandbox_transport,
)
from conclave.taskpacket import build_packet, write_packet
from conclave.workspace import Workspace

NOW = "2026-08-26T12:00:00Z"
EID = "eid:" + "a" * 26
MID = "mid:" + "b" * 26
KID = "kid:sha256:" + "A" * 43
TDID = "tdid:" + "c" * 26
TRUST = b'{"public":"sandbox trust"}'
REVOCATION = b"signed sandbox revocation evidence"
TIME = b"trusted sandbox time evidence"
ENVELOPE = b"fixture exact COSE Sign1 bytes"


def _ref(name: str, value: bytes) -> PublicEvidenceReference:
    return PublicEvidenceReference(reference=name, content_hash=sha256_bytes(value))


class FixtureVerifier:
    def __init__(self, payload: SignedEvidencePayload, *, fail: bool = False):
        self.payload = payload
        self.fail = fail

    def verify_evidence(self, *, envelope: bytes, **_kwargs):
        findings = EvidenceVerificationFindings(
            **{name: not self.fail for name in EvidenceVerificationFindings.model_fields}
        )
        return IDMEvidenceVerifierReport(
            implementation=FROZEN_IDM_IMPLEMENTATION,
            evidence_id=derive_evidence_id(envelope), context=EVIDENCE_CONTEXT,
            trust_domain_id=TDID, signer_kid=KID,
            verified_roles=["audit_attester"], verified_scopes=[EVIDENCE_SCOPE],
            payload=self.payload, findings=findings,
            reason_codes=["FIXTURE_REJECTED"] if self.fail else [],
        )


class RecordingResolver:
    def __init__(self, value="disposable-sandbox-token"):
        self.value = value
        self.calls = []

    def resolve(self, selector):
        self.calls.append(selector)
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


class RecordingTransport:
    def __init__(self, response=None, failure=None):
        self.response = response or TransportResponse(200, RESPONSE_MEDIA_TYPE, ENVELOPE)
        self.failure = failure
        self.calls = []

    def send(self, **kwargs):
        self.calls.append(kwargs)
        if self.failure:
            raise self.failure
        return self.response


@pytest.fixture
def prepared(tmp_path):
    ws = Workspace.create(tmp_path, principal="Arthur")
    ledger.initialise(ws, ws.load_config())
    packet = build_packet(objective="sandbox transport fixture", created_by="Arthur")
    packet_path = write_packet(ws, packet)
    request, request_path, _ = prepare_signing_request(
        ws, storage_reference=packet_path.relative_to(ws.root).as_posix(),
        artifact_schema="task-packet/0.1.0", attester_eid=EID, attester_mid=MID,
        attester_role="audit_attester", attester_kid=KID,
        purpose="sandbox attest exact bytes",
        expiry_policy=ExpiryPolicy(expires_at_required=True, maximum_validity_seconds=3600),
        requester_actor_id="Arthur", requester_authority_level="human_principal",
    )
    trust = seal_record(TrustInputSet, {
        "profile": "idm-trust-input-set", "schema_version": "idm-trust-input-set/0.1.0",
        "idm_implementation": FROZEN_IDM_IMPLEMENTATION,
        "trust_bundle": _ref("public/trust", TRUST), "trust_domain_id": TDID,
        "revocation_evidence": [_ref("public/revocation", REVOCATION)],
        "evaluation_time": NOW, "time_source_classification": "trusted",
        "time_evidence": _ref("public/time", TIME),
        "accepted_roles": ["audit_attester"], "required_scopes": [EVIDENCE_SCOPE],
        "created_by": "Arthur", "created_at": NOW,
    })
    trust_path, _ = write_immutable_record(ws.identity_trust_inputs_dir / "sandbox-trust.json", trust)
    trust_ref = trust_path.relative_to(ws.root).as_posix()
    verifier_profile, vp_path, _ = create_verifier_profile(
        ws, profile_id="sandbox-idm", expected_trust_input_reference=trust_ref,
        expected_trust_domain_id=TDID, created_by="Arthur", created_at=NOW,
    )
    vp_ref = vp_path.relative_to(ws.root).as_posix()
    broker, broker_path, _ = create_broker_profile(
        ws, profile_id="sandbox-broker", classification="sandbox",
        verifier_profile_reference=vp_ref, transport_identifier="sandbox:staging",
        credential_reference="env:SANDBOX_BROKER_TOKEN", created_by="Arthur",
        created_at=NOW,
    )
    broker_ref = broker_path.relative_to(ws.root).as_posix()
    endpoint, endpoint_path, _ = create_sandbox_endpoint(
        ws, endpoint_id="staging", broker_profile_reference=broker_ref,
        origin="https://sandbox.example.test", request_path="/v1/evidence/sign",
        created_by="Arthur", created_at=NOW,
    )
    endpoint_ref = endpoint_path.relative_to(ws.root).as_posix()
    auth, auth_path, _ = create_broker_authorization(
        ws, endpoint_reference=endpoint_ref,
        signing_request_reference=request_path.relative_to(ws.root).as_posix(),
        trust_input_reference=trust_ref, transmitted_classification="internal",
        purpose="one sandbox fixture attempt", principal_reviewed_for_secrets=True,
        confirmed_principal="Arthur",
        issued_at="2026-08-26T11:59:00Z", expires_at="2026-08-26T12:30:00Z",
    )
    auth_ref = auth_path.relative_to(ws.root).as_posix()
    payload = SignedEvidencePayload(
        profile=SIGNED_PAYLOAD_PROFILE,
        artifact_reference=request.artifact_reference,
        artifact_schema=request.artifact_schema,
        artifact_content_hash=request.artifact_content_hash,
        canonical_payload_hash=request.canonical_payload_hash,
        signing_request_reference=request_path.relative_to(ws.root).as_posix(),
        signing_request_hash=request.content_hash,
        workspace_id=request.replay_domain.workspace_id,
        bounded_domain=request.replay_domain.bounded_domain,
        attester_eid=EID, attester_mid=MID, attester_role="audit_attester",
        attester_kid=KID, asserted_scope=EVIDENCE_SCOPE,
        issued_at=NOW, expires_at="2026-08-26T12:30:00Z",
        authority_effect="none", decision_effect="none", membership_effect="none",
    )
    return {
        "ws": ws, "request": request, "request_path": request_path,
        "trust": trust, "trust_ref": trust_ref, "endpoint": endpoint,
        "endpoint_ref": endpoint_ref, "auth": auth, "auth_ref": auth_ref,
        "payload": payload,
    }


def _execute(prepared, *, transport=None, resolver=None, verifier=None):
    return execute_sandbox_transport(
        prepared["ws"], endpoint_reference=prepared["endpoint_ref"],
        authorization_reference=prepared["auth_ref"],
        transport=transport or RecordingTransport(),
        credential_resolver=resolver or RecordingResolver(),
        public_evidence={"public/trust": TRUST, "public/revocation": REVOCATION,
                         "public/time": TIME},
        verifier=verifier or FixtureVerifier(prepared["payload"]), now=NOW,
    )


def test_success_binds_exact_bytes_attempt_receipt_and_existing_verifier(prepared):
    transport, resolver = RecordingTransport(), RecordingResolver()
    result = _execute(prepared, transport=transport, resolver=resolver)
    assert result.receipt.outcome == "RESPONSE_ACCEPTED_FOR_VERIFICATION"
    assert result.receipt.verification_status == "PASS"
    assert result.attempt.state == "PREPARED" and result.attempt.maximum_transmissions == 1
    assert resolver.calls == ["env:SANDBOX_BROKER_TOKEN"]
    call = transport.calls[0]
    wire = json.loads(call["body"])
    assert wire["signing_request"]["content_hash"] == prepared["request"].content_hash
    assert wire["artifact_sha256"] == prepared["request"].canonical_payload_hash
    assert call["idempotency_key"] == result.attempt.attempt_id.rsplit(":", 1)[1]
    events = ledger.read_events(prepared["ws"])
    assert events[-1]["event_type"] == "sandbox_broker_transport_attempt_recorded"
    assert events[-1]["payload"]["authority_effect"] == "none"


def test_secret_never_enters_any_workspace_artifact(prepared):
    secret = "UNIQUE-DISPOSABLE-SECRET-DO-NOT-STORE"
    _execute(prepared, resolver=RecordingResolver(secret))
    for path in prepared["ws"].root.rglob("*"):
        if path.is_file():
            assert secret.encode() not in path.read_bytes()


def test_existing_attempt_blocks_resend_before_credential_lookup(prepared):
    _execute(prepared)
    resolver, transport = RecordingResolver(), RecordingTransport()
    with pytest.raises(ValidationError, match="ATTEMPT_OUTCOME_UNKNOWN"):
        _execute(prepared, resolver=resolver, transport=transport)
    assert resolver.calls == [] and transport.calls == []


def test_unreadable_attempt_store_blocks_before_credential_lookup(prepared):
    bad = prepared["ws"].signing_broker_attempts_dir / "attempt-bad.json"
    bad.write_text('{"damaged":true}', encoding="utf-8")
    resolver = RecordingResolver()
    with pytest.raises(ValidationError, match="ATTEMPT_STORE_INVALID"):
        _execute(prepared, resolver=resolver)
    assert resolver.calls == []


def test_missing_credential_writes_not_sent_receipt(prepared):
    resolver = RecordingResolver(ValidationError("CREDENTIAL_MISSING"))
    result = _execute(prepared, resolver=resolver)
    assert result.receipt.outcome == "NOT_SENT"
    assert result.receipt.reason_codes == ["CREDENTIAL_MISSING"]
    assert result.receipt.response_body_hash is None


def test_adapter_exceptions_are_sanitized_and_conservative(prepared):
    resolver = RecordingResolver(RuntimeError("secret-bearing resolver detail"))
    first = _execute(prepared, resolver=resolver)
    assert first.receipt.outcome == "NOT_SENT"
    assert first.receipt.reason_codes == ["CREDENTIAL_RESOLVER_ERROR"]

    prepared2 = prepared.copy()
    # A new exact authorization creates a distinct governed attempt.
    auth, path, _ = create_broker_authorization(
        prepared["ws"], endpoint_reference=prepared["endpoint_ref"],
        signing_request_reference=prepared["request_path"].relative_to(
            prepared["ws"].root).as_posix(), trust_input_reference=prepared["trust_ref"],
        transmitted_classification="internal", purpose="second bounded attempt",
        principal_reviewed_for_secrets=True, confirmed_principal="Arthur",
        issued_at="2026-08-26T11:58:00Z",
        expires_at="2026-08-26T12:29:00Z",
    )
    prepared2["auth"], prepared2["auth_ref"] = auth, path.relative_to(prepared["ws"].root).as_posix()

    class BrokenTransport:
        def send(self, **_kwargs):
            raise RuntimeError("secret-bearing transport detail")

    second = _execute(prepared2, transport=BrokenTransport())
    assert second.receipt.outcome == "SENT_NO_RESPONSE"
    assert second.receipt.reason_codes == ["TRANSPORT_ERROR"]
    for receipt in prepared["ws"].signing_broker_receipts_dir.glob("*.json"):
        assert b"secret-bearing" not in receipt.read_bytes()


def test_malformed_transport_response_is_rejected_without_raw_detail(prepared):
    class MalformedTransport:
        def send(self, **_kwargs):
            return TransportResponse(200, RESPONSE_MEDIA_TYPE, "not-bytes")  # type: ignore[arg-type]

    result = _execute(prepared, transport=MalformedTransport())
    assert result.receipt.outcome == "RESPONSE_REJECTED"
    assert result.receipt.reason_codes == ["TRANSPORT_RESPONSE_INVALID"]
    assert result.receipt.response_body_hash is None


@pytest.mark.parametrize("sent,outcome", [(False, "NOT_SENT"), (True, "SENT_NO_RESPONSE")])
def test_transport_failure_preserves_ambiguous_delivery(prepared, sent, outcome):
    failure = SandboxTransportFailure("TRANSPORT_TIMEOUT", sent=sent)
    result = _execute(prepared, transport=RecordingTransport(failure=failure))
    assert result.receipt.outcome == outcome
    assert result.receipt.reason_codes == ["TRANSPORT_TIMEOUT"]


@pytest.mark.parametrize("response,code", [
    (TransportResponse(302, RESPONSE_MEDIA_TYPE, b"redirect"), "HTTP_RESPONSE_REJECTED"),
    (TransportResponse(503, RESPONSE_MEDIA_TYPE, b"down"), "HTTP_RESPONSE_REJECTED"),
    (TransportResponse(200, "text/plain", ENVELOPE), "RESPONSE_MEDIA_TYPE_INVALID"),
    (TransportResponse(200, RESPONSE_MEDIA_TYPE, b""), "RESPONSE_EMPTY"),
    (TransportResponse(200, RESPONSE_MEDIA_TYPE, b"x" * (MAX_RESPONSE_BYTES + 1)),
     "RESPONSE_TOO_LARGE"),
    (TransportResponse(200, RESPONSE_MEDIA_TYPE, b"x" * (MAX_RESPONSE_BYTES + 2)),
     "TRANSPORT_RESPONSE_BOUND_VIOLATION"),
])
def test_response_failures_never_reach_verifier(prepared, response, code):
    verifier = FixtureVerifier(prepared["payload"])
    result = _execute(prepared, transport=RecordingTransport(response=response), verifier=verifier)
    assert result.receipt.outcome == "RESPONSE_REJECTED"
    assert result.receipt.reason_codes == [code]
    assert result.evidence is None


def test_verification_failure_remains_failure(prepared):
    result = _execute(prepared, verifier=FixtureVerifier(prepared["payload"], fail=True))
    assert result.receipt.outcome == "RESPONSE_ACCEPTED_FOR_VERIFICATION"
    assert result.receipt.verification_status == "FAIL"
    assert "EVIDENCE_VERIFICATION_FAILED" in result.receipt.reason_codes


def test_expired_authorization_fails_before_attempt_and_credential(prepared):
    resolver = RecordingResolver()
    with pytest.raises(ValidationError, match="invalid or expired"):
        execute_sandbox_transport(
            prepared["ws"], endpoint_reference=prepared["endpoint_ref"],
            authorization_reference=prepared["auth_ref"], transport=RecordingTransport(),
            credential_resolver=resolver, public_evidence={},
            verifier=FixtureVerifier(prepared["payload"]), now="2026-08-26T13:00:00Z",
        )
    assert resolver.calls == []
    assert list(prepared["ws"].signing_broker_attempts_dir.glob("*.json")) == []


def test_wrong_principal_cannot_create_authorization(prepared):
    with pytest.raises(ValidationError, match="exact workspace principal"):
        create_broker_authorization(
            prepared["ws"], endpoint_reference=prepared["endpoint_ref"],
            signing_request_reference=prepared["request_path"].relative_to(
                prepared["ws"].root).as_posix(),
            trust_input_reference=prepared["trust_ref"], transmitted_classification="internal",
            purpose="wrong", principal_reviewed_for_secrets=True,
            confirmed_principal="Mallory",
            issued_at=NOW, expires_at="2026-08-26T12:30:00Z",
        )


def test_secret_review_confirmation_is_not_inferred(prepared):
    with pytest.raises(ValidationError, match="explicit secret-review"):
        create_broker_authorization(
            prepared["ws"], endpoint_reference=prepared["endpoint_ref"],
            signing_request_reference=prepared["request_path"].relative_to(
                prepared["ws"].root).as_posix(),
            trust_input_reference=prepared["trust_ref"], transmitted_classification="internal",
            purpose="unreviewed", principal_reviewed_for_secrets=False,
            confirmed_principal="Arthur", issued_at=NOW,
            expires_at="2026-08-26T12:30:00Z",
        )


@pytest.mark.parametrize("origin", [
    "http://sandbox.example.test", "https://127.0.0.1", "https://user@host.test",
    "https://host.test/path", "https://HOST.test", "https://host.test?x=1",
    "https://*.example.test", "https://höst.test",
])
def test_endpoint_origin_is_fail_closed(prepared, origin):
    with pytest.raises((PydanticValidationError, ValueError)):
        create_sandbox_endpoint(
            prepared["ws"], endpoint_id="bad",
            broker_profile_reference=prepared["endpoint"].broker_profile_reference,
            origin=origin, request_path="/v1/evidence/sign", created_by="Arthur",
            created_at=NOW,
        )


def test_environment_credential_resolver_is_exact_and_bounded(monkeypatch):
    resolver = EnvironmentCredentialResolver()
    monkeypatch.setenv("SANDBOX_TOKEN", " disposable-token ")
    with pytest.raises(ValidationError, match="CREDENTIAL_MALFORMED"):
        resolver.resolve("env:SANDBOX_TOKEN")
    monkeypatch.setenv("SANDBOX_TOKEN", "disposable-token")
    assert resolver.resolve("env:SANDBOX_TOKEN") == "disposable-token"
    with pytest.raises(ValidationError, match="SELECTOR"):
        resolver.resolve("env:lowercase")


def test_public_address_policy_rejects_private_and_accepts_public(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_a, **_k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))
    ])
    with pytest.raises(SandboxTransportFailure, match="DESTINATION_ADDRESS_NOT_PUBLIC"):
        _public_addresses("sandbox.example.test", 443)
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_a, **_k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))
    ])
    assert _public_addresses("sandbox.example.test", 443) == ["8.8.8.8"]


def test_reconciliation_restores_receipt_event_without_inference(prepared, monkeypatch):
    import conclave.sandbox_transport as module
    monkeypatch.setattr(module, "record_event", lambda *_a, **_k: (_ for _ in ()).throw(
        ValidationError("ledger unavailable")
    ))
    with pytest.raises(ValidationError, match="ledger unavailable"):
        _execute(prepared)
    receipts = list(prepared["ws"].signing_broker_receipts_dir.glob("*.json"))
    assert len(receipts) == 1
    report = reconcile(prepared["ws"])
    event = next(item for item in report.created
                 if item["event_type"] == "sandbox_broker_transport_attempt_recorded")
    assert "not inferred" in event["payload"]["note"]


def _certificate(tmp_path: Path, host: str):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, host)])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(hours=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(host)]), critical=False)
        .sign(key, hashes.SHA256())
    )
    cert_path, key_path = tmp_path / "cert.pem", tmp_path / "key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    return cert_path, key_path


def test_concrete_https_transport_uses_tls_exact_headers_and_binary_body(tmp_path, monkeypatch):
    host, observed = "sandbox.example.test", {}
    cert_path, key_path = _certificate(tmp_path, host)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            size = int(self.headers["Content-Length"])
            observed.update(path=self.path, authorization=self.headers["Authorization"],
                            idempotency=self.headers["Idempotency-Key"], body=self.rfile.read(size))
            self.send_response(200)
            self.send_header("Content-Type", RESPONSE_MEDIA_TYPE)
            self.end_headers()
            self.wfile.write(ENVELOPE)

        def log_message(self, *_args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    import conclave.sandbox_transport as module
    monkeypatch.setattr(module, "_public_addresses", lambda *_a: ["127.0.0.1"])
    original = ssl.create_default_context
    monkeypatch.setattr(module.ssl, "create_default_context",
                        lambda: original(cafile=str(cert_path)))
    endpoint = SandboxBrokerEndpoint.model_validate({
        **{
            "profile": "sandbox-broker-endpoint", "schema_version": "sandbox-broker-endpoint/0.1.0",
            "endpoint_id": "local-fixture",
            "broker_profile_reference": "signing/broker-profiles/" + "a" * 64 + ".json",
            "broker_profile_hash": "sha256:" + "a" * 64,
            "origin": f"https://{host}:{server.server_port}", "request_path": "/sign",
            "authentication_scheme": "bearer-env-v1", "credential_reference": "env:TOKEN",
            "tls_policy": "system-ca-hostname-tls12-plus", "maximum_request_bytes": 1024,
            "maximum_response_bytes": 1024, "connect_timeout_seconds": 5,
            "total_timeout_seconds": 5, "created_by": "test", "created_at": NOW,
            "environment": "sandbox", "authority_effect": "none", "decision_effect": "none",
            "membership_effect": "none", "action_execution_allowed": False,
            "content_hash": "sha256:" + "0" * 64,
        }
    }, context={"skip_content_hash": True})
    response = HttpsSandboxBrokerTransport().send(
        endpoint=endpoint, body=b'{"exact":true}', credential="fixture-token",
        idempotency_key="abc123",
    )
    thread.join(timeout=5)
    server.server_close()
    assert response.body == ENVELOPE and response.content_type == RESPONSE_MEDIA_TYPE
    assert observed == {"path": "/sign", "authorization": "Bearer fixture-token",
                        "idempotency": "abc123", "body": b'{"exact":true}'}


def test_records_are_closed_and_authority_neutral(prepared):
    assert prepared["endpoint"].authority_effect == "none"
    assert prepared["auth"].authority_effect == "broker_egress_only"
    raw = prepared["auth"].model_dump(mode="json")
    raw["production_use_allowed"] = True
    with pytest.raises(PydanticValidationError):
        BrokerEgressAuthorization.model_validate(raw)
