# Stage 21C Factual PR Assistant — Council technical review 0002

Date: 2026-09-19
Status: 1/5 PASS_EXACT_DRAFT; 4/5 FAIL_EXACT_DRAFT / NOT FREEZE-READY

## Provenance and authority

Arthur requested a Claude-appointed Council performing the same five functions as
review 0001. Five separate Claude subagent seats performed bounded read-only
reviews at Opus.

These are internal same-provider technical reviews. They are **not** five
distinct providers, human Council votes, or independent cross-provider assurance
— the same limitation review 0001 recorded for its five Codex seats. No external
API credential or separate provider billing route was used.

One property does improve across rounds rather than within one: review 0001 was
Codex-provider and review 0002 is Claude-provider, on successive candidates. That
is sequential cross-provider exposure, not concurrent cross-provider assurance,
and it does not satisfy a five-distinct-provider requirement if one is imposed.

The coordinating author did not vote and is the author of the corrections under
review. Seats received no other seat's findings before returning verdicts. All
five ran; no early-stop shortcut was taken. No `council.py` or aggregation
runtime was executed; the tally below is arithmetic and confers no approval.

Arthur's decision remains unfilled:

```json
{"arthur_decision": {}}
```

## Exact object

- Candidate: `INCREMENT-21C-FACTUAL-PR-ASSISTANT-PROTOCOL.md`
- SHA-256: `84c0b1e3c74370667583b14c8b0f4ebb3f1df63ad4126b3fc7f3cc5c4a12f26c`
- Git blob: `92d835bad36f4d9e51fe17cc8e196fa1be6e2b85`
- Bytes: 26,952; LF: 432; CR: 0
- Local HEAD: `154394c570a9919fc00b7c00779f565f742508e2`

Every seat independently recomputed both hashes and matched. The coordinator
verified them before and after review: the candidate and both preserved
predecessors (`e939fe1e…`, `b73676b1…`) are byte-unchanged. No seat edited,
created or deleted any file. The worktree holds 21 untracked drafting files with
no tracked or index diff.

## Seat returns

| Seat | Verdict |
|---|---|
| 1 Governance, authority and supersession | FAIL_EXACT_DRAFT |
| 2 Security, credentials and permission semantics | PASS_EXACT_DRAFT |
| 3 GitHub and Git correctness | FAIL_EXACT_DRAFT |
| 4 Evidence, schema and record algebra | FAIL_EXACT_DRAFT |
| 5 Determinism, time and cross-platform testability | FAIL_EXACT_DRAFT |

Seat 2 established no security blocker and tested the round-2 hunks in its remit
directly. Its pass covers its remit only and does not override another seat's
blockers.

## Finding of record: the remediation itself introduced four defects

Four of the eleven blocking findings below (CR7, CR9, CR10, CR11) exist **only
because of** the round-2 remediation hunks, and none is a residue of CR1-CR3.
Two of those four are the same defect class the correction claimed to close:

- CR11 reintroduces an unconstructible acceptance fixture — the exact class of C1,
  which the previous round removed. The C2 "closure" widened §8 to demand a
  fixture for a guard that cannot fail.
- CR7 exists because the CR1 null-field exemption removed the Stage 21A §8.2
  guard that had been implicitly forcing `actor_comparison` to UNKNOWN, without
  extending the actor-comparison rule in the same hunk.

This is the "repairs that introduce new coupling" class the brief instructed
seats to hunt. It is recorded here as a process finding, not only as document
defects: three consecutive rounds have now closed findings while opening new ones
in adjacent text.

## Blocking findings, deduplicated

### CR4 — Section 2 displaces three merged freeze records it never names

Seat 1, G1. Section 2 names only the master protocol, Erratum 0001 and the two
profile documents. It names none of `INCREMENT-21C-PROTOCOL-FREEZE-RECORD.md`,
`INCREMENT-21-ERRATUM-0001-FREEZE-RECORD.md`, or
`INCREMENT-21C-CONTROL-ATTESTATION-COLLECTION-PROTOCOL-FREEZE-RECORD.md` — all
merged into protected `main` through PRs #21, #22 and #24 and present in the
candidate's own declared local base. The first designates `d3701754…` "the
selected implementation baseline for any later separately authorized Stage 21C
work" with seven binding requirements; the second states "Any later replacement
must conform to this frozen erratum." Rule 1 calls the profiles "historical".

