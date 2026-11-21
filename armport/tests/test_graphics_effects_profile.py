"""0.13.73, ArmPort patch 0129: the ARM64 client's launch-only `effects_off` graphics profile.

Thor 0.13.72 (2026-11-17): 19-26 frames a second looking one way and 35-59 another, with the
whole client under one core in the slow case. The app's "Use performance graphics" option had
never reached the ARM64 client. The patch adds a self-contained header; this test takes it out
of the patch and runs it on the host against a stand-in for the game's settings structure.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / 'armport/patches/0129-armport-graphics-effects-profile.patch'
HEADER = 'Game/src/graphics/cohArmportGraphicsProfile.h'

HARNESS = r'''
#include <stdio.h>
typedef enum { WATER_OFF, WATER_LOW, WATER_MED } OptionWater;
typedef enum { BLOOM_OFF, BLOOM_REGULAR } OptionBloom;
typedef enum { SHADOW_OFF, SHADOW_STENCIL } OptionShadow;
typedef enum { CUBEMAP_OFF, CUBEMAP_LOWQUALITY } OptionCubemap;
typedef enum { AMBIENT_DISABLE, AMBIENT_BALANCED } OptionAmbient;
typedef enum { AMBIENT_OFF, AMBIENT_MEDIUM } OptionAmbientStrength;
typedef struct GfxSettings {
    struct {
        int mipLevel, useWater, buildingPlanarReflections, useBloom, useDOF, useDesaturate, shadowMode,
            cubemapMode, useVSync;
        float worldDetailLevel;
        struct { int option, strength; } ambient;
    } advanced;
    int antialiasing, screenX;
    float renderScaleX;
} GfxSettings;
/* The game redefines these; the header must still reach the C library's. */
#define printf game_printf_must_not_be_used
#define fflush game_fflush_must_not_be_used
#define fputs game_fputs_must_not_be_used
#include "cohArmportGraphicsProfile.h"
#undef printf
#undef fflush
#undef fputs

static GfxSettings recommended(void)
{
    GfxSettings value = {0};
    value.advanced.mipLevel = -1; value.advanced.worldDetailLevel = 1.0f;
    value.advanced.useWater = WATER_MED; value.advanced.useBloom = BLOOM_REGULAR; value.advanced.useDOF = 1;
    value.advanced.useDesaturate = 1; value.advanced.shadowMode = SHADOW_STENCIL; value.advanced.useVSync = 1;
    value.advanced.cubemapMode = CUBEMAP_LOWQUALITY; value.advanced.buildingPlanarReflections = 1;
    value.advanced.ambient.option = AMBIENT_BALANCED; value.advanced.ambient.strength = AMBIENT_MEDIUM;
    value.antialiasing = 4; value.screenX = 800; value.renderScaleX = 1.0f;
    return value;
}

static void show(const char *label, int applied, const GfxSettings *s)
{
    printf("%s applied=%d water=%d planar=%d bloom=%d dof=%d desaturate=%d shadow=%d cubemap=%d ambient=%d/%d "
           "vsync=%d aa=%d mip=%d detail=%.1f screen=%d scale=%.2f\n", label, applied, s->advanced.useWater,
           s->advanced.buildingPlanarReflections, s->advanced.useBloom, s->advanced.useDOF, s->advanced.useDesaturate,
           s->advanced.shadowMode, s->advanced.cubemapMode, s->advanced.ambient.option, s->advanced.ambient.strength,
           s->advanced.useVSync, s->antialiasing, s->advanced.mipLevel, s->advanced.worldDetailLevel, s->screenX,
           s->renderScaleX);
}

int main(void)
{
    static CohArmportGraphicsProfile profile;
    GfxSettings settings = recommended(), later, saved;
    int applied = cohArmportGraphicsProfileApply(&profile, &settings);
    show("first", applied, &settings);
    /* The player changes an option in the game while the profile is on. */
    later = recommended(); later.screenX = 1024; later.advanced.useWater = WATER_LOW;
    applied = cohArmportGraphicsProfileApply(&profile, &later);
    show("later", applied, &later);
    /* What the game writes back for next time. */
    saved = later;
    cohArmportGraphicsProfileSaved(&profile, &saved);
    show("saved", profile.captured, &saved);
    return 0;
}
'''


def added_file(patch, name):
    block = re.search(r'^diff --git a/%s b/%s\n.*?(?=^diff --git |\Z)' % (re.escape(name), re.escape(name)),
                      patch, re.M | re.S)
    assert block is not None and '\n--- /dev/null\n' in block.group(0)
    lines = block.group(0).split('\n@@', 1)[1].split('\n')[1:]
    assert all(line.startswith('+') for line in lines if line)
    return '\n'.join(line[1:] for line in lines)


class GraphicsEffectsProfile(unittest.TestCase):
    def test_patch_shape(self):
        patch = PATCH.read_text()
        self.assertEqual(sorted(re.findall(r'^diff --git a/(\S+) ', patch, re.M)),
                         [HEADER, 'Game/src/graphics/gfxSettings.c'])
        self.assertIn('+#include "graphics/cohArmportGraphicsProfile.h"', patch)
        self.assertIn('+    cohArmportGraphicsProfileApply(&cohArmportGraphicsProfile, gfxSettings);', patch)
        self.assertIn('+    cohArmportGraphicsProfileSaved(&cohArmportGraphicsProfile, gfxSettings);', patch)
        # Its own variable: the launcher program resets COH_CLIENT_GRAPHICS_PROFILE to the values it knows.
        self.assertIn('getenv("ARMPORT_GRAPHICS_PROFILE")', patch)
        self.assertNotIn('getenv("COH_CLIENT_GRAPHICS_PROFILE")', patch)
        launcher = ROOT / 'android/native/client-launcher.c'
        if launcher.is_file():          # not in the build workflow's sparse checkout (run 44115020828)
            self.assertIn('SetEnvironmentVariableA("COH_CLIENT_GRAPHICS_PROFILE",graphics)', launcher.read_text())
            self.assertNotIn('ARMPORT_GRAPHICS_PROFILE', launcher.read_text())
        self.assertIn(PATCH.name, (ROOT / 'armport/patches/series').read_text().split()[-2:])   # 0130 follows it

    def run_harness(self, value):
        compiler = shutil.which('gcc') or shutil.which('cc')
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            (work / 'cohArmportGraphicsProfile.h').write_text(added_file(PATCH.read_text(), HEADER))
            (work / 'harness.c').write_text(HARNESS)
            subprocess.run([compiler, '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-O1', '-o', str(work / 'harness'),
                            str(work / 'harness.c')], check=True, cwd=work, timeout=120)
            environment = {key: text for key, text in os.environ.items() if key != 'ARMPORT_GRAPHICS_PROFILE'}
            if value is not None:
                environment['ARMPORT_GRAPHICS_PROFILE'] = value
            return subprocess.run([str(work / 'harness')], check=True, capture_output=True, text=True, timeout=30,
                                  env=environment).stdout.splitlines()

    OFF = 'water=0 planar=0 bloom=0 dof=0 desaturate=0 shadow=0 cubemap=0 ambient=0/0 vsync=0 aa=0 '
    OWN = 'water=2 planar=1 bloom=1 dof=1 desaturate=1 shadow=1 cubemap=1 ambient=1/1 vsync=1 aa=4 '

    @unittest.skipUnless(shutil.which('gcc') or shutil.which('cc'), 'no host C compiler')
    def test_effects_off_keeps_detail_and_the_saved_settings(self):
        output = self.run_harness('effects_off')
        self.assertEqual(len(output), 4, output)
        self.assertTrue(output[0].startswith('ARMPORT_GRAPHICS_PROFILE_V1 effects_off water=0 '), output[0])   # logged once
        self.assertEqual(output[1], 'first applied=1 ' + self.OFF + 'mip=-1 detail=1.0 screen=800 scale=1.00')
        self.assertEqual(output[2], 'later applied=1 ' + self.OFF + 'mip=-1 detail=1.0 screen=1024 scale=1.00')
        # The first settings seen are what is written back, not the profile.
        self.assertEqual(output[3], 'saved applied=1 ' + self.OWN + 'mip=-1 detail=1.0 screen=800 scale=1.00')

    @unittest.skipUnless(shutil.which('gcc') or shutil.which('cc'), 'no host C compiler')
    def test_any_other_value_changes_nothing(self):
        for value in (None, 'standard', 'performance', 'effects_off ', ''):
            with self.subTest(value=value):
                output = self.run_harness(value)
                self.assertEqual(output[0], 'first applied=0 ' + self.OWN + 'mip=-1 detail=1.0 screen=800 scale=1.00')
                self.assertEqual(output[1], 'later applied=0 water=1 ' + self.OWN.split(' ', 1)[1]
                                 + 'mip=-1 detail=1.0 screen=1024 scale=1.00')
                self.assertEqual(output[2], 'saved applied=0 water=1 ' + self.OWN.split(' ', 1)[1]
                                 + 'mip=-1 detail=1.0 screen=1024 scale=1.00')

    def test_guest_app_and_ci_plumbing(self):
        guest = (ROOT / 'armport/app/armport_interactive.py').read_text()
        self.assertIn("value = environ.get('COH_ARMPORT_GRAPHICS_PROFILE', 'standard')", guest)
        self.assertIn("ARMPORT_STDIO_LOG='armport_stdio.txt', COH_CLIENT_GRAPHICS_PROFILE='standard',", guest)
        self.assertIn('ARMPORT_GRAPHICS_PROFILE=graphics,', guest)
        self.assertIn("GRAPHICS_PROFILE_MARK = b'ARMPORT_GRAPHICS_PROFILE_V1 effects_off '", guest)
        self.assertIn('fputs("ARMPORT_GRAPHICS_PROFILE_V1 effects_off water=0 ', PATCH.read_text())
        java = (ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/'
                'ClientRuntime.java').read_text()
        self.assertIn('armportGraphicsProfileRequested="arm64".equals(clientArchitectureRequested)'
                      '&&performanceGraphicsEnabled(context)?"effects_off":"standard";', java)
        self.assertIn('"COH_ARMPORT_GRAPHICS_PROFILE="+armportGraphicsProfileRequested,', java)
        # The x86 client's variable keeps the two values its launcher accepts.
        self.assertIn('graphicsProfileRequested="arm64".equals(clientArchitectureRequested)?"standard":'
                      'performanceGraphicsEnabled(context)?"performance":"standard";', java)
        host = (ROOT / 'armport/app/interactive_host.py').read_text()
        self.assertIn("next_command.insert(next_command.index('/usr/bin/python3'), "
                      "'COH_ARMPORT_GRAPHICS_PROFILE=effects_off')", host)
        self.assertIn("print('ARMPORT_GRAPHICS_PROFILE_V1 ' + json.dumps(", host)

    def test_guest_reads_the_request_and_the_clients_confirmation(self):
        import ast
        tree = ast.parse((ROOT / 'armport/app/armport_interactive.py').read_text())
        wanted = [node for node in tree.body
                  if (isinstance(node, ast.Assign) and getattr(node.targets[0], 'id', '').startswith('GRAPHICS_PROFILE'))
                  or (isinstance(node, ast.FunctionDef) and node.name in ('armport_graphics_profile',
                                                                         'graphics_profile_confirmed'))]
        self.assertEqual(len(wanted), 4)
        namespace = {'os': os}
        exec(compile(ast.Module(body=wanted, type_ignores=[]), 'armport_interactive.py', 'exec'), namespace)
        profile, confirmed = namespace['armport_graphics_profile'], namespace['graphics_profile_confirmed']
        self.assertEqual(profile({}), 'standard')
        self.assertEqual(profile({'COH_ARMPORT_GRAPHICS_PROFILE': 'effects_off'}), 'effects_off')
        self.assertEqual(profile({'COH_ARMPORT_GRAPHICS_PROFILE': 'performance'}), 'standard')
        self.assertEqual(profile({'COH_CLIENT_GRAPHICS_PROFILE': 'effects_off'}), 'standard')
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / 'armport_stdio.txt'
            self.assertIs(confirmed(log), False)                                   # no log at all
            log.write_bytes(b'[INFO] Running City of Heroes\n')
            self.assertIs(confirmed(log), False)
            self.assertIs(confirmed(log, b'x\nARMPORT_GRAPHICS_PROFILE_V1 effects_off water=0 bloom=0\n'), True)
            log.write_bytes(b'[INFO] x\nARMPORT_GRAPHICS_PROFILE_V1 effects_off water=0 bloom=0 dof=0\n' + b'y' * 4096)
            self.assertIs(confirmed(log), True)


if __name__ == '__main__':
    unittest.main()
