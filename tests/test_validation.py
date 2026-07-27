"""Validation: schema vs semantic vs governance, and the no-repair rule."""

import copy

import pytest

from conclave.taskpacket import build_packet, seal
from conclave.validation import (
    Category,
    Severity,
    validate_packet_data,
    validate_schema,
)
from conclave.workspace import Workspace


@pytest.fixture
def config(tmp_path):
    return Workspace.create(tmp_path, principal="Arthur").load_config()


def good(**kw):
    defaults = dict(
        objective="Draft RA-001 Part I",
        created_by="Arthur",
        target_objects=[{"object_id": "RA-001"}],
        read_only_objects=[{"object_id": "ADR-0002"}],
        assigned_providers=[{"provider": "claude", "role": "governance_critic"}],
    )
    defaults.update(kw)
    return build_packet(**defaults).to_serialisable()


def codes(report, category=None):
    return {f.code for f in report.findings if category is None or f.category is category}


# -- baseline --------------------------------------------------------------

def test_valid_packet_passes(config):
    report = validate_packet_data(good(), config)
    assert report.ok, [str(f) for f in report.findings]


# -- schema ----------------------------------------------------------------

@pytest.mark.parametrize("field", [
    "task_id", "created_at", "objective", "target_objects", "read_only_objects",
    "prohibited_objects", "assigned_providers", "egress", "content_hash", "schema_version",
])
def test_missing_required_field_is_schema_error(config, field):
    raw = good()
    del raw[field]
    report = validate_packet_data(raw, config)
    assert "missing-required-field" in codes(report, Category.SCHEMA)
    assert not report.ok


def test_wrong_type_is_schema_error(config):
    raw = good()
    raw["target_objects"] = "not a list"
    report = validate_packet_data(raw, config)
    assert report.by_category(Category.SCHEMA)
    assert not report.ok


def test_malformed_task_id_is_schema_error(config):
    raw = good()
    raw["task_id"] = "TP-bad"
    report = validate_packet_data(raw, config)
    assert not report.ok
    assert report.by_category(Category.SCHEMA)


def test_forbidden_field_rejected(config):
    raw = good()
    raw["approved"] = True
    report = validate_packet_data(raw, config)
    assert "forbidden-field" in codes(report, Category.SCHEMA)


def test_schema_version_mismatch_warns(config):
    raw = good()
    raw["schema_version"] = "task-packet/9.9.9"
    report = validate_packet_data(raw, config)
    assert "schema-version-mismatch" in codes(report)
    assert any(f.severity is Severity.WARNING for f in report.findings)


def test_non_mapping_rejected(config):
    report = validate_packet_data(["not", "a", "mapping"], config)
    assert "not-a-mapping" in codes(report, Category.SCHEMA)


def test_schema_failure_stops_before_semantics(config):
    """No point reporting semantic findings about an object that would not parse."""
    raw = good()
    raw["task_id"] = "invalid"
    report = validate_packet_data(raw, config)
    assert report.by_category(Category.SEMANTIC) == []
    assert report.by_category(Category.GOVERNANCE) == []


# -- semantic --------------------------------------------------------------

def test_unknown_provider_is_semantic(config):
    raw = good(assigned_providers=[{"provider": "mistral", "role": "critic"}])
    report = validate_packet_data(raw, config)
    assert "unknown-provider" in codes(report, Category.SEMANTIC)


def test_no_providers_is_semantic(config):
    raw = good(assigned_providers=[])
    report = validate_packet_data(raw, config)
    assert "no-providers" in codes(report, Category.SEMANTIC)


def test_duplicate_provider_is_semantic(config):
    raw = good(assigned_providers=[
        {"provider": "claude", "role": "critic"},
        {"provider": "claude", "role": "verifier"},
    ])
    report = validate_packet_data(raw, config)
    assert "duplicate-provider" in codes(report, Category.SEMANTIC)


def test_duplicate_object_reference_is_semantic(config):
    raw = good(target_objects=[{"object_id": "RA-001"}, {"object_id": "RA-001"}])
    report = validate_packet_data(raw, config)
    assert "duplicate-object-reference" in codes(report, Category.SEMANTIC)


def test_no_targets_warns(config):
    report = validate_packet_data(good(target_objects=[]), config)
    assert "no-target-objects" in codes(report, Category.SEMANTIC)


def test_tampered_hash_is_semantic(config):
    raw = good()
    raw["objective"] = "quietly changed after sealing"
    report = validate_packet_data(raw, config)
    assert "content-hash-mismatch" in codes(report, Category.SEMANTIC)


def test_v1_cannot_supersede(config):
    raw = good()
    raw["supersedes"] = "TP-other-0123456789@v1"
    report = validate_packet_data(raw, config)
    assert "v1-supersedes" in codes(report, Category.SEMANTIC)


def test_v2_must_supersede(config):
    raw = good()
    raw["version"] = 2
    report = validate_packet_data(raw, config)
    assert "missing-supersedes" in codes(report, Category.SEMANTIC)


# -- governance ------------------------------------------------------------

