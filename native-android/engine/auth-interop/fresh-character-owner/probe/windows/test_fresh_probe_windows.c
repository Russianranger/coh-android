/* New Windows backend, controlled Win32/transport/entropy API doubles.
 * Actual host OpenSSL hashes synthetic retained-file byte streams. */
#include "../fresh_probe_platform.h"
#include "test_fresh_windows_api.h"
#include <openssl/evp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static unsigned checks,scenarios,api_calls,fail_at,closed,wiped_frees;
static const char *fault;
static void *allocation;static size_t allocation_bytes;
static int tcp_live,udp_live;static unsigned udp_closes,udp_cleanups;
static unsigned udp_default_zero;
static unsigned tcp_uncertain,tcp_finish_calls,quarantine_observations;
static int process_open;static unsigned process_queries;
typedef struct {
    unsigned char bytes[128];size_t bytes_count,position;
    BY_HANDLE_FILE_INFORMATION info;unsigned open,reads,infos;
} FakeFile;
static FakeFile policy,map,self;
static unsigned process_token;
#define CHECK(x) do { ++checks;if(!(x)){fprintf(stderr,"windows backend test line %u: %s\n",(unsigned)__LINE__,#x);exit(1);} } while(0)
static int is(const char *value) {return fault&&!strcmp(fault,value);}
static int refuse(void) {++api_calls;return fail_at&&fail_at==api_calls;}
static int zeroed(const void *p,size_t n) {const unsigned char *b=p;while(n--)if(*b++)return 0;return 1;}
void *__real_calloc(size_t,size_t);
void __real_free(void *);
void *__wrap_calloc(size_t n,size_t bytes) {
    CHECK(!allocation&&n==1);if(is("allocate"))return NULL;
    allocation=__real_calloc(n,bytes);allocation_bytes=bytes;CHECK(allocation);return allocation;
}
void __wrap_free(void *p) {
    CHECK(p==allocation&&zeroed(p,allocation_bytes));allocation=NULL;allocation_bytes=0;wiped_frees++;__real_free(p);
}
void coh_auth_wipe(void *p,size_t bytes) {volatile unsigned char *b=p;while(bytes--)*b++=0;}
static CohAuthCrypto provider;
const CohAuthCrypto *coh_auth_openssl_provider(void) {if(refuse()||is("provider"))return NULL;return &provider;}
int fresh_test_RAND_bytes(unsigned char *out,int bytes) {
    CHECK(bytes==4);if(refuse()||is("entropy-fail"))return 0;
    memset(out,is("entropy-zero")?0:0x65,(size_t)bytes);return 1;
}
static FakeFile *file(HANDLE handle) {
    CHECK(handle==&policy||handle==&map||handle==&self);FakeFile *f=handle;CHECK(f->open);return f;
}
static int tagged(FakeFile *f,const char *p,const char *m,const char *s) {
    return is(f==&policy?p:f==&map?m:s);
}
static void open_args(DWORD access,DWORD share,void *security,DWORD mode,DWORD flags,HANDLE template_file) {
    CHECK(access==GENERIC_READ&&share==FILE_SHARE_READ&&!security&&mode==OPEN_EXISTING&&
        flags==(FILE_ATTRIBUTE_NORMAL|FILE_FLAG_OPEN_REPARSE_POINT)&&!template_file);
}
HANDLE CreateFileA(const char *path,DWORD access,DWORD share,void *security,DWORD mode,DWORD flags,HANDLE template_file) {
    open_args(access,share,security,mode,flags,template_file);CHECK(!strcmp(path,"PRIVATE_POLICY_SENTINEL"));
    if(refuse()||is("policy-open"))return INVALID_HANDLE_VALUE;
    CHECK(!policy.open);policy.open=1;return &policy;
}
HANDLE CreateFileW(const wchar_t *path,DWORD access,DWORD share,void *security,DWORD mode,DWORD flags,HANDLE template_file) {
    FakeFile *f=!wcscmp(path,L"PRIVATE_SELF_SENTINEL")?&self:&map;
    open_args(access,share,security,mode,flags,template_file);CHECK(f==&self||!wcscmp(path,L"PRIVATE_MAP_SENTINEL"));
    if(refuse()||tagged(f,"unused","map-open","self-open"))return INVALID_HANDLE_VALUE;
    CHECK(!f->open);f->open=1;return f;
}
DWORD GetFileType(HANDLE handle) {
    FakeFile *f=file(handle);return refuse()||tagged(f,"policy-device","map-device","self-device")?0:FILE_TYPE_DISK;
}
BOOL GetFileInformationByHandle(HANDLE handle,BY_HANDLE_FILE_INFORMATION *out) {
    FakeFile *f=file(handle);f->infos++;
    if(refuse())return 0;
    *out=f->info;
    if(tagged(f,"policy-reparse","map-reparse","self-reparse"))out->dwFileAttributes|=FILE_ATTRIBUTE_REPARSE_POINT;
    if(tagged(f,"policy-directory","map-directory","self-directory"))out->dwFileAttributes|=FILE_ATTRIBUTE_DIRECTORY;
    if(tagged(f,"policy-info-change","map-info-change","self-info-change")&&f->infos>1)out->nFileIndexLow++;
    return 1;
}
BOOL GetFileSizeEx(HANDLE handle,LARGE_INTEGER *out) {
    FakeFile *f=file(handle);if(refuse())return 0;
    out->QuadPart=(int64_t)f->bytes_count;
    if(tagged(f,"policy-empty","map-empty","self-empty"))out->QuadPart=0;
    if(tagged(f,"policy-size-change","map-size-change","self-size-change"))out->QuadPart++;
    if(tagged(f,"policy-huge","map-huge","self-huge"))out->QuadPart=128*1024*1024;
    return 1;
}
BOOL SetFilePointerEx(HANDLE handle,LARGE_INTEGER offset,LARGE_INTEGER *new_offset,DWORD method) {
    FakeFile *f=file(handle);CHECK(offset.QuadPart==0&&!new_offset&&method==FILE_BEGIN);
    if(refuse())return 0;
    f->position=0;return 1;
}
BOOL ReadFile(HANDLE handle,void *out,DWORD capacity,DWORD *bytes,void *overlap) {
    FakeFile *f=file(handle);CHECK(!overlap&&capacity);f->reads++;
    if(refuse())return 0;
    size_t available=f->bytes_count-f->position,take=available<capacity?available:capacity;
    if(tagged(f,"policy-short","map-short","self-short")&&take)take--;
    if(is("policy-excess")&&f==&policy&&!take){*(unsigned char*)out=0x21;*bytes=1;return 1;}
    memcpy(out,f->bytes+f->position,take);f->position+=take;*bytes=(DWORD)take;return 1;
}
BOOL CloseHandle(HANDLE handle) {
    if(refuse()||is("close-persistent"))return 0;
    if(handle==&process_token){CHECK(process_open);process_open=0;}
    else {FakeFile *f=file(handle);f->open=0;}
    closed++;return 1;
}
DWORD GetModuleFileNameW(HANDLE module,wchar_t *out,DWORD capacity) {
    CHECK(!module&&capacity==32768);if(refuse()||is("self-path"))return 0;
    if(is("self-path-truncated"))return capacity;
    wcscpy(out,L"PRIVATE_SELF_SENTINEL");return (DWORD)wcslen(out);
}
HANDLE OpenProcess(DWORD access,BOOL inherit,DWORD pid) {
    CHECK(access==(PROCESS_QUERY_LIMITED_INFORMATION|SYNCHRONIZE)&&!inherit&&pid==4242);
    if(refuse()||is("process-open"))return NULL;
    CHECK(!process_open);process_open=1;return &process_token;
}
DWORD WaitForSingleObject(HANDLE process,DWORD ms) {
    CHECK(process==&process_token&&process_open&&!ms);process_queries++;
    if(refuse()||is("wait-failed"))return WAIT_FAILED;
    if(is("process-exited")||(is("process-late-exit")&&process_queries>3))return 0;
    return WAIT_TIMEOUT;
}
DWORD GetProcessId(HANDLE process) {
    CHECK(process==&process_token&&process_open);return refuse()||is("process-pid")?4243:4242;
}
BOOL GetProcessTimes(HANDLE process,FILETIME *creation,FILETIME *exit_time,FILETIME *kernel,FILETIME *user) {
    CHECK(process==&process_token&&process_open);if(refuse())return 0;
    *creation=(FILETIME){is("process-creation")?100:99,0};
    *exit_time=*kernel=*user=(FILETIME){0,0};return 1;
}
BOOL QueryFullProcessImageNameW(HANDLE process,DWORD flags,wchar_t *out,DWORD *bytes) {
    CHECK(process==&process_token&&process_open&&!flags&&*bytes==32768);
    if(refuse()||is("map-path"))return 0;
    if(is("map-path-truncated")){*bytes=32768;return 1;}
    wcscpy(out,L"PRIVATE_MAP_SENTINEL");*bytes=(DWORD)wcslen(out);return 1;
}
uint64_t GetTickCount64(void) {return 123456;}
void Sleep(DWORD ms) {CHECK(ms==2);}
int coh_win_initialize(void) {
    if(refuse()||is("tcp-init")||is("tcp-wrong-version-forgotten-cleanup")){tcp_uncertain=1;return -1;}
    tcp_live=1;return 0;
}
int coh_win_limits(unsigned send,unsigned receive,int corrupt) {
    CHECK(send==1024&&receive==11&&!corrupt&&tcp_live);return refuse()||is("tcp-limits")?-1:0;
}
int coh_db_win_initialize(void) {
    if(is("udp-init-unacquired")){udp_default_zero=1;return -1;}
    udp_live=1;return refuse()||is("udp-init")?-1:0;
}
int coh_db_win_finish(void) {
    if(refuse()||is("udp-finish-persistent")){udp_cleanups++;return -1;}
    udp_live=0;return 0;
}
void coh_db_win_diagnostics(CohDbWinDiagnostics *out) {
    *out=(CohDbWinDiagnostics){(unsigned)udp_live,is("udp-handles")?1u:0u,0,0,udp_closes,udp_cleanups,(unsigned)(!udp_live&&!udp_default_zero)};
}
int coh_win_finish(void) {
    /* Exact frozen adapter shape: failed WSACleanup forgets initialized;
     * the following call returns success without releasing that reference. */
    tcp_finish_calls++;
    if(!tcp_live)return 0;
    tcp_live=0;
    if(refuse()||is("tcp-finish-persistent")||is("tcp-finish-forgotten-cleanup")){tcp_uncertain=1;return -1;}
    return 0;
}
unsigned coh_win_open_handles(void) {return is("tcp-handles")?1u:0u;}
static void le32(unsigned char *p,uint32_t value) {
    p[0]=(unsigned char)value;p[1]=(unsigned char)(value>>8);p[2]=(unsigned char)(value>>16);p[3]=(unsigned char)(value>>24);
}
static void fixture(const char *label,unsigned failure) {
    CHECK(!allocation&&!process_open&&!policy.open&&!map.open&&!self.open);
    fault=label;fail_at=failure;api_calls=closed=process_queries=0;tcp_live=udp_live=0;
    udp_closes=udp_cleanups=udp_default_zero=tcp_uncertain=tcp_finish_calls=0;
    memset(&policy,0,sizeof(policy));memset(&map,0,sizeof(map));memset(&self,0,sizeof(self));
    memcpy(map.bytes,"Synthetic Map executable bytes",30);map.bytes_count=30;
    memcpy(self.bytes,"Synthetic probe executable bytes",32);self.bytes_count=32;
    policy.bytes_count=96;memcpy(policy.bytes,"COHFRC01",8);le32(policy.bytes+8,1);le32(policy.bytes+12,29999);
    le32(policy.bytes+16,1);policy.bytes[20]=127;policy.bytes[23]=1;le32(policy.bytes+24,7001);
    le32(policy.bytes+28,4242);le32(policy.bytes+32,99);memset(policy.bytes+72,0x43,16);
    unsigned bytes=0;CHECK(EVP_Digest(map.bytes,map.bytes_count,policy.bytes+40,&bytes,EVP_sha256(),NULL)==1&&bytes==32);
    if(is("policy-invalid"))policy.bytes[0]=0;
    if(is("map-hash"))policy.bytes[40]^=1;
    FakeFile *files[3]={&policy,&map,&self};
    for(unsigned i=0;i<3;i++)files[i]->info=(BY_HANDLE_FILE_INFORMATION){FILE_ATTRIBUTE_NORMAL,{11,0},{22,0},{33,0},55,0,(DWORD)files[i]->bytes_count,1,0,i+1};
}
static FreshProbePlatformDiagnostics observation(FreshProbeLease *lease) {
    FreshProbePlatformDiagnostics out;memset(&out,0,sizeof(out));
    CHECK(fresh_probe_platform_diagnostics(lease,&out)==COH_OK);return out;
}
static unsigned transaction(const char *label,unsigned failure,int preflight,int expected_success) {
    CohFreshCharacterConfig config,prior;FreshProbeLease *lease;
    fixture(label,failure);lease=fresh_probe_platform_open(preflight,preflight?NULL:"PRIVATE_POLICY_SENTINEL");
    CHECK(lease&&!fresh_probe_platform_open(preflight,preflight?NULL:"PRIVATE_POLICY_SENTINEL"));
    memset(&config,0xa5,sizeof(config));prior=config;
    CohStatus status=fresh_probe_platform_config(lease,&config);
    if(status!=COH_OK)CHECK(!memcmp(&config,&prior,sizeof(config)));
    else {
        CHECK(config.connect_id&&config.crypto==&provider);
        CHECK(!zeroed(config.executable_checksum,16));
        CHECK(fresh_probe_platform_config(lease,&config)==COH_STATE);
        if(!preflight){CHECK(config.auth_endpoint.port==29999&&config.owned_map_id==1&&config.owned_map_endpoint.port==7001);status=fresh_probe_platform_before_begin(lease);}
    }
    CohStatus finish=fresh_probe_platform_finish(lease);FreshProbePlatformDiagnostics d=observation(lease);
    unsigned calls=api_calls;
    if(expected_success) {
        CHECK(status==COH_OK&&finish==COH_OK&&d.initialization_verified&&d.cleanup_complete&&d.no_live_tcp_handles&&d.no_live_udp_handles);
        CHECK(d.supplied_map_policy_admitted==(unsigned)!preflight&&d.map_process_file_generation_before==(unsigned)!preflight&&
            d.map_process_file_generation_after==(unsigned)!preflight);
    } else CHECK(status!=COH_OK||finish!=COH_OK);
    CHECK(fresh_probe_platform_config(lease,&config)==COH_STATE&&fresh_probe_platform_before_begin(lease)==COH_STATE);
    if(tcp_uncertain) {
        /* No test backdoor resets the production quarantine. This child must
         * exit with the still-owned lease rather than free it after a no-op. */
        FreshProbeLease *same=lease;unsigned prior_calls=tcp_finish_calls;
        CHECK(!d.cleanup_complete&&!d.transport_cleanup_complete);
        CHECK(fresh_probe_platform_destroy(&lease)==COH_IO&&lease==same&&allocation);
        CHECK(!observation(lease).cleanup_complete&&tcp_finish_calls==prior_calls);
        quarantine_observations++;
    } else CHECK(fresh_probe_platform_destroy(&lease)==COH_OK&&!lease&&!allocation&&!process_open&&!policy.open&&!map.open&&!self.open);
    scenarios++;return calls;
}
static unsigned isolated_transaction(const char *label,unsigned failure,int preflight,int success) {
    unsigned result[5]={0},before_checks=checks,before_scenarios=scenarios,before_frees=wiped_frees,before_quarantine=quarantine_observations;
    int channel[2],status=0;CHECK(pipe(channel)==0);pid_t child=fork();CHECK(child>=0);
    if(!child) {
        CHECK(close(channel[0])==0);
        result[0]=transaction(label,failure,preflight,success);
        result[1]=checks-before_checks;result[2]=scenarios-before_scenarios;
        result[3]=wiped_frees-before_frees;result[4]=quarantine_observations-before_quarantine;
        CHECK(write(channel[1],result,sizeof(result))==(ssize_t)sizeof(result));
        CHECK(close(channel[1])==0);_exit(0);
    }
    CHECK(close(channel[1])==0);
    CHECK(read(channel[0],result,sizeof(result))==(ssize_t)sizeof(result));
    CHECK(close(channel[0])==0&&waitpid(child,&status,0)==child&&WIFEXITED(status)&&!WEXITSTATUS(status));
    checks+=result[1];scenarios+=result[2];wiped_frees+=result[3];quarantine_observations+=result[4];return result[0];
}
static void stage_change(const char *label,int before) {
    CohFreshCharacterConfig config;FreshProbePlatformDiagnostics d;
    fixture(NULL,0);FreshProbeLease *lease=fresh_probe_platform_open(0,"PRIVATE_POLICY_SENTINEL");
    CHECK(lease&&fresh_probe_platform_config(lease,&config)==COH_OK);
    if(!before)CHECK(fresh_probe_platform_before_begin(lease)==COH_OK);
    fault=label;
    if(is("map-byte-change"))map.bytes[0]^=1;
    if(is("self-byte-change"))self.bytes[0]^=1;
    if(is("policy-identity-change"))policy.info.nFileIndexLow++;
    if(is("map-identity-change"))map.info.nFileIndexLow++;
    if(before) {
        CHECK(fresh_probe_platform_before_begin(lease)==COH_STATE);
        CHECK(fresh_probe_platform_before_begin(lease)==COH_STATE);
    }
    CHECK(fresh_probe_platform_finish(lease)==COH_STATE);d=observation(lease);
    CHECK(d.cleanup_complete&&d.map_process_file_generation_before==(unsigned)!before);
    CHECK(d.map_process_file_generation_after==(unsigned)is("self-byte-change"));
    CHECK(fresh_probe_platform_destroy(&lease)==COH_OK&&!lease&&!allocation);scenarios++;
}
int main(void) {
    FreshProbePlatformDiagnostics out,prior;CohFreshCharacterConfig config;
    memset(&out,0xa5,sizeof(out));prior=out;
    CHECK(fresh_probe_platform_diagnostics(NULL,&out)==COH_INVALID&&!memcmp(&out,&prior,sizeof(out)));
    CHECK(fresh_probe_platform_config(NULL,&config)==COH_INVALID&&fresh_probe_platform_before_begin(NULL)==COH_INVALID&&
        fresh_probe_platform_finish(NULL)==COH_INVALID&&fresh_probe_platform_destroy(NULL)==COH_INVALID);
    FreshProbeLease *none=NULL;CHECK(fresh_probe_platform_destroy(&none)==COH_OK);
    CHECK(!fresh_probe_platform_open(-1,NULL)&&!fresh_probe_platform_open(2,NULL)&&
        !fresh_probe_platform_open(1,"x")&&!fresh_probe_platform_open(0,NULL)&&!fresh_probe_platform_open(0,""));
    fixture("allocate",0);CHECK(!fresh_probe_platform_open(1,NULL)&&!allocation);
    unsigned runtime_calls=isolated_transaction(NULL,0,0,1),preflight_calls=isolated_transaction(NULL,0,1,1);
    /* Inject exactly one failure at each fallible API operation reached by
     * each successful path. The independent destroy retries retained closes. */
    for(unsigned i=1;i<=runtime_calls;i++)isolated_transaction(NULL,i,0,0);
    for(unsigned i=1;i<=preflight_calls;i++)isolated_transaction(NULL,i,1,0);
    const char *faults[]={"provider","entropy-fail","entropy-zero","self-path","self-path-truncated","self-open",
        "self-device","self-reparse","self-directory","self-empty","self-size-change","self-huge","self-info-change","self-short",
        "policy-open","policy-device","policy-reparse","policy-directory","policy-empty","policy-size-change","policy-huge",
        "policy-info-change","policy-short","policy-excess","policy-invalid","process-open","process-exited","wait-failed",
        "process-pid","process-creation","process-late-exit","map-path","map-path-truncated","map-open","map-device","map-reparse",
        "map-directory","map-empty","map-size-change","map-huge","map-info-change","map-short","map-hash","tcp-init","tcp-limits","udp-init","udp-init-unacquired",
        "tcp-wrong-version-forgotten-cleanup","tcp-finish-forgotten-cleanup","tcp-finish-persistent"};
    for(unsigned i=0;i<sizeof(faults)/sizeof(faults[0]);i++)isolated_transaction(faults[i],0,0,0);
    const char *late[]={"process-exited","wait-failed","process-pid","process-creation",
        "map-byte-change","policy-identity-change","map-identity-change"};
    for(unsigned i=0;i<sizeof(late)/sizeof(late[0]);i++) {
        stage_change(late[i],1);stage_change(late[i],0);
    }
    stage_change("self-byte-change",0);
    /* Known owner aliases refuse before writes/retirement; preflight cannot
     * begin. A persistent CloseHandle failure retains the private lease. */
    fixture(NULL,0);FreshProbeLease *lease=fresh_probe_platform_open(1,NULL);CHECK(lease);
    CHECK(fresh_probe_platform_config(lease,(CohFreshCharacterConfig*)(void*)lease)==COH_INVALID);
    CHECK(fresh_probe_platform_diagnostics(lease,(FreshProbePlatformDiagnostics*)(void*)lease)==COH_INVALID);
    CHECK(fresh_probe_platform_destroy((FreshProbeLease**)(void*)lease)==COH_INVALID);
    CHECK(fresh_probe_platform_before_begin(lease)==COH_STATE);
    fault="close-persistent";CHECK(fresh_probe_platform_finish(lease)==COH_IO&&!observation(lease).cleanup_complete);
    FreshProbeLease *same=lease;CHECK(fresh_probe_platform_destroy(&lease)==COH_IO&&lease==same&&allocation);
    fault=NULL;CHECK(fresh_probe_platform_destroy(&lease)==COH_OK&&!lease&&!allocation);
    const char *persistent[]={"udp-finish-persistent","tcp-handles","udp-handles"};
    for(unsigned i=0;i<sizeof(persistent)/sizeof(persistent[0]);i++) {
        fixture(NULL,0);lease=fresh_probe_platform_open(1,NULL);CHECK(lease);
        fault=persistent[i];CHECK(fresh_probe_platform_finish(lease)==COH_IO&&!observation(lease).cleanup_complete);
        same=lease;CHECK(fresh_probe_platform_destroy(&lease)==COH_IO&&lease==same&&allocation);
        fault=NULL;CHECK(fresh_probe_platform_destroy(&lease)==COH_OK&&!lease&&!allocation);scenarios++;
    }
    CHECK(fresh_probe_monotonic_ms()==123456);fresh_probe_pause();
    printf("{\"schema\":\"coh-fresh-windows-backend-api-controls-v1\",\"checks\":%u,\"scenarios\":%u,\"runtime_fallible_operations\":%u,\"preflight_fallible_operations\":%u,\"wiped_lease_frees\":%u,\"quarantined_child_leases\":%u,\"real_host_EVP_file_digests\":true,\"synthetic_file_process_transport_entropy_APIs\":true,\"Windows_execution\":false,\"original_owner_or_server\":false,\"Map_READY_or_world_authority\":false}\n",checks,scenarios,runtime_calls,preflight_calls,wiped_frees,quarantine_observations);
    return 0;
}
