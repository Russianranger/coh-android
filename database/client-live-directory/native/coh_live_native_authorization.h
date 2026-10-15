/* Private Game-only Wine directory authorization. Runtime recipe unqualified
 * until actual SDK/Wine/Android fixtures pass; this source never enables it. */
#ifndef COH_LIVE_NATIVE_AUTHORIZATION_H
#define COH_LIVE_NATIVE_AUTHORIZATION_H
#include "coh_live_native_policy.h"
#include <windows.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
typedef struct CohLiveUnicodeString {USHORT Length,MaximumLength;PWSTR Buffer;} CohLiveUnicodeString;
typedef struct CohLiveObjectAttributes {
 ULONG Length;HANDLE RootDirectory;CohLiveUnicodeString *ObjectName;
 ULONG Attributes;PVOID SecurityDescriptor;PVOID SecurityQualityOfService;
} CohLiveObjectAttributes;
typedef struct CohLiveIoStatus {
 union {LONG Status;PVOID Pointer;} value;ULONG_PTR Information;
} CohLiveIoStatus;
#if defined(_WIN32)
typedef char CohLivePointerAbiMustBe32[(sizeof(void*)==4)?1:-1];
typedef char CohLiveUnicodeAbiMustBe8[(sizeof(CohLiveUnicodeString)==8)?1:-1];
typedef char CohLiveObjectAbiMustBe24[(sizeof(CohLiveObjectAttributes)==24)?1:-1];
typedef char CohLiveIoAbiMustBe8[(sizeof(CohLiveIoStatus)==8)?1:-1];
#endif
typedef LONG (WINAPI *CohLiveNtOpenFile)(PHANDLE,ULONG,CohLiveObjectAttributes*,CohLiveIoStatus*,ULONG,ULONG);
typedef LONG (WINAPI *CohLiveNtQueryInformationFile)(HANDLE,CohLiveIoStatus*,PVOID,ULONG,ULONG);
typedef BOOLEAN (WINAPI *CohLiveRtlDosPath)(PCWSTR,CohLiveUnicodeString*,PWSTR*,PVOID);
typedef VOID (WINAPI *CohLiveRtlFreeString)(CohLiveUnicodeString*);
typedef DWORD (WINAPI *CohLiveGetFinalPath)(HANDLE,LPSTR,DWORD,DWORD);
typedef struct CohLiveAuthorizedDirectory {
 HANDLE handle;uint64_t inode;LONG open_status,query_status;
 DWORD final_path_error,close_error;int cleanup_failed;char original_dos[COH_LIVE_GUEST_PATH_CAP+8u];
 char final_guest[COH_LIVE_GUEST_PATH_CAP];
} CohLiveAuthorizedDirectory;
static int cohLiveAuthorizeDirectory(const char *basepath,CohLiveAuthorizedDirectory *out) {
 HMODULE nt,kernel;CohLiveNtOpenFile nt_open;CohLiveNtQueryInformationFile nt_query;
 CohLiveRtlDosPath rtl_path;CohLiveRtlFreeString rtl_free;CohLiveGetFinalPath final_path;
 WCHAR dos[COH_LIVE_GUEST_PATH_CAP+8u];char final_dos[COH_LIVE_GUEST_PATH_CAP+8u];
 CohLiveUnicodeString name;CohLiveObjectAttributes attributes;CohLiveIoStatus io;
 LARGE_INTEGER internal;DWORD len,last_error=GetLastError();size_t i;int saved_errno=errno,ok=0;
 if(!out)goto done;
 memset(out,0,sizeof(*out));out->handle=INVALID_HANDLE_VALUE;
 out->open_status=out->query_status=(LONG)0xc0000001u;
 if(!basepath)goto done;
 len=GetFullPathNameA(basepath,sizeof(out->original_dos),out->original_dos,NULL);
 if(!len||len>=sizeof(out->original_dos)||!cohLiveGuestFromDos(out->original_dos,out->final_guest))goto done;
 for(i=0;i<len;i++)dos[i]=(WCHAR)(unsigned char)out->original_dos[i];dos[len]=0;
 nt=GetModuleHandleA("ntdll.dll");kernel=GetModuleHandleA("kernel32.dll");
 if(!nt||!kernel)goto done;
 nt_open=(CohLiveNtOpenFile)GetProcAddress(nt,"NtOpenFile");
 nt_query=(CohLiveNtQueryInformationFile)GetProcAddress(nt,"NtQueryInformationFile");
 rtl_path=(CohLiveRtlDosPath)GetProcAddress(nt,"RtlDosPathNameToNtPathName_U");
 rtl_free=(CohLiveRtlFreeString)GetProcAddress(nt,"RtlFreeUnicodeString");
 final_path=(CohLiveGetFinalPath)GetProcAddress(kernel,"GetFinalPathNameByHandleA");
 if(!nt_open||!nt_query||!rtl_path||!rtl_free||!final_path)goto done;
 memset(&name,0,sizeof(name));
 if(!rtl_path(dos,&name,NULL,NULL))goto done;
 memset(&attributes,0,sizeof(attributes));attributes.Length=sizeof(attributes);
 attributes.ObjectName=&name;attributes.Attributes=0x40u; /* OBJ_CASE_INSENSITIVE */
 memset(&io,0,sizeof(io));
 /* Exact pinned Wine FindFirst directory authorization, not GENERIC_READ
  * of every leaf and not a POSIX permission approximation. */
 out->open_status=nt_open(&out->handle,0x00100001u,&attributes,&io,3u,0x00004021u);
 rtl_free(&name);
 if(out->open_status!=0||out->handle==INVALID_HANDLE_VALUE||!out->handle)goto done;
 memset(&io,0,sizeof(io));memset(&internal,0,sizeof(internal));
 out->query_status=nt_query(out->handle,&io,&internal,sizeof(internal),6u); /* FileInternalInformation */
 if(out->query_status!=0||io.Information!=sizeof(internal))goto done;
 out->inode=(uint64_t)internal.QuadPart;
 if(!out->inode)goto done;
 len=final_path(out->handle,final_dos,sizeof(final_dos),0u); /* normalized DOS object name */
 out->final_path_error=GetLastError();
 if(!len||len>=sizeof(final_dos)||strncmp(final_dos,"\\\\?\\",4)||
    !cohLiveGuestFromDos(final_dos+4,out->final_guest))goto done;
 ok=1;
done:
 if(!ok&&out&&out->handle!=INVALID_HANDLE_VALUE&&out->handle) {
  if(CloseHandle(out->handle))out->handle=INVALID_HANDLE_VALUE;
  else {out->cleanup_failed=1;out->close_error=GetLastError();}
 }
 SetLastError(last_error);errno=saved_errno;return ok;
}
static int cohLiveCloseAuthorized(CohLiveAuthorizedDirectory *directory) {
 DWORD saved=GetLastError();int saved_errno=errno,ok=1;
 if(directory&&directory->cleanup_failed)ok=0;
 else if(directory&&directory->handle!=INVALID_HANDLE_VALUE&&directory->handle) {
  ok=CloseHandle(directory->handle)!=0;
  if(ok)directory->handle=INVALID_HANDLE_VALUE;
  else {directory->cleanup_failed=1;directory->close_error=GetLastError();}
 }
 SetLastError(saved);errno=saved_errno;return ok;
}
#endif
