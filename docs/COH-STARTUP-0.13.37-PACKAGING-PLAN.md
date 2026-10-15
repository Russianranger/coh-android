# COH Android 0.13.37 packaging and qualification plan

Status: design only. No successor APK, build claim, promotion or publication is authorized by this document alone. Version 0.13.36 remains the latest published qualified gameplay APK. New native components are admitted only after the applicable gates below pass.

## Exact donor

- Repository/branch: `Russianranger/coh-android`, `codex/character-persistence-continuation`.
- APK source: `3570430cefdb15d9b239563e85cccf4d8fe6f32e`, tree `3ba011b6c653bd59eb39e1a4ed60babb95cc46f2`.
- Publication workflow: `38346809297`, all four jobs successful, including independent public audit `115141593507`.
- APK: `COH-Atlas-Gameplay-0.13.36.apk`, 42,076,692 bytes, SHA-256 `14d88da1796d155dc1b98e45ac642c7702ff3286e7ef0f2a0772f8e48693b12f`, version code 51.
- Retained signer: `92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282`.
- Accepted artifact `11790511602`: 54,708,216 bytes, SHA-256 `3b3bdd9b9e3d6425b7ef40ca45468979bd2700606bab4c2318b54d799d5d6f7e`.
- Build receipt: 12,621,902 bytes, SHA-256 `7eaebff204771bd35f444f4a5294f467c682f27b77b9973294bb678e9e239e4e`.
- Public audit artifact `11790804742`: 850 bytes, SHA-256 `ef0b4e5b1299c00e7988a9323307e51746eacf3a6a24261551844e678e62c198`.
- Public audit receipt: 1,707 bytes, SHA-256 `56f60e79bb0213869da59e8f1d2cec73f8994b5885f03ab3ecf85bd1b6f07e4d`.
- Current qualification: 2,848 tests in 205 suites, zero skips/failures/errors; 115 inherited tests in eight suites retain original source/producer identities. The recovered publication receipt records the exact lineage and scope.

All four original Assets 1.0.0 volumes, player databases, saved profile, Wine prefix, GPU/FEX/Wine runtime and independently qualified native libraries remain inputs. Main and the independent `native-android` branch are outside this work. PR #1 stays draft and unmerged.

## Required Android recompilation

The diagnostics repair changes Java behavior. The .36 `build_client_startup_latency_apk.py` intentionally copies retained DEX and is unsuitable unchanged.

Use the existing .35 `compile_shell` sequence as the reviewed implementation model: version-only manifest rewrite; pinned SDK `aapt2` compile/link; exact unchanged resource inventory/bytes; `javac --release 8`; D8 with minimum API 26; zipalign; signing with the existing retained key. Compile the authenticated 24-source .36 Java inventory plus exactly enumerated added helpers and reviewed changed sources. The source census must reject unexpected additions and removals. The final DEX must change and be recreated in a fresh independent process during audit.

The successor is provisionally version `0.13.37`, code `52`. Package identity, min/target SDK, ABI, resources and signing certificate remain verified against the donor. The legitimate manual capture policy must be verified from operation identity, report/manual-session agreement, zero-deadline budget and requested finish. It must not be represented as a bounded timer by changing the guest evidence flag.

## Native component promotion boundaries

The existing `native_map_startup_contract` admits the exact .32 consumer and recipe. Replacing `MapServer.exe` beneath that receipt would break provenance. Introduce an additive typed metadata component whose previous package reconstructs the complete old package and its old raw receipt serialization. Validate the new producer source, build artifact, executable PE/import inventory, exact source patch, native fixtures and fresh qualification separately. Preserve historical animation, FX, monorail, DbServer, schema and graph producer identities.

The build-only Map candidate presently known is 7,480,832 bytes, SHA-256 `5927f87fdac50c5a839ac067ccbb34b5dfad6223e579287a66a2f866a7d4b2e6`; build source `47e40d4d586d29e273e31ed4d0d51d160832b89d`, workflow `38350813669`, job `115142552789`, artifact `11790609618` (ZIP 3,307,410 bytes, SHA-256 `69bfc9f44e5304eae786d0668ba30f183f5b99a58586f8db7861f697d8e23aab`). Its paired preload at source `9454e789` / run `38352862725` establishes only the retained generated-provider preload scope. Full native Atlas/Kings world, collision and memory qualification remains a promotion gate. Observed host savings are not a device forecast.

The new Map metadata option is disabled by default. If promoted, launch configuration must enable it only for the authenticated admitted Map consumer; unknown consumers keep the stock path. Its parser scope must retain schema/content semantics and native decision ordering. Freshness checks remain active. Any reusable generated BIN output requires an explicit source/provider-generation proof binding all dependencies, consumer and ownership; the earlier 18 changed BIN outputs are not an unchanged-cache result.

There are additional consumer bindings to update through the typed contract:

- `native_map_startup_contract.verify_current_map`, its progress contract and callers must reach the current consumer while preserving original animation/cache-donor identity only where native parity proves compatibility.
- `server_cache_package`, animation certificates, collision/beacon proof inventories and closed cache identities must bind the actual current Map executable. Existing caches from another consumer need conservative invalidation or a separately qualified compatibility bridge.
- `local_character_server.server_input_projection` admits only exact Map SHA `fea96d0a...`. A new Map otherwise causes a full texture mirror. Admit the new consumer only after its exact unchanged texture-exclusion call site and actual server provider parity are established; retain the original consumer as a separate accepted identity.
- Native world, port, graph and readiness must agree for Atlas 1/7001 and Kings 5/7003. Native progress/status evidence and character connection remain independent. No player mutation is permitted to repair a startup failure.

