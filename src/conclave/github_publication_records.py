"""Closed governing records for the Stage 21B publication evaluator."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
import re
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .github_foundation import (
    CLAIMS_SIGNATURE_DOMAIN,
    ENDPOINTS,
    CredentialLeaseEvidence,
    GitHubApiProfile,
    GitHubCredentialProviderKey,
    GitHubObservation,
    GitHubOperationAttemptClaim,
    GitHubOperationAuthorization,
    GitHubOperationIntent,
    GitHubRecord,
    GitHubRepositoryProfile,
    PermissionEnvelope,
    RecordReference,
    _verify_signature,
)
from .github_publication import (
    BaseTreeClosure,
    canonical_github_ref_target,
    BaseTreeIdentityObservation,
    ProposalBlob,
    PublicationRepositoryExtension,
    RecursiveTreeAttemptClaim,
    RecursiveTreeAuthorization,
    RecursiveTreeIntent,
    RecursiveTreeLeaseEvidence,
    RecursiveTreeObservation,
    validate_head_ref,
    STAGE_21B_PROTOCOL_HASH,
    INCREMENT_21_PROTOCOL_HASH,
    STAGE_21A_PROTOCOL_HASH,
    STAGE_21B_ERRATUM_HASH,
)
from .identity import ClosedModel
from .models import TaskPacket
from .handoff import HandoffPacket
from .scope import ScopeReview
from .taskpacket import verify_content_hash as verify_task_hash
from .handoff import verify_handoff_content_hash
from .scope import verify_review_content_hash

HASH = r"^sha256:[0-9a-f]{64}$"
PUBLICATION_ATTEMPT = r"^publication:sha256:[0-9a-f]{64}$"
PUBLICATION_LEASE_CLAIMS_DOMAIN = b"CONCLAVE-GITHUB-PUBLICATION-LEASE-CLAIMS-V1\0"


class ProposalFile(ProposalBlob):
    mode: Literal["100644"] = "100644"
    artifact: RecordReference


def proposal_aggregate_hash(files: tuple[ProposalFile, ...]) -> str:
    projection = [
        {
            "path": item.path,
            "mode": item.mode,
            "byte_count": item.byte_count,
            "content_sha256": item.content_sha256,
            "blob_oid": item.blob_oid,
            "artifact": item.artifact.model_dump(mode="json"),
        }
        for item in files
    ]
    payload = json.dumps(
        projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return (
        "sha256:"
        + hashlib.sha256(b"CONCLAVE-GITHUB-PROPOSAL-V1\0" + payload).hexdigest()
    )


def publication_attempt_id(
    *,
    authorization: "PublicationAuthorization",
    manifest: "ProposalManifest",
    plan: "PublicationPlan",
) -> str:
    payload = json.dumps(
        {
            "authorization": authorization.model_dump(mode="json"),
            "manifest": manifest.model_dump(mode="json"),
            "plan_content_hash": plan.content_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return (
        "publication:sha256:"
        + hashlib.sha256(
            b"CONCLAVE-GITHUB-PUBLICATION-ATTEMPT-V1\0" + payload
        ).hexdigest()
    )


class CommitIdentity(ClosedModel):
    name: str = Field(min_length=1, max_length=128)
    email: str = Field(min_length=3, max_length=254)
    timestamp: str

    @model_validator(mode="after")
    def safe_identity(self) -> "CommitIdentity":
        datetime.strptime(self.timestamp, "%Y-%m-%dT%H:%M:%SZ")
        if any(c in self.name + self.email for c in "\r\n<>") or "@" not in self.email:
            raise ValueError("commit identity is unsafe")
        return self


class ProposalManifest(GitHubRecord):
    profile: Literal["github-proposal-manifest"] = "github-proposal-manifest"
    schema_version: Literal["github-proposal-manifest/0.1.0"] = (
        "github-proposal-manifest/0.1.0"
    )
    manifest_id: str = Field(min_length=1, max_length=128)
    repository_profile: RecordReference
    api_profile: RecordReference
    repository_extension: RecordReference
    repository_id: int = Field(gt=0)
    account_id: int = Field(gt=0)
    owner: str = Field(min_length=1, max_length=39)
    repository: str = Field(min_length=1, max_length=100)
    task_packet: RecordReference
    handoff: RecordReference
    scope_review: RecordReference
    base_observation: RecordReference
    base_tree_closure: RecordReference
    branch_rules_observation: RecordReference
    ruleset_observation: RecordReference
    base_ref: str = Field(min_length=12, max_length=255)
    base_commit_oid: str
    base_tree_oid: str
    head_ref: str
    object_format: Literal["sha1", "sha256"]
    files: tuple[ProposalFile, ...] = Field(min_length=1, max_length=64)
    allowed_paths: tuple[str, ...] = Field(min_length=1, max_length=64)
    aggregate_byte_count: int = Field(gt=0, le=8 * 1024 * 1024)
    aggregate_manifest_hash: str = Field(pattern=HASH)
    commit_message: RecordReference
    commit_message_byte_count: int = Field(gt=0, le=4 * 1024)
    commit_identity: CommitIdentity
    commit_identity_artifact: RecordReference
    pull_request_title: RecordReference
    pull_request_title_byte_count: int = Field(gt=0, le=256)
    pull_request_body: RecordReference
    pull_request_body_byte_count: int = Field(ge=0, le=64 * 1024)
    proposal_tree_oid: str
    proposal_commit_oid: str
    proposal_only: Literal[True] = True
    merge_authorized: Literal[False] = False
    action_execution_allowed: Literal[False] = False

    @field_validator("head_ref")
    @classmethod
    def exact_head_ref(cls, value: str) -> str:
        return validate_head_ref(value)

    @field_validator("base_ref")
    @classmethod
    def canonical_base_ref(cls, value: str) -> str:
        canonical_github_ref_target(value)
        return value

    @field_validator("owner")
    @classmethod
    def safe_owner(cls, value: str) -> str:
        if (
            re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", value)
            is None
        ):
            raise ValueError("owner is not a canonical GitHub login")
        return value

    @field_validator("repository")
    @classmethod
    def safe_repository(cls, value: str) -> str:
        if re.fullmatch(
            r"[A-Za-z0-9_.-]{1,100}", value
        ) is None or value.lower().endswith(".git"):
            raise ValueError("repository is not canonical")
        return value

    @model_validator(mode="after")
    def exact_manifest(self) -> "ProposalManifest":
        paths = tuple(item.path for item in self.files)
        if paths != tuple(sorted(set(paths))) or self.allowed_paths != paths:
            raise ValueError(
                "manifest paths and accepted scope must be exact and sorted"
            )
        if self.aggregate_byte_count != sum(item.byte_count for item in self.files):
            raise ValueError("aggregate byte count mismatch")
        if self.aggregate_manifest_hash != proposal_aggregate_hash(self.files):
            raise ValueError("aggregate manifest hash mismatch")
        oid_length = 40 if self.object_format == "sha1" else 64
        import re

        for oid in (
            self.base_commit_oid,
            self.base_tree_oid,
            self.proposal_tree_oid,
            self.proposal_commit_oid,
        ):
            if re.fullmatch(rf"[0-9a-f]{{{oid_length}}}", oid) is None:
                raise ValueError("manifest OID does not match object format")
        return self


class PublicationAuthorization(GitHubRecord):
    profile: Literal["github-publication-authorization"] = (
        "github-publication-authorization"
    )
    schema_version: Literal["github-publication-authorization/0.1.0"] = (
        "github-publication-authorization/0.1.0"
    )
    authorization_id: str = Field(min_length=1, max_length=128)
    authorized_principal: str = Field(min_length=1, max_length=256)
    issued_at: str
    expires_at: str
    purpose: str = Field(min_length=1, max_length=512)
    protocol_hash: Literal[STAGE_21B_PROTOCOL_HASH] = STAGE_21B_PROTOCOL_HASH
    increment_21_hash: Literal[INCREMENT_21_PROTOCOL_HASH] = INCREMENT_21_PROTOCOL_HASH
    stage_21a_hash: Literal[STAGE_21A_PROTOCOL_HASH] = STAGE_21A_PROTOCOL_HASH
    erratum_hash: Literal[STAGE_21B_ERRATUM_HASH] = STAGE_21B_ERRATUM_HASH
    manifest: RecordReference
    rate_observation: RecordReference
    repository_profile: RecordReference
    api_profile: RecordReference
    task_packet: RecordReference
    handoff: RecordReference
    scope_review: RecordReference
    base_observation: RecordReference
    base_tree_closure: RecordReference
    base_tree_source_observation: RecordReference
    branch_rules_observation: RecordReference
    ruleset_observation: RecordReference
    repository_id: int = Field(gt=0)
    account_id: int = Field(gt=0)
    app_id: int = Field(gt=0)
    installation_id: int = Field(gt=0)
    provider_id: str = Field(min_length=1, max_length=64)
    provider_version: str = Field(min_length=1, max_length=64)
    provider_key: RecordReference
    provider_public_key_sha256: str = Field(pattern=HASH)
    api_version: str = Field(min_length=1, max_length=32)
    resource_bucket: str = Field(min_length=1, max_length=64)
    base_ref: str
    head_ref: str
    base_commit_oid: str
    base_tree_oid: str
    proposal_tree_oid: str
    proposal_commit_oid: str
    allowed_paths: tuple[str, ...]
    aggregate_proposal_hash: str = Field(pattern=HASH)
    commit_message_hash: str = Field(pattern=HASH)
    commit_message_byte_count: int = Field(gt=0, le=4 * 1024)
    pull_request_title_hash: str = Field(pattern=HASH)
    pull_request_title_byte_count: int = Field(gt=0, le=256)
    pull_request_body_hash: str = Field(pattern=HASH)
    pull_request_body_byte_count: int = Field(ge=0, le=64 * 1024)
    publication_mechanism: Literal["github_rest_git_database"] = (
        "github_rest_git_database"
    )
    permission_metadata: Literal["read"] = "read"
    permission_contents: Literal["write"] = "write"
    permission_pull_requests: Literal["write"] = "write"
    every_other_permission: Literal["none"] = "none"
    maximum_publication_transactions: Literal[1] = 1
    maximum_branch_creations: Literal[1] = 1
    maximum_pull_requests: Literal[1] = 1
    maximum_mutation_requests: int = Field(ge=5, le=68)
    maximum_total_requests: int = Field(ge=16, le=142)
    automatic_mutation_retries: Literal[0] = 0
    maintainer_can_modify: Literal[False] = False
    draft: Literal[False] = False
    merge_requested: Literal[False] = False
    merge_authorized: Literal[False] = False
    authority_effect: Literal["github_publish_proposal_only"] = (
        "github_publish_proposal_only"  # type: ignore[assignment]
    )

    @model_validator(mode="after")
    def bounded_lifetime(self) -> "PublicationAuthorization":
        issued = datetime.strptime(self.issued_at, "%Y-%m-%dT%H:%M:%SZ")
        expires = datetime.strptime(self.expires_at, "%Y-%m-%dT%H:%M:%SZ")
        if not 1 <= (expires - issued).total_seconds() <= 900:
            raise ValueError("authorization lifetime is outside 1..900 seconds")
        return self


class PublicationPlan(GitHubRecord):
    profile: Literal["github-publication-plan"] = "github-publication-plan"
    schema_version: Literal["github-publication-plan/0.1.0"] = (
        "github-publication-plan/0.1.0"
    )
    plan_id: str = Field(min_length=1, max_length=128)
    authorization: RecordReference
    manifest: RecordReference
    rate_observation: RecordReference
    upstream_records: tuple[RecordReference, ...] = Field(min_length=17, max_length=17)
    rate_scope_hash: str = Field(pattern=HASH)
    blob_request_hashes: tuple[str, ...] = Field(min_length=1, max_length=64)
    expected_blob_oids: tuple[str, ...] = Field(min_length=1, max_length=64)
    tree_request_hash: str = Field(pattern=HASH)
    commit_request_hash: str = Field(pattern=HASH)
    ref_request_hash: str = Field(pattern=HASH)
    pull_request_request_hash: str = Field(pattern=HASH)
    ordered_endpoint_plan: tuple[str, ...] = Field(min_length=16, max_length=142)
    ordered_request_hashes: tuple[str, ...] = Field(min_length=16, max_length=142)
    expected_tree_oid: str
    expected_commit_oid: str
    base_ref: str
    head_ref: str
    maximum_total_requests: int = Field(ge=16, le=142)
    automatic_mutation_retries: Literal[0] = 0

    @model_validator(mode="after")
    def exact_count(self) -> "PublicationPlan":
        if len(self.ordered_request_hashes) != self.maximum_total_requests:
            raise ValueError("plan request count mismatch")
        if any(
            re.fullmatch(HASH, value) is None for value in self.ordered_request_hashes
        ):
            raise ValueError("plan contains an invalid request hash")
        return self


class OperationIntentV2(GitHubRecord):
    profile: Literal["github-operation-intent"] = "github-operation-intent"
    schema_version: Literal["github-operation-intent/0.2.0"] = (
        "github-operation-intent/0.2.0"
    )
    intent_id: str = Field(min_length=1, max_length=128)
    authorization: RecordReference
    manifest: RecordReference
    plan: RecordReference
    rate_observation: RecordReference
    upstream_records: tuple[RecordReference, ...] = Field(min_length=17, max_length=17)
    attempt_id: str = Field(pattern=PUBLICATION_ATTEMPT)
    ordered_endpoint_plan: tuple[str, ...] = Field(min_length=16, max_length=142)
    canonical_request_hashes: tuple[str, ...] = Field(min_length=16, max_length=142)
    rate_scope_hash: str = Field(pattern=HASH)
    maximum_mutation_requests: int = Field(ge=5, le=68)
    maximum_total_requests: int = Field(ge=16, le=142)
    automatic_mutation_retries: Literal[0] = 0
    not_after: str


class PublicationIntent(GitHubRecord):
    profile: Literal["github-publication-intent"] = "github-publication-intent"
    schema_version: Literal["github-publication-intent/0.1.0"] = (
        "github-publication-intent/0.1.0"
    )
    publication_intent_id: str = Field(min_length=1, max_length=128)
    authorization: RecordReference
    manifest: RecordReference
    plan: RecordReference
    operation_intent: RecordReference
    rate_observation: RecordReference
    attempt_id: str = Field(pattern=PUBLICATION_ATTEMPT)
    upstream_records: tuple[RecordReference, ...] = Field(min_length=17, max_length=17)
    rate_scope_hash: str = Field(pattern=HASH)
    blob_request_hashes: tuple[str, ...] = Field(min_length=1, max_length=64)
    expected_blob_oids: tuple[str, ...] = Field(min_length=1, max_length=64)
    tree_request_hash: str = Field(pattern=HASH)
    commit_request_hash: str = Field(pattern=HASH)
    ref_request_hash: str = Field(pattern=HASH)
    pull_request_request_hash: str = Field(pattern=HASH)
    base_commit_oid: str
    ordered_endpoint_plan: tuple[str, ...] = Field(min_length=16, max_length=142)
    maximum_mutation_requests: int = Field(ge=5, le=68)
    maximum_total_requests: int = Field(ge=16, le=142)
    automatic_mutation_retries: Literal[0] = 0
    state: Literal["prepared"] = "prepared"
    exact_request_hashes: tuple[str, ...] = Field(min_length=16, max_length=142)
    expected_tree_oid: str
    expected_commit_oid: str
    base_ref: str
    head_ref: str


class PublicationAttemptClaim(GitHubRecord):
    profile: Literal["github-publication-attempt-claim"] = (
        "github-publication-attempt-claim"
    )
    schema_version: Literal["github-publication-attempt-claim/0.1.0"] = (
        "github-publication-attempt-claim/0.1.0"
    )
    attempt_id: str = Field(pattern=PUBLICATION_ATTEMPT)
    authorization: RecordReference
    manifest: RecordReference
    plan: RecordReference
    operation_intent: RecordReference
    publication_intent: RecordReference
    rate_observation: RecordReference
    upstream_records: tuple[RecordReference, ...] = Field(min_length=17, max_length=17)
    provider_key: RecordReference
    provider_public_key_sha256: str = Field(pattern=HASH)
    state: Literal["claimed"] = "claimed"


class PublicationLeaseClaims(ClosedModel):
    """Provider-signed, credential-free proof of one fixture capability.

    These claims deliberately contain no token or credential material.  They
    authenticate the exact write-shaped transaction that the offline fixture
    evaluates, while ``fixture_loopback_only`` and ``live_use_allowed`` make it
    impossible to reinterpret the claims as authority for a live transport.
    """

    schema_version: Literal["github-publication-lease-claims/0.1.0"] = (
        "github-publication-lease-claims/0.1.0"
    )
    provider_id: str = Field(min_length=1, max_length=64)
    provider_version: str = Field(min_length=1, max_length=64)
    key_id: str = Field(min_length=1, max_length=128)
    lease_id: str = Field(min_length=1, max_length=128)
    capability_class: Literal["fixture_only_github_publication"] = (
        "fixture_only_github_publication"
    )
    repository_profile_hash: str = Field(pattern=HASH)
    api_profile_hash: str = Field(pattern=HASH)
    authorization_hash: str = Field(pattern=HASH)
    plan_hash: str = Field(pattern=HASH)
    operation_intent_hash: str = Field(pattern=HASH)
    publication_intent_hash: str = Field(pattern=HASH)
    attempt_claim_hash: str = Field(pattern=HASH)
    attempt_id: str = Field(pattern=PUBLICATION_ATTEMPT)
    rate_observation_hash: str = Field(pattern=HASH)
    rate_scope_hash: str = Field(pattern=HASH)
    app_id: int = Field(gt=0)
    installation_id: int = Field(gt=0)
    account_id: int = Field(gt=0)
    repository_ids: tuple[int, ...] = Field(min_length=1, max_length=1)
    repository_selection: Literal["selected"] = "selected"
    api_version: str = Field(min_length=1, max_length=32)
    resource_bucket: str = Field(min_length=1, max_length=64)
    permission_metadata: Literal["read"] = "read"
    permission_contents: Literal["write"] = "write"
    permission_pull_requests: Literal["write"] = "write"
    every_other_permission: Literal["none"] = "none"
    maximum_publication_transactions: Literal[1] = 1
    maximum_mutation_requests: int = Field(ge=5, le=68)
    maximum_total_requests: int = Field(ge=16, le=142)
    automatic_mutation_retries: Literal[0] = 0
    minted_at: str
    expires_at: str
    resolution_nonce_hash: str = Field(pattern=HASH)
    provider_authentication_scheme: Literal["Ed25519"] = "Ed25519"
    provider_authentication_key_id: str = Field(min_length=1, max_length=128)
    fixture_loopback_only: Literal[True] = True
    live_use_allowed: Literal[False] = False
    signature: str = Field(pattern=r"^[A-Za-z0-9_-]{86}$")

    @field_validator("minted_at", "expires_at")
    @classmethod
    def valid_claim_time(cls, value: str) -> str:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        return value

    @model_validator(mode="after")
    def exact_one_shot_claim(self) -> "PublicationLeaseClaims":
        minted = datetime.strptime(self.minted_at, "%Y-%m-%dT%H:%M:%SZ")
        expires = datetime.strptime(self.expires_at, "%Y-%m-%dT%H:%M:%SZ")
        if not minted < expires or (expires - minted).total_seconds() > 900:
            raise ValueError("publication fixture capability lifetime is invalid")
        if self.provider_authentication_key_id != self.key_id:
            raise ValueError("publication fixture capability key ID mismatch")
        return self


class PublicationLeaseEvidence(GitHubRecord):
    profile: Literal["github-publication-lease-evidence"] = (
        "github-publication-lease-evidence"
    )
    schema_version: Literal["github-publication-lease-evidence/0.1.0"] = (
        "github-publication-lease-evidence/0.1.0"
    )
    attempt_claim: RecordReference
    authorization: RecordReference
    operation_intent: RecordReference
    publication_intent: RecordReference
    plan: RecordReference
    rate_observation: RecordReference
    provider_key: RecordReference
    provider_public_key_sha256: str = Field(pattern=HASH)
    provider_claims: PublicationLeaseClaims
    provider_claims_hash: str = Field(pattern=HASH)
    claims_signature_validation: Literal["pass"] = "pass"
    claims_signature_validated_at: str
    resolution_nonce_hash: str = Field(pattern=HASH)
    rate_scope_hash: str = Field(pattern=HASH)
    protocol_hash: Literal[STAGE_21B_PROTOCOL_HASH] = STAGE_21B_PROTOCOL_HASH
    increment_21_hash: Literal[INCREMENT_21_PROTOCOL_HASH] = INCREMENT_21_PROTOCOL_HASH
    stage_21a_hash: Literal[STAGE_21A_PROTOCOL_HASH] = STAGE_21A_PROTOCOL_HASH
    erratum_hash: Literal[STAGE_21B_ERRATUM_HASH] = STAGE_21B_ERRATUM_HASH
    repository_profile: RecordReference
    api_profile: RecordReference
    repository_id: int = Field(gt=0)
    account_id: int = Field(gt=0)
    app_id: int = Field(gt=0)
    installation_id: int = Field(gt=0)
    provider_id: str = Field(min_length=1, max_length=64)
    provider_version: str = Field(min_length=1, max_length=64)
    api_version: str = Field(min_length=1, max_length=32)
    resource_bucket: str = Field(min_length=1, max_length=64)
    selected_repository: Literal[True] = True
    ordered_endpoint_plan: tuple[str, ...] = Field(min_length=16, max_length=142)
    maximum_mutation_requests: int = Field(ge=5, le=68)
    maximum_total_requests: int = Field(ge=16, le=142)
    automatic_mutation_retries: Literal[0] = 0
    first_rate_check_at: str
    first_rate_check_fresh: Literal[True] = True
    first_rate_check_scoped: Literal[True] = True
    first_rate_check_sufficient: Literal[True] = True
    permission_metadata: Literal["read"] = "read"
    permission_contents: Literal["write"] = "write"
    permission_pull_requests: Literal["write"] = "write"
    every_other_permission: Literal["none"] = "none"
    publication_started_at_evidence_creation: Literal[False] = False
    credential_present: Literal[False] = False

    @field_validator("claims_signature_validated_at")
    @classmethod
    def valid_claim_validation_time(cls, value: str) -> str:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        return value

    @model_validator(mode="after")
    def claims_are_exactly_embedded(self) -> "PublicationLeaseEvidence":
        claims_bytes = json.dumps(
            self.provider_claims.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        expected_hash = "sha256:" + hashlib.sha256(claims_bytes).hexdigest()
        claims = self.provider_claims
        if not all(
            (
                self.provider_claims_hash == expected_hash,
                self.resolution_nonce_hash == claims.resolution_nonce_hash,
                self.provider_id == claims.provider_id,
                self.provider_version == claims.provider_version,
                self.app_id == claims.app_id,
                self.installation_id == claims.installation_id,
                self.account_id == claims.account_id,
                self.repository_id == claims.repository_ids[0],
                self.api_version == claims.api_version,
                self.resource_bucket == claims.resource_bucket,
                self.rate_observation.content_hash == claims.rate_observation_hash,
                self.rate_scope_hash == claims.rate_scope_hash,
                self.maximum_mutation_requests == claims.maximum_mutation_requests,
                self.maximum_total_requests == claims.maximum_total_requests,
            )
        ):
            raise ValueError("publication fixture capability claims are not exact")
        validated = datetime.strptime(
            self.claims_signature_validated_at, "%Y-%m-%dT%H:%M:%SZ"
        )
        minted = datetime.strptime(claims.minted_at, "%Y-%m-%dT%H:%M:%SZ")
        expires = datetime.strptime(claims.expires_at, "%Y-%m-%dT%H:%M:%SZ")
        if not minted <= validated < expires:
            raise ValueError(
                "publication fixture capability validation time is invalid"
            )
        return self

    @field_validator("first_rate_check_at")
    @classmethod
    def valid_first_rate_check_time(cls, value: str) -> str:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        return value


class BranchRulesPublicationObservation(GitHubRecord):
    profile: Literal["github-publication-branch-rules-observation"] = (
        "github-publication-branch-rules-observation"
    )
    schema_version: Literal["github-publication-branch-rules-observation/0.1.0"] = (
        "github-publication-branch-rules-observation/0.1.0"
    )
    repository_profile: RecordReference
    api_profile: RecordReference
    repository_id: int = Field(gt=0)
    account_id: int = Field(gt=0)
    head_ref: str
    observed_at: str
    complete: Literal[True] = True
    permission_limited: Literal[False] = False
    protected: Literal[False] = False
    creation_prohibited: Literal[False] = False

    @field_validator("observed_at")
    @classmethod
    def valid_observed_at(cls, value: str) -> str:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        return value


class RulesetPublicationObservation(GitHubRecord):
    profile: Literal["github-publication-ruleset-observation"] = (
        "github-publication-ruleset-observation"
    )
    schema_version: Literal["github-publication-ruleset-observation/0.1.0"] = (
        "github-publication-ruleset-observation/0.1.0"
    )
    repository_profile: RecordReference
    api_profile: RecordReference
    repository_id: int = Field(gt=0)
    account_id: int = Field(gt=0)
    head_ref: str
    observed_at: str
    complete: Literal[True] = True
    permission_limited: Literal[False] = False
    ruleset_targeted: Literal[False] = False
    creation_prohibited: Literal[False] = False

    @field_validator("observed_at")
    @classmethod
    def valid_observed_at(cls, value: str) -> str:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        return value


class Stage21AObservationEvidence(ClosedModel):
    """One complete, authenticated Stage 21A factual-observation chain."""

    repository_profile_record: GitHubRepositoryProfile
    api_profile_record: GitHubApiProfile
    provider_key_reference: RecordReference
    provider_key_record: GitHubCredentialProviderKey
    authorization_record: GitHubOperationAuthorization
    intent_record: GitHubOperationIntent
    attempt_claim_record: GitHubOperationAttemptClaim
    lease_evidence_record: CredentialLeaseEvidence
    observation_reference: RecordReference
    observation_record: GitHubObservation

    @model_validator(mode="after")
    def chain_is_exact_and_authenticated(self) -> "Stage21AObservationEvidence":
        repo = self.repository_profile_record
        api = self.api_profile_record
        key = self.provider_key_record
        authorization = self.authorization_record
        intent = self.intent_record
        claim = self.attempt_claim_record
        lease = self.lease_evidence_record
        observation = self.observation_record
        claims = lease.provider_claims
        endpoint = ENDPOINTS[authorization.operation_key]

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

        expected = (
            self.provider_key_reference.reference == repo.provider_key_reference,
            self.provider_key_reference.content_hash == key.content_hash,
            repo.provider_key_hash == key.content_hash,
            repo.expected_provider_id == key.provider_id,
            repo.expected_provider_key_id == key.key_id,
            repo.expected_provider_public_key_sha256 == key.public_key_sha256,
            authorization.repository_profile.content_hash == repo.content_hash,
            authorization.api_profile.content_hash == api.content_hash,
            intent.authorization.content_hash == authorization.content_hash,
            intent.repository_profile == authorization.repository_profile,
            intent.api_profile == authorization.api_profile,
            claim.authorization == intent.authorization,
            claim.intent.content_hash == intent.content_hash,
            claim.repository_profile == intent.repository_profile,
            claim.api_profile == intent.api_profile,
            lease.authorization == intent.authorization,
            lease.intent == claim.intent,
            lease.attempt_claim.content_hash == claim.content_hash,
            observation.repository_profile == intent.repository_profile,
            observation.api_profile == intent.api_profile,
            observation.authorization == intent.authorization,
            observation.intent == claim.intent,
            observation.attempt_claim == lease.attempt_claim,
            observation.lease_evidence.content_hash == lease.content_hash,
            self.observation_reference.content_hash == observation.content_hash,
            authorization.repository_id
            == repo.repository_id
            == intent.repository_id
            == claim.repository_id
            == observation.repository_id
            == claims.repository_ids[0],
            authorization.account_id
            == repo.account_id
            == intent.account_id
            == claim.account_id
            == observation.account_id
            == claims.account_id,
            repo.expected_app_id
            == intent.app_id
            == claim.app_id
            == observation.app_id
            == claims.app_id,
            repo.expected_installation_id
            == intent.installation_id
            == claim.installation_id
            == observation.installation_id
            == claims.installation_id,
            authorization.operation_key
            == intent.operation_key
            == claim.operation_key
            == observation.operation_key,
            authorization.path_parameters
            == intent.path_parameters
            == observation.path_parameters,
            authorization.query_parameters
            == intent.query_parameters
            == observation.query_parameters,
            intent.attempt_id == claim.attempt_id == observation.attempt_id,
            claim.intent_expiry == intent.not_after,
            intent.maximum_response_body_bytes_per_page
            == api.maximum_response_body_bytes_per_page,
            intent.maximum_total_response_body_bytes
            == api.maximum_total_response_body_bytes,
            intent.maximum_pages == endpoint.maximum_pages,
            intent.maximum_items == endpoint.maximum_items,
            intent.operation_timeout_seconds == api.operation_timeout_seconds,
            intent.maximum_retry_transmissions_per_operation
            == api.maximum_retry_transmissions_per_operation,
            authorization.maximum_network_requests
            == intent.maximum_network_requests
            == lease.maximum_network_requests
            == endpoint.maximum_pages + 1,
            authorization.operation_key in repo.read_operations,
            claims.provider_id == key.provider_id,
            claims.provider_version in repo.expected_provider_versions,
            claims.key_id == key.key_id,
            claims.provider_authentication_key_id == key.key_id,
            claims.repository_profile_hash == repo.content_hash,
            claims.api_profile_hash == api.content_hash,
            claims.authorization_hash == authorization.content_hash,
            claims.intent_hash == intent.content_hash,
            claims.permissions == required_permissions,
            lease.receipt_projection.permissions == required_permissions,
            required_permissions.read_keys().issubset(
                repo.permission_ceiling.read_keys()
            ),
            claims.api_version == api.api_version,
            observation.status_class == "2xx",
            observation.complete,
            observation.pagination_complete,
            observation.identity_match,
            observation.visibility == "complete_for_endpoint",
            observation.reason_codes == (),
            len(observation.pages) <= endpoint.maximum_pages,
            sum(page.item_count for page in observation.pages)
            <= endpoint.maximum_items,
            sum(page.response_bytes for page in observation.pages)
            <= api.maximum_total_response_body_bytes,
            all(
                page.response_bytes <= api.maximum_response_body_bytes_per_page
                for page in observation.pages
            ),
        )
        if not all(expected):
            raise ValueError("Stage 21A observation evidence is not exactly bound")

        issued = datetime.strptime(authorization.issued_at, "%Y-%m-%dT%H:%M:%SZ")
        expires = datetime.strptime(authorization.expires_at, "%Y-%m-%dT%H:%M:%SZ")
        not_after = datetime.strptime(intent.not_after, "%Y-%m-%dT%H:%M:%SZ")
        claimed = datetime.strptime(claim.claim_time, "%Y-%m-%dT%H:%M:%SZ")
        observed = datetime.strptime(observation.observed_at, "%Y-%m-%dT%H:%M:%SZ")
        key_valid_from = datetime.strptime(key.valid_from, "%Y-%m-%dT%H:%M:%SZ")
        key_valid_until = datetime.strptime(key.valid_until, "%Y-%m-%dT%H:%M:%SZ")
        claims_minted = datetime.strptime(claims.minted_at, "%Y-%m-%dT%H:%M:%SZ")
        claims_expires = datetime.strptime(claims.expires_at, "%Y-%m-%dT%H:%M:%SZ")
        if not (
            issued <= claimed <= observed <= min(expires, not_after)
            and key_valid_from <= claims_minted < claims_expires <= key_valid_until
            and claims_minted <= observed < claims_expires
        ):
            raise ValueError("Stage 21A observation evidence time order is invalid")
        try:
            _verify_signature(claims, public_key=key, domain=CLAIMS_SIGNATURE_DOMAIN)
        except Exception:
            raise ValueError(
                "Stage 21A credential claims signature is invalid"
            ) from None
        return self


class AuthenticatedRateBudgetObservation(GitHubRecord):
    """Canonical rate record whose values must match a signed 21A response."""

    profile: Literal["github-rate-budget-observation"] = (
        "github-rate-budget-observation"
    )
    schema_version: Literal["github-rate-budget-observation/0.1.0"] = (
        "github-rate-budget-observation/0.1.0"
    )
    source_observation: RecordReference
    repository_profile: RecordReference
    api_profile: RecordReference
    repository_id: int = Field(gt=0)
    account_id: int = Field(gt=0)
    app_id: int = Field(gt=0)
    installation_id: int = Field(gt=0)
    provider_id: str = Field(min_length=1, max_length=64)
    provider_version: str = Field(min_length=1, max_length=64)
    provider_key: RecordReference
    provider_public_key_sha256: str = Field(pattern=HASH)
    api_version: str = Field(min_length=1, max_length=32)
    resource_bucket: str = Field(min_length=1, max_length=64)
    limit: int = Field(ge=0)
    remaining: int = Field(ge=0)
    reset_at: str | None = None
    retry_after_present: bool
    observed_at: str
    complete: Literal[True] = True

    @field_validator("observed_at", "reset_at")
    @classmethod
    def valid_rate_time(cls, value: str | None) -> str | None:
        if value is not None:
            datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        return value

    @model_validator(mode="after")
    def remaining_does_not_exceed_limit(self) -> "AuthenticatedRateBudgetObservation":
        if self.remaining > self.limit:
            raise ValueError("rate remaining exceeds the observed limit")
        return self


def _rate_budget_matches_signed_source(
    rate: AuthenticatedRateBudgetObservation,
    evidence: Stage21AObservationEvidence,
) -> bool:
    observation = evidence.observation_record
    claims = evidence.lease_evidence_record.provider_claims
    if len(observation.pages) != 1:
        return False
    projected_rate = observation.pages[0].rate_limit
    return all(
        (
            observation.operation_key == "repository.get",
            observation.complete,
            observation.pagination_complete,
            observation.identity_match,
            observation.visibility == "complete_for_endpoint",
            observation.reason_codes == (),
            rate.source_observation == evidence.observation_reference,
            rate.repository_profile.content_hash
            == evidence.repository_profile_record.content_hash,
            rate.api_profile.content_hash == evidence.api_profile_record.content_hash,
            rate.repository_id
            == observation.repository_id
            == evidence.repository_profile_record.repository_id,
            rate.account_id
            == observation.account_id
            == evidence.repository_profile_record.account_id,
            rate.app_id == observation.app_id == claims.app_id,
            rate.installation_id
            == observation.installation_id
            == claims.installation_id,
            rate.provider_id == claims.provider_id,
            rate.provider_version == claims.provider_version,
            rate.provider_key == evidence.provider_key_reference,
            rate.provider_public_key_sha256
            == evidence.provider_key_record.public_key_sha256,
            rate.api_version == claims.api_version,
            projected_rate.resource is not None,
            rate.resource_bucket == projected_rate.resource,
            projected_rate.limit is not None,
            rate.limit == projected_rate.limit,
            projected_rate.remaining is not None,
            rate.remaining == projected_rate.remaining,
            rate.reset_at == projected_rate.reset_at,
            rate.retry_after_present == projected_rate.retry_after_present,
            rate.observed_at == observation.observed_at,
        )
    )


def _branch_rules_are_exact_for_head(
    evidence: Stage21AObservationEvidence, head_ref: str
) -> bool:
    observation = evidence.observation_record
    projection = observation.projection
    return (
        observation.operation_key == "branch_rules.list"
        and observation.path_parameters
        == {"branch": head_ref.removeprefix("refs/heads/")}
        and observation.query_parameters == {"per_page": 100, "page": 1}
        and set(projection) == {"rules"}
        and type(projection.get("rules")) is list
        and projection["rules"] == []
        and sum(page.item_count for page in observation.pages) == 0
    )


def _rulesets_are_exact(
    evidence: Stage21AObservationEvidence,
) -> bool:
    observation = evidence.observation_record
    projection = observation.projection
    rulesets = projection.get("rulesets")
    return (
        observation.operation_key == "repository_rulesets.list"
        and observation.path_parameters == {}
        and observation.query_parameters
        == {"includes_parents": True, "per_page": 100, "page": 1}
        and set(projection) == {"rulesets"}
        and type(rulesets) is list
        and rulesets == []
        and sum(page.item_count for page in observation.pages) == 0
    )


def _source_credential_authenticates_recursive_tree(
    authorization: RecursiveTreeAuthorization,
    intent: RecursiveTreeIntent,
    claim: RecursiveTreeAttemptClaim,
    lease: RecursiveTreeLeaseEvidence,
    credential: CredentialLeaseEvidence,
) -> bool:
    """Require signed credential claims to name the exact tree-source chain."""

    claims = credential.provider_claims
    return all(
        (
            credential.authorization == lease.authorization,
            credential.intent == lease.intent,
            credential.attempt_claim == lease.claim,
            credential.authorization.content_hash
            == claims.authorization_hash
            == authorization.content_hash,
            credential.intent.content_hash == claims.intent_hash == intent.content_hash,
            lease.authorization.content_hash == authorization.content_hash,
            lease.intent.content_hash == intent.content_hash,
            lease.claim.content_hash == claim.content_hash,
        )
    )


class PublicationGovernanceChain(ClosedModel):
    repository_profile_record: GitHubRepositoryProfile
    api_profile_record: GitHubApiProfile
    repository_extension_record: PublicationRepositoryExtension
    task_packet_record: TaskPacket
    handoff_record: HandoffPacket
    scope_review_record: ScopeReview
    provider_key_record: GitHubCredentialProviderKey
    source_authorization_record: RecursiveTreeAuthorization
    source_intent_record: RecursiveTreeIntent
    source_attempt_claim_record: RecursiveTreeAttemptClaim
    source_lease_evidence_record: RecursiveTreeLeaseEvidence
    source_credential_lease_evidence_record: CredentialLeaseEvidence
    rate_observation_record: AuthenticatedRateBudgetObservation
    rate_source_observation_chain: Stage21AObservationEvidence
    branch_rules_observation_chain: tuple[Stage21AObservationEvidence, ...] = Field(
        min_length=1, max_length=1
    )
    ruleset_observation_chain: tuple[Stage21AObservationEvidence, ...] = Field(
        min_length=1, max_length=1
    )
    base_identity_observation: BaseTreeIdentityObservation
    recursive_tree_observation: RecursiveTreeObservation
    base_tree_closure: BaseTreeClosure
    manifest: ProposalManifest
    authorization: PublicationAuthorization
    plan: PublicationPlan
    operation_intent: OperationIntentV2
    publication_intent: PublicationIntent
    attempt_claim: PublicationAttemptClaim
    lease_evidence: PublicationLeaseEvidence

    @property
    def rate_source_observation_record(self) -> GitHubObservation:
        """Compatibility accessor for the evaluator's durable reopen path."""

        return self.rate_source_observation_chain.observation_record

    @model_validator(mode="after")
    def all_links_exact(self) -> "PublicationGovernanceChain":
        m, a, p = self.manifest, self.authorization, self.plan
        closure = self.base_tree_closure
        repo = self.repository_profile_record
        api = self.api_profile_record
        extension = self.repository_extension_record
        base = self.base_identity_observation
        source = self.recursive_tree_observation
        branch_evidence = self.branch_rules_observation_chain[0]
        ruleset_evidence = self.ruleset_observation_chain[0]
        branch_rules = branch_evidence.observation_record
        ruleset = ruleset_evidence.observation_record
        source_claims = self.source_credential_lease_evidence_record.provider_claims
        publication_claims = self.lease_evidence.provider_claims
        rate = self.rate_observation_record
        rate_chain = self.rate_source_observation_chain
        source_read_permissions = PermissionEnvelope(
            metadata="read",
            contents="read",
            pull_requests="none",
            checks="none",
            statuses="none",
            administration="none",
        )
        source_target = (
            f"/repos/{repo.owner}/{repo.repository}/git/trees/"
            f"{self.source_intent_record.root_tree_oid}?recursive=1"
        )
        source_target_hash = (
            "sha256:" + hashlib.sha256(source_target.encode("ascii")).hexdigest()
        )
        oi, pi, claim, lease = (
            self.operation_intent,
            self.publication_intent,
            self.attempt_claim,
            self.lease_evidence,
        )
        expected = [
            m.repository_profile.content_hash == repo.content_hash,
            m.api_profile.content_hash == api.content_hash,
            m.repository_extension.content_hash == extension.content_hash,
            extension.repository_profile == m.repository_profile,
            m.task_packet.content_hash == self.task_packet_record.content_hash,
            m.handoff.content_hash == self.handoff_record.content_hash,
            m.scope_review.content_hash == self.scope_review_record.content_hash,
            a.provider_key.content_hash == self.provider_key_record.content_hash,
            closure.source_authorization.content_hash
            == self.source_authorization_record.content_hash,
            closure.source_intent.content_hash
            == self.source_intent_record.content_hash,
            closure.source_attempt_claim.content_hash
            == self.source_attempt_claim_record.content_hash,
            closure.source_lease_evidence.content_hash
            == self.source_lease_evidence_record.content_hash,
            self.source_lease_evidence_record.credential_lease_evidence.content_hash
            == self.source_credential_lease_evidence_record.content_hash,
            _source_credential_authenticates_recursive_tree(
                self.source_authorization_record,
                self.source_intent_record,
                self.source_attempt_claim_record,
                self.source_lease_evidence_record,
                self.source_credential_lease_evidence_record,
            ),
            self.source_intent_record.authorization.content_hash
            == self.source_authorization_record.content_hash,
            self.source_intent_record.repository_profile
            == self.source_authorization_record.repository_profile,
            self.source_intent_record.api_profile
            == self.source_authorization_record.api_profile,
            self.source_intent_record.repository_extension
            == self.source_authorization_record.repository_extension,
            self.source_intent_record.repository_id
            == self.source_authorization_record.repository_id,
            self.source_intent_record.account_id
            == self.source_authorization_record.account_id,
            self.source_intent_record.base_ref
            == self.source_authorization_record.base_ref,
            self.source_intent_record.object_format
            == self.source_authorization_record.object_format,
            self.source_intent_record.request_target_hash == source_target_hash,
            self.source_intent_record.not_after
            == self.source_authorization_record.expires_at,
            self.source_attempt_claim_record.authorization.content_hash
            == self.source_authorization_record.content_hash,
            self.source_attempt_claim_record.intent.content_hash
            == self.source_intent_record.content_hash,
            self.source_attempt_claim_record.repository_profile
            == self.source_authorization_record.repository_profile,
            self.source_attempt_claim_record.api_profile
            == self.source_authorization_record.api_profile,
            self.source_attempt_claim_record.repository_id
            == self.source_authorization_record.repository_id,
            self.source_attempt_claim_record.account_id
            == self.source_authorization_record.account_id,
            self.source_lease_evidence_record.authorization.content_hash
            == self.source_authorization_record.content_hash,
            self.source_lease_evidence_record.intent.content_hash
            == self.source_intent_record.content_hash,
            self.source_lease_evidence_record.claim.content_hash
            == self.source_attempt_claim_record.content_hash,
            self.source_lease_evidence_record.provider_key.content_hash
            == self.provider_key_record.content_hash,
            self.source_lease_evidence_record.provider_key.reference
            == repo.provider_key_reference,
            self.source_lease_evidence_record.provider_public_key_sha256
            == repo.expected_provider_public_key_sha256,
            self.source_lease_evidence_record.provider_id
            == source_claims.provider_id
            == self.provider_key_record.provider_id
            == repo.expected_provider_id,
            self.source_lease_evidence_record.provider_version
            == source_claims.provider_version,
            source_claims.provider_version in repo.expected_provider_versions,
            self.source_lease_evidence_record.app_id
            == source_claims.app_id
            == repo.expected_app_id,
            self.source_lease_evidence_record.installation_id
            == source_claims.installation_id
            == repo.expected_installation_id,
            self.source_lease_evidence_record.repository_id
            == source_claims.repository_ids[0]
            == repo.repository_id,
            self.source_lease_evidence_record.account_id
            == source_claims.account_id
            == repo.account_id,
            source_claims.key_id == self.provider_key_record.key_id,
            source_claims.provider_authentication_key_id
            == self.provider_key_record.key_id,
            self.source_credential_lease_evidence_record.authorization.content_hash
            == source_claims.authorization_hash
            == self.source_authorization_record.content_hash,
            self.source_credential_lease_evidence_record.authorization
            == self.source_lease_evidence_record.authorization,
            self.source_credential_lease_evidence_record.intent.content_hash
            == source_claims.intent_hash
            == self.source_intent_record.content_hash,
            self.source_credential_lease_evidence_record.intent
            == self.source_lease_evidence_record.intent,
            self.source_credential_lease_evidence_record.attempt_claim
            == self.source_lease_evidence_record.claim,
            source_claims.repository_profile_hash == repo.content_hash,
            source_claims.api_profile_hash == api.content_hash,
            source_claims.api_version == api.api_version,
            source_claims.permissions == source_read_permissions,
            self.source_credential_lease_evidence_record.receipt_projection.permissions
            == source_read_permissions,
            source_read_permissions.read_keys().issubset(
                repo.permission_ceiling.read_keys()
            ),
            self.source_authorization_record.repository_profile.content_hash
            == repo.content_hash,
            self.source_authorization_record.api_profile.content_hash
            == api.content_hash,
            self.source_authorization_record.repository_extension.content_hash
            == extension.content_hash,
            self.source_authorization_record.base_ref == m.base_ref,
            self.source_authorization_record.base_commit_oid == m.base_commit_oid,
            self.source_authorization_record.root_tree_oid == m.base_tree_oid,
            self.source_authorization_record.authorized_principal
            == a.authorized_principal,
            self.source_intent_record.root_tree_oid == m.base_tree_oid,
            self.source_lease_evidence_record.repository_id == m.repository_id,
            self.source_lease_evidence_record.account_id == m.account_id,
            self.source_lease_evidence_record.provider_public_key_sha256
            == self.provider_key_record.public_key_sha256,
            _rate_budget_matches_signed_source(rate, rate_chain),
            a.rate_observation.content_hash == rate.content_hash,
            branch_evidence.repository_profile_record == repo,
            branch_evidence.api_profile_record == api,
            branch_evidence.provider_key_record == self.provider_key_record,
            ruleset_evidence.repository_profile_record == repo,
            ruleset_evidence.api_profile_record == api,
            ruleset_evidence.provider_key_record == self.provider_key_record,
            _branch_rules_are_exact_for_head(branch_evidence, m.head_ref),
            _rulesets_are_exact(ruleset_evidence),
            m.owner == repo.owner,
            m.repository == repo.repository,
            m.repository_id == repo.repository_id,
            m.account_id == repo.account_id,
            m.object_format == repo.git_object_format,
            m.base_ref in repo.allowed_base_refs,
            closure.base_observation.content_hash == base.content_hash,
            closure.source_observation.content_hash == source.content_hash,
            base.repository_profile.content_hash == repo.content_hash,
            source.repository_profile.content_hash == repo.content_hash,
            base.api_profile == source.api_profile == closure.api_profile,
            base.repository_id == source.repository_id == closure.repository_id,
            base.account_id == source.account_id == closure.account_id,
            base.base_ref == source.base_ref == closure.base_ref,
            base.base_commit_oid == source.base_commit_oid == closure.base_commit_oid,
            base.base_root_tree_oid
            == source.root_tree_oid
            == closure.base_root_tree_oid,
            base.object_format == source.object_format == closure.object_format,
            base.observed_at == closure.base_observed_at,
            source.created_at == closure.source_observed_at,
            source.entries == closure.entries,
            source.authorization == closure.source_authorization,
            source.intent == closure.source_intent,
            source.attempt_claim == closure.source_attempt_claim,
            source.lease_evidence == closure.source_lease_evidence,
            a.manifest
            == RecordReference(
                reference=a.manifest.reference, content_hash=m.content_hash
            ),
            m.base_tree_closure
            == RecordReference(
                reference=m.base_tree_closure.reference,
                content_hash=closure.content_hash,
            ),
            m.base_observation == closure.base_observation,
            m.repository_profile == closure.repository_profile,
            m.api_profile == closure.api_profile,
            m.repository_id == closure.repository_id,
            m.account_id == closure.account_id,
            m.base_ref == closure.base_ref,
            m.base_commit_oid == closure.base_commit_oid,
            m.base_tree_oid == closure.base_root_tree_oid,
            m.branch_rules_observation == branch_evidence.observation_reference,
            m.ruleset_observation == ruleset_evidence.observation_reference,
            branch_rules.repository_profile
            == ruleset.repository_profile
            == m.repository_profile,
            branch_rules.api_profile == ruleset.api_profile == m.api_profile,
            branch_rules.repository_id == ruleset.repository_id == m.repository_id,
            branch_rules.account_id == ruleset.account_id == m.account_id,
            p.authorization.content_hash == a.content_hash,
            p.manifest == a.manifest,
            p.rate_observation == a.rate_observation,
            oi.authorization == p.authorization,
            oi.manifest == p.manifest,
            oi.plan.content_hash == p.content_hash,
            oi.rate_observation == p.rate_observation,
            pi.authorization == oi.authorization,
            pi.manifest == oi.manifest,
            pi.plan == oi.plan,
            pi.operation_intent.content_hash == oi.content_hash,
            pi.rate_observation == oi.rate_observation,
            claim.authorization == pi.authorization,
            claim.manifest == pi.manifest,
            claim.plan == pi.plan,
            claim.operation_intent == pi.operation_intent,
            claim.publication_intent.content_hash == pi.content_hash,
            claim.rate_observation == pi.rate_observation,
            lease.attempt_claim.content_hash == claim.content_hash,
            lease.authorization == claim.authorization,
            lease.operation_intent == claim.operation_intent,
            lease.publication_intent == claim.publication_intent,
            lease.plan == claim.plan,
            lease.rate_observation == claim.rate_observation,
            tuple(p.ordered_request_hashes) == tuple(pi.exact_request_hashes),
            p.expected_tree_oid == pi.expected_tree_oid == m.proposal_tree_oid,
            p.expected_commit_oid == pi.expected_commit_oid == m.proposal_commit_oid,
            p.base_ref == pi.base_ref == m.base_ref,
            p.head_ref == pi.head_ref == m.head_ref,
            a.maximum_total_requests
            == p.maximum_total_requests
            == oi.maximum_total_requests
            == 2 * len(m.files) + 14,
            a.maximum_mutation_requests == len(m.files) + 4,
            a.repository_profile == m.repository_profile,
            a.api_profile == m.api_profile,
            a.repository_id == m.repository_id,
            a.account_id == m.account_id,
            a.base_ref == m.base_ref,
            a.head_ref == m.head_ref,
            a.base_commit_oid == m.base_commit_oid,
            a.base_tree_oid == m.base_tree_oid,
            a.base_tree_closure == m.base_tree_closure,
            a.base_tree_source_observation == closure.source_observation,
            a.proposal_tree_oid == m.proposal_tree_oid,
            a.proposal_commit_oid == m.proposal_commit_oid,
            a.allowed_paths == m.allowed_paths,
            a.aggregate_proposal_hash == m.aggregate_manifest_hash,
            a.commit_message_hash == m.commit_message.content_hash,
            a.commit_message_byte_count == m.commit_message_byte_count,
            a.pull_request_title_hash == m.pull_request_title.content_hash,
            a.pull_request_title_byte_count == m.pull_request_title_byte_count,
            a.pull_request_body_hash == m.pull_request_body.content_hash,
            a.pull_request_body_byte_count == m.pull_request_body_byte_count,
            a.provider_key == lease.provider_key,
            a.provider_key.reference == repo.provider_key_reference,
            a.provider_public_key_sha256 == lease.provider_public_key_sha256,
            a.rate_observation
            == p.rate_observation
            == oi.rate_observation
            == pi.rate_observation,
            p.rate_scope_hash
            == oi.rate_scope_hash
            == pi.rate_scope_hash
            == lease.rate_scope_hash,
            p.ordered_endpoint_plan
            == oi.ordered_endpoint_plan
            == pi.ordered_endpoint_plan
            == lease.ordered_endpoint_plan,
            p.ordered_request_hashes
            == oi.canonical_request_hashes
            == pi.exact_request_hashes,
            p.blob_request_hashes == pi.blob_request_hashes,
            p.expected_blob_oids == pi.expected_blob_oids,
            p.tree_request_hash == pi.tree_request_hash,
            p.commit_request_hash == pi.commit_request_hash,
            p.ref_request_hash == pi.ref_request_hash,
            p.pull_request_request_hash == pi.pull_request_request_hash,
            oi.attempt_id == pi.attempt_id == claim.attempt_id,
            claim.attempt_id
            == publication_attempt_id(
                authorization=a,
                manifest=m,
                plan=p,
            ),
            claim.provider_key == lease.provider_key,
            claim.provider_public_key_sha256 == lease.provider_public_key_sha256,
            claim.upstream_records
            == pi.upstream_records
            == oi.upstream_records
            == p.upstream_records,
            p.upstream_records
            == (
                m.repository_profile,
                m.api_profile,
                m.repository_extension,
                m.task_packet,
                m.handoff,
                m.scope_review,
                m.base_observation,
                m.base_tree_closure,
                closure.source_observation,
                closure.source_authorization,
                closure.source_intent,
                closure.source_attempt_claim,
                closure.source_lease_evidence,
                m.branch_rules_observation,
                m.ruleset_observation,
                a.rate_observation,
                a.provider_key,
            ),
            lease.protocol_hash == a.protocol_hash,
            lease.increment_21_hash == a.increment_21_hash,
            lease.stage_21a_hash == a.stage_21a_hash,
            lease.erratum_hash == a.erratum_hash,
            lease.repository_profile == a.repository_profile,
            lease.api_profile == a.api_profile,
            lease.repository_id == a.repository_id,
            lease.account_id == a.account_id,
            lease.app_id == a.app_id,
            lease.installation_id == a.installation_id,
            lease.provider_id == a.provider_id,
            lease.provider_version == a.provider_version,
            lease.api_version == a.api_version,
            lease.resource_bucket == a.resource_bucket,
            lease.maximum_mutation_requests == a.maximum_mutation_requests,
            lease.maximum_total_requests == a.maximum_total_requests,
            publication_claims.repository_profile_hash == repo.content_hash,
            publication_claims.api_profile_hash == api.content_hash,
            publication_claims.authorization_hash == a.content_hash,
            publication_claims.plan_hash == p.content_hash,
            publication_claims.operation_intent_hash == oi.content_hash,
            publication_claims.publication_intent_hash == pi.content_hash,
            publication_claims.attempt_claim_hash == claim.content_hash,
            publication_claims.attempt_id == claim.attempt_id,
            publication_claims.rate_observation_hash == rate.content_hash,
            publication_claims.rate_scope_hash == lease.rate_scope_hash,
            publication_claims.provider_id
            == lease.provider_id
            == self.provider_key_record.provider_id,
            publication_claims.provider_version == lease.provider_version,
            publication_claims.key_id == self.provider_key_record.key_id,
            publication_claims.provider_authentication_key_id
            == self.provider_key_record.key_id,
            publication_claims.app_id == lease.app_id,
            publication_claims.installation_id == lease.installation_id,
            publication_claims.account_id == lease.account_id,
            publication_claims.repository_ids == (lease.repository_id,),
            publication_claims.api_version == lease.api_version,
            publication_claims.resource_bucket == lease.resource_bucket,
            publication_claims.maximum_mutation_requests
            == lease.maximum_mutation_requests,
            publication_claims.maximum_total_requests == lease.maximum_total_requests,
        ]
        if not all(expected):
            raise ValueError("publication governance chain is not exactly cross-bound")
        try:
            _verify_signature(
                source_claims,
                public_key=self.provider_key_record,
                domain=CLAIMS_SIGNATURE_DOMAIN,
            )
        except Exception:
            raise ValueError(
                "recursive-tree source credential claims signature is invalid"
            ) from None
        try:
            _verify_signature(
                publication_claims,
                public_key=self.provider_key_record,
                domain=PUBLICATION_LEASE_CLAIMS_DOMAIN,
            )
        except Exception:
            raise ValueError(
                "publication fixture capability claims signature is invalid"
            ) from None
        source_issued = datetime.strptime(
            self.source_authorization_record.issued_at, "%Y-%m-%dT%H:%M:%SZ"
        )
        source_expires = datetime.strptime(
            self.source_authorization_record.expires_at, "%Y-%m-%dT%H:%M:%SZ"
        )
        source_claimed = datetime.strptime(
            self.source_attempt_claim_record.created_at, "%Y-%m-%dT%H:%M:%SZ"
        )
        source_observed = datetime.strptime(source.created_at, "%Y-%m-%dT%H:%M:%SZ")
        credential_minted = datetime.strptime(
            source_claims.minted_at, "%Y-%m-%dT%H:%M:%SZ"
        )
        credential_expires = datetime.strptime(
            source_claims.expires_at, "%Y-%m-%dT%H:%M:%SZ"
        )
        publication_minted = datetime.strptime(
            publication_claims.minted_at, "%Y-%m-%dT%H:%M:%SZ"
        )
        publication_expires = datetime.strptime(
            publication_claims.expires_at, "%Y-%m-%dT%H:%M:%SZ"
        )
        publication_validated = datetime.strptime(
            lease.claims_signature_validated_at, "%Y-%m-%dT%H:%M:%SZ"
        )
        provider_key_from = datetime.strptime(
            self.provider_key_record.valid_from, "%Y-%m-%dT%H:%M:%SZ"
        )
        provider_key_until = datetime.strptime(
            self.provider_key_record.valid_until, "%Y-%m-%dT%H:%M:%SZ"
        )
        if not (
            source_issued <= source_claimed <= source_observed <= source_expires
            and credential_minted <= source_observed < credential_expires
            and provider_key_from
            <= publication_minted
            <= publication_validated
            < publication_expires
            <= provider_key_until
        ):
            raise ValueError("publication governance credential time order is invalid")
        if not (
            verify_task_hash(self.task_packet_record)
            and verify_handoff_content_hash(self.handoff_record)
            and verify_review_content_hash(self.scope_review_record)
            and self.scope_review_record.scope_status == "within_scope"
            and not self.scope_review_record.human_review_required
            and self.handoff_record.packet_ref == self.task_packet_record.ref
            and self.scope_review_record.task_packet_ref == self.task_packet_record.ref
            and self.handoff_record.packet_content_hash
            == self.task_packet_record.content_hash
            and self.scope_review_record.task_packet_hash
            == self.task_packet_record.content_hash
            and self.scope_review_record.handoff_packet_hash
            == self.handoff_record.content_hash
            and self.handoff_record.provider == self.scope_review_record.provider
            and self.handoff_record.role == self.scope_review_record.role
            and tuple(
                sorted(
                    result.object_id
                    for result in self.scope_review_record.object_results
                    if result.allowed
                    and result.action == "proposed_change"
                    and result.section_id is None
                )
            )
            == m.allowed_paths
            and tuple(
                sorted(
                    touch.object_id
                    for touch in self.handoff_record.objects_touched
                    if touch.action == "proposed_change" and touch.section_id is None
                )
            )
            == m.allowed_paths
            and all(
                result.allowed
                and result.classification == "in_target"
                and result.matched_grant == result.object_id
                for result in self.scope_review_record.object_results
            )
        ):
            raise ValueError("publication governance scope chain is invalid")
        return self
