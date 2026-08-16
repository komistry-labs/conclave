# CONCLAVE v0.7.0

A local command-line tool for coordinating several AI providers on Komistry OS
work through manual relay or explicitly authorized live adapters, with an
auditable trail.

```
one instruction  →  independent advisory responses  →  structured review  →  human decision
```

---

## Purpose

CONCLAVE lets one person issue a single instruction, obtain genuinely
independent responses from several AI providers, and receive a structured
review that preserves disagreement rather than averaging it away — with every
artifact hashed, immutable, and recorded in a verifiable chain.

## Non-goals

CONCLAVE deliberately does **not**:

- call a provider API without an explicit principal-authored egress decision
- automate GitHub, pull requests or merges
- modify Komistry OS in any way
- interpret provider prose, semantically or with embeddings
- approve, ratify, commission or merge anything

**Komistry OS is external and read-only.** CONCLAVE never writes to it. A KOS
path may be recorded in config, but the governed workflows use explicit,
operator-supplied source manifests rather than silently traversing KOS.

---

## Installation

Requires Python 3.10 or newer.

The current increment is verified on **Windows with Python 3.12** and
**Debian/Linux with Python 3.13**. GitHub Actions runs the same platform pair.

```powershell
cd conclave
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -e .
conclave --help
```

---

## Workspace layout

```
.conclave/
├── config.yaml              principal, providers, authority policy, hashing
├── tasks/
│   └── <task-id>/
│       ├── v1.yaml          immutable Task Packet
│       └── v2.yaml          revision — a new object, not an edit
├── relay/
│   ├── outbox/
│   │   ├── <task>__v1__<provider>__<hash12>.md    prompt to paste
│   │   ├── context/<task>__v1__s0__<provider>__*.md
│   │   ├── context/<task>__v1__s0__<provider>__*.yaml
│   │   └── exports.jsonl                          export/replacement events
│   └── inbox/
│       ├── raw/<hash12>.raw.md    exact bytes received, never altered
│       ├── repair/<hash12>__repair.md
│       └── <task>__v1__<provider>__<hash12>.yaml  sealed Handoff Packet
├── scope/                   sealed Scope Reviews
├── council/                 Council Review YAML (canonical) + .md (projection)
├── ledger/ledger.jsonl      hash-chained event ledger
├── context/                 sealed provider context bundles
├── routes/                  sealed stage and token-budget plans
├── runs/                    normalized, immutable provider runs
├── batches/                 sealed concurrent-wave records
├── orchestrations/          immutable batch-to-Council pause checkpoints
└── synthesis/               immutable sequential-synthesis continuations
```

---

## Operator workflow

```powershell
conclave init --principal "Arthur"
conclave ledger init

conclave task create `
  -o "Draft RA-001 Part I" `
  -t "RA-001#RA-001-PART-I" `
  -r "ADR-0002" `
  -x "KOS-CONSTITUTION" `
  -P "adrian:institutional_architect" `
  -P "claude:governance_critic" `
  -P "gemini:external_verifier" `
  -c "do not rename approved Reasoning Architectures" `
  -a "constitutional grounding stated explicitly"

conclave validate
conclave relay export TP-draft-ra-001-part-i-<hash>

# ... manual relay, see below ...

conclave relay import claude-reply.md
conclave scope review
conclave council review TP-draft-ra-001-part-i-<hash>
conclave ledger verify
```

For an explicitly authorised live independent-review wave, supply one model,
prompt file, and input estimate per stage:

```powershell
conclave run concurrent-live `
  --context .conclave/context/<bundle>.yaml `
  --route .conclave/routes/<route>.yaml `
  --egress-decision D7-egress.yaml `
  --model 0:gpt-model --model 1:claude-model --model 2:gemini-model `
  --prompt 0:lead.txt --prompt 1:critic.txt --prompt 2:verify.txt `
  --estimated-input 0:1200 --estimated-input 1:1200 --estimated-input 2:1200 `
  --max-workers 3 --max-attempts 1
```

Lead, critic, and verifier remain isolated and may overlap. A synthesizer is
never admitted to the concurrent wave.

After a completed batch:

```powershell
conclave orchestrate batch .conclave/batches/<execution-batch>.yaml
```

This validates every response before downstream writes, creates Handoff and
Scope artifacts, assembles the Council Review, and stops at an explicit pause.
It does not record Arthur's decision or execute any authorised action.

