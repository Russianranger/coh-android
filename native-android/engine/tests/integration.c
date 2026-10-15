#include "../assets/coh_asset_loader.h"
#include "../renderer/coh_renderer.h"
#include "../network/coh_net.h"
#include "../sequencer/coh_sequencer.h"
#include "../ui/coh_ui.h"
#include "../audio/coh_mixer.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#ifdef COH_ENGINE_WITH_DECODER
#include "../assets/coh_asset_audio.h"
#include <stdlib.h>
static void compressed_ownership(const char *path) {
    FILE *file=fopen(path,"rb");assert(file);assert(fseek(file,0,SEEK_END)==0);
    long length=ftell(file);assert(length>0 && length<=COH_DECODE_MAX_COMPRESSED);
    rewind(file);uint8_t *encoded=malloc((size_t)length);assert(encoded);
    assert(fread(encoded,1,(size_t)length,file)==(size_t)length);fclose(file);
    CohDecodedAudio decoded={0};CohDecodeProof proof={0};
    assert(coh_asset_sound_decode((CohBytes){encoded,(size_t)length},&decoded,&proof)==COH_OK);
    CohMixerConfig config={proof.sample_rate,4,16,4,1024*1024,0};CohMixer *mixer=NULL;
    assert(coh_mixer_create(&config,&mixer)==COH_OK);CohAudioResource resource;
    assert(coh_mixer_cache_decoded(mixer,(CohAssetId){"sound/authentic-ownership.ogg",1},
           (CohBytes){decoded.data,decoded.length},&resource)==COH_OK);
    coh_decode_release(&decoded);free(encoded);
    for(unsigned i=0;i<3;i++) {CohAudioEvent e={0};e.source=i+1;e.emitter=i+1;e.resource=resource;e.gain=.1f;e.bus=COH_BUS_FX;assert(coh_mixer_play(mixer,&e)==COH_OK);}
    float output[2048];assert(coh_mixer_render(mixer,output,1024)==COH_OK);
    CohMixerDiagnostics d;assert(coh_mixer_diagnostics(mixer,&d)==COH_OK && d.play_started==3);
    coh_mixer_destroy(mixer);
}
#endif

/* A contract test, not a source/GPU/server oracle. Authentic corpus admission
 * and original-function comparisons belong to the individual module suites. */
