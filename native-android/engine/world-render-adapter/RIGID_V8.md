# Additive rigid GEOv8 resource owner

Base: `767d55e48fa35261f1428bd542aa6cd3b2b9fa32`. No accepted asset loader,
bridge, appearance, renderer or JNI source was changed. Existing same-Surface
frame rollback controls are untouched.

The protected GEO reader supportsv8, but accepted rigid bridge admitsv0/v7.
`coh_wr_rigid_acquire` closes that CPU conversion gap for explicit rigidv8
models through protected `coh_asset_acquire`, GEO envelope/model/material/stream
views and delta decoders. It does not emulate an actor or add one-bone skinning.

Input requires an exact nonzero asset generation, exact model name, independently
trusted GEO SHA256 and SHA256 callback, exact material generation and off-thread
material owner callbacks. The callback sees authentic GEO model/partition/texture
identity. It must supply qualified zero-handle renderer material, explicit UV
scales and logical texture identities, per-part immutable geometry identity,
nonzero material source digest and retained owner pin. These fields are producer
attestations; this module checks identity presence/consistency and owns pins,
not external trick or material authentication. Callback failures retain ownership
of their failed output; successful callback pins transfer and release once.

The converter rejects bone information, weights/matrix indices, secondary
lightmap UV, reflection channels/counts, alternate pivots, nonunit source scale,
missing required streams, duplicate model names/part geometry identities,
unsupported material semantics, nonfinite values and out-of-range triangles.
Grid/reduction metadata can remain in the source; it is not interpreted for
collision or LOD. The material producer must reject unsupported tricks/LOD and
other source-dependent states rather than return defaults. No texture bytes are
decoded or uploaded here; exact resource mapping remains independently required.

Positions/normals remain model-local source values. Each original partition gets
its original index slice; vertices apply exactly one source GPU `V=1-V`, followed
by producer-qualified bind scales. Both renderer UV channels currently derive
from that same primary GEO UV stream; separate lightmap UV is refused.

The opaque resource owns immutable CPU packets, retains the exact loader blob
and all material pins, and exposes actual canonical asset path/generation and
model name. Loader trim cannot invalidate it; loader destruction refuses until
release. Keep resource through snapshot preparation and additionally through
binding/flush while its material/GPU resources are borrowed, unless those pins
have transferred to an independent retained owner. `coh_wr_prepare` copies CPU
bytes and IDs, never acquires GPU resources itself.

All allocations and callbacks are off-thread and serialized. The named96MiB
maximum aggregate counts caller external retained/peak ownership, the complete
caller-provided loader reservation, source header, stream/inflate scratch, aligned
decoded staging, candidate descriptors/geometry and other prior resources charged
as external. The loader MUST be independently configured with total_bytes no greater than
`loader_reservation`; the protected opaque API cannot inspect that configuration.
The full reservation is charged before acquire, then actual loader peak stats
are checked before/after against it. This prevents an uncharged acquisition peak
under that explicit supplier contract. The successful report is conservative payload/peak
accounting, not whole-process RSS, allocator metadata, transient driver or guest
memory. Separate arenas avoid an uncharged realloc old/new overlap. Caller must
reserve callback material/digest peaks externally before calling.

A nonNULL candidate output refuses with COH_STATE; it cannot overwrite a prior
resource. Failure/cancellation leaves output untouched, releases every transferred pin
and source blob; no graph/world publication or application ACK exists. This
module is still an isolated source-resource owner. A complete live GROUPS
transaction, asset/trick/LOD closure, authoritative actor/full update and atomic
world/actor admission remain separate requirements.

Run:

```sh
python3 native-android/engine/world-render-adapter/acquire_rigid.py --output /tmp/new-rigid-v8-corpus
python3 native-android/engine/world-render-adapter/check_rigid.py --actual-geo /tmp/new-rigid-v8-corpus/praetorianbox_open.geo --output /new/path/rigid-v8.json
```

Qualification compiles unchanged original GetVrmlv8 producer structures with
true32-bit pointers into a nonexecuted object and checks16 exact size/offset
values. It executes pinned original `uncompressDeltas` for all four safe fixture
channels and compares every emitted partition position/normal/UV/index byte.
Release, ASan and UBSan execute the same lifecycle/identity/capacity/refusal corpus
and emit identical packets. The tiny authored grammar fixture remains fixture-only.

