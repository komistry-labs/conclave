# Stage 21C — Factual PR assistant

Date: 2026-09-21
Status: CONSOLIDATED LOCAL CANDIDATE / NOT FROZEN / NOT IMPLEMENTED

## 1. Scope

Answer five factual questions: which PR/commits were observed; which check
results were returned; which reviews and commit bindings were recorded; which
protection settings were visible; and whether GitHub reports a merge and its
subsequent checks. Never emit a readiness verdict, safety score, recommendation
to merge, approval, authorization, or overall green indicator.

The human independently decides and acts in GitHub. CONCLAVE performs no review
submission, merge, queue, auto-merge, settings change, browser automation or
other mutation. It never receives the human's credentials or second factor.
Account security, reviewer independence, effective policy sufficiency, bypass
absence and interval continuity are NOT VERIFIED by this profile. Keys and
external signing are deferred, not replaced by 2FA or content hashes. That
deferral is confined to Stage 21C human-approval signing. Stage 21A's signed
credential-provider lease verification and key pinning are retained in full,
and no eventual live operation under this profile is credential-free or without
a cryptographic provider boundary.

Method: this profile records what Stage 21A returns. It does not restate how
Stage 21A works internally. Every Step, stop and coverage value is a function of
results Stage 21A stores or emits, so a validator can recompute them from the
report and the observations it references.

## 2. Governing transition proposed for adoption

Local base: `154394c570a9919fc00b7c00779f565f742508e2`.
This is the active local candidate, replacing the unfinished advisory-verdict
candidate (SHA-256 `97e3236229f7028f395195cf817bff72c6a719af1f1d477db0b5c333b748e81f`).
Preserve all earlier drafts and reviews; none supplies approval for these bytes.

Adoption is effective only through the separate Arthur-issued record
`INCREMENT-21C-FACTUAL-PROFILE-ADOPTION-RECORD.md`, which must bind these exact
bytes by SHA-256. That record, not this document, supersedes the
baseline-selection effect of Arthur's merged freeze records
`INCREMENT-21C-PROTOCOL-FREEZE-RECORD.md`
(`7f01b8bd9237c2fdd389fa6882291803a0d4ee4b483b5cdfb4e3f5a1d7b33e4b`),
`INCREMENT-21-ERRATUM-0001-FREEZE-RECORD.md`
(`d336f9fc98d424bda3907f864060967d66a8c1c417ee09892a557a63e44051b3`) and
`INCREMENT-21C-CONTROL-ATTESTATION-COLLECTION-PROTOCOL-FREEZE-RECORD.md`
(`fb6a785fb600bb0860bb47347056a4aceec396266dc8fc9757b623c9951712d7`), clause
by clause. The rules below govern the frozen documents they name: the master
protocol, Erratum 0001, Stage 21A, and the two unselected profiles. Without that
issued record none of them takes effect.

On exact adoption only, apply the following additive precedence rules:

1. Select this factual-only profile instead of the entire signed readiness
   profile (`d3701754c7ab782835bc92db07c055509e415a69765373ed5cd30f250164b257`)
   and external collection profile
   (`6ea468c1cdd3a4ac0befecd3ffa3c2c26cfb51218902fb3af20366e4dbbb91c2`).
   Neither profile is claimed implemented or satisfied. Both remain frozen,
   merged and preserved byte-for-byte; adoption leaves them unselected, not
   rescinded.
2. For master protocol
   `89a05211a4323db2e79d2854952b24ce033c71f357430c7ac839457ff0878d75`,
   replace section 1 objective 5, section 4 Stage 21C, section 6 Stage 21C record
   reservations, section 8 invariants 8-12, section 10 Stage 21C readiness and
   authorization acceptance requirements, and section 12 decisions 5-7 only
   insofar as they prescribe Stage 21C readiness, authorization, attestation or
   execution. The replacement is factual observation under this document. Where
   this rule reaches master text that Erratum 0001 did not supersede, this rule,
   not the erratum's supersession list, governs.
