# Thor test: COH Atlas Gameplay 0.13.62 (ARM64 client): any character name, unlocked controls

In 0.13.61 you created the villain Ralakar and played Mercy Island. The app
only recognized a character named THORHERO, so it never recognized Ralakar.
It kept walking (the sticks and the on-screen pad) and **Save character / log
out** turned off the whole time. 0.13.62:

- **Any name the game accepts** (3 to 20 letters, spaces or punctuation). It
  is still one character per install; the app now follows that character by
  its database ID under whatever name you gave it.
- **Walking is not locked.** It works as soon as you are in the game, without
  waiting for the app to recognize the character. It only pauses while Save
  character / log out runs (moving would cancel the game's log-out), after the
  save, and while you change zones.
- **Reopen saved character** (the button was "Reopen saved THORHERO") opens
  Ralakar in the zone it was saved in.
- A save after ordinary play (experience, influence, a trained level) in
  Mercy Island or any other zone the game started is now checked the same way
  as in Atlas Park, so it can be verified.

Everything else is 0.13.61: [THOR-TEST-0.13.61.md](THOR-TEST-0.13.61.md). Same
limits: one character per install; at most two zone servers; NPCs outside Atlas
Park and King's Row stand still; missions are not served. Station travel (Game's
own zone travel unticked) still follows only a character named THORHERO, so keep
that option on. A creation session still ends 20 minutes after the game opens
(plus the zone's start), so save soon after you are in the world; Reopen has no
time limit. Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.62".

CI: CI_SUMMARY

## Steps (update in place: no uninstall, no new import)

1. Install 0.13.62 over 0.13.61. Your imported assets and the database profile
   (with Ralakar) stay.
2. Leave the options at their defaults (**Game's own zone travel** on, ARM64
   client).
3. **2 · Reopen saved character**. Before the game opens, the app should say
   that Ralakar is saved in Mercy Island and that Mercy Island starts when you
   press Enter Game. Log in with `COHLOCAL / offline`, select Ralakar, **Enter
   Game**. Mercy Island's server files were prepared in 0.13.61, so this start
   should be faster; note the time from Enter Game until you are in the world.
   - Walk with the stick right away. The movement buttons should work as soon
     as the world is on screen. (They also work on the login and character
     screens now, where the stick types W, A, S or D like a keyboard, so leave
     it alone there.)
   - Play normally for a while: defeat a few enemies (your pets count), so the
     save has experience to keep. Change zone if you like (a ferry or a door).
   - **Save character / log out**, wait for **Saved character verified**, then
     **Finish and save report**.
   - The 0.13.61 session ended with Quit instead of Save, so the game kept
     only what it had saved by itself. If Reopen stops before the game opens
     (for example "powers or costume are incomplete"), note the message and
     export the report.
4. **Reopen again**: you should arrive where you saved in step 3, with the
   experience kept. Save/log out, **Finish** and export.
5. **Storage and cleanup**, **Scan storage**, export the storage report.

If an error box appears, tap **Ignore** (not Stop Program), note what it says
and keep going. If the app closes by itself, open it, **Recover interrupted
reports**, export the top report, then also export a storage report (it holds
Android's reason).

## Report

The exports of steps 3-4 and the storage report, the Enter Game to world times,
whether walking worked at once, and anything odd. Fields I will read:
`character_profile_eligibility.character_name`, `character_reopen.name`,
`client_ready_evidence` (its `source` should be the zone's stock log),
`gameplay_progress` (the save of step 3), `character_zoning.initial_zone`,
`stock_travel.starts`, and the storage report's `android_process_exit_history`.
