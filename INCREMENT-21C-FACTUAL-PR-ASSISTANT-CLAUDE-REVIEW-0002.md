# Stage 21C Factual PR Assistant — independent exact-draft review 0002

Date: 2026-09-19
Reviewer: Independent automated review (Claude, Claude Code session), outside the
CONCLAVE Council and outside the authoring chain.
Verdict: `FAIL_EXACT_DRAFT` — one blocking finding; B1–B4 closed.

Read-only throughout: no file edited other than this record, no code implemented,
no dependency installed, no credential accessed, no authenticated GitHub call,
no commit, push, PR or merge. This is not a five-seat Council review and cannot
support freeze.

---

## 1. Exact reviewed object

Recomputed from the staged bytes, not accepted from the handoff or from
Technical Review 0002.

| Property | Value | Result |
|---|---|---|
| SHA-256 | `b73676b1bdfd67ff9e8fed70c96c67320efed5bd9ff329e14e6e8439faac0d33` | **matches handoff** |
| Git blob | `6c5dba3a789ad8edc9d0c67daec98bc659015fb9` | recorded |
| Size | 24,152 bytes | — |
| Lines | 386 LF-terminated, 0 CR, final LF present | clean |
| Encoding | valid UTF-8, no BOM, 1 non-ASCII char (U+2014 em-dash, line 1) | clean |
| Predecessor | `73ac7565…aedf8b7c`, 19,276 bytes / 321 lines | +4,876 bytes / +65 lines |

The remediation is bounded. It did not repeat the ceremony plan's pattern of
answering findings with large prose expansion.

Every hash cited in §2 resolves to a real present file in the same directory:

| Cited | Resolves to |
|---|---|
| `d3701754…0164b257` | `INCREMENT-21C-READINESS-AND-HUMAN-MERGE-OBSERVATION.md` |
| `6ea468c1…dbbb91c2` | `INCREMENT-21C-CONTROL-ATTESTATION-COLLECTION-PROTOCOL.md` |
| `a0fa6388…10a5c742` | `INCREMENT-21-ERRATUM-0001-STAGE-21C-HUMAN-MERGE-SPLIT.md` |
| `89a05211…f0878d75` | `INCREMENT-21-GITHUB-REPOSITORY-AND-PR-ADAPTER.md` (master) |
| `97e32362…3b748e81f` | `INCREMENT-21C-GITHUB-BACKED-OBSERVATION-PROTOCOL-CANDIDATE.md` |

