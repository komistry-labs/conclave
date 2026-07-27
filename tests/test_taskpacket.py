"""Task Packet identity, hashing, immutability and revision."""

import pytest
import yaml

from conclave.errors import ValidationError, WorkspaceError
from conclave.models import SCHEMA_VERSION, ObjectRef, TaskPacket
from conclave.taskpacket import (
    build_packet,
    build_revision,
    compute_content_hash,
    derive_task_id,
    latest_version,
    list_versions,
    packet_path,
    read_packet,
    seal,
    slugify,
    verify_content_hash,
    write_packet,
)
from conclave.workspace import Workspace


@pytest.fixture
def ws(tmp_path):
    return Workspace.create(tmp_path, principal="Arthur")


def make(objective="Draft RA-001 Part I", targets=("RA-001",), **kw):
    return build_packet(
        objective=objective,
        created_by="Arthur",
        target_objects=[{"object_id": t} for t in targets],
        assigned_providers=[{"provider": "claude", "role": "governance_critic"}],
        **kw,
    )


# -- identity --------------------------------------------------------------

def test_task_id_is_deterministic():
    a = derive_task_id("Draft RA-001 Part I", ["RA-001"])
    b = derive_task_id("Draft RA-001 Part I", ["RA-001"])
    assert a == b


def test_task_id_independent_of_target_order():
    a = derive_task_id("obj", ["RA-001", "RA-002"])
    b = derive_task_id("obj", ["RA-002", "RA-001"])
    assert a == b


def test_task_id_changes_with_objective():
    assert derive_task_id("one", ["X"]) != derive_task_id("two", ["X"])


def test_task_id_changes_with_targets():
    assert derive_task_id("obj", ["X"]) != derive_task_id("obj", ["Y"])


def test_task_id_shape():
    tid = derive_task_id("Draft RA-001 Part I", ["RA-001"])
    assert tid.startswith("TP-")
    assert len(tid.rsplit("-", 1)[1]) == 10


def test_task_id_excludes_timestamp():
    """Two packets built at different moments must share an id."""
    assert make().task_id == make().task_id


def test_slugify_handles_awkward_input():
    assert slugify("  RA-001: Part IV — evidence!  ") == "ra-001-part-iv-evidence"
    assert slugify("!!!") == "task"
    assert len(slugify("x" * 200)) <= 40


def test_invalid_task_id_rejected():
    with pytest.raises(Exception):
        TaskPacket.model_validate(
            {"task_id": "not-valid", "created_at": "2026-01-01T00:00:00Z",
             "created_by": "A", "objective": "o"}
        )


# -- hashing ---------------------------------------------------------------

def test_packet_is_sealed_on_build():
    assert make().content_hash.startswith("sha256:")


def test_content_hash_verifies():
    assert verify_content_hash(make())


def test_content_hash_excludes_itself():
    p = make()
    tampered = p.model_copy(update={"content_hash": "sha256:" + "0" * 64})
    assert compute_content_hash(tampered) == compute_content_hash(p)


def test_tampering_detected():
    p = make()
    tampered = p.model_copy(update={"objective": "something else"})
    assert not verify_content_hash(tampered)


def test_unsealed_packet_fails_verification():
    p = make().model_copy(update={"content_hash": None})
    assert not verify_content_hash(p)


def test_hash_stable_across_field_order():
    """Serialisation sorts keys, so insertion order must not affect the hash."""
    p = make()
    reordered = TaskPacket.model_validate(dict(reversed(list(p.to_serialisable().items()))))
    assert compute_content_hash(reordered) == compute_content_hash(p)


# -- required fields -------------------------------------------------------

def test_all_required_fields_present():
    data = make().to_serialisable()
    for name in ("task_id", "created_at", "objective", "target_objects",
                 "read_only_objects", "prohibited_objects", "assigned_providers",
                 "egress", "content_hash", "schema_version"):
        assert name in data, name


def test_schema_version_recorded():
    assert make().schema_version == SCHEMA_VERSION


# -- unknown fields --------------------------------------------------------

def test_unknown_fields_preserved():
    p = make(extra={"komistry_programme": "KOS-2026", "custom": {"nested": [1, 2]}})
    data = p.to_serialisable()
    assert data["komistry_programme"] == "KOS-2026"
    assert data["custom"] == {"nested": [1, 2]}


def test_unknown_fields_survive_round_trip(ws):
    p = make(extra={"tracking_ref": "ABC-123"})
    write_packet(ws, p)
    assert read_packet(ws, p.task_id, 1).to_serialisable()["tracking_ref"] == "ABC-123"


def test_unknown_fields_included_in_hash():
    a = make()
    b = make(extra={"extra_field": "changes the packet"})
    assert a.content_hash != b.content_hash


def test_unknown_nested_fields_on_object_ref():
    ref = ObjectRef.model_validate({"object_id": "RA-001", "kos_note": "unresolved type"})
    assert ref.model_dump()["kos_note"] == "unresolved type"


# -- scope structures ------------------------------------------------------

def test_scope_keys_shape():
    p = build_packet(
        objective="o", created_by="A",
        target_objects=[{"object_id": "RA-001", "section_id": "RA-001-PART-IV"}],
        read_only_objects=[{"object_id": "ADR-0002"}],
        prohibited_objects=[{"object_id": "KOS-CONSTITUTION"}],
    )
    assert p.scope_keys() == {
        "target": {"RA-001#RA-001-PART-IV"},
        "read_only": {"ADR-0002"},
        "prohibited": {"KOS-CONSTITUTION"},
    }


