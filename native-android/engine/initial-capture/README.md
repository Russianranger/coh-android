# Nonshipping initial packet capture

These translation units replace ordinary Map/Local objects in a separately
built diagnostic executable. They include the ordinary `.c` files unchanged.
No default CMake/Gradle/JNI/workflow registration exists. Compile
`coh_initial_map.c` and `coh_initial_local.c` instead of
`mapclient/coh_mapclient.c` and `local/coh_local.c`; retain the ordinary strong
Map owned-handoff bridge, DB, replication, network, auth and protocol objects.

The opaque capture owns Local, so callers cannot inject a Map pointer, handoff,
DBID, schema or scene-count assertion. It starts the ordinary explicit loopback
UseFakeAuth DB/Map flow. A complete normal GROUPS inspection and actual claimed
DB handoff loan precede the synchronous GROUPS observer. After successful I/O,
release and cancellation polling, it queues REQALLENTS exactly once. Transport
reliable retransmission is not a second application request. Incoming unknown
commands, failed parses, stale owners, cancellation and timeout terminate.

A later actual owned ALLENTS message has its command/profile/source update
header checked under the existing 4 MiB decoder cap before the ordinary 16 KiB
semantic gate. The synchronous lease retains full payload bytes, exact bits,
post-command cursor, actual shortcut schema, selection/DB/Map/message generations
and transport IDs. It is raw diagnostic evidence; an opaque tail has not passed
whole character syntax or semantics. After callback success, loan release and
final cancellation, it records CAPTURED and closes. No READY, RECEIVED_CHARACTER,
full-update ACK, actor, current dictionary generation or acceptance is granted.
An earlier valid GROUPS observation and numeric metadata survive later initial
failure, allowing the separate GROUPS capture scope to remain useful.

Refused command diagnostics expose only `refused_command_valid` and a typed
`refused_command_kind`, rendered by `coh_initial_capture_command_name`. The fixed
whitelist is the231 original `ServerCommCmd` identifiers, excluding the count
sentinel. No decoded command is false/NONE; an actually decoded unrecognized
normalized command is true/UNKNOWN. Current classification is cleared before
each decode and service, then the first refusal is latched before Map cleanup.
Malformed/truncated/legacy-underflow input cannot reuse the preceding GROUPS
classification. Later close/cancel/timeout preserve that first observation.
These fields contain no packet text or raw numeric command identifier and do
not authorize a body parser, command skipping or a protocol response.

The separately witnessed SERVER_EDITMSG branch now has a complete bounded body
parser during WAIT_ALLENTS. It reads type and NUL-terminated text to the exact
logical packet end, retains only count/type/length, releases the loan, polls
cancellation and continues with the original deadline. It does not invoke UI
services or send a response. See [EDITMSG.md](EDITMSG.md) for original source
ordering, explicit domain limits, new focused qualification and CLI peer cases.

Original source does not guarantee ALLENTS is the next application packet after
GROUPS: REQSCENE sends the world and leaves the client NOT_READY; REQALLENTS later
sets its source state, while `entFinishUpdate` also flushes already pending game
command packets independently. `START_PACKET` can create a SERVER_GAME_CMDS
envelope. Dynamic definition sends are separately gated IN_GAME. These source
paths explain the need to observe the actual enum; none identifies the command
in an unclassified live refusal or justifies adding a guessed intervening parser.

`diagnostics.first_failure` records the first diagnostic failure/cancellation
with typed Local/DB/Map phases, status and failure reason before diagnostic
cleanup closes the controller. The private Map wrapper latches its actual phase
before its own failure close; the outer owner combines it with current Local/DB
phases. If an ordinary inner module has already reached a terminal phase, that
actual phase is retained; no earlier progress is reconstructed. Later diagnostic
copies, rejected service, close and cancellation preserve this snapshot and its
first cause. Successful raw capture, rejected inputs/reentry and plain close do
not create it. Ordinary `local.terminal_failure`/`terminal_*` fields retain their
existing meanings and bytes; callers choose the new snapshot explicitly.

An enclosing tool deadline can expire before the DB/Map module deadlines.
`coh_initial_capture_timeout` explicitly records `COH_STATE` / `FAILURE_TIMEOUT`
with the actual active phases, then closes the diagnostic attempt. It accepts
only begun active CONNECTING..WAIT_ALLENTS owners and has no caller-supplied
failure/status input. Null, callback-busy, idle, captured, failed, cancelled and
closed owners are unchanged. A tool whose total deadline expires while service
still returns OK must call this API before plain close; interruption uses cancel.

