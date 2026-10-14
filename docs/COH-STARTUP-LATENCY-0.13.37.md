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

The full-world native Map gate is active at source `8a08a1927225fdaa334ae330b8c8c5d044306fc2`, run [38489822992](https://github.com/Russianranger/coh-android/actions/runs/38489822992). Original successful preparation and binaries are reused. Earlier failed attempts are retained separately. Native readiness/held process/world/SDK/SQL/cache checks remain mandatory; 31 fresh harness tests passed. No completed world case is claimed yet.

Source review also identified about 1.58 GB of unnecessary repeated BIN-body processing in a dormant cache bridge. Exact original archive/manifest evidence and current ownership must remove that work before activation. A separate native full metadata-census prototype is under source review; its aim is fewer filesystem operations without moving work into world entry. It has not been built, executed or shipped.

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
