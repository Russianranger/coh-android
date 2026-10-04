"""Execute the real string allocator and qualify its Win32 /O2 copy path."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools')]
import package_client_loading_native as native
import test_startup_bundle_client as old_tests


def harness():
    original, current = native.patched_text()
    stock = native.function(original, 'char* StructAllocStringLenDbg(').replace('StructAllocStringLenDbg(', 'stock_allocator(')
    candidate = native.function(current, 'char* StructAllocStringLenDbg(').replace('StructAllocStringLenDbg(', 'candidate_allocator(')
    flags = native.function(current, 'static int cohClientLoadingFlags(')
    prefix = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <assert.h>
#ifdef _WIN32
#include <windows.h>
#define NOINLINE __declspec(noinline)
#define TLS __declspec(thread)
#else
#define NOINLINE __attribute__((noinline))
#define TLS _Thread_local
static int strncpy_s(char*d,size_t cap,const char*s,size_t count) {
    size_t i=0; while(i<count && s[i]){assert(i+1<cap);d[i]=s[i];i++;}
    assert(i<cap);d[i]=0;return 0;
}
#endif
#define PRIVATE_PARSER_HEAPS 0
#define _NORMAL_BLOCK 0
static size_t allocations,last_size;
static void* test_malloc(size_t size,int b,const char*f,int l){(void)b;(void)f;(void)l;allocations++;last_size=size;return malloc(size);}
#define _malloc_dbg test_malloc
static TLS int coh_client_loading_flags = -1;
static TLS unsigned int coh_client_known_length_copies;
static volatile unsigned long observer;
'''
    tail = r'''
static void equivalent(const char*s,int len) {
    size_t before=allocations;char*a=stock_allocator(s,len,"test",1);size_t old_size=last_size;
    char*b=candidate_allocator(s,len,"test",1);
    if(!s){assert(!a && !b && allocations==before);return;}
    assert(a && b && allocations==before+2 && old_size==last_size && !strcmp(a,b));
    assert(!memcmp(a,b,strlen(a)+1));free(a);free(b);
}
#ifdef _WIN32
static DWORD WINAPI thread_check(LPVOID value) {
    int *ok=(int*)value;
    assert(coh_client_loading_flags==-1 && coh_client_known_length_copies==0);
    coh_client_loading_flags=0;char*p=candidate_allocator("thread",-1,"test",1);free(p);
    assert(coh_client_known_length_copies==0);*ok=1;return 0;
}
#endif
static double bench(int enabled,int length,int iterations) {
    char*s=malloc((size_t)length+1);memset(s,'s',(size_t)length);s[length]=0;
    coh_client_loading_flags=enabled?1:0;
    clock_t begin=clock();
    for(int i=0;i<iterations;i++){char*p=enabled?candidate_allocator(s,-1,"bench",0):stock_allocator(s,-1,"bench",0);observer+=(unsigned char)p[length-1];free(p);}
    double elapsed=(double)(clock()-begin)/CLOCKS_PER_SEC;free(s);return elapsed;
}
int main(int argc,char**argv) {
    int lens[]={0,1,8,48,128,511,512,11999,12000,65535};
    for(int flags=0;flags<4;flags++){
        coh_client_loading_flags=flags;coh_client_known_length_copies=0;
        equivalent(NULL,-1);equivalent("",-1);
        for(unsigned int n=0;n<sizeof(lens)/sizeof(lens[0]);n++){
            int length=lens[n];char*s=malloc((size_t)length+1);memset(s,'t',(size_t)length);s[length]=0;
            equivalent(s,-1);equivalent(s,0);equivalent(s,length);equivalent(s,length/2);equivalent(s,length+3);free(s);
        }
        assert(coh_client_known_length_copies==((flags==3)?11u:0u));
    }
    coh_client_loading_flags=-1;
#ifdef _WIN32
    _putenv_s("COH_CLIENT_KNOWN_STRING_COPY","1");_putenv_s("COH_CLIENT_BIN_PROFILE","0");
#else
    setenv("COH_CLIENT_KNOWN_STRING_COPY","1",1);setenv("COH_CLIENT_BIN_PROFILE","0",1);
#endif
    assert(cohClientLoadingFlags()==1);
    int ok=1;
#ifdef _WIN32
    ok=0;HANDLE thread=CreateThread(NULL,0,thread_check,&ok,0,NULL);assert(thread);assert(WaitForSingleObject(thread,10000)==WAIT_OBJECT_0);CloseHandle(thread);
#endif
    assert(ok && coh_client_loading_flags==1);
    if(argc==2 && !strcmp(argv[1],"bench")){
        int sizes[]={8,48,128,512,11999};
        for(unsigned int j=0;j<sizeof(sizes)/sizeof(sizes[0]);j++){
            int repeats=sizes[j]>512?200000:2000000;
            for(int round=0;round<5;round++){
                double old,now;
                if(round&1){now=bench(1,sizes[j],repeats);old=bench(0,sizes[j],repeats);}
                else{old=bench(0,sizes[j],repeats);now=bench(1,sizes[j],repeats);}
                printf("BENCH %d %.9f %.9f\n",sizes[j],old,now);
            }
        }
    }
    puts("EQUIVALENCE_OK");return 0;
}
'''
    return prefix+flags+'\nNOINLINE '+stock+'\nNOINLINE '+candidate+'\n'+tail


def compile_harness(directory, require_windows=False):
    directory=Path(directory); source=directory/'copy.c'; source.write_text(harness())
    if os.name=='nt':
        compiler=shutil.which('cl'); native.require(compiler, 'MSVC cl required for real Win32 qualification')
        executable=directory/'copy.exe'; assembly=directory/'copy.asm'
        subprocess.run([compiler,'/nologo',*native.COMPILER_OPTIONS,'/W3','/FAs','/Fa'+str(assembly),
            '/Fe'+str(executable),str(source)],cwd=directory,check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        from package_reference_runtime import file_record
        native.require(file_record(executable)['pe_machine']==332, 'Native proof compiler must target Win32')
    else:
        native.require(not require_windows, 'Formal loading native proof requires Windows/MSVC Win32')
        compiler=shutil.which('cc') or shutil.which('gcc'); native.require(compiler, 'C compiler required')
        executable=directory/'copy'; assembly=directory/'copy.s'
        args=[compiler,'-std=c11','-D_POSIX_C_SOURCE=200809L','-O2','-Wall','-Wextra','-Werror',str(source)]
        subprocess.run(args+['-o',str(executable)],cwd=directory,check=True)
        subprocess.run(args+['-S','-o',str(assembly)],cwd=directory,check=True)
    return executable,assembly


def windows_receipt(output):
    with tempfile.TemporaryDirectory(prefix='coh-client-copy-msvc-') as temporary:
        executable,assembly=compile_harness(temporary, True)
        proc=subprocess.run([str(executable),'bench'],check=True,capture_output=True,text=True)
        native.require('EQUIVALENCE_OK' in proc.stdout, 'Actual native copy equivalence failed')
        raw=assembly.read_text(errors='replace')
        # The produced assembly must still contain the secure CRT fallback and
        # a distinct memcpy call in the gated candidate allocator.
        candidate=raw.split('_candidate_allocator PROC',1)[-1].split('_candidate_allocator ENDP',1)[0]
        native.require('_candidate_allocator PROC' in raw and re.search(r'call[^\r\n]*memcpy|rep\s+movs|movdqu',candidate)
            and re.search(r'call[^\r\n]*strncpy_s',candidate), 'MSVC copy and secure CRT fallback assembly missing')
        groups={n:[] for n in (8,48,128,512,11999)}
        for line in proc.stdout.splitlines():
            if line.startswith('BENCH '):
                _,length,old,now=line.split();groups[int(length)].append((float(old),float(now)))
        native.require(all(len(rows)==5 for rows in groups.values()), 'Missing repeated MSVC benchmark')
        benchmark=[{'length':n,'stock_seconds':statistics.median(x[0] for x in rows),
            'candidate_seconds':statistics.median(x[1] for x in rows),'rounds':5}
            for n,rows in groups.items()]
        receipt={'format':1,'status':'passed','platform':'windows','architecture':'Win32','configuration':'OptDebug',
            'compiler_options':native.COMPILER_OPTIONS,'build_input':native.expected_receipt(),'equivalence_verified':True,'explicit_length_behavior_verified':True,
            'thread_local_flags_verified':True,'opt_in_and_fallback_verified':True,
            'known_length_path_secure_crt_call_eliminated':True,'benchmarks':benchmark,
            'assembly_sha256':hashlib.sha256(assembly.read_bytes()).hexdigest(),
            'harness_sha256':hashlib.sha256(harness().encode()).hexdigest(),
            'physical_startup_savings_validated':False}
        native.validate_checks(receipt)
        Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(json.dumps(receipt,indent=2)+'\n')
        return receipt


class ClientLoadingNativeTests(unittest.TestCase):
    def test_exact_decoder_scope_preserves_schema_and_freshness(self):
        expected=native.expected_receipt(); original,current=native.patched_text()
        self.assertEqual(set(expected['patched_sha256']),{native.FILE})
        self.assertEqual(expected['source_sha256'],{native.FILE:native.base.baseline.schema_pins()[native.FILE]})
        self.assertTrue(expected['reverse_patch_exact_base_verified'])
        # Only source-preserving profile probes surround this function: all date
        # comparison / failure clauses must be retained, including production.
        for token in ('FileListRead(&binlist, binfile)','fileScanAllDataDirs(dir, DateCheckCallback)',
            'fileDatesEqual(scanfile->date, binfile->date, true)',
            'fileDatesEqual(diskdate,binfile->date, true)','FileListFind(&lf_filedates, binfile->path)',
            'SerializeReadOpen(persistfile, PARSE_SIG, crc, isProductionMode())'):
            self.assertEqual(original.count(token),current.count(token))
        self.assertNotIn('quickLoadAnims',current.replace(original,''))

    def test_actual_allocator_equivalence_and_explicit_length_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            executable,_=compile_harness(temporary)
            result=subprocess.run([str(executable)],check=True,capture_output=True,text=True)
            self.assertIn('EQUIVALENCE_OK',result.stdout)

    def test_profile_and_copy_are_separately_opted_in_and_thread_local(self):
        _,text=native.patched_text()
        flags=native.function(text,'static int cohClientLoadingFlags(')
        self.assertIn('strcmp(copy, "1") == 0',flags);self.assertIn('strcmp(profile, "1") == 0',flags)
        self.assertIn('static __declspec(thread) int coh_client_loading_flags = -1;',text)
        self.assertIn('static __declspec(thread) unsigned int coh_client_known_length_copies;',text)
        for phase in ('open','freshness','decode'):self.assertIn('cohClientBinProfile("'+phase+'"',text)
        self.assertEqual(native.COPY['environment_variable'],'COH_CLIENT_KNOWN_STRING_COPY')
        self.assertEqual(native.PROFILE['phases'],['open','freshness','decode'])

    def test_source_layer_rejects_foreign_or_repeated_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture=old_tests.StartupBundleClientTests();fixture.root=Path(temporary)
            source=fixture.frozen_source();native.base.apply_overlay(source)
            old={p:(source/p).read_bytes() for p in native.base.baseline.SCHEMA_FILES if p!=native.FILE}
            expected=native.apply_overlay(source)
            self.assertEqual(native.validate_source(source)[0],expected)
            for p,data in old.items():self.assertEqual((source/p).read_bytes(),data)
            with self.assertRaisesRegex(ValueError,'receipt exists'):native.apply_overlay(source)
            (source/native.FILE).write_bytes((source/native.FILE).read_bytes()+b'foreign')
            with self.assertRaisesRegex(ValueError,'parser source changed'):native.validate_source(source)

    def test_formal_proof_rejects_fabricated_scope_non_windows_and_slowdown(self):
        # Structural tests never masquerade as the real MSVC benchmark receipt.
        valid={'format':1,'status':'passed','platform':'windows','architecture':'Win32','configuration':'OptDebug',
            'compiler_options':native.COMPILER_OPTIONS,'build_input':native.expected_receipt(),'equivalence_verified':True,'explicit_length_behavior_verified':True,
            'thread_local_flags_verified':True,'opt_in_and_fallback_verified':True,
            'known_length_path_secure_crt_call_eliminated':True,'physical_startup_savings_validated':False,
            'assembly_sha256':'a'*64,'harness_sha256':hashlib.sha256(harness().encode()).hexdigest(),
            'benchmarks':[{'length':n,'stock_seconds':2.0,'candidate_seconds':1.0,'rounds':5}for n in (8,48,128,512,11999)]}
        native.validate_checks(valid)
        for key,value in (('platform','linux'),('architecture','AMD64'),('equivalence_verified',False),
                ('physical_startup_savings_validated',True),('build_input',{}),
                ('harness_sha256','b'*64),('compiler_options',['/O2'])):
            bad=copy.deepcopy(valid);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):native.validate_checks(bad)
        bad=copy.deepcopy(valid)
        for item in bad['benchmarks']:item['candidate_seconds']=3
        with self.assertRaisesRegex(ValueError,'did not improve'):native.validate_checks(bad)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--require-windows',action='store_true');parser.add_argument('--output',type=Path)
    args,unknown=parser.parse_known_args()
    if args.require_windows:
        native.require(args.output is not None,'MSVC proof output required');windows_receipt(args.output)
        print('Qualified actual Win32 copy equivalence, assembly and benchmark; physical startup savings pending')
    else:
        unittest.main(argv=[sys.argv[0],*unknown])
