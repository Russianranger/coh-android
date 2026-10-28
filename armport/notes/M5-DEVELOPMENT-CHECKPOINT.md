# M5 development checkpoint — 2026-10-28

PR #8 candidate preparation is `0bf31c81b1b5a9f8427b4692c623702b30e7029e`
on `armport/m5-thor` (0.13.45/code 60). Its native patch tree remains
`992ed11b116a2db10179c8507ce61e3f37b27840` through 0118. All 292 local ArmPort
unit tests passed. No candidate CI, APK, Thor measurement or Claude handoff
approval has been obtained. STATUS.md and M5-THOR-TEST.md describe that candidate.

This separate `armport/server-metrics` branch is experimental development. It
must not be packaged as 0.13.45 or merged into the candidate while qualification
is pending. It adds:

- Native 0119, exported through patchwork, and an extracted-source CI check.
  Eight actual staged-source cases plus an unpatched runtime negative control
  pass locally. The plain ArmPort prepared tree has seven applicable cases.
  Source identity tests: eight passed. See SERVER-METRICS-PRODUCER.md and the
  bound `../evidence/server-metrics-host-checks.json`.
- Exact source adapters and a MapServer-only packaging tool for two distinct
  lineages: retained 0.10 progress and the Thor certified-startup server.
  Package tests: 22 passed. Guest readers and native Windows build jobs are
  not wired; no replacement MapServer PE has been built. The full modern source
  stage still needs the pinned animation inputs. See SERVER-METRICS-DEVELOPMENT.md.
- A bounded ARM64 existing-character enhancement policy: preserve every prior
  enhancement exactly and allow only new free inventory slots with native field
  bounds and zero fresh-award auxiliary payload. Existing connection, logout,
  character identity, committed SQL and all other save checks remain required.
  Tests cover current readonly definition paths, malformed rows, x86 refusal,
  same-name changed definition bytes and replacement during observation.
  This observes additive committed inventory. It does not prove defeat/award
  causality, native effects or definition byte identity since preparation.
- Source-backed SERVER-LIFECYCLE-PLAN.md and NATIVE-SERVER-BRINGUP.md. These are
  plans, not implemented server retirement or a native ARM64 server port.

## Immediate pipeline blocker

The GitHub connector supports repository updates and read-only run inspection,
but exposes no workflow-dispatch operation. The shell has no authenticated
GitHub credentials. The Actions UI did not expose Run workflow for this workflow.
No active run was found. Dispatch from an authenticated Actions environment:

```sh
gh workflow run armport-build.yml --repo Russianranger/coh-android --ref armport/m5-thor
```

After success, dispatch armport-app-runtime on the same branch with both
client_run_id and data_run_id equal to that build. After its success, dispatch
armport-thor-apk with m4_run_id equal to that runtime run. Record exact run IDs,
artifact ZIP digest, APK bytes/hash and provenance before asking Claude to
approve handoff. No competing CI, releases or protected-branch edits.

Continue native/server integration independently while the candidate runs;
update version and provenance only when selecting a later candidate. CPU/tick
rates, battery, thermals and startup improvements remain unmeasured on Thor.
Wine request counts remain unavailable in the shipping lane; esync and routine
Wine counter instrumentation require a pinned-runtime proposal before changes.