def test_target_also_prohibited_is_governance(config):
    raw = good(target_objects=[{"object_id": "RA-001"}],
               prohibited_objects=[{"object_id": "RA-001"}])
    report = validate_packet_data(raw, config)
    assert "target-is-prohibited" in codes(report, Category.GOVERNANCE)
    assert report.has_governance_violation


def test_target_also_read_only_is_governance(config):
    raw = good(target_objects=[{"object_id": "RA-001"}],
               read_only_objects=[{"object_id": "RA-001"}])
    report = validate_packet_data(raw, config)
    assert "target-is-read-only" in codes(report, Category.GOVERNANCE)


def test_read_only_also_prohibited_is_governance(config):
    raw = good(read_only_objects=[{"object_id": "X"}],
               prohibited_objects=[{"object_id": "X"}])
    report = validate_packet_data(raw, config)
    assert "read-only-is-prohibited" in codes(report, Category.GOVERNANCE)


def test_section_target_does_not_clash_with_whole_object_prohibition(config):
    """Distinct keys, so no false positive. Deliberate, and worth pinning down."""
    raw = good(target_objects=[{"object_id": "RA-001", "section_id": "RA-001-PART-IV"}],
               prohibited_objects=[{"object_id": "RA-002"}])
    report = validate_packet_data(raw, config)
    assert "target-is-prohibited" not in codes(report, Category.GOVERNANCE)


def test_workspace_permitting_merge_is_governance(config):
    cfg = copy.deepcopy(config)
    cfg["authority"]["agents_may_merge"] = True
    report = validate_packet_data(good(), cfg)
    assert "workspace-permits-merge" in codes(report, Category.GOVERNANCE)


def test_egress_exceeding_workspace_policy_is_governance(config):
    cfg = copy.deepcopy(config)
    cfg["egress"] = {"policy": "relay-only"}
    raw = good(egress={"policy": "all"})
    report = validate_packet_data(raw, cfg)
    assert "egress-exceeds-policy" in codes(report, Category.GOVERNANCE)


def test_egress_within_policy_passes(config):
    cfg = copy.deepcopy(config)
    cfg["egress"] = {"policy": "non-constitutional"}
    report = validate_packet_data(good(egress={"policy": "relay-only"}), cfg)
    assert "egress-exceeds-policy" not in codes(report)


def test_constitutional_egress_permitted_warns(config):
    raw = good(egress={"policy": "non-constitutional", "prohibited_classifications": []})
    report = validate_packet_data(raw, config)
    assert "constitutional-egress-permitted" in codes(report, Category.GOVERNANCE)


def test_multiple_non_independent_providers_warns(config):
    raw = good(assigned_providers=[
        {"provider": "claude", "role": "critic", "independent": False},
        {"provider": "gemini", "role": "verifier", "independent": False},
    ])
    report = validate_packet_data(raw, config)
    assert "no-independent-providers" in codes(report, Category.GOVERNANCE)


def test_semantic_and_governance_reported_separately(config):
    """With no schema error, semantic and governance findings both surface."""
    raw = good(
        assigned_providers=[{"provider": "mistral", "role": "critic"}],   # semantic
        target_objects=[{"object_id": "RA-001"}],
        prohibited_objects=[{"object_id": "RA-001"}],                     # governance
    )
    report = validate_packet_data(raw, config)
    assert "unknown-provider" in codes(report, Category.SEMANTIC)
    assert "target-is-prohibited" in codes(report, Category.GOVERNANCE)


def test_forbidden_field_short_circuits_despite_parsing(config):
    """A forbidden field parses cleanly, because extra fields are preserved.

    It is still a schema error, and must stop validation before semantic and
    governance checks — otherwise a structurally invalid packet generates
    findings about a body that should never have been accepted.
    """
    raw = good(
        assigned_providers=[{"provider": "mistral", "role": "critic"}],   # would be semantic
        target_objects=[{"object_id": "RA-001"}],
        prohibited_objects=[{"object_id": "RA-001"}],                     # would be governance
    )
    raw["approved"] = True
    report = validate_packet_data(raw, config)
    assert "forbidden-field" in codes(report, Category.SCHEMA)
    assert report.by_category(Category.SEMANTIC) == []
    assert report.by_category(Category.GOVERNANCE) == []
    assert report.packet is None


# -- no silent repair ------------------------------------------------------

def test_validation_does_not_mutate_input(config):
    raw = good(target_objects=[{"object_id": "RA-001"}],
               prohibited_objects=[{"object_id": "RA-001"}])
    before = copy.deepcopy(raw)
    validate_packet_data(raw, config)
    assert raw == before


def test_validation_does_not_repair_bad_hash(config):
    raw = good()
    raw["objective"] = "changed"
    original_hash = raw["content_hash"]
    validate_packet_data(raw, config)
    assert raw["content_hash"] == original_hash


def test_validation_does_not_strip_forbidden_field(config):
    raw = good()
    raw["approved"] = True
    validate_packet_data(raw, config)
    assert raw["approved"] is True


def test_validation_does_not_fill_missing_fields(config):
    raw = good()
    del raw["egress"]
    validate_packet_data(raw, config)
    assert "egress" not in raw


def test_schema_validation_returns_none_packet_on_failure():
    report, packet = validate_schema({"nonsense": True})
    assert packet is None
    assert not report.ok
