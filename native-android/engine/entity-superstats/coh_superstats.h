#ifndef COH_SUPERSTATS_H
#define COH_SUPERSTATS_H
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_SG_MEMBERS_MAX 150u
#define COH_SG_RANKS 7u
#define COH_SG_ALLIES 10u
#define COH_SG_RAM_MAX (8u*1024u*1024u)
#define COH_SG_STACK_RESERVE 4096u
typedef struct{
 char name[32],arch[32],origin[32],zone[256];
 uint32_t dbid,rank,level,last_online,online,member_since,prestige,player_type;
}CohSuperMember;
typedef struct{char name[64];uint8_t permission_bytes[4];}CohSuperRank;
typedef struct{uint32_t dbid,dont_talk,min_display_rank;char name[64];}CohSuperAlly;
typedef struct{
 uint32_t count,financial[7],update;CohSuperMember members[COH_SG_MEMBERS_MAX];
 char name[64],motto[256],message[256],emblem[64],description[512];
 uint32_t colors_tithe_spaces[4],demote_timeout;CohSuperRank ranks[COH_SG_RANKS];
 uint32_t entry_permission,memberrank_count,memberranks[COH_SG_MEMBERS_MAX][2];
 CohSuperAlly allies[COH_SG_ALLIES];uint32_t alliance_min_talk_rank;
 size_t begin_bit,end_bit;
}CohSuperStats;
typedef struct{CohSuperStats candidate;}CohSuperStatsWorkspace;
/* Complete original sgroup_sendList producer-defined wire body. Raw strings,
 * IDs, ranks and permission bytes have no dictionary/gameplay authority. Count
 * and memberrank storage bounded150, rank7/permissionbytes4/allies10 source
 * schema. Exact conditional update fields and byte-array alignment preserved.
 * Pairwise disjoint spans; input+bothPODs+4096stack+retained within8MiB. Caller
 * heap/arena; no allocation or retained input; output/reader atomic on failure.
 * Original consumer executable qualification remains separate. No actor/ACK. */
CohStatus coh_superstats_read(CohRepReader *,CohSuperStats *,CohSuperStatsWorkspace *,size_t budget,size_t retained_bytes);
#ifdef __cplusplus
}
#endif
#endif
