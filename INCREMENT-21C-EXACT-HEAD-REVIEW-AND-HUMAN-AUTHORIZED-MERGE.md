# CONCLAVE Stage 21C — Exact-Head Review and Human-Authorized Merge Protocol

## Status

`REMEDIATED DRAFT / NOT FROZEN / NOT IMPLEMENTED / NO LIVE AUTHORITY`

Drafted: 2026-09-10
Remediated: 2026-09-11

This exact draft supersedes, but does not erase, the rejected candidates bound
to SHA-256
`5cce5525659cccea9be2d0c8ee180a3609c17cf72fa7f1bcde120b2173ccd6e1` and
`f306134fa93a61b14393579f018a348c7958fe445de36e6bdd90d934d056bafd`,
`cc865b616dcda1edaa0dbb689ed16292b47d21f44aa67748e03dfcd11d946bec`,
`95fa98ce569f1f0553c3d0d75ef9804029bdf3832bc2185f25862de1b3b3d3c1`,
  `d82af781441b916855861322c5c8143d70abf3211c21f823d31866046eb954a1`,
  and `2bded70672d5ceb8f671f5bce46692670a53d73473f2cb3f1af6635cf289b515`.
Council Reviews 0001 through 0006 preserve their respective findings. This
replacement has no Council verdict until reviewed as a new exact object.

Nothing in this document authorizes implementation, credential access, GitHub
App creation or installation, a live request, merge, administrator exception,
protection change, deployment, production use, KOS or IDM change, signing,
identity allocation, or membership activation.

## 0. Governing baseline

This draft is subordinate to the frozen Increment 21 master protocol:

- document: `INCREMENT-21-GITHUB-REPOSITORY-AND-PR-ADAPTER.md`;
- SHA-256:
  `89a05211a4323db2e79d2854952b24ce033c71f357430c7ac839457ff0878d75`;
- Git blob: `83d8fb2cabb9d343b6a8d089d920d25dcd8c5728`; and
- governed `main` entry baseline:
  `dda5961fa4aa0c67acafac2de230e9ce9313a03e`.

Stage 21A and Stage 21B remain byte-for-byte governed inputs. Stage 21C does
not widen, amend, reinterpret, or replace their schemas. Every capability that
Stage 21A cannot express is represented by an additive Stage 21C family and a
new schema version in this protocol.

## 1. Objective and completion boundary

After a future separate implementation authorization, Stage 21C may:

1. produce immutable factual readiness evidence for one exact Stage-21B-
   published PR head; and
2. only after a new authenticated exact human authorization, make at most one
   synchronous normal-merge request and reconcile the factual outcome.

`READY` is evidence only. It never grants authority and cannot be promoted to
authority by a model, caller, GitHub state, Council score, administrator,
elapsed time, or default.

Implementation completion requires deterministic fixture and source-only
loopback evidence, isolated installed-wheel evidence, four-platform CI, and
exact-head Council review. It does not activate live use. A later live exercise
requires a new exact authorization and a dedicated disposable conformance
repository satisfying §6.

## 2. Explicit exclusions

Stage 21C contains no capability to:

- create, install, reconfigure, or uninstall a GitHub App;
- generate or store an App private key, mint an App JWT, or mint an
  installation token;
- use a personal, OAuth, user-to-server, Actions, SSH, browser, cookie, or
  ambient Git credential;
- approve, request changes, dismiss, resolve, edit, close, reopen, label,
  assign, update, enqueue, auto-merge, or update a PR branch;
- create, update, or delete a ref, tag, commit, tree, blob, workflow, ruleset,
  protection rule, setting, collaborator, or team;
- lower, bypass, suspend, or create an administrator exception to protection;
- use a merge queue, asynchronous merge, squash, rebase, default merge method,
  direct protected-branch write, force push, or history rewrite;
- retry a merge mutation automatically;
- operate on KOS, IDM, CONCLAVE `main`, a client repository, or a production
  repository; or
- infer KOS authority, IDM identity, approval, adoption, membership,
  deployment, truth, or production readiness.

If ordinary protection blocks a merge, CONCLAVE records and stops. Stage 21C
has no exception or repair path.

## 3. Closed notation and common invariant

The following notation is normative:

| Symbol | Exact contract |
| --- | --- |
| `uuid7` | lowercase canonical RFC 9562 UUIDv7 string |
| `id` | JSON integer 1 through `2^63-1`, never boolean |
| `node` | NFC UTF-8 string 1–128 bytes, controls and NUL forbidden |
| `safe(N)` | NFC UTF-8 string 1–N bytes, controls and NUL forbidden |
| `ascii(N)` | printable ASCII string 1–N bytes matching the field's closed pattern |
| `ts` | second-precision UTC RFC 3339 with literal `Z`, no leap second |
| `oid` | lowercase hex of the governed repository object format: 40 for SHA-1 or 64 for SHA-256 |
| `hash` | literal `sha256:` plus 64 lowercase hex characters |
| `record_ref` | closed object `{reference:safe(512),content_hash:hash}` using a workspace-relative POSIX path without traversal |
| `permission_map` | exact keys `metadata`, `contents`, `pull_requests`, `checks`, `statuses`, `administration`; each exact `none`, `read`, or where explicitly permitted `write` |

Every durable Stage 21C record has exactly these invariant fields plus exactly
the family fields listed later:

| Field | Exact contract |
| --- | --- |
| `profile` | exact family-name literal without version suffix |
| `schema_version` | exact family/version literal |
| `record_id` | `uuid7`, except the deterministic target claim ID in §13 |
| `created_at` | `ts` |
| `authority_effect` | family literal defined below |
| `approval_effect` | family literal defined below |
| `decision_effect` | always `none` |
| `membership_effect` | always `none` |
| `production_use_allowed` | always `false` |
| `content_hash` | canonical `hash` |

Unknown or duplicate fields, implicit nulls, floats, non-finite numbers,
non-NFC strings, duplicate collection keys, invalid UTF-8, or non-canonical
timestamps fail before persistence. Optional fields are named explicitly and
use exact JSON null; omission and null are not interchangeable.

Canonical JSON uses sorted keys, compact separators, UTF-8, and no non-finite
values. `content_hash` is computed with only `content_hash` omitted. Lists keep
protocol order unless declared sorted unique. Records are immutable and
insert-once. Equal bytes at an existing content-addressed path are idempotent;
unequal bytes are retained as a conflict and block. Every reference includes
both path and exact content hash.

Hash-safe filenames contain a content digest, never a repository name, login,
ref, URL, selector, lease ID, or secret. The deterministic target-claim path in
§13 is the only exception and contains only a domain-separated digest.

## 4. Additive Stage 21C API profile

### 4.1 `github-21c-api-profile/0.1.0`

This immutable profile references, but does not modify, the Stage 21A API
profile. Its family fields are exactly:

| Field | Type and rule |
| --- | --- |
| `api_profile_id` | `ascii(64)` |
| `stage_21a_api_profile` | `record_ref` |
| `origin` | literal `https://api.github.com` |
| `api_version` | literal `2026-03-10` |
| `rest_accept` | literal `application/vnd.github+json` |
| `graphql_content_type` | literal `application/json` |
| `user_agent` | literal `conclave-github-adapter/21c` |
| `tls_policy` | literal `system-ca-hostname-tls12-plus` |
| `redirect_policy` | literal `deny` |
| `proxy_policy` | literal `ignore-environment-and-deny` |
| `connect_timeout_seconds` | literal `5` |
| `read_timeout_seconds` | literal `20` |
| `operation_timeout_seconds` | literal `60` |
| `maximum_request_header_bytes` | literal `16384` |
| `maximum_response_header_bytes` | literal `32768` |
| `maximum_response_body_bytes_per_page` | literal `2097152` |
| `maximum_total_response_body_bytes_per_logical_operation` | literal `8388608` |
| `maximum_json_depth` | literal `16` |
| `maximum_json_nodes_per_page` | literal `10000` |
| `maximum_object_keys` | literal `256` |
| `maximum_pages_per_pass` | literal `10` |
| `maximum_items_per_collection` | literal `1000` |
| `maximum_read_retry_transmissions` | literal `0` |
| `maximum_mutation_retry_transmissions` | literal `0` |
| `endpoint_table_version` | literal `github-21c-endpoints/0.1.0` |
| `projection_version` | literal `github-21c-projections/0.1.0` |
| `graphql_query_sha256` | exact hash from §10 without `sha256:` prefix |
| `authority_effect` | literal `none` |
| `approval_effect` | literal `none` |

No redirect, compression, ambient proxy, userinfo, alternate origin, direct
IP, arbitrary header, or caller URL is accepted. REST sends only `Accept`,
`Authorization`, `X-GitHub-Api-Version`, and `User-Agent`. GraphQL additionally
sends the fixed `Content-Type`. The HTTP library may add only protocol-required
host and framing headers.

### 4.2 `github-21c-permission-policy/0.1.0`

Family fields are `policy_id:ascii(64)`, `api_profile:record_ref`, the exact
sorted endpoint-to-permission rows in §9, and `authority_effect:none`,
`approval_effect:none`. The stage ceiling is Metadata read, Contents write,
Pull requests read, Checks read, Statuses read, and Administration read. The
ceiling is not a reusable token envelope; every operation must equal its exact
narrower row. Extra permission, including extra read access, blocks before
network I/O.

## 5. Governed trust root and signer profiles

### 5.1 External trust-root pin

Before any Stage 21C operation, the site-local governance bootstrap must pin
one exact `github-21c-trust-policy/0.1.0` content hash under the non-caller-
controlled key `workspace.governance.github_21c_trust_policy_hash`. Task
packets, prompts, CLI flags, environment variables, repository files, provider
text, and network responses cannot set or replace this pin.

Establishing or rotating the pin is a separate human-governance operation
outside Stage 21C. Rotation creates a new policy and invalidates every
readiness, attestation, authorization, lease, and attempt bound to the old
hash. Missing, conflicting, runtime-discovered, or mutable pins block.

### 5.2 `github-21c-trust-policy/0.1.0`

Exact family fields:

| Field | Type and rule |
| --- | --- |
| `policy_id` | `ascii(64)` |
| `repository_profile` | exact Stage 21A `record_ref` |
| `repository_id` | `id` |
| `human_authority_key` | `record_ref` |
| `human_authority_key_id` | `ascii(128)` |
| `human_authority_key_fingerprint` | `hash` over exactly 32 decoded key bytes |
| `independent_review_key` | `record_ref` |
| `independent_review_key_id` | `ascii(128)` |
| `independent_review_key_fingerprint` | `hash` |
| `control_attestor_key` | `record_ref` |
| `control_attestor_key_id` | `ascii(128)` |
| `control_attestor_key_fingerprint` | `hash` |
| `required_distinct_key_count` | literal `3` |
| `valid_from` | `ts` |
| `valid_until` | `ts` |
| `status` | literal `active` |
| `rotation_mode` | literal `new_policy_and_invalidate_dependents` |
| `authority_effect` | literal `none` |
| `approval_effect` | literal `none` |

The three key IDs, 32-byte public keys, fingerprints, principals, and roles
must be pairwise distinct. The policy cannot authenticate itself; its trust
comes only from the pre-existing external pin.

### 5.3 Signer-key profiles

The three exact families are:

- `github-human-merge-authority-key/0.1.0`, role
  `human_merge_authority`;
- `github-independent-review-key/0.1.0`, role
  `independent_exact_head_reviewer`; and
- `github-control-attestor-key/0.1.0`, role
  `ruleset_protection_and_head_provenance_attestor`.

Each contains exactly: principal ID `ascii(128)`, role literal, key ID
`ascii(128)`, `algorithm:"ed25519"`, unpadded base64url public key decoding to
exactly 32 bytes, public-key fingerprint `hash`, one-element sorted repository
ID scope, `valid_from:ts`, `valid_until:ts`, `status:"active"`,
`authority_effect:none`, and `approval_effect:none`.

For every signed family, the unsigned projection omits exactly `signature` and
`content_hash` and retains all other fields. The signature is unpadded
base64url Ed25519 over:

`ASCII_DOMAIN || 0x00 || canonical_unsigned_record_bytes`

The durable content hash is then computed over the signed object with only
`content_hash` omitted, so it commits to the signature. Wrong domain, key,
length, encoding, fingerprint, policy, repository, principal, role, time, or
signature blocks. Private keys remain outside CONCLAVE.

## 6. Disposable live-exercise boundary

### 6.1 `github-21c-live-exercise-capability/0.1.0`

This separately governed, human-signed overlay leaves the Stage 21A
`live_use_allowed:false` profile unchanged. It contains exactly:

- capability ID `uuid7`;
- trust policy, Stage 21A repository profile, Stage 21C API profile, and
  permission policy `record_ref`s;
- repository/account/App/installation numeric IDs;
- repository class literal `dedicated_disposable_conformance`;
- exact PR number, PR node ID, base ref/commit, head ref/commit;
- prohibited target classes exactly sorted as `client`, `conclave_main`,
  `idm`, `kos`, `production`;
- known prohibited repository numeric IDs as a sorted unique non-empty list;
- assertions `target_is_disposable:true`, `target_is_production:false`, and
  `target_is_known_prohibited_repository:false`;
- allowed operation keys exactly the sorted Stage 21C keys in §9;
- validity window of at most 15 minutes;
- maximum logical operations `38`, maximum transmissions `162`, maximum merge
  transmissions `1`, and mutation retries `0`;
- `network_use_mode:"disposable_conformance_only"`;
- `authority_effect:"github_21c_capability_boundary_only"`;
- `approval_effect:"none"`; and
- human key ID, signature domain
  `CONCLAVE-GITHUB-21C-LIVE-CAPABILITY-V1`, and signature.

