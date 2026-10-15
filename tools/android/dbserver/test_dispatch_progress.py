"""Exercise the real Win32 progress producer with an independent external reader."""
import json
import mmap
import os
from pathlib import Path
import queue
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[3]
OVERLAY = ROOT / 'database/wine-dbserver/overlay/DBServer/src'
CONTRACT = ROOT / 'database/wine-dbserver/tests/dispatch_progress_contract.c'
ENVIRONMENT = 'COH_WINE_DB_PROGRESS'
RECORD = struct.Struct('<8s9I')


class Producer:
    def __init__(self, executable, directory, path=None):
        env = os.environ.copy()
        env.pop(ENVIRONMENT, None)
        if path is not None:
            env[ENVIRONMENT] = str(path)
        self.process = subprocess.Popen([str(executable)], cwd=directory, env=env,
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, bufsize=1)
        self.lines = queue.Queue()

        def read():
            for line in self.process.stdout:
                self.lines.put(line)
            self.lines.put(None)

        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()

    def receive(self):
        try:
            line = self.lines.get(timeout=10)
        except queue.Empty as exc:
            raise AssertionError('progress contract did not respond within 10 seconds') from exc
        if line is None:
            raise AssertionError('progress contract exited before its response')
        return json.loads(line)

    def send(self, command):
        self.process.stdin.write(command + '\n')
        self.process.stdin.flush()
        return self.receive()

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
        self.process.wait(timeout=10)
        self.reader.join(timeout=10)
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            stream.close()


@unittest.skipUnless(os.name == 'nt', 'live progress mapping requires Windows')
class DispatchProgressWindowsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('cl'):
            raise RuntimeError('x86 MSVC environment must be initialized for Windows progress tests')
        cls.build = tempfile.TemporaryDirectory(prefix='coh-progress-build-')
        cls.binary = Path(cls.build.name) / 'dispatch-progress-contract.exe'
        try:
            subprocess.run(['cl', '/nologo', '/W4', '/WX', '/O2', '/MT', '/D_WIN32_WINNT=0x0601',
                            f'/I{OVERLAY}', str(CONTRACT), str(OVERLAY / 'wine_dispatch_progress.c'),
                            f'/Fe:{cls.binary}'], cwd=cls.build.name, check=True)
        except BaseException:
            cls.build.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.build.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='coh-progress-case-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def start(self, path=None):
        producer = Producer(self.binary, self.root, path)
        self.addCleanup(producer.close)
        ready = producer.receive()
        self.assertEqual(ready['kind'], 'ready')
        self.assertEqual(ready['pid'], producer.process.pid)
        self.assertGreater(ready['tid'], 0)
        self.assertGreater(ready['threads_before'], 0)
        self.assertEqual(ready['threads_before'], ready['threads_after'], 'producer must not start a thread')
        return producer, ready

    def finish(self, producer):
        self.assertEqual(producer.send('close'), {'kind': 'closed'})
        self.assertEqual(producer.process.wait(timeout=10), 0)
        producer.reader.join(timeout=10)
        self.assertEqual(producer.process.stderr.read(), '')

    def record(self, shared, ready):
        raw = shared[:128]
        values = RECORD.unpack_from(raw)
        self.assertEqual(values[:3], (b'COHDBP1\0', 1, 128))
        names = ('pid', 'tid', 'sequence', 'stage', 'loop_count', 'flags', 'stage_count')
        result = dict(zip(names, values[3:]))
        self.assertEqual((result['pid'], result['tid']), (ready['pid'], ready['tid']))
        self.assertGreater(result['sequence'], 0)
        self.assertEqual(result['sequence'] % 2, 0, 'published record must finish its update')
        self.assertEqual(result['flags'], 0)
        self.assertEqual(result['stage_count'], 37)
        self.assertEqual(raw[RECORD.size:], bytes(128 - RECORD.size))
        return result

    def test_disabled_mode_has_no_file_or_thread_and_marker_calls_remain_noops(self):
        producer, ready = self.start()
        self.assertEqual(ready['status'], 0)
        self.assertEqual(producer.send('mark 4'), {'kind': 'marked', 'stage': 4})
        self.assertEqual(producer.send('mark 5'), {'kind': 'marked', 'stage': 5})
        self.finish(producer)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_enabled_mapping_is_visible_externally_with_identity_and_ordered_progress(self):
        path = self.root / 'dispatch.bin'
        producer, ready = self.start(path)
        self.assertEqual(ready['status'], 1)
        self.assertEqual(path.stat().st_size, 4096)
        with path.open('rb') as handle, mmap.mmap(handle.fileno(), 4096, access=mmap.ACCESS_READ) as shared:
            initialized = self.record(shared, ready)
            self.assertEqual((initialized['sequence'], initialized['stage'], initialized['loop_count']), (2, 1, 0))
            previous = initialized
            for stage, loops in ((4, 1), (5, 1), (4, 2), (5, 2)):
                self.assertEqual(producer.send(f'mark {stage}'), {'kind': 'marked', 'stage': stage})
                current = self.record(shared, ready)
                self.assertEqual(current['stage'], stage)
                self.assertEqual(current['loop_count'], loops)
                self.assertEqual(current['sequence'], previous['sequence'] + 2)
                self.assertEqual(current['stage_count'], initialized['stage_count'])
                previous = current
            self.assertEqual(shared[128:], bytes(4096 - 128))
            final = shared[:]
            self.finish(producer)
            self.assertEqual(shared[:], final, 'closing must retain the last observation')
        self.assertEqual(path.read_bytes(), final)

    def test_existing_file_is_refused_without_modifying_evidence(self):
        path = self.root / 'already-present.bin'
        original = b'previous evidence must survive\0' * 19
        path.write_bytes(original)
        producer, ready = self.start(path)
        self.assertEqual(ready['status'], -1)
        self.assertNotEqual(ready['error'], 0)
        producer.send('mark 4')
        self.finish(producer)
        self.assertEqual(path.read_bytes(), original)

    def test_relative_missing_parent_and_directory_paths_are_refused(self):
        for path in ('relative.bin', self.root / 'missing' / 'progress.bin', self.root):
            with self.subTest(path=str(path)):
                producer, ready = self.start(path)
                self.assertEqual(ready['status'], -1)
                self.assertNotEqual(ready['error'], 0)
                producer.send('mark 5')
                self.finish(producer)
                self.assertEqual(list(self.root.iterdir()), [])


if __name__ == '__main__':
    if '--require-windows' in sys.argv:
        sys.argv.remove('--require-windows')
        if os.name != 'nt' or not shutil.which('cl'):
            raise SystemExit('Windows contracts require an initialized x86 MSVC environment')
    unittest.main(verbosity=2)
