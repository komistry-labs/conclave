# CONCLAVE Stage 21C — Control-Attestation Collection Protocol Publication Closeout 0001

## Status

PR #24 publication reconciled · frozen governance present on protected `main` ·
independent exact-head review preserved · post-merge CI and artifacts verified ·
this record prepared on the separately governed closeout branch · not
implemented or used

This record supplies the post-merge disposition for the immutable Stage 21C
Control-Attestation Collection Protocol and its freeze record. It supersedes
only their earlier publication-state statements. Its own later Git publication
state is determined from repository history and the protected branch, not from
a mutable status assertion inside this file. It does not alter the frozen
objects' bytes, resolve an implementation design, or grant implementation or
operational authority.

## 1. Governed objects

The frozen collection protocol remains:

- file:
  `INCREMENT-21C-CONTROL-ATTESTATION-COLLECTION-PROTOCOL.md`;
- SHA-256:
  `6ea468c1cdd3a4ac0befecd3ffa3c2c26cfb51218902fb3af20366e4dbbb91c2`;
- Git blob: `f51fb51ed85e93b12ad6ecd74d44b56963b17faa`;
- size: `83,038` bytes; and
- line form: `1,624` LF terminators, zero CR bytes, final LF present, no BOM.

Its freeze record remains:

- file:
  `INCREMENT-21C-CONTROL-ATTESTATION-COLLECTION-PROTOCOL-FREEZE-RECORD.md`;
- SHA-256:
  `fb6a785fb600bb0860bb47347056a4aceec396266dc8fc9757b623c9951712d7`;
- Git blob: `8bfc70d717dd58eb99da1bb787634a876f56a6ad`;
- size: `6,632` bytes; and
- line form: `153` LF terminators, zero CR bytes, final LF present, no BOM.

The governing replacement Stage 21C protocol remains:

- file: `INCREMENT-21C-READINESS-AND-HUMAN-MERGE-OBSERVATION.md`;
- SHA-256:
  `d3701754c7ab782835bc92db07c055509e415a69765373ed5cd30f250164b257`;
- Git blob: `6553d2371c534e0c8159aa9a8ddd2fec964dc208`; and
- freeze record: `INCREMENT-21C-PROTOCOL-FREEZE-RECORD.md`.

The collection protocol remains subordinate to that governing baseline. It
supplies factual evidence only and creates no authority to decide readiness,
authorize or perform a human merge, sign an attestation, or execute an action.

## 2. Independent review and Arthur decision

The independent review record was supplied as
`CONCLAVE-PR24-INDEPENDENT-EXACT-HEAD-REVIEW.md` and accepted by Arthur at
SHA-256:

`d88257c5a5e1b62641483943c765df08c3c090ece3d9a57504263a370d22a175`

The review returned `PASS_EXACT_HEAD` for only:

`cae5eacbc85b0bea7fba384c7aaf685b8814b95b`

It was preserved in the PR #24 record at:

`https://github.com/komistry-labs/conclave/pull/24#issuecomment-5679673531`

The reviewer independently recomputed the protocol and freeze-record object
identities, verified the one-commit two-file diff, found no executable or
operational change, and found no merge blocker. Arthur accepted that verdict
and separately authorized the exact-head merge and bounded review-count
exception recorded below.

## 3. Pull request and merge

- pull request: `#24`;
- base: `main`;
- base commit:
  `ee4c196042dbae990530a8367c2352137a37dcbc`;
- exact accepted head:
  `cae5eacbc85b0bea7fba384c7aaf685b8814b95b`;
- accepted head tree:
  `31a3d9b4bbaa955934d8938b857326503c42cfa2`;
- merge commit:
  `f78d656e4b6c03d55d3f385c7d310399a3e45879`;
- merge tree:
  `31a3d9b4bbaa955934d8938b857326503c42cfa2`;
- ordered parents:
  `[ee4c196042dbae990530a8367c2352137a37dcbc,
  cae5eacbc85b0bea7fba384c7aaf685b8814b95b]`;
- merge actor: GitHub login `komistry-dev`;
- merged at: `2026-09-15T11:49:58Z`; and
- GitHub merge-commit verification: valid signature.

The merge tree equals the accepted head tree. Protected `main` therefore
advanced through one normal two-parent merge that introduced exactly the two
governance files in §1 and no additional content.

## 4. Branch-protection exception and restoration

Arthur authorized a one-time change of only
`required_approving_review_count` from `1` to `0` solely for the exact PR #24
merge. No other merge was performed during the exception window. The setting
was restored to `1` immediately after the merge attempt.

The complete normalized protection snapshot before the exception and after
restoration was identical at SHA-256:

`2aa89863ec898a17d217f31894d627cf797ecf4ae4835f91bb4670a6202582f7`

The exact compact UTF-8 JSON hashed for both snapshots was:

