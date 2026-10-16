# Bounded entity-list staging qualification

This receipt qualifies the optional native entity-list substructure parser on
the host. It does not qualify a whole ALLENTS/UPDATE, a real player create, an
authoritative actor, server interoperability, the accepted Combined APK, or
gates 25–27.

`host.json` binds the native/parser/checker source hashes, 14 pinned original
source files, 24 unchanged original component functions, and retained
`fixtures.h`. The fixture SHA-256 is
`ce20d805c9d410e84432afc9dee1c1905b2ae57734337ed0262c36087e4122b3`.
There are 98 fixtures across both original bit-packed and byte-aligned modes.
Lists use synthetic source-function compositions; neither the complete
original `sendEntity` nor `entSendUpdate` runs in this oracle. Synthetic self
records suppress unsupported character/appearance branches and cannot stand
in for a real player full update.

| Host mode | Checks | Every-bit truncations | List truncations | Random bodies |
|---|---:|---:|---:|---:|
| Release | 363,305 | 23,627 | 9,084 | 20,000 |
| ASan | 363,305 | 23,627 | 9,084 | 20,000 |
| UBSan | 363,305 | 23,627 | 9,084 | 20,000 |

All three native JSON results match. The 50 focused list cases include the
canonical maximum-slot sentinel, a sentinel whose synthetic index equals an
earlier record, descending indices, late unsupported appearance, missing
capacity, duplicate indices, unknown updates, stale update/creation ordering,
deletion tombstones, seeded global ownership conflicts and unchanged self slots.
Every failure preserves the public reader, staging table and receipt; caller
workspace contents are explicitly scratch and may change. Random bodies also
exercise the new list entry point with rollback checks.

Source review uses the unchanged pinned files:

- `MapServer/src/entity/entsend.c`: `sendEntity` writes the signed index
  difference to a U32 packed writer. `entSendUpdate` first scans the bitset,
  then can append additional player/debug/self records with lower indices.
  Its end marker is packed delta 0, create 1, end 1. Appended actual records are
  guarded by the sent bitset, supporting rejection of repeated record indices.
- `Game/src/entity/entrecv.c`: `entReceiveUpdate` starts the index at -1;
  `checkEntCreate` tests create/end before accessing the entity index. Thus the
  sentinel after slot 10239 has synthetic index 10240. The native parser uses
  defined uint32 arithmetic for the intended original modular delta behavior.
- `entSendCreate` identifies self by equality with the receiving player.
  Native table-wide selected-DBID/self uniqueness is an explicit admission
  guard; the old consumer itself selected the last self object.

Reproduce from the repository root:

```sh
python native-android/engine/entities/check.py --source-root . --sanitize \
  --fixtures-output /tmp/entities-list-fixtures.h \
  --output /tmp/entities-list-host.json
```

The checker retains existing optional `--ndk` / `--android-output` behavior;
Android receipts still bind fixture, source and binary hashes and say
`executed:false`. No Android cross-build or execution was performed in this
host receipt. CMake verification was attempted but unavailable (`cmake: command
not found`); the checker compiled all new C with strict C99 warnings instead.
LeakSanitizer is disabled for the sandbox's unavailable process walk; ASan
memory-access and UBSan remain enabled.

The full-update tail barrier still returns `COH_UNSUPPORTED`. No parser path
produces READY, RECEIVED_CHARACTER, ACK_FULL_UPDATE, socket messages, or actors.
