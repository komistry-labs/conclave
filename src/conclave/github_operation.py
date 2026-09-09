"""Governed Stage 21A coordinator for one read-only GitHub operation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Callable

from .github_foundation import (
    CredentialResolutionRequest,
    GitHubApiProfile,
    GitHubCredentialLeaseProvider,
    GitHubCredentialProviderKey,
    GitHubFoundationFailure,
    GitHubObservation,
    GitHubOperationAttemptClaim,
    GitHubOperationAuthorization,
    GitHubOperationIntent,
    GitHubOperationExecutionFailure,
    GitHubRepositoryProfile,
    GitHubTransport,
    ENDPOINTS,
    PermissionEnvelope,
    create_failure_observation,
    create_success_observation,
    prepare_credential_lease,
    project_github_responses,
    run_github_transport,
    safe_failure_diagnostic,
    write_attempt_claim,
    write_durable_record,
)
from .ledger import record_event
from .workspace import Workspace


@dataclass(frozen=True)
class GitHubReadResult:
    """Safe result surface: one immutable observation or one local diagnostic."""

    observation: GitHubObservation | None
    observation_path: Path | None
    ledger_event_created: bool
    diagnostic: dict[str, str] | None


def _record_path(workspace: Workspace, reference: str) -> Path:
    relative = PurePosixPath(reference)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise GitHubFoundationFailure("PROFILE_INVALID")
    if relative.parts[0] != "github" or relative.suffix != ".json":
        raise GitHubFoundationFailure("PROFILE_INVALID")
    root = workspace.root.resolve()
    path = workspace.root.joinpath(*relative.parts).resolve()
    if path == root or root not in path.parents:
        raise GitHubFoundationFailure("PROFILE_INVALID")
    return path


def _validate_chain(
    *,
    workspace: Workspace,
    repository_profile: GitHubRepositoryProfile,
    api_profile: GitHubApiProfile,
    provider_key: GitHubCredentialProviderKey,
    authorization: GitHubOperationAuthorization,
    intent: GitHubOperationIntent,
    attempt_claim: GitHubOperationAttemptClaim,
    request: CredentialResolutionRequest,
    now: datetime,
) -> None:
    principal = workspace.load_config().get("principal")
    instant = now.replace(tzinfo=None)
    if not principal or authorization.authorized_principal != principal:
        raise GitHubFoundationFailure("AUTHORIZATION_INVALID")
    if instant < datetime.strptime(authorization.issued_at, "%Y-%m-%dT%H:%M:%SZ"):
        raise GitHubFoundationFailure("AUTHORIZATION_INVALID")
    if instant > datetime.strptime(authorization.expires_at, "%Y-%m-%dT%H:%M:%SZ"):
        raise GitHubFoundationFailure("AUTHORIZATION_EXPIRED")
    expected = (
        authorization.repository_profile.content_hash
        == repository_profile.content_hash,
        authorization.api_profile.content_hash == api_profile.content_hash,
        intent.authorization.content_hash == authorization.content_hash,
        intent.repository_profile.content_hash == repository_profile.content_hash,
        intent.api_profile.content_hash == api_profile.content_hash,
        attempt_claim.authorization.content_hash == authorization.content_hash,
        attempt_claim.intent.content_hash == intent.content_hash,
        attempt_claim.repository_profile.content_hash
        == repository_profile.content_hash,
        attempt_claim.api_profile.content_hash == api_profile.content_hash,
        request.authorization_hash == authorization.content_hash,
        request.intent_hash == intent.content_hash,
        request.provider_key_hash == provider_key.content_hash,
    )
    identifiers = (
        authorization.repository_id
        == repository_profile.repository_id
        == intent.repository_id
        == attempt_claim.repository_id
        == request.repository_id,
        authorization.account_id
        == repository_profile.account_id
        == intent.account_id
        == attempt_claim.account_id
        == request.account_id,
        repository_profile.expected_app_id
        == intent.app_id
        == attempt_claim.app_id
        == request.app_id,
        repository_profile.expected_installation_id
        == intent.installation_id
        == attempt_claim.installation_id
        == request.installation_id,
        authorization.operation_key
        == intent.operation_key
        == attempt_claim.operation_key,
        authorization.path_parameters == intent.path_parameters,
        authorization.query_parameters == intent.query_parameters,
        authorization.maximum_network_requests == intent.maximum_network_requests,
    )
    if not all(expected) or not all(identifiers):
        raise GitHubFoundationFailure("LEASE_BINDING_MISMATCH")
    endpoint = ENDPOINTS[intent.operation_key]
    permission_values = {
        "metadata": "read",
        "contents": "none",
        "pull_requests": "none",
        "checks": "none",
        "statuses": "none",
        "administration": "none",
    }
    if endpoint.additional_permission is not None:
        permission_values[endpoint.additional_permission] = "read"
    required_permissions = PermissionEnvelope.model_validate(permission_values)
    if (
        intent.operation_key not in repository_profile.read_operations
        or request.permission_envelope != required_permissions
        or not request.permission_envelope.read_keys().issubset(
            repository_profile.permission_ceiling.read_keys()
        )
        or request.api_version != api_profile.api_version
        or request.intent_expiry != intent.not_after
    ):
        raise GitHubFoundationFailure("LEASE_PERMISSION_MISMATCH")
    if instant > datetime.strptime(intent.not_after, "%Y-%m-%dT%H:%M:%SZ"):
        raise GitHubFoundationFailure("AUTHORIZATION_EXPIRED")


def _observation_path(workspace: Workspace, observation: GitHubObservation) -> Path:
    return (
        workspace.github_observations_dir
        / f"observation-{observation.observation_id}.json"
    )


def _record_observation_event(
    workspace: Workspace, observation: GitHubObservation
) -> bool:
    _event, created = record_event(
        workspace,
        event_type="github_read_observation_recorded",
        actor="conclave",
        authority_level="system",
        subject_refs=[observation.observation_id, observation.attempt_id],
        artifact_hashes={
            "observation": observation.content_hash,
            "repository_profile": observation.repository_profile.content_hash,
            "api_profile": observation.api_profile.content_hash,
            "authorization": observation.authorization.content_hash,
            "intent": observation.intent.content_hash,
            "attempt_claim": observation.attempt_claim.content_hash,
            "lease_evidence": observation.lease_evidence.content_hash,
        },
        payload={
            "operation_key": observation.operation_key,
            "complete": observation.complete,
            "pagination_complete": observation.pagination_complete,
            "identity_match": observation.identity_match,
            "reason_codes": list(observation.reason_codes),
            "authority_effect": "none",
            "decision_effect": "none",
            "membership_effect": "none",
            "merge_authorized": False,
            "action_execution_allowed": False,
        },
    )
    return created


def execute_github_read(
    *,
    workspace: Workspace,
    repository_profile: GitHubRepositoryProfile,
    api_profile: GitHubApiProfile,
    provider_key: GitHubCredentialProviderKey,
    authorization: GitHubOperationAuthorization,
    intent: GitHubOperationIntent,
    attempt_claim: GitHubOperationAttemptClaim,
    request: CredentialResolutionRequest,
    provider: GitHubCredentialLeaseProvider,
    transport: GitHubTransport,
    observation_id: str,
    clock: Callable[[], datetime],
    monotonic: Callable[[], float],
    sleeper: Callable[[float], None] = lambda _: None,
) -> GitHubReadResult:
    """Execute exactly one fully bound Stage 21A operation and seal its evidence."""

    lease = None
    lease_evidence = None
    responses = ()
    try:
        _validate_chain(
            workspace=workspace,
            repository_profile=repository_profile,
            api_profile=api_profile,
            provider_key=provider_key,
            authorization=authorization,
            intent=intent,
            attempt_claim=attempt_claim,
            request=request,
            now=clock(),
        )
        records = (
            (authorization.repository_profile.reference, repository_profile),
            (authorization.api_profile.reference, api_profile),
            (repository_profile.provider_key_reference, provider_key),
            (intent.authorization.reference, authorization),
            (attempt_claim.intent.reference, intent),
        )
        for reference, record in records:
            write_durable_record(_record_path(workspace, reference), record)
        claim_path = write_attempt_claim(
            workspace.github_attempt_claims_dir, attempt_claim
        )
        lease = prepare_credential_lease(
            provider=provider,
            request=request,
            repository_profile=repository_profile,
            api_profile=api_profile,
            provider_key=provider_key,
            authorization=authorization,
            intent=intent,
            attempt_claim=attempt_claim,
            attempt_claim_reference=claim_path.relative_to(workspace.root).as_posix(),
            authorization_reference=intent.authorization.reference,
            intent_reference=attempt_claim.intent.reference,
            evidence_directory=workspace.github_lease_evidence_dir,
            clock=clock,
        )
        lease_evidence = lease.evidence
        responses = run_github_transport(
            lease=lease,
            transport=transport,
            repository_profile=repository_profile,
            api_profile=api_profile,
            intent=intent,
            clock=clock,
            monotonic=monotonic,
            sleeper=sleeper,
        )
        lease = None  # run_github_transport always closes it
        bundle = project_github_responses(
            responses=responses,
            operation_key=intent.operation_key,
            repository=repository_profile,
            intent=intent,
            maximum_page_bytes=api_profile.maximum_response_body_bytes_per_page,
        )
        observation = create_success_observation(
            observation_id=observation_id,
            observed_at=clock().replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
            responses=responses,
            repository_profile=repository_profile,
            api_profile=api_profile,
            authorization=authorization,
            intent=intent,
            attempt_claim=attempt_claim,
            lease_evidence=lease_evidence,
            projection=bundle.projection,
            page_item_counts=bundle.page_item_counts,
        )
    except GitHubFoundationFailure as exc:
        if lease_evidence is None:
            return GitHubReadResult(
                observation=None,
                observation_path=None,
                ledger_event_created=False,
                diagnostic=safe_failure_diagnostic(
                    operation_key=intent.operation_key,
                    reason_code=exc.reason_code,
                ),
            )
        failure_responses = (
            exc.responses
            if isinstance(exc, GitHubOperationExecutionFailure)
            else responses
        )
        transmitted = (
            exc.transmitted
            if isinstance(exc, GitHubOperationExecutionFailure)
            else bool(failure_responses)
        )
        observation = create_failure_observation(
            observation_id=observation_id,
            observed_at=clock().replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
            reason_codes=(exc.reason_code,),
            status_class="transport" if transmitted else "none",
            responses=failure_responses,
            repository_profile=repository_profile,
            api_profile=api_profile,
            authorization=authorization,
            intent=intent,
            attempt_claim=attempt_claim,
            lease_evidence=lease_evidence,
        )
    finally:
        if lease is not None:
            lease.close()

    path, _ = write_durable_record(
        _observation_path(workspace, observation), observation
    )
    return GitHubReadResult(
        observation=observation,
        observation_path=path,
        ledger_event_created=_record_observation_event(workspace, observation),
        diagnostic=None,
    )
