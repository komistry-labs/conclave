import yaml
import pytest
from typer.testing import CliRunner

from conclave.cli import app
from conclave.council import CouncilReview, seal as seal_council, write_council
from conclave.decision import (
    DecisionInstruction,
    read_decision,
    record_decision,
    verify_decision_content_hash,
)
from conclave.errors import ValidationError
from conclave.ledger import append_event, initialise, read_events, verify
from conclave.taskpacket import build_packet, write_packet
from conclave.workspace import Workspace


@pytest.fixture
def ws(tmp_path):
    workspace = Workspace.create(tmp_path, principal="Arthur")
    initialise(workspace, workspace.load_config())
    return workspace


def council(ws, *, status="ready_for_human_review"):
    packet = build_packet(
        objective="Review bounded change",
        created_by="Arthur",
        target_objects=[{"object_id": "RA-001"}],
        assigned_providers=[],
    )
    write_packet(ws, packet)
    review = seal_council(CouncilReview(
        council_review_id=f"CR-{packet.task_id}-v1-dec1510abc",
        task_packet_ref=packet.ref,
        task_packet_hash=packet.content_hash,
        created_at="2026-08-16T10:00:00Z",
        review_status=status,
        human_decision_required=True,
    ))
    paths = write_council(ws, review)
    return packet, review, paths


def instruction(review, **changes):
    data = {
        "council_review_id": review.council_review_id,
        "council_review_hash": review.content_hash,
        "decision": "approve",
        "decided_by": "Arthur",
        "decided_at": "2026-08-16T10:10:00Z",
        "rationale": "The bounded evidence satisfies the stated acceptance criteria.",
        "authorised_actions": ["Create the approved bounded implementation commit."],
        "authority_ref": "Arthur approval recorded in the governing session.",
    }
    data.update(changes)
    return DecisionInstruction.model_validate(data)


def test_records_separate_immutable_decision_and_ledger_event(ws):
    _, review, (review_yaml, _) = council(ws)
    before = review_yaml.read_bytes()
    outcome = record_decision(ws, instruction(review), confirmed_principal="Arthur")

    assert outcome.created
    assert outcome.yaml_path.exists() and outcome.markdown_path.exists()
    assert review_yaml.read_bytes() == before
    assert yaml.safe_load(review_yaml.read_text(encoding="utf-8"))["decision_block"] == {
        "decision": "pending", "decided_by": None, "decided_at": None,
        "rationale": None, "authorised_actions": [],
    }
    loaded = read_decision(outcome.yaml_path)
    assert verify_decision_content_hash(loaded)
    event = read_events(ws)[-1]
    assert event["event_type"] == "human_decision_recorded"
    assert event["actor"] == "Arthur"
    assert event["authority_level"] == "human_principal"
    assert event["artifact_hashes"]["authority_decision"] == loaded.content_hash
    assert verify(ws).ok


def test_wrong_confirmation_writes_nothing(ws):
    _, review, _ = council(ws)
    with pytest.raises(ValidationError, match="confirmation did not match"):
        record_decision(ws, instruction(review), confirmed_principal="claude")
    assert not list(ws.decisions_dir.glob("*"))
    assert not any(e["event_type"] == "human_decision_recorded" for e in read_events(ws))


def test_wrong_decided_by_refused(ws):
    _, review, _ = council(ws)
    with pytest.raises(ValidationError, match="not the workspace principal"):
        record_decision(
            ws, instruction(review, decided_by="Gemini"), confirmed_principal="Arthur"
        )


def test_review_hash_mismatch_refused(ws):
    _, review, _ = council(ws)
    with pytest.raises(ValidationError, match="different Council Review hash"):
        record_decision(
            ws,
            instruction(review, council_review_hash="sha256:" + "0" * 64),
            confirmed_principal="Arthur",
        )


def test_tampered_review_refused(ws):
    _, review, (path, _) = council(ws)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["review_status"] = "blocked_by_governance"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValidationError, match="does not verify"):
        record_decision(ws, instruction(review), confirmed_principal="Arthur")


