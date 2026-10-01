"""Graphical creator identity, ordinary logout ordering and image freshness."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('character_host_test', Path(__file__).with_name('character_host_smoke.py'))
character = importlib.util.module_from_spec(spec)
spec.loader.exec_module(character)
host = character.host
SESSION = '0123456789abcdef0123456789abcdef'
PID = 460


class Connection:
    def __init__(self):
        self.data = bytearray()
        self.sent = []

    def sendall(self, data): self.sent.append(data)

    def recv(self, size):
        result = bytes(self.data[:size])
        del self.data[:size]
        return result


def save(path, pixels, *geometry): path.write_bytes(b'bounded-image-fixture')


def events():
    return [
        {'type': 'client_interaction_ready', 'session_id': SESSION, 'client_pid': PID},
        {'type': 'client_login_ready', 'session_id': SESSION, 'client_pid': PID, 'character_list_sent': True},
        {'type': 'character_connected', 'session_id': SESSION, 'client_pid': PID,
         'character_id': 7, 'name': 'THORHERO', 'account': 'COHLOCAL', 'map_id': 1},
        {'type': 'character_saved', 'session_id': SESSION, 'client_pid': PID,
         'character_id': 7, 'name': 'THORHERO', 'committed_sql_verified': True}]


class CharacterHostTests(unittest.TestCase):
    def test_save_requires_current_ready_login_atlas_identity_and_committed_sql(self):
        ready, login, connected, saved = events()
        invalid = [([], connected), ([ready], connected), ([ready, login], saved),
            ([ready, login], dict(connected, map_id=24)), ([ready, login], dict(connected, character_id=True)),
            ([ready, login], dict(connected, client_pid=PID+1)),
            ([ready, login, connected], dict(saved, character_id=8)),
            ([ready, login, connected], dict(saved, committed_sql_verified=False)),
            ([ready, login, connected, saved], saved)]
        terminal = {'type': 'stage', 'stage': 'actual_client_interaction', 'status': 'passed'}
        invalid += [([ready, login, connected], terminal), ([ready, login, connected, saved, terminal], saved)]
        for prefix, change in invalid:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary)/'events'
                path.write_text(''.join(json.dumps(item)+'\n' for item in prefix+[change]))
                with self.assertRaises(ValueError): character.CharacterEvents(path, SESSION).poll()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'events'
            path.write_text(''.join(json.dumps(item)+'\n' for item in events()[:3]))
            reader = character.CharacterEvents(path, SESSION)
            reader.poll()
            self.assertEqual(reader.connected_generation, 1)
            with path.open('a') as output:
                output.write(json.dumps(dict(saved, session_id='f'*32))+'\n')
                output.write(json.dumps(saved)[:12])
            reader.poll()
            self.assertEqual(reader.saved_generation, 0)
            with path.open('a') as output: output.write(json.dumps(saved)[12:]+'\n')
            reader.poll()
            self.assertEqual(reader.saved_generation, 1)

    def test_graphical_script_waits_for_atlas_before_logout_and_fresh_save_before_finish(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            finish = root/'finish.json'
            script = character.CharacterInteraction(SESSION, root, finish)
            frame = host.ClientFramebuffer()
            frame.pixels[:] = bytes((32, 64, 96, 0))*(800*600)
            frame.request_login_generation = 1
            frame.request_connected_generation = frame.request_saved_generation = 0
            proof = SimpleNamespace(client_pid=PID, character_id=7, login_generation=1, connected_generation=0, saved_generation=0)
            connection = Connection()
            clock = [0.0]
            sequence = [0]

            def tick():
                sequence[0] += 1
                clock[0] += 2
                script.on_frame(connection, frame, proof, sequence[0], [{}, {}, {}], clock[0])

            with mock.patch.object(host.time, 'monotonic', side_effect=lambda: clock[0]), \
                 mock.patch.object(host.time, 'sleep', side_effect=lambda seconds: clock.__setitem__(0, clock[0]+seconds)), \
                 mock.patch.object(host, 'save_png', side_effect=save), \
                 mock.patch.object(character, 'read_button', return_value=((350, 340, 95), 'actual-frame-ocr')):
                connected_index = next(i for i, action in enumerate(script.ACTIONS) if action[0] == 'connected')
                for _ in range(230):
                    tick()
                    if script.action == connected_index: break
                self.assertEqual(script.action, connected_index)
                for _ in range(5): tick()
                self.assertEqual(script.action, connected_index)
                self.assertNotIn('type_ordinary_logout', [step['action'] for step in script.result['steps']])
                self.assertFalse(finish.exists())
                self.assertFalse((root/'character-logout.json').exists())
                proof.connected_generation = 1
                tick()
                self.assertEqual(script.result['connected_captures'], [])
                frame.request_connected_generation = 1
                saved_index = next(i for i, action in enumerate(script.ACTIONS) if action[0] == 'saved')
                for _ in range(20):
                    tick()
                    if script.action == saved_index: break
                self.assertEqual(script.action, saved_index)
                self.assertIn('submit_ordinary_logout', [step['action'] for step in script.result['steps']])
                self.assertEqual(json.loads((root/'character-logout.json').read_text()), script.result['logout_request'])
                for _ in range(5): tick()
                self.assertFalse(finish.exists())
                proof.saved_generation = 1
                tick()
                self.assertEqual(script.result['post_save_captures'], [])
                frame.request_saved_generation = 1
                for _ in range(2):
                    tick()
                    self.assertFalse(finish.exists())
                tick()  # Third complete frame after the saved event.
                self.assertFalse(finish.exists())
                tick()
                self.assertTrue(finish.exists())
            self.assertTrue(script.result['script_completed'])
            self.assertFalse(script.result['character_creation_visual_validated'])
            self.assertEqual(len(script.result['post_save_captures']), 3)
            self.assertEqual(json.loads(finish.read_text()), {'format': 1, 'session_id': SESSION,
                'client_pid': PID, 'action': 'finish_interaction'})
            keys = [struct.unpack('!BBHI', data)[3] for data in connection.sent if data[0] == 4 and data[1] == 1]
            text = ''.join(chr(code) for code in keys if code < 128)
            self.assertIn('/quittologin', text)
            self.assertNotIn('/quit\n', text)

    def test_logout_receipt_is_written_only_after_successful_final_return_release(self):
        for break_release in (False, True):
            with self.subTest(break_release=break_release), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                receipt = root/'character-logout.json'
                script = character.CharacterInteraction(SESSION, root, root/'finish.json')
                script.ready_at = 0
                script.action = next(i for i, action in enumerate(script.ACTIONS) if action[2] == 'submit_ordinary_logout')
                frame = host.ClientFramebuffer()
                script.frame_generation = frame.generation
                proof = SimpleNamespace(client_pid=PID, character_id=7)
                checked = []

                class ObserveDelivery(Connection):
                    def sendall(self, data):
                        checked.append(not receipt.exists())
                        if break_release and data == struct.pack('!BBHI', 4, 0, 0, 0xff0d):
                            raise BrokenPipeError('Final Return release was not delivered')
                        super().sendall(data)

                connection = ObserveDelivery()
                with mock.patch.object(host.time, 'sleep'), mock.patch.object(host.time, 'time', return_value=123456.789), \
                     mock.patch.object(host, 'save_png', side_effect=save):
                    if break_release:
                        with self.assertRaises(BrokenPipeError):
                            script.on_frame(connection, frame, proof, 1, [{}, {}, {}], 5)
                    else:
                        script.on_frame(connection, frame, proof, 1, [{}, {}, {}], 5)
                self.assertEqual(checked, [True, True])
                self.assertEqual(receipt.exists(), not break_release)
                if break_release:
                    self.assertNotIn('logout_request', script.result)
                else:
                    self.assertEqual(json.loads(receipt.read_text()), {'format': 1, 'session_id': SESSION,
                        'client_pid': PID, 'character_id': 7, 'action': 'quittologin', 'sent_utc_ms': 123456789})
                    self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
                    self.assertEqual(list(root.glob('*.tmp-*')), [])

    def test_ocr_literal_region_and_button_row_prevent_prose_and_outside_clicks(self):
        header = 'level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n'
        rows = [
            '5\t1\t1\t1\t1\t1\t1000\t780\t75\t30\t95\tNo',  # prose
            '5\t1\t2\t1\t1\t1\t1200\t1010\t80\t30\t80\tNO',  # button
            '5\t1\t2\t1\t1\t2\t10\t1200\t80\t30\t90\tNo',   # outside dialog
            '5\t1\t2\t1\t1\t3\t1200\t1100\t80\t30\t5\tNo']  # weak OCR
        result = character.ocr_button(header+'\n'.join(rows), 'No', (220, 230, 580, 465))
        self.assertEqual(result, (413, 342, 80.0))
        self.assertIsNone(character.ocr_button(header+'\n'.join(rows), 'Yes', (220, 230, 580, 465)))

    def test_observer_retains_pre_save_request_generation_when_event_arrives_with_pixels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            event_path = root/'events'
            event_path.write_text(''.join(json.dumps(item)+'\n' for item in events()[:3]))
            seen = []
            clock = [0.0]

            class Frames(Connection):
                requests = 0

                def sendall(self, data):
                    super().sendall(data)
                    self.requests += 1
                    if self.requests == 2:
                        with event_path.open('a') as output: output.write(json.dumps(events()[3])+'\n')
                    if self.requests == 4:
                        with event_path.open('a') as output:
                            output.write(json.dumps({'type': 'stage', 'stage': 'actual_client_interaction',
                                                     'status': 'passed'})+'\n')
                        raise BrokenPipeError()
                    pixels = b''.join(bytes((value, value, value, 0)) for value in range(8))
                    self.data.extend(b'\0'+struct.pack('!BH', 0, 1)+struct.pack('!HHHHi', 0, 0, 8, 1, 0)+pixels)

            class Observer:
                def __init__(self, *args): self.result = {}
                def on_frame(self, connection, frame, proof, sequence, captures, now):
                    seen.append((sequence, proof.saved_generation, frame.request_saved_generation))

            process = mock.Mock()
            process.poll.return_value = None
            with mock.patch.object(host, 'client_rfb_handshake', return_value='desktop'), \
                 mock.patch.object(host.time, 'monotonic', side_effect=lambda: clock[0]), \
                 mock.patch.object(host.time, 'sleep', side_effect=lambda seconds: clock.__setitem__(0, clock[0]+seconds)), \
                 mock.patch.object(host, 'save_png', side_effect=save):
                result = character.observe_rfb(Frames(), SESSION, process, 20, root,
                    event_path, root/'finish.json', Observer)
            self.assertIsNone(result['failure'])
            self.assertEqual(seen, [(1, 0, 0), (2, 1, 0), (3, 1, 1)])

    def test_twenty_minute_deadline_never_writes_finish_without_save(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = character.CharacterInteraction(SESSION, root, root/'finish.json')
            script.ready_at = 0
            with self.assertRaisesRegex(ValueError, 'twenty-minute'):
                script.on_frame(Connection(), host.ClientFramebuffer(), SimpleNamespace(), 1, [], 1200)
            self.assertFalse((root/'finish.json').exists())


if __name__ == '__main__': unittest.main()
