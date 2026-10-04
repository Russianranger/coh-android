# Opt-in MapServer main-thread progress observer

This separate overlay observes late MapServer startup and its main tick without
changing protocol readiness, callback behavior, heartbeat limits or accepted
game donors. Apply `patches/mapserver-progress/0001-mapserver-progress.patch`
after the creation variant of the game-loopback overlay, then copy the two
`overlay/MapServer/src/svr/wine_map_progress` files into that fresh source tree.
The upstream snapshot and the accepted game-loopback patch stay unchanged.

`COH_WINE_MAP_PROGRESS` opts in with an absolute Windows drive path beneath the
launcher's private runtime directory. Unset means disabled. Initialization uses
`CREATE_NEW`, refuses relative/UNC/device paths, and never overwrites evidence.
An explicitly requested initialization failure exits MapServer with code 2.
Initialization happens after `parseArgs1`, respecting the source's file-mode
setup order. Only enabled initialization registers an exit cleanup handler.

The producer creates a 4096-byte mapping with a 128-byte little-endian record:

| Offset | Field |
| --- | --- |
| 0 | Eight-byte magic `COHMAP1\0` |
| 8, 12 | Format 1, record size 128 |
| 16, 20 | Windows PID, main thread ID |
| 24, 28 | Sequence, explicit stage ID |
| 32, 36 | Ticks started, ticks completed |
| 40, 44 | Flags, stage count 37 |
| 48–127 | Reserved zero bytes |

Only the main thread publishes. Positive even sequence values bracket complete
records; readers must independently check stable bytes, identity, monotonic
counters, reserved bytes and zero flags. A saturated sequence/counter sets flag
1 and is rejected. Stage 24 starts a tick; stage 34 completes it. The explicit
stage enum in the header is the authoritative versioned contract. A marker
identifies an operation about to run unless its name explicitly says completed.

Markers perform ordinary aligned stores and compiler barriers. They perform no
allocation, clock reads, I/O, synchronization or OS calls. The observer starts no
thread, retains its last publication on exit, and cannot establish game success.
`FOLDER_CALLBACKS` covers the existing `FolderCacheDoCallbacks` call as a whole;
it does not distinguish directory updates from individual callbacks.

Run the actual producer contracts from an initialized x86 MSVC environment:

```
python tools/android/game/test_mapserver_progress.py --require-windows
```

The Windows tests compile the production source, inspect the compiled marker
instructions, and independently read its mapping while the process is alive.
They cover every stage, distinct tick counts, no added thread, disabled mode,
path and existing-file refusal, reinitialization refusal, and retained evidence
after closing. These native checks are skipped on non-Windows hosts; such skips
do not qualify the producer.