The external trust-root pin must already trust the signing profile. The
capability is necessary but not sufficient: assessment and merge
authorizations remain separate. A KOS, IDM, CONCLAVE-main, client, production,
unknown-class, or unclassified target fails regardless of signature. No live
target is authorized or created by this protocol draft.

## 7. External factual evidence

### 7.1 `github-head-provenance-attestation/0.1.0`

Stage 21C v0.1 accepts only an exact PR produced by Stage 21B whose head ref and
commit have never changed since publication. The control attestor signs this
closed record under domain
`CONCLAVE-GITHUB-HEAD-PROVENANCE-ATTESTATION-V1`.

Exact fields are: trust policy and control-key references; Stage 21B
publication receipt reference/hash; repository/profile/account/App/
installation IDs; PR numeric/node IDs; base and head refs/OIDs; publication
actor numeric ID/type; latest head-pusher numeric ID/type; complete ref-event
and audit-evidence hash; observation interval; assertion
`head_never_changed_since_publication:true`; expiry at most five minutes after
observation; `authority_effect:none`; `approval_effect:none`; key ID; and
signature.

Missing complete provenance, any ref update even if later restored to the same
OID, or mismatch with the Stage 21B receipt blocks. This attestation is factual
and cannot authorize merge.

### 7.2 `github-independent-exact-head-review/0.1.0`

Signed by the pinned independent-review key under domain
`CONCLAVE-GITHUB-INDEPENDENT-EXACT-HEAD-REVIEW-V1`, its exact family fields are:

- trust policy/key and Stage 21B publication receipt `record_ref`s;
- reviewer principal, GitHub numeric account ID/type literal `User`;
- repository/profile/account IDs and PR numeric/node IDs;
- PR-author and latest-head-pusher numeric IDs;
- exact base/head refs and OIDs;
- reviewed tree OID and retained review-evidence hash;
- procedure ID/version;
- verdict `PASS_EXACT_HEAD` or `FAIL_EXACT_HEAD`;
- assertions reviewer differs from PR author, latest head pusher, human merge
  authorizer, control attestor, App, installation, and acting account;
- matching GitHub review ID;
- creation and expiry, no more than 24 hours apart;
- `authority_effect:none`;
- `approval_effect:"independent_exact_head_evidence_only"`;
- key ID and signature.

Only `PASS_EXACT_HEAD` can satisfy readiness. It becomes stale immediately on
head, base, protection, applicable ruleset, required-check, conversation, or
referenced evidence change. The matching GitHub review must be an exact-head
human `APPROVED` review and remain the reviewer's latest effective state.

### 7.3 `github-ruleset-no-bypass-attestation/0.1.0`

Signed by the pinned control-attestor key under domain
`CONCLAVE-GITHUB-RULESET-NO-BYPASS-ATTESTATION-V1`, this exact record contains:

- trust policy/key, repository/API profiles, and live capability `record_ref`s;
- repository/profile/account/App/installation/acting-account IDs;
- exact base ref/commit and head commit;
- complete retained raw-evidence hashes and source API versions;
- every applicable repository and organization ruleset, sorted by source type,
  source ID, ruleset ID, and target, with source, target, enforcement, version
  or update marker, condition hash, rule-type/parameter hashes, and complete
  bypass actors including explicit empty sets;
- complete legacy branch-protection projection including required checks,
  strictness, required review count, stale/code-owner/last-push flags,
  conversation resolution, administrator enforcement, restrictions,
  `bypass_pull_request_allowances` user/team/App IDs, signatures, linear
  history, force-push, deletion, creation, lock, and fork-sync state;
- complete effective administrative-actor and bypass-path projection;
- normalized effective requirements for the exact base;
- assertions that inheritance, targeting, conditions, rules, legacy bypass,
  administrator roles, and bypass actors are complete;
- assertions that the App, installation, acting account, credential provider,
  and publication actor are absent from every bypass path;
- observation start/end and expiry at most five minutes after end;
- `authority_effect:none`, `approval_effect:none`, key ID, and signature.

Omission is never an empty set. Unknown active rules, hidden organization
coverage, incomplete legacy bypass data, disabled administrator enforcement
for an administrative acting identity, or any acting-role bypass blocks.
Administration-read may corroborate this record but cannot replace its
independent completeness evidence. CONCLAVE receives no Administration-write.

### 7.4 `github-protection-freeze-lease/0.1.0`

The pinned control attestor signs one short-lived operational lease under
domain `CONCLAVE-GITHUB-PROTECTION-FREEZE-LEASE-V1`. Exact fields are trust
policy/key, no-bypass attestation, repository/account/PR/base/head identities,
complete administrative-writer-set hash, external serialization mechanism
ID/version, exclusive lease ID, acquired/expiry times no more than five minutes
apart, `protection_changes_serialized:true`,
`ruleset_changes_serialized:true`, `bypass_changes_serialized:true`,
`authority_effect:none`, `approval_effect:none`, key ID, and signature.

The lease asserts factual external control-plane serialization; it cannot
authorize merge. If the site cannot supply and maintain this lease through the
merge response, Stage 21C blocks before mutation. Any observed control change
invalidates it and triggers incident classification.

After the merge response or transport failure, the same pinned attestor must
issue `github-protection-freeze-closeout/0.1.0` under domain
`CONCLAVE-GITHUB-PROTECTION-FREEZE-CLOSEOUT-V1`. Its exact fields are the lease
and pre-mutation no-bypass references; repository/PR/base/head identities;
post-response protection, ruleset, legacy-bypass, and administrative-writer
hashes; closeout time; lease-held-through-response boolean; protection/ruleset/
bypass changed booleans; external serialization release time; complete true;
`authority_effect:none`; `approval_effect:none`; key ID; and signature. Missing
closeout evidence prevents confirmed success; a changed boolean produces the
control-drift terminal outcome.

## 8. Additive operation record families

Stage 21C defines additive versions because frozen Stage 21A is Stage-21A,
GET, and read-only constrained.

### 8.1 `github-operation-authorization/0.2.0`

Exact family fields are authorization ID `uuid7`; parent authority variant
`assessment`, `merge`, or `reconciliation`; parent signed-record `record_ref`; trust policy,
capability, repository, API, and permission-policy references; repository/
account/App/installation IDs; `stage:"21C"`; mode `read_only` or `mutation`;
one operation key from §9; exact path/query maps; request-material variant
`none`, `single_exact_body`, or `graphql_cursor_template`; exact body hash and
byte count, exact nulls for `none`, or fixed query/template hash and maximum
body bytes for the GraphQL variant; purpose `safe(512)`; authorized human
principal; issued, not-before, and expiry times; maximum logical operations
`1`; exact maximum transmissions from §9;
`authority_effect:"github_21c_exact_operation_only"`; and
`approval_effect:none`.

An assessment parent permits only readiness reads. A merge parent permits only
the exact final-revalidation, merge, and proof operations enumerated in its
plan. A reconciliation parent permits only the exact read keys and ceilings in
§16.4. The child cannot widen its parent.

### 8.2 `github-operation-intent/0.2.0`

Exact family fields are intent ID `uuid7`; operation authorization, trust
policy, capability, repository/API/permission profiles as `record_ref`s;
repository/account/App/installation IDs; `stage:"21C"`; exact operation key,
HTTP method, path/query maps, the authorization's exact request-material
variant and values; exact permission map; page/item/body/header/time limits;
read/mutation retry ceiling literal zero; maximum transmissions;
deterministic `attempt_id`; creation/expiry; maximum credential resolutions
`1`; `authority_effect:none`; and `approval_effect:none`.

For `review_threads.graphql`, the cursor-template projection is exactly the
fixed query, operation name, profile-derived owner/name/PR number, cursor type
and maximum bytes, canonical JSON rules, and a typed cursor placeholder. It is
not a request body and cannot be transmitted. Every actual page body is bound
before transmission by §8.6. All other body-bearing operations use
`single_exact_body`.

The attempt ID is SHA-256 of domain
`CONCLAVE-GITHUB-OPERATION-ATTEMPT-V2`, zero byte, and canonical JSON of every
selector, reference hash, request-material hash, permission, limit, and expiry
field.

### 8.3 `github-operation-attempt-claim/0.2.0`

Before credential resolution for each logical operation, exclusive-create one
immutable claim at the deterministic attempt-digest path. Exact fields are
attempt ID, intent/authorization/profile references, repository/account/App/
installation IDs, operation key, claim/expiry times, `state:"claimed"`,
optional merge-attempt and permanent-target-claim references that are required
only for `merge.put`, `authority_effect:none`, and `approval_effect:none`. It
contains no lease, admission, response, result, or future reference. Existing
equal or unequal paths block.

### 8.4 Credential lease receipt and evidence `0.2.0`

The transient receipt and durable
`github-credential-lease-evidence/0.2.0` retain the Stage 21A authentication,
nonce, token-instance commitment, freshness, App/installation/repository/API,
single-resolution, and secret-exclusion rules. The additive version permits
the exact Stage 21C permission maps, binds the operation authorization/intent/
claim and target claim where applicable, and adds `stage:"21C"` and operation
key. Durable evidence contains no token or tag. Its authority and approval
effects are `none`.

### 8.5 `github-observation/0.2.0`

Exact fields are observation ID; authorization/intent/claim/lease and all
profile references; repository/account/App/installation IDs; operation key;
request projection hash; accepted HTTP status; response projection kind/hash;
complete and pagination-complete booleans; pass ordinal where applicable;
item/page/transmission counts; ordered GraphQL page-result references when
applicable; stable-state projection hash separate from the ordered rate-fact
hash; bounded `core` or `graphql` rate projection;
observed start/end; sorted reason codes; `authority_effect:none`;
`approval_effect:none`; and content hash. Raw bodies, headers, cursors, URLs,
logins, emails, messages, and secrets are never durable.

### 8.6 GraphQL per-page admission and result

Each page of `review_threads.graphql` uses two new immutable records without
creating a new logical operation, credential resolution, or retry.

`github-graphql-page-admission/0.1.0` is durably written before the page send.
Its exact family fields are operation authorization/intent/attempt-claim/lease
and profile references; repository and PR numeric/node IDs; pass ordinal `1`
or `2`; page ordinal `1..10`; prior page-result reference or exact null only
for page one; prior response-projection hash or exact null only for page one;
prior returned-cursor hash or exact null only for page one; fixed query and
cursor-template hashes; canonical actual request-body hash and byte count;
transmission count before exact `N-1` and after exact `N` for page ordinal
`N`; rate budget before admission;
`state:"page_dispatch_admitted_not_confirmed"`; `retry_allowed:false`;
`authority_effect:none`; and `approval_effect:none`. It contains no raw cursor,
response, or future reference.

The production encoder constructs the actual body only from the fixed template
and the transport-held cursor whose hash equals the preceding result. Before
send it reserializes canonically, verifies the admission body hash/length, and
sends those exact bytes. Page one requires cursor null. Page `N>1` requires
page `N-1` with `hasNextPage:true`; a skipped, repeated, substituted, or
cross-pass cursor blocks before admission.

`github-graphql-page-result/0.1.0` is written only after one complete accepted
page response. Its exact family fields are page admission and predecessor page
result reference, which is exact null iff page ordinal is one and otherwise
must equal the admission's preceding page result; pass/page ordinals; canonical request-body hash; accepted
status and media type; raw-response commitment; normalized stable-state page
projection hash; page item count and sorted thread tuples; `hasNextPage`;
returned-cursor hash or exact null under §10; response-projection hash; exact
GraphQL cost/remaining/reset rate projection; transmission count `1`;
completion time; `authority_effect:none`; and `approval_effect:none`. Raw
cursors and bodies are never durable. The final observation binds the ordered
non-empty page-result hash list and independently binds the stable-state and
ordered rate-fact aggregates.

### 8.7 Interrupted read-operation inventory

`github-read-prefix-inventory/0.1.0` is an immutable local-only record for a
read chain that did not produce a complete observation. Exact family fields
are governing profile/capability/parent-authorization references; phase from
`initial_assessment`, `final_revalidation`, `post_mutation_proof`, or
`later_reconciliation`; operation key and deterministic attempt ID; exact
authorization and intent references; lifecycle variant; claim, lease,
GraphQL-page, and observation references under the union below; deterministic
paths with state and safe byte commitments; inventory time;
`authority_effect:none`; and `approval_effect:none`.

The lifecycle variant is exactly one of:

- `authorization_only`: intent through observation exact null;
- `intent_only`: claim through observation exact null;
- `claim_present`: claim required, later fields null;
- `lease_present`: claim and lease required, later record references null. For
  a GraphQL operation it is the sole variant only when zero complete page pairs
  exist and every deterministic page-admission and page-result path for
  ordinals 1 through 10 is `absent`;
- `graphql_pages_incomplete`: claim and lease required; the longest ordered
  chain-valid prefix of zero through ten complete page admission/result pairs;
  observation null; and an ordered fixed suffix of terminal path-state tuples
  for every remaining ordinal through 10. Each suffix tuple independently
  records admission and result path state from `valid_present`,
  `invalid_or_partial_present`, or `absent`, producing nine observable pairs
  per ordinal. A valid result beside a non-valid admission is retained as an
  artifact but never accepted as a complete pair. If both artifacts are valid
  but their ordinal, predecessor, request-body, or cross-reference binding
  fails, the tuple states `chain_valid:false` with the exact closed mismatch
  reason; it and every later tuple remain outside the valid prefix. Every non-
  valid path has no `record_ref` and follows the byte-count/hash rules below.
  With ten valid pairs, page 10 must have `hasNextPage:true`, the suffix is
  empty, reason is `GRAPHQL_PAGE_LIMIT_CONTINUATION`, and page 11 admission is
  forbidden. With fewer than ten valid pairs: when the prefix is non-empty and
  its final result has `hasNextPage:true`, an all-absent suffix is permitted as
  an interrupted continuation; when the final result has
  `hasNextPage:false`, at least one suffix path must be non-absent and reason is
  `GRAPHQL_PAGE_CHAIN_INVALID`; and when the prefix is empty, at least one of
  the twenty page-path states must be non-absent, because the all-absent case
  belongs only to `lease_present`. No suffix artifact authorizes another
  transmission or permits a later pair to bypass the first broken link;
