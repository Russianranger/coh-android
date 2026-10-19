"""Notification-pregrant lifecycle controls; no Android execution claim."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import upgrade_emulator_check as driver


RECEIPT = {'version_code': '11', 'version_name': '0.1.10-memory-diagnostic-test',
           'apk': {'bytes': 7, 'sha256': 'a' * 64}}
REPORT = {'version_code': 11, 'version_name': RECEIPT['version_name'],
          'installed_apk_status': 'ready', 'installed_apk': RECEIPT['apk'],
          'updated_elapsed_ms': 1000001, 'busy': False,
          'server': {'owned_process_alive': False, 'ready': False, 'phase': 'stopped', 'failure_code': ''}}


class Simulated(driver.UpgradeCheck):
    def __init__(self, directory, reports=(), granted=True):
        super().__init__(SimpleNamespace(output=Path(directory)))
        self.reports = list(reports)
        self.commands = []
        self.granted = granted

    def text(self, *command):
        self.commands.append(command)
        if command[-1] == '/proc/uptime':
            return '1000.00 0.00'
        if command[:3] == ('shell', 'dumpsys', 'package'):
            return '\n    android.permission.POST_NOTIFICATIONS: granted=' + str(self.granted).lower() + ', flags=[]\n'
        return 'Status: ok\nActivity: org.coh.nativecombined/.MainActivity\n'

    def adb(self, *command, **kwargs):
        self.commands.append(command)
        if command[:3] == ('exec-out', 'run-as', driver.PACKAGE):
            return SimpleNamespace(returncode=0, stdout=json.dumps(self.reports.pop(0)).encode(), stderr=b'')
        return SimpleNamespace(returncode=0, stdout=b'Success\n', stderr=b'')

    def capture(self, label):
        pass

    def assert_no_app_fault(self, label):
        pass


class UpgradeDriverControls(unittest.TestCase):
    def test_old_update_rollback_and_reinstall_all_pregrant_requested_runtime_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            check = Simulated(tmp)
            for label, replace, downgrade in [('old', False, False), ('update', True, False), ('rollback', True, True), ('reinstall', True, False)]:
                check.install(Path('fixture.apk'), label, replace=replace, downgrade=downgrade)
            installs = [x for x in check.commands if x[0] == 'install']
            self.assertEqual(installs, [
                ('install', '-g', Path('fixture.apk')),
                ('install', '-g', '-r', Path('fixture.apk')),
                ('install', '-g', '-r', '-d', Path('fixture.apk')),
                ('install', '-g', '-r', Path('fixture.apk'))])

    def test_ungranted_notification_prompt_is_rejected_before_launch_or_report_polling(self):
        with tempfile.TemporaryDirectory() as tmp:
            check = Simulated(tmp, granted=False)
            with self.assertRaisesRegex(ValueError, 'must grant notifications'):
                check.launch_and_quiesce(RECEIPT, 'blocked')
            self.assertFalse(any(x[:3] == ('shell', 'am', 'start') for x in check.commands))
            self.assertFalse(any(x[0] == 'exec-out' for x in check.commands))

    def test_pregrant_still_requires_a_fresh_matching_report_after_old_stale_report(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(driver.time, 'sleep', return_value=None):
            stale = dict(REPORT, version_code=10, version_name='0.1.9-gates25-27-test', updated_elapsed_ms=50008)
            check = Simulated(tmp, [stale, REPORT])
            check.launch_and_quiesce(RECEIPT, 'fresh')
            observations = json.loads((Path(tmp) / 'fresh-report-observations.json').read_bytes())
            self.assertEqual(observations['read_attempts'], 2)
            self.assertTrue(check.proofs[-1]['notification_permission_granted'])
            self.assertTrue(check.proofs[-1]['fresh_report_epoch'])

    def test_pregrant_does_not_hide_wrong_apk_or_failed_initialization(self):
        for change, expected in [('apk', 'APK identity differs'), ('failed', 'initialization failed')]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                report = copy.deepcopy(REPORT)
                if change == 'apk':
                    report['installed_apk']['sha256'] = 'b' * 64
                else:
                    report['server'].update(phase='failed', failure_code='SERVER_ADMISSION_FAILED')
                with self.assertRaisesRegex(ValueError, expected):
                    Simulated(tmp, [report]).launch_and_quiesce(RECEIPT, 'refused')


if __name__ == '__main__':
    unittest.main()
