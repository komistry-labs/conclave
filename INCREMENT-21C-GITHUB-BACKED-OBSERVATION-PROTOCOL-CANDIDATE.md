# Stage 21C GitHub-backed observation protocol candidate

Date: 2026-09-19
Status: LOCAL DRAFT / NOT FROZEN / NOT IMPLEMENTATION AUTHORITY

## 1. Purpose and assurance boundary

Implement Arthur's selected GitHub-backed human-approval direction as a proposed
replacement profile. CONCLAVE observes and explains; the human uses GitHub to
approve or merge. Account 2FA is an account safeguard, not signed evidence of a
particular action. No ceremony, external signing provider or operational trust
store is required by this profile. None is silently removed from the old one.

The result is advisory and point-in-time. It cannot prove uninterrupted policy
enforcement, absence of undisclosed bypass, independent issuer authenticity,
human identity from a username, or use of 2FA during a particular merge.

## 2. Required governing replacement

Local drafting base: `154394c570a9919fc00b7c00779f565f742508e2`.
All historical frozen bytes remain unchanged.

Adoption requires an additive governing instrument explicitly replacing the
signed Stage 21C profile, not an unsigned extension of its validators:

- Increment 21 master SHA-256
  `89a05211a4323db2e79d2854952b24ce033c71f357430c7ac839457ff0878d75`,
  as modified by human-merge Erratum 0001 SHA-256
  `a0fa63884be7970e9c0463014b1091f118bc32d0702fc7ebb5402a8410a5c742`:
  replace the erratum's sections 4-6, 8-11 and 13 only where they require
  signed-profile readiness, no-bypass attestation, external human authorization,
  its record reservations, lifecycle, or their acceptance criteria. Corresponding
  master requirements must explicitly select this reduced-assurance profile.
  Keep sections 7 and 14's zero-mutation boundary and deferred automatic merge.
- Readiness SHA-256
  `d3701754c7ab782835bc92db07c055509e415a69765373ed5cd30f250164b257`:
  replace its operational profile in full, rather than mixing unsigned and
  signed record families or reusing its `ready` predicate.
- Collection SHA-256
  `6ea468c1cdd3a4ac0befecd3ffa3c2c26cfb51218902fb3af20366e4dbbb91c2`:
  defer its external attestation implementation. Do not represent observations
  from this profile as successful execution of that collection protocol.

This is a proposed supersession scope, not an applied amendment. Before freeze,
review must finish the clause-by-clause master compatibility check. Stage 21A,
Stage 21B, Stage 21D, KOS and IDM are not changed. Existing signed-profile
consumers must reject all new discriminators. No automatic downgrade on missing
keys, invalid signatures or unavailable control evidence is permitted.

## 3. Actors and credentials

Separate the read-only observation installation, configured human merge actor,
PR author and independent reviewers. Use numeric GitHub IDs, not display names.
Account IDs alone do not establish that different people control two accounts.
Any required person-level separation needs an explicit, reviewable human
mapping; unknown separation is UNKNOWN, known same-person approval is BLOCKED.

The adapter never acquires the human's browser session, token, 2FA code, recovery
code or key. A later live collector must use separately authorized read-only
installation credentials under Stage 21A's lease boundary. No credential access
or live transport is authorized by drafting or testing this document.

## 4. Closed proposed record model

These are schema specifications, not implemented schemas. All records use the
Stage 21A canonical encoding, hashing (excluding the content-hash field), strict
parsing and immutable storage contract after compatibility verification. Reject
unknown keys, duplicate JSON names, invalid numbers, invalid Unicode and excess
size before reduction. Records never contain arbitrary executable instructions.

Common fields, all required:

