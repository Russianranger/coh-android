import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from client_stdio import read_stdio, MAX_BYTES


class StartupLogTests(unittest.TestCase):
    def test_early_renderer_evidence_survives_asset_noise(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'stdio.txt'
            prefix = 'OpenGL Renderer: llvmpipe\nRenderer initialization complete\n'
            log.write_text(prefix + 'missing asset\n' * 100000 + 'Loaded all data!\n')
            text = read_stdio(log)
            self.assertTrue(text.startswith(prefix))
            self.assertIn('Loaded all data!', text)
            self.assertGreater(log.stat().st_size, 1024 * 1024)
            with log.open('r+b') as stream:
                stream.truncate(MAX_BYTES + 1)
            with self.assertRaises(ValueError):
                read_stdio(log)


if __name__ == '__main__':
    unittest.main()
