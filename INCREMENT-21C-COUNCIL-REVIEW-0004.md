# CONCLAVE Stage 21C Council Review 0004

Status: `2/5 PASS_EXACT_DRAFT / 3/5 FAIL_EXACT_DRAFT / REMEDIATION REQUIRED`

Review date: 2026-09-10

## 1. Exact reviewed object

- File:
  `INCREMENT-21C-EXACT-HEAD-REVIEW-AND-HUMAN-AUTHORIZED-MERGE.md`
- SHA-256:
  `95fa98ce569f1f0553c3d0d75ef9804029bdf3832bc2185f25862de1b3b3d3c1`
- Git blob: `291cdd8782c5604bc69c16fb8494a28fb1369842`
- Size: `89,714` bytes
- Length: `1,649` LF-terminated lines
- Governing baseline:
  `HEAD == origin/main == dda5961fa4aa0c67acafac2de230e9ce9313a03e`

All five seats independently recomputed the exact candidate identifiers. The
frozen Increment 21 master protocol independently remained SHA-256
`89a05211a4323db2e79d2854952b24ce033c71f357430c7ac839457ff0878d75`
and Git blob `83d8fb2cabb9d343b6a8d089d920d25dcd8c5728`.

The embedded GraphQL query independently remained exactly 440 UTF-8 bytes and
SHA-256
`6249f30d7812a26534ae9cf06fd0683f2a8e57c75ca56873a5452fbb35d60e0a`.

The full repository suite passed before review: `1301 passed, 2 skipped`.
This review records the candidate without modifying it. Any correction creates
a different exact object and requires a new five-seat review.

## 2. Council verdicts

### Seat 1 — Governance and authority

Verdict: `FAIL_EXACT_DRAFT`

Blocking findings:

1. The protocol requires page-10 continuation to block, but its closed
   interrupted-read union cannot preserve the resulting ten complete page
   admission/result pairs. A mandatory failure state that cannot be recorded
   or reconstructed is not governable evidence.
2. A valid `Retry-After` on a status other than 403 or 429 can be classified
   `not_rate_limited`, while the global policy requires every observable
   `Retry-After` signal to stop. This permits contradictory admission and
   terminal evidence.
3. The open phrase “syntactically valid printable-ASCII media type” delegates
   a result-changing decision to unspecified parser behavior. The same bytes
   can therefore produce different refusal or ambiguity evidence across
   implementations.

The authority separation, disposable-only target boundary, permanent target
claim, one-transmission mutation ceiling, zero retry, and no administrator
exception path otherwise passed this seat.

### Seat 2 — GitHub API and schema correctness

Verdict: `FAIL_EXACT_DRAFT`

Blocking findings:

1. `graphql_pages_incomplete` permits only zero through nine complete page
   pairs, while `graphql_pages_complete_without_observation` permits ten only
   when page 10 has `hasNextPage:false`. The required page-10-continuation
   rejection therefore leaves ten durable pairs that fit neither variant.
2. The rate classifier recognizes a valid `Retry-After` as
   `secondary_limited` only for 403 or 429. A 200 with valid `Retry-After` and
   absent or positive remaining can become `not_rate_limited` and satisfy the
   success shape, contradicting the mandatory global stop rule.
3. `other_valid` lacks a normative media-type grammar and deterministic rules
   for tokens, whitespace, parameters, quoting, escaping, duplication, and
   ordering. Because its classification changes `status_refusal` into
   `ambiguous_response`, this is a schema and cross-platform behavior gap.

The endpoint inventory, mandatory repository-hash-algorithm read, fixed
GraphQL query/hash, page predecessor rule, canonical merge-body order, and
operation/rate arithmetic otherwise passed this seat.

### Seat 3 — Security, trust, and append-only integrity

Verdict: `PASS_EXACT_DRAFT`

This seat found no blocker in its assigned scope. It verified:

- externally pinned trust and three pairwise-distinct signer roles;
- separately signed disposable capability, assessment authority, and merge
  authority;
- complete ruleset, legacy-protection, administrator, and bypass evidence;
- parent-bounded operation authorization, deterministic intents, pre-
  credential claims, and credential-lease binding;
