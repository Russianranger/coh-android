/* Synthetic owner, power dictionary and UI adapters for exact rare component
 * functions/inline statement blocks. Never an authenticated actor dictionary. */
#define ENTINFO(e) ((e)->net_info)
#define SET_ENTINFO(e) ((e)->net_info)
#define COUNT(...)
#define SAFE_MEMBER(p,f) ((p)?(p)->f:0)
#define MAX_AFK_STRING 48
#define SAFE_FREE(p) do{free(p);(p)=NULL;}while(0)
static char *rare_strdup(const char *s){size_t n=strlen(s)+1;char *p=malloc(n);assert(p);memcpy(p,s,n);return p;}
#define strdup rare_strdup
static Entity *rare_player;
static Entity *playerPtr(void){return rare_player;}
static Entity *entFromId(int id){assert(id>=0&&id<10240);return entities[id];}
static Entity *erGetRef(Entity *e){return e;}
static U32 timerCpuTicks(void){return 12345;}
typedef int PlayerType;typedef int PlayerSubType;typedef int PraetorianProgress;
#define UISKIN_HEROES 0
#define UISKIN_VILLAINS 1
#define UISKIN_FROM_ENT(e) ((e)->pl->playerType)
#define ENT_IS_IN_PRAETORIA(e) ((e)->pl->praetorianProgress!=0)
static void resetVillainHeroDependantStuff(int n){(void)n;}
static void setHeroVillainEventChannel(int n){(void)n;}
static void calcSeqTypeName(void *s,int t,int p,int e){(void)s;(void)t;(void)p;(void)e;}
typedef int PowerDictionary;static PowerDictionary g_PowerDictionary;
static BasePower rare_power={0xa1b2c3d4u};
static const BasePower *powerdict_GetBasePowerByCRC(const PowerDictionary *p,int crc){(void)p;return (U32)crc==rare_power.crcFullName?&rare_power:NULL;}
/* Unknown source power lookup must never silently pass or send traffic. */
#define CLIENT 1
#define CLIENT_BASEPOWER_NOT_FOUND 1
static int comm_link;
static Packet *pktCreateEx(void *l,int n){(void)l;(void)n;abort();return NULL;}
static void pktSend(Packet **p,void *l){(void)p;(void)l;abort();}
static void lnkFlushAll(void){abort();}
