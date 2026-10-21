# Native Android roadmap

Updated 2026-10-20 America/Chicago.
Thor 0.1.18 completed the 303,112-bit initial packet; ACK and READY were accepted.
One full snapshot and 114 UPDATE messages arrived without a disconnect.
The real-pose box and Atlas pavement remain the physical rendering baseline.
Its costume used the box fallback and its exported PNG was stale.

The final 0.1.19 fixes bounded raw post-READY export, capture freshness, and
case-insensitive texture names across all verified imported archives.
The continuation refreshes its capture viewport after actor preparation.
The host draws all 13 Huge meshes with the reference helmet texture.
A Thor export must still confirm the fresh capture and Huge appearance.

Signed ARM64 APK: 15,288,279 bytes, version code 20.
SHA-256: 9383ebd105c3bc75d3df7184c85baf2c55682d43b288fca83525b59a17d0a98a
Build and audits passed in 39542047531. Exact-APK Android 13 qualification
passed in 39543941512 without rebuilding; all shipping and build files match.

All three saved initial packets reach exact EOF in release, ASan and UBSan.
Post-READY bodies are saved without new decoding, capped at 8 MiB including
framing and 128 messages, with explicit partial and error flags.
Caps remain 4 MiB decoded, 16 KiB ordinary, 8 MiB initial, 96 MiB scene and
7168 B for the native report. Source initial peak is 7,534,461 bytes;
actual process RSS/PSS remains the separate 0.1.18 observation. No tuning was done.

Thor procedure:

1. Install 0.1.19 over 0.1.18 without clearing data; keep imports and profile.
2. Start the existing server, choose the same character and hand off once.
3. Use Full screen; the corner button or Back returns to controls.
4. Wait 35 seconds after ACK and READY show sent.
5. Return to controls, then Back to the launcher; Export report and save ZIP.
6. Keep both replays and the fresh 640x360 PNG, or its stated omission reason.
7. Stop normally and return the ZIP; do not alter the database or repeat handoff.

Native Android development is frozen. Further changes require an explicit user
request. No cleanup, update decoding, world expansion or runtime deployment follows.
