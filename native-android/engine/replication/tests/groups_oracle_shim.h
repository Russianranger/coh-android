/* Trusted host oracle shim; never linked into the Android application.
 * Bounded source structs deliberately contain only fields touched by extracted
 * functions. Unknown/base service calls trap. Values are fixture-owned. */
#include <math.h>
#include <zlib.h>
typedef float F32; typedef double F64;
typedef float Vec3[3], Mat3[3][3], Mat4[4][3];
typedef struct { int has_pos,has_pyr,has_scale; Vec3 pos,pyr,scale; } PackMat;
#define INLINEDBG inline
#define ABS(x) ((x)<0?-(x):(x))
#define SQR(x) ((x)*(x))
#define fsqrt(a) (float)sqrt(a)
#define PI 3.14159265358979323846
#define RAD(a) (((a)*PI)*(1.0f/180.0f))
#define EPSILON 0.00001f
#define NEARZERO(x) (fabs(x)<EPSILON)
#define STATIC_INFUNC_ASSERT(x) ((void)sizeof(char[(x)?1:-1]))
#define devassert(x) (assert(x),(x))
#define MAP_TEAM_COUNT 5
#define MAP_TEAM_EVERYBODY 4
#define MAX_PATH 1024
#define copyVec3(a,b) memcpy((b),(a),sizeof(Vec3))
#define copyMat4(a,b) memcpy((b),(a),sizeof(Mat4))
#define subVec3(a,b,c) do {for(int v3i=0;v3i<3;v3i++)(c)[v3i]=(a)[v3i]-(b)[v3i];} while(0)
#define scaleVec3(a,s,b) do {for(int v3i=0;v3i<3;v3i++)(b)[v3i]=(a)[v3i]*(s);} while(0)
static Mat4 unitmat={{1,0,0},{0,1,0},{0,0,1},{0,0,0}};
static Vec3 zerovec3={0,0,0},onevec3={1,1,1};
static F32 near_same_vec3_tol_squared=0.001f;
static void mathutil_sincosf(float x,float *s,float *c){*s=sinf(x);*c=cosf(x);}
static void bsTypedWriteString(BitStream *s,const char *v){(void)s;(void)v;assert(0);}
static void bsTypedWriteF32(BitStream *s,float v){(void)s;(void)v;assert(0);}
static int auto_bins[]={2,10,24,32};
typedef struct { char name_str[64]; char *value_str; int type; } PropertyEnt;
typedef struct { int count; PropertyEnt *entries[4]; } OracleStash;
typedef OracleStash *StashTable;
typedef PropertyEnt *StashElement;
static void *stashElementGetPointer(StashElement p){return p;}
static int stashGetValidElementCount(StashTable p){return p?p->count:0;}
static void stashForEachElement(StashTable p,int (*f)(StashElement)){if(p)for(int i=0;i<p->count;i++)assert(f(p->entries[i]));}
static Packet *packet;
static int property_send_count;
typedef struct { char *name; } Model;
typedef struct { char *tex_name,*replace_name; int composite; } DefTexSwap;
typedef struct GroupDef GroupDef;
typedef struct { GroupDef *def; Mat4 mat; } GroupEnt;
struct GroupDef {
 int id,in_use,count; char *name; U32 mod_time; GroupEnt *entries;
 F32 lod_scale,lod_near,lod_far,lod_nearfade,lod_farfade;
 int lod_fadenode,no_fog_clip,no_coll,child_parent_fade,parent_fade;
 int child_light,child_ambient,child_volume,child_beacon,open_tracker,child_no_fog_clip;
 F32 sound_radius,shadow_dist;
 int has_light,has_cubemap,has_ambient,lib_ungroupable,has_sound,has_volume,has_fog,has_beacon;
 int has_tint_color,has_tex,has_properties,has_alpha;
 char *type_name; F32 light_radius; U8 color[2][4];
 int cubemapGenSize,cubemapCaptureSize; F32 cubemapBlurAngle,cubemapCaptureTime;
 char *sound_name,*sound_script_filename; int sound_vol; F32 sound_ramp; int sound_exclude;
 F32 fog_near,fog_far,fog_radius,fog_speed; Vec3 box_scale;
 char *beacon_name; F32 beacon_radius; char *tex_names[2]; F32 groupdef_alpha;
 StashTable properties; DefTexSwap **def_tex_swaps; Model *model;
 int hideForGameplay,file_idx,saved;
};
typedef struct Base {U32 mod_time;} Base;
typedef struct {char *fullname;U32 bounds_checksum,mod_time;Base *base;int count,force_reload,modified_on_disk;GroupDef **defs;} GroupFile;
typedef struct {GroupDef *def;Mat4 mat;U32 mod_time;} DefTracker;
static struct {int file_count,ref_count;GroupFile **files;DefTracker **refs;char *loadscreen;} group_info;
static struct {int is_endgame_raid,is_static_map,local_server,instance_id,base_map_id;} db_state;
static struct {int doNotAutoGroup,levelEditor;} server_state;
typedef struct {int teamArea;char **loadScreenPages;} MapSpec;
typedef struct {int introZone;} StaticMapInfo;
typedef struct {char **loadScreenPages;} MissionDef;
static struct {int sahandle;} *g_activemission;
static int world_id,g_MapIsTutorial,g_isBaseRaid,g_baseRaidType;
static Base g_base,**g_raidbases;
static Vec3 *g_baseraidOffsets;
static MapSpec oracle_spec;
static StaticMapInfo oracle_static_info;
static int oracle_has_spec,oracle_aligned,oracle_groups_command=6;
static int oracle_base_header_only;
#define SERVER_GROUPS oracle_groups_command
static const MapSpec *MapSpecFromMapId(int id){(void)id;return oracle_has_spec?&oracle_spec:0;}
static StaticMapInfo *staticMapInfoFind(int id){(void)id;return oracle_has_spec?&oracle_static_info:0;}
static const MissionDef *TaskMissionDefinition(const int *p){(void)p;assert(0);return 0;}
/* Earray identity/size is supplied by the trusted fixture registry, not an ABI
 * claim about engine layout. Traversal order is fixed for deterministic stash. */