For a canonical route paused at `awaiting_sequential_synthesizer`, run exactly
one governed final stage:

```powershell
conclave orchestrate synthesize-live `
  .conclave/orchestrations/<orchestration>.yaml `
  --instruction synthesis-instruction.md `
  --egress-decision D7-egress.yaml `
  --model claude-model `
  --estimated-input-tokens 3200
```

The sealed prompt includes every independent Handoff and its provenance. The
result becomes a new Run, Handoff, Scope Review, Council Review, and immutable
synthesis-continuation record. Earlier artifacts are never changed. The final
state is still a pause for the human principal; no action is authorised.

Scope flags: `-t` target (may be changed) · `-r` read-only (may be read and
cited) · `-x` prohibited (must not be touched at all). Object references take
the form `ID`, `ID#SECTION`, or `ID#SECTION@VERSION`.

---

## Manual relay procedure

1. `conclave relay export <task-id>` writes one Markdown file per assigned
   provider into `relay/outbox/`.
2. Open **one** file. Paste its entire contents into that provider.
3. Save the reply to a file.
4. `conclave relay import <reply-file>`.
5. Repeat per provider.

**Do not show one provider another's prompt or reply.** Independence is the
point: each prompt is generated from the Task Packet alone and contains no
other provider's content. Showing one provider another's answer produces
agreement that means nothing.

If a reply is rejected, send the generated repair request back to the *same*
provider and import the corrected reply. The rejected bytes are kept.

For governed work that needs a sealed Context Bundle and Route Plan, export
one route stage instead:

```powershell
conclave relay export-context `
  --context .conclave/context/<bundle>.yaml `
  --route .conclave/routes/<route>.yaml `
  --instruction instruction.md `
  --stage-index 0
```

This command verifies the Task Packet, Context Bundle, Route Plan, and stage
binding; projects the complete sealed context into one provider prompt; and
writes a content-addressed prompt plus sealed manifest under
`relay/outbox/context/`. It makes no provider API call. The manifest lets
Handoff import and ledger reconciliation prove exactly which context, route,
stage, provider, and role the response answers.

---

## Live provider execution

OpenAI, Claude, and Gemini have live HTTP adapters. Manual relay remains
available. Live execution still uses the same sealed Task Packet, Context
Bundle, Route Plan, cumulative token ceilings, provider independence rules,
and immutable Run Record.

Credentials are read only from the process environment:

| Route provider | API | Credential |
|---|---|---|
| `adrian` or `openai` | OpenAI Responses API | `OPENAI_API_KEY` |
| `claude` | Anthropic Messages API | `ANTHROPIC_API_KEY` |
| `gemini` | Gemini `generateContent` API | `GEMINI_API_KEY` |

CONCLAVE does not create an egress decision. Arthur must supply the D7 policy:

```yaml
schema_version: egress-decision/0.1.0
allowed: true
transports:
  - openai-responses-api
  - anthropic-messages-api
  - gemini-generate-content-api
classifications:
  - public
  - internal
authority: Arthur
decision_ref: D7-<authoritative-reference>
```

Then execute one route stage:

```powershell
conclave run live `
  --context .conclave/context/<bundle>.yaml `
  --route .conclave/routes/<route>.yaml `
  --prompt instruction.md `
  --egress-decision D7-egress.yaml `
  --model <provider-model-id> `
  --stage-index 0 `
  --estimated-input-tokens 1000
```

The command fails before network access if the policy authority does not match
the workspace principal, the route transport or context classification is not
authorized, the Task Packet binding is invalid, a predecessor stage is
missing, or the estimated cumulative token ceiling is exceeded.

Provider-reported total, cached-input, output, and reasoning-output tokens are
normalized into the Run Record. Pricing is deliberately not embedded.

---

## Packet and artifact lifecycle

```
Task Packet v1
      │  relay export
      ▼
Relay prompt  ──paste──►  provider  ──reply──►  Raw Provider Response
                                                       │ parsed into
                                                       ▼
                                                Handoff Packet
                                                       │ evaluated by
                                                       ▼
                                                 Scope Review
                                                       │ aggregated into
                                                       ▼
                                                Council Review
                                                       │
                                                       ▼
                                          Authority Decision Record
                                                       │
                                                       ▼
                                                Task Packet v2
