"""Council Review: aggregation, structural comparison, status, idempotency."""

import pytest
import yaml

from conclave.council import (
    COUNCIL_SCHEMA_VERSION,
    CouncilReview,
    DISCLAIMER,
    build_council_review,
    council_review_id,
    derive_status,
    detect_structural,
    read_council,
    render_markdown,
    review_task,
    verify_council_content_hash,
    write_council,
    yaml_path,
)
from conclave.errors import ValidationError
from conclave.handoff import HandoffPacket, seal_handoff, write_handoff
from conclave.scope import evaluate, review_handoff, write_review
from conclave.taskpacket import build_packet, packet_path, write_packet
from conclave.workspace import Workspace, utcnow


@pytest.fixture
def ws(tmp_path):
    return Workspace.create(tmp_path, principal="Arthur")


def task(providers=(("claude", "governance_critic"), ("gemini", "external_verifier")),
         targets=("RA-001",), read_only=("ADR-0002",), prohibited=("KOS-CONSTITUTION",)):
    def refs(items):
        out = []
        for i in items:
            oid, _, sec = i.partition("#")
            out.append({"object_id": oid, "section_id": sec or None})
        return out

    return build_packet(
        objective="Draft RA-001 Part I", created_by="Arthur",
        target_objects=refs(targets), read_only_objects=refs(read_only),
        prohibited_objects=refs(prohibited),
        assigned_providers=[{"provider": p, "role": r} for p, r in providers],
    )


def handoff(packet, provider, role, *, touches=(("RA-001", "proposed_change"),),
            status="submitted", action="revise", findings=(), unresolved=(),
            abstentions=(), summary="a summary", imported_at=None, raw_seed="1"):
    return seal_handoff(HandoffPacket.model_validate({
        "packet_ref": packet.ref,
        "packet_content_hash": packet.content_hash,
        "provider": provider, "role": role, "status": status,
        "objects_touched": [
            {"object_id": o.split("#")[0],
             "section_id": (o.split("#")[1] if "#" in o else None), "action": a}
            for o, a in touches
        ],
        "output": {"type": "critique", "summary": summary, "body": "b"},
        "findings": list(findings), "assumptions": [],
        "abstentions": list(abstentions), "unresolved": list(unresolved),
        "evidence_used": [],
        "recommended_next_action": action,
        "raw_response_hash": "sha256:" + raw_seed * 64,
        "prompt_hash": "sha256:" + "2" * 64,
        "imported_at": imported_at or utcnow(),
    }))


def store(ws, packet, handoffs, *, with_scope=True):
    write_packet(ws, packet)
    for h in handoffs:
        write_handoff(ws, h)
        if with_scope:
            write_review(ws, evaluate(packet, h))
    return packet


# -- assembly --------------------------------------------------------------

def test_required_fields_present(ws):
    p = task()
    hs = [handoff(p, "claude", "governance_critic"),
          handoff(p, "gemini", "external_verifier", raw_seed="3")]
    store(ws, p, hs)
    data = review_task(ws, p.task_id, 1).review.to_serialisable()
    for name in ("schema_version", "council_review_id", "task_packet_ref", "task_packet_hash",
                 "created_at", "providers_expected", "submissions", "missing_providers",
                 "provider_summaries", "consolidated_findings", "structural_agreements",
                 "structural_disagreements", "unresolved_items", "abstentions",
                 "scope_summary", "governance_alerts", "decision_block", "review_status",
                 "human_decision_required", "source_handoff_hashes",
                 "source_scope_review_hashes", "content_hash"):
        assert name in data, name


def test_submission_entry_fields(ws):
    p = task()
    hs = [handoff(p, "claude", "governance_critic"),
          handoff(p, "gemini", "external_verifier", raw_seed="3")]
    store(ws, p, hs)
    s = review_task(ws, p.task_id, 1).review.submissions[0].model_dump()
    for name in ("provider", "role", "submission_status", "recommended_next_action",
                 "handoff_packet_hash", "raw_response_hash", "scope_status",
                 "scope_violation_count", "summary", "findings", "assumptions",
                 "abstentions", "unresolved", "evidence_used"):
        assert name in s, name


def test_missing_providers_reported_not_ignored(ws):
    p = task()
    store(ws, p, [handoff(p, "claude", "governance_critic")])
    r = review_task(ws, p.task_id, 1).review
    assert r.missing_providers == ["gemini"]
    assert r.review_status == "incomplete"


def test_all_present_is_ready(ws):
    p = task()
    store(ws, p, [handoff(p, "claude", "governance_critic"),
                  handoff(p, "gemini", "external_verifier", raw_seed="3")])
    r = review_task(ws, p.task_id, 1).review
    assert r.missing_providers == []
    assert r.review_status == "ready_for_human_review"


