# CONCLAVE Increment 21 Erratum 0001 — Stage 21C Human-Merge Split

## Status

Draft correction candidate · Council review required · not frozen · local only

This erratum candidate responds to Arthur's selection of Governed Alternative
1 in Stage 21C Council Review 0007. It does not edit or replace the historical
frozen Increment 21 master protocol. If and only if this exact erratum is later
reviewed, frozen, and applied, it becomes an additive controlling instrument
and supersedes only the master-protocol clauses identified in §3.

This draft grants no implementation, credential, network, repository, merge,
commit, push, pull-request, deployment, production, KOS, IDM, signing,
identity, or membership authority.

## 1. Governing inputs

This candidate is bound to:

- frozen master protocol:
  `INCREMENT-21-GITHUB-REPOSITORY-AND-PR-ADAPTER.md`;
- master SHA-256:
  `89a05211a4323db2e79d2854952b24ce033c71f357430c7ac839457ff0878d75`;
- master Git blob:
  `83d8fb2cabb9d343b6a8d089d920d25dcd8c5728`;
- rejected Stage 21C Review 0007 candidate SHA-256:
  `2373bb9dbb96146c8b22d868a284ea0be54015720c18ef80406c2633f9a7d6d4`;
- rejected Stage 21C Review 0007 candidate Git blob:
  `84dbb36abd719bc1c60f14ef4c541b9f6e2880fc`; and
- immutable review record:
  `INCREMENT-21C-COUNCIL-REVIEW-0007.md`.

Council Review 0007 returned `1/5 PASS_EXACT_DRAFT / 4/5 FAIL_EXACT_DRAFT`.
The failed candidate is preserved as historical evidence and cannot be frozen
or implemented.

## 2. Demonstrated design pressure and adopted correction

Seven review rounds showed that safely issuing a GitHub merge mutation from
CONCLAVE requires durable cross-process target consumption, exclusive and
total partial-write state machines, restart-safe mutation accounting, and
standalone reconciliation evidence. Those requirements exceed the bounded
verification purpose now selected for Stage 21C.

The adopted correction separates the responsibilities:

1. CONCLAVE performs read-only observation and deterministic exact-head merge-
   readiness evaluation.
2. A configured human principal may author an exact, expiring authorization
   for that same human principal to perform one normal protected GitHub merge.
3. The human, outside CONCLAVE and using GitHub's ordinary protected workflow,
   independently rechecks the exact head and performs or declines the merge.
4. CONCLAVE performs read-only post-action observation and reconciliation.

CONCLAVE does not send, queue, retry, schedule, or otherwise cause a merge.
The human authorization is evidence available to the human workflow; it is
not an operation authorization for CONCLAVE.

## 3. Narrow supersession

Once frozen and applied, this erratum supersedes only the following parts of
the frozen master protocol where they grant, imply, specify, test, or document
adapter-issued merge execution:

- §1 objective item 5;
- §4 Stage 21C;
- §5's Stage 21C merge-permission requirement and merge-specific credential
  causality, while leaving all Stage 21A and 21B authentication controls intact;
- §6's merge-operation authorization, merge-attempt, and merge-receipt
  reservations;
- §7's merge-specific mutation intent and transport requirements;
- §8 items 8 through 12;
- §9 threats that presuppose a CONCLAVE-issued merge request;
- §10 acceptance-evidence items 4, 6, 7, and 9 only to the extent that they
  presuppose a Stage 21C mutation, mutation credential, or mutation retry;
- §11's ambiguous-mutation and bad-merge rules only as applied to Stage 21C;
- §12 accepted decisions 5 and 6; and
- §13's synchronous merge-endpoint reference as a selected Increment 21
  implementation dependency.

All other frozen Increment 21 clauses remain controlling. This erratum does
not reopen or change Stage 21A, Stage 21B, Stage 21B Erratum 0001, Stage 21D,
the v0.8.0 baseline, or any accepted implementation evidence.

## 4. Replacement objective

Master §1 item 5 is replaced by:

> 5. prepare exact-head merge-readiness evidence for a separately authorized
> human action and factually observe and reconcile the resulting GitHub state,
> without CONCLAVE receiving merge permission or executing a merge.

The adapter remains an evidence and execution boundary for its authorized
read-only operations. It is not the merge actor, approver, or decision-maker.

## 5. Replacement Stage 21C

Master §4 Stage 21C is replaced in full by:

### 21C — exact-head readiness and human-merge observation

