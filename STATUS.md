# COH-ArmPort status

Updated 2026-10-21.

M0 survey: merged (PR #3, approved by Sol). Route: build the original client
as an ARM64 Windows program for the app's existing ARM64 Wine.

M1 libraries: exit test passed, PR #4 in re-review. Under the app's own Wine on
an ARM64 runner, the original textparser built for ARM64 reads bodyparts.bp and
the shipped 32-bit-built BodyParts.bin (same checksum) to 28 matching entries,
and the precise floating-point check passes. Details: armport/M1-REPORT.md.

M2 client (branch armport/m2-client, in progress):
- CityOfHeroes.exe compiles (1116 steps) and links as an ARM64 PE32+ GUI
  program: CI run 39671416130. 27 patches; upstream/ untouched.
- Under the app's ARM64 Wine on Xvfb it starts and stays up; it stopped at
  "Couldn't Create Window" because the mingw CRT skipped WinMain (window class
  never registered, traced under Wine). Fixed by patch 0027; re-run pending.
- Cg: vertex/fragment programs now load as ARB assembly precompiled by the
  original cgc.exe (standins/cg/cg_arb.cpp); CI records the programs the
  client asks for, compiles them on Windows, and re-runs the client with them.
- Stand-ins with reduced function: no ragdolls (PhysX), CgFX effects (SSAO,
  post-processing filters), runtime DXT compression, SSE reported absent.

Next: login screen in CI. CI has the text data only (no textures or UI art),
so how far the login screen can render there is still to be measured.
