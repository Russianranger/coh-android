#include "../coh_wr_gpu_lease.h"
#ifdef COH_GPU_LEASE_FIXTURE_DIGEST
#include "egl_fixture_digest.h"
#define SHA256 coh_egl_fixture_digest
#else
#include <openssl/sha.h>
#endif
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do {checks++;if(!(x)){fprintf(stderr,"gpu lease control line %d\n",__LINE__);exit(2);}}while(0)
static const char asset_path[]="data/texture_library/npcs/objects/praetorian_box/box-1.texture";
typedef struct {uint8_t *raw;size_t size;CohAssetLoader *loader;CohWrTextureResource *cpu;CohWrTextureReport report;} Cpu;
static CohStatus read_at(void *v,uint64_t offset,void *out,size_t n) {
    Cpu *c=v;if(offset>c->size || n>c->size-offset)return COH_IO;
    memcpy(out,c->raw+(size_t)offset,n);return COH_OK;
}
static CohStatus digest(void *v,CohBytes b,uint8_t hash[32]) {(void)v;return SHA256(b.data,b.size,hash)?COH_OK:COH_IO;}
static void cpu_open(Cpu *c,const char *path) {
    FILE *f=fopen(path,"rb");CHECK(f);c->size=43990;c->raw=malloc(c->size);CHECK(c->raw);
    CHECK(fread(c->raw,1,c->size,f)==c->size && fgetc(f)==EOF && !fclose(f));
    CohAssetLimits al={8u<<20,4u<<20,2u<<20,2u<<20,16,16,8};CHECK(coh_asset_create(&al,&c->loader)==COH_OK);
    CHECK(coh_asset_mount_file(c->loader,asset_path,(CohAssetSource){read_at,c,c->size,17})==COH_OK);
    CohWrTextureRequest q={{asset_path,17},{0},digest,NULL};CHECK(digest(NULL,(CohBytes){c->raw,c->size},q.sha256)==COH_OK);
    CohWrTextureLimits l={16u<<20,c->size,8u<<20,1u<<20,1024,16};
    CHECK(coh_wr_texture_acquire(c->loader,&q,&l,(CohCancel){0},&c->cpu)==COH_OK);
    CHECK(coh_wr_texture_report(c->cpu,&c->report)==COH_OK && c->report.levels==9 && c->report.rgba_bytes==349524);
}
static void cpu_close(Cpu *c) {
    coh_wr_texture_release(&c->cpu);CHECK(!c->cpu);
    if(c->loader) {coh_asset_trim(c->loader);CHECK(!coh_asset_stats(c->loader).pinned_blobs);CHECK(coh_asset_destroy(&c->loader)==COH_OK);}
    free(c->raw);c->raw=NULL;
}
static CohWrSamplerSource fixture_sampler(void) {
    /* Explicit effective values for this ownership probe, NOT CLIENT witness. */
    CohWrSamplerSource s={192,0x0de1u,256,256,9,9,1,1.f};return s;
}
static CohWrGpuLeaseInput input(Cpu *c,uint64_t id,CohWrGpuTexture **take) {
    CohWrGpuLeaseInput v={id,{asset_path,17},{0},take};memcpy(v.source_sha256,c->report.sha256,32);return v;
}
static CohWrGpuLeaseLimits limits(size_t count) {
    CohWrGpuLeaseLimits l={COH_WR_MAX_MEMORY,32u<<20,count*4096,1u<<20};return l;
}
#ifndef COH_GPU_LEASE_TEST_LIBRARY
static unsigned fail_allocation;
void *__real_calloc(size_t,size_t);
void *__wrap_calloc(size_t n,size_t s) {if(fail_allocation){fail_allocation--;return NULL;}return __real_calloc(n,s);}
typedef struct {
    pthread_t gl;CohWrGpuToken token;uint64_t dead_context;
    unsigned pins,retains,releases,gate,deletes,images,currents,next;
    unsigned fail_retain,fail_delete,consume_error,fail_begin,fail_end;
    uint8_t names[128];int32_t state[6];
} Mock;
static int owns(Mock *m) {return pthread_equal(m->gl,pthread_self());}
static int token_same(CohWrGpuToken a,CohWrGpuToken b) {return a.surface_generation==b.surface_generation && a.context_generation==b.context_generation && a.render_thread==b.render_thread;}
static CohStatus m_current(void *v,CohWrGpuToken t) {Mock *m=v;m->currents++;return owns(m)&&!m->gate&&token_same(t,m->token)?COH_OK:COH_STATE;}
static CohStatus m_retire(void *v,CohWrGpuToken t) {Mock *m=v;return owns(m)&&t.context_generation==m->token.context_generation&&t.render_thread==m->token.render_thread&&t.surface_generation<=m->token.surface_generation?COH_OK:COH_STATE;}
static CohStatus m_dead(void *v,CohWrGpuToken t) {Mock *m=v;return owns(m)&&t.context_generation==m->dead_context&&t.render_thread==m->token.render_thread?COH_OK:COH_STATE;}
static CohStatus m_integer(void *v,uint32_t p,int32_t *out) {
    Mock *m=v;static const uint32_t keys[]={0x8069,0x88ef,0x0cf5,0x0cf2,0x0cf3,0x0cf4};
    if(!owns(m)||m->gate)return COH_STATE;
    if(p==0x0d33){*out=4096;return COH_OK;}
    for(unsigned i=0;i<6;i++)if(keys[i]==p){*out=m->state[i];return COH_OK;}
    return COH_INVALID;
}
static CohStatus m_generate(void *v,uint32_t *out) {Mock *m=v;if(!owns(m)||m->gate||m->next>=127)return COH_STATE;*out=++m->next;m->names[*out]=1;return COH_OK;}
static CohStatus m_bind(void *v,uint32_t n) {Mock *m=v;if(!owns(m)||m->gate)return COH_STATE;m->state[0]=(int32_t)n;return COH_OK;}
static CohStatus m_buffer(void *v,uint32_t n) {Mock *m=v;if(!owns(m)||m->gate)return COH_STATE;m->state[1]=(int32_t)n;return COH_OK;}
static CohStatus m_pixel(void *v,uint32_t p,int32_t n) {Mock *m=v;static const uint32_t keys[]={0x0cf5,0x0cf2,0x0cf3,0x0cf4};if(!owns(m)||m->gate)return COH_STATE;for(unsigned i=0;i<4;i++)if(p==keys[i]){m->state[i+2]=n;return COH_OK;}return COH_INVALID;}
static CohStatus m_image(void *v,uint32_t l,uint32_t w,uint32_t h,CohBytes b) {Mock *m=v;(void)l;if(!owns(m)||m->gate||!b.data||b.size!=(size_t)w*h*4)return COH_INVALID;m->images++;return COH_OK;}
static CohStatus m_parameter(void *v,uint32_t p,int32_t n) {Mock *m=v;(void)p;(void)n;return owns(m)&&!m->gate?COH_OK:COH_STATE;}
static CohStatus m_other_parameter(void *v,uint32_t p,int32_t n) {return m_parameter(v,p,n);}
static CohStatus m_delete(void *v,uint32_t *name) {Mock *m=v;if(!owns(m))return COH_STATE;m->deletes++;if(m->fail_delete)return COH_IO;CHECK(*name<128);m->names[*name]=0;*name=0;return m->consume_error?COH_IO:COH_OK;}
static CohStatus m_retain(void *v) {Mock *m=v;m->retains++;if(m->fail_retain)return COH_IO;m->pins++;return COH_OK;}
static void m_release(void *v) {Mock *m=v;CHECK(m->pins);m->pins--;m->releases++;}
static CohStatus m_begin(void *v,CohWrGpuToken t) {Mock *m=v;if(m->fail_begin || m->gate || (m_retire(v,t)!=COH_OK&&m_dead(v,t)!=COH_OK))return COH_STATE;m->gate=1;return COH_OK;}
static CohStatus m_end(void *v,CohWrGpuToken t) {Mock *m=v;(void)t;if(!owns(m)||!m->gate||m->fail_end)return COH_IO;m->gate=0;return COH_OK;}
static CohWrGpuLeaseBackend backend(Mock *m) {
    CohWrGpuLeaseBackend b={{m,m_current,m_retire,m_dead,m_integer,m_generate,m_bind,m_buffer,m_pixel,m_image,m_parameter,m_delete},m_retain,m_release,m_begin,m_end};return b;
}
static CohWrGpuTexture *upload(Cpu *c,Mock *m,const CohWrGpuLeaseBackend *b) {
    CohWrGpuTexture *g=NULL;CohWrGpuJournal j={0};CohWrSamplerSource s=fixture_sampler();
    CohWrGpuLimits l={64u<<20,16u<<20,c->report.rgba_bytes,1024};
    CHECK(coh_wr_gpu_upload(c->cpu,&s,m->token,&b->gpu,&l,(CohCancel){0},&g,&j)==COH_OK && g && !j.pending);return g;
}
typedef struct {unsigned at,calls;} Cancel;
static int cancel(void *v) {Cancel *c=v;return ++c->calls==c->at;}
typedef struct {CohWrPresentationResources resources;CohWrGpuLease *owner;CohStatus hold,resolve,drain;uint32_t handle;} Wrong;
static void *wrong(void *v) {Wrong *w=v;w->hold=w->resources.hold(w->resources.context);w->resources.drop(w->resources.context);w->handle=0x12345678;w->resolve=w->resources.resolve(w->resources.context,11,17,1,&w->handle);w->drain=coh_wr_gpu_lease_drain(w->owner);return NULL;}
int main(int argc,char **argv) {
    CHECK(argc==2);Cpu c={0};cpu_open(&c,argv[1]);Mock m={0};m.gl=pthread_self();m.token=(CohWrGpuToken){1,1,1};m.state[2]=4;
    CohWrGpuLeaseBackend b=backend(&m);CohWrGpuTexture *g[2]={upload(&c,&m,&b),upload(&c,&m,&b)};
    CohWrGpuTexture *saved[2]={g[0],g[1]};CohWrGpuLeaseInput in[2]={input(&c,11,g),input(&c,22,g+1)};
    CohWrGpuLeaseLimits l=limits(2);CohWrGpuLease *r=NULL;unsigned callbacks=m.currents,retains=m.retains;
    CohWrGpuLeaseInput bad[2];memcpy(bad,in,sizeof(bad));bad[1].texture_id=11;
    CHECK(coh_wr_gpu_lease_adopt(bad,2,&b,&l,(CohCancel){0},&r)==COH_INVALID && !r && g[0]==saved[0] && g[1]==saved[1]);
    bad[1]=in[1];bad[1].take=g;CHECK(coh_wr_gpu_lease_adopt(bad,2,&b,&l,(CohCancel){0},&r)==COH_INVALID);
    CohWrGpuTexture *duplicate=g[0];bad[1]=in[1];bad[1].take=&duplicate;
    CHECK(coh_wr_gpu_lease_adopt(bad,2,&b,&l,(CohCancel){0},&r)==COH_INVALID && duplicate==g[0]);
    bad[1]=in[1];bad[1].source_sha256[0]^=1;CHECK(coh_wr_gpu_lease_adopt(bad,2,&b,&l,(CohCancel){0},&r)==COH_STATE);
    bad[1]=in[1];bad[1].asset.path="data/other.texture";CHECK(coh_wr_gpu_lease_adopt(bad,2,&b,&l,(CohCancel){0},&r)==COH_STATE);
    bad[1]=in[1];bad[1].asset.generation=18;CHECK(coh_wr_gpu_lease_adopt(bad,2,&b,&l,(CohCancel){0},&r)==COH_STATE);
    /* Deliberately point another immutable path into a caller-owned take slot.
     * Shape is bounded first; alias refusal precedes any GPU report/GL callback. */
    const unsigned char *slot_bytes=(const unsigned char*)(const void*)g;size_t first=0;
    while(first<sizeof(g)&&!slot_bytes[first])first++;
    CHECK(first<sizeof(g)&&memchr(slot_bytes+first,0,sizeof(g)-first));
    bad[1]=in[1];bad[1].asset.path=(const char*)(const void*)(slot_bytes+first);
    CHECK(coh_wr_gpu_lease_adopt(bad,2,&b,&l,(CohCancel){0},&r)==COH_INVALID && g[0]==saved[0] && g[1]==saved[1]);
    CohWrGpuLeaseLimits low=l;low.external_bytes=0;CHECK(coh_wr_gpu_lease_adopt(in,2,&b,&low,(CohCancel){0},&r)==COH_LIMIT);
    low=l;low.gpu_owner_cpu_reservation=0;CHECK(coh_wr_gpu_lease_adopt(in,2,&b,&low,(CohCancel){0},&r)==COH_LIMIT);
    low=l;low.external_bytes=SIZE_MAX;CHECK(coh_wr_gpu_lease_adopt(in,2,&b,&low,(CohCancel){0},&r)==COH_LIMIT);
    CHECK(coh_wr_gpu_lease_adopt(in,2,&b,&l,(CohCancel){0},(CohWrGpuLease**)(void*)in)==COH_INVALID);
    CHECK(coh_wr_gpu_lease_adopt(in,2,&b,&l,(CohCancel){0},(CohWrGpuLease**)(void*)&l)==COH_INVALID);
    CHECK(m.currents==callbacks && m.retains==retains && !r && g[0]==saved[0] && g[1]==saved[1]);
    fail_allocation=1;CHECK(coh_wr_gpu_lease_adopt(in,2,&b,&l,(CohCancel){0},&r)==COH_LIMIT && !r && !m.pins);
    m.fail_retain=1;CHECK(coh_wr_gpu_lease_adopt(in,2,&b,&l,(CohCancel){0},&r)==COH_IO && !r && !m.pins);m.fail_retain=0;
    for(unsigned point=1;point<=4;point++) {Cancel x={point,0};CHECK(coh_wr_gpu_lease_adopt(in,2,&b,&l,(CohCancel){cancel,&x},&r)==COH_CANCELLED && !r && !m.pins && g[0]==saved[0] && g[1]==saved[1]);}
    CohWrGpuLeaseBackend other=b;other.gpu.parameter=m_other_parameter;
    CHECK(coh_wr_gpu_lease_adopt(in,2,&other,&l,(CohCancel){0},&r)==COH_STATE && !r && !m.pins && g[0]==saved[0] && g[1]==saved[1]);
    m.token.surface_generation=2;CHECK(coh_wr_gpu_lease_adopt(in,2,&b,&l,(CohCancel){0},&r)==COH_STATE && !r && !m.pins);m.token.surface_generation=1;
    CHECK(coh_wr_gpu_lease_adopt(in,2,&b,&l,(CohCancel){0},&r)==COH_OK && r && !g[0] && !g[1] && m.pins==1);
    CohWrGpuLeaseReport report;CHECK(coh_wr_gpu_lease_report(r,&report)==COH_OK && report.textures==2 && report.remaining_textures==2);
    CHECK(coh_wr_gpu_lease_report(r,(CohWrGpuLeaseReport*)(void*)r)==COH_INVALID);
    CohWrGpuTexture *exact_gpu[2]={upload(&c,&m,&b),upload(&c,&m,&b)};
    CohWrGpuLeaseInput exact_in[2]={input(&c,55,exact_gpu),input(&c,66,exact_gpu+1)};CohWrGpuLease *exact_owner=NULL;
    CohWrGpuLeaseLimits exact=l;exact.aggregate_limit=exact.external_bytes+report.owned_bytes+COH_WR_GPU_LEASE_CONTROL_RESERVE;
    exact.aggregate_limit--;unsigned before=m.currents;
    CHECK(coh_wr_gpu_lease_adopt(exact_in,2,&b,&exact,(CohCancel){0},&exact_owner)==COH_LIMIT && !exact_owner && exact_gpu[0] && exact_gpu[1] && m.currents==before);
    exact.aggregate_limit++;CHECK(coh_wr_gpu_lease_adopt(exact_in,2,&b,&exact,(CohCancel){0},&exact_owner)==COH_OK && !exact_gpu[0] && !exact_gpu[1]);
    CohWrPresentationResources exact_resources;CHECK(coh_wr_gpu_lease_resources(exact_owner,&exact_resources)==COH_OK);
    CHECK(coh_wr_gpu_lease_retire(exact_owner)==COH_OK && coh_wr_gpu_lease_drain(exact_owner)==COH_OK && coh_wr_gpu_lease_collect(&exact_owner)==COH_OK);
    CohWrGpuTexture *another=upload(&c,&m,&b);CohWrGpuLeaseInput one=input(&c,33,&another);CohWrGpuLease *prior=r;
    CHECK(coh_wr_gpu_lease_adopt(&one,1,&b,&l,(CohCancel){0},&r)==COH_STATE && r==prior && another);
    CHECK(coh_wr_gpu_release(&another,&b.gpu)==COH_OK && !another);
    CohWrPresentationResources resources;CHECK(coh_wr_gpu_lease_resources(r,&resources)==COH_OK);
    CHECK(coh_wr_gpu_lease_resources(r,(CohWrPresentationResources*)(void*)r)==COH_INVALID);
    CHECK(resources.hold(resources.context)==COH_OK && resources.hold(resources.context)==COH_OK);
    uint32_t name=0;CHECK(resources.resolve(resources.context,11,17,1,&name)==COH_OK && m.names[name]);
    CHECK(resources.resolve(resources.context,11,17,1,(uint32_t*)(void*)r)==COH_INVALID);
    uint32_t sentinel=123;CHECK(resources.resolve(resources.context,99,17,1,&sentinel)==COH_NOT_FOUND && sentinel==123);
    CHECK(resources.resolve(resources.context,11,18,1,&sentinel)==COH_STATE && sentinel==123);
    CHECK(resources.resolve(resources.context,11,17,2,&sentinel)==COH_STATE && sentinel==123);
    CHECK(coh_wr_gpu_lease_retire(r)==COH_OK && resources.hold(resources.context)==COH_STATE);
    unsigned deletes=m.deletes;CHECK(coh_wr_gpu_lease_drain(r)==COH_STATE && m.deletes==deletes);
    Wrong w={resources,r,COH_OK,COH_OK,COH_OK,0};pthread_t thread;CHECK(!pthread_create(&thread,NULL,wrong,&w) && !pthread_join(thread,NULL));
    CHECK(w.hold==COH_STATE && w.resolve==COH_STATE && w.drain==COH_STATE && w.handle==0x12345678 && m.deletes==deletes);
    CHECK(coh_wr_gpu_lease_report(r,&report)==COH_OK && report.leases==2 && report.callback_faults==1);
    resources.drop(resources.context);CHECK(coh_wr_gpu_lease_drain(r)==COH_STATE && m.names[name]);resources.drop(resources.context);
    m.fail_begin=1;CHECK(coh_wr_gpu_lease_drain(r)==COH_STATE && !m.gate && m.deletes==deletes && m.pins==1);m.fail_begin=0;
    m.fail_delete=1;CHECK(coh_wr_gpu_lease_drain(r)==COH_IO && m.gate && m.pins==1 && m.names[name]);
    CHECK(coh_wr_gpu_lease_collect(&r)==COH_STATE && r==prior);
    m.fail_delete=0;m.fail_end=1;CHECK(coh_wr_gpu_lease_drain(r)==COH_IO && m.gate && !m.names[name]);
    CHECK(coh_wr_gpu_lease_report(r,&report)==COH_OK && !report.remaining_textures && report.cleanup_gate && !report.drained);
    m.fail_end=0;CHECK(coh_wr_gpu_lease_drain(r)==COH_OK && !m.gate);CHECK(coh_wr_gpu_lease_collect(&r)==COH_OK && !r && !m.pins);
    /* Error after a verified delete retains the small opaque owner for retry. */
    g[0]=upload(&c,&m,&b);one=input(&c,44,g);CHECK(coh_wr_gpu_lease_adopt(&one,1,&b,&l,(CohCancel){0},&r)==COH_OK);
    CHECK(coh_wr_gpu_lease_resources(r,&resources)==COH_OK && coh_wr_gpu_lease_retire(r)==COH_OK);m.consume_error=1;
    CHECK(coh_wr_gpu_lease_drain(r)==COH_IO && m.gate);m.consume_error=0;CHECK(coh_wr_gpu_lease_drain(r)==COH_OK);CHECK(coh_wr_gpu_lease_collect(&r)==COH_OK);
    cpu_close(&c);CHECK(!m.pins && !m.gate);for(unsigned i=1;i<=m.next;i++)CHECK(!m.names[i]);
    printf("{\"passed\":true,\"checks\":%u,\"model_only\":true,\"actual_gles\":false,\"world_authority\":false,\"actor_authority\":false,\"source_generation_admitted\":false}\n",checks);return 0;
}
#endif
