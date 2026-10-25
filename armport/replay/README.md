## Current acceptance (2026-10-24)

PR #6 comment 6385679120 supersedes the older process-wide game-error rule below.
`receiver.c` writes indexed replay.dispatch.begin/end to the isolated zone log.
All 117 paired ordered windows and the final loader drain must contain zero errors.
Before replay.map.end the driver drains static-map background work with
forceGeoLoaderToComplete() and texForceTexLoaderToComplete(0), keeping its
errors in the map-load phase. After dispatch 116 it calls those functions again:
forceGeoLoaderToComplete(), then
texForceTexLoaderToComplete(0), inside replay.drain.begin/end. Both drains run
the original texCheckThreadLoader and loadUpdate, including GL texture uploads
under Xvfb. These are explicit driver steps, not captured packets. Inter-dispatch
gaps also remain in dispatch phase. Each isolated record has a separate thread
ID; IDs never enter literal message comparisons. Startup/load inventories
must match literally with counts across all six executions; compare_state.py
checks this before partial state comparisons. Wine exceptions, assertions,
fatals, malformed traces and missing stdio error/fatal markers remain fatal.
The isolated inventory reports phases and the diagnostic resolves texture names
against actual staged files; group names remain symbolic references. No new
assets or message normalization are introduced. Full state coverage is still
incomplete and no milestone flag is set by these checks.

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
full entity/player dump. The follow-ups below add inventories, groups, badges,
world and retained costumes, but complete player tail, tasks/UI game-command
state, power activation/recharge, supergroups, NPC costume customization and
other receiver fields remain to be covered. Timer/interpolation fields,
rendering quaternions, pointers, struct padding and asset addresses are excluded.
All completion flags remain false and successful execution still exits 2.
After the terminal result, `replay.cleanup.begin` precedes CloseHandle/free,
and `replay.exit.begin` precedes ExitProcess(2). These are diagnostic witnesses
for the unexplained SIGKILL in run 40118399218; neither permits another exit
code or rescues an incomplete/failed transcript.

The host requires 117 authenticated snapshots. The follow-up comparison
reads one pair at a time, compares same-ID repeats and cross-architecture
files byte-for-byte, and only for ID1/31 applies Claude's five explicitly named field
normalizations (review 5638209554): pkt_id_create, lastClientStatePktId,
delete-history pkt_id, each pkt_id_pos[] and pkt_id_qrot[] element. Only
values equal to that run's synthetic INITIAL ID change; later IDs remain
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
Run 40092531364 at 0296f2fb writes all 117 ARM64 snapshots, then rejects
the native costume subset: it compared 60 allocated slots with 28 logical
parts. The corrected check uses costume.num_parts and retains all slots in
the literal dump. It does not weaken snapshot comparison. See M3-REPORT.md
for the subsequent review fixes and newly inventoried game errors.

### Review 5638209554 follow-up

Both receiver.c and state.c now unbind the three CRT formatting macros after
all game headers. Actual preprocessing plus old-macro negative controls cover
both translation units on ARM64 and i686. Both updated Game links pass; the
local host suite passes 46 tests (`python3 -m unittest discover -s armport/tests -v`).
The two architectures both enable client.error traces (patch 0060, exported
through patchwork.py). Acceptance requires zero game errors/asserts as well as
zero Wine exceptions. The original mixed stdio inventory was lossy; review
5638301654 led to the isolated full-message log described below. No error
allowlist has been introduced.

CI now emits per-execution and comparison notices. A separately logged
seh-control.exe raises and handles 0xe0424242 under the installed Wine +seh;
the host requires its completion marker and real exception trace and must
reject that log. Both control executables link locally; actual Wine execution
remains pending. Pinned bins/Cg from run 40043254025 are copied to an exact-run
cache and retained for 90 days, before their original October 31 expiration.

### Review 5638301654: complete error evidence and data collisions

Code 0b42f7cf adds patch 0061, exported by patchwork.py. `ARMPORT_ZONE_LOG`
selects an independent Win32 append handle. One locked WriteFile stores each
complete ASCII-escaped JSON record; stderr keeps its bounded progress text.
The log reports write/allocation/size failures, which fail strict replay.
The i686 reference now honors ARMPORT_STDIO_LOG in WinMain and console setup,
matching ARM64: run 40094942235's i686 job 120875377664 otherwise produced no
client-stdio.txt. Both targets passed the real handled-SEH rejection control.

