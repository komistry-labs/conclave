"""Stage 21C factual PR assistant — fixture-only implementation.

Implements the adopted profile ``INCREMENT-21C-FACTUAL-PR-ASSISTANT-PROTOCOL.md``
(SHA-256 ``ed45fb9f2e1dfc8d8e9f542d71b8e67678aafe1d99120f209f5cb3b1891ab962``).

The profile answers factual questions about one pull request and never emits a
readiness verdict, approval or overall green indicator. It records what Stage
21A returns and never restates how Stage 21A works: every Step disposition,
stop, coverage, target and Merge value below is a pure function of Stage 21A
results, so a validator holding the referenced observations can recompute them.
Three report fields are not recomputable that way and are recorded as given: a
NO_OBSERVATION step's `reason` (Stage 21A emits it without an observation) and
the informational `started_at` / `completed_at` readings.

Scope of this module (profile §8): fixture-only. ``mode: live`` is refused, no
transport or credential is created here, and each slot is executed by an
injected executor that returns one Stage 21A ``GitHubReadResult``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal, Mapping

from pydantic import Field, field_validator, model_validator

from .errors import ValidationError
from .github_foundation import (
    ENDPOINTS,
    FACTUAL_RESPONSE_PROJECTION_VERSION,
    HASH_PATTERN,
    REASON_CODES,
    GitHubFactualApiProfile,
    GitHubObservation,
    GitHubOperationAttemptClaim,
    GitHubOperationAuthorization,
    GitHubOperationIntent,
    GitHubRecord,
    GitHubRepositoryProfile,
    RecordReference,
    attempt_claim_path,
    write_durable_record,
)
from .github_operation import GitHubReadResult
from .identity import ClosedModel, seal_record

PROTOCOL_SHA256 = (
    "sha256:ed45fb9f2e1dfc8d8e9f542d71b8e67678aafe1d99120f209f5cb3b1891ab962"
)
REQUEST_SCHEMA = "github-factual-request/0.1.0"
REPORT_SCHEMA = "github-factual-report/0.1.0"

SectionKind = Literal["TARGET", "CHECKS", "REVIEWS", "PROTECTIONS", "POST_MERGE_CHECKS"]
Disposition = Literal[
    "OBSERVED", "FAILED", "NO_OBSERVATION", "NOT_ATTEMPTED", "NOT_APPLICABLE"
]
Coverage = Literal["COMPLETE_WITHIN_ENDPOINT", "PARTIAL", "UNAVAILABLE", "NOT_REQUESTED"]
StopReason = Literal["NONE", "OPERATION_FAILURE", "LINKAGE_CHANGED"]
Target = Literal["SAME", "CHANGED", "UNKNOWN"]
MergeState = Literal["OPEN", "CLOSED_UNMERGED", "MERGED", "UNKNOWN"]
ParentsComparison = Literal["MATCH", "DIFFERENT", "UNSUPPORTED", "UNKNOWN"]
ActorComparison = Literal["SAME_ACCOUNT", "DIFFERENT_ACCOUNT", "UNKNOWN"]


@dataclass(frozen=True)
class Slot:
    name: str
    operation_key: str
    section: str
    maximum_pages: int


# Profile §4.1: the whole plan, in dispatch order.
SLOTS: tuple[Slot, ...] = (
    Slot("repository", "repository.get", "TARGET", 1),
    Slot("object_format", "repository_hash_algorithm.get", "TARGET", 1),
    Slot("base_ref", "ref.get", "TARGET", 1),
    Slot("pr_before", "pull_request.get", "TARGET", 1),
    Slot("head_checks", "check_runs.list", "CHECKS", 10),
    Slot("head_status", "combined_status.get", "CHECKS", 10),
    Slot("reviews", "reviews.list", "REVIEWS", 10),
    Slot("protection", "branch_protection.get", "PROTECTIONS", 1),
    Slot("branch_rules", "branch_rules.list", "PROTECTIONS", 10),
    Slot("rulesets", "repository_rulesets.list", "PROTECTIONS", 10),
    Slot("pr_after", "pull_request.get", "TARGET", 1),
    Slot("merge_commit", "commit.get", "POST_MERGE_CHECKS", 1),
    Slot("merge_checks", "check_runs.list", "POST_MERGE_CHECKS", 10),
    Slot("merge_status", "combined_status.get", "POST_MERGE_CHECKS", 10),
    Slot("repository_after", "repository.get", "TARGET", 1),
    Slot("object_format_after", "repository_hash_algorithm.get", "TARGET", 1),
)
SLOT_BY_NAME: Mapping[str, Slot] = {slot.name: slot for slot in SLOTS}
CONDITIONAL_SLOTS = frozenset({"merge_commit", "merge_checks", "merge_status"})
PROTECTION_SLOTS = frozenset({"protection", "branch_rules", "rulesets"})
VERIFICATION_SLOTS = frozenset(
    {"repository", "object_format", "repository_after", "object_format_after"}
)
SECTION_KINDS: tuple[str, ...] = tuple(
    sorted({"TARGET", "CHECKS", "REVIEWS", "PROTECTIONS", "POST_MERGE_CHECKS"})
)
# Profile §4.3 rule 2: these no-observation results return an error.
STORE_CODES = frozenset(
    {"ATTEMPT_CLAIM_STORE_FAILED", "LEASE_EVIDENCE_STORE_FAILED", "OBSERVATION_STORE_FAILED"}
)
# Profile §7.
LIMITATIONS: tuple[str, ...] = (
    "ACCOUNT_SECURITY_NOT_VERIFIED",
    "ARTIFACTS_UNSUPPORTED",
    "CHECK_SUITE_VISIBILITY_HORIZON",
    "EFFECTIVE_POLICY_NOT_VERIFIED",
    "INDEPENDENCE_NOT_VERIFIED",
    "NO_ACTION_AUTHORITY",
    "NO_ATOMIC_SNAPSHOT",
    "NO_BYPASS_ATTESTATION",
    "NO_INDEPENDENT_SIGNATURE",
    "NO_INTERVAL_CONTINUITY",
    "THREAD_RESOLUTION_NOT_VERIFIED",
)
# Profile §4.1 and §6: 79 pages + 16 retries = 7 x 11 + 9 x 2.
MAXIMUM_TRANSMISSIONS = sum(slot.maximum_pages + 1 for slot in SLOTS)
assert MAXIMUM_TRANSMISSIONS == 95

FAILURE_CODES = frozenset(
    {
        "REQUEST_INVALID",
        "LIVE_MODE_NOT_AUTHORIZED",
        "PRIOR_REPORT_INVALID",
        "PREFLIGHT_INVALID",
        "BUDGET_OVERFLOW",
        "SOURCE_BINDING_INVALID",
        "RESULT_INVALID",
        "STORE_FAILURE",
    }
)


class FactualCollectionError(ValidationError):
    """A cycle that returns an error, not a report. Carries one closed code."""

    def __init__(self, code: str):
        if code not in FAILURE_CODES:
            raise ValueError("unknown factual collection failure code")
        self.code = code
        super().__init__(code)


def _branch_tail(ref: str) -> str:
    return ref.removeprefix("refs/heads/")


def _validate_request_ref(value: str) -> str:
    """Profile §3: full ``refs/heads/<tail>`` with the tail validated as in
    Stage 21A section 7.1 (tail syntax only; not the base-ref allowlist)."""

    if not value.startswith("refs/heads/"):
        raise ValueError("refs must be full refs/heads/<tail> references")
    tail = _branch_tail(value)
    if not tail or any(char in tail for char in "%?#"):
        raise ValueError("ref tail contains a prohibited character")
    GitHubRepositoryProfile.valid_branch(tail)
    return value


class FactualRequest(GitHubRecord):
    profile: Literal["github-factual-request"] = "github-factual-request"
    schema_version: Literal[REQUEST_SCHEMA] = REQUEST_SCHEMA
    protocol_sha256: str = Field(pattern=HASH_PATTERN)
    repository_profile: RecordReference
    api_profile: RecordReference
    mode: Literal["fixture", "live"]
    repository_id: int = Field(gt=0)
    pull_number: int = Field(gt=0)
    base_ref: str
    head_ref: str
    expected_base_sha: str = Field(pattern=r"^[0-9a-f]{40}([0-9a-f]{24})?$")
    expected_head_sha: str = Field(pattern=r"^[0-9a-f]{40}([0-9a-f]{24})?$")
    expected_human_id: int | None = Field(default=None, gt=0)
    prior_report: RecordReference | None = None
    expected_merge_sha: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{40}([0-9a-f]{24})?$"
    )
    purpose: Literal["initial", "post_action"]
    merge_authorized: Literal[False] = False
    action_execution_allowed: Literal[False] = False

    @field_validator("base_ref", "head_ref")
    @classmethod
    def valid_refs(cls, value: str) -> str:
        return _validate_request_ref(value)

    @model_validator(mode="after")
    def purpose_is_consistent(self) -> "FactualRequest":
        initial = self.purpose == "initial"
        if (self.prior_report is None) != initial:
            raise ValueError("prior_report must be null iff purpose is initial")
        if (self.expected_merge_sha is None) != initial:
            raise ValueError("expected_merge_sha must be null iff purpose is initial")
        return self


class Step(ClosedModel):
    slot: str
    disposition: Disposition
    observation: RecordReference | None
    reason: str | None

    @model_validator(mode="after")
    def closed_nullity(self) -> "Step":
        if self.slot not in SLOT_BY_NAME:
            raise ValueError("unknown slot")
        has_observation = self.disposition in {"OBSERVED", "FAILED"}
        if (self.observation is not None) != has_observation:
            raise ValueError("observation is non-null iff OBSERVED or FAILED")
        if (self.reason is not None) != (self.disposition == "NO_OBSERVATION"):
            raise ValueError("reason is non-null iff NO_OBSERVATION")
        if self.reason is not None and self.reason not in REASON_CODES:
            raise ValueError("reason is outside the Stage 21A section 10 set")
        if self.disposition == "NOT_APPLICABLE" and self.slot not in CONDITIONAL_SLOTS:
            raise ValueError("NOT_APPLICABLE is confined to the conditional slots")
        return self


class Section(ClosedModel):
    kind: SectionKind
    coverage: Coverage
    sources: tuple[RecordReference, ...]


class Merge(ClosedModel):
    state: MergeState
    merge_sha: str | None
    actor_id: int | None
    commit_source: RecordReference | None
    parents_comparison: ParentsComparison
    actor_comparison: ActorComparison


class FactualReport(GitHubRecord):
    profile: Literal["github-factual-report"] = "github-factual-report"
    schema_version: Literal[REPORT_SCHEMA] = REPORT_SCHEMA
    request: RecordReference
    started_at: str
    completed_at: str
    stop_reason: StopReason
    stop_slot: str | None
    observations: tuple[RecordReference, ...]
    pr_before: RecordReference | None
    pr_after: RecordReference | None
    target: Target
    sections: tuple[Section, ...]
    merge: Merge
    limitations: tuple[str, ...]
    steps: tuple[Step, ...]
    merge_authorized: Literal[False] = False
    action_execution_allowed: Literal[False] = False

    @model_validator(mode="after")
    def closed_report(self) -> "FactualReport":
        if tuple(step.slot for step in self.steps) != tuple(s.name for s in SLOTS):
            raise ValueError("steps must be exactly one per slot in slot order")
        if (self.stop_slot is None) != (self.stop_reason == "NONE"):
            raise ValueError("stop_slot is null iff stop_reason is NONE")
        if self.stop_slot is not None and self.stop_slot not in SLOT_BY_NAME:
            raise ValueError("unknown stop_slot")
        if tuple(section.kind for section in self.sections) != SECTION_KINDS:
            raise ValueError("exactly five sections sorted by kind")
        if self.limitations != LIMITATIONS:
            raise ValueError("limitations must be the exact sorted section 7 list")
        step_refs = [s.observation for s in self.steps if s.observation is not None]
        if sorted(r.content_hash for r in step_refs) != sorted(
            r.content_hash for r in self.observations
        ) or len({r.content_hash for r in self.observations}) != len(self.observations):
            raise ValueError("every observation belongs to exactly one step")
        by_step = {s.slot: s for s in self.steps}
        by_slot = {slot: step.observation for slot, step in by_step.items()}
        if self.pr_before != by_slot["pr_before"] or self.pr_after != by_slot["pr_after"]:
            raise ValueError("pr_before/pr_after must equal their slot references")
        for section in self.sections:
            expected = tuple(
                by_slot[slot.name]
                for slot in SLOTS
                if slot.section == section.kind and by_slot[slot.name] is not None
            )
            if section.sources != expected:
                raise ValueError("section sources must be its slots' observations in slot order")
        # §5.2 is a biconditional: commit_source is the merge_commit observation
        # reference exactly when that Step is OBSERVED, and null in every other
        # case -- including a FAILED merge_commit, which still carries an
        # observation. Keying on the observation alone enforced one direction
        # only, so a FAILED step with a commit_source, or an OBSERVED step
        # without one, both sealed (review 0002).
        merge_step = by_step["merge_commit"]
        expected_source = (
            merge_step.observation if merge_step.disposition == "OBSERVED" else None
        )
        if self.merge.commit_source != expected_source:
            raise ValueError(
                "commit_source is the merge_commit observation iff that step is OBSERVED"
            )
        # §5.3: a null commit_source yields UNKNOWN parents, on every path.
        if expected_source is None and self.merge.parents_comparison != "UNKNOWN":
            raise ValueError("parents_comparison is UNKNOWN when commit_source is null")
        return self


def observation_reference(observation: GitHubObservation) -> RecordReference:
    return RecordReference(
        reference=f"github/observations/observation-{observation.observation_id}.json",
        content_hash=observation.content_hash,
    )


# ---------------------------------------------------------------------------
# Pure decision rules
# ---------------------------------------------------------------------------


def expected_parameters(
    slot: Slot, request: FactualRequest
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Exact Stage 21A path and query parameters for one slot (profile §4.1)."""

    spec = ENDPOINTS[slot.operation_key]
    merge_sha = request.expected_merge_sha
    path: dict[str, Any] = {
        "repository": {},
        "object_format": {},
        "base_ref": {"ref": request.base_ref},
        "pr_before": {"pull_number": request.pull_number},
        "head_checks": {"commit_sha": request.expected_head_sha},
        "head_status": {"commit_sha": request.expected_head_sha},
        "reviews": {"pull_number": request.pull_number},
        "protection": {"branch": _branch_tail(request.base_ref)},
        "branch_rules": {"branch": _branch_tail(request.base_ref)},
        "rulesets": {},
        "pr_after": {"pull_number": request.pull_number},
        "merge_commit": {"commit_sha": merge_sha},
        "merge_checks": {"commit_sha": merge_sha},
        "merge_status": {"commit_sha": merge_sha},
        "repository_after": {},
        "object_format_after": {},
    }[slot.name]
    query = dict(spec.fixed_query)
    if spec.paginated:
        query.update({"per_page": 100, "page": 1})
    return path, query


