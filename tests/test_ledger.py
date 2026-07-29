"""Hash-chained event ledger: genesis, chaining, append-only, verification."""

import json
import os
import time

import pytest

from conclave import ledger
from conclave.errors import LedgerError
from conclave.ledger import (
    GENESIS_EVENT,
    LEDGER_SCHEMA_VERSION,
    REQUIRED_FIELDS,
    append_event,
    build_snapshot_manifest,
    canonical_json,
    compute_entry_hash,
    derive_event_id,
    exclusive_lock,
    initialise,
    read_events,
    record_event,
    verify,
)
from conclave.workspace import Workspace


@pytest.fixture
def ws(tmp_path):
    return Workspace.create(tmp_path, principal="Arthur")


@pytest.fixture
def config(ws):
    return ws.load_config()


@pytest.fixture
def live(ws, config):
    initialise(ws, config)
    return ws


def codes(report):
    return {d.code for d in report.defects}


def rewrite(ws, events):
    """Write raw lines directly, bypassing append. For damage simulation only."""
    ws.ledger_path.write_text(
        "".join(canonical_json(e) + "\n" for e in events), encoding="utf-8")


# -- genesis ---------------------------------------------------------------

def test_genesis_created(ws, config):
    events = initialise(ws, config)
    g = events[0]
    assert g["sequence"] == 1
    assert g["previous_entry_hash"] is None
    assert g["event_type"] == GENESIS_EVENT
    assert g["authority_level"] == "system"
    assert g["actor"] == "conclave"


def test_genesis_payload_identifies_workspace(ws, config):
    p = initialise(ws, config)[0]["payload"]
    assert p["principal"] == "Arthur"
    assert p["bootstrap_version"] == "0.3.0"
    assert p["authority_policy"]["agents_may_merge"] is False
    assert p["hashing_algorithm"] == "sha256"
    assert p["canonicalisation"] == "kos-canonical-text-v1"
    assert p["kos_access"] == "read-only"


def test_genesis_plus_snapshot(ws, config):
    events = initialise(ws, config)
    assert len(events) == 2
    assert events[1]["event_type"] == "workspace_snapshot_attested"
    assert events[1]["sequence"] == 2
    assert events[1]["previous_entry_hash"] == events[0]["entry_hash"]


def test_genesis_verifies(live):
    assert verify(live).ok


def test_initialise_is_idempotent(ws, config):
    initialise(ws, config)
    before = ws.ledger_path.read_bytes()
    initialise(ws, config)
    assert ws.ledger_path.read_bytes() == before


def test_append_before_genesis_refused(ws):
    with pytest.raises(LedgerError, match="no genesis"):
        append_event(ws, event_type="task_packet_created", subject_refs=["TP-x@v1"])


def test_genesis_cannot_be_appended_directly(live):
    with pytest.raises(LedgerError, match="genesis is created by"):
        append_event(live, event_type=GENESIS_EVENT)


# -- snapshot bridge -------------------------------------------------------

def test_empty_workspace_snapshot(ws, config):
    events = initialise(ws, config)
    assert events[1]["payload"]["artifact_count"] == 0
    assert events[1]["payload"]["classes"] == {}


def test_populated_workspace_snapshot(ws, config):
    from conclave.relay import export_prompts
    from conclave.taskpacket import build_packet, write_packet
    p = build_packet(objective="o", created_by="Arthur",
                     target_objects=[{"object_id": "RA-001"}],
                     assigned_providers=[{"provider": "claude", "role": "governance_critic"}])
    write_packet(ws, p)
    export_prompts(ws, p, config)

    payload = initialise(ws, config)[1]["payload"]
    assert payload["artifact_count"] >= 3
    assert "task_packets" in payload["classes"]
    assert "relay_prompts" in payload["classes"]
    assert "relay_export_records" in payload["classes"]


