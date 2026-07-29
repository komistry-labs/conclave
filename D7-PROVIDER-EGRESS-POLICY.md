# D7 — Provider Egress Policy

| Field | Decision |
|---|---|
| Decision reference | `D7-PROVIDER-EGRESS-v1` |
| Authority | Arthur |
| Effective date | 29 July 2026 |
| Status | Active |

## Decision

CONCLAVE may send sealed Context Bundles classified `public` or `internal`
through the following live provider transports:

- `openai-responses-api`
- `anthropic-messages-api`
- `gemini-generate-content-api`

Context classified `restricted` or `constitutional` is prohibited from live
provider APIs. Those classifications remain relay-only and require Arthur to
control the disclosure directly.

The machine-readable policy is
`policies/D7-PROVIDER-EGRESS-v1.yaml`.

## Conditions

1. A live request must still pass Task Packet, Context Bundle, Route Plan,
   stage-order, classification, transport, and cumulative token-budget checks.
2. API credentials remain process-environment inputs and must not be written
   to CONCLAVE artifacts, logs, prompts, or error messages.
3. Provider outputs remain advisory. They must pass the existing Run Record,
   Handoff, Scope Review, and Council Review workflow before human decision.
4. Providers remain isolated. One provider does not receive another
   provider's prompt, response, or private reasoning unless Arthur creates a
   later explicit authorization.
5. This decision authorizes the transport boundary only. It does not
   authorize a particular task, approve an output, modify Komistry OS, or
   begin Phase 1B.
6. CONCLAVE must not silently broaden this policy. Adding a classification or
   transport requires a new principal-authored decision reference.

## Recorded consequence

This resolves D7 from the bootstrap integration plan. Live adapters may be
used for `public` and `internal` context after the normal task-specific
governance checks pass. Constitutional and restricted context cannot reach
those adapters under this decision.
