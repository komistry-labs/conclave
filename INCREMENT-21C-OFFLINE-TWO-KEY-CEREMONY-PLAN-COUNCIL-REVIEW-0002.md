# CONCLAVE Stage 21C Offline Two-Key Ceremony Plan — Council Review 0002

Status: `COMPLETE / FAIL_EXACT_DRAFT / REMEDIATION REQUIRED`

Review date: 2026-09-19

## 1. Exact reviewed object

- candidate: `INCREMENT-21C-OFFLINE-TWO-KEY-CEREMONY-PLAN.md`
- SHA-256:
  `7e489a8a7dd1f429b6ace7360fa98e3f0d0c3eb2c012e6827d5e5030dc67556a`
- Git blob: `4201a9092f95c7c574a89dd222c93769804ba977`
- size: `61,895` bytes
- length: `1,318` LF-terminated lines
- base: `154394c570a9919fc00b7c00779f565f742508e2`

Every seat independently verified the exact identity. Review 0001 was treated
as immutable history. No reviewer edited the candidate.

## 2. Disposition

| Seat | Domain | Verdict |
|---|---|---|
| 1 | Governance | `FAIL_EXACT_DRAFT` |
| 2 | Cryptography and serialization | `PASS_EXACT_DRAFT` |
| 3 | Custody and operations | `FAIL_EXACT_DRAFT` |
| 4 | Security and threat model | `FAIL_EXACT_DRAFT` |
| 5 | Testability and operability | `FAIL_EXACT_DRAFT` |

Aggregate:

`1/5 PASS_EXACT_DRAFT / 4/5 FAIL_EXACT_DRAFT / REMEDIATION REQUIRED`

## 3. Consolidated blockers

1. **Registry governance and authenticity:** the lifecycle registry lacks one
   authoritative governed location, closed append authority, authenticated
   current-head checkpoint, predecessor compare-and-append rule, atomic
   publication, fork/rollback/replay handling, and deterministic consumer head
   selection.
2. **Attestor role collision:** overlap between the control-attestor principal
   and operator, witness, media, or passphrase roles is not expressly closed.
3. **Storage authorization:** the execution authorization cannot represent the
   eight required storage-location commitments or custody plan.
4. **Custody continuity:** custody register, passphrase-holder record, quarterly
   audit, missed-audit, broken-seal, custodian replacement, and conflicting-
   register states lack closed schemas and fail-closed rules.
5. **Handoff proof:** the media receipt lacks a bound physical-receipt hash,
   destination acknowledgement, authorized destination, and final origin-
   authenticated receipt set.
6. **Recovery transaction:** the quorum is named, but recovery purpose, exact
   authorization, record, evidence, origin authentication, outcome, and failure
   disposition are open.
7. **Pre-seed key IDs:** a pre-gate failure leaves manifest-reserved key IDs in
   an unresolved `planned` state; no `abandoned` transition exists.
8. **Device provenance and interval enforcement:** media and origin devices rely
   on self-reported facts, lack approved supply/firmware attestation, and have
   no continuous controller-level class monitoring that catches transient
   BadUSB behavior.
9. **Embedded versus hashed objects:** the canonical contract ambiguously
   applies `content_hash` to embedded `pre_gate_check`, `public_file`, and
   `platform_result` structures. Several manifest-bound hashes lack closed
   objects or exact raw-byte commitment rules.
10. **Media identity preimage:** the domain is named but the complete field,
    type, encoding, normalization, absence, and ordering contract is missing.
11. **Pre-gate measurement closure:** network probe destination/error/bounds,
    system-control projection, clock uncertainty ceiling, and per-predicate
    evidence schemas are incomplete.
12. **Zeroization semantics:** universal zeroization wording conflicts with the
    later bounded-attempt evidence model.
13. **Terminal-result ordering:** a `completed` result and origin evidence can
    exist before custody handoff, while a later handoff failure requires the
    same ceremony to be unsuccessful.
14. **Lifecycle transitions:** quarantine/revocation/retirement ordering is not
    total, and `accepted` requires origin evidence not present in the event.
15. **Failure disposition:** abort and lifecycle schemas cannot express the
    required per-medium and per-key terminal dispositions used by failure-
    injection oracles.

## 4. Materially resolved findings

The successor closed Review 0001's trust-decision hash cycle, high-level
recovery-role identities, verifier build pinning, deterministic CBOR envelope,
origin authentication, mandatory host/firmware/TPM binding, secret/export-media
separation, passphrase profile, bounded secret-leak claims, and two-key atomic
failure after seed creation. Those closures remain subject to fresh review in
any amended successor.

## 5. Next action

Review 0002 and its exact failed candidate remain immutable. A corrected file
is a new candidate and requires an entirely fresh five-seat review. This review
authorizes no freeze, commit, push, implementation, key generation, signature,
trust operation, credential access, live GitHub operation, deployment, KOS or
IDM change, identity allocation, or membership activation.