A new Game candidate similarly needs an additive typed receipt retaining raw donor ancestry, source/build/native fixtures, exact renderer/dependency inventory and compatible schemas. Change only the admitted Game archive member and its enclosing manifest, keeping every other native member byte identical unless separately admitted. Installed-client refresh must replace the exact qualified executable atomically inside an owned inactive runtime without recreating the existing Wine prefix or profile.

## Proposed finite file set

Names below are provisional until the native source scope is frozen. Native research workflows stay on their research branches; production does not incorporate unrelated research trees.

| Area | Proposed successor-owned paths |
|---|---|
| Publication | `.github/workflows/android-client-zone-startup.yml`; `tools/android/interactive/release-client-zone-startup-0.13.37.json` |
| APK assembly/audit | `build_client_zone_startup_apk.py`, `test_client_zone_startup_package.py` under `tools/android/interactive/` |
| Current host qualification | `qualify_client_zone_startup.py` and focused native-component/preparation proof validators under `tools/android/interactive/` |
| CI ownership | `classify_client_zone_startup_change.py` and the minimal existing classification dispatch callers needed to recognize its finite direct-parent scope |
| Android | Diagnostics agent's exact reviewed changed Java files and additional pure Java helper; matching host tests |
| Guest | Exact diagnostics cleanup repair sources/tests, new typed native metadata contract, and narrowly required consumer/admission/launch/inactive-refresh sources/tests |
| Native inputs | Exact producer marker/receipt pins; source recipe and fixture files required to independently reconstruct and validate each admitted component |
| Evidence/docs | `.36` publication receipt; successor changelog/guide/HANDOFF; current host/native/source/publication evidence; physical follow-up evidence kept independent |

Do not edit the .36 marker, builder, workflow, frozen testing guide or historical producer recipes. The .37 builder authenticates actual .36 public APK bytes, build report and public audit before accepting any donor. Changed APK payloads are an explicit set. Any native archive rebuild must preserve exact inventory and all non-admitted member bytes, deterministic safe archive names, ordered nested receipts and historical ownership. Added payloads are separately enumerated.

## Qualification and publication sequence

1. Freeze reviewed Android/guest/native scopes. Run focused diagnostics/manual-policy/cleanup tests, native source/fixture tests, archive/receipt tamper tests and cache failure/fallback tests. Preserve the existing working Send Text/L3 and manual Start/Stop behavior.
2. Authenticate original producer metadata and actual artifact ZIP bytes. Reuse completed native build artifacts rather than rebuilding successful candidates. Native tests must execute the exact executable later packaged.
3. Require the native Map gates: actual Atlas/Kings initialization with native DbServer and PostgreSQL, independent progress/status, exact world/port, geometry/beacons/PhysX/collision parity and owned process cleanup; full/compact FX equivalence; animation semantics and provider/BIN identifiers/decision ordering; bounded measured memory. Record initialization versus gameplay scope explicitly.
4. Require the native Game gates if promoted: actual retained/candidate Game startup under a complete authenticated client provider, identical renderer/runtime, logical output/cache semantics and preserved libraries/graphics behavior. Software-renderer host runs cannot establish Thor speed or GPU compatibility alone. Any gate failure retains the qualified current consumer.
5. Execute all applicable current host regression suites, strict isolated SQL saved-location/identity/enhancement fixtures and actual complete Assets 1.0.0 preparation for cold and warm Atlas/Kings. Preserve accurate inherited historical packaging qualification separately. Modified native consumers require current native compatibility receipts; their old production qualification cannot be merely inherited.
6. Execute actual packaged helper/preparation tests plus fresh genuine retained native Db startup/restart/schema/query/cleanup as appropriate. No test may access the physical THORHERO database. Report checks distinguish committed successful saves from later cleanup/finalization failures.
7. Compile the reviewed Android inventory, assemble deterministic changed runtime payloads, sign with the retained certificate, and retain candidate diagnostics before acceptance. The private signing artifact's original owner remains `36731428735`; no key is generated or replaced.
8. In a fresh process with a different hash seed, independently recompile DEX, reconstruct all changed manifests/native archives/payloads, rerun mandatory actual runtime preparation on the final signed APK, verify manifest/resource identity, signature and checksum, and require exact equality to the accepted qualification.
9. Publish once only after gates pass. Publish APK, checksum and versioned test guide; verify unchanged Assets 1.0.0 release metadata. A new public-audit job must download the release bytes independently and verify the actual APK/guide/checksum, signature and source/artifact provenance. Preserve incomplete/failed artifacts as diagnostics rather than accepted releases.
10. Append the final receipt/HANDOFF in a finite documentation-only direct-parent commit. Verify main unchanged and PR #1 draft/unmerged. First device test begins from authoritative saved SQL (latest physical follow-up exported Atlas), short reopen/save/export, then same-map reopen and a single measured transfer.

The publication workflow must own only this reviewed direct-parent change set and marker. Unknown paths or ambiguous ancestry retain historical gates. The native builds/qualification workflows keep their original source identities; .37 consumes their exact artifacts through authenticated admission. No CI result converts host timings into the user's sub-one-minute client or 90-second zoning acceptance.
