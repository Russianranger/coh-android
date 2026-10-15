# COH Local Login 0.8.1 — one Thor session

> Completed on Thor. The [October 1 acceptance](android-evidence/local-login-thor-20261001.json)
> supersedes the device-test request below; retain these instructions as history.

Corrected build from source `1fb4c6057fda579da1913670889922ba8e53bbdc`:
[run 36785793934](https://github.com/Russianranger/coh-android/actions/runs/36785793934).
Hosted saved-profile refresh and graphical-login qualification passed. Root
screenshot review confirms the empty **Server Used/Total: 0/12** selection screen.
The next acceptance step is this one physical Thor session.

APK: `COH-Local-Login-0.8.1.apk`, 373,849,564 bytes.
SHA-256: `2f9663f43c24b071714a7ea2f63a2f8abd624a49bca4b64298f58c7e56278a20`.
The retained signing certificate SHA-256 is
`92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282`.
See the [hosted review](android-evidence/local-login-hosted-36785793934.json)
and [package review](android-evidence/local-login-package-review-36785793934.json).

Version 0.8.1 corrects Wine registration after an in-place runtime update. It
preserves the Windows profile and existing assets/caches, verifies the installed
Wine registration timestamp, and requires the real PE32 probe before continuing.
It also handles the consumed readiness marker left by the failed 0.8.0 attempt.
No reset or manual file repair is required.

This milestone connects the graphical client to its private local PostgreSQL and
DbServer, then displays an empty character-selection screen. The database remains
on the device after cleanup. World entry, audio and hardware acceleration remain
later milestones; the accepted touch/controller/text checks need no repeat.

## Update the existing app

1. Install the supplied `COH-Local-Login-0.8.1.apk` as an update to **COH Local Login
   0.8.0** (or **COH Client Interaction 0.7.0**). It uses the same app identity and
   signing key, with Android version code 3. Do not uninstall the old app or clear its storage.
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
   Wait for the empty character-selection screen with **Server Used/Total: 0/12**
   and twelve **Create Character** slots. Do not create a character yet.
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
