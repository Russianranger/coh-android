# Default local coordinator owns its DB-to-Map selection

The explicit development-only local coordinator now takes an actual opaque
DBSession handoff owner. It compares the selected slot and actual session/selection
generations against the same DBSession diagnostics, reads only nonsecret source
Map candidates, applies the existing loopback policy, then invokes the strong
owned Map begin bridge. No controller copy of the raw cookie/handoff is made.
The Map retains the owner on success; every failure retires and releases it.
Suspend/close/drop/retry retain the existing socket and lifecycle behavior.

`selected_dbid_owner_bound` in local diagnostics reports actual retained ownership
and clears when it retires. A positive source-selected DBID is not a complete
character transaction, authenticated AuthServer receipt or world publication.
The separate encrypted live coordinator retains its previous scope; this change
does not silently convert its raw handoff path. Default scene parsing still ends
at SCENE_INCOMPLETE and sends no READY/full-update application acknowledgement.

The local controller's cumulative UI selection counter is not substituted for
the DBSession's source selection generation. The bridge uses the latter from the
actual owned receipt and verifies it against that DBSession. This preserves fresh
controller attempts without inventing or rewriting source-generation labels.

Host qualification: `check_owned_local.py` freezes project helpers/native inputs
before any project import, executes helper source bytes directly, and rechecks
them afterward. Five controls reproduce timestamp-valid stale bytecode, bypass
it, refuse PYC/unadmitted paths and refuse changed source. The retained host proof
records1389 unchanged Git-bound inputs,8 checked helper loads,1088 checks/9 actual OS UDP
scenarios per release/ASan/UBSan, separate large scripted UI peer and balanced
socket cleanup. It is source-layout scripted interoperability, not a live shard.
No LeakSanitizer or actual server acceptance is inferred. The bound proof adds
complete current Git/source/driver identities and the exact three generated
fixture hashes; both ABI descriptors must carry that same fixture map. Twenty-six
synthetic runner admission negatives cover omitted/contradictory provenance,
fixture associations and binary/ABI/scope records.

The optional bridge is present in the module and Combined source CMake lists;
no APK was built. A targeted `[owned-local-requalify]` publication enables the
existing native foundations workflow and reuses its already installed NDK for
ARM64/x86_64 local test binaries. The Android runner validates both build records,
ELF ABIs and transferred hashes, requires an Android13 x86_64 emulator, compares
the actual result to the source-qualified host result and verifies owned-temp
cleanup. Synthetic driver controls do not execute Android. Until actual CI output
is inspected, ARM64 build and emulator execution remain pending.


## Optional exact receive observation

`coh_local_service_observed` forwards a successfully inspected normal GROUPS
message synchronously with the actual opaque Map client and exact event address.
This permits `coh_map_client_scene_lease` and the separately bounded immutable
scene recorder without exposing or retaining the private client between calls.
The default service installs no observer. A malformed/unsupported structural
message never invokes it. Callback work and copies require an explicit complete
aggregate budget. The callback must not retain client/event/input pointers.

Local service, begin, selection and character reads refuse reentry during the
callback; suspend, cancel, close and destroy do nothing. Numeric diagnostics may
be read. All other Map calls remain forbidden by the Map callback contract.
Callback return has no protocol result and cannot enable READY, character ACK,
entity requests, source generation or world authority. The local development
authentication scope remains unchanged. No producer capture or live correlation
has been performed by adding this seam.
