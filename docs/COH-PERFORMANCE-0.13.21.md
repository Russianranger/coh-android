# 0.13.21: repair the failed GPU preflight and launcher completion

## Exact physical evidence

The user reports Software performance unchanged and GPU failure at client
start. Both exports bind to published 0.13.20 and its retained 0.13.19 Game.
The previous 0.13.20 release was already completely built, signed, published
and independently audited; it was not an unfinished source milestone.

| Export | Bytes | SHA-256 |
| --- | ---: | --- |
| `coh-atlas-gameplay-20261008-185209.zip` (GPU) | 1,700,091 | `56672993697367eaa82a86a328ccc14b91b941b7de8a766e5fcdbe64faa898bf` |
| `coh-atlas-gameplay-20261008-193638.zip` (Software) | 13,113,683 | `1606847ddc691ad16afc5ec802cb59cee2c4d6a6638099553a0942d228aecda0` |

Software's actual Game renderer is `llvmpipe (LLVM 15.0.6, 128 bits)`, OpenGL
4.3 compatibility Mesa 22.3.6. Its 7,366 pure-gameplay frames in stable 30-cap
windows average 106.587 ms interval / 9.382 Hz; p95 is a histogram upper bound
of 200 ms and maximum is 567.247 ms. Mean pacing is only 0.171 ms. These native
cadence measurements are neither display refresh nor an isolated controlled
optimization result. They corroborate the reported low FPS; raising the cap
has not solved the render/worker bottleneck.

The GPU Game process never started (`client_process_started=false`). Native
Turnip 26 KGSL detected Adreno 740 and verified a 4,096-byte queue operation.
The PE32 Wine probe reported `zink (Turnip Adreno (TM) 740)` and passed
ARB programs, multitexture, VBO/FBO, NPOT depth24, DXT1/3/5 mip/subimage, BGRA,
backbuffer drawing and SwapBuffers. It returned exit10 at
`post_swap_frontbuffer_readback`, with false GL_FRONT proof and zero GL error.
These successful prerequisites do not establish Game compatibility or GPU
gameplay performance.

The nonzero probe leader left owned Wine background services holding its output
pipe. Generic probe shutdown raised a cleanup error before private-prefix
cleanup completed, masking the original presentation failure. Later token/
prefix cleanup proved safe, but the already-fatal error prevented Software
fallback. This was not evidence of a Game crash or failed Vulkan driver.

Software's guest passed all save/reopen/SQL/powers/costume/native-position and
cleanup checks. Android nevertheless rejected `observation_seconds=1304.498`
against a legacy 1210-second limit. Its matching native gameplay-budget receipt
starts after actual character connection and grants 1200 seconds; Android's
approved deadline was exceeded by only 1.414 seconds at producer completion.
All 62 guest/runtime client pins matched. The failure was launcher completion
validation, not a demonstrated save loss.

## Narrow repair

The WGL V2 probe preserves the existing real rendering/texture/cleanup checks.
It swaps two distinct asymmetric four-quadrant RGB patterns and reads actual
visible screen pixels through Win32 GDI, with exact client size, GL-to-screen
coordinate conversion, window ownership and bounded attempts/time checks.
The second pattern rejects stale first-frame output. GL_FRONT and its error
remain diagnostic and do not substitute for visible-pixel proof. Other GL
errors remain fatal. A passing probe still does not grant Game acceptance.

The helper delays rejection of a failed owned-background probe leader until
the private prefix, token workers and output EOF are safely finalized. It keeps
the bounded raw receipt, original failure stage and exit code. Ordinary failed
prerequisites may fall back only after proven cleanup; uncertain ownership,
EOF/shutdown failure, cancellation or server-health failure remains fatal.
Ordinary WGL timeout, malformed result or local output-limit rejection follows
the same cleanup proof. The operation's global output/health/deadline bounds
remain fatal, including an original health failure that later checks recover.

Android's two evidence validators require a native budget matching the
current-session Android-approved event and a bounded monotonic deadline for
longer observations. The legacy short-session rule remains available when no
budget event exists. Current-session/PID, APK/runtime/native producer, strict
save/reopen and cleanup checks remain mandatory.

## Retained payload and next qualification

0.13.21 retains the exact public 0.13.20 APK as donor, including Game and twenty
DLLs, prepared assets, servers, Wine/FEX/rootfs, RFB/Android display and input,
Turnip/Mesa driver and native Vulkan probe. The production Windows job rebuilds
only the small WGL probe. Two Java evidence validators and DEX are rebuilt;
four runtime verification/helper/archive payloads change and 73 retain exact
bytes. The old GPU/Game producers and their source/ABI proofs remain explicit.
The signing identity and upgrade/data-preservation workflow are retained.

Hosted regression, real PostgreSQL, native Windows compilation, exact donor
conservation, SDK/signing and independently downloaded public APK verification
are release gates. No physical Thor FPS gain, successful GPU Game launch,
shader/material correctness or black-tearing resolution is claimed by them.

The next physical milestone is a successfully corroborated GPU Game session,
then the same Atlas 30-cap route with actual frame cadence, presentation,
visual correctness, temperatures and strict save completion. If the repaired
preflight still fails, the original stage and raw pixel evidence determine
the next targeted fix. If Game uses hardware successfully, prioritize the
largest measured native/renderer/presentation cost and black flashes before
another optimization. Do not repeat the unchanged Software benchmark or
rebuild Mesa/Game without new evidence requiring it.

Follow `COH-Atlas-Gameplay-0.13.21-testing.txt`. Final publication/source/APK
pins are recorded separately after the release audits pass.
