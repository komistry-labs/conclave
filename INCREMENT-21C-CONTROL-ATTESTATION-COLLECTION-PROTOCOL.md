# CONCLAVE Stage 21C — Control-Attestation Collection Protocol

## Status

Protocol candidate · local draft · Council review required · not frozen · not
authorized for implementation or use.

This candidate defines the independently operated, read-only evidence-collection
procedure whose exact canonical SHA-256 may later be named by a
`control_attestor` trust authorization. It does not create that trust
authorization, generate a key, access a credential, collect live evidence, or
authorize any GitHub or CONCLAVE operation.

## 0. Governing authority and identity

This candidate is drafted under Arthur's bounded authorization of 15 September
2026 and the frozen replacement Stage 21C protocol:

- `INCREMENT-21C-READINESS-AND-HUMAN-MERGE-OBSERVATION.md`;
- SHA-256
  `d3701754c7ab782835bc92db07c055509e415a69765373ed5cd30f250164b257`;
- Git blob `6553d2371c534e0c8159aa9a8ddd2fec964dc208`; and
- freeze record `INCREMENT-21C-PROTOCOL-FREEZE-RECORD.md`.

The governing Stage 21C protocol prevails over this subordinate collection
procedure. This procedure supplies signed factual evidence to Stage 21C; it
does not amend Stage 21C, create authority, decide readiness, authorize a human
merge, or execute an action.

The future frozen SHA-256 of this complete document, including its factual
references and disposition, is the only value eligible to appear as
`collection_protocol_sha256`. Until Council review and Arthur freeze, no hash
of this draft may be used as that value.

## 1. Objective and completion boundary

The collector's sole objective is to produce the complete, source-bound facts
needed by an independent control attestor to author one
`github-ruleset-no-bypass-attestation/0.2.0` record for either:

1. `purpose: readiness`; or
2. `purpose: action_interval`.

The collection is complete only when it positively accounts for:

- repository, account, pull-request, base-ref, base-commit, and head-commit
  identities;
- legacy branch protection and effective branch rules;
- every applicable active or enabled repository and organization ruleset, plus
  positive proof that no enterprise ruleset can apply; an enterprise-governed
  or unknown-enterprise target is deliberately incomplete in this revision;
- every effective required check, approval, code-owner, last-push,
  conversation-resolution, strict-update, administrator-enforcement,
  force-push, deletion, and normal-merge requirement;
- every relevant bypass route of the configured human, Stage 21A observation
  App, and Stage 21A observation installation;
- a complete review-thread inventory without retaining conversation content;
  and
- for `action_interval`, continuous evidence sufficient to determine whether
  protection, rulesets, enforcement, or bypass capability changed at any point
  in the covered interval.

The collector produces evidence only. The independent attestor separately
validates the collection, reduces its closed findings, and signs the Stage 21C
attestation. Collection success is not an attestation and never implies
`controls_intact`.

## 2. Explicit non-objectives

This protocol does not permit the collector, attestor, or CONCLAVE to:

- merge, queue, auto-merge, close, reopen, approve, review, dismiss, comment on,
  label, assign, or modify a pull request;
- create, update, delete, enable, disable, bypass, or test a branch-protection
  rule, ruleset, repository setting, team, role, App, installation, deploy key,
  credential, or organization setting;
- create a commit, branch, tag, release, deployment, check, status, or workflow
  dispatch;
- generate, hold, copy, print, log, or recover an attestor private key;
- supply a credential, URL, request, response, or GraphQL transport to
  CONCLAVE;
- make the human action atomic with observation;
- infer an unavailable permission or bypass state from silence, a `404`, a
  missing field, or a promise not to exercise a capability;
- treat matching before-and-after snapshots as proof of interval continuity;
  or
- create an authority, decision, membership, production, constitutional, KOS,
  or IDM effect.

## 3. Process and actor separation

The following actors and processes are distinct:

1. **Stage 21A observation installation** — supplies the already durable
   repository-scoped observations consumed by readiness and post-action cycles;
2. **attestor acquisition supervisor** — exclusively holds the transient
   GitHub lease, executes the closed transport, and writes immutable raw
   evidence;
3. **external collector normalizer** — requests only fixed operation keys and
   reduces supervisor-supplied responses into closed factual projections;
4. **independent control-attestor verifier/signer** — one build-pinned,
   closed-state-machine executable independently validates the raw and
   normalized evidence and, only after reaching its terminal verified state,
   obtains an opaque one-use handle to sign the exact verified attestation;
5. **configured human merge principal** — may later perform one ordinary
   protected GitHub merge outside CONCLAVE;
6. **independent review principals** — may supply qualifying GitHub reviews;
   and
7. **CONCLAVE reducer** — verifies the attestation and combines it with durable
   Stage 21A observations without collecting or signing it.

The configured human, every counted reviewer, and the control attestor must be
distinct governed principals. The acquisition supervisor and collector
normalizer are operated for the attestor but cannot be the configured merge
actor or a counted reviewer. The verifier/signer is a separate executable from
both and has no general signing interface; the external key provider releases
no key bytes and issues a one-use handle only to the approved executable in its
terminal verified state. The private key remains offline until that transition.
The Stage 21A App and installation cannot be represented as human or attestor.

Security bindings use immutable numeric or node identities. Login, display
name, email, organization name, team slug, App slug, and repository name are
descriptive only and cannot establish identity.

Any prohibited role collision, missing numeric identity, ambiguous identity,
identity change, or inability to bind a descriptive value to its immutable
identity makes collection incomplete.

## 4. Isolation and credential boundary

The acquisition supervisor, collector normalizer, and attestor verifier/signer
are separate executables and process boundaries. None is importable by
`conclave`; all are absent from the CONCLAVE wheel and expose no callable
transport or credential object to CONCLAVE. CONCLAVE receives only an already
signed Stage 21C attestation and its allowed source hashes.

The acquisition supervisor exclusively holds a dedicated, short-lived
credential lease obtained from a separately governed provider. The collector
normalizer never receives the token, authorization header, cookie, or lease
handle; it may request only a build-pinned operation key and canonical bound
parameters through a local mutually authenticated channel. The supervisor
independently validates that request against the closed table before transport.
The provider, credential type, repository,
organization, enterprise when applicable, principal, permissions, issue time,
expiry, and non-reversible credential-instance tag must be recorded in a
sanitized lease-evidence artifact before collection begins. Token bytes,
authorization headers, cookies, private keys, and recovery material are never
durable.

GitHub currently requires organization `Administration: write` permission to
return complete organization-ruleset details, even for the read operation and
even though `bypass_actors` is withheld without ruleset write access. That
platform permission is a capability ceiling, not authority for this protocol.
If such visibility is required, its use requires a separately governed
attestor credential whose executable surface remains GET/query-only. Both the
supervisor and normalizer must mechanically reject every mutation method and
mutation GraphQL document. If the necessary complete visibility cannot be
provided safely, the collection result is incomplete; it may not silently
reduce its scope.

The credential must not belong to the configured merge human, any counted
reviewer, or the Stage 21A observation installation. It must not be stored on
the future offline signing medium. Credential acquisition and key custody are
separate processes.

The provider creates two closed immutable artifacts. The admission receipt,
created before the first request, contains exactly:

```text
schema_version: literal(github-control-credential-lease-admission/0.1.0)
provider_principal_id: ascii(128)
provider_key_id: ascii(128)
provider_authorization_sha256: hash
lease_instance_tag: hash
credential_type: enum(github_app_user_access_token,github_app_installation_access_token,fine_grained_personal_access_token)
credential_principal_github_user_id: id?
credential_app_id: id?
credential_installation_id: id?
repository_id: id
account_id: id
permission_set: [ascii(64),64]
issued_at: ts
expires_at: ts
acquisition_session_id: ascii(64)
attestor_supervisor_nonce: ascii(64)
acquisition_supervisor_executable_sha256: hash
delivery_mode: literal(direct_authenticated_ipc)
operator_secret_access: literal(false)
content_hash: hash
```

Null identity fields follow the credential type and exactly one governed
credential principal is unambiguous. Permissions are sorted and unique. The
terminal closure evidence, created after provider-confirmed revocation or
expiry, contains exactly:

```text
schema_version: literal(github-control-credential-lease-closure/0.1.0)
admission: external_record_ref
lease_instance_tag: hash
acquisition_session_id: ascii(64)
attestor_supervisor_nonce: ascii(64)
closed_at: ts
close_result: enum(revoked,expired,failed)
provider_evidence_sha256: hash
content_hash: hash
```

`failed` is never successful cleanup. Every REST and GraphQL raw record and
envelope cites the admission content hash; the terminal bundle cites the
closure content hash. Missing, conflicting, overbroad, operator-visible,
unapproved, expired-before-use, or unclosed lease evidence makes collection
incomplete.

No live collection is authorized by this document. Credential provisioning and
live use each require later, explicit, repository-specific authority.

## 5. Closed collector input

A readiness cycle begins from one closed `collection_request`. An action
interval begins from an immutable `action_interval_open` request before human
handoff and ends with a separately immutable `action_interval_close` request
after the final Stage 21A observations exist. Both use this exact canonical
UTF-8 JSON schema:

