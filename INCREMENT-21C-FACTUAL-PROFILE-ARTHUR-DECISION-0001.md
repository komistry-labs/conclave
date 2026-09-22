# Stage 21C Factual Profile — Arthur decision capture 0001

Date received: 2026-09-21
Recorded by: Claude (Claude Code session), coordinator. Capture only; this
record confers nothing beyond what Arthur's text states.

## 1. Arthur's text, verbatim

Preserved exactly as received, including its template brackets and syntax
errors. Not reformatted into valid JSON, so that no interpretation is embedded
in the preserved bytes.

```text
{
  "arthur_decision": {
    "decision": "<ISSUE>"
    "date": "<2026-09-21>",
    "adopted_object_sha256": "<must equal §2>",
    "accepted_council_revi"<file and SHA-256>",
    "council_standard_accepted": "<five same-provider seats acceptable>"
  }
}
```

## 2. What is established

| Field | Reading | Status |
|---|---|---|
| decision | ISSUE | Intent recorded |
| date | 2026-09-21 | Recorded |
| council_standard_accepted | five same-provider seats acceptable | **Determined** |
| adopted_object_sha256 | template placeholder, unbound | **Open** |
| accepted_council_review | template placeholder, truncated key | **Open** |

**Council standard — determined.** Arthur accepts five same-provider subagent
seats as satisfying the five-seat requirement of Erratum 0001 freeze record §6.
This resolves the provenance question carried by Council reviews 0001 and 0002
and is not conditional on any later event.

## 3. Why the issuance is not yet effective

The draft adoption record (`7ce3e3b9…`) §2 requires that its binding values be
"those of the exact bytes that received the Council review Arthur accepts", and
§9 states that until completed the record has no effect. No Council has reviewed
candidate `d0718db3…`; the most recent review (0002) failed its predecessor
`84c0b1e3…`. The two binding fields therefore cannot be completed, and were not.

The coordinator has not bound them on Arthur's behalf. Doing so before a review
returns would adopt unreviewed bytes, contrary to Arthur's direction that five
Council seats review before freeze, and would let a Council tally stand in for
Arthur's act, which every Council record in this lineage disclaims.

## 4. Path to effect

1. Round 3 reviews candidate `d0718db3…` under the determined standard.
2. If it returns 5/5 PASS_EXACT_DRAFT, the coordinator prepares the adoption
   record with §2 and §9 bound to those exact bytes and that review, and returns
   it to Arthur.
3. Arthur confirms the two bound values. Only then does the record take effect.

If round 3 does not pass, the ISSUE intent carries no effect for any later
candidate without Arthur's confirmation of that candidate's exact hash.
