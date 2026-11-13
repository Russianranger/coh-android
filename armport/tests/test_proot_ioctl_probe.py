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
    wanted = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    assert len(wanted) == 1
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
        self.assertEqual(set(result['microseconds_per_call']), {'getppid', 'fionread', 'tcgets2', 'getsockopt'})
        self.assertIs(result['getsockopt_stops'], False)
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

    def test_filter_at_work_passes(self):
        load_gate(True)({'armport_proot_ioctl': {'reading': 'listed_commands_only', 'requested': True,
                                                 'getsockopt_stops': False}})

    def test_other_readings_fail(self):
        gate = load_gate(True)
        for probe in (None, {'reading': 'no_ioctl_stops', 'requested': True},
                      {'reading': 'every_ioctl_stops', 'requested': True},
                      {'reading': 'listed_commands_only', 'requested': False}, {'reading': 'unavailable'},
                      {'reading': 'listed_commands_only', 'requested': True},
                      {'reading': 'listed_commands_only', 'requested': True, 'getsockopt_stops': True}):
            with self.subTest(probe=probe), self.assertRaises(RuntimeError):
                gate({} if probe is None else {'armport_proot_ioctl': probe})

    def test_ci_passes_the_request_into_the_guest(self):
        host = HOST.read_text()
        self.assertIn("command.insert(command.index('/usr/bin/python3'), 'COH_PROOT_IOCTL_FILTER=1')", host)
        java = (ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/'
                'ClientRuntime.java').read_text()
        self.assertIn('"COH_PROOT_IOCTL_FILTER="+(prootIoctlFilterUsed?"1":"0")', java)

    def test_workflow_passes_the_switch(self):
        workflow = (ROOT / '.github/workflows/armport-app-runtime.yml').read_text()
        self.assertIn("COH_PROOT_IOCTL_FILTER: ${{ inputs.proot_ioctl_filter && '1' || '' }}", workflow)


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
        patch = (ROOT / 'android/native/proot/0005-stop-counts-getsockopt-filter.patch').read_text()
        for text in ('getenv("PROOT_STOP_COUNTS")', 'getenv("PROOT_GETSOCKOPT_PEERCRED_ONLY")', 'PROOT_STOP_COUNTS_V1 seconds='):
            self.assertIn(text, patch)


if __name__ == '__main__':
    unittest.main()
