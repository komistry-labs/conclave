# CONCLAVE Stage 21B — Bounded Branch and Pull-Request Publication Protocol

## Status

Council-review candidate · unfrozen · uncommitted · local only

This document is subordinate to the frozen Increment 21 master protocol and
does not alter Stage 21A. It is a protocol candidate, not implementation or
operational authority. It authorizes nothing by its own existence.

## 0. Basis and entry condition

Stage 21B begins only after the exact Stage 21A implementation is reviewed,
merged to protected `main`, and verified by the required cross-platform CI.
Until that gate is satisfied, this candidate may be reviewed but not frozen,
implemented, exercised, or used to publish any repository content.

The Stage 21A implementation branch was locally verified and published for
review. No Stage 21B code, credential, GitHub mutation, branch, or pull request
has been created by preparing this document.

## 1. Objective

Stage 21B permits one separately authorized publication transaction to:

1. reproduce one exact governed proposal as Git objects derived from one exact
   base commit;
2. create one new task-scoped non-protected branch at the exact proposal
   commit; and
3. create one pull request from that branch to the authorized base branch.

The publication is a proposal. It has no approval, decision, merge,
constitutional, KOS, IDM, identity, membership, deployment, or production
effect.

## 2. Selected publication mechanism

Stage 21B selects bounded GitHub REST Git-database operations over Git
smart-HTTP transport.

The decision is specific to Stage 21B because REST:

- reuses the Stage 21A fixed `https://api.github.com` origin, TLS policy,
  credential lease, request encoder, bounded reader, and closed projections;
- exposes each created blob, tree, commit, reference, and pull request as a
  separately hash-bound factual result;
- allows local computation and comparison of Git object identifiers before a
  branch becomes visible;
- avoids subprocess Git, credential helpers, askpass programs, remote URL
  credential injection, pack protocol negotiation, and packfile parsing; and
- admits a closed endpoint table and deterministic fixture evidence.

This decision does not authorize the REST endpoints. It freezes the mechanism
to be implemented only after a separate implementation authorization.

## 3. Maximum boundary

One publication transaction has these hard ceilings:

| Limit | Value |
|---|---:|
| repositories | 1 |
| base refs | 1 |
| new head refs | 1 |
| proposal commits | 1 |
| pull requests created | 1 |
| changed regular files | 64 |
| bytes per file before base64 | 2 MiB |
| aggregate proposal bytes before base64 | 8 MiB |
| path bytes per file | 512 UTF-8 bytes |
| commit-message bytes | 4 KiB UTF-8 |
| pull-request-title bytes | 256 UTF-8 |
| pull-request-body bytes | 64 KiB UTF-8 |
| total mutation requests | file count + 4; maximum 68 |
| repository-identity recheck requests | file count + 4; maximum 68 |
| total read and mutation requests | 2 x file count + 14; maximum 142 |
| rate-limit safety reserve | 10 additional requests |
| automatic mutation retries | 0 |
| authorization lifetime | at most 15 minutes |
| publication operation timeout | 10 minutes monotonic |

Directories, symlinks, submodules, executable-mode changes, deletions, renames,
Git LFS pointer generation, and binary-to-text conversion are excluded from
the initial 21B surface. Every proposal entry is one regular file with mode
`100644`, type `blob`, and content supplied to GitHub as canonical base64.

The following are absent by construction:

- updating or deleting any existing ref;
- creating tags or annotated tag objects;
- writing to the default branch or any protected/ruleset-targeted branch;
- editing `.github/**`, `CODEOWNERS` at any location, branch/ruleset controls,
  governance authority files, credential files, or repository settings;
- force, merge, rebase, squash, auto-merge, merge queue, review submission,
  reviewer assignment, labels, milestones, assignees, comments, or issue
  conversion;
- fork or cross-repository publication;
- draft-PR creation, `maintainer_can_modify:true`, or multiple pull requests;
- personal access tokens, OAuth user tokens, GitHub App user tokens, ambient
  credentials, Git credential helpers, or CLI authentication; and
- automatic cleanup, branch deletion, PR closure, or mutation retry.

## 4. Governing input chain

Before credential resolution, one publication transaction is constructed in
this strictly acyclic order. Every later record binds predecessor references
and content hashes; no predecessor names or hashes a successor:

1. frozen Increment 21 and 21B protocol hashes;
2. exact Stage 21A repository and API profiles;
3. Task Packet and its accepted version;
4. Handoff packet naming the exact proposal artifact set;
5. scope review with an accepted result and exact allowed paths;
6. exact local base observation: repository numeric identity, full base ref,
   base commit OID, base tree OID, object format, protection/ruleset projection,
   and observation time;
7. exact rate-limit observation reference/hash from §11.1, bound to the same
   repository/API profile, account, App, installation, credential provider,
   provider-key reference/hash and public-key fingerprint, API version, and
   applicable GitHub resource bucket;
