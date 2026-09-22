# CONCLAVE Stage 21C — Factual Profile Adoption and Baseline Supersession Record

Status: DRAFT PREPARED FOR ARTHUR / NOT ISSUED / NO EFFECT

Drafted: 2026-09-21 by Claude (Claude Code session) at Arthur's direction
(CR4 option A); revised the same day for Council review 0003 findings CR16 and
N3-N5. This draft has no governing effect. It takes effect only as §9 states.
Until then every instrument named below keeps its full current effect.

## 1. Purpose

Arthur's merged freeze records select the Stage 21C implementation baseline.
The factual PR assistant profile replaces that baseline, but a protocol
candidate cannot withdraw the effect of Arthur's own freeze acts. This record is
the authority act that does so. It is narrow: it withdraws **baseline
selection** only, to the extent listed in §4, and leaves every other retained
control in force.

Division of instruments:

- the factual candidate's §2 governs the frozen **documents**: the Increment 21
  master protocol, Erratum 0001, Stage 21A, and the readiness and collection
  profiles;
- this record governs Arthur's merged **freeze records**, which select among
  those documents.

Neither instrument restates the other's rules. Where a freeze record retained
below describes the effect of a frozen document, that description is subject to
the candidate's §2 for the document itself. The candidate identifies this record
by path; this record binds the candidate by exact hash (§2). That is the only hash
binding between the two, and it runs in one direction.

## 2. Adopted object

| Field | Value |
|---|---|
| File | `INCREMENT-21C-FACTUAL-PR-ASSISTANT-PROTOCOL.md` |
| SHA-256 | `<BIND AT ISSUANCE>` |
| Git blob | `<BIND AT ISSUANCE>` |
| Accepted Council review | `<BIND AT ISSUANCE: file, SHA-256, verdict>` |

The values must be those of the exact bytes that received the Council review
Arthur accepts in §9. Any other bytes are outside this record. This record
creates no effect for any candidate earlier or later than the bound one.

## 3. Instruments affected

All three are merged on protected `main` and are present, byte-identical, at
local base `154394c570a9919fc00b7c00779f565f742508e2`.

| Record | SHA-256 | Git blob |
|---|---|---|
| `INCREMENT-21C-PROTOCOL-FREEZE-RECORD.md` | `7f01b8bd9237c2fdd389fa6882291803a0d4ee4b483b5cdfb4e3f5a1d7b33e4b` | `077759f4960eace30fb33da7afbf5a798ea30676` |
| `INCREMENT-21-ERRATUM-0001-FREEZE-RECORD.md` | `d336f9fc98d424bda3907f864060967d66a8c1c417ee09892a557a63e44051b3` | `bf8024cdb3c17673f34716d7bf40cd23fde2740d` |
| `INCREMENT-21C-CONTROL-ATTESTATION-COLLECTION-PROTOCOL-FREEZE-RECORD.md` | `fb6a785fb600bb0860bb47347056a4aceec396266dc8fc9757b623c9951712d7` | `8bfc70d717dd58eb99da1bb787634a876f56a6ad` |

None of them is edited. This record supplies a later disposition for each, in
the same manner each of them supplied a later disposition for its own frozen
object without changing that object's bytes.

## 4. Supersession, clause by clause

### 4.1 Stage 21C protocol freeze record (`7f01b8bd…`)

- **§5, first sentence** — "The frozen replacement Stage 21C protocol is the
  selected implementation baseline for any later separately authorized Stage
  21C work." Superseded. `INCREMENT-21C-READINESS-AND-HUMAN-MERGE-OBSERVATION.md`
  (`d3701754…`) is no longer the selected baseline. The adopted object in §2 is.
- **§5 items 2, 3, 4, 5 and 7** — deterministic exact-head readiness reduction;
  independently governed no-bypass and action-spanning control attestations;
  separately authored human-only merge-authorization evidence; a complete stop
  before the external human action; factual reconciliation. Superseded as
  requirements of Stage 21C. Item 5 described the readiness profile's pre-action
  phase boundary; the adopted object has no pre-action phase, and an initial
  report may be taken before or after a merge. Its substance — CONCLAVE causes no
  human action — is retained through the closing paragraph below.
- **§5 items 1 and 6** — retained, each satisfied by a named clause of the
  adopted object:
  - item 1, bounded Stage 21A read-only observations and single-operation
    authorizations: adopted object §§4.1 and 4.6 (fixed read-only plan; one
    externally supplied authorization and unused attempt digest per operation);
  - item 6, separately authorized read-only post-action observation: adopted
    object §3 (`purpose: post_action` requires a separate request bound to a
    prior initial report).
- **§5, closing paragraph** — the no-merge-credential, no-mutation-endpoint,
  no-GraphQL, no-generic-request and no-authority-to-cause-action sentence is
  **retained in full**. The list of instruments that "together establish the
  current governance state" is amended by adding this record and the adopted
  object; `d3701754…` remains in that list as frozen, preserved and unselected.
- **§§1-4, 6-8** — unaffected.

### 4.2 Erratum 0001 freeze record (`d336f9fc…`)

