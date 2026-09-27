"""Execute the native probe's readback rejection and bounded output contracts.

The hosted runtime gate must separately compile/run the complete PE32 program.
These host tests cannot establish that WGL or DirectInput works.
"""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'android/native/client-probe.c'
FIXTURE = r'''
#define COH_CLIENT_PROBE_TEST
#include SOURCE_PATH
int main(int argc, char **argv) {
    unsigned char samples[4][3] = {{255,0,0}, {0,255,0}, {0,0,255}, {255,255,255}};
    if (argc != 2) return 2;
    if (!strcmp(argv[1], "correct")) printf("%d", samples_match(samples));
    else if (!strcmp(argv[1], "blank")) {
        memset(samples, 0, sizeof(samples)); printf("%d", samples_match(samples));
    } else if (!strcmp(argv[1], "mirrored")) {
        unsigned char pixel[3];
        memcpy(pixel, samples[0], 3); memcpy(samples[0], samples[1], 3); memcpy(samples[1], pixel, 3);
        printf("%d", samples_match(samples));
    } else if (!strcmp(argv[1], "corrupt")) {
        samples[3][2] = 250; printf("%d", samples_match(samples));
    } else if (!strcmp(argv[1], "rounding")) {
        samples[3][2] = 252; samples[0][1] = 3; printf("%d", samples_match(samples));
    } else if (!strcmp(argv[1], "software")) {
        printf("%d%d%d%d%d%d", software_renderer("LLVMPIPE (LLVM 17.0)"),
            software_renderer("Software Rasterizer"), software_renderer("zink Vulkan 1.3(lavapipe)"),
            software_renderer("GDI Generic"), software_renderer("Adreno (TM) 740"), software_renderer(""));
    } else if (!strcmp(argv[1], "extensions")) {
        printf("%d%d%d%d", extension_present("GL_ARB_vertex_program GL_ARB_shader_objects", "GL_ARB_vertex_program"),
            extension_present("GL_ARB_vertex_program_extra", "GL_ARB_vertex_program"),
            extension_present("XGL_ARB_vertex_program", "GL_ARB_vertex_program"),
            extension_present("GL_ARB_vertex_program GL_ARB_shader_objects", "GL_ARB_shader_objects"));
    } else if (!strcmp(argv[1], "json")) {
        json_string("driver\"name\\tail\n\t\001\377");
    } else if (!strcmp(argv[1], "bounded")) {
        char text[1025]; memset(text, 'x', sizeof(text)); text[1024] = 0; json_string(text);
    } else return 3;
    return 0;
}
'''


class NativeClientProbeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-client-probe-')
        cls.directory = Path(cls.temporary.name)
        fixture = cls.directory / 'probe-checks.c'
        fixture.write_text(FIXTURE.replace('SOURCE_PATH', json.dumps(SOURCE.as_posix())))
        cls.executable = cls.directory / 'probe-checks'
        subprocess.run(['cc', '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror', str(fixture),
                        '-o', str(cls.executable)], check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def output(self, mode):
        return subprocess.check_output([str(self.executable), mode], text=True, timeout=10)

    def test_actual_samples_accept_expected_texture_and_bounded_rounding(self):
        self.assertEqual(self.output('correct'), '1')
        self.assertEqual(self.output('rounding'), '1')

    def test_actual_samples_reject_blank_mirrored_and_corrupt_rendering(self):
        for mode in ['blank', 'mirrored', 'corrupt']:
            with self.subTest(mode=mode):
                self.assertEqual(self.output(mode), '0')

    def test_software_renderers_are_detected_without_claiming_hardware(self):
        self.assertEqual(self.output('software'), '111100')

    def test_gl_extension_names_require_complete_tokens(self):
        self.assertEqual(self.output('extensions'), '1001')

    def test_driver_string_output_is_valid_bounded_json(self):
        self.assertEqual(json.loads(self.output('json')), 'driver"name\\tail\n\t\x01\xff')
        self.assertEqual(json.loads(self.output('bounded')), 'x' * 512)


if __name__ == '__main__':
    unittest.main()
