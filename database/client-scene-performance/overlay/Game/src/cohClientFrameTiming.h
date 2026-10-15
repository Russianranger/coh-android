/* Opt-in, bounded wall-frame diagnostics. No rendering or pacing policy changes.
 * A translation unit owns one thread-local stream: game.c owns main, and
 * rt_win_init.c owns presentation. There is no shared mutable cross-thread state.
 * Interval and SwapBuffers measurements are wall time, NOT GPU completion or
 * Android/RFB display latency. Thread CPU excludes other renderer/Wine workers.
 */
#ifndef COH_CLIENT_FRAME_TIMING_H
#define COH_CLIENT_FRAME_TIMING_H
/* Retained stdtypes/file headers remap these CRT names. The formatter accepts
 * a bounded pointer+length, not an array, and the single-line emitter uses the
 * real CRT stdout. Restore every macro before returning to native callers.
 */
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

#define COH_FT_REPORT_MS 10000.0
#define COH_FT_MAX_REPORTS 120u
#define COH_FT_BUCKETS 22
#define COH_FT_STATES 4
#define COH_FT_METRICS 9
#define COH_FT_LINE_BYTES 12288

enum CohFtState { COH_FT_MENU, COH_FT_LOADING, COH_FT_GAMEPLAY, COH_FT_MIXED };
enum CohFtMetric { COH_FT_INTERVAL, COH_FT_FRAME, COH_FT_ENGINE,
    COH_FT_SUBMIT, COH_FT_PACING, COH_FT_WORK, COH_FT_PRESENT_INTERVAL,
    COH_FT_PRESENT, COH_FT_SWAP };
enum CohFtPhase { COH_FT_ENGINE_PHASE, COH_FT_SUBMIT_PHASE, COH_FT_PACING_PHASE };

/* The last bucket is overflow; its quantile upper bound is JSON null. */
static const unsigned int coh_ft_bounds[COH_FT_BUCKETS-1] = {
    16,33,50,66,83,100,110,125,150,200,250,333,500,750,1000,2000,5000,
    10000,30000,60000,120000
};
static const char *const coh_ft_states[COH_FT_STATES] = {
    "menu", "loading", "gameplay", "mixed"
};
static const char *const coh_ft_metrics[COH_FT_METRICS] = {
    "frame_interval", "frame_wall", "engine_wall", "submit_wall", "pacing_wall",
    "work_wall", "presentation_interval", "present_wall", "swap_wall"
};
typedef struct CohFtMetricData {
    unsigned int count, over125, over200, histogram[COH_FT_BUCKETS];
    double sum, maximum;
} CohFtMetricData;
typedef struct CohFtStream {
    int initialized, enabled, presentation, frame_open, previous_state;
    unsigned int reports;
    double frequency, window_start, cpu_start, previous_begin, frame_begin;
    int cpu_valid, have_previous, state;
    double phase_begin[3], phase_wall[3], swap_begin, swap_wall;
    unsigned int phase_open;
    CohFtMetricData data[COH_FT_STATES][COH_FT_METRICS];
} CohFtStream;

