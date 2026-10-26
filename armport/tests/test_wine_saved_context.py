"""A wrong TEB/layout/stack must never produce a plausible game stack."""
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from arm64_wine_context import saved_context


class WineContextTests(unittest.TestCase):
    def setUp(self):
        self.memory = bytearray(0x10000)
        self.teb, self.frame, self.sp = 0x1000, 0x2000, 0x8000
        self.put(self.teb + 8, 0xa000, 0x7000)
        self.put(self.teb + 48, self.teb)
        self.put(self.teb + 0x2f0, self.frame)
        self.put(self.frame + 0xe8, self.sp, 0x140001000, self.sp, 0x6fffff001000)
        self.put(self.sp, self.sp + 0x20, 0x140002000)
        self.put(self.sp + 0x20, 0, 0x140003000)
        self.reads = []

    def put(self, address, *values):
        struct.pack_into('<' + 'Q' * len(values), self.memory, address, *values)

    def read(self, address, size):
        self.reads.append((address, size))
        return self.memory[address:address+size]

    def test_reads_saved_windows_chain(self):
        state = saved_context(self.read, self.teb)
        self.assertEqual(state['sp'], self.sp)
        self.assertEqual([ret for _, ret in state['frames']], [0x140002000, 0x140003000])

    def test_rejects_wrong_self_before_syscall_frame(self):
        self.put(self.teb + 48, 0x1234)
        with self.assertRaisesRegex(ValueError, 'self pointer'):
            saved_context(self.read, self.teb)
        self.assertEqual(len(self.reads), 1)

    def test_rejects_saved_sp_outside_stack(self):
        self.put(self.frame + 0xf8, 0x6000)
        with self.assertRaisesRegex(ValueError, 'outside Windows stack'):
            saved_context(self.read, self.teb)

    def test_cyclic_and_excessive_chains_are_bounded(self):
        self.put(self.sp, self.sp, 0x140002000)
        self.assertEqual(len(saved_context(self.read, self.teb)['frames']), 1)
        for i in range(30):
            self.put(self.sp + 16*i, self.sp + 16*(i+1), 0x140002000)
        self.assertEqual(len(saved_context(self.read, self.teb)['frames']), 16)


if __name__ == '__main__':
    unittest.main()
