"""Increment 20D closed report and bounded security-closeout tests."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError

from conclave import ledger
from conclave.conformance import (
    REQUIRED_CONTROLS,
    SandboxBrokerConformanceReport,
    create_conformance_report,
    read_conformance_report,
)
from conclave.identity import FROZEN_IDM_IMPLEMENTATION
from conclave.reconcile import reconcile
from conclave.workspace import Workspace

H = "sha256:" + "a" * 64
NOW = "2026-08-27T12:00:00Z"


def _ref(reference: str) -> dict:
    return {"reference": reference, "content_hash": H}


def _data(status: str = "PASS") -> dict:
    reason = [] if status == "PASS" else ["EVIDENCE_NOT_AVAILABLE"]
    overall = "PASS" if status == "PASS" else "INCOMPLETE" if status == "NOT_RUN" else "FAIL"
    return {
        "profile": "sandbox-broker-conformance-report",
        "schema_version": "sandbox-broker-conformance-report/0.1.0",
        "conclave_commit": "1" * 40,
        "conclave_tree": "2" * 40,
        "protocol_documents": [
            {"increment": name, **_ref(f"source/INCREMENT-{name}.md")}
            for name in ("20A", "20B", "20C", "20D")
        ],
        "idm_pin_document": _ref("source/policies/idm-reference-pin.json"),
        "idm_implementation": FROZEN_IDM_IMPLEMENTATION.model_dump(mode="json"),
        "platform_evidence": [
            {"os": os_name, "python_version": py, "test_suite_id": "conclave-20d-full-v1",
             "status": status, "required_security_skips": 0,
             "report": _ref(f"reports/{os_name}-py{py}.json"), "reason_codes": reason}
            for os_name, py in (("windows", "3.12"), ("ubuntu", "3.13"), ("macos", "3.12"))
        ],
        "package_evidence": [
            {"kind": kind, "artifact": _ref(f"packages/conclave.{kind}"),
             "inventory": _ref(f"reports/{kind}-inventory.json"),
             "status": status, "reason_codes": reason}
            for kind in ("sdist", "wheel")
        ],
        "dependency_and_workflow_evidence": [
            _ref("source/.github/workflows/tests.yml"),
            _ref("source/tests/fixtures/idm-baseline/requirements.lock"),
        ],
        "machine_reports": [
            {"kind": kind, **_ref(f"reports/{kind.lower()}.json"),
             "status": status, "reason_codes": reason}
            for kind in ("PACKAGE", "SECRET_SCAN", "STATIC_SCAN", "TEST")
        ],
        "findings": [
            {"control_id": control, "status": status,
             "evidence": [_ref(f"reports/controls/{index:02d}.json")],
             "reason_codes": reason}
            for index, control in enumerate(REQUIRED_CONTROLS, 1)
        ],
        "overall_status": overall,
        "live_sandbox_exercised": False,
        "production_ready": False,
        "production_use_allowed": False,
        "authority_effect": "none",
        "decision_effect": "none",
        "membership_effect": "none",
        "action_execution_allowed": False,
        "created_at": NOW,
        "time_source_classification": "diagnostic-local",
    }


@pytest.fixture
def ws(tmp_path: Path) -> Workspace:
    result = Workspace.create(tmp_path, principal="Arthur")
    ledger.initialise(result, result.load_config())
    return result


def test_pass_report_is_closed_hash_addressed_immutable_and_factual(ws: Workspace):
    report, path, created = create_conformance_report(ws, _data())
    assert created and report.overall_status == "PASS"
    assert path.parent == ws.signing_conformance_reports_dir
    assert path.name == f"conformance-{report.content_hash.removeprefix('sha256:')}.json"
    assert read_conformance_report(path) == report
    assert create_conformance_report(ws, _data())[2] is False
    event = ledger.read_events(ws)[-1]
    assert event["event_type"] == "sandbox_broker_conformance_report_recorded"
    assert event["authority_level"] == "system"
    assert event["payload"]["production_ready"] is False
    assert "approval" in event["payload"]["note"]


@pytest.mark.parametrize("field,value", [
    ("production_ready", True),
    ("production_use_allowed", True),
    ("live_sandbox_exercised", True),
    ("action_execution_allowed", True),
    ("authority_effect", "approval"),
    ("decision_effect", "decision"),
    ("membership_effect", "membership"),
])
def test_report_cannot_claim_production_authority_or_live_use(field, value):
    data = _data()
    data[field] = value
    with pytest.raises(PydanticValidationError):
        create_conformance_report.__globals__["seal_record"](SandboxBrokerConformanceReport, data)


def test_missing_or_not_run_evidence_can_never_claim_pass(ws: Workspace):
    missing = _data()
    missing["findings"].pop()
    with pytest.raises(PydanticValidationError, match="frozen control matrix"):
        create_conformance_report(ws, missing)

    not_run = _data("NOT_RUN")
    not_run["overall_status"] = "PASS"
    with pytest.raises(PydanticValidationError, match="INCOMPLETE"):
        create_conformance_report(ws, not_run)
    report, _, _ = create_conformance_report(ws, _data("NOT_RUN"))
    assert report.overall_status == "INCOMPLETE"


def test_fail_evidence_forces_overall_fail(ws: Workspace):
    data = _data()
    data["findings"][0]["status"] = "FAIL"
    data["findings"][0]["reason_codes"] = ["CONTROL_FAILED"]
    data["overall_status"] = "FAIL"
    report, _, _ = create_conformance_report(ws, data)
    assert report.overall_status == "FAIL"


@pytest.mark.parametrize("reference", [
    "/absolute/report.json", "C:/report.json", "../report.json", "a/../report.json",
    "\\\\server\\share\\report.json", "reports\\report.json", "report.json:stream",
])
def test_evidence_references_reject_drive_unc_ads_traversal_and_backslash(ws, reference):
    data = _data()
    data["idm_pin_document"]["reference"] = reference
    with pytest.raises(PydanticValidationError, match="canonical relative POSIX"):
        create_conformance_report(ws, data)


def test_unknown_fields_tampering_and_wrong_filename_are_rejected(ws: Workspace):
    report, path, _ = create_conformance_report(ws, _data())
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["unknown"] = True
    with pytest.raises(PydanticValidationError):
        SandboxBrokerConformanceReport.model_validate(raw)
    raw.pop("unknown")
    raw["conclave_tree"] = "3" * 40
    with pytest.raises(PydanticValidationError, match="content_hash"):
        SandboxBrokerConformanceReport.model_validate(raw)
    other = path.with_name("conformance-" + "0" * 64 + ".json")
    other.write_bytes(path.read_bytes())
    with pytest.raises(Exception, match="FILENAME_MISMATCH"):
        read_conformance_report(other)
    assert report.content_hash in path.read_text(encoding="utf-8")


def test_reconciliation_restores_existence_only_without_inference(ws: Workspace):
    report, _, _ = create_conformance_report(ws, _data(), record_ledger=False)
    outcome = reconcile(ws)
    event = next(item for item in outcome.created
                 if item["event_type"] == "sandbox_broker_conformance_report_recorded")
    assert event["artifact_hashes"]["sandbox_broker_conformance_report"] == report.content_hash
    assert "not inferred" in event["payload"]["note"]
    assert event["payload"]["reconciled"] is True


def test_increment20_runtime_has_no_key_signing_allocation_or_dynamic_execution_surface():
    root = Path(__file__).parents[1] / "src" / "conclave"
    # 20A fixture diagnostics deliberately invoke a pinned public verifier in
    # a subprocess.  The transport/recovery/conformance surfaces themselves
    # must never acquire a shell, dynamic execution or crypto/key library.
    files = [root / name for name in (
        "sandbox_transport.py", "sandbox_recovery.py", "conformance.py"
    )]
    forbidden_import_roots = {"subprocess", "cryptography", "nacl", "jose"}
    forbidden_calls = {"eval", "exec", "compile", "__import__"}
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not ({item.name.split(".")[0] for item in node.names} & forbidden_import_roots)
            elif isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in forbidden_import_roots
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden_calls


def test_installed_wheel_configuration_excludes_tests_and_fixture_material():
    root = Path(__file__).parents[1]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'packages = ["src/conclave"]' in text
    assert "tests/fixtures" not in text
    assert "conclave/policies/idm-reference-pin.json" in text


def test_workspace_area_is_dormant_until_a_report_is_explicitly_created(tmp_path: Path):
    ws = Workspace.create(tmp_path, principal="Arthur")
    assert ws.signing_conformance_reports_dir.is_dir()
    assert list(ws.signing_conformance_reports_dir.iterdir()) == []
