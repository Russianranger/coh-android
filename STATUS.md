# COH-ArmPort status

Updated 2026-10-22.

M0 survey: merged (PR #3). Route: build the original client as an ARM64
Windows program for the app's existing ARM64 Wine.

M1 libraries: merged (PR #4, approved by Sol). The original textparser built
for ARM64 reads bodyparts.bp and the shipped BodyParts.bin to 28 matching
entries under the app's Wine. Details: armport/M1-REPORT.md.

M2 client (branch armport/m2-client, in progress; 37 patches, upstream/ untouched):
- CityOfHeroes.exe builds for ARM64 Windows (Release and OptDebug).
- Under the app's ARM64 Wine (Xvfb, Mesa) the Release client renders the
  Freedom loading screen with the game's textures (screen exported from CI
  run 39713451350); it stops at a missing bin (authmsg-en.bin).
- Cg: the client's vertex/fragment programs are compiled to ARB assembly by
  the original cgc.exe in CI and loaded by the ARM64 stand-in.
- Data bins: FINAL builds only read bins, so CI builds them with the OptDebug
  client (-createbins). It now gets through messages, sequencer state bits,
  tricks, textures and texWords; each stop so far was a 64-bit bug, fixed one
  by one (armport/notes/64BIT-AUDIT.md): DDS and .anim/.geo file layouts,
  truncated find handles, the hash table's deleted-slot marker, and pointers
  kept in the expression evaluator's int table.
- Wine does not keep a 64-bit program below 4 GB (measured in CI), so
  truncated pointers have to be fixed, not tolerated.
- Reduced function: no ragdolls (PhysX), CgFX effects (SSAO, filters), runtime
  DXT compression, SSE reported absent.

CI uses the reviewed client asset bundle the repo's other runtime workflows
use (release asset 588984151) for fonts, UI textures and models.

Next: complete the bins, then the login screen in CI.
