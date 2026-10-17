# Original model-name Trick selection

`coh_wr_trick_model_select` and `coh_wr_trick_detached_model_select` execute the
bounded original `trickFromObjectName` selection over the already admitted whole
or detached historical Trick dictionary. This closes actual model-name selection:
the earlier historical association inspector began with an already captured Trick
name. The new selector starts with the actual captured model name and GEO path.
It creates no new cache, material, texture binding or generation.

## Exact source selection

Original `Common/seq/tricks.c` uses the complete suffix after the first `__` when
present. It never retries the base model name after a suffix miss. Without `__`,
the complete model name is the key. Existing owner lookup preserves original
case-insensitive reverse-registration/nonoverwriting precedence, including the
highest original ordinal for duplicate names. No texture-name normalization,
directory lookup, substring fallback or last-suffix rule is introduced.

The original global existence-reporting switch is an explicit 0/1 query input.
A missing suffix can produce a filename or generic diagnostic; an ordinary
whole-name miss is silent. The result classifies the original would-log branch,
without logging or invoking callbacks. The GEO path affects only diagnostics.
The qualifier executes the complete unchanged original `trickFromObjectName` and
`getDirectoryName` from `libs/UtilitiesLib/src/utils/utils_opt.c`. Dictionary
registration/storage and logging are explicit observers; original stash/runtime
ABI, message formatting and active dictionary construction are not claimed.
The original caller `modelInitTrickNodeFromName` in `Common/seq/anim.c` is pinned
as a source dependency, but this kernel does not allocate or mutate a model node.

Queries require a nonempty printable ASCII model name and a printable ASCII GEO
path, each shorter than 260 bytes. The path may be empty but must not be NULL.
Each pointer must contain NUL within 260 readable bytes or supply all 260 readable
bytes for bounded refusal. A short unterminated span is not a valid pointer input.
Inputs stay immutable. Outputs must be disjoint from query, limits, strings,
owner and retained body; all refusals preserve output. A completed historical
miss returns OK with `matched=0` and `source_ordinal=UINT32_MAX`.

The copied result contains the exact lookup key, branch, matched ordinal,
diagnostic classification and the existing cache hash/historical import label.
It retains no pointers. To inspect the selected record, use the same still-live
owner's existing raw/numeric/child APIs. Selection does not complete animation
postprocessing: the 32 root observations with historical StAnim obligations
still need their actual track bindings. A miss does not authorize a default Trick,
material or LOD.

## Actual retained association evidence

The new qualifier admits the exact retained 13,537,052-byte `tricks.bin`, SHA256
`cf9595e54bc65a40d2dddc3a5a13c475d7c2ce07a96420e6001b0e2312926bc1`,
12,596,422-byte COHRES capture, SHA256
`8500764939215b576e5ff88056ec85b475785038e09600019846ff5a06eb1cd6`, and
1,103,262-byte root partition ledger, SHA256
`46df6643795c3d06aa5b52b3c2fadeed1eac00a3693f33ac611bb5d990109e2a`.
Complete input/source hashes are checked before use and readmitted afterward.
The independent dictionary fixture is decoded from the exact historical bytes in
original source order. Root ordinals, complete model/GEO names, ordered texture
partitions, captured Trick presence/name/source file are read from actual retained
resource records and checked against the root ledger.

| Actual root observations, for each owner form | Count |
| --- | ---: |
| Complete model names queried | 3,083 |
| First-`__` suffix queries | 1,958 |
| Whole-name queries | 1,125 |
| Selected historical Trick records | 1,959 |
| No historical dictionary match | 1,124 |
| Distinct selected historical rows | 528 |
| Selected presence/name/source-file disagreements with capture | 0 |

These are actual historical model associations, rather than derived TexBind
inputs. Additional name/case/suffix/diagnostic controls use actual dictionary keys
in explicitly derived queries. They do not add observed model associations.
The whole and detached APIs produce the same source selection. Detached tests
repeat all queries after the original cache/TexOpt owners retire, loader resident
and allocated bytes return to its actual baseline, the loader is destroyed and
the provider body is freed. No new body download or runtime capture is needed;
the retained 391-GEO qualification remains intact and is not rerun.

The old reader/getter implementations are preserved byte for byte, checked by
fixed legacy implementation hashes after removing only the new header include
and selector instantiation. Existing old qualifier dependency/export allowlists
are updated for the added public function; those old qualifiers are not rerun.
Only the new source-specific qualifier runs release, ASan, UBSan, actual C-object/
C++ linking, and six semantic/refusal mutations. It checks first versus last
suffix, forbidden base fallback, source-path leakage, whole-name diagnostics,
aggregate admission, name/path bounds, owner/body aliases and output preservation.

## Ownership and remaining identities

The new selection owns zero persistent bytes, performs zero heap allocations,
acquires no pins and invokes no callbacks. On the qualified host its copied
output is 320 bytes and each selector's release frame is 432 bytes. A fixed 4 KiB
query/input/output/control reserve is added before lookup. The caller's external
reservation must include the existing owner, the whole configured loader
reservation for a whole-cache owner, all other live owners and source
statics/code/runtime/provider peaks. Detached lookup requires only its existing
owner and external execution context; it does not retain the retired provider.
These are component bounds, not complete process RSS, ARM64 stack measurements
or a new aggregate memory closure.

The result remains a historical CLIENT dictionary selection compared with
captured SERVER names. Neither matching names/files nor a matching cache hash
proves equality of live SERVER/CLIENT generations, current model ownership,
reload/removed dictionary state or the active Trick table. Actual selected
TexBind/composite/Basic inventories, overlay/duplicate order, locale and swaps,
default texture-owner identities, capabilities/fallback/water state and effective
material ownership remain missing. Existing material admission is unchanged.
No current material, GPU, world, Android/GLES or physical Thor acceptance is
granted by this kernel.

```
python native-android/engine/world-render-adapter/check_trick_model.py \
  --actual-cache /path/to/exact/tricks.bin \
  --resources /path/to/exact/resources.cohres \
  --output /tmp/FRESH-trick-model-selection.json
```
