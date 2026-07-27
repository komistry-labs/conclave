"""Scope drift detection: containment, action rules, precedence, sealing."""

import pytest
import yaml

from conclave.errors import ValidationError
from conclave.handoff import HandoffPacket, seal_handoff
from conclave.scope import (
    ScopeReview,
    evaluate,
    grant_covers,
    review_handoff,
    scope_dir,
    verify_review_content_hash,
    write_review,
)
from conclave.taskpacket import build_packet, packet_path, write_packet
from conclave.workspace import Workspace, utcnow


@pytest.fixture
def ws(tmp_path):
    return Workspace.create(tmp_path, principal="Arthur")


def task(targets=(), read_only=(), prohibited=()):
    def refs(items):
        out = []
        for i in items:
            oid, _, sec = i.partition("#")
            out.append({"object_id": oid, "section_id": sec or None})
        return out

    return build_packet(
        objective="Draft RA-001 Part I",
        created_by="Arthur",
        target_objects=refs(targets),
        read_only_objects=refs(read_only),
        prohibited_objects=refs(prohibited),
        assigned_providers=[{"provider": "claude", "role": "governance_critic"}],
    )


def handoff(packet, touches, provider="claude", role="governance_critic"):
    return seal_handoff(HandoffPacket.model_validate({
        "packet_ref": packet.ref,
        "packet_content_hash": packet.content_hash,
        "provider": provider,
        "role": role,
        "status": "submitted",
        "objects_touched": [
            {"object_id": o.split("#")[0],
             "section_id": (o.split("#")[1] if "#" in o else None),
             "action": a}
            for o, a in touches
        ],
        "output": {}, "findings": [], "assumptions": [], "abstentions": [],
        "unresolved": [], "evidence_used": [],
        "recommended_next_action": "revise",
        "raw_response_hash": "sha256:" + "1" * 64,
        "prompt_hash": "sha256:" + "2" * 64,
        "imported_at": utcnow(),
    }))


def result_for(review, key):
    return next(r for r in review.object_results if r.key == key)


# -- containment -----------------------------------------------------------

def test_whole_object_target_covers_touched_section():
    p = task(targets=["RA-001"])
    r = evaluate(p, handoff(p, [("RA-001#RA-001-PART-IV", "proposed_change")]))
    assert result_for(r, "RA-001#RA-001-PART-IV").classification == "in_target"
    assert r.scope_status == "within_scope"


def test_whole_object_target_covers_whole_object():
    p = task(targets=["RA-001"])
    r = evaluate(p, handoff(p, [("RA-001", "proposed_change")]))
    assert result_for(r, "RA-001").classification == "in_target"


def test_section_target_does_not_cover_whole_object():
    """Permission to edit a section is not permission to edit the object."""
    p = task(targets=["RA-001#RA-001-PART-IV"])
    r = evaluate(p, handoff(p, [("RA-001", "proposed_change")]))
    assert result_for(r, "RA-001").classification == "undeclared_expansion"
    assert r.scope_status == "expansion_detected"


def test_section_target_does_not_cover_sibling_section():
    p = task(targets=["RA-001#RA-001-PART-IV"])
    r = evaluate(p, handoff(p, [("RA-001#RA-001-PART-I", "proposed_change")]))
    assert result_for(r, "RA-001#RA-001-PART-I").classification == "undeclared_expansion"


def test_section_target_covers_itself():
    p = task(targets=["RA-001#RA-001-PART-IV"])
    r = evaluate(p, handoff(p, [("RA-001#RA-001-PART-IV", "proposed_change")]))
    assert result_for(r, "RA-001#RA-001-PART-IV").classification == "in_target"


def test_whole_object_prohibition_covers_sections():
    p = task(targets=["RA-001"], prohibited=["KOS-CONSTITUTION"])
    r = evaluate(p, handoff(p, [("KOS-CONSTITUTION#ARTICLE-III", "read")]))
    assert result_for(r, "KOS-CONSTITUTION#ARTICLE-III").classification == "prohibited_touched"


def test_section_prohibition_covers_only_that_section():
    p = task(targets=["RA-001"], prohibited=["KOS-CONSTITUTION#ARTICLE-III"])
    r = evaluate(p, handoff(p, [("KOS-CONSTITUTION#ARTICLE-IV", "read")]))
    assert result_for(r, "KOS-CONSTITUTION#ARTICLE-IV").classification == "undeclared_expansion"


