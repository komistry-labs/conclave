"""Handoff import: extraction, schema, provenance, immutability, repair."""

import textwrap

import pytest
import yaml

from conclave.handoff import (
    HandoffPacket,
    extract_yaml_block,
    handoff_filename,
    import_response,
    raw_dir,
    repair_dir,
)
from conclave.hashing import hash_file
from conclave.relay import export_prompts, read_export_records
from conclave.taskpacket import build_packet, packet_path, write_packet
from conclave.workspace import Workspace


@pytest.fixture
def ws(tmp_path):
    return Workspace.create(tmp_path, principal="Arthur")


@pytest.fixture
def config(ws):
    return ws.load_config()


@pytest.fixture
def exported(ws, config):
    """A packet exported to claude and gemini, ready for responses."""
    packet = build_packet(
        objective="Draft RA-001 Part I",
        created_by="Arthur",
        target_objects=[{"object_id": "RA-001", "section_id": "RA-001-PART-I"}],
        read_only_objects=[{"object_id": "ADR-0002"}],
        assigned_providers=[
            {"provider": "claude", "role": "governance_critic"},
            {"provider": "gemini", "role": "external_verifier"},
        ],
    )
    write_packet(ws, packet)
    export_prompts(ws, packet, config)
    return packet


def response_yaml(packet, provider="claude", role="governance_critic", **over):
    body = {
        "handoff_packet": "handoff-packet/0.1.0",
        "packet_ref": packet.ref,
        "packet_content_hash": packet.content_hash,
        "provider": provider,
        "role": role,
        "status": "submitted",
        "objects_touched": [
            {"object_id": "RA-001", "section_id": "RA-001-PART-I", "action": "proposed_change"},
            {"object_id": "ADR-0002", "action": "cited"},
        ],
        "output": {"type": "critique", "summary": "s", "body": "b"},
        "findings": [{"finding_id": "F-001", "severity": "high", "claim": "c"}],
        "assumptions": [],
        "abstentions": [],
        "unresolved": [],
        "evidence_used": [],
        "recommended_next_action": "revise",
    }
    body.update(over)
    return body


def write_response(tmp_path, body, name="reply.md", prose="Here is my response.\n\n"):
    text = prose + "```yaml\n" + yaml.safe_dump(body, sort_keys=False) + "```\n"
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


# -- extraction ------------------------------------------------------------

def test_extracts_single_yaml_block():
    block, defects = extract_yaml_block("intro\n```yaml\na: 1\n```\noutro\n")
    assert defects == []
    assert block.strip() == "a: 1"


def test_zero_blocks_rejected():
    block, defects = extract_yaml_block("just prose, no fences at all")
    assert block is None
    assert defects[0].code == "no-yaml-block"


def test_multiple_yaml_blocks_rejected_as_ambiguous():
    block, defects = extract_yaml_block("```yaml\na: 1\n```\n```yaml\nb: 2\n```\n")
    assert block is None
    assert defects[0].code == "ambiguous-yaml-blocks"


def test_untagged_block_accepted_when_no_tagged_block():
    block, defects = extract_yaml_block("```\na: 1\n```\n")
    assert defects == []
    assert block.strip() == "a: 1"


def test_tagged_block_wins_over_untagged():
    """Deterministic preference, not a guess among heterogeneous blocks."""
    block, defects = extract_yaml_block("```\nnoise\n```\n```yaml\na: 1\n```\n")
    assert defects == []
    assert block.strip() == "a: 1"


def test_other_language_blocks_are_never_candidates():
    block, defects = extract_yaml_block("```python\nx = 1\n```\n```yaml\na: 1\n```\n")
    assert defects == []
    assert block.strip() == "a: 1"


def test_prose_is_not_accepted_as_fields():
    block, defects = extract_yaml_block("packet_ref: TP-x@v1\nstatus: submitted\n")
    assert block is None
    assert defects[0].code == "no-yaml-block"