#ifdef COH_FRAME_TIMING_TEST
/* Deterministic tests exercise this exact aggregation and emission code. */
#ifdef _WIN32
#define COH_FT_TLS __declspec(thread)
#else
#define COH_FT_TLS _Thread_local
#endif
static __inline const char *cohFtEnvironment(void) { return cohFtTestEnvironment(); }
static __inline int cohFtPlatformInit(double *frequency) { *frequency=1.0; return 1; }
static __inline int cohFtPlatformWall(double frequency, double *value) {
    (void)frequency; return cohFtTestWall(value);
}
static __inline int cohFtPlatformCpu(double *value) { return cohFtTestCpu(value); }
static __inline void cohFtEmit(const char *line) { cohFtTestEmit(line); }
#else
#ifndef _WIN32
#error Production frame diagnostics require the retained Win32 Game runtime
#endif
#include <windows.h>
#define COH_FT_TLS __declspec(thread)
static __inline const char *cohFtEnvironment(void) { return getenv("COH_CLIENT_FRAME_TIMING"); }
static __inline int cohFtPlatformInit(double *frequency) {
    LARGE_INTEGER value;
    if (!QueryPerformanceFrequency(&value) || value.QuadPart <= 0) return 0;
    *frequency=(double)value.QuadPart; return 1;
}
static __inline int cohFtPlatformWall(double frequency, double *value) {
    LARGE_INTEGER ticks;
    if (!QueryPerformanceCounter(&ticks) || ticks.QuadPart < 0) return 0;
    *value=(double)ticks.QuadPart * 1000.0 / frequency; return 1;
}
static __inline int cohFtPlatformCpu(double *value) {
    FILETIME creation, exit_time, kernel, user;
    ULARGE_INTEGER kernel_ticks, user_ticks;
    if (!GetThreadTimes(GetCurrentThread(), &creation, &exit_time, &kernel, &user)) return 0;
    kernel_ticks.LowPart=kernel.dwLowDateTime; kernel_ticks.HighPart=kernel.dwHighDateTime;
    user_ticks.LowPart=user.dwLowDateTime; user_ticks.HighPart=user.dwHighDateTime;
    *value=((double)kernel_ticks.QuadPart+(double)user_ticks.QuadPart) / 10000.0;
    return 1;
}
static __inline void cohFtEmit(const char *line) {
    /* One bounded stdio write/flush per report, never one per frame. */
    printf("%s\n", line); fflush(stdout);
}
#endif

static COH_FT_TLS CohFtStream coh_ft_stream;