def test_grant_covers_unit():
    from conclave.handoff import ObjectTouched
    from conclave.models import ObjectRef
    whole = ObjectRef(object_id="RA-001")
    section = ObjectRef(object_id="RA-001", section_id="P4")
    assert grant_covers(whole, ObjectTouched(object_id="RA-001"))
    assert grant_covers(whole, ObjectTouched(object_id="RA-001", section_id="P4"))
    assert grant_covers(section, ObjectTouched(object_id="RA-001", section_id="P4"))
    assert not grant_covers(section, ObjectTouched(object_id="RA-001"))
    assert not grant_covers(section, ObjectTouched(object_id="RA-001", section_id="P1"))
    assert not grant_covers(whole, ObjectTouched(object_id="RA-002"))


# -- action rules ----------------------------------------------------------

@pytest.mark.parametrize("action", ["read", "cited", "proposed_change"])
def test_target_permits_every_action(action):
    p = task(targets=["RA-001"])
    r = evaluate(p, handoff(p, [("RA-001", action)]))
    assert result_for(r, "RA-001").allowed


def test_read_only_read_allowed():
    p = task(targets=["RA-001"], read_only=["ADR-0002"])
    r = evaluate(p, handoff(p, [("ADR-0002", "read")]))
    assert result_for(r, "ADR-0002").classification == "in_read_only"
    assert r.scope_status == "within_scope"


def test_read_only_citation_allowed():
    p = task(targets=["RA-001"], read_only=["ADR-0002"])
    r = evaluate(p, handoff(p, [("ADR-0002", "cited")]))
    assert result_for(r, "ADR-0002").classification == "in_read_only"


def test_read_only_proposed_change_is_violation():
    p = task(targets=["RA-001"], read_only=["ADR-0002"])
    r = evaluate(p, handoff(p, [("ADR-0002", "proposed_change")]))
    res = result_for(r, "ADR-0002")
    assert res.classification == "read_only_modified"
    assert not res.allowed
    assert r.scope_status == "expansion_detected"


@pytest.mark.parametrize("action", ["read", "cited", "proposed_change"])
def test_prohibited_any_action_is_violation(action):
    p = task(targets=["RA-001"], prohibited=["KOS-CONSTITUTION"])
    r = evaluate(p, handoff(p, [("KOS-CONSTITUTION", action)]))
    res = result_for(r, "KOS-CONSTITUTION")
    assert res.classification == "prohibited_touched"
    assert not res.allowed


@pytest.mark.parametrize("action", ["read", "cited", "proposed_change"])
def test_undeclared_any_action_is_expansion(action):
    p = task(targets=["RA-001"])
    r = evaluate(p, handoff(p, [("RA-009", action)]))
    res = result_for(r, "RA-009")
    assert res.classification == "undeclared_expansion"
    assert not res.allowed
    assert res.matched_grant is None


# -- precedence ------------------------------------------------------------

def test_prohibited_beats_read_only():
    """Malformed overlap must resolve toward restriction, never permission."""
    p = task(targets=["RA-001"], read_only=["X"], prohibited=["X"])
    r = evaluate(p, handoff(p, [("X", "read")]))
    assert result_for(r, "X").classification == "prohibited_touched"


def test_prohibited_beats_target():
    p = task(targets=["X"], prohibited=["X"])
    r = evaluate(p, handoff(p, [("X", "proposed_change")]))
    assert result_for(r, "X").classification == "prohibited_touched"


def test_read_only_beats_target():
    p = task(targets=["X"], read_only=["X"])
    r = evaluate(p, handoff(p, [("X", "proposed_change")]))
    assert result_for(r, "X").classification == "read_only_modified"


def test_whole_object_prohibition_beats_section_target():
    p = task(targets=["RA-001#P4"], prohibited=["RA-001"])
    r = evaluate(p, handoff(p, [("RA-001#P4", "proposed_change")]))
    assert result_for(r, "RA-001#P4").classification == "prohibited_touched"


# -- aggregate -------------------------------------------------------------

