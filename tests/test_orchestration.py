import yaml
import pytest
from typer.testing import CliRunner

from conclave import ledger
from conclave.cli import app
from conclave.concurrency import execute_concurrent, write_concurrent_outcome
from conclave.context import ContextSource, build_context_bundle
from conclave.errors import ValidationError
from conclave.orchestration import (
    OrchestrationRecord, orchestrate_batch, read_orchestration,
)
from conclave.providers import EgressDecision, FixtureAdapter
from conclave.reconcile import reconcile
from conclave.routing import ProviderCapability, TokenBudget, build_route, write_route_plan
from conclave.taskpacket import build_packet, write_packet
from conclave.workspace import Workspace


def make_workspace(
    tmp_path, *, risk="important", prohibited=False, invalid_stage: int | None = None
):
    ws = Workspace.create(tmp_path, principal="Arthur")
    packet = build_packet(
        objective="Orchestrate completed evidence", created_by="Arthur",
        target_objects=[] if prohibited else [{"object_id": "DOC-001"}],
        prohibited_objects=[{"object_id": "DOC-001"}] if prohibited else [],
    )
    write_packet(ws, packet)
    bundle = build_context_bundle(
        packet_ref=packet.ref, packet_content_hash=packet.content_hash,
        sources=[ContextSource.seal(
            object_id="DOC-001", status="active", authority="Arthur",
            classification="internal", content="facts",
        )],
    )
    capabilities = [
        ProviderCapability(provider="adrian", roles=frozenset({"lead"})),
        ProviderCapability(
            provider="claude", roles=frozenset({"critic", "synthesizer"})
        ),
        ProviderCapability(provider="gemini", roles=frozenset({"verifier"})),
    ]
    route = build_route(
        packet_ref=packet.ref, risk=risk, capabilities=capabilities,
        budget=TokenBudget(max_input_tokens=1000, max_output_tokens=400),
    )
    write_route_plan(ws, route)
    indices = tuple(
        index for index, stage in enumerate(route.stages)
        if stage.role != "synthesizer"
    )
    decision = EgressDecision(
        allowed=True, transports=frozenset({"fixture"}),
        classifications=frozenset({"internal"}), authority="Arthur",
        decision_ref="D7-ORCHESTRATION-TEST",
    )
    adapters = {}
    for index in indices:
        stage = route.stages[index]
        submission = {
            "handoff_packet": "handoff-packet/0.1.0",
            "packet_ref": packet.ref, "packet_content_hash": packet.content_hash,
            "provider": stage.provider, "role": stage.role, "status": "submitted",
            "objects_touched": [{"object_id": "DOC-001", "action": "read"}],
            "output": {
                "type": stage.role, "summary": f"{stage.role} complete", "body": "work"
            },
            "findings": [], "assumptions": [], "abstentions": [],
            "unresolved": [], "evidence_used": [],
            "recommended_next_action": "accept",
        }
        adapters[index] = FixtureAdapter(
            provider=stage.provider,
            response_text=(
                "not a handoff submission" if index == invalid_stage else
                "```yaml\n" + yaml.safe_dump(submission, sort_keys=False) + "```\n"
            ),
        )
    batch = execute_concurrent(
        packet=packet, bundle=bundle, plan=route, stage_indices=indices,
        adapters=adapters, decisions={index: decision for index in indices},
        models={index: f"model-{index}" for index in indices},
        prompts={index: f"isolated prompt {index}" for index in indices},
        estimated_input_tokens={index: 2 for index in indices},
    )
    stored = write_concurrent_outcome(ws, batch)
    return ws, packet, route, stored


def test_completed_batch_reaches_human_decision_pause(tmp_path):
    ws, _, _, stored = make_workspace(tmp_path)
    outcome = orchestrate_batch(ws, stored.batch_path)
    assert outcome.record.pause_state == "awaiting_human_decision"
    assert outcome.record.council_review_status == "ready_for_human_review"
    assert outcome.record.action_execution_allowed is False
    assert outcome.record.human_decision_required is True
    assert len(outcome.record.processed_stages) == 2
    assert all(stage.scope_status == "within_scope" for stage in outcome.record.processed_stages)
    assert len(list(ws.inbox_dir.glob("*.yaml"))) == 2
    assert len(list((ws.root / "scope").glob("*.yaml"))) == 2
    assert outcome.council.review.decision_block.decision == "pending"
    assert not list(ws.decisions_dir.glob("*.yaml"))


