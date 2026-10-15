# Native gameplay HUD extension (Gates 34–36)

This opt-in module extends the previously host-qualified `coh_ui` without changing it. It does not modify the Session Client, launcher, networking, authentication, protocol formats, accepted APK, root build files or CI. It consumes copied local gameplay snapshots and emits local intent records. A future session adapter chooses whether and how to act on them.

Implemented components: health/absorb and endurance bars; ten power slots with readiness/recharge and generic icon resources; target name/health; eight bounded chat/message lines and committed UTF-8 chat input; an eight-character selection window; touch, controller focus/navigation, keyboard and Android IME adapters. Character selection is modal to these HUD controls. No live game-state behavior is implied by the mock demonstration.

| Scope | Status |
|---|---|
| Existing `coh_ui` implementation and tests | Reused, source unchanged |
| HUD, copied bindings, intent queue, safe areas, lifecycle, Android event adapters | Implemented; host + ASan/UBSan qualified in documented scope |
| Original health/endurance colors and primary tray width | 30,759 original C oracle comparisons pass; ten-slot definition pinned |
| Original Montreal Heavy font | Actual game font recovered; 95 ASCII glyphs prepared using source NOHINT flags, independently checked advances |
| Last-pass GLES3 backend | ARM64 linked; actual Mesa software GLES shader/pixel/scissor/batching tests pass |
| Android emulator | Coordinator integration/qualification pending |
| Physical AYN Thor | Pending combined APK test; no acceptance inferred from compilation |
| Full original CoH UI appearance, gameplay and complete Gates 34–36 | Open |

Public API is in `../coh_hud.h`. `CohHud` is a fixed caller arena (340,048 bytes on this 64-bit host), including retained `CohUi` storage; a snapshot is 3,120 bytes. It constructs 64 widgets. Tests observe 177 draw commands at high water and bounded 32-intent backpressure. The GLES backend is a separate 58,472-byte caller arena, with 128-quad batches and a fixed resource-resolution table. Reported CPU timings are host snapshot/drawlist timings only, with no GPU or full-game FPS claim.

## Integration

1. Compile unchanged `coh_ui.c`, additive `coh_hud.c`, `gameplay/coh_hud_android.c`, `coh_hud_atlas.c`, `coh_hud_quad.c`, `coh_hud_gles.c`. Link `m` and `GLESv3` on Android. All names are additive.
2. Choose one owner thread. The intended Android harness owns HUD and GL objects on its GL thread and queues touch, controller, IME and copied game-state updates from Android callbacks. Concurrent unsynchronized calls are unsupported. No JNI/Activity/session pointers are stored in this module.
3. Prepare a bounded font atlas outside the frame path. For the recovered original font:

   ```sh
   python native-android/engine/ui/gameplay/make_atlas.py --font /path/to/assets/fonts/mont_hvbold.ttf --output /tmp/coh-hud-atlas
   ```

   The generator uses host FreeType's no-hint normal grayscale path, matching the audited original font policy for `mont_hvbold`. It emits `atlas.h`, `atlas.alpha`, `atlas.png` and `atlas.json`. The default is a 256×128, 32 KiB alpha atlas; no TTF or glyph bitmap is committed into the repository. Include `atlas.h` from the harness and validate `coh_hud_font` before use. Unsupported Unicode glyphs use an explicitly configured `?` fallback, preserving committed text and UTF-8 scalar backspace. This fallback is not a localized-font implementation.
