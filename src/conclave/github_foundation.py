"""Increment 21A read-only GitHub adapter foundation.

This module implements only local, closed-schema and durable-record mechanics.
It does not discover credentials, mint tokens, or perform network operations.
"""

from __future__ import annotations

import base64
import hashlib
import http.client
import json
import os
import re
import socket
import ssl
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Callable, Literal, Mapping, Protocol
from urllib.parse import quote, unquote
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .errors import IntegrityError, ValidationError
from .identity import ClosedModel, HashedRecord, sha256_bytes

REPOSITORY_PROFILE_SCHEMA = "github-repository-profile/0.1.0"
API_PROFILE_SCHEMA = "github-api-profile/0.1.0"
PROVIDER_KEY_SCHEMA = "github-credential-provider-key/0.1.0"
AUTHORIZATION_SCHEMA = "github-operation-authorization/0.1.0"
INTENT_SCHEMA = "github-operation-intent/0.1.0"
ATTEMPT_CLAIM_SCHEMA = "github-operation-attempt-claim/0.1.0"
ATTEMPT_PREIMAGE_SCHEMA = "github-operation-attempt-preimage/0.1.0"
ENDPOINT_TABLE_VERSION = "github-21a-rest-endpoints/0.1.0"
RESPONSE_PROJECTION_VERSION = "github-21a-rest-projections/0.1.0"
ATTEMPT_DOMAIN = b"CONCLAVE-GITHUB-OPERATION-ATTEMPT-V1\x00"

Hash = str
Scalar = str | int | bool
OperationKey = Literal[
    "repository.get",
    "repository_hash_algorithm.get",
    "ref.get",
    "commit.get",
    "pull_request.get",
    "check_runs.list",
    "combined_status.get",
    "reviews.list",
    "issue_comments.list",
    "review_comments.list",
    "branch_protection.get",
    "branch_rules.list",
    "repository_rulesets.list",
    "repository_ruleset.get",
]

HASH_PATTERN = r"^sha256:[0-9a-f]{64}$"
ATTEMPT_PATTERN = r"^attempt:sha256:[0-9a-f]{64}$"
SAFE_ID_PATTERN = r"^[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?$"
KEBAB_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _validate_timestamp(value: str) -> str:
    if TIMESTAMP_PATTERN.fullmatch(value) is None:
        raise ValueError("timestamp must be second-precision UTC RFC 3339 text")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError("timestamp is not a valid UTC calendar value") from exc
    return value


def _parse_timestamp(value: str) -> datetime:
    _validate_timestamp(value)
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def _validate_uuid7(value: str) -> str:
    try:
        parsed = UUID(value)
    except ValueError as exc:
        raise ValueError("identifier must be a canonical UUIDv7") from exc
    if (
        str(parsed) != value
        or parsed.version != 7
        or parsed.variant != "specified in RFC 4122"
    ):
        raise ValueError("identifier must be a canonical UUIDv7")
    return value