8. proposal manifest from §5;
9. configured-human publication authorization from §6;
10. publication plan from §7.1;
11. publication attempt ID computed from items 1–10;
12. generic operation intent from §7.2;
13. publication intent from §7.3;
14. exclusive attempt claim from §7.4; and
15. credential-lease evidence, step records, receipt, and ledger event, each
    referencing predecessors only.

Missing, stale, reordered, circular, differently hashed, or identity-mismatched
input fails before credential resolution. Advisory-agent output cannot supply
the human publication authorization.

### 4.1 Common durable-record invariant

Every 21B durable record named by this protocol—including manifest,
authorization, rate observation, plan, generic intent, publication intent,
claim, lease evidence, step admission, step result, terminal failure capsule,
publication receipt, and reconciliation records—has:

- one exact profile/schema-version discriminator and no unknown keys;
- strict JSON scalar/array/object types, explicit nullability, closed enums,
  and per-field byte/item bounds;
- canonical UTF-8 JSON serialization with lexicographically sorted object keys,
  no insignificant whitespace, duplicate keys, floats, non-finite values, or
  Unicode normalization ambiguity;
- a domain-separated `sha256:` content hash computed with the content-hash
  field absent;
- a deterministic workspace-relative filename derived only from its safe ID
  or content hash;
- predecessor-only reference/hash links following the acyclic order in §4;
- the Stage 21A immutable final-path create, platform durability barrier,
  close/reopen byte verification, and content-hash verification; and
- idempotent equal-content handling only where expressly permitted, while an
  exclusive claim/admission or unequal existing content fails closed and
  retains the existing bytes.

No record is amended, completed in place, deleted, or treated as authoritative
because it was stored. Each schema's listed fields are mandatory unless this
protocol explicitly marks one nullable.

## 5. `github-proposal-manifest/0.1.0`

The proposal manifest is closed-schema, canonical, content-hashed, immutable,
and contains only:

- manifest ID and creation time;
- repository/API-profile references and hashes;
- repository numeric ID and account numeric ID;
- full base ref, exact base commit OID, and exact base tree OID;
- full proposed head ref;
- Git object format from the repository profile;
- Task Packet, Handoff, and scope-review references and hashes;
- sorted file entries, each containing normalized repository-relative path,
  mode `100644`, byte count, `sha256:` content hash, locally computed Git blob
  OID, and an artifact reference outside the manifest;
- sorted allowed paths copied exactly from the accepted scope review;
- aggregate byte count and aggregate manifest hash;
- exact commit-message hash and byte count;
- exact bounded commit-author and committer artifact reference/hash, using
  explicit name, email, and second-precision timestamp fields needed to
  reproduce the Git commit object; author and committer must be equal;
- exact pull-request-title hash and byte count;
- exact pull-request-body hash and byte count;
- exact title/body artifact references whose bytes are re-read and verified
  against those hashes before credential resolution;
- locally computed proposal tree OID and commit OID;
- `proposal_only:true`, `merge_authorized:false`,
  `action_execution_allowed:false`, and all authority/decision/membership
  effects set to `none`.

The artifact reader uses descriptor-relative, no-follow semantics where the
platform supports them, rejects reparse points/symlinks and path escapes, reads
each file at most once into a bounded buffer, and verifies its byte count and
hash immediately before credential resolution. Case-fold and Unicode-normalized
path collisions are rejected. Paths use NFC UTF-8 and `/`; absolute paths,
`.`/`..`, empty segments, controls, backslashes, percent escapes, trailing dot
or space segments, reserved Windows device names, and `.git` segments are
rejected.

The initial prohibited-path set is:

- `.github/**`;
- `CODEOWNERS`, `.github/CODEOWNERS`, `docs/CODEOWNERS`;
- `.gitmodules`, `.gitattributes`, `.gitignore`;
- `.env`, `.env.*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.pkcs12`;
- `docs/governance/**`, `architecture/decisions/**`, `adr/**`;
- KOS, IDM, Constitution, membership, identity, trust-domain, signing, key,
  credential, branch-protection, ruleset, deployment, workflow, release, and
  production control records as classified by the repository profile.

Any later exception requires a new protocol decision; a publication
authorization cannot override this set.

### 5.1 Head-ref convention and policy observation

The full head ref is ASCII and matches exactly:

`refs/heads/conclave/<task-uuidv7>/<slug>`

`<task-uuidv7>` is the Task Packet identifier. `<slug>` is 1–48 lowercase
ASCII letters, digits, or single hyphens, beginning and ending alphanumeric.
The full ref is at most 160 ASCII bytes. Empty segments, repeated hyphens,
leading/trailing slash, `.`, `..`, `@{`, `~`, `^`, `:`, `?`, `*`, `[`, `\\`,
controls, spaces, percent escapes, Unicode, and `.lock` endings are refused.

