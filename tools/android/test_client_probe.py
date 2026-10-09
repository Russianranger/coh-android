"""Reject missing, contradictory or overclaimed client-rendering evidence."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

from test_diagnostic import diagnostic


def sample():
    return {
        'format': 1, 'status': 'passed', 'failure_stage': '', 'pointer_bits': 32,
        'scope': 'headless_wgl_client_capabilities',
        'gl': {'vendor': 'Mesa', 'renderer': 'llvmpipe', 'version': '4.5',
               'renderer_class': 'software', 'pbuffer_exercised': False},
        'render': {'textured_quad_verified': True, 'samples_verified': 4, 'swap_buffers': True,
                   'rgb_samples': [[255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 255]]},
        'input': {'scope': 'synthetic_own_window_and_device_creation_only',
                  'window_messages_verified': True, 'keyboard_message_mask': 3, 'mouse_message_mask': 7,
                  'directinput_devices_created': True, 'directinput_hresult': 0, 'physical_input_validated': False},
        'audio': {'scope': 'device_enumeration_only', 'playback_validated': False},
        'cg_shaders_validated': False, 'game_rendering_validated': False,
        'android_surface_validated': False, 'hardware_acceleration_validated': False,
    }


def output(value):
    return 'COH_CLIENT_PROBE_V1 ' + json.dumps(value) + '\n'


class ClientEvidenceTests(unittest.TestCase):
    def test_realistic_wine_output_preserves_observed_identity_and_pixels(self):
        result = diagnostic.validate_client_probe('Wine warning\r\n' + output(sample()).replace('\n', '\r\n'))
        self.assertEqual(result['gl']['renderer'], 'llvmpipe')
        self.assertEqual(result['render']['rgb_samples'][2], [0, 0, 255])

    def test_missing_duplicate_malformed_or_ambiguous_result_is_rejected(self):
        valid = output(sample())
        for value in ('', 'PASS', valid + valid, valid.replace('V1 ', 'V1'),
                      'COH_CLIENT_PROBE_V1 []\n', 'COH_CLIENT_PROBE_V1 {bad}\n',
                      valid.replace('"status": "passed"', '"status":"failed","status":"passed"')):
            with self.subTest(value=value), self.assertRaises(diagnostic.DiagnosticError):
                diagnostic.validate_client_probe(value)

    def test_false_positive_render_and_input_claims_are_rejected(self):
        mutations = [('pointer_bits', 64), ('render.samples_verified', 0),
                     ('render.textured_quad_verified', False), ('render.swap_buffers', False),
                     ('render.rgb_samples', [[0, 0, 0]] * 4),
                     ('render.rgb_samples', [[255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, True]]),
                     ('input.keyboard_message_mask', 1), ('input.mouse_message_mask', 3),
                     ('input.directinput_devices_created', False), ('input.directinput_hresult', 1),
                     ('gl.renderer', ''), ('failure_stage', 'wgl_cleanup')]
        for path, value in mutations:
            evidence = sample()
            parent = evidence
            keys = path.split('.')
            for key in keys[:-1]:
                parent = parent[key]
            parent[keys[-1]] = value
            with self.subTest(path=path), self.assertRaises(diagnostic.DiagnosticError):
                diagnostic.validate_client_probe(output(evidence))

    def test_scope_expansion_and_missing_boundaries_cannot_pass(self):
        for key in ('cg_shaders_validated', 'game_rendering_validated', 'android_surface_validated',
                    'hardware_acceleration_validated'):
            for value in (True, None):
                evidence = sample()
                evidence[key] = value
                with self.subTest(key=key, value=value), self.assertRaises(diagnostic.DiagnosticError):
                    diagnostic.validate_client_probe(output(evidence))
        for section, key in (('input', 'physical_input_validated'), ('audio', 'playback_validated'),
                             ('gl', 'pbuffer_exercised')):
            evidence = sample()
            evidence[section][key] = True
            with self.subTest(section=section), self.assertRaises(diagnostic.DiagnosticError):
                diagnostic.validate_client_probe(output(evidence))

    def test_failure_can_be_preserved_but_cannot_be_accepted(self):
        evidence = sample()
        evidence.update(status='failed', failure_stage='wgl_context')
        evidence['gl']['renderer'] = ''
        evidence['render']['textured_quad_verified'] = False
        self.assertEqual(diagnostic.validate_client_probe(output(evidence), require_pass=False), evidence)
        with self.assertRaises(diagnostic.DiagnosticError):
            diagnostic.validate_client_probe(output(evidence))


class ClientAssetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.assets = Path(self.temp.name)
        pe = bytearray(256)
        pe[:2] = b'MZ'
        struct.pack_into('<I', pe, 60, 128)
        pe[128:132] = b'PE\0\0'
        struct.pack_into('<H', pe, 132, 0x14c)
        struct.pack_into('<H', pe, 152, 0x10b)
        self.manifest = {'format': 1, 'files': {}, 'runtime_probe': {
            'executable': 'runtime-probe.exe', 'marker': diagnostic.RUNTIME_MARKER, 'dll': 'probe.dll'}}
        for name in diagnostic.REQUIRED_ASSETS:
            (self.assets / name).write_bytes(pe)
            self.manifest['files'][name] = {'sha256': hashlib.sha256(pe).hexdigest()}
        (self.assets / 'client-probe.exe').write_bytes(pe)
        self.manifest['files']['client-probe.exe'] = {'sha256': hashlib.sha256(pe).hexdigest()}
        self.manifest['client_probe'] = {'executable': 'client-probe.exe', 'marker': 'COH_CLIENT_PROBE_V1 ',
                                         'scope': 'headless_wgl_client_capabilities', 'optional': True}
        self.write_manifest()

    def write_manifest(self):
        (self.assets / 'runtime-manifest.json').write_text(json.dumps(self.manifest))

    def test_optional_asset_is_not_needed_for_database_but_is_required_for_client(self):
        diagnostic.verify_assets(self.assets, client_probe=True)
        (self.assets / 'client-probe.exe').unlink()
        diagnostic.verify_assets(self.assets)
        with self.assertRaises(diagnostic.DiagnosticError):
            diagnostic.verify_assets(self.assets, client_probe=True)

    def test_modified_or_wrong_architecture_client_is_rejected(self):
        path = self.assets / 'client-probe.exe'
        data = bytearray(path.read_bytes())
        struct.pack_into('<H', data, 132, 0x8664)
        path.write_bytes(data)
        with self.assertRaisesRegex(diagnostic.DiagnosticError, 'hash mismatch'):
            diagnostic.verify_assets(self.assets, client_probe=True)
        self.manifest['files'][path.name]['sha256'] = hashlib.sha256(data).hexdigest()
        self.write_manifest()
        with self.assertRaisesRegex(diagnostic.DiagnosticError, 'PE32'):
            diagnostic.verify_assets(self.assets, client_probe=True)


if __name__ == '__main__':
    unittest.main()
