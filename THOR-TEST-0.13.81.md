# Thor test: COH Atlas Gameplay 0.13.81 (ARM64 client): two experimental loading options

0.13.81 is 0.13.80 with one change that is always on and two experimental
options, both **off by default**. CI can time the options and see that a
session passes; it cannot see the drawn world or characters moving. That is
what this test is for.

## What is new

- **A trip starts sooner (always on).** The app looked for the game's request
  to start a zone only every five seconds, so each trip waited up to five
  seconds before the spare zone server was given the zone (2.3-3.3 s in the
  one 0.13.79 trip where your export holds both ends). It now looks twice a
  second. The "request to map ready" times in earlier reports were multiples
  of five seconds (20.2, 20.3, 25.3 s) because the app also only *noticed*
  a ready zone every five seconds; that part cost the trip nothing, and the
  times in 0.13.81 reports are simply accurate now.
- **Keep prepared zone object files (experimental, ARM64 client; faster zone
  loading).** 0.13.80's measurement: of the 508 group files a zone names, the
  game reads 341 object library files from their text form at every zone
  load, 6.4-7.5 s of each trip in CI. The zone servers save a prepared form
  of each such file the first time and read that afterwards; the game never
  did. With the option it does, into a folder of its own beside its saved
  file list. **CI's result is modest:** the first load of a zone after
  ticking it is about 3 s longer (it writes 541 files); later loads are
  1-2 s shorter (object files 5.6-5.7 s for 6.4-7.5 s). Reading the text was
  only about a second of that time; the next build measures the rest.
- **Finish zone loading while the game loads the zone (experimental, needs
  Fast server).** A zone server reads its navigation data and starts its
  ragdoll physics after it is ready, while the game loads the zone, instead
  of before (4.7 s and 1.5 s of a trip's 18.8 s of server loading on the Thor
  in 0.13.79). For about a second after you appear, the zone has no
  navigation data yet. CI's navigation data is tiny (the late steps took
  0.25 s there), so the gain can only be measured on the Thor.

Details: `HANDOFF-X86.md`, sections "0.13.81 (96)" and the three after it.

CI (build 45160491073 at `ca58343c8`, every runtime run with the x87 option):
zone-change run 45175868959 with prepared zone object files: first load
parsed and wrote 541 files (object files 9.9 s, game ready 12.2 s after the
load began), three later loads read all 541 (5.6-5.7 s, ready 7.1-7.3 s;
0.13.80: 6.4-7.5 s and 8.2-9.5 s). Default options 45181648415: zone server
start 358.8 s for a new character, 23.4 s reopened (0.13.80: 358.3, 23.6).
Spare run 45187469113 with both options: files written in one launch and
read in the next; each zone server ran its late steps 0.5 s after it first
sent the world (navigation 14-23 ms, physics 237-253 ms warm); trip: zone
ready 9.3 s after the request, arrivals 13.2 s and 78.8 s (0.13.80: 11.7,
74.2), no resent input. One trip per run cannot show the faster pick-up.
APK run 45193693577: 93,606,154 bytes, sha256 `74648e10...8f8ba7`, signer
unchanged, its 51 guest files equal the commit.

## Steps (update in place: no uninstall; assets and the navigation map pack stay imported)

1. Install 0.13.81 over the installed version. The app should still show
   **Navigation maps 1.0.0 · verified; reusable with this APK**.
