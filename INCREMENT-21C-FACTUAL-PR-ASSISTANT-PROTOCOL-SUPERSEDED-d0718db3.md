# Stage 21C — Factual PR assistant

Date: 2026-09-19
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
by clause. The rules below govern only the frozen protocol documents they name.
Without that issued record none of them takes effect.

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
   execution. The replacement is factual observation under this document.
3. For human-merge Erratum 0001
   `a0fa63884be7970e9c0463014b1091f118bc32d0702fc7ebb5402a8410a5c742`,
   replace sections 4-6, 8-11 and 13 with this document's factual objective,
   records, lifecycle and acceptance requirements. Keep sections 7 and 14's
   no-mutation boundary and deferred adapter-issued merge. Normal two-parent
   merge remains the only structurally compared method; other methods can be
   observed but are not declared conforming.
   Erratum section 12 retains only its mutation, rollback and live-exercise
   boundaries; its obsolete failed-readiness trigger is not a retained gate.
   Erratum section 2 items 1 and 4, which allocate exact-head merge-readiness
   evaluation and reconciliation to CONCLAVE, describe the replaced sections and
   carry no independent normative force. Its item 3 and its closing statement
   that CONCLAVE does not send, queue, retry, schedule or otherwise cause a merge
   are retained.
4. Retain administration-read-only restrictions, Stage 21A/21B controls,
   credential isolation, bounds, privacy and all non-conflicting restrictions.
   Exactly three Stage 21A clauses receive additive precedence, for this
   factual profile only, each bounded as stated and specified in section 5:
   (a) section 4.2's fixed API-profile family and response_projection_version,
   extended by the separately versioned github-factual-api-profile/0.1.0 record
   and github-factual-rest-projections/0.1.0 set; (b) the API-profile reference
   validation of sections 5.1 and 5.2, extended to accept that record, while old
   validators still reject it; and (c) section 8.2's rule that a null
   identity-bearing value sets identity_match:false or complete:false, displaced
   only for the two new fields merge_commit_sha and merged_by. No other Stage 21A
   clause is displaced. Old projection versions and consumers remain unchanged.
   No new route or scope.
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
- started_at, completed_at: acquisition timestamps as defined in section 6,
  elapsed at most 300 seconds;
- stop_reason: NONE/TIME_BUDGET/OPERATION_FAILURE/LINKAGE_CHANGED;
- observations: 0-14 observation references under section 5, sorted by operation key,
  canonical parameters then content hash, duplicates rejected;
- pr_before, pr_after: observation references or null;
- target: SAME/CHANGED/UNKNOWN;
- sections: exactly five Section objects sorted by kind;
- merge: Merge object;
- limitations: exact sorted list from section 7.

The report also requires `steps`: exactly one closed Step per slot in section 4,
in slot order. Step is {slot, disposition, observation, reason}; slot is that
table's literal; disposition is OBSERVED/FAILED/ATTEMPTED_NO_OBSERVATION/
NOT_ATTEMPTED/NOT_APPLICABLE; observation is a reference or null; reason is a
Stage 21A section 10 reason code or null. OBSERVED requires a complete valid
source; FAILED requires a valid incomplete Stage 21A outcome source, which
includes a stored NOT_SENT observation. Both references must be in observations.
ATTEMPTED_NO_OBSERVATION, NOT_ATTEMPTED and NOT_APPLICABLE require a null
observation. reason is non-null exactly for ATTEMPTED_NO_OBSERVATION.
ATTEMPTED_NO_OBSERVATION represents only Stage 21A section 10's pre-transmission
failure class in which no lease-evidence and no observation record was created
and the attempt claim is retained. Its reason is exactly one Stage 21A section 10
code that can arise in that class; no new code, free text or fabricated Stage 21A
observation is introduced. The retained claim stays consumed, so later cycles
cannot reuse it. A slot in this state contributes no section source and always
stops dispatch.
NOT_APPLICABLE is allowed only for the three conditional post-merge slots.
All observations must belong to exactly one step; section sources and PR/commit
pointers may refer to those observations but cannot introduce another one.

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

## 4. Collection lifecycle and drift

