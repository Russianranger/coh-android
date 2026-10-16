#define _POSIX_C_SOURCE 200809L
#include "coh_process_memory.h"
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static unsigned checks, guard, allocator_calls, fake, closes, opens;
#define CHECK(c) do { checks++; if (!(c)) { fprintf(stderr,"check %u line %u: %s\n",checks,__LINE__,#c); abort(); } } while (0)
void *__real_malloc(size_t); void *__real_calloc(size_t,size_t);
void *__real_realloc(void *,size_t); void __real_free(void *);
void *__wrap_malloc(size_t n) { if (guard) allocator_calls++; return __real_malloc(n); }
void *__wrap_calloc(size_t n,size_t m) { if (guard) allocator_calls++; return __real_calloc(n,m); }
void *__wrap_realloc(void *p,size_t n) { if (guard) allocator_calls++; return __real_realloc(p,n); }
void __wrap_free(void *p) { if (guard) allocator_calls++; __real_free(p); }
typedef struct {
    const char *text; size_t size, position, chunk;
    int open_error, read_error, close_error;
    unsigned interrupts, read_calls, closed;
} FakeFile;
static FakeFile files[2];
int __real_open(const char *, int, ...); ssize_t __real_read(int,void *,size_t); int __real_close(int);
int __wrap_open(const char *path,int flags,...) {
    if (!fake) {
        mode_t mode = 0;
        if (flags & O_CREAT) { va_list ap; va_start(ap,flags); mode = va_arg(ap,mode_t); va_end(ap); }
        return __real_open(path,flags,mode);
    }
    CHECK(flags == (O_RDONLY | O_CLOEXEC));
    int index;
    if (!strcmp(path,"/proc/self/smaps_rollup")) index = 0;
    else { CHECK(!strcmp(path,"/proc/self/status")); index = 1; }
    opens++;
    if (files[index].open_error) { errno = files[index].open_error; return -1; }
    return 101 + index;
}
ssize_t __wrap_read(int fd,void *out,size_t bytes) {
    if (!fake) return __real_read(fd,out,bytes);
    CHECK(fd == 101 || fd == 102); FakeFile *f = &files[fd-101];
    CHECK(!f->closed && bytes > 0 && bytes <= COH_PROCESS_MEMORY_TEXT_LIMIT + 1);
    f->read_calls++;
    if (f->interrupts) { f->interrupts--; errno = EINTR; return -1; }
    if (f->read_error) { errno = f->read_error; return -1; }
    size_t n = f->size - f->position;
    if (n > bytes) n = bytes;
    if (f->chunk && n > f->chunk) n = f->chunk;
    if (n) memcpy(out,f->text+f->position,n);
    f->position += n; return (ssize_t)n;
}
int __wrap_close(int fd) {
    if (!fake) return __real_close(fd);
    CHECK(fd == 101 || fd == 102); FakeFile *f = &files[fd-101];
    CHECK(!f->closed); f->closed = 1; closes++;
    if (f->close_error) { errno = f->close_error; return -1; }
    return 0;
}
static const char *rollup = "00001000-ffff0000 ---p 00000000 00:00 0 [rollup]\nRss: 8192 kB\nPss: 4096 kB\nPss_Anon: 7 kB\n";
static const char *status = "Name:\tcoh\nVmSize:\t99999 kB\nVmRSS:\t12345 kB\n";
static void reset(void) {
    memset(files,0,sizeof files);
    files[0].text=rollup; files[0].size=strlen(rollup);
    files[1].text=status; files[1].size=strlen(status);
    fake=1; opens=closes=0;
}
static void parse_tests(void) {
    CohProcessMemorySnapshot out, saved; memset(&saved,0x5a,sizeof saved); out=saved;
    CHECK(coh_process_memory_parse(COH_PROCESS_MEMORY_NONE,rollup,strlen(rollup),&out)==COH_INVALID);
    CHECK(!memcmp(&out,&saved,sizeof out));
    CHECK(coh_process_memory_parse(COH_PROCESS_MEMORY_STATUS,NULL,0,&out)==COH_INVALID);
    CHECK(coh_process_memory_parse(COH_PROCESS_MEMORY_STATUS,status,strlen(status),NULL)==COH_INVALID);
    CHECK(coh_process_memory_parse(COH_PROCESS_MEMORY_STATUS,status,COH_PROCESS_MEMORY_TEXT_LIMIT+1,&out)==COH_LIMIT);
    CHECK(!memcmp(&out,&saved,sizeof out));
    const char *invalid[] = {"Rss: -1 kB\nPss: 2 kB\n", "Rss: +1 kB\nPss: 2 kB\n",
        "Rss: 1 KB\nPss: 2 kB\n", "Rss: 1 B\nPss: 2 kB\n", "Rss: 1kB\nPss: 2 kB\n",
        "Rss: 1 kB junk\nPss: 2 kB\n", "Rss: 1.0 kB\nPss: 2 kB\n",
        "Rss: 1 kB\nPss: 2 kB\nPss: 2 kB", "Rss: 1 kB\nRss: 1 kB\nPss: 2 kB",
        "Rss: kB\nPss: 2 kB", "Rss:\nPss: 2 kB"};
    for (size_t i=0;i<sizeof invalid/sizeof *invalid;i++) {
        CHECK(coh_process_memory_parse(COH_PROCESS_MEMORY_SMAPS_ROLLUP,invalid[i],strlen(invalid[i]),&out)==COH_INVALID);
        CHECK(!memcmp(&out,&saved,sizeof out));
    }
    const char nul[]="Rss: 1 kB\n\0Pss: 2 kB\n";
    CHECK(coh_process_memory_parse(COH_PROCESS_MEMORY_SMAPS_ROLLUP,nul,sizeof nul-1,&out)==COH_INVALID);
    const char *overflow[] = {"Rss: 18446744073709551616 kB\nPss: 2 kB",
        "Rss: 18014398509481984 kB\nPss: 2 kB", "Rss: 00018446744073709551616 kB\nPss: 2 kB"};
    for (size_t i=0;i<sizeof overflow/sizeof *overflow;i++)
        CHECK(coh_process_memory_parse(COH_PROCESS_MEMORY_SMAPS_ROLLUP,overflow[i],strlen(overflow[i]),&out)==COH_LIMIT);
    const char *missing[] = {"", "Rss: 1 kB", "Pss: 2 kB", "VmRSS: 1 kB\nPss_Anon: 2 kB", " Rss: 1 kB\nPss: 2 kB"};
    for (size_t i=0;i<sizeof missing/sizeof *missing;i++)
        CHECK(coh_process_memory_parse(COH_PROCESS_MEMORY_SMAPS_ROLLUP,missing[i],strlen(missing[i]),&out)==COH_NOT_FOUND);
    char text[512];
    for (uint64_t i=0;i<4096;i++) {
        uint64_t rss=i*4398046511103u,pss=rss/3;
        int n=snprintf(text,sizeof text,"Header ignored\nRss:\t%"PRIu64" kB \r\nPss:\t%"PRIu64" kB\nPss_File: 999 kB\n",rss,pss);
        CHECK(n>0 && (size_t)n<sizeof text);
        guard=1;
        CHECK(coh_process_memory_parse(COH_PROCESS_MEMORY_SMAPS_ROLLUP,text,(size_t)n,&out)==COH_OK);
        guard=0;
        CHECK(out.rss.bytes==rss*1024 && out.pss.bytes==pss*1024);
        CHECK(out.rss.source==COH_PROCESS_MEMORY_SMAPS_ROLLUP && out.pss.status==COH_OK);
    }
    const char *maximum="Rss: 18014398509481983 kB\nPss: 0 kB";
    CHECK(coh_process_memory_parse(COH_PROCESS_MEMORY_SMAPS_ROLLUP,maximum,strlen(maximum),&out)==COH_OK);
    CHECK(out.rss.bytes==UINT64_MAX-1023 && out.pss.bytes==0 && out.pss.status==COH_OK);
    CHECK(coh_process_memory_parse(COH_PROCESS_MEMORY_STATUS,status,strlen(status),&out)==COH_OK);
    CHECK(out.rss.bytes==12345*1024 && out.rss.source==COH_PROCESS_MEMORY_STATUS);
    CHECK(out.pss.status==COH_NOT_FOUND && out.pss.bytes==0);
}
static void sample_tests(void) {
    CohProcessMemorySnapshot s;
    CHECK(coh_process_memory_sample(NULL)==COH_INVALID);
    reset(); guard=1; CHECK(coh_process_memory_sample(&s)==COH_OK); guard=0;
    CHECK(s.rss.bytes==8192*1024 && s.pss.bytes==4096*1024);
    CHECK(s.files_opened==1 && s.read_calls==2 && opens==1 && closes==1);
    reset(); files[0].open_error=EACCES;
    CHECK(coh_process_memory_sample(&s)==COH_OK);
    CHECK(s.rss.bytes==12345*1024 && s.rss.source==COH_PROCESS_MEMORY_STATUS);
    CHECK(s.pss.status==COH_IO && s.pss.system_error==EACCES && s.pss.bytes==0);
    CHECK(s.rollup_status==COH_IO && s.rollup_errno==EACCES && opens==2 && closes==1);
    reset(); files[0].open_error=ENOENT; files[1].open_error=EACCES;
    CHECK(coh_process_memory_sample(&s)==COH_IO);
    CHECK(s.pss.system_error==ENOENT && s.rss.system_error==EACCES && !s.files_opened && !closes);
    reset(); files[0].read_error=EIO;
    CHECK(coh_process_memory_sample(&s)==COH_OK && s.pss.system_error==EIO && closes==2);
    reset(); files[0].close_error=EINTR;
    CHECK(coh_process_memory_sample(&s)==COH_OK && s.pss.system_error==EINTR && closes==2);
    reset(); files[0].interrupts=3; files[0].chunk=7;
    CHECK(coh_process_memory_sample(&s)==COH_OK && s.pss.status==COH_OK);
    CHECK(s.read_calls==3+(strlen(rollup)+6)/7+1);
    reset(); files[0].interrupts=COH_PROCESS_MEMORY_READ_LIMIT+1;
    CHECK(coh_process_memory_sample(&s)==COH_OK && s.pss.status==COH_LIMIT);
    CHECK(files[0].read_calls==COH_PROCESS_MEMORY_READ_LIMIT && closes==2);
    reset(); files[0].text="Rss: 2 kB\nPss: -1 kB"; files[0].size=strlen(files[0].text);
    CHECK(coh_process_memory_sample(&s)==COH_OK && s.pss.status==COH_INVALID && s.rss.source==COH_PROCESS_MEMORY_STATUS);
    char large[COH_PROCESS_MEMORY_TEXT_LIMIT+1]; memset(large,'x',sizeof large);
    memcpy(large,rollup,strlen(rollup)); large[strlen(rollup)]='\n';
    reset(); files[0].text=large; files[0].size=COH_PROCESS_MEMORY_TEXT_LIMIT;
    CHECK(coh_process_memory_sample(&s)==COH_OK && s.pss.status==COH_OK && s.bytes_read==COH_PROCESS_MEMORY_TEXT_LIMIT);
    reset(); files[0].text=large; files[0].size=sizeof large;
    CHECK(coh_process_memory_sample(&s)==COH_OK && s.pss.status==COH_LIMIT);
    CHECK(files[0].position==sizeof large && closes==2);
    reset(); files[0].open_error=EINTR; files[1].interrupts=COH_PROCESS_MEMORY_READ_LIMIT+1;
    CHECK(coh_process_memory_sample(&s)==COH_LIMIT && s.rss.status==COH_LIMIT && s.pss.system_error==EINTR);
    CHECK(opens==2 && closes==1 && s.read_calls==COH_PROCESS_MEMORY_READ_LIMIT);
    reset(); files[0].open_error=EACCES; files[1].text="Name: x\nVmPeak: 100 kB"; files[1].size=strlen(files[1].text);
    CHECK(coh_process_memory_sample(&s)==COH_NOT_FOUND && s.rss.status==COH_NOT_FOUND);
    reset(); files[0].open_error=EACCES; files[1].close_error=EIO;
    CHECK(coh_process_memory_sample(&s)==COH_IO && s.rss.system_error==EIO);
}
static void apply_json_tests(void) {
    CohProcessMemorySnapshot s; CohPerfBridge b,copy; coh_perf_bridge_init(&b);
    reset(); files[0].open_error=EACCES; files[1].open_error=ENOENT;
    CHECK(coh_process_memory_sample(&s)==COH_IO);
    CHECK(coh_process_memory_apply(&s,&b)==COH_NOT_FOUND);
    CHECK(!b.memory[COH_PERF_MEMORY_RSS].observations && !b.memory[COH_PERF_MEMORY_PSS].observations);
    reset(); CHECK(coh_process_memory_sample(&s)==COH_OK);
    CHECK(coh_process_memory_apply(&s,&b)==COH_OK); copy=b;
    CHECK(b.memory[COH_PERF_MEMORY_RSS].current_bytes==8192*1024 && b.memory[COH_PERF_MEMORY_PSS].current_bytes==4096*1024);
    s.pss.source=COH_PROCESS_MEMORY_STATUS;
    CHECK(coh_process_memory_apply(&s,&b)==COH_INVALID && !memcmp(&b,&copy,sizeof b));
    s.pss.source=COH_PROCESS_MEMORY_SMAPS_ROLLUP; s.pss.system_error=1;
    CHECK(coh_process_memory_apply(&s,&b)==COH_INVALID && !memcmp(&b,&copy,sizeof b));
    s.pss.system_error=0; s.pss.status=COH_IO;
    CHECK(coh_process_memory_apply(&s,&b)==COH_INVALID && !memcmp(&b,&copy,sizeof b));
    CHECK(coh_process_memory_apply(NULL,&b)==COH_INVALID && coh_process_memory_apply(&s,NULL)==COH_INVALID);
    reset(); files[0].open_error=EACCES; files[1].open_error=ENOENT;
    CHECK(coh_process_memory_sample(&s)==COH_IO);
    CHECK(coh_process_memory_apply(&s,&b)==COH_NOT_FOUND && !memcmp(&b,&copy,sizeof b));
    char json[1024],one[1]; size_t needed=0,again=0;
    CHECK(coh_process_memory_json(&s,NULL,0,&needed)==COH_LIMIT && needed<sizeof json);
    CHECK(coh_process_memory_json(&s,one,1,&again)==COH_LIMIT && !one[0] && again==needed);
    CHECK(coh_process_memory_json(&s,json,needed-1,&again)==COH_LIMIT && !json[0]);
    CHECK(coh_process_memory_json(&s,json,needed,&again)==COH_OK && strlen(json)+1==needed);
    CHECK(strstr(json,"\"known\":false") && strstr(json,"\"source\":\"unavailable\""));
    CHECK(coh_process_memory_json(&s,NULL,1,&needed)==COH_INVALID);
    CHECK(coh_process_memory_json(&s,json,sizeof json,NULL)==COH_INVALID);
    reset(); files[0].text="Rss: 0 kB\nPss: 0 kB"; files[0].size=strlen(files[0].text);
    CHECK(coh_process_memory_sample(&s)==COH_OK && coh_process_memory_apply(&s,&b)==COH_OK);
    CHECK(!b.memory[COH_PERF_MEMORY_RSS].current_bytes && b.memory[COH_PERF_MEMORY_RSS].peak_bytes==8192*1024);
    CHECK(coh_process_memory_json(&s,json,sizeof json,&needed)==COH_OK && strstr(json,"\"known\":true,\"bytes\":0"));
    for (unsigned i=0;i<10000;i++) {
        reset(); if (i%3==0) files[0].open_error=EACCES;
        if (i%5==0) { files[0].open_error=ENOENT; files[1].open_error=EACCES; }
        guard=1;
        CohStatus status=coh_process_memory_sample(&s);
        CHECK(status==(i%5==0?COH_IO:COH_OK));
        CHECK(coh_process_memory_apply(&s,&b)==(i%5==0?COH_NOT_FOUND:COH_OK));
        CHECK(closes==s.files_opened && s.read_calls<=64);
        guard=0;
    }
    CHECK(b.memory[COH_PERF_MEMORY_RSS].observations==8002);
    CHECK(b.memory[COH_PERF_MEMORY_PSS].observations==5335);
}
int main(void) {
    parse_tests(); sample_tests(); apply_json_tests(); CHECK(allocator_calls==0);
    fake=0; CohProcessMemorySnapshot actual; guard=1;
    CohStatus status=coh_process_memory_sample(&actual); guard=0;
    CHECK(status==actual.rss.status && actual.files_opened<=2 && actual.read_calls<=64);
    char json[1024]; size_t needed;
    CHECK(coh_process_memory_json(&actual,json,sizeof json,&needed)==COH_OK);
    printf("{\"status\":\"passed\",\"checks\":%u,\"parser_property_cases\":4096,\"sample_stress_cycles\":10000,"
           "\"direct_allocator_calls\":%u,\"snapshot_bytes\":%zu,\"read_buffer_bytes\":%u,\"actual_host_sample\":%s}\n",
           checks,allocator_calls,sizeof actual,COH_PROCESS_MEMORY_TEXT_LIMIT+1,json);
    return 0;
}
