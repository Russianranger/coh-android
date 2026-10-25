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

## Audio-table evidence follow-up (2026-10-25 UTC)

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

`python3 armport/scripts/audit_audio_tables.py --identities /tmp/coh-r21/audio-identities.json
--cache /tmp/coh-r21/audio-metadata --output armport/evidence/m3-audio-file-tables.json`
reports 15 archives, 2,177 file paths, 207,340 metadata bytes and zero texture/geometry
entries. The identity input is exactly `git show HEAD:assets/zones-audio-metadata.json`,
SHA-256 `729035bea0e65fc9585c084efbb67dea0ffc2546f630dc01c28811173e95c78b`.
The reused range reader validates HTTP 206, exact Content-Range, length, ETag and
Last-Modified; metadata decoding validates frozen SHA-256 and complete PIGG tables.
Full decoded paths are retained. A mutated cached byte is rejected by the digest check.
A set comparison with `assets/catalog.json` and the earlier 57-archive evidence
confirms 57 + 15 = 72, disjoint, missing []. No payload bytes were fetched or staged.
This supplies the previously missing audio tables; it does not establish six-run
literal replay agreement or activate the texture exception. Reviewer acceptance,
rendered Atlas and full state comparison remain outstanding. M3 is incomplete.

## Sol review 5641405794: runtime follow-up (2026-10-25 UTC)