def record_result(result: GitHubReadResult) -> tuple[str, GitHubObservation | None, str | None]:
    """Profile §4.3, keyed only on what Stage 21A returned."""

    if result.observation is not None:
        if result.diagnostic is not None:
            raise FactualCollectionError("RESULT_INVALID")
        disposition = "OBSERVED" if result.observation.complete else "FAILED"
        return disposition, result.observation, None
    diagnostic = result.diagnostic
    code = diagnostic.get("reason_code") if isinstance(diagnostic, Mapping) else None
    if code is None or code not in REASON_CODES:  # rule 4
        raise FactualCollectionError("RESULT_INVALID")
    if code in STORE_CODES:  # rule 2
        raise FactualCollectionError("STORE_FAILURE")
    return "NO_OBSERVATION", None, code  # rule 3


def is_tolerated(slot: str, observation: GitHubObservation) -> bool:
    """Profile §4.4: the only FAILED result after which dispatch continues."""

    if slot not in PROTECTION_SLOTS or observation.complete:
        return False
    if observation.status_class != "4xx":
        return False
    if observation.reason_codes != ("HTTP_RESPONSE_REJECTED",):
        return False
    if not observation.pages:
        return False
    return all(
        page.rate_limit.retry_after_present is False
        and page.rate_limit.remaining is not None
        and page.rate_limit.remaining > 0
        for page in observation.pages
    )


