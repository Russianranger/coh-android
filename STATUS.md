# x86 track integration

Updated 2026-11-09 America/Chicago. Claude leads development (PR #11, issue #10).
The ARM64 client is primary (user decision 2026-11-03); x86 is the shelved fallback.
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
- Full interactive (unittest discover -s tools/android/interactive): 3227 run/86 failures/14 errors/36 skips; not green.
  Same failures as 0.13.62, a subset of c07d94895's (3206/87/14/34); 0.13.63's modules pass (HANDOFF "0.13.63").
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
- 0.13.64 published (APK 42674721584; build 42653524766, runtime 42668990132 at 4f9e8eebe): Thor 0.13.63 fast
  turns closed the game (display update >1024 rectangles); decoder takes the U16 range. Mercy Island: no graph. HANDOFF "0.13.64".
- 0.13.65 published (APK 42724564742; build 42705346414, runtime 42719564293 at caf52c828; graph 42678203754):
  Mercy Island navigation graph (407,100 beacons, CRC 0x086f500e) so pets/NPCs path there. HANDOFF "0.13.65".
- 0.13.66 (81) in CI: every zone's navigation map as an importable pack (owner 2026-11-09: one run, <=8 jobs). 3 workers:
  Mercy 4596 s vs 8413 s (pilot 42731367743: maps 55/71/72 passed); full run 42743592550 (61 maps). HANDOFF "0.13.66".
