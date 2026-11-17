"""0.13.69: the guest's ioctl probe and CI's gate for PRoot's ioctl command filter (patch 0004).

Measured with a locally built PRoot (x86-64, pinned tree with patches 0001-0004, 2026-11-11):
without the switch getppid 0.15, FIONREAD 0.23, TCGETS2 0.78 microseconds per call; with
PROOT_IOCTL_COMMANDS_ONLY=1 0.20, 0.43 and 55.89. The checked-in functions are executed
unchanged, without importing the guest modules they live beside.
"""
import ast
import errno
import fcntl
import os
from pathlib import Path
import socket
import struct
import termios
import time
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
GUEST = ROOT / 'armport/app/armport_interactive.py'
HOST = ROOT / 'armport/app/interactive_host.py'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_probe(ioctl=None, clock=None):
    tree = ast.parse(GUEST.read_text())
    wanted = [node for node in tree.body
              if (isinstance(node, ast.Assign) and any(getattr(t, 'id', '').startswith('IOCTL_') for t in node.targets))
              or (isinstance(node, ast.FunctionDef) and node.name == 'proot_ioctl_probe')]
    assert len(wanted) == 4
    fake_fcntl = types.SimpleNamespace(ioctl=ioctl or fcntl.ioctl)
    namespace = {'os': os, 'errno': errno, 'fcntl': fake_fcntl, 'struct': struct, 'termios': termios,
                 'time': time, 'require': require, 'socket': socket}
    exec(compile(ast.Module(body=wanted, type_ignores=[]), str(GUEST), 'exec'), namespace)
    return namespace


def load_gate(requested, name='require_proot_ioctl_filter'):
    tree = ast.parse(HOST.read_text())
    wanted = [node for node in tree.body if (isinstance(node, ast.FunctionDef) and node.name == name)
              or (isinstance(node, ast.Assign) and getattr(node.targets[0], 'id', '') == 'NETLINK_DESCRIPTOR_FLOOR')]
    assert len(wanted) == 2
    runtime = types.SimpleNamespace(proot_ioctl_filter_requested=lambda: requested)
    namespace = {'require': require, 'runtime_host': types.SimpleNamespace(runtime=runtime)}
    exec(compile(ast.Module(body=wanted, type_ignores=[]), str(HOST), 'exec'), namespace)
    return namespace[name]


class Simulated:
    """A clock that advances by a fixed cost per call kind (microseconds)."""

    def __init__(self, costs):
        self.costs, self.now = costs, 0.0

    def clock(self):
        self.now += self.costs['getppid'] / 1e6 / 2      # two reads per loop cancel out of the difference
        return self.now

    def ioctl(self, descriptor, command, buffer):
        if command == termios.FIONREAD:
            self.now += self.costs['fionread'] / 1e6
            buffer[:4] = struct.pack('i', 3)
            return 0
        self.now += self.costs['tcgets2'] / 1e6
        raise OSError(errno.ENOTTY, 'not a terminal')


