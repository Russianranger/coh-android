"""API-boundary controls with a fake Windows SDK, not Windows execution."""
import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
WINDOWS = r'''
#ifndef TEST_WINDOWS_H
#define TEST_WINDOWS_H
#include <stdint.h>
#include <stddef.h>
#define WINAPI
typedef uint32_t DWORD,ULONG;typedef int32_t LONG;typedef uint16_t USHORT,WCHAR;
typedef unsigned char BOOLEAN;typedef void *PVOID,*HANDLE,*HMODULE;typedef HANDLE *PHANDLE;
typedef uintptr_t ULONG_PTR;typedef WCHAR *PWSTR;typedef const WCHAR *PCWSTR;typedef char *LPSTR;
typedef void VOID;typedef union {int64_t QuadPart;} LARGE_INTEGER;
#define INVALID_HANDLE_VALUE ((HANDLE)(intptr_t)-1)
DWORD GetLastError(void);void SetLastError(DWORD);
DWORD GetFullPathNameA(const char*,DWORD,char*,char**);
HMODULE GetModuleHandleA(const char*);void *GetProcAddress(HMODULE,const char*);
int CloseHandle(HANDLE);
#endif
'''
FIXTURE = r'''
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include "coh_live_native_authorization.h"
static int stage,closes,frees,open_calls,query_calls;static DWORD last_error;
static ULONG access_observed,share_observed,options_observed,attributes_observed;
static uint64_t observed_inode;static char final_path[1040];
DWORD GetLastError(void){return last_error;}void SetLastError(DWORD v){last_error=v;}
DWORD GetFullPathNameA(const char *p,DWORD count,char *out,char **unused){
 size_t n=p?strlen(p):0;(void)unused;last_error=101;errno=102;
 if(stage==1)return 0;if(n>=count)return (DWORD)n+1;memcpy(out,p,n+1);return (DWORD)n;
}
HMODULE GetModuleHandleA(const char *name){(void)name;return stage==2?NULL:(HMODULE)(uintptr_t)1;}
static BOOLEAN fake_path(PCWSTR p,CohLiveUnicodeString *name,PWSTR *part,PVOID unused){
 size_t n=0;(void)part;(void)unused;if(stage==4)return 0;while(p[n])n++;
 name->Buffer=(PWSTR)malloc((n+1)*sizeof(WCHAR));memcpy(name->Buffer,p,(n+1)*sizeof(WCHAR));
 name->Length=(USHORT)(n*sizeof(WCHAR));name->MaximumLength=name->Length+2;return 1;
}
static void fake_free(CohLiveUnicodeString *name){frees++;free(name->Buffer);name->Buffer=NULL;}
static LONG fake_open(PHANDLE h,ULONG access,CohLiveObjectAttributes *a,CohLiveIoStatus *io,ULONG share,ULONG options){
 (void)io;open_calls++;access_observed=access;share_observed=share;options_observed=options;attributes_observed=a->Attributes;
 if(stage==5)return (LONG)0xc0000043u;*h=(HANDLE)(uintptr_t)27;return stage==14?1:0;
}
static LONG fake_query(HANDLE h,CohLiveIoStatus *io,PVOID result,ULONG bytes,ULONG type){
 query_calls++;if(h!=(HANDLE)(uintptr_t)27||bytes!=8||type!=6)abort();
 if(stage==6||stage==13)return (LONG)0xc0000022u;((LARGE_INTEGER*)result)->QuadPart=(int64_t)observed_inode;
 io->Information=stage==7?4:8;return stage==15?0x103:0;
}
static DWORD fake_final(HANDLE h,LPSTR out,DWORD count,DWORD flags){
 size_t n=strlen(final_path);if(h!=(HANDLE)(uintptr_t)27||flags)abort();
 if(stage==8)return 0;if(n>=count)return (DWORD)n+1;memcpy(out,final_path,n+1);return (DWORD)n;
}
void *GetProcAddress(HMODULE module,const char *name){(void)module;if(stage==3)return NULL;
 if(!strcmp(name,"NtOpenFile"))return (void*)fake_open;
 if(!strcmp(name,"NtQueryInformationFile"))return (void*)fake_query;
 if(!strcmp(name,"RtlDosPathNameToNtPathName_U"))return (void*)fake_path;
 if(!strcmp(name,"RtlFreeUnicodeString"))return (void*)fake_free;
 if(!strcmp(name,"GetFinalPathNameByHandleA"))return (void*)fake_final;return NULL;
}
int CloseHandle(HANDLE h){if(h!=(HANDLE)(uintptr_t)27)abort();closes++;last_error=777;errno=778;return stage==10||stage==13?0:1;}
int execute(int failure,const char *input,const char *final,uint64_t inode){
 CohLiveAuthorizedDirectory out;int ok;
 stage=failure;closes=frees=open_calls=query_calls=0;observed_inode=inode;
 if(strlen(final)>=sizeof(final_path))abort();strcpy(final_path,final);
 last_error=51;errno=52;ok=cohLiveAuthorizeDirectory(input,&out);
 if(GetLastError()!=51||errno!=52)abort();
 if(ok){if(out.inode!=inode||strcmp(out.original_dos,input))abort();
   if(!cohLiveCloseAuthorized(&out)){if(stage!=10)abort();ok=-1;}
   if(GetLastError()!=51||errno!=52)abort();
   if(stage==10){if(!out.cleanup_failed||out.handle!=(HANDLE)(uintptr_t)27)abort();}
   else if(out.handle!=INVALID_HANDLE_VALUE)abort();
 }else if(stage==13){if(!out.cleanup_failed||out.handle!=(HANDLE)(uintptr_t)27||cohLiveCloseAuthorized(&out)!=0||closes!=1)abort();}
 else if(out.handle!=INVALID_HANDLE_VALUE)abort();
 return ok;
}
int fact(int index){switch(index){case0:return closes;case1:return frees;case2:return open_calls;case3:return query_calls;
 case4:return access_observed;case5:return share_observed;case6:return options_observed;case7:return attributes_observed;}return -1;}
'''.replace('case0', 'case 0').replace('case1', 'case 1').replace('case2', 'case 2').replace('case3', 'case 3').replace('case4', 'case 4').replace('case5', 'case 5').replace('case6', 'case 6').replace('case7', 'case 7')


