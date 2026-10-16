# Combined 0.1.7 AYN Thor acceptance

The user reported that the October 16, 2026 physical AYN Thor test worked.
Accept the **bounded complete normal-world GROUPS structure inspection,
accepted offline preview and Return to launcher**, with the subsequent current
server Stop and cleanup recorded below. This does not complete Gates 25–27,
encrypted AuthServer authentication or server-authoritative world entry.

The reports identify `org.coh.nativecombined`, version
`0.1.7-local-server-native`, code **8**, on AYN Thor / Android SDK **33** /
`arm64-v8a`, emulator flag false. All three current app identities match the
qualified **11,536,171-byte** APK, SHA256
`58c45d44501373309788d70e2483786e412d9b0593e86ba1bae94140a8147475`.
The published qualification baseline is
`eb7af800d5dd4e942f56c702200d0da929c941b8` on `native-android`.
The identity also matches the retained
[hosted ARM64 package receipt](../full-scene-0.1.7/hosted/package-arm64.json).

The original attachments were read without modification. The companion
[numeric acceptance](thor-017-sanitized.json) and existing bounded analyzer's
[startup analysis](startup-analysis.json) publish allowlisted observations and
input checksums. Session identifiers, account/character names, imported paths,
arbitrary report strings, commands and packet bodies are omitted.

## Real local DB/Map and GROUPS observations

The standalone JSON records **`SCENE_INCOMPLETE`**, one connection attempt,
one character list, one character choice and one DB-to-Map handoff. Development
authentication is explicit. AuthServer authentication and live-world rendering
remain false.

| Receipt | Observed value |
| --- | ---: |
| Normalized command | 6 (`GROUPS`) |
| Compressed / decoded body | 10,354 / 42,889 bytes |
| Payload / consumed structure | 343,112 / 343,112 bits |
| Completed scene structures | 1 |
| Present files / file slots | 508 / 508 |
| Wire definitions / children | 0 / 0 |
| Roots / raw root matrices | 33 / 33 |
| Strings / string bytes | 541 / 35,957 |
| Footer file count / active roots | 508 / 33 |
| Scene failure stage / offset / status | 0 / 0 / 0 |
| Entity prefixes | 0 |
| Owned decoded bytes retained / high water | 0 / 42,889 |
| UDP datagrams received / sent | 24 / 10 |
| UDP I/O / malformed / truncated errors | 0 / 0 / 0 |
| Protocol failures / policy rejections | 0 / 0 |

This verifies traversal through the normal GROUPS footer, extending the earlier
prefix-only physical acceptance. Zero wire definitions does not describe an
empty map: saved-library definitions still require resolution against imported
assets. The 33 root identities/matrices and footer CRC numbers were inspected,
not materialized into a verified scene graph or recomputed against library data.

The map reports two accepted messages and one rejected/unsupported result, with
zero malformed messages. This is the explicit promotion boundary in
`engine/mapclient/coh_mapclient.c`: after successful complete structural
inspection and incrementing `scene_structures`, the client returns
`COH_UNSUPPORTED` because imported graph, checksums and authoritative character
acceptance are not established. It is not a failed structural parse. Keeping
`SCENE_INCOMPLETE` is the correct result.

## Export, Return and renderer cleanup

The standalone JSON is an active export snapshot. The ZIP native report belongs
to the same activity session and follows export, foreground return, explicit
Return and final render teardown. Its scene inspection is identical.

| Observation | Standalone export | ZIP after Return |
| --- | ---: | ---: |
| Rendered frames | 3,520 | 3,748 |
| Contexts started / completed | 3 / 2 | 4 / 4 |
| Objects released | false | true |
| Running / resumed / render busy | true / true / true | false / false / false |
| Protocol sockets opened / closed | 2 / 1 | 2 / 2 |
| Protocol identity bound | 1 | 0 |
| Protocol phase | `SCENE_INCOMPLETE` | `SUSPENDED` |
| Static GPU bytes | 557,056 | 0 |

`return_to_launcher_requested` occurs at activity elapsed **66,243 ms**,
`return_to_launcher_ready` at **66,274 ms**, and final `render_returned` at
**66,335 ms**: **31 ms** to owner suspension and **92 ms** to completed render
teardown. These are lifecycle handoff timings, not server/world-load timings.
Native `total_ms` resets across render epochs; it is not cumulative activity
duration and must not be used to infer total preview duration or FPS.

The offline preview is **1920×410** on Adreno 740. GL/EGL status and cleanup
errors are zero. One separately classified expected surface-cancellation error
is retained with expected EGL code **12301**; it did not become a render or
cleanup failure. Character, walkable and static transform mismatch counts are
zero. Static maximum numeric error is **0.00000762939453**. Two raw depth changes
are both qualified equal-depth ties; non-tie mismatches are zero. The depth
witness remains the four startup images, not continuous whole-scene validation.

