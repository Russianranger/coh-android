#ifndef COH_INITIAL_RECORD_H
#define COH_INITIAL_RECORD_H
#include "../selected-record/coh_selected_record.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Raw INITIAL/full-create profile for self and other source entity types.
 * Types are shared staging layouts, not independently authoritative actors.
 * `selected` in the shared result is this record's raw slot even for nonself.
 * Exact immutable input/dictionary lifetime and memory provider contracts are
 * inherited from coh_selected_record_read. Expected selected DBID remains the
 * positive owned DB-handoff identity; other players cannot alias that DBID.
 * Initial source full-update forces complete mode/position/orientation/sequence
 * and all rare groups. Delta/non-create/interpolated profiles refuse rather
 * than interpreting an initial record as a later update. Self-only inventory
 * and taskforce branches follow the actual decoded self bit. No list/control/
 * deletes/tails/semantic dictionary/actor/ACK admission is returned here. */
CohStatus coh_initial_record_read(CohRepReader*,const CohSelectedRecordContext*,
 const CohEntSlot*,const CohSelectedRecordMemory*,CohSelectedRecord*,
 CohSelectedRecordWorkspace*,CohSelectedRecordFailure*,size_t,size_t);
#ifdef __cplusplus
}
#endif
#endif
