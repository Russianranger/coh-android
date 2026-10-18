# Existing receive counters

This separate diagnostic role preserves the current initial-progress producer
body by five reversible identifier substitutions at eight sites. The original
main loop, protocol, policies, timeout, observer, private GROUPS/initial envelope,
stdout and request-progress output remain byte-identical after reversal. Public
begin/diagnostics/destroy wrappers delegate once. They retain only a held owner
key until actual destruction and a bounded numeric projection. The new private
receive-counters.json is attempted only after the legacy role succeeds and its
owner has closed and been destroyed, on the original still-owned directory FD. Failure to write optional diagnostics does
not change the original capture result. Original transport sources are unchanged.

The explicit new schema coh-initial-receive-counters-v1 exposes existing UDP and
NetLink rejection/count scalars, final queue counts, sampled queue peaks and the
last decode receipt's failure enum and sizes. Decode failure_kind is a last
receipt, not a cumulative failure counter. Peaks cover sampled diagnostics only;
queues cleared inside a core failure may never be sampled while pending. No
fragment-count/header-byte, endpoint, packet ID, generation, character, account,
payload, key or string is projected. Counts cap at 1000000; overflow refuses the
diagnostic and leaves protocol behavior unchanged. Observation retirement is
distinct from storage/OS cleanup; cleanup is only equality of owned transport
open/close counters. No projection proves server dispatch or world authority.

The same header supplies a new receive_diagnostics object in the JNI report.
The outer report schema and eight JNI operations remain; this object's explicit
schema distinguishes its new keys. JNI samples existing diagnostics while the
single executor owns the adapter; terminal/cancel/close retire the observation.
No Activity, native transport, budget, timeout or policy is changed.

The focused new controls use explicit owner/diagnostics doubles and minimal host
JNI doubles. They do not invoke the old adapter main or old native qualification
entrypoints. The new production host role links the unchanged core, retains its
exact ELF, and runs only the no-argument exit2 check. These are not original
protocol/server, Android ABI/emulator or Thor execution evidence. Host compiler,
headers, linked-file hashes and stack records are scoped metadata, not a full
runtime memory, RSS/GPU or Android fit proof. LeakSanitizer is disabled alone.
