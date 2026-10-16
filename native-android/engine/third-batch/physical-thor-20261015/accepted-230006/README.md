# Support 0.2.0 code 201 — physical acceptance within agreed scope

**The user-approved physical test round is complete. No further tests of this APK are requested.** The user states: “Consider 2,5, and 6 as unnecessary tests for now. All the rest were successfully completed.”

The deferred checks are **2: Male portrait framing**, **5: external audio-focus interruption**, and **6: alternate audio-output route listening**. They remain untested/deferred, not passed. All other requested final checks are accepted from the user's confirmation, report and screenshots. This acceptance covers the bounded offline Support application; it does not close full numbered engine gates or qualify live gameplay.

The installed APK remains `org.coh.nativesupport`, version `0.2.0-gameplay`, code 201, SHA256 `ed280805188d82ffbb911e9799f43c42a5a0382fb8346ff97ffc794d85cc9ddc`. Runtime source: `e89f20c56619cbab87728bd49eff8f835b3b3c98`. All four reports share the session and original verified asset manifests. Device: AYN Thor, Android 13, Adreno 740, native ARM64.

| Observation | Latest physical result |
| --- | --- |
| Active foreground | **43m51.354s** |
| Rendered frames / aggregate rate | **157,101 / 59.70 FPS** |
| Frame observer | Mean 15.612 ms; p95 upper 20.5 ms; p99 upper 28 ms; maximum 47.483 ms |
| Slow samples | 161 above 33.33 ms; **zero 100 ms stalls** |
| Graphics lifecycle | 37 contexts started /36 completed; zero unexpected graphics/cleanup/transform/support errors |
| Male lifecycle | Male Home/return observed, including 18.597 s pause; 4,459 preview frames, 8 resource uploads, 0 failures |
| Animation | 8 explicit selections, 7 new presses with Wretch visible; final mode normal locomotion |
| Bounded collision | 34 wall hits and 15 sliding ticks; larger-world alignment remains outside this scope |
| Memory | RSS 187.02 MiB / PSS 77.51 MiB; lower than the prior 200.17/91.25 MiB |
| Audio | Running, 19 opens/18 closes; no reported device error; prior user-confirmed audible playback |

Both supplied screenshots were read successfully. They show readable Missions and Contacts panels, focused rows, local inspection messages, health/endurance HUD and power tray over the bounded station. The missing authentic icons are explicitly labeled. The screenshots do not change original-material/full-zone acceptance.

Four event windows reconstruct all 301 events without gaps. Nine pauses/resumes include actual Male and Wretch recovery; three explicit recreations are preserved. Three expected canceled/stale Surface errors recovered. Nine abandoned timing observations are lifecycle accounting, not compositor-drop measurements. Render-frame means exclude outer sleep; FPS uses frames divided by active foreground time.

Developer follow-ups remain: process/managed heap and report-allocation profiling, and the newly retained **86.108ms maximum audio callback**. The latest RSS/PSS/Java endpoints fell, so the four samples do not show monotonic growth or prove a leak. Callback statistics cover joined backends only; zero recorded mixer stream-underrun frames does not certify deadlines, platform xruns or latency. No new manual endurance or audio tests are requested for this release.

Female/Huge completion, source face/material parity, full zones, larger-world/multi-actor work and complete FX/icons remain development work. Gates 25–27 and all server/live-session paths remain exclusively owned by the primary agent. Accepted Session 0.3.0 and Combined apps are unchanged.

`assessment.json` records the exact user decision, input identities, metrics and limits. The report is preserved byte-for-byte as `COH-NativeSupport-20261015-230006.json.gz`, raw SHA256 `1f9b28e1c8b44ef0bcb2042ecbfe7fc7bd11151b7a2d8294c49b403db9d017de`. Screenshot hashes identify the unchanged original attachments. Earlier assessments remain historical evidence. This publication changes evidence only and requires no rebuild.
