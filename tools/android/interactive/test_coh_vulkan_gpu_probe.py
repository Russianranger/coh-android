"""Compile the actual native source; exercise its finite queue on CPU Vulkan.

The host-only build can prove byte readback and guard behavior. Its marker and
native_gpu_executed=false prevent that evidence from qualifying Thor hardware.
No mocks, optional skips, or device performance claims are used here.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'android/native/coh-vulkan-gpu-probe.c'
FIELDS = {'format', 'pointer_bits', 'status', 'failure_stage', 'vendor_id',
    'device_id', 'device_type', 'api_version', 'driver_version', 'driver_id',
    'kgsl_chip_id', 'kgsl_verified', 'native_gpu_executed', 'fill_verified',
    'bytes_verified', 'expected_bytes', 'elapsed_ms'}
GUARD = r'''
#define main coh_production_entry
#include SOURCE_PATH
#undef main
int main(int argc, char **argv) {
    struct result r = {0};
    unsigned int i;
    if (argc != 2) return 2;
    if (!strcmp(argv[1], "chips")) {
        printf("%d%d%d%d%d%d%d", a740_chip(0x43050a01), a740_chip(0x43050b00),
            a740_chip(0x07040000), a740_chip(0x070400ff), a740_chip(0x43050c01),
            a740_chip(0x07050000), a740_chip(740));
    } else if (!strcmp(argv[1], "development_chips")) {
        for (i=0; i<256; ++i) if (!a740_chip(0x07040000+i)) return 3;
        printf("256");
    } else if (!strcmp(argv[1], "identity")) {
        r.vendor_id=0x5143; r.device_id=0x43050a01; r.kgsl_chip_id=r.device_id;
        r.driver_id=18; r.driver_version=VK_MAKE_VERSION(26,0,0);
        r.device_type=VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU;
        r.api_version=VK_API_VERSION_1_2; r.kgsl_verified=1;
        printf("%d",hardware_identity(&r));
        r.kgsl_verified=0; printf("%d",hardware_identity(&r)); r.kgsl_verified=1;
        r.kgsl_chip_id=0x43050b00; printf("%d",hardware_identity(&r)); r.kgsl_chip_id=r.device_id;
        r.driver_id=13; printf("%d",hardware_identity(&r)); r.driver_id=18;
        r.device_type=VK_PHYSICAL_DEVICE_TYPE_CPU; printf("%d",hardware_identity(&r));
        r.device_type=VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU;
        r.driver_version=VK_MAKE_VERSION(25,0,0); printf("%d",hardware_identity(&r));
        r.driver_version=VK_MAKE_VERSION(26,0,0);
        r.vendor_id=0x10005; printf("%d",hardware_identity(&r));
    } else if (!strcmp(argv[1], "environment")) printf("%d",candidate_environment());
    else return 4;
    return 0;
}
'''


def clean_environment(icd=None):
    value = {key: val for key, val in os.environ.items()
        if not key.startswith(('TU_', 'MESA_', 'VK_', 'LIBGL_', 'GALLIUM_', 'ZINK_'))}
    if icd:
        value['VK_DRIVER_FILES'] = value['VK_ICD_FILENAMES'] = str(icd)
    return value


class NativeVulkanProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-vulkan-tests-')
        cls.directory = Path(cls.temporary.name)
        candidates = sorted(Path('/usr/share/vulkan/icd.d').glob('lvp_icd*.json'))
        supplied = os.environ.get('COH_VULKAN_TEST_ICD')
        cls.icd = Path(supplied) if supplied else (candidates[0] if candidates else None)
        if not cls.icd or not cls.icd.is_file():
            raise RuntimeError('Actual host CPU Vulkan ICD required (mesa-vulkan-drivers)')
        compiler = shutil.which('cc')
        if not compiler:
            raise RuntimeError('Actual C compiler required')
        cls.production, cls.fixture, cls.guard = (cls.directory / x for x in ('production', 'fixture', 'guard'))
        flags = [compiler, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror']
        library = '-lvulkan' if Path('/usr/lib/x86_64-linux-gnu/libvulkan.so').exists() or Path('/usr/lib/aarch64-linux-gnu/libvulkan.so').exists() else '-l:libvulkan.so.1'
        subprocess.run([*flags, str(SOURCE), '-o', str(cls.production), library], check=True)
        subprocess.run([*flags, '-DCOH_VULKAN_GPU_PROBE_HOST_FIXTURE', str(SOURCE), '-o', str(cls.fixture), library], check=True)
        wrapper = cls.directory / 'guard.c'
        wrapper.write_text(GUARD.replace('SOURCE_PATH', json.dumps(str(SOURCE))))
        subprocess.run([*flags, str(wrapper), '-o', str(cls.guard), library], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def guard_output(self, name, env=None):
        return subprocess.check_output([str(self.guard), name], text=True,
            env=env or clean_environment(self.icd), timeout=15)

    def probe(self, executable, args=(), env=None):
        result = subprocess.run([str(executable), *args], text=True, capture_output=True,
            env=env or clean_environment(self.icd), timeout=15)
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith('COH_VULKAN_GPU_PROBE_V1 '))
        value = json.loads(lines[0].split(' ', 1)[1])
        self.assertEqual(set(value), FIELDS)
        self.assertEqual(value['format'], 1)
        self.assertEqual(value['pointer_bits'], 64)
        self.assertEqual(value['expected_bytes'], 4096)
        for name in FIELDS - {'status', 'failure_stage', 'kgsl_verified', 'native_gpu_executed', 'fill_verified'}:
            self.assertIs(type(value[name]), int)
            self.assertGreaterEqual(value[name], 0)
        for name in ('kgsl_verified', 'native_gpu_executed', 'fill_verified'):
            self.assertIs(type(value[name]), bool)
        return result, value

    def test_exact_source_derived_a740_descriptor(self):
        self.assertEqual(self.guard_output('chips'), '1111000')
        self.assertEqual(self.guard_output('development_chips'), '256')

    def test_identity_requires_kgsl_driver_vendor_version_and_same_chip(self):
        self.assertEqual(self.guard_output('identity'), '1000000')

    def test_environment_requires_one_owned_absolute_icd(self):
        self.assertEqual(self.guard_output('environment'), '1')
        cases = [{}, {'VK_DRIVER_FILES': 'relative.json', 'VK_ICD_FILENAMES': 'relative.json'},
            {'VK_DRIVER_FILES': '/a.json', 'VK_ICD_FILENAMES': '/b.json'},
            {'VK_DRIVER_FILES': '/a.json:/b.json', 'VK_ICD_FILENAMES': '/a.json:/b.json'}]
        for overrides in cases:
            env = clean_environment(); env.update(overrides)
            self.assertEqual(self.guard_output('environment', env), '0')
        for name in ('TU_FORCE_GPU_ID', 'MESA_VK_DEVICE_SELECT',
                'MESA_VK_DEVICE_SELECT_FORCE_DEFAULT_DEVICE', 'VK_INSTANCE_LAYERS',
                'VK_LAYER_PATH', 'VK_ADD_DRIVER_FILES'):
            env = clean_environment(self.icd); env[name] = ''
            self.assertEqual(self.guard_output('environment', env), '0')

    def test_actual_queue_fill_readback_has_no_hardware_authority(self):
        result, value = self.probe(self.fixture)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(value['status'], 'passed')
        self.assertEqual(value['failure_stage'], '')
        self.assertTrue(value['fill_verified'])
        self.assertEqual(value['bytes_verified'], 4096)
        self.assertFalse(value['kgsl_verified'])
        self.assertFalse(value['native_gpu_executed'])
        self.assertEqual(value['device_type'], 4)  # actual lavapipe CPU device
        self.assertIn('COH_VULKAN_GPU_PROBE_BUILD:host_fixture', result.stderr)

    def test_production_rejects_same_software_icd(self):
        result, value = self.probe(self.production)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(value['status'], 'failed')
        self.assertFalse(value['native_gpu_executed'])
        self.assertFalse(value['fill_verified'])
        self.assertIn(value['failure_stage'], ('kgsl', 'identity'))
        self.assertIn('COH_VULKAN_GPU_PROBE_BUILD:production', result.stderr)

    def test_arguments_and_unowned_environment_fail_before_device_use(self):
        for executable in (self.production, self.fixture):
            result, value = self.probe(executable, ('--override',))
            self.assertEqual(result.returncode, 1)
            self.assertEqual(value['failure_stage'], 'arguments')
            result, value = self.probe(executable, env=clean_environment())
            self.assertEqual(result.returncode, 1)
            self.assertEqual(value['failure_stage'], 'environment')
            self.assertEqual(value['bytes_verified'], 0)

    def test_missing_icd_returns_bounded_failure_record(self):
        result, value = self.probe(self.fixture, env=clean_environment(self.directory / 'missing.json'))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(value['failure_stage'], 'instance')
        self.assertFalse(value['fill_verified'])
        self.assertFalse(value['native_gpu_executed'])

    def test_compile_markers_cannot_confuse_fixture_with_production(self):
        self.assertIn(b'COH_VULKAN_GPU_PROBE_BUILD:production', self.production.read_bytes())
        self.assertNotIn(b'COH_VULKAN_GPU_PROBE_BUILD:host_fixture', self.production.read_bytes())
        self.assertIn(b'COH_VULKAN_GPU_PROBE_BUILD:host_fixture', self.fixture.read_bytes())
        self.assertNotIn(b'COH_VULKAN_GPU_PROBE_BUILD:production', self.fixture.read_bytes())


if __name__ == '__main__':
    unittest.main()