```text
schema_version: literal(github-control-attestation-collection-request/0.1.0)
collection_protocol_sha256: hash
collector_implementation_manifest_sha256: hash
collector_implementation_authorization_sha256: hash
implementation_trust_store_sha256: hash
implementation_trust_store_authorization_sha256: hash
acquisition_supervisor_executable_sha256: hash
collector_normalizer_executable_sha256: hash
attestor_verifier_signer_executable_sha256: hash
pinned_rest_table_sha256: hash
pinned_graphql_document_sha256: hash
continuity_source_profile_sha256: hash?
purpose: enum(readiness,action_interval)
phase: enum(readiness,action_interval_open,action_interval_close)
interval_id: ascii(64)?
open_request_sha256: hash?
readiness_boundary: external_record_ref?
human_handoff_boundary: external_record_ref?
post_action_boundary: external_record_ref?
repository_profile: record_ref
repository_id: id
repository_node_id: s(128)
account_id: id
account_node_id: s(128)
pull_request_number: id
pull_request_node_id: s(128)
base_ref: s(255)
base_commit: oid
head_commit: oid
configured_human_principal_id: ascii(128)
configured_human_github_user_id: id
observation_app_id: id
observation_installation_id: id
control_attestor_principal_id: ascii(128)
control_attestor_github_user_id: id?
initial_stage_21a_branch_protection_observation: record_ref
initial_stage_21a_branch_rules_observation: record_ref
initial_stage_21a_ruleset_summary_observation: record_ref
final_stage_21a_branch_protection_observation: record_ref?
final_stage_21a_branch_rules_observation: record_ref?
final_stage_21a_ruleset_summary_observation: record_ref?
coverage_not_before: ts
coverage_not_after: ts?
maximum_logical_reads: literal(96)
maximum_network_transmissions: literal(192)
maximum_elapsed_seconds: literal(600)
created_at: ts
content_hash: hash
```

For `readiness`, `phase` is `readiness`; `interval_id`, `open_request_sha256`,
all three boundary references, and all three final observations are null;
`coverage_not_after` is non-null and
contains the initial Stage 21A observation interval no later than attestation
issue.

For `action_interval_open`, `purpose` is `action_interval`; a fresh
`interval_id` is non-null; `open_request_sha256`, all three boundary references,
all three final observations, and `coverage_not_after` are null. The three initial observations and
`coverage_not_before` bind the planned readiness inputs, and the supervisor
starts the approved continuity source before readiness sealing and human
handoff.

For `action_interval_close`, `purpose` is `action_interval`; `interval_id` is
identical to the open request; `open_request_sha256` equals the `content_hash`
of that immutable request; all three final observations and
all three boundary references and `coverage_not_after` are non-null and end no
earlier than those observations.
All target, actor, implementation, protocol, continuity-profile, initial-
observation, coverage-start, and limit members must byte-for-byte equal the
open request. `created_at` must be later; phase, open-reference, final-
observation, boundary-reference, coverage-end, and content-hash members take
their close values.
The close request does not start, resume, or repair collection; it only binds facts
that did not exist when the interval opened. The same acquisition session,
supervisor nonce, lease policy, and continuous evidence stream must cover both.
Missing, late, conflicting, or multiply matching open/close requests make the
interval incomplete.

`collector_implementation_manifest_sha256` identifies a closed manifest that
binds the source commit/tree, build recipe, dependency lock, separate
supervisor, normalizer, and verifier executable/package hashes, REST table
hash, GraphQL document hash, schema hashes, and supported platform.
`collector_implementation_authorization_sha256` identifies a separate
Arthur-approved exact-manifest decision loaded by the attestor from its local
deployment-pinned trust store. The five executable/table/document hashes in the
request must equal that manifest. `continuity_source_profile_sha256` is non-null
only for `action_interval` and must identify an exact, separately approved
source/event/retention profile included in the same trust store.

The trust store is a separately immutable configuration object outside every
executable and package hash. It contains exactly:

```text
schema_version: literal(github-control-implementation-trust-store/0.1.0)
stage_21c_protocol_sha256: hash
collection_protocol_sha256: hash
repository_id: id
collector_implementation_manifest_sha256: hash
collector_implementation_authorization_sha256: hash
acquisition_supervisor_executable_sha256: hash
collector_normalizer_executable_sha256: hash
attestor_verifier_signer_executable_sha256: hash
pinned_rest_table_sha256: hash
pinned_graphql_document_sha256: hash
authorized_continuity_source_profiles: [hash,8]
not_before: ts
expires_at: ts
status: enum(active,revoked)
content_hash: hash
```

After the executable hashes and manifest authorization exist, a separate exact
Arthur deployment authorization names this store's `content_hash` and installs
the object through a fixed local path as a read-only handle. That authorization
is external to the store and therefore does not create a hash cycle. The
request carries its SHA-256 as
`implementation_trust_store_authorization_sha256`. The governed launcher and
external key-provider policy pin both hashes, reject mutable or caller-selected
configuration, and give the verifier only that already-open handle. Trust-store bytes are
explicitly excluded from the executable/package hash, so installing the store
does not change an authorized executable. The verifier recomputes the store
hash and requires the request, manifest, executable, table, document, profile,
repository, validity, and status to match. A request-carried store or hash
cannot select or authenticate the store itself.

This binding is mandatory even though the implementation is produced after the
collection procedure freezes. The procedure defines how implementation
identity is carried and verified; the later Arthur decision selects one exact
reviewed build without changing this protocol. A caller-carried manifest or
decision hash cannot trust itself.

The request grants no authority and contains no credential or signing key. Its
profile is omitted deliberately: it is an external collection input, not a
sixth Stage 21C durable record family.

Unknown members, duplicate JSON names, floats, invalid Unicode, noncanonical
timestamps, negative or zero IDs, malformed hashes, mixed Git object formats,
oversized strings, invalid references, and noncanonical JSON are rejected
before any credential request. Missing, unapproved, revoked, conflicting, or
multiply matching implementation or continuity authorization stops before any
credential request.

`target_sha256` used below equals the `content_hash` of exactly this closed
object, using values copied unchanged from the request:

```text
schema_version: literal(github-control-attestation-target/0.1.0)
repository_id: id
repository_node_id: s(128)
account_id: id
account_node_id: s(128)
pull_request_number: id
pull_request_node_id: s(128)
base_ref: s(255)
base_commit: oid
head_commit: oid
configured_human_principal_id: ascii(128)
configured_human_github_user_id: id
observation_app_id: id
observation_installation_id: id
control_attestor_principal_id: ascii(128)
control_attestor_github_user_id: id?
content_hash: hash
```

As for every content-addressed object in this protocol, `content_hash` is the
lowercase SHA-256 of the canonical object with the `content_hash` member
omitted; verification reconstructs that preimage exactly.

## 6. Closed source and transport table

The collector's network surface is closed to REST requests under the exact
origin `https://api.github.com` and to the single GraphQL URL
`https://api.github.com/graphql`. HTTPS, verified hostname, system trust
store, TLS 1.2 or later, direct connections, ignored proxy environment,
forbidden redirects, fixed GitHub API version, fixed media type, and a fixed
user agent are mandatory. Alternate hosts, GitHub Enterprise Server origins,
caller URLs, redirects, proxy discovery, DNS override, custom trust roots, and
generic request construction are forbidden.

The permitted REST requests are GET only:

| Key | Fixed path | Purpose |
|---|---|---|
| `repository.get` | `/repos/{owner}/{repository}` | repository/account identity and merge-method settings |
| `user_by_id.get` | `/user/{account_id}` | bind configured human numeric ID to transient login and node identity for username-routed reads |
| `pull_request.get` | `/repos/{owner}/{repository}/pulls/{pull_number}` | exact PR/head/base identity and state |
| `branch_protection.get` | `/repos/{owner}/{repository}/branches/{branch}/protection` | legacy branch-protection controls and bypass allowances |
| `repository_rulesets.list` | `/repos/{owner}/{repository}/rulesets?includes_parents=true&per_page=100&page=N` | complete repository-effective summary, including inherited rulesets |
| `repository_ruleset.get` | `/repos/{owner}/{repository}/rulesets/{ruleset_id}?includes_parents=true` | complete applicable ruleset details and bypass actors |
| `organization_rulesets.list` | `/orgs/{organization}/rulesets?per_page=100&page=N` | positive organization-scope inventory |
| `organization_ruleset.get` | `/orgs/{organization}/rulesets/{ruleset_id}` | complete organization ruleset, conditions, rules, and bypass actors |
| `organization_membership.get` | `/orgs/{organization}/memberships/{username}` | corroborating human membership/role evidence only |
| `pull_request_files.list` | `/repos/{owner}/{repository}/pulls/{pull_number}/files?per_page=100&page=N` | exact base-to-head changed-file set for CODEOWNERS evaluation |
| `codeowners_dotgithub.get` | `/repos/{owner}/{repository}/contents/.github/CODEOWNERS?ref={base_commit}` | first CODEOWNERS search location at exact base commit |
| `codeowners_root.get` | `/repos/{owner}/{repository}/contents/CODEOWNERS?ref={base_commit}` | second CODEOWNERS search location when the first is positively absent |
| `codeowners_docs.get` | `/repos/{owner}/{repository}/contents/docs/CODEOWNERS?ref={base_commit}` | third CODEOWNERS search location when the first two are positively absent |
| `team_membership.get` | `/orgs/{organization}/teams/{team_slug}/memberships/{username}` | team-mediated bypass membership after numeric team/user binding |
| `team_members.list` | `/orgs/{organization}/teams/{team_slug}/members?role=all&per_page=100&page=N` | complete relevant team membership after numeric team binding |
| `team_child_teams.list` | `/orgs/{organization}/teams/{team_slug}/teams?per_page=100&page=N` | recursive nested-team expansion with cycle detection |
| `collaborator_permission.get` | `/repos/{owner}/{repository}/collaborators/{username}/permission` | effective human repository permission after numeric user binding |
| `repository_teams.list` | `/repos/{owner}/{repository}/teams?per_page=100&page=N` | team-mediated repository capability inventory |
| `repository_collaborators.list` | `/repos/{owner}/{repository}/collaborators?affiliation=direct&per_page=100&page=N` | explicit direct collaborator capability and CODEOWNERS eligibility inventory |
| `deploy_keys.list` | `/repos/{owner}/{repository}/keys?per_page=100&page=N` | deploy-key bypass inventory |
| `organization_custom_repository_roles.list` | `/orgs/{organization}/custom-repository-roles` | complete custom repository-role definitions and base permissions |
| `organization_roles.list` | `/orgs/{organization}/organization-roles` | complete custom organization-role definitions and permissions |
| `organization_role_users.list` | `/orgs/{organization}/organization-roles/{role_id}/users?per_page=100&page=N` | users assigned to a relevant custom organization role |
| `organization_role_teams.list` | `/orgs/{organization}/organization-roles/{role_id}/teams?per_page=100&page=N` | teams assigned to a relevant custom organization role |
| `organization_audit_log.list` | `/orgs/{organization}/audit-log?include=all&order=asc&per_page=100&phrase={fixed_interval_filter}&after={cursor}` | approved continuity events when the governed profile proves complete coverage |

