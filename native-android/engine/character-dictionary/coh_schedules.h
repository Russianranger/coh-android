#ifndef COH_SCHEDULES_H
#define COH_SCHEDULES_H
#include "coh_origins.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_SCHEDULE_FIELDS 7u
#define COH_SCHEDULE_WORDS_MAX 4096u
#define COH_SCHEDULE_INPUT_MAX 65536u
#define COH_SCHEDULE_RAM_MAX 262144u
#define COH_SCHEDULE_STACK_RESERVE 8192u
typedef struct{uint32_t first,count;}CohScheduleSpan;
typedef struct{
 uint8_t input_sha256[32];uint64_t source_lease;
 uint32_t schema_crc,dependency_count,word_count;
 uint8_t raw_schema_validated,historical_schema_crc_matched,runtime_generation,actor_authority;
 CohScheduleSpan fields[COH_SCHEDULE_FIELDS];uint32_t words[COH_SCHEDULE_WORDS_MAX];
}CohSchedules;
typedef struct{CohSchedules candidate;}CohSchedulesWorkspace;
/* Complete historical ParseSchedules/ParseSchedule binary grammar. Copies all
 * seven source ordered signed-int arrays; duplicates/negative/unsorted entries
 * are not normalized. Input may retire on success. Digest/header equality is
 * not current SERVERONLY/shared/cache generation. No callbacks after import.
 * Complete input/out/work/digest context/scratch/retained/8KiB stack charged
 * before digest callback. No allocation; output unchanged on every refusal. */
CohStatus coh_schedules_read(CohBytes,uint64_t,const uint8_t[32],const CohCostumeImportDigest*,
 CohSchedules*,CohSchedulesWorkspace*,size_t,size_t);
/* Exact source CountForLevel: clamp negative level to0, then count the ordered
 * PREFIX whose thresholds<=level. No sorting or count-all shortcut is valid. */
CohStatus coh_schedule_count(const CohSchedules*,uint32_t,int32_t,uint32_t*);
#ifdef __cplusplus
}
#endif
#endif