Before credential resolution, a current complete Stage 21A ruleset observation
and branch-rules observation for the proposed head name must show that it is
not protected and no applicable rule prohibits creation. Unknown, incomplete,
permission-limited, or unrecognized security state fails closed. The 21B
repository-profile extension carries the exact allowed head prefix and exact
prohibited path patterns; neither is caller-supplied at execution time.

## 6. `github-publication-authorization/0.1.0`

The configured human principal creates one expiring authorization containing:

- authorization ID, issuing principal, issued-at, expires-at, and purpose;
- exact protocol, repository profile, API profile, proposal manifest, Task
  Packet, Handoff, scope review, and base-observation hashes;
- exact rate-limit observation reference/hash and its repository/API-profile,
  account/App/installation/provider/provider-key-reference/provider-key-hash/
  public-key-fingerprint/API-version/resource-bucket scope;
- repository/account/App/installation numeric IDs;
- full base and head refs, base commit/tree OIDs, proposal tree/commit OIDs;
- exact sorted allowed paths and aggregate proposal hash;
- commit-message, PR-title, and PR-body hashes and byte counts;
- `publication_mechanism:"github_rest_git_database"`;
- exact permission envelope: Metadata read, Contents write, Pull requests
  write, and every other permission `none`;
- `maximum_publication_transactions:1`, `maximum_branch_creations:1`,
  `maximum_pull_requests:1`, `maximum_mutation_requests:<file-count + 4>`,
  `maximum_total_requests:<2 x file-count + 14>`, and
  `automatic_mutation_retries:0`;
- `maintainer_can_modify:false`, `draft:false`;
- `merge_requested:false`, `merge_authorized:false`;
- `authority_effect:"github_publish_proposal_only"`; and
- decision and membership effects `none`, production use false.

The authorization lifetime is 1–900 seconds. It expires at the earlier of its
own expiry, any upstream authorization expiry, or the monotonic transaction
deadline. It cannot authorize a different proposal with the same branch name.

## 7. Acyclic plan, intent, and exclusive claim

### 7.1 Publication plan

`github-publication-plan/0.1.0` is constructed from §§4–6 before any attempt ID
or generic intent exists. It contains all upstream references/hashes; the exact
rate observation and scope; sorted blob request hashes and expected OIDs; tree,
commit, ref, and PR request hashes; expected tree/commit OIDs; base/head refs;
closed ordered endpoint plan; exact request ceilings; and zero-retry rule. It
names no attempt ID, generic operation intent, publication intent, claim,
lease, dispatch/result record, receipt, or ledger event.

The attempt ID is:

`publication:sha256:<hex(sha256(domain || canonical_preimage))>`

with domain `CONCLAVE-GITHUB-PUBLICATION-ATTEMPT-V1\0`. The preimage binds every
input and limit in §§4–6 plus the publication-plan content hash. It contains
no attempt ID and no successor hash.

### 7.2 Generic operation intent

`github-operation-intent/0.2.0` represents the complete multi-request
publication transaction. It binds the §6 authorization, §7.1 publication plan,
computed attempt ID, exact ordered endpoint plan, canonical request-body
hashes, request ceilings, zero-retry rule, and exact rate-limit observation
reference/hash and scope. It names no publication intent or later record.

Version `0.2.0` is additive for 21B mutation plans. It does not replace or
reinterpret the frozen read-only `github-operation-intent/0.1.0` used by 21A.

### 7.3 Publication intent

`github-publication-intent/0.1.0` contains:

- publication-plan and generic operation-intent references/hashes and the
  publication attempt ID;
- all upstream references/hashes from §4;
- exact rate-limit observation reference/hash and complete scope, equal to the
  authorization and generic intent;
- exact blob request hashes in sorted path order;
- exact expected blob OIDs;
- exact tree, commit, ref, and PR request hashes;
- exact expected tree/commit OIDs;
- base and head refs and the base/proposal commit OIDs;
- the closed endpoint plan and maximum counts;
- `state:"prepared"`, zero automatic retries, and no authority effects.

It is durably sealed before the attempt claim and before credential resolution.

### 7.4 Attempt claim

`github-publication-attempt-claim/0.1.0` uses an exclusive final-path create.
It binds the publication plan, generic intent, publication intent, attempt ID,
rate observation, provider-key reference/hash/public-key fingerprint,
authorization, and every upstream record by reference/hash.
Any existing claim blocks credential resolution, whether its bytes are equal,
different, partial, or crash-retained. Equal content yields
`PUBLICATION_ALREADY_CLAIMED`; unequal content yields
`PUBLICATION_CLAIM_CONFLICT`. Claims are never deleted or reused.

## 8. Closed endpoint table and order

Only these mutation endpoints exist in Stage 21B:

| Key | Method and fixed route | Accepted success | Permission |
|---|---|---|---|
| `git_blob.create` | `POST /repos/{owner}/{repo}/git/blobs` | `201` | Contents write |
| `git_tree.create` | `POST /repos/{owner}/{repo}/git/trees` | `201` | Contents write |
| `git_commit.create` | `POST /repos/{owner}/{repo}/git/commits` | `201` | Contents write |
| `git_ref.create` | `POST /repos/{owner}/{repo}/git/refs` | `201` | Contents write |
| `pull_request.create` | `POST /repos/{owner}/{repo}/pulls` | `201` | Pull requests write |

