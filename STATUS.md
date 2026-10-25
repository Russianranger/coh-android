# COH-ArmPort status

Updated 2026-10-25. M0 survey: merged (PR #3). Route: build the original client as an ARM64
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
M3 into Atlas (79 patches including partial replay observers; Astra leads,
see armport/HANDOFF.md):
- CI job server-run: the repository's qualified ARM64 game stack (original
  DbServer and Atlas MapServer under the app's Wine 10/FEX, PostgreSQL, PRoot,
  loopback-only network) plus the ARM64 client, login typed on Xvfb.
- Run 39960894368: the ARM64 client logged in through its own UI, chose the
  TestClient-created character and is connected on Atlas Park in the
  database (loaded, map 1), still connected after the screenshots.
- Fixes on the way: SOCKET width (0044), version-check opt-in for the
  fake-auth server (0045), empty world-group slots (0047), login-stage log
  (0046, diagnostics only).
- Run 39973792458 failed: zone stayed loading, then Atlas disconnected.
- Sol 5643610947: retry resolved, audio tables accepted; no milestone approval.
- 0077 observes world traversal; duplicate host cleanup fixed, fresh runtime pending.
- Approved Steel Canyon texture staged/verified; Atlas 40197277872 rendering fails.
- Replay 40203125375: six normal exits; exact approved texture opt-in needs fresh CI.
- M4 40176336731 passes guest create/reopen and continuity; review/surface pending.
