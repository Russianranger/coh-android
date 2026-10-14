# Source arithmetic and shader variants

The world point and normal helpers reproduce the pinned source C kernels with
separate products and left-associated sums. Affine positions and homogeneous clip
coordinates evaluate `((x*m0 + y*m1) + z*m2) + translation`; normals omit the final
translation. The six-link source eye hierarchy is still computed in native C.
Fixtures, independent references and the absolute `0.0001` comparison limit are
unchanged.

The original generic GLSL matrix multiply did not specify its dot-product
operation order. Thor recorded 88 world-position differences of one float ULP at
large world coordinates; source matrices, eye positions, normals and clip outputs
matched. A source-order shader avoids that evaluation ambiguity. The exact
instruction sequence executed on Adreno has not been captured.

`embed_world_shaders.py` embeds the reviewed body once and creates variants by
changing only its prologue. Every program links a vertex and fragment shader with
the same language version.

| Observed context capability | Vertex language | Arithmetic control |
| --- | --- | --- |
| GLES 3.2 or later | ESSL 3.20 | Core `precise` on every helper product, sum and result |
| GLES 3.1 and advertised `GL_EXT_gpu_shader5` | ESSL 3.10 | Required EXT extension, same `precise` helpers |
| GLES 3.1 and advertised `GL_OES_gpu_shader5` | ESSL 3.10 | Required OES extension, same `precise` helpers |
| Other GLES 3 contexts | ESSL 3.00 | Explicit source order; the existing actual GPU transform gate remains mandatory |

The compatibility path does not promise the optimization restrictions supplied by
`precise`. It qualifies only when all actual GPU outputs satisfy the unchanged
reference gate. No fallback substitutes reference geometry, source matrices or
CPU results for the measured GPU transform.

A precise caller does not automatically constrain arithmetic in a helper
function. Each helper therefore declares its own intermediate products, sums and
returned result as precise in the strict variants. This is also why a generic
matrix multiply was replaced by explicit component operations.

Primary specifications:

- [GLSL ES 3.20, section 4.9](https://registry.khronos.org/OpenGL/specs/es/3.2/GLSL_ES_Specification_3.20.html#the-precise-qualifier): precise scalar and vector operations preserve the stated order and prohibit compiler-generated multiply-add contraction; cross-function propagation has explicit limits.
- [EXT_gpu_shader5](https://registry.khronos.org/OpenGL/extensions/EXT/EXT_gpu_shader5.txt): adds precise to ESSL 3.10 and requires GLES 3.1; extension support must be advertised.
- [OES_gpu_shader5](https://registry.khronos.org/OpenGL/extensions/OES/OES_gpu_shader5.txt): corresponding OES functionality and GLES/ESSL requirements.

The fragment shader still implements the reviewed original MULTIPLY and
COLORBLEND_DUAL slices, controlled neutral lighting, fog and GREATER alpha test.
The diagnostic reference vertex shader and material quad driver retain their
comparison-only roles. The report records the selected language, precise status,
capability and mechanism for each fresh context.
