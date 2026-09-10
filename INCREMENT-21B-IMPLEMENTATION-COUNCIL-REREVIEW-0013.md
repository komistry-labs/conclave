# CONCLAVE Stage 21B Implementation Council Re-review 0013

Date: 2026-09-10
Disposition: `PASS_EXACT_BUNDLE` — 5/5

## 1. Reviewed candidate

This review covers only the following ordered five-file second-recovery
aggregate:

1. `tools/installed_wheel_probe.py` —
   `3f915cfcf9732c497e765b0d8522ce67a3d01201f8d341e37fe0722910a52e22`
2. `tests/test_installed_wheel_probe.py` —
   `7b8fac9c97c386928385a46203e8873286bed6505b6426bf1b138004e63b0b09`
3. `src/conclave/ledger.py` —
   `e0e3a4fe7e4fb07f137690150b5a95eac69c9a6057c6e98a781379ebee0f2598`
4. `tests/test_ledger.py` —
   `fe68b7a76e520ff1c81fb48ed90c2d0af6a5e28ae7956b4084515a6243d693af`
5. `INCREMENT-21B-PUBLICATION-RECOVERY-0001.md` —
   `2181191270c00eed6052a3f3589c1ba41270bf4e9bdf2f78f2d0d1eaf7f18e7b`

Aggregate construction is the ordered UTF-8 concatenation of each path,
NUL, lowercase file SHA-256, and LF. Its SHA-256 is:

`f545344b57a0aba4cad4b959014dd94d829de6f0d2bbbd2ef6ae3ba821fc1a1f`

Every Council seat independently reviewed the exact aggregate. The three
delegated seats independently recomputed it. Any change invalidates this
review.

## 2. Preserved failed remote evidence

- Run `34444730211` remains a failed first-candidate run. It demonstrated an
  unnormalized Unix no-follow refusal and a Windows temporary-root alias in
  the installed-wheel probe.
- Run `34446903733` remains a failed first-recovery run. It demonstrated that
  the embedded macOS publication probe retained a second non-canonical
  temporary root and that Windows lock creation could report a transient
  `PermissionError` during an exclusive-create collision.

Neither failed run is acceptance evidence. Their observations and corrective
scope are preserved in `INCREMENT-21B-PUBLICATION-RECOVERY-0001.md`.

## 3. Council votes

### Seat 1 — adversarial cross-platform security: PASS

Confirmed that Windows permission-contention handling enters the existing
bounded retry loop without an immediate, race-prone existence decision;
`O_CREAT | O_EXCL` remains the sole acquisition mechanism; no concurrent-entry
path is introduced; and non-Windows permission failures remain immediate.

### Seat 2 — Git, path, and package portability: PASS

Reproduced the release-before-observation interleaving, successful bounded
reacquisition, and cleanup. Confirmed that the embedded macOS publication
probe resolves its own temporary root before either workspace is created and
reproduced the exact fresh package hashes.

### Seat 3 — governance and evidence integrity: PASS

Confirmed the two failed remote runs remain historical failures, diagnoses
that still require replacement remote evidence remain provisional, and the
runtime amendment is limited to the demonstrated Windows race-dependent
defect.

### Seat 4 — protocol and authority boundary: PASS

Confirmed the corrections affect only portable installed-package verification
and bounded exclusive-lock contention handling. They do not broaden the
closed endpoint table, mutation or rate budgets, approval gates, credential
boundary, or authority over KOS or IDM.

### Seat 5 — test, package, and future-KOS suitability: PASS

Confirmed the complete Windows/Python 3.12 suite, targeted regressions, fresh
package installation, installed-wheel probe, static conformance, and secret
scan all pass. The corrections close real portability and concurrency defects
without granting CONCLAVE policy authority over future KOS operations.

## 4. Exact local evidence

- targeted second-recovery regressions: `14 passed`
- complete Windows/Python 3.12 suite: `1,301 passed`, `2` permitted skips,
  `1,303` collected, zero failures and zero errors
- fresh wheel SHA-256:
  `4e24763595d7a92085fca4108ff0d028808e84cb62784cca2cf301a7b54f1ef4`
- fresh sdist SHA-256:
  `12294f06e903b97252ecae0e5bc9fd0d839f3b94e085dbe1d54f59cbc309bc23`
- isolated installed-wheel probe: `PASS`
- installed wheel inventory: `47` members
- embedded publication probe: `github-publication-probe-ok`
- conformance static findings: none
- conformance secret findings: none
- scoped Ruff and diff checks: pass

Replacement Windows, Ubuntu 3.12, Ubuntu 3.13, and macOS remote CI plus their
four retained artifacts remain mandatory post-push acceptance evidence.

## 5. Boundary

This review authorizes preservation of this record and supports only the
already authorized corrective branch commit and push. It does not authorize a
pull request, merge, branch-protection change, credential access, GitHub App
operation, live Stage 21B adapter call, deployment, production use, KOS or IDM
change, signing, identity allocation, or membership activation.