No update-reference, delete-reference, contents-file, tag, merge, review,
comment, issue, workflow, repository-settings, branch-protection, ruleset,
GraphQL, upload, redirect, or caller-selected route is present.

These supporting reads are also closed and credential-bound. Existing Stage
21A projections are reused where named:

| Key | Method and fixed route | Accepted success | Purpose |
|---|---|---|---|
| `repository.get` | Stage 21A route | `200` | numeric repository/account identity and profile recheck immediately before each mutation |
| `ref.get` | Stage 21A route | `200` | exact base/head binding |
| `matching_refs.list` | `GET /repos/{owner}/{repo}/git/matching-refs/{ref}` | `200` | positive empty/non-empty head test |
| `pull_requests.matching.list` | `GET /repos/{owner}/{repo}/pulls` with fixed `state=all`, exact `head`, exact `base`, `per_page=2`, `page=1` | `200` | duplicate-PR refusal and post-create identity |
| `pull_request.get` | Stage 21A route | `200` | post-create exact identity |

An empty matching-reference array is accepted as head absence only while an
exact repository/base-ref observation succeeds in the same transaction and
the authenticated lease remains valid. A 404 is never treated as proof of
absence.

The order is fixed:

1. immediately before each sorted manifest path, read the repository identity,
   require exact numeric repository/account identity and repository/API-profile
   hashes, then create that one blob;
2. read and require that same repository identity, then create one tree using
   the exact base tree and created blob OIDs;
3. read and require that same repository identity, then create one commit with
   the exact tree and sole parent base commit;
4. read the exact base ref and matching head refs, proving the head is still
   absent and base still equals the authorized base commit;
5. read and require that same repository identity, then create the new full
   head ref at the exact proposal commit;
6. read the exact head/base refs and matching PRs, proving the new ref exists
   at the exact proposal commit, base remains unchanged, and no PR already
   exists for the exact head/base; and
7. read and require that same repository identity, then create one pull request
   with exact title/body, `head` equal to the local branch name, exact `base`, `draft:false`, and
   `maintainer_can_modify:false`; then
8. read the created PR by its returned numeric ID and require exact repository,
   head, base, title/body hashes, and proposal commit identity.

The read reconciliations have their own bounded factual observations and do
not consume mutation retry authority. Failure or ambiguity at any step stops
the plan; later steps do not run.

Every repository-identity recheck is a closed Stage 21A factual observation.
An incomplete observation, read failure, changed numeric repository/account
identity, or repository/API-profile mismatch stops before the adjacent mutation.
Its reference/hash is bound into that mutation's step admission, step result
when present, and the terminal receipt or failure capsule. No earlier
observation, lease claim, matching owner/name text, or cached transport result
may substitute for the immediately preceding recheck.

## 9. Request construction and exact object verification

All requests use the Stage 21A API version, media type, fixed origin, fixed
host, environment-proxy refusal, TLS verification, response limits, safe
diagnostics, and no caller URL/header injection.

Blob bodies contain only `content:<canonical RFC 4648 base64>` and
`encoding:"base64"`. Required `=` or `==` padding is retained; whitespace,
line wrapping, alternate alphabets, and non-canonical encodings are refused.
The locally computed Git blob OID must equal the closed response projection.
Tree bodies contain exact sorted path/mode/type/OID
entries and `base_tree` equal to the authorized base tree. Null SHA and inline
content are prohibited. Commit bodies contain only exact bounded message,
tree OID, sole-parent base commit OID, and the required equal
author/committer projections from the manifest. The protocol supplies no
signature, infers no verified authorship, and retains GitHub's verification
result only as a factual projection. Root commits, multiple parents, implicit
server-selected identity/time, and different author/committer values are
prohibited.

The returned tree and commit OIDs must equal the locally computed expected
OIDs. The ref response must name the exact full new ref and proposal commit.
The PR response must match repository numeric ID, new head ref, proposal head
OID, base ref, and base OID. Raw response text, URLs, user display names,
emails, token material, and unbounded bodies are not retained.

If GitHub cannot reproduce the exact locally expected object identifier, the
transaction stops before ref creation. Created unreachable objects remain
factual remote objects and are not deleted.

## 10. Credential lease and transport

The only credential is one externally supplied GitHub App installation access
token, atomically paired with the provider-authenticated receipt and claims
required by Increment 21 and Stage 21A.

The durable lease evidence must additionally bind:

- the 21B protocol and publication authorization/intent/claim hashes;
- the publication plan and exact rate-limit observation reference/hash plus
  repository/API-profile, account/App/installation/provider/provider-key
  reference/hash/public-key-fingerprint/API-version and resource-bucket scope;
