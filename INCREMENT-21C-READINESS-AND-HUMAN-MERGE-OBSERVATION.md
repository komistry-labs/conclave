# CONCLAVE Stage 21C — Readiness and Human-Merge Observation

## Status

Replacement protocol candidate · local draft · Council review required · not
frozen · not implemented

This candidate is drafted under frozen Increment 21 Erratum 0001. It defines a
smaller Stage 21C that evaluates exact-head readiness, validates separately
authored human-only authorization evidence, stops for the human action, and
later observes and reconciles factual GitHub state. CONCLAVE never performs,
requests, queues, retries, or causes a merge.

This document grants no implementation, credential, network, repository,
commit, push, pull-request, merge, deployment, production, KOS, IDM, signing,
identity, or membership authority.

## 1. Governing baseline

This candidate is bound to:

- protected `main` commit:
  `24f615fa6b6b2d25a2b03161c719f226f4f20f84`;
- protected `main` tree:
  `1a1eec05cea9b740ef84f8981195d662d7c1c72b`;
- frozen Increment 21 master protocol SHA-256:
  `89a05211a4323db2e79d2854952b24ce033c71f357430c7ac839457ff0878d75`;
- frozen Increment 21 master protocol Git blob:
  `83d8fb2cabb9d343b6a8d089d920d25dcd8c5728`;
- frozen Stage 21A protocol SHA-256:
  `4493237e46c72b3b3eed8150e4994580568831e55ffa24046b5058eb4a7b0b5f`;
- frozen Stage 21A protocol Git blob:
  `6602c2d2f4708774ec054db02603638661433082`;
- frozen Stage 21B protocol SHA-256:
  `b90c97284afec9ac7cef44fd9186b38f9e2a86630e283c593dc2ed95e88384c4`;
- frozen Stage 21B Erratum 0001 SHA-256:
  `f79aae70e15dd90bda10948ee172f77acac3557a87ff2d2f1c35a65a1ed0658e`;
- frozen Increment 21 Erratum 0001 SHA-256:
  `a0fa63884be7970e9c0463014b1091f118bc32d0702fc7ebb5402a8410a5c742`;
- frozen Increment 21 Erratum 0001 Git blob:
  `acd0556124be766ec600b63519408952297a582e`; and
- Increment 21 Erratum 0001 freeze-record SHA-256:
  `d336f9fc98d424bda3907f864060967d66a8c1c417ee09892a557a63e44051b3`.

The rejected predecessor
`INCREMENT-21C-EXACT-HEAD-REVIEW-AND-HUMAN-AUTHORIZED-MERGE.md` and Council
Reviews 0001 through 0007 remain immutable historical evidence. They are not
operative inputs and none of their mutation machinery is incorporated here.

## 2. Objective and non-objectives

Stage 21C may:

1. obtain separately authorized, bounded, read-only GitHub observations;
2. reduce those observations and independent no-bypass evidence to exactly one
   of `ready`, `blocked`, or `indeterminate` for one exact repository, pull
   request, base commit, and head commit;
3. validate and preserve separately authored, expiring evidence that authorizes
   only a named human to attempt one normal protected merge;
4. produce a non-operative handoff to that human and stop all GitHub activity;
5. after a separate human request and separately authorized read cycle, observe
   GitHub state; and
6. reconcile the observation against the earlier readiness and human
   authorization without approval inference or corrective action.

Stage 21C must not:

- obtain or use a human GitHub credential, browser session, cookie, token,
  private key, SSH key, passkey, or device code;
- use contents-write, pull-requests-write, administration-write, merge,
  bypass, branch-update, review, conversation-resolution, or settings-change
  permission;
- call a REST write method, the GitHub merge endpoint, a GraphQL mutation,
  merge queue, auto-merge, rebase, squash, branch update, review submission,
  conversation-resolution, or repository-setting endpoint;
- construct or expose a generic caller-selected GitHub method, path, origin,
  operation name, query, or body;
- count, enforce, or attest external human browser or CLI attempts;
- infer that a green check, approval, mergeability field, human authorization,
  or completed merge is a KOS decision, production approval, identity fact, or
  membership fact; or
- mutate KOS, IDM, CONCLAVE protected `main`, a client repository, or any
  production target.

## 3. Actors and required separation

The following identities are explicit and non-interchangeable:

1. **read-only observation installation** — the GitHub App and installation
   numeric identities bound by the frozen Stage 21A repository profile;
2. **configured human merge principal** — one external human principal bound
   to one GitHub numeric user ID;
3. **independent review principals** — GitHub numeric user IDs whose qualifying
   reviews may satisfy repository policy; and
4. **independent control attestor** — the principal and verification key that
   issues the no-bypass attestation.

The configured human merge principal must be distinct from every independent
review principal whose approval is counted and from the independent control
attestor. The observation App and installation must not be represented as the
merge actor. Display names and login strings are descriptive only; security
bindings use numeric or GitHub node identities plus the governed external
principal binding.

If any required identity is absent, ambiguous, duplicated across prohibited
roles, unverifiable, suspended, or changed during a cycle, the result is
`indeterminate`, never `ready`.

## 4. Selected immutable record families

Stage 21C selects only the durable families permitted by Increment 21 Erratum
0001:

- `github-merge-readiness/0.2.0`;
- `github-ruleset-no-bypass-attestation/0.2.0`;
- `github-human-merge-authorization-evidence/0.1.0`;
- `github-human-merge-observation/0.1.0`; and
- `github-human-merge-reconciliation/0.1.0`.

The human handoff is a deterministic presentation of the readiness and
authorization records. It is not a sixth durable family, an operation intent,
or a capability token.

Every selected record is closed-schema, bounded, canonical UTF-8 JSON,
content-hashed, immutable, and stored under its content hash. Unknown members,
duplicate JSON names, non-integer numbers where integers are required,
non-canonical encodings, invalid Unicode, and objects exceeding their frozen
byte ceiling are rejected before semantic processing. Cross-record references
point only to already durable hashes and therefore form an acyclic chain:

`attestation -> readiness -> human authorization -> observation -> reconciliation`.

The attestation may be renewed after the human action. A renewal is a new
immutable object; it does not replace or modify the earlier object.

### 4.1 Inherited common contract and ceilings

All five families inherit the frozen Stage 21A `ClosedModel`/`HashedRecord`
contract, including its exact canonical JSON, timestamps, content-hash,
reference/path, immutable-create, durability, reopen-verification, conflict,
and effect fields. For every Stage 21C family:

