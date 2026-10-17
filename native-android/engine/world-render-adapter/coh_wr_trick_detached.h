#ifndef COH_WR_TRICK_DETACHED_H
#define COH_WR_TRICK_DETACHED_H
#include "coh_wr_trick.h"
typedef struct CohWrTrickDetached CohWrTrickDetached;
typedef struct{size_t owned_limit,aggregate_limit,loader_reservation,external_bytes;}CohWrTrickDetachedLimits;
typedef struct{CohWrTrickReport source_admission;uint8_t retained_sha256[32];size_t source_offset,retained_bytes,owned_bytes,preparation_aggregate_reserved_bytes,preparation_loader_reservation;}CohWrTrickDetachedReport;
/* Copies exact count/length-prefixed Trick suffix; no record reencoding. On final
 * SUCCESS only consumes/releases *source and publishes *out. All failure paths
 * preserve both outputs and balance candidate pins. Source must be an immutable
 * qualified old owner; loader provider/digest/limits stay immutable throughout.
 * Configure loader TOTAL limit<=loader_reservation before entry; historical peak
 * is checked too. external_bytes covers old source owned bytes+its WHOLE loader
 * reservation+32KiB old stack/statics, other dictionaries/owners, provider/digest/
 * runtime peaks. New whole loader reservation, metadata+suffix and32KiB own
 * reserve charged before allocation/acquire. Same-loader reservations deliberately
 * double charge. Run preparation before unrelated GEO/graph peaks when possible.
 * No loader/cache/source lifetime remains after SUCCESS. Other owners (especially
 * TexOpt) can still pin the whole cache; actual release depends on retiring ALL.
 * Views are borrowed byte spans owned by detached owner, never C strings. Old
 * views of the consumed source become invalid. Historical provenance only; no
 * current CLIENT generation/animation/material/world permission is introduced. */
CohStatus coh_wr_trick_detach(CohAssetLoader*,CohWrTrickCache**,CohWrTexOptDigest,void*,const CohWrTrickDetachedLimits*,CohCancel,CohWrTrickDetached**);
void coh_wr_trick_detached_release(CohWrTrickDetached**);
CohStatus coh_wr_trick_detached_report(const CohWrTrickDetached*,CohWrTrickDetachedReport*);
CohStatus coh_wr_trick_detached_source_bytes(const CohWrTrickDetached*,CohBytes*);
CohStatus coh_wr_trick_detached_find(const CohWrTrickDetached*,const char*,uint32_t*);
CohStatus coh_wr_trick_detached_view(const CohWrTrickDetached*,uint32_t,CohWrTrickView*);
CohStatus coh_wr_trick_detached_numeric_projection(const CohWrTrickDetached*,uint32_t,CohWrTrickView*);
CohStatus coh_wr_trick_detached_stanim(const CohWrTrickDetached*,uint32_t,uint32_t,CohWrTrickStAnim*);
CohStatus coh_wr_trick_detached_autolod(const CohWrTrickDetached*,uint32_t,uint32_t,CohWrTrickAutoLOD*);
#endif
