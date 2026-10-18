# Smallest proposed strict Map status observer

This is an implementation plan only. No decoder, transport, WinAPI backend,
monitor client or test is implemented or executed by this file. It follows the
retained-handle contract in`../deployment/WINDOWS-MAP-READY-OBSERVER-CONTRACT.md`
and its corrected source-only audit-v2. Source schema has31 live MapCon fields,
2 BaseCon fields and2 NetLink fields. Commented schema entries are not fields;
the old v1 inventory remains preserved history and must not generate a decoder.

Use a NEW status-only native executable rather than the GUI ServerMonitor or
an extension of the Auth/list/creation owner. Its only application request is
the original monitor CONNECT and its only admitted data message is the first
complete full MAPSERVERS snapshot. The existing scalar bit/frame primitives
are possible dependencies, not an already qualified NetLink TCP controller.
The UDP session, Auth TCP framing and permissive original monitor receiver
must not be presented as that missing TCP codec.

## New source split and API

Confine source to this new directory, with no ordinary server/controller edit:

| Proposed file | Single responsibility |
| --- | --- |
| `coh_map_ready.h/.c` | Opaque one-shot observer; begin/service/cancel/destroy/diagnostics, busy refusal, fixed outcomes WAITING/READY/REFUSED. No raw packet, row, PID or schema getter. |
| `mapcon_full_private.h/.c` | Pure bounded transactional decoder for the exact schema and complete first full snapshot. Private scratch; fixed scalar facts only. |
| `monitor_tcp_private.h/.c` | Bounded TCP stream framing and exact profile5 NetLink handshake/application CONNECT. No downgrade/retry/exec/relay/player/version request. |
| `windows_map_ready_lease.c` | Private fixed-input parsing, retained Db/Map process/file identity observation, socket ownership and cleanup. No launcher/profile/SQL mutation. |
| `map_ready_probe.c` | One-shot CLI, fixed JSON and private input. No account, password, Auth grant or character API. |

The public observer takes only an opaque platform lease created by the new
private backend. There is no public constructor from raw PID/handle/generation
or caller readiness boolean. Its initial scope fixes Db monitor127.0.0.1:6996,
Map1/UDP7001 and the exact current realm lease. Begin is consumed before opening
a socket; service is nonblocking and budgeted, and diagnostics/destroy outputs
remain unchanged during callback reentry. It closes the monitor socket and
wipes packet/schema/row scratch before publishing a terminal summary.

The proposed sole CLI is`map-ready-observer --snapshot PRIVATE_READY_INPUT`.
The new private input is distinct from the creation probe's unchanged96-byte
policy: it needs both actual Db and Map identities, whereas that policy carries
only the Map identity/Auth port. Do not infer the Db generation from an Auth
port or rebrand the96-byte file as readiness. Root must review a fixed bounded
format before implementation. It will carry only current process creation/file
pins and an operation nonce from the independently owned driver; no account,
UID, DBID, cookie, SQL, arbitrary path or endpoint selector is necessary.

The backend opens and retains observation handles to the exact current Db/Map
processes and rechecks wait-state, PID/creation identity and actual image file
pin before and after network observation. Those handles complement, not
replace, the launcher's original lifetime handles. It must fail on denied
cross-user observation; no privilege/DACL grant is a fallback. Source-owned
socket observations bind the fresh TCP connection to Db6996 and the Map's
ordinary current6997+6989 channels. The driver owns SQL/profile/job admission
and repeats those gates around the observer and the one creation probe.

E's f23 inert helper and the tiny6d01645 successor remain inert-only; the latter
changes definite-assignment and allocation cleanup, not a live Map API. This
observer cannot make those helpers keep a Map alive. The fixed live-Map lease,
private target-user log capture and current Map/DLL/assets admission must be
implemented and qualified separately before any original-service run.

## Decoder and transport limits before implementation

The decoder should generate its finite field manifest from the exact pinned
original schema/ParseTable macros and original full-update writer. Include the
actual field type/parameter/order and nested tables. Do not derive it from a
regex that retains comments, accept a peer-supplied callback table, or call
`sdUnpackParseInfo(...false)` as admission. The new bounded reader validates
names/type/parameter/counts before allocating or interpreting field payloads.

