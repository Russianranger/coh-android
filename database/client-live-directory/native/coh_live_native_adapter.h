/* Dormant private Game-only consumer. Actual runtime/source registration and
 * Android namespace parity remain qualification gates outside this header. */
#ifndef COH_LIVE_NATIVE_ADAPTER_H
#define COH_LIVE_NATIVE_ADAPTER_H
#include "coh_live_native_authorization.h"
#include "coh_live_transport.h"
#include <winsock2.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <limits.h>
typedef char CohLiveWfdSizeMustBe320[(sizeof(WIN32_FIND_DATAA)==320)?1:-1];
typedef struct CohLiveNativeState {
 DWORD owner_thread,owner_pid;void *cache;int attempted,enabled,stopped,wsa_owned;
 SOCKET socket;int socket_error,socket_close_failed;uint32_t directory_sequence;
 uint64_t device;char guest_root[COH_LIVE_GUEST_PATH_CAP];char descriptor[65];
 CohLiveTransport transport;
} CohLiveNativeState;
typedef struct CohLiveNativeDirectory {
 CohLiveAuthorizedDirectory authorized;uint32_t handle;uint64_t rows;
} CohLiveNativeDirectory;
static CohLiveNativeState coh_live_native = {.socket=INVALID_SOCKET};
static int32_t cohLiveSocketRead(void *context,unsigned char *out,uint32_t count) {
 CohLiveNativeState *state=(CohLiveNativeState*)context;int result,saved_errno=errno;DWORD saved=GetLastError();
 result=recv(state->socket,(char*)out,(int)count,0);
 if(result==SOCKET_ERROR)state->socket_error=WSAGetLastError();
 SetLastError(saved);errno=saved_errno;return result;
}
static int32_t cohLiveSocketWrite(void *context,const unsigned char *data,uint32_t count) {
 CohLiveNativeState *state=(CohLiveNativeState*)context;int result,saved_errno=errno;DWORD saved=GetLastError();
 result=send(state->socket,(const char*)data,(int)count,0);
 if(result==SOCKET_ERROR)state->socket_error=WSAGetLastError();
 SetLastError(saved);errno=saved_errno;return result;
}
static void cohLiveSocketClose(void *context) {
 CohLiveNativeState *state=(CohLiveNativeState*)context;int saved_errno=errno;DWORD saved=GetLastError();
 if(state->socket!=INVALID_SOCKET) {
  shutdown(state->socket,SD_BOTH);
  if(closesocket(state->socket)==SOCKET_ERROR) {
   state->socket_error=WSAGetLastError();state->socket_close_failed=1;
  }else state->socket=INVALID_SOCKET;
 }
 SetLastError(saved);errno=saved_errno;
}
static void *cohLiveNativeAllocate(void *context,size_t bytes) {(void)context;return malloc(bytes);}
static void cohLiveNativeRelease(void *context,void *memory) {(void)context;free(memory);}
static void cohLiveNativeReport(const char *event,const char *path,LONG status) {
 int saved_errno=errno;DWORD saved=GetLastError();
 printf("COH_LIVE_DIRECTORY event=%s pid=%lu thread=%lu native_status=%ld socket_error=%d socket_close_failed=%d rows=%llu reason=%d backend_status=%lu backend_error=%lu path=%s\n",
  event,(unsigned long)GetCurrentProcessId(),(unsigned long)GetCurrentThreadId(),(long)status,
  coh_live_native.socket_error,coh_live_native.socket_close_failed,(unsigned long long)coh_live_native.transport.rows_returned,
  (int)coh_live_native.transport.reason,(unsigned long)coh_live_native.transport.backend_status,
  (unsigned long)coh_live_native.transport.backend_error,path?path:"");fflush(stdout);
 SetLastError(saved);errno=saved_errno;
}
void FolderCacheLiveDirectorySetMainThread(void) {
 int saved_errno=errno;DWORD saved=GetLastError();
 if(!coh_live_native.owner_thread) {
  coh_live_native.owner_thread=GetCurrentThreadId();coh_live_native.owner_pid=GetCurrentProcessId();
  coh_live_native.socket=INVALID_SOCKET;
 }
 SetLastError(saved);errno=saved_errno;
}
static void cohLiveNativeFatal(const char *event,const char *path,LONG status);
static void cohLiveNativeRegisterCache(void *cache) {
 const char *enabled=getenv("COH_CLIENT_LIVE_DIRECTORY"),*endpoint,*recipe,*root,*descriptor;
 unsigned char operation[16],nonce[32],descriptor_bytes[32];unsigned short port;
 struct sockaddr_in address;WSADATA data;CohLiveTransportIo io;
 int no_delay=1,saved_errno=errno;DWORD saved=GetLastError();
 if(coh_live_native.attempted||coh_live_native.stopped||!enabled||strcmp(enabled,"1"))goto done;
 coh_live_native.attempted=1;
 if(!coh_live_native.owner_thread||GetCurrentThreadId()!=coh_live_native.owner_thread||
    GetCurrentProcessId()!=coh_live_native.owner_pid)goto declined;
 endpoint=getenv("COH_CLIENT_LIVE_DIRECTORY_ENDPOINT");recipe=getenv("COH_CLIENT_LIVE_DIRECTORY_RECIPE");
 root=getenv("COH_CLIENT_LIVE_DIRECTORY_GUEST_ROOT");descriptor=getenv("COH_CLIENT_LIVE_DIRECTORY_DESCRIPTOR");
 if(!recipe||strcmp(recipe,COH_LIVE_NATIVE_RECIPE)||!cohLiveEndpoint(endpoint,&port)||
    !cohLiveGuestPathValid(root)||!cohLiveAsciiHex(descriptor,descriptor_bytes,32)||
    !cohLiveAsciiHex(getenv("COH_CLIENT_LIVE_DIRECTORY_SESSION"),operation,16)||
    !cohLiveAsciiHex(getenv("COH_CLIENT_LIVE_DIRECTORY_AUTH"),nonce,32)||
    !cohLiveDecimalU64(getenv("COH_CLIENT_LIVE_DIRECTORY_DEVICE"),&coh_live_native.device))goto declined;
 if(WSAStartup(MAKEWORD(2,2),&data)!=0)goto declined;
 coh_live_native.wsa_owned=1;
 coh_live_native.socket=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
 if(coh_live_native.socket==INVALID_SOCKET) {coh_live_native.socket_error=WSAGetLastError();goto declined;}
 if(setsockopt(coh_live_native.socket,IPPROTO_TCP,TCP_NODELAY,(const char*)&no_delay,sizeof(no_delay))==SOCKET_ERROR) {
  coh_live_native.socket_error=WSAGetLastError();goto declined;
 }
 memset(&address,0,sizeof(address));address.sin_family=AF_INET;
 address.sin_addr.s_addr=htonl(0x7f000001u);address.sin_port=htons(port);
 if(connect(coh_live_native.socket,(const struct sockaddr*)&address,sizeof(address))==SOCKET_ERROR) {
  coh_live_native.socket_error=WSAGetLastError();goto declined;
 }
 memset(&io,0,sizeof(io));io.context=&coh_live_native;io.read=cohLiveSocketRead;io.write=cohLiveSocketWrite;
 io.close=cohLiveSocketClose;io.allocate=cohLiveNativeAllocate;io.release=cohLiveNativeRelease;
 if(cohLiveTransportInit(&coh_live_native.transport,&io,operation,nonce)!=COH_TRANSPORT_OK)goto declined;
 strcpy(coh_live_native.guest_root,root);strcpy(coh_live_native.descriptor,descriptor);
 coh_live_native.cache=cache;coh_live_native.enabled=1;
 cohLiveNativeReport("registered_startup_only",root,0);goto done;
declined:
 cohLiveSocketClose(&coh_live_native);
 if(coh_live_native.socket_close_failed)cohLiveNativeFatal("terminal_registration_socket_cleanup",NULL,0);
 if(coh_live_native.wsa_owned){WSACleanup();coh_live_native.wsa_owned=0;}
 cohLiveNativeReport("initial_registration_decline",NULL,0);
done:
 memset(operation,0,sizeof(operation));memset(nonce,0,sizeof(nonce));
 SetLastError(saved);errno=saved_errno;
}
static void cohLiveNativeFatal(const char *event,const char *path,LONG status) {
 cohLiveNativeReport(event,path,status);cohLiveTransportShutdown(&coh_live_native.transport);
 if(coh_live_native.wsa_owned){WSACleanup();coh_live_native.wsa_owned=0;}
 fflush(stderr);fflush(stdout);ExitProcess(77);
}
void FolderCacheLiveDirectoryStop(void) {
 int saved_errno=errno;DWORD saved=GetLastError();
 if(coh_live_native.enabled) {
  cohLiveTransportShutdown(&coh_live_native.transport);
  if(coh_live_native.socket_close_failed)cohLiveNativeFatal("terminal_startup_socket_cleanup",coh_live_native.guest_root,0);
  cohLiveNativeReport("startup_scope_closed_zoning_stock",coh_live_native.guest_root,0);
 }
 coh_live_native.enabled=0;coh_live_native.stopped=1;
 if(coh_live_native.wsa_owned){WSACleanup();coh_live_native.wsa_owned=0;}
 SetLastError(saved);errno=saved_errno;
}
/* A foreign cache or nonselected branch always retains the stock route. A
 * violated guard for an admitted branch after any live rows is terminal. */
