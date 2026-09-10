from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from conclave.github_foundation import (
    RecordReference,
    write_durable_record,
)
from conclave.github_publication import (
    BaseTreeClosure,
    RecursiveTreeEntry,
    RecursiveTreeObservation,
    INCREMENT_21_PROTOCOL_HASH,
    STAGE_21A_PROTOCOL_HASH,
    STAGE_21B_ERRATUM_HASH,
    STAGE_21B_PROTOCOL_HASH,
    apply_proposal,
    canonical_closure_entries_bytes,
    reconstruct_tree_oid,
)
from conclave.github_publication_engine import (
    MutationAdmittedWithoutResult,
    PublicationStepAdmission,
    RateBudgetObservation,
    TerminalArtifactInventory,
)
from conclave.github_publication_records import (
    CommitIdentity,
    PUBLICATION_LEASE_CLAIMS_DOMAIN,
    ProposalFile,
    ProposalManifest,
    PublicationAttemptClaim,
    PublicationLeaseClaims,
    PublicationLeaseEvidence,
    PublicationPlan,
    proposal_aggregate_hash,
)
from conclave.github_publication_reconciliation import (
    FixtureReadTranscript,
    BlobReadProjection,
    CommitReadProjection,
    PullRequestMatch,
    PullRequestReadProjection,
    ReconciliationBundle,
    RefReadProjection,
    RetainedPublicationSubject,
    TreeReadProjection,
    assemble_fixture_reconciliation,
    derive_expected_identity,
    persist_fixture_reconciliation,
    validate_retained_publication_directories,
    fixture_read_request_hash,
    fixture_read_target,
    _hash_json,
)
from conclave.identity import seal_record
from conclave.workspace import Workspace
from test_github_publication import (
    _stage21a_fixture_context,
    _stage21a_observation_evidence,
)
from test_github_foundation import _sign_model

FOUNDATION_CREATED = "2026-09-10T00:00:00Z"
NOW = "2026-09-10T00:00:30Z"
EXPIRY = "2026-09-10T00:10:00Z"
H = "sha256:" + "a" * 64
BASE_COMMIT = "1" * 40
BLOB = "3" * 40
PROPOSAL_COMMIT = "5" * 40
ATTEMPT = "publication:sha256:" + "6" * 64
HEAD_REF = "refs/heads/conclave/018f0c10-7b58-7a22-8b0d-123456789abc/proposal"
ENDPOINTS = (
    "repository.get",
    "git_blob.create",
    "repository.get",
    "git_tree.create",
    "repository.get",
    "git_commit.create",
    "ref.get",
    "matching_refs.list",
    "repository.get",
    "git_ref.create",
    "ref.get",
    "ref.get",
    "pull_requests.matching.list",
    "repository.get",
    "pull_request.create",
    "pull_request.get",
)
REQUESTS = tuple("sha256:" + f"{i:064x}" for i in range(1, 17))


def rr(name: str, content_hash: str = H) -> RecordReference:
    return RecordReference(reference=name + ".json", content_hash=content_hash)


