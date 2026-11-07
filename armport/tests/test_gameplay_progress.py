"""ARM64 reopen: ordinary play combines changes the narrow verifiers accept one at a time.

Rows are the Thor 0.13.53 sessions (exports 20261104-193441 and -195518):
session 1 trained to level 2 and bought Burst, received the level's automatic
Inherent powers, a Day Job power and experience; session 2 saw that Day Job
power expire and the stock auto-set PowerSetLevelBought normalization.
"""
import copy
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/app'), str(ROOT / 'android/guest')]
import local_character_server as character  # noqa: E402
import native_training_save  # noqa: E402

COLUMNS = ('subid', 'powerid', 'categoryname', 'powersetname', 'powername', 'powerlevelbought',
           'powernumboostsbought', 'powersetlevelbought', 'buildnum', 'uniqueid')
B1 = [(0, 1, 2312, 2312, 3117, None, None, None, None, 933277026), (1, 2, 1367, 1367, 408, None, None, None, None, 1649555836), (2, 3, 1367, 1367, 6759, None, None, None, None, 1311144360), (3, 4, 1367, 1367, 6756, None, None, None, None, 1758889093), (4, 5, 1367, 1367, 6748, None, None, None, None, 421988681), (5, 6, 11427, 805, 11430, None, None, None, None, 942409123), (6, 7, 11419, 6142, 1219, None, None, None, None, 884730202)]  # noqa: E501
A1 = [(0, 1, 2312, 2344, 2449, None, None, None, None, 873465944), (1, 2, 2312, 2312, 3117, None, None, None, None, 933277026), (2, 3, 1367, 1367, 408, None, None, None, None, 1649555836), (3, 4, 1367, 1367, 6759, None, None, None, None, 1311144360), (4, 5, 1367, 1367, 6756, None, None, None, None, 1758889093), (5, 6, 1367, 1367, 6748, None, None, None, None, 421988681), (6, 7, 1367, 1367, 2953, 1, None, None, None, 1933790680), (7, 8, 1367, 1367, 6758, 1, None, None, None, 1338278401), (8, 9, 1367, 1367, 6757, 1, None, None, None, 1581157534), (9, 10, 1367, 5110, 6720, 1, None, None, None, 339073957), (10, 11, 1367, 5110, 5113, 1, None, None, None, 1466152830), (11, 12, 1367, 5110, 5112, 1, None, None, None, 192234668), (12, 13, 1367, 5110, 5111, 1, None, None, None, 82868611), (13, 14, 11427, 805, 11430, None, None, None, None, 942409123), (14, 15, 11427, 805, 773, 1, None, None, None, 1287522346), (15, 16, 11419, 6142, 1219, None, None, None, None, 884730202)]  # noqa: E501
A2 = [(0, 1, 2312, 2312, 3117, None, None, None, None, 933277026), (1, 2, 1367, 1367, 408, None, None, 1, None, 1649555836), (2, 3, 1367, 1367, 6759, None, None, 1, None, 1311144360), (3, 4, 1367, 1367, 6756, None, None, 1, None, 1758889093), (4, 5, 1367, 1367, 6748, None, None, 1, None, 421988681), (5, 6, 1367, 1367, 2953, 1, None, 1, None, 1933790680), (6, 7, 1367, 1367, 6758, 1, None, 1, None, 1338278401), (7, 8, 1367, 1367, 6757, 1, None, 1, None, 1581157534), (8, 9, 1367, 5110, 6720, 1, None, 1, None, 339073957), (9, 10, 1367, 5110, 5113, 1, None, 1, None, 1466152830), (10, 11, 1367, 5110, 5112, 1, None, 1, None, 192234668), (11, 12, 1367, 5110, 5111, 1, None, 1, None, 82868611), (12, 13, 11427, 805, 11430, None, None, None, None, 942409123), (13, 14, 11427, 805, 773, 1, None, None, None, 1287522346), (14, 15, 11419, 6142, 1219, None, None, None, None, 884730202)]  # noqa: E501
# Names resolved by the Thor report for every added row; the rest are stand-ins
# with the categories' real prefixes (only the prefixes matter to the policy).
NAMES = {2312: 'temporary_powers', 2344: 'day_job_powers', 2449: 'day_job_movement_increase_lesser',
         3117: 'brawl_tranq', 1367: 'inherent', 408: 'brawl', 6759: 'sprint', 6756: 'vision_phase',
         6748: 'defiance', 2953: 'walk', 6758: 'rest', 6757: 'fitness_fix', 5110: 'fitness',
         6720: 'swift', 5113: 'hurdle', 5112: 'health', 5111: 'stamina', 11427: 'blaster_ranged',
         805: 'assault_rifle', 11430: 'slug', 773: 'burst', 11419: 'blaster_support', 6142: 'devices',
         1219: 'toxic_dart', 9001: 'pool', 9002: 'speed', 9003: 'hasten'}
