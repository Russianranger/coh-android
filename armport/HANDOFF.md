# COH-ArmPort handoff (to Astra)

Updated 2026-10-23. From now on Astra leads development and Claude reviews
(roles reversed for now; see "Roles" below). Read this file, `PORT-PLAN.md`
and `STATUS.md` first. Everything here can be checked against the repository
and the CI runs it cites.

## 1. What the project is

Run the original City of Heroes client source natively on ARM64 Android, on
one AYN Thor, for personal use only. The client (`Game`, `Common`,
`UtilitiesLib` from `upstream/ouroboros`) is built as an **ARM64 Windows
program** with llvm-mingw and runs in the Android app's own ARM64 Wine 10
runtime (`android/runtime-lock.json`). ARM64 code needs no emulation there.
The local game servers stay as they are (32-bit x86 builds under the same
Wine via FEX).

## 2. Rules (from PORT-PLAN.md; they still apply)

- `upstream/` is never edited. All source changes are patches in
  `armport/patches/` (one purpose each), applied by `armport/scripts/prepare.py`.
- Original game logic is not rewritten; if behaviour must change, the patch
  says why. Opt-ins are environment variables set only by our harness
  (`ARMPORT_LOOSE_DATA`, `ARMPORT_NO_VERSION_CHECK`, `ARMPORT_STDIO_LOG`).
- Every claim in a PR points to a CI run or command output.
- `STATUS.md` stays at most 40 lines.
- Two compiler processes (`CMAKE_BUILD_PARALLEL_LEVEL=2`).
- **Stop and ask the user before:** changing `main` or `native-android`,
  rewriting pushed history, using secrets or signing keys, publishing
  releases, spending money, or any legal question.

## 3. Branches and review

- `COH-ArmPort`: integration branch. M0 (PR #3), M1 (PR #4), M2 (PR #5) are
  merged with merge commits.
- `armport/m3-atlas`: current M3 work (HEAD at handoff: see `git log`; last
  code commit 748504dc). Not yet a PR.
- Each milestone: PR from `armport/<milestone>` into `COH-ArmPort`; reviewer
  approves; author addresses findings; merge with a merge commit
  (`gh api -X PUT repos/Russianranger/coh-android/pulls/<n>/merge -f merge_method=merge`).
- If the base moved since the branch point, merge `COH-ArmPort` into the
  branch (never rebase pushed branches) and confirm the tree is unchanged.

## 4. Milestones and state

| | Exit test | State |
|---|---|---|
| M0 | survey, route | merged |
| M1 | libraries build; textparser unit runs under the app's Wine | merged |
| M2 | client links and reaches the login screen under that Wine (Xvfb, Mesa) | merged; boot test still runs in every CI run (`client-run`) |
| M3 | scripted login against the CI server to Atlas Park; saved native-android packets replay through the original receive code; screenshot check | **login reached Atlas; loading stalls in texLoadQueueFinish; replay inputs recovered** |
| M4 | the Android app runs the ARM64 client in its existing runtime instead of the x86 one; verified on the ARM64 runner with the same runtime files | not started |
| M5 | user installs once and play-tests about 10 minutes on the Thor | not started |

### M3 evidence so far

- CI run **39960894368** (attempt 2), job `server-run`, commit c04eb2f1:
  guest report passed; the ARM64 client logged in through its own login
  screen (typed by xdotool), chose the TestClient-created character, joined
  the Atlas MapServer, and the database shows it `loaded`, `connected`,
  map 1, and still connected after the screenshots. The capture shows the
  same DbServer exchange as the TestClient's (login 244 bytes, character
  list, choice) and about 25 KB of map data on UDP 7001.
- Its screenshots show the **zone loading screen** (white with a progress
  bar), because the client was still loading 20-50 s after the database
  confirmation. Commit 748504dc makes the host wait up to 25 minutes for the
  window to leave the loading screen and requires a rendered frame for the
  verdict.
- **Run 39973792458 (commit 748504dc) failed: the zone never loaded.** Login
  and character select worked again; the DB showed the character connected
  on Atlas at 15:59:48. The host then captured about 50 `zone-loading`
  frames over the 25-minute wait. The final `ArmPort M3 screen` is still the
  white loading screen with the progress bar near empty. After the wait the
  DB showed `loaded false, connected false` (`still_connected` false), and
  the guest failed with "ARM64 client did not stay connected on Atlas". The
  client process had not exited (no `armport-client-exited`). So the load
  stalls near the start and the server drops the link. Saved annotations:
  `ci_results.py --run 39973792458 --job server-run --grep "login driver"
  "client exceptions" "UDP sequences" "stdio"` (the stdio has 16,347
  filtered lines). Next, find what the client is doing in the stall: a
  missing data file, a wait on a packet it never parses (the 64-bit receive
  path, see 0044), or a busy loop. Also find when the server dropped it
  (MapServer stdout tail).

