# CONCLAVE v0.2.0 — Governed Provider Integration

| | |
|---|---|
| Based on | `v0.1.2` @ `1294050` |
| Release type | Minor feature release |
| Runtime | Context, routing, execution, accounting, handoff, and Council integration |
| Providers | OpenAI, Claude, Gemini, and deterministic fixture |
| Tests | **680 Windows · 680 Linux** |

## 1. Outcome

v0.2.0 adds the governed provider-integration foundation while retaining the
Bootstrap 0.1 authority model:

- Arthur remains the sole constitutional authority.
- Providers remain advisory and independent.
- Komistry OS remains external and unmodified.
- No agent can approve, ratify, commission, or merge.
- Manual relay remains supported.

## 2. New governed artifacts

- sealed, provenance-bearing Context Bundles
- deterministic Route Plans with role-based provider selection
- cumulative route-wide token budgets
- immutable Provider Run Records
- optional usage and price-catalog accounting artifacts
- route-bound Handoffs
- stage-aware Council Reviews

## 3. Live provider adapters

The release implements:

- OpenAI Responses API
- Anthropic Claude Messages API
- Gemini `generateContent` API

Model identifiers are supplied at execution time. Credentials are read from
`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `GEMINI_API_KEY` and are never
persisted.

Provider-reported input, cached-input, output, and reasoning-output tokens are
normalized in every Run Record. Pricing is optional, catalog-based, and kept
separate from factual token usage.

## 4. Egress governance

D7 is resolved by `D7-PROVIDER-EGRESS-v1`:

- `public` and `internal` context may use the three named live transports.
- `restricted` and `constitutional` context are excluded from live APIs.
- every live invocation requires the principal-authored machine policy
- transport and classification checks occur before adapter execution

No live provider call was made while producing this release.

## 5. Corrected defects

- execution now verifies the stored Task Packet and its Context Bundle binding
- later stages require exactly one completed run for every predecessor stage
- route-wide budgets account for prior-stage usage
- structured provider output is preserved with explanatory text
- route assignments are authoritative when converting Runs to Handoffs
- historical Council 0.1 hashes remain verifiable
- route-ineligible evidence cannot alter route-bound Council identity
- reconciliation now covers Context Bundles, Route Plans, Provider Runs, and
  route-aware Council provenance

## 6. Verification

| Platform | Environment | Result |
|---|---|---|
| Windows | Python 3.12.10 | **680 passed** |
| Linux | Debian 13 WSL2, Python 3.13.5 | **680 passed** |

Additional checks:

- editable installation succeeded on both platforms
- source compilation succeeded
- live command help and fail-closed authorization paths succeeded
- API boundary tests used injected HTTP responses; no external request ran
- whitespace validation passed

## 7. Compatibility

- Existing Task Packet, Handoff, Scope, and ledger schemas remain readable.
- Council Review 0.1 retains version-aware hash verification.
- New Provider Runs use `provider-run/0.2.0`.
- Existing v0.1 workspaces remain readable. Newly created workspaces record
  `bootstrap_version: 0.2.0`.
- No migration writes to existing workspaces or Komistry OS.

## 8. Phase boundary

This release completes the CONCLAVE integration foundation. It does not begin
Phase 1B. The Phase 1B P1–P4 preconditions and P5 resolution or explicit
deferral remain governed separately by the canonical authoring plan.
