"""A Scope Review is an attestation, not a recomputation."""

import pytest
import yaml

from conclave.errors import ValidationError
from conclave.handoff import HandoffPacket, seal_handoff, write_handoff
from conclave.scope import SCOPE_SCHEMA_VERSION, review_handoff, scope_dir
from conclave.taskpacket import build_packet, write_packet
from conclave.workspace import Workspace, utcnow


@pytest.fixture
def ws(tmp_path):
    return Workspace.create(tmp_path, principal="Arthur")


@pytest.fixture
def stored(ws):
    packet = build_packet(
        objective="Draft RA-001 Part I", created_by="Arthur",
        target_objects=[{"object_id": "RA-001"}],
        prohibited_objects=[{"object_id": "KOS-CONSTITUTION"}],
        assigned_providers=[{"provider": "claude", "role": "governance_critic"}],
    )
    write_packet(ws, packet)
    h = seal_handoff(HandoffPacket.model_validate({
        "packet_ref": packet.ref, "packet_content_hash": packet.content_hash,
        "provider": "claude", "role": "governance_critic", "status": "submitted",
        "objects_touched": [{"object_id": "KOS-CONSTITUTION", "action": "read"}],
        "output": {}, "findings": [], "assumptions": [], "abstentions": [],
        "unresolved": [], "evidence_used": [], "recommended_next_action": "revise",
        "raw_response_hash": "sha256:" + "1" * 64,
        "prompt_hash": "sha256:" + "2" * 64, "imported_at": utcnow(),
    }))
    return packet, write_handoff(ws, h)


def test_first_run_creates(ws, stored):
    _, path = stored
    outcome = review_handoff(ws, path)
    assert outcome.created is True
    assert outcome.path.exists()


def test_second_run_returns_unchanged(ws, stored):
    _, path = stored
    first = review_handoff(ws, path)
    second = review_handoff(ws, path)
    assert second.created is False
    assert second.path == first.path


def test_evaluated_at_is_not_recomputed(ws, stored):
    _, path = stored
    first = review_handoff(ws, path)
    second = review_handoff(ws, path)
    assert second.review.evaluated_at == first.review.evaluated_at
    assert second.review.content_hash == first.review.content_hash


def test_nothing_is_rewritten_on_second_run(ws, stored):
    _, path = stored
    first = review_handoff(ws, path)
    before = first.path.read_bytes()
    review_handoff(ws, path)
    assert first.path.read_bytes() == before


def test_only_one_review_file_exists(ws, stored):
    _, path = stored
    review_handoff(ws, path)
    review_handoff(ws, path)
    review_handoff(ws, path)
    assert len(list(scope_dir(ws).glob("*.yaml"))) == 1


def test_verdict_is_stable_across_runs(ws, stored):
    _, path = stored
    a = review_handoff(ws, path).review
    b = review_handoff(ws, path).review
    assert a.scope_status == b.scope_status == "expansion_detected"
    assert a.human_review_required == b.human_review_required is True


def test_filename_carries_schema_version(ws, stored):
    _, path = stored
    name = review_handoff(ws, path).path.name
    assert f"scope-{SCOPE_SCHEMA_VERSION.rsplit('/', 1)[-1]}" in name


def test_tampered_existing_review_is_refused(ws, stored):
    _, path = stored
    outcome = review_handoff(ws, path)
    data = yaml.safe_load(outcome.path.read_text(encoding="utf-8"))
    data["scope_status"] = "within_scope"
    data["human_review_required"] = False
    outcome.path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValidationError, match="content_hash"):
        review_handoff(ws, path)


def test_existing_review_with_wrong_provenance_is_refused(ws, stored):
    """Re-sealed after tampering: hash verifies, provenance does not."""
    from conclave.scope import read_review, seal
    _, path = stored
    outcome = review_handoff(ws, path)
    forged = seal(read_review(outcome.path).model_copy(
        update={"task_packet_hash": "sha256:" + "0" * 64}))
    outcome.path.write_text(
        yaml.safe_dump(forged.to_serialisable(), sort_keys=False), encoding="utf-8")
    with pytest.raises(ValidationError, match="task_packet_hash"):
        review_handoff(ws, path)


def test_unreadable_existing_review_is_refused(ws, stored):
    _, path = stored
    outcome = review_handoff(ws, path)
    outcome.path.write_text("not: [valid yaml", encoding="utf-8")
    with pytest.raises(ValidationError, match="unreadable"):
        review_handoff(ws, path)


def test_no_force_option_exists():
    """A --force would let a later run silently overwrite an earlier finding."""
    import inspect
    assert "force" not in inspect.signature(review_handoff).parameters
