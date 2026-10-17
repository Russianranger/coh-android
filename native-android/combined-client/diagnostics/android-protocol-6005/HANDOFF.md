# Native protocol qualification at 6005bbf

Source: `6005bbf34376cb71bb5b3fc71058af629b19ce86`, tree `022276e3173aa7abfcb0bb27c5b7641a4ab83fdf`.

Both already configured protocol workflows ran because the new publication changed their native source inputs. Neither builds an APK or starts a shard. Both jobs in each run passed; the actual downloaded evidence was then admitted independently with `verify.py`.

| Workflow | Host/ARM64 artifact | Android 13 execution artifact |
|---|---|---|
| [39002917149](https://github.com/Russianranger/coh-android/actions/runs/39002917149) | [12090071990](https://github.com/Russianranger/coh-android/actions/runs/39002917149/artifacts/12090071990) | [12089827111](https://github.com/Russianranger/coh-android/actions/runs/39002917149/artifacts/12089827111) |
| [39002917152](https://github.com/Russianranger/coh-android/actions/runs/39002917152) | [12088939718](https://github.com/Russianranger/coh-android/actions/runs/39002917152/artifacts/12088939718) | [12090290394](https://github.com/Russianranger/coh-android/actions/runs/39002917152/artifacts/12090290394) |

The five live-foundation executables were built for ARM64 and x86_64. Actual execution was Android 13 x86_64 emulator only:

| Suite | Checks | Additional scope |
|---|---:|---|
| Crypto | 1,920 | 10,000 malformed inputs; no authenticated session |
| DB wire | 95,949 | 10,000 malformed inputs; no real server login |
| Owned DB session | 958 | 14 actual OS UDP scripted-peer scenarios |
| Login | 523 | 11 actual OS TCP synthetic-AuthServer scenarios |
| Map client | 31,780 | 33 actual OS UDP scripted-peer scenarios; 10,665 negative cases |
| Independent UDP boundary | 1,194 | 22 socket scenarios, 61 negative cases |

The Map suite includes the source-qualified selected-DBID admission changes and borrowed GROUPS observer. It explicitly reports scene assets unresolved, scene CRC unverified, no authentication and no live world. The original source producer/consumer fixtures and host sanitizer jobs are recorded separately in the retained host receipts. The whole-session owner host contract has 277 checks/11 synthetic component scenarios and a separate 41-check/3-scenario actual TCP refusal boundary; this is not a complete successful Auth→DB→Map socket chain.

`artifact-replay.json` records independent replay against all four full artifact SHA256/size pins, all ZIP member CRCs, 772 recorded Git source hashes at the exact source revision, both ABI manifests/binary receipts, ELF machine fields and the execution report bindings. Hashing a source file does not imply that the file was compiled or exercised. Replay imports only the two small existing evidence validators extracted from pinned Git source; it never executes artifact binaries. The Android execution archives and principal host receipts are preserved here. The full host archives remain at their linked artifacts and in the recovery workspace; their hashes and sizes are also immutable in `verify.py`.

To replay with the four downloaded archives arranged as `ID/artifact.zip`:

```sh
python native-android/combined-client/diagnostics/android-protocol-6005/verify.py --repo . --artifacts /path/to/protocol-ci-6005 --output /fresh/receipt.json
```

ARM64 execution, Thor, real-server acceptance, complete scene/entity transactions, JNI/application integration and atomic world/actor rendering remain unqualified for these changes. These protocol results do not qualify the later catalog, texture-input, graph-pager or selected-record work. Accepted APKs, accounts, characters, runtime profiles and deferred tests are unchanged. No expensive capture or workflow rerun was requested.

Device cleanup evidence differs: the five-suite runner sets success only after its owned temporary-directory removal succeeds. The older standalone UDP boundary writes its proof before cleanup and suppresses cleanup errors. Its passing artifact therefore does not independently establish device-file cleanup; `boundary_device_cleanup_verified` remains false. Socket/descriptor cleanup inside each native test is a separate, explicitly tested property.
