# AYN Thor: native systems gates 10–12

Use **CoH Native Systems Probe 0.1.1** (`org.coh.systemsprobe`), ARM64.
This is the next diagnostic after the accepted World Probe 0.1.1. It tests
native input, authentic audio playback and offline packet framing together.
It does not yet log into the server or render a playable City of Heroes world.
No game installation, asset import or server startup is needed for this probe.

## Install

Install `CoH-Native-Systems-Probe-0.1.1-arm64.apk`, then open **CoH Native
Systems Probe**. The World, Character and other probes have separate package
names and can stay installed. The production launcher also stays separate.

If Android reports a signature conflict with an earlier *Systems Probe*,
export any existing Systems Probe report and uninstall only **CoH Native
Systems Probe** before installing this APK. These diagnostic CI builds use
isolated debug keys. Do not uninstall the production launcher or erase its data.

## Test in one session

1. Tap **Run checks**. Drag the blue arrow left, right, up and down, releasing
   after each drag. Press and release a Thor controller button, such as **A**.
   Circle **both** sticks through their full range, then release them to center.
2. Tap **Play sound** and let it finish. You should hear three short game sound
   clips; the middle clip is quieter. Then tap **Heard 3 sounds**. Raise media
   volume if necessary; tap the confirmation only if you heard all three clips.
3. Tap **Resize**, wait for its checks to finish, then tap **Recreate** and wait
   again. The controls are in a horizontal row: swipe that row to reveal buttons
   beyond the right edge.
4. Tap **Play sound**, then press Android **Home while the sound is playing**.
   Return to the app without force-stopping it. Tap **Play sound** again and let
   the full three-clip sequence finish. If Home was too early or too late, repeat
   this step; the interrupted stream must actually have started.
5. Wait for **SYSTEM GATES PASSED** and for the separate stick coverage and
   audible confirmation to be complete. Tap **Export report**, save the JSON
   somewhere easy to find, and attach it with your observations.

## What to report

State whether the left stick changed the **Held** input value and the right
stick rotated the arrow, whether held values cleared and rotation stopped
when released, whether all three sounds were audible, and whether Home/return
recovered. Send `COH-NativeSystems-*.json` even if a check remains pending or
fails. A screenshot of the final status can help identify a missing action.

The exported report must have all these fields `true` for Thor acceptance:

| Field | Evidence |
| --- | --- |
| `qualification_passed` | Current source checks, actual touch/button callbacks, resizing, recreation and active-audio Home/return recovery |
| `input_gate_passed` | Source input and Android callback checks |
| `audio_engine_gate_passed` | Source audio and clean AAudio play/cancel/close/reopen |
| `protocol_gate_passed` | Restricted offline packet framing checks |
| `controller_axis_coverage_passed` | All four directions on both physical sticks |
| `device_audible_confirmation_passed` | Your **Heard 3 sounds** confirmation |

`session_failures` must be zero. **SYSTEM GATES PASSED** describes the engine
checks; it does not replace the two separate physical controller/audibility
checks. Emulator results never establish either physical observation.

If a backend error occurs, export that failing report first. A later playback
must not erase the failure. After preserving the report, close and relaunch this
probe to start a fresh test session if needed.