| Field | Type / rule |
| --- | --- |
| schema_version | Exact family literal below |
| protocol_sha256 | Lowercase 64-hex adopted protocol identity |
| mode | `fixture` or `live`; never mixed within a chain |
| repository_id, pull_number | Positive integers; booleans rejected |
| base_sha, head_sha | Exact object IDs under pinned Stage 21A object format |
| observed_at | Canonical UTC timestamp under Stage 21A |
| authority_effect, decision_effect, membership_effect | Literal `none` |
| production_use_allowed, merge_authorized | Literal false |
| content_hash | Canonically derived SHA-256 |

Additional fields are exactly the following, with no extra extension map:

1. `github-advisory-snapshot/0.1.0`: `cycle_id` (64 lowercase hex),
   `profile_sha256` (64 hex), `started_at`, `completed_at` (timestamps),
   `sources` (0-96 Source entries), `criteria` (exactly one Criterion for each
   code below), `limitations` (sorted unique codes, at most 32).
2. `github-advisory-assessment/0.1.0`: `snapshot_sha256` (64 hex),
   `result` (SATISFIED_AS_OBSERVED/BLOCKED/UNKNOWN), `expires_at` (timestamp),
   `failed_criteria`, `unknown_criteria` (sorted unique criterion-code lists).
3. `github-advisory-post-action/0.1.0`: `assessment_sha256` (64 hex),
   `snapshot_sha256` (64 hex of new observation cycle), `pr_state`
   (OPEN/CLOSED_UNMERGED/MERGED/UNKNOWN), `merge_sha` (object ID or null),
   `ordered_parents` (0-2 object IDs), `merge_actor_id` (positive integer or
   null), `comparison` (MATCH/MISMATCH/UNKNOWN), `reasons` (sorted unique
   codes, at most 32). The common head/base retain the assessed target;
   newly observed head/base are those of the referenced new snapshot.

Source is closed: `operation_key` (Stage 21A allowlisted literal), `sequence`
(integer 1-96), `captured_at` (timestamp), `body_sha256` (64 hex),
`evidence_ref` (Stage 21A hash-safe immutable reference), `coverage`
(COMPLETE/PARTIAL/UNAVAILABLE). References must resolve to retained, sanitized
evidence, not cookies, tokens or unrestricted response dumps. A local hash
does not prove that GitHub supplied the bytes.

Criterion is closed: `code` (enum below), `state` (SATISFIED/FAILED/UNKNOWN),
`source_sequences` (sorted unique integers 1-96), `reason`
(OBSERVED_MATCH/OBSERVED_FAILURE/MISSING/STALE/CONFLICT/UNSUPPORTED/INCOMPLETE).
SATISFIED requires OBSERVED_MATCH and nonempty complete supporting sources;
FAILED requires OBSERVED_FAILURE and nonempty supporting sources; UNKNOWN
requires one of the other reasons. No caller-provided verdict is trusted.

Criterion codes: TARGET_BINDING, REQUIRED_CHECKS, REQUIRED_REVIEWS,
PERSON_SEPARATION, CONVERSATIONS, CODE_OWNER, LAST_PUSH, POLICY_COVERAGE,
ADMIN_ENFORCEMENT, FORCE_PUSH_DELETION, BYPASS_VISIBILITY, ACCOUNT_SECURITY.
Inapplicable policy requirements need complete evidence of inapplicability;
they are not inferred from an empty array. ACCOUNT_SECURITY may remain UNKNOWN
when no admitted source establishes it. A login is insufficient.

Each record is at most 1 MiB canonical bytes. No record may refer to itself or
a future object. Snapshot -> assessment -> new snapshot -> post-action is the
only chain. Reopening verifies hashes, target, profile, mode and time binding.

## 5. Deterministic results and human action

Invalid schema or corrupted evidence produces a validation error and no usable
assessment. For valid evidence, any FAILED criterion yields BLOCKED; otherwise
any UNKNOWN yields UNKNOWN; otherwise SATISFIED_AS_OBSERVED. Failed and unknown
criteria are both retained even when failure takes precedence.

