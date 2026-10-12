"""Exact live-to-dead Wine worker lineage when Android denies environ reads."""
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import game_device_diagnostic as guest


class CleanupLineageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.context = guest.base.Context(self.root)
        self.owner = guest.DeviceWineProcessOwner(self.context, self.root)
        self.owner.initialized = True
        self.owner.real_uid = 42
        self.owner.excluded = set()
        self.owner.direct_pid_view = True
        self.owner.diagnostic_starttime = 1
        self.prefix = '/private/test-wine'
        self.group = self.root / '123'
        self.task = self.group / 'task/124'
        self.group_stat = dict(pid=123, state='S', parent=1, starttime=10, process_group=123, session=123)
        self.worker_stat = dict(pid=124, state='R', parent=1, starttime=11, process_group=123, session=123)
        self.group_status = dict(uid=42, pid=123, tgid=123, namespace_pids=[123])
        self.worker_status = dict(uid=42, pid=124, tgid=123, namespace_pids=[124])
        self.write_process(self.group, self.group_stat, self.group_status)
        self.write_process(self.task, self.worker_stat, self.worker_status)
        (self.root / 'self/ns').mkdir(parents=True)
        (self.root / 'self/ns/pid').symlink_to('pid:[111]')

    def write_stat(self, path, value):
        fields = ['0'] * 22
        fields[0], fields[1] = value['state'], str(value['parent'])
        fields[2], fields[3] = str(value['process_group']), str(value['session'])
        fields[19] = str(value['starttime'])
        (path / 'stat').write_text(str(value['pid']) + ' (wine worker) ' + ' '.join(fields) + '\n')

    def write_status(self, path, value):
        (path / 'status').write_text(f"Uid:\t{value['uid']}\nPid:\t{value['pid']}\n"
            f"Tgid:\t{value['tgid']}\nNSpid:\t" + '\t'.join(map(str, value['namespace_pids'])) + '\n')

    def write_process(self, path, identity, status):
        path.mkdir(parents=True, exist_ok=True)
        self.write_stat(path, identity)
        self.write_status(path, status)
        (path / 'environ').write_bytes(self.owner.needle + b'\0WINEPREFIX=' + os.fsencode(self.prefix) + b'\0')
        (path / 'ns').mkdir(exist_ok=True)
        (path / 'ns/pid').symlink_to('pid:[111]')

    def remember(self):
        failures = self.owner.receipt['inspection_failures']
        self.owner.observe_live_lineage(time.monotonic() + 1, prefix=self.prefix)
        self.assertEqual(self.owner.live_lineage['samples'], 1)
        self.assertEqual(len(self.owner.live_lineage['groups']), 1)
        self.assertEqual(self.owner.receipt['inspection_failures'], failures)

    def dead_leader(self):
        self.group_stat['state'] = 'Z'
        self.write_stat(self.group, self.group_stat)

    def deny_worker(self):
        original = self.owner.has_token
        return patch.object(self.owner, 'has_token', side_effect=lambda path:
            (_ for _ in ()).throw(PermissionError(13, 'private environment denied'))
            if path == self.task else original(path))

    def assert_signal_rejected(self):
        identity = {'proc_pid': 123, 'pid': 123, 'starttime': 10}
        with self.deny_worker(), patch.object(guest.os, 'pidfd_open', return_value=19), \
                patch.object(guest.os, 'close'), patch.object(guest.signal, 'pidfd_send_signal') as send, \
                patch.object(guest.os, 'kill') as kill:
            with self.assertRaises((guest.base.DiagnosticError, PermissionError)):
                self.owner.signal_owned(identity, signal.SIGTERM, time.monotonic() + 1)
            send.assert_not_called()
            kill.assert_not_called()

    def test_dead_leader_with_exact_authenticated_live_worker_can_drain(self):
        self.remember()
        self.dead_leader()
        def exit_worker(*_):
            self.worker_stat['state'] = 'Z'
            self.write_stat(self.task, self.worker_stat)
        with self.deny_worker(), patch.object(guest.os, 'pidfd_open', return_value=19), \
                patch.object(guest.os, 'close'), \
                patch.object(guest.signal, 'pidfd_send_signal', side_effect=exit_worker) as send:
            receipt = self.owner.cleanup(time.monotonic() + 1)
        self.assertTrue(receipt['complete'])
        self.assertEqual((receipt['remaining'], receipt['inspection_failures']), (0, 0))
        self.assertEqual(receipt['pidfd_signals'], 1)
        self.assertEqual(receipt['term_signals'], 1)
        self.assertEqual(receipt['kill_signals'], 0)
        self.assertGreaterEqual(receipt['lineage_ownership_rechecks'], 2)
        self.assertEqual(receipt['permission_observations'][0]['resolution'],
                         'verified_authenticated_worker_lineage')
        send.assert_called_once_with(19, signal.SIGTERM, None, 0)
        self.assertNotIn(self.owner.environment[self.owner.ENV_KEY], json.dumps(receipt))
        self.assertNotIn('private environment denied', json.dumps(receipt))

    def test_matching_shape_without_prior_live_authentication_stays_closed(self):
        self.dead_leader()
        self.assert_signal_rejected()

    def test_readable_worker_under_dead_leader_is_authenticated_before_term(self):
        # Physical .34 read and signaled six workers before a post-TERM EACCES.
        # No live-leader snapshot existed. The worker itself must provide the
        # complete proof while it is still readable; no guessed lineage needed.
        self.dead_leader()
        self.owner.live_lineage['prefix'] = self.prefix
        denied = False
        original = self.owner.has_token
        def token(path):
            if denied and path == self.task:
                raise PermissionError(13, 'environment denied after TERM')
            return original(path)
        def signal_worker(_fd, sig, *_args):
            nonlocal denied
            if sig == signal.SIGTERM:
                denied = True
            else:
                self.worker_stat['state'] = 'Z'
                self.write_stat(self.task, self.worker_stat)
        with patch.object(self.owner, 'has_token', side_effect=token), \
                patch.object(guest.os, 'pidfd_open', return_value=19), patch.object(guest.os, 'close'), \
                patch.object(guest.signal, 'pidfd_send_signal', side_effect=signal_worker):
            receipt = self.owner.cleanup(time.monotonic() + 4)
        self.assertTrue(receipt['complete'])
        self.assertEqual((receipt['term_signals'], receipt['kill_signals']), (1, 1))
        self.assertEqual(receipt['live_lineage_observation']['authenticated_dead_leader_workers'], 1)
        self.assertGreater(receipt['lineage_ownership_rechecks'], 0)
        self.assertNotIn('prefix', receipt['live_lineage_observation'])
        self.assertNotIn(self.owner.environment[self.owner.ENV_KEY], json.dumps(receipt))

    def test_dead_leader_observation_requires_exact_worker_prefix_and_namespace(self):
        self.dead_leader()
        self.owner.live_lineage['prefix'] = self.prefix
        for failure in ('prefix', 'namespace', 'uid', 'session'):
            with self.subTest(failure=failure):
                self.owner.live_lineage['groups'].clear()
                original = (self.task / 'environ').read_bytes()
                if failure == 'prefix':
                    (self.task / 'environ').write_bytes(self.owner.needle + b'\0WINEPREFIX=/other\0')
                if failure == 'namespace':
                    (self.task / 'ns/pid').unlink()
                    (self.task / 'ns/pid').symlink_to('pid:[222]')
                if failure == 'uid':
                    self.worker_status['uid'] = 43
                    self.write_status(self.task, self.worker_status)
                if failure == 'session':
                    self.worker_stat['session'] = 999
                    self.write_stat(self.task, self.worker_stat)
                try:
                    self.owner.inspect(123, time.monotonic() + 1)
                except guest.base.DiagnosticError:
                    pass
                self.assertEqual(self.owner.live_lineage['groups'], {})
                self.assert_signal_rejected()
                (self.task / 'environ').write_bytes(original)
                if failure == 'namespace':
                    (self.task / 'ns/pid').unlink()
                    (self.task / 'ns/pid').symlink_to('pid:[111]')
                self.worker_status['uid'] = 42
                self.worker_stat['session'] = 123
                self.write_status(self.task, self.worker_status)
                self.write_stat(self.task, self.worker_stat)

    def test_second_authenticated_worker_survives_first_worker_exit(self):
        self.dead_leader()
        self.owner.live_lineage['prefix'] = self.prefix
        second = self.group / 'task/125'
        self.write_process(second, dict(self.worker_stat, pid=125, starttime=12),
                           dict(self.worker_status, pid=125, namespace_pids=[125]))
        self.assertIsNotNone(self.owner.inspect(123, time.monotonic() + 1))
        self.assertEqual(set(self.owner.live_lineage['groups'][(123, 10)]['workers']), {(124, 11), (125, 12)})
        self.worker_stat['state'] = 'Z'
        self.write_stat(self.task, self.worker_stat)
        original = self.owner.has_token
        with patch.object(self.owner, 'has_token', side_effect=lambda path:
                (_ for _ in ()).throw(PermissionError(13, 'environment denied'))
                if path == second else original(path)):
            self.assertIsNotNone(self.owner.inspect(123, time.monotonic() + 1))
        self.assertEqual(self.owner.receipt['permission_observations'][-1]['resolution'],
                         'verified_authenticated_worker_lineage')

    def test_one_unreadable_observation_does_not_discard_other_complete_proofs(self):
        unrelated = self.root / '122'
        unrelated.mkdir()
        original = guest.DeviceWineProcessOwner.inspect
        def inspect(owner, pid, deadline=None):
            if pid == 122:
                raise PermissionError(13, 'unrelated unreadable process')
            return original(owner, pid, deadline)
        with patch.object(guest.DeviceWineProcessOwner, 'inspect', new=inspect):
            self.owner.observe_live_lineage(time.monotonic() + 1, prefix=self.prefix)
        self.assertEqual(self.owner.live_lineage['unavailable_samples'], 1)
        self.assertIn((123, 10), self.owner.live_lineage['groups'])
        self.assertEqual(self.owner.receipt['inspection_failures'], 0)
        self.dead_leader()
        with self.deny_worker():
            self.assertIsNotNone(self.owner.inspect(123, time.monotonic() + 1))

    def test_readable_dead_worker_prefix_change_revokes_cached_proof(self):
        self.dead_leader()
        self.owner.live_lineage['prefix'] = self.prefix
        self.assertIsNotNone(self.owner.inspect(123, time.monotonic() + 1))
        self.assertIn((124, 11), self.owner.live_lineage['groups'][(123, 10)]['workers'])
        (self.task / 'environ').write_bytes(self.owner.needle + b'\0WINEPREFIX=/different\0')
        self.assertIsNotNone(self.owner.inspect(123, time.monotonic() + 1))
        self.assertEqual(self.owner.live_lineage['groups'][(123, 10)]['workers'], {})
        self.assert_signal_rejected()

    def test_unseen_worker_in_authenticated_group_stays_closed(self):
        self.remember()
        original = self.task
        self.task = self.group / 'task/125'
        self.worker_stat.update(pid=125, starttime=12)
        self.worker_status.update(pid=125, namespace_pids=[125])
        self.write_process(self.task, self.worker_stat, self.worker_status)
        gone = dict(self.worker_stat, pid=124, starttime=11, state='Z')
        self.write_stat(original, gone)
        self.dead_leader()
        self.assert_signal_rejected()

    def test_exact_pid_and_tid_reuse_does_not_borrow_prior_start_time(self):
        for path, value in ((self.group, self.group_stat), (self.task, self.worker_stat)):
            with self.subTest(path=path.name):
                self.owner.live_lineage['groups'].clear()
                self.owner.live_lineage['next_sample'] = 0
                self.owner.live_lineage['samples'] = 0
                self.group_stat['state'] = 'S'
                self.write_stat(self.group, self.group_stat)
                self.remember()
                self.dead_leader()
                value['starttime'] += 1
                self.write_stat(path, value)
                self.assert_signal_rejected()
                value['starttime'] -= 1
                self.write_stat(path, value)

    def test_changed_process_group_or_session_does_not_authorize_signal(self):
        for path, value in ((self.group, self.group_stat), (self.task, self.worker_stat)):
            for field in ('process_group', 'session'):
                with self.subTest(path=path.name, field=field):
                    self.owner.live_lineage['next_sample'] = 0
                    self.owner.live_lineage['samples'] = 0
                    self.group_stat['state'] = 'S'
                    self.write_stat(self.group, self.group_stat)
                    self.remember()
                    self.dead_leader()
                    value[field] += 1
                    self.write_stat(path, value)
                    self.assert_signal_rejected()
                    value[field] -= 1
                    self.write_stat(path, value)

    def test_changed_uid_tgid_namespace_or_pid_view_stays_closed(self):
        self.remember()
        self.dead_leader()
        for field, changed in (('uid', 43), ('tgid', 999), ('namespace_pids', [999])):
            before = self.worker_status[field]
            with self.subTest(field=field):
                self.worker_status[field] = changed
                self.write_status(self.task, self.worker_status)
                self.assert_signal_rejected()
                self.worker_status[field] = before
                self.write_status(self.task, self.worker_status)
        namespace = self.task / 'ns/pid'
        namespace.unlink()
        namespace.symlink_to('pid:[222]')
        self.assert_signal_rejected()

    def test_readable_token_removal_revokes_historical_worker_proof(self):
        self.remember()
        self.dead_leader()
        (self.task / 'environ').write_bytes(b'WINEPREFIX=/private/test-wine\0')
        self.assertIsNone(self.owner.inspect(123, time.monotonic() + 1))
        self.assertEqual(self.owner.live_lineage['groups'][(123, 10)]['workers'], {})
        self.assert_signal_rejected()

    def test_readable_leader_token_removal_revokes_whole_group_proof(self):
        self.remember()
        (self.group / 'environ').write_bytes(b'WINEPREFIX=/private/test-wine\0')
        self.assertIsNone(self.owner.inspect(123, time.monotonic() + 1))
        self.assertEqual(self.owner.live_lineage['groups'], {})
        self.dead_leader()
        self.assert_signal_rejected()

    def test_prefix_mismatch_or_unreadable_authentication_records_no_proof(self):
        (self.task / 'environ').write_bytes(self.owner.needle + b'\0WINEPREFIX=/another/wine\0')
        self.remember()
        self.assertEqual(self.owner.live_lineage['groups'][(123, 10)]['workers'], {})
        self.dead_leader()
        self.assert_signal_rejected()

    def test_optional_sample_failure_does_not_poison_cleanup_receipt(self):
        with patch.object(guest.DeviceWineProcessOwner, 'lineage_environment',
                          side_effect=PermissionError(13, 'sample unavailable')):
            self.owner.observe_live_lineage(time.monotonic() + 1, prefix=self.prefix)
        self.assertEqual(self.owner.live_lineage['unavailable_samples'], 1)
        self.assertEqual(self.owner.live_lineage['groups'], {})
        self.assertEqual(self.owner.receipt['inspection_failures'], 0)
        self.assertIsNone(self.owner.receipt['last_inspection_failure'])
        self.dead_leader()
        self.assert_signal_rejected()

    def test_status_or_namespace_denial_cannot_use_environment_fallback(self):
        self.remember()
        self.dead_leader()
        for operation in ('status', 'pid_namespace', 'lineage_stat'):
            original = getattr(self.owner, operation)
            with self.subTest(operation=operation), patch.object(self.owner, operation, side_effect=lambda path:
                    (_ for _ in ()).throw(PermissionError(13, 'independent proof unavailable'))
                    if path == self.task else original(path)):
                self.assert_signal_rejected()

    def test_sampling_is_throttled_and_uses_shared_registry_with_isolated_receipts(self):
        self.remember()
        registry = self.owner.live_lineage
        clone = copy.copy(self.owner)
        clone.receipt = copy.deepcopy(self.owner.receipt)
        self.assertIs(clone.live_lineage, registry)
        with patch.object(self.owner, 'scan', side_effect=AssertionError('unthrottled scan')):
            self.owner.observe_live_lineage(time.monotonic() + 1, prefix=self.prefix)
        self.dead_leader()
        with self.deny_worker():
            self.assertIsNotNone(self.owner.inspect(123, time.monotonic() + 1))
        self.assertEqual(clone.receipt['lineage_ownership_rechecks'], 0)

    @unittest.skipIf(os.name == 'nt', 'Exact /proc task proof requires Linux')
    def test_real_pthread_leader_death_drains_only_authenticated_worker(self):
        self.real_pthread_cleanup(False)

    @unittest.skipIf(os.name == 'nt', 'Exact /proc task proof requires Linux')
    def test_real_pthread_dead_leader_worker_proof_before_shutdown(self):
        self.real_pthread_cleanup(True)

    def real_pthread_cleanup(self, authenticate_after_leader_exit):
        source = self.root / 'lineage-fixture.c'
        source.write_text('''#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <unistd.h>
static void *worker(void *arg) { (void)arg; for (;;) sleep(1); return NULL; }
int main(int argc, char **argv) {
    (void)argv; pthread_t tid;
    if (signal(SIGTERM, argc == 1 ? SIG_IGN : SIG_DFL) == SIG_ERR) return 1;
    if (pthread_create(&tid, NULL, worker, NULL)) return 2;
    if (puts("worker_ready") < 0 || fflush(stdout)) return 3;
    if (getchar() == EOF) return 4;
    pthread_exit(NULL);
}
''')
        binary = self.root / 'lineage-fixture'
        subprocess.run(['cc', '-Wall', '-Wextra', '-Werror', '-pthread', str(source), '-o', str(binary)],
                       check=True, capture_output=True, timeout=10)
        owner = guest.DeviceWineProcessOwner(self.context)
        owner.initialize()
        environment = {**os.environ, **owner.environment, 'WINEPREFIX': self.prefix}
        sentinel_environment = {**os.environ, 'WINEPREFIX': self.prefix}
        sentinel_environment.pop(owner.ENV_KEY, None)
        children = []
        try:
            owned = subprocess.Popen([str(binary)], env=environment, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            children.append(owned)
            sentinel = subprocess.Popen([str(binary), '--sentinel'], env=sentinel_environment,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            children.append(sentinel)
            for child in children:
                self.assertEqual(child.stdout.readline(), b'worker_ready\n')
            if authenticate_after_leader_exit:
                # Restrict only enumeration to these two actual children. This
                # shared development host runs other same-UID agents whose
                # namespaces are deliberately unreadable. All fixture proc
                # fields, namespaces, environments and pidfd signals remain
                # real kernel operations; the inherited test below still scans
                # full /proc in clean CI. No production exclusion is added.
                view = self.root / 'native-proc-inventory'
                view.mkdir()
                own = guest.base.WineProcessOwner.process_stat(Path('/proc/self'))
                (view / 'self').symlink_to(Path('/proc') / str(own['pid']), target_is_directory=True)
                for child in children:
                    matches = []
                    for candidate in Path('/proc').iterdir():
                        if not candidate.name.isdecimal():
                            continue
                        try:
                            status = guest.base.WineProcessOwner.status(candidate)
                            identity = guest.base.WineProcessOwner.process_stat(candidate)
                        except (OSError, ValueError, KeyError, IndexError):
                            continue
                        visible = status['namespace_pids'][-1] if status['namespace_pids'] else status['pid']
                        if (status['uid'] == owner.real_uid and visible == child.pid
                                and identity['parent'] == own['pid']):
                            matches.append(candidate)
                    self.assertEqual(len(matches), 1, 'Native child PID namespace mapping must be unique')
                    (view / matches[0].name).symlink_to(matches[0], target_is_directory=True)
                owner.proc_root = view
                owner.initialized = False
                owner.initialize()
            if not authenticate_after_leader_exit:
                owner.observe_live_lineage(time.monotonic() + 1, prefix=self.prefix)
            # PRoot/container Popen PIDs can differ from the host /proc view.
            # Use the same authenticated namespace mapping as the runtime.
            identity = [value for value in owner.scan(time.monotonic() + 1) if value['pid'] == owned.pid]
            self.assertEqual(len(identity), 1)
            group = owner.proc_root / str(identity[0]['proc_pid'])
            starttime = owner.process_stat(group)['starttime']
            if not authenticate_after_leader_exit:
                proof = owner.live_lineage['groups'].get((identity[0]['proc_pid'], starttime))
                self.assertIsNotNone(proof, owner.live_lineage['last_unavailable_type'])
                self.assertGreaterEqual(len(proof['workers']), 2)
            for child in children:
                child.stdin.write(b'x')
                child.stdin.flush()
                child.stdin.close()
            deadline = time.monotonic() + 3
            while owner.process_stat(group)['state'] != 'Z':
                self.assertLess(time.monotonic(), deadline, 'Native pthread leader did not exit')
                time.sleep(.01)
            if authenticate_after_leader_exit:
                self.assertEqual(owner.live_lineage['groups'], {})
                owner.observe_live_lineage(time.monotonic() + 1, prefix=self.prefix)
                proof = owner.live_lineage['groups'].get((identity[0]['proc_pid'], starttime))
                self.assertIsNotNone(proof, owner.live_lineage['last_unavailable_type'])
                self.assertEqual(proof['stat']['state'], 'Z')
                self.assertGreaterEqual(len(proof['workers']), 1)
            original = owner.has_token
            def denied(path):
                if path.parent.parent == group and path.parent.name == 'task':
                    raise PermissionError(13, 'simulated Android environment-only denial')
                return original(path)
            with patch.object(owner, 'has_token', side_effect=denied):
                receipt = owner.cleanup(time.monotonic() + 6)
            self.assertTrue(receipt['complete'])
            self.assertEqual((receipt['remaining'], receipt['inspection_failures']), (0, 0))
            self.assertGreaterEqual(receipt['lineage_ownership_rechecks'], 2)
            self.assertGreaterEqual(receipt['kill_signals'], 1)
            self.assertEqual(owned.wait(timeout=3), -signal.SIGKILL)
            self.assertIsNone(sentinel.poll(), 'Same-shape unrelated dead-leader sentinel must survive')
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=3)
                for stream in (child.stdin, child.stdout, child.stderr):
                    if stream is not None and not stream.closed:
                        stream.close()


if __name__ == '__main__':
    unittest.main()
