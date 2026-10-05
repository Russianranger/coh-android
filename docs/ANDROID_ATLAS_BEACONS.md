# Native Atlas beacon graph

The October 5 physical 0.13.13 test retained level across reopen, completed
training without a crash, and still displayed the native unbeaconized warning.
This pass produces a genuine graph for the current Atlas world. Zoning remains
a later pass. The warning is not patched or hidden.

## Native producer and qualification

The prior `atlas-beacon-input-preflight.json` remains accurate about the input
inventories: they contain no generated `.bcn`. The authored Atlas beacon layer
is placement source rather than a generated combat graph. The legacy
`beaconProcessCombatBeacons` body and generator wrapper are compiled out. This
pass leaves those functions unchanged and uses the active native Beacon master,
server, sentry and worker roles in a separately built host-only MapServer.

`tools/prepare_atlas_beacon_generator_source.py` stages the accepted MapServer
progress base plus a finite containment patch. The host executable rejects
ordinary gameplay and production-mode startup. It cannot install itself, write
an autorun registration, spawn workers or read personal/global map lists. Four
owned processes use one worker, loopback-bound/admitted native ports and exactly
`maps/city_zones/city_01_01/city_01_01.txt`. The server completes one pass. Native
generation, collision connection, graph writer, graph reader and pathfinder
algorithm files retain their original hashes. This binary never enters an APK.

`tools/android/interactive/generate_atlas_beacons.py` reconstructs the same
private native world using the exact 0.13.13 APK, reviewed base asset ZIP and
unmodified Java importer. It applies the retained world and visual supplements
with the shipped missing-only precedence. The generator pins the physical GEOs,
object-library group text, Atlas placement/layer text and trick text before and
after generation. UI-only texture additions do not change this graph identity.

After native generation and connection, the server freshly loads the ordinary
Atlas map without the generator's missing-definition cleanup. It compares the
v9 date-sidecar full-world CRC with that fresh world, fully rereads the v8 graph,
requires populated connected combat/grid data and exercises 32 real native
pathfinder routes. Failure prevents a qualified package. Four role logs and a
source/input/build receipt accompany the output. A finite 90-minute deadline
and log bounds apply; all owned roles are stopped before publication.

The standalone `android-atlas-beacon-generation.yml` workflow builds under a
short Windows path to stay below the historical utility diagnostic thread-name
buffer boundary. It emits `atlas-beacons.zip`, `atlas-beacon-manifest.json`,
`atlas-beacon-generation-report.json` and bounded evidence. A completed graph
may be reused in a later documentation/UI commit only while every generation
implementation pin, native build input and world identity still matches. The
receipt continues to name the actual generation commit.

## Private installation and startup

`android/guest/atlas_beacon_package.py` accepts only the frozen qualified graph
and v9 sidecar. Its published SHA-256 constants remain pending until a real
hosted generation succeeds. The installer requires the retained gameplay
MapServer and the already qualified readonly private world. It hashes the
physical collision/group/Atlas/trick inputs on the first successful install.
Existing different graphs and linked target paths are preserved and refused.
Only the two server-only files and an owned proof receipt are written.

The ordinary Atlas preparation path installs the package for saved and fresh
characters. The unmodified gameplay MapServer discovers and loads the graph
through `beaconReload`; no client gameplay or persistence semantics change.
The ordinary loader reads the v8 graph directly and does not compare the date
sidecar or source-file timestamps. The optional v9 freshness check accepts a
matching full-world CRC; its timestamp-only fallback remains compiled out.
Android import/copy timestamps and cache-directory renames therefore do not
cause graph regeneration. The installer still checks actual source bytes and
fingerprint freshness independently.
The server data cache carries the graph and proof across clean shutdown/reopen.
Warm reuse still performs a bounded readonly fingerprint walk, but skips input
payload hashing and ZIP decoding. Both first preparation and warm reuse expose
`atlas_beacon_graph.preparation_elapsed_seconds`, the input count/bytes hashed
and whether the archive was decoded. A native graph proof does not certify
physical NPC behavior on the AYN Thor.

## Tests and physical check

Source tests prove containment scope, unchanged active algorithms and clean
patch application. Producer tests reject missing/duplicate graph receipts,
empty connections, absent native routes and mismatched sidecar CRC/version.
Installer tests cover first install, warm reuse without archive decoding,
changed geometry, invalidated input fingerprints, preservation of different
existing graphs, linked targets, writable inputs and incomplete native proofs.
Synthetic unit fixtures are explicitly not native generation evidence.

After publication, install the next APK over the current app and reopen the
saved THORHERO. Record setup/preparation, local Atlas, client, login and world
entry separately. Observe whether the native unbeaconized warning disappears,
then test normal NPC pursuit/pathing around nearby obstacles while retaining
combat, movement and targeting. Save normally, finish/export, reopen and verify
level/XP/powers plus graph reuse. Inspect the exported native log and
`atlas_beacon_graph` receipt before accepting beaconization or a startup claim.