No new implementation finding at 703ad1e / code 396c470; review is not a
milestone or merge approval. [Review](https://github.com/Russianranger/coh-android/pull/6#pullrequestreview-5641405794).
Evidence and exact local outputs: `evidence/m3-m4-review16.json`.

M4 run 40155140217's creation trace proves menu 8/index -16 at queue and
primary selection. `hybrid_start_menu` invokes the destination entry before
`start_menu`, which only sets `gNextMenu`; `serve_menus` commits it next frame.
0074 replaces the immediate initialization restart with the existing preview
reset/deferred-loop mechanism. It does not substitute or filter a pointer.
The actual initialization/queue/animation selection control rejects the old
index under UBSan; 36 fixed source-derived transitions/empty selections pass.
Live create/save/restart/reopen remains unqualified.

Atlas 40154965180 ends at character selection without host Next. The retained
stdio later shows stage 6/select 1 and the isolated history is clear. The
startup diagnostic's `setvbuf` was macro-routed to FileWrapper despite CRT
streams; 0075 calls CRT `(setvbuf)` directly. Preprocessing verifies the calls;
the host macro-routing control changes live visibility 0 to 1 (two wrapper
calls to zero). That host control models the wrapper's non-CRT no-op branch;
real Wine before/after controls are now part of libraries CI. This is not yet
an Atlas pass or proof of the complete stall resolution.

Run 40156677877's server job instead failed before runtime on the expired
reference-win32-runtime artifact. Artifact 12428500525 from 39782080360 has
been downloaded and matched to API SHA-256
`3745750f83d35ceda47871d65570e579f66eff0af011f0c983d228c9eae1fe98`.
The existing retained set has 47 files / 52,230,721 bytes. CI now restores that
bundle, verifies every file on both cache hit and miss, and retains a new copy.
No donor binary or external asset is changed.

Replay 40156677880: i686 completes/rejects all three runs on the same texture
error. ARM64 id1-a rejects likewise; id1-b returns -9 after 134.060 s, despite
terminal/cleanup/exit witnesses. No host timeout or recorded cgroup OOM count
increase; the cause is still unresolved. No acceptance relaxation is made.

Validation: 112 Python tests; source-derived power and stdio controls; complete
donor inventory and corruption/missing/link controls; both changed native
translation units compile for ARM64 then i686. Outputs are in the evidence
file. Full builds, real Wine controls and runtime reruns remain pending.
Texture exceptions stay OFF. M3/M4 are incomplete; no merge approval.

# M3 report: incomplete, implementation review requested

Updated 2026-10-25. Draft PR #6 targets COH-ArmPort. This is an implementation
review checkpoint, not a claim that M3 is complete or ready to merge.

## Sol review 5641229238: changing OCR history and complete error series

Code 396c47010c1480639ab9afe0c80410dc8b771597 is being qualified by
[build/Atlas 40156677877](https://github.com/Russianranger/coh-android/actions/runs/40156677877)
and [replay 40156677880](https://github.com/Russianranger/coh-android/actions/runs/40156677880)
on armport/m3-review15. The following documentation-only integration preserves
the already running Atlas 40154965180; these new runs test the identical code.

[Review 5641229238](https://github.com/Russianranger/coh-android/pull/6#pullrequestreview-5641229238)
confirmed the prior layout, pipefail and QA-selector corrections and found a
remaining OCR timing gap. Character selection can open a dialog during the
wait/capture/OCR before final Play/Return. The host now rechecks the complete
isolated history immediately before that input and records `play_blocked`
without sending input or writing a play marker on rejection. Character OCR
and layout-coordinate lookup likewise cannot carry a stale clear-history check
across the following click.

[Actual-host before/after controls and complete local test output](evidence/m3-sol-review-5641229238.json)
reproduce the unsafe Return and Play click before the fix, and only the initial
character click afterward. New cases cover error/alert/fatal, malformed/torn
or missing history arising during selection, waiting, capture or OCR. Clear
history preserves both final-input paths. The full Python suite passes 111 tests.

Replay now retains all three independent executions when ordinary dispatch
data errors are the only rejection. It first checks Wine, integrity, complete
cursor/ACK transcript and every partial-state hash, then raises a distinct
data-error rejection caught only to collect the next fresh-prefix execution.
Any rejection still fails the overall job; later successes cannot rescue it.
Abnormal exits, Wine exceptions, malformed evidence, fatal/assert or snapshot
failures still stop immediately. Six-run artifacts remain pending CI; this
does not enable a texture exception or qualify partial-state comparison.

The running [Atlas 40154965180](https://github.com/Russianranger/coh-android/actions/runs/40154965180)
is kept intact while a separate candidate branch qualifies this follow-up.
[M4 40155140217](https://github.com/Russianranger/coh-android/actions/runs/40155140217)
passed guest boot and started interactive create/save/reopen. Sol found no new
implementation issue in M4 staging 78a5624; its runtime result and bad-power
producer remain pending. M3/M4 remain incomplete, with no merge approval.

## Sol 6.1 review 5641164200 follow-up (2026-10-25)

[Review](https://github.com/Russianranger/coh-android/pull/6#pullrequestreview-5641164200)
requests two implementation corrections at 2e83133f. Both are addressed here;
new review and runtime qualification remain required.
[Artifact identities, actual-function/shell controls and 101-test output](evidence/m3-sol-review-5641164200.json)
record the evidence.

- Remove the host's `server_clicked` fallback for layout Next. Revalidate
  stage/selection and the complete isolated dialog history immediately before
  layout entry. OCR Play also requires clear history. Tests execute the actual
  `drive_login` function with mocked process/UI boundaries. Missing, malformed
  and outstanding-dialog traces each click Next and write the marker before
  the fix, but send no input and write no marker afterward. Positive layout/OCR
  paths and a dialog appearing after the wait are covered.
- Enable `pipefail` in the grid-corruption control step. A test executes the
  actual workflow block under `bash -e` with an injected control exit 23.
  Before: step exits 0 and emits the notice; after: exit 23, no success notice.
  A successful control still emits its output notice.
- Completed [Atlas 40148424741](https://github.com/Russianranger/coh-android/actions/runs/40148424741/job/121037254901)
  fails at the exact access-level QA notice. All 49 samples have unchanged
  3,376,618-byte stdio, no QA input, and no rendered world after 1,506 seconds.
  The selector returns two windows; 10485761 is the previously mapped main
  game window. xdotool's source documents/defaults to `--any`, so PID **or**
  title matches. Add `--all` to require both. Keep the exact notice, one PID,
  unique window, successful focus and three-attempt bound. Unknown/finished
  notices and failed/ambiguous searches still receive no input. Live resolution
  of this stall is pending new CI; the saved frame is still loading.
- Completed [replay 40148424802](https://github.com/Russianranger/coh-android/actions/runs/40148424802)
  no longer reproduces the objSplitPlanes crash in id1-a. Both architectures
  exit 2 after 117 dispatches/partial snapshots, but fail one identical
  `HIPS_miniskirt_1` dispatch error. id1-b/id31 are unrun and partial-state
  comparison is skipped. Sol verified 176,168 staged files, 8,971 directories,
  zero case aliases and the exact eight-file composite layer in both jobs.

Local command `python3 -m unittest discover -s armport/tests -p 'test_*.py' -v`
passes 101 tests. No native source changes in this follow-up; the prior
ARM64/i686 compilation and grid-control evidence remain applicable. M3/M4
remain incomplete. The texture exception stays OFF; complete audio file tables,
six-run identity and full state coverage remain outstanding. M4 still needs the
new Release diagnostic and corrected case staging to identify the bad power's
producer. No new data fetch, APK, signing or merge is part of this checkpoint.

## Review 5639886811 follow-up: native grid overlap (2026-10-24)

[Exact artifact identities, terminal rows, disassembly and local command outputs](evidence/m3-review12-grid-and-runtime-40128377861.json)
cover the following findings. This checkpoint addresses implementation findings;
M3 and M4 remain incomplete, with no milestone or merge approval.

- Replay [40128377861](https://github.com/Russianranger/coh-android/actions/runs/40128377861):
  ARM64 stops inside dispatch index 1, ID 32, command 29, cursor 309912.
  There is no receiver failure row, cleanup-begin or exit-begin witness.
  Stdio records EXCEPTION_ACCESS_VIOLATION; Wine faults at 0x1400A1228,
  `objSplitPlanes` gridcollobj.c:319, reading a corrupted child pointer.
  The new failure notice includes terminal receiver/zone rows, cleanup/exit
  witnesses, failure/assert text, Wine exception and failed inventory.
- Atlas [40128377899](https://github.com/Russianranger/coh-android/actions/runs/40128377899/job/120976643585):
  stops at map.finish.begin. Its exact Release binary resolves 0x14009607C
  to the same function, gridcollobj.c:259. `ldrh w9,[x22],#2` reads tri_idxs
  through x22=0xC180000000000000. This is a different corrupted cell field.
- Patch 0071 fixes a concrete overlap in modelCreateCtris: triangles used
  the raw on-disk grid size as their offset despite 0034 expanding native
  cells and retaining raw indices in a larger grid allocation. They now start
  at uiGridAllocSize, as the shared-heap path already does. i686 retains its
  existing offset because its grid allocation equals the disk size.
  Source-derived ASan/UBSan controls overwrite grid cells with the old offset
  and preserve all grid bytes with 0071, for raw sizes 74 and 80. These controls
  establish the allocation defect; new runtime CI must establish crash resolution.
- i686's itemized dispatch inventory contains 14 texture errors and no
  mission_room error. This confirms the two room errors disappeared after
  the case-equivalent staging repair, without granting an error exception.
- M1: the character-select shortcut takes dialog/fatal state from the entire
  ordered zone-trace.jsonl. Missing, malformed, truncated, unmatched or
  outstanding dialog records fail closed. Stdio supplies only the latest UI
  stage. Earlier, interleaved and cross-thread dialog controls are included.
- L1: 0072 caches the power-trace environment opt-in. L2: smoke staging emits
  a case-duplicate audit after **all** runtime data layers, including the new
  composite layer. The actual CI inventory counts are still pending.
- M4 [40127841088](https://github.com/Russianranger/coh-android/actions/runs/40127841088)
  supplies the corrected caller 0x1403BD1E0: createPrimaryAnimationEvents,
  uiPowerCust.c:1634 (getPowerCustomization inlined). The selected power is
  0x10000000000. Patch 0073 logs the original menu/index, selected pointer,
  passed power and array address at queue/primary sites. It neither repairs
  nor filters the pointer. The producer and runtime fix remain outstanding;
  M4 must consume the newly built Release and the corrected staging afterward.

Local validation: 92 tests pass; all three modified source files compile for
ARM64 Release and i686 Release sequentially with two compiler processes.
The evidence above records commands, exit codes, object hashes and control
output. Both workflows run the new checks; full runtime CI remains required.

### Eight approved composite dependencies

[User decision 6389265419](https://github.com/Russianranger/coh-android/pull/6#issuecomment-6389265419)
authorizes exactly the historical proposal's 8 files / 658,461 bytes. The new
staging script mechanically recomputes original declaration leaves, subtracts
the prior selection, and checks exact proposal paths, manifest/archive pins,
counts and hashes. Both workflows add a separate final strict layer. Every
cache and artifact hit reopens the existing reviewed source archives, verifies
archive SHA and full inventory, checks selected payload SHA, and independently
checks the restored layer for missing/extra/linked/changed files. This costs
another read of the existing archives; it introduces no new source or leaf.
A CI notice reports the count/bytes and disabled texture exception. Actual
CI staging and resulting errors are pending.

All paths below are relative to `data/texture_library/v_players/avatar/super_shared/`:

| File | Reviewed source |
|---|---|
| gloves/glove_v_enforcer_01.texture | zones-world-supplement |
| gloves/glove_v_enforcer_01_bump.texture | zones-world-supplement |
| gloves/glove_v_enforcer_01_mask.texture | zones-world-supplement |
| shoulders/spadr_v_gears_01.texture | zones-world-supplement |
| shoulders/spadr_v_gears_01_bump.texture | zones-world-supplement |
| shoulders/spadr_v_gears_01_mask.texture | zones-world-supplement |
| belts/belt_v_imperialdefense_01.texture | client-visual |
| belts/belt_v_imperialdefense_01_normal.texture | client-visual |

L3 remains unresolved: `assets/zones-audio-metadata.json` pins 15 archive metadata
records, but does not itself contain their complete decoded file tables.
Names alone do not prove texture absence. The conditional texture exception
stays OFF pending complete tables and the required six-run literal identity.
The previous sections below retain historical evidence, not current approval state.

## Case-equivalent data directories (2026-10-24)

[Replay 40118399218](https://github.com/Russianranger/coh-android/actions/runs/40118399218/job/120944883208)
identifies the two missing-room groups as PPD_Start_01_22& and grp141175.
Their original parent definitions use _BNK_HALLWAY_01 and _ofc1_start_01.
The same stdio records both geometry paths missing even though their exact
files and models are in the retained, already approved Atlas supplement.
[Artifact hashes, local reproduction and test output](evidence/m3-case-merged-data-40118399218.json)
record the investigation. This is not a request for additional assets.

The old merger creates separate original-case text directories and lowercase
supplement directories. A reproduction with the real original text/rootnames
and verified geometry leaves both requested original-case paths absent.
The merger now keeps one physical directory for each case-equivalent path,
using the first spelling, and preserves first-layer file contents. Strict
supplement checks still compare every earlier colliding input's bytes before
copying. Existing ambiguous destination entries and file/directory conflicts
fail explicitly. Four regression tests cover those cases; all 87 tests pass.
The corrected reproduction finds both exact geometry hashes at the original
requested paths with no duplicate case-folded entries. A full local merge of
156,287 original files and 2,877 approved supplement files retains all 159,164
files, has zero case-duplicate entries, and verifies both geometry hashes.

This establishes a staging defect, not a runtime tray or Atlas pass. New CI
must establish the resulting error inventories and rendered world; neither
strict replay acceptance nor the conditional texture exception changes.

M4 is independently running [40127841088](https://github.com/Russianranger/coh-android/actions/runs/40127841088)
at a63d0952d72987a1c237b6604304a3fbb15af3df, using Release 40127311343 and the
existing data pin. Exact downloaded Release disassembly now confirms the
48-byte power-lookup frame captures incoming LR before getenv and passes it
to the noinline helper. No __chkstk is present in that lookup. This confirms
0070's generated code; runtime caller identification is still pending.

## Login progress and corrected caller diagnostic (2026-10-24)

The completed [Atlas run 40118399219](https://github.com/Russianranger/coh-android/actions/runs/40118399219/job/120947425896)
failed before map.start. Its selected-character stage remained at 6, and no
Next/play marker was recorded before guest cleanup. The eight post-login
screens are 70–114 seconds apart; the driver runs OCR repeatedly on each
same image. The final character screen shows TEST26602 and the Next arrow;
it is not rendered Atlas. [Verified artifact and command evidence](evidence/m3-m4-diagnostics-40118399219.json)
retains the exact frame identities, timestamps and logged stage.

The driver now recognizes a selected existing character from the original
stage log and clicks the established Next layout immediately. A later stage,
pending error/alert or fatal rejects this shortcut. OCR results are reused for
an unchanged image. Neither path establishes Atlas success: all database,
rendered-frame, error and Wine checks remain required. Two local tests cover
the stage/dialog cases and OCR invalidation; the full 83-test suite passes.

[Replay 40118399218](https://github.com/Russianranger/coh-android/actions/runs/40118399218)
fails ARM64 on 16 dispatch errors and i686 on exit -9. The i686 observation
records SIGKILL at 310.978 seconds against a 600-second host timeout, no host
kill flag, and unchanged zero cgroup OOM counters. This does not establish the
kill's source. The receiver adds cleanup-begin and ExitProcess(2)-begin trace
witnesses to localize another occurrence; expected exit 2 is unchanged.

[M4 run 40118768539](https://github.com/Russianranger/coh-android/actions/runs/40118768539/job/120947602089)
reproduces the bad power key 0x10000000000. Its recorded caller 0x140074774 is
inside powerCust_FindPowerCustomization, immediately after __chkstk in the
exact Release executable: the inlined large trace buffer caused the compiler
to capture LR after its stack probe. Patch 0070 moves formatting/tracing to a
noinline helper. Local ARM64 O2 disassembly has no stack probe in the lookup
function and preserves incoming LR; full ARM64 OptDebug linking and both
changed i686 units pass. The new runtime caller and pointer producer remain
unproved. No pointer guard or game-logic repair is included.

The 8-file dependency proposal is still unstaged, the conditional texture
exception is OFF, and both milestones remain incomplete. A new CI result is
required for these implementation changes; local builds are not runtime proof.

## Review 5639193819 follow-up

Source `f0d78fd78e96643da50d90ddb5549110f73bb506` is tested by
[build/Atlas 40118399219](https://github.com/Russianranger/coh-android/actions/runs/40118399219)
and [replay 40118399218](https://github.com/Russianranger/coh-android/actions/runs/40118399218).
Release and libraries jobs pass; replay and Atlas fail as recorded above.
The following current-run fixture adds no validator behavior.

[Review](https://github.com/Russianranger/coh-android/pull/6#pullrequestreview-5639193819)
and [conditional exception decision](https://github.com/Russianranger/coh-android/pull/6#issuecomment-6387467359).
No texture exception is enabled. The required completeness and six-run proof
are not established. No additional assets have been fetched or staged.

[Replay 40113107670](https://github.com/Russianranger/coh-android/actions/runs/40113107670)
fails on 16 errors on both targets. The exact occurrence list, dispatch index,
thread ID, trace hash and artifact identities are in
[evidence](evidence/m3-dispatch-errors-40113107670.json), produced with
`python3 armport/scripts/itemize_dispatch_errors.py --arm64 <ARM64>/id1-a/zone-trace.jsonl --i686 <i686>/id1-a/zone-trace.jsonl --output <evidence>`.
Both available id1-a traces match literal texts, counts and indices; both have
thread ID 372. The validator stops after id1-a failure, so id1-b/id31 are not
available and six-way equivalence must not be inferred.

| Literal error text | dispatch 0 | dispatch 1 |
|---|---:|---:|
| CUSTOM TEXTURE ERROR: HUGE wants nonexistent texture X_Enforcer_Glove_01_Mask as texture 1 on bone LARMR. | 2 | 2 |
| CUSTOM TEXTURE ERROR: HUGE wants nonexistent texture X_Enforcer_Glove_01_Mask as texture 1 on bone LARML. | 2 | 2 |
| CUSTOM TEXTURE ERROR: HUGE wants nonexistent texture X_Gear_Pads as texture 1 on bone SPADR. | 2 | 2 |
| CUSTOM TEXTURE ERROR: FEM wants nonexistent texture HIPS_miniskirt_1 as texture 2 on bone HIPS. | 0 | 1 |
| CUSTOM TEXTURE ERROR: FEM wants nonexistent texture X_ImperialDefense_Belt_01 as texture 1 on bone BELT. | 0 | 1 |
| mission.c: Room -1 marker isn't in a room | 0 | 2 |

The committed client recipe `upstream/i24/tools/fetch_data.ps1` and
`assets/catalog.json` agree on 72 archives. The 57-name scan omits 15 sound
archives (listed in the evidence). Their metadata identities already exist
in `assets/zones-audio-metadata.json`, but the ArmPort scan did not inspect
those file tables. Archive names alone do not establish texture absence.

More significantly, all three failing X_* names have original composite
texture declarations. The evidence identifies their exact source blocks and
leaf paths: eight referenced textures exist in reviewed visual/zone manifests
but are absent from the current staged manifests. This is a dependency lead,
not proof of a fix; no expanded dependency staging is authorized by the
14-name fetch decision. The exact proposal (8 files / 658,461 bytes) is in
[m3-proposed-composite-dependencies.json](evidence/m3-proposed-composite-dependencies.json),
including per-file and source archive pins. It has not been staged.
Missing literal composite filenames do not by
themselves prove erroneous original data. HIPS names also pass through the
original gender_prefix_fixup lookup; no guessed substitution is made.

The retained Thor archives COH-NativeCombined-1792606619522.zip and
COH-ObservedScene-1792606604967.zip match the published SHA-256 values. Their
JSON members contain no identical literal texts and neither ZIP has a
standalone client log. This cannot prove the original client was error-free.

The exact first 28 Wine lines from Atlas run 40105902326 artifact 12566815878
(SHA-256 335a3ed556eccbee69d3b4ea1b967b5a931a50d2a4da5fdd7def6cb231beb7f1)
are retained as a fixture. The real dispatch/unwind/restore sequence passes
the startup matcher and fails when moved after a test boundary. That historical
run predates 0067; its synthetic test boundary is not runtime qualification.
Server-run 120931544128 has now finished: [run 40113107671](https://github.com/Russianranger/coh-android/actions/runs/40113107671)
fails. Its complete Wine output is retained byte-for-byte as
`tests/fixtures/atlas-wine-40113107671.txt`; [artifact and validator evidence](evidence/m3-atlas-wine-40113107671.json)
pins the download. The real dispatch/unwind/restore occur at lines 1/14/28,
before the actual shared-stream map boundary at 45. The validator reports
one allowed startup RPC, then correctly rejects the access violation at 46
and unhandled page fault at 63 (read 0x88, PC 0x1400a56d4). Its result matches
the retained CI wine-errors.json. The complete-log regression must fail, while
the prefix through its real boundary passes and moving the RPC after it fails.
The isolated trace ends with a NULL-def root tracker id=8, group_id=0,
count=10 and no parent; its source definition is not yet identified. The
retained screenshot is black, not a rendered Atlas frame. No NULL bypass.

M4 diagnostic [40118768539](https://github.com/Russianranger/coh-android/actions/runs/40118768539)
runs commit aa9cdcaa91334ab460e8bd6bb1918bf0688e2090 with the Release client
from 40118399219 and existing data 40100355259. It enables only the requested
power lookup caller/input diagnostic; it fails as recorded above.

L1: successful uncached range staging now reports each response's actual
Content-Range, status and received bytes; cache verification reports no new
transfers. L2: the trace comment explicitly says every map.start emits a marker.

0068 logs caller address, incoming power pointer and list address at the
original powerCust_FindPowerCustomization entry, only with ARMPORT_POWER_TRACE.
It never dereferences or repairs the suspect pointer. 0069 logs the original
mission-room group, property and failed tray-lookup coordinates; the original
error and RoomAdd call remain unchanged. These diagnostics investigate the
M4 bad key and two replay mission-room errors without granting an exception.

Local validation: [command evidence](evidence/review-5639193819-local.json).
80 host tests and 23 M4 client tests pass. Full ARM64 OptDebug Game links;
both changed translation units compile with the i686 compiler using the
recorded adjusted build commands. That is not a full i686 link or runtime pass.

## Review 5638956748 and approved follow-up (2026-10-24)

Source/harness commit `07c536d7fe5d7748ced9e03845c53b0b3cf907d4` runs
[build/Atlas 40113107671](https://github.com/Russianranger/coh-android/actions/runs/40113107671)
and [replay 40113107670](https://github.com/Russianranger/coh-android/actions/runs/40113107670).
The PR integration adds documentation/evidence only. Both asset jobs pass;
build jobs 120928759073 (OptDebug), 120928759106 (Release) and 120928759247
(libraries) pass. Replay fails on 16 dispatch errors; Atlas fails with a
NULL-def access violation. See the newer evidence above.

The [review](https://github.com/Russianranger/coh-android/pull/6#pullrequestreview-5638956748)
verified the 166-file selection, trace IDs, final drain and NULL diagnostic.
The [user decision](https://github.com/Russianranger/coh-android/pull/6#issuecomment-6386664502)
approves the 14 exact-name PIGG fetch and handled startup RPC 6ba allowance.
It supersedes the two pending-decision statements in the historical section.

`discover_approved_ranges.py` scans the 57 previously frozen metadata prefixes
and rejects ambiguous exact matches. It found all seven geometry paths and
`chest_stripe_1`: **8 files / 2,523,936 bytes**, ZIP SHA-256
`ce591c96db8ff48e64e1ccf7b3be9a9d613859ec1f6a536f8aa20fc21f5a06ec`.
A second discovery reproduced every file and archive pin. Selected transfers
require HTTP 206, exact range/length/URL and frozen ETag/Last-Modified; payloads
pass stored/decoded SHA-256, zlib bounds, PIGG table MD5 and cached headers.
The committed manifest records every range and all unresolved names:
`face_skin_head_09`, `hips_miniskirt_1`, `hips_skin_tights`,
`x_enforcer_glove_01_mask`, `x_gear_pads`, `x_imperialdefense_belt_01`.
No similar filename or composite dependency is substituted or fetched.
Both workflows verify this separate layer on every cache/artifact retrieval
and apply `--strict-data` after all preceding layers. Whole PIGGs are neither
downloaded nor claimed SHA-256 verified. The layer artifact lasts 90 days.

M1: before `replay.map.end`, the driver now calls the original geometry and
texture completion functions inside required map-drain markers, keeping
background static-map errors before dispatch 0. The final drain remains.
Both texture drains invoke original texCheckThreadLoader/loadUpdate, including
GL uploads under Xvfb; README lists these extra driver steps. L1: only the
build workflow saves the shared reviewed-dispatch cache; replay restores it.

Atlas-only allowance: patch 0067 writes every map boundary directly into
the same append-only file as Wine's +seh trace, before the isolated map.start.
Cross-file line numbers or clocks are not compared. A 6ba dispatch is counted
only after matching same-thread unwind and handler-target restoration, all
before that boundary. Missing/malformed boundaries, pending/nested exceptions,
late 6ba, every other code, page faults, unhandled exceptions and :err:seh:
fail. The phased-errors notice includes the count even when another failure
rejects the run. Replay retains its unmodified strict no-SEH checker.
A real Wine logger control passes shared-file append ordering in libraries
job 120928759247, which also passes 78 tests. Tests reject identical 6ba after
map.start and incomplete or
wrong-thread restoration. No game error, assertion or modal rule is weakened.

[Replay 40111054487](https://github.com/Russianranger/coh-android/actions/runs/40111054487),
ARM64 job 120923329915 at 7a91b34d, fails with return -9 instead of required 2.
Artifact 12566549630 verifies SHA-256
`659d0c158ca31d20145fa0b8886584c2b380d1c983d5547764d8435ccf5599a3`;
it contains the 117-dispatch result and final drain end. The termination cause
is unproved. The follow-up records bounded process memory samples, cgroup
memory events and whether the host timeout killed the process, and retains
game-error inventories on abnormal exit. It still rejects every return but 2.
Shared cgroup counters alone cannot identify an OOM victim. Do not infer a
replay pass from a terminal row or change exit acceptance to accommodate -9.

[Local command evidence](evidence/review-5638956748-local.json): 78 tests pass;
ARM64 and i686 OptDebug links pass sequentially with two compiler processes;
range discovery/staging pass, YAML parses, and upstream/ is unchanged.
M3 remains incomplete (six unresolved names, accepted replay, full state and
rendered Atlas outstanding).

[M4 diagnostic 40110421624](https://github.com/Russianranger/coh-android/actions/runs/40110421624/job/120922819992)
reproduces the power-customization fault. The verified artifact and exact
executable disassembly are recorded in
[register evidence](evidence/m4-power-fault-40110421624.json). The instruction
at 0x14007457c reads `[x8+0x10]`, with x8=0x10000000000 loaded from the search
key, whereas the candidate's power pointer is x9=0x1e236670. This establishes
which operand is bad, not where that key originated. Trace the original game
caller and pointer producer next; no NULL/range bypass is justified.

## Review 5638821870: corrected coverage and loader evidence

Code `7a91b34d956a115940cd4e9c5a58b50415110a71` runs
[build/Atlas 40111054496](https://github.com/Russianranger/coh-android/actions/runs/40111054496)
and [replay 40111054487](https://github.com/Russianranger/coh-android/actions/runs/40111054487).
The PR integration adds only these CI links over that code; execution is pending.

Claude's [review](https://github.com/Russianranger/coh-android/pull/6#pullrequestreview-5638821870)
confirms the accepted phase rule implementation and 0064's VBO correction;
it does not approve a milestone or merge.

Run [40105902494](https://github.com/Russianranger/coh-android/actions/runs/40105902494)
fails on both targets with 541 dispatch errors: 179 geometry/model reports,
360 custom-texture reports and two mission-room reports. All 117 pairs exist.
Run [40106727443](https://github.com/Russianranger/coh-android/actions/runs/40106727443)
repeats the failure. Comparison job 120915264128 has 133,392 shared literal
texts, no architecture-only texts and no count differences. Its downloaded
artifact 12565955691 matches SHA-256
`1def01e816b3ed6bdac9cb9ab937a6586aba61aba50e0c5f557330a58ef16310`.
All 45 geometry paths and 135 texture names in the retained dispatch evidence
are absent from both staged runtimes. i686 is no longer pending.

The previous manifest scan was wrong: it did not decode gzip+base64 manifests.
`reviewed_asset_coverage.py` verifies both compressed and decoded identities,
then resolves exact geometry paths and texture candidates. Against these same
missing files, its retained `evidence/m3-reviewed-file-selection.json` selects:

| Reviewed archive | Files selected | Bytes |
|---|---:|---:|
| client-visual-assets, 0.13.10 | 142 | 15,334,280 |
| character-avatar-defaults | 11 | 1,882,288 |
| zones-world-supplement | 13 | 776,315 |

Command: `python3 armport/scripts/reviewed_asset_coverage.py --evidence
armport/evidence/m3-dispatch-errors-40105902494.json --output
armport/evidence/m3-reviewed-file-selection.json`. It reports zero ambiguous
candidates and **seven uncovered geometry files plus seven texture names**.
The earlier 37/119 figures are superseded. Every selected texture resolves to
one exact path and hash across reviewed sources; ambiguous stems fail staging.

CI retrieves the existing visual artifact from 37249488856 and zone resource
artifact from 38112251836. Archive bytes/SHA-256, complete inventories and each
selected file are verified before staging. The 166-file/17,992,883-byte result
is checked again after retrieval and merged with strict checks against all
earlier data layers. The selected archive is retained for 90 days. No original
pigg fetch is made. Local staging verified the 153 visual/default files;
zone donor execution and the new replay are pending CI.

Patch 0065 adds a separate numeric thread ID to isolated records; literal error
text and counts remain unchanged. After dispatch 116, the driver runs the
original geometry and texture completion functions inside a mandatory paired
drain window. Errors between dispatches also count as dispatch errors, so late
APCs cannot escape simply by falling between markers. This extra driver step
is not a captured packet or a change to original receive logic. Patch 0066
logs a NULL grid tracker, its ID/entries and its parent's group name if available;
the original assertion/fault stays intact. No NULL bypass is added.

Local validation: `python3 -m unittest discover -s armport/tests -p 'test_*.py'`
passes 66 tests, including malformed drain markers, delayed errors, missing
thread IDs, compressed-manifest corruption and conflicting file pins. Both
ARM64 and i686 OptDebug Game links pass with `CMAKE_BUILD_PARALLEL_LEVEL=2`
(`review-round7-arm-build.log`, `review-round7-i686-build.log`). YAML parsing and
`git diff --check` pass. Runtime replay/Atlas evidence is still required.

Two explicit decisions remain: fetching the 14 uncovered files from original
pigg archives, and allowing only handled startup RPC code 6ba before map.start.
Neither is implemented or assumed approved. M3 still lacks full state coverage,
accepted replay and a rendered/connected Atlas screenshot.

M4 run [40106299491](https://github.com/Russianranger/coh-android/actions/runs/40106299491)
passes guest boot but fails creation with PC 0x14007457c reading
0x0000010000000010. Exact executable hash
`0e82dd6656a91e0e09eadb2a685de9c1dfb59e7573f22f6fa6d04e9c4dcf0844`
symbolizes to searchPowerCustomizations, power_customization.c:159 (invalid
search key). M4 diagnostic head b9cf89cb enables Wine SEH registers/caller
logging in [40110421624](https://github.com/Russianranger/coh-android/actions/runs/40110421624).
The cause is not yet established; all 23 M4 client host tests pass. Neither
milestone is complete and no APK signing/Thor test is requested.

## Review 5638651994 and the accepted error split

The [user decision 6385679120](https://github.com/Russianranger/coh-android/pull/6#issuecomment-6385679120)
on 2026-10-24 supersedes the earlier process-wide zero-game-error rule below.
All 117 dispatch windows must have zero errors; indexed begin/end records are
written in the isolated trace around original receive, ACK and snapshot work.
Missing, nested, unclosed or misindexed windows fail. Game-run Wine exceptions,
stdio assertions, fatals and log-write failures still fail. Error/fatal marker
counts must match between stdio and the isolated trace, including partial loss.
All six startup/load error inventories must match literally, with counts, across
ARM64/i686, repeats and synthetic IDs. No error normalization is accepted.
Atlas inventories startup/load and rejects post-load errors, incomplete evidence,
Wine exceptions and blocking dialogs; no error dialog is auto-acknowledged.

Run [40100355275](https://github.com/Russianranger/coh-android/actions/runs/40100355275)
at efc716bb still fails the old process-wide rule on both targets. Diagnostic job
120896348621 reports 183,269 occurrences per target, 133,392 shared literal keys,
zero architecture-only keys and 45 shared absent geometry paths. This confirms
patch 0062's deterministic spellings; it is not a replay/milestone pass.
The same counts were recorded in run 40099922039 at 023fd0dd.

Classification of that retained ARM64 inventory with `client_errors.error_class`
(command output, 2026-10-24):

| CI data/environment gap class | Occurrences |
|---|---:|
| Deleted symbolic group reference | 22,290 |
| Missing root geometry/model | 9,887 |
| Geometry file or model | 179 |
| Custom costume texture | 80,023 |
| Player costume texture | 65,317 |
| Texture trick | 5,156 |
| Material texture | 412 |
| DirectSound unavailable | 1 |
| Loading-screen match | 1 |
| Parser input | 1 |
| Mission room marker | 2 |

The new diagnostic resolves named textures case-insensitively under the actual
staged texture_library, recording paths, sizes and hashes. It separately retains
symbolic group references and phase/class counts. Only a shared error's file
absent from both actual runtimes is a missing-file candidate; a missing model in
an existing geometry file is not. Group references alone do not establish file
absence. No new data is added. Existing startup evidence predates phase markers;
new CI is required for phase attribution and the full texture lookup.

Review nits: patch 0062 now explains the optional Appearance fields at the edit;
supplement artifact retention is restored for 90 days under the existing public
upload authorization; Atlas notices include trace_record_count.

### Runtime fixes and remaining crashes

Run [40100355259](https://github.com/Russianranger/coh-android/actions/runs/40100355259)
passes both builds, libraries and login boot, including original/patched grid
controls under Wine. However server-run 120893845364 still faults at
0x1400a4ff4, groupGridActivate (groupgrid.c:96), reading NULL+0x88.
Patch 0063 repairs genuine pointer loss but has not resolved this Atlas fault.
The remaining NULL definition/lifecycle cause must be investigated; no bypass
is added and no rendered Atlas is claimed.

M4 run [40098262167](https://github.com/Russianranger/coh-android/actions/runs/40098262167)
at ddceae53 passes startup but crashes during character creation. Exact client
SHA256 0392424f466ceb6cbcb31d6c40252eace3570319db071369711ef35b74a6a00f,
`llvm-symbolizer --obj=CityOfHeroes.exe 0x140231a94`: createVboDirect,
rt_model_cache.c:79:41. The producer stores a native pointer then overwrites
its upper four bytes with TexID at offset four; the consumer uses that same
four-byte header. Patch 0064 changes both offsets and allocation to sizeof(VBO*).
The original 32-bit layout stays four bytes. No rendering logic is replaced.

Local validation commands (2026-10-24):
- `python3 -m unittest discover -s armport/tests -p 'test_*.py'`: 63 tests OK
  (review-round6-tests.log); window/order/error/lost-record negatives and
  literal startup-inventory/count differences are covered.
- `ASAN_OPTIONS=detect_leaks=0 python3 armport/tests/vbo_header.py --source
  upstream/ouroboros --expect-full-width 0`: allocation=0, payload=0.
  Patched-source control with --expect-full-width 1: allocation=1, payload=1.
  Both exit 0. ASan/UBSan active; leak detection unavailable in the local tracer.
  CI additionally executes both controls under ARM64 Wine.
- Both OptDebug Game links: [103/103], exit 0, two compiler processes;
  review-round6-arm-build.log and review-round6-i686-build.log.
- M4 `python3 -m unittest discover -s armport/tests -p 'test_client*.py'`:
  23 tests OK (m4-round4-tests.log), including data byte/time metrics and bounded
  guest crash notices. Cleanup remains fail-closed. M4 must retry with 0064.

## Earlier review follow-up (5638301654; superseded where noted)

Claude verified the previous corrections at 045fe9aad, then requested full
unmixed errors, same-commit ARM64/i686 data-gap classification, and runtime
supplement collision checks. Code 0b42f7cf implements those corrections.
Run [40097455262](https://github.com/Russianranger/coh-android/actions/runs/40097455262)
fails strict replay on both targets: each has 183,269 complete game errors.
The diagnostic comparison job 120887913787 succeeds; it is not replay success.
It reports 132,393 shared literal keys, 1,020 ARM64-only spellings and 999
i686-only spellings. Both actual staged runtimes lack the same 45 named
geometry paths. No new costume assets have been added.

The downloaded comparison artifact 12561139952 matches API SHA256
8c971df69594458d9b18ce2b5e16685c8c47a84b1ba3d5d9c873bd0a519bcd77.
A local diagnostic that casefolds the full texts produces identical dictionaries:
133,341 keys, 183,269 occurrences, zero differing counts. Acceptance remains
literal and zero-error. Source inspection found an uninitialized optional
costumeFilePrefix in costumeVerifyTextures' dummy Appearance, used by
determineTextureNames to choose uppercase B versus the data's lowercase b.
Patch 0062 zero-initializes that structure, preserving the selected bodytype.
Both OptDebug links pass ([8/8]); run
[40099922039](https://github.com/Russianranger/coh-android/actions/runs/40099922039)
at 023fd0dd tests whether this explains the architecture-only spellings.
That result is still required; casefolding does not prove source correctness.

A local manifest scan finds five of the 45 geometry paths in the reviewed
character-avatar-defaults manifest and three in zones-world-supplement; 37
have no matching entry in assets/*manifest.json. The 45-path list is not a
complete inventory of every missing texture/model. Only shared errors and
actual absent files can justify additions, from already reviewed pinned
sources with per-file hashes. Any new data source needs the user's approval.

Patch 0061 adds the full JSONL trace on a dedicated locked append handle and
corrects i686 stdio routing. Strict replay rejects missing/malformed trace,
error/fatal records, stdio assertions, and log-write failures. The independent
error-comparison job checks source identity and actual-runtime file hashes.
The earlier i686 run 40094942235 lacked client-stdio.txt; the new run supplies
complete evidence on both targets. Both earlier real handled-SEH controls pass.
No decoder, dialog-acknowledgement or zero-error rule is loosened.

The Atlas stage mechanically verifies all 2,877 retained hashes and sizes
against the repository's reviewed 2,904-file manifest. Runtime staging checks
case-insensitive collisions against every earlier layer, including shadowed
files; differing bytes fail before copying. The second public supplement
upload is removed: future runs use cache and the existing pinned donor.
Previously uploaded artifacts have not been deleted.

### Atlas crash and pointer correction

Run [40094942248](https://github.com/Russianranger/coh-android/actions/runs/40094942248)
at 7fb7c692 fails server-run 120877721069. The original client exits 5, with
an access violation reading 0x88 at 0x1400a4da4 after map.finish.begin.
The final screenshot is black and the database never confirms this client's
Atlas connection. QA-notice search/acknowledgement was not reached; the
previous modal is not established as this run's failure.

Evidence artifact 12562347411 matches API SHA256
8aa29fecadec100f6fdc6ade178f1925aa89320a4a68b3bd27591d010f8f6403.
The exact Release archive 12560726582 matches
e87a4c98b28fa0497607196da2c765566c50ca9b5817a845c520ebec87fbd9a7.
`llvm-symbolizer --obj=CityOfHeroes.exe 0x1400A4DA4` reports groupGridActivate,
groupgrid.c:96:14. Disassembly loads def from the retrieved tracker and faults
at def+0x88. Source inspection finds grid entries, insertion and collision
lookup narrowing pointers to U32, plus an int temporary in sphere lookup.
Patch 0063 preserves uintptr_t throughout storage, removal indices and both
lookup paths. Small numeric node IDs and the low-bit group tag are preserved.
It adds no NULL bypass or missing-geometry allowance.

`grid_pointers.py` runs the actual grid insertion/removal and both lookup
bodies with allocator/geometry adapters. Opaque addresses above 4 GB are never
dereferenced. Original source returns storage=0, sphere=0, collision=0,
distinct=0; patched source returns all four as 1. Two high addresses with
identical low bits must remain distinct. Both generated controls compile for
ARM64 Windows; the workflow also executes them under the pinned Wine.
Actual Atlas execution after this correction remains required.

Local validation on 2026-10-24:
- `python3 -m unittest discover -s armport/tests -v`: 57 tests, OK.
- `python3 armport/tests/grid_pointers.py --source ../patchwork-active/src
  --expect-full-width 1` and the original-source negative control: exit 0.
- Both OptDebug Game builds use CMAKE_BUILD_PARALLEL_LEVEL=2. Patch 0062
  links both targets; patch 0063 also links both targets ([99/99], exit 0).
- The standalone armport_zone_trace concurrent test links for ARM64. It checks
  64 complete 8,191-byte messages from four threads; Wine execution is required.
- `stage_atlas_supplement.py stage --source ../recovered-atlas --output
  ../reviewed-atlas-data`: 2,877 files / 309,655,940 bytes, matching reviewed
  manifest SHA256 204a7f0da20cdbbb4ea8b8e2d9e9b5ebccfaa10d5213fff03bbb85cc7f9e3c86.
- Workflow YAML parses; git diff --check passes; upstream/ has no changes.

M4 continues independently: run 40095316035 reaches the actual ARM64 client,
then faults at 0x140204184. The exact retained executable resolves that address
to texResetTrickBasedParametersComposite, tex.c:1081:61 (generic texture NULL).
Its log records failures opening reviewed textures. M4 branch ddceae53 makes
private regular copies instead of calling link() inside --link2symlink PRoot,
and captures client evidence from the ARM64 directory. The 22 app tests pass;
run 40098262167 must confirm the staging hypothesis. No M4 pass is claimed.

## Exit-test evidence

| Requirement | Evidence and current result |
|---|---|
| Scripted original-client login to Atlas | Run [39960894368](https://github.com/Russianranger/coh-android/actions/runs/39960894368), attempt 2: typed login, character selection, database loaded/connected on map 1, still connected after captures. Accepted in Claude review 5635319013. |
| Rendered Atlas screenshot | Not met. Run [40054327137](https://github.com/Russianranger/coh-android/actions/runs/40054327137), server-run 120756731269, ended with world_rendered=false and still_connected=false. Its artifact has the access-level QA notice trace and a modal on the loading screen. Run [40087788009](https://github.com/Russianranger/coh-android/actions/runs/40087788009) at 563e49ac also fails: world_rendered=false, zero QA-notice actions, 1,507 seconds loading. Its inspected screen remains white with a blank modal area; the pending exact notice is still in stdio. |
| All supplied packets through original receivers | Cursor/ACK stage passed in [40087788115](https://github.com/Russianranger/coh-android/actions/runs/40087788115), head 563e49ac: ARM64 job 120854188812, i686 job 120854188725. Each target executes ID1 twice and ID31 once; each execution reports 117 exact cursors, ACK IDs [1,2], and matching native INITIAL command boundaries. |
| Full deterministic state comparison | Not met. Patch 0059 and replay/state.c now emit explicitly partial snapshots. CI [40091320504](https://github.com/Russianranger/coh-android/actions/runs/40091320504), head 1e6952ed, fails in the first snapshot formatter after INITIAL cursor/ACK. The corrected formatter has passed both local links and four preprocessing controls; rerun [40092531364](https://github.com/Russianranger/coh-android/actions/runs/40092531364) at 0296f2fb writes 117 ARM64 snapshots but rejects the costume subset because the validator confused 60 allocated slots with 28 logical parts. The current correction compares num_parts; full state remains incomplete. Full entity/player/tail coverage is still incomplete. |
| Independent native INITIAL comparison | Command boundaries passed in 40087788115. Four additional recorded fields are checked by the new observer harness: selected entity index/type and costume bodytype/part count. That subset is not full native INITIAL equivalence; see replay/fixtures/native-initial-entity.json and replay/README.md. |
| Final milestone approval | Pending. Claude implementation review [5638301654](https://github.com/Russianranger/coh-android/pull/6#pullrequestreview-5638301654) verified prior fixes and requested the follow-up above. Its new corrections require execution and review; this is not milestone approval. |

## Earlier implementation changes

The last review identified a P2: accepting a plausible receiver transcript
without examining the game Wine log. The integrated check_wine_output now
rejects handled/unhandled exception dispatches, fatal Wine and loader reports;
bootstrap/registry logs are separate. Counterexample tests in
`test_receiver_evidence.py` supply complete transcripts plus fatal/handled-SEH
logs, missing logs and oversized evidence. The exact-head cursor run
40087788115 passes with this rejection enabled.

The first original replay failed because earlier handshake initialization
was missing, not because an alternative decoder was required. The driver
now installs the 35 original command-shortcut names in original shared-table
order and initializes the original static Atlas map list. Both prerequisites
are logged and documented in `replay/README.md`. Patch 0058 records original
command boundaries. Run 40087788115 establishes all 117 dispatches after
these changes; it does not establish complete state equivalence.

The Atlas harness recognizes only the exact traced access-level QA notice.
It requires one mapped client PID and one visible Program Error window for
that PID, records before/after captures, and attempts acknowledgement at most
three times. Unknown/fatal alerts are not acknowledged. The input operation
does not count as a rendered frame. Existing original load/READY markers,
client-cropped Atlas text, two nonblank/non-loading frames, database connection
and cleanup requirements remain in force. Human screenshot inspection is
still required. The tests are in `test_qa_notice.py` and `test_zone_frame.py`.

Patch 0059 was exported with `patchwork.py`. Its read-only observers retain
accepted wire quaternion components before normalization and expose actual
delete history in server-index order. `state.c` is inactive without replay
initialization. It writes bounded JSON and SHA-256 after each completed
receiver dispatch. Identity, raw network position/orientation, ordering IDs,
selected costume parts, selected character scalar/attribute fields and one
player lifecycle ID are included. Full power/inventory/player, team/task/UI,
dynamic-group and further costume fields remain missing. All completion flags
are false. See `replay/README.md` for coverage and explicit exclusions.

The comparison checks input/commit identity and snapshot hashes, then compares
same-ID repeats and ARM64/i686 bytes literally. Only ID1-versus-ID31 checks
canonicalize the five named fields agreed in reviews 5635783793/5638209554, only when equal
to that run's synthetic INITIAL ID; all other values stay literal. A mismatch
fails the partial stage and records field paths. A passing partial stage
cannot complete M3.

## Validation and limits

Commands executed on 2026-10-24 for the observer implementation:

- `python3 -m unittest discover -s armport/tests -v`: 41 tests, OK. Includes
  authenticated but changed final state, wrong commit, missing/tampered state,
  path substitution, native subset mismatch, Wine exceptions and frame checks.
- `CMAKE_BUILD_PARALLEL_LEVEL=2 cmake --build ../build-arm-new --target Game`
  and the same command for `../build-i686-new`: both exit 0; final output
  `[8/8] Linking CXX executable bin/CityOfHeroes.exe`. Both are OptDebug.
- PyYAML parsed armport-reference.yml; `git diff --check` passed. STATUS has
  40 lines. `git diff HEAD -- upstream/ native-android/ android/` is empty
  for this replay change. Source modifications are patchwork exports.

The i686 reference uses the same ArmPort patches and clang, with SSE2 math.
It isolates architecture/pointer-width differences, not shared source/compiler
mistakes. Both targets disable NOVODEX; i686 retains real CPUID while ARM64
reports no SSE. Reference-only patch 0054 removes three local SEH handlers;
any resulting fault fails the run, never establishes equivalent recovery.
See `notes/M3-REPLAY-PLAN.md` for the agreed scope and wire-value rules.

Earlier fixes and diagnostic evidence remain in `notes/64BIT-AUDIT.md`,
`notes/M3-LOAD-STALL.md` and `notes/WORKER-QUEUE.md`. In particular, run
40035482170 demonstrates the independently reproduced worker wake/publication
fix; it is not an Atlas rendering result. Run 40042636088 validates CRT trace
writes and the socketless sink, not world loading. No ACK/READY grammar or
original receive decoder was replaced.

The first observer execution exposed the original ARRAY_SIZE_CHECKED printf
macros on a heap-buffer offset (40091320504, quick_sprintf.c:101). The writer
now explicitly uses bounded CRT formatting. Actual ARM64/i686 preprocessing
and negative controls verify the correction; both updated links pass. See
replay/README.md for the artifact identity and exact command. Runtime
state comparison is still unqualified. The corrected code is tested by
40092531364 at 0296f2fb fails the native costume count check described above.

## Next exits

Inspect the current Atlas run and its actual image; fix any remaining load
failure. Complete and execute full deterministic state coverage, retaining
the agreed literal and sensitivity checks plus independent native evidence.
Then update this report, obtain Claude's milestone review and the user's merge
approval, and merge with a merge commit. M4 work is on armport/m4-runtime;
its startup/interactive results do not waive any M3 requirement.

## Review 5638209554 corrections and data evidence

- H1: sensitivity-only normalization now explicitly includes pkt_id_pos[]
  and pkt_id_qrot[]; same-ID/cross-architecture bytes remain exact.
- M1: receiver.c also unbinds CRT macros; actual preprocessing and negative
  controls cover both observer units on both architectures.
- M3: patch 0060 enables identical game-error tracing on i686; both targets
  require zero client.error/assert reports. Complete recorded multiline
  texts and counts go into client-errors.json, including Atlas artifacts.
- M4: per-run and partial comparison summaries emit Actions notices.
- L1/L2: retain pinned bins/Cg in a run-keyed cache and 90-day artifacts;
  add a real handled-SEH Wine control, separately logged from the game.

M2 investigation: parsing all 16,721 entries of
assets/reference-inputs-manifest.json with casefold searches finds zero
matches for tickertape_talos_island or arch_ent_wall_brick_01. In the verified
40054327137 artifact, client_errors.inventory reports 12,713 errors and
11,063 distinct recorded texts, including twice: `TexSwap Warning: was unable
to find source texture 'tickertape_TALOS_ISLAND' to swap (does not exist in
texture_library/)`. This is the source-texture warning in texCheckSwapList,
not a failed destination texFind call. It means no matching source was
swapped; the name comparison in texCheckForSceneSwaps is stricmp. The absent
case-insensitive manifest entry establishes a reviewed-bundle data gap; it
does not prove that adding this one asset will complete loading. The QA
notice/error pop-ups are specific to the fake-auth access-level-9 account.
No error dialog is automatically acknowledged.

Run 40092531364 artifact 12559387913 (SHA256
da15257d2fd11d850ffc08a888d532f27d7f336582c597c5361653f2632b70bf)
contains 184,514 game error records, 137,888 legacy inventory keys (not reliable distinct messages), in
id1-a/client-stdio.txt. `client_errors.inventory` collected mixed/truncated stdio text;
examples include missing Arch_Ent_Wall_Brick_01 and deleted geometry references.
The new strict validator will reject these, even with exact dispatch cursors.
The data errors must be resolved before state equivalence is accepted.

Local review validation, 2026-10-24: 46 host tests pass; ARM64 and i686
OptDebug Game links exit 0 with `[15/15] Linking CXX executable
bin/CityOfHeroes.exe`; current/negative preprocessing controls pass for
receiver.c and state.c on both targets. seh-control.c links for both targets.
Workflow YAML parses; git diff --check passes. Runtime controls are pending.
M4 branch 723bbc32 addresses the separate missing client_visual_assets import
from run 40092467628; 19 app tests pass. No M4 completion is claimed.

### Reviewed Atlas supplement and current execution

The missing texture is present in the already reviewed
assets/atlas-world-supplement-manifest.json: 22,316 bytes, SHA256
60e4fa246b6212ae882c44a0d3571bcb4ecc7d2c35f85f316fdad8a35f53b344.
The retained 0.10 APK (run 36920583713, artifact 11192425448) supplies the
original 2,877-file Atlas supplement. CI now verifies the exact APK and
embedded manifest/archive hashes, retains the archive, and adds those
original bytes to the client data for Atlas and both replay architectures.
It does not modify the server's existing data or acknowledge error dialogs.
The reviewed current 2,904-file Atlas manifest and base reference manifest
have zero overlapping paths (`casefold` missing-texture search and Python
manifest-set intersection, 2026-10-24). The 27 later material additions are
not silently substituted for the retained baseline. This is a data-gap
correction to test, not evidence that all game errors or loading are fixed.

Run 40087788009 artifact 12559808809 SHA256
68f239a459ff0cada2eafc49c375c831acce4e7ea3139a02791641768984612e
was downloaded and verified. Its final trace is the exact QA notice after
the missing source-texture warning; pending_qa_notice returns true locally,
but qa_notice_actions is empty. The next run records the exact-window search
result without widening its acceptance.

Run 40094248191 at 1e3df462 fails the newly expanded preprocessing check
before compilation because AutoGen/bones_h_ast.h has not been generated.
Commit 06296c38 moves that check after the build and before executable caching;
40094448205 tests it. Actual local incremental links and eight preprocessing
controls already passed. The supplemental data change has 50 passing host
tests, including byte identity, unexpected members, path links and refusal
to overwrite different data; production donor execution remains pending.
M4 correction 723bbc32 runs in 40094077884; app sources and guest boot pass,
interactive creation/save/reopen is still running.

### Review follow-up execution, 2026-10-24

Run 40094448205 ARM64 job 120873737155 passes the real handled-SEH rejection
control (`target=arm64, rejected=true` annotation at 12:40:27 UTC), then
fails closed on 184,514 game error reports as intended. This is a validator
control/data-error result, not state equivalence. Artifact 12560234319 SHA256
0689027af7bb9e780e2e71eef7c0aff97ddaa3b40277965cc01b957e9136ce30
retains all recorded errors; the i686 side is still running.

At code 7fb7c692, new runs 40094942235 (replay) and 40094942248 (Atlas/build)
are in progress. The latter's libraries, Release and OptDebug jobs pass.
Both asset jobs recover the reviewed supplement. Downloaded artifact
12560402926 matches API SHA256
1167a7d2a36adf1a264d6007ff2f7f1106bcfef15cd6e19aa88489b16e0a2308.
`python3 armport/scripts/stage_atlas_supplement.py stage --source
../recovered-atlas --output ../reviewed-atlas-data` then verifies and stages
2,877 files / 309,655,940 bytes locally. The missing texture is 22,316 bytes
and its SHA256 equals the reviewed 60e4fa24...f53b344 pin. No rendered-frame
or error-free replay result has yet been established with this data.

M4 run 40094077884 passes boot and proceeds beyond the visual-helper failure,
then fails importing native_monorail_contract during cache ancestry checking.
Branch commit 589a015bf86dada8d1f5673cd5ca53eed91b0478 adds the cache ancestry
helpers; 20 app tests pass, including unsupported-producer rejection.
40095316035 tests it; complete interactive qualification remains pending.

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

### Dynamic group and sky observation follow-up (2026-10-25 UTC)

Partial snapshots now retain ordered dynamic-group hp/repair fields and the
server sky indices/raw weight bits from original receive storage. They do
not hash bitfield layout, tracker pointers or render overrides. Both target
units compile sequentially; actual-writer sanitizer controls and 145 Python
tests pass. Evidence: evidence/m3-world-state-observations.json. Runtime
pending, schema still partial, no change to packet bytes or acceptance.

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
