"""Patch 0135: the client's side of a zone transfer, as six tick-stamped boundaries. Evidence only.

CI run 45187469113 (0.13.81): the spare zone server was ready 9.3 s after the request and the
game had its new world 3.7 s later. The client waits up to 5 s for the old zone to answer its
disconnect (`netSendDisconnect(&comm_link, 5.f)`), then connects and asks for the scene; none
of that was recorded. The patch adds "xfer." records to the quiet log and the host reports
them per load as milliseconds before "map.start".
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/app'), str(ROOT / 'android/guest')]
PATCH = ROOT / 'armport/patches/0135-armport-transfer-boundaries.patch'
COMM = 'Game/src/clientcomm/clientcomm.c'
INIT = 'Game/src/gameComm/initClient.c'
TRACE = 'libs/UtilitiesLib/include/utilitieslib/utils/armport_zone_trace.h'


def sections(patch):
    found, name = {}, None
    for line in patch.splitlines():
        match = re.match(r'diff --git a/(\S+)', line)
        if match:
            name = match.group(1); found[name] = {'added': [], 'removed': []}
        elif name is None or line.startswith(('+++', '---', '@@', 'index ')):
            continue
        elif line.startswith('+'):
            found[name]['added'].append(line[1:])
        elif line.startswith('-'):
            found[name]['removed'].append(line[1:])
    return found


class TransferBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sections = sections(PATCH.read_text())

    def test_it_is_the_last_patch_and_touches_three_client_files(self):
        self.assertEqual((ROOT / 'armport/patches/series').read_text().split()[-1], PATCH.name)
        self.assertEqual(sorted(self.sections), sorted([COMM, INIT, TRACE]))

    def test_the_game_files_only_gain_trace_calls(self):
        stages = []
        for name in (COMM, INIT):
            self.assertEqual(self.sections[name]['removed'], [])
            for line in self.sections[name]['added']:
                text = line.strip()
                if not text or text.startswith(('/*', '*')) or text == '#include <utilitieslib/utils/armport_zone_trace.h>':
                    continue
                match = re.fullmatch(r'armportZoneTrace\("(xfer\.[a-z.]+)", (NULL|mapname)\);(\s*/\*.*\*/)?', text)
                self.assertIsNotNone(match, text)
                stages.append(match.group(1))
        self.assertEqual(stages, ['xfer.wait', 'xfer.address', 'xfer.disconnected',
                                  'xfer.connect.begin', 'xfer.connected', 'xfer.scene.done'])

    def test_the_disconnect_wait_is_between_its_two_records(self):
        patch = PATCH.read_text()
        self.assertRegex(patch, r'\+    armportZoneTrace\("xfer\.address", NULL\);\r?\n     dbOrMapConnect\(pak_in\);')
        self.assertRegex(patch, r'     netSendDisconnect\(&comm_link,5\.f\);\r?\n\+    armportZoneTrace\("xfer\.disconnected", NULL\);')
        self.assertRegex(patch, r'\+    armportZoneTrace\("xfer\.connect\.begin", NULL\);[^\n]*\n     if\(!tryConnect\(\)\)')

    def test_the_quiet_log_keeps_them(self):
        trace = self.sections[TRACE]
        self.assertEqual([line.strip() for line in trace['removed']], ['"texmodels.welded.", "texmodels.done"};'])
        added = '\n'.join(trace['added'])
        self.assertIn('"texmodels.welded.", "texmodels.done",', added)
        self.assertIn('"xfer."};', added)

    def test_the_host_reports_them_before_the_load_they_lead_to(self):
        import interactive_host as host
        log = '\n'.join([
            'ArmPort zone: 100 map.start maps/City_Zones/City_01_01/City_01_01.txt tid=1',
            'ArmPort zone: 7000 ready.sent  tid=1',
            'ArmPort zone: 50000 xfer.wait City_01_02 tid=1',
            'ArmPort zone: 59000 xfer.address  tid=1',
            'ArmPort zone: 61500 xfer.disconnected  tid=1',
            'ArmPort zone: 61520 xfer.connect.begin  tid=1',
            'ArmPort zone: 61700 xfer.connected  tid=1',
            'ArmPort zone: 61900 xfer.scene.done  tid=1',
            'ArmPort zone: 62000 map.start maps/City_Zones/City_01_02/City_01_02.txt tid=1',
            'ArmPort zone: 69000 ready.sent  tid=1',
        ])
        first, second = host.client_zone_loads(log)
        self.assertNotIn('transfer_ms_before', first)
        self.assertEqual(second['transfer_ms_before'], {'wait': 12000, 'address': 3000, 'disconnected': 500,
                                                        'connect.begin': 480, 'connected': 300, 'scene.done': 100})
        self.assertEqual(second['ms'], {'ready.sent': 7000})
        # A trip that begins while a load never reported ready closes that load.
        unfinished = host.client_zone_loads('\n'.join([
            'ArmPort zone: 100 map.start maps/a/a.txt tid=1',
            'ArmPort zone: 900 xfer.wait b tid=1',
            'ArmPort zone: 950 groups.files.done  tid=1',
            'ArmPort zone: 1000 map.start maps/b/b.txt tid=1']))
        self.assertEqual(unfinished[0]['ms'], {})
        self.assertEqual(unfinished[1]['transfer_ms_before'], {'wait': 100})


if __name__ == '__main__':
    unittest.main()
