# Worker wake and ARM64 publication

Patch 0050 fixes a reproduced scheduling race in the original worker. Before
the patch, the consumer checked the queue, then set `thread_asleep` before
waiting. A producer publishing between that check and the flag store saw an
awake worker and skipped `SetEvent`; the consumer then slept with work queued.
The wake flag now precedes ResetEvent and the final queue check. The native
Android render patch already uses this ordering; no render timing or batching
changes are imported here.

On ARM64 llvm-mingw, command/message start and end indices, the sleep flag and
thread state use sequentially consistent atomic loads/stores. Besides publishing
filled payloads and consumed slots, the global order prevents both sides of the
sleep handshake from missing the other's store. Acquire/release alone on the
two separate variables would not establish that guarantee. Other targets keep
their existing volatile accesses: the i686 path still has a store/load ordering
race under x86 TSO. The reordered flag alone does not fix that path. ArmPort
ships the ARM64 client; the i686 build is only reference/compile coverage.
The event is created before publishing
THREAD_RUNNING, so wtStart cannot return with an uninitialized event handle.

No command layout, order, dispatch callback or gameplay behavior changes. The
extra ARM64 barriers have a potential throughput cost, to be measured during
the Thor play-test; this patch favors a correct baseline.

Local evidence, 2026-10-23:

```
python3 armport/tests/worker_wake.py --source upstream/ouroboros --expect-dispatch 0
final-empty-check publication: dispatched=0 expected=0
wrapped payloads: commands=4096 messages=4096

python3 armport/tests/worker_wake.py --source <patchwork>/src --expect-dispatch 1
final-empty-check publication: dispatched=1 expected=1
wrapped payloads: commands=4096 messages=4096

python3 armport/tests/worker_wake.py --source <patchwork>/src --expect-dispatch 1 --atomic-path
final-empty-check publication: dispatched=1 expected=1
wrapped payloads: commands=4096 messages=4096
```

The temporary harness inserts a barrier immediately after the final empty
check, publishes exactly one command, and releases the consumer. The first
assertion occurs before any flush wakes it. It then verifies 4096 varying-sized
payloads and replies through wrapped queues. Host pthread adapters establish
the scheduling regression only, not ARM64 hardware ordering.

The original WorkerThread.c unit compiled for ARM64 using the repository CMake
toolchain (ninja target `libs/UtilitiesLib/CMakeFiles/UtilitiesLib.dir/src/components/WorkerThread.c.obj`, exit 0).
The Windows harness compiles the complete same worker body for aarch64 and
i686 with llvm-mingw 20250910 and the repository's MS compatibility flags.
CI's `libraries` job runs the original negative control and patched positive
case under the app's ARM64 Wine. Run **40035482170**, libraries job
**120693769990**, passed: original `dispatched=0`, patched `dispatched=1`,
both followed by `commands=4096 messages=4096`. Full job logs contain these
lines; subsequent runs also publish them as check-run notices for ci_results.py.

This is a latency bug, not an established Atlas stall cause: `wtReqFlush`
unconditionally signals the event, and both `wtFlush` and a full command queue
call it. Patch 0050 is not claimed as an M3 loading fix. Run
40032719161 supplies the independent texture-queue trace; M3 still requires
a rendered Atlas frame and the receive-code packet replay.
