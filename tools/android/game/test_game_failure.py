import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'android/guest'))
import game_failure


class FailureCaptureTests(unittest.TestCase):
    def test_parse_only_complete_expected_private_game_process_set(self):
        listing = " pid threads executable (all id:s are in hex)\n 000000a0 65       'DbServer.exe'\n 000000bc 4        \\_ 'MapServer.exe'\n 00000100 3        'MapServer.exe'\n=00000104 1        'winedbg.exe'\n"
        self.assertEqual(game_failure.game_pids(listing), [(160, 'DbServer'), (188, 'MapServer'), (256, 'MapServer')])
        for bad in (listing.replace('DbServer.exe', 'Other.exe'),
                    listing.replace('00000100', '000000a0'),
                    listing + " 00000200 1 'MapServer.exe'\n",
                    listing.replace('000000a0', '00000000')):
            with self.assertRaises(ValueError):
                game_failure.game_pids(bad)

    def test_observer_timeout_and_overflow_stop_only_owned_child(self):
        for overflow in (False, True):
            child = SimpleNamespace(process=Mock(), reader=Mock(), overflow=overflow, stop=Mock())
            child.process.poll.return_value = None
            ctx = SimpleNamespace(record=Mock())
            game_failure.finish(ctx, child, time.monotonic() - 1)
            child.stop.assert_called_once_with()
            ctx.record.assert_called_once_with(child, refresh=True)

    def test_completed_observer_is_not_forcibly_stopped(self):
        child = SimpleNamespace(process=Mock(), reader=Mock(), overflow=False, stop=Mock())
        child.process.poll.return_value = 0
        child.reader.is_alive.return_value = False
        game_failure.finish(SimpleNamespace(record=Mock()), child, time.monotonic() + 1)
        child.stop.assert_not_called()