# -- valid import ----------------------------------------------------------

def test_valid_import(ws, exported, tmp_path):
    src = write_response(tmp_path, response_yaml(exported))
    result = import_response(ws, src)
    assert result.status == "imported", [str(d) for d in result.defects]
    assert result.packet.provider == "claude"
    assert result.packet.role == "governance_critic"
    assert result.handoff_path.exists()


def test_import_injects_system_fields(ws, exported, tmp_path):
    src = write_response(tmp_path, response_yaml(exported))
    p = import_response(ws, src).packet
    assert p.raw_response_hash.startswith("sha256:")
    assert p.prompt_hash.startswith("sha256:")
    assert p.imported_at.endswith("Z")
    assert p.content_hash.startswith("sha256:")


def test_prompt_hash_bound_from_export_record(ws, exported, tmp_path):
    src = write_response(tmp_path, response_yaml(exported))
    p = import_response(ws, src).packet
    rec = {r["provider"]: r for r in read_export_records(ws)}["claude"]
    assert p.prompt_hash == rec["prompt_hash"]


def test_objects_touched_captured(ws, exported, tmp_path):
    src = write_response(tmp_path, response_yaml(exported))
    p = import_response(ws, src).packet
    assert p.touched_keys() == {"RA-001#RA-001-PART-I", "ADR-0002"}


def test_handoff_filename_shape(ws, exported, tmp_path):
    src = write_response(tmp_path, response_yaml(exported))
    p = import_response(ws, src).packet
    assert handoff_filename(p).startswith(f"{exported.task_id}__v1__claude__")
    assert handoff_filename(p).endswith(".yaml")
    assert ":" not in handoff_filename(p)


# -- raw preservation ------------------------------------------------------

def test_raw_preserved_verbatim(ws, exported, tmp_path):
    src = write_response(tmp_path, response_yaml(exported))
    original = src.read_bytes()
    result = import_response(ws, src)
    assert result.raw_path.read_bytes() == original


def test_raw_preserved_even_when_rejected(ws, tmp_path):
    src = tmp_path / "garbage.md"
    src.write_text("no yaml here at all", encoding="utf-8")
    result = import_response(ws, src)
    assert result.status == "rejected"
    assert result.raw_path.exists()
    assert result.raw_path.read_text(encoding="utf-8") == "no yaml here at all"


def test_raw_hash_matches_file(ws, exported, tmp_path):
    """Binary hash. Canonical text hashing would match only by coincidence here,
    and would stop matching the moment a response arrived with CRLF."""
    src = write_response(tmp_path, response_yaml(exported))
    result = import_response(ws, src)
    assert hash_file(result.raw_path, binary=True) == result.raw_hash


def test_raw_and_handoff_are_distinct_objects(ws, exported, tmp_path):
    src = write_response(tmp_path, response_yaml(exported))
    result = import_response(ws, src)
    assert result.raw_path != result.handoff_path
    assert result.raw_path.parent == raw_dir(ws)
    assert result.handoff_path.parent == ws.inbox_dir


# -- provenance failures ---------------------------------------------------

def _codes(result):
    return {d.code for d in result.defects}


def test_wrong_packet_reference(ws, exported, tmp_path):
    src = write_response(tmp_path, response_yaml(exported, packet_ref="TP-other-0123456789@v1"))
    result = import_response(ws, src)
    assert result.status == "rejected"
    assert "no-matching-export" in _codes(result)


def test_wrong_packet_hash(ws, exported, tmp_path):
    src = write_response(tmp_path,
                         response_yaml(exported, packet_content_hash="sha256:" + "0" * 64))
    result = import_response(ws, src)
    assert "packet-hash-mismatch" in _codes(result)


def test_wrong_provider(ws, exported, tmp_path):
    src = write_response(tmp_path, response_yaml(exported, provider="adrian"))
    result = import_response(ws, src)
    assert "no-matching-export" in _codes(result)


