# Native Android roadmap

Updated 2026-10-20. Signed 0.1.17 is qualified and remains unchanged.
Its original source/build checks passed; the exact APK later passed 45 Android 13
framework checks and 14 update/rollback checks in CI run 39503076641.
The saved initial packet parses to 301656/301656 bits with 343 tolerated
unresolved power CRCs. Original ACK/READY sending is implemented and host tested.
Actual Thor sends, responses and position changes have not been observed yet.
0.1.17 retains a 10-second, 128-message response window; the requested 20-second
window, one transport retry and detailed send timing are next-APK source work.

Android 13 verifies a 1920x1080 full-screen view, Back and corner return.
The 640x360 host capture shows textured pavement and the yellow real-pose box.
The latest physical evidence is 0.1.16; a new Thor capture remains necessary.
The Huge snapshot has 13 visible records and 11 cleared records; the earlier
14-record count was incorrect. The original Huge rig is recovered and verified.
The eleven GEO paths include huge_emblem.geo, huge_uarmr.geo and huge_waist.geo;
actual availability of those three files remains unproved. Live keeps the box.

Retained Wine PSS is about 2.42 GB, including an unlabeled 1.83 GB process.
Map/DB startup took 279/67 seconds; no world/collision allocation split exists.
Process identity export is next-APK work. PostgreSQL settings stay unchanged.

Thor procedure:
1. Install 0.1.17 over 0.1.16 without clearing data; preserve profile and imports.
2. Start the existing local server; select the same character and hand off once.
3. Use Full screen if needed and dismiss Android's Got it hint if shown.
4. The corner Return to controls button or Back exits; Full screen enters again.
5. Wait 30 seconds after the handoff before exporting; do not hand off again.
6. Return to controls, then Back to the Combined launcher and tap Export report.
7. Save the Combined ZIP; check scene-capture.png is 640x360 and JSON is included.
8. Stop the server normally; retain the ZIP even after disconnect or timeout.

Next: collect that Thor export, finish genuine Huge mesh/texture rendering,
and verify archive streaming at another real pose without rebuilding.
Caps remain 4 MiB decoded, 16 KiB ordinary transport, 8 MiB initial aggregate,
96 MiB scene transaction and 7168 bytes per native report. Source replay peaks
at 7533495 bytes. Physical peaks remain 4021653504 RSS / 2925635584 PSS bytes;
these are separate from source accounting. Gates 25–27 remain open.