Validate request and profiles; perform required repository/hash-algorithm checks;
read PR before collection; collect factual sections; read PR again; optionally
collect post-merge facts using only that final PR read; persist report and stop.
Both PR reads bind numeric repository/PR IDs and refs.
SAME requires complete before/after PR base/head/ref identity equal to request
and a matching standalone base_ref observation; no second ref read is implied.
Any explicit mismatch is CHANGED; missing/incomplete/conflicting evidence is
UNKNOWN unless a mismatch is already established. Equal endpoints do not prove
atomicity or absence of intermediate changes. Never retry a cycle to hide drift.

All source times must fall within the report interval. Reports are immutable
historical observations, never a current authorization; display age and warn
after 300 seconds. Post-action collection requires a separate request, with the
same expected target as prior report. A later base change is reported as such;
it does not rewrite the earlier target. Fixture/live chains may not mix.

The fixed slot table below is the whole plan, in dispatch order. Paged slots
retain Stage 21A's ten pages (1000 items);
a next page beyond that bound is incomplete, never silently truncated.

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
| merge_commit | commit.get | final observed actual merge SHA / POST_MERGE_CHECKS | 1 |
| merge_checks | check_runs.list | same merge SHA / POST_MERGE_CHECKS | 10 |
| merge_status | combined_status.get | same merge SHA / POST_MERGE_CHECKS | 10 |

This is 77 maximum page transmissions plus 14 single-operation retry allowances,
91 maximum transmissions: this document's cycle ceiling. Authorizations retain
Stage 21A's exact endpoint page ceiling plus one retry (11 paged, 2 single).
No page-cap or attempt-preimage override is introduced. No ruleset-detail expansion,
head-ref dereference in a foreign fork, additional route or caller-selected plan
is admitted. Rulesets are summary observations, not complete effective policy.
The fixed table, request and steps make the plan reproducible offline.

Each step binds the exact request repository/profile identities, operation,
canonical parameters and permitted projection version. Source observations must
match these bindings and their own authorization/intent/lease chain. Checks and
statuses must bind their slot's commit SHA. A wrong source binding is a validation
error, not PARTIAL. A correctly requested PR reporting a changed head/base is
valid evidence of CHANGED, not a source-binding error. PR chronology follows
slot order; equal-second timestamps do not replace verified intent/step ordering.

Every operation needs an externally supplied distinct authorization hash and
an unused Stage 21A attempt digest. Before/after reads must not reuse an
authorization or attempt; a fresh UUID alone is insufficient. Validate fixed
slot attempts before dispatch. For post_action, all conditional authorizations
are pre-issued for expected_merge_sha before the cycle begins. Missing or wrong
bindings fail preflight. The final PR read must still report that same actual
merge SHA before use. No mid-cycle authorization issuance is allowed. The
coordinator cannot create or broaden authority.
Later cycles cannot reuse consumed authorizations or claims. Do not delete
claims or weaken Stage 21A replay protection.

An operation failure stops further dispatch except a PROTECTIONS slot whose
only failure is a rejected HTTP response that is definitively not rate-limited.
That exception requires an actual received HTTP response, so a pre-transmission
failure recorded as ATTEMPTED_NO_OBSERVATION never qualifies and always stops.
The tolerated PROTECTIONS slot remains FAILED; collection may continue with subsequent independently
authorized slots, without retry or broader credentials. Ambiguous 403/rate
classification, RATE_LIMITED, transport, pagination, projection, identity, claim,
lease, cleanup or persistence failures always stop. Stage 21A's classifier is
controlling; no new raw-header retention or inference that 404 means unprotected.
If its safe outcome cannot establish the exception, stop. Remaining mandatory slots are
NOT_ATTEMPTED, not omitted. Conditional slots are NOT_APPLICABLE only when a
valid final PR source makes them inapplicable or purpose is initial. With no
valid final source in post_action they remain NOT_ATTEMPTED. Reports preserve
the completed prefix without resuming, recollecting or merging another cycle.

stop_reason records the first dispatch-terminating condition: OPERATION_FAILURE,
LINKAGE_CHANGED, or section 6's time condition. NONE means the plan finished,
possibly with tolerated protection failures. Later conditions never overwrite
the first. Invalid clock/storage state returns an error rather than a report.