def test_wrong_role(ws, exported, tmp_path):
    src = write_response(tmp_path, response_yaml(exported, role="institutional_architect"))
    result = import_response(ws, src)
    assert "role-mismatch" in _codes(result)


def test_wrong_prompt_hash_selector(ws, exported, tmp_path):
    src = write_response(tmp_path, response_yaml(exported))
    result = import_response(ws, src, prompt_hash="sha256:" + "9" * 64)
    assert "prompt-hash-mismatch" in _codes(result)


def test_absent_export_record(ws, tmp_path, config):
    """Packet exists and is valid, but was never exported to this provider."""
    packet = build_packet(objective="never exported", created_by="Arthur",
                          target_objects=[{"object_id": "X"}],
                          assigned_providers=[{"provider": "claude", "role": "governance_critic"}])
    write_packet(ws, packet)
    src = write_response(tmp_path, response_yaml(packet))
    result = import_response(ws, src)
    assert "no-matching-export" in _codes(result)


def test_missing_task_packet(ws, exported, tmp_path):
    packet_path(ws, exported.task_id, 1).unlink()
    src = write_response(tmp_path, response_yaml(exported))
    result = import_response(ws, src)
    assert "task-packet-missing" in _codes(result)


def test_altered_task_packet(ws, exported, tmp_path):
    path = packet_path(ws, exported.task_id, 1)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["objective"] = "quietly rewritten after export"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    src = write_response(tmp_path, response_yaml(exported))
    result = import_response(ws, src)
    assert "task-packet-integrity-failure" in _codes(result)


def test_echoing_plausible_identifiers_is_not_enough(ws, tmp_path):
    """Well-formed identifiers that were never issued must not be accepted."""
    fake = build_packet(objective="fabricated", created_by="X",
                        target_objects=[{"object_id": "RA-001"}],
                        assigned_providers=[{"provider": "claude", "role": "governance_critic"}])
    src = write_response(tmp_path, response_yaml(fake))
    result = import_response(ws, src)
    assert result.status == "rejected"
    assert result.handoff_path is None


# -- schema failures -------------------------------------------------------

def test_malformed_yaml(ws, tmp_path):
    src = tmp_path / "bad.md"
    src.write_text("```yaml\nkey: [unclosed\n```\n", encoding="utf-8")
    result = import_response(ws, src)
    assert "malformed-yaml" in _codes(result)


def test_block_not_a_mapping(ws, tmp_path):
    src = tmp_path / "list.md"
    src.write_text("```yaml\n- one\n- two\n```\n", encoding="utf-8")
    result = import_response(ws, src)
    assert "not-a-mapping" in _codes(result)


@pytest.mark.parametrize("field", [
    "packet_ref", "packet_content_hash", "provider", "role", "status",
    "objects_touched", "output", "findings", "assumptions", "abstentions",
    "unresolved", "evidence_used", "recommended_next_action",
])
def test_missing_required_field(ws, exported, tmp_path, field):
    body = response_yaml(exported)
    del body[field]
    src = write_response(tmp_path, body)
    result = import_response(ws, src)
    assert "missing-required-field" in _codes(result)


@pytest.mark.parametrize("field", ["raw_response_hash", "prompt_hash", "imported_at"])
def test_provider_cannot_supply_system_fields(ws, exported, tmp_path, field):
    src = write_response(tmp_path, response_yaml(exported, **{field: "forged"}))
    result = import_response(ws, src)
    assert "provider-supplied-system-field" in _codes(result)


def test_wrong_type_for_list_field(ws, exported, tmp_path):
    src = write_response(tmp_path, response_yaml(exported, findings="not a list"))
    result = import_response(ws, src)
    assert "wrong-type" in _codes(result)


