# Presentation renderer identity

Presentation previously accepted a second `CohRenderer` with the same numeric
Surface generation. A successful wrong-renderer Stop could release active
publication/resource leases after abandoning only that second renderer. The
existing exclusive-renderer contract required the caller to avoid this mistake
but did not reject it.

The first successful resume, pause or Surface-loss operation now records the
actual borrowed renderer pointer. Every subsequent GL-facing presentation call
refuses a different pointer before backend calls, binding invalidation, resource
retirement, publication changes or result writes. Failed initial admission does
not record a pointer. Correct renderer pause/resume, Surface recreation, active
frame rendering and Stop retain their existing behavior. The additional pointer
is included in the existing `sizeof` aggregate allocation/reservation.

This guard does not retain or own the renderer. The caller must keep the same
renderer alive through Stop and cannot destroy/recreate it at a reused address.
A pointer check cannot authenticate a physical EGL display, context, Surface or
pthread; the separate application EGL producer contract remains pending. No
Combined/JNI/renderer-core/resource module, accepted APK or shipping activation
changes here.

The focused checker runs only the new test with the actual existing generic
renderer and deterministic backend callbacks: release, ASan and UBSan each
58 checks, six draw submissions, one resource hold and one drop. Five mutations
independently remove the guard from resume, pause, render, Surface loss and Stop;
each is rejected. The test verifies unchanged second-renderer/backend state,
result bytes, active resource leases and CPU budget after wrong-owner calls,
then exercises correct rendering and cleanup. CPU input is explicitly fixture
scope. No GLES/Android/Thor execution, current CLIENT material, actor/world
authority, global memory fit or frame pacing is established. Accepted historical
GPU evidence is reused within its original scope and was not replayed.

Run `python3 native-android/engine/world-render-adapter/check_presentation_renderer_identity.py --output /path/to/new-evidence`.
