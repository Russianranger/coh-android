# Thor 0.1.4: server boot and bounded Map handshake; receive decode limit

The physical Thor reports establish that the **exact qualified Combined 0.1.4 ARM64 APK** booted its local server, supplied an existing character to the native picker, accepted the native Map CONNECT and shortcut exchange, and stopped cleanly after testing. The native connection then failed while obtaining the next compressed message, before a scene message reached its parser. The offline preview remained healthy throughout the character-picker resize and later protocol failure. No server-authoritative world or encrypted AuthServer authentication is established.

[thor-014-connection.json](thor-014-connection.json) contains allowlisted evidence, input/image hashes, source interpretation, and a validation/privacy receipt. Private reports, images, character labels, credentials, cookies, identifiers, and packet bodies are not committed.

## Binary identity and report ordering

The combined report, standalone native report, and ZIP's later native report all identify version `0.1.4-local-server-native`, code **5**, with **11,527,815 bytes** and SHA256 **`18b06672a11af3a50bd2ece77ce41bc2fecec7f8ebe6037408245119ca21ad2c`**. This matches the recorded delivery built from `294041ddff3b5f80ae4dbf25073b01e037ecc7ee` in workflow `38811852104`. The device identifies as physical AYN Thor, SDK 33 / ARM64.

The standalone report at 17:23:17.734 (UTC−05:00) preserves protocol phase `FAILED`. The later ZIP native report at 17:23:48.657 retains the terminal failure checkpoint but has phase `SUSPENDED` after export/pause. The final combined report is stopped after a successful manual server stop; its ready-stage history and current guest report prove the earlier boot. This is new 0.1.4 execution, unlike the stale 0.1.2 native report retained in the preceding 0.1.3 export.

The four older archived attempts retain 0.1.2 ready evidence and 0.1.3 admission/interruption/display failures. They do not describe the current attempt.

## Server startup, timing, and cleanup

The current guest progresses through fresh session-bound presentation, Wine, local DB, and Atlas startup. Server readiness is reached at **800,298 ms (13 min 20.298 s)**. The ready receipt reports one saved character under the local development policy; native character creation and encrypted authentication remain false.

| Milestone | App stage elapsed ms |
| --- | ---: |
| PostgreSQL | 14,895 |
| Fresh owned presentation endpoint | 15,929 |
| Wine initialization | 16,204 |
| Local login ODBC | 28,997 |
| DB startup | 43,751 |
| Atlas startup | 594,654 |
| Ready for manual native client | 800,298 |
| Final run duration | 920,216 |

The DB stage lasts 550.781 seconds; Atlas lasts 205.637 seconds. The preparation receipt records **438.672194 seconds for `cold_server_data_mirror`** and **67.560703 seconds for `atlas_beacon_graph`**. These measured preparation costs explain substantial time spent before readiness. They do not by themselves establish the next run's cache behavior. Required geometry is reused, with 406 files checked and no geometry worker needed.

The app records a manual stop request followed by guest process exit **4,304 ms** later. Guest exit code is zero, failure codes are empty, and the final guest report states profile preserved and cleanup complete. PostgreSQL graceful cleanup, Wine-prefix shutdown, owned-process reaping, and presentation-socket removal are all true. The presentation policy reports a fresh session-bound endpoint, no legacy fixed-endpoint reuse, and original display bootstrap reuse. This attempt has no recurrence of `OWNED_DISPLAY_SOCKET_ALREADY_EXISTS`.

## Memory/resource observations

The Android observer records **897 valid samples**, zero invalid/pressure samples, and no safety-stop request. Minimum observed system headroom is **6,732,345,344 bytes**; minimum Java heap headroom is **177,847,968 bytes**.

The guest contributes 28 stage-boundary resource samples. Its maximum reported self peak RSS is 317,660 KiB; the final sampled guest RSS is 148,464 KiB. Child peak RSS is a separate reaped-child resource counter, not a sum of concurrently running processes. All sampled cgroup current/max/OOM-counter fields are unavailable. These observations do not establish the full process tree's concurrent memory peak or qualify prevention of Android kills.

