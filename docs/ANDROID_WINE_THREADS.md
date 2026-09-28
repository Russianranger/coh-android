# Thor Wine thread cleanup retry (0.1.5)

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

Version 0.1.5 must inspect surviving tasks of an exited leader and authenticate
the same run ownership before signaling the complete thread group. A true
zombie with no live tasks is harmless. Unknown ownership, surviving owned tasks
or a capture that never reaches EOF must still fail. Task observations are
included in the receipt without exposing environment data or ownership tokens.

## Qualification

Hosted qualification is pending. Keep the ordinary detached-helper regression
and add the exited-leader/live-worker regression under the actual pinned PRoot,
alongside fresh and repeated database/client diagnostics. The new case must
preserve unrelated processes and prove genuine EOF after bounded cleanup.

## Device retry

1. Export old reports, uninstall only **COH Diagnostic**, and install
   `COH-Diagnostic-0.1.5.apk`. Test builds have different signing certificates.
2. Choose **Setup runtime**, then **Run diagnostics**, and export the report.
3. Run **Run client probe** only after diagnostics completely passes. If it
   fails, send the report before further checks.

Physical 0.1.5 acceptance, Android presentation, hardware acceleration, real
controls, audible playback and CoH gameplay remain unvalidated.