def test_consolidated_findings_sorted_by_severity(ws):
    p = task()
    hs = [handoff(p, "claude", "governance_critic",
                  findings=[{"finding_id": "F-001", "severity": "low", "claim": "l"}]),
          handoff(p, "gemini", "external_verifier", raw_seed="3",
                  findings=[{"finding_id": "F-001", "severity": "high", "claim": "h"}])]
    store(ws, p, hs)
    sev = [f["severity"] for f in review_task(ws, p.task_id, 1).review.consolidated_findings]
    assert sev == ["high", "low"]


def test_unresolved_and_abstentions_collected(ws):
    p = task()
    hs = [handoff(p, "claude", "governance_critic",
                  unresolved=["constitution absent"], abstentions=["cannot verify"]),
          handoff(p, "gemini", "external_verifier", raw_seed="3")]
    store(ws, p, hs)
    r = review_task(ws, p.task_id, 1).review
    assert len(r.unresolved_items) == 1
    assert len(r.abstentions) == 1


# -- decision block --------------------------------------------------------

def test_decision_block_is_empty_and_pending(ws):
    p = task()
    store(ws, p, [handoff(p, "claude", "governance_critic"),
                  handoff(p, "gemini", "external_verifier", raw_seed="3")])
    d = review_task(ws, p.task_id, 1).review.decision_block
    assert d.decision == "pending"
    assert d.decided_by is None and d.decided_at is None and d.rationale is None
    assert d.authorised_actions == []


@pytest.mark.parametrize("field,value", [
    ("decision", "approved"), ("decided_by", "claude"),
    ("decided_at", "2026-07-27T00:00:00Z"), ("rationale", "looks fine"),
    ("authorised_actions", ["merge"]),
])
def test_decision_block_cannot_be_populated(field, value):
    """Types forbid an AI-generated review expressing a decision."""
    from conclave.council import DecisionBlock
    with pytest.raises(Exception):
        DecisionBlock.model_validate({field: value})


def test_human_decision_always_required(ws):
    p = task()
    store(ws, p, [handoff(p, "claude", "governance_critic"),
                  handoff(p, "gemini", "external_verifier", raw_seed="3")])
    assert review_task(ws, p.task_id, 1).review.human_decision_required is True


# -- structural agreement --------------------------------------------------

def _pair(p, **kw):
    a = handoff(p, "claude", "governance_critic", **kw.get("a", {}))
    b = handoff(p, "gemini", "external_verifier", raw_seed="3", **kw.get("b", {}))
    return {"claude": a, "gemini": b}


def test_identical_next_action_is_agreement():
    p = task()
    subs = _pair(p, a={"action": "revise"}, b={"action": "revise"})
    agree, _ = detect_structural(subs, {})
    assert any(a["kind"] == "recommended_next_action" and a["value"] == "revise" for a in agree)


def test_conflicting_next_action_is_disagreement():
    p = task()
    subs = _pair(p, a={"action": "accept"}, b={"action": "revise"})
    _, dis = detect_structural(subs, {})
    assert any(d["kind"] == "recommended_next_action" for d in dis)


def test_accept_versus_dissent_called_out():
    p = task()
    subs = _pair(p, a={"action": "accept"}, b={"action": "escalate"})
    _, dis = detect_structural(subs, {})
    entry = next(d for d in dis if d["kind"] == "accept_versus_dissent")
    assert entry["accepting"] == ["claude"]
    assert entry["dissenting"] == {"gemini": "escalate"}


def test_identical_status_is_agreement():
    p = task()
    subs = _pair(p, a={"status": "submitted"}, b={"status": "submitted"})
    agree, _ = detect_structural(subs, {})
    assert any(a["kind"] == "submission_status" for a in agree)


def test_conflicting_status_is_disagreement():
    p = task()
    subs = _pair(p, a={"status": "submitted"}, b={"status": "abstained"})
    _, dis = detect_structural(subs, {})
    assert any(d["kind"] == "submission_status" for d in dis)


def test_shared_finding_key_identical_values_agree():
    p = task()
    f = [{"key": "EVIDENCE-STATES", "finding_id": "F-001", "severity": "high",
          "dimension": "epistemic-integrity", "claim": "wording differs entirely"}]
    g = [{"key": "EVIDENCE-STATES", "finding_id": "F-007", "severity": "high",
          "dimension": "epistemic-integrity", "claim": "quite different prose"}]
    subs = _pair(p, a={"findings": f}, b={"findings": g})
    agree, _ = detect_structural(subs, {})
    assert any(a["kind"] == "finding" and a["finding_key"] == "EVIDENCE-STATES" for a in agree)


