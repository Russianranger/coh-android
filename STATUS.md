# COH-ArmPort status

Updated 2026-10-21.

M0 survey: merged (PR #3, approved by Sol). Route: build the original client
as an ARM64 Windows program for the app's existing ARM64 Wine.

M1 libraries: exit test passed, PR in review. Under the app's own Wine on an
ARM64 runner, the original textparser built for ARM64 reads bodyparts.bp and
the shipped 32-bit-built BodyParts.bin (same checksum) to 28 entries, and the
precise floating-point check passes. 8 small patches; upstream/ untouched.
Details: armport/M1-REPORT.md.

Next (M2): compile and link CityOfHeroes.exe for ARM64 Windows, replace the
Cg runtime dependency, then boot to the login screen in CI.
