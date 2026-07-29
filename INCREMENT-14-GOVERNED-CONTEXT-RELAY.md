# Increment 14 — Governed Context Bundle Manual Relay

Status: **RELEASE VERIFIED — v0.3.0**

## Defect demonstrated

D7 correctly refuses constitutional context on the live provider adapters.
The existing manual relay prompt, however, projected only the Task Packet. It
did not bind or project the sealed Context Bundle and Route Plan used by the
provider-execution workflow. A constitutional task therefore had no auditable,
provider-independent path from its governed source set to a manually relayed
prompt.

This was a runtime integration defect, not a reason to weaken D7.

## Resolution

`conclave relay export-context` now creates one local manual-relay prompt for
one frozen route stage. Before writing anything it verifies:

- the Task Packet content hash;
- the common Task Packet reference across packet, context, and route;
- the Context Bundle's recorded Task Packet hash;
- the requested route-stage index; and
- that the route provider is assigned to the Task Packet.

The exported prompt includes:

- the full Task Packet projection and response contract;
- the complete sealed Context Bundle, including every source's provenance,
  classification, content hash, and exact content;
- the Context Bundle and Route Plan hashes;
- the stage index, provider, and route role; and
- the operator-authored instruction.

The prompt and its YAML manifest are canonical UTF-8/LF artifacts under
`relay/outbox/context/`. The manifest is hash-sealed and the prompt hash is
verified whenever it is read. A retry with identical inputs is idempotent; a
differing prompt at the same governed identity is refused.

## Independence and egress

Export is entirely local and invokes no provider adapter, HTTP client, browser,
clipboard, or provider API. It includes no provider response and instructs the
operator not to add one. One stage is exported at a time, so a provider sees
only the prompt prepared for its named role.

Manual delivery remains an operator action. This increment does not alter D7,
authorize live constitutional egress, or create provider credentials.

## Evidence and recovery

The sealed manifest is accepted as Handoff provenance and records:

- Task Packet reference and hash;
- Context Bundle hash;
- Route Plan hash;
- stage index;
- provider and role;
- prompt filename and hash; and
- export timestamp and manifest content hash.

The ledger event is `context_relay_prompt_exported`. If the artifact is written
but the ledger append fails, `conclave ledger reconcile` reconstructs the event
from the verified manifest without inventing a timestamp or decision.

## Authority boundary

This increment prepares and records advisory work. It cannot approve, ratify,
commission, merge, modify KOS, or call a provider on Arthur's behalf.

## Verification

- Windows, Python 3.12: **689 passed**
- Debian 13 under WSL2, Python 3.13: **689 passed**
- canonical UTF-8/LF check: **passed**
- Git whitespace check: **passed**
- live provider calls during verification: **none**
