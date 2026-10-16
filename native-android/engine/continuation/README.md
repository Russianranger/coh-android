# Primary protocol continuation qualification

This additive harness qualifies six independent modules: `scenegraph`,
`entities`, `entity-control`, `character-data`, `entity-globals`, and `auth-interop`. It preserves the existing Combined 0.1.7 APK and
does not modify the shared engine build, support client, server runtime, imported
profile, account, or application data.

The host job runs each module's pinned original-source checks and malformed-input
tests, optionally under ASan/UBSan, plus the existing public crypto source oracle.
It also builds the full auth interoperability host probe and exercises its
isolated TCP cancellation, timeout and rejected-input lifecycle; no success
authentication reply is supplied.
The same module scripts cross-build their standalone tests for Android ARM64 and
x86_64 using their host-generated fixtures. Each ABI has a retained ELF hash and
build receipt. A separate Android 13 job executes the exact x86_64 binaries and
requires the full native JSON result to match the successful host result,
including value types and counts.
The generated scene and entity fixture headers are retained and their exact
hashes must match the host oracle and both ABI build receipts before execution.

These checks do not establish a complete imported world, complete ALLENTS
decoding, authenticated account login, physical Thor acceptance, or completion of
gates 25–27. Auth interoperability tests exercise strict deployment admission and
report redaction without contacting an AuthServer. The public crypto oracle uses
source-layout fixtures. A separately configured compatible server and disposable
account are still needed for real encrypted login evidence.

## Local qualification

Commit the source first for clean-source qualification. Keep all output under an
ignored `native-android/results/` directory or outside the checkout. The output
directory must be empty; a new run cannot replace previous evidence.

```sh
python3 -m unittest discover -s native-android/engine/continuation/tests -v
python3 native-android/engine/continuation/qualify.py \
  --source-root . --sanitize --require-clean --workers 3 \
  --ndk /path/to/android-ndk-r28c \
  --output native-android/results/primary-continuation
```

The harness accepts a dirty local tree only when `--require-clean` is omitted and
records that state explicitly. Hosted qualification requires a clean source tree
before and after the build, and rejects a source revision change during the run.
All independent host failures and logs are retained in `qualification.json` and
`logs/`; a failed batch does not issue a successful Android manifest.

## Android execution

Run against a disposable Android 13 x86_64 emulator with the same exact source
revision as the build. The runner validates hashes, receipts, ELF architecture,
host results, Android SDK, and emulator/device kind before execution.

```sh
python3 native-android/engine/continuation/run_android.py \
  --adb /path/to/adb --serial emulator-5554 --require-clean \
  --artifacts native-android/results/primary-continuation \
  --output native-android/results/primary-continuation/android-execution/receipt.json
```

The runner uses a unique `/data/local/tmp/coh-primary.*` directory and removes
only that directory on completion. It never installs, uninstalls, launches, or
clears an APK. Android commands and failed native output are retained. One failed
suite does not prevent the other independent suites from producing evidence.
Cleanup failure fails the final qualification receipt.

ARM64 binaries are built but are not considered executed by the emulator job.
`--abi arm64-v8a --device-kind physical` can execute these isolated contracts on
an explicitly selected Android 13 device; this still does not mark the Combined
APK physically accepted.

## Workflow and integration boundary

`.github/workflows/native-primary-continuation.yml` runs only on `native-android`
pushes affecting these three new module directories, this harness, or its own
workflow, and on explicit manual dispatch. It does not cancel in-progress runs.
Host/ARM64/x86_64 build evidence and Android execution evidence are separate
artifacts retained for 90 days. Removing this harness/workflow and the independent
module callers is sufficient rollback; the accepted Combined artifact is unchanged.

Each module supplies `check.py --source-root ROOT --output JSON --sanitize --ndk
NDK --android-output DIR`. The host receipt must report `passed: true` and
`checks.release` containing the platform-neutral native test result. Each
`DIR/{arm64-v8a,x86_64}/receipt.json` identifies `passed`, `abi`, `binary`, and
`binary_sha256`. The scene and entity host/ABI receipts also identify
`fixtures_sha256`, with `scenegraph_fixtures.h` and `fixtures.h` respectively
retained at their Android module output roots. The standalone result must contain `passed: true` and positive
integer `checks`. The batch binds the exact host and build receipt hashes in
`android-execution-manifest.json`.
