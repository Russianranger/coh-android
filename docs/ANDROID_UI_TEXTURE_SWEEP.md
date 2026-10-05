# Native interface texture sweep after 0.13.13

The physical 0.13.13 screenshots show restored inspiration/power icons but remaining white tip icons, enhancement slot overlays and some NPC name graphics. This pass adds **788 exact original textures / 23,704,759 decoded bytes**. It preserves all **9,613** previously accepted visual ZIP streams, including the prior 123 UI additions, byte for byte. No world geometry, existing animation, character database, Game executable, renderer or input behavior changes are part of this texture producer.

## Scope and screenshot findings

The frozen request graph audits all **184 native UI C modules**, complete literal filename arrays, variable-backed atlas requests, shared frame/button constructors, **2,551 stock enhancement power definitions**, enhancement attribute/origin badges and player archetype definitions. It contains **1,609 exact texture keys**, **797 retained dependencies**, 788 appended leaves, one native stock composite alias and **23 explicit unresolved exact donor names**. It reads frozen PIGG metadata prefixes and 26 bounded payload ranges, with 524,396 bytes of bounded transfer gaps. It does not download/import entire source archives.

| Reported area | Source evidence | Result |
| --- | --- | --- |
| White tip icons | `uiPopHelp.c` variable-backed `Pop_Help_Icon_On_Alert`, `_Glow`, `Pop_Help_Icon_Off_Blue` | All three original textures appended; the first pass only scanned direct string arguments and missed these globals. |
| Enhancement inventory/slot white centers | `uiCombineSpec.c:531–596` loads `EnhncTray_Ring`, `_Ring_highlight` and `_RingHole`; the shell menu draws the first two above the hole | Ring and highlight were absent from all installed texture layers and are appended. The retained 64×64 RingHole is byte-identical. Its center is opaque dark blue, so it is not responsible for the white square. Missing ring/highlight one-pixel atlas fallbacks explain the overlay by source/draw-order inference; physical confirmation remains required. |
| Enhancement rewards and details | `uiEnhancement.c`, `uiCombineSpec.c`, `boosts_*.powers`, `attrib_names.def` | Exact stock enhancement icons, origin frames, attribute badges, combine instructions, controls and labels audited; present leaves retained. |
| White graphics below NPC names | `uiReticle.c`/`uiTarget.c`: `Conning_arrow`, `bar_background`, `BAR_HEALTH`, `BAR_ENDURANCE`, `BAR_GRAY` | Original conning arrow and overhead bar textures appended. |
| Tooltips/shared borders | `uiToolTip.c` calls the shared frame constructors | Frame corner/background/edge variants are derived from actual native PIX/radius calls; generic button rest/press layers and map icon struct arrays also audited. |
| Empty third trainer pane at level 2 | `uiLevelPower.c:360–363`, `schedules.def` | This is the native Pool/Epic selector, first available at displayed levels **4 / 35**. Hovered power details are below the three columns. No replacement information or new trainer behavior is invented. |

The native texture index in both 0.13.13 reports registered all 20,053 installed headers with 20,053 index hits and zero ordinary header reads. The first report rebuilt after installing the 123 prior UI leaves; the second revalidated and reused the index. There is no evidence of a stale pre-supplement index or a basename collision. Native atlas lookup silently returns its white one-pixel fallback for absent names, so absence of missing-texture log messages is not proof of complete UI binding.

The new scanner preserves comment markers inside quoted filenames. A literal `texture_library/maps/*/%s` must not erase following code while stripping C comments. It also follows the native atlas suffix removal followed by `texFind` normalization, including the authored `.tga.tga` caller, instead of inventing donor spellings.

## Focused contact overhead geometry audit

The three `UI/Icon_MissionAvailable.fx`, `UI/Icon_MissionInProgress.fx` and `UI/Icon_MissionCompleted.fx` files request the exact `Icons_Contact_Mission*` models in the already accepted `data/object_library/iconsandui/icons_contact.geo`.

- Retained GEO: 18,071 bytes; SHA-256 `b9bb563ea013f45ede84c2068e2923a100ab9883d42e11b281e4bf0a0d9374c5`.
- Native model-table SHA-256: `df33a4599af2413bc0c7192904ed9bb224d395cc9400242632ffd079df75f814`.
- All three model prefixes match the original GEO table. Their materials are `MissionAvailable`, `MissionInProgress`, and the stock composite `X_Icon_Contact_MissionCompleted`.
- Completed-contact composite slots (`MissionCompleted`, `Generic_Scroll_Offset3`, `Mission_BumpMap`) and the other two materials already exist. The exact original trick definition is source-pinned. No substitute GEO or material is imported, and this table audit does not claim device mesh/rendering qualification.

## Finite remaining boundaries

The five previously unavailable stems remain explicit: `checkbar_meat_base_underlight_{l,mid,r}`, `checkbox_base_underlight`, `default_tray`. The other absent exact donor keys are `compass_facing_bottom`, `gradient`, `map_enticon_store_{magic,mutant,natural,science,tech}`, `map_enticon_tailor`, `me_marker`, `powers_iconring_background`, the authored trailing-dot `taboverlap_24px_frame_corner.`, and seven `v_archetypeicon_*` hero names. Native archetype lookup has its normal non-`v_` fallback, which is retained. No similar-looking donor replaces these names.

This is a complete source sweep of the declared interface scope, not a claim that every dynamic property/emblem, every world/material dependency or every unvisited UI screen is visually qualified. Physical screenshots remain the acceptance evidence.

## Reproducibility and cache behavior

`discover_client_ui_sweep_assets.py` derives source witnesses and resolves only exact missing names. `prepare_client_ui_sweep_assets.py` verifies the immutable recipe and original donor ranges, checks all retained encoded streams and reuses the original compressed streams for every addition. The new source manifest is a small, bounded append recipe over the pinned existing 0.13.13 source manifest; it reconstructs the exact plaintext bytes before packaging. Requests and plan use bounded source envelopes as well. These transport choices do not change runtime JSON or ZIP bytes.

| Runtime artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `client-visual-assets.zip` | 859,075,775 | `5f91b7d4ebe91e6a547923d702e2fcd56d7fc1d36fb7bffbb66463562d977d60` |
| `client-visual-manifest.json` | 48,591,999 | `8587015400e1af639e2118649f0d9c77a089d564bfe2c97cbf9d80baaee5f9a2` |

The guest installer validates a separate UI sweep partition and projects precisely the old 9,613 leaves before running existing UI/appearance/world partition checks. It records added UI sweep counts while retaining the existing missing-only installation, readonly fingerprints, cache freshness and warm reuse policy. Warm preparation continues to require zero archive/decode I/O after a successful matching receipt. The first updated launch prepares the new finite resources and native index; subsequent launches reuse valid preparation. No physical startup speedup is claimed from this asset append.

Targeted validation: 35 new UI sweep tests, 32 retained UI tests, 52 existing visual installer/cache tests; all pass. Actual archive verification checks the complete 10,401-leaf inventory. Separate encoded-stream checks establish 9,613 conserved donor streams and 788 byte-identical original added streams. A separate fresh materialization from the committed append recipe and 26 pinned original source ranges reproduced the exact ZIP/manifest pins and passed the full inventory and preservation checks.
