# Standalone source RGBA32 upload and GPU lease

The new typed `coh_wr_gpu_upload_rgba32` entry consumes an actual immutable
`CohWrTexRgba32` owner through its real getter. It never casts a legacy opaque
texture owner. Identity, generation, whole-source SHA and every RGBA mip come
from that live owner. The source and caller inputs remain immutable through all
synchronous backend and cancellation callbacks.

`CohWrGpuReport.source_kind` distinguishes legacy DXT (0) from namespace RGBA32
(1). Both kinds expose identity, dimensions, levels, owned/RGBA bytes, source
aggregate peak and SHA through the shared report prefix needed by the existing
GPU lease. For kind1, legacy format, cached TexOpt flags, loader reservation and
source external bytes are invalid and zero only as storage. The kind-specific
report retains the selected row, declared input generation, original mip count,
skip count and full decoded-source aggregate reservation. `owner_bytes` measures
the actual GPU CPU owner for both entry points. The legacy function body changes
only its final report initializer; the new entry shares existing journal,
restore, context authentication and release functions without a legacy refactor.

The new entry enforces external reservation for the complete decoded owner's
recorded aggregate plus known caller/journal spans before any external callback
or GL call. It charges an additional 16KiB preparation reserve, actual GPU CPU
owner and GPU reservation. Provider, namespace or CPU retirement supplies no
historical budget subtraction. The standalone test declares 32MiB GPU external
and 48MiB lease external reservations; these are explicit assumptions covering
old/new overlaps, not driver measurements, process RSS or a global fit proof.
Known writable output/journal/input aliases against one another and exposed
source path/pixels refuse. Callers must also keep opaque source/backend/provider
storage disjoint and retain every source/view through the synchronous call.

The new test starts one real standalone private EGL pbuffer context and uses an
enforced finite three-file memory provider. Its complete declared fixture catalog
contains authentic grey plus a patterned RGBA32 control and a small legacy DXT1
control; it is not an original/current CLIENT catalog. Source holds guard every
read. The namespace acquires real loader pins; the RGBA32 owner copies independent
immutable pixels. The legacy smoke checks the existing typed path and kind0.
All provider bytes are overwritten and freed before the two RGBA32 uploads.
All CPU owners retire before immutable GPU lease resolve and readback.

Controls cover a short source reservation, known aliases, allocation failure,
every upload cancellation point including after final pixels/state restoration,
real partial-upload rollback with a retained failed-delete journal, actual
context quarantine, exact identity refusal, control-thread hold/drop/retire,
wrong-thread drain refusal, failed GL drain followed by retry, real deletion and
registry/context cleanup. Only executable-linked calloc blocks are tracked;
libc, driver and other allocation families remain outside that counter. No
LeakSanitizer or loaded-driver mapping proof is inferred.

The host checker reuses exact artifact12118720382 (12,308 bytes, SHA256
`87a999e6c1c003b96a9fa169ce11637b61eb696766517e063fafce73fdc39c24`). It extracts only
the authentic 894-byte grey body, independently creates the two explicit
controls, and derives an independent Python RGBA expectation for all 18 readbacks
(1,488 bytes). The compiled digest predicate admits only those exact three byte
strings; it is not a general SHA implementation. Patterned source channels and
alpha vary independently, including zero and opaque alpha. All generated input,
executable, readback and project bytes are bound before/after use. The host
checker binds the declared compiler file/version, five primary EGL/GLES headers
and declared library files; it does not claim a complete host system compiler,
standard-header or loaded-runtime closure. The Android driver records its
separate NDK toolchain dependency closure.

```sh
python native-android/engine/world-render-adapter/check_source_rgba32_gpu.py \
  --source-root /absolute/checkout --actual-defaults-zip /absolute/reused.zip \
  --host-headers /absolute/pinned-headers --host-egl /absolute/libEGL.so \
  --host-gles /absolute/libGL.so --output /absolute/fresh-proof --sanitize
```

The new driver `tests/run_source_rgba32_android.py build` accepts `--source-root`,
`--actual-defaults-zip`, `--ndk` and fresh `--output`; `execute` accepts
`--source-root`, `--build`, `--adb`, fresh `--output` and optional
`--timeout-seconds`. It builds nine actual production translation units plus
this new test for arm64-v8a and x86_64/API26. Root owns the new workflow and its
Android13 x86 execution. No APK, app-context adoption, old602 replay, original
Game namespace, default identity, sampler/material, actor, world or current
generation authority follows from this standalone path.
