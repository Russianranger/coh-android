# M3 replay method agreed with Claude

2026-10-23. Claude agreed in PR #6 review 5635319013. The input-envelope
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

Required comparison: build the same test entry point with the
ArmPort-patched i686 client and run the same files through it under Wine/FEX. Compare
deterministic decoded summaries and cursor boundaries with ARM64. If that
reference cannot be built, report the gap; changing this exit test requires
the user's approval. Compile i686 with `-msse2 -mfpmath=sse`.
This clang-built reference isolates pointer-width/architecture differences;
it is not independent of shared ArmPort patches or clang behavior. The
recorded native-android 32-bit INITIAL decode remains a separate required
comparison, to detect mistakes shared by both same-driver builds.

The approved conditions (review
https://github.com/Russianranger/coh-android/pull/6#pullrequestreview-5635319013):

- Inert without ARMPORT_REPLAY_DIR, guarded for aarch64/mingw and the i686
  reference. Run after normal startup; list any extra initialization calls.
- Verify the sink NetLink accepts pktSend/lnkBatchSend/netSendIdle while
  unconnected. Record outgoing CLIENTINP_ACK_FULL_UPDATE IDs and compare them.
- Dispatch below commGetStats; packet-loss/troubled-mode handling is outside
  replay coverage. INITIAL ID, ordered and ordered_id are synthetic.
- Require 117 dispatches, exact cursors, no overrun/error, unknown game command,
  assertion or unexpected SEH. Any padding allowance must come from metadata.
- Compare wire values (quantized integers and raw float bits), not interpolated
  state. Dump full entity/player state after INITIAL, packet 32 and packet 155;
  hash state after every record. Include svr_idx, id, type, name, pkt_id_create,
  raw position/orientation, costume-part hash and the player's tail state.
- List excluded timer/interpolation fields. Repeat ARM64 twice with identical
  output; same-ID ARM64/i686 comparisons must also match literally.
- For INITIAL ID 1/31 sensitivity only, apply the narrowly scoped
  canonicalization agreed in review 5635783793 below.

Method agreement is not approval to merge M3. The rendered Atlas screenshot,
replay results, final report and user's merge approval are still required.

## Socketless link preflight

Original netio_send.c checks `!link->socket` before raw batch I/O; pktSendDbg
frees and nulls an outgoing packet with no socket or NLT_NONE. netSendIdle
may construct a control ACK but routes it through that same discard path.
The new armport_replay_sink test calls these actual UtilitiesLib functions
with a zeroed link and both zero/nonzero ack_count. It compiles/links as an
ARM64 PE executable with llvm-mingw and `ninja -j2 armport_replay_sink`.
The libraries CI job runs it under the app Wine and emits a notice. Run 40041703285, libraries job 120714048504, passed and emitted:
`socketless replay sink: pktSend discards, netSendIdle/lnkBatchSend return`.
This preflight is not one of the 117 receiver dispatches.


## i686 reference build preparation

The reference-only toolchain enables COX_ARMPORT_REFERENCE_I686. It builds
the same Game/Common/UtilitiesLib sources with the same reduced SDK features
as ARM64, explicit `-msse2 -mfpmath=sse`, and Microsoft inline-assembly syntax.
Patch 0053 permits that opt-in build; normal i686/MSVC behavior is unchanged.
The intrinsic stand-in keeps real i686 CPUID and supplies its missing __nop;
0055 selects clang's existing vector-lane access rather than MSVC members.
Both targets disable NOVODEX, so original i686 PhysX/ragdoll receive paths
are outside this comparison. Real i686 CPUID sets sseAvailable whereas ARM64
reports no SSE; zOcclusion/frustum rendering paths therefore differ. This
is a recorded reference limitation, not a receiver-path equivalence claim.

Local Release `ninja -C coh-build-i686 -j2 Game` exited zero. `file` reports
`PE32 executable (GUI) Intel 80386, for MS Windows, 17 sections`. The original
clientcomm.c compiles in this target. The separate armport-reference workflow
builds it on ARM64, checks the receiver's actual compile flags and saves a
separate artifact; it does not qualify execution or replay equivalence.
Run 40043254232, reference-build job 120718968162, passed this build check.

0054 is limited to this reference: clang's local 32-bit SEH compilation fails
with undefined L__ehtable and parent_frame_offset labels. Three protected
bodies (volume exit, audio decode, disabled keep-memory experiment) remain,
but the reference does not recover their faults. Any such SEH must fail the
replay, consistent with its no-unexpected-SEH criterion. This is not equivalent
exception recovery; ARM64 and normal builds retain their original handlers.
The original keepMemoryThread call is already behind if(0), so removing
its local handler changes no active path. Volume-exit or audio faults must
be reported as replay failures, not recovered or omitted from the result.
No receive decoder is replaced. ARM64 pmotion.c, game.c, ogg_decode.c,
frustum_c.c and the intrinsic stand-in compile after these guarded changes.

## Agreed synthetic-ID sensitivity comparison

PR #6 review 5635783793 answers comment 6377175041. Keep raw IDs in every
full dump; require literal identity for same-ID repeats and ARM64/i686
comparisons. For the 1-versus-31 sensitivity comparison only, canonicalize
these ID-valued fields when they hold that run's synthetic INITIAL ID:

- entity pkt_id_create;
- lastClientStatePktId;
- delete-history pkt_id (entrecv.c addDelete).

Assert that no real post-READY record ID is below 32 (the inventory is
32–155), and list the canonicalized fields in the output. All other state,
including every later ID, must match exactly. Do not normalize arbitrary
integers that happen to equal 1 or 31. This rule is agreed but the receiver
driver and sensitivity execution remain outstanding.
