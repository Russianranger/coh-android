"""Replay .35 physical differences without relabeling those original reports.

SQL position/ownership/status boundaries are controlled fixtures. Native logs,
selected SQL row snapshots and session identity come from the preserved device
archives. No device database is opened or mutated by these tests.
"""
import copy
import calendar
import json
from pathlib import Path
import shutil
import sys
import time
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import local_character_server as server
import character_zoning as zoning
import character_reopen_diagnostic as diagnostic

FIXTURE = ROOT / 'tools/android/interactive/fixtures/thor-save-lifecycle-0.13.35-20261013.json'


def sessions():
    return json.loads(FIXTURE.read_text())['sessions']


def attributes(session):
    ids = set()
    for snapshot in (session['before'], session['after']):
        for table, fields in server.evidence.ATTRIBUTE_FIELDS.items():
            ids.update(row[k] for row in snapshot['rows'][table] for k in fields if row[k])
    names = {2312: 'temporary_powers', 2344: 'day_job_powers', 2449: 'day_job_movement_increase_lesser'}
    return {'attributes': [dict(id=i, name=names.get(i, 'fixture_attribute_' + str(i))) for i in sorted(ids)],
            'badgestatsattributes': [], 'pophelpattributes': []}


class PhysicalSaveLifecycleTests(unittest.TestCase):
    def instance(self, index):
        item = sessions()[index]
        state = Path(self.enterContext(tempfile.TemporaryDirectory()))
        owner = SimpleNamespace(ctx=SimpleNamespace(report={}, event=Mock()), root=state,
            args=SimpleNamespace(state=state, session_id=item['proof']['session_id']))
        d = server.LocalCharacterReopenServer(owner)
        d.creation_report.update(item['proof'], zoning_enabled=True)
        d.baseline_snapshot = copy.deepcopy(item['before'])
        d.baseline = [copy.deepcopy(item['before']['identity'])]
        d.auth_id = item['proof']['auth_id']
        d.schema = {'expected_attributes': attributes(item)}
        # Synthetic complete enhancement rows exercise packed-ID changes. The
        # original .35 exports did not include Boosts and cannot prove equality.
        def boosts(rows):
            core = next(row for row in rows['powers'] if row['uniqueid'] == 425095545)
            boost = dict.fromkeys(server.BOOST_FIELDS)
            boost.update(containerid=1, subid=0, powerid=core['powerid'], idx=None,
                categoryname=1367, powersetname=1367, boostname=408, var0=0.5)
            return [boost, dict(boost, subid=1, powerid=-1, idx=3)]
        baseline_boosts = boosts(item['before']['rows'])
        d.baseline_enhancements = {'rows': baseline_boosts,
            'semantic': server.enhancement_semantics(baseline_boosts, item['before']['rows']['powers'],
                                                     d.schema['expected_attributes']['attributes'])}
        d.sql_rows = Mock(return_value=boosts(item['after']['rows']))
        d.runtime = state / 'native-runtime'; d.runtime.mkdir()
        d.kings_row_runtime = d.runtime; d.atlas_map_runtime = d.runtime
        for name in server.STOCK_DAYJOB_DATA_INPUTS:
            target = d.runtime / name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / 'upstream/i24' / name, target)
        # The Android guest logs use UTC; the host may have a different TZ.
        self.enterContext(patch.object(server.time, 'mktime', side_effect=calendar.timegm))
        now_ms = item['logout_delivery']['sent_utc_ms'] + 40000
        self.enterContext(patch.object(server.time, 'time', return_value=now_ms / 1000))
        d.current_logs = Mock(return_value=item['native_logs'])
        d.native_positions = Mock(return_value=[item['native_position']])
        d.native_logout_record = lambda: zoning.stock_logout(item['native_logs'], d.creation_report['map_id'],
            d.creation_report['client_ready_observed_utc_ms'], now_ms)
        d.native_terminal_position = lambda delivery, start, end: zoning.terminal_position(item['native_logs'],
            d.creation_report['map_id'], delivery, start, end)
        terminal = d.native_terminal_position(item['logout_delivery'],
            d.creation_report['client_ready_observed_utc_ms'], now_ms)
        self.assertIsNotNone(terminal)
        sql_position = dict(containerid=1, mapid=d.creation_report['map_id'],
            staticmapid=d.creation_report['map_id'], **dict(zip(('posx','posy','posz'), terminal['position'])))
        # Explicit synthetic SQL-location boundary: .35 aborted before exporting it.
        d.character_position = Mock(return_value=sql_position)
        d.inventory = Mock(return_value=d.baseline)
        d.character_rows = Mock(return_value=copy.deepcopy(item['after']['rows']))
        d.health = Mock(); d.query = Mock(return_value='invalid container request\n')
        d.sample_progress = Mock(return_value={'available': True, 'tick_completed': 7, 'unchanged_seconds': 0})
        self.enterContext(patch.object(server.progress, 'compare_records'))
        (state / 'character-logout.json').write_text(json.dumps(item['logout_delivery']))
        d.sql = Mock(side_effect=AssertionError('No SQL mutations or extra queries are permitted'))
        return d, item

    def test_both_physical_row_differences_pass_complete_normal_save_with_synthetic_matching_position(self):
        for index, map_id, count, lifecycle in ((0, 5, 6, 'added'), (1, 1, 7, 'removed')):
            with self.subTest(index=index):
                d, item = self.instance(index)
                before = copy.deepcopy(item)
                proof = d.character_evidence()
                self.assertTrue(zoning.save_verified(proof, item['proof']['session_id']))
                self.assertEqual(proof['saved_position']['staticmapid'], map_id)
                self.assertEqual(proof['login_count'], count)
                self.assertEqual(proof['temporary_power_lifecycle_observed'], lifecycle)
                self.assertTrue(proof['permanent_powers_preserved'])
                self.assertFalse(proof['dayjob_grant_independently_verified'])
                self.assertFalse(proof['native_stock_power_preservation']['sql_game_mutations_performed'])
                self.assertFalse(proof['native_stock_power_preservation']['spatial_predicates_verified'])
                self.assertEqual(item, before)
                d.sql.assert_not_called()
                if index == 1:
                    credit = proof['native_reward_credit_evidence']
                    self.assertEqual((credit['experiencepoints_delta'], credit['influencepoints_delta']), (25, 17))

    def test_actual_first_save_snapshot_is_the_next_session_baseline(self):
        first, second = sessions()
        self.assertEqual(first['after'], second['before'])
        self.assertEqual(first['after']['login_count'], 6)

    def test_core_power_costume_identity_and_unexplained_rewards_remain_failures(self):
        for change in ('core_loss', 'core_change', 'costume', 'identity', 'xp', 'inf', 'unknown_temp'):
            with self.subTest(change=change):
                d, item = self.instance(1); rows = d.character_rows.return_value
                if change == 'core_loss': rows['powers'].pop()
                if change == 'core_change': rows['powers'][0]['uniqueid'] += 1
                if change == 'costume': rows['costumeparts'][0]['color1'] += 1
                if change == 'identity': rows['ents'][0]['authid'] += 1
                if change == 'xp': rows['ents'][0]['experiencepoints'] += 1
                if change == 'inf': rows['ents'][0]['influencepoints'] += 1
                if change == 'unknown_temp':
                    rows['powers'].append(dict(rows['powers'][-1], uniqueid=99999, subid=7, powerid=8))
                with self.assertRaises(server.base.DiagnosticError): d.character_evidence()
                self.assertFalse(d.creation_report['committed_sql_verified'])
                self.assertFalse(diagnostic.save_verified(d.creation_report, item['proof']['session_id']))
                if change != 'identity':
                    observed = d.creation_report['post_logout_location_observation']
                    self.assertEqual(observed['saved_position']['staticmapid'], 1)
                    self.assertTrue(observed['sql_location_matches_native_logout'])
                    self.assertFalse(observed['complete_character_save_verified'])
                    self.assertTrue(d.creation_report['requested_logout_observed'])
                    self.assertTrue(d.creation_report['logout_timer_observed'])
                d.sql.assert_not_called()

    def test_source_or_definition_changes_never_authorize_temporary_power_loss(self):
        for change in ('native', 'definition', 'symlink'):
            with self.subTest(change=change):
                d, _ = self.instance(1)
                if change == 'native': d.creation_report['mapserver_producer']['mapserver_sha256'] = 'a'*64
                else:
                    path = d.runtime / next(iter(server.STOCK_DAYJOB_DATA_INPUTS))
                    if change == 'definition': path.write_text(path.read_text() + '\n')
                    else:
                        actual = path.with_suffix('.original'); path.rename(actual); path.symlink_to(actual)
                with self.assertRaises(server.base.DiagnosticError): d.character_evidence()
                self.assertFalse(d.creation_report['committed_sql_verified'])

    def readonly_definition_links(self, d):
        d.owner.work = d.owner.root / 'client'; d.owner.work.mkdir()
        d.owner.args.game_data = d.owner.root / 'import'; d.owner.args.game_data.mkdir()
        d.ctx.report['client_worktree'] = {'imported_inputs_readonly': True}
        d.server_data_identity = {'source_roots': [{'path': str(root),
            'identity': server.server_data_cache.fingerprint(root, directory=True)}
            for root in (d.owner.work, d.owner.args.game_data)]}
        for i, name in enumerate(server.STOCK_DAYJOB_DATA_INPUTS):
            path = d.runtime / name
            source = (d.owner.work, d.owner.args.game_data)[i] / name
            source.parent.mkdir(parents=True, exist_ok=True)
            path.rename(source); source.chmod(0o400); path.symlink_to(source)

    def test_prepared_readonly_definition_links_preserve_the_stock_lifecycle(self):
        for index in (0, 1):
            d, item = self.instance(index); self.readonly_definition_links(d)
            self.assertTrue(zoning.save_verified(d.character_evidence(), item['proof']['session_id']))

    def test_untrusted_or_changed_link_sources_never_authorize_temporary_power_loss(self):
        for change in ('writable', 'foreign', 'chain', 'parent_link', 'root_identity', 'receipt', 'during_read'):
            with self.subTest(change=change):
                d, _ = self.instance(1); self.readonly_definition_links(d)
                path = d.runtime / next(iter(server.STOCK_DAYJOB_DATA_INPUTS))
                actual = path.resolve()
                if change == 'writable': actual.chmod(0o600)
                if change == 'foreign':
                    other = d.owner.root / 'foreign'; actual.rename(other)
                    path.unlink(); path.symlink_to(other)
                if change == 'chain':
                    other = actual.with_suffix('.original'); actual.rename(other); actual.symlink_to(other)
                if change == 'parent_link':
                    other = actual.parent.with_name('other'); actual.parent.rename(other); actual.parent.symlink_to(other)
                if change == 'root_identity': d.server_data_identity['source_roots'][0]['identity']['inode'] += 1
                if change == 'receipt': d.ctx.report['client_worktree']['imported_inputs_readonly'] = False
                if change == 'during_read':
                    original_fdopen = server.os.fdopen
                    def race(fd, *args, **kwargs):
                        path.unlink(); path.symlink_to(actual)
                        return original_fdopen(fd, *args, **kwargs)
                    self.enterContext(patch.object(server.os, 'fdopen', side_effect=race))
                with self.assertRaises(server.base.DiagnosticError): d.character_evidence()
                self.assertFalse(d.creation_report['committed_sql_verified'])

    def test_partial_duplicate_foreign_wrong_map_rewards_cannot_authorize_points(self):
        for change in ('missing', 'partial', 'duplicate', 'foreign', 'wrong_map'):
            with self.subTest(change=change):
                d, item = self.instance(1)
                logs = copy.deepcopy(item['native_logs'])
                idx = next(i for i,(name,_) in enumerate(logs) if '/rewards_' in name)
                raw = logs[idx][1]
                if change == 'missing': raw = ''
                if change == 'partial': raw += next(l for l in raw.splitlines() if 'XP: 15' in l)
                if change == 'duplicate': raw += next(l for l in raw.splitlines(keepends=True) if 'XP: 15' in l)
                if change == 'foreign': raw = raw.replace('THORHERO:COHLOCAL','OTHER:COHLOCAL')
                if change == 'wrong_map': raw = raw.replace('City_01_01_1','City_01_02_1')
                logs[idx][1] = raw; d.current_logs.return_value = logs
                with self.assertRaises(server.base.DiagnosticError): d.character_evidence()

    def test_wrong_session_ready_process_identity_and_missing_independent_query_refuse_binding(self):
        for key, value in (('session_id','f'*32), ('auth_id',77), ('map_id',5),
                           ('windows_pid',999), ('sequence',True), ('loaded_world_assets',False)):
            d, item = self.instance(1)
            d.creation_report['client_ready_evidence'][key] = value
            self.assertIsNone(server.reopen_connection_binding(d.creation_report,
                item['proof']['session_id'], item['proof']['client_pid'], int(server.time.time()*1000)))
        for key in ('db_map_assignment_observed','connected_on_supported_map'):
            d, item = self.instance(1); d.creation_report[key] = False
            self.assertIsNone(server.reopen_connection_binding(d.creation_report,
                item['proof']['session_id'], item['proof']['client_pid'], int(server.time.time()*1000)))

    def test_enhancement_payload_slot_and_unique_power_attachment_survive_packed_ids(self):
        for kind in ('wrong_parent', 'drop', 'slot', 'payload', 'foreign', 'duplicate', 'orphan'):
            with self.subTest(kind=kind):
                d, item = self.instance(1); boosts = d.sql_rows.return_value
                if kind == 'wrong_parent': boosts[0]['powerid'] -= 1
                if kind == 'drop': boosts.pop()
                if kind == 'slot': boosts[0]['idx'] = 1
                if kind == 'payload': boosts[0]['var0'] = 0.6
                if kind == 'foreign': boosts[0]['containerid'] = 2
                if kind == 'duplicate': boosts.append(copy.deepcopy(boosts[0]))
                if kind == 'orphan': boosts[0]['powerid'] = 127
                with self.assertRaises(server.base.DiagnosticError): d.character_evidence()
                self.assertFalse(d.creation_report['committed_sql_verified'])
                self.assertEqual(d.creation_report['post_logout_location_observation']['saved_position']['staticmapid'], 1)
                self.assertFalse(d.creation_report['enhancement_preservation']['native_save_failure_proven'])

    def test_unverified_inventory_addition_is_incomplete_without_claiming_native_save_failure(self):
        d, _ = self.instance(1)
        boosts = d.sql_rows.return_value
        boosts.append(dict(boosts[1], subid=2, idx=4))
        with self.assertRaisesRegex(server.base.DiagnosticError, 'Character diagnostic incomplete'):
            d.character_evidence()
        proof = d.creation_report['enhancement_preservation']
        self.assertEqual(proof['status'], 'incomplete')
        self.assertFalse(proof['native_save_failure_proven'])
        self.assertFalse(proof['native_gameplay_inventory_change_independently_verified'])
        self.assertEqual(proof['saved_rows'], boosts)
        self.assertTrue(d.creation_report['post_logout_location_observation']['sql_location_matches_native_logout'])
        self.assertFalse(d.creation_report['committed_sql_verified'])

    def test_numeric_default_contract_is_exactly_the_retained_native_serializer(self):
        for name, expected in server.BOOST_ZERO_DEFAULT_SOURCE.items():
            self.assertEqual(server.hashlib.sha256((ROOT / 'upstream/ouroboros' / name).read_bytes()).hexdigest(), expected)
        import analyze_enhancement_persistence as analysis
        analysis.generated_contract(ROOT)
        self.assertEqual(analysis.BOOST_FIELDS, server.BOOST_FIELDS)
        source = (ROOT / analysis.SOURCE).read_text()
        section = source[source.index('LineDesc boost_line_desc[]'):source.index('StructDesc boost_desc[]')]
        descriptors = server.re.findall(r'PACKTYPE_(INT|FLOAT|ATTR),\s+[A-Z0-9_]+,\s+"([A-Za-z0-9_]+)"', section)
        numeric = {name.lower() for kind, name in descriptors if kind in ('INT', 'FLOAT')}
        self.assertEqual(numeric, {'powerid', 'idx', *server.BOOST_FIELDS[7:]})

    def test_native_null_zero_payload_defaults_preserve_normal_save_in_both_directions(self):
        for field in server.BOOST_FIELDS[7:]:
            for previous, current in ((None, 0), (0, None), (None, 0.0)):
                if isinstance(current, float) and field not in ('var0','var1','var2','var3'):
                    continue
                with self.subTest(field=field, previous=previous, current=current):
                    d, item = self.instance(1)
                    d.baseline_enhancements['rows'][0][field] = previous
                    d.baseline_enhancements['semantic'] = server.enhancement_semantics(
                        d.baseline_enhancements['rows'], item['before']['rows']['powers'],
                        d.schema['expected_attributes']['attributes'])
                    d.sql_rows.return_value[0][field] = current
                    proof = d.character_evidence()
                    self.assertTrue(zoning.save_verified(proof, item['proof']['session_id']))
                    self.assertIs(proof['enhancement_preservation']['before_rows'][0][field], previous)
                    self.assertEqual(proof['enhancement_preservation']['saved_rows'][0][field], current)

    def test_default_normalization_never_masks_nonzero_loss_or_missing_identity(self):
        for field in server.BOOST_FIELDS[7:]:
            for current in (None, 0, True):
                with self.subTest(field=field, current=current):
                    d, item = self.instance(1)
                    d.baseline_enhancements['rows'][0][field] = 1
                    d.baseline_enhancements['semantic'] = server.enhancement_semantics(
                        d.baseline_enhancements['rows'], item['before']['rows']['powers'],
                        d.schema['expected_attributes']['attributes'])
                    d.sql_rows.return_value[0][field] = current
                    with self.assertRaises(server.base.DiagnosticError): d.character_evidence()
                    self.assertFalse(d.creation_report['committed_sql_verified'])
        for field in ('categoryname','powersetname','boostname','powerid'):
            d, _ = self.instance(1); d.sql_rows.return_value[0][field] = None
            with self.assertRaises(server.base.DiagnosticError): d.character_evidence()

    def history(self, d, item):
        current = copy.deepcopy(d.creation_report)
        initial = copy.deepcopy(current)
        initial.update(map_id=5, client_ready_evidence=item['initial_native_ready'],
            client_ready_observed_utc_ms=item['initial_native_ready']['utc_ms'])
        d.creation_report.update(initial); d.remember_reward_connection()
        history = d.creation_report['reward_connection_history']
        d.creation_report.update(current, reward_connection_history=history)
        d.remember_reward_connection()
        d.zoning_report = {'transfers': [copy.deepcopy(item['native_transfer'])]}

    def test_rewards_before_and_after_verified_native_transfer_are_both_preserved(self):
        d, item = self.instance(1); self.history(d, item)
        reward_index = next(i for i,(name,_) in enumerate(item['native_logs']) if '/rewards_' in name)
        sample = next(l for l in item['native_logs'][reward_index][1].splitlines(keepends=True) if 'XP: 15' in l)
        early = time.strftime('%y%m%d %H:%M:%S', time.gmtime((item['initial_native_ready']['utc_ms'] + 10000) / 1000))
        extra = (early + sample[15:]).replace('City_01_01_1','City_01_02_1').replace('XP: 15','XP: 5').replace('Inf: 7','Inf: 2')
        d.current_logs.return_value[reward_index][1] += extra
        d.character_rows.return_value['ents'][0].update(experiencepoints=50, influencepoints=36)
        proof = d.character_evidence()
        self.assertTrue(zoning.save_verified(proof, item['proof']['session_id']))
        credit = proof['native_reward_credit_evidence']
        self.assertEqual((credit['experiencepoints_delta'],credit['influencepoints_delta']), (30,19))
        self.assertEqual([w['connection']['map_id'] for w in credit['reward_connection_windows']], [5,1])
        self.assertEqual(len(d.creation_report['reward_connection_history']), 2)
        d.remember_reward_connection()
        self.assertEqual(len(d.creation_report['reward_connection_history']), 2)

    def test_forged_transfer_or_wrong_interval_cannot_authorize_old_map_rewards(self):
        for change in ('foreign_pid','foreign_session','wrong_destination','arrival','overlap','stale_ready'):
            with self.subTest(change=change):
                d,item = self.instance(1); self.history(d,item)
                leg = d.zoning_report['transfers'][0]
                if change == 'foreign_pid': leg['delivery']['native_station_departure']['pid'] += 1
                if change == 'foreign_session': leg['delivery']['session_id'] = 'f'*32
                if change == 'wrong_destination': leg['delivery']['native_station_departure']['target'] = 5
                if change == 'arrival': leg['arrival_native_verified'] = False
                if change == 'overlap': leg['delivery']['sent_utc_ms'] = item['proof']['client_ready_observed_utc_ms'] + 1
                if change == 'stale_ready': leg['native_ready']['line_sha256'] = 'a'*64
                with self.assertRaises(server.base.DiagnosticError): d.character_evidence()
                self.assertFalse(d.creation_report['committed_sql_verified'])

    def test_direct_kings_reward_route_is_exact_and_other_map_is_excluded(self):
        d,item = self.instance(0)
        sample = next(raw for name,raw in sessions()[1]['native_logs'] if '/rewards_' in name)
        line = next(l for l in sample.splitlines(keepends=True) if 'XP: 15' in l)
        stamp = time.strftime('%y%m%d %H:%M:%S', time.gmtime((item['logout_delivery']['sent_utc_ms'] - 10000)/1000))
        line = (stamp + line[15:]).replace('City_01_01_1','City_01_02_1')
        d.current_logs.return_value.append(['logs/dbserver/rewards_2026-10-13-03-00-00.log', line])
        d.character_rows.return_value['ents'][0].update(experiencepoints=35,influencepoints=24)
        proof = d.character_evidence()
        self.assertTrue(zoning.save_verified(proof,item['proof']['session_id']))
        self.assertEqual(proof['native_reward_credit_evidence']['experiencepoints_delta'],15)

    def test_packing_reorder_preserves_stable_identity_but_not_semantic_mutations(self):
        item = sessions()[1]; before = item['after']['rows']['powers']; after = copy.deepcopy(before[::-1])
        for i,row in enumerate(after): row.update(subid=i, powerid=i+1)
        kwargs = dict(native_sha256=server.SERVER_TEXTURE_EXCLUSION_MAP, data_sha256=server.STOCK_DAYJOB_DATA_INPUTS)
        proof = server.stock_power_preservation(before, after, attributes(item)['attributes'], **kwargs)
        self.assertEqual(proof['temporary_lifecycle'], 'unchanged')
        for key in ('powernumboostsbought','powersetlevelbought','buildnum','powerlevelbought'):
            changed = copy.deepcopy(after); changed[0][key] = 1
            self.assertIsNone(server.stock_power_preservation(before, changed, attributes(item)['attributes'], **kwargs))


if __name__ == '__main__': unittest.main()
