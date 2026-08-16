# Increment 19B — Governed evidence import

## Disposition

**IMPLEMENTED WITHIN THE AUTHORIZED 19B BOUNDARY.** Repository application is
governed by a reviewed PR, exact-head CI and protected-main post-merge CI.

Arthur authorized 19B and directed all departments to review it. Independent
Security & Trust, Architecture & Governance, and Verification & Cross-platform
reviews returned a conditional go with no constitutional blocker. Their
required controls were reconciled before implementation.

## Delivered

`src/conclave/evidence.py` implements:

- closed immutable `evidence-signing-request/0.1.0`,
  `conclave-signed-evidence/0.1.0` and
  `signed-evidence-binding/0.1.0` records;
- signing-request preparation only from a recognized Task Packet, Council
  Review or Synthesis Continuation that passes its native schema and hash;
- workspace replay identity derived from the verified ledger genesis hash;
- canonical workspace-relative POSIX references with traversal, drive, UNC,
  alternate-stream, backslash, symlink, junction and reparse-point refusal;
- bounded single-read artifact and envelope handling;
- an explicit verification-only IDM evidence adapter with no default or
  signature-only fallback;
- full semantic enforcement of attached payload, canonical CBOR, context,
  trust, signature, delegation, role, `audit.sign`, trusted time, expiry,
  revocation and every request/artifact/workspace/identity cross-binding;
- exact binary `.cose` preservation under hash-safe content-addressed names;
- request-scoped locking and immutable idempotent bindings;
- dynamic conflict blocking for distinct envelopes whose parsed payloads
  actually bind the same request—opaque rejected bytes cannot manufacture a
  trusted conflict;
- evidence-only ledger events and snapshot coverage; and
- reconciliation that records artifact existence but never reconstructs a
  verification outcome, signature, approval, authority or membership.

Every request and binding fixes `authority_effect`, `decision_effect` and
`membership_effect` to `none`, and `action_execution_allowed` to `false`.
Even a verified binding reports `VERIFIED_NOT_GATED`; workflow reliance belongs
to 19C and is not enabled by 19B.

## Verification boundary

The injected verifier must return a closed evidence-specific report and the
exact frozen IDM implementation identity. CONCLAVE independently verifies all
public input hashes, report identity, evidence ID, KID, trust domain, role,
scope, time policy and payload cross-bindings. Missing or mismatched verifier
input fails deterministically.

The verifier's implementation claim is part of the trusted adapter boundary;
19B does not misrepresent that self-report as independent cryptographic proof.
Actual IDM/COSE fixture and external broker conformance remain 19D. Tests use
only inert public envelope bytes and deterministic report adapters. They do not
generate, load, unlock or use keys and perform no signing.

## Validation

Local Windows validation on 2026-08-16:

- focused 19B suite: **64 passed, 1 platform-conditional symlink test skipped**;
- complete CONCLAVE suite: **852 passed, 1 platform-conditional test skipped**;
- Python compilation: **PASS**; and
- v0.7.0 and 19A behavior: **no regression**.

The required PR and protected-main matrices cover Python 3.12 on Windows and
Python 3.13 on Ubuntu. The package retains Python 3.10-compatible language
features. Frozen §10 macOS cryptographic evidence remains explicitly
outstanding for 19D, where the adopted IDM fixture is authorized and available.

## Preserved non-authorization

19B does not provide or authorize:

- a key path, signer, broker invocation, passphrase, secret environment input,
  identity allocation, issuance or trust bootstrap;
- automatic provider, model or API-account attester identity;
- identity-mode changes, egress gates, decision gates or signed checkpoints;
- membership, approval, ratification, authority or execution effects;
- KOS, IDM, ADR or Constitution changes;
- Stage 19C or 19D behavior; or
- deployment, release or production reliance.