def test_section_ref_distinct_from_whole_object():
    """Permission to edit a section is not permission to edit the object."""
    whole = ObjectRef(object_id="RA-001")
    section = ObjectRef(object_id="RA-001", section_id="RA-001-PART-IV")
    assert whole.key() != section.key()


def test_object_ref_is_frozen():
    ref = ObjectRef(object_id="RA-001")
    with pytest.raises(Exception):
        ref.object_id = "RA-002"


def test_path_hint_is_optional_and_not_identity():
    a = ObjectRef(object_id="RA-001", path_hint="docs/x.md")
    b = ObjectRef(object_id="RA-001", path_hint="architecture/reasoning/x.md")
    assert a.key() == b.key()


# -- immutability ----------------------------------------------------------

def test_write_then_refuse_overwrite(ws):
    p = make()
    write_packet(ws, p)
    with pytest.raises(WorkspaceError, match="immutable"):
        write_packet(ws, p)


def test_identical_task_cannot_be_created_twice(ws):
    """Deterministic ids plus write-once means re-issuing is caught, not duplicated."""
    write_packet(ws, make())
    with pytest.raises(WorkspaceError, match="immutable"):
        write_packet(ws, make())


def test_unsealed_packet_refused(ws):
    p = make().model_copy(update={"content_hash": None})
    with pytest.raises(ValidationError, match="not sealed"):
        write_packet(ws, p)


def test_revision_creates_new_version(ws):
    v1 = make()
    write_packet(ws, v1)
    v2 = build_revision(v1, reason="scope narrowed", changes={"objective": "narrower"})
    write_packet(ws, v2)
    assert list_versions(ws, v1.task_id) == [1, 2]


def test_revision_leaves_predecessor_untouched(ws):
    v1 = make()
    path1 = write_packet(ws, v1)
    before = path1.read_bytes()
    write_packet(ws, build_revision(v1, reason="r", changes={"objective": "new"}))
    assert path1.read_bytes() == before


def test_revision_inherits_task_id(ws):
    v1 = make()
    v2 = build_revision(v1, reason="r", changes={"objective": "new"})
    assert v2.task_id == v1.task_id
    assert v2.version == 2


def test_revision_records_supersedes(ws):
    v1 = make()
    v2 = build_revision(v1, reason="scope narrowed", changes={"objective": "new"})
    assert v2.supersedes == v1.ref == f"{v1.task_id}@v1"
    assert v2.revision_reason == "scope narrowed"


def test_revision_reseals(ws):
    v1 = make()
    v2 = build_revision(v1, reason="r", changes={"objective": "different"})
    assert verify_content_hash(v2)
    assert v2.content_hash != v1.content_hash


def test_revision_requires_reason():
    with pytest.raises(ValidationError, match="reason"):
        build_revision(make(), reason="   ", changes={"objective": "x"})


@pytest.mark.parametrize("field", ["task_id", "version", "supersedes", "content_hash", "created_at"])
def test_revision_cannot_set_controlled_fields(field):
    with pytest.raises(ValidationError, match="may not set"):
        build_revision(make(), reason="r", changes={field: "forged"})


def test_revision_chain_of_three(ws):
    v1 = make()
    write_packet(ws, v1)
    v2 = build_revision(v1, reason="a", changes={"objective": "second"})
    write_packet(ws, v2)
    v3 = build_revision(v2, reason="b", changes={"objective": "third"})
    write_packet(ws, v3)
    assert list_versions(ws, v1.task_id) == [1, 2, 3]
    assert v3.supersedes == v2.ref
    assert latest_version(ws, v1.task_id) == 3


# -- storage ---------------------------------------------------------------

def test_written_file_is_lf(ws):
    path = write_packet(ws, make())
    assert b"\r\n" not in path.read_bytes()


def test_written_file_is_valid_yaml(ws):
    path = write_packet(ws, make())
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["schema_version"] == SCHEMA_VERSION


def test_round_trip_preserves_hash(ws):
    p = make()
    write_packet(ws, p)
    assert read_packet(ws, p.task_id, 1).content_hash == p.content_hash


def test_read_missing_packet_raises(ws):
    with pytest.raises(WorkspaceError, match="no packet"):
        read_packet(ws, "TP-nothing-0123456789", 1)


def test_latest_version_none_for_unknown(ws):
    assert latest_version(ws, "TP-unknown-0123456789") is None


def test_packet_path_layout(ws):
    p = make()
    assert packet_path(ws, p.task_id, 1) == ws.tasks_dir / p.task_id / "v1.yaml"


# -- defaults --------------------------------------------------------------

def test_egress_defaults_restrictive():
    e = make().egress
    assert e.policy == "relay-only"
    assert "constitutional" in e.prohibited_classifications


def test_providers_cannot_be_given_merge_authority():
    with pytest.raises(Exception):
        build_packet(objective="o", created_by="A",
                     assigned_providers=[{"provider": "claude", "role": "r", "may_merge": True}])


def test_providers_cannot_be_non_advisory():
    with pytest.raises(Exception):
        build_packet(objective="o", created_by="A",
                     assigned_providers=[{"provider": "claude", "role": "r",
                                          "authority_level": "decisive"}])


def test_providers_independent_by_default():
    p = build_packet(objective="o", created_by="A",
                     assigned_providers=[{"provider": "claude", "role": "r"}])
    assert p.assigned_providers[0].independent is True
