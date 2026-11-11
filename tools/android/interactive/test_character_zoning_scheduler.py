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

    def test_idle_token_weights_only_its_resident_map_by_ten_and_restores(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        owner = SimpleNamespace(wine_owner=SimpleNamespace(receipt={}), ctx=SimpleNamespace(secrets=['a' * 64]))
        probe = {'supported': True, 'original_nice': 0, 'rlimit_nice_soft': 40, 'lowered_nice': 5, 'restored_nice': 0}
        self.create()   # installs the priority patches
        control = scheduler.PreparationScheduler(owner, 1, probe=probe, token='a' * 64,
            environment_name=scheduler.IDLE_ENVIRONMENT, increment=scheduler.IDLE_NICE_INCREMENT,
            policy='idle_resident_plus_10_nice', sample_limit=scheduler.IDLE_SAMPLE_LIMIT)
        control.scanner = FakeScanner(Path(temporary.name))
        self.assertEqual(owner.ctx.secrets, ['a' * 64])
        self.assertEqual(control.needle, b'COH_ZONING_IDLE_OWNER=' + b'a' * 64)
        self.group(control, 81001, tids=(81002,))
        foreign = self.group(control, 82001)
        (foreign / 'environ').write_bytes(b'COH_ZONING_PREPARATION_OWNER=' + b'a' * 64 + b'\0')
        control.sample()
        self.assertCountEqual(self.writes, [(81001, 10), (81002, 10)])
        self.assertEqual((control.report['policy'], control.report['nice_increment']), ('idle_resident_plus_10_nice', 10))
        control.restore()
        self.assertEqual([self.nice[p] for p in (81001, 81002, 82001)], [0, 0, 0])
        self.assertTrue(control.report['restore_complete'])
        for _ in range(40):
            control.next_sample = 0; control.sample()
        self.assertLessEqual(len(control.report['samples']), scheduler.IDLE_SAMPLE_LIMIT)

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


class WinePrioritySnapshotTests(unittest.TestCase):
    """Read-only evidence: thread nice values per Wine program."""
    def fake_proc(self, root, pid, command, tasks):
        directory = root / str(pid); (directory / 'task').mkdir(parents=True)
        (directory / 'cmdline').write_bytes(command)
        for tid, state, nice, *cpu in tasks:
            task = directory / 'task' / str(tid); task.mkdir()
            # stat fields 3.., nice is field 19 (index 16), processor field 39 (index 36).
            # utime and stime are fields 14 and 15 (indexes 11 and 12): tid ticks of each here.
            fields = ([state] + ['0'] * 10 + [str(tid), str(tid)] + ['0'] * 3 + [str(nice)] + ['0'] * 19
                      + [str(cpu[0] if cpu else 0)] + ['0'] * 10)
            (task / 'stat').write_text(str(tid) + ' (wine) name) ' + ' '.join(fields) + '\n')

    def test_counts_threads_per_nice_for_known_programs_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fake_proc(root, 10, b'/usr/bin/FEXInterpreter\0C:\\coh\\CityOfHeroes.exe\0-noaudio\0',
                           [(10, 'S', 0), (11, 'S', 11), (12, 'R', 11), (13, 'Z', 11)])
            self.fake_proc(root, 20, b'C:\\srv\\MapServer.exe\0', [(20, 'S', 0, 7), (21, 'S', 0, 2)])
            self.fake_proc(root, 30, b'/opt/wine/bin/wineserver\0', [(30, 'S', 0)])
            self.fake_proc(root, 40, b'/usr/bin/python3\0guest.py\0', [(40, 'S', 0)])
            (root / 'self').mkdir()
            # 0.13.67: where each program may run, and which threads use the CPU.
            (root / '10/status').write_text('Name:\twine\nCpus_allowed:\t7f\nCpus_allowed_list:\t0-6\n')
            (root / '10/cgroup').write_text('3:cpuset:/foreground\n1:cpu:/\n')
            (root / 'self/status').write_text('Name:\tpython3\nCpus_allowed_list:\t0-7\n')
            (root / 'meminfo').write_text('MemTotal:       15620000 kB\nMemAvailable:   10240000 kB\n'
                                          'SwapTotal:       8388604 kB\nSwapFree:        4194302 kB\n')
            # 0.13.69: context switches of the busiest threads (waiting or computing?).
            (root / '10/task/12/status').write_text('Name:\twine\nvoluntary_ctxt_switches:\t9000\n'
                                                    'nonvoluntary_ctxt_switches:\t41\n')
            (root / '10/task/11/status').write_text('Name:\twine\nvoluntary_ctxt_switches:\tmany\n')
            value = scheduler.wine_priority_snapshot(root)
        self.assertEqual(value['programs']['CityOfHeroes.exe'],
                         {'processes': 1, 'threads': 3, 'nice': {'0': 1, '11': 2}, 'last_cpu': {'0': 3},
                          'busiest_threads': [[24, 'wine) name', 0, 11, 9000, 41], [22, 'wine) name', 0, 11, None, None],
                                              [20, 'wine) name', 0, 0, None, None]],
                          'cpus_allowed': ['0-6'], 'cgroup': ['3:cpuset:/foreground']})
        self.assertEqual(value['programs']['MapServer.exe'],
                         {'processes': 1, 'threads': 2, 'nice': {'0': 2}, 'last_cpu': {'2': 1, '7': 1},
                          'busiest_threads': [[42, 'wine) name', 2, 0, None, None], [40, 'wine) name', 7, 0, None, None]],
                          'cpus_allowed': [], 'cgroup': []})
        self.assertEqual(value['guest'], {'cpus_allowed': '0-7', 'cgroup': None})
        self.assertEqual(value['memory'], {'MemTotal': 15253, 'MemAvailable': 10000, 'SwapTotal': 8191,
                                           'SwapFree': 4095, 'pressure': None})
        self.assertEqual(set(value['programs']), {'CityOfHeroes.exe', 'MapServer.exe', 'wineserver'})
        self.assertEqual(value['processes_scanned'], 4)
        self.assertFalse(value['truncated'])
        self.assertEqual(len(value['rlimit_nice']), 2)

    def test_cpu_max_frequencies_tell_clusters_apart_and_hidden_sysfs_is_none(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for cpu, khz in ((0, 2016000), (1, 2016000), (3, 2803200), (7, 3187200)):
                path = root / ('cpu%d' % cpu) / 'cpufreq'; path.mkdir(parents=True)
                (path / 'cpuinfo_max_freq').write_text(str(khz) + '\n')
            (root / 'cpu2').mkdir()   # online CPU without cpufreq
            for cpu in (4, 5, 6):
                (root / ('cpu%d' % cpu)).mkdir()
            self.assertEqual(scheduler.cpu_max_khz(root), {'0': 2016000, '1': 2016000, '3': 2803200, '7': 3187200})
            self.assertIsNone(scheduler.cpu_max_khz(root / 'missing'))

    def test_foreign_uid_vanished_and_malformed_entries_are_skipped_and_bounds_hold(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fake_proc(root, 10, b'MapServer.exe', [(10, 'S', 0)])
            (root / '11').mkdir()  # vanished: no cmdline
            self.fake_proc(root, 12, b'MapServer.exe', [(12, 'S', 0)])
            (root / '12/task/12/stat').write_text('garbage')
            value = scheduler.wine_priority_snapshot(root, uid=os.getuid() + 1)
            self.assertEqual(value['programs'], {})
            value = scheduler.wine_priority_snapshot(root)
            self.assertEqual(value['programs']['MapServer.exe']['threads'], 1)
            with patch.object(scheduler, 'PRIORITY_PROCESS_LIMIT', 1):
                self.assertTrue(scheduler.wine_priority_snapshot(root)['truncated'])


if __name__ == '__main__':
    unittest.main()
