"""Execute actual GPU-probe helpers and reject incomplete/false success records.

The C test seam excludes Windows APIs only. No fixture can establish a working
WGL context, GPU execution, Game/Cg compatibility, or Android presentation.
The separate production job compiles the full PE32 program; Thor runs its real
API exercise under an independently pinned Vulkan physical-device gate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'android/native/coh-gpu-probe.c'
WINDOWS_EVIDENCE_DIR = None
BOOL_FIELDS = (
    'zink_nonsoftware', 'multitexture', 'texture_compression',
    'arb_vertex_program', 'arb_fragment_program', 'framebuffer_extension',
    'vertex_buffer_object', 's3tc', 'npot', 'bgra_extension', 'api_loaded',
    'arb_programs', 'multitexture_render', 'vbo_render', 'npot_depth24_fbo',
    'dxt1_render', 'dxt3_render', 'dxt5_render', 'dxt1_mipmaps', 'dxt3_mipmaps',
    'dxt5_mipmaps', 'dxt1_subimage', 'dxt3_subimage', 'dxt5_subimage',
    'bgra_render', 'bgra_subimage', 'backbuffer_render', 'swapped',
    'presented_pattern_first', 'presented_pattern_second', 'presented_readback', 'cleanup_ok',
)
FIXTURE_MARKER = 'COH_GPU_PROBE_BUILD:host_fixture'
PRODUCTION_MARKER = 'COH_GPU_PROBE_BUILD:production'
FIXTURE = r'''
#define COH_GPU_PROBE_TEST
#include SOURCE_PATH

static void positive(struct probe_result *r) {
    memset(r,0,sizeof(*r));
    r->pointer_bits = 32;
    r->fp_max_local_parameters = 32;
    r->fp_max_temporaries = 17;
    r->fp_max_native_temporaries = 17;
    r->frontbuffer_readback = 1;
    r->presentation_client_width = r->presentation_client_height = PRESENTATION_SIZE;
    r->presentation_attempts_first = r->presentation_attempts_second = 1;
    {
        unsigned int i;
        for (i = 0; i < SAMPLE_COUNT; ++i) {
            memcpy(r->presented_pixels_first[i],pattern_rgba[i],3);
            memcpy(r->presented_pixels_second[i],presentation_alternate_rgba[i],3);
        }
    }
    POSITIVE_FIELDS
}

int main(int argc, char **argv) {
    struct probe_result r;
    unsigned char actual[4][4], expected[4][4], data[64], bgra[60], rgb[4][3];
    unsigned int i;
    char string[1025], copied[513];
    if (argc != 2) return 2;
    positive(&r); memcpy(actual,pattern_rgba,sizeof(actual));
    if (!strcmp(argv[1],"pointer_bits")) printf("%u",(unsigned int)(sizeof(void *)*8));
    else if (!strcmp(argv[1],"correct")) printf("%d",pixels_match(actual,pattern_rgba));
    else if (!strcmp(argv[1],"rounding")) {
        actual[0][0] = 252; actual[0][1] = 3; actual[2][3] = 252;
        printf("%d",pixels_match(actual,pattern_rgba));
    } else if (!strcmp(argv[1],"blank")) {
        memset(actual,0,sizeof(actual)); printf("%d",pixels_match(actual,pattern_rgba));
    } else if (!strcmp(argv[1],"mirrored")) {
        memcpy(actual[0],pattern_rgba[1],4); memcpy(actual[1],pattern_rgba[0],4);
        printf("%d",pixels_match(actual,pattern_rgba));
    } else if (!strcmp(argv[1],"alpha_corrupt")) {
        actual[1][3] = 251; printf("%d",pixels_match(actual,pattern_rgba));
    } else if (!strcmp(argv[1],"channel_corrupt")) {
        actual[3][2] = 251; printf("%d",pixels_match(actual,pattern_rgba));
    } else if (!strcmp(argv[1],"presentation_coordinates")) {
        int x, y;
        for (i = 0; i < SAMPLE_COUNT; ++i) {
            if (!presentation_coordinates(64,64,i,&x,&y)) return 9;
            printf("%d,%d;",x,y);
        }
        printf("%d%d%d%d%d%d",presentation_coordinates(64,64,4,&x,&y),
            presentation_coordinates(63,64,0,&x,&y),presentation_coordinates(64,65,0,&x,&y),
            presentation_coordinates(-64,64,0,&x,&y),presentation_coordinates(64,64,0,NULL,&y),
            presentation_coordinates(64,64,0,&x,NULL));
    } else if (!strcmp(argv[1],"presentation_pixels")) {
        for (i = 0; i < SAMPLE_COUNT; ++i) memcpy(rgb[i],presentation_alternate_rgba[i],3);
        printf("%d",presentation_pixels_match(rgb,presentation_alternate_rgba));
        printf("%d",presentation_pixels_match(r.presented_pixels_first,presentation_alternate_rgba));
        memset(rgb,0,sizeof(rgb)); printf("%d",presentation_pixels_match(rgb,presentation_alternate_rgba));
        for (i = 0; i < SAMPLE_COUNT; ++i) {
            rgb[i][0] = presentation_alternate_rgba[i][2]; rgb[i][1] = presentation_alternate_rgba[i][1];
            rgb[i][2] = presentation_alternate_rgba[i][0];
        }
        printf("%d",presentation_pixels_match(rgb,presentation_alternate_rgba));
        for (i = 0; i < SAMPLE_COUNT; ++i) memcpy(rgb[i],presentation_alternate_rgba[i ^ 1],3);
        printf("%d",presentation_pixels_match(rgb,presentation_alternate_rgba));
        for (i = 0; i < SAMPLE_COUNT; ++i) memcpy(rgb[i],presentation_alternate_rgba[i ^ 2],3);
        printf("%d",presentation_pixels_match(rgb,presentation_alternate_rgba));
        for (i = 0; i < SAMPLE_COUNT; ++i) memcpy(rgb[i],presentation_alternate_rgba[i],3);
        rgb[0][0] += 3; rgb[1][1] -= 3;
        printf("%d",presentation_pixels_match(rgb,presentation_alternate_rgba));
        rgb[0][0] += 1; printf("%d",presentation_pixels_match(rgb,presentation_alternate_rgba));
    } else if (!strcmp(argv[1],"presentation_poll_transition")) {
        unsigned int attempts = 0, elapsed = 0;
        int verdict;
        printf("%d",presentation_poll_step(10,10,&attempts,&elapsed,1,
            r.presented_pixels_first,presentation_alternate_rgba));
        printf("%d",presentation_poll_step(10,30,&attempts,&elapsed,1,
            r.presented_pixels_first,presentation_alternate_rgba));
        verdict = presentation_poll_step(10,50,&attempts,&elapsed,1,
            r.presented_pixels_second,presentation_alternate_rgba);
        printf("%d:%u:%u",verdict,attempts,elapsed);
        if (attempts != 3 || elapsed != 40) return 10;
    } else if (!strcmp(argv[1],"presentation_poll_bounds")) {
        unsigned int attempts = 0, elapsed = 0;
        int verdict = 0;
        printf("%d,",presentation_poll_step(0,0,&attempts,&elapsed,0,r.presented_pixels_first,pattern_rgba));
        printf("%d,",presentation_poll_step(0,2000,&attempts,&elapsed,0,r.presented_pixels_first,pattern_rgba));
        attempts = 0;
        printf("%d,",presentation_poll_step(0,2001,&attempts,&elapsed,1,r.presented_pixels_first,pattern_rgba));
        attempts = 100;
        printf("%d,",presentation_poll_step(0,0,&attempts,&elapsed,1,r.presented_pixels_first,pattern_rgba));
        attempts = 0;
        printf("%d,",presentation_poll_step(0xfffffff0u,0,&attempts,&elapsed,1,r.presented_pixels_first,pattern_rgba));
        if (elapsed != 16) return 11;
        attempts = 0;
        printf("%d,",presentation_poll_step(0,2000,&attempts,&elapsed,1,r.presented_pixels_first,pattern_rgba));
        attempts = 0;
        for (i = 0; i < 100; ++i) {
            verdict = presentation_poll_step(0,0,&attempts,&elapsed,0,r.presented_pixels_first,pattern_rgba);
            if ((i < 99 && verdict != 0) || (i == 99 && verdict != -1)) return 12;
        }
        printf("%d:%u",verdict,attempts);
    } else if (!strcmp(argv[1],"identity")) {
        const char *identities[] = {
            "zink Vulkan 1.3 (FD740)", "ZINK (Adreno 740)",
            "zink Vulkan (LLVMPIPE)", "zink Vulkan (lavapipe)",
            "zink Software", "zink SwiftShader", "zink softpipe", "zink swrast",
            "zink GDI Generic", "Adreno 740", "", NULL
        };
        for (i = 0; i < sizeof(identities)/sizeof(identities[0]); ++i)
            printf("%d",nonsoftware_zink(identities[i]));
    } else if (!strcmp(argv[1],"extensions")) {
        printf("%d%d%d%d%d%d%d%d", extension_present("GL_ARB_vertex_program GL_EXT_bgra","GL_ARB_vertex_program"),
            extension_present("GL_ARB_vertex_program_extra","GL_ARB_vertex_program"),
            extension_present("XGL_ARB_vertex_program","GL_ARB_vertex_program"),
            extension_present(" GL_ARB_vertex_program  GL_EXT_bgra ","GL_EXT_bgra"),
            extension_present(NULL,"GL_EXT_bgra"), extension_present("", "GL_EXT_bgra"),
            extension_present("GL_EXT_bgra", ""), extension_present("GL_EXT_bgra", "GL EXT_bgra"));
    } else if (!strcmp(argv[1],"bounded_extension")) {
        char list[EXTENSION_LIMIT+32];
        memset(list,'x',sizeof(list)); list[EXTENSION_LIMIT] = ' ';
        memcpy(list+EXTENSION_LIMIT+1,"GL_EXT_bgra",12);
        printf("%d",extension_present(list,"GL_EXT_bgra"));
    } else if (!strcmp(argv[1],"json")) json_string("driver\"name\\tail\n\t\001\377");
    else if (!strcmp(argv[1],"bounded_string")) {
        memset(string,'x',sizeof(string)); string[1024] = 0;
        copy_string(copied,string); json_string(copied);
    } else if (!strcmp(argv[1],"null_string")) { copy_string(copied,NULL); json_string(copied); }
    else if (!strcmp(argv[1],"bgra")) {
        static const unsigned char color[4] = {173,93,41,255};
        fill_bgra(bgra,color); solid_expected(expected,color);
        for (i = 0; i < 60; ++i) printf("%s%u",i ? "," : "",bgra[i]);
        printf(";%d",pixels_match(expected,expected));
    } else if (!strcmp(argv[1],"blocks")) {
        for (i = 0; i < 3; ++i) {
            unsigned int j, block_size = i == 0 ? 8 : 16;
            fill_compressed(data,i,4);
            for (j = 0; j < 4; ++j) if (memcmp(data+j*block_size,dxt_blocks[i],block_size)) return 5;
            /* Independently decode each source block's index-zero endpoint. */
            for (j = 0; j < 2; ++j) {
                const unsigned char *block = j ? dxt_alternate_blocks[i] : dxt_blocks[i];
                const unsigned char *color = j ? dxt_alternate_expected[i] : dxt_expected[i];
                unsigned int offset = i == 0 ? 0 : 8;
                unsigned int endpoint = block[offset] | ((unsigned int)block[offset+1] << 8);
                unsigned char rgba[4];
                rgba[0] = (unsigned char)(((endpoint >> 11) & 31) * 255 / 31);
                rgba[1] = (unsigned char)(((endpoint >> 5) & 63) * 255 / 63);
                rgba[2] = (unsigned char)((endpoint & 31) * 255 / 31);
                rgba[3] = i == 0 ? 255 : i == 1 ? (unsigned char)((block[0] & 15) * 17) : block[0];
                if (memcmp(rgba,color,4)) return 8;
            }
            printf("%u:%u:%u;",block_size,dxt_expected[i][i],dxt_alternate_expected[i][3]);
        }
        fill_compressed(data,3,4);
        for (i = 0; i < 64; ++i) if (data[i]) return 6;
        fill_compressed(data,0,5);
        for (i = 0; i < 64; ++i) if (data[i]) return 7;
    } else if (!strcmp(argv[1],"positive")) {
        printf("%d\n",result_passes(&r)); print_result(&r,"","Mesa","zink FD740","4.6");
    } else if (!strcmp(argv[1],"booleans_fail_closed")) {
        REJECT_FIELDS
        printf("%d",result_passes(NULL));
    } else if (!strcmp(argv[1],"boundaries")) {
        r.pointer_bits = 64; printf("%d",result_passes(&r)); positive(&r);
        r.fp_max_local_parameters = 31; printf("%d",result_passes(&r)); positive(&r);
        r.fp_max_temporaries = 16; printf("%d",result_passes(&r)); positive(&r);
        r.fp_max_native_temporaries = 16; printf("%d",result_passes(&r)); positive(&r);
        r.gl_error = 0x0502; printf("%d",result_passes(&r)); positive(&r);
        r.fp_max_local_parameters = 96; r.fp_max_temporaries = 256; printf("%d",result_passes(&r));
    } else if (!strcmp(argv[1],"failure_json")) {
        r.presented_pattern_second = r.presented_readback = 0;
        print_result(&r,"post_swap_presented_pattern_second","Mesa","zink","4.6");
    } else if (!strcmp(argv[1],"front_diagnostic")) {
        r.frontbuffer_readback = 0; r.frontbuffer_gl_error = 0x0502;
        printf("%d\n",result_passes(&r)); print_result(&r,"","Mesa","zink","4.6");
    } else if (!strcmp(argv[1],"presentation_boundaries")) {
        r.presentation_attempts_first = 0; printf("%d",result_passes(&r)); positive(&r);
        r.presentation_attempts_first = 101; printf("%d",result_passes(&r)); positive(&r);
        r.presentation_attempts_second = 0; printf("%d",result_passes(&r)); positive(&r);
        r.presentation_attempts_second = 101; printf("%d",result_passes(&r)); positive(&r);
        r.presentation_elapsed_ms_first = 2001; printf("%d",result_passes(&r)); positive(&r);
        r.presentation_elapsed_ms_second = 2001; printf("%d",result_passes(&r)); positive(&r);
        r.presentation_client_width = 63; printf("%d",result_passes(&r)); positive(&r);
        r.presentation_client_height = 65; printf("%d",result_passes(&r)); positive(&r);
        r.presented_pixels_first[0][0] = 251; printf("%d",result_passes(&r)); positive(&r);
        memcpy(r.presented_pixels_second,r.presented_pixels_first,sizeof(r.presented_pixels_second));
        printf("%d",result_passes(&r)); positive(&r);
        r.presentation_attempts_first = r.presentation_attempts_second = 100;
        r.presentation_elapsed_ms_first = r.presentation_elapsed_ms_second = 2000;
        printf("%d",result_passes(&r));
    } else if (!strcmp(argv[1],"inconsistent_failure")) {
        print_result(&r,"driver_error","Mesa","zink","4.6");
    } else return 3;
    return 0;
}
'''


class CohGpuProbeNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-gpu-probe-')
        cls.directory = Path(cls.temporary.name)
        fixture = cls.directory / 'gpu-probe-checks.c'
        positive = '\n'.join(f'r->{field} = 1;' for field in BOOL_FIELDS)
        rejected = '\n'.join(f'positive(&r); r.{field} = 0; printf("%d",result_passes(&r));'
                             for field in BOOL_FIELDS)
        fixture.write_text(FIXTURE.replace('SOURCE_PATH', json.dumps(SOURCE.as_posix()))
                           .replace('POSITIVE_FIELDS', positive).replace('REJECT_FIELDS', rejected))
        cls.executable = cls.directory / ('gpu-probe-checks.exe' if sys.platform == 'win32' else 'gpu-probe-checks')
        if sys.platform == 'win32':
            command = ['cl', '/nologo', '/std:c11', '/O2', '/W4', '/WX', '/TC', str(fixture),
                       '/Fe' + str(cls.executable), '/Fo' + str(cls.directory / 'gpu-probe-checks.obj')]
        else:
            command = ['cc', '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror',
                       str(fixture), '-o', str(cls.executable)]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True, cwd=cls.directory)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f'Native helper compile failed:\n{exc.stdout}\n{exc.stderr}') from exc
        raw = cls.executable.read_bytes()
        cls.native_receipt = {
            'platform': 'windows' if sys.platform == 'win32' else sys.platform,
            'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            'tests_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'source_bytes': SOURCE.stat().st_size,
            'tests_source_bytes': Path(__file__).stat().st_size,
            'fixture_bytes': fixture.stat().st_size,
            'fixture_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest(),
            'executable_bytes': len(raw), 'executable_sha256': hashlib.sha256(raw).hexdigest(),
            'pointer_bits': int(subprocess.check_output([str(cls.executable), 'pointer_bits'], text=True, timeout=10)),
        }
        cls.executed_checks = {'pointer_bits': {'stdout': str(cls.native_receipt['pointer_bits']),
                                               'exit_code': 0, 'timeout_seconds': 10}}
        if WINDOWS_EVIDENCE_DIR is not None:
            if sys.platform != 'win32' or raw[:2] != b'MZ':
                raise RuntimeError('Windows qualification requires an actual Windows PE helper')
            pe_offset = struct.unpack_from('<I', raw, 0x3c)[0]
            if raw[pe_offset:pe_offset+4] != b'PE\0\0':
                raise RuntimeError('Invalid Windows helper PE signature')
            cls.native_receipt['pe_machine'] = struct.unpack_from('<H', raw, pe_offset+4)[0]
            if cls.native_receipt['pe_machine'] != 332 or cls.native_receipt['pointer_bits'] != 32:
                raise RuntimeError('Windows qualification requires genuine Win32 compilation and execution')
            if FIXTURE_MARKER.encode() not in raw or PRODUCTION_MARKER.encode() in raw:
                raise RuntimeError('Host helper fixture and production probe must be distinct binaries')
            cls.native_receipt['architecture'] = 'Win32'
            cls.native_receipt['build_marker'] = FIXTURE_MARKER
            WINDOWS_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fixture, WINDOWS_EVIDENCE_DIR / 'coh-gpu-probe-helper-checks.c')
            shutil.copy2(cls.executable, WINDOWS_EVIDENCE_DIR / 'coh-gpu-probe-helper-checks.exe')

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def output(self, mode):
        process = subprocess.run([str(self.executable), mode], text=True, timeout=10,
                                 capture_output=True, check=True)
        type(self).executed_checks[mode] = {'stdout': process.stdout, 'exit_code': process.returncode,
                                          'timeout_seconds': 10}
        return process.stdout

    @staticmethod
    def record(output):
        prefix, _, payload = output.partition(' ')
        if prefix != 'COH_GPU_PROBE_V2':
            raise AssertionError(output)
        return json.loads(payload)

    def test_actual_readback_accepts_only_expected_color_and_tolerance(self):
        self.assertEqual(self.output('correct'), '1')
        self.assertEqual(self.output('rounding'), '1')

    def test_actual_readback_rejects_blank_reordered_rgb_and_alpha_corruption(self):
        for mode in ('blank', 'mirrored', 'alpha_corrupt', 'channel_corrupt'):
            with self.subTest(mode=mode):
                self.assertEqual(self.output(mode), '0')

    def test_presented_coordinates_convert_real_gl_pixels_and_reject_wrong_client_bounds(self):
        self.assertEqual(self.output('presentation_coordinates'), '16,47;48,47;16,15;48,15;000000')

    def test_presented_screen_rgb_rejects_stale_blank_reflections_and_channel_swaps(self):
        self.assertEqual(self.output('presentation_pixels'), '10000010')

    def test_presented_polling_waits_for_the_second_pattern_and_bounds_unowned_or_late_pixels(self):
        self.assertEqual(self.output('presentation_poll_transition'), '001:3:40')
        self.assertEqual(self.output('presentation_poll_bounds'), '0,-1,-1,-1,1,1,-1:100')

    def test_presented_conjunction_rechecks_pixels_dimensions_attempts_and_deadlines(self):
        self.assertEqual(self.output('presentation_boundaries'), '00000000001')

    def test_front_gl_readback_is_separate_diagnostic_and_never_substitutes_screen_proof(self):
        accepted, output = self.output('front_diagnostic').split('\n', 1)
        self.assertEqual(accepted, '1')
        record = self.record(output)
        self.assertIs(record['passed'], True)
        self.assertIs(record['frontbuffer_readback'], False)
        self.assertEqual(record['frontbuffer_gl_error'], 0x0502)
        self.assertIs(record['presented_readback'], True)
        self.assertEqual(record['presented_pixels_first'], [[255,0,0],[0,255,0],[0,0,255],[255,255,255]])
        self.assertEqual(record['presented_pixels_second'], [[41,93,173],[211,57,99],[77,201,33],[163,29,227]])

    def test_renderer_identity_is_only_a_prerequisite_and_rejects_software(self):
        self.assertEqual(self.output('identity'), '11' + '0' * 10)
        self.assertEqual(self.output('booleans_fail_closed'), '0' * (len(BOOL_FIELDS) + 1))

    def test_extension_matching_requires_whole_tokens_and_bounded_list(self):
        self.assertEqual(self.output('extensions'), '10010000')
        self.assertEqual(self.output('bounded_extension'), '0')

    def test_driver_json_string_encoding_and_copy_are_bounded(self):
        self.assertEqual(json.loads(self.output('json')), 'driver"name\\tail\n\t\x01\xff')
        self.assertEqual(json.loads(self.output('bounded_string')), 'x' * 512)
        self.assertEqual(json.loads(self.output('null_string')), '')

    def test_bgra_and_expected_pixel_helpers_preserve_exact_channel_order(self):
        pixels, accepted = self.output('bgra').split(';')
        self.assertEqual(list(map(int, pixels.split(','))), [41,93,173,255] * 15)
        self.assertEqual(accepted, '1')

    def test_compressed_block_buffers_and_invalid_bounds_are_executed(self):
        self.assertEqual(self.output('blocks'), '8:255:255;16:255:85;16:255:120;')

    def test_limits_pointer_width_and_any_gl_error_fail_closed(self):
        self.assertEqual(self.output('boundaries'), '000001')

    def test_positive_record_contains_real_json_booleans_and_scope_limits(self):
        accepted, output = self.output('positive').split('\n', 1)
        self.assertEqual(accepted, '1')
        record = self.record(output)
        self.assertIs(record['passed'], True)
        self.assertEqual(record['status'], 'passed')
        self.assertEqual(record['failure'], '')
        self.assertEqual(record['pointer_bits'], 32)
        self.assertEqual(record['fp_max_native_temporaries'], 17)
        self.assertEqual(record['scope'], 'bounded_wgl_gpu_prerequisites')
        self.assertEqual(record['build_marker'], FIXTURE_MARKER)
        self.assertEqual(record['format'], 2)
        self.assertEqual(record['presentation_method'], 'win32_screen_getpixel_two_patterns')
        for field in BOOL_FIELDS:
            self.assertIs(record[field], True, field)
        for field in ('game_rendering_validated', 'cg_shaders_validated',
                      'android_surface_validated', 'hardware_acceleration_validated'):
            self.assertIs(record[field], False, field)

    def test_missing_actual_presented_proof_and_failure_stage_prevent_success_json(self):
        for mode in ('failure_json', 'inconsistent_failure'):
            with self.subTest(mode=mode):
                record = self.record(self.output(mode))
                self.assertIs(record['passed'], False)
                self.assertEqual(record['status'], 'failed')
                self.assertTrue(record['failure'])

    def test_production_source_executes_arb_programs_and_actual_indexed_readback(self):
        source = SOURCE.read_text()
        production = source.split('#ifndef COH_GPU_PROBE_TEST', 1)[1]
        for call in ('wglCreateContext(', 'wglMakeCurrent(', 'glGetString(GL_EXTENSIONS)',
                     'glDrawElements(GL_TRIANGLES', 'glReadPixels(', 'SwapBuffers(dc)',
                     'glReadBuffer(GL_FRONT)', 'a->program_string(',
                     'GetDC(NULL)', 'GetPixel(screen_dc,', 'ClientToScreen(window,&point)',
                     'WindowFromPoint(point) != window', 'GetClientRect(window,&client)',
                     'SetWindowPos(window,HWND_TOPMOST,', 'MsgWaitForMultipleObjects(',
                     'a->program_local_parameter(C_FRAGMENT_PROGRAM, 31,',
                     'a->get_program(C_FRAGMENT_PROGRAM, C_MAX_PROGRAM_TEMPORARIES',
                     'a->get_program(C_FRAGMENT_PROGRAM, C_MAX_PROGRAM_NATIVE_TEMPORARIES',
                     'a->get_program(C_FRAGMENT_PROGRAM, C_MAX_PROGRAM_LOCAL_PARAMETERS',
                     'a->buffer_data(C_ELEMENT_ARRAY_BUFFER, sizeof(indices), indices',
                     'a->client_active_texture(C_TEXTURE1)'):
            self.assertIn(call, production)
        self.assertIn('TEMP t0,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,t13,t14,t15,t16;', production)
        self.assertIn('PARAM tone = program.local[31];', production)
        self.assertRegex(production, r'error_position\s*==\s*-1')
        self.assertRegex(production, r'if\s*\(argc\s*!=\s*1\)\s*goto done;')
        self.assertRegex(production, r'return completed && !\*failure && result_passes\(&r\) \? 0 : 10;')
        for override in ('MESA_GL_VERSION_OVERRIDE', 'MESA_EXTENSION_OVERRIDE', 'MESA_GLSL_VERSION_OVERRIDE'):
            self.assertNotIn(override, source)

    def test_production_texture_fbo_and_all_resource_cleanup_calls_are_present(self):
        source = SOURCE.read_text()
        for statement in ('C_RGBA8, 600, 450', 'C_DEPTH_COMPONENT24, 600, 450',
                          'depth_size < 24', 'C_FRAMEBUFFER_COMPLETE',
                          'upload_vertices(a,o,0.5f)', 'glEnable(GL_DEPTH_TEST)',
                          'a->compressed_image(GL_TEXTURE_2D, 0, formats[kind], 8, 8',
                          'a->compressed_image(GL_TEXTURE_2D, 1, formats[kind], 4, 4',
                          'memcpy(mip,dxt_alternate_blocks[kind],(size_t)block_size)',
                          'solid_expected(expected,dxt_alternate_expected[kind])',
                          'a->compressed_subimage(GL_TEXTURE_2D, 0, 0, 0, 4, 4',
                          'texture_properties(r, 1, formats[kind], 4)',
                          'C_TEXTURE_BASE_LEVEL, 1', 'glTexSubImage2D(GL_TEXTURE_2D,0,0,0,3,5,C_BGRA',
                          'a->delete_framebuffers(', 'a->delete_renderbuffers(',
                          'a->delete_buffers(', 'a->delete_programs(', 'glDeleteTextures(',
                          'wglDeleteContext(context)', 'ReleaseDC(window,dc)',
                          'ReleaseDC(NULL,screen_dc)',
                          'DestroyWindow(window)', 'UnregisterClassA('):
            self.assertIn(statement, source)
        self.assertIn('if (!no_gl_error(r)) success = 0;', source)
        self.assertIn('value == 1 || value == 2 || value == 3 || value == (uintptr_t)-1', source)

    def test_windows_receipt_validator_rejects_missing_guards_and_false_authority(self):
        import copy
        receipt = {
            'format': 1, 'role': 'coh_gpu_probe_actual_source_helpers', 'status': 'passed',
            **type(self).native_receipt, 'platform': 'windows', 'architecture': 'Win32',
            'pointer_bits': 32, 'pe_machine': 332, 'build_marker': FIXTURE_MARKER,
            'commit': '1' * 40,
            'github_run_url': 'https://github.com/Russianranger/coh-android/actions/runs/123',
            'tests': len(test_inventory()), 'failures': 0, 'errors': 0, 'skipped': 0,
            'test_inventory': test_inventory(),
            'production_gl_exercised': False, 'hardware_acceleration_validated': False,
            'cg_shaders_validated': False, 'game_rendering_validated': False,
            'android_surface_validated': False,
            'production_probe': {'bytes': 4096, 'sha256': '2' * 64, 'pe_machine': 332,
                                 'build_marker': PRODUCTION_MARKER},
            'executed_checks': {},
        }
        for mode in expected_guard_modes():
            output = '32' if mode == 'pointer_bits' else self.output(mode)
            receipt['executed_checks'][mode] = {'stdout': output, 'exit_code': 0, 'timeout_seconds': 10}
        validate_windows_checks(receipt)
        for field, value in (('platform', 'linux'), ('pointer_bits', True), ('architecture', 'x64'),
                             ('pe_machine', 34404), ('source_sha256', '0' * 64),
                             ('tests_source_sha256', '0' * 64), ('tests', True), ('skipped', 1),
                             ('production_gl_exercised', True), ('cg_shaders_validated', True),
                             ('game_rendering_validated', True), ('hardware_acceleration_validated', True),
                             ('build_marker', PRODUCTION_MARKER), ('commit', 'main'),
                             ('github_run_url', 'https://example.com/actions/runs/123')):
            with self.subTest(field=field):
                candidate = copy.deepcopy(receipt)
                candidate[field] = value
                with self.assertRaises(ValueError):
                    validate_windows_checks(candidate)
        for change in ('missing_guard', 'changed_guard', 'helper_substitution', 'missing_native_limit'):
            candidate = copy.deepcopy(receipt)
            if change == 'missing_guard':
                del candidate['executed_checks']['blank']
            elif change == 'changed_guard':
                candidate['executed_checks']['blank']['stdout'] = '1'
            elif change == 'helper_substitution':
                candidate['production_probe']['build_marker'] = FIXTURE_MARKER
            else:
                stdout = candidate['executed_checks']['positive']['stdout']
                candidate['executed_checks']['positive']['stdout'] = stdout.replace(
                    '\"fp_max_native_temporaries\":17', '\"fp_max_native_temporaries\":16')
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_windows_checks(candidate)


def test_inventory():
    return sorted(name for name, value in CohGpuProbeNativeTests.__dict__.items()
                  if name.startswith('test_') and callable(value))


def expected_guard_modes():
    return ('pointer_bits', 'correct', 'rounding', 'blank', 'mirrored', 'alpha_corrupt',
            'channel_corrupt', 'identity', 'booleans_fail_closed', 'extensions',
            'bounded_extension', 'json', 'bounded_string', 'null_string', 'bgra', 'blocks',
            'boundaries', 'positive', 'failure_json', 'inconsistent_failure',
            'presentation_coordinates', 'presentation_pixels', 'presentation_poll_transition',
            'presentation_poll_bounds', 'presentation_boundaries', 'front_diagnostic')


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate proof JSON key: {key}')
        result[key] = value
    return result


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _integer(value, lower, upper):
    return type(value) is int and lower <= value <= upper


def _sha(value):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _guard_record(stdout, failure='', front=True, front_error=0, presented=True, renderer='zink'):
    prefix, _, payload = stdout.partition(' ')
    _require(prefix == 'COH_GPU_PROBE_V2', 'Unexpected helper record prefix')
    actual = json.loads(payload, object_pairs_hook=_unique_object)
    expected = {
        'format': 2, 'build_marker': FIXTURE_MARKER, 'status': 'failed' if failure else 'passed',
        'passed': not bool(failure), 'failure': failure, 'scope': 'bounded_wgl_gpu_prerequisites',
        'pointer_bits': 32, 'win32_error': 0, 'gl_error': 0,
        'gl_vendor': 'Mesa', 'gl_renderer': renderer, 'gl_version': '4.6',
        **{field: True for field in BOOL_FIELDS}, 'frontbuffer_readback': front,
        'frontbuffer_gl_error': front_error,
        'presented_pattern_second': presented, 'presented_readback': presented,
        'presentation_method': 'win32_screen_getpixel_two_patterns',
        'presentation_sample_count': 4, 'presentation_pattern_count': 2,
        'presentation_client_width': 64, 'presentation_client_height': 64,
        'presentation_attempts_first': 1, 'presentation_attempts_second': 1,
        'presentation_elapsed_ms_first': 0, 'presentation_elapsed_ms_second': 0,
        'presented_pixels_first': [[255,0,0],[0,255,0],[0,0,255],[255,255,255]],
        'presented_pixels_second': [[41,93,173],[211,57,99],[77,201,33],[163,29,227]],
        'fp_max_local_parameters': 32, 'fp_max_temporaries': 17, 'fp_max_native_temporaries': 17,
        'game_rendering_validated': False, 'cg_shaders_validated': False,
        'android_surface_validated': False, 'hardware_acceleration_validated': False,
    }
    _require(type(actual) is dict and set(actual) == set(expected), 'Incomplete helper JSON proof')
    for key, value in expected.items():
        _require(type(actual[key]) is type(value) and actual[key] == value,
                 f'Unexpected actual-source helper proof field {key}')


def validate_windows_checks(checks):
    """Validate Win32 helper content; producer separately binds its run and PE.

    Receipt provenance comes from the current hosted job. This validates source
    closure and actual guard outputs; it grants no GPU/Game authority. The
    producer compares commit/run and production PE bytes/SHA to the archive,
    and validates PE imports and the archived helper source/executable pins.
    """
    _require(type(checks) is dict, 'Windows proof must be an object')
    for key, value in (('format', 1), ('role', 'coh_gpu_probe_actual_source_helpers'),
                       ('status', 'passed'), ('platform', 'windows'), ('architecture', 'Win32'),
                       ('pointer_bits', 32), ('pe_machine', 332), ('build_marker', FIXTURE_MARKER),
                       ('failures', 0), ('errors', 0), ('skipped', 0)):
        _require(type(checks.get(key)) is type(value) and checks.get(key) == value,
                 f'Unexpected Windows proof field {key}')
    for key in ('production_gl_exercised', 'hardware_acceleration_validated',
                'cg_shaders_validated', 'game_rendering_validated', 'android_surface_validated'):
        _require(checks.get(key) is False, f'Windows helper proof cannot claim {key}')
    for stem, path in (('source', SOURCE), ('tests_source', Path(__file__))):
        raw = path.read_bytes()
        _require(type(checks.get(stem + '_bytes')) is int and checks[stem + '_bytes'] == len(raw),
                 f'Current {stem} byte count mismatch')
        _require(checks.get(stem + '_sha256') == hashlib.sha256(raw).hexdigest(),
                 f'Current {stem} SHA-256 mismatch')
    for stem in ('fixture', 'executable'):
        _require(_sha(checks.get(stem + '_sha256')) and
                 _integer(checks.get(stem + '_bytes'), 1, 16 * 1024 * 1024),
                 f'Missing {stem} binary/source pins')
    _require(type(checks.get('commit')) is str and
             re.fullmatch(r'[0-9a-f]{40}', checks['commit']) is not None, 'Missing exact source commit')
    _require(type(checks.get('github_run_url')) is str and re.fullmatch(
        r'https://github\.com/Russianranger/coh-android/actions/runs/[1-9][0-9]{0,19}',
        checks['github_run_url']) is not None, 'Missing current hosted run provenance')
    _require(checks.get('test_inventory') == test_inventory() and
             _integer(checks.get('tests'), len(test_inventory()), len(test_inventory())),
             'Incomplete exact test inventory')
    production = checks.get('production_probe')
    _require(type(production) is dict and set(production) == {'bytes','sha256','pe_machine','build_marker'},
             'Missing production PE identity')
    _require(_integer(production.get('bytes'), 1024, 16 * 1024 * 1024) and
             _sha(production.get('sha256')) and type(production.get('pe_machine')) is int and
             production['pe_machine'] == 332 and production.get('build_marker') == PRODUCTION_MARKER,
             'Production PE cannot be a host helper substitute')
    guards = checks.get('executed_checks')
    _require(type(guards) is dict and set(guards) == set(expected_guard_modes()), 'Missing executed guard cases')
    for mode, record in guards.items():
        _require(type(record) is dict and set(record) == {'stdout','exit_code','timeout_seconds'} and
                 type(record.get('stdout')) is str and len(record['stdout']) <= 16384 and
                 type(record.get('exit_code')) is int and record['exit_code'] == 0 and
                 type(record.get('timeout_seconds')) is int and record['timeout_seconds'] == 10,
                 f'Invalid executed guard receipt {mode}')
    expected_text = {
        'pointer_bits': '32', 'correct': '1', 'rounding': '1', 'blank': '0', 'mirrored': '0',
        'alpha_corrupt': '0', 'channel_corrupt': '0', 'identity': '11' + '0' * 10,
        'booleans_fail_closed': '0' * (len(BOOL_FIELDS) + 1), 'extensions': '10010000',
        'bounded_extension': '0', 'bgra': ','.join(map(str, [41,93,173,255] * 15)) + ';1',
        'blocks': '8:255:255;16:255:85;16:255:120;', 'boundaries': '000001',
        'presentation_coordinates': '16,47;48,47;16,15;48,15;000000',
        'presentation_pixels': '10000010', 'presentation_poll_transition': '001:3:40',
        'presentation_poll_bounds': '0,-1,-1,-1,1,1,-1:100',
        'presentation_boundaries': '00000000001',
    }
    for mode, expected in expected_text.items():
        _require(guards[mode]['stdout'] == expected, f'Executed guard mismatch {mode}')
    for mode, expected in (('json', 'driver"name\\tail\n\t\x01\xff'),
                           ('bounded_string', 'x' * 512), ('null_string', '')):
        _require(json.loads(guards[mode]['stdout']) == expected, f'Actual bounded JSON guard mismatch {mode}')
    accepted, _, positive = guards['positive']['stdout'].partition('\n')
    _require(accepted == '1', 'Positive conjunction did not execute')
    _guard_record(positive, renderer='zink FD740')
    _guard_record(guards['failure_json']['stdout'], 'post_swap_presented_pattern_second', presented=False)
    _guard_record(guards['inconsistent_failure']['stdout'], 'driver_error')
    accepted, _, diagnostic = guards['front_diagnostic']['stdout'].partition('\n')
    _require(accepted == '1', 'Front GL diagnostic must not substitute or invalidate actual presented proof')
    _guard_record(diagnostic, front=False, front_error=0x0502)
    return checks


def _production_pe(path):
    raw = path.read_bytes()
    _require(1024 <= len(raw) <= 16 * 1024 * 1024 and raw[:2] == b'MZ', 'Missing bounded production PE')
    offset = struct.unpack_from('<I', raw, 0x3c)[0]
    _require(64 <= offset <= len(raw) - 26 and raw[offset:offset+4] == b'PE\0\0', 'Bad production PE header')
    machine = struct.unpack_from('<H', raw, offset+4)[0]
    magic = struct.unpack_from('<H', raw, offset+24)[0]
    _require(machine == 332 and magic == 0x10b, 'Production probe must be PE32 Win32')
    _require(PRODUCTION_MARKER.encode() in raw and FIXTURE_MARKER.encode() not in raw,
             'Production PE cannot be the host helper fixture')
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'pe_machine': machine, 'build_marker': PRODUCTION_MARKER}


def windows_qualify():
    global WINDOWS_EVIDENCE_DIR
    parser = argparse.ArgumentParser(description='Genuine Win32 actual-source helper checks; no GL/GPU claim')
    parser.add_argument('--windows-qualify', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--production-probe', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--github-run-url', required=True)
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('Windows qualification must execute on an actual Windows host')
    WINDOWS_EVIDENCE_DIR = args.output.resolve().parent
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(CohGpuProbeNativeTests))
    accepted = result.wasSuccessful() and result.testsRun == len(test_inventory()) and not result.skipped
    receipt = {
        'format': 1, 'role': 'coh_gpu_probe_actual_source_helpers',
        'status': 'passed' if accepted else 'failed',
        **getattr(CohGpuProbeNativeTests, 'native_receipt', {}),
        'tests': result.testsRun, 'failures': len(result.failures),
        'errors': len(result.errors), 'skipped': len(result.skipped),
        'test_inventory': test_inventory(), 'commit': args.commit,
        'github_run_url': args.github_run_url,
        'production_probe': _production_pe(args.production_probe),
        'executed_checks': getattr(CohGpuProbeNativeTests, 'executed_checks', {}),
        'production_gl_exercised': False, 'hardware_acceleration_validated': False,
        'cg_shaders_validated': False, 'game_rendering_validated': False,
        'android_surface_validated': False,
    }
    if accepted:
        validate_windows_checks(receipt)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    return 0 if accepted else 1


if __name__ == '__main__':
    if '--windows-qualify' in sys.argv:
        raise SystemExit(windows_qualify())
    unittest.main()