Observe and bind the exact repository, pull request, base ref and commit, head
ref and commit, required status contexts, review identities and freshness,
unresolved conversations, mergeability, protection and ruleset state, and any
head or base change. Produce one immutable readiness record with no authority
effect.

A `ready` result requires every frozen readiness precondition, including a
fresh and complete independently governed no-bypass attestation. A missing,
unknown, stale, conflicting, incomplete, or unverifiable input produces
`blocked` or `indeterminate`, never `ready`.

A configured human principal may separately author one immutable, expiring,
exact-head human-merge authorization. It names the repository numeric ID,
pull-request number, exact base, exact head commit, normal merge method,
required checks, accepted independent-review record, readiness-record hash,
expiry, and the human-governance instruction `maximum_human_attempts: 1`. That
limit constrains only the named human's authority. CONCLAVE does not observe,
enforce, count, or attest browser, CLI, or other external-client attempts, and
no readiness, observation, or reconciliation record may claim compliance with
the attempt count. The authorization permits only the named human to use
GitHub's ordinary protected workflow. It gives CONCLAVE no merge authority and
is not accepted by any CONCLAVE mutation interface.

Immediately before acting, the human remains responsible for confirming that
GitHub still displays the authorization-bound repository, PR, base, and exact
head and that continuing protections remain satisfied. Any drift invalidates
the readiness and authorization; the human must not merge and a fresh read-
only readiness cycle is required.

After the human action or declared non-action, CONCLAVE may perform a separately
authorized read-only observation. It records whether the PR remains open, was
merged, or is in an unknown or inconsistent state; the observed head, base,
merge commit, actor identity when supplied by the bounded projection, relevant
timestamps, and whether the observed result matches the prior readiness and
human authorization. Observation never retroactively authorizes an action.

If the human action is blocked, differs from the authorization, used a bypass,
or cannot be established from bounded evidence, CONCLAVE records the fact and
stops. It performs no retry, correction, settings change, or cleanup.

## 6. Authority and actor separation

The replacement Stage 21C has three non-interchangeable evidence classes:

1. **Readiness evidence** is CONCLAVE-produced factual analysis with
   `authority_effect: none` and `merge_authorized: false`.
2. **Human-merge authorization evidence** is authored by the configured human
   principal, authorizes only that human's direct GitHub action, and has
   `conclave_operation_authorized: false`.
3. **Post-action observation evidence** is CONCLAVE-produced factual evidence
   with no approval, authority, identity, membership, truth, deployment, or
   production effect.

No provider output, Council review, readiness result, GitHub review, green
check, mergeability field, authorization evidence, or post-action observation
can substitute for another class or grant CONCLAVE merge authority.

## 7. Permission and endpoint closure

The master §5 permission envelope is corrected as follows:

- Stage 21C receives no write, pull-request-write, contents-write, merge,
  administration-write, ruleset-write, or bypass permission.
- Stage 21C adds no credential class and no credential-bearing mutation lease.
- Every Stage 21C GitHub access is a separately authorized read-only operation
  admitted by the frozen Stage 21A endpoint table or by a later reviewed and
  frozen read-only Stage 21C extension.
- Administration-read remains permitted only under the master's existing
  endpoint-specific evidence rule. It cannot authorize or perform a mutation.
- `PUT /repos/{owner}/{repo}/pulls/{pull_number}/merge`, asynchronous merge,
  merge queues, auto-merge, branch update, review submission, conversation
  resolution, and repository-setting mutations are absent from every Stage
  21C endpoint and transport table.
- The runtime must have no method, coordinator branch, generic operation key,
  or caller-supplied escape capable of issuing a merge request.

The human's browser, GitHub CLI, or other directly controlled client is outside
the CONCLAVE adapter and credential-provider boundary. CONCLAVE does not
receive, proxy, store, log, or inspect the human's session or credential.

## 8. Revised immutable record reservations

Stage 21C may define only the following new durable record families at its own
exact protocol freeze:

- `github-merge-readiness/0.2.0` — exact bounded inputs, total deterministic
  result, reasons, expiry, and `authority_effect: none`;
- `github-ruleset-no-bypass-attestation/0.2.0` — independently governed,
  expiring evidence covering the actual human merge actor and every applicable
  repository and organization ruleset, while separately binding the read-only
  App and installation identities used by CONCLAVE;
- `github-human-merge-authorization-evidence/0.1.0` — the configured human's
  exact external authorization and its binding to readiness, with
  `conclave_operation_authorized: false`;
- `github-human-merge-observation/0.1.0` — bounded factual post-action GitHub
  state; and