def expected_hash(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def store(directory: Path, name: str, record) -> RecordReference:
    path, _ = write_durable_record(directory / f"{name}.json", record)
    return RecordReference(reference=path.name, content_hash=record.content_hash)


def store_reference(directory: Path, reference: str, record) -> RecordReference:
    path = directory / reference
    path.parent.mkdir(parents=True, exist_ok=True)
    written, _ = write_durable_record(path, record)
    return RecordReference(
        reference=written.relative_to(directory).as_posix(),
        content_hash=record.content_hash,
    )


def retained_fixture(root: Path, operation_key: str):
    records, evidence = root / "records", root / "original-evidence"
    records.mkdir(parents=True)
    evidence.mkdir(parents=True)
    private_key, provider, repository, api = _stage21a_fixture_context(
        FOUNDATION_CREATED
    )
    provider_ref = store_reference(records, repository.provider_key_reference, provider)
    repository_ref = store_reference(
        records, "github/fixture/repository-profile.json", repository
    )
    api_ref = store_reference(records, "github/fixture/api-profile.json", api)
    base_entries = (
        RecursiveTreeEntry(path="README.md", mode="100644", type="blob", oid="7" * 40),
    )
    base_tree = reconstruct_tree_oid(base_entries, "sha1")
    source = seal_record(
        RecursiveTreeObservation,
        {
            "observation_id": "source-1",
            "repository_profile": repository_ref,
            "api_profile": api_ref,
            "base_observation": rr("base-observation"),
            "authorization": rr("source-authorization"),
            "intent": rr("source-intent"),
            "attempt_claim": rr("source-claim"),
            "lease_evidence": rr("source-lease"),
            "repository_id": 101,
            "account_id": 202,
            "base_ref": "refs/heads/main",
            "base_commit_oid": BASE_COMMIT,
            "root_tree_oid": base_tree,
            "object_format": "sha1",
            "response_bytes": 256,
            "entries": base_entries,
            "created_at": NOW,
        },
    )
    source_ref = store(records, "base-tree-source", source)
    closure = seal_record(
        BaseTreeClosure,
        {
            "closure_id": "closure-1",
            "increment_21_hash": INCREMENT_21_PROTOCOL_HASH,
            "stage_21a_hash": STAGE_21A_PROTOCOL_HASH,
            "stage_21b_hash": STAGE_21B_PROTOCOL_HASH,
            "erratum_hash": STAGE_21B_ERRATUM_HASH,
            "repository_profile": repository_ref,
            "api_profile": api_ref,
            "base_observation": source.base_observation,
            "source_observation": source_ref,
            "source_authorization": source.authorization,
            "source_intent": source.intent,
            "source_attempt_claim": source.attempt_claim,
            "source_lease_evidence": source.lease_evidence,
            "repository_extension": rr("repository-extension"),
            "repository_id": 101,
            "account_id": 202,
            "base_ref": "refs/heads/main",
            "base_commit_oid": BASE_COMMIT,
            "base_root_tree_oid": base_tree,
            "object_format": "sha1",
            "entries": base_entries,
            "entry_count": 1,
            "canonical_byte_count": len(canonical_closure_entries_bytes(base_entries)),
            "recomputed_base_root_tree_oid": base_tree,
            "base_observed_at": NOW,
            "source_observed_at": NOW,
            "created_at": NOW,
        },
    )
    closure_ref = store(records, "base-tree-closure", closure)
    rate = seal_record(
        RateBudgetObservation,
        {
            "source_observation": rr("rate-source"),
            "repository_profile": repository_ref,
            "api_profile": api_ref,
            "repository_id": 101,
            "account_id": 202,
            "app_id": 303,
            "installation_id": 404,
            "provider_id": "fixture-provider",
            "provider_version": "v1",
            "provider_key": provider_ref,
            "provider_public_key_sha256": provider.public_key_sha256,
            "api_version": "2026-03-10",
            "resource_bucket": "core",
            "limit": 5000,
            "remaining": 40,
            "reset_at": None,
            "retry_after_present": False,
            "observed_at": NOW,
            "created_at": NOW,
        },
    )
    rate_ref = store(records, "rate", rate)
    file = ProposalFile(
        path="docs/proposal.md",
        byte_count=7,
        content_sha256="sha256:" + "c" * 64,
        blob_oid=BLOB,
        artifact=rr("proposal-artifact", "sha256:" + "c" * 64),
    )
    proposal_tree = apply_proposal(base_entries, (file,), "sha1")
    manifest = seal_record(
        ProposalManifest,
        {
            "manifest_id": "manifest-1",
            "repository_profile": repository_ref,
            "api_profile": api_ref,
            "repository_extension": closure.repository_extension,
            "repository_id": 101,
            "account_id": 202,
            "owner": "komistry-labs",
            "repository": "conclave",
            "task_packet": rr("task"),
            "handoff": rr("handoff"),
            "scope_review": rr("scope"),
            "base_observation": closure.base_observation,
            "base_tree_closure": closure_ref,
            "branch_rules_observation": rr("branch-rules"),
            "ruleset_observation": rr("ruleset"),
            "base_ref": "refs/heads/main",
            "base_commit_oid": BASE_COMMIT,
            "base_tree_oid": base_tree,
            "head_ref": HEAD_REF,
            "object_format": "sha1",
            "files": (file,),
            "allowed_paths": (file.path,),
            "aggregate_byte_count": file.byte_count,
            "aggregate_manifest_hash": proposal_aggregate_hash((file,)),
            "commit_message": rr("message", "sha256:" + "d" * 64),
            "commit_message_byte_count": 7,
            "commit_identity": CommitIdentity(
                name="Arthur", email="arthur@example.test", timestamp=NOW
            ),
            "commit_identity_artifact": rr("identity"),
            "pull_request_title": rr("title", "sha256:" + "e" * 64),
            "pull_request_title_byte_count": 5,
            "pull_request_body": rr("body", "sha256:" + "f" * 64),
            "pull_request_body_byte_count": 4,
            "proposal_tree_oid": proposal_tree,
            "proposal_commit_oid": PROPOSAL_COMMIT,
            "created_at": NOW,
        },
    )
    manifest_ref = store(records, "manifest", manifest)
    upstream = tuple(rr(f"upstream-{i}") for i in range(17))
    plan = seal_record(
        PublicationPlan,
        {
            "plan_id": "plan-1",
            "authorization": rr("publication-auth"),
            "manifest": manifest_ref,
            "rate_observation": rate_ref,
            "upstream_records": upstream,
            "rate_scope_hash": H,
            "blob_request_hashes": (REQUESTS[1],),
            "expected_blob_oids": (BLOB,),
            "tree_request_hash": REQUESTS[3],
            "commit_request_hash": REQUESTS[5],
            "ref_request_hash": REQUESTS[9],
            "pull_request_request_hash": REQUESTS[14],
            "ordered_endpoint_plan": ENDPOINTS,
            "ordered_request_hashes": REQUESTS,
            "expected_tree_oid": proposal_tree,
            "expected_commit_oid": PROPOSAL_COMMIT,
            "base_ref": manifest.base_ref,
            "head_ref": manifest.head_ref,
            "maximum_total_requests": 16,
            "created_at": NOW,
        },
    )
    plan_ref = store(records, "plan", plan)
    claim = seal_record(
        PublicationAttemptClaim,
        {
            "attempt_id": ATTEMPT,
            "authorization": plan.authorization,
            "manifest": manifest_ref,
            "plan": plan_ref,
            "operation_intent": rr("operation-intent"),
            "publication_intent": rr("publication-intent"),
            "rate_observation": rate_ref,
            "upstream_records": upstream,
            "provider_key": provider_ref,
            "provider_public_key_sha256": provider.public_key_sha256,
            "created_at": NOW,
        },
    )
    claim_ref = store(evidence, "original-claim", claim)
    resolution_nonce_hash = (
        "sha256:" + hashlib.sha256(b"reconciliation-publication-lease").hexdigest()
    )
    publication_claims = _sign_model(
        PublicationLeaseClaims,
        {
            "provider_id": provider.provider_id,
            "provider_version": "v1",
            "key_id": provider.key_id,
            "lease_id": "reconciliation-publication-lease",
            "repository_profile_hash": repository.content_hash,
            "api_profile_hash": api.content_hash,
            "authorization_hash": claim.authorization.content_hash,
            "plan_hash": plan.content_hash,
            "operation_intent_hash": claim.operation_intent.content_hash,
            "publication_intent_hash": claim.publication_intent.content_hash,
            "attempt_claim_hash": claim.content_hash,
            "attempt_id": claim.attempt_id,
            "rate_observation_hash": rate.content_hash,
            "rate_scope_hash": H,
            "app_id": repository.expected_app_id,
            "installation_id": repository.expected_installation_id,
            "account_id": repository.account_id,
            "repository_ids": (repository.repository_id,),
            "api_version": api.api_version,
            "resource_bucket": "core",
            "maximum_mutation_requests": 5,
            "maximum_total_requests": 16,
            "minted_at": NOW,
            "expires_at": EXPIRY,
            "resolution_nonce_hash": resolution_nonce_hash,
            "provider_authentication_key_id": provider.key_id,
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
            "attempt_claim": claim_ref,
            "authorization": claim.authorization,
            "operation_intent": claim.operation_intent,
            "publication_intent": claim.publication_intent,
            "plan": plan_ref,
            "rate_observation": rate_ref,
            "provider_key": provider_ref,
            "provider_public_key_sha256": provider.public_key_sha256,
            "provider_claims": publication_claims,
            "provider_claims_hash": "sha256:"
            + hashlib.sha256(publication_claims_bytes).hexdigest(),
            "claims_signature_validated_at": NOW,
            "resolution_nonce_hash": resolution_nonce_hash,
            "rate_scope_hash": H,
            "repository_profile": repository_ref,
            "api_profile": api_ref,
            "repository_id": 101,
            "account_id": 202,
            "app_id": 303,
            "installation_id": 404,
            "provider_id": "fixture-provider",
            "provider_version": "v1",
            "api_version": "2026-03-10",
            "resource_bucket": "core",
            "ordered_endpoint_plan": ENDPOINTS,
            "maximum_mutation_requests": 5,
            "maximum_total_requests": 16,
            "first_rate_check_at": NOW,
            "created_at": NOW,
        },
    )
    lease_ref = store(evidence, "original-lease", lease)
    ordinal = ENDPOINTS.index(operation_key) + 1
    projections = {
        "git_blob.create": {"oid": BLOB},
        "git_tree.create": {"oid": proposal_tree},
        "git_commit.create": {
            "oid": PROPOSAL_COMMIT,
            "tree_oid": proposal_tree,
            "parents": [BASE_COMMIT],
        },
        "git_ref.create": {"ref": HEAD_REF, "oid": PROPOSAL_COMMIT},
        "pull_request.create": {
            "repository_id": 101,
            "head_ref": HEAD_REF,
            "head_oid": PROPOSAL_COMMIT,
            "base_ref": manifest.base_ref,
            "base_oid": BASE_COMMIT,
            "title_hash": manifest.pull_request_title.content_hash,
            "body_hash": manifest.pull_request_body.content_hash,
        },
    }
    admission = seal_record(
        PublicationStepAdmission,
        {
            "attempt_id": ATTEMPT,
            "step_id": ATTEMPT + f"-{ordinal:03d}",
            "ordinal": ordinal,
            "operation_key": operation_key,
            "planned_request_hash": REQUESTS[ordinal - 1],
            "request_body_hash": REQUESTS[ordinal - 1],
            "expected_identity": expected_hash(projections[operation_key]),
            "local_budget_before": 17 - ordinal,
            "local_budget_after": 16 - ordinal,
            "rate_observation": rate_ref,
            "attempt_claim": claim_ref,
            "lease_evidence": lease_ref,
            "provider_key": provider_ref,
            "provider_public_key_sha256": provider.public_key_sha256,
            "repository_identity_observation": rr("repository-recheck"),
            "created_at": NOW,
        },
    )
    admission_ref = store(evidence, "ambiguous-admission", admission)
    state = MutationAdmittedWithoutResult(
        step_id=admission.step_id,
        admission=admission_ref,
        repository_identity_observation=admission.repository_identity_observation,
    )
    terminal = seal_record(
        TerminalArtifactInventory,
        {
            "original_claim": claim_ref,
            "last_step_record": admission_ref,
            "receipt_present": False,
            "failure_capsule_present": False,
            "step_state_inventory_hash": _hash_json([state.model_dump(mode="json")]),
            "created_at": NOW,
        },
    )
    terminal_ref = store(evidence, "terminal-inventory", terminal)
    retained = RetainedPublicationSubject(
        manifest=manifest,
        manifest_reference=manifest_ref,
        plan=plan,
        plan_reference=plan_ref,
        original_claim=claim,
        original_claim_reference=claim_ref,
        original_lease=lease,
        original_lease_reference=lease_ref,
        ambiguous_admission=admission,
        ambiguous_admission_reference=admission_ref,
        original_step_states=(state,),
        base_tree_closure=closure_ref,
        base_tree_source_observation=source_ref,
        rate_observation=rate_ref,
        terminal_inventory=terminal_ref,
        repository_profile=repository_ref,
        api_profile=api_ref,
        provider_key=provider_ref,
        provider_public_key_sha256=provider.public_key_sha256,
    )
    foundation = _stage21a_observation_evidence(
        private_key=private_key,
        provider_key=provider,
        profile=repository,
        api=api,
        operation_key="repository.get",
        path_parameters={},
        query_parameters={},
        projection={"repository_id": repository.repository_id},
        item_count=1,
        suffix="reconciliation-foundation",
        authorization_id="018f0c10-7b58-7a22-8b0d-123456789ab1",
        intent_id="018f0c10-7b58-7a22-8b0d-123456789ab2",
        observation_id="018f0c10-7b58-7a22-8b0d-123456789ab3",
        created=FOUNDATION_CREATED,
    )
    store_reference(
        records,
        foundation.intent_record.authorization.reference,
        foundation.authorization_record,
    )
    store_reference(
        records,
        foundation.attempt_claim_record.intent.reference,
        foundation.intent_record,
    )
    store_reference(
        records,
        foundation.lease_evidence_record.attempt_claim.reference,
        foundation.attempt_claim_record,
    )
    store_reference(
        records,
        foundation.observation_record.lease_evidence.reference,
        foundation.lease_evidence_record,
    )
    store_reference(
        records,
        foundation.observation_reference.reference,
        foundation.observation_record,
    )
    return retained, records, evidence, closure, foundation


def accepted(retained: RetainedPublicationSubject, closure: BaseTreeClosure):
    key = retained.ambiguous_admission.operation_key
    expected = derive_expected_identity(
        manifest=retained.manifest,
        plan=retained.plan,
        admission=retained.ambiguous_admission,
        base_tree_closure=closure,
    )
    if key == "git_blob.create":
        projection = BlobReadProjection(
            present=True, oid=BLOB, content_sha256="sha256:" + "c" * 64, byte_count=7
        )
    elif key == "git_tree.create":
        projection = TreeReadProjection(
            present=True,
            oid=expected.oid,
            entries=expected.entries,
            entries_hash=expected.entries_hash,
        )
    elif key == "git_commit.create":
        projection = CommitReadProjection(
            present=True,
            oid=PROPOSAL_COMMIT,
            tree_oid=retained.manifest.proposal_tree_oid,
            parents=(BASE_COMMIT,),
            message_sha256="sha256:" + "d" * 64,
        )
    elif key == "git_ref.create":
        projection = RefReadProjection(
            present=True, full_ref=HEAD_REF, target_oid=PROPOSAL_COMMIT
        )
    else:
        projection = PullRequestReadProjection(
            matches=(
                PullRequestMatch(
                    repository_id=101,
                    number=7,
                    head_ref=HEAD_REF,
                    head_oid=PROPOSAL_COMMIT,
                    base_ref="refs/heads/main",
                    base_oid=BASE_COMMIT,
                    title_sha256="sha256:" + "e" * 64,
                    body_sha256="sha256:" + "f" * 64,
                ),
            )
        )
    read_key = {
        "git_blob.create": "git_blob.get",
        "git_tree.create": "git_tree.get",
        "git_commit.create": "commit.get",
        "git_ref.create": "ref.get",
        "pull_request.create": "pull_requests.matching.list",
    }[key]
    target = fixture_read_target(
        manifest=retained.manifest,
        read_operation_key=read_key,
        expected=expected,
    )
    return FixtureReadTranscript(
        request_target=target,
        request_hash=fixture_read_request_hash(
            method="GET",
            target=target,
            expected_identity_digest=retained.ambiguous_admission.expected_identity,
        ),
        accepted_status=200,
        projection=projection,
    )


def assemble(root: Path, key: str, read_evidence="accepted"):
    retained, records, evidence, closure, foundation = retained_fixture(root, key)
    supplied = (
        accepted(retained, closure) if read_evidence == "accepted" else read_evidence
    )
    bundle = assemble_fixture_reconciliation(
        retained=retained,
        record_store_directory=records,
        original_evidence_directory=evidence,
        reconciliation_id="reconcile-1",
        authorized_principal="Arthur",
        issued_at=NOW,
        expires_at=EXPIRY,
        created_at=NOW,
        purpose="Classify one ambiguous mutation.",
        foundation_evidence=foundation,
        read_evidence=supplied,
    )
    return bundle, retained, records, evidence


@pytest.mark.parametrize("value", [1.0, float("nan"), float("inf"), ("tuple",)])
def test_hash_rejects_non_strict_json(value):
    with pytest.raises(ValueError, match="strict JSON rejects"):
        _hash_json({"value": value})


@pytest.mark.parametrize(
    "key,read_key",
    (
        ("git_blob.create", "git_blob.get"),
        ("git_tree.create", "git_tree.get"),
        ("git_commit.create", "commit.get"),
        ("git_ref.create", "ref.get"),
        ("pull_request.create", "pull_requests.matching.list"),
    ),
)
def test_directory_reopened_operation_specific_reconciliation(tmp_path, key, read_key):
    bundle, _, _, _ = assemble(tmp_path, key)
    assert bundle.state == "read_result_present"
    assert bundle.intent.read_operation_key == read_key
    assert bundle.intent.method == "GET"
    assert bundle.intent.request_target == bundle.read_admission.request_target
    assert bundle.intent.request_hash == bundle.read_admission.request_hash
    assert bundle.receipt.classification == "FIXTURE_MATCHED_PRESENT"
    assert bundle.receipt.schema_version.endswith("/0.3.0")
    assert bundle.receipt.profile == "github-publication-fixture-reconciliation-receipt"


def test_reconciliation_uses_same_canonical_ref_target_encoding(tmp_path):
    retained, _records, _evidence, closure, _foundation = retained_fixture(
        tmp_path, "pull_request.create"
    )
    expected = derive_expected_identity(
        manifest=retained.manifest,
        plan=retained.plan,
        admission=retained.ambiguous_admission,
        base_tree_closure=closure,
    ).model_copy(
        update={
            "head_ref": "refs/heads/conclave/caf\u00e9%ready",
            "base_ref": "refs/heads/release#1&ready=yes%",
        }
    )
    target = fixture_read_target(
        manifest=retained.manifest,
        read_operation_key="pull_requests.matching.list",
        expected=expected,
    )
    assert (
        target == "/repos/komistry-labs/conclave/pulls?state=all&head="
        "komistry-labs:conclave%2Fcaf%C3%A9%25ready"
        "&base=release%231%26ready%3Dyes%25&per_page=2&page=1"
    )


def test_complete_tree_includes_base_survivor_and_recomputed_directory(tmp_path):
    bundle, _, _, _ = assemble(tmp_path, "git_tree.create")
    expected = bundle.authorization.expected_identity
    assert tuple(entry.path for entry in expected.entries) == (
        "README.md",
        "docs",
        "docs/proposal.md",
    )


def test_no_response_has_admission_only(tmp_path):
    bundle, _, _, _ = assemble(tmp_path, "git_ref.create", None)
    assert bundle.state == "read_admitted_without_result"
    assert bundle.observation is bundle.read_result is bundle.receipt is None
    workspace = Workspace.create(tmp_path / "external", principal="Arthur")
    paths = persist_fixture_reconciliation(workspace, bundle)
    expected = workspace.github_publication_fixture_reconciliations_dir / "reconcile-1"
    assert len(paths) == 5
    assert all(path.parent == expected for path in paths)


def test_absence_requires_accepted_status(tmp_path):
    retained, records, evidence, closure, foundation = retained_fixture(
        tmp_path, "git_ref.create"
    )
    absent = RefReadProjection(present=False)
    expected = derive_expected_identity(
        manifest=retained.manifest,
        plan=retained.plan,
        admission=retained.ambiguous_admission,
        base_tree_closure=closure,
    )
    target = fixture_read_target(
        manifest=retained.manifest,
        read_operation_key="ref.get",
        expected=expected,
    )
    request_hash = fixture_read_request_hash(
        method="GET",
        target=target,
        expected_identity_digest=retained.ambiguous_admission.expected_identity,
    )
    with pytest.raises(ValidationError, match="PUBLICATION_RECONCILIATION_REQUIRED"):
        FixtureReadTranscript(
            request_target=target,
            request_hash=request_hash,
            accepted_status=200,
            projection=absent,
        )
    bundle = assemble_fixture_reconciliation(
        retained=retained,
        record_store_directory=records,
        original_evidence_directory=evidence,
        reconciliation_id="absent",
        authorized_principal="Arthur",
        issued_at=NOW,
        expires_at=EXPIRY,
        created_at=NOW,
        purpose="Confirm absence.",
        foundation_evidence=foundation,
        read_evidence=FixtureReadTranscript(
            request_target=target,
            request_hash=request_hash,
            accepted_status=404,
            projection=absent,
        ),
    )
    assert bundle.receipt.classification == "FIXTURE_MATCHED_ABSENT"


def test_fixture_transcript_cannot_claim_authentication_or_change_target(tmp_path):
    retained, records, evidence, closure, foundation = retained_fixture(
        tmp_path, "git_ref.create"
    )
    transcript = accepted(retained, closure)
    with pytest.raises(ValidationError):
        FixtureReadTranscript.model_validate(
            {**transcript.model_dump(mode="python"), "authenticated": True}
        )
    forged_target = transcript.model_copy(
        update={"request_target": transcript.request_target + "/wrong"}
    )
    with pytest.raises(ValueError, match="PUBLICATION_RECONCILIATION_REQUIRED"):
        assemble_fixture_reconciliation(
            retained=retained,
            record_store_directory=records,
            original_evidence_directory=evidence,
            reconciliation_id="wrong-target",
            authorized_principal="Arthur",
            issued_at=NOW,
            expires_at=EXPIRY,
            created_at=NOW,
            purpose="Reject a substituted target.",
            foundation_evidence=foundation,
            read_evidence=forged_target,
        )


def test_reconciliation_rejects_transcript_subclass_without_invoking_it(tmp_path):
    retained, records, evidence, closure, foundation = retained_fixture(
        tmp_path, "git_blob.create"
    )
    original = accepted(retained, closure)
    invocations = 0

    class ExecutableTranscript(FixtureReadTranscript):
        def __getattribute__(self, name):
            nonlocal invocations
            if name in {
                "method",
                "request_target",
                "request_hash",
                "accepted_status",
                "projection",
            }:
                invocations += 1
            return super().__getattribute__(name)

    hostile = ExecutableTranscript.model_validate(original.model_dump(mode="python"))
    invocations = 0
    with pytest.raises(ValueError, match="PUBLICATION_RECONCILIATION_REQUIRED"):
        assemble_fixture_reconciliation(
            retained=retained,
            record_store_directory=records,
            original_evidence_directory=evidence,
            reconciliation_id="hostile-transcript",
            authorized_principal="Arthur",
            issued_at=NOW,
            expires_at=EXPIRY,
            created_at=NOW,
            purpose="Reject executable transcript access.",
            foundation_evidence=foundation,
            read_evidence=hostile,
        )
    assert invocations == 0


def test_reconciliation_rejects_projection_subclass_without_invoking_it(tmp_path):
    retained, records, evidence, closure, foundation = retained_fixture(
        tmp_path, "git_blob.create"
    )
    original = accepted(retained, closure)
    invocations = 0

    class ExecutableProjection(BlobReadProjection):
        def __getattribute__(self, name):
            nonlocal invocations
            if name in {"kind", "present", "oid", "content_sha256", "byte_count"}:
                invocations += 1
            return super().__getattribute__(name)

    hostile_projection = ExecutableProjection.model_validate(
        original.projection.model_dump(mode="python")
    )
    hostile = original.model_copy(update={"projection": hostile_projection})
    invocations = 0
    with pytest.raises(ValueError, match="PUBLICATION_RECONCILIATION_REQUIRED"):
        assemble_fixture_reconciliation(
            retained=retained,
            record_store_directory=records,
            original_evidence_directory=evidence,
            reconciliation_id="hostile-projection",
            authorized_principal="Arthur",
            issued_at=NOW,
            expires_at=EXPIRY,
            created_at=NOW,
            purpose="Reject executable projection access.",
            foundation_evidence=foundation,
            read_evidence=hostile,
        )
    assert invocations == 0


def test_reconciliation_resnapshots_bypass_mutated_transcript(tmp_path):
    retained, records, evidence, closure, foundation = retained_fixture(
        tmp_path, "git_blob.create"
    )
    transcript = accepted(retained, closure)
    object.__setattr__(transcript, "accepted_status", True)

    with pytest.raises(ValueError, match="PUBLICATION_RECONCILIATION_REQUIRED"):
        assemble_fixture_reconciliation(
            retained=retained,
            record_store_directory=records,
            original_evidence_directory=evidence,
            reconciliation_id="mutated-transcript",
            authorized_principal="Arthur",
            issued_at=NOW,
            expires_at=EXPIRY,
            created_at=NOW,
            purpose="Reject a bypass-mutated transcript.",
            foundation_evidence=foundation,
            read_evidence=transcript,
        )


def test_foreign_signed_foundation_chain_is_rejected(tmp_path):
    retained, records, evidence, closure, _ = retained_fixture(
        tmp_path / "subject", "git_blob.create"
    )
    _, _, _, _, foreign_foundation = retained_fixture(
        tmp_path / "foreign", "git_blob.create"
    )
    with pytest.raises(ValueError, match="PUBLICATION_RECONCILIATION_REQUIRED"):
        assemble_fixture_reconciliation(
            retained=retained,
            record_store_directory=records,
            original_evidence_directory=evidence,
            reconciliation_id="foreign-foundation",
            authorized_principal="Arthur",
            issued_at=NOW,
            expires_at=EXPIRY,
            created_at=NOW,
            purpose="Reject a different signed repository chain.",
            foundation_evidence=foreign_foundation,
            read_evidence=accepted(retained, closure),
        )


def test_missing_retained_foundation_observation_is_rejected(tmp_path):
    retained, records, evidence, closure, foundation = retained_fixture(
        tmp_path, "git_blob.create"
    )
    (records / foundation.observation_reference.reference).unlink()
    with pytest.raises(ValueError, match="PUBLICATION_RECONCILIATION_REQUIRED"):
        assemble_fixture_reconciliation(
            retained=retained,
            record_store_directory=records,
            original_evidence_directory=evidence,
            reconciliation_id="missing-foundation-observation",
            authorized_principal="Arthur",
            issued_at=NOW,
            expires_at=EXPIRY,
            created_at=NOW,
            purpose="Reject an unretained foundation observation.",
            foundation_evidence=foundation,
            read_evidence=accepted(retained, closure),
        )


def test_fixture_receipt_never_uses_live_fact_classifications(tmp_path):
    bundle, _, _, _ = assemble(tmp_path, "pull_request.create")
    assert bundle.receipt.source_trust == "untrusted_fixture_transcript"
    assert bundle.receipt.classification.startswith("FIXTURE_")
    serialized = bundle.receipt.model_dump_json()
    assert "CONFIRMED_CREATED" not in serialized
    assert "CONFIRMED_ABSENT" not in serialized


def test_original_provider_substitution_is_rejected(tmp_path):
    retained, records, evidence, _, _ = retained_fixture(tmp_path, "git_ref.create")
    (records / retained.provider_key.reference).write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="PUBLICATION_INPUT_MISMATCH"):
        validate_retained_publication_directories(
            record_store_directory=records,
            original_evidence_directory=evidence,
            retained=retained,
        )