Callbacks may call only the exact-event lease getter and diagnostics. Mutations
and service reentry refuse or no-op. All pointers expire on return; the observer
copies/streams privately and returns COH_IO or another refusal on failed I/O.
Getter and observer boundaries reject known owner/event/message/payload aliases.
No raw packet copy or observer allocation is made by the new wrapper. Its two
calloc owner sizes, ordinary Local/Map sizes and lease size are measured by the
focused host receipt. These extra fixed owners still add to the ordinary
DB/Map/UDP/decoder allocation. This API does not perform a global aggregate
memory admission or prove process RSS; the caller must budget observer storage,
file retention and every transitive live module. Existing 16 KiB encoded and 4 MiB
decoded transport bounds remain unchanged. No new eager dictionary is built.

Run the new focused suite after committing its source:

```
python native-android/engine/initial-capture/check_initial_capture.py \
  --source-root "$PWD" --output /tmp/initial-capture.json --sanitize
```

It executes only the new capture suites on actual local UDP with synthetic
source-layout DB/Map peers and pinned original bit/GROUPS fixture producers.
It freezes all compilation/helper inputs, requires their exact HEAD blobs, and
rechecks source bytes/revision after execution. It does not run old qualifier
entrypoints or claim execution of a complete original ALLENTS producer. Native
malloc/calloc/free balance and FD counts cover successful/failed lifecycles.
LSan is disabled for the executor's unsupported `/proc` task walk; ASan/UBSan
remain enabled for their separate modes. The root-owned tool checker covers the
new CLI/file/receipt behavior separately.

`test_initial_peer.c` includes the unchanged scripted UI peer and extends only
post-GROUPS handling. Its generated `server-command-fixtures.h` must append:

```
#ifdef COH_INITIAL_PEER_RENAME_MAIN
#define main accepted_ui_peer_main
#endif
```

This trampoline renames the UI entrypoint after its included DB fixture suite
undefines its own main macro. Peer arguments are
`--serve --report PATH --mode captured|unknown|badheader|none`. Its readiness
JSON uses the original pid/db_port/map_port fields. Captured/badheader modes send
an explicit synthetic 65,536 B byte-aligned ALLENTS header plus opaque tail;
unknown emits normalized command 15; none acknowledges only at transport level.
The peer refuses READY or any other unexpected application request and reports
all authority flags false. It is never shipped or an authentic server witness.

## First-failure snapshot qualification

The command-classification follow-up is source
`f7d69537f922ff3f7996d4f2bdb320565bbfcc87`. Release/ASan/UBSan each passed22
public UDP scenarios /6,120 checks and five owner faults /1,797 checks. The
unchanged whole original `ServerCommCmd` and `getServerCmdName` run in an explicit
host fixture; all231 native names match, and three altered whitelist maps refuse.
Known/UNKNOWN/none, truncated owned command, legacy underflow and first-refusal
preservation controls pass. A same-service valid CONNECT_MSG followed by an
invalid compressed stream proves the candidate is cleared **before** every
owned-message fetch, including decode failure. The unchanged transport drops a
malformed one-bit UDP command; its later explicit deadline correctly reports
NONE, rather than pretending the application received that command.

All70 source/header/helper hashes match the qualified committed revision and
remained unchanged. Original name-oracle fixture runs unsanitized; the native
classifier runs in all three modes. Receipt
`qualification/initial-capture-command-classification-f7d69537f.json.gz` is6,000
bytes, SHA256
`fe7a63e2fa2d629d5cbcd868da26325e14509876a1f3861d3e9d888b315b5c1a`.
The binding JSON records every changed isolated input and the negative controls.

Measured host capture/Map wrapper sizes are1,080/1,304 bytes:2,384 bytes combined,
32 more than the deadline baseline. Diagnostics is1,024 bytes; existing first
snapshot24, private Map phase8, ordinary Local/Map1,040/2,536 and lease1,344 bytes
are unchanged. No native heap allocation path was added. Static known names
contain5,604 bytes including their NULs (maximum38 characters); code/static data,
transitive owners and external stacks still prevent a global RAM/RSS admission.
Only synthetic qualification ran for that historical classifier scope; the
separate run39088537547 later supplied the actual SERVER_EDITMSG command witness
described in EDITMSG.md, without its body/subtype/text/length.

