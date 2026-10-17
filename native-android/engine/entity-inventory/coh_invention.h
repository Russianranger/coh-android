#ifndef COH_ENTITY_INVENTION_H
#define COH_ENTITY_INVENTION_H
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_INVENTION_SLOTS 10u
#define COH_INVENTION_POWERUPS 10u
#define COH_INVENTION_CONCEPTS_PER_SLOT 64u
#define COH_INVENTION_CONCEPTS_MAX (COH_INVENTION_SLOTS*COH_INVENTION_CONCEPTS_PER_SLOT)
#define COH_INVENTION_RAM_MAX (8u*1024u*1024u)
#define COH_INVENTION_STACK_RESERVE 4096u
typedef struct {uint32_t type,id,filled;}CohInventionPowerup;
typedef struct {uint32_t id,variable_words[4];}CohInventionConcept;
typedef struct {uint32_t state,concept_first,concept_count;}CohInventionSlot;
typedef struct {
 uint32_t status_change,state,recipe_id,boost_inventory_index,variable_words[4];
 CohInventionPowerup powerups[COH_INVENTION_POWERUPS];
 CohInventionSlot slots[COH_INVENTION_SLOTS];
 uint32_t concept_count;CohInventionConcept concepts[COH_INVENTION_CONCEPTS_MAX];
 uint32_t original_consumer_compatible;
 size_t begin_bit,end_bit;
}CohInventionUpdate;
typedef struct {CohInventionUpdate candidate;}CohInventionWorkspace;
/* Complete active ORIGINAL PRODUCER grammar for diagnosis, not original
 * consumer-equivalent application. Original invention_Receive is a no-op:
 * any nonzero status_change leaves producer data unread in that consumer.
 * Therefore original_consumer_compatible derives true ONLY for status0.
 * This API consumes all producer bytes and records raw metadata even for active
 * state; callers must never treat that as live interoperability or state/ACK
 * permission. The combined phase API refuses every nonzero status_change.
 * Raw unknown states/IDs are retained. Counts64per-slot/640aggregate are local
 * refusal limits. Float words must be finite. All spans disjoint; caller heap/
 * arena, no allocation. Budget charges entire input+bothPODs+stack+retained.
 * Refusal preserves reader/output; workspace private scratch. No actor/ACK. */
CohStatus coh_invention_update_read(CohRepReader *,CohInventionUpdate *,
 CohInventionWorkspace *,size_t budget,size_t retained_bytes);
#ifdef __cplusplus
}
#endif
#endif
