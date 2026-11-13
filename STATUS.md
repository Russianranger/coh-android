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
- Fast mode: CI Atlas start −26/−32% (41588867344 vs 41584980465). 0.13.49 Thor: FPS mean 45-48, Atlas ready 204/222 s.
- 0.13.50-54 (APKs 41712293048/41750489814/41791858823/41881826170/41960891294): cache reuse, 0121-0124, audio, ordinary-play
  save check; shared heap off. Thor 0.13.54 (20261105-043833): save passed; King's Row cold 191 s, trip 30 s.
- 0.13.55-56 (APKs 42037755195/42169364145): stock travel, any zone, gear menu; weeklyTF.cfg. Thor: King's Row ~3½ min.
- 0.13.57 (APK 42281556221 at 8050afca8): every static zone, 0125, occupied probe; CI trip 101 ready 182 s. Thor (20261106-
  210545/220022): hero saved in King's Row; its start overlapped the client's → Android low-memory kill (reason 3, foreground).
- 0.13.58-59 published (APKs 42329179898 at 919e23760, 42429765739 at 825bae059): saved zone at Enter Game (0126), mount
  repair; then no zone before Enter Game, only the character's own; Save survives its Enter (0127). HANDOFF "0.13.58"/"0.13.59".
- 0.13.60-63 published (APKs 42456241853, 42516615576, 42546944715, 42566326193): shared `-zones` tree admitted (Mercy Island start);
  Resume removes the unentered THORHERO; any name, walking unlocked; Reopen not refused as station travel. HANDOFF "0.13.60".."0.13.63".
- 0.13.64-65 published (APKs 42674721584 at 4f9e8eebe, 42724564742 at caf52c828): display updates above 1024
  rectangles (fast turns closed the game); Mercy Island navigation graph (run 42678203754). HANDOFF "0.13.64"/"0.13.65".
- 0.13.66-67 published (APKs 42827583406 at d8f417ea8, 42940665672 at 0c37bef41): map pack coh-navigation-maps-v1.0.0 (64 zones); Mercy graph check follows the
  phone's file links; launch receipts, folder index kept, cache return, 60 cap (0128). Thor 20261111-035325: graph verified, pets path; in world 923 s. HANDOFF "Thor test of 0.13.67".
- 0.13.68-69 published (APKs 42963857636 at 42728face, 43104941674 at 22d90d987): early zone start (inert in .68, runs in .69), PRoot patch 0004 as an option, ioctl probe.
  Thor 20261113 A/B/C: in world 339/361/235 s (client log; app +70 s, server log delay), zone start 233/276/157 s, FPS 30-42/31-54/50-61,
  ioctl 46.8 to 0.8 us; save after travel never confirmed (app defect). HANDOFF "0.13.70".
- 0.13.70 published (APK 43372592357; build 43353706777, runtime 43368553729 at a774abd0d): save-after-travel fix; fast server + second PRoot build default (new keys); PRoot patch 0005
  (stop counts, getsockopt filter); client timeline; zone graph receipt. CI stop counts (43363707492): newfstatat 36 %, readlinkat 17 %, accept 17 %. HANDOFF "0.13.70".
- 0.13.71 published (APK 43393932170; build 43373369060, runtime 43389182271 at ade9f7cde): PRoot patch 0006 (accept untraced; stop counts by program); CI 11.8 M stops per reopen (14.2 M before). HANDOFF "0.13.71".