- Run **40011219458** (ff50ae2db) narrows the stall to
  `texLoadQueueFinish()`: `textures.wait` is the final zone marker, and 49
  log-growth samples are identical. Patch 0049 adds internal texture-queue
  markers. See `notes/M3-LOAD-STALL.md`; no loading fix or M3 pass yet.

## 5. M3: remaining steps

1. **Screenshot check.** Blocked on the zone-load stall above; fix that
   first. Once a run has `world_rendered` true,
   look at the `ArmPort M3 screen` image (Atlas Park should be visible) and
   copy it to `armport/evidence/m3-atlas.jpg`. If the zone never finishes
   loading, the client log and `loading_brightness` list say how far it got;
   likely causes are missing CI data (see section 8) or a 64-bit bug in the
   zone loader (look for crashes in `client exceptions`).
2. **Packet replay.** Both inputs were recovered and hash-verified on
   2026-10-23; see `notes/M3-LOAD-STALL.md`. Use `initial-replay.bin` (37,994 bytes, sha256
   cc949b01...7b39) and `post-ready-replay.bin` (74,416 bytes, sha256
   f134c3c0...96a9) from the user's Thor report of 2026-10-21 (client
   session 1a15fad27e9; hashes in
   `native-android/combined-client/DIAGNOSTIC-STATUS.json`). They are not in
   the repo; the original report archive now supplies both. Format notes are in that JSON
   (`coh-post-ready-logical-messages-v1`; logical payloads, not UDP wire
   packets). Method agreed by Claude in PR #6 review 5635319013 (2026-10-23);
   details and required i686 comparison are in `notes/M3-REPLAY-PLAN.md`: feed the logical
   messages to the client's original receive functions (entity/initial
   receive in `Game/src/clientcomm/`) from a small ARM64 test driver, or
   replay them from a stand-in MapServer. Compare with the 32-bit decode the
   native-android work recorded.
3. **M3 report and PR.** Write `armport/M3-REPORT.md` in the style of
   `armport/M2-REPORT.md` (exit test, evidence, what it took, gaps), update
   `STATUS.md`, open the PR `armport/m3-atlas` → `COH-ArmPort`, and ask for
   review (prompt for the reviewer: the user relays it).

## 6. M4 and M5 outline

- M4: find where the app starts the x86 client in its runtime (the
  `android-*` workflows and `android/guest/` scripts; the app's Wine runs in
  PRoot on the device). Add the ARM64 client next to it as an option, with
  the same data and runtime files, and verify on `ubuntu-24.04-arm` with the
  same runtime files the device uses. Note from M3: inside the PRoot guest
  the ARM64 client died with an Xlib BadWindow error before drawing (run
  39795786028); on the host it works. M4 has to solve the device display
  path (the app presents through its own X server; check how the x86 client
  is shown on the device first).
- Building or signing an APK uses signing keys: ask the user first.
- M5: the user installs once and play-tests; prepare a short test list.

## 7. CI: how it works and how to read it

Workflow `.github/workflows/armport-build.yml` (triggers on pushes to
`armport/**` that touch `armport/` or the workflow; `[skip ci]` in the commit
message for docs-only commits):

| Job | What it does | Time |
|---|---|---|
| `libraries` | M1 unit, nvDXT decoder test (ASan/UBSan) | 3 min |
| `assets` | caches the reviewed asset ZIP (release asset 588984151) | 1 min |
| `client` | Release and OptDebug builds (cached by build inputs) | 1-40 min |
| `client-run1` | OptDebug `-createbins` builds the data bins; records Cg requests | 8 min |
| `cg-precompile` | original `cgc.exe` on Windows compiles Cg programs to ARB | 1 min |
| `client-run` | M2 boot test (`--require-alive`) plus a login probe (no server) | 6-11 min |
| `server-run` | M3: server stack plus ARM64 client login to Atlas | 60-120 min |

**Reading results.** The current GitHub connector can fetch full job logs
and download artifacts. Verify downloads against their API SHA-256 digests.
The annotation reader remains a useful fallback without connector access.
Use `python3 armport/scripts/ci_results.py --sha <commit> --job <job>`
(waits, saves annotations, rebuilds exported images, prints sections;
`--grep` to filter). Failing commands in `server-run` are wrapped in
`armport/scripts/step.sh`, which puts the last 3,500 characters of output
into an error annotation. GitHub keeps only about ten notices per step;
images go through `armport/scripts/screen_export.py` (at most 10 parts, one
image per step).

