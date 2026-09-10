# CONCLAVE Stage 21B Implementation Council Re-review 0002

## Status

`0/5 PASS — CHANGES_REQUIRED`

Review date: 2026-09-10

This is a local review record. It preserves a failed review and grants no
authority to freeze, commit, push, create or merge a pull request, access a
credential, perform a live GitHub operation, deploy, or use Stage 21B in
production.

## Exact reviewed worktree

- Branch: `feature/increment-21b-bounded-publication`
- Base commit: `c3804e2077bfe38f66623404da51d1bd0478846b`
- Corrected implementation bundle SHA-256:
  `463ca538ca74562e6d681afa20f18ba7446cf2dd1fd8251f09f964df845eb325`
- Manifest algorithm: concatenate each numbered UTF-8 path below, one NUL
  byte, its lowercase SHA-256, and one LF byte, in the numbered order; hash the
  result with SHA-256.

Reviewed files:

1. `src/conclave/github_publication.py` — `a1571043ed8158e2a1fae9e61ba2eb451bb1b8d39de41b1100361f7b26546541`
2. `src/conclave/github_publication_records.py` — `94137e04f1008f9a17da59c9e9d8005c775360d783018d5e471bbb1c78566bf0`
3. `src/conclave/github_publication_engine.py` — `5059566790068375b8e5c97393153d01f383f821f3192c5c5fea3b62cbf29b06`
4. `src/conclave/github_publication_reconciliation.py` — `354acf49f3121486740335871c4e431f4b2a4e583ff985a3cbc6e234fff5854a`
5. `src/conclave/ledger.py` — `55b04226fc9a34baaa6841c048123d11e2f50748e110c21ef99757d0e488ad6d`
6. `src/conclave/workspace.py` — `9886543b3411245f76fc55eb45216ceb17b7a7bee3a1c5fbd97ba684eb8f5a96`
7. `tools/conformance_evidence.py` — `fb49ada0b2113f853f891b3254eaf28926df4383b7c8f65a7ea29c56a2b5a655`
8. `tools/installed_wheel_probe.py` — `8f523a6e8c6d0b9b993560218003d6e823be22bb797f7127c24273f991323393`
9. `tests/test_github_publication.py` — `2583e77d703c16d7a13cb87dc598983c6dd2a02425bed4c84400779d85e90db5`
10. `tests/test_github_publication_reconciliation.py` — `924cde9be9ee918f523627c03c6d84bfa5d9dad0ed9a0388b29e4591a4b6b3dc`
11. `tests/test_conformance_evidence_tool.py` — `533436667f1dc73ee8a32e5b280addc1f2bef15197daf0b983d16ee34449e2d3`
12. `tests/test_installed_wheel_probe.py` — `0b859c949005c629db98586f240829500211bb360172c443b6e0da9d21f27727`
13. `INCREMENT-21B-IMPLEMENTATION-REMEDIATION-0001.md` — `422c125e8ac77d361832aced6f8b180ce209cdca282103285af06636b6dfc45d`

## Council verdicts

1. Governance and authority — `CHANGES_REQUIRED`
2. Security and credentials — `CHANGES_REQUIRED`
3. Git and GitHub correctness — `CHANGES_REQUIRED`
4. Evidence and schema integrity — `CHANGES_REQUIRED`
5. Cross-platform and installed-package evidence — `CHANGES_REQUIRED`

## Blocking findings

### R2-1 — Fixture transport can create production-shaped factual success

An arbitrary structural transport satisfying only a caller-set fixture flag can
return raw matching bytes and cause `proposal_published:true` plus a
`github_proposal_publication_recorded` ledger event. The evaluator consumes no
authenticated one-shot publication credential/transport capability, and step
results copy provider identity from earlier rate evidence rather than proving
which provider admitted the dispatch.

### R2-2 — Scope is not bound to proposal paths

Task, Handoff, and scope hashes are verified, but their object-level scope is
not derived and compared with the manifest's exact allowed proposal paths. The
passing fixture scopes `CONCLAVE-STAGE-21B` while publishing `a.txt`.

### R2-3 — Source and head-policy chains are not genuine Stage 21A chains

The recursive-tree source wrappers do not cross-bind the complete signed
credential evidence to authorization, intent, principal, route, and request.
Branch-rule and ruleset observations omit their actual authorization, intent,
claim, and lease records and use invented projection keys that the frozen Stage
21A projector does not emit.

### R2-4 — Reconciliation remains incomplete

Caller-supplied projected absence can become `CONFIRMED_ABSENT` without an
accepted authenticated complete read. Tree reconciliation compares an overlay
rather than the complete resultant tree. Original claims, leases, admissions,
ordered step states, terminal inventory, closure, rate, provider, repository,
and API evidence are not all reopened. A read without response incorrectly
receives a result. Two incompatible record families also reuse the same
reconciliation `0.1.0` profile/schema identities.

### R2-5 — Terminal classifications and terminalization are incomplete

Provable pre-dispatch existing-head and duplicate-PR stops remain
`NOT_ATTEMPTED` rather than `REFUSED` or `CONFLICT`. Several post-claim record
construction and persistence paths can still escape without a sanitized
receipt or terminal capsule.

### R2-6 — Conformance accepts forged installed-package evidence

The installed-wheel producer now proves the full transaction and package
inventory, but the conformance verifier does not independently require or
compare that inventory with the exact wheel. It accepts missing/forged module
hashes, prohibited members, and the obsolete shallow inline probe shape.

## Positive evidence retained

- Exact protocol pins and negative substitution tests pass.
- Operation-specific blob/tree/commit/ref/PR identity types and `commit.get`
  admission exist.
- Pull-request identity includes repository and base/head commit identity.
- Strict JSON, integer monotonic time, artifact-alias rejection, and the closed
  diagnostic vocabulary are materially improved.
- Focused corrected suite: 101 passed.
- Full local Windows suite: 1,213 passed, 2 permitted environment-dependent
  skips.
- Fresh sdist/wheel build and isolated Python 3.12 installation pass.
- The installed probe runs the 16-step transaction, receipt, ledger,
  ambiguity, and eight-record reconciliation path with four-module inventory.

## Disposition

The reviewed bundle is not suitable to freeze, commit, push, or create a pull
request. This record is historical evidence for the next bounded local
correction wave. Cross-platform exact-current CI remains pending a separately
authorized publication step.
