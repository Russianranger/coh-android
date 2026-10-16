# Support code 201 — AYN Thor physical evidence, October 15, 2026

**Closed within user-approved scope:** [Final physical acceptance](accepted-230006/README.md). Final checks 1, 3, 4, 7 passed; 2 portrait, 5 audio focus and 6 alternate route were explicitly deferred by the user. No further tests of this APK are requested. The instructions/assessments below are historical.

**Newest update:** [22:45 longer-run assessment](long-run-224517/README.md) reaches 29m59s at 59.75 FPS and verifies nonempty chat plus Male-active recreation. [Remaining tests](long-run-224517/REMAINING-TESTS.md) exclude already completed checks. Latest RSS/PSS rise requires developer investigation; earlier records below remain historical.

**Earlier update:** [The 22:31 endurance follow-up](endurance-223100/README.md) verifies 15m44s of active execution at 59.85 frames/s, two pause/resume cycles, audio route reopens and user-confirmed normal music/audio. The bounded ten-minute endurance and audibility checks pass; the full consolidated checklist remains open. The assessment below is the preserved initial 22:18 report.

**Physical execution and the exercised subset pass. The full consolidated physical checklist remains open.** The user supplied one JSON report and four screenshots, without a blanket statement that every requested test passed.

The installed package is exactly the published ARM64 APK, `org.coh.nativesupport` version `0.2.0-gameplay`, code 201, SHA256 `ed280805188d82ffbb911e9799f43c42a5a0382fb8346ff97ffc794d85cc9ddc`. Both report asset manifests match the signed build receipt. Device: AYN Thor, Android 13/API 33, native 64-bit, Adreno 740; emulator=false.

| Observation | Physical result |
| --- | --- |
| Foreground interval | 195.104 seconds (3 minutes 15 seconds) |
| Rendered frames | 11,660; approximately 59.76 frames per foreground second |
| Frame observation | Mean 15.552ms; p95 bucket upper bound 18 ms; p99 upper bound 23 ms |
| Slow samples | 6 over 33.33 ms; zero over 100 ms; maximum 40.913 ms |
| Graphics lifecycle | 9 contexts started, 8 completed, final context active; zero reported GL/EGL/cleanup errors |
| Movement/input | 5,537 movement ticks; 141 animation transitions; 1,722 external controller events plus touch |
| Male preview | 576 frames,4,608 draws, 8 parts, 1 upload, zero failures |
| UI/mock state | 31 power uses; 33 presentation events/animation bindings; 8 inspection intents |
| Process memory | RSS 180.65 MiB, PSS 72.65 MiB; one current sample 197 ms old |
| Audio | Running; no backend close; diagnostics_valid=0, so callback/underrun fields are unavailable |

The measured short bounded scene sustains approximately 60 rendered frames per foreground second. This is not full-game or ten-minute performance acceptance. The reciprocal of the frame-observer mean is not used as an FPS claim. GPU timing and thermal behavior are unmeasured.

The complete Male is visible in landscape, including hair, head, both hands and boots, without clipping or HUD occlusion. Wretch, station geometry and native UI remain visible after switching back. The visible lower-face/neck blue region, angular face markings and thin part-join seams match the emulator appearance; source-original face/material/morphology parity remains open. Static screenshots cannot establish absence of flicker. Black terrain gaps reflect the bounded scene; empty power-specific icons remain incomplete.

## Remaining physical checks

Use the existing APK; this evidence update does not rebuild or change it. Complete ten active foreground minutes and multiple memory reports, Home/resume, audio-focus interruption/alternate route and a stopped-backend audio observation. Send a nonempty chat message, exercise the explicit animation selector, and recreate while Male preview is active. Portrait Male framing, wall/sliding collision and complete panel/character-selection coverage are not established by this report. Do not reset/uninstall accepted applications.

`assessment.json` records exact input SHA256 values, counters and scope. The original report is preserved byte-for-byte as `COH-NativeSupport-20261015-221828.json.gz`; decompress it with gzip to inspect the original. Screenshots remain the user's unchanged attachments, identified by filename/hash.

No new full numbered gate is closed. Gates 1–24 retain their earlier scope; gates 25–27 remain exclusively with the primary agent. Larger-world, Female/Huge, authoritative combat and sustained audio/performance work remain open.
