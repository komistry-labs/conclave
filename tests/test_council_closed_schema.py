"""The canonical Council Review is a closed schema."""

import pytest
import yaml

from conclave.council import CouncilReview, read_council, review_task
from conclave.handoff import HandoffPacket, seal_handoff, write_handoff
from conclave.scope import evaluate, write_review
from conclave.taskpacket import build_packet, write_packet
from conclave.workspace import Workspace, utcnow


@pytest.fixture
def ws(tmp_path):
    return Workspace.create(tmp_path, principal="Arthur")


@pytest.fixture
def outcome(ws):
    p = build_packet(objective="Draft RA-001 Part I", created_by="Arthur",
                     target_objects=[{"object_id": "RA-001"}],
                     assigned_providers=[{"provider": "claude", "role": "governance_critic"}])
    write_packet(ws, p)
    h = seal_handoff(HandoffPacket.model_validate({
        "packet_ref": p.ref, "packet_content_hash": p.content_hash,
        "provider": "claude", "role": "governance_critic", "status": "submitted",
        "objects_touched": [{"object_id": "RA-001", "action": "read"}],
        "output": {}, "findings": [], "assumptions": [], "abstentions": [],
        "unresolved": [], "evidence_used": [], "recommended_next_action": "revise",
        "raw_response_hash": "sha256:" + "1" * 64,
        "prompt_hash": "sha256:" + "2" * 64, "imported_at": utcnow(),
    }))
    write_handoff(ws, h)
    write_review(ws, evaluate(p, h))
    return review_task(ws, p.task_id, 1)


def _base(outcome):
    return outcome.review.to_serialisable()


def test_arbitrary_unknown_field_rejected(outcome):
    data = {**_base(outcome), "some_unexpected_field": "anything"}
    with pytest.raises(Exception):
        CouncilReview.model_validate(data)


def test_plausible_looking_unknown_field_rejected(outcome):
    data = {**_base(outcome), "reviewer_notes": "looks fine to me"}
    with pytest.raises(Exception):
        CouncilReview.model_validate(data)


@pytest.mark.parametrize("field,value", [
    ("approved", True),
    ("ratified", True),
    ("commissioned", True),
    ("merged", True),
    ("merge_authorised", True),
    ("authority_override", "granted"),
    ("decision", "approve"),
    ("decided_by", "claude"),
    ("authorised_actions", ["merge"]),
])
def test_authority_bearing_unknown_fields_rejected(outcome, field, value):
    """A manipulated review must not be able to smuggle in an authorisation."""
    with pytest.raises(Exception):
        CouncilReview.model_validate({**_base(outcome), field: value})


def test_tampered_file_with_authority_field_refuses_to_load(outcome):
    data = yaml.safe_load(outcome.yaml_path.read_text(encoding="utf-8"))
    data["merge_authorised"] = True
    outcome.yaml_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(Exception):
        read_council(outcome.yaml_path)


def test_tampered_review_blocks_regeneration(outcome, ws):
    """A council review that will not parse cannot be silently replaced either."""
    from conclave.errors import ValidationError
    data = yaml.safe_load(outcome.yaml_path.read_text(encoding="utf-8"))
    data["approved"] = True
    outcome.yaml_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    task_id = outcome.review.task_packet_ref.split("@")[0]
    with pytest.raises(ValidationError, match="unreadable"):
        review_task(ws, task_id, 1)


def test_valid_review_still_round_trips(outcome):
    assert read_council(outcome.yaml_path).content_hash == outcome.review.content_hash


def test_declared_optional_fields_still_accepted(outcome):
    data = _base(outcome)
    assert "superseded_submissions" in data
    assert "comparison_basis" in data
    assert CouncilReview.model_validate(data).content_hash == outcome.review.content_hash