4. Upload `coh_hud_font_alpha` once per graphics context with `glTexImage2D(... GL_R8, 256, 128, ..., GL_RED, GL_UNSIGNED_BYTE, ...)`, `GL_UNPACK_ALIGNMENT=1`, clamp-to-edge and linear or nearest filtering. `CohHudTextureFn` maps resource 7 to this current-context texture with `red_coverage=1`. Normal RGBA images set `red_coverage=0`. Resources are caller-owned original asset identities, not persistent GL handles.
5. Call `coh_hud_init(&hud,coh_hud_atlas_glyph,&coh_hud_font)`, `coh_hud_set_state(&hud,&snapshot)`, then `coh_hud_surface(&hud,generation,width,height,safeInsets)`. Insets are actual surface pixels. Logical 1024×768 content fits and centers inside the safe area; draw output and touch conversion include its offset. `coh_hud_set_skin` optionally supplies original frame/font resource IDs; the current backend stretches frame images, without the original segmented frame decoration.
6. After updates call `coh_hud_build`, obtain `coh_hud_draws(&hud,generation,&count)`, then draw last with `coh_hud_gles_draw`. Start `CohHudGles` zeroed and create it on the current GLES3 context. The backend validates the complete drawlist and resources before drawing, preserves order, batches only contiguous equal texture/clip/mode commands and performs no readback or synchronization waits. Observe the documented GL state left by this final pass and establish scene state before the next scene draw.
7. `coh_hud_android_touch` accepts masked MotionEvent actions and pointer IDs. `coh_hud_android_key` maps D-pad, A/B, L1/R1, Tab/Shift-Tab, Enter/Delete/Escape/Back; activation repeats are suppressed. `coh_hud_navigation_axis` provides edge-triggered joystick navigation. The host test pins the adapter's 22 numeric constants against real NDK r28c headers at ARM64 compilation.
8. Android's actual InputConnection must queue `coh_hud_ime_composing`, `coh_hud_ime_commit`, finish/delete, and submit calls. Composition stays separate from committed chat text. Delete supports one previous Unicode scalar. Android displays/hides its keyboard from the latest owner-thread `coh_hud_keyboard_requested` result. This is a native adapter contract, not an independently qualified Java InputConnection implementation.
9. Poll `CohHudIntent`: use-power, send-chat, target, select-character, and open/close-character-menu. Each carries snapshot revision, actor ID and copied data. No callback reaches the game/session; that adapter remains primary-agent owned. Snapshot changes never rebuild widgets or erase the in-progress committed chat input.
10. On Surface loss call `coh_hud_surface_lost` and `coh_hud_gles_forget` after actual context loss. Re-upload caller textures, create a fresh GLES backend with the new nonzero generation, then call `coh_hud_surface` again. Logical state/focus and chat text survive; stale drawlists are rejected. Destroy GL resources only while their same context is current. `coh_hud_destroy` is idempotent and does not own atlas/backend resources.

## Reproduce qualification

```sh
python native-android/engine/ui/gameplay/check.py --output /tmp/hud-check.json --source-root /path/to/full/coh-android --sanitize --ndk /path/to/android-ndk-r28c --font /path/to/assets/fonts/mont_hvbold.ttf
python native-android/engine/ui/gameplay/gles_check.py --ndk /path/to/android-ndk-r28c --font /path/to/assets/fonts/mont_hvbold.ttf --output /tmp/hud-gles-host.json
```

`--source-root` also accepts the `upstream/ouroboros` directory. The source hashes must match the audit. `--font` verifies the original asset SHA and runs 95 glyph/advance checks, mask packing, generated C atlas consumption, fallback and five malformed-input checks. Host strict C99, ASan and UBSan exercise copied state, 18 malformed snapshot cases, zero maxima, touch cancel, controller repeat filtering, Unicode IME, modal focus, queue saturation, 32 context-loss/recreation cycles, image/glyph generation validation and geometry/scissors. LSan is disabled; no owned heap exists and host/ARM binaries are checked for direct malloc-family imports. This does not assert that libc internals or the entire Android process allocate zero memory.

The GLES host suite creates an actual surfaceless EGL pbuffer and GLES3 shaders. Four RGBA pixel comparisons use ±1 channel tolerance for straight-alpha blending, original color bytes, R8 glyph coverage and clipping. With `--font` it uploads the original Montreal Heavy atlas and compares 9,915 rendered glyph pixels against the CPU masks, also at ±1 channel. It checks batching across 129 quads, invalid/stale/missing resources, repeated create/destroy and disabled scissor on return. Its renderer is Mesa llvmpipe; it is not Android or Adreno qualification, nor a comparison to the original client's legacy rasterizer.