3. For human-merge Erratum 0001
   `a0fa63884be7970e9c0463014b1091f118bc32d0702fc7ebb5402a8410a5c742`,
   replace sections 4-6, 8-11 and 13 with this document's factual objective,
   records, lifecycle and acceptance requirements. Keep sections 7 and 14's
   no-mutation boundary and deferred adapter-issued merge. Normal two-parent
   merge is the only structurally compared method; no merge method is declared
   conforming, and other methods can be observed.
   Erratum section 12 retains only its mutation, rollback and live-exercise
   boundaries; its obsolete failed-readiness trigger is not a retained gate.
   Erratum section 2: items 1 and 4, which allocate exact-head merge-readiness
   evaluation and reconciliation to CONCLAVE, describe the replaced sections and
   carry no independent normative force. Item 2 is retained as a permission to
   the human that this profile neither consumes nor verifies. Item 3 and both
   sentences of the closing paragraph are retained.
4. Retain administration-read-only restrictions, Stage 21A/21B controls,
   credential isolation, bounds, privacy and all non-conflicting restrictions.
   For this factual profile only, exactly the following clauses of Stage 21A
   (`INCREMENT-21A-READ-ONLY-GITHUB-FOUNDATION.md`, SHA-256
   `4493237e46c72b3b3eed8150e4994580568831e55ffa24046b5058eb4a7b0b5f`) receive
   additive precedence, each specified in section 5:
   (a) section 4.2's fixed API-profile family and response_projection_version,
   extended by the separately versioned github-factual-api-profile/0.1.0 record
   and github-factual-rest-projections/0.1.0 set;
   (b) the sites at which Stage 21A validates or records an API-profile
   reference or hash — sections 5.1, 5.2 (including the attempt preimage), 5.3,
   6.1 (credential-resolution request), 6.3, 6.4 (provider claims and lease
   evidence) and 9 — each extended to accept that record, while old validators
   still reject it;
   (c) section 8's retained-facts rule for the pull-request family and section
   8.1's pull_request.get raw contract and its rule that additive raw fields not
   named there are discarded, each displaced only to admit merge_commit_sha and
   merged_by; and
   (d) section 8.2's rule that a null identity-bearing value sets
   identity_match:false or complete:false, displaced only for those two fields.
   These are the only Stage 21A changes: (a) and (b) select the projection set,
   (c) and (d) define its one extended shape, and every other operation maps to
   an unchanged Stage 21A projection. No other Stage 21A clause is displaced.
   Old projection versions and consumers remain unchanged. No new route or scope.
5. Stage 21D is not authorized. Its later acceptance must distinguish deferred
   signing from successful factual tests. Signing/custody findings are deferred,
   never relabelled resolved. Any remaining normative conflict blocks adoption.

Frozen documents remain byte-identical. This candidate does not apply its own
supersession or authorize implementation, publication or live access.

## 3. Closed records and input

Use Stage 21A sections 3 and 8.1 strict canonical JSON, hash, timestamp, integer,
object-ID and immutable persistence rules. Every durable record includes its
exact profile/schema_version, created_at, content_hash and constants:
authority_effect=decision_effect=membership_effect=none;
production_use_allowed=merge_authorized=action_execution_allowed=false.
Hash means `sha256:` plus 64 lowercase hex. References are closed objects
{path, content_hash} using Stage 21A safe relative paths and reopen verification.
Reject unknown members, duplicate JSON keys, invalid Unicode/types and excess
size. Maximum canonical record size is 1 MiB. No arbitrary map or free text.

`github-factual-request/0.1.0` adds exactly:

- protocol_sha256: hash of adopted protocol;
- repository_profile: Stage 21A profile reference;
- api_profile: section 5 factual API-profile reference;
- mode: fixture/live;
- repository_id, pull_number: strict positive IDs;
- base_ref, head_ref: Stage 21A full refs;
- expected_base_sha, expected_head_sha: verified-format object IDs;
- expected_human_id: positive GitHub user ID or null (account comparison only);
- prior_report: report reference or null;
- expected_merge_sha: oid or null, null iff purpose is initial;
- purpose: initial/post_action (prior_report null iff initial).

