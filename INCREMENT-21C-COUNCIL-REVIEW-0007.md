# CONCLAVE Stage 21C Council Review 0007

Status: `1/5 PASS_EXACT_DRAFT / 4/5 FAIL_EXACT_DRAFT / REMEDIATION OR SCOPE DECISION REQUIRED`

Review date: 2026-09-11

Review execution: five distinct Council seats using `gpt-5.6-sol` with
`xhigh` reasoning. Seats reviewed independently and did not negotiate a
consensus.

## 1. Exact reviewed object

- File:
  `INCREMENT-21C-EXACT-HEAD-REVIEW-AND-HUMAN-AUTHORIZED-MERGE.md`
- SHA-256:
  `2373bb9dbb96146c8b22d868a284ea0be54015720c18ef80406c2633f9a7d6d4`
- Git blob: `84dbb36abd719bc1c60f14ef4c541b9f6e2880fc`
- Size: `117,392` bytes
- Length: `2,062` LF-terminated lines; zero CR bytes; final LF present
- Governing baseline:
  `HEAD == origin/main == dda5961fa4aa0c67acafac2de230e9ce9313a03e`

All five seats independently recomputed the candidate identifiers. The frozen
Increment 21 master protocol independently remained SHA-256
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

1. `target_claim_path_inventory_store_failed` cannot satisfy a non-circular
   target-evidence variant. The valid-claim and valid-inventory arms do not fit;
   the failure-capsule arm is restricted to later reconciliation and would be
   circular if the capsule referenced itself while its hash was being created.
2. The claim-plus-inventory coexistence state has no canonical precedence. It
   can be encoded by omitting either reference, even though the protocol says
   the coexisting claim grants no authority.
3. When claim, inventory, and failure-capsule writes all leave absent paths,
   only a process-local diagnostic remains. A restart cannot distinguish that
   state from an untouched target, so permanent consumption is not durably
   reconstructable.

The frozen-boundary, signer separation, disposable-only restriction, GraphQL
repair, mutation-chain terminal, one-send/no-retry rule, and lossless-header
input otherwise passed this seat.

### Seat 2 — GitHub API and schema correctness

Verdict: `FAIL_EXACT_DRAFT`

Blocking finding:

1. The lossy-header response branch is not schema-total. The protocol mandates
   `ambiguous_response`, `rate_signal_invalid`, and
   `RATE_HEADER_TRANSPORT_LOSSY`, but every result still requires one of the
   four media classes and a bounded core-rate projection. No media-unavailable
   arm or exact-null core-rate arm exists for a transport that cannot prove the
   original header occurrences.

The all-ten-page GraphQL partition, lossless-header classifier, endpoints,
permissions, response mapping outside this branch, and exact `15/78` and
`36/162` arithmetic otherwise passed this seat.

### Seat 3 — Security, trust, and append-only integrity

Verdict: `FAIL_EXACT_DRAFT`

Blocking findings:

1. A valid `mutation_prefix_inventory_store_failed` capsule cannot be selected
   by the later reconciliation authorization. The union accepts a valid
   mutation inventory, an unusable inventory bound by terminal inventory, or a
   target failure before mutation-prefix creation, but not this valid capsule.
2. A contender blocked by a valid target claim belonging to another plan is
   forbidden to create a target-path inventory and has no block-only target-
   evidence, mutation-prefix, and terminal arm of its own.
3. If mutation-prefix inventory storage fails, the capsule and terminal-
   inventory fallback do not retain both independent admission/result path
   states and their `chain_valid:false` mismatch reason. Chain-invalid evidence
   therefore disappears with the failed inventory.

Trust, credential exclusion, conservative accounting, target consumption,
nominal chain-invalid terminal closure, attribution, and production/KOS/IDM
boundaries otherwise passed this seat.

### Seat 4 — Evidence, conformance, and platform operations

Verdict: `PASS_EXACT_DRAFT`

This seat found no blocker in its assigned scope. It verified the GraphQL
partition and page boundary; target-path state commitments; nominal mutation-
chain closure; lossless header behavior; request arithmetic; positive,
negative, mutant, loopback, network-denial, and installed-wheel requirements;
and Windows/macOS/Linux acceptance obligations. This independent PASS does not
override blockers found by other seats.

