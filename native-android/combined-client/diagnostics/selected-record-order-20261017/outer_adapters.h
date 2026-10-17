/* Host fixture shells for unchanged sendEntity control flow. No child grammar
 * is implemented here. Every injected child span must be qualified separately. */
#include <limits.h>
#define DEFAULT_CLIENT_INTERP_DATA_LEVEL 0
#define DEFAULT_CLIENT_INTERP_DATA_PRECISION 0
#define TSTB(a,b) (1)
#define SETB(a,b) ((void)0)
#define ENTINFO(e) (*fixture_info(e))
#define CLAMP(v,a,b) ((v)<(a)?(a):(v)>(b)?(b):(v))
#define SAFE_MEMBER(p,m) ((p)?(p)->m:0)
#define STATIC_INFUNC_ASSERT(v) ;
#define PERFINFO_AUTO_START(a,b) ((void)0)
#define CONFUSED_COSTUMES 0
typedef struct FixtureEntity Entity;
typedef struct {int send_afk_string,titleThe,titleColors[2],titleBadge,glowieUnlocked,attachArticle,respecTokens,lastTurnstileEventID,lastTurnstileMissionID,helperStatus,playerType,playerSubType,praetorianProgress,pvpSwitch,bIsGanker;char *titleTheText,*titleCommon,*titleOrigin,*titleSpecial;} Player;
typedef struct {int iCombatModShiftToSendToClient,iAllyID,iGangID,bIgnoreCombatMods,ignoreCombatModLevelShift,playerTypeByLocation,bPvPActive;} Character;
struct FixtureEntity {int pos_update,qrot_update,move_update,logout_update,supergroup_update,team_update,levelingpact_update,draw_update,collision_update,pvp_update,petinfo_update,send_on_odd_send_update,status_effects_update,tf_params_update,send_all_costume,send_all_powerCust,send_costume,send_xlucency,updated_powerCust,cached_send_packet,resend_hp,lastticksent,triggered_move_count,netfx_count,level_update,target_update,bitfieldVisionPhases,exclusiveVisionPhase,shouldIConYellow,helper_status_update,name_update,gender,name_gender,notSelectable,noDrawOnClient,showOnMap,contactOrPnpc,contactArchitect,alwaysCon,seeThroughWalls;float xlucency,pvpZoneTimer;struct{int mode,last_sent_mode;}state;struct{int net_prepared,send_on_odd_send;}info;struct{struct{int no_ent_collision;}input;}*motion;Player*pl;Character*pchar;void*taskforce;void*erOwner;char*name;Packet*send_packet;};
static unsigned taskforce_started,taskforce_end;
static __typeof__(((Entity*)0)->info)*fixture_info(Entity*e){if(taskforce_started)taskforce_end=bsGetCursorBitPosition(&packet.stream);return &e->info;}
static struct {Entity*player_ent;Packet*destpak;int full_update,last_idx_sent,is_generic_pos_update;struct{unsigned*sent_ids;}*sent_buf;}send_ent;
static struct{int global_frame_count;}global_state;
static struct{int is_endgame_raid;}db_state;
static unsigned need_to_send_cache[8];
static int determineNeedToSend(int idx){(void)idx;assert(0);return 0;}
static Entity*erGetEnt(void*p){(void)p;assert(0);return NULL;}
static int pktGetDebugInfo(void){return 0;}
static Packet*pktCreate(void){assert(0);return NULL;}
static void pktAppend(Packet*a,Packet*b){(void)a;(void)b;assert(0);}
enum {CH_CREATE=1,CH_MODES,CH_POSITION,CH_QROT,CH_SEQUENCE,CH_TRIGGERS,CH_AI,
 CH_NETFX,CH_COSTUME,CH_POWER,CH_RAGDOLL,CH_STATS,CH_TARGET,CH_STATUS,
 CH_INVENTORY,CH_ARCHITECT,CH_PARAMS,CH_PET,CH_AFK,CH_SUPERGROUP,CH_PACT,
 CH_LOGOUT,CH_TEAMMATE,CH_COUNT};
typedef struct{const U8*data;unsigned bits,required_mod8;}Child;
static Child children[CH_COUNT];static unsigned events[CH_COUNT*3],event_count;
static void child(Packet*p,unsigned id){
 assert(id>0&&id<CH_COUNT&&event_count<CH_COUNT);Child*c=&children[id];
 unsigned begin=bsGetCursorBitPosition(&p->stream);assert(c->required_mod8==255||(begin&7)==c->required_mod8);
 assert(c->bits<=65536&&(!c->bits||c->data));events[3*event_count]=id;events[3*event_count+1]=begin;
 /* Exact bit-span injection, not calls falsely labelled original serializers.
  * Aligned scalar fixtures must begin/end on bytes. Any explicit child byte
  * alignment must be generated for required_mod8 by its independent provider. */
 unsigned aligned=p->stream.byteAlignedMode;if(aligned)assert(!(begin&7)&&!(c->bits&7));p->stream.byteAlignedMode=0;
 for(unsigned k=0;k<c->bits;k++)bsWriteBits(&p->stream,1,(c->data[k/8]>>(k&7))&1);
 p->stream.byteAlignedMode=aligned;events[3*event_count+2]=bsGetCursorBitPosition(&p->stream);event_count++;
}
#define entSendCreate(p,...) child(p,CH_CREATE)
#define entSendModes(p,...) child(p,CH_MODES)
#define entSendPosUpdate(p,...) child(p,CH_POSITION)
#define entSendQrotUpdate(p,...) child(p,CH_QROT)
#define entSendSeqMoveUpdate(p,...) child(p,CH_SEQUENCE)
#define entSendSeqTriggeredMoves(p,...) child(p,CH_TRIGGERS)
#define entSendAiAnimList(p,...) child(p,CH_AI)
#define entSendNetFx(p,...) child(p,CH_NETFX)
#define entSendCostume(p,...) child(p,CH_COSTUME)
#define entSendPowerCust(p,...) child(p,CH_POWER)
#define entSendRagdollUpdate(p,...) child(p,CH_RAGDOLL)
#define entSendCharacterStats(p,...) child(p,CH_STATS)
#define entSendTargetUpdate(p,...) child(p,CH_TARGET)
#define character_SendStatusEffects(p,...) child(p,CH_STATUS)
#define character_SendInventorySizes(c,p) child(p,CH_INVENTORY)
#define entSendTaskforceArchitectInfo(e,p) child(p,CH_ARCHITECT)
#define entSendTaskforceParameters(t,p) child(p,CH_PARAMS)
#define entSendPetInfo(p,...) child(p,CH_PET)
#define entSendAfk(p,...) child(p,CH_AFK)
#define entSendOtherSupergroupInfo(p,...) child(p,CH_SUPERGROUP)
#define entSendLevelingpactInfo(p,...) child(p,CH_PACT)
#define entSendLogoutUpdate(p,...) child(p,CH_LOGOUT)
#define appendTeammatePacket(p,...) child(p,CH_TEAMMATE)
static unsigned flashback;
static unsigned TaskForceIsOnFlashback(Entity*e){(void)e;taskforce_started=1;return flashback;}
