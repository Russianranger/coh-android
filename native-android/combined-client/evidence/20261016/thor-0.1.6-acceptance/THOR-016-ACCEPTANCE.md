# Combined 0.1.6 AYN Thor acceptance

The user declared this test successful on October 15, 2026, America/Chicago
(October 16 UTC). Record **physical acceptance of the bounded scene-receive
milestone and Return to launcher within the observations below**. This does not
accept complete Gates 25–27, encrypted AuthServer login or a live rendered world.

The current reports identify the exact qualified Combined 0.1.6 ARM64 APK:

- Package: `org.coh.nativecombined`; version `0.1.6-local-server-native`, code **7**.
- APK: **11,532,139 bytes**; SHA256
  `c41000d95573e5ed7baa73dabce0baa3d5c85d75bff6b88a3253385384f6345d`.
- AYN Thor, Android SDK **33**, primary ABI `arm64-v8a`, emulator flag false.
- Qualification/handoff reference:
  `bf653dd4ef5372c921b049a76f902a4a921e8c4d` on `native-android`.

Both native snapshots and the ZIP's current launcher report agree on the APK
identity. The two native snapshots belong to the same activity session, observed
first during scene reception and subsequently after Return. Session identifiers,
account/character names, private paths and raw payloads are omitted from this
public evidence. The originals were read without modification.

## Actual local-server protocol observations

The first JSON records **`SCENE_INCOMPLETE`**, one character list, one character
choice and one DB-to-Map handoff. The local development route is explicit;
`authserver_authenticated` and `live_world_rendered` are both false.

| Receipt | Observed value |
| --- | ---: |
| Last normalized command | 6 (`GROUPS`) |
| Full decoded payload | 42,889 bytes / 343,112 bits |
| Compressed input | 10,354 bytes |
| Configured owned decode budget | 4,194,304 bytes |
| Decode failure kind | 0 |
| Scene prefixes inspected | 1 |
| Entity prefixes inspected | 0 |
| Owned decoded bytes still retained | 0 |
| Owned decoded high water | 42,889 bytes |
| Map UDP received / sent datagrams | 24 / 10 |
| UDP I/O / malformed / truncated errors | 0 / 0 / 0 |
| Link malformed / queue-limit events | 0 / 0 |
| Local connection failures | 0 |

The real server supplied a body larger than the former 16,384-byte decode cap.
It was decoded, its supported scene prefix was inspected and its owned buffer
was released. Map diagnostics report two accepted messages and one unsupported
message, with zero malformed messages: the unimplemented `GROUPS` tail remains
explicitly unsupported. This is successful bounded receive and prefix
inspection, not acceptance of the complete scene message. The connection stays
`SCENE_INCOMPLETE` rather than claiming `READY` or a world spawn.

## Return, export and renderer observations

The later ZIP native report records:

- Document export requested, activity pause/surface destruction, foreground
  return and `export_complete`.
- `return_to_launcher_requested` at activity elapsed **17,294 ms** and
  `return_to_launcher_ready` at **17,309 ms**, a **15 ms** owner-suspension
  handoff. Render teardown completes at **17,359 ms**, **65 ms** after Return
  was requested. These timings are not server startup or world-load timings.
- Native protocol **`SUSPENDED`**, **2 sockets opened / 2 closed**, no connection
  failure, no retained owned decoded body, and the earlier successful numeric
  scene receipt preserved.
- **938 rendered frames**, **2 graphics contexts started / 2 completed**,
  `objects_released=true`, static GPU bytes **0** after teardown.
- Preview viewport **1920×410** on Adreno 740. Zero GL, EGL, cleanup, character,
  WALK and static transform mismatches, and zero non-tie depth mismatches.
  Transform components: character **81,588**, WALK **176,124**, static **82,992**.
- Original preview assets remain verified: **3 GEO loads**, **6 texture loads**,
  zero source-asset errors, **6 of 11** instances selected, **157,491** resident
  stream bytes within the **524,288**-byte preview budget. Those decode counts
  remain unchanged across the two context observations.

The subsequent launcher report shows its server still **ready** and its owned
process **alive**. This supports physical Return and server continuity for this
attempt. The reports do not identify launcher PID/task identity, a fresh client
reopen or a final server Stop, so they do not establish those additional cases.

