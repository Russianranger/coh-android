# COH-ArmPort status

Updated 2026-10-21.

Current milestone: M0 survey, in review (PR from `armport/m0-survey`).

M0 result: build the client as an ARM64 Windows program for the app's existing
ARM64 Wine. With flags, three one-line fixes and SSE shims, 502 of 558 Game
files and 158 of 165 UtilitiesLib files compile for ARM64. 29 of 30 shaders
precompile to ARB. 460 pointer-truncation warnings to fix. Details:
`armport/M0-REPORT.md`.

Next (M1): CMake + llvm-mingw ARM64 build of UtilitiesLib and dependencies,
first patches, and an original unit running under ARM64 Wine in CI.