def test_schema_version_mismatch(ws, exported, tmp_path):
    src = write_response(tmp_path,
                         response_yaml(exported, **{"handoff_packet": "handoff-packet/9.9.9"}))
    result = import_response(ws, src)
    assert "schema-version-mismatch" in _codes(result)


# -- no silent repair ------------------------------------------------------

def test_rejected_response_produces_no_handoff(ws, exported, tmp_path):
    body = response_yaml(exported)
    del body["findings"]
    src = write_response(tmp_path, body)
    result = import_response(ws, src)
    assert result.handoff_path is None
    assert list(ws.inbox_dir.glob("*.yaml")) == []


def test_repair_request_generated(ws, exported, tmp_path):
    body = response_yaml(exported)
    del body["objects_touched"]
    src = write_response(tmp_path, body)
    result = import_response(ws, src)
    assert result.repair_path.exists()
    text = result.repair_path.read_text(encoding="utf-8")
    assert "objects_touched" in text
    assert exported.ref in text
    assert result.raw_path.name in text


def test_repair_request_contains_no_fabricated_answer(ws, exported, tmp_path):
    body = response_yaml(exported)
    del body["findings"]
    src = write_response(tmp_path, body)
    text = import_response(ws, src).repair_path.read_text(encoding="utf-8")
    for word in ("suggested finding", "we propose", "for example you could"):
        assert word not in text.lower()
    # No YAML block: the repair request must not hand back a pre-filled
    # response for the provider to sign off on. Naming the required fence in
    # prose is instruction, not substance.
    assert "```yaml\n" not in text


def test_repair_request_survives_unreadable_identifiers(ws, tmp_path):
    src = tmp_path / "junk.md"
    src.write_text("total nonsense", encoding="utf-8")
    text = import_response(ws, src).repair_path.read_text(encoding="utf-8")
    assert "<not supplied or unreadable>" in text


def test_repair_request_quotes_authoritative_role_not_the_wrong_one(ws, exported, tmp_path):
    """A repair request must not tell a provider to repeat its own mistake."""
    body = response_yaml(exported, role="institutional_architect")
    del body["assumptions"]
    src = write_response(tmp_path, body)
    text = import_response(ws, src).repair_path.read_text(encoding="utf-8")
    assert "role                : governance_critic" in text
    assert "institutional_architect" not in text


def test_repair_request_uses_export_record_hash_not_submitted_hash(ws, exported, tmp_path):
    body = response_yaml(exported, packet_content_hash="sha256:" + "0" * 64)
    del body["assumptions"]
    src = write_response(tmp_path, body)
    text = import_response(ws, src).repair_path.read_text(encoding="utf-8")
    assert exported.content_hash in text
    assert "0" * 64 not in text


# -- immutability and duplicates -------------------------------------------

def test_duplicate_raw_response_is_idempotent(ws, exported, tmp_path):
    src = write_response(tmp_path, response_yaml(exported))
    first = import_response(ws, src)
    second = import_response(ws, src)
    assert first.status == "imported"
    assert second.status == "duplicate"
    assert len(list(ws.inbox_dir.glob("*.yaml"))) == 1


def test_duplicate_of_rejected_response_says_rejected_not_imported(ws, exported, tmp_path):
    body = response_yaml(exported)
    del body["findings"]
    src = write_response(tmp_path, body)
    import_response(ws, src)
    second = import_response(ws, src)
    assert second.status == "duplicate"
    assert second.handoff_path is None
    assert second.repair_path is not None
    assert "rejected" in second.defects[0].message


def test_duplicate_does_not_overwrite_raw(ws, exported, tmp_path):
    src = write_response(tmp_path, response_yaml(exported))
    first = import_response(ws, src)
    before = first.raw_path.read_bytes()
    import_response(ws, src)
    assert first.raw_path.read_bytes() == before


