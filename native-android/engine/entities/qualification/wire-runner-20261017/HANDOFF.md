# Standalone wire Android execution driver

`run_wire_android.py` executes only the new pre-character prefix or power-range
standalone contracts. It reuses the pinned continuation adapter's
`bounded_execute`, its bounded failure logs, and common strict JSON/path/source/
ELF admission helpers. It does not rebuild APKs, run server services or promote
entity staging into authoritative actors.

Both checkers now hash the running driver, common helpers and negative-control
suite into source inventories and per-ABI build receipts. They retain source
revision/tree, exact expected native results, original-source pins and exact
fixtures. Both native ABI binaries must exist and match their SHA256/64-bit PIE
machine identities. Source, fixtures, build-only false flags, standalone scope,
all release/ASan/UBSan results and exact current runner/helper bytes must match.
The execution checkout must be the exact clean source revision/tree. Original
source LF hashes are rechecked using local source files or pinned Git objects
when sparse checkout omits them.

Build each module into a separate new artifacts directory OUT, outside the
checkout so generated evidence does not dirty the source tree:

```
python native-android/engine/entities/check_character_prefix.py \
  --output "$OUT/qualification.json" --ndk "$ANDROID_NDK_HOME" \
  --android-output "$OUT/android"
```

For ranges, use `check_power_ranges.py` with the same arguments. Then, on an
independently started Android 13 x86_64 emulator:

```
python native-android/engine/entities/run_wire_android.py \
  --module prefix --source-root "$CHECKOUT" --artifacts "$OUT" \
  --adb "$ADB" --serial "$SERIAL" --output "$NEW_EVIDENCE/result.json"
```

Use `--module ranges` for the range artifact. NEW_EVIDENCE must be empty and
outside the checkout. Each driver records actual SDK/QEMU/ABI/fingerprint and
serial. It owns only its validated mktemp `/data/local/tmp/coh-wire.*` directory,
pushes the SHA-bound x86_64 binary, verifies its device SHA, and executes under
a device 90-second KILL deadline with a host bound. Native stdout must exactly
match every sanitized host result. It rechecks artifact/driver/source bytes and
source state after execution. Cleanup removes the owned directory and verifies
absence; cleanup refusal revokes `passed` and `emulator_qualified` even if native
execution and result matching occurred.

Build receipts always retain `executed=false`. Separate execution receipts
record command attempted/exit status, validated native execution and exact-result
match independently. A failed adb/shell/timeout or invalid stdout does not prove
native execution. A structurally valid native result differing from host records
`android_executed=true`, `native_match=false`, and qualification fails. Complete
character, full PowerInfoUpdate, authoritative actors, full live world and
physical Thor flags remain false in all scopes.

`test_run_wire_android.py` covers both artifact formats using synthetic ELF
headers, temporary Git repositories and an injected command executor. No fake
ELF header is executed and no real adb/device is used by those tests. Nine test
methods cover wrong machine ABI, missing executable, overclaims, host mismatch,
fixture/receipt drift, source drift before/during execution, repinned driver
mutation, wrong Android version, changed push bytes, failed native command,
timeout, invalid/overclaimed native stdout, native-result mismatch, rm and
post-rm absence failures, plus a real bounded-log decode-ceiling control. The
checkers execute these controls and retain their explicit Android-false summary.

Local controls and both native host/sanitizer suites passed. No NDK or Android
emulator was available in this worker. The coordinator must run actual dual-ABI
build and actual Android13 x86_64 execution in CI; this handoff makes no device
execution claim.
