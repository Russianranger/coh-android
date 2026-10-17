#ifndef COH_CHARACTER_OUTER_H
#define COH_CHARACTER_OUTER_H
#include "coh_character_creation.h"
#include "coh_character_tail.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_CHARACTER_OUTER_RAM_MAX (8u*1024u*1024u)
#define COH_CHARACTER_OUTER_STACK_RESERVE 32768u
typedef struct {
 CohCharacterCreationPrefix creation;CohCharacterTail tail;
 size_t begin_bit,creation_end_bit,end_bit;
} CohCharacterOuter;
typedef struct {
 CohCharacterOuter candidate;
 CohCharacterCreationWorkspace creation;CohCharacterTailWorkspace tail;
} CohCharacterOuterWorkspace;
/* Complete ordered raw receiveCharacterFromServer wire body, groups1..6.
 * Does not execute original character_Receive gameplay/dictionary application,
 * resolve selected DBID/entity, validate enclosing ALLENTS/global tails/end,
 * apply previous state, publish an actor or enable any completion ACK. Ordinary
 * source character metadata/profile constraints remain. Unknown resource IDs and
 * duplicate events retained. Success stops after rename; later enclosing fields
 * untouched. No public certification/actor conversion is supplied.
 * Input/reader/profile/output/workspace must be pairwise disjoint. Output and
 * workspace on caller heap/arena. Entire input+output+workspace+32KiBstackreserve+
 * retained bytes within8MiB; child charges excluded from extra then counted once.
 * No allocation/retained input; on failure reader/output unchanged atomically.
 * Raw account bytes and command strings sensitive: never log by default. */
CohStatus coh_character_outer_read(CohRepReader *,const CohCharacterWireProfile *,
 uint32_t packet_id,CohCharacterOuter *,CohCharacterOuterWorkspace *,
 size_t budget,size_t retained_bytes);
#ifdef __cplusplus
}
#endif
#endif