An authenticv8 asset was then recovered from the existing public release using
bounded nested ZIP ranges: `praetorianbox_open.geo` (1,289bytes, SHA256
`218d1b2ff890678cca25b005d295aff8f76c6f551acad6b2144d1786723239b5`).
The published49MB source manifest was fully verified against its existing
`8587015400e1af639e2118649f0d9c77a089d564bfe2c97cbf9d80baaee5f9a2` pin,
and its selected exact GEO record and original PIGG provenance retained in
`rigid-authentic-pins.json`. Outer1.63GB/inner859MB full ZIP hashes and original
PIGG were not reverified. The selected ZIP payload SHA and CRC were verified.
`acquire_rigid.py` reproducibly downloads only this source-pinned member;
raw game bytes remain external and are not committed.

Actual model `FX_PraetorianBox_Open` has56vertices,28triangles and one
`Box-1.tga` partition, unit scale, no skin/lightmap/reflection/pivot. Grid and
reduction packs remain unconsumed. All three native modes convert these real
geometry bytes; pinned unchanged original delta decoder independently verifies
every emitted position/normal/UV/index component. The source generation17 and
material generation19, logical texture IDs, unit material UV scales and default
shader in this control are explicitly synthetic test bindings. This qualifies
real geometry conversion, not the actual model's material/trick/LOD state.
No full source resource permit is minted.

Original producer structure layout qualification is not execution of the full
original exporter. Actual inherited materials and loaded model identity supplier,
textures, graph generation and actor transaction remain unqualified. No GLES,
Android, Thor or live world acceptance is claimed here.

## Standalone Android CPU qualification

The qualifier can package both API26 ARM64 and x86_64 executables with the exact
fixture inventory, source/header/oracle/runner hashes, generated digest replay
header, expected native results and source-oracle packet hashes. Host release,
ASan and UBSan retain real OpenSSL SHA256 callbacks and execute original source
oracles. A separately compiled fixture digest replay is also executed on host
and must produce identical native results and packets before crossbuilding.

NDK tests use exact byte-equality replay over the preauthenticated finite fixture
set because no general OpenSSL runtime is shipped in this CPU harness. This is
explicit test infrastructure, not a replacement SHA implementation, and grants
no general cryptography or AuthServer acceptance. Production resource callbacks
still require genuine independently qualified source digest computation.

Coordinator commands, from the clean integrated source commit:

```sh
python3 -m unittest discover -s native-android/engine/world-render-adapter/tests -p test_rigid_android.py -v
python3 native-android/engine/world-render-adapter/check_rigid.py --actual-geo /tmp/rigid-corpus/praetorianbox_open.geo --ndk /tmp/recovery-ndk/android-ndk-r28c --output native-android/results/rigid/qualification.json --android-output native-android/results/rigid/android
python3 native-android/engine/world-render-adapter/run_rigid_android.py --source-root . --artifacts native-android/results/rigid --validate-only --output native-android/results/rigid-admission/receipt.json
```

Upload the complete `results/rigid/` tree, including generated header and fixtures.
Inside the existing Android13 x86_64 emulator job on the identical clean commit:

```sh
python3 native-android/engine/world-render-adapter/run_rigid_android.py --source-root . --artifacts native-android/results/rigid --adb "$ANDROID_HOME/platform-tools/adb" --serial emulator-5554 --output native-android/results/rigid-execution/receipt.json
```

Use a new empty evidence directory each time and retain all logs on failure.
Driver admission requires both ABI PIE identities/receipts, exact scope/counts
across all host modes and build receipts, all regenerated authored fixtures,
the exact authentic fixture if present, and the executing driver's/helpers'
source hashes. It verifies actual Android13 x86_64 emulator identity, transferred
ELFs/fixtures, returned native JSON, independently source-qualified packet hashes,
unchanged source and owned remote cleanup. ARM64 remains build-only. Admission
alone retains execution/emulator flags false. Mocked device control tests verify
receipt rollback for packet mismatch and cleanup failure; these are not device
execution evidence. No original producer/delta oracle runs on Android itself.
No GLES, actual material, loaded generation or live world qualification follows.
