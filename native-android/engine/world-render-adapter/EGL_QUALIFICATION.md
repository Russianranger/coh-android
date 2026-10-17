# Actual standalone EGL/GLES texture qualification

This opt-in test owns private EGL pbuffers and ES3 contexts in a standalone
native executable. It cannot adopt the protected renderer context or publish a
material, actor or world. Production source adapter/CPU owner and all protected
renderer/assets/bridge files are unchanged. Rigid MIP_LINEAR admission remains
closed. Fixture geometry has no observed Atlas membership; the exact associated
texture remains a standalone asset fixture, not a live CLIENT material binding.

`tests/coh_gpu_egl_backend.c/.h` implements the narrow checked GLES operations
with actual EGL display/context/read+draw Surface and pthread verification before
every GL call. Tokens are emitted only after successful owned creation; a registry
retains exact Surface/context generations, including verified destruction. All owned context/Surface handles are exclusive to this backend and must never
be rebound or made current on another thread. Unbind checks verify NO_CONTEXT,
NO_SURFACE and NO_DISPLAY before destruction; exclusive ownership excludes EGL
deferred destruction caused by a context still current on another thread. One
backend owns the default EGL display per process. It is for this isolated probe,
not adoption into an application already sharing that display. An initialization
failure can leave a partial owner requiring explicit close, rather than forgetting
resources whose cleanup was not verified.

The backend owns its cleanup journal and quarantines **all** public GL operations
while pending, including release of another GPU owner. Only explicit cleanup
retry or actual context destruction can dispose of that journal. Test-only
callback fault controls produce a real-context candidate upload/deletion failure
and verify quarantine, then retry. They do not weaken the underlying uploader or
shipping authentication/material/runtime policy. Backend registry and serialized
owner-thread calls satisfy the uploader's external quarantine requirement within
this standalone process.

The probe runs183 controls. Three complete uploads each read back all9 actual
RGBA8 mip levels through FBOs, preserving texture/PBO/unpack and readback pack/FBO
state. A nondefault unpack PBO/row-length/skips fixture exercises real GL state
restoration. A real deliberately dirty GL error refuses upload. Wrong pthread,
old Surface and destroyed context views refuse. Surface-only recreation keeps the
same context and retires old names; full context recreation verifies old context
destruction before retiring its names. Actual numeric name reuse is reported as
an observation, not required. CPU storage/loader pins can retire after upload.
All2 contexts/3 surfaces and GPU owners must clean up before success.

Every byte from all27 readbacks must equal the authentic CPU mip chain. That chain
is independently checked by Pillow's DDS decoding, not just the upload callback.
Full packet1,048,572bytes SHA256:
`261155800f81fbd7645e9e34a7b4c4ed9b453e1596fe3e947162df24bf29e45c`.

## Host and Android packaging

Host dependencies: C11 compiler, OpenSSL/zlib development libraries, pthreads,
Pillow, EGL and GLES3-capable Mesa software libraries. Host EGL uses the explicit
`EGL_PLATFORM=surfaceless` setting. Header acquisition fetches five exact pinned
primary Khronos header bodies into scratch; no package installation is required.
The local test can link GL dispatch (`libGL.so.1`) for GLES symbols, while hosted
Linux can use `libGLESv2.so.2`. Actual GL version/renderer strings and library/header
hashes are retained before/after the run. These are declared dispatch-file
observations, not a verified loaded mapping or complete transitive-driver closure;
system Mesa/vendor drivers remain unsanitized even in source-ASan/UBSan runs. Host Linux software-driver execution is separate from Android.

```
python native-android/engine/world-render-adapter/acquire_sampler_texture.py --output /tmp/new-egl-input
python native-android/engine/world-render-adapter/acquire_egl_headers.py --output /tmp/new-egl-headers
python native-android/engine/world-render-adapter/prepare_gpu_egl.py --source-root . --actual-texture /tmp/new-egl-input/box-1.texture --host-headers /tmp/new-egl-headers --host-egl /lib/x86_64-linux-gnu/libEGL.so.1 --host-gles /lib/x86_64-linux-gnu/libGLESv2.so.2 --ndk /tmp/android-ndk-r28c --output out/new-egl
python native-android/engine/world-render-adapter/run_gpu_egl_android.py --source-root . --artifacts out/new-egl --validate-only --output out/new-egl-admission/receipt.json
python native-android/engine/world-render-adapter/run_gpu_egl_android.py --source-root . --artifacts out/new-egl --adb /path/to/adb --serial emulator-5554 --output out/new-egl-execution/receipt.json
```

Omit `--ndk` for host-only preparation; such output cannot pass Android admission.
The preparer binds exact clean source commit/tree and its own/new driver hashes,
prior source-model proof and unchanged production dependencies. It runs actual
host release/ASan/UBSan and finite-fixture builds, retaining stdout/stderr and exact
readback packets. Leak detection is disabled for the third-party driver path.

Android uses NDKr28c/API26 PIE executables for ARM64 and x86_64, linked with actual
platform EGL/GLESv3/zlib. The generated digest helper is an explicitly **finite
byte-equality fixture replay**, not general SHA256 or authentication code; host
replay must match real OpenSSL's qualified CPU chain and independent DDS oracle.
The exact transferred fixture/header and both binaries are hash-bound. Source
checks include the executing driver itself. Strict ELF64 ABI/interpreter bounds,
all host modes, exact native result maps and unchanged prior source proof admit
before device startup. Every consumed source/helper must be tracked and committed.
Postexecution readmission checks source/artifact stability. Declared platform
library files are hashed before/after, explicitly without loaded-mapping proof.
Fresh evidence directories prevent any previous logs or receipts being replaced. Android13/ABI and platform library hashes are observed.
Native execution has a120-second device kill bound and180-second host bound.
Actual execution is recorded only after validated native JSON; qualification also
requires exact device/pulled readback hashes and removal of the unique owned temp
directory. Failure and cleanup receipts remain exportable; no APK is built.

Current local evidence may qualify actual Linux EGL/GLES plus sanitizers; ARM64
build, Android13 execution and physical Thor qualification must each be recorded
only after those operations actually run. No encrypted login, server generation,
CLIENT shader/LOD selection or server-authoritative world claim follows.
