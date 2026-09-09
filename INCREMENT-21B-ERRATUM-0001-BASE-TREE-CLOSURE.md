# CONCLAVE Stage 21B Erratum 0001 — Verifiable Base-Tree Closure

## Status

Correction candidate · Council review required · not frozen · local only

This erratum corrects one demonstrated implementability defect in the frozen
Stage 21B protocol. It does not rewrite or replace the historical frozen
artifact. Once reviewed and frozen, this erratum is an additive controlling
instrument and supersedes only the clauses identified in §2.

It grants no implementation, credential, network, publication, merge,
deployment, production, KOS, IDM, signing, identity, or membership authority.

## 1. Demonstrated defect

The frozen protocol supplies the base commit OID and base root-tree OID, then
requires CONCLAVE to calculate the final proposal tree OID locally before
publication. It does not supply the base tree entries or affected ancestor
subtrees from which the final canonical Git tree bytes can be reconstructed.

A Git tree OID is the hash of its complete canonical tree-object bytes. It
cannot be derived from a prior tree OID plus a patch list. Consequently the
requirements to use GitHub's `base_tree` overlay and independently reproduce
the returned final tree OID cannot both be implemented from the frozen inputs.

This is a protocol defect, not a runtime defect. No Stage 21B runtime code was
changed before detecting it.

## 2. Narrow supersession

Once frozen, this erratum supersedes only:

- Stage 21B §4 item 6, by adding the exact base-tree-closure record defined
  here to the governing input chain immediately after the base observation;
- Stage 21B §5, by binding that closure into the proposal manifest and using
  it to calculate the proposal tree and commit OIDs;
- Stage 21B §§6–7, by adding the closure reference/hash and closure-source
  observation reference/hash to the authorization, plan, attempt preimage,
  generic intent, publication intent, and attempt claim;
- Stage 21B §9, by defining the only permitted local tree reconstruction;
- Stage 21B §12, by binding the closure into the terminal receipt, capsule,
  reconciliation records, and ledger only through its content hash; and
- Stage 21B §14, by adding the deterministic evidence in §11 below.

The Stage 21B credential-bearing publication sequence, its `F + 4` mutation
limit, `F + 4` identity rechecks, six supporting reads, `2F + 14` total request
limit, ten-request reserve, zero retry rule, endpoint exclusions, authority
effects, and all other frozen boundaries remain unchanged.

## 3. Pre-publication read-only source operation

The closure is derived before proposal authorization through one separately
authorized Stage 21A-compatible read-only operation:

`git_tree_recursive.get`

- Method: `GET`
- Fixed route: `/repos/{owner}/{repo}/git/trees/{tree_sha}`
- Fixed query: exactly `recursive=1`
- Accepted status: exactly `200`
- Permission: Contents read
- Network requests: exactly one; no pagination and no retry
- Input `{tree_sha}`: exact base root-tree OID from the accepted base
  observation

The repository profile must explicitly admit this operation. The request uses
the frozen Stage 21A origin, API version, authentication, TLS, proxy refusal,
redirect refusal, bounded reader, per-dispatch lease, immutable evidence, and
safe-diagnostic rules. It is not part of the later credential-bearing
publication request budget.

The response projection retains only:

- returned root-tree OID;
- `truncated`, which must be exactly `false`; and
- bounded entries containing NFC repository-relative path, canonical Git
  mode, type, and object OID.

Names, URLs, sizes, response text, headers outside the bounded rate projection,
and unknown fields are ignored rather than retained. Duplicate paths, invalid
UTF-8 after JSON decoding, non-NFC paths, ambiguous path forms, unsupported
modes/types, malformed OIDs, an unexpected root OID, or `truncated:true` fail
the observation. A failed or incomplete observation cannot produce a closure.

## 4. Hard closure limits

One source observation and closure are bounded by:

- one repository, base commit, and base root tree;
- at most 100,000 projected entries;
- at most 7 MiB accepted response bytes before parsing;
- at most 8 MiB canonical closure bytes;
- at most 32 path segments and 512 NFC UTF-8 bytes per path;
- at most 256 bytes per individual path segment; and
- exactly the repository object format pinned by the repository profile.

Exceeding any limit fails before proposal authorization. The adapter does not
fall back to a partial closure, a non-recursive walk, GraphQL, Git smart HTTP,
a local checkout, a Git executable, or caller-supplied tree data.

## 5. `github-base-tree-closure/0.1.0`

The closure is a closed, canonical, immutable, content-hashed durable record.
It contains only:

- closure ID and creation time;
- frozen Increment 21, Stage 21A, Stage 21B, and this erratum hashes;
- repository/API-profile references and hashes;
- repository and account numeric IDs;
- exact base-observation reference/hash;
- exact `git_tree_recursive.get` authorization, intent, claim, lease-evidence,
  and successful observation references/hashes;
- exact base ref, base commit OID, and base root-tree OID;
- exact repository object format;
- `source_complete:true`, `source_truncated:false`;
- sorted projected entries from §3;
- entry count and canonical byte count;
- recomputed base root-tree OID; and
- authority, decision, membership, approval, merge, deployment, and
  production effects all `none` or false.

The common Stage 21A/21B durable-record invariant applies. The closure filename
is derived only from its safe closure ID. Equal-content idempotency is allowed;
unequal existing content fails and preserves the existing bytes.

## 6. Permitted base entry forms

The closure admits the Git tree forms necessary to reproduce an existing base:

- `040000 tree`;
- `100644 blob`;
- `100755 blob`;
- `120000 blob`; and
- `160000 commit`.