Consequence: two conforming readers derive different Stage 21C governance
baselines from identical adopted bytes — one requiring readiness reduction,
no-bypass attestation, human-merge authorization evidence and reconciliation, the
other requiring none. Governance-layer two-implementer divergence.

Minimum correction: add a precedence rule naming those three records by file and
SHA-256 and stating exactly which clauses cease to select an implementation
baseline on adoption; delete or correct "historical" in rule 1. Alternatively
state that adoption is effective only through a new Arthur freeze record that
expressly supersedes their baseline-selection effect.

### CR5 — Erratum 0001 section 2 is displaced but not named

Seat 1, G2. Rule 3 replaces Erratum §§4-6, 8-11 and 13 but not §2, whose
operative text allocates to CONCLAVE "deterministic exact-head merge-readiness
evaluation" and "read-only post-action observation and reconciliation". The
candidate's §1 says "Never emit a readiness verdict" and abolishes reconciliation
records. An unreplaced clause of a frozen merged instrument contradicts §1.

Minimum correction: add Erratum §2 items 1 and 4 to rule 3's replacement list, or
state that §2 is descriptive of the superseded sections and carries no
independent normative force after adoption.

### CR6 — Rule 4's "only Stage 21A extension" claim is false on the candidate's own text

Seat 1, G3. Rule 4 states "The only Stage 21A extension is the versioned API
profile in section 5", but §5 declares two further displacements: an additive
precedence extending Stage 21A profile-reference validation, and the new
"Explicit additive precedence over Stage 21A section 8.2" null-field clause. The
latter displaces a Stage 21A **control**, not an API-profile record, so rule 4's
blanket "Retain … Stage 21A/21B controls" contradicts it.

Consequence: §2.5 ("Any remaining normative conflict blocks adoption") is
violated by the candidate against itself. Secondarily, an adopter applying rule 4
literally retains §8.2, under which `merged_by: null` yields
`identity_match:false`, TARGET cannot reach COMPLETE_WITHIN_ENDPOINT, and report
bytes differ from an adopter applying §5.

Minimum correction: add a sixth numbered rule naming Stage 21A §8.2's
null-identity sentence and §4.2's profile-reference validation as the exact and
only Stage 21A clauses receiving additive precedence, bounded respectively to the
two new fields and to the `github-factual-api-profile/0.1.0` family; amend rule
4 to enumerate all three extensions.

### CR7 — No actor-comparison arm for a null merged actor *(introduced by the CR1 repair)*

Seat 3, G1. §5's only rule is "Actor comparison uses expected_human_id if
non-null, otherwise UNKNOWN". No arm covers `Merge.actor_id = null` with
`expected_human_id` non-null. In the predecessor this state was unreachable
because Stage 21A §8.2 made a `merged_by: null` projection not-complete; the CR1
exemption removed that guard, and §8 now makes the state a mandatory fixture
("merged PR with null actor and null SHA").

Consequence: Reading A performs the comparison and yields `DIFFERENT_ACCOUNT` —
a positive factual assertion that a different account merged, manufactured from
unavailable data, contradicting §5's "null means unavailable, not invented
identity" and §1's factual-only scope. Reading B yields UNKNOWN. Nothing selects
between them, so the mandated fixture has no determinate expected value.

Minimum correction: replace the sentence with an exhaustive mutually exclusive
rule — UNKNOWN whenever `actor_id` is null, `expected_human_id` is null, or the
actor type is not `User`; otherwise SAME_ACCOUNT / DIFFERENT_ACCOUNT on equality;
and state explicitly that a null actor never yields DIFFERENT_ACCOUNT.

### CR8 — `Merge.commit_source` has no derivation rule for a failed merge-commit read

Seat 3, G2. `commit_source` appears only in §3's field list and implicitly in the
OPEN/CLOSED_UNMERGED arm. No clause states whether it is the incomplete
observation reference or null when `pr_after` is complete, `merged=true`, the
reported SHA matches, and the `merge_commit` slot is FAILED — a branch §8
mandates as a fixture.

Minimum correction: add one sentence — `commit_source` is the `merge_commit`
observation reference only when that slot is OBSERVED, complete, and its commit
SHA equals `Merge.merge_sha`; null in every other case, including a FAILED read.