def test_empty_objects_touched_is_within_scope():
    p = task(targets=["RA-001"])
    r = evaluate(p, handoff(p, []))
    assert r.object_results == []
    assert r.scope_status == "within_scope"
    assert r.human_review_required is False
    assert r.declared_touch_count == 0


def test_mixed_allowed_and_violating():
    p = task(targets=["RA-001"], read_only=["ADR-0002"], prohibited=["KOS-CONSTITUTION"])
    r = evaluate(p, handoff(p, [
        ("RA-001#RA-001-PART-I", "proposed_change"),
        ("ADR-0002", "cited"),
        ("ADR-0005", "read"),
        ("KOS-CONSTITUTION", "read"),
    ]))
    assert result_for(r, "RA-001#RA-001-PART-I").classification == "in_target"
    assert result_for(r, "ADR-0002").classification == "in_read_only"
    assert result_for(r, "ADR-0005").classification == "undeclared_expansion"
    assert result_for(r, "KOS-CONSTITUTION").classification == "prohibited_touched"
    assert r.scope_status == "expansion_detected"
    assert r.human_review_required is True
    assert r.violation_count == 2


def test_violations_sort_first():
    p = task(targets=["RA-001"])
    r = evaluate(p, handoff(p, [("RA-001", "read"), ("RA-009", "read")]))
    assert r.object_results[0].key == "RA-009"


def test_within_scope_sets_human_review_false():
    p = task(targets=["RA-001"])
    r = evaluate(p, handoff(p, [("RA-001", "proposed_change")]))
    assert r.scope_status == "within_scope"
    assert r.human_review_required is False
    assert r.violation_count == 0


# -- duplicates ------------------------------------------------------------

def test_duplicate_touches_collapse_to_one_result():
    p = task(targets=["RA-001"])
    r = evaluate(p, handoff(p, [("RA-001", "read"), ("RA-001", "read")]))
    assert len(r.object_results) == 1
    assert r.declared_touch_count == 2


def test_most_severe_duplicate_action_governs():
    """A later 'read' must not excuse an earlier 'proposed_change'."""
    p = task(targets=["RA-001"], read_only=["ADR-0002"])
    r = evaluate(p, handoff(p, [
        ("ADR-0002", "proposed_change"),
        ("ADR-0002", "read"),
    ]))
    res = result_for(r, "ADR-0002")
    assert res.action == "proposed_change"
    assert res.classification == "read_only_modified"
    assert sorted(res.actions) == ["proposed_change", "read"]


def test_duplicate_ordering_does_not_matter():
    p = task(targets=["RA-001"], read_only=["ADR-0002"])
    a = evaluate(p, handoff(p, [("ADR-0002", "read"), ("ADR-0002", "proposed_change")]))
    b = evaluate(p, handoff(p, [("ADR-0002", "proposed_change"), ("ADR-0002", "read")]))
    assert a.scope_status == b.scope_status == "expansion_detected"


# -- prose is not parsed ---------------------------------------------------

def test_prose_is_not_mined_for_undeclared_objects():
    """Bootstrap 0.1 evaluates declarations only and must not pretend otherwise."""
    p = task(targets=["RA-001"])
    h = handoff(p, [("RA-001", "proposed_change")])
    h = seal_handoff(h.model_copy(update={
        "output": {"type": "critique",
                   "body": "I also rewrote ADR-0002 and consulted KOS-CONSTITUTION."}
    }))
    r = evaluate(p, h)
    assert r.scope_status == "within_scope"
    assert {x.key for x in r.object_results} == {"RA-001"}
    assert "prose" in r.evaluation_basis


# -- sealing and immutability ----------------------------------------------

def test_review_is_sealed():
    p = task(targets=["RA-001"])
    r = evaluate(p, handoff(p, [("RA-001", "read")]))
    assert r.content_hash.startswith("sha256:")
    assert verify_review_content_hash(r)


def test_review_is_frozen():
    p = task(targets=["RA-001"])
    r = evaluate(p, handoff(p, [("RA-001", "read")]))
    with pytest.raises(Exception):
        r.scope_status = "within_scope"


def test_tampered_review_fails_verification():
    p = task(targets=["RA-001"])
    r = evaluate(p, handoff(p, [("RA-009", "read")]))
    tampered = r.model_copy(update={"scope_status": "within_scope",
                                    "human_review_required": False})
    assert not verify_review_content_hash(tampered)


