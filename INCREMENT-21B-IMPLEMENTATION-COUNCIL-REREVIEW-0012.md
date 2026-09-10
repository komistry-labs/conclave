# CONCLAVE Stage 21B Implementation Council Re-review 0012

Date: 2026-09-10
Disposition: `PASS_EXACT_BUNDLE` — 5/5

## 1. Reviewed candidate

This review covers only the following ordered four-file recovery aggregate:

1. `src/conclave/github_publication.py` —
   `5fedd721a4e0b4ba7583e6a833086c333cf6cec38ee618e4dba8d5af04778190`
2. `tools/installed_wheel_probe.py` —
   `9304955ef035f987ca35e0d468c96e8e6d9ab11e0bb3cbe4be994719789bae16`
3. `tests/test_installed_wheel_probe.py` —
   `fa78ee9d148b3d092cd2ff9684cd28496a8ab16f2941dba7de1ca79c7aa66c1f`
4. `INCREMENT-21B-PUBLICATION-RECOVERY-0001.md` —
   `a3b2070c0910a1ac1eab54eed582ea0e241ade02fb49ada81d9b4b6253318654`

Aggregate construction is the ordered UTF-8 concatenation of each path,
NUL, lowercase file SHA-256, and LF. Its SHA-256 is:

`f8fd463f5abba9cb2af31ed8555220d8b28a1aca84a972c15f6ad899b48954c3`

Every Council seat independently recomputed the aggregate or reviewed against
that exact independently verified value. Any change invalidates this review.

## 2. Preserved rejected candidate

The first recovery draft aggregate
`2fd0958d0bd5e9dba96df664ffba7b24c5d81d0eeab424cff7d8b681d57a723f`
was blocked because canonicalization was local to the environment helper and
the caller retained its potentially aliased root for fixture creation. It was
not committed or pushed and carries no approval.

## 3. Council votes

### Seat 1 — adversarial cross-platform security: PASS

Confirmed `O_NOFOLLOW` remains enforced, root/intermediate/leaf descriptor
open failures close safely and map to `PROPOSAL_CONTENT_CHANGED`, and the
canonical probe root is propagated to every later operational path.

### Seat 2 — Git, path, and package portability: PASS

Confirmed the helper returns the canonical root and `main()` rebinds to it
before installation, fixture creation, and command execution. Confirmed 124
focused tests and exact package evidence, while retaining the remote matrix as
a pending post-push gate.

### Seat 3 — governance and evidence integrity: PASS

Confirmed failed run `34444730211` and the rejected first recovery draft are
preserved as historical failures, the Windows diagnosis remains provisional,
and no remote acceptance is claimed before replacement CI.

### Seat 4 — protocol and authority boundary: PASS

Confirmed the amendment changes failure normalization and test-environment
path identity only. The closed endpoint table, rate and mutation budgets,
approval gates, credential boundary, and prohibition on KOS/IDM authority
remain unchanged.

### Seat 5 — test, package, and future-KOS suitability: PASS

Confirmed the complete Windows/Python 3.12 suite passed 1,299 tests with two
permitted platform skips; the new isolated wheel probe and conformance run
passed; the 47-member wheel contains every required Stage 21B runtime module
and no prohibited test/fixture member. The change improves portable evidence
behavior without granting CONCLAVE authority over KOS.

## 4. Exact evidence

- focused publication and installed-wheel-probe suite: `124 passed`
- complete Windows/Python 3.12 suite: `1,299 passed`, `2` permitted skips,
  zero failures and zero errors
- fresh wheel SHA-256:
  `7bd825d37645dc0a2581d69892f8191b972c6c0d12d011ca7b989f5c7b3213eb`
- fresh sdist SHA-256:
  `40dbc851a25c47c48622dc1626c5135db7128785c9fd3c20b972bb2414e38354`
- isolated installed-wheel probe: `PASS`
- conformance static findings: none
- conformance secret findings: none
- scoped Ruff and diff checks: pass

Windows, Ubuntu 3.12, Ubuntu 3.13, and macOS remote CI plus their four retained
artifacts remain mandatory post-push acceptance evidence.

## 5. Boundary

This review authorizes preservation of this review record and supports only
the already authorized corrective branch commit and push. It does not
authorize a pull request, merge, branch-protection change, credential access,
GitHub App operation, live Stage 21B adapter call, deployment, production use,
KOS or IDM change, signing, identity allocation, or membership activation.