### CR9 — §8's coverage fixtures do not cover the four branches *(introduced by the CR3 repair)*

Seat 4, finding 1. The four named fixtures map to branches 1, 4/2, 2 and 4.
Branch 3 (COMPLETE_WITHIN_ENDPOINT) is produced by none of them; branch 4 is
produced twice. "Failed merge-commit read" is itself two-valued because the
clause does not say whether the failure is pre- or post-transmission — the
distinction the new `ATTEMPTED_NO_OBSERVATION` disposition makes decisive. The
COMPLETE arm of the newly introduced algorithm has no fixture targeting it.

Minimum correction: replace the clause with an explicit branch-to-fixture
enumeration covering all four and unambiguous about transmission state.

### CR10 — §4's "That slot remains FAILED" antecedent *(introduced by the CR2 repair)* — SEATS DISAGREE

Seat 4, finding 2. The inserted sentence "That exception requires an actual
received HTTP response, so a pre-transmission failure recorded as
ATTEMPTED_NO_OBSERVATION never qualifies and always stops." now sits between the
sentence introducing the tolerated PROTECTIONS slot and "That slot remains
FAILED". The nearest antecedent of "That slot" is now the
ATTEMPTED_NO_OBSERVATION slot, which §3 requires to carry a null observation,
while FAILED requires a non-null one — an unsatisfiable Step.

**Seat 2 examined the same text and reached the opposite conclusion**, holding
that only one reading survives because the contradictory reading defeats itself
against both "always stops" and §3's nullity rule, so a conforming implementer is
forced to the PROTECTIONS antecedent — "Resolvable, not a divergence."

This disagreement is recorded, not resolved. The coordinator does not adjudicate
between seats. The minimum correction is trivial under either reading and is
recommended regardless: replace "That slot remains FAILED" with "The tolerated
PROTECTIONS slot remains FAILED", or move the inserted sentence to the end of the
paragraph.

### CR11 — The pre-pair guard cannot fail, and §8 mandates a fixture for its failure *(introduced by the C2 repair)*

Seat 5, F1. §6 requires `now+120 <= D` before the verification pair, where `D` =
acquisition start + 300 s. That predicate fails only if more than 180 s elapse
between the instant defining `D` and the immediately following check, and §4
places nothing between them but local validation. §8 nevertheless mandates
"insufficient time before dispatch, both before the verification pair and before
a later slot." The later-slot arm is reachable; the pre-pair arm is not.

Correction record 0001 §4 had itself conceded the predecessor guard was "Not
reachable as a failure, but not closed" — and the remediation then widened §8 to
demand a fixture for exactly that unreachable failure.

Minimum correction: either delete the "before the verification pair" arm from
§8's time fixture and restate §6's pre-pair reservation as a non-failing
preflight assertion in the class of §6's "Overflow is a preflight error"; or make
the arm reachable by anchoring `D` per CR12 and stating the resulting disposition
and `stop_reason`.

### CR12 — `D` is not well-defined

Seat 5, F2. §6 pins `completed_at` and `created_at` precisely but never fixes the
"monotonic acquisition start" instant that defines the sole binding deadline. §4
orders "Validate request and profiles" ahead of the verification pair without
saying which side of the stamp it falls on.

Consequence: two conforming implementers derive different `D` — one stamping at
request admission, one at first dispatch — then stop at different slots, retain
different prefixes, and disagree on whether §3's "elapsed at most 300 seconds"
holds for the same cycle. `D` governs every reservation, so the divergence
propagates to every slot, and CR11's reachability turns on it.

Minimum correction: define acquisition start as exactly one instant — e.g. the
monotonic reading taken immediately after request and profile validation succeed
and immediately before the verification-pair reservation, with `started_at` the
UTC instant of that same reading — and state that no operation may precede it.

### CR13 — The later-slot reservation's lease/authority arm has no defined outcome

Seat 5, F3. §6 requires "now+60 <= D, as well as valid lease/authority" but
supplies a consequence for the time arm only. Latent before; decisive now,
because `ATTEMPTED_NO_OBSERVATION` is defined as requiring that the attempt claim
already exists.

