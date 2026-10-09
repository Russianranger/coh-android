# 0.13.22: render-worker wakeup and focused pipeline measurements

## Recovered checkpoint and completed device milestones

Recovery found branch `codex/character-persistence-continuation` at
`75cc2947b180f34bb5c2ef8857bdfaf367ba85ef`, open draft PR #1, and main still
at `04d62616e2e1b41b10f35a04d4c798e43680d5ba`. No newer branch work or
published APK was present. No COH checkout or active build existed in this
accessible workspace before the clean clone. This cannot establish the state
of an inaccessible prior agent workspace. Recent Actions were complete; owner
run 37837207655 passed all six 0.13.21 qualification/public-audit jobs. The
published source remains `20b559420b1bb0978b7eac6e6eecdfe2a468f693`.

The user's physical 0.13.21 test on AYN Thor succeeded with the GPU renderer.
They report regular 15–30 FPS, occasional lower dips, substantially smoother
gameplay than Software, and no observed loss of graphical fidelity. These are
user observations, separate from the log measurements below. GPU Game startup
and the observed improvement are completed device milestones. Stable 30 FPS
has not been established. Do not repeat the completed preflight repair or an
unchanged long Software benchmark.

## Reviewed device evidence

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| `coh-atlas-gameplay-20261009-111411.zip` | 14,019,289 | `ef9993c8d48c38ce558e875c3a17cbf8606a19150a160659f08270f7ce68381b` |

Actual owned Game logs report `zink (Turnip Adreno (TM) 740)`, OpenGL 4.3
compatibility Mesa 22.3.6. This confirms the Game backend independently of the
successful Vulkan/WGL prerequisites and selector. Conservative generic
hardware-validation flags in the report are not a failed launch. The export
passes Android/guest completion, committed SQL/position/powers/costume,
reopened character identity and cleanup.

Pure-gameplay windows conservatively attributed to native cap 30 contain
5,196 samples over 27 windows (main reports 37–63, 271.141 seconds). Mean frame
interval is **52.189 ms / 19.161 native cadence Hz**, histogram p95 upper bound
125 ms, maximum 349.706 ms. Per-window mean intervals range 36.153–86.713 ms.
Mean work is 48.951 ms, explicit pacing 2.990 ms, and sampled main-thread CPU
18.008 ms/frame. Native cadence is neither display refresh nor pure GPU
completion; the route/actions were not timestamp-labelled, so it is not a
controlled before/after comparison.

Independent slow renderer windows show non-swap batch wall time around
53–69 ms with only about 6–7 ms renderer-thread CPU and approximately 3 ms
swap. Measured framebuffer readback is zero and selected texture/VBO upload
callbacks contribute little in those windows. Main gfx remainder can dominate,
but includes scene processing and synchronous renderer waits. Renderer batch
time spans INITTOPOFFRAME through SWAP and **includes idle gaps waiting for
commands**. Main/renderer stream ordinals do not align and must not be joined
as if they were the same frame. These observations do not isolate GPU rendering
as the bottleneck.

Android recorded 733 captures: mean PixelCopy/presentation freeze 2.675 ms,
mean encoding CPU 106.375 ms per capture, zero encodes on the UI thread.
Encoding can compete for CPU, but capture freeze is not the dominant measured
native cost. It is sampled much less often than gameplay frames.

Exact identities, representative independent records, analyzer output pins
and limits are retained in
`android-evidence/renderer-sync-0.13.21-thor-20261009.json`.

## Next implementation and qualification

The native continuation repairs a concrete render-worker lost-wakeup race:
the worker previously declared itself asleep after resetting the event and
checking an empty queue. A producer could publish between that final check
and the asleep flag, see an awake worker, and omit the wake signal. The
consumer handshake declares sleep before the reset/recheck, and clears that
state when it finds work or returns from waiting. Queue contents, command
ordering, renderer features, worker count and frame buffering policy remain
preserved. Tests must cover publication/reset/recheck/wait interleavings and
the retained unthreaded behavior.

Focused bounded `COH_CLIENT_RENDER_PIPELINE_V1` instrumentation separates
major main graphics phases and synchronous queue flushes on gameplay frames,
plus render-command active wall time and inter-command gaps sampled once per
sixteen renderer batches. Renderer batches cover all states independently.
Main CPU/window boundary totals can include intervening menu/loading work;
phase overlap and sampling coverage must remain explicit. Command execution
can include driver blocking; gaps
can include scheduling or waiting for the producer. Neither is automatically
pure CPU work or GPU completion. No glFinish or blocking GPU query is added
to manufacture attribution. The next device report will identify the largest
measured phase and whether the wakeup correction affects frame cadence.

0.13.22 appends to the accepted Game source chain and uses the audited 0.13.21
APK as immutable donor. Preserve all assets, resolution/render scale, shaders,
visual features, controls, Android UI/capture, servers, saving/persistence,
Wine/FEX and the working GPU driver/probes and Software fallback. All nineteen
authored Java sources, DEX and Android resources stay exact.
Seventy of seventy-seven runtime payloads stay byte-identical; only the
reviewed Game archive, four typed native integration helpers and two
verification/provenance manifests change.
Do not rebuild Mesa or repeat the WGL repair. Startup and zoning remain deferred.

The first owner run `37924638566` completed actual Windows Game compilation,
the retained/new Win32 checks and source binding at native source
`5af0e27ccf6fbb53d5b3ff5c2c2f3bf5a1d58396`. The produced Game is 9,494,016
bytes, SHA-256
`1953fa3ed1bee3dcdecaed14ccd369730a13bc4addf06ddfc283f7f6f9211b72`.
Qualification then stopped because its shallow checkout lacked the parent
commit required by a retained publication-routing test. No APK was built or
published by that failed run.

The host-only recovery fetches the required history and gives this continuation
an exact administrative routing lane. It authenticates and reuses the completed
native artifact, keeping its original source, run, build recipe, Windows proof,
CMake evidence and Game bytes. The current publication source/run is recorded
separately; Game, Mesa and both GPU probes are not rebuilt. The package verifier
also checks the actual nested client manifest through its full typed ancestry
and exact canonical bytes, including boolean/integer/float rejection tests.

Publication requires actual Windows Game/native checks, the complete retained
99-suite qualification plus focused new checks and seven real PostgreSQL
fixtures, exact donor conservation, SDK/signing/source/payload verification,
and independent download/audit of the published APK. This source checkpoint
does not claim those jobs have completed or a new APK has been published.

Follow `COH-Atlas-Gameplay-0.13.22-testing.txt` after the release gates pass.
No sustained FPS gain, lower temperature, or visual correctness for the changed
Game is claimed before physical testing. The exact next milestone is a
successful .22 GPU Atlas route at retained fidelity, with native frame/pipeline
attribution, ordinary save/Finish, and then optimization of the largest remaining
measured rendering cost toward sustained 30 FPS or better.
