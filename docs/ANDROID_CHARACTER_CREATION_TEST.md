# COH Character Creation 0.9.0 — one Thor session

The signed candidate passed hosted graphical creation, first Atlas connection
and ordinary logout/save in run **36862027713**, at APK and driver source
`bc4d750deab00f0fdbbd084b32b563aa3abdddce`. Its size is **386,658,292 bytes** and
SHA-256 is `001e1dc4db87f1184814a8f75a33953504d6ee06b238490a8c26c71c4ca7f963`.
See the [hosted review](android-evidence/character-hosted-36862027713.json) and
[package review](android-evidence/character-package-review-36862027713.json).

**Known limitation:** the creator's Male/Clear preview is complete, but hosted
Atlas scenery remained black/incomplete. Its HUD and welcome appeared, and the
normal save succeeded. This session tests creation/save; rendered Atlas scenery,
broader costume coverage and gameplay need further work. Save once
**Character connected** is confirmed, even if the scenery remains black.

Local login on Thor is already accepted. This session creates **THORHERO**, enters
Atlas Park and saves through the game's ordinary logout. Exact-character reopen
after a restart is the following milestone.

This candidate includes a small verified supplement for the **Male body and the
costume selected by Clear**. Its rendering is part of hosted qualification. Use
that reset for this test; other bodies and costume choices need broader asset coverage.
The existing imported assets stay in place; no additional import is requested.

## Update

1. Install `COH-Character-Creation-0.9.0.apk` over **COH Local Login 0.8.1**.
   Keep the installed app and its storage. Version code 4 retains the same app
   identity and signing key.
2. Open the app and tap **1 · Refresh runtime** after this update. Keep the existing
   imported assets. Wait for **Runtime ready**. An update preserves the private
   database, Wine profile and compatible client caches.
3. Start character creation once. Keep the app foreground while its private
   database, Atlas server and client start. Wait for **Client ready for input**.
   This startup adds Atlas preparation to the accepted login startup.

## Create and save

1. Cancel any Quality/Ultra prompt. Enter `COHLOCAL` / `offline` and check that
   the visible account is exactly **COHLOCAL**, including its first C, before
   pressing Log In. Select `127.0.0.1`. **Send text / L3** replaces a
   focused text field when its **Replace** option is checked.
2. Wait for **Local login verified**, then open an empty **Create Character** slot.
3. On the initial Origin screen, choose **Primal Earth** and **Science** and enter
   the exact name **THORHERO**. Continue with **Ranged → Blaster**, then choose
   **Archery / Snap Shot** and **Devices / Web Grenade**.
   Select **Male**. On the **Costume** screen,
   tap **Clear** at the bottom to reset the randomly selected initial costume.
   Keep the resulting costume and default power colors, then continue to registration.
4. Press **Play**. Decline the tutorial, choose **Hero** and confirm creation so
   the character enters **Atlas Park**. Leave the game visible until the app
   shows **Character connected** and enables **Save character / log out**.
   Record the world appearance; black/incomplete scenery is the known limitation.
5. Tap **Save character / log out** once. This enters `/quittologin` through the
   game. Allow the logout countdown to finish without moving or pressing keys.
   Wait for **Saved character verified**, after committed character records and
   three fresh Android captures. **Character saved** is an earlier stage.
   The expected game screen after logout is the login screen.
6. When enabled, tap **Finish and save report**. Wait for completion and cleanup,
   then **Export latest report** and send the ZIP. Include whether the Atlas Park
   environment appeared and whether the app confirmed the character's save.

The interaction window lasts twenty minutes after input becomes ready. The app
requires the same session's map connection, ordinary logout, committed database
records and fresh captures before accepting success. Initial world entry serves
the creation/save test; combat and performance testing come later.

## If something fails

Export the current report without another long boot. If still running on an
unexpected screen, use **Abort operation**, wait for cleanup and export. Include
the last visible message or screen. Keep the app storage and imported assets.
If **THORHERO already exists**, keep it and send that report; this creation-only
candidate preserves an existing character rather than creating it again.