def test_completed_chain_persists_eight_records(tmp_path):
    bundle, _, _, _ = assemble(tmp_path / "source", "git_blob.create")
    workspace = Workspace.create(tmp_path / "external", principal="Arthur")
    paths = persist_fixture_reconciliation(workspace, bundle)
    expected = workspace.github_publication_fixture_reconciliations_dir / "reconcile-1"
    assert len(paths) == 8
    assert all(path.parent == expected for path in paths)


@pytest.mark.parametrize(
    "field_name",
    (
        "authorization",
        "intent",
        "claim",
        "lease_evidence",
        "read_admission",
        "observation",
        "read_result",
        "receipt",
    ),
)
def test_reconciliation_persistence_rejects_each_bypass_mutated_record_without_writes(
    tmp_path, field_name
):
    bundle, _, _, _ = assemble(tmp_path / "source", "git_blob.create")
    record = object.__getattribute__(bundle, field_name)
    assert record is not None
    object.__setattr__(record, "created_at", "2026-09-10T00:00:59Z")
    workspace = Workspace.create(tmp_path / "external", principal="Arthur")

    with pytest.raises(ValueError, match="PUBLICATION_INPUT_MISMATCH"):
        persist_fixture_reconciliation(workspace, bundle)

    destination = workspace.github_publication_fixture_reconciliations_dir
    assert not tuple(destination.rglob("*.json"))


