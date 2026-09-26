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
    SLOT_BY_NAME,
    Section,
    Step,
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


def _binding(
    slot_index: int,
    request: FactualRequest,
    *,
    auth_id: int | None = None,
    requests_override: int | None = None,
    pages_override: int | None = None,
    attempt_id_override: str | None = None,
) -> SlotBinding:
    slot = SLOTS[slot_index]
    path, query = expected_parameters(slot, request)
    requests = requests_override or (slot.maximum_pages + 1)
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
        maximum_pages=pages_override or slot.maximum_pages,
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
            "maximum_pages": pages_override or slot.maximum_pages,
            "maximum_items": 1000 if slot.maximum_pages > 1 else 1,
            "operation_timeout_seconds": 60,
            "maximum_retry_transmissions_per_operation": 1,
            "maximum_network_requests": requests,
            "attempt_id": attempt_id_override or attempt,
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
            "attempt_id": attempt_id_override or attempt,
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
    pagination_complete: bool | None = None,
    path_parameters: dict[str, Any] | None = None,
    query_parameters: dict[str, Any] | None = None,
    projection_version: str = FACTUAL_RESPONSE_PROJECTION_VERSION,
    attempt_id: str | None = None,
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
            "query_parameters": query_parameters if query_parameters is not None else dict(intent.query_parameters),
            "attempt_id": attempt_id or intent.attempt_id,
            "observed_at": NOW,
            "status_class": status_class,
            "pages": pages if pages is not None else (_page(),),
            "response_projection_version": projection_version,
            "projection": projection or {"visibility": "complete_for_endpoint"},
            "complete": complete,
            "pagination_complete": complete if pagination_complete is None else pagination_complete,
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


_FORBIDDEN_NAMES = frozenset(
    {
        "HTTPSGitHubTransport",
        "create_production_https_transport",
        "prepare_credential_lease",
        "run_github_transport",
        "execute_github_read",
    }
)


def _conclave_source(name: str) -> str:
    import conclave

    return (Path(conclave.__file__).parent / f"{name}.py").read_text(encoding="utf-8")


def _module_exists(name: str) -> bool:
    import conclave

    return (Path(conclave.__file__).parent / f"{name}.py").is_file()


