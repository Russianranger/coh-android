/* Deterministic original-function owner shells. Dictionaries/UI effects are
 * fixtures only. Monitor CheckAndSortInfo observes raw input; no sorting or
 * dictionary validity is certified by the wire parser. */
#include "badge_observation.h"
typedef int bool;
#define MIN(a,b) ((a)<(b)?(a):(b))
#define ENT_IS_VILLAIN(e) 0
#define BADGE_ENT_MAX_BADGES COH_BADGE_PLAYER_MAX
#define BADGE_SG_MAX_BADGES COH_BADGE_SUPERGROUP_MAX
#define BADGE_ENT_RECENT_BADGES COH_BADGE_RECENT_MAX
#define MAX_BADGE_MONITOR_ENTRIES COH_BADGE_MONITOR_MAX
#define BADGE_SG_MAX_STATS 2000
typedef struct {
    int iIdx;const char *filename,*pchDisplayButton,*pchDisplayText[2],*pchDisplayHint[2];
} BadgeDef;
typedef struct {BadgeDef **ppBadges;} BadgeDefs;
typedef struct {int iIdx;} BadgeMonitorInfo;
typedef struct {
    int debugBadgeLevel;U32 aiBadges[BADGE_ENT_MAX_BADGES];
    struct {U32 idx,timeAwarded;} recentBadges[BADGE_ENT_RECENT_BADGES];
    BadgeMonitorInfo badgeMonitorInfo[MAX_BADGE_MONITOR_ENTRIES];
} EntPlayer;
typedef struct {struct {U32 *eaiStates;} badgeStates;} Supergroup;
typedef struct {EntPlayer *pl;Supergroup *supergroup;int supergroup_id,db_id;} Entity;
static BadgeDefs g_BadgeDefs,g_SgroupBadges;
static int player_def_count,sg_def_count;
static struct {int clickToSource;} server_state;
static U32 server_sg[BADGE_SG_MAX_STATS];
static char *g_pchBadgeText[BADGE_ENT_MAX_BADGES],*g_pchBadgeFilename[BADGE_ENT_MAX_BADGES],*g_pchBadgeButton[BADGE_ENT_MAX_BADGES];
static char *g_pchSgBadgeText[BADGE_SG_MAX_BADGES],*g_pchSgBadgeFilename[BADGE_SG_MAX_BADGES],*g_pchSgBadgeButton[BADGE_SG_MAX_BADGES];
static int g_DebugBadgeDisplayMode,monitor_sort_calls;
static BadgeDef fallback_badge={1,"fixture","button",{"text","text"},{"hint","hint"}};
static int eaSize(BadgeDef ***p){return p==&g_BadgeDefs.ppBadges?player_def_count:sg_def_count;}
static int eaiSize(U32 **p){(void)p;return BADGE_SG_MAX_STATS;}
static void eaiSetSize(U32 **p,int n){(void)p;assert(n==BADGE_SG_MAX_STATS);}
static void eaiCreate(U32 **p){(void)p;assert(0);}
static U32 *sgrpbadge_eaiStatesFromId(int id){assert(id==721);return server_sg;}
static void ErrorFilenamef(const char *f,const char *m){(void)f;(void)m;}
static const BadgeDef *badge_GetBadgeByIdx(int id){assert(id>0&&id<(int)BADGE_ENT_MAX_BADGES);return &fallback_badge;}
static const BadgeDef *badge_GetSgroupBadgeByIdx(int id){assert(id>0&&id<(int)BADGE_SG_MAX_BADGES);return &fallback_badge;}
static const char *textStd(const char *s){return s;}
static void badgeReparse(void){}
static void badgeMonitor_CheckAndSortInfo(Entity *e){(void)e;monitor_sort_calls++;}