- `graphql_pages_complete_without_observation`: claim and lease required;
  ordered one through ten complete page admission/result pairs; final result
  requires `hasNextPage:false`; every later ordinal's admission and result
  paths through 10 are `absent`; observation exact null; or
- `observation_present`: claim, lease, and complete observation required, with
  the observation's ordered page chain when GraphQL and every later page path
  through ordinal 10 `absent`.

Every deterministic claim, lease, page-admission, page-result, observation,
terminal, capsule, and receipt path inspected by an inventory has exact state
`valid_present`, `absent`, or `invalid_or_partial_present`. Valid state requires
a `record_ref`. Absent state requires record reference, byte count, and byte
hash null. Invalid/partial state requires reference null, byte count
`0..8388608`, and the hash of exactly the retained bytes; the bytes themselves
are never copied. The inventory never treats invalid or partial bytes as a
record, never deletes them, and never infers whether a read request or remote
mutation occurred.

### 8.8 Target-claim path inventory

`github-target-claim-path-inventory/0.1.0` is an immutable local-only recovery
record for the deterministic target-claim path. It is created when claim
creation, durability/readback, or later recovery cannot accept that path as the
current attempt's valid lifecycle record. Its exact fields are all governing
profile, trust, capability, merge-authorization, readiness, and plan
references; repository numeric/node ID, account/App/installation numeric IDs,
PR numeric/node ID, and base/head identities;
target digest and the exact repository-relative target-claim path; path state
from `valid_present`, `absent`, or `invalid_or_partial_present`; inventory-only
artifact reference, byte count, and byte hash under the §8.7 rules; observation
context from `same_process_claim_create_failure` or `restart_or_recovery`;
whether exclusive create was entered; deterministic target-inventory path;
inventory time; `target_permanently_consumed:true`;
`mutation_authority:false`; `replacement_allowed:false`;
`authority_effect:none`; and `approval_effect:none`.

The deterministic inventory path is
`github/merge-target-claim-inventories/target-<digest>.json`. It is itself
exclusive-created, durable, immutable, and never deleted, replaced, released,
or taken over. The closed target-consumption path set also includes the
deterministic §17.4 target-inventory-failure capsule and §17.2 target-bound
terminal-inventory paths. Every Stage 21C attempt checks the entire set before
claim creation and again immediately after a valid claim readback. Any non-
absent path in the set, whether valid, invalid/partial, stale, or crashed,
blocks the target permanently. If any such artifact appears concurrently with
a newly valid claim, that claim grants no authority and the attempt stops.

An existing chain-valid target claim bound to a different plan or authorization
already consumes the target and blocks with `TARGET_ALREADY_CLAIMED`; the
blocked attempt does not create an inventory for that foreign valid claim.

`valid_present` means the bytes parse and validate as the same plan and
authorization's target claim during recovery, but the claim is retained only
as an inventory artifact and is not a trusted lifecycle reference for this
recovery path. `absent` requires a same-process create or
durability failure observed before credential resolution and the exact null
byte fields required by §8.7. `invalid_or_partial_present` retains only the
bounded byte count/hash. All three states consume the target once this
inventory is durable. No state grants mutation authority.

Every downstream family uses exactly one target-evidence variant:

- `target_claim_present`: one chain-valid target-claim `record_ref` and target-
  path-inventory reference exact null; or
- `target_claim_unusable`: target-claim lifecycle reference exact null and one
  valid target-path-inventory `record_ref` whose digest, path, repository, and
  PR bindings match. Its plan/authorization either match the current attempt or
  are retained as conflicting prior bindings with `TARGET_ALREADY_CLAIMED`;
  neither case grants mutation authority; or
- `target_claim_evidence_unusable`: both references exact null and exactly one
  valid §17.4 target-inventory-failure capsule or §17.2 target-bound terminal-
  inventory reference that binds both deterministic path states. This variant
  is permitted only in later read-only reconciliation, its receipt, and ledger.
  It is forbidden in mutation-prefix inventories and merge terminals.

The inventory's own storage failure is represented only by the failure capsule
and later terminal inventory in §17. It never permits replacement or a new
claim.

### 8.9 Mutation-prefix inventory

`github-mutation-prefix-inventory/0.1.0` is an immutable local-only record for
the exact mutation chain from target evidence through response result. Its
exact fields are every governing profile, trust, capability, merge-
authorization, plan, and readiness reference; exactly one of the first two
§8.8 target-evidence variants; repository/account/App/installation/PR/base/head identities; exact
lifecycle variant; valid optional
predecessor references through revalidation, generic intent, merge attempt,
operation claim, lease, admission, and result; deterministic path state for
each optional record using `valid_present`, `absent`, or
`invalid_or_partial_present` and the §8.7 reference/byte-commitment rules;
last valid predecessor ID/hash; inventory time; observation context from
`same_process_before_transport_dispatch` or `restart_or_recovery`;
transmission accounting from `proven_zero`, `conservatively_one`, or
`admission_present_one`; sorted reasons; `authority_effect:none`; and
`approval_effect:none`.

The inventory lifecycle variant is `target_claim_unusable`, the same valid-
claim prefix through `lease_present`, `admitted_without_result`, or
`result_present` used by §17.1, plus
`pre_admission_artifact_unusable` when the admission path is absent or invalid/
partial after a valid lease, and `mutation_chain_artifact_unusable` when one or
more later artifacts are present but their predecessor chain does not validate.
`target_claim_unusable` requires the unusable target-evidence variant, makes
every later lifecycle reference exact null, and inventories every deterministic
path from revalidation through result independently. Path states are
independent: a result path may be valid or invalid/partial even when its
admission path is absent or invalid/partial, but no such combination is a valid
chain and no result fact is inferred from it. For
`mutation_chain_artifact_unusable`, admission and result lifecycle references
are exact null even when their path artifacts are individually valid. A
`valid_present` inventory tuple may identify the isolated artifact only inside
the inventory; `chain_valid:false` and a closed mismatch reason prevent that
artifact from becoming a trusted predecessor reference.

`proven_zero` is permitted only when the same uninterrupted process records,
before entering the transport dispatch function, either that it stopped at a
named pre-admission gate with both admission and result paths absent, or that
admission exclusive-create or durability/readback failed with admission absent
or invalid/partial and result absent; or when a target-claim creation,
durability, or target-consumption-set conflict is immediately inventoried in
the same process before credential resolution with every later deterministic
mutation path absent. `admission_present_one` requires a valid
durable admission whose predecessor chain validates and uses the conservative
§15.2 accounting of one even when socket transmission is not provable; later
result absence, invalidity, or chain failure does not change that accounting.
Every restart/recovery observation without a chain-valid admission, every
unusable target observation outside the same-process zero rule, every chain
failure at or before admission, or any non-absent result beside a non-valid admission uses
`conservatively_one`, consumes the permanent claim and mutation budget, and
cannot support a zero-transmission assertion or another mutation. The
inventory reports local durable state only and never asserts a remote result.
For target-claim or mutation-chain unusable variants, both target and mutation
authority are permanently consumed and retry is forbidden.

## 9. Closed endpoints and permissions

`github-21c-endpoints/0.1.0` contains only these rows. All reads and the merge
have zero retries.

| Key | Method and fixed path | Query/body | Exact permission | Pages/transmissions |
| --- | --- | --- | --- | ---: |
| `rate_limit.get` | `GET /rate_limit` | none | no additional permission; implicit App Metadata read only | 1/1 |
| `repository.get` | `GET /repos/{owner}/{repo}` | none | Metadata read only | 1/1 |
| `repository_hash_algorithm.get` | `GET /repos/{owner}/{repo}/hash-algorithm` | none | Metadata read only | 1/1 |
| `ref.get` | `GET /repos/{owner}/{repo}/git/ref/{ref}` | none | Metadata read + Contents read | 1/1 |
| `commit.get` | `GET /repos/{owner}/{repo}/git/commits/{oid}` | none | Metadata read + Contents read | 1/1 |
| `pull_request.get` | `GET /repos/{owner}/{repo}/pulls/{pr}` | none | Metadata read + Pull requests read | 1/1 |
| `post_merge_pull_request.get` | same GET PR path | none | Metadata read + Pull requests read | 1/1 |
| `check_runs.list` | `GET /repos/{owner}/{repo}/commits/{head}/check-runs` | `per_page=100&page=N` | Metadata read + Checks read | 10/10 |
| `combined_status.get` | `GET /repos/{owner}/{repo}/commits/{head}/status` | `per_page=100&page=N` | Metadata read + Statuses read | 10/10 |
| `reviews.list` | `GET /repos/{owner}/{repo}/pulls/{pr}/reviews` | `per_page=100&page=N` | Metadata read + Pull requests read | 10/10 |
| `review_requests.get` | `GET /repos/{owner}/{repo}/pulls/{pr}/requested_reviewers` | none | Metadata read + Pull requests read | 1/1 |
| `branch_protection.get` | `GET /repos/{owner}/{repo}/branches/{base}/protection` | none | Metadata read + Administration read | 1/1 |
| `branch_rules.list` | `GET /repos/{owner}/{repo}/rules/branches/{base}` | `per_page=100&page=N` | Metadata read only | 10/10 |
| `repository_rulesets.list` | `GET /repos/{owner}/{repo}/rulesets` | `includes_parents=true&per_page=100&page=N` | Metadata read only | 10/10 |
| `review_threads.graphql` | `POST /graphql` | exact §10 body | Metadata read + Pull requests read | 10/10 per pass |
| `merge.put` | `PUT /repos/{owner}/{repo}/pulls/{pr}/merge` | exact §15 body | Metadata read + Contents write | 1/1 |
| `compare_commits.get` | `GET /repos/{owner}/{repo}/compare/{merge_oid}...{current_base_oid}` | `per_page=1&page=1` | Metadata read + Contents read | 1/1 |

Owner/repository values originate only from the profile and are corroborated by
numeric identity. Refs and OIDs pass closed encoders; callers cannot supply a
slash-bearing `basehead`, path, query key, method, or origin. Exact maximum
boundaries pass only when the final response proves no continuation; a next
page at the limit blocks.

`repository.get` followed by `repository_hash_algorithm.get` is the mandatory
Stage 21A profile-verification pair in every Stage 21C observation cycle; no
cache assumption removes either named operation from the maximum plan.

## 10. Fixed GraphQL review-thread operation

REST review comments do not expose the complete thread-resolution state. Stage
21C therefore permits one fixed read-only GraphQL document and no other
GraphQL operation.

The exact UTF-8 query is this single 440-byte line:

```graphql
query ConclaveReviewThreads($owner:String!,$name:String!,$number:Int!,$cursor:String){repository(owner:$owner,name:$name){id nameWithOwner pullRequest(number:$number){id number updatedAt state isDraft baseRefName baseRefOid headRefName headRefOid mergeable mergeStateStatus reviewDecision reviewThreads(first:100,after:$cursor){totalCount nodes{id isResolved isOutdated} pageInfo{hasNextPage endCursor}}}} rateLimit{cost remaining resetAt}}
```

Its SHA-256 is:

`6249f30d7812a26534ae9cf06fd0683f2a8e57c75ca56873a5452fbb35d60e0a`

The request object has exactly `query`, `operationName`, and `variables`.
`query` equals the bytes above, `operationName` is
`ConclaveReviewThreads`, and variables are exactly profile-derived `owner` and
`name`, positive integer `number`, and null or the prior page's opaque cursor.
Callers cannot supply query text, fields, aliases, fragments, directives,
operation name, page size, or cursor except the transport-held prior cursor.
`mutation`, introspection, and persisted-query substitution are prohibited.
Canonical request bytes must be 1 through 4,096 bytes; a longer body blocks
before page admission.

Only HTTP 200 with `Content-Type` exactly `application/json` or
`application/json; charset=utf-8` is accepted. Response/header/body/node/depth
limits are from §4. `Content-Encoding`, redirects, multipart, streaming,
extensions, top-level `errors`, partial data, and unknown top-level keys block.

The exact raw response contract is:

- top object keys exactly `data`;
- `data` keys exactly `repository` and `rateLimit`, both non-null objects;
- `repository` keys exactly `id`, `nameWithOwner`, and `pullRequest`;
- repository `id:node`, canonical `nameWithOwner:safe(256)`, and non-null PR;
- PR keys exactly `id`, `number`, `updatedAt`, `state`, `isDraft`,
  `baseRefName`, `baseRefOid`, `headRefName`, `headRefOid`, `mergeable`,
  `mergeStateStatus`, `reviewDecision`, and `reviewThreads`;
- PR `id:node`, `number:id`, `updatedAt:ts`, state in `OPEN|CLOSED|MERGED`,
  booleans strict, refs `safe(255)`, OIDs exact, mergeable in
  `MERGEABLE|CONFLICTING|UNKNOWN`, merge state in
  `BEHIND|BLOCKED|CLEAN|DIRTY|DRAFT|HAS_HOOKS|UNKNOWN|UNSTABLE`, and review
  decision in `APPROVED|CHANGES_REQUESTED|REVIEW_REQUIRED` or exact null;
- `reviewThreads` keys exactly `totalCount`, `nodes`, and `pageInfo`;
- `totalCount` integer 0–1000; nodes array length 0–100; each node has exactly
  `id:node`, `isResolved:bool`, and `isOutdated:bool`;
- `pageInfo` keys exactly `hasNextPage:bool` and `endCursor`; cursor is null
  only when `hasNextPage:false`, otherwise opaque NFC `safe(1024)`; and
