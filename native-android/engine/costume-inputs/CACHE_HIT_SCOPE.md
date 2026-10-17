# Exact-cache-hit and text-fallback callback scopes

This clarifies the remaining-gate wording in the original47ef643b7 qualification
without changing that frozen decoder/source proof. The API still stages raw
serialized fields and accurately reports original_callbacks_applied=0.

Original ParserLoadFiles first tries ParserIsPersistNewer/ParserReadBinaryFile.
On successful binary read it returns1 IMMEDIATELY. It does not proceed to the
text-loading branch, its preprocessor callback, or binary regeneration.
Only text/fallback parsing invokes the preprocessor, then writes the bin.
Therefore a previously generated bin can already contain the serialized results
of that preprocessor. Do not apply it again merely because the callback exists.

| Original input/path | Successful exact binary read | Text/fallback regeneration |
| --- | --- | --- |
| bpReadBodyPartFiles / BodyParts.bin | ParseBoneNames is the preprocessor only; it is not rerun on cache hit. The serialized28part count, bone numbers and indices are consumed directly | ParseBoneNames must execute with the exact generated BoneIdEnum/name lookup; missing generated dictionary remains a regeneration dependency |
| loadCostumes / costume.bin | costume_preprocess is not rerun; serialized names/angles already reflect generation-time preprocessing | Original preprocess forward-slash/texture truncation/!none replacement and degree conversion must execute in the original order before bin writing |
| loadCostumes / supergroupColors.bin | No preprocess/post/final callback passed for this load | Original Parse6/table text generation and input inventory still required |

ParserLoadFilesShared adds another independently selected source branch:

- SMAR_Error or no-persist/forced fallback: DefaultAction calls ParserLoadFiles,
  then passed postprocessor/finalprocessor run. A successful inner cache hit
  skips preprocess but does not skip the outer finalprocessor.
- SMAR_FirstCaller: DefaultAction loads data, postprocessor runs if present,
  data is compressed/copied into shared storage, then finalprocessor runs with
  shared_memory=true.
- SMAR_DataAcquired with matching ParseTableCRC: existing shared root data is
  copied and ret=true. It does not rerun any of those callbacks in that branch.
  The previous shared generation's source/input/state provenance must be bound.

loadCostumes passes costume_fillExtraDataCallback as finalprocessor. This is a
real source dependency for first/error/no-shared construction, distinct from
preprocess. Its effect on dictionary-bearing fields and array ordering must be
qualified before offline dictionary publication. The full builder also performs
its own texture-name dot truncation during costume_initHashTable.

No runtime cache-selection branch or shared generation was observed in these
host decoder tests. Recovering and decoding authenticated CLIENT bins proves
those bytes and their grammar, not that the current MapServer consumed the same
bins unchanged. Exact server source/profile/schema, cache consumption versus
fallback, shared-state selection and complete dictionary slot equality remain
external gates. Missing BoneIdEnum is NOT an invented prerequisite for the
exact verified binary-cache-hit route. Neither this clarification nor cached
bone words independently grants selected-character/renderer/ACK authority.