- **§4 item 1** — "corrected Stage 21C is limited to read-only exact-head
  readiness, bounded human-authorization evidence, post-action observation, and
  reconciliation." Superseded and replaced by: Stage 21C is limited to the
  factual observation defined by the adopted object.
- **§4 items 2 and 3** — the human merge as a direct action outside CONCLAVE; no
  merge permission, write credential, mutation lease, merge endpoint, send point,
  retry path, merge receipt or hidden mutation route. **Retained in full.**
- **§4 items 4 and 5** — the erratum's narrow supersession of master clauses, and
  the preservation of Stage 21A, 21B, 21B Erratum 0001, 21D and v0.8.0. Retained
  as accurate statements of what Erratum 0001 itself did. They do not cap later
  instruments: the adopted object's §2 rule 2 additionally governs master text,
  and its §2 rule 4 gives the Stage 21A clauses it names additive precedence for
  the factual profile only.
- **§6, "Any later replacement must conform to this frozen erratum"** —
  retained, read as conformance with the erratum as amended by the adopted
  object's §2 rule 3. The adopted object conforms to every erratum clause that
  rule 3 retains, including the §§7 and 14 no-mutation boundary. The same
  sentence's requirement of a fresh five-seat exact-draft review, freeze, and
  separate implementation authority is **retained in full**.
- **§§1-3, 5, 7** — unaffected.

### 4.3 Control-attestation collection protocol freeze record (`fb6a785f…`)

- **§5, first sentence** — the collection protocol (`6ea468c1…`) as "the
  selected collection-procedure baseline eligible to be named later by an exact
  Arthur-issued `control_attestor` trust authorization." Superseded. The adopted
  object uses no control attestor, so the collection protocol is not selected
  for Stage 21C and no such trust authorization can name it under this profile.
- **§5 items 1-10 and its closing sentence** — unaffected as a description of
  the frozen collection procedure, which is unselected, not rescinded.
- **§2** — subordination of the collection protocol to `d3701754…`. Unaffected
  as a statement about those two frozen documents. It gives neither any selected
  status after this record.
- **§§1, 3, 4, 6, 7, 8, 9** — unaffected.

## 5. Status of the unselected instruments

`d3701754…` and `6ea468c1…` are **not historical drafts**. Each stays frozen,
Council-approved, merged, and preserved byte-for-byte. After this record takes
effect each is *unselected*: no Stage 21C implementation or trust authorization
may rely on either as its baseline. Selecting either again requires a new
Arthur-issued record naming it by exact hash. Nothing in this record or in the
adopted object rescinds, deprecates or edits them.

## 6. What this record does not change

- The frozen Increment 21 master protocol, Erratum 0001, Stage 21A, and both
  unselected profiles remain byte-identical. Supersession or additive precedence
  over their **text** is governed solely by the adopted object's §2, not by this
  record.
- Stage 21A remains byte-identical; the clauses named in the adopted object's
  §2 rule 4 receive additive precedence for the factual profile only, and every
  other Stage 21A clause is unchanged.
- Stage 21B, Stage 21B Erratum 0001, Stage 21D, v0.8.0, and all accepted
  evidence remain unchanged.
- Stage 21A's signed credential-provider lease verification and key pinning
  remain in full.
- All earlier Council reviews, failed candidates, and freeze records remain
  immutable historical evidence.

## 7. Authority boundary

Issuing this record freezes and adopts the bound object only. It does not
authorize:

- a commit, push, pull request, merge, or branch-protection change;
- an administrator exception;
- Stage 21C implementation or any runtime or test change;
- credential access, GitHub App creation or installation, or token minting;
- a live GitHub adapter operation or any repository mutation;
- Stage 21D, deployment or production use;
- KOS or IDM changes; or
- signing, identity allocation or membership activation.

Each needs its own separately named authority.

## 8. Next governed gate after issuance

Authorization naming the bounded governance payload (the adopted object, its
accepted Council review, this record, and a reconciled CPS) and its destination
for commit and publication. Implementation authority follows only after that
payload is incorporated through the governed publication process.

## 9. Arthur decision

To be completed by Arthur only.

This record takes effect only when `decision` is ISSUE and every other field is
bound to a concrete value. A completed DECLINE, or any unbound field, gives it no
effect, and every instrument in §3 then keeps its full current effect.

The issued record may differ from the reviewed draft only in: the Status line,
the §2 bound values, and the JSON values in this §9. `reviewed_draft_sha256` binds the exact
draft the Council reviewed; any other difference means the issued record was not
reviewed.

```json
{
  "arthur_decision": {
    "decision": "<ISSUE | DECLINE>",
    "date": "<YYYY-MM-DD>",
    "adopted_object_sha256": "<must equal §2>",
    "accepted_council_review": "<file and SHA-256>",
    "reviewed_draft_sha256": "<SHA-256 of the draft this Council reviewed>",
    "council_standard_accepted": "<e.g. five same-provider seats / five distinct providers>"
  }
}
```

Arthur determined `council_standard_accepted` on 2026-09-21 as "five
same-provider seats acceptable"
(`INCREMENT-21C-FACTUAL-PROFILE-ARTHUR-DECISION-0001.md`).
