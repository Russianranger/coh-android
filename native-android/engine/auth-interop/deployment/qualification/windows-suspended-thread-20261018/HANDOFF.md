# Suspended-thread helper: source/API-double handoff

Five new paths only: `windows_suspended_thread.py`, its new controlled tests,
`WINDOWS-SUSPENDED-THREAD.md` and this proof directory. Existing registry,
activation, default/selected launchers, source, profiles and workflows unchanged.

The fixed `resume_primary(process, *, api=None)` API verifies one fresh,
already-job-assigned `CREATE_SUSPENDED` Popen before one primary-thread resume.
D owns the exact suspended launch, assignment and one-shot caller integration.
The helper never launches or accepts PID/TID selectors, borrows the retained
process handle, and does not infer suspension provenance from arbitrary Popen.

`mock.json` passes 12 new controlled methods on Linux/Python 3.12.14: 197,264
modeled API calls, all 19 modeled success-path API failure sites, at most two
owned model handles, exact 65,536-entry limits in each of two scans and one-past
refusal. Counts describe the finite fixture, not an OS/global memory guarantee.
Python DLL-double controls check real ctypes declarations, 28-byte thread-entry
layout, pointer width, rights, flags, dwSize reset/short refusal, API error and
metadata-only behavior without calling a DLL. Three source hashes match before
and after the final new control run.

Identity checks bind the held process handle/PID/start/alive and one internally
selected thread handle/TID/owner/start, then repeat both generations and a full
single-thread snapshot before `ResumeThread`. Only previous suspend count one
passes. Refusals never retry resume. A late-close refusal can leave a handle and
retains `resume_observed: true` after an actual count-one observer, while
`passed` and `cleanup_verified` remain false as appropriate. Independent close
attempts preserve primary errors/interruptions. No raw identities, timestamps,
handles, paths or error text leave the fixed projection.

E independently read the frozen native signatures/layout/identity/cleanup and
explicit caller-contract scope; no concrete blocker found, no E execution.
Final Git/proof binding and D's separate exact call-site source map remain
independent review steps.

No actual Windows API/DLL, process/thread, compiler, registry, service or native
runtime ran. No old qualifier or capture was replayed. Actual Windows behavior,
the new driver's launch/assignment contract and a live development transaction
are not qualified by this standalone source/API-double proof.
