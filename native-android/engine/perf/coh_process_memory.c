#define _POSIX_C_SOURCE 200809L
#include "coh_process_memory.h"
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#if defined(__linux__) || defined(__ANDROID__)
#include <fcntl.h>
#include <unistd.h>
#endif

static CohProcessMemorySnapshot unknown(CohStatus status, int error) {
    CohProcessMemorySnapshot s = {0};
    s.rss.status = s.pss.status = s.rollup_status = s.status_file_status = status;
    s.rss.system_error = s.pss.system_error = s.rollup_errno = s.status_file_errno = error;
    return s;
}
static int space(char c) { return c == ' ' || c == '\t' || c == '\r'; }
static CohStatus number(const char *p, const char *end, uint64_t *bytes) {
    while (p < end && space(*p)) p++;
    if (p == end || *p < '0' || *p > '9') return COH_INVALID;
    uint64_t value = 0;
    while (p < end && *p >= '0' && *p <= '9') {
        unsigned digit = (unsigned)(*p++ - '0');
        if (value > (UINT64_MAX - digit) / 10) return COH_LIMIT;
        value = value * 10 + digit;
    }
    if (p == end || !space(*p)) return COH_INVALID;
    while (p < end && space(*p)) p++;
    if (end - p < 2 || p[0] != 'k' || p[1] != 'B') return COH_INVALID;
    p += 2;
    while (p < end && space(*p)) p++;
    if (p != end) return COH_INVALID;
    if (value > UINT64_MAX / 1024) return COH_LIMIT;
    *bytes = value * 1024;
    return COH_OK;
}
CohStatus coh_process_memory_parse(CohProcessMemorySource source, const char *text,
                                  size_t size, CohProcessMemorySnapshot *out) {
    if (!out || !text || (source != COH_PROCESS_MEMORY_SMAPS_ROLLUP &&
                         source != COH_PROCESS_MEMORY_STATUS)) return COH_INVALID;
    if (size > COH_PROCESS_MEMORY_TEXT_LIMIT) return COH_LIMIT;
    if (memchr(text, 0, size)) return COH_INVALID;
    CohProcessMemorySnapshot result = unknown(COH_NOT_FOUND, 0);
    const char *p = text, *end = text + size;
    unsigned found = 0;
    while (p < end) {
        const char *line = p, *newline = memchr(p, '\n', (size_t)(end - p));
        const char *line_end = newline ? newline : end;
        p = newline ? newline + 1 : end;
        const char *key = NULL;
        unsigned flag = 0;
        if (source == COH_PROCESS_MEMORY_STATUS) {
            key = "VmRSS:"; flag = 1;
        } else if ((size_t)(line_end-line) >= 4 && !memcmp(line, "Rss:", 4)) {
            key = "Rss:"; flag = 1;
        } else { key = "Pss:"; flag = 2; }
        size_t key_size = strlen(key);
        if ((size_t)(line_end-line) < key_size || memcmp(line, key, key_size)) continue;
        if (found & flag) return COH_INVALID;
        CohProcessMemoryValue *value = flag == 1 ? &result.rss : &result.pss;
        CohStatus status = number(line + key_size, line_end, &value->bytes);
        if (status != COH_OK) return status;
        value->status = COH_OK; value->source = source;
        found |= flag;
    }
    if (found != (source == COH_PROCESS_MEMORY_STATUS ? 1u : 3u)) return COH_NOT_FOUND;
    if (source == COH_PROCESS_MEMORY_STATUS) result.status_file_status = COH_OK;
    else result.rollup_status = COH_OK;
    *out = result;
    return COH_OK;
}

