# Catalog/graph/entity source-boundary review on Android 13

This is a read-only, cross-module evidence review for renderer integration. It
adds no adapter implementation and does not authorize a scene or actor to render.

[Catalog qualification run 38946463029](https://github.com/Russianranger/coh-android/actions/runs/38946463029)
passed host job `117126725191` and Android job `117127874587` at source
`fd86ff196f172bf62cd24c7e0f807df39c33e0a5`, tree
`645c6741a1cd2e95a3da4778fe7c770fc08d4ea6`. The optional experimental Win32
export compile job was skipped. No workflow was repeated for this review.

The reviewer independently downloaded both artifacts, checked ZIP digests,
verified every one of the aggregate inventory's 125 source files against the
exact Git commit, and replayed the exact commit's read-only artifact-admission
validator. That admission checks required source closure, original fixture
identities, all host modes, both ABI build receipts, ELF identities and binary
hashes before Android. Android receipt, manifest, qualification hashes and
cleanup were then independently matched. Graph/entity binaries also match the
separate primary run retained in `../android13-fd86ff196/`.

| Standalone suite | Host release/ASan/UBSan and Android x86_64 checks |
| --- | ---: |
| Saved scene catalog | 21,111 |
| Dynamic scene graph and raw metadata | 193,219 |
| Entity, costume and power-customization staging | 1,142,224 |

The catalog stress fixture has 508 files, 12,192 definitions and 36,567 child
links, using 26,276,931 owned bytes and a 52,553,862-byte replacement peak. The
scene-graph stress fixture uses 26,806,591 owned bytes and an 81,706,049-byte
aggregate transaction peak, within its 96-MiB aggregate ceiling. These are
source-produced synthetic fixture observations, not captured Atlas data or
Android runtime memory measurements. The native results were identical across
the qualified host modes and Android 13 SDK33 x86_64. ARM64 binaries were built
and byte-verified but were not executed by this run.

[Host artifact 12066187405](https://github.com/Russianranger/coh-android/actions/runs/38946463029/artifacts/12066187405)
ZIP SHA256 `bcf282299a1c63eaac81704d36f010b6e10a952a35f5b89e499e9a210397d7c5`.

[Android artifact 12066716624](https://github.com/Russianranger/coh-android/actions/runs/38946463029/artifacts/12066716624)
ZIP SHA256 `2e5f0de6e4ef038833687c28be445542df9415e99ff8dc917c37adee78bba520`.

Both ABI receipt identities, exact binary hashes and generated fixture hashes
are preserved in the manifest and independent review. Native command output and
cleanup logs are retained. No installed APK or server profile was touched.

This evidence does not capture an authentic saved catalog, resolve inherited
asset/material semantics, close the complete character/global-tail transaction,
verify encrypted login or establish an authoritative actor. It therefore does
not satisfy renderer activation prerequisites, physical Thor acceptance or
gates 25–27. The fixture's similarity in file/root dimensions to the accepted
server structural report does not make it authentic server content.