- `authority_effect`, `decision_effect`, and `membership_effect` are `none`;
- `production_use_allowed` is `false`;
- all integer IDs are positive and all counts are non-negative integers;
- object IDs are bounded safe UTF-8 strings of at most 128 bytes;
- commit IDs match the repository's frozen object format;
- refs use the frozen Stage 21A full-ref contract;
- record-reference arrays are ordered, unique, and contain at most 128 items;
- reason codes are sorted unique safe uppercase ASCII strings, at most 128
  codes of 64 characters each; and
- nullable fields are allowed only where named below.

The complete canonical byte ceilings are:

| Family | Maximum canonical bytes |
|---|---:|
| `github-merge-readiness/0.2.0` | `1048576` |
| `github-ruleset-no-bypass-attestation/0.2.0` | `524288` |
| `github-human-merge-authorization-evidence/0.1.0` | `131072` |
| `github-human-merge-observation/0.1.0` | `1048576` |
| `github-human-merge-reconciliation/0.1.0` | `262144` |

The inherited discriminator values are exact and serialized in every record:

| Family | `profile` | `schema_version` |
|---|---|---|
| readiness | `github-merge-readiness` | `github-merge-readiness/0.2.0` |
| attestation | `github-ruleset-no-bypass-attestation` | `github-ruleset-no-bypass-attestation/0.2.0` |
| human authorization | `github-human-merge-authorization-evidence` | `github-human-merge-authorization-evidence/0.1.0` |
| observation | `github-human-merge-observation` | `github-human-merge-observation/0.1.0` |
| reconciliation | `github-human-merge-reconciliation` | `github-human-merge-reconciliation/0.1.0` |

Arrays of checks, statuses, reviews, rules, or rulesets contain at most `1000`
items; review threads contain at most `100`; source-evidence references contain
at most `32`. Any exceeded ceiling is an input failure, not truncation.

### 4.2 Required family fields

The following notation is normative: `id` is a positive integer; `count` is a
non-negative integer; `hash` is `sha256:` plus 64 lowercase hexadecimal
characters; `oid` follows the repository object format; `ts` is the inherited
timestamp; `s(N)` is a UTF-8 string of at most N bytes; `ascii(N)` is safe ASCII
of at most N characters; `bool` is exact JSON true or false; `record_ref` is the inherited exact path/hash pair;
`T?` is nullable; `[T,N]` is an ordered array of at most N items. No member is
optional. Every object named below has exactly the listed members.

Common nested objects are:

```text
protocol_hashes = {
  increment_21: hash,
  increment_21_erratum_0001: hash,
  stage_21a: hash,
  stage_21c: hash
}

repository_identity = {
  repository_id: id,
  repository_node_id: s(128),
  account_id: id
}

target = {
  repository: repository_identity,
  pull_request_number: id,
  base_ref: s(255),
  base_commit: oid,
  head_commit: oid
}

required_check = {
  context: s(512),
  app_id: id?,
  source_rule_hashes: [hash,32]
}

selected_check_result = {
  requirement: required_check,
  source: enum(check_run,status),
  result_id: id,
  producer_id: id?,
  observed_at: ts,
  state: enum(success),
  observation: record_ref
}
```

`github-merge-readiness/0.2.0` adds exactly:

```text
protocol_hashes: protocol_hashes
repository_profile: record_ref
api_profile: record_ref
target: target
cycle_id: hash
configured_human_principal_id: ascii(128)
configured_human_id: id
operation_authorizations: [record_ref,13]
observations: [record_ref,13]
no_bypass_attestation: record_ref
required_checks: [required_check,1000]
selected_check_results: [selected_check_result,2000]
qualifying_reviewer_ids: [id,1000]
observation_started_at: ts
observation_completed_at: ts
sealed_at: ts
expires_at: ts
logical_operation_count: count
network_request_count: count
result: enum(ready,blocked,indeterminate)
reason_codes: [ascii(64),128]
merge_authorized: literal(false)
conclave_operation_authorized: literal(false)
```

The authorization and observation arrays use the exact operation order in §6,
contain one reference per operation, and contain no duplicate hash.
For a `ready` record, `required_checks`, `selected_check_results`, and
`qualifying_reviewer_ids` are nonempty. An `indeterminate` prefix record may
contain fewer than thirteen observations but still carries all thirteen
operation-authorization references.

`github-ruleset-no-bypass-attestation/0.2.0` adds exactly:

```text
protocol_hashes: protocol_hashes
purpose: enum(readiness,action_interval)
target: target
repository_profile: record_ref
configured_human_principal_id: ascii(128)
configured_human_id: id
observation_app_id: id
observation_installation_id: id
branch_protection_observation: record_ref
branch_rules_observation: record_ref
ruleset_summary_observation: record_ref
applicable_rulesets: [applicable_ruleset,1000]
effective_policy: effective_policy
conversation_state: conversation_state
actor_capabilities: actor_capabilities
source_evidence_hashes: [hash,32]
collection_protocol_sha256: hash
coverage_started_at: ts
coverage_completed_at: ts
issued_at: ts
expires_at: ts
attestor_id: ascii(128)
attestor_github_user_id: id?
attestor_key_id: ascii(128)
attestor_public_key_sha256: hash
trust_authorization_sha256: hash
result: enum(controls_intact,controls_changed,bypass_present,indeterminate)
reason_codes: [ascii(64),128]
signature: ascii(86)
```

Its exact nested contracts are:

```text
applicable_ruleset = {
  ruleset_id: id,
  ruleset_node_id: s(128),
  source_type: enum(Repository,Organization,Enterprise),
  source_id: id,
  target: enum(branch,push,tag),
  enforcement: enum(active,evaluate,disabled,enabled),
  created_at: ts,
  updated_at: ts,
  conditions_sha256: hash,
  rules_sha256: hash,
  bypass_actors_sha256: hash,
  semantic_rules: [semantic_rule,128]
}

semantic_rule = {
  type: ascii(64),
  parameters_sha256: hash,
  normalized_requirement_sha256: hash,
  requirement_known: bool,
  satisfied: bool,
  evidence_hashes: [hash,32]
}

effective_policy = {
  applicable_ruleset_ids: [id,1000],
  all_active_rules_known: bool,
  strict_required: bool,
  administrator_enforcement_required: bool,
  conversation_resolution_required: bool,
  required_approving_review_count: count,
  code_owner_review_required: bool,
  code_owner_requirement_satisfied: bool,
  code_owner_eligible_reviewer_ids: [id,1000],
  last_push_approval_required: bool,
  last_pusher_id: id?,
  last_push_requirement_satisfied: bool,
  required_checks: [required_check,1000],
  normal_merge_allowed: bool,
  force_push_allowed: bool,
  deletion_allowed: bool,
  all_effective_requirements_satisfied: bool
}

conversation_state = {
  pull_request_node_id: s(128),
  total_thread_count: count,
  unresolved_thread_count: count,
  complete: bool,
  thread_inventory_sha256: hash
}

actor_capabilities = {
  human_has_bypass: bool?,
  app_has_bypass: bool?,
  installation_has_bypass: bool?,
  capability_inventory_complete: bool,
  capability_inventory_sha256: hash
}
```

