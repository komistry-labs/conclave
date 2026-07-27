"""Deterministic ledger reconciliation."""

import json

import pytest
import yaml

from conclave.errors import LedgerError
from conclave.handoff import import_response
from conclave.ledger import compute_entry_hash, initialise, read_events
from conclave.reconcile import RECONCILIATION_REASON, discover, reconcile
from conclave.relay import export_filename, export_prompts
from conclave.scope import review_handoff
from conclave.council import review_task
from conclave.taskpacket import build_packet, build_revision, write_packet
from conclave.workspace import Workspace


@pytest.fixture
def ws(tmp_path):
    return Workspace.create(tmp_path, principal="Arthur")


@pytest.fixture
def config(ws):
    return ws.load_config()


def full_workflow(ws, config, tmp_path):
    """Build a populated workspace with NO ledger, so everything needs reconciling."""
    packet = build_packet(
        objective="Draft RA-001 Part I", created_by="Arthur",
        target_objects=[{"object_id": "RA-001", "section_id": "RA-001-PART-I"}],
        read_only_objects=[{"object_id": "ADR-0002"}],
        prohibited_objects=[{"object_id": "KOS-CONSTITUTION"}],
        assigned_providers=[{"provider": "claude", "role": "governance_critic"}],
    )
    write_packet(ws, packet)
    export_prompts(ws, packet, config)

    body = {
        "handoff_packet": "handoff-packet/0.1.0",
        "packet_ref": packet.ref, "packet_content_hash": packet.content_hash,
        "provider": "claude", "role": "governance_critic", "status": "submitted",
        "objects_touched": [{"object_id": "RA-001", "section_id": "RA-001-PART-I",
                             "action": "proposed_change"}],
        "output": {"type": "critique", "summary": "s", "body": "b"},
        "findings": [], "assumptions": [], "abstentions": [], "unresolved": [],
        "evidence_used": [], "recommended_next_action": "revise",
    }
    src = tmp_path / "reply.md"
    src.write_text("```yaml\n" + yaml.safe_dump(body) + "```\n", encoding="utf-8")
    result = import_response(ws, src)
    assert result.status == "imported", [str(d) for d in result.defects]

    review_handoff(ws, result.handoff_path)
    review_task(ws, packet.task_id, 1)
    return packet


def types_of(events):
    return [e["event_type"] for e in events]


# -- discovery -------------------------------------------------------------

def test_discovers_all_supported_classes(ws, config, tmp_path):
    full_workflow(ws, config, tmp_path)
    candidates, unresolved = discover(ws)
    found = {c.event_type for c in candidates}
    assert found == {
        "task_packet_created", "relay_prompt_exported",
        "provider_response_preserved", "handoff_packet_imported",
        "scope_review_created", "council_review_created",
    }
    assert unresolved == []


def test_empty_workspace_discovers_nothing(ws):
    candidates, unresolved = discover(ws)
    assert candidates == [] and unresolved == []


# -- reconciliation --------------------------------------------------------

def test_reconcile_creates_missing_events(ws, config, tmp_path):
    full_workflow(ws, config, tmp_path)
    initialise(ws, config)
    report = reconcile(ws)
    assert len(report.created) == 6
    assert report.already_recorded == []
    assert report.unresolved == []


def test_reconciled_events_are_marked(ws, config, tmp_path):
    full_workflow(ws, config, tmp_path)
    initialise(ws, config)
    for e in reconcile(ws).created:
        assert e["payload"]["reconciled"] is True
        assert e["payload"]["reconciliation_reason"] == RECONCILIATION_REASON
        assert "source_artifact" in e["payload"]


def test_reconcile_is_idempotent(ws, config, tmp_path):
    full_workflow(ws, config, tmp_path)
    initialise(ws, config)
    reconcile(ws)
    before = ws.ledger_path.read_bytes()
    second = reconcile(ws)
    assert second.created == []
    assert len(second.already_recorded) == 6
    assert ws.ledger_path.read_bytes() == before


