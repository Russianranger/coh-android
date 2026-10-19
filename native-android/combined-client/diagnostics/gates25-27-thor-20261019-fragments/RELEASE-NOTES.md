CoH Native Combined 0.1.9 is a focused Gates 25–27 diagnostic update for the AYN Thor (Android 13, ARM64).

This corrects two native receive incompatibilities demonstrated against original server source: ordered continuation fragments can carry order ID zero, and an exact-size packet can use a single-sibling envelope. The native client now derives the complete message's order identity from part zero, including when that part arrives last. Existing packet, reassembly, decoded-message and memory limits remain in place.

The world-handoff report also adds bounded receive counters and decode observations. These help distinguish rejected datagrams, incomplete fragment groups, decode limits and a missing response. They contain numeric/Boolean/fixed enum observations; no packet bodies, credentials, account names, character DBIDs or endpoints are added to this report.

This update does not establish the cause of the earlier Thor timeout or complete original character/world acceptance. The scene remains a local preview. It does not grant CLIENT_READY, RECEIVED_CHARACTER, application full-update ACK, actor publication or authoritative world rendering. Gates 25–27 remain open.

Test this changed build once:

1. Stop your existing Combined server and wait for **Stopped**. Stop any other local CoH server too.
2. Install the ARM64 0.1.9 APK over Combined 0.1.8. Keep the app's data; no uninstall or asset reimport is needed.
3. Start the existing server and wait for **Server ready**. Launch the native client, tap **Test world handoff**, and select an existing test character.
4. Keep the app foreground until the result becomes terminal. Export the native report even if it times out or refuses a packet.
5. Tap **Return to launcher**, export the full diagnostic ZIP, then stop the server and wait for **Stopped**.

Keep the existing settings, encryption policy and DB-selected Map endpoint. No new character, forced map or unrelated audio/resource/controller/rendering retest is requested. The earlier device reports remain accepted within their existing scope.
