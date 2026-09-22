# Stage 21C Factual PR Assistant — Council technical review 0001

Date: 2026-09-19
Status: 2/5 PASS_EXACT_DRAFT; 3/5 FAIL_EXACT_DRAFT / NOT FREEZE-READY

## Provenance and authority

Arthur requested convening the Council on Claude's corrected candidate. Five
separate Codex subagent seats performed bounded read-only reviews. These are
internal same-provider technical reviews, not five distinct providers, human
Council votes or independent cross-provider assurance. No external API credential
or separate provider billing route was used. Ordinary Codex usage still applies.
The coordinating author did not vote. Seats received no other seat's findings
before their verdicts. All five ran; no early-stop shortcut was taken.

This record summarizes their returned findings and preserves their exact verdicts.
No semantic aggregation runtime or council.py was executed. The arithmetic tally
does not confer approval. Arthur's decision remains unfilled:

```json
{"arthur_decision": {}}
```

## Exact object

- Candidate: INCREMENT-21C-FACTUAL-PR-ASSISTANT-PROTOCOL.md
- SHA-256: `e939fe1e32ded72714db6da22823822fbd2b4eb4acc4a8dd9969eeae6b43a0d6`
- Git blob: `7428e43533235c71f80aa705d19766b9ffcbd98d`
- Bytes: 24,458; LF: 391; CR: 0.
- Local HEAD: `154394c570a9919fc00b7c00779f565f742508e2`.

Every seat independently verified both candidate hashes. Coordinator verified
them before and after review. Candidate and pre-existing documents were not edited.
The starting worktree had 18 untracked drafting files and no tracked/index diff.
No ownership or Git configuration change was needed for these checks.

## Seat returns

| Seat | Agent | Verdict |
| --- | --- | --- |
| 1 Governance, authority and supersession | factual_governance | PASS_EXACT_DRAFT |
| 2 Security, credentials and permission semantics | factual_security | PASS_EXACT_DRAFT |
| 3 GitHub and Git correctness | factual_git | FAIL_EXACT_DRAFT |
| 4 Evidence, schema and record algebra | factual_schema | FAIL_EXACT_DRAFT |
| 5 Determinism, time and cross-platform testability | factual_time | FAIL_EXACT_DRAFT |

Seat 1 established no governance blocker: factual-only scope, prospective
supersession and human-only merge remain explicit. Seat 2 established no security
blocker: authorization/lease isolation, no mutation, restrictive failure handling
and no overall success verdict remain intact. Their passes cover their assigned
remits only and do not override another seat's blockers.

## Blocking findings, deduplicated

### CR1 — New nullable merge fields conflict with inherited completeness

Raised by seat 3 as G1. Candidate section 5 against Stage 21A section 8.2.
Stage 21A makes null identity-bearing objects incomplete or identity-mismatched.
The new merged_by is identity-bearing and nullable, but the candidate does not
explicitly exempt it from that inherited whole-observation rule.

An ordinary open PR with merged_by:null can therefore make pr_before incomplete
and stop all later collection. A merged PR with a null actor can also lose the
advertised factual report with unknown actor. Another implementer might continue
by treating the actor alone as unavailable: the text permits divergent readings.

Minimum correction: narrowly state that null values in the two new informational
merge fields do not themselves clear PR completeness or target identity_match.
Only linkage/actor availability changes. Missing/malformed fields still reject;
original repository/head identity completeness rules remain unchanged. Add open
PR null-actor and merged PR null-actor/SHA fixtures.

### CR2 — Attempted operation without an observation has no Step state

Independently raised by seats 4 (S4-1) and 5 (T1). Candidate sections 3, 4 and 6
against Stage 21A section 10's no-observation pre-transmission failures.

After a valid completed prefix, a slot can create an attempt claim and fail
credential resolution/authentication before lease evidence is stored. Stage 21A
intentionally preserves the claim and emits a safe diagnostic, with no observation.
FAILED requires an observation; OBSERVED is false; NOT_APPLICABLE is forbidden;
NOT_ATTEMPTED misstates the attempted claim/credential work. Yet the candidate
promises a prefix report, which has no honest Step representation for this case.

Minimum correction: either add one closed attempted-without-observation branch
with permitted safe-reason/evidence binding, or explicitly make this a reportless
error preserving all existing durable evidence and qualify the prefix-report
promise. Do not fabricate a Stage 21A observation. Test missing lease or provider
auth failure at a later slot after a nonempty durable prefix.

### CR3 — POST_MERGE_CHECKS coverage is not single-valued

Raised by seat 4 as S4-2. Section 3 requires PARTIAL when a section has any
source but is incomplete. Section 5 says linkage failure is otherwise UNAVAILABLE.
A failed merge_commit read with a valid incomplete observation therefore requires
both values. Initial reports similarly collide with section 3's NOT_REQUESTED.

Minimum correction: one ordered algorithm in section 3: initial post-merge
section -> NOT_REQUESTED; otherwise no sources -> UNAVAILABLE; otherwise all
section slots complete -> COMPLETE_WITHIN_ENDPOINT; otherwise PARTIAL. Section 5
should constrain dispatch but refer to that coverage algorithm rather than
override it. Test initial, failed commit, null-linkage and partial-check cases.

## Non-blocking notes and verified factual update

- All relevant seats independently derived seven single-page plus seven ten-page
  slots: 77 pages + 14 retries = 91 maximum transmissions. Stage 21A authorization
  totals also equal 7*2 + 7*11 = 91.
- Seat 5 found Claude's dead-enum removal and verification-pair reservation sound
  at the arithmetic level. It reported an abstract 931-case timing check, not a
  runtime test. Reserving whole slot durations including credential/persistence
  handling remains important. Equality of verification expiry and D in zero-time
  fixtures is harmless; >= is sufficient, not strictly >.
- Deferral of Stage 21C signing does not remove Stage 21A's signed credential-
  provider lease verification and key pinning. Do not describe eventual live
  operation as requiring no cryptographic provider boundary.
- Older frozen readiness summaries should remain historical in current-state
  records, not be edited retroactively.
- Seat 3 and coordinator checked official GitHub documentation: the hash-algorithm
  endpoint is documented, accepts GitHub App installation tokens, and requires
  Metadata repository permission (read). The correction record's documentary
  permission uncertainty is therefore stale. This closes documentation uncertainty,
  not separately authorized fixture/live qualification:
  https://docs.github.com/en/rest/repos/repos#get-the-hash-algorithm-for-a-repository

## Work performed and remaining boundary

Read-only document/hash checks, independent seat analysis, public official-doc
inspection and arithmetic only. No implementation, credential access, signing,
live adapter calls, runtime/fixture/platform acceptance, commit, push, PR, merge,
branch-protection change, KOS/IDM change or production operation occurred.

Next: return these three bounded findings to Claude for remediation. Fresh exact-
draft review is required after any byte change. No freeze or adoption requested
on this failed candidate. No authority decision is inferred from the review tally.
