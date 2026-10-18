#ifndef COH_INITIAL_CAPTURE_H
#define COH_INITIAL_CAPTURE_H
/* NONSHIPPING only. Diagnostic replacement Map/Local translation units include
 * the unchanged ordinary sources. Never add these TUs to a default build. */
#include "../local/coh_local.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct CohInitialCapture CohInitialCapture;
typedef enum { COH_INITIAL_CAPTURE_IDLE,COH_INITIAL_CAPTURE_CONNECTING,
 COH_INITIAL_CAPTURE_WAIT_GROUPS,COH_INITIAL_CAPTURE_WAIT_ALLENTS,
 COH_INITIAL_CAPTURED,COH_INITIAL_CAPTURE_FAILED,COH_INITIAL_CAPTURE_CANCELLED,
 COH_INITIAL_CAPTURE_CLOSED } CohInitialCapturePhase;
typedef enum { COH_INITIAL_CAPTURE_NONE,COH_INITIAL_CAPTURE_GROUPS,
 COH_INITIAL_CAPTURE_ALLENTS } CohInitialCaptureKind;
/* Explicit diagnostic domain, not limits asserted by the original sender. */
#define COH_INITIAL_EDIT_MESSAGE_BYTES_MAX 16384u /* includes terminating NUL */
#define COH_INITIAL_EDIT_MESSAGES_MAX 16u
typedef enum { COH_INITIAL_EDIT_LOW_PRIORITY=0,COH_INITIAL_EDIT_ERROR=1,
 COH_INITIAL_EDIT_HIGH_PRIORITY=2,COH_INITIAL_EDIT_ERROR_SERVER_WRITE=3
} CohInitialCaptureEditMessageType;
typedef enum { COH_INITIAL_CAPTURE_FAILURE_NONE,COH_INITIAL_CAPTURE_FAILURE_INPUT,
 COH_INITIAL_CAPTURE_FAILURE_OWNER,COH_INITIAL_CAPTURE_FAILURE_PROTOCOL,
 COH_INITIAL_CAPTURE_FAILURE_GROUPS,COH_INITIAL_CAPTURE_FAILURE_REQUEST,
 COH_INITIAL_CAPTURE_FAILURE_COMMAND,COH_INITIAL_CAPTURE_FAILURE_HEADER,
 COH_INITIAL_CAPTURE_FAILURE_OBSERVER,COH_INITIAL_CAPTURE_FAILURE_RELEASE,
 COH_INITIAL_CAPTURE_FAILURE_TIMEOUT,COH_INITIAL_CAPTURE_FAILURE_CANCELLED,
 COH_INITIAL_CAPTURE_FAILURE_MEMORY } CohInitialCaptureFailure;
/* Classification of an actually decoded normalized command, never a raw ID or
 * packet string. NONE pairs with valid=0; UNKNOWN is a decoded nonwhitelist ID.
 * All known names come from pinned original ServerCommCmd, excluding sentinel. */
typedef enum { COH_INITIAL_CAPTURE_COMMAND_NONE,COH_INITIAL_CAPTURE_COMMAND_UNKNOWN,
#define COH_INITIAL_CAPTURE_COMMAND(name,id) COH_INITIAL_CAPTURE_COMMAND_##name,
#include "coh_initial_command_kinds.inc"
#undef COH_INITIAL_CAPTURE_COMMAND
} CohInitialCaptureCommandKind;
const char *coh_initial_capture_command_name(CohInitialCaptureCommandKind);
/* Exact event ADDRESS is a synchronous loan key, not caller-populated labels.
 * No pointer inside this value grants ownership or durable session authority. */
typedef struct { CohInitialCaptureKind kind; } CohInitialCaptureEvent;
typedef struct {
 CohRepReader reader; /* whole payload; cursor immediately after command */
 CohRepSchema schema;CohGroupsInspection groups;CohRepUpdatePrefix update;
 CohInitialCaptureKind kind;
 uint64_t message_generation,groups_message_generation;
 uint32_t message_id,ordered_id,connection_id,transport_version;
 uint32_t map_generation,selection_generation,selected_slot,selected_dbid;
 uint32_t map_id,map_link_id,db_session_generation,db_receipt_generation;
 unsigned ordered,local_development_authorized,selected_dbid_owner_bound;
 unsigned source_generation_admitted,complete_initial_character,actor_publication,
  ack_permitted,world_authority; /* always zero */
} CohInitialCaptureLease;
/* First diagnostic failure/cancellation, latched before diagnostic cleanup.
 * These are actual typed module phases, not reconstructed progress. An inner
 * ordinary module may already have reached its own terminal phase. Cause and
 * phases stay together through later close/cancel/service attempts. This does
 * not modify or reinterpret CohLocalDiagnostics.terminal_* fields. */
typedef struct {
 unsigned valid;
 CohLocalPhase local_phase;CohDbSessionPhase db_phase;CohMapPhase map_phase;
 CohStatus status;CohInitialCaptureFailure failure;
} CohInitialCaptureFailureSnapshot;
/* Immutable numeric observation survives later ALLENTS refusal/close. It does
 * not retain packet pointers, schemas, secrets or a semantic authority permit. */