The implementation manifest must contain the exact canonical REST table above,
the fully percent-encoded query templates, permissions, and response schema
hashes. GitHub's documented
repository and organization endpoint paths require owner, repository, or
organization names. The collector may use those path values only after binding
them to the required numeric and node identities in the same cycle; path text
is routing data and is never retained as authority.

The already durable and independently verified Stage 21A repository profile
supplies transient owner/repository routing names paired with numeric repository
and account identities. The first `repository.get` response must reproduce both
numeric identities and the repository node ID before those names may route any
further repository or organization request. The first configured-human lookup uses only
`configured_human_github_user_id` as `account_id`; its returned numeric ID must
match before its login may route membership or permission requests. Returned
logins, owner names, repository names, and team slugs remain transient routing
values tied to their numeric/node evidence. Missing, renamed, conflicting, or
unavailable numeric lookup evidence yields `IDENTITY_AMBIGUOUS` before any
dependent name-routed call.

Complete visibility has the following fail-closed credential requirements:

- repository ruleset details, including bypass actors, require repository
  Administration write visibility when GitHub withholds those actors from a
  lesser credential;
- organization ruleset details require organization Administration write
  visibility;
- audit-log use requires the exact plan, organization permission, event-class,
  retention, pagination, and delivery guarantees frozen in the approved
  continuity profile; and
- the initial revision does not admit enterprise credentials or enterprise
  collection.

These are visibility ceilings, not operational permissions. The supervisor and
normalizer executables expose only the fixed GET and query operations above and
reject a credential broader than the approved manifest requires. A credential
that cannot expose every applicable bypass actor, or one whose effective scope
cannot be proved exactly, yields `PERMISSION_INCOMPLETE`. Repository custom
roles, secret or nested team relationships, and other indirect grants are
supported only where the closed table and response schemas positively
enumerate their definitions, full relevant membership, and current effective
permission. If any unsupported role can affect the target, its existence
cannot be ruled out, or an expansion is not complete, the actor-capability
inventory is incomplete.

`GET /app/installations/{installation_id}` is deliberately not selected. It is
available only to the authenticated App using that App's JWT, which would
improperly couple the external collector to the Stage 21A observation App's
private-key path. Observation App and installation identity, repository
selection, permission ceiling, and lease freshness instead come from the
already durable Stage 21A repository profile, provider-key record, operation
authorization, intent, attempt claim, credential-lease evidence, and
observation chain. Every referenced object is hash- and identity-verified by
the attestor. Missing or stale Stage 21A lease evidence makes the App or
installation capability inventory incomplete.

Enterprise rulesets require one of two complete paths:

1. a separately governed enterprise inventory source with fixed read-only
   operations and positive enterprise identity; or
2. positive evidence that the repository's organization is not governed by an
   enterprise capable of supplying applicable rulesets.

Absence of enterprise access is not evidence of absence. The initial closed
profile supports no enterprise-ruleset detail endpoint and therefore cannot
produce `complete` for an enterprise-governed target or any target whose
enterprise status is unknown. Supporting an enterprise requires a revision of
this collection protocol that adds the exact enterprise endpoint, Enterprise
Administration visibility, actor expansion, and plan/identity evidence; an
implementation manifest alone cannot expand the endpoint table.

The fixed GraphQL document is exactly the UTF-8 text between the markers below,
including LF line endings and final LF. Its SHA-256 is recorded in the reviewed
implementation manifest and repeated in every request:

```graphql
query ConclaveStage21CReviewThreads($owner: String!, $repository: String!, $pullRequestNumber: Int!, $after: String) {
  repository(owner: $owner, name: $repository) {
    id
    databaseId
    pullRequest(number: $pullRequestNumber) {
      id
      number
      headRefOid
      baseRefOid
      reviewThreads(first: 100, after: $after) {
        totalCount
        pageInfo {
          endCursor
          hasNextPage
        }
        nodes {
          id
          isResolved
        }
      }
    }
  }
}
```

This one persisted GraphQL query document may be sent only as `POST` to the
exact `https://api.github.com/graphql` URL by the acquisition supervisor for
pull-request review-thread inventory. The POST body is a mechanically produced
closed envelope containing only the fixed query text and its bounded variables;
this sole GraphQL transport exception does not permit a REST POST or any
mutation. It selects only repository
numeric/node identity, PR number/node identity, exact head/base OIDs,
review-thread node ID, `isResolved`, pagination cursors, and total counts. It
selects no body, diff,
path, author login, comment content, reaction, timeline, or mutation field.
Variables are limited to the already bound repository owner/name, PR number,
`first:100`, and a nullable server cursor. The document's exact SHA-256 is
build-pinned. Introspection, aliases that change selected semantics, fragments
outside the pinned document, directives, persisted-query fallback, batching,
subscriptions, and every `mutation` operation are forbidden.

This external GraphQL allowance does not amend Stage 21C §5.2: CONCLAVE gains no
GraphQL dependency, credential, query, result, or transport. Only the attestor's
signed inventory count and hash cross the boundary.

## 7. Pagination, retry, rate, and size bounds

All list connections use a fixed page size of `100`, at most `10` pages and
`1000` items. Review threads use at most `100` items as required by frozen Stage
21C. A response that asserts more items than the applicable ceiling, provides a
next cursor after the last permitted page, repeats or cycles a cursor, changes
total count during one snapshot, duplicates an immutable item identity, or
omits pagination metadata is incomplete and stops the cycle.

Each logical read permits one initial transmission and at most one retry, only
before any response body is accepted and only for a transport failure or GitHub
`502`, `503`, or `504`. The retry uses the identical method, target, headers,
variables, credential lease, and deadline. `401`, `403`, `404`, `409`, `422`,
`429`, other `4xx`, parsing failure, pagination failure, permission omission,
rate-limit response, and any response after partial acceptance are not retried.

Before any next transmission, the supervisor durably writes and reads back one
closed attempt record for the preceding transmission:

```text
schema_version: literal(github-control-transmission-attempt/0.1.0)
collection_request_sha256: hash
implementation_trust_store_sha256: hash
implementation_trust_store_authorization_sha256: hash
acquisition_supervisor_executable_sha256: hash
acquisition_session_id: ascii(64)
attestor_supervisor_nonce: ascii(64)
operation_key: ascii(64)
logical_read_number: count
transmission_number: count
method: enum(GET,POST)
request_target_sha256: hash
credential_lease_evidence_sha256: hash
started_at: ts
completed_at: ts
outcome: enum(response,transport_failure)
transport_failure_class: enum(dns,tls,connect,write,read_timeout,connection_reset)?
http_status: id?
raw_response_evidence: external_record_ref?
retry_eligible: bool
content_hash: hash
```

For `response`, failure class is null and both status and raw-response reference
are non-null. For `transport_failure`, failure class is non-null and status and
raw-response reference are null. A response-bearing attempt is recorded even
when its response is later rejected or retryable. `retry_eligible` is a derived
fact: true only for the first attempt and one of the permitted conditions
above. Attempt numbers begin at one, are contiguous within a logical read, and
never exceed two. The verifier recomputes eligibility and rejects a second
attempt without a complete first-attempt record or after any accepted body.

The complete cycle permits at most `96` logical reads, `192` transmissions,
`600` elapsed seconds, `10` pages per list, `1000` rules/rulesets/actors, `100`
review threads, `2 MiB` decompressed bytes per response, and `32 MiB`
decompressed bytes in aggregate. Those are ceilings, not permission to issue
unnecessary requests. The implementation freezes a smaller derived budget for
the exact endpoint plan.

