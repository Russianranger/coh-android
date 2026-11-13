"""CI: with the early_zone input the reopened session must have decided on an early start (0.13.69).

0.13.68's chain passed with the input on while the ARM64 launch never reached the call
(run 42955090151: no `early_start` record). The checked-in function is executed unchanged,
without importing the host script's server-package bootstrap.
"""
import ast
import os
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / 'armport/app/interactive_host.py'


def load():
    tree = ast.parse(HOST.read_text())
    wanted = [node for node in tree.body if isinstance(node, ast.FunctionDef)
              and node.name in ('require_early_zone_decision', 'early_zone_requested')]
    assert len(wanted) == 2

    def require(condition, message):
        if not condition:
            raise RuntimeError(message)
    namespace = {'os': os, 'require': require}
    exec(compile(ast.Module(body=wanted, type_ignores=[]), str(HOST), 'exec'), namespace)
    return namespace['require_early_zone_decision']


def report(early):
    initial = {} if early is None else {'early_start': early}
    return {'character_zoning': {'initial_zone': initial}}


class EarlyZoneGateTest(unittest.TestCase):
    def setUp(self):
        self.gate = load()

    def test_without_the_input_nothing_is_required(self):
        with mock.patch.dict(os.environ, {'COH_EARLY_ZONE': ''}):
            self.gate({})
            self.gate(report(None))

    def test_with_the_input_a_started_zone_or_a_memory_refusal_passes(self):
        with mock.patch.dict(os.environ, {'COH_EARLY_ZONE': '1'}):
            self.gate(report({'requested': True, 'started': True, 'reason': None}))
            self.gate(report({'requested': True, 'started': False, 'reason': 'low_memory'}))
            self.gate(report({'requested': True, 'started': False, 'reason': 'available_memory_unknown'}))

    def test_with_the_input_no_decision_or_another_refusal_fails_the_run(self):
        with mock.patch.dict(os.environ, {'COH_EARLY_ZONE': '1'}):
            for value in ({}, {'character_zoning': None}, report(None)):
                with self.subTest(value=value), self.assertRaisesRegex(RuntimeError, 'never decided'):
                    self.gate(value)
            for reason in ('not_requested', 'a_zone_server_is_already_running', 'start_failed', 'zone_not_served'):
                with self.subTest(reason=reason), self.assertRaisesRegex(RuntimeError, 'not made: ' + reason):
                    self.gate(report({'requested': True, 'started': False, 'reason': reason}))
            with self.assertRaisesRegex(RuntimeError, 'start failed'):
                self.gate(report({'requested': True, 'started': True, 'failure': 'MapServer exited'}))

    def test_the_arm64_launch_calls_the_start_after_its_client_inputs(self):
        source = (ROOT / 'armport/app/armport_interactive.py').read_text()
        inputs = source.index('        self.prepare_client_visual_inputs()\n        # 0.13.69')
        call = source.index("getattr(getattr(self, 'local_server', None), 'start_early_zone', None)")
        self.assertLess(inputs, call)
        self.assertLess(call, source.index("self.ctx.stage('armport_client_data')"))
        host = HOST.read_text()
        self.assertIn('                require_early_zone_decision(report)\n', host)


if __name__ == '__main__':
    unittest.main()