def test_reconciliation_persistence_rejects_bundle_subclass_without_writes(tmp_path):
    bundle, _, _, _ = assemble(tmp_path / "source", "git_blob.create")

    class ReconciliationBundleSubclass(ReconciliationBundle):
        pass

    hostile = ReconciliationBundleSubclass.model_validate(
        bundle.model_dump(mode="json")
    )
    workspace = Workspace.create(tmp_path / "external", principal="Arthur")

    with pytest.raises(ValueError, match="PUBLICATION_INPUT_MISMATCH"):
        persist_fixture_reconciliation(workspace, hostile)

    assert not tuple(
        workspace.github_publication_fixture_reconciliations_dir.rglob("*.json")
    )


@pytest.mark.parametrize(
    "field_name",
    (
        "authorization",
        "intent",
        "claim",
        "lease_evidence",
        "read_admission",
        "observation",
        "read_result",
        "receipt",
    ),
)
def test_reconciliation_persistence_rejects_nested_record_subclasses_without_writes(
    tmp_path, field_name
):
    bundle, _, _, _ = assemble(tmp_path / "source", "git_blob.create")
    record = object.__getattribute__(bundle, field_name)
    assert record is not None
    record_type = type(record)
    hostile_type = type(f"Hostile{record_type.__name__}", (record_type,), {})
    hostile_record = hostile_type.model_validate(record.model_dump(mode="json"))
    hostile_bundle = bundle.model_copy(update={field_name: hostile_record})
    workspace = Workspace.create(tmp_path / "external", principal="Arthur")

    with pytest.raises(ValueError, match="PUBLICATION_INPUT_MISMATCH"):
        persist_fixture_reconciliation(workspace, hostile_bundle)

    assert not tuple(
        workspace.github_publication_fixture_reconciliations_dir.rglob("*.json")
    )