Primary or secondary rate limitation stops collection. A partial result is
`SOURCE_EVIDENCE_INCOMPLETE`; the collector does not sleep until reset, resume
pagination, borrow a later credential, or join partial evidence from another
cycle.

Connection/TLS uses a five-second deadline, socket reads use twenty seconds,
and each logical operation uses a sixty-second monotonic deadline. Trusted UTC
provides record times; monotonic time enforces elapsed deadlines. Clock rollback,
missing trusted time, leap-second text, subsecond serialization, or time drift
beyond the implementation's frozen tolerance stops collection.

## 8. Source-evidence envelope

External evidence uses a closed content-addressed reference, never a path or
caller-selected locator:

```text
external_record_ref = {
  schema_version: ascii(64),
  content_hash: hash
}
```

The external store resolves the pair only by canonical schema family and
content hash, verifies the retrieved bytes and closed schema, rejects aliases
and multiple matches, and never accepts a filesystem path, URL, or mutable
name.

Before normalization, the acquisition supervisor durably creates exactly one
raw response object per response-bearing REST or GraphQL transmission:

```text
schema_version: literal(github-control-raw-response/0.1.0)
collection_request_sha256: hash
collector_implementation_manifest_sha256: hash
collector_implementation_authorization_sha256: hash
implementation_trust_store_sha256: hash
implementation_trust_store_authorization_sha256: hash
acquisition_supervisor_executable_sha256: hash
acquisition_session_id: ascii(64)
attestor_supervisor_nonce: ascii(64)
operation_key: ascii(64)
source_class: enum(rest,graphql)
method: enum(GET,POST)
fixed_document_sha256: hash?
request_target_sha256: hash
logical_read_number: count
transmission_number: count
received_at: ts
http_status: id
safe_headers: {
  content_type: s(128)?,
  content_encoding: enum(identity,gzip)?,
  date: s(128)?,
  etag: s(256)?,
  last_modified: s(128)?,
  link: s(4096)?,
  x_github_request_id: ascii(128)?,
  x_ratelimit_limit: ascii(32)?,
  x_ratelimit_remaining: ascii(32)?,
  x_ratelimit_reset: ascii(32)?,
  x_ratelimit_resource: ascii(64)?,
  x_ratelimit_used: ascii(32)?
}
wire_body_base64url: ascii(2796203)
wire_body_sha256: hash
wire_body_bytes: count
decoded_body_sha256: hash
decoded_body_bytes: count
credential_lease_evidence_sha256: hash
content_hash: hash
```

Every safe-header member is present and is null when absent. No other response
header is retained. `method` is `GET` for REST and `POST` for the one fixed
GraphQL transport; the GraphQL document hash is non-null only for GraphQL.
`request_target_sha256` hashes the canonical fixed operation key, fully encoded
path or GraphQL URL, and canonical variables without authorization material.
The unpadded base64url value decodes canonically to the exact HTTP message-body
bytes after transfer framing and before content decoding. Their hash and count
are recorded; the decoded hash and count are recomputed from the sole permitted
`identity` or `gzip` content encoding. Both encoded and decoded bodies have a
`2 MiB` ceiling; the complete canonical raw object has a `3 MiB` ceiling.
Truncation, stacked or alternate encoding, decompression overrun, duplicate
header ambiguity, missing status, or inconsistent lengths is failure.

Every accepted response is then reduced to a closed, sanitized source envelope
before durable storage. Each envelope contains exactly:

```text
schema_version: literal(github-control-source-envelope/0.1.0)
collection_request_sha256: hash
collector_implementation_manifest_sha256: hash
collector_implementation_authorization_sha256: hash
implementation_trust_store_sha256: hash
implementation_trust_store_authorization_sha256: hash
acquisition_supervisor_executable_sha256: hash
collector_normalizer_executable_sha256: hash
attestor_verifier_signer_executable_sha256: hash
pinned_rest_table_sha256: hash
pinned_graphql_document_sha256: hash
acquisition_session_id: ascii(64)
attestor_supervisor_nonce: ascii(64)
operation_key: ascii(64)
source_class: enum(rest,graphql,stage_21a)
method: literal(GET)?
fixed_document_sha256: hash?
stage_21a_observation: record_ref?
raw_response_evidence: external_record_ref?
credential_lease_evidence_sha256: hash?
repository_id: id
account_id: id
logical_read_number: count
transmission_count: count
page_number: count
observed_at: ts
http_status_class: enum(2xx,transport,none)
wire_body_sha256: hash
wire_body_bytes: count
normalized_projection_sha256: hash
item_count: count
pagination_complete: bool
identity_match: bool
permission_visibility: enum(complete,incomplete,not_observed)
rate_limit_class: ascii(64)?
rate_limit_remaining: count?
rate_limit_reset_at: ts?
reason_codes: [ascii(64),32]
content_hash: hash
```

For a Stage 21A source, `method`, `fixed_document_sha256`,
`raw_response_evidence`, and `credential_lease_evidence_sha256` are null and
`stage_21a_observation` is non-null. For REST, `method` is `GET`,
`fixed_document_sha256` and `stage_21a_observation` are null, and both the raw
response reference and lease-evidence hash are non-null. For GraphQL, `method`
and `stage_21a_observation` are null, the fixed-document hash, raw-response
reference, and lease-evidence hash are non-null, and the source is accepted
only for the pinned query document. No conditional member is omitted; it is
present with canonical null where required.

For a Stage 21A envelope, `logical_read_number`, `transmission_count`, and
`page_number` are zero; `http_status_class` is `none`; `wire_body_sha256` is
the SHA-256 of the exact canonical referenced Stage 21A record bytes;
`wire_body_bytes` is their byte length; `normalized_projection_sha256` hashes
the closed facts selected from that record; `pagination_complete` and
`identity_match` are true only after full record/reference validation;
`permission_visibility` is `not_observed`; and all rate-limit members are null.
For REST or GraphQL, logical-read, transmission, page, status, permission,
pagination, and rate fields are derived only from the cited raw record and
closed endpoint response schema.

Before the normalizer receives a response, the acquisition supervisor writes
the exact status, approved safe response headers, and body bytes directly from
its verified TLS stream to an immutable, encrypted, access-controlled
raw-response vault outside CONCLAVE. The normalizer has no write access to that
vault. The raw
record binds request hash, implementation identity, acquisition session,
attestor nonce, operation key, transmission number, lease-evidence hash,
receipt time, and the SHA-256 and byte count of each retained wire component.
The normalizer cannot mark an envelope complete unless raw-record creation,
durable readback, and cross-reference succeed.

Collection is an attestor-supervised acquisition session. Before any lease is
issued, the independent verifier supplies a fresh unpredictable nonce and
session identifier to the supervisor and normalizer over separate mutually
authenticated local channels. The supervisor binds both values to its lease,
transport, and raw records; the normalizer binds them to every request,
envelope, inventory, and bundle. The verifier obtains separate read-only access
to the sealed raw-response vault and
Stage 21A evidence store; it independently reads every cited object and
recomputes wire, normalized-projection, envelope, inventory, and bundle hashes.
It also validates supervisor-authenticated transport and lease provenance and
checks the implementation manifest, authorization, trust store, all three
executables, REST table, and GraphQL document against its deployment-pinned
read-only trust handle. Caller-carried hashes, self-consistent collector
output, TLS success asserted by the collector, or possession of a bundle hash
alone are insufficient provenance.

The private key and opaque signing handle remain unavailable throughout
acquisition and verification. The verifier/signer accepts only a bundle
reference, not caller-supplied attestation bytes or a signing request. After it
independently constructs canonical attestation bytes in its terminal verified
state, it binds request hash, session ID, nonce, bundle hash, attestation hash,
verifier/signer executable hash, key ID, and one-use handle identifier in an
internal signing release. The external key provider validates the approved
executable identity and one-use release state, returns only the signature, and
atomically consumes the handle. No stdin, command-line, environment, file,
socket, generic IPC, or reusable API can submit arbitrary bytes for signing.
Unavailable raw evidence, inaccessible Stage 21A evidence, missing session or
nonce binding, unverified lease or transport provenance, an unapproved build,
or any recomputation mismatch makes the future attestation `indeterminate`.

Raw bodies remain in the external vault for the minimum governed retention
period. CONCLAVE and the signed Stage 21C attestation retain only permitted
normalized facts and hashes. Logs and exceptions retain stable reason codes,
operation keys, and safe content hashes only.

## 9. Ruleset discovery and applicability

The collector establishes scope in this order:

1. bind repository ID/node ID, account ID/node ID, base full ref, and exact
   commits to the collection request and Stage 21A observations;
2. enumerate repository-effective rulesets with inherited parents included;
3. enumerate the complete organization ruleset inventory;
4. obtain details for every candidate repository or organization ruleset;
5. obtain the complete enterprise inventory or positive non-enterprise proof;
6. normalize each ruleset's source identity, target, enforcement, timestamps,
   conditions, rules, and bypass actors; and
7. evaluate applicability to the numeric repository and exact full base ref.

