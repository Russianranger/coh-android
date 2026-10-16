# Consolidated AYN Thor test — Support Client 0.2.0 code 201

Use the ARM64 APK and SHA256 in `release.json`. Package identity is
`org.coh.nativesupport`. Keep Session Client 0.3.0, Combined Client and their data
intact. No server/account changes are needed. Do not clear data or uninstall an
existing app to work around an installation/signature error; report the error.
The build uses a fresh disposable test certificate, recorded in `release.json`.
A previously installed Support APK with another signer cannot be upgraded in
place. This does not affect the distinct Session or Combined packages.

1. **Wretch, landscape and WALK.** Confirm the compact toolbar leaves the scene
   visible. Walk with the left stick, look with the right stick, and check
   grounding/collision around the available station geometry. Under **Show
   controls**, toggle **View distance** between Near/Far. Capture a baseline
   screenshot. Observe missing geometry, flicker, input drift and stuck movement.

2. **UI and chat.** Tap **Panels** to cycle Details → Inventory → Enhance →
   Missions → Contacts. Inspect rows with touch and D-pad/left stick + A; camera
   movement should stop during panel interaction. B or **Close** dismisses a
   panel. Panels enables UI navigation; switch **UI navigation: OFF** before
   returning to walking. Open **Show controls**, enter **Chat text**, press
   **Send**, and confirm one local chat entry. Check source-font readability,
   health/endurance, target information and power-tray/cooldown presentation.

3. **Mock combat and animation.** Press **Mock hit** with Wretch visible: observe
   brief damage text, the mock target-health bar and authenticated Huge punch.
   Activate a ready tray slot and observe cooldown. No impact sound is expected:
   the hit-audio binding is unavailable. **Mock animation** cycles punch,
   jump-power preview, reaction and grounded locomotion. Jump animation does
   not implement jump physics. Capture a short video if animation looks wrong.

4. **Authentic Male preview.** Close panels and tap **Preview: Wretch** to switch
   to **Preview: Male**. Capture the eight-part costume and inspect missing parts,
   detached geometry, textures and flicker. This uses neutral morphology and a
   fixed camera; WALK/camera input is intentionally paused. Music and ambient
   remain background Wretch-scene audio. Tap **Preview: Male** to return.

5. **Lifecycle and audio.** Use **Recreate** once in each preview mode. Press
   Android Home and return three times, including while Male preview is active.
   Confirm rendering, chat/panel state and audio recover without stuck input.
   Start/pause another media app to exercise focus interruption. Connect and
   disconnect an available headphone/audio route; note silence, crackling, delay
   or restart failure. Mark route testing untested if no alternate output exists.

6. **Ten active minutes and reports.** Accumulate at least ten minutes in the
   foreground, alternating Wretch movement, Near/Far, panels, mock hits and brief
   Male previews. Background time does not count. **Export report** at about
   1, 5 and 10 active minutes and preserve each timestamped
   `COH-NativeSupport-…json`. Note whether frame pacing, responsiveness, audio or
   heat worsens. Reports include per-observation timestamps; a restarted renderer
   lifetime alone does not establish total active time.

Return all three JSON reports; Wretch, Missions/Contacts and Male screenshots;
any failure screenshot/video; approximate failure times; and pass/fail/untested
observations for controller, touchscreen, keyboard, focus, route and lifecycle.
Include device Android/build version and whether power/performance settings were
changed. Do not include credentials or unrelated app data.

Reports bind the installed package/build and expose rendering/presentation errors,
audio counters and independently sampled process memory. Preview memory values
are explicitly partial/source-payload observations; thermal readings and driver
residency are not inferred. Emulator execution cannot establish audible quality,
Adreno performance or physical controller behavior.

**Physical reports have now verified endurance/audibility, chat and Wretch/Male Surface recreation.** Use the [remaining checks after the 22:45 report](physical-thor-20261015/long-run-224517/REMAINING-TESTS.md); do not repeat the full procedure above. The full consolidated checklist remains open.
This qualifies only the bounded offline build: it does not establish complete
zones, Female/Huge costume coverage, authoritative combat or full-game FPS.
