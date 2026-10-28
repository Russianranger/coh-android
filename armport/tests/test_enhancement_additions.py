"""Exercise the real save comparator with bounded synthetic inventory changes.

The connection/logout log fixture is retained Thor evidence. Added Boosts rows,
prepared input roots and SQL positions are explicit controlled test boundaries;
these tests do not constitute a device save or independently prove loot events.
"""
import calendar
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'android/guest'))
import local_character_server as server
import character_zoning as zoning


def source(name):
    # git show also works in the sparse development worktree without copying
    # or modifying upstream/. Full CI checkout reads precisely the same bytes.
    return subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=ROOT)


class EnhancementAdditions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.definition = source('upstream/i24/data/defs/powers/boosts_generic_damage.powers')

    def instance(self):
        item = json.loads((ROOT / 'tools/android/interactive/fixtures/'
            'thor-save-lifecycle-0.13.35-20261013.json').read_text())['sessions'][1]
        state = Path(self.enterContext(tempfile.TemporaryDirectory()))
        context = SimpleNamespace(report={'client_worktree': {'imported_inputs_readonly': True}},
                                  event=Mock(), check=Mock())
        work, data, runtime = (state / name for name in ('work', 'game-data', 'native-runtime'))
        for path in (work, data, runtime):
            path.mkdir()
        owner = SimpleNamespace(ctx=context, root=state, work=work,
            args=SimpleNamespace(state=state, game_data=data, session_id=item['proof']['session_id']))
        value = server.LocalCharacterReopenServer(owner)
        value.creation_report.update(copy.deepcopy(item['proof']), zoning_enabled=True)
        value.baseline_snapshot = copy.deepcopy(item['before'])
        value.baseline = [copy.deepcopy(item['before']['identity'])]
        value.auth_id = item['proof']['auth_id']
        ids = {row[field] for table, fields in server.evidence.ATTRIBUTE_FIELDS.items()
               for row in item['before']['rows'][table] for field in fields if row[field]}
        attributes = [dict(id=identifier, name='fixture_' + str(identifier)) for identifier in sorted(ids)]
        attributes += [dict(id=100001, name='Boosts'), dict(id=100002, name='Generic_Damage')]
        value.schema = {'expected_attributes': {'attributes': attributes,
            'badgestatsattributes': [], 'pophelpattributes': []}}
        rows = copy.deepcopy(value.baseline_snapshot['rows'])
        rows['ents'][0]['logincount'] += 1
        value.character_rows = Mock(return_value=rows)
        baseline = self.boost(3)
        baseline['var0'] = .5  # Existing non-default payload must remain exact.
        value.baseline_enhancements = {'rows': [baseline], 'semantic': server.enhancement_semantics(
            [baseline], rows['powers'], attributes)}
        value.sql_rows = Mock(return_value=[copy.deepcopy(baseline)])
        value.runtime = value.atlas_map_runtime = value.kings_row_runtime = runtime
        value.server_data_identity = {'source_roots': [{'path': str(root),
            'identity': server.server_data_cache.fingerprint(root, directory=True)} for root in (work, data)]}
        leaf = data / 'data/defs/powers/boosts_generic_damage.powers'
        leaf.parent.mkdir(parents=True)
        leaf.write_bytes(self.definition)
        leaf.chmod(0o400)
        link = runtime / 'data/defs/powers/boosts_generic_damage.powers'
        link.parent.mkdir(parents=True)
        link.symlink_to(leaf)
        value.definition_leaf, value.definition_link = leaf, link
        self.enterContext(patch.object(server.time, 'mktime', side_effect=calendar.timegm))
        now_ms = item['logout_delivery']['sent_utc_ms'] + 40000
        self.enterContext(patch.object(server.time, 'time', return_value=now_ms / 1000))
        value.current_logs = Mock(return_value=item['native_logs'])
        value.native_positions = Mock(return_value=[item['native_position']])
        value.native_logout_record = lambda: zoning.stock_logout(item['native_logs'],
            value.creation_report['map_id'], value.creation_report['client_ready_observed_utc_ms'], now_ms)
        value.native_terminal_position = lambda delivery, start, end: zoning.terminal_position(
            item['native_logs'], value.creation_report['map_id'], delivery, start, end)
        terminal = value.native_terminal_position(item['logout_delivery'],
            value.creation_report['client_ready_observed_utc_ms'], now_ms)
        value.character_position = Mock(return_value=dict(containerid=1, mapid=1, staticmapid=1,
            **dict(zip(('posx', 'posy', 'posz'), terminal['position']))))
        value.inventory = Mock(return_value=value.baseline)
        value.health = Mock()
        value.query = Mock(return_value='invalid container request\n')
        value.sample_progress = Mock(return_value={'available': True, 'tick_completed': 7, 'unchanged_seconds': 0})
        self.enterContext(patch.object(server.progress, 'compare_records'))
        (state / 'character-logout.json').write_text(json.dumps(item['logout_delivery']))
        value.sql = Mock(side_effect=AssertionError('No SQL mutation or extra query permitted'))
        return value

    @staticmethod
    def boost(index, level=None):
        value = dict.fromkeys(server.BOOST_FIELDS)
        value.update(containerid=1, subid=index, powerid=-1, idx=index,
            categoryname=100001, powersetname=100002, boostname=100002, level=level)
        return value

    def save(self, value, arch='arm64'):
        with patch.dict(os.environ, {'COH_CLIENT_ARCH': arch}):
            return value.character_evidence()

    def test_existing_equal_inventory_and_one_addition_complete_normal_save(self):
        for added in (False, True):
            with self.subTest(added=added):
                value = self.instance()
                if added:
                    value.sql_rows.return_value.append(self.boost(0, 52))
                proof = self.save(value)
                self.assertTrue(proof['committed_sql_verified'])
                self.assertTrue(proof['enhancements_preserved'])
                comparison = proof['enhancement_preservation']
                self.assertFalse(comparison['native_gameplay_inventory_change_independently_verified'])
                if added:
                    observed = comparison['additive_inventory']
                    self.assertEqual(observed['added_inventory_count'], 1)
                    self.assertFalse(observed['native_award_causality_verified'])
                    self.assertFalse(observed['combat_defeat_verified'])
                    self.assertEqual(observed['additions'][0]['level'], 52)
                value.sql.assert_not_called()

    def test_inventory_limit_all_seventy_slots_from_empty_baseline(self):
        value = self.instance()
        value.baseline_enhancements = {'rows': [], 'semantic': []}
        value.sql_rows.return_value = [self.boost(i, i % 53) for i in range(70)]
        proof = self.save(value)
        self.assertEqual(proof['enhancement_preservation']['additive_inventory']['added_inventory_count'], 70)
        # One repeated definition is read/checked only once.
        self.assertEqual(len(proof['enhancement_preservation']['additive_inventory']['current_readonly_definitions']), 1)

    def test_current_definition_hash_does_not_claim_unchanged_bytes_since_preparation(self):
        value = self.instance()
        value.sql_rows.return_value.append(self.boost(0))
        leaf = value.definition_leaf
        changed = self.definition.replace(b'Accuracy             1', b'Accuracy             9')
        self.assertNotEqual(changed, self.definition)
        leaf.chmod(0o600); leaf.write_bytes(changed); leaf.chmod(0o400)
        proof = self.save(value)['enhancement_preservation']['additive_inventory']
        self.assertFalse(proof['definition_identity_since_preparation_verified'])
        self.assertFalse(proof['native_effect_verified'])
        self.assertFalse(proof['native_award_causality_verified'])
        self.assertTrue(proof['definition_identity_during_observation_verified'])
        observed = next(iter(proof['current_readonly_definitions'].values()))
        self.assertEqual(observed['sha256'], server.hashlib.sha256(changed).hexdigest())
        self.assertNotEqual(observed['sha256'], server.hashlib.sha256(self.definition).hexdigest())

    def test_definition_replaced_after_descriptor_open_is_refused(self):
        value = self.instance()
        value.sql_rows.return_value.append(self.boost(0))
        leaf = value.definition_leaf
        original = os.open
        def replace_after_open(path, *args, **kwargs):
            descriptor = original(path, *args, **kwargs)
            if Path(path) == leaf:
                leaf.unlink()
                leaf.write_bytes(self.definition)
                leaf.chmod(0o400)
            return descriptor
        with patch.object(server.os, 'open', side_effect=replace_after_open):
            with self.assertRaises(server.base.DiagnosticError):
                self.save(value)
        self.assertFalse(value.creation_report['committed_sql_verified'])

    def test_removal_mutation_reparenting_duplicates_and_noncanonical_additions_refused(self):
        mutations = {
            'removed_prior': lambda rows: rows.pop(0),
            'changed_prior_payload': lambda rows: rows[0].update(var0=.6),
            'moved_prior': lambda rows: rows[0].update(idx=2),
            'duplicate_slot': lambda rows: rows[1].update(idx=3),
            'duplicate_subid': lambda rows: rows[1].update(subid=3),
            'attached_new': lambda rows: rows[1].update(powerid=1),
            'bad_level': lambda rows: rows[1].update(level=53),
            'combined': lambda rows: rows[1].update(numcombines=1),
            'vars': lambda rows: rows[1].update(var3=.1),
            'powerup': lambda rows: rows[1].update(powerupslotid9=1),
            'mask': lambda rows: rows[1].update(slottedpowerupsmask=1),
            'foreign': lambda rows: rows[1].update(containerid=2),
            'slot_limit': lambda rows: rows[1].update(idx=70),
            'unknown_power_path': lambda rows: rows[1].update(boostname=100001),
        }
        for name, change in mutations.items():
            with self.subTest(name=name):
                value = self.instance()
                value.sql_rows.return_value.append(self.boost(0))
                change(value.sql_rows.return_value)
                with self.assertRaises(server.base.DiagnosticError):
                    self.save(value)
                self.assertFalse(value.creation_report['committed_sql_verified'])

    def test_x86_keeps_strict_policy_and_other_character_fields_still_fail(self):
        for changed in ('x86', 'costume', 'identity', 'login_count'):
            with self.subTest(changed=changed):
                value = self.instance()
                value.sql_rows.return_value.append(self.boost(0))
                rows = value.character_rows.return_value
                if changed == 'costume':
                    rows['costumeparts'][0]['color1'] = 17
                if changed == 'identity':
                    rows['ents'][0]['authid'] += 1
                if changed == 'login_count':
                    rows['ents'][0]['logincount'] += 1
                with self.assertRaises(server.base.DiagnosticError):
                    self.save(value, arch='x86' if changed == 'x86' else 'arm64')
                self.assertFalse(value.creation_report['committed_sql_verified'])

    def test_definition_missing_mutable_malformed_or_replaced_root_refused(self):
        for changed in ('missing', 'mutable', 'wrong_power', 'wrong_type', 'nested_type',
                        'root_identity', 'outside_root', 'copied_private_leaf', 'receipt'):
            with self.subTest(changed=changed):
                value = self.instance()
                value.sql_rows.return_value.append(self.boost(0))
                leaf = value.definition_leaf
                if changed == 'missing':
                    leaf.unlink()
                if changed == 'mutable':
                    leaf.chmod(0o600)
                if changed in ('wrong_power', 'wrong_type', 'nested_type'):
                    raw = self.definition.replace(b'Power Boosts.Generic_Damage.Generic_Damage',
                        b'Power Boosts.Generic_Damage.Bogus') if changed == 'wrong_power' else (
                        b'Power Boosts.Generic_Damage.Generic_Damage\n{\n Type kClick\n' +
                        (b' AttribMod\n {\n Type kBoost\n }\n' if changed == 'nested_type' else b'') + b'}\n')
                    leaf.chmod(0o600); leaf.write_bytes(raw); leaf.chmod(0o400)
                if changed == 'root_identity':
                    value.server_data_identity['source_roots'][0]['identity']['inode'] += 1
                if changed == 'outside_root':
                    target = leaf.parents[4] / 'outside.powers'
                    target.write_bytes(self.definition); target.chmod(0o400)
                    value.definition_link.unlink(); value.definition_link.symlink_to(target)
                if changed == 'copied_private_leaf':
                    value.definition_link.unlink(); value.definition_link.write_bytes(self.definition)
                if changed == 'receipt':
                    value.ctx.report['client_worktree']['imported_inputs_readonly'] = False
                with self.assertRaises(server.base.DiagnosticError):
                    self.save(value)
                self.assertFalse(value.creation_report['committed_sql_verified'])

    def test_missing_logout_or_session_binding_cannot_authorize_additions(self):
        for changed in ('delivery', 'session', 'native_logout', 'forced_stop'):
            with self.subTest(changed=changed):
                value = self.instance()
                value.sql_rows.return_value.append(self.boost(0))
                if changed == 'delivery':
                    (value.owner.args.state / 'character-logout.json').unlink()
                if changed == 'session':
                    value.creation_report['session_id'] = 'f' * 32
                if changed == 'native_logout':
                    value.native_logout_record = lambda: None
                if changed == 'forced_stop':
                    value.creation_report['forced_stop_before_save'] = True
                try:
                    result = self.save(value)
                except server.base.DiagnosticError:
                    result = None
                self.assertIsNone(result)
                self.assertFalse(value.creation_report['committed_sql_verified'])

    def test_level_bounds_and_payload_defaults_come_from_real_native_source(self):
        reward = source('upstream/ouroboros/MapServer/src/Reward.c').decode()
        header = source('upstream/ouroboros/Common/entity/power_system.h').decode()
        add = source('upstream/ouroboros/Common/entity/character_base.c').decode()
        self.assertRegex(header, r'#define MAX_PLAYER_SECURITY_LEVEL\s+50\b')
        self.assertIn('level = MAX_PLAYER_SECURITY_LEVEL+3;', reward)
        self.assertIn('character_AddBoost(e->pchar, basePower, level-1, 0, NULL)', reward)
        self.assertIn('character_SetBoost(p, i, ppowBase, iLevel, iNumCombines, NULL, 0, NULL, 0)', add)


if __name__ == '__main__':
    unittest.main()
