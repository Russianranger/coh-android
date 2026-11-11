# x86 track integration

Updated 2026-11-10 America/Chicago. Claude leads development (PR #11, issue #10).
The ARM64 client is primary (user decision 2026-11-03); x86 is the shelved fallback. Scope: single-player only (2026-11-10).
Keep x86 Win32 servers, PhysX, ragdolls. Pre-releases user-approved; default branch main, settings unchanged.

- Merge order: sampler-review-fix → startup-60s → modern-runtime-qualification → m5-thor (b7806a6bd) → performance-path docs.
- P2/P3 sampler and Windows producer fixes included through 8dc2a66d7 (armport/notes/M5-SAMPLER-REVIEW.md, HANDOFF-X86.md).
- Last x86-track device result (.44): King's Row cold prep 656.024 s, request→arrival 711.056 s, loaded render mean
  25.63 FPS (11 complete windows); see armport/notes/M5-THOR-20261102-RESULTS.md and its export evidence.
- Both zone servers are x86. Swap pressure does not prove gameplay causation; no matched pre-port x86 baseline.
- Save committed, but Wine worker EACCES prevented proved owned cleanup; Atlas cache return failed, data cache stranded.
- Historical .46 build40929292200/runtime40945708189/APK40952408285 succeeded (scope differs from modern Thor checks).
- Startup instrumentation/ODBC reuse included (build41363927704); gain/≤60 s unmeasured; old 0119 pin (runtime41372922907) fixed.
- Local ArmPort445/modern53, guest27/64/17 pass; whole-/proc cleanup: one inherited host EACCES (pristine c86), guards intact.
- Full interactive (unittest discover -s tools/android/interactive): 3289 run/86 failures/13 errors/36 skips at 0.13.67;
  not green. None new against 08c4b9c79 (3273/87/14/36 in a clean worktree); HANDOFF "0.13.67".
- .37 cleanup hardening e50a0e42e, packaging admission 263acad1f. Source, logs, skips, pins: HANDOFF-X86.md, issue10.

## Performance rounds (Claude, 2026-11-03; PR #11, issue #10)
- Fast mode on: CI Atlas start −26/−32% (41588867344 vs 41584980465); CI-only creation re-parse (41630365042).
- 0.13.49 Thor: FPS mean 45-48, Atlas ready 204/222 s (.44: 287 s). 0.13.50 (APK 41712293048): King's Row cold trip 562 s.
- 0.13.51-53 (APKs 41750489814/41791858823/41881826170): cache reuse, station cap 0121, clock wrap 0123/0122, audio 0124.
- 0.13.54 (APK 41960891294 at a66b533f6): ordinary-play save check; shared heap off (41931773800, 41956900853
  failed); external-maps DbServer CI 41961253764. Thor (20261105-043833): save passed; King's Row cold 191 s, trip 30 s.
- 0.13.55-56 (APKs 42037755195/42169364145): stock travel, any zone, gear menu; weeklyTF.cfg. Thor: King's Row ~3½ min.
- 0.13.57 (APK 42281556221 at 8050afca8): every static zone, 0125, occupied probe; CI trip 101 ready 182 s. Thor (20261106-
  210545/220022): hero saved in King's Row; its start overlapped the client's → Android low-memory kill (reason 3, foreground).
- 0.13.58-59 published (APKs 42329179898 at 919e23760, 42429765739 at 825bae059): saved zone at Enter Game (0126), mount
  repair; then no zone before Enter Game, only the character's own; Save survives its Enter (0127). HANDOFF "0.13.58"/"0.13.59".
- 0.13.60-61 published (APKs 42456241853 at 81b6cdfc0, 42516615576 at bd27744ed): FX step admits the shared `-zones` tree
  (Mercy Island start); Resume removes the unentered THORHERO; Lua fetch timeout (42488979665) fixed. HANDOFF "0.13.60"/"0.13.61".
- 0.13.62-63 published (APKs 42546944715 at 75523980e, 42566326193 at e679031ca): Ralakar in Mercy Island; any name,
  walking unlocked; Reopen no longer refused as station travel (check waits). HANDOFF "0.13.62"/"0.13.63".
- 0.13.64-65 published (APKs 42674721584 at 4f9e8eebe, 42724564742 at caf52c828): display updates above 1024
  rectangles (fast turns closed the game); Mercy Island navigation graph (run 42678203754). HANDOFF "0.13.64"/"0.13.65".
- 0.13.66 published (APK 42827583406; build 42809195810, runtime 42821819932 at d8f417ea8): map pack coh-navigation-maps-v1.0.0
  (64 zones). Thor 20261110-213045: pack bound, Mercy graph refused (linked inputs vs new lstat check). HANDOFF "Thor test of 0.13.66".
- 0.13.67 published (APK 42940665672; build 42922800561, runtime 42936024060 at 0c37bef41): Mercy graph check follows the phone's file links; launch receipts, folder index
  kept across updates, zone data cache returned, 60 cap from launch (0128). Phone gains unmeasured. HANDOFF "0.13.67".
