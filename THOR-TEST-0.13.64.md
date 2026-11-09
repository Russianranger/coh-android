# Thor test: COH Atlas Gameplay 0.13.64 (ARM64 client): fast camera turns

In 0.13.63 the game closed while you turned the camera quickly in Mercy Island:
"Local display connection failed: RFB rectangle count exceeds limit" (export
20261109-154935). The game itself was fine; the app's display reader stopped.

The app receives the game's picture as screen updates, each a list of changed
rectangles. A fast turn changes the picture in many separate places, so an
update can hold many rectangles: your session averaged 176 per update. The
reader accepted at most 1024 in one update. When one update had more, the app
treated the display as broken and closed the game, about 10 seconds with the
last picture frozen, before its menu came back. 0.13.64 accepts every update
the display protocol can describe (up to 65535 rectangles); each rectangle is
still checked against the 800x600 picture. The report now records the largest
update it read (`presentation_timing.rfb_update_rectangles_max`).

The session ended without a save, so Reopen starts from Ralakar's last save.

Not fixed yet: Mercy Island has no navigation graph (its server log says
"Beacon file not loaded for map: maps/City_Zones/V_City_01_01/V_City_01_01.txt"),
so pets and NPCs there cannot walk to a target. Your pet still follows you,
but it attacks only enemies already near it. Atlas Park and King's Row have
graphs. Mercy Island's comes in a later version. Everything else is 0.13.63:
[THOR-TEST-0.13.63.md](THOR-TEST-0.13.63.md). Evidence:
[HANDOFF-X86.md](HANDOFF-X86.md), "0.13.64".

CI: CI_SUMMARY

## Steps (update in place: no uninstall, no new import)

1. Install 0.13.64 over 0.13.63. Your imported assets and the database profile
   (with Ralakar) stay.
2. Leave the options at their defaults (**Game's own zone travel** on, ARM64
   client).
3. **2 · Reopen saved character**. Log in with `COHLOCAL / offline`, select
   Ralakar, **Enter Game**.
   - In the world, turn the camera quickly for about a minute, the way that
     closed 0.13.63: left and right, up and down, with whatever you used then
     (right stick, shoulder buttons or a drag). The picture should keep moving.
   - Play normally for a while: defeat a few enemies, so the save has
     experience to keep.
   - **Save character / log out**, wait for **Saved character verified**, then
     **Finish and save report**.
   - If the picture freezes again, wait until the menu comes back, note its
     message and export the report.
4. **Storage and cleanup**, **Scan storage**, export the storage report.

If an error box appears, tap **Ignore** (not Stop Program), note what it says
and keep going. If the app closes by itself, open it, **Recover interrupted
reports**, export the top report, then also export a storage report (it holds
Android's reason).

## Report

The export of step 3 and the storage report, whether the fast turns kept the
picture moving, and anything odd. Fields I will read: `app_error`,
`receiver_error`, `presentation_timing.rfb_update_rectangles_max`,
`presentation_timing.delivered_frames_per_window`, `gameplay_progress` (the
save of step 3) and the storage report's `android_process_exit_history`.