prior_report must be an initial report with the same protocol, repository/API
profiles, mode, repository ID, PR, refs, expected SHAs and expected_human_id.
For post_action, prior_report.merge.state must be MERGED with a non-null
merge_sha equal to expected_merge_sha. This initial report supplies the discovery
evidence for a separately authorized exact-SHA follow-up. If an initial report
shows no merge yet, obtain another separately authorized initial observation
later; do not poll, wait for new authority inside a cycle or chain reports.
Reject any difference before collection.

The request is input, not operation authorization. Each network operation still
requires its separate Stage 21A authorization/intent/lease. Repository identity,
profiles and prior target must agree before dispatch. Caller-selected endpoints,
credentials, source URLs and policy verdicts are forbidden.

`github-factual-report/0.1.0` adds exactly:

- request: request reference;
- started_at, completed_at: informational UTC readings, taken immediately
  before slot 1 is dispatched and immediately after the last dispatched slot
  returns. No validity rule depends on their values or their difference;
- stop_reason: NONE/OPERATION_FAILURE/LINKAGE_CHANGED;
- stop_slot: a section 4 slot literal or null, null iff stop_reason is NONE;
- observations: 0-16 observation references under section 5, sorted by
  operation key, canonical parameters then content hash, duplicates rejected;
- pr_before, pr_after: observation references or null;
- target: SAME/CHANGED/UNKNOWN;
- sections: exactly five Section objects sorted by kind;
- merge: Merge object;
- limitations: exact sorted list from section 7.

The report also requires `steps`: exactly one closed Step per slot in section 4,
in slot order. Step is exactly {slot, disposition, observation, reason}:

- slot is that table's literal;
- disposition is OBSERVED/FAILED/NO_OBSERVATION/NOT_ATTEMPTED/NOT_APPLICABLE;
- observation is a reference, non-null iff disposition is OBSERVED or FAILED;
- reason is a Stage 21A section 10 reason code, non-null iff disposition is
  NO_OBSERVATION.

Section 4 fixes which disposition each slot receives. NOT_APPLICABLE is allowed
only for the three conditional post-merge slots. All observations must belong to
exactly one step; section sources and PR/commit pointers may refer to those
observations but cannot introduce another one.

Section is exactly {kind, coverage, sources}. kind is TARGET/CHECKS/REVIEWS/
PROTECTIONS/POST_MERGE_CHECKS; coverage is COMPLETE_WITHIN_ENDPOINT/PARTIAL/
UNAVAILABLE/NOT_REQUESTED; sources are unique references drawn from observations.
Section sources are exactly the non-null observations for its slots, sorted by
slot order. No caller-selected subset can satisfy coverage.

Coverage is determined by exactly this ordered algorithm. The first matching
step decides, and no clause elsewhere in this document overrides it:

1. POST_MERGE_CHECKS in an initial report -> NOT_REQUESTED;
2. otherwise, no sources -> UNAVAILABLE;
3. otherwise, every slot of that section OBSERVED, identity-matched and
   pagination-complete -> COMPLETE_WITHIN_ENDPOINT;
4. otherwise -> PARTIAL.

NOT_REQUESTED arises only at step 1. An empty returned collection is a source
and can reach COMPLETE_WITHIN_ENDPOINT; a missing collection is not a source.
PARTIAL retains explicitly incomplete source records. This is coverage, not
satisfaction of repository policy. pr_before/pr_after must equal the respective
slot reference, including null when not attempted.

Merge is exactly {state, merge_sha, actor_id, commit_source, parents_comparison,
actor_comparison}. state is OPEN/CLOSED_UNMERGED/MERGED/UNKNOWN; merge_sha is oid
or null; actor_id is positive ID or null; commit_source is observation reference
or null; parents_comparison is MATCH/DIFFERENT/UNSUPPORTED/UNKNOWN;
actor_comparison is SAME_ACCOUNT/DIFFERENT_ACCOUNT/UNKNOWN.

Reports contain projections by reference, not copied arbitrary API payloads.
Rendering shows native check/review statuses with target SHA and observation
time. No required-check or review-sufficiency reduction exists. Review author ID,
state, submitted time and commit_id are displayed without independence claims.

## 4. Collection plan, recording and drift

### 4.1 Plan

The fixed slot table below is the whole plan, in dispatch order. Paged slots
retain Stage 21A's ten pages (1000 items); a next page beyond that bound is
incomplete, never silently truncated.

