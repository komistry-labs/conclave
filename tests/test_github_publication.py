from __future__ import annotations

import hashlib
import base64
import json
import os
import shutil
import subprocess
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import pytest
from pydantic import ValidationError

from conclave.github_publication import (
    RecursiveTreeEntry,
    RequestBudget,
    apply_proposal,
    canonical_repository_path,
    canonical_github_ref_target,
    git_blob_oid,
    git_commit_oid,
    git_object_oid,
    proposal_blobs,
    reconstruct_tree_oid,
    verify_proposal_blobs,
    proposal_repository_path,
    validate_head_ref,
    build_recursive_tree_source_request,
    project_recursive_tree_source,
    BaseTreeClosure,
    BaseTreeIdentityObservation,
    RecursiveTreeObservation,
    canonical_closure_entries_bytes,
    read_artifacts_once,
    INCREMENT_21_PROTOCOL_HASH,
    STAGE_21A_PROTOCOL_HASH,
    STAGE_21B_PROTOCOL_HASH,
    STAGE_21B_ERRATUM_HASH,
    RecursiveTreeAuthorization,
    RecursiveTreeIntent,
    RecursiveTreeAttemptClaim,
    RecursiveTreeLeaseEvidence,
)
from conclave.github_foundation import (
    CLAIMS_SIGNATURE_DOMAIN,
    ENDPOINTS,
    RECEIPT_SIGNATURE_DOMAIN,
    CredentialLeaseClaims,
    CredentialLeaseEvidence,
    CredentialLeaseReceipt,
    GitHubCredentialProviderKey,
    GitHubOperationAttemptClaim,
    GitHubOperationAuthorization,
    GitHubOperationIntent,
    LeasePublicFields,
    PermissionEnvelope,
    RecordReference,
    write_durable_record,
    GitHubTransportResponse,
    GitHubObservation,
    ObservationPage,
    SafeRateLimitProjection,
    compute_attempt_id,
    sanitized_receipt_hash,
)
from test_github_foundation import _api_profile, _repository_profile, _sign_model
from conclave.models import TaskPacket
from conclave.taskpacket import seal as seal_task
from conclave.handoff import HandoffPacket, seal_handoff
from conclave.scope import evaluate as evaluate_scope
from conclave.github_publication_engine import (
    FixtureTranscriptEntry,
    OfflinePublicationTranscript,
    RateBudgetObservation,
    admit_rate_budget,
    build_exact_publication_dispatches,
    evaluate_governed_publication,
    rate_scope_hash,
)
from conclave.github_publication_records import (
    AuthenticatedRateBudgetObservation,
    CommitIdentity,
    OperationIntentV2,
    ProposalFile,
    ProposalManifest,
    PublicationAttemptClaim,
    PublicationAuthorization,
    PublicationGovernanceChain,
    PublicationIntent,
    PublicationLeaseEvidence,
    PublicationLeaseClaims,
    PUBLICATION_LEASE_CLAIMS_DOMAIN,
    PublicationPlan,
    Stage21AObservationEvidence,
    proposal_aggregate_hash,
    publication_attempt_id,
)
from conclave.identity import seal_record, sha256_bytes
from conclave import ledger
from conclave.workspace import Workspace


def entry(path: str, mode: str, kind: str, oid: str) -> RecursiveTreeEntry:
    return RecursiveTreeEntry(path=path, mode=mode, type=kind, oid=oid)


@pytest.mark.parametrize(
    ("fmt", "empty_blob", "empty_tree"),
    [
        (
            "sha1",
            "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
            "4b825dc642cb6eb9a060e54bf8d69288fbee4904",
        ),
        (
            "sha256",
            "473a0f4c3be8a93681a267e3b1e9a7dcda1185436fe141f7749120a303721813",
            "6ef19b41225c5369f1c104d45d8d85efa9b057b53b14b4b9b939dd74decc5321",
        ),
    ],
)
def test_empty_git_vectors(fmt: str, empty_blob: str, empty_tree: str) -> None:
    assert git_blob_oid(b"", fmt) == empty_blob
    assert reconstruct_tree_oid((), fmt) == empty_tree


def test_recursive_tree_source_is_closed_one_request_zero_retry() -> None:
    root = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    request = build_recursive_tree_source_request(
        owner="komistry-labs",
        repository="conclave",
        tree_oid=root,
        object_format="sha1",
    )
    assert (
        request.target == f"/repos/komistry-labs/conclave/git/trees/{root}?recursive=1"
    )
    assert request.maximum_network_requests == 1
    assert request.maximum_retries == 0
    assert (
        project_recursive_tree_source(
            {"sha": root, "truncated": False, "tree": [], "ignored_url": "secret"},
            root_tree_oid=root,
            object_format="sha1",
        )
        == ()
    )
    with pytest.raises(ValueError, match="incomplete"):
        project_recursive_tree_source(
            {"sha": root, "truncated": True, "tree": []},
            root_tree_oid=root,
            object_format="sha1",
        )


def test_nested_tree_reconstruction_and_overlay() -> None:
    readme = git_blob_oid(b"base\n", "sha1")
    nested = git_blob_oid(b"nested\n", "sha1")
    docs_oid = git_object_oid(
        "tree", b"100644 guide.txt\0" + bytes.fromhex(nested), "sha1"
    )
    rows = (
        entry("README.md", "100644", "blob", readme),
        entry("docs", "040000", "tree", docs_oid),
        entry("docs/guide.txt", "100644", "blob", nested),
    )
    root_payload = (
        b"100644 README.md\0"
        + bytes.fromhex(readme)
        + b"40000 docs\0"
        + bytes.fromhex(docs_oid)
    )
    # Git's tree mode is serialized without the leading zero.
    expected_root = git_object_oid("tree", root_payload, "sha1")
    assert reconstruct_tree_oid(rows, "sha1") == expected_root
    proposal = proposal_blobs({"docs/new.txt": b"new\n"}, "sha1")
    assert apply_proposal(rows, proposal, "sha1") != expected_root
    assert reconstruct_tree_oid(rows, "sha1") == expected_root


@pytest.mark.parametrize("object_format", ["sha1", "sha256"])
def test_git_independently_confirms_modes_prefix_and_non_ascii_order(
    tmp_path, object_format
) -> None:
    if shutil.which("git") is None:
        pytest.skip("Git executable unavailable for independent vector")
    repo = tmp_path / object_format
    subprocess.run(
        ["git", "init", f"--object-format={object_format}", str(repo)],
        check=True,
        capture_output=True,
    )
    blob = (
        subprocess.run(
            ["git", "-C", str(repo), "hash-object", "-w", "--stdin"],
            input=b"",
            check=True,
            capture_output=True,
        )
        .stdout.decode()
        .strip()
    )
    tree = (
        subprocess.run(
            ["git", "-C", str(repo), "hash-object", "-w", "-t", "tree", "--stdin"],
            input=b"",
            check=True,
            capture_output=True,
        )
        .stdout.decode()
        .strip()
    )
    commit = "1" * (40 if object_format == "sha1" else 64)
    rows = tuple(
        sorted(
            (
                entry("alpha", "100644", "blob", blob),
                entry("alpha.beta", "040000", "tree", tree),
                entry("link", "120000", "blob", blob),
                entry("run", "100755", "blob", blob),
                entry("sub", "160000", "commit", commit),
                entry("é.txt", "100644", "blob", blob),
            ),
            key=lambda item: item.path,
        )
    )
    mktree = "".join(
        f"{item.mode} {item.type} {item.oid}\t{item.path}\n" for item in rows
    ).encode("utf-8")
    expected = (
        subprocess.run(
            ["git", "-C", str(repo), "mktree", "--missing"],
            input=mktree,
            check=True,
            capture_output=True,
        )
        .stdout.decode()
        .strip()
    )
    assert reconstruct_tree_oid(rows, object_format) == expected


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/x",
        "a\\b",
        "a//b",
        "a/../b",
        "a/%2e/b",
        "NUL.txt",
        "trail. ",
        "decomposed-e\u0301.txt",
        "a/" + "b" * 257,
    ],
)
def test_ambiguous_paths_fail_closed(path: str) -> None:
    with pytest.raises(ValueError):
        canonical_repository_path(path)


def test_entry_set_rejects_missing_parent_wrong_oid_and_unknown_field() -> None:
    blob = git_blob_oid(b"x", "sha1")
    with pytest.raises(ValueError, match="missing"):
        reconstruct_tree_oid((entry("a/b", "100644", "blob", blob),), "sha1")
    with pytest.raises(ValueError, match="subtree"):
        reconstruct_tree_oid(
            (
                entry("a", "040000", "tree", "0" * 40),
                entry("a/b", "100644", "blob", blob),
            ),
            "sha1",
        )
    with pytest.raises(ValidationError):
        RecursiveTreeEntry(
            path="x", mode="100644", type="blob", oid=blob, surprise=True
        )


def test_proposal_metadata_is_bound_to_exact_bytes() -> None:
    rows = proposal_blobs({"a.txt": b"alpha"}, "sha1")
    verify_proposal_blobs({"a.txt": b"alpha"}, rows, "sha1")
    with pytest.raises(ValueError, match="metadata"):
        verify_proposal_blobs({"a.txt": b"beta"}, rows, "sha1")
    with pytest.raises(ValueError, match="collide"):
        proposal_blobs({"A.txt": b"a", "a.txt": b"b"}, "sha1")


def test_overlay_rejects_base_case_collision_and_non_regular_replacement() -> None:
    blob = git_blob_oid(b"base", "sha1")
    proposal = proposal_blobs({"a.txt": b"new"}, "sha1")
    with pytest.raises(ValueError, match="case folding"):
        apply_proposal((entry("A.txt", "100644", "blob", blob),), proposal, "sha1")
    with pytest.raises(ValueError, match="regular"):
        apply_proposal((entry("a.txt", "100755", "blob", blob),), proposal, "sha1")


def test_commit_oid_matches_independent_payload() -> None:
    tree = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    parent = "1" * 40
    actual = git_commit_oid(
        tree_oid=tree,
        parent_oid=parent,
        name="Conclave",
        email="bot@example.invalid",
        timestamp="2026-01-02T03:04:05Z",
        message="proposal\n",
        object_format="sha1",
    )
    stamp = 1767323045
    ident = f"Conclave <bot@example.invalid> {stamp} +0000"
    payload = f"tree {tree}\nparent {parent}\nauthor {ident}\ncommitter {ident}\n\nproposal\n".encode()
    expected = hashlib.sha1(
        b"commit " + str(len(payload)).encode() + b"\0" + payload
    ).hexdigest()
    assert actual == expected


def test_request_budget_is_bounded_monotonic_and_never_retries() -> None:
    budget = RequestBudget(file_count=3, observed_remaining=30)
    assert budget.remaining == 20
    budget.admit_dispatch(still_possible_after=19)
    assert budget.remaining == 19
    budget.observe(27)
    budget.observe(
        999
    )  # apparently increasing server evidence cannot enlarge admission
    with pytest.raises(ValueError, match="RATE_LIMITED"):
        budget.observe(26, retry_after=True)
    with pytest.raises(ValueError, match="INSUFFICIENT"):
        RequestBudget(file_count=3, observed_remaining=29)


def test_rate_budget_observation_requires_fresh_complete_scoped_evidence() -> None:
    ref = {"reference": "github/evidence/x.json", "content_hash": "sha256:" + "5" * 64}
    observation = seal_record(
        RateBudgetObservation,
        {
            "source_observation": ref,
            "repository_profile": ref,
            "api_profile": ref,
            "repository_id": 1,
            "account_id": 2,
            "app_id": 3,
            "installation_id": 4,
            "provider_id": "fixture-provider",
            "provider_version": "v1",
            "provider_key": ref,
            "provider_public_key_sha256": "sha256:" + "6" * 64,
            "api_version": "2026-03-10",
            "resource_bucket": "core",
            "limit": 5000,
            "remaining": 30,
            "reset_at": None,
            "retry_after_present": False,
            "observed_at": "2026-09-10T00:00:00Z",
            "created_at": "2026-09-10T00:00:00Z",
        },
    )
    assert (
        admit_rate_budget(
            observation, file_count=1, now="2026-09-10T00:01:00Z"
        ).remaining
        == 16
    )
    with pytest.raises(ValueError, match="RATE_LIMIT_EVIDENCE_INVALID"):
        admit_rate_budget(observation, file_count=1, now="2026-09-10T00:01:01Z")


