"""The persistent profile must survive cleanup and prove this launch's login."""
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import client_login_diagnostic as guest
import local_login_server as server

SESSION = '0123456789abcdef0123456789abcdef'
DEBUG = '260930 00:28:21 0 127.0.0.1 successful login for "COHLOCAL" AuthID 900260380 Cookie 0\n'
SPECS = '260930 00:28:21 0 IP,127.0.0.1,AuthName,COHLOCAL,SystemSpecs,Disabled\n'


class LoginProofTests(unittest.TestCase):
    def instance(self, debug=DEBUG, specs=SPECS):
        owner = SimpleNamespace(ctx=SimpleNamespace(report={}), root=Path('/private'),
            args=SimpleNamespace(session_id=SESSION))
        value = server.LocalLoginServer(owner)
        value.current_logs = Mock(return_value=[('logs/dbserver/debug_000.log', debug),
            ('logs/dbserver/SystemSpecs_000.log', specs)])
        value.sql = Mock(side_effect=['900260380|COHLOCAL', '0'])
        return value

    def test_fresh_matching_send_and_sql_proves_sender_not_receipt(self):
        value = self.instance().login_evidence()
        self.assertTrue(value['character_list_response_sent'])
        self.assertTrue(value['local_account_verified'])
        self.assertFalse(value['character_selection_visual_validated'])
        self.assertNotIn('character_selection_received', value)

    def test_both_owned_logs_required(self):
        for debug, specs in [('', SPECS), (DEBUG, ''), (DEBUG.replace('COHLOCAL', 'another'), SPECS),
                            (DEBUG, SPECS.replace('COHLOCAL', 'another')),
                            (DEBUG.replace('127.0.0.1', '192.168.0.1'), SPECS)]:
            with self.subTest(debug=debug, specs=specs):
                value = self.instance(debug, specs)
                self.assertIsNone(value.login_evidence()); value.sql.assert_not_called()

    def test_incomplete_log_lines_cannot_prove_send(self):
        self.assertIsNone(self.instance(DEBUG, SPECS[:50]).login_evidence())
        self.assertIsNone(self.instance(DEBUG, SPECS.rstrip('\n')).login_evidence())
        self.assertIsNone(self.instance(DEBUG.rstrip('\n'), SPECS).login_evidence())

    def test_changed_auth_identity_and_existing_character_refused(self):
        for rows in [['900260381|COHLOCAL', '0'], ['900260380|COHLOCAL\n1|COHLOCAL', '0'],
                     ['900260380|COHLOCAL', '1']]:
            value = self.instance(); value.sql.side_effect = rows
            with self.assertRaises(guest.base.DiagnosticError): value.login_evidence()
        value = self.instance(DEBUG + DEBUG.replace('900260380', '1'))
        with self.assertRaises(guest.base.DiagnosticError): value.login_evidence()

    def test_log_filename_must_be_current_dbserver_category(self):
        value = self.instance(); value.current_logs.return_value = [('other.log', DEBUG + SPECS)]
        self.assertIsNone(value.login_evidence())


class PersistenceTests(unittest.TestCase):
    def test_deletion_refused_even_if_fixture_flag_accidentally_changes(self):
        d = guest.ClientLoginDiagnostic.__new__(guest.ClientLoginDiagnostic)
        d.database_created = True
        with patch.object(guest.base.Diagnostic, 'sql') as execute:
            for sql in ['DROP DATABASE "coh_local_android";', 'drop\n database x;']:
                with self.assertRaises(guest.base.DiagnosticError): d.sql(sql, cleanup=True)
            execute.assert_not_called()

    def test_marker_is_exact_and_disallows_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'profile.json'
            good = dict(server.PROFILE_IDENTITY, initialized=True)
            path.write_text(json.dumps(good))
            self.assertEqual(server.profile_record(path), good)
            for bad in [dict(good, database='production'), dict(good, initialized=1), dict(good, extra=1)]:
                path.write_text(json.dumps(bad))
                with self.assertRaises(guest.base.DiagnosticError): server.profile_record(path)
            other = path.with_name('other.json'); other.write_text(json.dumps(good))
            path.unlink(); path.symlink_to(other)
            with self.assertRaises(guest.base.DiagnosticError): server.profile_record(path)

    def test_cleanup_keeps_cluster_and_verifies_postgres_shutdown(self):
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            (profile / 'pgdata').mkdir(); (profile / 'pgdata/PG_VERSION').write_text('17\n')
            (profile / 'profile.json').write_text(json.dumps(dict(server.PROFILE_IDENTITY, initialized=True)))
            d = guest.ClientLoginDiagnostic.__new__(guest.ClientLoginDiagnostic)
            d.ctx = SimpleNamespace(server_health=Mock(), report={'postgres_started': True})
            d.cleanup_status = {'postgres_graceful': True}; d.database_created = False
            d.local_server = SimpleNamespace(profile=profile, report={}, cleanup_config=Mock())
            with patch.object(guest.interactive.ClientInteractiveDiagnostic, 'cleanup', return_value=[]):
                self.assertEqual(d.cleanup(), [])
            self.assertTrue(d.local_server.report['database_preserved'])
            self.assertTrue((profile / 'pgdata/PG_VERSION').exists())
            self.assertIsNone(d.ctx.server_health)
            d.cleanup_status['postgres_graceful'] = False
            with patch.object(guest.interactive.ClientInteractiveDiagnostic, 'cleanup', return_value=[]):
                self.assertTrue(d.cleanup())
            self.assertFalse(d.local_server.report['database_preserved'])

    def test_finish_cannot_pass_before_send_proof(self):
        d = guest.ClientLoginDiagnostic.__new__(guest.ClientLoginDiagnostic)
        d.login_announced = False; d.local_server = SimpleNamespace(report={})
        with patch.object(guest.interactive.ClientInteractiveDiagnostic, 'finish_observation') as finish:
            with self.assertRaises(guest.base.DiagnosticError): d.finish_observation({'pid': 4}, '', 100)
            finish.assert_not_called()


class ArchiveTests(unittest.TestCase):
    def archive(self, root, members):
        path = root / 'archive.tar.gz'
        with tarfile.open(path, 'w:gz') as archive:
            for name, kind in members:
                info = tarfile.TarInfo(name); info.mode = 0o644; info.size = 1
                if kind == 'link': info.type = tarfile.SYMTYPE; info.linkname = '/etc/passwd'; info.size = 0
                archive.addfile(info, io.BytesIO(b'x') if info.size else None)
        return path

    def test_traversal_link_duplicates_and_case_collisions_refused(self):
        cases = [[('../outside', '')], [('/absolute', '')], [('link', 'link')],
                 [('same', ''), ('same', '')], [('A', ''), ('a', '')]]
        for members in cases:
            with self.subTest(members=members), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                with self.assertRaises(guest.base.DiagnosticError):
                    server.extract_regular(self.archive(root, members), root / 'out')

    def test_regular_sorted_payload_extracts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            server.extract_regular(self.archive(root, [('data/file', ''), ('file', '')]), root / 'out')
            self.assertEqual((root / 'out/data/file').read_bytes(), b'x')


if __name__ == '__main__': unittest.main()
