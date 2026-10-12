"""Real PostgreSQL saved-destination selection, without native/gameplay claims.

Only the guarded disposable host fixture is accepted. Each case owns a fresh
schema, and production SQL runs inside BEGIN READ ONLY. The only SQL adaptation
is replacing the literal dbo schema qualifier with that fresh fixture schema.
Neither player databases nor the shared dbo fixture tables are modified.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'android/guest'), str(Path(__file__).parent)]
import character_zoning as zoning
import analyze_enhancement_persistence as enhancements
from test_character_server import fixture

REQUIRE_POSTGRESQL = os.environ.get('COH_REQUIRE_SAVED_MAP_PG') == '1'
POSTGRES_FIXTURES_RUN = set()
REQUIRED_POSTGRES_FIXTURES = {
    'kings_unassigned', 'kings_assigned', 'atlas_unassigned', 'atlas_assigned',
    'atlas_instance_unassigned', 'atlas_instance_assigned', 'repeated_kings_selection',
    'unsupported_saved_destination', 'inconsistent_active_map', 'foreign_name',
    'foreign_account', 'account_identity_mismatch', 'missing_power_rows',
    'missing_costume_rows', 'missing_native_kings_qualification',
    'nonfinite_saved_position', 'read_only_transaction_enforced',
}
SCOPE = 'actual_postgresql_readonly_saved_map_selection'


def fixture_connection_guard(environment):
    if (environment.get('PGHOST') not in ('127.0.0.1', 'localhost')
            or environment.get('PGDATABASE') != 'coh_test_startup_bundle'):
        raise RuntimeError('Saved-map tests require explicit localhost/coh_test_startup_bundle fixture')


def sql_literal(value):
    """Fixture seeding only; production SQL never calls this function."""
    if value is None:
        return 'NULL'
    if type(value) is str:
        return "'" + value.replace("'", "''") + "'"
    if type(value) in (int, float):
        return str(value)
    raise TypeError('Unsupported fixture scalar')


class GuardTests(unittest.TestCase):
    def test_guard_refuses_remote_or_nonfixture_database_before_sql(self):
        fixture_connection_guard({'PGHOST': '127.0.0.1', 'PGDATABASE': 'coh_test_startup_bundle'})
        for host, database in (('192.0.2.1', 'coh_test_startup_bundle'),
                ('127.0.0.1', 'coh_local'), ('', 'coh_test_startup_bundle')):
            with self.subTest(host=host, database=database), self.assertRaises(RuntimeError):
                fixture_connection_guard({'PGHOST': host, 'PGDATABASE': database})

    def test_every_required_fixture_has_one_real_test(self):
        cases = {name.removeprefix('test_pg_') for name in
            unittest.defaultTestLoader.getTestCaseNames(SavedMapPostgreSQLTests)}
        self.assertEqual(cases, REQUIRED_POSTGRES_FIXTURES)
        self.assertEqual(len(cases), 17)

    def test_artifact_validator_rejects_missing_sql_and_fabricated_native_claims(self):
        # Synthetic artifact schema fixture only. It is never written as real
        # execution evidence; the real inventory still requires executed cases.
        with patch.dict(globals(), REQUIRE_POSTGRESQL=True), \
                patch.object(sys.modules[__name__], 'POSTGRES_FIXTURES_RUN',
                    set(REQUIRED_POSTGRES_FIXTURES)):
            proof = qualification_inventory()
        self.assertIs(validate_qualification_inventory(proof), proof)
        for field, wrong in (('format', True), ('fixtures', []),
                ('native_process_booted', True), ('native_client_connected', True),
                ('native_save_logout_executed', True), ('physical_ayn_thor_validated', True),
                ('boost_fields', []), ('shipping_enhancement_capture_changed', True)):
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                validate_qualification_inventory(dict(proof, **{field: wrong}))
        with self.assertRaises(RuntimeError):
            validate_qualification_inventory({key: value for key, value in proof.items()
                if key != 'generated_boost_template_sha256'})


@unittest.skipUnless(REQUIRE_POSTGRESQL, 'Actual SQL fixture requires COH_REQUIRE_SAVED_MAP_PG=1')
class SavedMapPostgreSQLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_connection_guard(os.environ)
        cls.psql = shutil.which('psql')
        if not cls.psql:
            raise RuntimeError('Required saved-map PostgreSQL fixture executable is unavailable')
        identity = cls.database_sql("SELECT current_database() || '|' || "
            "(current_setting('server_version_num')::integer / 10000)::text;")
        if identity != 'coh_test_startup_bundle|16':
            raise RuntimeError('Saved-map PostgreSQL 16 fixture identity differs')

    @classmethod
    def database_sql(cls, text):
        result = subprocess.run([cls.psql, '-X', '-qAt', '-v', 'ON_ERROR_STOP=1'],
            input=text, capture_output=True, text=True, timeout=20)
        if result.returncode:
            raise RuntimeError(result.stderr[:2048])
        return result.stdout.strip()

    def setUp(self):
        # Exactly this random, invocation-owned schema may be created/deleted.
        # It is independent of every existing PostgreSQL release fixture.
        self.namespace = 'coh_saved_map_' + secrets.token_hex(8)
        if not re.fullmatch(r'coh_saved_map_[0-9a-f]{16}', self.namespace):
            raise RuntimeError('Invalid fixture ownership')
        self.database_sql('CREATE SCHEMA ' + self.namespace + ';')
        self.addCleanup(self.database_sql, 'DROP SCHEMA ' + self.namespace + ' CASCADE;')
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix='coh-saved-map-pg-')))
        self.sql_calls = []

    def seed(self, *, map_id=5, active_map=None, qualified=True, changes=None,
             missing_table=None, account_authid=77):
        rows, _, attributes = fixture()
        for values in rows.values():
            for row in values:
                row['containerid'] = 1
        rows['ents'][0].update(staticmapid=map_id, mapid=active_map,
            posx=321.125, posy=-48.5, posz=97.875)
        if changes:
            rows['ents'][0].update(changes)
        text_fields = {'authname', 'name', 'description', 'motto', 'datecreated'}
        expected = {}
        for table, values in rows.items():
            fields = list(values[0])
            expected[table] = fields
            columns = [name + (' text' if table == 'ents' and name in text_fields
                else ' double precision' if name in ('posx', 'posy', 'posz') else ' integer')
                for name in fields]
            self.database_sql('CREATE TABLE ' + self.namespace + '.' + table
                + ' (' + ','.join(columns) + ');')
            if table != missing_table:
                for row in values:
                    self.database_sql('INSERT INTO ' + self.namespace + '.' + table
                        + ' (' + ','.join(fields) + ') VALUES ('
                        + ','.join(sql_literal(row[name]) for name in fields) + ');')
        self.database_sql('CREATE TABLE ' + self.namespace + '.shardaccounts '
            '(containerid integer, authname text); INSERT INTO ' + self.namespace
            + '.shardaccounts VALUES (' + str(account_authid) + ", 'COHLOCAL');")
        # Authenticate all 34 Boosts fields from the accepted generated schema
        # and native descriptor before seeding actual slotted/inventory payloads.
        enhancements.generated_contract(ROOT)
        boost_fields = list(enhancements.BOOST_FIELDS)
        expected['boosts'] = boost_fields
        self.database_sql('CREATE TABLE ' + self.namespace + '.boosts ('
            + ','.join(name + (' real' if name in enhancements.FLOAT_FIELDS else ' integer')
                for name in boost_fields) + ');')
        for subid, powerid, index in ((0, -1, 3), (1, 1, 0)):
            boost = {name: 0 for name in boost_fields}
            boost.update(containerid=1, subid=subid, powerid=powerid, idx=index,
                categoryname=1, powersetname=1, boostname=1, level=4,
                numcombines=2, var0=.5, var1=.25, var2=.125, var3=.0625)
            self.database_sql('INSERT INTO ' + self.namespace + '.boosts ('
                + ','.join(boost_fields) + ') VALUES ('
                + ','.join(sql_literal(boost[name]) for name in boost_fields) + ');')
        # Additional inventory/progression sentinel is outside selected-row
        # acceptance. It is a no-mutation witness, not native game validation.
        self.database_sql('CREATE TABLE ' + self.namespace + '.extra_state_sentinel '
            '(containerid integer, payload jsonb); INSERT INTO ' + self.namespace
            + '.extra_state_sentinel VALUES (1, '
            + "'{\"inventory\":[17,28],\"progression\":{\"xp\":19}}'::jsonb);")
        ctx = SimpleNamespace(report={}, children=[], event=Mock(), start=Mock())
        owner = SimpleNamespace(ctx=ctx, root=self.root,
            args=SimpleNamespace(session_id='a' * 32, state=self.root))
        value = zoning.LocalCharacterZoningServer(owner)
        value.schema = {'expected_attributes': attributes, 'expected_tables': expected}
        value.monorail_qualified = qualified

        def production_sql(text, *, game=False, cleanup=False):
            self.assertTrue(game, 'Saved-map evidence unexpectedly queried another database')
            self.assertFalse(cleanup, 'Selection unexpectedly invoked SQL cleanup')
            self.assertRegex(text, r'^SELECT\b', 'Saved-map selection attempted a non-SELECT statement')
            self.sql_calls.append(text)
            output = self.database_sql('BEGIN READ ONLY; SET LOCAL statement_timeout = 5000; '
                + text.replace('dbo.', self.namespace + '.') + ' COMMIT;')
            ctx.children.append(SimpleNamespace(text=lambda: output))
            return output
        owner.sql = production_sql
        return value

    def snapshot(self):
        tables = self.database_sql("SELECT tablename FROM pg_tables WHERE schemaname='"
            + self.namespace + "' ORDER BY tablename;").splitlines()
        rows = {table: self.database_sql('SELECT coalesce(jsonb_agg(x ORDER BY to_jsonb(x)::text),'
            + "'[]'::jsonb) FROM " + self.namespace + '.' + table + ' x;') for table in tables}
        return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()

    def real_case(self, name, *, allowed=False, twice=False, **options):
        value = self.seed(**options)
        before = self.snapshot()
        boosts = value.sql_rows('boosts', enhancements.BOOST_FIELDS,
            ('containerid', 'subid'), 'containerid=1')
        self.assertEqual(len(boosts), 2)
        self.assertTrue(all(set(row) == set(enhancements.BOOST_FIELDS) for row in boosts))
        if allowed:
            value.capture_baseline()
            baseline = copy.deepcopy(value.creation_report['baseline'])
            position = baseline['saved_position']
            expected_map = options.get('map_id', 5)
            self.assertEqual(value.active_map_id, expected_map)
            self.assertEqual(position, dict(containerid=1, staticmapid=expected_map,
                mapid=options.get('active_map'), posx=321.125, posy=-48.5, posz=97.875))
            self.assertEqual(value.creation_report['map_id'], expected_map)
            self.assertEqual(value.baseline_snapshot['identity'],
                dict(containerid=1, authid=77, authname='COHLOCAL', name='THORHERO'))
            self.assertEqual(set(baseline['table_sha256']), set(zoning.character.evidence.SELECTED))
            saved = value.zoning_report['saved_startup']
            self.assertEqual(saved['map_id'], expected_map)
            self.assertEqual(saved['port'], zoning.MAPS[expected_map]['port'])
            self.assertEqual(saved['world'], zoning.MAPS[expected_map]['world'])
            self.assertFalse(saved['native_ready_verified'])
            self.assertFalse(saved['character_world_entry_verified'])
            self.assertFalse(saved['sql_game_mutations_performed'])
            if twice:
                value.active_map_id = 1  # a new launcher default; never SQL relocation
                value.capture_baseline()
                self.assertEqual(value.active_map_id, 5)
                self.assertEqual(value.creation_report['baseline']['saved_position'], position)
                self.assertEqual(value.creation_report['baseline']['table_sha256'], baseline['table_sha256'])
        else:
            with self.assertRaises(zoning.base.DiagnosticError):
                value.capture_baseline()
            self.assertFalse(value.creation_report.get('existing_character_verified'))
        value.ctx.start.assert_not_called()
        self.assertTrue(self.sql_calls)
        self.assertEqual(before, self.snapshot(), 'Selection changed character/extra sentinel state')
        self.assertEqual(boosts, value.sql_rows('boosts', enhancements.BOOST_FIELDS,
            ('containerid', 'subid'), 'containerid=1'), 'Selection changed complete Boosts payload')
        POSTGRES_FIXTURES_RUN.add(name)

    def test_pg_kings_unassigned(self): self.real_case('kings_unassigned', allowed=True)
    def test_pg_kings_assigned(self): self.real_case('kings_assigned', allowed=True, active_map=5)
    def test_pg_atlas_unassigned(self): self.real_case('atlas_unassigned', allowed=True, map_id=1)
    def test_pg_atlas_assigned(self): self.real_case('atlas_assigned', allowed=True, map_id=1, active_map=1)
    def test_pg_atlas_instance_unassigned(self): self.real_case('atlas_instance_unassigned', allowed=True, map_id=101)
    def test_pg_atlas_instance_assigned(self): self.real_case('atlas_instance_assigned', allowed=True, map_id=101, active_map=101)
    def test_pg_repeated_kings_selection(self): self.real_case('repeated_kings_selection', allowed=True, twice=True)
    def test_pg_unsupported_saved_destination(self): self.real_case('unsupported_saved_destination', map_id=2)
    def test_pg_inconsistent_active_map(self): self.real_case('inconsistent_active_map', active_map=1)
    def test_pg_foreign_name(self): self.real_case('foreign_name', changes={'name': 'OTHERHERO'})
    def test_pg_foreign_account(self): self.real_case('foreign_account', changes={'authname': 'OTHER'})
    def test_pg_account_identity_mismatch(self): self.real_case('account_identity_mismatch', account_authid=78)
    def test_pg_missing_power_rows(self): self.real_case('missing_power_rows', missing_table='powers')
    def test_pg_missing_costume_rows(self): self.real_case('missing_costume_rows', missing_table='costumeparts')
    def test_pg_missing_native_kings_qualification(self): self.real_case('missing_native_kings_qualification', qualified=False)
    def test_pg_nonfinite_saved_position(self):
        value = self.seed()
        self.database_sql('UPDATE ' + self.namespace + ".ents SET posx='NaN'::double precision;")
        before = self.snapshot()
        with self.assertRaises(zoning.base.DiagnosticError): value.capture_baseline()
        self.assertEqual(before, self.snapshot())
        value.ctx.start.assert_not_called()
        POSTGRES_FIXTURES_RUN.add('nonfinite_saved_position')

    def test_pg_read_only_transaction_enforced(self):
        value = self.seed()
        before = self.snapshot()
        # A function call still begins SELECT. The actual PostgreSQL transaction
        # must prohibit writes even if an unexpectedly impure SELECT is added.
        self.database_sql('CREATE FUNCTION ' + self.namespace + '.forbidden_mutation() '
            + 'RETURNS integer LANGUAGE plpgsql AS $$BEGIN UPDATE ' + self.namespace
            + '.ents SET staticmapid=1; RETURN 1; END;$$;')
        with self.assertRaisesRegex(RuntimeError, 'read-only transaction'):
            value.owner.sql('SELECT ' + self.namespace + '.forbidden_mutation();', game=True)
        self.assertEqual(before, self.snapshot())
        POSTGRES_FIXTURES_RUN.add('read_only_transaction_enforced')


def qualification_inventory():
    if not REQUIRE_POSTGRESQL or POSTGRES_FIXTURES_RUN != REQUIRED_POSTGRES_FIXTURES:
        raise RuntimeError('Every real saved-map PostgreSQL fixture is required; skipped tests are not proof')
    return {'format': 1, 'status': 'passed', 'scope': SCOPE, 'postgresql_major': 16,
        'fixtures': sorted(POSTGRES_FIXTURES_RUN), 'sql_transaction_mode': 'READ ONLY',
        'fixture_schema_isolated': True, 'player_database_accessed': False,
        'native_process_booted': False, 'native_client_connected': False,
        'native_save_logout_executed': False, 'physical_ayn_thor_validated': False,
        'enhancement_no_mutation_scope': 'actual_isolated_postgresql_full_34_field_boosts_rows',
        'boost_fields': list(enhancements.BOOST_FIELDS),
        'generated_boost_template_sha256': enhancements.TEMPLATE_SHA256,
        'shipping_enhancement_capture_changed': False}


def validate_qualification_inventory(proof):
    """Validate a saved artifact independently of local executed-test state."""
    expected = {'format': 1, 'status': 'passed', 'scope': SCOPE, 'postgresql_major': 16,
        'fixtures': sorted(REQUIRED_POSTGRES_FIXTURES), 'sql_transaction_mode': 'READ ONLY',
        'fixture_schema_isolated': True, 'player_database_accessed': False,
        'native_process_booted': False, 'native_client_connected': False,
        'native_save_logout_executed': False, 'physical_ayn_thor_validated': False,
        'enhancement_no_mutation_scope': 'actual_isolated_postgresql_full_34_field_boosts_rows',
        'boost_fields': list(enhancements.BOOST_FIELDS),
        'generated_boost_template_sha256': enhancements.TEMPLATE_SHA256,
        'shipping_enhancement_capture_changed': False}
    if (type(proof) is not dict or set(proof) != set(expected)
            or any(type(proof[name]) is not type(value) or proof[name] != value
                for name, value in expected.items())):
        raise RuntimeError('Actual saved-map PostgreSQL fixture proof differs')
    return proof


if __name__ == '__main__': unittest.main()
