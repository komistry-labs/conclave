# CONCLAVE Stage 21C Council Review 0005

Status: `1/5 PASS_EXACT_DRAFT / 4/5 FAIL_EXACT_DRAFT / REMEDIATION REQUIRED`

Review date: 2026-09-10

## 1. Exact reviewed object

- File:
  `INCREMENT-21C-EXACT-HEAD-REVIEW-AND-HUMAN-AUTHORIZED-MERGE.md`
- SHA-256:
  `d82af781441b916855861322c5c8143d70abf3211c21f823d31866046eb954a1`
- Git blob: `ff68bd9ab22080a526e2a9d17f45335fe7615a08`
- Size: `93,777` bytes
- Length: `1,712` LF-terminated lines
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

1. The GraphQL interrupted-read union is not mutually exclusive for a lease
   followed by zero complete pairs and an absent first admission: both
   `lease_present` and `graphql_pages_incomplete` can encode the same durable
   prefix.
2. The rate rules do not explicitly state whether global validation of every
   present rate header occurs before the valid-`Retry-After` precedence rule.
   Mixed valid and malformed fields can therefore produce different durable
   classifications.
3. A zero-transmission mutation terminal requires proof that the deterministic
   admission path is absent, but its exact fields can bind only interrupted
   read inventories. The mutation-side admission-path evidence is not
   referenceable by that terminal.

The high-level authority separation, disposable-only target boundary,
permanent target claim, protection freeze, one-send/no-retry rule, and
non-production boundary otherwise passed this seat.

### Seat 2 — GitHub API and schema correctness

Verdict: `FAIL_EXACT_DRAFT`

Blocking finding:

1. A response containing valid `Retry-After` plus malformed or duplicate
   `X-RateLimit-Remaining` matches both `rate_signal_invalid` and
   `secondary_limited`; malformed `Retry-After` plus remaining zero has the
   symmetric problem. Downstream response and refusal variants differ by that
   choice. All present fields must be validated first, with any invalidity
   winning, before valid-field precedence is applied.

The endpoint and permission table, fixed GraphQL query/hash, page-10 and
partial-result inventory additions, media grammar, projections, operation
arithmetic, and cross-platform parser independence otherwise passed this seat.

### Seat 3 — Security, trust, and append-only integrity

Verdict: `PASS_EXACT_DRAFT`

This seat found no blocker in its assigned scope. It verified:

- externally pinned trust and three distinct signer roles;
- separate disposable capability, evidence-only readiness, and merge
  authority;
- complete ruleset, protection, administrator, and bypass evidence;
- deterministic claims, lease binding, and permanent target exclusion;
- durable one-way admission, one transmission, and zero retry;
- conservative external/concurrent merge attribution;
- immutable terminal, capsule, receipt, reconciliation, and ledger history;
  and
- the no-production, no-KOS/IDM, no-identity/membership authority boundary.

### Seat 4 — Evidence, conformance, and platform operations

Verdict: `FAIL_EXACT_DRAFT`

Blocking finding:

1. After the mutation lease is durable, failure or crash while exclusively
   creating the admission can leave its path absent or invalid/partial before
   any send. A `lease_present` terminal must prove the absent admission path to
   claim zero transmissions. The terminal can bind only §8.7 read inventories;
   `github-merge-terminal-inventory` contains admission path state but is
   available only to later reconciliation when terminal artifacts are
   unusable. No successfully stored terminal can bind its required mutation-
   prefix proof.

The page-10 continuation repair, partial GraphQL result states, remaining
terminal/capsule/receipt recovery, exact arithmetic, non-vacuity, installed-
wheel isolation, and Windows/macOS/Linux evidence otherwise passed this seat.

### Seat 5 — Independent adversarial implementability

Verdict: `FAIL_EXACT_DRAFT`

Blocking findings:

1. Mixed valid and invalid rate headers have contradictory applicable rules.
   Global multiplicity/syntax validation must precede all value and status
   precedence.
2. Zero complete GraphQL pairs with absent first admission overlaps
   `lease_present` and `graphql_pages_incomplete`.
3. The terminal page-state tuple requires invalid/partial admission to have an
   absent result. It cannot represent a once-valid admission that becomes
   corrupted after dispatch while the result path remains valid or itself
   invalid/partial. Observable artifact states must be independently retained
   without treating an unresolvable chain as complete.

The bounded media grammar, page-10 continuation state, one-send/no-retry rule,
conservative outcome attribution, arithmetic, and authority boundaries
otherwise passed this seat.

## 3. Consolidated mandatory remediation

Before Review 0006, a corrected exact candidate must:

1. define rate classification as one total ordered algorithm: validate
   multiplicity, ASCII syntax, and numeric bounds of every present rate field;
   if any field fails, return `rate_signal_invalid`; only otherwise apply
   valid `Retry-After`, remaining-zero, status-429, and default precedence;
2. add mixed-field adversarial vectors for valid/malformed/duplicate
   combinations across HTTP 200, 403, 404, 405, 409, 422, 429, and an
   unrecognized status;
3. make `lease_present` the sole representation for zero complete GraphQL
   pairs when both first-page paths are absent, or define another single
   canonical representation with no overlap;
4. make GraphQL terminal page-path states total under later corruption: retain
   admission and result path states independently, including a valid or
   invalid/partial result beside an absent or invalid/partial admission, while
   refusing to count a pair as complete unless both artifacts and their
   predecessor binding are valid;
5. distinguish artifact presence from chain validity and add positive and
   negative recovery tests for all permitted page-path combinations;
6. define an immutable mutation-prefix inventory, or broaden the existing
   terminal inventory for ordinary terminal construction, so every zero-
   transmission mutation terminal can bind deterministic admission-path state
   and its exact absent or invalid/partial byte commitment;
7. propagate the mutation-prefix inventory through terminal, failure capsule,
   receipt, later reconciliation, and ledger schemas without using it to infer
   a remote outcome; and
8. add non-vacuous crash mutants immediately before and during admission
   persistence, proving whether zero transmission is durably supportable and
   forcing ambiguity wherever it is not.

The correction must remain additive to frozen Stage 21A and Stage 21B and must
not widen credentials, live targets, mutation count, retry, repository scope,
or production authority.

## 4. Review 0004 remediation confirmed

Council Review 0005 confirmed that the principal Review 0004 repairs were
materially effective: page-10 continuation is retained as ten complete pairs
without page-11 admission; partial page-result state is named; every valid
`Retry-After` is intended to block on every status; and `other_valid` now has a
bounded library-independent ASCII grammar. The remaining findings are narrower
totality, precedence, and mutation-prefix evidence defects inside or adjacent
to those repairs.

Reviews 0001 through 0004 remain immutable historical records.

## 5. Review boundary

This review rejects only the exact candidate identified in §1. It grants no
authority to remediate, freeze, implement, access credentials, create or
install a GitHub App, call a live endpoint, change a repository, commit, push,
create a pull request, merge, alter protection, deploy, use production, change
KOS or IDM, sign, allocate identity, or activate membership.

The next permitted action requires bounded local protocol-remediation
authority, followed by a new exact-hash five-seat Council review. No rejected
finding is silently discarded.