| Slot | Operation | Parameters / section | Max pages |
| --- | --- | --- | --- |
| repository | repository.get | bound repository / TARGET | 1 |
| object_format | repository_hash_algorithm.get | bound repository / TARGET | 1 |
| base_ref | ref.get | request base_ref / TARGET | 1 |
| pr_before | pull_request.get | request pull_number / TARGET | 1 |
| head_checks | check_runs.list | expected_head_sha / CHECKS | 10 |
| head_status | combined_status.get | expected_head_sha / CHECKS | 10 |
| reviews | reviews.list | request pull_number / REVIEWS | 10 |
| protection | branch_protection.get | base_ref branch / PROTECTIONS | 1 |
| branch_rules | branch_rules.list | base_ref branch / PROTECTIONS | 10 |
| rulesets | repository_rulesets.list | includes_parents=true / PROTECTIONS | 10 |
| pr_after | pull_request.get | request pull_number / TARGET | 1 |
| merge_commit | commit.get | expected_merge_sha / POST_MERGE_CHECKS | 1 |
| merge_checks | check_runs.list | expected_merge_sha / POST_MERGE_CHECKS | 10 |
| merge_status | combined_status.get | expected_merge_sha / POST_MERGE_CHECKS | 10 |
| repository_after | repository.get | bound repository / TARGET | 1 |
| object_format_after | repository_hash_algorithm.get | bound repository / TARGET | 1 |

This is 79 maximum page transmissions plus 16 single-operation retry allowances,
95 maximum transmissions: this document's cycle ceiling. Authorizations retain
Stage 21A's exact endpoint page ceiling plus one retry (11 paged, 2 single), and
7 x 11 + 9 x 2 = 95. No page-cap or attempt-preimage override is introduced. No
ruleset-detail expansion, head-ref dereference in a foreign fork, additional
route or caller-selected plan is admitted. Rulesets are summary observations,
not complete effective policy. The fixed table, request and steps make the plan
reproducible offline.

Dispatch follows table order. The three conditional slots are dispatched only
in post_action and only as section 5 permits; otherwise dispatch passes from
pr_after directly to repository_after.

### 4.2 Repository verification

The slot pairs repository/object_format and repository_after/object_format_after
each verify the bound repository ID and object format. This profile does not rely
on Stage 21A's profile-verification cache or its five-minute expiry to establish
repository identity for its reads, and no verification from a prior cycle is
used. Every read between the two pairs is bracketed by them: the report shows
repository identity observed before and after, not continuous identity
(NO_INTERVAL_CONTINUITY). If a Stage 21A implementation refuses an operation
because its own profile verification has lapsed, that refusal is recorded by
section 4.3 like any other result.

### 4.3 Recording each slot

Each dispatched slot makes exactly one Stage 21A logical-operation call. Its Step
is a function of what that call returned, applied in this order:

1. An observation was returned: OBSERVED if its `complete` is true, otherwise
   FAILED.
2. No observation was returned and the single reason code Stage 21A emitted is
   ATTEMPT_CLAIM_STORE_FAILED, LEASE_EVIDENCE_STORE_FAILED or
   OBSERVATION_STORE_FAILED: the cycle returns an error, not a report.
3. No observation was returned and the emitted code is any other Stage 21A
   section 10 code: NO_OBSERVATION, with that code as reason.
4. Neither an observation nor a section 10 code was returned: the cycle returns
   an error, not a report.

This order is keyed on results Stage 21A stores or emits, not on Stage 21A's
internal sequence. Where a conforming Stage 21A implementation can reach a
failure at more than one internal point, the Step records the result that
implementation produced; this profile does not choose between them.
NO_OBSERVATION asserts nothing about attempt-claim state; Stage 21A's retained
claims are its own durable evidence. No Stage 21A observation is fabricated.

### 4.4 Continuing or stopping

After each Step:

- OBSERVED: dispatch continues.
- FAILED is tolerated, and dispatch continues, iff all four hold: the slot is
  protection, branch_rules or rulesets; the observation's status class is 4xx;
  its reason codes are exactly [HTTP_RESPONSE_REJECTED]; and every per-page
  record of the observation carries a Stage 21A section 9 safe rate-limit
  projection whose retry_after_present is false and whose remaining is greater
  than zero. An absent projection fails the fourth condition. A tolerated FAILED
  does not change stop_reason.
