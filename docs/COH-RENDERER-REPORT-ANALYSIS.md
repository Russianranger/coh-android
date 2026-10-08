# Renderer report analysis after 0.13.20 recovery

The interrupted session already published and audited 0.13.20 at
`5a592380a5272a187248a1f971d9798a298ca5c0`. The next device test remains that
APK. The report analyzer is host tooling only; it changes no installed runtime,
renderer, server, input, assets, character state or save acceptance. No APK
version increment or duplicate publication is needed for this change.

## Analyze a complete device export

Run from the repository root:

```bash
python3 tools/android/interactive/analyze_client_renderer_performance.py \
  /path/to/coh-atlas-gameplay-report.zip --output /path/to/renderer-summary.json
```

Use the complete outer export, including `android-client-report.json` and
`guest-report.zip`. The summary retains the support file hash, app identity,
startup and scene measurements, native frame distributions, renderer costs,
Android capture metrics, GPU selection/fallback evidence and strict save result.
Reports before the GPU selector can still be analyzed; absent GPU diagnostics
are reported as absent.

Main gameplay frame windows are grouped by the observed native FPS cap. The
first window after a cap/state change is conservatively excluded from stable
cap groups. Transition, mixed-state and unclassified coverage remain visible.
This avoids combining 10 and 30 FPS into a misleading single gameplay result.
Actual cadence comes from measured native intervals, not the configured cap.
Percentiles are histogram bucket upper bounds, not exact frame-time samples.
Stable windows at the same cap can cover multiple separated episodes. In the
latest 0.13.19 export, the analyzer includes both stable 30-cap gameplay
episodes; the earlier static assessment selected the later episode only and
also reported frames per observation-window second. Its numbers need not equal
the analyzer's count-weighted interval cadence. Neither scope labels a route
or establishes a controlled gain.

Renderer and presentation summaries remain separate. Their report ordinals do
not identify the same frames or prove synchronized intervals. Renderer batches
include queue gaps, scheduling and driver waits. Thread CPU excludes Wine/FEX
and llvmpipe worker CPU. Selected upload/readback callbacks are nested costs,
not exhaustive texture conversion or GPU completion measurements. Scene phases
overlap and must not be added to their parent timings.

GPU requested mode, selected mode and successful prerequisites are distinct from
Game's reported renderer. Selecting GPU or passing the Vulkan/WGL probes cannot
establish full gameplay hardware rendering, visual correctness, sustained 30 FPS
or a thermal improvement. A Software fallback and its reason remain evidence,
even when the resulting gameplay is unchanged. Conflicting or missing backend
evidence must not be treated as a successful GPU test.

Save failures remain failures. The latest 0.13.19 export reports a power
comparison difference; temporary Commuter expiry is an inference, not an
accepted save result or proof of character loss. Export failures before another
operation replaces their evidence.

## Next device comparison

Follow `COH-Atlas-Gameplay-0.13.20-testing.txt` and the current `HANDOFF.md`:
preserve app data, update the runtime once, then run matched Software and GPU
test routes at Performance 800x600 and the 30 FPS cap. Record actual FPS,
temperatures, visual glitches and fallback status, saving and exporting after
each run. Stay in Atlas. Analyze each export separately before choosing the
next runtime optimization; no causal improvement follows from unmatched routes.

The focused `client-performance-report.yml` workflow runs the existing startup
and scene analyzer tests together with the new renderer report tests. It builds
no APK, driver, server or native Game and uses read-only repository permissions.
