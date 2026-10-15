# Gate 34: bounded native game UI framework

Status: **framework implemented and host qualified; ARM64 Android shared-library build passed. Android rendering, emulator and physical Thor acceptance are pending. Gate 34 is not accepted.** This module is opt-in, outside every existing APK/JNI/Gradle/CMake execution path. It does not alter the launcher, accepted client, or gates 19–21.

`coh_ui.h`/`coh_ui.c` provide seven reusable widget types: panel, window, label, button, editable single-line input, icon and normalized progress bar. Widgets have stable IDs, parent IDs, anchor layout, binding IDs, font IDs and original-resource IDs. Windows are containers, not a replacement for the original movable/curved-window implementation. A fixed caller-owned arena holds 128 widgets with 255 text bytes each, 4,096 draw commands and 64 input events. `sizeof(CohUi)` is the exact bound, reported by tests. The module allocates no heap, takes no locks and performs no file, transport or GL operations.

The output is a flat insertion-ordered drawlist of clipped solid/image/glyph quads. Commands carry pixel rectangles, normalized UVs, straight `0xRRGGBBAA` color, stable resource IDs and Surface generation. A visible border identifies controller focus. Logical state is separate from GPU resource ownership. Font lookup is a synchronous caller callback with font ID, Unicode scalar and logical font size; it must supply qualified metrics and an atlas resource ID. Missing fonts/glyphs and full command arenas fail the complete frame with `draw_count=0`, rather than silently presenting partial text.

## Public contract

- Single owner thread; caller copies game snapshots or input across its own bounded queues. Glyph callbacks cannot reenter/mutate the UI. Borrowed callback context/font resources remain caller owned until teardown.
- Initialize `CohUi` in a heap or static caller allocation; its approximately 320 KiB arena should not be put on a small Android thread stack. Call `coh_ui_surface` before layout/input/build. Add parents before children; IDs are nonzero and unique.
- Rectangles use the original 1024×768 reference plane. Each child uses its parent's logical rectangle and `anchor_x/y` in `[0,1]`; all descendants clip to parent bounds. `XY`, fixed pixel and centered fit scaling are explicit modes. The HUD adapter chooses its mode; it does not infer the original game's shell/global settings.
- `coh_ui_bind_text/value/enabled` changes existing controls using a stable binding ID, without rebuilding the tree. Text binding validates every target's line policy before changing any target. Values clamp to `[0,1]`; nonfinite input is rejected.
- Pointer coordinates are pixels; one captured pointer is supported. Only release over the captured control activates it. Other pointers cannot overwrite capture. Touch at zero coordinates is valid. Directional controller focus uses visible enabled control centers; next/previous navigation uses insertion order.
- Poll `coh_ui_keyboard_requested` after layout/input and translate its state into Android IME show/hide calls. Convert Android committed text to scalar UTF-8, then call `coh_ui_text_commit`; `BACKSPACE` removes one Unicode scalar. Events identify widget and binding, so the game adapter decides whether to trigger a power, send chat, or change character selection. Text events refer to current logical text rather than retaining a second snapshot.
- The event queue rejects an action before changing text/focus when capacity is exhausted. Drain it each frame. Removing a subtree drops events for removed IDs, and clears its focus/capture. Hidden/disabled ancestor changes clear descendant focus/capture at the next layout.
- On Surface loss, stop draw consumption and call `coh_ui_surface_lost`. It clears capture and draw validity, preserving widgets, text, bindings and logical focus. On recreation supply a **new nonzero generation**, recreate the renderer's own GL atlas resources, and rebuild. Consume only a successful build for which `coh_ui_drawlist_valid` matches the active generation. The UI stores no GL handles. Destroy is idempotent after producers stop.
- All public text inputs are valid accessible NUL-terminated C strings. Status returns distinguish bad input, missing ID, unsupported glyph backend, fixed capacity and unavailable Surface. UI diagnostics contain no credentials/chat text.