## Combined Thor checks

Use the coordinator's offline support APK, keeping accepted Session Client 0.3.0 installed. Confirm original-font text is legible; HP/endurance/target changes follow mock state; D-pad/A and touch select ready powers; cooldown/disabled powers do not activate; character menu isolates focus and returns copied selection intents; text input commits/submits once and deletes a full Unicode scalar; Home/return and Surface recreation retain text/state; diagnostics export shows frame generation, HUD draw/intent counts, zero GL errors and no growing arena. Exercise landscape/portrait or display-size changes and safe areas. Authentic font rendering and input on the Thor remain unaccepted until actual reports/screenshots are reviewed.

## Limits and rollback

The layout is a compact native HUD using authentic source colors and font, not a pixel-identical port of the original desktop interface. It omits formatted/rich chat, text selection, cursor positioning, full IME surrounding-text editing, composition underline, arbitrary Unicode font fallback/shaping, drag/resizable saved windows, original frame slicing, circular cooldown shader, full power target semantics, chat channels, inventory/mission UI and real character/server actions. Atlas fonts support 512 sorted glyph records per table; this qualified preparation uses ASCII only with explicit replacement. Snapshot limits and error returns are intentional bounds. No live authentication/session dependency is required for this module.

Integration is additive: remove the coordinator's opt-in harness calls and library source references to roll back. Existing UI kernels, 0.3.0 accepted scene and accepted APK receipts were untouched. Preserve primary gates 25–27 ownership. Do not reset the shared branch or revert unrelated commits when removing this extension.

## Consolidated support-client adapter

The coordinator explicitly delegated the two additive `support-client/src/support_ui.{h,c}` files after the HUD commit. `SupportUi` serializes every public update/draw/snapshot call with its own mutex. Its opaque initialization allocates one 412,184-byte arena on this host; the engine remains fixed-capacity thereafter. GL create/draw/destroy must stay on the current-context GL thread. Touch/key/IME/snapshot calls may arrive on another thread and acquire the same bounded-operation mutex. The parent must stop/join external callbacks before CPU destruction; it calls `context_destroy` while current, or `context_lost` after actual context loss.

The adapter uploads the generated original-font R8 texture, retains a bounded local intent history, and exposes counters for exported reports. `support_ui_tick_mock` intentionally animates mock health/endurance and 2.5-second recharge; local powers and chat are explicitly labeled offline. Character choices only update mock data and a message that the scene remains Huge/Wretch. It invokes no game/session/network API. `support_ui_focus_chat` is an optional Android chat-button affordance; all text supplied to `support_ui_text` is appended committed UTF-8, not a complete replacement buffer.

Packaging generates `support_font.h` from the default atlas generator symbols rather than committing font/glyph bytes. Add its generated directory and `engine/ui/gameplay` to includes, and compile the adapter with the HUD sources. The coordinator owns JNI, Java IME, build/package wiring and actual emulator qualification.

`support_ui_check.py --ndk ... --font ... --output ... --sanitize` reproduces real host EGL 1280×720 rendering, 104 GPU frames, five local intent paths, Surface/backend recreation with retained chat, 2,000 concurrent snapshot calls and 2,000 concurrent controller-navigation calls, plus ASan/UBSan and an Android API26 ARM64 shared-library link. This observed mutex stress is not a TSan proof. The adapter receipt is `docs/qualification-support-adapter.json`; Android emulator and physical Thor testing remain separate coordinator work.

## Original tray decoration continuation

The additive [tray extension](tray/README.md) recovers and qualifies original ring
and 1–9,0 slot-number imagery. It preserves existing typed HUD state/intents and
input behavior. Source-backed preparation, host GPU, sanitizers and ARM64 evidence
are in `tray/qualification.json`; Android/Thor qualification of this extension
remains pending coordinator integration. Power-specific ability icons remain open.

