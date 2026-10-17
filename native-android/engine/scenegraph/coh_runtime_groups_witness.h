#ifndef COH_RUNTIME_GROUPS_WITNESS_H
#define COH_RUNTIME_GROUPS_WITNESS_H
#include "coh_runtime_groups.h"
#define COH_GROUPS_WITNESS_FIXED_SCRATCH_BYTES (128u*1024u)
#define COH_GROUPS_WITNESS_RECORD_BYTES 64u
#define COH_GROUPS_WITNESS_INPUT_MAX ((2u+4096u+65536u+65536u)*64u)
typedef struct CohRuntimeGroupsWitness CohRuntimeGroupsWitness;
typedef struct {
 uint32_t graph_generation,catalog_generation,observation_id;
 uint32_t map_generation,selection_generation,selected_dbid;
 uint8_t witness_sha256[32],packet_sha256[32],session_sha256[32];
 uint8_t catalog_sha256[32],snapshot_sha256[32],source_sha256[32],run_sha256[32];
} CohRuntimeGroupsWitnessBinding;
typedef struct {size_t owned_limit,aggregate_limit,retained_bytes;} CohRuntimeGroupsWitnessBudget;
typedef struct {
 size_t owned_bytes,aggregate_reserved_bytes;
 uint32_t records,files,slots,roots,eligible_definitions,saved_omissions,time_omissions;
 uint32_t source_generation_admitted,world_authority;
} CohRuntimeGroupsWitnessReport;
/* Preparation-side immutable copy of exact fixed64-byte PRE-producer records
 * from source_groups_eligibility.inc and the exact normalized reader allocation.
 * Digest callback must compute real SHA256 over owned bytes, not return pins.
 * Binding provenance/session labels are externally authenticated input, never
 * evidence established by this parser. Synthetic labels confer no authority.
 * CatalogOwner is retained; graph + borrowed snapshot owner remain caller-held
 * and immutable until final release. Exact actual graph pointer/source spans
 * and recorded catalog/snapshot/source/run pins must match, not just labels.
 * All controls/known source/input spans must be pairwise disjoint; opaque owner,
 * graph and digest context allocations are caller-disjoint. Caller serializes
 * refs/access/retirement. *out must be NULL. On any refusal out/report unchanged.
 * Limits cover named graph/catalog/snapshot/input/copied payload and128KiB stack
 * reserve. Only raw snapshot.size is automatically charged: retained_bytes MUST
 * add its actual SnapshotOwner metadata/index/allocation slack beyond that raw
 * span, plus every other hidden dependency, opaque graph/digest context, owner
 * and digest scratch/slack. No complete SnapshotOwner reservation is inferred.
 * Narrow initial scope: full NEW_WORLD, every normal file present, all root
 * slots emitted. Source saved omission may affect ANY file, including file0.
 * No CLIENT saved-file import, real live generation, assets, actor or ACK permit.
 */
CohStatus coh_runtime_groups_witness_create(const CohRuntimeGraph *,CohCatalogOwner *,
 CohBytes records,const CohRepReader *,const CohRuntimeGroupsWitnessBinding *,
 const CohRuntimeGroupsWitnessBudget *,const CohCatalogDigest *,
 CohRuntimeGroupsWitness **out,CohRuntimeGroupsWitnessReport *);
/* Actual immutable allocation payload only, not retained source dependencies. */
size_t coh_runtime_groups_witness_owned_bytes(const CohRuntimeGroupsWitness *);
CohStatus coh_runtime_groups_witness_retain(CohRuntimeGroupsWitness *);
void coh_runtime_groups_witness_release(CohRuntimeGroupsWitness *);
/* Optional compatibility extension; original compare_groups is unchanged.
 * Expected binding must exactly equal retained binding; actual graph/owner must
 * be the retained identities. Reader bytes/bounds/cursor/compression must match
 * the immutable copied packet. Every eligible definition must emit exactly
 * once in original slot order, every omitted definition must be source-ineligible.
 * This does not prove saved CLIENT imports or a same-generation live session.
 * Reader/report unchanged on every failure. No allocations; caller charges all
 * other live resources in budget.retained_bytes. Known controls disjoint.
 */
CohStatus coh_runtime_graph_compare_groups_witness(const CohRuntimeGraph *,const CohCatalogOwner *,
 const CohRuntimeGroupsWitness *,const CohRuntimeGroupsWitnessBinding *,const CohRepReader *,
 const CohRuntimeGroupsBudget *,CohRuntimeGroupsReport *);
#endif
