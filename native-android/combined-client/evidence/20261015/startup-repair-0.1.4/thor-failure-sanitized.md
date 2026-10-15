# Thor 0.1.3 startup interruption and retained display endpoint

The new October 15, 2026 Thor export contains two distinct failures: Android reported a low-memory exit during an early 0.1.3 startup; after ownership recovery, the next startup failed because the owned presentation endpoint already existed. **This export does not contain a new 0.1.3 native-client test result.** Its embedded native-client report is the retained 0.1.2 report, byte for byte.

The allowlisted evidence is [thor-failure-sanitized.json](thor-failure-sanitized.json). Original private input bodies remain outside the repository. The record preserves the input/member SHA256 hashes, fixed status codes, public app identity, bounded numeric memory observations, and event timing. It excludes account/character names, credentials, private paths, import identity, and session identity.

## Current failure: existing presentation endpoint

The combined app report identifies `0.1.3-local-server-native`, code 4, ARM64 / SDK 33. It records `OWNED_DISPLAY_SOCKET_ALREADY_EXISTS` at **15,652 ms**, with the last published stage `preflight_selected_map_port`. The guest's matching final report records:

| Field | Result |
| --- | --- |
| Status | Failed / `AdmissionError` |
| Primary failure | `OWNED_DISPLAY_SOCKET_ALREADY_EXISTS` |
| Cleanup failure | None |
| Profile preserved | True |
| Cleanup complete | True |
| PostgreSQL graceful cleanup | True |
| Owned processes reaped | True |
| Server ready | False |
| Conventional/native client started by guest | False / False |

The guest UTC stages start at **2026-10-15 21:25:42.736526 UTC** for local-port preflight. Input admission passes after 4.120 seconds; private server input preparation passes after 6.386 seconds. Existing verified required geometry is reused, with 406 files checked and no geometry worker needed. PostgreSQL starts, and selected-map-port preflight passes at **21:25:57.836546 UTC**. The failure then occurs before the next `presentation_display` stage.

The source `server_runtime.py` rejects an existing presentation endpoint before calling the presentation/Wine startup path. The exported failure establishes that this admission check rejected an existing object. It does not record the object's filesystem type or listener liveness. The completed Android ownership recovery checks for remaining owned processes and clears interrupted ownership/ready markers; in 0.1.3 it does not remove this endpoint. The retained endpoint therefore remains an independent restart blocker even though ownership recovery completed.

The current memory observer has 17 valid samples, no pressure samples, and no stop request. Its minimum recorded system headroom is 9,193,500,672 bytes; minimum Java heap headroom is 245,924,776 bytes. This attempt reaches a normal diagnostic failure and records cleanup. The result does not qualify a subsequent restart or guarantee that no old filesystem object remains.

## Earlier interruption: Android low-memory exit

The same bundle archives an earlier 0.1.3 attempt with a last persisted snapshot at **5,135 ms**. Its last stage is `server_only_input_admission`; it is still marked starting with an owned process alive at that snapshot. There is no final guest report for that attempt.

Its seven valid memory samples span admission through 5,092 ms. They show:

| Observation | Value |
| --- | ---: |
| Minimum sampled system headroom | 8,315,179,008 bytes |
| Minimum sampled Java heap headroom | 245,580,856 bytes |
| Invalid samples | 0 |
| Pressure samples | 0 |
| Cooperative stop requested | False |

Android's latest process-exit record has **reason 3 (`LOW_MEMORY`) at 2026-10-15 21:25:32.637 UTC**, with importance 100, PSS 78,634 KiB, and RSS 184,828 KiB. This corroborates an Android low-memory exit. High sampled system/Java headroom did not prevent it; those samples neither identify the failing allocation nor establish which native/guest process, memory-accounting limit, or transient pressure caused the exit. No allocation cause is claimed.

The app elapsed-clock sequence is:

| Event | Android elapsed ms |
| --- | ---: |
| Earlier 0.1.3 startup requested | 605,429,456 |
| Earlier guest process started | 605,429,557 |
| Last persisted earlier snapshot | 605,434,621 |
| Ownership recovery requested after reopening | 605,440,474 |
| Ownership recovery completed | 605,440,489 |
| New startup requested | 605,444,693 |
| New guest process started | 605,444,746 |
| New guest process exited | 605,460,353 |

The current run's finalized duration and exit event imply an app diagnostic origin of 605,444,701 ms. The earlier running snapshot implies an origin of 605,429,486 ms. Correlating the current guest's first-stage UTC timestamp with its app stage time places the OS low-memory exit **approximately 5.4 seconds into the earlier run**, shortly after its 5.135-second snapshot. This is an approximate ordering check: guest UTC stages are generated before Android receives their progress messages, and diagnostic millisecond values are rounded. It is not exact allocation timing or proof that input admission itself allocated the fatal memory.

Another archived 0.1.3 snapshot precedes this interrupted run: an eight-millisecond `SERVER_ADMISSION_FAILED` attempt followed by ownership recovery. Older 0.1.1 startup-failure and successful 0.1.2 server-ready snapshots also remain in history. They are separate attempts, not competing descriptions of the current failure.

## Embedded client report is stale 0.1.2 evidence

The native-client member has **223,933 bytes**, SHA256 **`a6f1afef6cd722b866529a47e7f7e17f89a8a6b3746d9b7e809ef3118c943e28`**, and is byte-identical to the native-client member in the previous 0.1.2 export. It explicitly identifies:

- `0.1.2-local-server-native`, code 3.
- Installed APK SHA256 `1913613656032400ee7ba70a46d56242567d23040b896032ad8a9bc90e9ae449`.
- Update time `2026-10-15T15:24:38.590-05:00`, before the new startup attempts.
- The previously observed suspended protocol status with `COH_LIMIT`, and the old 1920 × 137 source-camera failure.

Those retained values cannot assess the 0.1.3 protocol or viewport repairs. The current combined report identifies version 0.1.3 but supplies no current installed-APK hash. The record therefore lists the expected qualified 0.1.3 delivery hash separately and does not claim an independent exact-binary match from these attachments.

## Scope and next verification

This evidence preserves the earlier physical 0.1.2 local-server boot result while recording that 0.1.3 startup/restart remains unaccepted. No new encrypted authentication, Map application acceptance, native live world, or Gate 25–27 acceptance is claimed. Accepted Gates 22–24 are unchanged.

A repair needs to recover the owned presentation endpoint safely after interruption and examine early startup memory independently of sampled Java/system headroom. A later Thor run must first establish a new server-ready attempt, then launch the native client and produce a report identifying that new app version. This file documents the failure; it does not qualify the 0.1.4 repair.