These forms describe factual base state only. Stage 21B proposals still create
or replace regular `100644 blob` entries only. They cannot create executables,
symlinks, submodules, trees as proposal entries, deletions, or renames.

Every path is canonical and unique. A tree entry must exist for every directory
that has descendants. A non-tree path cannot have descendants. Every entry's
OID length must match the pinned object format.

## 7. Independent closure verification

Before sealing the closure, CONCLAVE reconstructs every base tree bottom-up:

1. group entries by their immediate parent path;
2. encode each direct entry as canonical Git tree bytes:
   `<mode-as-Git-text> SP <basename-UTF8> NUL <raw-object-id-bytes>`;
3. sort direct entries by Git tree ordering, treating a tree name as if it had
   a trailing `/` for comparison;
4. hash `tree <payload-byte-count> NUL <payload>` using the repository's
   pinned Git object format;
5. require each reconstructed subtree OID to equal the tree OID carried by its
   parent entry; and
6. require the reconstructed root OID to equal both the source observation's
   returned root OID and the accepted base observation's root-tree OID.

Missing parent trees, unreferenced orphan entries, duplicate basenames,
ordering ambiguity, cycles, impossible type/mode pairs, or any OID mismatch
fails before the closure is stored.

## 8. Proposal tree reconstruction

Before credential resolution for publication, CONCLAVE:

1. reopens and verifies the immutable closure and every predecessor hash;
2. verifies each proposal artifact once under the frozen path and byte rules;
3. replaces or inserts only the proposal's `100644 blob` entries in an
   in-memory copy of the verified base tree graph;
4. creates missing directory nodes only where required by an authorized
   proposal path, refusing a collision with any existing non-tree entry;
5. recalculates each affected tree bottom-up using §7;
6. requires all unaffected subtree OIDs to remain exactly those in the
   verified closure;
7. calculates the final root-tree OID; and
8. calculates the proposal commit OID from the final tree OID, exact sole
   parent, equal author/committer identity, exact timestamps, and exact message.

The final root-tree and commit OIDs are bound into the manifest and all
downstream records already required by Stage 21B. The GitHub create-tree
request remains the sorted proposal path/mode/type/blob-OID overlay with
`base_tree` equal to the verified base root-tree OID. The returned tree and
commit OIDs must equal the locally calculated values before ref creation.

No closure entry, proposal byte, Git object body, tree graph, or full path is
written to the ledger.

## 9. Freshness and drift

The closure source observation and base observation must identify the same
repository, account, base ref, base commit, base root tree, object format, and
profiles. Their observation times must fall within one bounded preparation
window of at most 15 minutes.

The existing same-transaction base-ref check immediately before ref creation
still proves that the base ref equals the authorized base commit. Any drift
stops before ref creation. The immutable closure is not refreshed, amended, or
silently replaced during publication.

## 10. Failure and rollback

Closure acquisition and proposal calculation are read-only preparation. Any
failure produces no publication authorization, credential resolution, or
mutation. Retained successful observations and closures remain factual
evidence and are never amended or deleted.

After mutation begins, the frozen Stage 21B ambiguity, receipt, reconciliation,
and no-rollback rules continue unchanged. This erratum creates no cleanup or
recovery mutation.

## 11. Required deterministic evidence

Tests must prove:

- SHA-1 and SHA-256 canonical tree vectors, including empty, nested,
  executable, symlink, and submodule base entries;
- Git tree ordering at file/tree prefix boundaries and non-ASCII NFC names;
- complete bottom-up reproduction of every supplied base subtree and root;
- proposal replacement and insertion at root and nested paths;
- unaffected subtree OIDs remain unchanged;
- final tree and commit OIDs equal independent Git fixture vectors;
- missing parent, orphan, duplicate, collision, invalid mode/type, wrong OID,
  wrong object format, wrong base root, truncation, oversize, depth, segment,
  Unicode, and ordering failures are fail-closed;
- every closure reference/hash and source-observation binding is indispensable;
- mutation of any closure or proposal byte fails before credential resolution;
- source-operation permission and endpoint closure, exactly one request, zero
  retry, fixed query, bounded response, and external-network denial;
- installed wheel and sdist contain no fixture closure, repository content,
  proposal content, response cassette, test constructor, credential, token, or
  private key; and
- Windows/Python 3.12, Ubuntu/Python 3.12 and 3.13, and macOS/Python 3.12 pass
  with zero erratum or Stage 21B failures, errors, skips, or xfails.

Every precondition failure asserts zero publication credential resolutions and
zero publication transport calls.

## 12. Council review questions

Each reviewer independently verifies the exact SHA-256 and Git blob and returns
`PASS_EXACT_DRAFT` or `BLOCK`:

1. Governance and authority: is the supersession narrow, non-retroactive, and
   free of new publication authority?
2. Security and credentials: are closure provenance, permissions, limits,
   substitution resistance, and secret/network boundaries fail-closed?
3. Git correctness: can the specified closure and ordering reproduce exact
   base, proposal-tree, and commit OIDs for both admitted object formats?
4. Evidence and schemas: is the new record acyclic, immutable, cross-bound,
   closed, and sufficient without storing raw content in the ledger?
5. Cross-platform testability: are all byte, path, durability, packaging,
   fault, and network claims deterministically testable on the required matrix?

Any byte correction voids all earlier verdicts and requires a fresh 5/5 exact
review.

## 13. Current disposition

The demonstrated tree-closure defect is specified for correction. This draft
is not frozen, committed, pushed, or operational. Stage 21B implementation
remains paused pending fresh 5/5 Council review and explicit Arthur freeze of
this exact erratum.