### Seat 5 — Independent adversarial implementability

Verdict: `FAIL_EXACT_DRAFT`

Blocking findings:

1. The foreign-valid-claim contender state has no terminal evidence arm, as
   independently found by Seat 3.
2. The target-inventory-store-failure capsule retains the target-claim path
   state but only names the target-inventory path. It omits that failed path's
   exact state, byte count, and byte hash, so it cannot satisfy the later
   reconciliation binding.
3. An invalid/partial admission with a later non-absent result satisfies both
   `pre_admission_artifact_unusable` and
   `mutation_chain_artifact_unusable`. No precedence or exclusion selects one,
   and the ambiguity propagates to two different terminal discriminants.

The GraphQL repair, raw-header repair, conservative unknown outcome, arithmetic,
merge-request construction, and authority boundaries otherwise passed this
seat.

## 3. Consolidated mandatory closure findings

If Arthur elects another direct remediation, a Review 0008 candidate must:

1. make the lossy-header result schema total with an exact unavailable media
   arm and exact-null rate projection/count rules;
2. add a block-only foreign-valid-target-claim evidence, mutation-prefix, and
   terminal path for the losing plan without promoting the foreign claim to its
   lifecycle predecessor;
3. make the target-evidence union exclusive by binding the complete target-
   consumption path set and prescribing canonical precedence when artifacts
   coexist;
4. make the target-inventory-store-failure capsule standalone and acyclic,
   retaining exact state/byte commitments for both the target-claim and target-
   inventory paths without requiring itself as target evidence;
5. define honest semantics for total local evidence-store failure: either one
   durable atomic target guard exists and consumes the target, or no durable
   claim exists and only the plan/authorization is consumed; a process-local
   diagnostic cannot prove permanent cross-session target consumption;
6. allow later read-only reconciliation to select a valid
   `mutation_prefix_inventory_store_failed` capsule;
7. retain independent admission and result path states plus chain-mismatch
   reasons in the mutation-inventory failure capsule and terminal inventory;
   and
8. make `pre_admission_artifact_unusable` and
   `mutation_chain_artifact_unusable` disjoint, for example by reserving the
   first for result-path absent and giving the chain-invalid arm precedence
   whenever any later artifact is non-absent.

These corrections must remain additive to frozen Stage 21A and Stage 21B and
must not widen credentials, live targets, mutation count, retry, repository
scope, or production authority.

## 4. Governed alternatives

These alternatives are proposals only and carry no authority:

1. **Split Stage 21C — recommended.** Freeze a smaller 21C-readiness protocol
   that produces exact-head, protection, review, and human-authorization
   evidence but performs no mutation. A human performs the normal protected
   GitHub merge; CONCLAVE observes and reconciles it read-only. Defer adapter-
   issued merge to a later protocol after the durable coordinator exists. This
   requires checking whether the frozen Increment 21 master needs an erratum.
2. **One more bounded Review 0008 remediation.** Keep the live single-send
   design, but replace the layered target inventory with one atomic target-
   guard rule and close all eight findings above before another full review.
   This preserves the intended capability but carries the highest immediate
   review and implementation complexity.
3. **Transactional coordinator foundation.** Pause 21C and first specify a
   cross-platform transactional, append-only coordination store for target
   guards and terminal evidence. Resume live merge only after that foundation
   passes its own protocol and conformance review. This is strongest for future
   multi-process KOS use but is a new increment, not a small remediation.

Freezing the failed candidate or accepting unrecorded evidence gaps is not a
governed alternative.

## 5. Review boundary

This review rejects only the exact candidate identified in §1. It grants no
authority to remediate, freeze, implement, access credentials, create or
install a GitHub App, call a live endpoint, change a repository, commit, push,
create a pull request, merge, alter protection, deploy, use production, change
KOS or IDM, sign, allocate identity, or activate membership.

The next action requires Arthur's explicit choice among bounded remediation,
scope split, or coordinator-foundation protocol work. Reviews 0001 through
0007 remain immutable historical records.
