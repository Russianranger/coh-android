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

## Qualified source and fixed host sizes

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
