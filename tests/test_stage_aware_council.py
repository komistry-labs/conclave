import yaml

from conclave.council import (
    CouncilReview, LEGACY_COUNCIL_SCHEMA_VERSION, build_council_review,
    compute_content_hash, review_task, verify_council_content_hash,
)
from conclave.hashing import hash_text
from conclave.handoff import HandoffPacket, seal_handoff, write_handoff
from conclave.routing import (
    ProviderCapability, TokenBudget, build_route, write_route_plan,
)
from conclave.scope import evaluate, write_review
from conclave.taskpacket import build_packet, write_packet
from conclave.workspace import Workspace, utcnow


def test_route_stages_keep_same_provider_roles_distinct(tmp_path):
    ws = Workspace.create(tmp_path, principal="Arthur")
    packet = build_packet(
        objective="Stage aware council", created_by="Arthur",
        target_objects=[{"object_id": "DOC-001"}],
    )
    write_packet(ws, packet)
    roles = frozenset({"lead", "critic", "verifier", "synthesizer"})
    route = build_route(
        packet_ref=packet.ref, risk="canonical",
        capabilities=[
            ProviderCapability(provider="adrian", roles=roles),
            ProviderCapability(provider="claude", roles=roles),
            ProviderCapability(provider="gemini", roles=roles),
        ],
        budget=TokenBudget(max_input_tokens=1000, max_output_tokens=1000),
    )
    route_path, _ = write_route_plan(ws, route)

    for index, stage in enumerate(route.stages):
        handoff = seal_handoff(HandoffPacket.model_validate({
            "packet_ref": packet.ref,
            "packet_content_hash": packet.content_hash,
            "provider": stage.provider,
            "role": stage.role,
            "status": "submitted",
            "objects_touched": [{"object_id": "DOC-001", "action": "read"}],
            "output": {"type": stage.role, "summary": stage.role, "body": "work"},
            "findings": [], "assumptions": [], "abstentions": [],
            "unresolved": [], "evidence_used": [],
            "recommended_next_action": "accept",
            "raw_response_hash": "sha256:" + str(index + 1) * 64,
            "prompt_hash": "sha256:" + "a" * 64,
            "imported_at": utcnow(),
            "route_plan_hash": route.content_hash,
            "route_stage_index": index,
        }))
        write_handoff(ws, handoff)
        write_review(ws, evaluate(packet, handoff))

    outcome = review_task(ws, packet.task_id, 1, route_path=route_path)
    review = outcome.review
    assert review.selection_basis == "route_plan_stages"
    assert review.route_plan_hash == route.content_hash
    assert len(review.providers_expected) == 4
    assert len(review.submissions) == 4
    assert review.missing_providers == []
    assert review.review_status == "ready_for_human_review"
    assert len({s.participant_key for s in review.submissions}) == 4


def test_wrong_route_hash_does_not_satisfy_stage(tmp_path):
    ws = Workspace.create(tmp_path, principal="Arthur")
    packet = build_packet(objective="Wrong route", created_by="Arthur")
    write_packet(ws, packet)
    route = build_route(
        packet_ref=packet.ref, risk="routine",
        capabilities=[ProviderCapability(
            provider="adrian", roles=frozenset({"lead"})
        )],
        budget=TokenBudget(max_input_tokens=100, max_output_tokens=100),
    )
    route_path, _ = write_route_plan(ws, route)
    handoff = seal_handoff(HandoffPacket.model_validate({
        "packet_ref": packet.ref, "packet_content_hash": packet.content_hash,
        "provider": "adrian", "role": "lead", "status": "submitted",
        "objects_touched": [], "output": {}, "findings": [], "assumptions": [],
        "abstentions": [], "unresolved": [], "evidence_used": [],
        "recommended_next_action": "accept",
        "raw_response_hash": "sha256:" + "1" * 64,
        "prompt_hash": "sha256:" + "2" * 64, "imported_at": utcnow(),
        "route_plan_hash": "sha256:" + "f" * 64, "route_stage_index": 0,
    }))
    write_handoff(ws, handoff)
    write_review(ws, evaluate(packet, handoff))
    review = review_task(ws, packet.task_id, 1, route_path=route_path).review
    assert review.review_status == "incomplete"
    assert review.missing_providers == ["s0:adrian:lead"]


def test_legacy_council_hash_verifies_without_new_default_fields():
    packet = build_packet(objective="Legacy council", created_by="Arthur")
    current = build_council_review(packet, [], {})
    legacy = current.model_dump(mode="json")
    legacy["schema_version"] = LEGACY_COUNCIL_SCHEMA_VERSION
    legacy.pop("route_plan_hash")
    legacy.pop("selection_basis")
    legacy.pop("content_hash")
    legacy_hash = hash_text(yaml.safe_dump(
        legacy, sort_keys=True, allow_unicode=True
    ))
    loaded = CouncilReview.model_validate({
        **legacy, "content_hash": legacy_hash
    })
    assert verify_council_content_hash(loaded)


def test_ineligible_handoff_does_not_change_route_review_identity(tmp_path):
    ws = Workspace.create(tmp_path, principal="Arthur")
    packet = build_packet(objective="Evidence filtering", created_by="Arthur")
    write_packet(ws, packet)
    route = build_route(
        packet_ref=packet.ref, risk="routine",
        capabilities=[ProviderCapability(
            provider="adrian", roles=frozenset({"lead"})
        )],
        budget=TokenBudget(max_input_tokens=100, max_output_tokens=100),
    )
    route_path, _ = write_route_plan(ws, route)
    first = review_task(ws, packet.task_id, 1, route_path=route_path).review
    foreign = seal_handoff(HandoffPacket.model_validate({
        "packet_ref": packet.ref, "packet_content_hash": packet.content_hash,
        "provider": "claude", "role": "critic", "status": "submitted",
        "objects_touched": [], "output": {}, "findings": [], "assumptions": [],
        "abstentions": [], "unresolved": [], "evidence_used": [],
        "recommended_next_action": "accept",
        "raw_response_hash": "sha256:" + "3" * 64,
        "prompt_hash": "sha256:" + "4" * 64, "imported_at": utcnow(),
        "route_plan_hash": "sha256:" + "f" * 64, "route_stage_index": 0,
    }))
    write_handoff(ws, foreign)
    write_review(ws, evaluate(packet, foreign))
    second = review_task(ws, packet.task_id, 1, route_path=route_path).review
    assert second.council_review_id == first.council_review_id
    assert second.content_hash == first.content_hash