def merge_state(projection: Mapping[str, Any]) -> str:
    """Profile §5.1 decision table over state, merged, merged_at, merged_by."""

    state = projection.get("state")
    merged = projection.get("merged")
    merged_at = projection.get("merged_at")
    merged_by = projection.get("merged_by")
    if state == "open" and merged is False and merged_at is None and merged_by is None:
        return "OPEN"
    if state == "closed" and merged is False and merged_at is None and merged_by is None:
        return "CLOSED_UNMERGED"
    if state == "closed" and merged is True and merged_at is not None:
        return "MERGED"
    return "UNKNOWN"


def derive_merge(
    *,
    pr_after: GitHubObservation | None,
    commit_source: GitHubObservation | None,
    request: FactualRequest,
) -> Merge:
    """Profile §5.1 and §5.3. ``pr_after`` is passed only when OBSERVED."""

    unknown = Merge(
        state="UNKNOWN",
        merge_sha=None,
        actor_id=None,
        commit_source=None,
        parents_comparison="UNKNOWN",
        actor_comparison="UNKNOWN",
    )
    if pr_after is None:
        return unknown
    projection = pr_after.projection
    state = merge_state(projection)
    if state != "MERGED":
        return Merge(
            state=state,
            merge_sha=None,
            actor_id=None,
            commit_source=None,
            parents_comparison="UNKNOWN",
            actor_comparison="UNKNOWN",
        )
    merge_sha = projection.get("merge_commit_sha")
    if merge_sha is not None and not isinstance(merge_sha, str):
        raise FactualCollectionError("RESULT_INVALID")
    merged_by = projection.get("merged_by")
    # §5 projects merged_by as a nullable actor object. A Mapping missing "id"
    # or "type" is a corrupted retained projection: §6 makes that an error with
    # a closed code, not an uncaught KeyError (review 0002).
    if merged_by is None:
        actor_id = actor_type = None
    elif isinstance(merged_by, Mapping) and "id" in merged_by and "type" in merged_by:
        actor_id, actor_type = merged_by["id"], merged_by["type"]
        if actor_id is not None and type(actor_id) is not int:
            raise FactualCollectionError("RESULT_INVALID")
    else:
        raise FactualCollectionError("RESULT_INVALID")

    parents = "UNKNOWN"
    if request.purpose == "post_action" and commit_source is not None:
        entries = commit_source.projection.get("parents", ())
        if not isinstance(entries, (list, tuple)) or any(
            not isinstance(entry, Mapping) or "sha" not in entry for entry in entries
        ):
            raise FactualCollectionError("RESULT_INVALID")
        found = [entry["sha"] for entry in entries]
        if len(found) == 2:
            parents = (
                "MATCH"
                if found == [request.expected_base_sha, request.expected_head_sha]
                else "DIFFERENT"
            )
        else:
            parents = "UNSUPPORTED"

    actor = "UNKNOWN"
    if (
        request.purpose == "post_action"
        and actor_id is not None
        and actor_type == "User"
        and request.expected_human_id is not None
    ):
        actor = "SAME_ACCOUNT" if actor_id == request.expected_human_id else "DIFFERENT_ACCOUNT"

    return Merge(
        state="MERGED",
        merge_sha=merge_sha,
        actor_id=actor_id,
        commit_source=None if commit_source is None else observation_reference(commit_source),
        parents_comparison=parents,
        actor_comparison=actor,
    )


