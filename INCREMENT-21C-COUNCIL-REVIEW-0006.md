# CONCLAVE Stage 21C Council Review 0006

Status: `2/5 PASS_EXACT_DRAFT / 3/5 FAIL_EXACT_DRAFT / REMEDIATION REQUIRED`

Review date: 2026-09-11

## 1. Exact reviewed object

- File:
  `INCREMENT-21C-EXACT-HEAD-REVIEW-AND-HUMAN-AUTHORIZED-MERGE.md`
- SHA-256:
  `2bded70672d5ceb8f671f5bce46692670a53d73473f2cb3f1af6635cf289b515`
- Git blob: `041c456b97a49d013e0247de30d8ef6e5bc59288`
- Size: `102,837` bytes
- Length: `1,844` LF-terminated lines
- Governing baseline:
  `HEAD == origin/main == dda5961fa4aa0c67acafac2de230e9ce9313a03e`

All five seats independently recomputed the exact candidate identifiers. The
frozen Increment 21 master protocol independently remained SHA-256
`89a05211a4323db2e79d2854952b24ce033c71f357430c7ac839457ff0878d75`
and Git blob `83d8fb2cabb9d343b6a8d089d920d25dcd8c5728`.

The embedded GraphQL query independently remained exactly 440 UTF-8 bytes and
SHA-256
`6249f30d7812a26534ae9cf06fd0683f2a8e57c75ca56873a5452fbb35d60e0a`.

The full repository suite passed immediately before review: `1301 passed, 2
skipped`. This review did not modify the candidate. Any correction creates a
different exact object and requires a new five-seat review.

## 2. Council verdicts

### Seat 1 — Governance and authority

Verdict: `FAIL_EXACT_DRAFT`

Blocking findings:

1. For GraphQL, `lease_present` is declared the sole variant when both page-one
   paths are absent, but `graphql_pages_incomplete` accepts an empty valid
   prefix with a later non-absent artifact. If page one is absent and page two
   remains present after corruption, both conditions apply. `lease_present`
   must require every deterministic page path through ordinal 10 to be absent.
2. A valid but predecessor-invalid admission can be represented by
   `mutation_chain_artifact_unusable`, yet no terminal variant accepts that
   inventory. The evidence model therefore records a state the terminal model
   cannot close.
3. The permanent target path blocks forever even when partially created or
   later corrupted, but every downstream recovery family requires a valid
   target-claim reference. Safe blocking without representable evidence is not
   a complete governed state machine.
4. Rate-value precedence is total, but the transport input is not: field-name
   case folding, duplicate-line preservation, comma coalescing, and lossy
   header maps are unspecified and can hide a rate signal.

The authority separation, disposable-only boundary, permanent no-retry
policy, protection freeze, and conservative unknown-outcome handling otherwise
passed this seat.

### Seat 2 — GitHub API and schema correctness

Verdict: `PASS_EXACT_DRAFT`

This seat found no blocker in its assigned scope. It verified:

- validation-first rate classification and closed response mapping;
- the bounded platform-independent media grammar;
- longest-valid GraphQL prefix, fixed per-ordinal suffix, page-10 boundary,
  and partial-result evidence;
- mutation-prefix accounting families;
- endpoint, permission, query, and projection closure; and
- exact `15/78`, `36/162`, core, GraphQL, and local-secondary arithmetic.

The later red-team transport-input and target-path findings do not rewrite
this seat's independent verdict.

### Seat 3 — Security, trust, and append-only integrity

Verdict: `PASS_EXACT_DRAFT`

This seat found no blocker in its assigned scope. It verified:

- the externally pinned trust policy and three distinct signer roles;
- separate disposable capability, readiness evidence, and human merge
  authority;
- complete protection, ruleset, administrator, and bypass evidence;
- permanent target and operation claims, credential-lease binding, and one
  send with zero retry;
- same-process proven-zero versus conservative restart accounting;
- mutation-prefix propagation through terminal, capsule, receipt,
  reconciliation, and ledger records; and
- non-attributing outcomes and the no-production/no-KOS/IDM boundary.

### Seat 4 — Evidence, conformance, and platform operations

Verdict: `FAIL_EXACT_DRAFT`

Blocking finding:

