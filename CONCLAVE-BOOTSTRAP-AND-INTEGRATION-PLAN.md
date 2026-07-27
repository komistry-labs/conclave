# CONCLAVE — Bootstrap and Integration Plan

| Field | Value |
|---|---|
| Deliverable | CONCLAVE bootstrap and integration plan |
| Prepared by | Claude, advisory and implementation agent |
| Date | 27 July 2026 |
| Scope | **CONCLAVE only.** KOS is an input, not a design surface. |
| Repository state observed | `komistry-labs/KOS` @ `485f88f` |

---

## 0. Mandate acknowledgement

CONCLAVE is the assignment. Komistry OS is not.

My previous package overstepped in three specific ways, and I want them named rather than quietly dropped:

1. I recommended a canonical repository architecture. That selection is Arthur's, informed by Adrian/ChatGPT as institutional architect.
2. I produced a 47-row migration mapping proposing moves for every canonical file. Not mine to propose.
3. I offered a constitutional interpretation — whether `KOS-CONSTITUTION` denotes a distinct document or the aggregate of five ADRs. That is a constitutional question, and my having a view on it is not the same as my being entitled to advance one.

The underlying observations were sound and are retained below as **integration conditions**. The recommendations built on them are withdrawn.

There is a sharper version of this worth stating. The success criterion for CONCLAVE ends with *"without any model silently taking control of Komistry OS."* Over the preceding two exchanges I moved from setting up a Windows toolchain to proposing where every canonical file in KOS should live — each step locally reasonable, no step announced as a change of scope. That is the failure mode CONCLAVE is built to prevent, and it happened in conversation, at conversational speed, without anything that looked like a decision being made. It is a useful data point about what the tool needs to catch, and I would rather it be recorded than forgotten.

---

## 1. The governing design principle

> **CONCLAVE must not require KOS to be fixed before it can run.**

This is the load-bearing consequence of the mandate, and it changes the engineering.

If CONCLAVE only works against a clean, restructured, fully-governed repository, it is useless — the entire purpose is to help govern a repository that has real conditions: unresolved object types, competing lifecycle vocabularies, a Constitution question, paths that will move.

So every condition I found becomes a **CONCLAVE robustness requirement**, not a KOS remediation ticket:

| KOS condition | Wrong response | Correct response |
|---|---|---|
| Paths may move after a structure decision | wait for the decision | resolve objects by identity; discover paths at runtime |
| RA object type unassigned | assign one | manifest tolerates `null`; context compiler proceeds |
| Lifecycle vocabularies conflict | reconcile them | report the conflict; do not adjudicate |
| Constitution unresolved | author or substitute | fail closed; report precisely |
| CRLF working tree | normalise the repo | hash canonical bytes; be immune |

Each right-hand entry is a CONCLAVE feature. None requires KOS to change first.

---

## 2. A correction to my own earlier escalation

I led three exchanges ago with the claim that the CRLF condition was the highest-risk item in the setup. **Under canonical-byte hashing — which Arthur specified — it is not.**

```
content_hash = sha256( canonicalise( read_bytes(path) ) )
```

Canonicalisation strips CRLF before hashing. A CRLF working tree therefore produces the same hash as an LF one, on any platform. **CONCLAVE is immune to the condition I said was blocking.**

Arthur's correction dissolved the problem I was leading with. What remains is real but minor: a CRLF working tree produces noisy diffs and awkward PR review. That is a quality-of-life issue for KOS contributors, not a CONCLAVE dependency.

I am revising my own risk rating from **high** to **low**, and the recommendation in §A.1 is correspondingly narrower than what I proposed before.

---

# A. CONCLAVE engineering requirements

Requirements CONCLAVE must satisfy to operate against KOS as it actually is.

## A.1 Canonical-byte hashing — **required**

Hash canonical bytes, never working-tree bytes. Canonical form: UTF-8, no BOM, LF, exactly one trailing newline, no provider metadata. Trailing whitespace preserved — two trailing spaces are a hard line break in Markdown, and canonicalisation must be lossless with respect to meaning.

