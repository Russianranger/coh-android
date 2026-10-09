/* Bounded observational pipeline clocks. Drawing, command scheduling, GL and
 * error policy are unchanged. Command timing samples one complete batch in
 * sixteen; QPC calls are skipped for commands in the other fifteen batches.
 * Command wall includes synchronous driver/wait work and is not GPU time.
 * Thread CPU is sampled only at window boundaries, excluding worker threads.
 */
#ifndef COH_CLIENT_RENDER_PIPELINE_H
#define COH_CLIENT_RENDER_PIPELINE_H
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

#define COH_RP_REPORT_MS 10000.0
#define COH_RP_MAX_REPORTS 120u
#define COH_RP_SAMPLE_INTERVAL 16u
#define COH_RP_BUCKETS 22
#define COH_RP_PHASES 7
#define COH_RP_METRICS 11
#define COH_RP_LINE_BYTES 8192
enum CohRpMetric { COH_RP_AUX, COH_RP_MAINVIEW, COH_RP_SUN, COH_RP_POST,
    COH_RP_UI, COH_RP_FINISH, COH_RP_FLUSH, COH_RP_GFX,
    COH_RP_BATCH, COH_RP_COMMAND, COH_RP_GAP };
static const unsigned int coh_rp_bounds[COH_RP_BUCKETS-1] = {
    16,33,50,66,83,100,110,125,150,200,250,333,500,750,1000,2000,5000,
    10000,30000,60000,120000
};
static const char *const coh_rp_names[COH_RP_METRICS] = {
    "aux_viewport_wall", "main_viewport_wall", "sun_wall", "postprocessing_wall",
    "ui_wall", "finish_wall", "queue_flush_wall", "gfx_wall",
    "renderer_batch_wall", "renderer_command_wall", "renderer_queue_gap_wall"
};
typedef struct CohRpMetricData {
    unsigned int count, histogram[COH_RP_BUCKETS];
    double sum, maximum;
} CohRpMetricData;
typedef struct CohRpStream {
    int initialized, enabled, renderer, frame_open, window_open, cpu_valid, have_wall;
    int sampled, command_open, command;
    unsigned int reports, incomplete, phase_open, sample_cursor, suppress_depth;
    unsigned int batch_commands, sampled_batches, sampled_commands;
    double frequency, window_start, cpu_start, frame_start, last_wall;
    double command_start, command_wall;
    double phase_start[COH_RP_PHASES], phase_wall[COH_RP_PHASES];
    CohRpMetricData metrics[COH_RP_METRICS];
} CohRpStream;
#ifdef COH_RENDER_PIPELINE_TEST
#ifdef _WIN32
#define COH_RP_TLS __declspec(thread)
#else
#define COH_RP_TLS _Thread_local
#endif
static __inline const char *cohRpEnvironment(void) { return cohRpTestEnvironment(); }
static __inline int cohRpPlatformInit(double *value) { *value=1.0; return 1; }
static __inline int cohRpPlatformWall(double frequency,double *value) {
    (void)frequency; return cohRpTestWall(value);
}
static __inline int cohRpPlatformCpu(double *value) { return cohRpTestCpu(value); }
static __inline void cohRpEmit(const char *line) { cohRpTestEmit(line); }
#else
#ifndef _WIN32
#error Production render pipeline diagnostics require Win32
#endif
#include <windows.h>
#define COH_RP_TLS __declspec(thread)
static __inline const char *cohRpEnvironment(void) { return getenv("COH_CLIENT_RENDER_PIPELINE"); }
static __inline int cohRpPlatformInit(double *value) {
    LARGE_INTEGER ticks;
    if (!QueryPerformanceFrequency(&ticks) || ticks.QuadPart<=0) return 0;
    *value=(double)ticks.QuadPart; return 1;
}
static __inline int cohRpPlatformWall(double frequency,double *value) {
    LARGE_INTEGER ticks;
    if (!QueryPerformanceCounter(&ticks) || ticks.QuadPart<0) return 0;
    *value=(double)ticks.QuadPart*1000.0/frequency; return 1;
}
static __inline int cohRpPlatformCpu(double *value) {
    FILETIME creation,exit_time,kernel,user;
    ULARGE_INTEGER k,u;
    if (!GetThreadTimes(GetCurrentThread(),&creation,&exit_time,&kernel,&user)) return 0;
    k.LowPart=kernel.dwLowDateTime;k.HighPart=kernel.dwHighDateTime;
    u.LowPart=user.dwLowDateTime;u.HighPart=user.dwHighDateTime;
    *value=((double)k.QuadPart+(double)u.QuadPart)/10000.0; return 1;
}
static __inline void cohRpEmit(const char *line) { printf("%s\n",line);fflush(stdout); }
#endif
#ifdef COH_RP_IMPLEMENTATION
COH_RP_TLS CohRpStream coh_rp_stream;
#else
extern COH_RP_TLS CohRpStream coh_rp_stream;
#endif
static __inline int cohRpFinite(double value) { return value==value && value>=0.0 && value<1.0e12; }
static __inline unsigned int cohRpIncrement(unsigned int value) { return value<UINT_MAX?value+1:value; }
static __inline unsigned int cohRpSum(unsigned int a,unsigned int b) { return UINT_MAX-a<b?UINT_MAX:a+b; }
static __inline void cohRpDisable(void) {
    CohRpStream *s=&coh_rp_stream;
    s->enabled=0;s->frame_open=0;s->command_open=0;s->phase_open=0;s->suppress_depth=0;
}
static __inline int cohRpActive(int renderer) {
    CohRpStream *s=&coh_rp_stream;
    if (!s->initialized) {
        const char *flag=cohRpEnvironment();
        s->initialized=1;s->renderer=renderer;
        s->enabled=flag && strcmp(flag,"1")==0 && cohRpPlatformInit(&s->frequency);
    }
    return s->enabled && s->renderer==renderer;
}
static __inline int cohRpWall(double *value) {
    CohRpStream *s=&coh_rp_stream;
    if (!cohRpPlatformWall(s->frequency,value) || !cohRpFinite(*value)
        || (s->have_wall && *value<s->last_wall)) { cohRpDisable();return 0; }
    s->have_wall=1;s->last_wall=*value;return 1;
}
static __inline void cohRpAdd(CohRpMetricData *m,double value) {
    unsigned int i;
    if (!cohRpFinite(value) || m->count==UINT_MAX) return;
    for (i=0;i<COH_RP_BUCKETS-1 && value>coh_rp_bounds[i];++i) {}
    ++m->count;++m->histogram[i];m->sum+=value;
    if (value>m->maximum) m->maximum=value;
}
static __inline int cohRpAppend(char *line,size_t *length,const char *format,...) {
    va_list arguments;int written;size_t available=COH_RP_LINE_BYTES-*length;
    if (!available) return 0;
    va_start(arguments,format);written=vsnprintf(line+*length,available,format,arguments);va_end(arguments);
    if (written<0 || (size_t)written>=available) { line[COH_RP_LINE_BYTES-1]=0;return 0; }
    *length+=(size_t)written;return 1;
}
static __inline int cohRpAppendNumber(char *line,size_t *length,double value) {
    uint64_t micros;
    if (!cohRpFinite(value)) return 0;
    micros=(uint64_t)(value*1000.0+0.5);
    return cohRpAppend(line,length,"%llu.%03u",(unsigned long long)(micros/1000),
        (unsigned int)(micros%1000));
}
static __inline int cohRpQuantile(const CohRpMetricData *m,unsigned int percent) {
    uint64_t rank=((uint64_t)m->count*percent+99)/100,seen=0;unsigned int i;
    for (i=0;i<COH_RP_BUCKETS;++i) {
        seen+=m->histogram[i];
        if (seen>=rank) return i<COH_RP_BUCKETS-1?(int)coh_rp_bounds[i]:-1;
    }
    return -1;
}
static __inline int cohRpAppendMetric(char *line,size_t *length,const CohRpMetricData *m) {
    unsigned int i;int p95=cohRpQuantile(m,95);
    if (!cohRpAppend(line,length,"{\"count\":%u,\"mean_ms\":",m->count)
        || !cohRpAppendNumber(line,length,m->sum/m->count)
        || !cohRpAppend(line,length,",\"max_ms\":") || !cohRpAppendNumber(line,length,m->maximum)
        || !cohRpAppend(line,length,",\"p95_upper_ms\":")) return 0;
    if (p95<0) { if (!cohRpAppend(line,length,"null")) return 0; }
    else if (!cohRpAppend(line,length,"%d",p95)) return 0;
    if (!cohRpAppend(line,length,",\"histogram\":[")) return 0;
    for (i=0;i<COH_RP_BUCKETS;++i)
        if (!cohRpAppend(line,length,"%s%u",i?",":"",m->histogram[i])) return 0;
    return cohRpAppend(line,length,"]}");
}
static __inline void cohRpReport(double now) {
    CohRpStream *s=&coh_rp_stream;char line[COH_RP_LINE_BYTES];size_t length=0;
    unsigned int i;int ok,cpu_valid,written=0;double cpu=0.0;
    if (!s->enabled || !s->window_open || now-s->window_start<COH_RP_REPORT_MS) return;
    cpu_valid=cohRpPlatformCpu(&cpu) && cohRpFinite(cpu);
    ok=cohRpAppend(line,&length,"COH_CLIENT_RENDER_PIPELINE_V1 {\"format\":1,\"event\":\"window\",\"role\":\"%s\",\"scope\":\"%s\",\"report\":%u,\"window_ms\":",s->renderer?"renderer":"main",s->renderer?"all_states_independent":"gameplay",s->reports+1)
        && cohRpAppendNumber(line,&length,now-s->window_start)
        && cohRpAppend(line,&length,",\"thread_cpu_ms\":");
    if (cpu_valid && s->cpu_valid && cpu>=s->cpu_start)
        ok=ok && cohRpAppendNumber(line,&length,cpu-s->cpu_start);
    else ok=ok && cohRpAppend(line,&length,"null");
    ok=ok && cohRpAppend(line,&length,",\"incomplete_batches\":%u,",s->incomplete);
    if (s->renderer) ok=ok && cohRpAppend(line,&length,"\"sample_interval\":%u,\"sampled_batches\":%u,\"sampled_command_count\":%u,",COH_RP_SAMPLE_INTERVAL,s->sampled_batches,s->sampled_commands);
    ok=ok && cohRpAppend(line,&length,"\"bucket_upper_ms\":[");
    for (i=0;i<COH_RP_BUCKETS-1;++i) ok=ok && cohRpAppend(line,&length,"%s%u",i?",":"",coh_rp_bounds[i]);
    ok=ok && cohRpAppend(line,&length,",null],\"metrics\":{");
    for (i=0;i<COH_RP_METRICS;++i) if (s->metrics[i].count) {
        ok=ok && cohRpAppend(line,&length,"%s\"%s\":",written?",":"",coh_rp_names[i])
            && cohRpAppendMetric(line,&length,&s->metrics[i]);written=1;
    }
    ok=ok && cohRpAppend(line,&length,"}}");
    if (ok) cohRpEmit(line);
    ++s->reports;
    if (!ok || s->reports>=COH_RP_MAX_REPORTS) cohRpDisable();
    memset(s->metrics,0,sizeof(s->metrics));s->incomplete=s->sampled_batches=s->sampled_commands=0;
    s->window_start=now;s->cpu_start=cpu;s->cpu_valid=cpu_valid;
}
static __inline void cohRpBegin(int renderer) {
    CohRpStream *s=&coh_rp_stream;double now;
    if (!cohRpActive(renderer) || !cohRpWall(&now)) return;
    if (!s->window_open) {
        s->window_open=1;s->window_start=now;
        s->cpu_valid=cohRpPlatformCpu(&s->cpu_start) && cohRpFinite(s->cpu_start);
    }
    if (s->frame_open) s->incomplete=cohRpIncrement(s->incomplete);
    s->frame_open=1;s->frame_start=now;s->phase_open=0;
    s->command_open=0;s->command_wall=0;s->batch_commands=0;
    memset(s->phase_wall,0,sizeof(s->phase_wall));
    s->sampled=renderer && s->sample_cursor==0;
    if (renderer) s->sample_cursor=(s->sample_cursor+1)%COH_RP_SAMPLE_INTERVAL;
}
static __inline void cohRpMainBegin(int ordinary) {
    CohRpStream *s=&coh_rp_stream;
    /* Loading/nonordinary recursive gfx calls must not overwrite the outer
     * frame's phases. Their time remains inside the outer enclosing phase,
     * but their child hooks (including queue flushes) are ignored. */
    if (s->suppress_depth || !ordinary || (s->enabled && !s->renderer && s->frame_open)) {
        if (s->suppress_depth==UINT_MAX) cohRpDisable();
        else ++s->suppress_depth;
        return;
    }
    cohRpBegin(0);
}
static __inline void cohRpPhaseBegin(int metric) {
    CohRpStream *s=&coh_rp_stream;double now;
    if (!s->enabled || s->renderer || !s->frame_open || s->suppress_depth
        || metric<0 || metric>=COH_RP_PHASES) return;
    if (s->phase_open&(1u<<metric)) {cohRpDisable();return;}
    if (!cohRpWall(&now)) return;
    s->phase_start[metric]=now;s->phase_open|=1u<<metric;
}
static __inline void cohRpPhaseEnd(int metric) {
    CohRpStream *s=&coh_rp_stream;double now;
    if (!s->enabled || s->renderer || !s->frame_open || s->suppress_depth
        || metric<0 || metric>=COH_RP_PHASES
        || !(s->phase_open&(1u<<metric)) || !cohRpWall(&now)) return;
    s->phase_wall[metric]+=now-s->phase_start[metric];s->phase_open&=~(1u<<metric);
}
static __inline void cohRpCommandBegin(int command) {
    CohRpStream *s=&coh_rp_stream;double now;
    if (!s->enabled || !s->renderer || !s->frame_open || !s->sampled) return;
    if (s->command_open) {cohRpDisable();return;}
    if (!cohRpWall(&now)) return;
    s->command_open=1;s->command=command;s->command_start=now;
}
static __inline void cohRpCommandEnd(int command) {
    CohRpStream *s=&coh_rp_stream;double now;
    if (!s->enabled || !s->renderer || !s->frame_open || !s->sampled) return;
    if (!s->command_open || s->command!=command) {cohRpDisable();return;}
    if (!cohRpWall(&now)) return;
    s->command_wall+=now-s->command_start;s->command_open=0;
    s->batch_commands=cohRpIncrement(s->batch_commands);
}
static __inline void cohRpEnd(int renderer) {
    CohRpStream *s=&coh_rp_stream;double now,total,gap;unsigned int i;
    if (!cohRpActive(renderer) || !s->frame_open || !cohRpWall(&now)) return;
    if (s->phase_open || s->command_open) {cohRpDisable();return;}
    total=now-s->frame_start;
    if (renderer) {
        cohRpAdd(&s->metrics[COH_RP_BATCH],total);
        if (s->sampled) {
            gap=total-s->command_wall;
            if (gap < -0.000001) {cohRpDisable();return;}
            if (gap<0) gap=0;
            cohRpAdd(&s->metrics[COH_RP_COMMAND],s->command_wall);
            cohRpAdd(&s->metrics[COH_RP_GAP],gap);
            s->sampled_batches=cohRpIncrement(s->sampled_batches);
            s->sampled_commands=cohRpSum(s->sampled_commands,s->batch_commands);
        }
    } else {
        cohRpAdd(&s->metrics[COH_RP_GFX],total);
        for (i=0;i<COH_RP_PHASES;++i) cohRpAdd(&s->metrics[i],s->phase_wall[i]);
    }
    s->frame_open=0;cohRpReport(now);
}
static __inline void cohRpMainEnd(int ordinary) {
    CohRpStream *s=&coh_rp_stream;
    if (s->suppress_depth) {--s->suppress_depth;return;}
    if (ordinary) cohRpEnd(0);
}
static __inline void cohRpRendererBegin(void) { cohRpBegin(1); }
static __inline void cohRpRendererEnd(void) { cohRpEnd(1); }
#pragma pop_macro("FILE")
#pragma pop_macro("fflush")
#pragma pop_macro("vsnprintf")
#pragma pop_macro("printf")
#endif
