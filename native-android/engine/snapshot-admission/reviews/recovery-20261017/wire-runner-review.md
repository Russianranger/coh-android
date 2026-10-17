# Independent Android wire driver source admission review

Reviewed exact candidate `d9266213d8b95d15ab32008474f53cdfe36c1db1` in a clean,
separate detached worktree. No Worker C files were edited. No correctness blocker
was found in the host admission/execution control flow. This review ran synthetic
command-executor controls only; no NDK build, native Android binary or emulator
was available or invoked.

Source and artifact admission:

Both `check_character_prefix.py` and `check_power_ranges.py` now pin their own
module/parser/test/oracle inputs plus `run_wire_android.py`, its nine-method host
test, the loaded adapter and common receipt helper. Each build captures commit
and tree and hashes its module dependencies before/after qualification. Both
ABI receipts bind those same hashes, original-source pins, generated fixture hash
and exact expected native JSON. The host checkers support development checkouts;
the Android runner separately requires a clean execution checkout with the
matching exact commit/tree and all hashes. A dirty build cannot be silently
admitted as a different clean source generation.

`validate` requires the correct standalone schema, incomplete actor/ACK scope,
nine successful host control methods, and identical strict native results in
release, ASan and UBSan. Result dictionaries have an exact key set, positive
integer counts (booleans refuse) and a false incomplete-boundary field. Original
fixtures, per-ABI receipts and binary hashes must match the top-level proof.
Both arm64-v8a and x86_64 PIE ELF identities are checked, even though execution
uses only x86_64. Compile receipts cannot assert execution/acceptance. The running
driver and its actually imported helpers must equal their admitted source hashes;
repinning a changed checkout driver does not bless a differently loaded driver.

`validate_checkout` requires clean Git status, matching revision/tree, all listed
source bytes and exact original source pins. Sparse original files are compared
through committed Git objects with original LF normalization rather than treating
absence as missing history. Source and artifact identities are checked again
after the native result; source drift invalidates emulator qualification.

Execution and cleanup:

Device properties must establish API 33, qemu=1, an x86_64 ABI and nonempty
fingerprint. No physical ARM64-device acceptance is inferred from ARM64 compile
identity. The runner creates a fresh device `mktemp` directory and only accepts
its narrowly matched owned path. It pushes the hash-admitted x86_64 binary,
verifies the remote SHA and runs with a bounded timeout. Attempted command,
known command exit code, structurally valid native execution and exact sanitized
host-result match are separately recorded. Malformed/overclaimed native output
cannot become verified native execution; mismatching valid JSON records execution
without a match or emulator qualification. These are deliberately stricter evidence
states than merely observing that an adb command returned.

Every recognized owned directory is removed in `finally` and absence is then
verified. Either deletion or verification failure clears final pass/emulator
qualification while preserving attempted/native-match facts and error logs.
Malformed `mktemp` output is not treated as a deletion permit. Command output
has a bounded in-memory decode ceiling, not a hard log-file or process-memory cap.

A nonempty output parent is rejected before any adb command or result write.
Source/checker artifact destinations likewise require new outputs; no code cleans
old build artifacts to reuse paths. Prior evidence must be retained separately.

Independent execution:

- Replayed all nine candidate host-control methods: zero failures/errors. They
  cover source/driver drift, missing/wrong ELF, host and fixture/receipt mismatch,
  wrong device, transfer mutation, timeout/failure, malformed native scope,
  native mismatch, cleanup refusal/verification and output decode limits.
- Added 25 independent checks. Both modules and both ABI identities refuse
  invalid ELF class despite updated SHA. Omitted driver/adapter/common source
  dependencies refuse. Wrong source tree refuses. Strict JSON rejects duplicate
  keys, NaN/infinite numbers, boolean counts, extra result keys and claimed
  completion. Occupied evidence directories preserve a preexisting marker,
  create no new result and invoke no synthetic adb commands.
- Fresh receipt retains all reviewed source hashes and confirms stable clean
  source before/after. Synthetic fixture ELF headers are explicitly nonexecuted.

Reproduce the independent review against this exact clean source revision:

```
python native-android/engine/snapshot-admission/reviews/recovery-20261017/wire-runner-review.py --source-root CHECKOUT --output NEW_RECEIPT.json
```

Actual Android builds and Android 13 execution remain workflow prerequisites.
This host review cannot qualify either module on Android or enable character,
PowerInfoUpdate, actor, world or ACK authority.