def pr_matches(projection: Mapping[str, Any], request: FactualRequest) -> bool:
    """Profile §4.5 matching of one PR read."""

    head = projection.get("head") or {}
    base = projection.get("base") or {}
    return (
        base.get("ref") == _branch_tail(request.base_ref)
        and head.get("ref") == _branch_tail(request.head_ref)
        and head.get("sha") == request.expected_head_sha
    )


def verification_shows_difference(
    observation: GitHubObservation, profile: GitHubRepositoryProfile
) -> bool:
    """Profile §4.5: a 2xx verification observation whose valid retained
    projection differs from the bound repository profile."""

    if observation.status_class != "2xx":
        return False
    projection = observation.projection
    if observation.operation_key == "repository.get":
        repository_id = projection.get("repository_id")
        account_id = projection.get("account_id")
        if type(repository_id) is not int or type(account_id) is not int:
            return False
        return repository_id != profile.repository_id or account_id != profile.account_id
    if observation.operation_key == "repository_hash_algorithm.get":
        algorithm = projection.get("hash_algorithm")
        if algorithm not in {"sha1", "sha256"}:
            return False
        return algorithm != profile.git_object_format
    return False


def derive_target(
    *,
    dispositions: Mapping[str, str],
    observations: Mapping[str, GitHubObservation],
    request: FactualRequest,
    profile: GitHubRepositoryProfile,
) -> str:
    """Profile §4.5: SAME / CHANGED / UNKNOWN."""

    def observed(slot: str) -> GitHubObservation | None:
        return observations.get(slot) if dispositions.get(slot) == "OBSERVED" else None

    for slot in ("pr_before", "pr_after"):
        obs = observed(slot)
        if obs is not None and not pr_matches(obs.projection, request):
            return "CHANGED"
    for slot in VERIFICATION_SLOTS:
        obs = observations.get(slot)
        if obs is not None and verification_shows_difference(obs, profile):
            return "CHANGED"
    base = observed("base_ref")
    if (
        observed("pr_before") is not None
        and observed("pr_after") is not None
        and base is not None
        and base.projection.get("returned_ref") == request.base_ref
        and all(dispositions.get(slot) == "OBSERVED" for slot in VERIFICATION_SLOTS)
    ):
        return "SAME"
    return "UNKNOWN"