The recognized `semantic_rule.type` set is exactly the frozen Stage 21A
`rule_type` enum. An unknown type remains representable only as bounded
evidence, but
`requirement_known` and `all_active_rules_known` must be false and the
attestation result must be `indeterminate`. `active` and `enabled` rules create
requirements; `disabled` and `evaluate` rules remain in inventory but do not.
Every normalized effective requirement is source-bound to at least one rule or
legacy-protection hash.

`source_evidence_hashes` contains 1–32 items. `applicable_rulesets` may be empty
only when the signed collection procedure positively establishes that no
repository, organization, or enterprise ruleset applies; legacy branch-
protection evidence remains mandatory.

`github-human-merge-authorization-evidence/0.1.0` adds exactly:

```text
protocol_hashes: protocol_hashes
target: target
cycle_id: hash
readiness: record_ref
independent_review_observation: record_ref
qualifying_reviewer_ids: [id,1000]
method: literal(normal_merge_commit)
configured_human_principal_id: ascii(128)
configured_human_id: id
human_key_id: ascii(128)
human_public_key_sha256: hash
trust_authorization_sha256: hash
maximum_human_attempts: literal(1)
issued_at: ts
expires_at: ts
authorized_actor_class: literal(human_external_to_conclave)
conclave_operation_authorized: literal(false)
signature: ascii(86)
```

`independent_review_observation` must be the exact complete `reviews.list`
Stage 21A observation already referenced by readiness. The nonempty sorted
`qualifying_reviewer_ids` must equal the readiness record exactly. The human
authorization's `cycle_id` must equal the referenced readiness cycle ID.

`github-human-merge-observation/0.1.0` adds exactly:

```text
protocol_hashes: protocol_hashes
target: target
cycle_id: hash
readiness: record_ref
human_authorization: record_ref
operation_authorizations: [record_ref,7]
observations: [record_ref,7]
action_interval_attestation: record_ref
pull_request_projection_version: literal(github-21c-post-action-pr/0.1.0)
observed_state: enum(open,closed_unmerged,merged,unknown)
observed_head_commit: oid
observed_base_ref: s(255)
observed_base_ref_commit: oid
merge_commit: oid?
merge_actor_id: id?
merge_actor_type: enum(User,Bot,Organization,Mannequin)?
merged_at: ts?
merge_commit_parent_oids: [oid,2]
collection_started_at: ts
collection_completed_at: ts
logical_operation_count: count
network_request_count: count
result: enum(merged_observed,still_open,closed_not_merged,state_mismatch,insufficient_evidence)
reason_codes: [ascii(64),128]
```

When `observed_state` is not `merged`, `merge_commit`, `merge_actor_id`,
`merge_actor_type`, and `merged_at` are null and `merge_commit_parent_oids` is
empty. When it is `merged`, all four nullable fields are non-null and the
parent array has exactly two items or the result is `insufficient_evidence`.

`github-human-merge-reconciliation/0.1.0` adds exactly:

```text
protocol_hashes: protocol_hashes
readiness: record_ref
human_authorization: record_ref
observation: record_ref
readiness_attestation: record_ref
action_interval_attestation: record_ref
reconciled_at: ts
result: enum(matching_normal_merge,no_action_observed,mismatched_action,protection_continuity_unproven,indeterminate)
reason_codes: [ascii(64),128]
corrective_action_authorized: literal(false)
```

Array ordering is exact: protocol and source-evidence hashes sort by lowercase
digest; operation authorizations and observations use lifecycle order;
required checks sort by context UTF-8 bytes then null App before numeric App;
selected results use §8.1 order; reviewer and code-owner IDs sort numerically;
rulesets sort by source-type UTF-8 bytes, source ID, then ruleset ID; semantic
rules sort by type UTF-8 bytes then parameters hash; reason codes sort by ASCII
bytes; and merge parents retain Git parent order. Duplicate elements are
invalid in every array.

`last_pusher_id` is null only when last-push approval is not required.
`attestor_github_user_id` is null only when the attestor has no GitHub user
identity; otherwise it must be present and participates in role separation. Each
nullable actor-capability boolean is null only when its inventory is incomplete,
which requires attestation result `indeterminate`. All other null-state rules
are stated in the family definitions above; no implementation-defined null is
permitted.

### 4.3 Signature closure

The control-attestor and configured-human verification keys are supplied only
by an exact Arthur-issued Stage 21C trust authorization outside the runtime
record store. That authorization names its purpose, this protocol hash,
repository numeric identity, principal ID, safe key ID, exactly 32 raw Ed25519
public-key bytes, their `sha256:` fingerprint, validity interval, and revocation
status. Its complete canonical SHA-256 is copied into
`trust_authorization_sha256`.

The trust authorization is a prerequisite governance input, not a Stage 21C
record, operation capability, or credential. Before implementation it must be
preserved by a separate governed Arthur decision whose exact canonical bytes
and SHA-256 are fixed; the build-time trust configuration pins that digest.
Its canonical object has exactly:

```text
purpose: enum(control_attestor,human_authorizer)
stage_21c_protocol_sha256: hash
repository_id: id
principal_id: ascii(128)
key_id: ascii(128)
public_key_base64url: ascii(43)
public_key_sha256: hash
collection_protocol_sha256: hash?
not_before: ts
expires_at: ts
status: enum(active,revoked)
arthur_decision_sha256: hash
```

`collection_protocol_sha256` is non-null only for `control_attestor`. The
43-character value decodes canonically to exactly 32 Ed25519 public-key bytes.
The implementation accepts the object only through a dedicated local trust-
loader fixed at build time; caller-
supplied record fields, environment variables, GitHub responses, network
locations, and generic configuration cannot select or replace it. Exactly one
current authorization must match the record's principal, key ID, fingerprint,
purpose, repository, protocol, and—when the purpose is `control_attestor`—
collection-protocol hash. Missing, expired, revoked, future,
conflicting, or multiple matches fail before signature verification. The
record-carried key fields are comparison values and never trust themselves.

Attestor signatures are canonical unpadded base64url encodings of exactly 64
Ed25519 signature bytes over the ASCII domain
`CONCLAVE-GITHUB-NO-BYPASS-ATTESTATION-V2`, one zero byte, then canonical JSON
bytes with `signature` and `content_hash` absent.

Human-authorization signatures use the ASCII domain
`CONCLAVE-GITHUB-HUMAN-MERGE-AUTHORIZATION-V1`, one zero byte, then canonical
JSON bytes with `signature` and `content_hash` absent. Alternate algorithms,
domains, encodings, padding, key lengths, self-supplied keys, or ambiguous key
selection are rejected before the record is considered current.