#if defined(__linux__) || defined(__ANDROID__)
static CohStatus read_proc(const char *path, char *text, size_t *size,
                           CohProcessMemorySnapshot *stats, int *error) {
    *size = 0; *error = 0;
    /* An interrupted open is unavailable for this sample, not an infinite retry. */
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) { *error = errno; return COH_IO; }
    stats->files_opened++;
    CohStatus status = COH_LIMIT;
    for (unsigned attempt = 0; attempt < COH_PROCESS_MEMORY_READ_LIMIT; attempt++) {
        /* One extra byte distinguishes a full valid file from an oversized one. */
        size_t remaining = COH_PROCESS_MEMORY_TEXT_LIMIT + 1u - *size;
        stats->read_calls++;
        ssize_t n = read(fd, text + *size, remaining);
        if (n < 0) {
            if (errno == EINTR) continue;
            *error = errno; status = COH_IO; break;
        }
        if (!n) { status = COH_OK; break; }
        *size += (size_t)n; stats->bytes_read += (uint64_t)n;
        if (*size > COH_PROCESS_MEMORY_TEXT_LIMIT) break;
    }
    /* Never retry close on Linux/Android: fd is consumed even after EINTR. */
    if (close(fd) < 0 && status == COH_OK) { *error = errno; status = COH_IO; }
    return status;
}
#endif
CohStatus coh_process_memory_sample(CohProcessMemorySnapshot *out) {
    if (!out) return COH_INVALID;
    CohProcessMemorySnapshot result = unknown(COH_UNSUPPORTED, 0);
#if defined(__linux__) || defined(__ANDROID__)
    result = unknown(COH_NOT_FOUND, 0);
    char text[COH_PROCESS_MEMORY_TEXT_LIMIT + 1u];
    size_t size = 0;
    CohProcessMemorySnapshot parsed;
    result.rollup_status = read_proc("/proc/self/smaps_rollup", text, &size, &result,
                                     &result.rollup_errno);
    if (result.rollup_status == COH_OK)
        result.rollup_status = coh_process_memory_parse(COH_PROCESS_MEMORY_SMAPS_ROLLUP,
                                                        text, size, &parsed);
    if (result.rollup_status == COH_OK) {
        result.rss = parsed.rss; result.pss = parsed.pss;
    } else {
        result.pss.status = result.rollup_status;
        result.pss.system_error = result.rollup_errno;
        result.status_file_status = read_proc("/proc/self/status", text, &size, &result,
                                              &result.status_file_errno);
        if (result.status_file_status == COH_OK)
            result.status_file_status = coh_process_memory_parse(COH_PROCESS_MEMORY_STATUS,
                                                                 text, size, &parsed);
        if (result.status_file_status == COH_OK) result.rss = parsed.rss;
        else {
            result.rss.status = result.status_file_status;
            result.rss.system_error = result.status_file_errno;
        }
    }
#endif
    *out = result;
    return result.rss.status == COH_OK ? COH_OK : result.rss.status;
}
static int valid_value(const CohProcessMemoryValue *v) {
    if ((unsigned)v->status > COH_STATE || (unsigned)v->source > COH_PROCESS_MEMORY_STATUS ||
        v->system_error < 0) return 0;
    if (v->status == COH_OK) return v->source != COH_PROCESS_MEMORY_NONE && !v->system_error;
    return !v->bytes && v->source == COH_PROCESS_MEMORY_NONE;
}
static int valid(const CohProcessMemorySnapshot *s) {
    return s && valid_value(&s->rss) && valid_value(&s->pss) &&
        (s->pss.status != COH_OK || s->pss.source == COH_PROCESS_MEMORY_SMAPS_ROLLUP) &&
        (unsigned)s->rollup_status <= COH_STATE && (unsigned)s->status_file_status <= COH_STATE &&
        s->rollup_errno >= 0 && s->status_file_errno >= 0 && s->files_opened <= 2 &&
        s->read_calls <= 2 * COH_PROCESS_MEMORY_READ_LIMIT &&
        s->bytes_read <= 2 * (COH_PROCESS_MEMORY_TEXT_LIMIT + 1u);
}
CohStatus coh_process_memory_apply(const CohProcessMemorySnapshot *s, CohPerfBridge *b) {
    if (!b || !valid(s)) return COH_INVALID;
    if (s->rss.status == COH_OK) coh_perf_bridge_memory(b, COH_PERF_MEMORY_RSS, s->rss.bytes);
    if (s->pss.status == COH_OK) coh_perf_bridge_memory(b, COH_PERF_MEMORY_PSS, s->pss.bytes);
    return s->rss.status == COH_OK || s->pss.status == COH_OK ? COH_OK : COH_NOT_FOUND;
}
static const char *source_name(CohProcessMemorySource source) {
    static const char *const names[] = {"unavailable", "proc_self_smaps_rollup", "proc_self_status_VmRSS"};
    return names[source];
}
CohStatus coh_process_memory_json(const CohProcessMemorySnapshot *s, char *out,
                                 size_t cap, size_t *needed) {
    if (!needed || (!out && cap) || !valid(s)) return COH_INVALID;
    int n = snprintf(out, cap,
        "{\"schema\":1,\"scope\":\"process_memory_sample\",\"unit\":\"bytes\","
        "\"rss\":{\"known\":%s,\"bytes\":%"PRIu64",\"source\":\"%s\",\"status\":%u,\"errno\":%d},"
        "\"pss\":{\"known\":%s,\"bytes\":%"PRIu64",\"source\":\"%s\",\"status\":%u,\"errno\":%d},"
        "\"rollup_status\":%u,\"rollup_errno\":%d,\"status_file_status\":%u,\"status_file_errno\":%d,"
        "\"files_opened\":%u,\"read_calls\":%u,\"bytes_read\":%"PRIu64"}",
        s->rss.status == COH_OK ? "true" : "false", s->rss.bytes, source_name(s->rss.source),
        (unsigned)s->rss.status, s->rss.system_error,
        s->pss.status == COH_OK ? "true" : "false", s->pss.bytes, source_name(s->pss.source),
        (unsigned)s->pss.status, s->pss.system_error,
        (unsigned)s->rollup_status, s->rollup_errno, (unsigned)s->status_file_status,
        s->status_file_errno, s->files_opened, s->read_calls, s->bytes_read);
    if (n < 0) { if (cap) out[0] = 0; return COH_IO; }
    *needed = (size_t)n + 1;
    if (*needed > cap) { if (cap) out[0] = 0; return COH_LIMIT; }
    return COH_OK;
}
