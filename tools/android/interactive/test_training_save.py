"""First training proof with synthetic stock-format records and selected SQL.

These host scenarios establish validator semantics, not an Android training
pass. The accepted ordinary reward/logout tests retain original device lines.
"""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import native_training_save as training
import local_character_server as server
import character_reopen_diagnostic as guest
import test_combat_reward_save as reward

PURCHASE = ('261004 22:35:00 City_01_01_1:127.0.0.1:127.0.0.1 "THORHERO:COHLOCAL" 0 '
    'BuyPower Click Blaster_Ranged.Archery.Fistful_of_Arrows ExpLevel:2, AlignmentNum:0, '
    'Archetype:Class_Blaster, Incarnate:0\n')
LOGOUT = reward.LOGOUT.replace('Level:1 XPLevel:1 XP:25', 'Level:2 XPLevel:2 XP:115').replace('ExpLevel:1', 'ExpLevel:2')
NAMES = ['Temporary_Powers.Temporary_Powers.Celebrate',
    'Inherent.Inherent.Brawl', 'Inherent.Inherent.Sprint',
    'Inherent.Inherent.Vision_Phase', 'Inherent.Inherent.Defiance',
    'Blaster_Ranged.Archery.Snap_Shot', 'Blaster_Support.Gadgets.Web_Grenade']