static CohUi ui;
static unsigned draws, programs;
static CohStatus read_at(void *ctx,uint64_t at,void *dst,size_t n) {
    const CohBytes *span=ctx;
    if (at>span->size || n>span->size-(size_t)at) return COH_IO;
    memcpy(dst,span->data+(size_t)at,n); return COH_OK;
}
static CohStatus compile_shader(void *ctx,CohMaterialFamily f,const char *v,const char *p,uint32_t *id) {
    (void)ctx; (void)f; assert(v && p); *id=++programs; return COH_OK;
}
static void destroy_shader(void *ctx,uint32_t id) { (void)ctx; assert(id); }
static CohStatus bind_material(void *ctx,uint32_t id,const CohRenderMaterial *m) {
    (void)ctx; assert(id && m); return COH_OK;
}
static CohStatus draw_mesh(void *ctx,uint32_t id,const CohRenderDraw *d) {
    (void)ctx; assert(id && d->geometry.vertex_count==3); draws++; return COH_OK;
}
static void identity(float m[16]) { memset(m,0,16*sizeof(float)); m[0]=m[5]=m[10]=m[15]=1; }
int main(int argc,char **argv) {
    int compressed_test=0;
#ifdef COH_ENGINE_WITH_DECODER
    if(argc>1){compressed_ownership(argv[1]);compressed_test=1;}
#else
    (void)argc;(void)argv;
#endif
    const int16_t pcm[8]={1000,2000,3000,4000,5000,6000,7000,8000};
    CohBytes backing={(const uint8_t *)pcm,sizeof pcm};
    CohAssetSource source={read_at,&backing,sizeof pcm,17};
    CohAssetLimits limits={1024*1024,4096,4096,4096,16,16,8};
    CohAssetLoader *assets=NULL; const CohAssetBlob *blob=NULL;
    CohAssetId asset={"sound/contract.pcm",17};
    assert(coh_asset_create(&limits,&assets)==COH_OK);
    assert(coh_asset_mount_file(assets,asset.path,source)==COH_OK);
    assert(coh_asset_acquire(assets,asset,(CohCancel){0},&blob)==COH_OK);
    coh_asset_trim(assets);
    assert(coh_asset_stats(assets).pinned_blobs==1);
    assert(coh_asset_destroy(&assets)==COH_STATE && assets);

    CohMixerConfig mc={8000,4,16,4,4096,0}; CohMixer *mixer=NULL;
    CohAudioResource resource; CohBytes bytes=coh_asset_bytes(blob);
    assert(coh_mixer_create(&mc,&mixer)==COH_OK);
    assert(coh_mixer_cache_pcm16(mixer,coh_asset_identity(blob),(const int16_t *)bytes.data,8,1,8000,&resource)==COH_OK);
    coh_asset_release(assets,blob); coh_asset_trim(assets);
    assert(coh_asset_stats(assets).resident_bytes==0);
    assert(coh_asset_destroy(&assets)==COH_OK && !assets);

    CohGameEvent event={0,77,1,{NULL,0}};
    CohAudioEvent audio={0}; audio.source=1; audio.emitter=event.actor;
    audio.resource=resource; audio.gain=.5f; audio.bus=COH_BUS_FX;
    assert(coh_mixer_play(mixer,&audio)==COH_OK);
    float stereo[16]; assert(coh_mixer_render(mixer,stereo,8)==COH_OK);
    assert(stereo[0]>0 && stereo[0]==stereo[1]);
    CohMixerDiagnostics diag; assert(coh_mixer_diagnostics(mixer,&diag)==COH_OK);
    assert(diag.play_started==1 && diag.play_completed==1);

    coh_ui_init(&ui,COH_UI_SCALE_FIT,NULL,NULL);
    CohUiDesc panel={0}; panel.id=1; panel.binding=event.actor; panel.kind=COH_UI_PROGRESS;
    panel.flags=COH_UI_VISIBLE|COH_UI_ENABLED; panel.rect=(CohUiRect){10,10,200,20};
    panel.color=0xffffffffu;panel.font_size=12; assert(coh_ui_add(&ui,&panel,"")==COH_OK);
    assert(coh_ui_bind_value(&ui,event.actor,(float)diag.play_started)==COH_OK);
    assert(coh_ui_surface(&ui,1,1280,720)==COH_OK);
    assert(coh_ui_build(&ui)==COH_OK && coh_ui_drawlist_valid(&ui,1));

    CohRenderBackend backend={compile_shader,destroy_shader,bind_material,draw_mesh,NULL};
    CohRenderer *renderer=NULL; CohRendererConfig rc=coh_renderer_default_config();
    assert(coh_renderer_create(&rc,&backend,&renderer)==COH_OK);
    coh_renderer_surface_lost(renderer,1,1); /* Explicitly adopt the common Surface generation. */
    const CohRenderVertex vertices[3]={
        {{-1,-1,-1},{0,0,1},{0,0},{0,0},{.125f,.125f,.125f,1}},
        {{1,-1,-1},{0,0,1},{1,0},{1,0},{.125f,.125f,.125f,1}},
        {{0,1,-1},{0,0,1},{.5f,1},{.5f,1},{.125f,.125f,.125f,1}}};
    uint32_t indices[3]={0,1,2};
    CohRenderDraw draw={0}; draw.geometry=(CohRenderGeometry){vertices,3,indices,3,1,1};
    draw.material=coh_renderer_default_material(COH_MAT_MULTIPLY); identity(draw.model_view);identity(draw.projection);
    assert(coh_renderer_begin(renderer,1)==COH_OK);
    assert(coh_renderer_submit(renderer,&draw)==COH_OK);
    assert(coh_renderer_flush(renderer,(CohCancel){0})==COH_OK && draws==1);

    CohSeqMove move={0}; move.name="ContractIdle";move.flags=COH_SEQ_CYCLE;move.scale=1;move.next_move=0;
    CohSeqGraph graph={&move,1}; CohSeqClip clip={asset,5,1,0,10,1};
    CohSequencer seq; assert(coh_seq_init(&seq,&graph,&clip,1,event.actor,8,0,0)==COH_OK);
    CohSeqInput input={0};input.timestep_frames=1;input.animation_scale=1;
    CohSeqSelection selection;assert(coh_seq_step(&seq,&input,&selection)==COH_OK);
    assert(selection.actor_id==audio.emitter && selection.rig_id==8);

    uint8_t frame[2048];size_t frame_bytes=0;CohNetPacket packet={0},parsed;
    packet.id=1;packet.payload_bits=8;packet.payload[0]=42;
    assert(coh_net_frame_encode(0,NULL,0,&packet,frame,sizeof frame,&frame_bytes)==COH_OK);
    assert(coh_net_frame_decode(0,NULL,0,0,(CohBytes){frame,frame_bytes},&parsed)==COH_OK);
    assert(parsed.payload_bits==8 && parsed.payload[0]==42);
    assert(coh_ui_bind_value(&ui,event.actor,parsed.payload[0]/100.f)==COH_OK);

    coh_renderer_surface_lost(renderer,2,1);coh_ui_surface_lost(&ui);
    assert(!coh_ui_drawlist_valid(&ui,1));
    assert(coh_ui_surface(&ui,2,720,1280)==COH_OK && coh_ui_build(&ui)==COH_OK);
    assert(coh_ui_drawlist_valid(&ui,2) && !coh_ui_drawlist_valid(&ui,1));
    assert(coh_renderer_begin(renderer,2)==COH_OK);
    assert(coh_renderer_submit(renderer,&draw)==COH_OK && coh_renderer_flush(renderer,(CohCancel){0})==COH_OK);
    assert(draws==2 && programs==2 && seq.actor_id==event.actor);
    coh_renderer_destroy(renderer);coh_ui_destroy(&ui);coh_mixer_destroy(mixer);
    printf("{\"passed\":true,\"groups\":6,\"authentic_compressed_ownership\":%s,\"scope\":\"cross-module ownership, identity, copied audio, UI binding, framing and lifecycle contracts; mocked renderer and synthetic network payload\"}\n",compressed_test?"true":"false");
    return 0;
}
