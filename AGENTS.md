# COH-ArmPort working guidance

## Scope and current state

- COH-ArmPort runs the original Game/Common/UtilitiesLib client as an ARM64
  Windows program in the Android app's Wine runtime on the AYN Thor. Preserve
  the original game logic and the currently qualified runtime/package contracts.
- At the start of a task, establish the assigned branch, actual HEAD, existing
  changes, and relevant running CI. Read root `STATUS.md` and the current task
  note or handoff it identifies. Check relevant current PR reviews AND comments.
- Follow the latest explicit user assignment for lead/reviewer roles. Older
  handoffs retain historical role, milestone, and pending-run statements; use
  current source and evidence to establish present status. Preserve applicable
  constraints rather than treating an old status statement as a new assignment.
- Keep one integration owner. Coordinate independent work and avoid competing
  writes to the patch series or duplicate builds. Preserve existing worktrees.

## Source changes

- Keep `upstream/` byte-identical to its lock. Native edits use
  `armport/scripts/patchwork.py` in an external source tree, then export into
  `armport/patches/`. Use `prepare.py` for a fresh validation tree when needed;
  do not erase a useful tree with `--force`.
- Consult `armport/notes/64BIT-AUDIT.md` for pointer, ABI, serialization, and
  file-layout changes. Read detailed experiment notes when the task needs them.
- Keep changes scoped. Document why any original behavior must change.

## Cloud setup and local validation

- Setup instructions: `armport/CLOUD-DEVELOPMENT.md`.
- Read-only preflight: `bash scripts/codex/doctor.sh --local`; add `--github`
  to check public API transport and authenticated repository/workflow reads.
- Local ArmPort suite: `bash scripts/codex/check.sh --armport`.
  Startup/zoning/monorail changes: also use `--lifecycle`, or `--all` for both.
  These wrappers require the pinned tools and pristine historical baseline;
  report missing prerequisites, not a test pass or an unexplained code failure.
- Wrapper regression tests: `bash scripts/codex/check.sh --foundation`.
- Run relevant tests, fix failures introduced by the change, and rerun affected
  checks as part of authorized development. Do not run the full native/runtime
  chain on every edit. Report exactly which checks were performed.
- At most TWO compiler processes total; set `CMAKE_BUILD_PARALLEL_LEVEL=2`.
  Preserve sequential native architectures and the existing CI coordination.

## Build, review, and handoff

- Use the current task's approved, serialized build -> app-runtime -> thor-apk
  chain. Bind explicit upstream run IDs and artifact identities to the candidate
  source. Check current workflow inputs; never select an unrelated latest run.
- Observe the current explicit-dispatch/[skip ci] policy. Starting a duplicate
  run can cancel useful CI. The setup/startup scripts must never dispatch CI.
- Network access, service authorization, local tests, native builds, runtime
  qualification, APK approval, and Thor results are separate claims. Verify
  the needed capability; a successful API read does not prove write permission.
- Preserve existing user/reviewer boundaries for signing, APK handoff, merging,
  protected branches, and publication. Prior authorization remains applicable
  within its stated scope; routine reversible work needs no repeated question.
- Continue through implementation and relevant verification within the assigned
  objective. If CI/review blocks one step, do useful independent work in scope.
- At a checkpoint, update `STATUS.md` (at most 40 lines) and the relevant task
  note with source identity, actual commands/results, pending runs, blockers,
  and the next concrete action. Use existing evidence formats and scripts.
  Do not introduce a new gate, lease, or receipt system.
