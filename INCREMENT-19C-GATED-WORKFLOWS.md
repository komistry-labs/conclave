# Increment 19C — Opt-in gated workflows

## Disposition

**IMPLEMENTED WITHIN THE AUTHORIZED 19C BOUNDARY.** Repository application is
governed by a separate reviewed PR, exact-head CI and protected-main
post-merge CI.

## Delivered

Increment 19C adds explicit workspace identity modes:

- `local` preserves v0.7 behavior and is the default for new and legacy
  workspaces;
- `verify` additionally requires a current immutable identity PASS bound to
  the exact human principal, verified ledger genesis and gated target; and
- `attested` additionally requires one exact, verified, non-conflicting signed
  evidence binding for the gated target.

Mode changes require exact interactive principal entry, a valid initialized
ledger for stronger modes, and are monotonic. No command silently upgrades or
downgrades a workspace.

The gate is applied to:

- live and concurrent provider egress decisions;
- live sequential-synthesis egress decisions;
- recording a separate human authority decision;
- recording a factual signed-evidence receipt; and
- recording an externally attested immutable ledger checkpoint.

Public actor-binding claims can be imported idempotently. Import records only
`awaiting-verification`; it does not establish PASS, membership or authority.

## Authority boundary

The existing exact-principal ceremony and every KOS authority check remain
mandatory. Identity PASS and `audit.sign` evidence supplement those checks and
never replace them. The evidence attached to an authority-decision flow covers
the exact immutable Council Review input; it does not cryptographically express
approval of the later human decision.

All gate and receipt results retain:

- `authority_effect: none`;
- `decision_effect: none` where applicable;
- `membership_effect: none`; and
- no independent action authority.

Provider, model and API-account identity cannot satisfy the human-principal
gate. Conflicting evidence blocks reliance rather than causing CONCLAVE to
select a preferred envelope.

## Checkpoints

Checkpoint candidates are closed, hash-bound summaries of one verified ledger
prefix. They contain the verified workspace ID, ledger schema, entry count and
chain hash, with no timestamp-derived identity. CONCLAVE prepares only the
unsigned public candidate. An external attestation must pass the 19B verifier
boundary before the principal may record the factual signed-checkpoint event.
CONCLAVE exposes no signing or key operation.

## Validation

Local Windows validation on 2026-08-16:

- focused 19A–19C suites: **171 passed, 1 platform-conditional symlink test
  skipped**;
- complete suite: **871 passed, 1 platform-conditional test skipped**;
- Python compilation: **PASS**; and
- all v0.7, 19A and 19B behavior: **no regression**.

The reviewed PR and protected-main matrices cover Python 3.12 on Windows and
Python 3.13 on Ubuntu. Actual IDM/COSE, external broker and macOS conformance
remain Stage 19D work.

## Preserved non-authorization

19C does not provide or authorize private keys, signing, key loading,
passphrases, identity allocation or issuance, trust-domain bootstrap,
membership, constitutional action, KOS or IDM mutation, deployment, release or
production reliance.
