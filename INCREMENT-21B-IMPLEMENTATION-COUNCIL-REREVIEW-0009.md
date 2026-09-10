# CONCLAVE Stage 21B Implementation Council Re-review 0009

## Status

`0/1 PASS — CHANGES_REQUIRED; five-seat review halted on a reproduced blocker`

Review date: 2026-09-10

This local record preserves a failed review. It grants no authority to freeze,
commit, push, create or merge a pull request, access credentials, perform live
GitHub operations, deploy, or use Stage 21B in production.

## Exact reviewed worktree

- Branch: `feature/increment-21b-bounded-publication`
- Base commit: `c3804e2077bfe38f66623404da51d1bd0478846b`
- Implementation bundle SHA-256:
  `a88eaf1b9949aa09e6cd5c3223a4e1dea7c5e04c2854914912cdcc058caf4e04`
- Manifest algorithm: concatenate each numbered UTF-8 path below, one NUL
  byte, its lowercase SHA-256, and one LF byte, in numbered order; hash the
  result with SHA-256.

Reviewed files:

1. `src/conclave/github_publication.py` — `0dfab3de0b280ec110e723c3848499c26d42166b28e989fb1e4af075975bb2b0`
2. `src/conclave/github_publication_records.py` — `05e3bf6e0bd6d6725e6e6805e0a500bbf502d1d6cf956226dca8206d58027d1f`
3. `src/conclave/github_publication_engine.py` — `d8fab4886f0ddb1606cb3ee18e03857fe97b65e9bfd4d78029a8850505c5c39f`
4. `src/conclave/github_publication_reconciliation.py` — `dca8d930217f26ccbd9af242b418e558f0ee49b7f54c0c19d92ff080bac81062`
5. `src/conclave/ledger.py` — `ab24c08b8277b647951af830df4357db56dd2667e1841b77fe30dfdca9fccc47`
6. `src/conclave/workspace.py` — `eefad736f5357d36e8c5e1750ff98ba902c3ee117aef34bbf153aaa1e788d9ae`
7. `tools/conformance_evidence.py` — `2ec335fe0c3d04ebc59ed9d937a3ec4de074dabd7f83ef070a546e9d48299e16`
8. `tools/installed_wheel_probe.py` — `c84485f8e82e70ec271b462259756a8f4032a1a13d40f5e1dc5210c021386e23`
9. `tests/test_github_publication.py` — `41d2d158b4af4419471e74e17f614ece038852563d6e81ed45660d593d033640`
10. `tests/test_github_publication_governance.py` — `4c8f11492efe362a081dda85dbb1e6ac721a145ed1c00c14f63d9f8777a16548`
11. `tests/test_github_publication_reconciliation.py` — `3df093f2994d237fabe5e46a7f386c91d2ffd23c2b6210cae380ddabeaab7d55`
12. `tests/test_conformance_evidence_tool.py` — `133e4a67762a655da738ffde74aee9a24755b8655b4b1954a899faaab8d7de19`
13. `tests/test_installed_wheel_probe.py` — `58346df8856c15c87ae9d2ab1a8e58ebc0b25b69f0917914b09865879f26b15e`
14. `INCREMENT-21B-IMPLEMENTATION-REMEDIATION-0001.md` — `c9e72b371dfc6c62ab4f65608ed241560187a3c5df94a0cdbab2a2f779780786`

## Returned verdict

1. Adversarial security — `CHANGES_REQUIRED`

The remaining seats were halted as soon as the blocker was reproduced. No
earlier verdict carries to this changed bundle.

## Blocking finding

The pre-write snapshot screened declared fields and then invoked
`value.model_dump_json()` through the caller-owned exact bundle instance. An
exact `ReconciliationBundle` could be bypass-mutated with an extra instance
attribute named `model_dump_json`; persistence invoked that callback and then
wrote eight records. Screening only declared fields did not inspect the extra
instance-dictionary entry.

## Disposition

The exact reviewed bundle is rejected and must not be committed or pushed.
Persistence must never call serialization methods through caller-owned
instances. It must require exact instance dictionaries with exactly the
declared field-name set, recursively extract fields with non-virtual built-in
operations into exact primitive containers, and validate a fresh bundle from
that primitive graph before any directory derivation or write. Tests must prove
bundle and nested method shadows neither execute nor produce files. A changed
bundle requires a fresh five-seat review.
