"""Character SQL acceptance must reject apparent success with changed/missing data."""
import copy
import io
import re
import unittest
from unittest.mock import patch
import zipfile

import character_snapshot as snapshot
import run_generated_schema as schema


ACCOUNT = 'CohPersist01'
NAME = 'TEST12345'
IDENTIFIER = 42


def accepted_tables():
    with zipfile.ZipFile(schema.ROOT / 'docs/schema-generation-evidence/accepted-36088012666.zip') as outer:
        with zipfile.ZipFile(io.BytesIO(outer.read('schema-evidence/schema-outputs.zip'))) as inner:
            tables = schema.template_columns(inner.read('data/server/db/templates/ents.template').decode(), 'ents')
    for name in ('attributes', 'badgestatsattributes', 'pophelpattributes'):
        tables[name] = ['id', 'name']
    return tables


class SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = accepted_tables()

    def setUp(self):
        self.records = {table: [{column: 1 for column in fields}]
                        for table, fields in snapshot.SELECTED.items()}
        for table, records in self.records.items():
            records[0]['containerid'] = IDENTIFIER
            if table != 'ents':
                records[0]['subid'] = 0
        self.records['ents'][0].update(authid=77, authname=ACCOUNT, name=NAME,
            influencepoints=12345, logincount=1, description='', motto='',
            datecreated='2026-09-26T12:00:00')
        self.records['ents2'][0].update(originalprimary='Energy_Blast', originalsecondary='Energy_Manipulation')
        self.accounts = [{field: self.records['ents'][0][field]
                          for field in snapshot.IDENTITY_FIELDS + ('logincount',)}]
        self.attributes = {name: [{'id': 1, 'name': 'reviewed_attribute'}]
                           for name in ('attributes', 'badgestatsattributes', 'pophelpattributes')}
        self.calls = []

    def query(self, cluster, sql):
        self.calls.append(sql)
        table = re.search(r'FROM dbo\.([a-z_][a-z_0-9]*)', sql).group(1)
        if table in self.attributes:
            return copy.deepcopy(self.attributes[table])
        if 'lower(authname)' in sql:
            return copy.deepcopy(self.accounts)
        return copy.deepcopy(self.records[table])

    def capture(self, **kwargs):
        with patch.object(snapshot, 'query_json', side_effect=self.query):
            return snapshot.capture(None, self.tables, ACCOUNT, IDENTIFIER, NAME, **kwargs)

    def test_contract_is_supported_by_actual_accepted_ents_template(self):
        contract = snapshot.selected_contract(self.tables)
        self.assertEqual(contract['expected_influence'], 12345)
        self.assertEqual(contract['row_keys']['powers'], ['containerid', 'subid'])
        for table in ('ents2', 'powers', 'costumeparts'):
            self.assertEqual(self.tables[table][:2], ['containerid', 'subid'])
        for absent in ('logincount', 'lastactive', 'posx', 'hitpoints', 'totaltime'):
            self.assertNotIn(absent, contract['fields']['ents'])
        for absent in ('creationtime', 'rechargedat', 'usagetime', 'active'):
            self.assertNotIn(absent, contract['fields']['powers'])

    def test_missing_selected_field_or_changed_keys_rejected_before_queries(self):
        for table, column in (('ents', 'influencepoints'), ('ents', 'logincount'),
                              ('powers', 'uniqueid'), ('costumeparts', 'subid')):
            changed = copy.deepcopy(self.tables)
            changed[table].remove(column)
            with self.subTest(table=table, column=column), patch.object(snapshot, 'query_json') as query:
                with self.assertRaises(ValueError):
                    snapshot.capture(None, changed, ACCOUNT, IDENTIFIER, NAME)
                query.assert_not_called()
        changed = copy.deepcopy(self.tables)
        changed['powers'][0:2] = reversed(changed['powers'][0:2])
        with self.assertRaisesRegex(ValueError, 'row keys'):
            snapshot.selected_contract(changed)

    def test_sql_reads_only_reviewed_columns_and_orders_by_schema_keys(self):
        result = self.capture()
        self.assertEqual(result['identity']['containerid'], IDENTIFIER)
        self.assertEqual(result['login_count'], 1)
        self.assertNotIn('logincount', result['rows']['ents'][0])
        self.assertEqual(len(self.calls), 5)
        for sql in self.calls:
            self.assertTrue(sql.startswith('SELECT '))
            self.assertNotIn('SELECT *', sql)
        for sql in self.calls[1:4]:
            self.assertIn('ORDER BY containerid,subid', sql)
            self.assertIn('WHERE containerid=42', sql)
        self.assertIn("WHERE lower(authname)='cohpersist01' OR authid=77", self.calls[-1])

    def test_fresh_account_empty_is_observable_and_unsafe_names_never_reach_sql(self):
        self.accounts = []
        with patch.object(snapshot, 'query_json', side_effect=self.query):
            self.assertEqual(snapshot.account_rows(None, ACCOUNT, self.tables), [])
        for value in ("a' OR TRUE--", 'account name', 'é', '', 'A' * 33, None):
            with self.subTest(value=value), patch.object(snapshot, 'query_json') as query:
                with self.assertRaises(ValueError):
                    snapshot.account_rows(None, value, self.tables)
                query.assert_not_called()

    def test_nonpositive_or_boolean_ids_cannot_identify_a_character(self):
        for value in (0, -1, True, '42', None):
            with self.subTest(value=value), patch.object(snapshot, 'query_json') as query:
                with self.assertRaisesRegex(ValueError, 'positive integer'):
                    snapshot.capture(None, self.tables, ACCOUNT, value, NAME)
                query.assert_not_called()

    def test_missing_required_child_cannot_pass(self):
        for table in ('ents', 'ents2', 'powers', 'costumeparts'):
            with self.subTest(table=table):
                original = self.records[table]
                self.records[table] = []
                with self.assertRaisesRegex(ValueError, 'missing: ' + table):
                    self.capture()
                self.records[table] = original

    def test_foreign_or_duplicate_child_keys_cannot_pass(self):
        for mutation in ('wrong_character', 'duplicate_key', 'negative_key', 'out_of_order'):
            with self.subTest(mutation=mutation):
                original = copy.deepcopy(self.records['powers'])
                if mutation == 'wrong_character':
                    self.records['powers'][0]['containerid'] = 43
                elif mutation == 'duplicate_key':
                    self.records['powers'].append(copy.deepcopy(self.records['powers'][0]))
                elif mutation == 'negative_key':
                    self.records['powers'][0]['subid'] = -1
                else:
                    self.records['powers'][0]['subid'] = 2
                    self.records['powers'].append(dict(self.records['powers'][0], subid=1))
                with self.assertRaises(ValueError):
                    self.capture()
                self.records['powers'] = original

    def test_missing_duplicate_or_changed_account_character_rejected(self):
        baseline = copy.deepcopy(self.accounts)
        for changed in ([], baseline * 2, [dict(baseline[0], containerid=43)],
                        baseline + [dict(baseline[0], containerid=43, name='CREATEDAGAIN')],
                        [dict(baseline[0], logincount=2)]):
            with self.subTest(changed=changed):
                self.accounts = changed
                with self.assertRaisesRegex(ValueError, 'extra character rows'):
                    self.capture()

    def test_identity_and_currency_must_match_protocol_selection(self):
        for field, value in (('name', 'WrongCharacter'), ('authname', 'SomeoneElse'),
                             ('authid', 0), ('influencepoints', 0), ('influencepoints', '12345')):
            with self.subTest(field=field, value=value):
                previous = self.records['ents'][0][field]
                self.records['ents'][0][field] = value
                with self.assertRaises(ValueError):
                    self.capture()
                self.records['ents'][0][field] = previous
        with self.assertRaisesRegex(ValueError, 'requires influence 12345'):
            self.capture(expected_influence=0)

    def test_restart_and_resume_compare_stable_data_and_count_progression_separately(self):
        before = self.capture()
        restarted = copy.deepcopy(before)
        resumed = copy.deepcopy(before)
        resumed['login_count'] = 2
        self.assertTrue(snapshot.compare(before, restarted, 'restart')['selected_rows_unchanged'])
        self.assertEqual(snapshot.compare(restarted, resumed, 'resume')['login_count_after'], 2)
        for phase, after in (('resume', restarted), ('restart', resumed),
                             ('resume', dict(resumed, login_count=3))):
            with self.subTest(phase=phase, count=after['login_count']):
                with self.assertRaisesRegex(ValueError, 'LoginCount'):
                    snapshot.compare(before, after, phase)

    def test_changed_selected_values_or_new_child_rows_rejected_after_restart(self):
        before = self.capture()
        for table, field, value in (('ents', 'description', 'changed'),
                                    ('ents2', 'curbuild', 2), ('powers', 'powername', 2),
                                    ('costumeparts', 'color1', 2)):
            with self.subTest(table=table):
                after = copy.deepcopy(before)
                after['rows'][table][0][field] = value
                with self.assertRaisesRegex(ValueError, 'rows changed'):
                    snapshot.compare(before, after, 'restart')
        after = copy.deepcopy(before)
        after['rows']['powers'].append(dict(after['rows']['powers'][0], subid=1))
        with self.assertRaisesRegex(ValueError, 'rows changed'):
            snapshot.compare(before, after, 'restart')

    def test_attribute_snapshot_requires_exact_accepted_mapping_and_stable_reload(self):
        with patch.object(snapshot, 'query_json', side_effect=self.query):
            actual = snapshot.attribute_snapshot(None, self.tables, expected=self.attributes)
            self.assertEqual(actual, self.attributes)
            wrong = copy.deepcopy(self.attributes)
            wrong['attributes'][0]['name'] = 'changed'
            with self.assertRaisesRegex(ValueError, 'accepted generated mappings'):
                snapshot.attribute_snapshot(None, self.tables, expected=wrong)
        self.assertTrue(snapshot.compare_attributes(actual, copy.deepcopy(actual))['unchanged'])
        with self.assertRaisesRegex(ValueError, 'mappings changed'):
            snapshot.compare_attributes(actual, wrong)
        for sql in self.calls:
            self.assertIn('ORDER BY id', sql)

    def test_selected_attribute_references_must_resolve_in_accepted_mapping(self):
        state = self.capture()
        self.assertTrue(snapshot.validate_attribute_references(state, self.attributes))
        state['rows']['costumeparts'][0]['fxname'] = None
        self.assertTrue(snapshot.validate_attribute_references(state, self.attributes))
        state['rows']['powers'][0]['powername'] = 999999
        with self.assertRaisesRegex(ValueError, 'powers.powername'):
            snapshot.validate_attribute_references(state, self.attributes)

    def test_optional_supercostumeparts_are_not_required(self):
        # New characters commonly lack these rows; ordinary costume evidence
        # still has to be present and comparable.
        self.assertNotIn('supercostumeparts', snapshot.SELECTED)
        self.capture()


if __name__ == '__main__':
    unittest.main()
