"""0.13.90: the app's own crash trace, run as shipped (the parts that need no Android class)."""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT/'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'


def method(text, signature):
    start = text.index(signature)
    cursor = text.index('{', start)
    depth, end = 1, cursor + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def harness():
    source = (JAVA/'ClientCrash.java').read_text()
    parts = [method(source, signature) for signature in (
        'static String record(String thread, Throwable failure, long utcMillis)',
        'private static void quote(StringBuilder out, String value, int limit)',
        'static void write(File target, String json)',
        'static String lastRecord(File filesDir)',
        'static String reasonName(int reason)')]
    return r'''
import java.io.*;
import java.nio.charset.StandardCharsets;
public class CrashHost {
 static final String FILE = "android-crash.json";
 static final int MAX_BYTES = 48 * 1024;
 static final int MAX_FRAMES = 48;
''' + '\n'.join(parts) + r'''
 static void deep(int n) { if (n == 0) throw new IllegalStateException("zone \"71\" asked for\né before the hero was in the world"); deep(n - 1); }
 public static void main(String[] a) throws Exception {
  File dir = new File(a[0]);
  if (lastRecord(dir) != null) throw new AssertionError("a record before any crash");
  Throwable failure;
  try { try { deep(200); } catch (RuntimeException inner) { throw new RuntimeException("event thread", inner); } failure = null; }
  catch (RuntimeException outer) { failure = outer; }
  String text = record("coh-client-output", failure, 1795806470000L);
  write(new File(dir, FILE), text);
  if (!text.equals(lastRecord(dir))) throw new AssertionError("the record was not read back");
  if (new File(dir, "." + FILE + ".part").exists()) throw new AssertionError("a part was left");
  // A second crash replaces the first; a record over the limit is refused and the earlier one stays.
  write(new File(dir, FILE), record(null, new OutOfMemoryError(), 5L));
  StringBuilder huge = new StringBuilder(); for (int i = 0; i < MAX_BYTES; i++) huge.append('x');
  try { write(new File(dir, FILE), "{\"x\":\"" + huge + "\"}"); throw new AssertionError("oversize accepted"); } catch (IOException expected) {}
  // A self-caused throwable ends the chain.
  Throwable loop = new Throwable("self") { @Override public synchronized Throwable getCause() { return this; } };
  System.out.println(text);
  System.out.println(lastRecord(dir));
  System.out.println(record("main", loop, 7L));
  System.out.println(reasonName(4) + " " + reasonName(5) + " " + reasonName(3) + " " + reasonName(2) + " " + reasonName(10) + " " + reasonName(99));
 }
}
'''


class ClientCrashJavaTests(unittest.TestCase):
    def test_a_crash_record_is_complete_bounded_and_read_back(self):
        with tempfile.TemporaryDirectory(prefix='coh-crash-java-') as build, tempfile.TemporaryDirectory() as files:
            host = Path(build)/'CrashHost.java'
            host.write_text(harness())
            subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8', '-d', build, str(host)],
                           check=True, capture_output=True, text=True)
            result = subprocess.run(['java', '-cp', build, 'CrashHost', files], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            first, second, loop, names = result.stdout.strip().split('\n')
            record = json.loads(first)
            self.assertEqual((record['format'], record['utc_ms'], record['thread']), (1, 1795806470000, 'coh-client-output'))
            outer, inner = record['chain']
            self.assertEqual((outer['exception'], outer['message']), ('java.lang.RuntimeException', 'event thread'))
            self.assertEqual(inner['exception'], 'java.lang.IllegalStateException')
            self.assertEqual(inner['message'], 'zone "71" asked for\né before the hero was in the world')
            self.assertEqual(len(inner['frames']), 48)                      # bounded; the total is kept
            self.assertGreater(inner['frames_total'], 200)
            self.assertTrue(inner['frames'][0].startswith('CrashHost.deep('))
            self.assertLess(len(first.encode()), 48 * 1024)
            later = json.loads(second)
            self.assertEqual((later['utc_ms'], later['thread'], later['chain'][0]['exception'], later['chain'][0]['message']),
                             (5, None, 'java.lang.OutOfMemoryError', None))
            self.assertEqual(len(json.loads(loop)['chain']), 1)
            self.assertEqual(names, 'CRASH CRASH_NATIVE LOW_MEMORY SIGNALED USER_REQUESTED UNKNOWN')

    def test_the_handler_keeps_androids_own_and_both_entry_points_install_it(self):
        crash = (JAVA/'ClientCrash.java').read_text()
        handler = method(crash, 'static synchronized void install(Context context)')
        self.assertIn('Thread.getDefaultUncaughtExceptionHandler()', handler)
        self.assertLess(handler.index('write(target, record('), handler.index('previous.uncaughtException(thread, failure)'))
        self.assertIn('catch (Throwable ignored)', handler)
        self.assertIn('ClientReports.setInterruptionEvidence(', handler)
        self.assertIn('ClientCrash.install(this);', (JAVA/'ClientService.java').read_text())
        self.assertIn('ClientCrash.install(this);', (JAVA/'ClientActivity.java').read_text())
        evidence = method(crash, 'static byte[] evidence(Context context)')
        for text in ('"last_crash"', '"exit_history"', 'Build.VERSION.SDK_INT < 30', '"is_success_proof", false'):
            self.assertIn(text, evidence)
        self.assertIn('.put("description"', crash)
        self.assertIn('.put("reason_name", reasonName(info.getReason()))', crash)

    def test_the_operation_log_is_written_as_it_grows(self):
        runtime = (JAVA/'ClientRuntime.java').read_text()
        line = method(runtime, 'private synchronized void line(String text)')
        self.assertIn('liveLogLine(text);', line)
        write = method(runtime, 'private synchronized void liveLogLine(String text)')
        self.assertIn('liveLog.flush();', write)
        self.assertIn('catch (Exception | OutOfMemoryError unavailable) { closeLiveLog(); }', write)
        opened = method(runtime, 'private synchronized void openLiveLog(boolean dropped)')
        self.assertIn('new File(directory, "operation.log")', opened)
        self.assertIn('LIVE_LOG_LIMIT = 1200L * 1024;', runtime)            # characters; under 4 MiB as UTF-8
        self.assertIn('openLiveLog(false);', runtime)
        self.assertIn('closeLiveLog(); }', method(runtime, 'private void endOperation()'))
        recovery = (ROOT/'android/recovery/src/main/java/io/github/russianranger/cohclientinteractive/ClientReports.java').read_text()
        self.assertIn('terminalSource(sources, omitted, "operation.log", run.resolve("operation.log"), 4L * 1024 * 1024);', recovery)


if __name__ == '__main__':
    unittest.main()