def test_snapshot_manifest_is_deterministic(ws, config):
    from conclave.taskpacket import build_packet, write_packet
    write_packet(ws, build_packet(objective="o", created_by="A",
                                  target_objects=[{"object_id": "X"}],
                                  assigned_providers=[{"provider": "claude", "role": "r"}]))
    assert build_snapshot_manifest(ws) == build_snapshot_manifest(ws)


def test_snapshot_records_file_hashes(ws, config):
    """The snapshot hashes the FILE, not the object body.

    A packet's own content_hash covers its body excluding that field. The
    snapshot needs to detect tampering with the whole file — including with
    the recorded content_hash line itself — so it hashes the file as stored.
    """
    from conclave.hashing import hash_file
    from conclave.taskpacket import build_packet, packet_path, write_packet
    p = build_packet(objective="o", created_by="A", target_objects=[{"object_id": "X"}],
                     assigned_providers=[{"provider": "claude", "role": "r"}])
    write_packet(ws, p)
    entry = initialise(ws, config)[1]["payload"]["classes"]["task_packets"][0]
    assert entry["content_hash"] == hash_file(packet_path(ws, p.task_id, 1))
    assert entry["path"].startswith("tasks/")
    assert entry["hashing"] == "kos-canonical-text-v1"


def test_snapshot_detects_tampering_with_a_declared_content_hash(ws, config):
    """Hashing the file catches edits the object's own hash field would not."""
    from conclave.taskpacket import build_packet, packet_path, write_packet
    p = build_packet(objective="o", created_by="A", target_objects=[{"object_id": "X"}],
                     assigned_providers=[{"provider": "claude", "role": "r"}])
    write_packet(ws, p)
    before = build_snapshot_manifest(ws)
    path = packet_path(ws, p.task_id, 1)
    path.write_text(path.read_text(encoding="utf-8").replace(
        "content_hash:", "content_hash:  "), encoding="utf-8")
    assert build_snapshot_manifest(ws) != before


def test_raw_responses_hashed_as_binary(ws, config):
    raw = ws.inbox_dir / "raw"
    raw.mkdir(parents=True)
    (raw / "aa.raw.md").write_bytes(b"crlf\r\nbody\r\n")
    entry = initialise(ws, config)[1]["payload"]["classes"]["raw_provider_responses"][0]
    assert entry["hashing"] == "binary"
    from conclave.hashing import hash_bytes
    assert entry["content_hash"] == hash_bytes(b"crlf\r\nbody\r\n", binary=True)


def test_snapshot_states_chronology_is_not_asserted(ws, config):
    payload = initialise(ws, config)[1]["payload"]
    assert "predate ledger instrumentation" in payload["chronology_note"]
    assert "No historical events have been fabricated." in payload["chronology_note"]
    assert "snapshot_taken_at" in payload


def test_no_fabricated_historical_events(ws, config):
    """Only genesis and one snapshot. Nothing pretending to be older."""
    from conclave.taskpacket import build_packet, write_packet
    write_packet(ws, build_packet(objective="o", created_by="A",
                                  target_objects=[{"object_id": "X"}],
                                  assigned_providers=[{"provider": "claude", "role": "r"}]))
    events = initialise(ws, config)
    assert [e["event_type"] for e in events] == [GENESIS_EVENT, "workspace_snapshot_attested"]
    assert not any(e["event_type"] == "task_packet_created" for e in events)


def test_kos_repository_excluded_from_snapshot(ws, config, tmp_path):
    """KOS is external and read-only. It is not CONCLAVE's to attest to."""
    kos = tmp_path / "KOS"
    (kos / "architecture" / "decisions").mkdir(parents=True)
    (kos / "architecture" / "decisions" / "ADR-0001.md").write_text("x", encoding="utf-8")
    config["kos_repository"] = str(kos)

    payload = initialise(ws, config)[1]["payload"]
    assert "the KOS repository" in payload["excludes"][0]
    serialised = canonical_json(payload)
    assert "ADR-0001" not in serialised
    assert str(kos) not in serialised


# -- hash chaining ---------------------------------------------------------

