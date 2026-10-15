/* Bounded stock NT observer. No Game/database/graphics/provider registration.
 * Source-only until a fresh real Win32 SDK receipt is produced. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include "coh_live_native_authorization.h"
#define NT_PROBE_MAX_BYTES (512u*1024u)
#define NT_PROBE_MAX_ROWS 256u
#define NT_PROBE_MAX_BATCHES 32u
#define NT_PROBE_BUFFER_BYTES 8192u
#define NT_PROBE_STATUS_NO_MORE_FILES ((LONG)0x80000006u)
typedef LONG (WINAPI *CohProbeNtQueryDirectoryFile)(HANDLE,HANDLE,PVOID,PVOID,
 CohLiveIoStatus*,PVOID,ULONG,ULONG,BOOLEAN,CohLiveUnicodeString*,BOOLEAN);
typedef struct CohProbe {
 HANDLE input,output;uint64_t inode;uint32_t bytes,rows,batches,mode;
 LONG open_status,info_status,last_query;int failed,cleanup_failed,header_written;const char *path;
} CohProbe;
static uint32_t get32(const unsigned char *p) {
 return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static void put32(unsigned char *p,uint32_t v) {unsigned int i;for(i=0;i<4;i++)p[i]=(unsigned char)(v>>(i*8));}
static void put64(unsigned char *p,uint64_t v) {put32(p,(uint32_t)v);put32(p+4,(uint32_t)(v>>32));}
static int write_owned(CohProbe *probe,const unsigned char *p,uint32_t count) {
 DWORD written;uint32_t left=count;
 if(probe->bytes>NT_PROBE_MAX_BYTES||count>NT_PROBE_MAX_BYTES-probe->bytes)return 0;
 while(left){if(!WriteFile(probe->output,p,left,&written,NULL)||!written||written>left)return 0;
  p+=written;left-=written;probe->bytes+=written;}
 return 1;
}
static int ascii_absolute(const char *path) {
 size_t i,n;if(!path||!(n=strlen(path))||n>=1024||n<4||path[1]!=':'||
    !((path[0]>='A'&&path[0]<='Z')||(path[0]>='a'&&path[0]<='z'))||
    (path[2]!='/'&&path[2]!='\\'))return 0;
 for(i=2;i<n;i++)if((unsigned char)path[i]<32||(unsigned char)path[i]>=127||strchr(":*?\"<>|",path[i]))return 0;
 return 1;
}
static int same_or_descendant(const char *directory,const char *output) {
 size_t i,n=strlen(directory);
 for(i=0;i<n;i++){unsigned char a=(unsigned char)directory[i],b=(unsigned char)output[i];
  if(!b)return 0;if(a=='\\')a='/';if(b=='\\')b='/';
  if(cohLiveAsciiUpper(a)!=cohLiveAsciiUpper(b))return 0;}
 /* GetFullPathName can retain a trailing separator, including a drive root.
  * That separator already supplies the descendant component boundary. */
 return !output[n]||directory[n-1]=='/'||directory[n-1]=='\\'||output[n]=='/'||output[n]=='\\';
}
/* Validate the actual FileBoth record chain before publishing a batch. Its
 * unused/reserved bytes are native observation, never canonical WFD proof. */
