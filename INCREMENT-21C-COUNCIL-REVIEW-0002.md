# CONCLAVE Stage 21C Council Review 0002

Status: `5/5 FAIL_EXACT_DRAFT / REMEDIATION REQUIRED`

Review date: 2026-09-10

## 1. Exact reviewed object

- File:
  `INCREMENT-21C-EXACT-HEAD-REVIEW-AND-HUMAN-AUTHORIZED-MERGE.md`
- SHA-256:
  `f306134fa93a61b14393579f018a348c7958fe445de36e6bdd90d934d056bafd`
- Git blob: `6f22c4d167cbeb8f1a4c6e6b886d787b22ca8821`
- Size: `70,117` bytes
- Length: `1,340` LF-terminated lines
- Governing baseline:
  `HEAD == origin/main == dda5961fa4aa0c67acafac2de230e9ce9313a03e`

All five seats independently recomputed the exact candidate identifiers. The
frozen Increment 21 master protocol also independently recomputed to SHA-256
`89a05211a4323db2e79d2854952b24ce033c71f357430c7ac839457ff0878d75`
and Git blob `83d8fb2cabb9d343b6a8d089d920d25dcd8c5728`.

The embedded GraphQL query independently recomputed to exactly 440 UTF-8 bytes
and SHA-256
`6249f30d7812a26534ae9cf06fd0683f2a8e57c75ca56873a5452fbb35d60e0a`.

This review records the rejected byte sequence without modifying it. Any
correction creates a different exact object and requires a new five-seat
review.

## 2. Council verdicts

### Seat 1 — Governance and authority

Verdict: `FAIL_EXACT_DRAFT`

Blocking findings:

1. The mandatory per-operation attempt claim is not present in the mutation's
   authoritative causal chain, so the merge lease cannot be proven to descend
   from the complete authorization and intent chain required by the protocol.
2. The terminal union cannot truthfully preserve every authorized durable
   prefix. A block after intent or lease creation but before admission is a
   zero-transmission fact, yet the only zero-transmission variant requires
   those predecessor references to be null.
3. The reconciliation authority requires terminal or failure artifacts that
   its own failure model permits to be absent, preventing governed recovery of
   the states that most require reconciliation.

These are authority-record and factual-truth defects: implementation would
have to infer or invent governance state that is not expressed by the frozen
candidate.

### Seat 2 — GitHub API and schema correctness

Verdict: `FAIL_EXACT_DRAFT`

Blocking findings:

1. One GraphQL logical-operation intent binds one exact request body, but page
   two onward contains a provider-generated cursor unavailable when that intent
   is sealed. No immutable per-page request/cursor chain binds the actual body
   sent on every page.
2. The two-pass GraphQL equality rule refers to normalized projections while
   the durable projection contains changing rate facts. Normal PR/thread state
   can be stable while `rateLimit.remaining` changes, leaving equality
   impossible or underdefined.
3. Documented non-200 merge refusals can create a result that requires a
   response-projection hash, but the candidate defines a complete projection
   only for HTTP 200.
4. The zero-transmission lifecycle variants do not cover durable intent and
   lease prefixes created by the prescribed execution order.

The endpoint methods, permissions, fixed query, REST projections, head-only
merge precondition, strict-base control, ancestry proof, and `79 + 79 + 1 + 5
= 164` transmission arithmetic otherwise passed this seat.

### Seat 3 — Security, trust, and append-only integrity

Verdict: `FAIL_EXACT_DRAFT`

Blocking findings:

1. Section 8 mandates `github-operation-attempt-claim/0.2.0` before every
   credential resolution, but the merge sequence moves from generic and
   merge-specific intent directly to lease resolution. Admission, result,
   terminal, receipt, ledger, and reconstruction also omit that operation
   claim.
2. Zero-transmission failure states after revalidation, generic intent, merge
   intent, operation claim, or lease lack a prefix-complete immutable terminal
   representation.
3. Terminal-storage failure is not an exact discriminated capsule variant, and
   later reconciliation authorization, read chains, receipt, and ledger event
   are absent from the normative reconstruction sequence.

The external trust pin, three-signature separation, effect constants,
credential isolation, permanent repository/PR target claim, no-bypass
coverage, protection freeze and closeout, and non-production boundary passed.

### Seat 4 — Evidence, conformance, and platform operations

Verdict: `FAIL_EXACT_DRAFT`

Blocking findings:

1. The terminal union cannot encode valid target-claim, revalidation, intent,
   attempt, or lease prefixes that stop before admission.
2. Reconciliation authorization requires original terminal and receipt/capsule
   references even though the recovery model permits both to be absent and
   represented by an immutable inventory.
