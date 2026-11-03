# COH-ArmPort status

Updated 2026-11-02 America/Chicago. User paused development; documentation only.
PR #8 remains draft; M5 is unaccepted.

- M3 merged (PR #6): build 40407492746/replay 40407492734 passed partial scope.
- M4 accepted/merged (PR #7, review 5660940046); armport/M4-REPORT.md.
- Last device-tested app: 0.13.44; ARM64 client, Turnip/Zink, x86 MapServers.
  APK run 40743596575/artifact 12840043807, sha256
  2cf80a03a0161fc42581147f0c75d8f22ea2ad93fc8884c9abab5c72388e5c1b.
- New exports: 20261103-010459 (reopen/zoning/save) and -010516 (setup only).
  User: King's Row still performs poorly, worse than before the ARM port.
  Cold destination prep 656.024 s; request→arrival 711.056 s; Atlas return 59.130 s.
  Loaded King's Row: 25.63 weighted render FPS across 11 complete windows.
  This is not a server tick rate; no matched pre-port gameplay run is supplied.
- Both zone servers remain x86; Atlas stays resident. Contention is plausible.
  Preparation-only RSS/swap observations do not establish gameplay causation.
  Server tick/file-duration, gameplay CPU and thermal measurements are absent.
- Committed save after zoning preserved state; owned cleanup failed on worker
  permission checks and blocked cache return. No unhandled client fault recorded.
  Details: armport/notes/M5-THOR-20261102-RESULTS.md and
  armport/evidence/20261102-thor-results.json; source ZIP digests are recorded.
- .45 approved for handoff by Claude 5692088051; no .45 device result supplied.
- .46 at 8dc2a66d: build 40929292200, runtime 40945708189, APK 40952408285 passed.
  Artifact 12931682996; Claude comment 6508052528 is CI evidence, not review.
  Thor server built/source-checked; retained CI is a different server lineage.
  No newer formal handoff approval or .46 device validation is recorded.
- P2/P3 sampler fixes and Windows producer fixes are on armport/sampler-review-fix.
  Old failed build 40805020119 is superseded; no dispatch is requested here.
- Next implementation waits for user instruction. Future diagnosis needs matched
  baseline runs and zone tick/CPU evidence; retirement/esync remain unproven.
  No code, native patch, runtime, APK, merge or release changed for this update.
