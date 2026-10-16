/* Deterministic source-function harness only. This is not game simulation. */
typedef float F32;typedef int32_t S32;typedef uint16_t U16;typedef float Vec3[3];
#define TEST_CLIENT 1
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define copyVec3(a,b) memcpy((b),(a),sizeof(Vec3))
#define sameVec3(a,b) (!memcmp((a),(b),sizeof(Vec3)))
#define vecParamsXYZ(a) (a)[0],(a)[1],(a)[2]
#define START_BIT_COUNT(a,b) ((void)0)
#define STOP_BIT_COUNT(a) ((void)0)
#define ABS_TIME 123456u
#define ENTPOS(e) ((e)->pos)
#define CONTROLID_RUN_PHYSICS 1
#define CONTROLID_APPLY_SERVER_STATE 2
#define CSC_ANGLE_F32_TO_U32(x) ((U32)0)
#define RAD(x) ((x)*0.017453292519943295f)
#define COLOR_BRIGHT 1
#define COLOR_RED 2
enum { SURFPARAM_GROUND, SURFPARAM_AIR, SURFPARAM_MAX };
/* Exact source declarations are inserted before the owner shells. */
typedef struct FuturePush FuturePush;
typedef struct ControlStateChange ControlStateChange;
struct FuturePush {FuturePush *controls_next,*csc_next;ControlStateChange *csc;U16 net_id_start,phys_tick_remaining,phys_tick_wait;U32 abs_time;Vec3 add_vel;U32 net_id_used,do_knockback_anim,was_sent;};
struct ControlStateChange {ControlStateChange *next;int sent,net_id,control_id,no_ack;U32 client_abs,time_stamp_ms,applied_server_state_id;FuturePush *future_push_list;struct{Vec3 pos;}after;};
typedef struct {Vec3 vel;struct{SurfaceParams surf_mods[2];int no_ent_collision,flying;}input;int falling,jumping,hit_stumble;float hitStumbleTractionLoss;} MotionState;
typedef struct {int net_id;Vec3 pos,vel;} PhysStep;
typedef struct {ControlStateChange *head,*tail;int count;} ChangeList;
typedef struct ControlState {
 FuturePush *future_push_list;struct{PhysStep latest,sent;}phys;int record_motion;
 struct{ServerControlState *tail;}queued_server_states;
 int cur_server_state_sent,sent_update_id,server_pos_id,client_pos_id,server_pos_id_sent;
 U32 server_state_pkt_id,server_pos_pkt_id,forced_move_pkt_id;int received_update_id;
 ServerControlState *server_state;int controldebug,first_packet_sent,nosync;
 struct{U32 last_send_ms;}time;ChangeList csc_processed_list;
 struct{Vec3 cur;U32 prev[3],send[3];}pyr;
 Vec3 cam_pyr_offset;struct{PhysStep step[8];int end;}svr_phys;
} ControlState;
typedef struct ClientLink{ControlState controls;}ClientLink;
typedef struct{struct{float fStunned;}attrCur;}Character;
typedef struct{int door_anim;}Player;
typedef struct{ClientLink *client;Character *pchar;Player *pl;MotionState *motion;Vec3 pos;}Entity;
static Entity fixture_entity;static ControlState control_state;static ServerControlState fixture_server;
static FuturePush received_pushes[40];static unsigned received_count;
static struct{int pause;U32 abs_time;}server_visible_state;
static struct{U32 client_abs_latency;}global_state;
static struct{Vec3 pyr,targetPYR;}cam_info;
static int glob_client_pos_id,glob_falling,glob_plrstate_valid;static Vec3 glob_pos,glob_vel;
static Entity *playerPtr(void){return &fixture_entity;}
static int timerCpuSeconds(void){return 100;}
static ServerControlState *getQueuedServerControlState(ControlState *c){assert(c->queued_server_states.tail);return c->queued_server_states.tail;}
static void destroyFuturePush(FuturePush *p){(void)p;}
static FuturePush *addFuturePush(ControlState *c){(void)c;assert(received_count<40);return &received_pushes[received_count++];}
static void pmotionSendPhysicsRecording(Packet *p,Entity *e,const char *n){(void)e;(void)n;pktSendBitsPack(p,1,0);}
static void pmotionReceivePhysicsRecording(Packet *p,Entity *e){(void)e;assert(pktGetBitsPack(p,1)==0);}
static ControlStateChange *createControlStateChange(void){assert(0);return NULL;}
static void addControlStateChange(ChangeList *l,ControlStateChange *c,int n){(void)l;(void)c;(void)n;assert(0);}
static void destroyControlStateChange(ControlStateChange *c){(void)c;assert(0);}
static int DoorAnimIgnorePositionUpdates(void){return 0;}
static float addAngle(float a,float b){return a+b;}
static float distance3(const Vec3 a,const Vec3 b){(void)a;(void)b;assert(0);return 0;}
static void entDebugAddLine(const Vec3 a,U32 b,const Vec3 c,U32 d){(void)a;(void)b;(void)c;(void)d;assert(0);}
static void entDebugAddText(const Vec3 a,const char *b,int c){(void)a;(void)b;(void)c;assert(0);}
static void consoleSetColor(int a,int b){(void)a;(void)b;assert(0);}
static void consoleSetDefaultColor(void){assert(0);}