class ProbeTest(unittest.TestCase):
    def reading(self, costs):
        simulated = Simulated(costs)
        probe = load_probe(simulated.ioctl)['proot_ioctl_probe']
        return probe(calls=50, clock=simulated.clock)

    def test_host_without_a_tracer_reads_no_stops(self):
        result = load_probe()['proot_ioctl_probe']()
        self.assertEqual(result['reading'], 'no_ioctl_stops', result)
        self.assertEqual(set(result['microseconds_per_call']),
                         {'getppid', 'fionread', 'tcgets2', 'getsockopt', 'send_recv'})
        self.assertIs(result['getsockopt_stops'], False)
        # 0.13.73 (patch 0007): an ordinary send and receive, and where a rtnetlink socket lands.
        self.assertIs(result['socket_stops'], False)
        self.assertIs(result['socket_filter_requested'], False)
        self.assertTrue(type(result.get('netlink_descriptor')) is int or 'netlink_error_type' in result, result)
        self.assertIs(result['is_success_proof'], False)

    def test_the_three_cases_are_told_apart(self):
        self.assertEqual(self.reading({'getppid': 0.2, 'fionread': 0.4, 'tcgets2': 0.9})['reading'], 'no_ioctl_stops')
        self.assertEqual(self.reading({'getppid': 0.2, 'fionread': 0.4, 'tcgets2': 55.9})['reading'],
                         'listed_commands_only')
        self.assertEqual(self.reading({'getppid': 0.5, 'fionread': 90.0, 'tcgets2': 95.0})['reading'],
                         'every_ioctl_stops')
        self.assertEqual(self.reading({'getppid': 0.5, 'fionread': 90.0, 'tcgets2': 1.0})['reading'], 'inconsistent')

    def test_request_is_recorded_as_the_launcher_passed_it(self):
        # Run 43065755111: the guest's environment is cleared, so PRoot's own switch is not visible.
        with mock.patch.dict(os.environ, {'COH_PROOT_IOCTL_FILTER': '1'}):
            self.assertIs(load_probe()['proot_ioctl_probe'](calls=5)['requested'], True)
        with mock.patch.dict(os.environ, {'COH_PROOT_IOCTL_FILTER': '0', 'PROOT_IOCTL_COMMANDS_ONLY': '1'}):
            self.assertIs(load_probe()['proot_ioctl_probe'](calls=5)['requested'], False)
        with mock.patch.dict(os.environ, {'COH_PROOT_SOCKET_FILTER': '1'}):
            self.assertIs(load_probe()['proot_ioctl_probe'](calls=5)['socket_filter_requested'], True)
        with mock.patch.dict(os.environ, {'COH_PROOT_SOCKET_FILTER': '0', 'PROOT_NETLINK_HIGH_FDS': '1'}):
            self.assertIs(load_probe()['proot_ioctl_probe'](calls=5)['socket_filter_requested'], False)

    def test_an_unexpected_error_is_a_record_not_a_failure(self):
        def broken(descriptor, command, buffer):
            raise OSError(errno.EPERM, 'refused')
        result = load_probe(broken)['proot_ioctl_probe'](calls=5)
        self.assertEqual((result['reading'], result['error_type']), ('unavailable', 'PermissionError'))

    def test_pipe_is_closed(self):
        before = set(os.listdir('/proc/self/fd'))
        load_probe()['proot_ioctl_probe'](calls=5)
        self.assertEqual(set(os.listdir('/proc/self/fd')), before)


class GateTest(unittest.TestCase):
    def test_without_the_input_nothing_is_required(self):
        load_gate(False)({})

    GOOD = {'reading': 'listed_commands_only', 'requested': True, 'getsockopt_stops': False,
            'socket_filter_requested': True, 'socket_stops': False, 'netlink_descriptor': 960}

    def test_filter_at_work_passes(self):
        gate = load_gate(True)
        gate({'armport_proot_ioctl': self.GOOD})
        gate({'armport_proot_ioctl': dict(self.GOOD, netlink_descriptor=1031)})
        # A guest that may not open a rtnetlink socket at all has nothing to place.
        without = {key: value for key, value in self.GOOD.items() if key != 'netlink_descriptor'}
        gate({'armport_proot_ioctl': dict(without, netlink_error_type='PermissionError')})

    def test_other_readings_fail(self):
        gate = load_gate(True)
        good = self.GOOD
        for probe in (None, dict(good, reading='no_ioctl_stops'), dict(good, reading='every_ioctl_stops'),
                      dict(good, requested=False), {'reading': 'unavailable'},
                      {key: value for key, value in good.items() if key != 'getsockopt_stops'},
                      dict(good, getsockopt_stops=True),
                      # 0.13.73 (patch 0007)
                      dict(good, socket_stops=True), dict(good, socket_filter_requested=False),
                      {key: value for key, value in good.items() if key != 'socket_stops'},
                      dict(good, netlink_descriptor=3), dict(good, netlink_descriptor=959),
                      dict(good, netlink_descriptor='960')):
            with self.subTest(probe=probe), self.assertRaises(RuntimeError):
                gate({} if probe is None else {'armport_proot_ioctl': probe})

    def test_ci_passes_the_request_into_the_guest(self):
        host = HOST.read_text()
        self.assertIn("command.insert(command.index('/usr/bin/python3'), 'COH_PROOT_IOCTL_FILTER=1')", host)
        java = (ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/'
                'ClientRuntime.java').read_text()
        self.assertIn('"COH_PROOT_IOCTL_FILTER="+(prootIoctlFilterUsed?"1":"0")', java)
        self.assertIn("command.insert(command.index('/usr/bin/python3'), 'COH_PROOT_SOCKET_FILTER=1')", host)
        self.assertIn('"COH_PROOT_SOCKET_FILTER="+(prootSocketFilterUsed?"1":"0")', java)

    def test_workflow_passes_the_switch(self):
        workflow = (ROOT / '.github/workflows/armport-app-runtime.yml').read_text()
        self.assertIn("COH_PROOT_IOCTL_FILTER: ${{ inputs.proot_ioctl_filter && '1' || '' }}", workflow)


