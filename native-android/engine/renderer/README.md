# Gate 24: incremental native renderer

**Status: implemented and host qualified for the scoped low-profile families below. Android ARM64 build qualified, Android execution/emulator and physical Thor qualification pending. Gate 24 as a complete broader renderer is not closed.** This opt-in module has no JNI, APK, existing renderer, Session Client, Gradle or CI dependency. Gates 19–21 and older accepted renderers remain untouched.

## Public boundary

`coh_renderer.h` is a C99 reusable renderer API, depending only on `../coh_contracts.h` and libm. It accepts arbitrary immutable indexed `CohRenderVertex`/uint32 geometry, explicit material/texture/sampler state, source-composed column-major model-view/projection and separate light/fog constants. There are no asset names or per-mesh rendering branches. The optional concrete `coh_renderer_gles.h` backend requires GLES3 and links GLESv3 on Android.

All calls are on the GL owner thread. Vertex/index spans and texture handles stay alive and unchanged until flush returns. Geometry is not retained afterward. Material/uniform/matrix descriptors are copied on submission. Texture uploads, asset references and cancellation producers belong to the caller. The asset loader bridge belongs to the coordinator: enumerate each decoded model's material partitions, resolve original texture identities, prepare source VBO UVs (`V=1-diskV`) once, upload DDS RGBA/mips, then submit through this API. The loader must not flip UVs twice or substitute serialized 32-bit offsets for pointers.

```c
CohRenderBackend backend;
CohGlesRenderer *gles = NULL;
CohRenderer *renderer = NULL;
CohRendererConfig limits = coh_renderer_default_config();
coh_renderer_gles_create(limits.max_vertices_per_draw,
                        limits.max_indices_per_draw, &gles, &backend);
coh_renderer_create(&limits, &backend, &renderer);
/* Assemble caller-owned geometry, matrices, resolved textures and material. */
coh_renderer_begin(renderer, 0);
coh_renderer_submit(renderer, &draw);
coh_renderer_flush(renderer, cancellation);
/* Producer has stopped; destroy renderer before its GLES backend. */
coh_renderer_destroy(renderer);
coh_renderer_gles_destroy(gles, 1);
```

Check every returned `CohStatus`. An invalid submit changes only the rejection counter; previously queued draws remain valid. Flush stops on cancellation, compiler, binding or draw failure and drops all pending borrowed spans. Earlier draws may already have executed. It never retries partial frames. Backend callbacks consume data synchronously and never retain a draw. Borrowed pointers are trusted C spans; the module validates declared bounds/content, not the inaccessible allocation length behind a caller pointer.

## Source contract and shader audit

The source pin manifest records ten original source files, checked before qualification. The exact original Cg sources are read from `upstream/i24/data/shaders/cgfx`, with material/state/UV setup audited in Ouroboros. Original Cg compiler output or original driver captures are not claimed.

| Family/feature | Implemented source semantics | Qualification |
|---|---|---|
| MULTIPLY | base × blend; RGB × 8 × vertex lighting; alpha = base.a × blend.a × const0.a | Original declared Signmetal + grey pair, accepted independent world reference, actual Mesa GLES |
| COLORBLEND_DUAL | dual RGB chooses const1→const0; base alpha masks tint→white; RGB × base × 4 × lighting; alpha = dual.a × const0.a | Original declared modern_bench + white pair, accepted independent world reference, actual Mesa GLES |
| ADDGLOW | `calc_old_tint`; RGB × 4 × lighting; source `floor(uv0)/128 + glow_params.yw` mask; strict mask.red < threshold adds glow; alpha = const0.a | Source equations and actual Mesa GLES with explicitly controlled texture pairing/masks; authentic declared ADDGLOW asset pairing pending |
| Vertex lighting | VERT_COLOR, DIFFUSE and FF_LIT_GL, including source specular behavior (no NdotL gate and no specular clamp) | Independent scalar + actual transform feedback on authentic geometry |
| Fog/coverage | Source radial fog coordinate, linear fog factor, RGB-only fog; strict alpha > reference | Reference FBO and independent scalar comparisons |
| State | Source CW/BACK defaults, LEQUAL, explicit depth writes, opaque/straight-alpha/additive blend, repeat/clamp/mirror and nearest/linear/mip-linear samplers | Binding/cache host checks and actual material alpha GPU cases; broad depth/cull/mip visual qualification remains pending |

`vp_master_vp.cg` supplies model-view, projection and normal conventions. The renderer does not replace the source normal transform with an inverse transpose. Normals are normalized for the selected original vertex-shader branches. This does not alter the separately accepted rigid-world CPU/source-matrix adapter or Huge skinning path. General skeletal geometry still uses that accepted adapter until a coordinator-owned bridge is qualified.

The transform expressions explicitly retain `((x*m0+y*m1)+z*m2)+translation`. GLES3.2 uses ESSL3.20 core `precise`; GLES3.0 falls back to explicit source order and must pass actual transform-feedback admission on each target. This module does not yet implement the accepted renderer's optional GLES3.1 EXT/OES precise selector. No parity is inferred from a compile result alone.

Shader variants are deterministic source files plus a generated header (`embed_shaders.py --check`). The renderer lazily compiles three material-family programs with a bounded 1–3 entry LRU. GLSL linking caches uniform locations. Program deletion requires no GL fence/readback. Native drivers may perform compilation work; no pipeline binaries are persisted across driver versions.

## Batching, allocation and diagnostics

