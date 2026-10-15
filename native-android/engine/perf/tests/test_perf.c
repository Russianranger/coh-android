#define _POSIX_C_SOURCE 200809L
#include "coh_perf.h"
#include "coh_skin_cache.h"
#include <assert.h>
#include <float.h>
#include <inttypes.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static uint64_t checks, allocations, releases;
#define CHECK(x) do { checks++; if (!(x)) { fprintf(stderr,"check failed at %s:%d: %s\n",__FILE__,__LINE__,#x); abort(); } } while (0)
void *__real_malloc(size_t); void *__real_calloc(size_t, size_t); void *__real_realloc(void *,size_t);
void __real_free(void *);
void *__wrap_malloc(size_t n) { allocations++; return __real_malloc(n); }
void *__wrap_calloc(size_t a,size_t b) { allocations++; return __real_calloc(a,b); }
void *__wrap_realloc(void *p,size_t n) { allocations++; return __real_realloc(p,n); }
void __wrap_free(void *p) { if(p)releases++; __real_free(p); }
static uint64_t ns(void) {
  struct timespec t; CHECK(!clock_gettime(CLOCK_PROCESS_CPUTIME_ID,&t));
  return (uint64_t)t.tv_sec*1000000000+(uint64_t)t.tv_nsec;
}
static float rows[COH_MESH_MAX_BONES*12];
static void palette(unsigned bones) {
  memset(rows,0,sizeof rows);
  for(unsigned b=0;b<bones;b++) {
    float a=(float)b*.13f, c=cosf(a), s=sinf(a); float *p=rows+b*12;
    p[0]=c;p[1]=-s;p[3]=(float)b*.07f;p[4]=s;p[5]=c;p[7]=-(float)b*.03f;p[10]=1;p[11]=(float)b*.09f;
  }
}
static void perf_checks(char *json,size_t cap) {
  CohPerf p, untouched; memset(&p,0x5a,sizeof p); untouched=p;
  CohPerfConfig config=coh_perf_default_config(); config.stall_ns=0;
  CHECK(coh_perf_init(&p,&config)==COH_INVALID);CHECK(!memcmp(&p,&untouched,sizeof p));
  config=coh_perf_default_config();CHECK(coh_perf_init(&p,&config)==COH_OK);
  coh_perf_surface(&p,1);
  CHECK(coh_perf_frame_end(&p,0)==COH_STATE);
  CHECK(coh_perf_frame_begin(&p,1,2)==COH_STATE);
  CHECK(coh_perf_stage_begin(&p,COH_PERF_SKINNING,0)==COH_STATE);
  CHECK(coh_perf_stage_begin(&p,(CohPerfStage)-1,0)==COH_INVALID);
  for(uint64_t i=0;i<1000;i++) {
    uint64_t start=i*1000000000, elapsed=(i%80+1)*1000000;
    CHECK(coh_perf_frame_begin(&p,start,1)==COH_OK);
    CHECK(coh_perf_stage_begin(&p,COH_PERF_SKINNING,start+100)==COH_OK);
    CHECK(coh_perf_stage_end(&p,COH_PERF_SKINNING,start+100+elapsed/4)==COH_OK);
    CHECK(coh_perf_count(&p,COH_PERF_DRAW_CALLS,i%11+1)==COH_OK);
    CHECK(coh_perf_count(&p,COH_PERF_UPLOAD_BYTES,96)==COH_OK);
    CHECK(coh_perf_frame_end(&p,start+elapsed)==COH_OK);
  }
  CohPerfSnapshot snap;coh_perf_snapshot(&p,&snap);CHECK(snap.frame.samples==1000);
  CHECK(coh_perf_percentile_upper_ns(&snap.frame,0)==0);
  CHECK(coh_perf_percentile_upper_ns(&snap.frame,101)==0);
  CHECK(coh_perf_percentile_upper_ns(NULL,95)==0);
  coh_perf_resident(&p,4096);coh_perf_resident(&p,1024);
  CHECK(coh_perf_frame_begin(&p,1000000000001,1)==COH_OK);
  CHECK(coh_perf_stage_begin(&p,COH_PERF_COLLISION,1000000000002)==COH_OK);
  coh_perf_set_paused(&p,1);CHECK(coh_perf_frame_end(&p,2000000000000)==COH_STATE);
  CHECK(coh_perf_count(&p,COH_PERF_ALLOCATIONS,999)==COH_OK);
  coh_perf_set_paused(&p,0);
  CHECK(coh_perf_frame_begin(&p,2000000000001,1)==COH_OK);
  coh_perf_surface(&p,2);CHECK(coh_perf_frame_end(&p,3000000000000)==COH_STATE);
  CHECK(coh_perf_gpu_sample(&p,1,999,1,0)==COH_STATE);
  CHECK(coh_perf_gpu_sample_epoch(&p,2,2,999,1,0)==COH_STATE);
  CHECK(coh_perf_gpu_sample(&p,2,999,0,0)==COH_OK);
  CHECK(coh_perf_gpu_sample(&p,2,999,1,1)==COH_OK);
  CHECK(coh_perf_gpu_sample(&p,2,123456,1,0)==COH_OK);
  coh_perf_gpu_unavailable(&p);
  size_t needed=0;char small[3]={'x','x','x'};
  CHECK(coh_perf_json(&p,small,sizeof small,&needed)==COH_LIMIT);CHECK(small[0]==0);CHECK(needed>sizeof small);
  size_t correct=needed;CHECK(coh_perf_json(&p,NULL,0,&needed)==COH_LIMIT);CHECK(needed==correct);
  CHECK(coh_perf_json(&p,json,cap,&needed)==COH_OK);CHECK(strlen(json)+1==needed);
  CHECK(coh_perf_json(&p,NULL,2,&needed)==COH_INVALID);
  CohPerf q;CHECK(coh_perf_init(&q,&config)==COH_OK);coh_perf_surface(&q,1);
  CHECK(coh_perf_frame_begin(&q,100,1)==COH_OK);CHECK(coh_perf_frame_begin(&q,101,1)==COH_STATE);
  CHECK(coh_perf_stage_begin(&q,COH_PERF_SKINNING,99)==COH_INVALID);
  CHECK(coh_perf_stage_begin(&q,COH_PERF_SKINNING,101)==COH_OK);
  CHECK(coh_perf_stage_begin(&q,COH_PERF_SKINNING,102)==COH_STATE);
  CHECK(coh_perf_stage_end(&q,COH_PERF_SKINNING,100)==COH_INVALID);
  CHECK(coh_perf_frame_end(&q,99)==COH_INVALID);CHECK(q.snapshot.dropped_frames==1);
  CHECK(coh_perf_frame_begin(&q,1,1)==COH_OK);CHECK(coh_perf_frame_end(&q,UINT64_MAX)==COH_OK);
  CHECK(coh_perf_frame_begin(&q,0,1)==COH_OK);CHECK(coh_perf_frame_end(&q,UINT64_MAX)==COH_OK);
  CHECK(q.snapshot.frame.sum_ns==UINT64_MAX);CHECK(coh_perf_percentile_upper_ns(&q.snapshot.frame,99)==UINT64_MAX);
  CHECK(coh_perf_count(&q,COH_PERF_COPIED_BYTES,UINT64_MAX)==COH_OK);
  CHECK(coh_perf_count(&q,COH_PERF_COPIED_BYTES,1)==COH_OK);CHECK(q.snapshot.counters[0]==UINT64_MAX);
  CHECK(coh_perf_count(&q,(CohPerfCounter)-1,1)==COH_INVALID);
  config.enabled=0;CHECK(coh_perf_configure(&q,&config)==COH_OK);CohPerfSnapshot disabled=q.snapshot;
  CHECK(coh_perf_frame_begin(&q,0,1)==COH_OK);CHECK(coh_perf_frame_end(&q,1)==COH_OK);
  CHECK(coh_perf_count(&q,COH_PERF_DRAW_CALLS,1)==COH_OK);CHECK(!memcmp(&disabled,&q.snapshot,sizeof disabled));
  config.enabled=1;config.stage_mask=0;CHECK(coh_perf_configure(&q,&config)==COH_OK);
  CHECK(coh_perf_stage_begin(&q,COH_PERF_SKINNING,1)==COH_OK);CHECK(!q.active_stages);
  config.stage_mask=UINT32_MAX;CHECK(coh_perf_configure(&q,&config)==COH_INVALID);
}
static void compare(CohSkinCache *c,CohSkinKey k,CohMeshVertex *v,unsigned count,unsigned bones,int expect_hit) {
  CohSkinnedVertex *baseline=malloc((size_t)count*sizeof *baseline);CHECK(baseline);
  for(unsigned i=0;i<count;i++)CHECK(!coh_mesh_skin_vertex(&v[i],rows,bones,&baseline[i]));
  const CohSkinnedVertex *actual=NULL;int hit=-1;
  CHECK(coh_skin_cache_sample(c,k,v,count,rows,bones,&actual,&hit)==COH_OK);
  CHECK(hit==expect_hit);CHECK(!memcmp(actual,baseline,(size_t)count*sizeof *baseline));free(baseline);
}
static void cache_checks(void) {
  CohSkinCacheConfig cfg={2,3,2,65536};CohSkinCache *cache=NULL;
  CHECK(coh_skin_cache_create(&cfg,&cache)==COH_OK);
  CohMeshVertex v[3];memset(v,0,sizeof v);for(unsigned i=0;i<3;i++){v[i].position[0]=(float)i;v[i].normal[1]=1;v[i].weights[0]=.75f;v[i].weights[1]=.25f;v[i].bones[1]=1;}
  palette(2);CohSkinKey key={1,2,3,1,1,1};compare(cache,key,v,3,2,0);compare(cache,key,v,3,2,1);
  for(unsigned field=0;field<6;field++) {
    CohSkinKey k=key;
    if(field==0)k.mesh++;else if(field==1)k.rig++;else if(field==2)k.pose++;
    else if(field==3)k.mesh_generation++;else if(field==4)k.rig_generation++;else k.pose_generation++;
    compare(cache,k,v,3,2,0);compare(cache,k,v,3,2,1);
  }
  compare(cache,key,v,3,2,0);v[0].position[0]+=1;compare(cache,key,v,3,2,0);
  rows[3]+=.2f;compare(cache,key,v,3,2,0);compare(cache,key,v,3,2,1);
  /* Mutation oracle: wrapper must match unchanged kernel acceptance and exact
   * output for every bit in a source vertex. No malformed hit may bypass it. */
  for(unsigned byte=0;byte<sizeof v[0];byte++)for(unsigned bit=0;bit<8;bit++) {
    CohMeshVertex copy=v[0];((unsigned char *)&copy)[byte]^=(unsigned char)(1u<<bit);
    CohSkinnedVertex reference;int result=coh_mesh_skin_vertex(&copy,rows,2,&reference);
    const CohSkinnedVertex *out=(const CohSkinnedVertex *)(uintptr_t)1;int hit=-1;
    CohStatus status=coh_skin_cache_sample(cache,key,&copy,1,rows,2,&out,&hit);
    CHECK((status==COH_OK)==!result);
    if(!result)CHECK(!memcmp(out,&reference,sizeof reference));else {CHECK(out==(const CohSkinnedVertex *)(uintptr_t)1);CHECK(hit==-1);}
  }
  const CohSkinnedVertex *out=(const CohSkinnedVertex *)(uintptr_t)1;int hit=-1;
  CHECK(coh_skin_cache_sample(cache,key,v,4,rows,2,&out,&hit)==COH_INVALID);
  CHECK(coh_skin_cache_sample(cache,key,v,3,rows,3,&out,&hit)==COH_INVALID);
  CHECK(coh_skin_cache_sample(cache,key,NULL,3,rows,2,&out,&hit)==COH_INVALID);
  CHECK(coh_skin_cache_sample(cache,key,v,0,rows,2,&out,&hit)==COH_INVALID);
  CHECK(coh_skin_cache_sample(cache,key,v,3,NULL,2,&out,&hit)==COH_INVALID);
  key.pose_generation=0;CHECK(coh_skin_cache_sample(cache,key,v,3,rows,2,&out,&hit)==COH_INVALID);key.pose_generation=1;
  CHECK(out==(const CohSkinnedVertex *)(uintptr_t)1);CHECK(hit==-1);
  rows[0]=NAN;CHECK(coh_skin_cache_sample(cache,key,v,3,rows,2,&out,&hit)==COH_INVALID);palette(2);
  rows[0]=FLT_MAX;v[0].position[0]=FLT_MAX;CHECK(coh_skin_cache_sample(cache,key,v,3,rows,2,&out,&hit)==COH_INVALID);palette(2);v[0].position[0]=0;
  coh_skin_cache_invalidate(cache);CHECK(!coh_skin_cache_stats(cache).resident_entries);compare(cache,key,v,3,2,0);
  CohSkinCacheStats s=coh_skin_cache_stats(cache);CHECK(s.allocated_bytes<=cfg.byte_budget);CHECK(s.evictions>0);CHECK(s.rejections>0);
  coh_skin_cache_destroy(&cache);CHECK(cache==NULL);coh_skin_cache_destroy(&cache);
  cfg.byte_budget=1;CHECK(coh_skin_cache_create(&cfg,&cache)==COH_LIMIT);CHECK(!cache);
  cfg.entries=65;CHECK(coh_skin_cache_create(&cfg,&cache)==COH_INVALID);
  CHECK(coh_skin_cache_sample(NULL,key,v,3,rows,2,&out,&hit)==COH_INVALID);
}
int main(int argc,char **argv) {
  CHECK(argc==2);char json[8192];perf_checks(json,sizeof json);cache_checks();
  FILE *f=fopen(argv[1],"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long length=ftell(f);CHECK(length>=64&&length<8*1024*1024);rewind(f);
  unsigned char *raw=malloc((size_t)length);CHECK(raw);CHECK(fread(raw,1,(size_t)length,f)==(size_t)length);CHECK(!fclose(f));
  CohMeshView mesh;CHECK(!coh_mesh_parse(raw,(size_t)length,&mesh));
  CohMeshVertex *vertices=malloc((size_t)mesh.vertex_count*sizeof *vertices);
  CohSkinnedVertex *baseline=malloc((size_t)mesh.vertex_count*sizeof *baseline);
  CohSkinnedVertex *dynamic=malloc((size_t)mesh.vertex_count*100*sizeof *dynamic);CHECK(vertices&&baseline&&dynamic);
  for(unsigned i=0;i<mesh.vertex_count;i++)CHECK(!coh_mesh_vertex(&mesh,i,&vertices[i]));
  palette(mesh.bone_count);CohSkinKey key={7,8,9,1,1,1};
  CohSkinCacheConfig cfg={2,mesh.vertex_count,mesh.bone_count,16*1024*1024};CohSkinCache *cache=NULL;
  uint64_t before=allocations;CHECK(coh_skin_cache_create(&cfg,&cache)==COH_OK);CHECK(allocations-before==1);
  const CohSkinnedVertex *actual=NULL;int hit=-1;CHECK(coh_skin_cache_sample(cache,key,vertices,mesh.vertex_count,rows,mesh.bone_count,&actual,&hit)==COH_OK);CHECK(!hit);
  uint64_t hot_allocations=allocations;unsigned iterations=1000;
  uint64_t start=ns();
  for(unsigned t=0;t<iterations;t++)for(unsigned i=0;i<mesh.vertex_count;i++)CHECK(!coh_mesh_skin_vertex(&vertices[i],rows,mesh.bone_count,&baseline[i]));
  uint64_t baseline_ns=ns()-start;start=ns();
  for(unsigned t=0;t<iterations;t++) {CHECK(coh_skin_cache_sample(cache,key,vertices,mesh.vertex_count,rows,mesh.bone_count,&actual,&hit)==COH_OK);CHECK(hit);CHECK(!memcmp(actual,baseline,(size_t)mesh.vertex_count*sizeof *baseline));}
  uint64_t hit_ns=ns()-start;CHECK(allocations==hot_allocations);
  CohSkinCacheStats stats=coh_skin_cache_stats(cache);CHECK(stats.hits==iterations);CHECK(stats.kernel_vertices==mesh.vertex_count);
  /* Dynamic poses are a deliberate miss workload: retain a test-only reference
   * array then compare every output. No claim that the cache benefits it. */
  start=ns();for(unsigned t=0;t<100;t++){rows[3]=(float)t*.001f;for(unsigned i=0;i<mesh.vertex_count;i++)CHECK(!coh_mesh_skin_vertex(&vertices[i],rows,mesh.bone_count,&dynamic[(size_t)t*mesh.vertex_count+i]));}
  uint64_t dynamic_reference_ns=ns()-start;
  start=ns();for(unsigned t=0;t<100;t++){rows[3]=(float)t*.001f;key.pose_generation=t+2;CHECK(coh_skin_cache_sample(cache,key,vertices,mesh.vertex_count,rows,mesh.bone_count,&actual,&hit)==COH_OK);CHECK(!hit);CHECK(!memcmp(actual,dynamic+(size_t)t*mesh.vertex_count,(size_t)mesh.vertex_count*sizeof *dynamic));}
  uint64_t dynamic_miss_ns=ns()-start;CHECK(allocations==hot_allocations);
  CohPerf observer;CohPerfConfig observer_config=coh_perf_default_config();CHECK(coh_perf_init(&observer,&observer_config)==COH_OK);coh_perf_surface(&observer,1);
  start=ns();for(uint64_t t=0;t<10000;t++){CHECK(coh_perf_frame_begin(&observer,t*100000000,1)==COH_OK);CHECK(coh_perf_stage_begin(&observer,COH_PERF_SKINNING,t*100000000+10)==COH_OK);CHECK(coh_perf_count(&observer,COH_PERF_UPLOAD_BYTES,4096)==COH_OK);CHECK(coh_perf_stage_end(&observer,COH_PERF_SKINNING,t*100000000+100)==COH_OK);CHECK(coh_perf_frame_end(&observer,t*100000000+16000000)==COH_OK);}
  uint64_t observer_ns=ns()-start;CHECK(allocations==hot_allocations);
  printf("{\"status\":\"passed\",\"checks\":%"PRIu64",\"host_only\":true,\"mesh_vertices\":%u,\"mesh_bones\":%u,\"cache_allocated_bytes\":%zu,\"observer_bytes\":%zu,\"iterations\":%u,\"repeated_pose_baseline_cpu_ns\":%"PRIu64",\"repeated_pose_hit_cpu_ns_including_memcmp_oracle\":%"PRIu64",\"dynamic_pose_iterations\":100,\"dynamic_pose_baseline_cpu_ns\":%"PRIu64",\"dynamic_pose_miss_cpu_ns_including_memcmp_oracle\":%"PRIu64",\"observer_10000_frames_cpu_ns\":%"PRIu64",\"hot_path_allocations\":%"PRIu64",\"cache_kernel_vertices_for_1000_repeats\":%"PRIu64",\"cache_compared_bytes\":%"PRIu64",\"perf\":%s}\n",
         checks,mesh.vertex_count,mesh.bone_count,stats.allocated_bytes,sizeof(CohPerf),iterations,baseline_ns,hit_ns,dynamic_reference_ns,dynamic_miss_ns,observer_ns,allocations-hot_allocations,stats.kernel_vertices,stats.compared_bytes,json);
  coh_skin_cache_destroy(&cache);free(vertices);free(baseline);free(dynamic);free(raw);CHECK(allocations==releases);return 0;
}