Applicability evaluation follows GitHub's documented include/exclude semantics
for repository ID/name/property and ref-name conditions. An exclusion takes
precedence where GitHub specifies it. Special selectors such as default branch
and all branches are resolved against facts collected in the same cycle.
Unsupported pattern syntax, unknown condition members, absent conditions,
conflicting duplicate rulesets, contradictory repository and organization
views, or inability to prove applicability is `RULESET_INCOMPLETE` or
`UNKNOWN_RULE`, never non-applicability.

Every applicable ruleset is retained in the exact Stage 21C
`applicable_ruleset` form. Conditions, full rule arrays, parameters, and bypass
actor arrays are canonicalized and hashed before unselected descriptive fields
are discarded. Rulesets sort by source-type UTF-8 bytes, numeric source ID, and
numeric ruleset ID. Duplicate keys with different content are conflicting
evidence.

`active` and `enabled` rules create requirements. `disabled` and `evaluate`
rules remain in the inventory but do not become effective requirements. Every
active rule must map to one frozen Stage 21A semantic-rule type and normalized
requirement. An unknown active rule makes `all_active_rules_known: false` and
the attestation `indeterminate`; the collector cannot ignore a rule merely
because it does not affect a currently recognized readiness predicate.

## 10. Effective-policy normalization

The collector computes a source-bound union of legacy branch protection and
every active applicable ruleset. It never applies a weakest-wins rule.

Required checks key on exact UTF-8 `(context, app_id)`, with null App before a
numeric App. Duplicate equal requirements combine sorted unique source-rule
hashes. A duplicate key with contradictory producer binding, semantics, or
parameters is conflicting evidence.

The effective approval count is the maximum of `1`, legacy protection, and all
active applicable rulesets. Boolean safeguards use the most restrictive
effective interpretation: any active requirement for strict updating,
administrator enforcement, conversation resolution, code-owner approval, or
last-push approval makes it required. Any active permission for force push,
deletion, alternate merge method, queue substitution, auto-merge, or a relevant
bypass is retained as a positive unsafe fact.

The exact `effective_policy` output is the Stage 21C §4.2 object. Every field
must retain one or more source-evidence hashes in the external normalization
bundle even though the signed Stage 21C object carries the bounded aggregate
source hashes. A value without a complete source chain makes
`all_effective_requirements_satisfied: false` and `POLICY_INCOMPLETE`.

Code-owner eligibility is derived from the exact base commit and exact
base-to-head changed-file inventory. The collector searches only the base
commit, in GitHub's order: `.github/CODEOWNERS`, root `CODEOWNERS`, then
`docs/CODEOWNERS`; the first existing file governs and an invalid line does not
cause fallback to a later location. The build-pinned evaluator
implements GitHub-compatible syntax, last-matching-pattern precedence, path
matching, and invalid-line handling. It maps every changed path to the required
owners and positively verifies that each user or team still exists and has
explicit repository write access at collection time. A user owner must appear
in the complete `affiliation=direct` collaborator inventory with sufficient
permission; a team owner must appear in the complete repository-team inventory
with sufficient permission, and its relevant membership must be complete.
Effective permission aggregated from organization base role, enterprise grant,
or an unidentified source is not explicit-access proof. Missing
files when code-owner review is required, changed-file truncation, ambiguous
precedence, unsupported pattern semantics, inaccessible source, invalid owner,
unknown team expansion, or inability to map an owner to immutable numeric IDs
makes the requirement incomplete. CODEOWNERS and changed paths are hashed and
excluded from the attestation.

The initial closed source table does not contain a GitHub source that identifies
the pusher of the exact most recent reviewable head push. Organization audit
`git.push` evidence is not accepted for that purpose because its documented
fields do not bind the actor to the exact ref and head commit. Consequently,
when last-push approval is required this revision ends collection as incomplete
with `LAST_PUSH_IDENTITY_INCOMPLETE` and the attestor constructs no Stage 21C
attestation from that cycle. Login text, commit author/committer, PR
sender, or audit actor alone is insufficient. Supporting this control requires
a revision to the closed source table and protocol; a continuity profile or
implementation manifest cannot add the missing source.

## 11. Review-thread conversation inventory

The pinned GraphQL query enumerates every review thread for the exact PR node.
The collector verifies repository, PR number, PR node, head, and base binding
against the collection request before accepting the inventory.

Each normalized item contains only:

```text
thread_node_id: s(128)
is_resolved: bool
```

Items sort by node ID and are unique. The collector records total count,
unresolved count, pagination completeness, and the canonical SHA-256 of the
complete ordered inventory. Thread bodies, comments, authors, paths, diffs,
replies, reactions, and resolution explanations are discarded.

A missing node, null resolution state, page/cursor anomaly, count mismatch,
permission omission, simultaneous inventory change, or more than `100` threads
makes `complete: false` and yields `CONVERSATION_INCOMPLETE`. Zero threads is a
complete positive inventory only when GitHub positively returns zero with
complete pagination for the exact PR.

The attestor may report `unresolved_thread_count > 0` only from a complete
inventory. An incomplete inventory cannot be converted into a positive
unresolved count or a claim of zero unresolved threads.

## 12. Actor-capability and bypass inventory

The collector evaluates the configured human, observation App, and observation
installation separately. It inventories all known paths by which each could
avoid or weaken the effective controls, including:

- repository administrator or organization-owner status;
- custom organization or repository roles;
- direct collaborator permission;
- team-derived permission and nested-team membership;
- branch-protection restrictions, dismissal restrictions, and pull-request
  bypass allowances;
- repository, organization, and enterprise ruleset bypass actors and modes;
- GitHub App, installation, and repository-selection capability;
- deploy-key and integration bypass entries;
- ability to alter checks, statuses, reviews, conversations, protection,
  rulesets, code-owner sources, or repository settings; and
- any documented GitHub role or feature capable of bypassing or disabling an
  effective requirement.

Actor matching uses numeric ID and actor type. The closed non-enterprise actor
domain is `Integration`, `OrganizationAdmin`, `RepositoryRole`, `Team`,
`DeployKey`, and `User`. `OrganizationAdmin` and `RepositoryRole` entries are
expanded against current immutable membership and role evidence. `Team`
entries are expanded to numeric membership, including nested and secret teams.
`Integration` entries bind App ID and installation scope. `User` entries bind
numeric user ID. `DeployKey` entries remain positive bypass classes when
applicable and may not be discarded because an actor ID is null. Unknown actor
types or an expansion that the closed endpoint set cannot complete make the
inventory incomplete.

GitHub enterprise rulesets may additionally expose `EnterpriseOwner` or
`EnterpriseRole`. Because this revision has no enterprise collection path,
either type, enterprise governance, or unknown enterprise status makes the
collection incomplete. It may never be normalized into a non-enterprise actor
or treated as absent.

Any `always`, `pull_request`, or `exempt` path applicable to the target actor
counts as bypass. A promise, policy note, unused status, audit-log silence, or
normal UI presentation cannot negate an available bypass capability.

The inventory is complete only when every source scope and indirect membership
is positively enumerated. Each of `human_has_bypass`, `app_has_bypass`, and
`installation_has_bypass` is null when its inventory is incomplete. A true
value yields `BYPASS_PRESENT`; a false value is permitted only with complete,
source-bound negative evidence. The canonical full inventory is hashed into
`capability_inventory_sha256` and not copied into CONCLAVE.

The supervisor credential capability is recorded in its external lease
evidence and assessed as an operational separation risk, but it does not
replace the three frozen actor fields. The lease provider delivers the secret
directly into the approved supervisor process; no operator, normalizer,
verifier, signer, file, environment variable, command line, clipboard, or log
may receive it. The supervisor has no generic request interface, and its
approved executable identity, process isolation, operation transcript, and
lease closure are independently verified. The control attestor must refuse to
sign `controls_intact` if credential scope, identity, delivery, executable, or
handling could have modified the target during collection without independently
detectable evidence.

## 13. Readiness collection sequence

A `readiness` collection is one non-resumable cycle:

1. validate the canonical request and already durable Stage 21A references;
2. acquire and durably admit a sanitized external credential-lease record;
3. bind repository, account, PR, base, head, human, App, and installation IDs;
4. collect repository and organization scope inventories and positive
   non-enterprise proof;
5. collect complete branch protection and all candidate ruleset details;
6. collect conversation threads, code-owner evidence, last-push evidence, and
   actor-capability evidence;
7. normalize applicable rules and effective policy;
8. repeat repository, PR, branch-protection, ruleset-summary, conversation-count,
   and actor-capability fingerprints as a final drift barrier;
9. close and erase the credential lease;
10. seal and read back the immutable external evidence bundle; and
11. notify the independent attestor that the sealed bundle and its cited raw
    and Stage 21A evidence are ready for separate read-only verification.

Any mismatch between initial and final barrier facts is conflicting evidence.
No attestation is signed from that cycle. A fresh request and fresh lease are
required; partial evidence cannot be resumed or combined.

The attestor independently reads the cited immutable evidence and verifies
every raw wire hash, projection, envelope, inventory, bundle hash,
implementation and lease authorization, transport provenance, completeness
marker, source binding, policy reduction, time bound, role separation, and
request identity. It then constructs the exact Stage 21C attestation and
applies the frozen reason precedence. Collection software never possesses the
signing key.

## 14. Action-interval continuity