- Every other FAILED, and every NO_OBSERVATION: dispatch stops. If stop_reason is
  NONE it becomes OPERATION_FAILURE and stop_slot becomes this slot.

Stage 21A's classifier alone determines status class and reason codes. This
profile adds no header inspection, retains no raw headers, and never infers that
404 means unprotected. An explicitly rate-limited, cleanup-failed or 5xx result
fails the exception by its code set or status class. A 4xx that Stage 21A
records only as HTTP_RESPONSE_REJECTED but whose retained rate-limit projection
is absent, shows remaining zero, or reports a Retry-After fails the fourth
condition. Beyond that, this profile does not verify Stage 21A's rate-limit
classification. Because Stage 21A stores only the status class, a tolerated
FAILED is rendered as rejected by GitHub (4xx), cause not recorded — never as a
confirmed permission failure or as absent protection.

After dispatch stops, every remaining slot is NOT_ATTEMPTED except where section
5 makes a conditional slot NOT_APPLICABLE. Mandatory slots are never omitted.
Reports preserve the completed prefix without resuming, recollecting or merging
another cycle. stop_reason and stop_slot record the first condition only; later
conditions never overwrite them.

### 4.5 Target and drift

Both PR reads bind numeric repository/PR IDs and refs. A PR read matches the
request when its base.ref equals the request base_ref and its head.ref equals
the request head_ref, each request value first stripped of its leading
`refs/heads/`, and its head.sha equals expected_head_sha. The base_ref
observation matches when its returned ref equals the request base_ref exactly.

target is SAME iff pr_before and pr_after are both OBSERVED and match, base_ref
is OBSERVED and matches, and all four verification slots are OBSERVED. target is
CHANGED iff an OBSERVED PR read does not match, or a verification slot's
observation has identity_match false. Otherwise target is UNKNOWN.

Neither the base_ref observation's object SHA nor either PR read's base.sha is
compared with expected_base_sha for target. Base movement, including movement
caused by the merge itself, is recorded as observed fact only and never changes
target; expected_base_sha is used only by section 5.3. Equal endpoints do not
prove atomicity or absence of intermediate changes. Never retry a cycle to hide
drift.

A correctly requested PR read that does not match the request, as defined
above, is valid evidence of CHANGED, not a source-binding error. Each step binds the exact request
repository/profile identities, operation, canonical parameters and permitted
projection version. Source observations must match these bindings and their own
authorization/intent/lease chain. Checks and statuses must bind their slot's
commit SHA. A wrong source binding is a validation error: the cycle returns an
error, not a report. PR chronology follows slot order; equal-second timestamps
do not replace verified intent/step ordering.

Reports are immutable historical observations, never a current authorization;
display their age and warn when more than 300 seconds have passed since
completed_at. Post-action collection requires a separate request, with the same
expected target as prior report. A later base change is reported as such; it does
not rewrite the earlier target. Fixture/live chains may not mix.

### 4.6 Authorizations

Every operation needs an externally supplied distinct authorization hash and an
unused Stage 21A attempt digest. The two PR reads, and the two verification
pairs, must not reuse an authorization or attempt; a fresh UUID alone is
insufficient. Validate all fixed-slot attempts before dispatch. Preflight checks
presence, bindings and attempt-digest non-use only; it evaluates no
authorization or intent time validity. Stage 21A evaluates time validity at
dispatch, and section 4.3 records its result. For post_action,
all conditional authorizations are pre-issued for expected_merge_sha before the
cycle begins. Missing or wrong bindings fail preflight. No mid-cycle
authorization issuance is allowed. The coordinator cannot create or broaden
authority. Later cycles cannot reuse consumed authorizations or claims. Do not
delete claims or weaken Stage 21A replay protection.

## 5. Small opt-in PR projection extension and Merge derivation

