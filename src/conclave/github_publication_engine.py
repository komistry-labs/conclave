"""Stage 21B coordinator and immutable offline-fixture evidence.

The coordinator owns fixture admission, bounded raw-response parsing and
terminalization. Its only response source is concrete immutable in-memory
transcript data; it has no callback, credential, socket, HTTP or live dispatch
surface.
"""

from __future__ import annotations

import hashlib
import json
import base64
import re
import stat
from datetime import datetime
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal, Sequence, Mapping, Annotated, Union

from pydantic import Field, field_validator, model_validator

from .github_foundation import (
    GitHubRecord,
    GitHubRepositoryProfile,
    RecordReference,
    write_durable_record,
    GitHubTransportResponse,
)
from .github_publication import (
    RequestBudget,
    canonical_github_ref_target,
    read_artifacts_once,
)
from .identity import ClosedModel, seal_record
from .errors import IntegrityError
from .ledger import exists as ledger_exists, record_event
from .workspace import Workspace
from .github_publication import apply_proposal, git_blob_oid, git_commit_oid
from .github_publication_records import (
    PublicationGovernanceChain,
    ProposalManifest,
)

STEP_ADMISSION_SCHEMA = "github-publication-fixture-step-admission/0.1.0"
STEP_RESULT_SCHEMA = "github-publication-fixture-step-result/0.1.0"
RECEIPT_SCHEMA = "github-publication-fixture-receipt/0.1.0"
RATE_OBSERVATION_SCHEMA = "github-rate-budget-observation/0.1.0"

READ_KEYS = frozenset(
    {
        "repository.get",
        "ref.get",
        "matching_refs.list",
        "pull_requests.matching.list",
        "pull_request.get",
        "git_blob.get",
        "git_tree.get",
        "commit.get",
    }
)
MUTATION_KEYS = frozenset(
    {
        "git_blob.create",
        "git_tree.create",
        "git_commit.create",
        "git_ref.create",
        "pull_request.create",
    }
)
ALL_KEYS = READ_KEYS | MUTATION_KEYS
PUBLICATION_CLOSED_REASONS = frozenset(
    {
        "PUBLICATION_AUTH_INVALID",
        "PUBLICATION_AUTH_EXPIRED",
        "PUBLICATION_INPUT_MISMATCH",
        "PROPOSAL_MANIFEST_INVALID",
        "PROPOSAL_PATH_PROHIBITED",
        "PROPOSAL_PATH_COLLISION",
        "PROPOSAL_CONTENT_CHANGED",
        "PROPOSAL_LIMIT_EXCEEDED",
        "BASE_OBSERVATION_STALE",
        "BASE_REF_CHANGED",
        "HEAD_REF_EXISTS",
        "HEAD_REF_PROTECTED",
        "HEAD_REF_RULESET_TARGETED",
        "PUBLICATION_ALREADY_CLAIMED",
        "PUBLICATION_CLAIM_CONFLICT",
        "PUBLICATION_CLAIM_STORE_FAILED",
        "PUBLICATION_INTENT_STORE_FAILED",
        "PUBLICATION_LEASE_INVALID",
        "PUBLICATION_PERMISSION_MISMATCH",
        "PUBLICATION_LEASE_EVIDENCE_STORE_FAILED",
        "PUBLICATION_LEASE_STALE",
        "PUBLICATION_CLEANUP_FAILED",
        "MUTATION_NOT_ALLOWED",
        "MUTATION_LIMIT_REACHED",
        "MUTATION_DISPATCH_FAILED",
        "MUTATION_OUTCOME_AMBIGUOUS",
        "GIT_OBJECT_ID_MISMATCH",
        "GIT_OBJECT_RESPONSE_INVALID",
        "REF_RESPONSE_INVALID",
        "PR_RESPONSE_INVALID",
        "PR_ALREADY_EXISTS",
        "PR_CREATION_REFUSED",
        "RATE_LIMITED",
        "INSUFFICIENT_RATE_BUDGET",
        "RATE_LIMIT_EVIDENCE_INVALID",
        "STEP_ADMISSION_STORE_FAILED",
        "STEP_RESULT_STORE_FAILED",
        "PUBLICATION_RECEIPT_STORE_FAILED",
        "TERMINAL_FAILURE_STORE_FAILED",
        "RECONCILIATION_AUTH_INVALID",
        "RECONCILIATION_ALREADY_CLAIMED",
        "PUBLICATION_RECONCILIATION_REQUIRED",
    }
)


