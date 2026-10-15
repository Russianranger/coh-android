"""Destination scheduler ownership, fallback, inheritance and restoration gates."""
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import character_zoning_scheduler as scheduler


class FakeScanner:
    def __init__(self, root):
        self.proc_root, self.real_uid, self.direct_pid_view = root, os.getuid(), True
        self.identities = []

    def scan(self, deadline):
        return list(self.identities)

    def inspect(self, pid, deadline):
        for row in self.identities:
            if row['proc_pid'] == pid:
                current = self.process_stat(self.proc_root / str(pid))
                return dict(row, starttime=current['starttime'])

    process_stat = staticmethod(scheduler.base.WineProcessOwner.process_stat)
    status = staticmethod(scheduler.base.WineProcessOwner.status)


class SchedulerTests(unittest.TestCase):
    def create(self, supported=True):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        owner = SimpleNamespace(wine_owner=SimpleNamespace(receipt={}), ctx=SimpleNamespace(secrets=[]))
        probe = {'supported': supported, 'original_nice': 0, 'rlimit_nice_soft': 40,
                 'lowered_nice': 5, 'restored_nice': 0}
        result = scheduler.PreparationScheduler(owner, 101, probe=probe)
        result.scanner = FakeScanner(Path(temporary.name))
        self.nice, self.writes = {}, []
        self.get_patch = patch.object(scheduler.os, 'getpriority', side_effect=lambda _kind, pid: self.nice[pid])
        def write(_kind, pid, nice):
            self.writes.append((pid, nice))
            self.nice[pid] = nice
        self.set_patch = patch.object(scheduler.os, 'setpriority', side_effect=write)
        self.get_patch.start(); self.set_patch.start()
        self.addCleanup(self.get_patch.stop); self.addCleanup(self.set_patch.stop)
        return result

    def task_files(self, path, pid, group, *, parent=1, nice=0, start=None):
        path.mkdir(parents=True, exist_ok=True)
        fields = ['S', str(parent)] + ['0'] * 22
        fields[11], fields[12], fields[16], fields[19] = '20', '10', str(nice), str(start or pid * 10)
        (path / 'stat').write_text(str(pid) + ' (private target) ' + ' '.join(fields))
        (path / 'status').write_text(f'Uid:\t{os.getuid()}\nPid:\t{pid}\nTgid:\t{group}\nVmRSS:\t128 kB\n')
        self.nice[pid] = nice

    def group(self, control, pid, *, parent=1, nice=0, token=True, tids=()):
        path = control.scanner.proc_root / str(pid)
        self.task_files(path, pid, pid, parent=parent, nice=nice)
        self.task_files(path / 'task' / str(pid), pid, pid, parent=parent, nice=nice)
        for tid in tids:
            self.task_files(path / 'task' / str(tid), tid, pid, parent=parent, nice=nice)
        (path / 'environ').write_bytes((control.needle if token else b'OTHER=foreign') + b'\0')
        (path / 'cgroup').write_text('0::/application\n')
        (path / 'autogroup').write_text('/autogroup-1 nice 0\n')
        control.scanner.identities.append({'proc_pid': pid, 'pid': pid, 'starttime': pid * 10})
        return path

    def test_unsupported_probe_does_not_change_any_task(self):
        control = self.create(False)
        self.group(control, 81001, tids=(81002,))
        control.sample(); control.restore()
        self.assertEqual(self.writes, [])
        self.assertTrue(control.report['restore_complete'])
        self.assertEqual(control.report['samples'][0]['processes'][0]['rss_kib'], 128)

    def test_no_mutation_restore_does_not_scan_inaccessible_proc(self):
        control = self.create(False)
        control.scanner.scan = lambda _: (_ for _ in ()).throw(PermissionError('unavailable'))
        control.restore()
        self.assertTrue(control.report['restore_complete'])
        self.assertEqual(self.writes, [])

    def test_private_destination_all_threads_restore_and_foreign_game_untouched(self):
        control = self.create()
        self.group(control, 81001, tids=(81002, 81003))
        self.group(control, 82001, token=False, tids=(82002,))
        control.sample()
        self.assertCountEqual(self.writes, [(81001, 5), (81002, 5), (81003, 5)])
        control.restore()
        self.assertTrue(control.report['restore_complete'])
        self.assertEqual(control.report['restored_threads'], 3)
        self.assertEqual([self.nice[p] for p in (81001, 81002, 81003, 82001, 82002)], [0]*5)
        self.assertIn('autogroup', control.report['samples'][0]['processes'][0])

    def test_new_thread_inherits_then_restores_original_not_temporary_nice(self):
        control = self.create()
        path = self.group(control, 81001)
        control.sample()
        self.task_files(path/'task'/'81002', 81002, 81001, nice=5)
        control.restore()
        self.assertEqual(self.nice[81002], 0)
        self.assertEqual(control.report['restored_threads'], 2)

    def test_zombie_leader_uses_verified_live_worker_environment(self):
        control = self.create()
        path = self.group(control, 81001, tids=(81002,))
        worker = path/'task'/'81002'
        (worker/'environ').write_bytes(control.needle + b'\0')
        for location in (path, path/'task'/'81001'):
            stat = location/'stat'
            stat.write_text(stat.read_text().replace(') S ', ') Z '))
        (path/'environ').write_bytes(b'')
        control.scanner.live_tasks = lambda _path, _deadline: iter([(worker, control.scanner.process_stat(worker))])
        control.scanner.has_token = lambda _task: True
        control.sample(); control.restore()
        self.assertEqual(self.writes, [(81002, 5), (81002, 0)])
        self.assertTrue(control.report['restore_complete'])

    def test_new_child_process_tracks_exact_changed_parent_without_double_lowering(self):
        control = self.create()
        self.group(control, 81001)
        control.sample()
        self.group(control, 82001, parent=81001, nice=5)
        control.next_sample = control.next_discovery = 0
        control.sample()
        self.assertNotIn((82001, 10), self.writes)
        control.restore()
        self.assertEqual(self.nice[82001], 0)

    def test_unattributed_orphan_inheritance_never_claims_restored_or_ready(self):
        control = self.create()
        self.group(control, 81001)
        control.sample()
        self.group(control, 82001, parent=1, nice=5)
        with self.assertRaises(scheduler.base.DiagnosticError):
            control.restore()
        self.assertFalse(control.report['restore_complete'])
        self.assertNotIn((82001, 0), self.writes)

    def test_new_thread_during_restore_is_found_in_stable_followup_pass(self):
        control = self.create()
        path = self.group(control, 81001)
        control.sample()
        original_set = scheduler.os.setpriority.side_effect
        def concurrent(_kind, tid, nice):
            if tid == 81001 and nice == 0 and 81002 not in self.nice:
                self.task_files(path/'task'/'81002', 81002, 81001, nice=5)
            original_set(_kind, tid, nice)
        scheduler.os.setpriority.side_effect = concurrent
        control.restore()
        self.assertEqual(self.nice[81002], 0)
        self.assertEqual(control.report['restored_threads'], 2)

    def test_heterogeneous_initial_group_stays_unchanged(self):
        control = self.create()
        path = self.group(control, 81001, tids=(81002,))
        self.nice[81002] = 1
        control.sample(); control.restore()
        self.assertEqual(self.writes, [])

    def test_pid_reuse_and_foreign_token_block_restore_syscall(self):
        for foreign in ('starttime', 'token'):
            control = self.create()
            path = self.group(control, 81001)
            control.sample()
            if foreign == 'starttime':
                self.task_files(path, 81001, 81001, start=999, nice=5)
            else:
                (path/'environ').write_bytes(b'FOREIGN=1\0')
            with self.subTest(foreign=foreign), self.assertRaises(scheduler.base.DiagnosticError):
                control.restore()
            self.assertNotIn((81001, 0), self.writes)
            self.assertFalse(control.report['restore_complete'])

    def test_denied_restoration_does_not_claim_success(self):
        control = self.create()
        self.group(control, 81001)
        control.sample()
        scheduler.os.setpriority.side_effect = PermissionError('denied')
        with self.assertRaises(PermissionError):
            control.restore()
        self.assertFalse(control.report['restore_complete'])

    def test_no_permission_probe_never_attempts_lower(self):
        with patch.object(scheduler.os, 'getpriority', return_value=0), \
             patch.object(scheduler.resource, 'getrlimit', return_value=(0, 0)), \
             patch.object(scheduler.os, 'setpriority') as setter:
            self.assertFalse(scheduler.priority_probe()['supported'])
            setter.assert_not_called()

    def test_actual_isolated_host_capability_probe_never_changes_parent(self):
        before = os.getpriority(os.PRIO_PROCESS, 0)
        result = scheduler.checked_probe()
        self.assertIs(type(result['supported']), bool)
        self.assertEqual(os.getpriority(os.PRIO_PROCESS, 0), before)
        if result['supported']:
            self.assertEqual(result['restored_nice'], before)

    def test_pid_namespace_mapping_targets_guest_tid_not_proc_host_tid(self):
        control = self.create()
        path = self.group(control, 81001)
        control.scanner.direct_pid_view = False
        control.scanner.namespace_depth = 2
        control.scanner.identities[0]['pid'] = 321
        task = path/'task'/'81001'/'status'
        task.write_text(task.read_text() + 'NSpid:\t81001\t321\n')
        self.nice[321] = 0
        control.sample(); control.restore()
        self.assertEqual(self.writes, [(321, 5), (321, 0)])
        self.assertEqual(self.nice[81001], 0)


