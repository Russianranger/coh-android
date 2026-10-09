# 0.13.25: render-worker wake coalescing and sparse scene/queue evidence

## Recovered state and completed device milestones

Work resumed from clean `fffd44f108fbcb871e35570df17d934f2cc158cd` on
`codex/character-persistence-continuation`, open draft PR #1. The latest published
APK was .24, source `3d73e9b4c71fe3f87de6bf0bb41fc0ce50f3f6ce`, owner
`37973264500`; main remained `04d62616e2e1b41b10f35a04d4c798e43680d5ba`.
Remote branches/tags/releases/PR/Actions and available local state showed no
newer work or active build to duplicate.

The user's new result confirms runtime setup and world login work, while FPS
has regressed. The complete .24 Thor export is
`coh-atlas-gameplay-20261009-195656.zip`, 13,704,444 bytes, SHA-256
`ab4e657d9cbcf133f3875d11b3c951ad5cfc4e0381e1e9a19e512f6950136521`.
Reviewed measurements, exact raw-member hashes/line pointers and acceptance
limits are in `android-evidence/render-queue-0.13.24-thor-20261009.json`.

Setup finished in 342.591 seconds. The export verifies world connection, an
accepted current-session gameplay deadline, ordinary committed character save,
native saved-position evidence, clean Finish and process exit. Persisted position
changed by approximately 248 horizontal world units. However, the report's
explicit input-effect and overall gameplay qualification flags remain false;
successful input submission and changed position do not establish every control
or task milestone. The original .21 GPU startup and the user's smoother 15–30 FPS
without observed fidelity loss remain completed historical device milestones.
Sustained 30 FPS is still unestablished. Another standalone setup/GPU-preflight or
long unchanged Software benchmark is not the next milestone.

## What the .24 logs establish

The owned Game console reports `zink (Turnip Adreno (TM) 740)`, Collabora, OpenGL
4.3 compatibility Mesa 22.3.6. Native ARM Turnip remains the retained Mesa 26.0.0
payload. There is no observed Software fallback. Generic conservative hardware/
gameplay flags from this startup-only Reopen operation do not contradict the
actual Game renderer. The current Game is the unchanged .22 executable,
9,494,016 bytes, SHA-256
`1953fa3ed1bee3dcdecaed14ccd369730a13bc4addf06ddfc283f7f6f9211b72`, native
source `5af0e27ccf6fbb53d5b3ff5c2c2f3bf5a1d58396`.

| Measured scope | Result | Interpretation |
| --- | ---: | --- |
| 888 pure-gameplay intervals at observed cap 30 | 194.165 ms mean; 5.150 Hz | Native cadence, not display refresh or configured cap |
| Same gameplay frames, main-thread CPU | 54.245 ms/frame | Substantial client CPU work, already above a 33.3 ms frame budget |
| Same frame stream, submission wall | 175.436 ms/frame | Inclusive wall time; includes waits, not pure scene CPU |
| Independently anchored main graphics windows | 174.829 ms/frame | Graphics dominates native main wall work |
| Independent renderer non-swap batch wall | 179.967 ms/batch | Dispatch, starvation, driver/scheduling/waits remain mixed |
| Independent swap wall | 3.493 ms/batch | Small relative to non-swap work in these windows |
| Instrumented framebuffer-readback callbacks | 0 | No measured use of that callback; not proof of zero driver-internal readback |
| Android PixelCopy/freeze, 541 whole-session captures | 2.928 ms mean | Not a gameplay-aligned native FPS measurement |
| Background PNG encoding CPU | 103.201 ms/capture | Can compete for resources; does not run on the UI thread |

The detailed pipeline sampler is explicitly disabled on this current Game and
emits zero pipeline records. Turning it off did not recover the earlier cadence.
Old bounded frame/renderer metrics remain available. Near-window main and
render-thread CPU occupancy are approximately 28% and 24%; neither is pure GPU
time. Full-ring producer waits, scene setup/sorting/submission and driver/GPU
execution are not separated sufficiently to identify a single cause.

The existing Performance profile uses UI/source size 800×600 and render scale
0.75. This continuation preserves those exact settings. It does not claim native
scene resolution is 800×600. The .21 log mean of 52.189 ms/19.161 Hz and .22 mean
of 152.044 ms/6.577 Hz are useful context, but routes, controls, durations and
thermal/frequency conditions differ; they do not quantify an isolated causal gain.

