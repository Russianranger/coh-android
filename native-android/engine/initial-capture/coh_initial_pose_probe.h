#ifndef COH_INITIAL_POSE_PROBE_H
#define COH_INITIAL_POSE_PROBE_H
#include "../entities/coh_entities.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef enum {
 COH_INITIAL_POSE_INPUT=1,COH_INITIAL_POSE_FLAGS,COH_INITIAL_POSE_MODE,
 COH_INITIAL_POSE_POSITION,COH_INITIAL_POSE_ORIENTATION,COH_INITIAL_POSE_SEQUENCE
} CohInitialPoseStage;
typedef struct {
 CohStatus status;CohInitialPoseStage stage;
 size_t begin_bit,flags_end_bit,mode_end_bit,position_end_bit,pose_end_bit,failure_bit;
 uint32_t flags_validated,mode_validated,position_validated,
  orientation_validated,pose_validated;
 CohEntFailure entity_failure;
} CohInitialPoseProbe;
/* Diagnostic INITIAL full-create profile only. The enclosing exact ALLENTS
 * observer first validates header/index/entSendCreate, then loans body_start
 * with cursor at create_end_bit and the actual transport message_id. Neither
 * caller-supplied offsets nor a packet-order ID grant actor/session ownership.
 * No dictionary or generation number is synthesized.
 *
 * Decode rare flags -> mode -> absolute position -> complete quaternion using
 * fresh scratch and existing position/orientation parsers. Create positions
 * have no interpolation-extra flag. Source requires all three rare flags,
 * mode update, position mask7 and quaternion mask7. Partial/delta profiles
 * refuse; no previous actor baseline is invented. Stop BEFORE sequence body.
 * Successful pose returns UNSUPPORTED/SEQUENCE, or INVALID there if no next
 * bits exist. No strings, raw pose/mode values, packet pointers/IDs or actor
 * state survive in the numeric report. Inputs are immutable on every return.
 * Invalid API inputs/overlaps leave output unchanged; syntax/profile refusals
 * initialize it. Position helper failures identify the atomic child's start;
 * orientation failures retain its precise child failure cursor.
 * No allocation; preserve existing4MiB decoded cap and fixed report limit.
 */
CohStatus coh_initial_pose_probe(const CohRepReader *body_start,
 uint32_t actual_packet_id,CohInitialPoseProbe *);
#define COH_INITIAL_POSE_REPORT_MAX 1024u
int coh_initial_pose_probe_json(const CohInitialPoseProbe *,char *,size_t);
#ifdef __cplusplus
}
#endif
#endif
