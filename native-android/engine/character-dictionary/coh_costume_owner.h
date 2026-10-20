#ifndef COH_COSTUME_OWNER_H
#define COH_COSTUME_OWNER_H
#include "../costume-import/coh_costume_import.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_COSTUME_OWNER_BODY_MAX 65536u
#define COH_COSTUME_OWNER_LEASE_MAX 16u
#define COH_COSTUME_OWNER_STACK_RESERVE 16384u
typedef struct CohCostumeOwner CohCostumeOwner;
typedef struct {
 CohBytes packet;size_t bit_length;uint32_t compressed;
 const void *loan_owner,*session_owner,*source_owner,*generation_owner;
 uint32_t generation;
} CohCostumePacketBinding;
typedef struct {
 uint8_t payload_sha256[32],source_sha256[32],build_sha256[32],profile_sha256[32],run_sha256[32];
} CohCostumeBodyPins;
typedef struct {
 CohCostumeOwner *owner;uint32_t slot;uint64_t serial;
} CohCostumeOwnerLease;
typedef struct {
 const CohEntCostumeDictionary *dictionary;
 CohBytes body_witness,bodytype_definitions;
 uint32_t body_parts,body_types;
 /* This view is candidate data, not permission for a live packet. */
} CohCostumeOwnerView;
typedef struct {
 CohCostumeImportReceipt dictionary;
 size_t owner_bytes,body_witness_bytes,charged_peak_bytes;
 uint32_t body_parts,body_types;
 /* All candidates remain unadmitted; no self-certified provenance field. */
} CohCostumeOwnerReceipt;
/* Host/off-thread immutable CANDIDATE. Fully copies COHBW1 ordered rows and
 * imports all original COHCDI1 slots using the existing importer. Expected pins
 * are independent integrity expectations, never runtime provenance proof.
 * Profile/run equality checks label coherence only. Full row/dictionary source
 * relation is unproved and therefore cannot activate this owner. No authentic
 * runtime producer lease or active-owner constructor exists in this module.
 * All direct spans and digest context are disjoint, fixed and immutable for
 * the whole call. Digest has the existing importer's qualification contract.
 * budget<=8MiB includes old/current/candidate/dependency/callback/scratch/source
 * storage supplied in retained, fixed metadata, original inputs, maximum new
 * dictionary, temporary slots and stack reserves BEFORE callback/allocation.
 * Output/receipt commit together. No parent ledger ticket is fabricated. */
CohStatus coh_costume_owner_candidate(CohBytes dictionary,CohBytes body,
 const CohCostumeImportPins *,const CohCostumeBodyPins *,
 const CohCostumeImportDigest *,CohCostumeOwner **,CohCostumeOwnerReceipt *,
 size_t budget,size_t retained);
/* Offline data leases pin owned dictionary/rows; never source/runtime leases.
 * Synchronous serial coordinator only; no concurrent mutation/destroy calls.
 * lease must be zero-initialized before its first borrow; its fields then stay
 * unchanged except through these calls; storage identity is retained until
 * release, so moving/copying the token cannot release the original borrow.
 * A lease may be
 * released once. Caller must not use pointers after release. Opaque owners
 * must be live objects returned here, not arbitrary/forged addresses. */
CohStatus coh_costume_owner_borrow(CohCostumeOwner *,CohCostumeOwnerLease *,CohCostumeOwnerView *);
CohStatus coh_costume_owner_release(CohCostumeOwnerLease *);
CohStatus coh_costume_owner_retire(CohCostumeOwner *);
CohStatus coh_costume_owner_destroy(CohCostumeOwner **);
/* Atomic offline candidate replacement; borrowed old owners refuse before
 * any mutation. No reconnect/reload can silently inherit an admitted owner. */
CohStatus coh_costume_owner_replace(CohCostumeOwner **,CohCostumeOwner **);
size_t coh_costume_owner_bytes(const CohCostumeOwner *);
/* Validation only: COH_OK carries no admission/authority. Validates endpoints
 * and rejects overlap with every owned immutable allocation, static source
 * definitions and actual active lease storage. NULL owner permits ordinary
 * absent-catalog diagnostics. */
CohStatus coh_costume_owner_output_disjoint(const CohCostumeOwner *,const void *,size_t);
/* Exact packet descriptor is necessary but insufficient for runtime admission.
 * NULL owner -> NOT_FOUND; retired -> STATE; valid candidate -> UNSUPPORTED.
 * Counts are unchanged on every refusal. No packet bytes/pointer are retained.
 * There is deliberately no hash/label/boolean path to a successful live query.
 * A future independently authenticated producer lease must provide the actual
 * loaded rows+dictionary relation and source/session/generation/loan lifetime. */
CohStatus coh_costume_owner_query(const CohCostumeOwner *,const CohCostumePacketBinding *,
 uint32_t *body_parts,uint32_t *body_types);
#ifdef __cplusplus
}
#endif
#endif