## Selected alternative

The render worker previously issued `SetEvent` for each published command while
its sleeping flag remained set. A burst can repeat the same cross-thread wake
while Wine/FEX has not scheduled the consumer. The new render-instance-only
state distinguishes awake, armed and notification pending. A producer first
reads that state and claims armed→pending atomically only when needed; awake and
pending commands do not take an unconditional atomic or timing call. Commands,
queue capacity, order, padding, dispatch and graphics work remain unchanged.

The consumer preserves arm/reset/recheck/wait lost-wakeup protection and rearms
after reset before the final recheck. That second rearm handles a late producer
claim for an already consumed command whose event is erased by the next reset.
The interleaving model exposed this case before publication, and the actual
WorkerThread fixture exercises it. Control/flush/shutdown wakes, other worker
instances and unthreaded behavior retain their existing paths. A failed event
signal is recorded and the pending claim is released for retry.

This targets a concrete redundant synchronization path inside the measured slow
submission region. Existing logs do not prove it caused the regression. A paused
1,024-command fixture demonstrates one producer event call instead of 1,024,
with conserved ordered dispatch, one successful producer CAS and no per-command
clocks. That is a native work-reduction result, not a physical FPS result.
Win32 semantics are documented by Microsoft for
[InterlockedCompareExchange](https://learn.microsoft.com/en-us/windows/win32/api/winnt/nf-winnt-interlockedcompareexchange),
[SetEvent](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-setevent)
and [ResetEvent](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-resetevent).

Sparse diagnostics time setup, sorting and draw submission only on the first
and every 32nd ordinary gameplay frame. Ring clocks run only on actual producer
full-ring waits. Cumulative counters record submitted commands, armed/pending
observations, successful/failed producer event calls and ring waits. There are no
counts of unchanged control/monitor/full-ring-flush event signals in the producer
wake counter. Draw wall covers the four sorted-model passes, not all particles,
sky, UI or other rendering. There are no
per-command clocks, GPU completion waits or blocking GPU queries. Reports are
bounded to one window per at least ten seconds and at most 120 windows. Counter
saturation and invalid clocks remain explicit or stop the stream, not fabricated
zero timings. Missing metrics remain missing.

`analyze_client_render_queue.py` validates and summarizes the complete exported
ZIP. Queue snapshots include startup/menus and are not summed. Sparse scene
phases and ring waits overlap; do not add them. Independent frame, renderer and
queue window ordinals are not frame identities. The new current Game producer
is kept separate from historical .22 pipeline and .19 attribution producers.
Analysis does not relax save, cleanup, renderer or gameplay acceptance.

## Preservation, validation and next milestone

The new Windows job builds only Game. Completed Mesa/GPU/probe/server builds
are retained. The .24 Android setup repair, all 19 Java sources and exact .24
compiled DEX are retained. Four existing guest verification helpers recognize
the new typed Game extension and enable its bounded observations only for a
verified current launch. The .23 movement deadline/ordinary save behavior and
Reopen detailed-pipeline-sampler-off policy remain intact. Software fallback,
controls, UI, character persistence, schema, assets and visual features remain
unchanged. Current source, native executable, raw donor receipts and publication
receipts have separate identities; historical proofs are not relabelled.

Release gates include the actual staged WorkerThread compiled and run on Win32,
adversarial wake interleavings, burst conservation, disabled-diagnostics work,
ring pressure/cancellation/unthreaded behavior, sparse header fixtures, retained
regressions and real PostgreSQL fixtures, exact donor/native/helper/DEX closure,
SDK/signing and a separate actual-public-download audit. Publication-specific
counts, hashes and links are recorded after those gates pass.

The next physical milestone is the same short GPU Atlas route, with walking,
camera and ordinary Save/Finish, to determine whether this synchronization change
improves native cadence at retained fidelity. Sparse evidence will distinguish
scene setup/sort/draw wall and full-ring waits from the remaining render batch
cost; it will still not isolate pure GPU duration. No FPS gain is claimed before
that test. Startup and zoning remain deferred. Follow
`COH-Atlas-Gameplay-0.13.25-testing.txt`.
