# COH-ArmPort status

Updated 2026-10-22.

M0 survey: merged (PR #3). Route: build the original client as an ARM64
Windows program for the app's existing ARM64 Wine.

M1 libraries: merged (PR #4, approved by Sol). The original textparser built
for ARM64 reads bodyparts.bp and the shipped BodyParts.bin to 28 matching
entries under the app's Wine. Details: armport/M1-REPORT.md.

M2 client (branch armport/m2-client, in progress; 29 patches, upstream/ untouched):
- CityOfHeroes.exe builds and links for ARM64 Windows in Release and OptDebug.
- Under the app's ARM64 Wine (Xvfb, Mesa) the Release client registers its
  window, loads data, and logs "Renderer initialization complete" (CI run
  39708928617, job client-run1).
- Cg: the client's 243 vertex/fragment programs are recorded, compiled to ARB
  assembly by the original cgc.exe (243/243), and loaded by the ARM64 stand-in.
- Data bins: Release (FINAL) builds only read prebuilt bins, so CI builds them
  with the OptDebug client (-createbins). It writes the message bins, then
  hits access violations; under investigation.
- Last stop: the client asked for fullscreen 1024x768, which the virtual screen
  lacks; now started windowed. Textures report "cant decode compressed
  texture" (likely the nvDXT stand-in); next to check.
- Reduced function: no ragdolls (PhysX), CgFX effects (SSAO, filters), runtime
  DXT compression, SSE reported absent.

CI uses the reviewed client asset bundle the repo's other runtime workflows
use (release asset 588984151) for fonts, UI textures and models.

Next: login screen in CI.
