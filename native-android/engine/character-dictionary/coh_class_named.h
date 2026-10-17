#ifndef COH_CLASS_NAMED_H
#define COH_CLASS_NAMED_H
#include "coh_classes.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_CLASS_NAMED_RAM_MAX (8u*1024u*1024u)
#define COH_CLASS_NAMED_STACK_RESERVE 8192u
#define COH_CLASS_NAMED_COMPARISON_WORK_MAX (8u*1024u*1024u)
typedef struct{const CohClassDictionary*source;uint64_t source_lease;uint8_t source_sha256[32];uint32_t table_count;uint8_t validated,runtime_generation,actor_authority;}CohClassNamedDictionary;
typedef struct{uint32_t class_index,table_index,requested_index,applied_index,value_word;uint8_t found,runtime_generation,actor_authority;}CohClassNamedValue;
/* Source classes_Finalize semantics for the finite ASCII named-table profile.
 * Retains the immutable raw class owner and its input lease, preserving each
 * class/table/index and rejecting same-class duplicate keys transactionally.
 * Empty value arrays remain represented; value lookup refuses their undefined
 * original negative-index path. Missing names explicitly return found=0/value1,
 * matching class_GetNamedTableValue's Errorf fallback, never a fabricated table.
 * Source/current cache, complete power dictionary, actor and ACK remain gated. */
CohStatus coh_class_named_prepare(const CohClassDictionary*,CohClassNamedDictionary*,size_t,size_t);
CohStatus coh_class_named_get(const CohClassNamedDictionary*,uint32_t,CohBytes,uint32_t,
 CohClassNamedValue*,size_t,size_t);
#ifdef __cplusplus
}
#endif
#endif
