#ifndef COH_CLASS_LEVEL_H
#define COH_CLASS_LEVEL_H
#include "coh_classes.h"
#include "coh_power_categories.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_CLASS_LEVEL_WORDS 115u
#define COH_CLASS_LEVEL_RAM_MAX (8u*1024u*1024u)
#define COH_CLASS_LEVEL_STACK_RESERVE 16384u
typedef struct {
 uint8_t class_sha256[32],category_sha256[32];uint64_t class_lease,category_lease;
 uint32_t class_index,level,levels,table_bytes,category_index[4];
 uint32_t attributes[6][COH_CLASS_LEVEL_WORDS];
 uint8_t historical_projection_validated,runtime_generation,actor_authority;
} CohClassLevel;
typedef struct{CohClassLevel candidate;}CohClassLevelWorkspace;
/* Finite-only historical projection of source classes_Repack at one level.
 * Rows0..3 are Max/MaxMax/StrengthMax/ResistanceMax, rows4..5 minima.
 * Whole source tables remain ordered and leased; this selects no gameplay actor.
 * Missing strength/resistance minima use source zero/-100 defaults. Max arrays
 * repeat their final value, or source default1 when empty. Category refs retain
 * original four identities and Pool/Epic fallback; absent dependency refuses.
 * All owners/input/workspace/output/retained charges precede processing; output
 * unchanged on refusal. No cache/runtime generation, full power dict or ACK. */
CohStatus coh_class_level_read(const CohClassDictionary*,const CohPowerCategoryDictionary*,
 uint32_t,uint32_t,CohClassLevel*,CohClassLevelWorkspace*,size_t,size_t);
#ifdef __cplusplus
}
#endif
#endif