## 5. Read-only endpoint closure

### 5.1 Reused Stage 21A operations

The readiness cycle may use only these frozen Stage 21A operations:

- `repository.get`;
- `repository_hash_algorithm.get`;
- `ref.get`;
- `commit.get`;
- `pull_request.get`;
- `check_runs.list`;
- `combined_status.get`;
- `reviews.list`;
- `branch_protection.get`;
- `branch_rules.list`; and
- `repository_rulesets.list`.

The post-action cycle may additionally use `commit.get` for the observed merge
commit. All Stage 21A permission, origin, path construction, lease, endpoint,
pagination, retry, redirect, redaction, response, evidence, and rate-budget
controls remain controlling.

`issue_comments.list` and `review_comments.list` are not selected because they
cannot prove conversation-resolution state.

### 5.2 No Stage 21C transport extension

Stage 21C adds no endpoint, transport, credential, operation-authorization
family, operation-intent family, lease family, attempt family, or GitHub API
observation family. In
particular it adds no GraphQL transport. Conversation completeness, effective
ruleset semantics, code-owner eligibility, last-push identity, and bypass
capability are supplied only by the independently governed signed attestation
in §7 and must be source-bound there.

Every live GitHub read remains one frozen Stage 21A logical operation with its
own `github-operation-authorization/0.1.0`, intent, attempt claim, credential lease,
and observation evidence. Stage 21A's literal `stage: 21A`, `GET` method, null
request body, one-operation use limit, endpoint table, and permission envelope
remain unchanged. The later Stage 21C reducer consumes completed immutable
Stage 21A observations; it does not reinterpret or aggregate their authority.

### 5.3 Mechanical negative closure

Implementation acceptance must enumerate every selected Stage 21A REST
method/path. Static and installed-wheel inspection must prove
the absence of:

- `PUT /repos/{owner}/{repo}/pulls/{pull_number}/merge`;
- every GraphQL query or mutation transport;
- auto-merge or merge-queue operations;
- caller-selected URLs, methods, paths, queries, bodies, or operation names;
- human credential adapters; and
- any Stage 21C mutation coordinator, retry loop, target claim, merge attempt,
  or merge receipt.

## 6. Readiness-cycle authorization and bounds

There is no multi-operation cycle authorization. Before the first read, the
caller supplies exactly thirteen already durable, distinct, current Stage 21A
`github-operation-authorization/0.1.0` records, one for each ordered operation below.
Each retains Stage 21A's `maximum_logical_operations: 1`, endpoint-specific
request ceiling, exact repository/profile/App/installation binding, time,
rate, and evidence-store controls. No authorization can be reused between two
slots, and failure of one slot cannot borrow another slot's authorization.

The non-authorizing `cycle_id` is the domain-separated SHA-256 of
`CONCLAVE-GITHUB-READINESS-CYCLE-V1`, one zero byte, this protocol hash, the
repository-profile hash, canonical target fields, and the thirteen ordered
authorization references. It groups evidence only and grants no operation.

The fixed sequence is:

1. repository identity and object-format observations;
2. initial PR observation;
3. initial base-ref and head-commit observations;
4. checks and combined status;
5. reviews;
6. branch protection, effective branch rules, and repository ruleset summary;
7. final PR observation; and
8. final base-ref observation.

The readiness cycle has exactly `13` logical operations and an aggregate
ceiling of `71` HTTP requests: eight scalar reads at at most two transmissions
each and five paginated reads at at most eleven transmissions each. These are
derived accounting limits, not shared authority. Exceeding any single Stage
21A authorization or either aggregate limit stops the cycle and yields
`indeterminate: REQUEST_BUDGET_EXHAUSTED`.

All observations must complete within the cycle window. The final PR and base
observations must finish no more than `30` seconds before the readiness record
is sealed. Any earlier observation older than `300` seconds at seal is stale.
Clock rollback, unavailable trusted time, expiration during storage, or an
observation spanning an unbounded interval yields `indeterminate`.

No observation begins unless its own immutable authorization and evidence-
store preconditions have passed. A durably recorded incomplete Stage 21A read
stops further reads and may produce an `indeterminate` readiness record that
references the completed prefix. A crash, missing terminal observation, or
storage failure produces no aggregate readiness record. In every case the
cycle is permanently closed and never resumed. Already durable Stage 21A
observations remain immutable prefix or orphan facts and cannot be combined
with a later cycle. A new cycle requires thirteen new authorizations, a new
`cycle_id`, and fresh reads from operation one. Reads already made are factual
side effects; no mutation or compensating operation follows.

## 7. Independent no-bypass attestation

`github-ruleset-no-bypass-attestation/0.2.0` is produced outside CONCLAVE by
the independent control attestor. CONCLAVE verifies but does not author it.
The closed record binds:

- protocol and repository-profile hashes;
- repository numeric and node identities;
- organization or enterprise numeric source identity where applicable;
- PR number, base ref, exact base commit, and exact head commit;
- configured human principal and GitHub numeric user ID;
- observation App and installation numeric identities;
- every applicable repository and organization ruleset identity, version or
  update timestamp, enforcement state, target, complete conditions/rules/
  bypass hashes, normalized semantic rules, and bypass-actor set;
- the effective branch-protection and branch-rules observation hashes;
- the complete normalized effective policy, including required checks with
  App identities, approval count, code-owner and last-push requirements,
  strictness, conversation resolution, administrator enforcement, allowed
  merge method, force-push state, and deletion state;
- complete source-bound review-thread inventory hash, total and unresolved
  counts, PR node identity, and collection interval;
- code-owner-eligible reviewer identities and latest-pusher identity when the
  corresponding active rule requires them;
- source-evidence hashes, the exact independently governed collection-procedure
  hash, and collection interval;
- whether the human actor, App, or installation has any administrator,
  organization-owner, team, role, App, deploy-key, ruleset, branch-protection,
  or other bypass route;
- attestor identity, fixed Ed25519 verification-key identity, issued time,
  expiry, and canonical content hash; and
- for a post-action renewal, the exact covered action interval and any
  protection, ruleset, bypass, or actor-capability changes observed in that
  interval.

The attestation reason-code domain is exactly:

```text
SCHEMA_INVALID, SOURCE_EVIDENCE_INCOMPLETE, COLLECTION_PROTOCOL_MISMATCH,
TRUST_INVALID, SIGNATURE_INVALID, TIME_INVALID, TARGET_MISMATCH,
RULESET_INCOMPLETE, UNKNOWN_RULE, POLICY_INCOMPLETE,
CONVERSATION_INCOMPLETE, ACTOR_CAPABILITY_INCOMPLETE, BYPASS_PRESENT,
PROTECTION_CHANGED, RULESET_CHANGED, CAPABILITY_CHANGED
```

