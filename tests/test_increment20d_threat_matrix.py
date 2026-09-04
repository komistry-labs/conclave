"""Adversarial regressions required by the frozen Increment 20D matrix."""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError

from conclave.errors import ValidationError
from conclave.identity import read_record, seal_record, write_immutable_record
from conclave.sandbox_transport import (
    EnvironmentCredentialResolver,
    SandboxBrokerEndpoint,
    SandboxTransportFailure,
    _validate_credential,
    _public_addresses,
)

NOW = "2026-08-27T12:00:00Z"


def _endpoint(**updates):
    data = {
        "profile": "sandbox-broker-endpoint",
        "schema_version": "sandbox-broker-endpoint/0.1.0",
        "endpoint_id": "fixture",
        "broker_profile_reference": "signing/broker-profiles/" + "a" * 64 + ".json",
        "broker_profile_hash": "sha256:" + "a" * 64,
        "origin": "https://sandbox.example.test",
        "request_path": "/v1/evidence/sign",
        "authentication_scheme": "bearer-env-v1",
        "credential_reference": "env:SANDBOX_TOKEN",
        "tls_policy": "system-ca-hostname-tls12-plus",
        "maximum_request_bytes": 1024,
        "maximum_response_bytes": 1024,
        "connect_timeout_seconds": 5,
        "total_timeout_seconds": 10,
        "created_by": "test",
        "created_at": NOW,
        "environment": "sandbox",
        "authority_effect": "none",
        "decision_effect": "none",
        "membership_effect": "none",
        "action_execution_allowed": False,
    }
    data.update(updates)
    return seal_record(SandboxBrokerEndpoint, data)


@pytest.mark.parametrize("origin", [
    "https://sandbox.example.test:443",
    "https://sandbox.example.test.",
    "https://_service.example.test",
    "https://-bad.example.test",
    "https://bad-.example.test",
    "ftp://sandbox.example.test",
    "https://user:pass@sandbox.example.test",
    "https://sandbox.example.test/#fragment",
])
def test_origin_rejects_noncanonical_port_host_scheme_userinfo_and_fragment(origin):
    with pytest.raises(PydanticValidationError):
        _endpoint(origin=origin)


@pytest.mark.parametrize("path", [
    "/..", "/.", "/v1/../sign", "/v1/./sign", "//sign", "/sign\\other",
    "/sign:stream", "/sign%2f..%2fother",
])
def test_request_path_rejects_traversal_backslash_ads_and_encoded_ambiguity(path):
    with pytest.raises(PydanticValidationError):
        _endpoint(request_path=path)


@pytest.mark.parametrize("address", [
    "0.0.0.0", "127.0.0.1", "10.0.0.1", "169.254.1.1", "224.0.0.1",
    "255.255.255.255", "::", "::1", "fe80::1", "ff02::1", "2001:db8::1",
    "::ffff:8.8.8.8",
])
def test_dns_rejects_every_nonpublic_reserved_or_mapped_class(monkeypatch, address):
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_a, **_k: [
        (family, socket.SOCK_STREAM, 6, "", (address, 443))
    ])
    with pytest.raises(SandboxTransportFailure, match="DESTINATION_ADDRESS_NOT_PUBLIC"):
        _public_addresses("sandbox.example.test", 443)


def test_dns_mixed_public_private_answers_fail_closed(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_a, **_k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),
    ])
    with pytest.raises(SandboxTransportFailure, match="DESTINATION_ADDRESS_NOT_PUBLIC"):
        _public_addresses("sandbox.example.test", 443)


def test_dns_malformed_answer_is_sanitized(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_a, **_k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("not-an-address", 443))
    ])
    with pytest.raises(SandboxTransportFailure, match="DNS_RESPONSE_INVALID"):
        _public_addresses("sandbox.example.test", 443)


@pytest.mark.parametrize("credential", ["", " token", "token ", "a\nheader", "a\rheader", "a\x00b", "x" * 8193])
def test_credentials_reject_empty_whitespace_control_injection_and_oversize(monkeypatch, credential):
    if "\x00" in credential:
        with pytest.raises(ValidationError, match="CREDENTIAL_MALFORMED"):
            _validate_credential(credential)
        return
    monkeypatch.setenv("SANDBOX_TOKEN", credential)
    with pytest.raises(ValidationError, match="CREDENTIAL_MALFORMED"):
        EnvironmentCredentialResolver().resolve("env:SANDBOX_TOKEN")


def test_immutable_json_reader_rejects_duplicate_members_and_noncanonical_encoding(tmp_path: Path):
    record = _endpoint()
    path = tmp_path / "endpoint.json"
    write_immutable_record(path, record)
    raw = path.read_text(encoding="utf-8")
    # Inject a second profile member independently of Pydantic's inherited
    # field-order choice, which can differ across supported dependency builds.
    duplicate = '{\n  "profile": "sandbox-broker-endpoint",' + raw[1:]
    path.write_text(duplicate, encoding="utf-8")
    with pytest.raises(ValidationError):
        read_record(path, SandboxBrokerEndpoint)

    path.write_text(json.dumps(record.model_dump(mode="json")), encoding="utf-8")
    with pytest.raises(ValidationError):
        read_record(path, SandboxBrokerEndpoint)