- repository/account/App/installation IDs;
- the exact permission envelope from §6;
- selected-repository scope for exactly one repository;
- the ordered endpoint plan and maximum mutation request count;
- zero retry; and
- `publication_started_at_evidence_creation:false`.

The token is admitted only after durable lease evidence and is consumed by one
publication transaction. It is held only in a mutable memory buffer, is never
converted to text outside the fixed Authorization-header encoder, and is
overwritten on every exit. Provider closure and cleanup failure are factual,
sanitized failures and never trigger another resolution.

Credential material cannot enter a Git remote URL, process arguments,
environment, filesystem, subprocess, Git configuration, credential helper,
exception, terminal, ledger, test report, archive, or CI artifact.

## 11. Mutation ambiguity and reconciliation

Immediately before each network dispatch, the adapter durably creates one
exclusive `github-publication-step-admission/0.1.0`. It binds the publication
attempt/claim, step ordinal and endpoint key, request-body hash, expected
object/ref/PR identity, local request budget before and after admission,
rate-observation hash, provider-key reference/hash/public-key fingerprint,
monotonic deadline class, `retry_allowed:false`, and
`state:"dispatch_admitted_not_confirmed"`. An existing record for that ordinal
blocks dispatch. Because a crash may occur after admission but before the
socket write, absence of a result record is conservatively ambiguous.
For a mutation dispatch, the admission additionally binds the accepted
repository-identity observation reference/hash from the directly preceding
`repository.get`. Read-dispatch admissions contain no repository-identity
recheck field, preventing a recursive requirement on the recheck itself.

After a complete accepted response and before any next step, the adapter
durably creates one `github-publication-step-result/0.1.0` binding the admission
record, accepted status, bounded response-projection hash, expected/observed
identity comparison, bounded per-response rate projection, completion time,
provider-key reference/hash/public-key fingerprint, and safe outcome. No next
step is admitted until this result is durable.
For a mutation response, the result also binds the same directly preceding
repository-identity observation reference/hash as its admission; read results
contain no such field.
Non-success HTTP responses also produce a bounded result but, because dispatch
occurred, their mutation outcome is `AMBIGUOUS`; `REFUSED` is reserved for a
provable pre-dispatch refusal with no network call. A transport loss,
process crash, or persistence failure after admission can leave admission
without result; the retained claim and admission block rerun.

No mutation is automatically retried, including failures reported before
response headers. A timeout, connection loss, cancellation, malformed success
body, status outside the closed success value, response-size failure, or crash
after dispatch makes that step `AMBIGUOUS` unless a retained accepted response
proves its result.

An ambiguous step stops the credential-bearing transaction and records only:
attempt and step IDs, request-body hash, expected object/ref/PR identity,
dispatch fact, safe reason code, and authority constants. It stores no raw
request content or response.

Later reconciliation is read-only and uses a new acyclic immutable chain:
`github-publication-reconciliation-authorization/0.1.0` authored by the
configured human principal, then reconciliation intent, exclusive claim,
credential-lease evidence, factual observations, and
`github-publication-reconciliation-receipt/0.1.0`. Every record binds the
original publication claim, the applicable ordered closed step-state entries
from §12, expected identity, and predecessors. An admission without a durable
result is represented only by the applicable `read_admitted_without_result` or
`mutation_admitted_without_result` variant; reconciliation may not synthesize,
infer, or insert result-only fields. It binds exactly one terminal-artifact
state: `receipt_present`, `failure_capsule_present`, or
`terminal_artifact_absent`. The absent state is permitted only when filesystem
inventory proves that neither terminal object exists and binds the original
claim plus the last durable admission/result hashes. The original record chain
is never amended. Reconciliation covers only the named ambiguous step:

- blob: read the expected OID and compare bounded bytes/hash;
- tree: read the expected tree and compare exact sorted entries/base result;
- commit: read the expected commit and compare tree, sole parent, and message
  hash;
- ref: read the exact full head ref and compare proposal commit;
- PR: list/search only within the exact repository and head/base selectors,
  then require exactly one matching PR with matching title/body hashes and
  proposal head.

Reconciliation may classify the step as `CONFIRMED_CREATED`,
`CONFIRMED_ABSENT`, `CONFLICTING_REMOTE_STATE`, or `STILL_AMBIGUOUS`. It never
continues the original transaction or repeats a mutation. Any continuation
requires a new human authorization and a new protocol-defined recovery path;
21B defines no such recovery path.

### 11.1 Rate-budget admission and exhaustion

Rate limiting is deterministic adapter policy and never delegated to a model.
`github-rate-budget-observation/0.1.0` is a closed factual record derived from
one accepted authenticated Stage 21A response. It binds the source observation
reference/hash; repository/API-profile hashes; repository/account/App/
installation IDs; credential-provider ID/version; provider-key reference/hash
and public-key fingerprint used to authenticate
the source lease receipt/claims; API version; exact GitHub resource bucket;
nonnegative limit and remaining integers; nullable reset time;
retry-after presence; observed-at; and `complete:true`. It grants no authority.

