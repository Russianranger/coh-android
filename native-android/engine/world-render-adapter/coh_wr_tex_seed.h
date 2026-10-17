#ifndef COH_WR_TEX_SEED_H
#define COH_WR_TEX_SEED_H
#include "coh_wr_texopt.h"
#include "coh_wr_tex_basic_lookup.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_WR_TEX_SEED_DEPENDENCIES 16u
enum {COH_WR_TEX_SEED_NO_BASE1=0,COH_WR_TEX_SEED_NAME_MATCHES_BASE1=1,COH_WR_TEX_SEED_CREATE_CANDIDATE=2};
typedef struct {size_t aggregate_limit,external_bytes;uint32_t guarded_short_key_policy;} CohWrTexSeedLimits;
typedef struct {uint32_t source_slot,header_ordinal,format_flags;char key[128];uint8_t header_sha256[32];} CohWrTexSeedDependency;
typedef struct {
 uint32_t classification,source_ordinal,table_owner_ordinal,historical_input_generation,query_count,guarded_short_key_policy;
 uint8_t cache_sha256[32];CohWrTexSeedDependency dependencies[COH_WR_TEX_SEED_DEPENDENCIES];
 size_t aggregate_reserved_bytes;
} CohWrTexSeed;
/* Initial trickCreateTextures SOURCE eligibility for one existing immutable,
 * postprocessed historical TexOpt record, using existing exact imported headers.
 * No Base1 skips; case-insensitive Base1 name PREFIX also skips (not a normalized
 * filename equality). Valid layers0..12 precede enabled fallback base/blend/bump.
 * Every required lookup must be positively observed in the imported subset.
 * Unknown subset lookup returns COH_NOT_FOUND, never original-table absence or
 * delayed-load/error eligibility. Original unsafe short keys return UNSUPPORTED
 * unless guarded_short_key_policy explicitly selects the separately qualified
 * repair. No old-base entry is admitted (original assertion requires NULL).
 * CREATE_CANDIDATE is only the original source call's conditional eligibility;
 * it creates no TexBind, resource/default, namespace, LWC state or current
 * generation. Real default identities and live enumeration remain external.
 * Borrowed record/inputs/loader remain immutable and live for this call. Result
 * copies ordinals/keys/hashes, owns no resource/pin/lease. external_bytes covers
 * record owned bytes + inputs owned bytes + WHOLE configured loader reservation
 * + old16KiB input control + other owners/provider/runtime/compiler peaks.
 * Adds32KiB own control +16KiB nested Basic reserve before polls/queries; named
 * budgets do not establish process RSS or allocator closure. All failures leave
 * output unchanged; output aliases with limits, record, input owner/bodies refuse.
 * Header ordinals remain meaningful only with that same still-live input owner.
 */
CohStatus coh_wr_tex_seed(const CohWrTexOptRecord*,const CohWrTexInputs*,const CohWrTexSeedLimits*,CohCancel,CohWrTexSeed*);
#ifdef __cplusplus
}
#endif
#endif