3. HTTP 403, 404, 405, 409, and 422 refusal results have no closed status-only
   response projection or deterministic arbitrary-body discard contract.

The additive profiles, disposable-only overlay, separate rate budgets,
ancestry recovery, source-only production-path loopback, network denial,
cryptographic vectors, installed-wheel isolation, evidence inventories, and
four-platform requirements passed.

### Seat 5 — Independent adversarial implementability

Verdict: `FAIL_EXACT_DRAFT`

Blocking findings:

1. Paginated GraphQL bodies and response-derived cursors lack an immutable
   per-page transcript binding.
2. Stable PR/thread equality is not separated from changing rate facts.
3. A timeout or disconnect may produce no result, and later proof may establish
   `MERGED_CONFIRMED_AFTER_AMBIGUITY`, but the terminal rules require every
   confirmed-merge variant to have a result.
4. Pre-admission crash prefixes are not closed by the terminal union.
5. Reconciliation authorization cannot express an absent terminal and absent
   failure capsule even though the recovery model explicitly allows it.
6. Non-200 refusal bodies have no exact response projection and discard rule.

The target-wide claim, no-bypass and control freeze, rate ceilings, residual-
race treatment, disposable capability, and adversarial evidence design
otherwise passed.

## 3. Consolidated mandatory remediation

Before another exact-hash review, a corrected candidate must:

1. define an immutable ordered GraphQL page transcript binding pass/page
   ordinal, previous response and cursor hashes, canonical request-body hash,
   response/projection hash, returned cursor hash, continuation state, and rate
   facts, then bind the ordered page records into the pass observation;
2. compare a separate stable repository/PR/thread projection while retaining
   and validating rate facts independently;
3. insert the mutation `github-operation-attempt-claim/0.2.0` after both
   intents and before credential resolution, and require it throughout lease,
   admission, result, terminal, receipt/capsule, ledger, and reconstruction;
4. replace the zero-transmission terminal case with a prefix-complete
   discriminated union covering target claim through lease, requiring all
   earlier predecessors and prohibiting all later ones;
5. allow `MERGED_CONFIRMED_AFTER_AMBIGUITY` to be proven from durable admission
   and complete read-only proof when no complete response result exists;
6. give reconciliation authorization the same terminal-present, capsule-
   present, or artifact-absent-with-inventory union as reconciliation receipt;
7. define exact terminal-store-failed and receipt-store-failed capsule variants
   and extend reconstruction through later reconciliation and its ledger event;
   and
8. define closed, bounded, provider-text-free refusal projections for each
   admitted non-200 status, leaving unmatched shapes ambiguous.

These corrections must preserve the already-correct 38-logical-operation and
164-transmission arithmetic or publish a new complete calculation if record or
network behavior changes. Durable per-page records alone do not add network
transmissions.

## 4. Verified remediations retained from Review 0001

All seats agreed that the remediated candidate materially closed the first
review's major architecture findings:

- frozen Stage 21A and Stage 21B remain unchanged and Stage 21C uses additive
  record versions;
- every durable family inherits explicit no-authority, no-decision,
  no-membership, and no-production effects;
- signer profiles are rooted in an externally pinned governed trust policy;
- the permanent repository/PR target claim closes cross-authorization and
  cross-session duplicate merge attempts;
- ruleset, organization, legacy protection, administrator, and acting-identity
  bypass evidence is complete and independently frozen through response;
- the fixed GraphQL query has immutable repository/PR identities, exact raw
  parsing, and bounded enumeration;
- REST/core and GraphQL primary budgets are separated and secondary-limit
  uncertainty is represented honestly;
- latest-head-pusher provenance, post-merge `merge_commit_sha`, strict server
  base currency, explicit residual-race outcomes, and later ancestry proof are
  present;
- the live-exercise overlay is restricted to a separately authorized dedicated
  disposable repository and excludes KOS, IDM, CONCLAVE `main`, client, and
  production targets; and
- production-path loopback, installed-wheel, adversarial, package, network,
  leak, signature-vector, exact-inventory, and four-platform evidence is
  non-vacuous.

Review 0001 remains historical and is not replaced by this record.

## 5. Review boundary

This review rejects only the exact candidate identified in §1. It grants no
authority to freeze, implement, access credentials, create or install a GitHub
App, call a live endpoint, change a repository, commit, push, create a pull
request, merge, alter protection, deploy, use production, change KOS or IDM,
sign, allocate identity, or activate membership.

The next permitted action is bounded local protocol remediation followed by a
new exact-hash five-seat Council review. No rejected finding is silently
discarded.
