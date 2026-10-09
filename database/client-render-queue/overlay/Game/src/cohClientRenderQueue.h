/* Main-thread observations for the exact render-worker continuation. Clocks
 * run on one gameplay frame in 32, never per render command. Worker counters
 * belong to the producer; the caller supplies their cumulative snapshot.
 * These wall clocks include driver/synchronization work and are not GPU time.
 */
#ifndef COH_CLIENT_RENDER_QUEUE_H
#define COH_CLIENT_RENDER_QUEUE_H
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

#define COH_RQ_REPORT_MS 10000.0
#define COH_RQ_MAX_REPORTS 120u
#define COH_RQ_SAMPLE_INTERVAL 32u
#define COH_RQ_BUCKETS 22
#define COH_RQ_PHASES 3
#define COH_RQ_LINE_BYTES 8192
#define COH_RQ_CLOCK_LIMIT 1.0e12
enum CohRqPhase { COH_RQ_SETUP, COH_RQ_SORT, COH_RQ_DRAW };
static const unsigned int coh_rq_bounds[COH_RQ_BUCKETS-1] = {
    16,33,50,66,83,100,110,125,150,200,250,333,500,750,1000,2000,5000,
    10000,30000,60000,120000
};
static const char *const coh_rq_names[COH_RQ_PHASES] = {
    "setup_wall", "sort_wall", "draw_wall"
};
typedef struct CohRqQueueSnapshot {
    uint64_t commands, armed_observations, wake_signals, wake_signal_failures;
    uint64_t pending_commands, ring_waits, ring_wait_iterations, ring_wait_clock_failures;
    double ring_wait_wall_ms, ring_wait_max_ms;
} CohRqQueueSnapshot;
typedef struct CohRqMetricData {
    unsigned int count, histogram[COH_RQ_BUCKETS];
    double sum, maximum;
} CohRqMetricData;
typedef struct CohRqStream {
    int initialized, enabled, frame_open, sampled, frame_invalid, window_open, have_wall;
    int have_snapshot;
    unsigned int reports, sample_cursor, suppress_depth, phase_open;
    unsigned int gameplay_frames, sampled_frames, incomplete_frames;
    double frequency, window_start, last_wall;
    double phase_start[COH_RQ_PHASES], phase_wall[COH_RQ_PHASES];
    CohRqMetricData metrics[COH_RQ_PHASES];
    CohRqQueueSnapshot last_snapshot;
} CohRqStream;
#ifdef COH_RENDER_QUEUE_TEST
#ifdef _WIN32
#define COH_RQ_TLS __declspec(thread)
#else
#define COH_RQ_TLS _Thread_local
#endif
static __inline const char *cohRqEnvironment(void) { return cohRqTestEnvironment(); }
static __inline int cohRqPlatformInit(double *value) { *value=1.0;return 1; }
static __inline int cohRqPlatformWall(double frequency,double *value) {
    (void)frequency;return cohRqTestWall(value);
}
static __inline void cohRqEmit(const char *line) { cohRqTestEmit(line); }
#else
#ifndef _WIN32
#error Production render queue diagnostics require Win32
#endif
#include <windows.h>
#define COH_RQ_TLS __declspec(thread)
static __inline const char *cohRqEnvironment(void) { return getenv("COH_CLIENT_RENDER_QUEUE"); }
static __inline int cohRqPlatformInit(double *value) {
    LARGE_INTEGER ticks;
    if (!QueryPerformanceFrequency(&ticks) || ticks.QuadPart<=0) return 0;
    *value=(double)ticks.QuadPart;return 1;
}
static __inline int cohRqPlatformWall(double frequency,double *value) {
    LARGE_INTEGER ticks;
    if (!QueryPerformanceCounter(&ticks) || ticks.QuadPart<0) return 0;
    *value=(double)ticks.QuadPart*1000.0/frequency;return 1;
}
static __inline void cohRqEmit(const char *line) { printf("%s\n",line);fflush(stdout); }
#endif
#ifdef COH_RQ_IMPLEMENTATION
COH_RQ_TLS CohRqStream coh_rq_stream;
#else
extern COH_RQ_TLS CohRqStream coh_rq_stream;
#endif
static __inline int cohRqFinite(double value) {
    return value==value && value>=0.0 && value<=COH_RQ_CLOCK_LIMIT;
}
static __inline void cohRqDisable(void) {
    CohRqStream *s=&coh_rq_stream;
    s->enabled=0;s->frame_open=0;s->sampled=0;s->phase_open=0;s->suppress_depth=0;
}
static __inline int cohRqEnabled(void) {
    CohRqStream *s=&coh_rq_stream;
    if (!s->initialized) {
        const char *flag=cohRqEnvironment();
        s->initialized=1;
        s->enabled=flag && strcmp(flag,"1")==0 && cohRqPlatformInit(&s->frequency)
            && cohRqFinite(s->frequency) && s->frequency>0.0;
    }
    return s->enabled;
}
static __inline int cohRqWall(double *value) {
    CohRqStream *s=&coh_rq_stream;
    if (!cohRqPlatformWall(s->frequency,value) || !cohRqFinite(*value)
        || (s->have_wall && *value<s->last_wall)) {cohRqDisable();return 0;}
    s->have_wall=1;s->last_wall=*value;return 1;
}
static __inline int cohRqIncrement(unsigned int *value) {
    if (*value==UINT_MAX) {cohRqDisable();return 0;}
    ++*value;return 1;
}
static __inline int cohRqAdd(CohRqMetricData *metric,double value) {
    unsigned int i;
    if (!cohRqFinite(value) || metric->count==UINT_MAX
        || !cohRqFinite(metric->sum+value)) {cohRqDisable();return 0;}
    for (i=0;i<COH_RQ_BUCKETS-1 && value>coh_rq_bounds[i];++i) {}
    ++metric->count;++metric->histogram[i];metric->sum+=value;
    if (value>metric->maximum) metric->maximum=value;
    return 1;
}
static __inline int cohRqAppend(char *line,size_t *length,const char *format,...) {
    va_list arguments;int written;size_t available=COH_RQ_LINE_BYTES-*length;
    if (!available) return 0;
    va_start(arguments,format);written=vsnprintf(line+*length,available,format,arguments);va_end(arguments);
    if (written<0 || (size_t)written>=available) {line[COH_RQ_LINE_BYTES-1]=0;return 0;}
    *length+=(size_t)written;return 1;
}
static __inline int cohRqAppendNumber(char *line,size_t *length,double value) {
    uint64_t micros;
    if (!cohRqFinite(value)) return 0;
    micros=(uint64_t)(value*1000.0+0.5);
    return cohRqAppend(line,length,"%llu.%03u",(unsigned long long)(micros/1000),
        (unsigned int)(micros%1000));
}
static __inline int cohRqQuantile(const CohRqMetricData *metric,unsigned int percent) {
    uint64_t rank=((uint64_t)metric->count*percent+99)/100,seen=0;unsigned int i;
    for (i=0;i<COH_RQ_BUCKETS;++i) {
        seen+=metric->histogram[i];
        if (seen>=rank) return i<COH_RQ_BUCKETS-1?(int)coh_rq_bounds[i]:-1;
    }
    return -1;
}
static __inline int cohRqAppendMetric(char *line,size_t *length,const CohRqMetricData *metric) {
    unsigned int i;int p95=cohRqQuantile(metric,95);
    if (!metric->count || !cohRqAppend(line,length,"{\"count\":%u,\"mean_ms\":",metric->count)
        || !cohRqAppendNumber(line,length,metric->sum/metric->count)
        || !cohRqAppend(line,length,",\"max_ms\":") || !cohRqAppendNumber(line,length,metric->maximum)
        || !cohRqAppend(line,length,",\"p95_upper_ms\":")) return 0;
    if (p95<0) {if (!cohRqAppend(line,length,"null")) return 0;}
    else if (!cohRqAppend(line,length,"%d",p95)) return 0;
    if (!cohRqAppend(line,length,",\"histogram\":[")) return 0;
    for (i=0;i<COH_RQ_BUCKETS;++i)
        if (!cohRqAppend(line,length,"%s%u",i?",":"",metric->histogram[i])) return 0;
    return cohRqAppend(line,length,"]}");
}
static __inline int cohRqSnapshotSaturated(const CohRqQueueSnapshot *q) {
    return q->commands==UINT64_MAX || q->armed_observations==UINT64_MAX
        || q->wake_signals==UINT64_MAX || q->wake_signal_failures==UINT64_MAX
        || q->pending_commands==UINT64_MAX || q->ring_waits==UINT64_MAX
        || q->ring_wait_iterations==UINT64_MAX || q->ring_wait_clock_failures==UINT64_MAX;
}
static __inline int cohRqSnapshotValid(const CohRqQueueSnapshot *q) {
    CohRqStream *s=&coh_rq_stream;const CohRqQueueSnapshot *p=&s->last_snapshot;
    if (!q || !cohRqFinite(q->ring_wait_wall_ms) || !cohRqFinite(q->ring_wait_max_ms)
        || q->ring_wait_max_ms>q->ring_wait_wall_ms) return 0;
    if (q->armed_observations>q->commands
        || q->pending_commands>q->commands || q->wake_signals>q->armed_observations
        || q->wake_signal_failures>q->armed_observations
        || (q->armed_observations!=UINT64_MAX
            && q->wake_signal_failures>q->armed_observations-q->wake_signals)
        || q->ring_waits>q->ring_wait_iterations || q->ring_wait_clock_failures>q->ring_waits) return 0;
    if (s->have_snapshot && (q->commands<p->commands || q->armed_observations<p->armed_observations
        || q->wake_signals<p->wake_signals || q->wake_signal_failures<p->wake_signal_failures
        || q->pending_commands<p->pending_commands || q->ring_waits<p->ring_waits
        || q->ring_wait_iterations<p->ring_wait_iterations
        || q->ring_wait_clock_failures<p->ring_wait_clock_failures
        || q->ring_wait_wall_ms<p->ring_wait_wall_ms || q->ring_wait_max_ms<p->ring_wait_max_ms)) return 0;
    return 1;
}
static __inline int cohRqAppendSnapshot(char *line,size_t *length,const CohRqQueueSnapshot *q) {
    return cohRqAppend(line,length,"\"queue_counters_saturated\":%s,\"queue_counters\":{"
        "\"commands\":%llu,\"armed_observations\":%llu,\"wake_signals\":%llu,"
        "\"wake_signal_failures\":%llu,\"pending_commands\":%llu,\"ring_waits\":%llu,"
        "\"ring_wait_iterations\":%llu,\"ring_wait_clock_failures\":%llu,\"ring_wait_wall_ms\":",
        cohRqSnapshotSaturated(q)?"true":"false",(unsigned long long)q->commands,
        (unsigned long long)q->armed_observations,(unsigned long long)q->wake_signals,
        (unsigned long long)q->wake_signal_failures,(unsigned long long)q->pending_commands,
        (unsigned long long)q->ring_waits,(unsigned long long)q->ring_wait_iterations,
        (unsigned long long)q->ring_wait_clock_failures)
        && cohRqAppendNumber(line,length,q->ring_wait_wall_ms)
        && cohRqAppend(line,length,",\"ring_wait_max_ms\":")
        && cohRqAppendNumber(line,length,q->ring_wait_max_ms) && cohRqAppend(line,length,"},");
}
static __inline void cohRqReport(double now,const CohRqQueueSnapshot *snapshot) {
    CohRqStream *s=&coh_rq_stream;char line[COH_RQ_LINE_BYTES];size_t length=0;
    unsigned int i;int ok;
    if (!s->enabled || !s->window_open || now-s->window_start<COH_RQ_REPORT_MS) return;
    if (!cohRqSnapshotValid(snapshot)) {cohRqDisable();return;}
    ok=cohRqAppend(line,&length,"COH_CLIENT_RENDER_QUEUE_V1 {\"format\":1,\"event\":\"window\","
        "\"scope\":\"gameplay\",\"queue_scope\":\"process_cumulative\",\"report\":%u,\"window_ms\":",s->reports+1)
        && cohRqAppendNumber(line,&length,now-s->window_start)
        && cohRqAppend(line,&length,",\"sample_interval\":%u,\"gameplay_frames\":%u,"
            "\"sampled_frames\":%u,\"incomplete_frames\":%u,",COH_RQ_SAMPLE_INTERVAL,
            s->gameplay_frames,s->sampled_frames,s->incomplete_frames)
        && cohRqAppendSnapshot(line,&length,snapshot)
        && cohRqAppend(line,&length,"\"bucket_upper_ms\":[");
    for (i=0;i<COH_RQ_BUCKETS-1;++i) ok=ok && cohRqAppend(line,&length,"%s%u",i?",":"",coh_rq_bounds[i]);
    ok=ok && cohRqAppend(line,&length,",null],\"metrics\":{");
    if (s->sampled_frames) for (i=0;i<COH_RQ_PHASES;++i)
        ok=ok && cohRqAppend(line,&length,"%s\"%s\":",i?",":"",coh_rq_names[i])
            && cohRqAppendMetric(line,&length,&s->metrics[i]);
    ok=ok && cohRqAppend(line,&length,"}}");
    if (!ok) {cohRqDisable();return;}
    cohRqEmit(line);++s->reports;s->last_snapshot=*snapshot;s->have_snapshot=1;
    memset(s->metrics,0,sizeof(s->metrics));
    s->gameplay_frames=s->sampled_frames=s->incomplete_frames=0;s->window_start=now;
    if (s->reports>=COH_RQ_MAX_REPORTS) cohRqDisable();
}
static __inline void cohRqMainBegin(int ordinary) {
    CohRqStream *s=&coh_rq_stream;double now;
    if (s->suppress_depth || !ordinary || s->frame_open) {
        if (s->suppress_depth==UINT_MAX) cohRqDisable();
        else ++s->suppress_depth;
        return;
    }
    if (!cohRqEnabled()) return;
    s->sampled=s->sample_cursor==0;
    s->sample_cursor=(s->sample_cursor+1)%COH_RQ_SAMPLE_INTERVAL;
    s->frame_open=1;s->frame_invalid=0;s->phase_open=0;
    if (!s->sampled) return;
    memset(s->phase_wall,0,sizeof(s->phase_wall));
    if (!cohRqWall(&now)) return;
    if (!s->window_open) {s->window_open=1;s->window_start=now;}
}
static __inline void cohRqPhaseBegin(int phase) {
    CohRqStream *s=&coh_rq_stream;double now;
    if (!s->enabled || !s->frame_open || !s->sampled || s->suppress_depth || s->frame_invalid) return;
    if (phase<0 || phase>=COH_RQ_PHASES || s->phase_open) {s->frame_invalid=1;return;}
    if (!cohRqWall(&now)) return;
    s->phase_start[phase]=now;s->phase_open=1u<<phase;
}
static __inline void cohRqPhaseEnd(int phase) {
    CohRqStream *s=&coh_rq_stream;double now;
    if (!s->enabled || !s->frame_open || !s->sampled || s->suppress_depth || s->frame_invalid) return;
    if (phase<0 || phase>=COH_RQ_PHASES || s->phase_open!=(1u<<phase)) {s->frame_invalid=1;return;}
    if (!cohRqWall(&now)) return;
    s->phase_wall[phase]+=now-s->phase_start[phase];s->phase_open=0;
    if (!cohRqFinite(s->phase_wall[phase])) cohRqDisable();
}
static __inline void cohRqMainEnd(int ordinary,const CohRqQueueSnapshot *snapshot) {
    CohRqStream *s=&coh_rq_stream;double now;unsigned int i;
    if (s->suppress_depth) {--s->suppress_depth;return;}
    if (!ordinary || !s->enabled || !s->frame_open) return;
    s->frame_open=0;
    if (!s->sampled) {cohRqIncrement(&s->gameplay_frames);return;}
    if (!cohRqWall(&now)) return;
    if (s->frame_invalid || s->phase_open) {
        s->phase_open=0;if (!cohRqIncrement(&s->incomplete_frames)) return;
    } else {
        if (!cohRqIncrement(&s->gameplay_frames) || !cohRqIncrement(&s->sampled_frames)) return;
        for (i=0;i<COH_RQ_PHASES;++i) if (!cohRqAdd(&s->metrics[i],s->phase_wall[i])) return;
    }
    cohRqReport(now,snapshot);
}
#pragma pop_macro("FILE")
#pragma pop_macro("fflush")
#pragma pop_macro("vsnprintf")
#pragma pop_macro("printf")
#endif
