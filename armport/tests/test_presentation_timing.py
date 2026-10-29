"""Presentation timing survives receiver teardown (Astra review 5673302120)."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
HOST = r'''package io.github.russianranger.cohclientinteractive;
import java.io.*;
public final class TimingHost {
    static void need(boolean v, String why) { if (!v) throw new AssertionError(why); }
    static byte[] wire(int w, int h) throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream(); DataOutputStream out = new DataOutputStream(bytes);
        out.writeBytes("RFB 003.008\n"); out.writeByte(1); out.writeByte(1); out.writeInt(0);
        out.writeShort(w); out.writeShort(h); out.write(new byte[16]); out.writeInt(0);
        for (int frame = 0; frame < 3; frame++) {
            out.writeByte(0); out.writeByte(0); out.writeShort(1);
            out.writeShort(0); out.writeShort(0); out.writeShort(w); out.writeShort(h); out.writeInt(0);
            for (int i = 0; i < w * h; i++) { out.writeByte(i); out.writeByte(frame); out.writeByte(7); out.writeByte(0); }
        }
        return bytes.toByteArray();
    }
    public static void main(String[] args) throws Exception {
        final int[] frames = {0};
        InteractiveRfbClient client = new InteractiveRfbClient(new ByteArrayInputStream(wire(320, 200)),
                new ByteArrayOutputStream(), (p, w, h, s) -> frames[0]++);
        try { client.run(); throw new AssertionError("wire must end with EOF"); } catch (EOFException expected) { }
        need(frames[0] == 3 && client.decodedRects() == 3, "three Raw rectangles decoded");
        need(client.readNanosSum() > 0 && client.convertNanosSum() > 0, "read and conversion are timed separately");
        need(client.readNanosMax() <= client.readNanosSum() && client.convertNanosMax() <= client.convertNanosSum(), "maxima bounded by sums");
        need(!client.totalsRetired() && client.retireTotals() && client.totalsRetired() && !client.retireTotals(),
             "totals retire exactly once");
        client.close();
        need(client.decodedRects() == 3, "totals readable after close");
        System.out.println("PASS");
    }
}
'''


RACE_HOST = r'''package io.github.russianranger.cohclientinteractive;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;
class LocalSocket { void close() throws IOException {} }
final class RuntimeHarness {
    volatile LocalSocket socket;
    volatile InteractiveRfbClient decoder;
%s
%s
}
public final class RaceHost {
    static void need(boolean v, String why) { if (!v) throw new AssertionError(why); }
    /** Pauses after copying the bytes that complete the final Raw rectangle.
     * Reads stop at the final rectangle's pixel start, so the decoder's bounded
     * chunks for it are direct reads into its own array (no read-ahead buffer):
     * the paused bytes have reached the decoder before closeReceiver() runs. */
    static final class Paused extends InputStream {
        final byte[] wire; final int chopAt, pauseAt; int position;
        final CountDownLatch reached = new CountDownLatch(1), release = new CountDownLatch(1);
        Paused(byte[] wire, int chopAt, int pauseAt) { this.wire = wire; this.chopAt = chopAt; this.pauseAt = pauseAt; }
        @Override public int read() { return position < wire.length ? wire[position++] & 255 : -1; }
        @Override public int read(byte[] b, int off, int len) {
            if (position >= wire.length) return -1;
            int n = Math.min(len, wire.length - position);
            if (position < chopAt && position + n > chopAt) n = chopAt - position;
            if (position < pauseAt && position + n > pauseAt) n = pauseAt - position;
            System.arraycopy(wire, position, b, off, n); position += n;
            if (position == pauseAt) {
                reached.countDown();
                try { release.await(10, TimeUnit.SECONDS); } catch (InterruptedException e) { throw new RuntimeException(e); }
            }
            return n;
        }
    }
    public static void main(String[] args) throws Exception {
        int w = 256, h = 256;
        ByteArrayOutputStream bytes = new ByteArrayOutputStream(); DataOutputStream out = new DataOutputStream(bytes);
        out.writeBytes("RFB 003.008\n"); out.writeByte(1); out.writeByte(1); out.writeInt(0);
        out.writeShort(w); out.writeShort(h); out.write(new byte[16]); out.writeInt(0);
        for (int frame = 0; frame < 3; frame++) {
            out.writeByte(0); out.writeByte(0); out.writeShort(1);
            out.writeShort(0); out.writeShort(0); out.writeShort(w); out.writeShort(h); out.writeInt(0);
            for (int i = 0; i < w * h; i++) { out.writeByte(i); out.writeByte(frame); out.writeByte(7); out.writeByte(0); }
        }
        byte[] wire = bytes.toByteArray();
        Paused input = new Paused(wire, wire.length - w * h * 4, wire.length);
        RuntimeHarness runtime = new RuntimeHarness();
        InteractiveRfbClient client = new InteractiveRfbClient(input, new ByteArrayOutputStream(), (p, fw, fh, seq) -> {});
        runtime.decoder = client;
        // Same receiver pattern as ClientRuntime.receiveFrames (checked from source).
        Thread receiver = new Thread(() -> {
            InteractiveRfbClient running = runtime.decoder;
            runtime.lastDecoder = running;
            try { running.run(); } catch (IOException expected) { } finally { runtime.retainDecoderTotals(running); }
        });
        receiver.start();
        need(input.reached.await(10, TimeUnit.SECONDS), "final rectangle bytes not reached");
        runtime.closeReceiver();
        Map<String,Object> interim = runtime.presentationTiming();
        need(Boolean.FALSE.equals(interim.get("rfb_totals_final")), "interim totals not marked partial");
        input.release.countDown();
        receiver.join(10000);
        need(!receiver.isAlive(), "receiver did not stop");
        Map<String,Object> last = runtime.presentationTiming();
        need(client.decodedRects() == 3, "decoder converted all rectangles");
        need(Long.valueOf(3).equals(last.get("rfb_decoded_rectangles")) && Boolean.TRUE.equals(last.get("rfb_totals_final")),
             "final export lost work: " + last);
        need(((Long) last.get("rfb_convert_ms_sum")) == client.convertNanosSum() / 1000000
             && ((Long) last.get("rfb_read_ms_max")) == client.readNanosMax() / 1000000, "final timings differ from the decoder");
        runtime.closeReceiver(); runtime.retainDecoderTotals(client); runtime.retainDecoderTotals(client);
        need(Long.valueOf(3).equals(runtime.presentationTiming().get("rfb_decoded_rectangles")), "repeated teardown double counted");
        System.out.println("PASS");
    }
}
'''


def runtime_methods():
    text = (JAVA / 'ClientRuntime.java').read_text()
    start = text.index('    // Delivered RFB frames per 5-second window')
    end = text.index('    private synchronized Map<String,Object> captureDiagnostics() {')
    close = re.search(r'    private void closeReceiver\(\) \{.*?\n    \}\n', text, re.S).group(0)
    # Only access changes: the harness calls the methods from another class.
    return text[start:end].replace('private ', ''), close.replace('private ', '')


class PresentationTiming(unittest.TestCase):
    def test_close_during_final_conversion_keeps_every_total(self):
        retention, close = runtime_methods()
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            (out / 'RaceHost.java').write_text(RACE_HOST % (retention, close))
            compiled = subprocess.run(['javac', '--release', '8', '-nowarn', '-d', str(out),
                str(JAVA / 'InteractiveRfbClient.java'), str(out / 'RaceHost.java')], capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr[-2500:])
            result = subprocess.run(['java', '-cp', str(out), 'io.github.russianranger.cohclientinteractive.RaceHost'],
                                    capture_output=True, text=True, timeout=60)
            self.assertEqual(result.stdout.strip(), 'PASS', result.stderr[-2000:])

    def test_decoder_totals_split_and_retire_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            host = out / 'TimingHost.java'
            host.write_text(HOST)
            subprocess.run(['javac', '--release', '8', '-nowarn', '-d', str(out),
                            str(JAVA / 'InteractiveRfbClient.java'), str(host)], check=True, capture_output=True)
            result = subprocess.run(['java', '-cp', str(out),
                'io.github.russianranger.cohclientinteractive.TimingHost'], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.stdout.strip(), 'PASS', result.stderr[-1500:])

    def test_runtime_retires_totals_only_from_the_stopped_receiver(self):
        text = (JAVA / 'ClientRuntime.java').read_text()
        close = re.search(r'private void closeReceiver\(\) \{(.*?)\n    \}', text, re.S).group(1)
        self.assertNotIn('retainDecoderTotals', close)
        self.assertIn('lastDecoder = running;\n                    try { running.run(); } finally { retainDecoderTotals(running); }', text)
        timing = re.search(r'presentationTiming\(\) \{(.*?)\n    \}', text, re.S).group(1)
        self.assertIn('retainedRects', timing)
        self.assertIn('current = lastDecoder', timing)
        self.assertIn('"rfb_totals_final"', timing)
        for key in ('rfb_read_ms_sum', 'rfb_convert_ms_sum', 'rfb_decoded_rectangles'):
            self.assertIn('"%s"' % key, timing)
        retain = re.search(r'void retainDecoderTotals\(InteractiveRfbClient retiring\) \{(.*?)\n    \}', text, re.S).group(1)
        self.assertIn('retiring.retireTotals()', retain)


if __name__ == '__main__':
    unittest.main()