Before credential resolution, the exact cross-bound rate-budget observation
must be no older than 60 seconds. It must show no retry-after indication and at
least:

`exact maximum total requests for this transaction + 10 safety-reserve requests`

remaining in the applicable GitHub resource bucket. Missing, malformed,
stale, differently scoped, or insufficient rate evidence fails before
credential resolution with `INSUFFICIENT_RATE_BUDGET`.

The observation reference, content hash, repository/API-profile hashes,
account/App/installation IDs, provider ID/version, provider-key reference/hash
and public-key fingerprint, API version, and exact resource bucket must equal
the values cross-bound through §§4, 6, and 7.
Equality of the numeric remainder alone is insufficient. Any substituted
observation or scope mismatch fails before credential resolution with
`RATE_LIMIT_EVIDENCE_INVALID`.

Freshness, scope, retry-after absence, and sufficient remainder are evaluated
twice using the wall and monotonic clocks: immediately before credential-lease
admission and again immediately before the first network dispatch. A backward
or forward wall-clock discontinuity, expired 60-second window, or exhausted
monotonic authorization window fails closed. These evaluations are recorded
as bounded booleans/timestamps in lease evidence and the first step admission;
they cannot expand the authorized budget.

The transaction maintains an in-memory request budget initialized to the exact
authorized `2 x file count + 14` ceiling. Every dispatch consumes one unit even if
no response arrives. No call is admitted when the remaining local budget is
zero.

After every response, the adapter parses only the bounded rate-limit
projection inherited from Stage 21A: resource, limit, remaining, reset time,
and presence/value class of `Retry-After`. It retains no raw headers. A
decreasing server value narrows the local budget; an increasing value cannot
expand the immutable authorization. If the projected server remainder falls
below the number of still-possible transaction requests plus the 10-request
safety reserve, the transaction stops before another dispatch.

GitHub primary or secondary limiting, including accepted rate-limit `403` or
`429` classification or a `Retry-After` indication, stops the transaction.
Reset and retry-after values are retained only as factual bounded evidence.
The adapter does not sleep, wait, resume, resolve another credential, or retry
any mutation. Continuing later requires expiry of the current attempt and a
new human authorization; an ambiguous dispatched mutation must first complete
the separately authorized reconciliation in §11.

## 12. `github-publication-receipt/0.1.0`

One immutable receipt records the factual terminal outcome:

- upstream references/hashes, exact rate-observation reference/hash and scope,
  provider-key reference/hash/public-key fingerprint, and publication
  attempt/claim identities;
- exact ordered step-state entries as a closed four-variant discriminated
  union. Every variant contains the step ID and immutable step-admission
  reference/hash. `read_admitted_without_result` contains only those common
  fields; `read_result_present` additionally requires the immutable
  step-result reference/hash and result fields below. Mutation variants
  `mutation_admitted_without_result` and `mutation_result_present` also require
  the accepted repository-identity observation reference/hash from the
  directly preceding recheck; the latter additionally requires the immutable
  step-result reference/hash. Each `*_result_present` variant contains accepted
  status class, response-projection hash, expected/observed object identity,
  and completion time. No result-only field is nullable or permitted on an
  `*_admitted_without_result` variant, and no repository-identity observation
  field is permitted on a read variant;
- branch result: `NOT_ATTEMPTED`, `CREATED`, `REFUSED`, `CONFLICT`, or
  `AMBIGUOUS`;
- PR result: `NOT_ATTEMPTED`, `CREATED`, `REFUSED`, `CONFLICT`, or
  `AMBIGUOUS`;
- repository ID, base/head refs, base/proposal OIDs, and PR numeric ID when an
  accepted response proves it;
- `complete` true only when the exact branch and one exact PR are positively
  observed;
- sorted safe reason codes;
- `proposal_published` as a factual boolean that is true if and only if
  `complete:true`, the exact branch is positively observed at the proposal
  commit, and exactly one matching PR is positively observed at the same head
  and authorized base; otherwise it is false;
- `approval_effect:"none"`, `decision_effect:"none"`,
  `membership_effect:"none"`, `merge_authorized:false`,
  `merge_requested:false`, and `production_use_allowed:false`.

The ledger event contains only receipt and upstream hashes, operation key,
terminal booleans, safe reason codes, repository numeric ID, and authority
constants. It contains no branch name, path, commit message, PR title/body,
URL, credential selector, lease ID, raw GitHub field, or exception text.
The rate observation is represented in the ledger only by its content hash;
raw rate values, reset time, provider version, and resource bucket are omitted.

If the publication receipt cannot be durably stored, no ledger event may claim
or hash that nonexistent receipt. The adapter attempts at most one immutable
`github-publication-terminal-failure/0.1.0` capsule containing only predecessor
hashes, the same exact ordered closed step-state entries defined above, safe
reason code, and authority constants. If that store also fails, it emits only
the sanitized local diagnostic and stops. Neither failure path dispatches
another request.

