/* NONSHIPPING Windows backend. Process/file policy is NOT Map readiness.
 * No import effects; one lease/process, used only after private driver admission.
 * Actual Windows compilation/execution is a separate qualification obligation. */
#include "../fresh_probe_platform.h"
#include "../fresh_probe_policy.h"
#ifdef COH_FRESH_WINDOWS_TEST
#include "test_fresh_windows_api.h"
#else
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0601
#endif
#include "../../../deployment/windows/winsock_compat.h"
#include "../../../deployment/windows/db_udp_winsock.h"
#endif
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <stdlib.h>
#include <string.h>

#define FRESH_PATH_CAP 32768u
#define FRESH_IMAGE_LIMIT (64u*1024u*1024u)
struct FreshProbeLease {
    FreshProbePlatformDiagnostics diagnostics;
    FreshProbeMapPolicy policy;
    CohFreshCharacterConfig config;
    HANDLE policy_file, map_process, map_file, self_file;
    BY_HANDLE_FILE_INFORMATION policy_identity, map_identity, self_identity;
    unsigned preflight, config_taken, before_attempted, finish_attempted;
    unsigned tcp_attempted, udp_attempted, udp_absent_after_failed_init, tcp_cleanup, tcp_cleanup_uncertain, map_admitted;
    CohStatus status;
};
static FreshProbeLease *active;

static void failed(FreshProbeLease *lease,CohStatus status) {
    if(lease->status==COH_OK)lease->status=status;
}
static int overlaps(const void *a,size_t an,const void *b,size_t bn) {
    uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
    return x<=y?y-x<an:x-y<bn;
}
static int distinct(const FreshProbeLease *lease,const void *out,size_t bytes) {
    return out&&!overlaps(lease,sizeof(*lease),out,bytes);
}
static uint64_t filetime(FILETIME value) {
    return (uint64_t)value.dwLowDateTime|((uint64_t)value.dwHighDateTime<<32);
}
static int same_file(const BY_HANDLE_FILE_INFORMATION *a,const BY_HANDLE_FILE_INFORMATION *b) {
    return a->dwFileAttributes==b->dwFileAttributes&&a->dwVolumeSerialNumber==b->dwVolumeSerialNumber&&
        a->nFileIndexHigh==b->nFileIndexHigh&&a->nFileIndexLow==b->nFileIndexLow&&
        a->nFileSizeHigh==b->nFileSizeHigh&&a->nFileSizeLow==b->nFileSizeLow&&
        filetime(a->ftCreationTime)==filetime(b->ftCreationTime)&&
        filetime(a->ftLastWriteTime)==filetime(b->ftLastWriteTime);
}
/* Retained handles deny concurrent write/delete opens, including preexisting
 * incompatible writers. Final-component reparses and devices refuse.
 * Ancestor policy/ACL/readiness admission belongs to the independent driver. */
