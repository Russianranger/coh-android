"""A map server source that includes file.h has fflush(f) defined as x_fflush(f), which takes
the game's FileWrapper. Given the C runtime's stdout it reads a wrong structure and asserts:
0.13.82's first build ended its zone server when the first client arrived (run 45352283396).
MSVC compiles it with a warning only, so the layers are checked as text."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]


class ServerConsoleFlush(unittest.TestCase):
    def test_no_map_server_layer_flushes_the_c_runtime_stdout(self):
        patches = sorted((ROOT / 'patches').glob('mapserver-*/*.patch'))
        self.assertGreaterEqual(len(patches), 9)
        for patch in patches:
            added = [line for line in patch.read_text(errors='replace').splitlines()
                     if line.startswith('+') and not line.startswith('+++')]
            for line in added:
                self.assertNotIn('fflush(stdout)', line, patch.name)

    def test_the_client_ready_line_is_flushed_through_the_games_stdout(self):
        text = (ROOT / 'patches/mapserver-single-player/0001-name-lists-and-ready-line.patch').read_text()
        ready = text.index('ARMPORT_CLIENT_READY_V1')
        self.assertIn('+        fflush(fileGetStdout());', text[ready:ready + 400])


if __name__ == '__main__':
    unittest.main()
