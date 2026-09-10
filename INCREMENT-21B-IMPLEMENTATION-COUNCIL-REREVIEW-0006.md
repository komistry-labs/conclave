# CONCLAVE Stage 21B Implementation Council Re-review 0006

## Status

`1/3 PASS — CHANGES_REQUIRED; five-seat review halted on reproduced blockers`

Review date: 2026-09-10

This local record preserves a failed review. It grants no authority to freeze,
commit, push, create or merge a pull request, access credentials, perform live
GitHub operations, deploy, or use Stage 21B in production.

## Exact reviewed worktree

- Branch: `feature/increment-21b-bounded-publication`
- Base commit: `c3804e2077bfe38f66623404da51d1bd0478846b`
- Implementation bundle SHA-256:
  `f34b3908e79d950c1d4ed0c35813bcd68c7a271f0f5bda4254805a88375b9429`
- Manifest algorithm: concatenate each numbered UTF-8 path below, one NUL
  byte, its lowercase SHA-256, and one LF byte, in numbered order; hash the
  result with SHA-256.

Reviewed files:

1. `src/conclave/github_publication.py` — `1a73c34f48024e326aba6726087d9de393edbec324f2fb63ceecde66817c16eb`
2. `src/conclave/github_publication_records.py` — `94b14e46a2e06719040671496116105aebee7f97782040b2f50c259f4c3175d7`
3. `src/conclave/github_publication_engine.py` — `2568e15794e5bf0737cbc7accd41eb9bea402f0cf0a2a7d4320a26becdb6b9ad`
4. `src/conclave/github_publication_reconciliation.py` — `c808fe2c5c97b9cb8ab6f5aaebfe11353f114354771632e242cd716e8c146ef8`
5. `src/conclave/ledger.py` — `ab24c08b8277b647951af830df4357db56dd2667e1841b77fe30dfdca9fccc47`
6. `src/conclave/workspace.py` — `eefad736f5357d36e8c5e1750ff98ba902c3ee117aef34bbf153aaa1e788d9ae`
7. `tools/conformance_evidence.py` — `2ec335fe0c3d04ebc59ed9d937a3ec4de074dabd7f83ef070a546e9d48299e16`
8. `tools/installed_wheel_probe.py` — `d935b759042678695350d452d853caa5ad5202a3342a81785d1a1c51cb72833c`
9. `tests/test_github_publication.py` — `d398d8c6c40d3beb271baddfceb33d74b5e206bc20009709a9e8a459913167d5`
10. `tests/test_github_publication_governance.py` — `4c8f11492efe362a081dda85dbb1e6ac721a145ed1c00c14f63d9f8777a16548`
11. `tests/test_github_publication_reconciliation.py` — `095162fb6990fb894e474a4d17ba7b64e37c494a88e4d67952272ff43933278e`
12. `tests/test_conformance_evidence_tool.py` — `133e4a67762a655da738ffde74aee9a24755b8655b4b1954a899faaab8d7de19`
13. `tests/test_installed_wheel_probe.py` — `58346df8856c15c87ae9d2ab1a8e58ebc0b25b69f0917914b09865879f26b15e`
14. `INCREMENT-21B-IMPLEMENTATION-REMEDIATION-0001.md` — `7529cfd1150ed179fba1a0ce07412d54a348c821d41cb3c3fb8d868da8b495f7`

## Returned verdicts

1. Governance and authority — `PASS_EXACT_BUNDLE`
2. Security and trust boundary — `CHANGES_REQUIRED`
3. Git, rate, and reconciliation correctness — `CHANGES_REQUIRED`

Seats 4 and 5 were not convened after two independently reproduced blockers.
The governance pass does not carry to a changed bundle.

## Blocking findings

- `assemble_fixture_reconciliation` accepted a subclass of the untrusted
  `FixtureReadTranscript` and accessed its caller-overridden attributes. It
  also lacked an exact-type snapshot of the nested projection. Caller code
  could therefore execute while reconciliation evidence was assembled.
- The evaluator reopened the final authenticated rate-source observation but
  omitted that Stage 21A chain's durable authorization, intent, attempt claim,
  and lease evidence from the complete predecessor reopen set. Missing or
  altered retained predecessors could go undetected before the fixture claim.

## Disposition

The exact reviewed bundle is rejected and must not be committed or pushed.
Reconciliation must reject transcript and projection subclasses before field
access and use a fresh exact built-in snapshot. Publication must reopen every
signed rate-source predecessor and reject each missing or substituted record
before claim creation. A new exact bundle requires a fresh five-seat review.
