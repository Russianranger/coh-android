# Standalone control-state qualification

`host.json` records exact original source/file/function hashes, the generated
oracle hash, fixture hash and native source input hashes. The source baseline is
Worker F parent `d841d3bddb08d3c15cb6dc7fe0cef4be593e283d`; only the new
`engine/entity-control/` directory is changed in this continuation.

Command:

```sh
python3 native-android/engine/entity-control/check.py --source-root . \
  --sanitize --output native-android/engine/entity-control/qualification/20261016/host.json \
  --fixtures-output /tmp/entity-control-fixtures/fixtures.h
```

Release, ASan and UBSan each passed 667,138 checks with identical result objects.
The 90 original complete producer fixtures yield 280 independently executed
original TEST_CLIENT consumer comparisons, plus finite-value, truncation,
generation, rollback, byte mutation and deterministic random input controls.
The original producer/consumer runs on trusted padded source fixtures; historical
code is not claimed sanitizer-clean. See the module README for exact shells,
recording refusal, future-push and prediction limitations.

Implemented and host/source qualified. Android ARM64/x86_64 builds, emulator
execution, physical Thor acceptance and genuine server interoperability are
pending. This environment has neither an Android NDK nor `cmake`; direct C
compiler qualification ran, while the additive CMake target remains unexecuted.
No APK, server, profile, shared build or gameplay module changed. No ACK or
full-update completion was enabled.

Worker C independently reviewed the original grammar, all flags, array ABI,
finite-value admission, stale and ID-only semantics, generation checks and
rollback. No blocker was found within this staging scope. That review inspected
code and documentation; it did not independently execute the test suite.

Worker B independently reproduced all 667,138 release/ASan/UBSan checks and
reviewed the bounded native/source contract. Its review identified a test-only
portability issue: struct-assigned rollback snapshots could change padding
before byte comparisons. All rollback snapshots now use `memcpy` into byte
arrays. The same qualification was rerun after that correction; production
decoder behavior and source fixtures are unchanged.