Require the exact CONNECT acceptance, full-update bit, whole exact schema,
absolute values and every expected field exactly once. Decode the entire map
list/terminators/deletes and exact logical end transactionally, not just a
prefix up to Starting. Starting must be explicitly present0. An all-zero
default object, missing/deleted row or diff cannot pass. Admit only the expected
Map1 row with current endpoint and present NetLink; additional/duplicate rows
refuse this fresh-realm scope. Other fixed strings/floats/stats are bounded
private decode material, never commands or exported data.

Transport must validate original TCP framing/checksum/padding and profile5
control semantics with original source oracles before using the native frame
primitives. No UDP retransmission owner is silently reused over TCP. Current
source defaults to uncompressed monitor packets; the first bounded implementation
can explicitly refuse compression unless its original source profile/codec is
also qualified. It must never treat a compressed body as already decoded.

Initial proposed bounds for root review: one active socket, one CONNECT,
one snapshot, no automatic reconnect; maximum5s monotonic total after platform
admission, per-service8 reads of at most1024 bytes, bounded32 frames and a64KiB
logical message cap, fixed recursion3 schema levels, fixed35 live total fields
across the tables and one map row. The field total means31+2+2 table entries,
not a35-field flat record. Actual original-writer fixtures must prove those
caps sufficient; otherwise report a blocker before any runtime. Do not raise
them from a timeout or silently clip strings/fields. Readiness polling creates
a new observer only, under the same live realm; it never retries Auth/creation.

MAPSERVERS is the first automatic full-update family. Once its entire exact
snapshot is consumed, close. Later frames already buffered on TCP are discarded
unaccepted, with no claim to parse their bodies. A different application command
before the required snapshot refuses. No general monitor message dispatcher,
schema fallback or independent-traffic ignore budget is added.

## New focused controls, with no old entrypoints

First freeze and independently review new source. Then use a NEW original-writer
fixture adapter to produce the exact schema/full-update bytes without invoking
the old monitor GUI or old Auth/list/creation suites. The oracle must preserve
whole original writer/type routines and independently bind the35 live entries.

New parser controls cover explicit Starting0/1, absent/default/deleted Map1,
wrong endpoint/link/id, extra/duplicate rows and fields, exact type/parameter/
order, unknown/commented schema names, full-vs-diff and absolute-vs-delta,
logical trailing bits, lengths/recursion/counts/compression and allocation
failure. Outputs stay unchanged on refusal and all new scratch is wiped.

New controlled TCP peers cover original handshake/frame parity, partial header/
body delivery, complete first snapshot, unknown-before-map, later-frame discard,
EOF/error/timeout/cancel and every new close/allocation failure. These are
synthetic observer tests, not original Db/Map readiness. Retained-handle models
must cover current-to-replaced process generations, denied observation, wrong
socket owner and late close, retaining the first cause and all cleanup attempts.
Only a separately approved Windows observer/platform qualification can claim
actual headers/WinAPI behavior; existing helper or owner tests are not replayed.

## Result meaning

READY means a fresh, complete Db-produced Map1 readiness-state snapshot with
explicit Starting0/current registered endpoints/link, bracketed by the same
actual owned processes/channels and successful observer teardown. Active is
inferred only from the exact source producer's active-or-starting selection;
it is not a wire field. `ready_command_sender_attributed` remains false because
the original ready handler does not compare packet MapID against its link.
The public receipt contains fixed outcome/failure enums, bounded counters and
these booleans only. Raw schema/packet/string/selector data remains private.

No actual readiness exists yet. This plan does not initialize a character,
consume a grant, allocate an entity, open a Map client socket, send a creation
body/READY/character/full-update ACK, admit a normal version/reference checksum
or establish world authority. The creation probe remains separately one-shot,
and whole fresh-DB retirement remains required for any actual uninitialized
allocation; observer cleanup is never persistent rollback.