def test_reconcile_skips_events_already_recorded_live(ws, config, tmp_path):
    """Events written by the live path must not be duplicated."""
    initialise(ws, config)
    packet = build_packet(objective="o", created_by="Arthur",
                          target_objects=[{"object_id": "RA-001"}],
                          assigned_providers=[{"provider": "claude", "role": "r"}])
    write_packet(ws, packet)
    from conclave.ledger import append_event
    append_event(ws, event_type="task_packet_created", subject_refs=[packet.ref],
                 artifact_hashes={"task_packet": packet.content_hash})
    report = reconcile(ws)
    assert report.created == []
    assert any(c.event_type == "task_packet_created" for c in report.already_recorded)


def test_reconcile_after_ledger_init_on_populated_workspace(ws, config, tmp_path):
    """Snapshot bridges history; reconcile then adds the operational events."""
    full_workflow(ws, config, tmp_path)
    initialise(ws, config)
    assert types_of(read_events(ws)) == ["workspace_genesis", "workspace_snapshot_attested"]
    reconcile(ws)
    after = types_of(read_events(ws))
    assert after[0] == "workspace_genesis"
    assert "council_review_created" in after
    assert len(after) == 8


# -- timestamps ------------------------------------------------------------

def test_uses_artifact_timestamp_where_available(ws, config, tmp_path):
    packet = full_workflow(ws, config, tmp_path)
    initialise(ws, config)
    created = {e["event_type"]: e for e in reconcile(ws).created}
    tp = created["task_packet_created"]
    assert tp["occurred_at"] == packet.created_at
    assert "original_event_time_unknown" not in tp["payload"]


def test_states_unknown_time_where_artifact_has_none(ws, config, tmp_path):
    full_workflow(ws, config, tmp_path)
    initialise(ws, config)
    created = {e["event_type"]: e for e in reconcile(ws).created}
    raw = created["provider_response_preserved"]
    assert raw["payload"]["original_event_time_unknown"] is True
    assert "does not indicate when the operation happened" in raw["payload"]["time_note"]


def test_handoff_uses_imported_at(ws, config, tmp_path):
    full_workflow(ws, config, tmp_path)
    initialise(ws, config)
    created = {e["event_type"]: e for e in reconcile(ws).created}
    handoff = created["handoff_packet_imported"]
    stored = yaml.safe_load(next(ws.inbox_dir.glob("*.yaml")).read_text(encoding="utf-8"))
    assert handoff["occurred_at"] == stored["imported_at"]


def test_no_fabricated_ordering_claim(ws, config, tmp_path):
    """Sequence numbers record reconciliation order, not operational order."""
    full_workflow(ws, config, tmp_path)
    initialise(ws, config)
    for e in reconcile(ws).created:
        text = json.dumps(e)
        assert "happened before" not in text
        assert "happened after" not in text


# -- replacement -----------------------------------------------------------

def test_replacement_reconciled_only_when_record_proves_it(ws, config, tmp_path):
    packet = build_packet(objective="o", created_by="Arthur",
                          target_objects=[{"object_id": "RA-001"}],
                          assigned_providers=[{"provider": "claude", "role": "r"}])
    write_packet(ws, packet)
    export_prompts(ws, packet, config)
    (ws.outbox_dir / export_filename(packet, "claude")).write_text("tampered\n",
                                                                   encoding="utf-8")
    export_prompts(ws, packet, config, force=True, reason="restored", authority="Arthur")

    initialise(ws, config)
    created = types_of(reconcile(ws).created)
    assert "relay_prompt_exported" in created
    assert "relay_prompt_replaced" in created


def test_no_replacement_event_without_proof(ws, config, tmp_path):
    packet = build_packet(objective="o", created_by="Arthur",
                          target_objects=[{"object_id": "RA-001"}],
                          assigned_providers=[{"provider": "claude", "role": "r"}])
    write_packet(ws, packet)
    export_prompts(ws, packet, config)
    initialise(ws, config)
    assert "relay_prompt_replaced" not in types_of(reconcile(ws).created)


