"""0.13.72 (CI only): the guest supervisor counts its own file and child calls by caller.

CI run 43383782947: the guest's Python made 22 % of PRoot's stops in a reopen session. The
checked-in functions are executed unchanged, without importing the guest module they live in.
"""
import ast
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
GUEST = ROOT / 'armport/app/armport_interactive.py'


def load():
    tree = ast.parse(GUEST.read_text())
    names = {'install_call_profile', 'call_profile_record'}
    wanted = [node for node in tree.body
              if (isinstance(node, ast.Assign) and getattr(node.targets[0], 'id', '').startswith('CALL_PROFILE'))
              or (isinstance(node, ast.FunctionDef) and node.name in names)]
    assert len(wanted) == 4
    namespace = {'os': os, 'sys': sys}
    exec(compile(ast.Module(body=wanted, type_ignores=[]), str(GUEST), 'exec'), namespace)
    return namespace


class CallProfile(unittest.TestCase):
    def test_off_without_the_switch(self):
        namespace = load()
        self.assertIsNone(namespace['install_call_profile'](environ={}))
        self.assertIsNone(namespace['call_profile_record']())

    def test_calls_are_counted_for_the_caller_outside_the_library(self):
        namespace = load()
        fake_os = types.SimpleNamespace(**{name: getattr(os, name) for name in namespace['CALL_PROFILE_NAMES']})
        fake_io = types.SimpleNamespace(open=open)
        counts = namespace['install_call_profile'](environ={'COH_CALL_PROFILE': '1'},
                                                   modules={'os': fake_os, 'io': fake_io})
        with tempfile.TemporaryDirectory() as folder:
            for _ in range(3):
                fake_os.stat(folder)
            fake_os.listdir(folder)
            with fake_io.open(os.path.join(folder, 'x'), 'w') as handle:
                handle.write('1')
        record = namespace['call_profile_record']()
        self.assertEqual(record['total'], 5)
        self.assertEqual(record['by_call'], {'os.stat': 3, 'os.listdir': 1, 'open': 1})
        self.assertEqual(record['callers'][0][:2], ['os.stat', 'test_call_profile.py'])
        self.assertEqual(record['callers'][0][3], 3)
        self.assertIs(counts, namespace['install_call_profile'](environ={'COH_CALL_PROFILE': '1'}))   # installed once

    def test_ci_switch_and_report(self):
        host = (ROOT / 'armport/app/interactive_host.py').read_text()
        self.assertIn("command.insert(command.index('/usr/bin/python3'), 'COH_CALL_PROFILE=1')", host)
        self.assertIn("print('PYTHON_CALL_PROFILE_V1 '", host)
        self.assertIn("self.ctx.report['python_call_profile'] = profile", GUEST.read_text())


if __name__ == '__main__':
    unittest.main()
