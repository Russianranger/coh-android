# Gate 43: opt-in native game audio module

Status: reusable mixer **implemented and host qualified**, including authentic
native Ogg decode integration. The optional AAudio callback sink builds and
links for Android ARM64 API 26. Android emulator playback, physical Thor
audibility, latency, device-change behavior and sustained backend underrun
acceptance are **pending**. Gate 43 is not physically accepted or complete.

This directory is outside existing APK/JNI/Session Client build paths. It does
not replace or edit accepted audio, decoder, gates 19–21, launcher, source pins,
fixtures or previous receipts. No Wine/Box64/FEX is used.

## Implementation boundary

`coh_mixer.h` exposes an owned, bounded mixer, cached PCM resources, scheduled
audio events, stream rings, emitter/listener updates, bus gains, cancellation,
pause/resume and diagnostics. `coh_mixer_aaudio.h` exposes a separate optional
Android sink. The existing accepted `audio/coh_audio.c` provides the exact
source gain curve and COHAUD11 parser. `decode/coh_decode.c` can decode compressed
assets on a producer worker; the mixer neither forks nor invokes the codec.

The implementation supports up to 32 simultaneous voices, 128 pending/copied
commands, 32 cache entries and four preallocated PCM stream rings. Configuration
chooses lower bounds. Callback commands/events are fixed-size copies; PCM cache
and stream storage allocate once at creation. Cache entries use original virtual
path plus content generation, copied into a 192-byte identity field. An unchanged
identity is a cache hit; callers must advance its generation when bytes change.
Resources have an internal generation, so evicted/reopened handles are rejected.

Cache capacity is equally partitioned across configured entries. This trades
some space utilization for deterministic no-allocation replacement. A producer
LRU replaces only entries without queued/active references. Pending play commands
pin their resource before publication; completion, rejection, interruption and
cancellation release it. Cache allocation, bytes used, peak bytes, hits, misses,
evictions and retained references are observable. Cache budgets are limited to
64 MiB; streams to 65,536 stereo frames each. Event/ring capacities are powers of
two, so unsigned index rollover preserves ring position.

The mixer produces stereo float PCM. Mono and stereo input must match its
configured rate: resampling returns unsupported. PCM16 cache import is generic;
COHAUD11 import retains the accepted parser's two-second/1 MiB bound. The existing
native Vorbis decoder has its own compressed/decoded byte bounds. Streaming is a
real bounded SPSC decoded-PCM ring, with starvation silence, recovery, EOF drain
and generation-safe explicit close. Continuous long-file compressed music
decoding remains an off-thread adapter dependency; it is not implemented by
pretending that a short whole-file decode streams.

## Source provenance and compatibility

Read-only source: Ouroboros revision
`61bcde64ece0c45a1e3ba1c39f038b15dc6efd7d`,
`Game/src/sound/sound.c` and `sound_sys.c`.

| Original behavior | Module behavior / evidence |
|---|---|
| `sndSphereVolume` linear inner/outer radius, optional ignored ramp | Same scalar formula, 1,000 comparisons against unchanged extracted function; malformed radii are rejected at API boundary |
| `sphereGroupGetVolume` normalized listener-right panning and volume | 1,000 single-sphere 3D comparisons against unchanged function; maximum allowed software pan error 0.0002 due to reduction/quantization rounding |
| `volumeRatioToDb`, `volumeDbToRatio` truncate hundredths dB and clamp [-10000,0] | Reuse the accepted native source kernels; source gain comparisons included in spatial and mix references |
| `sndSysUpdateChannel` limits ordinary stereo pan to +/-2000 dB100 | Same pan domain, software channel attenuation approximation; DirectSound/HRTF sample output is not claimed |
| `sndFindBestSphereGroup` retains one sound per owner, requires interrupt to replace, steals quieter channel | Emitter ownership and interrupt rule retained; equal-priority full pools steal only quieter voices. An explicit higher-priority event can displace lower priority, an intentional new scheduling policy |
| FX, music, voiceover volume controls; ambient normally routes to FX | Four explicit FX/music/voice/ambient buses, initialized at unity for composability. Coordinator maps original user settings; ambient must receive FX settings where source behavior requires it |
| Source DirectSound rolloff effectively disabled, external sphere attenuation | Software sphere attenuation drives output gain; no second distance rolloff |

Source hashes and unchanged function hashes are in `host-proof.json`. The source
oracle compiles the original scalar/group/gain functions with a small type/vector
shim. For group comparison it selects one 3D sphere, no fade, no spatial variance,
maximum volume one, zero listener and X as listener-right. This does not qualify
all original owner-specific routing or multi-sphere merging. The software pan
balance cannot establish parity with the closed DirectSound mixer.

The authentic integration test uses the byte-pinned
`data/sound/ogg/player/headset_incoming_02.ogg`. All 79 existing codec dependency
file pins and the existing unsigned-shift overlay are verified before compilation.
The original Ogg memory callbacks and accepted decoder remain unchanged. Fresh
native decoding is compared to the accepted PCM reference (maximum one signed
16-bit LSB), then **three instances of that same authentic clip** play concurrently
through FX/music/voice buses and compare to an independent source gain oracle.
This is not a broad music/ambient/power sound corpus or speaker audibility proof.

## Threading and lifecycle contract

One owner produces cache/control operations. One producer writes a given stream
ring; one mixer consumer reads it. Callers must serialize producer APIs and
marshal game/decoder/lifecycle work to that owner. The only asynchronous control
exception is `coh_mixer_device_error`, an atomic request suitable for AAudio's
error callback. Lock-free atomics are required and checked at creation.

