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
