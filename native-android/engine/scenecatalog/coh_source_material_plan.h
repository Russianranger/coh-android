#ifndef COH_SOURCE_MATERIAL_PLAN_H
#define COH_SOURCE_MATERIAL_PLAN_H
#include "coh_source_sealed.h"
#include "../world-render-adapter/coh_wr_texopt.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_SOURCE_MATERIAL_SLOTS 16u
#define COH_SOURCE_MATERIAL_NAME 260u
typedef struct {size_t aggregate_limit,retained_bytes;} CohSourceMaterialBudget;
typedef struct {uint32_t present;char name[COH_SOURCE_MATERIAL_NAME];} CohSourceMaterialName;
typedef struct {
 uint32_t source_ordinal,source_part,texture_index,triangles;
 uint32_t graph_generation,catalog_generation,source_asset_generation;
 uint32_t historical_client_generation,texopt_ordinal,table_owner_ordinal;
 uint8_t resources_sha256[32],resource_record_sha256[32],texopt_cache_sha256[32];
 char partition_key[COH_SOURCE_MATERIAL_NAME],texopt_key[COH_SOURCE_MATERIAL_NAME];
 CohSourceMaterialName texopt_source_file;uint32_t texopt_source_age,texopt_flags,texopt_blend;
 CohSourceMaterialName slots[COH_SOURCE_MATERIAL_SLOTS];
 uint32_t fallback_enabled,original_CLIENT_postprocessed;
 size_t sealed_owned_bytes,shared_source_bytes,record_owned_bytes,aggregate_reserved_bytes,preparation_reserve;
 uint32_t effective_client_material,texture_bodies_verified,gpu_owner,live_generation_admitted,world_authority;
} CohSourceMaterialPlan;
/* Read-only exact-key association between one authentic sealed SOURCE partition
 * and one existing immutable historical CLIENT TexOpt record. Only a table-owner
 * record whose key equals the partition key (ASCII case-insensitive, NO extension
 * stripping/alias/default search) is supported. A miss is explicit; the caller
 * must use existing source-qualified cache_find/create to select that owner.
 * This is an inventory of all nullable postprocessed layer names and enabled
 * fallback dependencies, NOT texFindComposite, effective material selection or
 * proof that any texture body/default/namespace belongs to this model.
 *
 * Copies keys and identities only; no pointer, allocation, reference, I/O, GPU
 * reservation ticket or resource lease survives. Sealed's real source/graph and
 * record must stay live and immutable throughout this synchronous call. Their
 * ACTUAL allocations plus shared source tree, input/output and 32KiB call reserve
 * are charged before reading parts/names. retained_bytes must include ALL other
 * old/new/borrowed owners, candidate GPU/upload resources, scratch, allocator and
 * callback/compiler runtime peaks. Unknown resources cannot be supplied as zero
 * to claim a rendering admission. This entry creates no renderer candidate.
 * Unchanged 96MiB ceiling; failure preserves output. Controls must be disjoint
 * from opaque/borrowed owners; known owner/source spans and endpoints guarded.
 * Historical source/client generation labels remain separate, never joined.
 */
CohStatus coh_source_material_plan(const CohSourceSealed*,uint32_t,uint32_t,
 const CohWrTexOptRecord*,const CohSourceMaterialBudget*,CohSourceMaterialPlan*);
#ifdef __cplusplus
}
#endif
#endif
