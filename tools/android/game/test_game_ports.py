"""Real socket regressions for the restart preflight, including TCP TIME_WAIT."""
import errno
from pathlib import Path
import socket
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'android/guest'))
import game_diagnostic as guest


class GamePortTests(unittest.TestCase):
    def test_stopped_tcp_connection_does_not_block_restart(self):
        with socket.socket() as listener, socket.socket() as client:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
            listener.listen(1)
            client.settimeout(2)
            client.connect(('127.0.0.1', port))
            with listener.accept()[0] as accepted:
                accepted.settimeout(2)
                accepted.shutdown(socket.SHUT_WR)
                self.assertEqual(client.recv(1), b'')
                client.close()
                self.assertEqual(accepted.recv(1), b'')
        # Confirm this exercises the precise old failure, not an unused port.
        with socket.socket() as old_check:
            with self.assertRaises(OSError) as failure:
                old_check.bind(('0.0.0.0', port))
            self.assertEqual(failure.exception.errno, errno.EADDRINUSE)
        guest.check_game_port(port, socket.SOCK_STREAM)

    def test_live_reusable_tcp_listener_is_still_rejected(self):
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            with self.assertRaises(OSError) as failure:
                guest.check_game_port(listener.getsockname()[1], socket.SOCK_STREAM)
            self.assertEqual(failure.exception.errno, errno.EADDRINUSE)

    def test_live_udp_socket_is_still_rejected(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(('127.0.0.1', 0))
            with self.assertRaises(OSError) as failure:
                guest.check_game_port(listener.getsockname()[1], socket.SOCK_DGRAM)
            self.assertEqual(failure.exception.errno, errno.EADDRINUSE)


if __name__ == '__main__':
    unittest.main()