## 5. Small opt-in PR projection extension

Use the existing GET /repos/{owner}/{repo}/pulls/{pull_number}, existing
pull_requests/read permission and operation-key admission. Add a separately
versioned projection-set `github-factual-rest-projections/0.1.0`, selected by
the new closed `github-factual-api-profile/0.1.0` record. This profile has exactly
the fields and constants of Stage 21A section 4.2, except profile/schema_version
name this new family and response_projection_version names this new set.
Every operation in the cycle binds its exact hash in authorization, intent,
attempt digest and observation. Explicit additive precedence extends Stage 21A
profile-reference validation for this factual profile only. Old validators must
reject it; no interpretation under the old API profile is permitted.
The new set maps all non-PR keys to unchanged Stage 21A projections and maps
pull_request.get to the extended PR shape below,
containing the full existing 21A PR projection plus:

- merge_commit_sha: required nullable oid;
- merged_by: required nullable closed {id: positive ID, type: Stage 21A actor_type}.

Missing extension fields reject that projection; null means unavailable, not
invented identity. Discard login, email, URLs and all other actor fields.
Explicit additive precedence over Stage 21A section 8.2: a null value in either
new field does not make its observation incomplete and does not clear target
identity_match. Only merge linkage and actor availability change. An ordinary
open PR reporting merged_by null is a complete, identity-matched observation and
never stops collection. Missing or malformed fields still reject the projection,
and the inherited repository, base and head identity completeness rules are
unchanged.
Do not mutate the old PR projection or allow old consumers to accept this one.
Every observation envelope records the new set version, including non-PR reads;
the operation key uniquely selects its shape. There is no per-call override,
caller-selected version or supposed inherited projection allowlist.

Merge derives solely from the complete, identity-matched pr_after slot; never
fall back to pr_before. Without that source all Merge fields are UNKNOWN/null.
Changed merge state or linkage between the reads does not combine their values:
retain both sources but derive only from pr_after. No third PR read occurs.
Post-action commit and check reads follow pr_after and remain point-in-time
observations, not proof that the PR subsequently remained unchanged.

Before merged=true, merge_commit_sha may describe GitHub's test merge. Never
label it an actual merge or dispatch post-merge reads using it. For merged=true,
retain the reported SHA/actor when available and, for post_action only, use
commit.get for that SHA. Initial requests skip all three conditional slots.
Identity-matched commit SHA must equal the reported SHA. Missing linkage leaves
comparisons UNKNOWN. commit_source is the merge_commit observation reference only
when that slot is OBSERVED, complete and identity-matched and its commit SHA
equals Merge.merge_sha; it is null in every other case, including a FAILED or
ATTEMPTED_NO_OBSERVATION merge_commit slot and every initial report. A FAILED
merge_commit observation still appears in observations and in its Step; it is
never cited as commit_source.
With a null actual SHA, conditional slots are NOT_APPLICABLE and merge linkage
remains unavailable. In post_action, a null or different final SHA also sets
stop_reason=LINKAGE_CHANGED and prevents all conditional dispatch. A differing
non-null SHA makes those slots NOT_ATTEMPTED; the reported merge facts are retained
without comparison to a fetched unrelated commit. Checks/status dispatch requires a complete merge_commit
observation with matching SHA. Failed linkage stops subsequent slots.

For post_action only, compare the ordered parents of the commit_source
observation with prior expected base then head: exactly two equal parents ->
MATCH; two different -> DIFFERENT; other parent count -> UNSUPPORTED; null
commit_source or otherwise missing evidence -> UNKNOWN. This is structural
comparison, not proof of merge method, approved tree or policy compliance.
actor_comparison is UNKNOWN whenever the report is initial, Merge.state is not
MERGED, Merge.actor_id is null (including a null merged_by), the reported actor
type is not User, or expected_human_id is null. Otherwise it is SAME_ACCOUNT if
actor_id equals expected_human_id and DIFFERENT_ACCOUNT if it does not. A null
or unavailable actor never yields DIFFERENT_ACCOUNT. The comparison proves only
account-ID equality. A merged flag alone establishes only that GitHub reports a merge.
OPEN/CLOSED_UNMERGED requires null merge fields/sources and UNKNOWN comparisons.
Contradictory PR flags (merged with open state, for example) yield UNKNOWN with
no derived merge fields. Initial reports leave comparisons UNKNOWN.

