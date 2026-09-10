# CONCLAVE Stage 21B Implementation Council Re-review 0008

## Status

`4/5 PASS — CHANGES_REQUIRED; exact bundle rejected`

Review date: 2026-09-10

This local record preserves a failed review. It grants no authority to freeze,
commit, push, create or merge a pull request, access credentials, perform live
GitHub operations, deploy, or use Stage 21B in production.

## Exact reviewed worktree

- Branch: `feature/increment-21b-bounded-publication`
- Base commit: `c3804e2077bfe38f66623404da51d1bd0478846b`
- Implementation bundle SHA-256:
  `bb38a5e67fa2370403598a113749be7ddea547116664866254d45cd3bd1e4f01`
- Manifest algorithm: concatenate each numbered UTF-8 path below, one NUL
  byte, its lowercase SHA-256, and one LF byte, in numbered order; hash the
  result with SHA-256.

Reviewed files:

1. `src/conclave/github_publication.py` — `0dfab3de0b280ec110e723c3848499c26d42166b28e989fb1e4af075975bb2b0`
2. `src/conclave/github_publication_records.py` — `05e3bf6e0bd6d6725e6e6805e0a500bbf502d1d6cf956226dca8206d58027d1f`
3. `src/conclave/github_publication_engine.py` — `d8fab4886f0ddb1606cb3ee18e03857fe97b65e9bfd4d78029a8850505c5c39f`
4. `src/conclave/github_publication_reconciliation.py` — `ab3b2a972db2726728b9bf610b23765253cdbc81298adb0c38afc010287fe4a2`
5. `src/conclave/ledger.py` — `ab24c08b8277b647951af830df4357db56dd2667e1841b77fe30dfdca9fccc47`
6. `src/conclave/workspace.py` — `eefad736f5357d36e8c5e1750ff98ba902c3ee117aef34bbf153aaa1e788d9ae`
7. `tools/conformance_evidence.py` — `2ec335fe0c3d04ebc59ed9d937a3ec4de074dabd7f83ef070a546e9d48299e16`
8. `tools/installed_wheel_probe.py` — `c84485f8e82e70ec271b462259756a8f4032a1a13d40f5e1dc5210c021386e23`
9. `tests/test_github_publication.py` — `41d2d158b4af4419471e74e17f614ece038852563d6e81ed45660d593d033640`
10. `tests/test_github_publication_governance.py` — `4c8f11492efe362a081dda85dbb1e6ac721a145ed1c00c14f63d9f8777a16548`
11. `tests/test_github_publication_reconciliation.py` — `67197dc460705cea084a0004f31de7a15cea58084d38f75d1b2d67e367127f29`
12. `tests/test_conformance_evidence_tool.py` — `133e4a67762a655da738ffde74aee9a24755b8655b4b1954a899faaab8d7de19`
13. `tests/test_installed_wheel_probe.py` — `58346df8856c15c87ae9d2ab1a8e58ebc0b25b69f0917914b09865879f26b15e`
14. `INCREMENT-21B-IMPLEMENTATION-REMEDIATION-0001.md` — `08a3a69cc140079b08b079418ae465929ea13111523c6be852caf4c52db64865`

## Returned verdicts

1. Governance and authority — `PASS_EXACT_BUNDLE`
2. Security and trust boundary — `PASS_EXACT_BUNDLE`
3. Git, rate, and reconciliation correctness — `PASS_EXACT_BUNDLE`
4. Evidence schema and durable-record integrity — `CHANGES_REQUIRED`
5. Package, portability, and future KOS boundary — `PASS_EXACT_BUNDLE`

The four passes do not carry to a changed bundle.

## Blocking finding

`persist_fixture_reconciliation` trusted the previously assembled bundle and
wrote its nested records without exact-type snapshotting or revalidating each
record's current canonical body against its retained content hash. A frozen
receipt could be bypass-mutated after assembly; persistence then wrote all
records, including the stale content hash, even though reopening the resulting
receipt correctly rejected it.

## Disposition

The exact reviewed bundle is rejected and must not be committed or pushed.
Before any filesystem write, persistence must reject bundle and nested record
subclasses, reject unexpected nested model or scalar types, reconstruct an
exact fresh bundle, and revalidate every current record content hash and
predecessor relation. Adversarial tests must prove that mutation of each of the
eight durable records, or substitution of bundle or nested subclasses, writes
zero reconciliation files. A changed bundle requires a fresh five-seat review.