def test_entry_hash_excludes_itself(live):
    e = read_events(live)[0]
    assert compute_entry_hash(e) == e["entry_hash"]
    assert compute_entry_hash({**e, "entry_hash": "sha256:" + "0" * 64}) == e["entry_hash"]


def test_chain_links(live):
    for _ in range(3):
        append_event(live, event_type="task_packet_created",
                     subject_refs=[f"TP-{_}@v1"],
                     artifact_hashes={"task_packet": "sha256:" + str(_) * 64})
    events = read_events(live)
    for prev, cur in zip(events, events[1:]):
        assert cur["previous_entry_hash"] == prev["entry_hash"]
    assert verify(live).ok


def test_sequences_contiguous_from_one(live):
    for i in range(3):
        append_event(live, event_type="task_packet_created", subject_refs=[f"TP-{i}@v1"])
    assert [e["sequence"] for e in read_events(live)] == [1, 2, 3, 4, 5]


def test_final_chain_hash_reported(live):
    report = verify(live)
    assert report.final_chain_hash == read_events(live)[-1]["entry_hash"]
    assert report.entry_count == 2


# -- damage detection ------------------------------------------------------

def test_altered_payload_detected(live):
    events = read_events(live)
    events[1]["payload"]["artifact_count"] = 999
    rewrite(live, events)
    assert "entry-hash-mismatch" in codes(verify(live))


def test_broken_previous_hash_detected(live):
    events = read_events(live)
    events[1]["previous_entry_hash"] = "sha256:" + "0" * 64
    events[1]["entry_hash"] = compute_entry_hash(events[1])   # re-seal the entry itself
    rewrite(live, events)
    assert "broken-chain" in codes(verify(live))


def test_malformed_json_line_detected(live):
    with live.ledger_path.open("a", encoding="utf-8") as fh:
        fh.write("{not json\n")
    assert "malformed-json" in codes(verify(live))


def test_missing_required_field_detected(live):
    events = read_events(live)
    del events[1]["actor"]
    rewrite(live, events)
    assert "missing-required-field" in codes(verify(live))


@pytest.mark.parametrize("field", REQUIRED_FIELDS)
def test_every_required_field_is_checked(live, field):
    events = read_events(live)
    del events[1][field]
    rewrite(live, events)
    assert "missing-required-field" in codes(verify(live))


def test_duplicate_sequence_detected(live):
    events = read_events(live)
    events[1]["sequence"] = 1
    events[1]["entry_hash"] = compute_entry_hash(events[1])
    rewrite(live, events)
    assert "duplicate-sequence" in codes(verify(live))


def test_sequence_gap_detected(live):
    events = read_events(live)
    events[1]["sequence"] = 7
    events[1]["entry_hash"] = compute_entry_hash(events[1])
    rewrite(live, events)
    assert "sequence-gap" in codes(verify(live))


def test_duplicate_event_id_detected(live):
    events = read_events(live)
    events[1]["event_id"] = events[0]["event_id"]
    events[1]["entry_hash"] = compute_entry_hash(events[1])
    rewrite(live, events)
    assert "duplicate-event-id" in codes(verify(live))


def test_multiple_genesis_detected(live):
    events = read_events(live)
    events[1]["event_type"] = GENESIS_EVENT
    events[1]["entry_hash"] = compute_entry_hash(events[1])
    rewrite(live, events)
    assert "multiple-genesis" in codes(verify(live))


def test_genesis_not_first_detected(live):
    events = read_events(live)
    events[0]["event_type"] = "workspace_snapshot_attested"
    events[0]["entry_hash"] = compute_entry_hash(events[0])
    events[1]["event_type"] = GENESIS_EVENT
    events[1]["entry_hash"] = compute_entry_hash(events[1])
    rewrite(live, events)
    assert "genesis-not-first" in codes(verify(live))


def test_missing_genesis_detected(live):
    events = read_events(live)
    events[0]["event_type"] = "workspace_snapshot_attested"
    events[0]["entry_hash"] = compute_entry_hash(events[0])
    rewrite(live, events)
    assert "missing-genesis" in codes(verify(live))


