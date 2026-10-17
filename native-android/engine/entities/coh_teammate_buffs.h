#ifndef COH_TEAMMATE_BUFFS_H
#define COH_TEAMMATE_BUFFS_H
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Local admission bounds, not original protocol maxima. */
#define COH_ENT_BUFFS_MAX 256u
#define COH_ENT_BUFF_MODS_PER_BUFF_MAX 64u
#define COH_ENT_BUFF_MODS_MAX 2048u
#define COH_ENT_BUFF_AGGREGATE_MAX (4u*1024u*1024u)
#define COH_ENT_BUFF_STACK_RESERVE 4096u
typedef struct { uint32_t magnitude_word,attribute_hash; } CohEntBuffMod;
typedef struct {
    uint32_t delete_mark,power_crc,timer_present,blink_now,uid,
        mods_present,mods_begin,mods_count;
} CohEntBuff;
typedef struct {
    uint32_t teammate,buffs_present,not_getting_buffs,diffs_only,count,mods_count;
    CohEntBuff buffs[COH_ENT_BUFFS_MAX];
    CohEntBuffMod mods[COH_ENT_BUFF_MODS_MAX];
    size_t begin_bit,end_bit;
} CohEntTeammateBuffs;
typedef struct { CohEntTeammateBuffs candidate; } CohEntTeammateBuffsWorkspace;
/* Complete appendTeammatePacket wire body, including teammate/buff flags,
 * character_SendBuffs and basepower_Send. Starts AFTER the very-rare suffix.
 * Preserves source reverse-send order and every raw signed magnitude word.
 * An absent mods field means retain previous mods, not replace with empty.
 * Diffs, deletion, timer and no-send flags are retained without application.
 * Power CRC/attribute hashes remain unresolved; no dictionary authority,
 * stale/prior-state application, entity ownership, actor publication or ACK.
 *
 * On refusal reader and output are unchanged. Candidate workspace unspecified.
 * All input/reader/output/workspace spans must be disjoint. Allocation-free;
 * put both PODs in caller-owned heap/storage, not Android stacks. Budget charges
 * input + complete output + workspace + stack reserve + caller_retained_bytes.
 * Every enclosing entity and complete message field must validate together
 * before an owner may publish any state or send completion acknowledgments. */
CohStatus coh_ent_teammate_buffs(CohRepReader *,CohEntTeammateBuffs *,
    CohEntTeammateBuffsWorkspace *,size_t caller_retained_bytes,size_t aggregate_limit);
#ifdef __cplusplus
}
#endif
#endif
