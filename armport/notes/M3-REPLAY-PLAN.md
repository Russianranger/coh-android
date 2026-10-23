# M3 replay method for Claude's review

2026-10-23. Proposal only: HANDOFF section 5 requires reviewer agreement
before implementing the original receive-code driver. The input-envelope
validator is implemented; it does not execute a game decoder or satisfy M3.

## Verified input

Command:

```
python3 armport/scripts/replay_inventory.py initial-replay.bin post-ready-replay.bin
```

Complete scalar output: `armport/evidence/m3-replay-inventory.json`.
The exact report archive and file hashes are in `M3-LOAD-STALL.md`.
The validator checks bounded framing, every payload hash, the archive prefix
hash, counters, completion, bit cursors and byte-alignment metadata against
the original capture formats. It preserves the original bytes.

- INITIAL: 303,248 logical bits, post-command cursor 32, appearance cursor
  1,848. The envelope contains no transport packet ID.
- Post-READY: 116 records, 61,264 payload bytes, 490,086 logical bits;
  one command 3 (`SERVER_ALLENTS`), then 115 command 2 (`SERVER_UPDATE`).
  Packet IDs, ordered IDs, bit cursors and alignment are present. The first
  snapshot has packet ID 32; the final update has ID 155.
- These are decoded logical-message payloads, not encrypted UDP datagrams.

## Proposed execution

Add a test-only entry point in the original client through patchwork. Use
the client's normal data and entity initialization, then wrap the existing
`commHandleMessage(Packet *, int, NetLink *)` in `clientcomm.c`. Dispatch the
captured command at the saved post-command cursor, preserving payload bytes,
logical bit length, alignment, packet ID, ordered flag and ordered ID.

The existing `SERVER_ALLENTS` path reads the full-update ACK ID, queues its
ACK, calls `entReceiveUpdate`, and dispatches the remaining game commands.
Use a harness-owned local link to capture those sends without communicating
with the user's server. Do not replace the entity, costume or game-command
decoders. Do not substitute a standalone costume-only decode.

Run INITIAL first, then every post-READY record in saved order. Because the
INITIAL envelope omits its packet ID, propose an explicit synthetic ID 1,
reported as synthetic in every result. Repeat with ID 31 to check whether
this missing metadata affects the later captured sequence. This is not a
claim to reproduce the missing original transport ID. Entity receive code
uses packet IDs for stale-update and entity lifecycle decisions, so this
assumption needs review.

For each dispatch record the consumed bit cursor, overrun/error state,
handled-command result and deterministic entity/player summary (IDs,
positions, costume identity and selected tail state). Require every supplied
payload to reach its exact logical end without overrun or an unhandled
command. Preserve full outputs as CI evidence. Count every dispatched record;
do not pass after only INITIAL or the first snapshot.

## Comparison and review decisions

The native-android report records a complete INITIAL tail decode for this
303,248-bit capture; compare the fields and command boundaries that it
actually records. Its post-READY body coverage was opaque, so that report
cannot supply an existing decoded baseline for all 115 updates. The older
301,656/303,112-bit captures are different inputs.

Preferred additional comparison: build the same test entry point with the
original i686 client and run the same files through it under Wine/FEX. Compare
deterministic decoded summaries and cursor boundaries with ARM64. If that
reference cannot be built, report the gap and obtain explicit agreement on
the narrower comparison before calling replay complete.

Claude: please review (1) the wrapper and initialization approach,
(2) synthetic INITIAL ID 1 plus ID 31 sensitivity run, (3) required i686
comparison versus the recorded INITIAL-only baseline, and (4) exact EOF and
decoded-state assertions. Agreement on this method does not approve an M3
merge. Atlas rendering remains independently blocked in `texLoadQueueFinish`
in CI run 40011219458; run 40032719161 adds finer queue diagnostics.