- `rateLimit` keys exactly `cost`, `remaining`, and `resetAt`, with cost literal
  integer `1`, remaining nonnegative integer, and reset `ts`.

Each page repeats repository node ID, canonical name, PR node ID/number,
updated time, base/head refs/OIDs, mergeability, and review decision. Every
value must remain identical across the pass and equal the additive REST
projection. Node IDs are immutable identity bindings; owner/name are never
sufficient.

One observation cycle performs two consecutive complete enumerations with new
operation intents, claims, leases, and §8.6 page chains. Each pass creates a
stable-state aggregate containing only repository/PR node identities, PR
number, updated time, refs/OIDs, closed merge/review enums, thread count, and
sorted unique thread ID/resolved/outdated tuples. The two stable-state
aggregates must be byte-identical.

Cursor and rate facts are expressly excluded from stable-state equality.
Cursors are held only in mutable transport memory and represented durably by
the ordered page-chain hashes. Each page's cost/remaining/reset values are
retained in a separate ordered rate-fact aggregate. Cost must equal one. Within
one unchanged reset window, each succeeding response's remaining value must be
at least one lower than the preceding response and must not fall by fewer than
that page's cost. A changed reset time, exhausted reserve, increase, equal
remaining value, or inconsistent decrease blocks; it is never hidden by state
equality.

Duplicate IDs, cursor loops, missing cursor, page-chain discontinuity, total
mismatch, more than 1,000 threads, a changed stable-state field, or
continuation after page 10 blocks. Exactly 1,000 threads on page 10 passes only
when `hasNextPage:false`. A page-10 continuation writes no page-11 admission;
its ten complete pairs are retained under `graphql_pages_incomplete` with
reason `GRAPHQL_PAGE_LIMIT_CONTINUATION`. Any unresolved thread blocks even
when outdated.

## 11. REST response extensions

Stage 21C reuses a Stage 21A projection only when all required facts are
already retained. The additive `github-21c-projections/0.1.0` adds:

1. **Repository identity:** requires/restores repository numeric and node IDs,
   account ID, canonical full name, visibility, archived/disabled flags,
   default branch, and merge-method booleans.
2. **PR readiness:** adds PR node ID while retaining numeric PR/repository,
   author, base/head repository IDs, refs/OIDs, state, draft, merged,
   mergeable, merge state, and timestamps.
3. **Requested reviewers:** exact objects `users` and `teams`; retains sorted
   unique user numeric IDs/types and team numeric IDs only. Any remaining user
   or team blocks.
4. **Branch protection:** additionally requires complete
   `bypass_pull_request_allowances` App/user/team numeric IDs and explicit
   presence/absence for every security block named in §7.3.
5. **Rate status:** `resources` must contain complete nonnegative `core` and
   `graphql` objects, each with exact `limit`, `used`, `remaining`, and epoch
   reset; other buckets are discarded only after these validate.
6. **Post-mutation PR:** retains numeric/node PR ID, base/head refs/OIDs and
   repository IDs, state, merged boolean, merge OID, and merged timestamp under
   the exact closed union `merged_pr | unmerged_pr`. `merged_pr` requires state
   `CLOSED`, `merged:true`, non-null object-format-valid `merge_commit_sha`, and
   non-null merged timestamp. `unmerged_pr` requires state `OPEN`,
   `merged:false`, `merge_commit_sha:null`, and merged timestamp null. Every
   other combination blocks.
7. **Compare commits:** retains status from `ahead|behind|diverged|identical`,
   nonnegative ahead/behind/total counts, exact base and merge-base OIDs, and
   the requested compare OIDs. Files, patches, messages, names, email, URLs,
   and commit arrays are discarded after the required top-level facts validate
   within the byte ceiling.

Unknown security enums, missing required fields, unsafe null, response
truncation, raw duplicate JSON keys, or identity mismatch blocks.

## 12. Assessment authority and readiness

### 12.1 `github-21c-assessment-authorization/0.1.0`

The pinned human authority signs this read-only record under domain
`CONCLAVE-GITHUB-21C-ASSESSMENT-AUTHORIZATION-V1`. Exact fields are trust
policy/capability/repository/API/permission references; repository/account/
App/installation and PR/base/head identities; exact sorted assessment
operation plan; issue and expiry within 15 minutes; maximum logical operations
`15`, transmissions `78`, core primary requests `57`, GraphQL primary points
`20`, REST secondary points `58`, GraphQL secondary points `20`; purpose;
`merge_authorized:false`;
`authority_effect:"github_21c_readiness_assessment_only"`;
`approval_effect:none`; key ID; and signature.

### 12.2 `github-merge-readiness/0.1.0`

Exact family fields are:

- assessment authorization, trust policy, capability, repository/API/
  permission profiles, Stage 21B receipt, head provenance, independent review,
  no-bypass attestation, every complete operation observation, and any
  interrupted read-prefix inventory as `record_ref`s;
- repository/account/App/installation/acting-account numeric IDs;
- PR numeric/node IDs, author and latest-pusher IDs/types;
- exact base/head refs/OIDs and reviewed tree OID;
- repository merge-method state;
- normalized protection and effective-ruleset hashes;
- exact sorted required-check keys and selected satisfying result IDs/hashes;
- effective review count and sorted qualifying reviewer IDs;
- requested-reviewer and unresolved-thread counts;
- REST/core and GraphQL budget-observation references and remaining values;
- evaluation and expiry, at most five minutes apart;
- status `READY` or `BLOCKED` and sorted unique closed reason codes;
- `merge_authorized:false`;
- `authority_effect:none`; and
- `approval_effect:none`.

`READY` requires all of the following from one stable exact state:

1. every numeric and node identity equals the governed profiles and capability;
2. the Stage 21B receipt proves this exact unmodified head and the fresh head-
   provenance attestation proves no intervening ref event;
3. PR is open, non-draft, unmerged, on the exact allowed base/head refs/OIDs;
4. REST and both GraphQL passes agree exactly;
5. GraphQL mergeable is `MERGEABLE`, merge state is `CLEAN`, and review
   decision is `APPROVED`;
6. normal merge commits are enabled; squash, rebase, queue, async, or default
   selection is never substituted;
7. base is protected, administrator enforcement is enabled, the effective
   up-to-date-before-merge rule is strict, and at least one required check is
   GitHub-enforced so a later base advance is rejected server-side;
8. every active applicable repository/organization rule and legacy protection
   is complete, known, unchanged, and agrees with the no-bypass attestation;
9. no App, installation, acting account, provider, publisher, administrative
   actor, user, or team used by this transaction has a ruleset or legacy bypass;
10. every effective required check has one unambiguous latest exact-head
    terminal `success` result from the required App where one is specified;
11. the effective approval count is the maximum of one, branch protection, and
    active rulesets; each counted human's latest effective review is exact-head
    `APPROVED`; the signed independent review matches one counted review;
12. no current changes-requested, dismissed/stale approval, requested user or
    team, self-review, bot substitution, or independence failure exists;
13. both stable GraphQL enumerations are complete and every thread is resolved;
14. core and GraphQL primary budgets, local secondary-point budgets, byte/page/
    item/time ceilings, and safety reserves are sufficient;
15. every credential lease is exact and no retained conflict, diagnostic, or
    ambiguity is open; and
16. capability proves the target is a dedicated disposable conformance
    repository and not any prohibited target.

Required checks reduce deterministically by context and required App ID. A
context without App ID passes only when the latest exact-name check/status
winner is unique. Neutral, skipped, cancelled, timed-out, action-required,
startup, queued, in-progress, stale, missing, unknown, tied, or conflicting
results block.

Reviews reduce per numeric human ID by submitted time and review ID. Only the
latest submitted non-dismissed exact-head approval counts. Missing timestamp,
type, commit ID, or deterministic order blocks.

A `BLOCKED` readiness is retained as fact and cannot be changed. A new cycle
creates a new record. Any incomplete read chain requires its §8.7 inventory,
forces `BLOCKED`, and cannot be omitted from the readiness evidence aggregate.

## 13. Human merge authorization and append-only plan

### 13.1 `github-merge-authorization/0.1.0`

The pinned human authority signs under domain
`CONCLAVE-GITHUB-MERGE-AUTHORIZATION-V1`. Exact fields are trust policy,
capability, profiles, readiness, head provenance, independent review,
no-bypass attestation, and protection-freeze lease `record_ref`s; repository/
account/App/installation/acting-account and PR numeric/node IDs; exact base/
head refs/OIDs; `merge_method:"merge"`; exact sorted required-check keys and
evidence hashes; protection/ruleset hashes; creation, not-before, and expiry
within five minutes; purpose/operator session; `maximum_attempts:1`;
`maximum_mutation_transmissions:1`; `automatic_mutation_retries:0`;
`maximum_logical_operations:21`; `maximum_total_transmissions:84`;
`maximum_core_primary_requests:63`; `maximum_graphql_primary_points:20`;
`maximum_local_secondary_points:88`;
`atomicity_class:"conditional_head_plus_server_strict_base_control"`;
`base_oid_is_not_endpoint_precondition:true`;
`administrator_exception_authorized:false`;
`merge_authorized:true`;
`authority_effect:"github_merge_exact_head_once"`;
`approval_effect:none`; key ID; and signature.

The authorization is created after readiness and while readiness and every
signed input remain valid. It explicitly acknowledges that GitHub's merge
endpoint conditionally binds only the head SHA; exact-base enforcement depends
on the still-active strict up-to-date server control and the externally
serialized protection-freeze lease. If either cannot be proven, no
authorization is admissible.

### 13.2 `github-merge-plan/0.1.0`

This non-authoritative immutable record contains exactly the authorization and
all profile/evidence references; target identities; exact request body/hash;
ordered final-revalidation operations; ordered success/reconciliation reads;
exact ceilings of 21 logical operations, 84 transmissions, 63 core-primary
requests, 20 GraphQL-primary points, 88 local secondary points, one mutation
transmission, and zero retry; deadline; deterministic target/attempt IDs;
`authority_effect:none`; and `approval_effect:none`.

### 13.3 Target-wide atomic claim

Before any final-revalidation credential resolution, Stage 21C exclusively
creates one `github-merge-target-claim/0.1.0` at:

`github/merge-target-claims/target-<digest>.json`

`<digest>` is SHA-256 of domain `CONCLAVE-GITHUB-MERGE-TARGET-V1`, zero byte,
and canonical repository numeric ID plus immutable PR node ID. It is
independent of authorization, head, session, and actor.

Exact claim fields are deterministic claim ID, target digest, merge plan and
authorization references, repository/account/PR numeric/node IDs, base/head
OIDs, claim time/expiry, `state:"claimed"`, `authority_effect:none`, and
`approval_effect:none`. It contains no lease, observation, dispatch, result,
or future hash.

Exclusive creation uses `CREATE_NEW` on Windows and `O_CREAT|O_EXCL` on POSIX,
followed by file and directory durability/readback verification. Any existing
target path—equal, unequal, terminal, stale, or crashed—permanently blocks
another Stage 21C merge attempt for that PR. Stage 21C v0.1 never deletes,
reuses, takes over, or releases a target claim. A new attempt therefore
requires a new PR, closing cross-authorization and cross-process races.

Before exclusive creation, and again immediately after a valid durability
readback, the process checks the complete deterministic target-consumption path
set from §8.8.
Any non-absent target-claim path that is not the exact chain-valid claim for
this attempt, or any non-absent target-inventory path, stops the attempt. A
claim create/durability failure or later unusable claim path creates the §8.8
inventory before any further step. The inventory's valid presence, and even an
invalid/partial inventory path found later, permanently blocks all future
attempts for the target. A same-process absent claim path can support zero-
transmission accounting only after its target inventory is durable and every
later mutation path is proven absent. If the inventory cannot be stored, §17.4
records the failure when possible and no mutation or replacement is allowed.

## 14. Final revalidation order and race boundary

After the target claim is durable, chain-valid, and accompanied by an absent
target-inventory path:

1. perform the complete 78-transmission maximum observation cycle under
   operation-specific read leases, beginning with fresh `rate_limit.get`
   evidence and including two stable GraphQL passes;
2. create immutable `github-merge-revalidation/0.1.0` containing the target
   claim, readiness/authorization, every fresh observation, old/new factual
   projection comparison, protection-freeze lease, evaluation time, status
   `MATCH` or `CHANGED`, reasons, `authority_effect:none`, and
   `approval_effect:none`;
3. only on `MATCH`, create the mutation generic intent and merge-specific
   attempt defined in §15;
4. exclusive-create the mutation's `github-operation-attempt-claim/0.2.0`,
   binding the generic intent, merge-specific attempt, and permanent target
   claim;
5. resolve and validate the one merge lease against that operation claim;
6. immediately before durable dispatch admission, revalidate local clock,
   trust-root pin, all key/profile status, authorization/readiness/control-
   lease expiry, merge lease, rate reserve, the exact target claim with every
   other target-consumption path still absent, and unchanged revalidation
   aggregate; and
7. after admission durability, perform no model call, filesystem traversal,
   network read, credential renewal, wait, sleep, or unrelated work before the
   single send.

Any remotely observed state change invalidates authorization before mutation.
There is no reauthorization or retry within the claim.

An unusable target-claim path never enters final revalidation, credential
resolution, or mutation admission. It closes through the target-path and
mutation-prefix evidence in §§8.8–8.9 and the matching §17 terminal or failure
path. Recovery is read-only and cannot turn that evidence into a claim.

If the final observation cycle stops before every observation exists, its
§8.7 inventories are bound to a `target_claim_only` terminal with transmission
zero. No mutation intent or credential resolution follows.