## 13. Closed reason codes

The initial Stage 21B vocabulary is:

`PUBLICATION_AUTH_INVALID`, `PUBLICATION_AUTH_EXPIRED`,
`PUBLICATION_INPUT_MISMATCH`, `PROPOSAL_MANIFEST_INVALID`,
`PROPOSAL_PATH_PROHIBITED`, `PROPOSAL_PATH_COLLISION`,
`PROPOSAL_CONTENT_CHANGED`, `PROPOSAL_LIMIT_EXCEEDED`,
`BASE_OBSERVATION_STALE`, `BASE_REF_CHANGED`, `HEAD_REF_EXISTS`,
`HEAD_REF_PROTECTED`, `HEAD_REF_RULESET_TARGETED`,
`PUBLICATION_ALREADY_CLAIMED`, `PUBLICATION_CLAIM_CONFLICT`,
`PUBLICATION_CLAIM_STORE_FAILED`, `PUBLICATION_INTENT_STORE_FAILED`,
`PUBLICATION_LEASE_INVALID`, `PUBLICATION_PERMISSION_MISMATCH`,
`PUBLICATION_LEASE_EVIDENCE_STORE_FAILED`, `PUBLICATION_LEASE_STALE`,
`PUBLICATION_CLEANUP_FAILED`, `MUTATION_NOT_ALLOWED`,
`MUTATION_LIMIT_REACHED`, `MUTATION_DISPATCH_FAILED`,
`MUTATION_OUTCOME_AMBIGUOUS`, `GIT_OBJECT_ID_MISMATCH`,
`GIT_OBJECT_RESPONSE_INVALID`, `REF_RESPONSE_INVALID`,
`PR_RESPONSE_INVALID`, `PR_ALREADY_EXISTS`, `PR_CREATION_REFUSED`,
`RATE_LIMITED`, `INSUFFICIENT_RATE_BUDGET`, `RATE_LIMIT_EVIDENCE_INVALID`,
`STEP_ADMISSION_STORE_FAILED`, `STEP_RESULT_STORE_FAILED`,
`PUBLICATION_RECEIPT_STORE_FAILED`, `TERMINAL_FAILURE_STORE_FAILED`,
`RECONCILIATION_AUTH_INVALID`, `RECONCILIATION_ALREADY_CLAIMED`, and
`PUBLICATION_RECONCILIATION_REQUIRED`.

Public exceptions expose only one reason code, operation key, and attempt ID.
They never interpolate paths, refs, GitHub content, HTTP text, headers,
credentials, environment values, or provider output.

## 14. Required deterministic acceptance evidence

### 14.1 Functional and integrity

Tests must prove:

- schema closure, strict typing, canonical cross-platform hashes, durable
  immutable writes, idempotent factual reads, and conflict retention;
- every upstream reference/hash and numeric identity is indispensable and
  substitution fails before credential resolution;
- substitution of the rate-limit observation, its reference/hash, repository,
  API profile, account, App, installation, provider, API version, or resource
  bucket, provider-key record/hash, or public-key fingerprint fails before
  credential resolution and transport;
- exact Git blob/tree/commit OID vectors for SHA-1 and any repository object
  format admitted by the final repository profile;
- file mutation between manifesting and admission fails before credentials;
- exact path normalization, case-fold/Unicode collision, reserved-name,
  symlink/reparse, escape, prohibited-path, file-count, and byte limits;
- deterministic sorted request order independent of filesystem enumeration;
- canonical padded RFC 4648 blob encoding and exact request-body hashes for
  content lengths modulo three equal to zero, one, and two;
- one exclusive caller, crash-retained claim, replay refusal, and zero second
  provider resolution;
- exact endpoint/method/body/permission/order ceilings;
- the Stage 21A repository-identity projection is freshly read immediately
  before every mutation, and numeric repository/account identity or profile
  substitution, drift, incompleteness, or read failure stops before dispatch;
- all successful response identities reproduce the local expected identities;
- base/head observations gate ref and PR creation at the moment required;
- admission requires the exact `2 x file count + 14` transaction request
  ceiling plus the fixed
  10-request safety reserve, and every dispatch monotonically consumes the
  local budget;
- PR title/body are hash-bound and excluded from logs/ledger;
- cleanup runs on success, every local failure, every transport failure,
  cancellation, and persistence failure; and
- complete, refused, conflicting, partial, and ambiguous receipts remain
  factual and non-authoritative.
- `proposal_published` obeys its exact truth condition, and `REFUSED` cannot be
  produced for any mutation that reached dispatch; and
- reconciliation covers receipt present, failure capsule present, and a hard
  crash with both terminal artifacts absent, binding the exact retained claim
  and step-record inventory without amending the original chain.

