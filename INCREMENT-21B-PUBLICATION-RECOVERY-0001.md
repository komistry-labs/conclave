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

No GitHub endpoint, credential flow, mutation budget, approval gate, authority
boundary, KOS behavior, IDM behavior, or production capability changed.

## 5. Local recovery evidence

- focused publication and installed-wheel-probe suite: `124 passed`
- directly targeted recovery regressions: `2 passed`
- complete Windows/Python 3.12 suite: `1,299 passed`, `2` permitted skips,
  zero failures and zero errors
- collected tests: `1,301`
- scoped Ruff check and format verification: pass
- fresh wheel SHA-256:
  `7bd825d37645dc0a2581d69892f8191b972c6c0d12d011ca7b989f5c7b3213eb`
- fresh sdist SHA-256:
  `40dbc851a25c47c48622dc1626c5135db7128785c9fd3c20b972bb2414e38354`
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
