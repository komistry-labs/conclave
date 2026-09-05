# CONCLAVE v0.8.0

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

Requires Python 3.12 or newer. The required cross-platform matrix verifies
**Windows with Python 3.12**, **Ubuntu/Linux with Python 3.13**, and **macOS
with Python 3.12**. An additional Ubuntu/Python 3.12 job verifies the declared
minimum independently of the Windows and macOS jobs. This is a targeted
compatibility matrix, not a claim that every operating-system/Python
combination is tested.

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
├── synthesis/               immutable sequential-synthesis continuations
├── identity/verifier-profiles/  immutable public IDM implementation profiles
├── signing/broker-profiles/     immutable fixture/sandbox transport profiles
├── signing/broker-endpoints/    immutable sandbox HTTPS endpoint profiles
├── signing/broker-authorizations/ exact one-attempt human egress grants
├── signing/broker-attempts/     durable pre-network attempt intents
├── signing/broker-receipts/     secret-free transport outcomes
├── signing/broker-recovery-authorizations/ exact human recovery grants
├── signing/broker-recovery-attempts/ durable one-replay intents
├── signing/broker-recovery-dispositions/ terminal recovery outcomes
└── diagnostics/                 keyless fixture diagnostics results
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
python -m pytest                  # full local test suite
```

`validate` separates its findings by category because they have different
owners. Schema is structural. Semantic is internally inconsistent. **Governance
is an authority-boundary breach and is not for an agent to resolve.**

### IDM verification, evidence and gates (Increment 19)

The v0.8.0 Increment 19A foundation defines closed, immutable trust-input,
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

Neither 19A nor 19B enables identity mode in existing workspaces.

19C adds explicit `local`, `verify` and `attested` workspace modes. Legacy
workspaces remain local. Strong modes retain the exact human-principal ceremony
while requiring a workspace-bound identity PASS and, for attested mode, one
exact non-conflicting evidence binding. Gated egress, authority-decision,
evidence-receipt and ledger-checkpoint flows confer no membership or authority.

19D adds a fixture-only external broker and a public verification adapter for
the exact hash-pinned IDM v1 wheel and source baseline. End-to-end tests use
actual attached-payload COSE_Sign1 evidence, delegation, role, scope, trusted
fixture time and signed revocation state. Fixture identities and deterministic
test keys are newly generated and explicitly non-production; B1/B2 trust,
identities and keys are not adopted. CI covers Windows, Ubuntu and macOS.

### Configuration and diagnostics (Increment 20A)

20A adds immutable, exact-reference verifier and broker profiles plus a
source-checkout-only keyless fixture diagnostics probe. It does not select a
default profile, change `identity.mode`, load trust input, resolve a credential,
open a network connection, use a key, sign, or execute identity verification.

```powershell
conclave identity verifier-profile create `
  --profile-id public-idm `
  --expected-trust-input identity/trust-inputs/future-public-trust.json `
  --expected-trust-domain tdid:cccccccccccccccccccccccccc

conclave evidence broker-profile create `
  --profile-id fixture-broker `
  --classification fixture-only `
  --verifier-profile identity/verifier-profiles/<hash-named-profile>.json `
  --transport fixture:conclave-19d-diagnostics `
  --credential-reference none

conclave evidence broker-check `
  --broker-profile signing/broker-profiles/<hash-named-profile>.json
```

The resulting `PASS` means only that the bounded fixture subprocess contract
returned the expected public IDM pin. Diagnostic time is local operational
time, not trusted verification time. Sandbox profiles can be stored for a
future increment, but 20A always refuses to call them and never dereferences
their `env:NAME` credential selector.

### Dormant sandbox transport library (Increment 20B)

20B adds a sandbox-only HTTPS transport library but deliberately adds no
operator CLI command. The library requires an exact endpoint, signing request,
public trust input and one-attempt human broker-egress authorization. It writes
an immutable attempt intent before credential resolution, so a crash can never
silently authorize a resend. Completed attempts produce secret-free receipts
and factual ledger evidence.

The sole credential mechanism is the exact `env:NAME` selector sealed in the
20A sandbox profile. The token value is read once immediately before the one
request and is never stored, hashed, logged or returned. HTTPS requires system
CA and hostname verification, TLS 1.2 or newer, a vetted public destination,
no redirect and no ambient proxy. Returned binary bytes remain subject to the
unchanged Increment 19 public verifier; HTTP success never means evidence PASS.