class TrainingSaveTests(unittest.TestCase):
    def instance(self):
        value, inventory = reward.CombatRewardSaveTests.instance(self)
        mapping = {'Class_Blaster': 1}

        def attribute(name):
            if name not in mapping:
                mapping[name] = len(mapping) + 1
            return mapping[name]

        def power(name, uid, level=0):
            category, powerset, pname = name.split('.')
            return dict(containerid=1, subid=0, powerid=1,
                categoryname=attribute(category), powersetname=attribute(powerset), powername=attribute(pname),
                powerlevelbought=level or None, powernumboostsbought=None,
                powersetlevelbought=None, buildnum=None, uniqueid=uid)

        before = value.baseline_snapshot['rows']
        before['ents'][0].update(experiencepoints=115, influencepoints=89, level=None)
        before['ents2'][0].update(originalprimary='Archery', originalsecondary='Gadgets')
        before['powers'] = [power(name, uid) for uid, name in enumerate(NAMES, 100)]
        for i, row in enumerate(before['powers']):
            row.update(subid=i, powerid=i + 1)
        self.rows = copy.deepcopy(before)
        self.rows['ents'][0].update(logincount=2, level=1)
        additions = [power(name, uid, training.AUTO_POWERS[name])
            for uid, name in enumerate(training.AUTO_POWERS, 200) if name not in NAMES]
        bought = power('Blaster_Ranged.Archery.Fistful_of_Arrows', 300, 1)
        self.rows['powers'] = self.rows['powers'][:5] + additions + [self.rows['powers'][5], bought, self.rows['powers'][6]]
        for i, row in enumerate(self.rows['powers']):
            row.update(subid=i, powerid=i + 1)
        value.schema['expected_attributes']['attributes'] = [dict(id=uid, name=name) for name, uid in mapping.items()]
        value.manual_atlas_startup = {'levelup_ui_repair_save': {'scope': 'physical_child_row_read_witness_and_order_only'}}
        value.current_logs.return_value = [(reward.ENTITY, reward.PERIODIC + PURCHASE + LOGOUT + reward.LOCATION)]
        return value, inventory

    def verify(self, value):
        logs = value.current_logs()
        return training.verify(logs, value.creation_report, reward.delivery(), server.logout_record(logs),
            value.baseline_snapshot['rows'], self.rows, value.schema['expected_attributes']['attributes'],
            session=reward.SESSION, client_pid=44, now_utc_ms=reward.NOW_MS)

    def test_native_purchase_first_training_and_seven_exact_auto_grants_keep_semantic_powers(self):
        value, inventory = self.instance()
        before = copy.deepcopy(value.baseline_snapshot)
        result = value.validate_saved_rows(self.rows, inventory)
        metadata = value.saved_metadata(result)
        self.assertTrue(metadata['native_training_values_committed_verified'])
        evidence = metadata['native_training_save_evidence']
        self.assertEqual((evidence['prior_power_count'], evidence['saved_power_count']), (7, 15))
        self.assertEqual(evidence['purchased_power']['power'], 'Blaster_Ranged.Archery.Fistful_of_Arrows')
        self.assertEqual(len(evidence['automatic_power_additions']), 7)
        self.assertTrue(evidence['prior_powers_preserved_by_uniqueid'])
        self.assertFalse(evidence['sql_game_mutations_performed'])
        self.assertFalse(evidence['trainer_identity_verified'])
        self.assertTrue(value.creation_report['committed_native_position_verified'])
        self.assertEqual(value.baseline_snapshot, before)
        self.assertEqual(result['rows']['ents2'], before['rows']['ents2'])
        self.assertEqual(result['rows']['costumeparts'], before['rows']['costumeparts'])

    def test_full_ordinary_logout_and_disconnected_sql_pipeline_accepts_first_training(self):
        value, inventory = self.instance()
        value.health = Mock()
        value.sample_progress = Mock(return_value={'available': True, 'tick_completed': 7, 'unchanged_seconds': 0})
        value.inventory = Mock(return_value=inventory)
        value.character_rows = Mock(return_value=self.rows)
        value.query = Mock(return_value='invalid container request\n')
        with patch.object(server.progress, 'compare_records'):
            proof = value.character_evidence()
        self.assertTrue(guest.save_verified(proof, reward.SESSION))
        for field in ('committed_sql_verified', 'disconnected_before_sql', 'requested_logout_observed',
                      'logout_timer_observed', 'powers_preserved', 'costume_preserved'):
            self.assertTrue(proof[field])
        self.assertFalse(proof['forced_stop_before_save'])
        self.assertEqual(value.character_evidence(), proof)

    def test_training_can_include_only_exact_existing_native_reward_deltas(self):
        value, inventory = self.instance()
        self.rows['ents'][0].update(experiencepoints=140, influencepoints=103)
        value.current_logs.return_value.append((reward.REWARDS, reward.AWARD_1 + reward.AWARD_2))
        result = value.validate_saved_rows(self.rows, inventory)
        metadata = value.saved_metadata(result)
        self.assertTrue(metadata['native_training_values_committed_verified'])
        self.assertTrue(metadata['native_reward_values_committed_verified'])
        self.rows['ents'][0]['experiencepoints'] = 141
        with self.assertRaises(server.base.DiagnosticError):
            value.validate_saved_rows(self.rows, inventory)

    def test_committed_training_rewards_then_following_reopen_keep_level_xp_and_purchased_uniqueid(self):
        value, inventory = self.instance()
        self.rows['ents'][0].update(experiencepoints=140, influencepoints=103)
        value.current_logs.return_value.append((reward.REWARDS, reward.AWARD_1 + reward.AWARD_2))
        first = value.validate_saved_rows(self.rows, inventory)
        self.assertTrue(value.saved_metadata(first)['native_training_values_committed_verified'])
        prior = copy.deepcopy(first)
        # Model the next server's captured committed SQL baseline and next
        # normal native login. No training witness exists in that new log tree.
        reopened, _ = self.instance()
        reopened.baseline_snapshot = prior
        reopened.creation_report.update(before_login_count=2,
            baseline={'character_id': 1, 'auth_id': 77, 'login_count': 2,
                'table_sha256': {}, 'row_counts': {}})
        self.rows = copy.deepcopy(prior['rows']); self.rows['ents'][0]['logincount'] = 3
        reopened.current_logs.return_value = [(reward.ENTITY, reward.PERIODIC + LOGOUT + reward.LOCATION)]
        second = reopened.validate_saved_rows(self.rows, inventory)
        self.assertEqual(second['rows']['ents'][0]['level'], 1)
        self.assertEqual(second['rows']['ents'][0]['experiencepoints'], 140)
        self.assertEqual(second['rows']['ents'][0]['influencepoints'], 103)
        self.assertEqual(next(row for row in second['rows']['powers'] if row['uniqueid'] == 300),
                         next(row for row in prior['rows']['powers'] if row['uniqueid'] == 300))
        self.assertEqual(second['rows']['powers'], prior['rows']['powers'])
        self.assertNotIn('native_training_values_committed_verified', reopened.saved_metadata(second))

    def test_other_available_original_primary_and_secondary_choices_are_bound_exactly(self):
        for path in ('Blaster_Ranged.Archery.Aimed_Shot', 'Blaster_Support.Gadgets.Caltrops'):
            value, inventory = self.instance()
            category, powerset, pname = path.split('.')
            attrs = value.schema['expected_attributes']['attributes']
            by_name = {row['name']: row['id'] for row in attrs}
            if pname not in by_name:
                uid = max(row['id'] for row in attrs) + 1
                attrs.append({'id': uid, 'name': pname}); by_name[pname] = uid
            bought = next(row for row in self.rows['powers'] if row['uniqueid'] == 300)
            bought.update(categoryname=by_name[category], powersetname=by_name[powerset], powername=by_name[pname])
            value.current_logs.return_value = [(reward.ENTITY, reward.PERIODIC + PURCHASE.replace(
                'Blaster_Ranged.Archery.Fistful_of_Arrows', path) + LOGOUT + reward.LOCATION)]
            with self.subTest(path=path):
                saved = value.validate_saved_rows(self.rows, inventory)
                self.assertEqual(value.saved_metadata(saved)['newly_purchased_power']['power'], path)

    def test_level_power_and_semantic_drifts_without_current_purchase_fail(self):
        value, inventory = self.instance()
        for bad in ('', PURCHASE[:-1], PURCHASE.replace('BuyPower Click', 'BuyPower:Error Click'),
                    PURCHASE.replace('Click ', ''), PURCHASE.replace('ExpLevel:2', 'ExpLevel:1'),
                    PURCHASE.replace('THORHERO', 'OTHERHERO'), PURCHASE.replace('Class_Blaster', 'Class_Tanker'),
                    PURCHASE.replace('AlignmentNum:0', 'AlignmentNum:1'),
                    PURCHASE.replace('Incarnate:0', 'Incarnate:1'),
                    PURCHASE.replace('Fistful_of_Arrows', 'Snap_Shot'),
                    PURCHASE.replace('22:35:00', '22:30:00'), PURCHASE.replace('22:35:00', '22:36:41')):
            value.current_logs.return_value = [(reward.ENTITY, reward.PERIODIC + LOGOUT + reward.LOCATION + bad)]
            with self.subTest(bad=bad), self.assertRaises(server.base.DiagnosticError):
                value.validate_saved_rows(self.rows, inventory)

    def test_local_verbose_logger_route_works_and_foreign_or_ambiguous_routes_fail(self):
        value, inventory = self.instance()
        local = PURCHASE.replace('City_01_01_1:127.0.0.1:127.0.0.1', '1')
        value.current_logs.return_value = [(reward.ENTITY, reward.PERIODIC + LOGOUT + reward.LOCATION),
                                          ('logs/mapserver/entity.log', local)]
        self.assertIsNotNone(value.validate_saved_rows(self.rows, inventory))
        for name, line in ((reward.ENTITY, local), ('logs/mapserver/entity.log', PURCHASE),
                           ('logs/foreign/entity.log', local), ('logs/mapserver/entity.log', local.replace(' 1 "', ' 0 "')),
                           (reward.ENTITY, PURCHASE.replace('City_01_01_1', 'City_01_01_2')),
                           (reward.ENTITY, PURCHASE * 2)):
            value.current_logs.return_value = [(reward.ENTITY, reward.PERIODIC + LOGOUT + reward.LOCATION), (name, line)]
            with self.subTest(name=name, line=line), self.assertRaises(server.base.DiagnosticError):
                value.validate_saved_rows(self.rows, inventory)
        value.current_logs.return_value = [(reward.ENTITY, reward.PERIODIC + PURCHASE + LOGOUT + reward.LOCATION),
                                          ('logs/mapserver/entity.log', local)]
        self.assertIsNone(self.verify(value))

    def test_each_preserved_power_field_and_all_other_tables_remain_strict(self):
        for table, fields in server.evidence.SELECTED.items():
            for field in fields:
                if table == 'ents' and field in ('level', 'experiencepoints', 'influencepoints'):
                    continue
                value, inventory = self.instance()
                row = self.rows[table][0]
                row[field] = 99999 if type(row[field]) is int else 'changed'
                with self.subTest(table=table, field=field), self.assertRaises(server.base.DiagnosticError):
                    value.validate_saved_rows(self.rows, inventory)

    def test_wrong_level_purchase_rows_duplicate_uniqueid_build_boost_or_auto_grants_fail(self):
        for field, changed in (('uniqueid', 100), ('uniqueid', None), ('uniqueid', True),
                ('uniqueid', -1), ('buildnum', 1), ('powerlevelbought', None),
                ('powerlevelbought', 2), ('powernumboostsbought', 1), ('powersetlevelbought', 1),
                ('powerid', 1000), ('subid', 1000)):
            value, inventory = self.instance()
            next(row for row in self.rows['powers'] if row['uniqueid'] == 300)[field] = changed
            with self.subTest(field=field, changed=changed), self.assertRaises(server.base.DiagnosticError):
                value.validate_saved_rows(self.rows, inventory)
        for field, changed in (('level', None), ('level', True), ('level', 2), ('experiencepoints', 105)):
            value, inventory = self.instance(); self.rows['ents'][0][field] = changed
            with self.subTest(field=field, changed=changed), self.assertRaises(server.base.DiagnosticError):
                value.validate_saved_rows(self.rows, inventory)
        for mutation in ('auto_wrong_level', 'auto_unknown', 'delete_old', 'new_uid_existing_name', 'no_purchase_row'):
            value, inventory = self.instance()
            if mutation == 'auto_wrong_level': self.rows['powers'][5]['powerlevelbought'] = 9
            if mutation == 'auto_unknown': self.rows['powers'][5]['powername'] = self.rows['powers'][0]['powername']
            if mutation == 'delete_old': self.rows['powers'].pop(0)
            if mutation == 'new_uid_existing_name': self.rows['powers'][5].update(value.baseline_snapshot['rows']['powers'][0], uniqueid=555)
            if mutation == 'no_purchase_row': self.rows['powers'] = [row for row in self.rows['powers'] if row['uniqueid'] != 300]
            with self.subTest(mutation=mutation), self.assertRaises(server.base.DiagnosticError):
                value.validate_saved_rows(self.rows, inventory)

    def test_current_producer_only_task_profile_and_ordinary_reopen_keep_strict_power_guards(self):
        for producer in (None, {}, {'startup_bundle_save': {}}, {'levelup_ui_repair_save': None}):
            value, inventory = self.instance(); value.manual_atlas_startup = producer
            with self.subTest(producer=producer), self.assertRaises(server.base.DiagnosticError):
                value.validate_saved_rows(self.rows, inventory)
        value, inventory = self.instance(); value.creation_report['task_gate_required'] = True
        with self.assertRaises(server.base.DiagnosticError):
            value.validate_saved_rows(self.rows, inventory)
        value, inventory = self.instance(); self.rows['ents'][0]['level'] = None
        with self.assertRaises(server.base.DiagnosticError):
            value.validate_saved_rows(self.rows, inventory)
        # A later unchanged level-2 reopen uses exact ordinary baseline proof;
        # it needs no second native purchase witness and cannot renumber powers.
        value, inventory = self.instance()
        value.baseline_snapshot['rows'] = copy.deepcopy(self.rows)
        value.baseline_snapshot['rows']['ents'][0]['logincount'] = 1
        value.current_logs.return_value = [(reward.ENTITY, reward.PERIODIC + LOGOUT + reward.LOCATION)]
        saved = value.validate_saved_rows(self.rows, inventory)
        self.assertNotIn('native_training_values_committed_verified', value.saved_metadata(saved))
        self.rows['powers'][0]['powerid'] += 1
        with self.assertRaises(server.base.DiagnosticError):
            value.validate_saved_rows(self.rows, inventory)

    def test_sender_position_recovery_and_bound_inventory_are_required_after_training(self):
        for failure in ('missing_sender', 'foreign_sender', 'missing_position', 'fallen', 'sql_position', 'recovery'):
            value, inventory = self.instance()
            path = value.owner.args.state / 'character-logout.json'
            if failure == 'missing_sender': path.unlink()
            if failure == 'foreign_sender': path.write_text(json.dumps(dict(reward.delivery(), session_id='f' * 32)))
            if failure == 'missing_position': value.current_logs.return_value = [(reward.ENTITY, PURCHASE + LOGOUT + reward.LOCATION)]
            if failure == 'fallen': value.current_logs.return_value[0] = (reward.ENTITY,
                reward.PERIODIC.replace('18.1875', '-2000') + PURCHASE + LOGOUT + reward.LOCATION)
            if failure == 'sql_position': value.character_position.return_value['posx'] += 10
            if failure == 'recovery': value.creation_report['recovery_requested'] = True
            with self.subTest(failure=failure), self.assertRaises(server.base.DiagnosticError):
                value.validate_saved_rows(self.rows, inventory)
            self.assertFalse(value.creation_report['committed_native_position_verified'])
        value, _ = self.instance()
        value.current_logs.return_value *= server.SERVER_LOG_COUNT_LIMIT + 1
        self.assertIsNone(self.verify(value))
        value, _ = self.instance()
        with patch.object(server, 'SERVER_LOG_FILE_LIMIT', 100):
            self.assertIsNone(self.verify(value))

    def test_source_contract_binds_real_success_format_and_original_first_level_schedule(self):
        native = ROOT / 'upstream/ouroboros'
        receive = (native / training.NATIVE_CONTRACT_FILES[0]).read_text()
        successful = receive[receive.index('if (character_BuyPower(pchar, pset, ppowBase, uniqueID) != NULL)'):]
        self.assertLess(successful.index('"BuyPower %s", dbg_BasePowerStr(ppowBase)'), successful.index('svrSendEntListToDb'))
        self.assertIn('LOG_LEVEL_VERBOSE', successful[:successful.index('svrSendEntListToDb')])
        self.assertIn('STR_COMBINE_CAT_C(\' \')', (native / 'MapServer/src/dbghelper.c').read_text())
        self.assertIn('iID = iCntPowers+1', (native / 'MapServer/src/entity/character_db.c').read_text())
        self.assertRegex((ROOT / 'upstream/i24/data/defs/experience.def').read_text(), r'ExperienceRequired\s+0,106,443')
        sets = (ROOT / 'upstream/i24/data/defs/powers/inherent.powersets').read_text()
        for name, level in training.AUTO_POWERS.items():
            with self.subTest(name=name):
                self.assertRegex(sets, r'Powers ' + name.replace('.', r'\.') + r'\s+Available ' + str(level) + r'\b')


if __name__ == '__main__': unittest.main()
