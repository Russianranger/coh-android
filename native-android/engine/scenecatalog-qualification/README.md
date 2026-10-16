# Standalone scene catalog qualification

This independent workflow qualifies the catalog importer against exact original
`sendDef` exporter envelopes, the scenegraph regression suite against original
GROUPS producers, and staged entity list transactions against the original entity
field producers. Fixture inputs are synthetic. It does not build or install a
Combined APK, launch a server, authenticate an account, prove live world support,
or replace the user's accepted Combined 0.1.7 package.

Run host release, AddressSanitizer and UndefinedBehaviorSanitizer contracts:

```sh
python3 -m unittest discover -s native-android/engine/scenecatalog-qualification/tests -v
python3 native-android/engine/scenecatalog-qualification/qualify.py \
  --source-root . --sanitize --workers 3 \
  --output native-android/results/scene-catalog-host
```

To also compile standalone PIE test executables for both `arm64-v8a` and `x86_64`,
add `--ndk /path/to/android-ndk-r28c`. Android artifacts require host sanitizer
qualification. Use `--require-clean` for release evidence. Every output directory
must be empty; prior artifacts and execution receipts are never overwritten.

The dedicated [workflow](../../../.github/workflows/native-scene-catalog.yml)
downloads checksum-pinned public NDK r28c, runs the host suites, builds both ABI
ELFs and executes the exact x86_64 executables on an Android 13 emulator. An ARM64
build is compilation evidence until its exact binary is separately executed.
Only a successful Android receipt sets `android_executed`; compile receipts do
not set emulator or physical acceptance.

The artifact retains each original-source-generated header, host receipt,
compiler/test log and both ABI build receipts/ELFs. SHA-256 identities bind the
headers and ELFs to the host results. The aggregate source inventory also binds
native implementations, adapters, original pin inputs and the qualification
driver/workflow. All three sanitizer results must equal the host release JSON.
Before any Android command the runner validates every ABI binary, ELF machine,
byte count, build receipt, source map, fixture and host result, including the ABI
not selected for execution. It rejects path traversal, escaping symlinks,
duplicate JSON keys, non-finite numbers, incorrect JSON evidence types,
incomplete suites and unsupported server or acceptance claims.

Execute preserved artifacts on Android 13:

```sh
python3 native-android/engine/scenecatalog-qualification/run_android.py \
  --adb /path/to/adb --serial emulator-5554 --require-clean \
  --artifacts native-android/results/scene-catalog \
  --output native-android/results/scene-catalog/android-execution/receipt.json
```

For a separately connected ARM64 Android device use `--abi arm64-v8a
--device-kind physical`; a successful run records physical standalone execution
while keeping `physical_thor_accepted` false. The runner verifies device ABI,
SDK, emulator status and pushed ELF hashes, compares each native JSON result to
the exact host result, retains command logs and removes its isolated temporary
directory. It does not touch installed applications or application data.

The default Linux job also runs the nonshipping server export sink and source
staging controls. They use a mocked producer/WinAPI shim and establish neither a
Windows MapServer build nor server execution.

An additional **experimental compile-only** Windows job is disabled by default.
To request it, dispatch the workflow with `experimental_export_compile=true`, or
put `[catalog-export-compile]` in the head commit message of a push that touches
a workflow input path. Ordinary pushes skip Windows. The job waits for the host
and ABI build gate, then runs alongside Android emulator qualification. It
downloads approximately 1.67 GB of exact published startup inputs on a fresh
cache and has a 90-minute budget. It stages the existing certified MapServer
source into a separate directory, applies the explicit nonshipping export
overlay, and builds only `MapServer` with the existing `vs2026` / Win32 /
`OptDebug` configuration.

The compile recorder revalidates the overlay and inherited source, verifies the
actual output is a PE32 i386 executable, and preserves source/input receipts,
patched source, overlays, CMake cache, executable bytes and SHA-256 identities.
Its receipt always records `compile_only=true`, `nonshipping=true`,
`runtime_executed=false` and `deployed=false`. Compilation emits no catalog and
does not change an APK or an active server runtime. Failed builds retain
separately labeled, unaccepted diagnostics.
