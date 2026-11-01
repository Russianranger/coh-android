# MapServer startup experiment status

Updated 2026-11-01 America/Chicago. Target <=60 seconds on Thor remains UNPROVEN.
Branch: armport/mapserver-startup-60s; base 8dc2a66d72477b3c62227e572538b13f0e4f912b.
Task commits: a14d1a838 (measurement), 95a09d11d (ODBC reuse), then this status commit.
Current exact head: git rev-parse HEAD. No protected branch or release changed.

- Latest playable Thor comparison: .44/a5bd2bbe3, APK run40743596575/artifact12840043807.
- Latest built predecessor: .46/code61, build40929292200/runtime40945708189/APK40952408285.
  The .46 modern Win32 server is built/source-checked, not runtime/device validated.
  Runtime CI qualified retained .10 only; last formal handoff approval is .45.
- Added outer supervisor request/preparation/spawn/ready timing, distinct resident
  returns, explicit failures/invalid clocks, existing full-console native phase logs.
- Native 0119 now observes startup after quiet argument processing; readiness,
  database durability, gameplay, collision and physics behavior are unchanged.
- ODBC experiment skips repeated MSI only for matching installed bytes and inputs;
  every launch still executes native registration/DLL/export checks. Gain unmeasured.
- ARM64 physics closure is unresolved: bundled PhysX2.8.4 has Win32/x64, no ARM64.
  Client NOVODEX disabling cannot qualify server physics; x86 lane retained.
- Validation: full ArmPort suite419 passed with pristine c86 baseline + javac module;
  source10/package26/producer8 checks passed; 11 compiled positive +2 original
  negative controls per actual retained/modern source. ODBC9 + timing7 + login15 pass.
  Additional affected lifecycle suites pass; known base fixture/namespace failures
  remain documented. See evidence/mapserver-startup-*-host-checks.json.
- Reserved .47/code62 packaging is wired; NO candidate APK, acceptance timing,
  new shipping-PE/runtime execution, persistence run, or physical test exists.
- Blocker: connector has no dispatch operation; shell GitHub authentication is401.
  No exposed Thor test connection. No job continues after this checkpoint.
- Next: authenticated serial build (build_server_metrics=true), retained runtime,
  exact modern full-data/runtime and disposable-DB correctness tests, signed APK
  plus real server-package rollback; then five cold starts/map + reboot/gameplay.
- Full identities, commands, hypotheses, limitations and handoff:
  armport/notes/MAPSERVER-STARTUP-60S.md. Integrate task commits in parent order
  only after their M5/.46 base dependencies, with modern runtime and Thor evidence.
