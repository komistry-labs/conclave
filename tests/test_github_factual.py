"""Stage 21C factual PR assistant — fixture-only acceptance tests.

Each test cites the clause of the adopted profile
(INCREMENT-21C-FACTUAL-PR-ASSISTANT-PROTOCOL.md, sha256 ed45fb9f…) it proves.
Stage 21A results are injected directly as result shapes, as profile §8 permits;
no transport, credential or network is used.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError as PydanticValidationError

from conclave.github_factual import (
    LIMITATIONS,
    MAXIMUM_TRANSMISSIONS,
    PROTOCOL_SHA256,
    SLOTS,
    FactualCollectionError,
    FactualReport,
    FactualRequest,
    SlotBinding,
    collect_factual_report,
    expected_parameters,
    is_tolerated,
    merge_state,
    persist_factual_report,
    record_result,
)
from conclave.github_foundation import (
    API_PROFILE_SCHEMA,
    FACTUAL_API_PROFILE_SCHEMA,
    FACTUAL_RESPONSE_PROJECTION_VERSION,
    RESPONSE_PROJECTION_VERSION,
    GitHubApiProfile,
    GitHubFactualApiProfile,
    GitHubFoundationFailure,
    GitHubObservation,
    GitHubOperationAttemptClaim,
    GitHubOperationAuthorization,
    GitHubOperationIntent,
    GitHubRepositoryProfile,
    ObservationPage,
    PermissionEnvelope,
    RecordReference,
    SafeRateLimitProjection,
    attempt_claim_path,
    compute_attempt_id,
    project_github_json,
)
from conclave.github_operation import GitHubReadResult
from conclave.identity import seal_record, sha256_bytes

NOW = "2026-09-23T06:00:00Z"
LATER = "2026-09-23T06:10:00Z"
H9 = "sha256:" + "9" * 64
BASE = "a" * 40
HEAD = "b" * 40
MERGE = "c" * 40
OTHER = "d" * 40
HUMAN = 5150
CONSTANTS = {
    "created_at": NOW,
    "authority_effect": "none",
    "decision_effect": "none",
    "membership_effect": "none",
    "production_use_allowed": False,
}


def _uuid7(n: int) -> str:
    return f"01890f3e-7b1a-7cc2-8b4f-8f2e9c90{n:04x}"


def _permissions(**changes: str) -> PermissionEnvelope:
    values = dict.fromkeys(
        ("contents", "pull_requests", "checks", "statuses", "administration"), "read"
    )
    values["metadata"] = "read"
    values.update(changes)
    return PermissionEnvelope.model_validate(values)


def _repository_profile() -> GitHubRepositoryProfile:
    return seal_record(
        GitHubRepositoryProfile,
        {
            "profile": "github-repository-profile",
            "schema_version": "github-repository-profile/0.1.0",
            "repository_profile_id": "komistry-conclave",
            "host": "github.com",
            "api_origin": "https://api.github.com",
            "owner": "komistry-labs",
            "repository": "conclave",
            "repository_id": 101,
            "repository_node_id": "R_fixture",
            "account_id": 202,
            "git_object_format": "sha1",
            "default_branch": "main",
            "allowed_base_refs": ("refs/heads/main",),
            "credential_provider_selector": "fixture-provider",
            "expected_provider_id": "fixture-provider",
            "expected_provider_versions": ("v1",),
            "provider_key_reference": "github/provider-keys/key.json",
            "provider_key_hash": H9,
            "expected_provider_key_id": "fixture-key",
            "expected_provider_public_key_sha256": sha256_bytes(bytes(range(32))),
            "expected_app_id": 303,
            "expected_installation_id": 404,
            "repository_selection": "selected",
            "permission_ceiling": _permissions(),
            "read_operations": tuple(sorted({s.operation_key for s in SLOTS})),
            "live_use_allowed": False,
            **CONSTANTS,
        },
    )


def _factual_api_profile() -> GitHubFactualApiProfile:
    return seal_record(
        GitHubFactualApiProfile,
        {
            "profile": "github-factual-api-profile",
            "schema_version": FACTUAL_API_PROFILE_SCHEMA,
            **CONSTANTS,
        },
    )


REPO = _repository_profile()
API = _factual_api_profile()
REPO_REF = RecordReference(reference="github/repository-profiles/repo.json", content_hash=REPO.content_hash)
API_REF = RecordReference(reference="github/api-profiles/factual.json", content_hash=API.content_hash)


def _request(**changes: Any) -> FactualRequest:
    values = {
        "profile": "github-factual-request",
        "schema_version": "github-factual-request/0.1.0",
        "protocol_sha256": PROTOCOL_SHA256,
        "repository_profile": REPO_REF,
        "api_profile": API_REF,
        "mode": "fixture",
        "repository_id": 101,
        "pull_number": 26,
        "base_ref": "refs/heads/main",
        "head_ref": "refs/heads/feature",
        "expected_base_sha": BASE,
        "expected_head_sha": HEAD,
        "expected_human_id": HUMAN,
        "prior_report": None,
        "expected_merge_sha": None,
        "purpose": "initial",
        "merge_authorized": False,
        "action_execution_allowed": False,
        **CONSTANTS,
    }
    values.update(changes)
    return seal_record(FactualRequest, values)


def _ref(record, name: str) -> RecordReference:
    return RecordReference(reference=f"github/{name}.json", content_hash=record.content_hash)


def _binding(slot_index: int, request: FactualRequest, *, auth_id: int | None = None) -> SlotBinding:
    slot = SLOTS[slot_index]
    path, query = expected_parameters(slot, request)
    requests = slot.maximum_pages + 1
    authorization = seal_record(
        GitHubOperationAuthorization,
        {
            "profile": "github-operation-authorization",
            "schema_version": "github-operation-authorization/0.1.0",
            "authorization_id": _uuid7(0x100 + (slot_index if auth_id is None else auth_id)),
            "repository_profile": REPO_REF,
            "api_profile": API_REF,
            "repository_id": 101,
            "account_id": 202,
            "stage": "21A",
            "operation_mode": "read_only",
            "operation_key": slot.operation_key,
            "path_parameters": path,
            "query_parameters": query,
            "purpose": f"Stage 21C factual slot {slot.name}",
            "authorized_principal": "arthur",
            "issued_at": NOW,
            "expires_at": LATER,
            "maximum_logical_operations": 1,
            "maximum_network_requests": requests,
            **{**CONSTANTS, "authority_effect": "github_read_only"},
        },
    )
    attempt = compute_attempt_id(
        authorization_hash=authorization.content_hash,
        repository_profile_hash=REPO.content_hash,
        api_profile_hash=API.content_hash,
        operation_key=slot.operation_key,
        path_parameters=path,
        query_parameters=query,
        maximum_response_body_bytes_per_page=2_097_152,
        maximum_total_response_body_bytes=8_388_608,
        maximum_pages=slot.maximum_pages,
        maximum_items=1000 if slot.maximum_pages > 1 else 1,
        operation_timeout_seconds=60,
        maximum_retry_transmissions_per_operation=1,
        maximum_network_requests=requests,
    )
    intent = seal_record(
        GitHubOperationIntent,
        {
            "profile": "github-operation-intent",
            "schema_version": "github-operation-intent/0.1.0",
            "intent_id": _uuid7(0x200 + slot_index),
            "authorization": _ref(authorization, f"authorizations/{slot.name}"),
            "repository_profile": REPO_REF,
            "api_profile": API_REF,
            "repository_id": 101,
            "account_id": 202,
            "app_id": 303,
            "installation_id": 404,
            "stage": "21A",
            "http_method": "GET",
            "operation_key": slot.operation_key,
            "path_parameters": path,
            "query_parameters": query,
            "request_body_hash": None,
            "request_body_bytes": 0,
            "maximum_response_body_bytes_per_page": 2_097_152,
            "maximum_total_response_body_bytes": 8_388_608,
            "maximum_pages": slot.maximum_pages,
            "maximum_items": 1000 if slot.maximum_pages > 1 else 1,
            "operation_timeout_seconds": 60,
            "maximum_retry_transmissions_per_operation": 1,
            "maximum_network_requests": requests,
            "attempt_id": attempt,
            "not_after": LATER,
            "maximum_credential_resolutions": 1,
            **CONSTANTS,
        },
    )
    claim = seal_record(
        GitHubOperationAttemptClaim,
        {
            "profile": "github-operation-attempt-claim",
            "schema_version": "github-operation-attempt-claim/0.1.0",
            "attempt_id": attempt,
            "authorization": intent.authorization,
            "intent": _ref(intent, f"intents/{slot.name}"),
            "repository_profile": REPO_REF,
            "api_profile": API_REF,
            "repository_id": 101,
            "account_id": 202,
            "app_id": 303,
            "installation_id": 404,
            "operation_key": slot.operation_key,
            "claim_time": NOW,
            "intent_expiry": LATER,
            "state": "claimed",
            **CONSTANTS,
        },
    )
    return SlotBinding(authorization=authorization, intent=intent, attempt_claim=claim)


def _bindings(request: FactualRequest, **overrides: SlotBinding) -> dict[str, SlotBinding]:
    result = {}
    for index, slot in enumerate(SLOTS):
        if request.purpose == "initial" and slot.name in {"merge_commit", "merge_checks", "merge_status"}:
            continue
        result[slot.name] = overrides.get(slot.name) or _binding(index, request)
    return result


def _page(*, remaining: int | None = 4000, retry_after: bool = False) -> ObservationPage:
    return ObservationPage(
        page=1,
        response_bytes=10,
        wire_body_hash=H9,
        item_count=1,
        rate_limit=SafeRateLimitProjection(
            resource="core", limit=5000, remaining=remaining, reset_at=None,
            retry_after_present=retry_after,
        ),
    )


_OBS_COUNTER = [0x400]


def _observation(
    binding: SlotBinding,
    *,
    projection: dict[str, Any] | None = None,
    complete: bool = True,
    status_class: str = "2xx",
    reasons: tuple[str, ...] = (),
    pages: tuple[ObservationPage, ...] | None = None,
    identity_match: bool | None = None,
    path_parameters: dict[str, Any] | None = None,
    repository_id: int = 101,
) -> GitHubObservation:
    _OBS_COUNTER[0] += 1
    intent = binding.intent
    return seal_record(
        GitHubObservation,
        {
            "profile": "github-observation",
            "schema_version": "github-observation/0.1.0",
            "observation_id": _uuid7(_OBS_COUNTER[0]),
            "observation_kind": "fixture" if complete else "failure",
            "repository_profile": REPO_REF,
            "api_profile": API_REF,
            "authorization": intent.authorization,
            "intent": binding.attempt_claim.intent,
            "attempt_claim": _ref(binding.attempt_claim, "attempt-claims/claim"),
            "lease_evidence": RecordReference(reference="github/lease-evidence/lease.json", content_hash=H9),
            "repository_id": repository_id,
            "account_id": 202,
            "app_id": 303,
            "installation_id": 404,
            "operation_key": intent.operation_key,
            "path_parameters": path_parameters if path_parameters is not None else dict(intent.path_parameters),
            "query_parameters": dict(intent.query_parameters),
            "attempt_id": intent.attempt_id,
            "observed_at": NOW,
            "status_class": status_class,
            "pages": pages if pages is not None else (_page(),),
            "response_projection_version": FACTUAL_RESPONSE_PROJECTION_VERSION,
            "projection": projection or {"visibility": "complete_for_endpoint"},
            "complete": complete,
            "pagination_complete": complete,
            "identity_match": complete if identity_match is None else identity_match,
            "visibility": "complete_for_endpoint" if complete else "not_observed",
            "reason_codes": reasons,
            "merge_authorized": False,
            "action_execution_allowed": False,
            **CONSTANTS,
        },
    )


def _pr(*, state="open", merged=False, merged_at=None, merged_by=None, merge_sha=None,
        head_sha=HEAD, head_ref="feature", base_ref="main") -> dict[str, Any]:
    return {
        "state": state, "merged": merged, "merged_at": merged_at, "merged_by": merged_by,
        "merge_commit_sha": merge_sha,
        "head": {"sha": head_sha, "ref": head_ref, "repository_id": 101},
        "base": {"sha": BASE, "ref": base_ref, "repository_id": 101},
    }


MERGED_PR = _pr(state="closed", merged=True, merged_at=NOW,
                merged_by={"id": HUMAN, "type": "User"}, merge_sha=MERGE)


def _default_projection(slot: str, request: FactualRequest) -> dict[str, Any]:
    return {
        "repository": {"repository_id": 101, "account_id": 202},
        "repository_after": {"repository_id": 101, "account_id": 202},
        "object_format": {"hash_algorithm": "sha1"},
        "object_format_after": {"hash_algorithm": "sha1"},
        "base_ref": {"requested_ref": "refs/heads/main", "returned_ref": "refs/heads/main", "object_sha": BASE},
        "pr_before": _pr(),
        "pr_after": _pr(),
        "merge_commit": {"sha": request.expected_merge_sha, "parents": [{"sha": BASE}, {"sha": HEAD}]},
    }.get(slot, {"visibility": "complete_for_endpoint"})


class Scripted:
    """Injected executor: per-slot overrides, otherwise a complete observation."""

    def __init__(self, request: FactualRequest, **per_slot):
        self.request = request
        self.per_slot = per_slot
        self.calls: list[str] = []

    def __call__(self, slot: str, binding: SlotBinding) -> GitHubReadResult:
        self.calls.append(slot)
        spec = self.per_slot.get(slot)
        if callable(spec):
            return spec(binding)
        if isinstance(spec, dict):
            return GitHubReadResult(_observation(binding, **spec), None, False, None)
        return GitHubReadResult(
            _observation(binding, projection=_default_projection(slot, self.request)),
            None, False, None,
        )


def _diagnostic(code: str):
    return lambda binding: GitHubReadResult(None, None, False, {"operation_key": binding.intent.operation_key, "reason_code": code})


def _clock():
    return NOW


def _run(tmp_path: Path, request: FactualRequest, executor, *, bindings=None, prior=None, prior_request=None):
    return collect_factual_report(
        request=request,
        request_reference=RecordReference(reference="github/factual-requests/req.json", content_hash=request.content_hash),
        repository_profile=REPO,
        api_profile=API,
        bindings=bindings if bindings is not None else _bindings(request),
        executor=executor,
        attempt_claims_dir=tmp_path / "claims",
        clock=_clock,
        prior_report=prior,
        prior_request=prior_request,
    )


def _steps(report: FactualReport) -> dict[str, str]:
    return {step.slot: step.disposition for step in report.steps}


def _coverage(report: FactualReport) -> dict[str, str]:
    return {section.kind: section.coverage for section in report.sections}


def _post_action(tmp_path: Path, **per_slot):
    initial_request = _request()
    initial = _run(tmp_path, initial_request, Scripted(initial_request, pr_after={"projection": MERGED_PR}))
    request = _request(
        purpose="post_action",
        prior_report=RecordReference(reference="github/factual-reports/initial.json", content_hash=initial.content_hash),
        expected_merge_sha=MERGE,
    )
    report = _run(tmp_path, request, Scripted(request, **per_slot), prior=initial, prior_request=initial_request)
    return request, report


# --------------------------------------------------------------------------- plan


def test_plan_and_budget_are_the_adopted_table() -> None:  # §4.1, §6
    assert [s.name for s in SLOTS][-2:] == ["repository_after", "object_format_after"]
    assert len(SLOTS) == 16
    assert sum(s.maximum_pages for s in SLOTS) == 79
    assert MAXIMUM_TRANSMISSIONS == 95 == 7 * 11 + 9 * 2
    assert LIMITATIONS == tuple(sorted(LIMITATIONS)) and len(LIMITATIONS) == 11


# ------------------------------------------------------------------ records (§3)


def test_request_rejects_non_branch_refs() -> None:  # §3 R5-3
    for ref in ("refs/tags/x", "main", "refs/heads/", "refs/heads/a/../b", "refs/heads/a%2f"):
        with pytest.raises(PydanticValidationError):
            _request(head_ref=ref)


def test_request_purpose_fields_are_consistent() -> None:  # §3
    with pytest.raises(PydanticValidationError):
        _request(purpose="post_action")
    with pytest.raises(PydanticValidationError):
        _request(expected_merge_sha=MERGE)


def test_old_api_profile_validator_rejects_factual_profile() -> None:  # §5, rule 4(a)
    data = API.model_dump(mode="json")
    with pytest.raises(PydanticValidationError):
        GitHubApiProfile.model_validate(data)
    assert API.response_projection_version == FACTUAL_RESPONSE_PROJECTION_VERSION
    assert API_PROFILE_SCHEMA != FACTUAL_API_PROFILE_SCHEMA


def _raw_pr(**changes: Any) -> dict[str, Any]:
    raw = {
        "id": 1, "number": 26, "state": "open", "draft": False, "merged": False,
        "mergeable": True, "mergeable_state": "clean",
        "user": {"id": 7, "type": "User", "login": "someone"},
        "head": {"sha": HEAD, "ref": "feature", "repo": {"id": 101}},
        "base": {"sha": BASE, "ref": "main", "repo": {"id": 101}},
        "created_at": NOW, "updated_at": NOW, "closed_at": None, "merged_at": None,
        "merge_commit_sha": None, "merged_by": None,
    }
    raw.update(changes)
    return raw


def test_factual_pr_projection_adds_two_nullable_fields(tmp_path: Path) -> None:  # §5, rule 4(c)-(d)
    request = _request()
    intent = _binding(3, request).intent
    factual = project_github_json(operation_key="pull_request.get", value=_raw_pr(),
                                  repository=REPO, intent=intent,
                                  projection_version=FACTUAL_RESPONSE_PROJECTION_VERSION)
    assert factual.normalized["merge_commit_sha"] is None
    assert factual.normalized["merged_by"] is None
    assert factual.complete and factual.identity_match  # null does not clear either
    merged = project_github_json(
        operation_key="pull_request.get",
        value=_raw_pr(merged_by={"id": HUMAN, "type": "User", "login": "x", "email": "e"}, merge_commit_sha=MERGE),
        repository=REPO, intent=intent, projection_version=FACTUAL_RESPONSE_PROJECTION_VERSION)
    assert merged.normalized["merged_by"] == {"id": HUMAN, "type": "User"}  # login/email discarded
    legacy = project_github_json(operation_key="pull_request.get", value=_raw_pr(),
                                 repository=REPO, intent=intent)
    assert "merge_commit_sha" not in legacy.normalized and "merged_by" not in legacy.normalized
    for missing in ("merge_commit_sha", "merged_by"):
        raw = _raw_pr()
        del raw[missing]
        with pytest.raises(GitHubFoundationFailure):
            project_github_json(operation_key="pull_request.get", value=raw, repository=REPO,
                                intent=intent, projection_version=FACTUAL_RESPONSE_PROJECTION_VERSION)
    assert RESPONSE_PROJECTION_VERSION != FACTUAL_RESPONSE_PROJECTION_VERSION


# ----------------------------------------------------------------- §4.3 recording


def test_recording_table_maps_every_result_shape() -> None:
    binding = _binding(0, _request())
    assert record_result(GitHubReadResult(_observation(binding), None, False, None))[0] == "OBSERVED"
    failed = _observation(binding, complete=False, status_class="transport", reasons=("TRANSPORT_TIMEOUT",))
    assert record_result(GitHubReadResult(failed, None, False, None))[0] == "FAILED"
    assert record_result(_diagnostic("LEASE_MISSING")(binding)) == ("NO_OBSERVATION", None, "LEASE_MISSING")
    for code in ("ATTEMPT_CLAIM_STORE_FAILED", "LEASE_EVIDENCE_STORE_FAILED", "OBSERVATION_STORE_FAILED"):
        with pytest.raises(FactualCollectionError) as error:
            record_result(_diagnostic(code)(binding))
        assert error.value.code == "STORE_FAILURE"
    for shape in (GitHubReadResult(None, None, False, None),
                  GitHubReadResult(None, None, False, {"reason_code": "NOT_A_CODE"})):
        with pytest.raises(FactualCollectionError) as error:
            record_result(shape)
        assert error.value.code == "RESULT_INVALID"


# ----------------------------------------------------------------- §4.4 tolerance


def test_tolerance_requires_all_four_conditions() -> None:
    binding = _binding(7, _request())

    def failed(**kw):
        values = {"complete": False, "status_class": "4xx", "reasons": ("HTTP_RESPONSE_REJECTED",)}
        values.update(kw)
        return _observation(binding, **values)

    assert is_tolerated("protection", failed())
    assert not is_tolerated("reviews", failed())
    assert not is_tolerated("protection", failed(status_class="5xx"))
    assert not is_tolerated("protection", failed(status_class="transport"))
    assert not is_tolerated("protection", failed(reasons=("RATE_LIMITED",)))
    assert not is_tolerated("protection", failed(reasons=("CREDENTIAL_CLEANUP_FAILED", "HTTP_RESPONSE_REJECTED")))
    assert not is_tolerated("protection", failed(pages=(_page(retry_after=True),)))
    assert not is_tolerated("protection", failed(pages=(_page(remaining=0),)))
    assert not is_tolerated("protection", failed(pages=(_page(remaining=None),)))
    assert not is_tolerated("protection", failed(pages=()))


# ---------------------------------------------------------------- §5.1 Merge.state


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({}, "OPEN"),
        ({"state": "closed"}, "CLOSED_UNMERGED"),
        ({"state": "closed", "merged": True, "merged_at": NOW}, "MERGED"),
        ({"state": "closed", "merged": True, "merged_at": NOW, "merged_by": {"id": 1, "type": "User"}}, "MERGED"),
        ({"state": "closed", "merged": True, "merged_at": None}, "UNKNOWN"),
        ({"state": "closed", "merged_by": {"id": 1, "type": "User"}}, "UNKNOWN"),
        ({"state": "open", "merged": True, "merged_at": NOW}, "UNKNOWN"),
        ({"merge_sha": MERGE}, "OPEN"),  # test-merge SHA never changes state
    ],
)
def test_merge_state_table(changes: dict, expected: str) -> None:
    assert merge_state(_pr(**changes)) == expected


# ------------------------------------------------------------ coordinator (§4-§5)


def test_initial_report_all_observed(tmp_path: Path) -> None:
    request = _request()
    executor = Scripted(request)
    report = _run(tmp_path, request, executor)
    steps = _steps(report)
    assert report.stop_reason == "NONE" and report.stop_slot is None
    assert report.target == "SAME"
    assert [steps[s] for s in ("merge_commit", "merge_checks", "merge_status")] == ["NOT_APPLICABLE"] * 3
    assert "merge_commit" not in executor.calls and executor.calls[-2:] == ["repository_after", "object_format_after"]
    assert _coverage(report) == {"CHECKS": "COMPLETE_WITHIN_ENDPOINT", "POST_MERGE_CHECKS": "NOT_REQUESTED",
                                 "PROTECTIONS": "COMPLETE_WITHIN_ENDPOINT", "REVIEWS": "COMPLETE_WITHIN_ENDPOINT",
                                 "TARGET": "COMPLETE_WITHIN_ENDPOINT"}
    assert report.merge.state == "OPEN" and report.merge.merge_sha is None
    assert len(report.observations) == 13
    assert report.limitations == LIMITATIONS
    assert report.merge_authorized is False and report.action_execution_allowed is False


def test_initial_merged_report_keeps_facts_but_no_comparisons(tmp_path: Path) -> None:  # R4-5
    request = _request()
    report = _run(tmp_path, request, Scripted(request, pr_after={"projection": MERGED_PR}))
    assert report.merge.state == "MERGED" and report.merge.merge_sha == MERGE and report.merge.actor_id == HUMAN
    assert report.merge.parents_comparison == "UNKNOWN" and report.merge.actor_comparison == "UNKNOWN"
    assert report.merge.commit_source is None


def test_post_action_happy_path(tmp_path: Path) -> None:
    _request_, report = _post_action(tmp_path, pr_after={"projection": MERGED_PR})
    steps = _steps(report)
    assert [steps[s] for s in ("merge_commit", "merge_checks", "merge_status")] == ["OBSERVED"] * 3
    assert _coverage(report)["POST_MERGE_CHECKS"] == "COMPLETE_WITHIN_ENDPOINT"  # branch 3
    assert report.merge.parents_comparison == "MATCH"
    assert report.merge.actor_comparison == "SAME_ACCOUNT"
    assert report.merge.commit_source is not None
    assert report.target == "SAME"


def test_post_action_base_advanced_by_merge_is_still_same(tmp_path: Path) -> None:  # R4-4
    advanced = {"requested_ref": "refs/heads/main", "returned_ref": "refs/heads/main", "object_sha": MERGE}
    _r, report = _post_action(tmp_path, pr_after={"projection": MERGED_PR}, base_ref={"projection": advanced})
    assert report.target == "SAME"


def test_post_action_null_linkage_skips_conditionals_and_keeps_closing_pair(tmp_path: Path) -> None:
    _r, report = _post_action(tmp_path, pr_after={"projection": _pr()})
    steps = _steps(report)
    assert [steps[s] for s in ("merge_commit", "merge_checks", "merge_status")] == ["NOT_APPLICABLE"] * 3
    assert report.stop_reason == "LINKAGE_CHANGED" and report.stop_slot == "pr_after"
    assert steps["repository_after"] == steps["object_format_after"] == "OBSERVED"
    assert _coverage(report)["POST_MERGE_CHECKS"] == "UNAVAILABLE"  # branch 2


def test_post_action_differing_linkage_is_not_attempted(tmp_path: Path) -> None:
    other = dict(MERGED_PR, merge_commit_sha=OTHER)
    _r, report = _post_action(tmp_path, pr_after={"projection": other})
    steps = _steps(report)
    assert [steps[s] for s in ("merge_commit", "merge_checks", "merge_status")] == ["NOT_ATTEMPTED"] * 3
    assert report.stop_reason == "LINKAGE_CHANGED" and report.merge.merge_sha == OTHER
    assert report.merge.parents_comparison == "UNKNOWN"


def test_tolerated_protection_then_later_linkage_is_recorded(tmp_path: Path) -> None:  # §4.4, CR17
    rejected = {"complete": False, "status_class": "4xx", "reasons": ("HTTP_RESPONSE_REJECTED",)}
    _r, report = _post_action(tmp_path, protection=rejected, pr_after={"projection": _pr()})
    steps = _steps(report)
    assert steps["protection"] == "FAILED" and steps["branch_rules"] == "OBSERVED"
    assert report.stop_reason == "LINKAGE_CHANGED" and report.stop_slot == "pr_after"
    assert _coverage(report)["PROTECTIONS"] == "PARTIAL"


def test_rate_limited_protection_stops_everything(tmp_path: Path) -> None:
    request = _request()
    limited = {"complete": False, "status_class": "4xx", "reasons": ("RATE_LIMITED",)}
    report = _run(tmp_path, request, Scripted(request, protection=limited))
    steps = _steps(report)
    assert report.stop_reason == "OPERATION_FAILURE" and report.stop_slot == "protection"
    assert all(steps[s] == "NOT_ATTEMPTED" for s in ("branch_rules", "rulesets", "pr_after", "repository_after"))
    assert report.target == "UNKNOWN"
    assert report.pr_after is None


def test_no_observation_after_prefix_records_reason(tmp_path: Path) -> None:  # CR2
    request = _request()
    report = _run(tmp_path, request, Scripted(request, reviews=_diagnostic("LEASE_MISSING")))
    step = next(s for s in report.steps if s.slot == "reviews")
    assert step.disposition == "NO_OBSERVATION" and step.reason == "LEASE_MISSING" and step.observation is None
    assert report.stop_slot == "reviews"
    assert _coverage(report)["REVIEWS"] == "UNAVAILABLE"
    assert len(report.observations) == 6  # prefix retained


def test_store_code_returns_error_not_report(tmp_path: Path) -> None:
    request = _request()
    with pytest.raises(FactualCollectionError) as error:
        _run(tmp_path, request, Scripted(request, reviews=_diagnostic("OBSERVATION_STORE_FAILED")))
    assert error.value.code == "STORE_FAILURE"


def test_initial_report_stopping_before_pr_after_keeps_conditionals_not_applicable(tmp_path: Path) -> None:  # R4-6
    request = _request()
    report = _run(tmp_path, request, Scripted(request, pr_before=_diagnostic("LEASE_STALE")))
    steps = _steps(report)
    assert [steps[s] for s in ("merge_commit", "merge_checks", "merge_status")] == ["NOT_APPLICABLE"] * 3
    assert steps["pr_after"] == "NOT_ATTEMPTED"


def test_post_action_stopping_before_pr_after_marks_conditionals_not_attempted(tmp_path: Path) -> None:
    _r, report = _post_action(tmp_path, reviews=_diagnostic("LEASE_STALE"))
    steps = _steps(report)
    assert [steps[s] for s in ("merge_commit", "merge_checks", "merge_status")] == ["NOT_ATTEMPTED"] * 3


def test_failed_merge_commit_leaves_commit_source_null(tmp_path: Path) -> None:  # CR8, branch 4
    failed = {"complete": False, "status_class": "transport", "reasons": ("TRANSPORT_TIMEOUT",)}
    _r, report = _post_action(tmp_path, pr_after={"projection": MERGED_PR}, merge_commit=failed)
    assert report.merge.commit_source is None and report.merge.parents_comparison == "UNKNOWN"
    assert _coverage(report)["POST_MERGE_CHECKS"] == "PARTIAL"
    assert _steps(report)["merge_checks"] == "NOT_ATTEMPTED"


def test_no_observation_merge_commit_is_unavailable(tmp_path: Path) -> None:  # branch 2
    _r, report = _post_action(tmp_path, pr_after={"projection": MERGED_PR}, merge_commit=_diagnostic("LEASE_MISSING"))
    assert _coverage(report)["POST_MERGE_CHECKS"] == "UNAVAILABLE"


def test_merge_commit_with_different_sha_is_an_error(tmp_path: Path) -> None:  # CR19
    wrong = {"complete": False, "projection": {"sha": OTHER, "parents": []}, "identity_match": False,
             "reasons": ("REPOSITORY_IDENTITY_MISMATCH",)}
    with pytest.raises(FactualCollectionError) as error:
        _post_action(tmp_path, pr_after={"projection": MERGED_PR}, merge_commit=wrong)
    assert error.value.code == "SOURCE_BINDING_INVALID"


def test_changed_and_unknown_targets(tmp_path: Path) -> None:  # §4.5, R5-4
    request = _request()
    moved_head = _run(tmp_path, request, Scripted(request, pr_after={"projection": _pr(head_sha=OTHER)}))
    assert moved_head.target == "CHANGED"
    other_repo = {"complete": False, "identity_match": False, "reasons": ("REPOSITORY_IDENTITY_MISMATCH",),
                  "projection": {"repository_id": 999, "account_id": 202}}
    transferred = _run(tmp_path / "t", request, Scripted(request, repository_after=other_repo))
    assert transferred.target == "CHANGED"
    timeout = {"complete": False, "status_class": "transport", "reasons": ("TRANSPORT_TIMEOUT",)}
    timed_out = _run(tmp_path / "u", request, Scripted(request, repository_after=timeout))
    assert timed_out.target == "UNKNOWN"


@pytest.mark.parametrize(
    ("merged_by", "expected_id", "expected"),
    [
        (None, HUMAN, "UNKNOWN"),
        ({"id": HUMAN, "type": "Bot"}, HUMAN, "UNKNOWN"),
        ({"id": HUMAN, "type": "User"}, None, "UNKNOWN"),
        ({"id": 1, "type": "User"}, HUMAN, "DIFFERENT_ACCOUNT"),
        ({"id": HUMAN, "type": "User"}, HUMAN, "SAME_ACCOUNT"),
    ],
)
def test_actor_comparison_is_exhaustive(tmp_path: Path, merged_by, expected_id, expected) -> None:  # CR7
    initial_request = _request(expected_human_id=expected_id)
    pr = dict(MERGED_PR, merged_by=merged_by)
    initial = _run(tmp_path, initial_request, Scripted(initial_request, pr_after={"projection": pr}))
    request = _request(expected_human_id=expected_id, purpose="post_action", expected_merge_sha=MERGE,
                       prior_report=RecordReference(reference="github/factual-reports/i.json", content_hash=initial.content_hash))
    report = _run(tmp_path, request, Scripted(request, pr_after={"projection": pr}), prior=initial, prior_request=initial_request)
    assert report.merge.actor_comparison == expected


# ------------------------------------------------------------------ §4.6 preflight


def test_live_mode_is_refused(tmp_path: Path) -> None:  # §8 fixture-only
    request = _request(mode="live")
    with pytest.raises(FactualCollectionError) as error:
        _run(tmp_path, request, Scripted(request))
    assert error.value.code == "LIVE_MODE_NOT_AUTHORIZED"


def test_preflight_rejects_reused_authorization_across_pr_reads(tmp_path: Path) -> None:
    request = _request()
    bindings = _bindings(request, pr_after=_binding(10, request, auth_id=3))
    bindings["pr_after"] = SlotBinding(bindings["pr_before"].authorization, bindings["pr_after"].intent, bindings["pr_after"].attempt_claim)
    with pytest.raises(FactualCollectionError) as error:
        _run(tmp_path, request, Scripted(request), bindings=bindings)
    assert error.value.code == "PREFLIGHT_INVALID"


def test_preflight_rejects_missing_or_extra_bindings(tmp_path: Path) -> None:
    request = _request()
    missing = _bindings(request)
    del missing["reviews"]
    extra = _bindings(request)
    post = _request(purpose="post_action", expected_merge_sha=MERGE,
                    prior_report=RecordReference(reference="github/factual-reports/x.json", content_hash=H9))
    extra["merge_commit"] = _binding(11, post)
    for bindings in (missing, extra):
        with pytest.raises(FactualCollectionError) as error:
            _run(tmp_path, request, Scripted(request), bindings=bindings)
        assert error.value.code == "PREFLIGHT_INVALID"


def test_preflight_rejects_used_attempt_digest(tmp_path: Path) -> None:
    request = _request()
    bindings = _bindings(request)
    used = attempt_claim_path(tmp_path / "claims", bindings["reviews"].intent.attempt_id)
    used.parent.mkdir(parents=True, exist_ok=True)
    used.write_bytes(b"{}")
    executor = Scripted(request)
    with pytest.raises(FactualCollectionError) as error:
        _run(tmp_path, request, executor, bindings=bindings)
    assert error.value.code == "PREFLIGHT_INVALID"
    assert executor.calls == []  # nothing dispatched


def test_preflight_does_not_evaluate_time(tmp_path: Path) -> None:  # R4-7
    request = _request()
    bindings = _bindings(request)
    executor = Scripted(request, reviews=_diagnostic("AUTHORIZATION_EXPIRED"))
    report = _run(tmp_path, request, executor, bindings=bindings)  # preflight passed
    assert report.stop_slot == "reviews"
    assert next(s for s in report.steps if s.slot == "reviews").reason == "AUTHORIZATION_EXPIRED"


def test_wrong_repository_observation_is_an_error(tmp_path: Path) -> None:  # §4.5 source binding
    request = _request()
    with pytest.raises(FactualCollectionError) as error:
        _run(tmp_path, request, Scripted(request, reviews={"repository_id": 999}))
    assert error.value.code == "SOURCE_BINDING_INVALID"


def test_prior_report_must_be_merged_initial(tmp_path: Path) -> None:  # §3
    initial_request = _request()
    initial = _run(tmp_path, initial_request, Scripted(initial_request))  # OPEN, not MERGED
    request = _request(purpose="post_action", expected_merge_sha=MERGE,
                       prior_report=RecordReference(reference="github/factual-reports/i.json", content_hash=initial.content_hash))
    with pytest.raises(FactualCollectionError) as error:
        _run(tmp_path, request, Scripted(request), prior=initial, prior_request=initial_request)
    assert error.value.code == "PRIOR_REPORT_INVALID"


# ------------------------------------------- real Stage 21A read under the profile


def _real_factual_read(tmp_path: Path, monkeypatch, response) -> Any:
    """Drive the real execute_github_read with the 21A ephemeral-key fixture,
    substituting only the API profile with the factual one (rule 4(a)-(b))."""

    import json as _json

    import test_github_foundation as tgf
    from conclave.github_foundation import GitHubTransportResponse
    from conclave.github_operation import execute_github_read
    from conclave.ledger import initialise as initialise_ledger
    from conclave.workspace import Workspace
    from github_fixture_support import FixtureGitHubTransport

    factual = seal_record(
        GitHubFactualApiProfile,
        {"profile": "github-factual-api-profile", "schema_version": FACTUAL_API_PROFILE_SCHEMA,
         **{**CONSTANTS, "created_at": tgf.NOW}},
    )
    monkeypatch.setattr(tgf, "_api_profile", lambda **_: factual)
    fixture = tgf._credential_fixture()
    workspace = Workspace.create(tmp_path / "workspace", principal="arthur")
    initialise_ledger(workspace, workspace.load_config())
    status, body = response
    transport = FixtureGitHubTransport([
        GitHubTransportResponse(status, (("Content-Type", "application/json"),
                                         ("X-RateLimit-Remaining", "4999")),
                                _json.dumps(body, separators=(",", ":")).encode())
    ])
    clock = tgf._Clock(*[f"2026-09-09T06:00:{s:02d}Z" for s in (0, 3, 4, 5, 6, 7, 8, 10)])
    result = execute_github_read(
        workspace=workspace, repository_profile=fixture["repository_profile"],
        api_profile=fixture["api_profile"], provider_key=fixture["provider_key"],
        authorization=fixture["authorization"], intent=fixture["intent"],
        attempt_claim=fixture["attempt_claim"], request=fixture["request"],
        provider=fixture["provider"], transport=transport,
        observation_id="01890f3e-7b1a-7cc2-8b4f-8f2e9c90a113",
        clock=clock, monotonic=lambda: 0.0,
    )
    return factual, result


def test_real_21a_read_records_factual_projection_set(tmp_path: Path, monkeypatch) -> None:  # §5
    ref = {"ref": "refs/heads/main", "node_id": "REF_fixture", "object": {"sha": "a" * 40, "type": "commit"}}
    factual, result = _real_factual_read(tmp_path, monkeypatch, (200, ref))
    observation = result.observation
    assert observation is not None and observation.complete
    assert observation.response_projection_version == FACTUAL_RESPONSE_PROJECTION_VERSION
    assert observation.api_profile.content_hash == factual.content_hash
    assert record_result(result)[0] == "OBSERVED"


def test_real_http_rejection_is_its_own_status_class_and_is_tolerated(tmp_path: Path, monkeypatch) -> None:
    """Stage 21A section 9: a received HTTP rejection carries its own status
    class. With that, profile section 4.4's tolerated-rejection path — the
    round-1 B2 fix — is reachable end to end: a branch-protection 404 on a
    repository governed by rulesets rather than classic protection no longer
    destroys the rest of the report."""

    _factual, result = _real_factual_read(tmp_path, monkeypatch, (404, {"message": "Not Found"}))
    observation = result.observation
    assert observation is not None and not observation.complete
    assert observation.reason_codes == ("HTTP_RESPONSE_REJECTED",)
    assert observation.status_class == "4xx"
    assert is_tolerated("protection", observation)  # continues; §7 still says unavailable
    assert not is_tolerated("reviews", observation)  # only PROTECTIONS slots


def test_real_transport_failure_keeps_transport_class(tmp_path: Path, monkeypatch) -> None:
    """The corrected rule does not relabel failures with no usable response."""

    import test_github_foundation as tgf
    from conclave.github_foundation import GitHubTransportFailure
    from conclave.github_operation import execute_github_read
    from conclave.ledger import initialise as initialise_ledger
    from conclave.workspace import Workspace
    from github_fixture_support import FixtureGitHubTransport

    factual = seal_record(
        GitHubFactualApiProfile,
        {"profile": "github-factual-api-profile", "schema_version": FACTUAL_API_PROFILE_SCHEMA,
         **{**CONSTANTS, "created_at": tgf.NOW}},
    )
    monkeypatch.setattr(tgf, "_api_profile", lambda **_: factual)
    fixture = tgf._credential_fixture()
    workspace = Workspace.create(tmp_path / "workspace", principal="arthur")
    initialise_ledger(workspace, workspace.load_config())
    transport = FixtureGitHubTransport([
        GitHubTransportFailure("TRANSPORT_TIMEOUT", before_headers=False),
    ])
    clock = tgf._Clock(*[f"2026-09-09T06:00:{s:02d}Z" for s in (0, 3, 4, 5, 6, 7, 8, 10)])
    result = execute_github_read(
        workspace=workspace, repository_profile=fixture["repository_profile"],
        api_profile=fixture["api_profile"], provider_key=fixture["provider_key"],
        authorization=fixture["authorization"], intent=fixture["intent"],
        attempt_claim=fixture["attempt_claim"], request=fixture["request"],
        provider=fixture["provider"], transport=transport,
        observation_id="01890f3e-7b1a-7cc2-8b4f-8f2e9c90a114",
        clock=clock, monotonic=lambda: 0.0,
    )
    assert result.observation is not None
    assert result.observation.status_class == "transport"
    assert not is_tolerated("protection", result.observation)


# ------------------------------------------------------------------ persistence


def test_report_persists_immutably_and_revalidates(tmp_path: Path) -> None:  # §3, §6
    request = _request()
    report = _run(tmp_path, request, Scripted(request))
    path = persist_factual_report(tmp_path, report)
    again = FactualReport.model_validate_json(path.read_bytes())
    assert again == report
    assert persist_factual_report(tmp_path, report) == path  # idempotent, no overwrite


def test_module_has_no_live_or_mutation_path() -> None:  # §8
    source = Path(__import__("conclave.github_factual", fromlist=["x"]).__file__).read_text(encoding="utf-8")
    for forbidden in ("HTTPSGitHubTransport", "create_production_https_transport", "prepare_credential_lease",
                      "\"PUT\"", "\"POST\"", "\"PATCH\"", "\"DELETE\"", "merge_pull"):
        assert forbidden not in source
