"""Relay export: prompt projection, independence, filenames, idempotency."""

import pytest

from conclave.errors import ValidationError
from conclave.models import ObjectRef
from conclave.relay import (
    HANDOFF_SCHEMA_VERSION,
    build_prompt,
    export_filename,
    export_prompts,
    hash_suffix,
    read_export_records,
    render_object_ref,
)
from conclave.taskpacket import build_packet, read_packet, write_packet
from conclave.workspace import Workspace


@pytest.fixture
def ws(tmp_path):
    return Workspace.create(tmp_path, principal="Arthur")


@pytest.fixture
def config(ws):
    return ws.load_config()


def make(**kw):
    defaults = dict(
        objective="Draft RA-001 Part I",
        created_by="Arthur",
        target_objects=[{"object_id": "RA-001", "section_id": "RA-001-PART-I"}],
        read_only_objects=[{"object_id": "ADR-0002"}, {"object_id": "ADR-0005"}],
        prohibited_objects=[{"object_id": "KOS-CONSTITUTION"}],
        assigned_providers=[
            {"provider": "adrian", "role": "institutional_architect"},
            {"provider": "claude", "role": "governance_critic"},
            {"provider": "gemini", "role": "external_verifier"},
        ],
        constraints=["do not rename approved Reasoning Architectures"],
        acceptance_criteria=["constitutional grounding stated explicitly"],
    )
    defaults.update(kw)
    return build_packet(**defaults)


# -- filenames -------------------------------------------------------------

def test_hash_suffix_strips_algorithm_prefix():
    """A colon is invalid in Windows filenames."""
    assert hash_suffix("sha256:abcdef0123456789") == "abcdef012345"
    assert ":" not in hash_suffix("sha256:" + "f" * 64)


def test_filename_shape():
    p = make()
    name = export_filename(p, "claude")
    assert name == f"{p.task_id}__v1__claude__{hash_suffix(p.content_hash)}.md"


def test_filename_is_windows_safe():
    name = export_filename(make(), "claude")
    assert not set(name) & set('<>:"/\\|?*')


def test_filename_changes_with_version(ws, config):
    from conclave.taskpacket import build_revision
    v1 = make()
    v2 = build_revision(v1, reason="r", changes={"objective": "different"})
    assert export_filename(v1, "claude") != export_filename(v2, "claude")


def test_filename_encodes_packet_hash():
    """A stale prompt cannot be mistaken for one matching a revised packet."""
    p = make()
    assert hash_suffix(p.content_hash) in export_filename(p, "claude")


# -- projection ------------------------------------------------------------

def test_object_ref_rendering_omits_nulls():
    assert render_object_ref(ObjectRef(object_id="ADR-0002")) == "ADR-0002"


def test_object_ref_rendering_includes_present_fields():
    line = render_object_ref(ObjectRef(
        object_id="RA-001", section_id="RA-001-PART-I",
        expected_version="0.3.0", canonical_id="kos:framework:000001",
    ))
    assert "RA-001" in line and "RA-001-PART-I" in line
    assert "0.3.0" in line and "kos:framework:000001" in line


def test_prompt_omits_null_fields(config):
    """The projection must not carry 'null' noise into provider context.

    Checked against the projection only. The response template below it
    legitimately contains `section_id: null` as an instruction to the
    provider, which is not the same thing.
    """
    p = make(interpreted_objective=None)
    prompt = build_prompt(p, p.assigned_providers[0], config)
    projection = prompt.split("## Required response format")[0]
    assert "null" not in projection
    assert "None" not in projection
    assert "Interpreted objective" not in projection


def test_prompt_includes_interpreted_objective_when_present(config):
    p = make(interpreted_objective="Produce a governed proposal for Part I.")
    prompt = build_prompt(p, p.assigned_providers[0], config)
    assert "Produce a governed proposal for Part I." in prompt


def test_prompt_contains_required_elements(config):
    p = make()
    a = p.assigned_providers[1]
    prompt = build_prompt(p, a, config)
    assert p.ref in prompt
    assert p.content_hash in prompt          # FULL hash, not the suffix
    assert a.provider in prompt
    assert a.role in prompt
    assert p.objective in prompt
    assert "RA-001" in prompt
    assert "ADR-0002" in prompt
    assert "KOS-CONSTITUTION" in prompt
    assert "do not rename approved Reasoning Architectures" in prompt
    assert "constitutional grounding stated explicitly" in prompt
    assert "advisory" in prompt
    assert HANDOFF_SCHEMA_VERSION in prompt


def test_prompt_states_authority_boundary(config):
    p = make()
    prompt = build_prompt(p, p.assigned_providers[0], config)
    assert "may not approve" in prompt
    assert "Arthur is the sole constitutional authority" in prompt


def test_prompt_requires_objects_touched(config):
    """Scope drift detection depends on this field being requested."""
    p = make()
    assert "objects_touched" in build_prompt(p, p.assigned_providers[0], config)


def test_prompt_uses_provider_display_name(config):
    p = make()
    prompt = build_prompt(p, p.assigned_providers[0], config)
    assert "Adrian (ChatGPT)" in prompt


def test_output_type_varies_by_role(config):
    p = make()
    prompts = {a.provider: build_prompt(p, a, config) for a in p.assigned_providers}
    assert "type: draft" in prompts["adrian"]
    assert "type: critique" in prompts["claude"]
    assert "type: verification" in prompts["gemini"]


