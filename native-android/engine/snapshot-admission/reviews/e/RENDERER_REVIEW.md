# Independent renderer admission review

Reviewed baseline: `3e8b5c9f5b794b58a66c6d8c62a593b926a10873`.
Only this new review directory is edited. The independently active renderer
worker and protected gameplay/runtime paths were not edited or executed.

## Result

The immutable adapter is useful for CPU ownership, generation consistency and
transactional publication. Its successful preparation is **not** verification of
source/world/actor authority. Its header and README explicitly document this
caller-attestation boundary. A runtime source snapshot with resolved topology
alone cannot supply the nine required renderer prerequisites. No activation or
new APK follows from this review.

`test_authority_boundary.c` independently exercises 29 controls in each release,
ASan and UBSan mode. `qualification.json` binds exact source and binary hashes.
The invented receipt experiment demonstrates the documented caller-attestation
limit: a selected actor at `(1000,2000,3000)` plus a player draw with identity
world transform passes adapter preparation. This is not an exploit or an
unexpected production bypass: no authentic producer is implemented by this
test. It establishes why a producer must verify geometry-to-authoritative-pose
association before setting the prerequisite bits. Nine missing-prerequisite
controls preserve output sentinel/accounting; a conflicting catalog in the same
scene cannot replace the mailbox; the old lease remains readable.

ASan runs disable LeakSanitizer because this executor cannot establish its task
inspection support. The test asserts final budget destruction succeeds. No
Android, GLES, source server or physical device execution occurred.

## Required producer checks

| Required evidence | Existing enforcement and remaining producer work |
|---|---|
| Authentic scene origin | `coh_world_render.h:14-27` declares nine caller attestations. `coh_world_render.c:167-169` only checks complete bits and nonzero hashes. Bind exact catalog, original-runtime snapshot and live GROUPS identity upstream. Source capture is not the current socket transaction. |
| Atomic actor identity | `coh_world_render.c:158-166` checks DBID/entity/generation/self and normalized finite quaternion. The full enclosing entity transaction, exact dictionary resolution and selected DBID source evidence remain upstream. Never derive them from the offline preview. |
| Actor draw pose | `coh_world_render.c:184-191` accepts finite affine draw transforms plus selected entity tags. `coh_wr_draw:386-391` renders supplied transforms; it does not compose `CohWrActor.position` or quaternion. The actor producer must compose each costume-part transform from the same validated actor pose, skeleton/appearance generation and model-local transform. Test nonidentity translation/rotation and local attachment transforms against original-source semantics. |
| Scene identity across publication | `coh_wr_publish:303-317` rejects regressed counters and conflicting catalog/asset digests within a retained generation. This validates continuity of supplied identities, not the source of those identities. Keep snapshot/session/generation and root-reference provenance together in the producer contract. |
| Supported resources | `coh_wr_prepare:184-185` checks material/geometry shape; it cannot resolve GEO version, texture names, inherited trick/material/LOD semantics or original lighting. Unsupported semantics must refuse before `COH_WR_RENDER_SEMANTICS` is set. Zero logical texture is explicitly unbound, not a missing-name fallback. |
| Pose-dependent geometry | The sharing key is geometry identity plus asset generation (`:197-210`). CPU-skinned model bytes change with pose, so include pose in the geometry identity. Asset generation alone is insufficient; conflicting same-identity bytes are rejected only within one preparation. |
| Texture and Surface lifetime | `coh_wr_bind:361-376` atomically replaces complete numeric tables; `:378-394` rejects stale Surface generation. Exact GPU-name identity/lifetime is an external ownership responsibility. Keep snapshot/binding/GPU leases until every queued span flushes or is abandoned. |
| Rollback | Preparation writes output only at `:253`; failure releases candidate/scratch at `:259-262`. Publication retains before replacing at `:320-324`. An admission diagnostic must likewise leave prior published generations and ownership untouched. |

## Capacity and batching decisions before activation

1. The adapter's 4096 draw capacity exceeds the default renderer queue of 512
   (`renderer/coh_renderer.c:82-84,160-162`). Preflight complete visible selection
   and draw sizes before submitting. A batch flush ends the active interval
   (`coh_renderer_flush:338-341`), so the next batch requires `coh_renderer_begin`
   with the same Surface generation. Do not silently discard draw 513.
2. Preserve original translucent order across batch boundaries. Flush only sorts
   contiguous opaque runs and never moves them across translucent submissions
   (`coh_renderer_flush:295-310`). A snapshot publish is atomic CPU state, not an
   atomic framebuffer operation. Partial GPU draw failure requires explicit frame
   abandonment/presentation policy; it must not advance server completion state.
3. CPU geometry deduplication does not remove per-instance work: submit scans all
   vertices and indices (`coh_renderer_submit:170-184`), then GLES uploads all
   geometry per draw (`coh_renderer_gles.c:211-223`). Visibility selection and
   qualified resource caching need measured independent work. The existing stress
   fixture establishes storage bounds, not viable whole-Atlas frame time.
4. The adapter's 96 MiB and graph's separate 96 MiB limits are not two allowances.
   Use one allocation inventory including old/new graph, source catalog backing,
   candidate/retired snapshots, texture decode buffers, queue and scratch. GPU,
   allocator overhead, thread stacks and local guest server remain additional
   measured process/device costs.

## Immediate safe integration decision

Admit the new artifact as an immutable **source diagnostic** only after exact
hash/source/generation/binding validation. Expose topology closure and unresolved
dependencies without setting renderer prerequisites, full-update ACK, READY,
RECEIVED_CHARACTER or live-world state. Continue complete actor/asset/live-GROUPS
closure independently. Existing accepted APKs remain unchanged.

## Independent A admission review

Reviewed `admit.py` SHA256
`66c33602009b4247c96c8c6d9e6a394f51852842536ae8aa2c732cad191f8bbb`
and `capture-trust.json` SHA256
`ad496a806005bb272acd1a30e54260ac46ed56c0768cb22c77161a8ee23811c5`.
Exact original archive SHA256 is
`8763048abd0d55070159955f02ae9d72e452aa44d1da6e6603a22637732d764d`.
`admission-review.json` records six independent executed controls and the actual
frozen result. No authority or rollback blocker was found in these reviewed bytes.

The local reviewed trust manifest seals all 34 retained member names, sizes and
bytes before semantic binding. Receipt, source, run, payload and diagnostic
digests/generation are cross-checked. ZIP content is not extracted; it is never
executed. Archive container SHA is provenance metadata, while admission explicitly
permits changed container metadata/compression with identical sealed members.
The independent positive control reversed member order and changed compression;
the result stayed identical. A subsequent truncated candidate refused while the
first immutable result and original archive remained unchanged. There was no
extraction into the test directory. Every live/actor/renderer/world flag was false.

The admitted diagnostic establishes 33 active roots and seven external objects,
with `_mmayhem_curtain_8_01c` the only root-reachable external name. It does not
establish that this object has renderable geometry. Most importantly it does not
claim that the captured process is a new Thor/socket generation. Keep this
one-capture trust contract separate from a future generalized snapshot parser or
live producer. The frozen dataclass is a data contract, not a security token;
its booleans are never a substitute for complete upstream source validation.

Final normalization review: importing `zlib` and translating `zlib.error` /
`EOFError` into `AdmissionError` preserves refusal and changes no authority or
binding policy. The reviewed source digest above includes that correction.
