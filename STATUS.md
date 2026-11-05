# x86 track integration

Updated 2026-11-05 America/Chicago. Claude leads development (PR #11, issue #10).
The ARM64 client is primary (user decision 2026-11-03); x86 is the shelved fallback.
Keep x86 Win32 servers, PhysX, ragdolls. Pre-releases user-approved; default branch main, settings unchanged.

- Merge order: sampler-review-fix → startup-60s → modern-runtime-qualification
  → m5-thor (b7806a6bd King's Row docs) → performance-path docs.
- P2/P3 sampler and Windows producer fixes included through 8dc2a66d72477b3c62227e572538b13f0e4f912b.
  See armport/notes/M5-SAMPLER-REVIEW.md and HANDOFF-X86.md.
- Last device result is .44: King's Row cold prep 656.024 s, request→arrival
  711.056 s, loaded render mean 25.63 FPS (11 complete windows).
  See armport/notes/M5-THOR-20261102-RESULTS.md and its export evidence.
- Both zone servers are x86. Swap pressure does not prove gameplay causation; no matched pre-port x86 baseline.
- Save committed, but Wine worker EACCES prevented proved owned cleanup;
  Atlas cache return failed and the data cache remained stranded.
- Historical .46 build40929292200/runtime40945708189/APK40952408285 succeeded (scope differs from modern Thor checks).
- Startup instrumentation/ODBC reuse included; gain and ≤60 s unmeasured. Historical build41363927704
  passed; runtime41372922907 rejected old 0119 pin before guest launch; corrected pin and regression included.
- Local ArmPort445/modern53 and guest27/64/17 pass. Cleanup whole-/proc has one
  inherited host EACCES error, reproduced on pristine c86; guards remain intact.
- Full interactive:3048 run/69 failures/28 errors/31 skips before fixture repair.
  Affected rerun138:2 legacy GPU-policy failures, no errors/skips; full is not green.
- .37 cleanup hardening e50a0e42e, packaging admission 263acad1f. Source, logs, skips, pins: HANDOFF-X86.md, issue10.

## Performance rounds (Claude, 2026-11-03; PR #11, issue #10)
- Fast mode on: CI Atlas start −26/−32% (41588867344 vs 41584980465); CI-only creation re-parse (41630365042).
- 0.13.49 Thor (ARM64 client): FPS mean 45-48; Atlas ready 204/222 s (.44: 287 s); King's Row failed (cold mirror).
- 0.13.50 (APK 41712293048) Thor: King's Row reached (cold trip 562 s, return 50 s); session 2 Atlas cache
  refused (shared folders missing from the changed-root check): Atlas ready 444 s vs 297 s on .49.
- 0.13.51 published (APK 41750489814, runtime 41745666658): cache reuse fix, 10 FPS station cap (0121), thermal/tick/CPU
  evidence. Thor: King's Row NPCs jump (Atlas smooth), 60s °C, no audio (never had a device in the guest).
- 0.13.52 published (APK 41791858823): clock wrap 0123, 0122. 0.13.53 published (APK 41881826170): game audio
  (TRASC plugin), 0124; Thor: audio, King's Row, RSS 6.3 GB total; reopen check rejected training+Day Job combos.
- 0.13.54 published (APK 41960891294 at a66b533f6; runtimes 41948749075/41952941661 passed): save check for ordinary play,
  pss_kib. Shared heap reserves 1 GB but 2/2 runs failed in session (41931773800, 41956900853) → keep off.
  External-maps DbServer passed creation/reopen in CI (41961253764). First APK 41935584201: 2 unreviewed helpers, fixed.
- 0.13.54 Thor (export 20261105-043833): save check passed; King's Row cold 191 s at the station, trip 30 s; PSS≈RSS.
- 0.13.55 published (APK 42037755195; build 41980185206, runtimes 41991355281/42020227060 at 81e81ddd0): stock zone travel,
  any zone, gear menu, controller map. CI zoning reopen unprovable on legacy MapServer (42029819713); HANDOFF "0.13.55".