Use the existing GET /repos/{owner}/{repo}/pulls/{pull_number}, existing
pull_requests/read permission and operation-key admission. Add a separately
versioned projection-set `github-factual-rest-projections/0.1.0`, selected by
the new closed `github-factual-api-profile/0.1.0` record. This profile has exactly
the fields and constants of Stage 21A section 4.2, except profile/schema_version
name this new family and response_projection_version names this new set. Every
operation in the cycle binds its exact hash wherever section 2 rule 4(b) applies.
Old validators must reject it; no interpretation under the old API profile is
permitted. The new set maps all non-PR keys to unchanged Stage 21A projections
and maps pull_request.get to the full existing 21A PR projection plus:

- merge_commit_sha: required nullable oid;
- merged_by: required nullable closed {id: positive ID, type: Stage 21A actor_type}.

Missing extension fields reject that projection; null means unavailable, not
invented identity. Discard login, email, URLs and all other actor fields. Under
section 2 rule 4(d), a null value in either new field does not make its
observation incomplete and does not clear identity_match. An ordinary open PR
reporting merged_by null is a complete, identity-matched observation. Missing or
malformed fields still reject the projection, and the inherited repository, base
and head identity completeness rules are unchanged. Do not mutate the old PR
projection or allow old consumers to accept this one. Every observation envelope
records the new set version, including non-PR reads; the operation key uniquely
selects its shape. There is no per-call override or caller-selected version.

### 5.1 Merge state

Merge derives solely from pr_after when its Step is OBSERVED; never fall back to
pr_before. Otherwise every Merge field is UNKNOWN or null. Changed merge state
between the reads does not combine their values. No third PR read occurs.

Merge.state is determined by exactly this table over pr_after's `state`,
`merged`, `merged_at` and `merged_by`:

| Merge.state | Condition |
| --- | --- |
| OPEN | state open, merged false, merged_at null, merged_by null |
| CLOSED_UNMERGED | state closed, merged false, merged_at null, merged_by null |
| MERGED | state closed, merged true, merged_at non-null |
| UNKNOWN | every other combination |

merge_commit_sha does not enter the table. With merged false it describes
GitHub's test merge: never label it an actual merge or use it for dispatch.

For MERGED, merge_sha is merge_commit_sha, which may be null, and actor_id is
merged_by.id when merged_by is non-null, otherwise null. For every other state,
merge_sha and actor_id are null and both comparisons are UNKNOWN.

### 5.2 Conditional slots and linkage

In an initial report the three conditional slots are NOT_APPLICABLE and dispatch
passes to repository_after.

In post_action, once pr_after is OBSERVED:

- if Merge.state is MERGED and merge_sha equals expected_merge_sha, dispatch
  merge_commit, then merge_checks and merge_status as section 4.4 allows;
- if merge_sha is null, including every non-MERGED state, the three slots are
  NOT_APPLICABLE;
- if merge_sha is non-null and differs, the three slots are NOT_ATTEMPTED and the
  reported merge facts are retained without comparison to an unrelated commit.

In the last two cases stop_reason becomes LINKAGE_CHANGED with stop_slot
pr_after, if stop_reason is still NONE, and dispatch continues to
repository_after. In post_action, if pr_after is not OBSERVED, section 4.4 has
already stopped dispatch and the three slots are NOT_ATTEMPTED. In an initial
report they are NOT_APPLICABLE on every path, including after a stop.

merge_checks and merge_status are dispatched only after merge_commit is OBSERVED.
A merge_commit observation whose projected commit SHA differs from the SHA
requested for that slot is a wrong source binding under section 4.5: the cycle
returns an error, not a report. commit_source is the merge_commit observation
reference exactly when that Step is OBSERVED; it is null in every other case,
including every initial report. A FAILED merge_commit observation still appears
in observations and in its Step; it is never commit_source. Post-action commit
and check reads remain point-in-time observations, not proof that the PR
subsequently remained unchanged.

### 5.3 Comparisons

For post_action only, compare the ordered parents of the commit_source
observation with prior expected base then head: exactly two equal parents ->
MATCH; two different -> DIFFERENT; other parent count -> UNSUPPORTED; null
commit_source -> UNKNOWN. In an initial report parents_comparison is UNKNOWN.
This is structural comparison, not proof of merge method, approved tree or
policy compliance.

