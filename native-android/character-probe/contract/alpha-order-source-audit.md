# Original GEO character alpha and depth behavior

The actual `Hair_Wretch_Mask` contains partial alpha values from 0 through 216.
That establishes the need to preserve fragment alpha, blending and the strict
`GL_GREATER,0` alpha test. It does **not** establish that the original client puts
this costume mesh in a later transparent queue or disables its depth writes.

The immutable primary source gives the following control flow:

| Operation | Original source | Observed behavior |
| --- | --- | --- |
| General texture alpha classification | `Game/src/render/model.c:76–79` | `COLORBLEND_DUAL` classifies alpha using the generic texture's `TEX_ALPHA` flag. |
| GEO character special case | `model.c:142–145,259–265` | `GEO_` geometry sets `colorblend_alpha_hack=1` and skips `modelNeedsAlphaSort`. The source comment explicitly says this geometry never alpha sorts without a specific trick. |
| Costume override alpha classification | `rendertree.c:322–355` | `gfxTreeSetCustomTextures` stores both overrides, but its alpha-sort flag logic is disabled by `if (0 && gfx_node->model)` at line 334. |
| Skinned queue choice | `rendertree.c:1257–1276` | Fully opaque actor alpha 255 goes into `SORT_BY_TYPE` unless the existing node/model flags require alpha sorting. |
| Draw pass order | `graphics/gfx.c:1153–1158,1209–1235` | Opaque pass precedes the distance-sorted alpha pass. This does not itself modify the depth write mask. |
| Hair and Neck model trick | `i24/data/tricks/hero_bump.txt:1–3` | `Collar2x` declares `DoubleSided`; it does not declare `ForceAlphaSort` or `NoZWrite`. |
| Depth writes disabled by a model trick | `render/thread/rt_tricks.c:313–316` | Only `TRICK_NOZWRITE` calls `WCW_DepthMask(0)` in this path. |
| Depth writes restored | `rt_tricks.c:546–549` | The matching `TRICK_NOZWRITE` undo calls `WCW_DepthMask(1)`. |
| Driver call | `render/thread/wcw_statemgmt.c:1755–1760` | `WCW_DepthMask(mask)` caches and calls `glDepthMask(mask)`. |
| Default alpha test | `render/thread/rt_state.c:1103` | The renderer selects strict `glAlphaFunc(GL_GREATER,0)`. |

`render/thread/rt_bonedmodel.c` receives the copied model trick, applies
`gfxNodeTricks`, draws the original indexed faces through `drawLoopBoned`, and
undoes the trick. This path contains no automatic alpha-specific depth-write
disable. The retained `GEO_Hair_Jack__Collar2x` suffix alone therefore provides
double-sided rendering while leaving source depth writes enabled.

For this isolated actor the diagnostic may explicitly choose a deterministic
part order to make comparisons reproducible. It must disclose that order and
must not call alpha-last/depth-writes-disabled behavior an original-client
reconstruction based only on the mask's partial alpha. Full source type-sort
ordering across scene materials and original-client runtime pixel captures
remain outside this actor assembly gate.