```

The raw response and the Handoff Packet are **two distinct objects**. CONCLAVE
keeps what the provider actually returned, not only its own reading of it.

---

## Immutability model

Every canonical artifact is written once and never edited.

| Artifact | Immutability |
|---|---|
| Task Packet | write-once per version; revision creates `v2`, `v1` untouched |
| Raw response | content-addressed; never overwritten, never decoded lossily |
| Handoff Packet | sealed at import; refuses to write with a stale hash |
| Scope Review | one attestation per (handoff, schema); re-running verifies, never recomputes |
| Council Review | id derived from its source set; a changed set is a new review |
| Authority Decision | one write-once record per exact Council Review; review remains unchanged |
| Context relay export | stage-bound prompt plus sealed content-addressed manifest |
| Synthesis continuation | binds the independent checkpoint, final Run and new Council; never edits them |
| Ledger | append-only, hash-chained, never rewritten or truncated |

All content hashes are computed on **canonical bytes** — UTF-8, no BOM, LF,
one trailing newline — so an artifact hashes identically on Windows, macOS and
Linux. Raw provider responses are the exception: they are hashed as raw bytes,
because a CRLF or BOM difference is evidence, not noise.

Models are frozen. Changing a sealed object produces a new object whose hash
is stale, and writes refuse stale hashes — so the only route from object to
disk runs through re-sealing.

---

## Authority boundaries

- **Arthur is the sole constitutional authority.** No AI agent approves,
  ratifies, commissions or merges anything.
- Providers are `advisory` and `may_merge: False` at the *type* level — a
  packet granting merge authority fails to construct.
- The Council Review decision block admits only `decision: pending`, with
  `decided_by`, `decided_at` and `rationale` typed as `None` and
  `authorised_actions` constrained to empty. CONCLAVE cannot express a
  decision even by accident.
- The Council Review schema is closed: a tampered file carrying `approved` or
  `merge_authorised` fails to load.
- A human decision is recorded in a **separate** sealed artifact bound to the
  exact Council Review and Task Packet hashes. `approve` is refused unless the
  review is `ready_for_human_review`.
- Recording requires an initialised, healthy ledger and interactive entry of
  the exact configured workspace principal. This is explicitly local operator
  confirmation, not cryptographic identity proof.
- In the ledger, `advisory_agent` may only be the actor for the three
  submission events. Any other combination is refused at append and flagged at
  verification.

`human_decision_required` is `true` on every Council Review. `review_status`
expresses readiness or blockers; it never removes the requirement to decide.

---

## What CONCLAVE deliberately will not infer

- **Scope drift evaluates declarations only.** It reads `objects_touched` and
  does not mine provider prose for undeclared work. Every Scope Review says so
  in its `evaluation_basis` field. Undeclared work is a Council Review concern,
  where a human is looking.
- **Agreement is structural.** Identical enum values, identical explicit
  shared finding keys, identical scope classifications. Never lexical
  similarity, never embeddings. `finding_id` is provider-local — two providers
  both writing `F-001` have agreed about nothing — so cross-provider finding
  comparison requires an explicit shared `key`.
- **Nothing is repaired silently.** Validation reports and refuses. A rejected
  response is preserved exactly as received.

---

## Failure and repair

**A rejected provider response.** Preserved verbatim. A bounded repair request
is generated naming only the defects and the authoritative identifiers — taken
from CONCLAVE's export record, not from the rejected reply, so a provider is
never told to repeat its own mistake. No Handoff Packet is created.

**An operational ledger append fails after an artifact is written.** The artifact is kept.
Re-running the original command will not help — creation is refused because
the artifact already exists. Instead:

```powershell
conclave ledger verify      # find and fix the chain damage
conclave ledger reconcile   # append the missing events
```

Human decisions are the deliberate exception: reconciliation never infers
them. If their ledger append fails, verify the ledger and rerun the exact
`council record-decision` command; the principal must reconfirm, after which
the event append is retried idempotently and the decision artifact is not
rewritten.

**Ledger damaged.** `verify` reports every defect and repairs nothing. Appends
refuse while the chain is broken, so corruption never gains the appearance of
continuity.

---

## Ledger

An audit chain of governed events, not a decision table. A human decision
attaches to the verifiable chain of evidence that produced its Council Review.

```powershell
conclave ledger init        # genesis + snapshot of pre-existing artifacts
conclave ledger verify      # full chain check; exits non-zero on any defect
conclave ledger reconcile   # append events for artifacts that lack them
conclave ledger show -n 20  # display recent entries
```

`ledger init` on a populated workspace writes exactly two entries: genesis, and
one `workspace_snapshot_attested` recording every existing artifact and its
verified hash. It states plainly that those artifacts predate instrumentation
and asserts nothing about when they were created or in what order. **No
historical events are fabricated.**

`ledger reconcile` reconstructs only what immutable artifact metadata
establishes, for its supported operational event types. Where an artifact records its
own timestamp that becomes `occurred_at`; where none exists, reconciliation
time is used and the payload says the original time is unknown. Ambiguous
cases are reported as unresolved rather than guessed. It never infers human
decisions.

An entry records that an event occurred — not that it was right.
`handoff_packet_imported` means a response passed validation, not that its
findings are true. `council_review_created` means a review was produced, not
that its recommendations were accepted.

---

## Verification

```powershell
conclave validate                 # Task Packets: schema / semantic / governance
conclave scope review             # declared touches vs granted scope
conclave ledger verify            # chain from genesis to head
python -m pytest                  # 852 passing on Windows; 1 symlink test conditional
```

`validate` separates its findings by category because they have different
owners. Schema is structural. Semantic is internally inconsistent. **Governance
is an authority-boundary breach and is not for an agent to resolve.**

### IDM verification and evidence foundation (Increments 19A–19B)

The unreleased Increment 19A foundation defines closed, immutable trust-input,
actor-binding and verification-result records. It pins the accepted IDM build,
requires exact public trust/revocation/time evidence, and fails closed on any
identity, domain, role, scope, time, revocation or content-binding mismatch.
Every result is authority-neutral and can neither confer membership nor permit
an action.

19B adds closed signing requests and fail-closed import of externally produced
evidence through an explicitly injected pinned public verifier. Exact envelope
bytes, immutable verification bindings, verified-request conflicts and neutral
ledger evidence are preserved. There is still no key, allocation, issuance or
signing surface and no default verifier fallback.

Neither stage enables identity mode in existing workspaces. Workflow gates and
broker/cryptographic-fixture conformance remain separately authorized future
stages 19C and 19D.

---

## Current limitations

Known and deliberate:

- No runtime GitHub repository adapter or automated pull-request creation or
  merge. Repository-hosted GitHub Actions does run the required Windows and
  Linux test matrix on pushes and pull requests.
- Human identity confirmation is local and single-operator, not cryptographic
  or multi-custodian. The verifier and evidence-import foundations exist, but
  workflow enforcement and IDM-backed signing are not implemented.
- No trust or calibration tracking.
- No semantic comparison of provider prose.
- Undeclared object use is not detected; only declarations are evaluated.
- `conclave validate` covers Task Packets only.
- Ledger events are wired at the CLI boundary, so calling the library directly
  records nothing for operational artifacts. Authority decision recording is
  the exception: its library operation also appends the required event.
- Single-operator design. The ledger lock guards concurrent local writers, but
  nothing coordinates multiple machines.

---

## Project layout

```
src/conclave/
├── hashing.py      canonical form and content hashing — the only implementation
├── workspace.py    layout, config, discovery
├── models.py       Task Packet, ObjectRef, provider assignment, egress
├── taskpacket.py   identity, sealing, write-once storage
├── decision.py     principal instruction, hash binding, write-once decision record
├── validation.py   schema / semantic / governance
├── relay.py        prompt projection and export provenance
├── contextrelay.py sealed Context Bundle manual-relay projection
├── handoff.py      raw preservation, extraction, provenance, sealing
├── scope.py        containment rules and Scope Review
├── council.py      aggregation, structural comparison, YAML + Markdown
├── ledger.py       hash-chained event ledger
├── reconcile.py    deterministic gap closure
├── routing.py      provider roles, route stages, and token ceilings
├── concurrency.py  bounded independent waves, retries, cancellation, batch evidence
├── orchestration.py batch-to-Handoff/Scope/Council projection and pause state
├── synthesis.py     verified sequential synthesis and immutable continuation
├── identity.py      closed IDM records and fail-closed verifier boundary
├── evidence.py      bounded signing requests and external evidence import
├── live_providers.py  explicitly authorized OpenAI, Claude, Gemini adapters
└── cli.py          command surface
```
