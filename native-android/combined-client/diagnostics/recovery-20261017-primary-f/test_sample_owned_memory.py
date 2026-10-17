import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sample_owned_memory as m


class OwnedMemory(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.proc = Path(self.temp.name)
        self.process(7, 1, 101, rss=20, pss=10)

    def process(self, pid, parent, start, *, uid=55, rss=4, pss=3):
        path = self.proc / str(pid)
        path.mkdir(exist_ok=True)
        tail = ['S', str(parent)] + ['0'] * 17 + [str(start)]
        (path / 'stat').write_text(str(pid) + ' (private ) account ( comm) ' + ' '.join(tail))
        (path / 'status').write_text(f'Name:\tprivate-account\nUid:\t{uid}\t{uid}\t{uid}\t{uid}\nVmRSS:\t{rss} kB\n')
        if pss is not None:
            (path / 'smaps_rollup').write_text(f'Pss: {pss} kB\n')

    def sample(self):
        return m.sample(self.proc, 7, 101, uid=55)

    def test_descendants_arbitrary_enumeration_and_exclude_unrelated(self):
        self.process(4, 8, 102)
        self.process(8, 7, 103)
        self.process(99, 1, 104, uid=66, rss=50000)
        result = self.sample()
        self.assertEqual(result['observed_processes'], 3)
        self.assertEqual(result['rss_sum_kib'], 28)
        self.assertEqual(result['enumerated_process_pss_sum_kib'], 16)
        self.assertFalse(result['whole_process_tree_peak_measured'])
        self.assertFalse(result['process_tree_membership_atomic'])
        self.assertNotIn('private', json.dumps(result))

    def test_reused_root_refused(self):
        with self.assertRaisesRegex(ValueError, 'ROOT_REUSED'):
            m.sample(self.proc, 7, 999, uid=55)

    def test_cross_uid_descendant_refused(self):
        self.process(8, 7, 102, uid=66)
        with self.assertRaisesRegex(ValueError, 'UID_OWNERSHIP'):
            self.sample()

    def test_setuid_process_refused(self):
        (self.proc / '7/status').write_text('Uid: 55 0 55 55\nVmRSS: 20 kB\n')
        with self.assertRaisesRegex(ValueError, 'UID_OWNERSHIP'):
            self.sample()

    def test_missing_pss_never_partial_sum(self):
        self.process(8, 7, 102, pss=None)
        out = self.sample()
        self.assertEqual(out['pss_available_processes'], 1)
        self.assertIsNone(out['enumerated_process_pss_sum_kib'])

    def test_selected_reparent_or_reuse_refused(self):
        self.process(8, 7, 102)
        original = m.metrics
        for parent, start in ((1, 102), (7, 103)):
            self.process(8, 7, 102)
            def changed(proc, pid, uid):
                result = original(proc, pid, uid)
                if pid == 8:
                    self.process(8, parent, start)
                return result
            with patch.object(m, 'metrics', side_effect=changed):
                with self.assertRaisesRegex(ValueError, 'SELECTED_IDENTITY_CHANGED'):
                    self.sample()

    def test_missing_rss_refused(self):
        (self.proc / '7/status').write_text('Uid: 55 55 55 55\n')
        with self.assertRaisesRegex(ValueError, 'RSS_UNAVAILABLE'):
            self.sample()

    def test_duplicate_pss_refused(self):
        (self.proc / '7/smaps_rollup').write_text('Pss: 1 kB\nPss: 2 kB\n')
        with self.assertRaisesRegex(ValueError, 'PSS_FORMAT'):
            self.sample()

    def test_large_file_refused(self):
        (self.proc / '7/stat').write_bytes(b'x' * (m.MAX_FILE + 1))
        with self.assertRaisesRegex(ValueError, 'PROC_FILE_BOUND'):
            self.sample()

    def test_owned_count_bound_refused(self):
        self.process(8, 7, 102)
        with patch.object(m, 'MAX_OWNED', 1):
            with self.assertRaisesRegex(ValueError, 'OWNED_PROCESS_BOUND'):
                self.sample()

    def test_process_scan_bound_refused(self):
        self.process(8, 1, 102)
        with patch.object(m, 'MAX_PIDS', 1):
            with self.assertRaisesRegex(ValueError, 'PROCESS_SCAN_BOUND'):
                self.sample()

    def test_pid_stat_disagreement_refused(self):
        path = self.proc / '7/stat'
        path.write_text(path.read_text().replace('7 (', '9 (', 1))
        with self.assertRaisesRegex(ValueError, 'STAT_PID'):
            self.sample()

    def test_bool_identity_refused(self):
        with self.assertRaisesRegex(ValueError, 'ROOT_IDENTITY_REQUIRED'):
            m.sample(self.proc, True, 101, uid=55)

    def test_read_only_files(self):
        before = {p.relative_to(self.proc): p.read_bytes() for p in self.proc.rglob('*') if p.is_file()}
        self.sample()
        after = {p.relative_to(self.proc): p.read_bytes() for p in self.proc.rglob('*') if p.is_file()}
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
