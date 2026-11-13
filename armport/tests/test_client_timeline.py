"""0.13.70: the client's own record of reaching a zone server.

Thor 0.13.69 (export 20261113-015905): the client log says it was connected 235.0 s after the
guest started; the supervisor's `connected`, read from the delayed server log, came at 306.8 s.
The checked-in function is executed unchanged, without importing the guest module it lives in.
"""
import ast
import datetime
from pathlib import Path
import re
import unittest

GUEST = Path(__file__).resolve().parents[2] / 'armport/app/armport_interactive.py'
LOG = '''[2026-11-13 01:41:01.206] [INFO] Running City of Heroes
[2026-11-13 01:43:07.900] [INFO] Connecting to MapServer 127.0.0.1:7004 (UDP) Cookie: a73d4c6
ArmPort zone: 2213580 ready.sent  tid=828
[2026-11-13 01:43:25.632] [INFO] Established successful MapServer connection
ARMPORT_FRAME_RATE_V1 fps=60.68 frames=304 seconds=5.01 maxfps=60 menu=10
[2026-11-13 01:50:21.114] [INFO] Connecting to MapServer 127.0.0.1:7005 (UDP) Cookie: 53df4c58
[2026-11-13 01:50:40.162] [INFO] Established successful MapServer connection
'''


def load():
    tree = ast.parse(GUEST.read_text())
    wanted = [node for node in tree.body
              if (isinstance(node, ast.Assign) and getattr(node.targets[0], 'id', '') == 'CLIENT_MAP_LINE')
              or (isinstance(node, ast.FunctionDef) and node.name == 'client_timeline')]
    assert len(wanted) == 2
    namespace = {'re': re, 'datetime': datetime}
    exec(compile(ast.Module(body=wanted, type_ignores=[]), str(GUEST), 'exec'), namespace)
    return namespace['client_timeline']


class ClientTimeline(unittest.TestCase):
    def test_thor_launch_c(self):
        record = load()(LOG, '2026-11-13T01:39:30.660965+00:00', '2026-11-13T01:44:37.492496+00:00')
        self.assertEqual([row['port'] for row in record['connections']], [7004, 7005])
        self.assertEqual(record['connections'][0]['connected_utc'], '2026-11-13T01:43:25.632000+00:00')
        self.assertEqual(record['first_connected_seconds_after_guest_start'], 235.0)
        self.assertEqual(record['observer_seconds_after_client'], 71.9)
        self.assertIs(record['is_success_proof'], False)

    def test_no_connection_and_bad_times(self):
        self.assertEqual(load()('nothing here\n')['connections'], [])
        record = load()(LOG, 'not a time', None, limit=1)
        self.assertEqual(len(record['connections']), 1)
        self.assertNotIn('first_connected_seconds_after_guest_start', record)

    def test_launcher_records_it_without_failing_the_session(self):
        source = GUEST.read_text()
        self.assertIn("report['armport_client_timeline'] = client_timeline(", source)
        self.assertIn("self.ctx.report['armport_client_timeline'] = {'format': 1, 'error_type'", source)


if __name__ == '__main__':
    unittest.main()