**Fast loop.** `client-run`'s login probe (`smoke_run.py --login-probe`)
drives the real login screen in 6-11 minutes without servers; use it for UI
automation changes before spending a 1-2 hour `server-run`. Cancel a stale
run with `gh api -X POST repos/Russianranger/coh-android/actions/runs/<id>/cancel`.

**Donor binaries.** `server-run` uses server executables from
`android-game.yml` run 38478387527 and inputs from runs 36460867428,
36088012664, 36297542986 and 36364550345. Two of those artifacts expire
2026-10-25/27; a copy is kept in the Actions cache (`armport-server-donors-v1`,
branch-scoped) and as artifact `armport-server-donors` of run 39782080360
(expires 2027-01-20). If both are gone, the donors must be rebuilt by
re-running android-game.yml's build jobs (ask the user: it is their workflow).

## 8. Things learned the hard way (each cost a CI cycle)

- **Wine puts a 64-bit program's memory above 4 GB**, so every truncated
  pointer crashes; fix them (`armport/notes/64BIT-AUDIT.md` lists all, with
  symptoms). A fault at a small address (0x5d, 0x60) is usually a field read
  through a NULL pointer, not truncation.
- **Production clients** read `scenes/`, `ent_types/`, `object_library/`,
  `geobin/` only from piggs (patch 0042), only take level-0 command-line
  options (`-quicklogin`, `-noversioncheck`, `-verbose` are ignored), and only
  read bins (bins are built in CI by the OptDebug client).
- **Fake-auth DbServer** rejects the Release client with WrongVersion unless
  the client sends the no-version-check flag (patch 0045,
  `ARMPORT_NO_VERSION_CHECK=1`).
- **Login UI**: the game samples keyboard and mouse once per frame
  (DirectInput). Hold keys ~60 ms (`login_ui.Screen.press`). Log In is
  disabled while either field is empty; use Tab and Return, not clicks, on
  the login form. After Return comes Select a Server (click the first row,
  layout (824, 281)), then character select (Next arrow at (969, 741)); both
  positions come from `uiLogin.c` / `uiHybridMenu.c` constants in the
  1024x768 design space. OCR is unreliable on the game's fonts; the layout
  fallbacks in `login_ui.LAYOUT` are what works. Use lowercase account names.
- **Screenshots** of the 60 fps window can catch half-presented frames;
  `Screen.shot` keeps the largest of four captures. Frame rate is 45-63 fps
  (Wine `+fps`), so slowness is not the issue.
- **Patch 0046** makes the client log its login stage and dialog texts to its
  stdio log (`ArmPort login: stage N ...`, stages from `uiLogin.h`); the M3
  report prints the changes. Use it instead of guessing from screenshots.
- **Server stack (guest)** runs in a private loopback-only network namespace;
  the client joins it with `sudo nsenter --net=/proc/<pid>/ns/net`. The
  guest's cleanup audits same-user processes: never leave a `sudo` process
  running (it has your real UID and a root-only environment), and stop the
  client and its wineserver (`wineserver -k` then `-w`) before the guest
  cleans up (marker handshake in `armport_game_host.py`).
- **Atlas readiness** sometimes misses a heartbeat during the original
  30-second observation; the guest repeats the observation once and records
  `atlas_observation_retry`.
- **Guest budgets**: the guest allows 80 (raised to 120) DbServer status
  queries per run; poll sparingly. Owned processes fail the run past 2 MB of
  output (keep `WINEDEBUG` quiet inside the guest).
- **CI data gaps**: many `object_library` geometry files are missing, so some
  world-group members do not load (the 32-bit MapServer logs the same "can't
  find member"); patch 0047 makes the client skip empty slots. Expect more of
  this kind in the zone loader.

## 9. Patch workflow

```sh
python3 armport/scripts/patchwork.py init /path/outside/checkouts/pw   # base + one commit per patch
cd /path/outside/checkouts/pw/src
# new patch: edit, then: git commit -am "0048-<area>-<purpose>.patch"
# change an existing patch: git commit -am "fixup! 00NN-<name>.patch"
GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash base
python3 <repo>/armport/scripts/patchwork.py export /path/outside/checkouts/pw
```

Check a changed file compiles for ARM64 (and i686 for the 32-bit branch of
`#if defined(_WIN64)` code) before pushing; CI builds in a few minutes when
the build cache misses only the changed files. Keep CRLF/Latin-1 source files
byte-preserved when editing with scripts.

## 10. Roles (temporary)

Astra leads and pushes to `armport/*` branches; Claude reviews each PR (PR
comment or `reviews/PR-<n>.md` on `armport-reviews`) and checks claims
against the cited CI runs. The user relays prompts between the two and
receives the daily summary and milestone alerts from the lead.
