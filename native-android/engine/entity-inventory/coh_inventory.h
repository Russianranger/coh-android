#ifndef COH_ENTITY_INVENTORY_H
#define COH_ENTITY_INVENTORY_H
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_INVENTORY_ITEMS_MAX 2048u
#define COH_INVENTORY_AUCTION_BYTES (256u*1024u)
#define COH_INVENTORY_RAM_MAX (8u*1024u*1024u)
#define COH_INVENTORY_STACK_RESERVE 4096u
typedef struct {uint32_t type,index,amount,id,variable_words[4];}CohInventoryItem;
typedef struct {
 uint32_t count;CohInventoryItem items[COH_INVENTORY_ITEMS_MAX];
 uint32_t auction_updated,auction_bytes;char auction_text[COH_INVENTORY_AUCTION_BYTES];
 size_t begin_bit,items_end_bit,end_bit;
}CohInventoryUpdate;
typedef struct {CohInventoryUpdate candidate;}CohInventoryWorkspace;
/* Complete entity_SendInvUpdate producer wire body. Concept type1 adds four
 * finite IEEE32 words; other raw types use original default ID-only grammar.
 * Original AuctionInventory wrapper carries one serialized string; stage it
 * opaquely, without auction-text/dictionary parsing, trading or state changes.
 * Unknown types/IDs, signed packed words and ordered duplicates are retained.
 * Local item2048/string256KiB limits refuse rather than truncate. All spans
 * pairwise disjoint; caller heap/arena for output/workspace. Aggregate budget
 * charges input+bothPODs+stackreserve+retained bytes. No allocation/retainedinput;
 * on failure output/reader unchanged. Not complete ALLENTS/actor/ACK authority. */
CohStatus coh_inventory_update_read(CohRepReader *,CohInventoryUpdate *,
 CohInventoryWorkspace *,size_t budget,size_t retained_bytes);
#ifdef __cplusplus
}
#endif
#endif