2. Tap **Set up / update runtime** and wait for **Runtime ready**.
3. Tap **Restore recommended options**; the line above the options should
   turn green. The options then are:

   Checked:
   - Use performance graphics
   - Fast mode (PRoot seccomp, experimental)
   - Share server data between zones (faster zone preparation)
   - Skip server-only folders in the client's file scan (faster client start)
   - Reuse the client's saved file list while the data is unchanged (faster client start)
   - Game audio (sound and music through Android)
   - Game's own zone travel (doors, tunnels, monorail; any zone)
   - Start my saved zone while the game starts (Reopen)
   - Keep a spare zone server loaded for travel (needs Fast server)
   - Fast server (untick for the 0.13.36 server)
   - Raise the frame cap to 60 FPS in the world
   - Lighter system-call monitor (untick for the 0.13.36 one)
   - Do not monitor ordinary socket traffic (needs Lighter system-call monitor)
   - Find files in any letter case in one step (needs Lighter system-call monitor)
   - Load zone server animations when first used (faster zone start)
   - Remember folder locations in the Wine server (faster file opening)
   - Reuse prepared collision meshes (faster zone start, needs Fast server)
   - Faster number emulation in zone servers (64-bit x87; faster zone start and travel)

   Unchecked:
   - Start King's Row in the background (zoning)
   - Lower the waiting zone server's priority (zoning, experimental)
   - Shared server memory (experiment: zone servers share game data)
   - Draw on the game's own thread (frame rate experiment)
   - Finish zone loading while the game loads the zone (experimental, needs Fast server)
   - Keep prepared zone object files (experimental, ARM64 client; faster zone loading)

4. **Launch A (only if you have not tested 0.13.80).** Change no options and
   follow launch A of `THOR-TEST-0.13.80.md`: stay four minutes, travel to a
   zone you know, stay four minutes, travel to a zone you have not visited
   with this app, save, export.
5. **Launch B: zone objects.** Tick **Keep prepared zone object files**
   (the line above the options turns amber and names it; that is expected).
   Reopen, Enter Game. Then:
   - The first loading screen is a few seconds longer than before (the
     files are written). In the zone, turn all the way around and walk a little: is anything missing or out of place
     (buildings, props, ground)?
   - Travel to a zone you know and note how long the loading screen stays.
     Look around again.
   - Travel back and note the loading time. This is the load that reads the
     saved files; expect a second or two less, not more. Look around again.
   - **Save character / log out**, **Finish and save report**, export.
6. **Launch C: both options.** Leave the first option ticked and also tick
   **Finish zone loading while the game loads the zone**. Reopen, Enter Game.
   Then:
   - As soon as you are in the zone: do pedestrians and cars appear and move,
     do enemies react and chase, does a pet follow you?
   - Travel to a zone you know, note the loading time, and check the same
     things there. Fight something.
   - Travel once more (any zone), note the loading time, check again.
   - **Save character / log out**, **Finish and save report**, export.
7. Tap **Restore recommended options** afterwards, unless you want to keep
   playing with the options on.

If the world looks wrong with an option on (missing objects, enemies or pets
that stand still or walk through walls): note which option and what you saw,
untick it, and carry on. Nothing is stored in the saved character by either
option.

If the game does not start at all: tap **Restore recommended options** and
try once more. If it still fails, untick **Keep a spare zone server loaded
for travel** and try again; then **Faster number emulation in zone
servers**; then **Fast server** once, and tell me which launch worked.
Either way, open the app, **Recover interrupted reports** and export the top
report. If an error box appears in the game, tap **Ignore** (not Stop
Program), note what it says and keep going.

If a trip fails (the game says the map could not be started, or the loading
screen returns you to where you were), travel again: the second try starts
the zone the ordinary way. Tell me which trip it was.

## Report

The exports of each launch, the loading times you noted, and what you saw
when looking around and watching characters. Fields I will read:

- The game's `ARMPORT_GROUP_LOAD_V1` lines: `bin=` (group files read from
  their saved form), `text=` (parsed from text), `wrote=` (saved this load),
  `full_ms=` and `total_ms=`.
- `client_group_bins` (whether the folder existed before each launch).
- `deferred_zone_load` and each zone server's `ARMPORT_DEFERRED_LOAD_V1`
  line: what triggered the late steps and how long they took.
- Trip times in `stock_travel`, as before; from 0.13.80:
  `spare_zone.graphs_checked_ahead` and `launch_receipts.zone_graph_*`.
