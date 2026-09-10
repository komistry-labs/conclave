"""Deterministic Stage 21B reconciliation records and fixture evaluator.

This module deliberately has no credential, socket, HTTP, or live GitHub
surface.  It derives the reconciliation subject from retained publication
records and evaluates one already-bounded fixture/loopback observation.
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, Union

from pydantic import Field, model_validator

from .github_foundation import (
    CredentialLeaseEvidence,
    GitHubApiProfile,
    GitHubCredentialProviderKey,
    GitHubObservation,
    GitHubOperationAttemptClaim,
    GitHubOperationAuthorization,
    GitHubOperationIntent,
    GitHubRecord,
    GitHubRepositoryProfile,
    RecordReference,
    write_durable_record,
)
from .github_publication import (
    BaseTreeClosure,
    RecursiveTreeEntry,
    RecursiveTreeObservation,
    canonical_github_ref_target,
    git_object_oid,
    read_artifacts_once,
)
from .github_publication_engine import (
    MutationAdmittedWithoutResult,
    MutationResultPresent,
    PublicationReceipt,
    PublicationStepAdmission,
    PublicationStepResult,
    PublicationTerminalFailure,
    RateBudgetObservation,
    StepState,
    TerminalArtifactInventory,
)
from .github_publication_records import (
    ProposalManifest,
    PublicationAttemptClaim,
    PublicationLeaseEvidence,
    PublicationPlan,
    Stage21AObservationEvidence,
)
from .identity import ClosedModel, seal_record
from .workspace import Workspace


HASH_PATTERN = r"^sha256:[0-9a-f]{64}$"
OID_PATTERN = r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$"
RECONCILIATION_ID_PATTERN = r"^[A-Za-z0-9](?:[A-Za-z0-9_-]{0,126}[A-Za-z0-9])?$"
RECONCILIATION_READ_KEYS = frozenset(
    {
        "git_blob.get",
        "git_tree.get",
        "commit.get",
        "ref.get",
        "pull_requests.matching.list",
    }
)
MUTATION_TO_READ = {
    "git_blob.create": "git_blob.get",
    "git_tree.create": "git_tree.get",
    "git_commit.create": "commit.get",
    "git_ref.create": "ref.get",
    "pull_request.create": "pull_requests.matching.list",
}

FIXTURE_RECONCILIATION_SCHEMA_VERSION = "0.3.0"


def _hash_json(value: object) -> str:
    _validate_strict_json(value, seen=set(), path="$", depth=0)
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _validate_strict_json(
    value: object, *, seen: set[int], path: str, depth: int
) -> None:
    """Admit only bounded, float-free JSON before hashing evidence."""

    if depth > 64:
        raise ValueError(f"strict JSON nesting exceeds limit at {path}")
    if value is None or type(value) in {str, bool, int}:
        return
    if type(value) is list:
        marker = id(value)
        if marker in seen:
            raise ValueError(f"strict JSON cycle at {path}")
        seen.add(marker)
        try:
            for index, item in enumerate(value):
                _validate_strict_json(
                    item, seen=seen, path=f"{path}[{index}]", depth=depth + 1
                )
        finally:
            seen.remove(marker)
        return
    if type(value) is dict:
        marker = id(value)
        if marker in seen:
            raise ValueError(f"strict JSON cycle at {path}")
        seen.add(marker)
        try:
            for key, item in value.items():
                if type(key) is not str:
                    raise ValueError(f"strict JSON key is not a string at {path}")
                _validate_strict_json(
                    item, seen=seen, path=f"{path}.{key}", depth=depth + 1
                )
        finally:
            seen.remove(marker)
        return
    raise ValueError(f"strict JSON rejects {type(value).__name__} at {path}")


def _rr(reference: str, record: GitHubRecord) -> RecordReference:
    return RecordReference(reference=reference, content_hash=record.content_hash)


class CompleteTreeEntryIdentity(ClosedModel):
    path: str = Field(min_length=1, max_length=512)
    mode: Literal["040000", "100644", "100755", "120000", "160000"]
    object_type: Literal["tree", "blob", "commit"]
    oid: str = Field(pattern=OID_PATTERN)


class BlobExpectedIdentity(ClosedModel):
    kind: Literal["blob"] = "blob"
    oid: str = Field(pattern=OID_PATTERN)
    content_sha256: str = Field(pattern=HASH_PATTERN)
    byte_count: int = Field(ge=0, le=8 * 1024 * 1024)
    source_artifact: RecordReference


class TreeExpectedIdentity(ClosedModel):
    kind: Literal["tree"] = "tree"
    oid: str = Field(pattern=OID_PATTERN)
    entries: tuple[CompleteTreeEntryIdentity, ...] = Field(
        min_length=1, max_length=100000
    )
    entries_hash: str = Field(pattern=HASH_PATTERN)

    @model_validator(mode="after")
    def exact_entries(self) -> "TreeExpectedIdentity":
        values = [item.model_dump(mode="json") for item in self.entries]
        if tuple(item.path for item in self.entries) != tuple(
            sorted({item.path for item in self.entries})
        ):
            raise ValueError("tree entries must be uniquely sorted")
        if self.entries_hash != _hash_json(values):
            raise ValueError("tree entries hash mismatch")
        return self


class CommitExpectedIdentity(ClosedModel):
    kind: Literal["commit"] = "commit"
    oid: str = Field(pattern=OID_PATTERN)
    tree_oid: str = Field(pattern=OID_PATTERN)
    sole_parent_oid: str = Field(pattern=OID_PATTERN)
    message_sha256: str = Field(pattern=HASH_PATTERN)


class RefExpectedIdentity(ClosedModel):
    kind: Literal["ref"] = "ref"
    full_ref: str = Field(min_length=12, max_length=255)
    target_oid: str = Field(pattern=OID_PATTERN)


class PullRequestExpectedIdentity(ClosedModel):
    kind: Literal["pull_request"] = "pull_request"
    repository_id: int = Field(gt=0)
    head_ref: str = Field(min_length=12, max_length=255)
    head_oid: str = Field(pattern=OID_PATTERN)
    base_ref: str = Field(min_length=12, max_length=255)
    base_oid: str = Field(pattern=OID_PATTERN)
    title_sha256: str = Field(pattern=HASH_PATTERN)
    body_sha256: str = Field(pattern=HASH_PATTERN)
    maximum_selector_matches: Literal[2] = 2


ExpectedIdentity = Annotated[
    Union[
        BlobExpectedIdentity,
        TreeExpectedIdentity,
        CommitExpectedIdentity,
        RefExpectedIdentity,
        PullRequestExpectedIdentity,
    ],
    Field(discriminator="kind"),
]


def publication_expected_projection(identity: ExpectedIdentity) -> dict[str, object]:
    """Return the exact mutation-success projection bound by an admission."""

    if isinstance(identity, BlobExpectedIdentity):
        return {"oid": identity.oid}
    if isinstance(identity, TreeExpectedIdentity):
        return {"oid": identity.oid}
    if isinstance(identity, CommitExpectedIdentity):
        return {
            "oid": identity.oid,
            "tree_oid": identity.tree_oid,
            "parents": [identity.sole_parent_oid],
        }
    if isinstance(identity, RefExpectedIdentity):
        return {"ref": identity.full_ref, "oid": identity.target_oid}
    return {
        "repository_id": identity.repository_id,
        "head_ref": identity.head_ref,
        "head_oid": identity.head_oid,
        "base_ref": identity.base_ref,
        "base_oid": identity.base_oid,
        "title_hash": identity.title_sha256,
        "body_hash": identity.body_sha256,
    }


def expected_identity_hash(identity: ExpectedIdentity) -> str:
    return _hash_json(publication_expected_projection(identity))


def fixture_read_target(
    *, manifest: ProposalManifest, read_operation_key: str, expected: ExpectedIdentity
) -> str:
    """Derive the one closed reconciliation target from retained identities."""

    root = f"/repos/{manifest.owner}/{manifest.repository}"
    if read_operation_key == "git_blob.get" and isinstance(
        expected, BlobExpectedIdentity
    ):
        return f"{root}/git/blobs/{expected.oid}"
    if read_operation_key == "git_tree.get" and isinstance(
        expected, TreeExpectedIdentity
    ):
        return f"{root}/git/trees/{expected.oid}?recursive=1"
    if read_operation_key == "commit.get" and isinstance(
        expected, CommitExpectedIdentity
    ):
        return f"{root}/git/commits/{expected.oid}"
    if read_operation_key == "ref.get" and isinstance(expected, RefExpectedIdentity):
        path_form, _ = canonical_github_ref_target(expected.full_ref)
        return f"{root}/git/ref/{path_form}"
    if read_operation_key == "pull_requests.matching.list" and isinstance(
        expected, PullRequestExpectedIdentity
    ):
        _, head = canonical_github_ref_target(expected.head_ref)
        _, base = canonical_github_ref_target(expected.base_ref)
        return (
            f"{root}/pulls?state=all&head={manifest.owner}:{head}"
            f"&base={base}&per_page=2&page=1"
        )
    raise ValueError("PUBLICATION_RECONCILIATION_REQUIRED")


def fixture_read_request_hash(
    *, method: str, target: str, expected_identity_digest: str
) -> str:
    if method != "GET" or not target.startswith("/repos/"):
        raise ValueError("PUBLICATION_RECONCILIATION_REQUIRED")
    return _hash_json(
        {
            "schema_version": "github-publication-fixture-reconciliation-request/0.3.0",
            "method": method,
            "target": target,
            "expected_identity_hash": expected_identity_digest,
        }
    )


def _tree_payload(entries: tuple[RecursiveTreeEntry, ...]) -> bytes:
    def sort_key(entry: RecursiveTreeEntry) -> bytes:
        basename = entry.path.rsplit("/", 1)[-1].encode("utf-8")
        return basename + (b"/" if entry.type == "tree" else b"\0")

    payload = bytearray()
    for entry in sorted(entries, key=sort_key):
        mode = "40000" if entry.mode == "040000" else entry.mode
        payload.extend(mode.encode("ascii"))
        payload.extend(b" ")
        payload.extend(entry.path.rsplit("/", 1)[-1].encode("utf-8"))
        payload.extend(b"\0")
        payload.extend(bytes.fromhex(entry.oid))
    return bytes(payload)


def _complete_resultant_tree(
    manifest: ProposalManifest, closure: BaseTreeClosure
) -> tuple[CompleteTreeEntryIdentity, ...]:
    """Materialize the exact recursive proposal tree, including base survivors."""

    if not (
        manifest.base_tree_closure.content_hash == closure.content_hash
        and manifest.base_tree_oid == closure.base_root_tree_oid
        and manifest.base_commit_oid == closure.base_commit_oid
        and manifest.object_format == closure.object_format
    ):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    state = {entry.path: entry for entry in closure.entries}
    oid_length = 40 if manifest.object_format == "sha1" else 64
    for item in manifest.files:
        parts = item.path.split("/")
        for index in range(1, len(parts)):
            directory = "/".join(parts[:index])
            existing = state.get(directory)
            if existing is not None and existing.type != "tree":
                raise ValueError("PUBLICATION_INPUT_MISMATCH")
            if existing is None:
                state[directory] = RecursiveTreeEntry(
                    path=directory,
                    mode="040000",
                    type="tree",
                    oid="0" * oid_length,
                )
        existing = state.get(item.path)
        if existing is not None and (
            existing.type != "blob" or existing.mode != "100644"
        ):
            raise ValueError("PUBLICATION_INPUT_MISMATCH")
        state[item.path] = RecursiveTreeEntry(
            path=item.path, mode="100644", type="blob", oid=item.blob_oid
        )

    tree_paths = sorted(
        (path for path, entry in state.items() if entry.type == "tree"),
        key=lambda value: value.count("/"),
        reverse=True,
    )
    for tree_path in tree_paths:
        children = tuple(
            entry
            for path, entry in state.items()
            if (path.rsplit("/", 1)[0] if "/" in path else "") == tree_path
        )
        state[tree_path] = state[tree_path].model_copy(
            update={
                "oid": git_object_oid(
                    "tree", _tree_payload(children), manifest.object_format
                )
            }
        )
    roots = tuple(entry for path, entry in state.items() if "/" not in path)
    root_oid = git_object_oid("tree", _tree_payload(roots), manifest.object_format)
    if root_oid != manifest.proposal_tree_oid:
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    return tuple(
        CompleteTreeEntryIdentity(
            path=entry.path,
            mode=entry.mode,
            object_type=entry.type,
            oid=entry.oid,
        )
        for entry in sorted(state.values(), key=lambda value: value.path)
    )


def derive_expected_identity(
    *,
    manifest: ProposalManifest,
    plan: PublicationPlan,
    admission: PublicationStepAdmission,
    base_tree_closure: BaseTreeClosure,
) -> ExpectedIdentity:
    """Derive one reconciliation target from genuine retained publication data."""

    ordinal = admission.ordinal
    if not 1 <= ordinal <= len(plan.ordered_endpoint_plan):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    if not (
        plan.manifest.content_hash == manifest.content_hash
        and plan.base_ref == manifest.base_ref
        and plan.head_ref == manifest.head_ref
        and plan.expected_tree_oid == manifest.proposal_tree_oid
        and plan.expected_commit_oid == manifest.proposal_commit_oid
        and plan.ordered_endpoint_plan[ordinal - 1] == admission.operation_key
        and plan.ordered_request_hashes[ordinal - 1] == admission.planned_request_hash
        and admission.operation_key in MUTATION_TO_READ
    ):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")

    if admission.operation_key == "git_blob.create":
        preceding_blobs = sum(
            key == "git_blob.create"
            for key in plan.ordered_endpoint_plan[: ordinal - 1]
        )
        if preceding_blobs >= len(manifest.files):
            raise ValueError("PUBLICATION_INPUT_MISMATCH")
        item = manifest.files[preceding_blobs]
        if plan.expected_blob_oids[preceding_blobs] != item.blob_oid:
            raise ValueError("PUBLICATION_INPUT_MISMATCH")
        identity: ExpectedIdentity = BlobExpectedIdentity(
            oid=item.blob_oid,
            content_sha256=item.content_sha256,
            byte_count=item.byte_count,
            source_artifact=item.artifact,
        )
    elif admission.operation_key == "git_tree.create":
        entries = _complete_resultant_tree(manifest, base_tree_closure)
        identity = TreeExpectedIdentity(
            oid=manifest.proposal_tree_oid,
            entries=entries,
            entries_hash=_hash_json([item.model_dump(mode="json") for item in entries]),
        )
    elif admission.operation_key == "git_commit.create":
        identity = CommitExpectedIdentity(
            oid=manifest.proposal_commit_oid,
            tree_oid=manifest.proposal_tree_oid,
            sole_parent_oid=manifest.base_commit_oid,
            message_sha256=manifest.commit_message.content_hash,
        )
    elif admission.operation_key == "git_ref.create":
        identity = RefExpectedIdentity(
            full_ref=manifest.head_ref, target_oid=manifest.proposal_commit_oid
        )
    else:
        identity = PullRequestExpectedIdentity(
            repository_id=manifest.repository_id,
            head_ref=manifest.head_ref,
            head_oid=manifest.proposal_commit_oid,
            base_ref=manifest.base_ref,
            base_oid=manifest.base_commit_oid,
            title_sha256=manifest.pull_request_title.content_hash,
            body_sha256=manifest.pull_request_body.content_hash,
        )

    if admission.expected_identity != expected_identity_hash(identity):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    return identity


class ReconciliationSubject(ClosedModel):
    manifest: RecordReference
    plan: RecordReference
    original_claim: RecordReference
    original_lease: RecordReference
    ambiguous_admission: RecordReference
    base_tree_closure: RecordReference
    base_tree_source_observation: RecordReference
    rate_observation: RecordReference
    terminal_inventory: RecordReference
    repository_profile: RecordReference
    api_profile: RecordReference
    provider_key: RecordReference
    provider_public_key_sha256: str = Field(pattern=HASH_PATTERN)
    foundation_evidence_hash: str = Field(pattern=HASH_PATTERN)
    expected_identity_hash: str = Field(pattern=HASH_PATTERN)


class ReconciliationAuthorization(GitHubRecord):
    profile: Literal["github-publication-fixture-reconciliation-authorization"] = (
        "github-publication-fixture-reconciliation-authorization"
    )
    schema_version: Literal[
        "github-publication-fixture-reconciliation-authorization/0.3.0"
    ] = "github-publication-fixture-reconciliation-authorization/0.3.0"
    reconciliation_id: str = Field(pattern=RECONCILIATION_ID_PATTERN)
    authorized_principal: str = Field(min_length=1, max_length=256)
    issued_at: str
    expires_at: str
    purpose: str = Field(min_length=1, max_length=512)
    subject: ReconciliationSubject
    expected_identity: ExpectedIdentity
    continuation_authorized: Literal[False] = False

    @model_validator(mode="after")
    def bounded_lifetime(self) -> "ReconciliationAuthorization":
        issued = datetime.strptime(self.issued_at, "%Y-%m-%dT%H:%M:%SZ")
        expires = datetime.strptime(self.expires_at, "%Y-%m-%dT%H:%M:%SZ")
        if not 1 <= (expires - issued).total_seconds() <= 900:
            raise ValueError("reconciliation authorization lifetime invalid")
        if self.subject.expected_identity_hash != expected_identity_hash(
            self.expected_identity
        ):
            raise ValueError("reconciliation expected identity mismatch")
        return self


class ReconciliationIntent(GitHubRecord):
    profile: Literal["github-publication-fixture-reconciliation-intent"] = (
        "github-publication-fixture-reconciliation-intent"
    )
    schema_version: Literal[
        "github-publication-fixture-reconciliation-intent/0.3.0"
    ] = "github-publication-fixture-reconciliation-intent/0.3.0"
    reconciliation_id: str = Field(pattern=RECONCILIATION_ID_PATTERN)
    authorization: RecordReference
    subject: ReconciliationSubject
    read_operation_key: Literal[
        "git_blob.get",
        "git_tree.get",
        "commit.get",
        "ref.get",
        "pull_requests.matching.list",
    ]
    method: Literal["GET"] = "GET"
    request_target: str = Field(min_length=1, max_length=2048)
    request_hash: str = Field(pattern=HASH_PATTERN)
    maximum_logical_operations: Literal[1] = 1
    maximum_network_requests: Literal[1] = 1
    automatic_retries: Literal[0] = 0
    fixture_loopback_only: Literal[True] = True


class ReconciliationClaim(GitHubRecord):
    profile: Literal["github-publication-fixture-reconciliation-claim"] = (
        "github-publication-fixture-reconciliation-claim"
    )
    schema_version: Literal["github-publication-fixture-reconciliation-claim/0.3.0"] = (
        "github-publication-fixture-reconciliation-claim/0.3.0"
    )
    reconciliation_id: str = Field(pattern=RECONCILIATION_ID_PATTERN)
    authorization: RecordReference
    intent: RecordReference
    subject: ReconciliationSubject
    state: Literal["claimed"] = "claimed"


class ReconciliationLeaseEvidence(GitHubRecord):
    profile: Literal["github-publication-fixture-reconciliation-lease-evidence"] = (
        "github-publication-fixture-reconciliation-lease-evidence"
    )
    schema_version: Literal[
        "github-publication-fixture-reconciliation-lease-evidence/0.3.0"
    ] = "github-publication-fixture-reconciliation-lease-evidence/0.3.0"
    authorization: RecordReference
    intent: RecordReference
    claim: RecordReference
    subject: ReconciliationSubject
    permission_mode: Literal["read_only"] = "read_only"
    maximum_network_requests: Literal[1] = 1
    automatic_retries: Literal[0] = 0
    credential_present: Literal[False] = False
    fixture_loopback_only: Literal[True] = True


class ReconciliationReadAdmission(GitHubRecord):
    profile: Literal["github-publication-fixture-reconciliation-read-admission"] = (
        "github-publication-fixture-reconciliation-read-admission"
    )
    schema_version: Literal[
        "github-publication-fixture-reconciliation-read-admission/0.3.0"
    ] = "github-publication-fixture-reconciliation-read-admission/0.3.0"
    reconciliation_id: str = Field(pattern=RECONCILIATION_ID_PATTERN)
    claim: RecordReference
    lease_evidence: RecordReference
    subject: ReconciliationSubject
    read_operation_key: Literal[
        "git_blob.get",
        "git_tree.get",
        "commit.get",
        "ref.get",
        "pull_requests.matching.list",
    ]
    method: Literal["GET"] = "GET"
    request_target: str = Field(min_length=1, max_length=2048)
    request_hash: str = Field(pattern=HASH_PATTERN)
    state: Literal["dispatch_admitted_not_confirmed"] = (
        "dispatch_admitted_not_confirmed"
    )
    retry_allowed: Literal[False] = False


class BlobReadProjection(ClosedModel):
    kind: Literal["blob"] = "blob"
    present: bool
    oid: str | None = Field(default=None, pattern=OID_PATTERN)
    content_sha256: str | None = Field(default=None, pattern=HASH_PATTERN)
    byte_count: int | None = Field(default=None, ge=0, le=8 * 1024 * 1024)

    @model_validator(mode="after")
    def exact_presence(self) -> "BlobReadProjection":
        fields = (self.oid, self.content_sha256, self.byte_count)
        if self.present != all(value is not None for value in fields):
            raise ValueError("blob presence shape mismatch")
        if not self.present and any(value is not None for value in fields):
            raise ValueError("absent blob carries result fields")
        return self


class TreeReadProjection(ClosedModel):
    kind: Literal["tree"] = "tree"
    present: bool
    oid: str | None = Field(default=None, pattern=OID_PATTERN)
    entries: tuple[CompleteTreeEntryIdentity, ...] = Field(
        default=(), max_length=100000
    )
    entries_hash: str | None = Field(default=None, pattern=HASH_PATTERN)

    @model_validator(mode="after")
    def exact_presence(self) -> "TreeReadProjection":
        fields = (self.oid, self.entries_hash)
        if self.present != (
            all(value is not None for value in fields) and bool(self.entries)
        ):
            raise ValueError("tree presence shape mismatch")
        if not self.present and (
            any(value is not None for value in fields) or self.entries
        ):
            raise ValueError("absent tree carries result fields")
        if self.present:
            values = [entry.model_dump(mode="json") for entry in self.entries]
            if tuple(entry.path for entry in self.entries) != tuple(
                sorted({entry.path for entry in self.entries})
            ):
                raise ValueError("tree entries must be uniquely sorted")
            if self.entries_hash != _hash_json(values):
                raise ValueError("tree entries hash mismatch")
        return self


class CommitReadProjection(ClosedModel):
    kind: Literal["commit"] = "commit"
    present: bool
    oid: str | None = Field(default=None, pattern=OID_PATTERN)
    tree_oid: str | None = Field(default=None, pattern=OID_PATTERN)
    parents: tuple[str, ...] = Field(default=(), max_length=2)
    message_sha256: str | None = Field(default=None, pattern=HASH_PATTERN)

    @model_validator(mode="after")
    def exact_presence(self) -> "CommitReadProjection":
        scalar_fields = (self.oid, self.tree_oid, self.message_sha256)
        if self.present:
            if (
                not all(value is not None for value in scalar_fields)
                or len(self.parents) != 1
            ):
                raise ValueError("commit presence shape mismatch")
        elif any(value is not None for value in scalar_fields) or self.parents:
            raise ValueError("absent commit carries result fields")
        return self


class RefReadProjection(ClosedModel):
    kind: Literal["ref"] = "ref"
    present: bool
    full_ref: str | None = Field(default=None, max_length=255)
    target_oid: str | None = Field(default=None, pattern=OID_PATTERN)

    @model_validator(mode="after")
    def exact_presence(self) -> "RefReadProjection":
        fields = (self.full_ref, self.target_oid)
        if self.present != all(value is not None for value in fields):
            raise ValueError("ref presence shape mismatch")
        if not self.present and any(value is not None for value in fields):
            raise ValueError("absent ref carries result fields")
        return self


class PullRequestMatch(ClosedModel):
    repository_id: int = Field(gt=0)
    number: int = Field(gt=0)
    head_ref: str = Field(min_length=12, max_length=255)
    head_oid: str = Field(pattern=OID_PATTERN)
    base_ref: str = Field(min_length=12, max_length=255)
    base_oid: str = Field(pattern=OID_PATTERN)
    title_sha256: str = Field(pattern=HASH_PATTERN)
    body_sha256: str = Field(pattern=HASH_PATTERN)


class PullRequestReadProjection(ClosedModel):
    kind: Literal["pull_request"] = "pull_request"
    matches: tuple[PullRequestMatch, ...] = Field(max_length=2)
    pagination_complete: Literal[True] = True


ReadProjection = Annotated[
    Union[
        BlobReadProjection,
        TreeReadProjection,
        CommitReadProjection,
        RefReadProjection,
        PullRequestReadProjection,
    ],
    Field(discriminator="kind"),
]


class FixtureReadTranscript(ClosedModel):
    """One untrusted fixture transcript; never an authenticated remote fact."""

    method: Literal["GET"] = "GET"
    request_target: str = Field(min_length=1, max_length=2048)
    request_hash: str = Field(pattern=HASH_PATTERN)
    accepted_status: Literal[200, 404]
    response_complete: Literal[True] = True
    projection: ReadProjection
    fixture_loopback_only: Literal[True] = True
    live_network_used: Literal[False] = False
    source_trust: Literal["untrusted_fixture_transcript"] = (
        "untrusted_fixture_transcript"
    )

    @model_validator(mode="after")
    def status_matches_projection(self) -> "FixtureReadTranscript":
        if isinstance(self.projection, PullRequestReadProjection):
            if self.accepted_status != 200 or not self.projection.pagination_complete:
                raise ValueError("PUBLICATION_RECONCILIATION_REQUIRED")
        else:
            expected = 200 if self.projection.present else 404
            if self.accepted_status != expected:
                raise ValueError("PUBLICATION_RECONCILIATION_REQUIRED")
        return self


def _exact_attribute(value: object, name: str, admitted: tuple[type, ...]) -> object:
    field = object.__getattribute__(value, name)
    if type(field) not in admitted:
        raise ValueError("PUBLICATION_RECONCILIATION_REQUIRED")
    return field


def _snapshot_fixture_projection(value: object) -> ReadProjection:
    """Copy one projection without invoking caller-overridable methods."""

    if type(value) is BlobReadProjection:
        kind = _exact_attribute(value, "kind", (str,))
        present = _exact_attribute(value, "present", (bool,))
        oid = _exact_attribute(value, "oid", (str, type(None)))
        content_sha256 = _exact_attribute(value, "content_sha256", (str, type(None)))
        byte_count = _exact_attribute(value, "byte_count", (int, type(None)))
        if kind != "blob":
            raise ValueError("PUBLICATION_RECONCILIATION_REQUIRED")
        return BlobReadProjection(
            present=present,
            oid=oid,
            content_sha256=content_sha256,
            byte_count=byte_count,
        )
    if type(value) is TreeReadProjection:
        kind = _exact_attribute(value, "kind", (str,))
        present = _exact_attribute(value, "present", (bool,))
        oid = _exact_attribute(value, "oid", (str, type(None)))
        entries = _exact_attribute(value, "entries", (tuple,))
        entries_hash = _exact_attribute(value, "entries_hash", (str, type(None)))
        if kind != "tree" or any(
            type(entry) is not CompleteTreeEntryIdentity for entry in entries
        ):
            raise ValueError("PUBLICATION_RECONCILIATION_REQUIRED")
        copied_entries = tuple(
            CompleteTreeEntryIdentity(
                path=_exact_attribute(entry, "path", (str,)),
                mode=_exact_attribute(entry, "mode", (str,)),
                object_type=_exact_attribute(entry, "object_type", (str,)),
                oid=_exact_attribute(entry, "oid", (str,)),
            )
            for entry in entries
        )
        return TreeReadProjection(
            present=present,
            oid=oid,
            entries=copied_entries,
            entries_hash=entries_hash,
        )
    if type(value) is CommitReadProjection:
        kind = _exact_attribute(value, "kind", (str,))
        present = _exact_attribute(value, "present", (bool,))
        oid = _exact_attribute(value, "oid", (str, type(None)))
        tree_oid = _exact_attribute(value, "tree_oid", (str, type(None)))
        parents = _exact_attribute(value, "parents", (tuple,))
        message_sha256 = _exact_attribute(value, "message_sha256", (str, type(None)))
        if kind != "commit" or any(type(parent) is not str for parent in parents):
            raise ValueError("PUBLICATION_RECONCILIATION_REQUIRED")
        return CommitReadProjection(
            present=present,
            oid=oid,
            tree_oid=tree_oid,
            parents=tuple(parents),
            message_sha256=message_sha256,
        )
    if type(value) is RefReadProjection:
        kind = _exact_attribute(value, "kind", (str,))
        present = _exact_attribute(value, "present", (bool,))
        full_ref = _exact_attribute(value, "full_ref", (str, type(None)))
        target_oid = _exact_attribute(value, "target_oid", (str, type(None)))
        if kind != "ref":
            raise ValueError("PUBLICATION_RECONCILIATION_REQUIRED")
        return RefReadProjection(
            present=present, full_ref=full_ref, target_oid=target_oid
        )
    if type(value) is PullRequestReadProjection:
        kind = _exact_attribute(value, "kind", (str,))
        matches = _exact_attribute(value, "matches", (tuple,))
        pagination_complete = _exact_attribute(value, "pagination_complete", (bool,))
        if kind != "pull_request" or any(
            type(match) is not PullRequestMatch for match in matches
        ):
            raise ValueError("PUBLICATION_RECONCILIATION_REQUIRED")
        copied_matches = tuple(
            PullRequestMatch(
                repository_id=_exact_attribute(match, "repository_id", (int,)),
                number=_exact_attribute(match, "number", (int,)),
                head_ref=_exact_attribute(match, "head_ref", (str,)),
                head_oid=_exact_attribute(match, "head_oid", (str,)),
                base_ref=_exact_attribute(match, "base_ref", (str,)),
                base_oid=_exact_attribute(match, "base_oid", (str,)),
                title_sha256=_exact_attribute(match, "title_sha256", (str,)),
                body_sha256=_exact_attribute(match, "body_sha256", (str,)),
            )
            for match in matches
        )
        return PullRequestReadProjection(
            matches=copied_matches, pagination_complete=pagination_complete
        )
    raise ValueError("PUBLICATION_RECONCILIATION_REQUIRED")


def _snapshot_fixture_read_transcript(value: object) -> FixtureReadTranscript:
    if type(value) is not FixtureReadTranscript:
        raise ValueError("PUBLICATION_RECONCILIATION_REQUIRED")
    projection = object.__getattribute__(value, "projection")
    snapshot = _snapshot_fixture_projection(projection)
    method = _exact_attribute(value, "method", (str,))
    request_target = _exact_attribute(value, "request_target", (str,))
    request_hash = _exact_attribute(value, "request_hash", (str,))
    accepted_status = _exact_attribute(value, "accepted_status", (int,))
    response_complete = _exact_attribute(value, "response_complete", (bool,))
    fixture_loopback_only = _exact_attribute(value, "fixture_loopback_only", (bool,))
    live_network_used = _exact_attribute(value, "live_network_used", (bool,))
    source_trust = _exact_attribute(value, "source_trust", (str,))
    return FixtureReadTranscript(
        method=method,
        request_target=request_target,
        request_hash=request_hash,
        accepted_status=accepted_status,
        response_complete=response_complete,
        projection=snapshot,
        fixture_loopback_only=fixture_loopback_only,
        live_network_used=live_network_used,
        source_trust=source_trust,
    )


class FixtureReconciliationObservation(GitHubRecord):
    profile: Literal["github-publication-fixture-reconciliation-observation"] = (
        "github-publication-fixture-reconciliation-observation"
    )
    schema_version: Literal[
        "github-publication-fixture-reconciliation-observation/0.3.0"
    ] = "github-publication-fixture-reconciliation-observation/0.3.0"
    admission: RecordReference
    subject: ReconciliationSubject
    read_operation_key: Literal[
        "git_blob.get",
        "git_tree.get",
        "commit.get",
        "ref.get",
        "pull_requests.matching.list",
    ]
    request_target: str = Field(min_length=1, max_length=2048)
    request_hash: str = Field(pattern=HASH_PATTERN)
    accepted_status: Literal[200, 404]
    response_complete: Literal[True] = True
    projection: ReadProjection
    foundation_evidence_hash: str = Field(pattern=HASH_PATTERN)
    foundation_authorization: RecordReference
    foundation_intent: RecordReference
    foundation_claim: RecordReference
    foundation_lease_evidence: RecordReference
    foundation_observation: RecordReference
    provider_key: RecordReference
    provider_public_key_sha256: str = Field(pattern=HASH_PATTERN)
    rate_observation: RecordReference
    fixture_loopback_only: Literal[True] = True
    live_network_used: Literal[False] = False
    source_trust: Literal["untrusted_fixture_transcript"] = (
        "untrusted_fixture_transcript"
    )

    @model_validator(mode="after")
    def exact_response_shape(self) -> "FixtureReconciliationObservation":
        transcript = FixtureReadTranscript(
            request_target=self.request_target,
            request_hash=self.request_hash,
            accepted_status=self.accepted_status,
            projection=self.projection,
        )
        if not transcript.response_complete:
            raise ValueError("PUBLICATION_RECONCILIATION_REQUIRED")
        return self


Classification = Literal[
    "FIXTURE_MATCHED_PRESENT",
    "FIXTURE_MATCHED_ABSENT",
    "FIXTURE_CONFLICT",
    "FIXTURE_STILL_AMBIGUOUS",
]


class ReconciliationReadResult(GitHubRecord):
    profile: Literal["github-publication-fixture-reconciliation-read-result"] = (
        "github-publication-fixture-reconciliation-read-result"
    )
    schema_version: Literal[
        "github-publication-fixture-reconciliation-read-result/0.3.0"
    ] = "github-publication-fixture-reconciliation-read-result/0.3.0"
    reconciliation_id: str = Field(pattern=RECONCILIATION_ID_PATTERN)
    admission: RecordReference
    observation: RecordReference
    subject: ReconciliationSubject
    expected_identity_hash: str = Field(pattern=HASH_PATTERN)
    observed_projection_hash: str = Field(pattern=HASH_PATTERN)
    classification: Classification


class PublicationReconciliationReceipt(GitHubRecord):
    profile: Literal["github-publication-fixture-reconciliation-receipt"] = (
        "github-publication-fixture-reconciliation-receipt"
    )
    schema_version: Literal[
        "github-publication-fixture-reconciliation-receipt/0.3.0"
    ] = "github-publication-fixture-reconciliation-receipt/0.3.0"
    reconciliation_id: str = Field(pattern=RECONCILIATION_ID_PATTERN)
    authorization: RecordReference
    intent: RecordReference
    claim: RecordReference
    lease_evidence: RecordReference
    read_admission: RecordReference
    read_result: RecordReference
    observation: RecordReference
    subject: ReconciliationSubject
    read_operation_key: Literal[
        "git_blob.get",
        "git_tree.get",
        "commit.get",
        "ref.get",
        "pull_requests.matching.list",
    ]
    method: Literal["GET"] = "GET"
    request_target: str = Field(min_length=1, max_length=2048)
    expected_identity_hash: str = Field(pattern=HASH_PATTERN)
    observed_projection_hash: str = Field(pattern=HASH_PATTERN)
    classification: Classification
    source_trust: Literal["untrusted_fixture_transcript"] = (
        "untrusted_fixture_transcript"
    )
    continuation_authorized: Literal[False] = False
    merge_authorized: Literal[False] = False


class RetainedPublicationSubject(ClosedModel):
    manifest: ProposalManifest
    manifest_reference: RecordReference
    plan: PublicationPlan
    plan_reference: RecordReference
    original_claim: PublicationAttemptClaim
    original_claim_reference: RecordReference
    original_lease: PublicationLeaseEvidence
    original_lease_reference: RecordReference
    ambiguous_admission: PublicationStepAdmission
    ambiguous_admission_reference: RecordReference
    original_step_states: tuple[StepState, ...] = Field(min_length=1)
    base_tree_closure: RecordReference
    base_tree_source_observation: RecordReference
    rate_observation: RecordReference
    terminal_inventory: RecordReference
    repository_profile: RecordReference
    api_profile: RecordReference
    provider_key: RecordReference
    provider_public_key_sha256: str = Field(pattern=HASH_PATTERN)

    @model_validator(mode="after")
    def references_are_exact(self) -> "RetainedPublicationSubject":
        pairs = (
            (self.manifest_reference, self.manifest),
            (self.plan_reference, self.plan),
            (self.original_claim_reference, self.original_claim),
            (self.original_lease_reference, self.original_lease),
            (self.ambiguous_admission_reference, self.ambiguous_admission),
        )
        if any(
            reference.content_hash != record.content_hash for reference, record in pairs
        ):
            raise ValueError("PUBLICATION_INPUT_MISMATCH")
        if not (
            self.plan.manifest.content_hash == self.manifest.content_hash
            and self.original_claim.manifest.content_hash == self.manifest.content_hash
            and self.original_claim.plan.content_hash == self.plan.content_hash
            and self.original_lease.attempt_claim.content_hash
            == self.original_claim.content_hash
            and self.ambiguous_admission.attempt_claim.content_hash
            == self.original_claim.content_hash
            and self.ambiguous_admission.lease_evidence.content_hash
            == self.original_lease.content_hash
            and self.original_claim.provider_key == self.provider_key
            and self.original_claim.provider_public_key_sha256
            == self.provider_public_key_sha256
            and self.original_step_states[-1].admission.content_hash
            == self.ambiguous_admission.content_hash
        ):
            raise ValueError("PUBLICATION_INPUT_MISMATCH")
        return self


def _load_exact_record(
    directory: Path, reference: RecordReference, record_type: type[GitHubRecord]
) -> GitHubRecord:
    try:
        raw = read_artifacts_once(
            directory, (reference,), maximum_total_bytes=8 * 1024 * 1024
        )[reference.reference]
        record = record_type.model_validate_json(raw)
    except Exception:
        raise ValueError("PUBLICATION_INPUT_MISMATCH") from None
    if record.content_hash != reference.content_hash:
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    return record


def validate_retained_publication_directories(
    *,
    record_store_directory: Path,
    original_evidence_directory: Path,
    retained: RetainedPublicationSubject,
) -> BaseTreeClosure:
    """Reopen and cross-bind the complete original reconciliation subject."""

    manifest = _load_exact_record(
        record_store_directory, retained.manifest_reference, ProposalManifest
    )
    plan = _load_exact_record(
        record_store_directory, retained.plan_reference, PublicationPlan
    )
    claim = _load_exact_record(
        original_evidence_directory,
        retained.original_claim_reference,
        PublicationAttemptClaim,
    )
    lease = _load_exact_record(
        original_evidence_directory,
        retained.original_lease_reference,
        PublicationLeaseEvidence,
    )
    admission = _load_exact_record(
        original_evidence_directory,
        retained.ambiguous_admission_reference,
        PublicationStepAdmission,
    )
    closure = _load_exact_record(
        record_store_directory, retained.base_tree_closure, BaseTreeClosure
    )
    source = _load_exact_record(
        record_store_directory,
        retained.base_tree_source_observation,
        RecursiveTreeObservation,
    )
    rate = _load_exact_record(
        record_store_directory, retained.rate_observation, RateBudgetObservation
    )
    repository = _load_exact_record(
        record_store_directory,
        retained.repository_profile,
        GitHubRepositoryProfile,
    )
    api = _load_exact_record(
        record_store_directory, retained.api_profile, GitHubApiProfile
    )
    provider = _load_exact_record(
        record_store_directory,
        retained.provider_key,
        GitHubCredentialProviderKey,
    )
    terminal = _load_exact_record(
        original_evidence_directory,
        retained.terminal_inventory,
        TerminalArtifactInventory,
    )
    assert isinstance(manifest, ProposalManifest)
    assert isinstance(plan, PublicationPlan)
    assert isinstance(claim, PublicationAttemptClaim)
    assert isinstance(lease, PublicationLeaseEvidence)
    assert isinstance(admission, PublicationStepAdmission)
    assert isinstance(closure, BaseTreeClosure)
    assert isinstance(source, RecursiveTreeObservation)
    assert isinstance(rate, RateBudgetObservation)
    assert isinstance(repository, GitHubRepositoryProfile)
    assert isinstance(api, GitHubApiProfile)
    assert isinstance(provider, GitHubCredentialProviderKey)
    assert isinstance(terminal, TerminalArtifactInventory)

    for reopened, supplied in (
        (manifest, retained.manifest),
        (plan, retained.plan),
        (claim, retained.original_claim),
        (lease, retained.original_lease),
        (admission, retained.ambiguous_admission),
    ):
        if reopened != supplied:
            raise ValueError("PUBLICATION_INPUT_MISMATCH")

    state_hash = _hash_json(
        [state.model_dump(mode="json") for state in retained.original_step_states]
    )
    final_state = retained.original_step_states[-1]
    if not isinstance(
        final_state, (MutationAdmittedWithoutResult, MutationResultPresent)
    ):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    last_record = (
        final_state.result
        if isinstance(final_state, MutationResultPresent)
        else final_state.admission
    )
    if not (
        terminal.original_claim.content_hash == claim.content_hash
        and terminal.last_step_record == last_record
        and terminal.step_state_inventory_hash == state_hash
        and final_state.admission.content_hash == admission.content_hash
    ):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")

    for state in retained.original_step_states:
        _load_exact_record(
            original_evidence_directory,
            state.admission,
            PublicationStepAdmission,
        )
        result_reference = getattr(state, "result", None)
        if result_reference is not None:
            _load_exact_record(
                original_evidence_directory,
                result_reference,
                PublicationStepResult,
            )

    receipt_path = original_evidence_directory / "receipt.json"
    failure_path = original_evidence_directory / "terminal-failure.json"
    if (
        receipt_path.is_file() != terminal.receipt_present
        or failure_path.is_file() != terminal.failure_capsule_present
        or (receipt_path.is_file() and failure_path.is_file())
    ):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    terminal_record: PublicationReceipt | PublicationTerminalFailure | None = None
    if terminal.receipt is not None:
        terminal_record = _load_exact_record(
            original_evidence_directory, terminal.receipt, PublicationReceipt
        )
    elif terminal.failure_capsule is not None:
        terminal_record = _load_exact_record(
            original_evidence_directory,
            terminal.failure_capsule,
            PublicationTerminalFailure,
        )
    if terminal_record is not None and tuple(terminal_record.step_states) != tuple(
        retained.original_step_states
    ):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")

    if not (
        manifest.repository_profile == retained.repository_profile
        and manifest.api_profile == retained.api_profile
        and manifest.base_tree_closure == retained.base_tree_closure
        and closure.source_observation == retained.base_tree_source_observation
        and closure.repository_profile == retained.repository_profile
        and closure.api_profile == retained.api_profile
        and source.repository_profile == retained.repository_profile
        and source.api_profile == retained.api_profile
        and rate.repository_profile == retained.repository_profile
        and rate.api_profile == retained.api_profile
        and rate.provider_key == retained.provider_key
        and rate.provider_public_key_sha256 == retained.provider_public_key_sha256
        and provider.public_key_sha256 == retained.provider_public_key_sha256
        and repository.repository_id == manifest.repository_id
        and repository.account_id == manifest.account_id
        and closure.repository_id == manifest.repository_id
        and closure.account_id == manifest.account_id
        and source.repository_id == manifest.repository_id
        and source.account_id == manifest.account_id
        and rate.repository_id == manifest.repository_id
        and rate.account_id == manifest.account_id
        and lease.repository_profile == retained.repository_profile
        and lease.api_profile == retained.api_profile
        and lease.provider_key == retained.provider_key
        and plan.rate_observation == retained.rate_observation
        and claim.rate_observation == retained.rate_observation
        and lease.rate_observation == retained.rate_observation
        and admission.rate_observation == retained.rate_observation
        and admission.provider_key == retained.provider_key
        and admission.provider_public_key_sha256 == retained.provider_public_key_sha256
        and admission.lease_evidence.content_hash == lease.content_hash
    ):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    return closure


class ReconciliationBundle(ClosedModel):
    state: Literal["read_admitted_without_result", "read_result_present"]
    authorization: ReconciliationAuthorization
    intent: ReconciliationIntent
    claim: ReconciliationClaim
    lease_evidence: ReconciliationLeaseEvidence
    read_admission: ReconciliationReadAdmission
    observation: FixtureReconciliationObservation | None = None
    read_result: ReconciliationReadResult | None = None
    receipt: PublicationReconciliationReceipt | None = None

    @model_validator(mode="after")
    def exact_predecessors(self) -> "ReconciliationBundle":
        a, i, c, lease = (
            self.authorization,
            self.intent,
            self.claim,
            self.lease_evidence,
        )
        d, o, r, receipt = (
            self.read_admission,
            self.observation,
            self.read_result,
            self.receipt,
        )
        subject = a.subject
        if self.state == "read_admitted_without_result":
            if any(value is not None for value in (o, r, receipt)):
                raise ValueError("reconciliation pending shape mismatch")
            if not all(
                (
                    i.authorization.content_hash == a.content_hash,
                    c.authorization.content_hash == a.content_hash,
                    c.intent.content_hash == i.content_hash,
                    lease.authorization.content_hash == a.content_hash,
                    lease.intent.content_hash == i.content_hash,
                    lease.claim.content_hash == c.content_hash,
                    d.claim.content_hash == c.content_hash,
                    d.lease_evidence.content_hash == lease.content_hash,
                    i.subject == c.subject == lease.subject == d.subject == subject,
                    i.read_operation_key == d.read_operation_key,
                    i.method == d.method == "GET",
                    i.request_target == d.request_target,
                    i.request_hash == d.request_hash,
                )
            ):
                raise ValueError("reconciliation predecessor chain mismatch")
            return self
        if o is None or r is None or receipt is None:
            raise ValueError("reconciliation completed shape mismatch")
        if not all(
            (
                i.authorization.content_hash == a.content_hash,
                c.authorization.content_hash == a.content_hash,
                c.intent.content_hash == i.content_hash,
                lease.authorization.content_hash == a.content_hash,
                lease.intent.content_hash == i.content_hash,
                lease.claim.content_hash == c.content_hash,
                d.claim.content_hash == c.content_hash,
                d.lease_evidence.content_hash == lease.content_hash,
                o.admission.content_hash == d.content_hash,
                o.foundation_evidence_hash == subject.foundation_evidence_hash,
                o.request_hash == d.request_hash,
                r.admission.content_hash == d.content_hash,
                r.observation.content_hash == o.content_hash,
                receipt.authorization.content_hash == a.content_hash,
                receipt.intent.content_hash == i.content_hash,
                receipt.claim.content_hash == c.content_hash,
                receipt.lease_evidence.content_hash == lease.content_hash,
                receipt.read_admission.content_hash == d.content_hash,
                receipt.read_result.content_hash == r.content_hash,
                receipt.observation.content_hash == o.content_hash,
                i.subject
                == c.subject
                == lease.subject
                == d.subject
                == o.subject
                == r.subject
                == receipt.subject
                == subject,
                i.read_operation_key
                == d.read_operation_key
                == o.read_operation_key
                == receipt.read_operation_key,
                i.method == d.method == receipt.method == "GET",
                i.request_target
                == d.request_target
                == o.request_target
                == receipt.request_target,
                i.request_hash == d.request_hash == o.request_hash,
                r.classification == receipt.classification,
                r.expected_identity_hash
                == receipt.expected_identity_hash
                == subject.expected_identity_hash,
            )
        ):
            raise ValueError("reconciliation predecessor chain mismatch")
        return self


def _classify(
    expected: ExpectedIdentity, evidence: FixtureReadTranscript
) -> Classification:
    projection = evidence.projection
    if projection.kind != expected.kind:
        raise ValueError("PUBLICATION_RECONCILIATION_REQUIRED")
    if isinstance(expected, PullRequestExpectedIdentity):
        assert isinstance(projection, PullRequestReadProjection)
        if not projection.matches:
            return "FIXTURE_MATCHED_ABSENT"
        exact = tuple(
            match
            for match in projection.matches
            if (
                match.repository_id == expected.repository_id
                and match.head_ref == expected.head_ref
                and match.head_oid == expected.head_oid
                and match.base_ref == expected.base_ref
                and match.base_oid == expected.base_oid
                and match.title_sha256 == expected.title_sha256
                and match.body_sha256 == expected.body_sha256
            )
        )
        return (
            "FIXTURE_MATCHED_PRESENT"
            if len(projection.matches) == len(exact) == 1
            else "FIXTURE_CONFLICT"
        )
    if not projection.present:
        return "FIXTURE_MATCHED_ABSENT"
    if isinstance(expected, BlobExpectedIdentity):
        assert isinstance(projection, BlobReadProjection)
        matches = (
            projection.oid == expected.oid
            and projection.content_sha256 == expected.content_sha256
            and projection.byte_count == expected.byte_count
        )
    elif isinstance(expected, TreeExpectedIdentity):
        assert isinstance(projection, TreeReadProjection)
        matches = (
            projection.oid == expected.oid
            and projection.entries == expected.entries
            and projection.entries_hash == expected.entries_hash
        )
    elif isinstance(expected, CommitExpectedIdentity):
        assert isinstance(projection, CommitReadProjection)
        matches = (
            projection.oid == expected.oid
            and projection.tree_oid == expected.tree_oid
            and projection.parents == (expected.sole_parent_oid,)
            and projection.message_sha256 == expected.message_sha256
        )
    else:
        assert isinstance(expected, RefExpectedIdentity)
        assert isinstance(projection, RefReadProjection)
        matches = (
            projection.full_ref == expected.full_ref
            and projection.target_oid == expected.target_oid
        )
    return "FIXTURE_MATCHED_PRESENT" if matches else "FIXTURE_CONFLICT"


def _validate_foundation_evidence(
    *,
    evidence: Stage21AObservationEvidence,
    retained: RetainedPublicationSubject,
    record_store_directory: Path,
    authorized_principal: str,
    created_at: str,
) -> str:
    """Bind one signed Stage 21A repository observation to this fixture read."""

    try:
        evidence = Stage21AObservationEvidence.model_validate(
            evidence.model_dump(mode="python")
        )
    except Exception:
        raise ValueError("PUBLICATION_RECONCILIATION_REQUIRED") from None
    repository = _load_exact_record(
        record_store_directory,
        retained.repository_profile,
        GitHubRepositoryProfile,
    )
    api = _load_exact_record(
        record_store_directory, retained.api_profile, GitHubApiProfile
    )
    provider = _load_exact_record(
        record_store_directory,
        retained.provider_key,
        GitHubCredentialProviderKey,
    )
    try:
        foundation_authorization = _load_exact_record(
            record_store_directory,
            evidence.intent_record.authorization,
            GitHubOperationAuthorization,
        )
        foundation_intent = _load_exact_record(
            record_store_directory,
            evidence.attempt_claim_record.intent,
            GitHubOperationIntent,
        )
        foundation_claim = _load_exact_record(
            record_store_directory,
            evidence.lease_evidence_record.attempt_claim,
            GitHubOperationAttemptClaim,
        )
        foundation_lease = _load_exact_record(
            record_store_directory,
            evidence.observation_record.lease_evidence,
            CredentialLeaseEvidence,
        )
        foundation_observation = _load_exact_record(
            record_store_directory,
            evidence.observation_reference,
            GitHubObservation,
        )
    except ValueError:
        raise ValueError("PUBLICATION_RECONCILIATION_REQUIRED") from None
    assert isinstance(repository, GitHubRepositoryProfile)
    assert isinstance(api, GitHubApiProfile)
    assert isinstance(provider, GitHubCredentialProviderKey)
    observation = evidence.observation_record
    authorization = evidence.authorization_record
    observed_at = datetime.strptime(observation.observed_at, "%Y-%m-%dT%H:%M:%SZ")
    current = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
    if not (
        evidence.repository_profile_record == repository
        and evidence.api_profile_record == api
        and evidence.provider_key_record == provider
        and evidence.authorization_record == foundation_authorization
        and evidence.intent_record == foundation_intent
        and evidence.attempt_claim_record == foundation_claim
        and evidence.lease_evidence_record == foundation_lease
        and evidence.observation_record == foundation_observation
        and evidence.provider_key_reference == retained.provider_key
        and authorization.authorized_principal == authorized_principal
        and authorization.operation_key == "repository.get"
        and authorization.path_parameters == {}
        and authorization.query_parameters == {}
        and observation.operation_key == "repository.get"
        and observation.path_parameters == {}
        and observation.query_parameters == {}
        and observation.repository_id == retained.manifest.repository_id
        and observation.account_id == retained.manifest.account_id
        and observation.repository_profile == retained.repository_profile
        and observation.api_profile == retained.api_profile
        and evidence.observation_reference.content_hash == observation.content_hash
        and provider.public_key_sha256 == retained.provider_public_key_sha256
        and 0 <= (current - observed_at).total_seconds() <= 900
    ):
        raise ValueError("PUBLICATION_RECONCILIATION_REQUIRED")
    return _hash_json(evidence.model_dump(mode="json"))


def assemble_fixture_reconciliation(
    *,
    retained: RetainedPublicationSubject,
    record_store_directory: Path,
    original_evidence_directory: Path,
    reconciliation_id: str,
    authorized_principal: str,
    issued_at: str,
    expires_at: str,
    created_at: str,
    purpose: str,
    foundation_evidence: Stage21AObservationEvidence,
    read_evidence: FixtureReadTranscript | None,
) -> ReconciliationBundle:
    """Assemble one immutable fixture-only reconciliation record chain."""

    closure = validate_retained_publication_directories(
        record_store_directory=record_store_directory,
        original_evidence_directory=original_evidence_directory,
        retained=retained,
    )
    expected = derive_expected_identity(
        manifest=retained.manifest,
        plan=retained.plan,
        admission=retained.ambiguous_admission,
        base_tree_closure=closure,
    )
    expected_hash = expected_identity_hash(expected)
    foundation_hash = _validate_foundation_evidence(
        evidence=foundation_evidence,
        retained=retained,
        record_store_directory=record_store_directory,
        authorized_principal=authorized_principal,
        created_at=created_at,
    )
    subject = ReconciliationSubject(
        manifest=retained.manifest_reference,
        plan=retained.plan_reference,
        original_claim=retained.original_claim_reference,
        original_lease=retained.original_lease_reference,
        ambiguous_admission=retained.ambiguous_admission_reference,
        base_tree_closure=retained.base_tree_closure,
        base_tree_source_observation=retained.base_tree_source_observation,
        rate_observation=retained.rate_observation,
        terminal_inventory=retained.terminal_inventory,
        repository_profile=retained.repository_profile,
        api_profile=retained.api_profile,
        provider_key=retained.provider_key,
        provider_public_key_sha256=retained.provider_public_key_sha256,
        foundation_evidence_hash=foundation_hash,
        expected_identity_hash=expected_hash,
    )
    read_key = MUTATION_TO_READ[retained.ambiguous_admission.operation_key]
    request_target = fixture_read_target(
        manifest=retained.manifest,
        read_operation_key=read_key,
        expected=expected,
    )
    request_hash = fixture_read_request_hash(
        method="GET",
        target=request_target,
        expected_identity_digest=expected_hash,
    )
    auth = seal_record(
        ReconciliationAuthorization,
        {
            "reconciliation_id": reconciliation_id,
            "authorized_principal": authorized_principal,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "purpose": purpose,
            "subject": subject,
            "expected_identity": expected,
            "created_at": created_at,
        },
    )
    auth_ref = _rr(f"reconciliation-auth-{reconciliation_id}.json", auth)
    intent = seal_record(
        ReconciliationIntent,
        {
            "reconciliation_id": reconciliation_id,
            "authorization": auth_ref,
            "subject": subject,
            "read_operation_key": read_key,
            "request_target": request_target,
            "request_hash": request_hash,
            "created_at": created_at,
        },
    )
    intent_ref = _rr(f"reconciliation-intent-{reconciliation_id}.json", intent)
    claim = seal_record(
        ReconciliationClaim,
        {
            "reconciliation_id": reconciliation_id,
            "authorization": auth_ref,
            "intent": intent_ref,
            "subject": subject,
            "created_at": created_at,
        },
    )
    claim_ref = _rr(f"reconciliation-claim-{reconciliation_id}.json", claim)
    lease = seal_record(
        ReconciliationLeaseEvidence,
        {
            "authorization": auth_ref,
            "intent": intent_ref,
            "claim": claim_ref,
            "subject": subject,
            "created_at": created_at,
        },
    )
    lease_ref = _rr(f"reconciliation-lease-{reconciliation_id}.json", lease)
    admission = seal_record(
        ReconciliationReadAdmission,
        {
            "reconciliation_id": reconciliation_id,
            "claim": claim_ref,
            "lease_evidence": lease_ref,
            "subject": subject,
            "read_operation_key": read_key,
            "request_target": request_target,
            "request_hash": request_hash,
            "created_at": created_at,
        },
    )
    admission_ref = _rr(f"reconciliation-admission-{reconciliation_id}.json", admission)
    if read_evidence is None:
        return ReconciliationBundle(
            state="read_admitted_without_result",
            authorization=auth,
            intent=intent,
            claim=claim,
            lease_evidence=lease,
            read_admission=admission,
        )
    read_evidence = _snapshot_fixture_read_transcript(read_evidence)
    if not (
        read_evidence.method == "GET"
        and read_evidence.request_target == request_target
        and read_evidence.request_hash == request_hash
    ):
        raise ValueError("PUBLICATION_RECONCILIATION_REQUIRED")
    expected_kind = {
        "git_blob.get": "blob",
        "git_tree.get": "tree",
        "commit.get": "commit",
        "ref.get": "ref",
        "pull_requests.matching.list": "pull_request",
    }[read_key]
    if read_evidence.projection.kind != expected_kind:
        raise ValueError("PUBLICATION_RECONCILIATION_REQUIRED")
    observation = seal_record(
        FixtureReconciliationObservation,
        {
            "admission": admission_ref,
            "subject": subject,
            "read_operation_key": read_key,
            "request_target": request_target,
            "request_hash": request_hash,
            "accepted_status": read_evidence.accepted_status,
            "response_complete": read_evidence.response_complete,
            "projection": read_evidence.projection,
            "foundation_evidence_hash": foundation_hash,
            "foundation_authorization": foundation_evidence.intent_record.authorization,
            "foundation_intent": foundation_evidence.attempt_claim_record.intent,
            "foundation_claim": foundation_evidence.lease_evidence_record.attempt_claim,
            "foundation_lease_evidence": foundation_evidence.observation_record.lease_evidence,
            "foundation_observation": foundation_evidence.observation_reference,
            "provider_key": retained.provider_key,
            "provider_public_key_sha256": retained.provider_public_key_sha256,
            "rate_observation": retained.rate_observation,
            "created_at": created_at,
        },
    )
    observation_ref = _rr(
        f"reconciliation-observation-{reconciliation_id}.json", observation
    )
    classification = _classify(expected, read_evidence)
    observed_hash = _hash_json(read_evidence.projection.model_dump(mode="json"))
    result = seal_record(
        ReconciliationReadResult,
        {
            "reconciliation_id": reconciliation_id,
            "admission": admission_ref,
            "observation": observation_ref,
            "subject": subject,
            "expected_identity_hash": expected_hash,
            "observed_projection_hash": observed_hash,
            "classification": classification,
            "created_at": created_at,
        },
    )
    result_ref = _rr(f"reconciliation-result-{reconciliation_id}.json", result)
    receipt = seal_record(
        PublicationReconciliationReceipt,
        {
            "reconciliation_id": reconciliation_id,
            "authorization": auth_ref,
            "intent": intent_ref,
            "claim": claim_ref,
            "lease_evidence": lease_ref,
            "read_admission": admission_ref,
            "read_result": result_ref,
            "observation": observation_ref,
            "subject": subject,
            "read_operation_key": read_key,
            "request_target": request_target,
            "expected_identity_hash": expected_hash,
            "observed_projection_hash": observed_hash,
            "classification": classification,
            "created_at": created_at,
        },
    )
    return ReconciliationBundle(
        state="read_result_present",
        authorization=auth,
        intent=intent,
        claim=claim,
        lease_evidence=lease,
        read_admission=admission,
        observation=observation,
        read_result=result,
        receipt=receipt,
    )


def _is_link_or_reparse(path: Path) -> bool:
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return True
    return path.is_symlink() or bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _fixture_reconciliation_directory(
    workspace: Workspace, reconciliation_id: str
) -> Path:
    """Derive one no-link reconciliation directory inside external state."""

    if (
        type(reconciliation_id) is not str
        or re.fullmatch(RECONCILIATION_ID_PATTERN, reconciliation_id) is None
    ):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    root = Path(workspace.root).absolute()
    try:
        resolved_root = root.resolve(strict=True)
    except OSError:
        raise ValueError("PUBLICATION_INPUT_MISMATCH") from None
    if resolved_root != root or root.name != ".conclave" or _is_link_or_reparse(root):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    if not workspace.config_path.is_file() or _is_link_or_reparse(
        workspace.config_path
    ):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    if (root / ".git").exists() or any(
        (parent / ".git").exists() for parent in root.parents
    ):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")

    github_root = workspace.root / "github"
    if not github_root.is_dir() or _is_link_or_reparse(github_root):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    base = workspace.github_publication_fixture_reconciliations_dir.absolute()
    try:
        base.relative_to(root)
    except ValueError:
        raise ValueError("PUBLICATION_INPUT_MISMATCH") from None
    if base.exists() and (not base.is_dir() or _is_link_or_reparse(base)):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    base.mkdir(parents=False, exist_ok=True)
    if base.resolve(strict=True) != base or _is_link_or_reparse(base):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")

    directory = base / reconciliation_id
    if directory.exists() and (
        not directory.is_dir() or _is_link_or_reparse(directory)
    ):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    directory.mkdir(parents=False, exist_ok=True)
    if directory.resolve(strict=True) != directory or _is_link_or_reparse(directory):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    return directory


_PERSISTENCE_MODEL_TYPES = frozenset(
    {
        ReconciliationBundle,
        ReconciliationAuthorization,
        ReconciliationIntent,
        ReconciliationClaim,
        ReconciliationLeaseEvidence,
        ReconciliationReadAdmission,
        FixtureReconciliationObservation,
        ReconciliationReadResult,
        PublicationReconciliationReceipt,
        ReconciliationSubject,
        BlobExpectedIdentity,
        TreeExpectedIdentity,
        CommitExpectedIdentity,
        RefExpectedIdentity,
        PullRequestExpectedIdentity,
        CompleteTreeEntryIdentity,
        BlobReadProjection,
        TreeReadProjection,
        CommitReadProjection,
        RefReadProjection,
        PullRequestReadProjection,
        PullRequestMatch,
        RecordReference,
    }
)


def _persistence_primitive(value: object) -> object:
    """Extract an exact primitive graph without calling caller-owned methods."""

    value_type = type(value)
    if value_type in _PERSISTENCE_MODEL_TYPES:
        fields = value_type.model_fields
        raw = object.__getattribute__(value, "__dict__")
        if type(raw) is not dict:
            raise ValueError("PUBLICATION_INPUT_MISMATCH")
        raw_keys = tuple(dict.keys(raw))
        if any(type(key) is not str for key in raw_keys) or set(raw_keys) != set(
            fields
        ):
            raise ValueError("PUBLICATION_INPUT_MISMATCH")
        return {
            name: _persistence_primitive(dict.__getitem__(raw, name)) for name in fields
        }
    if value_type is tuple:
        return tuple(_persistence_primitive(item) for item in value)
    if value_type is dict:
        keys = tuple(dict.keys(value))
        if any(type(key) is not str for key in keys):
            raise ValueError("PUBLICATION_INPUT_MISMATCH")
        return {
            key: _persistence_primitive(dict.__getitem__(value, key)) for key in keys
        }
    if value_type in {str, int, bool, type(None)}:
        return value
    raise ValueError("PUBLICATION_INPUT_MISMATCH")


def _snapshot_reconciliation_bundle(value: object) -> ReconciliationBundle:
    """Return a fully revalidated exact snapshot or fail before any write."""

    if type(value) is not ReconciliationBundle:
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    try:
        primitive = _persistence_primitive(value)
        snapshot = ReconciliationBundle.model_validate(primitive)
    except Exception:
        raise ValueError("PUBLICATION_INPUT_MISMATCH") from None
    _persistence_primitive(snapshot)
    return snapshot


def persist_fixture_reconciliation(
    workspace: Workspace, bundle: ReconciliationBundle
) -> tuple[Path, ...]:
    """Persist records under verified external state, in predecessor order."""

    bundle = _snapshot_reconciliation_bundle(bundle)
    rid = bundle.authorization.reconciliation_id
    directory = _fixture_reconciliation_directory(workspace, rid)
    records: tuple[tuple[str, GitHubRecord], ...] = (
        (f"reconciliation-auth-{rid}.json", bundle.authorization),
        (f"reconciliation-intent-{rid}.json", bundle.intent),
        (f"reconciliation-claim-{rid}.json", bundle.claim),
        (f"reconciliation-lease-{rid}.json", bundle.lease_evidence),
        (f"reconciliation-admission-{rid}.json", bundle.read_admission),
    )
    if bundle.state == "read_result_present":
        assert bundle.observation is not None
        assert bundle.read_result is not None
        assert bundle.receipt is not None
        records += (
            (f"reconciliation-observation-{rid}.json", bundle.observation),
            (f"reconciliation-result-{rid}.json", bundle.read_result),
            (f"reconciliation-receipt-{rid}.json", bundle.receipt),
        )
    paths: list[Path] = []
    for name, record in records:
        path, _ = write_durable_record(directory / name, record, reject_existing=True)
        paths.append(path)
    return tuple(paths)
