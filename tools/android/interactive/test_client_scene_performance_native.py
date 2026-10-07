"""Actual tree/reload call-order equivalence and bounded opt-in scene timing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT / 'tools')]
import package_client_loading_native as loading
from prepare_resume_client_source import apply_patch

PATCH = 'patches/client-scene-performance/0001-scene-loading-phase-and-preload.patch'
HEADER = 'android/native/client-scene-performance/cohClientSceneTiming.h'
OVERLAY = 'Game/src/cohClientSceneTiming.h'
FILES = ('Common/seq/gfxtree.c', 'Common/seq/gfxtree.h', 'Game/src/game.c',
         'Game/src/clientcomm/clientcomm.c', 'Game/src/group/groupnetrecv.c',
         'Game/src/graphics/gfx.c')
OPTIONS = ['/O2', '/Oy-', '/MT', '/TC']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sources():
    old = {name: (ROOT / 'upstream/ouroboros' / name).read_text() for name in FILES}
    with tempfile.TemporaryDirectory(prefix='coh-scene-patch-proof-') as temporary:
        source = Path(temporary)
        for name, value in old.items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value)
        patch = (ROOT / PATCH).read_bytes().replace(b'\r\n', b'\n')
        names = tuple(line[6:] for line in patch.decode().splitlines() if line.startswith('+++ b/'))
        assert names == FILES, 'Unexpected scene source member'
        apply_patch(source, patch)
        new = {name: (source / name).read_text() for name in FILES}
        loading.reverse_patch(source, patch)
        assert all((source / name).read_text() == value for name, value in old.items())
    return old, new


def strip_timing(text):
    text = re.sub(r'^[ \t]*DWORD coh_scene_phase = cohClientSceneBegin\(\);\n', '', text, flags=re.M)
    return re.sub(r'^[ \t]*cohClientScenePhase\([^\n]+\);[ \t]*\n', '', text, flags=re.M)


def source_proof():
    old, new = sources()
    pairs = [('Game/src/game.c', 'void game_loadData('),
             ('Game/src/clientcomm/clientcomm.c', 'int commReqScene('),
             ('Game/src/group/groupnetrecv.c', 'void worldReceiveGroups(')]
    for name, signature in pairs:
        assert strip_timing(loading.function(new[name], signature)) == loading.function(old[name], signature)
    before = loading.function(old['Game/src/graphics/gfx.c'], 'void gfxReload(')
    after = strip_timing(loading.function(new['Game/src/graphics/gfx.c'], 'void gfxReload('))
    option = ('        if (cohClientSceneDeferDiscardedFx())\n'
              '            gfxTreeInitForGfxReload();\n        else\n            gfxTreeInit();')
    assert after.replace(option, '        gfxTreeInit();', 1) == before
    tree_before = loading.function(old['Common/seq/gfxtree.c'], 'void gfxTreeInitCharacterAndFxTree(')
    tree_after = loading.function(new['Common/seq/gfxtree.c'], 'static void cohGfxTreeInitCharacterAndFxTree(')
    tree_after = tree_after.replace('static void cohGfxTreeInitCharacterAndFxTree(int defer_discarded_fx)',
                                   'void gfxTreeInitCharacterAndFxTree()', 1)
    tree_after = tree_after.replace('    if (!defer_discarded_fx)\n        fxPreloadGeometry();',
                                   '    fxPreloadGeometry();', 1)
    assert tree_after == tree_before
    return True


def harness():
    old, new = sources()
    functions = loading.function
    original = '\n'.join(functions(old[name], signature) for name, signature in (
        ('Common/seq/gfxtree.c', 'void gfxTreeInitCharacterAndFxTree('),
        ('Common/seq/gfxtree.c', 'void gfxTreeInit('), ('Game/src/graphics/gfx.c', 'void gfxReload(')))
    candidate = '\n'.join(functions(new[name], signature) for name, signature in (
        ('Common/seq/gfxtree.c', 'static void cohGfxTreeInitCharacterAndFxTree('),
        ('Common/seq/gfxtree.c', 'void gfxTreeInitCharacterAndFxTree('),
        ('Common/seq/gfxtree.c', 'static void cohGfxTreeInit('),
        ('Common/seq/gfxtree.c', 'void gfxTreeInit('),
        ('Common/seq/gfxtree.c', 'void gfxTreeInitForGfxReload('),
        ('Game/src/graphics/gfx.c', 'void gfxReload(')))
    prefix = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#ifdef _WIN64
#error Actual Win32 qualification required
#endif
#else
typedef uint32_t DWORD;
static DWORD tick;
static DWORD GetTickCount(void) { return tick++; }
#endif
#define CLIENT 1
#define NOVODEX 0
#define GFXDEBUG 0
#define PERFINFO_AUTO_START(a,b) ((void)0)
#define PERFINFO_AUTO_STOP() ((void)0)
#define PERFINFO_AUTO_STOP_CHECKED(a) ((void)0)
typedef int GeoUseType;
typedef struct GfxNode { int unused; } GfxNode;
#define GEO_USED_BY_GFXTREE 1
#define GEO_USED_BY_WORLD 2
#define GEO_INIT_FOR_DRAWING 4
#define GEO_DONT_INIT_FOR_DRAWING 8
static int gfxnode_mp, gfx_tree_root, gfx_tree_root_tail;
static struct { int simpleShadow, simpleShadowUniqueId; } cam_info;
static char trace[1024]; static int trace_count, fx_count, free_count, live_models, inventory;
static void mark(char value) { assert(trace_count<1023);trace[trace_count++]=value;trace[trace_count]=0; }
static void destroyMemoryPoolGfxNode(int v) { assert(v==1);mark('D'); }
static int createMemoryPool(void) {mark('C');return 1;}
static void initMemoryPool(int v,int size,int count) { assert(v==1&&size==sizeof(GfxNode)&&count==2000);mark('I'); }
static void modelFreeAllCache(GeoUseType flags) { assert(flags==1||flags==15);++free_count;live_models=0;mark('M'); }
static void skyNotifyGfxTreeDestroyed(void) {mark('N');}
static void gfxTreeInitSkyTree(void) {mark('Y');}
static void fxPreloadGeometry(void) {++fx_count;live_models=inventory;mark('X');}
static void ErrorfResetCounts(void) {mark('E');}
static void fxReInit(void) {mark('F');}
static void entReset(void) {mark('R');}
static void playerSetEnt(int p) { assert(p==0);mark('P'); }
static void groupReset(void) {mark('G');}
static void rdrInit(void) {mark('V');}
static void loadBG(void) {mark('B');}
static void sunSetSkyFadeClient(int a,int b,double c) {assert(a==0&&b==1&&c==0);mark('S');}
static void sceneLoad(const char *name) {assert(strcmp(name,"scenes/default_scene.txt")==0);mark('L');}
static void reset(void) { trace_count=fx_count=free_count=live_models=0;trace[0]=0;gfxnode_mp=1;gfx_tree_root=gfx_tree_root_tail=7;cam_info.simpleShadow=cam_info.simpleShadowUniqueId=9; }
'''
    return (prefix + (ROOT / HEADER).read_text() + '\n'
        '#define gfxTreeInitCharacterAndFxTree oldGfxTreeInitCharacterAndFxTree\n'
        '#define gfxTreeInit oldGfxTreeInit\n#define gfxReload oldGfxReload\n' + original
        + '\n#undef gfxTreeInitCharacterAndFxTree\n#undef gfxTreeInit\n#undef gfxReload\n'
        + candidate + r'''
int main(int argc,char **argv) {
    char stock[1024], expected[1024]; int unload,inv,enabled=cohClientSceneDeferDiscardedFx();
    if(argc>1 && strcmp(argv[1],"profile")==0) {
        DWORD begin=cohClientSceneBegin();int j;
        for(j=0;j<300;j++)cohClientScenePhase("bounded_fixture",&begin,j%2);
        printf("SCENE_PROFILE_BOUND_PASS\n");return 0;
    }
    for(unload=0;unload<=1;unload++) for(inv=0;inv<3;inv++) {
        inventory=inv==0?0:inv==1?1:31;
        reset();oldGfxReload(unload);strcpy(stock,trace);
        assert(fx_count==2&&free_count==2&&live_models==inventory);
        strcpy(expected,stock);
        if(enabled) {char *x=strchr(expected,'X');assert(x);memmove(x,x+1,strlen(x));}
        reset();gfxReload(unload);
        assert(strcmp(trace,expected)==0&&fx_count==(enabled?1:2)&&free_count==2&&live_models==inventory);
        assert(gfx_tree_root==0&&gfx_tree_root_tail==0&&cam_info.simpleShadow==0&&cam_info.simpleShadowUniqueId==0);
        reset();oldGfxTreeInit();strcpy(stock,trace);
        reset();gfxTreeInit();assert(strcmp(trace,stock)==0&&fx_count==1);
        reset();oldGfxTreeInitCharacterAndFxTree();strcpy(stock,trace);
        reset();gfxTreeInitCharacterAndFxTree();assert(strcmp(trace,stock)==0&&fx_count==1);
    }
    printf("SCENE_RELOAD_EQUIVALENCE_PASS enabled=%d cases=6 invalidations=2 surviving_preload=1 default_after_candidate=1\n",enabled);
    return 0;
}
''')


def compile_harness(directory, windows=False):
    path = Path(directory) / 'scene-proof.c'; path.write_text(harness())
    if windows:
        compiler = shutil.which('cl'); assert compiler, 'Actual Win32 MSVC required'
        binary = Path(directory) / 'scene-proof.exe'
        command = [compiler, '/nologo', *OPTIONS, str(path), '/Fe:' + str(binary)]
    else:
        compiler = shutil.which('cc') or shutil.which('gcc'); assert compiler, 'C compiler required'
        binary = Path(directory) / 'scene-proof'
        command = [compiler, '-std=c11', '-O2', str(path), '-o', str(binary)]
    subprocess.run(command, cwd=directory, check=True, capture_output=True, text=True)
    return binary


def run_checks(binary):
    for enabled in ('', '0', '01', '1', 'invalid'):
        environment = dict(os.environ, COH_CLIENT_DEFER_DISCARDED_FX_PRELOAD=enabled,
                           COH_CLIENT_SCENE_PROFILE='0')
        result = subprocess.check_output([str(binary)], env=environment, text=True)
        assert 'enabled=' + str(int(enabled == '1')) in result
        assert 'COH_CLIENT_SCENE_PHASE_V1' not in result
    for profile in ('', '0', '01', '1', 'invalid'):
        environment = dict(os.environ, COH_CLIENT_SCENE_PROFILE=profile)
        result = subprocess.check_output([str(binary), 'profile'], env=environment, text=True)
        assert result.count('COH_CLIENT_SCENE_PHASE_V1') == (128 if profile == '1' else 0)
    source_proof()


def expected_checks():
    return {'format': 1, 'status': 'passed', 'platform': 'windows', 'architecture': 'Win32',
        'configuration': 'OptDebug', 'compiler_options': OPTIONS,
        'harness_sha256': hashlib.sha256(harness().encode()).hexdigest(),
        'patch_sha256': digest(ROOT / PATCH), 'header_sha256': digest(ROOT / HEADER),
        'baseline_fallback_verified': True, 'discarded_preload_elision_verified': True,
        'surviving_preload_and_invalidation_verified': True, 'scene_phase_bound_verified': True,
        'scene_failure_and_wait_paths_preserved': True, 'physical_scene_savings_validated': False}


def validate_windows_checks(checks):
    assert checks == expected_checks(), 'Source-bound Win32 scene qualification differs'
    return checks


class SceneNativeTests(unittest.TestCase):
    def test_production_scene_crc_waits_geometry_and_texture_completion_remain_exact(self):
        self.assertTrue(source_proof())

    def test_native_reload_equivalence_fallback_and_bounded_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            run_checks(compile_harness(directory))

    def test_qualification_refuses_any_changed_pin_or_semantic_claim(self):
        receipt = expected_checks()
        self.assertEqual(validate_windows_checks(receipt), receipt)
        for key in receipt:
            wrong = dict(receipt); wrong[key] = None
            with self.subTest(key=key), self.assertRaises(AssertionError): validate_windows_checks(wrong)


if __name__ == '__main__':
    if '--windows-qualify' in sys.argv:
        parser = argparse.ArgumentParser(); parser.add_argument('--windows-qualify', action='store_true')
        parser.add_argument('--output', type=Path, required=True); arguments = parser.parse_args()
        with tempfile.TemporaryDirectory(prefix='coh-win32-scene-') as directory:
            run_checks(compile_harness(directory, windows=True))
        arguments.output.write_text(json.dumps(expected_checks(), indent=2) + '\n')
    else:
        unittest.main()
