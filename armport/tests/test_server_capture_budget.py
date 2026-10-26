"""Exercise the original subprocess reader at stock and M3 capture limits."""
import ast
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]

class CaptureBudget(unittest.TestCase):
    def read_bytes(self, limit, count):
        path = ROOT / 'android/guest/diagnostic.py'
        node = next(n for n in ast.parse(path.read_text()).body
                    if isinstance(n, ast.ClassDef) and n.name == 'OwnedProcess')
        ns = dict(subprocess=subprocess, threading=threading, time=time,
                  os=os, OUTPUT_LIMIT=limit)
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), ns)
        child = ns['OwnedProcess']('capture-control', [sys.executable, '-c',
            'import sys; sys.stdout.buffer.write(b"x" * int(sys.argv[1]))', str(count)], os.environ.copy())
        self.assertEqual(child.process.wait(timeout=15), 0)
        child.reader.join(timeout=5)
        child.writer.join(timeout=5)
        self.assertFalse(child.reader.is_alive())
        self.assertLessEqual(len(child.output), limit)
        return child

    def test_original_cap_rejects_longer_capture(self):
        self.assertTrue(self.read_bytes(2*1024*1024, 2*1024*1024+8192).overflow)

    def test_m3_retains_complete_output_and_still_rejects_overflow(self):
        source = (ROOT / 'armport/server/armport_game_guest.py').read_text()
        tree = ast.parse(source)
        nodes = [n for n in tree.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'SERVER_OUTPUT_LIMIT' for t in n.targets)]
        ns = {}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), '<capture-budget>', 'exec'), ns)
        limit = ns['SERVER_OUTPUT_LIMIT']
        self.assertEqual(limit, 8*1024*1024)
        child = self.read_bytes(limit, limit)
        self.assertFalse(child.overflow)
        self.assertEqual(child.output, b'x'*limit)
        self.assertTrue(self.read_bytes(limit, limit+8192).overflow)