@pytest.mark.parametrize(
    "path",
    [
        ".github/workflows/ci.yml",
        "CODEOWNERS",
        "docs/CODEOWNERS",
        ".gitmodules",
        ".gitattributes",
        ".gitignore",
        ".env.local",
        "secret.pem",
        "docs/governance/x.md",
        "architecture/decisions/ADR-1.md",
        "adr/x.md",
        "docs/KOS-state.md",
        "config/branch-protection.json",
    ],
)
def test_proposal_control_paths_are_non_overridable(path: str) -> None:
    with pytest.raises(ValueError, match="prohibited|control"):
        proposal_repository_path(path)


def test_head_ref_convention_is_exact() -> None:
    valid = "refs/heads/conclave/01890f3e-7b1a-7cc2-8b4f-8f2e9c90a113/my-change"
    assert validate_head_ref(valid) == valid
    for invalid in (
        valid.upper(),
        valid + ".lock",
        valid.replace("my-change", "my--change"),
        "refs/heads/feature/x",
    ):
        with pytest.raises(ValueError):
            validate_head_ref(invalid)


class Loopback:
    fixture_and_loopback_only = True

    def __init__(self, remaining: int = 40, fail_at: int | None = None):
        self.remaining = remaining
        self.fail_at = fail_at
        self.scope_hash = ""
        self._rows = ()

    def prepare(self, chain, rate, artifacts):
        self._rows = build_exact_publication_dispatches(
            chain.manifest, chain.repository_profile_record, artifacts
        )
        if not self.scope_hash:
            self.scope_hash = rate_scope_hash(rate)
        self._manifest = chain.manifest
        self._artifacts = artifacts
        return OfflinePublicationTranscript(
            entries=tuple(
                FixtureTranscriptEntry(
                    planned_request_hash=dispatch.request_hash,
                    response=self.response_for(dispatch),
                )
                for dispatch in self._rows
            )
        )

    def __len__(self):
        return len(self._rows)

    def response_for(self, dispatch):
        self.remaining -= 1
        expected = dispatch.expected_projection
        key = dispatch.operation_key
        wrong_oid = "0" * (40 if self._manifest.object_format == "sha1" else 64)
        if key == "repository.get":
            raw = {
                "id": expected["repository_id"],
                "owner": {"id": expected["account_id"]},
            }
        elif key in {
            "git_blob.create",
            "git_blob.get",
            "git_tree.create",
            "git_tree.get",
        }:
            raw = {"sha": expected["oid"]}
        elif key in {"git_commit.create", "commit.get"}:
            raw = {
                "sha": expected["oid"],
                "tree": {"sha": expected["tree_oid"]},
                "parents": [{"sha": expected["parents"][0]}],
            }
        elif key in {"ref.get", "git_ref.create"}:
            raw = {"ref": expected["ref"], "object": {"sha": expected["oid"]}}
        elif key in {"matching_refs.list", "pull_requests.matching.list"}:
            raw = []
        elif key in {"pull_request.create", "pull_request.get"}:
            raw = {
                "number": 7,
                "title": self._artifacts[
                    self._manifest.pull_request_title.reference
                ].decode(),
                "body": self._artifacts[
                    self._manifest.pull_request_body.reference
                ].decode(),
                "head": {
                    "ref": self._manifest.head_ref.removeprefix("refs/heads/"),
                    "sha": self._manifest.proposal_commit_oid,
                    "repo": {"id": self._manifest.repository_id},
                },
                "base": {
                    "ref": self._manifest.base_ref.removeprefix("refs/heads/"),
                    "sha": self._manifest.base_commit_oid,
                    "repo": {"id": self._manifest.repository_id},
                },
            }
        else:
            raise AssertionError(key)
        if dispatch.ordinal == self.fail_at:
            if key == "repository.get":
                raw["id"] += 1
            elif key in {
                "git_blob.create",
                "git_blob.get",
                "git_tree.create",
                "git_tree.get",
            }:
                raw["sha"] = wrong_oid
            elif key in {"git_commit.create", "commit.get"}:
                raw["sha"] = wrong_oid
            elif key in {"ref.get", "git_ref.create"}:
                raw["object"]["sha"] = wrong_oid
            elif key == "matching_refs.list":
                raw = [{"ref": self._manifest.head_ref, "object": {"sha": wrong_oid}}]
            elif key == "pull_requests.matching.list":
                raw = [{"number": 99}]
            else:
                raw["number"] = 8
        headers = (
            ("X-RateLimit-Remaining", str(self.remaining)),
            ("X-RateLimit-Limit", "5000"),
            ("X-RateLimit-Resource", "core"),
        )
        return GitHubTransportResponse(
            status=201 if key.endswith(".create") else 200,
            headers=headers,
            body=json.dumps(raw, separators=(",", ":")).encode(),
        )


def _fixture_placeholder_bytes(name: str) -> bytes:
    return (json.dumps({"fixture_record": name}, sort_keys=True) + "\n").encode()


def _rr(name: str, record=None, digest: str | None = None) -> RecordReference:
    return RecordReference(
        reference=f"github/fixture/{name}.json",
        content_hash=(
            record.content_hash
            if record is not None
            else (
                digest
                or "sha256:"
                + hashlib.sha256(_fixture_placeholder_bytes(name)).hexdigest()
            )
        ),
    )


def _stage21a_fixture_context(created: str):
    private_key = Ed25519PrivateKey.generate()
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    public_text = base64.urlsafe_b64encode(public_bytes).rstrip(b"=").decode("ascii")
    provider_key = seal_record(
        GitHubCredentialProviderKey,
        {
            "provider_id": "fixture-provider",
            "key_id": "fixture-key",
            "public_key": public_text,
            "public_key_sha256": sha256_bytes(public_bytes),
            "valid_from": "2026-09-09T23:59:00Z",
            "valid_until": "2026-09-10T01:00:00Z",
            "created_at": created,
        },
    )
    profile = _repository_profile(
        provider_key_hash=provider_key.content_hash,
        expected_provider_public_key_sha256=provider_key.public_key_sha256,
        read_operations=(
            "branch_rules.list",
            "ref.get",
            "repository.get",
            "repository_rulesets.list",
        ),
        created_at=created,
    )
    api = _api_profile(created_at=created)
    return private_key, provider_key, profile, api