Attestation result precedence is exact: any of the first twelve structural
codes produces `indeterminate` even when another code is present; otherwise
`BYPASS_PRESENT` produces `bypass_present`; otherwise any of the final three
change codes produces `controls_changed`; otherwise the reason list must be
empty and the result is `controls_intact`. No other code or result combination
is valid.

Readiness requires an attestation issued after the bound protection and ruleset
observations, expiring no more than `600` seconds after issue and not before
readiness expiry. Its independent source evidence must be complete for every
applicable repository, organization, and enterprise rule and every review
thread; its hashes are retained even though the external evidence itself is not
a Stage 21C record. `controls_intact` is accepted only if the applicable ruleset,
policy, conversation, and actor-capability inventories are complete and the
named human, App, and installation have no bypass path. A promise not to use an
available bypass is insufficient.

Missing rulesets, unknown rule semantics, incomplete enterprise/organization/
repository scope, incomplete conversation enumeration, unknown actor
capability, unverifiable trust or signature, stale evidence, or mismatch yields
`indeterminate`. A complete positive bypass fact yields `bypass_present` and
blocks readiness. Readiness accepts only `controls_intact`.

The post-action reconciliation requires a renewed attestation from the same
governed attestor that covers the complete interval from readiness seal through
the post-action observations. It must positively establish that protection,
rulesets, enforcement, and bypass capability did not weaken during that
interval. Two matching endpoint snapshots alone do not prove continuity.

## 8. Deterministic readiness reduction

The reducer is pure, total, and order-independent after canonical ordering. It
uses this exact precedence and returns exactly one state:

1. Any structural, schema, identity, completeness, ordering, trust, signature,
   time, rate, storage, unknown-domain, or conflicting-evidence failure returns
   `indeterminate` with all applicable sorted reason codes. No policy
   conclusion is evaluated.
2. Otherwise, any complete positive policy or target failure returns `blocked`
   with all applicable sorted reason codes.
3. Otherwise, and only if every condition below is true, return `ready`.

The readiness reason-code domain is exactly:

```text
SCHEMA_INVALID, REFERENCE_INVALID, IDENTITY_AMBIGUOUS,
EVIDENCE_INCOMPLETE, EVIDENCE_CONFLICT, UNKNOWN_RULE, TIME_INVALID,
RATE_INVALID, STORAGE_INVALID, AUTHORIZATION_INVALID, TRUST_INVALID,
SIGNATURE_INVALID, REQUEST_BUDGET_EXHAUSTED, REVIEW_ORDER_AMBIGUOUS,
CHECK_ORDER_AMBIGUOUS, PR_NOT_OPEN, PR_DRAFT, PR_ALREADY_MERGED,
TARGET_MISMATCH, HEAD_COMMIT_MISMATCH, BASE_COMMIT_MISMATCH,
HEAD_COMMIT_INVALID, CHECK_NOT_SUCCESSFUL, APPROVAL_REQUIREMENT_UNMET,
CODE_OWNER_REQUIREMENT_UNMET, LAST_PUSH_APPROVAL_UNMET,
CONVERSATION_UNRESOLVED, MERGEABILITY_UNMET, NORMAL_MERGE_UNAVAILABLE,
STRICT_UPDATE_UNMET, ADMIN_ENFORCEMENT_UNMET, FORCE_PUSH_ENABLED,
DELETION_ENABLED, BYPASS_PRESENT, POLICY_REQUIREMENT_UNMET,
HEAD_BASE_DRIFT
```

The first fifteen codes, through `CHECK_ORDER_AMBIGUOUS`, are structural and
produce `indeterminate`. The remaining codes are complete positive target or
policy failures and produce `blocked`. `HEAD_BASE_DRIFT` is therefore a
complete factual block, while an absent or contradictory head/base observation
is `EVIDENCE_INCOMPLETE` or `EVIDENCE_CONFLICT`. Implementations may not mint
free-text or unreviewed reason codes.

### 8.1 Required-check reduction

The complete effective required-check set is the sorted unique union of legacy
branch protection and every active attested ruleset. Its key is exact UTF-8
`(context, app_id)`, with null sorting before integers. Contradictory duplicate
keys or a source rule absent from the attestation is structural
`EVIDENCE_CONFLICT` or `EVIDENCE_INCOMPLETE`.

For an App-bound requirement, the only channel is exact-head check runs with
equal `name` and equal non-null `app.id`; null producer identity cannot satisfy
it. For a null-App requirement, the check-run channel contains exact-head runs
with equal `name`, and the legacy-status channel independently contains exact-
head statuses with equal `context`. At least one channel must exist. If both
exist, both must pass; success in one can never mask failure, pending state, or
ambiguity in the other.

Within the check-run channel, candidates are ordered by `completed_at`, then
`started_at`. Within the status channel they are ordered by `updated_at`. A
candidate without its required timestamp is structurally incomplete. If two
non-identical candidates in the same channel share the greatest timestamp,
that channel is ambiguous and readiness is `indeterminate`. Otherwise each
applicable channel's unique latest result is selected independently.

Every selected check run must have `status: completed` and `conclusion:
success`; every selected legacy status must have `state: success`. CONCLAVE
deliberately adopts this stricter success-only rule even where GitHub may treat
`neutral` or `skipped` as passing. `neutral`,
`skipped`, `cancelled`, `timed_out`, `action_required`, `startup_failure`,
`failure`, `error`, `pending`, `queued`, `requested`, `waiting`,
`in_progress`, null, stale, or unknown never satisfies a requirement. Older
results have no authority effect. One selected result is stored for an App-
bound requirement and one or two for a null-App requirement. Each retains its
result ID, producer, timestamp, source, and observation reference in
`selected_check_results`. That array sorts by context UTF-8 bytes, null App
before numeric App, `check_run` before `status`, then result ID.

### 8.2 Review and policy reduction

Reviews are grouped by immutable numeric reviewer ID. Only actor type `User` is
eligible. The PR author, configured merge human, control attestor when it has a
GitHub user identity, Bots, Organizations, Mannequins, null users, and duplicate
role identities are ineligible. Within a group, greatest `submitted_at` wins;
equal greatest timestamps with non-identical review IDs are structurally
ambiguous. A missing timestamp or commit binding is structurally incomplete.

Only the unique latest exact-head `APPROVED` review counts. A latest
`CHANGES_REQUESTED`, `DISMISSED`, `COMMENTED`, `PENDING`, or unknown state does
not count. The effective required count is the maximum of `1`, legacy branch
protection, and every active ruleset, as supplied by the complete attested
effective policy.

