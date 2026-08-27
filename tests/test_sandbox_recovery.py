"""Increment 20C bounded operator recovery acceptance tests."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError as PydanticValidationError
from typer.testing import CliRunner

from conclave.cli import app
from conclave.errors import ValidationError
from conclave.identity import TrustInputSet, seal_record, sha256_bytes, write_immutable_record
from conclave.reconcile import reconcile
from conclave.sandbox_operator_runtime import load_operator_verification_runtime
from conclave.sandbox_recovery import (
    BrokerRecoveryAuthorization,
    create_recovery_authorization,
    execute_recovery,
)
from conclave.sandbox_transport import SandboxTransportFailure
from test_sandbox_transport import (
    NOW,
    REVOCATION,
    TIME,
    TRUST,
    FixtureVerifier,
    RecordingResolver,
    RecordingTransport,
    _execute,
    prepared,
)


def _public():
    return {"public/trust": TRUST, "public/revocation": REVOCATION, "public/time": TIME}


def _ambiguous(prepared):
    first_transport = RecordingTransport(
        failure=SandboxTransportFailure("TRANSPORT_TIMEOUT", sent=True)
    )
    first = _execute(prepared, transport=first_transport)
    assert first.receipt.outcome == "SENT_NO_RESPONSE"
    return first, first_transport


def _authorize(prepared, first, *, action="IDEMPOTENT_REPLAY", purpose="recover exact attempt"):
    record, path, _ = create_recovery_authorization(
        prepared["ws"],
        original_attempt_reference=first.attempt_path.relative_to(prepared["ws"].root).as_posix(),
        original_receipt_reference=first.receipt_path.relative_to(prepared["ws"].root).as_posix(),
        action=action, purpose=purpose, confirmed_principal="Arthur",
        principal_confirmed_ambiguous_outcome=True,
        principal_reviewed_artifact_for_secrets=True,
        principal_acknowledged_replay_consequence=True,
        issued_at="2026-08-26T11:59:00Z", expires_at="2026-08-28T12:30:00Z",
    )
    return record, path.relative_to(prepared["ws"].root).as_posix()


def _recover(prepared, reference, *, transport=None, resolver=None):
    return execute_recovery(
        prepared["ws"], recovery_authorization_reference=reference,
        transport=transport or RecordingTransport(),
        credential_resolver=resolver or RecordingResolver(),
        public_evidence=_public(), verifier=FixtureVerifier(prepared["payload"]), now=NOW,
    )


def test_replay_uses_exact_original_body_and_idempotency_key(prepared):
    first, first_transport = _ambiguous(prepared)
    authorization, reference = _authorize(prepared, first)
    transport, resolver = RecordingTransport(), RecordingResolver()
    result = _recover(prepared, reference, transport=transport, resolver=resolver)
    assert result.disposition.outcome == "REPLAY_RESPONSE_ACCEPTED_FOR_VERIFICATION"
    assert result.disposition.verification_status == "PASS"
    assert resolver.calls == ["env:SANDBOX_BROKER_TOKEN"]
    original_call, replay_call = first_transport.calls[0], transport.calls[0]
    assert replay_call["body"] == original_call["body"]
    assert replay_call["idempotency_key"] == original_call["idempotency_key"]
    assert replay_call["idempotency_key"] == authorization.original_idempotency_key
    assert result.recovery_attempt.idempotency_key == authorization.original_idempotency_key


def test_abandonment_never_resolves_credential_or_calls_transport(prepared):
    first, _ = _ambiguous(prepared)
    _authorization, reference = _authorize(prepared, first, action="ABANDON")
    transport, resolver = RecordingTransport(), RecordingResolver()
    result = _recover(prepared, reference, transport=transport, resolver=resolver)
    assert result.disposition.outcome == "ABANDONED_WITHOUT_TRANSMISSION"
    assert result.recovery_attempt is None
    assert resolver.calls == [] and transport.calls == []


def test_missing_receipt_crash_window_can_be_abandoned_but_not_inferred(prepared, monkeypatch):
    import conclave.sandbox_transport as module

    original = module.write_immutable_record
    calls = 0

    def crash_before_receipt(path, record):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated hard stop before receipt")
        return original(path, record)

    monkeypatch.setattr(module, "write_immutable_record", crash_before_receipt)
    with pytest.raises(RuntimeError, match="before receipt"):
        _execute(prepared)
    monkeypatch.setattr(module, "write_immutable_record", original)
    attempt_path = next(prepared["ws"].signing_broker_attempts_dir.glob("*.json"))
    first = SimpleNamespace(attempt_path=attempt_path)
    authorization, path, _ = create_recovery_authorization(
        prepared["ws"],
        original_attempt_reference=first.attempt_path.relative_to(prepared["ws"].root).as_posix(),
        original_receipt_reference=None, action="ABANDON", purpose="abandon unknown crash window",
        confirmed_principal="Arthur", principal_confirmed_ambiguous_outcome=True,
        principal_reviewed_artifact_for_secrets=True,
        principal_acknowledged_replay_consequence=True,
        issued_at="2026-08-26T11:59:00Z", expires_at="2026-08-26T12:30:00Z",
    )
    assert authorization.original_outcome == "MISSING_RECEIPT"
    result = _recover(prepared, path.relative_to(prepared["ws"].root).as_posix())
    assert result.disposition.outcome == "ABANDONED_WITHOUT_TRANSMISSION"


def test_deleted_recorded_receipt_cannot_be_reclassified_as_crash_window(prepared):
    first, _ = _ambiguous(prepared)
    first.receipt_path.unlink()
    with pytest.raises(ValidationError, match="RECOVERY_RECORDED_RECEIPT_MISSING"):
        create_recovery_authorization(
            prepared["ws"],
            original_attempt_reference=first.attempt_path.relative_to(prepared["ws"].root).as_posix(),
            original_receipt_reference=None, action="ABANDON", purpose="must fail",
            confirmed_principal="Arthur", principal_confirmed_ambiguous_outcome=True,
            principal_reviewed_artifact_for_secrets=True,
            principal_acknowledged_replay_consequence=True,
            issued_at="2026-08-26T11:59:00Z", expires_at="2026-08-28T12:30:00Z",
        )


def test_not_sent_receipt_is_not_recovery_eligible(prepared):
    first = _execute(
        prepared,
        transport=RecordingTransport(failure=SandboxTransportFailure("DNS_RESOLUTION_FAILED", sent=False)),
    )
    with pytest.raises(ValidationError, match="RECOVERY_ORIGINAL_OUTCOME_INELIGIBLE"):
        _authorize(prepared, first)


def test_exact_duplicate_execute_returns_disposition_without_resend(prepared):
    first, _ = _ambiguous(prepared)
    _authorization, reference = _authorize(prepared, first)
    transport = RecordingTransport()
    one = _recover(prepared, reference, transport=transport)
    two = _recover(prepared, reference, transport=transport)
    assert one.disposition.content_hash == two.disposition.content_hash
    assert len(transport.calls) == 1


def test_second_recovery_authorization_blocks_before_credential(prepared):
    first, _ = _ambiguous(prepared)
    _one, reference = _authorize(prepared, first, purpose="first")
    _authorize(prepared, first, purpose="second")
    resolver = RecordingResolver()
    with pytest.raises(ValidationError, match="RECOVERY_AUTHORIZATION_CONFLICT"):
        _recover(prepared, reference, resolver=resolver)
    assert resolver.calls == []


def test_concurrent_recovery_transmits_once(prepared):
    first, _ = _ambiguous(prepared)
    _authorization, reference = _authorize(prepared, first)
    transport = RecordingTransport()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _i: _recover(prepared, reference, transport=transport), range(2)))
    assert len(transport.calls) == 1
    assert results[0].disposition.content_hash == results[1].disposition.content_hash


def test_crash_after_recovery_intent_blocks_future_transmission(prepared, monkeypatch):
    import conclave.sandbox_recovery as module

    first, _ = _ambiguous(prepared)
    _authorization, reference = _authorize(prepared, first)
    original = module.write_immutable_record
    calls = 0

    def crash_on_disposition(path, record):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated hard stop")
        return original(path, record)

    monkeypatch.setattr(module, "write_immutable_record", crash_on_disposition)
    with pytest.raises(RuntimeError, match="hard stop"):
        _recover(prepared, reference)
    monkeypatch.setattr(module, "write_immutable_record", original)
    resolver = RecordingResolver()
    with pytest.raises(ValidationError, match="RECOVERY_OUTCOME_UNKNOWN"):
        _recover(prepared, reference, resolver=resolver)
    assert resolver.calls == []


def test_second_ambiguous_replay_is_terminal(prepared):
    first, _ = _ambiguous(prepared)
    _authorization, reference = _authorize(prepared, first)
    failure = RecordingTransport(failure=SandboxTransportFailure("TRANSPORT_TIMEOUT", sent=True))
    result = _recover(prepared, reference, transport=failure)
    assert result.disposition.outcome == "REPLAY_SENT_NO_RESPONSE"
    _recover(prepared, reference, transport=failure)
    assert len(failure.calls) == 1


def test_deleted_recorded_disposition_does_not_reopen_replay(prepared):
    first, _ = _ambiguous(prepared)
    _authorization, reference = _authorize(prepared, first)
    completed = _recover(prepared, reference)
    completed.disposition_path.unlink()
    resolver = RecordingResolver()
    with pytest.raises(ValidationError, match="RECOVERY_RECORDED_DISPOSITION_MISSING"):
        _recover(prepared, reference, resolver=resolver)
    assert resolver.calls == []


def test_corrupt_recovery_store_blocks_before_credential(prepared):
    first, _ = _ambiguous(prepared)
    _authorization, reference = _authorize(prepared, first)
    (prepared["ws"].signing_broker_recovery_attempts_dir / "bad.json").write_text(
        '{"damaged":true}', encoding="utf-8"
    )
    resolver = RecordingResolver()
    with pytest.raises(ValidationError, match="RECOVERY_STORE_INVALID"):
        _recover(prepared, reference, resolver=resolver)
    assert resolver.calls == []


def test_secret_never_enters_recovery_artifacts_or_ledger(prepared):
    secret = "RECOVERY-SENTINEL-SECRET-NEVER-PERSIST"
    first, _ = _ambiguous(prepared)
    _authorization, reference = _authorize(prepared, first)
    _recover(prepared, reference, resolver=RecordingResolver(secret))
    for path in prepared["ws"].root.rglob("*"):
        if path.is_file():
            assert secret.encode() not in path.read_bytes()


def test_confirmation_and_principal_are_explicit(prepared):
    first, _ = _ambiguous(prepared)
    kwargs = dict(
        original_attempt_reference=first.attempt_path.relative_to(prepared["ws"].root).as_posix(),
        original_receipt_reference=first.receipt_path.relative_to(prepared["ws"].root).as_posix(),
        action="ABANDON", purpose="invalid", issued_at="2026-08-26T11:59:00Z",
        expires_at="2026-08-26T12:30:00Z", principal_confirmed_ambiguous_outcome=True,
        principal_reviewed_artifact_for_secrets=True,
        principal_acknowledged_replay_consequence=True,
    )
    with pytest.raises(ValidationError, match="RECOVERY_PRINCIPAL_MISMATCH"):
        create_recovery_authorization(prepared["ws"], confirmed_principal="Mallory", **kwargs)
    kwargs["principal_acknowledged_replay_consequence"] = False
    with pytest.raises(ValidationError, match="RECOVERY_CONFIRMATION_REQUIRED"):
        create_recovery_authorization(prepared["ws"], confirmed_principal="Arthur", **kwargs)


def test_reconciliation_restores_recovery_event_without_inference(prepared, monkeypatch):
    import conclave.sandbox_recovery as module

    first, _ = _ambiguous(prepared)
    _authorization, reference = _authorize(prepared, first, action="ABANDON")
    monkeypatch.setattr(module, "record_event", lambda *_a, **_k: (_ for _ in ()).throw(
        ValidationError("ledger unavailable")
    ))
    with pytest.raises(ValidationError, match="ledger unavailable"):
        _recover(prepared, reference)
    report = reconcile(prepared["ws"])
    event = next(item for item in report.created
                 if item["event_type"] == "sandbox_broker_recovery_abandoned")
    assert "not inferred" in event["payload"]["note"]


def test_records_are_closed_schema(prepared):
    first, _ = _ambiguous(prepared)
    authorization, _reference = _authorize(prepared, first)
    raw = authorization.model_dump(mode="json")
    raw["unapproved"] = True
    with pytest.raises(PydanticValidationError):
        BrokerRecoveryAuthorization.model_validate(raw)


def test_public_idempotency_material_is_hash_bound(prepared):
    first, _ = _ambiguous(prepared)
    authorization, _reference = _authorize(prepared, first)
    payload = json.loads(authorization.model_dump_json())
    assert payload["original_idempotency_key"] == first.attempt.attempt_id.rsplit(":", 1)[1]
    assert payload["production_use_allowed"] is False
    assert payload["action_execution_allowed"] is False


def test_cli_surface_is_exact_and_has_no_signing_or_key_command():
    runner = CliRunner()
    result = runner.invoke(app, ["evidence", "--help"])
    assert result.exit_code == 0
    for command in (
        "sandbox-endpoint", "broker-authorization", "broker-submit",
        "broker-attempt", "broker-receipt", "broker-recovery",
    ):
        assert command in result.stdout
    assert "broker-sign " not in result.stdout and "key-generate " not in result.stdout


def test_cli_submit_fails_before_credential_when_public_runtime_unavailable(
    prepared, monkeypatch,
):
    monkeypatch.setenv("CONCLAVE_HOME", str(prepared["ws"].root))
    monkeypatch.delenv("CONCLAVE_IDM_WHEEL", raising=False)
    monkeypatch.delenv("CONCLAVE_IDM_SOURCE_ARCHIVE", raising=False)
    monkeypatch.setenv("SANDBOX_BROKER_TOKEN", "CLI-SECRET-MUST-NOT-APPEAR")
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["evidence", "broker-submit", "--endpoint", prepared["endpoint_ref"],
         "--authorization", prepared["auth_ref"]],
        input="Arthur\n",
    )
    assert result.exit_code == 1
    assert "PINNED_PUBLIC_VERIFIER_RUNTIME_UNAVAILABLE" in result.stderr
    assert "CLI-SECRET-MUST-NOT-APPEAR" not in result.stdout + result.stderr
    assert list(prepared["ws"].signing_broker_attempts_dir.glob("*.json")) == []


def test_cli_abandonment_needs_no_public_runtime_or_credential(prepared, monkeypatch):
    first, _ = _ambiguous(prepared)
    _authorization, reference = _authorize(prepared, first, action="ABANDON")
    monkeypatch.setenv("CONCLAVE_HOME", str(prepared["ws"].root))
    monkeypatch.delenv("CONCLAVE_IDM_WHEEL", raising=False)
    monkeypatch.delenv("CONCLAVE_IDM_SOURCE_ARCHIVE", raising=False)
    monkeypatch.setenv("SANDBOX_BROKER_TOKEN", "ABANDON-SECRET-MUST-NOT-APPEAR")
    runner = CliRunner()
    result = runner.invoke(
        app, ["evidence", "broker-recovery", "execute", "--authorization", reference],
        input="Arthur\n",
    )
    assert result.exit_code == 0
    assert "ABANDONED_WITHOUT_TRANSMISSION" in result.stdout
    assert "ABANDON-SECRET-MUST-NOT-APPEAR" not in result.stdout + result.stderr


def test_cli_show_does_not_resolve_credential(prepared, monkeypatch):
    monkeypatch.setenv("CONCLAVE_HOME", str(prepared["ws"].root))
    secret = "SHOW-COMMAND-SECRET-MUST-NOT-APPEAR"
    monkeypatch.setenv("SANDBOX_BROKER_TOKEN", secret)
    result = CliRunner().invoke(
        app, ["evidence", "sandbox-endpoint", "show", "--endpoint", prepared["endpoint_ref"]]
    )
    assert result.exit_code == 0
    assert '"environment": "sandbox"' in result.stdout
    assert secret not in result.stdout + result.stderr


def test_public_operator_runtime_is_exact_workspace_evidence_and_pinned_distribution(
    prepared, monkeypatch,
):
    ws = prepared["ws"]
    values = {
        "identity/trust-inputs/runtime-public-trust.json": TRUST,
        "identity/trust-inputs/runtime-public-revocation.cose": REVOCATION,
        "identity/trust-inputs/runtime-public-time.json": TIME,
    }
    for reference, value in values.items():
        ws.root.joinpath(*reference.split("/")).write_bytes(value)
    raw = prepared["trust"].model_dump(mode="json", exclude={"content_hash"})
    raw["trust_bundle"] = {
        "reference": "identity/trust-inputs/runtime-public-trust.json",
        "content_hash": sha256_bytes(TRUST),
    }
    raw["revocation_evidence"] = [{
        "reference": "identity/trust-inputs/runtime-public-revocation.cose",
        "content_hash": sha256_bytes(REVOCATION),
    }]
    raw["time_evidence"] = {
        "reference": "identity/trust-inputs/runtime-public-time.json",
        "content_hash": sha256_bytes(TIME),
    }
    trust = seal_record(TrustInputSet, raw)
    trust_path, _ = write_immutable_record(
        ws.identity_trust_inputs_dir / "runtime-trust-input.json", trust
    )
    fixtures = Path(__file__).parent / "fixtures" / "idm-baseline"
    monkeypatch.setenv(
        "CONCLAVE_IDM_WHEEL",
        str((fixtures / "idm_reference-0.1.0.dev0-py3-none-any.whl").resolve()),
    )
    monkeypatch.setenv(
        "CONCLAVE_IDM_SOURCE_ARCHIVE",
        str((fixtures / "idm-3769ce3-source.zip").resolve()),
    )
    runtime = load_operator_verification_runtime(
        ws, trust_input_reference=trust_path.relative_to(ws.root).as_posix()
    )
    assert runtime.public_evidence == values
    monkeypatch.setenv("CONCLAVE_IDM_WHEEL", "relative-wheel.whl")
    with pytest.raises(ValidationError, match="PINNED_PUBLIC_VERIFIER_RUNTIME_INVALID"):
        load_operator_verification_runtime(
            ws, trust_input_reference=trust_path.relative_to(ws.root).as_posix()
        )
