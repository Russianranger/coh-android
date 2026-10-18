/* Executes the production adapter/core with explicit synthetic original and
 * Win32 file providers. It does not execute original Map or a Windows kernel. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include "coh_server_initial_api.h"
typedef uint32_t DWORD;typedef void* HANDLE;typedef struct{long long QuadPart;}LARGE_INTEGER;
typedef struct{DWORD dwFileAttributes,nNumberOfLinks,dwVolumeSerialNumber,nFileIndexHigh,nFileIndexLow,nFileSizeHigh,nFileSizeLow;}BY_HANDLE_FILE_INFORMATION;
#define INVALID_HANDLE_VALUE ((HANDLE)(intptr_t)-1)
#define FILE_ATTRIBUTE_DIRECTORY 1u
#define FILE_ATTRIBUTE_REPARSE_POINT 2u
#define INVALID_FILE_ATTRIBUTES 0xffffffffu
#define GENERIC_WRITE 1u
#define OPEN_EXISTING 3u
#define FILE_ATTRIBUTE_NORMAL 4u
#define FILE_FLAG_OPEN_REPARSE_POINT 8u
#define FILE_BEGIN 0u
#define COH_CATALOG_SINK_PATH_MAX 512u
#define MAX_ENTITIES_PRIVATE 8
#define ENTITY_IN_USE 1
#define ENTITY_SLEEPING 2
#define ENTTYPE_PLAYER 1
#define ENTTYPE(e) ((e)->type)
#define NLT_UDP 2
struct Entity;struct ClientLink;
typedef struct Character{struct Entity*entParent;int initialized;}Character;
typedef struct NetLink{void*userData;unsigned UID,connection_id,connect_id,protocolVersion;int type,connected,pending,connecting,disconnected,destroyed,removedFromMasterList;}NetLink;
typedef struct Entity{struct ClientLink*client;int owner,db_id,type,owned;unsigned id,auth_id;void*pl;Character*pchar;}Entity;
typedef struct ClientLink{NetLink*link;Entity*entity;int ready;}ClientLink;
typedef struct{int size,maxSize;NetLink**storage;}LinkArray;
static struct{LinkArray*links;}net_links;
static int entities_max;static Entity*entities[8];static int entity_state[8];
static struct{DWORD thread;unsigned configured;}coh_groups_capture_file;
static DWORD fake_thread=7,last_error=97;static unsigned writes,closes,failed_write;static size_t extent,cursor;static char content[4096];static BY_HANDLE_FILE_INFORMATION fileinfo;
static DWORD GetCurrentThreadId(void){errno=66;last_error=88;return fake_thread;}
static DWORD GetLastError(void){return last_error;}
static void SetLastError(DWORD e){last_error=e;}
static DWORD GetEnvironmentVariableA(const char*n,char*p,DWORD cap){const char*s="C:\\coh-native-catalog\\server-initial-ledger.json";(void)n;if(strlen(s)>=cap)return cap;strcpy(p,s);return (DWORD)strlen(s);}
static int coh_catalog_sink_path(const char*p,unsigned n){return p&&n>0;}
static DWORD GetFileAttributesA(const char*p){(void)p;return 0;}
static HANDLE CreateFileA(const char*p,DWORD a,DWORD b,void*c,DWORD d,DWORD e,void*f){(void)p;(void)a;(void)b;(void)c;(void)d;(void)e;(void)f;return (HANDLE)(intptr_t)1;}
static int CloseHandle(HANDLE h){(void)h;closes++;return 1;}
static int GetFileInformationByHandle(HANDLE h,BY_HANDLE_FILE_INFORMATION*i){(void)h;*i=fileinfo;i->nFileSizeLow=(DWORD)extent;return 1;}
static int SetFilePointerEx(HANDLE h,LARGE_INTEGER q,void*p,DWORD whence){(void)h;(void)p;(void)whence;cursor=(size_t)q.QuadPart;return 1;}
static int WriteFile(HANDLE h,const void*p,DWORD n,DWORD*w,void*o){(void)h;(void)o;writes++;if(failed_write)return 0;if(cursor+n>sizeof(content))return 0;memcpy(content+cursor,p,n);cursor+=n;if(cursor>extent)extent=cursor;*w=n;return 1;}
static int SetEndOfFile(HANDLE h){(void)h;extent=cursor;return 1;}
static int FlushFileBuffers(HANDLE h){(void)h;return 1;}
static int character_IsInitialized(Character*c){return c->initialized;}
#include "source_adapter.inc"
static unsigned checks;
#define CHECK(v) do{checks++;if(!(v)){fprintf(stderr,"ADAPTER_CONTROL_FAILURE:%u\n",__LINE__);exit(2);}}while(0)
static NetLink link;static ClientLink client;static Entity entity;static Character character;static LinkArray list;static NetLink*storage[1];static int packet;
static void reset(void){memset(&coh_sio_ledger,0,sizeof(coh_sio_ledger));coh_sio_started=coh_sio_configured=coh_sio_write_failed=coh_sio_writes=0;memset(&coh_sio_last_written,0,sizeof(coh_sio_last_written));coh_sio_handle=INVALID_HANDLE_VALUE;writes=closes=failed_write=0;extent=cursor=0;fake_thread=7;fileinfo=(BY_HANDLE_FILE_INFORMATION){0,1,2,3,4,0,0};
 memset(&link,0,sizeof(link));memset(&client,0,sizeof(client));memset(&entity,0,sizeof(entity));character.entParent=&entity;character.initialized=1;client.link=&link;client.entity=&entity;client.ready=1;entity.client=&client;entity.owner=1;entity.db_id=11;entity.id=12;entity.auth_id=13;entity.type=1;entity.owned=1;entity.pl=&packet;entity.pchar=&character;link.userData=&client;link.type=NLT_UDP;link.connected=1;link.UID=14;link.connection_id=15;link.connect_id=16;link.protocolVersion=5;entities_max=2;entities[1]=&entity;entity_state[1]=ENTITY_SLEEPING;storage[0]=&link;list=(LinkArray){1,1,storage};net_links.links=&list;coh_groups_capture_file.thread=7;coh_groups_capture_file.configured=1;errno=41;last_error=42;
}
static void ev(unsigned e,const void*p,unsigned a,unsigned b){errno=41;last_error=42;coh_sio_source_event(e,&link,&entity,p,a,b,0);CHECK(errno==41&&last_error==42);}
int main(void){unsigned before,i;CohSIOLedger saved;
 reset();coh_sio_source_bind_groups(&link);CHECK(errno==41&&last_error==42&&coh_sio_ledger.report.groups_owner_bound&&writes==1&&extent>0);CHECK(entity_state[1]==ENTITY_SLEEPING&&client.ready==1);
 saved=coh_sio_ledger;before=writes;fake_thread=8;errno=41;last_error=42;coh_sio_source_character(COH_SIO_CHARACTER_ENTER,&entity,&packet);CHECK(!memcmp(&saved,&coh_sio_ledger,sizeof(saved))&&writes==before&&errno==41&&last_error==42);coh_sio_source_finish_entity(&entity,&packet);CHECK(errno==41&&last_error==42);fake_thread=7;
 ev(COH_SIO_DISPATCH,NULL,0,0);ev(COH_SIO_REQUEST_STATE,NULL,1,0);for(i=0;i<1000;i++){ev(COH_SIO_TICK,NULL,1,0);ev(COH_SIO_BACKPRESSURE_ENTER,NULL,0,0);ev(COH_SIO_BACKPRESSURE_PASS,NULL,0,0);ev(COH_SIO_MAPXFER_ENTER,NULL,0,0);ev(COH_SIO_MAPXFER_RETURN,NULL,0,0);}CHECK(coh_sio_ledger.report.valid&&writes<30&&coh_sio_ledger.report.tick_seen==1000);
 ev(COH_SIO_SELECTED,NULL,0,0);ev(COH_SIO_FULL_ENTER,NULL,1,1);ev(COH_SIO_ALLENTS_HEADER,&packet,0,0);
 errno=41;last_error=42;coh_sio_source_character(COH_SIO_CHARACTER_ENTER,&entity,&packet);CHECK(errno==41&&last_error==42);coh_sio_source_character(COH_SIO_CHARACTER_CORE_ENTER,&entity,&packet);coh_sio_source_character(COH_SIO_CHARACTER_CORE_RETURN,&entity,&packet);ev(COH_SIO_CHARACTER_RETURN,&packet,0,0);ev(COH_SIO_ATTACHED,&packet,0,0);coh_sio_source_finish_entity(&entity,&packet);ev(COH_SIO_SEND_BEGIN,&packet,200000,7);coh_sio_source_send_return((uintptr_t)&entity,1);CHECK(coh_sio_ledger.send_pending&&!coh_sio_ledger.report.pkt_send_returned);errno=41;last_error=42;coh_sio_source_send_return((uintptr_t)&packet,0);CHECK(errno==41&&last_error==42&&coh_sio_ledger.report.stop==COH_SIO_FINAL_RETURN&&closes==1&&!coh_sio_ledger.key.link);CHECK(extent>0);printf("ADAPTER_SNAPSHOT %.*s",(int)extent,content);
 reset();coh_sio_source_bind_groups(&link);storage[0]=NULL;ev(COH_SIO_TICK,NULL,1,0);CHECK(coh_sio_ledger.report.refusal==COH_SIO_OWNER&&!coh_sio_ledger.key.link&&closes==1);
 reset();coh_sio_source_bind_groups(&link);link.connection_id++;ev(COH_SIO_TICK,NULL,1,0);CHECK(coh_sio_ledger.report.refusal==COH_SIO_OWNER);
 reset();coh_sio_source_bind_groups(&link);failed_write=1;ev(COH_SIO_DISPATCH,NULL,0,0);CHECK(coh_sio_ledger.report.refusal==COH_SIO_SINK&&extent==0&&closes==1);
 reset();entity.client=NULL;coh_sio_source_character(COH_SIO_CHARACTER_ENTER,&entity,&packet);CHECK(!coh_sio_started&&writes==0);entity.client=&client;
 reset();fake_thread=8;coh_sio_source_bind_groups(&link);CHECK(!coh_sio_started&&writes==0);fake_thread=7;coh_sio_source_bind_groups(&link);CHECK(coh_sio_ledger.report.valid);
 reset();coh_sio_source_bind_groups(&link);coh_sio_writes=128;ev(COH_SIO_DISPATCH,NULL,0,0);CHECK(coh_sio_ledger.report.refusal==COH_SIO_LIMIT&&closes==1);
 reset();coh_sio_source_bind_groups(&link);errno=41;last_error=42;coh_sio_source_retire_entity(&entity);CHECK(errno==41&&last_error==42&&coh_sio_ledger.report.refusal==COH_SIO_OWNER&&!coh_sio_ledger.key.link&&closes==1);
 reset();coh_sio_source_bind_groups(&link);coh_sio_source_send_return((uintptr_t)&packet,0);CHECK(coh_sio_ledger.report.valid&&!coh_sio_ledger.report.pkt_send_returned);
 printf("ADAPTER_CONTROLS checks=%u\n",checks);return 0;
}
