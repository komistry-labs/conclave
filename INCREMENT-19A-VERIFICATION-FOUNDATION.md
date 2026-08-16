# Increment 19A — Verification foundation

## Current disposition

**IMPLEMENTED WITHIN THE AUTHORIZED 19A BOUNDARY.** Repository application is
governed by a reviewed PR, exact-head CI and protected-main post-merge CI.

Arthur authorized bounded Increment 19A implementation. The authorization did
not extend to Increment 19B, 19C or 19D; identity or key allocation; signing;
trust-domain bootstrap; KOS or IDM changes; constitutional action; deployment;
release; or production use.

## Delivered boundary

Increment 19A adds `src/conclave/identity.py`, which provides:

- strict, immutable, closed models for `idm-trust-input-set/0.1.0`,
  `idm-actor-binding/0.1.0` and `idm-verification-result/0.1.0`;
- canonical JSON content hashes for each record;
- exact binary SHA-256 binding for IDM artifacts, trust bundles, revocation
  evidence and trusted-time evidence;
- a machine-readable dependency pin at `policies/idm-reference-pin.json`;
- an IDM verifier protocol containing verification operations only—there is no
  key, allocation, issuance or signing method;
- fail-closed cross-checks for the implementation baseline, trust-input
  reference and hash, trust domain, EID, MID, VID, role, scope and every
  normalized verification finding;
- mandatory authoritative revocation and trusted-time inputs;
- deterministic ordered reason codes with adapter exceptions sanitized;
- verification results that always record `authority_effect: none`,
  `membership_effect: none` and `action_execution_allowed: false`; and
- immutable conflict-refusing storage with idempotent identical retries.

The accepted IDM implementation is pinned to:

| Item | Exact value |
|---|---|
| Commit | `3769ce3943c87e6a5a72bf94b0efdaa2b11c3bd2` |
| Tree | `425f650696a798c10f2a553781fee45e0950dc2a` |
| Wheel SHA-256 | `07120effab0182701e47449e572b94e5a952c210aebfdf217fd965696154d903` |
| Source archive SHA-256 | `98335d16dd0dd7bdfeb27fa77374e741e575cec3bbafc009a66c80374188efb7` |

The distribution hashes identify previously verified reproducible build
outputs from the accepted tree. They are dependency evidence only. They do not
adopt the B1/B2 rehearsal trust domain, identities, trust bundle, revocation
state, keys or allocated objects, and they confer no production eligibility.

## Deliberate stage boundary

19A defines and enforces the CONCLAVE side of the public verifier boundary. It
does not bundle the private IDM repository or its wheel. An independently
provisioned verifier must report the exact pinned implementation identity and
CONCLAVE rejects any other identity.

The deterministic test verifier exercises only the normalized public boundary;
it contains no key and performs no signing. It is not represented as an IDM
identity or cryptographic signer. A cryptographic conformance fixture and
external broker remain Stage 19D work and require separate authorization.

19A does not add CLI commands or change existing workspace behavior. Existing
v0.7.0 workspaces remain in local, non-cryptographic mode. Import workflows,
ledger events and evidence envelopes belong to 19B; workflow gates belong to
19C.

## Validation evidence

Local Windows validation on 2026-08-16:

- focused Increment 19A suite: **45 passed**;
- complete CONCLAVE suite: **788 passed**;
- Python bytecode compilation: **PASS**;
- existing v0.7.0 tests: no regression; and
- repository source contains no private key, passphrase, authority directory,
  identity allocation or signing implementation introduced by 19A.

The reviewed PR must pass the required Windows and Ubuntu matrix at its exact
head. After merge, protected `main` must pass the same matrix. Those operational
results are retained by GitHub rather than recursively embedded into the commit
whose exact head they validate.

## Non-authorization preserved

This implementation does not authorize or perform:

- Stage 19B, 19C or 19D behavior;
- use of `E:` or any authority/key directory;
- IDM trust-domain or identity bootstrap;
- UUIDv7, K1, EID, MID, RID, VID or key allocation;
- signing, key generation, key loading or passphrase handling;
- adoption of B1/B2 rehearsal evidence as trust;
- KOS, IDM, ADR or Constitution changes;
- membership, authority or lifecycle effects; or
- deployment, release or production reliance.
