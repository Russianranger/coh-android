/* NONSHIPPING ONLY. Included in BodyPart.c before bpReadBodyPartFiles.
 * A frozen source owner is borrowed. No engine allocation, dictionary generation,
 * selected-session proof, catalog admission or actor/ACK authority is produced. */
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdlib.h>
#define COH_BODY_WITNESS_CAP 65536u
#define COH_BODY_WITNESS_ROWS 29u
#define COH_BODY_WITNESS_STACK_RESERVE 4096u
#include "coh_body_witness_configuration.inc"
typedef struct CohBodyWitnessState {
 unsigned char bytes[COH_BODY_WITNESS_CAP];
 const void *root,*rows;
 size_t used;
 unsigned active,ready,error,acquire,binary,text,completed,located;
 int count;
 char path[260];
} CohBodyWitnessState;
static CohBodyWitnessState coh_body_witness;
static unsigned coh_body_witness_last_status;
static void coh_body_witness_wipe(void*p,size_t n){volatile unsigned char*q=(volatile unsigned char*)p;while(n--)*q++=0;}
static int coh_body_witness_span(const void*p,size_t n,uintptr_t*end){uintptr_t a=(uintptr_t)p;if(!p||!n||n>UINTPTR_MAX-a)return 0;*end=a+n;return 1;}
static int coh_body_witness_overlap(const void*a,size_t n,const void*b,size_t m){uintptr_t e,f;if(!coh_body_witness_span(a,n,&e)||!coh_body_witness_span(b,m,&f))return 1;return(uintptr_t)a<f&&(uintptr_t)b<e;}
static int coh_body_witness_length(const char*p,size_t*n){size_t i;uintptr_t end;if(p&&!coh_body_witness_span(p,260,&end))return 0;if(!p){*n=0;return 1;}for(i=0;i<=259;i++)if(!p[i]){*n=i;return 1;}return 0;}
static int coh_body_witness_source_span(const void*p,size_t n){return !coh_body_witness_overlap(p,n,&coh_body_witness,sizeof(coh_body_witness));}
/* Small writer can either write a new candidate or compare frozen live rows
 * directly with the retained post-load bytes. It never copies a second catalog. */
typedef struct CohBodyWitnessWriter{size_t at,cap;unsigned compare,error;}CohBodyWitnessWriter;
static void coh_body_witness_put(CohBodyWitnessWriter*w,const void*p,size_t n){
 if(w->error)return;
 if(w->at>w->cap||n>w->cap-w->at){w->error=2;return;}
 if(w->compare){if(n&&memcmp(coh_body_witness.bytes+w->at,p,n)){w->error=3;return;}}
 else if(n)memcpy(coh_body_witness.bytes+w->at,p,n);
 w->at+=n;
}
static void coh_body_witness_word(CohBodyWitnessWriter*w,uint32_t v){unsigned char b[4];unsigned i;for(i=0;i<4;i++)b[i]=(unsigned char)(v>>(8*i));coh_body_witness_put(w,b,4);}
static void coh_body_witness_string(CohBodyWitnessWriter*w,const char*p){size_t n=0;unsigned char b[2];if(!coh_body_witness_length(p,&n)){w->error=1;return;}b[0]=p?(unsigned char)n:255;b[1]=p?(unsigned char)(n>>8):255;coh_body_witness_put(w,b,2);if(p)coh_body_witness_put(w,p,n);}
static unsigned coh_body_witness_serialize(unsigned compare,size_t capacity,size_t*written){
 CohBodyWitnessWriter w;int count=GetBodyPartCount(),i;const BodyPart**rows=bodyPartList.bodyParts;size_t j,n,need=8+8*4+4*32+2;
 if(!written||!coh_body_witness_source_span(written,sizeof(*written))||capacity>COH_BODY_WITNESS_CAP||!capacity||count<1||count>(int)COH_BODY_WITNESS_ROWS||!rows)return 1;
 if(!coh_body_witness_source_span(rows,(size_t)count*sizeof(*rows)))return 1;
 /* All known source extents and complete conservative output size preflight
  * before copying. Null and present-empty strings have distinct wire values. */
 for(i=0;i<count;i++){
  const BodyPart*p=rows[i];const char*s[5];
  if(!p||!coh_body_witness_source_span(p,sizeof(*p)))return 1;
  s[0]=p->name;s[1]=p->name_geo;s[2]=p->name_tex;s[3]=p->base_var;s[4]=p->sourceFile;
  need+=6*4+5*2;
  for(j=0;j<5;j++)if(s[j]){if(!coh_body_witness_length(s[j],&n)||!coh_body_witness_source_span(s[j],n+1))return 1;need+=n;}
 }
 if(!coh_body_witness_length(coh_body_witness.path,&n))return 1;
 need+=n;if(need>capacity)return 2;
 w.at=0;w.cap=capacity;w.compare=compare;w.error=0;
 coh_body_witness_put(&w,"COHBW1\0\0",8);coh_body_witness_word(&w,1);
 coh_body_witness_word(&w,coh_body_witness.acquire);coh_body_witness_word(&w,coh_body_witness.binary);
 coh_body_witness_word(&w,coh_body_witness.text);coh_body_witness_word(&w,coh_body_witness.completed);
 coh_body_witness_word(&w,(uint32_t)count);
 /* No current-Map/session/generation or authority permit. These are wire zeros. */
 coh_body_witness_word(&w,0);coh_body_witness_word(&w,0);
 coh_body_witness_put(&w,coh_body_witness_source,32);coh_body_witness_put(&w,coh_body_witness_build,32);
 coh_body_witness_put(&w,coh_body_witness_profile,32);coh_body_witness_put(&w,coh_body_witness_run,32);
 coh_body_witness_string(&w,coh_body_witness.path);
 for(i=0;i<count;i++){
  const BodyPart*p=rows[i];
  coh_body_witness_word(&w,(uint32_t)p->bone_num[0]);coh_body_witness_word(&w,(uint32_t)p->bone_num[1]);
  coh_body_witness_word(&w,(uint32_t)p->bodyPartIndex);coh_body_witness_word(&w,(uint32_t)p->num_parts);
  coh_body_witness_word(&w,(uint32_t)p->influenceCost);coh_body_witness_word(&w,(uint32_t)p->dont_clear);
  coh_body_witness_string(&w,p->name);coh_body_witness_string(&w,p->name_geo);coh_body_witness_string(&w,p->name_tex);
  coh_body_witness_string(&w,p->base_var);coh_body_witness_string(&w,p->sourceFile);
 }
 if(w.error)return w.error;
 if(count!=GetBodyPartCount()||rows!=bodyPartList.bodyParts)return 3;
 *written=w.at;return 0;
}
static void coh_body_witness_begin(const void*root){
 const char*enabled=getenv("COH_NATIVE_BODY_WITNESS_OUTPUT");
 if(!enabled)return;
 if(coh_body_witness.active||coh_body_witness.ready){coh_body_witness_wipe(&coh_body_witness,sizeof(coh_body_witness));coh_body_witness.error=4;return;}
 coh_body_witness_wipe(&coh_body_witness,sizeof(coh_body_witness));coh_body_witness.root=root;coh_body_witness.active=1;
}
/* Only calls for this exact source-owned root during its synchronous load are
 * observed. Normalized acquisition:1=DataAcquired,2=Error,3=FirstCaller,4=other.
 * event1 acquisition,event2 binary result+1,event3 text,event4 shared return+1. */
