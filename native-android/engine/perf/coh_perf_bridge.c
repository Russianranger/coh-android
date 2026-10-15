#include "coh_perf_bridge.h"
#include <inttypes.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

static uint64_t add(uint64_t a,uint64_t b){return UINT64_MAX-a<b?UINT64_MAX:a+b;}
void coh_perf_bridge_init(CohPerfBridge *b){if(b)memset(b,0,sizeof *b);}
CohStatus coh_perf_bridge_total(CohPerfBridge *b,CohPerf *p,CohPerfCounter c,uint64_t gen,uint64_t total){
    if(!b||!p||(unsigned)c>=COH_PERF_COUNTER_COUNT||!gen)return COH_INVALID;
    CohPerfCounterBinding *s=&b->counters[c];
    if(s->known&&!s->baseline){s->rejected=add(s->rejected,1);return COH_STATE;}
    if(s->known&&s->generation==gen&&total<s->total){s->rejected=add(s->rejected,1);return COH_STATE;}
    uint64_t delta=0;
    if(s->known&&s->generation==gen)delta=total-s->total;
    else if(s->known)s->rebases=add(s->rebases,1);
    s->known=s->baseline=1;s->generation=gen;s->total=total;s->observations=add(s->observations,1);
    return coh_perf_count(p,c,delta);
}
CohStatus coh_perf_bridge_delta(CohPerfBridge *b,CohPerf *p,CohPerfCounter c,uint64_t delta){
    if(!b||!p||(unsigned)c>=COH_PERF_COUNTER_COUNT)return COH_INVALID;
    CohPerfCounterBinding *s=&b->counters[c];
    if(s->baseline){s->rejected=add(s->rejected,1);return COH_STATE;}
    s->known=1;s->total=add(s->total,delta);s->observations=add(s->observations,1);
    return coh_perf_count(p,c,delta);
}
CohStatus coh_perf_bridge_memory(CohPerfBridge *b,CohPerfMemoryKind kind,uint64_t bytes){
    if(!b||(unsigned)kind>=COH_PERF_MEMORY_COUNT)return COH_INVALID;
    CohPerfMemoryGauge *g=&b->memory[kind];g->current_bytes=bytes;
    if(bytes>g->peak_bytes)g->peak_bytes=bytes;
    g->observations=add(g->observations,1);return COH_OK;
}
typedef struct{char *out;size_t cap,used;int failed;} Json;
static void append(Json *j,const char *fmt,...){
    size_t left=j->used<j->cap?j->cap-j->used:0;va_list args;va_start(args,fmt);
    int n=vsnprintf(left?j->out+j->used:NULL,left,fmt,args);va_end(args);
    if(n<0||(size_t)n>SIZE_MAX-j->used)j->failed=1;else j->used+=(size_t)n;
}
CohStatus coh_perf_bridge_json(const CohPerfBridge *b,char *out,size_t cap,size_t *needed){
    static const char *const names[COH_PERF_COUNTER_COUNT]={"copied_bytes","upload_bytes","draw_calls","state_binds","skinned_vertices","collision_tests","asset_hits","asset_misses","asset_evictions","readbacks","explicit_waits","allocations"};
    static const char *const memory[COH_PERF_MEMORY_COUNT]={"module_accounted","process_rss","process_pss"};
    if(!b||(!out&&cap)||!needed)return COH_INVALID;
    Json j={out,cap,0,0};append(&j,"{\"schema\":1,\"module\":\"coh-native-perf-bindings\",\"counters\":{");
    for(unsigned i=0;i<COH_PERF_COUNTER_COUNT;i++){
        const CohPerfCounterBinding *s=&b->counters[i];
        append(&j,"%s\"%s\":{\"known\":%s,\"mode\":\"%s\",\"generation\":%"PRIu64",\"owner_total\":%"PRIu64",\"observations\":%"PRIu64",\"rebases\":%"PRIu64",\"rejected\":%"PRIu64"}",i?",":"",names[i],s->known?"true":"false",!s->known?"unknown":s->baseline?"total":"delta",s->generation,s->total,s->observations,s->rebases,s->rejected);
    }
    append(&j,"},\"memory\":{");
    for(unsigned i=0;i<COH_PERF_MEMORY_COUNT;i++){
        const CohPerfMemoryGauge *s=&b->memory[i];
        append(&j,"%s\"%s\":{\"known\":%s,\"current_bytes\":%"PRIu64",\"peak_bytes\":%"PRIu64",\"observations\":%"PRIu64"}",i?",":"",memory[i],s->observations?"true":"false",s->current_bytes,s->peak_bytes,s->observations);
    }
    append(&j,"}}");if(j.failed||j.used==SIZE_MAX){if(cap)out[0]=0;return COH_LIMIT;}
    *needed=j.used+1;if(*needed>cap){if(cap)out[0]=0;return COH_LIMIT;}return COH_OK;
}