def derive_coverage(
    kind: str,
    purpose: str,
    dispositions: Mapping[str, str],
    sources: tuple,
    observations: Mapping[str, GitHubObservation],
) -> str:
    """Profile §3 ordered coverage algorithm; first match wins."""

    if kind == "POST_MERGE_CHECKS" and purpose == "initial":
        return "NOT_REQUESTED"
    if not sources:
        return "UNAVAILABLE"
    slots = [slot.name for slot in SLOTS if slot.section == kind]
    # §3 branch 3 names three conditions, each checked here rather than
    # relying on Stage 21A deriving completeness from the other two.
    if all(
        dispositions[slot] == "OBSERVED"
        and observations[slot].identity_match
        and observations[slot].pagination_complete
        for slot in slots
    ):
        return "COMPLETE_WITHIN_ENDPOINT"
    return "PARTIAL"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


# ---------------------------------------------------------------------------
# Preflight and binding
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SlotBinding:
    """One slot's externally supplied, pre-issued Stage 21A chain."""

    authorization: GitHubOperationAuthorization
    intent: GitHubOperationIntent
    attempt_claim: GitHubOperationAttemptClaim


SlotExecutor = Callable[[str, SlotBinding], GitHubReadResult]


def _validate_request(
    request: FactualRequest,
    repository_profile: GitHubRepositoryProfile,
    api_profile: GitHubFactualApiProfile,
) -> None:
    if request.mode != "fixture":
        raise FactualCollectionError("LIVE_MODE_NOT_AUTHORIZED")
    length = 40 if repository_profile.git_object_format == "sha1" else 64
    shas = [request.expected_base_sha, request.expected_head_sha]
    if request.expected_merge_sha is not None:
        shas.append(request.expected_merge_sha)
    if (
        request.protocol_sha256 != PROTOCOL_SHA256
        or not isinstance(api_profile, GitHubFactualApiProfile)
        or api_profile.response_projection_version != FACTUAL_RESPONSE_PROJECTION_VERSION
        or request.repository_profile.content_hash != repository_profile.content_hash
        or request.api_profile.content_hash != api_profile.content_hash
        or request.repository_id != repository_profile.repository_id
        or any(len(sha) != length for sha in shas)
    ):
        raise FactualCollectionError("REQUEST_INVALID")


