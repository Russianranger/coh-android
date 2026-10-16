# Original player control-state staging

This isolated module decodes one non-debug `playerReceiveControlState` wire
substructure. It is additive and has no Combined, JNI, gameplay physics, renderer
or acknowledgment integration. A valid control block is not a complete character
or `ALLENTS` transaction. Gates 25–27 remain open.

The exact original functions are available in Git even when the sparse working
tree omits them. `check.py` reads unchanged files from the working tree or
`git show HEAD:upstream/ouroboros/...`, and validates every decoded LF source pin
before compiling the oracle. No network or prior historical commit is needed.

## Wire contract

The original producer is `MapServer/src/svr/svr_player.c::svrPlayerSendControlState`,
called by `entsend.c` with `full_update | re_predict`. The matching complete
consumer is `Game/src/player/player.c::playerReceiveControlState`, called after
optional entity-debug tails and before deletes. Supported order:

1. Future pushes: sentinel list, 16-bit network ID, packed waiting ticks,
   absolute time, velocity, and knockback animation flag. Admission caps one
   block at 32 pushes and rejects waiting ticks beyond the source U16 range.
2. Physics positions: reuse the existing `coh_rep_physics` parser unchanged.
   The source diagnostic `record_motion` branch remains unsupported. That branch
   carries raw `MotionState` records and needs separate ABI qualification.
3. Optional server state: 8-bit update ID, three speeds, backward speed,
   raw surface parameters, jump height and all 17 movement/control flags.
4. Optional forced move: packed position ID, position, optional velocity and
   pitch/yaw/roll, and the source one-bit `falling` value in packed form.

`SurfaceParams[2]` is exactly 40 source bytes: two 20-byte structures, each
containing five IEEE754 binary32 fields at offsets 0/4/8/12/16. The oracle
compiles the unchanged source declarations and asserts those sizes/offsets and
little-endian host storage. Arrays align to the next byte in **both** bit modes.
The native POD retains all 40 bytes; `coh_control_surface_value` converts explicit
little-endian words without assuming native physics layout or compiler packing.
All decoded floats, including surface values, must be finite. Source padding is
skipped rather than interpreted as state. Compressed mode means source scalar
byte alignment, not compressed input bytes.

## Transaction and lifetime contract

`coh_control_read` borrows an initialized `CohRepReader` input only for the call.
It returns a pointer-free POD and commits the reader and output together after
all supported branches succeed. On failure both are unchanged; an optional
failure receipt contains only stage/status/bit offset. It allocates no memory.
The 64-bit host update occupies 1,064 bytes, and the state occupies 176 bytes.
Parser scratch is one bounded update plus its reader and scalars. There is no
unbounded string, list, callback, retained packet view or main-thread work queue.

`coh_control_stage` takes a successfully decoded POD and a caller-owned **staging
copy**. It requires a nonzero session generation and packet ID and rejects a
generation mismatch. New sessions call `coh_control_state_init` explicitly.
Its ordinary unsigned comparisons preserve original `packet <= prior` stale
handling; it does not guess serial wrap behavior. Server state, forced moves
and physics positions have separate packet IDs. A network-ID-only physics
update inherits the previous position and does not advance the original
position packet ID; without a prior position it has no effect. Forced pitch is
consumed and retained in the wire update but ignored in staged actor orientation,
as in the original consumer. Camera and local prediction are untouched.

Future pushes remain raw events in the decoded update. The enclosing complete
transaction must deduplicate packet delivery, retain bounded events, and resolve
their local physics-history references. This module does not execute pushes,
replay movement, create control acknowledgments or identify the selected player.
The coordinator must stage entities, control and all remaining tails together,
validate selected DBID/ownership and the complete packet, and only then publish.
Rollback is discard of the caller's candidate POD/state; accepted modules remain
unchanged. No new public API from gameplay-support is required.

## Qualification

```sh
python3 native-android/engine/entity-control/check.py --source-root . \
  --sanitize --output /tmp/entity-control.json \
  --fixtures-output /tmp/entity-control-fixtures/fixtures.h
```

The host oracle executes the unchanged complete producer and its two component
producers, plus all four unchanged original consumer functions. `TEST_CLIENT=1`
is explicit: local prediction history is empty, `first_packet_sent=0`, and owner,
clock and allocation shells are deterministic. Native actor physics, camera
behavior, real server traffic and the regular Game prediction path are not
qualified by this oracle. Packet scalar adapters call unchanged original
BitStream functions. Original x86-oriented code runs at `-O0` on trusted padded
fixtures; sanitizers cover the new native decoder and its tests, not the
historical writer's aliasing assumptions.

Ninety producer fixtures cover empty/all sections, full-update stun restoration,
32/33 push boundaries, already-sent push stopping, removal of used pushes,
diagnostic recording refusal, both scalar modes, and every ordinary bit offset.
Seventy supported fixtures each compare decoded events and staged fields with
the original consumer, then compare prior packet IDs 11/12/13 against packet 12:
280 consumer comparisons. Tests also cover every truncated bit boundary of
supported fixtures, byte mutations, nonfinite surface/velocity input, malformed
flags/ticks/falling, generation reset and rollback, ID-only physics state, and
20,000 deterministic random malformed inputs. These are source fixtures and
bounded mutation controls, not captured server packets or coverage-guided fuzzing.

`--ndk PATH --android-output DIR` compiles the same qualified fixture tests as
ARM64 and x86_64 Android executables without running the original oracle there.
Build receipts explicitly say `executed: false`. The isolated CMake target
`coh_native_entity_control` can consume generated fixtures with
`COH_ENTITY_CONTROL_FIXTURE_DIR`. Shared CMake/CI, emulator execution and Combined
integration remain coordinator-owned. Do not rebuild an accepted APK for this
standalone module.
