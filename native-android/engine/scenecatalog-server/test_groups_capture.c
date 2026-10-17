/* Actual sink and boundary with original catalog/runtime/raw/world suppliers.
 * These are deterministic source-layout fixtures; WinAPI/quiet/entity/resource
 * substitutions are explicit and never establish runtime or Win32 qualification.
 * The qualification driver prepends the shared original-supplier fixture. */
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
#include <stdarg.h>
static const char*destination;
static unsigned file_exists,file_partial,file_open,file_size,last_error,current_thread=17u,reparse,lookup_error,short_write;
static unsigned file_calls[6],fault_kind,fault_at;
static unsigned char file_bytes[4u*1024u*1024u];
static char capture_log[2048];
static int capture_printf(const char*format,...){int n;va_list args;va_start(args,format);n=vsnprintf(capture_log,sizeof(capture_log),format,args);va_end(args);return n;}
static int io_fault(unsigned kind){file_calls[kind]++;return fault_kind==kind+1u&&file_calls[kind]==fault_at;}
static DWORD GetCurrentThreadId(void){return current_thread;}
static DWORD GetEnvironmentVariableA(const char*name,char*out,DWORD size)
{size_t n;if(strcmp(name,"COH_NATIVE_GROUPS_TRANSACTION_OUTPUT")||!destination)return 0;n=strlen(destination);if(n>=size)return(unsigned)n+1u;memcpy(out,destination,n+1u);return(unsigned)n;}
static DWORD GetFileAttributesA(const char*path)
{if(destination&&!strcmp(path,destination)){last_error=lookup_error?5u:ERROR_FILE_NOT_FOUND;return file_exists?FILE_ATTRIBUTE_NORMAL:INVALID_FILE_ATTRIBUTES;}return FILE_ATTRIBUTE_DIRECTORY|(reparse?FILE_ATTRIBUTE_REPARSE_POINT:0u);}
static DWORD GetLastError(void){return last_error;}
static HANDLE CreateFileA(const char*path,DWORD access,DWORD share,void*security,DWORD disposition,DWORD attributes,void*template_file)
{(void)security;(void)template_file;CHECK(access==GENERIC_WRITE&&!share&&disposition==CREATE_NEW&&attributes==FILE_ATTRIBUTE_NORMAL);CHECK(!strncmp(path,destination,strlen(destination))&&!strcmp(path+strlen(destination),".partial"));if(io_fault(0)||file_partial)return INVALID_HANDLE_VALUE;file_partial=file_open=1;return 11;}
static int WriteFile(HANDLE handle,const unsigned char*p,DWORD n,DWORD*written,void*overlap)
{(void)overlap;CHECK(handle==11&&file_open&&p&&n<=sizeof(file_bytes)-file_size);if(io_fault(1)){*written=short_write?n/2u:0u;return short_write?1:0;}memcpy(file_bytes+file_size,p,n);file_size+=n;*written=n;return 1;}
static int FlushFileBuffers(HANDLE h){CHECK(h==11&&file_open);return!io_fault(2);}
static int CloseHandle(HANDLE h){CHECK(h==11&&file_open);if(io_fault(3))return 0;file_open=0;return 1;}
static int MoveFileExA(const char*from,const char*to,DWORD flags)
{CHECK(!file_open&&file_partial&&flags==MOVEFILE_WRITE_THROUGH&&!strcmp(to,destination)&&!strcmp(from+strlen(destination),".partial"));if(io_fault(4)||file_exists)return 0;file_partial=0;file_exists=1;return 1;}
static int DeleteFileA(const char*path){CHECK(file_partial&&!file_open&&!strcmp(path+strlen(destination),".partial"));if(io_fault(5))return 0;file_partial=0;return 1;}
#define printf capture_printf
#include "source_sink.inc"
#include "source_groups_capture_sink.inc"
#undef printf
static void capture_setup(void)
{
 unsigned f,i;CHECK(!quiet&&!file_open);
 memset(&coh_groups_boundary,0,sizeof(coh_groups_boundary));memset(&coh_groups_transaction_hooks,0,sizeof(coh_groups_transaction_hooks));memset(&coh_groups_capture_file,0,sizeof(coh_groups_capture_file));coh_groups_transaction_active=0;
 memset(file_calls,0,sizeof(file_calls));memset(file_bytes,0,sizeof(file_bytes));capture_log[0]=0;
 destination="C:\\private\\live.cohgtx";file_exists=file_partial=file_open=file_size=last_error=fault_kind=fault_at=reparse=lookup_error=short_write=0;current_thread=17;
 folder_cache_update_enable=0;folder_cache_manual_callback_check=1;
 snapshot_setup(0,0);for(f=0;f<(unsigned)group_info.file_count;f++){GroupFile*file=group_info.files[f];file->idx=(int)f;for(i=0;i<(unsigned)file->count;i++)if(file->defs[i])((unsigned char*)file->defs[i]->min)[59]|=0x80;}group_info.files[1]->force_reload=1;
}
static void capture_world(void){NetLink link={0};worldSendUpdate(&link,1);CHECK(!quiet&&!file_open);}
static void capture_check_envelope(void)
{
 unsigned at=64,sequence=0,packets=0,footer=0,id=coh_raw_bounds_u32(file_bytes+16),sizes[9]={0},chunks[9]={0};
 CHECK(file_exists&&!file_partial&&!file_open&&file_size>=64&&!memcmp(file_bytes,"COHGTX01",8)&&coh_raw_bounds_u32(file_bytes+8)==1&&coh_raw_bounds_u32(file_bytes+12)==64&&id==1);
 while(at<file_size){unsigned kind,n;CHECK(file_size-at>=16);kind=coh_raw_bounds_u32(file_bytes+at);n=coh_raw_bounds_u32(file_bytes+at+8);CHECK(kind>=1&&kind<=9&&coh_raw_bounds_u32(file_bytes+at+4)==id&&coh_raw_bounds_u32(file_bytes+at+12)==sequence++&&n<=file_size-at-16);at+=16;
  if(kind==8){packets++;CHECK(n==(oracle_packet.stream.bitLength+7u)/8u&&!memcmp(file_bytes+at,oracle_storage,n));}
  if(kind==9){unsigned j;footer++;CHECK(n==128&&at+n==file_size&&!memcmp(file_bytes+at,"COHGEND1",8)&&coh_raw_bounds_u32(file_bytes+at+20)==file_size&&coh_raw_bounds_u32(file_bytes+at+24)==sequence);for(j=0;j<8;j++){CHECK(coh_raw_bounds_u32(file_bytes+at+32+j*4)==sizes[j]);CHECK(coh_raw_bounds_u32(file_bytes+at+64+j*4)==chunks[j]);}}
  sizes[kind-1]+=n;chunks[kind-1]++;at+=n;
 }
 CHECK(packets==1&&footer==1&&at==file_size&&strstr(capture_log,"status=1")&&strstr(capture_log,"source_quiet_released=1")&&!strstr(capture_log,"private"));
}
BOUNDARY_ORIGINAL_WORLD
int main(int argc,char**argv)
{
 unsigned counts[6],i,j,failures=0;
 capture_setup();destination=NULL;coh_source_groups_capture_install();CHECK(!coh_groups_transaction_hooks.begin&&!file_calls[0]);capture_world();CHECK(!file_size&&!capture_log[0]);
 capture_setup();coh_source_groups_capture_install();CHECK(coh_groups_transaction_hooks.begin&&!file_size&&!file_calls[0]);capture_world();capture_check_envelope();memcpy(counts,file_calls,sizeof(counts));
 if(argc==2){FILE*out=fopen(argv[1],"wb");CHECK(out&&fwrite(file_bytes,1,file_size,out)==file_size&&fclose(out)==0);}
 i=file_size;capture_world();CHECK(file_size==i&&file_exists&&coh_groups_capture_file.attempted);
 for(i=0;i<5;i++)for(j=1;j<=counts[i];j++){capture_setup();fault_kind=i+1;fault_at=j;coh_source_groups_capture_install();capture_world();CHECK(!file_exists&&!file_partial&&!file_open&&coh_groups_capture_file.attempted&&strstr(capture_log,"status=2"));failures++;}
 capture_setup();fault_kind=2;fault_at=2;short_write=1;coh_source_groups_capture_install();capture_world();CHECK(!file_exists&&!file_partial&&!file_open);failures++;
 capture_setup();file_exists=1;coh_source_groups_capture_install();capture_world();CHECK(file_exists&&!file_partial&&!file_calls[0]);
 capture_setup();file_partial=1;coh_source_groups_capture_install();capture_world();CHECK(!file_exists&&file_partial&&!file_open&&file_calls[0]==1);file_partial=0;
 capture_setup();lookup_error=1;coh_source_groups_capture_install();capture_world();CHECK(!file_exists&&!file_partial&&!file_calls[0]);
 capture_setup();reparse=1;coh_source_groups_capture_install();CHECK(!coh_groups_transaction_hooks.begin);capture_world();CHECK(!file_calls[0]);
 capture_setup();destination="Z:\\private\\..\\bad";coh_source_groups_capture_install();CHECK(!coh_groups_transaction_hooks.begin);capture_world();CHECK(!file_calls[0]);
 capture_setup();coh_source_groups_capture_install();current_thread=18;capture_world();CHECK(!file_size&&!coh_groups_capture_file.attempted);current_thread=17;capture_world();capture_check_envelope();
 capture_setup();coh_source_groups_capture_install();folder_cache_update_enable=1;capture_world();CHECK(!file_size&&!coh_groups_capture_file.attempted);folder_cache_update_enable=0;capture_world();capture_check_envelope();
 capture_setup();coh_source_groups_capture_install();coh_groups_capture_file.bytes=COH_GROUPS_CAPTURE_BYTES_MAX;capture_world();CHECK(!file_exists&&!file_partial&&!file_open);
 capture_setup();coh_groups_transaction_hooks.begin=coh_groups_boundary_begin;coh_source_groups_capture_install();CHECK(!coh_groups_capture_file.configured&&coh_groups_transaction_hooks.begin==coh_groups_boundary_begin);
 printf("{\"passed\":true,\"checks\":%u,\"io_refusals\":%u,\"actual_sink_and_original_source_suppliers_executed\":true,\"quiet_owner_resource_winapi_substituted\":true,\"actual_server_capture_count\":0,\"world_authority\":false}\n",checks,failures);return 0;
}
