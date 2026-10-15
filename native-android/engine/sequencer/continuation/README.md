# Gate 33 continuation: generic raw-pose playback

Status: implemented, host qualified and Android API26 ARM64 object built.
Android execution, graphics/lifecycle integration and physical Thor acceptance
remain pending. This does not complete Gate 33 or alter accepted gates 1–24.

`../coh_seq_playback.h` adds an opt-in adapter around the unchanged
`CohSequencer`/`CohSeqSelection` and original raw-key sampler. It supports
actor-specific immutable per-move rig bindings; recursive source per-bone move
transition blending; explicit forced-self-transition generations; lazy rebinding;
ordered bounded animation cues; and a transactional original-state-bit bridge.
No character name, original asset path or state family is hardcoded in the
shipping C module. The existing graph, grounded locomotion, character, animation,
network/auth/session, renderer, JNI, root build and workflows remain unchanged.

## API and ownership

1. The asset owner validates raw rigs with `coh_animation_parse`, resolves
   ParentType/animation base fallbacks and retains their storage. Existing
   `coh_locomotion_parse` is reused in qualification for the accepted male-to-Huge
   fallback; this adapter does not invent cross-skeleton retargeting.
2. Initialize `CohSeqPlayback` with actor/rig IDs, immutable per-move
   `CohSeqPoseBinding` records and an optional sorted `CohSeqMarker` table.
   Each actor owns its playback state on one simulation thread. Different actors
   may use different hierarchies. Changing hierarchy within an actor returns
   `COH_STATE`; initialize a new actor/appearance generation instead.
3. Run the existing `coh_seq_step`. Pass its selection, its
   `diagnostics.transitions` counter, source `TIMESTEP` and an increasing tick to
   `coh_seq_playback_sample`. Source time is 30 Hz frames, bounded [0,3]; use the
   unscaled timestep for blending, not MoveScale-adjusted clip advancement.
4. Render the caller-owned local/world pose using an opt-in neutral-rig adapter.
   The module performs no GL work. Morphing, actor root transforms, registration,
   SmoothSprint and root motion remain the character/locomotion owner's concern.
   Do not apply world-matrix interpolation or alter the accepted renderer.
5. Dispatch caller-owned typed events after the successful simulation tick.
   `coh_seq_playback_state` applies explicit bit updates to copied mock/game state;
   no network packet format or primary agent session state is changed.

`coh_seq_playback_rebind` swaps a complete immutable table between ticks, retaining
the active clip identity/hierarchy/range. Release old tables/raw storage after all
borrowing actors have rebound. A missing rig returns `COH_NOT_FOUND` without
advancing playback. Any error preserves state, pose, events and event count.
Poll cancellation once before doing work. Producers must stop before destroying
storage. Surface recreation retains logical animation; only GPU resources change.
Resume without replaying wall-clock backlog.

## Timing and cue semantics

The original `animPlayInst` percent-new expression is applied recursively to the
last stored per-bone pose, preserving source quaternion hemisphere handling,
normalization, rotation and squared-translation thresholds. A new move resets
the interpolation clock; interruption blends from the current partially blended
pose. `NOINTERP` follows the source rule of producing raw output without changing
stored interpolated translations/rotations. The hierarchy is recomposed from
local translations/quaternions after blending. Clocks saturate above 1,000
frames; all admitted interpolation durations are at most 1,000.

Cues are a **local adapter contract**, not original PlayFx timing or network
packets. Thresholds use `(previous,current]`; entries emit authored markers at or
before the selected entry frame. One-wrap cycles emit the old tail then the new
head. Equal-frame cues retain declaration order. At most 256 immutable cues and
257 output events (entry/cycle plus cues) exist per tick. Insufficient output
capacity returns `COH_LIMIT` with no partial delivery; resize and retry the same
tick. Forced self-entry is detected from the transition counter. The caller
must not replay a successful tick or alias outputs with borrowed tables/state.

## Qualification

```sh
python native-android/engine/sequencer/continuation/check.py \
  --output /tmp/coh-playback/report.json \
  --source-root /path/to/repository-with-upstream \
  --corpus /path/to/accepted-directional-raw-corpus \
  --extra-corpus /path/to/new-raw-corpus \
  --landing-corpus /path/to/original-male-landing-corpus \
  --android-clang /path/to/aarch64-linux-android26-clang --sanitize
```

The recorded qualification includes:

