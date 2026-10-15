# Gate 43 continuation: compressed streaming and rate conversion

Status: implementation and host qualification; Android ARM64 library built.
Android execution and physical Thor acceptance are separate coordinator/device
checks. This extension does not mark gate 43 complete. Existing 32-voice mixer,
AAudio sink, source decoder, accepted audio gates and Session Client are unchanged.
The primary coordinator's unpublished `coh_audio_session.{h,c}` lifecycle owner
was inspected read-only and is reused by the consolidated Android harness.
There is no competing lifecycle controller, JNI, workflow or protocol change.

`coh_music.h` is the streaming control API. A borrowed random-access source may
read a file, asset-pack span or memory. It need not retain/copy a whole compressed
file. Open validates complete original Ogg pages, CRC, sequence, serial and EOS,
then opens the already qualified pinned libogg/libvorbis. Unsupported chained
streams, invalid channel/rate metadata, truncation and source read failures are
rejected. Compressed source limit is caller chosen up to 512 MiB; source duration
is limited to 24 hours. Open scans compressed pages and builds the codec's seek
index off the callback; this favors integrity and deterministic failure over
instant startup. Cancellation is polled between pages and bounded pump steps.

Pump decodes signed16 little-endian Vorbis chunks, converts rate on the owner,
and writes the existing bounded mixer stream ring. Fixed 2,048-sample input and
output buffers bound retained PCM independently of music length. No whole-file
PCM output is created. Backpressure retains the output chunk and returns
`COH_LIMIT`, without continuing to decode. Pump bounds actual decoder calls to
the requested 1..32 and bounds conversion/submission steps. A loop performs
`ov_pcm_seek(0)` on the owner; the resampler phase and mixer stream remain
continuous. EOF drains fractional resampler output, then marks mixer EOF.

`coh_resample.h` implements mono/stereo PCM16 rate conversion from 8..192 kHz,
with no allocation. The explicit rational phase gives identical output for
different caller chunk sizes. Linear interpolation and final sample hold are
intentional new portable adapter policies. This is not DirectSound sample parity
or a bandlimited resampler. High-frequency downsampling may alias, so a later
lowpass/polyphase adapter is needed before broad musical fidelity acceptance.

## Ownership and Android integration

One serialized non-realtime mixer control/decoder owner calls music APIs. The
source, its context and borrowed mixer must outlive successful music close.
Pump/source callbacks and codec operations never run from AAudio or the mixer
render callback. The existing mixer remains the only SPSC publication boundary.
All allocation/free, decode, disk access and cancellation polling happen on the
owner. Source mutation during playback violates the immutable source contract.

For the opt-in consolidated harness:

1. Configure mixer rate to 48 kHz (or the explicitly supported device rate),
   stream ring 16,384 frames and chunk size 256. Chunk size must fit the ring.
2. Open verified `atlasplaza.ogg` with loop enabled. Prefill with bounded pump
   calls until ring backpressure, then publish `coh_music_event` on MUSIC.
3. Open verified `steam1.ogg` on AMBIENT, set spatial/radii/position on the
   returned event, and play authentic cached headset audio on FX if desired.
   Original ambient routing normally uses the user's FX volume; the future game
   binding must copy that setting to AMBIENT rather than invent new source rules.
4. Pump every 16..30 ms on the owner while the existing AAudio sink renders.
   Poll `CohMusicReport` there. Mixer diagnostics still require suspended/joined
   callbacks; never inspect its live non-atomic counters during playback.
5. Supply foreground/audio focus to the primary lifecycle session owner. Surface
   loss alone is not an audio pause event. Suspend retains stream buffers and
   freezes audio time. Device errors flush voices through the existing sink;
   explicit recovery/requeue remains the primary owner's responsibility.
6. Stop emitter/cancel externally; let render retire references, close/join the
   backend on its owner, then close music and destroy the mixer. `COH_STATE` on
   music close retains the handle for retry while a voice/pending event owns it.

`CMakeLists.txt` adds only the streaming extension and links existing
`coh_game_audio`/`coh_pinned_vorbis` targets. Add those once before this target;
do not create duplicate codec or source gain symbols. Standalone check's NDK
path directly links the extension, unchanged mixer/sink and same codec sources
into `libcoh_stream_audio.so` API 26, with `--no-undefined`.

## Source provenance and authentic corpus

Read-only Ouroboros revision `61bcde64ece0c45a1e3ba1c39f038b15dc6efd7d`,
`Game/src/sound/ogg_decode.c` SHA256
`6a37c461d45b46b89c2feefe7edb43ae693d8465f58bf49e4b696a27cc32b5de`.
The source `oggDecode` requests bounded `ov_read(...,0,2,1,...)` signed16 LE PCM.
This extension preserves that conversion and the qualified codec pins/unsigned
shift overlay; it replaces the whole-clip wrapper with incremental owner reads.
The generalized file callbacks adapt the original fread/seek/tell convention
to an immutable read_at source and wider offsets. The strict complete-file CRC
policy follows the accepted native decoder, and deliberately rejects codec hole
resynchronization. Source `sndSphereVolume`, gain and panning kernels remain in
the existing mixer; tests compile unchanged extracted scalar oracles.