def test_unsupported_schema_version_detected(live):
    events = read_events(live)
    events[1]["schema_version"] = "conclave-ledger/9.9.9"
    events[1]["entry_hash"] = compute_entry_hash(events[1])
    rewrite(live, events)
    assert "unsupported-schema-version" in codes(verify(live))


def test_invalid_authority_level_detected(live):
    events = read_events(live)
    events[1]["authority_level"] = "constitutional_authority"
    events[1]["entry_hash"] = compute_entry_hash(events[1])
    rewrite(live, events)
    assert "invalid-authority-level" in codes(verify(live))


def test_empty_ledger_reported(ws):
    assert "empty-ledger" in codes(verify(ws))


# -- advisory authority boundary -------------------------------------------

def test_advisory_agent_cannot_claim_council_review(live):
    with pytest.raises(LedgerError, match="advisory agent cannot"):
        append_event(live, event_type="council_review_created",
                     actor="claude", authority_level="advisory_agent")


@pytest.mark.parametrize("event_type", [
    "task_packet_created", "scope_review_created", "council_review_created",
    "workspace_snapshot_attested", "human_decision_recorded", "action_authorised",
])
def test_advisory_agent_blocked_for_authority_bearing_events(live, event_type):
    with pytest.raises(LedgerError, match="advisory agent cannot"):
        append_event(live, event_type=event_type, actor="gemini",
                     authority_level="advisory_agent")


@pytest.mark.parametrize("event_type", [
    "provider_response_preserved", "handoff_packet_imported", "provider_response_rejected",
])
def test_advisory_agent_permitted_for_submission_events(live, event_type):
    event, created = append_event(live, event_type=event_type, actor="claude",
                                  authority_level="advisory_agent",
                                  artifact_hashes={"x": event_type})
    assert created and event["authority_level"] == "advisory_agent"


def test_forbidden_advisory_authority_detected_on_read(live):
    """Even if written by another tool, verification catches it."""
    events = read_events(live)
    events[1]["authority_level"] = "advisory_agent"
    events[1]["actor"] = "claude"
    events[1]["entry_hash"] = compute_entry_hash(events[1])
    rewrite(live, events)
    assert "forbidden-advisory-authority" in codes(verify(live))


def test_invalid_authority_rejected_at_append(live):
    with pytest.raises(LedgerError, match="invalid authority_level"):
        append_event(live, event_type="task_packet_created", authority_level="principal")


def test_unknown_event_type_rejected_at_append(live):
    with pytest.raises(LedgerError, match="unknown event_type"):
        append_event(live, event_type="everything_approved")


# -- idempotency -----------------------------------------------------------

def _eid(event_type="task_packet_created", actor="conclave", authority="system",
         subjects=("TP-x@v1",), hashes=None, payload=None):
    return derive_event_id(event_type, actor, authority, list(subjects),
                           hashes or {}, payload or {})


def test_event_id_is_deterministic():
    assert _eid(hashes={"h": "sha256:aa"}) == _eid(hashes={"h": "sha256:aa"})


def test_event_id_ignores_subject_ordering():
    assert _eid(subjects=("a", "b")) == _eid(subjects=("b", "a"))


def test_event_id_ignores_payload_key_ordering():
    assert _eid(payload={"a": 1, "b": 2}) == _eid(payload={"b": 2, "a": 1})


def test_event_id_ignores_nested_payload_key_ordering():
    assert _eid(payload={"outer": {"x": 1, "y": 2}}) == \
           _eid(payload={"outer": {"y": 2, "x": 1}})


def test_event_id_changes_with_payload():
    assert _eid(payload={"reason": "one"}) != _eid(payload={"reason": "two"})


def test_event_id_changes_with_actor():
    assert _eid(actor="conclave") != _eid(actor="claude")


def test_event_id_changes_with_authority_level():
    assert _eid(authority="system") != _eid(authority="human_principal")