### 14.2 Security and abuse

Adversarial tests cover:

- every extra read/write permission, wrong credential class, wrong repository,
  App, installation, account, provider, protocol, intent, and claim;
- POST to every route outside §8 and every PUT/PATCH/DELETE/GraphQL request;
- alternate origins, schemes, ports, userinfo, redirects, ambient proxies,
  poisoned DNS, TLS/hostname failure, CR/LF, arbitrary headers, encoded path
  tricks, caller URL injection, and decompression expansion;
- executable, symlink, submodule, deletion, rename, case collision, Unicode
  ambiguity, workflow/governance/credential path, and content-after-review
  substitution;
- existing ref, protected ref, ruleset-targeted ref, base drift, wrong tree,
  wrong parent, wrong object OID, cross-repository head, draft PR,
  maintainer modification, duplicate PR, and PR identity substitution;
- failure before and after dispatch at every mutation boundary, crash after
  every remote object, and proof of no automatic repeat or cleanup mutation;
- concurrency at intent, claim, lease, ref, and PR boundaries; and
- missing, stale, malformed, cross-resource, insufficient, decreasing, and
  apparently increasing rate-limit evidence; primary and secondary limiting;
  and proof that neither reset time nor `Retry-After` causes sleep, automatic
  resume, credential renewal, or mutation retry; and
- sentinel credentials across workspace, ledger, stdout, stderr, exceptions,
  JUnit, wheel, sdist, and CI artifacts.

Every precondition failure asserts zero credential resolutions and zero
transport calls. Every post-dispatch failure asserts zero repeat calls.

### 14.3 Platform, package, and network evidence

The exact implementation head and protected `main` must pass with zero Stage
21B failures, errors, skips, or xfails on:

- Windows / Python 3.12;
- Ubuntu / Python 3.12;
- Ubuntu / Python 3.13; and
- macOS / Python 3.12.

Installed-wheel tests execute deterministic publication fixtures outside the
source tree. Wheel and sdist inventories contain no token, private key,
proposal payload, GitHub response cassette, repository identifier, fixture
transport, test-only constructor, writable live profile, credential helper,
or Git executable dependency.

CI denies or detects external network access. Its TLS fixture is loopback-only,
uses a test-support constructor absent from production packages, exercises the
production encoder/TLS/bounded-reader/parser path, and proves no request can
reach `api.github.com`.

## 15. Review questions for the Council of five

Each reviewer returns `PASS_EXACT_DRAFT` or `BLOCK` with exact section and
reason:

1. **Governance and authority:** Are human authorization, proposal-only effect,
   stage boundaries, and ledger semantics explicit and non-circular?
2. **Security and credentials:** Are permission narrowing, lease admission,
   secret exclusion, path control, mutation ambiguity, and no-retry behavior
   fail-closed?
3. **Git and GitHub correctness:** Does the REST object sequence reproduce the
   exact proposal without updating an existing ref or confusing object/ref/PR
   identity?
4. **Evidence and schemas:** Are all durable records closed, immutable,
   cross-bound, sufficient for replay/conflict/reconciliation, and free of raw
   untrusted data?
5. **Cross-platform testability:** Can every filesystem, durability, transport,
   packaging, concurrency, and ambiguity claim be tested deterministically on
   the required matrix?

Any blocker changes the draft bytes and invalidates prior exact-draft passes.
After reconciliation, compute SHA-256 and Git blob without committing, then
submit those exact identifiers for a fresh 5/5 review and Arthur freeze.

## 16. Rollback and failure rules

Before publication, defects produce a new proposal and authorization; accepted
evidence is never rewritten. After publication, created Git objects, branch,
or PR remain factual remote state. CONCLAVE performs no automatic deletion,
closure, force update, rewrite, or rollback mutation.

Credential suspicion requires external provider revocation and sanitized
incident handling. Removing Stage 21B code later cannot delete its immutable
historical evidence.

## 17. Official factual references

Consulted on 9 September 2026; these platform facts grant no authority:

- Git database REST API: `https://docs.github.com/en/rest/git`
- Git blobs: `https://docs.github.com/en/rest/git/blobs`
- Git trees: `https://docs.github.com/en/rest/git/trees`
- Git commits: `https://docs.github.com/en/rest/git/commits`
- Git references: `https://docs.github.com/en/rest/git/refs`
- Pull requests: `https://docs.github.com/en/rest/pulls/pulls`
- GitHub App permissions:
  `https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app`
- Installation-token narrowing:
  `https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app`
- REST API versioning:
  `https://docs.github.com/en/rest/about-the-rest-api/api-versions`

## 18. Current disposition

Stage 21B is ready for exact-draft Council review only. It is unfrozen,
uncommitted, and unpushed. No Stage 21B implementation, credential access,
GitHub API call by the adapter, remote branch, pull request, merge, repository
setting change, KOS or IDM change, signing, identity allocation, membership
activation, deployment, or production operation is authorized or performed.