def _local_imports(source: str) -> set[str]:
    """Every first-party module this source imports, at ANY nesting depth.

    ast.walk descends into function and class bodies, so a lazy
    ``from .github_publication_engine import ...`` inside a helper is found —
    the hole that let a module-namespace walk be defeated (review 0002).
    """

    import ast

    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module and node.level in (0, 1):
            head = node.module.split(".")[0]
            found.add(head if node.level == 1 else node.module.removeprefix("conclave.").split(".")[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("conclave."):
                    found.add(alias.name.split(".")[1])
    return found


def _referenced_names(source: str) -> set[str]:
    """Every identifier the source mentions, at any depth: bare names, imported
    names and attribute tails, so ``foundation.HTTPSGitHubTransport()`` and a
    function-local ``from .github_foundation import HTTPSGitHubTransport`` are
    both visible."""

    import ast

    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, ast.Attribute):
            found.add(node.attr)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                found.add(alias.name.split(".")[-1])
                if alias.asname:
                    found.add(alias.asname)
    return found


def test_module_references_no_transport_or_credential_machinery() -> None:  # §8
    """§8 fixture-only, as a source property of THIS module at any nesting depth.

    The claim is deliberately narrow and true: github_factual creates no
    transport, lease or dispatch of its own; every slot is run by an injected
    executor. It does import github_operation for the GitHubReadResult shape,
    and github_operation does build a live path — so a transitive 'nothing
    reachable builds a transport' claim would be false, and the previous test
    made it."""

    referenced = _referenced_names(_conclave_source("github_factual"))
    assert not (referenced & _FORBIDDEN_NAMES), sorted(referenced & _FORBIDDEN_NAMES)


def test_no_mutation_module_is_reachable_at_any_depth() -> None:  # §8
    """Transitive import closure over first-party modules, computed from source
    so that an import hidden inside a function body is still counted."""

    seen: set[str] = set()
    pending = ["github_factual"]
    while pending:
        name = pending.pop()
        if name in seen or not _module_exists(name):
            continue
        seen.add(name)
        pending.extend(_local_imports(_conclave_source(name)))

    assert "github_foundation" in seen and "github_operation" in seen  # closure is real
    assert not {name for name in seen if "publication" in name}, sorted(seen)


def test_the_reachability_detectors_catch_a_lazy_import() -> None:
    """Guards the two tests above from passing vacuously.

    Seat 3 of review 0002 defeated the previous module-namespace walk with
    exactly this shape — a live transport and a publication-engine import
    placed inside a function body — and all tests still passed."""

    defeat = chr(10).join(
        (
            'from __future__ import annotations',
            'def collect():',
            '    from .github_publication_engine import publish',
            '    from .github_foundation import HTTPSGitHubTransport',
            '    return HTTPSGitHubTransport(), publish',
        )
    )
    assert "github_publication_engine" in _local_imports(defeat)
    assert _referenced_names(defeat) & _FORBIDDEN_NAMES == {"HTTPSGitHubTransport"}

    clean = 'from .github_operation import GitHubReadResult'
    assert _local_imports(clean) == {"github_operation"}
    assert not (_referenced_names(clean) & _FORBIDDEN_NAMES)


def test_live_use_cannot_be_switched_on() -> None:  # §8
    from conclave.github_foundation import create_production_https_transport

    assert GitHubRepositoryProfile.model_fields["live_use_allowed"].annotation is not bool
    with pytest.raises(GitHubFoundationFailure):
        create_production_https_transport(REPO, API)


# --------------------------------------------------- review-0001 regression tests


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"merged_at": NOW}, "UNKNOWN"),               # open + merged_at
        ({"merged_by": {"id": 1, "type": "User"}}, "UNKNOWN"),  # open + merged_by
        ({"state": "closed", "merged_at": NOW}, "UNKNOWN"),     # closed, unmerged, merged_at
    ],
)
def test_merge_state_requires_every_qualifier(changes: dict, expected: str) -> None:
    assert merge_state(_pr(**changes)) == expected


def test_target_changed_from_account_id_and_object_format(tmp_path: Path) -> None:
    request = _request()
    account = {"complete": False, "identity_match": False, "reasons": ("REPOSITORY_IDENTITY_MISMATCH",),
               "projection": {"repository_id": 101, "account_id": 999}}
    assert _run(tmp_path / "a", request, Scripted(request, repository_after=account)).target == "CHANGED"
    fmt = {"complete": False, "identity_match": False, "reasons": ("REPOSITORY_IDENTITY_MISMATCH",),
           "projection": {"hash_algorithm": "sha256"}}
    assert _run(tmp_path / "b", request, Scripted(request, object_format_after=fmt)).target == "CHANGED"


def test_non_2xx_verification_projection_is_not_evidence_of_change(tmp_path: Path) -> None:
    """§4.5: identity_match false without a 2xx projection is not CHANGED."""

    request = _request()
    for status in ("transport", "4xx"):
        differing = {"complete": False, "identity_match": False, "status_class": status,
                     "reasons": ("TRANSPORT_TIMEOUT",) if status == "transport" else ("HTTP_RESPONSE_REJECTED",),
                     "projection": {"repository_id": 999, "account_id": 999}}
        report = _run(tmp_path / status, request, Scripted(request, repository_after=differing))
        assert report.target == "UNKNOWN", status


@pytest.mark.parametrize("field", ["base_ref", "head_ref"])
def test_target_changed_when_a_pr_ref_differs(tmp_path: Path, field: str) -> None:
    request = _request()
    pr = _pr(**{field: "somewhere-else"})
    assert _run(tmp_path / field, request, Scripted(request, pr_after={"projection": pr})).target == "CHANGED"


def test_same_requires_the_base_ref_observation_to_match(tmp_path: Path) -> None:
    request = _request()
    wrong = {"projection": {"requested_ref": "refs/heads/main", "returned_ref": "refs/heads/other",
                            "object_sha": BASE}}
    assert _run(tmp_path, request, Scripted(request, base_ref=wrong)).target == "UNKNOWN"


