"""Pass the actual C bridge receipts through the guest and host consumers."""
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import host_game_smoke as host

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import game_diagnostic as guest

COMPILER = next((path for name in ('cc', 'gcc', 'clang') if (path := shutil.which(name))), None)


def producer_harness():
    source = (ROOT / 'database/wine-game/TestClientBridge.c').read_text(encoding='utf-8')

    def function(name):
        # The production functions have unindented closing braces. Extract their
        # complete definitions verbatim, including every serialized field.
        match = re.search(r'^static (?:int|void) ' + name + r'\([^\n]*\)\n\{\n.*?^\}',
                          source, re.MULTILINE | re.DOTALL)
        if match is None:
            raise AssertionError('Cannot extract production bridge function: ' + name)
        return match.group()

    constants = '\n'.join(re.findall(
        r'^#define (?:ROWS|CAPTURE_LIMIT|EVENT_LIMIT|PATH_LIMIT) .+$', source, re.MULTILINE))
    return r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
''' + constants + r'''
/* Keep Win32's printf-compatible DWORD spelling; all test values fit uint32. */
typedef unsigned long DWORD;
static struct { DWORD dwProcessId; } child;
static const char *directory, *failure;
static FILE *events;
static unsigned long long started;
static unsigned sequence, event_bytes, command_count, snapshots, version_requests;
static int forced_stop, final_snapshot, framing_complete = 1, disconnected;

/* Only OS/path publication and observation state are supplied by this shim. */
static unsigned long long GetTickCount64(void) { return 0; }
static int fail(const char *reason) { failure = reason; return 0; }
static int path_for(char *path, const char *name)
{
    int n = snprintf(path, PATH_LIMIT, "%s/%s", directory, name);
    return n > 0 && n < PATH_LIMIT ? 1 : fail("fixture output path exceeds bound");
}
static int replace_file(const char *temporary, const char *final)
{
    return rename(temporary, final) == 0 ? 1 : fail("fixture publication failed");
}
''' + '\n\n'.join(function(name) for name in ('json_string', 'event', 'publish_ready', 'result')) + r'''

int main(int argc, char **argv)
{
    char path[PATH_LIMIT];
    FILE *console;
    if (argc != 4) return 2;
    directory = argv[1];
    forced_stop = atoi(argv[2]);
    child.dwProcessId = 42;
    version_requests = command_count = 1;
    snapshots = 2;
    disconnected = final_snapshot = 1;
    if (!path_for(path, "events.jsonl") || !(events = fopen(path, "wb"))) return 3;
    if (!event("PID", "42", "PID: 42", 0) ||
        !event("VersionRequest", "", "VersionRequest:", 0) ||
        !event("Command", "CMD quit", "CMD quit", 1)) return 4;
    if (fclose(events)) return 5;
    if (!path_for(path, "console.txt") || !(console = fopen(path, "wb"))) return 6;
    fputs("bounded final console\n", console);
    if (fclose(console) || !publish_ready()) return 7;
    result(strtoul(argv[3], NULL, 10), 1);
    return failure ? 8 : 0;
}
'''


class BridgeReceiptTests(unittest.TestCase):
    @unittest.skipUnless(COMPILER, 'Native bridge receipt contract requires a C compiler')
    def test_actual_producer_receipts_pass_guest_stop_and_host_validation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, executable = root / 'bridge-receipt.c', root / 'bridge-receipt'
            source.write_text(producer_harness(), encoding='utf-8')
            compiled = subprocess.run([COMPILER, '-std=c99', '-Wall', '-Wextra', '-Werror',
                                       str(source), '-o', str(executable)],
                                      capture_output=True, text=True, timeout=30)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            for forced_stop, exit_code in ((False, 0), (True, 125)):
                with self.subTest(forced_stop=forced_stop, exit_code=exit_code):
                    output = root / ('forced' if forced_stop else 'natural')
                    output.mkdir()
                    subprocess.run([str(executable), str(output), str(int(forced_stop)), str(exit_code)],
                                   check=True, capture_output=True, text=True, timeout=10)
                    # Exercise the real receipt wrapper and file hashing while
                    # supplying the already-finished process and completed proof.
                    session = object.__new__(guest.BridgeSession)
                    session.root = output
                    session.commands = session.acknowledged_commands = 1
                    session.last_event_count = 0
                    session.proof_complete = True
                    session.stopped = False
                    session.ctx = SimpleNamespace(check=Mock(), record=Mock())
                    session.child = SimpleNamespace(
                        process=Mock(returncode=0, poll=Mock(return_value=0)),
                        reader=Mock(is_alive=Mock(return_value=False)))
                    receipt = session.stop()
                    self.assertEqual(receipt['result']['child_exit_code'], exit_code)
                    self.assertIs(receipt['result']['child_forced_stop'], forced_stop)
                    for filename, field in (('console.txt', 'console_sha256'),
                                            ('events.jsonl', 'events_sha256')):
                        self.assertEqual(receipt[field], hashlib.sha256((output / filename).read_bytes()).hexdigest())
                    host.validate_session(receipt)


if __name__ == '__main__':
    unittest.main()
