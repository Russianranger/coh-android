# Thor test: COH Atlas Gameplay 0.13.73 (ARM64 client): socket traffic no longer monitored, the zone map check fixed, and a sampler for the frame rate

0.13.73 comes from your 0.13.72 launches A, B and C (2026-11-17).

**What those launches showed**

- In the world 4 min 21 s, 3 min 51 s and 3 min 45 s after the tap (goal:
  under 5 minutes). The zone server took 168, 154 and 149 s to start.
- Save after travelling worked (Mercy Island, Port Oakes and back; the trip
  back took 17 s).
- Frame rate: 19-26 steady, 35-59 looking another way, as you saw. In the
  slow direction the whole game used less than one CPU core and no thread
  was busy more than about 30 % of the time. It is waiting on something, and
  the report did not say on what. Launch C ("Draw on the game's own thread")
  made no difference.
- The zone map check from 0.13.70 was never skipped on the phone (13-17 s
  on every zone start).
- 38-49 % of everything the system-call monitor stopped was ordinary socket
  traffic, most of it the display server sending each frame to the app
  (3,000-4,200 stops a second). CI has no such traffic, so it never showed.

**What changed**

- **New, on by default: "Do not monitor ordinary socket traffic"** (needs
  "Lighter system-call monitor"). The monitor needs socket calls only for one
  rare kind of socket; those now get numbers the monitor can tell apart, and
  all other sends and receives run without stopping.
- **Fixed:** the zone map check is skipped when the zone's folders are
  unchanged. The first start of each zone after this update still runs it in
  full once.
- **New in the report:** twice a minute in the world, what each of the game's
  busiest threads and the display server are doing or waiting on; and which
  lines of the app's own script make file calls.

Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.73 and the Thor test of 0.13.72".

CI: CI_EVIDENCE_PLACEHOLDER

## Steps (update in place: no uninstall; assets and the navigation map pack stay imported)

1. Install 0.13.73 over what you have. The app should still show
   **Navigation maps 1.0.0 · verified; reusable with this APK**.
2. Tap **Set up / update runtime** and wait for **Runtime ready**. Nothing
   needs importing again. Then set the options exactly like this.

   Checked:
   - Use performance graphics
   - Fast mode (PRoot seccomp, experimental)
   - Share server data between zones (faster zone preparation)
   - Skip server-only folders in the client's file scan (faster client start)
   - Reuse the client's saved file list while the data is unchanged (faster client start)
   - Game audio (sound and music through Android)
   - Game's own zone travel (doors, tunnels, monorail; any zone)
   - Start my saved zone while the game starts (Reopen)
   - Fast server (untick for the 0.13.36 server)
   - Raise the frame cap to 60 FPS in the world
   - Lighter system-call monitor (untick for the 0.13.36 one)
   - Do not monitor ordinary socket traffic (needs Lighter system-call monitor)

   Unchecked:
   - Start King's Row in the background (zoning)
   - Lower the waiting zone server's priority (zoning, experimental)
   - Keep a spare zone server loaded for travel (needs Fast server)
   - Shared server memory (experiment: zone servers share game data)
   - Draw on the game's own thread (frame rate experiment)

   **Do not monitor ordinary socket traffic** is new and should already be
   ticked; tell me if it was not.
3. **Launch A** (the defaults). **2 · Reopen saved character**, log in with
   `COHLOCAL / offline`, select Ralakar, **Enter Game**. With the FPS display
   on:
   - Face the direction where you saw the 20s and **hold still for two full
     minutes** (do not turn the camera). Note the frame rate and what is on
     screen (water, buildings, sky, other characters).
   - Turn to a direction where the frame rate was higher and hold still for
     two more minutes. Note the frame rate.
   - **Save character / log out**, **Finish and save report**, export.
4. **Launch B** (the same spot with the new option off). Untick **Do not
   monitor ordinary socket traffic**, repeat step 3 exactly, export, and tick
   it again.
5. Optional **Launch C** (the zone map check). With the defaults, Reopen,
   travel to Port Oakes and back, save, export. Launches A and B already
   recorded Mercy Island's map; this one shows Port Oakes'.
6. **Storage and cleanup**: 21.8 GB on the phone is old runtimes that can be
   removed (your character, game data and imports are protected). Clean up if
   you want the space, then **Scan storage** and export the storage report.

If the game does not start at all: untick **Do not monitor ordinary socket
traffic** and try once more; if it still fails, untick **Lighter system-call
monitor** as well; then **Fast server**. Either way, open the app, **Recover
interrupted reports** and export the top report so I can see which one it
was. If an error box appears in the game, tap **Ignore** (not Stop Program),
note what it says and keep going.

## Report

The exports of the launches you ran, and for launches A and B the frame rate
you saw in each direction and what was on screen. Fields I will read:

- `character_zoning.thread_waits.bursts`: per burst, for the client and the
  display server, each busy thread's CPU share, how often it was running,
  how often it was stopped in PRoot, and the calls and kernel functions it
  waited in.
- `proot_stop_counts`: the first line's `moved_netlink_fds`,
  `failed_netlink_moves` and `fd_stats`, and the rows for calls 206, 207 and
  212 (`sendto`, `recvfrom`, `recvmsg`), which should be near zero in launch
  A and as in 0.13.72 in launch B.
- `armport_proot_ioctl`: `socket_stops` (false in A, true in B) and
  `netlink_descriptor` (960 or more in A).
- `python_call_profile`: the supervisor's file calls by caller.
- `launch_receipts.zone_graph_71` and `zone_graph_72`: `status` (`reused`
  from the second start of a zone) and `reason`.
- The client's `ARMPORT_FRAME_RATE_V1` lines and `armport_client_timeline`.