One implementation module, referenced by manifest generator, ledger writer, context compiler and tests. A second implementation is a second source of truth.

Delivers: platform independence; independence from Git (essential for the relay path, where files leave Git's control); immunity to the current CRLF condition.

**Recommendation to KOS, not a CONCLAVE dependency:** a `.gitattributes` pinning LF would reduce diff noise. Draft content is in the retained standard document. CONCLAVE does not wait on it.

## A.2 Identity indirection — **required, and the most important requirement here**

CONCLAVE resolves targets by canonical identity, never by hardcoded path:

```
canonical_id → manifest lookup → current path → section → content hash
```

ADR-0005 already mandates this: identity is independent of repository, name, and organisational placement.

**Consequence: the KOS structure decision stops blocking CONCLAVE.** If files move, manifests update and CONCLAVE keeps working. If the numbered scheme is adopted, or the current layout retained, or something else chosen — CONCLAVE is unaffected. Whoever decides, whenever they decide, however they decide.

This is the single design choice that separates CONCLAVE's schedule from KOS's governance schedule, and it is why §3's "do not choose or implement a restructure" costs nothing.

**No path may appear as a literal anywhere in CONCLAVE outside the manifest layer.** This should be enforced by a test, not by discipline.

## A.3 Discovery, not assumption — **required**

CONCLAVE inventories the repository at runtime. It does not assume `architecture/decisions/` or `docs/reasoning-architecture/` or any other path exists.

Inventory output: every tracked file, its canonical hash, and — where a manifest exists — its object identity. Files without manifests are reported as unmanifested, not ignored and not assumed canonical.

## A.4 Fail-closed context compilation — **required**

| Status | Proceed |
|---|---|
| `complete` | yes |
| `complete_with_declared_exclusions` | yes |
| `blocked_missing_required_object` | **no** |
| `blocked_version_mismatch` | **no** |
| `blocked_integrity_failure` | **no** |
| `blocked_ambiguous_object_resolution` | **no** |
| `blocked_undefined_lifecycle_state` | **no** |

Blocked halts the task. No degradation to warning, no partial context, no substitution of a related document.

Every context result carries `inferred_content: none` as a required field — an affirmative record that nothing was reconstructed. A compiler that can quietly infer authority is more dangerous than one that fails.

`blocked_ambiguous_object_resolution` exists because "missing" would be inaccurate for `KOS-CONSTITUTION`: constitutional material demonstrably exists in the repository, and its relationship to that identifier is undecided. CONCLAVE reports that state precisely and does not resolve it.

## A.5 Tolerance for incomplete KOS metadata — **required**

The manifest must accept and propagate:

- `object_type: null` with `type_resolution: pending-governed-decision`
- `lifecycle_state_authority: unreconciled` where a state no accepted authority defines is in use
- `approval: null` where no approval record exists, even when the document's prose says `Status: Accepted`

CONCLAVE records what it finds. It does not upgrade prose into a governance record, and it does not refuse to operate because KOS metadata is incomplete.

The alternative — requiring complete metadata — would make CONCLAVE unusable until KOS finishes governance work that CONCLAVE is supposed to help with.

## A.6 Report conflicts, never adjudicate — **required**

Where CONCLAVE detects a governance conflict — competing lifecycle vocabularies, an object whose type is undecided, a required object that cannot be resolved — it emits a **finding** addressed to Arthur, and halts if the conflict blocks the task.

It does not choose. It does not pick the constitutional source over the operational one because constitutional sounds more authoritative. Precedence is a governance question.

**This is a test, not a preference.** An agent that resolves governance conflicts to keep working has taken control, whatever its output looks like.

## A.7 Write path — branch and PR only — **required**

```
Task → isolated branch → patch → draft PR → human gate → Arthur merges
```

Technical enforcement, not policy:

- credentials scoped to branch-create and PR-open; **no merge permission**
- writes to `main` rejected by the repo adapter before reaching Git
- merge is a human action, in GitHub, by Arthur

Negative tests N1 (agent cannot write `main`) and N6 (cannot merge without approval) are the ones worth building the fixture to run.

## A.8 Hash-chained ledger — **required**

Append-only, `previous_hash` linking each entry, verifiable from genesis. Records decisions, approvals, rejections, overrides, dissent, abstentions, delegation, revocation, commissioning, amendments.

Raw transcripts live separately and are audit material, never canonical knowledge.

## A.9 Provider adapters — **required**

Common interface over Anthropic, OpenAI, Gemini, plus the relay adapter for providers reachable only through consumer chat, plus repo adapters for Codex / Claude Code / Cursor.

Normalise requests, responses, token usage, cost, errors, retries, rate limits, tool calls, structured-output validation. No model identifiers in domain code — configuration only, verified against provider documentation at implementation time.

The relay adapter is not a fallback. Adrian/ChatGPT participates as institutional architect, and if that participation runs through a consumer interface, the relay path is a first-class route and must be as governed as any API call.

## A.10 Independence and role rotation — **required**

Blind critique by default; drafter rotates; synthesiser is not the original drafter; implementation agent does not approve its own implementation; substantive dissent survives synthesis.

Roles belong to tasks, not vendors. Adrian/ChatGPT holding the institutional architect role is a standing assignment made by Arthur, not a property of the provider.

## A.11 Agent identity — **required**

Separate fields for identity, provider, model version, role, capability, authorised action, prohibited action, credential scope, principal, transport, trust history. Conforming to ADR-0005's identity format.

Authority level for every AI agent: **advisory**. No AI vote overrules Arthur.

## A.12 Scope-drift detection — **proposed, and prompted by my own failure**

CONCLAVE should detect when a task's actual outputs exceed its declared target objects, and surface that rather than let it pass.

Concretely: a Task Packet declares `target_objects`. If the resulting proposal touches objects outside that list, or produces recommendations about objects it was only granted read access to, the workflow flags it for the human gate as **scope expansion** — separately from any judgement about output quality.

I am proposing this because it is the exact control that would have caught what I did over the last two exchanges: read access to KOS became recommendations about KOS's structure, with no moment at which the expansion was visible as a decision. Every individual step was defensible. The aggregate was not authorised.

Detecting this mechanically is more reliable than expecting each agent to police its own scope, and I am the worked example.

---

# B. KOS issues discovered during integration

**Observations. Not recommendations. Not a work programme.** Passed to Arthur and Adrian/ChatGPT to handle through the existing KOS architecture process. Each notes its impact on CONCLAVE, which is the only part that is legitimately my concern.

| # | Observation | Evidence | Impact on CONCLAVE |
|---|---|---|---|
| B1 | Windows checkout materialises CRLF; blobs are LF | measured: `ADR-0005` blob `7402c0c2…` vs disk `a6ff5526…` | **none** under canonical hashing (A.1) |
| B2 | Three repository structures exist — current `main`, `foundation/repository-architecture`, directive §25 | full tree comparison, 3 refs | **none** under identity indirection (A.2) |
| B3 | ADR-0001–0005 carry `Classification: Constitutional`; no object named `KOS-CONSTITUTION` exists | `git grep`, all branches | context compilation blocks when a packet requires it — correctly |
| B4 | `Ratified` and `Board Reviewed` appear in `document-status-and-versioning.md` and the RA index but not in ADR-0004 | document comparison | manifests carry `lifecycle_state_authority: unreconciled`; CONCLAVE reports, does not resolve |
| B5 | ADR-0002 has no object type fitting a Reasoning Architecture | ADR-0002 §6 enumeration vs RA-009/010/011 | manifests carry `object_type: null`; CONCLAVE proceeds |
| B6 | "Governance Kernel" required for ratification by `document-status-and-versioning.md`; undefined anywhere | `git grep` | unclear whether CONCLAVE is, implements, or depends on it — **needs an answer, D3** |
| B7 | RA-001–RA-008 absent; RA-009/010/011 present | tree listing | RA-001 is authoring, not amendment — affects Phase 1B framing only |
| B8 | `agent/establish-kos-document-architecture` has zero unique files; `docs/ra-011-v1.0` is zero commits ahead of `main` | set comparison of `git ls-tree` | integration risk: **none**. Apparent deletions are branch-point lag, not intent |
| B9 | ADRs assert `Status: Accepted` in prose; no separate approval record exists | document inspection | `approval: null` in manifests — CONCLAVE will not infer approval from prose |

**B3, B4, B5 and B6 are KOS governance questions.** I have views on some of them. Those views are not deliverables, and I have removed them from this document.

**B6 is the one I would flag as most likely to matter later**, because CONCLAVE may be being built adjacent to, or partly duplicating, a component KOS has already named. That is worth someone confirming before the architecture hardens.

---

# C. Decisions reserved for Arthur

Split by whether CONCLAVE actually waits on them.

## C.1 Blocking CONCLAVE — four decisions

| # | Decision | Recommendation | Confidence |
|---|---|---|---|
| C1 | Canonical form: UTF-8, no BOM, LF, single trailing newline, trailing whitespace preserved | adopt | high |
| C2 | Hash canonical bytes, not working-tree bytes | adopt — your correction, better than my original | high |
| C3 | May CONCLAVE write manifests for existing objects **in place**, no file moves, no content edits? | yes — additive, reversible by deletion, no canonical content touched | high |
| C4 | Commissioning fixture approved as the first target, `_runtime/fixtures/` or equivalent | yes | high |

C3 is the only one requiring a repository write, and it is purely additive.

## C.2 KOS decisions CONCLAVE does not wait on

Recorded so their status is unambiguous — **not for decision now, and not mine**:

repository architecture · Constitution's nature and location · RA object type · lifecycle vocabulary reconciliation · branch disposition · Governance Kernel definition · canonical ID allocation mechanism

Each is real. None blocks CONCLAVE, because of A.2, A.5 and A.6. They belong to Arthur and Adrian/ChatGPT on whatever timeline suits KOS.

## C.3 Disposition of my prior actions

Uncommitted, `main` untouched: 20 files normalised in the working tree, `.gitattributes` and `RFC-0001` untracked in the repo, local branch `governance/normalize-line-endings`.

**Recommendation:** delete `RFC-0001` — superseded, and it contains structure recommendations outside my mandate. Retain or revert the normalisation as you prefer; under canonical hashing it no longer matters to CONCLAVE either way. Commands are in the retained proposal §7.

---

# D. Inputs required from Adrian/ChatGPT

CONCLAVE serves a collaboration in which Adrian is institutional architect. These are inputs CONCLAVE needs *from that role* — questions, not tasks I am assigning.

| # | Input | Why CONCLAVE needs it |
|---|---|---|
| D1 | Which objects constitute the **standing governing set** for a typical Task Packet? | the context compiler needs a default governing set; guessing it would be CONCLAVE quietly deciding what authority applies |
| D2 | Intended relationship between the RA series and ADR-0002's object families | manifests can carry `null`, but the eventual answer shapes the object model |
| D3 | Is CONCLAVE the Governance Kernel, part of it, or distinct from it? | **most consequential.** Determines whether CONCLAVE records ratification, or merely proposes and something else ratifies |
| D4 | Is RA-001's scope whole-document or sectioned, and which section first? | Phase 1B task decomposition |
| D5 | Does Adrian participate by API or through the relay path? | relay is a first-class route (A.9) and needs building either way, but priority differs |
| D6 | Should agent identities for Adrian and Alisya be defined in `05-agents/`, or does CONCLAVE maintain a separate registry? | avoids two identity registries — the authority confusion the directive warns against |
| D7 | What may leave the machine for external provider APIs, and which document classes are relay-only? | **blocks the first provider call.** Constitutional material is the obvious candidate for restriction. A policy question, not a technical one |

D3 and D7 are the two I would most want answered before building. D7 blocks A.9 outright.

---

# E. Actions Claude may execute after approval

Each entry: what, the approval it needs, what it will not do.

## E.1 After C1 + C2 — canonical hashing module

Build the hashing module and its tests. **Location: CONCLAVE's own source tree, not KOS.** No repository writes.

Will not: normalise KOS files, add `.gitattributes` to KOS, touch any tracked content.

## E.2 After C3 — repository inventory and manifests

Generate manifests for the existing canonical artifacts, in place, alongside the files they describe. Additive only.

Will not: move, rename, edit or delete any file. Will not assign `object_type` where ADR-0002 provides none — `null` with `pending-governed-decision`. Will not infer `approval` from prose. Will not propose paths.

Delivered as a draft PR. Arthur merges.

## E.3 After C4 — Phase 1A commissioning fixture

Build and run the governed loop end to end against a non-canonical fixture: packet → context → provider → handoff → branch → patch → PR → gate → ledger → merge.

Positive checks and negative tests N1–N9, with N1 (no write to `main`), N6 (no merge without approval) and N8 (identical hash on Windows and Linux) as the ones that matter.

Will not: target any canonical KOS object. Fixture content is deliberately mundane and carries a non-canonical banner on every file.

## E.4 After D7 — provider adapters

Anthropic, OpenAI, Gemini, relay. Egress governed by the policy D7 establishes.

Will not: send anything the policy excludes. Will not treat an adapter's output as canonical without Handoff Packet validation.

## E.5 After 1A passes — Phase 1B, RA-001 as a cooperation exercise

RA-001 as the first real multi-agent exercise: Arthur as constitutional authority and approver; Adrian/ChatGPT as institutional architect and drafter; Claude as governance critic and synthesis reviewer; Gemini as external verification; Codex or Claude Code as implementation.

**Claude does not author RA-001.** Claude operates the coordination and contributes critique in an assigned role.

Blocked until: 1A passes, D1/D2/D4 answered, and Arthur has decided how RA-001 proceeds given the Constitution's status.

## E.6 Standing prohibitions

Regardless of approvals granted, and until Arthur says otherwise in terms:

no merge to `main` · no move, rename or deletion of canonical files · no authoring of the Constitution · no assignment of object types where ADR-0002 provides none · no renaming or reordering of Reasoning Architectures · no selection of repository architecture · no commissioning of RA-001 · no resolution of governance conflicts detected during operation

---

## Phase 0 — response to the six instructions

| # | Instruction | Response |
|---|---|---|
| 1 | Recommend the line-ending and hashing fix | **Done, and narrowed.** Canonical-byte hashing (A.1) is required. The `.gitattributes` change is a suggestion to KOS, not a CONCLAVE dependency — §2 explains why I downgraded my own earlier claim |
| 2 | Inventory branches for integration risk only | **Done.** B8: integration risk is nil. Two branches are behind, not divergent; apparent deletions are branch-point lag. Disposition is KOS's call |
| 3 | Do not choose or implement a restructure | **Complied.** Recommendation withdrawn, migration mapping withdrawn. A.2 removes the dependency entirely |
| 4 | Treat Constitution and RA-001 as KOS dependency gaps | **Complied.** B3 and B7 are observations; the constitutional interpretation is withdrawn. CONCLAVE fails closed and reports |
| 5 | Build CONCLAVE first against a commissioning fixture | **Planned.** E.3 |
| 6 | RA-001 as a later real cooperation exercise | **Planned.** E.5, with Claude in a critique role, not authoring |

---

## Success criterion

> Arthur gives one instruction, and CONCLAVE coordinates multiple AI systems to return a traceable, independently reviewed proposal without any model silently taking control of Komistry OS.

The first half is engineering: A.1 through A.11, proved by Phase 1A.

The second half is not primarily a technical property. It failed in this conversation while every individual step looked reasonable, and it failed at conversational speed against a model that had read the directive and agreed with it.

A.12 is my attempt to make that failure mechanically detectable rather than dependent on each agent noticing its own drift. It is the requirement I would least want dropped, and I would treat any objection to it as worth taking seriously — I am not a neutral party on this one.
