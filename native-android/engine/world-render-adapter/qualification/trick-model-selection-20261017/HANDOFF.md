# Historical model-name Trick selection handoff

This tranche follows worker-b commit
`35299ada512a0a02df0c8ce738cf2cc36aa1c999`. New public selectors query the existing
whole and detached Trick owners using original `trickFromObjectName` semantics.
They start from actual model names, rather than the already captured Trick names
used by the previous historical correlation inspector. No cache or renderer
producer is added.

Release, ASan and UBSan each pass 301,210 checks and 28,046 unchanged original
source comparisons, with 14,023 comparisons per owner form. Each owner executes
all 3,083 actual retained root model/GEO queries: 1,958 first-suffix queries,
1,125 whole-name queries, 1,959 historical positives across 528 distinct rows and
1,124 misses. Selected presence, name and source file agree with the capture in
every case. Derived name controls do not add authentic model associations.

The complete unchanged original `trickFromObjectName` and `getDirectoryName`
execute under explicit dictionary-registration/storage and logging observers.
Six altered policies are refused: complete-name substitution, last suffix,
base-name fallback after suffix miss, GEO-path lookup leakage, diagnostics on
ordinary misses and aggregate limit bypass. Additional controls cover bounded
name/path inputs, exact/short/overflow limits, owner/body/input aliases, output
preservation, no policy allocation/read/digest callback and strict C/C++ linking
against the actual whole/detached C objects.

The selected output is 320 bytes; measured host release frame is 432 bytes for
each selector. New persistent owner bytes, heap allocations and pins are zero.
An explicit 4 KiB own query/input/output/control reserve is added to caller
external accounting. Detached tests repeat after the actual whole cache/TexOpt
owners retire, loader bytes return to baseline, loader destruction and provider
body freeing. These are component and lifetime controls, not process RSS or
aggregate/GPU closure.

Exact command from worker-b:

```
python native-android/engine/world-render-adapter/check_trick_model.py \
  --actual-cache /workspace/scratch/7ed1da2a7e55/retained-inputs/tricks.bin \
  --resources /workspace/scratch/7ed1da2a7e55/retained-inputs/resource-capture/capture/resources.cohres \
  --output /workspace/scratch/7ed1da2a7e55/worker-b-trick-model-final.json
```

`host.json` is that receipt. Its source revision is the preceding commit; all new
and existing source bytes are bound by the receipt's before/after source hashes.
Fixed legacy implementation hashes independently verify that existing whole and
detached reader/getter implementations remain unchanged after removing only the
new include and selector instantiation. Old qualifier dependency/export
allowlists are extended for the new symbol, but those old qualifiers are not
rerun. No 391-GEO body is downloaded, compared again or recaptured, and no APK,
JNI, build, workflow, GLES, renderer or protected gameplay source is modified.

The historical CLIENT cache label in the native fixture is explicitly 17; it is
not equated with the captured SERVER generation label. Positive association and
name/file agreement do not prove a current table/model generation, animation
postprocess, TexBind/Basic selection or material/world permission. Actual current
dictionary state and the composite/Basic namespace/default-owner inputs remain
external, as detailed in `CLIENT_TRICK_MODEL_SELECTION.md`.
