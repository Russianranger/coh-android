/* NONSHIPPING replacement TU; ordinary source bytes remain unchanged. */
#include "../mapclient/coh_mapclient.c"
#include "coh_initial_capture_private.h"
struct CohInitialMap {
 CohMapClient *map;CohDbHandoffMetadata bound;
 CohInitialCaptureDiagnostics d;
 CohInitialMapFailurePhase first_failure_phase;
 unsigned command_valid,command_refusal_latched;
 CohInitialCaptureCommandKind command_kind;
 const CohInitialCaptureEvent *event;const CohMapSceneObservation *scene;
 const CohNetOwnedMessage *message;CohRepReader reader;CohRepUpdatePrefix update;
 const void *owner;size_t owner_bytes;const void *context;size_t context_bytes;
 CohInitialMapObserver observer;void *observer_context;
 CohStatus observer_status;unsigned busy;
 uint32_t connection_id,version;uint64_t request_ms;
};
static int ic_span(const void *p,size_t n){return p&&n&&n<=UINTPTR_MAX-(uintptr_t)p;}
static int ic_disjoint(const void *a,size_t an,const void *b,size_t bn){return scene_disjoint(a,an,b,bn);}
const char *coh_initial_capture_command_name(CohInitialCaptureCommandKind kind){
 switch(kind){case COH_INITIAL_CAPTURE_COMMAND_NONE:return "NONE";
#define COH_INITIAL_CAPTURE_COMMAND(name,id) case COH_INITIAL_CAPTURE_COMMAND_##name:return #name;
#include "coh_initial_command_kinds.inc"
#undef COH_INITIAL_CAPTURE_COMMAND
 default:return "UNKNOWN";}
}
static CohInitialCaptureCommandKind ic_command_kind(uint32_t normalized){
 switch(normalized){
#define COH_INITIAL_CAPTURE_COMMAND(name,id) case id:return COH_INITIAL_CAPTURE_COMMAND_##name;
#include "coh_initial_command_kinds.inc"
#undef COH_INITIAL_CAPTURE_COMMAND
 default:return COH_INITIAL_CAPTURE_COMMAND_UNKNOWN;}
}
static void ic_command_clear(CohInitialMap*x){x->command_valid=0;x->command_kind=COH_INITIAL_CAPTURE_COMMAND_NONE;}
static void ic_command_decoded(CohInitialMap*x,uint32_t normalized){x->command_kind=ic_command_kind(normalized);x->command_valid=1;}
static int ic_meta_equal(const CohDbHandoffMetadata*a,const CohDbHandoffMetadata*b){
 return a->user_id==b->user_id&&a->selected_dbid==b->selected_dbid&&a->selected_slot==b->selected_slot&&a->selection_generation==b->selection_generation&&a->session_generation==b->session_generation&&a->receipt_generation==b->receipt_generation&&a->connect_id==b->connect_id&&a->db_peer.port==b->db_peer.port&&!memcmp(a->db_peer.address,b->db_peer.address,4)&&a->local_development_auth==b->local_development_auth&&a->selected_dbid_owner_bound==b->selected_dbid_owner_bound&&a->claimed==b->claimed&&a->retired==b->retired;
}
static CohStatus ic_owner(const CohInitialMap*x){
 CohMapClient*m=x->map;CohDbHandoffMetadata meta;
 if(!m||!m->authorized||!m->udp||m->config.udp.peer.address[0]!=127||m->config.udp.local.address[0]!=127||m->last_connect_id!=x->connection_id||m->config.udp.link.version!=x->version||m->diag.generation!=x->d.map_generation||m->diag.map_id!=x->d.map_id||m->diag.map_link_id!=x->d.map_link_id||m->diag.selection_generation!=x->d.selection_generation||m->diag.selected_slot!=x->d.selected_slot||m->diag.selected_dbid!=x->d.selected_dbid||!m->diag.local_development_authorized||!m->diag.selected_dbid_owner_bound||m->diag.character_identity_verified)return COH_STATE;
 CohStatus s=owned_metadata(m,&meta);if(s!=COH_OK)return s;
 if(!meta.claimed||meta.retired||!meta.local_development_auth||!meta.selected_dbid_owner_bound||!meta.selected_dbid||meta.db_peer.address[0]!=127||!ic_meta_equal(&meta,&x->bound))return COH_STATE;
 return COH_OK;
}
CohInitialMap *coh_initial_map_create(CohMapClient*m){
 if(!m||m->active_scene||m->diag.phase!=COH_MAP_NET_CONNECTING||m->diag.scene_structures||!m->last_connect_id)return NULL;
 CohInitialMap*x=calloc(1,sizeof(*x));if(!x)return NULL;x->map=m;
 if(owned_metadata(m,&x->bound)!=COH_OK){free(x);return NULL;}
 x->connection_id=m->last_connect_id;x->version=m->config.udp.link.version;
 x->d.phase=COH_INITIAL_CAPTURE_WAIT_GROUPS;x->d.map_generation=m->diag.generation;
 x->d.selection_generation=m->diag.selection_generation;x->d.selected_slot=m->diag.selected_slot;x->d.selected_dbid=m->diag.selected_dbid;x->d.map_id=m->diag.map_id;x->d.map_link_id=m->diag.map_link_id;x->d.db_session_generation=m->diag.db_session_generation;x->d.db_receipt_generation=m->diag.db_receipt_generation;
 if(ic_owner(x)!=COH_OK){wipe(x,sizeof(*x));free(x);return NULL;}return x;
}
void coh_initial_map_destroy(CohInitialMap*x){if(x&&!x->busy){wipe(x,sizeof(*x));free(x);}}
static CohStatus ic_fail(CohInitialMap*x,CohStatus s,CohInitialCaptureFailure why){
 if(!x->command_refusal_latched){x->d.refused_command_valid=x->command_valid;x->d.refused_command_kind=x->command_kind;x->command_refusal_latched=1;}
 if(!x->first_failure_phase.valid)x->first_failure_phase=(CohInitialMapFailurePhase){1,x->map->diag.phase};
 x->d.status=s;x->d.failure=why;x->d.phase=s==COH_CANCELLED?COH_INITIAL_CAPTURE_CANCELLED:COH_INITIAL_CAPTURE_FAILED;
 x->map->diag.last_status=s;coh_map_client_close(x->map);return s;
}
static int ic_cancel(CohCancel c){return c.poll&&c.poll(c.context);}
static CohStatus ic_observe(CohInitialMap*x,CohInitialCaptureKind kind){
 CohMapClient*m=x->map;const CohNetOwnedMessage*n=x->message;
 if(!n||!ic_span(n->payload,n->payload_bytes)||!ic_disjoint(x->context,x->context_bytes,n->payload,n->payload_bytes)||!ic_disjoint(x->owner,x->owner_bytes,n->payload,n->payload_bytes)||!ic_disjoint(x->context,x->context_bytes,n,sizeof(*n))||!ic_disjoint(x->owner,x->owner_bytes,n,sizeof(*n)))return COH_INVALID;
 const CohInitialCaptureEvent event={kind};
 if(!ic_disjoint(x->context,x->context_bytes,&event,sizeof(event))||!ic_disjoint(x->owner,x->owner_bytes,&event,sizeof(event)))return COH_INVALID;
 x->event=&event;CohStatus s=x->observer(x->observer_context,&event);x->event=NULL;
 if(m->active_scene&&kind!=COH_INITIAL_CAPTURE_GROUPS)return COH_STATE;
 return s;
}
static void ic_groups(void*opaque,const CohMapSceneObservation*event){
 CohInitialMap*x=opaque;CohMapSceneLease loan;CohMapClient*m=x->map;
 x->observer_status=ic_owner(x);if(x->observer_status==COH_OK)x->observer_status=coh_map_client_scene_lease(m,event,&loan);
 if(x->observer_status!=COH_OK)return;
 if(x->d.groups_observed||x->d.reqallents_sent||m->diag.scene_structures!=1||m->diag.scene_failure.status||m->diag.scene_inspection.consumed_bits!=loan.inspection.consumed_bits||!loan.message_generation||!loan.selected_dbid_owner_bound||!loan.local_development_authorized||loan.source_generation_admitted||loan.world_authority||loan.map_generation!=x->d.map_generation||loan.selection_generation!=x->d.selection_generation||loan.selected_dbid!=x->d.selected_dbid||loan.selected_slot!=x->d.selected_slot||loan.db_session_generation!=x->d.db_session_generation||loan.db_receipt_generation!=x->d.db_receipt_generation){x->observer_status=COH_STATE;return;}
 x->scene=event;x->reader=loan.reader;x->d.groups_message_generation=loan.message_generation;x->d.groups_message_id=loan.message_id;x->d.groups=loan.inspection;
 x->observer_status=ic_observe(x,COH_INITIAL_CAPTURE_GROUPS);x->scene=NULL;memset(&x->reader,0,sizeof(x->reader));
 if(x->observer_status==COH_OK){x->d.groups_observed=1;x->d.groups_observations=1;}
}
static void ic_message_diag(CohInitialMap*x,const CohNetOwnedMessage*n){
 x->d.last_payload_bits=n->payload_bits;x->d.last_decoded_bytes=(uint32_t)n->payload_bytes;x->d.last_byte_aligned=n->compressed;
}
CohStatus coh_initial_map_lease(const CohInitialMap*x,const CohInitialCaptureEvent*event,CohInitialCaptureLease*out){
 if(!x||!event||!out)return COH_INVALID;
 if(!x->busy||event!=x->event||!x->message||!x->owner)return COH_STATE;
 CohMapClient*m=x->map;const CohNetOwnedMessage*n=x->message;
 if(!ic_span(out,sizeof(*out))||!ic_disjoint(out,sizeof(*out),x,sizeof(*x))||!ic_disjoint(out,sizeof(*out),m,sizeof(*m))||!ic_disjoint(out,sizeof(*out),x->owner,x->owner_bytes)||!ic_disjoint(out,sizeof(*out),event,sizeof(*event))||!ic_disjoint(out,sizeof(*out),n,sizeof(*n))||!ic_disjoint(out,sizeof(*out),n->payload,n->payload_bytes))return COH_INVALID;
 CohRepReader reader=x->reader;
 if(event->kind==COH_INITIAL_CAPTURE_GROUPS){CohMapSceneLease scene;CohStatus s=coh_map_client_scene_lease(m,x->scene,&scene);if(s!=COH_OK)return s;if(scene.message_generation!=n->generation)return COH_STATE;reader=scene.reader;}
 else if(event->kind==COH_INITIAL_CAPTURE_ALLENTS){if(ic_owner(x)!=COH_OK||x->d.reqallents_sent!=1||!x->d.groups_observed||n->generation<=x->d.groups_message_generation)return COH_STATE;}
 else return COH_STATE;
 if(!n->generation||reader.bytes.data!=n->payload||reader.bytes.size!=n->payload_bytes||reader.bits!=n->payload_bits||reader.compressed!=n->compressed||reader.cursor>reader.bits||reader.max_bytes!=COH_NET_DECODED_MAX)return COH_STATE;
 CohInitialCaptureLease v;memset(&v,0,sizeof(v));v.kind=event->kind;v.reader=reader;v.schema=m->schema;v.groups=x->d.groups;v.update=x->update;v.message_generation=n->generation;v.groups_message_generation=x->d.groups_message_generation;v.message_id=n->id;v.ordered_id=n->ordered_id;v.ordered=n->ordered;v.connection_id=x->connection_id;v.transport_version=x->version;v.map_generation=x->d.map_generation;v.selection_generation=x->d.selection_generation;v.selected_slot=x->d.selected_slot;v.selected_dbid=x->d.selected_dbid;v.map_id=x->d.map_id;v.map_link_id=x->d.map_link_id;v.db_session_generation=x->d.db_session_generation;v.db_receipt_generation=x->d.db_receipt_generation;v.local_development_authorized=1;v.selected_dbid_owner_bound=1;*out=v;return COH_OK;
}
static CohStatus ic_initial(CohInitialMap*x,const CohNetOwnedMessage*n){
 CohMapClient*m=x->map;CohRepReader reader;uint32_t command;
 ic_command_clear(x);
 m->diag.stage=COH_MAP_STAGE_COMMAND;m->diag.last_command_valid=0;m->diag.last_payload_bits=n->payload_bits;m->diag.last_decoded_bytes=(uint32_t)n->payload_bytes;m->diag.last_byte_aligned=n->compressed;
 CohStatus s=coh_rep_reader_bounded(&reader,(CohBytes){n->payload,n->payload_bytes},n->payload_bits,n->compressed,COH_NET_DECODED_MAX);if(s==COH_OK)s=coh_rep_pack(&reader,1,&command);
 if(s==COH_OK&&x->version<4){if(command<7)s=COH_UNSUPPORTED;else command-=5;}
 if(s!=COH_OK){x->d.failure=COH_INITIAL_CAPTURE_FAILURE_COMMAND;return s;}
 ic_command_decoded(x,command);
 x->d.last_command=command;m->diag.last_command=command;m->diag.last_command_valid=1;
 if(command!=COH_REP_ALLENTS){x->d.failure=COH_INITIAL_CAPTURE_FAILURE_COMMAND;return COH_UNSUPPORTED;}
 if(ic_owner(x)!=COH_OK||m->diag.phase!=COH_MAP_SCENE_INCOMPLETE||m->inspector.phase!=COH_REP_SCENE_PREFIX_SEEN||m->inspector.schema_generation!=m->inspector.generation||n->generation<=x->d.groups_message_generation){x->d.failure=COH_INITIAL_CAPTURE_FAILURE_OWNER;return COH_STATE;}
 x->reader=reader;m->diag.stage=COH_MAP_STAGE_ENTITY_PREFIX;
 CohRepUpdatePrefix prefix;s=coh_rep_update_prefix(&reader,&m->schema,command,&prefix);
 if(s!=COH_OK||!prefix.odd_send||reader.cursor>=reader.bits){x->d.failure=COH_INITIAL_CAPTURE_FAILURE_HEADER;return s==COH_OK?COH_INVALID:s;}
 x->update=prefix;s=ic_observe(x,COH_INITIAL_CAPTURE_ALLENTS);if(s!=COH_OK)x->d.failure=COH_INITIAL_CAPTURE_FAILURE_OBSERVER;
 memset(&x->reader,0,sizeof(x->reader));memset(&x->update,0,sizeof(x->update));return s;
}
CohStatus coh_initial_map_service(CohInitialMap*x,uint64_t now,CohCancel cancel,
 CohInitialMapObserver observer,void*observer_context,const void*owner,size_t owner_bytes,
 const void*context,size_t context_bytes){
 if(!x||!observer||!ic_span(owner,owner_bytes)||!ic_span(context,context_bytes))return COH_INVALID;
 if(x->busy||x->d.phase==COH_INITIAL_CAPTURED||x->d.phase==COH_INITIAL_CAPTURE_FAILED||x->d.phase==COH_INITIAL_CAPTURE_CANCELLED)return COH_STATE;
 CohMapClient*m=x->map;
 if(!ic_disjoint(context,context_bytes,x,sizeof(*x))||!ic_disjoint(context,context_bytes,m,sizeof(*m))||!ic_disjoint(context,context_bytes,owner,owner_bytes)||!ic_disjoint(owner,owner_bytes,x,sizeof(*x))||!ic_disjoint(owner,owner_bytes,m,sizeof(*m)))return COH_INVALID;
 if(now<m->last_ms)return COH_INVALID;
 x->busy=1;x->owner=owner;x->owner_bytes=owner_bytes;x->context=context;x->context_bytes=context_bytes;x->observer=observer;x->observer_context=observer_context;
 ic_command_clear(x);
 CohStatus result=COH_OK;CohInitialCaptureFailure why=COH_INITIAL_CAPTURE_FAILURE_PROTOCOL;
 if(ic_cancel(cancel)){result=COH_CANCELLED;why=COH_INITIAL_CAPTURE_FAILURE_CANCELLED;goto done;}
 if(ic_owner(x)!=COH_OK){result=COH_STATE;why=COH_INITIAL_CAPTURE_FAILURE_OWNER;goto done;}
 m->last_ms=now;result=coh_net_udp_service(m->udp,now,cancel);CohNetUdpDiagnostics udp;coh_net_udp_diagnostics(m->udp,&udp);
 if(result!=COH_OK||udp.state!=COH_UDP_ACTIVE){if(result==COH_OK)result=COH_STATE;if(result==COH_CANCELLED)why=COH_INITIAL_CAPTURE_FAILURE_CANCELLED;else if(udp.state==COH_UDP_TIMED_OUT)why=COH_INITIAL_CAPTURE_FAILURE_TIMEOUT;goto done;}
 if(m->diag.phase==COH_MAP_NET_CONNECTING&&udp.link_state==COH_NET_CONNECTED){m->diag.stage=COH_MAP_STAGE_SEND_COMMAND;result=send_command(m,COH_MAP_CONNECT,now);m->cookie=0;if(result!=COH_OK)goto done;m->diag.phase=COH_MAP_WAIT_CONNECT;m->phase_ms=now;}
 for(unsigned i=0;i<m->config.message_budget;i++){
  ic_command_clear(x);
  CohNetOwnedMessage n;result=coh_net_udp_next_owned(m->udp,&n);if(result==COH_NOT_FOUND){result=COH_OK;break;}if(result!=COH_OK)goto done;
  x->message=&n;ic_message_diag(x,&n);x->observer_status=COH_OK;
  if(ic_cancel(cancel)){result=COH_CANCELLED;why=COH_INITIAL_CAPTURE_FAILURE_CANCELLED;}
  else if(x->d.reqallents_sent){result=ic_initial(x,&n);why=x->d.failure;}
  else {result=inspect(m,&n,now,ic_groups,x);x->d.last_command=m->diag.last_command;if(m->diag.last_command_valid)ic_command_decoded(x,m->diag.last_command);
   if(result==COH_UNSUPPORTED&&x->d.groups_observed&&x->observer_status==COH_OK){result=COH_OK;}
   else if(x->observer_status!=COH_OK){result=x->observer_status;why=COH_INITIAL_CAPTURE_FAILURE_OBSERVER;}
   else if(result!=COH_OK)why=m->diag.stage==COH_MAP_STAGE_SCENE_STRUCTURE?COH_INITIAL_CAPTURE_FAILURE_GROUPS:COH_INITIAL_CAPTURE_FAILURE_PROTOCOL;
  }
  uint64_t observed_generation=n.generation;x->message=NULL;CohStatus released=coh_net_udp_owned_release(m->udp,&n);
  if(result==COH_OK&&released!=COH_OK){result=released;why=COH_INITIAL_CAPTURE_FAILURE_RELEASE;}
  if(result!=COH_OK)goto done;
  if(ic_cancel(cancel)){result=COH_CANCELLED;why=COH_INITIAL_CAPTURE_FAILURE_CANCELLED;goto done;}
  if(x->d.reqallents_sent){x->d.raw_allents_observed=1;x->d.allents_observations=1;x->d.allents_message_generation=observed_generation;x->d.phase=COH_INITIAL_CAPTURED;x->d.status=COH_UNSUPPORTED;m->diag.last_status=COH_UNSUPPORTED;coh_map_client_close(m);result=COH_UNSUPPORTED;why=COH_INITIAL_CAPTURE_FAILURE_NONE;goto done;}
  if(x->d.groups_observed){
   if(ic_owner(x)!=COH_OK||m->diag.scene_structures!=1){result=COH_STATE;why=COH_INITIAL_CAPTURE_FAILURE_OWNER;goto done;}
   result=send_command(m,COH_MAP_REQALLENTS,now);if(result!=COH_OK){why=COH_INITIAL_CAPTURE_FAILURE_REQUEST;goto done;}
   x->d.reqallents_sent=1;x->d.phase=COH_INITIAL_CAPTURE_WAIT_ALLENTS;x->request_ms=now;break;
  }
 }
 if(now-(x->d.reqallents_sent?x->request_ms:m->phase_ms)>=m->config.application_timeout_ms){result=COH_STATE;why=COH_INITIAL_CAPTURE_FAILURE_TIMEOUT;}
 done:
 x->event=NULL;x->scene=NULL;x->message=NULL;memset(&x->reader,0,sizeof(x->reader));x->owner=NULL;x->owner_bytes=0;x->context=NULL;x->context_bytes=0;x->observer=NULL;x->observer_context=NULL;
 if(result!=COH_OK&&x->d.phase!=COH_INITIAL_CAPTURED)ic_fail(x,result,why);
 x->busy=0;return result;
}
int coh_initial_map_output_disjoint(const CohInitialMap*x,const void*out,size_t bytes){
 if(!x||!ic_span(out,bytes)||!ic_disjoint(out,bytes,x,sizeof(*x))||!ic_disjoint(out,bytes,x->map,sizeof(*x->map)))return 0;
 if(x->owner&&!ic_disjoint(out,bytes,x->owner,x->owner_bytes))return 0;
 if(x->event&&!ic_disjoint(out,bytes,x->event,sizeof(*x->event)))return 0;
 if(x->message&&(!ic_disjoint(out,bytes,x->message,sizeof(*x->message))||!ic_disjoint(out,bytes,x->message->payload,x->message->payload_bytes)))return 0;
 return 1;
}
void coh_initial_map_diagnostics(const CohInitialMap*x,CohInitialCaptureDiagnostics*out){if(x&&out&&coh_initial_map_output_disjoint(x,out,sizeof(*out)))*out=x->d;}
CohInitialMapFailurePhase coh_initial_map_failure_phase(const CohInitialMap*x){return x?x->first_failure_phase:(CohInitialMapFailurePhase){0};}
