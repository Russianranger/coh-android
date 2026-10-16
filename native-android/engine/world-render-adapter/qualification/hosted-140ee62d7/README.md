# Exact hosted adapter build, Android command not attempted

Source commit `140ee62d7b648de737fcec5e7d80b52bfbb9ae67`, tree
`1564740084820438298a580040e1382ae21ed1fe`.

[Primary run 38943674280](https://github.com/Russianranger/coh-android/actions/runs/38943674280)
completed host job `117117312284` successfully. The adapter release, ASan and
UBSan results agree on 16,745 checks, including 512 original matrix cases,
5,000 bounded mutations, 2,000 publications with three concurrent readers,
4,096 draws and zero render-path allocations/frees. Source files were independently
hashed against this exact Git commit; generated oracle, both ABI receipt maps,
ELF machine types and binary digests were checked.

[Host/ABI artifact 12064401812](https://github.com/Russianranger/coh-android/actions/runs/38943674280/artifacts/12064401812)
ZIP SHA256: `5a4fdce958d76293acc584dbfba9dc8d2bfd128d8dbe58369b0bf420ee1f32e3`.

| Standalone binary | SHA256 | Status |
| --- | --- | --- |
| ARM64 | `c509cd378a161d1de75c0c9bf2b241ca6df3d561a7d3874fcedd715882f8b790` | Built; not executed |
| x86_64 | `089c75aff4c8b514bf12b18ec1c0f515c34b766fdb53953dc740c28bddfdaaec` | Built; not executed |

Android job `117117986050` failed in the preceding scene-graph suite at
`test_scenegraph.c:164`; the exact assertion is retained. Entity and auth-policy
suites in that job passed within their scopes. The job's shell exited before
invoking the adapter runner: **the adapter Android command was not attempted**,
and no adapter execution receipt exists. This is not a repeated adapter
concurrency-test failure and is not emulator qualification of the adapter.

[Android artifact 12064093925](https://github.com/Russianranger/coh-android/actions/runs/38943674280/artifacts/12064093925)
ZIP SHA256: `6da3355a63bd3d1d38c76b979c710d0be59f4421427f9dd95360a306a779ef0d`.

The earlier adapter failed log and its diagnostic limitations remain preserved
in `../android-observation-recovery/`. No accepted APK, runtime or gameplay module
changed here. This evidence qualifies fixture/source/lifecycle contracts only;
complete server scene/actor prerequisites, genuine world entry, physical Thor
acceptance and gates 25–27 remain unavailable.
