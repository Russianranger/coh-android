#include "../coh_wr_lod.h"
#include <float.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "lod-autodata-fixtures.h"
static unsigned checks,cases,rows_seen[5];
#define CHECK(x) do { checks++; if(!(x)){fprintf(stderr,"AutoLOD line%d %s\n",__LINE__,#x);exit(1);} } while(0)
extern CohWrAutoLodProjection original_autodata(const CohWrAutoLodInput*);
static CohWrAutoLodProjection compare(const CohWrAutoLodInput*q){
 CohWrAutoLodInput saved=*q;
 CohWrAutoLodProjection expected=original_autodata(q),actual;
 memset(&actual,0x55,sizeof(actual));
 CHECK(coh_wr_lod_autodata(q,&actual)==COH_OK);
 CHECK(!memcmp(q,&saved,sizeof(saved)));
 CHECK(actual.count==expected.count&&actual.count>=1&&actual.count<=4);
 CHECK(!memcmp(&actual,&expected,sizeof(actual)));
 cases++;rows_seen[actual.count]++;return actual;
}
static void refuse(CohWrAutoLodInput q,CohStatus status){
 CohWrAutoLodProjection actual,saved;memset(&saved,0x33,sizeof(saved));actual=saved;
 CHECK(coh_wr_lod_autodata(&q,&actual)==status);
 CHECK(!memcmp(&saved,&actual,sizeof(saved)));
}
int main(void){
 const float radii[]={0,1,199.999f,200,200.001f,500};
 const uint32_t triangles[]={0,1,199,200,201,266,267,268,2000,2001,2666,2667,4000,4001,8000,1000000,2147483647};
 const float distances[]={-1,0,124.999f,125,125.001f,250,375,500,874.999f,875,875.001f,1000};
 CohWrAutoLodInput q={0};q.has_reduction_distances=1;q.trick_lod[2]=1000;
 for(unsigned r=0;r<sizeof(radii)/sizeof(*radii);r++)
  for(unsigned t=0;t<sizeof(triangles)/sizeof(*triangles);t++)
   for(unsigned a=0;a<sizeof(distances)/sizeof(*distances);a++)
    for(unsigned b=0;b<sizeof(distances)/sizeof(*distances);b++){
     q.model_radius=radii[r];q.source_triangle_count=triangles[t];
     q.reduction_distances[0]=distances[a];q.reduction_distances[1]=distances[b];q.reduction_distances[2]=600;
     compare(&q);
    }
 /* Independent exact expectations cover all three source thresholds. */
 q=(CohWrAutoLodInput){10,0,{0,0,1000,100},{150,400,650},2000,1};
 CohWrAutoLodProjection out=compare(&q);CHECK(out.count==4);
 CHECK(out.rows[0].lod_farfade==5&&out.rows[1].lod_nearfade==5);
 CHECK(out.rows[1].lod_farfade==0&&out.rows[2].lod_nearfade==0);
 CHECK(out.rows[1].max_error==25&&out.rows[2].max_error==50&&out.rows[3].max_error==75);
 CHECK(out.rows[1].flags==130&&out.rows[3].lod_far==1000&&out.rows[3].lod_farfade==100);
 q.model_radius=200;out=compare(&q);CHECK(out.rows[0].lod_farfade==5);
 q.model_radius=200.001f;out=compare(&q);CHECK(out.rows[0].lod_farfade==25&&out.rows[3].lod_nearfade==25);
 q.model_radius=10;q.source_triangle_count=200;out=compare(&q);CHECK(out.count==1);
 q.source_triangle_count=201;out=compare(&q);CHECK(out.count==2);
 q.source_triangle_count=1000000;out=compare(&q);CHECK(out.count==3&&out.rows[1].max_error==50);
 q.source_triangle_count=2000;q.reduction_distances[0]=125;out=compare(&q);CHECK(out.rows[1].max_error==50);
 q.reduction_distances[0]=875;out=compare(&q);CHECK(out.count>=2);
 q.reduction_distances[0]=875.001f;out=compare(&q);CHECK(out.count==1);
 q=(CohWrAutoLodInput){20,30,{0,0,0,0},{0,0,0},0,0};out=compare(&q);
 CHECK(out.count==1&&out.rows[0].lod_far==500&&out.rows[0].lod_farfade==125);
 for(unsigned mask=1;mask<16;mask++){
  q=(CohWrAutoLodInput){20,30,{0,0,0,0},{0,0,0},0,0};
  for(unsigned j=0;j<4;j++)if(mask&(1u<<j))q.trick_lod[j]=(float)(j+1);
  out=compare(&q);
  /* Any specified trick distance suppresses the automatic quarter farfade. */
  CHECK(out.rows[0].lod_farfade==((mask&8)?4:0));
 }
 /* Captured model fields are actual SERVER numeric observations. No reduction
  * array or CLIENT decision was captured: array-absent is an explicit SOURCE
  * projection control, never a claim that a live model has no reductions. */
 for(unsigned i=0;i<sizeof(authentic_inputs)/sizeof(*authentic_inputs);i++){
  q=authentic_inputs[i];out=compare(&q);CHECK(out.count==1);
 }
 q=(CohWrAutoLodInput){20,30,{0,0,1000,0},{150,400,650},2000,1};
 for(unsigned field=0;field<9;field++)for(unsigned kind=0;kind<3;kind++){
  CohWrAutoLodInput bad=q;float*values[]={&bad.model_radius,&bad.shadow_distance,&bad.trick_lod[0],&bad.trick_lod[1],&bad.trick_lod[2],&bad.trick_lod[3],&bad.reduction_distances[0],&bad.reduction_distances[1],&bad.reduction_distances[2]};
  *values[field]=kind==0?NAN:kind==1?INFINITY:-1.f;
  if(kind==2&&field>=6)compare(&bad);else refuse(bad,COH_INVALID);
 }
 q.has_reduction_distances=2;refuse(q,COH_INVALID);q.has_reduction_distances=1;
 q.source_triangle_count=2147483648u;refuse(q,COH_INVALID);q.source_triangle_count=2000;
 q.model_radius=FLT_MAX;q.trick_lod[2]=0;refuse(q,COH_LIMIT);
 union {CohWrAutoLodInput input;CohWrAutoLodProjection output;} overlap;
 memset(&overlap,0,sizeof(overlap));overlap.input=q;
 CHECK(coh_wr_lod_autodata(&overlap.input,&overlap.output)==COH_INVALID);
 CHECK(coh_wr_lod_autodata(NULL,&out)==COH_INVALID);CHECK(coh_wr_lod_autodata(&q,NULL)==COH_INVALID);
 CHECK(rows_seen[1]&&rows_seen[2]&&rows_seen[3]&&rows_seen[4]);
 printf("{\"passed\":true,\"checks\":%u,\"source_combinations\":%u,\"actual_root_model_numeric_inputs\":%zu,\"row_counts\":[%u,%u,%u,%u],\"active_LOD_selection\":false,\"world_authority\":false}\n",checks,cases,sizeof(authentic_inputs)/sizeof(*authentic_inputs),rows_seen[1],rows_seen[2],rows_seen[3],rows_seen[4]);
 return 0;
}
