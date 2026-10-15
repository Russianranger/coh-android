# 0.13.20 opt-in GPU renderer qualification

This pass follows the complete 0.13.19 scene/frame/renderer and background-capture
release. The new Thor export is `coh-atlas-gameplay-20261008-124326.zip`,
10,618,151 bytes, SHA-256
`592f0be66bf6da1eace77f5e7e13df9c5e5d2c051410cddcde4c99e8cd75dcea`.
It binds to app 0.13.19, source
`a4a658be25d2b5ca1393b7d3daedd83a7d9ca1f4`, and the audited Game
`adcabb11135fe44b2c1f997a088ec58e4ea0d90e9defaa9f88efea34538caa44`.
The complete bounded analysis is
`android-evidence/gpu-profile-0.13.19-thor-20261008.json`.

The user reports similarly low performance at 10 and 30, occasional 11–12 FPS
at 30, and 61–69 degrees Celsius. Startup is acceptable for current testing;
no manual startup time was recorded. Startup optimization and zoning are outside
this pass.

Native state confirms 30 -> 10 -> 30 with Show FPS enabled. Clean main windows
at 10 cover 70.476 seconds / 571 frames: 8.102 FPS, 123.586 ms mean interval,
97.721 ms work and 25.129 ms pacing. Clean 30 windows cover 121.090 seconds /
1,106 frames: 9.134 FPS, 109.574 ms mean interval, 108.808 ms work and 0.023 ms
pacing. Main thread CPU is about 20.6–20.8 ms per frame. Routes and thermal
conditions are not matched controlled experiments; do not claim a causal gain
from the cap comparison.

Approximately corresponding 30 renderer windows average 95.439 ms per batch,
67.954 ms excluding swap and 27.486 ms in swap, with about 30.036 ms renderer
thread CPU per frame. Main frame p95 upper bucket is 250 ms; 268/1,106 intervals
exceed 125 ms and 69 exceed 200 ms, with maximum 661.820 ms. Renderer batches
include queue gaps, scheduling and driver waits, so they are not pure GL or
raster CPU time. Explicit wait-iteration counters are zero even where the
backpressure bracket has appreciable wall time; that bracket is not proof of
`WaitForSingleObject` blocking.

Selected texture-copy/subcopy/VBO dispatch costs total approximately 0.0056 ms
per steady frame; selected framebuffer readback callbacks are zero. These
counters do not cover every possible internal effect callback or disk decode.
The final process snapshot contains eight llvmpipe workers, without interval
worker CPU, effective environment or CPU topology evidence. No unmeasured
worker-count/affinity override is justified.

The accepted capture optimization is operating: 380 captures, zero encoding on
the UI thread, mean copy/presentation freeze 4.679 ms (maximum 37), off-UI
encoding wall 84.161 ms / CPU 81.674 ms, and mean dispatch delay 0.189 ms.
Seventeen retained PNGs match their receipts. The relocated counter is visible
in route captures at 7.97 and 11.63 FPS. These observations verify behavior;
they do not establish an isolated FPS gain. Retained-PNG verification/callback
time remains outside encoder timing.

The strict save result remains FAILED: the previous temporary Commuter power
UID 680838905 disappears, while the other fifteen powers have no semantic
changes. Its approximately two-hour availability and ten-hour lifecycle gap
support an expiry inference only; authoritative native grant/eligibility proof
is absent. Cleanup passes and no crash is established. This pass does not relax
save comparison or change server/power/SQL behavior.

## Chosen renderer path and retained baseline

Stable 30 FPS needs about 33.3 ms per frame. The measured render/worker path
merits a substantial renderer change rather than another cap adjustment.
The new candidate is an opt-in GPU test: retain the existing Wine/FEX, native
Game, TigerVNC/RFB, Android Surface/input and graphics settings, and use retained
GLX Zink/Kopper with a separately source-built ARM64-glibc KGSL Turnip driver.
Software rendering remains the default comparison/recovery path.

The exact locked base runtime archive was independently downloaded and verified:
353,710,639 bytes, SHA-256
`08c639c26506dc6fbd15464bec475337087bb23cb7c0c5ace2db5240ee36424f`.
Its Mesa 22.3.6 Gallium binary contains the Zink entry point; retained native
GLX and Vulkan loader 1.3.239 are present. Mesa 26 source contains KGSL and
Adreno 740 support. This is native ARM64 driver execution; a FEX OpenGL-thunk
toggle is not the missing prerequisite.

`MESA_VK_WSI_DEBUG=sw` preserves presentation through the existing X display
while Vulkan rendering uses the selected GPU. It is a window-system transport
setting, not a claim that the renderer is hardware-backed. Driver/device and
real rendering probes must establish the candidate route independently.
No GL version override, gameplay graphics degradation, extra buffering, old
native-layer change, resolution/asset change or server change is included.

The fixed selector is captured for each owned operation. A GPU request must
verify the installed source-bound archive, native Vulkan driver/device/queue
execution and the actual PE32 Wine/WGL shader/buffer/texture/framebuffer path.
The probes do not grant Game visual, gameplay or save acceptance. Rejection with
verified cleanup can select the retained software route before Game starts;
uncertain cleanup or cancellation must not start a fallback Game. No mid-game
automatic restart is permitted.

The GL prerequisite probe exercises compatibility drawing, ARB vertex/fragment
program execution and limits, indexed VBOs, DXT1/3/5 mip/subimage uploads, BGRA,
and a 600x450 framebuffer with 24-bit depth plus presentation/readback. A
renderer string, extension list or the old simple client-probe PASS alone is
insufficient. These are prerequisite checks, not complete Cg/material/Game
compatibility or physical performance qualification.

## Release and device evidence boundary

The 0.13.19 Game/client archive and all twenty DLLs remain retained. The next
candidate adds a separately identified GPU archive and policy helper, updates
only the reviewed selector/launch helper sources and verification manifests,
and preserves the accepted source recipes. Runtime identity changes require
one Set up / update runtime before testing; no asset reimport or data reset.

Qualification must carry all 91 retained suites and seven real PostgreSQL
fixtures, plus the new GPU policy/package/probe/source/ABI checks. Exact public
donor/source/payload/DEX/resource conservation, SDK/signing/alignment, fresh
prepublication audit and an independent actual-public-APK audit remain gates.
Final source/APK/archive/probe pins belong in HANDOFF/publication evidence after
those gates pass. Hosted checks cannot establish Adreno activation, stable
30 FPS, temperatures, material correctness or stability on Thor.

Follow `COH-Atlas-Gameplay-0.13.20-testing.txt`: compare retained software and
opt-in GPU over the same 30 FPS Atlas route, collect displayed renderer/FPS,
visual glitches, hitches, temperatures and stability, and export the complete
outer report after each operation. Do not zone. Keep startup timing optional
for this pass; record GPU prerequisite/fallback status separately.
