# Game audio: guest ALSA to Android AudioTrack

The game client plays through DirectSound; Wine's ALSA driver (`winealsa.drv`)
needs a playback device, and the guest has none ("Unknown PCM default",
"Couldn't start DirectSound, continuing without audio" in every export up to
0.13.51). This directory adds the device.

- `pcm_trasc.c`, `audio-LICENSE` (MIT), `audio_receiver.py` and
  `check_audio_native.py` are unchanged copies from the owner's TRASC project,
  [trasc-server-android@99e8c86](https://github.com/Russianranger/trasc-server-android/tree/99e8c86fa2666c8d4da6c52f4b6f45160aa6d795)
  (`native/` and `tests/`), also used by
  [lsb-android](https://github.com/Russianranger/lsb-android) on the Thor.
- The plugin is an ALSA `ioplug` playback endpoint. ALSA `plug` converts
  Wine's format to 48 kHz stereo S16_LE. It connects to the app-private
  filesystem socket in `TRASC_AUDIO_SOCKET` and speaks a small request/reply
  protocol (little-endian words): open `{0x50414c54, 1, 48000, 2, buffer
  frames}`, then 1 start, 2 stop, 3 playback head, 4 write `{frames}` + PCM
  (reply: frames accepted, non-blocking on Android), 5 prepare. Android's
  AudioTrack playback head is the clock.
- `build.sh` builds it in `debian:bookworm-slim` (the guest root filesystem's
  release) on an ARM64 host and runs `check_audio_native.py` against real
  alsa-lib (48 kHz stereo, 22.05 kHz mono and 44.1 kHz conversion, a pause
  that empties the ring, drain and reconnect).
- The Android side is `ClientAudio.java` (adapted from lsb-android's
  `AudioBridge`, `AudioPcmSession` and `AudioBufferPolicy`). The guest side is
  `armport_interactive.ArmPortClient.client_audio_environment`.