static struct {const void *data;int count;} oracle_arrays[1024];
static int oracle_array_count;
static int eaSize(const void *address){const void *data=*(const void*const*)address;if(!data)return 0;for(int i=0;i<oracle_array_count;i++)if(oracle_arrays[i].data==data)return oracle_arrays[i].count;assert(0);return 0;}
static void register_array(const void *data,int count){assert(oracle_array_count<1024);oracle_arrays[oracle_array_count].data=data;oracle_arrays[oracle_array_count++].count=count;}
/* Only the unsupported-base HEADER negative fixture may reach this service.
 * Its nested body is deliberately absent and is never labeled complete. */
static void baseSendAll(Packet *p,Base *b,U32 m,int f){(void)p;(void)b;(void)m;(void)f;assert(oracle_base_header_only);}
static int sgRaidGetBaseRaidSGID(int i){(void)i;assert(0);return 0;}
static int sgRaidGetBaseRaidRaidID(int i){(void)i;assert(0);return 0;}
static int journalUndosRemaining(void){return 2;}
static int journalRedosRemaining(void){return 1;}
static int beaconGetReadFileVersion(void){return 1;}
static void errorSetVerboseLevel(int n){(void)n;}
#define verbose_printf(...) ((void)0)
static U32 oracle_storage[262146];
static Packet oracle_packet;
void pktSetCompression(Packet *,int);
/* Source pktCreate starts byteAligned true, then applies the network default.
 * We retain bounded storage and select only compressionDefault0/1 explicitly;
 * the unchanged compression/mode helpers below perform the actual transition.
 * Packed defaults match source versions0,2..5, aligned defaults version1. */
static Packet *pktCreate(void){memset(oracle_storage,0,sizeof(oracle_storage));memset(&oracle_packet,0,sizeof(oracle_packet));initBitStream(&oracle_packet.stream,(U8*)oracle_storage,sizeof(oracle_storage)-8,Write,1,0);pktSetCompression(&oracle_packet,oracle_aligned);return &oracle_packet;}
static U32 pktGetSize(Packet *p){return (p->stream.bitLength+7)/8;}
static void pktSend(Packet **p,NetLink *l){(void)l;assert(*p==&oracle_packet);assert(!(*p)->stream.errorFlags);*p=0;}
/* zlib is an independent adapter for the digest primitive. Exact original
 * groupInfo checksum traversal runs below; Final reproduces Crypto++'s four
 * big-endian digest bytes before the source little-endian numeric load. */
static uLong oracle_adler;
static void cryptAdler32Init(void){oracle_adler=adler32(0,0,0);}
static void cryptAdler32Update(const void *data,int len){assert(len>=0);oracle_adler=adler32(oracle_adler,data,(uInt)len);}
static U32 cryptAdler32Final(void){U32 n=(U32)oracle_adler;return ((n&255)<<24)|((n&65280)<<8)|((n>>8)&65280)|(n>>24);}