def test_write_refuses_stale_hash(ws):
    p = task(targets=["RA-001"])
    r = evaluate(p, handoff(p, [("RA-009", "read")]))
    tampered = r.model_copy(update={"scope_status": "within_scope"})
    with pytest.raises(ValidationError, match="stale"):
        write_review(ws, tampered)


def test_write_refuses_unsealed(ws):
    p = task(targets=["RA-001"])
    r = evaluate(p, handoff(p, [("RA-001", "read")]))
    with pytest.raises(ValidationError, match="not sealed"):
        write_review(ws, r.model_copy(update={"content_hash": None}))


def test_write_refuses_overwrite(ws):
    p = task(targets=["RA-001"])
    r = evaluate(p, handoff(p, [("RA-001", "read")]))
    write_review(ws, r)
    with pytest.raises(ValidationError, match="immutable"):
        write_review(ws, r)


def test_required_fields_present():
    p = task(targets=["RA-001"])
    data = evaluate(p, handoff(p, [("RA-001", "read")])).to_serialisable()
    for name in ("schema_version", "task_packet_ref", "task_packet_hash",
                 "handoff_packet_hash", "provider", "evaluated_at", "object_results",
                 "scope_status", "human_review_required", "content_hash"):
        assert name in data, name


def test_stored_review_round_trips(ws):
    p = task(targets=["RA-001"])
    r = evaluate(p, handoff(p, [("RA-001", "read")]))
    path = write_review(ws, r)
    loaded = ScopeReview.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    assert loaded.content_hash == r.content_hash
    assert verify_review_content_hash(loaded)


# -- end to end, with packet verification ----------------------------------

def _stored(ws, packet, touches):
    from conclave.handoff import write_handoff
    write_packet(ws, packet)
    h = handoff(packet, touches)
    return write_handoff(ws, h)


def test_review_handoff_end_to_end(ws):
    p = task(targets=["RA-001"], prohibited=["KOS-CONSTITUTION"])
    path = _stored(ws, p, [("RA-001", "proposed_change"), ("KOS-CONSTITUTION", "read")])
    outcome = review_handoff(ws, path)
    assert outcome.review.scope_status == "expansion_detected"
    assert outcome.created is True
    assert outcome.path.parent == scope_dir(ws)
    assert outcome.path.exists()


def test_review_does_not_modify_either_packet(ws):
    p = task(targets=["RA-001"])
    hpath = _stored(ws, p, [("RA-001", "read")])
    tpath = packet_path(ws, p.task_id, 1)
    before_task, before_handoff = tpath.read_bytes(), hpath.read_bytes()
    review_handoff(ws, hpath)
    assert tpath.read_bytes() == before_task
    assert hpath.read_bytes() == before_handoff


def test_missing_task_packet_refused(ws):
    p = task(targets=["RA-001"])
    hpath = _stored(ws, p, [("RA-001", "read")])
    packet_path(ws, p.task_id, 1).unlink()
    with pytest.raises(ValidationError, match="not present"):
        review_handoff(ws, hpath)


def test_altered_task_packet_refused(ws):
    p = task(targets=["RA-001"])
    hpath = _stored(ws, p, [("RA-001", "read")])
    tpath = packet_path(ws, p.task_id, 1)
    data = yaml.safe_load(tpath.read_text(encoding="utf-8"))
    data["target_objects"].append({"object_id": "RA-009", "canonical_id": None,
                                   "object_type": None, "section_id": None,
                                   "expected_version": None, "path_hint": None})
    tpath.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValidationError, match="altered"):
        review_handoff(ws, hpath)


def test_altered_handoff_packet_refused(ws):
    p = task(targets=["RA-001"])
    hpath = _stored(ws, p, [("RA-001", "read")])
    data = yaml.safe_load(hpath.read_text(encoding="utf-8"))
    data["objects_touched"] = []
    hpath.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValidationError, match="altered"):
        review_handoff(ws, hpath)


def test_missing_handoff_file_refused(ws, tmp_path):
    with pytest.raises(ValidationError, match="no such handoff"):
        review_handoff(ws, tmp_path / "nope.yaml")
