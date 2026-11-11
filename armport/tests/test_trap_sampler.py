"""The CI host's read-only sampler of guest tasks stopped for PRoot (0.13.69)."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'armport/app'))
import trap_sampler


def task(proc, pid, tid, comm, state, parent, syscall=None, cmdline=None, tracer=0):
    base = proc / str(pid)
    (base / 'task' / str(tid)).mkdir(parents=True, exist_ok=True)
    line = '%d (%s) %s %d 0 0 0\n' % (tid, comm, state, parent)
    if pid == tid:
        (base / 'stat').write_text(line)
        (base / 'status').write_text('Name:\t%s\nTracerPid:\t%d\n' % (comm, tracer))
        (base / 'cmdline').write_bytes((cmdline or '').encode() + b'\0')
    (base / 'task' / str(tid) / 'stat').write_text(line)
    if syscall is not None:
        (base / 'task' / str(tid) / 'syscall').write_text(syscall)


class TrapSamplerTest(unittest.TestCase):
    def tree(self, proc):
        task(proc, 100, 100, 'libproot.so', 'S', 1, cmdline='/data/app/lib/libproot.so')
        task(proc, 101, 101, 'python3', 't', 100, '56 0xffffff9c 0x7f 0x0 0x0 0x0 0x0 0x7ffd 0x7f01\n',
             cmdline='/usr/bin/python3', tracer=100)
        # Wine starts a program through two forks: its parent is init, PRoot still traces it.
        task(proc, 150, 150, 'MapServer.exe', 't', 1, '48 0x0\n', cmdline='Z:\\state\\MapServer.exe', tracer=100)
        task(proc, 151, 151, 'other-traced', 't', 1, '56 0x0\n', cmdline='/bin/debugged', tracer=999)
        task(proc, 102, 102, 'CityOfHeroes.ex', 'R', 101, cmdline='Z:\\state\\client\\CityOfHeroes.exe')
        task(proc, 102, 103, 'CityOfHe:gl0', 't', 101, '79 0x3 0x7f 0x0\n')
        task(proc, 102, 104, 'wine (odd) name', 't', 101, '-1 0x7ffd 0x7f01\n')
        task(proc, 102, 105, 'gone', 't', 101)                      # no syscall file: counted, not fatal
        task(proc, 200, 200, 'unrelated', 't', 1, '56 0x0\n', cmdline='/bin/other')   # not below the guest
        (proc / 'self').mkdir()                                     # non-numeric entries are skipped
        (proc / '300').mkdir()                                      # a process that exited mid-scan

    def test_stat_line_with_spaces_and_parentheses_in_the_name(self):
        self.assertEqual(trap_sampler.stat_fields('7 (a (b) c) t 3 0 0'), ('a (b) c', 't', 3))

    def test_one_burst_counts_states_and_the_calls_of_stopped_tasks(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            self.tree(proc)
            pids = trap_sampler.descendants(proc, 100)
            self.assertEqual(sorted(pids), [100, 101, 102, 150])
            lines = []
            sampler = trap_sampler.TrapSampler(100, 'reopen', proc=proc, rounds=3, gap=0, emit=lines.append)
            window = sampler.empty()
            sampler.burst(window)
            self.assertEqual((window['rounds'], window['processes'], window['unreadable']), (3, 4, 0))
            self.assertEqual(window['states'], {'libproot.so': {'S': 3}, 'python3': {'t': 3},
                                                'CityOfHeroes.exe': {'R': 3, 't': 9}, 'MapServer.exe': {'t': 3}})
            self.assertEqual(window['stops'], {'python3 56': 3, 'CityOfHeroes.exe 79': 3, 'MapServer.exe 48': 3,
                                               'CityOfHeroes.exe -1': 3, 'CityOfHeroes.exe unreadable': 3})
            sampler.flush(window, 0.0)
            self.assertEqual(len(lines), 1)
            self.assertTrue(lines[0].startswith(trap_sampler.MARK))
            record = json.loads(lines[0][len(trap_sampler.MARK):])
            self.assertEqual((record['session'], record['rounds'], record['stopped_tasks'], record['other_stops']),
                             ('reopen', 3, 15, 0))
            self.assertEqual(record['stops'][0][1], 3)
            self.assertLess(len(lines[0]), 4000)

    def test_summary_is_bounded(self):
        window = trap_sampler.TrapSampler.empty()
        window['rounds'] = 1
        for index in range(100):
            window['stops']['program%d %d' % (index, index)] = index + 1
            window['states']['program%d' % index] = {'t': index + 1}
        record = trap_sampler.summary(window, 0.0, 1.0)
        self.assertEqual((len(record['stops']), len(record['states'])), (trap_sampler.TOP, trap_sampler.TOP))
        self.assertEqual(record['stops'][0], ('program99 99', 100))
        self.assertEqual(record['other_stops'] + sum(count for _, count in record['stops']), 5050)

    def test_thread_stops_and_reports_a_guest_that_already_exited(self):
        with tempfile.TemporaryDirectory() as directory:
            lines = []
            sampler = trap_sampler.TrapSampler(4242, 'creation', proc=Path(directory), rounds=1, gap=0, pause=0.01,
                                               window=0.0, emit=lines.append)
            sampler.start()
            result = sampler.finish()
            self.assertFalse(sampler.is_alive())
            self.assertEqual(result['requested'], True)
            self.assertEqual(result['lines'], len(lines))

    def test_privileged_child_command_and_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            stop = Path(directory) / 'stop'
            calls = []

            class Child:
                def wait(self, timeout):
                    calls.append(('wait', stop.exists()))
                    return 0

            def popen(command):
                calls.append(command)
                return Child()
            sampler = trap_sampler.PrivilegedSampler(4242, 'reopen', stop, popen=popen)
            sampler.start()
            self.assertEqual(calls[0][:2], ['sudo', '-n'])
            self.assertEqual(calls[0][3:], [str(ROOT / 'armport/app/trap_sampler.py'), '--root-pid', '4242',
                                            '--label', 'reopen', '--stop-file', str(stop)])
            result = sampler.finish()
            self.assertEqual(calls[1], ('wait', True))          # the stop file exists while the child is awaited
            self.assertFalse(stop.exists())
            self.assertEqual((result['privileged'], result['exit_code']), (True, 0))

    def test_child_main_ends_with_the_stop_file_or_the_guest(self):
        with tempfile.TemporaryDirectory() as directory:
            stop = Path(directory) / 'stop'
            started = time.monotonic()
            # No such first process: the loop ends at once.
            self.assertEqual(trap_sampler.main(['--root-pid', '999999999', '--label', 'creation',
                                                '--stop-file', str(stop)]), 0)
            stop.write_text('stop')
            self.assertEqual(trap_sampler.main(['--root-pid', str(os.getpid()), '--label', 'creation',
                                                '--stop-file', str(stop)]), 0)
            self.assertLess(time.monotonic() - started, 20)

    def test_sudo_probe_never_raises(self):
        def missing(*args, **kwargs):
            raise FileNotFoundError('sudo')
        self.assertIs(trap_sampler.sudo_available(missing), False)
        self.assertIs(trap_sampler.sudo_available(lambda *a, **k: mock.Mock(returncode=1)), False)
        self.assertIs(trap_sampler.sudo_available(lambda *a, **k: mock.Mock(returncode=0)), True)

    def test_option_values(self):
        for value, expected in (('', False), ('0', False), ('1', True)):
            with mock.patch.dict(os.environ, {trap_sampler.ENV: value}):
                self.assertIs(trap_sampler.requested(), expected)
        with mock.patch.dict(os.environ, {trap_sampler.ENV: 'yes'}), self.assertRaises(ValueError):
            trap_sampler.requested()

    def test_host_and_workflow_carry_the_option(self):
        host = (ROOT / 'armport/app/interactive_host.py').read_text()
        self.assertIn("trap_sampler.start(process.pid, 'reopen' if reopening else 'creation',", host)
        self.assertLess(host.index('sampled = sampler.finish()'), host.index("cleanup = character.stop_guest(process"))
        workflow = (ROOT / '.github/workflows/armport-app-runtime.yml').read_text()
        self.assertIn("COH_TRAP_SAMPLER: ${{ inputs.trap_sampler && '1' || '' }}", workflow)


if __name__ == '__main__':
    unittest.main()
