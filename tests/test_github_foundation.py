"""Increment 21A local foundation acceptance and abuse tests."""

from __future__ import annotations

import base64
import hmac
import hashlib
import json
import pickle
from pathlib import Path
from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError as PydanticValidationError

from conclave.errors import IntegrityError, ValidationError
from conclave.github_foundation import (
    API_PROFILE_SCHEMA,
    ATTEMPT_DOMAIN,
    ATTEMPT_PREIMAGE_SCHEMA,
    CLAIMS_SIGNATURE_DOMAIN,
    ENDPOINTS,
    RECEIPT_SIGNATURE_DOMAIN,
    CredentialEnvelope,
    CredentialLeaseClaims,
    CredentialLeaseReceipt,
    CredentialResolutionRequest,
    GitHubTransportFailure,
    GitHubTransportResponse,
    DurableLeaseEvidenceAdmission,
    GitHubApiProfile,
    GitHubCredentialProviderKey,
    GitHubFoundationFailure,
    GitHubOperationAttemptClaim,
    GitHubOperationAuthorization,
    GitHubOperationIntent,
    GitHubRepositoryProfile,
    PermissionEnvelope,
    RecordReference,
    attempt_claim_path,
    build_github_request,
    compute_attempt_id,
    create_durable_lease_admission,
    prepare_credential_lease,
    create_production_https_transport,
    create_failure_observation,
    create_success_observation,
    parse_bounded_json,
    project_github_json,
    project_github_responses,
    run_github_transport,
    safe_failure_diagnostic,
    sanitized_receipt_hash,
    write_attempt_claim,
    write_durable_record,
)
from conclave.identity import seal_record, sha256_bytes
from conclave.workspace import Workspace
from github_fixture_support import FixtureGitHubTransport
from conclave.github_operation import execute_github_read
from conclave.ledger import initialise as initialise_ledger, read_events

run_fixture_transport = run_github_transport

NOW = "2026-09-09T06:00:00Z"
LATER = "2026-09-09T06:10:00Z"
UUID7_A = "01890f3e-7b1a-7cc2-8b4f-8f2e9c90a111"
UUID7_B = "01890f3e-7b1a-7cc2-8b4f-8f2e9c90a112"
H1 = "sha256:" + "1" * 64
H2 = "sha256:" + "2" * 64
H3 = "sha256:" + "3" * 64


def _permissions(**changes: str) -> PermissionEnvelope:
    values = {
        "metadata": "read",
        "contents": "none",
        "pull_requests": "none",
        "checks": "none",
        "statuses": "none",
        "administration": "none",
    }
    values.update(changes)
    return PermissionEnvelope.model_validate(values)


def _api_profile(**changes) -> GitHubApiProfile:
    values = {
        "profile": "github-api-profile",
        "schema_version": API_PROFILE_SCHEMA,
        "created_at": NOW,
        "authority_effect": "none",
        "decision_effect": "none",
        "membership_effect": "none",
        "production_use_allowed": False,
    }
    values.update(changes)
    return seal_record(GitHubApiProfile, values)


def _repository_profile(**changes) -> GitHubRepositoryProfile:
    key = bytes(range(32))
    values = {
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
        "provider_key_hash": H1,
        "expected_provider_key_id": "fixture-key",
        "expected_provider_public_key_sha256": sha256_bytes(key),
        "expected_app_id": 303,
        "expected_installation_id": 404,
        "repository_selection": "selected",
        "permission_ceiling": _permissions(contents="read"),
        "read_operations": ("ref.get", "repository.get"),
        "live_use_allowed": False,
        "created_at": NOW,
        "authority_effect": "none",
        "decision_effect": "none",
        "membership_effect": "none",
        "production_use_allowed": False,
    }
    values.update(changes)
    return seal_record(GitHubRepositoryProfile, values)


def _authorization(**changes) -> GitHubOperationAuthorization:
    values = {
        "profile": "github-operation-authorization",
        "schema_version": "github-operation-authorization/0.1.0",
        "authorization_id": UUID7_A,
        "repository_profile": RecordReference(
            reference="github/repository-profiles/repo.json", content_hash=H1
        ),
        "api_profile": RecordReference(
            reference="github/api-profiles/api.json", content_hash=H2
        ),
        "repository_id": 101,
        "account_id": 202,
        "stage": "21A",
        "operation_mode": "read_only",
        "operation_key": "ref.get",
        "path_parameters": {"ref": "refs/heads/main"},
        "query_parameters": {},
        "purpose": "Read one exact ref for a governed observation",
        "authorized_principal": "arthur",
        "issued_at": NOW,
        "expires_at": LATER,
        "maximum_logical_operations": 1,
        "maximum_network_requests": 2,
        "created_at": NOW,
        "authority_effect": "github_read_only",
        "decision_effect": "none",
        "membership_effect": "none",
        "production_use_allowed": False,
    }
    values.update(changes)
    return seal_record(GitHubOperationAuthorization, values)


def _attempt_values() -> dict:
    return {
        "authorization_hash": H1,
        "repository_profile_hash": H2,
        "api_profile_hash": H3,
        "operation_key": "ref.get",
        "path_parameters": {"ref": "refs/heads/main"},
        "query_parameters": {},
        "maximum_response_body_bytes_per_page": 2_097_152,
        "maximum_total_response_body_bytes": 8_388_608,
        "maximum_pages": 1,
        "maximum_items": 1,
        "operation_timeout_seconds": 60,
        "maximum_retry_transmissions_per_operation": 1,
        "maximum_network_requests": 2,
    }


