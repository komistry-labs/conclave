# CONCLAVE Stage 21B Implementation Council Re-review 0003

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
  `5dcf387ed12f179cc2d923911aaf40797f9f46f9b6eabbe3b2ec8e806bb4cd2a`
- Manifest algorithm: concatenate each numbered UTF-8 path below, one NUL
  byte, its lowercase SHA-256, and one LF byte, in the numbered order; hash the
  result with SHA-256.

Reviewed files:

1. `src/conclave/github_publication.py` — `1a73c34f48024e326aba6726087d9de393edbec324f2fb63ceecde66817c16eb`
2. `src/conclave/github_publication_records.py` — `31477c68c8df687d51dceabe473a99074c35dd501032ffd2cf048b850789f620`
3. `src/conclave/github_publication_engine.py` — `22514584840c9aca839da45290fb5f8bcb08b8074a5e92a36796228f4dd2243c`
4. `src/conclave/github_publication_reconciliation.py` — `f3b56fc9184aee4396f830fb62aa99776bf1eeebd10766a9b5db2dc992496203`
5. `src/conclave/ledger.py` — `e4f9c5629b66ccbebcbc22241280332a2a0ba2f44713e02eb162a23832243cba`
6. `src/conclave/workspace.py` — `9886543b3411245f76fc55eb45216ceb17b7a7bee3a1c5fbd97ba684eb8f5a96`
7. `tools/conformance_evidence.py` — `2ec335fe0c3d04ebc59ed9d937a3ec4de074dabd7f83ef070a546e9d48299e16`
8. `tools/installed_wheel_probe.py` — `dff1bcc3db3d1f0ae7d372917773a78a7500b58710741a6a802fdc62800313af`
9. `tests/test_github_publication.py` — `2a7b77491e1a40a0af34d67b94e5ca01cda1dc9bc6c2ca6087deb86e790b232b`
10. `tests/test_github_publication_governance.py` — `318c45774e703dbfc46f5509d381928d2d7d0f85ba3591c1dffbd281e6a870c3`
11. `tests/test_github_publication_reconciliation.py` — `51bff6aec762a6d141aa8265742e9154709d8cc56e306e25ea0554781be2b481`
12. `tests/test_conformance_evidence_tool.py` — `133e4a67762a655da738ffde74aee9a24755b8655b4b1954a899faaab8d7de19`
13. `tests/test_installed_wheel_probe.py` — `58346df8856c15c87ae9d2ab1a8e58ebc0b25b69f0917914b09865879f26b15e`
14. `INCREMENT-21B-IMPLEMENTATION-REMEDIATION-0001.md` — `a9bf5daa87ce1eceffd74e8887fa63371f904fe5d86e540bac244c0fce6b5fc5`

## Returned verdicts

1. Governance and authority — `CHANGES_REQUIRED`
2. Security, credentials, and trust boundary — `CHANGES_REQUIRED`
3. Git and GitHub correctness — `CHANGES_REQUIRED`

Seats 4 and 5 were not convened after all first three seats independently
returned blockers. No approval threshold could be reached for this exact
bundle.

## Blocking findings

- Offline fixture evidence reused production publication profile/schema and
  production-shaped outcome names.
- A caller-supplied structural transport could claim fixture-only status while
  executing arbitrary code or live I/O.
- Writable evidence paths were not structurally derived from and contained by
  the CONCLAVE workspace.
- The recursive-tree credential signature authenticated a different operation
  rather than the exact source authorization and intent.
- Rate capacity was not derived from and checked against an authenticated
  Stage 21A rate projection, including `remaining <= limit`.
- Publication lease fields asserted write authority without exact signed
  publication claims.
- Reconciliation trusted a caller-set `authenticated` literal rather than a
  complete signed Stage 21A read-observation chain and used live-fact-shaped
  classifications for fixture evidence.

## Disposition

The exact reviewed bundle is rejected and must not be committed or pushed.
The next correction must use a distinct fixture evidence vocabulary, execute
no caller-controlled transport code, keep writes inside governed CONCLAVE
workspace directories, and derive all security-relevant observations from
complete signed evidence chains. A new exact bundle requires a fresh five-seat
review from the beginning.
