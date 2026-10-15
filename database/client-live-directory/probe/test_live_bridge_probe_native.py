"""Compile the exact probe against fake SDK APIs; genuine SDK is pending."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'native'))
from test_live_native_authorization import WINDOWS,FIXTURE
import parse_live_bridge_probe as parser

SDK=WINDOWS.replace('#endif',r'''
#define GENERIC_WRITE 0x40000000u
#define FILE_SHARE_READ 1u
#define CREATE_NEW 1u
#define FILE_ATTRIBUTE_NORMAL 128u
HANDLE CreateFileA(const char*,DWORD,DWORD,void*,DWORD,DWORD,HANDLE);
int WriteFile(HANDLE,const void*,DWORD,DWORD*,void*);int FlushFileBuffers(HANDLE);
DWORD GetCurrentProcessId(void);DWORD GetCurrentThreadId(void);
#endif
''')
BASE=FIXTURE.split('int execute(',1)[0].replace('void *GetProcAddress(', 'void *oldGetProcAddress(')
BASE=BASE.replace('int CloseHandle(HANDLE h){', 'int oldCloseHandle(HANDLE h){')
EXTRA=r'''
#define main probe_main
#include "coh_live_bridge_probe.c"
#undef main
static unsigned char captured[NT_PROBE_MAX_BYTES];static uint32_t captured_bytes;
static int scenario,query_calls_fixture,output_closes,opened_output;
DWORD GetCurrentProcessId(void){return 12;}DWORD GetCurrentThreadId(void){return 13;}
HANDLE CreateFileA(const char *path,DWORD access,DWORD share,void *security,DWORD create,DWORD flags,HANDLE template){
 (void)path;if(access!=GENERIC_WRITE||share!=1||security||create!=CREATE_NEW||flags!=128||template)abort();
 opened_output++;return scenario==1?INVALID_HANDLE_VALUE:(HANDLE)(uintptr_t)88;
}
int WriteFile(HANDLE h,const void *data,DWORD bytes,DWORD *written,void *overlap){
 uint32_t take=bytes>17?17:bytes;if(h!=(HANDLE)(uintptr_t)88||overlap||captured_bytes+take>sizeof(captured))abort();
 memcpy(captured+captured_bytes,data,take);captured_bytes+=take;*written=take;return 1;
}
int FlushFileBuffers(HANDLE h){if(h!=(HANDLE)(uintptr_t)88)abort();return scenario==8?0:1;}
int CloseHandle(HANDLE h){if(h==(HANDLE)(uintptr_t)88){output_closes++;return 1;}return oldCloseHandle(h);}
static LONG fake_query_directory(HANDLE h,HANDLE event,PVOID apc,PVOID context,CohLiveIoStatus *io,PVOID raw,
 ULONG bytes,ULONG cls,BOOLEAN single,CohLiveUnicodeString *mask,BOOLEAN restart){
 unsigned char *data=(unsigned char*)raw;const char *name=query_calls_fixture?"b.fx":"a.fx";size_t i,n=strlen(name);
 if(h!=(HANDLE)(uintptr_t)27||event||apc||context||bytes!=8192||cls!=3||single||mask->Length!=2||mask->MaximumLength!=4||mask->Buffer[0]!='*'||restart!=(query_calls_fixture==0))abort();
 query_calls_fixture++;
 if(scenario==5){io->Information=8;return 1;}
 if(query_calls_fixture==3){io->Information=scenario==7?8:0;return (LONG)0x80000006u;}
 put32(data,scenario==6?1:0);put64(data+24,123456789);put64(data+40,100);put32(data+56,7);put32(data+60,(uint32_t)(n*2));
 for(i=0;i<n;i++){data[94+i*2]=(unsigned char)name[i];data[95+i*2]=0;}
 io->Information=94+n*2;return 0;
}
void *GetProcAddress(HMODULE m,const char *name){if(!strcmp(name,"NtQueryDirectoryFile"))return (void*)fake_query_directory;return oldGetProcAddress(m,name);}
int main(int argc,char **argv){char *args[6]={"probe","stock","C:\\fixture\\fx","C:\\output\\data.bin",NULL,NULL};
 FILE *stream;int result;
 if(argc!=3)return 64;scenario=atoi(argv[1]);observed_inode=99;
 strcpy(final_path,"\\\\?\\C:\\fixture\\fx");
 if(scenario==2)stage=2;if(scenario==3)stage=14;if(scenario==4)stage=15;
 if(scenario==9)args[1]="share-block";
 if(scenario==10)args[3]="C:\\fixture\\fx\\inside.bin";
 if(scenario==12){args[2]="C:\\fixture\\fx\\";args[3]="C:\\fixture\\fx\\inside.bin";}
 if(scenario==13){args[2]="C:\\";args[3]="C:\\inside.bin";if(!same_or_descendant(args[2],args[3]))abort();}
 if(scenario==14){args[2]="C:/fixture/fx/";args[3]="c:\\fixture\\FX\\inside.bin";}
 if(scenario==11)args[4]="step";
 result=probe_main(scenario==11?5:4,args);
 if(scenario==10||scenario>=12){if(opened_output||query_calls_fixture||closes||captured_bytes)abort();}
 else if(scenario==1){if(query_calls_fixture||closes||captured_bytes)abort();}
 else if(output_closes!=1)abort();
 stream=fopen(argv[2],"wb");if(!stream)return 70;
 if(fwrite(captured,1,captured_bytes,stream)!=captured_bytes||fclose(stream))return 71;
 return result;
}
'''


class NativeProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        path=Path(cls.temp.name)
        (path/'windows.h').write_text(SDK)
        (path/'fixture.c').write_text(BASE+EXTRA)
        cls.exe=path/'probe'
        subprocess.run(['cc','-std=c99','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-Wno-unused-function',
                        '-I',str(path),'-I',str(ROOT),'-I',str(ROOT.parent/'native'),str(path/'fixture.c'),'-o',str(cls.exe)],check=True)

    def invoke(self,scenario,expected,input=None):
        path=Path(self.temp.name)/('case-'+str(scenario)+'.bin')
        result=subprocess.run([str(self.exe),str(scenario),str(path)],input=input,capture_output=True,text=True)
        self.assertEqual(result.returncode,expected,result.stdout+result.stderr)
        return result,path.read_bytes()

    def test_native_api_two_batches_exact_eof_and_partial_writes(self):
        result,data=self.invoke(0,0)
        value=parser.parse(data)
        self.assertTrue(value['packet_complete'])
        self.assertEqual([r['name'] for r in value['rows']],['a.fx','b.fx'])
        self.assertIn('complete=1',result.stdout)

    def test_existing_output_and_input_namespace_output_refuse_before_open(self):
        for scenario,code in ((1,65),(10,64)):
            _,data=self.invoke(scenario,code)
            self.assertEqual(data,b'')

    def test_missing_api_and_positive_nt_auth_status_report_partial(self):
        for scenario in (2,3,4):
            _,data=self.invoke(scenario,1)
            self.assertFalse(parser.parse(data)['packet_complete'])

    def test_trailing_separator_drive_root_and_mixed_separator_refuse_before_output_open(self):
        for scenario in (12,13,14):
            _,data=self.invoke(scenario,64)
            self.assertEqual(data,b'')

    def test_positive_query_malformed_buffer_or_data_at_eof_never_pass(self):
        for scenario in (5,6,7):
            _,data=self.invoke(scenario,1)
            self.assertFalse(parser.parse(data)['packet_complete'])

    def test_output_flush_failure_requires_outer_exit_not_packet_only(self):
        result,data=self.invoke(8,1)
        self.assertTrue(parser.parse(data)['packet_complete'])
        self.assertIn('complete=0',result.stdout)
        self.assertTrue(parser.parse(data)['outer_native_exit_console_and_custody_required'])

    def test_share_hold_is_explicit_stdin_barrier(self):
        result,data=self.invoke(9,0,'C')
        self.assertIn('COH_NT_SHARE_READY',result.stdout)
        self.assertEqual(parser.parse(data)['mode'],2)

    def test_batch_step_requires_explicit_command_for_each_native_buffer(self):
        result,data=self.invoke(11,0,'NN')
        self.assertEqual(result.stdout.count('COH_NT_BATCH_READY'),2)
        self.assertTrue(parser.parse(data)['packet_complete'])


if __name__=='__main__':
    unittest.main()