@pytest.mark.parametrize(
    ("slot", "spec"),
    [
        ("head_checks", {"path_parameters": {"commit_sha": MERGE}}),
        ("reviews", {"query_parameters": {"per_page": 100, "page": 2}}),
        ("reviews", {"projection_version": "github-21a-rest-projections/0.1.0"}),
        ("reviews", {"attempt_id": "attempt:sha256:" + "e" * 64}),
    ],
)
def test_source_binding_rejects_mismatched_observations(tmp_path: Path, slot: str, spec: dict) -> None:
    request = _request()
    with pytest.raises(FactualCollectionError) as error:
        _run(tmp_path, request, Scripted(request, **{slot: spec}))
    assert error.value.code == "SOURCE_BINDING_INVALID"


def test_preflight_rejects_a_fully_reused_binding(tmp_path: Path) -> None:
    """§4.6: a self-consistent chain reused across two slots must still fail,
    so the reuse rule is what fires — not the chain-consistency rule."""

    request = _request()
    for reused, source in (("pr_after", "pr_before"), ("repository_after", "repository")):
        bindings = _bindings(request)
        bindings[reused] = bindings[source]
        executor = Scripted(request)
        with pytest.raises(FactualCollectionError) as error:
            _run(tmp_path / reused, request, executor, bindings=bindings)
        assert error.value.code == "PREFLIGHT_INVALID"
        assert executor.calls == []


def test_duplicate_attempt_digests_cannot_be_constructed() -> None:
    """§4.6 requires unused, distinct attempt digests. Two slots cannot share
    one with valid records at all: Stage 21A binds the digest to its canonical
    preimage, so a forged intent is rejected before this profile sees it. The
    21C check remains as defence for injected results."""

    request = _request()
    shared = _binding(3, request).intent.attempt_id
    with pytest.raises(Exception) as error:
        _binding(6, request, attempt_id_override=shared)
    assert "attempt_id" in str(error.value)


def test_preflight_rejects_a_binding_with_the_wrong_page_ceiling(tmp_path: Path) -> None:
    request = _request()
    bindings = _bindings(request)
    bindings["reviews"] = _binding(6, request, pages_override=3)
    with pytest.raises(FactualCollectionError) as error:
        _run(tmp_path, request, Scripted(request), bindings=bindings)
    assert error.value.code == "PREFLIGHT_INVALID"


def test_wrong_network_request_ceiling_is_refused_by_stage_21a() -> None:
    """§4.6 also pins maximum_network_requests, but Stage 21A rejects a
    mismatch first: an authorization must carry the endpoint ceiling plus one.
    The 21C check remains as defence."""

    with pytest.raises(Exception) as error:
        _binding(6, _request(), requests_override=2)
    assert "maximum_network_requests" in str(error.value)


def test_first_stop_condition_is_never_overwritten(tmp_path: Path) -> None:  # §4.4
    failed = {"complete": False, "status_class": "transport", "reasons": ("TRANSPORT_TIMEOUT",)}
    _r, report = _post_action(tmp_path, pr_after={"projection": _pr()}, repository_after=failed)
    assert report.stop_reason == "LINKAGE_CHANGED" and report.stop_slot == "pr_after"
    assert _steps(report)["repository_after"] == "FAILED"
    assert _steps(report)["object_format_after"] == "NOT_ATTEMPTED"


def test_test_merge_sha_is_never_dispatched(tmp_path: Path) -> None:  # §5.1
    open_with_test_merge = _pr(merge_sha=MERGE)
    _r, report = _post_action(tmp_path, pr_after={"projection": open_with_test_merge})
    steps = _steps(report)
    assert [steps[s] for s in ("merge_commit", "merge_checks", "merge_status")] == ["NOT_APPLICABLE"] * 3
    assert report.merge.state == "OPEN" and report.merge.merge_sha is None
    assert report.stop_reason == "LINKAGE_CHANGED"


