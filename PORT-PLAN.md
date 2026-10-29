# COH-ArmPort plan

Goal: run the original City of Heroes client source natively on ARM64 Android
(AYN Thor, personal use only). Compile the original `Game`, `Common` and
`UtilitiesLib` code as an ARM64 Windows program and run it in the app's
existing ARM64 Wine 10, which needs no x86 emulation for ARM64 code (decided in
M0, see `armport/M0-REPORT.md`). Changes are limited to 64-bit fixes, x86-only
code (SSE, inline assembly, PhysX, Cg) and build files. The local server stays
on its existing Wine/FEX runtime.

## Layout

- `upstream/` stays byte-identical to `upstream-lock.json`.
- `armport/` holds everything new: platform layer, build scripts, survey tools.
- `armport/patches/` holds source changes the port needs (for example 64-bit
  fixes). Each patch is small and named for one purpose; nothing edits
  `upstream/` in place.

## Roles and workflow

- One agent leads, one reviews. Follow the latest explicit user assignment.
  Read root `STATUS.md`, the current task note/handoff it identifies, and the
  relevant current PR reviews/comments. Earlier handoffs retain historical
  assignments and milestone statements; they are not current task instructions.
  Durable working rules are in `AGENTS.md`; Cloud setup is documented in
  `armport/CLOUD-DEVELOPMENT.md`.
- Each milestone is a pull request from `armport/<milestone>` into
  `COH-ArmPort`. The reviewer reviews it (PR comment, or `reviews/PR-<n>.md`
  on `armport-reviews`); the lead addresses the review, then merges.
- The user gets a daily summary and an alert when a milestone passes, a Thor
  test is needed, or work is blocked.

## Milestones

| | Milestone | Exit test (no user needed except M5) |
|---|---|---|
| M0 | Survey | Compile errors by category for all three trees; 64-bit risk list; Cg shader precompile result; graphics route chosen |
| M1 | Libraries | `UtilitiesLib` and dependencies build as ARM64 Windows libraries with llvm-mingw in CI; an original unit (textparser loading `defs/ui/bodyparts.bp` to 28 entries) runs under the app's ARM64 Wine on an `ubuntu-24.04-arm` runner |
| M2 | Client boots | `CityOfHeroes.exe` links for ARM64 Windows and reaches the login screen under that Wine with a virtual X server and software GL (no server connection; moved to M3 in the PR #5 review) |
| M3 | Into Atlas | Scripted login against the CI server to Atlas Park in CI; saved native-android packets replay through the original receive code; screenshot check |
| M4 | App integration | The Android app runs the ARM64 client in its existing runtime instead of the x86 one; verified on the ARM64 runner with the same runtime files |
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