An `action_interval` collection starts when the immutable open request is
accepted no later than the readiness seal and ends only when its matching close
request and all post-action observations have been verified. The interval is
named before the human handoff; it cannot be reconstructed after the fact.
Evidence acquired before close binds the open-request hash; the final Stage 21A
envelopes and close validation bind the close-request hash. The bundle binds
both external references, the shared interval ID, session ID, and nonce. No
source may migrate between request identities or intervals.

The supervisor seals three immutable external boundary objects. Their schemas
are exact:

```text
readiness_boundary = {
  schema_version: literal(github-control-readiness-boundary/0.1.0),
  open_request: external_record_ref,
  interval_id: ascii(64),
  acquisition_session_id: ascii(64),
  attestor_supervisor_nonce: ascii(64),
  readiness_record: record_ref,
  readiness_sealed_at: ts,
  continuity_source_profile_sha256: hash,
  source_stream_id: ascii(128),
  source_position: s(512),
  boundary_observed_at: ts,
  content_hash: hash
}

human_handoff_boundary = {
  schema_version: literal(github-control-human-handoff-boundary/0.1.0),
  open_request: external_record_ref,
  readiness_boundary: external_record_ref,
  interval_id: ascii(64),
  acquisition_session_id: ascii(64),
  attestor_supervisor_nonce: ascii(64),
  human_authorization_record: record_ref,
  human_authorization_accepted_at: ts,
  human_handoff_at: ts,
  continuity_source_profile_sha256: hash,
  source_stream_id: ascii(128),
  source_position: s(512),
  content_hash: hash
}

post_action_boundary = {
  schema_version: literal(github-control-post-action-boundary/0.1.0),
  open_request: external_record_ref,
  human_handoff_boundary: external_record_ref,
  interval_id: ascii(64),
  acquisition_session_id: ascii(64),
  attestor_supervisor_nonce: ascii(64),
  final_stage_21a_branch_protection_observation: record_ref,
  final_stage_21a_branch_rules_observation: record_ref,
  final_stage_21a_ruleset_summary_observation: record_ref,
  latest_final_observed_at: ts,
  post_action_completed_at: ts,
  continuity_source_profile_sha256: hash,
  source_stream_id: ascii(128),
  source_position: s(512),
  content_hash: hash
}
```

Each time equals or bounds the cited record's verified canonical timestamp;
operator-entered time is forbidden. The continuity profile freezes the source-
position grammar, comparison function, inclusive/exclusive semantics, and
proof that no relevant position can be omitted. The close request must cite
these exact objects and the same final observations as the post-action
boundary. The bundle must satisfy the total time order:

```text
open.created_at
  <= coverage_started_at
  <= readiness_sealed_at
  <= human_authorization_accepted_at
  <= human_handoff_at
  <= latest_final_observed_at
  <= post_action_completed_at
  <= coverage_completed_at
```

Its start position must compare at or before the readiness-boundary position;
the readiness position at or before the handoff position; the handoff position
at or before the post-action position; and the post-action position at or before
the end position. Every boundary must have the same stream ID, profile, target,
interval, session, and nonce through its cited open request and evidence chain.
An unequal binding, false inequality, incomparable position, or coverage gap is
`CONTINUITY_INCOMPLETE`.

Continuity requires an append-only, independently timestamped sequence of
control fingerprints or equivalent source events covering the full interval.
The separately approved continuity source profile and implementation manifest
must freeze at least one complete mechanism:

1. subscribed, durable GitHub audit or webhook events whose delivery,
   pagination, sequence, repository/account identity, and event coverage are
   positively proved; or
2. bounded periodic full snapshots whose maximum gap is frozen and whose source
   guarantees make an intervening change and restoration detectable.

Endpoint snapshots at the two interval boundaries alone are insufficient. A
mechanism that can miss a protection change and restoration is insufficient.
Polling without a documented completeness guarantee cannot yield
`controls_intact`.

The interval inventory covers changes to protection, applicable rulesets,
ruleset enforcement, bypass actors, actor roles, team membership, custom roles,
App/installation permissions and repository selection, deploy keys,
conversation policy, code-owner source, required checks, review policy,
force-push/deletion settings, and merge-method settings.

An observed change yields the corresponding `PROTECTION_CHANGED`,
`RULESET_CHANGED`, or `CAPABILITY_CHANGED` code even if the final state equals
the initial state. A gap, sequence ambiguity, delayed subscription, dropped
event, unavailable retention range, clock uncertainty, or unsupported event
class yields structural incompleteness. It cannot be reported as unchanged.

The profile must bind the exact GitHub plan, account and repository identity,
event classes, subscription or audit-log query, start boundary, delivery and
pagination behavior, retention, maximum delay, completeness proof, and
collector implementation hash. Audit-log silence is useful only where those
frozen guarantees prove that every relevant event would have appeared. If any
relevant control or capability event class is unavailable, undocumented,
delayed beyond the interval, or not provably complete, the action-interval
attestation is `indeterminate`.

Until such a profile is separately reviewed, Arthur-approved, and present in
the attestor's deployment-pinned trust store, an action-interval attestation must be
`indeterminate`. This protocol does not assume that every GitHub plan exposes
adequate audit, webhook, or polling history.

## 15. Canonical external evidence bundle

After successful collection, the external process seals exactly one
`github-control-attestation-source-bundle/0.1.0` object containing:

```text
schema_version: literal(github-control-attestation-source-bundle/0.1.0)
collection_protocol_sha256: hash
collector_implementation_manifest_sha256: hash
collector_implementation_authorization_sha256: hash
implementation_trust_store_sha256: hash
implementation_trust_store_authorization_sha256: hash
acquisition_supervisor_executable_sha256: hash
collector_normalizer_executable_sha256: hash
attestor_verifier_signer_executable_sha256: hash
pinned_rest_table_sha256: hash
pinned_graphql_document_sha256: hash
continuity_source_profile_sha256: hash?
acquisition_session_id: ascii(64)
attestor_supervisor_nonce: ascii(64)
collection_request: external_record_ref
open_request: external_record_ref?
readiness_boundary: external_record_ref?
human_handoff_boundary: external_record_ref?
post_action_boundary: external_record_ref?
purpose: enum(readiness,action_interval)
target_sha256: hash
credential_lease_evidence_sha256: hash
transmission_attempt_inventory_sha256: hash
raw_response_evidence_inventory_sha256: hash
stage_21a_evidence_inventory_sha256: hash
source_envelopes: [external_record_ref,96]
repository_identity_sha256: hash
ruleset_inventory_sha256: hash
effective_policy_sha256: hash
conversation_inventory_sha256: hash
actor_capability_inventory_sha256: hash
continuity_inventory_sha256: hash?
coverage_started_at: ts
coverage_completed_at: ts
coverage_start_position: s(512)?
coverage_end_position: s(512)?
logical_read_count: count
network_transmission_count: count
complete: bool
reason_codes: [ascii(64),32]
sealed_at: ts
content_hash: hash
```

For `readiness`, the open and three boundary references and two coverage
positions are null, and `collection_request` cites the readiness request. For
`action_interval`, all five are non-null; `open_request` cites the immutable
open request and `collection_request` cites the immutable close request; their
hashes and repeated fields must satisfy §5. `continuity_source_profile_sha256`
and `continuity_inventory_sha256` are non-null only for `action_interval`.
References are ordered by lifecycle and unique. The raw-response and Stage 21A inventory hashes bind sorted lists of
the exact immutable record references and content hashes independently read by
the attestor. The transmission-attempt inventory is the complete list of
attempt references sorted by logical-read number then transmission number; its
length equals `network_transmission_count`, and each response-bearing attempt
has exactly one matching raw-response reference. Other inventory hashes are hashes of closed canonical
projections, never arbitrary files or raw response text. The bundle ceiling is
`2 MiB`; each source envelope ceiling is `64 KiB`. Exceeding a ceiling is
failure, not truncation.

Every external object in this protocol uses this exact canonical byte
algorithm, which extends the frozen Stage 21A contract without relying on a
platform JSON default:

1. accept only Unicode scalar values already in NFC; reject invalid UTF-8,
   surrogates, a BOM, and any key or string whose NFC form differs;
2. permit only schema-declared objects, arrays, strings, booleans, null, and
   integers from `-9223372036854775808` through `9223372036854775807`; schema
   IDs remain positive and counts non-negative;
3. sort object keys by the unsigned lexicographic bytes of their unescaped UTF-8
   encoding; reject duplicate keys before parsing into a map;
4. emit strings in shortest UTF-8, escaping quotation mark and reverse solidus
   as `\"` and `\\`; emit backspace, horizontal tab, line feed, form feed, and
   carriage return as `\b`, `\t`, `\n`, `\f`, and `\r`; emit other U+0000–U+001F
   controls as lowercase `\u00xx`; do not escape solidus or non-ASCII scalars;
5. emit integers as base-ten ASCII with no plus sign or leading zero, with zero
   exactly `0` and a negative value as `-` followed by its nonzero magnitude;
6. emit booleans and null exactly as `true`, `false`, and `null`; preserve each
   array's protocol-defined order; use only comma and colon separators with no
   whitespace; and append no newline;
7. encode timestamps exactly as UTC RFC 3339 `YYYY-MM-DDTHH:MM:SSZ`, with valid
   calendar fields, second precision, and no leap second; and
8. compute a `hash` as `sha256:` plus 64 lowercase hexadecimal characters over
   the canonical object with its `content_hash` member omitted, then insert that
   value and canonicalize once more for storage.

