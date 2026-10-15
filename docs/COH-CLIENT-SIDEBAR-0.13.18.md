# 0.13.18 Android sidebar controls and Start/Enter

The physical 0.13.17 test reached Atlas and saved/cleaned up normally, but its
requested 10/30 FPS comparison was blocked by unavailable Enter input.
The exact 0.13.17 Activity handled keyboard Enter but omitted controller Start;
the Send text dialog sends printable characters without Return. Aggregate
transport success did not prove command submission. The bounded physical audit
is in `android-evidence/client-sidebar-0.13.17-thor-20261007.json`.

The export confirms about 662.886 seconds (11:03) to the input-ready client,
223.323 seconds local Atlas startup, and 178.431 seconds client startup.
An additional 277.118 seconds elapsed before observed server login; this is
interaction/wait, not initialization. Login-to-world was 67.910 seconds.
The actual accepted Game and its 30 FPS launch record were present. The limited
route sampled 9.609 Hz, 103.406 ms main work and 0.023 ms explicit pacing; it does
not establish a controlled comparison or a performance gain. No repeated
custom-texture error identities or suppression progress records occurred on
this route, so physical duplicate-suppression benefit remains unverified.

The fix adds sidebar Show FPS, 10 FPS and 30 FPS actions. They submit only the
three fixed native commands through the existing atomic RFB chat route, including
Enter, without arbitrary command entry. Enter / Start is also available in the
sidebar, and controller Start queues one paired Enter transaction per physical
press, including short taps, with repeats consumed. Existing L3 text entry,
movement, pointer, save/task input and emergency releases remain retained.

FPS actions require the current visible owned post-Atlas session and fresh
world views. Input and competing save/task actions are held during a command.
Session/PID/decoder identity, input epochs, pause, cancellation, reconnect,
queue rejection and session deadlines retain authority. Status says submitted,
not applied: the native game does not acknowledge these commands to the Android
button. Fixed safe action names and timestamps are recorded without typed text
or credentials. Close existing chat/dialogs with B/Esc before a sidebar command.
The setup label is corrected to Set up / update runtime and the sidebar caption
identifies 0.13.18.

This release recompiles the Android shell from five reviewed Java changes while
retaining the published 0.13.17 Game, native proofs, all 75 runtime payloads,
servers, assets, beacons, cache schemas, llvmpipe, resolution and graphics profile.
The embedded runtime manifest stays byte-identical to 0.13.17. Therefore a ready
0.13.17 installation needs no repeated setup or import for this Android-only
update. This conclusion must be checked against the actual candidate and public
APK; it is not a generic rule for future native/helper updates.

The release lane requires full retained qualification and new input/queue/
package scenarios, seven PostgreSQL fixtures, authenticated native ancestry,
exact runtime conservation, bounded Java changes and DEX reconstruction,
SDK 35/signing checks, a fresh prepublication audit and an independent audit
of actual public APK/checksum/testing-note bytes. Final pins and gate results
belong in HANDOFF and the publication receipt after those gates pass.

Follow `COH-Atlas-Gameplay-0.13.18-testing.txt` for the direct sidebar comparison
and Start/Enter test. Physical 0.13.18 controls, performance and stability remain
pending. Continue client scene/frame optimization from that evidence; zoning
remains deferred and the accepted native optimization is not reimplemented.
