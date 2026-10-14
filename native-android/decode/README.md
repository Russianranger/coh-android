# Gate 13: native compressed Ogg decoding

This component consumes the authentic 12,930-byte
`data/sound/ogg/player/headset_incoming_02.ogg` on the device. It decodes into an
owned `COHAUD11` buffer and passes that result to the accepted `coh_audio_play`
sink. The trusted reference is comparison-only; failure never plays it.

The codec revisions are the original client dependency pins in
`upstream/ouroboros/cmake/dependencies/Vorbis.cmake`:

- Ogg: `be05b13e98b048f0b5a0f5fa8ce514d56db5f822` (1.3.6).
- Vorbis: `0657aee69dec8508a0011f47f3b69d7538e9d262` (1.3.7).

`dependency-pins.json` fixes archive identities and all 79 selected source/header
files. `tools/decode_fixture/acquire.py` verifies them, generates fixed-width Ogg
types and prepares the ignored `.deps` directory. It runs at build time; the
application has no network dependency. Both BSD licenses are in `licenses/` and
must be included in the APK's third-party notices.

`source_callbacks.inc` retains the four original callback function bodies
unchanged. The bounded adapters instrument their use and stop after 8,192 calls.
The source `ov_read(...,0,2,1,...)` parameters remain signed16 little endian.
Additional Ogg page checks require every page CRC, consecutive page numbers,
exact source exhaustion, one serial/stream and a complete EOS. The wrapper
caps compressed input at 1 MiB and the owned PCM+header blob at 1 MiB, rejects
unsupported rates/channels, compares declared/actual frames, and clears every
successfully opened decoder exactly once.

One deliberate codec adaptation is generated from the verified source:
`sharedbook.c:425` casts `i` to `ogg_uint32_t` before shifting it into the sign bit.
UBSan exposed undefined signed-shift behavior on the valid fixture. This narrow
cast defines the intended unsigned bits; its source and overlay hashes and exact
replacement are recorded in the acquisition receipt. Codec sources otherwise
remain unchanged. Codec internals retain their own allocations; the limits here
bound input/output and callback count, rather than claiming a codec heap cap.

PCM comparison has a fixed maximum error of one signed16 LSB, declared before
running the tests. This allows native libm/SIMD rounding at integer quantization
boundaries; metadata, frames, header and sample count must match exactly. Every
compared sample contributes maximum, differing count, absolute/squared sum and
RMS error. On sanitized x86_64, 20 of 36,336 samples differ from the accepted
system-library reference by exactly one LSB (RMS 0.023460995672); the derivative
is byte-exact to the original callback wrapper built with the same pinned codec.
This is a numeric comparison, not evidence that the physical speaker is audible.

## Integration

```sh
python3 native-android/tools/decode_fixture/acquire.py
```

Add `decode/` as a CMake subdirectory and link `coh_native_decode`. It exports
`coh_decode.h`. Use a zero-initialized `CohDecodedAudio`, check
`coh_decode_ogg` and `coh_decode_compare_reference`, play its `data/length`, and
call `coh_decode_release` after playback or cancellation finishes. Each caller
owns its result; there is no shared decoder state. `coh_decode_selftest` covers
metadata/PCM, exact one-close cleanup, repeated decode/release, truncation,
CRC-corruption, a CRC-valid malformed identification packet and input limits.

## Host checks

```sh
python3 native-android/tools/decode_fixture/prepare.py \
  --corpus CORPUS --reference ACCEPTED_AUDIO_BIN --output FIXTURE_DIRECTORY
python3 native-android/tools/decode_fixture/build_host.py \
  --corpus CORPUS --reference ACCEPTED_AUDIO_BIN --output HOST_BUILD --sanitize
```

The second command instruments the decoder and codec with ASan and UBSan,
rejects all 12,930 truncated prefixes, reaches the decoder with CRC-valid hostile
identification packets, exercises 160 CRC-valid payload mutations and 64 repeated
owned decodes. It compares the native result byte-for-byte to the unchanged
callback source wrapper, then compares both to the trusted PCM within the fixed
one-LSB limit. Each process has a 60-second deadline. LeakSanitizer cannot run
under this execution environment's ptrace; this limitation is recorded, while
ASan and UBSan remain enabled with immediate abort. Repeated one-close cleanup
is tested; no complete heap-leak qualification is claimed.

This gate does not implement the full sound scheduler/mixer, multiple audio
assets, streaming music, spatial sound or native gameplay.
