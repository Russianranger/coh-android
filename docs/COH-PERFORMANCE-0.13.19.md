# 0.13.19 renderer attribution and bounded Android capture work

The physical 0.13.18 run reached Atlas with the accepted 0.13.17 native client.
The user reports unchanged startup, a perceptible difference between the 10 and
30 FPS settings, low FPS, occasional hitches, an unreadable/missing FPS counter,
and brief black tearing at 30. The raw export is 10,166,662 bytes with SHA-256
`3474f571b7cc0b552c07980274c834b192e19d6260622c4de0a899f4b19b6dbd`.
The bounded evidence audit is `android-evidence/renderer-attribution-0.13.18-thor-20261008.json`.

Operation-to-input-ready was 580.454 seconds, observed login 615.012 seconds,
and world connection 683.521 seconds. Local Atlas startup was 232.156 seconds,
actual client startup 168.145 seconds, and login-to-world 68.509 seconds.
These milestones are different from a manually timed launcher-to-playable-world
measurement. No controlled startup improvement is established.

Clean main-thread windows after the 10 FPS submission cover 50.108 seconds and
422 frames: 8.422 Hz, mean work 92.470 ms, pacing 25.615 ms and gfx submission
25.205 ms. After the 30 FPS submission, 90.372 seconds and 909 frames give
10.035 Hz, work 98.781 ms, pacing 0.005 ms and gfx submission 41.020 ms.
Routes are not matched. These observations do not establish a gain or sustained
30 FPS. The old submission bracket includes `gfxUpdateFrame`, scene traversal,
and `windowUpdate` backpressure; it is not pure enqueue CPU time. Sampled main
thread CPU is about 18 ms/frame and excludes llvmpipe/Wine/FEX worker costs.

The native FPS display is visible in retained captures 122 and 128, reading
9.29 and 13.54 respectively, but overlaps the top HUD and lacks an FPS label.
The new append-only native layer changes only its label/position, preserving
stock sampling, showfps gating and timestep. It displays `FPS … | … ms/frame`
at stock default-font coordinates (8,112), below the crowded HUD. The same
sidebar Show FPS / 10 FPS / 30 FPS commands and paired Start/Enter stay retained.

The concrete presentation optimization moves Surface diversity scanning, PNG
compression and initial SHA computation out of the Android UI thread. Previously
they ran there after each roughly one-second PixelCopy. Presentation now resumes
as soon as PixelCopy completes while a process-wide worker encodes its owned
bitmap. One worker, zero waiting queue and per-view ownership bound outstanding
work, including Activity recreation. Session, listener, surface generation,
freshness, three-frame readiness, PNG limits and exactly-once bitmap recycling
remain enforced. Runtime independently rehashes retained PNG proof bytes as
before; that bounded callback cost is not included in the new encoding metric.
No screenshots or acceptance gates are removed to obtain a better benchmark.

`android-client-report.json.android_capture_diagnostics` contains constant-size
count/mean/maximum/sum data for successful owned captures, including discarded
proof views: PixelCopy wall time, presentation freeze, encoder dispatch delay,
encoding wall/CPU time, actual UI-thread encoding count, pending-frame peak and
frames coalesced during copy. Individual retained captures carry the same costs.
The count is bounded to 20,000. This is Android capture overhead, not native FPS
or RFB throughput, and cannot authorize any readiness/save predicate.

The new native `COH_CLIENT_RENDERER_ATTRIBUTION_V1` stream retains the four older
diagnostic streams. Main windows split gfx wall time into unchanged frame
backpressure and the remaining gfx work. Renderer windows measure command-batch
elapsed time through completed swap, swap wall time, selected texture copy/
subcopy, VBO creation and framebuffer readback dispatch, with distributions and
long-frame buckets. Actual thread CPU is sampled only at window boundaries.
Numeric maxfps/showfps state observations provide native corroboration; they
are not a per-button acknowledgement. Each thread stream is bounded to 120
roughly ten-second windows and numeric state observations to 64.

These phases overlap. Renderer batches include queue gaps, driver waits and OS
scheduling; thread CPU excludes llvmpipe/FEX/Wine workers. Texture/VBO/readback
dispatch costs include synchronous driver work, not isolated texture disk decode
or GPU completion. Native scene phases cover loading completion. Do not add
nested metrics or interpret RFB updates as native FPS. Seven llvmpipe workers
were observed in the prior process snapshot, without effective environment or
per-worker profiles. No worker count, affinity, buffering, GL flags, resolution,
assets, server code or zoning behavior is changed on that evidence.

The 0.13.18 report failed strict save comparison because one temporary power
was added. UID-based analysis preserves all 15 prior semantic power rows and
identifies the added power as the stock-compatible Commuter movement bonus.
The export lacks proof of the exact native grant/eligibility. The historical
failure stays failed. New producer-only read-only lifecycle observations and a
bounded failure-after snapshot/power delta improve the next diagnosis. They do
not relax save acceptance or mutate SQL, schema, powers or server behavior.

Release qualification authenticates the 0.13.18 APK/receipt and accepted native
ancestry, reconstructs/reverses the new patch, executes the shared native helper
and unchanged font path on genuine Win32, and builds the Game-only client with
the accepted toolchain. Retained suites, seven real PostgreSQL fixtures, exact
four Java/four helper changes, seven runtime replacements and 68 preserved
payloads, all DLL/server/cache/resource identities, SDK/signing/DEX closure,
fresh prepublication audit and independent actual-public-APK audit are gates.
Final source, APK and receipt pins belong in HANDOFF/publication evidence only
after those gates pass. Hosted correctness is not a physical performance result.

The first hosted candidate `a32df4e24d1e80168f9b27897a2a1c2b8f9d9b57`
in run 37721873467 passed genuine Win32 logic qualification but failed the real
Game build: the new gfx header imported Windows before stock Winsock2 includes.
No APK was published. Only the new header insertion moved below the complete
stock include block, with an exact source-order regression; old native layers,
global compiler flags, rendering, buffering and timing policy remain unchanged.

Install as an update and run **Set up / update runtime once** for the changed
native/helper generation. Preserve imported assets and the existing character.
Follow `COH-Atlas-Gameplay-0.13.19-testing.txt`, export the complete outer report
after each run, and continue client/presentation optimization from that evidence.
Physical improvement, counter visibility and stability remain pending Thor
testing. Zoning remains deferred.