def test_reconciliation_persistence_rejects_deep_projection_subclass_without_writes(
    tmp_path,
):
    bundle, _, _, _ = assemble(tmp_path / "source", "git_blob.create")
    observation = bundle.observation
    assert observation is not None
    projection = observation.projection

    class HostileBlobProjection(BlobReadProjection):
        pass

    hostile = HostileBlobProjection.model_validate(projection.model_dump(mode="json"))
    object.__setattr__(observation, "projection", hostile)
    workspace = Workspace.create(tmp_path / "external", principal="Arthur")

    with pytest.raises(ValueError, match="PUBLICATION_INPUT_MISMATCH"):
        persist_fixture_reconciliation(workspace, bundle)

    assert not tuple(
        workspace.github_publication_fixture_reconciliations_dir.rglob("*.json")
    )


def test_reconciliation_persistence_rejects_scalar_subclass_without_writes(tmp_path):
    bundle, _, _, _ = assemble(tmp_path / "source", "git_blob.create")
    receipt = bundle.receipt
    assert receipt is not None

    class HostileString(str):
        pass

    object.__setattr__(receipt, "classification", HostileString(receipt.classification))
    workspace = Workspace.create(tmp_path / "external", principal="Arthur")

    with pytest.raises(ValueError, match="PUBLICATION_INPUT_MISMATCH"):
        persist_fixture_reconciliation(workspace, bundle)

    assert not tuple(
        workspace.github_publication_fixture_reconciliations_dir.rglob("*.json")
    )


