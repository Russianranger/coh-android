#define main source_mapclient_regression_main
#include "../../mapclient/tests/test_mapclient.c"
#undef main
#include "coh_runtime_groups.h"
#include <openssl/sha.h>
static CohBytes udp_load(const char *name){FILE *f=fopen(name,"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0);rewind(f);unsigned char *p=malloc((size_t)n);CHECK(p);CHECK(fread(p,1,(size_t)n,f)==(size_t)n);fclose(f);return(CohBytes){p,(size_t)n};}
static CohStatus udp_digest(void *context,CohBytes b,uint8_t out[32]){(void)context;return SHA256(b.data,b.size,out)?COH_OK:COH_INVALID;}
typedef struct {const CohRuntimeGraph *graph;const CohCatalogOwner *owner;CohMapClient *client;CohBytes wire;CohMapDiagnostics before;CohRuntimeGroupsReport report,prior;CohStatus wanted;unsigned calls;} Composition;
static void correlate(void *context,const CohMapSceneObservation *event){
 Composition *c=context;c->calls++;CHECK(c->calls==1);CHECK(event->reader.cursor==32&&event->reader.compressed==1&&event->reader.bits==c->wire.size*8);CHECK(event->reader.bytes.size==c->wire.size&&!memcmp(event->reader.bytes.data,c->wire.data,c->wire.size));
 CHECK(event->map_generation==c->before.generation&&event->selection_generation==c->before.selection_generation);CHECK(event->selected_slot==c->before.selected_slot&&event->selected_dbid==c->before.selected_dbid);CHECK(event->map_id==c->before.map_id&&event->map_link_id==c->before.map_link_id&&event->local_development_authorized==c->before.local_development_authorized);
 if(c->wire.size>COH_REP_MESSAGE_MAX)CHECK(diagnostics(c->client).udp.link.owned_retained_bytes==c->wire.size);
 CohRepReader before=event->reader;CohRuntimeGroupsBudget b={COH_SG_TRANSACTION_MAX,32u*1024u*1024u};
 CHECK(coh_runtime_graph_compare_groups(c->graph,c->owner,&event->reader,&b,&c->report)==c->wanted);CHECK(!memcmp(&before,&event->reader,sizeof(before)));
 if(c->wanted==COH_OK)CHECK(!c->report.world_authority&&!c->report.source_generation_admitted&&!c->report.assets_admitted);
 else CHECK(!memcmp(&c->report,&c->prior,sizeof(c->report)));
}
static void send_part(Peer p,CohNetEndpoint to,const uint8_t *data,size_t bytes,unsigned part,unsigned count){
 CohNetPacket packet={0};packet.id=200+part;packet.compressed=1;packet.sibling_id=200;packet.sibling_count=count;packet.sibling_part=part;
 size_t offset=(size_t)part*COH_NET_PAYLOAD_MAX,n=bytes-offset;if(n>COH_NET_PAYLOAD_MAX)n=COH_NET_PAYLOAD_MAX;memcpy(packet.payload,data+offset,n);packet.payload_bits=(uint32_t)n*8;
 uint8_t frame[COH_PROTOCOL_FRAME_MAX];size_t size;CHECK(coh_net_frame_encode(5,NULL,0,&packet,frame,sizeof(frame),&size)==COH_OK);struct sockaddr_in target=address(to);CHECK(sendto(p.fd,frame,size,0,(struct sockaddr*)&target,sizeof(target))==(ssize_t)size);
}
int main(int argc,char **argv){
 CHECK(argc==4);unsigned descriptors=fd_count();CohBytes catalog=udp_load(argv[1]),snapshot=udp_load(argv[2]),wire=udp_load(argv[3]);CHECK(wire.size>COH_REP_MESSAGE_MAX&&wire.size<=COH_NET_DECODED_MAX);
 uint32_t generation=(uint32_t)catalog.data[20]|(uint32_t)catalog.data[21]<<8|(uint32_t)catalog.data[22]<<16|(uint32_t)catalog.data[23]<<24;
 CohCatalogBinding cb={0};cb.owner_generation=1;cb.catalog_generation=generation;cb.asset_generation=generation;memset(cb.source_sha256,0x11,32);memset(cb.inventory_sha256,0x33,32);CHECK(udp_digest(NULL,catalog,cb.catalog_sha256)==COH_OK);
 CohCatalogOwner *owner=NULL,*other=NULL;CohCatalogOwnerBudget ob={COH_SG_MEMORY_MAX,COH_SG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,262144};CohCatalogDigest digest={NULL,udp_digest};CohCatalogOwnerReport owner_report;
 CHECK(coh_catalog_owner_create(NULL,catalog,&cb,&ob,&digest,&owner,&owner_report)==COH_OK);CHECK(coh_catalog_owner_create(NULL,catalog,&cb,&ob,&digest,&other,&owner_report)==COH_OK);CohBytes owned;CHECK(coh_catalog_owner_bytes(owner,&owned)==COH_OK);
 CohRuntimeGraphBinding binding={0};binding.generation=1;binding.catalog_generation=generation;binding.pins.asset_generation=generation;memcpy(binding.pins.catalog_sha256,cb.catalog_sha256,32);memcpy(binding.pins.source_sha256,cb.source_sha256,32);memset(binding.pins.run_sha256,0x22,32);binding.pins.digest=udp_digest;CHECK(udp_digest(NULL,snapshot,binding.pins.snapshot_sha256)==COH_OK);
 CohRuntimeSnapshotBudget budget={COH_SG_TRANSACTION_MAX,262144+coh_catalog_owner_owned_bytes(owner)+coh_catalog_owner_owned_bytes(other)};CohRuntimeGraph *graph=NULL;CohRuntimeGraphReport graph_report;CHECK(coh_runtime_graph_build(NULL,owned,snapshot,&binding,&budget,NULL,&graph,&graph_report)==COH_OK);
 CHECK(coh_catalog_owner_retain(owner)==COH_OK);/* Explicit graph borrowed-catalog lease. */coh_catalog_owner_release(owner);
 for(unsigned scenario=0;scenario<3;scenario++){
  Peer p=peer_open();CohMapConfig config=configuration(p,5);CohMapClient *client=coh_map_client_create(&config);CHECK(client);uint64_t now=handshake(client,p,5,1,12345,81,100,1);
  Composition c={0};c.graph=graph;c.owner=scenario==1?other:owner;c.client=client;c.wire=wire;c.before=diagnostics(client);c.wanted=scenario==1?COH_STATE:COH_OK;memset(&c.report,0x51,sizeof(c.report));c.prior=c.report;
  CHECK(c.before.selected_slot==7&&c.before.selected_dbid==12345&&c.before.map_id==19&&c.before.map_link_id==23&&c.before.selection_generation==9);
  /* Late end mismatch must prevent every callback and compatibility commit. */
  size_t rawsize=wire.size+(scenario==2?1:0);unsigned char *raw=malloc(rawsize);CHECK(raw);memcpy(raw,wire.data,wire.size);if(scenario==2)raw[wire.size]=0;
  unsigned char encoded[COH_NET_MESSAGE_MAX];uLongf compressed_bytes=sizeof(encoded)-8;memcpy(encoded,raw,4);scene_fixture_u32(encoded+4,(uint32_t)rawsize-4);CHECK(compress2(encoded+8,&compressed_bytes,raw+4,(uLong)rawsize-4,Z_DEFAULT_COMPRESSION)==Z_OK);size_t encoded_bytes=(size_t)compressed_bytes+8;free(raw);
  unsigned count=(unsigned)((encoded_bytes+COH_NET_PAYLOAD_MAX-1)/COH_NET_PAYLOAD_MAX);CHECK(count>1&&count<=COH_NET_FRAGMENT_MAX);
  for(unsigned part=0;part<count;part++){send_part(p,local(client),encoded,encoded_bytes,part,count);CohStatus status=coh_map_client_service_observed(client,now++,(CohCancel){0},correlate,&c);if(part+1<count){CHECK(status==COH_OK&&c.calls==0);CHECK(!memcmp(&c.report,&c.prior,sizeof(c.report)));}else CHECK(status==COH_UNSUPPORTED);drain_idle(p,5);}
  CohMapDiagnostics after=diagnostics(client);CHECK(c.calls==(scenario==2?0u:1u));CHECK(after.phase==COH_MAP_SCENE_INCOMPLETE&&!after.character_identity_verified&&after.accepted_messages==2);CHECK(!after.udp.link.owned_retained_bytes&&after.udp.link.owned_high_water_bytes==rawsize);
  if(scenario==2)CHECK(!memcmp(&c.report,&c.prior,sizeof(c.report)));
  CHECK(coh_map_client_service_observed(client,now++,(CohCancel){0},correlate,&c)==COH_OK);CHECK(c.calls==(scenario==2?0u:1u));drain_idle(p,5);struct pollfd unread={p.fd,POLLIN,0};CHECK(poll(&unread,1,0)==0);
  coh_map_client_close(client);after=diagnostics(client);CHECK(after.udp.sockets_opened==after.udp.sockets_closed&&!after.udp.link.owned_retained_bytes&&!after.udp.link.tx_pending);coh_map_client_destroy(client);peer_close(p);scenarios++;
 }
 coh_runtime_graph_free(graph);coh_catalog_owner_release(owner);coh_catalog_owner_release(other);free((void*)catalog.data);free((void*)snapshot.data);free((void*)wire.data);CHECK(fd_count()==descriptors);
 printf("{\"passed\":true,\"checks\":%u,\"scenarios\":%u,\"actual_os_udp\":true,\"scripted_peer_only\":true,\"owned_network_loan_released\":true,\"world_authority\":false}\n",checks,scenarios);return 0;
}