`acquire.py` reuses existing HTTPRange/Subrange ZIP readers. Only 960,534 bytes
of the 848 MB published audio pack were transferred. The selected sounds are
verified against the original pinned manifest SHA, their size/SHA and ZIP CRC.
The complete outer/inner ZIP digest was not recomputed from partial ranges.

| Original asset | Compressed bytes | Source audio | SHA256 |
|---|---:|---|---|
| `data/sound/ogg/music/atlasplaza.ogg` | 256,209 | Stereo 44.1 kHz, 688,128 frames, 15.603810 s | `1a9f7ee21bc425508eb2e4a17c6ac66c04059ee6f0b0e4d0517ba3e1095c7bf7` |
| `data/sound/ogg/city/steam1_loop.ogg` | 42,318 | Mono 44.1 kHz, 166,812 frames, 3.782585 s | `176bfd08df6a17af558157ad1934d23c92aaaa81d7428e2e04d1250cfa0c6821` |
| `data/sound/ogg/player/headset_incoming_02.ogg` | 12,930 | Stereo 44.1 kHz, 18,168 frames | Existing accepted decoder/PCM pins |

Atlas Plaza decodes to 2,752,512 PCM bytes, exceeding the old whole-clip decoder's
1 MiB bound; the extension streams it using the same 9,456-byte fixed adapter
allocation as the 0.412-second headset clip. Codec allocations remain separate
and off callback. The adapter retains no whole-file compressed or PCM copy.

## Qualification

```sh
python3 native-android/engine/audio/android-integration/acquire.py \
  --output /tmp/coh-audio-stream-corpus
python3 native-android/engine/audio/android-integration/check.py \
  --source-root /path/to/full/repository --stream-corpus /tmp/coh-audio-stream-corpus \
  --output /tmp/audio-stream-host.json
python3 native-android/engine/audio/android-integration/check.py \
  --source-root /path/to/full/repository --stream-corpus /tmp/coh-audio-stream-corpus \
  --sanitize --output /tmp/audio-stream-sanitize.json
python3 native-android/engine/audio/android-integration/check.py \
  --source-root /path/to/full/repository --stream-corpus /tmp/coh-audio-stream-corpus \
  --ndk /path/to/android-ndk-r28c --build-dir /tmp/audio-stream-arm64 \
  --output /tmp/audio-stream-arm64.json
```

Use `--codec-root`/`--asset-root` for the existing verified codec/headset corpus.
The long corpus is optional only for an explicitly partial test. FFmpeg is used
as an independent native Vorbis decode oracle for long music/ambient; expected
PCM is computed afresh, never played as fallback. Its reference bytes exist
only in temporary host test storage. They are not embedded in the engine/APK.

Tests cover 49 input/output rate combinations, mono/stereo, randomized chunking
and an independent double-precision interpolation oracle; authenticated decoded
headset reference; both complete long files at 48 kHz (maximum observed independent
FFmpeg difference 1 signed16 LSB); three distinct authentic sources mixed together
on MUSIC/AMBIENT/FX with source gain comparisons and positional emitter reversal;
backpressure, EOF, stale active-reference close, cancellation, invalid rates,
truncation, CRC corruption, source failure and zero-capacity input semantics.
The 120 simulated-second decoder/loop stress includes 45 pause/resume cycles,
5,760,000 output frames, 291 rewinds, no underruns, no audio-thread allocations,
and stable 461,146 tracked live heap bytes at every stress checkpoint. A linker
allocator guard rejects allocate/free during render and requires zero tracked
allocations/bytes after full codec/mixer teardown. Tracking covers linked
application+codec allocations, not hidden allocations inside libc or a driver.
The stress runs faster than real time on a host and establishes no Thor timing.

Committed receipts separately record host, sanitizer and Android build results.
ASan/UBSan tests include the actual codec and complete cleanup; the receipt
states any environment restriction on LeakSanitizer rather than claiming it ran.

## Physical test plan and remaining work

Use the coordinator's single opt-in APK with mock gameplay. Confirm continuous
Atlas Plaza music across file boundaries; audible steam panning left/right as
the emitter moves; simultaneous headset FX; music/ambient/FX gain changes;
touch/controller interaction while sound runs; repeated Home/resume and focus
loss; audio route changes; clean teardown and replay. Run at least 5 minutes,
exporting sink callback times/xruns/presentation timestamp, decoder backpressure,
stream underruns, source error/cancel state and retained-resource counts after
suspend/close. Android emulator execution cannot establish physical audibility,
Bluetooth/USB route behavior, latency or long-run Thor underrun acceptance.

Remaining work: bandlimited resampling, source music fades/ducking and original
multi-sphere owner routing, wider source corpus, compressed streaming startup
cost profiling, Doppler/HRTF/reverb, measured Android latency and sustained
playback qualification. Full game performance is outside this module's evidence.

## Integration and rollback

Only new extension files are owned here. Coordinator refetches remote and checks
intervening audio additions before integrating this local commit. The primary
audio lifecycle files and all networking/authentication/session code stay
untouched. Keep this extension opt-in until combined Android checks pass.
Rollback removes the harness's optional link/adapter or additively reverts this
extension commit, after dependency review. Never reset branch history, overwrite
old qualification receipts or replace accepted Session Client 0.3.0.
