# Original CLIENT model material policy

`coh_wr_model_material_project` closes the model-level promotion and alpha
classification step between separately selected CLIENT texture bindings and
existing per-part rigid material admission. The original `modelResetFlags`
does more than classify each part independently: one ADDGLOW part can promote
other parts, source MODULATE becomes at least MULTIPLY, and FORCEOPAQUE can put
the merged blend on the first part. This module preserves that numerical policy
for a fresh initial model, including source flags, common blend and alpha/hidden/
fullbright results. It creates no material, namespace, texture pin or generation.

## Source and bounded input contract

The qualifier executes unchanged original `BlendMode`, `blendModeHasBump`,
`blendModeHasDualColor`, `promoteBlendMode`, `modelInitTrickNodeFromName`, CLIENT
`modelHasNorms`, `texNeedsAlphaSort`, `modelNeedsAlphaSort`, `allocModelTrick` and
`modelResetFlags`. The authoritative source dependencies are
`Game/src/render/model.c`, `Game/src/render/thread/rt_state.c` and `.h`,
`Common/seq/anim.c` and `.h`, `Common/seq/tricks.h`, `Game/src/render/tex.h`,
`texEnums.h`, `Game/src/render/thread/rt_init.h` and
`Game/src/graphics/gfxSettings.h`, under `upstream/ouroboros`. Complete file and
extracted function hashes are retained in the receipt. Twenty-five native flag
constants are independently compared with compiled original declarations.

The public input has 1..256 selected parts, original shader0..9 and 16-bit blend
bits, eleven original Basic layer presence/alpha bits, actual exact-white mask
identity, selected TexOpt scalars, postprocessed selected Trick scalars, bone and
normal presence, actual GFXF_BUMPMAPS capability and original OptionWater0..4.
Absent Trick/TexOpt inputs must have zero associated scalars. Unknown source flag
bits are preserved. Each name must have a NUL within256 readable bytes or supply
all256 readable bytes for bounded refusal; a short unterminated pointer is not a
valid input. Accepted names are nonempty printable ASCII shorter than256 bytes.
Borrowed inputs and names must stay immutable and disjoint from writable output.
All refusals preserve output. No input pointers are retained.

Original Model/TexBind/BasicTexture layout, initial selection, storage, allocation
and capability accesses are explicit qualification observers. These are source
policy comparisons, not original CLIENT ABI execution or proof that any supplied
binding belongs to the current model. The scope excludes prior mutable model
state, reload, texture swaps, custom overrides and draw-time grouping. In
particular, the first-part merged result does not independently qualify the
original whole-model drawing/splitting behavior.

## Historical and derived controls

Release, ASan and UBSan each pass 322,641 checks and 79,721 comparisons with the
unchanged original functions. The case set includes shader/capability/water/flag
combinations, every effective layer-alpha mask and exact-white branch, maximum
part count, name and scalar refusal, overlap and output preservation. The native
policy executes with zero heap allocations. Six altered production policies
must fail: global ADDGLOW promotion, common blend bits, first merged partition,
white-mask early return, fallback-only force opaque and MULTI variant intersection.
The actual standalone C object also links and executes through the public header
from a strict C++17 consumer, and exports only the public policy function.

The qualifier reuses the exact retained COHRES capture, root partition ledger,
`tricks.bin` and `seqstatebits.bin`; it verifies bounded complete input hashes
before use and again before writing the receipt. Historical source controls are:

| Input | Authentic fields used | Association boundary |
| --- | --- | --- |
| 3,083 root observations | Model name, ordered part count and raw SERVER Trick scalar fields | TexBind bindings, layer masks, normals and capabilities are explicitly derived controls |
| 8 historical TexOpt records | Native admitted postprocessed scalar projections | Independent controls, not selected model materials |
| 3,644 historical Trick records | Native admitted postprocessed scalar projections | Independent controls, not selected model Tricks |

The exact input hashes are in `qualification/model-material-policy-20261017/host.json`.
No GEO bodies are recaptured. The existing qualified 391-GEO/resource observations
still do not provide current CLIENT TexBind selection. The 79,721 source cases
must not be described as authentic current material associations.

Original-only warning allowances are `-Wno-unused-variable`,
`-Wno-parentheses` and `-Wno-error=pedantic`; they preserve the extracted original
code, including its signed enum declarations. The new native policy and actual
C++ consumer compile with strict warnings. Host release stack usage is 2,288
bytes for the public function and at most32 bytes per measured helper. The parent
aggregate must reserve borrowed input/name storage, output and4KiB own control
stack, plus compiler/runtime overhead. This is component accounting, not an
independent process memory allowance or an ARM64 stack measurement.

## Material authority still required

Source shader numbering differs from `CohMaterialFamily`: no cast is valid.
The result reports final shader families outside original MULTIPLY1, DUAL2 and
ADDGLOW3, and separately ORs nonzero blend bits. Even those three source families
need an explicit producer mapping and existing `CohWrRigidMaterial` admission.
`coh_wr_rigid.c` and `.h` are unchanged. Unsupported final families include
ALPHADETAIL4, BUMPMAP_MULTIPLY5, BUMPMAP_COLORBLEND_DUAL6, WATER7, MULTI8
(including BUILDING, SINGLE_MATERIAL, OLDTINT and reflection variants), and
SUNFLARE9. Remaining source flags, alpha cutout/tree splitting, subtractive
ordering, dynamic TexWord/UV state, reflection, visibility and lighting also
require their real producer/consumer semantics.

The immediate upstream dependency is actual old-style composite selection through
`texResetTrickBasedParametersComposite` and its `texFindVerify*`/Basic/TexOpt
dependencies. That producer needs the complete active Basic/composite inventories
and enumeration/overlay/duplicate order, actual filename/dirname and alias keys,
current import/cache generation and delayed membership, actual texture-swap and
locale search state, selected TexOpt membership, capability/fallback/water inputs,
and actual white/grey/invisible/black/dummy-bump/dynamic-cubemap/building-pattern
owners. A GEO partition basename, historical TexOpt miss, retained TexWord cache
or named white texture does not establish these inputs. Current TexBind selection,
effective render material, CLIENT/world generation, Android/GLES execution and
physical Thor acceptance remain unqualified.

```
python native-android/engine/world-render-adapter/check_model_material.py \
  --actual-cache /path/to/exact/tricks.bin \
  --actual-states /path/to/exact/seqstatebits.bin \
  --resources /path/to/exact/resources.cohres --output /tmp/FRESH-model-policy.json
```
