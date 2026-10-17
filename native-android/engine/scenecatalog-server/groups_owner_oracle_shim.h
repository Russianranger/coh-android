/* Explicit bounded HOST storage only. Original ClientLink/Array/enums are
 * inserted unchanged; Entity/Character/NetLink expose source-verified member
 * subsets, never original ABI/Win32 layouts. External services only observe. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <signal.h>
#include <sys/wait.h>
#include <unistd.h>
#include <sys/resource.h>
typedef unsigned U32;typedef unsigned char U8;typedef float F32;typedef float Vec3[3];
typedef struct Entity Entity;typedef struct Character Character;typedef struct EntNetLink EntNetLink;typedef void*StashTable;
typedef struct {int nocoll;} ControlState;
/* ORIGINAL_TYPES */
typedef struct NetLink {
 NetLinkType type;NetLinkOperationType opType;U32 UID;void*userData;
 U32 connected:1,pending:1,connecting:1,disconnected:1,destroyed:1,removedFromMasterList:1;
 U32 compressionAllowed:1,compressionDefault:1,orderedAllowed:1,orderedDefault:1,controlCommandsSeparate:1,cookieSend:1,cookieEcho:1;
 U32 protocolVersion,connection_id,connect_id,last_update_time;int last_world_id;
 U32 last_processed_id,last_recv_id,last_ordered_recv_id;
 void (*packetSentCallback)(void);
} NetLink;
/* ORIGINAL_CLIENT_LINK */
struct Entity {int owner;U32 id;int db_id;U32 auth_id;int map_id,static_map_id;ClientLink*client;Character*pchar;DbFlag db_flags;U8 ready:1;};
typedef struct CharacterClass {unsigned opaque_fixture_only;} CharacterClass;
static CharacterClass fixture_class;
struct Character {Entity*entParent;const CharacterClass*pclass;};
typedef struct {Array*links;} NetLinkList;
static NetLinkList net_links;static Entity*entities[MAX_ENTITIES_PRIVATE];static U8 entity_state[MAX_ENTITIES_PRIVATE];static int entities_max,world_id;static Vec3 entpos[MAX_ENTITIES_PRIVATE];
/* ORIGINAL_POSITION_MACROS */
static unsigned checks,position_calls,log_queries,flush_calls;static int log_enabled,last_log_dbid;static const Entity*position_entity;static const F32*position_pointer;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"owner check line%d: %s\n",__LINE__,#x);abort();}}while(0)
static void entUpdatePosInstantaneous(Entity*e,const F32*p){position_calls++;position_entity=e;position_pointer=p;}
static int clientPacketLogIsEnabled(int dbid){log_queries++;last_log_dbid=dbid;return log_enabled;}
static void clientPacketSentCallback(void){abort();}
static void lnkFlush(NetLink*link){CHECK(link!=NULL);flush_calls++;}
#define INLINEDBG inline
