# Native Android roadmap

Updated 2026-10-21 UTC. Physical Thor 0.1.17 shows textured Atlas pavement and
an observed-pose box in its exported 640x360 full-screen frame.
0.1.18 is signed and CI-qualified; stage 41 remains passed. Thor results are pending.

Both saved packets now reach their exact original zero terminators on the host:
301656 and 303112 bits, through shipping JNI in release, ASan and UBSan.
The tail covers 34 active original handlers plus inline Friends; the source table
has 213 textual entries, 212 active. All 343 unmapped power CRCs are tolerated.
The original ACK/READY send path is wired with a 20-second first-response timeout,
one accepted same-ID retry, clean disconnect and 30 seconds of response observation.
Diagnostic partial-tail fallback is explicit; an incomplete tail stays incomplete.
The 128-message cap can shorten observation; a short window is reported incomplete.
Actual post-READY server behavior awaits Thor. Counts/sizes replace raw payloads.

The host draws all 13 genuine Huge meshes with the original rig, decoded RGB and
authored scales. This is static Ready/base inspection, using the original coarse
no-MULTI/no-BUMP material fallback and a limited texture sampler. Live retains the
box on a missing asset or failed owner/upload. The zones supplement is in the
accepted import set. A different real pose remains unverified without rebuilding.

Next 3 steps: validate 0.1.18 ACK/server traffic and Huge world capture on Thor;
finish any real post-READY update limitation; verify another server-sent Atlas pose.
One physical validation remains to establish the received Huge in the live world.
No database position change or cleanup is scheduled. Gates 25–27 remain open.

Thor procedure for 0.1.18:
1. Install over 0.1.17 without clearing data; retain the same imports and profile.
2. Start the existing server, select the same character and hand off once.
3. Full screen enters the scene; corner Return to controls or Back exits it.
4. Wait 35 seconds after ACK and READY show sent; on timeout/disconnect export anyway.
5. Return to controls, then Back to Combined launcher; tap Export report and save ZIP.
6. Keep the 640x360 scene-capture.png, initial replay, send timing and memory JSON.
7. Stop normally. Do not repeat handoff or change the database for this test.

Caps remain 4 MiB decoded, 16 KiB ordinary, 8 MiB initial, 96 MiB scene, 7168 B report.
Host initial peak is 7534269 B; Huge preparation module peak is 12228910 B.
These source charges are separate from physical 0.1.17 peak PSS 2930128896 B.
Wine identities are included in the next export; PostgreSQL is unchanged.