class ActualOwnershipTests(unittest.TestCase):
    def test_actual_device_scanner_excludes_shared_run_process_and_keeps_all_target_threads(self):
        import game_device_diagnostic as device
        context = SimpleNamespace(secrets=[])
        owner = SimpleNamespace(ctx=context, wine_owner=device.DeviceWineProcessOwner(context))
        control = scheduler.PreparationScheduler(owner, 101, probe={'supported': False})
        program = ('import threading,time; '
            'threading.Thread(target=lambda:time.sleep(30),daemon=True).start(); '
            'print("ready",flush=True); time.sleep(30)')
        children = []
        try:
            for extra in ({}, control.environment):
                env = dict(os.environ, **owner.wine_owner.environment, **extra)
                child = subprocess.Popen([sys.executable, '-c', program], env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
                children.append(child)
                self.assertEqual(child.stdout.readline(), b'ready\n')
            before = [os.getpriority(os.PRIO_PROCESS, child.pid) for child in children]
            rows = []
            for _ in range(3):
                control.next_sample = control.next_discovery = 0
                control.sample()
                if control.report['samples']:
                    rows = control.report['samples'][-1]['processes']
                if rows:
                    break
            self.assertEqual([row['pid'] for row in rows], [children[1].pid])
            self.assertGreaterEqual(len(rows[0]['tasks']), 2)
            control.restore()
            self.assertEqual([os.getpriority(os.PRIO_PROCESS, child.pid) for child in children], before)
            self.assertEqual(control.report['changed_threads'], 0)
        finally:
            for child in children:
                child.terminate(); child.wait(timeout=3)
                child.stdout.close(); child.stderr.close()


if __name__ == '__main__':
    unittest.main()
