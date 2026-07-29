# Increment 11 — Run-to-Handoff Integration

Status: **FROZEN FOR IMPLEMENTATION**

## 1. Purpose

Convert a completed, sealed Provider Run into the existing sealed Handoff
Packet and immediately evaluate its declared object touches through the
existing Scope Review.

## 2. Admission rules

Conversion is refused unless:

- the Run Record verifies and has status `completed`;
- its Task Packet exists and verifies;
- its stored Route Plan verifies and cites the same Task Packet;
- provider, role, and stage index exactly match that Route Plan;
- the response contains exactly one valid Handoff submission, either as the
  adapter's structured output or as one fenced YAML block;
- packet reference, packet hash, provider, and role match the Run Record;
- all existing Handoff schema requirements pass.

The exact normalized provider response is preserved as the raw response. For
structured responses this is a canonical envelope containing both text and the
structured payload. The Handoff records the Run, Context Bundle, Route Plan,
and stage provenance.

## 3. Council compatibility boundary

The Handoff cites its exact Route Plan and stage. Stage-aware Council
aggregation is supplied by Increment 12.

## 4. Acceptance criteria

1. Budget-exceeded runs cannot become Handoffs.
2. Missing or mismatched route, stage, identity, role, or packet hash is refused.
3. Provider response text is preserved before Handoff construction.
4. Handoff provenance cites the exact Run, Context, Route, and stage.
5. Re-converting the same Run is idempotent.
6. Scope Review is created through the existing evaluator.
7. Existing Council behavior and all prior tests remain unchanged.
