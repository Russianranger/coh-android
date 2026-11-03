# x86 track integration

Updated 2026-11-02 America/Chicago. Integration/handoff only; Claude leads next.
The x86 client is primary; ARM64 stays experimental and shelved.
Keep x86 Win32 servers, PhysX and ragdolls; cold-start goals remain unmeasured here.
Default branch remains main; no release, APK handoff or repository setting change.

- Merge order: sampler-review-fix → startup-60s → modern-runtime-qualification
  → m5-thor (b7806a6bd King's Row docs) → performance-path docs.
- P2/P3 sampler and Windows producer fixes included through 8dc2a66d72477b3c62227e572538b13f0e4f912b.
  See armport/notes/M5-SAMPLER-REVIEW.md and HANDOFF-X86.md.
- Last device result is .44: King's Row cold prep 656.024 s, request→arrival
  711.056 s, loaded render mean 25.63 FPS (11 complete windows).
  See armport/notes/M5-THOR-20261102-RESULTS.md and its export evidence.
- Both zone servers are x86; Atlas stays resident. Preparation swap pressure
  does not prove gameplay causation. No matched pre-port x86 baseline is supplied.
- Save committed, but Wine worker EACCES prevented proved owned cleanup;
  Atlas cache return failed and the data cache remained stranded.
- Historical .46 build40929292200/runtime40945708189/APK40952408285 succeeded;
  modern Thor build checks and retained-runtime execution have different scope.
- Startup instrumentation/ODBC reuse included; gain and ≤60 s remain unmeasured.
  Historical build41363927704 passed; runtime41372922907 rejected old 0119 pin
  before guest launch. Corrected pin and regression are included.
- .37 app/guest work assessed without joining unrelated histories.
- Final port/skip list, local suites, source identity and CI request: HANDOFF-X86.md
  and the x86 integration issue. Use X86-THOR-TEST.md for the next device lane.