## Source and reference evidence

See [docs/SOURCE-AUDIT.md](docs/SOURCE-AUDIT.md) and the exact content hashes in [docs/source-hashes.json](docs/source-hashes.json). The host oracle compiles unchanged original `calc_scrn_scaling_with_offset` and `uiFocus.c` bodies under narrow platform stubs. It compares 768 resolution/mode cases and 259 focus trace steps. A separate Python Unicode reference compares more than 8,700 valid/invalid UTF-8 cases. This proves the selected scaling/focus behaviors, not complete original UI parity. Tests deliberately permit Android touch at `x=0/y=0`, where the old mouse predicate excluded those points.

Run from repository root:

```sh
python native-android/engine/ui/check.py --output /tmp/coh-ui-qualification.json --source-root /path/to/full/coh-android --sanitize
```

`--source-root` accepts the repository containing `upstream/ouroboros` or that source directory itself. Hash mismatch fails rather than updating the reference. Without original sources, unit checks can run but source qualification remains explicitly incomplete. The driver runs strict C99 `-Wall -Wextra -Werror -Wpedantic`, 11 groups including a mock HUD/game-state binding integration, negative queues/UTF-8/geometry/atlas/capacity tests, 20,000 repeated text/draw/lifecycle cycles, and ASan+UBSan. `nm` verifies there are no malloc-family imports. LeakSanitizer cannot enumerate this environment's `/proc` tasks under ptrace and is explicitly disabled; no LSan pass is claimed. The recorded host CPU time is a small synthetic workload diagnostic and is not a game benchmark or Thor measurement.

## Integration and rollback

1. Cherry-pick the isolated UI commit only after re-fetching `native-android` and checking this directory for concurrent changes. No root build or live Session Client file is owned here.
2. Coordinator adds `coh_ui.c` to an opt-in consolidated library. Dependencies are `coh_contracts.h`, libc and libm. A renderer adapter resolves stable resource IDs through gate 22, submits clipped pixel-space quads through gate 24, applies `SRC_ALPHA/ONE_MINUS_SRC_ALPHA`, and checks generation before use. It must match the source engine's alpha-channel blend semantics and GL top/bottom scissor conversion in GPU tests.
3. Qualify authentic game atlas textures and FreeType font metrics/rasterization through the asset/font adapter. Connect health/endurance/powers/chat/character selection/inventory/mission snapshots through application-chosen binding IDs. No gameplay/server command is sent by this module.
4. Connect Android touchscreen, gamepad, keyboard and committed IME input, and Android window/Surface lifecycle. Consolidate with other ready gates for one test APK. Test scaling, focus visibility, chat entry, Surface recovery, limits and authentic font/image captures on emulator then Thor.
5. Existing conventional and accepted native APKs remain untouched. Rollback before adapter activation is simply omitting the opt-in library. After activation disable the coordinator adapter or additively revert the UI commit plus its dependent adapter; never reset history or delete existing receipts.

## Remaining requirements

No Android app, APK, GL draw pass, authentic font atlas, real touch/controller/IME event bridge or screenshot comparison is included. Source-compatible resource/font IDs are supported but authentic font/image rendering is **not yet qualified**. The original font engine uses FreeType face streams, fallback/cache/render parameters and Windows synchronization; those facilities were audited, not ported. The callback boundary prevents placeholder fonts being presented as source accurate.

The first framework supports explicit anchors, clipping and insertion order. Original curved nine-slice borders, draggable/resizable windows, z sorting, rich/SMF text, auto wrapping, scroll containers, kerning/shaping, font fallback, clipboard, multiline editing, caret/selection/preedit composition, accessibility and multiple simultaneous touches remain future adapters or extensions. Deletion is scalar based rather than grapheme based. Focus veto callbacks from the original engine are not implemented. None of these omissions blocks independent host work on HUD bindings, renderer/asset adapters or gate 35 components, but Android rendering/input and authentic UI asset tests are required before gate acceptance.