def test_reconciliation_persistence_does_not_invoke_bundle_method_shadow(tmp_path):
    bundle, _, _, _ = assemble(tmp_path / "source", "git_blob.create")
    invoked = False

    def hostile_serializer():
        nonlocal invoked
        invoked = True
        return bundle.model_dump_json()

    object.__setattr__(bundle, "model_dump_json", hostile_serializer)
    workspace = Workspace.create(tmp_path / "external", principal="Arthur")

    with pytest.raises(ValueError, match="PUBLICATION_INPUT_MISMATCH"):
        persist_fixture_reconciliation(workspace, bundle)

    assert not invoked
    assert not tuple(
        workspace.github_publication_fixture_reconciliations_dir.rglob("*.json")
    )


def test_reconciliation_persistence_does_not_invoke_nested_method_shadow(tmp_path):
    bundle, _, _, _ = assemble(tmp_path / "source", "git_blob.create")
    receipt = bundle.receipt
    assert receipt is not None
    invoked = False

    def hostile_serializer(*_args, **_kwargs):
        nonlocal invoked
        invoked = True
        return {}

    object.__setattr__(receipt, "model_dump", hostile_serializer)
    workspace = Workspace.create(tmp_path / "external", principal="Arthur")

    with pytest.raises(ValueError, match="PUBLICATION_INPUT_MISMATCH"):
        persist_fixture_reconciliation(workspace, bundle)

    assert not invoked
    assert not tuple(
        workspace.github_publication_fixture_reconciliations_dir.rglob("*.json")
    )


