"""Execute the production host teardown with controlled child-process outcomes."""
import ast
import os
from pathlib import Path
import subprocess
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]


class HostCleanup(unittest.TestCase):
    def shared_cleanup(self, stop):
        path = ROOT / 'armport/server/armport_game_host.py'
        node = next(n for n in ast.parse(path.read_text()).body
                    if isinstance(n, ast.ClassDef) and n.name == 'ClientCleanup')
        ns = dict(threading=threading, stop_client=stop)
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), ns)
        return ns['ClientCleanup']('args', 'process')

    def test_final_cleanup_reuses_coordinated_success(self):
        # CI 40197277872: first cleanup succeeds; a second -k exits 1.
        stop = Mock(side_effect=[[], ['wineserver stop: exit 1']])
        cleanup = self.shared_cleanup(stop)
        self.assertEqual(cleanup.stop(), [])
        self.assertEqual(cleanup.stop(), [])
        stop.assert_called_once_with('args', 'process')

    def test_shared_failure_cannot_be_erased_by_a_later_success(self):
        stop = Mock(side_effect=[['wineserver wait: TimeoutExpired'], []])
        cleanup = self.shared_cleanup(stop)
        errors = cleanup.stop()
        errors.clear()
        self.assertEqual(cleanup.stop(), ['wineserver wait: TimeoutExpired'])
        stop.assert_called_once()

    def test_concurrent_guest_and_final_cleanup_execute_once(self):
        entered, release = threading.Event(), threading.Event()
        def stop(*args):
            entered.set()
            if not release.wait(5):
                raise RuntimeError('control failed to release teardown')
            return ['client wait: TimeoutExpired after KILL']
        operation = Mock(side_effect=stop)
        cleanup = self.shared_cleanup(operation)
        results = []
        first = threading.Thread(target=lambda: results.append(cleanup.stop()))
        second = threading.Thread(target=lambda: results.append(cleanup.stop()))
        first.start()
        self.assertTrue(entered.wait(5))
        second.start()
        release.set()
        first.join(5); second.join(5)
        self.assertFalse(first.is_alive() or second.is_alive())
        self.assertEqual(results, [['client wait: TimeoutExpired after KILL']] * 2)
        operation.assert_called_once()

    def exercise(self, *, live=True, waits=(), failures=None):
        path = ROOT / 'armport/server/armport_game_host.py'
        node = next(n for n in ast.parse(path.read_text()).body
                    if isinstance(n, ast.FunctionDef) and n.name == 'stop_client')
        commands = []
        def run(command, **kwargs):
            commands.append((command, kwargs))
            key = command[-1] if 'wineserver' in command[0] else command[3]
            result = (failures or {}).get(key, 0)
            if isinstance(result, Exception):
                raise result
            return SimpleNamespace(returncode=result)
        ns = dict(os=os, subprocess=SimpleNamespace(run=run, TimeoutExpired=subprocess.TimeoutExpired))
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), ns)
        proc = Mock(pid=234)
        proc.poll.return_value = None if live else 0
        proc.wait.side_effect = list(waits) if waits else None
        a = SimpleNamespace(client_prefix=Path('/client-prefix'), client_home=Path('/client-home'), wine=Path('/wine'))
        errors = ns['stop_client'](a, proc)
        return errors, commands, proc

    def test_success_waits_for_client_and_wineserver(self):
        errors, commands, proc = self.exercise()
        self.assertEqual(errors, [])
        proc.wait.assert_called_once_with(timeout=30)
        self.assertEqual([c[0][-1] for c in commands], ['-234', '-k', '-w'])
        self.assertEqual(commands[-1][1]['env']['WINEPREFIX'], '/client-prefix')
        self.assertLessEqual(sum(c[1]['timeout'] for c in commands) + 30, 180)

    def test_wine_timeout_is_retained(self):
        errors, commands, _ = self.exercise(failures={'-w': subprocess.TimeoutExpired('wine wait', 60)})
        self.assertEqual(errors, ['wineserver wait: TimeoutExpired'])

    def test_kill_fallback_waits_and_has_bounded_total(self):
        errors, commands, proc = self.exercise(waits=[subprocess.TimeoutExpired('client', 30), 0])
        self.assertEqual(errors, [])
        self.assertEqual([c[0][3] for c in commands[:2]], ['-TERM', '-KILL'])
        self.assertEqual([c.kwargs['timeout'] for c in proc.wait.call_args_list], [30, 10])
        self.assertLessEqual(sum(c[1]['timeout'] for c in commands) + 40, 180)

    def test_stuck_kill_and_failed_stop_still_attempt_wine_wait(self):
        errors, commands, _ = self.exercise(waits=[subprocess.TimeoutExpired('client', 30),
                                                  subprocess.TimeoutExpired('client', 10)],
                                            failures={'-k': 1})
        self.assertEqual(errors, ['client wait: TimeoutExpired after KILL', 'wineserver stop: exit 1'])
        self.assertEqual(commands[-1][0][-1], '-w')

    def test_os_error_does_not_skip_remaining_cleanup(self):
        errors, commands, _ = self.exercise(live=False, failures={'-k': OSError('missing')})
        self.assertEqual(errors, ['wineserver stop: OSError'])
        self.assertEqual(commands[-1][0][-1], '-w')
