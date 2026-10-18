CoH Native Combined 0.1.8 is a Gates 25–27 diagnostic build for the AYN Thor (Android 13, ARM64).

This adds **Test world handoff** to the native client. It uses your existing local server and an existing character, observes GROUPS, queues the ordinary REQALLENTS request, and reports the initial-packet result. New numeric diagnostics associate that specific request with its transport queue/send/retry/peer-ACK observations. A transport ACK is not an application full-update ACK or proof of complete server character/world acceptance.

The offline preview remains a preview. This build does not send CLIENT_READY, RECEIVED_CHARACTER or an application full-update ACK, publish a server-backed actor, or enable authoritative world rendering. Gates 25–27 remain open until their required actual transactions and world state are accepted. The APK is a physical compatibility/diagnostic test, not a completed gameplay release.

Update and test:

1. In your existing Combined app, stop the server and wait for **Stopped**. Stop any conventional launcher server too.
2. Install the ARM64 APK over the existing Combined app. Keep its data; do not uninstall or reimport your files.
3. Start the server and wait for **Server ready**, then launch the native client.
4. Tap **Test world handoff**, choose an existing test character, and keep the app foreground until a terminal result appears. Export the native report even if it times out or refuses a packet.
5. Tap **Return to launcher**, export the full diagnostic ZIP, then stop the server and wait for **Stopped**.

If the first attempt is stable, make one additional attempt and press Home while it is active. Return to the app, verify that the connection was cancelled/suspended rather than silently reconnected, then explicitly start a fresh test and export its report. This checks ownership and cleanup for the new network mode; no additional audio, asset, controller or rendering gate tests are requested.

Existing imports and server settings are sufficient. The DB chooses the actual saved Map endpoint; do not force a map, change ports/encryption, or create a new character for this diagnostic. Character names remain transient picker content. Exported new diagnostics contain fixed numeric/Boolean/enum fields, not raw packets, account names, DBIDs, cookies or endpoints.