Assessments expire no later than 300 seconds after snapshot completion. They
also cease to be current on observed target or policy drift. Missing time,
clock rollback or conflicting observations yield UNKNOWN. No old signed-profile
success record can be emitted, and no advisory result is a merge capability.

The human independently checks the current GitHub PR and decides whether to
act within existing authority. No automatic approval, review submission,
merge, queue, auto-merge, setting change, browser control or polling for a
human action occurs. A later observation needs a separate bounded read request.

Post-action MATCH is limited to a normal two-parent merge whose ordered parents
equal assessed base then head, whose observed PR head equals assessed head,
and whose merge actor equals the configured human. Missing supporting evidence
yields UNKNOWN; contradictory evidence yields MISMATCH. OPEN/CLOSED_UNMERGED
produce UNKNOWN comparison, never a fabricated successful match. Squash/rebase
cannot be coerced into MATCH. MATCH is structural only: it does not prove the
merge tree was independently reviewed or controls were continuously enforced.

Post-merge CI/artifact status is reported from the new snapshot only when
exact merge-commit binding is supported; pre-merge checks do not establish it.
The final schema must distinguish these checks before implementation.

## 6. Transport and resource envelope

Only the frozen Stage 21A read endpoint table is eligible. No arbitrary method,
URL, query, redirect, operation key or mutation can be supplied by callers.
Evidence that needs an unavailable endpoint stays UNKNOWN until a separately
reviewed read-only extension is adopted. This draft creates no extension.

Per cycle: at most 48 page transmissions plus at most one additional retry
per admitted Stage 21A operation, 96 transmissions total and 96 evidence slots;
each retry consumes transmission and evidence
capacity even if no usable body arrives. A smaller deterministic endpoint plan
must be admitted before collection. Reserve worst-case retry capacity; never
start a read/page without capacity. Pagination counts as additional reads.

Ceilings: 600 seconds total; 10 pages/list; 100 items/page; 1000 items/list;
100 review threads; 2 MiB decompressed per response and 32 MiB total.
Use the stricter inherited Stage 21A limit wherever it is lower. No truncation
or joining partial cycles. Stage 21A section 7.3 controls retries: only classified
DNS, connect, TLS-handshake or connection-loss failure before response headers;
one retry across the entire paginated operation, not one per page. Never retry
an HTTP response, including 502/503/504. Retain its 250 ms retry delay, five-second
connect/TLS, twenty-second socket read and sixty-second operation deadline.
Stage 21A section 6.5 time, lease and persistence gates remain mandatory.
Stop on rate limiting. No renewed lease or resumed partial cycle is permitted.

## 7. Acceptance and next gates

The initial implementation, after protocol adoption and separate authorization,
is fixture-only: no credentials, live transport, signing, trust-store loading
or browser automation. Synthetic evidence must remain marked fixture and cannot
be converted into live evidence by a runtime flag or file edit.

Required tests: every reduction combination; malformed records; duplicate IDs;
unresolved references; tampering; target/mode/profile mismatch; stale and
dismissed reviews; wrong check issuer; same-person review; unresolved threads;
ruleset omission; unknown bypass; missing account-security evidence; drift;
expired assessment; pagination loops; byte/time/read-budget exhaustion; retry
accounting; wrong merge parents/actor; squash/rebase; pre/post-CI confusion;
and rejection by old signed-profile consumers. Verify installed-package lack
of mutation paths and obtain actual Windows/macOS/Linux evidence.

Before exact-draft review/freeze, close these design tasks:

1. Complete precise master/erratum supersession and precedence text.
2. Map each criterion to an admitted source and exact deterministic reducer;
   explicitly mark unsupported criteria rather than promising universal success.
3. Finalize closed evidence/projection types, limitation/reason enumerations,
   policy input schema, post-merge CI/artifact projection and freshness rules.
4. Review endpoint/privacy/budget compatibility with Stage 21A.

