# COH Local Login 0.8.0 — one Thor session

Candidate qualification is pending. The APK's accepted build receipt and SHA-256
must be recorded before this procedure is issued for device testing.

This milestone connects the graphical client to its private local PostgreSQL and
DbServer, then displays an empty character-selection screen. The database remains
on the device after cleanup. World entry, audio and hardware acceleration remain
later milestones; the accepted touch/controller/text checks need no repeat.

## Update the existing app

1. Install the supplied `COH-Local-Login-0.8.0.apk` as an update to **COH Client
   Interaction 0.7.0**. It uses the same app identity and signing key, with Android
   version code 2. Do not uninstall the old app or clear its storage.
2. Open the updated app. Tap **1 · Refresh runtime** if setup is required, then
   wait for **Runtime ready**. Keep Internet available for any required download.
   The refresh preserves cached inputs, the completed asset import, Wine state
   and compatible prepared/generated client caches.
3. Keep the existing imported assets. **Import assets (new install only)** is not
   part of this update. If the app does not recognize the completed import,
   export its report and tell us before doing another import.

## Log in once

1. Tap **2 · Start local login** once. Keep the app foreground and screen visible
   while its local server and client start. Wait for **Client ready for input**;
   loading artwork can appear several minutes before the client is ready.
2. If the game's Quality/Ultra graphics prompt appears, tap **Cancel**.
3. Tap the game's **Account Name** field, then **Send text / L3**. Send `COHLOCAL`
   with **Replace focused game field (Ctrl+A)** checked. Confirm the field shows
   exactly `COHLOCAL`, replacing the previous `COHINPUT` or any saved text.
4. Tap the game's **Password** field, open **Send text / L3**, replace the dialog
   text with `offline`, keep **Replace focused game field (Ctrl+A)** checked, and
   tap **Send**. This is the local test password; use these supplied values.
5. Tap the game's **Log In**, then select its single `127.0.0.1` server row.
   Wait for the empty character-selection screen with its empty character slots.
6. Leave that screen visible until the Android status says **Local login
   verified**. Server logs can take about 60 seconds to flush; the app then saves
   three fresh Android captures. The general capture counter alone does not mean
   this step is complete.
7. Tap **Finish and save report** and wait for cleanup and **Local login check
   complete**. Tap **Export latest report** and send the ZIP. State whether the
   empty character slots appeared and whether **Local login verified** appeared.

The interaction window lasts three minutes after input becomes ready. The app
also finishes when that window expires. No character creation, world entry or
Settings test is requested in this session.

## If this session fails

Export this session's report without another long boot. If the session is still
running on an error or an unexpected prompt, use **Abort operation**, wait for
cleanup, then **Export latest report**. Describe the last visible screen and any
message. If cleanup is blocked, follow the app's recovery message and preserve
the report; do not uninstall, clear storage, or restart the test.
