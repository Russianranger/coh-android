"""Exercise the actual host input branch, without starting Wine or servers."""
import ast
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'armport/scripts'))
import login_ui


def row(stage):
    return json.dumps(dict(stage=stage, text='', tid=1)) + '\n'


def load_driver(namespace, source=None):
    # Execute the checked-in function unchanged; avoid importing the unrelated
    # server-package bootstrap and its host dependencies into this unit test.
    path = ROOT / 'armport/server/armport_game_host.py'
    tree = ast.parse(path.read_text() if source is None else source)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'drive_login')
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace['drive_login']


class HostLoginGate(unittest.TestCase):
    def drive(self, trace, *, ocr=False, selected=True, replace_after_wait=None, source=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdio, zone = root / 'armport_stdio.txt', root / 'zone-trace.jsonl'
            stdio.write_text('ArmPort login: stage 6 select %d player 0 of 1 timeout 0\n' % selected)
            if trace is not None:
                zone.write_text(trace)
            screen = Mock()
            screen.find.return_value = None
            screen.text.return_value = 'TEST123 Play'
            screen.shot.return_value = root / 'frame.png'
            status = dict(server_clicked=True, guest_exited=True)
            def after_login(screen, status, **kw):
                kw['done'](root / 'frame.png')
                if replace_after_wait is not None:
                    zone.write_text(replace_after_wait)
                return root / 'frame.png' if ocr else None
            namespace = dict(json=json, time=SimpleNamespace(time=lambda: 0, sleep=Mock()),
                start_client=lambda *a: (object(), dict(account='test', character='TEST123')),
                login=lambda *a, **kw: True, after_login=after_login,
                character_select_from_log=login_ui.character_select_from_log,
                dialogs_clear=login_ui.dialogs_clear, at=lambda *a: (960, 720),
                sh=lambda *a: SimpleNamespace(stdout=''))
            load_driver(namespace, source)(SimpleNamespace(client=root), screen, root, status, root)
            marker = root / 'armport-play-sent.json'
            return screen, status, json.loads(marker.read_text()) if marker.exists() else None

    def test_server_click_without_valid_trace_never_sends_next_or_play(self):
        for trace in (None, '', '{}\n', row('login') + '{', row('dialog.alert.begin'),
                      row('dialog.error.begin'), row('client.fatal')):
            for ocr in (False, True):
                with self.subTest(trace=trace, ocr=ocr):
                    screen, status, marker = self.drive(trace, ocr=ocr)
                    screen.click.assert_not_called()
                    screen.key.assert_not_called()
                    self.assertIsNone(marker)
                    self.assertFalse(status.get('enter_by_layout'))
                    self.assertFalse(status.get('play_sent'))

    def test_valid_selected_character_sends_one_next(self):
        for ocr in (False, True):
            screen, status, marker = self.drive(row('login'), ocr=ocr)
            screen.click.assert_called_once_with(960, 720)
            screen.key.assert_not_called()
            self.assertTrue(status['enter_by_layout'])
            self.assertEqual(marker, dict(play_sent='layout'))

    def test_no_selection_without_ocr_never_uses_server_click_fallback(self):
        screen, status, marker = self.drive(row('login'), selected=False)
        screen.click.assert_not_called()
        screen.key.assert_not_called()
        self.assertIsNone(marker)

    def test_clear_history_keeps_ocr_play_available(self):
        screen, status, marker = self.drive(row('login'), selected=False, ocr=True)
        screen.key.assert_called_once_with('Return')
        self.assertTrue(status['play_sent'])
        self.assertEqual(marker, dict(play_sent=True))

    def test_revalidates_after_wait_before_layout_input(self):
        screen, status, marker = self.drive(row('login'), replace_after_wait=row('dialog.error.begin'))
        screen.click.assert_not_called()
        screen.key.assert_not_called()
        self.assertIsNone(marker)
        self.assertFalse(status['character_select_by_trace'])