External directional/controller/touch movement counters are zero, with three
focus-clear callbacks, zero held directions and zero run samples. This test
does not independently repeat physical controller movement or the held-input
Return case. Earlier physical renderer/input acceptance and hosted regression
qualification remain separately documented. The rendered character/scene in
these reports is the accepted offline preview; server-authoritative rendering
remains false.

## Current server startup and memory

The **current code 7** launcher reports ready at **392,192 ms** (**6 min
32.192 s**) and remains ready/alive at elapsed **421,288 ms**. Stage-boundary
deltas are **69,787 ms** for DB startup and **280,303 ms** for Atlas startup.
The differences between current resource-boundary timestamps are 69.779 s and
280.284 s; the small differences reflect independently sampled stage records.

There are **416 valid memory observations**, zero invalid samples, zero pressure
samples and no requested pressure stop. Minimum observed system headroom is
**8,270,680,064 bytes**, and Java heap headroom **209,006,312 bytes**. The 28
guest boundary samples report a self peak RSS of **305,184 KiB**. Cgroup totals,
limits and OOM-kill counters are unavailable, so this is not a whole-server or
whole-device peak-memory measurement.

The collected Android exit history includes eight older records: three marked
low-memory and five reason 10 records. Every recorded exit precedes the current
native activity session. They are historical observations, not evidence of a
kill during this successful code 7 attempt. Current sampled pressure observation
does not prove Android can never kill a future run.

## Historical data in this ZIP

The ZIP deliberately includes `previous-session-combined-server-latest-report.json`
and four previous-attempt records. These are not the current code 7 guest report:

| Historical entry | App code | Scope |
| --- | ---: | --- |
| 0 | 4 | Admission failed after 8 ms |
| 1 | 4 | Snapshot while starting/input admission; terminal outcome absent |
| 2 | 4 | `OWNED_DISPLAY_SOCKET_ALREADY_EXISTS`; cleanup completed, profile preserved |
| 3 | 5 | Prior 0.1.4 server stopped with exit 0; cleanup and profile preservation recorded |

The standalone historical guest report exactly matches entry 3's guest report
and has a different server-session identity from the current launcher. Its
**438.672194 s cold mirror**, **67.560703 s beacon phase**, **800,298 ms ready
time**, graceful PostgreSQL/Wine cleanup and presentation-socket removal belong
to **0.1.4**. They must not be relabelled as 0.1.6 data.

The faster code 7 ready time is observed. Its current detailed guest cache
receipt is absent, so warm/cold cache classification and the cause of the
startup difference remain unestablished. This milestone did not change the
server startup/cache implementation.

## Provenance and review

The companion [sanitized numeric summary](thor-016-sanitized.json) contains
allowlisted counters, lifecycle event names, safe version identifiers, source
hashes and ZIP member checksums. It excludes arbitrary report strings,
identifiers, imported paths, account names, credentials and packet bytes.

| Original upload | Bytes | SHA256 |
| --- | ---: | --- |
| `COH-NativeCombined-20261015-200934.json` | 38,391 | `fafbc93c30c0677c5f9dc18c52e5239ec590c22f082a1432725e4151cf213c43` |
| `COH-NativeCombined-1792112986044.zip` | 27,108 | `f4b0d29988272e83b2582094649660841a9e5217152b26dd461106e832016f3f` |

| ZIP member | Bytes | CRC32 |
| --- | ---: | --- |
| `combined-report.json` | 39,093 | `314710c0` |
| `native-client-report.json` | 142,145 | `ec109340` |
| `previous-session-combined-server-latest-report.json` | 30,332 | `32dd1333` |
| `combined-server-previous-attempts.json` | 118,349 | `2c548b3c` |

All four member CRCs were verified; member SHA256 values are in the sanitized
summary. Exact current app identity, same native session, distinct historical
guest session and historical-report equality were checked. Both original upload
hashes were rechecked after evidence generation and were unchanged.

The next implementation milestone is bounded complete source `GROUPS` grammar
decoding and its integration contract. Imported-library resolution,
server-authoritative spawn/entities and encrypted authentication require their
own implementation and qualification; this acceptance does not promote them.
