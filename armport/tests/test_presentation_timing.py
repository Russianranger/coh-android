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


class PresentationTiming(unittest.TestCase):
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

    def test_runtime_retains_totals_before_dropping_the_decoder(self):
        text = (JAVA / 'ClientRuntime.java').read_text()
        close = re.search(r'private void closeReceiver\(\) \{(.*?)\n    \}', text, re.S).group(1)
        self.assertLess(close.index('retainDecoderTotals(activeDecoder);'), close.index('decoder = null;'))
        self.assertIn('try { running.run(); } finally { retainDecoderTotals(running); }', text)
        timing = re.search(r'presentationTiming\(\) \{(.*?)\n    \}', text, re.S).group(1)
        self.assertIn('retainedRects', timing)
        self.assertIn('!current.totalsRetired()', timing)
        for key in ('rfb_read_ms_sum', 'rfb_convert_ms_sum', 'rfb_decoded_rectangles'):
            self.assertIn('"%s"' % key, timing)
        retain = re.search(r'void retainDecoderTotals\(InteractiveRfbClient retiring\) \{(.*?)\n    \}', text, re.S).group(1)
        self.assertIn('retiring.retireTotals()', retain)


if __name__ == '__main__':
    unittest.main()
