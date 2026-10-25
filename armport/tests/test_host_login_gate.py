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
    def drive(self, trace, *, ocr=False, selected=True, replace_after_wait=None, source=None,
              character_found=False, play_found=False, change_at=None,
              changed_trace=None, progress=(), final_retry_stage=None, final_retry_trace=None,
              final_retry_atlas=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdio, zone = root / 'armport_stdio.txt', root / 'zone-trace.jsonl'
            stdio.write_text('ArmPort login: stage 6 select %d player 0 of 1 timeout 0 frames 1\n' % selected)
            if trace is not None:
                zone.write_text(trace)
            def change(event):
                if event == change_at:
                    if changed_trace is None:
                        zone.unlink(missing_ok=True)
                    else:
                        zone.write_text(changed_trace)
            screen = Mock()
            def find(png, *words):
                if words == ('TEST123',):
                    change('character_ocr')
                    return (100, 200) if character_found else None
                if words == ('Play', 'PLAY'):
                    change('play_ocr')
                    return (900, 700) if play_found else None
                return None
            def click(*position):
                if position == (100, 200):
                    change('character_click')
            def shot(label):
                if label == 'character-chosen':
                    change('capture')
                return root / 'frame.png'
            def at(*args):
                change('layout_lookup')
                return (960, 720)
            screen.find.side_effect = find
            screen.click.side_effect = click
            screen.text.return_value = 'TEST123 Play'
            screen.shot.side_effect = shot
            status = dict(server_clicked=True, guest_exited=True)
            def after_login(screen, status, **kw):
                kw['done'](root / 'frame.png')
                if replace_after_wait is not None:
                    zone.write_text(replace_after_wait)
                return root / 'frame.png' if ocr else None
            progress_iter = iter(progress)
            def sleep(seconds):
                if seconds == 2:
                    change('selection_wait')
                if seconds == 15:
                    next_line = next(progress_iter, None)
                    if next_line is not None:
                        stdio.write_text(stdio.read_text() + next_line)
                    change('next_wait')
            retry_reads = [0]
            def frame(path, trace_path):
                result = login_ui.character_select_frame(path, trace_path)
                if screen.click.call_count == 1:
                    retry_reads[0] += 1
                    if retry_reads[0] == 2:
                        # Publish after geometry revalidation has read the old
                        # sample, before the final adjacent input check reads.
                        if final_retry_stage is not None:
                            stdio.write_text(stdio.read_text() + final_retry_stage)
                        if final_retry_trace is not None:
                            zone.write_text(final_retry_trace)
                        if final_retry_atlas:
                            (root / 'armport-atlas.json').write_text('{}')
                return result
            namespace = dict(json=json, time=SimpleNamespace(time=lambda: 0, sleep=sleep),
                start_client=lambda *a: (object(), dict(account='test', character='TEST123')),
                login=lambda *a, **kw: True, after_login=after_login,
                character_select_from_log=login_ui.character_select_from_log,
                character_select_frame=frame,
                dialogs_clear=login_ui.dialogs_clear, at=at,
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

    def test_history_changed_during_selection_never_sends_final_input(self):
        for event in ('character_click', 'selection_wait', 'capture', 'play_ocr'):
            for trace in (row('dialog.error.begin'), row('dialog.alert.begin'),
                          row('client.fatal'), '{}\n', row('login') + '{', None):
                for play_found in (False, True):
                    with self.subTest(event=event, trace=trace, play_found=play_found):
                        screen, status, marker = self.drive(row('login'), ocr=True, selected=False,
                            character_found=True, play_found=play_found, change_at=event,
                            changed_trace=trace)
                        screen.click.assert_called_once_with(100, 200)
                        screen.key.assert_not_called()
                        self.assertIsNone(marker)
                        self.assertFalse(status.get('play_sent'))
                        self.assertIn('rejected', status['play_blocked'])

    def test_history_changed_during_character_ocr_blocks_selection_too(self):
        screen, status, marker = self.drive(row('login'), ocr=True, selected=False,
            character_found=True, play_found=True, change_at='character_ocr',
            changed_trace=row('dialog.error.begin'))
        screen.click.assert_not_called()
        screen.key.assert_not_called()
        self.assertIsNone(marker)

    def test_history_changed_during_layout_lookup_blocks_next(self):
        screen, status, marker = self.drive(row('login'), change_at='layout_lookup',
            changed_trace=row('dialog.error.begin'))
        screen.click.assert_not_called()
        screen.key.assert_not_called()
        self.assertIsNone(marker)
        self.assertIn('changed', status['enter_layout_error'])

    def test_clear_history_after_selection_keeps_both_final_input_paths(self):
        for play_found in (False, True):
            screen, status, marker = self.drive(row('login'), ocr=True, selected=False,
                character_found=True, play_found=play_found)
            self.assertEqual(screen.click.call_args_list[0].args, (100, 200))
            if play_found:
                self.assertEqual(screen.click.call_args_list[1].args, (900, 700))
                self.assertEqual(screen.click.call_count, 2)
                screen.key.assert_not_called()
            else:
                self.assertEqual(screen.click.call_count, 1)
                screen.key.assert_called_once_with('Return')
            self.assertTrue(status['play_sent'])
            self.assertEqual(marker, dict(play_sent=True))

    def test_next_retries_only_on_new_selected_character_frames(self):
        def sample(frame, stage=6):
            return f'ArmPort login: stage {stage} select 1 player 0 of 1 timeout 0 frames {frame}\n'
        for progress, expected in (([sample(2), sample(3), sample(4)], 3),
                                   ([sample(2), sample(3, 7)], 2),
                                   ([sample(1)], 1),
                                   ([sample(2).rstrip()], 1)):
            screen, status, marker = self.drive(row('login'), progress=progress)
            self.assertEqual(screen.click.call_count, expected)
            self.assertEqual(status['enter_attempts'], expected)
            screen.key.assert_not_called()

    def test_new_dialog_blocks_next_retry(self):
        screen, status, marker = self.drive(row('login'),
            progress=['ArmPort login: stage 6 select 1 player 0 of 1 timeout 0 frames 2\n'],
            change_at='next_wait', changed_trace=row('dialog.alert.begin'))
        screen.click.assert_called_once()

    def test_final_retry_recheck_rejects_new_stage_or_torn_sample(self):
        ready = 'ArmPort login: stage 6 select 1 player 0 of 1 timeout 0 frames 2\n'
        for latest in ('ArmPort login: stage 7',
                       'ArmPort login: stage 6 select 1 player 0 of 1 timeout 0 frames 3',
                       'ArmPort login: stage 7 select 1 player 0 of 1 timeout 0 frames 3\n'):
            with self.subTest(latest=latest):
                screen, status, _ = self.drive(row('login'), progress=[ready], final_retry_stage=latest)
                screen.click.assert_called_once()
                self.assertEqual(status['enter_attempts'], 1)

    def test_final_retry_recheck_rejects_new_modal(self):
        screen, _, _ = self.drive(row('login'),
            progress=['ArmPort login: stage 6 select 1 player 0 of 1 timeout 0 frames 2\n'],
            final_retry_trace=row('dialog.alert.begin'))
        screen.click.assert_called_once()

    def test_final_retry_recheck_rejects_new_atlas_marker(self):
        # Stop before downstream rendering code; retain the marker check in
        # the actual input branch, then return before the unrelated rendering loop.
        source = (ROOT / 'armport/server/armport_game_host.py').read_text()
        source = source.replace("    # In game: wait for the guest's database confirmation, then screenshots.",
                                "    return\n    # In game: wait for the guest's database confirmation, then screenshots.")
        screen, _, _ = self.drive(row('login'), source=source,
            progress=['ArmPort login: stage 6 select 1 player 0 of 1 timeout 0 frames 2\n'], final_retry_atlas=True)
        screen.click.assert_called_once()
