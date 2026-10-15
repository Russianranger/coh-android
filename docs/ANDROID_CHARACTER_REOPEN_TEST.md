# COH Character Reopen 0.10.0 — one Thor session

This milestone reopens the **existing COHLOCAL / THORHERO, character ID 1** from
the accepted Thor creation/save session. Keep the installed app, its storage,
and the imported assets. No character creation, deletion or reimport is needed.

The candidate retains the same package and signing key, with version code 5.
It includes the missing Atlas geometry and referenced textures, refreshes the
affected private compiled map caches, and uses the game's ordinary `/stuck`
command to recover the character saved at Y=-2000. The original import and
accepted cache archive remain unchanged. Package and hosted qualification
receipts will be linked here after the build completes.

## Update and reopen

1. Install **COH-Character-Reopen-0.10.0.apk** over the existing 0.9.0 app.
   Keep app data. Open it and tap **1 · Refresh runtime** once after updating.
   Wait for **Runtime ready**. Keep the existing imported assets.
2. Tap **2 · Reopen saved THORHERO** once. Keep the app foreground while the
   private database, Atlas server and client start. Wait for
   **Client ready for input**. The interaction window then lasts twenty minutes.
3. Cancel a Quality/Ultra prompt if one appears. Log in with **COHLOCAL / offline**
   and check the first **C** is present before pressing Log In. Choose
   **127.0.0.1**, select the existing **THORHERO**, and press **Enter Game**.
   Keep the current costume and powers. **Send text / L3** can replace the
   focused account/password field with its **Replace** option checked.

## Recover and save

1. Wait for **Saved character reopened**. Dismiss the Welcome/help popup with
   **OK**, then tap **Return to safe ground** once. Stay still while it delivers
   `/stuck` and checks two native server positions at least 25 seconds apart.
   Log flushing can delay confirmation; allow several minutes.
2. Wait for **Atlas position verified**. Look for Atlas ground, buildings and
   scenery, and a complete character with the existing costume. Note whether
   the character appears to stand on the ground. This session does not require
   walking, combat or editing the costume.
3. Tap **Save character / log out** once. Allow the normal logout countdown to
   finish without moving or pressing keys. Wait for **Saved character verified**,
   after committed database records and three fresh Android captures. The game
   should return to its login screen.
4. Tap **Finish and save report** when enabled. Wait for completion and cleanup,
   then **Export latest report** and send the `coh-character-reopen-*.zip` file.
   Include whether Atlas scenery appeared, whether the character stood on the
   ground, and the final app message. A screenshot of the recovered world view
   is useful alongside the ZIP.

The checks require the same saved character, unchanged powers/costume, an
ordinary login count increment, native position observations after recovery,
normal logout/save and fresh Android captures. Stable position evidence does
not establish collision throughout Atlas; wider gameplay and customization
remain later milestones.

## If a step fails

Do not start another long boot or create a replacement character. If an
unexpected screen remains, tap **Abort operation**, wait for cleanup, then
export the report and include the last visible message. Keep app storage and
imported assets. If THORHERO is missing or the app reports a baseline mismatch,
send that report before changing the profile.
