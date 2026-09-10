"""Focused security tests for the Stage 21B predecessor evidence chain."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError as PydanticValidationError

from conclave.github_foundation import (
    CredentialLeaseEvidence,
    GitHubObservation,
    ObservationPage,
    RecordReference,
    SafeRateLimitProjection,
    _verify_signature,
    prepare_credential_lease,
)
from conclave.github_publication_records import (
    AuthenticatedRateBudgetObservation,
    PUBLICATION_LEASE_CLAIMS_DOMAIN,
    PublicationLeaseClaims,
    PublicationLeaseEvidence,
    Stage21AObservationEvidence,
    _branch_rules_are_exact_for_head,
    _rate_budget_matches_signed_source,
    _rulesets_are_exact,
    _source_credential_authenticates_recursive_tree,
)
from conclave.identity import seal_record
from test_github_foundation import _credential_fixture, _sign_model
from test_github_publication import (
    _stage21a_fixture_context,
    _stage21a_observation_evidence,
)


OBSERVED_AT = "2026-09-09T06:00:07Z"
HEAD_REF = "refs/heads/conclave/01890f3e-7b1a-7cc2-8b4f-8f2e9c90a113/change"


def _rr(reference: str, record) -> RecordReference:
    return RecordReference(reference=reference, content_hash=record.content_hash)


def _page(*, item_count: int = 0) -> ObservationPage:
    body = b"[]" if item_count == 0 else b"[{}]"
    return ObservationPage(
        page=1,
        response_bytes=len(body),
        wire_body_hash="sha256:" + hashlib.sha256(body).hexdigest(),
        item_count=item_count,
        rate_limit=SafeRateLimitProjection(
            resource="core",
            limit=5000,
            remaining=4999,
            retry_after_present=False,
        ),
    )


def _observation(
    fixture: dict,
    lease: CredentialLeaseEvidence,
    *,
    operation_key: str = "ref.get",
    path_parameters: dict | None = None,
    query_parameters: dict | None = None,
    projection: dict | None = None,
    item_count: int = 1,
) -> GitHubObservation:
    intent = fixture["intent"]
    claim = fixture["attempt_claim"]
    return seal_record(
        GitHubObservation,
        {
            "observation_id": "01890f3e-7b1a-7cc2-8b4f-8f2e9c90a121",
            "observation_kind": operation_key,
            "repository_profile": intent.repository_profile,
            "api_profile": intent.api_profile,
            "authorization": intent.authorization,
            "intent": _rr("github/intents/intent.json", intent),
            "attempt_claim": _rr("github/claims/claim.json", claim),
            "lease_evidence": _rr("github/leases/lease.json", lease),
            "repository_id": intent.repository_id,
            "account_id": intent.account_id,
            "app_id": intent.app_id,
            "installation_id": intent.installation_id,
            "operation_key": operation_key,
            "path_parameters": (
                intent.path_parameters if path_parameters is None else path_parameters
            ),
            "query_parameters": (
                intent.query_parameters
                if query_parameters is None
                else query_parameters
            ),
            "attempt_id": intent.attempt_id,
            "observed_at": OBSERVED_AT,
            "status_class": "2xx",
            "pages": (_page(item_count=item_count),),
            "projection": {"ref": "refs/heads/main"}
            if projection is None
            else projection,
            "complete": True,
            "pagination_complete": True,
            "identity_match": True,
            "visibility": "complete_for_endpoint",
            "reason_codes": (),
            "created_at": OBSERVED_AT,
        },
    )


def _evidence(tmp_path: Path) -> Stage21AObservationEvidence:
    fixture = _credential_fixture(evidence_time="2026-09-09T06:00:06Z")
    lease_handle = prepare_credential_lease(
        **{
            key: fixture[key]
            for key in (
                "provider",
                "request",
                "repository_profile",
                "api_profile",
                "provider_key",
                "authorization",
                "intent",
                "attempt_claim",
                "clock",
            )
        },
        attempt_claim_reference="github/claims/claim.json",
        authorization_reference="github/authorizations/auth.json",
        intent_reference="github/intents/intent.json",
        evidence_directory=tmp_path,
    )
    lease = lease_handle.evidence
    lease_handle.close()
    observation = _observation(fixture, lease)
    return Stage21AObservationEvidence(
        repository_profile_record=fixture["repository_profile"],
        api_profile_record=fixture["api_profile"],
        provider_key_reference=RecordReference(
            reference=fixture["repository_profile"].provider_key_reference,
            content_hash=fixture["provider_key"].content_hash,
        ),
        provider_key_record=fixture["provider_key"],
        authorization_record=fixture["authorization"],
        intent_record=fixture["intent"],
        attempt_claim_record=fixture["attempt_claim"],
        lease_evidence_record=lease,
        observation_reference=_rr("github/observations/ref.json", observation),
        observation_record=observation,
    )


def test_stage21a_observation_evidence_accepts_complete_signed_chain(
    tmp_path: Path,
) -> None:
    evidence = _evidence(tmp_path)
    assert evidence.observation_record.operation_key == "ref.get"
    values = evidence.model_dump(mode="python")
    values["unexpected"] = True
    with pytest.raises(PydanticValidationError):
        Stage21AObservationEvidence.model_validate(values)


def test_stage21a_observation_evidence_rejects_forged_claims_signature(
    tmp_path: Path,
) -> None:
    evidence = _evidence(tmp_path)
    lease_values = evidence.lease_evidence_record.model_dump(
        mode="python", exclude={"content_hash"}
    )
    claims = dict(lease_values["provider_claims"])
    claims["signature"] = "A" * 86
    lease_values["provider_claims"] = claims
    claims_bytes = json.dumps(
        claims, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    lease_values["provider_claims_hash"] = (
        "sha256:" + hashlib.sha256(claims_bytes).hexdigest()
    )
    forged_lease = seal_record(CredentialLeaseEvidence, lease_values)
    observation_values = evidence.observation_record.model_dump(
        mode="python", exclude={"content_hash"}
    )
    observation_values["lease_evidence"] = RecordReference(
        reference=observation_values["lease_evidence"]["reference"],
        content_hash=forged_lease.content_hash,
    )
    forged_observation = seal_record(
        GitHubObservation,
        observation_values,
    )
    with pytest.raises(
        PydanticValidationError, match="credential claims signature is invalid"
    ):
        Stage21AObservationEvidence(
            repository_profile_record=evidence.repository_profile_record,
            api_profile_record=evidence.api_profile_record,
            provider_key_reference=evidence.provider_key_reference,
            provider_key_record=evidence.provider_key_record,
            authorization_record=evidence.authorization_record,
            intent_record=evidence.intent_record,
            attempt_claim_record=evidence.attempt_claim_record,
            lease_evidence_record=forged_lease,
            observation_reference=_rr(
                "github/observations/ref.json", forged_observation
            ),
            observation_record=forged_observation,
        )


def test_exact_policy_projection_shapes_reject_legacy_summaries() -> None:
    branch = SimpleNamespace(
        observation_record=SimpleNamespace(
            operation_key="branch_rules.list",
            path_parameters={"branch": HEAD_REF.removeprefix("refs/heads/")},
            query_parameters={"per_page": 100, "page": 1},
            projection={"rules": []},
            pages=(_page(),),
        )
    )
    assert _branch_rules_are_exact_for_head(branch, HEAD_REF)
    branch.observation_record.projection = {
        "head_ref": HEAD_REF,
        "protected": False,
    }
    assert not _branch_rules_are_exact_for_head(branch, HEAD_REF)

    rulesets = SimpleNamespace(
        observation_record=SimpleNamespace(
            operation_key="repository_rulesets.list",
            path_parameters={},
            query_parameters={"includes_parents": True, "per_page": 100, "page": 1},
            projection={"rulesets": []},
            pages=(_page(),),
        )
    )
    assert _rulesets_are_exact(rulesets)
    rulesets.observation_record.projection = {
        "head_ref": HEAD_REF,
        "applicable_rulesets": [],
    }
    assert not _rulesets_are_exact(rulesets)
    rulesets.observation_record.projection = {"rulesets": [{"id": 1}]}
    rulesets.observation_record.pages = (_page(item_count=1),)
    assert not _rulesets_are_exact(rulesets)


def _repository_rate_evidence() -> Stage21AObservationEvidence:
    created = "2026-09-10T00:00:00Z"
    private_key, provider_key, profile, api = _stage21a_fixture_context(created)
    return _stage21a_observation_evidence(
        private_key=private_key,
        provider_key=provider_key,
        profile=profile,
        api=api,
        operation_key="repository.get",
        path_parameters={},
        query_parameters={},
        projection={"repository_id": profile.repository_id},
        item_count=1,
        suffix="rate-security",
        authorization_id="01890f3e-7b1a-7cc2-8b4f-8f2e9c90a141",
        intent_id="01890f3e-7b1a-7cc2-8b4f-8f2e9c90a142",
        observation_id="01890f3e-7b1a-7cc2-8b4f-8f2e9c90a143",
        created=created,
    )


def _authenticated_rate(
    evidence: Stage21AObservationEvidence,
) -> AuthenticatedRateBudgetObservation:
    page_rate = evidence.observation_record.pages[0].rate_limit
    claims = evidence.lease_evidence_record.provider_claims
    return seal_record(
        AuthenticatedRateBudgetObservation,
        {
            "source_observation": evidence.observation_reference,
            "repository_profile": evidence.observation_record.repository_profile,
            "api_profile": evidence.observation_record.api_profile,
            "repository_id": evidence.observation_record.repository_id,
            "account_id": evidence.observation_record.account_id,
            "app_id": evidence.observation_record.app_id,
            "installation_id": evidence.observation_record.installation_id,
            "provider_id": claims.provider_id,
            "provider_version": claims.provider_version,
            "provider_key": evidence.provider_key_reference,
            "provider_public_key_sha256": evidence.provider_key_record.public_key_sha256,
            "api_version": claims.api_version,
            "resource_bucket": page_rate.resource,
            "limit": page_rate.limit,
            "remaining": page_rate.remaining,
            "reset_at": page_rate.reset_at,
            "retry_after_present": page_rate.retry_after_present,
            "observed_at": evidence.observation_record.observed_at,
            "created_at": evidence.observation_record.created_at,
        },
    )


def test_rate_budget_is_exactly_derived_from_signed_stage21a_projection() -> None:
    evidence = _repository_rate_evidence()
    rate = _authenticated_rate(evidence)
    assert _rate_budget_matches_signed_source(rate, evidence)

    values = rate.model_dump(mode="python", exclude={"content_hash"})
    forged = seal_record(
        AuthenticatedRateBudgetObservation,
        {**values, "remaining": rate.remaining + 1},
    )
    assert not _rate_budget_matches_signed_source(forged, evidence)

    with pytest.raises(PydanticValidationError, match="exceeds the observed limit"):
        seal_record(
            AuthenticatedRateBudgetObservation,
            {**values, "remaining": rate.limit + 1},
        )


def test_recursive_tree_credential_must_name_exact_custom_chain() -> None:
    unrelated = _repository_rate_evidence().lease_evidence_record
    auth_hash = "sha256:" + "1" * 64
    intent_hash = "sha256:" + "2" * 64
    claim_hash = "sha256:" + "3" * 64
    authorization = SimpleNamespace(content_hash=auth_hash)
    intent = SimpleNamespace(content_hash=intent_hash)
    claim = SimpleNamespace(content_hash=claim_hash)
    lease = SimpleNamespace(
        authorization=RecordReference(
            reference="tree/auth.json", content_hash=auth_hash
        ),
        intent=RecordReference(reference="tree/intent.json", content_hash=intent_hash),
        claim=RecordReference(reference="tree/claim.json", content_hash=claim_hash),
    )
    assert not _source_credential_authenticates_recursive_tree(
        authorization, intent, claim, lease, unrelated
    )

    exact_credential = SimpleNamespace(
        authorization=lease.authorization,
        intent=lease.intent,
        attempt_claim=lease.claim,
        provider_claims=SimpleNamespace(
            authorization_hash=auth_hash,
            intent_hash=intent_hash,
        ),
    )
    assert _source_credential_authenticates_recursive_tree(
        authorization, intent, claim, lease, exact_credential
    )


def _signed_publication_claims():
    created = "2026-09-10T00:00:00Z"
    private_key, provider_key, profile, api = _stage21a_fixture_context(created)

    def h(digit: str) -> str:
        return "sha256:" + digit * 64

    claims = _sign_model(
        PublicationLeaseClaims,
        {
            "provider_id": provider_key.provider_id,
            "provider_version": "v1",
            "key_id": provider_key.key_id,
            "lease_id": "fixture-publication-lease-1",
            "repository_profile_hash": profile.content_hash,
            "api_profile_hash": api.content_hash,
            "authorization_hash": h("1"),
            "plan_hash": h("2"),
            "operation_intent_hash": h("3"),
            "publication_intent_hash": h("4"),
            "attempt_claim_hash": h("5"),
            "attempt_id": "publication:sha256:" + "6" * 64,
            "rate_observation_hash": h("7"),
            "rate_scope_hash": h("8"),
            "app_id": profile.expected_app_id,
            "installation_id": profile.expected_installation_id,
            "account_id": profile.account_id,
            "repository_ids": (profile.repository_id,),
            "api_version": api.api_version,
            "resource_bucket": "core",
            "maximum_mutation_requests": 5,
            "maximum_total_requests": 16,
            "minted_at": "2026-09-10T00:00:01Z",
            "expires_at": "2026-09-10T00:10:00Z",
            "resolution_nonce_hash": h("9"),
            "provider_authentication_key_id": provider_key.key_id,
        },
        private_key,
        PUBLICATION_LEASE_CLAIMS_DOMAIN,
    )
    return claims, provider_key


def test_publication_fixture_capability_is_provider_signed_and_tamper_evident() -> None:
    claims, provider_key = _signed_publication_claims()
    _verify_signature(
        claims,
        public_key=provider_key,
        domain=PUBLICATION_LEASE_CLAIMS_DOMAIN,
    )
    forged = claims.model_copy(update={"maximum_total_requests": 17})
    with pytest.raises(Exception):
        _verify_signature(
            forged,
            public_key=provider_key,
            domain=PUBLICATION_LEASE_CLAIMS_DOMAIN,
        )


def test_publication_lease_rejects_claim_field_substitution() -> None:
    claims, provider_key = _signed_publication_claims()
    claims_hash = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(
                claims.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
    )

    def ref(name: str, digest: str) -> RecordReference:
        return RecordReference(reference=name, content_hash=digest)

    values = {
        "attempt_claim": ref("publication/claim.json", claims.attempt_claim_hash),
        "authorization": ref("publication/auth.json", claims.authorization_hash),
        "operation_intent": ref(
            "publication/operation-intent.json", claims.operation_intent_hash
        ),
        "publication_intent": ref(
            "publication/intent.json", claims.publication_intent_hash
        ),
        "plan": ref("publication/plan.json", claims.plan_hash),
        "rate_observation": ref("publication/rate.json", claims.rate_observation_hash),
        "provider_key": ref("publication/provider-key.json", provider_key.content_hash),
        "provider_public_key_sha256": provider_key.public_key_sha256,
        "provider_claims": claims,
        "provider_claims_hash": claims_hash,
        "claims_signature_validated_at": "2026-09-10T00:00:02Z",
        "resolution_nonce_hash": claims.resolution_nonce_hash,
        "rate_scope_hash": claims.rate_scope_hash,
        "repository_profile": ref(
            "publication/repository.json", claims.repository_profile_hash
        ),
        "api_profile": ref("publication/api.json", claims.api_profile_hash),
        "repository_id": claims.repository_ids[0],
        "account_id": claims.account_id,
        "app_id": claims.app_id,
        "installation_id": claims.installation_id,
        "provider_id": claims.provider_id,
        "provider_version": claims.provider_version,
        "api_version": claims.api_version,
        "resource_bucket": claims.resource_bucket,
        "ordered_endpoint_plan": tuple("repository.get" for _ in range(16)),
        "maximum_mutation_requests": claims.maximum_mutation_requests,
        "maximum_total_requests": claims.maximum_total_requests,
        "first_rate_check_at": "2026-09-10T00:00:02Z",
        "created_at": "2026-09-10T00:00:02Z",
    }
    seal_record(PublicationLeaseEvidence, values)
    with pytest.raises(
        PydanticValidationError, match="capability claims are not exact"
    ):
        seal_record(PublicationLeaseEvidence, {**values, "provider_id": "substituted"})
