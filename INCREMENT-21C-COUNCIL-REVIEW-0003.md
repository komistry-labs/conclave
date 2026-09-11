# CONCLAVE Stage 21C Council Review 0003

Status: `1/5 PASS_EXACT_DRAFT / 4/5 FAIL_EXACT_DRAFT / REMEDIATION REQUIRED`

Review date: 2026-09-10

## 1. Exact reviewed object

- File:
  `INCREMENT-21C-EXACT-HEAD-REVIEW-AND-HUMAN-AUTHORIZED-MERGE.md`
- SHA-256:
  `cc865b616dcda1edaa0dbb689ed16292b47d21f44aa67748e03dfcd11d946bec`
- Git blob: `8a369a65ac72e91d214ca800cfb6d4abecd6f76e`
- Size: `80,280` bytes
- Length: `1,508` LF-terminated lines
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

1. The only post-mutation PR projection requires `merged:true`, non-null merge
   OID, and merged time. It cannot represent the open/unmerged facts required
   for a governed `NOT_MERGED_OBSERVED` outcome.
2. The final execution order performs a fresh rate read and then a complete
   observation cycle that already includes that read. Literal execution
   exceeds the signed operation, transmission, and secondary-point ceilings.
3. A refusal response followed by factual proof that the exact merge occurred
   has no truthful non-success terminal outcome. Governance evidence cannot
   infer success, non-mutation, or attribution around that gap.

### Seat 2 — GitHub API and schema correctness

Verdict: `FAIL_EXACT_DRAFT`

Blocking findings:

1. Canonical JSON requires sorted keys, but the mutation requires serialized
   order `sha` then `merge_method`. Sorted canonical order is `merge_method`
   then `sha`, so no request satisfies both rules.
2. The GraphQL page-result schema requires a predecessor result but does not
   provide the explicit null arm needed for page one.
3. Refusal response `media-type class`, `rate class`, accepted contract, and
   403 classification precedence are not closed enums and algorithms.
4. A concurrently or externally completed exact merge can yield a local
   candidate-refusal response followed by complete merge proof, but no factual
   terminal outcome accepts that combination without misattributing success.
5. The fixed GraphQL operation permits cost zero, although the governed query
   must consume one point per call; same-window remaining-value validation is
   consequently too weak.

The Review 0002 GraphQL page binding, stable-state separation, mutation claim,
prefix lifecycle, resultless ambiguity, and nominal refusal variants otherwise
passed this seat.

### Seat 3 — Security, trust, and append-only integrity

Verdict: `PASS_EXACT_DRAFT`

This seat found no remaining blocker in its assigned scope. It verified:

- mutation operation-claim placement and propagation;
- prefix-complete mutation-side terminal variants;
- proof of ambiguous success without a response result;
- terminal/capsule/absent-artifact reconciliation authority;
- terminal- and receipt-store failure variants;
- appended later-reconciliation history and ledger binding;
- external trust root and signer separation;
- complete no-bypass and protection-freeze evidence;
- credential isolation and redaction; and
- the disposable-only, non-production authority boundary.

### Seat 4 — Evidence, conformance, and platform operations

Verdict: `FAIL_EXACT_DRAFT`

Blocking findings:

1. The duplicated final rate read makes the maximum totals 39 logical
   operations, 165 transmissions, 23/86 for the merge plan, and 90 local
   secondary points, rather than the frozen 38/164, 22/85, and 89.
2. Durable interrupted read and GraphQL-page subchains are not represented in
   terminal or inventory records. A page admission can exist without a page
   result or final observation, leaving crash reconstruction incomplete.
3. `NOT_MERGED_OBSERVED` says no merge “commit/result” may exist, ambiguously
   excluding the local `candidate_refusal` result whose reconciliation the
   protocol requires.
4. Refusal media/rate vocabularies and deterministic 403/429 classification
   are incomplete.
5. Artifact recovery has no invalid- or partial-present variant even though a
   failed durable write may retain a partial final-path artifact.

The platform matrix, installed-wheel isolation, disposable target, leak and
network denial, cryptographic vectors, and mutation-based non-vacuity rules
otherwise passed.

### Seat 5 — Independent adversarial implementability

Verdict: `FAIL_EXACT_DRAFT`

Blocking findings:

1. Negative reconciliation is structurally impossible because the post-
   mutation projection rejects `merged:false`, null merge OID, and null merged
   time.
2. A proof-confirmed exact merge following a `candidate_refusal` result has no
   legal non-success incident outcome. The claim must remain consumed and the
   result must not be attributed to CONCLAVE without evidence.

All other attacked paths remained fail-closed: incomplete pages cannot create
readiness; resultless timeout can confirm only through full proof; exhausted
proof budgets yield unknown; reconciliation artifacts remain append-only; and
trust, no-bypass, credential, and target boundaries remain closed.

## 3. Consolidated mandatory remediation

Before Review 0004, a corrected exact candidate must:

1. make post-mutation PR projection a closed `merged_pr | unmerged_pr` union,
   retaining the same repository/PR/base/head identities and exact
   variant-specific nullability;
2. add a factual non-success incident outcome for complete merge proof after a
   refusal, without attributing the external/concurrent merge to CONCLAVE;
3. require the merge body key set exactly and serialize it only in canonical
   sorted order;
4. make GraphQL page-result predecessor exact null iff page ordinal is one and
   otherwise equal to the admission's preceding result;
5. enumerate exact response media and rate classes, accepted body rules, and a
   deterministic status/header classifier including 403 and 429;
6. require GraphQL cost exactly one and same-reset remaining to fall by at
   least each page's cost;
7. remove the duplicated final rate read and recompute the closed plan directly
   from the endpoint inventory rather than an unnamed singleton count;
8. add immutable read-operation and GraphQL-page prefix inventory, including
   page admission without result and incomplete observation, throughout
   terminal, capsule, reconciliation, and receipt evidence;
9. state that `NOT_MERGED_OBSERVED` forbids a remote merge commit while
   permitting a bound local `candidate_refusal` result; and
10. represent valid, invalid/partial-present, and absent terminal/capsule/
    receipt artifacts without contradicting platform durable-write behavior.

Any arithmetic change must remain bound consistently through capability,
assessment, merge authorization, plan, operation authorizations, rate budgets,
and acceptance evidence.

## 4. Review 0002 remediation confirmed

Council Review 0003 confirmed that the prior eight findings were materially
addressed:

- actual GraphQL page bodies and response-derived cursors are pre-admitted and
  chained without retaining raw cursors;
- stable repository/PR/thread state is separated from ordered rate facts;
- the mutation operation claim is inserted before credential resolution and
  propagated through the append-only chain;
- mutation-side zero-transmission terminal prefixes are represented;
- a missing response result can support only fully proved ambiguity recovery;
- reconciliation authority supports terminal, capsule, and artifact-absent
  variants;
- terminal- and receipt-store failures and later reconciliation history are
  separately represented; and
- bounded success, refusal, and ambiguous response variants now exist, though
  their exact refusal classifier still requires closure.

Reviews 0001 and 0002 remain immutable historical records.

## 5. Review boundary

This review rejects only the exact candidate identified in §1. It grants no
authority to freeze, implement, access credentials, create or install a GitHub
App, call a live endpoint, change a repository, commit, push, create a pull
request, merge, alter protection, deploy, use production, change KOS or IDM,
sign, allocate identity, or activate membership.

The next permitted action is bounded local protocol remediation followed by a
new exact-hash five-seat Council review. No rejected finding is silently
discarded.
