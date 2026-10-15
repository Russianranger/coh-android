"""Pre-Wine profile eligibility, real SQL, and non-destructive first-create resume."""
import copy
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
}


def saved_fixture():
    rows, _, attributes = fixture()
    for values in rows.values():
        for row in values:
            row['containerid'] = 1
    inventory = [{key: rows['ents'][0][key] for key in server.evidence.IDENTITY_FIELDS}]
    return rows, inventory, attributes


class EligibilityTests(unittest.TestCase):
    def instance(self, *, reopen=False, resume=False, profile=True, presence='present', inventory=None):
        state = Path(self.enterContext(tempfile.TemporaryDirectory(prefix='coh-profile-gate-')))
        owner = SimpleNamespace(ctx=SimpleNamespace(report={}, children=[], start=Mock()), root=state,
            args=SimpleNamespace(session_id='1'*32, state=state, resume_empty_profile=resume))
        value = (server.LocalCharacterReopenServer if reopen else server.LocalCharacterServer)(owner)
        rows, saved, attributes = saved_fixture()
        value.schema = {'expected_attributes': attributes,
            'expected_tables': {table: list(fields) + (['logincount'] if table == 'ents' else [])
                for table, fields in server.evidence.SELECTED.items()}}
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

    def actual(self, *, reopen=False, missing=False, inventory=None, provisional=False, missing_powers=False, advanced=False):
        value = self.instance(reopen=reopen, resume=not reopen, inventory=inventory)
        # These tables live solely in the explicitly guarded disposable fixture.
        self.database_sql((ROOT/'database/postgresql/001-coh-compat.sql').read_text())
        self.database_sql('DROP TABLE IF EXISTS dbo.costumeparts, dbo.powers, dbo.ents2, dbo.ents CASCADE;')
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
        def production_sql(text, **_kwargs):
            output = self.database_sql(text)
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


if __name__ == '__main__': unittest.main()
