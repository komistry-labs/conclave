# CONCLAVE Stage 21C Offline Two-Key Ceremony Plan — Council Review 0005

Status: `EARLY STOPPED / FAIL_EXACT_DRAFT / REMEDIATION REQUIRED`

Review date: 2026-09-19

## Exact reviewed object

- SHA-256: `1b11eba699e64dfca11e1f2a9cb6e7a5b43174cb0ab5bebb69dda69993f63057`
- Git blob: `4d881064a596b45034bbe2c30ca576cd4c0464fa`
- size: `124,172` bytes
- length: `2,699` LF-terminated lines
- base: `154394c570a9919fc00b7c00779f565f742508e2`

Governance, Cryptography, and Custody independently verified the exact object
and returned `FAIL_EXACT_DRAFT`. Because 5/5 passage was then mathematically
impossible, Security and Testability were not run against this candidate.
Aggregate: `0/3 PASS / 3/3 FAIL / TWO SEATS NOT RUN`.

## Consolidated blockers

1. Pre-origin inventory still requires a signed custody checkpoint that is
   intentionally created only after shutdown; the unsigned checkpoint preimage
   itself lacks a closed schema.
2. Repository-wide lifecycle batches are allowed by authority but the
   publication rule still permits only one or two events.
3. Audit signer identity uses independently sorted parallel arrays rather than
   one nested authenticated auditor object; non-pass signature rules are open.
4. Device monitor, custody review, and audit signatures lack explicit Ed25519
   and canonical base64url requirements.
5. Recovery's transfer medium is not bound by Arthur's authorization.
6. Recovery pause/resume records are absent from result/origin/completion, and
   phase one still depends on a fully signed checkpoint created externally.
7. Cumulative package ordering lacks `package_id` as a final tie-breaker.
8. Storage-location holder equality and nested zone/container/access/environment
   schemas are incomplete.
9. Replacement and recovery do not restate the full current-role collision
   matrix for incoming custodians/holders.
10. Three passphrase-package seals have only one undifferentiated photograph
    hash, and photograph attribution is forced into a receipt-specific schema.

## Disposition

This review is not a five-seat Council approval and cannot support freeze. The
exact failed object and this record are historical evidence only. No commit,
push, implementation, ceremony, key generation, signature, credential, live
operation, trust action, activation, deployment, KOS/IDM change, identity
allocation, or membership activation is authorized.