20B is dormant by default. Production endpoints, production credentials,
production trust, private keys and embedded signing remain prohibited.

### Explicit sandbox operation and recovery (Increment 20C)

20C adds exact-reference operator commands for creating/showing endpoints and
one-attempt authorizations, submitting an already sealed evidence request,
inspecting the resulting attempt/receipt, and resolving an ambiguous outcome.
Recovery is either non-transmitting abandonment or one explicitly authorized
replay of the byte-identical original body under the exact original
idempotency key. There is no automatic retry, and a second ambiguous replay is
terminal for CONCLAVE transmission.

The public operator surface is explicit: `conclave evidence sandbox-endpoint`,
`broker-authorization`, `broker-submit`, `broker-attempt`, `broker-receipt` and
`broker-recovery` operate only on the exact records named by the operator.
Their presence does not schedule work or authorize a provider or broker call;
submission and the single bounded replay remain subject to their separate,
exact human authorization records.

Before any CLI submission or replay, the public-only pinned IDM runtime must
be explicitly provisioned with `CONCLAVE_IDM_WHEEL` and
`CONCLAVE_IDM_SOURCE_ARCHIVE`. Every trust/revocation/time evidence reference
must name an existing canonical file directly under the workspace's
`identity/trust-inputs/` area. These inputs are public verification evidence,
not broker credentials. The broker bearer value continues to come only from
the authorization-bound `env:NAME` selector and is never persisted or shown.

Abandonment does not load the public verifier, resolve a credential, perform
DNS or open a socket. Deleted receipts or dispositions that already have
ledger evidence block recovery; deletion can never reopen a transmission.
All recovery records and events remain factual, immutable and authority
neutral. A live sandbox call still requires separate Arthur authorization.

### Security and conformance closeout (Increment 20D)

20D adds no transport, retry route, credential resolver, signer, key API or
production mode. It adds one closed, content-hashed record at
`.conclave/signing/conformance-reports/` for binding the exact CONCLAVE source,
the frozen 20A–20D protocols, the pinned public IDM implementation, the three
required platform runs, package inventories, machine reports and all fourteen
frozen threat-control findings.

The report cannot represent overall `PASS` unless every required item is
present and passing with zero required security skips. A failed item forces
`FAIL`; an unavailable or `NOT_RUN` item forces `INCOMPLETE`. The schema fixes
`live_sandbox_exercised`, `production_ready`, `production_use_allowed` and
`action_execution_allowed` to false and all authority, decision and membership
effects to `none`.

CI builds and inventories both sdist and wheel, scans their bounded
decompressed members for fixture and private-material markers, binds the
machine-readable pytest report, performs a bounded static capability scan,
installs the wheel in a fresh environment and publishes secret-free evidence
for every matrix job. The required cross-platform jobs are Windows/Python
3.12, Ubuntu/Python 3.13 and macOS/Python 3.12; Ubuntu/Python 3.12 separately
verifies the declared minimum. The package configuration excludes
the repository test broker, fixture archives, test identities, certificates
and tokens from both distributions.

A conformance report and its ledger event are factual evidence only. Ledger
reconciliation may restore report existence from an already valid immutable
record, but cannot infer PASS, approval or production readiness. Fixture-level
20D closeout never authorizes a live sandbox call or production use.

---

## Current limitations

Known and deliberate:

- No runtime GitHub repository adapter or automated pull-request creation or
  merge. Repository-hosted GitHub Actions does run the required Windows,
  Linux and macOS test matrix on pushes and pull requests.
- Human confirmation remains local and single-operator, not multi-custodian.
  Identity/evidence workflow enforcement and fixture conformance are
  available, but there is no production signing-broker or key integration.
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
├── idm_reference_adapter.py  hash-pinned, verification-only IDM v1 adapter
├── sandbox_transport.py  sandbox HTTPS first-attempt boundary
├── sandbox_recovery.py   explicit abandonment and one exact replay
├── sandbox_operator_runtime.py  fail-closed public verifier provisioning
├── gating.py        explicit identity modes and fail-closed workflow gates
├── checkpoint.py    immutable ledger checkpoint candidates and receipts
├── live_providers.py  explicitly authorized OpenAI, Claude, Gemini adapters
└── cli.py          command surface
```
