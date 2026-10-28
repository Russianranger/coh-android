# COH-ArmPort status

Updated 2026-10-27. M0 survey: merged (PR #3). Route: build the original client as an ARM64
Windows program for the app's existing ARM64 Wine.

M1 libraries: merged (PR #4, approved by Sol). The original textparser built
for ARM64 reads bodyparts.bp and the shipped BodyParts.bin to 28 matching
entries under the app's Wine. Details: armport/M1-REPORT.md.

M2 client boots: merged (PR #5, approved by Sol; 43 patches, upstream/
untouched). Details: armport/M2-REPORT.md.
- CityOfHeroes.exe (ARM64 Windows) runs under the app's ARM64 Wine on Xvfb
  and Mesa and shows the login screen with the game's own UI; still running
  with no exceptions at 180 s (CI run 39742143066, screen in
  armport/evidence/m2-login-screen.jpg).
- Data bins built in CI by the OptDebug client; Cg compiled to ARB by cgc.exe.
- 64-bit bugs fixed one by one as they stopped the client
  (armport/notes/64BIT-AUDIT.md). Wine places a 64-bit program's memory above
  4 GB (measured), so truncated pointers have to be fixed, not tolerated.
- Reduced function: no ragdolls (PhysX), CgFX effects (SSAO, filters), runtime
  DXT compression, SSE reported absent.

CI data: the reviewed client asset bundle (release asset 588984151).
M3 into Atlas: accepted (Sol 5659701771), merged; 106 patches (armport/HANDOFF.md):
- CI job server-run: the repository's qualified ARM64 game stack (original
  DbServer and Atlas MapServer under the app's Wine 10/FEX, PostgreSQL, PRoot,
  loopback-only network) plus the ARM64 client, login typed on Xvfb.
- Run 39960894368: the ARM64 client logged in through its own UI, chose the
  TestClient-created character and is connected on Atlas Park in the
  database (loaded, map 1), still connected after the screenshots.
- Fixes: SOCKET width (0044), version-check opt-in (0045), empty world groups (0047).
- Reviewed-head replay 40321211800 passes partial scope; full state/M3 remain false.
- Final head d7c072246: Atlas 40407492746 and replay 40407492734 pass. World
  rendered (plaza/statue/dome), 0 after-load errors, still connected; ARM64 =
  i686 partial state, equal error inventories. Reduced scope: completeness
  flags false; textures incomplete (purple/flat surfaces), Android/Thor pending.
- M4 app runtime: accepted (Sol 5660940046), merged (PR #7; armport/M4-REPORT.md).
- M5 Thor (PR #8): 0.13.44 (APK 40743596575, Astra 5687848443) plays on Thor: combat, defeats,
  zoning, save work; 12-30 FPS. Open: second-zone NPC stutter (servers), ~12 min start.
  Handoff and next steps: armport/M5-HANDOFF.md. Scheduled checks cancelled 2026-10-28.
