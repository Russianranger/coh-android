"""Execute the native minimum preset and reversible launch-only overlay.

These host checks cover policy and preference preservation, not device FPS or
OpenGL framebuffer compatibility; those remain physical-device observations.
"""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
GRAPHICS = ROOT / 'upstream/ouroboros/Game/src/graphics'
sys.path.insert(0, str(ROOT / 'tools'))
import prepare_client_graphics_source as graphics


def function(source, declaration):
    start = source.index(declaration)
    opening = source.index('{', start)
    depth = 1
    position = opening + 1
    while depth:
        depth += (source[position] == '{') - (source[position] == '}')
        position += 1
    return source[start:position]


HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
enum { SHADOW_OFF=0, CUBEMAP_OFF=0, WATER_OFF=0, AMBIENT_DISABLE=0,
       SHADERDETAIL_NOBUMPS=4, RENDERSCALE_SCALE=1 };
typedef struct Advanced {
    int suppressCloseFx, physicsQuality, ageiaOn, mipLevel, entityMipLevel;
    float worldDetailLevel, entityDetailLevel;
    int maxParticles, maxParticleFill, useVSync, colorMouseCursor;
    int shadowMode, cubemapMode, enableVBOs, texLodBias, texAniso, shaderDetail;
    int useWater, buildingPlanarReflections, useBloom;
    float bloomMagnitude;
    int useDOF;
    float dofMagnitude;
    int useDesaturate;
    struct { int option; } ambient;
} Advanced;
typedef struct GfxSettings {
    Advanced advanced;
    int antialiasing, useRenderScale;
    float renderScaleX, renderScaleY;
    int screenX, screenY, fullScreen;
    float gamma, fxSoundVolume;
    char accountName[32];
} GfxSettings;
static int IsUsingWin9x(void) { return 0; }
static void gfxSettingsApplyRestrictions(GfxSettings *s) { (void)s; }
static void gfxUpdateAmbientAdvanced(GfxSettings *s) { (void)s; }
static void gfxUpdateShadowMapAdvanced(GfxSettings *s) { (void)s; }
MINIMUM_FUNCTION
#include "PROFILE_HEADER"
LAUNCHER_FUNCTION
static void require(int condition, const char *message) {
    if (!condition) { fprintf(stderr,"%s\n",message); exit(1); }
}
static GfxSettings baseline(void) {
    GfxSettings value;
    memset(&value,0,sizeof(value));
    value.screenX=800; value.screenY=600; value.fullScreen=1;
    value.gamma=1.2f; value.fxSoundVolume=0.8f;
    strcpy(value.accountName,"COHLOCAL");
    value.advanced.mipLevel=-1; value.advanced.entityMipLevel=0;
    value.advanced.worldDetailLevel=1.0f; value.advanced.entityDetailLevel=1.0f;
    value.advanced.maxParticles=50000; value.advanced.useVSync=1;
    value.advanced.shadowMode=3; value.advanced.useWater=4;
    value.advanced.cubemapMode=1; value.advanced.useBloom=1;
    value.advanced.useDOF=1; value.advanced.useDesaturate=1;
    value.advanced.buildingPlanarReflections=1; value.advanced.ambient.option=2;
    value.antialiasing=4; value.renderScaleX=value.renderScaleY=1.0f;
    return value;
}
int main(int argc,char **argv) {
    GfxSettings original=baseline(), runtime=original, persisted;
    CohAndroidGraphicsProfile profile={0};
    if (argc!=2) return 2;
    if (!strcmp(argv[1],"performance")) {
        require(cohAndroidGraphicsProfileApply(&profile,"performance",&runtime,gfxGetMinAdvancedSettings),"profile not applied");
        require(runtime.renderScaleX==0.75f && runtime.renderScaleY==0.75f && runtime.useRenderScale==RENDERSCALE_SCALE,"world scale");
        require(runtime.screenX==800 && runtime.screenY==600 && runtime.fullScreen==1,"UI dimensions");
        require(runtime.advanced.worldDetailLevel==0.5f && runtime.advanced.entityDetailLevel==0.3f,"detail levels");
        require(runtime.advanced.mipLevel==3 && runtime.advanced.entityMipLevel==3,"texture reduction");
        require(runtime.advanced.maxParticles==100 && runtime.antialiasing==0,"particle/AA policy");
        require(!runtime.advanced.shadowMode && !runtime.advanced.useWater && !runtime.advanced.cubemapMode,"shadow/reflection effects");
        require(!runtime.advanced.useBloom && !runtime.advanced.useDOF && !runtime.advanced.useDesaturate && !runtime.advanced.ambient.option,"postprocessing effects");
        require(!runtime.advanced.buildingPlanarReflections && runtime.advanced.shaderDetail==SHADERDETAIL_NOBUMPS,"shader/reflection policy");
        require(runtime.gamma==original.gamma && runtime.fxSoundVolume==original.fxSoundVolume && !strcmp(runtime.accountName,original.accountName),"unrelated settings changed");
        persisted=runtime; cohAndroidGraphicsProfileSaved(&profile,&persisted);
        require(!memcmp(&original,&persisted,sizeof(original)),"original preferences not preserved");
    } else if (!strcmp(argv[1],"reapply")) {
        cohAndroidGraphicsProfileApply(&profile,"performance",&runtime,gfxGetMinAdvancedSettings);
        runtime.gamma=2.0f; runtime.screenX=1920; runtime.renderScaleX=0.5f;
        cohAndroidGraphicsProfileApply(&profile,"performance",&runtime,gfxGetMinAdvancedSettings);
        persisted=runtime; cohAndroidGraphicsProfileSaved(&profile,&persisted);
        require(!memcmp(&original,&persisted,sizeof(original)),"renderer reapply overwrote original preferences");
        require(runtime.renderScaleX==0.75f,"reapply lost profile");
    } else if (!strcmp(argv[1],"standard")) {
        const char *values[]={NULL,"standard","PERFORMANCE","performance ","custom"};
        size_t i;
        for(i=0;i<sizeof(values)/sizeof(values[0]);i++) {
            require(!cohAndroidGraphicsProfileApply(&profile,values[i],&runtime,gfxGetMinAdvancedSettings),"unselected profile applied");
            cohAndroidGraphicsProfileSaved(&profile,&runtime);
            require(!profile.captured && !memcmp(&original,&runtime,sizeof(original)),"standard preferences changed");
        }
    } else if (!strcmp(argv[1],"launcher")) {
        require(!strcmp(graphics_policy(5,"--character-creation","performance"),"performance"),"interactive performance missing");
        require(!strcmp(graphics_policy(5,"--character-creation","standard"),"standard"),"standard request changed");
        require(!strcmp(graphics_policy(5,"--generate-caches","performance"),"standard"),"cache generation changed");
        require(!strcmp(graphics_policy(5,"--local-login","performance"),"standard"),"local login diagnostic changed");
        require(!strcmp(graphics_policy(4,NULL,"performance"),"standard"),"baseline diagnostic changed");
        require(!strcmp(graphics_policy(5,"--character-creation",NULL),"standard"),"unset environment changed");
        require(!graphics_policy(5,"--character-creation","PERFORMANCE") && !graphics_policy(5,"--character-creation","performance -screen 1 1"),"unrecognized profile accepted");
    } else return 3;
    puts("ok");
    return 0;
}
'''


class GraphicsProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-graphics-profile-')
        cls.directory = Path(cls.temporary.name)
        source = HARNESS.replace('MINIMUM_FUNCTION', function(
            (GRAPHICS / 'gfxSettings.c').read_text(), 'static void gfxGetMinAdvancedSettings('))
        source = source.replace('LAUNCHER_FUNCTION', function(
            (ROOT / 'android/native/client-launcher.c').read_text(), 'static const char *graphics_policy('))
        source = source.replace('PROFILE_HEADER', (ROOT / graphics.OVERLAY / graphics.OVERLAY_FILES[0]).as_posix())
        fixture = cls.directory / 'profile.c'
        fixture.write_text(source)
        cls.executable = cls.directory / 'profile'
        subprocess.run(['cc', '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror',
                        str(fixture), '-o', str(cls.executable)], check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def run_profile(self, mode):
        self.assertEqual(subprocess.check_output([str(self.executable), mode], text=True, timeout=10), 'ok\n')

    def test_actual_minimum_preset_preserves_interface_and_saved_preferences(self):
        self.run_profile('performance')

    def test_reapplying_renderer_settings_retains_original_snapshot(self):
        self.run_profile('reapply')

    def test_standard_unset_and_unrecognized_profiles_leave_preferences_unchanged(self):
        self.run_profile('standard')

    def test_launcher_limits_overlay_to_interactive_mode_and_rejects_unknown_values(self):
        self.run_profile('launcher')


class GraphicsSourceOverlayTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='coh-graphics-source-')
        self.addCleanup(temporary.cleanup)
        self.source = Path(temporary.name) / 'source'
        self.source.mkdir()
        self.name = graphics.GRAPHICS_FILES[0]
        self.path = self.source / self.name
        self.path.parent.mkdir(parents=True)
        shutil.copy2(ROOT / 'upstream/ouroboros' / self.name, self.path)

    def test_overlay_changes_only_graphics_and_preserves_immutable_source(self):
        original = graphics.sha256(ROOT / 'upstream/ouroboros' / self.name)
        receipt = graphics.apply_graphics_overlay(self.source)
        self.assertEqual(receipt, graphics.expected_graphics_receipt())
        self.assertEqual(json.loads((self.source / graphics.RECEIPT).read_text()), receipt)
        self.assertEqual(graphics.sha256(self.path), receipt['patched_sha256'][self.name])
        self.assertEqual(graphics.sha256(ROOT / 'upstream/ouroboros' / self.name), original)
        self.assertEqual(set(receipt['patched_sha256']), {self.name})
        self.assertEqual(receipt['build_targets'], ['Game'])
        self.assertEqual(receipt['runtime_validation'], 'unverified')
        text = self.path.read_text()
        self.assertIn('cohAndroidGraphicsProfileApply(&cohAndroidGraphicsProfile,', text)
        self.assertIn('cohAndroidGraphicsProfileSaved(&cohAndroidGraphicsProfile, gfxSettings);', text)

    def test_dirty_source_rejected_without_mutation(self):
        self.path.write_bytes(self.path.read_bytes() + b'\n/* foreign */\n')
        original = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'source SHA-256 mismatch'):
            graphics.apply_graphics_overlay(self.source)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse((self.source / graphics.RECEIPT).exists())

    def test_existing_linked_repeat_and_upstream_destinations_rejected(self):
        target = self.source / graphics.OVERLAY_FILES[0]
        target.write_text('foreign')
        with self.assertRaisesRegex(ValueError, 'would overwrite source'):
            graphics.apply_graphics_overlay(self.source)
        target.unlink()
        target.symlink_to(self.path)
        with self.assertRaisesRegex(ValueError, 'would overwrite source'):
            graphics.apply_graphics_overlay(self.source)
        target.unlink()
        graphics.apply_graphics_overlay(self.source)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            graphics.apply_graphics_overlay(self.source)
        with self.assertRaisesRegex(ValueError, 'immutable snapshots'):
            graphics.apply_graphics_overlay(ROOT / 'upstream/ouroboros')


if __name__ == '__main__':
    unittest.main()
