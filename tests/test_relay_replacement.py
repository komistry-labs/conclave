"""Forced prompt replacement must be auditable, not silent."""

import pytest

from conclave.errors import ValidationError
from conclave.relay import export_filename, export_prompts, read_export_records
from conclave.taskpacket import build_packet, write_packet
from conclave.workspace import Workspace


@pytest.fixture
def ws(tmp_path):
    return Workspace.create(tmp_path, principal="Arthur")


@pytest.fixture
def config(ws):
    return ws.load_config()


@pytest.fixture
def packet(ws, config):
    p = build_packet(
        objective="Draft RA-001 Part I",
        created_by="Arthur",
        target_objects=[{"object_id": "RA-001"}],
        assigned_providers=[{"provider": "claude", "role": "governance_critic"}],
    )
    write_packet(ws, p)
    return p


def tamper(ws, packet, text="different content\n"):
    (ws.outbox_dir / export_filename(packet, "claude")).write_text(text, encoding="utf-8")


def test_force_without_reason_is_refused(ws, packet, config):
    export_prompts(ws, packet, config)
    tamper(ws, packet)
    with pytest.raises(ValidationError, match="requires a reason"):
        export_prompts(ws, packet, config, force=True)


def test_force_with_blank_reason_is_refused(ws, packet, config):
    export_prompts(ws, packet, config)
    tamper(ws, packet)
    with pytest.raises(ValidationError, match="requires a reason"):
        export_prompts(ws, packet, config, force=True, reason="   ")


def test_replacement_status_is_distinct(ws, packet, config):
    export_prompts(ws, packet, config)
    tamper(ws, packet)
    results = export_prompts(ws, packet, config, force=True,
                             reason="prompt template corrected", authority="Arthur")
    assert results[0].status == "replaced"


def test_replacement_event_recorded(ws, packet, config):
    original = export_prompts(ws, packet, config)[0]
    tamper(ws, packet)
    replacement = export_prompts(ws, packet, config, force=True,
                                 reason="prompt template corrected",
                                 authority="Arthur")[0]

    events = [r for r in read_export_records(ws)
              if r["event_type"] == "prompt_export_replaced"]
    assert len(events) == 1
    e = events[0]
    for key in ("packet_ref", "packet_content_hash", "provider", "role", "prompt_file",
                "replaced_prompt_hash", "replacement_prompt_hash", "replaced_at",
                "replacement_reason", "replacement_authority"):
        assert key in e, key
    assert e["packet_ref"] == packet.ref
    assert e["provider"] == "claude"
    assert e["role"] == "governance_critic"
    assert e["replacement_reason"] == "prompt template corrected"
    assert e["replacement_authority"] == "Arthur"
    assert e["replacement_prompt_hash"] == replacement.prompt_hash == original.prompt_hash


def test_replaced_prompt_hash_is_the_hash_that_was_destroyed(ws, packet, config):
    from conclave.hashing import hash_text
    export_prompts(ws, packet, config)
    tamper(ws, packet, "the content being destroyed\n")
    destroyed = hash_text("the content being destroyed\n")
    export_prompts(ws, packet, config, force=True, reason="r", authority="Arthur")
    e = [r for r in read_export_records(ws) if r["event_type"] == "prompt_export_replaced"][0]
    assert e["replaced_prompt_hash"] == destroyed


def test_replacement_is_not_recorded_as_ordinary_export(ws, packet, config):
    export_prompts(ws, packet, config)
    tamper(ws, packet)
    export_prompts(ws, packet, config, force=True, reason="r", authority="Arthur")
    exported = [r for r in read_export_records(ws) if r["event_type"] == "prompt_exported"]
    assert len(exported) == 1, "the replacement must not appear as an initial export"


def test_ordinary_export_carries_event_type(ws, packet, config):
    export_prompts(ws, packet, config)
    assert read_export_records(ws)[0]["event_type"] == "prompt_exported"


def test_idempotent_reexport_records_nothing(ws, packet, config):
    export_prompts(ws, packet, config)
    export_prompts(ws, packet, config)
    export_prompts(ws, packet, config, force=True, reason="unnecessary but harmless")
    assert len(read_export_records(ws)) == 1


def test_force_on_first_export_is_an_ordinary_export(ws, packet, config):
    results = export_prompts(ws, packet, config, force=True, reason="not actually replacing")
    assert results[0].status == "created"
    assert read_export_records(ws)[0]["event_type"] == "prompt_exported"