def _validate_prior_report(request: FactualRequest, prior: "FactualReport | None", prior_request: "FactualRequest | None") -> None:
    if request.purpose == "initial":
        return
    if prior is None or prior_request is None or request.prior_report is None:
        raise FactualCollectionError("PRIOR_REPORT_INVALID")
    if (
        prior.content_hash != request.prior_report.content_hash
        or prior.request.content_hash != prior_request.content_hash
        or prior_request.purpose != "initial"
        or prior.merge.state != "MERGED"
        or prior.merge.merge_sha is None
        or prior.merge.merge_sha != request.expected_merge_sha
    ):
        raise FactualCollectionError("PRIOR_REPORT_INVALID")
    same = (
        "protocol_sha256",
        "repository_profile",
        "api_profile",
        "mode",
        "repository_id",
        "pull_number",
        "base_ref",
        "head_ref",
        "expected_base_sha",
        "expected_head_sha",
        "expected_human_id",
    )
    if any(getattr(prior_request, name) != getattr(request, name) for name in same):
        raise FactualCollectionError("PRIOR_REPORT_INVALID")


def preflight(
    *,
    request: FactualRequest,
    repository_profile: GitHubRepositoryProfile,
    api_profile: GitHubFactualApiProfile,
    bindings: Mapping[str, SlotBinding],
    attempt_claims_dir: Path,
) -> None:
    """Profile §4.6: record validity under §3, presence, bindings,
    attempt-digest non-use and the §6 budget only. No time validity."""

    required = {s.name for s in SLOTS if s.name not in CONDITIONAL_SLOTS}
    if request.purpose == "post_action":
        required |= CONDITIONAL_SLOTS
    if set(bindings) != required:
        raise FactualCollectionError("PREFLIGHT_INVALID")

    # §6: pre-admit the entire fixed plan before checking anything else. Each
    # supplied binding is admitted at the ceiling it *declares*; every slot this
    # purpose does not supply is still reserved at its plan allowance, because a
    # conditional read is reserved even when it turns out inapplicable.
    #
    # No conforming binding set can overflow: Stage 21A pins every
    # authorization's maximum_network_requests to its endpoint's page ceiling
    # plus one, and the 16-slot plan is frozen at exactly 95. This is therefore
    # defence against an injected binding Stage 21A would refuse to seal, and it
    # runs ahead of the chain check so such a binding is reported as the cap
    # enlargement it is rather than as a malformed chain. The previous form
    # compared the plan against itself (95 > 95) and could not fire even for an
    # injected binding (review 0002).
    declared = sum(
        binding.authorization.maximum_network_requests for binding in bindings.values()
    )
    reserved = sum(slot.maximum_pages + 1 for slot in SLOTS if slot.name not in bindings)
    if declared + reserved > MAXIMUM_TRANSMISSIONS:
        raise FactualCollectionError("BUDGET_OVERFLOW")

    authorization_hashes: set[str] = set()
    attempt_ids: set[str] = set()
    for name, binding in bindings.items():
        slot = SLOT_BY_NAME[name]
        path, query = expected_parameters(slot, request)
        authorization, intent, claim = binding.authorization, binding.intent, binding.attempt_claim
        chain = (
            authorization.operation_key == intent.operation_key == claim.operation_key == slot.operation_key,
            dict(authorization.path_parameters) == dict(intent.path_parameters) == path,
            dict(authorization.query_parameters) == dict(intent.query_parameters) == query,
            authorization.maximum_network_requests == slot.maximum_pages + 1,
            intent.maximum_pages == slot.maximum_pages,
            intent.authorization.content_hash == authorization.content_hash,
            claim.authorization.content_hash == authorization.content_hash,
            claim.intent.content_hash == intent.content_hash,
            claim.attempt_id == intent.attempt_id,
            authorization.repository_profile.content_hash == repository_profile.content_hash,
            authorization.api_profile.content_hash == api_profile.content_hash,
            intent.api_profile.content_hash == api_profile.content_hash,
            authorization.repository_id == repository_profile.repository_id,
        )
        if not all(chain):
            raise FactualCollectionError("PREFLIGHT_INVALID")
        if authorization.content_hash in authorization_hashes or intent.attempt_id in attempt_ids:
            raise FactualCollectionError("PREFLIGHT_INVALID")
        if attempt_claim_path(attempt_claims_dir, intent.attempt_id).exists():
            raise FactualCollectionError("PREFLIGHT_INVALID")
        authorization_hashes.add(authorization.content_hash)
        attempt_ids.add(intent.attempt_id)