static int cohLiveNativeFirst(void *cache,void *global_cache,const char *basepath,
 const char *gdd,int gdd_count,int virtual_location,int callbacks_absent,
 int updates_disabled,int dev_dynamic,int all_folders,int dev_data,
 CohLiveNativeDirectory **out,WIN32_FIND_DATAA *wfd) {
 CohLiveNativeDirectory *directory=NULL;char gdd_dos[COH_LIVE_GUEST_PATH_CAP+8u],gdd_guest[COH_LIVE_GUEST_PATH_CAP];
 char requested_dos[COH_LIVE_GUEST_PATH_CAP+8u],requested_guest[COH_LIVE_GUEST_PATH_CAP],selected[COH_LIVE_GUEST_PATH_CAP];
 unsigned char token[16];const unsigned char *row=NULL;DWORD len,saved=GetLastError();int result=-1,saved_errno=errno;
 *out=NULL;
 if(!coh_live_native.enabled||coh_live_native.stopped||cache!=global_cache||cache!=coh_live_native.cache)goto done;
 len=GetFullPathNameA(gdd,sizeof(gdd_dos),gdd_dos,NULL);
 if(!len||len>=sizeof(gdd_dos)||!cohLiveGuestFromDos(gdd_dos,gdd_guest))goto done;
 len=GetFullPathNameA(basepath,sizeof(requested_dos),requested_dos,NULL);
 if(!len||len>=sizeof(requested_dos)||!cohLiveGuestFromDos(requested_dos,requested_guest)||
    !cohLiveSelectedGuestPath(coh_live_native.guest_root,gdd_guest,requested_guest,selected))goto done;
 if(gdd_count!=1||virtual_location!=0||!callbacks_absent||!updates_disabled||!dev_dynamic||!all_folders||!dev_data||
    GetCurrentThreadId()!=coh_live_native.owner_thread||GetCurrentProcessId()!=coh_live_native.owner_pid)goto failed;
 directory=(CohLiveNativeDirectory*)calloc(1,sizeof(*directory));
 if(!directory)goto failed;directory->authorized.handle=INVALID_HANDLE_VALUE;
 if(!cohLiveAuthorizeDirectory(basepath,&directory->authorized)) {
  cohLiveNativeReport("native_directory_authorization_refusal",basepath,directory->authorized.open_status);
  goto failed;
 }
 if(!cohLiveAuthorizedFinalScope(coh_live_native.guest_root,requested_guest,directory->authorized.final_guest))goto failed;
 if(coh_live_native.directory_sequence==UINT32_MAX)goto failed;
 memcpy(token,coh_live_native.transport.operation,16);
 {uint32_t sequence=++coh_live_native.directory_sequence;unsigned int i;
  for(i=0;i<4;i++)token[12+i]=(unsigned char)(sequence>>(i*8));}
 result=cohLiveTransportOpen(&coh_live_native.transport,selected,token,coh_live_native.device,directory->authorized.inode,&directory->handle);
 if(result!=COH_TRANSPORT_OK)goto failed;
 result=cohLiveTransportNext(&coh_live_native.transport,directory->handle,&row);
 if(result<0)goto failed;
 if(result==COH_TRANSPORT_OK){memcpy(wfd,row,320);directory->rows++;}
 *out=directory;goto done;
failed:
 if(directory){
  int authorization_closed;
  if(directory->handle)cohLiveTransportClose(&coh_live_native.transport,&directory->handle);
  authorization_closed=cohLiveCloseAuthorized(&directory->authorized);free(directory);
  if(!authorization_closed)cohLiveNativeFatal("terminal_native_authorization_cleanup",basepath,result);
 }
 if(result==COH_TRANSPORT_TERMINAL||coh_live_native.transport.rows_returned)
  cohLiveNativeFatal("terminal_directory_admission",basepath,result);
 cohLiveNativeReport("initial_directory_decline",basepath,result);
 cohLiveTransportShutdown(&coh_live_native.transport);coh_live_native.enabled=0;
 if(coh_live_native.socket_close_failed)cohLiveNativeFatal("terminal_initial_socket_cleanup",basepath,result);
 if(coh_live_native.wsa_owned){WSACleanup();coh_live_native.wsa_owned=0;}
 result=COH_TRANSPORT_INITIAL_DECLINE;
done:
 SetLastError(saved);errno=saved_errno;return result;
}
static int cohLiveNativeNext(CohLiveNativeDirectory *directory,WIN32_FIND_DATAA *wfd) {
 const unsigned char *row;int saved_errno=errno,result;DWORD saved=GetLastError();
 result=cohLiveTransportNext(&coh_live_native.transport,directory->handle,&row);
 if(result<0)cohLiveNativeFatal("terminal_directory_batch",directory->authorized.original_dos,result);
 if(result==COH_TRANSPORT_OK){memcpy(wfd,row,320);directory->rows++;}
 SetLastError(saved);errno=saved_errno;return result;
}
static void cohLiveNativeClose(CohLiveNativeDirectory *directory) {
 int saved_errno=errno,result,authorization_closed;DWORD saved=GetLastError();
 result=cohLiveTransportClose(&coh_live_native.transport,&directory->handle);
 authorization_closed=cohLiveCloseAuthorized(&directory->authorized);
 if(result!=COH_TRANSPORT_OK||!authorization_closed)
  cohLiveNativeFatal("terminal_directory_close",directory->authorized.original_dos,result);
 free(directory);SetLastError(saved);errno=saved_errno;
}
#endif
