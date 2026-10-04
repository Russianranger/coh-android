# Wine TestClient launcher bridge

`TestClientBridge.exe` is a separate diagnostic helper. It starts the accepted
stock or resume-only TestClient binary, owns the stock `TestClientLauncher`
named pipe, and observes the child's real console. It implements no game
networking, entity mutation, SQL, logout, or save behavior. Commands remain
ordinary launcher `CMD` messages. DbServer and MapServer binaries are unchanged.

Build from an x86 MSVC developer shell:

```text
cl /nologo /W4 /O2 /MT /D_WIN32_WINNT=0x0601 database/wine-game/TestClientBridge.c /Fe:out/TestClientBridge.exe
```

The package receipt must bind both `TestClientBridge.c` and `bridge_protocol.h`
(SHA-256 of normalized LF bytes), the resulting PE32 executable, and its import
closure. The bridge links the CRT statically and uses only Windows system APIs.
The source-independent C parser contract runs through
`tools/android/game/test_bridge_protocol.py` on Linux; actual console and pipe
behavior require the hosted Windows/Wine qualification.

Invocation:

```text
TestClientBridge.exe --output Z:\state\create-bridge --version VERSION --timeout 1200 -- Z:\state\runtime\TestClient.exe -db 127.0.0.1 -fakeauth -authname ACCOUNT -dontpause -nosharedmemory
```

The output directory must be new or empty, private, and unlinked. The bridge
creates the launcher pipe before `CreateProcess`, launches with
`DETACHED_PROCESS` so the unchanged client allocates its own console, verifies
the pipe peer and console process list against `PROCESS_INFORMATION.dwProcessId`,
and verifies the initial launcher `PID` message. It sends the version reply only
after publishing a bounded initial console snapshot and verified readiness.

Files:

| File | Contract |
|---|---|
| `events.jsonl` | At most 8 MiB/20,000 complete records; global increasing `sequence`, `kind`, `value`, original `raw`, `elapsed_ms`. Stock pipe bytes use Latin-1-preserving JSON escapes. |
| `console.txt` | Atomic UTF-8 snapshots of the actual child console, at most 16 MiB, 16,384 rows and width 200–256. Changed dimensions, backward row movement or reaching the last row fails closed. |
| `ready.json` | Exact `child_pid`/`transport_pid`, true console/pipe/protocol ownership flags, initial snapshot and one version request. |
| `command-NNNNNN.txt` | Parent atomically writes sequential files starting at 000001. Printable ASCII only, fewer than 4,096 bytes, no newline/NUL, `CMD ` prefix. A `Command` event acknowledges complete `WriteFile` with `command_sequence` and exact text; it does not acknowledge game execution. |
| `stop` | Explicit cleanup request. The final console is retained, then a still-running child is terminated. This is never a logout or save acknowledgment. |
| `result.json` | Final child exit code, forced-stop flag, final snapshot, pipe framing/disconnect flags, counters, limits and nullable error. |

Bridge exit zero requires verified readiness, final console capture, complete
framing, child exit, and no transport/limit/deadline errors. The harness must
independently verify protocol state and committed SQL **before** requesting
cleanup. A clean helper exit does not prove gameplay or Android acceptance.

The containing owned Wine process tree remains the guest harness's cleanup
responsibility, including on external termination of this helper.
