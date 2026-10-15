"""Exercise real adapter+protocol with fake SDK calls, never claim Wine."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_live_native_authorization import WINDOWS, FIXTURE

ROOT = Path(__file__).resolve().parent
TRANSPORT = ROOT.parent/'transport'
SDK = WINDOWS.replace('#endif', r'''
typedef struct {DWORD low,high;} FILETIME;
typedef struct {DWORD dwFileAttributes;FILETIME ftCreationTime,ftLastAccessTime,ftLastWriteTime;
 DWORD nFileSizeHigh,nFileSizeLow,dwReserved0,dwReserved1;char cFileName[260],cAlternateFileName[14];} WIN32_FIND_DATAA;
DWORD GetCurrentThreadId(void);DWORD GetCurrentProcessId(void);void ExitProcess(DWORD);
#endif
''')
WINSOCK = r'''
#ifndef FAKE_WINSOCK_H
#define FAKE_WINSOCK_H
#include <stdint.h>
typedef int SOCKET;typedef struct {int unused;} WSADATA;
struct in_addr {uint32_t s_addr;};
struct sockaddr_in {short sin_family;unsigned short sin_port;struct in_addr sin_addr;char zero[8];};
struct sockaddr {short family;char rest[14];};
#define INVALID_SOCKET (-1)
#define SOCKET_ERROR (-1)
#define AF_INET 2
#define SOCK_STREAM 1
#define IPPROTO_TCP 6
#define TCP_NODELAY 1
#define SD_BOTH 2
#define MAKEWORD(a,b) ((unsigned short)((a)|((b)<<8)))
int WSAStartup(unsigned short,WSADATA*);int WSACleanup(void);int WSAGetLastError(void);
SOCKET socket(int,int,int);int connect(SOCKET,const struct sockaddr*,int);
int send(SOCKET,const char*,int,int);int recv(SOCKET,char*,int,int);
int shutdown(SOCKET,int);int closesocket(SOCKET);
int setsockopt(SOCKET,int,int,const char*,int);
unsigned short htons(unsigned short);uint32_t htonl(uint32_t);
#endif
'''
ADAPTER = r'''
#include "coh_live_native_adapter.h"
static unsigned char request[1120],response[28000];static unsigned int request_bytes,response_bytes,response_taken;
static int scenario,commands[4],socket_closes,wsa_starts,wsa_ends,no_delay_calls;static DWORD current_thread=200;
DWORD GetCurrentThreadId(void){return current_thread;}DWORD GetCurrentProcessId(void){return 100;}
void ExitProcess(DWORD code){exit((int)code);}
int WSAStartup(unsigned short v,WSADATA *d){(void)d;if(v!=0x202)abort();wsa_starts++;return 0;}
int WSACleanup(void){wsa_ends++;return 0;}int WSAGetLastError(void){return 10054;}
SOCKET socket(int a,int b,int c){if(a!=2||b!=1||c!=6)abort();return 9;}
int setsockopt(SOCKET s,int level,int option,const char *value,int length){
 if(s!=9||level!=6||option!=1||length!=sizeof(int)||*(const int*)value!=1)abort();
 no_delay_calls++;return scenario==13?-1:0;
}
unsigned short htons(unsigned short v){return (unsigned short)((v>>8)|(v<<8));}
uint32_t htonl(uint32_t v){return (v>>24)|((v>>8)&0xff00)|((v<<8)&0xff0000)|(v<<24);}
int connect(SOCKET s,const struct sockaddr *a,int bytes){const struct sockaddr_in *v=(const struct sockaddr_in*)a;
 if(s!=9||bytes!=sizeof(*v)||v->sin_family!=2||v->sin_port!=htons(12345)||v->sin_addr.s_addr!=htonl(0x7f000001)||no_delay_calls!=1)abort();
 return scenario==11?-1:0;
}
int shutdown(SOCKET s,int mode){if(s!=9||mode!=2)abort();return 0;}
int closesocket(SOCKET s){if(s!=9)abort();socket_closes++;return scenario==14||scenario==15?-1:0;}
static void p32(unsigned char *p,uint32_t v){unsigned int i;for(i=0;i<4;i++)p[i]=(unsigned char)(v>>(i*8));}
static uint32_t u32(const unsigned char *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static void p64(unsigned char *p,uint64_t v){p32(p,(uint32_t)v);p32(p+4,(uint32_t)(v>>32));}
int send(SOCKET s,const char *p,int bytes,int flags){int count=bytes>17?17:bytes;(void)flags;
 if(s!=9||count<=0||request_bytes+(unsigned)count>sizeof(request))abort();memcpy(request+request_bytes,p,count);request_bytes+=(unsigned)count;return count;
}
static void reply(void){uint32_t command=u32(request+12),length;
 if(request_bytes!=u32(request+88)||memcmp(request,"COHLDIR1",8)||command<1||command>3)abort();commands[command]++;
 memset(response,0,sizeof(response));memcpy(response,"COHRSP1",7);p32(response+8,1);p32(response+16,u32(request+64));
 length=command==1?32:command==2?(scenario==9?64:392):0;
 if(command==3&&scenario==4){p32(response+12,2);p32(response+24,77);length=0;}
 p32(response+20,length);
 if(command==1){p64(response+32,scenario==2?89:88);p64(response+40,123);p32(response+48,1);p32(response+52,1);
  if(u32(request+84)!=strlen("/state/operation/data/scripts.loc")||memcmp(request+96,"/state/operation/data/scripts.loc",u32(request+84)))abort();
 }else if(command==2){unsigned char *frame=response+32,*wfd=frame+72;
  memcpy(frame,"COHLIVE1",8);memcpy(frame+8,request+16,16);memcpy(frame+24,request+68,16);
  p32(frame+40,(uint32_t)(commands[2]-1));p32(frame+44,(uint32_t)(commands[2]-1));
  p32(frame+48,scenario==9?0:1);p32(frame+52,scenario==3?0:1);p32(frame+60,length);
  if(scenario!=9){p32(frame+64,(uint32_t)(commands[2]-1));p32(wfd,1);p32(wfd+32,5);strcpy((char*)wfd+44,"fixture.fx");}
  if(scenario==1||scenario==15||(scenario==3&&commands[2]==2))frame[0]='X';
 }
 response_bytes=32+length;response_taken=0;request_bytes=0;
}
int recv(SOCKET s,char *out,int bytes,int flags){unsigned int remain,count;(void)flags;if(s!=9)abort();
 if(response_taken==response_bytes)reply();remain=response_bytes-response_taken;count=(unsigned)bytes;
 if(count>11)count=11;if(count>remain)count=remain;memcpy(out,response+response_taken,count);response_taken+=count;return (int)count;
}
static void config(void){
 setenv("COH_CLIENT_LIVE_DIRECTORY","1",1);setenv("COH_CLIENT_LIVE_DIRECTORY_ENDPOINT","127.0.0.1:12345",1);
 setenv("COH_CLIENT_LIVE_DIRECTORY_SESSION","11111111111111111111111111111111",1);
 setenv("COH_CLIENT_LIVE_DIRECTORY_AUTH","2222222222222222222222222222222222222222222222222222222222222222",1);
 setenv("COH_CLIENT_LIVE_DIRECTORY_DESCRIPTOR","3333333333333333333333333333333333333333333333333333333333333333",1);
 setenv("COH_CLIENT_LIVE_DIRECTORY_GUEST_ROOT","/state/operation/data",1);
 setenv("COH_CLIENT_LIVE_DIRECTORY_DEVICE","88",1);setenv("COH_CLIENT_LIVE_DIRECTORY_RECIPE","wine-b073-constructor-v1",1);
}
int main(int argc,char **argv){CohLiveNativeDirectory *directory=NULL;WIN32_FIND_DATAA wfd;void *cache=(void*)(uintptr_t)17;int result;
 if(argc!=2)return 64;scenario=atoi(argv[1]);config();observed_inode=123;
 strcpy(final_path,"\\\\?\\Z:\\state\\operation\\data\\scripts.loc");
 if(scenario==16)strcpy(final_path,"\\\\?\\Z:\\game-import\\data\\scripts.loc");
 if(scenario==12)stage=13;
 if(scenario==7)unsetenv("COH_CLIENT_LIVE_DIRECTORY");
 if(scenario==8)setenv("COH_CLIENT_LIVE_DIRECTORY_RECIPE","other",1);
 if(scenario!=10)FolderCacheLiveDirectorySetMainThread();cohLiveNativeRegisterCache(cache);
 last_error=51;errno=52;
 result=cohLiveNativeFirst(cache,cache,"Z:\\state\\operation\\data\\SCRIPTS.LOC","Z:\\state\\operation\\data",1,0,1,1,1,1,1,&directory,&wfd);
 if(GetLastError()!=51||errno!=52)abort();
 if(scenario==1||scenario==2||scenario==7||scenario==8||scenario==10||scenario==11||scenario==13){
  if(result!=-1||directory||coh_live_native.transport.rows_returned)abort();FolderCacheLiveDirectoryStop();return 0;
 }
 if(scenario==9){if(result||!directory)abort();cohLiveNativeClose(directory);FolderCacheLiveDirectoryStop();return 0;}
 if(result!=1||!directory||strcmp(wfd.cFileName,"fixture.fx")||wfd.nFileSizeLow!=5||commands[1]!=1||commands[2]!=1)abort();
 if(scenario==3){cohLiveNativeNext(directory,&wfd);abort();}
 if(cohLiveNativeNext(directory,&wfd)!=0||commands[2]!=1)abort();
 cohLiveNativeClose(directory);
 if(scenario==5){current_thread++;cohLiveNativeFirst(cache,cache,"Z:\\state\\operation\\data\\SCRIPTS.LOC","Z:\\state\\operation\\data",1,0,1,1,1,1,1,&directory,&wfd);abort();}
 if(scenario==6){if(cohLiveNativeFirst((void*)(uintptr_t)18,cache,"Z:\\state\\operation\\data\\SCRIPTS.LOC","Z:\\state\\operation\\data",1,0,1,1,1,1,1,&directory,&wfd)!=-1)abort();}
 FolderCacheLiveDirectoryStop();
 if(socket_closes!=1||wsa_starts!=1||wsa_ends!=1||commands[3]!=1||closes!=1)abort();
 if(cohLiveNativeFirst(cache,cache,"Z:\\state\\operation\\data\\SCRIPTS.LOC","Z:\\state\\operation\\data",1,0,1,1,1,1,1,&directory,&wfd)!=-1)abort();
 if(GetLastError()!=51||errno!=52)abort();return 0;
}
'''


class NativeAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        path=Path(cls.temp.name)
        (path/'windows.h').write_text(SDK)
        (path/'winsock2.h').write_text(WINSOCK)
        (path/'fixture.c').write_text('#define _POSIX_C_SOURCE 200809L\n'+FIXTURE.split('int execute(',1)[0]+ADAPTER)
        cls.executable=path/'fixture'
        subprocess.run(['cc','-std=c99','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function',
                        '-Wno-misleading-indentation','-I',str(path),'-I',str(ROOT),'-I',str(TRANSPORT),
                        str(path/'fixture.c'),str(TRANSPORT/'coh_live_transport.c'),'-o',str(cls.executable)],check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def invoke(self,scenario,expected=0):
        result=subprocess.run([str(self.executable),str(scenario)],capture_output=True,text=True)
        self.assertEqual(result.returncode,expected,result.stdout+result.stderr)
        return result.stdout

    def test_current_native_handle_join_success_and_balanced_stop(self):
        self.assertIn('startup_scope_closed_zoning_stock',self.invoke(0))

    def test_initial_malformed_frame_or_identity_mismatch_stock_before_rows(self):
        for scenario in (1,2):
            self.assertIn('initial_directory_decline',self.invoke(scenario))

    def test_late_batch_failure_exits_nonzero_without_fallback(self):
        self.assertIn('terminal_directory_batch',self.invoke(3,77))

    def test_late_close_or_thread_guard_failure_is_terminal(self):
        self.assertIn('terminal_directory_close',self.invoke(4,77))
        self.assertIn('terminal_directory_admission',self.invoke(5,77))

    def test_foreign_cache_preserves_stock_route_after_prior_rows(self):
        self.invoke(6)

    def test_absent_or_unknown_registration_no_native_requests(self):
        for scenario in (7,8,10,11):
            self.invoke(scenario)

    def test_empty_final_frame_closes_without_returning_row(self):
        self.invoke(9)

    def test_unclosed_native_authorization_never_falls_back(self):
        self.assertIn('terminal_native_authorization_cleanup',self.invoke(12,77))

    def test_no_delay_failure_closes_socket_before_any_native_request(self):
        self.assertIn('initial_registration_decline',self.invoke(13))

    def test_socket_close_failure_never_claims_successful_cleanup(self):
        self.assertIn('terminal_startup_socket_cleanup',self.invoke(14,77))
        self.assertIn('terminal_initial_socket_cleanup',self.invoke(15,77))

    def test_native_import_alias_witness_keeps_original_request_and_inode_join(self):
        self.assertIn('startup_scope_closed_zoning_stock',self.invoke(16))


if __name__=='__main__':
    unittest.main()