- permanent repository/PR target exclusion across crashes and concurrency;
- immediate revalidation, durable admission, one transmission, and zero
  retry;
- non-attributed external/concurrent merge classification;
- valid, absent, and invalid/partial artifact states; and
- fresh signed read-only reconciliation and append-only ledger history.

### Seat 4 — Evidence, conformance, and platform operations

Verdict: `PASS_EXACT_DRAFT`

This seat found no blocker in its assigned scope. It verified GraphQL page
admission/result chaining, artifact-state handling, post-mutation proof,
negative `unmerged_pr` evidence, external/concurrent outcome handling,
terminal/capsule/receipt/reconciliation reconstruction, deterministic crash
and storage-failure tests, production-path loopback and network denial, and
installed-wheel evidence on Windows, macOS, and Linux.

Seat 5's adversarial boundary test subsequently found a closed-union defect in
the page-10-continuation state. That later finding does not rewrite Seat 4's
independent verdict.

### Seat 5 — Independent adversarial implementability

Verdict: `FAIL_EXACT_DRAFT`

Blocking finding:

1. A complete accepted tenth GraphQL page whose result has
   `hasNextPage:true` must block and cannot create a complete observation, but
   neither interrupted-read inventory variant can represent its ten complete
   pairs. This makes the exact pagination boundary non-total and prevents
   deterministic crash/restart reconstruction.

Seat 5 also requested explicit closure and a dedicated test for an invalid or
partial page-result write following a valid page admission. The deterministic
path-state collection appears intended to cover it, but the lifecycle bullet
names only an unmatched page-admission path and should not leave this state to
inference.

## 3. Consolidated mandatory remediation

Before Review 0005, a corrected exact candidate must:

1. allow `graphql_pages_incomplete` to represent zero through ten complete
   page pairs, with ten permitted only when page 10 is complete and
   `hasNextPage:true`;
2. forbid any page-11 admission and permit an optional unmatched page
   admission only below the ten-page boundary;
3. explicitly represent an invalid/partial page-result path after a valid
   page admission, without treating partial bytes as a record or allowing an
   overwrite;
4. add positive inventory/reconstruction tests for page-10 continuation and a
   partial page-result, plus negative page-11/overflow and invalid-state tests;
5. classify a syntactically valid `Retry-After` on every HTTP status as a
   blocking rate signal, or otherwise define an equally strict closed rule
   that can never satisfy `success_shape` or a non-rate refusal;
6. reconcile the response classifier with the global rule that any observable
   `Retry-After` stops execution and that headers may narrow but never expand
   authority; and
7. replace “syntactically valid printable-ASCII media type” with one explicit,
   bounded byte grammar and deterministic parsing/classification algorithm,
   including whitespace, token characters, parameters, quoting, escaping,
   duplicate parameters, and ordering—or narrow `other_valid` to a simpler
   fully enumerated grammar.

The correction must propagate these rules through the exact schemas, reason
codes, result reducer, inventory reconstruction, acceptance tests, and
remediation traceability without changing frozen Stage 21A or Stage 21B.

## 4. Review 0003 remediation confirmed

Council Review 0004 confirmed that the ten Review 0003 findings were
materially addressed: the post-mutation projection now has merged and
unmerged variants; external/concurrent merge observation is non-attributing;
the merge body uses canonical sorted order; page-one predecessor nullability
is explicit; media and rate classes are enumerated; GraphQL cost is one with a
strict same-window decrement; the rate read is no longer double-counted; read
and page prefixes have an immutable inventory; a local refusal result is
compatible with `NOT_MERGED_OBSERVED`; and artifact paths distinguish valid,
absent, and invalid/partial-present states.

Review 0004 found narrower defects inside the new pagination-boundary and
classifier rules. Reviews 0001 through 0003 remain immutable historical
records.

## 5. Review boundary

This review rejects only the exact candidate identified in §1. It grants no
authority to remediate, freeze, implement, access credentials, create or
install a GitHub App, call a live endpoint, change a repository, commit, push,
create a pull request, merge, alter protection, deploy, use production, change
KOS or IDM, sign, allocate identity, or activate membership.

The next permitted action requires bounded local protocol-remediation
authority, followed by a new exact-hash five-seat Council review. No rejected
finding is silently discarded.
