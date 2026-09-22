# Stage 21C Factual Profile — Arthur decision capture 0002

Date received: 2026-09-22
Recorded by: Claude (Claude Code session), coordinator. Capture only.

## 1. Arthur's text, verbatim

```text
issue
```

## 2. Context

Given in reply to the coordinator's question whether to issue the adoption record
bound to candidate
`ed45fb9f2e1dfc8d8e9f542d71b8e67678aafe1d99120f209f5cb3b1891ab962` and Council
review 0006 (`47134e0f…cb28010e`, 5/5 PASS_EXACT_DRAFT). This is the
confirmation of the exact bound hash that decision capture 0001 §4 required
before its ISSUE intent could take effect.

## 3. Effect as applied

- `decision` set to `ISSUE`.
- `date` set to `2026-09-22`, the date of Arthur's reply; Arthur supplied no
  other date.
- Status line set to `ISSUED BY ARTHUR 2026-09-22 / IN EFFECT`.

Immediately before applying, the coordinator re-verified that the candidate,
review 0006, the bound record and the reviewed draft were byte-identical to the
values the record binds. After applying, the issued record differs from the
reviewed draft (`f3046039…`) only in the Status line, the §2 bound values and the
§9 JSON values, as its §9 permits.

By the record's §7, issuance freezes and adopts the bound object only. It
authorizes no commit, push, PR, merge, implementation, credential use, live
operation, Stage 21D, production, KOS or IDM change. The next governed gate
(record §8) is Arthur's authorization naming the governance payload and its
destination for commit and publication. Arthur has not yet given it.
