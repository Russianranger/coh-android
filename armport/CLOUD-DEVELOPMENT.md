# COH-ArmPort in Codex Cloud

This is the host development setup. It prepares source editing and local checks.
Full native builds, retained runtime qualification, signed APK packaging, and
Thor measurements remain the project's existing, separately qualified stages.

## First use

1. Open **Settings -> Codex Cloud -> Environments** and create or edit a private
   environment with `Russianranger/coh-android` attached.
2. During setup, select the foundation branch named in the delivery (or a later
   development branch containing these files). Ask the setup agent to verify
   branch/HEAD and preserve any existing changes before switching branches.
3. Enable package-manager domains and permit `api.github.com` and
   `raw.githubusercontent.com` when needed. Keep inherited proxy and TLS trust.
   GitHub source/archive/release hosts and dependency hosts must also be allowed;
   check actual redirects if a download is denied. Network permission and
   repository/service permission are separate.
4. From the repository root, run:

   ```bash
   bash scripts/codex/setup.sh --install-system
   bash scripts/codex/doctor.sh --github
   bash scripts/codex/check.sh --all
   ```

5. Resolve reported prerequisites/access failures. Record the tested setup in
   the environment's Install script and Start skill, save and publish/republish.
6. Start a new task from the published environment. Verify the assigned branch
   and run the same doctor before starting development. Preserve the distinction
   between the setup branch and the currently frozen gameplay candidate.

The current Cloud UI uses Install script and Start skill. Existing tasks retain
their own state after environment republication; a new task uses the updated
prepared environment. Older Setup/Maintenance-script environments use a
different lifecycle; configure those fields only if that is the UI you have.

Official guide: <https://learn.chatgpt.com/docs/environments/cloud-environments>.

## Install script

Run from the checkout containing this file:

```bash
bash scripts/codex/setup.sh --install-system
```

The script installs missing Debian/Ubuntu host tools when explicitly given
`--install-system`, prepares a Python virtual environment, installs the exact
Pillow version read from the build workflow, and prepares the pinned baseline.
It does not install an ARM64-host compiler onto an x86 host or run the game.
Without `--install-system`, system tools are left to the prepared environment.
The Android SDK and signing material remain in the established APK workflow.

`--skip-baseline` is an explicit partial-setup option for specialized work.
Its result does not establish that the ArmPort suite is ready. The normal
foundation setup includes the baseline.

## Start skill text

Use these instructions in the environment's Start skill field:

```text
Locate the Russianranger/coh-android checkout and preserve existing changes.
Read AGENTS.md and root STATUS.md; establish the assigned branch and actual HEAD.
Run bash scripts/codex/doctor.sh --local from that checkout.
Report missing prerequisites precisely and continue useful authorized work.
Use the repository check wrappers for validation; they load the prepared paths.
Start runtime services only when the current task needs them. Coordinate native
builds and follow the current task's serialized CI/reviewer instructions.
```

This field is startup guidance, not an instruction to reinstall every tool or
run all tests on every turn. It creates no recurring schedule or background job.

## Paths and variables

| Name | Meaning |
| --- | --- |
| `COH_CODEX_CACHE_DIR` | Optional cache location. Default: `$XDG_CACHE_HOME/coh-codex`, or `$HOME/.cache/coh-codex`. Put it outside the repository. |
| `ARMPORT_SERVER_BASELINE_ROOT` | Optional existing baseline path. It must be the exact clean baseline checkout; otherwise setup uses the cache's `baselines/<pin>` directory. |
| `CMAKE_BUILD_PARALLEL_LEVEL` | Wrappers enforce `2`, matching project limits. |
| `GH_TOKEN` / other credentials | Use the environment's supported authentication/secret configuration only when required by the chosen integration. No token belongs in these files. |

Scripts resolve the current baseline commit from the literal `BASELINE_COMMIT`
in `armport/app/server_package.py`. They parse it without importing runtime code.
They check the baseline's Git root, exact HEAD, cleanliness, and nonsymlink path.
An existing wrong or dirty checkout is reported and preserved. A new baseline
uses the workflow's sparse inputs and avoids large LFS asset downloads.

Wrappers load the virtual environment and baseline path themselves. There is no
need to rely on an `export` in a previous setup shell surviving into a new task.
For a manual command in a terminal, use:

```bash
source scripts/codex/common.sh
coh_activate
python3 -m unittest discover -s armport/tests -p 'test_*.py'
```

The source checkout needs real Git history: several existing tests read
historical or sparse inputs with `git show`. A folder of downloaded files is
not sufficient to claim the complete project test suite passed.

## Daily commands

| Command | Scope |
| --- | --- |
| `bash scripts/codex/doctor.sh --local` | Read-only repository/tool/baseline checks. |
| `bash scripts/codex/doctor.sh --github` | Also bounded public transport and GitHub repository/workflow GET checks. |
| `bash scripts/codex/check.sh --armport` | Existing ArmPort unit suite. |
| `bash scripts/codex/check.sh --lifecycle` | Existing saved-startup, zoning, and monorail suites. |
| `bash scripts/codex/check.sh --all` | Both groups, sequentially. |
| `bash scripts/codex/check.sh --foundation` | Disposable-fixture tests of these setup scripts; Python/Git/Bash, no network needed. |
| `bash scripts/codex/ci-status.sh` | Runs for the current exact commit. |
| `bash scripts/codex/ci-status.sh RUN_ID` | One explicit run's identity and result. |

Doctor exit codes: `0` requested checks passed; `2` local prerequisites missing;
`3` GitHub checks unavailable with local prerequisites satisfied. A network or
authentication error is not a game regression. The checks do not exercise push,
workflow dispatch, signing, artifact downloads, or device access.

Run checks relevant to the change. Use native extracted-source sanitizer
controls when native behavior changes; choose their existing commands from the
current workflow/task note. No new compiler or runtime compatibility is implied
by the shell foundation tests.

## Native edits and the candidate chain

Use `armport/scripts/patchwork.py init <fresh-external-directory>` to prepare a
native authoring tree when needed. Edit/commit in its `src` directory, with
patch-filename commit subjects, then export with `patchwork.py export <directory>`.
Preserve an existing useful tree. `upstream/` remains unchanged.

The full chain is `armport-build.yml` -> `armport-app-runtime.yml` ->
`armport-thor-apk.yml`. Use the assigned candidate head and explicit source run
IDs, continue only after success, and preserve the current review boundaries.
For the server-metrics candidate, consult the current producer correction note
for `build_server_metrics`, server input IDs, and `server_metrics` requirements.
Do not reuse a historical default or choose an unrelated latest artifact.

Read root STATUS.md, current PR reviews/comments, and the current task note
before dispatch. Foundation scripts only prepare/check the host and read CI.

## Integration and recovery

The initial foundation is a separate commit/branch. Once it is accepted for the
development branch, integrate that commit through the normal review workflow;
do not advance a frozen candidate while its source identity is being qualified.
The environment must use a branch containing these scripts when invoking them.

Keep current work in Git and update the existing short checkpoint at handoff:
source, changed behavior, actual validation, pending runs, blocker, next action.
Historical handoffs remain available for rationale. They do not reassign roles
or make an old pending run current.
