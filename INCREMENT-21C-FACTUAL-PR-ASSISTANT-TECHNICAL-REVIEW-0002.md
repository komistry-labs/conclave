# Factual PR assistant — technical review 0002

Date: 2026-09-19
Disposition: F1-F4 ADDRESSED IN DRAFT / READY FOR INDEPENDENT REVIEW
Reviewer: Adrian, author-side technical review, not Council approval.

Candidate SHA-256:
`73ac7565807a0167c3f2793e2b74f8ef0c971f5fcaf88314a600afadaedf8b7c`
Candidate Git blob: `122f5d5d3886d1a8d6897b3845e2c9dfde2f4e18`
File: INCREMENT-21C-FACTUAL-PR-ASSISTANT-PROTOCOL.md

## Finding closure

| Finding | Draft correction | Verification performed |
| --- | --- | --- |
| F1 source binding | Fixed per-slot operation/parameters; all report pointers resolve to exactly one step; wrong repository/SHA is an error | Read-through of request, report, step, source and target rules |
| F2 merge source | Complete pr_after only; no fallback or mixing; conditional commit/check reads follow it | Traced open-to-merged, missing final source, null SHA and changed linkage branches |
| F3 repeated authorization | Distinct external authorization hashes and unused attempts; no coordinator-minted authority | Compared with Stage 21A single-use attempt-digest contract |
| F4 retained plan | Fixed 14-slot table plus exact ordered steps; deterministic conditional slots; no dynamic detail expansion | Arithmetic: 28 page transmissions + 14 retry allowances = 42 maximum |

These are document-level closures, not implemented safeguards. Tests listed in
the candidate remain NOT RUN. The budget arithmetic was evaluated in-session;
no runtime, cryptography, installed-package or platform execution occurred.

## Boundaries and remaining gate

The scope remains a factual assistant, not a readiness engine. No key ceremony,
new endpoint, mutation, independent identity claim or overall green verdict was
introduced. The narrower plan deliberately omits ruleset-detail collection and
artifact publication. These limitations must survive later implementation.

The original technical review is preserved. The two frozen Stage 21C protocol
hashes still match their historical values. Tracked working-tree and index
diffs are empty; the candidate/reviews are local untracked drafting artifacts.

Independent review must challenge exact supersession scope, source-version
dispatch, conditional authorization and partial-result semantics. This author's
closure of four findings is not a substitute for that review or a 5/5 Council
PASS. No freeze, commit, push, implementation or live operation is authorized.

Next action: independently review the exact candidate identified above together
with Stage 21A, the master/human-merge erratum and technical reviews 0001-0002.
Any candidate byte change invalidates this exact identity and requires recheck.
