#ifndef COH_INITIAL_CREATE_PROBE_H
#define COH_INITIAL_CREATE_PROBE_H
#include "../entities/coh_entities.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef enum {
 COH_INITIAL_PROBE_INPUT=1,COH_INITIAL_PROBE_HEADER,COH_INITIAL_PROBE_INDEX,
 COH_INITIAL_PROBE_CREATE,COH_INITIAL_PROBE_RECORD_BODY,COH_INITIAL_PROBE_EMPTY_LIST
} CohInitialCreateProbeStage;
typedef struct {
 CohStatus status;CohInitialCreateProbeStage stage;
 size_t header_end_bit,create_end_bit,failure_bit;
 uint32_t header_validated,create_validated,entity_index,entity_type,is_self,
  self_dbid_matches_handoff;
 CohEntFailure entity_failure;
} CohInitialCreateProbe;
/* Diagnostic only: post_command is the immutable synchronous ALLENTS loan at
 * its post-command cursor, not its post-header cursor. The enclosing observer
 * obtains selected_dbid from its actual owned DB/Map handoff. A supplied scalar
 * is not an ownership certificate. All inputs and the numeric report must be
 * disjoint; invalid API inputs leave the report unchanged.
 *
 * Reuses the original-layout header, delta and complete entSendCreate grammar.
 * It deliberately stops before the first record's remaining body. Self need
 * not be first; never scan for another delta/DBID. Even a matching self create
 * proves neither list uniqueness nor a complete character/source generation.
 * Returns UNSUPPORTED at RECORD_BODY on successful prefix inspection, or the
 * first syntax/profile refusal. An absent remaining body is INVALID there.
 * Child transactional header failures report the rejected header's start;
 * entity failures carry the child's precise cursor. No packet/name/DBID,
 * pointer, actor, authority or application ACK permit is retained or granted.
 * No allocation; existing 4MiB reader cap and fixed child string limits apply.
 */
CohStatus coh_initial_create_probe(const CohRepReader *post_command,
 const CohRepSchema *,uint32_t selected_dbid,CohInitialCreateProbe *);
#define COH_INITIAL_PROBE_REPORT_MAX 1024u
/* Fixed diagnostic projection; zero stage renders null before observation. */
int coh_initial_create_probe_json(const CohInitialCreateProbe *,char *,size_t);
#ifdef __cplusplus
}
#endif
#endif