@pytest.mark.parametrize(
    ("parents", "expected"),
    [
        ([{"sha": BASE}, {"sha": HEAD}], "MATCH"),
        ([{"sha": HEAD}, {"sha": BASE}], "DIFFERENT"),   # order matters
        ([{"sha": OTHER}, {"sha": HEAD}], "DIFFERENT"),
        ([{"sha": BASE}], "UNSUPPORTED"),                 # squash
        ([{"sha": BASE}, {"sha": HEAD}, {"sha": OTHER}], "UNSUPPORTED"),
    ],
)
def test_parents_comparison_arms(tmp_path: Path, parents: list, expected: str) -> None:  # §5.3
    commit = {"projection": {"sha": MERGE, "parents": parents}}
    _r, report = _post_action(tmp_path, pr_after={"projection": MERGED_PR}, merge_commit=commit)
    assert report.merge.parents_comparison == expected


def test_request_reference_must_bind_the_request(tmp_path: Path) -> None:
    request = _request()
    with pytest.raises(FactualCollectionError) as error:
        collect_factual_report(
            request=request,
            request_reference=RecordReference(reference="github/factual-requests/req.json", content_hash=H9),
            repository_profile=REPO, api_profile=API, bindings=_bindings(request),
            executor=Scripted(request), attempt_claims_dir=tmp_path / "claims", clock=_clock,
        )
    assert error.value.code == "REQUEST_INVALID"


@pytest.mark.parametrize("change", [{"mode": "fixture", "head_ref": "refs/heads/other"}, {"expected_human_id": 7}])
def test_prior_report_request_must_match(tmp_path: Path, change: dict) -> None:  # §3
    initial_request = _request()
    initial = _run(tmp_path, initial_request, Scripted(initial_request, pr_after={"projection": MERGED_PR}))
    request = _request(purpose="post_action", expected_merge_sha=MERGE,
                       prior_report=RecordReference(reference="github/factual-reports/i.json",
                                                    content_hash=initial.content_hash), **change)
    with pytest.raises(FactualCollectionError) as error:
        _run(tmp_path, request, Scripted(request), prior=initial, prior_request=initial_request)
    assert error.value.code == "PRIOR_REPORT_INVALID"


def _report_body(report: FactualReport) -> dict[str, Any]:
    """Re-sealable body: strict mode needs tuples, not the JSON lists."""

    body = report.model_dump(mode="json")
    body.pop("content_hash")
    body["observations"] = tuple(report.observations)
    body["sections"] = tuple(report.sections)
    body["steps"] = tuple(report.steps)
    body["limitations"] = tuple(report.limitations)
    body["merge"] = report.merge
    body["request"] = report.request
    body["pr_before"] = report.pr_before
    body["pr_after"] = report.pr_after
    return body


def test_report_body_reseals_unchanged(tmp_path: Path) -> None:
    """Guards the tampering test below from passing vacuously."""

    request = _request()
    report = _run(tmp_path, request, Scripted(request))
    assert seal_record(FactualReport, _report_body(report)).content_hash == report.content_hash


def test_report_record_closure_rejects_tampering(tmp_path: Path) -> None:  # §3
    request = _request()
    report = _run(tmp_path, request, Scripted(request))

    def reseal(message: str, **changes) -> None:
        with pytest.raises(PydanticValidationError) as error:
            seal_record(FactualReport, {**_report_body(report), **changes})
        assert message in str(error.value)

    reseal("exact sorted section 7 list", limitations=LIMITATIONS[:-1])
    reseal("exactly one step", observations=report.observations + report.observations[:1])
    reseal("must equal their slot references", pr_before=None)
    with pytest.raises(PydanticValidationError) as error:  # rejected at Step level
        Step(slot="reviews", disposition="NOT_APPLICABLE", observation=None, reason=None)
    assert "confined to the conditional slots" in str(error.value)
    steps = list(report.steps)
    steps[6] = Step(slot="reviews", disposition="NOT_ATTEMPTED", observation=None, reason=None)
    reseal("exactly one step", steps=tuple(steps))  # drops an observation's owner
    sections = list(report.sections)
    sections[0] = Section(kind=sections[0].kind, coverage=sections[0].coverage, sources=())
    reseal("slots' observations in slot order", sections=tuple(sections))


