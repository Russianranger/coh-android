# Phase6 source and native mesh gate

The selected real source is `data/player_library/v_arachnos_wretch_sleeves.geo`, SHA256 `7d56d6fe65a1be2d02fe66e078b4c7b6a3998177dce47e8ac35b34a77baa413c`, v3 model0 `GEO_Sleeves_Wretch`. It supplies 116 real vertices, 198 triangles, one direct material and three local palette slots. Global identities in local order are `[9,5,7]`: `BONEID_LARMR`, `BONEID_COL_R`, `BONEID_UARMR`. Thirty-seven vertices have genuine nontrivial two-bone blends. This is a go for the bounded skinned-material GPU fixture, with the limitations below.

Original source remains unchanged, pinned by `upstream-lock.json` to `0b75ade0c801735e10c5798f641948a45cc50488`. The exact scalar delta function, full source and source weight/palette consumer files are independently hash-checked by `original_delta_check.py`. The task's stale local checkout was preserved; no reset was performed.

## Original decode and skinning contracts

| Requirement | Exact source location | Contract |
| --- | --- | --- |
| Model attributes | `Common/seq/anim.h:296-343`; `Game/src/render/model_cache.c:238-269` | Triangles decode as U32 triples, positions/normals as F32 triples, UV as F32 pairs. |
| Delta decoding | `Common/seq/anim.c:235-293` | Packed 2-bit code per scalar; controls precede one scale exponent, then variable-size deltas. Per-component previous values start at zero. |
| Delta codes | `anim.c:258-288` | c0=0; c1=U8-127; c2=LE U16-32767; c3=LE32 bit pattern. F32 c0-2 scale by `1.f/(1<<exponent)`; F32 c3 reinterprets raw bits, with no scale. Index deltas add `previous+delta+1`. |
| GPU UV upload | `model_cache.c:82-98,492`; `rt_model_cache.c:93` | Decoded UVs receive unconditional `v=1.f-v` before VBO upload. Legacy binds may additionally scale UV at `model_cache.c:111-149`; this fixture declares unit default bind scales and zero scrolling, with the full named trick resolver unqualified. |
| Packed streams | `anim.c:460-503` | zlib expansion occurs first when packsize is nonzero; unpacksize is the intermediate delta stream byte size, not the final F32/U32 output size. Weight/matrix bytes use raw `geoUnpack`, not delta. |
| Weight conversion | `model_cache.c:464-472` | One U8 per vertex is converted using exact source expression `weights[i] * 1.f / 255.f`; second weight is `1.f-weight0`. This is float division, not multiplication by a pre-rounded reciprocal. |
| Bone encoding | `anim.h:19,82-89`; `rt_bonedmodel.c:55-61` | MAX_OBJBONES=15. Disk BoneInfo is72 bytes in Win32: count,15global IDs,2pointer slots. Two U8 encoded palette indices per vertex are row offsets; local slot=encoded/3. Shader capacity16 is separate from the disk bound15. |
| Palette mapping | `renderbonedmodel.c:137-158` | Local slot j maps to `boneinfo->bone_ID[j]` in global `SeqGfxData.bpt`; socket offset from btt is transformed into final palette translation. |
| Shader rows | `rt_bonedmodel.c:200-229` | Three vec4 affine rows per local bone, each `{m[0][r],m[1][r],m[2][r],m[3][r]}`. |
| GPU skin blend | shader `functions.cgh:565-584`, `vp_master_vp.cg:123` | Lerp both deformed positions/normals using weights.y; normalize the blended normal. The original CPU fallback's DeformObject leaves its output normal unnormalized, so it is a separate contract. |

## Implemented bounded API

`material-probe/app/src/main/cpp/coh_mesh.{h,c}` parses canonical COHMESH1 assets generated offline from the real geometry. It does not reinterpret disk pointers or implement a full runtime .geo loader. It exposes a borrowed immutable view, checked vertex/index/global-bone getters and source-GPU-contract CPU deformation. The public core header from prior phases was not changed.

The canonical64-byte header has magicCOHMESH1 and14 little-endian U32 fields: version1,header64,vertex count,index count,bone count,stride48,vertex offset64,index offset,bone-ID offset,total bytes,flags0 and3reserved0. Offsets and file length must match contiguous canonical arrays exactly. Each48-byte vertex stores pos3/norm3/GPU-ready UV2/weights2 float32 followed by2U32 local palette slots; triangles are U32 and the final palette identity table uses U32 global BoneId values. The parser validates finite values, nonzero normals, weight range/sum, triangle and local/global bone references, unique palette IDs, supported bounds and all spans before publishing the view. Failed calls preserve their output.

`coh_mesh_skin_vertex` consumes12 floats per local bone (three affine rows). It uses weight.y to blend transformed positions and normals, then normalizes the blended normal. Palette parameters are controlled validation transforms. They do not represent original sequencer or animation playback.

## Executed proof

- The original scalar `uncompressDeltas` function ran under local C type and xcase macro shims on a Linux host. Its594 triangle indices,348 position scalars,348 normal scalars and232 UV scalars match the independent bounded Python decoder and canonical fixture byte for byte. The source float weight conversion and encoded-index division match232 weight scalars and232 local slots byte for byte. A separate source-exact GPU UV fixup also matches all232 uploaded UV scalars byte for byte, after validating raw delta output. The final canonical GPU-ready mesh SHA256 is `65e62ef126df267186b221c04a29f440019536f59171ddf68fa86728ca7a1661`.
- The separate native parser and CPU deformation passed36 primitive tests covering malformed headers, spans, truncation, finite values, weights, indices, palette IDs and a hand-computed two-bone rotation/translation and normalized-normal control.
- On the8020-byte real mesh,24,061 ASan/UBSan checks covered every exact-allocation truncation and two mutations at every byte offset, unaligned inputs, valid getters and identity skinning. Both sanitizers were active; leak detection was explicitly disabled because the local container's proc/ptrace constraints prevent LeakSanitizer. The parser itself allocates no memory.
- Both bind and controlled-palette poses compare all116positions/normals:696scalars per pose,1392total. Native C output and separately prepared scalar Python goldens agree with zero maximum absolute error on this host. The GPU gate allows a documented tolerance for shader/compiler rounding.

Receipts: `original-delta-check.json`, `native-mesh-check.json` in this folder. Reproducible repository scripts: `tools/material_fixture/original_delta_check.py` and `native_mesh_check.py`. CI instructions have been sent to the build owner; these host gates run before the APK build.

This qualifies one real v3 mesh's decode and controlled bone/material inputs. It does not qualify the full original Win32 Game loader, all .geo versions, Android GPU execution, original animation tracks, sequencer/bind-offset reconstruction, normal maps/tangents, complete costume assembly, gameplay, FPS or startup/zone performance. The next decision requires actual transform-feedback and framebuffer evidence from the separate material probe.