This draft is not freeze-ready while these tasks remain. No Council or
independent PASS, runtime testing, platform acceptance, commit or push is claimed.
The new direction is recorded; the old frozen baseline remains authoritative
until the additive replacement is reviewed and adopted.

## 8. Source compatibility findings and conservative first reducer

This section narrows the candidate where earlier descriptions imply unavailable
data. It is based on the frozen Stage 21A sections 7.2 and 8 projections, not
assumptions about additional raw GitHub fields. No live API was used.

| Criterion | Admitted source | Conservative reduction |
| --- | --- | --- |
| TARGET_BINDING | repository.get, repository_hash_algorithm.get, ref.get, pull_request.get | SATISFIED only for complete matching repository/object format/base/head/ref observations; explicit mismatch FAILED; incomplete UNKNOWN |
| REQUIRED_CHECKS | branch_protection.get, check_runs.list, combined_status.get | UNKNOWN until effective requirements and issuer selectors are established; a conclusively required failing check can yield FAILED, never infer requirements from check success |
| REQUIRED_REVIEWS | branch_protection.get, reviews.list | UNKNOWN for complete approval sufficiency: review records alone do not establish current reviewer permissions or full applicable policy |
| PERSON_SEPARATION | none | UNKNOWN/UNSUPPORTED; different account IDs do not establish different people |
| CONVERSATIONS | review_comments.list is insufficient | UNKNOWN/UNSUPPORTED; comments do not establish thread resolution |
| CODE_OWNER | branch_protection.get and reviews.list are insufficient | UNKNOWN/UNSUPPORTED; requirement flag does not establish ownership or qualifying owner review |
| LAST_PUSH | branch_protection.get and reviews.list are insufficient | UNKNOWN/UNSUPPORTED; exact last-pusher approval eligibility is not projected |
| POLICY_COVERAGE | branch_rules.list, repository_rulesets.list, repository_ruleset.get | UNKNOWN; conditions and parameters are hashed then discarded, preventing full policy normalization |
| ADMIN_ENFORCEMENT | branch_protection.get | Explicit disabled enforcement yields FAILED; enabled flag alone leaves UNKNOWN because effective ruleset/bypass coverage is incomplete |
| FORCE_PUSH_DELETION | branch_protection.get | Explicit allowed force-push or deletion yields FAILED against this profile's restrictive policy; disabled flags alone leave UNKNOWN for overall effective policy |
| BYPASS_VISIBILITY | repository_ruleset.get | UNKNOWN; Stage 21A explicitly admits incomplete_by_permission or observed_not_attested, neither is proof of complete absence |
| ACCOUNT_SECURITY | none | UNKNOWN/UNSUPPORTED; neither account 2FA status nor organization enforcement is projected |

Consequently this first profile always reports BLOCKED or UNKNOWN overall under
current projections. It still exposes exact target state and observed failures.
It must never present an all-green indicator or claim operational merge readiness.
Enabling SATISFIED_AS_OBSERVED in real use needs separately reviewed source/schema
extensions or an explicit later scope reduction; callers cannot disable criteria.

For REQUIRED_CHECKS, the conservative first reducer returns UNKNOWN unconditionally
until an effective-policy reducer is adopted. Raw failing checks may be displayed
as observed facts but not elevated to policy failures. This closes ambiguity in
the table without guessing which checks are required. Likewise REQUIRED_REVIEWS
does not count apparent approvals as sufficient. All unavailable criteria above
remain UNKNOWN even when a branch-protection flag is absent or disabled.

Post-action limitations: Stage 21A pull_request.get does not retain merge commit
SHA or merged-by actor. Thus post-action MATCH is unreachable in this first
profile; merge_sha and merge_actor_id remain null, ordered_parents empty and
comparison UNKNOWN, with reason POST_ACTION_LINKAGE_UNAVAILABLE. The PR's merged
boolean may be reported as GitHub-observed state, not verified merge linkage.
Artifact publication has no admitted endpoint and remains UNSUPPORTED. Commit
checks are not relabelled post-merge CI without independently observed linkage.

