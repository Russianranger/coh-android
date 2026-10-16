/* Synthetic storage/menu/renderer adapters for unchanged original appearance
 * envelope producer/consumer. No runtime asset or UI behavior is qualified. */
#define INLINEDBG
#define MAX_COSTUMES 10
#define ENTTYPE(e) ((e)->type)
#define TEST_CLIENT 1
#define CC_EMOTE_BASIC_TIMEOUT 5
#define CC_EMOTE_IGNORE_EXTRA_TIMEOUT 15
#define SEQ_LOAD_FULL 1
#define MENU_LOAD_POWER_CUST 1
#define MENU_GENDER 2
#define MENU_BODY 3
#define MENU_TAILOR 4
#define MENU_SUPERCOSTUME 5
#define MENU_SUPER_REG 6
#define MENU_LOADCOSTUME 7
#define MENU_SAVECOSTUME 8
#define TODO() assert(0)
#define log_printf(...)
#define Strncpyt(dst,src) do{assert(strlen(src)<sizeof(dst));strcpy(dst,src);}while(0)
typedef struct {const char *reward;} RewardToken;
typedef struct {uint32_t crcFullName;const char *pchFullName;} BasePower;
typedef struct {const char *powerFullName;const BasePower *power;struct {Color primary,secondary;} customTint;const char *token;} PowerCustomization;
typedef struct {PowerCustomization **powerCustomizations;} PowerCustomizationList;
typedef struct {
 int pendingCostumeForceTime,current_costume,current_powerCust,num_costume_slots,num_costumes_stored,supergroup_mode,hide_supergroup_emblem,npc_costume;
 int pendingCostumeIgnoreTime,pendingCostumeNumber;
 Costume *costume[10],*superCostume,*pendingCostume;PowerCustomizationList *powerCustomizationLists[10];
 RewardToken **rewardTokens,**ArchitectRewardTokens;
 char costumeFxSpecial[260];
} Player;
typedef struct {struct {const char *name;} *type;} SeqInst;
typedef struct {
 int type,npcIndex,costumeIndex,send_all_costume,supergroup_id,randSeed,next_move_idx,next_move_bits,updated_powerCust,send_all_powerCust;
 PowerCustomizationList *ownedPowerCustomizationList,*powerCust;
 Player *pl;SeqInst *seq;Costume *ownedCostume;const Costume *costume;
 CustomNPCCostume *customNPC_costume;const char *costumeWorldGroup;const char *name;
} Entity;
static Entity *fixture_player;
static Entity *playerPtr(void){return fixture_player;}
static int demo_recording,ent_create,g_costume_apply_hack;
static Costume *dummy_ent_costume,*fixture_npc_costume;
static int menuCanSetCostumeAndPowerCust(void){return 1;}
static int isMenu(int v){(void)v;return 0;}
static int shell_menu(void){return 0;}
static int timerSecondsSince2000(void){return 10;}
static void costume_Apply(Entity *e){(void)e;}
static Costume *costume_as_const(Costume *c){return c;}
static Costume *costume_current(Entity *e){return e->pl->costume[e->pl->current_costume];}
static Costume *costume_makeSupergroup(Entity *e){return e->pl->superCostume;}
static Costume allocated_costumes[4];static CostumePart allocated_parts[4][30];static unsigned allocated_count;
static Costume *costume_create(int n){Costume *c;unsigned i;(void)n;assert(allocated_count<4);c=&allocated_costumes[allocated_count];memset(c,0,sizeof(*c));for(i=0;i<30;i++)c->parts[i]=&allocated_parts[allocated_count][i];allocated_count++;return c;}
static void costume_init(Costume *c){init_costume(c);}
static Costume *npcDefsGetCostume(int n,int c){(void)n;(void)c;return fixture_npc_costume;}
static Costume *entUseCopyOfCostume(Entity *e,Costume *c){e->costume=c;return c;}
static Costume *entUseCopyOfCurrentCostumeAndOwn(Entity *e){return (Costume*)e->costume;}
static void costumeApplyNPCColorsToCostume(Costume *c,CustomNPCCostume *n){(void)c;(void)n;}
static void tailor_exit(int v){(void)v;}
static SeqInst *seqLoadInst(char *s,int n,int mode,int seed,Entity *e){static struct {const char *name;} t;static SeqInst seq;(void)n;(void)mode;(void)seed;(void)e;t.name=s;seq.type=(void*)&t;return &seq;}
static void entSetSeq(Entity *e,SeqInst *s){e->seq=s;}
static void demoRecordAppearance(Entity *e){(void)e;}
static void demoRecordMove(Entity *e,int a,int b){(void)e;(void)a;(void)b;}
/* Fixture name is already canonical. Asset FX normalization is unresolved. */
static void fxCleanFileName(char *dst,const char *src){assert(!strcmp(src,"FIXTUREFX"));if(dst!=src)strcpy(dst,src);}
static char world_strings[16][260];static unsigned world_count;
static char *fixture_strdup(const char *s){assert(world_count<16&&strlen(s)<260);strcpy(world_strings[world_count],s);return world_strings[world_count++];}
#define strdup fixture_strdup
static void fixture_custom_free(CustomNPCCostume *c){for(unsigned i=0;i<custom_count;i++)free(c->parts[i]);free(c);}
#define StructDestroy(fn,p) fixture_custom_free(p)
static RewardToken *reward_ptrs[3],*architect_ptrs[2];
static int fixture_ea_size(void *p){if(p==reward_ptrs)return 3;if(p==architect_ptrs)return 2;return custom_count;}
#undef eaSize
#define eaSize(p) fixture_ea_size((void*)*(p))
static int costume_isReward(const char *s){return strcmp(s,"NotAReward")!=0;}
static const char *received_rewards[2][256];static unsigned received_reward_count[2];
static void costumereward_clear(int n){(void)n;memset(received_rewards,0,sizeof(received_rewards));memset(received_reward_count,0,sizeof(received_reward_count));}
static void costumereward_add(char *s,int arch){assert(arch<2&&received_reward_count[arch]<256);received_rewards[arch][received_reward_count[arch]++]=s;}