POST_MERGE_CHECKS uses existing checks/status endpoints for the actual reported
merge SHA only after commit linkage succeeds. That constrains dispatch only; the
section's coverage value follows section 3's ordered algorithm. Artifacts
are NOT SUPPORTED: no Actions endpoint or artifact-download capability is added.

GitHub reference checked 2026-09-19:
https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request
The documented merge_commit_sha meaning changes after merge and by merge method.
This source supports field interpretation, not verification of any live PR.

## 6. Budget, failures and storage

Pre-admit the entire fixed plan's 77 page and 14 retry allowances, at most 91
transmissions overall. Mandatory verification and before/after reads count;
conditional reads are reserved even when eventually inapplicable. Overflow is
a preflight error, never permission to skip a mandatory slot or enlarge caps.
Keep an in-memory transmission counter across operations; Stage 21A attempts
retain durable outcomes. A retry consumes budget even without a response.

Inherit 21A exact page/item/byte/deadline/lease caps and cleanup, with an
additional 300-second acquisition limit and 32 MiB aggregate response-body limit
(compression remains disabled).

Acquisition start T0 is the single monotonic clock reading taken immediately
after request validation, profile validation, fixed-slot attempt validation and
budget pre-admission all succeed, and immediately before slot 1 is dispatched.
started_at is the UTC instant of that same reading. No Stage 21A attempt claim,
credential resolution or network operation of the cycle precedes T0. Let
D = T0 + 300 s. D is the sole binding deadline.

Slots 1 and 2 are dispatched without a time check. Each is bounded by its
60-second Stage 21A operation deadline, which includes any permitted retry, so
together they end no later than T0 + 120 s, inside D. Before every later slot
require now+60 <= D. If that fails, stop without dispatch, mark remaining
applicable slots NOT_ATTEMPTED and record TIME_BUDGET. This is the only
dispatch-time reservation. It is a time check only, not a lease or authority
check.

No cached verification pair from a prior cycle is accepted, so slots 1-2 always
run inside the cycle, and the frozen Stage 21A profile-verification expiry E
falls at slot 2's success time + 300 s. That success is no earlier than T0, so E
is no earlier than D. Every later slot starts no later than D - 60 and ends no
later than D, so every operation of an admitted cycle starts before E and ends
no later than E. An operation ending exactly at E, possible only when E = D
under a fixture clock, is admitted. No extra verification pair is inserted.

After a slot's time check passes, Stage 21A's own order fixes the disposition of
any failure, and every such failure records stop_reason OPERATION_FAILURE:

1. Authorization, intent, profile and parameter validation fail before any
   attempt claim is created (Stage 21A section 5.2). The slot is NOT_ATTEMPTED
   and no claim is created or consumed.
2. Exclusive attempt-claim creation precedes credential resolution (Stage 21A
   section 5.3). A failure from claim creation onward, before any lease-evidence
   record is stored, is ATTEMPTED_NO_OBSERVATION. A failure after lease evidence
   is stored but before the first transmission is FAILED with its stored
   NOT_SENT observation. A claim-store or other storage failure instead returns
   an error under this section's storage rule.
3. Failures after a transmission follow sections 3 and 4.
The transport must enforce its monotonic deadline; completed_at is acquisition
termination time, not later serialization time. created_at records actual report
creation and may be later. Persist the valid prefix after acquisition stops.
A clock-integrity failure or deadline overrun that prevents valid timestamps
returns an error but retains already durable Stage 21A evidence; it never
deletes that evidence. 14 x 60 seconds is not a completion promise: slow cycles
end partially rather than executing on expired verification.
Retry only classified DNS/connect/TLS/connection-loss failure before headers,
once per whole logical operation, 250 ms delay. Never retry HTTP responses,
including 5xx, parsing errors or rate limits. Never renew credentials or resume
an interrupted cycle automatically. Clock failure stops collection.

