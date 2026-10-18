`groups_native_status.py` preserves the first bounded native failure observation
that was missing from failed owned run 39078874753. It adds diagnostics to the
private supervisor and its fixed public summary. It does not change GROUPS
receipts, pairing, source-generation scope, initial packet acceptance or any
actor/ACK/world gate. There is no runtime, source rebuild or retry in this change.

The root-owned initial tool emits exactly 20 fields under
`coh-local-initial-capture-status-v2`: the existing ten fixed status/socket/scope
fields plus schema, diagnostic failure code, GROUPS-observed flag, one-request
count, current local phase, three preserved terminal fields, and the two fixed
refused-message classification fields. Unknown or
missing fields, duplicate JSON keys, extra log text, oversized output, Boolean
integers, out-of-range values and non-false authority flags refuse the diagnostic.
The exact source-owned failure vocabulary is NONE, INPUT, OWNER, PROTOCOL,
GROUPS, REQUEST, COMMAND, HEADER, OBSERVER, RELEASE, TIMEOUT, CANCELLED, MEMORY.
The native fallback UNKNOWN is refused rather than exported.

`refused_command_valid:false` requires kind NONE. A decoded command in a refused
message has valid true and either one of the 231 exact pinned original
ServerCommCmd names (excluding SERVER_CMD_COUNT), or UNKNOWN for a decoded
nonwhitelist value. Decode failure cannot reuse a previous GROUPS command. The
collector never exports a raw numeric command or a runtime-supplied name.
The original enum, COMM_MAX_CMD2, the C X-macro map and its source-pin manifest
are checked together and included in the committed source closure. UNKNOWN here
is a fixed command classification, separate from the refused failure-code
fallback of the same spelling. No packet is skipped or newly accepted.

The numeric maps are checked against the actual source enum members and values:

| Type | Header | Inclusive range |
|---|---|---|
| CohStatus | engine/coh_contracts.h | 0..7 |
| CohLocalPhase | engine/local/coh_local.h | 0..10 |
| CohDbSessionPhase | engine/dbclient/coh_db_session.h | 0..12 |
| CohMapPhase | engine/mapclient/coh_mapclient.h | 0..10 |

The supervisor latches the actual registered native child object/PID and its
registered open stdout descriptor's device/inode/uid immediately after launch.
After child retirement and handle closure, during final receipt collection after
aggregate cleanup attempts, it reads only that same private regular single-link
file. Output is limited to 16 KiB; exact SHA/length are checked before reading,
against the parsed raw bytes, and after parsing, with final file identity checks.
Those hashes, file identities, source-header pins and child PID stay private.
Stderr is never consumed or exported by this collector.

Collection may run when aggregate cleanup failed: that existing result remains
explicitly false in the public summary. A valid native diagnostic says only that
this owned child and stdout were closed and its bounded values were collected;
`native_sockets_closed` compares the tool's opened/closed counters and does not
claim all server/PG/Wine cleanup. The root tool's terminal fields and failure
code/status use the separate typed `CohInitialCaptureDiagnostics.first_failure`
snapshot when valid. Its first-write-only values precede the diagnostic owner's
Local close; diagnostic Map failures also preserve their actual phase before
their own close. If an unchanged ordinary inspector has already closed or marked
Map failed internally, that actual terminal phase is preserved. No guessed
earlier phase is reconstructed. Current `local_phase` still describes the final
closed owner, independently of those first-failure values. Plain close/success
does not invent a failure. Without a valid typed first snapshot, the tool
faithfully reports the ordinary Local terminal fields/current cause, including
false/IDLE when those are the actual values.
Python faithfully projects this producer data and never reinterprets ordinary
Local terminal fields, infers the cause from a phase, or combines a later cancel
status with an earlier failure's phases.

The public summary gains one fixed `coh-native-source-diagnostic-v2` object. It contains only
process-started and validation/result booleans, fixed exit 0/1/2/UNEXPECTED, the
fixed C failure enum, bounded status/local/terminal phases, request count,
fixed refused-command valid/kind pair, and
source-capture/partial presence booleans. NOT STARTED is represented by
process_started false and exit UNEXPECTED. Unavailable/legacy output has state
UNAVAILABLE and null status/phases; malformed new output has state REFUSED.
Exact historical stdout v1 and nested diagnostic v1 normalize to UNAVAILABLE;
only validated process exit/source-entry metadata is retained. Existing GROUPS
receipt acceptance and pairing remain unchanged. The historical compatibility
proofs below bind their original v1 parser rather than claim v2 ownership.
Presence flags mean only that those exact source-owned paths have entries at
collection time; they do not assert regularity, completion or packet admission.

The public constructor never serializes a native/private dictionary. No raw
stdout/stderr, account, DBID, cookie, connection/message ID, pointer, source or
packet body, hash, PID, file identity, arbitrary phase or exception string is
projected. The existing source stage/failure enums and public upload allowlist
remain fixed. Latch/read/parse/collection refusal cannot alter a valid GROUPS
result. Legacy private receipts without this object retain their old acceptance
behavior and receive fixed unavailable public diagnostics.

Sixteen `test_groups_native_status.py` methods cover exact source enums, all fields,
strict types/ranges, fixed failure names, ownership/closure/replacement/link
refusals, before/after hash changes, exit normalization, source-presence flags,
privacy canaries and preservation of GROUPS on late diagnostic refusal. Tiny
owned Python children test real Linux stdout descriptors and closure; synthetic
JSON supplies the status values. No actual native capture, PG, Wine, MapServer,
initial packet or authority token is executed or produced by these controls.
The five added methods cover all fixed command names, invalid classification
pairs, legacy normalization, command-map/source mutation, and stdout mutation
during late source verification; eight related public-summary methods also pass.

The follow-up `native-first-failure-stdout-compatibility.json` reuses all twelve
retained release/ASan/UBSan stdout files from the root CLI qualification at
`fe9b8abc14156ca76d27bd8a3d5d25eee9e391b9`. It checks their recorded byte hashes,
all build source pins against current bytes and committed Git blobs, the source
enums, and `parse()` compatibility. It does not rerun the CLI, recreate its child
ownership latch, or establish an original-server/native transaction. The
COMMAND/HEADER cases preserve first-failure phases; the timeout case faithfully
retains false/IDLE fallback terminal fields. All authority flags remain false.

The final `native-deadline-stdout-compatibility.json` separately binds the twelve
updated root qualification outputs after the explicit enclosing deadline fix.
Before closing an active diagnostic owner, the CLI now invokes
`coh_initial_capture_timeout()` for its deadline or the existing cancel operation
for interruption. Timeout has fixed COH_STATE/TIMEOUT semantics and leaves null,
busy, inactive and terminal owners unchanged. It captures the actual first
failure phases through the same typed snapshot; it does not rewrite ordinary
Local terminal diagnostics. The retained timeout output now has
`terminal_failure:true`, DB CLOSED and Map SCENE_INCOMPLETE, while current Local
is CLOSED. The final proof again performs only retained-byte parsing and source
checks, with no CLI replay or retroactive child ownership claim.
All 1,750 recorded audit pins bind to the qualification's committed revision;
the proof records one later unrelated nonconsumer audit change separately. The
current 42-file compiler dependency closure still matches the recorded build.
