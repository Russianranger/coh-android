# CoH native: Thor report regression and Combined 0.1.11 follow-up

Current task starts from `5eef7eae530b60b30b9196ac75fec90dcd1b12d6`,
`native-android` only. Follow-up 0.1.11/code 12 is qualified and published for
Thor diagnostic testing from `042a149e6ca00d76e498fae9958bf49e5b795dd6`.
Physical Thor acceptance remains PENDING. Gates 25–27 remain OPEN.

Physical Thor 0.1.10 regression (user-supplied observations, not a new host test):
exact APK SHA-256 `7d74d9824fd80f08ca9a77a9d8ee68746d36dcfe9e74920ee864ffe2065880cf`.
Server ready ~395 s; separate local protocol accepted one character list,
choice and Map handoff, with two sockets opened/two closed. Normal GROUPS:
42,889 bytes, 508 present files, 33 roots, 343,112 bits. World-handoff report
became `REPORT_LIMIT` when the fixed 7,168-byte JSON formatter overflowed.
The fallback erased capture/first-failure evidence; derived `initial_packet:
NOT_OBSERVED` is inconclusive. It does not disprove initial packet receipt.
Sampled peak app RSS ~198.2 MiB/PSS ~93.3 MiB; minimum system headroom ~7.16 GiB;
zero sampler failures/sustained memory-pressure stops. Two native EGL contexts
completed with clean object release. These observations do not establish
genuine server-world entry or complete character/catalog/ACK authority.

Fix: bounded essential-first numeric report, deterministic optional omission,
explicit truncation metadata, and a separate native owner/control-state query.
Android must preserve owner activity, completed capture and first failure even
when report serialization is partial; unknown observation is not NOT_OBSERVED.
No auto-reconnect or application ACK is added. Existing report/parser/memory
limits, game data, assets, server runtime and signer stay preserved.

Focused host qualification: release/ASan/UBSan each 211 checks over the complete
retained source-layout probe chain, maximum supported request/receive counters,
full-width scalar stress, explicit progress omission and INITIAL_OBSERVED/CLOSED
cleanup. The original formatter requires 7,355 bytes in the supported maximum
fixture, exceeding 7,168; corrected maximum output is 6,863 bytes. All 70 source
closure pins match; no new report heap allocation. LeakSanitizer is unavailable
under host ptrace restrictions; owned zero-wipe/allocation controls pass, without
a leak-proof claim. Java phase controls: 44; phase-memory checks: 2,899; memory
worker: 34 checks/9,000 requests/two injected failures. Busy/unavailable and
server-only initial observation now stays UNKNOWN; a positive observation is
sticky through cleanup. These host tests do not qualify Android or Thor.

The historical adapter expected every optional object and eight JNI methods.
Its source stays immutable. The additive `interop-report-adapter-20261020`
role verifies exact bounded shipping JSON before a clearly marked host-only
detail projection runs every old deep assertion: release/ASan/UBSan each
12,913 checks/131 scenarios, 248 shipping reports, maximum 6,774 bytes. The
Android driver also strictly validates the three new Java control metadata
fields before applying the unchanged numeric/privacy contract.
The Android driver now starts its 30-second control-search budget after its
first independently bounded fresh accessibility capture, then inspects every
issued scroll before enforcing the unchanged ten-scroll cap. This fixes the
observed 57-second helper-bootstrap/portrait offscreen Sample memory locator
failure without bypassing the real widget. All 232 driver controls pass.

Final qualification/publication workflow (all five jobs PASS):
https://github.com/Russianranger/coh-android/actions/runs/39352586218
Android 13 x86_64: framework/import/preview 65 checks; native JNI, source-layout
single/multi-fragment INITIAL_OBSERVED, lifecycle and cleanup 23; same-signer
0.1.10 update/launch/debuggable rollback/reinstall 14. Four synthetic files,
69,863 B and UID 10174 survived; this is not real game-save migration proof.
The framework's first attempt failed in external UiAutomation (Bad file
descriptor/exit 137); its raw artifact is retained and excluded from PASS.
Only that job was replayed successfully; the APK was not rebuilt. The final
framework recorded installed APK hash matches the exact x86_64 candidate.
Retained part-count/additive bounded adapter qualification also PASS:
https://github.com/Russianranger/coh-android/actions/runs/39351960994
All compiled inputs for that run match the final candidate. Independent review
verifies 2,235 raw/committed source pins, 70 native compiler project pins,
nine protected inputs, actual binary manifest, all five ARM64 ELF libraries,
nine JNI exports and actual APK v2 signature/content digest.

