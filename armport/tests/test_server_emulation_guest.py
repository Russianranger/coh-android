"""0.13.79: emulator settings reach the zone servers only when asked for, and are recorded."""
import os
from pathlib import Path
import re
import sys
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'android/guest'))
sys.path.insert(0, str(ROOT / 'armport/app'))
import local_character_server as server

TSO = 'MapServer.exe:mapserver.exe:MAPSERVER.EXE'


def method():
    for name in dir(server):
        cls = getattr(server, name)
        if isinstance(cls, type) and 'map_metrics_environment' in vars(cls):
            return vars(cls)['map_metrics_environment']
    raise AssertionError('map_metrics_environment not found')


class ServerEmulationGuest(unittest.TestCase):
    def apply(self, requested, inherited=None):
        environment = dict(inherited or {}, KEEP='1')
        with mock.patch.dict(os.environ, {'COH_SERVER_EMULATION': requested} if requested is not None else {}):
            if requested is None:
                os.environ.pop('COH_SERVER_EMULATION', None)
            return environment, server.apply_server_emulation(environment)

    def test_nothing_is_set_unless_asked_and_an_inherited_variable_is_removed(self):
        environment, record = self.apply(None, {'FEX_X87REDUCEDPRECISION': '1', 'FEX_EXTENDEDVOLATILEMETADATA': 'x'})
        self.assertEqual(environment, {'KEEP': '1'})
        self.assertEqual(record, {'format': 1, 'requested': [], 'ignored': [], 'environment': {},
                                  'scope': 'zone_servers_only', 'is_success_proof': False})
        self.assertEqual(self.apply('')[0], {'KEEP': '1'})

    def test_each_setting_names_one_emulator_variable(self):
        environment, record = self.apply('tso')
        self.assertEqual(environment, {'KEEP': '1', 'FEX_EXTENDEDVOLATILEMETADATA': TSO})
        self.assertEqual((record['requested'], record['environment']), (['tso'], {'FEX_EXTENDEDVOLATILEMETADATA': TSO}))
        environment, record = self.apply('x87', {'FEX_EXTENDEDVOLATILEMETADATA': 'stale'})
        self.assertEqual(environment, {'KEEP': '1', 'FEX_X87REDUCEDPRECISION': '1'})
        environment, record = self.apply(' x87 , tso ')
        self.assertEqual(record['requested'], ['tso', 'x87'])          # table order, not the order asked
        self.assertEqual(environment, {'KEEP': '1', 'FEX_EXTENDEDVOLATILEMETADATA': TSO, 'FEX_X87REDUCEDPRECISION': '1'})

    def test_the_module_list_is_what_the_emulator_parses(self):
        # FEX splits modules at ':' and a module's ranges at ';' (Source/Common/VolatileMetadata.cpp):
        # a bare name disables store-order emulation for that module only.
        variable, value = server.SERVER_EMULATION_SETTINGS['tso']
        self.assertEqual(variable, 'FEX_EXTENDEDVOLATILEMETADATA')
        self.assertNotIn(';', value)
        self.assertEqual({name.lower() for name in value.split(':')}, {'mapserver.exe'})
        # Never the whole-process switch, which also drops it for Wine's and PhysX's code.
        self.assertFalse(any('TSOENABLED' in variable for variable, _ in server.SERVER_EMULATION_SETTINGS.values()))

    def test_an_unknown_name_is_ignored_and_recorded_never_a_reason_to_stop(self):
        environment, record = self.apply('tso,fast,' + 'y' * 40)
        self.assertEqual(environment, {'KEEP': '1', 'FEX_EXTENDEDVOLATILEMETADATA': TSO})
        self.assertEqual(record['ignored'], ['fast', 'y' * 24])

    def test_every_zone_server_start_goes_through_it_and_the_report_holds_the_record(self):
        value = types.SimpleNamespace(owner=None, map_package={'files': {}}, creation_report={})
        with mock.patch.dict(os.environ, {'COH_SERVER_EMULATION': 'x87'}):
            os.environ.pop('COH_PHYSX_CACHE', None); os.environ.pop('COH_TRUSTED_BINS', None)
            environment = method()(value, {'KEEP': '1', 'FEX_EXTENDEDVOLATILEMETADATA': 'stale'}, ROOT)
        self.assertEqual(environment, {'KEEP': '1', 'FEX_X87REDUCEDPRECISION': '1'})
        self.assertEqual(value.creation_report['server_emulation']['environment'], {'FEX_X87REDUCEDPRECISION': '1'})
        # The initial zone, a travelled-to zone and the spare all build their environment there.
        zoning = (ROOT / 'android/guest/character_zoning.py').read_text()
        own = (ROOT / 'android/guest/local_character_server.py').read_text()
        self.assertEqual(len(re.findall(r'self\.map_metrics_environment\(', zoning)), 2)
        self.assertEqual(len(re.findall(r'self\.map_metrics_environment\(', own)), 1)
        # The DbServer and the client are started without it: the names appear nowhere else in the guest.
        for path in (ROOT / 'android/guest').glob('*.py'):
            if path.name != 'local_character_server.py':
                self.assertNotIn('FEX_X87REDUCEDPRECISION', path.read_text(), path.name)
                self.assertNotIn('FEX_EXTENDEDVOLATILEMETADATA', path.read_text(), path.name)


class ServerEmulationHost(unittest.TestCase):
    def test_ci_input_reaches_the_guest_command_and_the_log_line(self):
        import interactive_host as host
        for value in ('', 'tso', 'x87', 'tso,x87'):
            with mock.patch.dict(os.environ, {'COH_SERVER_EMULATION': value}):
                self.assertEqual(host.server_emulation_requested(), value)
        for value in ('TSO', 'tso x87', 'tso;x87', 'a,b,c,d,e', 'tso,'):
            with mock.patch.dict(os.environ, {'COH_SERVER_EMULATION': value}):
                with self.assertRaises(ValueError):
                    host.server_emulation_requested()
        source = (ROOT / 'armport/app/interactive_host.py').read_text()
        self.assertIn("'COH_SERVER_EMULATION=' + server_emulation_requested()", source)
        record = {'format': 1, 'requested': ['tso'], 'ignored': [], 'environment': {'FEX_EXTENDEDVOLATILEMETADATA': TSO},
                  'scope': 'zone_servers_only', 'is_success_proof': False}
        line = host.start_options_line({'character_reopen': {'server_emulation': record}}, 'reopen')
        self.assertIn('"server_emulation":{"requested":["tso"],"ignored":[],"environment":{"FEX_EXTENDEDVOLATILEMETADATA":"'
                      + TSO + '"}}', line)
        self.assertIn('"server_emulation":null', host.start_options_line({}, 'reopen'))
        workflow = (ROOT / '.github/workflows/armport-app-runtime.yml').read_text()
        self.assertIn('      server_emulation:\n', workflow)
        self.assertIn("  COH_SERVER_EMULATION: ${{ inputs.server_emulation }}\n", workflow)


if __name__ == '__main__':
    unittest.main()
