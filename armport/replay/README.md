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
decode. See ../notes/M3-REPLAY-PLAN.md for the binding criteria. Only the two exact logical input files are now gzip test fixtures under
fixtures/; the enclosing report archive remains outside the repository.

## Executable CI stage

armport-reference.yml now builds ARM64 and i686 OptDebug in a sequential
matrix, capped at two compiler processes. Each target uses the app's pinned
Wine/FEX runtime, the reviewed asset ZIP and bins/ARB shaders from completed
run 40043254025 (no intervening data/schema/shader changes).
run_ci.py requires an unprivileged process in a fresh network namespace
containing only loopback, runs ID 1 twice and ID 31 once with separate Wine
prefixes, and retains JSONL and logs. Each full-update ACK is compared to
the incoming ID by the original packet reader. The host validates all
117 ordered dispatch metadata/cursor records and both ACK records, and
compares same-ID cursor/ACK output byte-for-byte. Full state equivalence
and cross-architecture state comparison remain incomplete.

A green job means only this cursor/ACK stage passed. The JSON result must
retain state_comparison_complete=false and m3_replay_complete=false.
Input/decoder failures, wrong process exit, timeouts, missing ACKs, partial
counts and cursor errors fail the job. Local host tests cover those output
rejection boundaries; runtime qualification awaits this workflow.

Validation commands: both OptDebug Game links (`ninja -j2 Game`) exited 0
after the ACK check, and the full Python unittest discovery passed 18 tests.
