/* New observer controls only. Original service/begin are explicit doubles;
 * link-wrapped sendto below is the actual POSIX loopback operation. */
#define COH_INITIAL_PROGRESS_NO_LEGACY 1
#include "../../combined-client/tools/capture_local_initial_progress.c"
#include <arpa/inet.h>
#include <stdlib.h>
static unsigned checks,begins,services,destroys,send_mode;
static CohStatus begin_result,service_result;
static CohInitialCaptureDiagnostics controlled;
static int source_fd=-1,target_fd=-1;
static struct sockaddr_in target;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"line %d: %s\n",__LINE__,#x);exit(1);}}while(0)
CohStatus coh_initial_capture_begin(CohInitialCapture*x,const CohDbLogin*p,const char*a,uint32_t db,uint32_t map,uint64_t now){(void)x;(void)p;(void)a;(void)db;(void)map;(void)now;begins++;return begin_result;}
void coh_initial_capture_diagnostics(const CohInitialCapture*x,CohInitialCaptureDiagnostics*out){(void)x;*out=controlled;}
CohStatus coh_initial_capture_service(CohInitialCapture*x,uint64_t now,CohCancel c,CohInitialCaptureObserver o,void*v,size_t bytes){
 (void)x;(void)now;(void)c;(void)o;(void)v;(void)bytes;services++;
 if(send_mode){char byte='X';errno=0;ssize_t n=sendto(send_mode==2?-1:source_fd,&byte,1,0,(struct sockaddr*)&target,sizeof(target));
  if(send_mode==2)CHECK(n==-1&&errno==EBADF);else CHECK(n==1);
 }
 controlled.groups_observed=1;controlled.groups_observations=1;controlled.reqallents_sent=1;controlled.groups_message_generation=5;controlled.map_generation=2;controlled.selection_generation=3;controlled.phase=COH_INITIAL_CAPTURE_WAIT_ALLENTS;controlled.local.db_phase=COH_DB_CLOSED;
 return service_result;
}
void coh_initial_capture_destroy(CohInitialCapture*x){(void)x;destroys++;}
static CohInitialCapture*owner(void){return(CohInitialCapture*)(uintptr_t)0x10000;}
static CohInitialCapture*other(void){return(CohInitialCapture*)(uintptr_t)0x20000;}
static void reset(void){memset(&progress,0,sizeof(progress));memset(&controlled,0,sizeof(controlled));begins=services=destroys=send_mode=0;begin_result=service_result=COH_OK;}
static void bind_owner(void){CHECK(progress_begin(owner(),NULL,NULL,1,2,100)==COH_OK&&begins==1&&progress.bound&&progress.owner==owner());}
static void queue(void){bind_owner();CHECK(progress_service(owner(),110,(CohCancel){0},NULL,NULL,0)==COH_OK);CHECK(progress.queued&&progress.queue_offset_ms==10&&!progress.post_queue_services&&!progress.post_queue_send_callbacks&&!progress.refusal);}
static void retire(void){progress_destroy(owner());CHECK(destroys==1&&progress.retired&&!progress.owner&&!progress.active);}
static void controls(void){
 reset();begin_result=COH_IO;CHECK(progress_begin(owner(),NULL,NULL,1,2,100)==COH_IO&&!progress.bound&&begins==1);
 reset();queue();retire();CHECK(!progress.post_queue_services&&!progress.post_queue_datagrams_emitted&&!progress.refusal);
 reset();queue();CHECK(progress_service(owner(),111,(CohCancel){0},NULL,NULL,0)==COH_OK);CHECK(progress.post_queue_services==1&&progress.last_post_queue_service_offset_ms==11&&!progress.post_queue_send_callbacks);retire();
 reset();bind_owner();send_mode=1;CHECK(progress_service(owner(),110,(CohCancel){0},NULL,NULL,0)==COH_OK);CHECK(progress.queued&&!progress.post_queue_send_callbacks);char b=0;CHECK(recv(target_fd,&b,1,0)==1&&b=='X');send_mode=0;retire();
 reset();queue();send_mode=1;CHECK(progress_service(owner(),111,(CohCancel){0},NULL,NULL,0)==COH_OK);CHECK(progress.post_queue_services==1&&progress.post_queue_send_callbacks==1&&progress.post_queue_datagrams_emitted==1&&!progress.post_queue_send_errors);char got=0;CHECK(recv(target_fd,&got,1,0)==1&&got=='X');retire();
 reset();queue();send_mode=2;service_result=COH_IO;CHECK(progress_service(owner(),111,(CohCancel){0},NULL,NULL,0)==COH_IO);CHECK(progress.post_queue_services==1&&progress.post_queue_send_callbacks==1&&!progress.post_queue_datagrams_emitted&&progress.post_queue_send_errors==1);retire();
 reset();queue();coh_initial_progress_service_begin(&progress,owner(),111,&controlled);CHECK(progress.active&&progress.counting);coh_initial_progress_send(&progress,1,0,1,0,0,0);coh_initial_progress_send(&progress,1,0,0,1,0,0);coh_initial_progress_send(&progress,1,0,0,0,1,0);CHECK(progress.post_queue_send_callbacks==3&&progress.post_queue_would_block==1&&progress.post_queue_interrupted==1&&progress.post_queue_partial_sends==1&&!progress.post_queue_datagrams_emitted);coh_initial_progress_service_end(&progress,owner(),111,&controlled);retire();
 for(unsigned field=0;field<6;field++){
  reset();queue();if(field==0)controlled.reqallents_sent=2;if(field==1)controlled.groups_message_generation++;if(field==2)controlled.map_generation++;if(field==3)controlled.selection_generation++;if(field==4)controlled.local.db_phase=COH_DB_CHARACTERS;if(field==5)controlled.phase=COH_INITIAL_CAPTURED;
  coh_initial_progress_service_begin(&progress,owner(),111,&controlled);CHECK(progress.refusal==COH_INITIAL_PROGRESS_STATE&&!progress.post_queue_services);coh_initial_progress_service_end(&progress,owner(),111,&controlled);retire();
 }
 reset();queue();coh_initial_progress_service_begin(&progress,other(),111,&controlled);CHECK(progress.refusal==COH_INITIAL_PROGRESS_OWNER&&!progress.active);coh_initial_progress_service_end(&progress,owner(),111,&controlled);retire();
 reset();queue();coh_initial_progress_service_begin(&progress,owner(),109,&controlled);CHECK(progress.refusal==COH_INITIAL_PROGRESS_CLOCK);coh_initial_progress_service_end(&progress,owner(),109,&controlled);retire();
 reset();queue();coh_initial_progress_service_begin(&progress,owner(),111,&controlled);coh_initial_progress_service_begin(&progress,owner(),111,&controlled);CHECK(progress.refusal==COH_INITIAL_PROGRESS_OWNER);coh_initial_progress_service_end(&progress,owner(),111,&controlled);retire();
 reset();queue();progress.post_queue_services=COH_INITIAL_PROGRESS_EVENT_MAX;coh_initial_progress_service_begin(&progress,owner(),111,&controlled);CHECK(progress.refusal==COH_INITIAL_PROGRESS_LIMIT);coh_initial_progress_service_end(&progress,owner(),111,&controlled);retire();
 reset();queue();coh_initial_progress_service_begin(&progress,owner(),111,&controlled);progress.post_queue_send_callbacks=COH_INITIAL_PROGRESS_EVENT_MAX;coh_initial_progress_send(&progress,1,1,0,0,0,0);CHECK(progress.refusal==COH_INITIAL_PROGRESS_LIMIT&&!progress.post_queue_datagrams_emitted);coh_initial_progress_service_end(&progress,owner(),111,&controlled);retire();
 for(unsigned bad=0;bad<4;bad++){
  reset();queue();coh_initial_progress_service_begin(&progress,owner(),111,&controlled);if(bad==0)coh_initial_progress_send(&progress,0,1,0,0,0,0);if(bad==1)coh_initial_progress_send(&progress,COH_PROTOCOL_FRAME_MAX+1u,1,0,0,0,0);if(bad==2)coh_initial_progress_send(&progress,1,1,1,0,0,0);if(bad==3)coh_initial_progress_send(&progress,1,-1,2,0,0,0);CHECK(progress.refusal==COH_INITIAL_PROGRESS_CALLBACK&&!progress.post_queue_datagrams_emitted);coh_initial_progress_service_end(&progress,owner(),111,&controlled);retire();
 }
 reset();queue();retire();coh_initial_progress_bind(&progress,owner(),120);CHECK(progress.refusal==COH_INITIAL_PROGRESS_OWNER);
 /* Opaque pointer retirement prevents an address-reused caller from silently
  * inheriting a previous one-shot witness. No old key is serialized. */
 reset();queue();retire();char json[COH_INITIAL_PROGRESS_REPORT_MAX];int n=progress_json(json,sizeof(json));CHECK(n>0&&(size_t)n<sizeof(json)&&strstr(json,"\"valid\":true")&&strstr(json,"\"command_specific_emission_proved\":false")&&strstr(json,"\"server_receipt_proved\":false"));CHECK(!strstr(json,"10000")&&!strstr(json,"20000"));
}
int main(void){
 source_fd=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);target_fd=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);CHECK(source_fd>=0&&target_fd>=0);memset(&target,0,sizeof(target));target.sin_family=AF_INET;target.sin_addr.s_addr=htonl(0x7f000001u);CHECK(!bind(target_fd,(struct sockaddr*)&target,sizeof(target)));socklen_t size=sizeof(target);CHECK(!getsockname(target_fd,(struct sockaddr*)&target,&size)&&size==sizeof(target));controls();CHECK(!close(source_fd)&&!close(target_fd));printf("{\"passed\":true,\"checks\":%u,\"observer_bytes\":%zu,\"actual_loopback_datagrams\":2,\"actual_send_error_errno_preserved\":true,\"service_protocol_doubled\":true,\"original_server_executed\":false,\"command_specific_emission_proved\":false,\"world_authority\":false}\n",checks,sizeof(CohInitialProgress));return 0;
}
