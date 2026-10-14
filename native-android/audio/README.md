# Native audio gate 11

This bounded gate replaces one DirectSound sink with Android AAudio. It plays
the authentic `player/headset_incoming_02.ogg` client asset after host-side
decoding, three times at source volume ratios 0.6, 0.3 and 0.6, with 150 ms
silent gaps. Pressing Play is the only action that starts sound.

The asset is recovered through bounded ranges from the frozen Audio asset
volume. Size, ZIP member identity, CRC32 and SHA-256 must match the release
manifest. Whole archive digests remain release provenance; the bounded subset
reader does not claim to hash either whole archive locally.

Host preparation compiles the four unchanged memory callbacks from pinned
`ogg_decode.c` and calls `ov_read(..., 0, 2, 1, ...)`, the signed 16-bit
little-endian contract used by the original decoder. The result is 18,168 stereo
frames at 44,100 Hz. Exact PCM bytes and metadata are pinned. The original
compressed decoder does not run on Android in this gate.

Two unchanged `sound_sys.c` functions establish the source volume curve. The
hundredths-of-dB integer truncation is retained before converting dB back to
linear gain. The 0.6 and 0.3 inputs become -443 and -1045 hundredths of dB.
Host comparisons are exact. Native selfchecks allow 1e-6 absolute error in the
final float gain across libm implementations while requiring exact integer dB.
The PCM adapter rounds float-scaled samples to nearest/even. DirectSound's
internal sample rounding is not qualified.

The caller runs `coh_audio_play` on one worker. AAudio requested sample rate,
channel count and PCM16 format must equal the returned stream configuration.
The sink retains AAudio's default MEDIA usage and MUSIC content routing, so all
used AAudio APIs are available at the application's minimum Android API 26.
Partial writes preserve remaining frames. Stream submission, consumption,
underrun count and optional presentation timestamp are reported separately.
Those engine counters do not prove physical speaker audibility. Only the user
can acknowledge hearing the clip; an emulator never supplies that acknowledgement.

`coh_audio_set_foreground(0)` and `coh_audio_cancel()` are thread-safe cancellation
requests. The worker exclusively owns stop, wait and close; the UI never closes
a stream concurrently. The foreground flag prevents a queued Play from starting
after pause. Deliberate interruption must produce cancelled/closed evidence, and
a fresh subsequent Play must open and complete a new stream. A foreground sound
test is bounded by seven seconds plus 1.5 seconds of consumption drain and a
500 ms state transition wait.

Native Ogg decoding, music, voiceover, the client scheduler/mixer, attenuation,
Doppler, gameplay latency and sustained underrun-free playback remain later work.