Delivered ARM64 APK: `CoH-Native-Combined-0.1.11-report-diagnostic-arm64.apk`,
13,934,565 B. Package `org.coh.nativecombined`; version
`0.1.11-report-diagnostic-test`, code 12. Existing signer SHA-256:
`9aec9a8635d33dabd676748c3287e035e00d676546b4da18469dd48eecf5c522`.
APK SHA-256:
`8492e7475f739a6472c13703b6812878ffa22bca38cf809ecad6ae0da56ad364`.
Direct download:
https://github.com/Russianranger/coh-android/releases/download/coh-native-combined-v0.1.11-report-diagnostic-test/CoH-Native-Combined-0.1.11-report-diagnostic-arm64.apk
Release, checksum and qualification receipts:
https://github.com/Russianranger/coh-android/releases/tag/coh-native-combined-v0.1.11-report-diagnostic-test
Independent review and public-byte audit are retained in
`native-android/combined-client/diagnostics/report-regression-20261020/`.
Server binaries, PostgreSQL data, Wine/FEX state, imported assets, saved
profiles, all existing memory policies and parser limits are unchanged.
The signed ARM64 package is host/package-qualified; actual Android execution
uses the separate exact x86_64 APK. Neither establishes genuine server-world
entry, dictionary generations, ACK permission or world authority.

Thor 0.1.11 procedure (physical acceptance PENDING):
1. Export the current launcher report, stop the server cleanly and retain the
   qualified 0.1.10 APK. Install 0.1.11 over Combined; do not uninstall, clear
   storage or reimport existing data.
2. Start the same server and wait for ready. Launch native client, tap Test
   world handoff once and choose the existing character. Export native JSON
   after capture/first failure. Check the retained actual phase, first failure,
   GROUPS/REQALLENTS/initial observations and explicit truncation/omissions.
   Unknown means unknown; the complete report must not become REPORT_LIMIT.
3. Leave a completed capture open briefly, Home/resume, then Return to launcher.
   Confirm no auto-reconnect/repeated completed capture; export launcher ZIP.
   Stop the server cleanly and export another ZIP. Keep JSON/ZIPs with this
   exact APK hash. Retained debuggable rollback uses `adb install -r -d`;
   never substitute uninstall/clear when the ordinary installer refuses it.

The qualified 0.1.10 build and earlier integration evidence below remain
historical acceptance records; they do not qualify the 0.1.11 candidate.

Use `native-android` only. Recovered `7030870e`; three independent worktrees and
sequential expected-parent, non-force publication. Gates 1–24 remain accepted
within their documented scopes. Gates 25–27 remain OPEN.

A — `11026bf7ab283a5e959343c29472e93dd7a129a4`
Disabled nonshipping BodyPart runtime witness: complete ordered values, actual
loader-route hooks and startup comparison in a disposable source overlay.
Release/ASan/UBSan each: 2,542 checks, 291 synthetic loads, 256 cleanup cycles.
Own static storage 65,860 B; new heap 0; selected frames 432 B < 4 KiB reserve.
No target MapServer compile/execution or current-Map catalog admission yet.
https://github.com/Russianranger/coh-android/actions/runs/39331558734 PASS.
Reproduce: native-android/engine/costume-export/BODY_RUNTIME_WITNESS.md.

B — `0a1668ee6121a8f77c0551a06544b022d47b85a7`
Streamed authentic source occurrences join to sealed CityHall/Plaza geometry:
76,192 occurrences; 2 prepared models/21 parts; 47,227 NOT_PREPARED and 28,963
NO_MODEL remain explicit. Exact actual owner identity/borrowed lifetime required;
trusted unmodified historical candidate input is a precondition.
Release/ASan/UBSan each: 312,809 checks. Query allocates nothing. Named placement
aggregate 57,403,703 B; earlier seal transition 93,228,133 B < 96 MiB.
Nonrendered: CLIENT materials, concrete live owner adapter and generation remain
unqualified. Offline preview preserved.
https://github.com/Russianranger/coh-android/actions/runs/39331622054 PASS.
Reproduce: native-android/engine/scenecatalog/SOURCE_PLACEMENT.md.

C — APK runtime source `ae5a11d0c0be5098d0aec66370dda99c055167ee`.
Combined 0.1.10-memory-diagnostic-test/code 11, `org.coh.nativecombined`.
Signer SHA-256 `9aec9a8635d33dabd676748c3287e035e00d676546b4da18469dd48eecf5c522`.
Build/lint/both ABI/package+DSO audits and 17 host suites passed:
https://github.com/Russianranger/coh-android/actions/runs/39334606957
Independent package audit verifies exact APKs, 74 assets, 2,226 source pins.
Corrected first-unavailable null history and sampler recovery: 2,895 phase checks,
10,407 records; 34 production-worker checks/9,000 requests/two injected failures.
Policy 2,710 checks unchanged; JNI release/ASan/UBSan each 186.
Original `7929bdb7` APK is permanently WITHHELD for the reproduced null bug.

