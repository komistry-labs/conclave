# Increment 9 — Provider Integration, Governed Context, and Adaptive Routing

Status: **FROZEN FOR IMPLEMENTATION**

Baseline: CONCLAVE v0.1.2 at `1294050`

## 1. Purpose

Add the foundation that lets CONCLAVE give providers the same governed context,
assign only the roles justified by a task, enforce token budgets, and use
different transports without placing provider-specific behavior in domain code.

This increment does not redesign Phase 1A, alter Task Packet schema 0.1.0, grant
authority to an AI provider, or modify KOS.

## 2. Safety boundary

Outbound provider egress is denied by default. A route and provider request may
be prepared locally, but execution is refused unless an explicit egress
decision permits the transport and every included context classification.

No consumer-chat login, browser session, credential, API key, or OAuth token is
stored in a CONCLAVE artifact. Credentials are supplied to transport adapters
at runtime and remain outside governed payloads.

## 3. Frozen contracts

### 3.1 Governed context

A context source declares:

- stable object identity;
- status and authority;
- classification;
- content hash;
- content.

A sealed Context Bundle is immutable, content-addressed, bound to one immutable
Task Packet reference and hash, and rejects missing provenance or stale hashes.
Provider prompts are deterministic projections of the sealed bundle plus the
stage instruction; callers cannot substitute an unrelated prompt. Projections
are filtered only by the explicit egress policy.

### 3.2 Adaptive routing

Roles belong to tasks, not vendors. The deterministic default route is:

| Risk | Required stages |
|---|---|
| routine | lead |
| important | lead, critic |
| evidence-sensitive | lead, verifier |
| canonical | lead, critic, verifier, synthesizer |

Stages are sequential unless a route explicitly marks an independent parallel
group. The original lead may not be the sole critic or synthesizer. Missing
provider capability is a refusal, not a silent downgrade.

### 3.3 Budgets

Every route has cumulative input and output token ceilings plus optional
per-stage ceilings. Prior completed runs are included before the next stage is
prepared. Estimates and actual usage are separate facts. Exceeding a ceiling
refuses preparation or further execution. Prices are injected configuration;
they are never hard-coded in domain logic.

### 3.4 Usage and cost accounting

Every completed provider call may produce an immutable Usage Record bound to
the Task Packet, project, provider, model, transport, role, and provider request
identifier. Normalized usage distinguishes:

- total input tokens;
- cached input tokens (a subset of input);
- output tokens;
- reasoning output tokens (a subset of output).

A versioned Price Catalog supplies per-million-token rates, currency, effective
time, source URL, retrieval time, and catalog hash. Calculated cost records cite
both the usage record and exact catalog entry. Decimal arithmetic is mandatory.
No default prices are embedded in CONCLAVE.

Project totals are derived views over immutable cost records. They are evidence
for later billing, not invoices and not authority to charge a client.

### 3.5 Provider boundary

All transports implement one interface and return a normalized response with
provider, model, transport, text, structured output, usage, finish status, and
provider request identifier. Model identifiers remain configuration.

Manual relay remains a first-class adapter. Fixture adapters exercise the full
contract without network access. Live OpenAI, Anthropic, and Gemini transports
are integration adapters behind the same boundary and remain disabled until
egress and credential configuration are explicitly approved.

## 4. Acceptance criteria

1. Context bundles are deterministic, immutable, and detect stale source or
   bundle hashes.
2. A source without identity, status, authority, classification, or hash is
   rejected.
3. Default routing uses one provider for routine work and expands only with
   declared risk.
4. Role separation prevents a lead from being its own sole critic or
   synthesizer.
5. Token ceilings fail closed before provider execution.
6. Egress defaults to deny and classification exclusions are enforced.
7. Provider responses normalize usage and identity without granting authority.
8. Usage cost is reproducible from an immutable usage record and a cited,
   versioned price catalog, including cached-input treatment.
9. Per-task and per-project totals derive only from matching sealed records.
10. Fixture and negative tests require no account, credential, network, KOS
   access, or live provider call.
11. All v0.1.2 tests continue to pass unchanged.

## 5. Deferred

- Arthur's final provider-egress policy and classification matrix;
- live credentials and OAuth/account-linking user experience;
- provider-specific SDK implementations and retry/rate-limit policy;
- automated price-catalog retrieval, pricing exceptions, and cost settlement;
- client invoicing, taxes, markup, credits, subscriptions, and payment capture;
- concurrent execution engine;
- Phase 1B authoring.
