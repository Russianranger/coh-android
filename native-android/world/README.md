# Source world and camera adapter

This bounded C11 adapter rebuilds one Atlas Park `modern_bench_2wide__mbench` branch from six original position/PYR records. Runtime input is the embedded 520-byte `COHWRI09` block. The native code composes all original ancestors at their actual world coordinates. No expected matrices or transformed vertices enter the runtime math API.

`Mat4` stores four columns of three binary32 floats, matching original `mathutil` storage. The final eye matrix is rebuilt by starting with the original camera view matrix and composing each selected group child in order. This retains the original `groupdrawinline.c` parent/local operation order and avoids replacing the source traversal with a shader that subtracts a camera from an already transformed, large world position. Source vertex positions and unnormalized normals enter that final model/view matrix directly; world positions are independently retained for transform feedback.

The original view convention transposes camera rotation, applies `rdrFixMat`'s X mirror, then transforms the negative camera position. Camera rotation uses original YPR order, including the original `RAD` expression's double-precision PI and binary32 reciprocal. Projection follows original perspective/frustum arithmetic and OpenGL homogeneous clip conventions. Six fixed PYR cameras use explicit controlled input positions, vertical FOV, aspect, near and far values. Above-4:3 gameplay FOV reduction, camera collision and gameplay controls remain outside this gate. A separate aspect override lets the window probe use its actual dimensions without changing the fixture cameras used for parity checks.

The camera positions are generated from the recovered source bench bounds, with six explicit pitch/yaw choices. This defines controlled test cameras rather than captured live gameplay cameras. Hair/actor rig logic and all accepted earlier phase code remain unchanged.

## Independent evidence

`tools/world_fixture/original_world_check.py` executes 15 unchanged, hash-pinned source function bodies: actual `degrees_parse`, original YPR and matrix functions, `gfxSetViewMat`, `rdrFixMat`, perspective and frustum functions. The token helper exposes a supplied float and a single destination slot; the camera inverse output is disabled; projection state is a local Mat44. The original `_WIN64` `sinf`/`cosf` implementation branch is selected for portable host and ARM64 qualification. This does not execute the original 32-bit x87 `fsincos` branch or the whole Windows client.

The independent Python reference uses mathematical row matrices and explicit binary32 rounding, without calling the native implementation. `COHWRF09` contains six local/world matrix pairs and six cases, each holding the view, projection, final source model/view, and 13 expected scalars per canonical vertex: world position, unnormalized eye normal, eye position and homogeneous clip position. Its exact size is 161,344 bytes, with 512 canonical vertices across two actual source material partitions. These expected values are used only by diagnostics and reference rendering.

`native_world_check.py` validates the immutable world container and all six cases at a fixed `1e-4` float tolerance. It requires rejection of named count/span/topology/float/rigid-weight violations and preserves output on parser failures. Its bounded sanitizer harness tests all 520 raw math truncations, scene truncations at fixed intervals, and 6,000 deterministic mutations under ASan and UBSan. LeakSanitizer is disabled because the host environment does not support its process inspection; this is explicit in the receipt.

## Limits

This is one source-selected root with 256 original GEO vertices, 188 triangles, and two material partitions. Each partition retains all 256 source vertices in the accepted canonical mesh adapter, so the GPU input has 512 vertices. The identity bone slot is a canonical-format adapter for static geometry, not evidence of an original world rig. The adapter does not implement full Atlas traversal, occlusion, original scene sorting, dynamic lighting, LOD transitions, physics, camera collision, input, networking or gameplay.
