import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import stack_probe_receipt as probe
import host_game_smoke as host


class ObserverReceiptTests(unittest.TestCase):
    def test_receipt_rejects_changed_bytes_source_commit_and_link(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = root / 'GameStackProbe.exe'
            executable.write_bytes(b'original')
            with mock.patch.object(probe, 'pe_info', return_value={'pe_machine': 0x14c}):
                original = probe.receipt(root, 'a' * 40)
                (root / 'stack-probe-build.json').write_text(json.dumps(original))
                self.assertEqual(probe.verify(root, 'a' * 40), original)
                with self.assertRaisesRegex(ValueError, 'differs'):
                    probe.verify(root, 'b' * 40)
                executable.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, 'differs'):
                    probe.verify(root, 'a' * 40)
                executable.unlink()
                executable.symlink_to(root / 'stack-probe-build.json')
                with self.assertRaisesRegex(ValueError, 'linked'):
                    probe.verify(root, 'a' * 40)

    def test_hang_export_refuses_unknown_or_oversized_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state, evidence = root / 'state', root / 'evidence'
            source = state / 'game-hang-captures'
            source.mkdir(parents=True)
            evidence.mkdir()
            snapshot = source / 'snapshot.json'
            snapshot.write_text('{}')
            unknown = source / 'private-data.txt'
            unknown.write_text('not diagnostic')
            with self.assertRaisesRegex(RuntimeError, 'unexpected name'):
                host.copy_hang_captures(state, evidence)
            unknown.unlink()
            snapshot.write_bytes(b'x' * (4 * 1024 * 1024 + 1))
            with self.assertRaisesRegex(RuntimeError, 'bounds'):
                host.copy_hang_captures(state, evidence)
            self.assertFalse((evidence / 'game-hang-captures').exists())


if __name__ == '__main__':
    unittest.main()
