# 0.13.37 client and cold-zone development

Status: development; no successor APK or physical speed result is claimed.
The exact audited 0.13.36 APK source is
`3570430cefdb15d9b239563e85cccf4d8fe6f32e`. Documentation recovery continued at
`31c9f75cc80907ccb49e75d6323b9adac9559386`. Main and draft PR #1 remain unmerged.

## Physical baseline

The [read-only report analysis](android-evidence/coh-physical-startup-0.13.36-analysis.json)
preserves the three uploaded archives and the event boundaries used below.

| Phase | First session | Second session |
| --- | ---: | ---: |
| GPU prerequisites | 26.285 s | 15.769 s |
| Native Game startup | 264.461 s | 264.197 s |
| Texture headers, within Game startup | 39.542 s | 38.494 s |
| Group catalog, within Game startup | 24.390 s | 37.763 s |
| FX, within Game startup | 27.925 s | 34.756 s |
| SCRIPTS.LOC, within Game startup | 18.381 s | 17.417 s |

Atlas-to-Kings request-to-native-READY took 399.273 s, with observer confirmation
at 412.881 s. Kings native initialization took 285.591 s, including sequencer
88.862 s, FX 46.330 s and story 40.962 s. The return reused the already resident
Atlas process: 82.844 s to native READY and 96.891 s to observer confirmation.
Resident reuse is distinct from validated cache reuse in a newly started process.
Nested phases and concurrent Map/Game phases must not be added together.

The next testing targets are client startup below 60 s and transfers no longer
than about 90 s. The long-term zoning target remains 30 s. Host qualification
cannot establish any of these physical targets.

Both ordinary native saves and final PostgreSQL comparisons succeeded. The last
saved location in the reports is Atlas Park, map 1, position
`(688.8623, 74, -1407.0708)`, at 20:55:35 UTC. Each reopen must still query the
existing authoritative profile; no destination or position may be hardcoded.
Send Text worked in these sessions. Assets 1.0.0 and all four volumes stay intact.

## Isolated native candidates

The completed Map animation metadata experiment uses only the stock metadata
request after native dependency validation. Its genuine native host pair reduced
combined move validation/attachment from 6.018023 to 0.662457 s and preload from
18.185 to 14.634 s. This one ordered pair does not establish full-world,
behavioral collision, memory or Thor qualification.

The client candidate gathers and sorts a bounded directory batch before the
stock FolderCache inserts metadata. Activation requires the exact native
consumer, an empty initial child list and no callback. Populated lists and
refusal paths retain stock behavior. Source fixtures identified roughly
29 million comparisons for the actual scripts tree; reducing those comparisons
is a hypothesis until an actual Game runtime comparison passes. Retained batch
storage is at most 5.0625 MiB; possible old/new allocation overlap is 7.59375 MiB
before allocator overhead. Payloads, provider precedence and freshness decisions
remain qualification gates.

Separate build/runtime receipts must identify the actual source, binary, provider
generation, native decisions, renderer, owned cleanup, memory and timing scope.
Successful native builds and prepared providers are reused with exact byte
authentication. Failed or cancelled qualification is retained as failure evidence.
Native candidates remain nonshipping until their appropriate gates pass.

## Actual client qualification outcome