def test_shared_finding_key_differing_values_disagree():
    p = task()
    f = [{"key": "K", "severity": "high", "dimension": "d"}]
    g = [{"key": "K", "severity": "low", "dimension": "d"}]
    subs = _pair(p, a={"findings": f}, b={"findings": g})
    _, dis = detect_structural(subs, {})
    assert any(d["kind"] == "finding" and d["finding_key"] == "K" for d in dis)


def test_finding_id_alone_is_never_treated_as_shared():
    """F-001 from two providers is a numbering coincidence, not agreement."""
    p = task()
    f = [{"finding_id": "F-001", "severity": "high", "claim": "one thing"}]
    g = [{"finding_id": "F-001", "severity": "low", "claim": "an unrelated thing"}]
    subs = _pair(p, a={"findings": f}, b={"findings": g})
    agree, dis = detect_structural(subs, {})
    assert not any(x["kind"] == "finding" for x in agree + dis)


def test_prose_similarity_never_creates_agreement():
    p = task()
    f = [{"finding_id": "F-001", "severity": "high", "claim": "The draft is unclear."}]
    g = [{"finding_id": "F-002", "severity": "high", "claim": "The draft is unclear."}]
    subs = _pair(p, a={"findings": f}, b={"findings": g})
    agree, _ = detect_structural(subs, {})
    assert not any(a["kind"] == "finding" for a in agree)


def test_shared_unresolved_identifier_is_agreement():
    p = task()
    subs = _pair(p,
                 a={"unresolved": [{"id": "U-CONSTITUTION", "note": "absent"}]},
                 b={"unresolved": [{"id": "U-CONSTITUTION", "note": "phrased differently"}]})
    agree, _ = detect_structural(subs, {})
    entry = next(a for a in agree if a["kind"] == "unresolved_item")
    assert entry["identifier"] == "U-CONSTITUTION"
    assert entry["providers"] == ["claude", "gemini"]


def test_scope_classification_agreement_and_disagreement():
    p = task()
    a = handoff(p, "claude", "governance_critic", touches=(("ADR-0002", "read"),))
    b = handoff(p, "gemini", "external_verifier", raw_seed="3",
                touches=(("ADR-0002", "proposed_change"),))
    scopes = {a.content_hash: evaluate(p, a), b.content_hash: evaluate(p, b)}
    _, dis = detect_structural({"claude": a, "gemini": b}, scopes)
    entry = next(d for d in dis if d["kind"] == "scope_classification")
    assert entry["object"] == "ADR-0002"
    assert sorted(entry["distinct_values"]) == ["in_read_only", "read_only_modified"]


def test_single_provider_produces_no_structural_comparison():
    p = task()
    agree, dis = detect_structural({"claude": handoff(p, "claude", "governance_critic")}, {})
    assert agree == [] and dis == []


# -- governance and status -------------------------------------------------

def test_scope_violation_creates_governance_alert(ws):
    p = task()
    hs = [handoff(p, "claude", "governance_critic",
                  touches=(("KOS-CONSTITUTION", "read"),)),
          handoff(p, "gemini", "external_verifier", raw_seed="3")]
    store(ws, p, hs)
    r = review_task(ws, p.task_id, 1).review
    assert any(a["kind"] == "scope_violation" for a in r.governance_alerts)
    assert r.review_status == "blocked_by_governance"
    assert r.human_decision_required is True


def test_missing_scope_review_is_flagged_not_assumed_clean(ws):
    p = task()
    hs = [handoff(p, "claude", "governance_critic"),
          handoff(p, "gemini", "external_verifier", raw_seed="3")]
    store(ws, p, hs, with_scope=False)
    r = review_task(ws, p.task_id, 1).review
    assert any(a["kind"] == "scope_not_evaluated" for a in r.governance_alerts)
    assert r.review_status == "blocked_by_governance"


@pytest.mark.parametrize("missing,ambiguous,alerts,expected", [
    ([], [], [], "ready_for_human_review"),
    (["gemini"], [], [], "incomplete"),
    ([], [], [{"kind": "scope_violation"}], "blocked_by_governance"),
    (["gemini"], [], [{"kind": "scope_violation"}], "blocked_by_governance"),
    ([], ["claude"], [], "ambiguous_submissions"),
    (["gemini"], ["claude"], [{"kind": "x"}], "ambiguous_submissions"),
])
def test_status_precedence(missing, ambiguous, alerts, expected):
    assert derive_status(missing=missing, ambiguous=ambiguous,
                         governance_alerts=alerts) == expected


