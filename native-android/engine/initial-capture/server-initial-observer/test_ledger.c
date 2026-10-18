#include "coh_server_initial_ledger.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(v) do{checks++;if(!(v)){fprintf(stderr,"CONTROL_FAILURE:%u\n",__LINE__);exit(2);}}while(0)
static int identity[5];
static CohSIOKey key(void){CohSIOKey k={&identity[0],&identity[1],&identity[2],&identity[3],11,12,13,14,15,16,17,5};return k;}
static void start(CohSIOLedger*s){CohSIOKey k=key();coh_sio_init(s);coh_sio_bind(s,&k,9);CHECK(s->report.groups_owner_bound&&s->report.valid);}
static void event(CohSIOLedger*s,CohSIOEvent e,const void*p,unsigned a,unsigned b,unsigned c){CohSIOKey k=key();coh_sio_record(s,&k,9,e,p,a,b,c);}
static void chain(CohSIOLedger*s){
 event(s,COH_SIO_DISPATCH,NULL,0,0,0);event(s,COH_SIO_REQUEST_STATE,NULL,1,0,0);
 event(s,COH_SIO_TICK,NULL,1,0,0);event(s,COH_SIO_BACKPRESSURE_ENTER,NULL,0,0,0);event(s,COH_SIO_BACKPRESSURE_PASS,NULL,0,0,0);
 event(s,COH_SIO_MAPXFER_ENTER,NULL,0,0,0);event(s,COH_SIO_MAPXFER_RETURN,NULL,0,0,0);event(s,COH_SIO_SELECTED,NULL,0,0,0);
 event(s,COH_SIO_FULL_ENTER,NULL,1,1,0);event(s,COH_SIO_ALLENTS_HEADER,&identity[4],0,0,0);
 event(s,COH_SIO_CHARACTER_ENTER,&identity[4],0,0,0);event(s,COH_SIO_CHARACTER_CORE_ENTER,&identity[4],0,0,0);event(s,COH_SIO_CHARACTER_CORE_RETURN,&identity[4],0,0,0);event(s,COH_SIO_CHARACTER_RETURN,&identity[4],0,0,0);event(s,COH_SIO_ATTACHED,&identity[4],0,0,0);
 event(s,COH_SIO_FINISH_ENTITY,&identity[4],0,0,0);CHECK(s->report.valid&&s->report.character_returned&&s->packet==(uintptr_t)&identity[4]);
}
static void retired(CohSIOLedger*s){CohSIOKey zero;memset(&zero,0,sizeof(zero));CHECK(!memcmp(&zero,&s->key,sizeof(zero))&&!s->packet&&!s->send_pending&&s->report.owner_retired);}
int main(void){CohSIOLedger s;CohSIOKey k,k2;CohSIOReport out;char raw[COH_SIO_MAX_JSON];unsigned i;int n;
 for(i=0;i<2;i++){start(&s);chain(&s);event(&s,COH_SIO_SEND_BEGIN,&identity[4],131073,7,0);CHECK(s.report.pkt_send_called);coh_sio_send_return(&s,9,(int)i);retired(&s);CHECK(s.report.stop==COH_SIO_FINAL_RETURN&&s.report.pkt_send_result==(int)i);coh_sio_refuse(&s,COH_SIO_OWNER);CHECK(s.report.valid);coh_sio_snapshot(&s,&out);n=coh_sio_json(&out,raw,sizeof(raw));CHECK(n>0&&n<4096);CHECK(!strstr(raw,"connection_id")&&!strstr(raw,"auth_id")&&!strstr(raw,"0x"));printf("SNAPSHOT %s",raw);}
 start(&s);event(&s,COH_SIO_TICK,NULL,0,1,0);event(&s,COH_SIO_BACKPRESSURE_BLOCK,NULL,0,0,0);CHECK(s.report.valid&&!s.report.dispatch_entered&&s.report.backpressure_blocked==1);n=coh_sio_json(&s.report,raw,sizeof(raw));CHECK(n>0);printf("SNAPSHOT %s",raw);
 for(i=0;i<12;i++){start(&s);k=key();switch(i){case 0:k.client=&identity[4];break;case 1:k.entity=&identity[4];break;case 2:k.character=&identity[4];break;case 3:k.uid++;break;case 4:k.connection_id++;break;case 5:k.connect_id++;break;case 6:k.entity_id++;break;case 7:k.dbid++;break;case 8:k.server_index++;break;case 9:k.auth_id++;break;case 10:k.protocol=4;break;default:k.client=NULL;break;}coh_sio_record(&s,&k,9,COH_SIO_DISPATCH,NULL,0,0,0);CHECK(s.report.refusal==COH_SIO_OWNER);retired(&s);coh_sio_refuse(&s,COH_SIO_SINK);CHECK(s.report.refusal==COH_SIO_OWNER);}
 start(&s);k=key();k.link=&identity[4];coh_sio_record(&s,&k,1,COH_SIO_DISPATCH,NULL,0,0,0);CHECK(s.report.valid&&!s.report.dispatch_entered);k=key();coh_sio_record(&s,&k,8,COH_SIO_DISPATCH,NULL,0,0,0);CHECK(s.report.refusal==COH_SIO_THREAD);retired(&s);
 start(&s);event(&s,COH_SIO_SELECTED,NULL,0,0,0);CHECK(s.report.refusal==COH_SIO_ORDER);retired(&s);
 start(&s);event(&s,COH_SIO_DISPATCH,NULL,0,0,0);event(&s,COH_SIO_REQUEST_STATE,NULL,1,0,0);event(&s,COH_SIO_SELECTED,NULL,0,0,0);event(&s,COH_SIO_FULL_ENTER,NULL,1,1,0);event(&s,COH_SIO_ALLENTS_HEADER,NULL,0,0,0);CHECK(s.report.refusal==COH_SIO_PACKET);retired(&s);
 start(&s);chain(&s);event(&s,COH_SIO_FINISH_ENTITY,&identity[0],0,0,0);CHECK(s.report.refusal==COH_SIO_PACKET);retired(&s);
 start(&s);chain(&s);event(&s,COH_SIO_SEND_BEGIN,&identity[4],7,8,0);CHECK(s.report.refusal==COH_SIO_VALUE);retired(&s);
 start(&s);chain(&s);event(&s,COH_SIO_SEND_BEGIN,&identity[4],7,0,0);coh_sio_send_return(&s,9,2);CHECK(s.report.refusal==COH_SIO_VALUE);retired(&s);
 start(&s);s.events=COH_SIO_MAX_EVENTS;event(&s,COH_SIO_TICK,NULL,1,0,0);CHECK(s.report.refusal==COH_SIO_LIMIT);retired(&s);
 start(&s);event(&s,COH_SIO_TICK,NULL,8,0,0);CHECK(s.report.refusal==COH_SIO_VALUE);retired(&s);
 start(&s);chain(&s);event(&s,COH_SIO_SEND_BEGIN,&identity[4],7,0,0);coh_sio_send_return(&s,8,0);CHECK(s.report.refusal==COH_SIO_THREAD);retired(&s);
 start(&s);k2=key();coh_sio_bind(&s,&k2,9);CHECK(s.report.refusal==COH_SIO_OWNER);retired(&s);
 coh_sio_init(&s);k=key();k.link=NULL;coh_sio_bind(&s,&k,9);CHECK(!s.report.valid&&!s.report.groups_owner_bound);CHECK(coh_sio_json(&s.report,raw,sizeof(raw))>0);printf("SNAPSHOT %s",raw);
 CHECK(coh_sio_json(&s.report,raw,4095)==0);printf("LEDGER_CONTROLS checks=%u\n",checks);return 0;
}
