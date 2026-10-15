# Original tray-art extension: Gates 34–36

Starting integration revision: `3c5da1d8cd501d778e270d395109d40666fbe37a`.
Original client source: `0b75ade0c801735e10c5798f641948a45cc50488`.
Original data identity: `d51533ec8e6a9cf726b9214968077a05fdcf19f3`.

The recovered support APK already implements the copied HUD, authentic Montreal
Heavy font, power/target/character/chat widgets, typed local intents and Android
input/IME bridge. This extension closes a concrete missing resource boundary:
its power tray had no original icon artwork. It adds genuine original tray ring
and slot-number decorations. These are **not** power-specific ability icons;
those remain unavailable and are not replaced with unrelated game imagery.
Existing mock power labels and gameplay behavior are retained.

The original `uiTray.c` loads `tray_ring_power.tga`, then numbers slots with
`slotNumber + 1`, wrapping the tenth to `0`. The eleven exact `.texture` members
are in the existing `coh-assets-v1.0.0` Base pack, and their identities match the
repository's recovered visual manifests. `pins.json` records selected members,
ZIP offsets/CRC, SHA256 and archive provenance. Whole remote archives were not
hashed locally. Initial recovery transferred 1,654,252 bounded HTTP206 bytes;
reproduction uses the pinned local records and avoids the inner central table.

Original artwork uses logical dimensions distinct from DDS storage: ring 38×38
inside 64×64, numerals 6/7×9 inside 8×16. Preparation applies the original
`rt_tex.c` BGRA→RGBA byte swap and the top-left logical crop used by
`atlasTexCopyPixData` / `borderize`. No padding is stretched into the icon.
Source hashes and independently compiled source bodies are recorded separately
from the asset hashes. The generated images total 8,224 RGBA bytes.

## Coordinator integration and ownership

Worker ownership is limited to `engine/ui/**`; no support-client, shared
renderer, JNI, workflow, accepted Session Client or live gates 25–27 file is
changed. The coordinator owns optional support-client build/GL wiring.

```sh
python native-android/engine/ui/gameplay/tray/prepare.py \
  --corpus /path/to/optional-local-tray-corpus --output /path/to/generated
```

Missing originals are recovered with exact bounded release ranges, stable ETag,
local ZIP identity, deflate bounds, size, CRC32 and SHA256 admission. All input
admission completes before generated outputs are written. The output contains
`support_tray.h`, eleven `.rgba` images and `tray-manifest.json`; do not commit
original or generated pixel bytes. Existing external assets are never modified.

1. Include generated `support_tray.h` in the coordinator's SupportUi GL owner.
   Its `coh_hud_tray_images[11]` table exposes `resource,width,height,rgba`.
   IDs are 100 for the ring and 101–110 for slots 1–9,0. Reserve these IDs in
   the resource resolver; original font resource 7 remains unchanged.
2. Upload each as `GL_RGBA8` / `GL_RGBA` / `GL_UNSIGNED_BYTE`, alignment 1,
   clamp-to-edge. Resolve with `red_coverage=0`. Upload once per current graphics
   generation; handles belong only to that current context.
3. Call `coh_hud_set_tray_decoration(hud,100,coh_hud_tray_numbers)` once after
   HUD initialization. Resources are copied. The setter retains gameplay
   snapshot, in-progress chat and existing focus. The optional decoration has
   no binding or focus flag, captures no input and emits no intent. Source
   numbering remains visible for disabled/recharging powers. Only populated
   slots draw decorations. Power-specific icon IDs in `CohHudPower` are retained.
4. Destroy current-context image textures with the other support UI resources;
   after actual context loss discard handles without GL calls, recreate/upload
   them for the next generation. The HUD retains only logical resource IDs,
   so Surface recreation preserves decoration and rejects stale drawlists.
5. Export prepared image SHA identities alongside existing font/asset identities.
   Additional draw submissions are 20 image quads for a ten-slot tray. This is
   a bounded diagnostic scene; no full-game FPS inference follows.

`CohHudState` and `CohHudIntent` are unchanged. The caller-owned `CohHud` arena
adds 44 resource-ID bytes and ten fixed widgets (74 total); rebuild all users
of its public struct header together. No allocations or GPU synchronization
are added to the runtime. The original source widget kernel is unchanged.

## Stable future GameState → HUD contract

A future session adapter copies its own authoritative values into `CohHudState`
on the HUD owner thread; it never lends entity/session pointers. Input produces
only copied `CohHudIntent` values. This extension does not dispatch commands.

| State owner supplies | HUD behavior / outgoing boundary |
|---|---|
| Revision and actor ID/name | Every local intent retains the snapshot revision and actor ID |
| Finite HP/absorb/endurance and maxima | Source-qualified color thresholds and bounded bars |
| Target ID/name and finite HP/max | Target panel, copied `COH_HUD_TARGET` intent |
| Up to ten unique power IDs, icon resource identities and recharge/enabled values | Ring/number decoration plus labels/icons; copied power ID/slot intent |
| Up to eight character choices and modal flag | Modal selection and copied character intent; scene replacement remains outside UI |
| Up to eight UTF-8 chat messages | Bounded display; committed user input becomes copied chat intent |
| Graphics generation, viewport and safe insets | Current-generation drawlist and safe touch conversion; no GL handles in gameplay snapshots |

The adapter is responsible for marshaling threads, rejecting obsolete revisions,
retaining gameplay IDs until intents are consumed and resolving assets to the
current graphics generation. UI bounds/queue errors remain explicit. A future
session owner decides whether an intent can be dispatched or must be discarded.

## Qualification and rollback

```sh
python native-android/engine/ui/gameplay/tray/check.py \
  --corpus /path/to/tray-corpus --source-root /path/to/original/ouroboros \
  --ndk /path/to/android-ndk-r28c --sanitize --output /tmp/tray-qualification.json
```

`qualification.json` distinguishes actual checks: 8,224 original-source and
independent Pillow byte comparisons; ten original slot-number comparisons;
18 malformed/corrupt input cases; 18,504 real Mesa GLES color-channel comparisons
across 33 image renders and three resource generations; zero GL errors. The
changed HUD is requalified with the original 30,759 source-color comparisons,
ASan/UBSan, copied intent/touch/modal/lifecycle tests and API26 ARM64 shared
library compilation. Generated original image bytes and API use are separately
ARM64 compiled. The GLES readbacks exist in the qualification test only.

Android emulator integration and physical Thor rendering of this extension
remain pending. Existing support APK qualification predates this extension;
its prior result is not relabeled as testing this code. Physical acceptance
requires actual support APK device reports and visual confirmation that source
ring/numbers are legible, controller/touch remain usable, chat survives Surface
recreation and asset/GL diagnostics contain no relevant errors.

Rollback is additive: clear decoration with zero resource IDs, remove the
coordinator's optional image upload/resolver and generated-header build hook,
and revert this extension commit if desired. Rebuild users of `CohHud` together.
Do not reset shared branch history or remove another agent's concurrent work.