The explicit enclosing-deadline follow-up is source
`30f9a3a6282d771c907d26d418aca22a0c9c1917`. Release/ASan/UBSan each passed19
public UDP scenarios /5,178 checks and five owner faults /1,544 checks. The added
DB and post-GROUPS Map cases call the timeout API while module deadlines remain
in the future, preserving actual DB_WAIT_PLAYERS/Map_SCENE_INCOMPLETE phases.
Callback-busy/null/idle/terminal rejection and first-cause preservation controls
passed; native allocation balance, descriptors and all owner sizes are unchanged.
All68 source hashes match the committed qualified revision; only four capture
source/test inputs changed from the previous snapshot proof, with all ordinary
and helper bytes unchanged. Receipt
`qualification/initial-capture-explicit-deadline-30f9a3a62.json.gz` is5,487 bytes,
SHA256 `9debb4fa590473ed56068342639f454ee8157ac86eaec337cdfc38ee38433e1a`.
The associated deadline binding JSON records exact controls and source changes.

Source `9901002fc0edc93c26720c0a6f0027ae3985ec60` includes the typed snapshot
and its focused controls. Release/ASan/UBSan each passed17 public UDP scenarios /
4,756 checks and five owner-fault scenarios /1,537 checks. Four added DB cases
use the pinned original server-error framing, request timeout, service
cancellation and explicit cancellation before Map handoff. Existing Map cases
now check actual pre-cleanup phases for protocol/header/GROUPS/observer/owner
failure, timeout and cancellation. Every first record remains byte-identical
through rejected service and repeated close/cancel; successful capture and plain
close followed by repeated cancel keep it invalid. Ordinary terminal fields
remain untouched and post-close phases/socket counts still prove cleanup.

All68 frozen compiled/header/helper input hashes equal the qualified committed
revision and remained unchanged. Only six isolated capture source/test files
differ from the prior seam receipt; every ordinary source/helper hash is equal.
No old qualifier entrypoint or server was run. Receipt
`qualification/initial-capture-first-failure-9901002fc.json.gz` is5,470 bytes,
SHA256 `c2bdb38e5179ac61f5802d690523ca49152ef60f34441adda5deeb56323f2618`.
The accompanying first-failure binding JSON records controls and exact sizes.

Measured host capture owner is1,072 bytes and its Map wrapper is1,280 bytes:
2,352 additional fixed owner bytes,56 more than the original seam. The public
first-failure snapshot is24 bytes, private Map phase latch8 bytes and diagnostics
value1,016 bytes. Ordinary Local/Map remain1,040/2,536 bytes and the borrowed
caller lease remains1,344 bytes. Caller diagnostic copies and every transitive
owner/callback/loan still add to the aggregate. This remains a separately bounded
diagnostic seam without global aggregate admission, process-RSS, original server,
whole character, source generation, actor or ACK qualification.

## Historical initial seam qualification

Implementation `d603351ff5db02a6377ca323aaf2046edb041265` passed the focused
release/ASan/UBSan suite: 13 public controlled UDP scenarios / 4,281 checks plus
five direct owner fault scenarios / 1,462 checks per mode. All 68 compilation,
header and fixture-helper inputs matched exact committed blobs before execution
and stayed unchanged. Receipt
`qualification/initial-capture-d603351ff.json.gz` is 5,410 bytes, SHA256
`df90b5ad9570a342fbb42fda80f5cd34bc0e56c089e3a6eef68ec1323b1b9fb4`.

Measured host capture owner is 1,048 bytes and its Map wrapper is 1,248 bytes:
2,296 additional bytes. Ordinary Local is 1,040 bytes, ordinary Map is 2,536
bytes and a caller-retained lease value is 1,344 bytes. These are exact local
ABI observations, not a global budget admission or process-RSS measurement.
The existing UDP/transport/decoder owners, immutable loan, caller context and
observer stack/retained copies still add to the live aggregate.

Cases include packed logical bits, decoded data above 16 KiB, exact 4 MiB
success and +1 refusal, malformed GROUPS/header, unknown preceding commands,
observer I/O refusal, post-GROUPS and final post-ALLENTS cancellation, timeout,
exact/copied/expired event and output aliases, owner retirement/stale generation/
remote-peer mutation, and allocation failures. Wrapped native allocation balance
and FD counts remain zero after cleanup. This proof executes no real server,
full original ALLENTS producer, whole character semantics or authority path.
E/F/D independently reviewed the source without replaying old qualifiers. The
root-owned CLI/disk/receipt qualification is a separate artifact and scope.