Draw count, per-draw vertex/index count and shader cache capacity are configured at creation. The core makes three allocations on create and none during submit/flush. Constant-storage heapsort groups only contiguous opaque runs by shader/state/texture key; a sequence tie-breaker preserves equal-key order. It never moves opaque draws across a translucent barrier. **The caller must submit translucent geometry back to front.** Compatible draws reuse bound state; geometry remains separate indexed draw calls.

The GLES adapter owns one fixed-capacity streaming VBO, one IBO, VAO and three samplers. Its buffer budget is `max_vertices*sizeof(CohRenderVertex) + max_indices*4`; default maximum buffers are 4,456,448 bytes. The first implementation uses BufferSubData uploads each draw. Driver allocations/stalls and GPU in-flight storage are outside these core counters. Immutable GPU mesh caching, instance batching and measured Adreno throughput are follow-up work. No claim of full-game FPS or zero GPU-driver allocation is made.

`coh_renderer_stats` reports owned CPU bytes, currently borrowed bytes, high-water draws, submissions, successful draws, rejection/cancellation counts, compilations/hits/evictions and pipeline binds. Shader logs are bounded to 1024 bytes in the GLES adapter. Use the application's GL debug/error-reporting path for asynchronous driver diagnostics; the adapter avoids per-draw glGetError/glFinish/readback. Tests use readback only for qualification.

## Lifecycle and rollback

Both core and GLES creation require an initially NULL output owner. Recreating
an occupied output previously replaced its pointer and lost the original CPU/GL
ownership. The occupied-output check now refuses with `COH_STATE` before any
allocation, backend callback or GL call; GLES also preserves the supplied
backend descriptor. The caller may continue using or explicitly destroy the
original owner. Reinitialization uses the existing Surface-loss/recreate APIs.

On Surface/context loss, stop submissions, call `coh_renderer_surface_lost(renderer, new_generation, context_alive)` and `coh_renderer_gles_recreate(gles, context_alive)`. With a lost context, stale GPU names are dropped without deleting unrelated names in the replacement context. Reupload caller-owned textures and submit with the new generation. Logical assets/animation/UI state remain outside this renderer. Destroy the core first, then the GLES backend; null destroy arguments are safe. Do not reuse a freed pointer.

The module is not in any accepted APK path. Integration order is loader-resolved geometry/material bridge, isolated Android GLES pass, cross-module regression, consolidated test APK, emulator qualification, then Thor acceptance. The coordinator must restore GL state explicitly when alternating with an older renderer; no interleaved callback or external GL state mutation is supported inside a flush. UI can use a separate orthographic pass, but scissor/clipped UI rendering needs an adapter extension.

Rollback before integration means removing the opt-in target/adapter. After integration use an additive revert of this module's integration commits; preserve source history and accepted APKs/receipts. Never reset `native-android` or modify gates 19–21 in order to roll this module back.

## Reproduce qualification

```sh
python3 native-android/engine/renderer/check.py \
  --output /tmp/coh-renderer-host.json \
  --source-root /path/to/full/original/repo \
  --corpus /path/to/accepted/world/assets \
  --ndk /path/to/android-ndk-r28c --sanitize
```

The corpus directory contains accepted `world.bin`, `world-fixture.json` and `material-reference.bin`. Their existing SHA256s, mesh and decoded texture hashes are checked; no assets are embedded here. `--source-root` points at the full source repository with `upstream/i24` and `upstream/ouroboros`. Host Mesa GLES checks use libEGL.so.1/libGL.so.1 and GLES headers isolated from the Android sysroot. All temporary native binaries are outside the repository.

The checked-in receipt records strict C99 host tests, 6,000 binary64 independent scalar comparisons, negative/failure/lifecycle/cache tests, 20,000 sustained frames with constant module-owned storage, ASan/UBSan, actual software Mesa GLES FBO comparisons and both ESSL3.00/3.20 transform-feedback profiles. It also records real EGL context destruction/recreation and a successful NDK ARM64 API26 shared-library build. LeakSanitizer cannot inspect `/proc` tasks in this traced runtime and is explicitly **not** qualified. Re-run LSan in a compatible host environment.

Remaining acceptance: Android emulator execution, physical Thor/Adreno source/GPU comparison and lifecycle tests; dynamic loader-to-renderer integration; authentic declared ADDGLOW pairing; general skeletal rendering bridge; original full mip/LOD/material catalog; HQ/bump/normal-mapping, cubemaps/reflection, shadows, MULTI, water, particles and CgFX postprocessing. Shader families absent from this API are unsupported and must be rejected by the material resolver rather than silently mapped to one of these families.

The narrow `check_create_ownership.py` check needs the five existing pinned
Khronos headers and actual host EGL/GLES dispatch library files. It executes only
the occupied-owner regression in release/ASan/UBSan, verifies unchanged original
owners/backend/GL bindings and an unconsumed deliberate GL error, then renders
through the retained owners before and after actual GLES resource recreation.
It removes each refusal independently to prove the regression test fails.
Project-owned allocation/free counts must balance. These controls use an explicit
triangle and two one-pixel textures; they do not requalify original materials,
server state, Android, driver allocations, process RSS or the broader renderer.

```sh
python3 native-android/engine/renderer/check_create_ownership.py \
  --source-root . --host-headers /absolute/pinned-khronos-headers \
  --host-egl /lib/x86_64-linux-gnu/libEGL.so.1 \
  --host-gles /lib/x86_64-linux-gnu/libGL.so.1 \
  --output /absolute/fresh-owner-qualification
```
