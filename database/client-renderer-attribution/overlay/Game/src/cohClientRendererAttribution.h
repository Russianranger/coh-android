/* Bounded renderer attribution only. Queue, pacing, loading and drawing policy
 * stay unchanged. One external TLS object is shared by the main-thread callsites
 * and separately owned by each render thread. Thread CPU is sampled at window
 * boundaries, not per command, and excludes llvmpipe/Wine/FEX worker threads.
 */
#ifndef COH_CLIENT_RENDERER_ATTRIBUTION_H
#define COH_CLIENT_RENDERER_ATTRIBUTION_H
#pragma push_macro("printf")
#pragma push_macro("vsnprintf")
#pragma push_macro("fflush")
#pragma push_macro("FILE")
#undef printf
#undef vsnprintf
#undef fflush
#undef FILE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdint.h>
#include <limits.h>

#define COH_RA_REPORT_MS 10000.0
#define COH_RA_MAX_REPORTS 120u
#define COH_RA_MAX_STATE_REPORTS 64u
#define COH_RA_BUCKETS 22
#define COH_RA_METRICS 10
#define COH_RA_LINE_BYTES 8192
#define COH_RA_FPS_COLUMN 1
#define COH_RA_FPS_ROW 14
enum CohRaMetric { COH_RA_GFX, COH_RA_WAIT, COH_RA_GFX_OTHER,
    COH_RA_BATCH, COH_RA_BATCH_OTHER, COH_RA_SWAP, COH_RA_TEXCOPY,
    COH_RA_TEXSUBCOPY, COH_RA_VBO, COH_RA_READBACK };