- `github-human-merge-reconciliation/0.1.0` — deterministic comparison of the
  prior readiness, human authorization, and post-action observation.

The names `github-merge-authorization/0.1.0`,
`github-merge-attempt/0.1.0`, and `github-merge-receipt/0.1.0` are not selected
for Stage 21C implementation. Their frozen-master reservations remain
historical and may be reused only by a later, separately governed adapter-
issued merge protocol that defines compatibility or a version transition.

Every selected record is closed-schema, bounded, canonical, content-hashed,
immutable, stored under a hash-safe filename, and acyclically cross-bound.
Human authorization evidence is stored before it may be presented as current;
post-action records cannot be back-referenced from an earlier immutable object.

## 9. Readiness and observation lifecycle

The replacement Stage 21C lifecycle is:

1. validate immutable profiles and governing protocol hashes;
2. obtain separately authorized bounded read-only observations;
3. validate completeness, freshness, repository numeric identity, exact base
   and head, reviews, checks, conversations, mergeability, protection,
   rulesets, and the independent no-bypass attestation;
4. deterministically store `ready`, `blocked`, or `indeterminate` readiness;
5. optionally accept and validate separately authored human-merge authorization
   evidence without resolving a merge credential or making a network request;
6. stop and return control to the named human;
7. after a separately declared human outcome, optionally obtain new separately
   authorized read-only observations; and
8. store factual observation and reconciliation records.

There is no CONCLAVE mutation phase, send point, mutation counter, target-claim
store, mutation-prefix store, merge receipt, retry, or ambiguous network write.
Concurrent CONCLAVE processes may duplicate equal-content reads but cannot
compete to mutate the PR. Conflicting readiness or observation evidence remains
visible and produces `indeterminate` until resolved by fresh factual reads.

## 10. Replacement invariants

Master §8 items 8 through 12 are replaced by:

8. Readiness binds one repository numeric ID, PR number, exact base, and exact
   head. Any observed drift makes that readiness non-current.
9. A `ready` result requires the master's complete independently governed no-
   bypass evidence, revised to cover the actual human merge actor and every
   applicable repository and organization ruleset. Omitted or unverifiable
   bypass state fails closed. The GitHub App and installation identities remain
   bound to CONCLAVE's read-only observations but are not represented as the
   merge actor.
10. Human-merge authorization binds one exact current readiness record and
    grants authority only to the named human. CONCLAVE cannot consume it as a
    mutation authorization.
11. Post-action observation reports a successful matching merge only when the
    bounded GitHub evidence proves that the authorization-bound head was merged
    into the authorization-bound base with the permitted normal merge method
    and continuing controls. Otherwise the result is mismatched, blocked,
    absent, or indeterminate.
12. A mismatch or unknown outcome permits read-only reconciliation only. No
    CONCLAVE merge, repeat, rollback, settings change, or corrective mutation
    follows.

## 11. Threat and acceptance-evidence correction

Stage 21C acceptance evidence must prove at least:

- no Stage 21C endpoint, permission, credential lease, transport, generic
  operation key, or public runtime entry point can issue a merge mutation;
- readiness is total and deterministic for every admitted and corrupted input
  combination and fails closed on missing, unknown, stale, conflicting,
  over-broad, or mismatched evidence;
- head, base, repository, ruleset, review, check, conversation, authorization,
  actor, time, and method substitution are detected;
- the human authorization cannot be mistaken for a CONCLAVE operation
  authorization and cannot trigger credential resolution or network I/O;
- all readiness evidence expires and any head, base, review, check, protection,
  ruleset, or authorization drift requires a fresh cycle;
- post-action observation distinguishes matching merge, mismatched merge,
  still-open PR, blocked action, absent action, insufficient evidence, and
  inconsistent evidence without approval inference;
- a human bypass, administrator exception, non-normal merge method, different
  head, different base, or unproven actor never yields a conforming result;
- read-only reconciliation is idempotent, immutable, bounded, acyclic, and
  incapable of causing or retrying a mutation;
- logs, exceptions, evidence, packages, and test artifacts contain no human or
  App credential, session, cookie, token, private key, private response body,
  or unbounded user content;
- fixture and loopback tests prove zero external network and zero mutation;
  installed-wheel tests prove no hidden merge path exists; and
- Windows/Python 3.12, Ubuntu/Python 3.12 and 3.13, and macOS/Python 3.12 pass
  with no required security skip or xfail.