The unavoidable residual interval between last remote observation and GitHub
processing is explicitly bounded, not misrepresented as an expected-base API
precondition. Server-side strict up-to-date protection must reject a base
advance. The independent control-plane freeze lease must serialize protection,
ruleset, and bypass changes. Post-mutation proof rechecks both. A control change
or merge onto a different base is a critical factual terminal outcome, never
success. Because Increment 21 forbids production use, any separately authorized
exercise remains confined to its disposable repository.

## 15. Mutation intent, admission, and transport

### 15.1 Generic and merge-specific intents

After successful revalidation, create one mutation
`github-operation-intent/0.2.0` and cross-bound
`github-merge-attempt/0.1.0`. The latter is the merge-specific immutable intent,
not a mutable lifecycle record.

Its exact fields are merge attempt ID `uuid7`; merge plan, target claim,
authorization, readiness, revalidation, trust policy, capability, profiles,
provenance, review, no-bypass, and protection-freeze references; generic intent
reference; repository/account/App/installation/acting-account and PR IDs;
base/head refs/OIDs; exact endpoint/method/body hash and byte count; exact
permission map; attempt ordinal `1`; mutation/transmission/retry ceilings
`1/1/0`; creation/expiry; `authority_effect:none`; and
`approval_effect:none`. It contains no later lease, admission, response,
result, receipt, or reconciliation reference.

The merge attempt is then referenced by the mutation's
`github-operation-attempt-claim/0.2.0`. That claim is the last durable
pre-credential predecessor and binds both intents plus the permanent target
claim. A missing, conflicting, or previously existing operation claim blocks
without credential resolution.

### 15.2 `github-merge-step-admission/0.1.0`

Immediately before send, durably create one immutable admission containing
exactly the merge attempt, generic intent, mutation operation claim, permanent
target claim, merge lease evidence, and revalidation references; step ordinal
`1`; repository/PR/base/head; request hash; local and server rate budgets
before/after admission; trust/key/deadline/control-lease/revalidation checks
all literal true; transmission count before `0` and after admission `1`;
`state:"dispatch_admitted_not_confirmed"`; `retry_allowed:false`;
`authority_effect:none`; and `approval_effect:none`.

An existing admission blocks. A crash after durable admission is ambiguous
even when socket transmission cannot be proven. No admission is deleted.

### 15.3 Only permitted request

- method: `PUT`;
- origin: literal `https://api.github.com`;
- path: `/repos/{owner}/{repo}/pulls/{pull_number}/merge`;
- query: none;
- body key set exactly `merge_method` and `sha`, serialized only in canonical
  sorted order `merge_method` then `sha`;
- `sha`: authorization-bound exact head OID;
- `merge_method`: literal `merge`;
- no caller header, title, commit message, or extra body field; and
- exactly one transmission, zero retry.

The request-body hash covers canonical UTF-8 JSON. Owner/repository/PR come
only from governed profiles and records. Hostname/TLS verification is
mandatory; redirect, proxy, alternate origin, userinfo, direct IP, header
injection, default method, async endpoint, queue, squash, rebase, auto-merge,
and update-branch fail before network I/O.

### 15.4 `github-merge-step-result/0.1.0`

After a complete bounded HTTP response, durably write a new immutable result;
never modify admission. A timeout, disconnect, cancellation, crash, or failure
without one complete accepted HTTP response creates no result record. Exact
result fields are admission/attempt/operation-claim/lease references;
transmission count `1`;
accepted HTTP status; response-header occurrence-view state from `lossless` or
`unavailable_or_lossy`; separate Content-Type, Retry-After, and remaining-field
occurrence counts `0..32768` only for `lossless` and exact null otherwise;
response variant; response projection hash; response received/complete
booleans both true;
returned merge OID or null; returned `merged` boolean or null; completion time;
bounded core rate projection; outcome class from `candidate_success`,
`candidate_refusal`, or `ambiguous`; safe reason codes;
`authority_effect:none`; and `approval_effect:none`.

Before any media or rate value is classified, the transport must expose an
ordered lossless response-header occurrence stream: HTTP/1 field lines or
HTTP/2 field entries after framing decode but before semantic normalization,
case folding, duplicate combination, comma coalescing, or map construction.
Field names are matched to `Content-Type`, `Retry-After`, and
`X-RateLimit-Remaining` by ASCII-case-insensitive byte comparison. Every
matching occurrence, including differently cased duplicates, is retained in
received order. A last-value-only map, comma-joined value, or adapter view that
cannot prove original multiplicity and order is forbidden. Failure to provide
this view makes the complete response `ambiguous_response`; rate class is
`rate_signal_invalid`, reason is `RATE_HEADER_TRANSPORT_LOSSY`, and no success
or refusal fact is accepted. The raw field names and values are processed only
transiently and never enter durable evidence.

The exact media-type classes are `github_json`, `other_valid`, `missing`, and
`invalid`. One field value is first required to contain 1 through 256 ASCII
bytes. Outer optional whitespace is removed, where optional whitespace is
only zero or more SP or HTAB bytes. ASCII letters are then case-folded to
lowercase for classification. `github_json` accepts only
`application/json`, `application/json;charset=utf-8`,
`application/json; charset=utf-8`, `application/vnd.github+json`,
`application/vnd.github+json;charset=utf-8`, or
`application/vnd.github+json; charset=utf-8` after that processing.

`other_valid` accepts only a non-`github_json` value matching this closed byte
grammar:

`type "/" subtype *( OWS ";" OWS parameter-name OWS "=" OWS parameter-value )`

`type`, `subtype`, `parameter-name`, and `parameter-value` are each one through
127 bytes and contain only ASCII `tchar`: letters, digits, or one of
``!#$%&'*+-.^_`|~``. `OWS` is zero through 16 SP or HTAB bytes. There are zero
through eight parameters. Parameter names must be unique after ASCII case
folding. A slash, semicolon, or equals sign cannot appear inside a token.
Quoted strings, backslash escapes, comments, empty tokens, duplicate parameter
names, trailing separators, other whitespace, controls, DEL, and non-ASCII are
invalid. Parameter order is accepted as received but is never retained or
normalized because only the class and raw-body commitment are durable.
`missing` means no Content-Type field. A duplicate field, empty value, failed
grammar, or value outside the byte bound is `invalid`. No platform or library
media-type parser participates in classification.

The exact rate classes are `not_rate_limited`, `primary_limited`,
`secondary_limited`, `rate_limited_unknown`, and `rate_signal_invalid`. The
classifier executes these four ordered steps with no short circuit before step
1 completes:

1. From the lossless occurrence stream, collect every field whose raw name
   ASCII-case-folds to `retry-after` or `x-ratelimit-remaining`. Preserve each
   occurrence separately and in received order. More than one occurrence of
   either folded name is invalid, including differently cased duplicates. A
   comma byte in either target value is invalid with reason
   `RATE_HEADER_COMMA_INVALID` and can never be interpreted as a combined list.
   Validate the multiplicity and bytes of every present
   occurrence. Each present value must be one
   ASCII decimal integer with no sign, whitespace, separator, leading zero
   except literal zero, or non-digit. `Retry-After` is valid only from 1
   through 120; zero, above 120, HTTP-date, malformed, or overflowing values
   are invalid. `X-RateLimit-Remaining` is valid only from 0 through
   `2^63-1`. If either field is duplicate or invalid, return exactly
   `rate_signal_invalid` without applying steps 2 through 4, even when the
   other field is valid. A transport that cannot supply the lossless occurrence
   stream also returns this class before steps 2 through 4.
2. With every present field valid, a present `Retry-After` returns exactly
   `secondary_limited`, regardless of HTTP status or remaining value.
3. Otherwise a present remaining value of zero returns exactly
   `primary_limited`; otherwise HTTP status 429 returns exactly
   `rate_limited_unknown`.
4. Every remaining combination returns exactly `not_rate_limited`.

Thus mixed valid/invalid or valid/duplicate fields have one result; every
valid `Retry-After`, including on HTTP 200 or a non-rate refusal status, is a
blocking secondary-limit signal; and invalid evidence never falls through to
a valid-field or status class. Platform or HTTP-library coalescing cannot
convert duplicate, differently cased, or comma-combined evidence into one
valid value.

The response variant is exactly one of:

- `success_shape`: HTTP 200, media class `github_json`, rate class
  `not_rate_limited`, and a top-level object
  with exactly object-format-valid `sha`, strict boolean `merged`, and bounded
  `message:safe(4096)`; the projection retains only status, OID, boolean, rate facts, and
  raw-body byte count/hash after discarding message text;
- `status_refusal`: HTTP 403, 404, 405, 409, 422, or 429; bounded body consumption;
  exact media-type class; raw-body byte count/hash; closed refusal class
  `forbidden`, `not_found`, `method_not_allowed`, `conflict`, `unprocessable`,
  or `rate_limited`; returned OID and merged fields exact null; and no retained
  provider text, with exact status/rate mapping defined below; or
- `ambiguous_response`: any other complete bounded HTTP response, or a 200 or
  refusal status whose body/media type violates its accepted contract;
  retaining only status, media-type class, raw-body byte count/hash, rate
  class, null returned fields, and closed ambiguity reason.

`status_refusal` permits media class `github_json`, `other_valid`, or `missing`
and forbids `invalid`. Status 403 uses refusal class `rate_limited` only with
rate class `primary_limited` or `secondary_limited`, uses `forbidden` only with
`not_rate_limited`, and otherwise uses `ambiguous_response`. Status 429 uses
`rate_limited` with `primary_limited`, `secondary_limited`, or
`rate_limited_unknown`, and otherwise uses `ambiguous_response`. Status 404,
405, 409, or 422 uses its respective named non-rate refusal class only with
`not_rate_limited`; every other rate class uses `ambiguous_response`. Every
other HTTP status uses `ambiguous_response` regardless of rate class. Thus
`rate_signal_invalid` always uses `ambiguous_response`. In particular, no HTTP
200 response carrying a valid `Retry-After` or remaining zero can satisfy
`success_shape`. A `github_json` body must pass the bounded duplicate-key-
safe JSON parser; `other_valid` and `missing` bodies are consumed opaquely under
the byte ceiling. Malformed or duplicate-key JSON uses `ambiguous_response`.
No error text, documentation URL, message, request ID,
login, or provider-selected value enters the canonical projection except the
one-way raw-body hash. Literal `merged:true` in `success_shape` creates only
`candidate_success`; it is not success until §16 proof. Literal false or
`status_refusal` creates `candidate_refusal` but still requires read-only
reconciliation before a terminal not-merged fact. Timeout, disconnect,
cancellation, TLS failure after admission, persistence failure, or crash
creates no result and is ambiguous. No result or variant triggers mutation
retry.

## 16. Post-mutation proof and ancestry

Every admitted mutation, including a candidate refusal or ambiguity, enters
one bounded proof/reconciliation sequence using new read-only operation chains.
The maximum five logical reads are:

1. repository identity;
2. additive post-merge PR observation retaining `merge_commit_sha`;
3. current base ref;
4. the candidate/reported merge commit when one exists; and
5. compare `{merge_oid}...{current_base_oid}` when the base has advanced.

An incomplete proof read produces a §8.7 inventory. The terminal binds every
complete proof observation and interrupted-read inventory, sets proof complete
false, and cannot infer success or non-mutation.

The signed protection-freeze closeout in §7.4 is also mandatory. It is supplied
through the external attestor boundary, not a GitHub network operation, and
therefore does not consume a Stage 21C GitHub transmission.

### 16.1 Confirmed merge

`MERGED_CONFIRMED` requires:

- repository numeric/node/account identity unchanged;
- PR `merged:true` and its exact `merge_commit_sha` equals the response OID;
- the merge commit has exactly pre-mutation base as first parent and authorized
  head as second parent; and
- either current base equals the merge OID, or bounded compare reports
  `identical`/`ahead` with merge-base OID equal to the merge OID, proving the
  current base contains that exact merge commit.

This satisfies containment even after a later benign base advance. Comparison
failure, divergence, body overflow, or incomplete proof never becomes success.

### 16.2 Base or control race

If the returned merge commit's first parent differs from the authorized base,
the factual outcome is `MERGED_ON_UNAUTHORIZED_BASE`. If protection, ruleset,
bypass state, trust pin, or the freeze lease changed before the response—or the
required signed freeze closeout is missing—the outcome cannot be confirmed as
success. Proven change is `MERGED_WITH_CONTROL_DRIFT`; missing/incomplete
closeout is `OUTCOME_UNKNOWN`. Either is a critical protocol incident:
the merge is retained as fact, success is false, no repeat occurs, and Stage
21C performs no rollback or repository mutation.

### 16.3 Refusal and ambiguity

`NOT_MERGED_OBSERVED` requires the PR remain open/unmerged, base/head remain
exact, the `unmerged_pr` projection, and no remote merge commit. Its local
result is exact null or `candidate_refusal`; a retained refusal result is not a
remote merge result. `MERGED_CONFIRMED_AFTER_AMBIGUITY` requires the complete
§16.1 proof.

If a `candidate_refusal` result is followed by `merged_pr` and the complete
authorized-base parent, head, containment, and closeout proof, the factual
outcome is `MERGED_EXTERNALLY_OR_CONCURRENTLY_OBSERVED`. It is an incident and
not a successful CONCLAVE result: merged is factual true, attribution to the
CONCLAVE request is false, the permanent claim remains consumed, and no retry
or rollback occurs. Contradictory, missing, changed, rate-limited, or incomplete
facts yield `OUTCOME_UNKNOWN`.

The target claim or target-consumption evidence and authorization are consumed
for every outcome. A later
read-only reconciliation may use the authorization below, new additive
operation chains, and the same proof rules, but it cannot send a mutation or
release the target claim.

### 16.4 `github-merge-reconciliation-authorization/0.1.0`