The newest retained OS low-memory exit is **21:26:19.091 UTC**, before this run begins around 22:08 UTC. It is historical; the new run ends through the recorded manual stop and zero exit code. No new Android low-memory exit during this attempt is evidenced.

## Real native DB and bounded Map progress

The terminal native handle records one attempt, one real DB character list, one existing-character choice, and one DB-to-Map handoff. Both opened sockets are closed. The Activity timeline contains three connect requests and three character-choice requests; handle counters restart with each new connection and must not be read as lifetime totals.

The final pre-export checkpoint is:

| Diagnostic | Value / interpretation |
| --- | --- |
| Local phase | `FAILED` |
| Status | 4 / `COH_LIMIT` |
| Preserved terminal Map phase | 4 / `COH_MAP_WAIT_SCENE` |
| Preserved terminal DB phase | 9 / `COH_DB_CLOSED` |
| Map diagnostic stage | 2 / `COH_MAP_STAGE_MESSAGE_NEXT` |
| Accepted application messages | 2 |
| Previous accepted command | 4 / `COH_REP_SHORTCUTS` |
| Previous payload length | 113,102 bits |
| Accepted scene/entity prefixes | 0 / 0 |
| Map UDP datagrams sent/received | 11 / 24 |
| Map UDP I/O errors, truncation, malformed | 0 / 0 / 0 |
| Inner link malformed / queue-limit counters | 1 / 0 |

The source state machine reaches `WAIT_SCENE` with two accepted messages only after parsing an accepted `CONNECT_MSG`, parsing the complete shortcut catalog, and successfully queuing `REQSCENE`. This supports **real local Map application CONNECT and shortcut acceptance**, a narrower milestone than a complete Map session or Gate 27 world entry. It does not prove encrypted AuthServer authentication.

The failure site is now distinguishable from that successful shortcut parse. `MESSAGE_NEXT` means `coh_net_udp_next` returned an error before the next message entered the application inspector. In this source, `COH_LIMIT` on that path propagates from compressed-message decoding in `coh_net_next`; that failure also increments the inner link's `malformed` counter. The counter label does not independently prove the server sent malformed wire data.

The exported 113,102-bit length and command 4 remain the **previous accepted shortcut message**, not the failed message. The failed compressed header, command, decoded size, and exact limit/allocation subcondition are unrecorded. A 16 KiB decoded-message bound exists in the audited source, but this evidence cannot establish the rejected message's advertised size. No scene prefix or complete scene/world state was accepted.

## Preview, picker, and physical input

The private images show `CHARACTERS_READY` with an existing-character button, then `FAILED` while the offline scene continues from 1,928 to 4,826 frames. Character text is excluded from the public evidence. The native timeline confirms picker-size surfaces of **1920 × 410**, with **1920 × 469** after selection; both stay within the unchanged source aspect bounds.

The standalone report reaches 4,963 frames with nine contexts started and no native failure. The later report reaches **6,039 frames**, ten contexts started/completed, objects released, and zero GL/EGL, transform, or depth-order errors. It records three GEO and six texture loads, zero source-asset errors, decoded cache reuse, and no cache evictions. Recreate, reset, report export, pause, and resume events remain visible.

The later external-input counters include 298 controller events, left/right directional masks, and touch input; all in-app synthetic counts are zero. These are observations from this physical run, not a replacement acceptance procedure for previously accepted movement or rendering gates. The scene is explicitly the offline preview (`preview_is_server_world: false`).

## Validation and acceptance scope

Evidence checks compare every numeric/status subset with the private source reports, verify all input/member/image hashes, check timing/arithmetic and exact APK identity, and scan for private identifiers/names/paths. Five compiled enum controls verify the source's status, phase, and command interpretation. Source hashes pin the reviewed Map, UDP, receive, and compression code. `git diff --check` passes.

This record supports physical 0.1.4 server boot/orderly stop, real local DB selection, bounded local Map CONNECT/shortcut acceptance, and picker resizing without the previous source-camera failure. Full Gates 25–27, encrypted login, scene/entity replication, and native server-authoritative world rendering remain pending. Gates 1–24 and the accepted native renderer are unchanged. This evidence worker makes no runtime edits or new APK qualification claim.
