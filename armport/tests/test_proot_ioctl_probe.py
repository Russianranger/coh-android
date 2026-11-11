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
                 'time': time, 'require': require}
    exec(compile(ast.Module(body=wanted, type_ignores=[]), str(GUEST), 'exec'), namespace)
    return namespace


def load_gate(requested):
    tree = ast.parse(HOST.read_text())
    wanted = [node for node in tree.body if isinstance(node, ast.FunctionDef)
              and node.name == 'require_proot_ioctl_filter']
    assert len(wanted) == 1
    runtime = types.SimpleNamespace(proot_ioctl_filter_requested=lambda: requested)
    namespace = {'require': require, 'runtime_host': types.SimpleNamespace(runtime=runtime)}
    exec(compile(ast.Module(body=wanted, type_ignores=[]), str(HOST), 'exec'), namespace)
    return namespace['require_proot_ioctl_filter']


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
        self.assertEqual(set(result['microseconds_per_call']), {'getppid', 'fionread', 'tcgets2'})
        self.assertIs(result['is_success_proof'], False)

    def test_the_three_cases_are_told_apart(self):
        self.assertEqual(self.reading({'getppid': 0.2, 'fionread': 0.4, 'tcgets2': 0.9})['reading'], 'no_ioctl_stops')
        self.assertEqual(self.reading({'getppid': 0.2, 'fionread': 0.4, 'tcgets2': 55.9})['reading'],
                         'listed_commands_only')
        self.assertEqual(self.reading({'getppid': 0.5, 'fionread': 90.0, 'tcgets2': 95.0})['reading'],
                         'every_ioctl_stops')
        self.assertEqual(self.reading({'getppid': 0.5, 'fionread': 90.0, 'tcgets2': 1.0})['reading'], 'inconsistent')

    def test_switch_is_recorded_as_the_guest_sees_it(self):
        with mock.patch.dict(os.environ, {'PROOT_IOCTL_COMMANDS_ONLY': '1'}):
            self.assertEqual(load_probe()['proot_ioctl_probe'](calls=5)['switch'], '1')
        environment = {k: v for k, v in os.environ.items() if k != 'PROOT_IOCTL_COMMANDS_ONLY'}
        with mock.patch.dict(os.environ, environment, clear=True):
            self.assertEqual(load_probe()['proot_ioctl_probe'](calls=5)['switch'], '')

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
        load_gate(True)({'armport_proot_ioctl': {'reading': 'listed_commands_only', 'switch': '1'}})

    def test_other_readings_fail(self):
        gate = load_gate(True)
        for probe in (None, {'reading': 'no_ioctl_stops', 'switch': '1'}, {'reading': 'every_ioctl_stops', 'switch': '1'},
                      {'reading': 'listed_commands_only', 'switch': ''}, {'reading': 'unavailable'}):
            with self.subTest(probe=probe), self.assertRaises(RuntimeError):
                gate({} if probe is None else {'armport_proot_ioctl': probe})

    def test_workflow_passes_the_switch(self):
        workflow = (ROOT / '.github/workflows/armport-app-runtime.yml').read_text()
        self.assertIn("COH_PROOT_IOCTL_FILTER: ${{ inputs.proot_ioctl_filter && '1' || '' }}", workflow)


if __name__ == '__main__':
    unittest.main()
