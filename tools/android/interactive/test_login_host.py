"""Local-login RFB actions, event identity, and post-response image freshness."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('local_login_host_test', Path(__file__).with_name('login_host_smoke.py'))
login = importlib.util.module_from_spec(spec)
spec.loader.exec_module(login)
host = login.host
SESSION = '0123456789abcdef0123456789abcdef'
PID = 460


class Connection:
    def __init__(self):
        self.data = bytearray()
        self.sent = []

    def sendall(self, data):
        self.sent.append(data)

    def recv(self, size):
        result = bytes(self.data[:size])
        del self.data[:size]
        return result


def save(path, pixels, *geometry):
    path.write_bytes(b'bounded-image-fixture')


class LoginHostTests(unittest.TestCase):
    def test_fixed_login_actions_replace_both_fields_and_require_three_fresh_login_views(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            finish = root/'finish.json'
            script = login.LoginInteraction(SESSION, root, finish)
            events = SimpleNamespace(client_pid=PID, login_generation=0)
            frame = host.ClientFramebuffer()
            frame.pixels[:32] = b''.join(bytes((value, value, value, 0)) for value in range(8))
            frame.request_login_generation = 0
            clock = [0.0]
            connection = Connection()

            def sleep(seconds):
                clock[0] += seconds

            with mock.patch.object(host.time, 'monotonic', side_effect=lambda: clock[0]), \
                 mock.patch.object(host.time, 'sleep', side_effect=sleep), \
                 mock.patch.object(host, 'save_png', side_effect=save):
                # Login may render successfully without server protocol evidence;
                # neither age nor pixels alone may generate Finish.
                for sequence in range(1, 66):
                    clock[0] = (sequence-1)*.5
                    script.on_frame(connection, frame, events, sequence, [{}, {}, {}], clock[0])
                self.assertEqual(script.action, 18)
                self.assertFalse(finish.exists())
                self.assertEqual(script.result['post_login_captures'], [])
                events.login_generation = 1
                clock[0] = 33
                script.on_frame(connection, frame, events, 66, [{}, {}, {}], clock[0])
                self.assertEqual(script.result['post_login_captures'], [])  # Request preceded login event.
                frame.request_login_generation = 1
                for sequence, when in ((67, 34), (67, 34), (68, 34.5), (69, 35), (70, 35.5)):
                    clock[0] = when
                    script.on_frame(connection, frame, events, sequence, [{}, {}, {}], when)
                    self.assertFalse(finish.exists())
                self.assertEqual(len(script.result['post_login_captures']), 2)
                clock[0] = 36
                script.on_frame(connection, frame, events, 71, [{}, {}, {}], 36)

            pointers = [struct.unpack('!BBHH', value) for value in connection.sent if value[0] == 5]
            expected = []
            for x, y in ((400, 403), (635, 430), (433, 70), (625, 240), (625, 328), (704, 379), (644, 219)):
                expected.extend(((5, 0, x, y), (5, 1, x, y), (5, 0, x, y)))
            self.assertEqual(pointers, expected)
            keys = [struct.unpack('!BBHI', value) for value in connection.sent if value[0] == 4]
            expected = [(4, 1, 0, 0xff1b), (4, 0, 0, 0xff1b)]
            for value in ('COHLOCAL', 'offline'):
                expected.extend(((4, 1, 0, 0xffe3), (4, 1, 0, ord('a')),
                                 (4, 0, 0, ord('a')), (4, 0, 0, 0xffe3)))
                expected.extend((4, down, 0, ord(character)) for character in value for down in (1, 0))
            self.assertEqual(keys, expected)
            self.assertTrue(script.result['script_completed'])
            self.assertFalse(script.result['character_selection_visual_validated'])
            self.assertEqual([capture['frame_sequence'] for capture in script.result['post_login_captures']], [67, 69, 71])
            self.assertEqual(json.loads(finish.read_text()), {'format': 1, 'session_id': SESSION,
                'client_pid': PID, 'action': 'finish_interaction'})

    def test_settings_remaining_on_left_prevents_login_until_three_restored_frames(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = login.LoginInteraction(SESSION, root, root/'finish.json')
            events = SimpleNamespace(client_pid=PID, login_generation=0)
            frame = host.ClientFramebuffer()
            original = bytes((32, 64, 96, 0))*(800*600)
            frame.pixels[:] = original
            clock = [0.0]
            connection = Connection()

            def sleep(seconds): clock[0] += seconds

            with mock.patch.object(host.time, 'monotonic', side_effect=lambda: clock[0]), \
                 mock.patch.object(host.time, 'sleep', side_effect=sleep), \
                 mock.patch.object(host, 'save_png', side_effect=save):
                sequence = 0
                while script.action < 7:
                    sequence += 1
                    clock[0] = sequence*.5
                    script.on_frame(connection, frame, events, sequence, [{}, {}, {}], clock[0])
                # The right account panel is unchanged, as it is when Settings
                # is still open. Only its left-side coverage is altered.
                for y in range(90, 350):
                    frame.pixels[(y*800+15)*4:(y*800+420)*4] = bytes((240, 240, 240, 0))*405
                for _ in range(4):
                    sequence += 1; clock[0] += 1
                    script.on_frame(connection, frame, events, sequence, [{}, {}, {}], clock[0])
                self.assertEqual(script.action, 7)
                self.assertEqual(script.restored_frames, 0)
                self.assertNotIn('settings_recovery', script.result)
                frame.pixels[:] = original
                for restored in range(1, 4):
                    sequence += 1; clock[0] += 1
                    script.on_frame(connection, frame, events, sequence, [{}, {}, {}], clock[0])
                    self.assertEqual(script.action, 8 if restored == 3 else 7)
                self.assertEqual(script.result['settings_recovery']['fresh_restored_frames'], 3)
                self.assertFalse((root/'finish.json').exists())

    def test_login_event_must_follow_current_readiness_and_cannot_repeat(self):
        ready = {'type': 'client_interaction_ready', 'session_id': SESSION, 'client_pid': PID}
        observed = {'type': 'client_login_ready', 'session_id': SESSION,
                    'client_pid': PID, 'character_list_sent': True}
        terminal = {'type': 'stage', 'stage': 'actual_client_interaction', 'status': 'passed'}
        for prefix, changed in (([], observed), ([ready], dict(observed, client_pid=PID+1)),
                                ([ready], dict(observed, character_list_sent=False)),
                                ([ready], dict(observed, client_pid=float(PID))),
                                ([ready, observed], observed), ([ready, terminal], observed)):
            with self.subTest(prefix=prefix, changed=changed), tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary)/'events'
                path.write_text(''.join(json.dumps(item)+'\n' for item in prefix+[changed]))
                with self.assertRaisesRegex(ValueError, 'local login event'):
                    host.ClientEvents(path, SESSION).poll()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'events'
            path.write_text(json.dumps(ready)+'\n'+json.dumps(dict(observed, session_id='f'*32))+'\n')
            events = host.ClientEvents(path, SESSION)
            events.poll()
            self.assertEqual(events.login_generation, 0)
            raw = json.dumps(observed)
            with path.open('a') as stream: stream.write(raw[:20])
            events.poll()
            self.assertEqual(events.login_generation, 0)
            with path.open('a') as stream: stream.write(raw[20:]+'\n')
            events.poll()
            self.assertEqual(events.login_generation, 1)

    def test_observer_keeps_pre_login_request_generation_when_event_arrives_with_pixels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            event_path = root/'events'
            event_path.write_text(json.dumps({'type': 'client_interaction_ready',
                'session_id': SESSION, 'client_pid': PID})+'\n')
            seen = []
            clock = [0.0]

            class Frames(Connection):
                requests = 0

                def sendall(self, data):
                    super().sendall(data)
                    self.requests += 1
                    if self.requests == 2:
                        with event_path.open('a') as stream:
                            stream.write(json.dumps({'type': 'client_login_ready', 'session_id': SESSION,
                                'client_pid': PID, 'character_list_sent': True})+'\n')
                    if self.requests == 4:
                        with event_path.open('a') as stream:
                            stream.write(json.dumps({'type': 'stage', 'stage': 'actual_client_interaction',
                                'status': 'passed'})+'\n')
                        raise BrokenPipeError()
                    pixels = b''.join(bytes((value, value, value, 0)) for value in range(8))
                    self.data.extend(b'\0'+struct.pack('!BH', 0, 1)+struct.pack('!HHHHi', 0, 0, 8, 1, 0)+pixels)

            class Observer:
                def __init__(self, *args): self.result = {}
                def on_frame(self, connection, frame, events, sequence, captures, now):
                    seen.append((sequence, events.login_generation, frame.request_login_generation))

            process = mock.Mock()
            process.poll.return_value = None
            with mock.patch.object(host, 'client_rfb_handshake', return_value='desktop'), \
                 mock.patch.object(host.time, 'monotonic', side_effect=lambda: clock[0]), \
                 mock.patch.object(host.time, 'sleep', side_effect=lambda seconds: clock.__setitem__(0, clock[0]+seconds)), \
                 mock.patch.object(host, 'save_png', side_effect=save):
                result = host.observe_rfb(Frames(), SESSION, process, 20, root,
                    event_path, root/'finish.json', Observer)
            self.assertIsNone(result['failure'])
            self.assertEqual(seen, [(1, 0, 0), (2, 1, 0), (3, 1, 1)])


if __name__ == '__main__':
    unittest.main()
