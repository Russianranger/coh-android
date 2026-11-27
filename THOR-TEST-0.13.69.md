# Thor test: COH Atlas Gameplay 0.13.69 (ARM64 client): the early zone start, and graphics calls that skip the system-call monitor

Two things are new against your 0.13.67 launch (export 20261111-035325).

**The early zone start now runs.** 0.13.68 was meant to start your
character's zone while the game itself starts. It did not: the call sat in a
launch sequence the ARM64 client does not use. 0.13.69 puts it in the right
place, and CI fails if the option is on and no early start was decided. If
you installed 0.13.68, nothing is lost; it behaved as 0.13.67. The one-time
work of your 0.13.67 launch (install checks, file list, texture list, zone
data) is recorded, so this launch should skip it.

**An experiment aimed at the frame rate and at loading times.**

Your 0.13.67 launch showed where the time goes: the Linux layer (PRoot) has
one helper thread, and every monitored system call of every process waits for
it. It used 647 s of CPU before the world appeared and half a core while you
played. On Android that helper stops every device-control call (`ioctl`)
twice, and the renderer talks to the GPU through exactly those calls.

0.13.69 carries a second build of the helper that stops only the seven
`ioctl` commands it needs to see. On my test machine a stopped call costs
about 50 microseconds and a passed one 0.16. It is behind an option, off by
default, because this build has never run on a phone: the default launch
still uses the helper every release since 0.13.36 used.

Every launch now also measures those calls itself (three short timings at
start), so launch A tells me what one stop costs on the Thor.

Evidence: [HANDOFF-X86.md](HANDOFF-X86.md), "0.13.69" and "0.13.69, PRoot part".

CI at 22d90d987: build 43077376317 passed; stock-travel runtime 43091944698
(`early_zone=true`, `proot_ioctl_filter=true`, sampler reading as root; one
trip); trusted runtime 43099656030 created and reopened a character (its
interactive job took 1856 s); APK 43104941674 published 0.13.69 (sha256
`37b0cf1e27ed4ab51b3e690b3991d9d2fc4cc78b954049b496002aea90a9e2bb`). Runtime
43091944698: early start `started`, the game's request 115.4 s later, zone
ready 60.6 s after it; ioctl probe `listed_commands_only` in both sessions
(FIONREAD 0.6, TCGETS2 31 microseconds per call) and no ioctl among 4,325
sampled stops; the trusted runtime, without the switch, reads `no_ioctl_stops`
(CI's Linux PRoot does not trace ioctl; Android's does). Atlas Park's
MapServer, spawn to ready: 176.0 s stock, 99.0 s with trusted bins.

## Steps (update in place: no uninstall; assets and the navigation map pack stay imported)

1. Install 0.13.69 over 0.13.67 or 0.13.68. The app should still show
   **Navigation maps 1.0.0 · verified; reusable with this APK**.
2. Leave the options at their defaults.
3. **Launch A** (defaults). **2 · Reopen saved character**, log in with
   `COHLOCAL / offline`, select Ralakar, **Enter Game**. Note roughly how long
   Enter Game takes to put you in Mercy Island (the zone now starts while the
   game itself starts).
   - Stand where you arrive for about a minute with the FPS display on, then
     play as you like.
   - **Save character / log out**, wait for **Saved character verified**, then
     **Finish and save report**. Export the report.
4. **Launch B** (the new experiment). Close the app from recents, open it,
   tick **Graphics calls skip the system-call monitor (frame rate
   experiment)** and repeat step 3, standing in the same spot for a minute.
   Export the report. If the game starts and plays normally, leave it ticked
   for launch C; if anything is wrong (no picture, a crash, the game not
   starting), export the report and untick it.
5. **Launch C** (fast server). Tick **Fast server start (test server with
   trusted bins)** and repeat step 3. Export the report, then untick it. This
   is the server CI runs; one phone time for it decides whether it becomes
   the default.
6. Optional **Launch D**: tick **Draw on the game's own thread (frame rate
   experiment)**, repeat step 3, stand in the same spot for a minute, export,
   untick.
7. Optional **Launch E** (the spare zone server): tick both **Fast server
   start** and **Keep a spare zone server loaded for travel**, repeat step 3,
   stay in Mercy Island about four minutes, travel to another zone and note
   how long the loading screen lasts; stay four minutes, travel again. Save,
   export, untick both.
8. **Storage and cleanup**, **Scan storage**, export the storage report.

If Reopen stops before the game opens, or the app closes by itself: open it,
**Recover interrupted reports**, export the top report and a storage report,
untick the experiment you had ticked and try once more. If an error box
appears in the game, tap **Ignore** (not Stop Program), note what it says and
keep going.

## Report

The exports of the launches you ran, the storage report, and for each launch
roughly how long Enter Game took and the frame rate you saw standing still.
Fields I will read:

- `armport_proot_ioctl`: `reading` (`every_ioctl_stops` in launch A,
  `listed_commands_only` in launch B) and `microseconds_per_call`.
- `proot_ioctl_filter_used`, the client's `ARMPORT_FRAME_RATE_V1` lines and
  the helper's CPU share (launch B against launch A).
- `character_zoning.initial_zone.early_start`: `started`,
  `ready_before_the_game_asked` or `requested_after_seconds`, `reason`.
- `launch_receipts`, `ARMPORT_FOLDER_CACHE_V1` (`index result=hit`),
  `texture_header_index.reused`, `server_data_cache.reused`.
- `wine_priorities.loading_samples` and the context switches in
  `busiest_threads`; `armport_gl_threads` (launch D);
  `character_zoning.spare_zone` (launch E); `memory_trace`.