static const unsigned int coh_ra_bounds[COH_RA_BUCKETS-1] = {
    16,33,50,66,83,100,110,125,150,200,250,333,500,750,1000,2000,5000,
    10000,30000,60000,120000
};
static const char *const coh_ra_names[COH_RA_METRICS] = {
    "gfx_wall", "backpressure_wall", "gfx_other_wall", "renderer_batch_wall",
    "renderer_batch_non_swap_wall", "swap_wall", "texture_copy_wall",
    "texture_subcopy_wall", "vbo_create_wall", "framebuffer_readback_wall"
};
typedef struct CohRaMetricData {
    unsigned int count, histogram[COH_RA_BUCKETS];
    double sum, maximum;
} CohRaMetricData;
typedef struct CohRaStream {
    int initialized, enabled, renderer, frame_open, window_open, cpu_valid, have_wall;
    int limit, threaded, delay, state_valid, cap;
    unsigned int sli, reports, state_reports, waits, incomplete;
    unsigned int callbacks[4], phase_open;
    double frequency, window_start, cpu_start, frame_start, last_wall;
    double phase_start[COH_RA_METRICS], phase_wall[COH_RA_METRICS], showfps;
    CohRaMetricData metrics[COH_RA_METRICS];
} CohRaStream;
#ifdef COH_RENDERER_ATTRIBUTION_TEST
#ifdef _WIN32
#define COH_RA_TLS __declspec(thread)
#else
#define COH_RA_TLS _Thread_local
#endif
static __inline const char *cohRaEnvironment(void) { return cohRaTestEnvironment(); }
static __inline int cohRaPlatformInit(double *value) { *value=1.0; return 1; }
static __inline int cohRaPlatformWall(double frequency,double *value) {
    (void)frequency; return cohRaTestWall(value);
}
static __inline int cohRaPlatformCpu(double *value) { return cohRaTestCpu(value); }
static __inline void cohRaEmit(const char *line) { cohRaTestEmit(line); }
#else
#ifndef _WIN32
#error Production renderer attribution requires Win32
#endif
#include <windows.h>
#define COH_RA_TLS __declspec(thread)
static __inline const char *cohRaEnvironment(void) { return getenv("COH_CLIENT_RENDERER_ATTRIBUTION"); }
static __inline int cohRaPlatformInit(double *value) {
    LARGE_INTEGER ticks;
    if (!QueryPerformanceFrequency(&ticks) || ticks.QuadPart<=0) return 0;
    *value=(double)ticks.QuadPart; return 1;
}
static __inline int cohRaPlatformWall(double frequency,double *value) {
    LARGE_INTEGER ticks;
    if (!QueryPerformanceCounter(&ticks) || ticks.QuadPart<0) return 0;
    *value=(double)ticks.QuadPart*1000.0/frequency; return 1;
}
static __inline int cohRaPlatformCpu(double *value) {
    FILETIME creation,exit_time,kernel,user;
    ULARGE_INTEGER k,u;
    if (!GetThreadTimes(GetCurrentThread(),&creation,&exit_time,&kernel,&user)) return 0;
    k.LowPart=kernel.dwLowDateTime;k.HighPart=kernel.dwHighDateTime;
    u.LowPart=user.dwLowDateTime;u.HighPart=user.dwHighDateTime;
    *value=((double)k.QuadPart+(double)u.QuadPart)/10000.0; return 1;
}
static __inline void cohRaEmit(const char *line) { printf("%s\n",line);fflush(stdout); }
#endif
#ifdef COH_RA_IMPLEMENTATION
COH_RA_TLS CohRaStream coh_ra_stream;
#else
extern COH_RA_TLS CohRaStream coh_ra_stream;
#endif
static __inline int cohRaFinite(double value) { return value==value && value>=0.0 && value<1.0e12; }
static __inline unsigned int cohRaIncrement(unsigned int value) { return value<UINT_MAX?value+1:value; }
static __inline int cohRaActive(int renderer) {
    CohRaStream *s=&coh_ra_stream;
    if (!s->initialized) {
        const char *flag=cohRaEnvironment();
        s->initialized=1;s->renderer=renderer;
        s->enabled=flag && strcmp(flag,"1")==0 && cohRaPlatformInit(&s->frequency);
    }
    return s->enabled && s->renderer==renderer;
}
static __inline int cohRaWall(double *value) {
    CohRaStream *s=&coh_ra_stream;
    if (!cohRaPlatformWall(s->frequency,value) || !cohRaFinite(*value)
        || (s->have_wall && *value<s->last_wall)) { s->enabled=0; return 0; }
    s->have_wall=1;s->last_wall=*value;
    return 1;
}
static __inline void cohRaAdd(CohRaMetricData *m,double value) {
    unsigned int i;
    if (!cohRaFinite(value) || m->count==UINT_MAX) return;
    for (i=0;i<COH_RA_BUCKETS-1 && value>coh_ra_bounds[i];++i) {}
    ++m->count;++m->histogram[i];m->sum+=value;
    if (value>m->maximum) m->maximum=value;
}
static __inline int cohRaAppend(char *line,size_t *length,const char *format,...) {
    va_list arguments;int written;size_t available=COH_RA_LINE_BYTES-*length;
    if (!available) return 0;
    va_start(arguments,format);written=vsnprintf(line+*length,available,format,arguments);va_end(arguments);
    if (written<0 || (size_t)written>=available) { line[COH_RA_LINE_BYTES-1]=0;return 0; }
    *length+=(size_t)written;return 1;
}
static __inline int cohRaAppendNumber(char *line,size_t *length,double value) {
    uint64_t micros;
    if (!cohRaFinite(value)) return 0;
    micros=(uint64_t)(value*1000.0+0.5);
    return cohRaAppend(line,length,"%llu.%03u",(unsigned long long)(micros/1000),
        (unsigned int)(micros%1000));
}
static __inline int cohRaQuantile(const CohRaMetricData *m,unsigned int percent) {
    uint64_t rank=((uint64_t)m->count*percent+99)/100,seen=0;unsigned int i;
    for (i=0;i<COH_RA_BUCKETS;++i) {
        seen+=m->histogram[i];
        if (seen>=rank) return i<COH_RA_BUCKETS-1?(int)coh_ra_bounds[i]:-1;
    }
    return -1;
}
static __inline int cohRaAppendMetric(char *line,size_t *length,const CohRaMetricData *m) {
    unsigned int i;int p95=cohRaQuantile(m,95);
    if (!cohRaAppend(line,length,"{\"count\":%u,\"mean_ms\":",m->count)
        || !cohRaAppendNumber(line,length,m->sum/m->count)
        || !cohRaAppend(line,length,",\"max_ms\":") || !cohRaAppendNumber(line,length,m->maximum)
        || !cohRaAppend(line,length,",\"p95_upper_ms\":")) return 0;
    if (p95<0) { if (!cohRaAppend(line,length,"null")) return 0; }
    else if (!cohRaAppend(line,length,"%d",p95)) return 0;
    if (!cohRaAppend(line,length,",\"histogram\":[")) return 0;
    for (i=0;i<COH_RA_BUCKETS;++i)
        if (!cohRaAppend(line,length,"%s%u",i?",":"",m->histogram[i])) return 0;
    return cohRaAppend(line,length,"]}");
}
static __inline void cohRaState(int cap,double showfps) {
    CohRaStream *s=&coh_ra_stream;char line[COH_RA_LINE_BYTES];size_t length=0;int ok;
    if (!cohRaActive(0) || !cohRaFinite(showfps) || s->state_reports>=COH_RA_MAX_STATE_REPORTS
        || (s->state_valid && s->cap==cap && s->showfps==showfps)) return;
    ok=cohRaAppend(line,&length,"COH_CLIENT_RENDERER_ATTRIBUTION_V1 {\"format\":1,\"event\":\"state\",\"ordinal\":%u,\"maxfps\":%d,\"showfps\":",s->state_reports+1,cap)
        && cohRaAppendNumber(line,&length,showfps) && cohRaAppend(line,&length,"}");
    s->cap=cap;s->showfps=showfps;s->state_valid=1;++s->state_reports;
    if (ok) cohRaEmit(line);else s->enabled=0;
}
static __inline void cohRaReport(double now) {
    CohRaStream *s=&coh_ra_stream;char line[COH_RA_LINE_BYTES];size_t length=0;
    unsigned int i;int ok,cpu_valid,written=0;double cpu=0.0;
    if (now-s->window_start<COH_RA_REPORT_MS) return;
    cpu_valid=cohRaPlatformCpu(&cpu) && cohRaFinite(cpu);
    ok=cohRaAppend(line,&length,"COH_CLIENT_RENDERER_ATTRIBUTION_V1 {\"format\":1,\"event\":\"window\",\"role\":\"%s\",\"report\":%u,\"window_ms\":",s->renderer?"renderer":"main",s->reports+1)
        && cohRaAppendNumber(line,&length,now-s->window_start)
        && cohRaAppend(line,&length,",\"thread_cpu_ms\":");
    if (cpu_valid && s->cpu_valid && cpu>=s->cpu_start)
        ok=ok && cohRaAppendNumber(line,&length,cpu-s->cpu_start);
    else ok=ok && cohRaAppend(line,&length,"null");
    ok=ok && cohRaAppend(line,&length,",\"wait_iterations\":%u,\"incomplete_batches\":%u,\"callback_counts\":[%u,%u,%u,%u],",s->waits,s->incomplete,s->callbacks[0],s->callbacks[1],s->callbacks[2],s->callbacks[3]);
    if (!s->renderer) ok=ok && cohRaAppend(line,&length,"\"configuration\":{\"allow_frames_buffered\":%d,\"threaded\":%d,\"sli_limit\":%u,\"frame_delay\":%d},",s->limit,s->threaded,s->sli,s->delay);
    ok=ok && cohRaAppend(line,&length,"\"bucket_upper_ms\":[");
    for (i=0;i<COH_RA_BUCKETS-1;++i) ok=ok && cohRaAppend(line,&length,"%s%u",i?",":"",coh_ra_bounds[i]);
    ok=ok && cohRaAppend(line,&length,",null],\"metrics\":{");
    for (i=0;i<COH_RA_METRICS;++i) if (s->metrics[i].count) {
        ok=ok && cohRaAppend(line,&length,"%s\"%s\":",written?",":"",coh_ra_names[i])
            && cohRaAppendMetric(line,&length,&s->metrics[i]);written=1;
    }
    ok=ok && cohRaAppend(line,&length,"}}");
    if (ok) cohRaEmit(line);
    ++s->reports;if (!ok || s->reports>=COH_RA_MAX_REPORTS) s->enabled=0;
    memset(s->metrics,0,sizeof(s->metrics));memset(s->callbacks,0,sizeof(s->callbacks));
    s->waits=s->incomplete=0;s->window_start=now;s->cpu_start=cpu;s->cpu_valid=cpu_valid;
}
static __inline void cohRaBegin(int renderer) {
    CohRaStream *s=&coh_ra_stream;double now;
    if (!cohRaActive(renderer) || !cohRaWall(&now)) return;
    if (!s->window_open) {
        s->window_open=1;s->window_start=now;
        s->cpu_valid=cohRaPlatformCpu(&s->cpu_start) && cohRaFinite(s->cpu_start);
    } else if (now<s->window_start || (s->frame_open && now<s->frame_start)) {s->enabled=0;return;}
    if (s->frame_open) s->incomplete=cohRaIncrement(s->incomplete);
    s->frame_open=1;s->frame_start=now;s->phase_open=0;memset(s->phase_wall,0,sizeof(s->phase_wall));
}
static __inline void cohRaMainBegin(int ordinary,int limit,int threaded,unsigned int sli,int delay,int cap,double showfps) {
    CohRaStream *s=&coh_ra_stream;
    if (!ordinary || !cohRaActive(0)) return;
    cohRaState(cap,showfps);s->limit=limit;s->threaded=threaded;s->sli=sli;s->delay=delay;cohRaBegin(0);
}
static __inline void cohRaPhaseBegin(int metric) {
    CohRaStream *s=&coh_ra_stream;double now;
    if (!s->enabled || !s->frame_open || metric<0 || metric>=COH_RA_METRICS || !cohRaWall(&now)) return;
    s->phase_start[metric]=now;s->phase_open|=1u<<metric;
}
static __inline void cohRaPhaseEnd(int metric) {
    CohRaStream *s=&coh_ra_stream;double now;
    if (!s->enabled || !s->frame_open || metric<0 || metric>=COH_RA_METRICS
        || !(s->phase_open&(1u<<metric)) || !cohRaWall(&now)) return;
    if (now<s->phase_start[metric]) {s->enabled=0;return;}
    s->phase_wall[metric]+=now-s->phase_start[metric];s->phase_open&=~(1u<<metric);
    if (metric>=COH_RA_TEXCOPY) s->callbacks[metric-COH_RA_TEXCOPY]=cohRaIncrement(s->callbacks[metric-COH_RA_TEXCOPY]);
}
static __inline void cohRaWaitIteration(void) {
    CohRaStream *s=&coh_ra_stream;
    if (s->enabled && !s->renderer && s->frame_open) s->waits=cohRaIncrement(s->waits);
}
static __inline void cohRaEnd(int renderer) {
    CohRaStream *s=&coh_ra_stream;double now,total,part;unsigned int i;
    if (!cohRaActive(renderer) || !s->frame_open || !cohRaWall(&now)) return;
    if (now<s->frame_start) {s->enabled=0;return;}
    total=now-s->frame_start;part=s->phase_wall[renderer?COH_RA_SWAP:COH_RA_WAIT];
    if (part>total || s->phase_open) {s->enabled=0;return;}
    cohRaAdd(&s->metrics[renderer?COH_RA_BATCH:COH_RA_GFX],total);
    cohRaAdd(&s->metrics[renderer?COH_RA_BATCH_OTHER:COH_RA_GFX_OTHER],total-part);
    if (renderer) for (i=COH_RA_SWAP;i<COH_RA_METRICS;++i) cohRaAdd(&s->metrics[i],s->phase_wall[i]);
    else cohRaAdd(&s->metrics[COH_RA_WAIT],part);
    s->frame_open=0;cohRaReport(now);
}
static __inline void cohRaMainEnd(int ordinary) {if(ordinary)cohRaEnd(0);}
static __inline void cohRaRendererBegin(void) {cohRaBegin(1);}
static __inline void cohRaRendererEnd(void) {cohRaEnd(1);}
#pragma pop_macro("FILE")
#pragma pop_macro("fflush")
#pragma pop_macro("vsnprintf")
#pragma pop_macro("printf")
#endif
