# CONCLAVE Stage 21B Implementation Council Re-review 0011

## Status

`5/5 PASS_EXACT_BUNDLE — APPROVED FOR AUTHORIZED COMMIT AND BRANCH PUSH`

Review date: 2026-09-10

This record preserves the final five-seat Council verdict for the exact
implementation bundle below. Arthur's authorization permits its bounded local
commit and push on branch `feature/increment-21b-bounded-publication` only.

## Exact approved implementation bundle

- Base commit: `c3804e2077bfe38f66623404da51d1bd0478846b`
- Aggregate SHA-256:
  `a8e5027ff48da9e67106c54ca4f7145dbc04a6f8e0fd96c2f783b7c0defeef5a`
- Manifest algorithm: concatenate each numbered UTF-8 path below, one NUL
  byte, its lowercase SHA-256, and one LF byte, in numbered order; hash the
  result with SHA-256.

Approved files:

1. `src/conclave/github_publication.py` — `0dfab3de0b280ec110e723c3848499c26d42166b28e989fb1e4af075975bb2b0`
2. `src/conclave/github_publication_records.py` — `05e3bf6e0bd6d6725e6e6805e0a500bbf502d1d6cf956226dca8206d58027d1f`
3. `src/conclave/github_publication_engine.py` — `d8fab4886f0ddb1606cb3ee18e03857fe97b65e9bfd4d78029a8850505c5c39f`
4. `src/conclave/github_publication_reconciliation.py` — `d5d58493ddcd29881b3b80b49e42ae882a50fb38b97eafe71c652955eeaf0172`
5. `src/conclave/ledger.py` — `ab24c08b8277b647951af830df4357db56dd2667e1841b77fe30dfdca9fccc47`
6. `src/conclave/workspace.py` — `eefad736f5357d36e8c5e1750ff98ba902c3ee117aef34bbf153aaa1e788d9ae`
7. `tools/conformance_evidence.py` — `2ec335fe0c3d04ebc59ed9d937a3ec4de074dabd7f83ef070a546e9d48299e16`
8. `tools/installed_wheel_probe.py` — `c84485f8e82e70ec271b462259756a8f4032a1a13d40f5e1dc5210c021386e23`
9. `tests/test_github_publication.py` — `41d2d158b4af4419471e74e17f614ece038852563d6e81ed45660d593d033640`
10. `tests/test_github_publication_governance.py` — `4c8f11492efe362a081dda85dbb1e6ac721a145ed1c00c14f63d9f8777a16548`
11. `tests/test_github_publication_reconciliation.py` — `749decc911d0aa7583552c9e057da2f16361d0ca51b4005c01b431e242a1e34f`
12. `tests/test_conformance_evidence_tool.py` — `133e4a67762a655da738ffde74aee9a24755b8655b4b1954a899faaab8d7de19`
13. `tests/test_installed_wheel_probe.py` — `58346df8856c15c87ae9d2ab1a8e58ebc0b25b69f0917914b09865879f26b15e`
14. `INCREMENT-21B-IMPLEMENTATION-REMEDIATION-0001.md` — `3d9dd615e6eb3868eca3a5ce5aced3f3d9cd070bf865a5d31a6d18a4b7292967`

This Council record is a preservation artifact outside the 14-file reviewed
implementation aggregate and does not change that aggregate.

## Council verdicts

1. Governance and authority — `PASS_EXACT_BUNDLE`
   - Confirmed every frozen governance identity and all authority boundaries.
   - Confirmed every rejected review remains historical and no earlier pass
     was carried to changed bytes.
2. Adversarial security and trust boundary — `PASS_EXACT_BUNDLE`
   - Replayed hostile transcript, projection, mutable-record, subclass,
     serializer-shadow, Pydantic-internal-shadow, and arbitrary-object attacks.
   - Confirmed zero callback execution and zero output on invalid persistence
     input.
3. Git, GitHub request, rate, and reconciliation correctness —
   `PASS_EXACT_BUNDLE`
   - Confirmed deterministic SHA-1/SHA-256 reconstruction, canonical ref
     grammar and URL encoding, exact request hashes, rate bindings and request
     ceilings, and fail-closed ambiguity.
4. Evidence schema and durable-record integrity — `PASS_EXACT_BUNDLE`
   - Confirmed non-virtual primitive extraction, exact instance-field sets,
     fresh content-hash and predecessor validation, and validation before any
     directory derivation or write.
5. Package, portability, and future KOS boundary — `PASS_EXACT_BUNDLE`
   - Reproduced package hashes and verified the 47-member wheel, fixture-only
     installed probe, CI matrix readiness, and absence of live, credential,
     authority, KOS, or IDM surfaces.

## Acceptance evidence

- Focused Windows Python 3.12 suite: `217 passed`.
- Full Windows Python 3.12 suite: `1299 passed, 2 permitted skips`.
- Local conformance: `1301 collected`, 0 failures, 0 errors, 2 permitted
  skips, empty static findings, empty secret findings, status `PASS`.
- Wheel SHA-256:
  `0171c3a4a3ffcff8e2cbf874cf2dfc67402168398f8f5f3b2f1edf4ee0329bec`.
- Source distribution SHA-256:
  `a8addedaf8a50d1dcb7599b9c60c5cd7ff8758c736681258c70882eb899148c7`.
- Clean isolated installed-wheel probe: `PASS`,
  `github-publication-probe-ok`, no stderr, 47 package members.
- Formatting, scoped static checks, and Git whitespace check: `PASS`.

Windows evidence is local. The configured GitHub Actions matrix remains the
post-push acceptance gate for Windows/Python 3.12, Ubuntu/Python 3.12 and 3.13,
and macOS/Python 3.12.

## Boundaries

This approval is exact-bundle-only and authorizes only the already requested
commit and branch push. It does not authorize a pull request, merge, branch
protection change, credential access, GitHub App creation or installation,
live GitHub adapter operation, deployment, production use, signing, identity
allocation, membership activation, KOS change, or IDM change.
