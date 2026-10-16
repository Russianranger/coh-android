# Gate31 native appearance assembly

The additive native GEO conversion and CPU render bridge is described separately
in [RENDER-BRIDGE.md](RENDER-BRIDGE.md). It extends this assembly without changing
the original qualification receipt or claiming complete-character acceptance.

This additive C11 library converts parsed original costume/body-part data into
bounded, caller-owned geometry, texture, socket and color draw requests. It is
independent of a game session. The accepted Huge/Wretch rig, morph, sampler,
locomotion, rendering, JNI, network, build workflows and APKs are unchanged.

`coh_appearance.h` is the public interface. The coordinator may compile
`coh_appearance.c` alone for assembly or add `coh_appearance_adapters.c` when the
existing GEO and character kernels are linked. `character/coh_character.c`
already includes the animation translation unit; do not link a second copy.

## Implemented behavior

- Nine original numeric body descriptors, explicit ent-type/costume-prefix
  overrides, source geometry and texture prefixes, and required Villain overrides.
- Source `BodyPart` data and bone IDs, up to 60 costume parts and 120 paired draws.
  `UINT32_MAX` in first socket preserves unknown source-bodypart no-op semantics.
- Automatic `prefix_BaseName.GEO_GeoName[R/L]_choice` identity and explicit
  `file.geo/model` identities; paired wildcard substitution and asymmetric
  LArm/LLeg selection. No model mirroring or synthetic fallback is introduced.
- Original `NONE`, explicit `!texture`, two-pass `01a`/`01B`, single-texture
  suffix, existence-dependent gender prefixes, and source SKIN color routing.
  Four authored colors survive; source first/second effective colors are emitted.
- Chest-linked candidate selection through a synchronous existence probe.
  Null probe means no inventory override exists. Mock inventories in host tests
  are labeled; they do not prove those textures exist in a pack.
- Original virtual paths plus generation, caller-owned names/colors, bounded
  GEO identity lookup ignoring source `__trick` suffix case-insensitively.
- Optional palettes reuse unchanged neutral-rig or Huge morph kernels and
  preserve inverse bind, socket transform order and nonpropagating bone scales.

The output is an appearance **delta**, not an implicitly emptied actor: absent or
unknown parts remain the actor owner's responsibility. `dont_clear` is carried
by the part definition for that owner; explicitly supplied `NONE` is emitted.
GEO model lookup is control-thread work: the reused variable-record reader
walks records, so callers should cache the selected model index after resolution.
No per-frame model-name scans are intended.
No global actor, shader, file cache, worker thread or network packet is created.
All borrowed inputs and probes are synchronous. The asset/rig owner pins decoded
views; the GL owner uploads resources separately. A Surface generation change
invalidates GPU resources without changing this logical appearance.

## Bounds and failure behavior

One fixed `CohAppearanceWorkspace` is 157,440 bytes; each draw is 1,312 bytes on the
qualified host/ARM64 ABI. It holds the largest source costume transaction outside
the stack. Reuse one arena per control thread rather than per actor. Assembly performs zero heap allocations, no decoding, no GL calls and
no blocking operations except any caller-defined probe/cancellation callback.
Output/count/diagnostics stay unchanged on failure; workspace may change. Avoid
aliasing workspace, output, input definitions, strings and request objects.
Callbacks must be side-effect-free and used only on a control/asset thread.
Input text is bounded printable ASCII because this source identity scope uses
ASCII names, with unsupported path forms rejected. Runtime UI text is unrelated.

## Qualification

`check.py --output evidence.json --source-root /full/checkout --sanitize
--corpus-root /verified/corpus --ndk /android-ndk-r28c` builds strict host C,
executes independently extracted original costume functions, checks source/data
hashes, compares actual GEO streams against original `uncompressDeltas`, compares
the adapter to the accepted Wretch palette, runs ASan/UBSan and links Android
ARM64 API26 with undefined-symbol rejection. Original source retains its own
historic unbounded `sprintf` warnings in the oracle; only short authentic and
controlled valid inputs reach it. Malformed inputs reach the hardened native
module under sanitizers, not the legacy oracle.

`acquire.py --output /corpus` recovers seven real Male/Female/Huge original GEO
files through strict bounded release ranges, CRC and independent manifest SHA.
It never downloads the full 1.63 GB Base archive. `corpus-pins.json` includes the
original PIGG provenance. The seven files total 1,638,884 bytes. Initial source-pin
creation verified the full 48,591,999-byte Base manifest SHA from accepted pins;
full outer and inner archive hashes were not locally verified.

The four authored source costumes are Aaron Thiery (Male), BurningBody Talon
(Female), ShadowSpider (Huge), and the accepted Wretch. Every requested geometry,
texture, socket and effective color is compared to executed source functions with
three independent mock existence inventories. The separate real GEO proof loads
and decodes actual body resources without claiming a newly rendered full model.

## Complete neutral Male continuation

The 2026-10-16 continuation in [ACTOR-PREVIEW.md](ACTOR-PREVIEW.md) resolves a complete neutral Male source-menu costume using the tracked avatar supplement, seven original texture selections and a matching source-qualified rig. It adds an atomic whole-actor adapter and opt-in GLES preview, host/source/sanitizer/ARM64 qualification, real host GLES context-recovery evidence and deterministic package preparation. It does not complete Female/Huge rendering or full Gate31. Historical receipts and accepted Wretch behavior are preserved.

## Current limits

Gate31 remains open. Full Male/Female/Huge model assembly still needs geometry
and texture closure, qualified matching skeletons and body morphology, original
material variants and Android GPU/device comparison. Existing morph parser and
sampler explicitly support Huge only; this library returns `COH_UNSUPPORTED`
for attaching another body to that morph. Neutral palettes are allowed only for
already-qualified neutral rigs. A fresh model definition is not a new rig proof.

The Base pack audit found `v_male_pants.geo` and `v_male_shirt.geo` without the
`male_pants.geo`/`male_shirt.geo` generated by some authored NPC definitions. The
tracked avatar supplement now supplies these exact Male resources; the new
preview authenticates them instead of substituting V-prefixed geometry. Missing geometry is explicit `COH_NOT_FOUND`; original LArm disappearance
can be decided by the actor owner following the existing qualified rule.
Cloth/capes, FX attachments, arbitrary malformed text parsing and entitlement
validation are not implemented. The fixture importer is test tooling, not the
production `.nd`/`.bp` parser. No emulator or physical Thor claim is made here.

## Integration and rollback

1. Add the optional library to the coordinator-owned harness; retain existing
   accepted actor as its own slot. Do not replace its source files or APK.
2. Feed parsed costume/bodypart records, immutable generation-aware resources,
   a matching rig and a material/texture inventory probe. Check each status.
3. Resolve each non-clear path using the existing bounded asset loader, select
   its model with `coh_appearance_geo_model`, and form the accepted palette with
   `coh_appearance_palette`. Retain assets through the draw and release outside GL.
4. Keep CPU source/reference checks distinct from GPU/device qualification.

All files belong to `engine/appearance/`; no other source changes are necessary.
Rollback is removal of the opt-in target/adapter calls or a conventional revert
of this module commit. Previously qualified APK 0.3.0 and its checksum are unchanged.
