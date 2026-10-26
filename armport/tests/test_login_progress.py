from pathlib import Path
import sys
import json
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import login_ui


class LoginProgress(unittest.TestCase):
    def test_only_current_selected_character_allows_next(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, trace = Path(tmp) / 'stdio', Path(tmp) / 'zone'
            self.assertFalse(login_ui.character_select_from_log(p, trace))
            trace.write_text(json.dumps(dict(stage='login', text='', tid=1)) + '\n')
            ready = 'ArmPort login: stage 6 select 1 player 0 of 1 timeout 0 frames 31267\n'
            for text, expected in (
                (ready, True), (ready + ready.replace('stage 6', 'stage 7'), False),
                (ready.replace('select 1', 'select 0'), False),
                (ready.replace('player 0', 'player -1'), False),
                (ready.replace('of 1', 'of 0'), False)):
                p.write_text(text)
                self.assertEqual(login_ui.character_select_from_log(p, trace), expected)

    def test_complete_isolated_dialog_history_is_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, trace = Path(tmp) / 'stdio', Path(tmp) / 'zone'
            # Earlier dialog markers can be outside the tail or interleaved.
            p.write_text('ERRArmPort zone: 12 dialog.alert.begin notice\n' + 'x' * 600000
                         + '\nArmPort login: stage 6 select 1 player 0 of 1 timeout 0\n')
            def row(stage, tid=1):
                return json.dumps(dict(stage=stage, text='', tid=tid)) + '\n'
            begin, done = row('dialog.alert.begin'), row('dialog.alert.done')
            for data, expected in (
                (row('login'), True), (begin, False), (begin + done, True),
                (begin + begin + done, False), (done, False),
                (begin + row('dialog.alert.done', 2), False),
                (begin + row('dialog.error.done'), False),
                (row('client.fatal'), False), (row('dialog.unknown'), False),
                ('', False), ('{}\n', False), ('[]\n', False),
                (row('login').rstrip(), False), (row('login') + '{', False),
                (row('login', True), False), (row('login', 0), False)):
                trace.write_text(data)
                self.assertEqual(login_ui.character_select_from_log(p, trace), expected, data)
            trace.write_bytes(b'\xff\n')
            self.assertFalse(login_ui.character_select_from_log(p, trace))
            trace.unlink()
            self.assertFalse(login_ui.character_select_from_log(p, trace))

    def test_repeated_ocr_reads_same_frame_once_but_new_frame_reprocesses(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'frame.png'
            p.write_bytes(b'frame')
            screen = login_ui.Screen(Path(tmp))
            row = '5\t1\t1\t1\t1\t1\t30\t60\t60\t30\t99\tNext\n'
            def run(*args, **kwargs):
                return SimpleNamespace(stdout='header\n' + row if args[0] == 'tesseract' else '', returncode=0)
            with patch.object(login_ui, 'sh', side_effect=run) as sh:
                self.assertEqual(screen.find(p, 'Next'), (20, 25))
                self.assertEqual(screen.text(p), 'Next')
                self.assertEqual(len([c for c in sh.call_args_list if c.args[0] == 'tesseract']), 1)
                p.write_bytes(b'another frame')
                self.assertEqual(screen.text(p), 'Next')
                self.assertEqual(len([c for c in sh.call_args_list if c.args[0] == 'tesseract']), 2)
