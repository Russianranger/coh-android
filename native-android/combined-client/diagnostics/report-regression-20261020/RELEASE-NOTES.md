# Combined 0.1.11 report diagnostic — Thor test

This follow-up fixes the Combined 0.1.10 world-handoff `REPORT_LIMIT`
regression. Essential protocol/capture phase, GROUPS/REQALLENTS/initial packet,
first failure, request/receive counters and owned cleanup observations survive
bounded serialization. Extended diagnostic omissions are explicit. Android uses
a separate native owner-state query so incomplete JSON cannot mark an active
owner idle or repeatedly service an already completed initial capture.
Unknown initial-packet observation is reported as unknown.

Package `org.coh.nativecombined`, version `0.1.11-report-diagnostic-test`, code
12. The existing public test signer and data-preserving update path are retained.
No server binaries, PostgreSQL data, imported assets, Wine/FEX state, saved
profiles, memory policies or parser limits are changed. No automatic reconnect
or application ACK is enabled. Gates 25–27 remain open; genuine server-world
entry, complete authoritative character and live world rendering are not claimed.

## Thor procedure

1. Export the current launcher report and stop the server cleanly. Keep the
   previous qualified APK for rollback. Install this ARM64 APK over Combined;
   do not uninstall, clear storage or reimport existing data.
2. Start the same server and wait for server ready. Launch the native client,
   tap **Test world handoff** once and select the existing test character.
3. Export the native JSON after capture or the first explicit failure. Confirm
   `world_handoff.phase` retains the actual phase, including `INITIAL_OBSERVED`
   when observed, and inspect `report_truncated`/omission metadata. An omitted
   optional detail is expected; `REPORT_LIMIT` replacing the report is not.
4. Leave the completed capture open briefly, then Home/resume. Confirm no
   automatic reconnect or repeated initial-capture service. Return to launcher
   and export its ZIP; confirm owned sockets and renderer resources retire.
5. Stop the server cleanly and export another launcher ZIP. Keep both exports
   and the native JSON with the exact APK SHA below. Report any first-failure
   or unknown-observation result without treating it as world-entry proof.

If rollback is needed, a retained debuggable APK can use `adb install -r -d`.
The ordinary installer may reject a version downgrade. Preserve app data.

Qualification is host release/ASan/UBSan plus signed ARM64 package/source audits
and Android 13 x86_64 framework, scripted protocol/lifecycle and update/rollback
tests. Emulator peers use controlled source-layout fixtures; they are not the
original AuthServer/DbServer/MapServer. Physical Thor acceptance of 0.1.11 remains
pending after delivery. The offline preview is still the accepted scene.
