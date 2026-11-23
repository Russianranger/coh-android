# x86 track integration

Updated 2026-11-22 America/Chicago. Claude leads development (PR #11, issue #10).
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
- 0.13.68-69 published (APKs 42963857636 at 42728face, 43104941674 at 22d90d987): early zone start (inert in .68, runs in .69), PRoot patch 0004 as an option, ioctl probe. Thor 20261113 A/B/C: in world 339/361/235 s (client log), zone start 233/276/157 s, FPS 30-42/31-54/50-61, ioctl 46.8 to 0.8 us; save after travel not confirmed (app defect). HANDOFF "0.13.70".
- 0.13.70-73 published (APKs 43372592357, 43393932170, 43833348924, 44151200472 at bc90fb8b1): save-after-travel fix; fast server + second PRoot build default; PRoot patches 0005-0007; performance graphics reach the ARM64 client (0129). Thor 20261118 A/B/C: in world ~215 s, 60 FPS at the cap (28-31 with socket stops), zone server start 150 s. HANDOFF "0.13.74".
- 0.13.74-75 published (APKs 44405347043 at 2b0ade277, 44445389436 at b270ff434): animations on first use (`quickLoadAnims`), wineserver realpath cache; trusted `defnames.bin`, cooked collision mesh file, PRoot patch 0008. CI 44441077783: reopen zone start 27.3 s (95.5 in 0.13.73). Thor 20261120 A-D: zone start 55-76 s (150), meshes read back (`misses` 0), client connected 117-126 s after launch, cold trip 71 s; all four launches had the socket option off (23-60 FPS). HANDOFF "0.13.76".
- 0.13.76 (91) published (APK 44682583963 at df7719461): the app names options that differ from the recommended set (`options_off_recommended`, restore button); a spare zone server serves a request that differs only by `-transient`. CI 44678714431, first hand-over: spare warm in 25.0 s, trip's zone ready 15.1 s after the request (101.1 s on the default server, 44669805331); trusted 44673984201 reopen 32.4 s. Not yet on the Thor. 0.13.77 (92) published (APK 44708151316 at 3e78d005e): no `Defs`/`Menu` read-ahead, trusted message bins, map load profile; CI 44698417683 reopen zone start 23.6 s (32.4), 44703232069 spare warm 19.9 s, trip ready 15.2 s, stops 1.84 M (2.13 M). HANDOFF "For 0.13.77". 0.13.78 (93) published (APK 44744229704 at d27dbb7c9): library bounds files not read back; CI 44727685589 map load 5.2 s (6.6), bounds step 20 ms (1,837), reopen zone start 24.1 s; spare 44739226760 trip ready 15.1 s (first spare run 44732475821 lost CI's typed return command after the trip passed). HANDOFF "For 0.13.78".
- Thor 0.13.78 (exports 20261121-051955/-053448): client connected 127-169 s after launch, 60 FPS at the cap, zone server 44 s by its own clock, trips through the spare 33.9 s and 27.7 s (cold 65.8 s, back 11 s). 0.13.79 (94): spare recommended; zone servers get `FEX_X87REDUCEDPRECISION=1` (CI 44882642501 group load 7.2 s for 8.3); graph receipts checked ahead; client patch 0130. Published (APK 44902543863 at 3c9812a41); CI trusted 44897019107 main loop 20.1 s (21.5), spare 44899910978 trip ready 10.1 s (15.1, includes mesh cooking). Not yet on the Thor. HANDOFF "Thor test of 0.13.78".
- Thor 0.13.79 (exports 20261121-202117/-203001): 60 FPS; trips through the spare 30.7 s and 25.6 s to known zones, 67.7 s on a first visit (35.6 s graph install), 49.4 s in the next launch (another zone's marker invalidated the receipts); x87 option no measurable gain outside mesh cooking. 0.13.80 (95): marker out of the receipt, shared inputs walked once, every zone's graph made ready ahead (not exercised by CI). Published (APK 45133831884 at eacf78602); CI trusted 45125692618 reopen 23.6 s, spare 45129721358 trip ready 10.1 s; client patch 0131 in CI 45121536099: 341 of 508 group files loaded in full at every zone load, 6.4-7.5 s. HANDOFF "Thor test of 0.13.79". 0.13.81 (96) published (APK 45193693577 at ca58343c8): trip requests picked up twice a second (were every 5 s); two experimental options, off by default. CI 45175868959 prepared group files: object library 5.6-5.7 s read back for 6.4-7.5 s parsed, 9.9 s when writing; 45187469113 deferred beacons/PhysX ran on every zone (0.25 s of work in CI), trip ready 9.3 s, client world 3.7 s later (unexplained); trusted 45181648415 reopen 23.4 s. 0.13.80 and 0.13.81 not yet on the Thor. Prepared, unbuilt: client patches 0134 (group load split) and 0135 (transfer boundaries). HANDOFF "0.13.81 (96)".