When code-owner review is required, at least one counted reviewer must appear
in the attested `code_owner_eligible_reviewer_ids` and
`code_owner_requirement_satisfied` must be true. When last-push approval is
required, `last_pusher_id` must be non-null, at least one counted reviewer must
differ from it, and `last_push_requirement_satisfied` must be true. Missing or
incomplete attestation makes readiness `indeterminate`; a complete false
satisfaction value makes it `blocked`.

The attestation's `all_active_rules_known` and
`all_effective_requirements_satisfied` must both be true. The reducer compares
its required checks, counts, method, strictness, administrator enforcement,
conversation policy, force-push, deletion, code-owner, and last-push fields to
the Stage 21A protection/rule summary hashes. Unknown semantics or disagreement
is `indeterminate`, never a policy pass.

### 8.3 Complete ready predicate

`ready` requires all of the following:

1. repository numeric and node identities match the immutable profile;
2. repository object format is supported and all commit identifiers use it;
3. PR is open, non-draft, in the bound repository, targets the configured base
   ref, and has the exact bound head and base commits;
4. initial and final PR head/base observations match each other;
5. initial and final base refs equal the bound base commit;
6. the exact head commit and its tree are present and internally consistent;
7. the effective required-check set is nonempty and every requirement has the
   unique exact-head successful result defined by §8.1;
8. the effective approval count and every code-owner or last-push requirement
   pass the exact §8.2 reduction;
9. the attested conversation inventory is complete and
   `unresolved_thread_count` is zero;
10. the attestation covers every active applicable rule with known semantics
    and proves all effective requirements satisfied;
11. the attestation's target and source observation hashes exactly match this
    cycle;
12. no identity in a prohibited role separation is counted;
13. no latest eligible review is `CHANGES_REQUESTED`;
14. `mergeable` is true and the closed mergeability classification is `clean`;
15. normal merge commits are enabled and squash, rebase, queue, and auto-merge
    are not selected for this action;
16. branch protection and effective branch rules require the observed checks,
    reviews, conversation resolution, and administrator enforcement;
17. strict up-to-date-branch enforcement is active;
18. force pushes and deletion are disabled;
19. the independent attestation completely binds all applicable rulesets and
    proves no bypass path for the human, App, or installation; and
20. every record, authorization, observation, time, rate, and storage bound is
    valid and current.

The readiness record includes all input hashes, the exact ordered reason codes,
`authority_effect: none`, `merge_authorized: false`,
`conclave_operation_authorized: false`, issue time, and expiry no later than
`300` seconds after seal. Equal canonical inputs must produce equal semantic
output apart from separately defined record-creation metadata.

## 9. Human-only authorization evidence and handoff

`github-human-merge-authorization-evidence/0.1.0` is authored and authenticated
outside CONCLAVE by the configured human principal. It must bind:

- the exact governing protocol hashes;
- repository numeric identity and, through the readiness reference, repository-
  profile hash;
- PR number;
- exact base ref, base commit, and head commit;
- exact `ready` record hash and expiry;
- the exact readiness-bound Stage 21A `reviews.list` observation and qualifying
  reviewer IDs;
- method `normal_merge_commit`;
- named human principal and GitHub numeric user ID;
- `maximum_human_attempts: 1` as a human-governance instruction;
- issue time and expiry no later than the readiness expiry;
- `authorized_actor_class: human_external_to_conclave`;
- `conclave_operation_authorized: false`; and
- the human principal's exact Ed25519 signature under §4.3.

CONCLAVE may validate and store the record only after the referenced readiness
record is durable and still `ready` and the separately supplied trust
authorization matches. Invalid or non-current evidence is rejected before
durable Stage 21C storage and is never presented as usable. Diagnostics retain
only a stable reason code and safe input hash; there is no alternate
authentication-proof path.

The deterministic handoff displays the bound repository, PR, base, head,
method, human identity, expiry, readiness hash, and the instruction to stop if
GitHub displays any drift or unavailable protection. It contains no credential,
URL override, executable command, API body, merge button automation, or claim
that CONCLAVE can observe the attempt count.

After handoff, CONCLAVE closes every credential lease and performs no network
request until a separately authorized post-action cycle. The human uses
GitHub's ordinary protected interface independently. GitHub remains the
enforcement point; CONCLAVE neither clicks nor invokes the merge.

## 10. Post-action observation

A post-action cycle uses six new distinct Stage 21A single-operation
authorizations, plus a seventh `commit.get` authorization only when the PR
projection reports a merge commit. No shared authorization exists. The non-
authorizing `cycle_id` uses domain
`CONCLAVE-GITHUB-POST-ACTION-CYCLE-V1` and hashes this protocol, target,
readiness, human authorization, and the six or seven ordered authorization
references.

The aggregate ceilings are six or seven logical operations and `30` or `32`
HTTP requests respectively. The fixed `600`-second cycle limit and each Stage
21A authorization's smaller limits both apply. A durably recorded incomplete
operation stops further reads and may seal `insufficient_evidence`; a crash,
missing terminal record, or storage failure seals no human observation. The
cycle is never resumed and no observation from it is combined with a later
cycle.

The cycle obtains:

1. repository and PR observations, using the exact additive read-only PR
   projection below;
2. current base-ref observation;
3. `commit.get` for the merge commit when one is reported;
4. current branch-protection, branch-rules, and ruleset-summary observations;
   and
5. the independently produced renewal of
   `github-ruleset-no-bypass-attestation/0.2.0` covering the complete action
   interval.

The normalized `github-21c-post-action-pr/0.1.0` projection contains exactly:

```text
id: id
number: id
state: enum(open,closed)
draft: bool
merged: bool
mergeable: bool?
mergeable_state: enum(clean,dirty,blocked,behind,unstable,draft,has_hooks,unknown)
user: {id:id,type:enum(User,Bot,Organization,Mannequin)}
head: {sha:oid,ref:s(255),repo:{id:id}?}
base: {sha:oid,ref:s(255),repo:{id:id}}
created_at: ts
updated_at: ts
closed_at: ts?
merged_at: ts?
merge_commit_sha: oid?
merged_by: {id:id,type:enum(User,Bot,Organization,Mannequin)}?
```

It reuses `pull_request.get`, its Stage 21A endpoint, permission, request, raw
response ceiling, evidence envelope, and all unchanged field rules. GitHub raw
presentation members not selected by either projection are discarded under
Stage 21A rules; an unknown selected enum or malformed selected value fails
closed. No caller controls the projection version or fields.

For `merged: false`, normalized `merged_at`, `merged_by`, and
`merge_commit_sha` are forced null even if GitHub supplies a temporary test-
merge SHA. For `merged: true`, `state` must be `closed` and all three must be
non-null; otherwise the observation is `insufficient_evidence`. `head.sha`
must equal the authorized head and `base.ref` the authorized base ref. Post-
merge `base.sha` is recorded but is not used as proof of the pre-merge base;
that fact is proved only by the merge commit's ordered parents.