ATTRIBUTES = [{'id': key, 'name': value} for key, value in NAMES.items()]
BURST = [{'power': 'Blaster_Ranged.Assault_Rifle.Burst', 'displayed_level': 2}]


def powers(entries):
    return [dict(zip(COLUMNS, entry), containerid=1) for entry in entries]


def snapshot(entries, level, xp, influence, logins):
    return {'ents': [{'containerid': 1, 'authid': 7, 'authname': 'COHLOCAL', 'name': 'THORHERO', 'class': 252,
                      'origin': 257, 'level': level, 'experiencepoints': xp, 'influencepoints': influence,
                      'logincount': logins, 'description': None, 'motto': None, 'datecreated': 'x'}],
            'ents2': [{'containerid': 1, 'subid': 0, 'originalprimary': 'Assault_Rifle'}],
            'powers': powers(entries), 'costumeparts': [{'containerid': 1, 'subid': 0, 'name': 'part'}]}


S1_BEFORE, S1_AFTER = snapshot(B1, None, 158, 113, 11), snapshot(A1, 1, 227, 173, 12)
S2_BEFORE, S2_AFTER = snapshot(A1, 1, 227, 173, 12), snapshot(A2, 1, 227, 173, 13)


def progress(before, after, purchases):
    return character.gameplay_progress(before, after, ATTRIBUTES, purchases)


class ThorSessions(unittest.TestCase):
    def test_training_day_job_and_experience_in_one_session(self):
        result = progress(S1_BEFORE, S1_AFTER, BURST)
        self.assertTrue(result['accepted'], result.get('reason'))
        self.assertEqual(result['internal_level'], [0, 1])
        self.assertEqual(result['purchased_powers'], [{'power': 'blaster_ranged.assault_rifle.burst', 'internal_level': 1}])
        self.assertEqual(result['granted_temporary_powers'], ['temporary_powers.day_job_powers.day_job_movement_increase_lesser'])
        self.assertEqual(len(result['automatic_powers']), 7)
        self.assertFalse(result['sql_game_mutations_performed'])

    def test_day_job_expiry_and_auto_set_normalization_in_the_next(self):
        result = progress(S2_BEFORE, S2_AFTER, [])
        self.assertTrue(result['accepted'], result.get('reason'))
        self.assertEqual([item['power'] for item in result['expired_temporary_powers']],
                         ['temporary_powers.day_job_powers.day_job_movement_increase_lesser'])
        self.assertEqual(len(result['normalized_set_level_uniqueids']), 11)


class Refusals(unittest.TestCase):
    def refused(self, before, after, purchases, reason):
        result = progress(before, after, purchases)
        self.assertFalse(result['accepted'])
        self.assertEqual(result['reason'], reason)

    def test_purchases_must_match_the_native_records(self):
        self.refused(S1_BEFORE, S1_AFTER, [], 'purchases_differ_from_native_records')
        self.refused(S1_BEFORE, S1_AFTER, None, 'purchase_records_unavailable')
        self.refused(S1_BEFORE, S1_AFTER, [dict(BURST[0], displayed_level=3)], 'purchases_differ_from_native_records')
        self.refused(S2_BEFORE, S2_AFTER, BURST, 'purchases_differ_from_native_records')

    def test_lost_or_changed_prior_powers(self):
        after = copy.deepcopy(S2_AFTER)
        del after['powers'][-1]
        self.refused(S2_BEFORE, after, [], 'prior_power_removed')
        after = copy.deepcopy(S2_AFTER)
        after['powers'][12]['powersetlevelbought'] = 1          # Assault Rifle, not an Inherent set
        self.refused(S2_BEFORE, after, [], 'prior_power_set_level')
        after = copy.deepcopy(S2_AFTER)
        after['powers'][13]['powerlevelbought'] = 3
        self.refused(S2_BEFORE, after, [], 'prior_power_changed')
        after = copy.deepcopy(S2_AFTER)
        after['powers'][13]['powernumboostsbought'] = 1         # slots without a level
        self.refused(S2_BEFORE, after, [], 'prior_power_slots')

    def test_character_regressions_and_other_tables(self):
        self.refused(S2_AFTER, S1_BEFORE, [], 'level')
        lower = copy.deepcopy(S2_AFTER); lower['ents'][0]['experiencepoints'] = 100
        self.refused(S2_BEFORE, lower, [], 'experience_decreased')
        renamed = copy.deepcopy(S2_AFTER); renamed['ents'][0]['name'] = 'OTHER'
        self.refused(S2_BEFORE, renamed, [], 'ents_identity')
        costume = copy.deepcopy(S2_AFTER); costume['costumeparts'][0]['name'] = 'changed'
        self.refused(S2_BEFORE, costume, [], 'changed_costumeparts')

    def test_added_powers_must_be_a_grant_an_automatic_power_or_a_witnessed_purchase(self):
        extra = copy.deepcopy(S1_AFTER)
        extra['powers'].append(dict(extra['powers'][-1], subid=16, powerid=17, categoryname=9001,
                                    powersetname=9002, powername=9003, powerlevelbought=1, uniqueid=55))
        # A pool power is allowed as a purchase, but two purchases need two levels.
        self.refused(S1_BEFORE, extra, BURST + [{'power': 'pool.speed.hasten', 'displayed_level': 2}],
                     'purchases_exceed_levels')
        early = copy.deepcopy(S1_AFTER); early['powers'][14]['powerlevelbought'] = 0
        self.refused(S1_BEFORE, early, BURST, 'added_power_unclassified')