def _check_source_binding(
    slot: Slot,
    observation: GitHubObservation,
    binding: SlotBinding,
    request: FactualRequest,
    repository_profile: GitHubRepositoryProfile,
    api_profile: GitHubFactualApiProfile,
) -> None:
    """Profile §4.5: a wrong source binding is an error, not PARTIAL."""

    path, query = expected_parameters(slot, request)
    bound = (
        observation.operation_key == slot.operation_key,
        dict(observation.path_parameters) == path,
        dict(observation.query_parameters) == query,
        observation.repository_id == repository_profile.repository_id,
        observation.repository_profile.content_hash == repository_profile.content_hash,
        observation.api_profile.content_hash == api_profile.content_hash,
        observation.authorization.content_hash == binding.authorization.content_hash,
        observation.intent.content_hash == binding.intent.content_hash,
        observation.attempt_claim.content_hash == binding.attempt_claim.content_hash,
        observation.attempt_id == binding.intent.attempt_id,
        observation.response_projection_version == FACTUAL_RESPONSE_PROJECTION_VERSION,
    )
    if not all(bound):
        raise FactualCollectionError("SOURCE_BINDING_INVALID")
    if slot.name == "merge_commit":
        sha = observation.projection.get("sha")
        if sha is not None and sha != request.expected_merge_sha:
            raise FactualCollectionError("SOURCE_BINDING_INVALID")


# ---------------------------------------------------------------------------
# Coordinator
# ---------------------------------------------------------------------------