## 9. Proposed additive supersession wording

On later exact adoption, this candidate's profile is the selected Stage 21C
advisory-observation profile. The prior signed readiness and collection profiles
remain historical and may not be used as compliance claims for this profile.

For Stage 21C only, the following existing requirements are replaced by sections
1, 3, 5, 6 and 8 of this candidate: master's section 4 Stage 21C, section 6 Stage
21C record reservations, section 8 invariants 8-12, section 10 Stage 21C readiness,
authorization and no-bypass acceptance requirements, and section 12 decisions
5-7 to the extent they require signed readiness/external attestation or prescribe
human-authorization evidence. Decision 7's administration-read-only restriction
is retained. Other Stage 21A/21B obligations in those sections are unaffected.

For human-merge Erratum 0001, replace sections 4-6, 8-11 and 13 only as applied
to signed readiness, authorization evidence and Stage 21C acceptance with this
candidate's advisory lifecycle and new record families. Retain the human-only,
normal-merge boundary and all zero-mutation restrictions. Replace its section 9
lifecycle with: validate -> authorized read -> store advisory observations ->
stop -> separately requested authorized read -> store factual post-action report.
No signed readiness or authorization record is required or synthesized.

Master/erratum threat requirements remain acceptance obligations where applicable;
signature/custody-specific tests are explicitly deferred with that capability,
not marked passed. No automatic merge or operational authorization is introduced.
Any unresolved normative conflict blocks adoption rather than choosing a weaker
interpretation. This text is a proposal until exact review and Arthur adoption.

## 10. Record-definition corrections and remaining closure

Use the Stage 21A hash type (`sha256:` followed by 64 lowercase hex) for every
hash/reference field above, including content_hash; this overrides the earlier
bare-hex shorthand. Object IDs retain the repository's SHA-1/SHA-256 format.
cycle_id remains bare 64-hex and is an identifier, not an evidence hash.

Source entries reference retained Stage 21A observation projections, never raw
responses. Rename body_sha256 to projection_sha256. The digest covers the
canonical sanitized projection; it does not claim a hash of original wire bytes.
Each sequence is contiguous from 1. Source references are unique by observation
hash and operation. Transmission failures consume the budget but are not invented
source entries; preserve them through Stage 21A outcome evidence. Missing required
observations yield UNKNOWN. Do not require a body hash for a missing body.

Closed limitations enum: NO_INDEPENDENT_SIGNATURE, NO_INTERVAL_CONTINUITY,
BYPASS_COVERAGE_UNAVAILABLE, ACCOUNT_SECURITY_UNAVAILABLE,
PERSON_SEPARATION_UNAVAILABLE, EFFECTIVE_POLICY_UNAVAILABLE,
POST_ACTION_LINKAGE_UNAVAILABLE, ARTIFACTS_UNSUPPORTED.
All eight are required in the first profile's snapshot limitations array.
Closed post-action reasons enum: POST_ACTION_LINKAGE_UNAVAILABLE,
OBSERVED_TARGET_MISMATCH, SOURCE_INCOMPLETE, PR_NOT_MERGED.
The first profile always includes POST_ACTION_LINKAGE_UNAVAILABLE. Other codes
are included only when the respective fact is observed. Sort and deduplicate.

Snapshot sources must fall within started_at <= captured_at <= completed_at;
observed_at equals completed_at. Assessment observed_at must be at or after
completion and at most 300 seconds later; expires_at equals completion + 300
seconds. A post-action snapshot is a separate cycle and never refreshes the
earlier assessment. Expiry does not prevent historical factual reconciliation.

Remaining pre-freeze blockers: normalize these corrections into one coherent
schema text rather than layered overrides; bind the immutable policy/profile
input and configured human identity; define exact partial-observation retention
and post-action common-field consistency; complete independent review of the
supersession scope. No freeze-readiness claim is made by this draft.
