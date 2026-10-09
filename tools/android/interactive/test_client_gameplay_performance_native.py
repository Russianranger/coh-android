"""Execute the real cap/error predicates and actual patched texture-load function."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools')]
import package_client_gameplay_performance_native as producer
import package_client_loading_native as loading
import test_client_gameplay_performance_source as source_proof
from package_reference_runtime import file_record

PATCH = producer.PATCHES[0]
HEADER = next(iter(producer.OVERLAYS.values()))
OPTIONS = ['/O2', '/Oy-', '/MT', '/TC']
PROFILE_PREFIX = 'COH_CLIENT_GAMEPLAY_PROFILE_V1 '
ERROR_PREFIX = 'COH_CLIENT_TEXTURE_ERRORS_V1 '


def harness(production=False):
    original, current = source_proof.sources()
    stock = loading.function(original[producer.FILES[1]], 'void changeTexture(')
    modified = loading.function(current[producer.FILES[1]], 'void changeTexture(')
    prefix = r'''
#include <assert.h>
#include <ctype.h>
#include <limits.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned int emissions, environment_queries;
static int emit_lines;
static char last_line[1024];
ENVIRONMENT_CODE
#define printf coh_gp_poison_printf
#define snprintf coh_gp_poison_formatter
#define fflush coh_gp_poison_flush
#define FILE coh_gp_poison_file
'''
    if production:
        environment = r'''
#ifndef _WIN32
#error Genuine Win32 qualification required
#endif
#ifdef _WIN64
#error Qualification must target Win32
#endif
static void select_environment(const char *fps,const char *errors) {
    assert(_putenv_s("COH_CLIENT_GAMEPLAY_FPS",fps?fps:"")==0);
    assert(_putenv_s("COH_CLIENT_BOUNDED_TEXTURE_ERRORS",errors?errors:"")==0);
}
'''
    else:
        environment = r'''
static const char *fps_environment,*error_environment;
static void select_environment(const char *fps,const char *errors) {
    fps_environment=fps;error_environment=errors;
}
static const char *cohGpTestEnvironment(const char *name) {
    ++environment_queries;
    if(!strcmp(name,"COH_CLIENT_GAMEPLAY_FPS"))return fps_environment;
    assert(!strcmp(name,"COH_CLIENT_BOUNDED_TEXTURE_ERRORS"));return error_environment;
}
static void cohGpTestEmit(const char *line) {
    assert(strlen(line)<sizeof(last_line)&&!strchr(line,'\n'));
    strcpy(last_line,line);++emissions;if(emit_lines)puts(line);
}
#define COH_GAMEPLAY_PERFORMANCE_TEST 1
'''
    common = r'''
#define COH_GP_STRING_INNER(value) #value
#define COH_GP_STRING(value) COH_GP_STRING_INNER(value)
static void check_macros(void) {
    assert(!strcmp(COH_GP_STRING(printf),"coh_gp_poison_printf"));
    assert(!strcmp(COH_GP_STRING(snprintf(a,b,c,d)),"coh_gp_poison_formatter(a,b,c,d)"));
    assert(!strcmp(COH_GP_STRING(fflush(a)),"coh_gp_poison_flush(a)"));
    assert(!strcmp(COH_GP_STRING(FILE),"coh_gp_poison_file"));
}
#undef printf
#undef snprintf
#undef fflush
#undef FILE
static void reset(const char *fps,const char *errors) {
    memset(&coh_gp_state,0,sizeof(coh_gp_state));
    select_environment(fps,errors);emissions=environment_queries=0;emit_lines=0;last_line[0]=0;
}
typedef int BoneId;
typedef struct TexBind {int tag;} TexBind;
typedef struct BasicTexture {int tag;} BasicTexture;
typedef struct NewTexture {TexBind *base;BasicTexture *generic;} NewTexture;
typedef struct SeqType {const char *name;} SeqType;
typedef struct SeqInst {SeqType *type;NewTexture newtextures[3];int updated_appearance;} SeqInst;
typedef struct Entity {SeqInst *seq;} Entity;
static TexBind white_bind={1},valid_bind={2};
static BasicTexture white_basic={1},valid_basic={2};
static TexBind *white_tex_bind=&white_bind;
static BasicTexture *white_tex=&white_basic;
static unsigned int load1_calls,load2_calls,error_calls;
static int development=1,quickload;
#define TEX_LOAD_IN_BACKGROUND 1
#define TEX_FOR_ENTITY 2
static int isDevelopmentMode(void) {return development;}
static int bone_IdIsValid(BoneId bone) {return bone>=0&&bone<3;}
static const char *bone_NameFromId(BoneId bone) {(void)bone;return "Head";}
static int fixture_stricmp(const char *left,const char *right) {
    while(*left&&*right) {
        int delta=tolower((unsigned char)*left)-tolower((unsigned char)*right);
        if(delta)return delta;
        ++left;++right;
    }
    return (unsigned char)*left-(unsigned char)*right;
}
#define _stricmp fixture_stricmp
static char *strstri(const char *value,const char *part) {
    const char *at;
    size_t n=strlen(part),i;
    for(at=value;*at;++at) {
        for(i=0;i<n&&at[i]&&tolower((unsigned char)at[i])==tolower((unsigned char)part[i]);++i) {}
        if(i==n)return (char*)at;
    }
    return NULL;
}
static TexBind *texLoad(const char *name,int mode,int purpose) {
    assert(mode==1&&purpose==2);++load1_calls;
    if(!strcmp(name,"missing"))return NULL;
    if(!strcmp(name,"fallback"))return white_tex_bind;
    return &valid_bind;
}
static BasicTexture *texLoadBasic(const char *name,int mode,int purpose) {
    assert(mode==1&&purpose==2);++load2_calls;
    if(!strcmp(name,"missing"))return NULL;
    if(!strcmp(name,"fallback"))return white_tex;
    return &valid_basic;
}
static void Errorf(const char *format,...) {(void)format;++error_calls;}
'''
    tail = r'''
static void texture_equivalence(void) {
    char *values[]={NULL,"none","missing","fallback","valid"};
    unsigned int i,j,round;int enabled,dev,quick;
    for(enabled=0;enabled<=1;++enabled)for(dev=0;dev<=1;++dev)for(quick=0;quick<=1;++quick) {
        reset("30",enabled?"1":"0");development=dev;quickload=quick;
        for(i=0;i<5;++i)for(j=0;j<5;++j)for(round=0;round<3;++round) {
            SeqType type={"Electro"};SeqInst before,after;Entity a,b;
            unsigned int old_load1,old_load2,old_errors;
            memset(&before,0,sizeof(before));memset(&after,0,sizeof(after));
            before.type=after.type=&type;a.seq=&before;b.seq=&after;
            load1_calls=load2_calls=error_calls=0;
            stockChangeTexture(&a,1,values[i],values[j]);
            old_load1=load1_calls;old_load2=load2_calls;old_errors=error_calls;
            load1_calls=load2_calls=error_calls=0;
            changeTexture(&b,1,values[i],values[j]);
            assert(load1_calls==old_load1&&load2_calls==old_load2);
            assert(!memcmp(&before,&after,sizeof(before)));
            assert(enabled?error_calls<=old_errors:error_calls==old_errors);
        }
    }
    reset("30","1");development=1;quickload=0;error_calls=0;
    changeTexture(NULL,1,"missing","missing");changeTexture(NULL,1,"missing","missing");
    assert(error_calls==2); /* unrelated garbage-entity errors remain exact */
    puts("TEXTURE_LOAD_FALLBACK_ASSIGNMENTS_EQUIVALENCE_PASS cases=600");
}
static void native_checks(void) {
    const char *flags[]={NULL,"","0","030","30 ","10x","-30","300","invalid","10","30"};
    unsigned int i,j,first,slot,index;char texture[64],oversized[300];int cap;
    check_macros();
    for(i=0;i<sizeof(flags)/sizeof(flags[0]);++i) {
        reset(flags[i],"1");cap=7;
        cohGpApplyProfile(&cap,0,10,10);
        assert(cap==(flags[i]&&!strcmp(flags[i],"30")?30:flags[i]&&!strcmp(flags[i],"10")?10:7));
        cap=17;cohGpApplyProfile(&cap,0,10,10);assert(cap==17); /* later /maxfps remains effective */
    }
    reset("30","1");cap=10;cohGpApplyProfile(&cap,1,10,10);
    assert(cap==10&&!coh_gp_state.profile_reported);
    cohGpApplyProfile(NULL,0,10,10);assert(!coh_gp_state.profile_reported);
    cohGpApplyProfile(&cap,0,10,10);assert(cap==30&&coh_gp_state.profile_reported);
    for(i=0;i<sizeof(flags)/sizeof(flags[0])-1;++i) {
        reset("30",flags[i]);
        for(j=0;j<10;++j)assert(cohGpTextureError(1,"Electro","Circuitry","Head"));
        assert(!coh_gp_state.unique_keys&&!coh_gp_state.suppressed);
    }
    reset("30","1");first=0;
    for(j=0;j<2648;++j)for(i=0;i<9;++i) {
        snprintf(texture,sizeof(texture),"Circuitry%u",i);
        first+=cohGpTextureError(1,"Electro",texture,"Head");
    }
    assert(first==9&&coh_gp_state.unique_keys==9&&coh_gp_state.original_errors==9);
    assert(coh_gp_state.suppressed==23823&&coh_gp_state.texture_reports==15);
    /* Every component, including slot, forms a distinct first-error identity. */
    assert(cohGpTextureError(2,"Electro","Circuitry0","Head"));
    assert(cohGpTextureError(1,"Circuitry","Circuitry0","Head"));
    assert(cohGpTextureError(1,"Electro","Circuitry0","Arm"));
    /* Force identical hashes: equality still checks the complete tuple. */
    reset("30","1");
    assert(cohGpTextureError(1,"Electro","original","Head"));
    slot=cohGpHashString(2166136261u^1u,"Electro",7);
    slot=cohGpHashString(slot,"different",9);slot=cohGpHashString(slot,"Head",4);
    index=slot%64u;
    for(i=0;i<64u;++i)if(coh_gp_state.keys[i].used)break;
    assert(i<64u);
    coh_gp_state.keys[index]=coh_gp_state.keys[i];coh_gp_state.keys[index].hash=slot;
    if(index!=i)memset(&coh_gp_state.keys[i],0,sizeof(coh_gp_state.keys[i]));
    assert(cohGpTextureError(1,"Electro","different","Head"));
    assert(!cohGpTextureError(1,"Electro","different","Head"));
    reset("30","1");
    for(i=0;i<64u;++i) {
        snprintf(texture,sizeof(texture),"unique%u",i);
        assert(cohGpTextureError(1,"Electro",texture,"Head"));
    }
    assert(coh_gp_state.unique_keys==64u);
    for(i=0;i<5u;++i)assert(cohGpTextureError(1,"Electro","overflow","Head"));
    assert(coh_gp_state.untracked_errors==5u&&!cohGpTextureError(1,"Electro","unique0","Head"));
    reset("30","1");memset(oversized,'A',sizeof(oversized));oversized[sizeof(oversized)-1]=0;
    for(i=0;i<3;++i) {
        assert(cohGpTextureError(1,NULL,"texture","Head"));
        assert(cohGpTextureError(1,"Electro",oversized,"Head"));
        assert(cohGpTextureError(1,oversized,"texture","Head"));
        assert(cohGpTextureError(1,"Electro","texture",oversized));
        assert(cohGpTextureError(3,"Electro","texture","Head"));
    }
    assert(coh_gp_state.untracked_errors==15&&!coh_gp_state.unique_keys);
    /* Saturation cannot wrap counts, reopen an error key or print indefinitely. */
    reset("30","1");assert(cohGpTextureError(1,"Electro","Circuitry","Head"));
    for(i=0;i<64u;++i)if(coh_gp_state.keys[i].used)break;
    assert(i<64u);
    for(j=0;j<32u;++j) {
        coh_gp_state.suppressed=coh_gp_state.next_report-1u;
        assert(!cohGpTextureError(1,"Electro","Circuitry","Head"));
    }
    assert(coh_gp_state.texture_reports==32u);
    coh_gp_state.suppressed=coh_gp_state.keys[i].suppressed=UINT_MAX;
    coh_gp_state.original_errors=coh_gp_state.untracked_errors=UINT_MAX;
    for(j=0;j<20u;++j) {
        assert(!cohGpTextureError(1,"Electro","Circuitry","Head"));
        assert(cohGpTextureError(1,NULL,"Circuitry","Head"));
    }
    assert(coh_gp_state.suppressed==UINT_MAX&&coh_gp_state.keys[i].suppressed==UINT_MAX);
    assert(coh_gp_state.original_errors==UINT_MAX&&coh_gp_state.untracked_errors==UINT_MAX);
    assert(coh_gp_state.texture_reports==32u);
    puts("CAP_EXACT_FALLBACK_TEXTURE_FULL_KEYS_BOUNDS_SATURATION_PASS");
    texture_equivalence();
    /* Small actual records are parsed independently by Python. */
    reset("30","1");emit_lines=1;cap=10;
    cohGpApplyProfile(&cap,0,10,10);
    assert(cohGpTextureError(1,"Electro","Circuitry","Head"));
    for(i=0;i<17u;++i)assert(!cohGpTextureError(1,"Electro","Circuitry","Head"));
}
int main(void) {native_checks();return 0;}
'''
    return (prefix.replace('ENVIRONMENT_CODE', environment)
        + (ROOT/HEADER).read_bytes().replace(b'\r\n', b'\n').decode('utf-8') + common
        + '\n#define changeTexture stockChangeTexture\n' + stock
        + '\n#undef changeTexture\n' + modified + tail)


def compile_harness(directory, windows=False, production=False):
    directory = Path(directory)
    source = directory/('gameplay-production.c' if production else 'gameplay.c')
    source.write_bytes(harness(production).encode('utf-8'))
    if os.name == 'nt':
        compiler = shutil.which('cl')
        if not compiler:
            raise ValueError('Actual Win32 MSVC required')
        binary = source.with_suffix('.exe')
        command = [compiler, '/nologo', *OPTIONS, '/W3', str(source), '/Fe:'+str(binary)]
    else:
        if windows or production:
            raise ValueError('Formal gameplay qualification requires real Win32 MSVC')
        compiler = shutil.which('cc') or shutil.which('gcc')
        if not compiler:
            raise ValueError('C compiler required')
        binary = source.with_suffix('')
        command = [compiler, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(binary)]
    try:
        subprocess.run(command, cwd=directory, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        raise RuntimeError('Gameplay fixture compilation failed:\n'+(error.stdout or '')+(error.stderr or '')) from error
    if windows or production:
        if file_record(binary)['pe_machine'] != 332:
            raise ValueError('Formal gameplay proof compiler must target Win32')
    return binary


def run_checks(binary, production=False):
    output = subprocess.check_output([str(binary)], text=True, timeout=30)
    assert 'CAP_EXACT_FALLBACK_TEXTURE_FULL_KEYS_BOUNDS_SATURATION_PASS' in output
    assert 'TEXTURE_LOAD_FALLBACK_ASSIGNMENTS_EQUIVALENCE_PASS cases=600' in output
    records = [json.loads(line[len(PROFILE_PREFIX):]) for line in output.splitlines()
        if line.startswith(PROFILE_PREFIX)]
    assert records
    profile = records[-1]
    assert profile['requested_cap'] == profile['effective_cap'] == 30
    assert profile['menu_cap'] == profile['inactive_cap'] == 10
    assert profile['override_applied'] == profile['bounded_texture_errors'] == 1
    errors = [json.loads(line[len(ERROR_PREFIX):]) for line in output.splitlines()
        if line.startswith(ERROR_PREFIX)]
    assert [row['suppressed_total'] for row in errors[-5:]] == [1, 2, 4, 8, 16]
    assert all(row['unique_tracked'] <= 64 and row['ordinal'] <= 32
        and row['first_error_preserved'] == row['asset_loading_unchanged'] == 1 for row in errors)
    if not production:
        assert len(records) == 1 and len(errors) == 5
    return profile, errors


def expected_checks():
    return {'format': 1, 'status': 'passed', 'platform': 'windows', 'architecture': 'Win32',
        'configuration': 'OptDebug', 'compiler_options': OPTIONS,
        'patch_sha256': producer.digest(ROOT/PATCH), 'header_sha256': producer.digest(ROOT/HEADER),
        'harness_sha256': hashlib.sha256(harness().encode()).hexdigest(),
        'production_harness_sha256': hashlib.sha256(harness(True).encode()).hexdigest(),
        'exact_cap_whitelist_and_fallback_verified': True,
        'cache_generation_and_menu_background_caps_preserved': True,
        'runtime_maxfps_override_preserved': True,
        'repeated_texture_errors_bounded_verified': True,
        'full_key_comparison_collision_verified': True,
        'unknown_oversized_and_full_table_fallback_verified': True,
        'loading_white_fallback_and_appearance_assignments_preserved': True,
        'counter_saturation_and_report_cap_verified': True,
        'disabled_diagnostics_preserve_error_path_verified': True,
        'retained_native_crt_macro_isolation_and_restoration_verified': True,
        'genuine_win32_environment_and_crt_verified': True,
        'physical_fps_gain_validated': False}


def validate_windows_checks(checks):
    encode = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
    if encode(checks) != encode(expected_checks()):
        raise ValueError('Exact source-bound genuine Win32 gameplay qualification required')
    return checks


def windows_receipt(output):
    with tempfile.TemporaryDirectory(prefix='coh-win32-gameplay-') as temporary:
        run_checks(compile_harness(temporary, windows=True))
        run_checks(compile_harness(temporary, windows=True, production=True), production=True)
    document = expected_checks()
    validate_windows_checks(document)
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('Fresh gameplay Win32 proof required')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2)+'\n')
    return document


class GameplayNativeTests(unittest.TestCase):
    def test_real_native_profile_deduplication_and_texture_loading_equivalence(self):
        with tempfile.TemporaryDirectory(prefix='coh-gameplay-native-') as temporary:
            run_checks(compile_harness(temporary))

    def test_formal_proof_rejects_any_changed_source_pin_platform_or_behavior_claim(self):
        document = expected_checks()
        self.assertEqual(validate_windows_checks(document), document)
        for name in document:
            wrong = dict(document)
            wrong[name] = None
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_windows_checks(wrong)
        for name, value in document.items():
            if type(value) in (bool, int):
                wrong = dict(document)
                wrong[name] = int(value) if type(value) is bool else float(value)
                with self.subTest(name=name, mutation='JSON_type'), self.assertRaises(ValueError):
                    validate_windows_checks(wrong)

    def test_host_qualification_cannot_masquerade_as_genuine_win32_proof(self):
        with tempfile.TemporaryDirectory(prefix='coh-gameplay-formal-') as temporary:
            output = Path(temporary)/'proof.json'
            if os.name == 'nt':
                self.assertEqual(windows_receipt(output), expected_checks())
            else:
                with self.assertRaisesRegex(ValueError, 'real Win32'):
                    windows_receipt(output)
                self.assertFalse(output.exists())


if __name__ == '__main__':
    if '--windows-qualify' in sys.argv:
        parser = argparse.ArgumentParser()
        parser.add_argument('--windows-qualify', action='store_true')
        parser.add_argument('--output', required=True, type=Path)
        arguments = parser.parse_args()
        windows_receipt(arguments.output)
    else:
        unittest.main()