class LaunchReceiptsLineTest(unittest.TestCase):
    """0.13.73: what each launch receipt decided, in the CI log (Thor 0.13.72 never reused one)."""

    def line(self, report):
        import json
        tree = ast.parse(HOST.read_text())
        wanted = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'launch_receipts_line']
        self.assertEqual(len(wanted), 1)
        namespace = {'json': json}
        exec(compile(ast.Module(body=wanted, type_ignores=[]), str(HOST), 'exec'), namespace)
        text = namespace['launch_receipts_line'](report, 'reopen')
        self.assertTrue(text.startswith('LAUNCH_RECEIPTS_V1 {'))
        return json.loads(text.split(' ', 1)[1])

    def test_line(self):
        value = self.line({'launch_receipts': {
            'zone_graph_71': {'status': 'reused', 'reason': None, 'elapsed_seconds': 0.4},
            'atlas_world': {'status': 'ran_in_full', 'reason': 'directory_changed: data/server' + 'x' * 200},
            7: {'status': 'reused'}, 'bad': 'row'}})
        self.assertEqual(value['session'], 'reopen')
        self.assertEqual(value['steps']['zone_graph_71'], ['reused', None, 0.4])
        self.assertEqual(value['steps']['atlas_world'][0], 'ran_in_full')
        self.assertEqual(len(value['steps']['atlas_world'][1]), 80)
        self.assertEqual(set(value['steps']), {'zone_graph_71', 'atlas_world'})
        self.assertEqual(self.line({})['steps'], {})
        self.assertEqual(self.line({'launch_receipts': []})['steps'], {})


class ThreadWaitsLineTest(unittest.TestCase):
    """0.13.73: the guest's thread-wait bursts, one line in the CI log."""

    def line(self, report):
        import json
        tree = ast.parse(HOST.read_text())
        wanted = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'thread_waits_line']
        self.assertEqual(len(wanted), 1)
        namespace = {'json': json}
        exec(compile(ast.Module(body=wanted, type_ignores=[]), str(HOST), 'exec'), namespace)
        text = namespace['thread_waits_line'](report, 'reopen')
        self.assertTrue(text.startswith('THREAD_WAITS_V1 {'))
        return json.loads(text.split(' ', 1)[1])

    def test_line(self):
        self.assertEqual(self.line({}), {'format': 1, 'session': 'reopen', 'bursts': None})
        self.assertEqual(self.line({'character_zoning': {'thread_waits': {'bursts': [], 'error': None,
                                                                         'skipped_not_in_world': 3}}}),
                         {'format': 1, 'session': 'reopen', 'bursts': 0, 'skipped_not_in_world': 3, 'error': None})
        burst = {'utc': '2026-11-17T13:20:00Z', 'rounds': 40, 'seconds': 2.1, 'call_files': 50, 'wchan_files': 50,
                 'unreadable': 0, 'programs': {'client': {'pid': 9, 'threads': 50, 'cpu_percent': 93.0, 'busiest': [
                     {'name': 'gdrv0', 'cpu_percent': 28.0, 'samples': 40, 'running': 9, 'stopped_in_proot': 2,
                      'waits': [[False, 'ioctl', '0xc0200947', 'kgsl_wait', 25], [False, 'futex', 'op=9', None, 4]]}] * 6}}}
        value = self.line({'character_zoning': {'thread_waits': {'bursts': ['bad', burst], 'error': None}}})
        self.assertEqual(value['bursts'], 1)
        client = value['last']['programs']['client']
        self.assertEqual((client['threads'], client['cpu_percent'], len(client['busiest'])), (50, 93.0, 4))
        self.assertEqual(client['busiest'][0], ['gdrv0', 28.0, 9, 2, [False, 'ioctl', '0xc0200947', 'kgsl_wait', 25]])