static int batch_rows(const unsigned char *data,uint32_t bytes,uint32_t *rows) {
 uint32_t at=0,count=0;
 if(!bytes||bytes>NT_PROBE_BUFFER_BYTES)return 0;
 for(;;){uint32_t next,name_bytes,i,minimum;
  if(at>bytes||bytes-at<94)return 0;next=get32(data+at);name_bytes=get32(data+at+60);
  if(!name_bytes||(name_bytes&1)||name_bytes>518)return 0;
  minimum=94+name_bytes;if(minimum>bytes-at)return 0;
  for(i=0;i<name_bytes;i+=2){unsigned int c=data[at+94+i]|((unsigned int)data[at+95+i]<<8);
   if(c<32||c>=127||strchr("/\\:*?\"<>|",(int)c))return 0;}
  if(++count>NT_PROBE_MAX_ROWS)return 0;
  if(!next)break;if((next&7)||next<minimum||next>bytes-at)return 0;
  at+=next;
 }
 *rows=count;return 1;
}
static int header(CohProbe *probe,const char *path,const char *final_path) {
 unsigned char data[96];size_t a=strlen(path),b=strlen(final_path);
 memset(data,0,sizeof(data));memcpy(data,"COHNTB1",7);put32(data+8,1);put32(data+12,probe->mode);
 put32(data+16,GetCurrentProcessId());put32(data+20,GetCurrentThreadId());put64(data+32,probe->inode);
 put32(data+40,(uint32_t)probe->open_status);put32(data+44,(uint32_t)probe->info_status);
 put32(data+48,(uint32_t)a);put32(data+52,(uint32_t)b);put32(data+56,NT_PROBE_BUFFER_BYTES);
 put32(data+60,NT_PROBE_MAX_ROWS);put32(data+64,NT_PROBE_MAX_BATCHES);put32(data+68,NT_PROBE_MAX_BYTES);
 if(write_owned(probe,data,sizeof(data))&&write_owned(probe,(const unsigned char*)path,(uint32_t)a)&&
  write_owned(probe,(const unsigned char*)final_path,(uint32_t)b)){probe->header_written=1;return 1;}return 0;
}
static int batch(CohProbe *probe,const unsigned char *data,uint32_t bytes,uint32_t rows) {
 unsigned char record[24];memset(record,0,sizeof(record));memcpy(record,"NTBATCH1",8);
 put32(record+8,probe->batches);put32(record+12,(uint32_t)probe->last_query);put32(record+16,bytes);put32(record+20,rows);
 return write_owned(probe,record,sizeof(record))&&write_owned(probe,data,bytes);
}
static int finish(CohProbe *probe) {
 unsigned char record[40];int rc=probe->failed?1:0;
 if(probe->output!=INVALID_HANDLE_VALUE&&!probe->header_written) {
  if(!header(probe,probe->path?probe->path:"",""))rc=1;
 }
 if(probe->input!=INVALID_HANDLE_VALUE&&probe->input){if(!CloseHandle(probe->input))probe->cleanup_failed=1;probe->input=INVALID_HANDLE_VALUE;}
 if(probe->cleanup_failed)rc=1;
 memset(record,0,sizeof(record));memcpy(record,"NTEND1",6);put32(record+8,1);
 put32(record+12,rc?0:1);put32(record+16,probe->batches);put32(record+20,probe->rows);
 put32(record+24,(uint32_t)probe->last_query);put32(record+28,probe->cleanup_failed?1:0);put32(record+32,probe->bytes+40);
 if(probe->output!=INVALID_HANDLE_VALUE){
  if(!write_owned(probe,record,sizeof(record))||!FlushFileBuffers(probe->output))rc=1;
  if(!CloseHandle(probe->output))rc=1;probe->output=INVALID_HANDLE_VALUE;
 }
 printf("COH_NT_PROBE_RESULT pid=%lu mode=%lu complete=%d rows=%lu batches=%lu input_cleanup_failed=%d bytes=%lu\n",
  (unsigned long)GetCurrentProcessId(),(unsigned long)probe->mode,rc==0,(unsigned long)probe->rows,
  (unsigned long)probe->batches,probe->cleanup_failed,(unsigned long)probe->bytes);fflush(stdout);
 return rc;
}
int main(int argc,char **argv) {
 CohProbe probe;HMODULE nt,kernel;CohLiveNtOpenFile nt_open;CohLiveNtQueryInformationFile nt_info;
 CohLiveRtlDosPath rtl_path;CohLiveRtlFreeString rtl_free;CohLiveGetFinalPath final_path;CohProbeNtQueryDirectoryFile query;
 CohLiveUnicodeString name,mask;CohLiveObjectAttributes attributes;CohLiveIoStatus io;LARGE_INTEGER internal;
 WCHAR wide[1024],wildcard[2]={'*',0};char input[1024],output[1024],final[1033];unsigned char buffer[NT_PROBE_BUFFER_BYTES];
 DWORD length;uint32_t count;size_t i;int step=0;
 memset(&probe,0,sizeof(probe));probe.input=probe.output=INVALID_HANDLE_VALUE;
 probe.open_status=probe.info_status=probe.last_query=(LONG)0xc0000001u;
 if((argc!=4&&argc!=5)||(!strcmp(argv[1],"stock")?0:strcmp(argv[1],"share-block"))||
    (argc==5&&strcmp(argv[4],"step"))||!ascii_absolute(argv[2])||!ascii_absolute(argv[3]))return 64;
 probe.mode=!strcmp(argv[1],"stock")?1:2;step=argc==5;
 length=GetFullPathNameA(argv[2],sizeof(input),input,NULL);if(!length||length>=sizeof(input))return 64;
 length=GetFullPathNameA(argv[3],sizeof(output),output,NULL);if(!length||length>=sizeof(output)||same_or_descendant(input,output))return 64;
 probe.path=input;
 probe.output=CreateFileA(output,GENERIC_WRITE,FILE_SHARE_READ,NULL,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,NULL);
 if(probe.output==INVALID_HANDLE_VALUE)return 65;
 nt=GetModuleHandleA("ntdll.dll");kernel=GetModuleHandleA("kernel32.dll");
 if(!nt||!kernel){probe.failed=1;return finish(&probe);}
 nt_open=(CohLiveNtOpenFile)GetProcAddress(nt,"NtOpenFile");nt_info=(CohLiveNtQueryInformationFile)GetProcAddress(nt,"NtQueryInformationFile");
 rtl_path=(CohLiveRtlDosPath)GetProcAddress(nt,"RtlDosPathNameToNtPathName_U");rtl_free=(CohLiveRtlFreeString)GetProcAddress(nt,"RtlFreeUnicodeString");
 final_path=(CohLiveGetFinalPath)GetProcAddress(kernel,"GetFinalPathNameByHandleA");query=(CohProbeNtQueryDirectoryFile)GetProcAddress(nt,"NtQueryDirectoryFile");
 if(!nt_open||!nt_info||!rtl_path||!rtl_free||!final_path||!query){probe.failed=1;return finish(&probe);}
 for(i=0;input[i];i++)wide[i]=(WCHAR)(unsigned char)input[i];wide[i]=0;
 memset(&name,0,sizeof(name));if(!rtl_path(wide,&name,NULL,NULL)){probe.failed=1;return finish(&probe);}
 memset(&attributes,0,sizeof(attributes));attributes.Length=sizeof(attributes);attributes.ObjectName=&name;attributes.Attributes=0x40;
 memset(&io,0,sizeof(io));probe.open_status=nt_open(&probe.input,0x100001,&attributes,&io,probe.mode==2?0:3,0x4021);rtl_free(&name);
 memset(final,0,sizeof(final));
 if(probe.open_status!=0||!probe.input||probe.input==INVALID_HANDLE_VALUE){probe.failed=1;header(&probe,input,final);return finish(&probe);}
 memset(&io,0,sizeof(io));memset(&internal,0,sizeof(internal));probe.info_status=nt_info(probe.input,&io,&internal,sizeof(internal),6);
 if(probe.info_status!=0||io.Information!=8){probe.failed=1;header(&probe,input,final);return finish(&probe);}
 probe.inode=(uint64_t)internal.QuadPart;length=final_path(probe.input,final,sizeof(final),0);
 if(!probe.inode||!length||length>=sizeof(final)){probe.failed=1;final[0]=0;header(&probe,input,final);return finish(&probe);}
 if(!header(&probe,input,final)){probe.failed=1;return finish(&probe);}
 if(probe.mode==2){printf("COH_NT_SHARE_READY pid=%lu inode=%llu\n",(unsigned long)GetCurrentProcessId(),(unsigned long long)probe.inode);fflush(stdout);
  if(getchar()!='C')probe.failed=1;return finish(&probe);}
 mask.Length=2;mask.MaximumLength=4;mask.Buffer=wildcard;
 for(;;){memset(&io,0,sizeof(io));memset(buffer,0,sizeof(buffer));
  probe.last_query=query(probe.input,NULL,NULL,NULL,&io,buffer,sizeof(buffer),3,0,&mask,probe.batches==0?1:0);
  if(probe.last_query==NT_PROBE_STATUS_NO_MORE_FILES){if(io.Information)probe.failed=1;break;}
  if(probe.last_query!=0||io.Information>sizeof(buffer)||!batch_rows(buffer,(uint32_t)io.Information,&count)||
     count>NT_PROBE_MAX_ROWS-probe.rows||probe.batches==NT_PROBE_MAX_BATCHES){probe.failed=1;break;}
  if(!batch(&probe,buffer,(uint32_t)io.Information,count)){probe.failed=1;break;}
  probe.rows+=count;probe.batches++;
  if(step){printf("COH_NT_BATCH_READY pid=%lu batch=%lu rows=%lu bytes=%lu\n",(unsigned long)GetCurrentProcessId(),
    (unsigned long)probe.batches,(unsigned long)probe.rows,(unsigned long)io.Information);fflush(stdout);
   if(getchar()!='N'){probe.failed=1;break;}}
 }
 return finish(&probe);
}