def _validate_reference(value: str) -> str:
    if "\\" in value or not value or len(value.encode("utf-8")) > 512:
        raise ValueError("reference must be a bounded POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("reference must be workspace-relative without traversal")
    return value


def _sorted_unique(values: tuple[str, ...]) -> tuple[str, ...]:
    if not values or tuple(sorted(set(values))) != values:
        raise ValueError("values must be non-empty, sorted, and unique")
    return values


class RecordReference(ClosedModel):
    reference: str
    content_hash: Hash = Field(pattern=HASH_PATTERN)

    @field_validator("reference")
    @classmethod
    def valid_reference(cls, value: str) -> str:
        return _validate_reference(value)


class PermissionEnvelope(ClosedModel):
    metadata: Literal["read", "none"]
    contents: Literal["read", "none"]
    pull_requests: Literal["read", "none"]
    checks: Literal["read", "none"]
    statuses: Literal["read", "none"]
    administration: Literal["read", "none"]

    def read_keys(self) -> frozenset[str]:
        return frozenset(
            name for name, value in self.model_dump().items() if value == "read"
        )


class GitHubRecord(HashedRecord):
    created_at: str
    authority_effect: Literal["none"] = "none"
    decision_effect: Literal["none"] = "none"
    membership_effect: Literal["none"] = "none"
    production_use_allowed: Literal[False] = False

    @field_validator("created_at")
    @classmethod
    def valid_created_at(cls, value: str) -> str:
        return _validate_timestamp(value)


class GitHubRepositoryProfile(GitHubRecord):
    profile: Literal["github-repository-profile"] = "github-repository-profile"
    schema_version: Literal[REPOSITORY_PROFILE_SCHEMA] = REPOSITORY_PROFILE_SCHEMA
    repository_profile_id: str = Field(min_length=1, max_length=64)
    host: Literal["github.com"] = "github.com"
    api_origin: Literal["https://api.github.com"] = "https://api.github.com"
    owner: str = Field(
        min_length=1,
        max_length=39,
        pattern=r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$",
    )
    repository: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    repository_id: int = Field(gt=0)
    repository_node_id: str | None = Field(default=None, max_length=128)
    account_id: int = Field(gt=0)
    git_object_format: Literal["sha1", "sha256"]
    default_branch: str = Field(min_length=1, max_length=255)
    allowed_base_refs: tuple[str, ...] = Field(min_length=1, max_length=8)
    credential_provider_selector: str = Field(min_length=1, max_length=128)
    expected_provider_id: str = Field(
        min_length=1, max_length=64, pattern=SAFE_ID_PATTERN
    )
    expected_provider_versions: tuple[str, ...] = Field(min_length=1, max_length=8)
    provider_key_reference: str
    provider_key_hash: Hash = Field(pattern=HASH_PATTERN)
    expected_provider_key_id: str = Field(
        min_length=1, max_length=128, pattern=SAFE_ID_PATTERN
    )
    expected_provider_public_key_sha256: Hash = Field(pattern=HASH_PATTERN)
    expected_app_id: int = Field(gt=0)
    expected_installation_id: int = Field(gt=0)
    repository_selection: Literal["selected"] = "selected"
    permission_ceiling: PermissionEnvelope
    read_operations: tuple[OperationKey, ...] = Field(min_length=1)
    live_use_allowed: Literal[False] = False

    @field_validator("repository_profile_id")
    @classmethod
    def valid_profile_id(cls, value: str) -> str:
        if len(value) > 64 or re.fullmatch(KEBAB_PATTERN, value) is None:
            raise ValueError("repository_profile_id must be lower kebab case")
        return value

    @field_validator("repository")
    @classmethod
    def no_git_suffix(cls, value: str) -> str:
        if value.lower().endswith(".git"):
            raise ValueError("repository must not use a .git suffix")
        return value

    @field_validator("default_branch")
    @classmethod
    def valid_branch(cls, value: str) -> str:
        if any(ord(char) < 32 for char in value) or "\\" in value:
            raise ValueError("branch contains a prohibited character")
        if (
            value in {".", ".."}
            or "//" in value
            or any(part in {".", ".."} for part in value.split("/"))
        ):
            raise ValueError("branch contains an ambiguous path form")
        return value

    @field_validator("allowed_base_refs")
    @classmethod
    def valid_refs(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        _sorted_unique(values)
        for value in values:
            if not value.startswith("refs/heads/"):
                raise ValueError("base refs must be full refs/heads references")
            cls.valid_branch(value.removeprefix("refs/heads/"))
        return values

    @field_validator("credential_provider_selector")
    @classmethod
    def valid_selector(cls, value: str) -> str:
        if re.fullmatch(SAFE_ID_PATTERN, value) is None:
            raise ValueError("credential provider selector must be safe ASCII")
        return value

    @field_validator("expected_provider_versions")
    @classmethod
    def valid_versions(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        _sorted_unique(values)
        if any(re.fullmatch(SAFE_ID_PATTERN, value) is None for value in values):
            raise ValueError("provider version must be safe ASCII")
        return values

    @field_validator("provider_key_reference")
    @classmethod
    def valid_key_reference(cls, value: str) -> str:
        return _validate_reference(value)

    @field_validator("read_operations")
    @classmethod
    def valid_operations(
        cls, values: tuple[OperationKey, ...]
    ) -> tuple[OperationKey, ...]:
        return _sorted_unique(values)  # type: ignore[return-value]


class GitHubApiProfile(GitHubRecord):
    profile: Literal["github-api-profile"] = "github-api-profile"
    schema_version: Literal[API_PROFILE_SCHEMA] = API_PROFILE_SCHEMA
    api_profile_id: Literal["github-rest-2026-03-10-read-only-v1"] = (
        "github-rest-2026-03-10-read-only-v1"
    )
    origin: Literal["https://api.github.com"] = "https://api.github.com"
    api_version: Literal["2026-03-10"] = "2026-03-10"
    accept: Literal["application/vnd.github+json"] = "application/vnd.github+json"
    user_agent: Literal["conclave-github-adapter/21a"] = "conclave-github-adapter/21a"
    authentication_scheme: Literal["Bearer"] = "Bearer"
    tls_policy: Literal["system-ca-hostname-tls12-plus"] = (
        "system-ca-hostname-tls12-plus"
    )
    redirect_policy: Literal["deny"] = "deny"
    proxy_policy: Literal["ignore-environment-and-deny"] = "ignore-environment-and-deny"
    connect_timeout_seconds: Literal[5] = 5
    read_timeout_seconds: Literal[20] = 20
    operation_timeout_seconds: Literal[60] = 60
    maximum_request_header_bytes: Literal[16384] = 16384
    maximum_response_header_bytes: Literal[32768] = 32768
    maximum_response_body_bytes_per_page: Literal[2097152] = 2097152
    maximum_total_response_body_bytes: Literal[8388608] = 8388608
    default_page_size: Literal[100] = 100
    maximum_pages: Literal[10] = 10
    maximum_items: Literal[1000] = 1000
    maximum_retry_transmissions_per_operation: Literal[1] = 1
    maximum_transmissions_for_one_page: Literal[2] = 2
    retry_delays_milliseconds: tuple[Literal[250], ...] = (250,)
    endpoint_table_version: Literal[ENDPOINT_TABLE_VERSION] = ENDPOINT_TABLE_VERSION
    response_projection_version: Literal[RESPONSE_PROJECTION_VERSION] = (
        RESPONSE_PROJECTION_VERSION
    )


class GitHubCredentialProviderKey(GitHubRecord):
    profile: Literal["github-credential-provider-key"] = (
        "github-credential-provider-key"
    )
    schema_version: Literal[PROVIDER_KEY_SCHEMA] = PROVIDER_KEY_SCHEMA
    provider_id: str = Field(min_length=1, max_length=64, pattern=SAFE_ID_PATTERN)
    key_id: str = Field(min_length=1, max_length=128, pattern=SAFE_ID_PATTERN)
    algorithm: Literal["Ed25519"] = "Ed25519"
    public_key: str = Field(min_length=43, max_length=43)
    public_key_sha256: Hash = Field(pattern=HASH_PATTERN)
    valid_from: str
    valid_until: str
    status: Literal["active"] = "active"

    @field_validator("valid_from", "valid_until")
    @classmethod
    def valid_time(cls, value: str) -> str:
        return _validate_timestamp(value)

    @model_validator(mode="after")
    def key_is_canonical_and_bound(self) -> "GitHubCredentialProviderKey":
        if (
            "=" in self.public_key
            or re.fullmatch(r"[A-Za-z0-9_-]{43}", self.public_key) is None
        ):
            raise ValueError("public key must be canonical unpadded base64url")
        try:
            decoded = base64.urlsafe_b64decode(self.public_key + "=")
        except Exception as exc:
            raise ValueError("public key is invalid base64url") from exc
        if len(decoded) != 32 or sha256_bytes(decoded) != self.public_key_sha256:
            raise ValueError("public key fingerprint mismatch")
        if _parse_timestamp(self.valid_from) > _parse_timestamp(self.valid_until):
            raise ValueError("provider key validity window is reversed")
        return self


@dataclass(frozen=True)
class EndpointSpec:
    path_template: str
    path_parameters: tuple[str, ...]
    fixed_query: Mapping[str, Scalar]
    paginated: bool
    additional_permission: str | None
    maximum_pages: int
    maximum_items: int


def _endpoint(
    path: str,
    params: tuple[str, ...],
    *,
    query: Mapping[str, Scalar] | None = None,
    paginated: bool = False,
    permission: str | None = None,
    pages: int = 1,
    items: int = 1,
) -> EndpointSpec:
    return EndpointSpec(
        path,
        params,
        MappingProxyType(dict(query or {})),
        paginated,
        permission,
        pages,
        items,
    )


ENDPOINTS: Mapping[str, EndpointSpec] = MappingProxyType(
    {
        "repository.get": _endpoint("/repos/{owner}/{repo}", ()),
        "repository_hash_algorithm.get": _endpoint(
            "/repos/{owner}/{repo}/hash-algorithm", ()
        ),
        "ref.get": _endpoint(
            "/repos/{owner}/{repo}/git/ref/{ref}", ("ref",), permission="contents"
        ),
        "commit.get": _endpoint(
            "/repos/{owner}/{repo}/git/commits/{commit_sha}",
            ("commit_sha",),
            permission="contents",
        ),
        "pull_request.get": _endpoint(
            "/repos/{owner}/{repo}/pulls/{pull_number}",
            ("pull_number",),
            permission="pull_requests",
        ),
        "check_runs.list": _endpoint(
            "/repos/{owner}/{repo}/commits/{commit_sha}/check-runs",
            ("commit_sha",),
            paginated=True,
            permission="checks",
            pages=10,
            items=1000,
        ),
        "combined_status.get": _endpoint(
            "/repos/{owner}/{repo}/commits/{commit_sha}/status",
            ("commit_sha",),
            paginated=True,
            permission="statuses",
            pages=10,
            items=1000,
        ),
        "reviews.list": _endpoint(
            "/repos/{owner}/{repo}/pulls/{pull_number}/reviews",
            ("pull_number",),
            paginated=True,
            permission="pull_requests",
            pages=10,
            items=1000,
        ),
        "issue_comments.list": _endpoint(
            "/repos/{owner}/{repo}/issues/{pull_number}/comments",
            ("pull_number",),
            paginated=True,
            permission="pull_requests",
            pages=10,
            items=1000,
        ),
        "review_comments.list": _endpoint(
            "/repos/{owner}/{repo}/pulls/{pull_number}/comments",
            ("pull_number",),
            paginated=True,
            permission="pull_requests",
            pages=10,
            items=1000,
        ),
        "branch_protection.get": _endpoint(
            "/repos/{owner}/{repo}/branches/{branch}/protection",
            ("branch",),
            permission="administration",
        ),
        "branch_rules.list": _endpoint(
            "/repos/{owner}/{repo}/rules/branches/{branch}",
            ("branch",),
            paginated=True,
            pages=10,
            items=1000,
        ),
        "repository_rulesets.list": _endpoint(
            "/repos/{owner}/{repo}/rulesets",
            (),
            query={"includes_parents": True},
            paginated=True,
            pages=10,
            items=1000,
        ),
        "repository_ruleset.get": _endpoint(
            "/repos/{owner}/{repo}/rulesets/{ruleset_id}",
            ("ruleset_id",),
            query={"includes_parents": True},
        ),
    }
)


class GitHubOperationAuthorization(GitHubRecord):
    profile: Literal["github-operation-authorization"] = (
        "github-operation-authorization"
    )
    schema_version: Literal[AUTHORIZATION_SCHEMA] = AUTHORIZATION_SCHEMA
    authorization_id: str
    repository_profile: RecordReference
    api_profile: RecordReference
    repository_id: int = Field(gt=0)
    account_id: int = Field(gt=0)
    stage: Literal["21A"] = "21A"
    operation_mode: Literal["read_only"] = "read_only"
    operation_key: OperationKey
    path_parameters: dict[str, Scalar]
    query_parameters: dict[str, Scalar]
    purpose: str = Field(min_length=1, max_length=512)
    authorized_principal: str = Field(min_length=1, max_length=256)
    issued_at: str
    expires_at: str
    maximum_logical_operations: Literal[1] = 1
    maximum_network_requests: int = Field(ge=2, le=11)
    authority_effect: Literal["github_read_only"] = "github_read_only"  # type: ignore[assignment]

    @field_validator("authorization_id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        return _validate_uuid7(value)

    @field_validator("issued_at", "expires_at")
    @classmethod
    def valid_time(cls, value: str) -> str:
        return _validate_timestamp(value)

    @field_validator("purpose")
    @classmethod
    def valid_purpose(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 512 or any(ord(char) < 32 for char in value):
            raise ValueError("purpose must be bounded UTF-8 without controls")
        return value

    @model_validator(mode="after")
    def valid_authorization_bounds(self) -> "GitHubOperationAuthorization":
        lifetime = (
            _parse_timestamp(self.expires_at) - _parse_timestamp(self.issued_at)
        ).total_seconds()
        if not 1 <= lifetime <= 900:
            raise ValueError("authorization lifetime must be 1..900 seconds")
        spec = ENDPOINTS[self.operation_key]
        expected_requests = spec.maximum_pages + 1
        if self.maximum_network_requests != expected_requests:
            raise ValueError(
                "maximum_network_requests must equal page ceiling plus one"
            )
        _validate_parameters(
            self.operation_key, self.path_parameters, self.query_parameters
        )
        return self


def _validate_parameters(
    operation_key: str, path: Mapping[str, Scalar], query: Mapping[str, Scalar]
) -> None:
    spec = ENDPOINTS[operation_key]
    if set(path) != set(spec.path_parameters):
        raise ValueError("path parameters do not match the closed endpoint")
    expected_query = dict(spec.fixed_query)
    if spec.paginated:
        expected_query.update({"per_page": 100, "page": 1})
    if dict(query) != expected_query:
        raise ValueError("query parameters do not match the closed endpoint")
    for key, value in path.items():
        if key in {"pull_number", "ruleset_id"}:
            if type(value) is not int or value <= 0:
                raise ValueError(f"{key} must be a positive integer")
        elif type(value) is not str or not value:
            raise ValueError(f"{key} must be a non-empty string")
        elif any(ord(char) < 32 for char in value) or any(
            char in value for char in "%\\?#"
        ):
            raise ValueError(f"{key} contains a prohibited character")
    if operation_key == "ref.get":
        ref = path["ref"]
        if not isinstance(ref, str) or not ref.startswith("refs/heads/"):
            raise ValueError("ref.get requires a full refs/heads reference")


def compute_attempt_id(
    *,
    authorization_hash: Hash,
    repository_profile_hash: Hash,
    api_profile_hash: Hash,
    operation_key: str,
    path_parameters: Mapping[str, Scalar],
    query_parameters: Mapping[str, Scalar],
    maximum_response_body_bytes_per_page: int,
    maximum_total_response_body_bytes: int,
    maximum_pages: int,
    maximum_items: int,
    operation_timeout_seconds: int,
    maximum_retry_transmissions_per_operation: int,
    maximum_network_requests: int,
) -> str:
    values = {
        "schema_version": ATTEMPT_PREIMAGE_SCHEMA,
        "authorization_hash": authorization_hash,
        "repository_profile_hash": repository_profile_hash,
        "api_profile_hash": api_profile_hash,
        "operation_key": operation_key,
        "path_parameters": dict(path_parameters),
        "query_parameters": dict(query_parameters),
        "maximum_response_body_bytes_per_page": maximum_response_body_bytes_per_page,
        "maximum_total_response_body_bytes": maximum_total_response_body_bytes,
        "maximum_pages": maximum_pages,
        "maximum_items": maximum_items,
        "operation_timeout_seconds": operation_timeout_seconds,
        "maximum_retry_transmissions_per_operation": maximum_retry_transmissions_per_operation,
        "maximum_network_requests": maximum_network_requests,
    }
    for name in ("authorization_hash", "repository_profile_hash", "api_profile_hash"):
        if re.fullmatch(HASH_PATTERN, values[name]) is None:
            raise ValidationError(f"{name} is not a canonical content hash")
    if operation_key not in ENDPOINTS:
        raise ValidationError("operation key is not in the closed endpoint table")
    _validate_parameters(operation_key, path_parameters, query_parameters)
    for name in (
        "maximum_response_body_bytes_per_page",
        "maximum_total_response_body_bytes",
        "maximum_pages",
        "maximum_items",
        "operation_timeout_seconds",
        "maximum_retry_transmissions_per_operation",
        "maximum_network_requests",
    ):
        if type(values[name]) is not int or values[name] < 0:
            raise ValidationError(f"{name} must be an unsigned JSON integer")
    return (
        "attempt:sha256:"
        + hashlib.sha256(ATTEMPT_DOMAIN + _canonical_json_bytes(values)).hexdigest()
    )


class GitHubOperationIntent(GitHubRecord):
    profile: Literal["github-operation-intent"] = "github-operation-intent"
    schema_version: Literal[INTENT_SCHEMA] = INTENT_SCHEMA
    intent_id: str
    authorization: RecordReference
    repository_profile: RecordReference
    api_profile: RecordReference
    repository_id: int = Field(gt=0)
    account_id: int = Field(gt=0)
    app_id: int = Field(gt=0)
    installation_id: int = Field(gt=0)
    stage: Literal["21A"] = "21A"
    http_method: Literal["GET"] = "GET"
    operation_key: OperationKey
    path_parameters: dict[str, Scalar]
    query_parameters: dict[str, Scalar]
    request_body_hash: None = None
    request_body_bytes: Literal[0] = 0
    maximum_response_body_bytes_per_page: int = Field(gt=0)
    maximum_total_response_body_bytes: int = Field(gt=0)
    maximum_pages: int = Field(gt=0)
    maximum_items: int = Field(gt=0)
    operation_timeout_seconds: int = Field(gt=0)
    maximum_retry_transmissions_per_operation: Literal[1] = 1
    maximum_network_requests: int = Field(gt=0)
    attempt_id: str = Field(pattern=ATTEMPT_PATTERN)
    not_after: str
    maximum_credential_resolutions: Literal[1] = 1

    @field_validator("intent_id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        return _validate_uuid7(value)

    @field_validator("not_after")
    @classmethod
    def valid_not_after(cls, value: str) -> str:
        return _validate_timestamp(value)

    @model_validator(mode="after")
    def attempt_is_current(self) -> "GitHubOperationIntent":
        _validate_parameters(
            self.operation_key, self.path_parameters, self.query_parameters
        )
        expected = compute_attempt_id(
            authorization_hash=self.authorization.content_hash,
            repository_profile_hash=self.repository_profile.content_hash,
            api_profile_hash=self.api_profile.content_hash,
            operation_key=self.operation_key,
            path_parameters=self.path_parameters,
            query_parameters=self.query_parameters,
            maximum_response_body_bytes_per_page=self.maximum_response_body_bytes_per_page,
            maximum_total_response_body_bytes=self.maximum_total_response_body_bytes,
            maximum_pages=self.maximum_pages,
            maximum_items=self.maximum_items,
            operation_timeout_seconds=self.operation_timeout_seconds,
            maximum_retry_transmissions_per_operation=self.maximum_retry_transmissions_per_operation,
            maximum_network_requests=self.maximum_network_requests,
        )
        if self.attempt_id != expected:
            raise ValueError("attempt_id does not match its canonical preimage")
        return self


class GitHubOperationAttemptClaim(GitHubRecord):
    profile: Literal["github-operation-attempt-claim"] = (
        "github-operation-attempt-claim"
    )
    schema_version: Literal[ATTEMPT_CLAIM_SCHEMA] = ATTEMPT_CLAIM_SCHEMA
    attempt_id: str = Field(pattern=ATTEMPT_PATTERN)
    authorization: RecordReference
    intent: RecordReference
    repository_profile: RecordReference
    api_profile: RecordReference
    repository_id: int = Field(gt=0)
    account_id: int = Field(gt=0)
    app_id: int = Field(gt=0)
    installation_id: int = Field(gt=0)
    operation_key: OperationKey
    claim_time: str
    intent_expiry: str
    state: Literal["claimed"] = "claimed"

    @field_validator("claim_time", "intent_expiry")
    @classmethod
    def valid_time(cls, value: str) -> str:
        return _validate_timestamp(value)


def attempt_claim_path(directory: Path, attempt_id: str) -> Path:
    if re.fullmatch(ATTEMPT_PATTERN, attempt_id) is None:
        raise ValidationError("attempt_id is not canonical")
    return Path(directory) / f"attempt-{attempt_id.rsplit(':', 1)[1]}.json"


def _record_bytes(record: HashedRecord) -> bytes:
    return (
        json.dumps(record.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sync_file(handle: Any) -> None:
    handle.flush()
    if os.name == "nt":
        import ctypes
        import msvcrt

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        if not kernel32.FlushFileBuffers(msvcrt.get_osfhandle(handle.fileno())):
            raise OSError(ctypes.get_last_error(), "FlushFileBuffers failed")
    elif sys.platform == "darwin":
        import fcntl

        command = getattr(fcntl, "F_FULLFSYNC", 51)
        fcntl.fcntl(handle.fileno(), command)
    else:
        os.fsync(handle.fileno())


def _sync_parent(directory: Path) -> None:
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(directory, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_durable_record(
    path: Path, record: HashedRecord, *, reject_existing: bool = False
) -> tuple[Path, bool]:
    """Exclusively persist and verify one immutable record.

    Attempt claims pass ``reject_existing=True`` so even identical content
    remains a replay refusal.
    """

    path = Path(path)
    payload = _record_bytes(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            _sync_file(handle)
        _sync_parent(path.parent)
    except FileExistsError as exc:
        if reject_existing:
            existing = path.read_bytes()
            reason = (
                "ATTEMPT_ALREADY_CLAIMED"
                if existing == payload
                else "ATTEMPT_CLAIM_CONFLICT"
            )
            raise IntegrityError(reason) from exc
        if path.read_bytes() != payload:
            raise IntegrityError(
                f"refusing to overwrite conflicting GitHub record {path}"
            ) from exc
        return path, False
    except Exception:
        # A partial final-path record is retained for forensic reconciliation.
        raise
    if path.read_bytes() != payload:
        raise IntegrityError("durable GitHub record readback mismatch")
    return path, True


def write_attempt_claim(directory: Path, claim: GitHubOperationAttemptClaim) -> Path:
    path = attempt_claim_path(directory, claim.attempt_id)
    return write_durable_record(path, claim, reject_existing=True)[0]


_ADMISSION_SENTINEL = object()


class DurableLeaseEvidenceAdmission:
    """Private process-local proof that durable evidence admission succeeded."""

    __slots__ = (
        "evidence_path",
        "evidence_hash",
        "attempt_id",
        "attempt_claim_hash",
        "_identity",
        "_used",
    )

    def __init__(
        self,
        sentinel: object,
        *,
        evidence_path: Path,
        evidence_hash: str,
        attempt_id: str,
        attempt_claim_hash: str,
    ) -> None:
        if sentinel is not _ADMISSION_SENTINEL:
            raise TypeError(
                "DurableLeaseEvidenceAdmission is not publicly constructible"
            )
        self.evidence_path = Path(evidence_path)
        self.evidence_hash = evidence_hash
        self.attempt_id = attempt_id
        self.attempt_claim_hash = attempt_claim_hash
        self._identity = object()
        self._used = False

    def __reduce__(self) -> Any:
        raise TypeError("DurableLeaseEvidenceAdmission is not serializable")

    def consume(
        self,
        *,
        evidence_path: Path,
        evidence_hash: str,
        attempt_id: str,
        attempt_claim_hash: str,
    ) -> None:
        if self._used:
            raise IntegrityError("LEASE_ADMISSION_INVALID")
        if (Path(evidence_path), evidence_hash, attempt_id, attempt_claim_hash) != (
            self.evidence_path,
            self.evidence_hash,
            self.attempt_id,
            self.attempt_claim_hash,
        ):
            raise IntegrityError("LEASE_ADMISSION_INVALID")
        self._used = True


def create_durable_lease_admission(
    *,
    evidence_path: Path,
    evidence: HashedRecord,
    attempt_id: str,
    attempt_claim_hash: str,
) -> DurableLeaseEvidenceAdmission:
    written_path, _ = write_durable_record(evidence_path, evidence)
    return DurableLeaseEvidenceAdmission(
        _ADMISSION_SENTINEL,
        evidence_path=written_path,
        evidence_hash=evidence.content_hash,
        attempt_id=attempt_id,
        attempt_claim_hash=attempt_claim_hash,
    )


RESOLUTION_REQUEST_SCHEMA = "github-credential-resolution-request/0.1.0"
LEASE_RECEIPT_SCHEMA = "github-credential-lease-receipt/0.1.0"
LEASE_CLAIMS_SCHEMA = "github-credential-lease-claims/0.1.0"
LEASE_EVIDENCE_SCHEMA = "github-credential-lease-evidence/0.1.0"
RECEIPT_SIGNATURE_DOMAIN = b"CONCLAVE-GITHUB-LEASE-RECEIPT-V1\x00"
CLAIMS_SIGNATURE_DOMAIN = b"CONCLAVE-GITHUB-LEASE-CLAIMS-V1\x00"
AUTHENTICATION_VERSION = "conclave-github-lease-ed25519-v1"


class GitHubFoundationFailure(ValidationError):
    """Safe failure carrying only a closed Increment 21A reason code."""

    def __init__(self, reason_code: str):
        self.reason_code = reason_code
        super().__init__(reason_code)


class CredentialResolutionRequest(ClosedModel):
    schema_version: Literal[RESOLUTION_REQUEST_SCHEMA] = RESOLUTION_REQUEST_SCHEMA
    provider_selector: str = Field(
        min_length=1, max_length=128, pattern=SAFE_ID_PATTERN
    )
    provider_id: str = Field(min_length=1, max_length=64, pattern=SAFE_ID_PATTERN)
    provider_versions: tuple[str, ...] = Field(min_length=1, max_length=8)
    repository_profile_hash: Hash = Field(pattern=HASH_PATTERN)
    api_profile_hash: Hash = Field(pattern=HASH_PATTERN)
    provider_key_hash: Hash = Field(pattern=HASH_PATTERN)
    repository_id: int = Field(gt=0)
    account_id: int = Field(gt=0)
    app_id: int = Field(gt=0)
    installation_id: int = Field(gt=0)
    permission_envelope: PermissionEnvelope
    api_version: Literal["2026-03-10"] = "2026-03-10"
    authorization_hash: Hash = Field(pattern=HASH_PATTERN)
    intent_hash: Hash = Field(pattern=HASH_PATTERN)
    intent_expiry: str
    resolution_nonce_hash: Hash = Field(pattern=HASH_PATTERN)

    @field_validator("provider_versions")
    @classmethod
    def ordered_versions(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _sorted_unique(values)

    @field_validator("intent_expiry")
    @classmethod
    def valid_expiry(cls, value: str) -> str:
        return _validate_timestamp(value)


class LeasePublicFields(ClosedModel):
    provider_id: str = Field(min_length=1, max_length=64, pattern=SAFE_ID_PATTERN)
    provider_version: str = Field(min_length=1, max_length=128, pattern=SAFE_ID_PATTERN)
    key_id: str = Field(min_length=1, max_length=128, pattern=SAFE_ID_PATTERN)
    lease_id: str = Field(min_length=1, max_length=128, pattern=SAFE_ID_PATTERN)
    credential_class: Literal["github_app_installation_access_token"] = (
        "github_app_installation_access_token"
    )
    app_id: int = Field(gt=0)
    installation_id: int = Field(gt=0)
    account_id: int = Field(gt=0)
    repository_ids: tuple[int, ...] = Field(min_length=1, max_length=1)
    repository_selection: Literal["selected"] = "selected"
    permissions: PermissionEnvelope
    minted_at: str
    expires_at: str
    api_version: Literal["2026-03-10"] = "2026-03-10"
    repository_profile_hash: Hash = Field(pattern=HASH_PATTERN)
    api_profile_hash: Hash = Field(pattern=HASH_PATTERN)
    authorization_hash: Hash = Field(pattern=HASH_PATTERN)
    intent_hash: Hash = Field(pattern=HASH_PATTERN)
    resolution_nonce_hash: Hash = Field(pattern=HASH_PATTERN)
    provider_receipt_validation_outcome: Literal["pass"] = "pass"
    provider_receipt_validation_at: str
    provider_authentication_scheme: Literal["Ed25519"] = "Ed25519"
    provider_authentication_version: Literal[AUTHENTICATION_VERSION] = (
        AUTHENTICATION_VERSION
    )
    provider_authentication_key_id: str = Field(
        min_length=1, max_length=128, pattern=SAFE_ID_PATTERN
    )

    @field_validator("minted_at", "expires_at", "provider_receipt_validation_at")
    @classmethod
    def valid_time(cls, value: str) -> str:
        return _validate_timestamp(value)

    @model_validator(mode="after")
    def valid_provider_sequence(self) -> "LeasePublicFields":
        minted = _parse_timestamp(self.minted_at)
        expires = _parse_timestamp(self.expires_at)
        receipt_validated = _parse_timestamp(self.provider_receipt_validation_at)
        if not minted <= receipt_validated < expires:
            raise ValueError("provider receipt times are out of order")
        if expires - minted > timedelta(minutes=60):
            raise ValueError("credential lifetime exceeds 60 minutes")
        if self.provider_authentication_key_id != self.key_id:
            raise ValueError("provider authentication key ID mismatch")
        if len(set(self.repository_ids)) != 1:
            raise ValueError("receipt must bind exactly one repository")
        return self


class CredentialLeaseReceipt(LeasePublicFields):
    schema_version: Literal[LEASE_RECEIPT_SCHEMA] = LEASE_RECEIPT_SCHEMA
    token_instance_tag: str = Field(
        min_length=16, max_length=256, pattern=r"^[A-Za-z0-9._~-]+$"
    )
    signature: str = Field(min_length=86, max_length=86)

    @field_validator("signature")
    @classmethod
    def canonical_signature(cls, value: str) -> str:
        _decode_signature(value)
        return value


class CredentialLeaseClaims(LeasePublicFields):
    schema_version: Literal[LEASE_CLAIMS_SCHEMA] = LEASE_CLAIMS_SCHEMA
    provider_pair_validation_outcome: Literal["pass"] = "pass"
    provider_pair_validation_at: str
    sanitized_transient_receipt_hash: Hash = Field(pattern=HASH_PATTERN)
    signature: str = Field(min_length=86, max_length=86)

    @field_validator("provider_pair_validation_at")
    @classmethod
    def valid_pair_time(cls, value: str) -> str:
        return _validate_timestamp(value)

    @field_validator("signature")
    @classmethod
    def canonical_signature(cls, value: str) -> str:
        _decode_signature(value)
        return value

    @model_validator(mode="after")
    def pair_follows_receipt(self) -> "CredentialLeaseClaims":
        if _parse_timestamp(self.provider_pair_validation_at) < _parse_timestamp(
            self.provider_receipt_validation_at
        ):
            raise ValueError("provider pair validation predates receipt validation")
        if _parse_timestamp(self.provider_pair_validation_at) >= _parse_timestamp(
            self.expires_at
        ):
            raise ValueError("provider pair validation is outside credential lifetime")
        return self


class CredentialLeaseEvidence(GitHubRecord):
    profile: Literal["github-credential-lease-evidence"] = (
        "github-credential-lease-evidence"
    )
    schema_version: Literal[LEASE_EVIDENCE_SCHEMA] = LEASE_EVIDENCE_SCHEMA
    provider_claims: CredentialLeaseClaims
    provider_claims_hash: Hash = Field(pattern=HASH_PATTERN)
    receipt_projection: LeasePublicFields
    receipt_signature_validation: Literal["pass"] = "pass"
    receipt_signature_validated_at: str
    pair_validation_completed_at: str
    claims_signature_validation: Literal["pass"] = "pass"
    claims_signature_validated_at: str
    attempt_claim: RecordReference
    authorization: RecordReference
    intent: RecordReference
    resolution_nonce_hash: Hash = Field(pattern=HASH_PATTERN)
    sanitized_transient_receipt_hash: Hash = Field(pattern=HASH_PATTERN)
    logical_operation_use_limit: Literal[1] = 1
    maximum_network_requests: int = Field(gt=0)
    network_started_at_evidence_creation: Literal[False] = False
    credential_material_persisted: Literal[False] = False

    @field_validator(
        "receipt_signature_validated_at",
        "pair_validation_completed_at",
        "claims_signature_validated_at",
    )
    @classmethod
    def valid_time(cls, value: str) -> str:
        return _validate_timestamp(value)

    @model_validator(mode="after")
    def evidence_is_bound(self) -> "CredentialLeaseEvidence":
        claims_hash = sha256_bytes(
            _canonical_json_bytes(self.provider_claims.model_dump(mode="json"))
        )
        if self.provider_claims_hash != claims_hash:
            raise ValueError("provider claims hash mismatch")
        if self.receipt_projection.model_dump() != _public_projection(
            self.provider_claims
        ):
            raise ValueError("receipt and provider claims projections differ")
        if (
            self.sanitized_transient_receipt_hash
            != self.provider_claims.sanitized_transient_receipt_hash
        ):
            raise ValueError("sanitized receipt hash mismatch")
        local_times = tuple(
            map(
                _parse_timestamp,
                (
                    self.receipt_signature_validated_at,
                    self.pair_validation_completed_at,
                    self.claims_signature_validated_at,
                    self.created_at,
                ),
            )
        )
        if tuple(sorted(local_times)) != local_times:
            raise ValueError("local validation times are out of order")
        return self


def _decode_signature(value: str) -> bytes:
    if "=" in value or re.fullmatch(r"[A-Za-z0-9_-]{86}", value) is None:
        raise ValueError("signature must be canonical unpadded base64url")
    try:
        decoded = base64.urlsafe_b64decode(value + "==")
    except Exception as exc:
        raise ValueError("signature is invalid base64url") from exc
    if (
        len(decoded) != 64
        or base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii") != value
    ):
        raise ValueError("signature is not canonical 64-byte base64url")
    return decoded


def _signature_payload(model: ClosedModel, *, domain: bytes) -> bytes:
    return domain + _canonical_json_bytes(
        model.model_dump(mode="json", exclude={"signature"})
    )


def _verify_signature(
    model: CredentialLeaseReceipt | CredentialLeaseClaims,
    *,
    public_key: GitHubCredentialProviderKey,
    domain: bytes,
) -> None:
    raw_key = base64.urlsafe_b64decode(public_key.public_key + "=")
    try:
        Ed25519PublicKey.from_public_bytes(raw_key).verify(
            _decode_signature(model.signature), _signature_payload(model, domain=domain)
        )
    except (InvalidSignature, ValueError) as exc:
        raise GitHubFoundationFailure("LEASE_AUTH_INVALID") from exc


def _public_projection(value: LeasePublicFields) -> dict[str, Any]:
    source = value.model_dump(mode="python")
    return {name: source[name] for name in LeasePublicFields.model_fields}


def sanitized_receipt_hash(receipt: CredentialLeaseReceipt) -> str:
    return sha256_bytes(_canonical_json_bytes(receipt.model_dump(mode="json")))


class PairValidationCapability(Protocol):
    def validate_pair_once(self, token: memoryview) -> CredentialLeaseClaims: ...
    def close(self) -> None: ...


class GitHubCredentialLeaseProvider(Protocol):
    provider_id: str
    provider_version: str

    def resolve_once(
        self, request: CredentialResolutionRequest
    ) -> "CredentialEnvelope": ...


class CredentialEnvelope:
    """One transient token, signed receipt, and provider-owned pair validator."""

    __slots__ = ("token", "receipt", "pair_validator", "_closed")

    def __init__(
        self,
        *,
        token: bytearray,
        receipt: CredentialLeaseReceipt,
        pair_validator: PairValidationCapability,
    ):
        if type(token) is not bytearray or not token:
            raise GitHubFoundationFailure("LEASE_PARTIAL")
        self.token = token
        self.receipt = receipt
        self.pair_validator = pair_validator
        self._closed = False

    def close(self) -> None:
        if self._closed:
            return
        failure = False
        try:
            for index in range(len(self.token)):
                self.token[index] = 0
        except Exception:
            failure = True
        try:
            self.pair_validator.close()
        except Exception:
            failure = True
        self._closed = True
        if failure:
            raise GitHubFoundationFailure("CREDENTIAL_CLEANUP_FAILED")


_LEASE_SENTINEL = object()


class SealedCredentialLease:
    """Private admitted credential object; no bare-token public accessor."""

    __slots__ = (
        "_envelope",
        "evidence",
        "_admission",
        "_consumed",
        "_closed",
        "_authorization_expires_at",
        "_intent_not_after",
    )

    def __init__(
        self,
        sentinel: object,
        *,
        envelope: CredentialEnvelope,
        evidence: CredentialLeaseEvidence,
        admission: DurableLeaseEvidenceAdmission,
        authorization_expires_at: str,
        intent_not_after: str,
    ):
        if sentinel is not _LEASE_SENTINEL:
            raise TypeError("SealedCredentialLease is not publicly constructible")
        self._envelope = envelope
        self.evidence = evidence
        self._admission = admission
        self._consumed = False
        self._closed = False
        self._authorization_expires_at = authorization_expires_at
        self._intent_not_after = intent_not_after

    def __reduce__(self) -> Any:
        raise TypeError("SealedCredentialLease is not serializable")

    def _admit_transport_once(self, now: datetime) -> memoryview:
        if self._consumed or self._closed:
            raise GitHubFoundationFailure("LEASE_ADMISSION_INVALID")
        local = now.replace(tzinfo=None)
        expires = _parse_timestamp(self.evidence.provider_claims.expires_at)
        if expires - local < timedelta(seconds=90):
            raise GitHubFoundationFailure("LEASE_STALE")
        if local > _parse_timestamp(
            self._authorization_expires_at
        ) or local > _parse_timestamp(self._intent_not_after):
            raise GitHubFoundationFailure("CREDENTIAL_TIME_INVALID")
        self._admission.consume(
            evidence_path=self._admission.evidence_path,
            evidence_hash=self.evidence.content_hash,
            attempt_id=self._admission.attempt_id,
            attempt_claim_hash=self._admission.attempt_claim_hash,
        )
        self._consumed = True
        return memoryview(self._envelope.token)

    def close(self) -> None:
        if not self._closed:
            self._envelope.close()
            self._closed = True

    def __enter__(self) -> "SealedCredentialLease":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise GitHubFoundationFailure("CREDENTIAL_TIME_INVALID")
    return value.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _check_future(provider_time: str, local_time: datetime) -> None:
    if _parse_timestamp(provider_time) > local_time.replace(tzinfo=None) + timedelta(
        seconds=30
    ):
        raise GitHubFoundationFailure("CREDENTIAL_TIME_INVALID")


def _check_key_time(key: GitHubCredentialProviderKey, local_time: datetime) -> None:
    instant = local_time.replace(tzinfo=None)
    if (
        not _parse_timestamp(key.valid_from)
        <= instant
        <= _parse_timestamp(key.valid_until)
    ):
        raise GitHubFoundationFailure("LEASE_AUTH_INVALID")


def prepare_credential_lease(
    *,
    provider: GitHubCredentialLeaseProvider,
    request: CredentialResolutionRequest,
    repository_profile: GitHubRepositoryProfile,
    api_profile: GitHubApiProfile,
    provider_key: GitHubCredentialProviderKey,
    authorization: GitHubOperationAuthorization,
    intent: GitHubOperationIntent,
    attempt_claim: GitHubOperationAttemptClaim,
    attempt_claim_reference: str,
    authorization_reference: str,
    intent_reference: str,
    evidence_directory: Path,
    clock: Callable[[], datetime],
) -> SealedCredentialLease:
    """Resolve and authenticate one fixture/provider lease without network I/O."""

    if (
        repository_profile.provider_key_hash != provider_key.content_hash
        or repository_profile.expected_provider_key_id != provider_key.key_id
        or repository_profile.expected_provider_public_key_sha256
        != provider_key.public_key_sha256
        or repository_profile.expected_provider_id != provider_key.provider_id
        or provider.provider_id != repository_profile.expected_provider_id
        or provider.provider_version
        not in repository_profile.expected_provider_versions
    ):
        raise GitHubFoundationFailure("LEASE_AUTH_INVALID")
    if (
        request.repository_profile_hash != repository_profile.content_hash
        or request.api_profile_hash != api_profile.content_hash
    ):
        raise GitHubFoundationFailure("LEASE_BINDING_MISMATCH")
    if (
        request.authorization_hash != authorization.content_hash
        or request.intent_hash != intent.content_hash
    ):
        raise GitHubFoundationFailure("LEASE_BINDING_MISMATCH")
    if (
        attempt_claim.intent.content_hash != intent.content_hash
        or attempt_claim.attempt_id != intent.attempt_id
    ):
        raise GitHubFoundationFailure("LEASE_BINDING_MISMATCH")

    envelope: CredentialEnvelope | None = None
    try:
        envelope = provider.resolve_once(request)
        receipt = envelope.receipt
        expected = {
            "provider_id": request.provider_id,
            "repository_ids": (request.repository_id,),
            "account_id": request.account_id,
            "app_id": request.app_id,
            "installation_id": request.installation_id,
            "permissions": request.permission_envelope,
            "api_version": request.api_version,
            "repository_profile_hash": request.repository_profile_hash,
            "api_profile_hash": request.api_profile_hash,
            "authorization_hash": request.authorization_hash,
            "intent_hash": request.intent_hash,
            "resolution_nonce_hash": request.resolution_nonce_hash,
        }
        if any(getattr(receipt, name) != value for name, value in expected.items()):
            raise GitHubFoundationFailure("LEASE_BINDING_MISMATCH")
        if receipt.provider_version not in request.provider_versions:
            raise GitHubFoundationFailure("LEASE_BINDING_MISMATCH")
        if receipt.permissions != request.permission_envelope:
            raise GitHubFoundationFailure("LEASE_PERMISSION_MISMATCH")

        _verify_signature(
            receipt, public_key=provider_key, domain=RECEIPT_SIGNATURE_DOMAIN
        )
        receipt_local = clock()
        _check_key_time(provider_key, receipt_local)
        _check_future(receipt.minted_at, receipt_local)
        _check_future(receipt.provider_receipt_validation_at, receipt_local)
        if _parse_timestamp(receipt.minted_at) < _parse_timestamp(
            authorization.issued_at
        ):
            raise GitHubFoundationFailure("CREDENTIAL_TIME_INVALID")

        claims = envelope.pair_validator.validate_pair_once(memoryview(envelope.token))
        pair_local = clock()
        _check_future(claims.provider_pair_validation_at, pair_local)
        if sanitized_receipt_hash(receipt) != claims.sanitized_transient_receipt_hash:
            raise GitHubFoundationFailure("LEASE_BINDING_MISMATCH")
        if _public_projection(receipt) != _public_projection(claims):
            raise GitHubFoundationFailure("LEASE_BINDING_MISMATCH")

        _verify_signature(
            claims, public_key=provider_key, domain=CLAIMS_SIGNATURE_DOMAIN
        )
        claims_local = clock()
        _check_key_time(provider_key, claims_local)
        evidence_time = clock()
        expires = _parse_timestamp(receipt.expires_at)
        local_naive = evidence_time.replace(tzinfo=None)
        if expires - local_naive < timedelta(seconds=90):
            raise GitHubFoundationFailure("LEASE_STALE")
        deadlines = (
            _parse_timestamp(authorization.expires_at),
            _parse_timestamp(intent.not_after),
        )
        if any(local_naive > deadline for deadline in deadlines):
            raise GitHubFoundationFailure("CREDENTIAL_TIME_INVALID")

        claims_hash = sha256_bytes(
            _canonical_json_bytes(claims.model_dump(mode="json"))
        )
        evidence = _seal_github_record(
            CredentialLeaseEvidence,
            {
                "profile": "github-credential-lease-evidence",
                "schema_version": LEASE_EVIDENCE_SCHEMA,
                "provider_claims": claims,
                "provider_claims_hash": claims_hash,
                "receipt_projection": _public_projection(receipt),
                "receipt_signature_validation": "pass",
                "receipt_signature_validated_at": _utc_text(receipt_local),
                "pair_validation_completed_at": _utc_text(pair_local),
                "claims_signature_validation": "pass",
                "claims_signature_validated_at": _utc_text(claims_local),
                "attempt_claim": {
                    "reference": attempt_claim_reference,
                    "content_hash": attempt_claim.content_hash,
                },
                "authorization": {
                    "reference": authorization_reference,
                    "content_hash": authorization.content_hash,
                },
                "intent": {
                    "reference": intent_reference,
                    "content_hash": intent.content_hash,
                },
                "resolution_nonce_hash": request.resolution_nonce_hash,
                "sanitized_transient_receipt_hash": claims.sanitized_transient_receipt_hash,
                "logical_operation_use_limit": 1,
                "maximum_network_requests": authorization.maximum_network_requests,
                "network_started_at_evidence_creation": False,
                "credential_material_persisted": False,
                "created_at": _utc_text(evidence_time),
                "authority_effect": "none",
                "decision_effect": "none",
                "membership_effect": "none",
                "production_use_allowed": False,
            },
        )
        evidence_path = (
            Path(evidence_directory)
            / f"lease-{evidence.content_hash.removeprefix('sha256:')}.json"
        )
        admission = create_durable_lease_admission(
            evidence_path=evidence_path,
            evidence=evidence,
            attempt_id=intent.attempt_id,
            attempt_claim_hash=attempt_claim.content_hash,
        )
        return SealedCredentialLease(
            _LEASE_SENTINEL,
            envelope=envelope,
            evidence=evidence,
            admission=admission,
            authorization_expires_at=authorization.expires_at,
            intent_not_after=intent.not_after,
        )
    except Exception:
        if envelope is not None:
            try:
                envelope.close()
            except GitHubFoundationFailure as cleanup_error:
                raise cleanup_error
        raise


def _seal_github_record(record_type: type[HashedRecord], data: dict[str, Any]) -> Any:
    if "content_hash" in data:
        raise ValidationError("content_hash is computed, not supplied")
    draft = record_type.model_validate(
        {**data, "content_hash": "sha256:" + "0" * 64},
        context={"skip_content_hash": True},
    )
    body = draft.model_dump(mode="json", exclude={"content_hash"})
    return record_type.model_validate(
        {**data, "content_hash": sha256_bytes(_canonical_json_bytes(body))}
    )


@dataclass(frozen=True)
class PreparedGitHubRequest:
    operation_key: str
    method: Literal["GET"]
    target: str
    page: int
    headers: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class GitHubTransportResponse:
    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes

    def header(self, name: str) -> str | None:
        lowered = name.lower()
        values = [value for key, value in self.headers if key.lower() == lowered]
        if not values:
            return None
        if len(values) != 1:
            raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
        return values[0]


class GitHubTransportFailure(GitHubFoundationFailure):
    def __init__(self, reason_code: str, *, before_headers: bool):
        super().__init__(reason_code)
        self.before_headers = before_headers


class GitHubOperationExecutionFailure(GitHubFoundationFailure):
    """Safe execution failure retaining only bounded transmission metadata."""

    def __init__(
        self,
        reason_code: str,
        *,
        transmitted: bool,
        responses: tuple[GitHubTransportResponse, ...],
    ):
        super().__init__(reason_code)
        self.transmitted = transmitted
        self.responses = responses


RETRYABLE_TRANSPORT_FAILURES = frozenset(
    {
        "TRANSPORT_DNS_FAILED",
        "TRANSPORT_CONNECT_FAILED",
        "TRANSPORT_TLS_FAILED",
        "TRANSPORT_CONNECTION_LOST",
    }
)


def _encode_route_value(value: str) -> str:
    if (
        not value
        or any(ord(char) < 32 for char in value)
        or any(char in value for char in "%\\?#")
        or "//" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise GitHubFoundationFailure("PARAMETER_INVALID")
    encoded = quote(value, safe="-._~")
    if unquote(encoded) != value:
        raise GitHubFoundationFailure("PARAMETER_INVALID")
    return encoded


def build_github_request(
    *,
    repository_profile: GitHubRepositoryProfile,
    api_profile: GitHubApiProfile,
    intent: GitHubOperationIntent,
    page: int = 1,
) -> PreparedGitHubRequest:
    """Build one request from the closed endpoint table without a credential."""

    if (
        intent.repository_profile.content_hash != repository_profile.content_hash
        or intent.api_profile.content_hash != api_profile.content_hash
    ):
        raise GitHubFoundationFailure("LEASE_BINDING_MISMATCH")
    spec = ENDPOINTS[intent.operation_key]
    if page < 1 or page > spec.maximum_pages or (not spec.paginated and page != 1):
        raise GitHubFoundationFailure("PAGINATION_INVALID")
    if (
        intent.maximum_pages != spec.maximum_pages
        or intent.maximum_items != spec.maximum_items
    ):
        raise GitHubFoundationFailure("INTENT_CONFLICT")

    values: dict[str, str] = {
        "owner": _encode_route_value(repository_profile.owner),
        "repo": _encode_route_value(repository_profile.repository),
    }
    for name in spec.path_parameters:
        raw = intent.path_parameters[name]
        if name in {"pull_number", "ruleset_id"}:
            if type(raw) is not int or raw <= 0:
                raise GitHubFoundationFailure("PARAMETER_INVALID")
            values[name] = str(raw)
            continue
        if not isinstance(raw, str):
            raise GitHubFoundationFailure("PARAMETER_INVALID")
        if name == "commit_sha":
            length = 40 if repository_profile.git_object_format == "sha1" else 64
            if re.fullmatch(rf"[0-9a-f]{{{length}}}", raw) is None:
                raise GitHubFoundationFailure("PARAMETER_INVALID")
        elif name == "ref":
            if raw not in repository_profile.allowed_base_refs:
                raise GitHubFoundationFailure("PARAMETER_INVALID")
            raw = raw.removeprefix("refs/")
        elif name == "branch":
            if f"refs/heads/{raw}" not in repository_profile.allowed_base_refs:
                raise GitHubFoundationFailure("PARAMETER_INVALID")
        values[name] = _encode_route_value(raw)

    target = spec.path_template
    for name, value in values.items():
        target = target.replace("{" + name + "}", value)
    if "{" in target or not target.startswith("/repos/") or "://" in target:
        raise GitHubFoundationFailure("ENDPOINT_NOT_ALLOWED")

    query: list[tuple[str, str]] = []
    for name, value in spec.fixed_query.items():
        query.append((name, "true" if value is True else str(value)))
    if spec.paginated:
        query.extend((("per_page", "100"), ("page", str(page))))
    if query:
        target += "?" + "&".join(f"{name}={value}" for name, value in query)
    if len(target.encode("ascii")) > api_profile.maximum_request_header_bytes:
        raise GitHubFoundationFailure("PARAMETER_INVALID")
    headers = (
        ("Accept", api_profile.accept),
        ("X-GitHub-Api-Version", api_profile.api_version),
        ("User-Agent", api_profile.user_agent),
    )
    return PreparedGitHubRequest(intent.operation_key, "GET", target, page, headers)


class GitHubTransport(Protocol):
    """Credential-independent transport boundary for one prepared request."""

    def send(
        self, request: PreparedGitHubRequest, token: memoryview
    ) -> GitHubTransportResponse: ...


def _has_next_link(response: GitHubTransportResponse) -> bool:
    link = response.header("Link")
    if link is None:
        return False
    if (
        any(ord(char) < 32 and char != "\t" for char in link)
        or "\r" in link
        or "\n" in link
    ):
        raise GitHubFoundationFailure("PAGINATION_INVALID")
    return any(part.strip().endswith('rel="next"') for part in link.split(","))


def run_github_transport(
    *,
    lease: SealedCredentialLease,
    transport: GitHubTransport,
    repository_profile: GitHubRepositoryProfile,
    api_profile: GitHubApiProfile,
    intent: GitHubOperationIntent,
    clock: Callable[[], datetime],
    monotonic: Callable[[], float],
    sleeper: Callable[[float], None] = lambda _: None,
) -> tuple[GitHubTransportResponse, ...]:
    """Exercise one admitted logical operation through an injected transport."""

    responses: list[GitHubTransportResponse] = []
    token: memoryview | None = None
    transmissions = 0
    retry_used = False
    total_body = 0
    operation_started = monotonic()
    try:
        token = lease._admit_transport_once(clock())
        page = 1
        while True:
            now = clock()
            local = now.replace(tzinfo=None)
            if monotonic() - operation_started > api_profile.operation_timeout_seconds:
                raise GitHubTransportFailure("TRANSPORT_TIMEOUT", before_headers=True)
            if local >= _parse_timestamp(lease.evidence.provider_claims.expires_at):
                raise GitHubFoundationFailure("LEASE_STALE")
            if local > _parse_timestamp(
                lease._authorization_expires_at
            ) or local > _parse_timestamp(lease._intent_not_after):
                raise GitHubFoundationFailure("CREDENTIAL_TIME_INVALID")
            request = build_github_request(
                repository_profile=repository_profile,
                api_profile=api_profile,
                intent=intent,
                page=page,
            )
            try:
                transmissions += 1
                if transmissions > lease.evidence.maximum_network_requests:
                    raise GitHubFoundationFailure("INTENT_CONFLICT")
                response = transport.send(request, token)
            except GitHubTransportFailure as exc:
                if (
                    retry_used
                    or not exc.before_headers
                    or exc.reason_code not in RETRYABLE_TRANSPORT_FAILURES
                    or page != 1
                ):
                    raise
                retry_used = True
                sleeper(0.250)
                continue
            if len(response.body) > api_profile.maximum_response_body_bytes_per_page:
                raise GitHubFoundationFailure("RESPONSE_BODY_TOO_LARGE")
            total_body += len(response.body)
            if total_body > api_profile.maximum_total_response_body_bytes:
                raise GitHubFoundationFailure("RESPONSE_BODY_TOO_LARGE")
            responses.append(response)
            if not 200 <= response.status < 300 or not _has_next_link(response):
                break
            if (
                not ENDPOINTS[intent.operation_key].paginated
                or page >= intent.maximum_pages
            ):
                raise GitHubFoundationFailure("PAGINATION_LIMIT_REACHED")
            page += 1
        return tuple(responses)
    except GitHubFoundationFailure as exc:
        raise GitHubOperationExecutionFailure(
            exc.reason_code,
            transmitted=transmissions > 0,
            responses=tuple(responses),
        ) from exc
    finally:
        if token is not None:
            token.release()
        lease.close()


_HTTPS_SENTINEL = object()


class HTTPSGitHubTransport:
    """Fixed-origin production transport; construction is gated by the profile."""

    __slots__ = ("_api_profile",)

    def __init__(self, sentinel: object, api_profile: GitHubApiProfile):
        if sentinel is not _HTTPS_SENTINEL:
            raise TypeError("HTTPSGitHubTransport is not publicly constructible")
        self._api_profile = api_profile

    def send(
        self, request: PreparedGitHubRequest, token: memoryview
    ) -> GitHubTransportResponse:
        api_profile = self._api_profile
        try:
            token_text = bytes(token).decode("ascii")
        except UnicodeDecodeError as exc:
            raise GitHubFoundationFailure("LEASE_AUTH_INVALID") from exc
        if not token_text or any(char in token_text for char in "\r\n"):
            raise GitHubFoundationFailure("LEASE_AUTH_INVALID")
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        connection = http.client.HTTPSConnection(
            "api.github.com",
            443,
            timeout=api_profile.connect_timeout_seconds,
            context=context,
        )
        try:
            headers = dict(request.headers)
            headers["Authorization"] = "Bearer " + token_text
            connection.request("GET", request.target, headers=headers)
            response = connection.getresponse()
            if connection.sock is not None:
                connection.sock.settimeout(api_profile.read_timeout_seconds)
            header_pairs = tuple(response.getheaders())
            header_size = sum(
                len(name.encode("latin-1")) + len(value.encode("latin-1")) + 4
                for name, value in header_pairs
            )
            if header_size > api_profile.maximum_response_header_bytes:
                raise GitHubFoundationFailure("RESPONSE_HEADERS_TOO_LARGE")
            content_encoding = next(
                (
                    value
                    for name, value in header_pairs
                    if name.lower() == "content-encoding"
                ),
                None,
            )
            if content_encoding not in {None, "identity"}:
                raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
            chunks: list[bytes] = []
            size = 0
            while True:
                chunk = response.read(
                    min(
                        65_536,
                        api_profile.maximum_response_body_bytes_per_page - size + 1,
                    )
                )
                if not chunk:
                    break
                size += len(chunk)
                if size > api_profile.maximum_response_body_bytes_per_page:
                    raise GitHubFoundationFailure("RESPONSE_BODY_TOO_LARGE")
                chunks.append(chunk)
            return GitHubTransportResponse(
                response.status, header_pairs, b"".join(chunks)
            )
        except socket.gaierror as exc:
            raise GitHubTransportFailure(
                "TRANSPORT_DNS_FAILED", before_headers=True
            ) from exc
        except ssl.SSLError as exc:
            raise GitHubTransportFailure(
                "TRANSPORT_TLS_FAILED", before_headers=True
            ) from exc
        except (ConnectionError, OSError) as exc:
            raise GitHubTransportFailure(
                "TRANSPORT_CONNECTION_LOST", before_headers=True
            ) from exc
        finally:
            connection.close()


def create_production_https_transport(
    repository_profile: GitHubRepositoryProfile,
    api_profile: GitHubApiProfile | None = None,
) -> HTTPSGitHubTransport:
    if not repository_profile.live_use_allowed:
        raise GitHubFoundationFailure("ENDPOINT_NOT_ALLOWED")
    if api_profile is None:
        raise GitHubFoundationFailure("PROFILE_INVALID")
    return HTTPSGitHubTransport(_HTTPS_SENTINEL, api_profile)


OBSERVATION_SCHEMA = "github-observation/0.1.0"
MAX_JSON_DEPTH = 16
MAX_JSON_NODES = 10_000
MAX_OBJECT_KEYS = 256
MAX_ID = 2**63 - 1
REASON_CODES = frozenset(
    {
        "AUTHORIZATION_INVALID",
        "AUTHORIZATION_EXPIRED",
        "PROFILE_INVALID",
        "ENDPOINT_NOT_ALLOWED",
        "PARAMETER_INVALID",
        "INTENT_CONFLICT",
        "INTENT_REPLAYED",
        "ATTEMPT_ALREADY_CLAIMED",
        "ATTEMPT_CLAIM_CONFLICT",
        "ATTEMPT_CLAIM_STORE_FAILED",
        "LEASE_MISSING",
        "LEASE_PARTIAL",
        "LEASE_AUTH_INVALID",
        "CREDENTIAL_TIME_INVALID",
        "LEASE_STALE",
        "LEASE_BINDING_MISMATCH",
        "LEASE_PERMISSION_MISMATCH",
        "LEASE_TOKEN_SUBSTITUTION",
        "LEASE_EVIDENCE_STORE_FAILED",
        "LEASE_ADMISSION_INVALID",
        "CREDENTIAL_CLEANUP_FAILED",
        "REPOSITORY_IDENTITY_MISMATCH",
        "TRANSPORT_DNS_FAILED",
        "TRANSPORT_CONNECT_FAILED",
        "TRANSPORT_TLS_FAILED",
        "TRANSPORT_TIMEOUT",
        "TRANSPORT_CONNECTION_LOST",
        "REDIRECT_REFUSED",
        "PROXY_REFUSED",
        "RESPONSE_HEADERS_TOO_LARGE",
        "RESPONSE_BODY_TOO_LARGE",
        "HTTP_RESPONSE_REJECTED",
        "RATE_LIMITED",
        "RESPONSE_JSON_INVALID",
        "RESPONSE_PROJECTION_INVALID",
        "UNKNOWN_SECURITY_STATE",
        "PAGINATION_INVALID",
        "PAGINATION_LIMIT_REACHED",
        "ITEM_LIMIT_REACHED",
        "OBSERVATION_STORE_FAILED",
    }
)

ENUMS: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "repository_visibility": frozenset({"public", "private", "internal"}),
        "actor_type": frozenset({"User", "Bot", "Organization", "Mannequin"}),
        "pull_state": frozenset({"open", "closed"}),
        "mergeable_state": frozenset(
            {
                "clean",
                "dirty",
                "blocked",
                "behind",
                "unstable",
                "draft",
                "has_hooks",
                "unknown",
            }
        ),
        "check_status": frozenset(
            {"queued", "in_progress", "completed", "waiting", "requested", "pending"}
        ),
        "check_conclusion": frozenset(
            {
                "action_required",
                "cancelled",
                "failure",
                "neutral",
                "success",
                "skipped",
                "stale",
                "startup_failure",
                "timed_out",
            }
        ),
        "commit_status_state": frozenset({"error", "failure", "pending", "success"}),
        "review_state": frozenset(
            {"APPROVED", "CHANGES_REQUESTED", "COMMENTED", "DISMISSED", "PENDING"}
        ),
        "verification_reason": frozenset(
            {
                "valid",
                "invalid",
                "malformed_signature",
                "unknown_key",
                "bad_email",
                "unverified_email",
                "no_user",
                "unsigned",
                "gpgverify_unavailable",
                "gpgverify_error",
                "not_signing_key",
                "expired_key",
                "ocsp_pending",
                "ocsp_error",
                "revoked_key",
                "not_verified",
            }
        ),
        "ruleset_source_type": frozenset({"Repository", "Organization", "Enterprise"}),
        "ruleset_target": frozenset({"branch", "tag", "push"}),
        "ruleset_enforcement": frozenset({"disabled", "active", "evaluate", "enabled"}),
        "bypass_actor_type": frozenset(
            {
                "Integration",
                "RepositoryRole",
                "Team",
                "User",
                "OrganizationAdmin",
                "DeployKey",
            }
        ),
        "bypass_mode": frozenset({"always", "pull_request", "exempt"}),
        "rule_type": frozenset(
            {
                "authorization",
                "branch_name_pattern",
                "code_scanning",
                "commit_author_email_pattern",
                "commit_message_pattern",
                "committer_email_pattern",
                "copilot_code_review",
                "creation",
                "deletion",
                "file_extension_restriction",
                "file_path_restriction",
                "license_compliance_scanning",
                "max_file_path_length",
                "max_file_size",
                "merge_queue",
                "non_fast_forward",
                "pull_request",
                "required_deployments",
                "required_linear_history",
                "required_signatures",
                "required_status_checks",
                "tag_name_pattern",
                "update",
                "workflows",
            }
        ),
    }
)


def parse_bounded_json(body: bytes, *, maximum_bytes: int) -> Any:
    if len(body) > maximum_bytes:
        raise GitHubFoundationFailure("RESPONSE_BODY_TOO_LARGE")
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GitHubFoundationFailure("RESPONSE_JSON_INVALID") from exc

    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(
            text,
            object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ValueError("non-finite number")
            ),
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise GitHubFoundationFailure("RESPONSE_JSON_INVALID") from exc

    nodes = 0

    def walk(item: Any, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
            raise GitHubFoundationFailure("RESPONSE_JSON_INVALID")
        if isinstance(item, dict):
            if len(item) > MAX_OBJECT_KEYS:
                raise GitHubFoundationFailure("RESPONSE_JSON_INVALID")
            for key, child in item.items():
                if not isinstance(key, str):
                    raise GitHubFoundationFailure("RESPONSE_JSON_INVALID")
                walk(child, depth + 1)
        elif isinstance(item, list):
            for child in item:
                walk(child, depth + 1)
        elif item is not None and type(item) not in {str, int, float, bool}:
            raise GitHubFoundationFailure("RESPONSE_JSON_INVALID")

    walk(value, 1)
    return value


def _object(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
    return value


def _array(value: Any) -> list[Any]:
    if type(value) is not list:
        raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
    return value


def _required(value: Mapping[str, Any], name: str) -> Any:
    if name not in value or value[name] is None:
        raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
    return value[name]


def _required_nullable(value: Mapping[str, Any], name: str) -> Any:
    if name not in value:
        raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
    return value[name]


def _strict_id(value: Any) -> int:
    if type(value) is not int or not 1 <= value <= MAX_ID:
        raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
    return value


def _nonnegative_int(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
    return value


def _strict_bool(value: Any) -> bool:
    if type(value) is not bool:
        raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
    return value


def _text(value: Any, maximum: int) -> str:
    if (
        type(value) is not str
        or len(value.encode("utf-8")) > maximum
        or any(ord(char) < 32 for char in value)
    ):
        raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
    return value


def _timestamp(value: Any, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if type(value) is not str:
        raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
    try:
        return _validate_timestamp(value)
    except ValueError as exc:
        raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID") from exc


def _oid(
    value: Any, repository: GitHubRepositoryProfile, *, nullable: bool = False
) -> str | None:
    if value is None and nullable:
        return None
    length = 40 if repository.git_object_format == "sha1" else 64
    if type(value) is not str or re.fullmatch(rf"[0-9a-f]{{{length}}}", value) is None:
        raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
    return value


def _enum(value: Any, family: str, reasons: set[str]) -> str:
    if type(value) is not str:
        raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
    if value not in ENUMS[family]:
        reasons.add("UNKNOWN_SECURITY_STATE")
        return sha256_bytes(value.encode("utf-8"))
    return value


def _actor(
    value: Any, reasons: set[str], *, nullable: bool = False
) -> dict[str, Any] | None:
    if value is None and nullable:
        return None
    actor = _object(value)
    return {
        "id": _strict_id(_required(actor, "id")),
        "type": _enum(_required(actor, "type"), "actor_type", reasons),
    }


def _hash_text(value: Any, maximum: int) -> str:
    return sha256_bytes(_text(value, maximum).encode("utf-8"))


@dataclass(frozen=True)
class ProjectionResult:
    observation_kind: str
    normalized: dict[str, Any]
    item_count: int
    complete: bool
    identity_match: bool
    reason_codes: tuple[str, ...]
    visibility: str


@dataclass(frozen=True)
class ResponseProjectionBundle:
    projection: ProjectionResult
    page_item_counts: tuple[int, ...]


def _sort_unique(items: list[dict[str, Any]], key: str = "id") -> list[dict[str, Any]]:
    ordered = sorted(items, key=lambda item: item[key])
    values = [item[key] for item in ordered]
    if len(values) != len(set(values)):
        raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
    return ordered


def project_github_json(
    *,
    operation_key: str,
    value: Any,
    repository: GitHubRepositoryProfile,
    intent: GitHubOperationIntent,
) -> ProjectionResult:
    if operation_key != intent.operation_key or operation_key not in ENDPOINTS:
        raise GitHubFoundationFailure("INTENT_CONFLICT")
    reasons: set[str] = set()
    identity = True
    visibility = "complete_for_endpoint"

    if operation_key == "repository.get":
        raw = _object(value)
        owner = _object(_required(raw, "owner"))
        repository_id = _strict_id(_required(raw, "id"))
        account_id = _strict_id(_required(owner, "id"))
        identity = (
            repository_id == repository.repository_id
            and account_id == repository.account_id
        )
        normalized = {
            "repository_id": repository_id,
            "repository_node_id": _text(_required(raw, "node_id"), 128),
            "name": _text(_required(raw, "name"), 100),
            "full_name": _text(_required(raw, "full_name"), 256),
            "account_id": account_id,
            "account_node_id": _text(_required(owner, "node_id"), 128),
            "private": _strict_bool(_required(raw, "private")),
            "archived": _strict_bool(_required(raw, "archived")),
            "disabled": _strict_bool(_required(raw, "disabled")),
            "visibility": _enum(
                _required(raw, "visibility"), "repository_visibility", reasons
            ),
            "default_branch": _text(_required(raw, "default_branch"), 255),
            "allow_merge_commit": _strict_bool(_required(raw, "allow_merge_commit")),
            "allow_squash_merge": _strict_bool(_required(raw, "allow_squash_merge")),
            "allow_rebase_merge": _strict_bool(_required(raw, "allow_rebase_merge")),
        }
        kind, count = "repository", 1
    elif operation_key == "repository_hash_algorithm.get":
        raw = _object(value)
        algorithm = _required(raw, "hash_algorithm")
        if algorithm not in {"sha1", "sha256"}:
            reasons.add("UNKNOWN_SECURITY_STATE")
        identity = algorithm == repository.git_object_format
        normalized, kind, count = (
            {"hash_algorithm": algorithm},
            "repository_hash_algorithm",
            1,
        )
    elif operation_key == "ref.get":
        raw = _object(value)
        obj = _object(_required(raw, "object"))
        returned_ref = _text(_required(raw, "ref"), 1024)
        requested_ref = intent.path_parameters["ref"]
        identity = returned_ref == requested_ref
        object_type = _required(obj, "type")
        if object_type != "commit":
            reasons.add("UNKNOWN_SECURITY_STATE")
        normalized = {
            "requested_ref": requested_ref,
            "returned_ref": returned_ref,
            "node_id": _text(_required(raw, "node_id"), 128),
            "object_sha": _oid(_required(obj, "sha"), repository),
            "object_type": object_type,
        }
        kind, count = "ref", 1
    elif operation_key == "commit.get":
        raw = _object(value)
        verification = _object(_required(raw, "verification"))
        parents = [
            {"sha": _oid(_required(_object(item), "sha"), repository)}
            for item in _array(_required(raw, "parents"))
        ]
        commit_sha = _oid(_required(raw, "sha"), repository)
        identity = commit_sha == intent.path_parameters["commit_sha"]
        normalized = {
            "sha": commit_sha,
            "node_id": _text(_required(raw, "node_id"), 128),
            "tree_sha": _oid(
                _required(_object(_required(raw, "tree")), "sha"), repository
            ),
            "parents": parents,
            "verification": {
                "verified": _strict_bool(_required(verification, "verified")),
                "reason": _enum(
                    _required(verification, "reason"), "verification_reason", reasons
                ),
                "verified_at": _timestamp(
                    _required_nullable(verification, "verified_at"), nullable=True
                ),
            },
        }
        kind, count = "commit", 1
    elif operation_key == "pull_request.get":
        raw = _object(value)
        user = _object(_required(raw, "user"))
        head = _object(_required(raw, "head"))
        base = _object(_required(raw, "base"))
        head_repo_raw = _required_nullable(head, "repo")
        head_repo_id = (
            None
            if head_repo_raw is None
            else _strict_id(_required(_object(head_repo_raw), "id"))
        )
        base_repo_id = _strict_id(_required(_object(_required(base, "repo")), "id"))
        number = _strict_id(_required(raw, "number"))
        identity = (
            number == intent.path_parameters["pull_number"]
            and base_repo_id == repository.repository_id
        )
        mergeable = _required_nullable(raw, "mergeable")
        if mergeable is not None:
            mergeable = _strict_bool(mergeable)
        normalized = {
            "id": _strict_id(_required(raw, "id")),
            "number": number,
            "state": _enum(_required(raw, "state"), "pull_state", reasons),
            "draft": _strict_bool(_required(raw, "draft")),
            "merged": _strict_bool(_required(raw, "merged")),
            "mergeable": mergeable,
            "mergeable_state": _enum(
                _required(raw, "mergeable_state"), "mergeable_state", reasons
            ),
            "author": _actor(user, reasons),
            "head": {
                "sha": _oid(_required(head, "sha"), repository),
                "ref": _text(_required(head, "ref"), 255),
                "repository_id": head_repo_id,
            },
            "base": {
                "sha": _oid(_required(base, "sha"), repository),
                "ref": _text(_required(base, "ref"), 255),
                "repository_id": base_repo_id,
            },
            "created_at": _timestamp(_required(raw, "created_at")),
            "updated_at": _timestamp(_required(raw, "updated_at")),
            "closed_at": _timestamp(
                _required_nullable(raw, "closed_at"), nullable=True
            ),
            "merged_at": _timestamp(
                _required_nullable(raw, "merged_at"), nullable=True
            ),
        }
        kind, count = "pull_request", 1
    elif operation_key == "check_runs.list":
        raw = _object(value)
        items = []
        for entry in _array(_required(raw, "check_runs")):
            item = _object(entry)
            app = _required_nullable(item, "app")
            conclusion = _required_nullable(item, "conclusion")
            items.append(
                {
                    "id": _strict_id(_required(item, "id")),
                    "name_hash": _hash_text(_required(item, "name"), 512),
                    "head_sha": _oid(_required(item, "head_sha"), repository),
                    "status": _enum(_required(item, "status"), "check_status", reasons),
                    "conclusion": None
                    if conclusion is None
                    else _enum(conclusion, "check_conclusion", reasons),
                    "app_id": None
                    if app is None
                    else _strict_id(_required(_object(app), "id")),
                    "started_at": _timestamp(
                        _required_nullable(item, "started_at"), nullable=True
                    ),
                    "completed_at": _timestamp(
                        _required_nullable(item, "completed_at"), nullable=True
                    ),
                }
            )
        total_count = _nonnegative_int(_required(raw, "total_count"))
        if total_count < len(items):
            raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
        normalized = {
            "total_count": total_count,
            "check_runs": _sort_unique(items),
            "github_check_suite_horizon": 1000,
            "global_history_complete": False,
        }
        kind, count = "check_runs", len(items)
        visibility = "complete_within_github_check_suite_horizon"
    elif operation_key == "combined_status.get":
        raw = _object(value)
        items = []
        for entry in _array(_required(raw, "statuses")):
            item = _object(entry)
            items.append(
                {
                    "id": _strict_id(_required(item, "id")),
                    "context_hash": _hash_text(_required(item, "context"), 512),
                    "state": _enum(
                        _required(item, "state"), "commit_status_state", reasons
                    ),
                    "creator": _actor(
                        _required_nullable(item, "creator"), reasons, nullable=True
                    ),
                    "updated_at": _timestamp(_required(item, "updated_at")),
                }
            )
        sha = _oid(_required(raw, "sha"), repository)
        identity = sha == intent.path_parameters["commit_sha"]
        total_count = _nonnegative_int(_required(raw, "total_count"))
        if total_count < len(items):
            raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
        normalized = {
            "sha": sha,
            "state": _enum(_required(raw, "state"), "commit_status_state", reasons),
            "total_count": total_count,
            "statuses": _sort_unique(items),
        }
        kind, count = "combined_status", len(items)
    elif operation_key in {
        "reviews.list",
        "issue_comments.list",
        "review_comments.list",
    }:
        items = []
        for entry in _array(value):
            item = _object(entry)
            common = {
                "id": _strict_id(_required(item, "id")),
                "user": _actor(
                    _required_nullable(item, "user"), reasons, nullable=True
                ),
            }
            if operation_key == "reviews.list":
                common.update(
                    {
                        "state": _enum(
                            _required(item, "state"), "review_state", reasons
                        ),
                        "submitted_at": _timestamp(
                            _required_nullable(item, "submitted_at"), nullable=True
                        ),
                        "commit_id": _oid(
                            _required_nullable(item, "commit_id"),
                            repository,
                            nullable=True,
                        ),
                    }
                )
            elif operation_key == "issue_comments.list":
                minimized = _required_nullable(item, "minimized")
                common.update(
                    {
                        "created_at": _timestamp(_required(item, "created_at")),
                        "updated_at": _timestamp(_required(item, "updated_at")),
                        "minimized": None
                        if minimized is None
                        else _strict_bool(minimized),
                    }
                )
            else:
                review_id = _required_nullable(item, "pull_request_review_id")
                reply_id = _required_nullable(item, "in_reply_to_id")
                common.update(
                    {
                        "pull_request_review_id": None
                        if review_id is None
                        else _strict_id(review_id),
                        "in_reply_to_id": None
                        if reply_id is None
                        else _strict_id(reply_id),
                        "path_hash": _hash_text(_required(item, "path"), 4096),
                        "commit_id": _oid(_required(item, "commit_id"), repository),
                        "original_commit_id": _oid(
                            _required_nullable(item, "original_commit_id"),
                            repository,
                            nullable=True,
                        ),
                        "created_at": _timestamp(_required(item, "created_at")),
                        "updated_at": _timestamp(_required(item, "updated_at")),
                    }
                )
            items.append(common)
        normalized = {"items": _sort_unique(items)}
        kind = operation_key.removesuffix(".list")
        count = len(items)
    elif operation_key == "branch_protection.get":
        normalized, extension = _project_branch_protection(_object(value), reasons)
        if extension:
            normalized["security_extension_hash"] = extension
        kind, count = "branch_protection", 1
    elif operation_key == "branch_rules.list":
        items = [
            _project_rule_entry(_object(item), reasons, include_source=True)
            for item in _array(value)
        ]
        ordered_rules = sorted(
            items,
            key=lambda item: (
                item["type"],
                item["parameter_hash"] or "",
                item["ruleset_id"],
            ),
        )
        rule_keys = [
            (item["type"], item["parameter_hash"], item["ruleset_id"])
            for item in ordered_rules
        ]
        if len(rule_keys) != len(set(rule_keys)):
            raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
        normalized = {"rules": ordered_rules}
        kind, count = "branch_rules", len(items)
    elif operation_key in {"repository_rulesets.list", "repository_ruleset.get"}:
        raw_items = _array(value) if operation_key.endswith(".list") else [value]
        items = [
            _project_ruleset(
                _object(item), reasons, detailed=operation_key.endswith(".get")
            )
            for item in raw_items
        ]
        normalized = {"rulesets": _sort_unique(items)}
        kind, count = "repository_ruleset", len(items)
        if (
            operation_key.endswith(".get")
            and items[0]["id"] != intent.path_parameters["ruleset_id"]
        ):
            identity = False
        if any(
            item.get("bypass_actor_visibility") == "incomplete_by_permission"
            for item in items
        ):
            visibility = "incomplete_by_permission"
    else:
        raise GitHubFoundationFailure("ENDPOINT_NOT_ALLOWED")

    if not identity:
        reasons.add("REPOSITORY_IDENTITY_MISMATCH")
    complete = not reasons and identity
    return ProjectionResult(
        kind, normalized, count, complete, identity, tuple(sorted(reasons)), visibility
    )


_PROTECTION_BLOCKS = (
    "required_status_checks",
    "enforce_admins",
    "required_pull_request_reviews",
    "restrictions",
    "required_signatures",
    "block_creations",
    "required_linear_history",
    "allow_force_pushes",
    "allow_deletions",
    "required_conversation_resolution",
    "lock_branch",
    "allow_fork_syncing",
)
_PRESENTATION_KEYS = frozenset({"url", "html_url", "name"})


def _project_branch_protection(
    raw: dict[str, Any], reasons: set[str]
) -> tuple[dict[str, Any], str | None]:
    result: dict[str, Any] = {}
    extensions: dict[str, Any] = {
        key: value
        for key, value in raw.items()
        if key not in _PROTECTION_BLOCKS and key not in _PRESENTATION_KEYS
    }
    enabled_blocks = set(_PROTECTION_BLOCKS) - {
        "required_status_checks",
        "required_pull_request_reviews",
        "restrictions",
    }
    for name in _PROTECTION_BLOCKS:
        if name not in raw:
            result[name] = {"present": False, "value": None}
            continue
        value = raw[name]
        if value is None:
            result[name] = {"present": True, "value": None}
            continue
        block = _object(value)
        if name in enabled_blocks:
            known = {"enabled"}
            normalized = {"enabled": _strict_bool(_required(block, "enabled"))}
        elif name == "required_status_checks":
            known = {"strict", "contexts", "checks"}
            contexts = [
                _hash_text(item, 512) for item in _array(_required(block, "contexts"))
            ]
            checks = []
            for item in _array(block.get("checks", [])):
                check = _object(item)
                app_id = check.get("app_id")
                checks.append(
                    {
                        "context_hash": _hash_text(_required(check, "context"), 512),
                        "app_id": None if app_id is None else _strict_id(app_id),
                    }
                )
            checks.sort(key=lambda item: (item["context_hash"], item["app_id"] or 0))
            if len(contexts) != len(set(contexts)) or len(checks) != len(
                {(item["context_hash"], item["app_id"]) for item in checks}
            ):
                raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
            normalized = {
                "strict": _strict_bool(_required(block, "strict")),
                "context_hashes": sorted(set(contexts)),
                "checks": checks,
            }
        elif name == "required_pull_request_reviews":
            known = {
                "dismiss_stale_reviews",
                "require_code_owner_reviews",
                "required_approving_review_count",
                "require_last_push_approval",
                "dismissal_restrictions",
                "bypass_pull_request_allowances",
            }
            count = _nonnegative_int(
                _required(block, "required_approving_review_count")
            )
            if count > 6:
                raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
            normalized = {
                "dismiss_stale_reviews": _strict_bool(
                    _required(block, "dismiss_stale_reviews")
                ),
                "require_code_owner_reviews": _strict_bool(
                    _required(block, "require_code_owner_reviews")
                ),
                "required_approving_review_count": count,
                "require_last_push_approval": _strict_bool(
                    _required(block, "require_last_push_approval")
                ),
            }
            for restriction_name in (
                "dismissal_restrictions",
                "bypass_pull_request_allowances",
            ):
                if restriction_name not in block:
                    continue
                restriction = _object(block[restriction_name])
                projected: dict[str, Any] = {}
                for collection in ("users", "teams", "apps"):
                    actors = []
                    for item in _array(restriction.get(collection, [])):
                        actor = _object(item)
                        actors.append(
                            {
                                "id": _strict_id(_required(actor, "id")),
                                "type": _enum(
                                    _required(actor, "type"), "actor_type", reasons
                                ),
                            }
                        )
                    projected[collection] = sorted(actors, key=lambda item: item["id"])
                normalized[restriction_name] = projected
        else:
            known = {"users", "teams", "apps"}
            normalized = {}
            for actor_type in ("users", "teams", "apps"):
                normalized[actor_type] = sorted(
                    _strict_id(_required(_object(item), "id"))
                    for item in _array(block.get(actor_type, []))
                )
        unknown = {
            key: value
            for key, value in block.items()
            if key not in known and key not in _PRESENTATION_KEYS
        }
        if unknown:
            extensions[f"{name}.unknown"] = unknown
        result[name] = {"present": True, "value": normalized}
    if extensions:
        reasons.add("UNKNOWN_SECURITY_STATE")
        return result, sha256_bytes(_canonical_json_bytes(extensions))
    return result, None


def _project_rule_entry(
    raw: dict[str, Any], reasons: set[str], *, include_source: bool
) -> dict[str, Any]:
    parameters = raw.get("parameters")
    if parameters is not None:
        parameters = _object(parameters)
    result = {
        "type": _enum(_required(raw, "type"), "rule_type", reasons),
        "parameter_hash": None
        if parameters is None
        else sha256_bytes(_canonical_json_bytes(parameters)),
    }
    if include_source:
        result.update(
            {
                "ruleset_source_type": _enum(
                    _required(raw, "ruleset_source_type"),
                    "ruleset_source_type",
                    reasons,
                ),
                "ruleset_source_hash": _hash_text(
                    _required(raw, "ruleset_source"), 256
                ),
                "ruleset_id": _strict_id(_required(raw, "ruleset_id")),
            }
        )
    return result


def _project_ruleset(
    raw: dict[str, Any], reasons: set[str], *, detailed: bool
) -> dict[str, Any]:
    result = {
        "id": _strict_id(_required(raw, "id")),
        "node_id": _text(_required(raw, "node_id"), 128),
        "source_type": _enum(
            _required(raw, "source_type"), "ruleset_source_type", reasons
        ),
        "source_hash": _hash_text(_required(raw, "source"), 256),
        "enforcement": _enum(
            _required(raw, "enforcement"), "ruleset_enforcement", reasons
        ),
        "created_at": _timestamp(_required(raw, "created_at")),
        "updated_at": _timestamp(_required(raw, "updated_at")),
    }
    target = _required_nullable(raw, "target")
    if target is not None:
        result["target"] = _enum(target, "ruleset_target", reasons)
    if detailed:
        if target is None:
            raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
        result["conditions_hash"] = sha256_bytes(
            _canonical_json_bytes(_object(_required(raw, "conditions")))
        )
        rules = [
            _project_rule_entry(_object(item), reasons, include_source=False)
            for item in _array(_required(raw, "rules"))
        ]
        result["rules"] = sorted(
            rules, key=lambda item: (item["type"], item["parameter_hash"] or "")
        )
        rule_keys = [(item["type"], item["parameter_hash"]) for item in result["rules"]]
        if len(rule_keys) != len(set(rule_keys)):
            raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
        if "bypass_actors" not in raw:
            result["bypass_actors"] = []
            result["bypass_actor_visibility"] = "incomplete_by_permission"
        else:
            actors = []
            for item in _array(raw["bypass_actors"]):
                actor = _object(item)
                actor_id = actor.get("actor_id")
                actors.append(
                    {
                        "actor_id": None if actor_id is None else _strict_id(actor_id),
                        "actor_type": _enum(
                            _required(actor, "actor_type"), "bypass_actor_type", reasons
                        ),
                        "bypass_mode": _enum(
                            _required(actor, "bypass_mode"), "bypass_mode", reasons
                        ),
                    }
                )
            result["bypass_actors"] = sorted(
                actors,
                key=lambda item: (
                    item["actor_type"],
                    item["actor_id"] or 0,
                    item["bypass_mode"],
                ),
            )
            result["bypass_actor_visibility"] = "observed_not_attested"
    return result


def project_github_responses(
    *,
    responses: tuple[GitHubTransportResponse, ...],
    operation_key: str,
    repository: GitHubRepositoryProfile,
    intent: GitHubOperationIntent,
    maximum_page_bytes: int,
) -> ResponseProjectionBundle:
    if not responses:
        raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
    spec = ENDPOINTS[operation_key]
    if (not spec.paginated and len(responses) != 1) or len(
        responses
    ) > spec.maximum_pages:
        raise GitHubFoundationFailure("PAGINATION_INVALID")
    projected: list[ProjectionResult] = []
    for response in responses:
        if not 200 <= response.status < 300:
            raise GitHubFoundationFailure("HTTP_RESPONSE_REJECTED")
        value = parse_bounded_json(response.body, maximum_bytes=maximum_page_bytes)
        projected.append(
            project_github_json(
                operation_key=operation_key,
                value=value,
                repository=repository,
                intent=intent,
            )
        )
    if len(projected) == 1:
        return ResponseProjectionBundle(projected[0], (projected[0].item_count,))

    reasons = {reason for item in projected for reason in item.reason_codes}
    identity = all(item.identity_match for item in projected)
    visibility = projected[0].visibility
    if any(item.visibility != visibility for item in projected):
        raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
    key = {
        "check_runs.list": "check_runs",
        "combined_status.get": "statuses",
        "reviews.list": "items",
        "issue_comments.list": "items",
        "review_comments.list": "items",
        "branch_rules.list": "rules",
        "repository_rulesets.list": "rulesets",
    }.get(operation_key)
    if key is None:
        raise GitHubFoundationFailure("PAGINATION_INVALID")
    combined_items = [entry for result in projected for entry in result.normalized[key]]
    if key in {"check_runs", "statuses", "items", "rulesets"}:
        combined_items = _sort_unique(combined_items)
    else:
        rule_keys = [
            (item["type"], item["parameter_hash"], item["ruleset_id"])
            for item in combined_items
        ]
        if len(rule_keys) != len(set(rule_keys)):
            raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
        combined_items = sorted(
            combined_items,
            key=lambda item: (
                item["type"],
                item["parameter_hash"] or "",
                item["ruleset_id"],
            ),
        )
    normalized = dict(projected[0].normalized)
    normalized[key] = combined_items
    if operation_key in {"check_runs.list", "combined_status.get"}:
        totals = {result.normalized["total_count"] for result in projected}
        if len(totals) != 1 or next(iter(totals)) != len(combined_items):
            raise GitHubFoundationFailure("PAGINATION_INVALID")
    total_items = len(combined_items)
    if total_items > spec.maximum_items:
        raise GitHubFoundationFailure("ITEM_LIMIT_REACHED")
    aggregate = ProjectionResult(
        projected[0].observation_kind,
        normalized,
        total_items,
        not reasons and identity,
        identity,
        tuple(sorted(reasons)),
        visibility,
    )
    return ResponseProjectionBundle(
        aggregate, tuple(item.item_count for item in projected)
    )


class SafeRateLimitProjection(ClosedModel):
    resource: str | None = Field(default=None, max_length=64)
    limit: int | None = Field(default=None, ge=0)
    remaining: int | None = Field(default=None, ge=0)
    reset_at: str | None = None
    retry_after_present: bool

    @field_validator("reset_at")
    @classmethod
    def valid_reset(cls, value: str | None) -> str | None:
        return None if value is None else _validate_timestamp(value)


class ObservationPage(ClosedModel):
    page: int = Field(gt=0)
    response_bytes: int = Field(ge=0)
    wire_body_hash: Hash = Field(pattern=HASH_PATTERN)
    item_count: int = Field(ge=0)
    rate_limit: SafeRateLimitProjection


class GitHubObservation(GitHubRecord):
    profile: Literal["github-observation"] = "github-observation"
    schema_version: Literal[OBSERVATION_SCHEMA] = OBSERVATION_SCHEMA
    observation_id: str
    observation_kind: str = Field(min_length=1, max_length=64)
    repository_profile: RecordReference
    api_profile: RecordReference
    authorization: RecordReference
    intent: RecordReference
    attempt_claim: RecordReference
    lease_evidence: RecordReference
    repository_id: int = Field(gt=0)
    account_id: int = Field(gt=0)
    app_id: int = Field(gt=0)
    installation_id: int = Field(gt=0)
    operation_key: OperationKey
    path_parameters: dict[str, Scalar]
    query_parameters: dict[str, Scalar]
    attempt_id: str = Field(pattern=ATTEMPT_PATTERN)
    observed_at: str
    status_class: Literal["2xx", "3xx", "4xx", "5xx", "transport", "none"]
    pages: tuple[ObservationPage, ...]
    response_projection_version: Literal[RESPONSE_PROJECTION_VERSION] = (
        RESPONSE_PROJECTION_VERSION
    )
    projection: dict[str, Any]
    complete: bool
    pagination_complete: bool
    identity_match: bool
    visibility: Literal[
        "complete_for_endpoint",
        "complete_within_github_check_suite_horizon",
        "not_observed",
        "incomplete_by_permission",
        "observed_not_attested",
    ]
    reason_codes: tuple[str, ...]
    merge_authorized: Literal[False] = False
    action_execution_allowed: Literal[False] = False

    @field_validator("observation_id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        return _validate_uuid7(value)

    @field_validator("observed_at")
    @classmethod
    def valid_time(cls, value: str) -> str:
        return _validate_timestamp(value)

    @field_validator("reason_codes")
    @classmethod
    def ordered_reasons(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if tuple(sorted(set(values))) != values:
            raise ValueError("reason codes must be sorted and unique")
        if any(value not in REASON_CODES for value in values):
            raise ValueError("reason code is outside the closed vocabulary")
        return values


def _rate_limit(headers: tuple[tuple[str, str], ...]) -> SafeRateLimitProjection:
    lowered: dict[str, str] = {}
    for name, value in headers:
        key = name.lower()
        if key in lowered:
            raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
        lowered[key] = value

    def integer(name: str) -> int | None:
        if name not in lowered:
            return None
        if re.fullmatch(r"[0-9]+", lowered[name]) is None:
            raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
        return int(lowered[name])

    reset = integer("x-ratelimit-reset")
    reset_at = (
        None
        if reset is None
        else datetime.fromtimestamp(reset, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    )
    resource = lowered.get("x-ratelimit-resource")
    if resource is not None:
        resource = _text(resource, 64)
    return SafeRateLimitProjection(
        resource=resource,
        limit=integer("x-ratelimit-limit"),
        remaining=integer("x-ratelimit-remaining"),
        reset_at=reset_at,
        retry_after_present="retry-after" in lowered,
    )


def create_success_observation(
    *,
    observation_id: str,
    observed_at: str,
    responses: tuple[GitHubTransportResponse, ...],
    repository_profile: GitHubRepositoryProfile,
    api_profile: GitHubApiProfile,
    authorization: GitHubOperationAuthorization,
    intent: GitHubOperationIntent,
    attempt_claim: GitHubOperationAttemptClaim,
    lease_evidence: CredentialLeaseEvidence,
    projection: ProjectionResult,
    page_item_counts: tuple[int, ...] | None = None,
) -> GitHubObservation:
    if not responses:
        raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
    status = responses[-1].status
    status_class = f"{status // 100}xx"
    if status_class not in {"2xx", "3xx", "4xx", "5xx"}:
        raise GitHubFoundationFailure("HTTP_RESPONSE_REJECTED")
    counts = page_item_counts or (
        (projection.item_count,) if len(responses) == 1 else ()
    )
    if len(counts) != len(responses) or any(
        type(count) is not int or count < 0 for count in counts
    ):
        raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
    pages = tuple(
        ObservationPage(
            page=index,
            response_bytes=len(response.body),
            wire_body_hash=sha256_bytes(response.body),
            item_count=counts[index - 1],
            rate_limit=_rate_limit(response.headers),
        )
        for index, response in enumerate(responses, 1)
    )
    reasons = set(projection.reason_codes)
    if status_class != "2xx":
        reasons.add("HTTP_RESPONSE_REJECTED")
    complete = projection.complete and status_class == "2xx"
    return _seal_github_record(
        GitHubObservation,
        {
            "profile": "github-observation",
            "schema_version": OBSERVATION_SCHEMA,
            "observation_id": observation_id,
            "observation_kind": projection.observation_kind,
            "repository_profile": {
                "reference": intent.repository_profile.reference,
                "content_hash": repository_profile.content_hash,
            },
            "api_profile": {
                "reference": intent.api_profile.reference,
                "content_hash": api_profile.content_hash,
            },
            "authorization": {
                "reference": intent.authorization.reference,
                "content_hash": authorization.content_hash,
            },
            "intent": {
                "reference": lease_evidence.intent.reference,
                "content_hash": intent.content_hash,
            },
            "attempt_claim": {
                "reference": lease_evidence.attempt_claim.reference,
                "content_hash": attempt_claim.content_hash,
            },
            "lease_evidence": {
                "reference": f"github/lease-evidence/lease-{lease_evidence.content_hash.removeprefix('sha256:')}.json",
                "content_hash": lease_evidence.content_hash,
            },
            "repository_id": repository_profile.repository_id,
            "account_id": repository_profile.account_id,
            "app_id": repository_profile.expected_app_id,
            "installation_id": repository_profile.expected_installation_id,
            "operation_key": intent.operation_key,
            "path_parameters": intent.path_parameters,
            "query_parameters": intent.query_parameters,
            "attempt_id": intent.attempt_id,
            "observed_at": observed_at,
            "status_class": status_class,
            "pages": pages,
            "response_projection_version": RESPONSE_PROJECTION_VERSION,
            "projection": projection.normalized,
            "complete": complete,
            "pagination_complete": complete,
            "identity_match": projection.identity_match,
            "visibility": projection.visibility,
            "reason_codes": tuple(sorted(reasons)),
            "merge_authorized": False,
            "action_execution_allowed": False,
            "created_at": observed_at,
            "authority_effect": "none",
            "decision_effect": "none",
            "membership_effect": "none",
            "production_use_allowed": False,
        },
    )


def create_failure_observation(
    *,
    observation_id: str,
    observed_at: str,
    reason_codes: tuple[str, ...],
    status_class: Literal["2xx", "3xx", "4xx", "5xx", "transport", "none"],
    responses: tuple[GitHubTransportResponse, ...],
    repository_profile: GitHubRepositoryProfile,
    api_profile: GitHubApiProfile,
    authorization: GitHubOperationAuthorization,
    intent: GitHubOperationIntent,
    attempt_claim: GitHubOperationAttemptClaim,
    lease_evidence: CredentialLeaseEvidence,
) -> GitHubObservation:
    reasons = tuple(sorted(set(reason_codes)))
    if not reasons or any(reason not in REASON_CODES for reason in reasons):
        raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
    pages = tuple(
        ObservationPage(
            page=index,
            response_bytes=len(response.body),
            wire_body_hash=sha256_bytes(response.body),
            item_count=0,
            rate_limit=_rate_limit(response.headers),
        )
        for index, response in enumerate(responses, 1)
    )
    return _seal_github_record(
        GitHubObservation,
        {
            "profile": "github-observation",
            "schema_version": OBSERVATION_SCHEMA,
            "observation_id": observation_id,
            "observation_kind": "failure",
            "repository_profile": {
                "reference": intent.repository_profile.reference,
                "content_hash": repository_profile.content_hash,
            },
            "api_profile": {
                "reference": intent.api_profile.reference,
                "content_hash": api_profile.content_hash,
            },
            "authorization": {
                "reference": intent.authorization.reference,
                "content_hash": authorization.content_hash,
            },
            "intent": {
                "reference": lease_evidence.intent.reference,
                "content_hash": intent.content_hash,
            },
            "attempt_claim": {
                "reference": lease_evidence.attempt_claim.reference,
                "content_hash": attempt_claim.content_hash,
            },
            "lease_evidence": {
                "reference": f"github/lease-evidence/lease-{lease_evidence.content_hash.removeprefix('sha256:')}.json",
                "content_hash": lease_evidence.content_hash,
            },
            "repository_id": repository_profile.repository_id,
            "account_id": repository_profile.account_id,
            "app_id": repository_profile.expected_app_id,
            "installation_id": repository_profile.expected_installation_id,
            "operation_key": intent.operation_key,
            "path_parameters": intent.path_parameters,
            "query_parameters": intent.query_parameters,
            "attempt_id": intent.attempt_id,
            "observed_at": observed_at,
            "status_class": status_class,
            "pages": pages,
            "response_projection_version": RESPONSE_PROJECTION_VERSION,
            "projection": {"visibility": "not_observed"},
            "complete": False,
            "pagination_complete": False,
            "identity_match": False,
            "visibility": "not_observed",
            "reason_codes": reasons,
            "merge_authorized": False,
            "action_execution_allowed": False,
            "created_at": observed_at,
            "authority_effect": "none",
            "decision_effect": "none",
            "membership_effect": "none",
            "production_use_allowed": False,
        },
    )


def safe_failure_diagnostic(*, operation_key: str, reason_code: str) -> dict[str, str]:
    if operation_key not in ENDPOINTS or reason_code not in REASON_CODES:
        raise GitHubFoundationFailure("RESPONSE_PROJECTION_INVALID")
    return {"operation_key": operation_key, "reason_code": reason_code}