void coh_source_body_witness_route(const void*root,unsigned event,unsigned value){
 if(!coh_body_witness.active||root!=coh_body_witness.root)return;
 if(event==1){if(coh_body_witness.acquire||value<1||value>3)coh_body_witness.error=4;else coh_body_witness.acquire=value;}
 else if(event==2){if(coh_body_witness.binary||coh_body_witness.text||value<1||value>2)coh_body_witness.error=4;else coh_body_witness.binary=value;}
 else if(event==3){if(coh_body_witness.text||coh_body_witness.binary==2)coh_body_witness.error=4;else coh_body_witness.text=1;}
 else if(event==4){if(coh_body_witness.completed||value<1||value>2)coh_body_witness.error=4;else coh_body_witness.completed=value;}
 else coh_body_witness.error=4;
}
int coh_source_body_witness_binary(const void*root,int result){coh_source_body_witness_route(root,2,result?2u:1u);return result;}
void coh_source_body_witness_located(const void*root,const char*path){
 size_t n;if(!coh_body_witness.active||root!=coh_body_witness.root)return;
 if(coh_body_witness.located||!path||!coh_body_witness_length(path,&n)||!coh_body_witness_source_span(path,n+1)){coh_body_witness.error=4;return;}
 memcpy(coh_body_witness.path,path,n+1);coh_body_witness.located=1;
}
static void coh_body_witness_end(void){
 unsigned rc;size_t written=0;
 if(!coh_body_witness.active)return;
 coh_body_witness.active=0;
 if(coh_body_witness.error||coh_body_witness.completed!=2||!coh_body_witness.acquire||
  (coh_body_witness.acquire==1&&(coh_body_witness.binary||coh_body_witness.text||coh_body_witness.located))||
  (coh_body_witness.acquire!=1&&!coh_body_witness.text&&coh_body_witness.binary!=2)||
  (coh_body_witness.binary==2&&!coh_body_witness.located)){coh_body_witness.error=4;return;}
 rc=coh_body_witness_serialize(0,COH_BODY_WITNESS_CAP,&written);
 if(rc){coh_body_witness.error=rc;return;}
 coh_body_witness.used=written;coh_body_witness.count=GetBodyPartCount();coh_body_witness.rows=bodyPartList.bodyParts;coh_body_witness.ready=1;
}