def _intent(**changes) -> GitHubOperationIntent:
    attempt_values = _attempt_values()
    values = {
        "profile": "github-operation-intent",
        "schema_version": "github-operation-intent/0.1.0",
        "intent_id": UUID7_B,
        "authorization": RecordReference(
            reference="github/authorizations/auth.json", content_hash=H1
        ),
        "repository_profile": RecordReference(
            reference="github/repository-profiles/repo.json", content_hash=H2
        ),
        "api_profile": RecordReference(
            reference="github/api-profiles/api.json", content_hash=H3
        ),
        "repository_id": 101,
        "account_id": 202,
        "app_id": 303,
        "installation_id": 404,
        "stage": "21A",
        "http_method": "GET",
        "operation_key": "ref.get",
        "path_parameters": {"ref": "refs/heads/main"},
        "query_parameters": {},
        "request_body_hash": None,
        "request_body_bytes": 0,
        "maximum_response_body_bytes_per_page": 2_097_152,
        "maximum_total_response_body_bytes": 8_388_608,
        "maximum_pages": 1,
        "maximum_items": 1,
        "operation_timeout_seconds": 60,
        "maximum_retry_transmissions_per_operation": 1,
        "maximum_network_requests": 2,
        "attempt_id": compute_attempt_id(**attempt_values),
        "not_after": LATER,
        "maximum_credential_resolutions": 1,
        "created_at": NOW,
        "authority_effect": "none",
        "decision_effect": "none",
        "membership_effect": "none",
        "production_use_allowed": False,
    }
    values.update(changes)
    return seal_record(GitHubOperationIntent, values)


def _claim(intent: GitHubOperationIntent, **changes) -> GitHubOperationAttemptClaim:
    values = {
        "profile": "github-operation-attempt-claim",
        "schema_version": "github-operation-attempt-claim/0.1.0",
        "attempt_id": intent.attempt_id,
        "authorization": intent.authorization,
        "intent": RecordReference(
            reference="github/intents/intent.json", content_hash=intent.content_hash
        ),
        "repository_profile": intent.repository_profile,
        "api_profile": intent.api_profile,
        "repository_id": 101,
        "account_id": 202,
        "app_id": 303,
        "installation_id": 404,
        "operation_key": "ref.get",
        "claim_time": NOW,
        "intent_expiry": LATER,
        "state": "claimed",
        "created_at": NOW,
        "authority_effect": "none",
        "decision_effect": "none",
        "membership_effect": "none",
        "production_use_allowed": False,
    }
    values.update(changes)
    return seal_record(GitHubOperationAttemptClaim, values)


def test_endpoint_table_is_closed_and_get_only_foundation() -> None:
    assert len(ENDPOINTS) == 14
    assert set(ENDPOINTS) == {
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
    }


def test_api_profile_is_exact_and_closed() -> None:
    profile = _api_profile()
    assert profile.api_version == "2026-03-10"
    assert profile.origin == "https://api.github.com"
    with pytest.raises(PydanticValidationError):
        _api_profile(origin="https://example.test")
    data = profile.model_dump(mode="json")
    data["unexpected"] = True
    with pytest.raises(PydanticValidationError):
        GitHubApiProfile.model_validate(data)


def test_repository_profile_rejects_unsafe_or_live_variants() -> None:
    profile = _repository_profile()
    assert profile.permission_ceiling.read_keys() == {"metadata", "contents"}
    for changes in (
        {"repository": "conclave.git"},
        {"default_branch": "../main"},
        {"provider_key_reference": "../secret.json"},
        {"live_use_allowed": True},
        {"read_operations": ("repository.get", "ref.get")},
    ):
        with pytest.raises(PydanticValidationError):
            _repository_profile(**changes)


def test_provider_key_is_canonical_and_fingerprint_bound() -> None:
    raw = bytes(range(32))
    encoded = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    key = seal_record(
        GitHubCredentialProviderKey,
        {
            "profile": "github-credential-provider-key",
            "schema_version": "github-credential-provider-key/0.1.0",
            "provider_id": "fixture-provider",
            "key_id": "fixture-key",
            "algorithm": "Ed25519",
            "public_key": encoded,
            "public_key_sha256": sha256_bytes(raw),
            "valid_from": NOW,
            "valid_until": LATER,
            "status": "active",
            "created_at": NOW,
            "authority_effect": "none",
            "decision_effect": "none",
            "membership_effect": "none",
            "production_use_allowed": False,
        },
    )
    assert key.public_key == encoded
    with pytest.raises(PydanticValidationError):
        seal_record(
            GitHubCredentialProviderKey,
            {**key.model_dump(exclude={"content_hash"}), "public_key_sha256": H1},
        )


def test_authorization_is_one_read_with_exact_bounds() -> None:
    authorization = _authorization()
    assert authorization.authority_effect == "github_read_only"
    with pytest.raises(PydanticValidationError):
        _authorization(maximum_network_requests=3)
    with pytest.raises(PydanticValidationError):
        _authorization(path_parameters={"ref": "refs/heads/main", "extra": "x"})
    with pytest.raises(PydanticValidationError):
        _authorization(expires_at="2026-09-09T06:20:00Z")


