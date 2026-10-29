# COH-ArmPort status

Updated 2026-10-29 CDT. Experimental server metrics + review fixes; PR #8 remains draft, M5 unaccepted.
Original client runs as an ARM64 Windows program in the app's ARM64 Wine.

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
- Claude-approved .45/code 60 (review 5692088051) at 0bf31c81b,
  build 40776745390 (8 jobs), requalification 40786315414 (4), APK 40791416254.
  Artifact 12860779714; APK 80,919,462 bytes, sha256
  1ff2252876def6cfeb28d33490d8c2f5d5952c330698d6a719fb67a2197b3959.
  Host CPU/tick-counter telemetry, manual-session
  acceptance correction, preservation of both Wine and cache cleanup failures.
  No native/runtime-pin changes. Longest ticks/file-load/Wine request counts
  remain unavailable until a separately qualified native producer is integrated.
- 0.13.46/code 61 development: opt-in serial Win32 producer, exact two-variant
  qualification, guest admission and bounded native-console export are wired.
  Build 40805020119: 9 jobs passed; Windows import of fcntl failed before MSVC.
- Local command: PATH=<javac-wrapper>:$PATH ARMPORT_SERVER_BASELINE_ROOT=<c86>
  python3 -m unittest discover -s armport/tests -p 'test_*.py': 419 passed; 61 lifecycle tests pass.
  Extracted retained-source ASan/UBSan controls pass; original control fails.
- P2/P3 fixed locally; bounded launch history added, retirement stays disabled.
  Windows host admission and CRLF-cache fixes tested; full revised CI chain pending.
- Remaining: prior-zone retirement, DbServer wait cost, ARM64 servers, persistent
  folder cache, late data-stage launch, enhancement additions and cleanup proof.
  Esync requires a proposal before changing the pinned runtime.
- Reduced client features remain: no PhysX ragdolls, CgFX effects, runtime DXT.
  No releases/protected-branch changes. See armport/M5-HANDOFF.md and M5-THOR-TEST.md.
