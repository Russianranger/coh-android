# Thor Wine thread cleanup (0.1.5)

**Accepted on Thor:** the [0.1.5 combined device run](THOR_DEVICE_ACCEPTANCE.md)
passed all twelve stages and complete cleanup. Three owned worker witnesses behind
exited leaders were found and cleaned up through pidfds. All thirty process
input/output captures closed; no owned groups remained.

The [0.1.4 Thor report](android-evidence/thor-capture-still-open-20260928.json)
again passed all eleven functional database/Windows stages. Wine initialization
completed in 85.957 seconds. PostgreSQL shut down gracefully and the Wine prefix
lock/socket checks passed, but wineboot output capture remained open. The new
ownership scan reported zero candidates, zero inspection failures and complete
cleanup, so its process accounting did not explain the open capture.

## Reproduced ownership defect

The cleanup code skipped every process whose thread-group leader appeared as
`Z` in `/proc/PID/stat`. That state does not prove the entire thread group has
exited. A leader can call `pthread_exit` while a worker remains alive and retains
the inherited output descriptor.

A native reproduction demonstrated exactly that case: the leader was `Z`, a
worker was live with the exact run token and pipe, the old cleanup reported zero
candidates and success, and the reader stayed open. Signaling the exact owned
thread group allowed genuine EOF. The pinned Wine
[thread exit implementation](https://github.com/wine-mirror/wine/blob/b073859675060c9211fcbccfd90e4e87520dc2c2/dlls/ntdll/unix/thread.c)
uses `pthread_exit` for nonfinal thread exit. This establishes a real cleanup
bug and a plausible explanation for Thor; the device report itself contains no
thread inventory and cannot prove which process retained its pipe.

Version 0.1.5 inspects surviving tasks of an exited leader and authenticates
the same run ownership before signaling the complete thread group. A true
zombie with no live tasks is harmless. Unknown ownership, surviving owned tasks
or a capture that never reaches EOF must still fail. Task observations are
included in the receipt without exposing environment data or ownership tokens.
A single bounded retry handles a leader exiting between its state and environment
or namespace reads, after verifying the same process identity. Missing task
visibility for an existing group remains a failure.

## Accepted hosted qualification

[Run 36364550345](https://github.com/Russianranger/coh-android/actions/runs/36364550345)
passed all five jobs at source `9dc58f62c58dc4fc5c01288071429bf2aa06d2f4`,
finishing on 2026-09-28 at 01:12:14 UTC. All 125 tooling tests passed without
skips. The same-source
[PostgreSQL regressions](https://github.com/Russianranger/coh-android/actions/runs/36364553676)
also passed.

Each ARM64 PRoot job passed both cleanup regressions. In the new case, its
independent snapshot observed a `Z` leader, one live token-owned worker and that
worker's write descriptor for the exact captured pipe. The old zombie skip would
miss the group. Cleanup used TERM then KILL through pidfds and observed genuine
EOF. An unrelated same-UID, same-prefix process running the same executable
survived; that sentinel would terminate if mistakenly signaled. No reader was
closed to manufacture an EOF result.

Fresh and repeated database runs passed all eleven stages; client runs passed
all twelve, with complete cleanup and every input/output capture closed. Client
evidence remains limited to headless llvmpipe rendering, exact RGB readbacks and
synthetic input. The ordinary runtime runs did not need the thread fallback;
the dedicated native regressions exercise it explicitly.

| Mode | Cold initialization | Repeat initialization | Registration passes |
| --- | ---: | ---: | --- |
| Database | 39.343 s | 4.176 s | 1 cold, 0 repeat |
| Client | 39.747 s | 4.277 s | 1 cold, 0 repeat |

These are hosted timings. All downloaded archive hashes, all twelve embedded
APK inputs and all eight hosted reports were verified. The
[acceptance receipt](android-evidence/accepted-wine-threads-36364550345.json)
binds the workflow results, package, payloads and runtime evidence.

Download [coh-diagnostic-apk](https://github.com/Russianranger/coh-android/actions/runs/36364550345/artifacts/10946846847):
`COH-Diagnostic-0.1.5.apk`, version code 6, 13,481,586 bytes, SHA-256
`bf78559ef47d3f679a93be48ca4127baa9c7238e838ed38799dffc7e0710ffd5`.
Runtime manifest SHA-256:
`fba5afaeb8ceaa4fb113102e436f3677d957a1c09d1d20f543cca630979d4203`.

## Historical device retry steps

1. Export old reports, uninstall only **COH Diagnostic**, and install
   `COH-Diagnostic-0.1.5.apk`. Test builds have different signing certificates.
2. Choose **Setup runtime**, then **Run diagnostics**, and export the report.
3. Run **Run client probe** only after diagnostics completely passes. If it
   fails, send the report before further checks.

The device retry above has passed; keep the installed 0.1.5 and runtime.
[Device acceptance](THOR_DEVICE_ACCEPTANCE.md) records the evidence and next work.
Stop/suspend/resume, Android presentation, hardware acceleration, real controls,
audible playback and CoH gameplay remain unvalidated.