def test_two_distinct_responses_from_one_provider_both_stored(ws, exported, tmp_path):
    a = write_response(tmp_path, response_yaml(exported), name="a.md")
    b = write_response(tmp_path,
                       response_yaml(exported, status="abstained",
                                     recommended_next_action="abstain"),
                       name="b.md", prose="Second attempt.\n\n")
    ra, rb = import_response(ws, a), import_response(ws, b)
    assert ra.status == "imported" and rb.status == "imported"
    assert ra.handoff_path != rb.handoff_path
    assert len(list(ws.inbox_dir.glob("*.yaml"))) == 2
    assert len(list(raw_dir(ws).glob("*.raw.md"))) == 2


def test_later_response_does_not_overwrite_earlier(ws, exported, tmp_path):
    a = write_response(tmp_path, response_yaml(exported), name="a.md")
    ra = import_response(ws, a)
    before = ra.handoff_path.read_bytes()
    b = write_response(tmp_path, response_yaml(exported, status="blocked"),
                       name="b.md", prose="Different.\n\n")
    import_response(ws, b)
    assert ra.handoff_path.read_bytes() == before


def test_handoff_packet_is_frozen(ws, exported, tmp_path):
    src = write_response(tmp_path, response_yaml(exported))
    p = import_response(ws, src).packet
    with pytest.raises(Exception):
        p.status = "approved"


def test_stored_handoff_round_trips(ws, exported, tmp_path):
    src = write_response(tmp_path, response_yaml(exported))
    result = import_response(ws, src)
    data = yaml.safe_load(result.handoff_path.read_text(encoding="utf-8"))
    assert HandoffPacket.model_validate(data).content_hash == result.packet.content_hash


def test_stored_handoff_is_lf(ws, exported, tmp_path):
    src = write_response(tmp_path, response_yaml(exported))
    assert b"\r\n" not in import_response(ws, src).handoff_path.read_bytes()


# -- ambiguity after forced replacement ------------------------------------

def _simulate_template_change(ws, packet):
    """Append a replacement event whose prompt content genuinely differs.

    Forcing a replacement in-process regenerates an identical prompt (the
    packet has not changed), so it cannot produce this state. A real template
    change between exports can, and that is the case worth defending against.
    """
    from conclave.relay import append_export_record, read_export_records
    original = [r for r in read_export_records(ws) if r["provider"] == "claude"][0]
    append_export_record(ws, {
        **original,
        "event_type": "prompt_export_replaced",
        "replaced_prompt_hash": original["prompt_hash"],
        "replacement_prompt_hash": "sha256:" + "a" * 64,
        "replaced_at": "2026-07-27T00:00:00Z",
        "replacement_reason": "prompt template revised",
        "replacement_authority": "Arthur",
    })
    return original["prompt_hash"], "sha256:" + "a" * 64


def test_identical_forced_replacement_is_not_ambiguous(ws, exported, config, tmp_path):
    """Two records describing the same prompt content answer the same question."""
    from conclave.relay import export_filename
    (ws.outbox_dir / export_filename(exported, "claude")).write_text("tampered\n",
                                                                    encoding="utf-8")
    export_prompts(ws, exported, config, providers=["claude"],
                   force=True, reason="restored after tampering", authority="Arthur")
    src = write_response(tmp_path, response_yaml(exported))
    result = import_response(ws, src)
    assert result.status == "imported", [str(d) for d in result.defects]


def test_materially_different_prompts_are_ambiguous(ws, exported, tmp_path):
    _simulate_template_change(ws, exported)
    src = write_response(tmp_path, response_yaml(exported))
    result = import_response(ws, src)
    assert "ambiguous-export" in _codes(result)


def test_selector_resolves_ambiguity(ws, exported, tmp_path):
    original_hash, _ = _simulate_template_change(ws, exported)
    src = write_response(tmp_path, response_yaml(exported))
    result = import_response(ws, src, prompt_hash=original_hash)
    assert result.status == "imported", [str(d) for d in result.defects]
    assert result.packet.prompt_hash == original_hash
