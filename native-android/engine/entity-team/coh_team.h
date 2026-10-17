#ifndef COH_TEAM_H
#define COH_TEAM_H
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_TEAM_MEMBERS_MAX 8u
#define COH_LEAGUE_MEMBERS_MAX 48u
#define COH_TEAM_RAM_MAX (8u*1024u*1024u)
#define COH_TEAM_STACK_RESERVE 4096u
typedef struct {
 uint32_t dbid,on_map,changed;char name[64],map[256];
 uint32_t team_leader,locked;
}CohTeamMember;
typedef struct {
 uint32_t league,identity_present,id,taskforce,lfg,leader,count,level,mentor,active;
 CohTeamMember members[COH_LEAGUE_MEMBERS_MAX];size_t begin_bit,end_bit;
}CohTeamList;
typedef struct {CohTeamList candidate;}CohTeamWorkspace;
/* Whole original team_sendList or league_sendList wire body. kind0=team,
 * kind1=league. Wire order preserved, raw identities/flags retained; no lookup,
 * inherited prior names, local on-map entity authority or gameplay application.
 * All input/reader/output/workspace spans disjoint. Caller-owned heap/arena.
 * Input+output+workspace+stack+retained within8MiB; no allocation. Failure leaves
 * reader/output unchanged. No enclosing ALLENTS/selected actor/ACK authority. */
CohStatus coh_team_list_read(CohRepReader *,unsigned kind,CohTeamList *,
 CohTeamWorkspace *,size_t budget,size_t retained_bytes);
#ifdef __cplusplus
}
#endif
#endif