`client_errors.inventory` requires this isolated log for replay, retains the
full client.error/client.fatal text, and also rejects stdio assertions and
log-write failures. Legacy stdio grouping is explicitly incomplete. The
concurrent Wine regression writes 64 identical 8,191-byte multiline messages
from four threads and checks exact decoded content; local ARM64 compilation
and linking pass. Runtime execution is still required.

The separate error-comparison job runs after failed receiver jobs as well as
successful ones. It validates the same source commit, re-inventories both
isolated logs, reports shared and architecture-only errors, and lists shared
geometry paths absent from both actual staged runtimes. Existing geometry is
reported with path, byte count and SHA256, so a missing model in an existing
file cannot be classified as a missing file. This is a diagnostic only;
zero-error replay, full state comparison and M3 remain separate requirements.
No additional costume data has been selected or supplied.

The Atlas stage checks every retained file's size/hash against the repository
manifest. Runtime staging verifies case-insensitive collisions against
every earlier input layer, including shadowed paths, and rejects differing
bytes before copying the supplement.
The workflow reports collision counts. Data uses cache plus the original
pinned donor fallback; no further supplemental game-data artifacts are uploaded.

Local commands: `python3 -m unittest discover -s armport/tests -v` gives 57
passing tests; both OptDebug Game links exit 0 (`[18/18] Linking CXX executable
bin/CityOfHeroes.exe`). The standalone concurrent trace test links for ARM64.
The actual retained archive stage verifies 2,877 files / 309,655,940 bytes and
repository manifest SHA256 204a7f0da20cdbbb4ea8b8e2d9e9b5ebccfaa10d5213fff03bbb85cc7f9e3c86.
Run 40097455262 rejects both targets on 183,269 complete errors each. The
same-commit comparison reports 132,393 shared literal keys, 1,020 ARM64-only
and 999 i686-only spellings; 45 named geometry paths are absent from both
runtimes. A local casefold diagnostic matches every text/count, but acceptance
remains literal and zero-error. Patch 0062 initializes the dummy costume
Appearance whose optional prefix affects the suffix spelling. Run 40099922039
at 023fd0dd tests that correction. See M3-REPORT.md for hashes, the separate
Atlas pointer crash, patch 0063 controls, and the remaining data-source gate.
# Diagnostic series after dispatch data errors

The host collects id1-a, id1-b and id31 even when an execution has ordinary
dispatch data errors, provided exit 2 and all Wine/integrity/transcript/state
checks pass. Each such execution remains rejected and any rejection fails the
job. This collects six-run comparison evidence without enabling exceptions or
accepting replay. Crashes, fatal/assert, malformed evidence, wrong cursors and
snapshot failures still stop immediately. See `test_receiver_run_series.py`.

## Rejected-run snapshot diagnostic

`diagnose_state.py --root <extracted-root> --commit <source-sha> --output <json>`
can inspect hash-authenticated partial snapshots even when the process exited
incorrectly or only dispatch data errors rejected it. It verifies the existing
Wine/integrity/cursor/ACK/snapshot/native-subset checks and preserves return
codes, timeout flags and error counts. Its seven comparisons use the same
literal and five-field ID rules; all qualification/completion flags stay false.
This is separate from `compare_state.py` and is never an acceptance fallback.
Run 40170942751's retained snapshots match, but its SIGKILL remains rejected.

The normal replay process observer samples the existing complete exit marker
at 20 Hz. After observing it, up to 40 bounded `/proc/<pid>/task` stat/wchan
samples can locate a shutdown wait. It neither sends signals nor attaches a
debugger, and cannot identify a signal sender. Unavailable observations are
explicit. Wine/runtime qualification of this diagnostic is still pending.

## Additional partial power observations (2026-10-25)

The v1 partial snapshot now includes character.power_inventory: current and
all build power arrays, stable logical definition names, decoded scalar/F32
values, slotted/global/inventory boosts and inspirations. Array order, null
slots and every float bit are preserved. This is an additive partial schema;
all completeness flags remain false. No new synthetic-ID normalization is
introduced. Local power/boost timers and host-initialized creation timestamps
are excluded; activation/recharge/mode storage, generic inventories and other
tail destinations still need separate observation. Same-commit six-run equality
must be requalified after this change; earlier snapshots cannot prove it.

`ASAN_OPTIONS=detect_leaks=0 python3 armport/tests/receiver_power_state.py`
executes the actual serializer with host fixtures under ASan/UBSan. It tests
null slots, escaped identities, negative zero/NaN/subnormal/infinity bit
preservation, final array slots, timer exclusion, changed decoded charges and
bound rejection. Local LeakSanitizer alone is disabled because /proc tasks
are hidden. CI runs the same control with its default sanitizer settings.
Both actual state.c units compile (ARM64 then i686, one compiler); formatter
preprocessing retains CRT calls and rejects the old macro variant as before.
See evidence/m3-power-state-observations.json. Runtime pending.

