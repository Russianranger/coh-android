"""Compile the real x86 producer; observe it through a separate live reader."""
import json
import mmap
import os
from pathlib import Path
import queue
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[3]
OVERLAY = ROOT / 'database/mapserver-progress/overlay/MapServer/src/svr'
CONTRACT = ROOT / 'database/mapserver-progress/tests/progress_contract.c'
ENVIRONMENT = 'COH_WINE_MAP_PROGRESS'
RECORD = struct.Struct('<8s10I')


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


@unittest.skipUnless(os.name == 'nt', 'live MapServer progress mapping requires Windows')
class MapserverProgressWindowsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('cl'):
            raise RuntimeError('x86 MSVC environment must be initialized for Windows progress tests')
        cls.build = tempfile.TemporaryDirectory(prefix='coh-map-progress-build-')
        build = Path(cls.build.name)
        cls.binary = build / 'map-progress-contract.exe'
        cls.assembly = build / 'wine_map_progress.asm'
        obj = build / 'wine_map_progress.obj'
        common = ['cl', '/nologo', '/W4', '/WX', '/O2', '/MT', '/D_WIN32_WINNT=0x0601', f'/I{OVERLAY}']
        try:
            subprocess.run([*common, '/c', '/FAs', f'/Fa{cls.assembly}', f'/Fo:{obj}',
                            str(OVERLAY / 'wine_map_progress.c')], cwd=build, check=True)
            subprocess.run([*common, str(CONTRACT), str(obj), f'/Fe:{cls.binary}'],
                           cwd=build, check=True)
        except BaseException:
            cls.build.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.build.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='coh-map-progress-case-')
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

    def finish(self, producer, command='close'):
        result = 'closed' if command == 'close' else 'closed-and-marked'
        self.assertEqual(producer.send(command), {'kind': result})
        self.assertEqual(producer.process.wait(timeout=10), 0)
        producer.reader.join(timeout=10)
        self.assertEqual(producer.process.stderr.read(), '')

    def record(self, shared, ready):
        raw = shared[:128]
        values = RECORD.unpack_from(raw)
        self.assertEqual(values[:3], (b'COHMAP1\0', 1, 128))
        names = ('pid', 'tid', 'sequence', 'stage', 'tick_started', 'tick_completed', 'flags', 'stage_count')
        result = dict(zip(names, values[3:]))
        self.assertEqual((result['pid'], result['tid']), (ready['pid'], ready['tid']))
        self.assertGreater(result['sequence'], 0)
        self.assertEqual(result['sequence'] % 2, 0)
        self.assertEqual(result['flags'], 0)
        self.assertEqual(result['stage_count'], 37)
        self.assertEqual(raw[RECORD.size:], bytes(128 - RECORD.size))
        return result

    def test_compiled_marker_has_no_calls_locks_or_interlocked_instructions(self):
        assembly = self.assembly.read_text(errors='replace')
        match = re.search(r'^_cohMapProgressMark\s+PROC\b(.*?)^_cohMapProgressMark\s+ENDP\b',
                          assembly, re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(match, 'MSVC assembly must expose the actual producer marker')
        # Ignore source comments; inspect only assembly instruction lines.
        instructions = '\n'.join(line.split(';', 1)[0] for line in match[1].splitlines())
        self.assertNotRegex(instructions, r'(?im)^\s*(?:call|lock|xchg|cmpxchg|rdtsc|rdtscp)\b')

    def test_disabled_mode_has_no_file_or_thread_and_markers_are_noops(self):
        producer, ready = self.start()
        self.assertEqual(ready['status'], 0)
        for stage in (24, 26, 28, 34):
            self.assertEqual(producer.send(f'mark {stage}'), {'kind': 'marked', 'stage': stage})
        self.finish(producer)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_live_external_reader_observes_every_stage_and_distinct_tick_counters(self):
        path = self.root / 'map-progress.bin'
        producer, ready = self.start(path)
        self.assertEqual(ready['status'], 1)
        self.assertEqual(path.stat().st_size, 4096)
        with path.open('rb') as handle, mmap.mmap(handle.fileno(), 4096, access=mmap.ACCESS_READ) as shared:
            current = self.record(shared, ready)
            self.assertEqual((current['sequence'], current['stage'], current['tick_started'],
                              current['tick_completed']), (2, 1, 0, 0))
            started = completed = 0
            for stage in (*range(2, 38), 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37):
                previous = current
                self.assertEqual(producer.send(f'mark {stage}'), {'kind': 'marked', 'stage': stage})
                started += stage == 24
                completed += stage == 34
                current = self.record(shared, ready)
                self.assertEqual((current['stage'], current['tick_started'], current['tick_completed']),
                                 (stage, started, completed))
                self.assertEqual(current['sequence'], previous['sequence'] + 2)
            self.assertEqual(shared[128:], bytes(4096 - 128))
            final = shared[:]
            self.finish(producer, 'close-and-mark')
            self.assertEqual(shared[:], final, 'close and subsequent no-op marker must retain last observation')
        self.assertEqual(path.read_bytes(), final)

    def test_reinitialization_is_refused_without_replacing_live_publication(self):
        path = self.root / 'map-progress.bin'
        producer, ready = self.start(path)
        self.assertEqual(ready['status'], 1)
        before = path.read_bytes()
        reply = producer.send('init-again')
        self.assertEqual((reply['kind'], reply['status']), ('reinitialized', -1))
        self.assertNotEqual(reply['error'], 0)
        self.assertEqual(path.read_bytes(), before)
        self.finish(producer)

    def test_existing_file_is_refused_without_modifying_evidence(self):
        path = self.root / 'already-present.bin'
        original = b'previous MapServer evidence must survive\0' * 19
        path.write_bytes(original)
        producer, ready = self.start(path)
        self.assertEqual(ready['status'], -1)
        self.assertNotEqual(ready['error'], 0)
        producer.send('mark 24')
        self.finish(producer)
        self.assertEqual(path.read_bytes(), original)

    def test_relative_drive_relative_unc_missing_parent_and_directory_paths_are_refused(self):
        for path in ('relative.bin', 'C:drive-relative.bin', r'\\localhost\unavailable\map.bin',
                     self.root / 'missing' / 'progress.bin', self.root):
            with self.subTest(path=str(path)):
                producer, ready = self.start(path)
                self.assertEqual(ready['status'], -1)
                self.assertNotEqual(ready['error'], 0)
                producer.send('mark 24')
                self.finish(producer)
                self.assertEqual(list(self.root.iterdir()), [])


if __name__ == '__main__':
    if '--require-windows' in sys.argv:
        sys.argv.remove('--require-windows')
        if os.name != 'nt' or not shutil.which('cl'):
            raise SystemExit('Windows contracts require an initialized x86 MSVC environment')
    unittest.main(verbosity=2)