actor_comparison is UNKNOWN whenever the report is initial, Merge.state is not
MERGED, actor_id is null, merged_by.type is not User, or expected_human_id is
null. Otherwise it is SAME_ACCOUNT if actor_id equals expected_human_id and
DIFFERENT_ACCOUNT if it does not. A null or unavailable actor never yields
DIFFERENT_ACCOUNT. The comparison proves only account-ID equality. A merged flag
alone establishes only that GitHub reports a merge.

POST_MERGE_CHECKS uses existing checks/status endpoints for the actual reported
merge SHA only. Its coverage value follows section 3's ordered algorithm.
Artifacts are NOT SUPPORTED: no Actions endpoint or artifact-download capability
is added.

GitHub reference checked 2026-09-21:
https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request
The documented merge_commit_sha meaning changes after merge and by merge method,
and merged_by is documented as required and nullable. This source supports field
interpretation, not verification of any live PR.

## 6. Budget, retry and storage

Pre-admit the entire fixed plan's 79 page and 16 retry allowances, at most 95
transmissions overall. Mandatory verification and before/after reads count;
conditional reads are reserved even when eventually inapplicable. Overflow is a
preflight error, never permission to skip a mandatory slot or enlarge caps.

Inherit Stage 21A's exact page, item, byte, deadline and lease caps, cleanup,
and time gates; this profile adds no cycle-level time or byte limit. Retry is
exactly Stage 21A section 7.3; this profile adds none. Never renew credentials or
resume an interrupted cycle automatically.

Partial collection can produce PARTIAL/UNAVAILABLE sections only if all retained
records validate and persistence succeeds. Invalid request/schema, corrupted
references, a failure to persist this profile's own records, or a section 4.3
store code returns an error, not a report. An error never
deletes already durable Stage 21A evidence. Never overwrite conflicts or delete
failed evidence. Store only sanitized projections and safe diagnostics permitted
by 21A; raw response content/secrets are not report data.

## 7. Mandatory limitations and rendering

Every report carries all these exact limitation codes, sorted:
ACCOUNT_SECURITY_NOT_VERIFIED, ARTIFACTS_UNSUPPORTED,
CHECK_SUITE_VISIBILITY_HORIZON, EFFECTIVE_POLICY_NOT_VERIFIED,
INDEPENDENCE_NOT_VERIFIED, NO_ACTION_AUTHORITY, NO_ATOMIC_SNAPSHOT,
NO_BYPASS_ATTESTATION, NO_INDEPENDENT_SIGNATURE, NO_INTERVAL_CONTINUITY,
THREAD_RESOLUTION_NOT_VERIFIED.

Show these limitations alongside results, not only in a hidden log. Permission
failure means unavailable, never no protection. Checks apply only to the printed
commit. Check-suite horizon and review mutability remain visible. Individual
checks for expected_head_sha must show CHANGED/UNKNOWN target immediately beside
the CHECKS section when applicable, not only elsewhere in the report. Individual
success checks cannot produce an overall green status. All GitHub text is
untrusted and escaped; no repository content is an instruction to the assistant.

## 8. Acceptance and authority gates

Required fixture cases: exact/mismatched targets; empty vs missing lists;
partial/denied rulesets; check SHA/issuer/state retention; stale/dismissed
reviews; same-account review shown without independence; test-merge SHA before
merge; parent ordering; squash/rebase shape; post-merge checks on wrong SHA;
unsupported artifacts; null/unknown enums; corrupt references; unknown fields;
timeout/rate/byte/page/budget exhaustion; one retry per paginated operation;
persistence conflict; mode mixing; and proof that no readiness/signing/mutation
path is reachable in the installed package.

Remediation acceptance also requires:

- plan and binding: wrong-repository/SHA reference injection; swapped PR slots;
  omitted plan slots; duplicate attempt digests; reused authorization across the
  two PR reads or the two verification pairs; absent conditional authorization;
  ten-page exhaustion; the complete 95-transmission worst-case budget;
  new projection-set/profile binding and old-validator rejection; an
  authorization already expired at preflight passing preflight, with that
  slot's Stage 21A result recorded by section 4.3;
