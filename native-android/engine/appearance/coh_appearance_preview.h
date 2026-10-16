#ifndef COH_APPEARANCE_PREVIEW_H
#define COH_APPEARANCE_PREVIEW_H
#include "../coh_contracts.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct CohAppearancePreview CohAppearancePreview;
typedef struct {
 uint64_t frames,draws,surface_uploads,failures;
 /* owned_cpu_bytes covers this owner/arenas, excluding backend CPU objects.
  * texture_bytes is retained RGBA source payload, including the white binding;
  * it is not active GPU residency. gpu_buffer_bytes becomes zero on loss. */
 size_t owned_cpu_bytes,borrowed_package_bytes,gpu_buffer_bytes,texture_bytes;
 uint32_t surface_generation,parts,vertices,indices;
} CohAppearancePreviewStats;
/* One serialized owner. create/destroy may allocate; create performs no GL/IO.
 * Package must be SHA-authenticated against prepared manifest by the asset owner,
 * remain immutable and outlive this object. No replacement or synthetic assets.
 * Native structural bounds are independently checked before publication.
 * out must point to NULL; failure never replaces an existing owner. */
CohStatus coh_appearance_preview_create(CohBytes,CohAppearancePreview **);
/* GL thread: caller binds its destination framebuffer first. Clears that frame
 * and renders complete neutral Male source-menu costume with a fixed camera.
 * First frame/new context creates GPU storage; steady frames allocate no heap,
 * read no assets, perform no readback/fence/glFinish, and send no network data.
 * seconds is local preview time, not authoritative or gameplay animation. */
CohStatus coh_appearance_preview_draw(CohAppearancePreview *,uint32_t width,
 uint32_t height,uint32_t surface_generation,double seconds);
/* GL owner only. If the old context is gone, pass 0: old numeric GL names must
 * never be deleted in its replacement. CPU source resources survive either. */
void coh_appearance_preview_surface_lost(CohAppearancePreview *,int context_alive);
void coh_appearance_preview_destroy(CohAppearancePreview *,int context_alive);
/* Same owner thread, or after it has stopped. Copy under the application's
 * snapshot lock; never call concurrently with draw/lost/destroy. */
CohAppearancePreviewStats coh_appearance_preview_stats(const CohAppearancePreview *);
#ifdef __cplusplus
}
#endif
#endif