Consequence: for one real failure (stale, missing or unauthenticated lease at
slot k), implementer A evaluates lease/authority before creating the claim and
records NOT_ATTEMPTED with no claim consumed; implementer B creates the claim,
fails pre-transmission, and records ATTEMPTED_NO_OBSERVATION with a claim
**irreversibly consumed**. `stop_reason` differs too (TIME_BUDGET vs
OPERATION_FAILURE). Identical input yields different durable records and
permanently different Stage 21A claim state, not recoverable by a later cycle.
§8's fixture presumes implementer B.

Minimum correction: state in §6 that the lease/authority condition is not a time
condition, that its failure records OPERATION_FAILURE, and fix whether the
attempt claim is created before or after that check so the disposition is
determined to be exactly one of NOT_ATTEMPTED or ATTEMPTED_NO_OBSERVATION.

### CR14 — "strictly later than D" is asserted, not derived

Seat 5, F4. `E = S + 300` with `S >= T0` and `D = T0 + 300` yields `E >= D`;
strictness requires `S > T0` strictly, which the document does not establish and
which a second-precision or frozen fixture clock does not provide. §8 then
requires "proof that no admitted cycle can outlive its own profile verification",
stated over an inequality the document cannot derive, on exactly the
deterministic clock a fixture would use.

The underlying safety property (`E >= D`) does hold, so this is a boundary defect
rather than an unsafe one.

Minimum correction: replace "strictly later than D" with "no earlier than D" and
state that an operation whose monotonic deadline falls at exactly `D` is
admitted; or move the pair's anchor so strictness is derivable.

## Verified sound — recorded so the failure is not read wider than it is

Independently derived by the relevant seats, not accepted from the document or
from the correction records:

- **Budget.** Recomputed from both directions by three seats: 7 paged × 10 + 7
  single × 1 = 77 pages, + 14 retries = 91; authorization sum 7 × 11 + 7 × 2 =
  91. §4 and §6 agree and no cap is raised. Every slot's page ceiling matches
  Stage 21A §7.2 row by row.
- **No new route or scope.** All 14 slots resolve to 11 Stage 21A operation keys,
  all GET; `administration/read` required only by `branch_protection.get`.
- **CR2's substance holds.** `ATTEMPTED_NO_OBSERVATION` maps to exactly Stage 21A
  §10's no-lease-evidence branch and is provably disjoint from the stored
  `NOT_SENT` branch, because 21A §6.4 commits lease evidence durably before the
  first request. The reason-code set is adequate from 21A §10's existing closed
  set; no new vocabulary is needed; no observation can be fabricated; Step remains
  closed with the nullity mapping total and exclusive. Seat 5 traced the round-1
  T1/CR2 prefix-report path end to end and confirmed it now holds.
- **CR3's algorithm is sound.** Total, single-valued, and a full-document token
  sweep confirms no other clause assigns a coverage value. The defect is in §8's
  fixtures (CR9), not the algorithm.
- **Factual-only scope holds.** No readiness verdict, safety score,
  recommendation or overall green indicator is derivable, including by
  composition across the five Section objects.
- **§1's signing clarifier is accurate and purely additive**, verified against
  Stage 21A §4.3's Ed25519 anchor and key pinning and §6.1's signed lease receipt.
  It narrows no retained control.
- **Untrusted text.** Stage 21A's projections retain no GitHub-authored free text
  at all; check names and status contexts are retained only as SHA-256 hashes.
- **All four `stop_reason` members are reachable**; `PROFILE_EXPIRY` is fully
  removed with zero occurrences, and no new dead enum member was introduced
  anywhere — seat 5 enumerated all eleven closed value sets.
- **GitHub facts re-verified** at docs.github.com by seat 3: `merge_commit_sha`
  holds the test-merge SHA before merge and varies by merge method after;
  `merged_by` is documented required-nullable; `GET /repos/{owner}/{repo}/hash-algorithm`
  returns `hash_algorithm` ∈ {sha1, sha256} under Repository permissions →
  Metadata (read), confirming both §8's documentary claim and Stage 21A §7.2's
  "additional permission: none".

## Work performed and remaining boundary

Read-only document and hash checks, independent seat analysis, public
official-documentation inspection, and arithmetic only. No implementation,
credential access, signing, live adapter call, runtime/fixture/platform
acceptance, commit, push, PR, merge, branch-protection change, KOS/IDM change or
production operation occurred.

Next: return CR4-CR14 for remediation. Fresh exact-draft review is required after
any byte change. No freeze or adoption is requested on this failed candidate, and
no authority decision is inferred from the review tally.