`github-human-merge-observation/0.1.0` records facts only and yields one of:

- `merged_observed`;
- `still_open`;
- `closed_not_merged`;
- `state_mismatch`; or
- `insufficient_evidence`.

Its exact precedence is: invalid or incomplete schema/reference/identity/time/
trust/operation evidence yields `insufficient_evidence`; otherwise an open,
unmerged PR yields `still_open`; otherwise a closed, unmerged PR yields
`closed_not_merged`; otherwise a merged PR whose repository, head, base-ref
name, actor, or
required merge fields contradict the authorization yields `state_mismatch`;
otherwise a merged PR with complete required fields yields `merged_observed`.
No other state combination is admitted.

The observation reason-code domain is exactly:

```text
SCHEMA_INVALID, REFERENCE_INVALID, IDENTITY_AMBIGUOUS,
EVIDENCE_INCOMPLETE, EVIDENCE_CONFLICT, TIME_INVALID, TRUST_INVALID,
AUTHORIZATION_INVALID, REQUEST_BUDGET_EXHAUSTED, PR_STILL_OPEN,
PR_CLOSED_NOT_MERGED, REPOSITORY_MISMATCH, HEAD_MISMATCH,
BASE_REF_MISMATCH, ACTOR_MISMATCH, MERGE_FIELDS_INVALID
```

The first nine codes produce `insufficient_evidence`; `PR_STILL_OPEN` alone
produces `still_open`; `PR_CLOSED_NOT_MERGED` alone produces
`closed_not_merged`; and any of the final five codes produces
`state_mismatch`. An empty reason list is permitted only for
`merged_observed`.

It includes the exact observation and attestation hashes, observed actor,
commits, ordered parents, timestamps, protection fingerprints, collection
interval, and `authority_effect: none`. It never calls a merge successful in a
governance or production sense.

## 11. Reconciliation

`github-human-merge-reconciliation/0.1.0` is a pure comparison over already
durable records. It yields exactly one of:

- `matching_normal_merge`;
- `no_action_observed`;
- `mismatched_action`;
- `protection_continuity_unproven`; or
- `indeterminate`.

The exact precedence is:

1. invalid schema/reference/hash/signature/trust/time, incomplete post-action
   reads, missing required value, unknown enum, ambiguous state, or conflicting
   evidence returns `indeterminate`;
2. otherwise, an open unmerged PR returns `no_action_observed`;
3. otherwise, a closed unmerged PR or any actor/head/base/parent/method/time
   mismatch returns `mismatched_action`;
4. otherwise, absent or incomplete action-spanning control evidence returns
   `protection_continuity_unproven`;
5. otherwise, any complete evidence of protection, ruleset, or capability
   change, or of bypass, returns `mismatched_action`; and
6. only the complete predicate below returns `matching_normal_merge`.

The reconciliation reason-code domain is exactly:

```text
SCHEMA_INVALID, REFERENCE_INVALID, IDENTITY_AMBIGUOUS,
EVIDENCE_INCOMPLETE, EVIDENCE_CONFLICT, TIME_INVALID, TRUST_INVALID,
SIGNATURE_INVALID, BASE_ADVANCED, PR_STILL_OPEN, PR_CLOSED_NOT_MERGED,
ACTOR_MISMATCH, HEAD_MISMATCH, BASE_REF_MISMATCH, MERGE_COMMIT_MISSING,
MERGE_PARENT_MISMATCH, METHOD_MISMATCH, MERGE_TIME_OUTSIDE_AUTHORIZATION,
CONTINUITY_EVIDENCE_MISSING, CONTROLS_CHANGED, BYPASS_PRESENT
```

The first nine codes, through `BASE_ADVANCED`, produce `indeterminate`.
`PR_STILL_OPEN` alone produces `no_action_observed`.
`CONTINUITY_EVIDENCE_MISSING` alone, or with `PR_STILL_OPEN` absent and no
mismatch code, produces `protection_continuity_unproven`. Every remaining
complete mismatch code produces `mismatched_action`. An empty reason list is
permitted only for `matching_normal_merge`. The precedence above resolves any
multi-code combination.

`matching_normal_merge` requires all of the following:

1. readiness was `ready` and unexpired when human authorization was issued;
2. authorization was valid, current, and named the observed numeric actor;
3. PR is observed merged with the authorization-bound head and base-ref name;
4. `merge_commit_sha` is present and the current base ref equals it;
5. `commit.get` proves the merge commit's ordered parents are exactly
   `[authorized_base_commit, authorized_head_commit]`;
6. the observed method is therefore a normal two-parent merge commit, not
   squash, rebase, queue substitution, or a different head/base;
7. `merged_by.type` is `User` and `merged_by.id` equals the authorized human
   numeric ID;
8. the merge timestamp falls within the human authorization interval;
9. the renewed independent attestation covers the complete interval and proves
   no protection weakening or bypass capability; and
10. all record identities, hashes, times, and schemas verify.

If the current base ref has advanced beyond the otherwise matching observed
merge commit, ancestry is not
inferred from this bounded protocol; the result is `indeterminate` and a later
protocol may define a separately bounded ancestry proof. If the actor, head,
base-ref name, merge parents, method, or interval differs, the result is `mismatched_action`.
If before-and-after controls match but action-spanning continuity evidence is
absent, the result is `protection_continuity_unproven`.

A still-open PR is only `no_action_observed`. Stage 21C defines no durable
human-declared non-action or rejected-attempt evidence and never infers or
counts an external attempt.

Every nonmatching or unknown result stops. CONCLAVE performs no retry, merge,
revert, branch deletion, PR closure, review change, conversation resolution,
settings change, or other correction.

## 12. Concurrency, replay, and drift

Read-only cycles may coexist, but readiness records bind exact observations and
expiry. Equal-content duplicates are harmless. Conflicting current records make
the cycle `indeterminate` until a fresh bounded cycle resolves the facts.

Human authorization binds one readiness hash and cannot be replayed for a
different repository, PR, base, head, actor, method, or time window. It is not
a bearer credential and no CONCLAVE runtime interface accepts it as an
operation authorization.

Any head, base, review, check, conversation, protection, ruleset, actor,
attestation, or time drift invalidates readiness. CONCLAVE cannot make the
human action atomic with its observations and makes no such claim. The human
must recheck GitHub immediately before acting; post-action reconciliation
reports evidence, not retroactive authorization.

The permitted Stage 21C reference graph is exact:

1. a `readiness` attestation may reference only its Stage 21A repository
   profile and already durable Stage 21A branch-protection, branch-rule, and
   ruleset-summary observations;
