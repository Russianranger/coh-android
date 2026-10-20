# CoH Native ARM64 — compact recovery, 2026-10-20

Use `native-android` ONLY. This cycle fetched baseline
`50a80ea29077d16332fb58c6999cc27631448b8d`; five linked sparse worktrees ran
concurrently with one shared source checkout. Heavy local builds were serialized
under `/tmp/coh-cycle-build.lock`; compiler/Gradle concurrency stayed bounded.
No accepted history, server binary, database, imports, signatures or app profile
was replaced. Gates 1–24 retain their documented scopes; gates 25–27 remain OPEN.

Read the ledger and worker receipts in
`native-android/engine/qualification-cycle-20261020/`, then only the relevant
contract. Worker receipts are historical host checkpoints; coordinator CI/audit
receipts describe the exact packaged source. All worktrees/commits were preserved.
Final documentation and preflight retention changes require no new APK/full build.

## Physical baseline and current refusal

Accepted Thor 0.1.11 APK SHA-256:
`8492e7475f739a6472c13703b6812878ffa22bca38cf809ecad6ae0da56ad364`.
User-supplied physical evidence: INITIAL_OBSERVED; genuine 37,884-byte ALLENTS
(303,072 logical bits); valid 42,889-byte GROUPS; 508 present world files/33 roots;
selection/Map handoff, selected-self prefix/raw DBID comparison; REQALLENTS;
two owned sockets closed; no reported memory pressure. No new Thor observation.

The live packet still stops at stage 41, FIRST_DEFAULT_CATALOG_REQUIRED /
DEFAULT_CATALOG_REQUIRED, compact `[2,41,3,1,2424,3416,262144]`. Flag 0 requires
genuine original GetBodyPartCount() from the current runtime owner. Historical
CLIENT 28 rows and native capacity 30 establish neither that count nor generation.
No runtime catalog, selected-character/world ownership, READY, RECEIVED_CHARACTER
or application full-update ACK is admitted. ALLENTS41/43 and later cache/index
boundaries remain intact.

## Five bounded increments

| Worker | Result and qualified source commit | Exact remaining boundary |
| --- | --- | --- |
| A | PARTIAL — `fe31a4e039e32a200da7c5316c5c95d937e26f3c`; conditional source-framing/count consumer; 51,868 standalone + 13,953 actual-owner composition checks per release/ASan/UBSan mode | Production queries refuse. Original bodytype/count validation precedes every part/cache bit; flag 1 retains Pack4 framing and separate catalog checks. |
| B | PARTIAL — initial target `31ca0a9e36025c8371c62d6632dfbddcdbdd5335`, final preflight/retention `38909a04a4797c43db28ab169d5c37b1ca2a8775`; 10 host preflight tests, 2,542 producer checks per mode | Target compiled twice; TARGET_EVALUATED_SDK_MISMATCH prevents executable qualification. No runtime, loaded rows, cache/shared selection or generation observation. |
| C | PARTIAL — `45ae1409396b46c9f55e3dab07f57a5e4c2e5bd0`; complete immutable candidate slots/rows, lease-storage identity, retirement/alias/cleanup; 18,195 checks per mode | No runtime-admitted constructor. Current source/profile/session/load-generation/packet association is absent. Historical authenticity cannot activate it. |
| D | PARTIAL — `b00faf61d5fdbe167add2b095c17c504295ab328`; 21 two-model partitions, 14 historical CLIENT TexOpt owners, 37 distinct raw layer names/133 occurrences; 313,744 checks per mode | Effective TexBind/Basic namespace/defaults, texture bodies, current generation and concrete GPU owner unavailable. Offline preview preserved. |
| E | QUALIFIED diagnostic scope — `054fdafb6faabd59add1f73151765aac6c8071d6`; essential marker/human refusal survive omissions/CLOSED; 341 native checks per mode, 85 Java checks | Positive stage-41 Android/Thor observation pending. Emulator peer stops earlier and correctly reports a null catalog marker. |

A/C: `initial-capture/PARTCOUNT_ADMISSION.md`, `character-dictionary/COSTUME_OWNER.md`.
B: `costume-export/BODY_RUNTIME_TARGET.md`. D: `scenecatalog/SOURCE_MATERIAL_PLAN.md`.
These contract paths are under `native-android/engine/`.

