# Outer character prefix continuation

Worker C was pinned to recovered unpublished primary
`4f6fe92107a10323a90123c6856de578943300e2`. Existing very-rare suffix and teammate
buff parsers are preserved. This addition closes only the exact first outer
`sendCharacterToClient` / `receiveCharacterFromServer` pre-character boundary.

Implemented `coh_character_prefix.*`: five raw packed server settings, original
128-byte account entitlement array, player type/subtype/praetorian progress and
location. Original `bsWriteBitsArray` / `bsReadBitsArray` unconditionally align
the auth array to a byte boundary. Normal bit-packed mode must do so too.
Packed settings remain raw 32-bit values; source does not require boolean-only
values. Rounded scalar fields reject values beyond their declared bit widths.
Parsing has no allocation, uses a 304-byte static host frame, rejects aliases,
and preserves both the original reader and output on every refusal. Sensitive
account entitlement bytes are retained as raw staging, with no logging or
export and no entitlement application.

The checker extracts and pins the exact original pre-character statement blocks
rather than claiming whole-function `sendCharacterToClient` qualification.
Original complete bitstream producer/consumer functions execute with synthetic
entity/account/server-state shells. Client skin changes and subsequent
`character_Receive` are outside this boundary. Host original oracle is not
sanitized; native production/tests are separately checked under ASan and UBSan.

Reproduce from this checkout:

```
python native-android/engine/entities/check_character_prefix.py --output /tmp/coh-character-prefix-new.json
```

The retained host receipt records all input and production source hashes and
checks unchanged-before/after identity. It records 280 original producer/consumer
cases spanning both scalar alignment modes, all eight starting bit offsets,
packed transitions through UINT32_MAX, and full auth-array patterns. Controls
exercise every truncation point with unchanged cursor/output, each oversized
rounded scalar field, original ignored array padding, invalid cursor and alias
refusal. C++ boundary linking also passes.

No Android toolchain was available in this worker environment: Android ARM64
build, Android 13 execution, physical Thor and real-server acceptance remain
unqualified. No shared build files were changed. No completion ACK or actor
admission was added. Production use must remain behind a future complete
transaction owner.

The next missing outer character body is the existing standalone
`character_Send` grammar plus its dictionary-bound application, followed by
original-power-set names / ally / PvP / full self statistics / trays / windows /
account and UI tails. PowerInfoUpdate remains missing after the character body;
its original implementation is in `Common/entity/PowerInfo.c` and includes power
redefinition and boosts, four status arrays, inspiration/boost changes and a
range list even when the outer update flag is zero. Treating that flag as an
empty body would desynchronize the original packet. All of these plus exact
message end must validate atomically before any authoritative actor receipt.

## Optional Android build continuation

The checker additionally accepts paired `--ndk` / `--android-output` and optional
`--fixtures-output`. Its existing `--output` invocation is unchanged. Output
receipt and fixture paths must be new; Android output must be a new directory.
Unpaired arguments and missing ABI drivers refuse before producing any output.

```
python native-android/engine/entities/check_character_prefix.py \
  --output /tmp/coh-prefix-build.json \
  --fixtures-output /tmp/coh-prefix-original-fixtures.h \
  --ndk "$ANDROID_NDK_HOME" \
  --android-output /tmp/coh-prefix-android
```

It builds `arm64-v8a/coh_character_prefix_test` and
`x86_64/coh_character_prefix_test` with API 26, C99, `-Wall -Wextra -Werror
-pedantic`, using exactly the generated original producer/consumer fixture
header used in the host tests. The Android directory retains that header.
Per-ABI `receipt.json` binds the compiled binary SHA256, fixture SHA256,
production/header/test/checker hashes, original source pins and Git revision/tree.
All build receipts say `executed=false`; creating a receipt cannot qualify
Android execution. The existing `test_character_prefix.c` is the standalone
source-pinned Android driver. It prints the same 280-fixture / 646561-check JSON
on successful actual execution, with `whole_character_complete=false`.

A coordinator may push the x86_64 binary to a running Android 13 emulator and
execute it as a narrow standalone driver. Its exit status and stdout must be
retained separately and bound to the exact receipt/binary hashes and emulator
identity. Do not mutate the build-only receipt into an execution claim. This
worker had no NDK/Clang or Android emulator, so its local validation covers host
build/sanitizers, retained generated fixtures and CLI rejection semantics only.
Android compilation and execution remain pending the coordinator's CI.