2. readiness may reference only its thirteen Stage 21A authorizations and
   observations plus its readiness attestation;
3. human authorization may reference only readiness and the exact Stage 21A
   `reviews.list` observation already referenced by readiness;
4. an `action_interval` attestation may reference only its Stage 21A repository
   profile and already durable post-action Stage 21A branch-protection,
   branch-rule, and ruleset-summary observations;
5. human observation may reference only readiness, human authorization, its
   six or seven Stage 21A authorizations and observations, and its action-
   interval attestation; and
6. reconciliation may reference only readiness, human authorization, human
   observation, and the two attestations.

Every other Stage 21C-to-Stage 21C edge is forbidden. In particular, an
attestation cannot reference readiness, human authorization, human observation,
reconciliation, or another attestation. References are validated before
content hashing, so no direct or indirect cycle is admissible.

## 13. Failure, privacy, and evidence handling

Every parse, validation, identity, rate, time, transport, storage, or evidence
failure is closed and bounded. Exceptions and logs use stable reason codes and
never contain credentials, cookies, authorization headers, private keys,
unbounded response bodies, human authorization signatures, or private
repository content.

Canonical records may retain only the minimum identifiers and hashes required
for audit. Display names, comment bodies, review bodies, review-thread bodies,
diff contents, file contents, and arbitrary query text are excluded. The
independent conversation inventory retains IDs, resolution booleans, counts,
and a content hash, never conversation content.

No redirect is followed. No alternate host is permitted. DNS, TLS, proxy,
lease, response-size, decompression, charset, media-type, and rate failures use
the existing Stage 21A fail-closed controls. Stage 21C adds no transport.

There is no rollback mutation. A human-performed merge is external factual
state and cannot be undone by Stage 21C. Any remediation requires a separate
governed human process and new authority.

## 14. Required implementation and adversarial evidence

Any later implementation must be preceded by a fresh 5/5 exact-draft Council
pass and Arthur freeze of this protocol. Implementation acceptance must then
demonstrate at least:

1. exact governing-hash and immutable-profile validation;
2. closed schemas and canonical content addressing for all five record
   families;
3. total deterministic readiness and reconciliation reducers;
4. correct latest-review reduction by numeric identity and exact head;
5. fail-closed check, status, conversation, protection, ruleset, bypass,
   actor, clock, expiry, and drift handling;
6. thirteen distinct Stage 21A single-read authorizations for readiness and six
   or seven distinct new authorizations for post-action observation, with no
   shared cycle authority or restart reuse;
7. signed source-bound completeness for every effective rule, required check,
   code-owner requirement, last-push requirement, conversation thread, and
   bypass route, with unknown semantics becoming `indeterminate`;
8. deterministic required-check selection across App-bound check runs, legacy
   statuses, reruns, name collisions, equal timestamps, nonterminal results,
   and exact-head substitution;
9. complete no-bypass inventory and independently verified action-spanning
   protection continuity;
10. human authorization incapable of resolving a credential, initiating I/O,
    or entering an operation dispatcher;
11. handoff closes leases and produces no request, command, or clickable merge
    automation;
12. normal merge proof using exact actor, head, base, merge commit, ordered
    parents, timestamp, and unchanged controls;
13. conservative handling of base advancement, missing actor, missing merge
    SHA, alternate merge method, mismatch, still-open PR, non-action, and
    insufficient evidence;
14. storage-failure, restart, duplicate-read, conflicting-record, tamper,
    traversal, symlink/reparse, oversized-input, invalid-Unicode, duplicate-key,
    and hash-substitution tests;
15. fixture and loopback tests proving zero external network and zero mutation;
16. installed-wheel inventory and static scans proving no hidden merge endpoint,
    GraphQL transport, human credential path, or generic transport escape;
17. secret scans over source, tests, logs, exceptions, evidence, wheels, and CI
    artifacts; and
18. Windows/Python 3.12, Ubuntu/Python 3.12 and 3.13, and macOS/Python 3.12
    passing without required security skip or xfail.

Tests must include adversarial combinations rather than only isolated field
mutations. At minimum, they combine stale-but-valid signatures, exact-head
substitution, duplicate reviewer states, ruleset omission plus apparent branch
protection, unresolved outdated threads, actor/bypass substitution, protection
change and restoration between snapshots, merge-parent reversal, base advance,
storage failure, and conflicting immutable evidence.

## 15. Implementation sequence

If separately authorized after freeze, the bounded implementation order is:

1. record schemas, canonicalization, size limits, trust loader, and reason-code
   domains;
2. independent attestation and trust-authorization verifier;
3. readiness Stage 21A observation assembler and reducer;
4. human-authorization validator and non-operative handoff;
5. exact additive post-action PR projection;
6. post-action Stage 21A observation assembler;
7. reconciliation reducer;
8. adversarial, fixture, loopback, installed-wheel, and secret tests;
9. cross-platform acceptance evidence; and
10. independent implementation Council review.

No step may add a mutation path. Discovery of a required write operation stops
implementation and requires a new governance decision; it cannot be fitted into
this protocol as remediation.

## 16. Council review questions

Each reviewer must independently bind the exact candidate SHA-256 and Git blob
and return `PASS_EXACT_DRAFT` or `FAIL_EXACT_DRAFT`:

1. **Governance:** Does the candidate implement the frozen human-merge split
   without reintroducing CONCLAVE merge authority or overstating human-attempt
   control?
2. **GitHub correctness:** Are exact head/base, latest reviews, required checks,
   conversations, protection, rulesets, actor, normal-merge parents, and drift
   evaluated conservatively and from sufficient bounded evidence?
3. **Security:** Are permissions, credentials, endpoints, the absence of a
   GraphQL transport,
   redirects, retries, bypass paths, rate budgets, storage, and generic
   transport escapes closed?
4. **Evidence:** Are the five permitted record families immutable, acyclic,
   total, distinguishable, and sufficient for readiness, human authorization,
   observation, and reconciliation?
5. **Operability:** Can the design be implemented and verified on the required
   platform matrix without importing the rejected mutation state machine or
   relying on claims CONCLAVE cannot observe?

Any byte change after review invalidates every verdict and requires a fresh
5/5 exact-draft Council review.

## 17. Current disposition

This replacement Stage 21C protocol is a local draft under the frozen and
merged Increment 21 Erratum 0001. It has not been reviewed, frozen, committed,
pushed, merged, or implemented. No credential has been accessed and no live
GitHub operation has been performed while drafting it. Runtime and tests remain
unchanged.

The next permitted action under the current authority is local validation and
Council review preparation. Commit, push, pull request, merge, implementation,
credentials, live GitHub operations, deployment, production use, KOS or IDM
changes, signing, identity allocation, and membership activation require
separate explicit authority.
