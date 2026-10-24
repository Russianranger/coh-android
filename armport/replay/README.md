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
setAssertMode (stderr plus exit), plus the original command shortcut table
prerequisite described below. The socketless NetLink path is covered by
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

The first attempt (40053724746, ARM64 job 120751905102) failed before Wine
launch: /sys/class/net still reflected the host's sysfs mount after unshare.
The harness now queries netlink with ip -j link show and requires only lo;
it also compares /proc/self/ns/net with the host namespace captured before
unshare. Neither isolation requirement is removed. Local unshare is denied
by this workspace, so the corrected namespace execution is CI-only.
The output checker still passes its five rejection tests and py_compile.

Replay-host/fixture-only changes no longer restart the Atlas build; the
reference workflow owns their checks. Receiver C/patch changes still restart
both. Executables are cached immediately after successful build so a later
replay failure does not force another unchanged compile.

Review 5636418576 identified that a valid JSONL transcript could conceal a
fatal Wine log. The acceptance function now requires the game Wine log and
rejects handled or unhandled SEH dispatches and fatal/loader failures before
checking JSONL. Bootstrap/registry output is retained separately; the game
has no exception allowlist, including during startup. The command
`python3 -m unittest discover -s armport/tests -p 'test_*.py' -v` passes 26
tests, including complete-transcript/fatal-log and handled-SEH counterexamples,
missing Wine evidence and separate bootstrap output. This closes the host
validator gap; it does not assert that the live receiver has no exceptions.

## First original-receiver execution

Run 40054327124, ARM64 job 120753892218, entered INITIAL and exited 3 on the
original BitStream.c:308 read-overrun assertion. Artifact 12544733343 was
downloaded and verified against SHA-256
2f72d1d96b2b53ef5e4b08ebcc25e1089627cd2ee240f696bb500f2f3895d82c.
It contains dispatch_begin index 0 but no completed dispatch. No cursor pass.

Source inspection found a missing harness prerequisite: the capture begins
after SERVER_CMDSHORTCUTS, but game_beforeLoop has no shortcut names installed.
cmdOldReceivePacked returns on an unknown shortcut without consuming its
arguments, which misaligns the rest of INITIAL. The captured first shortcut
is ID 26; the original cmdOldServerInitShortcuts puts control_cmds first
(25 entries), then server_visible_cmds (10), with ID 26 named time.
The driver now seeds those original shared tables with cmdOldSetShortcut,
logs every ID/name, and refuses an unexpected preexisting table or a changed
count/name. This is a reconstructed initialization prerequisite, not replay
of the missing handshake message. No receive body or captured byte is changed.
Both local OptDebug Game links (`ninja -j2 Game`) pass after this change.
Its runtime effect still requires a fresh replay run.

The armport/replay-* development branch runs the same reference workflow
without restarting the milestone branch's Atlas workflow. Changes return
through a normal merge; no milestone criteria or history are rewritten.

That first branch run (40055381560, ARM64 job 120757110347) linked the client
but stopped before execution because Actions caches are branch-scoped. The
reference workflow now has the same reviewed-asset download/cache job as the
milestone workflow; its matrix waits for that job and still verifies the ZIP
hash before unpacking. No server/runtime result came from this failed attempt.

Patch 0058 adds inert replay-only cursor observations around the original
receive phases and game commands. It neither reads extra packet bits nor
changes decoded state. The host compares INITIAL's entity-tail boundary
(300328), final cursor (303248), eleven tail commands and zero terminator
against the recorded native-android report's exact capture. The small frozen
baseline records the source/report/input hashes; it does not invent a
post-READY baseline. This boundary comparison is only part of the required
independent INITIAL check, not full entity/player-state equivalence.

After 0058, both ARM64 and i686 OptDebug Game links pass, all 29 host tests
pass, and workflow YAML/compiler/matrix/data-dependency checks pass. Full
state dumping/hashing and cross-architecture comparison remain unfinished.