def test_approve_only_when_ready(ws):
    _, review, _ = council(ws, status="incomplete")
    with pytest.raises(ValidationError, match="ready_for_human_review"):
        record_decision(ws, instruction(review), confirmed_principal="Arthur")


def test_defer_incomplete_review_but_cannot_authorise_actions(ws):
    _, review, _ = council(ws, status="incomplete")
    deferred = instruction(review, decision="defer", authorised_actions=[])
    assert record_decision(ws, deferred, confirmed_principal="Arthur").record.decision == "defer"
    with pytest.raises(ValueError, match="cannot authorise actions"):
        instruction(review, decision="defer", authorised_actions=["do it"])


def test_exact_retry_is_idempotent_and_conflict_refused(ws):
    _, review, _ = council(ws)
    first = record_decision(ws, instruction(review), confirmed_principal="Arthur")
    count = len(read_events(ws))
    second = record_decision(ws, instruction(review), confirmed_principal="Arthur")
    assert first.yaml_path == second.yaml_path
    assert not second.created
    assert len(read_events(ws)) == count

    with pytest.raises(ValidationError, match="already has an immutable"):
        record_decision(
            ws,
            instruction(review, rationale="A materially different decision rationale."),
            confirmed_principal="Arthur",
        )


def test_requires_initialised_healthy_ledger(tmp_path):
    workspace = Workspace.create(tmp_path, principal="Arthur")
    _, review, _ = council(workspace)
    with pytest.raises(ValidationError, match="initialised ledger"):
        record_decision(
            workspace, instruction(review), confirmed_principal="Arthur"
        )


def test_closed_instruction_schema_and_utc_time():
    with pytest.raises(ValueError):
        DecisionInstruction.model_validate({
            "council_review_id": "CR-x", "council_review_hash": "sha256:" + "0" * 64,
            "decision": "reject", "decided_by": "Arthur",
            "decided_at": "2026-08-16T10:10:00", "rationale": "No.",
            "authority_ref": "session", "approved": True,
        })


def test_instruction_rejects_path_like_council_id():
    with pytest.raises(ValueError):
        DecisionInstruction.model_validate({
            "council_review_id": "../config", "council_review_hash": "sha256:" + "0" * 64,
            "decision": "reject", "decided_by": "Arthur",
            "decided_at": "2026-08-16T10:10:00Z", "rationale": "No.",
            "authority_ref": "session",
        })


def test_ledger_rejects_nonhuman_actor_for_human_event(ws):
    with pytest.raises(Exception, match="requires authority_level 'human_principal'"):
        append_event(ws, event_type="human_decision_recorded", authority_level="system")


def test_ledger_rejects_wrong_named_human_principal(ws):
    with pytest.raises(Exception, match="not the configured workspace principal"):
        append_event(
            ws, event_type="human_decision_recorded", actor="Claude",
            authority_level="human_principal",
        )


def test_cli_requires_exact_interactive_principal(ws, tmp_path, monkeypatch):
    _, review, _ = council(ws)
    path = tmp_path / "decision.yaml"
    path.write_text(yaml.safe_dump(instruction(review).to_serialisable(), sort_keys=False),
                    encoding="utf-8")
    monkeypatch.setenv("CONCLAVE_HOME", str(ws.root))
    runner = CliRunner()

    refused = runner.invoke(app, ["council", "record-decision", str(path)], input="Claude\n")
    assert refused.exit_code == 1
    assert not list(ws.decisions_dir.glob("*.yaml"))

    accepted = runner.invoke(app, ["council", "record-decision", str(path)], input="Arthur\n")
    assert accepted.exit_code == 0, accepted.output
    assert "DECISION RECORDED" in accepted.output
    assert list(ws.decisions_dir.glob("*.yaml"))


def test_reconciliation_never_infers_human_decision(ws):
    from conclave.reconcile import discover

    _, review, _ = council(ws)
    record_decision(ws, instruction(review), confirmed_principal="Arthur")
    candidates, _ = discover(ws)
    assert "human_decision_recorded" not in {candidate.event_type for candidate in candidates}