Exact-package Android qualification source:
`22ae9d770fb4d0e6c6550103a896d5f0f59243c0`.
https://github.com/Russianranger/coh-android/actions/runs/39338244800
All four jobs PASS: immutable admission, Android13 framework/import (65 checks),
fragment/memory/lifecycle (25), update/rollback/reinstall (14). CI also passes
229 UI controls and four upgrade controls. Package was NOT rebuilt: all 51
original package members are identical; 2,221 non-driver source pins unchanged.
Same UID and four synthetic files/69,863 B survived update, launch, debuggable
rollback and reinstall. This does not claim real game-save migration or guest
startup on x86. Renderer contexts, held input, sockets and retained bodies retire
under actual Android Return tests; no app crash/ANR was accepted.
Final independent execution audit: PASS; qualified for Thor TEST delivery only.
Audit SHA-256 `f8f2725c33d487e9594b49b2fa29cfb8e4215c1d850cb4968cd1528c75409d57`.
ARM64 test artifact is delivered; physical acceptance remains PENDING.

ARM64 APK: CoH-Native-Combined-0.1.10-memory-diagnostic-arm64.apk, 13,929,833 B.
SHA-256 `7d74d9824fd80f08ca9a77a9d8ee68746d36dcfe9e74920ee864ffe2065880cf`.
Original package artifact 12226012507, archive 17,868,604 B, SHA-256
`0d38981d31781a0e2d24adc579017e335ecb80cef547e45e5d0ee915d44ddd04`.

Memory: nine fixed phase slots, event/control-worker sampling at most once per
second, explicit unknown guest/native-owner/GPU totals. Android13 x86 emulator
fragment run: 13 samples, sampler failures 0, system samples valid; sampled peak
app RSS 144,199,680 B/PSS 71,669,760 B. FINAL_CLEANUP phase app RSS 91,340,800 B/
PSS 30,082,048 B. Minimum observed system headroom 499,650,560 B; Java headroom
160,623,520 B. These are sampled app observations, not total server RAM, absolute
peaks, physical Thor fit or leak proof. Genuine SERVER_READY/SERVER_STOPPED
measurements await the physical test. Host reservations are not device RSS/PSS.

Preserved: all nine protected locks/policy/import/runtime/signing inputs match
baseline hashes. Database, Wine/FEX, rootfs, assets, profiles and saves were not
changed. Existing 4 MiB decoded/16 KiB ordinary/8 MiB initial/96 MiB scene limits
remain. Generic parent ledger is not an installed concrete owner adapter.
No live catalog/default generation, complete authoritative character, actor,
world READY, RECEIVED_CHARACTER or application full-update ACK is admitted.
Combined 0.1.9 physical INITIAL_OBSERVED evidence retains its original scope.

Thor test (physical acceptance PENDING; installation belongs to the user):
1. Stop the existing server, keep accepted 0.1.9 for rollback, and install the
   qualified ARM64 APK over Combined. Never uninstall, clear storage or reimport.
2. Start the same server, launch native client, Test world handoff and choose the
   existing character. Missing catalog/character/resource states are expected;
   the image remains the accepted offline preview.
3. Sample memory and export native JSON. Home/resume; confirm no automatic
   reconnect. Return to launcher; confirm the same server remains available.
4. Export launcher ZIP, stop the server cleanly, then export another ZIP. Retain
   APK identity and exports. Genuine server-ready/stopped memory remains pending
   until these real-device observations exist.
5. Rollback, if needed, uses the retained debuggable 0.1.9 APK with a data-preserving
   `adb install -r -d` update. The normal installer may refuse version downgrade;
   do not replace it with uninstall/clear. No remote Thor installation was done.

Next three independent tasks:
1. Target-qualify the disabled provenance witness, then obtain independently
   attested executable/profile/run/current-Map and original cache/generation
   ownership from a separately qualified diagnostic runtime. Never auto-deploy
   instrumentation into the accepted server.
2. Authenticate CLIENT materials and install concrete owner/lifetime admission
   for the two-model subset, reserving old + candidate + scratch + retained
   assets before exposing any renderer candidate.
3. Retain genuine bounded ALLENTS/whole-initial diagnostics at the exact admitted
   input boundary. Preserve first unsupported dictionary/size/provenance states,
   existing caps and every actor/READY/ACK restriction.

Exact recovery, historical failures, package audits and final execution evidence:
native-android/integration/three-workstreams-20261019/integration.json.
