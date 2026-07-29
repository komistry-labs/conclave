# Increment 12 — Stage-Aware Council

Status: **FROZEN FOR IMPLEMENTATION**

## 1. Purpose

Allow Council Review to use a sealed Route Plan as its expected-participant
authority while preserving the original Task-Packet-assignment behavior when
no route is supplied.

## 2. Frozen behavior

- `conclave council review` without `--route` is unchanged.
- With `--route`, expected submissions are route stages, not static provider
  assignments.
- A stage identity is `(stage_index, provider, role)`.
- Only Handoffs citing the exact Route Plan hash and stage identity are
  eligible.
- Multiple stages may use the same provider without one submission
  superseding another.
- Repeated submissions for the same stage retain the existing latest-import
  and ambiguity rules.
- Structural comparison labels participants by stage, provider, and role.
- The Route Plan hash is sealed into the Council Review and its identifier.
- Human decision remains mandatory and the decision block remains empty.

## 3. Compatibility

New reviews use `council-review/0.2.0`. The reader retains version-aware
canonicalization for `council-review/0.1.0`, so historical artifacts verify
without inserting new fields into their hashed body. Existing commands and
static-assignment reviews retain their original interpretation.

## 4. Acceptance criteria

1. Static Council behavior is unchanged without a route.
2. Route-bound Council derives exactly one expectation per route stage.
3. Same-provider submissions in different stages remain distinct.
4. Wrong-route or wrong-stage Handoffs cannot satisfy an expectation.
5. Route hash changes Council identity.
6. Decision authority remains human-only.
