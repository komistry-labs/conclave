"""Increment 19A verification-foundation acceptance and negative tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError

from conclave.errors import IntegrityError, ValidationError
from conclave.identity import (
    ACTOR_BINDING_SCHEMA,
    IDM_BASELINE_COMMIT,
    IDM_BASELINE_SOURCE_SHA256,
    IDM_BASELINE_TREE,
    IDM_BASELINE_WHEEL_SHA256,
    TRUST_INPUT_SCHEMA,
    VERIFICATION_RESULT_SCHEMA,
    ActorIdentityBinding,
    FROZEN_IDM_IMPLEMENTATION,
    IDMImplementationPin,
    IDMVerifierReport,
    IdentityVerificationResult,
    PublicEvidenceReference,
    TrustInputSet,
    VerificationFindings,
    read_record,
    seal_record,
    sha256_bytes,
    verify_actor_identity,
    write_immutable_record,
)

EID = "eid:" + "a" * 26
MID = "mid:" + "b" * 26
VID = "vid:sha256:" + "A" * 43
TDID = "tdid:" + "c" * 26
ARTIFACT = b"public fixture IDM artifact"
TRUST = b'{"public":"fixture trust bundle"}'
REVOCATION = b"signed current public revocation evidence"
TIME_EVIDENCE = b"trusted time evidence"


def _ref(name: str, value: bytes) -> dict[str, str]:
    return {"reference": name, "content_hash": sha256_bytes(value)}


def _trust_data(**changes):
    data = {
        "profile": "idm-trust-input-set",
        "schema_version": TRUST_INPUT_SCHEMA,
        "idm_implementation": FROZEN_IDM_IMPLEMENTATION,
        "trust_bundle": _ref("public/trust.json", TRUST),
        "trust_domain_id": TDID,
        "revocation_evidence": [_ref("public/revocation.cose", REVOCATION)],
        "evaluation_time": "2026-08-16T12:00:00Z",
        "time_source_classification": "trusted",
        "time_evidence": _ref("public/time.json", TIME_EVIDENCE),
        "accepted_roles": ["identity_authority"],
        "required_scopes": ["identity.issue"],
        "created_by": "arthur",
        "created_at": "2026-08-16T12:00:00Z",
    }
    data.update(changes)
    return data


def _trust_inputs(**changes) -> TrustInputSet:
    return seal_record(TrustInputSet, _trust_data(**changes))


def _binding_data(trust_inputs: TrustInputSet, **changes):
    data = {
        "profile": "idm-actor-binding",
        "schema_version": ACTOR_BINDING_SCHEMA,
        "actor_id": "fixture-agent",
        "actor_kind": "advisory_agent",
        "expected_authority_level": "advisory_agent",
        "eid": EID,
        "mid": MID,
        "vid": VID,
        "idm_artifact_hash": sha256_bytes(ARTIFACT),
        "trust_input_reference": "identity/trust-inputs/fixture.json",
        "trust_input_hash": trust_inputs.content_hash,
        "required_identity_role": "identity_authority",
        "required_claim": None,
        "binding_purpose": "fixture verification only",
        "workspace_id": "WS-fixture",
        "task_scope": "TP-fixture",
    }
    data.update(changes)
    return data


def _binding(trust_inputs: TrustInputSet, **changes) -> ActorIdentityBinding:
    return seal_record(ActorIdentityBinding, _binding_data(trust_inputs, **changes))


def _evidence(**changes) -> dict[str, bytes]:
    data = {
        "public/trust.json": TRUST,
        "public/revocation.cose": REVOCATION,
        "public/time.json": TIME_EVIDENCE,
    }
    data.update(changes)
    return data


class FixtureVerifier:
    """Public deterministic test double; it has no key or signing interface."""

    def __init__(self, **changes):
        self.changes = changes

    def verify_identity(self, **_inputs) -> IDMVerifierReport:
        data = {
            "implementation": FROZEN_IDM_IMPLEMENTATION,
            "trusted": True,
            "eid": EID,
            "mid": MID,
            "vid": VID,
            "trust_domain_id": TDID,
            "verified_roles": ["identity_authority"],
            "verified_scopes": ["identity.issue"],
            "findings": VerificationFindings(
                trust=True,
                signature=True,
                lineage=True,
                delegation=True,
                role=True,
                scope=True,
                time=True,
                revocation=True,
                actor_binding=True,
            ),
            "reason_codes": [],
        }
        data.update(self.changes)
        return IDMVerifierReport.model_validate(data)


def _verify(*, trust=None, binding=None, verifier=None, evidence=None, artifact=ARTIFACT):
    trust = trust or _trust_inputs()
    binding = binding or _binding(trust)
    return verify_actor_identity(
        binding_reference="identity/bindings/fixture.json",
        trust_input_reference="identity/trust-inputs/fixture.json",
        binding=binding,
        trust_inputs=trust,
        artifact=artifact,
        public_evidence=evidence or _evidence(),
        verifier=verifier or FixtureVerifier(),
    )


def test_frozen_idm_dependency_pin_is_exact():
    assert IDM_BASELINE_COMMIT == "3769ce3943c87e6a5a72bf94b0efdaa2b11c3bd2"
    assert IDM_BASELINE_TREE == "425f650696a798c10f2a553781fee45e0950dc2a"
    assert IDM_BASELINE_WHEEL_SHA256 == (
        "07120effab0182701e47449e572b94e5a952c210aebfdf217fd965696154d903"
    )
    assert IDM_BASELINE_SOURCE_SHA256 == (
        "98335d16dd0dd7bdfeb27fa77374e741e575cec3bbafc009a66c80374188efb7"
    )
    assert FROZEN_IDM_IMPLEMENTATION.is_frozen_baseline()


def test_machine_readable_dependency_pin_matches_runtime_constants():
    pin_path = Path(__file__).parents[1] / "policies" / "idm-reference-pin.json"
    pin = json.loads(pin_path.read_text(encoding="utf-8"))
    assert pin["commit"] == IDM_BASELINE_COMMIT
    assert pin["tree"] == IDM_BASELINE_TREE
    assert pin["wheel"]["sha256"] == IDM_BASELINE_WHEEL_SHA256
    assert pin["source_archive_sha256"] == IDM_BASELINE_SOURCE_SHA256
    assert pin["provisioning"] == "external-hash-verified"
    assert pin["classification"] == "verification-dependency-pin-not-a-trust-anchor"


def test_invalid_calendar_timestamp_is_refused():
    with pytest.raises(PydanticValidationError, match="calendar"):
        _trust_inputs(evaluation_time="2026-99-99T12:00:00Z")


@pytest.mark.parametrize(
    "record_type,data",
    [
        (TrustInputSet, lambda: _trust_data(unknown=True)),
        (
            ActorIdentityBinding,
            lambda: _binding_data(_trust_inputs(), unknown=True),
        ),
    ],
)
def test_input_schemas_reject_unknown_fields(record_type, data):
    with pytest.raises(PydanticValidationError, match="Extra inputs are not permitted"):
        seal_record(record_type, data())


def test_verification_result_schema_rejects_unknown_fields():
    valid = _verify().model_dump(mode="json")
    valid["unknown"] = True
    with pytest.raises(PydanticValidationError, match="Extra inputs are not permitted"):
        IdentityVerificationResult.model_validate(valid)


def test_record_hash_is_mandatory_and_cannot_be_stale():
    trust = _trust_inputs()
    value = trust.model_dump(mode="json")
    value["created_by"] = "tampered"
    with pytest.raises(PydanticValidationError, match="content_hash"):
        TrustInputSet.model_validate(value)
    with pytest.raises(ValidationError, match="computed"):
        seal_record(TrustInputSet, {**_trust_data(), "content_hash": "sha256:" + "0" * 64})


def test_valid_public_fixture_identity_passes_without_authority_effect():
    result = _verify()
    assert result.status == "PASS"
    assert result.reason_codes == []
    assert result.eid == EID and result.mid == MID and result.vid == VID
    assert result.authority_effect == "none"
    assert result.membership_effect == "none"
    assert result.action_execution_allowed is False


@pytest.mark.parametrize(
    "case,expected",
    [
        ("artifact", "IDM_ARTIFACT_HASH_MISMATCH"),
        ("trust", "TRUST_BUNDLE_HASH_MISMATCH"),
        ("revocation", "REVOCATION_EVIDENCE_HASH_MISMATCH"),
        ("time", "TIME_EVIDENCE_HASH_MISMATCH"),
    ],
)
def test_exact_input_tampering_fails_closed(case, expected):
    kwargs = {}
    if case == "artifact":
        kwargs["artifact"] = ARTIFACT + b"!"
    else:
        evidence = _evidence()
        key = {
            "trust": "public/trust.json",
            "revocation": "public/revocation.cose",
            "time": "public/time.json",
        }[case]
        evidence[key] += b"!"
        kwargs["evidence"] = evidence
    result = _verify(**kwargs)
    assert result.status == "FAIL"
    assert expected in result.reason_codes


@pytest.mark.parametrize(
    "missing,expected",
    [
        ("public/trust.json", "TRUST_BUNDLE_MISSING"),
        ("public/revocation.cose", "REVOCATION_EVIDENCE_MISSING"),
        ("public/time.json", "TIME_EVIDENCE_MISSING"),
    ],
)
def test_missing_authoritative_inputs_fail_closed(missing, expected):
    evidence = _evidence()
    del evidence[missing]
    result = _verify(evidence=evidence)
    assert result.status == "FAIL"
    assert expected in result.reason_codes


def test_rehearsal_local_time_cannot_pass():
    trust = _trust_inputs(time_source_classification="rehearsal-local-time")
    result = _verify(trust=trust, binding=_binding(trust))
    assert result.status == "FAIL"
    assert "UNTRUSTED_TIME" in result.reason_codes


def test_unpinned_trust_input_and_verifier_builds_fail():
    wrong_pin = IDMImplementationPin(
        commit="0" * 40,
        tree=IDM_BASELINE_TREE,
        wheel_sha256=IDM_BASELINE_WHEEL_SHA256,
        source_archive_sha256=IDM_BASELINE_SOURCE_SHA256,
    )
    trust = _trust_inputs(idm_implementation=wrong_pin)
    result = _verify(trust=trust, binding=_binding(trust))
    assert "IDM_BASELINE_MISMATCH" in result.reason_codes

    report_result = _verify(verifier=FixtureVerifier(implementation=wrong_pin))
    assert "IDM_VERIFIER_BASELINE_MISMATCH" in report_result.reason_codes


@pytest.mark.parametrize(
    "change,expected",
    [
        ({"eid": "eid:" + "d" * 26}, "EID_MISMATCH"),
        ({"mid": "mid:" + "e" * 26}, "MID_MISMATCH"),
        ({"vid": "vid:sha256:" + "B" * 43}, "VID_MISMATCH"),
        ({"trust_domain_id": "tdid:" + "f" * 26}, "TRUST_DOMAIN_MISMATCH"),
        ({"verified_roles": ["unrelated"]}, "ROLE_MISSING"),
        ({"verified_scopes": ["manifest.revise"]}, "SCOPE_MISSING"),
    ],
)
def test_identity_domain_role_and_scope_substitution_fails(change, expected):
    result = _verify(verifier=FixtureVerifier(**change))
    assert result.status == "FAIL"
    assert expected in result.reason_codes


@pytest.mark.parametrize("failed_finding", VerificationFindings.model_fields)
def test_every_required_verification_finding_fails_closed(failed_finding):
    findings = {name: True for name in VerificationFindings.model_fields}
    findings[failed_finding] = False
    result = _verify(verifier=FixtureVerifier(findings=VerificationFindings(**findings)))
    assert result.status == "FAIL"
    expected = {
        "trust": "TRUST_INVALID",
        "signature": "SIGNATURE_INVALID",
        "lineage": "LINEAGE_INVALID",
        "delegation": "DELEGATION_INVALID",
        "role": "ROLE_INVALID",
        "scope": "SCOPE_INVALID",
        "time": "TIME_INVALID",
        "revocation": "REVOCATION_INVALID",
        "actor_binding": "ACTOR_BINDING_INVALID",
    }[failed_finding]
    assert expected in result.reason_codes


def test_trust_input_reference_is_cross_bound():
    trust = _trust_inputs()
    binding = _binding(trust, trust_input_reference="identity/trust-inputs/other.json")
    result = _verify(binding=binding, trust=trust)
    assert result.status == "FAIL"
    assert "TRUST_INPUT_REFERENCE_MISMATCH" in result.reason_codes


def test_verifier_exception_is_sanitized_and_deterministic():
    class ExplodingVerifier:
        def verify_identity(self, **_inputs):
            raise RuntimeError("secret at C:/authority/keys/root.idmk")

    first = _verify(verifier=ExplodingVerifier())
    second = _verify(verifier=ExplodingVerifier())
    assert first.status == "FAIL"
    assert first.reason_codes == ["IDM_VERIFIER_ERROR"]
    assert first == second
    assert "root.idmk" not in json.dumps(first.model_dump(mode="json"))


def test_binding_cannot_raise_or_mislabel_authority():
    trust = _trust_inputs()
    with pytest.raises(PydanticValidationError, match="authority ceiling"):
        _binding(trust, actor_kind="advisory_agent", expected_authority_level="human_principal")


@pytest.mark.parametrize(
    "reference",
    [
        "E:/offline-root/root.idmk",
        "authority/keys/issuance.idmk",
        "vault/private-key.json",
        "evidence/passphrase.txt",
        "evidence/operator.pem",
        "evidence/secrets/operator.txt",
    ],
)
def test_private_material_references_are_refused(reference):
    with pytest.raises(PydanticValidationError, match="private material"):
        PublicEvidenceReference(reference=reference, content_hash=sha256_bytes(b"x"))


def test_verification_is_content_idempotent_and_time_bound():
    first = _verify()
    second = _verify()
    assert first.content_hash == second.content_hash

    later_trust = _trust_inputs(
        evaluation_time="2026-08-16T12:00:01Z",
        created_at="2026-08-16T12:00:01Z",
    )
    later = _verify(trust=later_trust, binding=_binding(later_trust))
    assert later.status == "PASS"
    assert later.content_hash != first.content_hash


def test_record_hash_does_not_depend_on_mapping_insertion_order():
    data = _trust_data()
    reversed_data = dict(reversed(list(data.items())))
    assert seal_record(TrustInputSet, data) == seal_record(TrustInputSet, reversed_data)


def test_immutable_storage_is_idempotent_and_conflicts_are_preserved(tmp_path):
    path = tmp_path / ".conclave" / "identity" / "trust-inputs" / "fixture.json"
    first = _trust_inputs()
    assert write_immutable_record(path, first) == (path, True)
    assert write_immutable_record(path, first) == (path, False)
    assert read_record(path, TrustInputSet) == first

    other = _trust_inputs(created_by="different")
    with pytest.raises(IntegrityError, match="overwrite"):
        write_immutable_record(path, other)


def test_read_record_refuses_oversize_and_malformed_input(tmp_path):
    path = tmp_path / "record.json"
    path.write_bytes(b"x" * (1024 * 1024 + 1))
    with pytest.raises(ValidationError, match="1 MiB"):
        read_record(path, TrustInputSet)
    path.write_text("not-json", encoding="utf-8")
    with pytest.raises(ValidationError, match="invalid identity record"):
        read_record(path, TrustInputSet)
