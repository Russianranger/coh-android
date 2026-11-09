# x86 track: integration and handoff to Claude

Recorded 2026-11-02 America/Chicago. This assignment consolidates existing work;
Claude owns subsequent development. Coordination: [issue #10](https://github.com/Russianranger/coh-android/issues/10).
Direction: [armport/PERFORMANCE-PATH.md](armport/PERFORMANCE-PATH.md), commit
`365ab195e29120d1cf2c862a5a5db05a361ed2f9`. The x86 client is primary; ARM64
remains selectable, experimental and shelved. Keep x86 Win32 servers and
PhysX/ragdolls. Goals are measured from cold start even if resident/idle servers
are added later. `main` remains the default branch.

## Exact source and delivery identity

The frozen source checkpoint is **`6a9ccc5b7de531b7dd8b1ba1e6247e71ed05da31`**,
tree **`582106762cabf6090904f82548b94d67a2120489`**. Production behavior last changed
at **`263acad1f57faff91505afcbb517494a8fc9841e`** (tree
`69d572483ae8e75989f530471dc15dbf40638b8b`); the two following commits correct
test adapters only. Subsequent commits contain handoff documentation and
validation records only. The final
doc-bearing `x86-track` head and tree are recorded verbatim in issue #10's
completion/CI-request comment; that is the head Claude must build. A committed
file cannot contain its own commit/tree hash. Verify the delivered pair with:

```bash
git fetch origin x86-track
git rev-parse origin/x86-track origin/x86-track^{tree}
```

Publication used the connected GitHub Git-data tools because terminal push had
no credentials. Those tools assign commit metadata; ordered merge parents and
all source file trees were preserved. Commit references here use the published
IDs. Raw test logs retain the local audit IDs; see
[publication-map.json](armport/evidence/x86-track-integration/publication-map.json)
for their exact published counterparts and matching trees. No existing branch
history was rewritten.

No native source was edited during consolidation. `upstream/` remains tree
`b343713b3067b4921165323858cd6553cb4301cf`; x86 `patches/` remains tree
`ffcb910e17540ea97360b6783b3a2099d485f8bc`, identical at .36, both older PR tips
and all five integrated tips. The inherited 0119 changes came from the startup
branch through its ordinary merge; no native patch was authored for this task.

## What was merged

`x86-track` starts at sampler-review-fix, then uses these ordinary merge commits
in the requested order. No existing branch was rewritten or deleted.

| Source line | Exact source head | Integration commit |
|---|---|---|
| armport/sampler-review-fix (.46) | `8dc2a66d72477b3c62227e572538b13f0e4f912b` | branch starting point |
| armport/mapserver-startup-60s (PR #9) | `1f75894db9117f3567b76d087d7cc5ddce87b3e6` | `ce359256d0e7e1bb9872698c5ab9da6e91e84b7b` |
| armport/mapserver-modern-runtime-qualification | `84c79f336b94442dc151b06df6e993823746154c` | `fb9fce3c33f480cd78ad4aa9efcb439b8fd87547` |
| armport/m5-thor (includes King's Row docs) | `b7806a6bdfc3cf159f743786fc9ed6aab94ce801` | `28234c9a29556768405357bfd6bf1e1235ce2eef` |
| armport/performance-path (docs) | `365ab195e29120d1cf2c862a5a5db05a361ed2f9` | `9c4c8124c4732a49e6890c57cf6c92a87353573b` |

Startup and modern qualification merged without conflicts. The M5 conflicts
were only `STATUS.md`, `armport/M5-HANDOFF.md`, and `armport/M5-THOR-TEST.md`:
the latter two retain the newer b7806a6bd results instead of obsolete running-CI
claims; STATUS is one coherent file under 40 lines. No code from the five live
tips was deliberately dropped; the discarded conflict text was the obsolete
checkpoint/status prose. Commit
`556193f7ea1fce317af6d253199686979cf711ca` adds the current
[X86-THOR-TEST.md](X86-THOR-TEST.md) and labels the M5 sheets historical.
`ClientRuntime.clientArchitecture(Context)` still defaults to x86;
`ClientActivity` still offers `ARM64 client (experimental)`.

## .37 app/guest port and skip audit

Reviewed release `3570430cefdb15d9b239563e85cccf4d8fe6f32e` through PR #1 head
`643d12638210d653e3b28de29b6239baf67da91c`, and PR #2 head
`398b46680c02026714665e4d8864e9ef4af6822e`. The checkout actually reports .36
as their common merge-base with this line; regardless, neither PR tip was
merged or made a parent. Applicable changes were ported as normal commits,
as requested. The guest-only .36→PR #1 delta is +1858/-76; including tooling
and fixtures the reviewed android/tools/android range is 40 files, +9634/-82.

| Decision | Source and destination | Reason |
|---|---|---|
| Ported | `b46984c78d067705c47d7fdb5bb0cc5a4508d824` → `e50a0e42e1dc489f540ccecb788266e39fd3ed70`: `android/guest/game_device_diagnostic.py` and `tools/android/atlasgame/test_device_cleanup_lineage.py` | Independent namespace-link/disappearing-task cleanup hardening. Keep exact worker/token/prefix/start-time ownership and fail-closed handling. This is **not** a proved fix for Thor's EACCES/cache-return failure. |
| Integration wiring | `263acad1f57faff91505afcbb517494a8fc9841e` | Admit the changed cleanup helper in `armport/app/build_thor_apk.py:CHANGED_RUNTIME`; existing donor inventory already stages it. Two package tests verify current bytes, inner/outer pins and donor tamper rejection. Both commits credit the source. |
| Already superseded | b46984c78 manual-report hunks in `ClientAcceptance.java`/`ClientRuntime.java`, `test_manual_report_acceptance.py`, `fixtures/thor-manual-report-0.13.36-20261013.json` | Retained `0bf31c81b1b5a9f8427b4692c623702b30e7029e` has the stricter `clientInteractionPolicyAccepted` policy, used by `guestAccepted`, requiring completed interaction and Finish. `armport/tests/test_manual_session_acceptance.py` covers it with actual Java. |
| Skipped | Dormant native-startup-metadata feature, .36→643d126382; paths below | Coupled to unqualified native consumers and .36 donor manifests. `ACTIVATION_IMPLEMENTED=False`, component/reviewed execution authorities remain None. Bringing it in would add dormant performance/activation work rather than preserve an enabled capability. |
| Skipped | .37 packaging/admission/routing and associated tests; paths below | These qualify the skipped metadata chain rather than the current 0119/metrics lane. |
| Skipped | PR #2 `398b46680c02026714665e4d8864e9ef4af6822e`, and PR #1's equivalent later `643d12638210d653e3b28de29b6239baf67da91c` | Source-audit/workflow repairs for that same .37 promotion chain; they do not repair armport-build/app-runtime. |

Skipped guest paths under `android/guest/` (only their .37 deltas were skipped;
current inherited implementations stay):
`atlas_beacon_package.py`, `character_zoning.py`, `client_gpu_profile.py`,
`client_interactive_diagnostic.py`, `client_startup_diagnostic.py`,
`game_diagnostic.py`, `local_character_server.py`, `native_map_startup_contract.py`,
`native_startup_metadata_contract.py`, `server_animation_package.py`,
`server_cache_package.py`, `server_fx_catalog.py`, `texture_header_index.py`.

Skipped tools under `tools/android/interactive/`:
`build_client_zone_startup_apk.py`, `classify_client_zone_startup_change.py`,
`classify_map_startup_native_change.py`, `derive_native_metadata_cache_proof.py`,
`native_startup_component_migration.py`, `native_startup_metadata_admission.py`,
`prepare_native_metadata_qualification_fixtures.py`, `qualify_client_zone_startup.py`,
`release-client-zone-startup-0.13.37.json`; new tests
`test_client_zone_startup_package.py`, `test_derive_native_metadata_cache_proof.py`,
`test_map_startup_native_change.py`, `test_native_metadata_map_activation.py`,
`test_native_metadata_qualification_fixtures.py`, `test_native_metadata_runtime_activation.py`,
`test_native_startup_component_migration.py`, `test_native_startup_metadata_admission.py`,
`test_native_startup_metadata_contract.py`. Also skipped the whitelist-only
changes in `classify_client_animation_repair_change.py`,
`classify_client_map_startup_change.py`, `classify_client_profile_recovery_change.py`.
No source work was deleted; all donor branches remain recoverable.

## Known open defects and measurement limits

Evidence: b7806a6bd's
[dated Thor report](armport/notes/M5-THOR-20261102-RESULTS.md) and
[machine-readable summary](armport/evidence/20261102-thor-results.json).
Both supplied exports identify .44, ARM64 client with x86 servers; the companion
export is setup-only. They do not validate .45/.46/.47 or this x86 integration.

- Repeated Wine worker-environment **EACCES** → `persistent_live_permission_denied`
  → **`Atlas data cache return lacks proved owned Wine cleanup`**. The data cache
  remains stranded. Save committed and PostgreSQL/prefix graceful shutdown are
  separate successes. Do not weaken ownership proof or label cache return passed.
- User reports **King's Row worse than before the port**. Cold destination
  preparation **656.024 s**, request→arrival **711.056 s**. The short loaded-zone
  interval averages **25.63 rendered FPS**, not server tick/NPC smoothness.
  Atlas remained resident. No matched pre-port run proves the regression cause.
- Preparation destination RSS peaked at **1772.25 MiB**; system-wide deltas were
  **17,747 swap-in pages**, **289,318 swap-out pages**, **18,104 major faults**.
  These establish preparation pressure, not app-attributed PSS, thermal throttling
  or the cause of post-arrival stutter. Gameplay CPU/tick causation is unmeasured.
- **P2/P3 fixes are in** via `624537231` and sampler head8dc2a66d: pending discovery
  gets a fresh-window retry; observer lineage preparation is resumable/bounded.
  See [M5-SAMPLER-REVIEW.md](armport/notes/M5-SAMPLER-REVIEW.md). Launch history
  does not implement prior-zone retirement. This integration does not fix stutter.
- ODBC reuse, startup clocks, metrics and corrected 0119 pin are inherited from
  PR #9. Performance gain, x86 Thor gameplay FPS and ≤60-second cold starts are
  **unmeasured/unproved at this head**. Retained runtime CI is not modern Thor
  server qualification or a device test.

## Pinned runtime, server and version identities

Sources: [android/runtime-lock.json](android/runtime-lock.json),
[armport/app/server_package.py](armport/app/server_package.py),
[android/guest/dbserver_diagnostic.py](android/guest/dbserver_diagnostic.py),
[armport/app/build_thor_apk.py](armport/app/build_thor_apk.py). No pin changed here.

| Item | Pinned identity |
|---|---|
| Bookworm ARM64 base | 353710639 B; SHA256 `08c639c26506dc6fbd15464bec475337087bb23cb7c0c5ace2db5240ee36424f` |
| Wine/FEX runtime bundle | 318095727 B; SHA256 `030f38066af7b786c142e199cb84adec037840b0f029338849e43f99203a93e1` |
| Wine / FEX commits | `b073859675060c9211fcbccfd90e4e87520dc2c2` / `320c5f18475b0c8a7e99c51a5fdc5b5e35b147ab` |
| x86 ODBC | 18.00.0004; MSI SHA256 `1b1c85f694ecad95fd3a0125a8b071669772bef098366738de48812124896773` |
| Game source / data | `0b75ade0c801735e10c5798f641948a45cc50488` / `d51533ec8e6a9cf726b9214968077a05fdcf19f3` |
| DbServer package / schema manifests | run36460867428; SHA256 `95f62cc81b0743c13652e55aee01aed6871fc96d70a84b8dfd62fb8a0d9fe0d6` / `b89136892e69ceb39db640613d3f8a34abf2ef8e75e947f4034728b935938b92` |
| Original modern Thor MapServer (.36/.44 donor) | 7475200 B; SHA256 `fea96d0a20f5e245930abd0a97e8cc1da7c4ef4c83ff8a7d5a5c283ba8071363` |
| Retained .10 MapServer | producer `003b07bcd98cb100c1505c15670c07d11a240c8f`; SHA256 `52f85c9e2cccfe88eb92f0a2c379a45b14eb997339ce902ed7ba5d470f3690fb` |
| .36 APK donor | 42076692 B; SHA256 `14d88da1796d155dc1b98e45ac642c7702ff3286e7ef0f2a0772f8e48693b12f` |

The .46 instrumented modern PE was
`f359eecc07a92990701c3cdbeb1409d2a8a1f3ab5fbce941f52fd161d25526c1`
(build40929292200, build/source scope). The e563 .47-attempt modern PE was
`f893cee6cd6c4dc8b7c45c8b5f7c07572aaabbe50ee5b8730b9ddd3da12dac94`
(7494656 B; see the exact record in
`armport/evidence/mapserver-startup-native-41363927704.json`). These are
historical identities, not hashes for the as-yet-unbuilt integrated head.

`build_thor_apk.py` still reserves **0.13.47/versionCode62**. A prior .47 APK
workflow already succeeded (historical run41389970347); no APK was built or
handed off by this integration. **Next free pair: 0.13.48/versionCode63**.
Claude must advance both before any subsequent installable build.

## Local validation

Final source checkpoint: 6a9ccc5b7de531b7dd8b1ba1e6247e71ed05da31.
Full logs, commands, tree checks and limitations are retained in
[armport/evidence/x86-track-integration/validation.json](armport/evidence/x86-track-integration/validation.json),
with gzip logs and the complete `interactive-failure-index.json` in that directory.
The official Android SDK compile and real guest/native execution remain CI work;
host Java fixtures are not full Android or physical qualification.

| Suite | Result |
|---|---|
| Full ArmPort, pristine c86 baseline | **445 passed**, no skips/errors/failures; `armport-final.log.gz` |
| Modern-runtime controls | **53 passed**, no skips/errors/failures; `modern-runtime-final.log.gz` |
| Client guest / main device lifecycle / host smoke | **27 / 64 / 17 passed**; respective guest logs |
| Cleanup lineage, whole host /proc | 29 run, **1 error** from unreadable unrelated same-UID PID namespace; other28 passed. Controlled unchanged test fails identically on pristine c86 and merged code; see `controlled_proc_namespace.py` and both controlled logs. No ownership check was weakened. |
| Full interactive/Java before fixture corrections | **3048 run, 69 failures, 28 errors, 31 skips**, 717.383 s; `interactive-full.log.gz`. This suite is **not green**. |
| Affected modules after fixture corrections, at 6a9ccc5b7 | **138 run, 2 failures, no errors/skips**, 13.571 s; `merged-focused-final.log.gz`. All87 guest fixture cases pass; all Java harnesses compile. The remaining two failures are the old GPU bounded-.20-report positive expectations versus the current manual-reopen policy. |

Commands (use an installed `javac`, or a scratch launcher for
`java -m jdk.compiler/com.sun.tools.javac.Main`):

```bash
ARMPORT_SERVER_BASELINE_ROOT=<clean-c86-checkout> python3 -m unittest discover -s armport/tests -p 'test_*.py' -v
COH_CANDIDATE_ROOT=<repo> ARMPORT_SERVER_BASELINE_ROOT=<clean-c86-checkout> python3 -m unittest discover -s armport/modern-runtime -p 'test_*.py' -v
python3 -m unittest discover -s tools/android/client -p 'test_guest.py' -v
python3 -m unittest discover -s tools/android/atlasgame -p 'test_game_device_diagnostic.py' -v
python3 -m unittest discover -s tools/android/atlasgame -p 'test_host_device_smoke.py' -v
python3 -m unittest discover -s tools/android/atlasgame -p 'test_device*.py' -v
python3 -m unittest discover -s tools/android/interactive -p 'test_*.py' -v
PYTHONPATH=tools/android/interactive python3 -m unittest test_character_server test_kings_preparation_budgets test_saved_map_preparation test_local_launcher_wait test_client_capture_metrics test_client_gpu_repair_evidence test_storage_ui -v
```

The full interactive invocation used the file tree published ate50a0e42e; its production and interactive
test trees were identical through e5218566. Fixture-only commits
`2bf52f2cfd7040306e0c297d3cd424965d102b5d` and
`6a9ccc5b7de531b7dd8b1ba1e6247e71ed05da31` then supply the retained presentation,
architecture, thermal-clock, admitted-uninstrumented-package, launch-history and
ODBC dependencies to existing host adapters. No production behavior, historical
report bytes, readiness/timeout/ownership guard, or legacy acceptance assertion
was relaxed. Affected modules were rerun at the final source checkpoint; the
12-minute full interactive suite was not repeated after test-adapter-only changes.

Remaining qualification gaps are explicit: authenticated historical APKs/build
receipts/native MapServer fixtures are absent; host Vulkan CPU ICD and PostgreSQL
fixture gates are unavailable; obsolete historical publication-path/loader-count
and appearance-producer assertions disagree with the current line; two old GPU
positives disagree with the intentional manual-reopen policy. Representative
donor failures and the two guest synthetic-package errors were reproduced on
pre-port/startup source in the comparison logs. Do not claim every remaining
failure was independently reproduced, or treat these gates as passed. The
failure index preserves exact cases and errors for Claude. Missing fixtures and
historical requalification were not expanded into new runtime/native work.

## CI request and coordinator usage

**Use issue #10's exact frozen-head CI request; do not run the old coordinator
unchanged.** `.github/workflows/mapserver-startup-ci.yml` and
`armport/scripts/startup_ci_chain.py` target `armport/mapserver-startup-60s` and
unconditionally dispatch build → runtime → signed APK. Their historical branch
and APK behavior is preserved, not repurposed during this handoff.

Claude/reviewer should perform exactly one chain, verifying the branch still
equals the full SHA posted in issue #10 before each dispatch:

1. `armport-build.yml`, ref `x86-track`, input `build_server_metrics=true`.
2. Only after that succeeds, `armport-app-runtime.yml`, ref `x86-track`, with
   `client_run_id`, `data_run_id`, `server_run_id` all equal to that **same build**.
3. Record both run IDs, head SHA and results in issue #10. On failure record the
   run/job/step and stop; **do not dispatch armport-thor-apk or publish a release**.

The coordinator's frozen-head, duplicate-run and required-artifact checks in
`startup_ci_chain.py` remain the model for a future two-stage coordinator; it is
not directly runnable for this request. The workflows are branch-resident;
default `main` and repository settings must stay unchanged. At most two compiler
processes; ARM64 and i686 sequential; one CI chain at a time. Modern support
waiters/rollback helpers retain historical startup-branch/cohort defaults and
must not be mistaken for qualification of this integrated head.

Historical CI, kept distinct from the new request:

- [41363927704](https://github.com/Russianranger/coh-android/actions/runs/41363927704)
  build passed; [41372922907](https://github.com/Russianranger/coh-android/actions/runs/41372922907)
  failed in `interactive-guest`, step13 `Create, save, restart and reopen through
  the selected ARM64 app guest`: staging rejected the stale 0119 hash before
  guest launch. Repair/regression is
  included; source evidence is under `armport/evidence/mapserver-startup-*`.
- Corrected source1f75894db9117f3567b76d087d7cc5ddce87b3e6:
  [coordinator41378023882](https://github.com/Russianranger/coh-android/actions/runs/41378023882),
  [build41378036783](https://github.com/Russianranger/coh-android/actions/runs/41378036783)
  and [runtime41385774100](https://github.com/Russianranger/coh-android/actions/runs/41385774100)
  succeeded. Its historical APK41389970347 also succeeded; no APK link/handoff is
  requested. The coordinator explicitly reports modern Thor qualification and
  the ≤60-second target false. These runs do not qualify x86-track.

## Superseded lines and stop boundary

Use `x86-track` as the integration/development line. Draft PRs **#8, #9, #1, #2**
are superseded through issue #10, with comments pointing here before closure.
Their branches are retained. The five merged source tips above, plus the
older `armport/server-metrics` line inherited by sampler, are superseded as
development entry points. PR #1/#2 remain recoverable donors for the skipped
.37 work. `COH-ArmPort` stays historical/secondary; `native-android` stays frozen.
Do not delete branches, change default `main`, force-push, or merge this work
into main as part of the handoff.

After posting the final source/tree, local results, port/skip list and CI request
and closing the four draft PRs, this agent stops. Claude continues development.

## 0.13.50: ARM64 client primary, King's Row and client start (Claude, 2026-11-03)

User decision (2026-11-03 11:38 CST): keep the ARM64 client, shelve x86 as the
reversion path. Test sheet: [THOR-TEST-0.13.50.md](THOR-TEST-0.13.50.md).

- **ARM64 is the default client**; `x86 client (fallback)` stays selectable.
- **Shared read-only server data** (option, on): both zone servers omit 15
  folders from their private trees and read them from one tree per Atlas data
  identity through `runtime/serverdata` (King's Row's runtime now has `tools/`).
  `sequencers` and `player_library` stay private: the wide CI probe rebuilt
  `sequencers.bin` and 21 power/salvage bins with them shared. A tree without
  its marker is rebuilt; older identities' trees are removed (directories and
  links only, checked first). The overlay's 52 files are all `object_library`.
- **Stranded-cache recovery race fixed** (0.13.49 session 1's 360 s cold mirror).
- **Client folder scan**: ArmPort patch 0120 (`ARMPORT_FOLDER_CACHE_SKIP`); the
  guest skips `scripts.loc` and `server/` for the ARM64 client (option, on). The
  ARM64 client is a production-mode client reading loose files (patch 0042), so
  it scans every folder upfront; switching it to the on-demand dev mode was
  rejected (different mode). The client source never reads either folder.
- **Client asset installs**: an unchanged reused install does one leaf pass, not
  two (visual 27.7 s, zones 47.6 s, audio 4.1 s on 0.13.49).
- Correction to the 0.13.49 priority note: the ARM64 client is in production
  mode, so the 7 nice-19 threads are threads it sets to idle priority itself,
  not an IDLE process class.
- Chain: build 41689729437 (client with 0120), runtime 41704290931 at
  `0bf0c1c4b` (shipping servers, fast mode, shared data and skip on; passed).
  APK 41711575113 failed: `zone_asset_package.py` and `client_visual_assets.py`
  were missing from `build_thor_apk.CHANGED_RUNTIME` (the only guest files changed
  since 0.13.49 that were not listed). Added; the APK is rebuilt from the same
  runtime, since guest payloads are byte-identical to `0bf0c1c4b`.
- **Published:** [coh-atlas-gameplay-v0.13.50](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.50)
  (pre-release), APK 41712293048 at `ef7d2d3dc`, 80,956,326 bytes, sha256
  `a789355404a594a34eb5146eba2efb6c560a8afd784743b53b10bae21bb00472`, version code 65.
- Runtime 41704290931 evidence: 15 folders shared (128,765 files, 3,524
  read-only directories), reused on reopen (link 0.004 s); reopen bin writes 0;
  story arcs 470/957/3528 both sessions; sequencer gap 40.7 s (level-1 probe
  40.8 s, 0.13.49 runtime 36.8 s; the wide set was 240 s). Creation: private
  mirror 31 s (was 99.5-106 s) plus 79 s to build the shared tree once.
  Client: `phase=skip folders=2`, scan 123,633 files in 44 s; client start
  81.7 → 71.8 s against runtime 41642095387. Reopen Atlas 129.6 s (unchanged).
  CI has no imported supplements, so the asset-pass trim is unmeasured there.
- Known: `test_classify_storage_cleanup_change` keys on the last commit's file
  list and fails for multi-area commits; not a behaviour regression.

## 0.13.51: cache reuse fix, station frame cap, thermal and tick evidence (Claude, 2026-11-03)

User follow-up to 0.13.50: in King's Row, NPCs, cars and the monorail train
jump from spot to spot; Atlas is fluid on first load and on return. The 76 °C is
the device's own reading (it idles at 40-43 °C). User approved the cache fix,
the station cap and evidence, and an earlier client start. Test sheet:
[THOR-TEST-0.13.51.md](THOR-TEST-0.13.51.md).

- **Cache reuse** (`38cb5dee8`): `verify_changed_directories` skips the shared
  top-level folders at the root when the generation did not record them; a
  private copy of one is still refused. Atlas and King's Row tests reproduce the
  0.13.50 refusal without the fix.
- **Station frame cap** (ArmPort patch 0121, `2f893d9b8`): the client polls
  `ARMPORT_FPS_CAP_FILE` once a second with Win32 calls; zoning writes 10 in the
  `baseline` and `map_ready` phases (before the blocking Python preparation) and
  removes it at ready, arrival, failure and cleanup. `/maxfps` changes during
  the cap are kept. Native behaviour test with stubs; ARM64 syntax check.
- **Evidence:** `android_thermal_samples` (30 s, API 30 headroom);
  `character_zoning.tick_probe` (every 30 s, 4 s at 50 Hz of completed-tick gaps
  for the occupied map); `wine_priorities` now 12 samples every 120 s with
  `last_cpu` per program and `cpu_max_khz`.
- **NPC jumping, source reading** (Ouroboros, file:line in the review notes of
  this round): the server sends entity updates 4 times a second, and NPCs and
  cars are simulated and sent only every 15th tick (2 per second,
  entaiInstance.c:1605-1646, entsend.c:1284). The client draws them 2 x
  `auto_delay` (0.3 s) in the past (entrecv.c:4086, 4153), so 0.1 s of slack; a
  late update freezes them and they catch up (entrecv.c:4019). Ticks over 2/30 s
  also drop game time (svr_init.c:212) and make the client re-sync its clock
  (entrecv.c:3673). Likely: the King's Row NPC/car tick overruns under FEX, or
  FEX is still compiling that code right after the zone starts (the visit began
  within a minute of ready). No send rate or delay setting exists; the ARM64
  patches change none of this.
- **Not built: earlier client preparation.** With the cache reused, the 0.13.49
  and 0.13.50 phases put the client (about 311 s to login) and Atlas (about
  311 s to ready) within about 15 s of each other. The client's asset installs
  write into the x86 client-work tree that the server's data copy reads, so an
  overlap needs a new concurrency proof for at most 15 s. Next big items instead:
  Atlas MapServer start (228-242 s) and a saved client folder scan (105-114 s).
- Chain: build 41734472082 failed in "ArmPort zoning guards":
  `test_prepares_off_thread_then_spawns_and_observes_first_tick` used fake time
  124 s, read as a reversed clock on a runner up for under 124 s (reproduced with
  a 60 s monotonic clock; fixed in `e5c15c3b4`, test-only). Build 41735032151
  (client with 0121) passed; runtime 41745666658 at `e5c15c3b4` passed (shipping
  servers, fast mode, shared data, skip on, seccomp).
- Runtime 41745666658 evidence: reopen bin writes 0; story arcs 470/957/3528 both
  sessions; reopen data cache checkout 1.4 s with no cold mirror; shared tree
  reused (link 0.004 s); reopen Atlas spawn → ready 133.6 s; client scan
  123,633 files in 47 s, `phase=skip folders=2`. CI takes no monorail trip, so
  the frame cap and the tick probe are covered by unit tests only.
- **Published:** [coh-atlas-gameplay-v0.13.51](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.51)
  (pre-release), APK 41750489814 at `e5c15c3b4`, 80,960,422 bytes, sha256
  `7ce19258a588de3c2d740ffd6b9713c28f785c99fe8811aabc12aeb6fe5dc7ce`, version
  code 66, client run 41735032151. The package record's
  `armport_client.default_architecture: x86` is a stale label from
  `stage_app_assets.py`; the app's default has been ARM64 since 0.13.50
  (`ClientRuntime.clientArchitecture`).

## Other zones: start-up anatomy and on-demand starts (study, Claude, 2026-11-04)

User, 23:57 CST: "1 and 2 are approved for development"; memory must stay well
under 16 GB (their PC "start everything" script exceeds 30 GB). Two
source-reading studies (upstream/ouroboros, with file:line evidence):

- **Zone server start-up splits cleanly.** The MapServer learns its map only at
  `connectToDbserver` → `dbRegister` (svr_init.c:2137; dbcomm.c:250-289), after
  every shared phase. The map name, static flag and mission info arrive in the
  DbServer's reply (dbcontainer.c:152-197). Device times (0.13.51 exports):
  shared 211 s (Atlas) / 198 s (King's Row) — sequencers 52-67 s, FX 43-49 s,
  story arcs 49 s, object library 15-18 s, config 12-17 s; map-specific 49 s /
  33 s (`groupLoadMap` 17-22 s, PhysX setup 6-17 s, collision, beacons, initMap).
  A pre-loaded spare can block before `connectToDbserver`, receive its map id
  and cookie, re-run the `base_map_id`/`instance_id` lookup
  (staticMapInfo.c:590-605) and continue: ready about 33-49 s after assignment
  instead of 231-260 s. Precedent: `-tsr` parks after the shared loads. A
  spare holds a full private copy of the shared data under `-nosharedmemory`;
  the stock shared-memory path (`ParserLoadFilesShared`) is untested under Wine.
- **DbServer map starts have one choke point.** Login (`findBestMapByBaseId`),
  zone doors/trains (`handleMapXferRequest` → `startMapIfStatic`), instances
  and missions (`teamStartMap` → `handleContainerSet`) all call
  `launcherCommStartProcess` (launchercomm.c:1496-1642), which builds
  `mapserver.exe -db <host> -udp -1 -map_id <id> -launcher -cookie <n>` and
  sends it to a Launcher. With no Launcher (our case) a static zone's
  container is deleted (mapxfer.c:312), so that zone is gone until restart;
  missions fail. Proposed hook: an overlay gated by an environment variable
  publishes a request record (map id, cookie, base map, name, mission info,
  command) instead, keeps `starting=1`, and never deletes a static container;
  the supervisor starts (or assigns a spare to) the map with that id and
  cookie, and delinks it (`-dbquery -delink`) on failure. The DbServer then
  waits as it does for a Launcher (waiting list, cookie-checked register,
  ready-for-players). maps.db has 901 containers (66 base maps + 835 clones).
- **Risks noted:** character select waits 90 s for a map (client `-notimeout`
  or pre-starting the saved zone); mission doors and contact lookups need door
  records from every static zone (`Doors.db`, none shipped); no upstream start
  timeout; memory per process is unmeasured (0.13.53 adds `rss_kib` per
  process to `server-metrics.jsonl`).

## 0.13.64: display updates above 1024 rectangles (Claude, 2026-11-09)

Thor 0.13.63 (user, 2026-11-09 09:55 CST, exports 20261109-154935 and
20261109-154946): Ralakar reopened in Mercy Island, moved and fought; then "a
sudden crash when my character was looking around with the camera rapidly";
the app seemed frozen and the gear lit up but did not open the menu; also "the
pet he summoned would not move towards an enemy when ordered to attack".

- **What happened**: the reopen connected on map 71 at 15:40:13 UTC
  (`character_connected_event`, name Ralakar). After the guest's last heartbeat
  at 15:46:21.7 the app logged "Client operation: Local display connection
  failed: RFB rectangle count exceeds limit" (`receiver_error`), stopped the
  guest (`postgres-graceful-stop` 15:46:29.9, guest result `cancelled`
  15:46:32.07) and finished the operation at 15:46:32 (run start 15:27:37.5 plus
  1134.6 s). No save in that session (`character_saved_event` null,
  `committed_sql_verified` false). `presentation_timing`: 19080 frames and
  3,359,190 Raw rectangles (176 per update), ~60 frames/s in the last minute.
  The second export is the preceding Set up / update runtime report
  (`setup_complete`).
- **Cause**: `InteractiveRfbClient` refused a FramebufferUpdate above 1024
  rectangles (`MAX_RECTS`). Xtigervnc (TigerVNC 1.12) counts its whole changed
  region into one update because the client advertises no LastRect; fast turns
  fragment that region.
- **Fix**: `MAX_RECTS = 0xFFFF`, the protocol's U16 range; each rectangle is
  still bounded by the framebuffer. New `presentation_timing.rfb_update_rectangles_max`
  (largest count of one update, kept across receiver teardown).
- **Gear**: not explained by the report. When the operation ends the menu
  reopens by itself (`refreshOverlayMenu`), and during the ~10 s shutdown the
  gear's click calls only `setMenuOpen` and the input release; no blocking call
  was found on that path.
- **Pets**: Mercy Island's MapServer console (`character-zoning-generation-1-map-71-console-tail.txt`):
  "loading beacons.. Beacon file not loaded for map:
  maps/City_Zones/V_City_01_01/V_City_01_01.txt". The shared zone tree has no
  graph (`prepare_zone_runtime`: "NPCs there do not path until their graphs are
  generated"); Atlas Park and King's Row use their generated graphs. A pet
  follows its owner but cannot walk to an attack target there. Next: a
  generator per map like King's Row's (`android-kings-row-native.yml`).
- **Tests**: `armport/tests/test_rfb_rectangle_count.py` (2): updates of 4096
  and 65535 1x1 rectangles decode with exact pixels and the largest count, a
  rectangle outside the framebuffer is still refused, the report keeps the
  counter; on 0.13.63's decoder the first fails with Thor's message. ArmPort
  suite: 539 run, 2 errors (the historical-baseline tests that need CI's
  baseline checkout; the same without this change).
- **Chain at 4f9e8eebe** (one chain on x86/perf-round1). Build 42653524766: the
  libraries job's ArmPort unit tests include `test_rfb_rectangle_count.py`.
  Trusted runtime 42668990132 (1780 s, THORHERO): the APK's runtime
  qualification; its `app-sources` job compiles the changed Java against the
  Android SDK. CI's runtimes read the display with their own Python RFB driver
  (`tools/android/client/host_smoke.py`), not `InteractiveRfbClient`, so the
  zone-trip and default runtimes were not repeated for this decoder-only
  change. Every run passed on its first attempt. APK 42674721584 published
  `coh-atlas-gameplay-v0.13.64` (92323241 bytes, sha256
  0201c871b8426f1aa9ed063bfd3de2a91b167f84ba8fcca80ed0d2e1c3d0a0fc, signer
  92955353…, the same as 0.13.50-0.13.63); its guest files match the commit.
- Version 0.13.64 (79); test sheet `THOR-TEST-0.13.64.md`.

## 0.13.63: Reopen any name with the game's own travel (Claude, 2026-11-08)

Thor 0.13.62 (user, 2026-11-08 19:56 CST, export 20261109-015537): "Failed when
trying to reopen hero".

- **What happened**: Reopen of Ralakar (saved in Mercy Island) passed the
  profile check before Wine (`character_profile_eligibility`: eligible,
  `character_name` Ralakar) and stopped in `local_dbserver_startup`: "Station
  travel (Game's own zone travel off) follows only a character named THORHERO.
  Turn Game's own zone travel back on to play Ralakar." The option was on
  (app report `stock_travel_requested` true; guest
  `character_zoning.stock_travel.requested` true). `prepare_runtime` calls
  `initial_map_preparation`, which qualifies the King's Row station route
  (`monorail_qualified`; the all-zone package is installed) and then captures
  the baseline, which binds the name (`bind_session_character`). 0.13.62's
  refusal asked `monorail_enabled()` there, but `stock_travel_active()` needs
  the external-maps DbServer layer, which `install_manual_atlas_dbserver`
  installs only after `initial_map_preparation` returns, so
  `monorail_enabled()` still read True. No SQL game mutation
  (`sql_game_mutations_performed` false); the profile is unchanged. CI's
  zone-trip runtime (OTHERHERO) has no King's Row package (`monorail_qualified`
  false), so it passed.
- **Fix** (`local_character_server.py`): `require_station_travel_name()`
  refuses another name only after `decide_zone_travel()`, which
  `prepare_runtime` calls right after installing the layer; every later bind
  (start()'s second baseline, creation's Enter Game) checks again. The message
  is unchanged (`STATION_TRAVEL_NAME`).
- **Tests**: `test_character_any_name.py` (16): a bind before the layer no
  longer refuses; `ReopenZoneTravelTests` drives the real zoning server in
  Thor's order (Ralakar saved in Mercy Island, King's Row qualified, the game's
  own travel): baseline, layer, decision, second baseline, the DbServer's Enter
  Game request for map 71, ready, connection metadata (`monorail_enabled`
  false, `stock_travel` true) and the reopen identity proof; station travel
  (option off, or on without the layer) still refuses Ralakar once known. On
  the published 0.13.62 guest these tests fail with Thor's message. Full
  interactive suite: 3227 run/86 F/14 E/36 S, the same failures as 0.13.62.
- **Chain at e679031ca** (one chain on x86/perf-round1). Build 42550231650: the
  libraries job ran `test_character_any_name.py` (16 OK,
  `ReopenZoneTravelTests` included). Zone-trip runtime 42558801806 with
  `character_name=OTHERHERO` (2300 s): creation typed OTHERHERO, and the run
  passes only when the guest's connected and saved events and its report carry
  that name; map 1 cookie 2 ready 620.7 s after the stock start (108 bins
  written, spawn to ready 443.9 s); reopen found OTHERHERO by OCR on the
  character list, no zone server before Enter Game (`local_atlas_startup` 0.0
  s), map 1 cookie 2 ready 142.1 s after the stock start, `/mapmove 101`
  (cookie 3) 177.2 s, 2 arrivals before the save. Trusted runtime 42563040886
  (1752 s, THORHERO). The default runtime was not repeated: the change only
  defers a check, and the trusted runtime runs the same THORHERO path (no stock
  travel) with trusted bins. Every run passed on its first attempt. APK
  42566326193 published `coh-atlas-gameplay-v0.13.63` (92323241 bytes, sha256
  8d748cb7a4b75acd9b92b26c325ee2c721ff40dc0006e04fa500c9db9373b508, signer
  92955353…, the same as 0.13.50-0.13.62); its guest files match the commit. CI
  has no King's Row package (`monorail_qualified` false), so only the unit
  tests replay Thor's order.
- Version 0.13.63 (78); test sheet `THOR-TEST-0.13.63.md`.

## 0.13.62: any character name; walking no longer waits (Claude, 2026-11-08)

Thor 0.13.61 (user, 2026-11-08 14:27 CST, exports 20261108-202601 setup and
-202611 session): "I was able to create a villain, but please make it so
controls arent locked and that i can name them something other than Thorhero."

- **What happened**: Resume removed the unfinished THORHERO
  (`unentered_character.removed`), the user created the Mastermind
  **Ralakar** (not THORHERO), and the DbServer started Mercy Island at Enter
  Game: `starting_zone_wait_seconds` 288.3, the first non-Atlas/King's Row zone
  on the phone, about 27 FPS (`ARMPORT_FRAME_RATE_V1`), Arachnos and Skulls
  spawned (entity log). The guest's `character_evidence` filtered the inventory
  by `name == 'THORHERO'`, so it never sampled Ralakar
  (`character_samples` empty, `connected_on_atlas` false); the app never got
  `character_connected`, so `canSaveLogout` stayed false. `canWalk` (the
  on-screen pad and the controller's W/A/S/D/Space, ControllerBridge) and Save
  required it: the "locked controls". After about 15 minutes the user quit
  (`ArmPort dialog: QuitNow`, client exit 0), which the session reports as
  "Actual CoH client exited".
- **Name** (`local_character_server.py`): `CHARACTER` is THORHERO until the
  session reads the real name from SQL: Reopen binds the saved row (ID 1 of
  COHLOCAL, any name) at the profile check before Wine; creation binds the one
  row the DbServer inserts at Enter Game (`bind_session_character`;
  `valid_character_name` = validate_name.c: ASCII, 3-20, no outer or double
  spaces; a session never renames). Every entity-log reader builds its pattern
  from `entity_name_prefix()` (re.escape): ready, positions, logout timer and
  location, rewards, BuyPower, contacts, tasks, and the zoning readers
  (`stock_ready`, `legacy_ready`, `stock_positions`, `stock_logout`,
  `terminal_position`, "Step 1: Ent <name> moving"). The opt-in native console
  producers (wine_character_events.c, the monorail producer) report only
  THORHERO, so for another name `immediate_event_contract()` is None and Atlas
  Park uses the stock entity logs (the legacy route); station travel refuses
  another name. Resume removes an unfinished character of any name; its SQL
  uses `md5(name)` instead of the player's text. Session budget (guest and
  app) carries the session's own name.
- **Ordinary-play save outside Atlas**: `reopen_connection_binding` accepted
  only Atlas (or monorail) ready evidence, so `accept_gameplay_progress`
  could not accept experience gained in Mercy Island. `stock_zone_binding`
  binds a reopen whose ready record is the zone's own stock CLIENT_READY line
  (`current_target_stock_CLIENT_READY_resumeCharacter_success`, embedded log
  route, same map, name and account).
- **App**: `ClientAcceptance.characterName` (the same rule) replaces the
  THORHERO checks; ClientRuntime keeps one name per session
  (`sameCharacter`) and shows it ("Ralakar is saved in Mercy Island"); texts
  say "your character". `canWalk` no longer needs `canSaveLogout`: walking
  follows the ordinary game-input gate and still stops while Save / log out
  runs (`movementSuppressed`; moving cancels the logout timer), after the save,
  during a zone transfer (ClientRuntime refuses gameplay input) and while a
  typed command or the text dialog is pending.
- **CI**: `armport-app-runtime.yml` gains `character_name` (3-15 capitals,
  default THORHERO): the host scripts type it and find it by OCR, so a
  runtime proves the guest with another name (Atlas through the stock logs).
- **Tests**: `test_character_any_name.py` (13: name rules, binding, every
  log reader with `Dr. O'Malley` and with Ralakar's own Mercy Island lines
  from the Thor export, creation binding and save, station-travel refusal,
  the stock-zone binding, the app's name rule and events, the walking gate);
  `test_character_profile_eligibility.py` (+2 unit, +2 real PostgreSQL:
  a named reopen and the md5 removal of an unfinished `Dr. O'Malley`; 38 OK on
  PostgreSQL 16.15); `test_session_budget_guest.py` (+1). Updated for the new
  wording or the bound name: `test_dynamic_initial_map.py`,
  `test_fresh_profile_recovery.py`, `test_manual_session.py`,
  `test_session_budget_java.py` (an invalid name, "X"). The build runs the
  any-name and budget modules. `build_thor_apk.CHANGED_RUNTIME` adds
  `stationary_contact_evidence.py` and `task_gate_evidence.py`
  (`test_thor_apk_runtime_review`).
- **Chain at 75523980e** (one chain on x86/perf-round1). Build 42525269953: the
  libraries job ran `test_character_any_name.py` (13 OK) and
  `test_session_budget_guest.py` (24 OK) after the real-PostgreSQL eligibility
  module (38 OK, PostgreSQL 16.15). Zone-trip runtime 42532830880 with
  `character_name=OTHERHERO` (2257 s): creation typed OTHERHERO, and the run
  passes only when the guest's connected and saved events and its report carry
  that name; map 1 cookie 2 ready 608.1 s after the stock start (108 bins
  written, spawn to ready 438.2 s); reopen found OTHERHERO by OCR on the
  character list, and its connected and saved events carried that name; no zone
  server before Enter Game (`local_atlas_startup` 0.0 s), map 1 cookie 2 ready
  141.2 s after the stock start; `/mapmove 101` (cookie 3) 171.8 s, 2 arrivals
  before the save; `client_logout_keys` kept 0 / aborted 0. Default runtime
  42536520114 (1792 s) and trusted runtime 42543661576 (1737 s) kept THORHERO.
  Default runtime attempts 1 and 2 failed in creation with CI's known flakes.
  Attempt 1, the slow logout (as trusted runtime 42322788540's attempt 1 and
  zone-trip runtime 42397533053): `/quittologin` sent 285 s after the client
  was ready, no Atlas logout line, "Character logout delivery does not match
  this ready client or its save window" (120 s), client 2.1 FPS in the world
  with the new-character help dialog drawn, `client_logout_keys` kept 0 /
  aborted 0 (not the 0127 key race). Attempt 2, the creator (as default runtime
  42316982535's attempt 1): "Costume page (HEAD/WEAPONS/Colors) not reached
  after body_next", OCR checks 144-156 s after ready at 9.4 FPS. Attempt 3, a
  second re-run of the failed `interactive-guest` job, passed. APK 42546944715
  published `coh-atlas-gameplay-v0.13.62` (92323241 bytes, sha256
  4151d44816333900a39889bd94b3451c5ec34ad895a13faa0e59203fad519eef, signer
  92955353…, the same as 0.13.50-0.13.61); its guest files match the commit.
- Version 0.13.62 (77); test sheet `THOR-TEST-0.13.62.md` (in place: Reopen
  Ralakar in Mercy Island, play, save).

## 0.13.61: Resume removes a THORHERO that never entered the game (Claude, 2026-11-08)

Thor 0.13.60 (user, 2026-11-08 07:53 CST, exports 20261108-135104 Resume and
-135110 Reopen): "Failed to even start the character start, both resume
character creation and reopen failed".

- **What happened**: both sessions stopped at the profile check before Wine
  (`character_profile_eligibility`, `checked_before_wine`). The inventory was
  `{"containerid":1,"authid":1353310574,"authname":"COHLOCAL","name":"THORHERO"}`.
  Resume: "First character creation requires a completely empty inventory".
  Reopen read its rows (`ents`: class, origin, level, experience, influence,
  description, motto, datecreated and logincount NULL; `ents2` subid 0,
  influencetype 1, no build; no powers, no costume) and stopped with "Saved
  THORHERO has no committed login baseline". No in-app path remained.
- **Cause**: 0.13.59's villain was not deleted; the 0.13.60 sheet and the
  0.13.60 section below said it was. s_finishHandleChoosePlayer allocates the
  container with `containerUpdate(..., 0)` (just_created stays 1), but
  handlePlayerContainerLoaded -> updateAuthUserData writes
  `Ents2[0].AuthUserDataEx` with `containerUpdate(..., TRUE)`, which clears
  just_created and inserts the whole container (COH_PG_INSERT_CONTAINER
  reserves ID 1) before setNewMap asks for the zone. When Mercy Island
  failed, doneWaitingChoosePlayerFailed took its unload branch (0.13.59
  DbServer error log: "setNewMap failed MapFailed", then "Someone unloaded a
  player during map transfer", which only containerUnload logs) and kept the
  row with Active 0. Only a MapServer writes class, origin, powers, costume
  and LoginCount, so this row never entered the game.
- **Fix** (`local_character_server.py`): `unentered_creation` (read-only)
  recognizes exactly that row: the accepted identity (ID 1, THORHERO,
  COHLOCAL); every field a MapServer writes NULL (`UNENTERED_NULL_FIELDS`,
  LoginCount included); at most Ents2 subid 0 without a build; no powers or
  costume; rows for ID 1 only in Ents and Ents2 among all 48 tables of the
  verified schema's `ents.template` (`ents_family_tables`, the set
  sqlDeleteContainer clears); ID high water exactly 1. Resume first character
  creation then runs one DO statement (`remove_unentered_creation`). It
  deletes those Ents2 and Ents rows under the same conditions and raises
  (rolling back) unless exactly those rows went and no row for ID 1 or any
  other character remains. Only then does it run `setval(ents sequence, 1,
  false)` (setval is not transactional) and require high water 0. The
  inventory and high water are read again afterwards. The eligibility
  record gains `unentered_character` (identity, row counts, start map, the
  kept fields of the removed rows, `removed`) and
  `sql_game_mutations_performed: true`. Anything else (a logged-in
  character, one power or badge, a second ID) is refused with the earlier
  message. Reopen of such a row says it never entered the game and to use
  Resume, and changes nothing. A creation session whose first zone fails now
  says Resume will create THORHERO again (`failed_creation`).
- **Tests**: `test_character_profile_eligibility.py`. Unit: the removal,
  16 refusals, the Reopen message, a failed removal, and the accepted
  48-table template (`run_generated_schema.template_columns`). Real
  PostgreSQL with the guest's own psql invocation: a DbServer-like row is
  removed (sequence `1:true` -> `1:false`, high water 0, the next DbServer ID
  is 1); Reopen changes nothing; a badge row refuses. Local PostgreSQL
  16.15: 34 tests OK, also in a copy limited to the libraries job's sparse
  checkout. The build now starts the runner's PostgreSQL 16
  (`armport/scripts/pg_fixture.sh`) and runs the module with
  `COH_REQUIRE_POSTGRESQL=1`.
- **App**: the Resume dialog says an unfinished THORHERO is removed first and
  the report keeps its rows; the ready-profile text mentions a first zone
  that did not start.
- Not changed: the DbServer (its unload is upstream behaviour; the guest
  handles the row at the next Resume). CI's sessions still start from a fresh
  profile, so the removal is proven on real PostgreSQL in the build, not in an
  app runtime; Thor is its first device run.
- **Build fix (Lua download)**: build 42488979665 at a4799e843 passed every
  job except `server-metrics-native`, which failed in both attempts (job logs
  128774761485 and 128778888649). That job builds two MapServer variants and
  CMake fetches Lua 5.1.5 from www.lua.org for each (`Lua.cmake`, CPM,
  URL_HASH). The first variant's fetch succeeded (4 s, then 15 s); the second,
  7 minutes later, timed out on all six connections ("Each download failed!").
  0.13.60's build fetched both in 4 s and 3 s. Placing the archive in the
  sub-build does not help: CPM deletes the sub-build before populating
  ("remove timestamps so CMake will re-download"). `server_metrics_producer.py`
  now gives a later variant a fresh extraction of the archive the first one
  downloaded (checked against the same SHA-256) through CPM's own override
  `CPM_lua51_SOURCE`, which still applies that variant's own
  `lua-cmake.patch`. The job also keeps the archive in an Actions cache
  (`out/lua-cache`), so later builds need no download at all; the evidence
  record gains `lua_archive`. Tests: 4 new producer tests (12 OK); a local
  CMake 3.28 replica with upstream CPM 0.40.8, the same declaration and a
  synthetic archive configured, patched, built and ran offline with the
  override, and failed without it. No source, game or app change.
- **Chain at bd27744ed** (one chain on x86/perf-round1, each on its first
  attempt; the first build at a4799e843 failed as above). Build 42499066512:
  the libraries job started the runner's PostgreSQL 16.15 (`pg_fixture.sh`)
  and ran `test_character_profile_eligibility.py` with
  `COH_REQUIRE_POSTGRESQL=1` (34 OK, none skipped). `server-metrics-native`
  (job 128805749349) found no cached archive, let CMake download Lua for
  `retained_progress`, configured `thor_certified_startup` with
  `-DCPM_lua51_SOURCE=.../lua-sources/thor_certified_startup` (its
  `lua51.lib` built from the patched `CMakeLists.txt`) and saved the cache
  `armport-lua-5.1.5-2640fc56…`. Zone-trip runtime 42506353321 on it
  (2260 s): creation, map 1 cookie 2 ready 608.9 s after the stock start (108
  bins written, spawn to ready 440.4 s); reopen, no zone server before Enter
  Game (`local_atlas_startup` 0.0 s), map 1 cookie 2 ready 136.1 s after the
  stock start, `/mapmove 101` (cookie 3) 172.0 s, 2 arrivals, same character
  ID and profile; `client_logout_keys` kept 0 / aborted 0. Default runtime
  42510220143 (1831 s); trusted runtime 42513450368 on the build (trusted bins
  applied, 1716 s); APK 42516615576 published `coh-atlas-gameplay-v0.13.61`
  (92319145 bytes, sha256
  1718a7844d7c1eb8cd16e28afda774938c0b06fbbca186c3142329b7ce4bc88b,
  signer 92955353…, the same as 0.13.50-0.13.60); its
  `local_character_server.py` and `character_zoning.py` match the commit.
- Version 0.13.61 (76); test sheet `THOR-TEST-0.13.61.md` (in place: Resume
  removes the unfinished THORHERO, then a villain in Mercy Island).

## 0.13.60: zones in the shared tree can start (Claude, 2026-11-07)

Thor 0.13.59 (user, 2026-11-07 20:56 CST, exports 20261108-025402 setup and
-025410 session): "Failed to load map when attempting mercy Island".

- **What happened** (operation.log, `character-zoning.json`, DbServer logs):
  a fresh-install villain; 02:47:20 the DbServer asked for map 71 (Mercy
  Island, cookie 2) at Enter Game and the dynamic start admitted it (no zone
  before). `_start_stock_map` -> `prepare_zone_runtime` built
  `local-login-server-<sid>-zones` (cold private mirror, then the shared
  server-data tree, 128704 files, "Preparing private map data directories",
  02:47:25-02:52:16, the guest loop blocked meanwhile), then
  `server_fx_catalog.install` refused the tree:
  `stock_travel.starts[0].failure` = "FX projection is restricted to the owned
  Atlas/Kings server namespace". The start was delinked; the DbServer logged
  `dbid 1 name "THORHERO" setNewMap failed MapFailed`, which deletes a
  just-created character (`doneWaitingChoosePlayerFailed`, `just_created`);
  (corrected in 0.13.61: it was no longer just_created, so it was unloaded
  and its row kept; see "0.13.61")
  the client showed "Map failed to start" and exited (code 0) 02:53:46.
  `initial_zone` still said `requested: false, attempts: []`.
- **Cause**: the FX namespace check (`local-login-server-<32 hex>`
  optionally `-kings-row`/`-atlas-park`) predates the shared tree of every
  other static zone (`-zones`, 5542e3d11, 0.13.57). No session had ever
  prepared that tree: CI's trip goes to 101 (Atlas tree), and the CI runtime
  has no all-zone package (`zone_tree_for` serves `zones` only with
  `zone_asset_document`; the retained 0.10.0 app's client-manifest has no
  zone package pins), so a CI Mercy Island trip would be delinked as
  `zone_not_served`. The unit test of a villain's Mercy Island start mocked
  `_spawn_map`, so preparation never ran there either.
- **Fix**: `-zones` admitted. `armport/tests/test_zone_travel.py`
  (`SessionServerTrees`, run by every build) derives the session tree suffixes
  from `local_character_server.py` and requires each to pass the FX namespace
  and other names to be refused; the released module fails it with the
  phone's message. The FX donor tests (`test_server_fx_catalog.py`, excluded
  from the retained host suites: authenticated public donor) also gain the
  case.
- **Reporting**: a first-zone start that fails before its server runs is an
  `initial_zone.attempts` row (`outcome: failed`, `failure`), `requested`
  true, and a `not_ready` event (the app clears its starting line and returns
  the wait) whose message names the reason. `prepare_zone_runtime` remembers
  its failure; a second Enter Game in the session repeats that reason (the
  partial tree stays where its data-cache receipt expects it) instead of
  "Shared zone runtime already exists".
- **CI**: the build now also runs `test_dynamic_initial_map.py`,
  `test_stock_travel.py` and `test_character_reopen_host.py` (none ran in CI
  before). Native coverage of the shared zone tree still needs the all-zone
  package in the CI runtime (1.9 GB archive plus client-manifest pins); not
  attempted here, so Mercy Island's server start is first proven on the phone.
- Not changed: the zones tree's data cache is never returned at cleanup
  (Atlas and King's Row are); the next session adopts it through
  `recover_stranded` while the old tree exists.
- **Chain at 81b6cdfc0** (one chain on x86/perf-round1, all passed on their
  first attempt). Build 42442419621: the libraries job's "Check bounded M3
  diagnostic reporting" step ran the ArmPort unit tests (`SessionServerTrees`
  included) and the three guard modules. Zone-trip runtime 42448320432 on it
  (2266 s): creation, map 1 cookie 2 ready 620.1 s after the stock start (the
  install's first MapServer start: 108 bins written, spawn to ready 455.8 s);
  reopen, no zone server before Enter Game (`local_atlas_startup` 0.0 s), map
  1 cookie 2 ready 135.7 s after the stock start, `/mapmove 101` (cookie 3)
  171.8 s, 2 arrivals, save passed; `client_logout_keys` kept 0 / aborted 0.
  Default runtime 42451345001 (1788 s); trusted runtime 42453750449 on the build
  (trusted bins applied, 1714 s); APK 42456241853 published
  `coh-atlas-gameplay-v0.13.60` (92315049 bytes, sha256
  3f2761d824bbef9b83450bd80a794bd51fd5b74317c6e16eaebdbf555fca0b67,
  signer 92955353…, the same as 0.13.50-0.13.59). Every CI start used the
  Atlas tree; `-zones` is first prepared on the phone.
- Version 0.13.60 (75); test sheet `THOR-TEST-0.13.60.md` (in place, Resume
  first character creation as a villain).

## 0.13.59: only the character's own zone, at Enter Game (Claude, 2026-11-07)

User, 00:28 CST, after the 0.13.58 test sheet: "I think you misunderstood my
instructions. I want the game to load whatever zone my character is in. Under
no circumstances should characters be transported to Atlas Park unless they
exist in that zone already, especially if I have a villain or other origin
characters that should start in their respective zones." Asked about scope, the
user chose one character at a time (THORHERO, any side) over several characters.
0.13.58 did not move the hero (the DbServer still sent it to its saved zone),
but it started Atlas Park's MapServer for every session and accepted a first
connection there.

- **No zone before Enter Game** (`character_zoning`, `DYNAMIC_INITIAL_POLICY`
  v2, `initial_zone` in the zoning report, `saved_startup.dynamic_start` is the
  same record): with stock travel and the ARM64 client, `initial_map_preparation`
  returns None for every saved map (Atlas Park included), `prepare_runtime`
  defers Atlas preparation (`character_zone_started_at_enter_game`), and
  `start_map` -> `defer_initial_zone` records the `local_atlas_startup` stage
  (the app's stage contract) with `zone_servers_started` 0. The DbServer's
  request at Enter Game (handleChoosePlayer -> handlePlayerContainerLoaded ->
  findBestMapByBaseId -> setNewMap -> startMapIfStatic) starts the zone through
  the zone policy; `tick_dynamic_initial` activates it once it ticks (attempts
  with outcomes, `request_to_ready_ms`, `mapserver_started`, startup timing
  `map_ready_observed`). `native_ready_record` is None until then;
  `poll_initial_map_startup` and `client_startup_assets_allowed` are true (the
  character list and the creator need only the DbServer).
- **Admission** (`zone_travel.ZoneTravelPolicy(admit=...)`,
  `admit_zone_request`): until the character first enters the world only its
  own zone may start: the saved zone or another instance of its world
  (`same_zone`: Atlas Park 1/101), one at a time (`not_the_saved_zone`,
  `initial_zone_already_starting`, recorded in `refused_requests`); a started
  zone of another world stops the session ("nothing was moved").
  `verify_initial_connection` requires the first connection on the activated
  zone. A failed start (900 s) is recorded and Enter Game may ask again.
- **Creation** (`LocalCharacterZoningCreationServer`,
  `character_creation_diagnostic.ZoningCharacterCreationDiagnostic`, chosen when
  COH_STOCK_TRAVEL=1, COH_EXTERNAL_MAPS=1 and the ARM64 client): the zoning
  machinery with the base creation identity (empty account, THORHERO ID 1, base
  rows check); the first request after the creator is the starting zone
  (determineStartMapId: 1 Atlas Park, 24 Outbreak, 71 Mercy Island, 70
  Breakout, 40 Precinct Five, 36 Nova Praetoria, 41 Destroyed Galaxy City).
  `creation_identity`/`creation_save_verified` accept a static zone with
  stock_travel; the zone's wait is added back to the 1200 s creator window
  (`initial_zone_wait_seconds`, bounded 1800 s). The legacy creation (x86, or
  no stock travel) is unchanged.
- **App**: `savedDestinationEvent` dynamic branch: port null, no
  `prepared_map_id`, any static zone; `characterConnectedEvent`/
  `characterCreationVerified`/`characterCreationAccepted` take the
  stock-travel flag for creation (`ClientRuntime.dynamicCreation`);
  `character_initial_zone` events show "Starting <zone>…" and keep it over the
  guest heartbeat until connection; zone display names (`ZONE_DISPLAY_NAMES`,
  `map_name` on connected/saved events, `ClientRuntime.zoneLabel`); messages
  for any side.
- **Trip timing rows**: `_start_stock_map` opens a `stock_travel_request`
  startup-timing row per trip (map ready at the first tick, client world at
  the arrival); before, a trip's spawn relabelled the session's initial row
  (see the 0.13.58 CI bullet). The first zone keeps the initial row
  (`initial_zone_started_by_dbserver_request`).
- CI: the zone-trip runtime now exercises the dynamic start for both sessions
  (CI's hero is a Primal hero, so Atlas Park is started by the DbServer's
  request after the creator and again at the reopen's Enter Game). Other
  starting zones and the saved-zone admission are unit-tested only
  (`test_dynamic_initial_map.py`) until the Thor test.
- **First zone-trip runtime at 18bdea026** (42397533053, 0.13.58 build's client):
  creation failed "Character logout delivery does not match this ready client
  or its save window". The dynamic start worked (request map 1 cookie 2, Atlas
  ready 609.9 s after the request including the deferred Atlas preparation;
  ResumeCharacter 18:06:22); `/quittologin` sent 18:07:53; at the failure
  (137 s later) the client was still in the zone at 2.1 FPS (helper dialog
  still drawn), no logout line. Same picture as r58t 42322788540 attempt 1 and
  shared-heap 41931773800 (all at ~2 FPS in the world).
- **Cause (source reading) and patch 0127** (ARM64 client: `game.c`, `input.c`,
  `input.h`, `clientcomm.c`): `checkLogoutProgress` cancels a logout on any key
  edge once the server's logout timer is back ("Press any key to abort",
  `commSendQuitGame(1)`). The frame order is inpUpdate (DirectInput buffer),
  windowProcessMessages, net, UI, checkLogoutProgress; Wine's dinput keyboard
  hook (dinput thread, `GetCurrentTime()` stamp) queues a press only while the
  window messages are pumped, so the Enter that sends `/quittologin` reaches
  the chat (WM_KEYDOWN) in frame N and becomes a DirectInput edge in frame N+1.
  At 2 FPS the server's logout update is back by frame N+1 and the stock client
  cancels its own logout; at 40-60 FPS (Thor) it rarely is. 0127 records the
  quit request time (`armportNoteQuitRequest`, timeGetTime) and each edge's
  DirectInput time (`inpEdgeTime`); a key pressed at or before the request
  does not cancel (`ARMPORT_LOGOUT_KEY_V1 ... logout_kept=1`), later keys still
  do. Native check `armport/tests/logout_abort_keys.py` (build workflow,
  extracted code, client frame order): patched keeps the logout, original
  fails with "aborted by key: 28" at 2 FPS; a later Escape cancels in both; 10
  FPS with a two-frame reply and Windows order pass in both. CI notices:
  `client_logout_keys` (kept / aborted) in the startup and failure details.
  x86 client (patches/ process) not changed yet.
- **Build 42402626384 at 154d8d814** (client with 0127; native check notice
  "ArmPort logout keys": patched PASS, original FAIL "aborted by key: 28").
  Zone-trip runtime 42410700974 on it: **creation passed** (DbServer request
  map 1 cookie 2 after the creator, Atlas ready 588.3 s after the stock start
  including the deferred preparation, save verified; `client_logout_keys`
  kept 0 / aborted 0, so the race did not occur that time). The reopen stopped
  at the client launch: "Early retry requires the still-live current owned
  native services" (`client_attempt_retry.service_identity` bound the Atlas
  MapServer, which the dynamic reopen no longer has before Enter Game).
  825bae059: the identity leaves the MapServer out only while the
  character's zone is still to start (`initial_zone_pending`) and none runs;
  the retry skips the Atlas tick check then (`zone_server_deferred_to_enter_game`),
  a zone started since forbids it; `client_attempt_retry.py` added to
  `CHANGED_RUNTIME` (`test_thor_apk_runtime_review` caught the omission).
- **Chain at 825bae059** (one chain on x86/perf-round1, all passed on their
  first attempt). Zone-trip runtime 42413409889 (client/data from build
  42402626384, same client source), 2232 s. Creation: DbServer request map 1
  cookie 2 after the creator, ready 579.7 s after the stock start (the
  install's first MapServer start: 108 bins written, spawn to ready 421.8 s).
  Reopen, the first CI run of the dynamic reopen: no zone server before Enter
  Game (`local_atlas_startup` 0.0 s, database server 9.8 s); the DbServer's
  request at Enter Game (map 1 cookie 2) was ready 136.1 s after the stock
  start (spawn to ready 133.3 s; the `initial_guest_service_request` row's
  257.7 s counts from the guest's start, before login); `/mapmove 101` (cookie
  3) ready 172.2 s, 2 arrivals, save passed. `client_logout_keys` kept 0 /
  aborted 0 in every session of the chain (the Enter race did not occur, so
  0127 rests on its native check). Default runtime 42416994465 (1816 s). Build
  42419983392 (native check again: patched PASS, original FAIL "aborted by
  key: 28"); trusted runtime 42426938668 on it (trusted bins applied, 1779 s);
  APK 42429765739 published `coh-atlas-gameplay-v0.13.59` (92315049 bytes,
  sha256 aa704cdf8767a9ccc159d3497d9d2e3fc3766a7f63d030569a9fc7781c316ec9,
  signer 92955353…, the same as 0.13.50-0.13.58).
- Version 0.13.59 (74); test sheet `THOR-TEST-0.13.59.md`.

## 0.13.58: Atlas Park first, the saved zone at Enter Game (Claude, 2026-11-06)

User, 14:59-15:20 CST: 0.13.57 "crashed during startup ... straight to the
Android home screen, no messages. The client splash screen had just appeared";
then "I'm going to completely wipe the app and start fresh ... I want the
initial map to be dynamic so we don't have an instance of this again."
Evidence: export 20261106-205910 is the setup report only (written 20:50Z,
exit history up to 20:47:47Z, reason 10 = the update). Recovered export
20261106-210545 (`previous-guest/latest-report.json`, status running, last
write 20:56:10Z): THORHERO saved in King's Row (`saved_startup` map 5, mapid 5,
staticmapid 5; left there by the 0.13.56 stop); stock travel requested; the
legacy saved start prepared King's Row (beacon graph 29.8 s, preparation
42.2 s) and overlapped the client: King's Row native ready 200.96 s
(20:56:10.258), client launcher started 20:56:09.2, no client window yet. No
guest failure; the Android process ended (no report finalized). Storage report
20261106-211807 has no exit history (format 1 inventory). The user's later
setup export 20261106-220022 has it: **20:58:39.314Z reason 3 (LOW_MEMORY),
importance 100 (foreground)**, app process PSS 242,631 KiB / RSS 364,340 KiB,
pid 32400 (the 20:47:55Z setup service pid), 2.5 min after the client launch.
Android's low-memory killer ended the foreground app while King's Row's
preparation and native start overlapped the client's own startup (Android
reported 10.9 GB available at setup; 0.13.52's per-process figures: client
~2.2 GB, each zone ~1.9 GB, DbServer ~0.4 GB). The 0.13.56 trip (client in
game, Atlas and King's Row resident) survived, which supports moving the
saved zone's start after the client's startup.

- **Dynamic initial map** (`character_zoning`, `DYNAMIC_INITIAL_POLICY`): with
  stock travel and the ARM64 client, `capture_baseline` keeps the saved zone in
  `saved_startup` (+ `prepared_map_id` 1, `dynamic_start`) but prepares Atlas
  Park (`active_map_id` 1), the start of every working session. At Enter Game
  the DbServer finds the saved static map not running (handleChoosePlayer ->
  setNewMap(is_gameclient=1) -> startMapIfStatic, no loading message to a game
  client) and publishes the start; the zone policy starts it like a trip.
  `tick_dynamic_initial` (each `character_evidence`) activates it once ready
  and before the first connection (no epoch, no arrival event), so the manual
  wait's `native_ready_record` reads that zone's stock log; the connection may
  also come on Atlas Park (findBestMapByBaseId for an Atlas instance).
  `start_map` refuses a dynamic start without the external-maps layer; a zone
  the runtime cannot serve stops at baseline. x86 client / station travel keep
  the legacy saved start.
- **Patch 0126** (ARM64 client, `initClient.c`): `dbChoosePlayer` waits 900 s
  (stock 90 s; the DbServer answers only when the map is ready, or with a
  failure message). The client's main loop is blocked during that wait (stock
  behaviour): the screen stays still.
- **Storage** (`ClientRuntime.ownedMountPoint`, `repairRuntimeMountPoints`):
  `/opt/coh/pgsql` is bound inside the `/opt/coh` bind (runtime `assets`);
  PRoot created the missing destination unreadable, the scan failed with
  errno 13 at `m2/runtime-9618983b6f58caae/assets/pgsql`, `complete` false,
  every category non-removable, 14 older runtimes kept (52.7 GB allocated).
  The launch now creates it 0700; a scan first repairs it in every runtime
  (`runtime_mount_points_repaired`) and the scan report carries
  `android_process_exit_history` (with descriptions).
- App: the saved-destination stage accepts `dynamic_start` (no port yet) and
  says the zone starts at Enter Game.
- Not covered by CI: CI's reopen starts with THORHERO in Atlas Park, so the
  dynamic path runs only in unit tests (`test_dynamic_initial_map.py`) until the
  Thor test (sheet step 6). The fresh install is the user's choice (uninstall
  deletes the hero and assets; asset packs coh-assets-v1.0.0).
- CI at 919e23760 (one chain, x86/perf-round1): build 42300265349 (server
  metrics) passed; zone-trip runtime 42312362966 (external maps 41883310382,
  stock travel) passed: `/mapmove 101` start ready 166.6 s (supervisor), 2
  arrivals, save passed. (The row labelled map 101, 192.7 s to map ready and
  339.6 s to client world, was the session's first Atlas Park start: a trip's
  spawn relabelled the initial timing row. 0.13.56-0.13.58's "client in the
  zone N s after the request" figures are those first-start times; 0.13.59
  gives each trip its own `stock_travel_request` row.) Default runtime 42316982535 attempt 1 failed in creation: "Costume
  page (HEAD/WEAPONS/Colors) not reached after body_next" (5 OCR checks,
  144.9-154.7 s after ready, menu 9.8 FPS); attempt 2 (re-run of the failed
  `interactive-guest` job) passed. Trusted runtime 42322788540 attempt 1
  failed in reopen: `/quittologin` sent 315 s after ready, no Atlas logout
  line, "Character logout delivery does not match this ready client or its
  save window" (120 s), client 2.1 FPS in world; reopen startup timings
  matched 0.13.57's r57t within 1 s; attempt 2 passed. Neither path changed in
  0.13.58 (creation UI; non-stock reopen). Both first attempts are open
  flakes, not proof of stability. APK 42329179898 (server metrics, trusted
  runtime, external maps) published `coh-atlas-gameplay-v0.13.58`
  (sha256 4feb75e2cd480f18d88e911c122e7d6c43728addb1c31b6dc77390c01e8dbb87).
- Version 0.13.58 (73); test sheet `THOR-TEST-0.13.58.md`.

## 0.13.57: a King's Row arrival no longer stops the session (Claude, 2026-11-06)

User, 09:22 CST (exports 20261106-152001/152038, screenshot): reached King's
Row by monorail, "Map loading, please wait..." stayed on screen, then a crash.
Evidence (entity log, guest report): Step 1 15:15:07Z (Atlas), supervisor
start of map 5 (cookie 2, tree `kings_row`, ready 185.6 s after launch),
Step 2 15:18:12, ResumeCharacter on City_01_02_1 15:18:33 (the trip worked;
both MapServers ran `-notwostagemapxfer`). The guest read the arrival at
15:19:40 (stock log route: the MapServer resends logs every 30 s) and 1.7 s
later failed the session: "Reopen phase budget lacks the current validated
graphical character".

- **Cause**: `character_zoning.character_identity` kept the station-era rule
  `map_id != 5 or monorail_enabled`; `_stock_arrival` sets `monorail_enabled`
  False (station queue off), so King's Row failed and the session was stopped.
  `SessionBudget.identity` already allowed it (`STATIC_ZONES`); CI's trip goes
  to map 101 and never reached the rule. Now `stock_travel` also qualifies.
  Test `test_stock_arrival_in_kings_row_or_another_zone_keeps_the_session`
  replays the device proof through the real `_stock_arrival` and
  `interaction_deadline` (fails with the old rule with the device's message).
- **App side** (same rule, would have failed a save or the next login in King's
  Row or any other zone): `ClientAcceptance.supportedCharacterMap`, the budget
  rows, `ClientSessionBudget.apply` and `ClientRuntime`'s proof check accept
  `stock_travel` with a static zone (1-999); the guest's connected/saved events
  carry `stock_travel`. Java case `stockarrival`.
- **Stale "Map loading" text** (patch 0125, ARM64 client): the DbServer sends
  only "loading on" (mapxfer.c, twice) and the load screen turns it off; with
  `-notwostagemapxfer` the load screen comes first, the notice arrived during it
  and stayed over the new zone. It is ignored on the load screen and cleared on
  the map handoff. The shelved x86 client is unchanged.
- **Third zone soon after a trip**: the arrival can be read up to ~60 s late, so
  `active_map_id` may still name the zone the hero left, and the policy could
  stop the zone the hero is on. `stock_occupied` asks the DbServer once
  (`-getstatus 3 1`, only when a request needs room; at most up to query 140 of
  160): the hero's map (still the origin during the request, InMapXfer) is the
  occupied zone, recorded as an arrival if it was unread; unknown → delink (the
  game says the map failed, the hero stays). `stock.occupied_probes` counts it.
- Also: `test_client_gpu_repair_evidence` compiles again (its harness lacked
  0.13.55's `stockTravelRequested`); two legacy 0.13.20 fixtures in it fail with
  or without these changes (not investigated).
- Version 0.13.57 (72); test sheet `THOR-TEST-0.13.57.md`.
- CI at 8050afca8: build 42246645668, stock-travel runtime 42263546136 (trip to
  101: instance ready 181.8 s, client world ready 352.1 s after the request, 2
  arrivals, interactive passed with no failures), default runtime 42270379862,
  trusted runtime 42276008129; APK 42281556221 published
  `coh-atlas-gameplay-v0.13.57` (prerelease; sha256 62221a94…f1c07). CI does not
  reach King's Row or a third zone, so the map-5 rule, `stock_occupied` and patch
  0125 on screen are unit-tested only until the Thor test.

## 0.13.56: zone starts no longer stop the DbServer; CI zone trip (Claude, 2026-11-05)

User, 14:30 CST (export 20261105-202806): logged in, took the monorail to
King's Row; "the client crashed immediately after the character boarded".
Evidence: the box was the **DbServer's** assertion (`weeklyTFcfg.c:120`,
`currentWeek`; built path `out\ex…` = the external-maps layer); the guest then
failed "Local DbServer exited during login"; the supervisor saw 0 requests.
`launcherCommStartProcess` builds every MapServer command with
`WeeklyTFCfg_getCurrentWeek` (launchercomm.c:1619), which devasserts when
`server/db/weeklyTF.cfg` has no entry; the pinned data lacks the file (schema
receipt `absent_in_pinned_data`). No CI run had ever made the DbServer start a
zone, so CI never reached it.

- **Fix** (`local_character_server.write_weekly_tf_config`): with the
  external-maps layer enabled, write one past week, no tokens (no
  `-WeeklyTFTokens`); recorded as `external_maps.weekly_tf_config`.
- **CI zone trip**: the stock-travel reopen (`StockTravelReopenInteraction`)
  types `/mapmove 101`, so the DbServer starts Atlas Park instance 2 through the
  same start path as a door or the monorail and publishes it to the supervisor;
  the host waits for the guest's `stock_travel` arrival (900 s), returns with
  `/mapmove 1`, then runs stuck/logout/save. On the CI donor's legacy MapServer
  the zoning flow reads Atlas CLIENT_READY with its log time (`legacy_ready`);
  the device keeps its immediate events. The failure notice adds the DbServer
  console tail and zone console tails.
- **What the CI trip found next** (round3, each run one fix):
  r56z 42105741978: the DbServer published map 101 (no assertion) but the
  supervisor refused `-productionmode` (shipped `MapServerParams`); r56z2
  42113734763: refused `-idleExitTimeout` — servercfg.c appends
  `-idleExitTimeout 30`, `-idleUpkeep 30`, `-MARTY_enabled` (and on other
  configs `-IsBetaShard`, `-dailyUpkeep A B`); all dropped, the session's own
  MapServers run without them (test rebuilds the whole command from the
  shipped servers.cfg). r56z3 42122856772: 101 started (cookie 2, ready 202 s)
  but the 4 KB notice hid why the hero stayed → "zone diagnostics" notices.
  r56z4 42130378619: the game did the trip (entity log: Step 1 00:08:09,
  Step 2 00:11:01, ResumeCharacter on City_01_01_2) but the guest missed it:
  after the connection is proved the base flow stops status probes →
  arrivals are read from the stock entity log (`_poll_stock_logs`). r56z5
  42136835869: round trip, stuck, logout and save all passed (arrival 101 in
  258.7 s host time, back in 84.2 s); the host's report check wanted the
  `local-character-atlas` process label → `local-character-zoning-1` accepted.
- **Loading screen at once**: the stock MapServer's two-stage transfer kept
  the hero in the world until the destination started; stock-travel session
  MapServers run with `-notwostagemapxfer` (svr_init.c): frozen,
  untargetable, invincible and the loading screen immediately.
- Version 0.13.56 (71); test sheet `THOR-TEST-0.13.56.md`.

## 0.13.55: the game's own zone travel, every zone (Claude, 2026-11-05)

User, 22:46 CST (0.13.54 test passed, temps high 50s/low 60s): a zone trigger
should show a loading screen and take the character out of the world; the
monorail should board at once, then load; open the whole zone list; full
screen 1280x720, launcher options in a floating movable touch icon, controller
mapping like trasc; "The biggest priority is nailing the map/zone server".
Answers: current zone + one spare; open all zones now (game's own rules).
Plan and stock-zoning evidence: `armport/notes/ON-DEMAND-ZONES.md`.

- **Guest** (`COH_STOCK_TRAVEL=1` + external-maps layer): station queue off;
  `external_map_supervisor.py` start policy (`zone_travel.py`: two zone
  servers, stop the idle one, 900 s start budget then stop + delink);
  `character_zoning` starts a request with `-cookie` and its own game options,
  follows arrival from the character status (`_observe_stock_move`).
- **Every zone**: `zone_index.py` (66 maps.db static zones; union of 380 extra
  collision leaves from the all-map closure evidence, all in the pinned
  zones-world-supplement); `prepare_zone_runtime` builds one owned tree for
  every zone other than 1/101/5 (no beacon graph yet); `register_zone`; a hero
  saved in such a zone starts there; reopen budget `static_zones`.
- **App**: `ClientZoning` follows `stock_travel` events (any static zone, no
  four-trip limit, no input block).
- **CI/APK**: runtime input `stock_travel` (reopen runs `--zoning`); APK input
  `external_maps_run_id` (run 41883310382) puts the external-maps DbServer in
  the APK. Version 0.13.55 (70). Chain `r55.sh`.
- **Interface** (merged ac9720c22): the game fills the window (still drawn at
  800x600 and scaled); launcher options in a draggable gear button
  (`ClientOverlayPosition`, Back toggles it); controller mapping
  (`ControllerInput/Profile/Bridge/Manager/Dialog`, 6 layers, deadzone, cursor
  speed; defaults = the 0.13.54 buttons; preset "COH power trays").
- **Published**: `coh-atlas-gameplay-v0.13.55` (pre-release), APK run
  42037755195 at 81e81ddd0, sha256 `bdd05be9…a4f68f00`, built from build
  41980185206, default runtime 41991355281 and trusted runtime 42020227060 (all
  passed at 81e81ddd0).
- **Stock-travel CI run (not a gate)**: r55z 42025310478 passed creation with
  the external-maps DbServer + `COH_STOCK_TRAVEL=1`, then the reopen failed:
  "No module named 'character_zoning'" (the CI guest's retained 0.10.0 donor
  predates the zoning flow). a1434f3ea (CI staging only; `android/` unchanged)
  adds the flow's modules. r55z2 42029819713: the zoning reopen started with
  `stock_travel.enabled` true, supervisor `session_maps` "dynamic", Atlas ready
  192 s, the client reached the world (help dialog), but the connection was
  never proven and the host's 20-minute bound ended it. Cause: the CI donor's
  legacy MapServer has no native events contract; the zoning flow's Atlas
  readiness needs `utc_ms` (`native_ready_record`), which legacy log records
  lack. The device uses the immediate events (export 20261105-043833,
  `character_reopen.immediate_native_events.enabled`). CI zoning coverage
  moves to step 2, which runs the Thor test server (it has the contract).
- Not covered by CI: an actual trip (needs a CI travel trigger; planned with
  the spare-server MapServer layer).

## 0.13.54: save check for ordinary play, shared server memory experiment (Claude, 2026-11-04)

- **Save check** (e6829cbae): `gameplay_progress()` composes the narrow reopen
  verifiers for ordinary play (training with its BuyPower records, automatic
  Inherent powers, temporary powers granted or expired, Inherent set-level
  normalization, slots with a level, experience/influence); see the 0.13.53
  Thor bullet below and `armport/tests/test_gameplay_progress.py` (exact rows).
- **Shared server memory** (3f725c8c9, owner's choice over the spare server):
  `COH_SHARED_HEAP=1` omits `-nosharedmemory` at both MapServer launches; app
  option off; CI input `shared_heap`; `pss_kib` per server every 30 s; console
  decision in `creation_report.shared_heap` / `zoning_report.shared_heap_consoles`.
  Notes: `armport/notes/ON-DEMAND-ZONES.md`.
- Chain at 3f725c8c9 (`r54.sh`): build 41906219190, default runtime 41920974522
  and trusted runtime 41926582700 passed creation and reopen. Shared-heap runtime
  41931773800 failed creation: "Character logout delivery does not match this
  ready client or its save window" (no Atlas logout line in 120 s; server ticks
  normal, client 0.26 FPS for 15 s after the quit; new-character welcome dialog
  twice in the stdio tail). Its console decision read all zeros: the first
  caller prints `initSharedHeapMemoryManager: SMAR_FirstCaller` inside the
  `reserving shared heap space...` load line, so the outcome lands on a later
  line. Cause of the logout miss unknown (shared heap or timing).
- APK 41935584201 failed before signing: "Unexpected runtime additions or
  removals" — `external_map_supervisor.py` (new guest dependency, fd73bc165) and
  `native_training_save.py` (changed) were not in `build_thor_apk`'s reviewed
  lists. Fixed, with `armport/tests/test_thor_apk_runtime_review.py` checking the
  lists against pinned 0.13.36 donor contents (`tests/fixtures/donor-0.13.36-runtime-pins.json`);
  it fails on 3f725c8c9 and passes now. Release notes' version slips corrected.
- Shared-heap evidence v2: the outcome is searched in a 4 KiB window after the
  marker, plus `first_caller`, `disabled_reasons` and a 6-line excerpt; zone
  server evidence (`shared_heap`, `external_maps`) moves to its own CI notice
  "zone servers <session>"; failure detail adds `client_dialogs`.
- **Published** (rerun chain `r54b.sh` at a66b533f6): build 41937339905, default
  runtime 41948749075 and trusted runtime 41952941661 passed creation and reopen;
  APK 41960891294 → release `coh-atlas-gameplay-v0.13.54` (prerelease, APK
  sha256 `9c24ef9e25cf1b35…`, version code 69).
- **Shared heap, CI verdict: not safe.** Runtime 41956900853 (v2 evidence):
  the first caller reserved the shared heap (`reserved 1024 MB`, active), Atlas
  ready 372.5 s / 106.5 s (creation / reopen) vs 357.1 s / 94.0 s without it.
  Creation passed; reopen failed "Ordinary stuck recovery lacked native
  stable-position proof within 180 seconds": client 0.04 FPS for 267 s, then the
  new-character welcome dialog 30 times; server ticks normal (max 27 ms), no
  logout line. With 41931773800 (creation logout lost) that is 2 of 2 shared-heap
  runs failing in session vs 4 of 4 passing without it. The option stays in the
  app, off; the test sheet says leave it off. Likely cause to study: the shared
  (read-only after load) definitions differ in use from private ones; repeated
  map-entry dialogs suggest the server re-sends the player's entry.
- **External-maps DbServer in a CI guest** (runtime 41961253764,
  `external_maps_run_id=41883310382`): the device lineage (manual Atlas level-up
  + map-request hook, layer `b9cb4391…`) passed creation and reopen; supervisor
  enabled, `manual_atlas_ack` true, 0 requests, no anomalies. The DbServer prints
  its acknowledgement only when it decides its mode at the first map start
  (`wine_external_maps.c`), and nothing asked for one (Atlas is the
  supervisor's own start), so `acknowledgement_observed: false` is expected.
  Requests need a zoning flow (CI monorail/zoning check or the Thor).

## 0.13.53: game audio (Claude, 2026-11-03)

User, 21:57 CST: "audio doesn't seem to be working and don't think it ever did
for the ARM client". Built on 0.13.52; its chain runs after 0.13.52's.

- **Cause:** the guest has no playback device. Wine's ALSA driver finds none
  ("Unknown PCM default"), so `DirectSoundCreate` fails and the client logs
  "Couldn't start DirectSound, continuing without audio" (every export since
  2026-10-27). The launcher's `-noaudio 1` is inert: `parseArgs` raises the
  command access level to 9 only in development mode, and the client runs in
  production (pigg) mode, so it is left unchanged.
- **Bridge (reused, device-proven):** the owner's TRASC ALSA plugin and
  protocol, `armport/audio/` (unchanged copies of `native/pcm_trasc.c`,
  `audio-LICENSE` MIT, `tests/audio_receiver.py`, `tests/check_audio_native.py`
  from trasc-server-android@99e8c86; also used by lsb-android on the Thor).
  ALSA `plug` converts to 48 kHz stereo S16_LE; the Android AudioTrack playback
  head is the clock; writes never block.
- **Build:** `armport/audio/build.sh` (runtime workflow, `guest-boot` job) builds
  it in `debian:bookworm-slim` (the guest rootfs release) and runs the native
  check against real alsa-lib (conversion, pause that empties the ring, drain,
  reconnect). Local x86-64 check against alsa-lib 1.2.11: PASS. The plugin
  rides in `armport-client.zip` as `armport-audio/libasound_module_pcm_trasc.so`
  (optional member, AArch64 ELF check on package and unpack).
- **Guest:** `ArmPortClient.client_audio_environment` (with `COH_CLIENT_AUDIO=1`
  and a listening `COH_CLIENT_AUDIO_SOCKET`) writes `armport-asound.conf`
  (includes `/usr/share/alsa/alsa.conf`, then `pcm.!default` → plug → trasc)
  and sets `ALSA_CONFIG_PATH`, `TRASC_AUDIO_SOCKET` and `winepulse.drv=d` for
  the client launch only. Any missing piece leaves audio off and is recorded in
  `client_audio`; it never fails the session.
- **App:** `ClientAudio.java` (lsb-android `AudioBridge`/`AudioPcmSession`/
  `AudioBufferPolicy`, statistics on a leaf lock, no log file) binds
  `<app>/s/audio.sock` (guest `/presentation-socket/audio.sock`, 0600, peer UID
  checked, at most 8 streams), requests game audio focus and reports
  `client_audio_bridge` in the Android report. Option "Game audio" (key
  `client-audio`, default on). The APK builder admits the one new source (25).
- **CI:** `interactive_host.py` runs the TRASC protocol sink (real-time playback
  head) on `work/socket/audio.sock` with `COH_CLIENT_AUDIO=1` (runtime input
  `client_audio`, default true), writes `audio-report.json`, and fails unless at
  least one stream connected without a protocol fault (non-zero samples are
  reported; they depend on what the scripted screens play). This is not
  evidence of audible playback.
- **Memory evidence:** `server-metrics.jsonl` process rows gain `rss_kib`
  (field 24 of `/proc/<pid>/stat` × page size) for the zone servers, DbServer,
  client and wineserver.
- **Independent review (before CI):** nothing serious in the session path.
  Fixed: the sink counted the client's shutdown disconnects (errno 32/104,
  simulated in about 5-67% of kills) as faults, which would have failed the
  chain; the plugin build step captured `step.sh` and hid its log; the
  listener thread outlived each session (now `Os.shutdown` wakes `accept`),
  and one failed connection ended later streams; the bridge no longer starts
  (or takes audio focus) for the x86 client. Left: push-triggered runtime runs
  read `client_audio` as off (same as `shared_server_data`; the chain
  dispatches). First run of the client's sound engine on ARM64 is the Thor test.
- **CI, 2026-11-04 (build 41819619887 at b6bf8dc64):** plugin native check
  PASS. Runtime 41832716509: the game opened one stream through the plugin
  (20.9 M frames, no protocol fault) but every sample was zero, because the CI
  client data has no sound files (reference assets, Atlas and reviewed zone
  supplements: none; "Loading sounds" takes 3 ms). Its creation session then
  failed the save window: logout typed, no save in 120 s (then the usual
  ownership-inspection cleanup symptom). Runtime 41838960420 at 6a8d7a08e
  added a **DirectSound tone probe** to the boot run (`armport/audio/dsound_tone.c`,
  the client's exact audio settings, packaged plugin, CI-only): **PASS, 1 stream,
  71,986 / 71,987 non-zero samples left/right** (1.5 s at 48 kHz). Its creation
  session failed the same way; the new failure-detail notice showed the client's
  last output "Could not find sound Element_Siren_02 … Element_Vehicle_03" and
  its frame rate falling from the 10 FPS cap to 3 and 2 FPS.
- **Cause and fix (patch 0124):** with DirectSound working, `loadSoundScripts`
  (sound_ambient.c) parses Atlas's ambient sound scripts; each script naming a
  sound the data lacks opens `winErrorDialog("Sound Script Errors")`, a modal
  dialog that stops the game's input. With audio off (all earlier runs) the
  loader returns first. The device holds all 6,219 original sounds, but a
  missing or renamed sound must never stop play: 0124 logs the errors
  (`ARMPORT_SOUND_SCRIPT_ERRORS_V1`) and bounds the 1,024-byte error text (a
  script naming many missing sounds overflowed it). Chain restarted at 7f0a59664.
- **CI with 0124 (build 41845880444 at c1b7097e1):** runtime 41868387083
  (default) and 41875359508 (trusted bins) **passed creation and reopen with
  game audio on**. Both: tone probe PASS (71,986 / 71,987 non-zero samples), the
  game opened 2 streams (38.6 M / 38.8 M frames, all silent: no CI sounds) with
  no protocol or teardown faults. The save windows that failed before 0124 now
  pass. The logged `ARMPORT_SOUND_SCRIPT_ERRORS_V1` lines are inside the report
  artifact, which cannot be downloaded here; from fd73bc165 the startup-detail
  notice reports them. Audio costs nothing measurable in CI: Atlas
  request→client world ready, creation/reopen, 1035/350 s and 1020/313 s
  (trusted) against 0.13.52's 1059/352 s and 1032/315 s. Build 41843958974 at
  7f0a59664 had failed its unit tests only (the sparse checkout lacked the
  qualified base DbServer manifest that the external-maps receipt test reads).
  APK 41881139424 (not published), then **published:**
  [coh-atlas-gameplay-v0.13.53](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.53)
  (APK run 41881826170 from runtime 41875359508, `COH-Atlas-Gameplay-0.13.53.apk`,
  92,249,277 bytes, code 68, sha256
  `e49b88e0faf003133a708eac8d6fbe1799fe3d01a59f119705a5d84217a02363`).
- **Thor, 2026-11-04 (exports 20261104-193441 and -195518, plus the startup
  export -193423):** the owner reports audio working well, King's Row fixed,
  the second start within target, temperatures mostly under 70 °C (the second
  session reached the low-mid 70s, then fell). Evidence: `ARMPORT_NET_CLOCK_V1`
  16 / 26 lines, King's Row lag 254-357 ms and 19-263 ms, one wrapped bias
  (4294317285) rendered correctly; no `ARMPORT_SOUND_SCRIPT_ERRORS_V1` on the
  device (all sounds present); folder index miss/scan 126.65 s (160,114 files)
  then **hit in 0.257 s**, client start 166.96 s → **40.60 s**; Atlas native
  ready 204.2 s / 149.6 s. King's Row prestart: session 1 rode after 48 s
  (prestarted loading, 134 s), session 2 found it resident (9.3 s to ready,
  return 5.9 s). In-world FPS median 53.2 / 39.2, p10 27.1 / 29.6 (0.13.52:
  36.6 / 43.1). Battery 29-35 °C / 35-38 °C, thermal status 0 throughout.
  **Memory (`rss_kib`, first device figures):** client 2,257 / 2,139 MiB, Atlas
  MapServer 1,814 / 1,782, King's Row 1,875 / 1,877, DbServer 415 / 417,
  wineserver 15; total peak 6,161 / 6,339 MiB with both zones; Android reported
  6,929 / 6,938 MiB available when King's Row started. So each further resident
  zone costs about 1.9 GB.
- **Both sessions report "failed" with the saves correct:** `Committed existing
  character rows changed after reopen: ents` (session 1: trained to level 2,
  bought `805/773`, got 7 stock automatic powers (Walk, Rest, Fitness_Fix,
  the four Fitness), a Day Job temporary
  power `temporary_powers.day_job_powers.day_job_movement_increase_lesser`, and
  XP/influence in the same session) and `: powers` (session 2: that Day Job power
  expired and the stock level-2 auto-set `powersetlevelbought` normalization
  ran). Each change has its own narrow verifier (training, temporary grants,
  normalization, rewards), but no combination is accepted, and expiry is not.
  Not a save failure; fix the comparator before the next APK.

## 0.13.52: King's Row interpolation fix, saved client file list, first-lookup links, opt-in test server (Claude, 2026-11-03)

User, 19:24 CST: "Work on 1 and 2 and 3, stage the update, wait for my results
to add more". 21:57 CST, with the 0.13.51 results: "Look through the reports,
see if there are additional fixes that can be made and integrate that into the
next apk in conjunction with the other updates you worked on". The staging
chain (build 41760267957 at `0395e3c16`, passed, folder-cache index check
included) was stopped before its runtimes and restarted with patch 0123.

- **King's Row NPC jumps** (ArmPort patch 0123, always on). Root cause found in
  `entrecv.c`: `local_time_bias` (U32) maps the client's clock onto the
  server's `abs_time`, and other entities are drawn at `client_abs`,
  `auto_delay` behind the newest update. `doMapXfer` resets the bias to 0; for
  a zone server younger than the client's clock (King's Row, started after
  the client was in Atlas) the correction `local_time_bias += dt * 3000.f` is
  negative. x86 converts that float to U32 modulo 2^32; AArch64 `fcvtzu`
  saturates to 0, so the bias stayed 0, `client_abs` was clamped to the
  newest update and entities jumped at the server's 4 updates per second.
  Atlas started before the client, so its correction was positive (matches
  the report: Atlas smooth on entry and return, King's Row jumpy on both
  trips, never on x86). With 0122 the client can reach its main loop before
  Atlas is ready, which would have exposed Atlas too. Fix:
  `armportWrapFloatToU32` (64-bit signed conversion, then modulo) for the
  bias correction and both `client_abs` computations; `ARMPORT_NET_CLOCK_LOG=1`
  (set by the guest) logs `ARMPORT_NET_CLOCK_V1 ... lag_ms=` every 30 s.
  `armport/tests/net_clock_interpolation.py` simulates Atlas → King's Row →
  Atlas with the extracted code (build step on the AArch64 runner; the
  original must lose the delay there; under `-fsanitize=float-cast-overflow`
  the original reports the -1.68e6 King's Row correction on any host).
  Audit: an IR scan of the ARM64 client and UtilitiesLib found 363 `fptoui`
  sites; the time, network, entity, sound and player ones were read and only
  this clock depends on the wrap (the rest are colours, sizes and UI values).

- **Saved client file list** (ArmPort patch 0122, app option on,
  `COH_CLIENT_FOLDER_INDEX`). `FolderCacheAddFolder("./data")` saves its scan
  to `<root>/armport-folder-cache-index.bin` and rebuilds the same nodes when
  `ARMPORT_FOLDER_CACHE_ID` matches. The identity (`armport_client_package.
  folder_cache_identity`) hashes the per-launch link validation digests (every
  source directory and link-target directory: device, inode, mtime, ctime),
  the link count, the overlay archive and executable, the skip and live lists,
  and the view-building code (`armport_client_package.py`). Installs publish
  new files, so any change moves a directory identity. The client also refuses
  on header, length, checksum or record errors (separators, NUL, long names),
  or when one of 64 sampled files changed size or time. It always scans live the
  overlay's root `bin/` (fresh mtimes every launch) and the writable cache roots
  `geobin` and `server` (`ARMPORT_FOLDER_CACHE_LIVE`; their files can be
  rewritten in place without a directory change), with the full scan's skip
  and exclusion rules. Log: `phase=index result=hit|miss reason=...` and
  `result=written`. `armport/tests/folder_cache_index.py` runs the extracted
  prepared code natively (20 checks; upstream fails) as a build step.
  160k-file fixture: 5.2 MB index, identical tree, 2 listings vs 1,642.
  Independent review (before CI): no serious defect; the CI step's pipe hid a
  failure, the in-place rewrite gap and the view-code identity were fixed.
  Left as is: merged directories carry the previous launch's folder times on a
  hit (nothing found that reads folder times), and the second server archive
  is in the client manifest, so it is hashed every launch.
- **First-lookup links** (`COH_SERVERDATA_FIRST_LOOKUP`, on). `runtime/serverdata`
  is now a directory of folder links (15 shared) plus `bin`, `geobin` and
  `server` linked to `../data/`. The Atlas console requests trees for 14 roots,
  none of these three, so they are looked up one file at a time and each first
  missed in `serverdata/`. Expected: some of the 5-6 s, measured only on the
  device (CI +0.8 s). Writes still land in `data/` through the links.
- **Opt-in test server** (`server_option` APK input, app option "Fast server
  start (test server)", off by default under a new key; the old `trusted-bins`
  key defaulted on). The APK keeps `game-package.tar.gz` byte-identical
  (`build_thor_apk` admits no change to it in this mode) and adds the admitted
  `thor_certified_startup` metrics server (0119 + trusted bins) as
  `game-package-trusted.tar.gz`. `select_game_archive` uses it only with
  `COH_TRUSTED_BINS=1`; the binding then pins that archive and requires the
  Thor variant with the reviewed switch. This server has never run anywhere
  (CI runs `retained_progress`); its first run is the Thor test. The data
  cache identity maps it to its shipping predecessor, so the mirror is reused.
- Chain (one at a time, one head): `armport-build` with `build_server_metrics=true` →
  runtime with the default server (evidence for the file list and links) →
  runtime with `server_run_id`, `trusted_bins=true` (qualifies the server
  package) → APK with `server_metrics`, `server_option`, published when qualified.
- **Published:** [coh-atlas-gameplay-v0.13.52](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.52),
  all at `424228d68`: build 41772928339 (interpolation clock notice: patched
  King's Row lag 197 ms; original `lag_ms=0 ... FAIL: no interpolation delay`
  on the AArch64 runner; folder-cache index 20 checks), runtime 41783448453
  (default server; passed; reopen bin writes 0; `phase=index result=written
  bytes=4651426` on creation, `result=hit reason=match seconds=0.127` for
  123,633 files on reopen; `first_lookup_private_folders` bin/geobin/server),
  runtime 41787724875 (`trusted_bins` applied; passed), APK 41791858823
  (`COH-Atlas-Gameplay-0.13.52.apk`, 92,236,989 bytes, code 67, sha256
  `047b0f4115e2c6ebfd51ec41ef40e6ce7c18fdcd17db04cb023086d48824f6a1`). The
  first chain (41760267957, `0395e3c16`) was stopped before its runtimes; a
  chain-script bug (the dispatch helper captured `gh workflow run`'s stdout
  as the run id) stalled the second after its build, and it was resumed from it.

## Thor test of 0.13.51 (user, 2026-11-03; exports 20261104-032856 and -035206)

Two sessions, both passed with proved cleanup; export -032851 is the runtime
setup. User: King's Row NPCs still "porting point to point" on both trips;
device temperature only into the 60s °C (0.13.50: 76 °C); no audio on the
ARM64 client (the x86 game they played before had audio and smooth King's Row).

| | Session 1 | Session 2 |
|---|---|---|
| Guest start → client launched (`startup_elapsed`) | 142 s | 161 s |
| King's Row trip (cold): Python / native ready / transfer | 51 / 238 / 45 s | 51 / 218 / 35 s |
| Return to Atlas (resident) | 8 + 40 s | 5 + 40 s |
| In-world FPS (windows above the 10 FPS cap) | mean 40, 77/111 ≥ 30 | mean 47, 70/72 ≥ 30 |

- **Tick probe:** King's Row completed 117-118 ticks per 4 s window in every
  sample (max gap 64-69 ms, 0-1 gaps over 67 ms), Atlas the same with max
  48 ms. The server was not starving; this led to the client clock (0123).
- **Station cap:** applied and removed twice per session, no error.
- **Priorities and CPUs:** MapServer threads at nice 0 (5 during preparation),
  client 7 of 21 threads at nice 19; CPU clusters 2.0/2.8/3.2 GHz.
- **Audio:** never worked in this app. The launcher passes `-noaudio 1`, yet
  the client still reaches `DirectSoundCreate` in `sndSysInit`, and Wine's ALSA
  driver finds no device in the guest ("Unknown PCM default"; "Couldn't start
  DirectSound, continuing without audio"). Every export since 2026-10-27
  shows the same. A sound path from the guest to Android is needed
  (planned: an ALSA plugin that hands PCM to an AudioTrack in the app); not in
  0.13.52.
- Pre-existing observation note in both sessions (and on 0.13.49/0.13.50):
  `Cache inventory: Linked private cache directory refused`.

## Thor test of 0.13.50 (user, 2026-11-03; exports 20261103-215454 and -220758)

Two sessions, both passed with proved cleanup; export -215435 is the runtime
setup. ARM64 client, fast mode, 60 FPS, shared data and the client skip on.
User report: King's Row reached; device at 76 °C while loading; King's Row NPCs
look laggy while the client is smooth; loading still long.

| | Session 1 (first start) | Session 2 | 0.13.49 session 2 |
|---|---|---|---|
| Tap → Atlas map ready | 762 s | 444 s | 297 s |
| Atlas Python preparation | 537 s (mirror 88, shared tree 282 one-time, beacons 75) | 202 s (mirror 84, beacons 75) | 70 s (checkout 9, beacons 25) |
| Atlas MapServer spawn → ready | 225 s | 242 s | 227 s |
| Client asset installs (incl. client data) | 97 s | 56 s | 98 s |
| Client folder scan | 160,114 files, 106 s | 160,114 files, 114 s | 212,496 files, 138 s |
| King's Row trip (request → in world) | 562 s (cold: Python 244 = mirror 103 + beacons 121; native 280; transfer 35) | not taken | failed |
| Return to Atlas (resident) | 50 s (prep 10, transfer 40) | | |

- **King's Row works:** Python preparation 244 s, inside the 420 s budget (cold
  mirror 103 s on the device, against 360 s+ on 0.13.49). Its cache was sealed
  and returned after owned cleanup.
- **Session 2 regression is a bug of mine:** the Atlas cache was refused with
  `Immutable Atlas child layout changed: .`. When the data root's mtime changes,
  `verify_changed_directories` expects every source top-level folder, but the
  generation omits the 15 shared folders. CI never changed the root mtime, so it
  never ran this path. Cost: cold mirror 84 s and beacon graph 75 s instead of
  checkout 9 s and 25 s. King's Row uses the same validator.
- **Shared tree lookup cost on the device:** Atlas `loading map` 34.1 s and
  King's Row 35.7 s, against 20.8 s on 0.13.49 (CI: +0.8 s). The engine searches
  `serverdata/` first, so every map-geometry open misses there first. Other
  phases are unchanged (story arcs 43-45 s, fx gap 35-36 s). *Correction
  (0.13.52 work): 20.8 s was 0.13.49's warm checkout; its cold copy (export
  -162813) took 29.0 s, and both 0.13.50 sessions were cold copies. The shared
  tree costs about 5-6 s per load, not 13 s.*
- **Client:** the skip saves 24-33 s of scan; the single-pass installs save
  about 42 s. Client preparation still starts only after Atlas's Python preparation.
- **NPC lag:** the King's Row MapServer ticked at 29/s throughout (same as
  Atlas), at 3-25% of one core; client 55-60 FPS there. The stay was about 80 s,
  beginning within a minute of King's Row's server becoming ready (3,768 entity file reads at ready).
  No cause found in the logs; the shipping MapServer does not report tick
  durations.
- **Heat:** the report has only battery temperature (31-35 °C) and Android thermal
  status `none` at Atlas start and ready. During the 9-minute station wait the
  client kept rendering Atlas at 30-60 FPS (dips to 15-20 during King's Row's load).

## Thor test of 0.13.49 (user, 2026-11-03; exports 20261103-162813 and -165322)

Two sessions on 0.13.49, both passed with proved cleanup. **They ran the ARM64
client** (`client_architecture_requested: arm64`, standard graphics, Turnip),
not the x86 client. Fast mode on; King's Row background start and idle priority
off. Export 20261103-162800 is only the post-update runtime setup (153 s).

| | Session 1 (first start after the update) | Session 2 (warm) |
|---|---|---|
| Tap → Atlas map ready | 728 s | 302 s |
| Atlas preparation (Python) | cold mirror 360 s, beacon graph 77 s | cache checkout 9 s, beacon graph 25 s |
| Atlas MapServer "Server ready (took …)" | 204 s | 222 s (.44: 287 s) |
| Client at login screen, from guest start | 850 s | 374 s |
| Client folder scan (212,496 files) | 127 s | 138 s |
| In-world FPS, 60 cap (windows above the 10 FPS inactive cap) | mean 48, median 49, 91% ≥ 30 | mean 45, median 42, 97% ≥ 30 |
| King's Row trip | failed | failed |

- **FPS goal met on the ARM64 client** (.44 ARM64: 25.6 FPS mean). The 60 FPS
  world-entry cap applied (`maxfps=60` windows). The x86 client is still
  unmeasured.
- **King's Row:** both trips failed with "Kings Row Python preparation timed out
  before native startup" at the 420 s Python budget (`python_inputs`). It was a
  cold King's Row mirror both times. Session 1 timed out mid-mirror, so no King's
  Row cache generation was sealed for session 2. Not caused by an unchecked
  option. The background start option has no 420 s cap until a trip is
  requested, so it is the stopgap.
- **Why session 1 was cold:** a generation for this exact identity existed
  (refused `…-6c6678d9…`, prior owner did not prove cleanup). Stranded recovery
  refused with `[Errno 2] … '/proc/26417/status'`: an ancestor exited during
  `foreign_processes`' parent walk. Fix: end the ancestor walk at a vanished
  ancestor (unwalked ancestors still count as foreign, so it stays fail-safe).
- **Mirror cost on the Thor:** cold mirror 360 s against 218-230 s on .44; CI
  shows fast mode does not speed the mirror (99.5 s off, 103.7 s on). The shared
  read-only tree removes it.
- **Prepared caches load on the device** with the shipping MapServer: spawn
  definitions 4 s (CI's retained-progress variant: 110 s).
- **Warm critical path is the client.** Session 2: Atlas ready at 297 s from
  guest start, client login screen at 374 s. The client waits for Atlas's Python
  preparation (client assets start at +70 s), then spends about 117 s on
  per-session asset installs (visual 28 s, animation 10 s, all-zone assets 48 s,
  audio 4 s, client data 8 s), then 190 s to start (138 s folder scan).
- **Wine priorities** (`character_zoning.wine_priorities`, one sample each,
  `RLIMIT_NICE` 40): `CityOfHeroes.exe` 14 threads at nice 0 and **7 at nice 19**;
  MapServer, DbServer and wineserver all at 0. Wine applies the dev-mode IDLE
  class to the client's later threads (likely loaders), not to its main thread.
  FPS is already good; the lead now concerns loading. Only one sample was taken,
  because the zoning tick stops calling it after a failed trip.
- **Cleanup:** complete in both sessions (5 dead leaders with live tasks, all
  signalled). The fallback lineage sampler mostly fails on its own 1 s budget
  ("Wine ownership task inspection timed out", 854 and 561 times), but still
  authenticated 19 and 14 groups.

## Performance rounds (Claude, 2026-11-03)

PR #11 (`x86/perf-round1` → `x86-track`); `x86/perf-round3` is the working
branch and is merged into round 1 for each release. Evidence and numbers:
[PERFORMANCE-PATH.md](armport/PERFORMANCE-PATH.md) and issue #10.

- **Published (use 0.13.49):** pre-release
  [coh-atlas-gameplay-v0.13.49](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.49)
  (APK 41647713812, qualifying runtime 41642095387 at `0f13f5741`, sha256
  `9520fb31…`). It is 0.13.48 plus read-only device evidence, and reuses build
  41616229359 (no native patch changed). Earlier:
  [0.13.48](https://github.com/Russianranger/coh-android/releases/tag/coh-atlas-gameplay-v0.13.48)
  (APK 41636249551). Neither has run on a device.
- Fast mode (PRoot seccomp) is on by default from 0.13.48. In CI it cut MapServer
  startup by 26-32% (41588867344 off vs 41584980465 on).
- **Servers in the published APKs:** the shipping MapServer that ran on .44,
  where the prepared server caches installed. Trusted prepared bins
  (`patches/mapserver-trusted-bins/0001`) need the instrumented MapServer, so
  they have no effect there. CI A/B with the instrumented retained-progress
  variant (41610459604 off, 41605600310 on): reopen Atlas 130→94 s.
- **CI's fresh-character re-parse is CI-only.** CI executes the retained-progress
  metrics variant, which has no startup receipt, so `verify_mapserver_compatibility`
  falls through to the monorail check and refuses the prepared caches
  (`Monorail native identity differs`, 41630365042). The MapServer then rewrites
  106 bins, including the archive's `spawndefs`/`storyarc`/`contacts`. A metrics
  APK would embed `thor_certified_startup`, which the startup contract accepts,
  but that variant has never run.
- Background King's Row start, idle priority for a resident MapServer,
  stranded-cache recovery and the 60 FPS world-entry cap; see X86-THOR-TEST.md.
- Shared read-only tree, CI probes (PERFORMANCE-PATH.md): level 1 (`scripts.loc`,
  52,149 files) passed with no side effects, per-start mirror 106 → 74 s
  (41636702283). The wide level (17 folders, 136,019 files) passed with a 28 s
  mirror, but it rebuilt `sequencers.bin` and 21 power/salvage bins on every
  start (sequencer phase 36 → 240 s; 41648097743). Probe the folders one at a time.
- Leads from source reading, with evidence in 0.13.49: the dev-mode client asks
  for `IDLE_PRIORITY_CLASS`, which wineserver turns into about nice +11 when
  `RLIMIT_NICE` allows (the Thor reports 40) (`character_zoning.wine_priorities`);
  the client loads its data folders before choosing the on-demand folder-cache
  mode (full 141 s scan; fix needs a client rebuild); the cleanup defect's
  failing /proc read (`live_lineage_observation.unavailable_by_operation`).
- Next: the Thor test of 0.13.49; per-folder shared-tree probes; a
  client-priority fix if the samples show it; a cache-compatibility path for
  the retained-progress variant so CI creation matches the device; a native
  60 FPS launch cap and the folder-cache order with the next client rebuild; an
  x86 FPS baseline on the Thor.