The pinned human authority signs this record under domain
`CONCLAVE-GITHUB-MERGE-RECONCILIATION-AUTHORIZATION-V1`. Exact family fields
are a fresh disposable capability and trust policy; original merge
authorization and plan; exactly one §8.8 target-evidence variant; revalidation,
generic intent, merge attempt, operation claim, lease, admission, and result
references using exact nulls only when absent in the proven durable prefix;
sorted original interrupted-read
inventory references; original mutation-prefix evidence variant defined
below; the terminal-artifact variant below;
repository/account/PR/base/head identities; exact
sorted read operation keys limited to `rate_limit.get`, `repository.get`,
`post_merge_pull_request.get`, `ref.get`, `commit.get`, and
`compare_commits.get`; issue/expiry within 15 minutes; maximum logical
operations `6`; maximum transmissions `6`; mutation transmissions `0`;
maximum core primary requests `5`; maximum GraphQL primary points `0`;
maximum local secondary points `6`;
`merge_authorized:false`;
`authority_effect:"github_21c_read_only_reconciliation"`;
`approval_effect:none`; key ID; and signature. It authorizes observation only
and cannot release, replace, or convert the original target-consumption
evidence into a claim.

The original target evidence is exactly `target_claim_present` with a valid
claim reference and target-path-inventory reference null;
`target_claim_unusable` with claim reference null and a valid target-path-
inventory reference; or `target_claim_evidence_unusable` with both null and a
valid target-inventory-failure capsule or target-bound terminal inventory. The
last reference must also be the selected terminal-artifact evidence and bind
both deterministic path states and byte commitments. No variant can promote an
inventory-only claim artifact to a lifecycle reference or authorize mutation.

The authorization's terminal-artifact variant is exactly one of
`terminal_present` with a terminal reference, `failure_capsule_present` with a
capsule reference, or `terminal_artifacts_unusable` with a
`github-merge-terminal-inventory/0.1.0` reference. Non-selected fields are exact
null. The inventory binds the complete durable prefix and its last predecessor;
the authorization cannot invent an absent record or assert a remote outcome.

The original mutation-prefix evidence is exactly one of
`mutation_prefix_inventory_present` with its valid `record_ref`, or
`mutation_prefix_inventory_unusable` with that field null and the same
`github-merge-terminal-inventory/0.1.0` reference used to bind the absent or
invalid/partial inventory path, or `mutation_not_entered_target_failure` with
the mutation-prefix reference null and the terminal-artifact capsule/inventory
binding an unusable target path before mutation-prefix creation. A terminal can
exist only with the first variant. The second exists solely for later read-only
reconciliation after the inventory write and terminal chain could not be
completed; it always accounts one conservatively. The third carries exactly
the target-failure capsule/inventory's `conservatively_one` accounting. A
proven-zero target failure is terminally closed and ineligible for
reconciliation.
Neither can authorize or attribute a mutation.

## 17. Immutable terminal and ledger contracts

### 17.1 `github-merge-terminal/0.1.0`

One terminal record is written after a pre-transmission block or proof. Its
common exact fields are all governing profile/evidence references; plan and
exactly one of the first two §8.8 target-evidence variants; sorted unique interrupted-read
inventory references;
exactly one mutation-prefix inventory reference; repository/PR/base/head
identities; terminal variant and outcome; transmission accounting from
`proven_zero`, `admission_present_one`, or `conservatively_one`;
transmission count `0` or `1`; merged factual boolean or exact null, where null
is required whenever outcome is unknown;
request attribution from `confirmed_by_response`, `not_attributed`, or
`not_applicable`;
returned/reconciled merge OID or null; current base OID or null;
ancestry-proven boolean; protection/control-drift booleans; proof-complete
boolean; sorted reasons; terminal time; `merge_authorized:false`;
`authority_effect:none`; and `approval_effect:none`.

The lifecycle references form this exact prefix-complete discriminated union.
Every named earlier reference is required and every unlisted later reference
is exact null. No inventory-only artifact reference is a lifecycle reference:

- `target_claim_unusable_zero`: unusable target evidence, target-claim
  lifecycle reference null, revalidation through result absent, and a mutation-
  prefix inventory in `target_claim_unusable` with `proven_zero`;
- `target_claim_uncertain`: the same unusable target evidence and null
  lifecycle references, with a `target_claim_unusable` mutation-prefix
  inventory using `conservatively_one`;
- `target_claim_only`: target claim, with revalidation through result absent;
- `revalidation_present`: target claim and revalidation;
- `generic_intent_present`: target claim, revalidation, and generic intent;
- `merge_attempt_present`: the preceding prefix plus merge attempt;
- `operation_claim_present`: the preceding prefix plus mutation operation
  claim;
- `lease_present`: the preceding prefix plus merge lease;
- `mutation_prefix_uncertain`: a valid predecessor prefix through optional
  lease, admission/result record references null, and a mutation-prefix
  inventory whose admission is absent or invalid/partial and whose
  transmission accounting is `conservatively_one`;
- `mutation_chain_uncertain`: a valid predecessor prefix through optional
  lease, admission/result lifecycle references exact null, and a mutation-
  prefix inventory in `mutation_chain_artifact_unusable`; any individually
  valid admission/result artifact remains inventory-only with
  `chain_valid:false`;
- `admitted_without_result`: the preceding prefix plus admission, with result
  exact null; or
- `result_present`: the complete preceding prefix plus result.

`target_claim_unusable_zero`, `target_claim_only`, `revalidation_present`,
`generic_intent_present`, `merge_attempt_present`, `operation_claim_present`,
and `lease_present` require a mutation-prefix inventory with
`transmission_accounting:proven_zero`; have transmission count zero;
admission/result/closeout and proof references null; merged false; and outcome
`BLOCKED_BEFORE_TRANSMISSION`. `target_claim_uncertain`,
`mutation_prefix_uncertain`, and `mutation_chain_uncertain` require
`transmission_accounting:conservatively_one`, count one against the immutable
mutation and transmission ceilings, have merged exact null, proof-complete
false, and outcome `OUTCOME_UNKNOWN`; they never claim that a request actually
reached GitHub. They use request attribution `not_attributed`, permanently
consume target and mutation authority, forbid retry, and can be resolved only
by separately authorized read-only reconciliation. `admitted_without_result`
and `result_present` require a valid
admission and mutation-prefix inventory accounting `admission_present_one`;
have transmission count one; and carry a sorted list of zero through five
proof-observation references plus sorted interrupted-proof inventories;
closeout is `record_ref` or exact null.

Closeout null forces proof-complete false and outcome `OUTCOME_UNKNOWN` unless
the terminal is a zero-transmission block. A confirmed or control-drift merge
requires a non-null authenticated closeout.

The closed terminal outcomes are:

- `BLOCKED_BEFORE_TRANSMISSION`;
- `NOT_MERGED_OBSERVED`;
- `MERGED_CONFIRMED`;
- `MERGED_CONFIRMED_AFTER_AMBIGUITY`;
- `MERGED_EXTERNALLY_OR_CONCURRENTLY_OBSERVED`;
- `MERGED_ON_UNAUTHORIZED_BASE`;
- `MERGED_WITH_CONTROL_DRIFT`; and
- `OUTCOME_UNKNOWN`.

Variant rules are exact. Absence or invalid/partial presence of admission
proves zero transmission only when a same-process mutation-prefix inventory
records `proven_zero` before transport dispatch. After restart, the same path
state is `mutation_prefix_uncertain`, conservatively consumes one, and makes no
remote assertion. A target-claim path observed unusable on restart is
`target_claim_uncertain`; a path-valid but chain-invalid mutation artifact is
`mutation_chain_uncertain`. An outcome other than
`BLOCKED_BEFORE_TRANSMISSION` or an uncertain variant requires valid admission.
`MERGED_CONFIRMED` requires a
`candidate_success` result, complete proof, merge OID, ancestry, and closeout.
It alone uses request attribution `confirmed_by_response`.
`MERGED_CONFIRMED_AFTER_AMBIGUITY` requires admission, complete proof, merge
OID, ancestry, and closeout but permits result exact null or an
`ambiguous_response` result and uses `not_attributed`. A drift variant requires merged true and its
specific drift boolean but does not require a complete response result when
proof establishes the factual merge.
`MERGED_EXTERNALLY_OR_CONCURRENTLY_OBSERVED` requires a `candidate_refusal`
result, complete proof, merge OID, ancestry, closeout,
request attribution `not_attributed`, and success false.
`BLOCKED_BEFORE_TRANSMISSION` and `NOT_MERGED_OBSERVED` use `not_applicable`;
every merged outcome other than `MERGED_CONFIRMED` uses `not_attributed`;
`OUTCOME_UNKNOWN` also uses `not_attributed`. Unknown requires proof-complete
false, merged exact null, and makes no negative merge assertion.

### 17.2 `github-merge-reconciliation-receipt/0.1.0`

Exact fields are reconciliation authorization and new read-chain references;
original target-evidence variant and complete durable-prefix references through
optional admission/result;
original and new interrupted-read inventories; original mutation-prefix
evidence variant from §16.4; terminal-artifact variant below;
repository/PR/base/head; factual outcome from the same closed
terminal enum except pre-transmission; merge/current-base OIDs or null;
ancestry and proof booleans; original transmission accounting/count;
reconciliation `mutation_transmissions:0`; reasons/time;
`authority_effect:none`; and `approval_effect:none`. It cannot synthesize
absent result fields or alter the original chain.

The terminal-artifact variant is exactly one of:

- `terminal_present` with terminal `record_ref` and other artifact fields null;
- `failure_capsule_present` with capsule `record_ref` and others null; or
- `terminal_artifacts_unusable` with both null and one
  `github-merge-terminal-inventory/0.1.0` reference.

The inventory is an immutable local-only record binding the exact lifecycle
variant, the §8.8 target-evidence variant or, when its inventory is unusable,
the deterministic target-claim and target-inventory path states directly;
every valid durable prefix reference through optional result; every §8.7 read-
prefix inventory; and the §8.9 mutation-prefix evidence variant or its
deterministic path state; deterministic mutation-inventory/admission/terminal/
capsule/receipt paths; artifact state for each from `valid_present`, `absent`,
or `invalid_or_partial_present` under §8.7; last durable predecessor ID/hash;
inventory time;
`authority_effect:none`; and `approval_effect:none`. It cannot assert a remote
result. `terminal_artifacts_unusable` requires terminal and capsule each be
`absent` or `invalid_or_partial_present`, with no valid record reference. A
claimed absent path is accepted only after platform durability and exclusive-
path readback checks. Partial or invalid final-path bytes are retained and
hashed, never treated as absent, valid, or safe to overwrite.

When the inventory binds unusable target evidence, its exclusive deterministic
path is `github/merge-terminal-inventories/target-<digest>.json`; any valid,
invalid/partial, or crashed presence is part of the permanent target-
consumption set in §8.8. It grants no claim or mutation authority.

### 17.3 `github-merge-receipt/0.1.0`

The receipt is a closed factual summary of a durably stored terminal. It
contains exactly terminal and every governing reference/hash, including every
present lifecycle reference, exactly one of the first two §8.8 target-evidence
variants, and the
optional mutation operation claim, lease, admission, and result; mutation-
prefix inventory; repository/PR/base/head
identities; transmission accounting and count; terminal outcome; merged/proof/
drift booleans; request attribution; merge/current-base OIDs or null; times;
sorted reasons; `merge_requested:true` only for `admission_present_one`, false
only for `proven_zero`, and exact null for `conservatively_one`;
`merge_authorized:false`; `authority_effect:none`; `approval_effect:none`;
`decision_effect:none`; `membership_effect:none`; and
`production_use_allowed:false`. The receipt never implies approval or KOS
adoption.

### 17.4 Target-, mutation-prefix-, terminal-, or receipt-store failure

At most one immutable `github-merge-terminal-failure/0.1.0` capsule uses this
exact discriminated union:

- `target_claim_path_inventory_store_failed`: target-claim lifecycle and
  target-path-inventory references exact null; merge authorization, readiness,
  plan, target digest/path, observed target-path state/byte commitment,
  deterministic inventory path and deterministic capsule path
  `github/merge-target-claim-failures/target-<digest>.json`, creation/recovery
  context, and every later mutation-path state required; transmission
  accounting is `proven_zero` only
  for same-process pre-credential failure with every later path absent and is
  otherwise `conservatively_one`; target and mutation authority are consumed;
- `mutation_prefix_inventory_store_failed`: mutation-prefix inventory and
  terminal/receipt references exact null; complete durable mutation prefix and
  last-predecessor ID/hash required; deterministic inventory path and failed-
  write state/byte hash required; transmission accounting
  `conservatively_one`; or
- `terminal_store_failed`: terminal reference exact null; complete durable
  prefix and last-predecessor ID/hash required; terminal path and failed-write
  byte hash required; receipt reference exact null; or
- `receipt_store_failed`: durable terminal reference required; receipt
  reference exact null; failed-receipt path and byte hash required.

All variants retain the target-evidence and mutation-prefix-inventory
references or exact nulls as their variant requires, transmission accounting
and count, factual outcome
class only when already proven by durable predecessors,
safe closed storage-failure reason, failure time, every interrupted-read
inventory, and all no-authority fields.
They never infer a remote result. If capsule storage also fails, emit only a
sanitized local diagnostic and stop; the later inventory records the actual
`absent` or `invalid_or_partial_present` state and byte commitment for each
failed artifact. No failure path sends another mutation.

### 17.5 Ledger truth

A ledger event is emitted only from a successfully persisted receipt or
terminal-failure capsule. It contains only record IDs/hashes, repository
numeric ID, PR numeric ID, present lifecycle-chain aggregate hash including
the target-consumption evidence and the mutation operation claim and mutation-
prefix inventory where created,
transmission accounting/count, nullable factual terminal values,
closed outcome/reasons, and no-authority constants. It contains no names, refs,
URLs, titles, bodies, messages, cursors, rate values, selectors, lease IDs,
credentials, email, or raw GitHub content.