# -- multiple submissions from one provider --------------------------------

def test_latest_submission_selected_and_earlier_retained(ws):
    p = task()
    early = handoff(p, "claude", "governance_critic", raw_seed="4",
                    imported_at="2026-07-27T10:00:00Z", summary="first")
    late = handoff(p, "claude", "governance_critic", raw_seed="5",
                   imported_at="2026-07-27T11:00:00Z", summary="second")
    store(ws, p, [early, late, handoff(p, "gemini", "external_verifier", raw_seed="3")])
    r = review_task(ws, p.task_id, 1).review
    claude = next(s for s in r.submissions if s.provider == "claude")
    assert claude.summary == "second"
    assert any(s["handoff_packet_hash"] == early.content_hash
               for s in r.superseded_submissions)
    assert early.content_hash in r.source_handoff_hashes


def test_tied_import_time_is_ambiguous(ws):
    p = task()
    same = "2026-07-27T10:00:00Z"
    a = handoff(p, "claude", "governance_critic", raw_seed="4", imported_at=same, summary="x")
    b = handoff(p, "claude", "governance_critic", raw_seed="5", imported_at=same, summary="y")
    store(ws, p, [a, b, handoff(p, "gemini", "external_verifier", raw_seed="3")])
    r = review_task(ws, p.task_id, 1).review
    assert r.review_status == "ambiguous_submissions"
    assert any(x["kind"] == "provider_submission_ambiguous" for x in r.governance_alerts)
    assert "claude" not in {s.provider for s in r.submissions}


def test_ambiguity_is_never_silently_resolved(ws):
    p = task()
    same = "2026-07-27T10:00:00Z"
    store(ws, p, [handoff(p, "claude", "governance_critic", raw_seed="4",
                          imported_at=same, summary="x"),
                  handoff(p, "claude", "governance_critic", raw_seed="5",
                          imported_at=same, summary="y")])
    r = review_task(ws, p.task_id, 1).review
    assert all(s.provider != "claude" for s in r.submissions)


# -- sealing, immutability, idempotency ------------------------------------

def test_review_is_sealed_and_frozen(ws):
    p = task()
    store(ws, p, [handoff(p, "claude", "governance_critic"),
                  handoff(p, "gemini", "external_verifier", raw_seed="3")])
    r = review_task(ws, p.task_id, 1).review
    assert verify_council_content_hash(r)
    with pytest.raises(Exception):
        r.review_status = "ready_for_human_review"


def test_idempotent_for_unchanged_sources(ws):
    p = task()
    store(ws, p, [handoff(p, "claude", "governance_critic"),
                  handoff(p, "gemini", "external_verifier", raw_seed="3")])
    first = review_task(ws, p.task_id, 1)
    second = review_task(ws, p.task_id, 1)
    assert first.created is True and second.created is False
    assert first.review.created_at == second.review.created_at
    assert first.review.content_hash == second.review.content_hash
    assert len(list(ws.council_dir.glob("*.yaml"))) == 1


def test_changed_source_set_creates_new_review(ws):
    p = task()
    store(ws, p, [handoff(p, "claude", "governance_critic")])
    first = review_task(ws, p.task_id, 1)
    h = handoff(p, "gemini", "external_verifier", raw_seed="3")
    write_handoff(ws, h)
    write_review(ws, evaluate(p, h))
    second = review_task(ws, p.task_id, 1)
    assert second.created is True
    assert second.review.council_review_id != first.review.council_review_id
    assert first.yaml_path.exists() and second.yaml_path.exists()


def test_review_id_deterministic_from_sources(ws):
    p = task()
    assert council_review_id(p, ["a", "b"], ["c"]) == council_review_id(p, ["b", "a"], ["c"])
    assert council_review_id(p, ["a"], ["c"]) != council_review_id(p, ["a", "b"], ["c"])


def test_write_refuses_overwrite(ws):
    p = task()
    store(ws, p, [handoff(p, "claude", "governance_critic")])
    r = review_task(ws, p.task_id, 1).review
    with pytest.raises(ValidationError, match="immutable"):
        write_council(ws, r)


def test_write_refuses_stale_hash(ws):
    p = task()
    store(ws, p, [handoff(p, "claude", "governance_critic")])
    r = review_task(ws, p.task_id, 1).review
    with pytest.raises(ValidationError, match="stale"):
        write_council(ws, r.model_copy(update={"review_status": "ready_for_human_review"}))