## Held analog focus navigation

`coh_hud_axis_navigation.{h,c}` is an additive mobile focus adapter, separate from
original game movement. Initialize `CohHudAxisNavigation` with
`coh_hud_axis_reset`. Pass the selected stick's normalized axes and a monotonic
elapsed millisecond sample to `coh_hud_axis_step(hud,axis,x,y,ms)` from the HUD
owner thread on each input sample and each mock frame. Positive Y means down.
Use the same elapsed-clock domain throughout a held gesture.

The adapter engages at magnitude .55, retains direction until below .35, and
requires a .15 stronger competing axis to switch diagonal focus. It immediately
navigates on direction changes, repeats once after 350 ms, then at 110 ms
intervals. A slow frame emits at most one focus action; equal timestamps never
repeat. Subtraction-based timing handles `UINT64_MAX` without deadline overflow.
A focus boundary is a counted no-op. Invalid axes/reversed time are rejected;
queue/Surface errors preserve the held edge and timing for retry. Public
counters distinguish samples, actions, repeats, blocked edges and rejections.
The fixed caller arena is 72 bytes on the qualified 64-bit host and stores no
HUD/session pointers, clock handle, heap or GL objects.

The coordinator must give the stick one owner: while UI navigation is ON,
suppress scene/camera dispatch for that selected stick. Reset the adapter and
clear its stored stick axes when switching OFF, losing focus, pausing or
removing the controller. On resume, a fresh sample creates a fresh edge. The
adapter emits only existing local `CohUiAction` focus directions. Activation,
chat, typed gameplay intents and later network dispatch keep their existing
owners.

`axis_check.py --ndk /path/to/ndk --sanitize --output /tmp/axis.json` covers held
repeat deadlines, deadband and diagonal jitter, direction reversal, stalled
frames, equal/overflow timestamps, invalid/backward input, full-queue retry,
Surface loss/recreation and reset. Host, ASan/UBSan and API26 ARM64 results are
in `docs/qualification-axis-navigation.json`; direct allocator imports are
absent. The mobile hysteresis timings are an explicit new policy; original
desktop stick-timing parity is not claimed. Existing source-qualified focus
geometry is called unchanged. Android emulator/Thor navigation remains pending
coordinator wiring and actual device evidence.

Rollback removes the coordinator's axis owner/tick wiring and this additive
module, preserving `coh_hud_navigation_axis` for existing neutral-edge callers.
No shared JNI, live session or accepted scene file changed in this worker.

## Coordinator SupportUi integration regression

`support_ui_check.py` uses C11, includes the analog adapter and prepares original
tray resources before linking the current coordinator SupportUi. Use
`--source-root /path/to/coordinator-checkout` for read-only qualification of a
separate checkout and `--tray-corpus /path/to/pinned-tray-cache` to reuse already
admitted originals. `--axis-checks` additionally tests the coordinator's public
atomic axis mailbox, held repetition, OFF suppression through a long pause and
chat retention through renderer recreation. It verifies an exact local mock
power intent after the expected three focus actions.

An already generated authentic `support_font.h` may be reused with
`--font-header /path/to/support_font.h --font-preparation /path/to/preparation.json`.
The runner verifies the preparation's generated-header hash and the pinned
original Montreal Heavy identity. Otherwise retain `--font /path/to/mont_hvbold.ttf`.
It reports generated font/tray header identities, compiled source hashes and
the actual checkout revision. This avoids unnecessary asset recovery while
preserving the previous source/font admission evidence.

`docs/qualification-root-support-integration.json` records host EGL,
ASan/UBSan and ARM64 build results against coordinator commit
`0425bc98e90924f399ed8f6db922f32d683133cd`. The tested UI C implementation is
unchanged from `eacf8bf415c4937d0daaed75d790a6ed2b37cd11`. The additional Java
HAT/device-removal policy requires its independent Java/emulator qualification;
this C harness does not establish Android framework or physical controller
acceptance.
