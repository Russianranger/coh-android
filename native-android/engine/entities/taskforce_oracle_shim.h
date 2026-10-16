/* Synthetic owners around unchanged original architect/parameter functions.
 * This is wire grammar qualification, not TaskForce engine ABI or UI behavior. */
#include "coh_taskforce.h"
#define devassert assert
typedef struct {int unused;} TeamMembers;
typedef struct {
    int onArchitect,onFlashback,taskforce_id,invincible,untargetable,
        architect_invincible,architect_untargetable;
    struct TaskForce *taskforce;
} TaskEntity;
typedef struct {char *pchName,*pchAuthor,*pchDescription;int rating,european;} PlayerCreatedStoryArc;
static PlayerCreatedStoryArc *task_arc;
static PlayerCreatedStoryArc *playerCreatedStoryArc_GetPlayerCreatedStoryArc(int id){(void)id;return task_arc;}
static int TaskForceIsOnArchitect(TaskEntity *e){return e->onArchitect;}
static void costume_destroy(Costume *c){(void)c;}
static char task_strings[16][4096];static unsigned task_string_count;
static char *task_get_string(Packet *p){
    assert(task_string_count<16);char *v=task_strings[task_string_count++];
    for(unsigned i=0;i<4096;i++){v[i]=(char)pktGetBits(p,8);if(!v[i])return v;}
    assert(0);return NULL;
}
static char *task_strdup(const char *s){size_t n=strlen(s)+1;char *v=malloc(n);assert(v);memcpy(v,s,n);return v;}
static char task_review_name[256],task_review_author[128],task_review_description[4096];
static U32 task_rating,task_european;static int task_review_received;
static void missionReview_Set(int id,int flags,const char *name,const char *author,const char *description,int rating,int european){
    (void)id;(void)flags;assert(strlen(name)<256&&strlen(author)<128&&strlen(description)<4096);
    strcpy(task_review_name,name);strcpy(task_review_author,author);strcpy(task_review_description,description);
    task_rating=rating;task_european=european;task_review_received=1;
}
static size_t task_custom_end;
static int task_custom_receive(Packet *p,CustomNPCCostume *c){int r=NPCcostume_receive(p,c);task_custom_end=bsGetCursorBitPosition(&p->stream);return r;}
#undef strdup
#define strdup task_strdup
#define SAFE_FREE(p) do{free(p);p=NULL;}while(0)
#define NPCcostume_receive task_custom_receive
#define pktGetString task_get_string
#define Entity TaskEntity