- 20,620,965 core checks, including 20,523,420 scalar comparisons against unchanged
  original per-bone blend/math functions across 18,002 authentic directional
  pose updates. Maximum scalar error: zero in this host scalar run.
- Original encoded combat punch, jump-and-smash power, fallout reaction and
  landing clips for male/female/Huge; male wave raw pose; 5,478,444 additional
  original raw-decoder/blend scalar comparisons and 4,500 transition poses.
- A six-move authored landing/punch/punch-post/jump-power/post/fallout graph,
  source requirements/priorities/rates preserved, with clip ends resolved from
  original raw headers. 36,000 comparisons against original sequencer kernels.
  All three bodies have admitted landing clips. Generated graph JSON,
  header and canonical rigs are in the selected output's `playback-build/families`.
- 20,000 bounded malformed-metadata mutations; invalid inputs, missing clips,
  tick replay, cancellation, hierarchy, maximum-capacity cues and atomic retry.
- ASan/UBSan for the full core suite plus 26,000 additional authentic-family pose
  samples and truncated-container negatives. LeakSanitizer is disabled due to
  this executor's `/proc` limitation; ASan and UBSan remain active.
- The unchanged original 18-move selection regression: 1,848,320 checks,
  89,111 original-kernel comparisons and one million bounded steady-state steps.
- A separate Android API26 ARM64 object build; no Android execution claimed.

Each playback actor retains 7,960 bytes on this host ABI and borrows raw storage.
The optimized compiler reports 15,760 bytes of stack in the sample adapter,
plus called sampler/helper frames. There are no per-sample heap allocations,
locks, file IO, GPU calls or callbacks other than the optional cancellation
poll. Symbol auditing verifies absent allocation/blocking imports. Markers,
rigs and output buffers are caller-owned with explicit ceilings. Reported host
elapsed times are test timings, not GPU, device thermal or gameplay FPS results.

## Integration and rollback

Add only `coh_seq_playback.c` to a coordinator-owned opt-in library with existing
sequencer/animation code and libm. For the character translation unit, reuse
`coh_character.c` instead of additionally compiling `coh_animation.c`, as its
existing build contract already includes the latter. No root build edits belong
to this module. The generated family rigs are neutral test assets; retain their
source identities and hashes through the shared asset owner.

In one consolidated offline APK, bind multiple bodies, transition combat and
jump/landing clips, interrupt midway, pause/resume, recreate the Surface, and
export actor IDs, clip IDs, frames, transition counters, cue counts, pose errors
and memory counters. Controller/touch choices should drive explicit mock bits.
Confirm correct attachments, no GL errors, stable memory and no lifecycle
backlog. These remain device acceptance tasks, not results of this receipt.

Rollback removes the opt-in adapter and its consumers via an ordinary additive
revert after checking dependencies. Keep accepted 0.3.0 and every previous
receipt unchanged. No network/live-session changes or server dependency exist.

Remaining: full player graph closure, original flags' gameplay side effects,
actual emote state bindings, registration/root motion,
morph-aware composition, attachment/FX routing, gameplay event reconciliation,
Android execution and physical Thor qualification. Gates 25–27 remain exclusively
owned by the primary agent.

## Isolated consolidated-client adapter

The coordinator explicitly delegated new `support-client/src/support_animation.h`
and `.c`. They expose opaque create/destroy/trigger/sample/active-rig/snapshot
calls for the authentic Huge punch, jump-and-smash and fallout raw clips.
The adapter borrows canonical rig bytes, allocates only during creation and
destruction, and forwards source timestep/transition state to this module.
Selected full raw clips loop with source strict-end wrapping and five-frame
blending. This is a mock event UI path, not the source gameplay graph.

`adapter_check.py --rig-directory OUTPUT/playback-build/families --output FILE`
passed 20,807 checks and 10,002 samples under ordinary and ASan/UBSan builds,
plus ARM64 API26 compilation. It retains 43,872 bytes and borrows 72,648 bytes
for these three prepared rigs. No per-sample allocation or GL work occurs.
Use the mesh's explicit bone IDs and attachment socket for palette generation;
the canonical test container's one-bone palette is only raw-pose test metadata.

The output is neutral. `coh_character_palette` applies skin bone scales and
attachment folding but does not perform missing morph hierarchy/root composition.
The consolidated client must retain neutral appearance for this mock or add a
separately qualified morph composer before claiming source-accurate morphed
output. The accepted grounded/morphed locomotion path remains unchanged.
