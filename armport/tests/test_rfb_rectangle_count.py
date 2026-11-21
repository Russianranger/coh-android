"""One display update may hold any number of rectangles the protocol can count (Thor 0.13.63).

Export 20261109-154935: fast camera turns in Mercy Island ended the session with
"Local display connection failed: RFB rectangle count exceeds limit". TigerVNC
counts its whole changed region into one FramebufferUpdate (this client
advertises no LastRect) and the decoder accepted at most 1024 rectangles.
"""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
HOST = r'''package io.github.russianranger.cohclientinteractive;
import java.io.*;
public final class RectHost {
    static void need(boolean v, String why) { if (!v) throw new AssertionError(why); }
    static DataOutputStream start(ByteArrayOutputStream bytes, int w, int h) throws IOException {
        DataOutputStream out = new DataOutputStream(bytes);
        out.writeBytes("RFB 003.008\n"); out.writeByte(1); out.writeByte(1); out.writeInt(0);
        out.writeShort(w); out.writeShort(h); out.write(new byte[16]); out.writeInt(0);
        return out;
    }
    /** One update of count 1x1 Raw rectangles in row order; pixel i is B=i, G=i>>8, R=7. */
    static void update(DataOutputStream out, int w, int count) throws IOException {
        out.writeByte(0); out.writeByte(0); out.writeShort(count);
        for (int i = 0; i < count; i++) {
            out.writeShort(i % w); out.writeShort(i / w); out.writeShort(1); out.writeShort(1); out.writeInt(0);
            out.writeByte(i); out.writeByte(i >> 8); out.writeByte(7); out.writeByte(0);
        }
    }
    static int expected(int i) { return 0xff000000 | (7 << 16) | (((i >> 8) & 255) << 8) | (i & 255); }
    static int[] decode(byte[] wire, long rects) throws Exception {
        final int[][] last = {null}; final int[] frames = {0};
        InteractiveRfbClient client = new InteractiveRfbClient(new ByteArrayInputStream(wire), new ByteArrayOutputStream(),
                (p, w, h, s) -> { last[0] = p; frames[0]++; });
        try { client.run(); throw new AssertionError("wire must end with EOF"); } catch (EOFException expected) { }
        need(frames[0] == 1 && client.decodedRects() == rects,
             "one frame of " + rects + " rectangles, decoded " + client.decodedRects());
        need(client.updateRectsMax() == rects, "largest update " + client.updateRectsMax());
        return last[0];
    }
    public static void main(String[] args) throws Exception {
        need(InteractiveRfbClient.MAX_RECTS == 0xFFFF, "the protocol's whole U16 count");
        // Above the old 1024 limit: 4096 rectangles cover a 64x64 desktop.
        ByteArrayOutputStream a = new ByteArrayOutputStream(); update(start(a, 64, 64), 64, 4096);
        int[] frame = decode(a.toByteArray(), 4096);
        for (int i = 0; i < 4096; i++) need(frame[i] == expected(i), "pixel " + i);
        // The largest count: 65535 rectangles of a 256x256 desktop; its last pixel stays black.
        ByteArrayOutputStream b = new ByteArrayOutputStream(); update(start(b, 256, 256), 256, 65535);
        frame = decode(b.toByteArray(), 65535);
        need(frame[65534] == expected(65534) && frame[65535] == 0xff000000, "the last rectangles");
        // Every rectangle is still bounded by the framebuffer.
        ByteArrayOutputStream c = new ByteArrayOutputStream(); DataOutputStream out = start(c, 64, 64);
        out.writeByte(0); out.writeByte(0); out.writeShort(2000);
        out.writeShort(63); out.writeShort(0); out.writeShort(2); out.writeShort(1); out.writeInt(0);
        try {
            new InteractiveRfbClient(new ByteArrayInputStream(c.toByteArray()), new ByteArrayOutputStream(),
                    (p, w, h, s) -> { }).run();
            throw new AssertionError("a rectangle outside the framebuffer was accepted");
        } catch (EOFException unexpected) {
            throw new AssertionError("a rectangle outside the framebuffer was read");
        } catch (IOException expected) {
            need("RFB rectangle outside framebuffer".equals(expected.getMessage()), expected.getMessage());
        }
        System.out.println("PASS");
    }
}
'''


class RectangleCount(unittest.TestCase):
    def test_updates_above_1024_rectangles_decode(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            host = out / 'RectHost.java'
            host.write_text(HOST)
            compiled = subprocess.run(['javac', '--release', '8', '-nowarn', '-d', str(out),
                                       str(JAVA / 'InteractiveRfbClient.java'), str(host)],
                                      capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            result = subprocess.run(['java', '-cp', str(out), 'io.github.russianranger.cohclientinteractive.RectHost'],
                                    capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout.strip(), 'PASS')

    def test_report_keeps_the_largest_update(self):
        text = (JAVA / 'ClientRuntime.java').read_text()
        retain = re.search(r'void retainDecoderTotals\(InteractiveRfbClient retiring\) \{(.*?)\n    \}', text, re.S).group(1)
        self.assertIn('retainedUpdateRectsMax = Math.max(retainedUpdateRectsMax, retiring.updateRectsMax());', retain)
        timing = re.search(r'Map<String,Object> presentationTiming\(\) \{(.*?)\n    \}', text, re.S).group(1)
        self.assertIn('updateRectsMax = Math.max(updateRectsMax, current.updateRectsMax());', timing)
        self.assertIn('result.put("rfb_update_rectangles_max", updateRectsMax);', timing)


if __name__ == '__main__':
    unittest.main()