class NativeAuthorization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        path = Path(cls.temp.name)
        (path/'windows.h').write_text(WINDOWS)
        (path/'fixture.c').write_text(FIXTURE)
        subprocess.run(['cc','-std=c99','-O2','-shared','-fPIC','-Wall','-Wextra','-Werror',
                        '-Wno-unused-function','-Wno-misleading-indentation','-I',str(path),'-I',str(ROOT),
                        str(path/'fixture.c'),'-o',str(path/'fixture.so')], check=True)
        cls.lib = ctypes.CDLL(str(path/'fixture.so'))
        cls.lib.execute.argtypes = [ctypes.c_int,ctypes.c_char_p,ctypes.c_char_p,ctypes.c_uint64]
        cls.lib.execute.restype = ctypes.c_int
        cls.lib.fact.argtypes = [ctypes.c_int]
        cls.lib.fact.restype = ctypes.c_int

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def invoke(self,stage=0,original=b'Z:\\state\\operation\\data\\SCRIPTS.LOC',
               final=b'\\\\?\\Z:\\state\\operation\\data\\scripts.loc',inode=123):
        return self.lib.execute(stage,original,final,inode)

    def test_exact_native_nt_authorization_and_full_u64_inode(self):
        self.assertEqual(self.invoke(inode=2**63+11),1)
        self.assertEqual([self.lib.fact(i) for i in range(8)], [1,1,1,1,0x100001,3,0x4021,0x40])

    def test_failures_before_open_never_create_or_close_native_handle(self):
        for stage in (1,2,3,4):
            self.assertEqual(self.invoke(stage),0)
            self.assertEqual(self.lib.fact(0),0)
            self.assertEqual(self.lib.fact(2),0)

    def test_sharing_refusal_preserves_nt_result_and_releases_path_buffer(self):
        self.assertEqual(self.invoke(5),0)
        self.assertEqual([self.lib.fact(i) for i in range(4)], [0,1,1,0])

    def test_information_and_final_path_failures_release_held_handle(self):
        for stage in (6,7,8):
            self.assertEqual(self.invoke(stage),0)
            self.assertEqual([self.lib.fact(i) for i in range(2)], [1,1])
        self.assertEqual(self.invoke(inode=0),0)
        self.assertEqual(self.lib.fact(0),1)

    def test_positive_nt_status_is_never_completed_authorization(self):
        for stage in (14,15):
            self.assertEqual(self.invoke(stage),0)
            self.assertEqual(self.lib.fact(0),1)

    def test_unproved_foreign_drive_or_object_path_refuses(self):
        for final in (b'Z:\\state\\data',b'\\\\?\\X:\\data',b'\\\\?\\Z:\\state\\..\\data',b'\\\\server\\data'):
            self.assertEqual(self.invoke(final=final),0)
            self.assertEqual(self.lib.fact(0),1)
        self.assertEqual(self.invoke(original=b'X:\\data\\fx'),0)
        self.assertEqual(self.lib.fact(2),0)

    def test_close_failure_is_observable_and_restores_caller_errors(self):
        self.assertEqual(self.invoke(10),-1)
        self.assertEqual(self.lib.fact(0),1)
        self.assertEqual(self.invoke(13),0)
        self.assertEqual(self.lib.fact(0),1)


if __name__=='__main__':
    unittest.main()
