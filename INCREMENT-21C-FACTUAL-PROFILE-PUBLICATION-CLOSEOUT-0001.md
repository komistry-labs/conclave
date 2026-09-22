# Stage 21C factual profile — publication closeout 0001 (PR #26)

Date: 2026-09-23
Recorded by: Claude (Claude Code session). Records facts reported by the
operator and those independently verified; confers no authority.

## 1. Authority and execution

Arthur authorized a one-time review-count exception for PR #26 only
(2026-09-22). The Claude Code session was blocked from performing it by its
permission check; Arthur directed Adrian (Codex) to execute it under
`handoffs/CODEX-PR26-MERGE-INSTRUCTION.md`.

## 2. Merge facts

| Fact | Value | Source |
|---|---|---|
| PR | #26 "Adopt Stage 21C factual PR assistant profile" | GitHub, verified |
| State | MERGED at 2026-09-22T07:23:43Z | GitHub, verified |
| Merge commit | `276b0f708f124e0a242b66db1167e4699ae84575` | GitHub, verified |
| Tree | `6af1f2b1f44443e348b52d381e85d47f8a509a33` | GitHub, verified |
| Parents | `154394c570a9919fc00b7c00779f565f742508e2`, then `d5caadc391ddd83deda7794100d85ac9e84fe300` | GitHub, verified |
| Merge tree equals PR head tree | yes | verified (`git diff d5caadc 276b0f7` empty) |
| Adopted profile on `main` | SHA-256 `ed45fb9f2e1dfc8d8e9f542d71b8e67678aafe1d99120f209f5cb3b1891ab962` | verified |
| Post-merge run | `35699382510`: success — Windows/Py3.12, Ubuntu/Py3.12, Ubuntu/Py3.13, macOS/Py3.12 | GitHub, verified |
| Conformance artifacts | 4 published, none expired | GitHub, verified |

## 3. Protection

| Fact | Value | Source |
|---|---|---|
| Review count during window | 1 → 0 → restored to 1 | operator report |
| Before/after protection snapshot SHA-256 | `c268471348b1c8b3f9e426b56b5caa449bef6399e8d191145bfdcec0d09a2860`, byte-identical | operator report |
| Current protection | review count 1; administrator enforcement on; strict checks on; conversation resolution on; force pushes off; deletions off | verified |
| Merge attempts | exactly one; no other merge in the window | operator report |

The before snapshot was taken by the operator; the coordinator cannot
reproduce its hash, only confirm the current settings hold every expected value.

## 4. Operator note

After the successful merge, a local evidence-logging error occurred because
`gh pr merge` returned no output and a null was written. The guaranteed
restoration had already completed; the merge was not retried; read-only
verification completed. No GitHub-side correction was required.

## 5. Disposition

The adopted factual profile, its accepted Council review, the issued adoption
record and the governance trail are on protected `main`. This record is carried
with the fixture-only implementation branch; it authorizes nothing.