static __inline int cohFtActive(int presentation) {
    CohFtStream *s=&coh_ft_stream;
    if (!s->initialized) {
        const char *flag=cohFtEnvironment();
        s->initialized=1; s->presentation=presentation;
        s->enabled=flag && strcmp(flag,"1")==0 && cohFtPlatformInit(&s->frequency);
    }
    return s->enabled && s->presentation==presentation && s->reports<COH_FT_MAX_REPORTS;
}
static __inline int cohFtWall(double *now) {
    CohFtStream *s=&coh_ft_stream;
    if (!cohFtPlatformWall(s->frequency,now)) { s->enabled=0; return 0; }
    return 1;
}
static __inline void cohFtAdd(CohFtMetricData *m,double value) {
    unsigned int bucket=0;
    if (value < 0.0) return;
    while (bucket < COH_FT_BUCKETS-1 && value > coh_ft_bounds[bucket]) bucket++;
    m->count++; m->sum+=value; if (value > m->maximum) m->maximum=value;
    m->histogram[bucket]++; m->over125+=(value>125.0); m->over200+=(value>200.0);
}
static __inline int cohFtQuantile(const CohFtMetricData *m,unsigned int percent) {
    unsigned int i;
    uint64_t seen=0,rank=((uint64_t)m->count*percent+99)/100;
    if (!m->count) return -1;
    for (i=0;i<COH_FT_BUCKETS;i++) {
        seen+=m->histogram[i];
        if (seen>=rank) return i<COH_FT_BUCKETS-1 ? (int)coh_ft_bounds[i] : -1;
    }
    return -1;
}
static __inline int cohFtAppend(char *line,size_t *length,const char *format,...) {
    int written;
    va_list arguments;
    size_t available=COH_FT_LINE_BYTES-*length;
    if (!available) return 0;
    va_start(arguments,format); written=vsnprintf(line+*length,available,format,arguments);
    va_end(arguments);
    if (written<0 || (size_t)written>=available) { line[COH_FT_LINE_BYTES-1]=0; return 0; }
    *length+=(size_t)written; return 1;
}
static __inline int cohFtAppendMs(char *line,size_t *length,double value) {
    /* Explicit decimal point, independent of the process numeric locale. */
    uint64_t micros=(uint64_t)(value*1000.0+0.5);
    return cohFtAppend(line,length,"%llu.%03u",(unsigned long long)(micros/1000),
        (unsigned int)(micros%1000));
}
static __inline int cohFtAppendMetric(char *line,size_t *length,const CohFtMetricData *m) {
    unsigned int i;
    int p50=cohFtQuantile(m,50),p95=cohFtQuantile(m,95);
    if (!cohFtAppend(line,length,"{\"count\":%u,\"mean_ms\":",m->count)
        || !cohFtAppendMs(line,length,m->sum/m->count)
        || !cohFtAppend(line,length,",\"max_ms\":")
        || !cohFtAppendMs(line,length,m->maximum)
        || !cohFtAppend(line,length,",\"p50_upper_ms\":")) return 0;
    if (p50<0) { if (!cohFtAppend(line,length,"null")) return 0; }
    else if (!cohFtAppend(line,length,"%d",p50)) return 0;
    if (!cohFtAppend(line,length,",\"p95_upper_ms\":")) return 0;
    if (p95<0) { if (!cohFtAppend(line,length,"null")) return 0; }
    else if (!cohFtAppend(line,length,"%d",p95)) return 0;
    if (!cohFtAppend(line,length,",\"over_125ms_count\":%u,\"over_200ms_count\":%u,\"histogram\":[",
        m->over125,m->over200)) return 0;
    for (i=0;i<COH_FT_BUCKETS;i++)
        if (!cohFtAppend(line,length,"%s%u",i?",":"",m->histogram[i])) return 0;
    return cohFtAppend(line,length,"]}");
}
static __inline void cohFtReport(double now) {
    CohFtStream *s=&coh_ft_stream;
    char line[COH_FT_LINE_BYTES];
    size_t length=0;
    unsigned int state,metric,i;
    int state_written=0,ok=1,cpu_valid;
    double cpu_now=0.0;
    if (now-s->window_start<COH_FT_REPORT_MS) return;
    /* CPU query at boundaries only; never in frame/phase clocks. */
    cpu_valid=cohFtPlatformCpu(&cpu_now);
    ok=cohFtAppend(line,&length,"COH_CLIENT_FRAME_TIMING_V1 {\"role\":\"%s\",\"report\":%u,\"window_ms\":",
        s->presentation?"presentation":"main",s->reports+1)
        && cohFtAppendMs(line,&length,now-s->window_start)
        && cohFtAppend(line,&length,",\"thread_cpu_ms\":");
    if (cpu_valid && s->cpu_valid && cpu_now>=s->cpu_start)
        ok=ok && cohFtAppendMs(line,&length,cpu_now-s->cpu_start);
    else ok=ok && cohFtAppend(line,&length,"null");
    ok=ok && cohFtAppend(line,&length,",\"histogram_upper_ms\":[");
    for (i=0;i<COH_FT_BUCKETS-1;i++)
        ok=ok && cohFtAppend(line,&length,"%s%u",i?",":"",coh_ft_bounds[i]);
    ok=ok && cohFtAppend(line,&length,",null],\"states\":{");
    for (state=0;state<COH_FT_STATES;state++) {
        int metric_written=0,any=0;
        for (metric=0;metric<COH_FT_METRICS;metric++) any|=(s->data[state][metric].count!=0);
        if (!any) continue;
        ok=ok && cohFtAppend(line,&length,"%s\"%s\":{",state_written?",":"",
            s->presentation?"unclassified":coh_ft_states[state]);
        state_written=1;
        for (metric=0;metric<COH_FT_METRICS;metric++) {
            const CohFtMetricData *m=&s->data[state][metric];
            if (!m->count) continue;
            ok=ok && cohFtAppend(line,&length,"%s\"%s\":",metric_written?",":"",coh_ft_metrics[metric])
                && cohFtAppendMetric(line,&length,m);
            metric_written=1;
        }
        ok=ok && cohFtAppend(line,&length,"}");
    }
    ok=ok && cohFtAppend(line,&length,"}}");
    if (ok) cohFtEmit(line);
    /* Exhaustion or formatting failure stops diagnostics, never the game. */
    s->reports++; if (!ok || s->reports==COH_FT_MAX_REPORTS) s->enabled=0;
    memset(s->data,0,sizeof(s->data));
    s->window_start=now; s->cpu_start=cpu_now; s->cpu_valid=cpu_valid;
}
static __inline void cohFtBegin(int presentation,int state) {
    CohFtStream *s=&coh_ft_stream;
    double now;
    if (!cohFtActive(presentation) || !cohFtWall(&now)) return;
    if (!s->have_previous) {
        s->window_start=now; s->cpu_valid=cohFtPlatformCpu(&s->cpu_start);
    } else if (now<s->previous_begin) { s->enabled=0; return; }
    else cohFtAdd(&s->data[s->previous_state][presentation?COH_FT_PRESENT_INTERVAL:COH_FT_INTERVAL],
        now-s->previous_begin);
    s->have_previous=1; s->previous_begin=now; s->frame_begin=now;
    s->state=state; s->previous_state=state; s->frame_open=1;
    memset(s->phase_wall,0,sizeof(s->phase_wall)); s->phase_open=0; s->swap_wall=0.0;
}
static __inline void cohFtMainBegin(int state) { cohFtBegin(0,state); }
static __inline void cohFtPhaseBegin(int phase) {
    CohFtStream *s=&coh_ft_stream;
    double now;
    if (!cohFtActive(0) || !s->frame_open || !cohFtWall(&now)) return;
    s->phase_begin[phase]=now; s->phase_open|=(1u<<phase);
}
static __inline void cohFtPhaseEnd(int phase) {
    CohFtStream *s=&coh_ft_stream;
    double now;
    if (!cohFtActive(0) || !s->frame_open || !(s->phase_open&(1u<<phase)) || !cohFtWall(&now)) return;
    if (now<s->phase_begin[phase]) { s->enabled=0; return; }
    s->phase_wall[phase]+=now-s->phase_begin[phase]; s->phase_open&=~(1u<<phase);
}
static __inline void cohFtMainEnd(int end_state) {
    CohFtStream *s=&coh_ft_stream;
    CohFtMetricData *m;
    int state;
    double now,frame;
    if (!cohFtActive(0) || !s->frame_open || !cohFtWall(&now)) return;
    if (now<s->frame_begin) { s->enabled=0; return; }
    state=s->state==end_state ? s->state : COH_FT_MIXED;
    m=s->data[state]; frame=now-s->frame_begin;
    cohFtAdd(&m[COH_FT_FRAME],frame);
    cohFtAdd(&m[COH_FT_ENGINE],s->phase_wall[COH_FT_ENGINE_PHASE]);
    cohFtAdd(&m[COH_FT_SUBMIT],s->phase_wall[COH_FT_SUBMIT_PHASE]);
    cohFtAdd(&m[COH_FT_PACING],s->phase_wall[COH_FT_PACING_PHASE]);
    cohFtAdd(&m[COH_FT_WORK],frame-s->phase_wall[COH_FT_PACING_PHASE]);
    s->previous_state=state; s->frame_open=0; cohFtReport(now);
}
static __inline void cohFtPresentBegin(void) { cohFtBegin(1,COH_FT_MENU); }
static __inline void cohFtSwapBegin(void) {
    CohFtStream *s=&coh_ft_stream;
    if (cohFtActive(1) && s->frame_open) cohFtWall(&s->swap_begin);
}
static __inline void cohFtSwapEnd(void) {
    CohFtStream *s=&coh_ft_stream;
    double now;
    if (!cohFtActive(1) || !s->frame_open || !cohFtWall(&now)) return;
    if (now<s->swap_begin) { s->enabled=0; return; }
    s->swap_wall+=now-s->swap_begin;
}
static __inline void cohFtPresentEnd(void) {
    CohFtStream *s=&coh_ft_stream;
    double now;
    if (!cohFtActive(1) || !s->frame_open || !cohFtWall(&now)) return;
    if (now<s->frame_begin) { s->enabled=0; return; }
    cohFtAdd(&s->data[COH_FT_MENU][COH_FT_PRESENT],now-s->frame_begin);
    cohFtAdd(&s->data[COH_FT_MENU][COH_FT_SWAP],s->swap_wall);
    s->frame_open=0; cohFtReport(now);
}
#pragma pop_macro("FILE")
#pragma pop_macro("fflush")
#pragma pop_macro("vsnprintf")
#pragma pop_macro("printf")
#endif
