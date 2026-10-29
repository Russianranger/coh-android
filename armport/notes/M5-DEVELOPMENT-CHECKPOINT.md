# M5 development checkpoint — 2026-10-29

PR #8 candidate 0.13.45/code 60 at `0bf31c81b1b5a9f8427b4692c623702b30e7029e`
passed build 40776745390, retained runtime 40786315414 and APK 40791416254.
Artifact 12860779714 was independently inspected; exact evidence is in
`../evidence/0.13.45-qualification.json`. Claude review 5692088051 approves this exact diagnostics APK for Thor handoff. No .45 Thor result or M5 acceptance.

This separate `armport/server-metrics` branch develops 0.13.46/code 61:

- Native 0119 was exported through patchwork. Actual retained-source ASan/UBSan
  cases and the original-code runtime negative control pass. It measures
  post-ready main-thread tick/loop and inclusive outer fileAlloc durations.
- Optional build jobs authenticate both historical donors and their exact source
  lineages, execute source fixtures, then build the two Win32 MapServers serially.
  The modern baseline needs actual pinned animation inputs; first CI still must
  execute that full preparation and both Windows builds.
- Runtime/APK integration authenticates exact run/head/package identities.
  Retained creation/reopen sessions bind distinct identities; the modern Thor
  server remains explicitly build/source-only until runtime/device evidence.
- Guest readers authenticate the current PE before historical metadata reuse.
  Native console export is bounded and separate from CPU/progress counters.
- The bounded ARM64 enhancement policy preserves all prior rows, accepts only
  new inventory slots with valid native fields/current readonly definitions,
  and retains existing connection/logout/identity/committed-SQL checks. It does
  not prove award causality or definition identity since preparation.
- 415 ArmPort unit tests and 61 existing saved-startup/zoning/monorail tests pass with the local JDK compiler launcher and pristine
  c86a579 baseline. Independent workflow review and syntax/whitespace checks pass.
  Detailed scope and dispatch inputs: SERVER-METRICS-DEVELOPMENT.md.

Build 40805020119 is running at frozen dd9d755bd; its downstream runtime/APK
chain is held by comment 6486287635. The separate sampler-review-fix branch
addresses review P2/P3 and adds bounded observational launch history; it needs a
new full chain after the current build finishes. No .46 runtime/APK/Thor result
exists. Details: M5-SAMPLER-REVIEW.md.
No performance, startup, battery or thermal improvement is claimed. Native
ARM64 servers and prior-zone retirement remain plans, not implemented features.
Wine request counts remain unavailable. Esync/runtime changes need a proposal
before implementation.

The connector cannot dispatch workflows; Claude offered to dispatch exact PR #8
CI requests. Ask for the experimental branch at its published full SHA, with
build_server_metrics=true; after success use that build ID for client/data/server
runtime inputs, then its runtime ID for APK m4_run_id with server_metrics=true.
Keep every stage serialized, commits [skip ci], and publish exact artifact/digests
before asking Claude to approve APK handoff. No releases or protected changes.
