# M5: one-install Thor play test (preparation only)

This is a proposed test, not a request to install now or evidence of a pass.
PORT-PLAN.md defines M5 as one installation and about ten minutes of play on
Thor. HANDOFF.md section 6 requires user approval before APK build/signing.
M4 run 40176336731 passes guest creation/reopen and host continuity; review
and physical Android surface validation remain pending. No installable ArmPort
APK is qualified. See M4-REPORT.md.

## Before asking for the device test

The developer must finish and cite M3's rendered Atlas screenshot and accepted
replay evidence, M4's full creation/save/restart/reopen and continuity checks,
and the corresponding reviewer decisions. Keep build success separate from
these exit criteria. Record the exact source, client/data donor runs, runtime
pins and accepted APK hash in the eventual test instructions.

After those checks, obtain the existing required APK/signing approval if it
has not already been granted for this exact action. Verify the selected
package/application ID and installation behavior before giving an install
command: never assume it can safely replace the user's existing CoH app.
Preserve existing app data/imports/saves and provide a rollback route before
installation. Do not ask the user to clear app storage or uninstall to fix a
failure. Validate the actual final UI labels and export path in the qualified
build; this plan intentionally does not invent them.

## One focused device session

1. Install the approved, hash-identified APK once. Confirm the build identity
   and ARM64 client selection before launch. Record the Thor Android version
   and display/controller setup used.
2. Reuse the qualified imports/setup path, enter Atlas with a test character,
   and capture a frame showing the rendered world and character. Record time
   to usable world separately from installation and preparation time.
3. Play for about ten minutes: move and turn the camera, open/close inventory
   and powers, target an NPC, and use an available basic power where appropriate.
   Note missing textures, visual corruption, input problems, audio faults,
   stalls, crashes and any device temperature/performance observations.
   These observations establish only this session, not performance guarantees.
4. Use ordinary logout/save. Reopen the same character without reinstalling
   or resetting data; confirm identity and expected saved progress. Keep the
   failure evidence if reopen fails rather than retrying over the report.
5. Stop through the app's normal control and export the complete report plus
   screenshots. Confirm the app finishes cleanup and does not leave a stuck
   game/server notification. No zone travel or unqualified renderer option is
   required for this initial test.

## Completion record

The developer must pair the user's observed play interval with the exact APK
identity, report/session identity, native ARM64 client identity, rendered-world
capture, normal save/reopen evidence and cleanup result. Any missing evidence
stays explicitly pending. Review results against PORT-PLAN.md before marking
M5 complete; CI and an APK download alone cannot establish a physical pass.
