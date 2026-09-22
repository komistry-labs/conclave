# Factual PR assistant — technical review 0001

Date: 2026-09-19
Verdict: CHANGES_REQUIRED / NOT FREEZE-READY
Reviewer: Adrian, author-side technical review; not independent Council approval.

Exact candidate: INCREMENT-21C-FACTUAL-PR-ASSISTANT-PROTOCOL.md
SHA-256: `1e16cbd0c79f7a1291a74816604496d607b30cc16fdbedead819f4e28d40b11f`
Git blob: `8c1ee4efa540c29090af06e2b0f2a9c2c514cb1f`
Local base: `154394c570a9919fc00b7c00779f565f742508e2`

## Scope and method

Read the exact candidate and compare its lifecycle with frozen Stage 21A
sections 5.2-5.3 and human-merge Erratum 0001's review boundary. This is a
document consistency review, not runtime, platform, live GitHub or independent
provider evidence. No candidate edits, runtime changes or remote writes made.

## Blocking findings

### F1 — Observations can be referenced without complete target binding

Sections 3-4 require hash verification and request/profile agreement, but do not
explicitly require every referenced observation to bind the request's repository,
profiles, operation parameters and section role. A valid, complete check record
for a different SHA could satisfy the stated coverage predicate. pr_before and
pr_after also lack an explicit membership/type/chronology constraint.

Required correction: define a per-section operation/parameter binding table;
require all pointers to be members of observations, enforce exact source identity
and time/role matching, and reject rather than merely label mismatched references.
Test valid hashes from wrong repositories/SHAs and swapped PR pointers.

### F2 — No deterministic merge-source selection across the two PR reads

Section 5 derives merge facts without selecting pr_before or pr_after. A PR
could be open before and merged after collection, or merge linkage could change.
Implementations could derive different Merge objects from the same source set.

Required correction: select the final complete PR observation as the merge-state
source, explicitly handle disagreement, and define when commit/check reads occur
relative to that observation. If linkage is unavailable within the admitted plan,
report unavailable; never combine actor/SHA facts from different snapshots.
Test open-to-merged, changed linkage and missing final observation.

### F3 — Repeated reads need explicit distinct authorization binding

The plan requires two identical PR operations. Stage 21A's attempt digest binds
authorization_hash and parameters, not the new intent UUID. Reusing the same
authorization with identical bounds/parameters produces the same single-use
attempt claim and blocks the second read.

Required correction: explicitly require separately issued, distinct authorization
hashes for before/after reads and later cycles; fail preflight on duplicate
attempt digests. Do not alter Stage 21A replay protection or mint authority in
the coordinator. Test duplicate and distinct authorization bindings.

### F4 — Coverage and budget rely on an unrecorded operation plan

Section 3 says COMPLETE_WITHIN_ENDPOINT means every planned source completed,
but the request/report has no closed plan binding. Ruleset detail discovery and
optional post-merge calls alter the set. An offline verifier cannot distinguish
an intentionally smaller plan from omitted evidence, or reproduce completeness.

Required correction: define a deterministic mandatory plan from request purpose,
retain an exact bounded plan/evidence binding including discovery expansion,
and derive section coverage from it. Reserve final PR and conditional merge
reads; prove the total including retries before dispatch. Test missing planned
operations, truncated detail discovery and reservation exhaustion.

## Positive findings

- No overall readiness verdict, signed-approval substitute or mutation path is
  proposed. Missing evidence is not represented as no protection.
- Pre-merge test SHA is explicitly excluded from actual merge interpretation.
- No new REST route or permission is proposed; artifacts remain unsupported.
- Signature, identity, independence and continuity limitations are explicit.
- HTTP retries now agree with Stage 21A's restrictive rule.

## Disposition

Keep the factual-only scope. Correct F1-F4 in the local candidate, preserve this
exact review, then recheck corrected bytes before independent review and freeze.
These are bounded evidence/lifecycle defects, not a reason to restart the key
ceremony or expand into a new identity/security system. No freeze, implementation,
commit, push or merge approval is conferred by this review.
