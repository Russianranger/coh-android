# COH-ArmPort status

Updated 2026-10-28. Branch armport/m5-thor; PR #8 remains draft, M5 unaccepted.
Original client runs as an ARM64 Windows program in the app's ARM64 Wine.

- M0/M1/M2 merged (PRs #3/#4/#5); details: armport/M1-REPORT.md and M2-REPORT.md.
- M3 merged (PR #6): final build 40407492746/replay 40407492734 passed partial
  state scope; world rendered, completeness false, textures incomplete.
- M4 app runtime accepted/merged (PR #7, review 5660940046); armport/M4-REPORT.md.
- Last device-tested candidate: 0.13.44, APK run 40743596575/artifact 12840043807,
  sha256 2cf80a03a0161fc42581147f0c75d8f22ea2ad93fc8884c9abab5c72388e5c1b.
  Build 40724321192/requalification 40736589404 passed; review 5687848443 approved
  that APK only. Retained 0.10 CI is not full 0.13.x runtime/device validation.
- Thor results recorded by previous lead: combat, defeats, zoning, save work;
  12–30 FPS (window mean 22.8); ~12 min warm startup, MapServer 9.5 min critical path.
  King's Row NPC/car stutter remains; server contention is a hypothesis to measure.
- Task A audit posted: PR #8 comment 6480628043; armport/notes/M5-ASTRA-ANALYSIS.md.
  Sequencer “Reading” logs precede cache lookup: not proof of disk loads.
  Java already knows ARM64; confirmed defect is manual/bounded interaction policy.
- CI-qualified, awaiting Claude review: 0.13.45/code 60 at 0bf31c81b,
  build 40776745390 (8 jobs), requalification 40786315414 (4), APK 40791416254.
  Artifact 12860779714; APK 80,919,462 bytes, sha256
  1ff2252876def6cfeb28d33490d8c2f5d5952c330698d6a719fb67a2197b3959.
  Host CPU/tick-counter telemetry, manual-session
  acceptance correction, preservation of both Wine and cache cleanup failures.
  No native/runtime-pin changes. Longest ticks/file-load/Wine request counts
  remain unavailable until a separately qualified native producer is integrated.
- Local command: PATH=<javac-module-wrapper>:$PATH python3 -m unittest discover
  -s armport/tests -p 'test_*.py':292 passed. No 0.13.45 Thor result yet.
- Native 0119 timing producer held in isolated patchwork/server-metrics branch;
  extracted ASan/UBSan controls pass, upstream negative fails as expected.
  Packaging must preserve distinct retained 0.10 and Thor server ancestry.
- Next: Claude candidate review before APK handoff; native server timing and
  package integration continue on armport/server-metrics (c86a57962 checkpoint).
- Remaining: prior-zone retirement, DbServer wait cost, ARM64 servers, persistent
  folder cache, late data-stage launch, enhancement additions and cleanup proof.
  Esync requires a proposal before changing the pinned runtime.
- Reduced client features remain: no PhysX ragdolls, CgFX effects, runtime DXT.
  No releases/protected-branch changes. See armport/M5-HANDOFF.md and M5-THOR-TEST.md.
