# Material probe UI and report contract

The Phase 6 diagnostic uses the separate application ID `org.coh.materialprobe`.
It does not replace the accepted Phase 5 surface probe or start the game/server.

Before entering JNI, the loader verifies every file listed by the `assets`
object in `material-fixture.json`. Each entry is keyed by a simple filename
and specifies its exact `sha256` and `bytes`. The metadata limit is 128 KiB;
each file is limited to 16 MiB, all files together to 32 MiB, and the manifest
to 32 entries. Paths and invalid hash/size types are rejected. Verified hashes
and total bytes are retained in the report. No unverified file reaches JNI.

The five required files are `mesh.bin`, `texture0.rgba`, `texture1.rgba`,
`poses.bin`, and `material-reference.bin`. JNI receives the Surface and those
five verified byte arrays, in that order. Texture dimensions and case data
belong to the frozen binary reference formats consumed by the renderer.

The application runs a bounded native check automatically after an actual
`SurfaceHolder.surfaceChanged` callback. The controls also allow a fresh run,
a resize of both the actual width and height, replacement of the SurfaceView,
and export through Android's document picker. No shared-storage permission is
required. The status panel has a fixed line count so a status message cannot
change the dimensions under test.

## Saved evidence

The current report is written atomically to the app-private file
`files/material-probe-report.json`. Its schema is
`coh-native-material-probe-v1`. `qualification_passed`, `overall_passed`, and
`passed` all describe the same aggregate gate. A report also contains device
information, fixture provenance and verified asset hashes, lifecycle events,
native results, the current session ID, and timestamps. Emulator evidence is
explicitly labeled; it does not qualify an AYN Thor.

`native_runs` retains the last 20 current-session runs. `run_history` retains
the last 20 runs across launches; older sessions cannot qualify the current
session. Events are limited to 160. A sticky current-session failure counter
prevents a failure from disappearing from the gate when bounded history is
trimmed. A new Activity session starts fresh qualification after previous
evidence has been retained in history.

Each run records `callback_width`, `callback_height`, `generation`, `request`,
`duration_ms`, `passed`, `obsolete`, and the native result. Only actual surface
creation callbacks increment a generation. A native result must report the
same dimensions as the callback that requested it.

The aggregate gate requires:

- A successful latest request for the current foreground surface.
- All required native material/pose checks for each passing run.
- No nonobsolete failures in the current session.
- Successful rendering at two actual widths and two actual heights.
- Successful rendering on at least two actual Surface generations.

Each passing native result must set `passed`, `mesh_valid`,
`skin_transform_match`, `skin_render_match`, `material_pixel_match`,
`alpha_fog_passed`, `offscreen_passed`, `context_recreation_passed`, and
`window_pixel_match` to true. Its `surface_width` and `surface_height` must
equal the dimensions supplied by the actual callback. The native result
retains its per-context-cycle evidence in `cycles`.

Java also requires `pointer_bytes` and `long_bytes` to be 8, and
`required_cycles` and `attempted_cycles` to be 2. The `cycles` array must have
exactly two entries. Each entry must report `completed`, `objects_released`,
and `swap_passed` as true, with zero `gl_errors` and `egl_error`. Missing fields
keep the aggregate gate pending.

Runs are serialized on a single executor. A pending replacement request clears
queued work. A returned result becomes obsolete if its request, surface,
generation, dimensions, or foreground state changed while it was running.
Obsolete results remain visible in evidence and cannot qualify a surface.
After Activity destruction, callbacks and returned work cannot overwrite a
new Activity's report.

Export captures an immutable foreground report before the document picker
pauses the Activity. The exported qualification therefore describes that
captured state. The live report independently records background/resume
callbacks and requires a fresh current request after returning to the app.

## Automation

Launch `org.coh.materialprobe/.MainActivity` with `autoSmoke=true` to run a
successful first check, resize both dimensions, await success, recreate the
actual SurfaceView, and await success. The sequence is advanced by validated
run completions rather than timer delays. `auto_smoke_stage` reaches 3 on
completion. Hosted automation must also background and resume the Activity,
then require another successful current run.

Explicit `probe_action` string extras accept `run`, `resize`, or `recreate`.
The singleTop Activity handles those commands; there is no exported command
receiver. The default manual controls remain available without automation.
