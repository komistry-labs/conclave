# CONCLAVE Stage 21B Implementation Council Re-review 0005

## Status

`1/2 PASS — CHANGES_REQUIRED; five-seat review halted on reproduced blocker`

Review date: 2026-09-10

This local record preserves a failed review. It grants no authority to freeze,
commit, push, create or merge a pull request, access credentials, perform live
GitHub operations, deploy, or use Stage 21B in production.

## Exact reviewed worktree

- Branch: `feature/increment-21b-bounded-publication`
- Base commit: `c3804e2077bfe38f66623404da51d1bd0478846b`
- Implementation bundle SHA-256:
  `9efc41427981c37165daedb5483b9993df22142e623b3beb86e68a8a800f0457`
- Manifest algorithm: concatenate each numbered UTF-8 path below, one NUL
  byte, its lowercase SHA-256, and one LF byte, in the numbered order; hash the
  result with SHA-256.

Reviewed files:

1. `src/conclave/github_publication.py` — `1a73c34f48024e326aba6726087d9de393edbec324f2fb63ceecde66817c16eb`
2. `src/conclave/github_publication_records.py` — `94b14e46a2e06719040671496116105aebee7f97782040b2f50c259f4c3175d7`
3. `src/conclave/github_publication_engine.py` — `8e393ab65030bafcc1d7c0222fa780e7ff0778bf831bce6b8539e8872b275213`
4. `src/conclave/github_publication_reconciliation.py` — `9beca59ce060cb6ee8efa28147cd472e1d6fb6125b205ffda31c7b7ac688ad7f`
5. `src/conclave/ledger.py` — `ab24c08b8277b647951af830df4357db56dd2667e1841b77fe30dfdca9fccc47`
6. `src/conclave/workspace.py` — `eefad736f5357d36e8c5e1750ff98ba902c3ee117aef34bbf153aaa1e788d9ae`
7. `tools/conformance_evidence.py` — `2ec335fe0c3d04ebc59ed9d937a3ec4de074dabd7f83ef070a546e9d48299e16`
8. `tools/installed_wheel_probe.py` — `d935b759042678695350d452d853caa5ad5202a3342a81785d1a1c51cb72833c`
9. `tests/test_github_publication.py` — `dd297837f42c7a5dcde4c861b8caed194e0d8043881ae8fea076a995ad34705b`
10. `tests/test_github_publication_governance.py` — `4c8f11492efe362a081dda85dbb1e6ac721a145ed1c00c14f63d9f8777a16548`
11. `tests/test_github_publication_reconciliation.py` — `c209f72d68ea467d6cc1268bffbf7bb1f72106857979a5b196d8168358a883a6`
12. `tests/test_conformance_evidence_tool.py` — `133e4a67762a655da738ffde74aee9a24755b8655b4b1954a899faaab8d7de19`
13. `tests/test_installed_wheel_probe.py` — `58346df8856c15c87ae9d2ab1a8e58ebc0b25b69f0917914b09865879f26b15e`
14. `INCREMENT-21B-IMPLEMENTATION-REMEDIATION-0001.md` — `5f60e1c3945089664cf0bbdb1dea08676000886a0f8d94526b8d5dee42948722`

## Returned verdicts

1. Governance and authority — `PASS_EXACT_BUNDLE`
2. Security and trust boundary — `CHANGES_REQUIRED`

Seats 3 through 5 were not convened after the security seat reproduced a
write-boundary bypass. The governance pass does not carry to a changed bundle.

## Blocking finding

Both Stage 21B write-path guards checked only `root.parents` for a `.git`
marker. They did not inspect the `.conclave` workspace root itself. A workspace
with `.conclave/.git` was therefore accepted and received publication or
reconciliation evidence, contrary to the non-repository workspace boundary.

## Disposition

The exact reviewed bundle is rejected and must not be committed or pushed.
Both guards must reject a `.git` file or directory at the workspace root as
well as at every ancestor, with adversarial coverage for both publication and
reconciliation paths. A new exact bundle requires a fresh five-seat review.