typedef struct {
 CohInitialCapturePhase phase;CohInitialCaptureFailure failure;CohStatus status;
 uint32_t groups_observations,allents_observations,reqallents_sent;
 uint32_t last_command,last_payload_bits,last_decoded_bytes,last_byte_aligned;
 uint64_t groups_message_generation,allents_message_generation;
 uint32_t groups_message_id,map_generation,selection_generation,selected_slot,
  selected_dbid,map_id,map_link_id,db_session_generation,db_receipt_generation;
 CohGroupsInspection groups;
 unsigned groups_observed,raw_allents_observed;
 /* Complete source-layout EDITMSG packets handled only while WAIT_ALLENTS.
  * Length excludes NUL; last type/length are valid iff count is nonzero.
  * No message text is copied, retained, logged or passed to UI services. */
 uint32_t edit_messages_handled,edit_message_last_bytes;
 CohInitialCaptureEditMessageType edit_message_last_type;
 unsigned refused_command_valid;CohInitialCaptureCommandKind refused_command_kind;
 unsigned source_generation_admitted,complete_initial_character,actor_publication,
  ack_permitted,world_authority; /* always zero */
 CohInitialCaptureFailureSnapshot first_failure;
 CohLocalDiagnostics local;
} CohInitialCaptureDiagnostics;
/* Observer may return a refusal to abort (e.g. file write failure). COH_OK means
 * only successful diagnostic I/O, never application validation or authority.
 * All event/client/reader/payload pointers expire on return. No mutation or
 * reentrant service/close/destroy is permitted; such calls refuse/no-op. Only
 * lease and diagnostics may be called during observation. Output/copies and
 * callback stack/allocation/retention require the caller's aggregate budget. */
typedef CohStatus (*CohInitialCaptureObserver)(void *,const CohInitialCapture *,
 const CohInitialCaptureEvent *);
/* Owns its Local and underlying DB/Map/UDP modules. Loopback local development
 * config only; this does not run an AuthServer login. One begin/transaction per
 * owner; create a new owner for an explicit new attempt. */
CohInitialCapture *coh_initial_capture_create(const CohLocalConfig *);
CohStatus coh_initial_capture_begin(CohInitialCapture *,const CohDbLogin *,
 const char *account,uint32_t db_connect_id,uint32_t map_connect_id,uint64_t now_ms);
CohStatus coh_initial_capture_characters(const CohInitialCapture *,CohLocalCharacters *);
CohStatus coh_initial_capture_choose_character(CohInitialCapture *,uint32_t slot,uint64_t now_ms);
/* Bounded synchronous service. observer/context required; context_bytes names
 * its COMPLETE live span (nonzero), disjoint from the owner and current loan.
 * Original complete GROUPS inspection and actual claimed DB handoff precede
 * one automatic REQALLENTS, after the GROUPS observer returns COH_OK. Only fully
 * parsed bounded SERVER_EDITMSG packets may continue WAIT_ALLENTS, without
 * changing its original deadline or sending a response. Unknown intervening
 * commands/failed parses terminate; no skip/scan/retry. Raw ALLENTS
 * has its source header checked under the existing4MiB decoded cap, before the
 * ordinary16KiB semantic gate. It is observed once then closed. No READY,
 * RECEIVED_CHARACTER, full-update ACK, LIVE state or character acceptance.
 * Waiting returns COH_OK; captured raw packet returns COH_UNSUPPORTED with
 * phase CAPTURED. Admitted protocol/I/O/cancel/timeout refusals close both sockets
 * and preserve prior GROUPS numeric
 * evidence. Invalid inputs and rejected reentry preserve the active owner.
 * Owner itself allocates no packet copy or observer workspace. */
CohStatus coh_initial_capture_service(CohInitialCapture *,uint64_t now_ms,CohCancel,
 CohInitialCaptureObserver,void *context,size_t context_bytes);
/* Valid only for the current owner's EXACT event address. Derives all values
 * from its actual opaque network loan/claimed handoff; no labels supplied by
 * caller. Output must be disjoint from owner/internal objects/event/message/
 * payload; error preserves output. Reader bytes expire on observer return. */
CohStatus coh_initial_capture_lease(const CohInitialCapture *,const CohInitialCaptureEvent *,
 CohInitialCaptureLease *);
void coh_initial_capture_diagnostics(const CohInitialCapture *,CohInitialCaptureDiagnostics *);
/* Explicit enclosing diagnostic deadline, independent of module deadlines.
 * Only a begun active CONNECTING..WAIT_ALLENTS owner can time out. Null,
 * callback-busy and all inactive/terminal owners are unchanged. Records typed
 * first failure as COH_STATE/TIMEOUT before closing; no generic failure input. */
void coh_initial_capture_timeout(CohInitialCapture *);
void coh_initial_capture_cancel(CohInitialCapture *);
void coh_initial_capture_close(CohInitialCapture *);
void coh_initial_capture_destroy(CohInitialCapture *);
#ifdef __cplusplus
}
#endif
#endif
