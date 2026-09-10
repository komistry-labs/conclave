"""Deterministic, network-free foundations for corrected Stage 21B.

This module deliberately contains no credential discovery and no transport.
It verifies a complete recursive base-tree projection and derives exact Git
objects for a bounded proposal before any publication authority can be used.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import os
import stat
from urllib.parse import quote
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, Mapping, Sequence

from pydantic import Field, field_validator, model_validator

from .github_foundation import GitHubRecord, RecordReference
from .identity import ClosedModel

BASE_TREE_CLOSURE_SCHEMA = "github-base-tree-closure/0.1.0"
TREE_SOURCE_SCHEMA = "github-recursive-tree-observation/0.1.0"
BASE_IDENTITY_OBSERVATION_SCHEMA = "github-base-tree-identity-observation/0.1.0"
PUBLICATION_REPOSITORY_EXTENSION_SCHEMA = (
    "github-publication-repository-extension/0.1.0"
)
MAX_TREE_ENTRIES = 100_000
MAX_CLOSURE_BYTES = 8 * 1024 * 1024
MAX_PATH_BYTES = 512
MAX_PATH_DEPTH = 32
MAX_SEGMENT_BYTES = 256
RECURSIVE_TREE_ENDPOINT_VERSION = "github-21b-erratum-tree-source/0.1.0"

# Exact identities of the four frozen governance documents that authorize the
# bounded Stage 21B base-tree closure.  Records must carry these values rather
# than merely supplying syntactically valid SHA-256 strings.
INCREMENT_21_PROTOCOL_HASH = (
    "sha256:89a05211a4323db2e79d2854952b24ce033c71f357430c7ac839457ff0878d75"
)
STAGE_21A_PROTOCOL_HASH = (
    "sha256:4493237e46c72b3b3eed8150e4994580568831e55ffa24046b5058eb4a7b0b5f"
)
STAGE_21B_PROTOCOL_HASH = (
    "sha256:b90c97284afec9ac7cef44fd9186b38f9e2a86630e283c593dc2ed95e88384c4"
)
STAGE_21B_ERRATUM_HASH = (
    "sha256:f79aae70e15dd90bda10948ee172f77acac3557a87ff2d2f1c35a65a1ed0658e"
)
# Descriptive alias retained for callers that distinguish future errata.
STAGE_21B_ERRATUM_0001_HASH = STAGE_21B_ERRATUM_HASH

GitObjectFormat = Literal["sha1", "sha256"]
GitEntryType = Literal["tree", "blob", "commit"]
ALLOWED_BASE_FORMS = frozenset(
    {
        ("040000", "tree"),
        ("100644", "blob"),
        ("100755", "blob"),
        ("120000", "blob"),
        ("160000", "commit"),
    }
)
_OID_LENGTH = {"sha1": 40, "sha256": 64}
_WINDOWS_DEVICES = frozenset(
    {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{i}" for i in range(1, 10)),
        *(f"lpt{i}" for i in range(1, 10)),
    }
)
_HEAD_REF = re.compile(
    r"refs/heads/conclave/"
    r"[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/"
    r"[a-z0-9](?:[a-z0-9]|-(?=[a-z0-9])){0,47}$"
)
_PROHIBITED_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".pkcs12")
_CONTROL_TERMS = frozenset(
    {
        "kos",
        "idm",
        "constitution",
        "membership",
        "identity",
        "signing",
        "credential",
        "credentials",
        "ruleset",
        "deployment",
        "workflow",
        "workflows",
        "release",
        "production",
    }
)


@dataclass(frozen=True)
class RecursiveTreeSourceRequest:
    operation_key: Literal["git_tree_recursive.get"]
    method: Literal["GET"]
    target: str
    maximum_network_requests: Literal[1] = 1
    maximum_retries: Literal[0] = 0


class RecursiveTreeAuthorization(GitHubRecord):
    profile: Literal["github-recursive-tree-authorization"] = (
        "github-recursive-tree-authorization"
    )
    schema_version: Literal["github-recursive-tree-authorization/0.1.0"] = (
        "github-recursive-tree-authorization/0.1.0"
    )
    authorization_id: str = Field(min_length=1, max_length=128)
    repository_profile: RecordReference
    api_profile: RecordReference
    repository_extension: RecordReference
    repository_id: int = Field(gt=0)
    account_id: int = Field(gt=0)
    base_ref: str
    base_commit_oid: str
    root_tree_oid: str
    object_format: GitObjectFormat
    operation_key: Literal["git_tree_recursive.get"] = "git_tree_recursive.get"
    method: Literal["GET"] = "GET"
    authorized_principal: str = Field(min_length=1, max_length=256)
    issued_at: str
    expires_at: str
    maximum_network_requests: Literal[1] = 1
    automatic_retries: Literal[0] = 0

    @model_validator(mode="after")
    def bounded(self) -> "RecursiveTreeAuthorization":
        issued = datetime.strptime(self.issued_at, "%Y-%m-%dT%H:%M:%SZ")
        expires = datetime.strptime(self.expires_at, "%Y-%m-%dT%H:%M:%SZ")
        if not 1 <= (expires - issued).total_seconds() <= 900:
            raise ValueError("recursive tree authorization lifetime is invalid")
        _validate_oid(self.base_commit_oid, self.object_format)
        _validate_oid(self.root_tree_oid, self.object_format)
        return self


class RecursiveTreeIntent(GitHubRecord):
    profile: Literal["github-recursive-tree-intent"] = "github-recursive-tree-intent"
    schema_version: Literal["github-recursive-tree-intent/0.1.0"] = (
        "github-recursive-tree-intent/0.1.0"
    )
    intent_id: str = Field(min_length=1, max_length=128)
    authorization: RecordReference
    repository_profile: RecordReference
    api_profile: RecordReference
    repository_extension: RecordReference
    repository_id: int = Field(gt=0)
    account_id: int = Field(gt=0)
    base_ref: str
    root_tree_oid: str
    object_format: GitObjectFormat
    operation_key: Literal["git_tree_recursive.get"] = "git_tree_recursive.get"
    request_target_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    maximum_network_requests: Literal[1] = 1
    automatic_retries: Literal[0] = 0
    not_after: str


class RecursiveTreeAttemptClaim(GitHubRecord):
    profile: Literal["github-recursive-tree-attempt-claim"] = (
        "github-recursive-tree-attempt-claim"
    )
    schema_version: Literal["github-recursive-tree-attempt-claim/0.1.0"] = (
        "github-recursive-tree-attempt-claim/0.1.0"
    )
    claim_id: str = Field(min_length=1, max_length=128)
    authorization: RecordReference
    intent: RecordReference
    repository_profile: RecordReference
    api_profile: RecordReference
    repository_id: int = Field(gt=0)
    account_id: int = Field(gt=0)
    operation_key: Literal["git_tree_recursive.get"] = "git_tree_recursive.get"
    state: Literal["claimed"] = "claimed"


class RecursiveTreeLeaseEvidence(GitHubRecord):
    profile: Literal["github-recursive-tree-lease-evidence"] = (
        "github-recursive-tree-lease-evidence"
    )
    schema_version: Literal["github-recursive-tree-lease-evidence/0.1.0"] = (
        "github-recursive-tree-lease-evidence/0.1.0"
    )
    authorization: RecordReference
    intent: RecordReference
    claim: RecordReference
    credential_lease_evidence: RecordReference
    provider_key: RecordReference
    provider_public_key_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    provider_id: str = Field(min_length=1, max_length=64)
    provider_version: str = Field(min_length=1, max_length=64)
    repository_id: int = Field(gt=0)
    account_id: int = Field(gt=0)
    app_id: int = Field(gt=0)
    installation_id: int = Field(gt=0)
    permission_mode: Literal["read_only"] = "read_only"
    maximum_network_requests: Literal[1] = 1
    automatic_retries: Literal[0] = 0
    credential_present: Literal[False] = False
    network_started_at_evidence_creation: Literal[False] = False


def build_recursive_tree_source_request(
    *, owner: str, repository: str, tree_oid: str, object_format: GitObjectFormat
) -> RecursiveTreeSourceRequest:
    """Build the erratum endpoint without altering frozen Stage 21A tables."""

    if re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", owner) is None:
        raise ValueError("invalid owner")
    if re.fullmatch(
        r"[A-Za-z0-9_.-]{1,100}", repository
    ) is None or repository.endswith(".git"):
        raise ValueError("invalid repository")
    _validate_oid(tree_oid, object_format)
    return RecursiveTreeSourceRequest(
        operation_key="git_tree_recursive.get",
        method="GET",
        target=f"/repos/{owner}/{repository}/git/trees/{tree_oid}?recursive=1",
    )


def project_recursive_tree_source(
    value: Any, *, root_tree_oid: str, object_format: GitObjectFormat
) -> tuple[RecursiveTreeEntry, ...]:
    """Strictly project the only response fields admitted by the erratum."""

    if not isinstance(value, dict) or type(value.get("truncated")) is not bool:
        raise ValueError("recursive tree response is invalid")
    if value["truncated"] is not False or value.get("sha") != root_tree_oid:
        raise ValueError("recursive tree response is incomplete or mismatched")
    raw_entries = value.get("tree")
    if not isinstance(raw_entries, list) or len(raw_entries) > MAX_TREE_ENTRIES:
        raise ValueError("recursive tree response exceeds entry boundary")
    rows: list[RecursiveTreeEntry] = []
    for raw in raw_entries:
        if not isinstance(raw, dict):
            raise ValueError("recursive tree entry is invalid")
        rows.append(
            RecursiveTreeEntry(
                path=raw.get("path"),
                mode=raw.get("mode"),
                type=raw.get("type"),
                oid=raw.get("sha"),
            )
        )
    rows.sort(key=lambda row: row.path)
    result = tuple(rows)
    _validate_entry_set(result, object_format)
    if reconstruct_tree_oid(result, object_format) != root_tree_oid:
        raise ValueError("recursive tree response does not close the base tree")
    return result


def _validate_canonical_json_value(
    value: object, *, _seen: set[int] | None = None
) -> None:
    """Reject values outside the strict, float-free JSON data model."""

    if value is None or type(value) in {str, bool, int}:
        return
    if type(value) not in {list, dict}:
        raise ValueError("canonical JSON contains a non-JSON value")

    seen = set() if _seen is None else _seen
    identity = id(value)
    if identity in seen:
        raise ValueError("canonical JSON contains a circular value")
    seen.add(identity)
    try:
        if type(value) is list:
            for item in value:  # type: ignore[union-attr]
                _validate_canonical_json_value(item, _seen=seen)
            return
        for key, item in value.items():  # type: ignore[union-attr]
            if type(key) is not str:
                raise ValueError("canonical JSON object keys must be strings")
            _validate_canonical_json_value(item, _seen=seen)
    finally:
        seen.remove(identity)


def _canonical_json_bytes(value: object) -> bytes:
    _validate_canonical_json_value(value)
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ValueError("canonical JSON encoding failed") from exc


def canonical_closure_entries_bytes(entries: Sequence["RecursiveTreeEntry"]) -> bytes:
    """Return the bounded canonical projection measured by a closure."""

    return _canonical_json_bytes([entry.model_dump(mode="json") for entry in entries])


def canonical_repository_path(value: str) -> str:
    """Validate one canonical repository path without repairing it."""

    if not value or unicodedata.normalize("NFC", value) != value:
        raise ValueError("path must be non-empty NFC text")
    if len(value.encode("utf-8")) > MAX_PATH_BYTES:
        raise ValueError("path exceeds byte limit")
    if value.startswith("/") or "\\" in value or "%" in value:
        raise ValueError("path has a prohibited representation")
    parts = value.split("/")
    if len(parts) > MAX_PATH_DEPTH or any(part in {"", ".", ".."} for part in parts):
        raise ValueError("path has invalid segments")
    for part in parts:
        if len(part.encode("utf-8")) > MAX_SEGMENT_BYTES:
            raise ValueError("path segment exceeds byte limit")
        if part.endswith((".", " ")) or any(
            ord(ch) < 32 or ord(ch) == 127 for ch in part
        ):
            raise ValueError("path segment is ambiguous")
        stem = part.split(".", 1)[0].casefold()
        if stem in _WINDOWS_DEVICES:
            raise ValueError("path uses a reserved device name")
    return value


def proposal_repository_path(value: str) -> str:
    """Validate the non-overridable Stage 21B proposal-path policy."""

    value = canonical_repository_path(value)
    parts = value.split("/")
    folded = [part.casefold() for part in parts]
    lower = value.casefold()
    if ".git" in folded or folded[0] == ".github":
        raise ValueError("proposal path is prohibited")
    if lower in {"codeowners", ".gitmodules", ".gitattributes", ".gitignore", ".env"}:
        raise ValueError("proposal path is prohibited")
    if parts[-1].casefold() == "codeowners" or lower.startswith(".env."):
        raise ValueError("proposal path is prohibited")
    if lower.endswith(_PROHIBITED_SUFFIXES):
        raise ValueError("proposal path is prohibited")
    if lower.startswith(("docs/governance/", "architecture/decisions/", "adr/")):
        raise ValueError("proposal path is prohibited")
    tokens = {token for part in folded for token in re.split(r"[^a-z0-9]+", part)}
    if (
        tokens & _CONTROL_TERMS
        or "trust-domain" in lower
        or "branch-protection" in lower
    ):
        raise ValueError("proposal path is a classified control record")
    return value


def validate_head_ref(value: str) -> str:
    if len(value.encode("ascii", errors="ignore")) != len(value) or len(value) > 160:
        raise ValueError("head ref must be bounded ASCII")
    if _HEAD_REF.fullmatch(value) is None or "--" in value or value.endswith(".lock"):
        raise ValueError("head ref does not match the closed convention")
    return value


def canonical_github_ref_target(value: str) -> tuple[str, str]:
    """Validate one full heads ref and encode its REST path/query forms."""

    if type(value) is not str or not value.startswith("refs/heads/"):
        raise ValueError("ref must be a full refs/heads reference")
    if unicodedata.normalize("NFC", value) != value:
        raise ValueError("ref must be NFC text")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("ref must be valid UTF-8 text") from exc
    if len(encoded) > 255:
        raise ValueError("ref exceeds the Git byte limit")
    branch = value.removeprefix("refs/heads/")
    if (
        not branch
        or branch == "@"
        or branch.startswith("/")
        or branch.endswith(("/", "."))
        or "//" in branch
        or ".." in branch
        or "@{" in branch
        or any(ord(char) <= 32 or ord(char) == 127 for char in branch)
        or any(char in "~^:?*[\\" for char in branch)
    ):
        raise ValueError("ref violates Git reference grammar")
    parts = branch.split("/")
    if any(part.startswith(".") or part.casefold().endswith(".lock") for part in parts):
        raise ValueError("ref violates Git component grammar")
    path_form = quote("heads/" + branch, safe="/")
    query_form = quote(branch, safe="")
    return path_form, query_form


def git_object_oid(
    kind: Literal["blob", "tree", "commit"],
    payload: bytes,
    object_format: GitObjectFormat,
) -> str:
    header = kind.encode("ascii") + b" " + str(len(payload)).encode("ascii") + b"\0"
    digest = hashlib.sha1 if object_format == "sha1" else hashlib.sha256
    return digest(header + payload).hexdigest()


def git_blob_oid(content: bytes, object_format: GitObjectFormat) -> str:
    return git_object_oid("blob", content, object_format)


class RecursiveTreeEntry(ClosedModel):
    path: str
    mode: Literal["040000", "100644", "100755", "120000", "160000"]
    type: GitEntryType
    oid: str

    @field_validator("path")
    @classmethod
    def valid_path(cls, value: str) -> str:
        return canonical_repository_path(value)

    @model_validator(mode="after")
    def valid_form(self) -> "RecursiveTreeEntry":
        if (self.mode, self.type) not in ALLOWED_BASE_FORMS:
            raise ValueError("unsupported Git mode/type pair")
        return self


class RecursiveTreeObservation(GitHubRecord):
    profile: Literal["github-recursive-tree-observation"] = (
        "github-recursive-tree-observation"
    )
    schema_version: Literal[TREE_SOURCE_SCHEMA] = TREE_SOURCE_SCHEMA
    observation_id: str = Field(min_length=1, max_length=128)
    repository_profile: RecordReference
    api_profile: RecordReference
    base_observation: RecordReference
    authorization: RecordReference
    intent: RecordReference
    attempt_claim: RecordReference
    lease_evidence: RecordReference
    repository_id: int = Field(gt=0)
    account_id: int = Field(gt=0)
    base_ref: str = Field(min_length=12, max_length=255)
    base_commit_oid: str
    root_tree_oid: str
    object_format: GitObjectFormat
    truncated: Literal[False] = False
    response_bytes: int = Field(ge=2, le=7 * 1024 * 1024)
    entries: tuple[RecursiveTreeEntry, ...] = Field(max_length=MAX_TREE_ENTRIES)
    complete: Literal[True] = True

    @model_validator(mode="after")
    def canonical_entries(self) -> "RecursiveTreeObservation":
        _validate_oid(self.base_commit_oid, self.object_format)
        _validate_oid(self.root_tree_oid, self.object_format)
        _validate_entry_set(self.entries, self.object_format)
        if reconstruct_tree_oid(self.entries, self.object_format) != self.root_tree_oid:
            raise ValueError("source observation entries do not reproduce root OID")
        return self


class BaseTreeIdentityObservation(GitHubRecord):
    profile: Literal["github-base-tree-identity-observation"] = (
        "github-base-tree-identity-observation"
    )
    schema_version: Literal[BASE_IDENTITY_OBSERVATION_SCHEMA] = (
        BASE_IDENTITY_OBSERVATION_SCHEMA
    )
    observation_id: str = Field(min_length=1, max_length=128)
    repository_profile: RecordReference
    api_profile: RecordReference
    repository_id: int = Field(gt=0)
    account_id: int = Field(gt=0)
    base_ref: str = Field(min_length=12, max_length=255)
    base_commit_oid: str
    base_root_tree_oid: str
    object_format: GitObjectFormat
    observed_at: str
    complete: Literal[True] = True

    @model_validator(mode="after")
    def exact_identity(self) -> "BaseTreeIdentityObservation":
        _validate_oid(self.base_commit_oid, self.object_format)
        _validate_oid(self.base_root_tree_oid, self.object_format)
        datetime.strptime(self.observed_at, "%Y-%m-%dT%H:%M:%SZ")
        return self


class PublicationRepositoryExtension(GitHubRecord):
    """21B-only profile extension; the frozen 21A profile remains unchanged."""

    profile: Literal["github-publication-repository-extension"] = (
        "github-publication-repository-extension"
    )
    schema_version: Literal[PUBLICATION_REPOSITORY_EXTENSION_SCHEMA] = (
        PUBLICATION_REPOSITORY_EXTENSION_SCHEMA
    )
    repository_profile: RecordReference
    source_operation: Literal["git_tree_recursive.get"] = "git_tree_recursive.get"
    endpoint_version: Literal[RECURSIVE_TREE_ENDPOINT_VERSION] = (
        RECURSIVE_TREE_ENDPOINT_VERSION
    )
    allowed_head_prefix: Literal["refs/heads/conclave/"] = "refs/heads/conclave/"
    prohibited_path_policy: Literal["stage-21b-initial-closed-set"] = (
        "stage-21b-initial-closed-set"
    )
    fixture_and_loopback_only: Literal[True] = True
    live_use_allowed: Literal[False] = False


class BaseTreeClosure(GitHubRecord):
    profile: Literal["github-base-tree-closure"] = "github-base-tree-closure"
    schema_version: Literal[BASE_TREE_CLOSURE_SCHEMA] = BASE_TREE_CLOSURE_SCHEMA
    closure_id: str = Field(min_length=1, max_length=128)
    increment_21_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    stage_21a_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    stage_21b_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    erratum_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    repository_profile: RecordReference
    api_profile: RecordReference
    base_observation: RecordReference
    source_observation: RecordReference
    source_authorization: RecordReference
    source_intent: RecordReference
    source_attempt_claim: RecordReference
    source_lease_evidence: RecordReference
    repository_extension: RecordReference
    repository_id: int = Field(gt=0)
    account_id: int = Field(gt=0)
    base_ref: str = Field(min_length=12, max_length=255)
    base_commit_oid: str
    base_root_tree_oid: str
    object_format: GitObjectFormat
    source_complete: Literal[True] = True
    source_truncated: Literal[False] = False
    entries: tuple[RecursiveTreeEntry, ...] = Field(max_length=MAX_TREE_ENTRIES)
    entry_count: int = Field(ge=0, le=MAX_TREE_ENTRIES)
    canonical_byte_count: int = Field(ge=2, le=MAX_CLOSURE_BYTES)
    recomputed_base_root_tree_oid: str
    approval_effect: Literal["none"] = "none"
    merge_authorized: Literal[False] = False
    action_execution_allowed: Literal[False] = False
    deployment_allowed: Literal[False] = False
    base_observed_at: str
    source_observed_at: str

    @model_validator(mode="after")
    def closure_is_exact(self) -> "BaseTreeClosure":
        if (
            self.increment_21_hash,
            self.stage_21a_hash,
            self.stage_21b_hash,
            self.erratum_hash,
        ) != (
            INCREMENT_21_PROTOCOL_HASH,
            STAGE_21A_PROTOCOL_HASH,
            STAGE_21B_PROTOCOL_HASH,
            STAGE_21B_ERRATUM_HASH,
        ):
            raise ValueError("base tree closure protocol identity mismatch")
        base_time = datetime.strptime(self.base_observed_at, "%Y-%m-%dT%H:%M:%SZ")
        source_time = datetime.strptime(self.source_observed_at, "%Y-%m-%dT%H:%M:%SZ")
        if abs((source_time - base_time).total_seconds()) > 900:
            raise ValueError("base-tree preparation window exceeds 15 minutes")
        if self.entry_count != len(self.entries):
            raise ValueError("entry_count mismatch")
        for oid in (
            self.base_commit_oid,
            self.base_root_tree_oid,
            self.recomputed_base_root_tree_oid,
        ):
            _validate_oid(oid, self.object_format)
        _validate_entry_set(self.entries, self.object_format)
        if self.canonical_byte_count != len(
            canonical_closure_entries_bytes(self.entries)
        ):
            raise ValueError("canonical_byte_count mismatch")
        computed = reconstruct_tree_oid(self.entries, self.object_format)
        if (
            computed != self.base_root_tree_oid
            or computed != self.recomputed_base_root_tree_oid
        ):
            raise ValueError("base tree closure does not reproduce root OID")
        return self


class ProposalBlob(ClosedModel):
    path: str
    byte_count: int = Field(ge=0, le=2 * 1024 * 1024)
    content_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    blob_oid: str

    @field_validator("path")
    @classmethod
    def valid_path(cls, value: str) -> str:
        return proposal_repository_path(value)


def _validate_oid(oid: str, object_format: GitObjectFormat) -> None:
    if re.fullmatch(f"[0-9a-f]{{{_OID_LENGTH[object_format]}}}", oid) is None:
        raise ValueError("object ID does not match pinned format")


def _validate_entry_set(
    entries: Sequence[RecursiveTreeEntry], object_format: GitObjectFormat
) -> None:
    paths = [entry.path for entry in entries]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ValueError("tree entries must be unique and path-sorted")
    folded = [unicodedata.normalize("NFC", path).casefold() for path in paths]
    if len(folded) != len(set(folded)):
        raise ValueError("tree entries collide under canonical case folding")
    by_path = {entry.path: entry for entry in entries}
    for entry in entries:
        _validate_oid(entry.oid, object_format)
        parts = entry.path.split("/")
        for index in range(1, len(parts)):
            parent = "/".join(parts[:index])
            parent_entry = by_path.get(parent)
            if parent_entry is None or parent_entry.type != "tree":
                raise ValueError("tree entry has a missing or non-tree parent")


def _tree_sort_key(entry: RecursiveTreeEntry) -> bytes:
    basename = entry.path.rsplit("/", 1)[-1].encode("utf-8")
    return basename + (b"/" if entry.type == "tree" else b"\0")


def _tree_payload(entries: Sequence[RecursiveTreeEntry]) -> bytes:
    payload = bytearray()
    for entry in sorted(entries, key=_tree_sort_key):
        # GitHub represents tree mode as ``040000``; canonical Git tree
        # objects serialize it as ``40000``.
        mode = "40000" if entry.mode == "040000" else entry.mode
        payload.extend(mode.encode("ascii"))
        payload.extend(b" ")
        payload.extend(entry.path.rsplit("/", 1)[-1].encode("utf-8"))
        payload.extend(b"\0")
        payload.extend(bytes.fromhex(entry.oid))
    return bytes(payload)


def reconstruct_tree_oid(
    entries: Sequence[RecursiveTreeEntry], object_format: GitObjectFormat
) -> str:
    """Verify every subtree and return the reconstructed root tree OID."""

    _validate_entry_set(entries, object_format)
    by_parent: dict[str, list[RecursiveTreeEntry]] = defaultdict(list)
    tree_entries: dict[str, RecursiveTreeEntry] = {}
    for entry in entries:
        parent = entry.path.rsplit("/", 1)[0] if "/" in entry.path else ""
        by_parent[parent].append(entry)
        if entry.type == "tree":
            tree_entries[entry.path] = entry
    directories = sorted(tree_entries, key=lambda value: value.count("/"), reverse=True)
    for directory in directories:
        actual = git_object_oid(
            "tree", _tree_payload(by_parent[directory]), object_format
        )
        if actual != tree_entries[directory].oid:
            raise ValueError("subtree OID mismatch")
    return git_object_oid("tree", _tree_payload(by_parent[""]), object_format)


def proposal_blobs(
    files: Mapping[str, bytes], object_format: GitObjectFormat
) -> tuple[ProposalBlob, ...]:
    if not 1 <= len(files) <= 64:
        raise ValueError("proposal file count outside boundary")
    total = sum(len(content) for content in files.values())
    if total > 8 * 1024 * 1024:
        raise ValueError("proposal aggregate bytes exceed boundary")
    rows: list[ProposalBlob] = []
    for path in sorted(files):
        proposal_repository_path(path)
        content = files[path]
        if len(content) > 2 * 1024 * 1024:
            raise ValueError("proposal file exceeds boundary")
        rows.append(
            ProposalBlob(
                path=path,
                byte_count=len(content),
                content_sha256="sha256:" + hashlib.sha256(content).hexdigest(),
                blob_oid=git_blob_oid(content, object_format),
            )
        )
    folded = [row.path.casefold() for row in rows]
    if len(folded) != len(set(folded)):
        raise ValueError("proposal paths collide under case folding")
    return tuple(rows)


def verify_proposal_blobs(
    files: Mapping[str, bytes],
    proposal: Sequence[ProposalBlob],
    object_format: GitObjectFormat,
) -> None:
    """Bind each retained proposal row to the exact bytes read once."""

    expected = proposal_blobs(files, object_format)
    if tuple(proposal) != expected:
        raise ValueError("proposal metadata does not match artifact bytes")


def read_artifacts_once(
    root: "os.PathLike[str]",
    references: Sequence[RecordReference],
    *,
    maximum_total_bytes: int = 8 * 1024 * 1024,
) -> dict[str, bytes]:
    """Read bounded workspace artifacts with containment and link refusal."""

    from pathlib import Path, PurePosixPath

    supplied_root = Path(root)
    root_info = supplied_root.lstat()
    root_reparse = getattr(root_info, "st_file_attributes", 0) & getattr(
        stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
    )
    if supplied_root.is_symlink() or root_reparse or not supplied_root.is_dir():
        raise ValueError("PROPOSAL_CONTENT_CHANGED")
    base = supplied_root.resolve(strict=True)
    unique: dict[str, RecordReference] = {}
    for reference in references:
        raw_reference = reference.reference
        relative = PurePosixPath(raw_reference)
        canonical_reference = relative.as_posix()
        if (
            raw_reference != canonical_reference
            or unicodedata.normalize("NFC", raw_reference) != raw_reference
            or relative.is_absolute()
            or not relative.parts
            or any(part in {"", ".", ".."} for part in relative.parts)
        ):
            raise ValueError("PROPOSAL_CONTENT_CHANGED")
        prior = unique.get(canonical_reference)
        if prior is not None and prior.content_hash != reference.content_hash:
            raise ValueError("PROPOSAL_CONTENT_CHANGED")
        unique.setdefault(canonical_reference, reference)
    result: dict[str, bytes] = {}
    total = 0
    for reference in unique.values():
        relative = PurePosixPath(reference.reference)
        candidate = base.joinpath(*relative.parts)
        reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        descriptor: int
        if os.name != "nt" and os.open in getattr(os, "supports_dir_fd", set()):
            directory_flags = (
                os.O_RDONLY
                | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_NOFOLLOW", 0)
            )
            try:
                directory_fd = os.open(base, directory_flags)
            except OSError as exc:
                raise ValueError("PROPOSAL_CONTENT_CHANGED") from exc
            try:
                for part in relative.parts[:-1]:
                    try:
                        next_fd = os.open(part, directory_flags, dir_fd=directory_fd)
                    except OSError as exc:
                        raise ValueError("PROPOSAL_CONTENT_CHANGED") from exc
                    os.close(directory_fd)
                    directory_fd = next_fd
                try:
                    descriptor = os.open(
                        relative.parts[-1],
                        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
                        dir_fd=directory_fd,
                    )
                except OSError as exc:
                    raise ValueError("PROPOSAL_CONTENT_CHANGED") from exc
            finally:
                os.close(directory_fd)
            info = os.fstat(descriptor)
        else:
            cursor = base
            for part in relative.parts:
                cursor = cursor / part
                info = cursor.lstat()
                attrs = getattr(info, "st_file_attributes", 0)
                if stat.S_ISLNK(info.st_mode) or attrs & reparse:
                    raise ValueError("PROPOSAL_CONTENT_CHANGED")
            resolved = candidate.resolve(strict=True)
            if base not in resolved.parents or not resolved.is_file():
                raise ValueError("PROPOSAL_CONTENT_CHANGED")
            flags = (
                os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            )
            descriptor = os.open(candidate, flags)
            opened = os.fstat(descriptor)
            if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                os.close(descriptor)
                raise ValueError("PROPOSAL_CONTENT_CHANGED")
        try:
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or getattr(opened, "st_file_attributes", 0) & reparse
            ):
                raise ValueError("PROPOSAL_CONTENT_CHANGED")
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                data = handle.read(maximum_total_bytes - total + 1)
        finally:
            os.close(descriptor)
        total += len(data)
        if total > maximum_total_bytes:
            raise ValueError("PROPOSAL_LIMIT_EXCEEDED")
        result[reference.reference] = data
    return result


def apply_proposal(
    entries: Sequence[RecursiveTreeEntry],
    proposal: Sequence[ProposalBlob],
    object_format: GitObjectFormat,
) -> str:
    """Apply regular-file overlays in memory and return the final root OID."""

    _validate_entry_set(entries, object_format)
    state = {entry.path: entry for entry in entries}
    for blob in proposal:
        _validate_oid(blob.blob_oid, object_format)
        parts = blob.path.split("/")
        folded_path = blob.path.casefold()
        if any(path != blob.path and path.casefold() == folded_path for path in state):
            raise ValueError("proposal path collides with base under case folding")
        for index in range(1, len(parts)):
            directory = "/".join(parts[:index])
            if any(
                path != directory and path.casefold() == directory.casefold()
                for path in state
            ):
                raise ValueError("proposal directory collides under case folding")
            existing = state.get(directory)
            if existing is not None and existing.type != "tree":
                raise ValueError("proposal directory collides with non-tree entry")
            if existing is None:
                state[directory] = RecursiveTreeEntry(
                    path=directory,
                    mode="040000",
                    type="tree",
                    oid="0" * _OID_LENGTH[object_format],
                )
        existing = state.get(blob.path)
        if existing is not None and existing.type == "tree":
            raise ValueError("proposal file collides with existing tree")
        if existing is not None and (
            existing.type != "blob" or existing.mode != "100644"
        ):
            raise ValueError("proposal may replace only an existing regular file")
        state[blob.path] = RecursiveTreeEntry(
            path=blob.path, mode="100644", type="blob", oid=blob.blob_oid
        )
    tree_paths = sorted(
        (path for path, entry in state.items() if entry.type == "tree"),
        key=lambda value: value.count("/"),
        reverse=True,
    )
    for tree_path in tree_paths:
        children = [
            entry
            for path, entry in state.items()
            if (path.rsplit("/", 1)[0] if "/" in path else "") == tree_path
        ]
        oid = git_object_oid("tree", _tree_payload(children), object_format)
        current = state[tree_path]
        state[tree_path] = current.model_copy(update={"oid": oid})
    roots = [entry for path, entry in state.items() if "/" not in path]
    return git_object_oid("tree", _tree_payload(roots), object_format)


def git_commit_oid(
    *,
    tree_oid: str,
    parent_oid: str,
    name: str,
    email: str,
    timestamp: str,
    message: str,
    object_format: GitObjectFormat,
) -> str:
    for oid in (tree_oid, parent_oid):
        _validate_oid(oid, object_format)
    if (
        "\n" in name
        or "<" in name
        or ">" in name
        or "\n" in email
        or "<" in email
        or ">" in email
    ):
        raise ValueError("author identity contains prohibited characters")
    instant = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    ident = f"{name} <{email}> {int(instant.timestamp())} +0000"
    payload = (
        f"tree {tree_oid}\nparent {parent_oid}\nauthor {ident}\n"
        f"committer {ident}\n\n{message}"
    ).encode("utf-8")
    return git_object_oid("commit", payload, object_format)


class RequestBudget:
    """Monotonic deterministic Stage 21B publication budget."""

    __slots__ = ("_remaining", "_server_remaining", "_reserve")

    def __init__(self, file_count: int, observed_remaining: int, reserve: int = 10):
        if not 1 <= file_count <= 64 or reserve != 10:
            raise ValueError("invalid publication budget boundary")
        ceiling = 2 * file_count + 14
        if observed_remaining < ceiling + reserve:
            raise ValueError("INSUFFICIENT_RATE_BUDGET")
        self._remaining = ceiling
        self._server_remaining = observed_remaining
        self._reserve = reserve

    @property
    def remaining(self) -> int:
        return self._remaining

    def admit_dispatch(self, still_possible_after: int) -> None:
        if (
            self._remaining <= 0
            or self._server_remaining < still_possible_after + 1 + self._reserve
        ):
            raise ValueError("INSUFFICIENT_RATE_BUDGET")
        self._remaining -= 1

    def observe(
        self,
        server_remaining: int,
        *,
        retry_after: bool = False,
        rate_limited: bool = False,
    ) -> None:
        if server_remaining < 0:
            raise ValueError("RATE_LIMIT_EVIDENCE_INVALID")
        if retry_after or rate_limited:
            raise ValueError("RATE_LIMITED")
        self._server_remaining = min(self._server_remaining, server_remaining)