def test_reconciliation_persistence_does_not_invoke_pydantic_serializer_shadow(
    tmp_path,
):
    bundle, _, _, _ = assemble(tmp_path / "source", "git_blob.create")
    invoked = False

    class HostileSerializer:
        def to_python(self, *_args, **_kwargs):
            nonlocal invoked
            invoked = True
            return {}

        def to_json(self, *_args, **_kwargs):
            nonlocal invoked
            invoked = True
            return b"{}"

    object.__setattr__(bundle, "__pydantic_serializer__", HostileSerializer())
    workspace = Workspace.create(tmp_path / "external", principal="Arthur")

    with pytest.raises(ValueError, match="PUBLICATION_INPUT_MISMATCH"):
        persist_fixture_reconciliation(workspace, bundle)

    assert not invoked
    assert not tuple(
        workspace.github_publication_fixture_reconciliations_dir.rglob("*.json")
    )


def test_reconciliation_persistence_does_not_inspect_unrecognized_object(tmp_path):
    bundle, _, _, _ = assemble(tmp_path / "source", "git_blob.create")
    receipt = bundle.receipt
    assert receipt is not None
    invoked = False

    class HostileValue:
        def __getattribute__(self, name):
            nonlocal invoked
            invoked = True
            raise AssertionError(f"hostile attribute accessed: {name}")

    object.__setattr__(receipt, "classification", HostileValue())
    workspace = Workspace.create(tmp_path / "external", principal="Arthur")

    with pytest.raises(ValueError, match="PUBLICATION_INPUT_MISMATCH"):
        persist_fixture_reconciliation(workspace, bundle)

    assert not invoked
    assert not tuple(
        workspace.github_publication_fixture_reconciliations_dir.rglob("*.json")
    )


