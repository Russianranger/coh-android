# Native Android roadmap

Updated 2026-10-20. Physical Thor 0.1.17 matches the signed, qualified APK.
The full-screen toggle/return works at 1920x1080; the exported 640x360 PNG shows
textured pavement and the yellow real-pose box. No real costume is drawn yet.

This new initial packet is 303112 bits. Huge bodytype 4, 28 parts and 343 tolerated
unresolved powers decode; source update ends at 300152. Application-tail command
205 SERVER_SEND_KARMA_STATS stops at 300248, with 2864 bits remaining. ACK/READY
were neither queued nor sent. The earlier 301656-bit host fixture still reaches EOF;
that result does not establish completion of this different physical packet.
One position was observed; later server movement and post-ACK traffic are unmeasured.

Host-only Huge work draws 10 of 13 genuine meshes with the original rig. Missing:
huge_emblem.geo, huge_uarmr.geo, huge_waist.geo, complete SH/material selection and
body-scale morphology. Six textures decode; one explicit chest layer is inspected.
Live keeps the box. The current pose matches 0.1.16; another pose remains unverified.

Actual latest PSS is 2.876 GB; sampled peak 2.930 GB. Wine totals 2.425 GB, PostgreSQL
0.149 GB. The omitted 1.828 GB Wine process is still unidentified. No new low-memory
exit is recorded; earlier exits remain unexplained. PostgreSQL SHOW is confirmed.
Native closed 2/2 sockets; 7/7 GL contexts completed. Server remained ready/alive.
Next-APK send timing, 20-second/one-retry and process identities remain unshipped.

Reference Thor export procedure:

1. Install 0.1.17 over 0.1.16 without clearing data; preserve profile and imports.
2. Start the existing server, select the same character and hand off once.
3. Use Full screen if needed; dismiss Android's Got it hint if shown.
4. Corner Return to controls or Back exits; Full screen enters again.
5. Wait 30 seconds after handoff before exporting; do not hand off again.
6. Return to controls, then Back to Combined launcher and tap Export report.
7. Save the Combined ZIP; check scene-capture.png is 640x360 and JSON is included.
8. Stop normally; retain the ZIP even after disconnect or timeout.

Next 3, when requested: original KarmaStats/tail to EOF and ACK observation;
finish genuine Huge rendering; verify streamed world at a different pose.
Caps stay 4 MiB decoded, 16 KiB ordinary, 8 MiB initial, 96 MiB scene and 7168 B report.
Physical source peak 7537773 B; capture charge 23682305 B, parent reservation 31866806 B.
Device RSS/PSS are separate from these source charges. Gates 25–27 remain open.