def collect_factual_report(
    *,
    request: FactualRequest,
    request_reference: RecordReference,
    repository_profile: GitHubRepositoryProfile,
    api_profile: GitHubFactualApiProfile,
    bindings: Mapping[str, SlotBinding],
    executor: SlotExecutor,
    attempt_claims_dir: Path,
    clock: Callable[[], str],
    prior_report: FactualReport | None = None,
    prior_request: FactualRequest | None = None,
) -> FactualReport:
    """Run one fixture-only factual cycle and return a sealed report.

    Raises ``FactualCollectionError`` for every path that the profile says
    returns an error rather than a report. Already durable Stage 21A evidence
    is never deleted by this function.
    """

    if request_reference.content_hash != request.content_hash:
        raise FactualCollectionError("REQUEST_INVALID")
    _validate_request(request, repository_profile, api_profile)
    _validate_prior_report(request, prior_report, prior_request)
    preflight(
        request=request,
        repository_profile=repository_profile,
        api_profile=api_profile,
        bindings=bindings,
        attempt_claims_dir=attempt_claims_dir,
    )

    dispositions: dict[str, str] = {}
    observations: dict[str, GitHubObservation] = {}
    reasons: dict[str, str] = {}
    stop_reason, stop_slot = "NONE", None
    stopped = False
    # §5.2 linkage outcome for the conditional slots in post_action, set only
    # after an OBSERVED pr_after: None (dispatch them), NOT_APPLICABLE (null
    # merge_sha) or NOT_ATTEMPTED (differing merge_sha).
    linkage_skip: str | None = None

    started_at = clock()
    completed_at = started_at
    for slot in SLOTS:
        if slot.name in CONDITIONAL_SLOTS:
            if request.purpose == "initial":
                # §5.2: NOT_APPLICABLE on every path in an initial report.
                dispositions[slot.name] = "NOT_APPLICABLE"
                continue
            if linkage_skip is not None:
                dispositions[slot.name] = linkage_skip
                continue
        if stopped:
            # §4.4: remaining slots NOT_ATTEMPTED; in post_action this includes
            # the conditional slots when pr_after was not OBSERVED (§5.2).
            dispositions[slot.name] = "NOT_ATTEMPTED"
            continue

        binding = bindings[slot.name]
        result = executor(slot.name, binding)
        completed_at = clock()
        disposition, observation, reason = record_result(result)  # §4.3
        dispositions[slot.name] = disposition
        if observation is not None:
            _check_source_binding(
                slot, observation, binding, request, repository_profile, api_profile
            )
            observations[slot.name] = observation
        if reason is not None:
            reasons[slot.name] = reason

        # §4.4: continue after OBSERVED or a tolerated FAILED; otherwise stop.
        tolerated = (
            disposition == "FAILED"
            and observation is not None
            and is_tolerated(slot.name, observation)
        )
        if disposition != "OBSERVED" and not tolerated:
            stopped = True
            if stop_reason == "NONE":
                stop_reason, stop_slot = "OPERATION_FAILURE", slot.name
            continue

        if slot.name == "pr_after" and request.purpose == "post_action":
            # §5.2: only reached with pr_after OBSERVED.
            state = merge_state(observation.projection)
            merge_sha = (
                observation.projection.get("merge_commit_sha") if state == "MERGED" else None
            )
            if merge_sha is None:
                linkage_skip = "NOT_APPLICABLE"
            elif merge_sha != request.expected_merge_sha:
                linkage_skip = "NOT_ATTEMPTED"
            if linkage_skip is not None and stop_reason == "NONE":
                stop_reason, stop_slot = "LINKAGE_CHANGED", "pr_after"

    steps = tuple(
        Step(
            slot=slot.name,
            disposition=dispositions[slot.name],
            observation=(
                observation_reference(observations[slot.name])
                if dispositions[slot.name] in {"OBSERVED", "FAILED"}
                else None
            ),
            reason=reasons.get(slot.name) if dispositions[slot.name] == "NO_OBSERVATION" else None,
        )
        for slot in SLOTS
    )

    def order_key(obs: GitHubObservation) -> tuple[str, str, str]:
        params = _canonical(
            {"path": dict(obs.path_parameters), "query": dict(obs.query_parameters)}
        )
        return obs.operation_key, params, obs.content_hash

    ordered = tuple(
        observation_reference(obs) for obs in sorted(observations.values(), key=order_key)
    )

    sections = []
    for kind in SECTION_KINDS:
        sources = tuple(
            observation_reference(observations[slot.name])
            for slot in SLOTS
            if slot.section == kind and slot.name in observations
        )
        sections.append(
            Section(
                kind=kind,
                coverage=derive_coverage(
                    kind, request.purpose, dispositions, sources, observations
                ),
                sources=sources,
            )
        )

    pr_after_obs = observations["pr_after"] if dispositions.get("pr_after") == "OBSERVED" else None
    commit_obs = (
        observations["merge_commit"] if dispositions.get("merge_commit") == "OBSERVED" else None
    )
    merge = derive_merge(pr_after=pr_after_obs, commit_source=commit_obs, request=request)
    target = derive_target(
        dispositions=dispositions,
        observations=observations,
        request=request,
        profile=repository_profile,
    )

    return seal_record(
        FactualReport,
        {
            "profile": "github-factual-report",
            "schema_version": REPORT_SCHEMA,
            "request": request_reference,
            "started_at": started_at,
            "completed_at": completed_at,
            "stop_reason": stop_reason,
            "stop_slot": stop_slot,
            "observations": ordered,
            "pr_before": next(s.observation for s in steps if s.slot == "pr_before"),
            "pr_after": next(s.observation for s in steps if s.slot == "pr_after"),
            "target": target,
            "sections": tuple(sections),
            "merge": merge,
            "limitations": LIMITATIONS,
            "steps": steps,
            "created_at": clock(),
            "authority_effect": "none",
            "decision_effect": "none",
            "membership_effect": "none",
            "production_use_allowed": False,
            "merge_authorized": False,
            "action_execution_allowed": False,
        },
    )


def persist_factual_report(root: Path, report: FactualReport) -> Path:
    """Write the sealed report immutably; a conflict or storage failure is an
    error, never an overwrite."""

    digest = report.content_hash.removeprefix("sha256:")
    path = Path(root) / "github" / "factual-reports" / f"report-{digest}.json"
    try:
        written, _created = write_durable_record(path, report)
    except Exception as exc:  # storage failure returns an error, not a report
        raise FactualCollectionError("STORE_FAILURE") from exc
    return written