def test_reconciliation_persistence_rejects_repository_contained_workspace(tmp_path):
    bundle, _, _, _ = assemble(tmp_path / "source", "git_blob.create")
    repository = tmp_path / "governed-repository"
    (repository / ".git").mkdir(parents=True)
    workspace = Workspace.create(repository / "operations", principal="Arthur")

    with pytest.raises(ValueError, match="PUBLICATION_INPUT_MISMATCH"):
        persist_fixture_reconciliation(workspace, bundle)

    assert not any(workspace.github_publication_fixture_reconciliations_dir.iterdir())


@pytest.mark.parametrize("marker_kind", ["directory", "file"])
def test_reconciliation_persistence_rejects_workspace_root_git_marker(
    tmp_path, marker_kind
):
    bundle, _, _, _ = assemble(tmp_path / "source", "git_blob.create")
    workspace = Workspace.create(tmp_path / "external", principal="Arthur")
    marker = workspace.root / ".git"
    if marker_kind == "directory":
        marker.mkdir()
    else:
        marker.write_text("gitdir: elsewhere\n", encoding="utf-8")

    with pytest.raises(ValueError, match="PUBLICATION_INPUT_MISMATCH"):
        persist_fixture_reconciliation(workspace, bundle)

    assert not any(workspace.github_publication_fixture_reconciliations_dir.iterdir())


def test_reconciliation_persistence_rejects_linked_destination(tmp_path, monkeypatch):
    bundle, _, _, _ = assemble(tmp_path / "source", "git_blob.create")
    workspace = Workspace.create(tmp_path / "external", principal="Arthur")
    destination = workspace.github_publication_fixture_reconciliations_dir
    outside = tmp_path / "outside"
    outside.mkdir()
    destination.rmdir()
    try:
        destination.symlink_to(outside, target_is_directory=True)
    except OSError:
        import conclave.github_publication_reconciliation as reconciliation_module

        destination.mkdir()
        original = reconciliation_module._is_link_or_reparse
        monkeypatch.setattr(
            reconciliation_module,
            "_is_link_or_reparse",
            lambda path: True if path == destination else original(path),
        )

    with pytest.raises(ValueError, match="PUBLICATION_INPUT_MISMATCH"):
        persist_fixture_reconciliation(workspace, bundle)

    assert not any(outside.iterdir())


@pytest.mark.parametrize("unsafe", ["../escape", "a/b", ".", "..", "trailing."])
def test_reconciliation_id_is_filename_safe(tmp_path, unsafe):
    retained, records, evidence, closure, foundation = retained_fixture(
        tmp_path, "git_blob.create"
    )
    with pytest.raises(ValidationError):
        assemble_fixture_reconciliation(
            retained=retained,
            record_store_directory=records,
            original_evidence_directory=evidence,
            reconciliation_id=unsafe,
            authorized_principal="Arthur",
            issued_at=NOW,
            expires_at=EXPIRY,
            created_at=NOW,
            purpose="Reject an unsafe reconciliation identifier.",
            foundation_evidence=foundation,
            read_evidence=accepted(retained, closure),
        )


def test_predecessor_substitution_is_rejected(tmp_path):
    bundle, _, _, _ = assemble(tmp_path, "git_ref.create")
    data = bundle.receipt.model_dump(mode="python", exclude={"content_hash"})
    data["claim"] = rr("wrong-claim")
    tampered = seal_record(type(bundle.receipt), data)
    with pytest.raises(ValidationError, match="predecessor chain mismatch"):
        ReconciliationBundle(
            state="read_result_present",
            authorization=bundle.authorization,
            intent=bundle.intent,
            claim=bundle.claim,
            lease_evidence=bundle.lease_evidence,
            read_admission=bundle.read_admission,
            observation=bundle.observation,
            read_result=bundle.read_result,
            receipt=tampered,
        )