The genuine paired run [38488820206](https://github.com/Russianranger/coh-android/actions/runs/38488820206) passed six Game launches: two retained, two constructor candidates and two original Cg observers. The [factual receipt](android-evidence/native-client-folder-sort-0.13.37-qualification.json) keeps original build and recovery identities. Providers, helper/animation/texture inputs, current software renderer, ordinary cache bytes and owned cleanup remained equal. The candidate actually sorted 184 batches / 98,243 entries per run.

Warm retained native console-to-all-data was 15.167 s; candidates were 15.421 / 15.563 s. Accepted current readiness was 19.236088 versus 19.217011 / 19.482232 s, with registry/OCR observation timing distinguished. This proves startup compatibility, not a material host speed benefit. No physical, cold-cache, character-world, visual or measured process RAM result follows. Both Cg cases used 249 OBJECT / zero SOURCE creations, about 0.17 s create and 0.50 s immediate load; later shader loads and device driver caches remain unmeasured.

The first genuine stock Atlas world reached readiness at 13.776624 s in [38489822992](https://github.com/Russianranger/coh-android/actions/runs/38489822992), but the overall run failed because 506 native-generated object-library `.bounds` files were outside the harness cache census. Original sources and SDK inputs remained unchanged; no candidate or Kings case passed. [Partial/failure evidence](android-evidence/native-map-world-bounds-failure-0.13.37.json) preserves that distinction. Reviewed source `04b7a623ef21d7ad48774a58b3122c69ae07f46b` adds only the fixed native bounds closure and stopped-output evidence. All 32 focused tests passed. Its run [38494199595](https://github.com/Russianranger/coh-android/actions/runs/38494199595) failed after a second genuine stock Atlas ready witness (15.471552 s; owned status/ticks 16.844 s). The next format gate rejected native zero-date negative dependencies for absent derived `.txt` paths. Exact stopped outputs are retained; 136 rows cover 68 same-stem paths and all 18 regenerated global payloads/schemas remain equal to the original donor. Strict complete-namespace absence validation and a separately reviewed resumed lane are pending; no candidate or Kings case passed. Original provider preparation and native binaries remain reused. World readiness, held-PID status/ticks, complete warm cache bytes/mtime, ownership, SDK, schema and SQL gates remain mandatory.

Source review also identified about 1.58 GB of unnecessary repeated BIN-body processing in a dormant cache bridge. Exact original archive/manifest evidence and current ownership must remove that work before activation. A separate closed native metadata-census prototype is preserved at source `7f3d37fc191f3f30c124d6d57581afb64cceef42`. Root and independent review each passed 12 portable tests; [its receipt](android-evidence/native-client-metadata-census-0.13.37-prototype.json) records the current-provider/native/runtime gates that remain unestablished. It aims to reduce repeated filesystem operations without moving initialization into world entry. It has not been built as Game, executed under Wine or shipped.

The [inactive integration checkpoint](android-evidence/native-metadata-adapter-0.13.37-source-checkpoint.json) and independent [Map adapter](android-evidence/native-map-metadata-adapter-0.13.37-review.json), [normalizer](android-evidence/native-cache-normalizer-0.13.37-review.json), [client adapter](android-evidence/native-client-metadata-adapter-0.13.37-review.json) and [material reader](android-evidence/native-client-material-reader-0.13.37-review.json) reviews preserve exact source pins. These are source/host checks, with native and publication authorities still closed. The full qualifier now lists 223 modules: 204 retained fresh, 10 new fresh and nine inherited contracts; full execution remains pending.

## Diagnostic corrections

The Android manual-capture gate previously rejected a valid user-controlled
report because it demanded bounded observation. The correction accepts explicit
manual start/stop evidence while retaining session, identity, save, assets and
ownership requirements. It does not rewrite the guest's observation flags.

Cleanup authenticates a numeric PID namespace alias only with exact task identity.
Unreadable later worker environments require prior authentication of that same
worker. Missing identity metadata fails safely; process names, groups or inherited
PID assumptions cannot authorize cleanup.

The dedicated clean-host run
[38478387822](https://github.com/Russianranger/coh-android/actions/runs/38478387822)
executed 146 tests in six suites with zero failures, errors or skips. This includes
the full process suites that encountered unrelated namespace permissions on the
shared scratch host. These are freshly executed host tests, not a physical result
for a new APK.

## Next physical acceptance

Install a qualified successor over the existing app and retain all data. Reopen
THORHERO and confirm the destination reported from current SQL. Start and stop
capture manually. First verify a short session, ordinary Save/Logout and export
of the complete outer ZIP. Then measure client startup and the first cold
Atlas-to-Kings transfer separately from the resident return. Verify movement,
powers, costume, enhancements and combat, save normally and export after each
session. Preserve failure evidence if readiness or transfer fails.

## Current observation and CI recovery checkpoint

Finite original-material recovery passed 73 integrated host cases with zero skips and preserves failed historical native runs as failed. It recovers original evidence/components and the retained Game recipe; it creates no runtime authority. The separately built 96 MiB observation probe passed four actual Windows SDK controls while retaining the original Game. The subsequent Wine lane failed and its evidence is being recovered. The full Atlas/Kings world matrix remains pending.

The exact-C FileList benchmark rules out bulk sorting as a substantial saving: 19,606 actual FX paths require only 151 pointer shifts, and the safe append shortcut saves about 3 ms on this Linux host. Repeated native metadata calls, directory enumeration and decoding/allocation remain under investigation. None of these host observations establishes the requested sub-60-second client or sub-90-second physical zone targets.


## Reviewed conditional packaging and latest measurements

The closed revision-9 checkpoint follows `ee941481`. Root passed 94 current host cases in six modules, 90.235 s with zero failures/errors/skips. Conditional packaging can change only the qualified Map executable/additive receipt, enclosing archive/manifests and independently derived proof; the public .36 Game, Db, DLL/schema/launcher, graphics and Assets 1.0.0 remain exact. Original SDK compilation and fresh world execution have separate identities. Raw world JSON is admitted up to 64 MiB only for the exact Map qualification member; other JSON stays bounded at 8 MiB. No candidate selection, full qualification, publication or runtime authority is enabled.

The actual 96 MiB observation run [38510646414](https://github.com/Russianranger/coh-android/actions/runs/38510646414) failed on four full-path `CreateFile` error-206 results. Its complete native packet is 79,033,587 bytes / 182,999 rows / 7,531 directories: enumeration passed, readability failed, native capture took 80.302 s. Its original artifact `11870156176` and all four errors remain retained. Three Game controls passed; capture-disabled native readiness was 17.089729 s. This ordered warm host evidence establishes no device improvement.

| Existing native BIN phase | Retained warm | Capture disabled |
| --- | ---: | ---: |
| Open | 135 ms | 159 ms |
| Freshness | 2,626 ms | 2,881 ms |
| Decode | 1,392 ms | 1,487 ms |
| Raw timer rows | 292 | 292 |
| Known-length string copies | 3,556,737 | 3,556,737 |

These host counters were already enabled; the physical .36 reports did not enable them. String copies are not allocation counts or allocation cost. Native CRC, schema and freshness behavior remains intact. Recorded source projection capture/encode/recheck took 14.322625/0.043996/13.429147 s on this runner. Separate full-provider qualification custody read 8,566,369,583 bytes per pass, taking 88.629812 and 77.056867 s outside the Game clock. Those explicit harness costs are not proposed zero-cost production prerequisites, and different warm/custody boundaries must not be summed as a measured startup gain. Qualifier/parser RSS is separate from unmeasured native Game/probe/device memory.

The current single Wine reuse lane [38518079259](https://github.com/Russianranger/coh-android/actions/runs/38518079259), source `6662a056cb5a80b3a3b51d3741b10793fb8b6300`, reuses the original Game and probe with no native compilation. Its six source pins and 153 host controls passed independent review; the actual job and every step now passed. Original artifact `11873456803` is advertised as 45,891,553 bytes / SHA-256 `5833162a2a5ca6ee78a408f7be9d48780ca4bb48162755dec9590c5f35c41646`; raw counters and independent original-byte intake remain pending, so workflow success is not a performance gain or runtime authority. An owned short probe namespace addresses the observed long-path boundary. Full readability/PIG/consumed-field/provider/cleanup parity remains required; no Android equivalence, replay or lease authority follows from source review.

Bounded live-directory research is persisted separately at [3b737d6](https://github.com/Russianranger/coh-android/commit/3b737d617e9d02b9083ba485bfc42bd4bd099023). Its controlled C fixture checks 167,937 historical rows in 9,315 frames; the maximum observed packet is 22,696 bytes under a 27,944-byte wire cap. Nine owned-kernel model controls passed independently. The 77,568 KiB C-fixture RSS includes its full historical packet/two trees and does not measure a live helper. No real transport or Game/SDK/Wine/FEX/PRoot integration ran. Native timestamp, order/filter/alias/sharing/ownership and metadata-observation semantics still require qualification before this can reduce production filesystem work.

The final Atlas/Kings native matrix at source `3a713dc` remained in progress in [38505018109](https://github.com/Russianranger/coh-android/actions/runs/38505018109), with the 180-minute deadline at 06:15:31 UTC. Actual full evidence, 15-fresh/one-inherited execution lineage, independently derived donor subset and exact component/execution authority must pass before selecting Map5927. A failed or timed-out run remains failed. Full 223-module qualification, current PostgreSQL/assets preparation, new Android DEX, signature/reconstruction and public-byte audit remain pending. No successor APK or sub-60-second client/sub-90-second zone result is claimed.
