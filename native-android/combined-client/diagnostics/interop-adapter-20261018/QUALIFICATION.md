# Thor local handoff JNI adapter

The new `InteropNative.java` has the same eight method signatures as
`LocalNative`, but loads the separate hidden-core `coh_combined_interop` DSO.
`interop_network.c` owns one `CohInitialCapture` on one Java executor. Monotonic
positive tokens reject stale/arbitrary handles and refuse exhaustion; they
are never emitted in reports. All engine/controller/provider state is borrowed
or owned through close and destroy. Begin failure wipes local account/policy/
connection-ID storage and destroys any partially created owner.

This is an explicit local development handoff diagnostic. The ordinary policy,
encryption option and real DB-supplied Map handoff remain; no Map port is
hardcoded. It selects an existing character. It does not run AuthServer login,
create a character, send READY/RECEIVED_CHARACTER/full-update ACK, initialize
the character or publish a world. Ordinary DB/Map request deadlines are retained.

The observer takes only the public synchronous exact-event lease, checks its
local owner/authority barriers and stores byte/bit counts and one private
message-generation association. It never copies payload, schema, shortcuts,
character identity or a pointer from that loan. The complete temporary lease
is wiped before return. Private names/map names are returned only by the
separate bounded transient character-picker byte array, which mirrors the
existing UI contract and wipes all native construction buffers. JNI array,
UTF and exception failures preserve a live accessible owner or clean the
partially created owner; exceptions are not silently cleared.

The numeric report schema is `coh-native-initial-interop-numeric-v1`.
`CHARACTERS_READY` retains the existing picker behavior; the new active phases
are `WAIT_GROUPS` and `WAIT_ALLENTS`. `INITIAL_OBSERVED` is terminal diagnostic
success with the core's expected `COH_UNSUPPORTED`, not accepted character
state. Failure/status/typed first failure survive later disconnect. The
`cleanup_verified` flag is explicitly scoped to `owned_transport_counters`:
terminal state with equal opened/closed core socket counts. It is not owner
storage destruction, independent OS inspection or whole-process cleanup.
Stale/busy handles return a fixed inactive CLOSED shape; report overflow returns
a fixed REPORT_LIMIT shape. Missing fields in these shapes must never default
to qualified success. All shapes retain `world_authority=false`.

With `COH_INTEROP_REQUEST_TX=1`, the adapter uses A's separately qualified
optional request witness. Services/cancellation/close use its original-operation
wrappers; typed terminal state retires borrowed keys. Subsequent close/cancel
uses ordinary operations so a retired witness is not re-entered or invalidated.
The witness is retired before owner destruction. A missing optional witness
does not suppress the real operation. Its new fixed `request_tx` object carries
only bounded transport observations; validity requires retirement and no
witness refusal. Peer transport ACK is not an application ACK, server request
dispatch, character acceptance or world authority. The actual witness kernels
are not executed by this adapter qualification.

The focused final02 run compiled the actual JNI adapter with explicit minimal
host JNI function-table, initial controller, crypto/provider and request witness
doubles. Release/ASan/UBSan each passed485 checks,14 scenarios and26 entirely
wiped frees. Controls cover argument/UTF bounds, allocation failures, JNI
array/string exceptions, private character escaping/termination, callback
lease admission/refusal, stale handles, reentry, terminal repeat refusal,
request retirement before destroy, suspension, disconnect and first failure.
The sample numeric report is retained; private sentinel identities/payload
never enter that report. No old native/fixture qualifier entrypoint was invoked.

The receipt brackets21 project inputs,89 actual host compiler/header inputs,
seven `ldd`-resolved dependency files and three exact retained host ELFs. These
linked-file records are not actual process mappings. The host JNI declarations
are deliberately not Android ABI evidence; the local environment has a JRE
without JNI headers/javac. Root's real NDK build and B's Android emulator/JNI
transaction are separate qualifications, and neither a scripted peer nor host
doubles establish original-server or physical Thor acceptance. LeakSanitizer
alone is disabled here. Host stack frames, scoped allocation wiping and source
bounds do not establish global96MiB, RSS/PSS/GPU or Android stack fit.

`host-final02/` preserves exact commands, hashes, three compressed host ELFs,
compiler/dependency records, stack records and child stdout/stderr. The binding
checks every retained file. Development refusals are separately labelled in
`development-refusals.json.gz`; the source-change refusal correctly prevented
the earlier mixed-header run from becoming an accepted proof.

For a changed adapter, run only the new controls in a fresh external directory:

```sh
python native-android/combined-client/diagnostics/interop-adapter-20261018/check_adapter.py --source-root . --output NEW_EXTERNAL_DIRECTORY
```
