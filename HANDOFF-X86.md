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

## 0.13.52 (staged, not published): saved client file list, first-lookup links, opt-in test server (Claude, 2026-11-03)

User, 19:24 CST: "Work on 1 and 2 and 3, stage the update, wait for my results
to add more". So the APK is built (`publish_release=false`) and published only
after the 0.13.51 results.

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
- Chain (one at a time): `armport-build` with `build_server_metrics=true` →
  runtime with the default server (evidence for the file list and links) →
  runtime with `server_run_id`, `trusted_bins=true` (qualifies the server
  package) → APK with `server_metrics`, `server_option`, no publish.

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