Reconstruction derives lifecycle solely from the append-only chain:

`plan → (target claim | target-path inventory | target-failure capsule/inventory) → revalidation? → generic intent? → merge attempt? → operation claim? → lease? → admission? → result? → mutation-prefix inventory? → proof? → terminal? → receipt/capsule? → ledger?`

A separately authorized later reconciliation appends, without changing that
history:

`original target evidence/durable prefix/read inventories/mutation-prefix evidence → reconciliation authorization → new read-operation chains → reconciliation receipt → reconciliation ledger event`

Any original terminal, capsule, receipt, or ledger event remains immutable.
The reconciliation ledger is emitted only from the durably stored
reconciliation receipt and binds the original and new chain hashes.

An admission without result is ambiguous. Admission absence or invalid/partial
presence proves no transmission only through a same-process mutation-prefix
inventory written before transport dispatch. Restart/recovery cannot infer
zero from current path state: it accounts one conservatively, keeps the target
consumed, and requires read-only reconciliation. Absence of evidence never
proves success or non-mutation.

An unusable target-claim path follows the same rule: only a same-process,
pre-credential inventory with every later mutation path absent can prove zero.
Restart, later corruption, an unusable inventory path, or any later artifact
accounts one conservatively. Neither the terminal, capsule, inventory,
reconciliation, receipt, nor ledger can turn it into mutation authority or
permit claim replacement.

## 18. Rate limits and complete request arithmetic

### 18.1 `github-21c-rate-budget-observation/0.1.0`

Derived only from accepted `rate_limit.get` plus bounded response headers, the
exact fields are source observation; trust/capability/repository/API/
permission/provider/lease identities; API version; complete `core` and
`graphql` limit/used/remaining/reset values; observation time; no Retry-After
observed; local REST and GraphQL secondary-point counters; complete true;
`authority_effect:none`; and `approval_effect:none`.

The record expires after 60 seconds. REST/core and GraphQL reserves are
separate and cannot substitute for one another. Each GraphQL page must report
query `cost == 1`; zero, higher, or unknown cost blocks. Response headers can narrow
but never expand the authorized budgets.

GitHub exposes no query for secondary-limit status. Stage 21C therefore makes
no claim that a secondary limit is absent. It uses a conservative deterministic
local policy: one sequential request at a time; no sleep/wait/resume; no retry;
GraphQL query cost exactly one; REST GET secondary cost one; the one PUT local
secondary cost five; and stop on Retry-After, rate-limit-classified 403/429,
GraphQL limit error, remaining zero, or other observable signal. Continuing
requires a new governed operation; an admitted mutation first requires factual
reconciliation.

### 18.2 Exact arithmetic

One maximum observation cycle is:

| Component | Logical operations | Maximum transmissions |
| --- | ---: | ---: |
| `repository.get`, `repository_hash_algorithm.get`, `ref.get`, `commit.get`, `pull_request.get`, and `branch_protection.get` | 6 | 6 |
| `check_runs.list`, `combined_status.get`, `reviews.list`, `branch_rules.list`, and `repository_rulesets.list` | 5 | 50 |
| `review_requests.get` | 1 | 1 |
| two ten-page GraphQL stability passes | 2 | 20 |
| `rate_limit.get` | 1 | 1 |
| **cycle total** | **15** | **78** |

Full maximum execution is:

| Phase | Logical operations | Maximum transmissions |
| --- | ---: | ---: |
| initial readiness cycle | 15 | 78 |
| final revalidation cycle | 15 | 78 |
| merge mutation | 1 | 1 |
| immediate post-mutation proof reads | 5 | 5 |
| **total** | **36** | **162** |

The immutable capability ceiling is therefore 38 logical operations and 162
transmissions. No retry is included or permitted. The two unused logical slots
are not network-transmission authority.

The initial assessment must reserve at least 57 core requests plus 10 safety
and 20 GraphQL points plus 10 safety. The merge transaction must independently
reserve at least 63 core requests plus 10 safety and 20 GraphQL points plus 10
safety. Safety reserve is never dispatch authority. Local secondary-point
ceilings are 78 for assessment and 88 for merge/proof. Any ceiling change
requires a protocol revision.

## 19. Closed reason codes

The initial exact vocabulary is:

`TRUST_PIN_MISSING`, `TRUST_POLICY_INVALID`, `KEY_INVALID`, `SIGNATURE_INVALID`,
`CAPABILITY_INVALID`, `TARGET_NOT_DISPOSABLE`, `TARGET_PROHIBITED`,
`REPOSITORY_IDENTITY_MISMATCH`, `PR_IDENTITY_MISMATCH`, `PR_NOT_OPEN`,
`PR_DRAFT`, `HEAD_PROVENANCE_INCOMPLETE`, `HEAD_CHANGED`, `BASE_CHANGED`,
`GRAPHQL_IDENTITY_MISMATCH`, `GRAPHQL_UNSTABLE`, `PAGINATION_INCOMPLETE`,
`GRAPHQL_PAGE_PREFIX_INCOMPLETE`, `GRAPHQL_PAGE_CHAIN_INVALID`,
`GRAPHQL_PAGE_LIMIT_CONTINUATION`,
`GRAPHQL_COST_INVALID`,
`GRAPHQL_REMAINING_INVALID`,
`MERGEABILITY_NOT_CLEAN`, `MERGE_METHOD_UNAVAILABLE`, `PROTECTION_MISSING`,
`PROTECTION_CHANGED`, `STRICT_BASE_CONTROL_MISSING`, `RULESET_INCOMPLETE`,
`RULESET_CHANGED`, `LEGACY_BYPASS_INCOMPLETE`, `BYPASS_ACTOR_PRESENT`,
`PROTECTION_FREEZE_MISSING`, `PROTECTION_FREEZE_EXPIRED`, `CHECK_MISSING`,
`CHECK_NOT_SUCCESS`, `CHECK_AMBIGUOUS`, `REVIEW_MISSING`, `REVIEW_STALE`,
`REVIEW_DISMISSED`, `CHANGES_REQUESTED`, `SELF_REVIEW`, `BOT_REVIEW`,
`REVIEW_INDEPENDENCE_UNPROVEN`, `REVIEW_REQUEST_PENDING`,
`UNRESOLVED_CONVERSATION`, `CONTENT_TYPE_INVALID`, `RATE_EVIDENCE_INVALID`,
`RATE_HEADER_TRANSPORT_LOSSY`, `RATE_HEADER_COMMA_INVALID`,
`CORE_BUDGET_INSUFFICIENT`, `GRAPHQL_BUDGET_INSUFFICIENT`,
`RETRY_AFTER_SIGNAL`, `SECONDARY_LIMIT_SIGNAL`, `AUTHORIZATION_INVALID`,
`AUTHORIZATION_EXPIRED`,
`AUTHORIZATION_MISMATCH`, `PERMISSION_INSUFFICIENT`, `PERMISSION_EXCESSIVE`,
`TARGET_ALREADY_CLAIMED`, `TARGET_CLAIM_CONFLICT`,
`TARGET_CLAIM_PATH_UNUSABLE`, `TARGET_CLAIM_PATH_INVENTORY_STORE_FAILED`,
`TARGET_CLAIM_UNCERTAIN`, `LEASE_INVALID`,
`FINAL_REVALIDATION_CHANGED`, `ADMISSION_PERSISTENCE_FAILED`,
`MUTATION_CHAIN_INVALID`, `MUTATION_CHAIN_UNCERTAIN`,
`MUTATION_PREFIX_INVENTORY_STORE_FAILED`, `MUTATION_PREFIX_UNCERTAIN`,
`DISPATCH_ALREADY_ADMITTED`,
`MERGE_HTTP_REJECTED`, `MERGE_RESPONSE_FALSE`, `MERGE_RESPONSE_INVALID`,
`MERGE_REFUSAL_CLASS_INVALID`, `POST_MUTATION_PR_INVALID`,
`MUTATION_OUTCOME_AMBIGUOUS`, `POST_MERGE_PROOF_FAILED`,
`MERGED_ON_UNAUTHORIZED_BASE`, `MERGED_WITH_CONTROL_DRIFT`,
`MERGED_EXTERNALLY_OR_CONCURRENTLY_OBSERVED`, `READ_PREFIX_INCOMPLETE`,
`ARTIFACT_INVALID_OR_PARTIAL_PRESENT`, `OUTCOME_UNKNOWN`,
`TERMINAL_STORE_FAILED`, `RECEIPT_STORE_FAILED`.

Diagnostics contain safe IDs, hashes, counts, booleans, timestamps, and these
codes only. Raw bodies/headers, provider messages, names, URLs, cursors,
emails, tokens, cookies, App keys/JWTs, credential tags, selectors, and private
paths are excluded.

## 20. Required deterministic acceptance evidence

### 20.1 Record, trust, and lifecycle integrity

Tests must prove exact closed fields/types/bounds/nullability/enums; canonical
bytes/hashes; domain-separated Ed25519 verification for all signed families;
positive vectors and wrong-key, wrong-domain, malformed-length, padding,
noncanonical, expired, future, revoked, substituted-profile, and changed-trust-
pin negatives; acyclic references; permanent target exclusion; operation claim
exclusion; insert-once conflicts; crash/restart reconstruction; and no mutable
state transition. Every terminal prefix variant, target-claim path state,
target-claim unusable/uncertain terminal, mutation-chain-uncertain terminal,
target-claim-path-inventory-store-failed, mutation-prefix-inventory-store-
failed, terminal-store-failed, and receipt-store-failed capsule variant,
artifact-absent inventory, target- and mutation-prefix accounting variant, later
reconciliation chain, and ambiguity
confirmation with no response result must have positive and predecessor-
missing/substituted negative cases.

The locked `cryptography==49.0.0` distribution and its exact wheel/sdist hashes
must be retained. Tests must run the same vectors on Windows, macOS, and Linux.

### 20.2 API, race, and abuse evidence

Tests cover every master threat plus:

- caller-selected GraphQL, alias/fragment/directive/introspection/mutation,
  wrong content type/status, top-level errors/extensions, partial/null data,
  identity change, cursor loop, duplicate thread, changed `updatedAt`, reordered
  pages, skipped/repeated/cross-pass cursor, page-admission/body-hash mismatch,
  page-one non-null predecessor, later-page null predecessor, page-result
  predecessor splice, cost zero, non-decreasing same-window remaining,
  stable-state/rate-fact confusion, exact
  1,000-item completion, page-10 continuation retained as ten complete pairs,
  forbidden page-11 admission, partial page-result after valid admission, and
  the complete nine-state admission/result path product at every suffix
  ordinal; zero-pair all-absent canonicalization to `lease_present`; corrupted
  earlier pairs with retained later artifacts; artifacts after a completed
  page; and chain-invalid valid artifacts;
- core/GraphQL bucket substitution, cost above one, boundary reserve, primary
  exhaustion, duplicated rate-read accounting, validation-before-precedence,
  valid plus malformed/duplicate mixed rate headers across every response
  status, every observable secondary-limit signal, and proof that no model
  decides rate behavior;
- incomplete organization/legacy bypass, App/user/team/admin bypass, disabled
  admin enforcement, false empty sets, trust/control-lease substitution,
  missing/forged/late closeout, and control change before closeout;
- self/bot/stale/dismissed/replayed review, pending request, requested changes,
  missing pusher provenance, head changed away-and-back, and independence
  substitution;
- base/head/protection/ruleset/check/review/thread/trust/key/rate races after
  readiness, after authorization, after claim, during final revalidation, and
  at the final admission boundary;
- duplicate authorizations targeting one PR, concurrent processes, existing
  equal/unequal target claims, crash before/during admission persistence and
  after admission/response; target-claim create failure with absent, partial,
  invalid, or later-corrupted claim bytes; concurrent target inventory;
  unusable target-inventory write/capsule failure; same-process proven-zero
  versus restart conservative-one accounting; corrupted admission with
  retained result; path-valid but chain-invalid admission/result artifacts;
  mutation-prefix inventory write/capsule failure; and replay;
- omitted/substituted `sha`, method, endpoint, body field, origin, permission,
  noncanonical key order, or sync semantics;
- 200/false, every documented status-refusal projection, arbitrary provider
  error text discard, every media/rate class, every accepted and rejected
  media grammar production, duplicate parameters, quoted/escaped parameters,
  deterministic rate classification on every status; raw ASCII-case-insensitive
  field-name matching; differently cased duplicate lines; comma-coalesced
  target values; a deliberately lossy last-value-only adapter; each header
  mutant crossed with every response-status class on Windows, macOS, and Linux
  and rejected before value precedence; valid `Retry-After` on 200 and every
  refusal status; malformed/duplicate-key refusal JSON; malformed success,
  timeout, disconnect, oversized body, result-store failure, terminal-store
  failure, receipt-store failure, invalid/partial-present artifacts, artifact-
  absent authorization, interrupted REST/GraphQL read prefixes, ambiguity
  confirmation without result, external/concurrent merge after refusal, and
  ambiguous reconciliation; and
- later benign base advancement proved by compare, divergence, unauthorized
  first parent, and control drift.

Every critical gate has an enumerated mutation operator and test ID. A
vulnerable mutant must fail while the protected implementation passes. A test
that never reaches the intended production gate or dispatch admission is
vacuous and fails evidence generation.

### 20.3 Production-path loopback and network denial

Source-only loopback must exercise the exact production request encoder,
credential-header encoder, TLS/hostname validator, proxy/redirect refusal,
bounded reader, lossless raw header-occurrence adapter, duplicate-key JSON
parser, REST/GraphQL projections, rate
admission, persistent claim/admission/result/terminal state machine, and
credential cleanup. The source-only constructor is unavailable in installed
artifacts.

