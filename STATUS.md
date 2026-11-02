# MapServer startup experiment status

Updated 2026-11-01 America/Chicago. Thor <=60 seconds remains UNPROVEN.
Branch armport/mapserver-startup-60s; base8dc2a66d72477b3c62227e572538b13f0e4f912b.
Exact qualification head is frozen by the coordinator-only kickoff; see git HEAD
and live draft PR9. No protected branch, merge, release or repository setting changed.

- Playable Thor comparison: .44/a5bd2bbe3, APK40743596575/artifact12840043807.
  Latest predecessor APK .46/code61 (build40929292200/runtime40945708189/APK40952408285).
  Its modern Win32 server was built/source-checked; last formal approval is .45.
- e563 build41363927704 passed all10 jobs, including both Win32 MapServers.
  Modern PE SHA f893cee6cd6c4dc8b7c45c8b5f7c07572aaabbe50ee5b8730b9ddd3da12dac94.
- Actual Windows ACK41372568968 passed unchanged commit/blocked/failed-write
  checks and postrun binary hashes; this is not gameplay or app-DbServer proof.
- App runtime41372922907 failed staging after5.419s, before guest/map launch:
  stale guest0119 hash49c0... versus actual5656... . No APK was dispatched.
  Coordinator41363909847 and modern/rollback upstream waits failed accordingly.
- Corrected pin + independent actual-file regression; real packages now admit.
- Primary Android service-entry→ready-event receipt clock now includes all
  Android/guest preparation and suspend. UI-action/world and guest/native clocks
  are separate; ready telemetry changes no input/save/readiness or timeouts.
- Contiguous PG/Wine/DbServer route + narrower ODBC interval; single owned-launch
  kernel HWM/RSS and sparse thermal-severity/battery observations have explicit
  exclusions. Aggregate server peak/PSS/CPU temperature/movable proof stay unknown.
- ODBC reuse still verifies inputs/actual DLL and executes native probe each launch;
  cache<4KiB, gain unmeasured. Win32 physics retained; ARM64 SDK closure unresolved.
- Corrected validation: ArmPort443; Android timing6 +69 existing cases;
  guest timing16/memory16/saved-map14. Actual official SDK35 all24 Java sources,
  resources and D8 passed; resources/manifest retained except version metadata.
- Source/native/ACK/staging failure/repair/SDK evidence: armport/evidence.
- Next: fresh exact build→retained runtime→signed .47/code62; separately modern
  full-data Atlas pair + original-server saved-data reopen and actual ACK checks.
  Refresh supporting cohort IDs; serialize primary then real rollback APK build.
- No installable .47 APK, modern asset-backed runtime, startup result, physical
  install/recovery, five-run Atlas/King's or reboot/gameplay acceptance exists.
- Thor unavailable. Complete CI/APK audits first, then physical capture procedure:
  armport/THOR-STARTUP-CAPTURE.md; full continuation armport/notes/MAPSERVER-STARTUP-60S.md.
  Integrate task commits in order after their inherited M5/.46 dependencies.