class StopCountsTest(unittest.TestCase):
    """0.13.70: PRoot's own stop counts (patch 0005), read by the CI host after the guest ends."""

    def reader(self):
        tree = ast.parse(HOST.read_text())
        wanted = [node for node in tree.body
                  if (isinstance(node, ast.Assign) and any(getattr(t, 'id', '').startswith('STOP_COUNTS_') for t in node.targets))
                  or (isinstance(node, ast.FunctionDef) and node.name == 'proot_stop_counts')]
        self.assertEqual(len(wanted), 3)
        namespace = {'Path': Path}
        exec(compile(ast.Module(body=wanted, type_ignores=[]), str(HOST), 'exec'), namespace)
        return namespace

    def test_file_is_read_sorted_and_bounded(self):
        import tempfile
        namespace = self.reader()
        with tempfile.TemporaryDirectory() as work:
            self.assertIsNone(namespace['proot_stop_counts'](work))
            (Path(work) / namespace['STOP_COUNTS_NAME']).write_text(
                'PROOT_STOP_COUNTS_V1 seconds=412 stops=1009\n56 300 0\n79 350 350\n57 9 0\nnot a row\n'
                'P wineserver 79 400\nP MapServer.exe 79 300\nP python3 56 300\nP bad x 1\n')
            counts = namespace['proot_stop_counts'](work, top=2)
            self.assertEqual((counts['valid'], counts['seconds'], counts['stops']), (True, 412, 1009))
            self.assertEqual(counts['calls'], [[79, 350, 350], [56, 300, 0]])
            self.assertEqual(counts['other_stops'], 9)
            self.assertEqual(counts['programs'], [['wineserver', 79, 400], ['MapServer.exe', 79, 300]])
            self.assertEqual([counts[key] for key in ('fd_stats', 'moved_netlink_fds', 'failed_netlink_moves')],
                             [None, None, None])                     # an older PRoot writes none of them
            (Path(work) / namespace['STOP_COUNTS_NAME']).write_text(
                'PROOT_STOP_COUNTS_V1 seconds=9 stops=40 fd_stats=12 moved_netlink_fds=3 failed_netlink_moves=0\n'
                '79 20 20\n')
            counts = namespace['proot_stop_counts'](work)
            self.assertEqual([counts[key] for key in ('stops', 'fd_stats', 'moved_netlink_fds', 'failed_netlink_moves')],
                             [40, 12, 3, 0])
            (Path(work) / namespace['STOP_COUNTS_NAME']).write_text('something else\n')
            self.assertEqual(namespace['proot_stop_counts'](work), {'format': 1, 'valid': False})

    def test_gate(self):
        load_gate(False, 'require_proot_stop_counts')(None)
        gate = load_gate(True, 'require_proot_stop_counts')
        gate({'valid': True, 'stops': 5, 'calls': [[56, 5, 0]]})
        for counts in (None, {'valid': False}, {'valid': True, 'stops': 0, 'calls': []}):
            with self.subTest(counts=counts), self.assertRaises(RuntimeError):
                gate(counts)

    def test_names_and_switches_agree(self):
        launcher = (ROOT / 'tools/android/dbserver/run_isolated_network.py').read_text()
        self.assertIn('STOP_COUNTS_NAME = "proot-stop-counts.txt"', launcher)
        self.assertIn('environment["PROOT_GETSOCKOPT_PEERCRED_ONLY"] = "1"', launcher)
        self.assertIn('environment["PROOT_ACCEPT_UNTRACED"] = "1"', launcher)
        later = (ROOT / 'android/native/proot/0006-accept-untraced-program-counts.patch').read_text()
        self.assertIn('getenv("PROOT_ACCEPT_UNTRACED")', later)
        self.assertIn('"P %s %u %llu\\n"', later)
        self.assertEqual(self.reader()['STOP_COUNTS_NAME'], 'proot-stop-counts.txt')
        # 0.13.73 (patch 0007)
        self.assertIn('environment["PROOT_NETLINK_HIGH_FDS"] = "1"', launcher)
        last = (ROOT / 'android/native/proot/0007-netlink-high-fds-socket-filter.patch').read_text()
        for text in ('getenv("PROOT_NETLINK_HIGH_FDS")', '+#define SOCKET_FD_FLOOR 960', 'moved_netlink_fds=%llu',
                     'register_chained_syscall_with_result(tracee, netlink_fd_moved, PR_fcntl,'):
            self.assertIn(text, last)
        self.assertIn('NETLINK_DESCRIPTOR_FLOOR = 960', HOST.read_text())
        patch = (ROOT / 'android/native/proot/0005-stop-counts-getsockopt-filter.patch').read_text()
        for text in ('getenv("PROOT_STOP_COUNTS")', 'getenv("PROOT_GETSOCKOPT_PEERCRED_ONLY")', 'PROOT_STOP_COUNTS_V1 seconds='):
            self.assertIn(text, patch)


if __name__ == '__main__':
    unittest.main()
