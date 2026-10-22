# COH-ArmPort status

Updated 2026-10-22.

M0 survey: merged (PR #3). Route: build the original client as an ARM64
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
- Not yet run against the CI server: that starts M3's scripted login.
- Data bins are built in CI by the OptDebug client (-createbins); Cg programs
  are compiled to ARB by the original cgc.exe and loaded by the stand-in.
- 64-bit bugs fixed one by one as they stopped the client
  (armport/notes/64BIT-AUDIT.md). Wine places a 64-bit program's memory above
  4 GB (measured), so truncated pointers have to be fixed, not tolerated.
- Reduced function: no ragdolls (PhysX), CgFX effects (SSAO, filters), runtime
  DXT compression, SSE reported absent.

CI uses the reviewed client asset bundle the repo's other runtime workflows
use (release asset 588984151) for fonts, UI textures and models.

M3 into Atlas (branch armport/m3-atlas): started. First step: the client
logs in against the CI server.
