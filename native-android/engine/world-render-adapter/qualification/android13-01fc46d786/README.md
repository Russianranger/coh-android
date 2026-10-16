# Independent consolidated Android 13 receipt review

Both workflows completed successfully at source
`01fc46d78611ec9b55d086a2ac55166e13949c82`, tree
`c47ad370bfeb09e708e650c3e509e441b54cbff5`.

| Workflow | Host artifact | Android execution artifact |
| --- | --- | --- |
| [Primary 38948147675](https://github.com/Russianranger/coh-android/actions/runs/38948147675) | 12067283273 | 12067158877 |
| [Catalog 38948147764](https://github.com/Russianranger/coh-android/actions/runs/38948147764) | 12066393891 | 12067875003 |

Downloaded archive SHA256 values were checked against GitHub's artifact digests:

| Archive | SHA256 |
| --- | --- |
| Primary host | `68b7ec0934a779f7d3f4f4f9de3d3ff8c38c8abe8f6b2059bda2f469f39ef102` |
| Primary Android | `d6c7dcc847ea3f53e857fae9478a2d6e1f10303f9b58ab57c0e4c66dd07999fa` |
| Catalog host | `fb800dbffbb6a8bffe05e94e79d3934900f7818cdbb8e6920f1da141d21148aa` |
| Catalog Android | `62382867da6494afd44c6fc7290f256f8bda7c5333f03d285ca89f4f5ddc491d` |

The retained independent review verifies every declared source byte hash with
`git show` at this exact source, host clean state, fixture identity, both ABI
build receipts, ELF class/machine and executable SHA256, expected-result parity,
and emulator command/result/cleanup receipts. The catalog's exact-source
admission driver was also replayed read-only against the retained artifacts.
The adapter test command was attempted, returned zero, and its native result was
validated. Independent batch execution succeeded for the contracts and adapter.

| Suite | Identical release, ASan, UBSan and Android checks |
| --- | ---: |
| Entity records, title, taskforce and costume helpers | 2,065,314 |
| Entity control | 667,138 |
| Scene graph | 193,219 |
| Catalog | 21,111 |
| Auth interoperability contracts | 2,147 |
| World adapter | 16,745 |

Execution was on Android 13 / SDK 33 x86_64 emulators. ARM64 executables were
built and their identities verified; ARM64 was not executed here. Entity and
graph binaries agree across the two independent workflow artifacts. The adapter
binary identities remain the previously qualified identities: ARM64
`c509cd378a161d1de75c0c9bf2b241ca6df3d561a7d3874fcedd715882f8b790`,
x86_64 `089c75aff4c8b514bf12b18ec1c0f515c34b766fdb53953dc740c28bddfdaaec`.

Only standalone contract executables ran. This evidence does not activate GLES,
build an APK, capture an authentic Atlas catalog, establish real encrypted
account login, complete the player/full-update transaction, or close gates 25–27.
No accepted APK was rebuilt or device test repeated. Optional Win32 exporter
compilation in the catalog workflow was skipped.

The JSON/log receipts below are copied from the exact artifacts. Executables and
generated fixtures remain in those artifact archives; the local review retained
the full archives at `/tmp/coh-qualification-01fc/{primary,catalog}` during this
session. `verify_retained_artifacts.py` documents the independent replay against
full extracted archives; it does not rerun a workflow or install an APK.
