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
receiver.jsonl and state-NNN.json are outputs for that run.

The driver uses the unchanged original receive switch below commGetStats,
preserves saved cursor/alignment/transport metadata, and requires exactly
117 successful dispatches with exact end cursors and no BitStream errors.
Unknown game commands fail explicitly even if a caller's assertions were
disabled. Actual CLIENTINP_ACK_FULL_UPDATE IDs are read back from the original
client_input_pak; this does not reconstruct a UDP ACK/READY envelope.

Extra initialization is limited to entReceiveInit (the original map-move
receive reset), commNewInputPak (per-record output isolation), and
setAssertMode (stderr plus exit), plus the original command shortcut table
and original static Atlas map prerequisites described below. The socketless
NetLink path is covered by
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

Partial wire-state dumps/hashes, same-ID and ARM64/i686 comparison, and the
agreed narrow ID1/31 canonicalization are implemented below (0059), with
execution under test in run 40091320504. Full entity/player/tail coverage and
complete qualification remain outstanding. The independent native INITIAL
comparison covers the boundaries and selected fields actually recorded; it
is not a full-state baseline. See ../notes/M3-REPLAY-PLAN.md for the binding criteria. Only the two exact logical input files are now gzip test fixtures under
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
compares same-ID cursor/ACK/state-hash output byte-for-byte. It also validates
117 snapshot digests and a recorded native INITIAL subset. The follow-up
comparison job checks both architectures and ID sensitivity for this partial
schema. Full state equivalence remains incomplete.

A green job means only its explicitly partial stage passed. The JSON result must
retain state_comparison_complete=false and m3_replay_complete=false.
Input/decoder failures, wrong process exit, timeouts, missing ACKs, partial
counts and cursor errors fail the job. Local host tests cover those output
rejection boundaries. Prior cursor-only execution passed in 40087788115;
0059 observer execution is being tested in 40091320504.

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

Run 40055978390, ARM64 job 120759128643, passes the shortcut-dependent
header and character receive phases with zero stream errors, then asserts
in groupdynrecv.c:24: dyn_group_count_from_server == dyn_group_count.
Artifact 12545547444 (SHA-256
a7db082751013cabbeba2eafb7d729adb8ec50f17dc8d0f67e0700b8e16e81d0)
records the last boundary as groupDynReceive at bit 300128. INITIAL has not
completed. The harness had no world roots because the saved files omit the
earlier SERVER_GROUPS message as well as the shortcut message.

The driver now calls clientLoadMapStart, groupLoadFull and
groupDynBuildBreakableList for maps/City_Zones/City_01_01/City_01_01.txt,
the static Atlas map used by the server (40042636088 first-dbserver-stdout).
It requires an initially empty world and nonempty roots after loading, and
records root/dynamic-group counts. This reconstructs local static-map
initialization from the same data, not the omitted server-group payload.
The original receive assertion remains intact and no synthetic group count,
breakable object or packet byte is substituted. No rendered-map completion
is claimed by this load. Both local OptDebug Game links (`ninja -j2 Game`)
pass with this prerequisite; runtime qualification remains pending.

Run 40057090615 (1c91081d), ARM64 job 120762415670 and i686 job
120762415580, passes all 117 cursor/ACK checks for ID1-a, ID1-b and ID31.
Native INITIAL command boundaries match. Both completion flags remain false;
this is not full receiver-state equivalence. The prerequisite fixes and
review 5636418576 fatal-Wine-log rejection are now integrated into M3.

## Partial state capture (0059)

The new replay-only observer retains accepted 9-bit quaternion components
before unpacking/normalization, keyed by server index and entity generation.
Normal gameplay does not enable it. The original decoder consumes exactly
the same nine bits, applies its same stale-packet decision and calls the same
unpacker. A read-only visitor exposes actual delete history in index order.
All original-source edits were exported with patchwork.py as patch 0059.

Each successful dispatch now writes state-NNN.json (16 MiB maximum) and its
SHA-256. Server indices are ordered; strings preserve source bytes with JSON
escapes; attribute floats use raw 32-bit representations. Included fields:
identity/name/type, raw network positions, observed wire quaternion values
(null where not observed), packet ordering IDs, selected costume appearance
and parts, character levels/xp/debt/rest/influence/current and maximum
attributes, player lastClientStatePktId, and actual delete history.

This is explicitly schema armport-receiver-state-v1-partial. It is NOT a
full entity/player dump: power sets, inventory, complete player tail,
teams/tasks/UI game-command state, dynamic groups, further costume metadata
and other receiver fields remain to be covered. Timer/interpolation fields,
rendering quaternions, pointers, struct padding and asset addresses are excluded.
All completion flags remain false and successful execution still exits 2.

The host requires 117 authenticated snapshots. The follow-up comparison
reads one pair at a time, compares same-ID repeats and cross-architecture
files byte-for-byte, and only for ID1/31 applies Claude's three agreed field
normalizations. All other fields, including pkt_id_pos and pkt_id_qrot, remain
literal. Differences fail this partial stage and are reported, not normalized
away. Passing this stage still cannot complete M3.

The recovered native report archive SHA256 is
623800b22640bb0f35a27bbf89bae04253c5acf9e1db10b0365084b0dd7def82;
native-client-report.json SHA256 is
2876eb9b504614fad1de03adf4fa9eff82cfee3f56e9446e68d4d14afb217016.
The native-initial-entity.json fixture records only its explicitly reported
entity index 125, type 2, costume bodytype 4 and part count 28. Field mapping
comes from world_handoff.first_create and OUTER_COSTUME_ARGS in the frozen
native-android interop_network.c. These checks complement the existing tail
boundaries; they do not claim that the truncated report contains full state.

Local validation on 2026-10-24: `python3 -m unittest discover -s armport/tests
-v` passed 41 tests, including a self-consistent changed final snapshot that
must fail comparison. `CMAKE_BUILD_PARALLEL_LEVEL=2 cmake --build
../build-arm-new --target Game` and the same command for `../build-i686-new`
both exited 0 and linked CityOfHeroes.exe. Workflow YAML parsed and
`git diff --check` passed. Full replay execution with this observer is pending;
the previous cursor-only execution passed at 563e49ac in run 40087788115.

### Snapshot formatter regression found by execution

Run 40091320504 at 1e6952ed, ARM64 job 120864480058, reaches INITIAL cursor
303248 and ACK ID 1, then exits 3 before writing its first state file.
Artifact 12558638797 (API/download SHA256
ab44ec03a6ad42faaba6528dfc7215fdc50130d22fd7b7e13d74eddebdbb773b)
records an assertion in quick_sprintf.c:101, `(size_t)(tail-buf+1) <= buf_size`.
This is an observer-output failure, not a completed state comparison.

The included stdtypes.h macros replace vsnprintf/snprintf/sprintf with
ARRAY_SIZE_CHECKED wrappers. The snapshot writer passes heap-buffer offsets,
so that inferred size is only a pointer width. state.c now undefines those
three macros after all game headers, preserving its explicit 16 MiB remaining
capacity checks and CRT formatting. Check failures also emit the failed
condition/line through WriteFile before exit 3. No original decoder changes.

`check_receiver_state_preprocess.py` uses the actual compile commands. For
ARM64 and i686, its current control finds CRT vsnprintf/snprintf/sprintf;
removing only the three undef directives reproduces all three quick_ calls.
Both controls pass for both targets and both updated OptDebug Game links
exit 0. The reference workflow runs this control before a new client build.
Run 40092531364 at 0296f2fb tests the corrected observer; execution evidence
is still pending; all complete flags
remain false and the previous failing run is retained as evidence.
