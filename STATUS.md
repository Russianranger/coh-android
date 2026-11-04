# x86 track integration

Updated 2026-11-04 America/Chicago. Claude leads development (PR #11, issue #10).
The ARM64 client is primary (user decision 2026-11-03); x86 is the shelved fallback.
Keep x86 Win32 servers, PhysX, ragdolls. Pre-releases user-approved; default branch main, settings unchanged.

- Merge order: sampler-review-fix → startup-60s → modern-runtime-qualification
  → m5-thor (b7806a6bd King's Row docs) → performance-path docs.
- P2/P3 sampler and Windows producer fixes included through 8dc2a66d72477b3c62227e572538b13f0e4f912b.
  See armport/notes/M5-SAMPLER-REVIEW.md and HANDOFF-X86.md.
- Last device result is .44: King's Row cold prep 656.024 s, request→arrival
  711.056 s, loaded render mean 25.63 FPS (11 complete windows).
  See armport/notes/M5-THOR-20261102-RESULTS.md and its export evidence.
- Both zone servers are x86; Atlas stays resident. Preparation swap pressure
  does not prove gameplay causation. No matched pre-port x86 baseline is supplied.
- Save committed, but Wine worker EACCES prevented proved owned cleanup;
  Atlas cache return failed and the data cache remained stranded.
- Historical .46 build40929292200/runtime40945708189/APK40952408285 succeeded;
  modern Thor build checks and retained-runtime execution have different scope.
- Startup instrumentation/ODBC reuse included; gain and ≤60 s remain unmeasured.
  Historical build41363927704 passed; runtime41372922907 rejected old 0119 pin
  before guest launch. Corrected pin and regression are included.
- .37 cleanup hardening ported at e50a0e42e; packaging admission at 263acad1f (dormant chain skipped).
- Local ArmPort445/modern53 and guest27/64/17 pass. Cleanup whole-/proc has one
  inherited host EACCES error, reproduced on pristine c86; guards remain intact.
- Full interactive:3048 run/69 failures/28 errors/31 skips before fixture repair.
  Affected rerun138:2 legacy GPU-policy failures, no errors/skips; full is not green.
- Exact source, preserved logs, skips, runtime pins, CI request: HANDOFF-X86.md and issue10.

## Performance rounds (Claude, 2026-11-03; PR #11, issue #10)
- Fast mode on: CI Atlas start −26/−32% (41588867344 vs 41584980465); CI-only creation re-parse (41630365042).
- 0.13.49 Thor (ARM64 client): FPS mean 45-48; Atlas ready 204/222 s (.44: 287 s); King's Row failed (cold mirror).
- 0.13.50 (APK 41712293048) Thor: King's Row reached (cold trip 562 s, return 50 s); session 2 Atlas cache
  refused (shared folders missing from the changed-root check): Atlas ready 444 s vs 297 s on .49.
- 0.13.51 published (APK 41750489814, runtime 41745666658): cache reuse fix, 10 FPS station cap (0121), thermal/tick/CPU
  evidence. Thor: King's Row NPCs jump (Atlas smooth), 60s °C, no audio (never had a device in the guest).
- 0.13.52 published (APK 41791858823, runtimes 41783448453/41787724875 passed, index hit 0.127 s): clock wrap 0123, 0122.
- 0.13.53: game audio (TRASC plugin + AudioTrack bridge), RSS. 41832716509/41838960420 failed logout: modal
  "Sound Script Errors" dialog → 0124. Published (APK run 41881826170). Thor: audio, King's Row, 2nd start 40.6 s OK;
  RSS client 2.2 GB, MapServer 1.8-1.9 GB each, total 6.3 GB; reopen check rejects training+Day Job combos (saves fine).
