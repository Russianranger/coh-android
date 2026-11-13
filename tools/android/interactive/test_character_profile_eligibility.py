"""Pre-Wine profile eligibility, real SQL, and non-destructive first-create resume."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'android/guest'), str(Path(__file__).parent)]
import character_creation_diagnostic as creation
import local_character_server as server
from test_character_server import fixture

REQUIRE_POSTGRESQL = os.environ.get('COH_REQUIRE_POSTGRESQL') == '1'
POSTGRES_FIXTURES_RUN = set()
REQUIRED_POSTGRES_FIXTURES = {
    'missing_inventory_creation', 'missing_inventory_reopen', 'empty_inventory_resume',
    'empty_inventory_reopen', 'saved_character_reopen', 'saved_character_resume_refused',
    'foreign_character_resume_refused', 'foreign_character_reopen_refused',
    'ambiguous_character_reopen_refused', 'provisional_character_reopen_refused',
    'missing_power_rows_reopen_refused', 'advanced_empty_allocator_resume_refused',
    'post_dbserver_character_race_refused', 'post_dbserver_allocator_race_refused',
    'unentered_character_resume_removed', 'unentered_character_reopen_explained',
    'unentered_character_with_badge_refused',
    'named_character_reopen', 'unentered_named_character_resume_removed',
}


def saved_fixture():
    rows, _, attributes = fixture()
    for values in rows.values():
        for row in values:
            row['containerid'] = 1
    inventory = [{key: rows['ents'][0][key] for key in server.evidence.IDENTITY_FIELDS}]
    return rows, inventory, attributes


# Thor 0.13.60 (exports 20261108-135104/-135110): the row the DbServer kept
# after a new villain's Mercy Island start failed in 0.13.59.
UNENTERED_IDENTITY = {'containerid': 1, 'authid': 1353310574, 'authname': 'COHLOCAL', 'name': 'THORHERO'}
# The DbServer's own write of a created character (s_finishHandleChoosePlayer,
# setNewMap, updateAuthUserData; COH_PG_INSERT_CONTAINER reserves the ID).
UNENTERED_ENTS = dict(UNENTERED_IDENTITY, active=0, staticmapid=71, mapid=71, playertype=1, accesslevel=0)
UNENTERED_ENTS2 = {'containerid': 1, 'subid': 0, 'influencetype': 1, 'praetorianprogress': 0, 'playersubtype': 0}
# One child table outside the selected evidence stands for the other Ents tables.
TEMPLATE = ('TeamupsId "int4" indexed\nAuthId "int4" indexed\nName "ansistring[128]" indexed\n'
            'Ents2[0].InfluenceType "int4"\nPowers[1000].PowerId "int4"\nCostumeParts[1000].Name "ansistring[64]"\n'
            'Badges[1000].Badge "int4"\n')


def unentered_rows():
    rows = {table: [] for table in server.evidence.SELECTED}
    rows['ents'] = [dict({field: None for field in server.evidence.SELECTED['ents']}, logincount=None, **UNENTERED_IDENTITY)]
    rows['ents2'] = [{field: UNENTERED_ENTS2.get(field) for field in server.evidence.SELECTED['ents2']}]
    return rows


def expected_tables():
    tables = {table: list(fields) + (['logincount'] if table == 'ents' else [])
              for table, fields in server.evidence.SELECTED.items()}
    tables['ents'][1:1] = ['active']
    tables['ents'] += ['staticmapid', 'mapid', 'playertype', 'accesslevel']
    tables['badges'] = ['containerid', 'subid', 'badge']
    return tables


class EligibilityTests(unittest.TestCase):
    def tearDown(self):
        server.reset_character()   # 0.13.62: a session's bound name never leaks into the next test

    def instance(self, *, reopen=False, resume=False, profile=True, presence='present', inventory=None):
        state = Path(self.enterContext(tempfile.TemporaryDirectory(prefix='coh-profile-gate-')))
        owner = SimpleNamespace(ctx=SimpleNamespace(report={}, children=[], start=Mock(), event=Mock()), root=state,
            args=SimpleNamespace(session_id='1'*32, state=state, resume_empty_profile=resume))
        value = (server.LocalCharacterReopenServer if reopen else server.LocalCharacterServer)(owner)
        rows, saved, attributes = saved_fixture()
        value.schema_dir = state / 'schema'
        (value.schema_dir / server.ENTS_TEMPLATE).parent.mkdir(parents=True)
        (value.schema_dir / server.ENTS_TEMPLATE).write_text(TEMPLATE)
        value.schema = {'expected_attributes': attributes, 'files': {server.ENTS_TEMPLATE: {}},
            'expected_tables': expected_tables()}
        value.inventory = Mock(return_value=copy.deepcopy(saved if inventory is None and reopen else inventory or []))
        value.character_rows = Mock(return_value=copy.deepcopy(rows))
        value.sql = Mock(side_effect=lambda text, **_: presence if 'to_regclass' in text else '0')
        if profile:
            value.profile.mkdir()
            (value.profile/'profile.json').write_text(json.dumps(dict(server.login.PROFILE_IDENTITY, initialized=True)))
            (value.profile/'credentials.json').write_text('{}')
            (value.profile/'pgdata').mkdir()
            (value.profile/'pgdata/PG_VERSION').write_text('18')
        return value

    def initialize_gate(self, value):
        reused = value.profile.exists()
        def initialized(current):
            current.report['profile_reused'] = reused
        with patch.object(server.login.LocalLoginServer, 'initialize', autospec=True, side_effect=initialized) as native:
            value.initialize()
        native.assert_called_once_with(value)
        value.ctx.start.assert_not_called()
        for call in value.sql.call_args_list:
            self.assertTrue(call.args[0].startswith('SELECT '))
        return value.creation_report['profile_eligibility']

    def test_missing_native_inventory_is_allowed_only_for_explicit_creation(self):
        for resume in (False, True):
            value = self.instance(resume=resume, profile=resume, presence='missing')
            proof = self.initialize_gate(value)
            self.assertTrue(proof['eligible']); self.assertTrue(proof['empty_inventory_verified'])
            self.assertEqual(proof['profile_reused'], resume)
            value.inventory.assert_not_called()
            value.sql.assert_called_once()

    def test_initialized_empty_profile_resume_keeps_profile_and_queries_high_water(self):
        value = self.instance(resume=True)
        before = {p.relative_to(value.profile).as_posix(): p.read_bytes()
            for p in value.profile.rglob('*') if p.is_file()}
        proof = self.initialize_gate(value)
        after = {p.relative_to(value.profile).as_posix(): p.read_bytes()
            for p in value.profile.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(proof['operation'], 'resume_first_creation')
        self.assertEqual(proof['supported_first_character_id'], 1)
        self.assertEqual(len(value.sql.call_args_list), 2)
        self.assertIn('coh_container_high_water', value.sql.call_args_list[-1].args[0])

    def test_reopen_empty_profile_is_actionable_before_wine(self):
        for presence in ('missing', 'present'):
            value = self.instance(reopen=True, inventory=[], presence=presence)
            with self.subTest(presence=presence), self.assertRaisesRegex(server.base.DiagnosticError, 'Resume first character creation'):
                self.initialize_gate(value)
            self.assertFalse(value.creation_report['profile_eligibility']['eligible'])
            value.ctx.start.assert_not_called()

    def test_resume_missing_uninitialized_or_linked_profile_never_initializes(self):
        for invalid in ('absent', 'uninitialized', 'linked'):
            value = self.instance(resume=True, profile=invalid != 'absent')
            if invalid == 'uninitialized':
                (value.profile/'profile.json').write_text(json.dumps(dict(server.login.PROFILE_IDENTITY, initialized=False)))
            elif invalid == 'linked':
                path = value.profile.with_name('preserved-profile'); value.profile.rename(path)
                value.profile.symlink_to(path, target_is_directory=True)
            with self.subTest(invalid=invalid), patch.object(server.login.LocalLoginServer, 'initialize') as native:
                with self.assertRaises(server.base.DiagnosticError): value.initialize()
                native.assert_not_called()

    def test_fresh_creation_cannot_reuse_existing_profile(self):
        value = self.instance()
        with patch.object(server.login.LocalLoginServer, 'initialize') as native:
            with self.assertRaisesRegex(server.base.DiagnosticError, 'Resume first character creation'): value.initialize()
            native.assert_not_called()

    def test_creation_refuses_every_existing_character_before_wine(self):
        _, saved, _ = saved_fixture()
        for inventory in (saved, [dict(saved[0], containerid=2, name='OTHER')], saved + [dict(saved[0], containerid=2, name='OTHER')]):
            value = self.instance(resume=True, inventory=inventory)
            with self.subTest(inventory=inventory), self.assertRaisesRegex(server.base.DiagnosticError, 'completely empty inventory'):
                self.initialize_gate(value)
            self.assertFalse(value.creation_report['profile_eligibility']['eligible'])
            value.ctx.start.assert_not_called()

    def test_empty_advanced_allocator_is_refused_without_rewind(self):
        value = self.instance(resume=True)
        value.sql.side_effect = lambda text, **_: 'present' if 'to_regclass' in text else '1'
        with self.assertRaisesRegex(server.base.DiagnosticError, 'already allocated character IDs'):
            self.initialize_gate(value)
        self.assertFalse(value.creation_report['profile_eligibility']['eligible'])
        self.assertFalse(any('setval' in call.args[0] or 'reserve_id' in call.args[0] for call in value.sql.call_args_list))

    def test_reopen_requires_exact_identity_and_complete_committed_rows(self):
        proof = self.initialize_gate(self.instance(reopen=True))
        self.assertTrue(proof['committed_character_rows_verified'])
        for change in ('name', 'id', 'null_auth', 'duplicate', 'second_local', 'login', 'power', 'class'):
            value = self.instance(reopen=True)
            inventory = value.inventory.return_value
            if change == 'name': inventory[0]['name'] = 'OTHER'
            if change == 'id': inventory[0]['containerid'] = 2
            if change == 'null_auth': inventory[0]['authid'] = None
            if change == 'duplicate': inventory.append(copy.deepcopy(inventory[0]))
            if change == 'second_local': inventory.append(dict(inventory[0], containerid=2, name='OTHER'))
            if change == 'login': value.character_rows.return_value['ents'][0]['logincount'] = 0
            if change == 'power': value.character_rows.return_value['powers'] = []
            if change == 'class': value.character_rows.return_value['ents'][0]['class'] = None
            with self.subTest(change=change), self.assertRaises(server.base.DiagnosticError): self.initialize_gate(value)
            self.assertFalse(value.creation_report['profile_eligibility']['eligible'])
            value.ctx.start.assert_not_called()

    def unentered(self, *, reopen=False, rows=None, counts=None, high_water='1', inventory=None, fail_removal=False):
        """The SQL a failed first zone leaves (Thor 0.13.60); the removal statement empties it."""
        value = self.instance(reopen=reopen, resume=not reopen)
        state = {'removed': False, 'statements': []}
        current = [dict(UNENTERED_IDENTITY)] if inventory is None else inventory
        counts = {'ents': 1, 'ents2': 1, 'powers': 0, 'costumeparts': 0, 'badges': 0} if counts is None else counts
        value.inventory = Mock(side_effect=lambda: [] if state['removed'] else copy.deepcopy(current))
        value.character_rows = Mock(return_value=unentered_rows() if rows is None else rows)
        records = {'ents': [{key: UNENTERED_ENTS[key] for key in server.UNENTERED_RECORD_FIELDS['ents']}],
                   'ents2': [{key: UNENTERED_ENTS2[key] for key in server.UNENTERED_RECORD_FIELDS['ents2']}]}
        def sql(text, **_kwargs):
            state['statements'].append(text)
            if text.startswith('DO $$'):
                if fail_removal:
                    raise server.base.DiagnosticError('sql-fixture failed: ERROR:  The unfinished character rows changed')
                state['removed'], output = True, 'DO'
            elif 'to_regclass' in text:
                output = 'present'
            elif 'coh_container_high_water' in text:
                output = '0' if state['removed'] else high_water
            elif 'json_object_agg' in text:
                output = json.dumps(counts)
            else:
                table = 'ents2' if 'FROM dbo.ents2 WHERE' in text else 'ents' if 'FROM dbo.ents WHERE' in text else None
                if table is None or 'staticmapid' not in text and 'influencetype' not in text:
                    raise AssertionError('Unexpected SQL: ' + text[:200])
                output = json.dumps(records[table])
            value.ctx.children.append(SimpleNamespace(text=lambda output=output: output))
            return output
        value.sql = Mock(side_effect=sql)
        return value, state

    def initialize_removal(self, value):
        reused = value.profile.exists()
        def initialized(current):
            current.report['profile_reused'] = reused
        with patch.object(server.login.LocalLoginServer, 'initialize', autospec=True, side_effect=initialized):
            value.initialize()
        value.ctx.start.assert_not_called()
        return value.creation_report['profile_eligibility']

    def test_resume_removes_a_thorhero_that_never_entered_the_game(self):
        value, state = self.unentered()
        proof = self.initialize_removal(value)
        self.assertTrue(proof['eligible']); self.assertTrue(proof['sql_game_mutations_performed'])
        self.assertTrue(proof['empty_inventory_verified']); self.assertEqual(proof['character_count'], 0)
        self.assertEqual((proof['character_id_high_water'], proof['supported_first_character_id']), (0, 1))
        record = proof['unentered_character']
        self.assertIs(record['removed'], True)
        self.assertEqual(record['identity'], UNENTERED_IDENTITY)
        self.assertEqual(record['row_counts'], {'ents': 1, 'ents2': 1})
        self.assertEqual((record['tables_checked'], record['start_map_id']), (5, 71))
        self.assertEqual((record['character_id_high_water'], record['character_id_high_water_after']), (1, 0))
        self.assertEqual(record['rows']['ents2'][0]['influencetype'], 1)
        self.assertIs(value.ctx.report['character_profile_eligibility'], proof)
        removal = [text for text in state['statements'] if not text.startswith('SELECT ')]
        self.assertEqual(len(removal), 1)
        statement = removal[0]
        self.assertTrue(statement.startswith('DO $$') and statement.endswith('END$$;'))
        for clause in ('DELETE FROM dbo.ents2 WHERE containerid=1 AND subid=0 AND curbuild IS NULL',
                       # 0.13.62: the player-chosen name enters SQL only as its digest.
                       "DELETE FROM dbo.ents WHERE containerid=1 AND md5(name)='"
                       + hashlib.md5(b'THORHERO').hexdigest() + "' AND authname='COHLOCAL' "
                       'AND authid=1353310574 AND class IS NULL', 'logincount IS NULL',
                       'OR EXISTS (SELECT 1 FROM dbo.ents) OR EXISTS (SELECT 1 FROM dbo.badges WHERE containerid=1)',
                       "setval(pg_get_serial_sequence('dbo.ents', 'containerid'), 1, false)"):
            self.assertIn(clause, statement)
        # Every check comes before the non-transactional setval.
        self.assertLess(statement.index("RAISE EXCEPTION 'The unfinished"), statement.index('setval'))
        self.assertIn('never entered the game', value.ctx.event.call_args.kwargs['message'])

    def test_resume_never_removes_a_character_that_entered_the_game_or_any_other(self):
        def power(rows, _counts): rows['powers'].append(dict(saved_fixture()[0]['powers'][0]))
        def costume(rows, _counts): rows['costumeparts'].append(dict(saved_fixture()[0]['costumeparts'][0]))
        changes = {
            'login': lambda rows, _: rows['ents'][0].update(logincount=1),
            'class': lambda rows, _: rows['ents'][0].update({'class': 3}),
            'origin': lambda rows, _: rows['ents'][0].update(origin=2),
            'level': lambda rows, _: rows['ents'][0].update(level=0),
            'created': lambda rows, _: rows['ents'][0].update(datecreated='2026-11-08'),
            'power': power, 'costume': costume,
            'build': lambda rows, _: rows['ents2'][0].update(originalprimary=7),
            'second_build': lambda rows, _: rows['ents2'].append(dict(rows['ents2'][0], subid=1)),
            'badge': lambda _, counts: counts.update(badges=1),
            'counted_ents2': lambda _, counts: counts.update(ents2=2),
        }
        for name, change in changes.items():
            rows, counts = unentered_rows(), {'ents': 1, 'ents2': 1, 'powers': 0, 'costumeparts': 0, 'badges': 0}
            change(rows, counts)
            value, state = self.unentered(rows=rows, counts=counts)
            with self.subTest(change=name), self.assertRaisesRegex(server.base.DiagnosticError, 'completely empty inventory'):
                self.initialize_removal(value)
            self.assertFalse(any(text.startswith('DO $$') for text in state['statements']))
            proof = value.creation_report['profile_eligibility']
            self.assertFalse(proof['sql_game_mutations_performed']); self.assertNotIn('unentered_character', proof)
        for name, inventory, high_water in (
                ('allocated_twice', None, '2'),
                ('other_name', [dict(UNENTERED_IDENTITY, name='OTHER')], '1'),
                ('other_account', [dict(UNENTERED_IDENTITY, authname='SOMEONE')], '1'),
                ('other_id', [dict(UNENTERED_IDENTITY, containerid=2)], '1'),
                ('two', [dict(UNENTERED_IDENTITY), dict(UNENTERED_IDENTITY, containerid=2, name='OTHER')], '1')):
            value, state = self.unentered(inventory=inventory, high_water=high_water)
            with self.subTest(inventory=name), self.assertRaisesRegex(server.base.DiagnosticError, 'completely empty inventory'):
                self.initialize_removal(value)
            self.assertFalse(any(text.startswith('DO $$') for text in state['statements']))

    def test_any_name_the_game_accepts_reopens_and_binds_the_session(self):
        # 0.13.62 (owner, 2026-11-08): the saved character may have any name;
        # Thor 0.13.61 created the villain Ralakar.
        for name in ('Ralakar', "Dr. O'Malley", 'Wolf-Spider X'):
            value = self.instance(reopen=True)
            value.inventory.return_value[0]['name'] = name
            value.character_rows.return_value['ents'][0]['name'] = name
            with self.subTest(name=name):
                proof = self.initialize_gate(value)
                self.assertTrue(proof['eligible'] and proof['committed_character_rows_verified'])
                self.assertEqual((proof['character_name'], server.CHARACTER, server.CHARACTER_BOUND), (name, name, True))
                self.assertEqual(value.creation_report['name'], name)
                self.assertIsNone(value.immediate_event_contract())   # THORHERO-only native producer
        # A name the game cannot have, or one the rows do not share, is refused.
        for inventory, rows in (('Two  Spaces', 'Two  Spaces'), ('x' * 21, 'x' * 21), ('Ralakar', 'THORHERO')):
            value = self.instance(reopen=True)
            value.inventory.return_value[0]['name'] = inventory
            value.character_rows.return_value['ents'][0]['name'] = rows
            with self.subTest(refused=inventory), self.assertRaises(server.base.DiagnosticError):
                self.initialize_gate(value)
            self.assertFalse(value.creation_report['profile_eligibility']['eligible'])

    def test_resume_removes_an_unfinished_character_of_any_name(self):
        for name in ('Ralakar', "Dr. O'Malley"):
            rows = unentered_rows(); rows['ents'][0]['name'] = name
            value, state = self.unentered(rows=rows, inventory=[dict(UNENTERED_IDENTITY, name=name)])
            with self.subTest(name=name):
                proof = self.initialize_removal(value)
                self.assertIs(proof['unentered_character']['removed'], True)
                self.assertEqual(proof['unentered_character']['identity']['name'], name)
                statement = [text for text in state['statements'] if text.startswith('DO $$')][0]
                # The player's name enters SQL only as its digest (an apostrophe stays harmless).
                self.assertIn("md5(name)='" + hashlib.md5(name.encode()).hexdigest() + "'", statement)
                self.assertNotIn(name, statement)
                self.assertIn('unfinished ' + name, value.ctx.event.call_args.kwargs['message'])
                # Removing it binds nothing: the new character's name comes from the creator.
                self.assertFalse(server.CHARACTER_BOUND)

    def test_reopen_explains_a_thorhero_that_never_entered_the_game_and_changes_nothing(self):
        value, state = self.unentered(reopen=True)
        with self.assertRaisesRegex(server.base.DiagnosticError,
                                    r'never entered the game.*Use Resume first character creation'):
            self.initialize_removal(value)
        self.assertTrue(all(text.startswith('SELECT ') for text in state['statements']))
        rows = unentered_rows(); rows['ents'][0]['class'] = 3
        value, state = self.unentered(reopen=True, rows=rows)
        with self.assertRaisesRegex(server.base.DiagnosticError, 'no committed login baseline'):
            self.initialize_removal(value)
        self.assertFalse(any('json_object_agg' in text for text in state['statements']))

    def test_a_failed_removal_says_nothing_was_changed(self):
        value, _ = self.unentered(fail_removal=True)
        with self.assertRaisesRegex(server.base.DiagnosticError, 'could not be removed and nothing was changed'):
            self.initialize_removal(value)
        proof = value.creation_report['profile_eligibility']
        self.assertFalse(proof['eligible']); self.assertIs(proof['unentered_character']['removed'], False)

    def test_ents_tables_follow_the_accepted_template_and_its_schema(self):
        sys.path.insert(0, str(ROOT/'database/postgresql/tests'))
        import run_generated_schema as schema
        with zipfile.ZipFile(ROOT/'docs/schema-generation-evidence/accepted-36088012666.zip') as outer:
            with zipfile.ZipFile(io.BytesIO(outer.read('schema-evidence/schema-outputs.zip'))) as inner:
                text = inner.read('data/server/db/templates/ents.template').decode()
        tables = schema.template_columns(text, 'ents')
        family = server.ents_family_tables(text, tables)
        self.assertEqual((family[0], len(family), set(family)), ('ents', 48, set(tables)))
        self.assertEqual(server.ents_family_tables(TEMPLATE, expected_tables()),
                         ('ents', 'badges', 'costumeparts', 'ents2', 'powers'))
        missing = dict(tables); missing.pop('badges')
        for broken_text, broken_tables in ((text.replace('Powers[', 'Power['), tables), (text, missing),
                                           (text, dict(tables, ents=['active'] + tables['ents']))):
            with self.subTest(), self.assertRaisesRegex(server.base.DiagnosticError, 'Ents template tables differ'):
                server.ents_family_tables(broken_text, broken_tables)

    def test_resume_flag_cannot_enter_reopen(self):
        value = self.instance(reopen=True, resume=True)
        with patch.object(server.login.LocalLoginServer, 'initialize') as native:
            with self.assertRaisesRegex(server.base.DiagnosticError, 'separate from saved-character reopen'): value.initialize()
            native.assert_not_called()

    def test_post_dbserver_creation_rechecks_all_inventory_and_allocator(self):
        value = self.instance(resume=True)
        self.initialize_gate(value)
        value.inventory.return_value = [dict(saved_fixture()[1][0], containerid=2, name='OTHER')]
        with self.assertRaisesRegex(server.base.DiagnosticError, 'every existing character was preserved'): value.capture_baseline()
        value.inventory.return_value = []
        value.sql.side_effect = lambda *_args, **_kwargs: '1'
        with self.assertRaisesRegex(server.base.DiagnosticError, 'IDs changed before creation'): value.capture_baseline()

    def test_creator_parser_flag_is_explicit_and_reopen_rejects_it(self):
        common = ['--profile', server.PROFILE, '--session-id', '1'*32]
        self.assertFalse(creation.parse_arguments(common, 'actual_character_creation').resume_empty_profile)
        self.assertTrue(creation.parse_arguments(common + ['--resume-empty-profile'], 'actual_character_creation').resume_empty_profile)
        for mode in ('actual_character_reopen', 'actual_character_startup_timing'):
            with self.subTest(mode=mode), patch('sys.stderr', new=io.StringIO()), self.assertRaises(SystemExit):
                creation.parse_arguments(common + ['--resume-empty-profile'], mode)

    def test_failed_initialize_announces_session_before_cleanup_and_retains_failed_report(self):
        for mode in ('actual_character_creation', 'actual_character_reopen'):
            with self.subTest(mode=mode):
                path = Path(self.enterContext(tempfile.TemporaryDirectory(prefix='coh-failed-session-')))
                ordering, events, reports = [], [], []
                class FailedDiagnostic:
                    REPORT_KEY = 'character_creation' if mode == 'actual_character_creation' else 'character_reopen'
                    proof_verified = staticmethod(lambda *_: False)
                    def __init__(self, args, context):
                        self.ctx = context; self.wine_started = False; self.capture_dir = path
                        self.cleanup_status = dict.fromkeys(('postgres_graceful', 'wine_prefix_stopped', 'owned_processes_reaped'), True)
                        self.local_server = SimpleNamespace(collect=lambda *_: ordering.append('collect'))
                    def initialize(self):
                        ordering.append('initialize')
                        raise server.base.DiagnosticError('No saved THORHERO exists; preserved profile')
                    def execute(self): self.initialize()
                    def cleanup(self): ordering.append('cleanup'); return []
                def event(context, kind, **fields):
                    ordering.append(kind); events.append(dict(type=kind, **fields))
                def persist(args, context, *_args, **_kwargs):
                    ordering.append('persist'); reports.append(copy.deepcopy(context.report))
                args = ['--profile', server.PROFILE, '--session-id', '1'*32, '--state', str(path),
                    '--assets', str(path/'assets'), '--socket-dir', str(path/'socket'), '--game-data', str(path/'data')]
                with patch.object(creation.CharacterContext, 'event', autospec=True, side_effect=event), \
                        patch.object(creation.interactive, 'persist_report', side_effect=persist), \
                        patch.object(creation.signal, 'signal'):
                    self.assertEqual(creation.run(args, FailedDiagnostic, mode + '_guest', mode), 1)
                failure = next(value for value in events if value['type'] == 'character_session_failed')
                self.assertEqual(failure['session_id'], '1'*32)
                self.assertEqual(failure['status'], 'failed'); self.assertIs(failure['passed'], False)
                self.assertEqual(failure['failures'], ['No saved THORHERO exists; preserved profile'])
                self.assertLess(ordering.index('character_session_failed'), ordering.index('cleanup'))
                self.assertLess(ordering.index('cleanup'), ordering.index('persist'))
                self.assertLess(ordering.index('persist'), ordering.index('result'))
                self.assertFalse(reports[0]['passed']); self.assertEqual(reports[0]['status'], 'failed')
                self.assertTrue(reports[0]['cleanup_complete'])
                self.assertEqual(events[-1]['session_id'], '1'*32)


@unittest.skipUnless(REQUIRE_POSTGRESQL, 'Real PostgreSQL fixtures require COH_REQUIRE_POSTGRESQL=1')
class PostgreSQLEligibilityTests(unittest.TestCase):
    """Actual production SELECTs, JSON typing, and retained allocator migration.

    CI requires these fixtures explicitly. Local unit-only runs leave the
    fixture inventory empty; the release qualifier refuses that as evidence.
    """
    instance = EligibilityTests.instance
    initialize_gate = EligibilityTests.initialize_gate
    initialize_removal = EligibilityTests.initialize_removal
    tearDown = EligibilityTests.tearDown
    @classmethod
    def setUpClass(cls):
        if os.environ.get('PGHOST') not in ('127.0.0.1', 'localhost') or os.environ.get('PGDATABASE') != 'coh_test_startup_bundle':
            raise RuntimeError('Profile eligibility requires explicit localhost/coh_test_startup_bundle fixture')
        cls.psql = shutil.which('psql')
        if not cls.psql or cls.database_sql('SELECT current_database();') != 'coh_test_startup_bundle':
            raise RuntimeError('Required profile eligibility PostgreSQL fixture is unavailable')

    @classmethod
    def database_sql(cls, text):
        result = subprocess.run([cls.psql, '-X', '-qAt', '-v', 'ON_ERROR_STOP=1', '-c', text],
            capture_output=True, text=True, timeout=20)
        if result.returncode:
            raise RuntimeError(result.stderr[:2048])
        return result.stdout.strip()

    def actual(self, *, reopen=False, missing=False, inventory=None, provisional=False, missing_powers=False, advanced=False,
               unentered=False, badge=False):
        value = self.instance(reopen=reopen, resume=not reopen, inventory=inventory)
        # These tables live solely in the explicitly guarded disposable fixture.
        self.database_sql((ROOT/'database/postgresql/001-coh-compat.sql').read_text())
        self.database_sql('DROP TABLE IF EXISTS ' + ', '.join('dbo.' + table for table in value.schema['expected_tables'])
                          + ' CASCADE;')
        if not missing:
            text_fields = {'authname', 'name', 'description', 'motto', 'datecreated'}
            for table, fields in value.schema['expected_tables'].items():
                columns = [name + (' SERIAL PRIMARY KEY' if table == 'ents' and name == 'containerid'
                    else ' text' if table == 'ents' and name in text_fields else ' integer') for name in fields]
                self.database_sql('CREATE TABLE dbo.' + table + ' (' + ','.join(columns) + ');')
            rows, saved, _ = saved_fixture()
            selected = inventory if inventory is not None else saved if reopen else []
            for identity in selected:
                record = copy.deepcopy(rows['ents'][0]); record.update(identity)
                if provisional: record['logincount'] = None
                raw = json.dumps(record).replace("'", "''")
                self.database_sql("INSERT INTO dbo.ents SELECT * FROM json_populate_record(NULL::dbo.ents, '" + raw + "'::json);")
            if selected and not provisional:
                for table in ('ents2', 'powers', 'costumeparts'):
                    if table == 'powers' and missing_powers: continue
                    raw = json.dumps(rows[table][0]).replace("'", "''")
                    self.database_sql('INSERT INTO dbo.' + table + ' SELECT * FROM json_populate_record(NULL::dbo.' + table + ", '" + raw + "'::json);")
            if advanced:
                self.database_sql("SELECT dbo.coh_reserve_id('dbo.ents'::regclass, 1);")
            if unentered:
                # The DbServer's own writes for a created character whose first
                # zone then failed: COH_PG_INSERT_CONTAINER, then its fields.
                self.database_sql("SELECT dbo.coh_reserve_id('dbo.ents'::regclass, 1);")
                self.database_sql('INSERT INTO dbo.ents (containerid) VALUES (1);')
                self.database_sql('UPDATE dbo.ents SET ' + ', '.join(key + '=' + (str(field) if type(field) is int else "'" + field + "'")
                                  for key, field in UNENTERED_ENTS.items() if key != 'containerid') + ' WHERE containerid=1;')
                self.database_sql('INSERT INTO dbo.ents2 (' + ','.join(UNENTERED_ENTS2) + ') VALUES ('
                                  + ','.join(str(field) for field in UNENTERED_ENTS2.values()) + ');')
            if badge:
                self.database_sql('INSERT INTO dbo.badges (containerid, subid, badge) VALUES (1, 0, 5);')
        def production_sql(text, **_kwargs):
            # The guest's own psql invocation: no -q, so a DO statement prints its tag.
            result = subprocess.run([self.psql, '-X', '-w', '-A', '-t', '-v', 'ON_ERROR_STOP=1'], input=text,
                capture_output=True, text=True, timeout=20)
            if result.returncode:
                raise server.base.DiagnosticError('sql-fixture failed: ' + (result.stdout + result.stderr)[-4096:])
            output = result.stdout.strip()
            value.ctx.children.append(SimpleNamespace(text=lambda: output))
            return output
        value.sql = Mock(side_effect=production_sql)
        value.inventory = server.LocalCharacterServer.inventory.__get__(value)
        value.character_rows = server.LocalCharacterServer.character_rows.__get__(value)
        return value

    def snapshot(self):
        presence = self.database_sql("SELECT to_regclass('dbo.ents') IS NOT NULL;")
        if presence == 'f': return ('missing',)
        return (self.database_sql('SELECT coalesce(json_agg(x ORDER BY containerid),\'[]\'::json) FROM dbo.ents x;'),
            self.database_sql('SELECT last_value || \':\' || is_called FROM dbo.ents_containerid_seq;'))

    def real_case(self, name, *, allowed=False, post_race=None, **options):
        value = self.actual(**options)
        before = self.snapshot()
        if allowed:
            self.assertTrue(self.initialize_gate(value)['eligible'])
        else:
            with self.assertRaises(server.base.DiagnosticError): self.initialize_gate(value)
            value.ctx.start.assert_not_called()
        self.assertEqual(before, self.snapshot(), 'Eligibility mutated persistent rows or allocator')
        if post_race:
            if post_race == 'character':
                self.database_sql("INSERT INTO dbo.ents(containerid,authid,authname,name) VALUES(2,77,'COHLOCAL','OTHER');")
            else:
                self.database_sql("SELECT dbo.coh_reserve_id('dbo.ents'::regclass, 1);")
            before = self.snapshot()
            with self.assertRaises(server.base.DiagnosticError): value.capture_baseline()
            self.assertEqual(before, self.snapshot())
        POSTGRES_FIXTURES_RUN.add(name)

    def test_pg_missing_inventory_creation(self): self.real_case('missing_inventory_creation', allowed=True, missing=True)
    def test_pg_missing_inventory_reopen(self): self.real_case('missing_inventory_reopen', reopen=True, missing=True)
    def test_pg_empty_inventory_resume(self): self.real_case('empty_inventory_resume', allowed=True)
    def test_pg_empty_inventory_reopen(self): self.real_case('empty_inventory_reopen', reopen=True, inventory=[])
    def test_pg_saved_character_reopen(self): self.real_case('saved_character_reopen', allowed=True, reopen=True)
    def test_pg_saved_character_resume_refused(self): self.real_case('saved_character_resume_refused', inventory=saved_fixture()[1])
    def test_pg_foreign_character_resume_refused(self): self.real_case('foreign_character_resume_refused', inventory=[dict(saved_fixture()[1][0], containerid=2, name='OTHER')])
    def test_pg_foreign_character_reopen_refused(self): self.real_case('foreign_character_reopen_refused', reopen=True, inventory=[dict(saved_fixture()[1][0], containerid=2, name='OTHER')])
    def test_pg_ambiguous_character_reopen_refused(self): self.real_case('ambiguous_character_reopen_refused', reopen=True, inventory=saved_fixture()[1] + [dict(saved_fixture()[1][0], containerid=2)])
    def test_pg_provisional_character_reopen_refused(self): self.real_case('provisional_character_reopen_refused', reopen=True, provisional=True)
    def test_pg_missing_power_rows_reopen_refused(self): self.real_case('missing_power_rows_reopen_refused', reopen=True, missing_powers=True)
    def test_pg_advanced_empty_allocator_resume_refused(self): self.real_case('advanced_empty_allocator_resume_refused', advanced=True)
    def test_pg_post_dbserver_character_race_refused(self): self.real_case('post_dbserver_character_race_refused', allowed=True, post_race='character')
    def test_pg_post_dbserver_allocator_race_refused(self): self.real_case('post_dbserver_allocator_race_refused', allowed=True, post_race='allocator')

    def test_pg_unentered_character_resume_removed(self):
        value = self.actual(unentered=True)
        self.assertEqual(self.snapshot()[1], '1:true')
        self.assertEqual(self.database_sql("SELECT dbo.coh_container_high_water('dbo.ents'::regclass);"), '1')
        proof = self.initialize_removal(value)
        self.assertTrue(proof['eligible']); self.assertIs(proof['unentered_character']['removed'], True)
        self.assertEqual(proof['unentered_character']['rows']['ents'][0]['staticmapid'], 71)
        self.assertEqual(self.snapshot(), ('[]', '1:false'))
        self.assertEqual(self.database_sql('SELECT count(*) FROM dbo.ents2;'), '0')
        value.capture_baseline()  # the post-DbServer recheck accepts the emptied profile
        # The DbServer's next character (COH_PG_HIGH_WATER + 1, COH_PG_INSERT_CONTAINER) is ID 1 again.
        self.assertEqual(self.database_sql("SELECT dbo.coh_container_high_water('dbo.ents'::regclass) + 1;"), '1')
        self.assertEqual(self.database_sql("SELECT dbo.coh_reserve_id('dbo.ents'::regclass, 1);"), '1')
        self.database_sql('INSERT INTO dbo.ents (containerid) VALUES (1);')
        POSTGRES_FIXTURES_RUN.add('unentered_character_resume_removed')

    def test_pg_named_character_reopen(self):
        # 0.13.62: a saved character with the player's own name (an apostrophe included).
        self.real_case('named_character_reopen', allowed=True, reopen=True,
                       inventory=[dict(saved_fixture()[1][0], name="Dr. O'Malley")])
        self.assertEqual(server.CHARACTER, "Dr. O'Malley")

    def test_pg_unentered_named_character_resume_removed(self):
        value = self.actual(unentered=True)
        self.database_sql("UPDATE dbo.ents SET name='Dr. O''Malley' WHERE containerid=1;")
        proof = self.initialize_removal(value)
        self.assertTrue(proof['eligible']); self.assertIs(proof['unentered_character']['removed'], True)
        self.assertEqual(proof['unentered_character']['identity']['name'], "Dr. O'Malley")
        self.assertEqual(self.snapshot(), ('[]', '1:false'))
        self.assertEqual(self.database_sql('SELECT count(*) FROM dbo.ents2;'), '0')
        POSTGRES_FIXTURES_RUN.add('unentered_named_character_resume_removed')

    def test_pg_unentered_character_reopen_explained(self):
        value = self.actual(reopen=True, unentered=True, inventory=[])
        before = self.snapshot()
        with self.assertRaisesRegex(server.base.DiagnosticError, 'never entered the game'):
            self.initialize_removal(value)
        self.assertEqual(before, self.snapshot())
        POSTGRES_FIXTURES_RUN.add('unentered_character_reopen_explained')

    def test_pg_unentered_character_with_badge_refused(self):
        value = self.actual(unentered=True, badge=True)
        before = self.snapshot()
        with self.assertRaisesRegex(server.base.DiagnosticError, 'completely empty inventory'):
            self.initialize_removal(value)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(self.database_sql('SELECT count(*) FROM dbo.badges;'), '1')
        POSTGRES_FIXTURES_RUN.add('unentered_character_with_badge_refused')


if __name__ == '__main__': unittest.main()
