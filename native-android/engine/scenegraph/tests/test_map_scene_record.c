#define main mapclient_regression_main
#include "../../mapclient/tests/test_mapclient.c"
#undef main
#include "coh_map_scene_record.h"
#include <openssl/sha.h>
static size_t record_alive,record_allocs,record_fault,record_seen;
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void __real_free(void*);
void *__wrap_malloc(size_t n){record_allocs++;if(record_fault&&++record_seen==record_fault)return NULL;void*p=__real_malloc(n);if(p)record_alive++;return p;}
void *__wrap_calloc(size_t n,size_t z){record_allocs++;if(record_fault&&++record_seen==record_fault)return NULL;void*p=__real_calloc(n,z);if(p)record_alive++;return p;}
void __wrap_free(void*p){if(p){CHECK(record_alive);record_alive--;}__real_free(p);}
static CohStatus record_digest(void*c,CohBytes b,uint8_t out[32]){(void)c;return SHA256(b.data,b.size,out)?COH_OK:COH_STATE;}
static CohStatus record_digest_fail(void*c,CohBytes b,uint8_t out[32]){(void)c;(void)b;(void)out;return COH_STATE;}
typedef struct {unsigned calls,at;} RecordCancel;
static int record_cancel(void*c){RecordCancel*s=c;return ++s->calls==s->at;}
typedef struct {CohMapClient*client,*other;CohMapSceneRecord*record;unsigned calls;CohBytes expected;size_t bits;CohMapSceneObservation copied;} RecordTest;
static void record_scene(void*context,const CohMapSceneObservation*event){
 RecordTest*t=context;t->calls++;CohMapSceneRecordReport report,guard;memset(&report,0x5a,sizeof(report));guard=report;CohMapSceneRecordBudget b={COH_SG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,262144};CohCatalogDigest d={NULL,record_digest};CohMapSceneRecord*candidate=NULL;size_t baseline=record_alive;
 CohMapSceneObservation copy=*event;t->copied=copy;CHECK(coh_map_scene_record_create(t->client,&copy,&b,&d,NULL,&candidate,&report)==COH_STATE&&!candidate&&!memcmp(&guard,&report,sizeof(guard)));
 CHECK(coh_map_scene_record_create(t->other,event,&b,&d,NULL,&candidate,&report)==COH_STATE&&!candidate);
 CHECK(coh_map_scene_record_create(t->client,event,&b,&d,NULL,&candidate,(CohMapSceneRecordReport*)event)==COH_INVALID&&!candidate);
 CHECK(coh_map_scene_record_create(t->client,event,&b,&d,NULL,&candidate,(CohMapSceneRecordReport*)event->reader.bytes.data)==COH_INVALID&&!candidate);
 CohCatalogDigest failed={NULL,record_digest_fail};CHECK(coh_map_scene_record_create(t->client,event,&b,&failed,NULL,&candidate,&report)==COH_STATE&&!candidate&&record_alive==baseline&&!memcmp(&guard,&report,sizeof(guard)));
 for(unsigned f=1;f<=2;f++){record_fault=f;record_seen=0;CHECK(coh_map_scene_record_create(t->client,event,&b,&d,NULL,&candidate,&report)==COH_LIMIT&&!candidate);record_fault=0;CHECK(record_alive==baseline&&!memcmp(&guard,&report,sizeof(guard)));}
 for(unsigned at=1;at<=2;at++){RecordCancel cs={0,at};CohCancel c={.poll=record_cancel,.context=&cs};CHECK(coh_map_scene_record_create(t->client,event,&b,&d,&c,&candidate,&report)==COH_CANCELLED&&!candidate&&record_alive==baseline&&!memcmp(&guard,&report,sizeof(guard)));}
 CHECK(coh_map_scene_record_create(t->client,event,&b,&d,NULL,&t->record,&report)==COH_OK&&t->record);
 CHECK(report.actual_client_loan_verified&&!report.session_owner_retained&&!report.receive.selected_dbid_owner_bound&&!report.receive.source_generation_admitted&&!report.receive.world_authority);
 CHECK(report.receive.reader.bytes.data!=event->reader.bytes.data&&report.receive.reader.bytes.size==t->expected.size&&report.receive.reader.bits==t->bits&&report.receive.reader.cursor==event->reader.cursor&&!memcmp(report.receive.reader.bytes.data,t->expected.data,t->expected.size));
 uint8_t sha[32];CHECK(record_digest(NULL,t->expected,sha)==COH_OK&&!memcmp(sha,report.packet_sha256,32));
 b.owned_limit=report.owned_bytes-1;size_t allocations=record_allocs;CHECK(coh_map_scene_record_create(t->client,event,&b,&d,NULL,&candidate,&guard)==COH_LIMIT&&!candidate&&allocations==record_allocs);
 b.owned_limit=COH_SG_MEMORY_MAX;b.aggregate_limit=report.aggregate_reserved_bytes-1;CHECK(coh_map_scene_record_create(t->client,event,&b,&d,NULL,&candidate,&guard)==COH_LIMIT&&!candidate&&allocations==record_allocs);
 b.aggregate_limit=report.aggregate_reserved_bytes;CHECK(coh_map_scene_record_create(t->client,event,&b,&d,NULL,&candidate,&guard)==COH_OK);coh_map_scene_record_release(candidate);
 CHECK(coh_map_scene_record_view(t->record,(CohMapSceneRecordReport*)t->record)==COH_INVALID);CHECK(coh_map_scene_record_view(t->record,(CohMapSceneRecordReport*)report.receive.reader.bytes.data)==COH_INVALID);
 CHECK(coh_map_scene_record_retain(t->record)==COH_OK);coh_map_scene_record_release(t->record);
}
int main(void){
 for(unsigned profile=0;profile<6;profile++){
  unsigned large=profile>=2,aligned=profile!=0,ordered=large?(profile&1):0;Peer p=peer_open();CohMapConfig c=configuration(p,5);CohMapClient*m=coh_map_client_create(&c),*other=coh_map_client_create(&c);CHECK(m&&other);uint64_t now=handshake(m,p,5,aligned,12345,91,100,1);
  CohNetPacket scene=scene_prefix(5,aligned,200);RecordTest t={.client=m,.other=other,.expected={scene.payload,(scene.payload_bits+7)/8},.bits=scene.payload_bits};
  if(large){uint8_t encoded[COH_NET_MESSAGE_MAX];size_t bytes=scene_fixture_encode(SCENE_FIXTURE_DECODED_BYTES,COH_REP_GROUPS,(int)ordered,encoded,sizeof(encoded));send_encoded(p,local(m),5,encoded,bytes,200,ordered);t.expected=(CohBytes){source_groups_large_world_byte_aligned,sizeof(source_groups_large_world_byte_aligned)};t.bits=source_groups_large_world_byte_aligned_bits;}else send_packet(p,local(m),5,scene);
  CHECK(coh_map_client_service_observed(m,now++,(CohCancel){0},record_scene,&t)==COH_UNSUPPORTED&&t.calls==1);drain_idle(p,5);CHECK(diagnostics(m).phase==COH_MAP_SCENE_INCOMPLETE&&diagnostics(m).udp.link.owned_retained_bytes==0);
  CohMapSceneRecordReport r,guard;memset(&r,0x5a,sizeof(r));guard=r;CohMapSceneRecord*bad=NULL;CohMapSceneRecordBudget b={COH_SG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,0};CohCatalogDigest d={NULL,record_digest};CHECK(coh_map_scene_record_create(m,&t.copied,&b,&d,NULL,&bad,&r)==COH_STATE&&!bad&&!memcmp(&r,&guard,sizeof(r)));
  CHECK(coh_map_scene_record_view(t.record,&r)==COH_OK&&r.receive.message_id==200&&r.receive.connection_id==91&&r.receive.ordered==ordered&&r.receive.ordered_id==ordered);
  coh_map_client_destroy(m);coh_map_client_destroy(other);peer_close(p);
  CHECK(coh_map_scene_record_view(t.record,&r)==COH_OK&&!memcmp(r.receive.reader.bytes.data,t.expected.data,t.expected.size));CohRepReader replay=r.receive.reader;CohGroupsInspection inspection;CHECK(coh_rep_groups(&replay,&inspection,NULL)==COH_OK&&!memcmp(&inspection,&r.receive.inspection,sizeof(inspection)));coh_map_scene_record_release(t.record);CHECK(record_alive==0);
 }
 printf("{\"passed\":true,\"checks\":%u,\"actual_os_udp\":true,\"scripted_peer_only\":true,\"selected_dbid_owner_bound\":false,\"source_generation_admitted\":false,\"world_authority\":false}\n",checks);return 0;
}
