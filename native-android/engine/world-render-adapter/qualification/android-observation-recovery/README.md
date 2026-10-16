# Android concurrency-harness recovery

Hosted baseline source `2d94aad69ed303d3587c509321eb7e79cb44f0b7`, primary
run **38939957550**, passed all 16,720 adapter checks in release/ASan/UBSan and
built exact ARM64/x86_64 standalone binaries. Independent review verified source
commit/tree, every source-byte hash, generated matrix fixture, binary SHA256 and
ELF machine, and source/result parity across both ABI receipts.

Host artifact: **12062457449**, SHA256
`bbc44c94bab1b7b9b9e1f9d01c8cc0cecc22478c41da780159265e2280449c4d`.

Android 13 x86_64 then executed the adapter test and failed its final combined
concurrency assertion: `!atomic_load(&c.failed) && atomic_load(&c.reads)>0`.
The original retained log does not distinguish inconsistent state from no reader
observations; scheduling alone is not established as the cause.

Failed execution artifact: **12062687561**, SHA256
`2a1437861759fe1bb4d90cbf0ddd2d941c960be45bfc9a5633b2ec7e79fa67df`.
`failed-010.log` and `failed-android-receipt.json` preserve that result. The receipt
correctly leaves emulator qualification false and confirms temporary cleanup.

Correction source: `a23e693b7e34277009a1ef170c8332b824c94463`. Only the test harness
changes. It now requires all three readers to observe generation 1, each
128-generation checkpoint, and generation 2000 before stopping. Independent
reader/writer execution remains concurrent throughout the 128-publication
bursts. Ten-second bounded condition waits report observed generations, read
count and consistency-failure flag separately. Final consistency, read count
and each reader's last generation are separate assertions.

Clean-source release, ASan and UBSan each pass **16,745 checks** with identical
native JSON (`host-sanitizer.json`). Android requalification of this correction
is pending. Production adapter C/H, renderer, APKs and runtime remain unchanged.
No geometry deduplication optimization was made.