def test_event_id_changes_with_event_type():
    assert _eid(event_type="task_packet_created") != _eid(event_type="task_packet_revised")


def test_duplicate_append_is_idempotent(live):
    kwargs = dict(event_type="task_packet_created", subject_refs=["TP-x@v1"],
                  artifact_hashes={"task_packet": "sha256:" + "a" * 64})
    first, c1 = append_event(live, **kwargs)
    second, c2 = append_event(live, **kwargs)
    assert c1 is True and c2 is False
    assert first["entry_hash"] == second["entry_hash"]
    assert len(read_events(live)) == 3


def test_materially_different_event_appends(live):
    append_event(live, event_type="task_packet_created", subject_refs=["TP-x@v1"],
                 artifact_hashes={"task_packet": "sha256:" + "a" * 64})
    _, created = append_event(live, event_type="task_packet_revised",
                              subject_refs=["TP-x@v2"],
                              artifact_hashes={"task_packet": "sha256:" + "b" * 64})
    assert created is True
    assert len(read_events(live)) == 4


def test_different_refusal_reasons_append_separately(live):
    """Payload-carried substance must not collapse into one event."""
    a, ca = append_event(live, event_type="operation_refused", subject_refs=["TP-x@v1"],
                         payload={"reason": "packet failed validation"})
    b, cb = append_event(live, event_type="operation_refused", subject_refs=["TP-x@v1"],
                         payload={"reason": "egress policy forbade this provider"})
    assert ca and cb
    assert a["event_id"] != b["event_id"]
    assert len(read_events(live)) == 4


def test_identical_refusals_remain_idempotent(live):
    kwargs = dict(event_type="operation_refused", subject_refs=["TP-x@v1"],
                  payload={"reason": "packet failed validation"})
    append_event(live, **kwargs)
    _, created = append_event(live, **kwargs)
    assert created is False
    assert len(read_events(live)) == 3


def test_different_integrity_defects_append_separately(live):
    a, _ = append_event(live, event_type="integrity_failure_detected",
                        subject_refs=["TP-x@v1"],
                        payload={"defect": "entry-hash-mismatch", "line": 4})
    b, _ = append_event(live, event_type="integrity_failure_detected",
                        subject_refs=["TP-x@v1"],
                        payload={"defect": "broken-chain", "line": 4})
    assert a["event_id"] != b["event_id"]
    assert len(read_events(live)) == 4


def test_timestamps_do_not_affect_event_id(live):
    a, _ = append_event(live, event_type="operation_refused", subject_refs=["TP-x@v1"],
                        payload={"reason": "r"}, occurred_at="2020-01-01T00:00:00Z")
    b, created = append_event(live, event_type="operation_refused", subject_refs=["TP-x@v1"],
                              payload={"reason": "r"}, occurred_at="2030-01-01T00:00:00Z")
    assert created is False
    assert a["event_id"] == b["event_id"]


def test_same_subject_different_artifact_appends(live):
    append_event(live, event_type="relay_prompt_exported", subject_refs=["TP-x@v1"],
                 artifact_hashes={"prompt": "sha256:" + "a" * 64})
    _, created = append_event(live, event_type="relay_prompt_exported",
                              subject_refs=["TP-x@v1"],
                              artifact_hashes={"prompt": "sha256:" + "b" * 64})
    assert created is True


# -- append-only behaviour -------------------------------------------------

def test_append_refused_on_damaged_chain(live):
    events = read_events(live)
    events[1]["payload"]["artifact_count"] = 999
    rewrite(live, events)
    with pytest.raises(LedgerError, match="does not verify"):
        append_event(live, event_type="task_packet_created", subject_refs=["TP-x@v1"])


def test_damaged_chain_is_not_repaired_by_failed_append(live):
    events = read_events(live)
    events[1]["payload"]["artifact_count"] = 999
    rewrite(live, events)
    before = live.ledger_path.read_bytes()
    with pytest.raises(LedgerError):
        append_event(live, event_type="task_packet_created", subject_refs=["TP-x@v1"])
    assert live.ledger_path.read_bytes() == before


