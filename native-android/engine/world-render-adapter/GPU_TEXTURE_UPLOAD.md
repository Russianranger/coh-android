# Bounded generation-owned texture upload adapter

`coh_wr_gpu_texture.c/.h` is an additive transaction adapter over the qualified
immutable all-mip CPU owner and source sampler projection. Its narrow injectable
GLES3 operations can describe actual resource upload. Current qualification
executes a host GL-state model, **not a GL driver or Android**. No production
GLES backend, material supplier, scene capability or world publication is added.
The protected renderer/assets/bridge are unchanged; rigid MIP_LINEAR admission
remains closed pending complete resource/material/Surface integration proof.

## Transaction and state ownership

A successful transaction creates one new texture name, uploads **every** retained
RGBA8 mip without generating/substituting levels, sets source-projected wrap and
min/mag filtering, and restores prior texture binding and all relevant 2D unpack
state. This includes pixel-unpack-buffer binding: leaving a PBO bound would
reinterpret the CPU pointer as an offset. UNPACK_ALIGNMENT becomes1 for upload;
ROW_LENGTH, SKIP_ROWS and SKIP_PIXELS become0. Their exact prior values and the
current unit's TEXTURE_BINDING_2D are restored before publication. No active
texture unit is changed. GLES3 is required for the PBO/row-state contract.

`image_rgba8` means a full `glTexImage2D(GL_TEXTURE_2D, level, GL_RGBA8, width,
height, 0, GL_RGBA, GL_UNSIGNED_BYTE, rgba.data)` consuming the complete span
synchronously. It must leave other state untouched. Other callbacks likewise
implement only their named GLES operation and check errors, without clearing
unrelated pending errors or performing hidden mip generation, shader changes,
active-unit selection, format conversion or CPU pointer retention. `generate`
returns partial names even on error; deletion acknowledges consumed ownership
through its in/out name. Callback implementation and actual-driver behavior
remain separately unqualified until a real backend/oracle is executed.

A token carries nonzero Surface generation, context generation and render-thread
identity. Backend `current` authenticates all three against actual current state
before every upload operation and view. Backend identity (context pointer and
every callback) is retained; a substituted operations table refuses. Backend
state/registries/callback code must outlive every resource and pending journal.
All calls are serialized on one owner thread; the backend/caller must quarantine
**all** other work in a context while any journal is pending, including uploads
using a different journal. This adapter does not implement a global registry. No
unrelated GL work may interleave snapshot, transaction or saved-state cleanup. Copied renderer descriptors
must not outlive the resource or same-token flush. A getter check cannot protect
a descriptor copied before later context loss.

## Context loss, Surface recreation and cleanup

Normal failure restores prior state and deletes the candidate, leaving output
NULL. If restoration/deletion cannot be verified, a caller-owned **pending cleanup
journal** retains the exact old name, backend, token and saved state. COH_STATE
reports that outstanding responsibility; another upload using that journal
refuses. The journal must not be copied, edited or abandoned.

Cleanup uses `retire_current`: it verifies the original live context generation
and render thread, allowing a recognized retired Surface on that **same** context.
Thus Surface-only recreation invalidates views but can retire an old name safely,
then upload a fresh name for the new Surface. Pending saved-state cleanup must
finish before other work in that context; it is not a general queue that may
restore stale bindings after arbitrary later rendering.

An unrelated replacement context never receives the old numeric name in a bind,
restore or delete operation. Retry cleanup when the original context returns,
or use `destroyed` to verify that exact original context lifetime ended. Only
that backend-verified disposition permits forgetting old names without GL calls.
A new context may reuse numeric name1: generations still distinguish it. Ready
resources follow the same explicit original-context retirement or verified-dead
path. Uncertain deletion retains ownership; a callback that reports an error
after verified consumption clears the name so later retry cannot delete reuse.

The GPU owner copies exact source path/generation/SHA and CPU texture metadata.
CPU resource/loader may retire after synchronous upload completes. Views and GL
names then remain owned by the GPU resource until same-token borrowers finish.
Source sampling values are still caller-supplied qualified CLIENT state, not
inferred from cached flags or texture filenames.

## Budgets and qualification boundaries

Preflight charges the GPU-owner allocation plus an explicit driver reservation
(no smaller than nominal complete RGBA bytes), all source/CPU/loader memory,
backend scratch, older GPU owners and pending journals through external bytes.
Aggregate limit has a hard256MiB ceiling. This reserves a declared working set;
it does not measure actual GL/driver heap allocation or RSS. Runtime MAX_TEXTURE_SIZE
and caller dimension caps both apply before name generation.

Host release/ASan/UBSan tests inject errors at all33 physical callback positions,
including mutation-after-error and partial generated-name paths. Tests compare
every uploaded pixel span/level to the authentic CPU owner, preserve prior PBO
and unpack state, enforce exact budget/one-byte-short limits, reject changed
backend/thread/Surface/context tokens, exercise cancellation and allocation
failure, retain/retry failed cleanup and verify name reuse after context loss.
Two-context and Surface-only recreation are model controls; they are not EGL or
Android evidence. Actual GLES3 backend binding, error handling, GPU readback,
Android13/EGL context recreation and physical Thor execution remain future steps.