Local base `154394c570a9919fc00b7c00779f565f742508e2` verified present in the
worktree as the current detached HEAD (merge of PR #25). Not verified against
the public remote.

---

## 2. B1–B4 closure

### B1 — page ceilings — **CLOSED**

The candidate adopted the conservative option: Stage 21A's ten-page ceiling is
retained rather than narrowing 21A §5.1. §4 now states the worst case explicitly
and §6 no longer contradicts it. Arithmetic recomputed independently:

```
7 paged slots  x 10 pages = 70
7 single slots x  1 page  =  7
                    pages = 77   (doc claims 77)
retry allowances, 1 per logical operation = 14   (doc claims 14)
coordinator ceiling = 91   (doc claims 91)

21A-conforming authorization sum:
7 x 11 (10 pages + 1 retry) + 7 x 2 (1 page + 1 retry) = 91
```

Coordinator ceiling and the sum of 21A-conforming authorizations are now equal
at 91. The two-implementer contradiction is gone: neither the counter nor a
strict 21A validator can reject a conforming cycle. Each slot's Max-pages value
also matches 21A §7.2's ceiling for that endpoint, checked row by row.

### B2 — protection stop rule — **CLOSED**

§4 now makes the stop rule failure-class-specific and does so more conservatively
than the finding required: the exception covers only a PROTECTIONS slot whose
only failure is a rejected HTTP response **definitively not rate-limited**.
Ambiguous 403/rate classification, `RATE_LIMITED`, transport, pagination,
projection, identity, claim, lease, cleanup and persistence failures all still
stop. "If its safe outcome cannot establish the exception, stop" fails closed.

Slots 8–10 are the PROTECTIONS slots and `pr_after` is slot 11, so a tolerated
protection rejection no longer erases the mandatory final PR read. Scope
questions 1 and 5 are answerable for repositories governed by rulesets rather
than classic protection. §7's "permission failure means unavailable, never no
protection" is retained, and the inference that 404 means unprotected is
explicitly prohibited. §8 requires fixtures for both the tolerated-rejection and
the rate-limited-stop paths.

### B3 — time budget — **CLOSED as to the original defect** (see C1)

The 600 s cycle limit is reduced to 300 s, a pre-dispatch reservation replaces
post-hoc rejection, and the completed prefix is now persisted rather than
discarded. `stop_reason` is added to the report schema, so an interrupted cycle
is representable instead of schema-invalid. The 840 s-vs-600 s overrun that
destroyed all evidence is gone: "14 x 60 seconds is not a completion promise."

The original failure scenario is closed. The replacement algorithm introduces a
new defect, recorded as C1 below.

### B4 — projection versioning — **CLOSED**

§5 takes the second option: a new closed `github-factual-api-profile/0.1.0`
record selecting a separately versioned `github-factual-rest-projections/0.1.0`
set, with every operation binding its exact hash in authorization, intent,
attempt digest and observation. The phantom "old projection allowlist" is
deleted and explicitly disclaimed — "There is no per-call override,
caller-selected version or supposed inherited projection allowlist."

The A/B implementer divergence is resolved: there is one profile, old validators
must reject it, and no interpretation under the old API profile is permitted.
Non-PR reads record the new set version too, with the operation key selecting
the shape, so the observation envelope is unambiguous. §2.4 is updated to match.

Also fixed alongside B4: merge derives solely from the identity-matched
`pr_after` slot and never falls back to `pr_before`.

---

## 3. New blocking finding

### C1 — `PROFILE_EXPIRY` is unreachable, and §8 mandates a fixture for it

**Sections:** §6 time algorithm, against §3 `stop_reason` enum and §8 acceptance list.

§6 defines two deadlines:

- `D` = monotonic acquisition start + 300 s;
- `V` = the Stage 21A profile-verification expiry, taken **after the first two
  successful operations**. 21A §7.2 fixes that expiry at five minutes, so
  `V` = (success time of slot 2) + 300 s.

§6 also states "No cached pair from a prior cycle is accepted," so verification
is always performed fresh, in-cycle, at slots 1–2. Slots 1 and 2 take strictly
positive time, therefore:

```
V = t_slot2 + 300   and   D = 0 + 300,  with t_slot2 > 0
=>  V > D  for every admissible cycle
=>  min(D, V) = D  always
```

Recomputed across `t_slot2` = 0.001 s, 5 s, 60 s, 120 s: `D` binds in every case.

**Consequences.** `PROFILE_EXPIRY` can never be emitted — it is a dead enum
member of `stop_reason` in §3. The tiebreak "expiry wins a tie" requires
`V == D`, i.e. `t_slot2 == 0`, which no cycle can produce. And §8's mandatory
remediation-acceptance list requires a fixture for "profile expiry," which
cannot be constructed under §6's own algorithm.

By the candidate's own §2.5 — "Any remaining normative conflict blocks adoption"
— a required acceptance fixture for a state the protocol makes unreachable is an
internal conflict and blocks.

**Severity qualification.** This cannot produce a wrong or dishonest report. No
observation is mislabelled and no evidence is lost; the binding deadline `D` is
enforced correctly and `TIME_BUDGET` covers every real stop. The defect is an
untestable acceptance criterion and a dead enum value, not an evidence defect.
It is in the same class as Review 0007's unreachable-variant findings.

**Smallest sufficient correction.** Either:

1. **Remove it.** Delete `PROFILE_EXPIRY` from §3's `stop_reason` enum and from
   §8's fixture list, and state in §6 that because verification is always
   performed fresh in-cycle, `V > D` always and `D` is the sole binding
   deadline. Retain the `min(D, V)` check as a defensive invariant if desired,
   but then say it can only ever select `D`. This is the smaller change and
   leaves no untestable requirement.
2. **Make it reachable.** Redefine `D` as acquisition start + 300 s while
   permitting `V` to derive from a profile verified earlier in the same
   authorized cycle chain. This reintroduces the staleness "No cached pair from
   a prior cycle is accepted" was added to prevent, and is not recommended.

Option 1 is recommended: one deletion in §3, one deletion in §8, one sentence in §6.

---

## 4. Non-blocking findings

### C2 — the verification pair reserves 60 s for two 60 s operations

§6 says "Before every later slot reserve its full 60-second operation deadline"
and separately "Before the verification pair require now+60 <= D." Slots 1 and 2
are two distinct 60-second logical operations covered by a single 60-second
reservation, and `V` — a term in the later-slot check — is undefined until slot 2
succeeds, so slot 2 sits in a small gap between the two rules.

Not reachable as a failure: the pair runs at t ≈ 0 against `D` = 300 s, so 120 s
of worst-case work always fits, and no wrong outcome can result. Recommend
"before the verification pair require now+120 <= D" for closure, and say
explicitly that slot 2 is governed by the pair's check rather than the
later-slot check.

### C3 — 21A cites no documentation source for `repository_hash_algorithm.get`

Stage 21A §7.2 pins `repository_hash_algorithm.get` to
`/repos/{owner}/{repo}/hash-algorithm`, and §13's reference list supplies an
authoritative `docs.github.com` citation for every other endpoint family in the
table — repos, git refs, git commits, pulls, check runs, statuses, reviews,
issue comments, PR comments, branch protection, rules — but none for this one.
That omission is what left the endpoint's existence open. It is a gap in frozen
21A, not a defect introduced by this candidate. Recorded so that the citation
can be added when 21A is next amended for another reason; it does not justify
reopening 21A on its own.

---

## 5. Resolution of the carried-forward open uncertainty

The handoff recorded: "the inherited hash-algorithm endpoint still needs
verification before live work," and §8 blocks live preflight until
`repository_hash_algorithm.get` "is confirmed against authoritative API
documentation."

**Resolved. The endpoint exists as specified.**

Verified against `https://docs.github.com/en/rest/repos/repos` on 2026-09-19.
The first query named the path, which risks a confirming answer, so it was
re-run as a neutral enumeration of the page's documented GET endpoints without
mentioning the path. Both passes returned it independently:

| Property | Documented | 21A / implementation | Result |
|---|---|---|---|
| Path | `GET /repos/{owner}/{repo}/hash-algorithm` | 21A §7.2 same path | **match** |
| Purpose | returns the hash algorithm used to store repository objects | profile verification | consistent |
| Response property | `hash_algorithm`, required string enum `sha1`/`sha256` | `github_foundation.py:2149` reads `_required(raw, "hash_algorithm")`; `git_object_format: Literal["sha1","sha256"]` | **match** |
| Status codes | 200, 403, 404 | — | recorded |

The frozen 21A path and the installed implementation's expected response key
both agree with the documentation. The endpoint is not invented.

**Residual, narrower gap.** The documentation page does not state the required
permissions or scopes for this endpoint. 21A §7.2 claims "none beyond mandatory
metadata/read." That specific claim remains unconfirmed and should be settled by
the separately authorized fixture/live qualification §8 already requires. The
403 status code is documented, so a permission-denied outcome is possible; note
that slot 2 is a TARGET-section slot and therefore **not** covered by B2's
PROTECTIONS-only tolerated-rejection exception — a 403 there stops the cycle.
That is the correct behaviour, since 21A derives OID length (40 vs 64) from the
verified object format, but it should be an explicit fixture.

Recommend narrowing §8's live-preflight gate from "confirmed against
authoritative API documentation" — now satisfied — to the remaining permission
question, rather than deleting the gate.

---

## 6. Disposition

`FAIL_EXACT_DRAFT`. One blocking finding (C1), two non-blocking (C2, C3).

This is a substantial improvement on review 0001: four blocking findings reduced
to one, the remediation is proportionate in size, and it did not trade closure in
one section for a new dependency in another — the single new defect is confined
to the replacement time algorithm and is correctable in three edits.

The factual-only scope remains sound and should be kept. Nothing here requires
restarting the key ceremony, adding an endpoint, expanding scope, or building an
identity or signing system.

This review is one automated reviewer, not five distinct Council seats, and
confers no approval. No freeze, adoption, implementation, commit, push, merge,
credential use, live operation, Stage 21D, production, KOS or IDM change is
authorized by it. Any change to the candidate's bytes invalidates the exact
identity in §1 and requires recheck.

**Next action:** correct C1 (three edits), recheck the resulting bytes, then put
the corrected candidate to five distinct Council seats.