def test_altered_existing_review_refused(ws):
    p = task()
    store(ws, p, [handoff(p, "claude", "governance_critic")])
    outcome = review_task(ws, p.task_id, 1)
    data = yaml.safe_load(outcome.yaml_path.read_text(encoding="utf-8"))
    data["review_status"] = "ready_for_human_review"
    outcome.yaml_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValidationError, match="content_hash"):
        review_task(ws, p.task_id, 1)


def test_altered_handoff_refused(ws):
    p = task()
    h = handoff(p, "claude", "governance_critic")
    store(ws, p, [h])
    path = next(ws.inbox_dir.glob("*.yaml"))
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["status"] = "blocked"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValidationError, match="altered"):
        review_task(ws, p.task_id, 1)


def test_altered_task_packet_refused(ws):
    p = task()
    store(ws, p, [handoff(p, "claude", "governance_critic")])
    tpath = packet_path(ws, p.task_id, 1)
    data = yaml.safe_load(tpath.read_text(encoding="utf-8"))
    data["objective"] = "changed"
    tpath.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValidationError, match="altered"):
        review_task(ws, p.task_id, 1)


def test_missing_task_packet_refused(ws):
    with pytest.raises(ValidationError, match="no Task Packet"):
        review_task(ws, "TP-nothing-0123456789", 1)


def test_round_trips(ws):
    p = task()
    store(ws, p, [handoff(p, "claude", "governance_critic")])
    outcome = review_task(ws, p.task_id, 1)
    loaded = read_council(outcome.yaml_path)
    assert loaded.content_hash == outcome.review.content_hash
    assert verify_council_content_hash(loaded)


# -- markdown projection ---------------------------------------------------

def test_markdown_written_alongside_yaml(ws):
    p = task()
    store(ws, p, [handoff(p, "claude", "governance_critic")])
    outcome = review_task(ws, p.task_id, 1)
    assert outcome.markdown_path.exists()
    assert outcome.markdown_path.suffix == ".md"


def test_markdown_carries_reference_and_full_hash(ws):
    p = task()
    store(ws, p, [handoff(p, "claude", "governance_critic")])
    outcome = review_task(ws, p.task_id, 1)
    text = outcome.markdown_path.read_text(encoding="utf-8")
    assert outcome.review.council_review_id in text
    assert outcome.review.content_hash in text
    assert outcome.review.task_packet_ref in text


def test_markdown_states_no_approval(ws):
    p = task()
    store(ws, p, [handoff(p, "claude", "governance_critic")])
    text = review_task(ws, p.task_id, 1).markdown_path.read_text(encoding="utf-8")
    assert DISCLAIMER in text
    assert "has not approved, ratified, commissioned or merged anything" in text


def test_markdown_has_required_sections(ws):
    p = task()
    hs = [handoff(p, "claude", "governance_critic",
                  touches=(("KOS-CONSTITUTION", "read"),),
                  findings=[{"finding_id": "F-001", "severity": "high", "claim": "c"}],
                  unresolved=["u"], abstentions=["a"]),
          handoff(p, "gemini", "external_verifier", raw_seed="3")]
    store(ws, p, hs)
    text = review_task(ws, p.task_id, 1).markdown_path.read_text(encoding="utf-8")
    for section in ("## Identity", "## Participation", "## Executive summaries",
                    "## Structural agreements", "## Structural disagreements",
                    "## Findings by severity", "## Unresolved items", "## Abstentions",
                    "## Scope and governance alerts", "## Source provenance",
                    "## Human decision"):
        assert section in text, section


def test_markdown_decision_section_is_empty(ws):
    p = task()
    store(ws, p, [handoff(p, "claude", "governance_critic")])
    text = review_task(ws, p.task_id, 1).markdown_path.read_text(encoding="utf-8")
    assert "decision: pending" in text
    assert "decided_by: null" in text
    assert "authorised_actions: []" in text


def test_markdown_shows_missing_provider(ws):
    p = task()
    store(ws, p, [handoff(p, "claude", "governance_critic")])
    text = review_task(ws, p.task_id, 1).markdown_path.read_text(encoding="utf-8")
    assert "**NO**" in text
    assert "Missing submissions:" in text


def test_markdown_banner_reflects_status(ws):
    p = task()
    store(ws, p, [handoff(p, "claude", "governance_critic",
                          touches=(("KOS-CONSTITUTION", "read"),)),
                  handoff(p, "gemini", "external_verifier", raw_seed="3")])
    text = review_task(ws, p.task_id, 1).markdown_path.read_text(encoding="utf-8")
    assert "BLOCKED BY GOVERNANCE" in text


def test_markdown_is_lf(ws):
    p = task()
    store(ws, p, [handoff(p, "claude", "governance_critic")])
    assert b"\r\n" not in review_task(ws, p.task_id, 1).markdown_path.read_bytes()
