#ifndef COH_SOCIAL_H
#define COH_SOCIAL_H
#include "../entity-team/coh_team.h"
#include "../entity-superstats/coh_superstats.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_SOCIAL_RAM_MAX (8u*1024u*1024u)
#define COH_SOCIAL_STACK_RESERVE 8192u
typedef struct{
 uint32_t team_up_to_date,league_up_to_date;CohTeamList team,league;
 CohSuperStats superstats;size_t begin_bit,team_end_bit,superstats_end_bit,end_bit;
}CohSocialPhase;
typedef struct{CohSocialPhase candidate;CohTeamWorkspace team;CohSuperStatsWorkspace superstats;}CohSocialWorkspace;
/* Atomic original post-workshop team-flag/list,superstats,league-flag/list body.
 * Stops BEFORE attribute-description present bit. Skipped lists remain absent;
 * no prior-state application. Original SGconsumer executable remains unqualified.
 * Heap/arena; pairwise disjoint spans; input+output+allworkspace+8192stack+retained
 * within8MiB charged once. Failure preserves reader/output; no dictionary/ACK. */
CohStatus coh_social_phase_read(CohRepReader *,CohSocialPhase *,CohSocialWorkspace *,size_t budget,size_t retained_bytes);
#ifdef __cplusplus
}
#endif
#endif