Partial collection can produce PARTIAL/UNAVAILABLE sections only if all retained
records validate and persistence succeeds. Invalid request/schema, corrupted
references or storage failure returns an error, not a report. Never overwrite
conflicts or delete failed evidence. Store only sanitized projections and safe
diagnostics permitted by 21A; raw response content/secrets are not report data.

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
partial/denied rulesets; check SHA/issuer/state retention; stale/dismissed reviews;
same-account review shown without independence; test-merge SHA before merge;
merged with null SHA/actor; wrong commit linkage; parent ordering; squash/rebase
shape; post-merge checks on wrong SHA; unsupported artifacts; null/unknown enums;
corrupt references; unknown fields; timeout/rate/byte/page/budget exhaustion;
one retry per paginated operation; persistence conflict; mode mixing; and proof
that no readiness/signing/mutation path is reachable in the installed package.

Initial implementation requires separate authority after review and adoption
and is fixture-only, with no live transport or credentials. Test provenance is
explicit; a test package cannot become live by changing a flag or editing a
record. Any live-capable artifact requires separate review and authorization.
Obtain actual Windows/macOS/Linux and installed-package evidence before claims.

Next gate: exact-draft review of this consolidated candidate, its additive
supersession and the draft adoption record named in section 2. Author
self-check is not independent approval or Council PASS.
Remediation acceptance also requires wrong-repository/SHA reference injection,
swapped PR slots, omitted plan slots, duplicate attempt digests, absent conditional
authorization, open-to-merged between reads, changed linkage, missing final read,
ten-page exhaustion and the complete 91-transmission worst-case budget;
protection HTTP rejection with final PR still observed; rate-limited protection
stopping; insufficient time before a later slot; proof that every operation of
an admitted cycle starts before and ends no later than its profile-verification
expiry, including the E = D boundary under a frozen fixture clock; T0 taken
after validation and before slot 1, with no claim or network operation before
it; retained prefix; new projection-set/profile binding and old-validator
rejection; pre-issued merge authorization with changed final SHA;
null expected_human_id; open PR with merged_by null and merged PR with null
actor and null SHA, each remaining a complete identity-matched observation;
merged PR with null actor and non-null expected_human_id yielding UNKNOWN,
never DIFFERENT_ACCOUNT; non-User actor yielding UNKNOWN; equal and unequal
actor IDs yielding SAME_ACCOUNT and DIFFERENT_ACCOUNT; a FAILED merge_commit read
leaving commit_source null and parents_comparison UNKNOWN; an authorization
expiring mid-cycle so that a later slot fails validation before claim creation,
yielding NOT_ATTEMPTED with no claim and OPERATION_FAILURE; missing lease and
provider authentication failure at a later slot after a nonempty durable
prefix, yielding ATTEMPTED_NO_OBSERVATION with a retained claim and no
fabricated observation; an injected failure after stored lease evidence and
before transmission, yielding FAILED with its NOT_SENT observation; and each
section 3 coverage branch, with transmission state explicit:
branch 1, POST_MERGE_CHECKS in an initial report (NOT_REQUESTED);
branch 2, post_action with null merge linkage leaving all three conditional
slots with null observations, and separately a merge_commit failing before
transmission as ATTEMPTED_NO_OBSERVATION (UNAVAILABLE);
branch 3, post_action with all three conditional slots OBSERVED,
identity-matched and pagination-complete (COMPLETE_WITHIN_ENDPOINT);
branch 4, merge_commit failing after transmission with a retained incomplete
observation, and separately CHECKS with head_checks OBSERVED and head_status
failing after transmission (PARTIAL).

Official GitHub documentation establishes repository_hash_algorithm.get: the
endpoint is documented, accepts GitHub App installation tokens, and requires
Metadata repository permission (read), consistent with Stage 21A section 7.2.
That closes the documentary question only. Live preflight remains blocked until
a separately authorized fixture/live qualification of that operation. Do not
remove the inherited verification gate or invent an alternative endpoint
silently.

No runtime changes, signing, key creation, credentials, GitHub settings, commit,
push, PR, merge, Stage 21D, production, KOS or IDM operation is authorized here.
