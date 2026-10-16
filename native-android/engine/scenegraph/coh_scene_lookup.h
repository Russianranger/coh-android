#ifndef COH_SCENE_LOOKUP_H
#define COH_SCENE_LOOKUP_H
#include "../coh_contracts.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Native admission limits, not original engine maxima. ASCII only: original
 * locale-dependent case folding is qualified here only for printable ASCII. */
#define COH_SG_LOOKUP_NAME_CAP 999u
#define COH_SG_LOOKUP_PATH_CAP 260u
#define COH_SG_LOOKUP_FILES_MAX 8192u
#define COH_SG_LOOKUP_LIBRARIES_MAX 65536u
#define COH_SG_LOOKUP_MODELS_MAX 262144u
#define COH_SG_LOOKUP_BYTES_MAX (16u*1024u*1024u)
#define COH_SG_LOOKUP_AGGREGATE_MAX (96u*1024u*1024u)
#define COH_SG_LOOKUP_STACK_RESERVE 8192u
#define COH_SG_LOOKUP_PROBES_MAX 256u
enum {COH_SG_LOOKUP_FIXTURE=1,COH_SG_LOOKUP_CALLER_VERIFIED_INPUT=2};
enum {COH_SG_LOOKUP_NEEDS_PROVENANCE=1,COH_SG_LOOKUP_NEEDS_GEO=2,
      COH_SG_LOOKUP_NEEDS_TRICKS=4,COH_SG_LOOKUP_NEEDS_MATERIALS=8,
      COH_SG_LOOKUP_NEEDS_BOUNDS=16,COH_SG_LOOKUP_UNRESOLVED=31};
typedef struct {
    uint32_t generation,asset_generation,map_generation,input_kind;
    uint8_t source_sha256[32],inventory_sha256[32],manifest_sha256[32];
} CohSgLookupBinding;
typedef struct {
    uint32_t slot,asset_id,asset_generation;
    uint8_t payload_sha256[32];
    const char *library_path,*geo_path;
} CohSgLookupFile;
typedef struct {uint32_t slot,file_slot;const char *name;} CohSgLookupLibrary;
typedef struct {uint32_t file_slot,slot;const char *name;} CohSgLookupModel;
/* Original slots may have holes. Files/library rows must increase by slot;
 * model rows increase lexicographically by (file_slot, original model slot).
 * All arrays/strings remain immutable during build and are deeply copied.
 * The GEO path must equal the original changeFileExt rule, never a guessed
 * association. Input digests are caller assertions, not cryptographic proof. */
typedef struct {
    CohSgLookupBinding binding;
    const CohSgLookupFile *files;uint32_t file_count;
    const CohSgLookupLibrary *libraries;uint32_t library_count;
    const CohSgLookupModel *models;uint32_t model_count;
} CohSgLookupManifest;
typedef struct CohSgLookupIndex CohSgLookupIndex;
typedef struct {size_t aggregate_limit,retained_bytes;} CohSgLookupBudget;
typedef struct {size_t input_bytes,prior_bytes,candidate_bytes,stack_reserve,
    retained_bytes,aggregate_bytes;} CohSgLookupMemory;
typedef struct {
    CohSgLookupBinding binding;
    uint32_t library_slot,file_slot,model_slot,asset_id,asset_generation,unresolved;
    uint8_t payload_sha256[32];
    char geo_path[COH_SG_LOOKUP_PATH_CAP],model_name[COH_SG_LOOKUP_NAME_CAP];
} CohSgLookupMatch;
/* All output/control objects and borrowed input are disjoint caller storage.
 * *candidate must be NULL. Preparation runs off the render thread, with one
 * bounded allocation, no I/O and no callbacks. Failure changes no output.
 * Budget includes measured manifest arrays/strings + old/candidate allocation
 * payloads + conservative stack reserve + all caller-retained graphs/catalogs,
 * other retired indexes, raw assets/GPU views, scratch, and external evidence.
 * Allocator overhead/process RSS are not measured. No resource pins are owned.
 * Build from old requires exact next generation; fresh index starts at one.
 * Input backing-allocation slack, additional owners and metadata not described
 * by arrays/strings must be included in retained_bytes by the caller. */
CohStatus coh_sg_lookup_build(const CohSgLookupIndex *old,const CohSgLookupManifest *,
    const CohSgLookupBudget *,CohSgLookupIndex **candidate,CohSgLookupMemory *);
/* Caller serializes publication and readers. This swaps pointers and returns
 * the prior generation without freeing it. *retired must be NULL. Retirement
 * requires the complete prior binding, preventing cross-session publication
 * when independent owners both have generation one. Retirement requires
 * acknowledgement from every borrower before free; no thread-safe
 * mailbox, atomic machine instruction or renderer permission is implied. */
CohStatus coh_sg_lookup_publish(CohSgLookupIndex **current,CohSgLookupIndex **candidate,
    CohSgLookupIndex **retired);
void coh_sg_lookup_free(CohSgLookupIndex *);
size_t coh_sg_lookup_owned_bytes(const CohSgLookupIndex *);
/* Exact expected binding is mandatory. Result owns copied identifiers/names;
 * no pointers survive index retirement. Unknown/ambiguous/missing data never
 * substitutes defaults. Success proves name-table lookup only: every result
 * retains all unresolved bits, even CALLER_VERIFIED_INPUT. No draw admission. */
CohStatus coh_sg_lookup_find(const CohSgLookupIndex *,const CohSgLookupBinding *,
    const char *model_name,CohSgLookupMatch *);
/* Compare a subsequently acquired asset identity with the recorded identity.
 * Caller must independently verify actual payload bytes and retain their pin.
 * This comparison does not clear unresolved bits. */
CohStatus coh_sg_lookup_asset_matches(const CohSgLookupMatch *,uint32_t asset_id,
    uint32_t asset_generation,const uint8_t payload_sha256[32]);
#ifdef __cplusplus
}
#endif
#endif
