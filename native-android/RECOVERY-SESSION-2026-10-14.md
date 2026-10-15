# Recovered Session Client checkpoint and continuation

The remote checkpoint at recovery was
`537f5b1a451a701018537b93631512b20cfb2b33`, recording qualified gates
16–18. Session workflow `38637681649` and portable-core workflow `38637681101`
had already completed successfully. The runtime source was
`e88a02b284de16ed6f7caf1e6b689f2e85d0b6e8`; the final qualification driver was
`5cea4041c8c822b6a983f815e3b4814a2e0d3b5a`.

The recovered source snapshot has no Git metadata. Exact Git blob comparison
found 519 matching tracked native files, no source differences and one absent
older recovery document. Its 236 additional generated files, source/asset
caches and test outputs were retained in the recovered snapshot. No unpublished
implementation beyond gates 16–18 was found. The original inventory identity
and comparison are retained in
[recovery-summary.json](evidence/phases19-21/recovery-summary.json).

No native build/test worker was present in the available process view. No
queued or running branch qualification remained at recovery, and no process
was terminated. The observable trail stops after publishing successful gates
16–18 qualification and the physical Thor handoff. It supports a missing final
handoff or wait for device testing, not a demonstrated stuck build. A previous
agent's private reasoning and inaccessible session state cannot be reconstructed
from these files.

The user subsequently supplied the real Thor report and confirmed “Everything
worked.” Its exact APK hash, AYN Thor/Adreno740 identity, 8,142 frames, zero
transform/non-tie depth mismatches, physical stick coverage, five contexts and
recovery/export evidence were recorded at
`8e83f2343f29c7b4baee7876268c5ccb1e8b01b4`. The raw report and original hosted
qualification remain unchanged. Gates 13–18 are accepted within their documented
scope; the recovery-summary's earlier pending status is historical.

Continuation implements [gates 19–21](PHASES19-21.md) in the same native Session
Client source. The exact accepted character, rig, morphology and benchmark are
recovered from the qualified APK rather than rebuilt. Its original
[Thor instructions](session-client/THOR-TEST-16-18.md) and APK remain available
for rollback. The new debug package installs alongside it with a pinned public
test signer, preserving app data and the conventional client. No import,
migration or deletion is performed.

The new runtime is `8629d6a7c4863f492ee50bc030c21c2b2d2f0c3d`. Source/host
checks, the full 1,585-file source trick audit, ARM64/x86_64 builds, lint,
signatures and exact package checks passed in
[workflow 38656997946](https://github.com/Russianranger/coh-android/actions/runs/38656997946).
Its ARM64 APK is **2,344,055 bytes**, SHA256
`2d59e2b39af99facc6f3ac26b310aeba85802542efabb1e71d90e2d33a00de92`:
[direct download](https://chatgpt.com/api/library/files/libfile_1f69175230b08191b4c8ea65e369139c/download),
[original artifact 11936304916](https://github.com/Russianranger/coh-android/actions/runs/38656997946/artifacts/11936304916).
Later driver-only runs reuse these exact APKs and original successful source
receipts instead of rebuilding unchanged code.

Failed source-pin, source-layout and NDK compile stops, followed by camera,
brief-RunPre observation and release-settling harness failures, remain under
`evidence/phases19-21/failed-*`. An earlier preserved stop is
[failed-slide-driver](evidence/phases19-21/failed-slide-driver/failure.json):
workflow `38660735982`, driver `c47ba93017ca00a5cfbaa8494948e120210f6649`,
failed a grounded-slide assertion after prolonged diagonal input. Its events
retain a grounded slide, followed by a later ungrounded sample; no exact
intervening crossing point is claimed. Native failure and GL/EGL/transform errors
remained clear. Six individual emulator checks passed, and six release-settling
windows passed, but the combined emulator procedure is still pending.
Portable-core workflow `38660735985` passed separately.

Physical gates 19–21 remain pending until a new Thor report and observations
are received. The [new combined procedure](session-client/THOR-TEST.md) records
the current package and bounded test scope. The accepted
[0.1.0 rollback artifact](https://github.com/Russianranger/coh-android/actions/runs/38637681649/artifacts/11929666705)
remains unchanged. All commits stay on `native-android`; no merge to `main` is
part of this work.

The later source/build-qualified APK remains byte-identical; no rebuild followed
runtime `8629d6a7c4863f492ee50bc030c21c2b2d2f0c3d`. Two retained startup
attempts showed system data clearing removing the newly launched Activity.
The fresh-install driver `c32f6cb9b4d276565d95093679187847f46c78e9` removes
that unnecessary clearing and verifies package/report absence and exact Activity
launch. It passed that correction on Android in session run `38663997193`.
The same run passed rendering and forward/backward release settling, then stopped
at the left-direction grounded predicate after prolonged travel in the selected
scene. Its original failed report is retained in `failed-directional-ground`.
Complete emulator qualification remains open; no physical acceptance is inferred.
Portable-core workflow `38663997261` passed. No qualification job remains running.

The next three milestones are closure of gates 19–21 emulator/Thor acceptance,
larger bounded authentic Atlas loading/streaming, and native live-server session
and replicated actor-state foundations. The missing authored floor detail texture
and unqualified sustained performance remain explicit limitations.
