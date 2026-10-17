#ifndef COH_CATALOG_SEED_H
#define COH_CATALOG_SEED_H
#include "coh_runtime_groups_witness.h"
typedef struct {
 uint32_t node,file,slot,external,in_use,emitted;
 CohBytes wire;size_t wire_bits;unsigned aligned;
} CohCatalogSeedRecord;
typedef CohStatus (*CohCatalogSeedVisit)(void *,const CohCatalogSeedRecord *);
typedef struct {
 uint32_t files,allocated_definitions,active_definitions,tombstones,omitted_definitions;
 uint32_t applied_equal_updates,captured_future_records,definitions_crc_verified,references_crc_verified;
 size_t aggregate_reserved_bytes;
 uint32_t protocol_wire_inputs_complete,client_derived_state_complete,bounds_cache_checksums_recomputed;
 uint32_t source_generation_admitted,world_authority;
} CohCatalogSeedReport;
/* Complete source serialization seed, not a CLIENT GroupDef memory image.
 * First validates immutable witness + full GROUPS compatibility, then stages a
 * bounded per-node emitted mask and visits EVERY allocated catalog record and
 * observed external future in graph order. Exact equal updates over this full
 * catalog leave the logical sendDef-visible input unchanged. Omitted records
 * are retained; no original CLIENT cache execution is required to possess those
 * raw protocol inputs. CLIENT-derived/trick/material/LOD/loader state is separate.
 *
 * Caller retains graph/source/witness/catalog leases for the entire synchronous
 * call. scratch_capacity >=graph.nodes, fully charged even when larger. Scratch
 * may change on ANY return; callback spans borrow immutable source bytes only
 * until return. Callback may write only its private staging context, never sources, controls
 * or scratch; it can stage bytes but must discard its ENTIRE stage on
 * ANY error; report commits only after every callback succeeds. No allocations.
 * No callback until complete packet/witness validation. All known source,
 * control, scratch and reader spans disjoint; opaque graph/witness/owner/digest
 * and callback allocations must additionally be disjoint by caller contract.
 * Budget.retained_bytes adds full hidden SnapshotOwner metadata/slack beyond
 * automatically charged raw span and every other owner/callback reservation.
 */
CohStatus coh_catalog_seed_visit(const CohRuntimeGraph *,const CohCatalogOwner *,
 const CohRuntimeGroupsWitness *,const CohRuntimeGroupsWitnessBinding *,const CohRepReader *,
 const CohRuntimeGroupsBudget *,uint8_t *scratch,size_t scratch_capacity,
 CohCatalogSeedVisit,void *context,CohCatalogSeedReport *);
/* Original bounds cache Adler32 input is raw sizeof(GroupBounds)==60 bytes,
 * including bitfield/padding bytes, followed by public name WITHOUT NUL, in
 * original file-slot order. Named-field/derived bounds are not substitutes.
 * Caller authenticates the raw Win32 source layout and actual file ownership.
 * File0 is refused: original objectLibraryWriteBoundsFileIfDifferent returns
 * without computing its checksum. Other source rows <=65536, names bounded
 * ASCII, raw bytes only interpreted as bytes (NaNs/padding preserved).
 * This pure check grants no source/asset/world authority. Report unchanged on
 * error or mismatch. Source rows/names/raw spans must stay immutable; report
 * must not overlap any known input span. No allocations or callbacks.
 */
typedef struct {const char *name;CohBytes raw_bounds;uint32_t in_use;} CohSourceBoundsChecksumRow;
typedef struct {uint32_t checksum,public_records;size_t bytes_hashed;} CohSourceBoundsChecksumReport;
CohStatus coh_source_bounds_checksum(uint32_t file_index,const char *file_name,
 const CohSourceBoundsChecksumRow *,size_t rows,uint32_t expected,CohSourceBoundsChecksumReport *);
#endif