static int regular_file(HANDLE file,uint64_t limit,BY_HANDLE_FILE_INFORMATION *identity) {
    LARGE_INTEGER size;
    return file!=INVALID_HANDLE_VALUE&&GetFileType(file)==FILE_TYPE_DISK&&
        GetFileInformationByHandle(file,identity)&&
        !(identity->dwFileAttributes&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT))&&
        GetFileSizeEx(file,&size)&&size.QuadPart>0&&(uint64_t)size.QuadPart<=limit&&
        !identity->nFileSizeHigh&&(uint64_t)identity->nFileSizeLow==(uint64_t)size.QuadPart;
}
static int digest_file(HANDLE file,const BY_HANDLE_FILE_INFORMATION *identity,
    const EVP_MD *method,unsigned expected,uint8_t *out) {
    uint8_t block[16384]={0},digest[EVP_MAX_MD_SIZE]={0};
    BY_HANDLE_FILE_INFORMATION before,after;LARGE_INTEGER origin;
    EVP_MD_CTX *ctx=NULL;uint64_t total=0;unsigned bytes=0;int valid=0;
    origin.QuadPart=0;
    if(!GetFileInformationByHandle(file,&before)||!same_file(identity,&before)||
       !SetFilePointerEx(file,origin,NULL,FILE_BEGIN))goto done;
    ctx=EVP_MD_CTX_new();if(!ctx||EVP_DigestInit_ex(ctx,method,NULL)!=1)goto done;
    for(;;) {
        DWORD got=0;if(!ReadFile(file,block,(DWORD)sizeof(block),&got,NULL))goto done;
        if(!got)break;
        total+=got;if(total>identity->nFileSizeLow||EVP_DigestUpdate(ctx,block,got)!=1)goto done;
        coh_auth_wipe(block,sizeof(block));
    }
    if(total!=identity->nFileSizeLow||EVP_DigestFinal_ex(ctx,digest,&bytes)!=1||bytes!=expected||
       !GetFileInformationByHandle(file,&after)||!same_file(identity,&after))goto done;
    memcpy(out,digest,expected);valid=1;
done:
    EVP_MD_CTX_free(ctx);coh_auth_wipe(block,sizeof(block));coh_auth_wipe(digest,sizeof(digest));
    coh_auth_wipe(&before,sizeof(before));coh_auth_wipe(&after,sizeof(after));
    return valid;
}
static int process_generation(const FreshProbeLease *lease) {
    FILETIME creation,exit_time,kernel,user;
    return lease->map_process&&WaitForSingleObject(lease->map_process,0)==WAIT_TIMEOUT&&
        GetProcessId(lease->map_process)==lease->policy.map_pid&&
        GetProcessTimes(lease->map_process,&creation,&exit_time,&kernel,&user)&&
        filetime(creation)==lease->policy.map_creation_filetime;
}
static int map_generation(const FreshProbeLease *lease) {
    uint8_t digest[32]={0};int valid=process_generation(lease)&&
        digest_file(lease->map_file,&lease->map_identity,EVP_sha256(),32,digest)&&
        !memcmp(digest,lease->policy.map_executable_sha256,32)&&process_generation(lease);
    coh_auth_wipe(digest,sizeof(digest));return valid;
}
static int policy_generation(const FreshProbeLease *lease) {
    BY_HANDLE_FILE_INFORMATION info;
    int valid=GetFileInformationByHandle(lease->policy_file,&info)&&same_file(&lease->policy_identity,&info);
    coh_auth_wipe(&info,sizeof(info));return valid;
}
static int admit_self(FreshProbeLease *lease) {
    wchar_t path[FRESH_PATH_CAP]={0};int valid=0;
    DWORD length=GetModuleFileNameW(NULL,path,FRESH_PATH_CAP);
    if(!length||length>=FRESH_PATH_CAP)goto done;
    lease->self_file=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,NULL,OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL|FILE_FLAG_OPEN_REPARSE_POINT,NULL);
    if(!regular_file(lease->self_file,16u*1024u*1024u,&lease->self_identity)||
       !digest_file(lease->self_file,&lease->self_identity,EVP_md5(),16,lease->config.executable_checksum))goto done;
    lease->diagnostics.checksum_measured_from_actual_probe=1;valid=1;
done:
    coh_auth_wipe(path,sizeof(path));return valid;
}
static int admit_policy(FreshProbeLease *lease,const char *path) {
    uint8_t record[FRESH_PROBE_POLICY_BYTES]={0},extra=0;DWORD bytes=0;
    wchar_t image[FRESH_PATH_CAP]={0};int valid=0;
    lease->policy_file=CreateFileA(path,GENERIC_READ,FILE_SHARE_READ,NULL,OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL|FILE_FLAG_OPEN_REPARSE_POINT,NULL);
    if(!regular_file(lease->policy_file,FRESH_PROBE_POLICY_BYTES,&lease->policy_identity)||
       lease->policy_identity.nFileSizeLow!=FRESH_PROBE_POLICY_BYTES||
       !ReadFile(lease->policy_file,record,FRESH_PROBE_POLICY_BYTES,&bytes,NULL)||bytes!=FRESH_PROBE_POLICY_BYTES||
       !ReadFile(lease->policy_file,&extra,1,&bytes,NULL)||bytes||
       fresh_probe_decode_policy((CohBytes){record,sizeof(record)},&lease->policy)!=COH_OK||
       !policy_generation(lease))goto done;
    lease->map_process=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION|SYNCHRONIZE,FALSE,lease->policy.map_pid);
    if(!process_generation(lease))goto done;
    bytes=FRESH_PATH_CAP;
    if(!QueryFullProcessImageNameW(lease->map_process,0,image,&bytes)||!bytes||bytes>=FRESH_PATH_CAP)goto done;
    lease->map_file=CreateFileW(image,GENERIC_READ,FILE_SHARE_READ,NULL,OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL|FILE_FLAG_OPEN_REPARSE_POINT,NULL);
    if(!regular_file(lease->map_file,FRESH_IMAGE_LIMIT,&lease->map_identity)||!map_generation(lease))goto done;
    lease->map_admitted=1;lease->diagnostics.supplied_map_policy_admitted=1;
    lease->config.auth_endpoint=lease->policy.auth_endpoint;
    lease->config.owned_map_endpoint=lease->policy.map_endpoint;
    lease->config.owned_map_id=lease->policy.map_id;valid=1;