Unknown or missing members, floats, non-finite values, alternate escapes,
overlong UTF-8, non-minimal integers, and semantically equal but byte-different
encodings are rejected. Implementations must pass shared byte fixtures across
Windows, macOS, and Linux before use.

Every object also uses immutable create, exclusive write, durable file flush,
parent-directory synchronization where supported, and readback verification.
Conflicting same-hash or same-path content is a storage failure.

The source bundle is not a CONCLAVE record family and cannot be placed in the
CONCLAVE Stage 21A/21B/21C record store. Its hash may appear among the signed
attestation's bounded `source_evidence_hashes`.

## 16. Result and reason reduction

The collection procedure returns exactly one process result:

- `complete` — every required source, identity, item, permission, time, and
  durability predicate is positively satisfied; or
- `incomplete` — one or more predicates is absent, unknown, ambiguous,
  conflicting, stale, over budget, or not durable.

Its closed collection reason-code domain is:

```text
SCHEMA_INVALID, REFERENCE_INVALID, IDENTITY_AMBIGUOUS,
CREDENTIAL_LEASE_INVALID, PERMISSION_INCOMPLETE, ENDPOINT_NOT_ALLOWED,
QUERY_NOT_ALLOWED, RESPONSE_INVALID, RESPONSE_OVERSIZED,
PAGINATION_INCOMPLETE, REQUEST_BUDGET_EXHAUSTED, RATE_LIMITED,
TIME_INVALID, STORAGE_INVALID, SOURCE_EVIDENCE_INCOMPLETE,
RULESET_INCOMPLETE, UNKNOWN_RULE, POLICY_INCOMPLETE,
CONVERSATION_INCOMPLETE, CODE_OWNER_INCOMPLETE,
LAST_PUSH_IDENTITY_INCOMPLETE, ACTOR_CAPABILITY_INCOMPLETE,
CONTINUITY_INCOMPLETE, EVIDENCE_CONFLICT, TARGET_DRIFT, REPLAY_DETECTED,
PROTECTION_CHANGED, RULESET_CHANGED, CAPABILITY_CHANGED,
BYPASS_PRESENT
```

Reason codes are sorted and unique. Every code except the final four denotes
structural incompleteness. Positive change or bypass evidence is complete
factual evidence but does not make the collection usable for
`controls_intact`; it maps to the exact Stage 21C attestation code. When any
structural code exists, the future CONCLAVE readiness outcome is
`indeterminate` even if change or bypass is also observed. The attestor may
sign an `indeterminate` attestation only when every mandatory frozen Stage 21C
field can be populated truthfully; otherwise it signs nothing and absence of a
usable attestation remains fail-closed.

The collector does not sign or choose the Stage 21C result. The attestor applies
this total one-to-one map; there is no context-selected alternative:

| Collection reason | Stage 21C attestation reason |
|---|---|
| `SCHEMA_INVALID` | `SCHEMA_INVALID` |
| `REFERENCE_INVALID` | `SOURCE_EVIDENCE_INCOMPLETE` |
| `IDENTITY_AMBIGUOUS` | `SOURCE_EVIDENCE_INCOMPLETE` |
| `CREDENTIAL_LEASE_INVALID` | `SOURCE_EVIDENCE_INCOMPLETE` |
| `PERMISSION_INCOMPLETE` | `SOURCE_EVIDENCE_INCOMPLETE` |
| `ENDPOINT_NOT_ALLOWED` | `SOURCE_EVIDENCE_INCOMPLETE` |
| `QUERY_NOT_ALLOWED` | `SOURCE_EVIDENCE_INCOMPLETE` |
| `RESPONSE_INVALID` | `SOURCE_EVIDENCE_INCOMPLETE` |
| `RESPONSE_OVERSIZED` | `SOURCE_EVIDENCE_INCOMPLETE` |
| `PAGINATION_INCOMPLETE` | `SOURCE_EVIDENCE_INCOMPLETE` |
| `REQUEST_BUDGET_EXHAUSTED` | `SOURCE_EVIDENCE_INCOMPLETE` |
| `RATE_LIMITED` | `SOURCE_EVIDENCE_INCOMPLETE` |
| `TIME_INVALID` | `TIME_INVALID` |
| `STORAGE_INVALID` | `SOURCE_EVIDENCE_INCOMPLETE` |
| `SOURCE_EVIDENCE_INCOMPLETE` | `SOURCE_EVIDENCE_INCOMPLETE` |
| `RULESET_INCOMPLETE` | `RULESET_INCOMPLETE` |
| `UNKNOWN_RULE` | `UNKNOWN_RULE` |
| `POLICY_INCOMPLETE` | `POLICY_INCOMPLETE` |
| `CONVERSATION_INCOMPLETE` | `CONVERSATION_INCOMPLETE` |
| `CODE_OWNER_INCOMPLETE` | `POLICY_INCOMPLETE` |
| `LAST_PUSH_IDENTITY_INCOMPLETE` | `POLICY_INCOMPLETE` |
| `ACTOR_CAPABILITY_INCOMPLETE` | `ACTOR_CAPABILITY_INCOMPLETE` |
| `CONTINUITY_INCOMPLETE` | `SOURCE_EVIDENCE_INCOMPLETE` |
| `EVIDENCE_CONFLICT` | `SOURCE_EVIDENCE_INCOMPLETE` |
| `TARGET_DRIFT` | `TARGET_MISMATCH` |
| `REPLAY_DETECTED` | `SOURCE_EVIDENCE_INCOMPLETE` |
| `PROTECTION_CHANGED` | `PROTECTION_CHANGED` |
| `RULESET_CHANGED` | `RULESET_CHANGED` |
| `CAPABILITY_CHANGED` | `CAPABILITY_CHANGED` |
| `BYPASS_PRESENT` | `BYPASS_PRESENT` |

The attestor independently adds `COLLECTION_PROTOCOL_MISMATCH`, `TRUST_INVALID`,
or `SIGNATURE_INVALID` only for the corresponding verified attestor-layer
failure. It sorts and deduplicates the mapped Stage 21C codes, then applies the
exact governing Stage 21C precedence: its first twelve structural codes yield
`indeterminate`; otherwise bypass yields `bypass_present`; otherwise a change
yields `controls_changed`; otherwise an empty list yields `controls_intact`.

No free-text code, warning-only bypass, best-effort success, partial success,
manual override, or operator-selected result is allowed.

## 17. Failure and cleanup

Before evidence verification, the attestor uses a fixed local append-only
replay registry outside CONCLAVE. Under one OS-enforced exclusive registry lock,
it computes six domain-separated key hashes for repository/purpose plus:

1. collection-request content hash;
2. open-request content hash or the literal `readiness`;
3. interval ID or the literal `readiness`;
4. acquisition-session ID;
5. supervisor nonce; and
6. source-bundle content hash.

For every key it exclusively creates this immutable claim record:

```text
schema_version: literal(github-control-attestor-replay-claim/0.1.0)
key_kind: enum(request,open_request,interval,session,nonce,bundle)
key_sha256: hash
repository_id: id
purpose: enum(readiness,action_interval)
collection_request_sha256: hash
open_request_sha256: hash?
interval_id: ascii(64)?
acquisition_session_id: ascii(64)
attestor_supervisor_nonce: ascii(64)
source_bundle_sha256: hash
claimed_at: ts
content_hash: hash
```

The registry lock is acquired before lookup and retained through exclusive
creation, durable flush, parent-directory synchronization, readback, and
release. If any key already exists, including byte-equal content, the entire
submission is rejected as `REPLAY_DETECTED`; replay is never idempotent success.
If a crash leaves only some claims, those tombstones remain and cause the same
fail-closed rejection. Claims are never deleted, replaced, or reused during the
governed retention period.

`claim_inventory_sha256` is the content hash of a closed object containing the
six claim `external_record_ref` values sorted by `key_kind` in the enumeration
order above. Missing, duplicate, reordered, or unequal claim content is
`STORAGE_INVALID`.

After terminal verification, the attestor appends exactly one terminal record:

```text
schema_version: literal(github-control-attestor-replay-terminal/0.1.0)
claim_inventory_sha256: hash
source_bundle_sha256: hash
outcome: enum(attested,rejected)
attestation_sha256: hash?
signature_sha256: hash?
reason_codes: [ascii(64),32]
completed_at: ts
content_hash: hash
```

For `attested`, both attestation and signature hashes are non-null and reasons
are empty. For `rejected`, both are null and reasons are nonempty. A second or
conflicting terminal is `STORAGE_INVALID` and cannot sign. The verifier checks
all six claims immediately before requesting its one-use signing handle. The
implementation manifest pins the registry schema, fixed root, lock mechanism,
and platform durability adapter; adversarial multiprocess and crash tests must
prove this exact invariant on Windows, macOS, and Linux.

Every parse, identity, permission, transport, TLS, DNS, proxy, redirect,
response, pagination, rate, size, time, semantic, conflict, storage, or cleanup
failure stops further reads except the minimum needed to close the credential
lease and preserve safe failure evidence.

On every normal, exceptional, cancellation, timeout, keyboard-interrupt, and
process-shutdown path, the mutable credential buffer is overwritten where the
runtime permits, references are dropped, transports are closed, and no signing
process is invoked. Erasure is best effort and is never overstated as physical
memory proof.

