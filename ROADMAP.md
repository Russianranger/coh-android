# Native Android roadmap

Updated 2026-10-20. Signed 0.1.17 is qualified and remains unchanged.
Its original source/build passed; exact-APK CI run 39503076641 then passed
45 Android 13 framework checks and 14 update/rollback checks after 2 harness reruns.
The saved initial packet parses to 301656/301656 bits with 343 tolerated unresolved
power CRCs. Original ACK/READY is host tested; live Thor traffic remains unmeasured.
0.1.17 has a 10-second response window and the existing transport retry policy.
Next-APK source adds send timing/bytes, a 20-second deadline and one ACK/READY retry;
it is opt-in, host qualified and has not been packaged or deployed.

Android 13 verifies 1920x1080 full screen, Back and corner return. The 640x360
world host capture shows pavement and the real-pose box; latest Thor is 0.1.16.
The Huge snapshot has 13 visible records and 11 CLEAR, correcting the earlier 14.
Host GLES now draws 10 genuine meshes with the original Huge rig; six textures
decode, and explicit Chest_Stripe_1 appears on chest UVs as a layer inspection.
Missing: huge_emblem.geo, huge_uarmr.geo, huge_waist.geo, complete SH texture lookup
and authored body scales. Host absence does not prove Thor absence; live keeps the box.

Wine PSS is about 2.42 GB; the old 1.83 GB process remains unidentified. Next-source
exports up to 4 prioritized Wine executable/redacted-command identities within the
24 KiB memory cap. No tuning; no world/collision allocation split is available.

Thor procedure:

1. Install 0.1.17 over 0.1.16 without clearing data; preserve profile and imports.
2. Start the existing server, select the same character and hand off once.
3. Use Full screen if needed; dismiss Android's Got it hint if shown.
4. Corner Return to controls or Back exits; Full screen enters again.
5. Wait 30 seconds after handoff before exporting; do not hand off again.
6. Return to controls, then Back to Combined launcher and tap Export report.
7. Save the Combined ZIP; check scene-capture.png is 640x360 and JSON is included.
8. Stop normally; retain the ZIP even after disconnect or timeout.

Next 3: collect Thor export; finish Huge assets/material/morphology for a later APK;
verify archive streaming at another real pose without rebuilding. These 3 steps
remain before a qualified visible world with the genuine character.
Caps: 4 MiB decoded, 16 KiB ordinary, 8 MiB initial, 96 MiB scene, 7168 B report.
Next-source initial peak 7533927 B; Huge explicit source+GPU 6209694 B; host RSS 103168 KiB.
Physical aggregate peak remains 4021653504 RSS / 2925635584 PSS bytes, separately.