```json
{"strict":true,"contexts":["test (windows-latest, 3.12)","test (ubuntu-latest, 3.13)","test (macos-latest, 3.12)"],"checks":[{"context":"test (windows-latest, 3.12)","app_id":15368},{"context":"test (ubuntu-latest, 3.13)","app_id":15368},{"context":"test (macos-latest, 3.12)","app_id":15368}],"dismiss_stale_reviews":true,"require_code_owner_reviews":false,"require_last_push_approval":false,"required_approving_review_count":1,"enforce_admins":true,"required_linear_history":false,"allow_force_pushes":false,"allow_deletions":false,"block_creations":false,"required_conversation_resolution":true,"lock_branch":false,"allow_fork_syncing":false,"required_signatures":false}
```

Strict required checks, App-bound required contexts, stale-review dismissal,
administrator enforcement, conversation-resolution enforcement, force-push
prohibition, and deletion prohibition remain unchanged. Code-owner review,
last-push approval, and required signatures remain disabled as before. No
protection gap remains.

## 5. Post-merge acceptance

GitHub Actions run `34965432845` executed on the exact merge commit
`f78d656e4b6c03d55d3f385c7d310399a3e45879` and completed with conclusion
`success`.

All matrix jobs passed:

1. Windows/Python 3.12;
2. Ubuntu/Python 3.12;
3. Ubuntu/Python 3.13; and
4. macOS/Python 3.12.

Each job completed dependency acquisition, offline installation, tests, exact
package construction, clean installed-wheel probing, evidence inventory and
scanning, and publication of secret-free conformance evidence.

Four unexpired artifacts were published:

| Artifact | SHA-256 digest |
|---|---|
| `conformance-windows-latest-py3.12` | `21801a87626f25ab081585897ec08d14f6e7397ac3b4ebd16115ad54054a7c24` |
| `conformance-macos-latest-py3.12` | `dbed983fa4826888694f8fe10d22875349b07ff8d02608c3ef3cfff3d37c0c74` |
| `conformance-ubuntu-latest-py3.13` | `22e6e61c0887f7e5b152faed58fe1399124772e6cebbea01aa844259f14d86d9` |
| `conformance-ubuntu-latest-py3.12` | `fcb12bcbc05ca3f9b703dbf243a47affb0ca84a8dd096b6d29c4645ce4ff8637` |

Run URL:

`https://github.com/komistry-labs/conclave/actions/runs/34965432845`

## 6. Preserved non-blocking findings

The independent review found no blocker but identified matters that remain
outside this immutable publication object:

1. the freeze record's drafting-time `local`, `uncommitted`, and `unpushed`
   statements are superseded by this closeout rather than edited;
2. the separate publication authority is evidenced by Arthur's later decision
   and this closeout, not by the frozen record itself;
3. a cycle may permit as many as 96 logical reads while the bundle permits only
   96 source-envelope references and Stage 21A sources add three readiness or
   six action-interval envelopes;
4. the reviewed head commit was unsigned, while the GitHub-created merge commit
   carries a valid GitHub signature and the continuing protection baseline does
   not require signed commits; and
5. external GitHub platform facts, schema assumptions, canonical-byte fixtures,
   replay behavior, and cross-platform locking remain implementation-review and
   acceptance obligations.

The third finding resolves only in the fail-closed direction under the frozen
protocol: exceeding an array ceiling fails rather than truncates or fabricates
evidence. It nevertheless creates an avoidable internal capacity mismatch.

For any later implementation candidate under these exact frozen bytes, its
reviewed implementation manifest and executable limits shall constrain the
derived logical-read budget to no more than `90` for both `readiness` and
`action_interval` cycles. This keeps the worst-case source-envelope count at or
below `96`. Raising the source-envelope array ceiling instead requires a future
reviewed protocol revision; it cannot be achieved by interpreting or altering
the frozen object.

This recorded constraint is a conservative implementation prerequisite. It is
not implementation authorization and does not amend the frozen protocol.

## 7. Reconciled disposition and next governed gate

The exact collection protocol and freeze record in §1 are now present on
protected `main`. They are the selected collection-procedure governance
baseline eligible for a later, separately authorized implementation candidate.
They have not been implemented, deployed, trusted, signed, or used.

This record and the reconciled CPS were prepared on branch
`docs/increment-21c-collection-publication-closeout` for publication through
PR #25. The live PR head, checks, review disposition, merge state, and protected
`main` head must be verified from GitHub; this record does not self-attest its
own publication.

After successful closeout publication, the next substantive Stage 21C gate is
separate authority for the offline two-key ceremony-plan protocol. Runtime or
external-collector implementation remains later in the frozen §20 sequence and
requires its own explicitly bounded authority. Any such development must remain
fixture- and loopback-only unless a further decision separately authorizes
credentials or live GitHub collection.

This closeout does not authorize implementation, runtime or test changes,
credentials, a GitHub App, token minting, key generation, signing, trust-store
deployment, live GitHub adapter operations, repository mutation, deployment,
production use, KOS or IDM changes, identity allocation, or membership
activation.
