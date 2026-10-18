# Separate application world EGL producer proposal

This is an ownership contract proposal, not an implemented backend or an application/world admission. The actual Android GPU lease proof covers a private standalone pbuffer registry. It does not establish the lifecycle of the application's EGL display, context, window or renderer. No source implementation is authorized until root supplies the typed mode/window producer alongside genuine world and selected-actor inputs. A current-context or `context_alive` boolean is not an ownership substitute.

## Existing boundary

Combined `NativeClientActivity` sends a `Surface` and Java epoch to `SessionNative.render`. The accepted fallback's actual `Graphics` structure is private stack state in protected `support-client/src/offline_scene.c`. `graphics_create` creates its EGL objects; `graphics_delete` attempts checked platform teardown. The generic `coh_renderer_gles` interface assumes a current context and accepts an integer previous-context-alive value. It has no retained EGL lifetime registry or whole-context quarantine. Support scene, HUD, appearance and stream code issue raw GL calls, so wrapping the new resource callbacks cannot gate that existing context.

The accepted fallback remains untouched. The proposed producer owns a new Combined world context and routes every GL operation in that context through its gates. It never interprets the fallback's fixtures as the selected player or an admitted server world.

## Required root producer

Root must supply a real TAKE-owned `ANativeWindow` reference and a typed opaque exclusive display/mode lease, with the actual Surface callback/handoff provenance and its nonzero epoch. The epoch is a cancellation/binding value, not physical context identity. Metadata labels or caller-populated lifetime records are insufficient.

The exclusive lease covers every same-process user of the resolved EGLDisplay and the window, beyond the fallback render worker. `eglGetDisplay(EGL_DEFAULT_DISPLAY)` may return the same process display handle. Another call therefore does not grant an independent display lifetime, and repeated `eglInitialize` calls do not supply a protective reference count. No module may initialize/terminate or use that display outside the coordinated ownership contract while this lease is held. `eglTerminate` remains behind the full exclusive lease until every producer-owned context has been verified dead.

Before granting the new-world mode, root must bind the actual completed fallback render call's success and checked `objects_released`/platform cleanup state. A single Java executor provides useful serialization, but no typed native ownership lease currently follows from it. `SessionNative.destroy()==true` alone is insufficient: its native destruction path checks running/support release but does not itself require `objects_released`. Any uncertain previous EGL cleanup keeps the new mode closed. Fallback cannot restart until the new owner proves complete platform cleanup and relinquishes the exclusive lease.

Entry also requires a genuinely admitted immutable production CPU world and selected-actor snapshot. Current missing CLIENT material/current-generation and complete actor producers remain gates. No new APK or accepted-app activation occurs before those inputs exist.

## Proposed isolated E surface

Only new E-owned `coh_wr_app_egl.h` and `.c`, a private registry header if required, uniquely named tests/checker and documentation are proposed. Root retains all common/JNI/CMake/Gradle/workflow and application switch ownership. No protected Support, gameplay renderer, appearance or audio file is changed.

The API should separate metadata transfer from physical driver mutation:

1. `create` allocates bounded registry/staging state and atomically takes the actual window and exclusive mode leases before any EGL call. Invalid input, cancellation, reservation or allocation failure preserves all input slots and output. `stage_window` follows the same transfer rule for a future replacement. Once staging succeeds, subsequent driver failure leaves the producer responsible for that staged reference.
2. `start` runs on the actual GL pthread and performs checked display initialization, GLES API/config selection, context/window-Surface creation and make-current. Each successful physical object is recorded immediately. A public token appears only after actual current display/context/draw+read Surface, actual pthread and GLES3 checks succeed. A failed start retains partial objects and both root leases in the same quarantined owner.
3. `backend` supplies one stable `CohWrGpuLeaseBackend` and exact physical-lifetime token. Logical generations come from private monotonic records for successful owned EGL operations, never a Java epoch, texture name or raw handle alone. Old records distinguish a later context/Surface that reuses the same platform handle.
4. `enter_frame`/`leave_frame` cover every new-context GL pass, including wrapped generic renderer compile, program destruction, bind/draw and presentation/swap. Every operation authenticates actual current handles and pthread before GL. No unwrapped Support draw enters this context. Frame, upload and retirement gates are mutually exclusive.
5. `upload` owns the existing real `CohWrGpuJournal` and registered raw GPU staging slots. All raw uploads stay inventoried and retain registry lifetime. `seal_uploaded` calls the existing atomic `coh_wr_gpu_lease_adopt` on those slots; only successful full transfer empties them and transfers responsibility to the sealed set's registry pin. Failed seal preserves staged owners. This closes the upload-before-adoption interval.
6. `replace_surface`, `replace_context` and physical `close` run on the exact GL owner after root has stopped/abandoned the relevant presentation work. Control `collect` releases metadata and root leases only after physical objects, staged owners, journals, sealed sets and active/pending presentation responsibilities have retired. No control hold/drop deletes, frees or uploads GL resources.

Function names are provisional until the root typed producer interface is fixed. The semantics above are required; an opaque owner must not become a public struct of asserted generations or destruction booleans.

## Failure and lifetime rules

Every new GL call belongs to a normal-frame, upload or cleanup scope. A pending rollback journal or failed retirement quarantines the whole context, including other resource sets. Saved binding/unpack state cannot interleave with another pass. Stable registry pins cover the actual operations object and old destruction records through final disposition.

A failed begin-retirement acquires no gate. Failed end-retirement retains its acquired gate. Failure after a delete may have consumed the name; ownership and quarantine must remain until exact retry/disposition is known. No other pass may cause numeric name reuse during that uncertainty.

Failed creation or replacement publishes no candidate token. Physical EGL operations cannot always roll back to a working old Surface; the old token may remain only a historical record. Partial replacement retains old/staged objects, window references, gate and cleanup responsibility, and normal rendering remains stopped until exact recovery. Wrong thread or wrong current display/context/draw+read Surface refuses before GL.

Context death requires a checked successful unbind on its owning thread using `EGL_NO_CONTEXT` and `EGL_NO_SURFACE`, followed by actual current-context/draw/read checks confirming those empty values, and then successful producer-owned `eglDestroyContext`. The exclusive lease and gates must exclude any other thread making that context current throughout this sequence. Successful destruction of a still-current handle alone is insufficient because physical deletion can remain pending. All relevant owned operations and return values remain in that lifetime record. A failed query, missing current handle, Java lifecycle event, epoch change or integer alive flag cannot certify death. Old GPU metadata may use verified-dead retirement; it must never delete names in a new context that reused the same numeric names. Failed destroy/unbind/terminate preserves the owner, gate, journal and root leases for retry.

Context/Surface/upload records have explicit finite capacities. Exhaustion refuses rather than silently relabeling a record. A record is recycled only after verified physical death and all registry/GPU/presentation obligations disappear; globally distinct logical generations prevent stale copied tokens from matching a recycled slot.

## Budget and qualification limits

Root books all old/new source, CPU, GPU, renderer, staging, registry, window/provider/display and driver overlap under the existing named allowance. Fixed registry/slab/control reserves are charged before acquisition. Reference-count changes do not create capacity or automatically subtract historical peaks. Allocator overhead, platform/driver storage and process RSS are not inferred from nominal resource sizes.

The existing successful 602-check Android job is not rerun for this proposal. Any future qualification must distinguish actual owned application-window lifecycle from host controls, native compilation or another private pbuffer. No application integration, physical-device execution, current generation, world prerequisites, material/actor authority or world publication is claimed by this document.
