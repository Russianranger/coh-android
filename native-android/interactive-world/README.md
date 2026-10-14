# Gate 15: current input drives authentic source-world rendering

This integration worker renders the accepted Atlas Park bench fixture using
the original six-link group transform, two original material families, source
camera/view/projection kernels and accepted precise shader selection. It
includes the qualified world renderer unchanged to reuse its checked scene,
uniform, geometry, EGL/GLES and source-reference helpers. It does not modify
the previous qualified probe or immutable upstream source.

Before accepting interaction, each fresh context compares all six frozen
source camera/group cases on the CPU and all 512 fixture vertices per camera
through actual GPU transform feedback. During the 180-frame, six-second input
window, current cameras are evaluated by source kernels and sampled GPU
feedback is compared with CPU source arithmetic. Rendering uses original
vertices and native matrices; feedback/reference geometry never drives it.

The caller supplies one freshly consumed `CohInputFrame` per rendered tick,
under its input mutex, plus a monotonically increasing external Android-event
revision. No competing UI timer may consume those input frames. Duplicate
source frames and regressing revisions are rejected. Native input's explicit
30 Hz step is consumed once; slow frames carry no elapsed-time input backlog.
The run has 180-frame and 25-second limits, independently of graphics startup.
These are bounded diagnostic limits, not an FPS or latency qualification.
Fifteen scheduled current-camera GPU comparisons run at frame indices 0, 12,
24, through 168, with additional immediate checks for new signed directions.
This retains the first version's comparison coverage while removing redundant
idle rendering. Its software-GPU run had correct source/GPU/image direction
coverage and zero comparison/backend errors but reached the unchanged
25-second bound before finishing the arbitrary original 450-frame loop.

The camera adapter preserves source editor look's pitch negation and yaw
increment after removing the fixed target yaw+180 degrees relative to the
fixture camera. It converts source radians to degrees, accumulates increments
and clamps each additional pitch/yaw offset to ±12 degrees. That range keeps
the selected real fixture useful for visual checking. Reversal immediately
leaves a saturated bound; no excess input is queued. Original camera position,
roll, FOV and authored nodes remain fixture values. Left-stick character
movement, camera obstruction, collision and full Atlas loading are separate.

The report separates the graphics engine result from actual interaction:
four signed camera directions, changes after external-event revisions,
input-linked image changes and at least two settled source frames after
release. Each newly observed signed direction immediately triggers current
GPU feedback comparison and image capture until visible change is measured.
The accepted direction mask intersects CPU movement, GPU parity and changed
image coverage. Identical camera states must produce identical pixels.
Resize/recreation/Home can cancel the worker; that report retains any observed
errors and requires cleanup, while the replacement generation must execute
a fresh successful run. Only explicit cancellation or specific cancelled
window-Surface errors receive `expected_cancel`; source/input/numeric/GPU/GL,
deadline or cleanup failures stay session failures even if Home arrives later.
Already accumulated mismatch counters also remain sticky on cancellation.
The aggregate Android app owns those lifecycle gates.

The renderer requires the existing world fixture, world-reference and material
reference byte arrays. The caller retains their storage and `ANativeWindow`
for the serialized call; all EGL/GL and transient image/mesh objects belong
to that worker. `coh_interactive_world_json` returns an independently owned
immutable snapshot which the caller frees.

The host source proof executes 4,106 unchanged editor-look steps and compares
114,968 current camera components exactly with unchanged original camera
construction. Twenty malformed cases preserve every failed output, and both
reversed-pitch and disconnected-yaw negative controls fail. ASan/UBSan also
passes 16,007 checks through 8,000 accepted native-input/current-camera steps,
8,000 transactional nonfinite rejections, focus-clear release and null inputs.
Run it with:

```sh
python3 native-android/tools/interactive_world_fixture/check.py \
  --world native-android/integration-probe/app/src/main/assets/world.bin \
  --output results/integration-probe/interactive-world-host-proof.json --sanitize
```

Host source proof does not establish Android callbacks, GPU behavior or Thor
acceptance. Those require the combined app's measured device report.
