# Owned suspended primary-thread resume

This new helper verifies the sole initial thread of a fresh suspended process
before one `ResumeThread` call. It does not create a process, assign a job, read
application data, adjust privileges, suspend an existing thread or accept raw
PID/TID selectors. It never closes the borrowed process handle.

The caller must create its exact `subprocess.Popen` with `CREATE_SUSPENDED`,
retain that returned object/handle, successfully assign it to its owned job,
then call `resume_primary(process)` **once** on the same owner thread. No other
actor may inject/create/resume threads in this child. These launch/assignment
facts are caller preconditions; this standalone helper does not infer them from
an arbitrary running Popen. Its separate development driver must source-bind
that call path. No old/default launcher is changed by this module.

Importing the module performs no WinAPI/DLL access. The default native adapter
is constructed lazily inside the call, supports 64-bit Windows, and loads only
System32 Kernel32. An explicit API double is used by the source controls.

```python
projection = resume_primary(exact_owned_suspended_popen)
if projection['passed'] is not True:
    # Never retry resume, including when a late CloseHandle failed.
    # Terminate/observe/close the already owned child and job instead.
    ...
```

The helper binds the held process handle to Popen's exact PID using
`GetProcessId` and a nonzero `GetProcessTimes` creation timestamp, with `poll()`
showing it remains alive. It takes a read-only thread-only Toolhelp snapshot,
examines at most 65,536 entries, and requires exactly one thread belonging to
that process. A snapshot omitting that thread, containing multiple owned
threads, failing enumeration, returning a short entry or exceeding the bound
refuses. Other processes' thread identifiers are never exported or opened.
`THREADENTRY32.dwSize` is reset before every First/Next call; a returned size
must cover the owner PID field (16 bytes) and fit the 28-byte structure.

It opens only the internally selected TID with noninheritable
`THREAD_QUERY_INFORMATION | THREAD_SUSPEND_RESUME` access. The held thread handle
must report the selected TID and process ID; its creation time must be at least
the held process's creation time. A second complete single-thread snapshot must
select the same TID. Immediately before resuming, held process PID/start/alive
and held thread TID/owner/start are checked again, including unchanged Popen
fields. FILETIME exit fields are ignored because their values are undefined for
live processes/threads. No module/heap snapshot is requested.

The `ResumeThread` return value must be the strict integer `1`: Microsoft defines
it as the previous suspend count, so `0` means it was already running, a larger
count leaves it suspended, and `0xffffffff` is failure. No loop or second resume
attempt is made. `resume_observed` means this exact native result was obtained;
it is not application readiness, successful execution, or a current registry/
network/world witness. A call may have attempted resume before a refusal or
interruption; the caller always cleans its owned child/job instead of retrying.

All acquired snapshots and the opened thread handle are independently closed on
every exit. Failed closes retain ownership in the adapter contract and can leave
handles. Before-resume snapshot close refusal prevents resuming and gets one
final close attempt; later close refusal keeps the first failure authoritative.
An ordinary refusal returns a fixed enum and bounded counts, without PID/TID,
timestamps, handles, paths, native error text or application output. A late close
failure after a count-one resume keeps `resume_observed: true`, `passed: false`.
`BaseException` interruption is rethrown only after independent close attempts,
preserving the first interruption if cleanup also refuses.

The success projection has exactly these fields:

- `schema`: `coh-owned-suspended-primary-thread-v1`.
- Eleven strict true booleans: `passed`, `process_identity_verified`,
  `single_owned_thread_verified`, `thread_identity_verified`,
  `generation_recheck_verified`, `resume_attempted`,
  `previous_suspend_count_one`, `resume_observed`, `snapshots_closed`,
  `thread_handle_closed`, `cleanup_verified`.
- `snapshot_passes`: integer `2`; `snapshot_entries_examined`: integer
  `2..131072`; `secondary_close_failures`: integer `0`; `failure`: `NONE`.

Ordinary refusal `failure` values are `INPUT`, `PLATFORM`, `PROCESS_QUERY`,
`PROCESS_IDENTITY`, `PROCESS_EXITED`, `SNAPSHOT_CREATE`, `SNAPSHOT_ENUM`,
`SNAPSHOT_ENTRY`, `SNAPSHOT_LIMIT`, `SINGLE_THREAD`, `THREAD_OPEN`, `THREAD_QUERY`,
`THREAD_IDENTITY`, `GENERATION_CHANGED`, `RESUME_API`, `RESUME_COUNT`,
`HANDLE_CLOSE`, `API_FAILED`. Fields record only completed checks; a success
validator must enforce the exact schema/keyset/types and all conditions above.

Run the new source/API-double controls only:

```sh
python3 native-android/engine/auth-interop/deployment/test_windows_suspended_thread.py --output NEW-RECEIPT.json
```

Controls bind current helper/test/document hashes before and after. They exercise
wire layouts/flags/prototypes through a Python DLL double, high process handles,
generation/owner/short-entry/multiple-thread refusals, both enumeration bounds,
every controlled API failure point, secondary closes/late resume failures,
interruption preservation and private-canary refusal. They do not call an actual
DLL, Windows API, compiler, child process, registry, service or native runtime.
Actual Windows behavior and the separate launch/assignment driver remain future
qualified gates. No old qualifier or runtime capture is replayed.

Primary Microsoft references read 2026-10-18:

- [CreateProcess flags](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags)
- [Toolhelp snapshot](https://learn.microsoft.com/en-us/windows/win32/api/tlhelp32/nf-tlhelp32-createtoolhelp32snapshot)
- [Thread32First](https://learn.microsoft.com/en-us/windows/win32/api/tlhelp32/nf-tlhelp32-thread32first)
- [GetProcessId](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocessid)
- [GetProcessTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes)
- [GetThreadTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getthreadtimes)
- [OpenThread](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openthread)
- [ResumeThread](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-resumethread)
