# Actual source RGBA32 Android qualification

The new standalone qualification completed successfully in run
`39083677877`, job `117545684612`, at source commit
`c98bb60fe187458f328a15882089ea742ce6e853` on `native-android`. Artifact
`12119502992` is preserved byte-for-byte as `retained-artifact.zip`: 154,504
bytes, SHA256
`55eb2466fc7701c6bc49d736677321c29b2672754e673aabdb4f88c952413bea`.
The retained GitHub artifact metadata independently binds this digest, run and
source revision; job metadata records all steps succeeding. No artifact was
downloaded by this audit: it reused root's single retained copy.

The archive contains 92 unique regular members. All CRCs and every member's
bytes/hash are checked in `archive-members.json`. Full build/execution logs and
fixtures remain inside the exact archive. The two ELF files, original build and
execution receipts, original native stdout and exact readback are also preserved
separately for review. `audit_artifact.py` performs retained-data admission only;
it executes no ELF, compiler, Android command or old qualifier.

## Build and source binding

Both arm64-v8a and x86_64 standalone executables built with NDKr28c
`28.2.13676358`, API26. The nine actual production translation units plus new
test match the approved ten-file closure. All 28 project source pins match both
current files and exact source-commit blobs; the source tree is
`48c3c041a591e736ef5a8e2f9091f4cf1a6aad67`. Each ABI's 25 compiler-derived
project dependencies match its retained dependency output and source pins.

| ABI | ELF bytes | SHA256 | Executed |
| --- | ---: | --- | --- |
| arm64-v8a | 113760 | `d2d54526f8cc2a0281cb7a659c7c09413637e1f51d8d99f2fcf81e0a7004f8d9` | No |
| x86_64 | 115296 | `e16c0a27ee53d31e28e2a875bd75380d9ee441f97a5c4a10a011cdbae4824a19` | Yes |

Both files are actual ELF64 little-endian PIEs with the correct machine and
`/system/bin/linker64` interpreter. Their actual parsed dynamic tables match
the retained readelf output and contain only EGL, GLESv3, z, m, c and dl platform
dependencies. The build receipt retains 26 selected NDK file pins and the
committed workflow checks the exact NDK archive digest before extraction. This
local audit does not independently rehash a downloaded NDK tree or establish a
complete standard-header/toolchain closure.

The original 12,308-byte defaults archive is unchanged, exact tracked source
data from artifact `12118720382`, run `39078874753`, SHA256
`87a999e6c1c003b96a9fa169ce11637b61eb696766517e063fafce73fdc39c24`.
Deterministic data-only regeneration reproduces all four input files and the
expected readback receipt. The authentic grey TX2 remains distinct from the
explicit patterned RGBA32 and small legacy DXT controls.

## Actual Android result

Only x86_64 executed, on SDK33 / Android13 / Google APIs emulator with requested
SwiftShader graphics. The native result reports GLES3.0 SwiftShader, 367 checks
and 18 actual readbacks. Two source-owned RGBA32 uploads and one legacy smoke
upload succeed; six cancellation points and retained partial-upload deletion
journal recovery are exercised. Nine generated texture names are deleted.
The two provider holds/drops, registry retain/release, one context and one
Surface each balance. Final tracked executable-linked calloc blocks are zero.

Provider bytes retire before RGBA32 uploads; all immutable CPU owners retire
before final GPU lease readback. The complete 1,488-byte chain has SHA256
`91bd157f743e7c25d2b43ba36b93144318f5d885c975e25ac9b19790b912163b`.
It covers legacy red, authentic grey, independently varying patterned channels
and alpha, all mip levels, and the second pass after CPU retirement.

The execution receipt binds the original build receipt, transferred inputs,
readback and final source/artifact admission. Native process completion, native
process cleanup and nonce-path removal/absence checks all succeed;
`process_cleanup_unobserved` is false. Three declared platform library file
hashes agree before and after execution. Loaded driver mapping verification,
Android sanitizer coverage and platform driver sanitizer coverage remain false.

## Scope

The GPU CPU owner is 1,328 bytes versus the prior 1,296-byte layout; report size
is 176 bytes. The entry retains full decoded-source aggregate reservation with
no provider/CPU retirement credit. The test declares 32MiB GPU external and
48MiB lease external reservations. This is not process RSS, driver memory or a
global budget fit proof.

This proves the new typed immutable CPU owner to real GLES upload and unchanged
GPU lease lifetime boundary in its separate finite-provider pbuffer context.
It does not admit an original/current CLIENT namespace, default identity,
material, actor, world, current source generation or the nine world
prerequisites. Production prepare and application-context adoption remain
false. No APK or physical device was built/executed. No old 602, old sampler,
new host suite or unchanged native executable was replayed during this audit.
