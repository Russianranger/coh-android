# Combined 0.1.10 memory diagnostic candidate — physical acceptance pending

This candidate adds bounded memory observations and typed unsupported states.
It preserves the accepted offline preview, installation identity, imports,
server executable, profile and existing admission thresholds. It does not admit
a runtime catalog, complete character, actor, READY or application update ACK.
Only install an independently audited ARM64 artifact after both ABI builds,
Android 13 framework/import/lifecycle checks and focused fragment/memory checks
pass. A build artifact is not physical acceptance.

1. Keep the accepted 0.1.9 APK. Install the qualified candidate over Combined;
   do not uninstall, clear storage or repeat imports/setup.
2. Start the existing local server and wait for Ready. Launch the native client.
   The added memory line distinguishes system headroom, Java headroom, app
   RSS/PSS, observation phase and sample age. Unavailable is an expected result
   when Android denies a measurement.
3. Tap Test world handoff and select the existing test character. Initial packet
   observation still reports incomplete character, missing catalog generation
   and unresolved resource identity. The image remains the offline preview.
4. Tap Sample memory once. Press Home, resume from Recents and explicitly
   reconnect if desired. Press Return to launcher. Confirm the server remains
   available; do not force-stop the application.
5. Export the launcher ZIP, stop the server cleanly and export another ZIP.
   Retain both exports and the candidate APK identity.

The `memory_diagnostics` field contains at most nine latest phase slots per app
process, request/sample elapsed times and sampled RSS/PSS peaks. Startup is an
app service-start observation, not proof of a cold server cache. PAUSE covers
Home and other Activity pauses such as SAF. FINAL_CLEANUP is requested after
both client-owner teardown tasks return; existing native cleanup receipts still
decide whether resources were actually released. SERVER_STOPPED is requested
only when the owned guest is no longer alive. Requests may share one later
control-worker sample; timestamps expose this delay. Sampling is event driven
and at most once per second, so peaks are observed samples, not absolute peaks.

Self process memory excludes owned Wine/FEX/PostgreSQL/DbServer/MapServer
processes. Their total is explicitly unavailable because no verified owner
adapter is installed. No shared RSS sum or renderer allocation estimate is
presented as device RAM. Diagnostics do not reserve memory or authorize heavy
integration. Existing ServerMemoryPolicy remains the admission authority.
