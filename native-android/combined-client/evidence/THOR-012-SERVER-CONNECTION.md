# Thor 0.1.2: server boot succeeded; native connection failed

The October 15, 2026 physical AYN Thor reports confirm that **Combined 0.1.2 booted the local server**. The native client then received a real local DB character list, selected an existing character, and began the DB-provided Map handoff. It stopped with `COH_LIMIT`; Map application acceptance and a native live world are unverified. A separate UI layout failure also stopped the accepted offline native preview.

The sanitized numeric record is [thor-012-server-connection.json](thor-012-server-connection.json). Original private reports remain outside the repository. Their SHA256 values and member hashes identify the inputs without copying credentials, account or character names, private paths, import identity, or session identity.

## Exact binary and report ordering

The installed APK matches the qualified 0.1.2 delivery:

| Property | Value |
| --- | --- |
| Package | `org.coh.nativecombined` |
| Version | `0.1.2-local-server-native`, code 3 |
| Bytes | 11,519,003 |
| SHA256 | `1913613656032400ee7ba70a46d56242567d23040b896032ad8a9bc90e9ae449` |
| Runtime source | `377584651471e748fbbd4a24cdf08bd2c48ca4a3` |
| Device | AYN Thor, Android 13 / SDK 33, ARM64, physical device |

These exports contain several different snapshots. Their roles matter:

- The archived **0.1.2 ready attempt** records the running server and current memory samples.
- The **earlier standalone client report**, before export-related suspension, preserves protocol phase `FAILED` and `last_status: 4`.
- The ZIP's later client report retains that status and failure count but has phase `SUSPENDED` after two suspends.
- The ZIP's top-level combined report records a fresh stopped app after process exit/reopen, with zero memory samples. It does not invalidate the archived ready attempt.
- The `previous-session` guest failure and older archived attempt belong to **0.1.1** (`RETAINED_GUEST_DEPENDENCY_FAILED` during DB startup). They are historical evidence of the already repaired startup failure.

## Physical local-server evidence

The ready stage was reached after **556,310 ms (9 min 16.310 s)**. The archived snapshot was captured at 716,398 ms with `ready: true`, `owned_process_alive: true`, and no failure code. Major startup milestones were:

| Stage | Elapsed ms |
| --- | ---: |
| PostgreSQL | 14,152 |
| Local login ODBC | 23,354 |
| DB startup | 36,901 |
| Atlas startup | 173,107 |
| Source helper create/connect | 455,183 |
| Source helper live currency | 550,123 |
| Source helper protocol logout | 553,274 |
| Server ready for manual native launch | 556,310 |

The source helper stages describe server preparation and its existing disposable character provisioning. They do not establish native character creation or native live-world rendering. The unchanged `server_runtime.py` requires server readiness and local `UseFakeAuth 1` policy before publishing this ready stage.

The running memory observer recorded 701 samples, zero invalid samples, zero pressure samples, and no stop request. Minimum observed system headroom was 6,055,989,248 bytes; minimum Java heap headroom was 200,999,568 bytes. These measurements cover the observed running attempt; they do not guarantee that Android cannot kill a later process.

Android exit history supplies independent evidence for the earlier reported kill: an older record has reason 3 (`LOW_MEMORY`). The latest two records have reason 10 (`USER_REQUESTED`) and `low_memory: false`. This confirms an earlier Android low-memory exit, but does not identify its allocating process, allocation, or precise cause. This attempt has no final orderly guest cleanup report; graceful server stop/restart remains unqualified by these attachments.

## Native local connection evidence and limits

The standalone report records one connection attempt, one received character list, one character choice, and one Map handoff. Two sockets opened and both closed; policy rejections were zero. The counters correspond to actual local DB messages and the DB handoff accepted by `coh_map_client_begin`, rather than an offline scripted test.

`last_status: 4` means **`COH_LIMIT`**, according to `engine/coh_contracts.h`. It does not mean unsupported. The report lacks detailed transport/Map terminal diagnostics, so it cannot locate the exact failing bound. Existing `coh_local.c` closes both modules before taking its terminal snapshot. Consequently the recorded closed/cancelled module phases and cleared identity flag cannot reconstruct the original failure site or disprove the earlier DB exchange.

No Map application connection, encrypted AuthServer login, server-authoritative world state, or native live-world rendering is claimed. Local `UseFakeAuth` character selection is a narrower development milestone than Gate 26 authentication. This report adds physical local-server/DB evidence without granting complete Gate 25, 26, or 27 acceptance.

## Independent native preview failure

At local connect, the preview rendered normally at **1920 × 469**. The next rendering context received **1920 × 137**, an aspect ratio of approximately **14.0146**, and immediately reported `Source session camera failed`. This happened before the character-choice event. The source camera in `world/coh_world.c` accepts aspect overrides only within **[0.25, 8]**. The combined Activity's expanding character controls consumed the scene height and supplied a surface outside that bound.

The unchanged source camera was compiled with `-std=c11 -Wall -Wextra -Werror -ffp-contract=off` for a focused four-control host check. With a valid camera (`fovy=60`, `aspect=1`, `znear=0.1`, `zfar=1000`), `coh_world_camera` accepts the earlier `1920/469` aspect and both bounds, and returns `-2` for the reported `1920/137` aspect. The numeric record includes the tested source SHA256 and return codes. This check isolates the rejected input; it does not qualify a UI repair.

The failure snapshot has 532 frames, two completed contexts, released objects, zero GL/EGL errors, zero transform mismatches, zero depth-order mismatches, and zero source-asset errors. Decoded cache reuse remains visible (25 hits, eight misses, no evictions). The preview is explicitly offline (`preview_is_server_world: false`).

The next repair must keep a source-valid render surface while the character list and status text change, and preserve useful terminal protocol diagnostics. The accepted renderer/camera bounds and Gates 22–24 need no implementation change. Testing a subsequent repair must cover actual character-list expansion as well as Surface/Home recovery.

## Evidence checks

The extraction used an explicit allowlist of app identity, numeric counters, status values, fixed stage names, and rendering diagnostics. Consistency checks compare each recorded subset against the original private inputs, verify their hashes and ordering, and reject leaked session/import identifiers or credential/name fields. The focused camera guard controls pass against the unmodified source. This record documents the observed 0.1.2 failure and partial progress; it is not a qualification result for a newer APK.
