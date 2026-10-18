#ifndef COH_WR_TEX_DEFAULTS_H
#define COH_WR_TEX_DEFAULTS_H
#include "coh_wr_tex_namespace.h"
#ifdef __cplusplus
extern "C" {
#endif

typedef struct CohWrTexDefaults CohWrTexDefaults;
enum {
 COH_WR_TEX_DEFAULT_WHITE, COH_WR_TEX_DEFAULT_GREY,
 COH_WR_TEX_DEFAULT_INVISIBLE, COH_WR_TEX_DEFAULT_BLACK,
 COH_WR_TEX_DEFAULT_BUMP, COH_WR_TEX_DEFAULT_DYNAMIC_CUBE,
 COH_WR_TEX_DEFAULT_BUILDING_LIGHTS, COH_WR_TEX_DEFAULT_COUNT
};
enum { COH_WR_TEX_DEFAULT_REQUIRED_MASK=35,
       COH_WR_TEX_DEFAULT_PREPARATION_RESERVE=16384 };
typedef struct { uint32_t cold_initial,guarded_short_keys; } CohWrTexDefaultsProfile;
typedef struct { size_t owned_limit,aggregate_limit,external_bytes; } CohWrTexDefaultsLimits;
typedef struct {
 uint32_t selected_mask,selected_count,source_input_generation,basic_rows;
 uint32_t cold_initial,guarded_short_keys,unresolved_client_semantics;
 size_t owned_bytes,aggregate_reserved_bytes;
} CohWrTexDefaultsReport;
typedef struct {
 CohWrTexNamespaceBasic source;
 uint32_t effective_basic_flags;
} CohWrTexDefaultsBasic;

/* Whole cold texFindNeededBinds operation over ONE real namespace, with the
 * already qualified texFixName short-key guard. Both profile fields must be1.
 * Original bare white/grey/black read before their arrays: their guarded keys
 * are explicit repaired policy, not unchanged legacy semantics. The selected
 * white/grey/dynamic-cube assertion is a native refusal if any is missing;
 * optional missing roles stay absent. No guessed fallback is introduced.
 *
 * The immutable effective view clears TEX_ALPHA on the selected invisible ROW,
 * including every alias of that row; all other rows keep initial flags. The
 * underlying namespace is unchanged. Consumers of this phase must use this
 * effective view, not its source.initial_basic_flags. This is not texSetBinds,
 * sampler reset, permutations, composites, material or original/current CLIENT
 * table authority. The caller supplies an actual cold initial scan snapshot;
 * warm/reload/LWC state is outside this operation's admitted domain.
 *
 * All calls use the namespace's one owner thread. The source and provider stay
 * immutable; callbacks may not destroy them or change current inputs/output.
 * During acquire the namespace's busy guard refuses callback access. At the
 * final direct poll the candidate's real pins protect the source; an unrelated
 * default owner can then retire its own pins. Such external retirement is not
 * rolled back or restored on candidate failure. The
 * owner holds one actual existing namespace body lease per selected role; those
 * pins prevent namespace destruction. It adds no provider hold/identity. Every
 * returned metadata/body view is borrowed until this owner is destroyed.
 *
 * external_bytes must cover at least the source's FULL recorded aggregate
 * reservation, including its configured loader, provider/input/context and any
 * still-live predecessor reservations. Additional live owners/runtime peaks
 * remain caller-charged. New owner, input/control spans and16KiB preparation
 * reserve are added before allocation, cancellation/digest/read callbacks or
 * body acquisition. No RSS/global-budget or actual-current namespace proof.
 *
 * *out must be NULL; failures preserve output and release all partial leases
 * under these owner-thread/immutability preconditions. Independent owner actions
 * are outside output-preservation/rollback claims. Inputs/outputs must be
 * disjoint from opaque source/provider storage. Exposed source metadata/body
 * spans and local owner/config spans are additionally checked. Caller inputs
 * and output slot may not change during a call. No external callback occurs
 * during release. Destroy attempts all releases and preserves a still-owned
 * handle on any release refusal; successful releases are not repeated.
 */
CohStatus coh_wr_tex_defaults_build(CohWrTexNamespace*,const CohWrTexDefaultsProfile*,const CohWrTexDefaultsLimits*,CohCancel,CohWrTexDefaults**);
CohStatus coh_wr_tex_defaults_report(const CohWrTexDefaults*,CohWrTexDefaultsReport*);
CohStatus coh_wr_tex_defaults_basic(const CohWrTexDefaults*,uint32_t,CohWrTexDefaultsBasic*);
CohStatus coh_wr_tex_defaults_role(const CohWrTexDefaults*,uint32_t,CohWrTexDefaultsBasic*);
CohStatus coh_wr_tex_defaults_body(const CohWrTexDefaults*,uint32_t,CohBytes*);
CohStatus coh_wr_tex_defaults_destroy(CohWrTexDefaults**);
#ifdef __cplusplus
}
#endif
#endif
