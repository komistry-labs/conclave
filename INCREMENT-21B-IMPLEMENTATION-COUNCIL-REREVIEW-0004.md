# CONCLAVE Stage 21B Implementation Council Re-review 0004

## Status

`0/3 PASS — CHANGES_REQUIRED; five-seat review halted after unanimous blockers`

Review date: 2026-09-10

This local record preserves a failed review. It grants no authority to freeze,
commit, push, create or merge a pull request, access credentials, perform live
GitHub operations, deploy, or use Stage 21B in production.

## Exact reviewed worktree

- Branch: `feature/increment-21b-bounded-publication`
- Base commit: `c3804e2077bfe38f66623404da51d1bd0478846b`
- Implementation bundle SHA-256:
  `54581deb9e46f97c017e3027ffa219329ee81ffa667039aa4fe566e786dba820`
- Manifest algorithm: concatenate each numbered UTF-8 path below, one NUL
  byte, its lowercase SHA-256, and one LF byte, in the numbered order; hash the
  result with SHA-256.

Reviewed files:

1. `src/conclave/github_publication.py` — `1a73c34f48024e326aba6726087d9de393edbec324f2fb63ceecde66817c16eb`
2. `src/conclave/github_publication_records.py` — `94b14e46a2e06719040671496116105aebee7f97782040b2f50c259f4c3175d7`
3. `src/conclave/github_publication_engine.py` — `e7a5463503dcd24b81af36468c796e1ed1d6ee607821f14861d9631bc73b4e32`
4. `src/conclave/github_publication_reconciliation.py` — `1f8e79aed5d187216589d6ac90682d547b30a79bd26fe4fedc34c322c93ec9ca`
5. `src/conclave/ledger.py` — `ab24c08b8277b647951af830df4357db56dd2667e1841b77fe30dfdca9fccc47`
6. `src/conclave/workspace.py` — `6f7484679213be330af48b62b8551576f9d07123faf477db7ddbf5262b0affa5`
7. `tools/conformance_evidence.py` — `2ec335fe0c3d04ebc59ed9d937a3ec4de074dabd7f83ef070a546e9d48299e16`
8. `tools/installed_wheel_probe.py` — `0cae168fb8414f37cb253b463a9c39aaf68c8d89fbc977a186389862e608e39d`
9. `tests/test_github_publication.py` — `f67535d502da7c63652fde24100fbddad0cdd8ce345f4d8887a639200e04b3a9`
10. `tests/test_github_publication_governance.py` — `4c8f11492efe362a081dda85dbb1e6ac721a145ed1c00c14f63d9f8777a16548`
11. `tests/test_github_publication_reconciliation.py` — `f7a552588051cb68c28b966263c59bb78363303ab76bd49138c293cbaf4fe4b0`
12. `tests/test_conformance_evidence_tool.py` — `133e4a67762a655da738ffde74aee9a24755b8655b4b1954a899faaab8d7de19`
13. `tests/test_installed_wheel_probe.py` — `58346df8856c15c87ae9d2ab1a8e58ebc0b25b69f0917914b09865879f26b15e`
14. `INCREMENT-21B-IMPLEMENTATION-REMEDIATION-0001.md` — `361a9e287a7373af1e80f2517a28bcbe8adc38af171abb3b3610f8c55c712b5c`

## Returned verdicts

1. Governance and authority — `CHANGES_REQUIRED`
2. Security, credentials, and trust boundary — `CHANGES_REQUIRED`
3. Git and GitHub correctness — `CHANGES_REQUIRED`

Seats 4 and 5 were not convened after all first three seats independently
returned blockers. No approval threshold could be reached for this exact
bundle.

## Blocking findings

- Reconciliation persistence accepted an arbitrary caller-selected directory,
  created missing parents, and wrote durable records without a verified
  external CONCLAVE workspace, Git-checkout exclusion, containment check, or
  link and Windows-reparse-point rejection. This could direct writes into KOS,
  IDM, or another governed repository.
- `FixtureTranscriptEntry` required the exact `GitHubTransportResponse` class
  but did not validate or defensively copy its fields. A caller-controlled
  iterable stored in `headers` could therefore execute code when the evaluator
  inspected response headers, contradicting the inert-transcript boundary.

## Disposition

The exact reviewed bundle is rejected and must not be committed or pushed.
The next correction must derive reconciliation output exclusively from a
verified external CONCLAVE workspace and must reduce every fixture response to
bounded exact built-in immutable values before any claim is retained. A new
exact bundle requires a fresh five-seat review from the beginning.