A crash before terminal durable source-bundle readback produces no complete
bundle and cannot be resumed. A crash after bundle durability but before
attestor validation leaves evidence only; it does not produce an attestation.
The attestor accepts only one terminal bundle for one request hash and rejects
conflicting or multiple current bundles.

No failure authorizes remediation, setting change, retry under broader
permissions, alternate credential, mutation, or human merge.

## 18. Privacy and retention

The minimum normalized record retains numeric/node identities, booleans,
counts, timestamps, closed enums, and hashes. It excludes:

- credentials, cookies, authorization headers, private or recovery keys;
- names, emails, logins except transiently where a fixed GitHub path requires
  one after numeric binding;
- PR titles/bodies, comments, review bodies, thread bodies, diff hunks, file
  contents, commit messages, check output, annotations, status descriptions,
  URLs, and arbitrary metadata; and
- organization, team, collaborator, or repository information unrelated to the
  exact target and bypass proof.

Raw source evidence is encrypted at rest, access logged, retained for a
separately governed period, and destroyed under a separately governed process.
The attestation remains verifiable from its normalized facts and hashes but
does not claim raw evidence remains available forever.

Diagnostics are single stable codes with safe hashes. Tests must prove secrets
and excluded content do not appear in logs, exceptions, source bundles,
attestations, wheels, CI artifacts, crash output, or temporary paths.

## 19. Required implementation and adversarial evidence

A later implementation requires separate authority and must demonstrate at
least:

1. exact frozen protocol-hash and collection-request validation;
2. a separate executable/package absent from the CONCLAVE runtime wheel;
3. closed GET/query tables and mechanical rejection of REST mutations,
   GraphQL mutations, aliases, introspection, caller URLs, redirects, proxies,
   custom roots, and generic transport escape;
4. independent credential-lease admission, cleanup, and no signing-key access;
5. complete repository and organization ruleset discovery, positive
   non-enterprise proof, and fail-closed rejection of enterprise or unknown
   enterprise scope until a protocol revision supplies its closed path;
6. exact include/exclude applicability and active-rule normalization;
7. complete bypass expansion across admins, roles, teams, Apps,
   installations, integrations, and deploy keys;
8. exact code-owner and last-push identity handling;
9. complete bounded review-thread pagination and zero-content retention;
10. action-interval change-and-restoration detection, with endpoint snapshots
    alone rejected;
11. deterministic source envelopes, inventories, bundles, hashes, ordering,
    and reason mapping;
12. stale, revoked, overbroad, wrong-repository, wrong-account, wrong-App,
    wrong-installation, and role-collision credential/identity failures;
13. partial pages, cursor cycles, count changes, duplicate IDs, unknown fields,
    unknown rules, omitted bypass actors, `404` ambiguity, rate exhaustion,
    clock rollback, oversize bodies, decompression bombs, malformed Unicode,
    duplicate JSON names, and conflicting evidence;
14. repository-level evidence that appears safe while an omitted organization
    or enterprise rule supplies bypass;
15. before/after snapshots that match while an interval event proves weakening
    and restoration;
16. storage failure, partial write, same-path conflict, traversal, symlink,
    junction/reparse, restart, and replay refusal;
17. fixture and loopback tests proving zero external network and zero mutation;
18. installed-package inventories and static scans proving no hidden mutation
    endpoint, CONCLAVE transport linkage, credential export, or private-key
    path;
19. secret scanning across source, tests, logs, exceptions, evidence, packages,
    and CI artifacts; and
20. Windows/Python 3.12, Ubuntu/Python 3.12 and 3.13, and macOS/Python 3.12
    passing without required security skip or xfail.

No live GitHub exercise is required for implementation acceptance. A later
live exercise must use an explicitly named disposable repository and separately
authorized credential, collection, signing, retention, and cleanup plan.

## 20. Implementation sequence after separate authority

If this protocol is reviewed and frozen, the bounded order is:

1. freeze this exact collection protocol and its closed schemas, endpoint
   table, query document, and implementation-manifest contract;
2. review and freeze an offline two-key ceremony plan;
3. under separate authority, generate distinct control-attestor and human-
   authorizer Ed25519 keys outside CONCLAVE, retaining only their public facts
   in the governed workspace;
4. construct, review, approve, and build-pin the two exact Arthur-issued Stage
   21C trust authorizations, including this protocol's frozen SHA-256 in the
   control-attestor authorization;
5. separately authorize and build the external collector and attestor verifier
   with fixture-only closed transports, then independently review and approve
   their exact implementation manifest and authorization binding source
   commit/tree, build recipe, dependency lock, supervisor, normalizer and
   verifier executable/package hashes, REST table, GraphQL document, schemas,
   platform, and derived request budget;
6. create, review, approve, and separately deploy the exact immutable
   implementation trust store, pinning its hash in the governed launcher and
   key-provider policy without changing any executable/package hash;
7. only after the Stage 21C trust prerequisite is satisfied, separately
   authorize Stage 21C runtime implementation and build-pin its two Stage 21C
   trust authorizations; CONCLAVE does not load the external implementation
   trust store;
8. implement any external credential provider and live transports only after a
   still further explicit authorization;
9. generate cross-platform and installed-package evidence; and
10. obtain a fresh independent implementation Council review.

Key generation can wait until this collection protocol and the ceremony plan
are frozen. It cannot wait until after Stage 21C runtime implementation because
the governing Stage 21C §4.3 requires the exact Arthur-issued trust
authorization to be preserved and build-pinned before implementation. This
protocol never binds a particular key; the later trust authorization binds the
key to this protocol's frozen hash.

## 21. Council review questions

Each reviewer must independently bind the exact candidate SHA-256 and Git blob
and return `PASS_EXACT_DRAFT` or `FAIL_EXACT_DRAFT`:

1. **Governance:** Is the collector strictly subordinate, factual,
   non-authorizing, and outside CONCLAVE's operation and credential boundary?
2. **GitHub correctness:** Does it positively cover repository, organization,
   enterprise, branch-protection, ruleset, conversation, code-owner,
   last-push, and actor-capability semantics without treating omission as
   absence?
3. **Security:** Are high-visibility credential risk, role separation,
   transport closure, mutation rejection, secrets, privacy, rate, size, time,
   storage, replay, and cleanup fail-closed?
4. **Continuity:** Can the action interval detect weakening and restoration,
   and does the protocol reject endpoint snapshots as sufficient proof?
5. **Evidence and operability:** Are the schemas, bounds, hashes, ordering,
   failure codes, test requirements, and cross-platform acceptance criteria
   implementable without weakening frozen Stage 21C?

Any byte change after review invalidates every verdict and requires a fresh 5/5
exact-draft Council review.

## 22. Official factual references

The following GitHub documentation was consulted on 15 September 2026. These
references describe external platform behavior and grant no authority:

- repository rules and inherited rulesets:
  `https://docs.github.com/en/rest/repos/rules`;
- organization rulesets, permission requirements, conditions, bypass actors,
  and rule history:
  `https://docs.github.com/en/rest/orgs/rules`;
- branch-protection fields and restrictions:
  `https://docs.github.com/en/rest/branches/branch-protection`;
- protected-branch review, code-owner, last-push, conversation, strict-check,
  force-push, and deletion behavior:
  `https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches`;
- GitHub GraphQL schema and pull-request objects:
  `https://docs.github.com/en/graphql/reference`;
- REST pagination:
  `https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api`;
- REST rate limits:
  `https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api`;
- GitHub App permission selection:
  `https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app`; and
- CODEOWNERS locations, base-branch operation, syntax, owner eligibility, and
  precedence:
  `https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners`;
- collaborator permission and affiliation behavior:
  `https://docs.github.com/en/rest/collaborators/collaborators`;
- durable numeric user-ID lookup:
  `https://docs.github.com/en/rest/users/users#get-a-user-using-their-id`;
- team membership and inherited child-team membership:
  `https://docs.github.com/en/rest/teams/members`;
- custom repository roles:
  `https://docs.github.com/en/rest/orgs/custom-roles`;
- custom organization roles and assignments:
  `https://docs.github.com/en/rest/orgs/organization-roles`; and
- organization audit log and streaming:
  `https://docs.github.com/en/organizations/keeping-your-organization-secure/managing-security-settings-for-your-organization/managing-the-audit-log-for-your-organization`; and
- organization audit event fields:
  `https://docs.github.com/en/organizations/keeping-your-organization-secure/managing-security-settings-for-your-organization/audit-log-events-for-your-organization`.

API availability, fields, permissions, plans, and retention are external facts
that may change. The implementation-manifest review must reverify them from
official documentation and fixtures. Any required endpoint, query, or semantic
change requires a protocol revision; a manifest cannot expand this closed
protocol.

## 23. Current disposition

This document is a local protocol candidate under drafting authority only. It
has not been reviewed, frozen, committed, pushed, merged, implemented, or used.
No key has been generated; no credential, private key, token, cookie, or live
GitHub evidence has been accessed; no GitHub setting or repository state has
been changed; and CONCLAVE runtime and tests have not been changed by this
drafting action.

The next permitted action is local validation and preparation for an exact-draft
Council review. Council review, remediation, freeze, commit, push, key ceremony,
trust authorization, implementation, live collection, signing, or any GitHub
operation requires the authority applicable to that step.
