# COH-ArmPort handoff to Claude

**Update 2026-10-26 (Claude lead): M3 is merged.** PR #6 merged into
`COH-ArmPort` as 3ac8eedc9 after Sol accepted it (5659701771) and the user
approved it. Its scope is reduced: the completeness flags stay false and the
textures are incomplete (see the M3-REPORT summary). The current work is M4 on
`armport/m4-runtime` (PR #7), which has COH-ArmPort merged in.

M4 checkpoint from 2026-10-25: run 40176336731 at 63f091de passes guest boot,
creation/save/restart/reopen and final host continuity (see M4-REPORT.md and
evidence/m4-continuity-40176336731.json). Sol re-review 5642680640 resolved
the explicit-Finish finding. M4 milestone review is still pending; the Android
surface and Thor execution are unvalidated. M4 work notes are in
armport/notes/M4-RUNTIME.md. Building or signing an APK needs the user's
approval first.

The sections below describe the M3 handoff, which is now complete.


Updated 2026-10-26. **The user has handed development leadership back to Claude.**
Astra is stopping active development. Sol remains the independent reviewer unless
the user changes that assignment. All scheduled ChatGPT tasks were disabled at
user request; do not recreate or resume them without a new request.

This document supersedes the previous role assignments and stale status entries.
The full development history is preserved in
[the previous handoff at dd0f0ea4](https://github.com/Russianranger/coh-android/blob/dd0f0ea454033abf21b84d7e1ad56c0267d927aa/armport/HANDOFF.md),
Git history, `M3-REPORT.md`, and `replay/README.md`. Those reports are chronological
and contain historical “pending” statements; use exact source/run identities.

## Start here

1. Read this file, root `PORT-PLAN.md` and `STATUS.md`, then
   `notes/M3-REPLAY-PLAN.md` and the latest PR #6 review.
2. Check current branches, processes, CI and reviews before editing. Do not
   duplicate another active development session or cancel a useful CI run.
3. Prioritize **M3 completion**, not another round of unrelated M4/M5 work.
4. Preserve and inspect Atlas run **40337294759**. It was still running at
   handoff; builds had passed, but no final rendering result was available.
5. Recover the unapplied NPC/Architect WIP below, review it and decide whether
   to integrate it. It is not part of the executable source at this handoff.

## Goal and constraints

Run the original City of Heroes Game/Common/UtilitiesLib source as an ARM64
Windows client under the Android app's ARM64 Wine 10 on the AYN Thor. Local
servers retain their existing x86 Wine/FEX runtime. M0–M2 are merged; M3 remains
incomplete. M4 has runner continuity evidence, not Android-surface qualification.
M5 has not been qualified and no substantial Thor test is ready.

- Never edit `upstream/`. Native source patches must use
  `armport/scripts/patchwork.py` in an external worktree and be exported into
  `armport/patches/`. There are currently 105 source patches.
- Preserve original game logic; clearly document necessary bounds/64-bit fixes.
- At most two compiler processes. ARM64 and i686 compilation stays sequential.
  Do not start competing native builds while another session is compiling.
- No new gate/lease/receipt systems. Keep root `STATUS.md` at most 40 lines.
- Do not change `main`, `native-android`, protected branches, pushed history,
  secrets/signing, APK publication or releases under this handoff.
- No merge is authorized here. Preserve explicit review and user merge gates.
- No agents or schedules should be started by this handoff. Work directly.
- Evidence must name commands, exact commits and CI runs. A green build or
  partial replay is not milestone completion; implementation approval is not
  milestone or merge approval.

## Branches and review boundary

| Branch / PR | Head before this documentation-only handoff | Meaning |
|---|---|---|
| `COH-ArmPort` | `9e76c4d48d1d5f69c1fa880551ed5e3690f09180` | Integration branch; unchanged |
| `armport/m3-atlas`, [PR #6](https://github.com/Russianranger/coh-android/pull/6) | `dd0f0ea454033abf21b84d7e1ad56c0267d927aa` | Current M3 code, draft and unmerged |
| `armport-work/power-receive-observations` | `dd0f0ea454033abf21b84d7e1ad56c0267d927aa` | Parallel preparation branch; no active CI trigger |
| `armport/replay-retained-state` | `e6d39d7a56f52ce2ad25e43ed7117389d0e8a0cb` | Last qualified partial replay |
| `armport/m4-runtime`, [PR #7](https://github.com/Russianranger/coh-android/pull/7) | `08e9a9773cbd36151a773faab404462655c5ccce` | Draft; guest continuity only |

The handoff commit advances only `armport/m3-atlas` with documentation and inert
WIP recovery files, using `[skip ci]` to preserve the running Atlas experiment.
Its native/runtime source remains dd0f0ea4. The work branch remains at dd0f0ea4.

Sol's latest [review 5651480055](https://github.com/Russianranger/coh-android/pull/6#pullrequestreview-5651480055)
approves implementation through **e6d39d7a** only. It covers patches 0103–0105
and the mission/keydoor snapshot writer. It does not grant milestone/merge or
six-texture selection approval. Later host report 189ef449, evidence24fb6e3e,
and the post-verdict Map diagnostic dd0f0ea4 still need review.

## CI and artifact evidence

| Run | Observed result / scope |
|---|---|
| [40321211800](https://github.com/Russianranger/coh-android/actions/runs/40321211800), e6d39d7a | Both native targets and both comparisons pass. Job121584110467 records partial-state and outside-error equality, but schema/state/M3 completion remain false. Qualifies mission/keydoor snapshots only within that partial scope. |
| [40314007807](https://github.com/Russianranger/coh-android/actions/runs/40314007807), e6d39d7a | Failed Atlas screenshot acceptance. Connection/load/READY pass; world_rendered and map_name_visible are false. |
| [40337294759](https://github.com/Russianranger/coh-android/actions/runs/40337294759), dd0f0ea4 | Running at handoff. libraries, Release, OptDebug, assets, client-run1 and Cg had passed. client-run121629180185 and server-run121629180393 were pending/in progress. Do not infer final pass. |
| [40176336731](https://github.com/Russianranger/coh-android/actions/runs/40176336731) | Reviewed M4 guest create/save/restart/reopen and host continuity pass. Not Android-surface/device/M4/M5 completion. |

Atlas40314007807 artifact12650754712 was downloaded and verified:
SHA-256 `1d9b886f124d01dd7ae3b0a521a0239f44986555e1880626161650361ee4c05a`.
Eight world.ui samples match model/draw frame and thread IDs: compass mode2
(DISPLAYING), map mode4(DOCKED), default destination type0, no name/map text.
The original default compass does not guarantee a zone label. That is not proof
of font failure or of accepted rendering. The inspected final frame still shows
incomplete purple/blue materials and white UI placeholders. The complete literal
error inventory is unchanged from40283068606:5659 occurrences/5656 unique.
See `evidence/m3-atlas-ui-outcome-40314007807.json` for hashes and commands.

The dd0f0ea4 diagnostic runs **after** original frames and world_rendered are
fixed. It attempts one unique OCR Map label in the owned navigation strip,
checks ownership/geometry and dialog history, and records separate before/after
frames or a blocked/error outcome. It does not dismiss helper dialogs or send
console commands. A click is not proof that the map opened; an overlay is not
accepted 3D terrain. All202 Python host tests passed, including six diagnostic
controls: `evidence/m3-map-ui-diagnostic-controls.json`.

## What still completes M3

### 1. Accepted Atlas rendering

Inspect run40337294759's original `atlas-later` image, `login-driver.json`,
complete client-errors inventory, and separate `map-ui-before`/`map-ui-after`
images. Preserve its actual result. Use `scripts/world_ui_report.py` on its
isolated trace; do not turn the default compass source observation or a readable
map overlay into an accepted terrain screenshot. Diagnose actual material/UI
problems and reconcile any proposed acceptance change through review/user gates.

Six plaza/statue files remain **proposal-only** in
`evidence/m3-proposed-plaza-statue-materials.json` (2,306,838 bytes):
AP_Asphalt_01_NS, Plaza_Brick_Floor_02_NS, deco_building_03_concrete_01_n,
Male_Statue_Atlas_N, Statue_Globe_02_MK, Statue_Stone_Detail.tga.
Use the manifest for exact paths/pins, not these shortened names. Existing
[approval6389265419](https://github.com/Russianranger/coh-android/pull/6#issuecomment-6389265419)
authorizes only the earlier eight composite files. It explicitly excludes
other leaves/new fetches; Sol's latest review does not expand this authority.
**Obtain explicit approval for this exact six-file selection before staging or
fetching it.** Do not broaden game-error exceptions.

### 2. Complete retained-state replay coverage and qualification

The old “missing initial-replay.bin/post-ready-replay.bin and no agreement”
baseline is obsolete. The exact two logical files are recovered as gzip fixtures;
Claude agreed the method in review5635319013. Read `notes/M3-REPLAY-PLAN.md`.
The native-android post-READY capture remains opaque source evidence, not a
historical decoded oracle. The i686 reference shares ArmPort patches/compiler
and has documented limits; the separate native INITIAL subset remains required.

Preserve all117 dispatches, exact cursors, ACK checks, frozen bytes, unknown-command
rejection, assertions/SEH rejection, six-run literal outside-error inventories,
same-ID repeats/architecture comparisons and narrowly enumerated ID1/31 rules.
There is exactly one authorized original-data texture occurrence, not a general
ignore list; see `replay/fixtures/original-data-errors.json` and its evidence.

`replay/state.c` and `compare_state.py` still deliberately report partial scope.
Many entity/player/inventory/costume/story/contact/task/world/options/turnstile
fields and raw received clock histories are covered, but no full coverage audit
has been completed. Do not flip completion flags because the suite is green.
Next build an explicit receiver-destination coverage/exclusion inventory for the
actual initial/entity/tail paths, then close concrete gaps. Known follow-ups:

- Review/integrate the custom NPC/Architect WIP below; mission-review widget
  state and cached-costume lifecycle are not covered by it.
- Audit selected task/waypoint lifecycle, remaining tray kinds and other retained
  state excluded in `replay/README.md`; distinguish received state from local
  caches, clocks, interpolation and pointer identity.
- Trace `cmdReceiveServerCommands` and original command-table destinations rather
  than assuming SERVER_GAME_CMDS dispatch counts prove all values are captured.
  This last audit was identified but not implemented.
- Qualify the combined candidate on sequential ARM64/i686 with all six runs and
  exact comparisons; obtain review of the coverage and final M3 evidence report.

### 3. Review and close only after both independent criteria pass

Update M3-REPORT with exact tested commits/results and all remaining exclusions.
Get implementation and milestone review, then the required user merge approval.
Keep PR #6 draft/unmerged until those conditions are met. M4/M5 are later work;
no physical Thor request is appropriate on current evidence.

## Recoverable unfinished work — unapplied, not qualified

Immediately before the user stopped development, Astra prepared:
`handoff/2026-10-26-npc-architect-wip.patch` and
`handoff/2026-10-26-npc-architect-wip-evidence.json`.
These are **inert recovery artifacts**, not patches in `armport/patches/` and
not applied to this handoff branch. They preserve edits to:

- `armport/replay/state.c`: ordered/null custom NPC regions/colors/name, plus
  retained Architect flags/contact IDs/name/full costume/custom NPC costume.
  Stale retained fields remain visible when onArchitect is cleared. No ID
  normalization, decoder edits or completion-flag changes.
- `armport/tests/receiver_npc_architect_state.py`:19 actual-receiver/writer host
  sanitizer cases, including original clear/retain/replace behavior, bounds,
  literal high-bit values, array order/nulls and nonmutation.
- `.github/workflows/armport-reference.yml`: run the new control on fresh replay
  executable builds, using existing `steps.replay-exe-cache` condition.

Local validation:19 new sanitizer cases pass; existing costume controls and15
TaskForce parameter cases plus original signed-shift negative control pass;
all202 Python tests pass. `state.c` compiled ARM64 then i686 successfully, one
compiler at a time. Exact compiler commands/output and post-apply SHA256 values
are in the evidence JSON. Both original receiver bodies were byte-compared to
patchwork base and are unchanged. Native patchwork is clean at0105.

Limits: host packet/earray/allocation/string-interning/mission-review and full
costume decoder adapters are substitutes; the full-costume writer has a separate
regression suite. Local LeakSanitizer was disabled for environment restrictions;
CI defaults remain unchanged. No live six-run replay or Sol review covers this WIP.

From a clean checkout of dd0f0ea4 (or this documentation-only descendant):

```sh
git apply --check armport/handoff/2026-10-26-npc-architect-wip.patch
git apply armport/handoff/2026-10-26-npc-architect-wip.patch
python3 armport/tests/receiver_npc_architect_state.py --source /path/to/prepared/source
python3 -m unittest discover -s armport/tests -p 'test_*.py'
```

The patch dry-run passed against copies of the base files. Apply once, compare
post-apply hashes to evidence, and review before committing. If files changed,
resolve manually; do not overwrite another developer's edits. Source changes to
upstream game files, if subsequently necessary, still require patchwork.py.

## Environment recovery (optional, never rely on these surviving)

Old scratch checkout: `/workspace/scratch/6e8acd6310fe/coh-active` (no `.git`).
It still contains the unapplied-to-GitHub WIP edits; do not apply the patch twice
there. Use a fresh Git checkout for Claude's work. External prepared source:
`/tmp/coh-world-patchwork/src`, clean patchwork HEAD
`e057696fcc6acc4dfc6dd03d38581a1cdfd74081` (0105). Toolchain:
`/tmp/coh-toolchain/bin`; compile databases under `/tmp/coh-world-build-arm64`
and `/tmp/coh-world-build-i686`. No local compiler was active at handoff.
Verified Atlas artifact extracts may remain under `/tmp/atlas-40314007807` and
`/tmp/atlas-40283068606`; prefer committed hashes and re-fetch if missing.
