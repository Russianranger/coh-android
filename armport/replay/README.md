# Original receiver replay: execution stage under development

`receiver.c` is linked into ARM64 and the opt-in i686 reference. Patch 0056,
exported through patchwork.py, calls it only after normal game_beforeLoop
startup. Without ARMPORT_REPLAY_DIR it immediately returns.

The opt-in requires an OptDebug executable so original assertions remain
active. It rejects FINAL/Release, any live server connection, different input
file sizes or SHA-256 identities, and any synthetic INITIAL ID except 1/31.
Place the recovered initial-replay.bin and post-ready-replay.bin in the
directory named by ARMPORT_REPLAY_DIR (a Wine-visible Windows path).
ARMPORT_REPLAY_INITIAL_ID defaults to 1. Every run needs a fresh directory:
receiver.jsonl is the output for that run.

The driver uses the unchanged original receive switch below commGetStats,
preserves saved cursor/alignment/transport metadata, and requires exactly
117 successful dispatches with exact end cursors and no BitStream errors.
Unknown game commands fail explicitly even if a caller's assertions were
disabled. Actual CLIENTINP_ACK_FULL_UPDATE IDs are read back from the original
client_input_pak; this does not reconstruct a UDP ACK/READY envelope.

Extra initialization is limited to entReceiveInit (the original map-move
receive reset), commNewInputPak (per-record output isolation), and
setAssertMode (stderr plus exit). The socketless NetLink path is covered by
the existing original-network preflight, CI 40041703285 libraries.
Input BitStream fields are initialized directly: initBitStream zeros the
first four payload bytes even in Read mode, so calling it on captured bytes
would corrupt the input. Packet ownership stays local; the original pool
does not free these stack Packet views.

This is not the completed replay exit test. The first execution stage emits
`state_comparison_complete: false` and `m3_replay_complete: false`, and exits
**2 even after all 117 cursors pass**. Malformed input, decoder failure or
unknown command exits 3. Assertions and unexpected SEH also invalidate a run.
No completed receiver run is claimed by merely compiling this driver.

Remaining before M3: full entity/player tail state dumps and per-record state
hashes; wire-orientation capture rather than normalized rendering quaternions;
literal ARM64/i686 and same-ID repeat comparison; the agreed narrow ID 1/31
canonicalization; and comparison against the recorded native-android INITIAL
decode. See ../notes/M3-REPLAY-PLAN.md for the binding criteria. The raw report
archive and replay files have not been added to the repository.