def test_verification_performs_no_repair(live):
    events = read_events(live)
    events[1]["sequence"] = 99
    rewrite(live, events)
    before = live.ledger_path.read_bytes()
    verify(live)
    verify(live)
    assert live.ledger_path.read_bytes() == before


def test_existing_lines_never_rewritten(live):
    first_line = live.ledger_path.read_text(encoding="utf-8").splitlines()[0]
    for i in range(3):
        append_event(live, event_type="task_packet_created", subject_refs=[f"TP-{i}@v1"])
    assert live.ledger_path.read_text(encoding="utf-8").splitlines()[0] == first_line


def test_ledger_only_grows(live):
    size = live.ledger_path.stat().st_size
    append_event(live, event_type="task_packet_created", subject_refs=["TP-x@v1"])
    assert live.ledger_path.stat().st_size > size


# -- locking and durability ------------------------------------------------

def test_concurrent_append_blocked_by_lock(live):
    with exclusive_lock(live.ledger_path, timeout=5):
        with pytest.raises(LedgerError, match="could not acquire ledger lock"):
            append_event(live, event_type="task_packet_created", subject_refs=["TP-x@v1"])


def test_lock_released_after_append(live):
    append_event(live, event_type="task_packet_created", subject_refs=["TP-x@v1"])
    lock = live.ledger_path.with_name(live.ledger_path.name + ".lock")
    assert not lock.exists()


def test_lock_released_after_failure(live):
    with pytest.raises(LedgerError):
        append_event(live, event_type="not_a_real_event")
    lock = live.ledger_path.with_name(live.ledger_path.name + ".lock")
    assert not lock.exists()


def test_stale_lock_is_reclaimed(live):
    lock = live.ledger_path.with_name(live.ledger_path.name + ".lock")
    lock.write_text("99999", encoding="utf-8")
    old = time.time() - 3600
    os.utime(lock, (old, old))
    _, created = append_event(live, event_type="task_packet_created",
                              subject_refs=["TP-x@v1"])
    assert created is True


def test_fsync_path_exercised(live, monkeypatch):
    calls = []
    real = os.fsync
    monkeypatch.setattr(os, "fsync", lambda fd: (calls.append(fd), real(fd))[1])
    append_event(live, event_type="task_packet_created", subject_refs=["TP-x@v1"])
    assert calls, "fsync was not called before reporting success"


def test_entry_is_on_disk_immediately(live):
    append_event(live, event_type="task_packet_created", subject_refs=["TP-x@v1"])
    reread = [json.loads(l) for l in
              live.ledger_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(reread) == 3


# -- record_event ----------------------------------------------------------

def test_record_event_noop_without_ledger(ws):
    event, created = record_event(ws, event_type="task_packet_created",
                                  subject_refs=["TP-x@v1"])
    assert event is None and created is False
    assert not ws.ledger_path.exists()


def test_record_event_appends_when_ledger_exists(live):
    event, created = record_event(live, event_type="task_packet_created",
                                  subject_refs=["TP-x@v1"])
    assert created is True and event["sequence"] == 3


# -- payload discipline ----------------------------------------------------

def test_payload_references_artifacts_rather_than_copying(live):
    """The ledger records that an artifact existed, not what it said."""
    from conclave.taskpacket import build_packet
    p = build_packet(objective="a distinctive objective string", created_by="Arthur",
                     target_objects=[{"object_id": "RA-001"}],
                     assigned_providers=[{"provider": "claude", "role": "r"}])
    event, _ = append_event(live, event_type="task_packet_created",
                            subject_refs=[p.ref],
                            artifact_hashes={"task_packet": p.content_hash},
                            payload={"task_id": p.task_id, "version": p.version})
    assert p.content_hash in canonical_json(event)
    assert "a distinctive objective string" not in canonical_json(event)