def _stage21a_observation_evidence(
    *,
    private_key,
    provider_key,
    profile,
    api,
    operation_key: str,
    path_parameters: dict,
    query_parameters: dict,
    projection: dict,
    item_count: int,
    suffix: str,
    authorization_id: str,
    intent_id: str,
    observation_id: str,
    created: str,
) -> Stage21AObservationEvidence:
    profile_ref = _rr("repository-profile", profile)
    api_ref = _rr("api-profile", api)
    key_ref = RecordReference(
        reference=profile.provider_key_reference,
        content_hash=provider_key.content_hash,
    )
    spec = ENDPOINTS[operation_key]
    maximum_network_requests = spec.maximum_pages + 1
    authorization = seal_record(
        GitHubOperationAuthorization,
        {
            "authorization_id": authorization_id,
            "repository_profile": profile_ref,
            "api_profile": api_ref,
            "repository_id": profile.repository_id,
            "account_id": profile.account_id,
            "operation_key": operation_key,
            "path_parameters": path_parameters,
            "query_parameters": query_parameters,
            "purpose": f"Fixture-only {operation_key} policy observation",
            "authorized_principal": "Arthur",
            "issued_at": created,
            "expires_at": "2026-09-10T00:10:00Z",
            "maximum_network_requests": maximum_network_requests,
            "created_at": created,
        },
    )
    authorization_ref = _rr(f"{suffix}-authorization", authorization)
    attempt_values = {
        "authorization_hash": authorization.content_hash,
        "repository_profile_hash": profile.content_hash,
        "api_profile_hash": api.content_hash,
        "operation_key": operation_key,
        "path_parameters": path_parameters,
        "query_parameters": query_parameters,
        "maximum_response_body_bytes_per_page": api.maximum_response_body_bytes_per_page,
        "maximum_total_response_body_bytes": api.maximum_total_response_body_bytes,
        "maximum_pages": spec.maximum_pages,
        "maximum_items": spec.maximum_items,
        "operation_timeout_seconds": api.operation_timeout_seconds,
        "maximum_retry_transmissions_per_operation": (
            api.maximum_retry_transmissions_per_operation
        ),
        "maximum_network_requests": maximum_network_requests,
    }
    intent = seal_record(
        GitHubOperationIntent,
        {
            "intent_id": intent_id,
            "authorization": authorization_ref,
            "repository_profile": profile_ref,
            "api_profile": api_ref,
            "repository_id": profile.repository_id,
            "account_id": profile.account_id,
            "app_id": profile.expected_app_id,
            "installation_id": profile.expected_installation_id,
            "operation_key": operation_key,
            "path_parameters": path_parameters,
            "query_parameters": query_parameters,
            "maximum_response_body_bytes_per_page": api.maximum_response_body_bytes_per_page,
            "maximum_total_response_body_bytes": api.maximum_total_response_body_bytes,
            "maximum_pages": spec.maximum_pages,
            "maximum_items": spec.maximum_items,
            "operation_timeout_seconds": api.operation_timeout_seconds,
            "maximum_retry_transmissions_per_operation": (
                api.maximum_retry_transmissions_per_operation
            ),
            "maximum_network_requests": maximum_network_requests,
            "attempt_id": compute_attempt_id(**attempt_values),
            "not_after": "2026-09-10T00:10:00Z",
            "created_at": created,
        },
    )
    intent_ref = _rr(f"{suffix}-intent", intent)
    claim = seal_record(
        GitHubOperationAttemptClaim,
        {
            "attempt_id": intent.attempt_id,
            "authorization": authorization_ref,
            "intent": intent_ref,
            "repository_profile": profile_ref,
            "api_profile": api_ref,
            "repository_id": profile.repository_id,
            "account_id": profile.account_id,
            "app_id": profile.expected_app_id,
            "installation_id": profile.expected_installation_id,
            "operation_key": operation_key,
            "claim_time": "2026-09-10T00:00:03Z",
            "intent_expiry": intent.not_after,
            "created_at": "2026-09-10T00:00:03Z",
        },
    )
    claim_ref = _rr(f"{suffix}-claim", claim)
    permissions = {
        "metadata": "read",
        "contents": "none",
        "pull_requests": "none",
        "checks": "none",
        "statuses": "none",
        "administration": "none",
    }
    if spec.additional_permission is not None:
        permissions[spec.additional_permission] = "read"
    envelope = PermissionEnvelope.model_validate(permissions)
    public_fields = {
        "provider_id": provider_key.provider_id,
        "provider_version": "v1",
        "key_id": provider_key.key_id,
        "lease_id": f"lease-{suffix}",
        "credential_class": "github_app_installation_access_token",
        "app_id": profile.expected_app_id,
        "installation_id": profile.expected_installation_id,
        "account_id": profile.account_id,
        "repository_ids": (profile.repository_id,),
        "repository_selection": "selected",
        "permissions": envelope,
        "minted_at": "2026-09-10T00:00:01Z",
        "expires_at": "2026-09-10T00:10:00Z",
        "api_version": api.api_version,
        "repository_profile_hash": profile.content_hash,
        "api_profile_hash": api.content_hash,
        "authorization_hash": authorization.content_hash,
        "intent_hash": intent.content_hash,
        "resolution_nonce_hash": "sha256:"
        + hashlib.sha256(f"nonce:{suffix}".encode("ascii")).hexdigest(),
        "provider_receipt_validation_outcome": "pass",
        "provider_receipt_validation_at": "2026-09-10T00:00:02Z",
        "provider_authentication_scheme": "Ed25519",
        "provider_authentication_version": "conclave-github-lease-ed25519-v1",
        "provider_authentication_key_id": provider_key.key_id,
    }
    receipt = _sign_model(
        CredentialLeaseReceipt,
        {**public_fields, "token_instance_tag": f"fixture-token-tag-{suffix}"},
        private_key,
        RECEIPT_SIGNATURE_DOMAIN,
    )
    claims = _sign_model(
        CredentialLeaseClaims,
        {
            **public_fields,
            "provider_pair_validation_outcome": "pass",
            "provider_pair_validation_at": "2026-09-10T00:00:04Z",
            "sanitized_transient_receipt_hash": sanitized_receipt_hash(receipt),
        },
        private_key,
        CLAIMS_SIGNATURE_DOMAIN,
    )
    claims_bytes = json.dumps(
        claims.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    lease = seal_record(
        CredentialLeaseEvidence,
        {
            "provider_claims": claims,
            "provider_claims_hash": "sha256:"
            + hashlib.sha256(claims_bytes).hexdigest(),
            "receipt_projection": LeasePublicFields.model_validate(public_fields),
            "receipt_signature_validated_at": "2026-09-10T00:00:03Z",
            "pair_validation_completed_at": "2026-09-10T00:00:04Z",
            "claims_signature_validated_at": "2026-09-10T00:00:05Z",
            "attempt_claim": claim_ref,
            "authorization": authorization_ref,
            "intent": intent_ref,
            "resolution_nonce_hash": public_fields["resolution_nonce_hash"],
            "sanitized_transient_receipt_hash": sanitized_receipt_hash(receipt),
            "maximum_network_requests": maximum_network_requests,
            "created_at": "2026-09-10T00:00:06Z",
        },
    )
    body = json.dumps(projection, sort_keys=True, separators=(",", ":")).encode()
    observation = seal_record(
        GitHubObservation,
        {
            "observation_id": observation_id,
            "observation_kind": operation_key,
            "repository_profile": profile_ref,
            "api_profile": api_ref,
            "authorization": authorization_ref,
            "intent": intent_ref,
            "attempt_claim": claim_ref,
            "lease_evidence": _rr(f"{suffix}-lease", lease),
            "repository_id": profile.repository_id,
            "account_id": profile.account_id,
            "app_id": profile.expected_app_id,
            "installation_id": profile.expected_installation_id,
            "operation_key": operation_key,
            "path_parameters": path_parameters,
            "query_parameters": query_parameters,
            "attempt_id": intent.attempt_id,
            "observed_at": "2026-09-10T00:00:07Z",
            "status_class": "2xx",
            "pages": (
                ObservationPage(
                    page=1,
                    response_bytes=len(body),
                    wire_body_hash="sha256:" + hashlib.sha256(body).hexdigest(),
                    item_count=item_count,
                    rate_limit=SafeRateLimitProjection(
                        resource="core",
                        limit=5000,
                        remaining=40,
                        retry_after_present=False,
                    ),
                ),
            ),
            "projection": projection,
            "complete": True,
            "pagination_complete": True,
            "identity_match": True,
            "visibility": "complete_for_endpoint",
            "reason_codes": (),
            "created_at": "2026-09-10T00:00:07Z",
        },
    )
    return Stage21AObservationEvidence(
        repository_profile_record=profile,
        api_profile_record=api,
        provider_key_reference=key_ref,
        provider_key_record=provider_key,
        authorization_record=authorization,
        intent_record=intent,
        attempt_claim_record=claim,
        lease_evidence_record=lease,
        observation_reference=_rr(f"{suffix}-observation", observation),
        observation_record=observation,
    )


def _governed_fixture():
    now = "2026-09-10T00:00:30Z"
    created = "2026-09-10T00:00:00Z"
    private_key, provider_key, profile, api = _stage21a_fixture_context(created)
    empty_tree = reconstruct_tree_oid((), "sha1")
    base_ref = _rr("base-observation")
    profile_ref = _rr("repository-profile", profile)
    api_ref = _rr("api-profile", api)
    from conclave.github_publication import PublicationRepositoryExtension

    extension = seal_record(
        PublicationRepositoryExtension,
        {
            "repository_profile": profile_ref,
            "created_at": created,
        },
    )
    extension_ref = _rr("repository-extension", extension)
    task = seal_task(
        TaskPacket.model_validate(
            {
                "task_id": "TP-stage-21b-0123456789",
                "created_at": created,
                "created_by": "Arthur",
                "objective": "Publish one bounded proposal",
                "target_objects": [{"object_id": "a.txt"}],
                "assigned_providers": [{"provider": "fixture", "role": "publication"}],
            }
        )
    )
    handoff = seal_handoff(
        HandoffPacket.model_validate(
            {
                "packet_ref": task.ref,
                "packet_content_hash": task.content_hash,
                "provider": "fixture",
                "role": "publication",
                "status": "submitted",
                "objects_touched": [
                    {"object_id": "a.txt", "action": "proposed_change"}
                ],
                "recommended_next_action": "accept",
                "raw_response_hash": "sha256:" + "1" * 64,
                "prompt_hash": "sha256:" + "2" * 64,
                "imported_at": created,
            }
        )
    )
    scope_review = evaluate_scope(task, handoff)
    task_ref, handoff_ref, scope_ref = (
        _rr("task", task),
        _rr("handoff", handoff),
        _rr("scope", scope_review),
    )
    base_identity = seal_record(
        BaseTreeIdentityObservation,
        {
            "observation_id": "base-identity-1",
            "repository_profile": profile_ref,
            "api_profile": api_ref,
            "repository_id": 101,
            "account_id": 202,
            "base_ref": "refs/heads/main",
            "base_commit_oid": "a" * 40,
            "base_root_tree_oid": empty_tree,
            "object_format": "sha1",
            "observed_at": created,
            "created_at": created,
        },
    )
    base_ref = _rr("base-observation", base_identity)
    source_auth = seal_record(
        RecursiveTreeAuthorization,
        {
            "authorization_id": "tree-auth-1",
            "repository_profile": profile_ref,
            "api_profile": api_ref,
            "repository_extension": extension_ref,
            "repository_id": 101,
            "account_id": 202,
            "base_ref": "refs/heads/main",
            "base_commit_oid": "a" * 40,
            "root_tree_oid": empty_tree,
            "object_format": "sha1",
            "authorized_principal": "Arthur",
            "issued_at": created,
            "expires_at": "2026-09-10T00:10:00Z",
            "created_at": created,
        },
    )
    source_auth_ref = _rr("tree-auth", source_auth)
    request_target = f"/repos/komistry-labs/conclave/git/trees/{empty_tree}?recursive=1"
    source_intent = seal_record(
        RecursiveTreeIntent,
        {
            "intent_id": "tree-intent-1",
            "authorization": source_auth_ref,
            "repository_profile": profile_ref,
            "api_profile": api_ref,
            "repository_extension": extension_ref,
            "repository_id": 101,
            "account_id": 202,
            "base_ref": "refs/heads/main",
            "root_tree_oid": empty_tree,
            "object_format": "sha1",
            "request_target_hash": "sha256:"
            + hashlib.sha256(request_target.encode()).hexdigest(),
            "not_after": source_auth.expires_at,
            "created_at": created,
        },
    )
    source_intent_ref = _rr("tree-intent", source_intent)
    source_claim = seal_record(
        RecursiveTreeAttemptClaim,
        {
            "claim_id": "tree-claim-1",
            "authorization": source_auth_ref,
            "intent": source_intent_ref,
            "repository_profile": profile_ref,
            "api_profile": api_ref,
            "repository_id": 101,
            "account_id": 202,
            "created_at": "2026-09-10T00:00:03Z",
        },
    )
    source_claim_ref = _rr("tree-claim", source_claim)
    source_permissions = PermissionEnvelope(
        metadata="read",
        contents="read",
        pull_requests="none",
        checks="none",
        statuses="none",
        administration="none",
    )
    source_public_fields = {
        "provider_id": provider_key.provider_id,
        "provider_version": "v1",
        "key_id": provider_key.key_id,
        "lease_id": "lease-tree-source",
        "credential_class": "github_app_installation_access_token",
        "app_id": profile.expected_app_id,
        "installation_id": profile.expected_installation_id,
        "account_id": profile.account_id,
        "repository_ids": (profile.repository_id,),
        "repository_selection": "selected",
        "permissions": source_permissions,
        "minted_at": "2026-09-10T00:00:01Z",
        "expires_at": source_auth.expires_at,
        "api_version": api.api_version,
        "repository_profile_hash": profile.content_hash,
        "api_profile_hash": api.content_hash,
        "authorization_hash": source_auth.content_hash,
        "intent_hash": source_intent.content_hash,
        "resolution_nonce_hash": "sha256:"
        + hashlib.sha256(b"nonce:tree-source").hexdigest(),
        "provider_receipt_validation_outcome": "pass",
        "provider_receipt_validation_at": "2026-09-10T00:00:02Z",
        "provider_authentication_scheme": "Ed25519",
        "provider_authentication_version": "conclave-github-lease-ed25519-v1",
        "provider_authentication_key_id": provider_key.key_id,
    }
    source_receipt = _sign_model(
        CredentialLeaseReceipt,
        {**source_public_fields, "token_instance_tag": "fixture-token-tag-tree-source"},
        private_key,
        RECEIPT_SIGNATURE_DOMAIN,
    )
    source_claims = _sign_model(
        CredentialLeaseClaims,
        {
            **source_public_fields,
            "provider_pair_validation_outcome": "pass",
            "provider_pair_validation_at": "2026-09-10T00:00:04Z",
            "sanitized_transient_receipt_hash": sanitized_receipt_hash(source_receipt),
        },
        private_key,
        CLAIMS_SIGNATURE_DOMAIN,
    )
    source_claims_bytes = json.dumps(
        source_claims.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    source_lease = seal_record(
        CredentialLeaseEvidence,
        {
            "provider_claims": source_claims,
            "provider_claims_hash": "sha256:"
            + hashlib.sha256(source_claims_bytes).hexdigest(),
            "receipt_projection": LeasePublicFields.model_validate(
                source_public_fields
            ),
            "receipt_signature_validated_at": "2026-09-10T00:00:03Z",
            "pair_validation_completed_at": "2026-09-10T00:00:04Z",
            "claims_signature_validated_at": "2026-09-10T00:00:05Z",
            "attempt_claim": source_claim_ref,
            "authorization": source_auth_ref,
            "intent": source_intent_ref,
            "resolution_nonce_hash": source_public_fields["resolution_nonce_hash"],
            "sanitized_transient_receipt_hash": sanitized_receipt_hash(source_receipt),
            "maximum_network_requests": 1,
            "created_at": "2026-09-10T00:00:06Z",
        },
    )
    source_lease_record = seal_record(
        RecursiveTreeLeaseEvidence,
        {
            "authorization": source_auth_ref,
            "intent": source_intent_ref,
            "claim": source_claim_ref,
            "credential_lease_evidence": _rr("tree-provider-lease", source_lease),
            "provider_key": RecordReference(
                reference=profile.provider_key_reference,
                content_hash=provider_key.content_hash,
            ),
            "provider_public_key_sha256": provider_key.public_key_sha256,
            "provider_id": "fixture-provider",
            "provider_version": "v1",
            "repository_id": 101,
            "account_id": 202,
            "app_id": 303,
            "installation_id": 404,
            "created_at": "2026-09-10T00:00:06Z",
        },
    )
    source_lease_ref = _rr("tree-lease", source_lease_record)
    recursive = seal_record(
        RecursiveTreeObservation,
        {
            "observation_id": "tree-source-1",
            "repository_profile": profile_ref,
            "api_profile": api_ref,
            "base_observation": base_ref,
            "authorization": source_auth_ref,
            "intent": source_intent_ref,
            "attempt_claim": source_claim_ref,
            "lease_evidence": source_lease_ref,
            "repository_id": 101,
            "account_id": 202,
            "base_ref": "refs/heads/main",
            "base_commit_oid": "a" * 40,
            "root_tree_oid": empty_tree,
            "object_format": "sha1",
            "response_bytes": 2,
            "entries": (),
            "created_at": "2026-09-10T00:00:07Z",
        },
    )
    closure = seal_record(
        BaseTreeClosure,
        {
            "closure_id": "closure-1",
            "increment_21_hash": INCREMENT_21_PROTOCOL_HASH,
            "stage_21a_hash": STAGE_21A_PROTOCOL_HASH,
            "stage_21b_hash": STAGE_21B_PROTOCOL_HASH,
            "erratum_hash": STAGE_21B_ERRATUM_HASH,
            "repository_profile": profile_ref,
            "api_profile": api_ref,
            "base_observation": base_ref,
            "source_observation": _rr("tree-source", recursive),
            "source_authorization": recursive.authorization,
            "source_intent": recursive.intent,
            "source_attempt_claim": recursive.attempt_claim,
            "source_lease_evidence": recursive.lease_evidence,
            "repository_extension": extension_ref,
            "repository_id": 101,
            "account_id": 202,
            "base_ref": "refs/heads/main",
            "base_commit_oid": "a" * 40,
            "base_root_tree_oid": empty_tree,
            "object_format": "sha1",
            "entries": (),
            "entry_count": 0,
            "canonical_byte_count": len(canonical_closure_entries_bytes(())),
            "recomputed_base_root_tree_oid": empty_tree,
            "base_observed_at": created,
            "source_observed_at": "2026-09-10T00:00:07Z",
            "created_at": created,
        },
    )
    content = b"hello\n"
    content_hash = "sha256:" + hashlib.sha256(content).hexdigest()
    artifact_ref = RecordReference(
        reference="artifacts/a.txt", content_hash=content_hash
    )
    proposal_file = ProposalFile(
        path="a.txt",
        byte_count=len(content),
        content_sha256=content_hash,
        blob_oid=git_blob_oid(content, "sha1"),
        artifact=artifact_ref,
    )
    tree_oid = apply_proposal((), (proposal_file,), "sha1")
    identity = CommitIdentity(
        name="Conclave", email="bot@example.invalid", timestamp=created
    )
    identity_bytes = json.dumps(
        identity.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    ).encode()
    message, title, body = b"proposal\n", b"Proposal", b"Body\n"

    def artifact(name, value):
        return RecordReference(
            reference=f"artifacts/{name}",
            content_hash="sha256:" + hashlib.sha256(value).hexdigest(),
        )

    message_ref, title_ref, body_ref = (
        artifact("message", message),
        artifact("title", title),
        artifact("body", body),
    )
    identity_ref = artifact("identity", identity_bytes)
    commit_oid = git_commit_oid(
        tree_oid=tree_oid,
        parent_oid="a" * 40,
        name=identity.name,
        email=identity.email,
        timestamp=identity.timestamp,
        message=message.decode(),
        object_format="sha1",
    )
    head_ref = "refs/heads/conclave/01890f3e-7b1a-7cc2-8b4f-8f2e9c90a113/change"
    rate_source_chain = _stage21a_observation_evidence(
        private_key=private_key,
        provider_key=provider_key,
        profile=profile,
        api=api,
        operation_key="repository.get",
        path_parameters={},
        query_parameters={},
        projection={"repository_id": 101},
        item_count=1,
        suffix="rate-source",
        authorization_id="01890f3e-7b1a-7cc2-8b4f-8f2e9c90a127",
        intent_id="01890f3e-7b1a-7cc2-8b4f-8f2e9c90a128",
        observation_id="01890f3e-7b1a-7cc2-8b4f-8f2e9c90a129",
        created=created,
    )
    branch_chain = _stage21a_observation_evidence(
        private_key=private_key,
        provider_key=provider_key,
        profile=profile,
        api=api,
        operation_key="branch_rules.list",
        path_parameters={"branch": head_ref.removeprefix("refs/heads/")},
        query_parameters={"per_page": 100, "page": 1},
        projection={"rules": []},
        item_count=0,
        suffix="branch-rules",
        authorization_id="01890f3e-7b1a-7cc2-8b4f-8f2e9c90a130",
        intent_id="01890f3e-7b1a-7cc2-8b4f-8f2e9c90a131",
        observation_id="01890f3e-7b1a-7cc2-8b4f-8f2e9c90a132",
        created=created,
    )
    ruleset_chain = _stage21a_observation_evidence(
        private_key=private_key,
        provider_key=provider_key,
        profile=profile,
        api=api,
        operation_key="repository_rulesets.list",
        path_parameters={},
        query_parameters={"includes_parents": True, "per_page": 100, "page": 1},
        projection={"rulesets": []},
        item_count=0,
        suffix="rulesets",
        authorization_id="01890f3e-7b1a-7cc2-8b4f-8f2e9c90a133",
        intent_id="01890f3e-7b1a-7cc2-8b4f-8f2e9c90a134",
        observation_id="01890f3e-7b1a-7cc2-8b4f-8f2e9c90a135",
        created=created,
    )
    manifest = seal_record(
        ProposalManifest,
        {
            "manifest_id": "manifest-1",
            "repository_profile": profile_ref,
            "api_profile": api_ref,
            "repository_extension": extension_ref,
            "repository_id": 101,
            "account_id": 202,
            "owner": "komistry-labs",
            "repository": "conclave",
            "task_packet": task_ref,
            "handoff": handoff_ref,
            "scope_review": scope_ref,
            "base_observation": base_ref,
            "base_tree_closure": _rr("closure", closure),
            "branch_rules_observation": branch_chain.observation_reference,
            "ruleset_observation": ruleset_chain.observation_reference,
            "base_ref": "refs/heads/main",
            "base_commit_oid": "a" * 40,
            "base_tree_oid": empty_tree,
            "head_ref": head_ref,
            "object_format": "sha1",
            "files": (proposal_file,),
            "allowed_paths": ("a.txt",),
            "aggregate_byte_count": len(content),
            "aggregate_manifest_hash": proposal_aggregate_hash((proposal_file,)),
            "commit_message": message_ref,
            "commit_message_byte_count": len(message),
            "commit_identity": identity,
            "commit_identity_artifact": identity_ref,
            "pull_request_title": title_ref,
            "pull_request_title_byte_count": len(title),
            "pull_request_body": body_ref,
            "pull_request_body_byte_count": len(body),
            "proposal_tree_oid": tree_oid,
            "proposal_commit_oid": commit_oid,
            "created_at": created,
        },
    )
    rate = seal_record(
        AuthenticatedRateBudgetObservation,
        {
            "source_observation": rate_source_chain.observation_reference,
            "repository_profile": profile_ref,
            "api_profile": api_ref,
            "repository_id": 101,
            "account_id": 202,
            "app_id": 303,
            "installation_id": 404,
            "provider_id": "fixture-provider",
            "provider_version": "v1",
            "provider_key": RecordReference(
                reference=profile.provider_key_reference,
                content_hash=provider_key.content_hash,
            ),
            "provider_public_key_sha256": provider_key.public_key_sha256,
            "api_version": "2026-03-10",
            "resource_bucket": "core",
            "limit": 5000,
            "remaining": 40,
            "reset_at": None,
            "retry_after_present": False,
            "observed_at": "2026-09-10T00:00:07Z",
            "created_at": created,
        },
    )
    auth = seal_record(
        PublicationAuthorization,
        {
            "authorization_id": "auth-1",
            "authorized_principal": "Arthur",
            "issued_at": created,
            "expires_at": "2026-09-10T00:10:00Z",
            "purpose": "Publish one fixture-only proposal",
            "protocol_hash": STAGE_21B_PROTOCOL_HASH,
            "increment_21_hash": INCREMENT_21_PROTOCOL_HASH,
            "stage_21a_hash": STAGE_21A_PROTOCOL_HASH,
            "erratum_hash": STAGE_21B_ERRATUM_HASH,
            "manifest": _rr("manifest", manifest),
            "rate_observation": _rr("rate", rate),
            "repository_profile": profile_ref,
            "api_profile": api_ref,
            "task_packet": manifest.task_packet,
            "handoff": manifest.handoff,
            "scope_review": manifest.scope_review,
            "base_observation": base_ref,
            "base_tree_closure": manifest.base_tree_closure,
            "base_tree_source_observation": closure.source_observation,
            "branch_rules_observation": manifest.branch_rules_observation,
            "ruleset_observation": manifest.ruleset_observation,
            "repository_id": 101,
            "account_id": 202,
            "app_id": 303,
            "installation_id": 404,
            "provider_id": "fixture-provider",
            "provider_version": "v1",
            "provider_key": rate.provider_key,
            "provider_public_key_sha256": rate.provider_public_key_sha256,
            "api_version": rate.api_version,
            "resource_bucket": rate.resource_bucket,
            "base_ref": manifest.base_ref,
            "head_ref": manifest.head_ref,
            "base_commit_oid": manifest.base_commit_oid,
            "base_tree_oid": manifest.base_tree_oid,
            "proposal_tree_oid": manifest.proposal_tree_oid,
            "proposal_commit_oid": manifest.proposal_commit_oid,
            "allowed_paths": manifest.allowed_paths,
            "aggregate_proposal_hash": manifest.aggregate_manifest_hash,
            "commit_message_hash": message_ref.content_hash,
            "commit_message_byte_count": len(message),
            "pull_request_title_hash": title_ref.content_hash,
            "pull_request_title_byte_count": len(title),
            "pull_request_body_hash": body_ref.content_hash,
            "pull_request_body_byte_count": len(body),
            "maximum_mutation_requests": 5,
            "maximum_total_requests": 16,
            "created_at": created,
        },
    )
    artifacts = {
        artifact_ref.reference: content,
        message_ref.reference: message,
        title_ref.reference: title,
        body_ref.reference: body,
        identity_ref.reference: identity_bytes,
    }
    dispatches = build_exact_publication_dispatches(manifest, profile, artifacts)
    hashes = tuple(item.request_hash for item in dispatches)
    endpoints = tuple(item.operation_key for item in dispatches)
    upstream = (
        profile_ref,
        api_ref,
        extension_ref,
        manifest.task_packet,
        manifest.handoff,
        manifest.scope_review,
        base_ref,
        manifest.base_tree_closure,
        closure.source_observation,
        closure.source_authorization,
        closure.source_intent,
        closure.source_attempt_claim,
        closure.source_lease_evidence,
        manifest.branch_rules_observation,
        manifest.ruleset_observation,
        _rr("rate", rate),
        rate.provider_key,
    )
    scope_hash = rate_scope_hash(rate)
    plan = seal_record(
        PublicationPlan,
        {
            "plan_id": "plan-1",
            "authorization": _rr("auth", auth),
            "manifest": _rr("manifest", manifest),
            "rate_observation": _rr("rate", rate),
            "upstream_records": upstream,
            "rate_scope_hash": scope_hash,
            "blob_request_hashes": (hashes[1],),
            "expected_blob_oids": (proposal_file.blob_oid,),
            "tree_request_hash": hashes[3],
            "commit_request_hash": hashes[5],
            "ref_request_hash": hashes[9],
            "pull_request_request_hash": hashes[14],
            "ordered_endpoint_plan": endpoints,
            "ordered_request_hashes": hashes,
            "expected_tree_oid": tree_oid,
            "expected_commit_oid": commit_oid,
            "base_ref": manifest.base_ref,
            "head_ref": manifest.head_ref,
            "maximum_total_requests": 16,
            "created_at": created,
        },
    )
    attempt_id = publication_attempt_id(
        authorization=auth, manifest=manifest, plan=plan
    )
    oi = seal_record(
        OperationIntentV2,
        {
            "intent_id": "intent-1",
            "authorization": _rr("auth", auth),
            "manifest": _rr("manifest", manifest),
            "plan": _rr("plan", plan),
            "rate_observation": _rr("rate", rate),
            "attempt_id": attempt_id,
            "upstream_records": upstream,
            "ordered_endpoint_plan": endpoints,
            "canonical_request_hashes": hashes,
            "rate_scope_hash": scope_hash,
            "maximum_mutation_requests": 5,
            "maximum_total_requests": 16,
            "not_after": auth.expires_at,
            "created_at": created,
        },
    )
    pi = seal_record(
        PublicationIntent,
        {
            "publication_intent_id": "publication-intent-1",
            "authorization": _rr("auth", auth),
            "manifest": _rr("manifest", manifest),
            "plan": _rr("plan", plan),
            "operation_intent": _rr("oi", oi),
            "rate_observation": _rr("rate", rate),
            "attempt_id": attempt_id,
            "upstream_records": upstream,
            "rate_scope_hash": scope_hash,
            "blob_request_hashes": (hashes[1],),
            "expected_blob_oids": (proposal_file.blob_oid,),
            "tree_request_hash": hashes[3],
            "commit_request_hash": hashes[5],
            "ref_request_hash": hashes[9],
            "pull_request_request_hash": hashes[14],
            "base_commit_oid": manifest.base_commit_oid,
            "ordered_endpoint_plan": endpoints,
            "maximum_mutation_requests": 5,
            "maximum_total_requests": 16,
            "exact_request_hashes": hashes,
            "expected_tree_oid": tree_oid,
            "expected_commit_oid": commit_oid,
            "base_ref": manifest.base_ref,
            "head_ref": manifest.head_ref,
            "created_at": created,
        },
    )
    claim = seal_record(
        PublicationAttemptClaim,
        {
            "attempt_id": attempt_id,
            "authorization": _rr("auth", auth),
            "manifest": _rr("manifest", manifest),
            "plan": _rr("plan", plan),
            "operation_intent": _rr("oi", oi),
            "publication_intent": _rr("pi", pi),
            "rate_observation": _rr("rate", rate),
            "upstream_records": upstream,
            "provider_key": rate.provider_key,
            "provider_public_key_sha256": rate.provider_public_key_sha256,
            "created_at": created,
        },
    )
    publication_nonce_hash = (
        "sha256:" + hashlib.sha256(b"nonce:publication-fixture").hexdigest()
    )
    publication_claims = _sign_model(
        PublicationLeaseClaims,
        {
            "provider_id": rate.provider_id,
            "provider_version": rate.provider_version,
            "key_id": provider_key.key_id,
            "lease_id": "lease-publication-fixture",
            "repository_profile_hash": profile.content_hash,
            "api_profile_hash": api.content_hash,
            "authorization_hash": auth.content_hash,
            "plan_hash": plan.content_hash,
            "operation_intent_hash": oi.content_hash,
            "publication_intent_hash": pi.content_hash,
            "attempt_claim_hash": claim.content_hash,
            "attempt_id": attempt_id,
            "rate_observation_hash": rate.content_hash,
            "rate_scope_hash": scope_hash,
            "app_id": profile.expected_app_id,
            "installation_id": profile.expected_installation_id,
            "account_id": profile.account_id,
            "repository_ids": (profile.repository_id,),
            "api_version": api.api_version,
            "resource_bucket": rate.resource_bucket,
            "maximum_mutation_requests": 5,
            "maximum_total_requests": 16,
            "minted_at": "2026-09-10T00:00:08Z",
            "expires_at": auth.expires_at,
            "resolution_nonce_hash": publication_nonce_hash,
            "provider_authentication_key_id": provider_key.key_id,
        },
        private_key,
        PUBLICATION_LEASE_CLAIMS_DOMAIN,
    )
    publication_claims_bytes = json.dumps(
        publication_claims.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    lease = seal_record(
        PublicationLeaseEvidence,
        {
            "attempt_claim": _rr("claim", claim),
            "authorization": _rr("auth", auth),
            "operation_intent": _rr("oi", oi),
            "publication_intent": _rr("pi", pi),
            "plan": _rr("plan", plan),
            "rate_observation": _rr("rate", rate),
            "provider_key": rate.provider_key,
            "provider_public_key_sha256": rate.provider_public_key_sha256,
            "provider_claims": publication_claims,
            "provider_claims_hash": "sha256:"
            + hashlib.sha256(publication_claims_bytes).hexdigest(),
            "claims_signature_validated_at": "2026-09-10T00:00:09Z",
            "resolution_nonce_hash": publication_nonce_hash,
            "rate_scope_hash": scope_hash,
            "protocol_hash": auth.protocol_hash,
            "repository_profile": profile_ref,
            "increment_21_hash": auth.increment_21_hash,
            "stage_21a_hash": auth.stage_21a_hash,
            "erratum_hash": auth.erratum_hash,
            "api_profile": api_ref,
            "repository_id": 101,
            "account_id": 202,
            "app_id": 303,
            "installation_id": 404,
            "provider_id": rate.provider_id,
            "provider_version": rate.provider_version,
            "api_version": rate.api_version,
            "resource_bucket": rate.resource_bucket,
            "ordered_endpoint_plan": endpoints,
            "maximum_mutation_requests": 5,
            "maximum_total_requests": 16,
            "first_rate_check_at": now,
            "created_at": created,
        },
    )
    chain = PublicationGovernanceChain(
        repository_profile_record=profile,
        api_profile_record=api,
        repository_extension_record=extension,
        task_packet_record=task,
        handoff_record=handoff,
        scope_review_record=scope_review,
        provider_key_record=provider_key,
        source_authorization_record=source_auth,
        source_intent_record=source_intent,
        source_attempt_claim_record=source_claim,
        source_lease_evidence_record=source_lease_record,
        source_credential_lease_evidence_record=source_lease,
        rate_observation_record=rate,
        rate_source_observation_chain=rate_source_chain,
        branch_rules_observation_chain=(branch_chain,),
        ruleset_observation_chain=(ruleset_chain,),
        base_identity_observation=base_identity,
        recursive_tree_observation=recursive,
        base_tree_closure=closure,
        manifest=manifest,
        authorization=auth,
        plan=plan,
        operation_intent=oi,
        publication_intent=pi,
        attempt_claim=claim,
        lease_evidence=lease,
    )
    return chain, rate, artifacts, now


def _stored_inputs(root: Path, chain, rate, artifacts) -> dict:
    workspace = Workspace(root / ".conclave")
    if not workspace.config_path.exists():
        workspace = Workspace.create(root, principal="Arthur")
        ledger.initialise(workspace, workspace.load_config())
    record_store_root = workspace.root
    for reference, record in (
        (chain.manifest.repository_profile, chain.repository_profile_record),
        (chain.manifest.api_profile, chain.api_profile_record),
        (chain.manifest.repository_extension, chain.repository_extension_record),
        (chain.manifest.task_packet, chain.task_packet_record),
        (chain.manifest.handoff, chain.handoff_record),
        (chain.manifest.scope_review, chain.scope_review_record),
        (chain.authorization.provider_key, chain.provider_key_record),
        (
            chain.base_tree_closure.source_authorization,
            chain.source_authorization_record,
        ),
        (chain.base_tree_closure.source_intent, chain.source_intent_record),
        (
            chain.base_tree_closure.source_attempt_claim,
            chain.source_attempt_claim_record,
        ),
        (
            chain.base_tree_closure.source_lease_evidence,
            chain.source_lease_evidence_record,
        ),
        (
            chain.source_lease_evidence_record.credential_lease_evidence,
            chain.source_credential_lease_evidence_record,
        ),
        (chain.authorization.rate_observation, rate),
        (
            chain.rate_source_observation_chain.provider_key_reference,
            chain.rate_source_observation_chain.provider_key_record,
        ),
        (
            chain.rate_source_observation_chain.observation_record.authorization,
            chain.rate_source_observation_chain.authorization_record,
        ),
        (
            chain.rate_source_observation_chain.observation_record.intent,
            chain.rate_source_observation_chain.intent_record,
        ),
        (
            chain.rate_source_observation_chain.observation_record.attempt_claim,
            chain.rate_source_observation_chain.attempt_claim_record,
        ),
        (
            chain.rate_source_observation_chain.observation_record.lease_evidence,
            chain.rate_source_observation_chain.lease_evidence_record,
        ),
        (
            rate.source_observation,
            chain.rate_source_observation_chain.observation_record,
        ),
        (chain.manifest.base_observation, chain.base_identity_observation),
        (chain.base_tree_closure.source_observation, chain.recursive_tree_observation),
        (chain.manifest.base_tree_closure, chain.base_tree_closure),
        (chain.authorization.manifest, chain.manifest),
        (chain.plan.authorization, chain.authorization),
        (chain.operation_intent.plan, chain.plan),
        (chain.publication_intent.operation_intent, chain.operation_intent),
        (chain.attempt_claim.publication_intent, chain.publication_intent),
    ):
        write_durable_record(
            record_store_root / Path(*reference.reference.split("/")), record
        )
    for evidence in (
        *chain.branch_rules_observation_chain,
        *chain.ruleset_observation_chain,
    ):
        for reference, record in (
            (evidence.provider_key_reference, evidence.provider_key_record),
            (evidence.observation_record.authorization, evidence.authorization_record),
            (evidence.observation_record.intent, evidence.intent_record),
            (evidence.observation_record.attempt_claim, evidence.attempt_claim_record),
            (
                evidence.observation_record.lease_evidence,
                evidence.lease_evidence_record,
            ),
            (evidence.observation_reference, evidence.observation_record),
        ):
            write_durable_record(
                record_store_root / Path(*reference.reference.split("/")), record
            )
    for reference in chain.plan.upstream_records:
        path = record_store_root / Path(*reference.reference.split("/"))
        if path.exists():
            continue
        name = path.stem
        content = _fixture_placeholder_bytes(name)
        assert "sha256:" + hashlib.sha256(content).hexdigest() == reference.content_hash
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    for reference, content in artifacts.items():
        path = root / Path(*reference.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_bytes() != content:
            path.unlink()
        if not path.exists():
            path.write_bytes(content)
    return {
        "artifact_root": root,
        "workspace": workspace,
        "lease_check_at": chain.lease_evidence.first_rate_check_at,
        "first_dispatch_check_at": chain.lease_evidence.first_rate_check_at,
        "monotonic_elapsed_milliseconds": 0,
    }


def _evidence_directory(root: Path, chain: PublicationGovernanceChain) -> Path:
    attempt_token = chain.attempt_claim.attempt_id.rsplit(":", 1)[-1]
    return (
        Workspace(root / ".conclave").github_publication_fixture_evidence_dir
        / attempt_token
    )


def test_governed_fixture_uses_exact_requests_and_four_state_evidence(tmp_path) -> None:
    chain, rate, artifacts, now = _governed_fixture()
    transport = Loopback(40)
    transport.scope_hash = rate_scope_hash(rate)
    receipt = evaluate_governed_publication(
        governance=chain,
        rate_observation_record=rate,
        **_stored_inputs(tmp_path, chain, rate, artifacts),
        transcript=transport.prepare(chain, rate, artifacts),
        now=now,
        configured_principal="Arthur",
    )
    assert len(transport) == 16
    assert receipt.fixture_conformance_complete is True
    assert receipt.fixture_conformance_passed is True
    assert receipt.live_publication_claimed is False
    assert len(receipt.step_states) == 16
    assert receipt.step_states[0].state == "fixture_read_result_present"
    assert receipt.step_states[1].state == "fixture_mutation_result_present"
    assert ledger.read_events(Workspace(tmp_path / ".conclave"))[-1]["event_type"] == (
        "github_proposal_publication_fixture_verified"
    )


def test_governed_fixture_rejects_content_and_chain_substitution(tmp_path) -> None:
    chain, rate, artifacts, now = _governed_fixture()
    changed = dict(artifacts)
    changed[chain.manifest.files[0].artifact.reference] = b"changed"
    transport = Loopback(40)
    transport.scope_hash = rate_scope_hash(rate)
    with pytest.raises(ValueError):
        evaluate_governed_publication(
            governance=chain,
            rate_observation_record=rate,
            **_stored_inputs(tmp_path, chain, rate, changed),
            transcript=transport.prepare(chain, rate, changed),
            now=now,
            configured_principal="Arthur",
        )
    plan_data = chain.plan.model_dump(mode="json", exclude={"content_hash"})
    plan_data["manifest"] = _rr("different-manifest")
    for key in (
        "upstream_records",
        "blob_request_hashes",
        "expected_blob_oids",
        "ordered_endpoint_plan",
        "ordered_request_hashes",
    ):
        plan_data[key] = tuple(plan_data[key])
    substituted_plan = seal_record(PublicationPlan, plan_data)
    with pytest.raises(ValueError, match="cross-bound"):
        PublicationGovernanceChain(
            repository_profile_record=chain.repository_profile_record,
            api_profile_record=chain.api_profile_record,
            repository_extension_record=chain.repository_extension_record,
            task_packet_record=chain.task_packet_record,
            handoff_record=chain.handoff_record,
            scope_review_record=chain.scope_review_record,
            provider_key_record=chain.provider_key_record,
            source_authorization_record=chain.source_authorization_record,
            source_intent_record=chain.source_intent_record,
            source_attempt_claim_record=chain.source_attempt_claim_record,
            source_lease_evidence_record=chain.source_lease_evidence_record,
            source_credential_lease_evidence_record=chain.source_credential_lease_evidence_record,
            rate_observation_record=chain.rate_observation_record,
            rate_source_observation_chain=chain.rate_source_observation_chain,
            branch_rules_observation_chain=chain.branch_rules_observation_chain,
            ruleset_observation_chain=chain.ruleset_observation_chain,
            base_identity_observation=chain.base_identity_observation,
            recursive_tree_observation=chain.recursive_tree_observation,
            base_tree_closure=chain.base_tree_closure,
            manifest=chain.manifest,
            authorization=chain.authorization,
            plan=substituted_plan,
            operation_intent=chain.operation_intent,
            publication_intent=chain.publication_intent,
            attempt_claim=chain.attempt_claim,
            lease_evidence=chain.lease_evidence,
        )


@pytest.mark.parametrize("mutation", ["reorder", "duplicate", "substitute"])
def test_governance_chain_rejects_every_exact_upstream_tuple_mutation(mutation) -> None:
    chain, _rate, _artifacts, _now = _governed_fixture()
    plan_data = chain.plan.model_dump(mode="json", exclude={"content_hash"})
    upstream = list(plan_data["upstream_records"])
    if mutation == "reorder":
        upstream[0], upstream[1] = upstream[1], upstream[0]
    elif mutation == "duplicate":
        upstream[1] = upstream[0]
    else:
        upstream[0] = _rr("substituted-upstream").model_dump(mode="json")
    plan_data["upstream_records"] = tuple(upstream)
    for key in (
        "blob_request_hashes",
        "expected_blob_oids",
        "ordered_endpoint_plan",
        "ordered_request_hashes",
    ):
        plan_data[key] = tuple(plan_data[key])
    substituted_plan = seal_record(PublicationPlan, plan_data)
    with pytest.raises(ValueError, match="cross-bound"):
        PublicationGovernanceChain(
            repository_profile_record=chain.repository_profile_record,
            api_profile_record=chain.api_profile_record,
            repository_extension_record=chain.repository_extension_record,
            task_packet_record=chain.task_packet_record,
            handoff_record=chain.handoff_record,
            scope_review_record=chain.scope_review_record,
            provider_key_record=chain.provider_key_record,
            source_authorization_record=chain.source_authorization_record,
            source_intent_record=chain.source_intent_record,
            source_attempt_claim_record=chain.source_attempt_claim_record,
            source_lease_evidence_record=chain.source_lease_evidence_record,
            source_credential_lease_evidence_record=chain.source_credential_lease_evidence_record,
            rate_observation_record=chain.rate_observation_record,
            rate_source_observation_chain=chain.rate_source_observation_chain,
            branch_rules_observation_chain=chain.branch_rules_observation_chain,
            ruleset_observation_chain=chain.ruleset_observation_chain,
            base_identity_observation=chain.base_identity_observation,
            recursive_tree_observation=chain.recursive_tree_observation,
            base_tree_closure=chain.base_tree_closure,
            manifest=chain.manifest,
            authorization=chain.authorization,
            plan=substituted_plan,
            operation_intent=chain.operation_intent,
            publication_intent=chain.publication_intent,
            attempt_claim=chain.attempt_claim,
            lease_evidence=chain.lease_evidence,
        )


def test_governance_chain_rejects_typed_source_and_policy_chain_substitution() -> None:
    chain, _rate, _artifacts, _now = _governed_fixture()
    bad_source_data = chain.source_intent_record.model_dump(
        mode="json", exclude={"content_hash"}
    )
    bad_source_data["root_tree_oid"] = "0" * 40
    bad_source = seal_record(type(chain.source_intent_record), bad_source_data)
    with pytest.raises(ValidationError, match="exactly bound|cross-bound"):
        PublicationGovernanceChain(
            **{
                **{
                    name: getattr(chain, name)
                    for name in PublicationGovernanceChain.model_fields
                },
                "source_intent_record": bad_source,
            }
        )
    original_branch = chain.branch_rules_observation_chain[0]
    bad_branch_data = original_branch.observation_record.model_dump(
        mode="python", exclude={"content_hash"}
    )
    bad_branch_data["projection"] = {
        "head_ref": chain.manifest.head_ref,
        "protected": True,
    }
    bad_branch_observation = seal_record(GitHubObservation, bad_branch_data)
    bad_branch = original_branch.model_copy(
        update={"observation_record": bad_branch_observation}
    )
    with pytest.raises(ValidationError, match="exactly bound|cross-bound"):
        PublicationGovernanceChain(
            **{
                **{
                    name: getattr(chain, name)
                    for name in PublicationGovernanceChain.model_fields
                },
                "branch_rules_observation_chain": (bad_branch,),
            }
        )


def test_governance_chain_rejects_unaccepted_scope_record() -> None:
    chain, _rate, _artifacts, _now = _governed_fixture()
    rejected = chain.scope_review_record.model_copy(
        update={"scope_status": "expansion_detected", "human_review_required": True}
    )
    with pytest.raises(ValidationError, match="scope chain"):
        PublicationGovernanceChain(
            **{
                **{
                    name: getattr(chain, name)
                    for name in PublicationGovernanceChain.model_fields
                },
                "scope_review_record": rejected,
            }
        )


def test_branch_rules_and_ruleset_record_substitution_fails_before_response(
    tmp_path,
) -> None:
    chain, rate, artifacts, now = _governed_fixture()
    for field_name in ("branch_rules_observation_chain", "ruleset_observation_chain"):
        original_evidence = getattr(chain, field_name)[0]
        stale_record = original_evidence.observation_record.model_copy(
            update={"observed_at": "2026-09-09T23:00:00Z"}
        )
        stale_evidence = original_evidence.model_copy(
            update={"observation_record": stale_record}
        )
        stale_chain = chain.model_copy(update={field_name: (stale_evidence,)})
        responses = Loopback(40).prepare(chain, rate, artifacts)
        with pytest.raises(ValueError, match="PUBLICATION_INPUT_MISMATCH"):
            evaluate_governed_publication(
                governance=stale_chain,
                rate_observation_record=rate,
                **_stored_inputs(tmp_path / field_name, chain, rate, artifacts),
                transcript=responses,
                now=now,
                configured_principal="Arthur",
            )
        assert not _evidence_directory(tmp_path / field_name, chain).exists()


def test_exact_dispatches_hash_canonical_request_bodies() -> None:
    chain, _rate, artifacts, _now = _governed_fixture()
    rows = build_exact_publication_dispatches(
        chain.manifest, chain.repository_profile_record, artifacts
    )
    blob = rows[1]
    assert json.loads(blob.body) == {"content": "aGVsbG8K", "encoding": "base64"}
    assert blob.request_hash != "sha256:" + hashlib.sha256(b"proposal").hexdigest()
    tree = rows[3]
    assert json.loads(tree.body)["base_tree"] == chain.manifest.base_tree_oid
    assert json.loads(tree.body)["tree"][0]["sha"] == chain.manifest.files[0].blob_oid


@pytest.mark.parametrize(
    "value",
    (
        "refs/heads/main?x=y",
        "refs/heads/main:port",
        "refs/heads/main branch",
        "refs/heads/main\x00tail",
        "refs/heads/main..tail",
        "refs/heads/.hidden",
        "refs/heads/topic.lock",
        "refs/heads/topic.LOCK",
        "refs/heads/decomposed-e\u0301",
    ),
)
def test_canonical_github_ref_target_rejects_invalid_git_refs(value: str) -> None:
    with pytest.raises(ValueError, match="ref"):
        canonical_github_ref_target(value)


@pytest.mark.parametrize(
    ("value", "path_form", "query_form"),
    (
        ("refs/heads/release#1", "heads/release%231", "release%231"),
        ("refs/heads/a&b=c", "heads/a%26b%3Dc", "a%26b%3Dc"),
        ("refs/heads/100%done", "heads/100%25done", "100%25done"),
        ("refs/heads/caf\u00e9/ready", "heads/caf%C3%A9/ready", "caf%C3%A9%2Fready"),
        ("refs/heads/%ZZ", "heads/%25ZZ", "%25ZZ"),
    ),
)
def test_canonical_github_ref_target_encodes_valid_refs(
    value: str, path_form: str, query_form: str
) -> None:
    assert canonical_github_ref_target(value) == (path_form, query_form)


@pytest.mark.parametrize(
    "value",
    (
        "refs/heads/main?x=y",
        "refs/heads/main branch",
        "refs/heads/main\x1ftail",
        "refs/tags/main",
    ),
)
def test_manifest_rejects_invalid_base_ref_before_planning(value: str) -> None:
    chain, _rate, _artifacts, _now = _governed_fixture()
    payload = chain.manifest.model_dump(mode="python", exclude={"content_hash"})
    payload["base_ref"] = value
    with pytest.raises(ValidationError, match="ref"):
        seal_record(ProposalManifest, payload)


def test_exact_dispatches_use_encoded_base_ref_targets() -> None:
    chain, _rate, artifacts, _now = _governed_fixture()
    base_ref = "refs/heads/release#1&ready=yes%"
    manifest = chain.manifest.model_copy(update={"base_ref": base_ref})
    profile = chain.repository_profile_record.model_copy(
        update={"allowed_base_refs": (base_ref,)}
    )
    rows = build_exact_publication_dispatches(manifest, profile, artifacts)
    targets = tuple(row.target for row in rows)
    assert targets[6].endswith("/git/ref/heads/release%231%26ready%3Dyes%25")
    assert targets[11].endswith("/git/ref/heads/release%231%26ready%3Dyes%25")
    assert "&base=release%231%26ready%3Dyes%25&per_page=2&page=1" in targets[12]
    assert all(target.isascii() for target in targets)


def test_fixture_transcript_rejects_executable_response_fields_without_invocation():
    invoked = False

    class ExecutableHeaders:
        def __iter__(self):
            nonlocal invoked
            invoked = True
            yield ("X-RateLimit-Remaining", "40")

    response = GitHubTransportResponse(
        status=200,
        headers=ExecutableHeaders(),
        body=b"{}",
    )
    with pytest.raises(ValueError, match="PUBLICATION_INPUT_MISMATCH"):
        FixtureTranscriptEntry(
            planned_request_hash="sha256:" + "1" * 64,
            response=response,
        )
    assert not invoked


def test_fixture_transcript_copies_only_exact_immutable_response_values():
    source = GitHubTransportResponse(
        status=200,
        headers=(("X-RateLimit-Remaining", "40"),),
        body=b"{}",
    )
    transcript = OfflinePublicationTranscript(
        entries=(
            FixtureTranscriptEntry(
                planned_request_hash="sha256:" + "1" * 64,
                response=source,
            ),
        )
    )
    retained = transcript.entries[0].response
    assert retained is not source
    assert type(retained.status) is int
    assert type(retained.headers) is tuple
    assert all(type(header) is tuple for header in retained.headers)
    assert retained.headers == (("x-ratelimit-remaining", "40"),)
    assert type(retained.body) is bytes


@pytest.mark.parametrize("marker_kind", ["directory", "file"])
def test_publication_rejects_workspace_that_is_itself_a_git_repository(
    tmp_path, marker_kind
):
    chain, rate, artifacts, now = _governed_fixture()
    inputs = _stored_inputs(tmp_path, chain, rate, artifacts)
    marker = inputs["workspace"].root / ".git"
    if marker_kind == "directory":
        marker.mkdir()
    else:
        marker.write_text("gitdir: elsewhere\n", encoding="utf-8")
    transcript = Loopback(40).prepare(chain, rate, artifacts)

    with pytest.raises(ValueError, match="PUBLICATION_INPUT_MISMATCH"):
        evaluate_governed_publication(
            governance=chain,
            rate_observation_record=rate,
            **inputs,
            transcript=transcript,
            now=now,
            configured_principal="Arthur",
        )

    assert not _evidence_directory(tmp_path, chain).exists()


def test_manifest_rejects_unsafe_route_and_unbound_aggregate() -> None:
    chain, _rate, _artifacts, _now = _governed_fixture()
    data = chain.manifest.model_dump(mode="json", exclude={"content_hash"})
    data["owner"] = "evil/x?y"
    for key in ("files", "allowed_paths"):
        data[key] = tuple(data[key])
    with pytest.raises(ValidationError, match="canonical GitHub login"):
        seal_record(ProposalManifest, data)
    data["owner"] = chain.manifest.owner
    data["aggregate_manifest_hash"] = "sha256:" + "0" * 64
    with pytest.raises(ValidationError, match="aggregate manifest hash mismatch"):
        seal_record(ProposalManifest, data)


def test_predecessor_reopen_and_controlled_artifact_reader_fail_closed(
    tmp_path,
) -> None:
    chain, rate, artifacts, now = _governed_fixture()
    roots = _stored_inputs(tmp_path, chain, rate, artifacts)
    plan_path = roots["workspace"].root / Path(
        *chain.operation_intent.plan.reference.split("/")
    )
    plan_path.write_bytes(
        plan_path.read_bytes().replace(b'"plan_id": "plan-1"', b'"plan_id": "plan-X"')
    )
    transport = Loopback(40)
    transport.scope_hash = rate_scope_hash(rate)
    with pytest.raises(ValueError, match="PUBLICATION_INPUT_MISMATCH"):
        evaluate_governed_publication(
            governance=chain,
            rate_observation_record=rate,
            **roots,
            transcript=transport.prepare(chain, rate, artifacts),
            now=now,
            configured_principal="Arthur",
        )


@pytest.mark.parametrize(
    "component",
    ("provider", "authorization", "intent", "claim", "lease", "observation"),
)
@pytest.mark.parametrize("damage", ("missing", "altered"))
def test_complete_rate_source_chain_is_reopened_before_claim(
    tmp_path, component, damage
):
    chain, rate, artifacts, now = _governed_fixture()
    root = tmp_path / f"{component}-{damage}"
    inputs = _stored_inputs(root, chain, rate, artifacts)
    evidence = chain.rate_source_observation_chain
    reference = {
        "provider": evidence.provider_key_reference,
        "authorization": evidence.observation_record.authorization,
        "intent": evidence.observation_record.intent,
        "claim": evidence.observation_record.attempt_claim,
        "lease": evidence.observation_record.lease_evidence,
        "observation": evidence.observation_reference,
    }[component]
    path = inputs["workspace"].root / Path(*reference.reference.split("/"))
    if damage == "missing":
        path.unlink()
    else:
        path.write_bytes(b"{}")

    with pytest.raises((ValueError, OSError)):
        evaluate_governed_publication(
            governance=chain,
            rate_observation_record=rate,
            **inputs,
            transcript=Loopback(40).prepare(chain, rate, artifacts),
            now=now,
            configured_principal="Arthur",
        )

    assert not _evidence_directory(root, chain).exists()


def test_controlled_artifact_reader_refuses_links(tmp_path, monkeypatch) -> None:
    target = tmp_path / "target.txt"
    target.write_bytes(b"secret")
    link = tmp_path / "artifact.txt"
    try:
        link.symlink_to(target)
    except OSError:
        link.write_bytes(b"not-read")
        original_lstat = Path.lstat

        class ReparseInfo:
            def __init__(self, wrapped):
                self._wrapped = wrapped
                self.st_file_attributes = 0x400

            def __getattr__(self, name):
                return getattr(self._wrapped, name)

        def injected_lstat(path):
            value = original_lstat(path)
            return ReparseInfo(value) if path == link else value

        monkeypatch.setattr(Path, "lstat", injected_lstat)
    reference = RecordReference(
        reference="artifact.txt",
        content_hash="sha256:" + hashlib.sha256(b"secret").hexdigest(),
    )
    with pytest.raises(ValueError, match="PROPOSAL_CONTENT_CHANGED"):
        read_artifacts_once(tmp_path, (reference,))


def test_artifact_alias_is_opened_once_and_conflicting_alias_is_refused(
    tmp_path, monkeypatch
) -> None:
    artifact = tmp_path / "artifact.txt"
    artifact.write_bytes(b"one read")
    digest = "sha256:" + hashlib.sha256(b"one read").hexdigest()
    reference = RecordReference(reference="artifact.txt", content_hash=digest)
    calls = 0
    original_open = os.open

    def counted_open(path, *args, **kwargs):
        nonlocal calls
        if Path(path).name == "artifact.txt":
            calls += 1
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", counted_open)
    assert (
        read_artifacts_once(tmp_path, (reference, reference))["artifact.txt"]
        == b"one read"
    )
    assert calls == 1
    conflicting = RecordReference(
        reference="artifact.txt", content_hash="sha256:" + "0" * 64
    )
    with pytest.raises(ValueError, match="PROPOSAL_CONTENT_CHANGED"):
        read_artifacts_once(tmp_path, (reference, conflicting))


@pytest.mark.parametrize("alias", ["a//b", "a/./b", "a/b/", "a\\b"])
def test_artifact_reader_rejects_raw_path_aliases_before_deduplication(
    tmp_path, alias
) -> None:
    with pytest.raises(ValueError):
        reference = RecordReference(
            reference=alias, content_hash="sha256:" + hashlib.sha256(b"x").hexdigest()
        )
        read_artifacts_once(tmp_path, (reference,))


@pytest.mark.parametrize(
    "field",
    ["increment_21_hash", "stage_21a_hash", "stage_21b_hash", "erratum_hash"],
)
def test_base_tree_closure_rejects_each_substituted_protocol_pin(field) -> None:
    chain, _rate, _artifacts, _now = _governed_fixture()
    data = chain.base_tree_closure.model_dump(mode="json", exclude={"content_hash"})
    data["entries"] = tuple(data["entries"])
    data[field] = "sha256:" + "0" * 64
    with pytest.raises(ValidationError, match="protocol identity mismatch"):
        seal_record(BaseTreeClosure, data)


@pytest.mark.parametrize("bad", [1.0, float("nan"), float("inf")])
def test_response_projection_rejects_all_float_forms(tmp_path, bad) -> None:
    chain, rate, artifacts, now = _governed_fixture()

    class FloatProjection(Loopback):
        def response_for(self, dispatch):
            response = super().response_for(dispatch)
            if dispatch.ordinal == 1:
                return GitHubTransportResponse(
                    status=response.status,
                    headers=response.headers,
                    body=json.dumps({"id": 1, "owner": {"id": bad}}).encode(),
                )
            return response

    transport = FloatProjection(40).prepare(chain, rate, artifacts)
    receipt = evaluate_governed_publication(
        governance=chain,
        rate_observation_record=rate,
        **_stored_inputs(tmp_path, chain, rate, artifacts),
        transcript=transport,
        now=now,
        configured_principal="Arthur",
    )
    assert len(receipt.step_states) == 1
    assert receipt.reason_codes == (
        "GIT_OBJECT_RESPONSE_INVALID",
        "MUTATION_DISPATCH_FAILED",
    )


def test_frozen_commit_message_and_title_limits_are_enforced() -> None:
    chain, _rate, _artifacts, _now = _governed_fixture()
    for record, field, boundary, overflow in (
        (chain.manifest, "commit_message_byte_count", 4096, 4097),
        (chain.manifest, "pull_request_title_byte_count", 256, 257),
        (chain.authorization, "commit_message_byte_count", 4096, 4097),
        (chain.authorization, "pull_request_title_byte_count", 256, 257),
    ):
        data = record.model_dump(mode="json", exclude={"content_hash"})
        for key, value in tuple(data.items()):
            if isinstance(value, list):
                data[key] = tuple(value)
        data[field] = boundary
        seal_record(type(record), data)
        data[field] = overflow
        with pytest.raises(ValidationError):
            seal_record(type(record), data)


def test_final_pr_read_is_bound_to_create_result(tmp_path) -> None:
    chain, rate, artifacts, now = _governed_fixture()
    transport = Loopback(40)
    transport.scope_hash = rate_scope_hash(rate)
    receipt = evaluate_governed_publication(
        governance=chain,
        rate_observation_record=rate,
        **_stored_inputs(tmp_path, chain, rate, artifacts),
        transcript=transport.prepare(chain, rate, artifacts),
        now=now,
        configured_principal="Arthur",
    )
    admission = json.loads(
        (_evidence_directory(tmp_path, chain) / "admission-016.json").read_text(
            encoding="utf-8"
        )
    )
    assert admission["derived_from_result"]["reference"] == "result-015.json"
    assert admission["planned_request_hash"] == chain.plan.ordered_request_hashes[-1]
    assert admission["request_body_hash"] != admission["planned_request_hash"]
    assert receipt.fixture_pull_request_number == 7


def test_ambiguous_mutation_retains_admission_state(tmp_path) -> None:
    chain, rate, artifacts, now = _governed_fixture()
    transport = Loopback(40, fail_at=2)
    transport.scope_hash = rate_scope_hash(rate)
    receipt = evaluate_governed_publication(
        governance=chain,
        rate_observation_record=rate,
        **_stored_inputs(tmp_path, chain, rate, artifacts),
        transcript=transport.prepare(chain, rate, artifacts),
        now=now,
        configured_principal="Arthur",
    )
    assert receipt.fixture_conformance_complete is False
    assert receipt.step_states[-1].state == "fixture_mutation_result_present"
    assert receipt.reason_codes == (
        "GIT_OBJECT_RESPONSE_INVALID",
        "MUTATION_OUTCOME_AMBIGUOUS",
    )


def test_dispatch_loss_retains_mutation_admitted_without_result(tmp_path) -> None:
    chain, rate, artifacts, now = _governed_fixture()

    class Loss(Loopback):
        def response_for(self, dispatch):
            response = super().response_for(dispatch)
            if dispatch.ordinal == 2:
                return GitHubTransportResponse(
                    status=response.status,
                    headers=response.headers,
                    body=b"not-json",
                )
            return response

    transport = Loss(40)
    transport.scope_hash = rate_scope_hash(rate)
    receipt = evaluate_governed_publication(
        governance=chain,
        rate_observation_record=rate,
        **_stored_inputs(tmp_path, chain, rate, artifacts),
        transcript=transport.prepare(chain, rate, artifacts),
        now=now,
        configured_principal="Arthur",
    )
    assert receipt.step_states[-1].state == "fixture_mutation_admitted_without_result"
    evidence = _evidence_directory(tmp_path, chain)
    assert (evidence / "admission-002.json").exists()
    assert not (evidence / "result-002.json").exists()


def test_rate_scope_substitution_stops_before_following_dispatch(tmp_path) -> None:
    chain, rate, artifacts, now = _governed_fixture()

    class BadRateScope(Loopback):
        def response_for(self, dispatch):
            response = super().response_for(dispatch)
            headers = tuple(
                (name, "search" if name == "X-RateLimit-Resource" else value)
                for name, value in response.headers
            )
            return GitHubTransportResponse(
                status=response.status, headers=headers, body=response.body
            )

    transport = BadRateScope(40)
    receipt = evaluate_governed_publication(
        governance=chain,
        rate_observation_record=rate,
        **_stored_inputs(tmp_path, chain, rate, artifacts),
        transcript=transport.prepare(chain, rate, artifacts),
        now=now,
        configured_principal="Arthur",
    )
    assert len(receipt.step_states) == 1
    assert receipt.reason_codes == (
        "MUTATION_DISPATCH_FAILED",
        "RATE_LIMIT_EVIDENCE_INVALID",
    )


def test_rate_limit_after_mutation_is_terminalized_without_repeat(tmp_path) -> None:
    chain, rate, artifacts, now = _governed_fixture()

    class RateLimited(Loopback):
        def response_for(self, dispatch):
            response = super().response_for(dispatch)
            if dispatch.ordinal == 2:
                return GitHubTransportResponse(
                    status=429,
                    headers=response.headers + (("Retry-After", "1"),),
                    body=response.body,
                )
            return response

    responses = RateLimited(40).prepare(chain, rate, artifacts)
    receipt = evaluate_governed_publication(
        governance=chain,
        rate_observation_record=rate,
        **_stored_inputs(tmp_path, chain, rate, artifacts),
        transcript=responses,
        now=now,
        configured_principal="Arthur",
    )
    assert len(receipt.step_states) == 2
    assert receipt.step_states[-1].state == "fixture_mutation_result_present"
    assert receipt.reason_codes == (
        "MUTATION_OUTCOME_AMBIGUOUS",
        "RATE_LIMITED",
    )
    assert (_evidence_directory(tmp_path, chain) / "receipt.json").is_file()


def test_result_store_failure_becomes_terminal_admission_state(
    tmp_path, monkeypatch
) -> None:
    import conclave.github_publication_engine as engine

    chain, rate, artifacts, now = _governed_fixture()
    responses = Loopback(40).prepare(chain, rate, artifacts)
    original = engine.write_durable_record

    def fail_second_result(path, record, **kwargs):
        if path.name == "result-002.json":
            raise OSError("injected result persistence failure")
        return original(path, record, **kwargs)

    monkeypatch.setattr(engine, "write_durable_record", fail_second_result)
    receipt = evaluate_governed_publication(
        governance=chain,
        rate_observation_record=rate,
        **_stored_inputs(tmp_path, chain, rate, artifacts),
        transcript=responses,
        now=now,
        configured_principal="Arthur",
    )
    assert receipt.step_states[-1].state == "fixture_mutation_admitted_without_result"
    assert receipt.reason_codes == (
        "MUTATION_OUTCOME_AMBIGUOUS",
        "STEP_RESULT_STORE_FAILED",
    )


def test_admission_store_failure_stops_before_response_and_writes_receipt(
    tmp_path, monkeypatch
) -> None:
    import conclave.github_publication_engine as engine

    chain, rate, artifacts, now = _governed_fixture()
    responses = Loopback(40).prepare(chain, rate, artifacts)
    original = engine.write_durable_record

    def fail_admission(path, record, **kwargs):
        if path.name == "admission-001.json":
            raise OSError("injected admission persistence failure")
        return original(path, record, **kwargs)

    monkeypatch.setattr(engine, "write_durable_record", fail_admission)
    receipt = evaluate_governed_publication(
        governance=chain,
        rate_observation_record=rate,
        **_stored_inputs(tmp_path, chain, rate, artifacts),
        transcript=responses,
        now=now,
        configured_principal="Arthur",
    )
    assert receipt.step_states == ()
    assert receipt.reason_codes == ("STEP_ADMISSION_STORE_FAILED",)
    assert (_evidence_directory(tmp_path, chain) / "receipt.json").is_file()


def test_claim_replay_maps_stage_21b_reason_and_never_consumes_response(
    tmp_path,
) -> None:
    chain, rate, artifacts, now = _governed_fixture()
    first = Loopback(40).prepare(chain, rate, artifacts)
    inputs = _stored_inputs(tmp_path, chain, rate, artifacts)
    evaluate_governed_publication(
        governance=chain,
        rate_observation_record=rate,
        **inputs,
        transcript=first,
        now=now,
        configured_principal="Arthur",
    )
    second = Loopback(40).prepare(chain, rate, artifacts)
    with pytest.raises(ValueError, match="PUBLICATION_ALREADY_CLAIMED"):
        evaluate_governed_publication(
            governance=chain,
            rate_observation_record=rate,
            **inputs,
            transcript=second,
            now=now,
            configured_principal="Arthur",
        )
    assert len(second.entries) == 16


def test_dual_clock_discontinuity_and_monotonic_expiry_fail_before_response(
    tmp_path,
) -> None:
    chain, rate, artifacts, now = _governed_fixture()
    for dispatch_time, elapsed in (("2026-09-09T23:59:59Z", 0), (now, 600_001)):
        root = tmp_path / str(elapsed).replace(".", "-")
        inputs = _stored_inputs(root, chain, rate, artifacts)
        inputs["first_dispatch_check_at"] = dispatch_time
        inputs["monotonic_elapsed_milliseconds"] = elapsed
        responses = Loopback(40).prepare(chain, rate, artifacts)
        with pytest.raises(ValueError, match="PUBLICATION_AUTH_EXPIRED"):
            evaluate_governed_publication(
                governance=chain,
                rate_observation_record=rate,
                **inputs,
                transcript=responses,
                now=now,
                configured_principal="Arthur",
            )
        assert not list(_evidence_directory(root, chain).glob("admission-*.json"))


def test_ambiguous_ref_is_not_recorded_as_not_attempted(tmp_path) -> None:
    chain, rate, artifacts, now = _governed_fixture()
    transport = Loopback(40, fail_at=10)
    transport.scope_hash = rate_scope_hash(rate)
    receipt = evaluate_governed_publication(
        governance=chain,
        rate_observation_record=rate,
        **_stored_inputs(tmp_path, chain, rate, artifacts),
        transcript=transport.prepare(chain, rate, artifacts),
        now=now,
        configured_principal="Arthur",
    )
    assert receipt.branch_fixture_outcome == "FIXTURE_AMBIGUOUS"
    assert receipt.pull_request_fixture_outcome == "NOT_EVALUATED"


@pytest.mark.parametrize(
    ("ordinal", "reason", "branch_result", "pull_request_result"),
    (
        (8, "HEAD_REF_EXISTS", "FIXTURE_CONFLICT", "NOT_EVALUATED"),
        (13, "PR_ALREADY_EXISTS", "FIXTURE_CREATED_MATCH", "FIXTURE_CONFLICT"),
    ),
)
def test_pre_dispatch_conflicts_have_factual_terminal_outcomes(
    tmp_path, ordinal, reason, branch_result, pull_request_result
) -> None:
    chain, rate, artifacts, now = _governed_fixture()
    transport = Loopback(40, fail_at=ordinal).prepare(chain, rate, artifacts)
    receipt = evaluate_governed_publication(
        governance=chain,
        rate_observation_record=rate,
        **_stored_inputs(tmp_path, chain, rate, artifacts),
        transcript=transport,
        now=now,
        configured_principal="Arthur",
    )
    assert receipt.reason_codes == (reason,)
    assert receipt.branch_fixture_outcome == branch_result
    assert receipt.pull_request_fixture_outcome == pull_request_result
    assert len(receipt.step_states) == ordinal
    assert receipt.step_states[-1].state == "fixture_read_result_present"
    evidence = _evidence_directory(tmp_path, chain)
    assert not list(evidence.glob(f"admission-{ordinal + 1:03d}.json"))
    assert not list(evidence.glob(f"result-{ordinal + 1:03d}.json"))


def test_receipt_store_failure_creates_terminal_capsule(tmp_path, monkeypatch) -> None:
    import conclave.github_publication_engine as engine

    chain, rate, artifacts, now = _governed_fixture()
    transport = Loopback(40)
    transport.scope_hash = rate_scope_hash(rate)
    original = engine.write_durable_record

    def fail_receipt(path, record, **kwargs):
        if path.name == "receipt.json":
            raise OSError("fixture persistence failure")
        return original(path, record, **kwargs)

    monkeypatch.setattr(engine, "write_durable_record", fail_receipt)
    with pytest.raises(ValueError, match="PUBLICATION_RECEIPT_STORE_FAILED"):
        evaluate_governed_publication(
            governance=chain,
            rate_observation_record=rate,
            **_stored_inputs(tmp_path, chain, rate, artifacts),
            transcript=transport.prepare(chain, rate, artifacts),
            now=now,
            configured_principal="Arthur",
        )
    assert (_evidence_directory(tmp_path, chain) / "terminal-failure.json").exists()
    assert all(
        event["event_type"] != "github_proposal_publication_fixture_verified"
        for event in ledger.read_events(Workspace(tmp_path / ".conclave"))
    )


def test_receipt_and_capsule_store_failure_remains_sanitized(
    tmp_path, monkeypatch
) -> None:
    import conclave.github_publication_engine as engine

    chain, rate, artifacts, now = _governed_fixture()
    responses = Loopback(40).prepare(chain, rate, artifacts)
    original = engine.write_durable_record

    def fail_terminal(path, record, **kwargs):
        if path.name in {"receipt.json", "terminal-failure.json"}:
            raise OSError("sensitive injected filesystem detail")
        return original(path, record, **kwargs)

    monkeypatch.setattr(engine, "write_durable_record", fail_terminal)
    with pytest.raises(ValueError) as caught:
        evaluate_governed_publication(
            governance=chain,
            rate_observation_record=rate,
            **_stored_inputs(tmp_path, chain, rate, artifacts),
            transcript=responses,
            now=now,
            configured_principal="Arthur",
        )
    assert str(caught.value) == "TERMINAL_FAILURE_STORE_FAILED"
    assert "sensitive" not in str(caught.value)


def test_malformed_post_claim_dispatch_clock_is_terminalized(
    tmp_path, monkeypatch
) -> None:
    chain, rate, artifacts, now = _governed_fixture()
    inputs = _stored_inputs(tmp_path, chain, rate, artifacts)
    inputs["first_dispatch_check_at"] = "not-a-timestamp"
    responses = Loopback(40).prepare(chain, rate, artifacts)

    with pytest.raises(ValueError) as caught:
        evaluate_governed_publication(
            governance=chain,
            rate_observation_record=rate,
            **inputs,
            transcript=responses,
            now=now,
            configured_principal="Arthur",
        )

    assert str(caught.value) == "RATE_LIMIT_EVIDENCE_INVALID"
    terminal = json.loads(
        (_evidence_directory(tmp_path, chain) / "terminal-failure.json").read_text()
    )
    assert terminal["reason_code"] == "RATE_LIMIT_EVIDENCE_INVALID"
    assert terminal["step_states"] == []


def test_terminal_capsule_construction_failure_is_sanitized(
    tmp_path, monkeypatch
) -> None:
    import conclave.github_publication_engine as engine

    chain, rate, artifacts, now = _governed_fixture()
    responses = Loopback(40).prepare(chain, rate, artifacts)
    original = engine.seal_record

    def fail_capsule(model, payload):
        if model is engine.PublicationTerminalFailure:
            raise RuntimeError("sensitive capsule construction detail")
        return original(model, payload)

    monkeypatch.setattr(engine, "seal_record", fail_capsule)
    inputs = _stored_inputs(tmp_path, chain, rate, artifacts)
    inputs["first_dispatch_check_at"] = "not-a-timestamp"
    with pytest.raises(ValueError) as caught:
        evaluate_governed_publication(
            governance=chain,
            rate_observation_record=rate,
            **inputs,
            transcript=responses,
            now=now,
            configured_principal="Arthur",
        )

    assert str(caught.value) == "TERMINAL_FAILURE_STORE_FAILED"
    assert "sensitive" not in str(caught.value)


def test_ledger_failure_preserves_receipt_and_is_sanitized(
    tmp_path, monkeypatch
) -> None:
    import conclave.github_publication_engine as engine

    chain, rate, artifacts, now = _governed_fixture()
    responses = Loopback(40).prepare(chain, rate, artifacts)
    monkeypatch.setattr(
        engine,
        "record_event",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("sensitive ledger detail")
        ),
    )
    with pytest.raises(ValueError) as caught:
        evaluate_governed_publication(
            governance=chain,
            rate_observation_record=rate,
            **_stored_inputs(tmp_path, chain, rate, artifacts),
            transcript=responses,
            now=now,
            configured_principal="Arthur",
        )
    assert str(caught.value) == "PUBLICATION_INPUT_MISMATCH"
    assert (_evidence_directory(tmp_path, chain) / "receipt.json").is_file()


def test_publication_modules_have_no_live_network_or_credential_runtime() -> None:
    from pathlib import Path

    root = Path(__file__).parents[1] / "src" / "conclave"
    text = (root / "github_publication.py").read_text(encoding="utf-8")
    text += (root / "github_publication_engine.py").read_text(encoding="utf-8")
    for prohibited in (
        "import socket",
        "import http.client",
        "import ssl",
        "subprocess",
        "api.github.com",
    ):
        assert prohibited not in text
    for prohibited_surface in (
        "FixturePublicationResponse",
        "LoopbackPublicationTransport",
        "execute_governed_fixture_publication",
        "reconcile_fixture_publication",
    ):
        assert prohibited_surface not in text