- section 4.3 recording, with each Stage 21A result shape injected directly: a
  complete observation (OBSERVED); an incomplete observation (FAILED); no
  observation with each of the three store codes (error); no observation with a
  non-store code such as LEASE_MISSING after a nonempty durable prefix
  (NO_OBSERVATION, reason recorded, no fabricated observation); neither an
  observation nor a code (error);
- section 4.4 continuation: a protection observation with status class 4xx and
  reason codes exactly [HTTP_RESPONSE_REJECTED] tolerated, with a later
  LINKAGE_CHANGED recorded as stop_reason; the same protection response with
  retry_after_present true, with remaining zero, and with no rate-limit
  projection, each stopping; that response combined with
  CREDENTIAL_CLEANUP_FAILED stopping; a 5xx HTTP_RESPONSE_REJECTED on protection
  stopping; RATE_LIMITED on protection stopping; a 4xx HTTP_RESPONSE_REJECTED on
  a non-PROTECTIONS slot stopping; stop_slot equal to the first stopping slot;
  retained prefix;
- section 4.5 target: SAME with all four verification slots OBSERVED; SAME in
  post_action with the base branch advanced by the merge, the base_ref object
  SHA differing from expected_base_sha; CHANGED from a PR read whose head.sha
  differs from expected_head_sha; CHANGED from a verification slot with
  identity_match false; request refs compared after stripping `refs/heads/`;
  UNKNOWN when the closing pair is NOT_ATTEMPTED after an earlier stop;
  open-to-merged between reads; missing final read;
- section 5.1 Merge.state: each table row; at least two UNKNOWN combinations —
  closed, merged true, merged_at null; and closed, merged false, merged_by
  non-null; a non-null merge_commit_sha with merged false leaving state
  unchanged; open PR with merged_by null and merged PR with null actor and null
  SHA, each remaining a complete identity-matched observation;
- section 5.2 linkage: post_action null merge_sha and differing merge_sha, each
  recording LINKAGE_CHANGED at pr_after and still dispatching the closing pair;
  pre-issued merge authorization with changed final SHA; a merge_commit
  observation with a different commit SHA returning an error; a FAILED
  merge_commit leaving commit_source null and parents_comparison UNKNOWN; an
  initial report stopping before pr_after with the three conditional slots
  NOT_APPLICABLE; an initial report with Merge.state MERGED leaving
  parents_comparison and actor_comparison UNKNOWN;
- section 5.3 actor: null expected_human_id; null actor with non-null
  expected_human_id yielding UNKNOWN, never DIFFERENT_ACCOUNT; non-User actor
  yielding UNKNOWN; equal and unequal actor IDs yielding SAME_ACCOUNT and
  DIFFERENT_ACCOUNT;
- section 3 coverage, with transmission state explicit: branch 1,
  POST_MERGE_CHECKS in an initial report (NOT_REQUESTED); branch 2, post_action
  null merge linkage leaving all three conditional slots with null observations,
  and separately merge_commit recorded as NO_OBSERVATION (UNAVAILABLE); branch 3,
  post_action with all three conditional slots OBSERVED, identity-matched and
  pagination-complete (COMPLETE_WITHIN_ENDPOINT); branch 4, merge_commit FAILED
  with a retained incomplete observation, and separately CHECKS with head_checks
  OBSERVED and head_status FAILED (PARTIAL).

Initial implementation requires separate authority after review and adoption
and is fixture-only, with no live transport or credentials. Test provenance is
explicit; a test package cannot become live by changing a flag or editing a
record. Any live-capable artifact requires separate review and authorization.
Obtain actual Windows/macOS/Linux and installed-package evidence before claims.

Next gate: exact-draft review of this consolidated candidate, its additive
supersession and the draft adoption record named in section 2. Author
self-check is not independent approval or Council PASS.

Official GitHub documentation establishes repository_hash_algorithm.get: the
endpoint is documented, accepts GitHub App installation tokens, and requires
Metadata repository permission (read), consistent with Stage 21A section 7.2.
That closes the documentary question only. Live preflight remains blocked until
a separately authorized fixture/live qualification of that operation. Do not
remove the inherited verification gate or invent an alternative endpoint
silently.

No runtime changes, signing, key creation, credentials, GitHub settings, commit,
push, PR, merge, Stage 21D, production, KOS or IDM operation is authorized here.