B runs 39363378870 and 39365299854 passed actual compile steps. The second retained
a raw 7,472,640-byte PE32/i386 candidate, SHA-256
`fe244f0256b2a45f07050c576f837c9bc69f36b39339db685f1ba32fa21b8df6`.
Generated SDK 10.0.26100.0/v145 identity is known; original effective SDK/UCRT
query operands were not retained. Their equality and actual UCRT selection are
unproved. New bounded query-sidecar retention cannot reattest that old build.
Raw artifact integrity is qualified; executable qualification is refused.
Do not deploy it or connect it to the working database.

## Exact diagnostic APK and CI

APK source `2cb7d999534ac79cb0f0e756f8a4da5702dd28d6`, tree
`a5cbf41644248da3ebe68f85927d05095f468c21`.
`CoH-Native-Combined-0.1.12-catalog-diagnostic-arm64.apk`, 13,936,213 bytes,
code 13 / `0.1.12-catalog-diagnostic-test`, SHA-256
`0fbe39effa0a608e683eed5ee788daf856099be46ad108d6ccc8bbafb75ad849`.
Signer `9aec9a8635d33dabd676748c3287e035e00d676546b4da18469dd48eecf5c522`.
The 0.1.11 default profile and accepted APK remain preserved.

CI https://github.com/Russianranger/coh-android/actions/runs/39364218500:
source contracts, package, Android 13 upgrade (14 checks), framework (66) and
fragment lifecycle (22) all passed. Independent exact-package/source/signer/
installed-APK admission also passed. GitHub release creation then failed HTTP 403
“Resource not accessible by integration”; overall workflow failed at publication.
No GitHub release was created. Qualified APK delivered directly. Retention now
runs even after a publication-service failure.

All 74 assets/four other ARM64 libraries match accepted 0.1.11; only interop DSO
changed. Audits matched 2,289 unique project files; 97 compiler/system headers
were not locally reauthenticated. Upgrade used four synthetic files and preserved
UID through 12→13→12→13, not actual user-save migration. Renderer snapshot reports
released objects/zero GL/EGL errors but 3 contexts started/2 completed; that
snapshot does not prove complete final renderer retirement.

## Accounting and observations — separate scopes

Caps unchanged: 4 MiB decoded; ordinary 16 KiB semantic transport; 8 MiB initial
aggregate; 96 MiB scene transaction; 7,168-byte report; ServerMemoryPolicy.
Report maximum 6,887 bytes. A+owner conservative host-frame sum 9,664 bytes under
16 KiB call reserve. C’s synthetic two-row fixture owns 1,365 bytes; named construction peak 4,249,484 bytes
includes all 16 lease/view controls. D named query peak 57,113,279 bytes; earlier
separate seal transition 93,228,133 bytes. Neither is complete process/GPU fit.
No fabricated reservation tickets exist.

D worker-local child peak RSS: release 61,173,760; ASan 564,649,984; UBSan 62,619,648
bytes. Hosted CI child RSS is recorded separately in its source artifact. Witness
host static 65,860 bytes, new heap zero, payload cap 65,536 bytes, observer stack
reserve 4 KiB. Host cgroup limit 8 GiB; observed oom/oom_kill zero, with no complete
simultaneous-process peak claim. Android 13 x86 app sampler: 13 samples/zero
failures, peak RSS 128,086,016/PSS 55,702,528 bytes. These are sampled emulator-app
observations, not guest/ARM64/Thor totals, absolute peak or leak proof.

## Next five tasks

1. Retain effective SDK/UCRT/IncludePath/LibraryPath values in compatible Windows
   preflight before another full build; qualify target provenance, then establish
   isolated disposable execution and real loader/cache/shared/load-generation ownership.
2. Capture coherent complete runtime BodyPart/costume tables and authenticate
   ordered row-to-slot, executable/profile/session/packet generation association.
3. Install a genuine producer-backed immutable lease; advance stage 41 only until
   the next actually supported original part/index boundary.
4. Resolve the 37 distinct raw CLIENT names through original filters/ordered
   namespace/defaults to establish actual texture bodies, then add concrete GPU
   reservation, lifetime and rollback checks.
5. Test this APK on Thor: install over 0.1.11 without uninstalling/clearing data;
   same server/character, enter world once, export JSON/ZIP; check INITIAL_OBSERVED
   and essential stage 41 through omission/CLOSED, then Home/resume/Return/clean
   stop. Retain hashes and sampled memory. No new catalog/actor/ACK is expected.

Historical handoff remains in baseline `50a80ea29`. Do not restart accepted
loader/cache/destructor milestones or bypass a costume body to read later records.