# -- rejection -------------------------------------------------------------

def test_rejection_reconciled_from_repair_artifact(ws, config, tmp_path):
    src = tmp_path / "bad.md"
    src.write_text("no yaml at all", encoding="utf-8")
    import_response(ws, src)
    initialise(ws, config)
    created = types_of(reconcile(ws).created)
    assert "provider_response_rejected" in created


def test_orphan_repair_artifact_is_unresolved(ws, config):
    from conclave.handoff import repair_dir
    d = repair_dir(ws)
    d.mkdir(parents=True, exist_ok=True)
    (d / "aaaaaaaaaaaa__repair.md").write_text("orphan\n", encoding="utf-8")
    initialise(ws, config)
    report = reconcile(ws)
    assert any("no raw response found" in u.reason for u in report.unresolved)


# -- refusal and ambiguity -------------------------------------------------

def test_refuses_without_ledger(ws, config, tmp_path):
    full_workflow(ws, config, tmp_path)
    with pytest.raises(LedgerError, match="no ledger"):
        reconcile(ws)


def test_refuses_on_damaged_chain(ws, config, tmp_path):
    full_workflow(ws, config, tmp_path)
    initialise(ws, config)
    events = read_events(ws)
    events[1]["payload"]["artifact_count"] = 999
    ws.ledger_path.write_text(
        "".join(json.dumps(e, sort_keys=True, separators=(",", ":")) + "\n" for e in events),
        encoding="utf-8")
    with pytest.raises(LedgerError, match="does not verify"):
        reconcile(ws)


def test_unverifiable_artifact_is_unresolved_not_attested(ws, config, tmp_path):
    packet = full_workflow(ws, config, tmp_path)
    from conclave.taskpacket import packet_path
    path = packet_path(ws, packet.task_id, 1)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["objective"] = "altered after the fact"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    initialise(ws, config)
    report = reconcile(ws)
    assert any("content_hash does not verify" in u.reason for u in report.unresolved)
    assert "task_packet_created" not in types_of(report.created)


def test_unreadable_artifact_is_unresolved(ws, config):
    from conclave.scope import scope_dir
    scope_dir(ws).mkdir(parents=True, exist_ok=True)
    (scope_dir(ws) / "broken.yaml").write_text("not: [valid", encoding="utf-8")
    initialise(ws, config)
    assert any("unreadable" in u.reason for u in reconcile(ws).unresolved)


def test_never_infers_human_decisions(ws, config, tmp_path):
    full_workflow(ws, config, tmp_path)
    initialise(ws, config)
    created = types_of(reconcile(ws).created)
    assert "human_decision_recorded" not in created
    assert "action_authorised" not in created


def test_reconciled_chain_verifies(ws, config, tmp_path):
    from conclave.ledger import verify
    full_workflow(ws, config, tmp_path)
    initialise(ws, config)
    reconcile(ws)
    assert verify(ws).ok


def test_advisory_authority_preserved_for_provider_events(ws, config, tmp_path):
    full_workflow(ws, config, tmp_path)
    initialise(ws, config)
    created = {e["event_type"]: e for e in reconcile(ws).created}
    assert created["handoff_packet_imported"]["authority_level"] == "advisory_agent"
    assert created["handoff_packet_imported"]["actor"] == "claude"
    assert created["council_review_created"]["authority_level"] == "system"


def test_report_separates_the_three_outcomes(ws, config, tmp_path):
    from conclave.handoff import repair_dir
    full_workflow(ws, config, tmp_path)
    d = repair_dir(ws)
    d.mkdir(parents=True, exist_ok=True)
    (d / "bbbbbbbbbbbb__repair.md").write_text("orphan\n", encoding="utf-8")
    initialise(ws, config)
    reconcile(ws)
    second = reconcile(ws)
    assert second.created == []
    assert second.already_recorded
    assert second.unresolved
