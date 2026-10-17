#ifndef COH_VERY_RARE_TAIL_H
#define COH_VERY_RARE_TAIL_H
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif

/* Local admission limits, except the original two-member/64-byte pact fields. */
#define COH_ENT_TAIL_TOKENS_MAX 256u
#define COH_ENT_TAIL_RECIPES_MAX 256u
#define COH_ENT_TAIL_DETAILS_MAX 256u
#define COH_ENT_TAIL_PACT_MAX 2u
#define COH_ENT_TAIL_PACT_NAME_MAX 64u
#define COH_ENT_TAIL_STRING_MAX 1024u
#define COH_ENT_TAIL_STRINGS_MAX (64u*1024u)
#define COH_ENT_TAIL_AGGREGATE_MAX (4u*1024u*1024u)
#define COH_ENT_TAIL_STACK_RESERVE 8192u

/* Offset into the owned strings pool; bytes excludes the terminating NUL.
 * Presence comes from the corresponding wire flag, not a zero-length string. */
typedef struct { uint32_t offset,bytes; } CohEntTailString;
typedef struct {
    uint32_t filename_present,owner_dbid,context,subhandle,level,
        difficulty_level_adjust,difficulty_team_size,dont_reduce_boss,always_av,
        alliance,timeout,timezero,timer_type,fail_on_timeout,
        complete,mission,running_mission,sg_mission,zone_transfer,
        teleport_on_complete,enforce_time_limit,abandonable,zowie,
        location_present,explicit_map_present,location_type,
        zinfo,zseed,zmap_id;
    CohEntTailString filename,description,owner,state,location_map,
        location_name,ztype,zname,zpool_sizes;
    float position[3];
} CohEntTailMission;
typedef struct { CohEntTailString name; uint32_t value,time; } CohEntTailToken;
typedef struct { CohEntTailString name; uint32_t unlimited,count; } CohEntTailRecipe;
typedef struct { CohEntTailString name; uint32_t creation_time,expiration_time,flags; } CohEntTailDetail;
typedef struct { uint32_t dbid,name_present; CohEntTailString name; } CohEntTailPactMember;
typedef struct {
    uint32_t supergroup_update,supergroup_id,colors[2],spaces_for_items,
        mission_present,token_count,recipe_count,detail_count,
        pact_update,pact_id,pact_count,logout_update,logout_bad_connection,
        logout_timer_present,logout_quanta,strings_bytes;
    CohEntTailString supergroup_name,supergroup_emblem;
    CohEntTailMission mission;
    CohEntTailToken tokens[COH_ENT_TAIL_TOKENS_MAX];
    CohEntTailRecipe recipes[COH_ENT_TAIL_RECIPES_MAX];
    CohEntTailDetail details[COH_ENT_TAIL_DETAILS_MAX];
    CohEntTailPactMember pact[COH_ENT_TAIL_PACT_MAX];
    char strings[COH_ENT_TAIL_STRINGS_MAX];
    size_t begin_bit,end_bit;
} CohEntVeryRareTail;
typedef struct { CohEntVeryRareTail candidate; } CohEntVeryRareTailWorkspace;

/* Consecutive original entSendOtherSupergroupInfo, entSendLevelingpactInfo and
 * entSendLogoutUpdate bodies, AFTER the qualified very-rare AFK prefix and
 * BEFORE the teammate-buff flag. No outer flag, entity identity or ACK signal.
 * Nested TaskStatusSend grammar, including location and zowie strings, is raw
 * metadata only. Dictionary/UI/prior-state/stale-packet application is absent.
 * Signed source int/time fields retain their raw 32-bit words. Logout quanta
 * are not multiplied or represented as an authoritative client timer.
 *
 * Reader/output are unchanged on every refusal; workspace is unspecified.
 * All reader/output/workspace/input spans must be disjoint and caller-owned.
 * No allocations, I/O, borrowed result pointers or hidden retained ownership.
 * Keep both PODs off Android stacks. Budget charges both complete PODs, input
 * bytes, an 8KiB stack reserve and caller_retained_bytes (including outer staged
 * data and previous generations). An outer message must stage this suffix
 * together with every preceding/following field before publishing any state.
 */
CohStatus coh_ent_very_rare_tail(CohRepReader *,CohEntVeryRareTail *,
    CohEntVeryRareTailWorkspace *,size_t caller_retained_bytes,size_t aggregate_limit);

#ifdef __cplusplus
}
#endif
#endif
