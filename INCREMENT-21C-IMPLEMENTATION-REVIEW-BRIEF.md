# Stage 21C fixture-only implementation — review brief

Date: 2026-09-23
Status: REVIEW PACKAGE READY / NO VERDICT ASSERTED

## Review object

Branch `feat/increment-21c-factual-assistant` at commit
`b3467a613d053475027c553fee6cd83c2e84d4de` (PR #27), based on protected `main`
`276b0f708f124e0a242b66db1167e4699ae84575`.

Two commits:

1. `1be0354` — Stage 21C fixture-only implementation.
2. `b3467a6` — Stage 21A status-class correction.

## What to review against

The **adopted profile is the specification**:
`INCREMENT-21C-FACTUAL-PR-ASSISTANT-PROTOCOL.md`, SHA-256
`ed45fb9f2e1dfc8d8e9f542d71b8e67678aafe1d99120f209f5cb3b1891ab962`, on `main`.
It is frozen: the implementation conforms to it, never the reverse. A defect
found in the profile itself is reported, not silently implemented around.

Also relevant: `INCREMENT-21A-READ-ONLY-GITHUB-FOUNDATION.md` (frozen Stage
21A), `INCREMENT-21C-FACTUAL-PR-ASSISTANT-COUNCIL-REVIEW-0006.md` (5/5 PASS,
carries the non-blocking residuals), and the author-side records
`INCREMENT-21C-IMPLEMENTATION-0001.md` and
`INCREMENT-21A-IMPLEMENTATION-CORRECTION-0001.md` — **claims to test, never
evidence**.

## Files

| File | Change |
|---|---|
| `src/conclave/github_factual.py` | new |
| `src/conclave/github_foundation.py` | additive rule-4 extension |
| `src/conclave/github_operation.py` | projection version pass-through; status-class correction |
| `tests/test_github_factual.py` | new, 48 tests |
| `tests/test_github_foundation.py` | one added Stage 21A regression test |
| docs + `00_CURRENT_STATE.md` | records |

## Standing constraints

- Profile §8: fixture-only. No live transport, no credentials, no mutation
  path, and a test package must not become live by changing a flag or editing a
  record.
- Stage 21A frozen text governs; rule 4 lists the only permitted 21A
  displacements.
- No authority, merge, deployment or production effect.

## What a reviewer must not assume

Passing tests prove only what they assert. Check whether each protocol rule is
actually enforced by code, whether a test could pass with the rule removed, and
whether any rule is implemented only in the test file.

## Severity

- **BROAD** — wrong against the profile, or a scope breach (live path,
  mutation, authority), or requires redesign.
- **NARROW** — a local code or test fix of at most one function.
- **NON-BLOCKING** — style, naming, or a Stage 21A residual the profile does
  not depend on.

Verdict is `FAIL_EXACT_IMPLEMENTATION` if any BROAD or NARROW finding exists.

## Disposition

No verdict asserted by this brief. Nothing is merged. Merge is Arthur's act.