Generic inventories are an additional partial observation in the same schema.
`receiver_inventory_state.py` exercises the actual writer against all five
array types, empty arrays, null entries/definitions, high unsigned amounts,
concept raw float patterns and a changed recipe count. Counts over 8192 reject.
Capacity totals are included; auction contents, inventions, team/task/UI and
other uncovered receive destinations are not thereby qualified. See
evidence/m3-generic-inventory-observations.json. Runtime pending.

Badge observations additionally retain all 4096 status words, 50 recent
indices/received timestamps and 10 monitor entries, plus client debug mode
and optional filenames. Received award times stay literal; localized text
and buttons are excluded. No new ID normalization. The actual writer's
`receiver_badge_state.py` sanitizer control checks final array slots, raw
unsigned words, null strings and mutation sensitivity. See
`../evidence/m3-badge-state-observations.json`; runtime pending and schema
still partial. Supergroup badge state remains uncovered.

Team/league observations retain active member order, IDs, names, on-map
flags, team reward fields, league leaders/locks, persistent map-name arrays
and taskforce/LFG flags. Counts must fit 8/48 original slots, backing arrays
must exist for nonzero counts, and fixed strings must terminate in storage.
`receiver_group_state.py` exercises actual writer behavior with null/empty
rosters, final slots, maximum strings, mutations and invalid storage. Unused
member tails and derived league UI rosters are explicitly not covered. See
`../evidence/m3-group-state-observations.json`; schema remains partial.

World observations include dynamic-group hp/repair values in original index
order and server sky indices/raw weight bits. The writer reads logical fields,
not bitfield storage or tracker pointers; render-volume overrides are excluded.
`receiver_world_state.py` checks raw NaN/negative-zero weights, hp/repair
mutations, empty state and invalid count/storage rejection. Evidence:
`../evidence/m3-world-state-observations.json`; runtime pending, still partial.

## Exact original-data texture exception (2026-10-25)

The default validator still rejects all dispatch data errors. The reference
workflow explicitly supplies `--original-texture-exception` to both execution
and partial comparison, under user decision PR #6 comment 6387467359.
`fixtures/original-data-errors.json` contains the sole literal occurrence:
HIPS_miniskirt_1 on FEM/HIPS texture 2, count 1 at dispatch index 1 (not after a
dispatch). The complete message is listed in M3-REPORT.md. A missing, changed,
additional or relocated occurrence rejects; other approved names are not
implicitly allowed. The policy verifies hashes of its archive and six-run proof.

The prerequisite run 40203125375 exits 2 in all six processes and has identical
literal occurrences and partial snapshots. Its jobs remain failed under their
then-active strict policy. Fresh execution is required. Each accepted occurrence
is printed in the replay notice; raw errors stay in evidence. All other rejection
rules and outside-error comparison remain. No full-state or M3 claim follows.

## Retained costume observations (2026-10-25)

Costume snapshots now include convertedScale, currentSuperColorSet and all six
SG color-selection arrays as named low/high U32 halves, not union storage bytes.
Player snapshots retain all ten costume slots, their null/order distinctions,
super and pending costumes, selected/stored/unlocked indices and mode flags.
The original costume_receive and receiveSGColorData destinations are read only.
Logical part count must fit the retained part array; the original 256-entry
output bound remains. Temporary editor colors, derived display/source/store
metadata and local deferred-costume clock deadlines remain excluded. NPC
customization, power customization and reward ownership are still coverage gaps.

The actual writer's ASan/UBSan control checks the final SG slot/high half,
all retained/null costume slots, raw float bits, source immutability, empty and
invalid counts, changed fields and timer/editor exclusion. Both native target
units compile sequentially; evidence/m3-costume-state-observations.json records
commands. Runtime qualification is pending; the current replay 40206484644
predates this observer. The schema remains partial and all completion flags false.

## Story observations (2026-10-25)

The story snapshot now retains story/key clue arrays (all six strings), server
souvenir UID/header/detail strings and visit-location names. Null items, empty
strings and original order remain distinct; counts are bounded to 8,192 and
the existing total output bound remains. Patch 0078 exposes only the original
server souvenir array through a build-guarded read-only accessor, used solely
by active replay snapshots. The player-created local-file array, UI formatting
and scroll/display caches are excluded. Contacts/tasks/waypoints and broader
state remain gaps. See evidence/m3-story-state-observations.json for sequential
native compilation and actual-writer/accessor sanitizer controls. Runtime
pending; schema remains partial.