def test_attempt_id_matches_frozen_canonical_preimage() -> None:
    values = _attempt_values()
    actual = compute_attempt_id(**values)
    preimage = {"schema_version": ATTEMPT_PREIMAGE_SCHEMA, **values}
    expected = (
        "attempt:sha256:"
        + hashlib.sha256(
            ATTEMPT_DOMAIN
            + json.dumps(preimage, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )
    assert actual == expected
    assert compute_attempt_id(**dict(reversed(tuple(values.items())))) == expected
    with pytest.raises(ValidationError):
        compute_attempt_id(**{**values, "maximum_pages": True})


def test_intent_rejects_attempt_substitution() -> None:
    intent = _intent()
    assert intent.attempt_id == compute_attempt_id(**_attempt_values())
    with pytest.raises(PydanticValidationError):
        _intent(attempt_id="attempt:sha256:" + "0" * 64)


def test_attempt_claim_is_exclusive_even_for_equal_bytes(tmp_path: Path) -> None:
    claim = _claim(_intent())
    path = write_attempt_claim(tmp_path, claim)
    assert path == attempt_claim_path(tmp_path, claim.attempt_id)
    assert (
        json.loads(path.read_text(encoding="utf-8"))["content_hash"]
        == claim.content_hash
    )
    with pytest.raises(IntegrityError, match="ATTEMPT_ALREADY_CLAIMED"):
        write_attempt_claim(tmp_path, claim)


def test_ordinary_durable_record_equal_retry_is_idempotent(tmp_path: Path) -> None:
    profile = _api_profile()
    path = tmp_path / "api.json"
    assert write_durable_record(path, profile) == (path, True)
    assert write_durable_record(path, profile) == (path, False)
    with pytest.raises(IntegrityError):
        write_durable_record(path, _api_profile(created_at="2026-09-09T06:00:01Z"))


def test_durable_admission_is_private_bound_and_single_use(tmp_path: Path) -> None:
    evidence = _api_profile()
    path = tmp_path / "evidence.json"
    admission = create_durable_lease_admission(
        evidence_path=path,
        evidence=evidence,
        attempt_id="attempt:sha256:" + "a" * 64,
        attempt_claim_hash=H1,
    )
    with pytest.raises(TypeError):
        DurableLeaseEvidenceAdmission(
            object(),
            evidence_path=path,
            evidence_hash=evidence.content_hash,
            attempt_id="attempt:sha256:" + "a" * 64,
            attempt_claim_hash=H1,
        )
    with pytest.raises(TypeError):
        pickle.dumps(admission)
    with pytest.raises(IntegrityError, match="LEASE_ADMISSION_INVALID"):
        admission.consume(
            evidence_path=path,
            evidence_hash=H2,
            attempt_id="attempt:sha256:" + "a" * 64,
            attempt_claim_hash=H1,
        )
    admission.consume(
        evidence_path=path,
        evidence_hash=evidence.content_hash,
        attempt_id="attempt:sha256:" + "a" * 64,
        attempt_claim_hash=H1,
    )
    with pytest.raises(IntegrityError, match="LEASE_ADMISSION_INVALID"):
        admission.consume(
            evidence_path=path,
            evidence_hash=evidence.content_hash,
            attempt_id="attempt:sha256:" + "a" * 64,
            attempt_claim_hash=H1,
        )


def test_workspace_creates_closed_github_record_directories(tmp_path: Path) -> None:
    workspace = Workspace.create(tmp_path, principal="arthur")
    directories = (
        workspace.github_repository_profiles_dir,
        workspace.github_api_profiles_dir,
        workspace.github_provider_keys_dir,
        workspace.github_authorizations_dir,
        workspace.github_intents_dir,
        workspace.github_attempt_claims_dir,
        workspace.github_lease_evidence_dir,
        workspace.github_observations_dir,
    )
    assert all(path.is_dir() for path in directories)


def _sign_model(
    model_type, values: dict, private_key: Ed25519PrivateKey, domain: bytes
):
    draft = model_type.model_validate({**values, "signature": "A" * 86})
    body = json.dumps(
        draft.model_dump(mode="json", exclude={"signature"}),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    signature = (
        base64.urlsafe_b64encode(private_key.sign(domain + body))
        .rstrip(b"=")
        .decode("ascii")
    )
    return model_type.model_validate({**values, "signature": signature})


class _PairValidator:
    def __init__(
        self, *, secret: bytes, expected_tag: str, claims: CredentialLeaseClaims
    ):
        self.secret = secret
        self.expected_tag = expected_tag
        self.claims = claims
        self.calls = 0
        self.closed = False

    def validate_pair_once(self, token: memoryview) -> CredentialLeaseClaims:
        self.calls += 1
        if self.calls != 1:
            raise GitHubFoundationFailure("LEASE_TOKEN_SUBSTITUTION")
        actual = hmac.new(self.secret, bytes(token), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(actual, self.expected_tag):
            raise GitHubFoundationFailure("LEASE_TOKEN_SUBSTITUTION")
        return self.claims

    def close(self) -> None:
        self.closed = True


class _FixtureProvider:
    provider_id = "fixture-provider"
    provider_version = "v1"

    def __init__(self, envelope: CredentialEnvelope):
        self.envelope = envelope
        self.calls = 0

    def resolve_once(self, request: CredentialResolutionRequest) -> CredentialEnvelope:
        self.calls += 1
        if self.calls != 1:
            raise GitHubFoundationFailure("INTENT_REPLAYED")
        return self.envelope


class _Clock:
    def __init__(self, *values: str):
        self.values = iter(values)

    def __call__(self) -> datetime:
        return datetime.strptime(next(self.values), "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )


def _credential_fixture(
    *, evidence_time: str = "2026-09-09T06:00:06Z", substitute_token: bool = False
):
    private_key = Ed25519PrivateKey.generate()
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    public_text = base64.urlsafe_b64encode(public_bytes).rstrip(b"=").decode("ascii")
    key = seal_record(
        GitHubCredentialProviderKey,
        {
            "profile": "github-credential-provider-key",
            "schema_version": "github-credential-provider-key/0.1.0",
            "provider_id": "fixture-provider",
            "key_id": "fixture-key",
            "algorithm": "Ed25519",
            "public_key": public_text,
            "public_key_sha256": sha256_bytes(public_bytes),
            "valid_from": "2026-09-09T05:59:00Z",
            "valid_until": "2026-09-09T07:00:00Z",
            "status": "active",
            "created_at": NOW,
            "authority_effect": "none",
            "decision_effect": "none",
            "membership_effect": "none",
            "production_use_allowed": False,
        },
    )
    repository = _repository_profile(
        provider_key_hash=key.content_hash,
        expected_provider_public_key_sha256=key.public_key_sha256,
    )
    api = _api_profile()
    authorization = _authorization(
        repository_profile=RecordReference(
            reference="github/repository-profiles/repo.json",
            content_hash=repository.content_hash,
        ),
        api_profile=RecordReference(
            reference="github/api-profiles/api.json", content_hash=api.content_hash
        ),
    )
    attempt_values = {
        **_attempt_values(),
        "authorization_hash": authorization.content_hash,
        "repository_profile_hash": repository.content_hash,
        "api_profile_hash": api.content_hash,
    }
    intent = _intent(
        authorization=RecordReference(
            reference="github/authorizations/auth.json",
            content_hash=authorization.content_hash,
        ),
        repository_profile=RecordReference(
            reference="github/repository-profiles/repo.json",
            content_hash=repository.content_hash,
        ),
        api_profile=RecordReference(
            reference="github/api-profiles/api.json", content_hash=api.content_hash
        ),
        attempt_id=compute_attempt_id(**attempt_values),
    )
    claim = _claim(intent)
    permission = _permissions(contents="read")
    request = CredentialResolutionRequest(
        provider_selector="fixture-provider",
        provider_id="fixture-provider",
        provider_versions=("v1",),
        repository_profile_hash=repository.content_hash,
        api_profile_hash=api.content_hash,
        provider_key_hash=key.content_hash,
        repository_id=101,
        account_id=202,
        app_id=303,
        installation_id=404,
        permission_envelope=permission,
        api_version="2026-03-10",
        authorization_hash=authorization.content_hash,
        intent_hash=intent.content_hash,
        intent_expiry=LATER,
        resolution_nonce_hash="sha256:" + "9" * 64,
    )
    token = bytearray(b"github-fixture-token-never-persist")
    provider_secret = b"provider-owned-fixture-secret"
    tag = hmac.new(provider_secret, bytes(token), hashlib.sha256).hexdigest()
    public_fields = {
        "provider_id": "fixture-provider",
        "provider_version": "v1",
        "key_id": "fixture-key",
        "lease_id": "lease-fixture-001",
        "credential_class": "github_app_installation_access_token",
        "app_id": 303,
        "installation_id": 404,
        "account_id": 202,
        "repository_ids": (101,),
        "repository_selection": "selected",
        "permissions": permission,
        "minted_at": "2026-09-09T06:00:01Z",
        "expires_at": LATER,
        "api_version": "2026-03-10",
        "repository_profile_hash": repository.content_hash,
        "api_profile_hash": api.content_hash,
        "authorization_hash": authorization.content_hash,
        "intent_hash": intent.content_hash,
        "resolution_nonce_hash": request.resolution_nonce_hash,
        "provider_receipt_validation_outcome": "pass",
        "provider_receipt_validation_at": "2026-09-09T06:00:02Z",
        "provider_authentication_scheme": "Ed25519",
        "provider_authentication_version": "conclave-github-lease-ed25519-v1",
        "provider_authentication_key_id": "fixture-key",
    }
    receipt = _sign_model(
        CredentialLeaseReceipt,
        {
            "schema_version": "github-credential-lease-receipt/0.1.0",
            **public_fields,
            "token_instance_tag": tag,
        },
        private_key,
        RECEIPT_SIGNATURE_DOMAIN,
    )
    claims = _sign_model(
        CredentialLeaseClaims,
        {
            "schema_version": "github-credential-lease-claims/0.1.0",
            **public_fields,
            "provider_pair_validation_outcome": "pass",
            "provider_pair_validation_at": "2026-09-09T06:00:04Z",
            "sanitized_transient_receipt_hash": sanitized_receipt_hash(receipt),
        },
        private_key,
        CLAIMS_SIGNATURE_DOMAIN,
    )
    validator = _PairValidator(secret=provider_secret, expected_tag=tag, claims=claims)
    actual_token = bytearray(b"substituted-token") if substitute_token else token
    envelope = CredentialEnvelope(
        token=actual_token, receipt=receipt, pair_validator=validator
    )
    provider = _FixtureProvider(envelope)
    clock = _Clock(
        "2026-09-09T06:00:03Z",
        "2026-09-09T06:00:04Z",
        "2026-09-09T06:00:05Z",
        evidence_time,
    )
    return {
        "provider": provider,
        "request": request,
        "repository_profile": repository,
        "api_profile": api,
        "provider_key": key,
        "authorization": authorization,
        "intent": intent,
        "attempt_claim": claim,
        "clock": clock,
        "validator": validator,
        "token": actual_token,
    }


def test_signed_credential_lease_is_durable_non_secret_and_cleans_up(
    tmp_path: Path,
) -> None:
    fixture = _credential_fixture()
    lease = prepare_credential_lease(
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
        attempt_claim_reference="github/attempt-claims/claim.json",
        authorization_reference="github/authorizations/auth.json",
        intent_reference="github/intents/intent.json",
        evidence_directory=tmp_path,
    )
    evidence_bytes = next(tmp_path.glob("lease-*.json")).read_bytes()
    assert bytes(fixture["token"]) not in evidence_bytes
    assert fixture["provider"].calls == 1
    assert fixture["validator"].calls == 1
    assert not fixture["validator"].closed
    lease.close()
    assert set(fixture["token"]) == {0}
    assert fixture["validator"].closed


def test_token_substitution_fails_before_admission_and_wipes_buffer(
    tmp_path: Path,
) -> None:
    fixture = _credential_fixture(substitute_token=True)
    with pytest.raises(GitHubFoundationFailure, match="LEASE_TOKEN_SUBSTITUTION"):
        prepare_credential_lease(
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
            attempt_claim_reference="github/attempt-claims/claim.json",
            authorization_reference="github/authorizations/auth.json",
            intent_reference="github/intents/intent.json",
            evidence_directory=tmp_path,
        )
    assert set(fixture["token"]) == {0}
    assert fixture["validator"].closed
    assert not list(tmp_path.glob("lease-*.json"))


def test_stale_credential_fails_and_wipes_after_pair_validation(tmp_path: Path) -> None:
    fixture = _credential_fixture(evidence_time="2026-09-09T06:08:31Z")
    with pytest.raises(GitHubFoundationFailure, match="LEASE_STALE"):
        prepare_credential_lease(
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
            attempt_claim_reference="github/attempt-claims/claim.json",
            authorization_reference="github/authorizations/auth.json",
            intent_reference="github/intents/intent.json",
            evidence_directory=tmp_path,
        )
    assert set(fixture["token"]) == {0}
    assert fixture["validator"].closed


def _prepare_fixture_lease(fixture: dict, directory: Path):
    return prepare_credential_lease(
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
        attempt_claim_reference="github/attempt-claims/claim.json",
        authorization_reference="github/authorizations/auth.json",
        intent_reference="github/intents/intent.json",
        evidence_directory=directory,
    )


def test_request_builder_owns_exact_route_query_and_headers() -> None:
    fixture = _credential_fixture()
    request = build_github_request(
        repository_profile=fixture["repository_profile"],
        api_profile=fixture["api_profile"],
        intent=fixture["intent"],
    )
    assert request.method == "GET"
    assert request.target == "/repos/komistry-labs/conclave/git/ref/heads%2Fmain"
    assert request.headers == (
        ("Accept", "application/vnd.github+json"),
        ("X-GitHub-Api-Version", "2026-03-10"),
        ("User-Agent", "conclave-github-adapter/21a"),
    )
    assert "Authorization" not in repr(request)


def test_paginated_request_is_rebuilt_not_followed_from_link() -> None:
    fixture = _credential_fixture()
    sha = "a" * 40
    attempt_values = {
        **_attempt_values(),
        "authorization_hash": fixture["authorization"].content_hash,
        "repository_profile_hash": fixture["repository_profile"].content_hash,
        "api_profile_hash": fixture["api_profile"].content_hash,
        "operation_key": "check_runs.list",
        "path_parameters": {"commit_sha": sha},
        "query_parameters": {"per_page": 100, "page": 1},
        "maximum_pages": 10,
        "maximum_items": 1000,
        "maximum_network_requests": 11,
    }
    intent = _intent(
        authorization=RecordReference(
            reference="github/authorizations/auth.json",
            content_hash=fixture["authorization"].content_hash,
        ),
        repository_profile=RecordReference(
            reference="github/repository-profiles/repo.json",
            content_hash=fixture["repository_profile"].content_hash,
        ),
        api_profile=RecordReference(
            reference="github/api-profiles/api.json",
            content_hash=fixture["api_profile"].content_hash,
        ),
        operation_key="check_runs.list",
        path_parameters={"commit_sha": sha},
        query_parameters={"per_page": 100, "page": 1},
        maximum_pages=10,
        maximum_items=1000,
        maximum_network_requests=11,
        attempt_id=compute_attempt_id(**attempt_values),
    )
    request = build_github_request(
        repository_profile=fixture["repository_profile"],
        api_profile=fixture["api_profile"],
        intent=intent,
        page=2,
    )
    assert request.target.endswith("/check-runs?per_page=100&page=2")


def test_request_builder_rejects_unallowlisted_ref() -> None:
    fixture = _credential_fixture()
    values = {
        **_attempt_values(),
        "authorization_hash": fixture["authorization"].content_hash,
        "repository_profile_hash": fixture["repository_profile"].content_hash,
        "api_profile_hash": fixture["api_profile"].content_hash,
        "path_parameters": {"ref": "refs/heads/unapproved"},
    }
    intent = _intent(
        authorization=RecordReference(
            reference="github/authorizations/auth.json",
            content_hash=fixture["authorization"].content_hash,
        ),
        repository_profile=RecordReference(
            reference="github/repository-profiles/repo.json",
            content_hash=fixture["repository_profile"].content_hash,
        ),
        api_profile=RecordReference(
            reference="github/api-profiles/api.json",
            content_hash=fixture["api_profile"].content_hash,
        ),
        path_parameters={"ref": "refs/heads/unapproved"},
        attempt_id=compute_attempt_id(**values),
    )
    with pytest.raises(GitHubFoundationFailure, match="PARAMETER_INVALID"):
        build_github_request(
            repository_profile=fixture["repository_profile"],
            api_profile=fixture["api_profile"],
            intent=intent,
        )


def test_fixture_transport_retries_once_before_headers_and_closes_lease(
    tmp_path: Path,
) -> None:
    fixture = _credential_fixture()
    lease = _prepare_fixture_lease(fixture, tmp_path)
    transport = FixtureGitHubTransport(
        [
            GitHubTransportFailure("TRANSPORT_CONNECT_FAILED", before_headers=True),
            GitHubTransportResponse(
                200, (("Content-Type", "application/json"),), b'{"ref":"fixture"}'
            ),
        ]
    )
    delays: list[float] = []
    responses = run_fixture_transport(
        lease=lease,
        transport=transport,
        repository_profile=fixture["repository_profile"],
        api_profile=fixture["api_profile"],
        intent=fixture["intent"],
        clock=_Clock(
            "2026-09-09T06:00:07Z", "2026-09-09T06:00:08Z", "2026-09-09T06:00:09Z"
        ),
        monotonic=lambda: 0.0,
        sleeper=delays.append,
    )
    assert len(responses) == 1
    assert len(transport.requests) == 2
    assert delays == [0.25]
    assert all(transport.token_was_present)
    assert set(fixture["token"]) == {0}
    assert fixture["validator"].closed


def test_fixture_transport_never_retries_after_headers(tmp_path: Path) -> None:
    fixture = _credential_fixture()
    lease = _prepare_fixture_lease(fixture, tmp_path)
    transport = FixtureGitHubTransport(
        [
            GitHubTransportFailure("TRANSPORT_CONNECTION_LOST", before_headers=False),
            GitHubTransportResponse(200, (), b"{}"),
        ]
    )
    with pytest.raises(GitHubFoundationFailure, match="TRANSPORT_CONNECTION_LOST"):
        run_fixture_transport(
            lease=lease,
            transport=transport,
            repository_profile=fixture["repository_profile"],
            api_profile=fixture["api_profile"],
            intent=fixture["intent"],
            clock=_Clock("2026-09-09T06:00:07Z", "2026-09-09T06:00:08Z"),
            monotonic=lambda: 0.0,
        )
    assert len(transport.requests) == 1
    assert set(fixture["token"]) == {0}


def test_production_https_transport_remains_unreachable_in_21a() -> None:
    with pytest.raises(GitHubFoundationFailure, match="ENDPOINT_NOT_ALLOWED"):
        create_production_https_transport(_repository_profile())


def _operation_intent(fixture: dict, operation_key: str, path_parameters: dict):
    spec = ENDPOINTS[operation_key]
    query_parameters = dict(spec.fixed_query)
    if spec.paginated:
        query_parameters.update({"per_page": 100, "page": 1})
    attempt_values = {
        **_attempt_values(),
        "authorization_hash": fixture["authorization"].content_hash,
        "repository_profile_hash": fixture["repository_profile"].content_hash,
        "api_profile_hash": fixture["api_profile"].content_hash,
        "operation_key": operation_key,
        "path_parameters": path_parameters,
        "query_parameters": query_parameters,
        "maximum_pages": spec.maximum_pages,
        "maximum_items": spec.maximum_items,
        "maximum_network_requests": spec.maximum_pages + 1,
    }
    return _intent(
        authorization=RecordReference(
            reference="github/authorizations/auth.json",
            content_hash=fixture["authorization"].content_hash,
        ),
        repository_profile=RecordReference(
            reference="github/repository-profiles/repo.json",
            content_hash=fixture["repository_profile"].content_hash,
        ),
        api_profile=RecordReference(
            reference="github/api-profiles/api.json",
            content_hash=fixture["api_profile"].content_hash,
        ),
        operation_key=operation_key,
        path_parameters=path_parameters,
        query_parameters=query_parameters,
        maximum_pages=spec.maximum_pages,
        maximum_items=spec.maximum_items,
        maximum_network_requests=spec.maximum_pages + 1,
        attempt_id=compute_attempt_id(**attempt_values),
    )


def test_bounded_json_rejects_duplicates_depth_and_non_finite() -> None:
    with pytest.raises(GitHubFoundationFailure, match="RESPONSE_JSON_INVALID"):
        parse_bounded_json(b'{"id":1,"id":2}', maximum_bytes=100)
    deep = b"[" * 17 + b"0" + b"]" * 17
    with pytest.raises(GitHubFoundationFailure, match="RESPONSE_JSON_INVALID"):
        parse_bounded_json(deep, maximum_bytes=100)
    with pytest.raises(GitHubFoundationFailure, match="RESPONSE_JSON_INVALID"):
        parse_bounded_json(b'{"value":NaN}', maximum_bytes=100)
    with pytest.raises(GitHubFoundationFailure, match="RESPONSE_BODY_TOO_LARGE"):
        parse_bounded_json(b"{}", maximum_bytes=1)


def test_repository_projection_is_factual_and_identity_bound() -> None:
    fixture = _credential_fixture()
    intent = _operation_intent(fixture, "repository.get", {})
    raw = {
        "id": 101,
        "node_id": "R_fixture",
        "name": "conclave",
        "full_name": "komistry-labs/conclave",
        "owner": {"id": 202, "node_id": "O_fixture", "login": "discarded"},
        "private": True,
        "archived": False,
        "disabled": False,
        "visibility": "private",
        "default_branch": "main",
        "allow_merge_commit": True,
        "allow_squash_merge": True,
        "allow_rebase_merge": False,
        "html_url": "discarded",
    }
    result = project_github_json(
        operation_key="repository.get",
        value=raw,
        repository=fixture["repository_profile"],
        intent=intent,
    )
    assert result.complete and result.identity_match
    assert "html_url" not in result.normalized
    mismatch = project_github_json(
        operation_key="repository.get",
        value={**raw, "id": 999},
        repository=fixture["repository_profile"],
        intent=intent,
    )
    assert not mismatch.complete and not mismatch.identity_match
    assert mismatch.reason_codes == ("REPOSITORY_IDENTITY_MISMATCH",)


def test_check_projection_sorts_hashes_text_and_marks_unknown_enum() -> None:
    fixture = _credential_fixture()
    sha = "a" * 40
    intent = _operation_intent(fixture, "check_runs.list", {"commit_sha": sha})
    raw = {
        "total_count": 2,
        "check_runs": [
            {
                "id": 2,
                "name": "Windows",
                "head_sha": sha,
                "status": "completed",
                "conclusion": "success",
                "app": {"id": 7},
                "started_at": None,
                "completed_at": NOW,
            },
            {
                "id": 1,
                "name": "Linux",
                "head_sha": sha,
                "status": "future_state",
                "conclusion": None,
                "app": None,
                "started_at": None,
                "completed_at": None,
            },
        ],
    }
    result = project_github_json(
        operation_key="check_runs.list",
        value=raw,
        repository=fixture["repository_profile"],
        intent=intent,
    )
    assert [item["id"] for item in result.normalized["check_runs"]] == [1, 2]
    assert "name" not in result.normalized["check_runs"][0]
    assert result.visibility == "complete_within_github_check_suite_horizon"
    assert result.reason_codes == ("UNKNOWN_SECURITY_STATE",)
    assert "future_state" not in json.dumps(result.normalized)
    assert not result.complete


def test_branch_protection_unknown_security_field_is_hashed_not_discarded() -> None:
    fixture = _credential_fixture()
    intent = _operation_intent(fixture, "branch_protection.get", {"branch": "main"})
    raw = {
        "enforce_admins": {"enabled": True, "url": "discarded"},
        "required_signatures": {"enabled": True},
        "future_security_gate": {"enabled": True, "secret_text": "not retained"},
    }
    result = project_github_json(
        operation_key="branch_protection.get",
        value=raw,
        repository=fixture["repository_profile"],
        intent=intent,
    )
    assert result.reason_codes == ("UNKNOWN_SECURITY_STATE",)
    assert not result.complete
    assert result.normalized["security_extension_hash"].startswith("sha256:")
    assert "future_security_gate" not in json.dumps(result.normalized)


def test_review_projection_sorts_and_excludes_body() -> None:
    fixture = _credential_fixture()
    intent = _operation_intent(fixture, "reviews.list", {"pull_number": 12})
    raw = [
        {
            "id": 2,
            "user": None,
            "state": "COMMENTED",
            "submitted_at": None,
            "commit_id": None,
            "body": "discard me",
        },
        {
            "id": 1,
            "user": {"id": 9, "type": "User", "login": "discarded"},
            "state": "APPROVED",
            "submitted_at": NOW,
            "commit_id": "a" * 40,
            "body": "discard me too",
        },
    ]
    result = project_github_json(
        operation_key="reviews.list",
        value=raw,
        repository=fixture["repository_profile"],
        intent=intent,
    )
    assert [item["id"] for item in result.normalized["items"]] == [1, 2]
    assert "body" not in json.dumps(result.normalized)
    assert result.complete


def test_observation_is_hash_bound_non_authoritative_and_immutable(
    tmp_path: Path,
) -> None:
    fixture = _credential_fixture()
    lease = _prepare_fixture_lease(fixture, tmp_path / "lease")
    raw = {
        "ref": "refs/heads/main",
        "node_id": "REF_fixture",
        "object": {"sha": "a" * 40, "type": "commit"},
    }
    body = json.dumps(raw, separators=(",", ":")).encode()
    response = GitHubTransportResponse(
        200,
        (
            ("X-RateLimit-Limit", "5000"),
            ("X-RateLimit-Remaining", "4999"),
            ("X-RateLimit-Reset", "1788937200"),
            ("X-RateLimit-Resource", "core"),
        ),
        body,
    )
    projection = project_github_json(
        operation_key="ref.get",
        value=parse_bounded_json(body, maximum_bytes=2_097_152),
        repository=fixture["repository_profile"],
        intent=fixture["intent"],
    )
    observation = create_success_observation(
        observation_id="01890f3e-7b1a-7cc2-8b4f-8f2e9c90a113",
        observed_at="2026-09-09T06:00:10Z",
        responses=(response,),
        repository_profile=fixture["repository_profile"],
        api_profile=fixture["api_profile"],
        authorization=fixture["authorization"],
        intent=fixture["intent"],
        attempt_claim=fixture["attempt_claim"],
        lease_evidence=lease.evidence,
        projection=projection,
    )
    assert observation.complete
    assert observation.authority_effect == "none"
    assert not observation.merge_authorized and not observation.action_execution_allowed
    path = (
        tmp_path
        / "observations"
        / f"observation-{observation.content_hash.removeprefix('sha256:')}.json"
    )
    assert write_durable_record(path, observation) == (path, True)
    assert (
        json.loads(path.read_text(encoding="utf-8"))["content_hash"]
        == observation.content_hash
    )
    lease.close()


def test_governed_coordinator_seals_complete_chain_and_safe_ledger(
    tmp_path: Path,
) -> None:
    fixture = _credential_fixture()
    workspace = Workspace.create(tmp_path / "workspace", principal="arthur")
    initialise_ledger(workspace, workspace.load_config())
    raw = {
        "ref": "refs/heads/main",
        "node_id": "REF_fixture",
        "object": {"sha": "a" * 40, "type": "commit"},
    }
    transport = FixtureGitHubTransport(
        [
            GitHubTransportResponse(
                200,
                (("Content-Type", "application/json"),),
                json.dumps(raw, separators=(",", ":")).encode(),
            )
        ]
    )
    clock = _Clock(
        "2026-09-09T06:00:00Z",
        "2026-09-09T06:00:03Z",
        "2026-09-09T06:00:04Z",
        "2026-09-09T06:00:05Z",
        "2026-09-09T06:00:06Z",
        "2026-09-09T06:00:07Z",
        "2026-09-09T06:00:08Z",
        "2026-09-09T06:00:10Z",
    )
    result = execute_github_read(
        workspace=workspace,
        repository_profile=fixture["repository_profile"],
        api_profile=fixture["api_profile"],
        provider_key=fixture["provider_key"],
        authorization=fixture["authorization"],
        intent=fixture["intent"],
        attempt_claim=fixture["attempt_claim"],
        request=fixture["request"],
        provider=fixture["provider"],
        transport=transport,
        observation_id="01890f3e-7b1a-7cc2-8b4f-8f2e9c90a113",
        clock=clock,
        monotonic=lambda: 0.0,
    )
    assert result.observation is not None and result.observation.complete
    assert result.observation_path is not None and result.observation_path.is_file()
    assert result.ledger_event_created
    assert len(transport.requests) == 1
    assert set(fixture["token"]) == {0}
    event = read_events(workspace)[-1]
    assert event["event_type"] == "github_read_observation_recorded"
    serialized = json.dumps(event, sort_keys=True)
    assert "api.github.com" not in serialized
    assert "refs/heads/main" not in serialized
    assert "lease-fixture-001" not in serialized


def test_coordinator_rejects_wrong_principal_before_claim_provider_or_transport(
    tmp_path: Path,
) -> None:
    fixture = _credential_fixture()
    workspace = Workspace.create(tmp_path / "workspace", principal="not-arthur")
    transport = FixtureGitHubTransport([])
    result = execute_github_read(
        workspace=workspace,
        repository_profile=fixture["repository_profile"],
        api_profile=fixture["api_profile"],
        provider_key=fixture["provider_key"],
        authorization=fixture["authorization"],
        intent=fixture["intent"],
        attempt_claim=fixture["attempt_claim"],
        request=fixture["request"],
        provider=fixture["provider"],
        transport=transport,
        observation_id="01890f3e-7b1a-7cc2-8b4f-8f2e9c90a113",
        clock=_Clock("2026-09-09T06:00:00Z"),
        monotonic=lambda: 0.0,
    )
    assert result.diagnostic == {
        "operation_key": "ref.get",
        "reason_code": "AUTHORIZATION_INVALID",
    }
    assert result.observation is None
    assert fixture["provider"].calls == 0
    assert transport.requests == []
    assert not list(workspace.github_attempt_claims_dir.iterdir())


def test_coordinator_crash_retained_claim_blocks_replay_before_second_provider_call(
    tmp_path: Path,
) -> None:
    fixture = _credential_fixture()
    workspace = Workspace.create(tmp_path / "workspace", principal="arthur")
    write_attempt_claim(workspace.github_attempt_claims_dir, fixture["attempt_claim"])
    with pytest.raises(IntegrityError, match="ATTEMPT_ALREADY_CLAIMED"):
        execute_github_read(
            workspace=workspace,
            repository_profile=fixture["repository_profile"],
            api_profile=fixture["api_profile"],
            provider_key=fixture["provider_key"],
            authorization=fixture["authorization"],
            intent=fixture["intent"],
            attempt_claim=fixture["attempt_claim"],
            request=fixture["request"],
            provider=fixture["provider"],
            transport=FixtureGitHubTransport([]),
            observation_id="01890f3e-7b1a-7cc2-8b4f-8f2e9c90a113",
            clock=_Clock("2026-09-09T06:00:00Z"),
            monotonic=lambda: 0.0,
        )
    assert fixture["provider"].calls == 0


def test_remaining_endpoint_projection_contracts() -> None:
    fixture = _credential_fixture()
    repository = fixture["repository_profile"]
    sha = "a" * 40
    other = "b" * 40

    cases = [
        ("repository_hash_algorithm.get", {}, {"hash_algorithm": "sha1"}),
        (
            "commit.get",
            {"commit_sha": sha},
            {
                "sha": sha,
                "node_id": "C_fixture",
                "tree": {"sha": other},
                "parents": [{"sha": other}],
                "verification": {
                    "verified": True,
                    "reason": "valid",
                    "verified_at": NOW,
                },
            },
        ),
        (
            "pull_request.get",
            {"pull_number": 7},
            {
                "id": 70,
                "number": 7,
                "state": "open",
                "draft": False,
                "merged": False,
                "mergeable": None,
                "mergeable_state": "unknown",
                "user": {"id": 9, "type": "User"},
                "head": {"sha": sha, "ref": "feature", "repo": None},
                "base": {"sha": other, "ref": "main", "repo": {"id": 101}},
                "created_at": NOW,
                "updated_at": NOW,
                "closed_at": None,
                "merged_at": None,
            },
        ),
        (
            "combined_status.get",
            {"commit_sha": sha},
            {
                "sha": sha,
                "state": "success",
                "total_count": 1,
                "statuses": [
                    {
                        "id": 3,
                        "context": "ci",
                        "state": "success",
                        "creator": None,
                        "updated_at": NOW,
                    }
                ],
            },
        ),
        (
            "issue_comments.list",
            {"pull_number": 7},
            [
                {
                    "id": 3,
                    "user": None,
                    "created_at": NOW,
                    "updated_at": NOW,
                    "minimized": None,
                    "body": "discarded",
                }
            ],
        ),
        (
            "review_comments.list",
            {"pull_number": 7},
            [
                {
                    "id": 3,
                    "pull_request_review_id": None,
                    "in_reply_to_id": None,
                    "user": None,
                    "path": "src/module.py",
                    "commit_id": sha,
                    "original_commit_id": None,
                    "created_at": NOW,
                    "updated_at": NOW,
                    "body": "discarded",
                }
            ],
        ),
        (
            "branch_rules.list",
            {"branch": "main"},
            [
                {
                    "type": "required_signatures",
                    "ruleset_source_type": "Repository",
                    "ruleset_source": "komistry-labs/conclave",
                    "ruleset_id": 5,
                    "parameters": None,
                }
            ],
        ),
        (
            "repository_rulesets.list",
            {},
            [
                {
                    "id": 5,
                    "node_id": "RS_fixture",
                    "source_type": "Repository",
                    "source": "komistry-labs/conclave",
                    "enforcement": "active",
                    "created_at": NOW,
                    "updated_at": NOW,
                    "target": None,
                }
            ],
        ),
        (
            "repository_ruleset.get",
            {"ruleset_id": 5},
            {
                "id": 5,
                "node_id": "RS_fixture",
                "source_type": "Repository",
                "source": "komistry-labs/conclave",
                "enforcement": "active",
                "created_at": NOW,
                "updated_at": NOW,
                "target": "branch",
                "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"]}},
                "rules": [{"type": "required_signatures", "parameters": None}],
            },
        ),
    ]
    for operation, parameters, raw in cases:
        intent = _operation_intent(fixture, operation, parameters)
        result = project_github_json(
            operation_key=operation,
            value=raw,
            repository=repository,
            intent=intent,
        )
        assert result.identity_match
        assert "discarded" not in json.dumps(result.normalized)
        assert result.observation_kind


def test_required_nullable_key_must_not_be_omitted() -> None:
    fixture = _credential_fixture()
    intent = _operation_intent(fixture, "reviews.list", {"pull_number": 7})
    raw = [{"id": 1, "user": None, "state": "APPROVED", "submitted_at": None}]
    with pytest.raises(GitHubFoundationFailure, match="RESPONSE_PROJECTION_INVALID"):
        project_github_json(
            operation_key="reviews.list",
            value=raw,
            repository=fixture["repository_profile"],
            intent=intent,
        )


def test_multi_page_projection_combines_deterministically_with_page_counts() -> None:
    fixture = _credential_fixture()
    sha = "a" * 40
    intent = _operation_intent(fixture, "check_runs.list", {"commit_sha": sha})

    def page(item_id: int, name: str) -> bytes:
        return json.dumps(
            {
                "total_count": 2,
                "check_runs": [
                    {
                        "id": item_id,
                        "name": name,
                        "head_sha": sha,
                        "status": "completed",
                        "conclusion": "success",
                        "app": None,
                        "started_at": None,
                        "completed_at": NOW,
                    }
                ],
            },
            separators=(",", ":"),
        ).encode()

    responses = (
        GitHubTransportResponse(200, (), page(2, "Windows")),
        GitHubTransportResponse(200, (), page(1, "Linux")),
    )
    bundle = project_github_responses(
        responses=responses,
        operation_key="check_runs.list",
        repository=fixture["repository_profile"],
        intent=intent,
        maximum_page_bytes=2_097_152,
    )
    assert bundle.page_item_counts == (1, 1)
    assert [item["id"] for item in bundle.projection.normalized["check_runs"]] == [1, 2]
    assert bundle.projection.complete


def test_failure_observation_and_diagnostic_are_closed_and_non_authoritative(
    tmp_path: Path,
) -> None:
    fixture = _credential_fixture()
    lease = _prepare_fixture_lease(fixture, tmp_path / "lease")
    response = GitHubTransportResponse(
        403,
        (("Retry-After", "secret-value-not-retained"),),
        b'{"message":"untrusted body"}',
    )
    observation = create_failure_observation(
        observation_id="01890f3e-7b1a-7cc2-8b4f-8f2e9c90a114",
        observed_at="2026-09-09T06:00:11Z",
        reason_codes=("RATE_LIMITED",),
        status_class="4xx",
        responses=(response,),
        repository_profile=fixture["repository_profile"],
        api_profile=fixture["api_profile"],
        authorization=fixture["authorization"],
        intent=fixture["intent"],
        attempt_claim=fixture["attempt_claim"],
        lease_evidence=lease.evidence,
    )
    encoded = json.dumps(observation.model_dump(mode="json"))
    assert not observation.complete and not observation.identity_match
    assert observation.reason_codes == ("RATE_LIMITED",)
    assert "secret-value-not-retained" not in encoded
    assert "untrusted body" not in encoded
    assert safe_failure_diagnostic(
        operation_key="ref.get", reason_code="RATE_LIMITED"
    ) == {"operation_key": "ref.get", "reason_code": "RATE_LIMITED"}
    with pytest.raises(GitHubFoundationFailure):
        safe_failure_diagnostic(operation_key="ref.get", reason_code="TOKEN=secret")
    lease.close()
