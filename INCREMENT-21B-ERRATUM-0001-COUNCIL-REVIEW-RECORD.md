# CONCLAVE Stage 21B Erratum 0001 Council Review Record

Status: `5/5 PASS_EXACT_DRAFT`

Review date: 2026-09-10

## Exact reviewed object

- File: `INCREMENT-21B-ERRATUM-0001-BASE-TREE-CLOSURE.md`
- SHA-256: `f79aae70e15dd90bda10948ee172f77acac3557a87ff2d2f1c35a65a1ed0658e`
- Git blob: `b018de92863a237a2aecf6cb693a9483c1e13e0a`
- Length: 265 lines

Each reviewer independently verified the exact identifiers above. No verdict
for any other byte sequence is counted.

## Council verdicts

1. Governance and authority — `PASS_EXACT_DRAFT`
   - The erratum preserves the original frozen protocol as historical evidence
     and supersedes only the clauses required for verifiable tree closure.
   - The separate source operation is read-only and creates no publication or
     downstream authority.
   - Existing publication limits, endpoint exclusions, and non-authoritative
     effects remain unchanged.

2. Security and credentials — `PASS_EXACT_DRAFT`
   - Closure acquisition is one separately authorized Contents-read request
     against the exact pinned root tree, with fixed query, zero retry, bounded
     response handling, and no fallback.
   - Truncation, identity/hash substitution, malformed paths, invalid modes,
     bad OIDs, duplicate entries, and every stated limit fail before
     publication authorization or publication credential resolution.
   - Publication credentials and request budgets remain separate; secrets and
     repository content remain excluded from ledgers and packages.

3. Git correctness — `PASS_EXACT_DRAFT`
   - A complete non-truncated recursive tree projection supplies sufficient
     canonical path, mode, type, and OID data for bottom-up reconstruction.
   - Parent tree entries bind every reconstructed subtree; the reconstructed
     root binds the source and base observations.
   - Canonical Git ordering, raw object-ID bytes, admitted base modes, affected
     ancestor recalculation, unaffected subtree preservation, and sole-parent
     commit computation are coherent for SHA-1 and SHA-256.

4. Evidence and schemas — `PASS_EXACT_DRAFT`
   - The source authorization/intent/claim/lease/observation chain precedes the
     closure, which precedes every proposal and publication record.
   - The closure is closed, canonical, bounded, immutable, durably stored, and
     cross-bound through terminal and reconciliation evidence.
   - The ledger retains only the closure content hash.

5. Cross-platform testability — `PASS_EXACT_DRAFT`
   - Canonical UTF-8/NFC paths, Git tree serialization/order, raw OID bytes,
     and pinned hashing are independent of the host operating system.
   - Positive and adversarial fixtures cover required Git forms, sorting,
     Unicode, reconstruction, collision, limit, truncation, packaging,
     loopback, and external-network behavior.
   - The Windows, Ubuntu, and macOS acceptance matrix remains explicit.

## Review boundary

This record establishes Council suitability of the exact erratum draft only.
It does not freeze, commit, push, merge, or operationalize the erratum. It does
not authorize runtime or test changes, credentials, live GitHub calls, GitHub
App creation or installation, publication, deployment, production use, KOS or
IDM changes, signing, identity allocation, or membership activation.