class NativeRecords(unittest.TestCase):
    LINE = ('{stamp} City_01_01_1:127.0.0.1:127.0.0.1 "THORHERO:COHLOCAL" 0 BuyPower Click '
            'Blaster_Ranged.Assault_Rifle.Burst ExpLevel:2, AlignmentNum:0, Archetype:Class_Blaster, '
            'Incarnate:0 BuildNumber: dev: 0000-00-00 00:00:00\n')

    def window(self, stamp):
        moment = int(time.mktime(time.strptime(stamp, '%y%m%d %H:%M:%S')) * 1000)
        return moment - 60000, moment + 60000

    def test_thor_record_from_the_embedded_dbserver_log(self):
        line = self.LINE.format(stamp='261104 19:31:07')
        start, end = self.window('261104 19:31:07')
        found = native_training_save.session_purchases(
            [('logs/dbserver/entity_2026-11-04-19-00-00.log', 'header\n' + line)], start, end)
        self.assertEqual([(item['power'], item['displayed_level']) for item in found],
                         [('Blaster_Ranged.Assault_Rifle.Burst', 2)])
        # Outside the window, nothing; a King's Row instance is read too.
        self.assertEqual(native_training_save.session_purchases(
            [('logs/dbserver/entity_1.log', line)], end + 1000, end + 2000), [])
        kings = line.replace('City_01_01_1', 'City_01_02_1')
        self.assertEqual(len(native_training_save.session_purchases([('logs/dbserver/entity_1.log', kings)],
                                                                     start, end)), 1)

    def test_malformed_or_unfinished_records_fail_closed(self):
        start, end = self.window('261104 19:31:07')
        line = self.LINE.format(stamp='261104 19:31:07')
        broken = line.replace('ExpLevel:2', 'ExpLevel:two')
        self.assertIsNone(native_training_save.session_purchases([('logs/dbserver/entity_1.log', broken)], start, end))
        self.assertIsNone(native_training_save.session_purchases(
            [('logs/dbserver/entity_1.log', line + line.rstrip('\n'))], start, end))
        local = line.replace('City_01_01_1:127.0.0.1:127.0.0.1', '1')
        other = local.replace('Burst', 'Slug')
        self.assertIsNone(native_training_save.session_purchases(
            [('logs/dbserver/entity_1.log', line), ('logs/mapserver/entity.log', other)], start, end))
        self.assertEqual(len(native_training_save.session_purchases(
            [('logs/dbserver/entity_1.log', line), ('logs/mapserver/entity.log', local)], start, end)), 1)


class ReopenComparison(unittest.TestCase):
    """The strict loop asks the progress policy once, only on ARM64, only after an ordinary logout."""
    def test_policy_gate(self):
        server = character.LocalCharacterReopenServer.__new__(character.LocalCharacterReopenServer)
        server.schema = {'expected_attributes': {'attributes': ATTRIBUTES}}
        server.creation_report = {'disconnected_before_sql': True, 'requested_logout_observed': True,
                                  'logout_timer_observed': True, 'forced_stop_before_save': False,
                                  'client_ready_observed_utc_ms': 1}
        server.owner = type('Owner', (), {'args': type('Args', (), {'session_id': 'a' * 32})()})()
        server.current_logs = lambda: []
        with patch.object(character, 'reopen_connection_binding', return_value={'map_id': 1}):
            with patch.dict(os.environ, {'COH_CLIENT_ARCH': 'x86'}):
                self.assertIsNone(server.accept_gameplay_progress({'rows': S2_BEFORE}, {'rows': S2_AFTER}))
            with patch.dict(os.environ, {'COH_CLIENT_ARCH': 'arm64'}):
                accepted = server.accept_gameplay_progress({'rows': S2_BEFORE}, {'rows': S2_AFTER})
                self.assertTrue(accepted['accepted'])
                self.assertEqual(server.creation_report['gameplay_progress']['connection'], {'map_id': 1})
                # Training needs its native record; none in the logs here.
                self.assertIsNone(server.accept_gameplay_progress({'rows': S1_BEFORE}, {'rows': S1_AFTER}))
                self.assertEqual(server.creation_report['gameplay_progress']['reason'],
                                 'purchases_differ_from_native_records')
                server.creation_report['forced_stop_before_save'] = True
                self.assertIsNone(server.accept_gameplay_progress({'rows': S2_BEFORE}, {'rows': S2_AFTER}))


if __name__ == '__main__':
    unittest.main()
