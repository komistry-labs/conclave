# CONCLAVE Stage 21C Offline Two-Key Ceremony Plan — Council Review 0004

Status: `COMPLETE / FAIL_EXACT_DRAFT / REMEDIATION REQUIRED`

Review date: 2026-09-19

## Exact reviewed object

- candidate: `INCREMENT-21C-OFFLINE-TWO-KEY-CEREMONY-PLAN.md`
- SHA-256: `a3870875abcaa0ad81cc4e36ae3e9fe3dfb7d36128c9ac0f36635745b3b57230`
- Git blob: `1c167b389b20d8a366aa965f2c9768cadcda9d88`
- size: `112,000` bytes
- length: `2,448` LF-terminated lines
- base: `154394c570a9919fc00b7c00779f565f742508e2`

All five seats independently verified the object and both controlling protocol
hashes. No reviewer edited it.

## Disposition

| Seat | Domain | Verdict |
|---|---|---|
| 1 | Governance | `FAIL_EXACT_DRAFT` |
| 2 | Cryptography | `FAIL_EXACT_DRAFT` |
| 3 | Custody | `FAIL_EXACT_DRAFT` |
| 4 | Security | `FAIL_EXACT_DRAFT` |
| 5 | Testability | `FAIL_EXACT_DRAFT` |

Aggregate: `0/5 PASS_EXACT_DRAFT / 5/5 FAIL_EXACT_DRAFT`.

## Consolidated blockers

1. Security-attestation, custody-update, lifecycle, and recovery signatures lack
   exact domain-zero-canonical-JSON preimages and exclusion rules.
2. Recovery does not bind the volume-encryption profile, replacement media
   custodian/location, or replacement passphrase-holder record and seals.
3. Repository-wide audits and cross-ceremony adverse actions exceed eight
   custody packages, two lifecycle events, and two/eight disposition limits.
4. Initial custody checkpoint signing cannot use the current ceremony-only
   authenticator inventory without an explicit external governance handoff.
5. New package audit timestamps, authenticated auditor observations, suspended
   package state, and storage-location uniqueness are incomplete.
6. Seal-photo evidence, physical receipt retention lifetime, and capture-device
   attestation role are incomplete.
7. Replacement review evidence is not a closed attributable object.
8. Offline recovery has no governed export/pause/import/resume bridge across
   protected-main custody publication.
9. Success witness, final inventory, terminal device interval, and completion
   ordering leaves terminal artifacts outside the sealed allowlist.
10. Recovery repeats the terminal interval/origin ordering defect.
11. Device-event/liveness logs and fresh TPM quotes lack closed authenticated
    schemas.
12. Cleanup omits the proof-signing buffer; abort stages omit export/origin; one
    sentence still uses retired before abandoned/quarantined.
13. Acceptance case/fixture schemas, case-ID hashing, rejection inventory, and
    cross-platform inventory equality remain open.

## Next action

This exact failed review is immutable history. Any amendment is a new candidate
requiring fresh five-seat review. No freeze, commit, push, implementation, key
generation, signing, trust operation, credential use, live operation,
deployment, KOS/IDM change, identity allocation, or membership activation is
authorized.
