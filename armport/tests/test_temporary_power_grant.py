"""ARM64 reopen accepts only a server-added temporary power (Thor 0.13.39 rows)."""
import copy
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/app'), str(ROOT / 'android/guest')]
import local_character_server as character

ROW = dict(containerid=1, powerlevelbought=None, powernumboostsbought=None,
           powersetlevelbought=None, buildnum=None)
# Thor session 8f2ed736 before-logout powers (categoryname, powersetname, powername, uniqueid).
BEFORE = [(1367, 1367, 408, 1649555836), (1367, 1367, 6759, 1311144360),
          (1367, 1367, 6756, 1758889093), (1367, 1367, 6748, 421988681),
          (11427, 805, 11430, 942409123), (11419, 6142, 1219, 884730202)]
GRANT = (2312, 2312, 3117, 933277026)
NAMES = {1367: 'inherent', 408: 'sprint', 6759: 'rest', 6756: 'brawl', 6748: 'jump',
         11427: 'pool', 805: 'speed', 11430: 'hasten', 11419: 'primary', 6142: 'set', 1219: 'blast',
         2312: 'temporary_powers', 3117: 'brawl_tranq', 999: 'origin'}


def rows(entries):
    return [dict(ROW, subid=i, powerid=i + 1, categoryname=c, powersetname=s, powername=n, uniqueid=u)
            for i, (c, s, n, u) in enumerate(entries)]


class TemporaryPowerGrant(unittest.TestCase):
    def server(self):
        server = character.LocalCharacterReopenServer.__new__(character.LocalCharacterReopenServer)
        server.schema = {'expected_attributes': {'attributes': [
            {'id': key, 'name': value} for key, value in NAMES.items()]}}
        server.creation_report = {}
        return server

    def check(self, after, arch='arm64'):
        server = self.server()
        with patch.dict(os.environ, {'COH_CLIENT_ARCH': arch}):
            accepted = server.accept_added_temporary_powers(
                {'rows': {'powers': rows(BEFORE)}}, {'rows': {'powers': rows(after)}})
        return accepted, server.creation_report

    def test_thor_brawl_tranq_grant_is_accepted_on_arm64_only(self):
        accepted, report = self.check([GRANT] + BEFORE)
        self.assertTrue(accepted)
        grant = report['accepted_temporary_power_grants']
        self.assertEqual([item['resolved_power'] for item in grant['power_delta']['added_powers']],
                         ['temporary_powers.temporary_powers.brawl_tranq'])
        self.assertEqual(self.check([GRANT] + BEFORE, arch='x86'), (False, {}))

    def test_other_changes_keep_the_strict_failure(self):
        changed = list(BEFORE); changed[2] = (1367, 1367, 6759, BEFORE[2][3])
        for name, after in (('non-temporary addition', [(999, 999, 999, 77)] + BEFORE),
                            ('deleted prior power', [GRANT] + BEFORE[1:]),
                            ('changed prior power', [GRANT] + changed),
                            ('no change', BEFORE)):
            with self.subTest(name):
                self.assertEqual(self.check(after), (False, {}))


if __name__ == '__main__':
    unittest.main()
