"""Execute extracted original/candidate Cg control flow; no GPU is simulated as real."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
import map_startup_namespace_certificate as namespace
import prepare_native_cg_profile_source as profile
from test_map_startup_observer_source import WINDOWS_ADAPTER


def harness():
    original = namespace.function(profile.source_bytes().decode('latin-1'), 'CGprogram rt_cgCreateProgramFromBuffer(')
    candidate = namespace.function(profile.patch_source(profile.source_bytes()).decode('latin-1'), 'CGprogram rt_cgCreateProgramFromBuffer(')
    prefix = r'''
#include <assert.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include "windows.h"
typedef void* CGprogram;
typedef int CGenum;
typedef int tShaderProgramType;
typedef int tCgShaderProfile;
typedef int tCgFxError;
enum { CG_SOURCE=4112, CG_OBJECT=4113, kCgFxError_NONE=0 };
static struct { int saveCgShaderListing; } game_state;
static int scenario, trace[32], calls, rows;
static char row[1024];
static void record(int n) { assert(calls<32); trace[calls++]=n; }
static void ValidateShaderProgramTypeConstant(int n) { assert(n==8);record(1); }
static void* rt_cgfxGetGlobalContext(void) { record(2);return (void*)5; }
static CGprogram cgCreateProgram(void* context,int kind,const char *program,int profile,const char* entry,const char**args) {
 assert(context==(void*)5&&(kind==CG_SOURCE||kind==CG_OBJECT||kind==9)&&!strcmp(program,"exact shader")&&profile==11&&!strcmp(entry,"main")&&args==NULL);
 record(3);return scenario==1?NULL:(void*)7;
}
static int ReviewShaderCompileResults(const char* name,CGprogram program) {
 assert(!strcmp(name,"fixture.cg"));record(4);return scenario==2?1:0;
}
static void SaveProgramAssembly(const char* name,CGprogram program) {assert(program==(void*)7);record(5);}
static void cgGLLoadProgram(CGprogram program) {assert(program==(void*)7);record(6);}
static int ReviewShaderLoadResults(const char* name,CGprogram program) {assert(program==(void*)7);record(7);return scenario==3?1:0;}
static void cgDestroyProgram(CGprogram program) {assert(program==(void*)7);record(8);}
static int fixturePrintf(const char *format,...) {
 va_list args;int n;va_start(args,format);n=vsnprintf(row,sizeof(row),format,args);va_end(args);
 assert(n>0&&(size_t)n<sizeof(row));++rows;return n;
}
#define printf fixturePrintf
#include "coh_native_cg_profile.h"
'''
    tail = r'''
static void reset(int n) {scenario=n;calls=0;memset(trace,0,sizeof(trace));game_state.saveCgShaderListing=n==4;}
int main(void) {
 int kind,n,old_trace[32],old_calls;CGprogram old,result;
 for(kind=CG_SOURCE;kind<=CG_OBJECT;kind++) for(n=0;n<5;n++) {
  reset(n);old=stockCreate("fixture.cg",kind,"exact shader",8,11,"main",NULL);old_calls=calls;memcpy(old_trace,trace,sizeof(trace));
  reset(n);result=rt_cgCreateProgramFromBuffer("fixture.cg",kind,"exact shader",8,11,"main",NULL);
  assert(old==result&&old_calls==calls&&!memcmp(old_trace,trace,sizeof(trace)));
  assert(strstr(row,kind==CG_SOURCE?"kind=1 ":"kind=2 "));
  assert(strstr(row,(n==1||n==2)?"driver_load_called=0":"driver_load_called=1"));
 }
 assert(rows==10);
#ifdef COH_PORTABLE_CLOCK
 fixture_clock_fail=1;reset(0);rt_cgCreateProgramFromBuffer("fixture.cg",CG_OBJECT,"exact shader",8,11,"main",NULL);
 assert(strstr(row,"clock_valid=0 create_us=0 driver_load_called=1 driver_load_us=0"));fixture_clock_fail=0;
 fixture_clock_regress_at=fixture_clock_calls+2;reset(0);rt_cgCreateProgramFromBuffer("fixture.cg",CG_SOURCE,"exact shader",8,11,"main",NULL);
 assert(strstr(row,"clock_valid=0"));fixture_clock_regress_at=0;
#endif
 while(cohCgRows<1024u) {reset(0);rt_cgCreateProgramFromBuffer("fixture.cg",9,"exact shader",8,11,"main",NULL);}
 assert(rows==1024&&strstr(row,"kind=0 "));
 for(n=0;n<100;n++) {reset(0);assert(rt_cgCreateProgramFromBuffer("fixture.cg",CG_SOURCE,"exact shader",8,11,"main",NULL)==(void*)7);}
 assert(rows==1024);puts("COH_CG_PROFILE_CONTROL_FLOW_PASS cases=10 rows_bounded=1024");return 0;
}
'''
    return prefix + original.replace('rt_cgCreateProgramFromBuffer(', 'stockCreate(', 1) + '\n' + candidate + tail


def execute(output=None, windows=False):
    namespace.require(not windows or os.name == 'nt', 'Actual Windows fixture execution required')
    compiler = shutil.which('cl' if windows else 'cc')
    namespace.require(compiler, 'C compiler required')
    with tempfile.TemporaryDirectory(prefix='coh-cg-profile-') as temporary:
        root=Path(temporary); code=harness(); (root/'fixture.c').write_text(code)
        (root/profile.HEADER).write_bytes((profile.ROOT/profile.OVERLAY).read_bytes())
        binary=root/('fixture.exe' if windows else 'fixture')
        if windows:
            command=[compiler,'/nologo','/O2','/TC','/MT','fixture.c','/Fe:'+str(binary)]
        else:
            (root/'windows.h').write_text(WINDOWS_ADAPTER)
            command=[compiler,'-std=c11','-O2','-DCOH_PORTABLE_CLOCK','-I',str(root),'fixture.c','-o',str(binary)]
        build=subprocess.run(command,cwd=root,capture_output=True,text=True)
        namespace.require(build.returncode==0,'Cg fixture compile failed: '+build.stdout+build.stderr)
        run=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30)
        namespace.require(run.returncode==0 and 'COH_CG_PROFILE_CONTROL_FLOW_PASS' in run.stdout,
                          'Cg fixture execution failed: '+run.stdout+run.stderr)
        receipt={'format':1,'status':'passed','role':'actual_extracted_Cg_control_flow_parity',
            'cases':10,'maximum_rows':1024,'native_windows_executed':windows,
            'native_cg_runtime_executed':False,'gpu_executed':False,'physical_device_executed':False,
            'shader_objects_are_controlled_fixture_handles':True,'source':profile.expected_receipt(),
            'harness_sha256':hashlib.sha256(code.encode()).hexdigest(),
            'fixture_binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
            'output':run.stdout.strip()}
        if output:
            output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
            output.write_text(json.dumps(receipt,indent=2)+'\n')
            shutil.copyfile(binary,output.with_suffix('.exe' if windows else '.bin'))
        return receipt


class NativeCgProfileTests(unittest.TestCase):
    def test_actual_function_control_flow_and_handles_match(self):
        self.assertEqual(execute()['cases'],10)

    def test_candidate_retains_every_native_statement_and_source_object(self):
        original=namespace.function(profile.source_bytes().decode('latin-1'),'CGprogram rt_cgCreateProgramFromBuffer(')
        candidate=namespace.function(profile.patch_source(profile.source_bytes()).decode('latin-1'),'CGprogram rt_cgCreateProgramFromBuffer(')
        stripped=re.sub(r'^ *CohNativeCgProfile profile_observation;\n|^ *cohCg[^\n]*\n','',candidate,flags=re.M)
        self.assertEqual(original,stripped)
        self.assertIn('program_type == CG_SOURCE ? 1u : program_type == CG_OBJECT ? 2u : 0u',candidate)

    def test_changed_source_anchor_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'anchor differs'):
            profile.patch_source(profile.source_bytes().replace(b'    return pgmHandle;\n',b'    return 0;\n'))

    def test_receipt_does_not_authorize_cache_or_publication(self):
        receipt=profile.expected_receipt()
        for key in ('publication_allowed','cache_acceptance_changed','native_game_executed'):
            self.assertFalse(receipt[key])
        self.assertTrue(receipt['object_does_not_prove_gpu_driver_cache_hit'])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--windows-qualify',action='store_true');parser.add_argument('--output',type=Path)
    args,rest=parser.parse_known_args()
    if args.windows_qualify:
        namespace.require(args.output is not None,'Windows evidence output required')
        print(json.dumps(execute(args.output,windows=True)))
    else:
        unittest.main(argv=[__file__,*rest])
