# CONCLAVE Stage 21C Offline Two-Key Ceremony Plan — Council Review 0003

Status: `COMPLETE / FAIL_EXACT_DRAFT / REMEDIATION REQUIRED`

Review date: 2026-09-19

## 1. Exact reviewed object

- candidate: `INCREMENT-21C-OFFLINE-TWO-KEY-CEREMONY-PLAN.md`
- SHA-256:
  `5ac168a00b3d1b1ed94b403f08fb631af8ecd9ba29c9a7792e5e32c01c4bbdb0`
- Git blob: `d7c9e8a5c2e07a682c68fa1d264947421afdff98`
- size: `89,881` bytes
- length: `1,957` LF-terminated lines
- base: `154394c570a9919fc00b7c00779f565f742508e2`

Every seat independently verified the exact identity and both controlling
protocol hashes. Reviews 0001 and 0002 remain immutable history. No reviewer
edited the candidate.

## 2. Disposition

| Seat | Domain | Verdict |
|---|---|---|
| 1 | Governance | `FAIL_EXACT_DRAFT` |
| 2 | Cryptography and serialization | `FAIL_EXACT_DRAFT` |
| 3 | Custody and operations | `FAIL_EXACT_DRAFT` |
| 4 | Security and threat model | `FAIL_EXACT_DRAFT` |
| 5 | Testability and operability | `FAIL_EXACT_DRAFT` |

Aggregate:

`0/5 PASS_EXACT_DRAFT / 5/5 FAIL_EXACT_DRAFT / REMEDIATION REQUIRED`

## 3. Consolidated blockers

1. **Execution authority authentication:** the ceremony authorization is
   content-addressed but is not signed or bound to an authenticated protected-
   main governance decision.
2. **Checkpoint verification keys:** custody and lifecycle checkpoint profiles
   do not close algorithm, public-key bytes, signature encoding, immutable
   trust reference, or required signer/key distinctness.
3. **Full-media unlock custody:** mandatory volume encryption has no governed
   credential generation, holder, separation, recovery, rotation, audit, or
   destruction contract.
4. **Role and destination separation:** storage destinations are not mapped to
   the manifested eight holders and can collapse required separation.
5. **Opaque storage commitments:** storage, seal, audit, and recovery policy
   hashes lack closed preimages and semantic validation rules.
6. **Physical receipt artifacts:** exact formats, size limits, retention,
   acquisition provenance, availability, and private/public handling of signed
   receipt bytes are not closed.
7. **Multi-ceremony custody:** the fixed register represents one ceremony and
   eight packages, so rotation cannot preserve prior custody, audit, recovery,
   retirement, and destruction obligations.
8. **Initial custody publication:** a completed result can precede authoritative
   protected-main custody publication, and no authenticated initial publication
   transaction is defined before acceptance.
9. **Audit advancement:** audit observations lack per-role binding and no
   authorized compare-and-replace transaction advances register audit dates.
10. **Replacement transaction:** custodian/holder replacement lacks a closed
    proposal, authority, current-head binding, atomic update, and verification
    record.
11. **Recovery authority and environment:** recovery is not signed or bound to
    protected-main current state, reviewed tool/build/environment, fresh boot,
    device monitoring, profiles, replacement passphrase roles, or cleanup.
12. **Recovery evidence:** no recovery witness schema, recovery-specific receipt,
    total result nullability, failure disposition, or acyclic current-head
    publication ordering exists.
13. **Post-ceremony disposition:** the ceremony-only terminal-disposition schema
    cannot express recovery failure, compromise, revocation, retirement, or
    destruction of one key and its then-current media.
14. **Lifecycle field contradiction:** prose still constrains nonexistent
    `result_or_abort_sha256` instead of the defined transition-evidence member.
15. **Positive planned-ID proof:** the pre-gate does not prove both exact current
    `planned` lifecycle events selected by the manifest.
16. **Two-key lifecycle atomicity:** one-event-per-commit append can publish only
    one of two required accepted/adverse transitions.
17. **Origin-failure dead end:** quarantine requires an origin commitment even
    when origin authentication itself failed.
18. **Lifecycle bootstrap:** a zero-event checkpoint conflicts with the default
    nonempty-array rule and no deterministic genesis transaction is defined.
19. **Device-interval evidence:** the provisional hash precedes later device
    activity, while no terminal event/liveness/detach schema closes the whole
    monitored interval.
20. **Media and host provenance:** firmware, device, controller, authenticator,
    Secure Boot, TPM, PCR, and acquisition commitments lack closed security
    schemas and validation semantics.
21. **Verifier measured boot:** the separate verifier host has no fresh TPM quote
    bound into terminal evidence.
22. **Cleanup evidence:** success does not bind a closed per-buffer destruction-
    attempt record; a witness Boolean cannot support the stated bounded claim.
23. **Five-media gate:** the single media check/evidence form cannot prove all
    five manifested media bindings and their ordered observations.
24. **Custody cardinality:** `[storage_binding,8]` is only an upper bound and does
    not require exactly one of each closed role.
25. **Abort semantics:** the abort object uses retired terminology inconsistent
    with abandoned/quarantined lifecycle states and can omit mandatory reasons
    or known reserved IDs.
26. **Tool acceptance:** zero tests/vectors/injections can satisfy the schema;
    referenced inventories and scans are open hashes without closed coverage
    objects.
27. **Artifact ceilings:** many authorization, evidence, custody, lifecycle,
    terminal, and recovery record classes have no pre-parse byte ceiling.
28. **Time validity:** interval inclusivity, timestamp ordering, and application
    of the 120-second uncertainty at validity boundaries are undefined.

## 4. Material closures retained

The candidate retained substantial valid work: bounded plan-only authority;
two-key purpose separation; Ed25519 public encoding and proof domains;
deterministic CBOR/AAD; Argon2id and XChaCha20-Poly1305 envelope rules; unbiased
passphrases; acyclic receipt preimages; provisional-before-handoff ordering;
dual-key origin authentication; conservative two-key ceremony failure intent;
protected-main rollback/fork principles; and a useful cross-platform negative-
test catalogue. Those closures remain subject to fresh review in a successor.

## 5. Next action

Review 0003 and its exact failed candidate are immutable history. A corrected
file is a new candidate and requires an entirely fresh five-seat review. This
review authorizes no freeze, commit, push, implementation, key generation,
signature, trust operation, credential access, live GitHub operation,
deployment, KOS or IDM change, identity allocation, or membership activation.
