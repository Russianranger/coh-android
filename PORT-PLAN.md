# COH-ArmPort plan

Goal: run the original City of Heroes client source natively on ARM64 Android
(AYN Thor, personal use only). Compile the original `Game`, `Common` and
`UtilitiesLib` code and replace only the Windows layer: window, input, sockets,
threads, files, sound and the OpenGL/Cg setup. The local server stays on its
existing Wine/FEX runtime.

## Layout

- `upstream/` stays byte-identical to `upstream-lock.json`.
- `armport/` holds everything new: platform layer, build scripts, survey tools.
- `armport/patches/` holds source changes the port needs (for example 64-bit
  fixes). Each patch is small and named for one purpose; nothing edits
  `upstream/` in place.

## Roles and workflow

- Claude leads. Each milestone is a pull request from `armport/<milestone>`
  into `COH-ArmPort`.
- Sol reviews each pull request (PR comment, or `reviews/PR-<n>.md` on
  `armport-reviews`). Claude addresses the review, then merges.
- The user gets a daily summary and an alert when a milestone passes, a Thor
  test is needed, or work is blocked.

## Milestones

| | Milestone | Exit test (no user needed except M5) |
|---|---|---|
| M0 | Survey | Compile errors by category for all three trees; 64-bit risk list; Cg shader precompile result; graphics route chosen |
| M1 | Libraries | `UtilitiesLib` and `Common` build for aarch64; original textparser loads `defs/ui/bodyparts.bp` to 28 entries on ARM64 |
| M2 | Headless client | `Game` links for aarch64; boots with offscreen GL and reaches the login screen against the CI server |
| M3 | Into Atlas | Scripted login to Atlas Park in CI; saved native-android packets replay through original receive code; screenshot check |
| M4 | Android package | Runs inside the Combined app on the Android 13 emulator (x86_64 build) and builds for arm64 |
| M5 | Thor | User installs once and play-tests (about 10 minutes) |

Time boxes: M0 2 days, M1 1 week, M2 2 weeks, M3 2 weeks, M4 1 week.
Overrunning a box triggers a short note to the user with the reason.

## Test data reused from native-android

- Three saved initial packets (301,656 / 303,112 / 303,248 bits).
- The 0.1.19 post-READY replay: one snapshot and 115 UPDATEs (74,416 bytes).
- Known ACK/READY payloads (5 and 26 bytes) and the CI server workflows.

## Rules

- No new gate, lease or receipt systems. `STATUS.md` stays at most 40 lines.
- Every claim in a PR points to a CI run or command output.
- Original game logic is not rewritten. If behavior must change, the patch
  says why.
- Stop and ask the user before: changing `main` or `native-android`, rewriting
  history, using secrets or signing keys, publishing releases, spending money,
  or any legal question.
