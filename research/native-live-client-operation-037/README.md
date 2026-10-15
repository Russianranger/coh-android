# Closed client directory-operation source stage

This directory preserves the reviewed, dormant operation owner, guest handoff and
their host tests. It introduces no production `ClientRuntime` caller or activation
validator. The copied `ClientRuntime.java` is the unchanged 199,541-byte launcher
fixture from commit `270ad89b4f2f85333692f54446901cc4da3cb4e4`, SHA-256
`827773adbba17e4702bcf0732b1afed5fbcfde3c30cec41362b425ef2967bdf9`.
Tests extract its literal finalized command. It is not a new Runtime implementation.

The five source components and five test modules retain their original relative
paths and exact reviewed bytes. `qualification.json` records their pins, selected
original JSON receipt pins and the limits of each result. The selected receipts
are copied verbatim; their original absolute paths remain historical provenance.
No native binary, source asset volume, database, character profile, private control
document or real credential is included.

## Current qualification scope

The current source has **216 unique qualified control cases**. Each case is counted
once, irrespective of owner/reviewer reruns. Older source revisions and inherited
native component tests are separate evidence.

| Module | Cases | Actual execution and limits |
| --- | ---: | --- |
| `test_client_guest_namespace` | 36 | Release-8 JVM descriptor and unchanged launcher-command fixture |
| `test_client_live_directory_service` | 71 | Release-8 JVM and TCP; native backend is a typed mock |
| `test_client_live_directory_operation` | 72 | Release-8 JVM and TCP; native calls, metadata and activation are typed mocks |
| `test_client_live_directory_operation_jni` | 5 | Host JNI, current kernel files and TCP; authenticated original helper is reused, activation is controlled |
| `test_client_live_directory_control` | 32 | Isolated current private-file controls; external fixture/producer context is controlled |

The five current JNI cases include real bound absolute and relative guest links,
held inode/device identity, current fields/order across NT observation batches,
safe initial refusal and terminal late retargeting. Current final counter evidence
survives EOF and owner close. The source review for the older 63-plus-5 revision is
preserved as historical scope. It does not qualify the current final-statistics
correction; the separate current 72-case review and current five-case JNI receipt
provide that evidence. Earlier guest cases inside the Service receipt use older
guest bytes and are excluded from the current 32-case guest count.

The copied research layout was freshly verified with the same 216 cases in
36.646 seconds, with zero failures, errors or skips. That layout replay reuses the
original host helper and contributes no additional unique cases or device timing.

## Operation boundary

`ClientGuestNamespace` copies the finalized PRoot arguments and environment and
describes fourteen bindings. It grants no native registration or root-metadata
authority. The operation factory requires an external reviewed activation contract
bound to the exact operation, session, process, UID, runtime, Game, helper, namespace
and current Game view. Its six production proof gates remain unimplemented here.

The factory checks seven current owned directory bindings on the same device and
with the real app UID. JNI independently opens and holds their ancestry. Initial
Game requests are restricted to FX and `scripts.loc` within the current work view.
A resolved target may use that view or the current `/game-import/data`, within the
same branch. The original request and resolved target are kept separately. Native
code revalidates the original request and held directory around each observation
batch. Unsupported initial requests can use ordinary native discovery before any
row is delivered. A late failure closes the operation's namespace without retry.

The transport has no authenticated Game idle or session timer. Its finite
preauthentication, cursor, wire and owned-cleanup bounds remain enforced. Optional
statistics retain only six validated counters, or an explicit bounded omission.
Counters describe entry-metadata requests and the bounded native core heap. Final
owned-heap values are observed after cursor cleanup and before namespace close;
they are not total filesystem calls, process RSS or device memory.

The private handoff is planned at `/tmp/client-live-directory-control.json`, in the
current operation's private tmp binding. The document has fourteen exact fields
including `format: 1`; it has no enable or qualification flag. The guest loader
requires external typed current proof, a regular owned mode-0600 single-link file,
exact current identities and a fresh first Game attempt. It strips inherited live
settings from shared environments and projects credentials only for that Game.
Nonce values are registered for redaction before error reporting. Missing, invalid
or stale handoff uses stock discovery. This stage writes no handoff file.

## Reproduction

Use Python 3 and a JDK with the `jdk.compiler` module. The tests compile Java with
`--release 8`. From this directory, the four host-only modules can be reproduced:

```sh
PYTHONPATH=tools/android/interactive:android/guest python3 -W error::ResourceWarning -m unittest test_client_guest_namespace test_client_live_directory_service test_client_live_directory_operation test_client_live_directory_control -v
```

For the five real host-JNI cases, supply the authenticated original build receipt
through `COH_LIVE_TEST_JNI_RECEIPT`. Its SHA-256 must be
`1b7feb737cc335f34775caff0ad769508c03a369f18d9fd83d2f92877f136fe6`.
The original adjacent `libcoh_live_directory-host.so` must be 35,664 bytes with
SHA-256 `b264121c80afb11ff84248b98099939a6657251c56bd2175174f260615d45708`.
The copied JSON receipt alone does not provide the binary. The test independently
checks the original receipt, native source recipe and complete helper bytes before
loading it; it does not rebuild native code.

```sh
COH_LIVE_TEST_JNI_RECEIPT=/path/to/original/qualification.json PYTHONPATH=tools/android/interactive:android/guest python3 -W error::ResourceWarning -m unittest test_client_live_directory_operation_jni -v
```

## Retained ARM component provenance

The separate read-only component audit at commit
`2d030678e7013891547ecd7d35fc0cf40ffabff9`, run
[38534800834](https://github.com/Russianranger/coh-android/actions/runs/38534800834),
authenticated the original ARM helper and ELF boundary. Its source and artifact
review is retained in `qualification/retained-ARM-component-independent-review.json`.
The 29,992-byte ARM helper SHA-256 is
`3d21ece5894b46e9315eb14c3cc12f8d2fcbd3082f99031b4bcbde3e03d5e282`.
That audit did not compile or reexecute the native components.

Original native build and execution belong to commit
`43ac85108fa9ebe6916f7fbea74e9f5df85fe529`, run
[38531585318](https://github.com/Russianranger/coh-android/actions/runs/38531585318).
Its twelve native commands completed successfully, including 42 host-kernel,
26 host-C, 28 checked host-JNI and 26 static Bionic ARM64 fixture controls. The
original overall job remains **failed** because its JNI dependency boundary check
rejected the NDK driver's `libdl.so` dependency. The later read-only audit verified
that dependency against the pinned driver source and retained bytes. It does not
rewrite the original failed report or add those inherited controls to 216.

No Android OS, packaged PRoot/Wine/FEX, native Game consumer, runtime activation,
shipping APK or physical AYN Thor performance gate is granted by this stage.
Production admission still requires the current packaged metadata fixture and
complete native Game/runtime/component qualification. No sub-minute client or
zone-loading improvement is claimed from these host controls.
