# Offline gameplay presentation continuation

Common starting revision: `58caf1d4ab3b39757190f194100ccbc697d57857`.
This module reuses the existing `CohUi`, source-font glyph callback, copied
`CohHudState` and typed HUD intent boundary. It adds five optional mobile panels
(character details, inventory, enhancements, missions and contacts), eight rows
per category, controller/touch inspection intents, source mission/contact text
colors and bounded local damage/healing text plus target-activation highlights.
All example character/item/task data are explicitly mock. This is preparation
for gates 34–38; it cannot qualify authoritative gameplay or close those gates.

Existing health/endurance, target, chat/IME, powers/cooldowns and original tray
artwork are reused unchanged. `CohHudState` and `CohHudIntent` remain unchanged.
`coh_ui_axis_step` factors the existing qualified analog hysteresis/repeat
algorithm behind a synchronous borrowed action callback. The existing
`coh_hud_axis_step` remains a compatible wrapper with the same checks and
semantics; the presentation panel uses that algorithm with a separate caller
navigation state. Original axis regression is rerun after this refactor.

## Integration contract

1. Compile `coh_presentation.c` alongside the existing `coh_ui.c`, `coh_hud.c`
   and `coh_hud_axis_navigation.c`; C11, `libm`, no new Android/GL dependency.
2. Initialize one caller-owned `CohPresentation` with the existing authentic
   font callback and context. Its fixed arena is 337,120 bytes on this host.
   All calls require one serialized owner; the support adapter's existing mutex
   can guard it. It retains no Android objects, GL handles or session pointers.
3. Copy `CohPresentationState` when relevant state changes. For the offline demo,
   `coh_presentation_mock_state(&state,&hud_state)` explicitly creates mock rows;
   then call `coh_presentation_set_state`. Avoid unnecessary per-frame snapshot
   revisions: a changed revision cancels an outstanding touch, preventing a
   press on one inventory revision from activating a remapped row. Old same-
   actor revisions are rejected. Actor changes clear old intents/effects/cues.
4. `coh_presentation_show(p,1,tab)` opens or cycles the five tabs. Route controller
   keys and touch to this panel exclusively while visible. B/cancel and Close
   hide it. `coh_presentation_axis` uses its own `CohHudAxisNavigation`; reset on
   panel ownership, focus, device or lifecycle changes. Sample/tick with the
   same monotonic clock; the shared algorithm bounds held repeats to one/frame.
5. Poll copied `CohPresentationIntent` values. They contain revision/actor/item
   IDs and distinguish inspect-item, inspect-enhancement, inspect-mission and
   inspect-contact. There is no consume/slot/delete/accept-task/network action.
6. Give the panel the same nonzero Surface generation, dimensions and safe
   insets as the HUD. `build` then `draws` returns a bounded ordinary `CohUiDraw`
   list for the existing GLES renderer's last pass. Resource IDs are optional
   original identities resolved by the caller; zero does not substitute art.
   Surface loss invalidates draws but retains copied panel/effect state.
7. A local power intent may produce `CohPresentationEvent` activation or signed
   impact (-damage/+healing). The event must match the copied actor, target and
   revision, have a strictly increasing nonzero sequence, and use a monotonic
   timestamp. Supply a caller-projected logical screen coordinate and copied
   emitter position. The module does not project entities or change health.
   Eight effects and sixteen cues are hard bounds; overload returns `COH_LIMIT`
   without advancing sequence/time or dropping earlier events.
8. `tick` updates display/fade. Explicit mobile durations are 400 ms target
   highlight and 1,500 ms impact text, rising forty logical pixels. These are
   new demonstration timing, not original full floaters behavior. Poll copied
   `CohPresentationCue` values outside audio callbacks: IDs for audio/animation
   are optional; zero explicitly means unavailable. No fabricated SFX/clip is
   played. A future adapter must resolve authenticated assets before playback.
9. Export `p.stats`, including fixed arena, queue limits, rejected/stale events,
   missing audio/animation bindings, effect/draw high water and Surface losses.
   These are bounded module counters, not whole-process memory or game FPS.

## Qualification and actual limits

`check.py --ndk PATH --source-root ORIGINAL_OUROBOROS --sanitize --output receipt.json`
compiles/runs host tests, a hash-pinned original `addFloatingDamage` source-body
oracle (72 RGB comparisons), four source mission/contact color checks, sixteen
malformed snapshot cases, twelve malformed event cases, stale/cross-actor
rejection, queue capacity, safe areas, touch revision cancellation, all tabs and
four inspect-intent types, and 64 Surface loss/recreation cycles. ASan/UBSan and
API26 ARM64/x86_64 links are distinct evidence. Direct allocator imports are
absent from the shared libraries; libc internals and entire Android process
allocation behavior are not inferred. Runtime owns no heap and performs no IO,
resource load, texture upload, GPU readback or GPU wait.

The parent support client owns integrated Android emulator and physical Thor
qualification. This worker's standalone compilation is not emulator execution.
GLES screenshot checks are separate host software-renderer evidence. Actual
Thor acceptance remains pending user reports. Full original UI frame slicing,
rich chat/SMF, inventory actions, powers icon closure, projectile/particle FX,
real combat and precise original floater trajectories remain open.

`asset-gaps.json` records a newer manifest discovery: original health/endurance/
damage inspiration icons exist with exact hashes and provenance, but were not
recovered here after the single source range returned HTTP403 under the current
network policy. Power-specific Brawl/Sprint/Archery icons remain absent from the
recovered repair/sweep file inventories. Existing font/tray art can still render;
new panel icons are explicitly unset. Original assets are never committed.

Rollback: remove the optional support adapter panel/effect calls and source-list
entry, then revert only this isolated module/refactor commit if desired. The
original HUD axis API remains available. Do not reset the branch or alter any
Session Client/Combined Client/server/live-session files.

## Reproduce visual composition evidence

`gles_check.py --ndk PATH --font-dir PREPARED_HEADERS --font-manifest atlas.json
--output OUTPUT_DIR` consumes the coordinator's existing generated
`support_font.h`, checks its 32,768 alpha bytes against the original-font
preparation manifest, and renders five 1280×720 actual Mesa GLES3 frames. It
writes Details/Inventory/Enhancements/Missions/Contacts PNGs plus a receipt.
`qualification-gles.json` records zero GL errors, exact original font/atlas
identities, image checksums and visible source health/mission/contact color
pixels. Host screenshots were inspected for panel/HUD overlap and readability.
The preview uses the existing compact HUD without optional original tray-ring
resources; the integrated support application retains its existing rings.
No character/world scene or real game performance is inferred from this UI-only
image. GPU readback exists only in this test program, never the runtime module.