def test_observations_are_sorted_by_operation_then_parameters(tmp_path: Path) -> None:  # §3
    _r, report = _post_action(tmp_path, pr_after={"projection": MERGED_PR})
    assert len(report.observations) == 16
    order = [reference.reference for reference in report.observations]
    # repository.get twice with identical parameters, check_runs.list and
    # combined_status.get twice each with different commit SHAs: the sort key
    # is (operation key, canonical parameters, content hash), so the head and
    # merge SHA variants must be adjacent and ordered by their parameters.
    head_checks, merge_checks = (
        next(i for i, s in enumerate(report.steps) if s.slot == slot)
        for slot in ("head_checks", "merge_checks")
    )
    head_ref = report.steps[head_checks].observation.reference
    merge_ref = report.steps[merge_checks].observation.reference
    # HEAD sha is "b"*40 and the merge sha "c"*40, so canonical parameters sort
    # the head read before the merge read within the same operation key.
    assert order.index(head_ref) < order.index(merge_ref)
    by_key: dict[str, list[int]] = {}
    for step in report.steps:
        if step.observation is not None:
            key = SLOT_BY_NAME[step.slot].operation_key
            by_key.setdefault(key, []).append(order.index(step.observation.reference))
    for key, positions in by_key.items():
        assert positions == sorted(positions) or len(positions) == 1, key
        assert max(positions) - min(positions) == len(positions) - 1, key  # adjacent


def test_checks_section_partial_when_one_slot_fails(tmp_path: Path) -> None:  # §3 branch 4
    request = _request()
    failed = {"complete": False, "status_class": "transport", "reasons": ("TRANSPORT_TIMEOUT",)}
    report = _run(tmp_path, request, Scripted(request, head_status=failed))
    assert _coverage(report)["CHECKS"] == "PARTIAL"
    assert report.stop_slot == "head_status"


def test_coverage_requires_identity_and_pagination(tmp_path: Path) -> None:  # §3 branch 3
    request = _request()
    odd = {"identity_match": False}
    assert _coverage(_run(tmp_path / "i", request, Scripted(request, reviews=odd)))["REVIEWS"] == "PARTIAL"
    assert _coverage(_run(tmp_path / "p", request, Scripted(request, reviews={"pagination_complete": False})))["REVIEWS"] == "PARTIAL"


# --------------------------------------------------- review-0002 regression tests


def test_plan_reservation_is_evaluated_against_real_ceilings() -> None:  # §6
    """Guards the overflow test below: a conforming initial binding set sits
    exactly at the 95-transmission plan, so the check compares supplied
    ceilings against the reserved remainder, not the plan against itself."""

    request = _request()
    bindings = _bindings(request)
    declared = sum(b.authorization.maximum_network_requests for b in bindings.values())
    reserved = sum(s.maximum_pages + 1 for s in SLOTS if s.name not in bindings)
    assert declared == 71 and reserved == 24
    assert declared + reserved == MAXIMUM_TRANSMISSIONS


def test_plan_overflow_is_refused_for_an_injected_binding(tmp_path: Path) -> None:  # §6
    """The overflow guard is defence against injected bindings, and only that.

    Stage 21A pins every authorization's maximum_network_requests to its own
    endpoint's page ceiling plus one, and the 16-slot plan is frozen at exactly
    95 transmissions, so no *conforming* binding set can overflow -- the same
    class as the two findings review 0001 recorded as 21A-enforced. The guard
    is reachable only by constructing a record Stage 21A would refuse to seal,
    which is what this test does. The previous form could not fire even then,
    because it compared the plan against itself (95 > 95).
    """

    request = _request()
    index = next(i for i, s in enumerate(SLOTS) if s.maximum_pages == 1)
    name = SLOTS[index].name
    sound = _binding(index, request)
    injected = SlotBinding(
        authorization=GitHubOperationAuthorization.model_construct(
            **{**dict(sound.authorization), "maximum_network_requests": 11}
        ),
        intent=sound.intent,
        attempt_claim=sound.attempt_claim,
    )
    assert injected.authorization.maximum_network_requests == 11
    with pytest.raises(PydanticValidationError):  # 21A would never seal it
        seal_record(
            GitHubOperationAuthorization,
            {k: v for k, v in dict(sound.authorization).items() if k != "content_hash"}
            | {"maximum_network_requests": 11},
        )

    bindings = _bindings(request, **{name: injected})
    executor = Scripted(request)
    with pytest.raises(FactualCollectionError) as error:
        _run(tmp_path, request, executor, bindings=bindings)
    assert error.value.code == "BUDGET_OVERFLOW"
    assert executor.calls == []  # overflow precedes every dispatch


