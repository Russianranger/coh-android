"""The persistent profile must survive cleanup and prove this launch's login."""
import io
import json
import re
import shutil
import subprocess
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


class LauncherPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('cc') or shutil.which('gcc')
        if compiler is None: raise unittest.SkipTest('A C compiler is needed for the native mode policy')
        cls.temporary = tempfile.TemporaryDirectory(); root = Path(cls.temporary.name)
        source = (ROOT / 'android/native/client-launcher.c').read_text()
        policy = source[source.index('static const char *launch_policy('):source.index('int main(int argc, char **argv)')]
        # Compile the production deadline expression/condition with a fake
        # monotonic clock, so a policy-only change cannot hide a fixed main-loop
        # bound that still consumes character interaction time during startup.
        deadline = re.search(r'    deadline=([^;]+);', source).group(1)
        expired = re.search(r'        if\((GetTickCount64\(\)>=deadline)\)', source).group(1)
        harness = ('#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n' + policy
            + 'static unsigned long long clock_ms=123456; '
            + 'static unsigned long long GetTickCount64(void) { return clock_ms; }\n'
            + 'int main(int argc,char **argv) { int generate=-1; const char *value; '
            + 'unsigned long lifetime_ms=0; unsigned long long deadline; '
            + 'if(argc<2)return 2; value=launch_policy(atoi(argv[1]),argc>2?argv[2]:NULL,&generate,&lifetime_ms); '
            + 'deadline=' + deadline + '; if(argc>3)clock_ms+=strtoull(argv[3],NULL,10); '
            + 'printf("%d|%lu|%s|%d",generate,lifetime_ms,value?value:"INVALID",' + expired + '); return 0; }\n')
        path = root / 'policy.c'; path.write_text(harness)
        cls.binary = root / 'policy'
        subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', str(path), '-o', str(cls.binary)], check=True)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'temporary'): cls.temporary.cleanup()

    def test_native_override_and_longer_lifetime_are_scoped_to_explicit_profiles(self):
        for arguments, expected in [(['4'], '0|1200000||0'), (['5','--generate-caches'], '1|1200000||0'),
                (['5','--local-login'], '0|1200000| -noversioncheck 1|0'),
                (['5','--character-creation'], '0|2160000| -noversioncheck 1|0'),
                (['5','--unknown'], '0|1200000|INVALID|0'), (['5'], '0|1200000|INVALID|0'),
                (['3'], '0|1200000|INVALID|0'), (['6','--local-login'], '0|1200000|INVALID|0'),
                (['6','--character-creation'], '0|1200000|INVALID|0')]:
            with self.subTest(arguments=arguments):
                actual = subprocess.check_output([str(self.binary), *arguments], text=True)
                self.assertEqual(actual, expected)

    def test_character_deadline_retains_post_startup_interaction_and_stays_bounded(self):
        # The failed hosted run spent 419s reaching the menu. Also cover the
        # permitted 900s startup plus 1200s interaction and 60s finish grace.
        for elapsed_ms, expired in [(1200000, 0), ((419+1200)*1000, 0),
                                    ((900+1200)*1000, 0), (2160000-1, 0), (2160000, 1)]:
            with self.subTest(elapsed_ms=elapsed_ms):
                value = subprocess.check_output([str(self.binary), '5', '--character-creation', str(elapsed_ms)], text=True)
                self.assertEqual(value, f'0|2160000| -noversioncheck 1|{expired}')
        for mode in ('--local-login', '--generate-caches'):
            value = subprocess.check_output([str(self.binary), '5', mode, '1200000'], text=True)
            self.assertTrue(value.endswith('|1'))

    def test_guest_mode_hook_preserves_default_and_scopes_local_login(self):
        args = SimpleNamespace(wine=Path('/wine'), assets=Path('/assets'), session_id=SESSION)
        default = guest.interactive.ClientInteractiveDiagnostic.__new__(guest.interactive.ClientInteractiveDiagnostic)
        default.args = args; default.work = Path('/work')
        local = guest.ClientLoginDiagnostic.__new__(guest.ClientLoginDiagnostic)
        local.args = args; local.work = Path('/work')
        expected = default.launcher_command()
        self.assertEqual(len(expected), 5)
        self.assertNotIn('--local-login', expected)
        self.assertEqual(local.launcher_command(), expected + ['--local-login'])


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
