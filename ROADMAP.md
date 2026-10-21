# Native Android roadmap

Updated 2026-10-20 America/Chicago.
Thor 0.1.18 completed the full 303,112-bit initial packet. ACK and READY were
accepted; one full snapshot and 114 UPDATE messages arrived without disconnect.
The real-pose box and Atlas pavement remain the physical rendering baseline.
The 0.1.18 costume kept the box and its exported PNG was stale.

The final 0.1.19 candidate changes only three things: bounded raw post-READY
fixture export, capture tied to the installed version and current activity
session, and case-insensitive texture names across all verified loaded archives.
The continuation republishes its capture viewport after actor preparation.
The host draws all 13 Huge meshes with the reference helmet texture; the device
keeps the box if an asset or upload fails. A new Thor export must confirm it.

Saved 0.1.16, 0.1.17 and 0.1.18 packets reach exact EOF in release, ASan and UBSan.
Raw post-READY bodies are saved without new decoding. Disk recording is bounded
to 8 MiB including framing and 128 messages, with explicit partial/error flags.
Caps remain 4 MiB decoded, 16 KiB ordinary, 8 MiB initial, 96 MiB scene and
7168 B for the native report. Source initial peak is 7,534,461 bytes; process
RSS/PSS measurements remain separate. No PostgreSQL or Wine tuning was done.

Thor procedure:
1. Install 0.1.19 over 0.1.18 without clearing data; keep imports and profile.
2. Start the existing server, choose the same character and hand off once.
3. Use Full screen; the corner button or Back returns to controls.
4. Wait 35 seconds after ACK and READY show sent.
5. Return to controls, then Back to the launcher; Export report and save ZIP.
6. Keep both replays and the fresh 640x360 PNG, or its stated omission reason.
7. Stop normally and return the ZIP; do not alter the database or repeat handoff.

After this one qualified build is delivered, native-android is frozen.
Further changes require an explicit user request. No cleanup, update decoding,
world expansion, database change, runtime deployment or release is part of this build.
