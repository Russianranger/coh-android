# COH-ArmPort handoff (to Astra)

Updated 2026-10-25. Astra leads development; Sol 6.1 reviews this PR per user direction
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
- `armport/m3-atlas`: current M3 work, draft PR #6. See `git log` and
  `M3-REPORT.md` for the current implementation-review checkpoint; not a
  milestone pass. Review 5638209554 corrections and the reviewed Atlas supplement are
  integrated at code 7fb7c692; runs 40094942235/40094942248 test them.
  40094448205 proves ARM64 handled-SEH rejection but fails on game data errors.
  Review 5638301654 follow-up is at 0b42f7cf on armport/replay-state, tested
  by 40097455262 (both targets fail on 183,269 complete errors):
  complete isolated errors, i686 stdio routing,
  same-commit data diagnostics and supplement identity/collision checks.
  Code 023fd0dd / run 40099922039 tests zero-initialized costume Appearance.
  Patch 0063 corrects collision-grid pointer truncation found in 40094942248;
  original/patched host controls fail/pass pointer identity as expected.
  M4 is on `armport/m4-runtime`.
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
| M3 | scripted login against the CI server to Atlas Park; saved native-android packets replay through the original receive code; screenshot check | **login/cursor replay pass; rendered Atlas and full state comparison outstanding** |
| M4 | the Android app runs the ARM64 client in its existing runtime instead of the x86 one; verified on the ARM64 runner with the same runtime files | startup path passes; complete interactive qualification pending |
| M5 | user installs once and play-tests about 10 minutes on the Thor | not started |

Sol supplemental review 5643697920 accepts implementation through 4c7ba7b
(world counters, render cleanup candidate, power observations and approved
texture staging), with no new finding. It explicitly grants no milestone or
merge approval; keep PR #6 draft. Later inventory/badge additions need review.

### Accepted partial replay checkpoint (2026-10-25 UTC)

