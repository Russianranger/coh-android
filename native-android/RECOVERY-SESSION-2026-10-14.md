# Session-client recovery and collision batch preparation

The remote native-android checkpoint was still
`537f5b1a451a701018537b93631512b20cfb2b33` at recovery. Its latest operation is
the qualification/handoff record committed at 2026-10-14 21:17:55 UTC. Session
run 38637681649 finished successfully at 21:11:12 UTC; portable-core run
38637681101 at 21:08:01 UTC. All 88 available branch workflow runs were checked
for non-completed status; none was queued or running. No native build, emulator
or test worker appeared in the available process view; no process was killed.
The former agent's private reasoning/UI step is not observable. Evidence
supports a completed qualification awaiting the physical handoff, not a blocked
build. There is no evidence identifying a specific frozen worker to restart.

The available source snapshot lacks Git metadata. An **untruncated**, exact
native subtree comparison found 519 matching tracked files, zero changed files,
and one missing older documentation file (`RECOVERY-2026-10-14.md`). It is
present remotely and was read; its absence is not a deletion. The 236 additional
files are generated fixture assets, codec/source acquisition dependencies,
Python caches and host/Java qualification outputs. No unpublished native
implementation beyond 16–18 was found. Unrelated partial source-tree omissions
were not interpreted as changes. The recovered source and all original build,
failed-run, final-run and emulator evidence directories remain untouched.
`evidence/phases19-21/recovery-summary.json` records this audit and the digest
of its complete local inventory.

The qualified APK was rehashed from the existing final artifact. It remains
`CoH-Native-Session-Client-0.1.0-arm64.apk`, 2,139,651 bytes, SHA256
`eb763d8c6e5354da06a336e8fe09a244a893755e82ef708ea1d2139dc17b8634`.
[Download the existing final artifact](https://github.com/Russianranger/coh-android/actions/runs/38637681649/artifacts/11929666705).
Runtime source `e88a02b284de16ed6f7caf1e6b689f2e85d0b6e8`, qualification driver
`5cea4041c8c822b6a983f815e3b4814a2e0d3b5a`, original build receipts and qualified
packages were not changed or rebuilt. Physical 13–15 acceptance is preserved;
**physical 16–18 acceptance remains pending**.

New work prepares gate 19's source collision acquisition boundary and the
integrated 19–21 dependency/acceptance plan. A bounded host `PolyCell` offset
decoder reads the authentic bench's 500-byte disk grid without reconstructing
host pointers. Five new tests passed: authentic asset/hash/triangle coverage,
all proper prefixes, leaf/children/shared-cell handling, malformed records,
cycle and depth rejection. The authentic grid contains three cells and 216
references covering all 188 triangles. Source files were matched to exact
repository Git blob IDs; source member size/CRC/SHA was verified with bounded
release ranges. [The preparation contract](tools/collision_fixture/README.md)
explains source flag reconstruction, the actual WALK call chain, locomotion
closure, and all unqualified boundaries. Dedicated new CI runs these host
checks. Existing portable-core CI may also run because its branch path filter
covers all native changes; no session APK rebuild or prior emulator replay is
requested by this change.

Gates 19–21 are **prepared, not runtime-complete or physically qualified**.
Their next steps are authentic Atlas ground/obstacle and flags/transform
closure, grounded source WALK/contact trace parity, and complete authored
RunPre/directional/interruption transitions in the existing Session Client.
No new Android probe or fabricated terrain/collision has been introduced.

Use the unchanged [combined Thor test](session-client/THOR-TEST.md) now. Install
and open the Session Client; inspect actor/bench depth, short forward and
left/right/back input with release, right-stick/drag camera, Recreate state,
held-input Home/release/return/fresh-input, Reset, then Export report. Return
`COH-NativeSession-*.json` and any visual/controller observations. Pass-through
NOCOLL motion and limited directional animation remain expected in this APK.
No account/server/import is needed. Do not wait for gates 19–21 to provide this
report, and do not interpret their preparation as acceptance of 16–18.

All writes in this recovery target native-android only; main, the conventional
launcher/client, existing asset packs and user data remain unchanged.
