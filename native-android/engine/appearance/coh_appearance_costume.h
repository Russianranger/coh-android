#ifndef COH_APPEARANCE_COSTUME_H
#define COH_APPEARANCE_COSTUME_H
#include "coh_appearance.h"
#include "../entities/coh_original_costume_receive.h"
#ifdef __cplusplus
extern "C" {
#endif
/* The ordinary source BodyPart definitions stay in original catalog order.
 * Existence probes use the caller's actual source inventory. No body type,
 * model, texture, neutral rig or prior costume is selected as a fallback. */
typedef struct {
 const CohAppearancePartDef *definitions;uint32_t definition_count,generation;
 const char *const *chest_links;uint32_t chest_link_count;
 CohAppearanceProbe probe;void *probe_context;CohCancel cancel;
} CohAppearanceCostumeInputs;
/* Fixed off-stack staging. Borrowed snapshot pointers exist only during the
 * call and are cleared before return. Assembly output contains copied names.
 * Charge this arena, snapshot, source assets, old/new rendered owners and
 * native stack to their existing 8 MiB initial / 96 MiB scene domains; this is
 * no allocation, resource admission or renderer publication operation. */
typedef struct {
 CohAppearanceWorkspace assembly;
 CohAppearanceRequest request;
 CohAppearancePart parts[30];
} CohAppearanceCostumeWorkspace;
typedef struct {
 CohAppearanceBody body;
 CohAppearanceDiagnostics assembly;
 size_t workspace_bytes;
} CohAppearanceCostumeDiagnostics;
/* Feed one complete original-receiver snapshot directly to the established
 * changeGeo/texture-selection adapter. Part index remains BodyPart index;
 * packet colors are unpacked explicitly in source little-endian RGBA order.
 * Scales and FX remain retained in the input for the sequencer/FX owner; this
 * function selects assets only, never claims an actor or applies fake morphs.
 * out/count/diagnostics are unchanged on failure. All output and workspace
 * spans must be disjoint from each other and from borrowed input storage. */
CohStatus coh_appearance_costume_assemble(const CohOriginalCostumeSnapshot *,
 const CohAppearanceCostumeInputs *,CohAppearanceCostumeWorkspace *,
 CohAppearanceDraw *,size_t capacity,size_t *count,
 CohAppearanceCostumeDiagnostics *);
#ifdef __cplusplus
}
#endif
#endif