Run [40206484644](https://github.com/Russianranger/coh-android/actions/runs/40206484644)
at 65a494c9 completed successfully: both target jobs, exact outside-error
comparison and partial-state comparison pass. Independent revalidation of both
SHA-256-verified artifacts reproduces all seven matching comparisons with the
one committed texture occurrence retained. Evidence and exact command:
`evidence/m3-accepted-partial-replay-40206484644.json`. Full schema, full state
comparison and M3 completion remain false. Historical 40203125375 stays failed.

Sol review [5644065631](https://github.com/Russianranger/coh-android/pull/6#pullrequestreview-5644065631)
finds no new implementation issue through b9f6cd8c, but grants no milestone or
merge approval. That head adds executable costume, story and contact/task
observers after the passing run. Fresh replay
[40210598573](https://github.com/Russianranger/coh-android/actions/runs/40210598573)
at e628a05c tests those additions; qualification remains pending. The trigger
changes only run_ci.py documentation and preserves Atlas 40204814232 at
b3125faa. Atlas is still running, not passed. Keep PR #6 draft and unmerged.

### Contact and task observation follow-up (2026-10-25 UTC)

Snapshots now retain ordered task sets/tasks, identities, difficulty, full
strings, individual flags, received U32 timer fields, ordinary destination
coordinates and received zowie fields. Known/accessible contacts retain strings,
identities, flags, points after the original clamp, and map/name/position.
Patch 0079 observes each alignment delay before the existing host-clock addition;
the original ten reads and U32 additions remain unchanged. The observer is inert
outside active replay, bounds its index and records only raw received delays.
Local clocks, format/icon caches, derived zowie coordinates/indices and resolved
contact destination objects remain excluded. No new ID normalization.

Patchwork exports 79 patches; upstream/ unchanged. Actual ARM64 then i686
state/contact units compile; actual-writer/receive-loop ASan/UBSan controls,
story regression and 151 Python tests pass. Evidence:
evidence/m3-contact-task-state-observations.json. Only local LeakSanitizer is
disabled due to /proc; CI defaults remain. Runtime pending; preserve replay
40206484644 at 65a494c9 (ARM64 cursor/partial stage passes, i686 pending).
Full entity/player/UI coverage and M3 remain incomplete.

### Story observation follow-up (2026-10-25 UTC)

Snapshots now retain all story/key clue strings, server souvenir IDs/header/
detail strings and visit-location names in their original array order, including
null entries. Patch 0078 supplies a read-only view of the original server clue
array; it is build-guarded and only called by active replay snapshots. Local
player-created clue files and UI caches are excluded. No receive code changes.
The patch was exported with patchwork.py; upstream/ remains unchanged.
Both native targets compile state.c and uiClue.c sequentially; source-derived
ASan/UBSan controls and 151 Python tests pass. Evidence:
evidence/m3-story-state-observations.json. Runtime pending; active replay
40206484644 predates this addition. Contacts/tasks/waypoints and broader player
state remain uncovered; partial schema and false completion flags remain.

### Retained costume observation follow-up (2026-10-25 UTC)

Snapshots now observe convertedScale, selected SG color set and all six SG
color-selection arrays as individual low/high U32 fields. All ten retained
player costume slots (including nulls), super/deferred costume bodies and
selection/mode fields are included. Logical part count is bounded by storage;
no source pointers, union padding or local deferred-change clocks are hashed.
Native ARM64 then i686 compilation, actual-writer ASan/UBSan controls, formatter
controls and 151 Python tests pass. Only local LeakSanitizer is disabled due to
/proc; CI defaults remain. Evidence: evidence/m3-costume-state-observations.json.
Runtime pending; preserve replay 40206484644 and Atlas 40204814232 at their
prior heads. NPC/power customization, reward ownership and broader tail/UI
state remain uncovered. Schema remains partial; no M3 or merge approval.

### Exact original-data exception enabled for fresh replay (2026-10-25 UTC)

Replay [40203125375](https://github.com/Russianranger/coh-android/actions/runs/40203125375)
(source 41c09e32) completes all six processes with expected exit 2 and no host
timeout/SIGKILL. All 702 snapshot hashes authenticate, all seven partial-state
comparisons match, and all six outside inventories match (117,777 errors each).
The CI jobs still fail under their strict no-dispatch-error policy. This does
not retroactively turn that run into an accepted replay or complete M3.

User decision [6387467359](https://github.com/Russianranger/coh-android/pull/6#issuecomment-6387467359)
authorizes an exact original-data exception after complete archive evidence and
literal six-run agreement. Sol [5643610947](https://github.com/Russianranger/coh-android/pull/6#pullrequestreview-5643610947)
accepted the frozen 57 non-audio plus 15 audio table coverage; their disjoint
union equals all 72 catalog archives. The six names remain absent; audio tables
contain no textures or geometry. The fresh replay workflow now explicitly opts
into only this committed occurrence, present identically in all six traces:

| Literal original-data error | Count per run | Dispatch index | After-dispatch index |
|---|---:|---:|---|
| `CUSTOM TEXTURE ERROR: FEM wants nonexistent texture HIPS_miniskirt_1 as texture 2 on bone HIPS.` | 1 | 1 | null |

The policy pins the archive proof and six-run evidence. Default CLI behavior
still rejects dispatch errors. An absent, added, moved or changed occurrence
fails even if it names another of the six approved textures. Mission-room and
all other errors remain fatal to replay qualification. Every accepted occurrence
is retained in each replay notice and the partial-comparison report. Wine,
trace integrity, cursor, ACK, snapshot and exact outside-inventory checks remain;
comparison also independently rejects abnormal process exits and host timeouts.

Evidence: `evidence/m3-six-run-texture-exception-40203125375.json` (verified
artifact digests and per-run literal texts, indices, process and trace hashes),
`replay/fixtures/original-data-errors.json`, and
`evidence/m3-original-data-exception-controls.json`. Local suite: 151 tests pass.
Fresh CI must qualify the opt-in and inventory/badge/team/world observers added
after 41c09e32. The schema remains partial and full-state/M3 flags remain false.
Atlas 40204814232 at b3125faa is preserved independently, with world counters,
approved texture and shared host teardown. No milestone or merge approval.

### Dynamic group and sky observation follow-up (2026-10-25 UTC)

Partial snapshots now retain ordered dynamic-group hp/repair fields and the
server sky indices/raw weight bits from original receive storage. They do
not hash bitfield layout, tracker pointers or render overrides. Both target
units compile sequentially; actual-writer sanitizer controls and 145 Python
tests pass. Evidence: evidence/m3-world-state-observations.json. Runtime
pending, schema still partial, no change to packet bytes or acceptance.

### Team and league observation follow-up (2026-10-25 UTC)

Partial snapshots now include team/league IDs and nullable active rosters,
team levels/mentor/active player, league leaders/locks, retained map names,
and player taskforce/LFG flags. Original member order and IDs remain literal;
counts, backing pointers and fixed-string termination are checked. Inactive
member tails, derived UI rosters and other receive destinations remain gaps.
ARM64 then i686 compilation, source-derived sanitizer controls and 145 Python
tests pass. Evidence: evidence/m3-group-state-observations.json. Runtime is
pending; this skip-ci follow-up preserves Atlas 40204814232 and replay
40203125375 at their earlier heads. Full-state/M3 completion remains false.

### Shared host cleanup after 40197277872 (2026-10-25 UTC)

Atlas 40197277872 (554afc86) still fails: connection/still-connected and
coordinated guest cleanup pass, but rendered terrain is absent after 1,542
seconds. Final host cleanup repeats the already successful stop and records
wineserver stop exit 1. The host now shares one process-scoped teardown result
between its coordinating thread and final fallback, including every original
failure. A lock prevents concurrent duplicate teardown; returned lists cannot
clear stored errors. No marker/ownership audit or rendering rule changes.
145 Python tests pass, including duplicate-stop and concurrent failure controls.
Evidence: evidence/m3-shared-cleanup-40197277872.json. Fresh Atlas qualification
must include this change, world diagnostic 0077 and the approved texture.

### Badge observation follow-up (2026-10-25 UTC)

Partial snapshots now retain all player badge status words, recent badge
indices and received award timestamps, monitor entries, and client filename
state. Localized UI text/buttons remain excluded. Actual ARM64 then i686
compilation, source-derived ASan/UBSan controls, formatter controls and 142
Python tests pass. Only local LeakSanitizer is disabled due to /proc; CI uses
default settings. No new ID normalization, decoder mutation or full-state
claim. Evidence: evidence/m3-badge-state-observations.json. The current replay
40203125375 at 41c09e32 predates both generic-inventory and badge additions;
these additions need fresh runtime qualification.

### Generic inventory observation follow-up (2026-10-25 UTC)

Partial replay snapshots now also include all five generic inventory arrays:
salvage, stored salvage, recipes, base details and concepts, plus decoded
capacity fields. Array order, null entries, empty definitions, unsigned
amounts and concept F32 bits are preserved. No decoder/state mutation or new
ID normalization. Actual ARM64 then i686 compilation and source-derived
ASan/UBSan controls pass, as do 142 Python tests and formatter controls.
Local LeakSanitizer alone is disabled due to /proc; CI uses default settings.
Evidence: evidence/m3-generic-inventory-observations.json. Full state still
needs other receive destinations and accepted six-run comparison. Runtime
pending: running replay 40203125375 tests preceding 41c09e32, including the
cleanup/power additions/approved texture, but not these generic inventories.
The running Atlas 40197277872 remains preserved at older 554afc86.

### Approved Atlas swap source staged; power observations expanded (2026-10-25 UTC)

The user approved the exact Steel Canyon texture proposal in this development
conversation. The original range returns HTTP 206, 5,859 stored bytes and
22,322 decoded bytes; MD5 and cached header match. Decoded SHA-256 is
b4a62083f96562f15b241534a93846dbaea09696b0fd5977b982628f03108b5c.
The approved layer now has 9 files for 15 requests; the previous eight files
and their provenance are identical. Six unresolved exact names stay absent.
Existing workflow cache keys follow the manifest hash and reverify all bytes
before strict staging. No source archive was downloaded in full. Five range
controls pass; evidence/m3-approved-atlas-swap-staging.json records commands
and the real transfer. This targets swap warnings; terrain remains unproved.

Power/build/inspiration/boost inventory observations now extend the partial
state dump. Actual ARM64 then i686 units compile; the source-derived host
ASan/UBSan serializer control passes bit-pattern/null-slot/order/bound checks.
142 Python tests pass. Local LeakSanitizer alone is disabled due to /proc;
CI uses default sanitizer settings. No new ID normalization or full-state
claim; other receive destinations remain uncovered. See
evidence/m3-power-state-observations.json and replay/README.md.

Completed replay 40200224489 still fails: five processes exit 2, ARM64 id31
exits -9; every run has one dispatch error. All 702 authenticated snapshots
and seven partial comparisons match diagnostically, as do the six literal
117,777-entry outside inventories. Evidence:
evidence/m3-rejected-snapshots-40200224489.json. This run predates render
cleanup, power additions and the new texture. All exceptions remain OFF.
Preserve active Atlas 40197277872; qualify the current changes next.

### Replay render cleanup candidate (2026-10-25 UTC)

Replay 40200224489 ARM64 id1 repeats exit 2 but id31 exits SIGKILL after
its terminal/exit witnesses. Forty passive samples retain 11 sleeping tasks,
including llvmpipe workers, at futex_do_wait. This is not a userspace stack
or signal-sender identification. The candidate now queues the original
DRAWCMD_DESTROYDISPLAYCONTEXTS and flushes before ExitProcess, matching the
render-cleanup portion of windowExit after all 117 dispatches/snapshots.
Full windowExit is not called. Timeout, kill, Wine and data-error rejection
remain unchanged. ARM64 then i686 receiver compilation exits 0, one compiler;
142 Python tests pass. Runtime pending. See evidence/m3-replay-exit-waits-40200224489.json.

Sol review 5643610947 resolves the final retry finding and accepts the
complete frozen audio-table coverage, with no new implementation finding
through 2b860079. It does not review patch 0077 or this cleanup candidate,
and grants no milestone/merge approval or additional asset permission.

### Bounded world traversal diagnostic (2026-10-25 UTC)

Patch 0077, exported with patchwork.py, adds eight sampled main-viewport
world.draw records under the existing stdio opt-in. It counts roots,
definition visits, selected culling branches, model-load/alpha rejections
and world-sort requests. It does not change visibility decisions, geometry,
assets, inputs or rendering acceptance. Counts are not proof of GPU drawing.
This separates traversal/culling from missing/unloaded geometry and submission
in the next Atlas run; the terrain cause in 40189560565 remains unproved.
Both changed translation units compile for ARM64 then i686 at one compiler
process. The source-derived ASan/UBSan controller emits 0 records when off
and exactly 8 across 5,000 frames when on; shell/non-main/empty-world calls
are excluded. Local LeakSanitizer alone is disabled because /proc tasks are
hidden; the added libraries CI control uses the default sanitizer settings.
Evidence: evidence/m3-world-render-observation.json. Runtime pending; preserve
active Atlas 40197277872 and replay 40200224489, which test earlier heads.

### Replay exit observation and rejected snapshot diagnostic (2026-10-25 UTC)

All 702 snapshots retained by run 40170942751 authenticate against their
recorded SHA-256 values. The seven partial-state comparisons match: literal
same-ID repeats/cross-target pairs and the agreed five-field ID sensitivity.
All six literal startup/load inventories match (117,777 errors per run).
This remains diagnostic: i686 id31 exits SIGKILL (-9), and every run has the
same one dispatch data error. No exception or replay qualification is enabled.
`replay/diagnose_state.py` reproduces the inspection while retaining failed
exit codes and false completion flags; hash/Wine/integrity failures abort.
See evidence/m3-rejected-snapshots-40170942751.json for verified artifacts.

The replay host now polls its existing complete exit witness every 50 ms and
retains up to 40 passive Linux stat/wchan samples (64 tasks maximum per sample).
This investigates the sub-second Wine exit timer hypothesis without ptrace,
signals or changed exit acceptance. Missing task evidence is explicit. All
142 Python tests pass, including real normal/SIGKILL exits and tampered state.
Runtime qualification is pending; Atlas 40197277872 remains independent.

### Historical proposal: exact missing Atlas swap source (now approved above)

Metadata-only inspection of all 57 pinned non-audio tables finds the exact
missing tickertape_STEEL_CANYON_SOUTH.texture in stage3f.pigg: offset 72610035,
5,859 stored bytes, 22,322 decoded bytes, table MD5
c0d3e59b54b214d4a0ec1e7b4e60ff4d. The existing Talos texture is present in
run 40189560565; only the Steel Canyon source is missing. This name is outside
the user's 14-name and 8-composite-file grants. No payload fetched or staged.
External action: approve only this exact original range for verification and
staging; no other dependency expansion. The proposed fix targets the two
post-load swap warnings, not the unproved terrain cause. Reproducer:
`python3 armport/scripts/inspect_atlas_swap_sources.py --cache <cache-dir>
--output <report.json>`. Complete identity/range evidence is in
`evidence/m3-atlas-swap-source-40189560565.json`. New runtime 40197277872
qualifies existing retry/shutdown fixes at 554afc86, without this missing asset.

### Atlas connection sustained, rendering still failed (2026-10-25 UTC)

Run 40189560565 / server 121159624900 at 3539492e finishes failed. Libraries,
client runs and Cg pass. Guest passed with no failures: two Next attempts,
Atlas loaded/connected and still connected at final check, normal shutdown
before cleanup. World rendered remains false after 1,563 seconds: character,
HUD and helper modal are visible but terrain is absent. Two post-load errors
are the same tickertape_STEEL_CANYON_SOUTH -> tickertape_TALOS_ISLAND swap
warning. No Wine/integrity failures. Artifact 12600255615 verified SHA-256
008cca75eedecfdc0cbcf25a1e04e580ef40c519cbd413145a1c884e2d6173f7.
This does not test fae492c3's final retry parser or stop-result validation;
start fresh qualification now the prior run is complete. Record is
`evidence/m3-connected-not-rendered-40189560565.json`. M3 remains incomplete.

### Complete audio file-table audit (2026-10-25 UTC)

The remaining 15 pinned audio metadata prefixes now verify against original
length, SHA-256 and complete PIGG tables: 207,340 bytes, 2,177 file paths,
zero texture/geometry entries. Full decoded paths and identities are in
`evidence/m3-audio-file-tables.json`; `scripts/audit_audio_tables.py` reproduces
it with the existing frozen range reader and no payload downloads. A corrupt
cached prefix is rejected. Names are disjoint from the earlier 57-archive
scan and their union equals all 72 catalog entries. This fills the audio
table evidence gap; reviewer acceptance and literal six-run replay agreement
remain required. Texture exception OFF, M3 incomplete, no new asset staging.
Command: `python3 armport/scripts/audit_audio_tables.py --cache <cache-dir>
--output <report.json>` (default pinned assets/zones-audio-metadata.json).

### Sol final retry check (2026-10-25 UTC)

Review 5643123702 reproduces a torn stage-7 prefix between the strict retry
read and the weaker final parser. The final input check now uses the same
complete latest frame sample and rechecks Atlas-marker absence. Controls
inject torn/transitioned stage records, a modal and an Atlas marker after
geometry revalidation. Original 3539492e sends two clicks in the torn-stage
negative control; corrected code sends one. All 135 tests pass. The new
commit also includes the shutdown validation below; skip CI to preserve
40189560565 at 3539492e. Its libraries pass resolves the earlier checkout
finding, but server-run is still active. These newer fixes require a fresh
runtime run after that completes; no milestone or merge approval.

### Shutdown acknowledgement validation (2026-10-25 UTC)

Source review of stop_client found wineserver -w timeout was ignored before
writing stopped=true. The host now retains command/timeout failures, waits
for a killed client, and publishes the existing stop marker atomically with
stopped=false on failure. The guest validates the marker on normal and error
paths; original service cleanup and ownership audits always run. Final host
teardown errors also fail the verdict. Worst-case subprocess timeouts sum to
150 seconds inside the existing 180-second coordination wait. 132 Python
tests pass, including Wine timeout, failed stop, stuck KILL, and invalid
marker controls. This follow-up skips CI to preserve 40189560565 (3539492e);
it requires the next runtime qualification and review. No PID identity claim.

### Sol review and Next retry (2026-10-25 UTC)

Sol 5642681417 identified the missing diagnostic.py dependency in libraries
121132992838 / run 40181381808. Its exact path is now checked out; the
reduced-dependency checkout passed 124 tests. The same run's server job
121135007849 remained at selected-character stage 6 after Next; screenshots
15/16 still show Next, and the guest reports no Atlas connection. A bounded
Next retry now requires advancing complete selected-character frame samples,
clear dialog history and no Atlas marker. Three attempts maximum; subsequent
connection/render/error acceptance is unchanged. 126 tests pass, including
stale, torn, transitioned and modal retry rejection. New runtime qualification
is required; M3 remains incomplete. See evidence/m3-next-input-40181381808.json.

### Failure-path host cleanup coordination (2026-10-25 UTC)

40176407354 records output overflow followed by same-UID ownership inspection
failure. Source inspection shows health() can raise before the normal host-stop
handshake. ArmPortGame.cleanup now requests host stop before the original
cleanup audit on this path, using a bounded wait independent of failed health.
Timeout is retained as a failure and original cleanup still runs. No ownership
check is bypassed. 124 tests pass, including failure, timeout, no-launch and
already-stopped controls. This explains a possible overlap, not the identity
of the unreadable process; runtime confirmation remains required. The commit
skips CI to preserve active 40181381808; qualify in the next Atlas run.

### Owned frame execution and server capture (2026-10-25 UTC)

40176407354 qualifies the frame lookup: geometry and brightness are present,
but Atlas OCR fails and screenshot shows no terrain. The server again exceeds
the stock 2 MiB output budget after 446 seconds of client observation.
M3 alone now allows 8 MiB per owned child, retaining unfiltered output and
fatal overflow checks. 120 tests pass, including real reader cap controls.
Fresh CI must qualify the longer observation; terrain and Wine ownership
cleanup remain separate. See evidence/m3-capture-budget-40176407354.json.
M4 40176336731 passes full guest creation/reopen and host continuity;
PR #7 retains pending reviewer approval and unvalidated Android surface.

### Frame title follow-up (2026-10-25 UTC)

40161198295 changes the owned game window title to Atlas Park after Next;
Screen.window still searched City of Heroes, so all frame stats were null.
Frame-only lookup now requires one owned PID, exact game class, visible and
unique game-sized geometry. Six controls plus all 118 tests pass. No input,
map/OCR/connection acceptance or server output limit changes. Evidence:
evidence/m3-frame-title-40161198295.json. Runtime qualification pending;
40170942752 has finished with server-run failure; the next run qualifies
the owned-window lookup and adds the 63-case selection control to CI.
The server output-bound failure remains separate and unresolved.

### Reopen selection boundary (2026-10-25 UTC)

M4 40167305715 now reaches reopen after creation validation; reopen crashes
in smf_SwitchBreakingToNonBreakingSpace. Exact Release disassembly and guest
registers prove -1 became UINT_MAX. Patch 0076 keeps the index signed and
checks bounds before reads, including both backward selection scans.
Source-derived ASan/UBSan helper controls reject old/pass fixed behavior;
ARM64 then i686 changed-unit builds pass. See evidence/m4-reopen-smf-40167305715.json.
Live reopen remains unqualified; select the new Release after CI succeeds.

### Active continuation after Sol review 5641405794 (2026-10-25 UTC)

Sol found no new implementation issue in code 396c470 / head 703ad1e, but
qualification failed. See evidence/m3-m4-review16.json for hash-verified
artifacts, source analysis and local command outputs. Continue independent
work while PR review waits, per the user's active-development instruction.

- M4 40155140217 identifies menu 8/index -16. hybrid_start_menu calls the
  destination entry before serve_menus commits gNextMenu. Patch 0074 uses
  the existing resetPowerCustomizationPreview/gLoopNow path to defer queue
  construction to the destination frame. Source-derived sanitizer controls
  reproduce old -16 access and pass 36 fixed transition/selection cases.
- Atlas 40154965180 never sent Next despite later ready-stage stdio. WinMain
  passed CRT streams to file.h's FileWrapper setvbuf macro. 0075 bypasses
  that macro; host control sees the marker immediately only after the fix.
  Real Wine controls and Atlas execution still need qualification.
- Atlas 40156677877 failed on an expired original donor artifact. The exact
  47-file retained bundle in 39782080360 remains available; the workflow
  now restores it on cache miss and verifies its inventory even on hits.
- Replay 40156677880: i686 runs all three, rejects the single dispatch error;
  ARM64 id1-b is killed after the exit witness. Do not accept the killed run.
  Investigate exit ownership/runtime behavior without changing acceptance.

Both changed native units compile on ARM64 then i686, with at most two
compiler processes. All 112 Python tests pass. M3/M4 remain incomplete;
texture exception OFF; full-state/audio-table evidence still outstanding.

### Previous checkpoint (Sol review 5641229238, 2026-10-25 UTC)

Candidate code 396c47010 runs in build/Atlas 40156677877 and replay
40156677880 on armport/m3-review15. The M3 integration adds documentation only
and preserves the earlier running Atlas job; cite the tested code SHA explicitly.

The remaining OCR timing gap is corrected: recheck isolated history after
selection/wait/capture/OCR, immediately before final Play/Return. Rejection
sends no final input or marker. Character OCR and layout lookup also revalidate
before clicking. Actual-host negative/positive controls and all 111 tests pass;
see evidence/m3-sol-review-5641229238.json and the leading M3-REPORT section.
Replay collects all three runs per target only when dispatch data errors are
the sole rejection after complete Wine/integrity/receiver checks. It still
fails qualification; crashes/fatals/integrity failures stop immediately.
Qualify the candidate without cancelling Atlas 40154965180. M4 40155140217
passed guest boot; interactive qualification and the power producer remain
pending. Sol found no new M4 staging issue. Exceptions remain OFF, M3/M4 are
incomplete, and no milestone or merge approval has been granted.

### Previous checkpoint (Sol review 5641164200, 2026-10-25)

Both requested corrections are implemented: remove the host server-click
bypass of rejected dialog history and propagate grid-control failures through
tee. Actual host/shell negative and positive controls and 101 tests pass; see
evidence/m3-sol-review-5641164200.json and the leading M3-REPORT section.
Atlas 40148424741 now stops at the exact QA notice: xdotool's default OR search
returns the main game window as well as the dialog. Require --all for PID AND
title, preserving exact-notice/unique-window/focus limits. Rerun Atlas to prove
progress; the current frame is still loading. Replay 40148424802 exits 2 on both
targets with 117 snapshots but fails one HIPS_miniskirt_1 dispatch error; the
other two runs per target and state comparison remain unqualified. Eight-file
staging passed with zero case aliases. The texture exception remains OFF.
M4 still needs the new Release and corrected case staging; identify the power
producer using 0073. M3/M4 remain incomplete, without milestone/merge approval.

### Previous checkpoint (review 5639886811 follow-up, 2026-10-24)

0071 fixes triangle writes overlapping expanded native collision-grid cells.
The exact replay and Atlas binaries both fault in objSplitPlanes, on child
and tri_idxs pointers respectively. Source-derived ASan/UBSan controls and
both target compilations pass; runtime resolution is not yet established.
See evidence/m3-review12-grid-and-runtime-40128377861.json and the leading
M3-REPORT section. Qualify the new replay/Atlas runs, then rerun M4 with the
new Release and corrected case staging. 0073 logs the selected menu/index
at the actual M4 caller createPrimaryAnimationEvents; its producer is unproved.
The login shortcut now requires the complete isolated dialog trace. Failure
notices retain exit diagnostics; a final runtime-tree audit checks all layers.
User approval 6389265419 permits exactly the 8 proposed composite files;
both workflows now stage them as a final strict layer, rechecking original
archive identity/inventory and restored bytes. No other fetch is authorized.
The texture exception remains OFF. Audio archive file tables and six-run
identity are still needed; M3 and M4 are not approved or complete.

The following paragraphs are historical checkpoints.


Latest completed evidence: build/Atlas 40118399219 fails before map.start,
remaining at character-select stage 6 while repeated OCR consumes the login
budget. The driver now uses the selected-character trace and caches same-frame
OCR. Replay 40118399218 fails ARM64 on 16 dispatch errors; i686 is SIGKILL at
311 seconds, no host timeout and no recorded cgroup OOM increment. New cleanup
and ExitProcess-begin witnesses do not change required exit 2. M4 40118768539
still faults on the bad power key. Its caller value is __chkstk's return PC
inside the lookup; patch 0070 separates trace buffers to preserve incoming LR.
See evidence/m3-m4-diagnostics-40118399219.json for artifacts, exact disassembly,
83 tests and target compilation outputs. Next: qualify these changes in CI,
then rerun M4 with the resulting Release client; symbolize its new caller.
The existing texture exception remains OFF and the 8-file proposal unstaged.


Review 5639193819 follow-up source f0d78fd78 runs in build/Atlas 40118399219
and replay 40118399218. The 8-file / 658,461-byte dependency proposal is
committed but not staged. See the leading M3-REPORT section and
m3-dispatch-errors-40113107670.json. Both targets have 14 texture and two
mission-room errors in id1-a; id1-b/id31 have not run. The conditional texture
exception approved in comment 6387467359 remains OFF: the archive scan is
57 of 72 and composite names have unstaged dependencies in reviewed manifests.
No extra fetch/staging or acceptance relaxation. Patches 0068/0069 diagnose
M4 power inputs/caller and missing mission-room tray coordinates. Enable
ARMPORT_POWER_TRACE only in the M4 interactive diagnostic. M4 run 40118768539
uses aa9cdcaa9 and the new Release client. Atlas 40113107671 is now failed:
the real startup RPC is counted once; a later NULL-def read at 0x88 is rejected.
Its complete Wine fixture and evidence are committed; screenshot is black.


Review 5638956748 follow-up code 07c536d7 is being qualified by build/Atlas
40113107671 and replay 40113107670 on armport/m3-review8. The user approved the 14-name
PIGG fetch and the narrow Atlas startup RPC exception allowance; recorded in
PR #6 comment 6386664502. Do not request those approvals again.

Exact frozen-index discovery found seven geometry files and chest_stripe_1:
eight files / 2,523,936 bytes. Six texture names have no exact donor match and
remain unresolved; no substitutions or additional dependency fetches. See
M3-REPORT.md, evidence/m3-approved-range-assets.json and the reproducible
commands in evidence/review-5638956748-local.json. Both workflows stage them
as a separate strict layer after the prior 166 reviewed files.

The replay now drains map loaders before replay.map.end as well as after the
117 dispatches; both drains are required. Replay's Wine check stays strict.
Atlas alone permits handled startup 6ba, proven by same-thread dispatch,
unwind and restoration before the first map-start witness in Wine's own
append log. Patch 0067 emits that boundary; CI checks concurrent append
ordering. Other exceptions/fatals still fail, and the count is reported.

Run 40111054487 (7a91b34d), ARM64 job 120923329915, writes its 117-dispatch
result and completes the final drain but returns -9, not the required 2.
Do not accept that transcript. New process/memory observations distinguish a
host timeout from a signal and retain failure inventories; cause not known.
M4 diagnostic 40110421624 fails with the same searchPowerCustomizations fault
at 0x14007457c. The register trace proves the bad search key: x8=0x10000000000,
loaded through x0 on the stack; candidate x9=0x1e236670 is not the faulting
operand. See evidence/m4-power-fault-40110421624.json. Its producer and game
caller are still unproved. No pointer guard, milestone pass or merge.

### Latest review decision (2026-10-24)

Review 5638651994 verified 0061-0063 as implementation only. User decision
6385679120 narrows errors to zero within all 117 indexed isolated dispatch
windows, with literally identical startup/load inventories and counts across
ARM64/i686. Global Wine exception, assertion/fatal and integrity rejection stays.
See M3-REPORT.md for the implementation and data-gap classes; no new data added.
Run 40100355275 reports identical 183,269-error inventories but fails the older
rule. Run 40100355259 still faults on NULL+0x88 in groupGridActivate despite
passing the grid pointer controls. Atlas remains unproved.
Patch 0064 repairs a separate VBO queue pointer-header overlap proven by the
M4 createVboDirect fault in 40098262167. Both local links and original/patched
controls pass; runtime execution with this patch remains required.

### Current checkpoint (2026-10-24)

- Run 40087788115 at 563e49ac passes all 117 original cursor/ACK dispatches
  on ARM64 and i686, each with ID1 twice and ID31 once. Full-state and M3
  completion flags remain false. The Wine-fatal/SEH rejection requested by
  Claude is integrated into that tested milestone head.
- Run 40054327137 still fails rendering/connection. Its artifact records the
  access-level QA notice and a modal on the loading screen. Run 40087788009 also fails with zero QA-notice actions; its image remains
  loading. Run 40094942248 stages the supplement but crashes in
  groupGridActivate before the QA notice; its final frame is black. Patch 0063
  fixes the grid storage/lookup pointer widths. No rendered Atlas is established.
- Partial state observer/comparison at 1e6952ed fails in the first snapshot
  formatter in 40091320504. Bounded CRT formatting replaces the inappropriate
  array-size macro; both links and preprocessing controls pass locally.
  Corrected execution run 40092531364 writes 117 ARM64 snapshots but fails
  the logical/allocated costume-part check; the review follow-up corrects it
  and rejects newly inventoried game data errors. See M3-REPORT.md.
  It is intentionally incomplete; coverage and local validation commands
  are in replay/README.md and M3-REPORT.md.
- M4 runtime probes 40040922125 and 40087554038 pass guest boot. The latter's
  interactive job fails on missing zone_asset_package. Commit ddaccd4 adds
  that required helper. Both interactive attempts in 40090844692 instead
  fail before launch on a dependency-download HTTP 503. Commit 58841f92
  recovers the exact pinned source from accepted artifacts and shares the
  successful boot PRoot with the interactive job. Run 40092467628 passes boot but interactive startup fails on missing
  client_visual_assets; 723bbc32 stages the server helper and distinguishes
  helper-only legacy inventories from optional visual payloads. Run 40094077884
  then exposes a missing cache ancestry helper. Commit 589a015b addresses it;
  40095316035 reaches client launch, then faults on a NULL texture. ddceae53
  changes the ARM64 staging to private regular copies (PRoot translates link
  calls) and fixes the evidence directory. 22 app tests pass; 40098262167 tests
  the correction. Full M4 remains unqualified.
- Latest Claude implementation review is 5638301654 at 045fe9aad. Request a new implementation
  review for the integrated P2, handshake prerequisites, QA-notice handling
  and state observers. Method agreement is not milestone approval.

### Earlier M3 evidence

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

1. **Screenshot check.** Finish investigating the current load/modal run. Once a run has `world_rendered` true,
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
   `native-android/combined-client/DIAGNOSTIC-STATUS.json`). They are available as exact gzip fixtures under armport/replay/fixtures/;
   the original report archive supplied both. Format notes are in that JSON
   (`coh-post-ready-logical-messages-v1`; logical payloads, not UDP wire
   packets). Method agreed by Claude in PR #6 review 5635319013 (2026-10-23);
   details and required i686 comparison are in `notes/M3-REPLAY-PLAN.md`: feed the logical
   messages to the client's original receive functions (entity/initial
   receive in `Game/src/clientcomm/`) from a small ARM64 test driver, or
   replay them from a stand-in MapServer. Compare with the 32-bit decode the
   native-android work recorded.
3. **M3 report and PR.** Keep `armport/M3-REPORT.md` and `STATUS.md` current.
   Draft PR #6 is already open from `armport/m3-atlas` → `COH-ArmPort`.
   Ask for review with the exact head and CI evidence (the user relays the
   prompt); retain incomplete status until all documented exits pass.

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

### Sampled world traversal diagnosis (2026-10-25 UTC)

Atlas [40204814232](https://github.com/Russianranger/coh-android/actions/runs/40204814232)
failed rendered-world qualification despite map-1 connection/still-connected.
Artifact 12605194825 verifies SHA-256
483cd92d87462105162c6ae8912df0dfaf75ba7452112b4b79f0e4ef16f95048.
All eight original 0077 samples have zero model calls and sort requests. The
steady samples have 4,870 visits: 4,534 editor-only, 307 distance and 13 frustum
rejections, leaving 16 visits beyond those three checks. This is not proof
that the flags, distances or definitions are wrong, nor evidence of GPU output.

`zone_report.py` now preserves a compact world-draw summary and all eight
parsed records in the evidence artifact. Missing, torn, inconsistent, duplicate
or excess samples produce unknown zero-call conclusions, not a pass. It does
not change rendering acceptance or original game code. The actual retained
artifact reproduces the summary; 154 Python tests pass. See
`evidence/m3-world-traversal-40204814232.json` for command, hashes and samples.
Next native investigation must distinguish the editor-only flag sources and
surviving definitions/camera distances; do not bypass visibility decisions.

New replay [40210598573](https://github.com/Russianranger/coh-android/actions/runs/40210598573)
at e628a05c now passes both targets and both comparison jobs, including the
new costume/story/contact/task observations. Partial comparison job 121229221929
still explicitly reports full-schema, full-comparison and M3 completion false.
No milestone or merge approval. Sol 5644065631 remains the latest review.

### Sol 5644275188 diagnostic integrity correction (2026-10-25 UTC)

An incomplete world.draw token was previously filtered out, and splitlines()
lost the newline needed to detect a partially written numeric field. The caller
now preserves line endings; candidate recognition includes an unfinished
world.draw token. Unterminated/malformed records invalidate aggregate conclusions.
Actual-caller controls cover both review reproductions and complete CRLF input.
156 Python tests pass; rerunning the verified Atlas 40204814232 artifact preserves
all eight previously committed samples and every summary field exactly.
Evidence: evidence/m3-world-report-review-5644275188.json. This is host-only;
no original renderer, acceptance or replay policy changes. Fresh CI not claimed.

Further source inspection narrows the next experiment: makeAGroupEnt sets
ONLY_EDITORVISIBLE for fog, sound, light, explicit editor-only/cubemap helpers,
or editor/hidden model tricks. Thus the large editor_skip count alone does not
prove a corrupt flag. closeEnough returns squared distance after its threshold
check, and the caller rejects zero; distance_skip can also mean exact zero
distance. The next native observation must record flag sources, camera-relative
midpoints/visibility distances and the remaining definitions without bypassing
those original decisions. Sources: original Game/src/graphics/groupdraw.c
makeAGroupEnt and groupdrawinline.c closeEnough/drawDefInternal (git show HEAD).

### Bounded definition-input observations (2026-10-25 UTC)

Patch 0080 adds at most four `world.def` observations for each of four reasons
in the existing eight sampled frames (128 records maximum). It identifies the
sample frame, sanitized definition name, model/children, editor-only sources,
camera/local midpoint, actual distance midpoint (including parent fade),
measured distance and valid calculated limit, cached visibility distance/radius
and LOD scale. Reason 3 means only that the first three checks were survived.
Original visibility decisions, arithmetic, shadow-map behavior and rendering
acceptance remain unchanged. This is an experiment, not a terrain fix.

Read full records from the retained isolated zone JSONL trace. Existing stdio
previews truncate details to 240 bytes and cannot supply the complete fields.
Only the first four definitions of each reason are observed, not all visits.

Commands and output: `evidence/m3-world-definition-controls.json`. Changed
`groupdraw.c`/`groupdrawinline.c` compile successfully for ARM64 then i686,
one compiler at a time. Actual-source ASan/UBSan controls preserve all 384
original distance results and calculation counts, bound names and record counts,
keep disabled/secondary paths inert and reset per-frame sampling. The previous
8-frame controller control and 156 Python tests pass. Host fixture types do not
prove native ABI; LeakSanitizer alone is disabled locally for /proc limitations.
CI runs these controls with its normal sanitizers. Runtime of 0080 is pending;
40204814232 remains failed, and replay 40210598573 qualifies the prior code's
partial observation scope only. No M3/M4/M5 completion or merge approval.

### Retained groups, customization and initial player fields (2026-10-25 UTC)

Snapshots now include the retained destinations of entReceiveOtherSupergroupInfo:
entity group name/emblem/colors, item-of-power spaces, mission, ordered/null reward
tokens, recipes and special details. Received server times and U32 sentinel
counts stay literal. Internal SpecialDetail.bValid bookkeeping is excluded.
Supergroup roster/rank/stat/UI coverage is not claimed by this addition.

Active/owned power-customization lists and all ten player slots preserve nulls,
original retained order, stored/resolved logical names, token bytes and individual
RGBA U32 values. Original packet reads/receivers and ID normalization do not
change. Counts remain bounded to 8,192 and the existing 16 MiB snapshot limit
applies. Broader entity/player/tail/UI coverage remains incomplete.

Initial player observations also retain type/subtype/progress, hidden/skills,
feature-version bits, original power-set names/comment and every account-game
and pop-help U32 word. Chat/window/tray/keybind/options receivers remain gaps.

Evidence: `evidence/m3-retained-group-customization-controls.json`. Twelve actual
writer/observer sanitizer controls and 156 Python tests pass; state.c compiles
ARM64 then i686 with one compiler. Fixture structures/earrays do not qualify
native ABI; mission forwarding uses the separately tested original task writer.
Only local LeakSanitizer is disabled for /proc; CI uses normal sanitizer settings.
Runtime remains pending. Atlas 40217209151 and replay 40217209257 test 5d1d2da9,
which predates these new serializers. All full-schema/full-state/M3 flags remain
false. Existing native renderer 0080 and the review's host truncation fix are
unchanged by this independent replay coverage work.

### Player identity, rewards and combat observations (2026-10-25 UTC)

Snapshots now retain literal title fields/colors/badge, workshop name, entity
description/motto, both ordered/null player reward-token name/value lists, PvP
flags, all ten combat-monitor key/order pairs and character class/origin logical
names, combat level/modifier, location type and ally/gang/PvP fields. Receivers
and synthetic-ID normalization are unchanged. Player token timers remain
excluded: INITIAL receives them, but later receiveRewardToken initializes them
from the local clock. This mixed provenance needs a separate observer. Title
expiry, UI localization/caches and other entity/control/UI destinations remain
uncovered; full-schema/full-comparison/M3 flags stay false.

Evidence: `evidence/m3-player-character-identity-controls.json`. Actual writers
pass ASan/UBSan controls for null/order/final slots, mutation sensitivity, U32
bits, string/count/output bounds, source immutability and clock/address
exclusion. Native state.c compiles ARM64 then i686 with one compiler; 156 Python
tests pass. Host fixtures do not prove native ABI; only local LeakSanitizer is
disabled for the known /proc limitation. Runtime qualification is pending:
40220658755 tests preceding 8813b215, not these additions.

Replay 40217209257 at 5d1d2da9 passes both targets and comparisons; job
121249121432 explicitly reports partial_state_equal true and full-state/M3 false.
The SHA-256-verified ARM64 artifact 12608430696 identifies 18 game-command types
in id1-a and authenticates its 117 state hashes. The committed command inventory
`evidence/m3-observed-game-commands-40217209257.json` guides remaining coverage;
command execution counts alone do not establish destination-state coverage.

### Retained visited-map and entity metadata observations (2026-10-25 UTC)

Patch 0081 exposes existing visited-map storage through a build-guarded const
accessor. The snapshot does not call automap_getMapStruct, whose normal behavior
loads files and creates owners. Original owner/map order, nulls, db/map IDs, fog
flags and all 256 U32 cell words are retained. Original local visited-map cache
data can also populate this storage; it is compared literally. Derived fog
grids, minimap bitmaps/textures and remaining UI state are not covered.

Entity observations add individual mode/vision bits, scalar taskforce/flashback/
NPC/gender fields, world-group/animation/pet strings, visibility/contact/pet flags
and special-power state. The received integer PvP delay is retained separately
from the excluded host update clock. Entity names must terminate within storage.
No new packet-ID field or synthetic-ID normalization is introduced.

Evidence: `evidence/m3-map-entity-metadata-controls.json`. Patchwork exports 81
patches with all prior 80 patch files byte-identical; upstream/ is unchanged.
Actual accessor/writer sanitizer controls, ARM64 then i686 native compilation
(one compiler) and 156 Python tests pass. Host fixture layouts are not native
ABI proof; only local LeakSanitizer is disabled for /proc. Fresh runtime is
pending: replay 40220658755 predates these additions. Full-schema, full-state
and M3 flags remain false.

### World-definition midpoint diagnostic correction (2026-10-25 UTC)

Sol review 5644680146 identified an incorrect midpoint predicate in 0080.
Patch 0082 makes all five distance-input observer sites use the same predicate
as original closeEnough: nonzero lod_fadenode and (PARENT_FADE or fade==2).
Original distance/culling calculations and returns are unchanged. The extended
control fails on 0080, then passes 768 original/patched decision and calculation-
count cases plus 1,920 logged midpoint/distance checks across all five sites.
It includes both reported mismatches and zero-distance bypass/ordinary cases.
The 5,000-frame off/on bound controls and sequential ARM64/i686 compilation
pass. Evidence: `evidence/m3-world-midpoint-review-5644680146.json`.

All prior 81 patch files are unchanged; patchwork exports 82. Atlas 40217209151
tests 5d1d2da9 before this correction: its distance_mid fields are unreliable
when the old and original predicates differ. Do not use those fields to claim
a root cause. Other observations need their own provenance and full records.
No rendering acceptance change, milestone completion or merge approval.

### Model-specific traversal evidence (2026-10-25 UTC)

Atlas 40217209151 at 5d1d2da9 completed with server-run failure: guest passes
and the client connects, but world_rendered remains false. Verified artifact
12610104475 (SHA-256 a9f8056323f7e54a14da71d77f5eff94d65862cc9f78034b2ba7c00c9cf2460b)
contains eight zero-model-submission samples and 128 full world.def records,
all for definitions without models. These bounded parent samples do not prove
that the loaded world has no models. Existing midpoint caveat from 0082 still
applies to this older run. `evidence/m3-world-definition-40217209151.json`
retains the samples and screenshot/report findings; root cause remains open.

Patch 0083 adds separate four-per-reason model-definition samples, preserving
the ordinary sample budget, and eight world.models summaries of model-bearing
visits and first-three-check outcomes. Model load state, flags, vertex and
triangle counts are diagnostic only. No culling/distance/render acceptance
changes. Actual source controls verify independent budgets, model metadata,
768 distance decisions, 1,920 midpoint/site checks, 32 traversal-prefix pairs
and 5,000-frame off/on behavior. ARM64 then i686 compile with one compiler.
Patchwork exports 83 patches; prior 82 are unchanged. Evidence:
`evidence/m3-world-model-controls.json`. Fresh runtime remains pending.

Replay 40220658755 at 8813b215 passes both architectures and partial-state/
outside-error comparisons (job 121259795237). This qualifies the retained
supergroup/customization/player-core additions; all full-state/M3 flags remain
false. Replay 40224584944 at 5919e8c tests later identity/map/metadata additions
and 0082; it does not include 0083. Do not claim milestone or merge approval.

### Retained karma and received desaturation observations (2026-10-25 UTC)

Partial snapshots now retain ordered karma widgets, literal unsigned identities,
logical types and all retained variable strings/nulls. Original receiver controls
cover creation, updates, retained tails after shorter updates and inactive clear.
General script-UI widgets/packet order/pending updates and tooltip caches remain
uncovered. No ID normalization is added.

Patch 0084 observes the four desaturation F32 values immediately after the
original four reads and assignments. The observer is inert outside replay.
Snapshots retain those individual bits, or null before the first receive,
instead of the live fields subsequently changed by game.c frame-time animation.
Original reads, stored bits and animation remain unchanged; this records received
representation, not complete current renderer state.

Evidence: `evidence/m3-karma-desaturation-controls.json`. Fourteen karma cases,
six original/patched desaturation off/on cases plus three replacements pass
ASan/UBSan controls. ARM64 then i686 state/receive units compile with one compiler;
156 Python tests pass. Fixture types are not native ABI proof; only local
LeakSanitizer is disabled for /proc. Patchwork exports 84 patches with the prior
83 byte-identical; upstream/ is unchanged. The visited-map CI control now uses
the same cache-miss condition as source preparation, as do the new controls.

Runtime is pending: replay 40224584944 tests earlier 5919e8c, not these additions
or model diagnostic 0083. Full-schema/full-state/M3 completion stays false.

### Server waypoint and turnstile receive storage (2026-10-25 UTC)

Snapshots now retain the original server-waypoint key/value mapping, sorting
a private entry array by literal string keys rather than allocation-dependent
stash bucket order. Values include received IDs/flags/names, individual F32
coordinate/angle bits and resolved icon names. No key or integer normalization,
stash mutation, asset loading or original receiver change. Selected compass
copies, display caches/coordinates and texture addresses remain excluded.

Patch 0085 exposes const views of retained turnstile missions/dummy categories
and queue/wait storage. Snapshots retain original mission order, selections,
eligibility, names, wait bits and literal player last event/mission IDs. Throttle
clocks, event dialog/response/status fields and window widgets remain uncovered.
The accessors are build-guarded and only called by active replay snapshots.

Evidence: `evidence/m3-waypoint-turnstile-controls.json`. Eighteen waypoint and
fourteen original turnstile receiver/accessor/writer cases pass ASan/UBSan. All
20 actual-writer/source controls pass together. Native state.c/uiTurnstile.c
compile for ARM64 then i686 with one compiler. Patchwork exports 85 patches;
the prior 84 are byte-identical and upstream/ unchanged. Host fixtures do not
prove native ABI; only local LeakSanitizer is disabled for /proc. Runtime is
pending and replay 40224584944 tests earlier 5919e8c, not these additions.
All full-schema/full-state/M3 completion flags remain false.

### Retained friends, saved keybinds and chat settings (2026-10-25 UTC)

Snapshots now retain friend values through the original friendCount (bounded
to MAX_FRIENDS), all 256 saved binding slots and their retained profile, and
all chat window/tab/channel settings. Final slots, unsigned masks/colors and
individual F32 divider bits are included. Chat names are the retained strings
after original localization, not a new raw-wire claim. No receiver changes.

Friend packet-order send/last_pak_id, map-info pointers, unused descriptions,
runtime binding profiles/generated uIDs/pressed states/command[1..3], deprecated
chat systemBF and live chat message/window objects remain uncovered. No new
packet-ID normalization. These exclusions keep the full-schema flag false.

Evidence: `evidence/m3-communication-state-controls.json`. Seventeen actual-writer
cases and the original keybind receiver pass ASan/UBSan, checking its 257 string
and 512 word reads, masks, Dev profile, null/order/final slots, mutation
sensitivity, source immutability and count/storage/string/output bounds.
state.c compiles for ARM64 then i686 with one compiler. Host fixtures are not
native ABI proof; only local LeakSanitizer is disabled for /proc. No new patch;
85 patch files remain unchanged, as does upstream/. Runtime is pending;
40224584944 tests earlier 5919e8c. Full-state and M3 completion remain false.

### Existing user-option table observations (2026-10-25 UTC)

Patch 0086 exposes a const view of the existing option array without calling
userOptionGet, which can initialize its lookup stash. Snapshots preserve original
array order, literal option IDs/bit sizes and the F32 or U32 representation used
by receiveOptions. Unused alternate numeric storage, display labels, data
pointers and delayed-save metadata are excluded. No option/receiver mutation,
lookup initialization or new packet-ID normalization.

Evidence: `evidence/m3-option-state-controls.json`. Eight original receiver/
actual accessor/writer cases pass ASan/UBSan, including mutation sensitivity,
raw NaN/negative-zero/high bits, table order and output bounds. Native uiOptions.c
and state.c compile ARM64 then i686 with one compiler. Patchwork exports 86
patches and the prior 85 remain byte-identical; upstream/ unchanged. Host
fixtures are not native ABI proof; only local LeakSanitizer is disabled for
/proc. Fresh runtime remains pending. Full-state and M3 flags remain false.

### Existing tray storage and default-power observations (2026-10-25 UTC)

Patch 0087 exposes existing player/server tray arrays and the received sticky
mode through const views. The normal getTrayObj lookup writes derived slot
metadata even when creation is disabled, so snapshots never use it. Array order,
nulls, all eight builds, stored tray selections/modes/index mask, power and
inspiration indices, logical power names, macro fields and nullable default-power
identity are retained. Render/icon caches, derived slot metadata and the local
momentary key mask are excluded. Other tray kinds currently retain type only;
this is an explicit coverage gap, not a complete tray/UI schema.

Evidence: `evidence/m3-tray-state-controls.json`. Nineteen actual accessor/writer
and original mode-receiver cases pass ASan/UBSan, including source immutability,
four sticky modes, separate arrays, last slots, nulls and count/string/output
bounds. Native trayCommon.c, uiTray.c and state.c compile ARM64 then i686 with
one compiler. Patchwork exports 87 patches with the prior 86 byte-identical;
upstream/ unchanged. Host fixtures are not native ABI proof; only local
LeakSanitizer is disabled for /proc. Runtime remains pending; full-schema,
full-state comparison and M3 completion remain false.

### Retained initial UI and server-control observations (2026-10-25 UTC)

Partial snapshots now include every built-in window's retained WdwBase fields,
its below flag, global RGBA, eight saved dividers, team/inspiration modes, five
server-feature flags and the received first-person/nocoll values. Patch 0088
adds const mode views only; window/default/clamp/color propagation and all
original receivers are unchanged. Snapshots read existing winDefs directly.
Window values are post-receiver retained state, not raw wire data. Custom and
minimized windows, animation clocks/caches, callbacks and broader control state
remain excluded; no packet-ID normalization is added.

Evidence: `evidence/m3-initial-ui-state-controls.json`. Twelve ASan/UBSan cases
execute original window/divider/mode receivers, actual accessor/writers and the
original server/control assignment fragments. Native state.c, uiGroupWindow.c
and uiInspiration.c compile ARM64 then i686 with one compiler. Patchwork exports
88 patches; prior 87 are byte-identical and upstream/ unchanged. Host fixtures
do not execute the entire initial-window setup block or establish native ABI
or viewport equivalence. Runtime qualification is pending; full-state/M3 flags
remain false.

Replay 40224584944 at 5919e8c has now completed: both targets, outside-error and
partial-state comparisons pass, still with all full-state/M3 flags false. Exact
API/log notices are in `evidence/m3-replay-40224584944.json`; this is CI evidence,
not independent artifact revalidation. PR #6 checkpoint e78f0193 starts fresh
Atlas 40227784437 and replay 40227784453, both pending when this note was written.
Keep their branch stable while they run; this UI addition is later work.

### Door receive-state observations (2026-10-25 UTC)

Patch 0089 adds a read-only view of door wait/loading/fade-request state. It does
not call waitingForDoor(), which can expire and clear the original wait state.
Snapshots also retain game mode and nullable door-animation state, entry/target
position bits, received integer radius, acknowledgement/threshold flags and
animation string. Fade clocks, derived final position/speed and the forced-move
packet-ID bookkeeping remain explicit gaps; no new ID normalization is added.

Evidence: `evidence/m3-door-state-controls.json`. Fourteen ASan/UBSan cases run
the original start/exit receivers, fade-in function and actual view/writers.
They cover no-player/null-packet branches, packet-order decisions, animation
freeing, output bounds and source immutability without any timeout clock read.
Native dooranimclient.c and state.c compile ARM64 then i686 with one compiler.
Patchwork exports 89 patches; prior 88 are byte-identical, upstream/ unchanged.
Dependency substitutes do not prove native ABI or full gameplay behavior; only
local LeakSanitizer is disabled for /proc. Runtime remains pending, including
later initial-UI work; M3/full-state completion flags remain false.

### Retained entity status observations (2026-10-25 UTC)

Snapshots retain status-effect flags, received translucency bits, the logout
bad-connection flag, nullable AFK state/message and ordered designer-status
strings. The original exclusiveVisionPhase read in character_ReceiveStatusEffects
is discarded by that function; this observer does not invent a destination.
Local countdown/rendering translucency, buffs, targeting and packet-order fields
remain gaps. No native patch or normalization change.

Evidence: `evidence/m3-entity-status-controls.json`. Fifteen original-receiver/
actual-writer ASan/UBSan cases cover current/stale packets, null parents, full
consumption, replacement/empty/null strings, retained AFK tails, bounds and
source immutability. Native state.c compiles ARM64 then i686 with one compiler.
All 89 patches and upstream/ remain unchanged. Host packet/earray substitutes
are not native ABI or full-entity proof; only local LeakSanitizer is disabled
for /proc. Runtime qualification and full-state/M3 completion remain pending.

### Bounded world camera observations (2026-10-25 UTC)

Patch 0090 records camera world position/view matrix and nullable player world
position/network coordinates on the existing eight sampled frames. It only
reads these values; no culling, camera or player decisions change. The isolated
model-counter report correlates frame/thread and counter relationships and
rejects incomplete/inconsistent evidence. It does not change visual acceptance
or infer a cause from counters.

Evidence: `evidence/m3-world-camera-controls.json`: opt-in/off and nullable-player
controls verify eight/zero reads over 5,000 frames and source immutability;
midpoint/path regressions and 161 Python tests pass. Native groupdraw.c compiles
ARM64 then i686 with one compiler. Patchwork exports 90 patches, prior 89
byte-identical and upstream/ unchanged. These are host/compile checks; runtime
qualification remains pending. Runs 40227784437/40227784453 use earlier e78f0193
and do not include this patch or the later UI/door/entity-status additions.

### Target and assist state observations (2026-10-25 UTC)

Snapshots now retain literal S64 target/assist/taunter references as two U32
words, ordered nullable placator references, selected DB ID/handle and nullable
current-target logical identity. No pointers or new ID normalization are added.
The original receiver clears the selected target even on a stale self update;
this result is preserved. Its random confuseRand assignment remains excluded.

Evidence: `evidence/m3-target-state-controls.json`: 17 ASan/UBSan cases execute
the original target receiver/reference packer and actual snapshot writers,
covering self/other/stale/null/no-update paths, all reads, order, full-width
values, bounds and immutability. ARM64 then i686 state.c compilation and 161
Python tests pass. CI includes this control on future comparison builds. All
90 native patches and upstream/ unchanged. Host dependencies are substitutes;
runtime qualification remains pending and full-state/M3 flags remain false.

### Retained buff observations (2026-10-25 UTC)

Patch 0091 adds a replay-only const view of the private PowerBuff storage.
Snapshots preserve list order/nulls, power identity, UID, blink/delete flags,
descriptor key/name identities and magnitude F32 bits. Descriptor and magnitude
counts remain independent; no repair or normalization is added. Timer, tooltip
and UI window are excluded. Original full stale updates can still mark buffs
for deletion before checking staleness; the observer preserves those marks.

Evidence: `evidence/m3-buff-state-controls.json`: 21 ASan/UBSan cases execute
original receive/find/update/mark/clear and actual view/writer code, covering
full/diff/delete/stale/no-player/unknown-descriptor paths, retained absent mods,
bounds and source/array immutability. Packet/lookup/earray/free dependencies are
substituted, with fixture arena cleanup; original ownership is not qualified.
Native uiBuff.c/state.c compile ARM64 then i686 with one compiler; 161 Python
tests pass. Patchwork exports 91 patches, prior 90 byte-identical, upstream/
unchanged. Runtime and reviewer qualification remain pending; no M3 pass.

### Literal receive-channel packet IDs (2026-10-25 UTC)

Snapshots now include all 16 additional scalar U32 receive-channel packet IDs
from entIncludeClient.h. Existing create/position/quaternion ID fields retain
their existing paths. No additional canonicalization is applied. If the new
fields expose INITIAL-ID sensitivity, the comparison must fail pending an
individually enumerated reviewer decision. Structured full/basic AttrDef ID
maps remain an explicit gap.

Evidence: `evidence/m3-packet-order-controls.json`: ten ASan/UBSan cases cover
the original header fields/update macro, ascending/stale/equal IDs, literal
0/1/31/32/full-width values, bounds and immutability. A new comparison control
proves newly added IDs are not canonicalized and genuine ID1/31 differences
fail while same-ID comparisons pass. All 162 Python tests and ARM64-then-i686
state.c compilation pass. No native patch or upstream/ change; runtime still
pending and no full-state/M3 claim.

### Leveling-pact roster and fresh replay (2026-10-25 UTC)

The observer retains leveling-pact ID, nullable pact, independent count and
ordered roster ID/name/on-map fields. It preserves stale zero-ID destruction
without rewriting the retained ID, and name tails when local lookup fails.
Derived map caches/server accounting are excluded. The original stale positive
member-count path skips member reads; these controls do not qualify that path.
Evidence: `evidence/m3-leveling-pact-controls.json`: 13 original-receiver/actual
writer ASan/UBSan cases pass, plus all receiver controls and 162 Python tests.
Native state.c compiles ARM64 then i686 with one compiler; all 91 patches and
upstream/ unchanged. Allocator/UI/packet/lookup substitutes limit host coverage.

Replay 40227784453 at e78f0193 completes both targets and both comparisons.
Independent revalidation of artifact 12612527715 (ARM64) and 12613195474 (i686),
each SHA-256 verified against the API digest, reproduces all seven matching
comparisons with the exact approved texture occurrence. Exact command/output:
`evidence/m3-accepted-partial-replay-40227784453.json`. This tests through tray
state, before later UI/door/entity-status/camera/target/buff/packet-order/pact
work. All full-schema/full-state/M3 flags stay false. Atlas 40227784437 is still
pending; keep its source branch stable until completion.

### Buff accessor build-guard correction (2026-10-25 UTC)

Patch 0092 includes the replay feature header before uiBuff.h. Without it,
uiBuff.c compiled successfully but emitted neither buff accessor; the snapshot
consumer still referenced both. This corrects a link defect in the pending
0091 addition, without changing original receiving or accessor behavior.

Evidence: `evidence/m3-buff-build-guard-controls.json`. Actual native uiBuff.c
commands compile sequentially for ARM64 then i686, and llvm-nm confirms both
accessor definitions in both objects. A new actual-header preprocessing control
checks both feature configurations and the disabled/missing-include negative
controls; all 21 existing sanitizer cases pass. The previous compile-only note
was insufficient to establish these definitions. Fresh full linking/runtime is
still pending. Patchwork exports 92 patches, prior 91 byte-identical, upstream/
unchanged. Full-schema/M3 completion and merge approval remain false.

### Pet ownership observations and completed Atlas evidence (2026-10-25 UTC)

Snapshots now retain literal owner/creator EntityRef words and nullable logical
created-by power identity. No pointer addresses or new ID normalization. The
original non-pet branch clears references even on a stale packet while retaining
the created-by power; this is preserved. Existing pet flags/names remain as
previously observed. No original receiving code or native patch changes.

Evidence: `evidence/m3-pet-ownership-controls.json`: ten original-receiver/
reference-packing/actual-writer ASan/UBSan cases, sequential ARM64/i686 state.c
compilation and 162 Python tests pass. Packet, lookup, power and pet-name
dependencies are substituted. Nonempty display-string paths and name decoding
are not qualified by this fixture. Only local LeakSanitizer is disabled for
/proc. Runtime and full-schema/M3 qualification remain pending.

Atlas 40227784437 at e78f0193 is now failed with world_rendered:false after
1,507 seconds despite successful guest connection/cleanup. Independently
SHA-256-verified artifact 12614392749 contains eight valid model-counter pairs
and 54 full model-definition records. Frame 1 has six model-bearing visits
beyond the first three checks; later sampled frames have none. All samples
still have zero model submissions. The final screenshot shows sky/HUD/partial
character and the Help modal, without Atlas terrain. Root cause remains open;
bounded visits are not a complete model census. Exact evidence:
`evidence/m3-world-models-40227784437.json`. Sol 5645585894 confirms the earlier
partial replay pass and failed Atlas, with no new defect or milestone approval.

Fresh Atlas/build 40240791819 and replay 40240791817 test f6332f29, including
the buff build-guard fix and camera diagnostics, but not this later ownership
addition. Preserve those runs; no full-state/M3/M4/M5 completion is claimed.

### Structured attribute packet-ID observations (2026-10-25 UTC)

Snapshots now retain the nested pkt_id_fullAttrDef/pkt_id_basicAttrDef trees
using the original SendCharacterToSelf/SendBasicCharacter parse-table order and
field names. Primitive ID slots become literal U32 values; nested arrays and
null/unallocated trees stay distinct. No pointers, cache initialization, game
receiver changes or added INITIAL-ID normalization. Unsupported schema types,
storage, depth, field count, wide scalar slots and output overflow reject.

Evidence: `evidence/m3-attribute-packet-id-controls.json`: 21 ASan/UBSan cases
execute original int/float/struct receivers and allocation/free with original
schema definitions and the actual observer. Packet/token-store/quantization
dependencies are substituted; attribute value decoding/native ABI are not
qualified. All 32 receiver programs and 163 Python tests pass, including literal
nested-ID sensitivity rejection. Native state.c compiles ARM64 then i686 with
one compiler. All 92 patches and upstream/ unchanged. Fresh runtime/reviewer
qualification remains pending; full schema and M3 remain false.

Sol review 5645758046 accepts implementation through f6332f29, explicitly not
milestone/merge approval. Current runs 40240791819/40240791817 retain that head;
this addition and pet ownership are not covered by those runs.

### Sequence receive observations and pending ID decision (2026-10-25 UTC)

Snapshots retain next sequence index/bits and the ordered triggered-move queue
(index, delay ticks and trigger FX ID). Local mixed-clock move_change_timer,
sequencer timestamps and server-only state are excluded. Original receiving,
queue saturation and stale-packet behavior are unchanged. Evidence:
`evidence/m3-sequence-receive-controls.json`: 17 original-receiver/actual-writer
ASan/UBSan cases, sequential ARM64/i686 state.c compilation and 163 Python tests
pass. Packet/demo substitutes limit host coverage; no native patch changes.

ARM64 artifact 12617326111 from replay 40240791817 is SHA-256 verified and all
351 snapshot digests checked. All three executions pass dispatch/cursor/ACK
validation and normal exit2. Same-ID repeated runs match. INITIAL1/31 differ
only in snapshot0 at 11 newly observed scalar packet-order fields, each 1/31.
`evidence/m3-arm64-id-sensitivity-40240791817.json` enumerates exact values and
original UPDATE_PACKET_ID sites. i686/combined comparison still pending.
Proposed decision for Sol: permit only these enumerated fields, only snapshot0
in the ID-sensitivity comparison, only values equal to that run's INITIAL ID.
This proposal is NOT implemented or approved; strict comparison stays unchanged,
all other/new structured IDs stay literal. Full-schema/M3 remain false.

### Pending NetFx receive-list observations (2026-10-25 UTC)

Snapshots now observe the retained NetFx queue in original order: command,
literal IDs/handle, received delay/duration/radius F32 bits, flags, tint and
active origin/target fields. Inactive fields can retain unwritten storage and
are excluded, as are server bookkeeping and renderer trackers. Client-created
effects may also populate this queue; no exclusive wire-origin claim is made.
Unknown target/origin types retain their literal tags with null active values.

Evidence: `evidence/m3-netfx-receive-controls.json`: 19 original-receiver/actual
writer ASan/UBSan cases pass, including ordered append, destroy command, both
position/entity branches, invalid type error path, full-width values, NaN and
negative-zero bits, source immutability, 8192-entry boundary and bounds failures.
Packet/allocator/demo/debug dependencies are substituted. Both native targets
compile sequentially and 163 Python tests pass. No native patch/upstream change;
full replay/schema, rendering and milestone qualification remain pending.

### Unsigned taskforce mask and nonclock parameter observations (2026-10-25 UTC)

Patch 0093 changes only `1 << count` to `1U << count` in the original taskforce
parameter receive loop. The old expression has undefined signed left shift at
bit31 (the 32nd slot) even with an empty enabled mask. The source-derived UBSan negative
control reproduces that error; the unsigned form preserves the U32 mask and
original read order, retention and clock additions. Exported with patchwork;
prior 92 patches byte-identical and upstream/ unchanged.

Snapshots retain the enabled mask and all 30 nonclock slots, including disabled
retained values. Time-limit/start-time slots are explicitly null because the
original receiver adds the local clock; raw provenance remains a gap. Evidence:
`evidence/m3-taskforce-parameter-controls.json`: nine sanitizer cases plus the
old-code negative control, original enable helper, all32 parameter bits, absent
updates/null taskforce, retained slots, clock addition, bounds and immutability.
Packet/clock dependencies are substitutes. Native entrecv.c/state.c compile
ARM64 then i686 with one compiler; 163 Python tests pass. Full-state/runtime
qualification and milestone approval remain pending.

### Completed strict replay and camera report preparation (2026-10-25 UTC)

Replay 40240791817 at f6332f29 completes both target executions and the outside
error comparison successfully, but its partial-state comparison fails. Both
SHA-256-verified receiver artifacts reproduce all seven CI comparisons exactly:
three cross-target and two same-ID repeat comparisons match; both INITIAL-ID
sensitivity comparisons differ at only snapshot0 in the same eleven enumerated
scalar fields. All702 snapshot digests verify. Evidence and exact command:
`evidence/m3-strict-partial-replay-40240791817.json`. The pending Sol proposal
remains unimplemented; no full-state/M3 pass, and no extra data exceptions.

A diagnostic camera report pairs the existing 0090 samples with validated model
and draw frames/threads. It retains camera/view/player coordinates and reports
the camera transformed by its view matrix plus camera-player distance. It does
not impose tolerances, change rendering acceptance or establish a root cause.
Five focused controls (including torn/malformed/nonfinite/duplicate/bounds and
report-caller paths) and all168 Python tests pass. Evidence:
`evidence/m3-world-camera-report-controls.json`. Atlas artifact still pending.

Independent pet/attribute-ID/sequence/NetFx/taskforce work through dd0c3dee is
now on armport/replay-retained-state and replay 40243785888 is running. Atlas
40240791819 remains undisturbed at f6332f29. No duplicate Atlas run is started;
the replay-only branch is excluded by armport-build.yml. Do not move that
replay branch with further replay/native changes until its run completes.

### Raw taskforce time receipt history (2026-10-25 UTC)

Patch0094 observes a parameter immediately after its original assignment and
before either original local-clock addition. The active replay observer records
only TIME_LIMIT/START_TIME values as bounded ordered receipts (entity index/ID,
taskforce ID, slot, raw U32 seconds). Ordinary execution and disabled builds are
inert. No packet reads, arithmetic or enable decisions change. Replay init clears
the receipt count; histories are not reconstructed deadline/lifecycle state.

Evidence: `evidence/m3-taskforce-time-controls.json`: 15 sanitizer cases plus
the old signed-shift negative control and the actual disabled-header test pass.
Controls cover both clocks, full-width/zero values, retained/absent/null cases,
changed entity/taskforce identities, active/nonclock inertness, 8192 receipt
boundary, overflow rejection and history/source immutability. Packet and clock
dependencies are substituted. Native entrecv.c/state.c compile sequentially
ARM64 then i686; 168 Python tests pass. Patchwork exports94 patches with prior93
byte-identical and upstream/ unchanged. Current replay40243785888 tests dd0c3dee
before this addition; keep it running. Full-schema/M3 and merge approval false.

### Retained control destinations (2026-10-25 UTC)

Partial snapshots now retain control_state.first/nocoll and individual F32 bits
of the optional slave orientation destination. Local input can also write these
fields; this is not exclusive wire provenance. Motion, prediction, input queues
and local clocks remain excluded. Original receive fragments are unchanged.

Evidence: `evidence/m3-control-state-controls.json`: 12 ASan/UBSan cases execute
the exact original receive fragments and actual writer, checking every legal
flag pair, present/absent orientation, full F32 bits (NaN, negative zero, infinity),
consumption, nonmutation, excluded local fields and overflow rejection. Packet
primitives/surrounding lifecycle are substituted; no native ABI claim. Native
state.c compiles ARM64 then i686 with one compiler. All169 Python tests pass,
including diagnostic rejection of derived camera-distance/transform overflow
from finite inputs. That report safeguard does not change rendering acceptance.
All94 patches and upstream/ are unchanged. Active replay40243785888 tests dd0c3dee
before the raw-taskforce-time/control additions; keep it running. No full-schema,
M3, merge or Thor qualification is claimed.

### Original world-model lookup observations (2026-10-25 UTC)

Patch0095 observes the existing groupModelFind results separately: missing
object-library entry, present entry but null modelFind result, or found model.
The network getGeo caller does not report a null model; prior traversal samples
therefore cannot distinguish these lookup failures. Each outcome has an atomic
process-wide16-record budget. Bounded labels and original loadstate/vertex/triangle
metadata are recorded; names are diagnostic labels, not acceptance identities.
No second lookup, fallback, culling/data/packet changes or root-cause claim.

Evidence: `evidence/m3-group-model-lookup-controls.json`. Four source-derived
ASan/UBSan configurations compare original and observed call counts/returns,
exercise eight concurrent callers, independent budgets, long/sanitized labels,
and disabled client/server guards. Lookup/Win32 atomic/environment/trace adapters
limit host coverage. Native group.c compiles sequentially ARM64 then i686.
All173 Python tests pass; the report rejects malformed/inconsistent/over-limit
observations and preserves complete isolated records without a rendering verdict.

All36 receiver-state programs also pass after fixing the contact test's overly
broad function extraction, which unintentionally included the new taskforce
observer. The intended original function body is still executed. All95 patches
were exported with patchwork, prior94 byte-identical; upstream/ unchanged.
Attempted local full links cannot run because these partial build directories
lack most original objects/libraries; only changed-unit compilation is qualified.
Full linking/runtime remains CI work. Keep active replay40243785888 and Atlas
40240791819 on their existing heads; this pending delta is not qualified there.
Full-schema/M3 completion, merge approval and Thor readiness remain false.

### Private server Atlas supplement (2026-10-25 UTC)

The base server assembly has173,011 files /2,977,730,517 bytes and lacks all
2,877 files (including488 geometry files) from the same pinned retained Atlas
archive already staged for the client. The retained server stdout from
40227784437 contains10,506 missing-root-geometry records; this is a bounded
capture, not a claim about complete server output. Original groupnetsend sends
geometry only for a non-null model; receiveDef clears the old definition and
only loads a model when that bit is set. This supports an input-mismatch cause
hypothesis, not proof of a fixed render or a particular observed packet.

The ArmPort host now freezes the same two pinned Atlas inputs beside its guest
helpers. After the original full base/schema validation and private copy, before
any database/server initialization, the guest verifies/extracts that archive and
merges it with the client's case-aware strict merge. Conflicting bytes fail;
matching collisions preserve the original file. No new assets, server binary,
base manifest, schema, generated-cache exemption or rendering threshold changes.
The original server-data validators remain unchanged.

All179 Python tests pass. A real-archive control rehashes all2,877 staged files
using the original base directory spelling (a structural fixture; unavailable
base binary payload is not claimed). There are no case duplicates or collisions.
Exact commands, controls, captured-log identity and limitations:
`evidence/m3-server-atlas-staging-controls.json`. A fresh native server/client
run remains required; preserve currentAtlas40240791819 until it completes.

Replay40243785888 ARM64 source dd0c3dee passes execution/hash checks for351
snapshots and same-ID repetition. INITIAL1/31 has44 literal mismatches only
in snapshot0: prior11 scalar packet IDs plus33 attribute-tree packet IDs. No
normalization has been added. See `evidence/m3-arm64-expanded-ids-40243785888.json`;
i686/cross-target results and Sol's exact normalization decision remain pending.

### Raw player reward times and completed replay (2026-10-25 UTC)

Patch 0096 observes the two original INITIAL token timer assignments only after
the original destination check accepts them. The bounded ordered history copies
entity identity, normal/active-player list, index, name and received U32 seconds.
It is inert outside replay and in disabled builds. It does not call award helpers,
change packet reads, or compare the live timer, which later awards set from a
local clock. Long names/history/output overflow fail rather than truncate.
All 37 receiver-control programs pass, including 20 new sanitizer cases; all
180 Python tests pass. Changed state.c/entrecv.c compile ARM64 then i686 with
one compiler. Host fixtures are not native ABI or complete runtime proof.
`evidence/m3-reward-time-controls.json` records commands, outputs and limits.

Replay 40243785888 at dd0c3dee is complete: both target execution jobs and
outside-error comparison pass; strict partial comparison fails. Independent
verification reproduces all seven comparisons and 702 hashes: three cross-target
pairs and both same-ID repetitions match; only snapshot 0 differs in each
INITIAL-ID sensitivity pair, with the same 44 fields on both architectures.
The previous 11 scalar IDs plus 33 attribute-tree leaves require Sol's explicit
normalization decision. No normalization was added. Full-schema/full-state/M3
flags remain false. `evidence/m3-replay-expanded-ids-40243785888.json`.

The server Atlas supplement merge explicitly copies ordinary private files.
PRoot --link2symlink must not turn temporary extraction links into dangling
paths. The no-link control and real retained-archive rehash pass after temporary
files are removed. Base/schema validators remain unchanged; runtime rendering
is still pending. `evidence/m3-server-atlas-staging-controls.json`.

### Friend receive ordering and exact missing server geometry (2026-10-26 UTC)

Patch 0097 exposes receiveFriendsList's existing last packet ID through a const
getter; the static keeps its original zero initialization/lifetime at file scope.
The receiver body is byte-compared against immutable upstream after reversing
only that scope/name change. Per-friend `send` and the global ID retain full U32
words. No new normalization or signed-comparison change. Source-derived controls
cover full/stale/equal/lower/high-bit IDs, absent entries/null entity, cumulative
out-of-order behavior, exact consumption, nonmutation and output/storage bounds.
All 16 new and 17 updated communication cases pass with ASan/UBSan; 180 Python
tests pass. Native uiNet.c/state.c compile sequentially ARM64/i686, and llvm-nm
confirms the accessor definition in both objects. Runtime remains pending.
`evidence/m3-friend-order-controls.json`. These newly exposed IDs may retain
INITIAL sensitivity beyond snapshot 0; do not silently normalize them.

The retained 40227784437 server capture explicitly lists 483 distinct missing
`.geo` paths. All 483 match files in the already approved Atlas supplement;
none needs a new source. The exact path lists are retained in
`evidence/m3-server-atlas-staging-controls.json`. This strengthens the staging
diagnosis; it does not declare rendering or M3 complete.

### Current runtime qualification (2026-10-26 UTC)

Tested implementation head is 4c8b6c39 on armport/m3-atlas. Runs 40247679019
(Atlas) and 40247679017 (replay) are active; do not restart them. Local working
branch is armport/replay-retained-state; no integration/milestone merge.
ARM64 replay artifact 12620176960 independently passes 351 snapshot hashes,
cursors/ACKs/error checks and 117 same-ID comparisons. ID1/31 differs only at
snapshot 0 in 45 fields: prior 44 plus friend_receive_id. i686/cross-target
qualification remains pending. No new normalization; Sol decision required.
See evidence/m3-arm64-replay-40247679017.json for exact command and paths.

Prior Atlas 40240791819 completed failed: connection passes, rendered world
false. Eight complete isolated camera records show player Y -978.519592 then
-2000, with camera tracking the player. The retained bounded server capture
has 482 explicit missing geometry paths, all in the approved supplement.
This supports, but does not prove, the missing-server-geometry hypothesis.
See evidence/m3-atlas-camera-40240791819.json. Fresh Atlas tests the staging
fix; no terrain pass is claimed. Full schema/M3/M4/M5 remain unqualified.

### Accepted power creation times (2026-10-26 UTC)

Patch 0098 observes the original character_ReceivePowers timestamp assignment
only after power acceptance. The bounded history records nullable parent
identity, received build/set/power ordinals, literal received/retained unique IDs,
copied logical name and U32 wire seconds. It runs before power_LevelFinalize;
it neither calls a packet reader nor changes original state or clock handling.
Live ulCreationTime remains excluded because power_Create and lifetime changes
also write local-clock values. This is receive history, not full power lifecycle.

All 26 source-derived ASan/UBSan cases and 20 reward-time regression cases pass;
180 Python tests pass. The original and observed accept blocks have identical
read/call counts and power/set storage across success/failure/existing/temp-power
controls. Changed native character_net.c/state.c compile ARM64 then i686 with
one compiler. Only local LeakSanitizer is disabled for /proc; CI keeps defaults.
`evidence/m3-power-creation-time-controls.json` records exact commands and limits.
Fresh runtime qualification is required. All prior 97 patch bytes are unchanged.
No new packet-ID normalization, milestone completion or merge approval.

Replay 40247679017 at 4c8b6c39 has now completed: both native jobs and outside-error
comparison pass; strict partial-state comparison fails. Independent verification
of both SHA-256-verified artifacts authenticates 702 snapshots and reproduces
all seven comparisons. Three cross-target pairs and both same-ID repeats match;
both INITIAL1/31 pairs differ only in snapshot 0 at the same 45 literal fields.
See `evidence/m3-replay-40247679017.json`. Sol's exact normalization decision is
still pending. Atlas 40247679019 remains active and must not be restarted.

### Retained active powers and received modes (2026-10-26 UTC)

Snapshots now retain PowerInfo.activePowers as ordered nullable logical
build/set/power references, without resolving or repairing them. Character
pPowerModes retains signed words, duplicates and order. Null PowerInfo remains
separate from an empty active list. Recharge timer values and membership remain
excluded: the original powerInfo_UpdateTimers changes and removes them using
elapsed time. No original receive/update behavior changes and no new patch.

All 19 source-derived sanitizer cases pass, including the actual mode receiver
and duplicate/add/remove/absent active helpers, bounds, nulls, nonmutation and
an inaccessible recharge pointer. Inventory-writer regression, 180 Python tests
and sequential ARM64/i686 state.c compilation pass. The inventory fixture now
extracts its five actual functions individually so adjacent observers do not
silently enlarge its dependencies. `evidence/m3-power-activity-controls.json`
records commands and limits. Host controls do not establish native ABI or full
activation/recharge lifecycle. Fresh runtime qualification remains required;
active replay 40254223051 tests preceding power-time head 38b5cebb only.

### Power-update wire-time observations (2026-10-26 UTC)

Patch 0099 extends the accepted creation-time history to PowerInfo updates and
records received recharge F32 bits after the original timer-change call. Ordered
bounded histories retain literal identities and signed references; no float
normalization, packet reads or original assignments change. Live recharge
countdown/membership and live creation clocks remain excluded because local
elapsed-time code changes them. This is receive history, not full lifecycle.

All 14 source-derived ASan/UBSan update cases, 26 initial creation-time cases,
20 reward regression cases and 180 Python tests pass. Original-vs-observed
controls retain reads/calls/storage, including skipped/accepted entries, raw
NaN/zero/infinity bits, repeated references, bounds/reset/nonmutation and later
local timer overwrite/removal. PowerInfo.c/state.c compile ARM64 then i686 with
one compiler. Only local LeakSanitizer is disabled for /proc; CI keeps defaults.
See `evidence/m3-power-update-time-controls.json` for commands and limits.
All prior 98 patches are byte-identical; upstream/ remains untouched. Fresh
native linking/runtime qualification is still required. No milestone pass.

### Atlas terrain and reviewed material follow-up (2026-10-26 UTC)

Atlas run 40247679019 at 4c8b6c39 has completed FAILED. Artifact 12622117293
SHA-256 f15fd5417893ae01967d9c4d09b9812cb6ed1535fe4b29ab6aaddeeeaf5a3b91
contains visible statue/stairs/trees and a grounded player in the final frame.
All eight camera samples retain player Y 0.251066208; all eight traversal samples
have 2253 model calls and 1293 sort requests. The guest reports successful
connection and cleanup. The screenshot gate still fails: Atlas Park map-name
OCR is absent, and the scene has flat blue surfaces/black blocks/missing textures.
The screenshot rule and rendering/culling behavior have not been weakened.

All 27 material additions in the existing reviewed 2904-file manifest have exact
texture-trick errors and empty runtime texture-path matches in this run. The
old 2877-file baseline remains intact. Existing reproduction code fetched only
27 pinned original ranges (4357758 bytes), reused the exact old baseline and
verified archive c7ed82aa plus every payload. No new donor/name/pin is introduced.
The new stage_atlas_materials.py selects just those 27 files (8955931 bytes),
verifies exact inventories/hashes after caches and artifact downloads, and
stages a separate strict-collision client layer in Atlas and both replay targets.
It does not replace the original baseline or server assets. New data is not
claimed to close all material errors; native visual qualification is pending.

All 186 Python tests pass, including corrupt archive/member/cache, missing/extra
files, atomic failure, links and collision preservation. Real archive staging
verifies all 27 files locally. Evidence, exact errors, snapshot pins, recovery
receipt and command outputs are in evidence/m3-atlas-materials-40247679019.json.
Full schema/comparison and M3/M4/M5 remain unqualified; PR #6 stays draft.

### Reviewed INITIAL-ID comparison scope (2026-10-26 UTC)

Sol review 5646841168 accepts implementation through 4c8b6c39 and permits a
comparison-only rule for the new source-proven packet-ID observations. The
implementation now normalizes only snapshot 0, 16 explicitly named scalar
channels, primitive leaves of the exact basic/self AttrDef schemas, and the
friend-order ID, each only when an integer equals that run's INITIAL ID. Schema
names/order/shapes and unrelated values stay literal. Saved snapshots, later
snapshots, cross-target and same-ID comparisons are unchanged. The previous
five lifecycle destinations retain their already agreed behavior. The scope
approval does not approve this new implementation or a milestone/merge.

All 191 Python tests pass (13 comparison tests), including wrong values/types,
exact and adjacent paths, schema mutation/nulls, input nonmutation and actual
comparison failures for later/same-ID/cross-target differences. SHA-verified
artifacts from 40247679017 and 40254223051 each revalidate 702 snapshots and pass
all seven pairs with this proposed comparator. The historical CI runs remain
FAILED; their strict sensitivity differences were respectively 45 and 20 fields
at snapshot 0. This is retrospective qualification, not fresh combined-head CI.
The exact single authorized texture occurrence and false full-schema/full-state/
M3 flags remain. Commands, pins and results are recorded in
`evidence/m3-initial-id-normalization-controls.json`.

Next: fresh native replay and Atlas qualification for the combined power-time,
active-power/mode, 27-material and comparison changes, plus Sol's implementation
review. Full retained-state coverage and the Atlas screenshot remain open;
M4 Android surface and physical Thor/M5 are not qualified. No Thor test ready.

### Retained turnstile event state (2026-10-26 UTC)

Patch 0100 adds a const-data/copy-out view of the original event name, expected
response, acceptance/decline/progress/player counts, instance ID and event-status
reply/status masks. The snapshot writer bounds the fixed name and preserves
signed counts and all U32 bits, including literal IDs 1/31. No original receive,
ACK, dialog or update behavior changes. Local input can also change response
state; the snapshot does not claim exclusive packet provenance. Local throttle
clocks, widget objects, force-queue and invitation state remain excluded.

Eleven original-receiver/actual-accessor/writer sanitizer cases pass, including
read widths/counts, ACK identity, replacements, response changes, high-bit IDs,
name/output bounds and nonmutation. Fourteen queue/status regression cases and
191 Python tests pass. uiTurnstile.c/state.c compile ARM64 then i686 with one
compiler. Host packet/dialog/ACK substitutes are not native ABI/runtime proof;
only local LeakSanitizer is disabled for /proc. Patchwork exports 100 patches;
prior 99 are byte-identical and upstream/ stays unchanged. Commands/output are
in `evidence/m3-turnstile-event-state-controls.json`. Fresh runtime/review pending.

Preserve Atlas 40263048945 and replay 40263048934 at 9d82645c; they test the
preceding combined power/material/normalization head, not this event addition.
Full state, screenshot, M3/M4/M5 and Thor readiness remain unqualified.


### Verified Atlas material outcome (2026-10-26 UTC)

Atlas 40263048945 at 9d82645c completed FAILED. Artifact 12628120860 was
independently downloaded and SHA-256 verified (4d67049025022d17caaaa6b88f4da39f43ac20b38916337c460f6ee2c7b5e0d4).
All 33 exact error messages associated with the reviewed 27-file material
extension are absent from the complete error inventory. This establishes that
bounded improvement, not complete materials or terrain acceptance. The full
screenshot shows stairs/railings/trees/player but flat blue buildings, a purple
statue and incomplete UI; map-name acceptance remains false. The guest remains
connected; world_rendered is false. Remaining exact plaza/statue errors and
artifact/file hashes are in evidence/m3-atlas-material-outcome-40263048945.json.
Do not weaken the screenshot criterion or expand asset selection silently.

Sol review 5647159725 accepts implementation through 9d82645c, explicitly not
milestone or merge approval. Replay 40263048934 passed the partial scope only;
full schema/state/M3 remain false. Patch0100 at c72dbc58 is now qualifying on
armport/replay-retained-state in run 40273728728; ARM64/i686 remain sequential.
This docs-only work-branch update must not cancel that run. Next investigate
remaining plaza/statue dependencies and UI/map-name rendering against existing
asset authority, then inspect fresh event-state replay and obtain its review.
M4 surface and Thor/M5 remain unqualified. No device action is ready.


### Retained force-queue name (2026-10-26 UTC)

Patch0101 exposes a const pointer and exact capacity of the original deferred
force-queue event name. Snapshots serialize the bounded retained name; original
packet reads, strcpy, window action and UI consumption/clearing remain unchanged.
Seven source-derived ASan/UBSan cases cover original reads/window call, replacement,
empty/cleared state, 127-byte boundary, invalid retained termination/output bounds
and nonmutation. Eleven event and fourteen queue regression cases and all191
Python tests pass. Native uiTurnstile.c/state.c compile ARM64 then i686 with one
compiler. This does not qualify oversized original input or full UI lifecycle.
Patchwork commit45ce405 exports101 patches; upstream/ remains untouched.
Commands/output: evidence/m3-force-queue-state-controls.json. Runtime and review
of this delta remain pending. Prior c72dbc58 replay40273728728 now passes both
targets and partial comparison; full-schema/full-state/M3 flags remain false.
No screenshot change, asset expansion, Android-surface or Thor qualification.
