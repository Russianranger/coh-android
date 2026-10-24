import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'scripts'),
               str(Path(__file__).resolve().parents[1] / 'replay')]
import atlas_wine
import run_ci

RPC = ('0050:trace:seh:dispatch_exception code=6ba (RPC_S_SERVER_UNAVAILABLE) flags=0 addr=00006FFFFF8EA5A4\n'
       '0050:trace:seh:RtlUnwindEx code=6ba flags=2 end_frame=00007FFFFE1FEFC0 target_ip=00006FFFFDCA3974\n'
       '0050:trace:seh:RtlRestoreContext returning to 6ffffdca3974 stack 7ffffe1fefb0\n')
BOUNDARY = atlas_wine.BOUNDARY + '\n'


class AtlasWineTests(unittest.TestCase):
    def test_retained_real_wine_rpc_sequence(self):
        # Exact first 28 lines from run 40105902326, artifact 12566815878.
        # This older run predates 0067: the boundary below is a test input,
        # not proof that the historical Atlas run passed its verdict.
        text = (Path(__file__).parent / 'fixtures/atlas-startup-rpc-40105902326.txt').read_text()
        result = self.check(text + BOUNDARY)
        self.assertTrue(result['passed'])
        self.assertEqual(result['allowed_startup_rpc_exceptions'], 1)
        self.assertFalse(self.check(BOUNDARY + text)['passed'])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.wine = Path(self.temp.name) / 'wine'
        self.trace = Path(self.temp.name) / 'trace'
        self.trace.write_text(json.dumps(dict(stage='map.start', text='Atlas', tid=36)) + '\n')

    def check(self, text):
        self.wine.write_text(text)
        return atlas_wine.inventory(self.wine, self.trace)

    def test_only_completed_startup_rpc_is_allowed_and_counted(self):
        result = self.check(RPC * 2 + BOUNDARY)
        self.assertTrue(result['passed'])
        self.assertEqual(result['allowed_startup_rpc_exceptions'], 2)
        with self.assertRaisesRegex(ValueError, 'Wine exception/fatal'):
            run_ci.check_wine_output(self.wine)

    def test_same_rpc_after_first_map_start_fails(self):
        for data in (BOUNDARY + RPC, RPC + BOUNDARY + RPC,
                     RPC.splitlines(True)[0] + BOUNDARY + ''.join(RPC.splitlines(True)[1:])):
            self.assertFalse(self.check(data)['passed'])

    def test_handling_and_order_must_be_proven(self):
        for data in (RPC, BOUNDARY + BOUNDARY, RPC.replace('0050:trace:seh:RtlUnwindEx', '0051:trace:seh:RtlUnwindEx') + BOUNDARY,
                     ''.join(RPC.splitlines(True)[:2]) + BOUNDARY,
                     RPC.replace('returning to 6ffffdca3974', 'returning to 6ffffdca3978') + BOUNDARY,
                     RPC.replace('flags=0', 'flags=1') + BOUNDARY,
                     RPC + 'prefix ' + BOUNDARY):
            self.assertFalse(self.check(data)['passed'], data)
        self.trace.write_text(json.dumps(dict(stage='other', text='', tid=1)) + '\n')
        self.assertFalse(self.check(RPC + BOUNDARY)['passed'])

    def test_every_other_exception_and_fatal_stays_rejected(self):
        for failure in ('0024:trace:seh:dispatch_exception code=c0000005 flags=0',
                        '0024:trace:seh:raise_exception code=e0424242 flags=0',
                        '0024:err:seh:anything', 'wine: Unhandled page fault on read access',
                        'Unhandled exception', 'wine: fatal error',
                        'wine client error: write failed', '0024:err:module:import_dll missing'):
            self.assertFalse(self.check(RPC + failure + '\n' + BOUNDARY)['passed'], failure)

    def test_missing_files_do_not_pass(self):
        with self.assertRaises(ValueError):
            atlas_wine.inventory(self.wine, self.trace)