def test_orchestration_is_idempotent_for_unchanged_evidence(tmp_path):
    ws, _, _, stored = make_workspace(tmp_path)
    first = orchestrate_batch(ws, stored.batch_path)
    before = first.path.read_bytes()
    counts = (
        len(list(ws.inbox_dir.glob("*.yaml"))),
        len(list((ws.root / "scope").glob("*.yaml"))),
        len(list(ws.council_dir.glob("*.yaml"))),
        len(list(ws.orchestrations_dir.glob("*.yaml"))),
    )
    second = orchestrate_batch(ws, stored.batch_path)
    assert not second.created
    assert second.path == first.path and second.path.read_bytes() == before
    assert counts == (
        len(list(ws.inbox_dir.glob("*.yaml"))),
        len(list((ws.root / "scope").glob("*.yaml"))),
        len(list(ws.council_dir.glob("*.yaml"))),
        len(list(ws.orchestrations_dir.glob("*.yaml"))),
    )


def test_all_submissions_preflight_before_any_downstream_write(tmp_path):
    ws, _, _, stored = make_workspace(tmp_path, invalid_stage=1)
    with pytest.raises(ValidationError, match="not a Handoff submission"):
        orchestrate_batch(ws, stored.batch_path)
    assert not list(ws.inbox_dir.glob("*.yaml"))
    assert not list((ws.root / "scope").glob("*.yaml"))
    assert not list(ws.council_dir.glob("*.yaml"))


def test_canonical_wave_pauses_for_sequential_synthesizer(tmp_path):
    ws, _, _, stored = make_workspace(tmp_path, risk="canonical")
    outcome = orchestrate_batch(ws, stored.batch_path)
    assert outcome.record.pause_state == "awaiting_sequential_synthesizer"
    assert outcome.record.council_review_status == "incomplete"
    assert any("synthesizer" in item for item in outcome.council.review.missing_providers)
    assert outcome.record.action_execution_allowed is False


def test_scope_expansion_pauses_as_governance_block(tmp_path):
    ws, _, _, stored = make_workspace(tmp_path, prohibited=True)
    outcome = orchestrate_batch(ws, stored.batch_path)
    assert outcome.record.pause_state == "blocked_by_governance"
    assert outcome.record.council_review_status == "blocked_by_governance"
    assert all(stage.scope_status == "expansion_detected"
               for stage in outcome.record.processed_stages)


def test_record_schema_cannot_authorise_action(tmp_path):
    ws, _, _, stored = make_workspace(tmp_path)
    outcome = orchestrate_batch(ws, stored.batch_path)
    data = outcome.record.model_dump(mode="json")
    data["action_execution_allowed"] = True
    with pytest.raises(ValueError):
        OrchestrationRecord.model_validate(data)


def test_tampered_batch_is_refused_before_downstream_writes(tmp_path):
    ws, _, _, stored = make_workspace(tmp_path)
    data = yaml.safe_load(stored.batch_path.read_text(encoding="utf-8"))
    data["status"] = "failed"
    stored.batch_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValidationError):
        orchestrate_batch(ws, stored.batch_path)
    assert not list(ws.inbox_dir.glob("*.yaml"))


def test_external_batch_path_is_refused_even_if_bytes_are_valid(tmp_path):
    ws, _, _, stored = make_workspace(tmp_path)
    external = tmp_path / "copied-batch.yaml"
    external.write_bytes(stored.batch_path.read_bytes())
    with pytest.raises(ValidationError, match="inside this workspace"):
        orchestrate_batch(ws, external)
    assert not list(ws.inbox_dir.glob("*.yaml"))


def test_orchestration_reconciles_operational_event(tmp_path):
    ws, _, _, stored = make_workspace(tmp_path)
    ledger.initialise(ws, ws.load_config())
    outcome = orchestrate_batch(ws, stored.batch_path)
    reconcile(ws)
    events = ledger.read_events(ws)
    assert any(
        event["event_type"] == "orchestration_recorded"
        and event["artifact_hashes"].get("orchestration") == outcome.record.content_hash
        for event in events
    )


def test_cli_records_full_chain_and_stops_without_decision(tmp_path, monkeypatch):
    ws, _, _, stored = make_workspace(tmp_path)
    ledger.initialise(ws, ws.load_config())
    monkeypatch.setenv("CONCLAVE_HOME", str(ws.root))
    result = CliRunner().invoke(app, ["orchestrate", "batch", str(stored.batch_path)])
    assert result.exit_code == 0, result.output
    assert "ORCHESTRATION PAUSED: AWAITING_HUMAN_DECISION" in result.output
    assert "action execution : not authorised" in result.output
    event_types = [event["event_type"] for event in ledger.read_events(ws)]
    assert event_types[-1] == "orchestration_recorded"
    assert event_types.count("handoff_packet_imported") == 2
    assert event_types.count("scope_review_created") == 2
    assert event_types.count("council_review_created") == 1
    assert not any(event["event_type"] == "human_decision_recorded" for event in ledger.read_events(ws))
    loaded = read_orchestration(next(ws.orchestrations_dir.glob("*.yaml")))
    assert loaded.pause_state == "awaiting_human_decision"
