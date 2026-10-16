# First Android 13 adapter contract qualification

[Primary run 38946462977](https://github.com/Russianranger/coh-android/actions/runs/38946462977)
passed at source `fd86ff196f172bf62cd24c7e0f807df39c33e0a5`, tree
`645c6741a1cd2e95a3da4778fe7c770fc08d4ea6`. Host job `117126725131` and
Android job `117127459369` both succeeded.

The retained adapter x86_64 binary executed on Android 13 SDK33 and returned
exactly the same result as host release, ASan and UBSan: **16,745 checks**,
512 original matrix cases, 5,000 bounded mutations, 2,000 published generations,
three concurrent readers, 4,096 fixture draws and zero adapter render-path
allocations/frees. The execution receipt separately confirms command attempted,
exit zero, native result validated, source/runner/binary identities and cleanup.
This is CPU adapter, source-matrix and lifecycle qualification; it is not a
hardware GLES scene-rendering test or server-world evidence.

| Standalone adapter binary | SHA256 | Qualification |
| --- | --- | --- |
| ARM64 | `c509cd378a161d1de75c0c9bf2b241ca6df3d561a7d3874fcedd715882f8b790` | Built, unexecuted |
| x86_64 | `089c75aff4c8b514bf12b18ec1c0f515c34b766fdb53953dc740c28bddfdaaec` | Android 13 emulator executed |

These binary bytes are unchanged from the prior `140ee62d7` build. The former
workflow skipped adapter execution after a different suite failed. The new batch
driver preserves separate protocol and adapter results. Earlier failures and
unattempted execution remain documented in sibling qualification directories.

The independent review verifies exact Git source tree, every declared host/build
source-byte map, generated fixture identities, both ABI hashes/ELF machines and
sanitizer parity. It also binds the protocol Android results: scene graph
193,219 checks, entities 1,142,224, entity control 667,138 and auth policy 2,147.
Those suites retain their own documented partial decoding and policy scopes.

[Host and ABI artifact 12067125625](https://github.com/Russianranger/coh-android/actions/runs/38946462977/artifacts/12067125625)
ZIP SHA256 `a16d303c93cdb6d3c875219a806f4fcccfc6237b08b9b7fe1dfb67b81be8390e`.

[Android execution artifact 12066856320](https://github.com/Russianranger/coh-android/actions/runs/38946462977/artifacts/12066856320)
ZIP SHA256 `cc54633961e0d82e3f7ccca9e2047920eb52fbd03585bc6013414f8e55af35cc`.

The 96-MiB aggregate reservation contract and 4,096-draw fixture ceiling remain
unchanged. This does not establish whole Atlas capacity, asset-semantic
completeness, authentic player identity, ARM64 execution, real encrypted login,
physical Thor acceptance or gates 25–27 completion. The adapter is not activated
in Combined. No accepted APK, profile or gameplay module is changed.
