/* The actual paired sink and unchanged path helper, with local WinAPI shims. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#define SERVER 1
#define _WIN32 1
#define COH_NATIVE_SCENE_CATALOG_TEST_WINAPI 1
typedef unsigned int DWORD;
typedef int HANDLE;
#define INVALID_HANDLE_VALUE (-1)
#define INVALID_FILE_ATTRIBUTES 0xffffffffu
#define FILE_ATTRIBUTE_DIRECTORY 16u
#define FILE_ATTRIBUTE_REPARSE_POINT 1024u
#define FILE_ATTRIBUTE_NORMAL 128u
#define GENERIC_WRITE 0x40000000u
#define CREATE_NEW 1u
#define ERROR_FILE_NOT_FOUND 2u
#define MOVEFILE_WRITE_THROUGH 8u
#define COH_SNAPSHOT_MAX_BYTES (16u*1024u*1024u)
typedef int (*CohSourceCatalogOutputFn)(void*,const unsigned char*,unsigned int);
typedef struct {unsigned int status,failure_file,failure_slot,files,definitions,slots,children,wire_bytes,total_bytes,emitted_bytes;} CohSourceCatalogExportReport;
typedef struct {unsigned int status,total_bytes,emitted_bytes,root_slots,active_roots,external_count,external_children,defs_crc,refs_crc;} CohSourceSnapshotReport;
static const char *paths[2],*generation;
static unsigned int exists[2],partial[2],opened[2],written[2],calls[6],fail_kind,fail_at,reparse,producer_failure,checks,last_error;
static char log_text[2048];
#define CHECK(x) do {if(!(x)){fprintf(stderr,"pair sink fail line%u\n",__LINE__);abort();}++checks;} while(0)
static int fault(unsigned int kind){++calls[kind];return fail_kind==kind+1 && calls[kind]==fail_at;}
static int mock_printf(const char *format,...){int n;va_list a;va_start(a,format);n=vsprintf(log_text,format,a);va_end(a);return n;}
static DWORD GetEnvironmentVariableA(const char *name,char *out,DWORD cap)
{
    const char *v=!strcmp(name,"COH_NATIVE_SCENE_CATALOG_OUTPUT")?paths[0]:!strcmp(name,"COH_NATIVE_RUNTIME_SNAPSHOT_OUTPUT")?paths[1]:generation;
    size_t n;if(!v)return 0;n=strlen(v);if(n>=cap)return (DWORD)n+1;memcpy(out,v,n+1);return (DWORD)n;
}
static DWORD GetFileAttributesA(const char *path)
{
    unsigned i;for(i=0;i<2;i++)if(paths[i]&&!strcmp(path,paths[i])){last_error=ERROR_FILE_NOT_FOUND;return exists[i]?FILE_ATTRIBUTE_NORMAL:INVALID_FILE_ATTRIBUTES;}
    return FILE_ATTRIBUTE_DIRECTORY|(reparse?FILE_ATTRIBUTE_REPARSE_POINT:0);
}
static DWORD GetLastError(void){return last_error;}
static HANDLE CreateFileA(const char *path,DWORD access,DWORD share,void *security,DWORD creation,DWORD attrs,void *template_file)
{
    unsigned i;(void)security;(void)template_file;CHECK(access==GENERIC_WRITE&&!share&&creation==CREATE_NEW&&attrs==FILE_ATTRIBUTE_NORMAL);
    for(i=0;i<2;i++)if(paths[i]&&!strncmp(path,paths[i],strlen(paths[i]))&&!strcmp(path+strlen(paths[i]),".partial"))break;
    CHECK(i<2);if(fault(0)||partial[i])return INVALID_HANDLE_VALUE;partial[i]=opened[i]=1;return (HANDLE)i+11;
}
static int WriteFile(HANDLE h,const unsigned char *bytes,DWORD n,DWORD *out,void *overlap)
{unsigned i=(unsigned)(h-11);(void)bytes;(void)overlap;CHECK(i<2&&opened[i]);if(fault(1)){*out=0;return 0;}written[i]+=n;*out=n;return 1;}
static int FlushFileBuffers(HANDLE h){CHECK(h>=11&&h<13&&opened[h-11]);return !fault(2);}
static int CloseHandle(HANDLE h){CHECK(h>=11&&h<13&&opened[h-11]);if(fault(3))return 0;opened[h-11]=0;return 1;}
static int MoveFileExA(const char *from,const char *to,DWORD flags)
{unsigned i;(void)from;for(i=0;i<2;i++)if(!strcmp(paths[i],to))break;CHECK(i<2&&!opened[i]&&partial[i]&&flags==MOVEFILE_WRITE_THROUGH);if(fault(4)||exists[i])return 0;partial[i]=0;exists[i]=1;return 1;}
static int DeleteFileA(const char *path)
{unsigned i;for(i=0;i<2;i++)if(!strncmp(path,paths[i],strlen(paths[i])))break;CHECK(i<2&&partial[i]);if(fault(5)||opened[i])return 0;partial[i]=0;return 1;}
static int coh_source_catalog_export(CohSourceCatalogOutputFn out,void *context,unsigned int gen,CohSourceCatalogExportReport *r)
{static unsigned char bytes[48];CHECK(gen==20261016);r->total_bytes=48;r->files=1;r->definitions=r->slots=1;if(producer_failure==1){r->status=3;return 3;}if(!out(context,bytes,48)){r->status=5;return 5;}r->emitted_bytes=48;return 0;}
static int coh_source_runtime_snapshot_export(CohSourceCatalogOutputFn out,void *context,const unsigned char head[48],const CohSourceCatalogExportReport *catalog,CohSourceSnapshotReport *r)
{static unsigned char bytes[80];(void)head;CHECK(catalog->emitted_bytes==48);r->total_bytes=80;if(producer_failure==2){r->status=3;return 3;}if(!out(context,bytes,80)){r->status=5;return 5;}r->emitted_bytes=80;return 0;}
static int coh_source_catalog_same_name(const char *a,const char *b)
{while(*a&&*b){unsigned ca=(unsigned char)*a++,cb=(unsigned char)*b++;if(ca>='A'&&ca<='Z')ca+=32;if(cb>='A'&&cb<='Z')cb+=32;if(ca!=cb)return 0;}return *a==*b;}
#define printf mock_printf
#include "source_sink.inc"
#include "source_snapshot_sink.inc"
#undef printf
static void reset(void)
{paths[0]="C:\\private\\catalog.cohcat";paths[1]="C:\\private\\runtime.cohrts";generation="20261016";memset(exists,0,sizeof(exists));memset(partial,0,sizeof(partial));memset(opened,0,sizeof(opened));memset(written,0,sizeof(written));memset(calls,0,sizeof(calls));fail_kind=fail_at=reparse=producer_failure=0;log_text[0]=0;}
static void status(unsigned n){char expected[64];sprintf(expected,"COH_RUNTIME_SNAPSHOT_V1 status=%u ",n);CHECK(!strncmp(log_text,expected,strlen(expected)));CHECK(!strstr(log_text,"private")&&!strstr(log_text,"cohrts"));}
int main(void)
{
    unsigned i,k;
    reset();paths[0]=paths[1]=NULL;coh_source_runtime_snapshot_startup();CHECK(!log_text[0]&&!calls[0]);
    reset();coh_source_runtime_snapshot_startup();status(1);CHECK(exists[0]&&exists[1]&&!partial[0]&&!partial[1]&&!opened[0]&&!opened[1]);
    for(k=1;k<=5;k++)for(i=1;i<=2;i++)
    {reset();fail_kind=k;fail_at=i;coh_source_runtime_snapshot_startup();status(k==1?4:k==2?5:k==3?6:k==4?7:8);CHECK(!opened[0]&&!opened[1]&&!partial[0]&&!partial[1]);CHECK(!exists[1]);CHECK(exists[0]==(k==5&&i==2));}
    for(i=1;i<=2;i++){reset();producer_failure=i;coh_source_runtime_snapshot_startup();status(5);CHECK(!exists[0]&&!exists[1]&&!opened[0]&&!opened[1]&&!partial[0]&&!partial[1]);}
    for(i=0;i<2;i++){reset();exists[i]=1;coh_source_runtime_snapshot_startup();status(3);CHECK(!calls[0]&&exists[i]);}
    reset();reparse=1;coh_source_runtime_snapshot_startup();status(3);CHECK(!calls[0]);
    reset();paths[1]=paths[0];coh_source_runtime_snapshot_startup();status(3);CHECK(!calls[0]);
    reset();paths[1]="c:\\private\\CATALOG.cohcat";coh_source_runtime_snapshot_startup();status(3);CHECK(!calls[0]);
    reset();paths[1]="C:\\private\\catalog.cohcat.partial";coh_source_runtime_snapshot_startup();status(3);CHECK(!calls[0]);
    reset();paths[1]="Z:\\private\\..\\runtime.cohrts";coh_source_runtime_snapshot_startup();status(3);CHECK(!calls[0]);
    reset();paths[1]=NULL;coh_source_runtime_snapshot_startup();status(2);CHECK(!calls[0]);
    reset();generation="4294967296";coh_source_runtime_snapshot_startup();status(2);CHECK(!calls[0]);
    reset();partial[1]=1;coh_source_runtime_snapshot_startup();status(4);CHECK(!partial[0]&&partial[1]&&!opened[0]);
    printf("{\"passed\":true,\"checks\":%u,\"actual_pair_sink\":true,\"runtime_executed\":false}\n",checks);return 0;
}
