# Increment 13 — Live Provider Adapters and Execution Integrity

Status: **RELEASE VERIFIED — v0.2.0**

## 1. Purpose

Add real OpenAI, Claude, and Gemini execution boundaries without weakening
the frozen Phase 1A protocol, provider independence, human authority, or
Komistry OS isolation.

## 2. Implemented adapters

| CONCLAVE provider | Provider API | Transport identity | Credential |
|---|---|---|---|
| `adrian` / `openai` | OpenAI Responses API | `openai-responses-api` | `OPENAI_API_KEY` |
| `claude` | Anthropic Messages API | `anthropic-messages-api` | `ANTHROPIC_API_KEY` |
| `gemini` | Gemini `generateContent` | `gemini-generate-content-api` | `GEMINI_API_KEY` |

No model identifier or provider price is hard-coded. The operator supplies
the model at execution time. Provider-reported total input, cached input,
total output, and reasoning output are normalized into the existing token
accounting fields.

Credentials are read from environment variables at request time. They are
not written to prompts, Run Records, ledger entries, errors, or command
output.

## 3. D7 remains a hard gate

`conclave run live` requires a principal-authored
`egress-decision/0.1.0` policy. The command refuses before adapter execution
unless all of the following hold:

1. `allowed` is true.
2. `authority` exactly matches the workspace principal.
3. The adapter transport is listed.
4. Every Context Bundle classification is listed.
5. A non-empty decision reference is present.

CONCLAVE does not generate or approve this decision. Every Run Record seals
the authority and decision reference used for its request.

## 4. Corrected execution defects

1. Execution now loads and verifies the stored Task Packet.
2. The Task Packet reference must match both Context Bundle and Route Plan.
3. The verified Task Packet content hash must match the Context Bundle's
   `packet_content_hash`.
4. Stage `n` requires exactly one completed Run Record for every stage
   `0..n-1`, all bound to the same Route Plan and Task Packet.
5. Cumulative input and output ceilings remain route-wide.

These checks occur before the provider adapter is called.

## 5. Corrected reconciliation gap

Ledger reconciliation now discovers, verifies, and reconstructs missing
operational events for:

- Context Bundles
- Route Plans
- Provider Run Records

It continues to report unreadable or hash-invalid artifacts as unresolved
instead of attesting to them.

## 6. Verification

- Live provider boundary tests use injected HTTP responses; no real provider
  request is made.
- Provider endpoints, request shapes, credentials, response text, request
  identifiers, finish status, and token normalization are covered.
- Missing credentials and identity mismatches fail before HTTP.
- Live CLI authorization failure is verified to occur before adapter
  construction.
- Full Windows suite: **680 passed** on Python 3.12.10, 29 July 2026.
- Full Linux suite: **680 passed** on Debian 13 / Python 3.13.5,
  29 July 2026.

The canonical Phase 1B preconditions remain separate governance gates. Phase
1B has not begun.
