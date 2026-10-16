/* Fixture-only title storage. Arrays mirror the pinned Entity/Player fields;
 * no game callbacks, actor owner, database identity or dictionary is supplied. */
#include "coh_entities.h"
#define MAX_NAME_LEN 128
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define AINRANGE(i,a) ((unsigned)(i)<ARRAY_SIZE(a))
static int g_bAssertOnBitStreamError;
typedef struct {
    int titleThe,titleColors[2],titleBadge,glowieUnlocked,attachArticle,
        respecTokens,lastTurnstileEventID,lastTurnstileMissionID,helperStatus;
    char titleTheText[10],titleCommon[32],titleOrigin[32],titleSpecial[128];
} TitlePlayer;
typedef struct {char name[MAX_NAME_LEN];int gender,name_gender;TitlePlayer *pl;} TitleEntity;
static struct {int is_endgame_raid;} db_state;
/* String storage/copy adapters: source scalar reads retain the original wire
 * order; trusted original fixtures are padded. Native code supplies bounds. */
static char *pktGetString(Packet *p){
    static char value[1024];unsigned i;
    for(i=0;i<sizeof(value);i++){value[i]=(char)pktGetBits(p,8);if(!value[i])return value;}
    assert(0);return NULL;
}
static const char *pktGetIfSetString(Packet *p){return pktGetBits(p,1)?pktGetString(p):"";}
static void strncpyt(char *out,const char *in,size_t n){size_t len=strlen(in);assert(n);if(len>=n)len=n-1;memcpy(out,in,len);out[len]=0;}
static void title_seed(TitleEntity *e,TitlePlayer *p){
    memset(e,0,sizeof(*e));memset(p,0,sizeof(*p));e->pl=p;
    strcpy(e->name,"PriorName");strcpy(p->titleTheText,"PriorThe");strcpy(p->titleCommon,"PriorCommon");
    strcpy(p->titleOrigin,"PriorOrigin");strcpy(p->titleSpecial,"PriorSpecial");
    p->titleThe=17;p->titleColors[0]=13;p->titleColors[1]=27;p->titleBadge=11;
    p->glowieUnlocked=1;e->gender=2;e->name_gender=1;p->attachArticle=1;
    p->respecTokens=51;p->lastTurnstileEventID=64;p->lastTurnstileMissionID=128;p->helperStatus=3;
}
static void title_export(const TitleEntity *e,U32 packet_id,CohEntTitles *v){
    const TitlePlayer *p=e->pl;memset(v,0,sizeof(*v));v->valid=1;v->packet_id=packet_id;
    v->title_the=p->titleThe;v->colors[0]=p->titleColors[0];v->colors[1]=p->titleColors[1];v->badge=p->titleBadge;
    v->glowie_unlocked=p->glowieUnlocked;v->gender=e->gender;v->name_gender=e->name_gender;
    v->attach_article=p->attachArticle;v->respec_tokens=p->respecTokens;
    v->turnstile_event=p->lastTurnstileEventID;v->turnstile_mission=p->lastTurnstileMissionID;v->helper_status=p->helperStatus;
    strcpy(v->name,e->name);strcpy(v->the_text,p->titleTheText);strcpy(v->common,p->titleCommon);
    strcpy(v->origin,p->titleOrigin);strcpy(v->special,p->titleSpecial);
}
