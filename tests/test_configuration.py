"""Increment 20A configuration and keyless diagnostics acceptance tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError
from typer.testing import CliRunner

from conclave import ledger
from conclave.cli import app
from conclave.configuration import (
    FIXTURE_TRANSPORT,
    BrokerTransportProfile,
    DiagnosticsResult,
    IDMVerifierProfile,
    create_broker_profile,
    create_verifier_profile,
    diagnostics_event_fields,
    read_broker_profile,
    read_verifier_profile,
    run_broker_check,
)
from conclave.errors import IntegrityError, ValidationError
from conclave.reconcile import reconcile
from conclave.workspace import Workspace

CREATED_AT = "2026-08-26T12:00:00Z"
TRUST_REF = "identity/trust-inputs/future-public-trust.json"
TDID = "tdid:" + "c" * 26


@pytest.fixture
def ws(tmp_path: Path) -> Workspace:
    return Workspace.create(tmp_path, principal="Arthur")


def verifier(ws: Workspace):
    record, path, created = create_verifier_profile(
        ws, profile_id="idm-reference", expected_trust_input_reference=TRUST_REF,
        expected_trust_domain_id=TDID, created_by="Arthur",
        created_at=CREATED_AT,
    )
    assert created
    return record, path.relative_to(ws.root).as_posix(), path


def broker(ws: Workspace, *, classification="fixture-only", credential="none",
           transport=FIXTURE_TRANSPORT):
    verifier_record, verifier_ref, _ = verifier(ws)
    record, path, created = create_broker_profile(
        ws, profile_id=f"{classification}-broker", classification=classification,
        verifier_profile_reference=verifier_ref, transport_identifier=transport,
        credential_reference=credential, created_by="Arthur", created_at=CREATED_AT,
    )
    assert created and record.verifier_profile_hash == verifier_record.content_hash
    return record, path.relative_to(ws.root).as_posix(), path


def test_workspace_adds_only_frozen_increment_20a_directories(ws):
    assert ws.identity_verifier_profiles_dir.is_dir()
    assert ws.signing_broker_profiles_dir.is_dir()
    assert ws.diagnostics_dir.is_dir()
    assert ws.load_config()["identity"]["mode"] == "local"


def test_verifier_profile_is_hash_named_closed_and_idempotent(ws):
    first, ref, path = verifier(ws)
    assert path.name == f"verifier-{first.content_hash.removeprefix('sha256:')}.json"
    second, second_path, created = create_verifier_profile(
        ws, profile_id="idm-reference", expected_trust_input_reference=TRUST_REF,
        expected_trust_domain_id=TDID, created_by="Arthur",
        created_at=CREATED_AT,
    )
    assert not created and second == first and second_path == path
    assert read_verifier_profile(ws, ref) == first
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["unknown"] = True
    with pytest.raises(PydanticValidationError):
        IDMVerifierProfile.model_validate(raw)


@pytest.mark.parametrize("field", [
    "commit", "tree", "wheel_filename", "wheel_sha256",
    "source_archive_sha256", "provisioning", "classification",
])
def test_every_implementation_pin_field_is_fail_closed(ws, field):
    _, _, path = verifier(ws)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["implementation"][field] = "wrong"
    raw["content_hash"] = "sha256:" + "0" * 64
    with pytest.raises(PydanticValidationError):
        IDMVerifierProfile.model_validate(raw)


@pytest.mark.parametrize("reference", [
    "", "/identity/verifier-profiles/x.json", "C:/x.json", "//host/share/x.json",
    "identity\\verifier-profiles\\x.json", "identity/verifier-profiles/../x.json",
    "identity/verifier-profiles/x.json:stream", "identity/./verifier-profiles/x.json",
    "signing/broker-profiles/x.json",
])
def test_unsafe_or_wrong_area_verifier_references_fail(ws, reference):
    with pytest.raises((ValidationError, ValueError)):
        read_verifier_profile(ws, reference)


def test_profile_id_and_trust_input_reference_grammars_are_closed(ws):
    with pytest.raises((PydanticValidationError, ValueError)):
        create_verifier_profile(
            ws, profile_id="Bad ID", expected_trust_input_reference=TRUST_REF,
            expected_trust_domain_id=TDID, created_by="Arthur", created_at=CREATED_AT,
        )
    with pytest.raises((PydanticValidationError, ValueError)):
        create_verifier_profile(
            ws, profile_id="valid", expected_trust_input_reference="E:/offline/root.idmk",
            expected_trust_domain_id=TDID, created_by="Arthur", created_at=CREATED_AT,
        )


def test_fixture_and_sandbox_broker_grammars(ws):
    fixture, ref, _ = broker(ws)
    assert read_broker_profile(ws, ref) == fixture

    ws2 = Workspace.create(ws.root.parent / "other", principal="Arthur")
    sandbox, _, _ = broker(
        ws2, classification="sandbox", credential="env:IDM_BROKER_TOKEN",
        transport="sandbox:staging",
    )
    assert sandbox.credential_reference == "env:IDM_BROKER_TOKEN"

    ws3 = Workspace.create(ws.root.parent / "invalid", principal="Arthur")
    _, verifier_ref, _ = verifier(ws3)
    with pytest.raises((PydanticValidationError, ValueError)):
        create_broker_profile(
            ws3, profile_id="bad", classification="sandbox",
            verifier_profile_reference=verifier_ref, transport_identifier="https://broker",
            credential_reference="secret-value", created_by="Arthur", created_at=CREATED_AT,
        )


def test_broker_profile_cross_hash_is_enforced(ws):
    _, _, path = broker(ws)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["verifier_profile_hash"] = "sha256:" + "0" * 64
    # Re-sealing proves that even a structurally valid attacker-created record
    # cannot cross-bind to a different verifier profile.
    from conclave.identity import seal_record
    raw.pop("content_hash")
    conflicting = seal_record(BrokerTransportProfile, raw)
    conflicting_path = path.with_name(
        f"broker-{conflicting.content_hash.removeprefix('sha256:')}.json"
    )
    from conclave.identity import write_immutable_record
    write_immutable_record(conflicting_path, conflicting)
    ref = conflicting_path.relative_to(ws.root).as_posix()
    with pytest.raises(IntegrityError, match="hash mismatch"):
        read_broker_profile(ws, ref)


def test_keyless_fixture_diagnostics_pass_and_are_content_addressed(ws):
    broker_record, broker_ref, _ = broker(ws)
    result, path, created = run_broker_check(
        ws, broker_profile_reference=broker_ref, checked_at=CREATED_AT,
    )
    assert created and result.status == "PASS" and result.reason_codes == []
    assert result.probe_result is not None
    assert result.time_source_classification == "diagnostic-local"
    assert result.authority_effect == result.decision_effect == result.membership_effect == "none"
    assert result.action_execution_allowed is False
    assert path.name == f"diagnostics-{result.content_hash.removeprefix('sha256:')}.json"
    retry, retry_path, retry_created = run_broker_check(
        ws, broker_profile_reference=broker_ref, checked_at=CREATED_AT,
    )
    assert not retry_created and retry == result and retry_path == path
    assert result.broker_profile_hash == broker_record.content_hash


def test_sandbox_check_fails_without_reading_credential_environment(ws, monkeypatch):
    _, ref, _ = broker(
        ws, classification="sandbox", credential="env:TOP_SECRET_SENTINEL",
        transport="sandbox:staging",
    )
    monkeypatch.setenv("TOP_SECRET_SENTINEL", "DO-NOT-READ-OR-EMIT")
    monkeypatch.setattr(os, "getenv", lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("credential environment was dereferenced")
    ))
    result, path, _ = run_broker_check(ws, broker_profile_reference=ref, checked_at=CREATED_AT)
    assert result.status == "FAIL"
    assert result.reason_codes == ["SANDBOX_TRANSPORT_NOT_AUTHORIZED"]
    assert "DO-NOT-READ-OR-EMIT" not in path.read_text(encoding="utf-8")


def test_missing_and_malformed_fixture_probe_fail_closed(ws, monkeypatch):
    _, ref, _ = broker(ws)
    import conclave.configuration as configuration

    monkeypatch.setattr(configuration, "_probe_path", lambda: None)
    unavailable, _, _ = run_broker_check(ws, broker_profile_reference=ref,
                                         checked_at=CREATED_AT)
    assert unavailable.reason_codes == ["FIXTURE_PROBE_UNAVAILABLE"]

    class Completed:
        returncode = 0
        stdout = b'{"unexpected":true}'
        stderr = b""

    monkeypatch.setattr(configuration, "_probe_path", lambda: Path(__file__))
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: Completed())
    malformed, _, _ = run_broker_check(
        ws, broker_profile_reference=ref, checked_at="2026-08-26T12:00:01Z"
    )
    assert malformed.reason_codes == ["FIXTURE_PROBE_MALFORMED"]


def test_probe_requires_flag_and_marker_and_has_no_signing_inputs():
    probe = Path(__file__).parent / "fixtures" / "idm_diagnostics_probe.py"
    missing = subprocess.run([sys.executable, str(probe), "--diagnostics-probe"],
                             capture_output=True, check=False, env={})
    assert missing.returncode == 2 and missing.stdout == b"" and missing.stderr == b""
    help_result = subprocess.run([sys.executable, str(probe), "--help"],
                                 capture_output=True, check=True, env={})
    help_text = help_result.stdout.decode("utf-8")
    for forbidden in ("key", "passphrase", "request", "envelope", "endpoint"):
        assert forbidden not in help_text.lower()


def test_diagnostics_event_and_reconciliation_are_factual_only(ws):
    _, ref, _ = broker(ws)
    ledger.initialise(ws, ws.load_config())
    result, path, _ = run_broker_check(ws, broker_profile_reference=ref, checked_at=CREATED_AT)
    ledger.record_event(ws, **diagnostics_event_fields(ws, result, path))
    event = ledger.read_events(ws)[-1]
    assert event["event_type"] == "fixture_broker_diagnostics_recorded"
    assert event["authority_level"] == "system"
    assert event["payload"]["authority_effect"] == "none"
    before = len(ledger.read_events(ws))
    reconcile(ws)
    assert len(ledger.read_events(ws)) == before

    # Remove only the event by rebuilding a fresh ledger around the already
    # immutable artifact, then prove reconciliation restores existence only.
    ws2 = Workspace.create(ws.root.parent / "reconcile", principal="Arthur")
    _, ref2, _ = broker(ws2)
    result2, _, _ = run_broker_check(ws2, broker_profile_reference=ref2,
                                     checked_at=CREATED_AT)
    ledger.initialise(ws2, ws2.load_config())
    report = reconcile(ws2)
    restored = next(e for e in report.created
                    if e["event_type"] == "fixture_broker_diagnostics_recorded")
    assert restored["artifact_hashes"]["diagnostics_result"] == result2.content_hash
    assert "no broker health" in restored["payload"]["note"]


def test_cli_exposes_exact_five_commands_and_no_default_selection(ws, monkeypatch):
    monkeypatch.setenv("CONCLAVE_HOME", str(ws.root))
    runner = CliRunner()
    created = runner.invoke(app, [
        "identity", "verifier-profile", "create", "--profile-id", "public-idm",
        "--expected-trust-input", TRUST_REF,
        "--expected-trust-domain", TDID,
    ])
    assert created.exit_code == 0, created.output
    verifier_ref = created.output.split("created: ", 1)[1].splitlines()[0]
    shown = runner.invoke(app, ["identity", "verifier-profile", "show",
                                "--profile", verifier_ref])
    assert shown.exit_code == 0 and '"profile_id": "public-idm"' in shown.output
    missing = runner.invoke(app, ["identity", "verifier-profile", "show"])
    assert missing.exit_code != 0

    broker_created = runner.invoke(app, [
        "evidence", "broker-profile", "create", "--profile-id", "fixture-broker",
        "--classification", "fixture-only", "--verifier-profile", verifier_ref,
        "--transport", FIXTURE_TRANSPORT, "--credential-reference", "none",
    ])
    assert broker_created.exit_code == 0, broker_created.output
    broker_ref = broker_created.output.split("created: ", 1)[1].splitlines()[0]
    broker_shown = runner.invoke(app, ["evidence", "broker-profile", "show",
                                       "--profile", broker_ref])
    assert broker_shown.exit_code == 0
    checked = runner.invoke(app, ["evidence", "broker-check",
                                  "--broker-profile", broker_ref])
    assert checked.exit_code == 0 and "status: PASS" in checked.output
    assert ws.load_config()["identity"]["mode"] == "local"


def test_symlink_profile_reference_is_rejected_when_supported(ws):
    _, ref, path = verifier(ws)
    link = path.with_name("linked.json")
    try:
        link.symlink_to(path)
    except OSError:
        pytest.skip("symlink creation is unavailable on this platform")
    bad_ref = str(Path(ref).with_name("linked.json")).replace("\\", "/")
    with pytest.raises(ValidationError, match="symlink|reparse"):
        read_verifier_profile(ws, bad_ref)


def test_closed_diagnostics_schema_rejects_authority_upgrade(ws):
    _, ref, _ = broker(ws)
    result, _, _ = run_broker_check(ws, broker_profile_reference=ref, checked_at=CREATED_AT)
    raw = result.model_dump(mode="json")
    raw["authority_effect"] = "approve"
    with pytest.raises(PydanticValidationError):
        DiagnosticsResult.model_validate(raw)
