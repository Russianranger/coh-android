# Source RGBA32 GPU upload handoff

Frozen implementation: `166fdb04f30ff52d2f000af478e2dc953d7cc438`, based on
`e54ceb26cf5dbd6ca74442d2de196827c82265fe`. This directory preserves the exact
new host qualification, three original native stdout records, and one identical
readback chain. `manifest.json` records their byte identities.

`host.json` is 21,518 bytes, SHA256
`e7d609502b1cfc45d1e1e876de2652087b14e1a9e490606560252af126b90ca8`.
Its 29 project source hashes bind actual current bytes and exact committed
blobs. Each native binary is pinned before execution, equal afterward and
rechecked with its readback at final publication. Nine actual production C
objects also link and call through C++.

## Actual host result

Release, AddressSanitizer and UndefinedBehaviorSanitizer each pass 367 checks
and 18 actual GLES readbacks. Each mode uploads two immutable decoded RGBA32
owners and one legacy DXT smoke owner, performs 20 image callbacks including
controlled failures, refuses six cancellation points, recovers a retained
failed-delete journal, and balances nine generated/deleted names. Both provider
holds are dropped, all provider bytes are overwritten/freed before the RGBA32
uploads, and all CPU owners retire before the lease readbacks. Registry retain
and release, context creation/destruction, and Surface creation/destruction each
balance. Final tracked executable-linked calloc blocks are zero.

The independently derived readback chain is 1,488 bytes, SHA256
`91bd157f743e7c25d2b43ba36b93144318f5d885c975e25ac9b19790b912163b`.
It contains legacy red, authentic grey and patterned channel/alpha mip chains,
then the same three chains after CPU retirement. Five semantic mutations are
refused: source aggregate minimum, missing RGBA mip, erased source kind, ignored
late cancellation and erased pending-journal error.

Actual GPU CPU owner size is 1,328 bytes, 32 bytes above the prior 1,296-byte
layout; report size is 176 bytes. The new entry charges its full decoded-source
recorded aggregate without retirement credit, actual GPU owner, GPU reservation
and a 16KiB preparation reserve. Four times the compiler-reported sum of adapter
frames is 8,448 bytes. This stack scope excludes namespace, loader, backend,
callback, libc and driver frames. The test declares 32MiB GPU external and 48MiB
lease external reservations; it does not establish global fit, driver memory or
process RSS.

The actual host is GLES 3.2 Mesa 25.2.8 llvmpipe. Primary EGL/GLES headers,
declared library files and declared compiler file/version are pinned. A complete
system toolchain, standard headers, loaded driver mapping and driver sanitizer
coverage are not established. AddressSanitizer leak detection is disabled;
tracked module calloc lifetime is measured separately.

## Source and integration boundary

The typed `coh_wr_gpu_upload_rgba32` getter consumes the real immutable
`CohWrTexRgba32` owner. The source-kind discriminator prevents cached TexOpt or
legacy-format provenance being fabricated. Legacy upload function bytes match
the baseline after neutralizing only the final report initializer. GPU lease,
protected renderer, JNI, CMake, Gradle and app files are unchanged.

Existing helper changes are dependency lists only: `check_gpu_lease.py` adds
the RGBA32 and namespace C files to `BASE`; `gpu_egl_contract.py` adds those C
files to `SOURCES` and headers to `EXTRA`; both GPU compiler lists and the source
receipt list in `check_sampler.py` add the same dependencies. No old 602 or
sampler qualifier was executed. Root owns the corresponding old Android
workflow embedded list and any workflow helper hash update.

## New Android interface

`tests/run_source_rgba32_android.py` is 19,324 bytes, SHA256
`9fce46b8476668b401c9ad8da6630d0beda1f1fbc84913c70517696cf80063c9`.
The new standalone driver has not built or executed Android yet. Its build CLI
is `build --source-root ROOT --actual-defaults-zip ZIP --ndk DIR --output NEWDIR`.
Its execution CLI is `execute --source-root ROOT --build BUILDDIR --adb ADB
--output NEWDIR [--timeout-seconds 120]`.

The fixed build closure is nine production translation units:
`coh_wr_gpu_lease.c`, `coh_wr_gpu_texture.c`, `coh_wr_texture.c`,
`coh_wr_sampler.c`, `../assets/coh_asset_loader.c`, `../../src/coh_assets.c`,
`../../src/coh_dds.c`, `coh_wr_tex_rgba32.c`, `coh_wr_tex_namespace.c`, plus new
`tests/test_source_rgba32_gpu.c`. It targets arm64-v8a and x86_64 at API26 with
NDK r28c. Root owns the focused Android13 x86 execution and workflow.

Reuse local artifact12118720382, 12,308 bytes, SHA256
`87a999e6c1c003b96a9fa169ce11637b61eb696766517e063fafce73fdc39c24`.
No download or capture was performed. The driver regenerates and checks its
four exact fixture files from this retained archive before use. The genuine
grey body is 894 bytes, SHA256
`b628966e91a864f9edcb0634605823a7ef3d8e2305f36d1a9f6e9834b018a013`.
Pattern and legacy bodies are explicit controls, and the digest predicate is
finite rather than a general SHA implementation.

This is a standalone finite-provider qualification. Current CLIENT namespace,
default identity, material, actor, world, source-generation admission,
production prepare and app-context adoption all remain false. No APK or actual
application mode producer follows from this proof.
