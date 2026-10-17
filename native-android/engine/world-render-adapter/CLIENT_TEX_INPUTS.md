# Retained texture and trick source inputs

`coh_wr_tex_inputs` imports immutable, hash-pinned cached texture headers and raw trick text. It deliberately creates no `BasicTexture`, `TexBind`, effective TexOpt, default composite, material, GPU resource or world publication permission. `input_generation` identifies this import; it does not establish a matching original CLIENT generation.

## Actual available inputs

The host qualifier admits two complete original cached `.texture` bodies: the previously qualified Box-1 fixture and Atlas supplement `Bar_vert_sign`. Box-1 has no demonstrated Atlas membership. The Bar candidate is the texture name on the authentic reachable Neon GEO partition; candidate lookup and body provenance do not establish the active CLIENT table or effective material.

Bar is 22,163 bytes, SHA256 `c224a6dff69716bde300bb956d7415745780ceeee249e526ad1de69cab654b58`. Its original cached filename is `texture_library/WORLD/Swappables_and_Decals/Signs/Billboard/Neon/Bar_vert_sign.dds`. Its observed dimensions are 128×256, cached flags/alpha/fade are zero. These are header observations, not effective runtime texture flags. Exact outer/inner ZIP membership, selected-body SHA and ZIP CRC are retained in `tex-inputs-authentic-pins.json` and the acquisition receipt. Complete outer/inner archive hashes were not verified. The bounded acquisition read 671,212 range bytes; it did not download either archive in full.

Before that acquisition, the retained artifact for run 38995343373 was inspected locally. Its exact ZIP SHA is `16fdb1671bbac5c3a3abc6e2d6668ecd2efaf5ac34d0ef523fe651fffa56a773`; it contains no texture bodies, sampler, cloud01 or KTX members. Existing sampler/EGL texture copies were all Box-1. The existing artifact was reused, without another workflow or server capture.

One exact original raw trick file, `coh_r/buildings/cohr_shaders_brickfiller.txt`, is admitted from its Git blob. It contains the complex `asphalt_squaremask` material used by the reachable Shop roof. Raw bytes are retained and explicitly unparsed. Its referenced cached texture is absent from the three supplemental manifests inspected by A; that is not proof it is missing from the complete original import.

`inspect_tex_inputs.py` verifies all 1,585 retained repository trick text blobs (12,161,418 bytes). The complete canonical per-file inventory SHA is `7cf616bc57211ef73e8c87934d06d2efbd31b9b38507307f73d890419f00b98e`. Repository availability does not prove those files, their enumeration order, or their compiled cache were the active CLIENT inputs.

## Original CLIENT rules and remaining inputs

The pinned `tex.c` factory builds separate Basic and composite stashes. ASCII case-insensitive keys are the default. Cached header naming uses the original `texFillInBind` basename/directory block and `texFixName`, rather than the model texture table's separate last-extension projection. The original header processor skips underscore-leading entries, checks cached key against filename stem, and retains the first duplicate key. LWC later stages skip existing keys. Therefore an unordered subset cannot reconstruct overlay winners.

This import retains input order and rejects case-insensitive duplicate Basic keys. It does not label input order as original CLIENT enumeration. Unknown, overlong, non-ASCII, unsafe short-suffix, mismatched cached filename, malformed header and wrong-role paths refuse. The guarded short-key repair remains a separate explicit projection policy; this cached-name import uses the unchanged source-safe subset. A failed lookup means absent only from this imported subset.

`texScanForTexHeaders` creates initial composites from Basic textures, invokes trick-created textures, applies scene/locale Basic substitutions, then resolves binds. A default composite copies names/directory and `orig_bind`; material fields are filled later by `texSetBindsSubComposite`. The new import does not manufacture these seeds because the complete active namespace and source order are not established.

Raw TexOpts are preprocessed (leading slash and extension removal) and postprocessed in reverse array order. `setupTexOpt` computes defaults, derived flags, shader layers and transforms. Trick-created composites require a Base1 relationship and availability checks. `trickFromTextureName` also uses basename, locale/extension processing and directory fallback. Cached flags are TexOptFlags; runtime Basic flags are a distinct flag domain. Zero cached flags cannot prove a no-trick material.

A qualified factory still needs all of the following:

- The exact active CLIENT cache/import inventory, archive/directory overlay rules and scan order, including duplicates and delayed LWC stages.
- The original parser schema, bin identity, complete active raw input order and postprocessed TexOpt records, including directory inheritance and all referenced layers.
- Matching CLIENT capability/fallback profile, Basic/composite table generation, ownership, `orig_bind`, scene/locale/definition swaps and delayed-load state.
- Effective layer UV/scroll/scale, blend/shader, alpha/depth/fog/glow/lighting and LOD dependencies, plus actual layer body identity and complete CPU/GPU/Surface lifetime proofs.

No source-only cached header, raw text file, manifest lookup or SERVER observation supplies these missing records. No CLIENT/server capture is performed by these helpers.

## Ownership and bounds

The owner allocates one bounded block and sorts index arrays with an in-place heapsort; original rows remain in input order. Each kind is limited to 256 inputs. Paths, keys and cached names have explicit smaller bounds than the original engine's broad namespace. Exact full body SHA and acquired path/generation are checked before parsing. Raw trick bytes are pinned but not interpreted.

The caller must configure the loader total budget no larger than `loader_reservation`. The whole reservation is charged before acquisition and checked against historical peak. `external_bytes` must reserve all other live source/old-resource/material/digest/provider peak bytes. This is an external accounting precondition because the protected opaque loader exposes no limit introspection. Input arrays/path strings are charged locally. A separately reported fixed 16 KiB preparation reserve is charged before allocation/acquisition for this module stack and limits/output/control storage. Compiler/sanitizer, loader/libc and callback stack/runtime overhead are outside that reserve and must be included in external accounting; this is not a whole-process peak-memory proof. Loader and all borrowed views must outlive the owner. Release balances all pins; failed preparation never changes the output owner. Known output aliases into inputs, owner and pinned bodies are refused.

## Qualification

Run `check_tex_inputs.py --actual-box PATH --actual-bar PATH --output FRESH.json` for release, ASan and UBSan. It compares the two actual cached-name projections against the unchanged original name block and original `texFixName`, verifies the original cached struct layout, and tests imported case-insensitive lookups, rollback, aliasing, budgets, cancellation, allocation failure, malformed headers and 256 explicitly derived namespace rows. Derived rows are stress fixtures, not authentic assets. `inspect_tex_inputs.py --output FRESH.json` independently binds complete retained raw-source availability. These are host source-input qualifications; Android execution, effective material and world acceptance remain false.
