# x86 track integration

Updated 2026-11-06 America/Chicago. Claude leads development (PR #11, issue #10).
The ARM64 client is primary (user decision 2026-11-03); x86 is the shelved fallback.
Keep x86 Win32 servers, PhysX, ragdolls. Pre-releases user-approved; default branch main, settings unchanged.

- Merge order: sampler-review-fix → startup-60s → modern-runtime-qualification → m5-thor (b7806a6bd) → performance-path docs.
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
- 0.13.50 (APK 41712293048) Thor: King's Row reached (cold trip 562 s); session 2 Atlas cache refused (444 s vs 297 s).
- 0.13.51 (APK 41750489814): cache reuse fix, 10 FPS station cap (0121). Thor: King's Row NPCs jump, no audio.
- 0.13.52 (APK 41791858823): clock wrap 0123, 0122. 0.13.53 (APK 41881826170): game audio (TRASC plugin), 0124.
- 0.13.54 (APK 41960891294 at a66b533f6): save check for ordinary play, pss_kib; shared heap 2/2 failed in session
  (41931773800, 41956900853) → off; external-maps DbServer passed in CI (41961253764). Thor (export 20261105-043833):
  save passed; King's Row cold 191 s at the station, trip 30 s; PSS≈RSS.
- 0.13.55 (APK 42037755195 at 81e81ddd0): stock zone travel, any zone, gear menu. Thor: monorail → weeklyTF assert (20261105-202806).
- 0.13.56 (APK 42169364145 at 85a8f9801): weeklyTF.cfg, -notwostagemapxfer; CI trip 101 ready 172 s. Thor (20261106-152038):
  King's Row reached (~3½ min), then the reopen budget rejected map 5 (monorail-only rule); "Map loading" notice stayed.
- 0.13.57 (APK 42281556221 at 8050afca8): every static zone, 0125, occupied probe; CI trip 101 ready 182 s. Thor (20261106-
  210545/220022): hero saved in King's Row; its start overlapped the client's → Android low-memory kill (reason 3, foreground).
- 0.13.58 published (APK 42329179898; build 42300265349, runtimes 42312362966/42316982535/42322788540 at 919e23760): Atlas
  first, saved zone at Enter Game (0126), storage mount-point repair; CI trip 167 s; r58/r58t passed on re-run. HANDOFF "0.13.58".