The former requirements to test merge-request construction, exactly-once
mutation sending, partial mutation-write durability, write-outcome ambiguity,
or merge-credential causality are removed from Stage 21C because the corrected
stage contains no merge mutation.

## 12. Failure, rollback, and operational boundary

Following a failed readiness evaluation, CONCLAVE must not accept, validate,
retain as current, or present any human authorization as usable. CONCLAVE
produces no operation authorization and performs no mutation. This rule does
not claim to prevent the human from authoring or retaining an external
authorization; such an authorization is non-current and unusable by CONCLAVE.
An invalid human authorization is retained only as bounded rejected evidence
when the later Stage 21C protocol expressly permits it; it never enables an
operation. A human-declared non-action ends the cycle without side effect.

A human-performed merge is external factual state. CONCLAVE cannot undo it.
Any mismatch requires the repository's governed corrective-change process and
new human authority. CONCLAVE performs no history rewrite, revert, branch
deletion, PR closure, review change, conversation resolution, or protection
change.

This erratum does not authorize a live exercise. Any later live observation
requires its own exact repository, permission, endpoint, credential-provider,
request-count, and evidence authorization under the then-frozen Stage 21C
protocol. KOS, IDM, CONCLAVE protected `main`, client, and production targets
remain excluded unless separately governed by later authority.

## 13. Superseded Arthur decisions

Master §12 decisions 5 and 6 are superseded only for Increment 21:

5. **Merge execution:** Stage 21C does not execute a merge. A configured human
   may perform one exact, normal protected merge outside CONCLAVE under a fresh
   human-only authorization after reviewing current readiness evidence.
6. **Merge method:** Stage 21C readiness and reconciliation recognize only a
   normal merge commit. Rebase, squash, auto-merge, queue submission, and method
   substitution are nonconforming. This recognition does not make CONCLAVE the
   merge actor.

The synchronous GitHub merge endpoint remains a factual reference for a future
protocol only. It is not a selected endpoint or dependency of corrected Stage
21C.

## 14. Deferred adapter-issued merge capability

Adapter-issued merge execution is outside corrected Increment 21. It may be
reconsidered only through a new master protocol after a separately governed,
cross-platform transactional coordination foundation demonstrates durable
target guards, total partial-write evidence, restart-safe accounting,
exclusive terminal states, and read-only reconciliation.

No identifier, version, schedule, implementation, or production commitment is
created for that future capability by this erratum.

## 15. Relationship to the rejected Stage 21C drafts

Stage 21C drafts and Council Reviews 0001 through 0007 remain immutable
historical evidence. None is incorporated by reference as an operative
protocol. Their merge-mutation state machines, credential-bearing mutation
path, and terminal mutation evidence must not be copied into the replacement
read-only Stage 21C merely to preserve sunk work.

The replacement Stage 21C protocol must be drafted afresh under this erratum
after this erratum itself receives a fresh 5/5 exact-draft Council pass and an
explicit Arthur freeze. A pass on this erratum does not freeze the later Stage
21C protocol or authorize implementation.

## 16. Council review questions

Each reviewer independently verifies the exact SHA-256 and Git blob and returns
`PASS_EXACT_DRAFT` or `FAIL_EXACT_DRAFT`:

1. Governance and authority: is the supersession narrow, explicit, non-
   retroactive, and incapable of granting CONCLAVE merge authority?
2. Security and credentials: are all merge permission, credential, endpoint,
   transport, retry, bypass, and hidden mutation paths closed?
3. GitHub correctness: can readiness and post-action observation honestly bind
   the exact head, base, human actor, normal merge result, protections, and
   drift without claiming atomic enforcement CONCLAVE does not possess?
4. Evidence and schemas: are the proposed record roles distinct, immutable,
   acyclic, total, and sufficient for a smaller replacement-stage protocol?
5. Cross-platform testability: can zero mutation, fail-closed readiness, human-
   authorization separation, and post-action reconciliation be demonstrated
   deterministically on the required matrix and installed package?

Any byte correction voids all earlier verdicts and requires a fresh 5/5 exact-
draft Council review.

## 17. Current disposition

Arthur selected the scope-split direction. The frozen Increment 21 master was
checked and requires this governed erratum because it explicitly authorizes a
Stage 21C merge permission, endpoint, intent, attempt, receipt, and execution.

This exact erratum remains a local draft. It is not reviewed, frozen, applied,
committed, pushed, or operational. The rejected Stage 21C candidate remains
rejected. No replacement Stage 21C protocol may be frozen or implemented until
this erratum passes fresh 5/5 exact-draft Council review and Arthur explicitly
freezes it.