def _validate_json_value(value: object, *, depth: int = 0) -> None:
    if depth > 32:
        raise ValueError("GIT_OBJECT_RESPONSE_INVALID")
    if value is None or type(value) in {bool, int, str}:
        return
    if isinstance(value, float):
        raise ValueError("GIT_OBJECT_RESPONSE_INVALID")
    if isinstance(value, list):
        for item in value:
            _validate_json_value(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        if any(type(key) is not str for key in value):
            raise ValueError("GIT_OBJECT_RESPONSE_INVALID")
        for item in value.values():
            _validate_json_value(item, depth=depth + 1)
        return
    raise ValueError("GIT_OBJECT_RESPONSE_INVALID")


def _canonical_json(value: object) -> bytes:
    _validate_json_value(value)
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise ValueError("GIT_OBJECT_RESPONSE_INVALID") from None


def _hash_json(value: object) -> str:
    data = _canonical_json(value)
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _record_bytes(record: ClosedModel) -> bytes:
    return (
        json.dumps(record.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _verify_reopened_records(
    root: Path, records: Sequence[tuple[RecordReference, ClosedModel]]
) -> None:
    references = tuple(reference for reference, _ in records)
    reopened = read_artifacts_once(
        root, references, maximum_total_bytes=8 * 1024 * 1024
    )
    for reference, record in records:
        content = reopened[reference.reference]
        if (
            content != _record_bytes(record)
            or getattr(record, "content_hash", None) != reference.content_hash
        ):
            raise ValueError("PUBLICATION_INPUT_MISMATCH")


def _verify_complete_upstream_inventory(
    root: Path, references: Sequence[RecordReference]
) -> None:
    if len(references) != 17 or len({item.reference for item in references}) != 17:
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    try:
        reopened = read_artifacts_once(
            root, tuple(references), maximum_total_bytes=16 * 1024 * 1024
        )
    except Exception:
        raise ValueError("PUBLICATION_INPUT_MISMATCH") from None
    if set(reopened) != {item.reference for item in references}:
        raise ValueError("PUBLICATION_INPUT_MISMATCH")


@dataclass(frozen=True)
class PublicationDispatch:
    ordinal: int
    operation_key: str
    request_hash: str
    expected_identity: str


@dataclass(frozen=True)
class ExactPublicationDispatch:
    ordinal: int
    operation_key: str
    method: Literal["GET", "POST"]
    target: str
    body: bytes
    request_hash: str
    expected_projection: dict[str, Any]


def _request_hash(method: str, target: str, body: bytes) -> str:
    return (
        "sha256:"
        + hashlib.sha256(
            b"CONCLAVE-GITHUB-21B-REQUEST-V1\0"
            + method.encode("ascii")
            + b"\0"
            + target.encode("ascii")
            + b"\0"
            + body
        ).hexdigest()
    )


def _request(
    ordinal: int,
    key: str,
    method: Literal["GET", "POST"],
    target: str,
    body_value: object | None,
    expected: dict[str, Any],
) -> ExactPublicationDispatch:
    body = b"" if body_value is None else _canonical_json(body_value)
    return ExactPublicationDispatch(
        ordinal,
        key,
        method,
        target,
        body,
        _request_hash(method, target, body),
        expected,
    )


def build_exact_publication_dispatches(
    manifest: ProposalManifest,
    repository_profile: GitHubRepositoryProfile,
    artifacts: Mapping[str, bytes],
) -> tuple[ExactPublicationDispatch, ...]:
    """Build every frozen request from hash-verified artifacts and no free routes."""

    file_bytes: dict[str, bytes] = {}
    for item in manifest.files:
        content = artifacts.get(item.artifact.reference)
        if content is None or len(content) != item.byte_count:
            raise ValueError("PROPOSAL_CONTENT_CHANGED")
        if "sha256:" + hashlib.sha256(content).hexdigest() != item.content_sha256:
            raise ValueError("PROPOSAL_CONTENT_CHANGED")
        if git_blob_oid(content, manifest.object_format) != item.blob_oid:
            raise ValueError("GIT_OBJECT_ID_MISMATCH")
        file_bytes[item.path] = content
    message = artifacts.get(manifest.commit_message.reference)
    title = artifacts.get(manifest.pull_request_title.reference)
    body = artifacts.get(manifest.pull_request_body.reference)
    identity_bytes = artifacts.get(manifest.commit_identity_artifact.reference)
    for content, reference, count in (
        (message, manifest.commit_message, manifest.commit_message_byte_count),
        (title, manifest.pull_request_title, manifest.pull_request_title_byte_count),
        (body, manifest.pull_request_body, manifest.pull_request_body_byte_count),
    ):
        if (
            content is None
            or len(content) != count
            or (
                "sha256:" + hashlib.sha256(content).hexdigest()
                != reference.content_hash
            )
        ):
            raise ValueError("PROPOSAL_CONTENT_CHANGED")
    assert message is not None and title is not None and body is not None
    expected_identity_bytes = json.dumps(
        manifest.commit_identity.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    if (
        identity_bytes != expected_identity_bytes
        or "sha256:" + hashlib.sha256(expected_identity_bytes).hexdigest()
        != manifest.commit_identity_artifact.content_hash
    ):
        raise ValueError("PROPOSAL_CONTENT_CHANGED")
    try:
        message_text, title_text, body_text = (
            message.decode("utf-8"),
            title.decode("utf-8"),
            body.decode("utf-8"),
        )
    except UnicodeDecodeError as exc:
        raise ValueError("PROPOSAL_CONTENT_CHANGED") from exc
    identity = manifest.commit_identity
    if (
        git_commit_oid(
            tree_oid=manifest.proposal_tree_oid,
            parent_oid=manifest.base_commit_oid,
            name=identity.name,
            email=identity.email,
            timestamp=identity.timestamp,
            message=message_text,
            object_format=manifest.object_format,
        )
        != manifest.proposal_commit_oid
    ):
        raise ValueError("GIT_OBJECT_ID_MISMATCH")
    if not (
        manifest.repository_profile.content_hash == repository_profile.content_hash
        and manifest.owner == repository_profile.owner
        and manifest.repository == repository_profile.repository
        and manifest.repository_id == repository_profile.repository_id
        and manifest.account_id == repository_profile.account_id
        and manifest.object_format == repository_profile.git_object_format
    ):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    root = f"/repos/{repository_profile.owner}/{repository_profile.repository}"
    repository_identity = {
        "repository_id": manifest.repository_id,
        "account_id": manifest.account_id,
    }
    rows: list[ExactPublicationDispatch] = []

    def add(
        key: str,
        method: Literal["GET", "POST"],
        target: str,
        request_body: object | None,
        expected: dict[str, Any],
    ) -> None:
        rows.append(
            _request(len(rows) + 1, key, method, target, request_body, expected)
        )

    for item in manifest.files:
        add("repository.get", "GET", root, None, repository_identity)
        add(
            "git_blob.create",
            "POST",
            root + "/git/blobs",
            {
                "content": base64.b64encode(file_bytes[item.path]).decode("ascii"),
                "encoding": "base64",
            },
            {"oid": item.blob_oid},
        )
    add("repository.get", "GET", root, None, repository_identity)
    add(
        "git_tree.create",
        "POST",
        root + "/git/trees",
        {
            "base_tree": manifest.base_tree_oid,
            "tree": [
                {
                    "path": item.path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": item.blob_oid,
                }
                for item in manifest.files
            ],
        },
        {"oid": manifest.proposal_tree_oid},
    )
    add("repository.get", "GET", root, None, repository_identity)
    ident = {"name": identity.name, "email": identity.email, "date": identity.timestamp}
    add(
        "git_commit.create",
        "POST",
        root + "/git/commits",
        {
            "message": message_text,
            "tree": manifest.proposal_tree_oid,
            "parents": [manifest.base_commit_oid],
            "author": ident,
            "committer": ident,
        },
        {
            "oid": manifest.proposal_commit_oid,
            "tree_oid": manifest.proposal_tree_oid,
            "parents": [manifest.base_commit_oid],
        },
    )
    base_path, base_query = canonical_github_ref_target(manifest.base_ref)
    head_path, head_query = canonical_github_ref_target(manifest.head_ref)
    add(
        "ref.get",
        "GET",
        root + "/git/ref/" + base_path,
        None,
        {"ref": manifest.base_ref, "oid": manifest.base_commit_oid},
    )
    add(
        "matching_refs.list",
        "GET",
        root + "/git/matching-refs/" + head_path,
        None,
        {"matches": []},
    )
    add("repository.get", "GET", root, None, repository_identity)
    add(
        "git_ref.create",
        "POST",
        root + "/git/refs",
        {
            "ref": manifest.head_ref,
            "sha": manifest.proposal_commit_oid,
        },
        {"ref": manifest.head_ref, "oid": manifest.proposal_commit_oid},
    )
    add(
        "ref.get",
        "GET",
        root + "/git/ref/" + head_path,
        None,
        {"ref": manifest.head_ref, "oid": manifest.proposal_commit_oid},
    )
    add(
        "ref.get",
        "GET",
        root + "/git/ref/" + base_path,
        None,
        {"ref": manifest.base_ref, "oid": manifest.base_commit_oid},
    )
    add(
        "pull_requests.matching.list",
        "GET",
        root
        + "/pulls?state=all&head="
        + manifest.owner
        + ":"
        + head_query
        + "&base="
        + base_query
        + "&per_page=2&page=1",
        None,
        {"matches": []},
    )
    add("repository.get", "GET", root, None, repository_identity)
    pr_expected = {
        "repository_id": manifest.repository_id,
        "head_ref": manifest.head_ref,
        "head_oid": manifest.proposal_commit_oid,
        "base_ref": manifest.base_ref,
        "base_oid": manifest.base_commit_oid,
        "title_hash": manifest.pull_request_title.content_hash,
        "body_hash": manifest.pull_request_body.content_hash,
    }
    add(
        "pull_request.create",
        "POST",
        root + "/pulls",
        {
            "title": title_text,
            "head": manifest.head_ref.removeprefix("refs/heads/"),
            "base": manifest.base_ref.removeprefix("refs/heads/"),
            "body": body_text,
            "draft": False,
            "maintainer_can_modify": False,
        },
        pr_expected,
    )
    add(
        "pull_request.get",
        "GET",
        root + "/pulls/{created_pull_number}",
        None,
        pr_expected,
    )
    return tuple(rows)


@dataclass(frozen=True)
class ParsedPublicationResponse:
    status: int
    projection: dict[str, Any]
    server_remaining: int
    rate_limited: bool
    retry_after: bool
    rate_scope_hash: str
    rate_limit: int
    reset_at: str | None
    resource_bucket: str


@dataclass(frozen=True)
class FixtureTranscriptEntry:
    """One immutable raw fixture response bound to one planned request hash."""

    planned_request_hash: str
    response: GitHubTransportResponse

    def __post_init__(self) -> None:
        if (
            type(self.planned_request_hash) is not str
            or re.fullmatch(r"sha256:[0-9a-f]{64}", self.planned_request_hash) is None
        ):
            raise ValueError("PUBLICATION_INPUT_MISMATCH")
        if type(self.response) is not GitHubTransportResponse:
            raise ValueError("PUBLICATION_INPUT_MISMATCH")
        response = self.response
        if (
            type(response.status) is not int
            or not 100 <= response.status <= 599
            or type(response.headers) is not tuple
            or len(response.headers) > 64
            or type(response.body) is not bytes
            or len(response.body) > 2 * 1024 * 1024
        ):
            raise ValueError("PUBLICATION_INPUT_MISMATCH")
        canonical_headers: list[tuple[str, str]] = []
        aggregate_header_bytes = 0
        for header in response.headers:
            if type(header) is not tuple or len(header) != 2:
                raise ValueError("PUBLICATION_INPUT_MISMATCH")
            name, value = header
            if (
                type(name) is not str
                or type(value) is not str
                or re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]{1,128}", name) is None
                or len(value) > 8192
                or any(character in value for character in ("\r", "\n", "\x00"))
            ):
                raise ValueError("PUBLICATION_INPUT_MISMATCH")
            canonical = (name.lower(), value)
            aggregate_header_bytes += len(name.encode("ascii")) + len(
                value.encode("utf-8")
            )
            if aggregate_header_bytes > 64 * 1024:
                raise ValueError("PUBLICATION_INPUT_MISMATCH")
            canonical_headers.append(canonical)
        # Retain only a defensive copy of exact built-in immutable values. The
        # evaluator never invokes an object supplied by the transcript caller.
        object.__setattr__(
            self,
            "response",
            GitHubTransportResponse(
                status=response.status,
                headers=tuple(canonical_headers),
                body=bytes(response.body),
            ),
        )


@dataclass(frozen=True)
class OfflinePublicationTranscript:
    """Concrete in-memory fixture data; it owns no callback or execution seam."""

    entries: tuple[FixtureTranscriptEntry, ...]
    profile: Literal["github-publication-offline-transcript/0.1.0"] = field(
        default="github-publication-offline-transcript/0.1.0", init=False
    )

    def __post_init__(self) -> None:
        if type(self.entries) is not tuple or not self.entries:
            raise ValueError("PUBLICATION_INPUT_MISMATCH")
        if any(type(entry) is not FixtureTranscriptEntry for entry in self.entries):
            raise ValueError("PUBLICATION_INPUT_MISMATCH")
        object.__setattr__(
            self,
            "entries",
            tuple(
                FixtureTranscriptEntry(
                    planned_request_hash=entry.planned_request_hash,
                    response=entry.response,
                )
                for entry in self.entries
            ),
        )


def _is_link_or_reparse(path: Path) -> bool:
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return True
    return path.is_symlink() or bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _fixture_attempt_directory(workspace: Workspace, attempt_token: str) -> Path:
    """Return a no-link attempt directory contained by the CONCLAVE workspace."""

    if re.fullmatch(r"[0-9a-f]{64}", attempt_token) is None:
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
    # A CONCLAVE workspace is external operational state, never a directory
    # nested in a Git checkout (especially not KOS or IDM).
    if (root / ".git").exists() or any(
        (parent / ".git").exists() for parent in root.parents
    ):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")

    base = workspace.github_publication_fixture_evidence_dir.absolute()
    try:
        base.relative_to(root)
    except ValueError:
        raise ValueError("PUBLICATION_INPUT_MISMATCH") from None
    github_root = workspace.root / "github"
    if not github_root.is_dir() or _is_link_or_reparse(github_root):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    if base.exists() and (not base.is_dir() or _is_link_or_reparse(base)):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    base.mkdir(parents=False, exist_ok=True)
    if base.resolve(strict=True) != base or _is_link_or_reparse(base):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")

    attempt = base / attempt_token
    if attempt.exists() and (not attempt.is_dir() or _is_link_or_reparse(attempt)):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    attempt.mkdir(parents=False, exist_ok=True)
    if attempt.resolve(strict=True) != attempt or _is_link_or_reparse(attempt):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    return attempt


def _response_header(response: GitHubTransportResponse, name: str) -> str | None:
    try:
        return response.header(name)
    except Exception:
        raise ValueError("GIT_OBJECT_RESPONSE_INVALID") from None


def _strict_response_projection(
    dispatch: ExactPublicationDispatch,
    response: GitHubTransportResponse,
    *,
    manifest: ProposalManifest,
    rate_scope: str,
) -> ParsedPublicationResponse:
    if not 100 <= response.status <= 599 or len(response.body) > 2 * 1024 * 1024:
        raise ValueError("GIT_OBJECT_RESPONSE_INVALID")
    try:
        raw = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("GIT_OBJECT_RESPONSE_INVALID") from None
    _validate_json_value(raw)
    if not isinstance(raw, (dict, list)):
        raise ValueError("GIT_OBJECT_RESPONSE_INVALID")

    def obj(value: object) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("GIT_OBJECT_RESPONSE_INVALID")
        return value

    def text(value: object, maximum: int = 1024) -> str:
        if type(value) is not str or not value or len(value.encode("utf-8")) > maximum:
            raise ValueError("GIT_OBJECT_RESPONSE_INVALID")
        return value

    def positive(value: object) -> int:
        if type(value) is not int or value <= 0:
            raise ValueError("GIT_OBJECT_RESPONSE_INVALID")
        return value

    def oid(value: object) -> str:
        length = 40 if manifest.object_format == "sha1" else 64
        if (
            type(value) is not str
            or re.fullmatch(rf"[0-9a-f]{{{length}}}", value) is None
        ):
            raise ValueError("GIT_OBJECT_RESPONSE_INVALID")
        return value

    key = dispatch.operation_key
    if key == "repository.get":
        root = obj(raw)
        projection = {
            "repository_id": positive(root.get("id")),
            "account_id": positive(obj(root.get("owner")).get("id")),
        }
    elif key in {"git_blob.create", "git_blob.get", "git_tree.create", "git_tree.get"}:
        root = obj(raw)
        projection = {"oid": oid(root.get("sha"))}
    elif key in {"git_commit.create", "commit.get"}:
        root = obj(raw)
        tree = obj(root.get("tree"))
        parents = root.get("parents")
        if not isinstance(parents, list) or len(parents) != 1:
            raise ValueError("GIT_OBJECT_RESPONSE_INVALID")
        projection = {
            "oid": oid(root.get("sha")),
            "tree_oid": oid(tree.get("sha")),
            "parents": [oid(obj(parents[0]).get("sha"))],
        }
    elif key in {"ref.get", "git_ref.create"}:
        root = obj(raw)
        projection = {
            "ref": text(root.get("ref"), 255),
            "oid": oid(obj(root.get("object")).get("sha")),
        }
    elif key == "matching_refs.list":
        if not isinstance(raw, list):
            raise ValueError("GIT_OBJECT_RESPONSE_INVALID")
        projection = {
            "matches": sorted(
                (
                    {
                        "ref": text(obj(item).get("ref"), 255),
                        "oid": oid(obj(obj(item).get("object")).get("sha")),
                    }
                    for item in raw
                ),
                key=lambda item: (item["ref"], item["oid"]),
            )
        }
    elif key == "pull_requests.matching.list":
        if not isinstance(raw, list):
            raise ValueError("GIT_OBJECT_RESPONSE_INVALID")
        projection = {
            "matches": sorted((positive(obj(item).get("number")) for item in raw))
        }
    elif key in {"pull_request.create", "pull_request.get"}:
        root = obj(raw)
        head = obj(root.get("head"))
        base = obj(root.get("base"))
        head_repo = obj(head.get("repo"))
        base_repo = obj(base.get("repo"))
        if positive(head_repo.get("id")) != positive(base_repo.get("id")):
            raise ValueError("GIT_OBJECT_RESPONSE_INVALID")
        projection = {
            "repository_id": positive(base_repo.get("id")),
            "head_ref": "refs/heads/" + text(head.get("ref"), 255),
            "head_oid": oid(head.get("sha")),
            "base_ref": "refs/heads/" + text(base.get("ref"), 255),
            "base_oid": oid(base.get("sha")),
            "title_hash": "sha256:"
            + hashlib.sha256(text(root.get("title"), 256).encode()).hexdigest(),
            "body_hash": "sha256:"
            + hashlib.sha256(
                (root.get("body") if type(root.get("body")) is str else "").encode()
            ).hexdigest(),
            "pull_number": positive(root.get("number")),
        }
    else:
        raise ValueError("GIT_OBJECT_RESPONSE_INVALID")

    remaining_raw = _response_header(response, "X-RateLimit-Remaining")
    limit_raw = _response_header(response, "X-RateLimit-Limit")
    resource = _response_header(response, "X-RateLimit-Resource")
    if (
        remaining_raw is None
        or limit_raw is None
        or resource is None
        or re.fullmatch(r"[0-9]+", remaining_raw) is None
        or re.fullmatch(r"[0-9]+", limit_raw) is None
        or re.fullmatch(r"[a-z0-9._-]{1,64}", resource) is None
    ):
        raise ValueError("RATE_LIMIT_EVIDENCE_INVALID")
    reset = _response_header(response, "X-RateLimit-Reset-At")
    if reset is not None:
        try:
            datetime.strptime(reset, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            raise ValueError("RATE_LIMIT_EVIDENCE_INVALID") from None
    return ParsedPublicationResponse(
        status=response.status,
        projection=projection,
        server_remaining=int(remaining_raw),
        rate_limited=response.status == 429,
        retry_after=_response_header(response, "Retry-After") is not None,
        rate_scope_hash=rate_scope,
        rate_limit=int(limit_raw),
        reset_at=reset,
        resource_bucket=resource,
    )


def _response_mismatch_reason(
    dispatch: ExactPublicationDispatch, manifest: ProposalManifest
) -> str:
    key = dispatch.operation_key
    if key == "matching_refs.list":
        return "HEAD_REF_EXISTS"
    if key == "pull_requests.matching.list":
        return "PR_ALREADY_EXISTS"
    if key == "ref.get":
        return (
            "BASE_REF_CHANGED"
            if dispatch.expected_projection.get("ref") == manifest.base_ref
            else "REF_RESPONSE_INVALID"
        )
    if key == "git_ref.create":
        return "REF_RESPONSE_INVALID"
    if key in {"pull_request.create", "pull_request.get"}:
        return "PR_RESPONSE_INVALID"
    if key.startswith("git_") or key == "commit.get":
        return "GIT_OBJECT_RESPONSE_INVALID"
    return "PUBLICATION_INPUT_MISMATCH"


class PublicationStepAdmission(GitHubRecord):
    profile: Literal["github-publication-fixture-step-admission"] = (
        "github-publication-fixture-step-admission"
    )
    schema_version: Literal[STEP_ADMISSION_SCHEMA] = STEP_ADMISSION_SCHEMA
    attempt_id: str = Field(min_length=1, max_length=128)
    step_id: str = Field(min_length=1, max_length=160)
    ordinal: int = Field(gt=0)
    operation_key: str = Field(min_length=1, max_length=64)
    planned_request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    request_body_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    expected_identity: str = Field(min_length=1, max_length=256)
    local_budget_before: int = Field(gt=0)
    local_budget_after: int = Field(ge=0)
    rate_observation: RecordReference
    attempt_claim: RecordReference
    lease_evidence: RecordReference
    provider_key: RecordReference
    provider_public_key_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    monotonic_deadline_class: Literal["ten-minute-publication-window"] = (
        "ten-minute-publication-window"
    )
    dispatch_rate_check_at: str | None = None
    dispatch_rate_check_fresh: Literal[True] | None = None
    dispatch_rate_check_scoped: Literal[True] | None = None
    dispatch_rate_check_sufficient: Literal[True] | None = None
    monotonic_elapsed_milliseconds: int | None = Field(default=None, ge=0, le=600_000)
    repository_identity_observation: RecordReference | None = None
    derived_from_result: RecordReference | None = None
    retry_allowed: Literal[False] = False
    state: Literal["fixture_response_admitted_not_evaluated"] = (
        "fixture_response_admitted_not_evaluated"
    )

    @model_validator(mode="after")
    def exact_step_shape(self) -> "PublicationStepAdmission":
        if self.operation_key not in ALL_KEYS:
            raise ValueError("operation key is not admitted")
        if self.local_budget_after != self.local_budget_before - 1:
            raise ValueError("step must consume exactly one budget unit")
        if (self.operation_key in MUTATION_KEYS) != (
            self.repository_identity_observation is not None
        ):
            raise ValueError("mutation identity evidence shape mismatch")
        if (self.operation_key == "pull_request.get") != (
            self.derived_from_result is not None
        ):
            raise ValueError("derived request evidence shape mismatch")
        checks = (
            self.dispatch_rate_check_at,
            self.dispatch_rate_check_fresh,
            self.dispatch_rate_check_scoped,
            self.dispatch_rate_check_sufficient,
            self.monotonic_elapsed_milliseconds,
        )
        if (self.ordinal == 1) != all(value is not None for value in checks):
            raise ValueError("first-dispatch rate evidence shape mismatch")
        if self.dispatch_rate_check_at is not None:
            datetime.strptime(self.dispatch_rate_check_at, "%Y-%m-%dT%H:%M:%SZ")
        return self


class RateBudgetObservation(GitHubRecord):
    profile: Literal["github-rate-budget-observation"] = (
        "github-rate-budget-observation"
    )
    schema_version: Literal[RATE_OBSERVATION_SCHEMA] = RATE_OBSERVATION_SCHEMA
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
    provider_public_key_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
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
    def valid_times(cls, value: str | None) -> str | None:
        if value is not None:
            datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        return value


def admit_rate_budget(
    observation: RateBudgetObservation, *, file_count: int, now: str
) -> RequestBudget:
    from datetime import datetime

    observed = datetime.strptime(observation.observed_at, "%Y-%m-%dT%H:%M:%SZ")
    current = datetime.strptime(now, "%Y-%m-%dT%H:%M:%SZ")
    age = (current - observed).total_seconds()
    if age < 0 or age > 60 or observation.retry_after_present:
        raise ValueError("RATE_LIMIT_EVIDENCE_INVALID")
    return RequestBudget(file_count, observation.remaining)


def rate_scope_hash(observation: RateBudgetObservation) -> str:
    return _hash_json(
        {
            "repository_profile": observation.repository_profile.content_hash,
            "api_profile": observation.api_profile.content_hash,
            "repository_id": observation.repository_id,
            "account_id": observation.account_id,
            "app_id": observation.app_id,
            "installation_id": observation.installation_id,
            "provider_id": observation.provider_id,
            "provider_version": observation.provider_version,
            "provider_key": observation.provider_key.content_hash,
            "provider_public_key_sha256": observation.provider_public_key_sha256,
            "api_version": observation.api_version,
            "resource_bucket": observation.resource_bucket,
        }
    )


class PublicationStepResult(GitHubRecord):
    profile: Literal["github-publication-fixture-step-result"] = (
        "github-publication-fixture-step-result"
    )
    schema_version: Literal[STEP_RESULT_SCHEMA] = STEP_RESULT_SCHEMA
    attempt_id: str = Field(min_length=1, max_length=128)
    step_id: str = Field(min_length=1, max_length=160)
    ordinal: int = Field(gt=0)
    operation_key: str = Field(min_length=1, max_length=64)
    admission: RecordReference
    accepted_status: int = Field(ge=100, le=599)
    response_projection_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    expected_identity_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    observed_identity_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    identity_match: bool
    fixture_outcome: Literal["FIXTURE_MATCHED", "FIXTURE_AMBIGUOUS"]
    server_remaining: int = Field(ge=0)
    resource_bucket: str = Field(min_length=1, max_length=64)
    rate_limit: int = Field(ge=0)
    reset_at: str | None = None
    retry_after_class: Literal["absent", "present"]
    provider_key: RecordReference
    provider_public_key_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    response_provenance: Literal["immutable_offline_fixture_transcript"] = (
        "immutable_offline_fixture_transcript"
    )
    completed_at: str
    repository_identity_observation: RecordReference | None = None

    @model_validator(mode="after")
    def exact_result_shape(self) -> "PublicationStepResult":
        if self.operation_key not in ALL_KEYS:
            raise ValueError("operation key is not admitted")
        if self.fixture_outcome == "FIXTURE_MATCHED" and (
            self.accepted_status not in {200, 201} or not self.identity_match
        ):
            raise ValueError("confirmed result is not exact")
        if (self.operation_key in MUTATION_KEYS) != (
            self.repository_identity_observation is not None
        ):
            raise ValueError("mutation identity evidence shape mismatch")
        return self


class ReadAdmittedWithoutResult(ClosedModel):
    state: Literal["fixture_read_admitted_without_result"] = (
        "fixture_read_admitted_without_result"
    )
    step_id: str
    admission: RecordReference


class ReadResultPresent(ClosedModel):
    state: Literal["fixture_read_result_present"] = "fixture_read_result_present"
    step_id: str
    admission: RecordReference
    result: RecordReference
    accepted_status: int
    response_projection_hash: str
    expected_identity_hash: str
    observed_identity_hash: str
    completed_at: str


class MutationAdmittedWithoutResult(ClosedModel):
    state: Literal["fixture_mutation_admitted_without_result"] = (
        "fixture_mutation_admitted_without_result"
    )
    step_id: str
    admission: RecordReference
    repository_identity_observation: RecordReference


class MutationResultPresent(ClosedModel):
    state: Literal["fixture_mutation_result_present"] = (
        "fixture_mutation_result_present"
    )
    step_id: str
    admission: RecordReference
    result: RecordReference
    repository_identity_observation: RecordReference
    accepted_status: int
    response_projection_hash: str
    expected_identity_hash: str
    observed_identity_hash: str
    completed_at: str


StepState = Annotated[
    Union[
        ReadAdmittedWithoutResult,
        ReadResultPresent,
        MutationAdmittedWithoutResult,
        MutationResultPresent,
    ],
    Field(discriminator="state"),
]


class PublicationReceipt(GitHubRecord):
    profile: Literal["github-publication-fixture-receipt"] = (
        "github-publication-fixture-receipt"
    )
    schema_version: Literal[RECEIPT_SCHEMA] = RECEIPT_SCHEMA
    attempt_id: str = Field(min_length=1, max_length=128)
    rate_observation: RecordReference
    rate_scope_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    upstream_records: tuple[RecordReference, ...] = Field(min_length=17, max_length=17)
    authorization: RecordReference
    manifest: RecordReference
    plan: RecordReference
    operation_intent: RecordReference
    publication_intent: RecordReference
    attempt_claim: RecordReference
    lease_evidence: RecordReference
    base_tree_closure: RecordReference
    base_tree_source_observation: RecordReference
    provider_key: RecordReference
    provider_public_key_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    repository_id: int = Field(gt=0)
    base_ref: str
    head_ref: str
    base_ref_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    head_ref_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    base_commit_oid: str
    proposal_tree_oid: str
    proposal_commit_oid: str
    fixture_pull_request_number: int | None = Field(default=None, gt=0)
    step_states: tuple[StepState, ...]
    branch_fixture_outcome: Literal[
        "NOT_EVALUATED",
        "FIXTURE_CREATED_MATCH",
        "FIXTURE_REFUSED",
        "FIXTURE_CONFLICT",
        "FIXTURE_AMBIGUOUS",
    ]
    pull_request_fixture_outcome: Literal[
        "NOT_EVALUATED",
        "FIXTURE_CREATED_MATCH",
        "FIXTURE_REFUSED",
        "FIXTURE_CONFLICT",
        "FIXTURE_AMBIGUOUS",
    ]
    execution_scope: Literal["immutable_offline_fixture_transcript"] = (
        "immutable_offline_fixture_transcript"
    )
    fixture_conformance_complete: bool
    fixture_conformance_passed: bool
    live_publication_claimed: Literal[False] = False
    reason_codes: tuple[str, ...]
    merge_authorized: Literal[False] = False
    merge_requested: Literal[False] = False
    approval_effect: Literal["none"] = "none"
    decision_effect: Literal["none"] = "none"
    membership_effect: Literal["none"] = "none"
    production_use_allowed: Literal[False] = False

    @model_validator(mode="after")
    def terminal_truth(self) -> "PublicationReceipt":
        if self.reason_codes != tuple(sorted(set(self.reason_codes))):
            raise ValueError("reason codes must be sorted and unique")
        if not set(self.reason_codes).issubset(PUBLICATION_CLOSED_REASONS):
            raise ValueError("reason code is outside the frozen vocabulary")
        expected = (
            self.branch_fixture_outcome == "FIXTURE_CREATED_MATCH"
            and self.pull_request_fixture_outcome == "FIXTURE_CREATED_MATCH"
            and not self.reason_codes
        )
        if (
            self.fixture_conformance_complete != expected
            or self.fixture_conformance_passed != expected
        ):
            raise ValueError("terminal factual booleans are inconsistent")
        if (
            self.fixture_conformance_complete
            and self.fixture_pull_request_number is None
        ):
            raise ValueError(
                "complete fixture receipt requires the fixture pull request number"
            )
        return self


class PublicationTerminalFailure(GitHubRecord):
    profile: Literal["github-publication-fixture-terminal-failure"] = (
        "github-publication-fixture-terminal-failure"
    )
    schema_version: Literal["github-publication-fixture-terminal-failure/0.1.0"] = (
        "github-publication-fixture-terminal-failure/0.1.0"
    )
    attempt_claim: RecordReference
    base_tree_closure_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    base_tree_source_observation_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    authorization_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    manifest_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    plan_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    publication_intent_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    lease_evidence_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    step_states: tuple[StepState, ...]
    reason_code: Literal[
        "PUBLICATION_RECEIPT_STORE_FAILED",
        "PUBLICATION_LEASE_EVIDENCE_STORE_FAILED",
        "PUBLICATION_AUTH_EXPIRED",
        "RATE_LIMIT_EVIDENCE_INVALID",
        "INSUFFICIENT_RATE_BUDGET",
        "PR_RESPONSE_INVALID",
        "PUBLICATION_INPUT_MISMATCH",
    ]
    merge_authorized: Literal[False] = False


def _store_terminal_capsule(
    *,
    evidence_directory: Path,
    claim_reference: RecordReference,
    governance: PublicationGovernanceChain,
    step_states: Sequence[StepState],
    created_at: str,
    reason_code: str,
) -> PublicationTerminalFailure:
    try:
        capsule = seal_record(
            PublicationTerminalFailure,
            {
                "attempt_claim": claim_reference,
                "base_tree_closure_hash": governance.base_tree_closure.content_hash,
                "base_tree_source_observation_hash": governance.recursive_tree_observation.content_hash,
                "authorization_hash": governance.authorization.content_hash,
                "manifest_hash": governance.manifest.content_hash,
                "plan_hash": governance.plan.content_hash,
                "publication_intent_hash": governance.publication_intent.content_hash,
                "lease_evidence_hash": governance.lease_evidence.content_hash,
                "step_states": tuple(step_states),
                "reason_code": reason_code,
                "created_at": created_at,
            },
        )
        write_durable_record(
            evidence_directory / "terminal-failure.json",
            capsule,
            reject_existing=True,
        )
    except Exception:
        raise ValueError("TERMINAL_FAILURE_STORE_FAILED") from None
    return capsule


class TerminalArtifactInventory(GitHubRecord):
    profile: Literal["github-publication-fixture-terminal-artifact-inventory"] = (
        "github-publication-fixture-terminal-artifact-inventory"
    )
    schema_version: Literal[
        "github-publication-fixture-terminal-artifact-inventory/0.1.0"
    ] = "github-publication-fixture-terminal-artifact-inventory/0.1.0"
    original_claim: RecordReference
    last_step_record: RecordReference
    receipt_present: bool
    failure_capsule_present: bool
    receipt: RecordReference | None = None
    failure_capsule: RecordReference | None = None
    step_state_inventory_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def exact_terminal_shape(self) -> "TerminalArtifactInventory":
        if self.receipt_present != (self.receipt is not None):
            raise ValueError("receipt inventory shape mismatch")
        if self.failure_capsule_present != (self.failure_capsule is not None):
            raise ValueError("failure capsule inventory shape mismatch")
        if self.receipt_present and self.failure_capsule_present:
            raise ValueError("terminal inventory is not exclusive")
        return self


def publication_sequence(file_hashes: Sequence[str]) -> tuple[tuple[str, str], ...]:
    """Return the closed order, with each mutation preceded by identity read."""

    ordered = tuple(sorted(file_hashes))
    if not 1 <= len(ordered) <= 64 or len(set(ordered)) != len(ordered):
        raise ValueError("invalid sorted publication files")
    steps: list[tuple[str, str]] = []
    for digest in ordered:
        steps.extend((("repository.get", "repository"), ("git_blob.create", digest)))
    steps.extend(
        (
            ("repository.get", "repository"),
            ("git_tree.create", "proposal-tree"),
            ("repository.get", "repository"),
            ("git_commit.create", "proposal-commit"),
            ("ref.get", "base-ref"),
            ("matching_refs.list", "head-absent"),
            ("repository.get", "repository"),
            ("git_ref.create", "proposal-ref"),
            ("ref.get", "head-ref"),
            ("ref.get", "base-ref"),
            ("pull_requests.matching.list", "no-matching-pr"),
            ("repository.get", "repository"),
            ("pull_request.create", "proposal-pr"),
            ("pull_request.get", "proposal-pr"),
        )
    )
    return tuple(steps)


def evaluate_governed_publication(
    *,
    governance: PublicationGovernanceChain,
    rate_observation_record: RateBudgetObservation,
    artifact_root: Path,
    transcript: OfflinePublicationTranscript,
    now: str,
    workspace: Workspace,
    configured_principal: str,
    lease_check_at: str,
    first_dispatch_check_at: str,
    monotonic_elapsed_milliseconds: int,
) -> PublicationReceipt:
    """Evaluate one offline transcript without claiming a GitHub publication."""
    manifest = governance.manifest
    authorization = governance.authorization
    if type(transcript) is not OfflinePublicationTranscript:
        raise ValueError("LIVE_USE_PROHIBITED")
    # Re-snapshot the exact immutable values at the evaluator boundary. This
    # also rejects a frozen dataclass that was bypass-mutated after creation.
    transcript = OfflinePublicationTranscript(entries=transcript.entries)
    if not ledger_exists(workspace):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    record_store_root = workspace.root
    policy_evidence_records = tuple(
        pair
        for evidence in (
            governance.rate_source_observation_chain,
            *governance.branch_rules_observation_chain,
            *governance.ruleset_observation_chain,
        )
        for pair in (
            (evidence.provider_key_reference, evidence.provider_key_record),
            (evidence.intent_record.authorization, evidence.authorization_record),
            (evidence.attempt_claim_record.intent, evidence.intent_record),
            (
                evidence.lease_evidence_record.attempt_claim,
                evidence.attempt_claim_record,
            ),
            (
                evidence.observation_record.lease_evidence,
                evidence.lease_evidence_record,
            ),
            (evidence.observation_reference, evidence.observation_record),
        )
    )
    _verify_reopened_records(
        record_store_root,
        (
            (manifest.repository_profile, governance.repository_profile_record),
            (manifest.api_profile, governance.api_profile_record),
            (manifest.repository_extension, governance.repository_extension_record),
            (manifest.task_packet, governance.task_packet_record),
            (manifest.handoff, governance.handoff_record),
            (manifest.scope_review, governance.scope_review_record),
            (authorization.provider_key, governance.provider_key_record),
            (
                governance.base_tree_closure.source_authorization,
                governance.source_authorization_record,
            ),
            (
                governance.base_tree_closure.source_intent,
                governance.source_intent_record,
            ),
            (
                governance.base_tree_closure.source_attempt_claim,
                governance.source_attempt_claim_record,
            ),
            (
                governance.base_tree_closure.source_lease_evidence,
                governance.source_lease_evidence_record,
            ),
            (
                governance.source_lease_evidence_record.credential_lease_evidence,
                governance.source_credential_lease_evidence_record,
            ),
            (
                rate_observation_record.source_observation,
                governance.rate_source_observation_record,
            ),
            (manifest.base_observation, governance.base_identity_observation),
            (
                governance.base_tree_closure.source_observation,
                governance.recursive_tree_observation,
            ),
            (manifest.base_tree_closure, governance.base_tree_closure),
            (authorization.manifest, manifest),
            (authorization.rate_observation, rate_observation_record),
            (governance.plan.authorization, authorization),
            (governance.operation_intent.plan, governance.plan),
            (
                governance.publication_intent.operation_intent,
                governance.operation_intent,
            ),
            (
                governance.attempt_claim.publication_intent,
                governance.publication_intent,
            ),
            *policy_evidence_records,
        ),
    )
    _verify_complete_upstream_inventory(
        record_store_root, governance.plan.upstream_records
    )
    if authorization.authorized_principal != configured_principal:
        raise ValueError("PUBLICATION_AUTH_INVALID")
    if not all(
        (
            authorization.repository_id == rate_observation_record.repository_id,
            authorization.account_id == rate_observation_record.account_id,
            authorization.app_id == rate_observation_record.app_id,
            authorization.installation_id == rate_observation_record.installation_id,
            authorization.provider_id == rate_observation_record.provider_id,
            authorization.provider_version == rate_observation_record.provider_version,
            authorization.provider_key == rate_observation_record.provider_key,
            authorization.provider_public_key_sha256
            == rate_observation_record.provider_public_key_sha256,
            authorization.api_version == rate_observation_record.api_version,
            authorization.resource_bucket == rate_observation_record.resource_bucket,
            authorization.commit_message_hash == manifest.commit_message.content_hash,
            authorization.commit_message_byte_count
            == manifest.commit_message_byte_count,
            authorization.pull_request_title_hash
            == manifest.pull_request_title.content_hash,
            authorization.pull_request_title_byte_count
            == manifest.pull_request_title_byte_count,
            authorization.pull_request_body_hash
            == manifest.pull_request_body.content_hash,
            authorization.pull_request_body_byte_count
            == manifest.pull_request_body_byte_count,
        )
    ):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    calculated_tree = apply_proposal(
        governance.base_tree_closure.entries, manifest.files, manifest.object_format
    )
    if calculated_tree != manifest.proposal_tree_oid:
        raise ValueError("GIT_OBJECT_ID_MISMATCH")
    if (
        authorization.rate_observation.content_hash
        != rate_observation_record.content_hash
    ):
        raise ValueError("RATE_LIMIT_EVIDENCE_INVALID")
    if (
        rate_observation_record.repository_profile.content_hash
        != manifest.repository_profile.content_hash
        or rate_observation_record.api_profile.content_hash
        != manifest.api_profile.content_hash
        or rate_observation_record.repository_id != manifest.repository_id
        or rate_observation_record.account_id != manifest.account_id
        or governance.lease_evidence.provider_key.content_hash
        != rate_observation_record.provider_key.content_hash
        or governance.lease_evidence.provider_public_key_sha256
        != rate_observation_record.provider_public_key_sha256
    ):
        raise ValueError("RATE_LIMIT_EVIDENCE_INVALID")
    current = datetime.strptime(now, "%Y-%m-%dT%H:%M:%SZ")
    if not (
        datetime.strptime(authorization.issued_at, "%Y-%m-%dT%H:%M:%SZ")
        <= current
        <= datetime.strptime(authorization.expires_at, "%Y-%m-%dT%H:%M:%SZ")
    ):
        raise ValueError("PUBLICATION_AUTH_EXPIRED")
    if current > datetime.strptime(
        governance.operation_intent.not_after, "%Y-%m-%dT%H:%M:%SZ"
    ):
        raise ValueError("PUBLICATION_AUTH_EXPIRED")
    for observed_at in (
        governance.base_identity_observation.observed_at,
        governance.recursive_tree_observation.created_at,
        governance.branch_rules_observation_chain[0].observation_record.observed_at,
        governance.ruleset_observation_chain[0].observation_record.observed_at,
    ):
        observed = datetime.strptime(observed_at, "%Y-%m-%dT%H:%M:%SZ")
        if not 0 <= (current - observed).total_seconds() <= 900:
            raise ValueError("BASE_OBSERVATION_STALE")
    artifact_references = tuple(item.artifact for item in manifest.files) + (
        manifest.commit_message,
        manifest.pull_request_title,
        manifest.pull_request_body,
        manifest.commit_identity_artifact,
    )
    artifacts = read_artifacts_once(
        artifact_root,
        artifact_references,
        maximum_total_bytes=manifest.aggregate_byte_count
        + manifest.commit_message_byte_count
        + manifest.pull_request_title_byte_count
        + manifest.pull_request_body_byte_count
        + 4096,
    )
    dispatches = build_exact_publication_dispatches(
        manifest, governance.repository_profile_record, artifacts
    )
    if len(transcript.entries) != len(dispatches) or tuple(
        entry.planned_request_hash for entry in transcript.entries
    ) != tuple(dispatch.request_hash for dispatch in dispatches):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    request_hashes = tuple(item.request_hash for item in dispatches)
    endpoint_plan = tuple(item.operation_key for item in dispatches)
    by_key = {
        key: tuple(
            item.request_hash for item in dispatches if item.operation_key == key
        )
        for key in MUTATION_KEYS
    }
    if not all(
        (
            request_hashes == governance.plan.ordered_request_hashes,
            request_hashes == governance.operation_intent.canonical_request_hashes,
            request_hashes == governance.publication_intent.exact_request_hashes,
            endpoint_plan == governance.plan.ordered_endpoint_plan,
            endpoint_plan == governance.operation_intent.ordered_endpoint_plan,
            endpoint_plan == governance.publication_intent.ordered_endpoint_plan,
            governance.plan.blob_request_hashes == by_key["git_blob.create"],
            governance.plan.expected_blob_oids
            == tuple(item.blob_oid for item in manifest.files),
            governance.plan.tree_request_hash == by_key["git_tree.create"][0],
            governance.plan.commit_request_hash == by_key["git_commit.create"][0],
            governance.plan.ref_request_hash == by_key["git_ref.create"][0],
            governance.plan.pull_request_request_hash
            == by_key["pull_request.create"][0],
        )
    ):
        raise ValueError("PUBLICATION_INPUT_MISMATCH")
    if governance.lease_evidence.first_rate_check_at != lease_check_at:
        raise ValueError("RATE_LIMIT_EVIDENCE_INVALID")
    admit_rate_budget(
        rate_observation_record, file_count=len(manifest.files), now=lease_check_at
    )
    attempt_token = governance.attempt_claim.attempt_id.rsplit(":", 1)[-1]
    evidence_directory = _fixture_attempt_directory(workspace, attempt_token)
    claim_filename = f"claim-{attempt_token}.json"
    lease_filename = f"lease-{attempt_token}.json"
    try:
        claim_ref = RecordReference(
            reference=claim_filename,
            content_hash=governance.attempt_claim.content_hash,
        )
        lease_ref = RecordReference(
            reference=lease_filename,
            content_hash=governance.lease_evidence.content_hash,
        )
    except Exception:
        raise ValueError("PUBLICATION_INPUT_MISMATCH") from None
    try:
        claim_path, _ = write_durable_record(
            evidence_directory / claim_filename,
            governance.attempt_claim,
            reject_existing=True,
        )
    except IntegrityError as exc:
        code = (
            "PUBLICATION_ALREADY_CLAIMED"
            if "ATTEMPT_ALREADY_CLAIMED" in str(exc)
            else "PUBLICATION_CLAIM_CONFLICT"
        )
        raise ValueError(code) from None
    except Exception:
        raise ValueError("PUBLICATION_CLAIM_STORE_FAILED") from None
    if claim_path.name != claim_filename:
        raise ValueError("PUBLICATION_CLAIM_STORE_FAILED") from None
    try:
        lease_path, _ = write_durable_record(
            evidence_directory / lease_filename,
            governance.lease_evidence,
            reject_existing=True,
        )
    except Exception:
        _store_terminal_capsule(
            evidence_directory=evidence_directory,
            claim_reference=claim_ref,
            governance=governance,
            step_states=(),
            created_at=now,
            reason_code="PUBLICATION_LEASE_EVIDENCE_STORE_FAILED",
        )
        raise ValueError("PUBLICATION_LEASE_EVIDENCE_STORE_FAILED") from None
    if lease_path.name != lease_filename:
        _store_terminal_capsule(
            evidence_directory=evidence_directory,
            claim_reference=claim_ref,
            governance=governance,
            step_states=(),
            created_at=now,
            reason_code="PUBLICATION_LEASE_EVIDENCE_STORE_FAILED",
        )
        raise ValueError("PUBLICATION_LEASE_EVIDENCE_STORE_FAILED") from None
    step_states: list[StepState] = []

    def terminal_raise(reason_code: str) -> None:
        _store_terminal_capsule(
            evidence_directory=evidence_directory,
            claim_reference=claim_ref,
            governance=governance,
            step_states=step_states,
            created_at=now,
            reason_code=reason_code,
        )
        raise ValueError(reason_code) from None

    latest_repository_result: RecordReference | None = None
    created_pull_number: int | None = None
    created_pull_result: RecordReference | None = None
    reasons: list[str] = []
    branch_fixture_outcome = "NOT_EVALUATED"
    pr_fixture_outcome = "NOT_EVALUATED"
    try:
        scope_hash = rate_scope_hash(rate_observation_record)
        lease_wall = datetime.strptime(lease_check_at, "%Y-%m-%dT%H:%M:%SZ")
        dispatch_wall = datetime.strptime(first_dispatch_check_at, "%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        terminal_raise("RATE_LIMIT_EVIDENCE_INVALID")
    if (
        dispatch_wall < lease_wall
        or type(monotonic_elapsed_milliseconds) is not int
        or monotonic_elapsed_milliseconds < 0
        or monotonic_elapsed_milliseconds > 600_000
    ):
        _store_terminal_capsule(
            evidence_directory=evidence_directory,
            claim_reference=claim_ref,
            governance=governance,
            step_states=(),
            created_at=now,
            reason_code="PUBLICATION_AUTH_EXPIRED",
        )
        raise ValueError("PUBLICATION_AUTH_EXPIRED")
    try:
        budget = admit_rate_budget(
            rate_observation_record,
            file_count=len(manifest.files),
            now=first_dispatch_check_at,
        )
    except ValueError as exc:
        code = (
            "INSUFFICIENT_RATE_BUDGET"
            if "INSUFFICIENT" in str(exc)
            else "RATE_LIMIT_EVIDENCE_INVALID"
        )
        _store_terminal_capsule(
            evidence_directory=evidence_directory,
            claim_reference=claim_ref,
            governance=governance,
            step_states=(),
            created_at=now,
            reason_code=code,
        )
        raise ValueError(code) from None
    except Exception:
        terminal_raise("RATE_LIMIT_EVIDENCE_INVALID")
    for dispatch in dispatches:
        planned_request_hash = dispatch.request_hash
        if dispatch.operation_key == "pull_request.get":
            if created_pull_number is None or created_pull_result is None:
                terminal_raise("PR_RESPONSE_INVALID")
            try:
                target = dispatch.target.replace(
                    "{created_pull_number}", str(created_pull_number)
                )
                expected = {
                    **dispatch.expected_projection,
                    "pull_number": created_pull_number,
                }
                dispatch = replace(
                    dispatch,
                    target=target,
                    expected_projection=expected,
                    request_hash=_request_hash(dispatch.method, target, dispatch.body),
                )
            except Exception:
                terminal_raise("PR_RESPONSE_INVALID")
        is_mutation = dispatch.operation_key in MUTATION_KEYS
        if is_mutation and latest_repository_result is None:
            terminal_raise("PUBLICATION_INPUT_MISMATCH")
        before = budget.remaining
        try:
            budget.admit_dispatch(len(dispatches) - dispatch.ordinal)
        except ValueError:
            reasons.append("INSUFFICIENT_RATE_BUDGET")
            break
        except Exception:
            terminal_raise("RATE_LIMIT_EVIDENCE_INVALID")
        try:
            expected_hash = _hash_json(dispatch.expected_projection)
            step_id = f"{governance.attempt_claim.attempt_id}-{dispatch.ordinal:03d}"
        except Exception:
            terminal_raise("PUBLICATION_INPUT_MISMATCH")
        try:
            admission = seal_record(
                PublicationStepAdmission,
                {
                    "attempt_id": governance.attempt_claim.attempt_id,
                    "step_id": step_id,
                    "ordinal": dispatch.ordinal,
                    "operation_key": dispatch.operation_key,
                    "planned_request_hash": planned_request_hash,
                    "request_body_hash": dispatch.request_hash,
                    "expected_identity": expected_hash,
                    "local_budget_before": before,
                    "local_budget_after": budget.remaining,
                    "rate_observation": authorization.rate_observation,
                    "attempt_claim": claim_ref,
                    "lease_evidence": lease_ref,
                    "provider_key": rate_observation_record.provider_key,
                    "provider_public_key_sha256": rate_observation_record.provider_public_key_sha256,
                    "dispatch_rate_check_at": first_dispatch_check_at
                    if dispatch.ordinal == 1
                    else None,
                    "dispatch_rate_check_fresh": True
                    if dispatch.ordinal == 1
                    else None,
                    "dispatch_rate_check_scoped": True
                    if dispatch.ordinal == 1
                    else None,
                    "dispatch_rate_check_sufficient": True
                    if dispatch.ordinal == 1
                    else None,
                    "monotonic_elapsed_milliseconds": monotonic_elapsed_milliseconds
                    if dispatch.ordinal == 1
                    else None,
                    "repository_identity_observation": latest_repository_result
                    if is_mutation
                    else None,
                    "derived_from_result": created_pull_result
                    if dispatch.operation_key == "pull_request.get"
                    else None,
                    "created_at": now,
                },
            )
            admission_path, _ = write_durable_record(
                evidence_directory / f"admission-{dispatch.ordinal:03d}.json",
                admission,
                reject_existing=True,
            )
        except Exception:
            reasons.append("STEP_ADMISSION_STORE_FAILED")
            break
        try:
            admission_ref = RecordReference(
                reference=admission_path.name, content_hash=admission.content_hash
            )
        except Exception:
            terminal_raise("PUBLICATION_INPUT_MISMATCH")
        try:
            raw_response = transcript.entries[dispatch.ordinal - 1].response
            response = _strict_response_projection(
                dispatch, raw_response, manifest=manifest, rate_scope=scope_hash
            )
        except Exception as exc:
            safe_code = str(exc)
            if safe_code in PUBLICATION_CLOSED_REASONS:
                reasons.append(safe_code)
            if is_mutation:
                assert latest_repository_result is not None
                step_states.append(
                    MutationAdmittedWithoutResult(
                        step_id=step_id,
                        admission=admission_ref,
                        repository_identity_observation=latest_repository_result,
                    )
                )
                reasons.append("MUTATION_OUTCOME_AMBIGUOUS")
                if dispatch.operation_key == "git_ref.create":
                    branch_fixture_outcome = "FIXTURE_AMBIGUOUS"
                if dispatch.operation_key == "pull_request.create":
                    pr_fixture_outcome = "FIXTURE_AMBIGUOUS"
            else:
                step_states.append(
                    ReadAdmittedWithoutResult(step_id=step_id, admission=admission_ref)
                )
                reasons.append("MUTATION_DISPATCH_FAILED")
            break
        mismatch_reason: str | None = None
        if (
            response.rate_scope_hash != scope_hash
            or response.rate_limit != rate_observation_record.limit
            or response.resource_bucket != rate_observation_record.resource_bucket
        ):
            reasons.append("RATE_LIMIT_EVIDENCE_INVALID")
            matched = False
        else:
            matched = True
            try:
                budget.observe(
                    response.server_remaining,
                    retry_after=response.retry_after,
                    rate_limited=response.rate_limited,
                )
            except ValueError as exc:
                reasons.append(
                    "RATE_LIMITED"
                    if "RATE_LIMITED" in str(exc)
                    else "RATE_LIMIT_EVIDENCE_INVALID"
                )
                matched = False
            if matched is not False and dispatch.operation_key == "pull_request.create":
                pull_number = response.projection.get("pull_number")
                matched = (
                    type(pull_number) is int
                    and pull_number > 0
                    and all(
                        response.projection.get(key) == value
                        for key, value in dispatch.expected_projection.items()
                    )
                    and set(response.projection)
                    == set(dispatch.expected_projection) | {"pull_number"}
                )
                if matched:
                    created_pull_number = pull_number
                else:
                    mismatch_reason = _response_mismatch_reason(dispatch, manifest)
            elif matched is not False:
                matched = response.projection == dispatch.expected_projection
                if not matched:
                    mismatch_reason = _response_mismatch_reason(dispatch, manifest)
        expected_status = 201 if is_mutation else 200
        confirmed = response.status == expected_status and matched
        try:
            observed_hash = _hash_json(response.projection)
        except Exception:
            terminal_raise("PR_RESPONSE_INVALID")
        try:
            result = seal_record(
                PublicationStepResult,
                {
                    "attempt_id": governance.attempt_claim.attempt_id,
                    "step_id": step_id,
                    "ordinal": dispatch.ordinal,
                    "operation_key": dispatch.operation_key,
                    "admission": admission_ref,
                    "accepted_status": response.status,
                    "response_projection_hash": observed_hash,
                    "expected_identity_hash": expected_hash,
                    "observed_identity_hash": observed_hash,
                    "identity_match": matched,
                    "fixture_outcome": (
                        "FIXTURE_MATCHED" if confirmed else "FIXTURE_AMBIGUOUS"
                    ),
                    "server_remaining": response.server_remaining,
                    "completed_at": now,
                    "resource_bucket": response.resource_bucket,
                    "rate_limit": response.rate_limit or 0,
                    "reset_at": response.reset_at,
                    "retry_after_class": "present"
                    if response.retry_after
                    else "absent",
                    "provider_key": rate_observation_record.provider_key,
                    "provider_public_key_sha256": rate_observation_record.provider_public_key_sha256,
                    "response_provenance": "immutable_offline_fixture_transcript",
                    "repository_identity_observation": latest_repository_result
                    if is_mutation
                    else None,
                    "created_at": now,
                },
            )
            result_path, _ = write_durable_record(
                evidence_directory / f"result-{dispatch.ordinal:03d}.json",
                result,
                reject_existing=True,
            )
        except Exception:
            if is_mutation:
                assert latest_repository_result is not None
                step_states.append(
                    MutationAdmittedWithoutResult(
                        step_id=step_id,
                        admission=admission_ref,
                        repository_identity_observation=latest_repository_result,
                    )
                )
                reasons.extend(
                    ("STEP_RESULT_STORE_FAILED", "MUTATION_OUTCOME_AMBIGUOUS")
                )
                if dispatch.operation_key == "git_ref.create":
                    branch_fixture_outcome = "FIXTURE_AMBIGUOUS"
                if dispatch.operation_key == "pull_request.create":
                    pr_fixture_outcome = "FIXTURE_AMBIGUOUS"
            else:
                step_states.append(
                    ReadAdmittedWithoutResult(step_id=step_id, admission=admission_ref)
                )
                reasons.append("STEP_RESULT_STORE_FAILED")
            break
        try:
            result_ref = RecordReference(
                reference=result_path.name, content_hash=result.content_hash
            )
            common = dict(
                step_id=step_id,
                admission=admission_ref,
                result=result_ref,
                accepted_status=response.status,
                response_projection_hash=observed_hash,
                expected_identity_hash=expected_hash,
                observed_identity_hash=observed_hash,
                completed_at=now,
            )
            if is_mutation:
                assert latest_repository_result is not None
                step_states.append(
                    MutationResultPresent(
                        **common,
                        repository_identity_observation=latest_repository_result,
                    )
                )
            else:
                step_states.append(ReadResultPresent(**common))
        except Exception:
            terminal_raise("PUBLICATION_INPUT_MISMATCH")
        if not confirmed:
            if mismatch_reason is not None:
                reasons.append(mismatch_reason)
            if mismatch_reason == "HEAD_REF_EXISTS":
                branch_fixture_outcome = "FIXTURE_CONFLICT"
            elif mismatch_reason == "PR_ALREADY_EXISTS":
                pr_fixture_outcome = "FIXTURE_CONFLICT"
            else:
                reasons.append(
                    "MUTATION_OUTCOME_AMBIGUOUS"
                    if is_mutation
                    else "MUTATION_DISPATCH_FAILED"
                )
                if dispatch.operation_key == "git_ref.create":
                    branch_fixture_outcome = "FIXTURE_AMBIGUOUS"
                if dispatch.operation_key == "pull_request.create":
                    pr_fixture_outcome = "FIXTURE_AMBIGUOUS"
            break
        if dispatch.operation_key == "repository.get":
            latest_repository_result = result_ref
        if dispatch.operation_key == "git_ref.create":
            branch_fixture_outcome = "FIXTURE_CREATED_MATCH"
        if dispatch.operation_key == "pull_request.create":
            pr_fixture_outcome = "FIXTURE_CREATED_MATCH"
        if dispatch.operation_key == "pull_request.create":
            created_pull_result = result_ref
    fixture_complete = not reasons and len(step_states) == len(dispatches)
    try:
        receipt = seal_record(
            PublicationReceipt,
            {
                "attempt_id": governance.attempt_claim.attempt_id,
                "rate_observation": authorization.rate_observation,
                "rate_scope_hash": scope_hash,
                "upstream_records": governance.plan.upstream_records,
                "authorization": governance.plan.authorization,
                "manifest": authorization.manifest,
                "plan": governance.operation_intent.plan,
                "operation_intent": governance.publication_intent.operation_intent,
                "publication_intent": governance.attempt_claim.publication_intent,
                "attempt_claim": claim_ref,
                "lease_evidence": lease_ref,
                "base_tree_closure": manifest.base_tree_closure,
                "base_tree_source_observation": governance.base_tree_closure.source_observation,
                "provider_key": rate_observation_record.provider_key,
                "provider_public_key_sha256": rate_observation_record.provider_public_key_sha256,
                "repository_id": manifest.repository_id,
                "base_ref": manifest.base_ref,
                "head_ref": manifest.head_ref,
                "base_ref_hash": _hash_json(manifest.base_ref),
                "head_ref_hash": _hash_json(manifest.head_ref),
                "base_commit_oid": manifest.base_commit_oid,
                "proposal_tree_oid": manifest.proposal_tree_oid,
                "proposal_commit_oid": manifest.proposal_commit_oid,
                "fixture_pull_request_number": created_pull_number,
                "step_states": tuple(step_states),
                "branch_fixture_outcome": branch_fixture_outcome,
                "pull_request_fixture_outcome": pr_fixture_outcome,
                "fixture_conformance_complete": fixture_complete,
                "fixture_conformance_passed": fixture_complete,
                "reason_codes": tuple(sorted(set(reasons))),
                "created_at": now,
            },
        )
        write_durable_record(
            evidence_directory / "receipt.json", receipt, reject_existing=True
        )
    except Exception:
        _store_terminal_capsule(
            evidence_directory=evidence_directory,
            claim_reference=claim_ref,
            governance=governance,
            step_states=step_states,
            created_at=now,
            reason_code="PUBLICATION_RECEIPT_STORE_FAILED",
        )
        raise ValueError("PUBLICATION_RECEIPT_STORE_FAILED") from None
    try:
        _event, ledger_created = record_event(
            workspace,
            event_type="github_proposal_publication_fixture_verified",
            actor="conclave",
            authority_level="system",
            subject_refs=[receipt.attempt_id],
            artifact_hashes={
                "receipt": receipt.content_hash,
                "authorization": authorization.content_hash,
                "manifest": manifest.content_hash,
                "plan": governance.plan.content_hash,
                "attempt_claim": governance.attempt_claim.content_hash,
                "base_tree_closure": governance.base_tree_closure.content_hash,
                "rate_observation": rate_observation_record.content_hash,
            },
            payload={
                "operation_key": "github.fixture_verify_proposal_publication",
                "execution_scope": "immutable_offline_fixture_transcript",
                "fixture_conformance_complete": receipt.fixture_conformance_complete,
                "fixture_conformance_passed": receipt.fixture_conformance_passed,
                "reason_codes": list(receipt.reason_codes),
                "repository_id": receipt.repository_id,
                "authority_effect": "none",
                "decision_effect": "none",
                "membership_effect": "none",
                "merge_authorized": False,
                "production_use_allowed": False,
            },
        )
        if not ledger_created:
            raise ValueError("PUBLICATION_INPUT_MISMATCH")
    except Exception:
        raise ValueError("PUBLICATION_INPUT_MISMATCH") from None
    return receipt