def test_commit_source_is_a_biconditional(tmp_path: Path) -> None:  # §5.2
    """commit_source is the merge_commit observation exactly when that Step is
    OBSERVED. Keying only on the observation left both other directions open:
    a FAILED step carries an observation but must never be commit_source, and
    an OBSERVED step must not seal with commit_source null."""

    from conclave.github_factual import Merge

    failed = {"complete": False, "status_class": "transport", "reasons": ("TRANSPORT_TIMEOUT",)}
    _r, failed_report = _post_action(tmp_path / "f", pr_after={"projection": MERGED_PR},
                                     merge_commit=failed)
    failed_step = next(s for s in failed_report.steps if s.slot == "merge_commit")
    assert failed_step.disposition == "FAILED" and failed_step.observation is not None
    assert failed_report.merge.commit_source is None

    _r2, ok_report = _post_action(tmp_path / "o", pr_after={"projection": MERGED_PR})
    ok_step = next(s for s in ok_report.steps if s.slot == "merge_commit")
    assert ok_step.disposition == "OBSERVED"
    assert ok_report.merge.commit_source == ok_step.observation

    def reseal(report: FactualReport, message: str, **merge_changes) -> None:
        merge = Merge(**{**report.merge.model_dump(), **merge_changes})
        with pytest.raises(PydanticValidationError) as error:
            seal_record(FactualReport, {**_report_body(report), "merge": merge})
        assert message in str(error.value)

    # A FAILED merge_commit whose observation is promoted to commit_source.
    reseal(failed_report, "iff that step is OBSERVED",
           commit_source=failed_step.observation, parents_comparison="MATCH")
    # An OBSERVED merge_commit sealing with commit_source dropped.
    reseal(ok_report, "iff that step is OBSERVED",
           commit_source=None, parents_comparison="UNKNOWN")
    # §5.3: a null commit_source can only yield UNKNOWN parents.
    reseal(failed_report, "parents_comparison is UNKNOWN",
           commit_source=None, parents_comparison="MATCH")


@pytest.mark.parametrize(
    "merged_by",
    [
        {"type": "User"},                    # no id
        {"id": HUMAN},                       # no type
        {"id": "5150", "type": "User"},      # id is not an integer
        "komistry-dev",                      # not an object at all
    ],
)
def test_malformed_actor_projection_is_a_closed_error(tmp_path: Path, merged_by: Any) -> None:
    """§6: a corrupted retained projection returns an error with a closed code,
    not an uncaught KeyError or TypeError escaping the cycle."""

    projection = {**MERGED_PR, "merged_by": merged_by}
    with pytest.raises(FactualCollectionError) as error:
        _post_action(tmp_path, pr_after={"projection": projection})
    assert error.value.code == "RESULT_INVALID"


@pytest.mark.parametrize("merge_sha", [12345, {"sha": MERGE}, [MERGE]])
def test_malformed_merge_sha_is_a_closed_error(tmp_path: Path, merge_sha: Any) -> None:
    """A non-string merge_commit_sha would otherwise surface as a raw pydantic
    error from Merge rather than this profile's closed failure code."""

    projection = {**MERGED_PR, "merge_commit_sha": merge_sha}
    with pytest.raises(FactualCollectionError) as error:
        _post_action(tmp_path, pr_after={"projection": projection})
    assert error.value.code == "RESULT_INVALID"


@pytest.mark.parametrize(
    "parents",
    [
        "c" * 40,                                  # not a sequence of objects
        [{"sha": BASE}, {"commit": HEAD}],         # an entry without "sha"
        [{"sha": BASE}, HEAD],                     # an entry that is not an object
    ],
)
def test_malformed_parents_projection_is_a_closed_error(tmp_path: Path, parents: Any) -> None:
    with pytest.raises(FactualCollectionError) as error:
        _post_action(tmp_path, pr_after={"projection": MERGED_PR},
                     merge_commit={"projection": {"sha": MERGE, "parents": parents}})
    assert error.value.code == "RESULT_INVALID"