done:
    coh_auth_wipe(record,sizeof(record));coh_auth_wipe(&extra,sizeof(extra));
    coh_auth_wipe(image,sizeof(image));return valid;
}
FreshProbeLease *fresh_probe_platform_open(int preflight,const char *path) {
    FreshProbeLease *lease;
    if(active||(preflight!=0&&preflight!=1)||(preflight?path!=NULL:!path||!path[0]))return NULL;
    lease=calloc(1,sizeof(*lease));if(!lease)return NULL;
    active=lease;lease->preflight=(unsigned)preflight;lease->status=COH_OK;
    lease->policy_file=lease->map_file=lease->self_file=INVALID_HANDLE_VALUE;
    lease->tcp_attempted=1;
    if(coh_win_initialize()) {
        /* The frozen TCP adapter does not report whether a failed startup
         * released a wrong-version WSA reference. It also forgets initialized
         * after failed finish. A later no-op is never cleanup evidence. Keep
         * this lease quarantined until this isolated CLI process exits. */
        lease->tcp_cleanup_uncertain=1;failed(lease,COH_IO);return lease;
    }
    if(coh_win_limits(1024,11,0)){failed(lease,COH_IO);return lease;}
    lease->udp_attempted=1;
    if(coh_db_win_initialize()) {
        /* WSAStartup may fail before the unchanged adapter acquires a WSA
         * reference or writes its default-zero diagnostics. Its finish then
         * correctly has nothing to release and leaves cleanup_complete zero.
         * Distinguish that observed absence from a retained partial startup. */
        CohDbWinDiagnostics udp={0};coh_db_win_diagnostics(&udp);
        lease->udp_absent_after_failed_init=!udp.initialized&&!udp.active_handles&&
            udp.sockets_created==udp.sockets_closed;
        coh_auth_wipe(&udp,sizeof(udp));failed(lease,COH_IO);return lease;
    }
    lease->config.crypto=coh_auth_openssl_provider();
    if(!lease->config.crypto||RAND_bytes((uint8_t*)&lease->config.connect_id,(int)sizeof(lease->config.connect_id))!=1||
       !lease->config.connect_id){failed(lease,COH_IO);return lease;}
    lease->diagnostics.fresh_connect_entropy=1;
    if(!admit_self(lease)||(!preflight&&!admit_policy(lease,path))){failed(lease,COH_INVALID);return lease;}
    lease->diagnostics.initialization_verified=1;return lease;
}
CohStatus fresh_probe_platform_config(FreshProbeLease *lease,CohFreshCharacterConfig *out) {
    if(!lease||lease!=active||!distinct(lease,out,sizeof(*out)))return COH_INVALID;
    if(lease->finish_attempted||lease->config_taken)return COH_STATE;
    if(lease->status!=COH_OK)return lease->status;
    memcpy(out,&lease->config,sizeof(*out));lease->config_taken=1;return COH_OK;
}
uint64_t fresh_probe_monotonic_ms(void) {return GetTickCount64();}
void fresh_probe_pause(void) {Sleep(2);}
CohStatus fresh_probe_platform_before_begin(FreshProbeLease *lease) {
    if(!lease||lease!=active)return COH_INVALID;
    if(lease->preflight||!lease->config_taken||lease->before_attempted||lease->finish_attempted)return COH_STATE;
    lease->before_attempted=1;
    if(lease->status!=COH_OK)return lease->status;
    if(!lease->map_admitted||!policy_generation(lease)||!map_generation(lease))failed(lease,COH_STATE);
    else lease->diagnostics.map_process_file_generation_before=1;
    return lease->status;
}
static void close_file(FreshProbeLease *lease,HANDLE *file) {
    if(*file!=INVALID_HANDLE_VALUE) {
        if(CloseHandle(*file))*file=INVALID_HANDLE_VALUE;else failed(lease,COH_IO);
    }
}
CohStatus fresh_probe_platform_finish(FreshProbeLease *lease) {
    CohDbWinDiagnostics udp={0};
    if(!lease||lease!=active)return COH_INVALID;
    if(!lease->finish_attempted) {
        lease->finish_attempted=1;
        if(lease->map_admitted) {
            if(!policy_generation(lease)||!map_generation(lease))failed(lease,COH_STATE);
            else lease->diagnostics.map_process_file_generation_after=1;
        }
        /* A retained actual self handle prevents ordinary write/delete races;
         * remeasure too, without publishing checksum/path/file contents. */
        if(lease->diagnostics.checksum_measured_from_actual_probe) {
            uint8_t digest[16]={0};
            if(!digest_file(lease->self_file,&lease->self_identity,EVP_md5(),16,digest)||
               memcmp(digest,lease->config.executable_checksum,16))failed(lease,COH_STATE);
            coh_auth_wipe(digest,sizeof(digest));
        }
    }
    if(lease->udp_attempted&&coh_db_win_finish())failed(lease,COH_IO);
    coh_db_win_diagnostics(&udp);
    lease->diagnostics.no_live_udp_handles=!udp.active_handles;
    if(udp.initialized||udp.active_handles||udp.close_failures||udp.cleanup_failures||
       (lease->udp_attempted&&!udp.cleanup_complete&&!lease->udp_absent_after_failed_init)||
       udp.sockets_created!=udp.sockets_closed)failed(lease,COH_IO);
    if(lease->tcp_attempted&&!lease->tcp_cleanup_uncertain) {
        lease->tcp_cleanup=coh_win_finish()==0;
        if(!lease->tcp_cleanup){lease->tcp_cleanup_uncertain=1;failed(lease,COH_IO);}
    }
    lease->diagnostics.no_live_tcp_handles=!coh_win_open_handles();
    if(!lease->diagnostics.no_live_tcp_handles)failed(lease,COH_IO);
    lease->diagnostics.transport_cleanup_complete=lease->diagnostics.no_live_tcp_handles&&
        lease->diagnostics.no_live_udp_handles&&!lease->tcp_cleanup_uncertain&&
        (!lease->tcp_attempted||lease->tcp_cleanup)&&
        !udp.initialized&&(!lease->udp_attempted||udp.cleanup_complete||lease->udp_absent_after_failed_init);
    close_file(lease,&lease->policy_file);close_file(lease,&lease->map_file);close_file(lease,&lease->self_file);
    if(lease->map_process) {
        if(CloseHandle(lease->map_process))lease->map_process=NULL;else failed(lease,COH_IO);
    }
    lease->diagnostics.private_policy_handle_closed=lease->policy_file==INVALID_HANDLE_VALUE;
    lease->diagnostics.map_process_handle_closed=lease->map_process==NULL;
    lease->diagnostics.cleanup_complete=lease->diagnostics.transport_cleanup_complete&&
        lease->diagnostics.private_policy_handle_closed&&lease->diagnostics.map_process_handle_closed&&
        lease->map_file==INVALID_HANDLE_VALUE&&lease->self_file==INVALID_HANDLE_VALUE;
    coh_auth_wipe(&udp,sizeof(udp));return lease->status;
}
CohStatus fresh_probe_platform_diagnostics(const FreshProbeLease *lease,FreshProbePlatformDiagnostics *out) {
    if(!lease||lease!=active||!distinct(lease,out,sizeof(*out)))return COH_INVALID;
    memcpy(out,&lease->diagnostics,sizeof(*out));return COH_OK;
}
CohStatus fresh_probe_platform_destroy(FreshProbeLease **slot) {
    FreshProbeLease *lease;
    if(!slot)return COH_INVALID;
    if(active&&overlaps(active,sizeof(*active),slot,sizeof(*slot)))return COH_INVALID;
    lease=*slot;if(!lease)return COH_OK;
    if(lease!=active)return COH_INVALID;
    (void)fresh_probe_platform_finish(lease);
    if(!lease->diagnostics.cleanup_complete)return lease->status==COH_OK?COH_STATE:lease->status;
    coh_auth_wipe(lease,sizeof(*lease));free(lease);active=NULL;*slot=NULL;return COH_OK;
}
