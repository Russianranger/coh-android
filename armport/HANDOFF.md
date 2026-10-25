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