CI denies external networking and proves no request reaches `api.github.com`.
Fixtures use only reserved local addresses and cannot contain a live
repository identifier or credential. At least one instrumented success path
must prove exactly one mutation dispatch; negative paths must prove zero or one
as specified, never pass by avoiding the exercised path.

### 20.4 Installed-package and four-platform evidence

At the exact implementation head and again on protected `main`, retain:

- Windows/Python 3.12, macOS/Python 3.12, Ubuntu/Python 3.12, and
  Ubuntu/Python 3.13 JUnit and conformance records;
- exact commit/tree, wheel, sdist, lockfile, and installed-inventory hashes;
- isolated `python -I` installed-wheel fixture conformance outside the source
  tree;
- exact Stage 21C module/projection/schema inventories in versioned
  `conformance_evidence` and `installed_wheel_probe` tools;
- static, secret, credential-sentinel, private-identifier, raw-response,
  network-denial, and package-member scans; and
- zero Stage 21C skip/xfail, with unrelated inherited platform skips allowed
  only by exact test-ID and reason allowlist.

No fixture transport, cassette, source-only loopback helper, raw GitHub body,
credential, private App material, or live repository identifier may ship.

## 21. Implementation order after separate authority

Only after exact-draft Council pass, Arthur freeze, and separate implementation
authorization:

1. exact primitives, invariant schemas, trust policy, and signing verification;
2. capability overlay, external attestations, and head provenance;
3. additive operation authorization/intent/claim/lease/observation records and
   target-claim path inventory/evidence union;
4. closed REST extensions, GraphQL query, per-page admission/result chain,
   stable-state projection, ordered rate facts, and rate buckets;
5. deterministic readiness reducer;
6. merge authorization, plan, permanent target claim, target-path recovery,
   and revalidation;
7. merge-specific intent, mutation operation claim, lease, raw lossless-header
   extraction, mutation-prefix inventory, admission, one-send transport, and
   result;
8. proof/ancestry, terminal/receipt/capsule/ledger, and reconciliation;
9. adversarial mutants, crashes, races, package/leak/network tests; and
10. exact-head and protected-main four-platform Council evidence.

Every correction remains on an isolated branch and is re-reviewed. No layer
becomes live because a later layer exists.

## 22. Council re-review questions

Each seat must independently answer:

1. Do additive `0.2.0` records leave frozen Stage 21A and 21B unchanged?
2. Are every family, trust root, signature, effect, and reference closed and
   acyclic?
3. Does the permanent repository/PR target claim prevent cross-authorization,
   cross-session, crash, and concurrent duplicate merge attempts, and can an
   unusable claim path close without a valid claim reference or replacement?
4. Are ruleset, legacy protection, administrator, and every acting bypass path
   independently complete and externally frozen through the response?
5. Are the GraphQL query, identity, per-page request/cursor chain, stable-state
   comparison, separate rate facts, parser, rate cost, and exact-boundary rules
   implementable and fail-closed?
6. Do the separate core and GraphQL budgets reconcile exactly to the operation
   plan with no hidden retry?
7. Is head-pusher provenance complete without introducing broad audit access
   into CONCLAVE?
8. Does the protocol honestly expose GitHub's head-only mutation precondition,
   enforce strict server-side base currency, and classify residual base/control
   races without calling them success?
9. Can confirmed merge and later reconciliation prove containment after the
   base advances?
10. Are every operation claim, read and mutation crash prefix, absent-result
     ambiguity, target-path failure, chain-invalid mutation artifact, refusal
     response, terminal, storage-failure, reconciliation, and ledger state
     append-only and reconstructable without inference, with one exclusive
     state and conservative transmission accounting?
11. Does the disposable-target overlay make KOS, IDM, CONCLAVE `main`, client,
    and production operation impossible?
12. Are loopback, installed-wheel, cross-platform, mutation-operator, lossless-
     header, rate, package, network, and leak tests non-vacuous?

Verdicts are `PASS_EXACT_DRAFT`, `FAIL_EXACT_DRAFT`, or `ABSTAIN`, bound to the
exact SHA-256 and Git blob. Freeze requires 5/5 PASS, no blocker, and Arthur's
explicit exact-draft decision.

## 23. Rollback and failure rules

- Before freeze, correction produces a new exact draft and full re-review.
- After freeze, protocol changes require a governed erratum or replacement.
- An existing target claim is never removed, reused, or taken over.
- An admitted mutation is never repeated under any authorization.
- A merged result is factual and is never erased by reset, force push,
  deletion, or history rewrite.
- A bad merge requires a new governed corrective PR outside Stage 21C.
- Protection obstruction is recorded; CONCLAVE never alters it.
- Credential suspicion triggers external revocation and sanitized incident
  handling; secrets never enter evidence.
- Storage failure never authorizes another request.

## 24. Official factual references

Consulted on 2026-09-10. These describe GitHub behavior and grant no authority:

- synchronous merge endpoint, conditional head `sha`, explicit merge method,
  response statuses, token compatibility, and Contents-write permission:
  `https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request`
- pull-request reviews:
  `https://docs.github.com/en/rest/pulls/reviews`
- requested reviewers:
  `https://docs.github.com/en/rest/pulls/review-requests#get-all-requested-reviewers-for-a-pull-request`
- check runs:
  `https://docs.github.com/en/rest/checks/runs`
- commit statuses:
  `https://docs.github.com/en/rest/commits/statuses`
- compare commits and Contents-read permission:
  `https://docs.github.com/en/rest/commits/commits#compare-two-commits`
- GraphQL PR identity, updated time, merge state, review decision, review
  threads, and resolution fields:
  `https://docs.github.com/en/graphql/reference/pulls`
- GraphQL connection pagination:
  `https://docs.github.com/en/graphql/guides/using-pagination-in-the-graphql-api`
- GraphQL primary/secondary point behavior and observable limit responses:
  `https://docs.github.com/en/graphql/overview/rate-limits-and-query-limits-for-the-graphql-api`
- REST `core` and `graphql` rate buckets:
  `https://docs.github.com/en/rest/rate-limit/rate-limit`
- REST primary/secondary rate-limit behavior and the absence of a query for
  secondary-limit status:
  `https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api`
- GitHub App least privilege and GraphQL permission behavior:
  `https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app`
- branch protection:
  `https://docs.github.com/en/rest/branches/branch-protection`
- repository rulesets:
  `https://docs.github.com/en/rest/repos/rules`
- organization rulesets:
  `https://docs.github.com/en/rest/orgs/rules`
- GitHub App endpoint-permission mapping:
  `https://docs.github.com/en/rest/authentication/permissions-required-for-github-apps?apiVersion=2026-03-10`

## 25. Remediation traceability

Council Review 0001 findings are closed in this draft as follows:

| Review 0001 blocker | Remediation |
| --- | --- |
| frozen 21A cannot express 21C | additive profiles, endpoints, projections, authorizations, intents, claims, leases, and observations in §§4, 8–11 |
| schemas/effects incomplete | normative primitives and exact common/family fields in §§3–8, 12–17 |
| signer profiles unanchored | external trust-root pin and trust policy in §5 |
| mutable/circular attempt | predecessor-only append-only chain in §§13–17 |
| authorization-scoped concurrency | permanent repository/PR target claim in §13.3 |
| legacy bypass incomplete | complete legacy/ruleset/admin evidence in §7.3 |
| final race window | target claim, final order, strict server control, protection-freeze lease, and explicit residual classification in §§7.4, 12–16 |
| GraphQL identity/stability/transport incomplete | immutable node IDs, exact raw contract, two full passes, fixed query/hash in §10 |
| rate buckets and ceiling wrong | separate core/GraphQL evidence and exact named-operation 36/162 arithmetic in §18 |
| latest pusher unobservable | Stage-21B-bound independent head provenance in §7.1 |
| post-merge PR omitted merge OID | additive post-merge projection in §11 |
| later base advance unrecoverable | compare/ancestry proof in §16 |
| terminal and ledger truth incomplete | exact append-only terminal/receipt/capsule/ledger rules in §17 |
| live target unrestricted | separately signed disposable-only overlay in §6 |
| conformance could be vacuous | production-path loopback, mutants, installed wheel, exact inventories, and four-platform evidence in §20 |

Council Review 0002 findings are closed in this draft as follows:

| Review 0002 blocker | Remediation |
| --- | --- |
| GraphQL page bodies/cursors unbound | pre-send page admission plus immutable page result and ordered pass chain in §§8.6 and 10 |
| stable equality included changing rate facts | separate stable-state and ordered rate-fact aggregates in §§8.5, 8.6, and 10 |
| mutation operation claim missing | claim inserted and cross-bound before lease throughout §§8.3 and 14–17 |
| zero-transmission prefixes incomplete | prefix-complete lifecycle union and inventory in §17 |
| ambiguity confirmation required result | result-optional `MERGED_CONFIRMED_AFTER_AMBIGUITY` rule in §17.1 |
| reconciliation could not start without terminal artifact | matching terminal/capsule/unusable-with-inventory union in §§16.4 and 17.2 |
| terminal/receipt storage and later chain incomplete | exact failure variants and appended reconciliation reconstruction in §§17.4–17.5 |
| non-200 refusal projections absent | closed success/refusal/ambiguous response variants in §15.4 |

Council Review 0003 findings are closed in this draft as follows:

| Review 0003 blocker | Remediation |
| --- | --- |
| post-mutation negative projection impossible | closed `merged_pr | unmerged_pr` projection in §11 |
| merge observed after refusal unrepresentable | non-attributing incident outcome in §§16.3 and 17.1 |
| canonical merge-body key order contradicted | exact key set and canonical sorted order in §15.3 |
| GraphQL page-one predecessor implicit | exact null-iff-page-one rule in §8.6 |
| refusal media/rate classifier open | closed enums and deterministic status/header precedence in §15.4 |
| GraphQL zero cost and weak remaining check | literal cost one and same-window decrement rule in §§10 and 18 |
| rate read double-counted and plan unnamed | one named 15-operation/78-transmission cycle including mandatory profile verification and exact 36/162 total in §§9, 14, and 18 |
| interrupted read/page prefixes absent | closed read-prefix inventory propagated through §§8.7 and 12–17 |
| not-merged wording excluded local refusal result | remote-commit distinction and permitted refusal result in §16.3 |
| partial-present artifacts unrepresentable | three-state artifact inventory and unusable-artifact union in §§8.7 and 16–17 |

Council Review 0004 findings are closed in this draft as follows:

| Review 0004 blocker | Remediation |
| --- | --- |
| page-10 continuation prefix unrepresentable | incomplete GraphQL inventory admits exactly ten complete pairs only with page-10 continuation and forbids page 11 in §8.7 |
| partial page-result path implicit | exact terminal-page-state tuple closes valid, absent, and invalid/partial admission/result combinations in §8.7 |
| `Retry-After` could evade stop rule | status-independent precedence makes every valid `Retry-After` a blocking secondary-limit signal in §15.4 |
| `other_valid` media grammar open | explicit bounded ASCII token grammar, parameter rules, and parser independence in §15.4 |

Council Review 0005 findings are closed in this draft as follows:

| Review 0005 blocker | Remediation |
| --- | --- |
| mixed rate-header precedence contradictory | mandatory all-field validation completes before ordered valid-field/status classification in §15.4 |
| zero-page GraphQL prefix overlapped | all admission/result paths through ordinal 10 must be absent for `lease_present`; any artifact selects `graphql_pages_incomplete` in §8.7 |
| GraphQL artifact corruption states incomplete | longest valid prefix plus fixed nine-state-per-ordinal suffix retains all later artifacts while separating presence from chain validity in §8.7 |
| mutation admission proof unbound | additive mutation-prefix inventory is required by terminal, capsule, receipt, reconciliation, and ledger records in §§8.9 and 16–17 |
| restart could falsely assert zero transmission | same-process pre-dispatch proof is the only zero path; restart/recovery conservatively consumes one and records unknown in §§8.9 and 17 |

Council Review 0006 findings are closed in this draft as follows:

| Review 0006 blocker | Remediation |
| --- | --- |
| GraphQL zero-page variant still overlapped retained later artifacts | `lease_present` now requires every admission/result path for ordinals 1–10 absent; every later artifact selects only the fixed-suffix incomplete variant in §8.7 |
| chain-invalid mutation artifacts had no terminal | `mutation_chain_uncertain` consumes one conservatively, trusts no invalid chain reference, records unknown/non-attributed, forbids retry, and propagates through every recovery family in §§8.9 and 16–17 |
| unusable permanent target path had no evidence closure | immutable target-path inventory and target-evidence union cover valid, absent, invalid/partial, store-failure, terminal, reconciliation, receipt, and ledger paths without granting mutation authority in §§8.8, 13.3, and 16–17 |
| header occurrence input could hide rate signals | lossless pre-normalization field occurrence stream, ASCII-insensitive name matching, duplicate preservation, comma rejection, and lossy-adapter failure precede value classification in §15.4 |

## 26. Current disposition

This is a local remediated protocol draft only. The six rejected exact
objects and their findings remain preserved in
`INCREMENT-21C-COUNCIL-REVIEW-0001.md`,
`INCREMENT-21C-COUNCIL-REVIEW-0002.md`, and
`INCREMENT-21C-COUNCIL-REVIEW-0003.md`, and
`INCREMENT-21C-COUNCIL-REVIEW-0004.md`, and
`INCREMENT-21C-COUNCIL-REVIEW-0005.md`, and
`INCREMENT-21C-COUNCIL-REVIEW-0006.md`.

This draft is not frozen, committed, pushed, or implemented. No credential,
live target, trust key, signature, GitHub App, API operation, repository
mutation, merge, deployment, production use, KOS/IDM change, identity, or
membership action has occurred or is authorized. The next gate is a new exact-
hash five-seat Council review.
