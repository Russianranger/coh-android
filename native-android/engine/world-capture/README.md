# Recovered diagnostic GROUPS capture

This candidate was recovered byte-for-byte from the previous Worker C tree.
`recovery.json` preserves its original identities before correction. The old
working tree was not changed. The candidate was unpublished and therefore had
no inherited host, Android or live-server acceptance.

The standalone probe uses the unchanged native local-development session owner
and restricted linker hooks. It allows one loopback DbServer and one expected
loopback MapServer and only the original CONNECT, REQSHORTCUTS and REQSCENE map
commands. It never requests ALLENTS, sends READY, RECEIVED_CHARACTER or a
full-update acknowledgment. Account and expected character names arrive through
stdin, are wiped after use and are absent from reports and command arguments.
No AuthServer password is accepted. This is a nonshipping diagnostic executable,
not an accepted APK or a replacement server runtime.

`coh_world_capture_stage` copies a complete, original-grammar-validated new-world
normal GROUPS message, preserving exact decoded bytes, logical bit count,
byte-alignment profile, packet/lease identities and the source footer. It checks
the expected file/root counts and CRC words, but those comparisons alone do not
prove matching runtime/catalog generation. Nonzero source/profile/runtime/catalog
and independent character-row SHA256 fields are caller attestations, not
authenticated certificates. Complete actual runtime inputs must supply them.

`coh_world_capture_confirm` additionally matches the unchanged local owner's
complete structure receipt, selected slot, actual map ID, structural counts and
exact payload extent at SCENE_INCOMPLETE after lease release. The wire DB handoff
does not contain the selected DBID, so expected DBID remains an external row
assertion. The receipt explicitly reports character identity and world readiness
as false. Confirmed diagnostic GROUPS bytes can provide real root names/matrices
to a later matching-scene validator; they cannot authorize graph or actor
publication on their own.

The owner uses one allocation under an aggregate 32 MiB cap. Admission charges
the borrowed message, owned copy, metadata, 8 KiB stack reserve and caller-retained
transport/session/catalog evidence. The probe reserves 8 MiB for local/DB/Map and
crypto state and separately includes measured Map transport/codec allocations.
This named reservation is not a measured full-process peak. It must be reviewed
against any future deployment context. The owner exports immutable borrowed
bytes until free; free wipes the owned allocation. Stage/control/output/input
overlap and view/output/owner overlap are rejected before writes.

Recovery qualification found two actual harness failures: a sparse checkout
lacked source files expected by old oracle helpers, and the fixture confused
link ID 17 with map ID 5. The driver now builds a temporary exact-Git source
mirror, expects the genuine synthetic map ID and tests a wrong-map refusal.
The strict production confirmation was not weakened. Stage/view alias checks
were then added because the old header's disjoint-memory contract lacked
enforcement. Original candidate hashes and these corrections remain distinct.

Run `python3 native-android/engine/world-capture/check.py --source-root .
--sanitize --output /tmp/world-capture.json --build-output /tmp/capture-probe`
from the repository. It executes unchanged original GROUPS producers, 44 source
fixtures, every/sampled truncations and malformed inputs. An independent scripted
UDP peer verifies success, wrong footer, wrong character, wrong endpoint,
wrong map and existing-output preservation, with both sockets closed each time.
Source files and final probe binary are bound by receipt hashes. The probe writes
only a new mode-0600 file after successful confirmation and cleanup.

All current runtime captures in these tests are synthetic peer fixtures. No
actual MapServer startup, existing character selection, matching catalog-runtime
transaction, AuthServer login, Android execution or physical Thor acceptance was
performed. Existing authentic catalog bytes must be reused; this candidate is a
way to capture the missing matching GROUPS evidence once an independently
staged disposable existing character and runtime contract are available.
