#include "../coh_debug_entity.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks,draws,allocations;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"debugentity line%d %s\n",__LINE__,#x);exit(1);}}while(0)
void*__real_malloc(size_t);void*__real_calloc(size_t,size_t);
void*__wrap_malloc(size_t n){allocations++;return __real_malloc(n);}void*__wrap_calloc(size_t n,size_t m){allocations++;return __real_calloc(n,m);}
static uint32_t word(FILE*f){uint8_t b[4];CHECK(fread(b,1,4,f)==4);return(uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;}
static CohStatus compile(void*v,CohMaterialFamily f,const char*a,const char*b,uint32_t*out){(void)v;(void)f;CHECK(a&&b&&*a&&*b);*out=11;return COH_OK;}
static void destroy(void*v,uint32_t p){(void)v;CHECK(p==11);}
static CohStatus bind(void*v,uint32_t p,const CohRenderMaterial*m){(void)v;CHECK(p==11&&m->textures[0].handle==73&&!m->cull_back&&m->depth_test&&m->depth_write);return COH_OK;}
static CohStatus draw(void*v,uint32_t p,const CohRenderDraw*d){(void)v;CHECK(p==11&&d->geometry.vertex_count==8&&d->geometry.index_count==36);for(unsigned i=0;i<36;i++)CHECK(d->geometry.indices[i]<8);draws++;return COH_OK;}
static void identity(float*m){memset(m,0,16*sizeof(*m));for(unsigned i=0;i<4;i++)m[i*5]=1;}
int main(int argc,char**argv){CHECK(argc==2);FILE*f=fopen(argv[1],"rb");CHECK(f);uint32_t count=word(f),valid=0;unsigned cuts=0;
 CohRenderer*r=NULL;CohRendererConfig config={1,8,36,1};CohRenderBackend backend={compile,destroy,bind,draw,NULL};CHECK(coh_renderer_create(&config,&backend,&r)==COH_OK);
 for(unsigned n=0;n<count;n++){
  uint32_t row[18];for(unsigned i=0;i<18;i++)row[i]=word(f);uint8_t*wire=malloc(row[0]);CHECK(wire&&fread(wire,1,row[0],f)==row[0]);
  CohRepReader reader;CHECK(coh_rep_reader_bounded(&reader,(CohBytes){wire,row[0]},row[1],(int)row[2],COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);reader.cursor=row[8];CohRepReader unchanged=reader;
  CohInitialPoseProbe old={0},probe={0};CohInitialPoseSample sample;memset(&sample,0xa5,sizeof(sample));unsigned before=allocations;
  CohStatus status=coh_initial_pose_probe(&reader,row[5],&old);CHECK(coh_initial_pose_probe_with_sample(&reader,row[5],&probe,&sample)==status&&!memcmp(&old,&probe,sizeof(old))&&!memcmp(&unchanged,&reader,sizeof(reader))&&allocations==before);
  CHECK(sample.valid==probe.pose_validated);
  if(sample.valid){
   valid++;CohRepReader position_reader=reader;position_reader.cursor=row[10];CohRepPosition reference;coh_rep_position_init(&reference);CHECK(coh_rep_position(&position_reader,row[5],&reference)==COH_OK&&reference.valid);CHECK(sample.packet_id==row[5]&&!memcmp(&sample.position,&reference.position,sizeof(sample.position)));
   float view[16],projection[16];identity(view);identity(projection);view[12]=-sample.position.x;view[13]=-sample.position.y-3;view[14]=-sample.position.z-22;CohRenderTexture white={73,COH_WRAP_CLAMP,COH_WRAP_CLAMP,COH_FILTER_NEAREST,COH_FILTER_NEAREST};CohRenderDraw d;before=allocations;
   CHECK(coh_debug_entity_draw(&sample,17,view,projection,white,&d)==COH_OK&&allocations==before);CHECK(d.model_view[12]==0&&d.model_view[13]==-3&&d.model_view[14]==-22);
   for(unsigned i=0;i<8;i++){float clip[4],normal[3],lit[4],fog;CHECK(coh_renderer_vertex(&d,d.geometry.vertices+i,clip,normal,lit,&fog)==COH_OK);CHECK(clip[0]==d.geometry.vertices[i].position[0]&&clip[1]==d.geometry.vertices[i].position[1]-3&&clip[2]==d.geometry.vertices[i].position[2]-22&&clip[3]==1);CHECK(lit[0]==1&&lit[1]==.45f&&lit[2]==.05f);}
   CHECK(coh_renderer_begin(r,0)==COH_OK&&coh_renderer_submit(r,&d)==COH_OK&&coh_renderer_flush(r,(CohCancel){0})==COH_OK);
   CohRenderDraw saved=d;CohInitialPoseSample bad=sample;bad.valid=0;CHECK(coh_debug_entity_draw(&bad,17,view,projection,white,&d)==COH_INVALID&&!memcmp(&saved,&d,sizeof(d)));bad=sample;bad.position.x=NAN;CHECK(coh_debug_entity_draw(&bad,17,view,projection,white,&d)==COH_INVALID&&!memcmp(&saved,&d,sizeof(d)));CHECK(coh_debug_entity_draw(&sample,0,view,projection,white,&d)==COH_INVALID&&!memcmp(&saved,&d,sizeof(d)));CHECK(coh_debug_entity_draw(&sample,COH_ENT_INDEX_MAX+1u,view,projection,white,&d)==COH_INVALID);CHECK(coh_debug_entity_draw(&sample,17,view,projection,white,(CohRenderDraw*)view)==COH_INVALID);
   view[0]=INFINITY;CHECK(coh_debug_entity_draw(&sample,17,view,projection,white,&d)==COH_INVALID&&!memcmp(&saved,&d,sizeof(d)));
  }else{CohInitialPoseSample zero={0};CHECK(!memcmp(&sample,&zero,sizeof(sample)));}
  if(row[3]==0)for(size_t end=reader.cursor;end<row[12];end++){CohRepReader shortened=reader;shortened.bits=end;sample=(CohInitialPoseSample){.position={111,222,333},.packet_id=123,.valid=1};CHECK(coh_initial_pose_probe_with_sample(&shortened,row[5],&probe,&sample)!=COH_OK&&!sample.valid&&!sample.packet_id);cuts++;}
  if(n==0){sample=(CohInitialPoseSample){.position={111,222,333},.packet_id=123,.valid=1};CohInitialPoseSample saved=sample;probe=old;CHECK(coh_initial_pose_probe_with_sample(&reader,0,&probe,&sample)==COH_INVALID&&!memcmp(&saved,&sample,sizeof(sample))&&!memcmp(&probe,&old,sizeof(probe)));CHECK(coh_initial_pose_probe_with_sample(&reader,row[5],&probe,(CohInitialPoseSample*)&probe)==COH_INVALID);CHECK(coh_initial_pose_probe_with_sample(&reader,row[5],&probe,(CohInitialPoseSample*)wire)==COH_INVALID);CHECK(coh_initial_pose_probe_with_sample(&reader,row[5],&probe,NULL)==COH_INVALID);}
  free(wire);
 }
 CHECK(fgetc(f)==EOF&&!fclose(f));CHECK(count==91&&valid==62&&draws==62);CohRendererStats stats=coh_renderer_stats(r);CHECK(stats.drawn==62&&stats.rejected==0);coh_renderer_destroy(r);
 printf("{\"passed\":true,\"checks\":%u,\"source_pose_fixtures\":%u,\"decoded_pose_box_draws\":%u,\"truncated_pose_cases\":%u,\"new_query_heap_allocations\":0,\"complete_actor\":false,\"application_ack\":false,\"actual_server_or_Android_execution\":false}\n",checks,count,draws,cuts);return 0;
}
