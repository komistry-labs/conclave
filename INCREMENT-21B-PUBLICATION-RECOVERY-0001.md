# CONCLAVE Stage 21B Publication Recovery 0001

Date: 2026-09-10
Branch: `feature/increment-21b-bounded-publication`

## 1. Purpose and status

This record preserves the first post-push acceptance failure for the corrected
Stage 21B implementation, the resulting bounded amendments, and the evidence
required before a replacement push. It does not erase or supersede the prior
Council records. The first pushed candidate remains a historical failed
publication candidate.

At the time this record was authored, the amended candidate had passed local
Windows/Python 3.12 verification. Replacement remote Windows, Ubuntu, and
macOS evidence remained pending and could be claimed only after a new exact
commit was pushed and its GitHub Actions run completed successfully.

## 2. Failed publication candidate

- commit: `930af95f72bd8de3c7d32f78af165515f13b5715`
- tree: `f2ec8957e45fd8c1e3ab66516ccf436a5834be03`
- remote branch: `feature/increment-21b-bounded-publication`
- GitHub Actions run: `34444730211`
- workflow conclusion: `failure`
- matrix: Windows/Python 3.12, Ubuntu/Python 3.12, Ubuntu/Python 3.13,
  macOS/Python 3.12

The remote branch was independently read back at the exact commit before the
workflow result was evaluated.

## 3. Findings preserved

### R-1 — Unix link refusal leaked an operating-system exception

Ubuntu and macOS each completed dependency acquisition and installation, then
failed one of 1,301 collected tests:
`test_controlled_artifact_reader_refuses_links`.

The descriptor-relative reader correctly refused a symbolic link through
`O_NOFOLLOW`, but `os.open()` surfaced platform-specific `OSError` values
(`ELOOP`, including macOS errno 62) instead of the protocol's closed
`PROPOSAL_CONTENT_CHANGED` classification. The security refusal worked; the
observable failure contract did not.

### R-2 — Windows installed-wheel probe used an aliased temporary root

Windows passed the complete test step, then failed during the clean
installed-wheel probe. The runner emitted the only path diagnostic before the
probe failure: the requested virtual-environment location used the 8.3 alias
`C:\\Users\\RUNNER~1`, while the actual environment resolved beneath
`C:\\Users\\runneradmin`.

The resulting diagnosis is that the probe named one environment through two
path spellings. This diagnosis is evidence-backed but remains provisional
until replacement Windows CI passes; the failed run did not publish its
otherwise secret-free probe report because the workflow correctly stopped at
the failed step.

### R-3 — First recovery draft did not propagate the canonical root

The first recovery draft resolved the temporary root inside
`prepare_probe_environment()`, but returned only the derived wheel and
executable paths. The caller retained its original potentially aliased `root`
when it created the external publication fixture. Council's Git/path review
blocked that exact draft before commit or push. Its aggregate
`2fd0958d0bd5e9dba96df664ffba7b24c5d81d0eeab424cff7d8b681d57a723f`
is therefore a rejected historical candidate, not an approval.

### R-4 — The external macOS probe created a second aliased root

Replacement GitHub Actions run `34446903733` fully passed both Ubuntu jobs.
macOS passed all 1,301 tests and built the exact package, then failed its
isolated installed-wheel publication probe. Review found that the embedded
external probe created a second `TemporaryDirectory` and used its raw `/var`
path. On macOS, `/var` can resolve beneath `/private/var`, recreating the path
identity split after the corrected outer environment. This diagnosis remains
provisional until replacement macOS CI passes.

### R-5 — Windows lock contention can surface as `PermissionError`

The same replacement run exposed an independent existing-runtime defect in
`test_concurrent_identical_import_is_idempotent`. Windows passed 1,300 tests,
but one concurrent ledger writer received `PermissionError` from the
`O_CREAT | O_EXCL` lock acquisition while the other writer owned the lock.
The lock loop handled only `FileExistsError`. Earlier Windows and local runs
passed, demonstrating the race-dependent nature of the defect.

## 4. Bounded amendments

1. Descriptor-relative directory and artifact opens now translate every
   refusal/open failure into `PROPOSAL_CONTENT_CHANGED`, preserving the closed
   Stage 21B diagnostic vocabulary across Unix platforms.
2. The installed-wheel probe now creates and resolves its existing temporary
   root to one canonical path before virtual-environment creation, so Windows
   8.3 and long-path spellings cannot diverge in later executable and fixture
   paths.
3. The probe-environment unit test now binds returned captured-wheel paths to
   that canonical root.
4. The environment helper now returns the canonical root itself, and `main()`
   rebinds to it before creating the external publication fixture. The test
   binds the captured wheel, interpreter, and CONCLAVE executable to that same
   returned root.
5. The embedded external publication probe now resolves its own existing
   temporary root before creating a CONCLAVE workspace, closing the nested
   macOS `/var` alias path.
6. The portable ledger lock treats a Windows `PermissionError` as contention
   under the existing bounded deadline without using a racy immediate
   existence check. If the deadline is exhausted without an observable lock,
   the permission failure propagates; non-Windows permission failures remain
   immediate. Deterministic regressions simulate release-before-observation,
   successful retry and cleanup, and a genuine non-Windows permission failure.

No GitHub endpoint, credential flow, mutation budget, approval gate, authority
boundary, KOS behavior, IDM behavior, or production capability changed.

## 5. Local recovery evidence

- directly targeted recovery regressions: `14 passed`
- complete Windows/Python 3.12 suite: `1,301 passed`, `2` permitted skips,
  zero failures and zero errors
- collected tests: `1,303`
- scoped Ruff check and format verification: pass
- fresh wheel SHA-256:
  `4e24763595d7a92085fca4108ff0d028808e84cb62784cca2cf301a7b54f1ef4`
- fresh sdist SHA-256:
  `12294f06e903b97252ecae0e5bc9fd0d839f3b94e085dbe1d54f59cbc309bc23`
- clean-environment installed-wheel probe: `PASS`
- installed publication probe stdout:
  `github-publication-probe-ok`
- package inventory: 47 members, all four required Stage 21B runtime modules,
  no prohibited test or fixture members
- conformance evidence: `PASS`, including empty static and secret findings

Build and conformance outputs remain ignored, external evidence and are not
repository payload.

## 6. Required closure

Before another push, a new five-seat Council review must bind the exact amended
source, test, tool, and recovery-record aggregate. After that push, all four
required GitHub Actions jobs and all four conformance artifacts must pass and
publish. A failed replacement run reopens this recovery record; it must not be
represented as acceptance evidence.

## 7. Boundary

This recovery work authorizes no pull request, merge, branch-protection change,
credential access, GitHub App operation, live Stage 21B adapter call,
deployment, production use, KOS or IDM change, signing, identity allocation,
or membership activation.