def test_empty_scope_sets_render_as_none(config):
    p = build_packet(objective="o", created_by="A",
                     target_objects=[{"object_id": "X"}],
                     assigned_providers=[{"provider": "claude", "role": "critic"}])
    prompt = build_prompt(p, p.assigned_providers[0], config)
    assert "_none_" in prompt


# -- independence ----------------------------------------------------------

def test_prompts_do_not_mention_other_providers(config):
    p = make()
    for a in p.assigned_providers:
        prompt = build_prompt(p, a, config)
        others = {x.provider for x in p.assigned_providers} - {a.provider}
        for other in others:
            assert other not in prompt, f"{a.provider}'s prompt mentions {other}"


def test_prompts_do_not_mention_other_roles(config):
    p = make()
    for a in p.assigned_providers:
        prompt = build_prompt(p, a, config)
        others = {x.role for x in p.assigned_providers} - {a.role}
        for role in others:
            assert role not in prompt


def test_prompt_instructs_independence(config):
    p = make()
    assert "independently" in build_prompt(p, p.assigned_providers[0], config)


# -- export ----------------------------------------------------------------

def test_export_writes_one_file_per_provider(ws, config):
    p = make()
    write_packet(ws, p)
    results = export_prompts(ws, p, config)
    assert len(results) == 3
    assert all(r.status == "created" for r in results)
    assert len(list(ws.outbox_dir.glob("*.md"))) == 3


def test_export_does_not_modify_packet(ws, config):
    p = make()
    path = write_packet(ws, p)
    before = path.read_bytes()
    export_prompts(ws, p, config)
    assert path.read_bytes() == before
    assert read_packet(ws, p.task_id, 1).content_hash == p.content_hash


def test_export_is_idempotent(ws, config):
    p = make()
    write_packet(ws, p)
    export_prompts(ws, p, config)
    second = export_prompts(ws, p, config)
    assert all(r.status == "unchanged" for r in second)


def test_idempotent_export_does_not_duplicate_records(ws, config):
    p = make()
    write_packet(ws, p)
    export_prompts(ws, p, config)
    export_prompts(ws, p, config)
    assert len(read_export_records(ws)) == 3


def test_export_refuses_to_overwrite_differing_content(ws, config):
    p = make()
    write_packet(ws, p)
    export_prompts(ws, p, config)
    path = ws.outbox_dir / export_filename(p, "claude")
    path.write_bytes(b"tampered\n")
    results = {r.provider: r for r in export_prompts(ws, p, config)}
    assert results["claude"].status == "refused"
    assert path.read_bytes() == b"tampered\n"


def test_force_with_reason_replaces(ws, config):
    p = make()
    write_packet(ws, p)
    export_prompts(ws, p, config)
    path = ws.outbox_dir / export_filename(p, "claude")
    path.write_bytes(b"tampered\n")
    results = {r.provider: r for r in export_prompts(
        ws, p, config, force=True, reason="restoring after tampering", authority="Arthur")}
    assert results["claude"].status == "replaced"
    assert b"tampered" not in path.read_bytes()


def test_export_subset_of_providers(ws, config):
    p = make()
    write_packet(ws, p)
    results = export_prompts(ws, p, config, providers=["claude"])
    assert len(results) == 1
    assert len(list(ws.outbox_dir.glob("*.md"))) == 1


def test_export_unassigned_provider_rejected(ws, config):
    p = make()
    write_packet(ws, p)
    with pytest.raises(ValidationError, match="not assigned"):
        export_prompts(ws, p, config, providers=["mistral"])


def test_export_unsealed_packet_rejected(ws, config):
    p = make().model_copy(update={"content_hash": None})
    with pytest.raises(ValidationError, match="unsealed"):
        export_prompts(ws, p, config)


def test_export_without_providers_rejected(ws, config):
    p = build_packet(objective="o", created_by="A", target_objects=[{"object_id": "X"}])
    with pytest.raises(ValidationError, match="no assigned providers"):
        export_prompts(ws, p, config)


def test_exported_file_is_lf(ws, config):
    p = make()
    write_packet(ws, p)
    export_prompts(ws, p, config)
    for f in ws.outbox_dir.glob("*.md"):
        assert b"\r\n" not in f.read_bytes()


# -- export records --------------------------------------------------------

def test_export_record_ties_response_to_packet(ws, config):
    p = make()
    write_packet(ws, p)
    export_prompts(ws, p, config)
    records = {r["provider"]: r for r in read_export_records(ws)}
    rec = records["claude"]
    assert rec["packet_ref"] == p.ref
    assert rec["packet_content_hash"] == p.content_hash
    assert rec["version"] == 1
    assert rec["task_id"] == p.task_id
    assert rec["prompt_hash"].startswith("sha256:")
    assert rec["prompt_file"] == export_filename(p, "claude")


def test_export_records_accumulate_across_versions(ws, config):
    from conclave.taskpacket import build_revision
    v1 = make()
    write_packet(ws, v1)
    export_prompts(ws, v1, config, providers=["claude"])
    v2 = build_revision(v1, reason="r", changes={"objective": "second"})
    write_packet(ws, v2)
    export_prompts(ws, v2, config, providers=["claude"])
    refs = {r["packet_ref"] for r in read_export_records(ws)}
    assert refs == {f"{v1.task_id}@v1", f"{v1.task_id}@v2"}


def test_prompt_hash_matches_file(ws, config):
    from conclave.hashing import hash_file
    p = make()
    write_packet(ws, p)
    results = export_prompts(ws, p, config)
    for r in results:
        assert hash_file(r.path) == r.prompt_hash
