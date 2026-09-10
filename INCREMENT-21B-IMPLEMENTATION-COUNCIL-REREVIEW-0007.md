# CONCLAVE Stage 21B Implementation Council Re-review 0007

## Status

`2/3 PASS — CHANGES_REQUIRED; five-seat review halted on a reproduced blocker`

Review date: 2026-09-10

This local record preserves a failed review. It grants no authority to freeze,
commit, push, create or merge a pull request, access credentials, perform live
GitHub operations, deploy, or use Stage 21B in production.

## Exact reviewed worktree

- Branch: `feature/increment-21b-bounded-publication`
- Base commit: `c3804e2077bfe38f66623404da51d1bd0478846b`
- Implementation bundle SHA-256:
  `13d77528a6eb56bec28a65647dcc880a380738c9488733747206bb83903a14d9`
- Manifest algorithm: concatenate each numbered UTF-8 path below, one NUL
  byte, its lowercase SHA-256, and one LF byte, in numbered order; hash the
  result with SHA-256.

Reviewed files:

1. `src/conclave/github_publication.py` — `1a73c34f48024e326aba6726087d9de393edbec324f2fb63ceecde66817c16eb`
2. `src/conclave/github_publication_records.py` — `94b14e46a2e06719040671496116105aebee7f97782040b2f50c259f4c3175d7`
3. `src/conclave/github_publication_engine.py` — `7406764c1740ef2f273052ae06b896d8e7c5bd2eca5c259cf14862f717112c44`
4. `src/conclave/github_publication_reconciliation.py` — `dce47514b36180d65dada07ca42545b29b697563c49e6ffa8a74f996c06ca3f1`
5. `src/conclave/ledger.py` — `ab24c08b8277b647951af830df4357db56dd2667e1841b77fe30dfdca9fccc47`
6. `src/conclave/workspace.py` — `eefad736f5357d36e8c5e1750ff98ba902c3ee117aef34bbf153aaa1e788d9ae`
7. `tools/conformance_evidence.py` — `2ec335fe0c3d04ebc59ed9d937a3ec4de074dabd7f83ef070a546e9d48299e16`
8. `tools/installed_wheel_probe.py` — `d935b759042678695350d452d853caa5ad5202a3342a81785d1a1c51cb72833c`
9. `tests/test_github_publication.py` — `5f27ce2129e7e137d6918352321e2176fc81cc56d5d84391e3025fa2f51725ab`
10. `tests/test_github_publication_governance.py` — `4c8f11492efe362a081dda85dbb1e6ac721a145ed1c00c14f63d9f8777a16548`
11. `tests/test_github_publication_reconciliation.py` — `cb573035d0004d00935c818043146fbc020d1f0b41e11d09b1709a601ae77499`
12. `tests/test_conformance_evidence_tool.py` — `133e4a67762a655da738ffde74aee9a24755b8655b4b1954a899faaab8d7de19`
13. `tests/test_installed_wheel_probe.py` — `58346df8856c15c87ae9d2ab1a8e58ebc0b25b69f0917914b09865879f26b15e`
14. `INCREMENT-21B-IMPLEMENTATION-REMEDIATION-0001.md` — `2151751e4ca31210c65f5c5813c36397ff7df26468e480cf8686edbfc4ac111d`

## Returned verdicts

1. Governance and authority — `PASS_EXACT_BUNDLE`
2. Security and trust boundary — `PASS_EXACT_BUNDLE`
3. Git, rate, and reconciliation correctness — `CHANGES_REQUIRED`

Seats 4 and 5 were not convened after the independently reproduced blocker.
The two passes do not carry to a changed bundle.

## Blocking finding

The authorized base ref was inserted directly into REST path and query targets.
Although repository-profile validation rejected several ambiguous path forms,
it accepted URL-reserved and non-ASCII characters that could alter query
semantics, make request hashing fail, or cause fixture evidence to diverge from
a future live request. Publication and reconciliation did not share a single
complete Git-ref validator and canonical UTF-8 percent-encoding policy.

## Disposition

The exact reviewed bundle is rejected and must not be committed or pushed. A
single shared validator and encoder must validate complete Git ref grammar,
canonically encode path and query components, and bind request hashes only to
the encoded target. Adversarial tests must cover reserved characters, spaces,
controls, Unicode, and percent forms. A changed bundle requires a fresh
five-seat review.