Assets remain verified: **3 GEO** and **6 texture** loads, zero source-asset
errors, **6 of 11** preview instances selected, and **157,491** resident stream
bytes within a **524,288**-byte budget. The preview remains separate from the
server world; full Atlas and GPU palette skinning are false.

The user accepted the physical test. Framework counters additionally record
**856** external controller/motion callbacks, all four left-axis directions
(mask **15**), touch movement in all four directions, and zero in-app synthetic
events. There are **215** run samples and **64** animation transitions. This is
consistent with the physical movement report. Right-axis and button counters
are zero. Ground contacts were exercised, but wall hits, blocked ticks and
sliding ticks are zero, so this run does not newly qualify wall collision. Held
directions are zero at Return; a held-input Return case, launcher PID/task
identity and fresh client reopen are not established.

## Current server startup and Stop

The ZIP's current launcher, guest report and readiness receipt have matching
server identities. The launcher records ready at **387,340 ms** (**6 min
27.340 s**) and a later stopped state at elapsed **475,992 ms**, guest exit
**0**, no owned process alive and no failure code. The matching guest records
graceful PostgreSQL stop, Wine-prefix stop, owned-process reaping, presentation
socket removal, complete cleanup and preserved profile. This accepts the
recorded current server Stop. The guest's `native_client_started=false` is
consistent with manual Android client launch; it does not negate the native
activity observations.

Current DB and Atlas stage-boundary deltas are **70,678 ms** and **271,736 ms**.
The bounded analyzer finds a matching **warm schema restore** receipt
(**0.183016 s**) and no cold-mirror phase. The beacon phase is **24.258214 s**.
Unlike the previous 0.1.6 attachment, this ZIP contains matching detailed guest
data for the current attempt.

The four historical attempts are kept separate:

| Historical entry | App code | Matching receipt / outcome |
| --- | ---: | --- |
| 0 | 4 | Starting snapshot; no matching detailed guest receipt |
| 1 | 4 | Failed attempt; cache classification unknown |
| 2 | 5 | Stopped; cold mirror observed; ready 800,298 ms |
| 3 | 7 | Stopped; warm schema restore observed; ready 392,192 ms |

Entry 3 now supplies a historical matching 0.1.6 warm receipt that was absent
from the earlier 0.1.6 attachment. The earlier acceptance correctly left that
classification unknown. Neither the cold code 5 measurements nor historical
failures are current code 8 results. The startup differences do not establish a
code-change speedup or a cold-start result.

There are **466** current valid memory observations, zero invalid/pressure
samples and no requested pressure stop. Minimum observed system headroom is
**7,997,022,208 bytes**; Java heap headroom is **213,160,432 bytes**. The 28 guest
boundary samples report self/reaped-child high water **305,192 KiB**. Cgroup
totals and OOM-kill counters are unavailable; this is not a concurrent whole
server peak-memory measurement. Eight Android exit-history records, including
three reason 3 records, predate the current native activity. They do not
establish a failure or allocation cause for this accepted attempt, nor does the
pressure observation guarantee prevention of future Android kills.

## Provenance

| Original upload | Bytes | SHA256 |
| --- | ---: | --- |
| `COH-NativeCombined-20261016-100312.json` | 164,862 | `6db0ed0232a564bd2a16d2bdb34e1b4df38b2c3068ad525b1fbefc104108475a` |
| `COH-NativeCombined-1792163012982.zip` | 37,864 | `e802501bce9738d538d8438cdcdbdb304810a9d7854d45a0dbb47a7188542b73` |

| ZIP member | Bytes | CRC32 |
| --- | ---: | --- |
| `combined-report.json` | 39,251 | `7a746c71` |
| `native-client-report.json` | 269,418 | `e57a80ad` |
| `combined-server-latest-report.json` | 30,283 | `d00a4e17` |
| `combined-server-previous-attempts.json` | 197,417 | `d0545fe6` |

All four member CRCs were verified; member SHA256 values are in the numeric
summary. Both original upload hashes were rechecked after evidence generation
and were unchanged. No APK, runtime, asset import or prior evidence was changed.
Exact report counters, final cleanup and lifecycle timings were checked against
the originals; all **26** existing bounded startup-analyzer tests passed.

The next implementation milestone is bounded imported-library resolution and
owned scene-graph materialization with original transforms and verified footer
checksums. Authoritative initial entity identity/position and encrypted
AuthServer interoperability need separate integration and qualification before
promoting a server-world renderer snapshot.