## Contact and task observations (2026-10-25)

Task sets preserve nested order/nulls, identities, difficulty, full retained
strings, individual flags, received timeout/timezero U32 values and ordinary
location F32 bits. Received zowie fields are included; locally selected zowie
coordinates/indices, request clocks and SMF caches are excluded. Contact arrays
preserve strings, identities, individual flags, retained points after the
original clamp and received map/name/position. Resolved PNPC/entity objects and
local overhead-icon state remain excluded.

Patch 0079 copies raw alignment delay values to a replay-only observer while
preserving the original clock addition and packet-read order. Snapshots store
those five delays (null until observed), earned counts and four self-point counts;
absolute host-clock deadlines are excluded. Actual receiver-loop controls prove
inert-off behavior and unchanged reads/addition, including U32 wrap, while
clock changes do not change the raw-delay output. Counts/strings/output remain
bounded and ID normalization unchanged. See evidence/m3-contact-task-state-observations.json.
Runtime pending, schema partial, no full entity/player/UI or M3 claim.

### Retained groups, customization and initial player fields (2026-10-25 UTC)

Snapshots now include the retained destinations of entReceiveOtherSupergroupInfo:
entity group name/emblem/colors, item-of-power spaces, mission, ordered/null reward
tokens, recipes and special details. Received server times and U32 sentinel
counts stay literal. Internal SpecialDetail.bValid bookkeeping is excluded.
Supergroup roster/rank/stat/UI coverage is not claimed by this addition.

Active/owned power-customization lists and all ten player slots preserve nulls,
original retained order, stored/resolved logical names, token bytes and individual
RGBA U32 values. Original packet reads/receivers and ID normalization do not
change. Counts remain bounded to 8,192 and the existing 16 MiB snapshot limit
applies. Broader entity/player/tail/UI coverage remains incomplete.

Initial player observations also retain type/subtype/progress, hidden/skills,
feature-version bits, original power-set names/comment and every account-game
and pop-help U32 word. Chat/window/tray/keybind/options receivers remain gaps.

Evidence: `evidence/m3-retained-group-customization-controls.json`. Twelve actual
writer/observer sanitizer controls and 156 Python tests pass; state.c compiles
ARM64 then i686 with one compiler. Fixture structures/earrays do not qualify
native ABI; mission forwarding uses the separately tested original task writer.
Only local LeakSanitizer is disabled for /proc; CI uses normal sanitizer settings.
Runtime remains pending. Atlas 40217209151 and replay 40217209257 test 5d1d2da9,
which predates these new serializers. All full-schema/full-state/M3 flags remain
false. Existing native renderer 0080 and the review's host truncation fix are
unchanged by this independent replay coverage work.

### Player identity, rewards and combat observations (2026-10-25 UTC)

Snapshots now retain literal title fields/colors/badge, workshop name, entity
description/motto, both ordered/null player reward-token name/value lists, PvP
flags, all ten combat-monitor key/order pairs and character class/origin logical
names, combat level/modifier, location type and ally/gang/PvP fields. Receivers
and synthetic-ID normalization are unchanged. Player token timers remain
excluded: INITIAL receives them, but later receiveRewardToken initializes them
from the local clock. This mixed provenance needs a separate observer. Title
expiry, UI localization/caches and other entity/control/UI destinations remain
uncovered; full-schema/full-comparison/M3 flags stay false.

Evidence: `evidence/m3-player-character-identity-controls.json`. Actual writers
pass ASan/UBSan controls for null/order/final slots, mutation sensitivity, U32
bits, string/count/output bounds, source immutability and clock/address
exclusion. Native state.c compiles ARM64 then i686 with one compiler; 156 Python
tests pass. Host fixtures do not prove native ABI; only local LeakSanitizer is
disabled for the known /proc limitation. Runtime qualification is pending:
40220658755 tests preceding 8813b215, not these additions.

Replay 40217209257 at 5d1d2da9 passes both targets and comparisons; job
121249121432 explicitly reports partial_state_equal true and full-state/M3 false.
The SHA-256-verified ARM64 artifact 12608430696 identifies 18 game-command types
in id1-a and authenticates its 117 state hashes. The committed command inventory
`evidence/m3-observed-game-commands-40217209257.json` guides remaining coverage;
command execution counts alone do not establish destination-state coverage.
