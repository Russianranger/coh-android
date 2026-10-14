# Native systems probe — phases 10–12

This separate Android package exercises three bounded native gates together:

| Gate | What executes | What remains outside this probe |
| --- | --- | --- |
| 10 | Original scalar editor-look and digital-key/joystick kernels, Android key/touch/controller event transport, and a diagnostic arrow | Gameplay camera, character motion, collision, player input integration |
| 11 | Source volume conversion, authentic client sound decoded to pinned PCM on the host, AAudio submission and consumption, interruption, stop/close and fresh reopen | Android compressed decoding, original mixer/spatial audio, speaker audibility and sustained audio performance |
| 12 | Source-compatible restricted legacy packet framing, packed-bit encoding, Blowfish, malformed-input and unaligned-buffer checks | Sockets, login/account transport, live server interoperability, compression and other packet profiles |

The app requests no network or microphone permission. Audio starts only from
an explicit Play action. The emulator's opt-in `autoSmoke` intent authorizes its
bounded playback checks. Pausing disables new playback and cancels the current
stream; the worker retains exclusive ownership of its stop and close.

## Device check

1. Run checks. Drag the arrow, then press and release a controller button. Move
   both sticks in all four directions; stick coverage is reported separately.
2. Play sound. Listen for the three source sound clips with a quieter middle
   clip. Press **Heard 3 sounds** only after hearing a complete playback.
3. Resize, then recreate the input view. Each real size callback triggers a
   fresh source check.
4. Start another sound playback and press Android Home immediately while it
   is playing. Return and play a complete three-clip sequence again.
5. Export the JSON when **SYSTEM GATES PASSED** appears.

The complete engine gate requires current foreground source checks, at least
three successful source runs across two actual sizes and two input view
generations, Android touch and key callbacks, and a same-session Home/return
receipt. The latter must identify the exact interrupted, started AAudio stream
and prove its cancellation, stop and close, followed by fresh foreground checks
and a complete fresh stream. An unrelated earlier cancellation cannot qualify.

`device_audible_confirmation_passed` is a separate user observation, never
enabled by the emulator or native frame counters. `controller_axis_coverage_passed`
is separate device callback coverage; emulator callback qualification does not
establish physical Thor controller operation.

The private report is `systems-probe-report.json`; an export is an immutable
snapshot taken before the Android document picker opens. Reports retain at most
400 events and 32 runs of each type. The loader limits metadata to 256 KiB and
PCM to 1 MiB, then requires exact byte count and SHA-256 from the fixture receipt.
The three gates qualify diagnostics only; they do not establish a playable
native City of Heroes client.

`tools/ui_host_check.py` tests the actual Java receipt-validation methods with
controlled data on a host JVM. It is separate from Android callback and AAudio
execution in the emulator workflow.
