# Thor test: COH Atlas Gameplay 0.13.72 (ARM64 client): the fast server and the lighter monitor by default, the save-after-travel fix, and fewer stopped calls

0.13.72 is 0.13.70 plus two changes that reduce what the system-call monitor
has to stop. If you have not tested 0.13.70 or 0.13.71, test this one instead:
the steps are the same. All three come from your 0.13.69 launches A, B and C
(2026-11-12).

**What those launches showed**

- Launch C (fast server) was in the world 4 min 0 s after the launch began;
  A and B took 5 min 43 s and 6 min 6 s. The app reported each about 70 s
  longer, because it learns of the connection from the server log, which the
  game holds back for 60 to 90 s.
- In launch C your character was saved, but the app never said so. You
  pressed Save before the app had been told you were back in Mercy Island,
  and it then refused the confirmation. That is fixed.
- The graphics-call option worked on the phone (47 microseconds per call
  without it, 0.8 with it).

**What changed**

- **Fixed:** Save after travelling.
- **New defaults**, each with a tick box to go back: **Fast server** and
  **Lighter system-call monitor**. They are stored under new names, so they
  are on even if you unticked the old ones.
- The lighter monitor now also counts the calls it still stops and puts the
  count in the report. That count decides the next frame rate work.
- New in 0.13.71: the monitor no longer stops the call a server uses to look
  for new connections. In CI that was 17 % of everything it stopped (1,340
  times a second). The count now also names the program behind each call.
- New in 0.13.72: the app's own supervisor script re-reads the state of
  every process once in 15 s instead of about once in 3 s. Those reads were
  most of that script's file calls during play.
- A zone's navigation map is no longer re-checked file by file at every
  start (16 s per start, 57 s on a first visit to a zone).
- The report holds the time the game itself reached the zone server.

Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.72", "0.13.71" and "0.13.70 and the Thor test of 0.13.69".

CI at e9f375739: build 43812957778 passed; stock-travel runtime 43823341031
(`early_zone=true`, `proot_ioctl_filter=true`, sampler and call profile; one
trip); trusted runtime 43828305781 created and reopened a character (its
interactive job took 1892 s); APK 43833348924 published 0.13.72 (sha256
`4ab62eccbb78bc12759bccdb9032752358d4234801260a3239e15eb587281583`). Runtime
43823341031: PRoot served 25.8 million stops in the 1,164 s creation session
and 10.4 million in the 887 s reopen session (0.13.71's 43383782947: 27.9 and
11.8 million). Reopen by program: MapServer 40 %, wineserver 25 %, the guest's
Python 12 % (22 % before), audio bridge 9 %, client 8 %. The supervisor's
wrapped file calls in that session: 267,606 (527,031 before).

## Steps (update in place: no uninstall; assets and the navigation map pack stay imported)

1. Install 0.13.72 over what you have. The app should still show
   **Navigation maps 1.0.0 · verified; reusable with this APK**.
2. Check the options: **Fast server** and **Lighter system-call monitor**
   should both be ticked without you touching them. Leave everything else as
   it is.
3. **Launch A** (the new defaults). **2 · Reopen saved character**, log in
   with `COHLOCAL / offline`, select Ralakar, **Enter Game**.
   - Stand where you arrive for about a minute with the FPS display on.
   - Travel to Port Oakes (the ferry), stay a minute, travel back to Mercy
     Island, and press **Save character / log out** soon after you arrive.
     This is the case that failed in 0.13.69. "Saved character verified" can
     still take a little over a minute; that delay is not fixed yet.
   - **Finish and save report**, then export the report.
4. **Launch B** (the same again). Close the app from recents, open it and
   repeat step 3 without the travel: just stand a minute, save and export.
   This shows what a second launch costs now that both zones' maps are
   recorded.
5. Optional **Launch C**: tick **Draw on the game's own thread (frame rate
   experiment)**, repeat step 4 standing in the same spot, export, untick.
6. Leave **Keep a spare zone server loaded for travel** unticked: its first
   CI run showed the spare loading but not being used, so there is nothing to
   measure on the phone yet.
7. **Storage and cleanup**, **Scan storage**, export the storage report.

If the game does not start at all with the new defaults: untick **Lighter
system-call monitor** and try once more; if it still fails, untick **Fast
server** as well. Either way, open the app, **Recover interrupted reports**
and export the top report so I can see which one it was. If an error box
appears in the game, tap **Ignore** (not Stop Program), note what it says and
keep going.

## Report

The exports of the launches you ran, the storage report, and for each launch
roughly how long Enter Game took and the frame rate you saw standing still.
Fields I will read:

- `proot_stop_counts` (the calls PRoot still stops, by number and by program) and
  `armport_proot_ioctl` (`reading`, `getsockopt_stops`).
- `armport_client_timeline`: `first_connected_seconds_after_guest_start` and
  `observer_seconds_after_client`.
- `launch_receipts.zone_graph_71` and `zone_graph_72`: `status` (`reused` in
  launch B) and `reason`.
- `character_saved_event` after the trip in launch A, and the app's `zoning`
  record.
- `character_zoning.initial_zone.early_start`, the client's
  `ARMPORT_FRAME_RATE_V1` lines, `wine_priorities`, `memory_trace`.
