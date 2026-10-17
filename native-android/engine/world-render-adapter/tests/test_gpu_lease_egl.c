/* Qualification-only access to the existing private pbuffer registry. No
 * application context adoption API is added or changed. Its current/pthread/
 * destruction checks still run before every delegated GPU operation. */
#include "coh_gpu_egl_backend.c"
#define COH_GPU_LEASE_TEST_LIBRARY
#include "test_gpu_lease.c"
typedef struct {
    CohGpuEglBackend *egl;CohWrGpuOps base;
    atomic_uint pins,retains,releases;
    CohWrGpuToken gate_token,cleanup_token;
    unsigned gate,fail_delete,fail_end,delete_calls,deleted,images;
} Registry;
static int eq_token(CohWrGpuToken a,CohWrGpuToken b) {return a.surface_generation==b.surface_generation&&a.context_generation==b.context_generation&&a.render_thread==b.render_thread;}
static CohStatus rg_normal(Registry *r) {if(!owner(r->egl)||r->gate)return COH_STATE;return r->base.current(r->base.context,token(r->egl));}
static CohStatus rg_current(void *v,CohWrGpuToken t) {Registry *r=v;if(rg_normal(r)!=COH_OK)return COH_STATE;return r->base.current(r->base.context,t);}
static CohStatus rg_retire(void *v,CohWrGpuToken t) {Registry *r=v;if(!owner(r->egl)||(r->gate&&!eq_token(t,r->gate_token)))return COH_STATE;CohStatus s=r->base.retire_current(r->base.context,t);if(s==COH_OK)r->cleanup_token=t;return s;}
static CohStatus rg_destroyed(void *v,CohWrGpuToken t) {Registry *r=v;return r->base.destroyed(r->base.context,t);}
static CohStatus rg_integer(void *v,uint32_t p,int32_t *out) {Registry *r=v;if(rg_normal(r)!=COH_OK)return COH_STATE;return r->base.get_integer(r->base.context,p,out);}
static CohStatus rg_generate(void *v,uint32_t *out) {Registry *r=v;if(rg_normal(r)!=COH_OK)return COH_STATE;return r->base.generate(r->base.context,out);}
static CohStatus rg_bind(void *v,uint32_t n) {Registry *r=v;if(rg_normal(r)!=COH_OK)return COH_STATE;return r->base.bind_texture(r->base.context,n);}
static CohStatus rg_buffer(void *v,uint32_t n) {Registry *r=v;if(rg_normal(r)!=COH_OK)return COH_STATE;return r->base.bind_unpack_buffer(r->base.context,n);}
static CohStatus rg_pixel(void *v,uint32_t p,int32_t n) {Registry *r=v;if(rg_normal(r)!=COH_OK)return COH_STATE;return r->base.pixel_store(r->base.context,p,n);}
static CohStatus rg_image(void *v,uint32_t level,uint32_t w,uint32_t h,CohBytes b) {Registry *r=v;if(rg_normal(r)!=COH_OK)return COH_STATE;CohStatus s=r->base.image_rgba8(r->base.context,level,w,h,b);if(s==COH_OK)r->images++;return s;}
static CohStatus rg_parameter(void *v,uint32_t p,int32_t n) {Registry *r=v;if(rg_normal(r)!=COH_OK)return COH_STATE;return r->base.parameter(r->base.context,p,n);}
static CohStatus rg_delete(void *v,uint32_t *name) {
    Registry *r=v;if(r->base.retire_current(r->base.context,r->cleanup_token)!=COH_OK)return COH_STATE;
    r->delete_calls++;if(r->fail_delete)return COH_IO;
    CohStatus s=r->base.delete_texture(r->base.context,name);if(!*name)r->deleted++;return s;
}
static CohStatus rg_retain(void *v) {Registry *r=v;atomic_fetch_add(&r->pins,1);atomic_fetch_add(&r->retains,1);return COH_OK;}
static void rg_release(void *v) {Registry *r=v;CHECK(atomic_load(&r->pins)>0);atomic_fetch_sub(&r->pins,1);atomic_fetch_add(&r->releases,1);}
static CohStatus rg_begin(void *v,CohWrGpuToken t) {
    Registry *r=v;if(!owner(r->egl)||r->gate)return COH_STATE;
    if(r->base.retire_current(r->base.context,t)!=COH_OK&&r->base.destroyed(r->base.context,t)!=COH_OK)return COH_STATE;
    r->gate_token=t;r->gate=1;return COH_OK;
}
static CohStatus rg_end(void *v,CohWrGpuToken t) {
    Registry *r=v;if(!owner(r->egl)||!r->gate||!eq_token(t,r->gate_token)||r->fail_end)return COH_IO;
    r->gate=0;return COH_OK;
}
static CohWrGpuLeaseBackend rg_backend(Registry *r) {
    CohWrGpuLeaseBackend b={{r,rg_current,rg_retire,rg_destroyed,rg_integer,rg_generate,rg_bind,rg_buffer,rg_pixel,rg_image,rg_parameter,rg_delete},rg_retain,rg_release,rg_begin,rg_end};return b;
}
static CohStatus rg_close(Registry *r) {if(atomic_load(&r->pins)||r->gate)return COH_STATE;return coh_gpu_egl_close(&r->egl);}
static CohWrGpuTexture *real_upload(Cpu *c,Registry *r,const CohWrGpuLeaseBackend *b) {
    CohWrGpuTexture *g=NULL;CohWrGpuJournal journal={0};CohWrSamplerSource s=fixture_sampler();
    CohWrGpuLimits l={64u<<20,32u<<20,c->report.rgba_bytes,1024};
    CHECK(coh_wr_gpu_upload(c->cpu,&s,token(r->egl),&b->gpu,&l,(CohCancel){0},&g,&journal)==COH_OK && g && !journal.pending);return g;
}
/* Only a probe readback. Production bridge has no readback/FBO dependency. */
static void readback(Registry *r,uint32_t name,unsigned level,uint32_t w,uint32_t h,uint8_t *out) {
    GLint draw,read,pack,buffer,row,skiprow,skippixel;
    CHECK(rg_normal(r)==COH_OK);
    glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING,&draw);glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING,&read);
    glGetIntegerv(GL_PACK_ALIGNMENT,&pack);glGetIntegerv(GL_PIXEL_PACK_BUFFER_BINDING,&buffer);
    glGetIntegerv(GL_PACK_ROW_LENGTH,&row);glGetIntegerv(GL_PACK_SKIP_ROWS,&skiprow);glGetIntegerv(GL_PACK_SKIP_PIXELS,&skippixel);CHECK(glGetError()==GL_NO_ERROR);
    GLuint fbo=0;CHECK(rg_normal(r)==COH_OK);glGenFramebuffers(1,&fbo);CHECK(fbo && glGetError()==GL_NO_ERROR);
    CHECK(rg_normal(r)==COH_OK);glBindFramebuffer(GL_FRAMEBUFFER,fbo);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,name,(GLint)level);
    CHECK(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE && glGetError()==GL_NO_ERROR);
    CHECK(rg_normal(r)==COH_OK);glBindBuffer(GL_PIXEL_PACK_BUFFER,0);glPixelStorei(GL_PACK_ALIGNMENT,1);glPixelStorei(GL_PACK_ROW_LENGTH,0);glPixelStorei(GL_PACK_SKIP_ROWS,0);glPixelStorei(GL_PACK_SKIP_PIXELS,0);
    CHECK(rg_normal(r)==COH_OK);glReadPixels(0,0,(GLsizei)w,(GLsizei)h,GL_RGBA,GL_UNSIGNED_BYTE,out);CHECK(glGetError()==GL_NO_ERROR);
    CHECK(rg_normal(r)==COH_OK);glBindFramebuffer(GL_DRAW_FRAMEBUFFER,(GLuint)draw);glBindFramebuffer(GL_READ_FRAMEBUFFER,(GLuint)read);glDeleteFramebuffers(1,&fbo);
    glBindBuffer(GL_PIXEL_PACK_BUFFER,(GLuint)buffer);glPixelStorei(GL_PACK_ALIGNMENT,pack);glPixelStorei(GL_PACK_ROW_LENGTH,row);glPixelStorei(GL_PACK_SKIP_ROWS,skiprow);glPixelStorei(GL_PACK_SKIP_PIXELS,skippixel);CHECK(glGetError()==GL_NO_ERROR);
}
enum {ATTACH=1,HOLD,DROP,RETIRE,DRAIN,COLLECT,WRONG_RESOLVE,QUIT};
typedef struct {
    pthread_t thread;pthread_mutex_t mutex;pthread_cond_t condition;
    int command,done,slot;uint32_t surface;CohStatus result;
    CohWrGpuLease *owners[3];CohWrPresentationResources resources[3];
} Worker;
static void *control_worker(void *v) {
    Worker *w=v;pthread_mutex_lock(&w->mutex);
    for(;;) {
        while(!w->command)pthread_cond_wait(&w->condition,&w->mutex);
        int cmd=w->command,slot=w->slot;pthread_mutex_unlock(&w->mutex);CohStatus s=COH_STATE;
        CohWrPresentationResources *p=w->resources+slot;
        if(cmd==ATTACH)s=coh_wr_gpu_lease_resources(w->owners[slot],p);
        if(cmd==HOLD)s=p->hold(p->context);
        if(cmd==DROP){p->drop(p->context);s=COH_OK;}
        if(cmd==RETIRE)s=coh_wr_gpu_lease_retire(w->owners[slot]);
        if(cmd==DRAIN)s=coh_wr_gpu_lease_drain(w->owners[slot]);
        if(cmd==COLLECT)s=coh_wr_gpu_lease_collect(&w->owners[slot]);
        if(cmd==WRONG_RESOLVE){uint32_t name=0x12345678;s=p->resolve(p->context,11,17,w->surface,&name);if(name!=0x12345678)s=COH_INVALID;}
        pthread_mutex_lock(&w->mutex);w->result=s;w->command=0;w->done=1;pthread_cond_broadcast(&w->condition);
        if(cmd==QUIT)break;
    }
    pthread_mutex_unlock(&w->mutex);return NULL;
}
static CohStatus send(Worker *w,int slot,int cmd) {
    pthread_mutex_lock(&w->mutex);w->slot=slot;w->done=0;w->command=cmd;pthread_cond_broadcast(&w->condition);
    while(!w->done)pthread_cond_wait(&w->condition,&w->mutex);
    CohStatus s=w->result;pthread_mutex_unlock(&w->mutex);return s;
}
typedef struct {unsigned at,calls;} Cancellation;
static int cancel_adoption(void *v) {Cancellation *c=v;return ++c->calls==c->at;}
static void string(const char *p) {putchar('"');for(;*p;p++){unsigned c=(unsigned char)*p;if(c=='"'||c=='\\'){putchar('\\');putchar((int)c);}else if(c>=32&&c<127)putchar((int)c);else printf("\\u%04x",c);}putchar('"');}
int main(int argc,char **argv) {
    CHECK(argc==3);Cpu cpu={0};cpu_open(&cpu,argv[1]);Registry registry={0};CHECK(coh_gpu_egl_create(&registry.egl)==COH_OK);registry.base=registry.egl->ops;
    CohWrGpuToken old_token=token(registry.egl);
    CohWrGpuLeaseBackend backend=rg_backend(&registry);CohWrGpuTexture *gpu[4]={0};uint32_t names[4]={0};
    uint8_t *pixels=malloc(256u*256u*4u),*expected=malloc(256u*256u*4u);CHECK(pixels&&expected);
    FILE *packet=fopen(argv[2],"wb");CHECK(packet);unsigned readbacks=0;
    for(unsigned i=0;i<4;i++) {
        gpu[i]=real_upload(&cpu,&registry,&backend);CohRenderTexture view;
        CHECK(coh_wr_gpu_view(gpu[i],token(registry.egl),&backend.gpu,&view)==COH_OK);names[i]=view.handle;
        CHECK(glIsTexture(names[i])==GL_TRUE && glGetError()==GL_NO_ERROR);
        for(unsigned level=0;level<9;level++) {
            uint32_t w,h;CohBytes rgba;CHECK(coh_wr_texture_mip(cpu.cpu,level,&w,&h,&rgba)==COH_OK);
            readback(&registry,names[i],level,w,h,pixels);readbacks++;CHECK(!memcmp(pixels,rgba.data,rgba.size));
            CHECK(fwrite(pixels,1,rgba.size,packet)==rgba.size);if(i==0&&level==0)memcpy(expected,pixels,rgba.size);
        }
    }
    CHECK(!fclose(packet));CohWrGpuLeaseInput old[2]={input(&cpu,11,gpu),input(&cpu,22,gpu+1)};
    CohWrGpuLeaseInput surface=input(&cpu,33,gpu+2),dead=input(&cpu,44,gpu+3);CohWrGpuLeaseLimits l=limits(4);
    Worker worker={0};worker.surface=(uint32_t)old_token.surface_generation;CHECK(!pthread_mutex_init(&worker.mutex,NULL)&&!pthread_cond_init(&worker.condition,NULL));
    Cancellation c={3,0};CHECK(coh_wr_gpu_lease_adopt(old,2,&backend,&l,(CohCancel){cancel_adoption,&c},worker.owners)==COH_CANCELLED);
    CHECK(gpu[0]&&gpu[1]&&!worker.owners[0]&&!atomic_load(&registry.pins));
    CHECK(coh_wr_gpu_lease_adopt(old,2,&backend,&l,(CohCancel){0},worker.owners)==COH_OK);
    CHECK(coh_wr_gpu_lease_adopt(&surface,1,&backend,&l,(CohCancel){0},worker.owners+1)==COH_OK);
    CHECK(coh_wr_gpu_lease_adopt(&dead,1,&backend,&l,(CohCancel){0},worker.owners+2)==COH_OK);
    CHECK(!gpu[0]&&!gpu[1]&&!gpu[2]&&!gpu[3]&&atomic_load(&registry.pins)==3&&rg_close(&registry)==COH_STATE);
    CHECK(!pthread_create(&worker.thread,NULL,control_worker,&worker));
    for(unsigned i=0;i<3;i++)CHECK(send(&worker,(int)i,ATTACH)==COH_OK&&send(&worker,(int)i,HOLD)==COH_OK);
    CHECK(send(&worker,0,HOLD)==COH_OK);
    /* Genuine CPU owner, loader pins and file-provider bytes retire now. */
    cpu_close(&cpu);readback(&registry,names[0],0,256,256,pixels);readbacks++;CHECK(!memcmp(pixels,expected,256u*256u*4u));
    uint32_t name=0;CHECK(worker.resources[0].resolve(worker.resources[0].context,11,17,(uint32_t)old_token.surface_generation,&name)==COH_OK&&name==names[0]);
    CHECK(send(&worker,0,WRONG_RESOLVE)==COH_STATE);
    CHECK(send(&worker,0,RETIRE)==COH_OK && send(&worker,0,HOLD)==COH_STATE);
    CHECK(coh_wr_gpu_lease_drain(worker.owners[0])==COH_STATE && registry.deleted==0);
    CHECK(send(&worker,0,DROP)==COH_OK && coh_wr_gpu_lease_drain(worker.owners[0])==COH_STATE && registry.deleted==0);
    CHECK(glIsTexture(names[0])==GL_TRUE && glIsTexture(names[1])==GL_TRUE);
    CHECK(send(&worker,0,DROP)==COH_OK && send(&worker,0,DRAIN)==COH_STATE && registry.deleted==0);
    registry.fail_delete=1;CHECK(coh_wr_gpu_lease_drain(worker.owners[0])==COH_IO && registry.gate);
    /* Whole context normal work, including another leased set, is quarantined. */
    name=0x12345678;CHECK(worker.resources[1].resolve(worker.resources[1].context,33,17,(uint32_t)old_token.surface_generation,&name)==COH_STATE&&name==0x12345678);
    CHECK(send(&worker,0,COLLECT)==COH_STATE && atomic_load(&registry.pins)==3);
    registry.fail_delete=0;registry.fail_end=1;CHECK(coh_wr_gpu_lease_drain(worker.owners[0])==COH_IO && registry.gate && registry.deleted==2);
    CHECK(glIsTexture(names[0])==GL_FALSE && glIsTexture(names[1])==GL_FALSE && glGetError()==GL_NO_ERROR);
    CHECK(send(&worker,0,COLLECT)==COH_STATE);registry.fail_end=0;
    CHECK(coh_wr_gpu_lease_drain(worker.owners[0])==COH_OK&&!registry.gate);CHECK(send(&worker,0,COLLECT)==COH_OK&&atomic_load(&registry.pins)==2);
    /* Real Surface replacement preserves context, never re-labels old names. */
    CHECK(coh_gpu_egl_replace_surface(registry.egl)==COH_OK);
    CohWrGpuToken new_token=token(registry.egl);CHECK(new_token.context_generation==old_token.context_generation&&new_token.surface_generation!=old_token.surface_generation);
    name=0x12345678;CHECK(worker.resources[1].resolve(worker.resources[1].context,33,17,(uint32_t)new_token.surface_generation,&name)==COH_STATE&&name==0x12345678);
    CHECK(send(&worker,1,RETIRE)==COH_OK&&send(&worker,1,DROP)==COH_OK);
    CHECK(coh_wr_gpu_lease_drain(worker.owners[1])==COH_OK&&registry.deleted==3&&glIsTexture(names[2])==GL_FALSE);
    CHECK(send(&worker,1,COLLECT)==COH_OK&&atomic_load(&registry.pins)==1);
    /* Old context is actually unbound/destroyed before metadata disposition. */
    CHECK(coh_gpu_egl_replace_context(registry.egl)==COH_OK);CohWrGpuToken replacement=token(registry.egl);
    CHECK(replacement.context_generation!=old_token.context_generation);
    GLuint sentinels[4]={0};CHECK(rg_normal(&registry)==COH_OK);glGenTextures(4,sentinels);
    unsigned reused=0;for(unsigned i=0;i<4;i++){glBindTexture(GL_TEXTURE_2D,sentinels[i]);CHECK(glIsTexture(sentinels[i])==GL_TRUE);if(sentinels[i]==names[3])reused=1;}CHECK(glGetError()==GL_NO_ERROR);
    CHECK(send(&worker,2,RETIRE)==COH_OK&&send(&worker,2,DROP)==COH_OK);
    unsigned deletes=registry.delete_calls;CHECK(coh_wr_gpu_lease_drain(worker.owners[2])==COH_OK&&registry.delete_calls==deletes);
    for(unsigned i=0;i<4;i++)CHECK(glIsTexture(sentinels[i])==GL_TRUE);
    CHECK(send(&worker,2,COLLECT)==COH_OK&&!atomic_load(&registry.pins));
    glDeleteTextures(4,sentinels);CHECK(glGetError()==GL_NO_ERROR);
    (void)send(&worker,0,QUIT);CHECK(!pthread_join(worker.thread,NULL));pthread_cond_destroy(&worker.condition);pthread_mutex_destroy(&worker.mutex);
    CHECK(atomic_load(&registry.retains)==4&&atomic_load(&registry.releases)==4&&registry.images==36&&!registry.gate);
    CohGpuEglReport report;CHECK(coh_gpu_egl_destroy_contexts(registry.egl)==COH_OK&&coh_gpu_egl_report(registry.egl,&report)==COH_OK);
    CHECK(report.contexts_created==2&&report.contexts_destroyed==2&&report.surfaces_created==3&&report.surfaces_destroyed==3);
    CHECK(rg_close(&registry)==COH_OK&&!registry.egl);free(pixels);free(expected);
    printf("{\"passed\":true,\"checks\":%u,\"actual_gles\":true,\"cleanup_verified\":true,\"uploads\":4,\"readbacks\":%u,\"registry_retains\":4,\"registry_releases\":4,\"verified_deletes\":3,\"destroyed_context_disposals\":1,\"contexts_created\":2,\"contexts_destroyed\":2,\"surfaces_created\":3,\"surfaces_destroyed\":3,\"context_name_reuse_observed\":%s,\"generation_fixture_only\":true,\"sampler_fixture_only\":true,\"production_prepare_executed\":false,\"world_authority\":false,\"actor_authority\":false,\"source_generation_admitted\":false,\"gl_version\":",checks,readbacks,reused?"true":"false");
    string(report.gl_version);printf(",\"gl_renderer\":");string(report.gl_renderer);puts("}");return 0;
}
