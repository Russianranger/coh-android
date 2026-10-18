/* New projection/lifecycle controls, with diagnostics and owner API doubles. */
#define COH_INITIAL_RECEIVE_NO_LEGACY
#include "capture_local_initial_receive.c"
#include <stdlib.h>
static unsigned checks,scenarios,begins,diagnostics,destroys;static int begin_fail;
static CohInitialCaptureDiagnostics fixture;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"receive control %u\n",(unsigned)__LINE__);exit(1);}}while(0)
CohStatus coh_initial_capture_begin(CohInitialCapture*o,const CohDbLogin*p,const char*a,uint32_t db,uint32_t map,uint64_t now){(void)o;(void)p;(void)a;(void)db;(void)map;(void)now;begins++;return begin_fail?COH_IO:COH_OK;}
void coh_initial_capture_diagnostics(const CohInitialCapture*o,CohInitialCaptureDiagnostics*out){(void)o;diagnostics++;*out=fixture;}
void coh_initial_capture_destroy(CohInitialCapture*o){(void)o;destroys++;}
static void reset(void){memset(&fixture,0,sizeof(fixture));memset(&receive_projection,0,sizeof(receive_projection));receive_owner=NULL;receive_bound=receive_retired=receive_cleanup=0;begin_fail=0;scenarios++;}
int main(void){
 char json[COH_RECEIVE_REPORT_MAX];CohReceiveProjection p={0};CohNetUdpDiagnostics u={0};CohInitialCaptureDiagnostics out;
 reset();CHECK(coh_receive_json(&p,0,0,json,sizeof(json))>0);CHECK(strstr(json,"\"valid\":false")&&strstr(json,"\"world_authority\":false"));
 reset();u.datagrams_received=45;u.malformed=20;u.link.received=25;u.link.rx_pending=16;u.link.fragment_groups=4;
 u.link.decode.failure_kind=COH_NET_DECODE_BUDGET;u.link.decode.compressed_bytes=16384;u.link.decode.declared_raw_bytes=UINT32_MAX;u.link.decode.output_budget=4u*1024u*1024u;
 coh_receive_sample(&p,&u);CHECK(p.sample_count==1&&!p.refusal&&p.udp_datagrams_received==45&&p.udp_malformed==20&&p.link_received==25);CHECK(p.max_rx_pending_sampled==16&&p.max_fragment_groups_sampled==4);
 u.link.rx_pending=u.link.fragment_groups=0;coh_receive_sample(&p,&u);CHECK(p.sample_count==2&&p.rx_pending==0&&p.max_rx_pending_sampled==16);CHECK(coh_receive_json(&p,1,1,json,sizeof(json))>0);CHECK(strstr(json,"\"observation_retired\":true"));char sample[COH_RECEIVE_REPORT_MAX];strcpy(sample,json);
 reset();memset(&p,0,sizeof(p));coh_receive_sample(&p,NULL);CHECK(p.refusal==1);coh_receive_sample(&p,&u);CHECK(!p.sample_count&&p.refusal==1);
 reset();memset(&p,0,sizeof(p));u.datagrams_received=1000000;coh_receive_sample(&p,&u);CHECK(!p.refusal);u.datagrams_received=1000001;coh_receive_sample(&p,&u);CHECK(p.refusal==2&&p.udp_datagrams_received==1000000);CHECK(coh_receive_json(&p,1,1,json,sizeof(json))>0&&strstr(json,"\"valid\":false"));
 reset();for(unsigned i=0;i<7;i++){memset(&p,0,sizeof(p));memset(&u,0,sizeof(u));switch(i){case 0:u.link.rx_pending=17;break;case 1:u.link.fragment_groups=5;break;case 2:u.link.decode.failure_kind=(CohNetDecodeFailure)5;break;case 3:u.link.decode.compressed_bytes=16385;break;case 4:u.link.decode.declared_raw_bytes=UINT64_C(0x100000000);break;case 5:u.link.decode.output_budget=4u*1024u*1024u+1;break;default:p.sample_count=1000000;break;}coh_receive_sample(&p,&u);CHECK(p.refusal!=0);}
 reset();int token;CohInitialCapture*owner=(CohInitialCapture*)&token;CHECK(receive_begin(owner,NULL,NULL,1,2,3)==COH_OK);fixture.local.map_protocol.udp.datagrams_received=45;fixture.local.map_protocol.udp.link.received=25;fixture.local.opened_sockets=fixture.local.closed_sockets=2;receive_diagnostics(owner,&out);CHECK(receive_projection.udp_datagrams_received==45&&receive_projection.link_received==25&&receive_cleanup);receive_destroy(owner);CHECK(receive_retired&&!receive_owner&&destroys==1);CHECK(coh_receive_json(&receive_projection,receive_retired,receive_cleanup,json,sizeof(json))>0&&strstr(json,"\"valid\":true"));
 reset();CHECK(receive_begin(owner,NULL,NULL,1,2,3)==COH_OK);int wrong;receive_diagnostics((CohInitialCapture*)&wrong,&out);CHECK(receive_projection.refusal==1);receive_destroy(owner);CHECK(receive_retired&&!receive_owner&&destroys==2);
 reset();begin_fail=1;CHECK(receive_begin(owner,NULL,NULL,1,2,3)==COH_IO&&!receive_bound&&!receive_owner);CHECK(begins==3&&diagnostics==2);CHECK(coh_receive_json(NULL,0,0,json,sizeof(json))<0&&coh_receive_json(&p,2,0,json,sizeof(json))<0);CHECK(coh_receive_json(&p,0,0,json,8)>=8);
 printf("{\"passed\":true,\"checks\":%u,\"scenarios\":%u,\"diagnostics_and_lifecycle_explicit_doubles\":true,\"actual_socket_or_server_executed\":false,\"sample\":%s}\n",checks,scenarios,sample);return 0;
}