1. `mutation_chain_artifact_unusable` permits a path-valid admission or result
   whose predecessor binding fails and correctly assigns
   `conservatively_one`. `mutation_prefix_uncertain` accepts only an absent or
   invalid/partial admission, while `admitted_without_result` and
   `result_present` require a chain-valid admission. A path-valid but chain-
   invalid admission, with or without a retained result, fits no terminal arm.

The GraphQL suffix repair, mutation-inventory storage-failure capsule,
conservative transmission accounting, remaining recovery families, arithmetic,
non-vacuity, installed-wheel isolation, and Windows/macOS/Linux evidence
otherwise passed this seat.

### Seat 5 — Independent adversarial implementability

Verdict: `FAIL_EXACT_DRAFT`

Blocking findings:

1. Crash or corruption during permanent target-claim creation is not
   representable. The path permanently blocks another attempt, but the
   mutation inventory, terminal inventory, and reconciliation authorization
   require a valid target-claim reference.
2. Rate-header occurrence collection does not mandate ASCII-case-insensitive
   raw field-name matching before coalescing or reject transports that cannot
   prove lossless multiplicity. Platform/library behavior can hide duplicate
   or differently cased rate signals.

The GraphQL fixed-suffix model, validation-first value classifier, mutation-
inventory failure accounting, one-send/no-retry rule, outcome attribution,
arithmetic, and authority boundaries otherwise passed this seat.

## 3. Consolidated mandatory remediation

Before Review 0007, a corrected exact candidate must:

1. make GraphQL `lease_present` require zero complete pairs and every
   deterministic admission/result path for ordinals 1 through 10 `absent`, so
   any retained later artifact selects only `graphql_pages_incomplete`;
2. add a terminal `mutation_chain_uncertain` arm, or broaden the existing
   uncertain arm, to accept every `mutation_chain_artifact_unusable` inventory
   without promoting chain-invalid artifacts to trusted lifecycle references;
3. require that arm to use `conservatively_one`, merged null, proof incomplete,
   `OUTCOME_UNKNOWN`, `not_attributed`, consumed target/mutation authority, and
   no retry, and propagate it through receipt, capsule, reconciliation, and
   ledger evidence;
4. add a target-claim-path inventory variant representing `valid_present`,
   `absent`, and `invalid_or_partial_present` at the deterministic target digest
   path without requiring a valid target-claim reference;
5. bind repository numeric ID, PR node/number, target digest, path byte
   commitment, creation/recovery context, and permanent-consumption fact while
   granting no mutation authority and never permitting claim replacement;
6. propagate unusable-target evidence through failure capsule, terminal
   inventory, read-only reconciliation, and ledger records, with positive and
   adversarial creation-crash and later-corruption tests;
7. define rate-header input extraction before value classification: match field
   names by ASCII case-insensitive bytes, preserve raw field-line occurrences
   before coalescing, reject a transport unable to prove lossless multiplicity,
   and treat comma-coalesced target fields as invalid; and
8. add mixed-case, duplicate-line, comma-coalesced, and lossy-adapter mutants on
   Windows, macOS, and Linux, across every response status class.

The correction must remain additive to frozen Stage 21A and Stage 21B and must
not widen credentials, live targets, mutation count, retry, repository scope,
or production authority.

## 4. Review 0005 remediation confirmed

Council Review 0006 confirmed that Review 0005's principal repairs were
materially effective: all rate field values now pass one validation-before-
precedence algorithm; GraphQL recovery retains the longest valid prefix and
later suffix artifacts; the all-absent zero-page case is intended to be unique;
and mutation-side evidence distinguishes same-process proven-zero, valid-
admission one, conservative restart, and inventory-store failure paths.

The remaining findings concern total closure between adjacent variants and the
raw transport and permanent-target boundaries. Reviews 0001 through 0005
remain immutable historical records.

## 5. Review boundary

This review rejects only the exact candidate identified in §1. It grants no
authority to remediate, freeze, implement, access credentials, create or
install a GitHub App, call a live endpoint, change a repository, commit, push,
create a pull request, merge, alter protection, deploy, use production, change
KOS or IDM, sign, allocate identity, or activate membership.

The next permitted action requires bounded local protocol-remediation
authority, followed by a new exact-hash five-seat Council review. No rejected
finding is silently discarded.
