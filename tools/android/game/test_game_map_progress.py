"""MapServer observer records are bounded, source-scoped diagnostics, never readiness."""
import copy
import hashlib
import mmap
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import game_diagnostic as guest
import game_map_progress as progress


class MapProgressTests(unittest.TestCase):
    producer = {'repository_commit': 'a' * 40, 'manifest_sha256': 'b' * 64, 'mapserver_sha256': 'c' * 64}

    def record(self, *, magic=b'COHMAP1\0', version=1, size=128, pid=41, tid=42,
               sequence=2, stage=1, started=0, completed=0, flags=0, count=37):
        return progress.HEADER.pack(magic, version, size, pid, tid, sequence, stage,
                                    started, completed, flags, count) + bytes(80)

    def publish(self, path, **values):
        path.write_bytes(self.record(**values) + bytes(progress.MAPPING_BYTES - progress.RECORD_BYTES))

    def phase(self, path, label):
        return {'path_name': path.name, 'process_label': label + '-atlas',
                'fresh_path_before_launch': True, 'launch_monotonic': time.monotonic() - 1,
                'samples': [], 'sample_count': 0, 'dropped_samples': 0}

    def diagnostic(self, root):
        value = object.__new__(guest.GameDiagnostic)
        value.runtime = root
        value.map_progress_contract = {'producer': self.producer}
        value.map_progress_paths, value.map_progress_previous = {}, {}
        value.map_progress_phase, value.map_progress_next_sample = None, 0
        value.game = {'mapserver_progress': progress.evidence(self.producer)}
        return value

    def complete_evidence(self, root):
        value = progress.evidence(self.producer)
        for label in ('first', 'restart'):
            path = root / ('coh-map-progress-' + label + '-example.bin')
            phase = self.phase(path, label)
            value['phases'][label] = phase
            self.publish(path)
            first = dict(progress.read_record(path), reason='startup')
            progress.append_sample(phase, first)
            self.publish(path, sequence=6, stage=34, started=1, completed=1)
            second = dict(progress.read_record(path, first), reason='observation')
            progress.append_sample(phase, second)
        return value

    def test_live_mapping_distinguishes_startup_dbcomm_folder_callback_and_completed_tick(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'progress.bin'
            self.publish(path)
            with path.open('r+b') as output, mmap.mmap(output.fileno(), 4096) as mapping:
                previous = progress.read_record(path)
                self.assertEqual(previous['stage'], 'INITIALIZED')
                self.assertEqual(previous['freshness'], 'initial')
                self.assertFalse(previous['is_success_proof'])
                for sequence, stage, name, completed in ((4, 26, 'DB_COMM', 0),
                        (6, 28, 'FOLDER_CALLBACKS', 0), (8, 34, 'TICK_DONE', 1)):
                    mapping[:128] = self.record(sequence=sequence, stage=stage, started=1, completed=completed)
                    sample = progress.read_record(path, previous)
                    self.assertEqual(sample['stage'], name)
                    self.assertEqual(sample['freshness'], 'advanced')
                    self.assertEqual(sample['raw_record_sha256'], hashlib.sha256(mapping[:128]).hexdigest())
                    previous = sample
                stalled = progress.read_record(path, previous)
                self.assertEqual(stalled['freshness'], 'unchanged')
                self.assertEqual(stalled['last_advance_monotonic'], previous['last_advance_monotonic'])

    def test_torn_and_odd_publications_have_a_fixed_read_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'progress.bin'
            self.publish(path, sequence=3)
            with patch.object(progress.time, 'sleep'):
                with self.assertRaises(progress.PublicationPending):
                    progress.read_record(path)
                alternating = [self.record(sequence=2), self.record(sequence=4)] * 16
                with patch.object(progress.os, 'pread', side_effect=alternating) as pread:
                    with self.assertRaises(progress.PublicationPending):
                        progress.read_record(path)
                self.assertEqual(pread.call_count, 32)
                with patch.object(progress.os, 'pread', side_effect=[self.record(sequence=3)] * 2
                        + [self.record(sequence=4)] * 2):
                    self.assertEqual(progress.read_record(path)['sequence'], 4)

    def test_malformed_record_dimensions_identity_flags_counters_and_reserved_bytes_fail(self):
        mutations = ({'magic': b'COHDBP1\0'}, {'version': 2}, {'size': 127}, {'pid': 0}, {'tid': 0},
                     {'stage': 0}, {'stage': 38}, {'count': 36}, {'flags': 1}, {'flags': 2},
                     {'started': 0, 'completed': 1}, {'started': 2, 'completed': 0})
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'progress.bin'
            for values in mutations:
                with self.subTest(values=values):
                    self.publish(path, **values)
                    with self.assertRaises(guest.base.DiagnosticError):
                        progress.read_record(path)
            path.write_bytes(self.record()[:-1] + b'X' + bytes(4096 - 128))
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'reserved'):
                progress.read_record(path)

    def test_regressed_or_changed_identity_and_same_sequence_changed_payload_fail(self):
        changes = ({'pid': 99, 'sequence': 10, 'started': 2, 'completed': 2},
                   {'tid': 99, 'sequence': 10, 'started': 2, 'completed': 2},
                   {'sequence': 6, 'started': 2, 'completed': 2},
                   {'sequence': 10, 'started': 1, 'completed': 1},
                   {'sequence': 8, 'stage': 28, 'started': 2, 'completed': 2})
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'progress.bin'
            self.publish(path, sequence=8, started=2, completed=2)
            previous = progress.read_record(path)
            for values in changes:
                with self.subTest(values=values):
                    self.publish(path, **values)
                    with self.assertRaises(guest.base.DiagnosticError):
                        progress.read_record(path, previous)
            replacement = path.with_name('replacement.bin')
            self.publish(replacement, sequence=10, started=2, completed=2)
            os.replace(replacement, path)
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'identity changed'):
                progress.read_record(path, previous)

    def test_replacement_during_pending_read_is_not_classified_as_pending(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'progress.bin'
            replacement = path.with_name('replacement.bin')
            self.publish(path, sequence=3)
            self.publish(replacement)
            pread = os.pread
            def replace(*args):
                raw = pread(*args)
                if replacement.exists():
                    os.replace(replacement, path)
                return raw
            with patch.object(progress.os, 'pread', side_effect=replace), patch.object(progress.time, 'sleep'):
                with self.assertRaisesRegex(guest.base.DiagnosticError, 'changed identity') as caught:
                    progress.read_record(path)
                self.assertNotIsInstance(caught.exception, progress.PublicationPending)

    def test_nonregular_linked_foreign_and_oversized_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'progress.bin'
            self.publish(path)
            with patch.object(progress.os, 'getuid', return_value=os.getuid() + 1):
                with self.assertRaisesRegex(guest.base.DiagnosticError, 'owned bounded'):
                    progress.read_record(path)
            hardlink = path.with_name('hardlink.bin')
            os.link(path, hardlink)
            with self.assertRaises(guest.base.DiagnosticError):
                progress.read_record(path)
            hardlink.unlink()
            link = path.with_name('linked.bin')
            link.symlink_to(path)
            with self.assertRaises(OSError):
                progress.read_record(link)
            path.write_bytes(bytes(4097))
            with self.assertRaises(guest.base.DiagnosticError):
                progress.read_record(path)
            fifo = path.with_name('pipe')
            os.mkfifo(fifo)
            with self.assertRaises(guest.base.DiagnosticError):
                progress.read_record(fifo)

    def test_phase_paths_are_unique_and_sampling_errors_do_not_change_readiness(self):
        with tempfile.TemporaryDirectory() as temporary:
            value = self.diagnostic(Path(temporary))
            for label in ('first', 'restart'):
                value.begin_map_progress(label)
                phase = value.game['mapserver_progress']['phases'][label]
                self.assertEqual(phase['samples'][0]['error_type'], 'FileNotFoundError')
                self.publish(value.map_progress_paths[label], sequence=3)
                with patch.object(progress.time, 'sleep'):
                    observed = value.sample_map_progress('startup', force=True)
                self.assertFalse(observed['available'])
                self.assertEqual(observed['error_type'], 'PublicationPending')
                with self.assertRaisesRegex(guest.base.DiagnosticError, 'fresh owned launch'):
                    value.begin_map_progress(label)
            self.assertNotEqual(value.map_progress_paths['first'], value.map_progress_paths['restart'])
            value.health = Mock()
            value.ctx = SimpleNamespace(deadline=time.monotonic() + 1)
            predicate = Mock(return_value={'db_confirmed_ready': True})
            self.assertEqual(value.wait(predicate, 1, 'Existing readiness'), {'db_confirmed_ready': True})
            predicate.assert_called_once()
            value.health.side_effect = guest.base.Cancelled('cancelled')
            with patch.object(progress, 'read_record') as probe:
                with self.assertRaises(guest.base.Cancelled):
                    value.wait(predicate, 1, 'Existing readiness')
                probe.assert_not_called()

    def test_history_keeps_initial_window_and_recent_tail_under_fixed_bound(self):
        phase = {'samples': [], 'sample_count': 0, 'dropped_samples': 0}
        for count in range(1000):
            progress.append_sample(phase, {'test': count})
        self.assertEqual(len(phase['samples']), 128)
        self.assertEqual([item['test'] for item in phase['samples'][:16]], list(range(16)))
        self.assertEqual(phase['samples'][-1]['test'], 999)
        self.assertEqual(phase['dropped_samples'], 872)

    def test_bounded_progress_history_is_exported_with_hash_bound_raw_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = self.diagnostic(root)
            value.args = SimpleNamespace(state=root)
            value.sessions, value.snapshots = [], {}
            value.game['sessions'] = {}
            value.game['mapserver_progress'] = self.complete_evidence(root)
            value.export_captures()
            path = root / 'game-captures/mapserver-progress.json'
            raw = path.read_bytes()
            self.assertLess(len(raw), progress.EXPORT_LIMIT)
            self.assertEqual(value.game['capture_files'][path.name],
                             {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})

    def test_host_qualification_checks_raw_record_digests_freshness_phases_and_real_tick_advance(self):
        with tempfile.TemporaryDirectory() as temporary:
            complete = self.complete_evidence(Path(temporary))
            self.assertIs(progress.validate_evidence(complete, self.producer), complete)
            mutations = {
                'digest': lambda v: v['phases']['first']['samples'][1].update(raw_record_sha256='f' * 64),
                'decoded': lambda v: v['phases']['first']['samples'][1].update(stage='DB_COMM'),
                'nan': lambda v: v['phases']['first']['samples'][1].update(observed_monotonic=float('nan')),
                'string-time': lambda v: v['phases']['first']['samples'][1].update(observed_monotonic='100'),
                'false-freshness': lambda v: v['phases']['first']['samples'][1].update(freshness='unchanged'),
                'wrong-age': lambda v: v['phases']['first']['samples'][1].update(unchanged_seconds=9),
                'wrong-producer': lambda v: v['producer'].update(manifest_sha256='f' * 64),
                'missing-phase': lambda v: v['phases'].pop('restart'),
                'shared-file': lambda v: [s.update(file_identity=copy.deepcopy(v['phases']['first']['samples'][0]['file_identity']))
                                           for s in v['phases']['restart']['samples']],
                'no-progress': lambda v: (v['phases']['first'].update(samples=v['phases']['first']['samples'][:1], sample_count=1)),
            }
            for name, mutate in mutations.items():
                with self.subTest(name=name):
                    value = copy.deepcopy(complete)
                    mutate(value)
                    with self.assertRaises(guest.base.DiagnosticError):
                        progress.validate_evidence(value, self.producer)


if __name__ == '__main__':
    unittest.main()