`coh_mixer_render` allocates, frees, blocks, decodes and invokes user callbacks
zero times. It accepts at most 8,192 frames, drains a bounded command snapshot,
starts events at exact audio frame positions, mixes bounded voice counts and
clips to [-1,1]. AAudio callback duration and missed callback budget counts are
measured separately from its backend xrun/consumption/presentation counters.
Invalid monotonic clock reads are counted, not converted to giant durations.
Backend transition waits have both a clock deadline and ten 50 ms attempts, so
clock failure/stagnation cannot leave an infinite wait.

Pause emits silence and freezes the audio simulation clock; it retains voices
for explicit resume. A stream starved of decoded PCM emits silence and keeps
its own read position, while cached voices continue. Device errors flush active
and pending audio, pause the mixer, and advance a device generation. They never
close backend objects from an audio callback.

For Android pause: enqueue `coh_mixer_pause(m,1)` on the producer, then close the
sink from its backend owner. On recreation enqueue resume and open a new sink.
For device failure: close consumes the error request with the callback stopped,
then explicitly resume/requeue appropriate game sounds and reopen. Close waits
for backend state transitions and closes on the owner. A failed platform close
retains the handle/context for retry. As in the existing accepted sink, the
platform close call itself has no application-side timeout/cancellation API.

Read diagnostics only with the producer and render callback quiescent; the
snapshot is deliberately not a racy live statistics API. Stop producers, close
the backend, then destroy the mixer. `destroy(NULL)` and closing a null sink are
idempotent; normal destruction consumes the pointer and callers must clear it.

## Validation

```sh
python3 native-android/engine/audio/check.py \
  --source-root /path/to/full/repository --output /tmp/audio-host.json
python3 native-android/engine/audio/check.py \
  --source-root /path/to/full/repository --sanitize --output /tmp/audio-sanitize.json
python3 native-android/engine/audio/android_build.py \
  --ndk /path/to/android-ndk-r28c --build-dir /tmp/audio-arm64 \
  --output /tmp/audio-android.json
```

Use `--codec-root` for an existing verified `decode/.deps` directory and
`--asset-root` for pinned `headset.ogg`/`audio.bin`. Defaults locate the recovered
read-only dependency/corpus checkpoint in this execution environment. No network
fetch or accepted-source modification occurs. `--no-authentic` explicitly runs
only a partial check and does not report authentic integration. All output paths
are caller chosen. C11 is required for standard lock-free SPSC atomics.

Host tests cover exact frame scheduling, mixed output, clipping, emitters,
priorities/interruptions, category gains, spatial updates, late events, cancellation,
pause/resume, device errors, cache eviction/pinning/stale handles, malformed data,
invalid rates/layouts/limits, queue saturation, stream wrap/EOF/starvation/recovery,
threaded SPSC publication and complete resource release. A linked allocator guard
asserts that callback execution calls no allocator. Linked allocation/free
accounting reaches zero after full mixer/codec teardown.

The extended test renders 120.001 simulated source-rate seconds with 32 voices,
constant 434,784 allocated bytes for its configuration and no realtime allocations.
It runs faster than real time on the host; that elapsed host time is diagnostic
only. It neither waits two wall-clock minutes nor proves sustainable Thor audio.
ASan/UBSan pass. LeakSanitizer cannot inspect `/proc/PID/task` in this execution
environment; the receipt records that limitation and the explicit allocation
accounting remains enforced. The host AAudio shim independently tests open/start,
configuration rejection, pause/reopen, device error, failed close/retry, stop
failure and clock-failure/stagnant-state limits. It does not simulate Android's
thread timing or qualify native backend behavior.

The NDK driver links the actual AAudio sink into a native AArch64 shared library,
API 26, with `--no-undefined`. It records source hashes, compiler, commands, ELF
header/dynamic linkage and library SHA. This is build evidence, not APK execution.

## Integration and rollback

The coordinator may opt-in `engine/audio/CMakeLists.txt`, or link `coh_mixer.c`
and existing `audio/coh_audio.c`, adding `coh_mixer_aaudio.c` and `aaudio` only on
Android. Avoid linking a duplicate definition of `audio/coh_audio.c` if its object
already belongs to another target. The module's CMake has no codec dependency.
Use the accepted decoder on a non-realtime worker and pass its owned result to
`coh_mixer_cache_decoded`, then immediately `coh_decode_release`. Asset identifiers
come from the generalized asset module; event emitters are stable game IDs.

Do not route accepted Session Client audio to this engine until a consolidated
opt-in test bridge validates three audible voices, left/right movement,
music/ambient/FX gains, interrupted playback, repeated background/foreground,
device route change, prolonged playback, xrun counts, latency and teardown on
Android and physical AYN Thor. Retain the old gate/sink and known qualified APK.
No gates 19–21 changes are required for library tests or the future isolated bridge.

Integrate the self-contained worker commit only after refetching the active
`native-android` branch and inspecting overlaps. Roll back through an additive
revert of this module/bridge; never reset history or replace prior receipts.

Remaining implementation work includes continuous compressed-stream decoding,
rate conversion, broader authentic sound corpus/routing, source voiceover ducking
and fade envelopes, multi-sphere merging/spatial variance, source max-volume
rules, Doppler/HRTF/reverb, and live diagnostics publication. Full game latency
and sustained underrun-free Android playback remain measured acceptance work.
