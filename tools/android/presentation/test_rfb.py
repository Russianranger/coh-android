#!/usr/bin/env python3
"""Exercise the shipped Java RFB decoder with hostile and incremental wire fixtures."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / 'android/presentation/src/main/java/io/github/russianranger/cohpresentation/RfbClient.java'
HARNESS = r'''
import io.github.russianranger.cohpresentation.RfbClient;
import java.io.*;
import java.nio.file.*;
public final class RfbHarness {
    public static void main(String[] args) throws Exception {
        ByteArrayOutputStream output = new ByteArrayOutputStream() {
            @Override public void write(int value) { super.write(value); Thread.yield(); }
        };
        final boolean mutate = args.length > 2 && args[2].equals("mutate");
        final boolean refresh = args.length > 2 && args[2].equals("refresh");
        final RfbClient[] reference = new RfbClient[1];
        RfbClient client = new RfbClient(new ByteArrayInputStream(Files.readAllBytes(Paths.get(args[0]))),
                output, (pixels, w, h, seq) -> {
            StringBuilder line = new StringBuilder("FRAME " + seq + " " + w + " " + h);
            for (int pixel : pixels) line.append(String.format(" %08x", pixel));
            System.out.println(line);
            if (mutate) pixels[0] = 0;
            if (refresh) {
                Thread[] writers = new Thread[4];
                for (int i=0;i<writers.length;i++) {
                    writers[i] = new Thread(() -> {
                        for (int count=0;count<100;count++) try { reference[0].requestFullUpdate(); }
                        catch(IOException failure) { throw new IllegalStateException(failure); }
                    });
                    writers[i].start();
                }
                for (Thread writer : writers) try { writer.join(); }
                catch(InterruptedException failure) { throw new IllegalStateException(failure); }
            }
        });
        reference[0] = client;
        if (refresh) client.requestFullUpdate(); // Must not write into the unnegotiated handshake.
        try { client.run(); System.out.println("END closed"); }
        catch (IOException ex) { System.out.println("END " + ex.getClass().getSimpleName() + " " + ex.getMessage()); }
        Files.write(Paths.get(args[1]), output.toByteArray());
    }
}
'''


def init(width=2, height=2, minor=8, name=b'local fixture', name_length=None):
    security = struct.pack('>I', 1) if minor == 3 else b'\x01\x01' + (b'\0' * 4 if minor == 8 else b'')
    return f'RFB 003.{minor:03d}\n'.encode('ascii') + security + struct.pack('>HH', width, height) + bytes(16) + struct.pack('>I', len(name) if name_length is None else name_length) + name


def rect(x, y, w, h, colors=(), encoding=0):
    return struct.pack('>HHHHi', x, y, w, h, encoding) + b''.join(struct.pack('<I', pixel) for pixel in colors)


def update(*rectangles, count=None):
    return b'\0\0' + struct.pack('>H', len(rectangles) if count is None else count) + b''.join(rectangles)


class RfbDecoderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.java = shutil.which('java') or os.environ.get('ATLAS_JAVA')
        javac = shutil.which('javac') or os.environ.get('ATLAS_JAVAC')
        if not cls.java:
            raise unittest.SkipTest('JDK required to test the actual Java RFB decoder')
        cls.compiler = [javac] if javac else [cls.java, '-m', 'jdk.compiler/com.sun.tools.javac.Main']
        cls.compiled = tempfile.TemporaryDirectory(prefix='coh-rfb-java-')
        harness = Path(cls.compiled.name) / 'RfbHarness.java'
        harness.write_text(HARNESS)
        subprocess.run(cls.compiler + ['--release', '8', '-d', cls.compiled.name, str(CORE), str(harness)], check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'compiled'):
            cls.compiled.cleanup()

    def decode(self, stream, mutate=False, refresh=False):
        with tempfile.TemporaryDirectory(prefix='coh-rfb-fixture-') as tmp:
            fixture, response = Path(tmp) / 'wire', Path(tmp) / 'response'
            fixture.write_bytes(stream)
            command = [self.java, '-Xmx32m', '-cp', self.compiled.name, 'RfbHarness', str(fixture), str(response)]
            if mutate:
                command.append('mutate')
            elif refresh:
                command.append('refresh')
            run = subprocess.run(command, check=True, capture_output=True, text=True, timeout=10)
            lines = run.stdout.splitlines()
            frames = []
            for line in lines:
                if line.startswith('FRAME '):
                    fields = line.split()
                    frames.append((int(fields[1]), int(fields[2]), int(fields[3]), [int(x, 16) for x in fields[4:]]))
            return frames, lines[-1], response.read_bytes()

    def test_versions_and_exact_little_endian_raw_negotiation(self):
        for minor in (3, 7, 8):
            with self.subTest(minor=minor):
                frames, end, sent = self.decode(init(minor=minor) + update(rect(0, 0, 2, 2, [0xff0000, 0x00ff00, 0x0000ff, 0xffffff])))
                self.assertEqual([(1, 2, 2, [0xffff0000, 0xff00ff00, 0xff0000ff, 0xffffffff])], frames)
                self.assertIn('EOFException', end)
                prefix = f'RFB 003.{minor:03d}\n'.encode('ascii') + (b'' if minor == 3 else b'\1') + b'\1'
                pixel_format = b'\0' * 4 + struct.pack('>BBBBHHHBBB', 32, 24, 0, 1, 255, 255, 255, 16, 8, 0) + b'\0' * 3
                encodings = struct.pack('>BBHii', 2, 0, 2, 0, -223)
                first = struct.pack('>BBHHHH', 3, 0, 0, 0, 2, 2)
                following = struct.pack('>BBHHHH', 3, 1, 0, 0, 2, 2)
                self.assertEqual(prefix + pixel_format + encodings + first + following, sent)

    def test_explicit_full_refresh_requests_are_serialized_after_handshake(self):
        frames, end, sent = self.decode(init() + update(rect(0, 0, 2, 2, [1, 2, 3, 4])), refresh=True)
        self.assertEqual(1, len(frames))
        self.assertIn('EOFException', end)
        # 46 handshake bytes, mandatory full request, 400 concurrent explicit
        # refreshes, then the decoder's unchanged incremental follow-up.
        self.assertEqual(46 + 402 * 10, len(sent))
        full = struct.pack('>BBHHHH', 3, 0, 0, 0, 2, 2)
        self.assertEqual(full * 401, sent[46:-10])
        self.assertEqual(struct.pack('>BBHHHH', 3, 1, 0, 0, 2, 2), sent[-10:])

    def test_incremental_rectangles_preserve_unchanged_pixels_and_clone_delivery(self):
        stream = init() + update(rect(0, 0, 2, 2, [1, 2, 3, 4])) + update(rect(1, 0, 1, 2, [5, 6]))
        frames, _, _ = self.decode(stream, mutate=True)
        self.assertEqual([0xff000001, 0xff000002, 0xff000003, 0xff000004], frames[0][3])
        self.assertEqual([0xff000001, 0xff000005, 0xff000003, 0xff000006], frames[1][3])
        self.assertEqual(2, frames[1][0])

    def test_desktop_resize_requests_full_update_and_resets_storage(self):
        stream = init() + update(rect(0, 0, 2, 2, [1, 2, 3, 4])) + update(rect(0, 0, 1, 1, encoding=-223)) + update(rect(0, 0, 1, 1, [0xabcdef]))
        frames, _, sent = self.decode(stream)
        self.assertEqual((2, 1, 1, [0xffabcdef]), frames[-1])
        self.assertEqual(struct.pack('>BBHHHH', 3, 0, 0, 0, 1, 1), sent[-20:-10])

    def test_empty_update_bell_and_bounded_clipboard_do_not_emit_frames(self):
        text = b'x' * 4096
        stream = init() + b'\2' + b'\3\0\0\0' + struct.pack('>I', len(text)) + text + update()
        frames, end, sent = self.decode(stream)
        self.assertEqual([], frames)
        self.assertIn('EOFException', end)
        self.assertEqual(struct.pack('>BBHHHH', 3, 1, 0, 0, 2, 2), sent[-10:])

    def test_wrong_version_and_security_rejected(self):
        cases = [b'RFB 003.009\n', b'RFB 003.008\n\1\2', b'RFB 003.008\n\0', b'RFB 003.008\n\x21', b'RFB 003.008\n\1\1\0\0\0\1', b'RFB 003.003\n\0\0\0\2']
        for stream in cases:
            with self.subTest(stream=stream):
                frames, end, _ = self.decode(stream)
                self.assertEqual([], frames)
                self.assertIn('IOException', end)

    def test_initial_dimensions_and_name_lengths_bounded_before_allocation(self):
        for stream in [init(0, 1), init(1, 0), init(1025, 1), init(1, 769), init(65535, 65535), init(name=b'', name_length=4097), init(name=b'', name_length=0xffffffff)]:
            with self.subTest(stream=stream[:24]):
                frames, end, _ = self.decode(stream)
                self.assertEqual([], frames)
                self.assertIn('IOException', end)

    def test_outside_zero_and_overflow_rectangles_rejected(self):
        for coordinates in [(0, 0, 0, 1), (0, 0, 1, 0), (2, 0, 1, 1), (0, 2, 1, 1), (1, 1, 2, 1), (0, 0, 65535, 65535), (65535, 65535, 2, 2)]:
            with self.subTest(rect=coordinates):
                frames, end, _ = self.decode(init() + update(rect(*coordinates)))
                self.assertEqual([], frames)
                self.assertIn('outside framebuffer', end)

    def test_rectangle_count_unknown_encoding_and_server_message_rejected(self):
        for suffix in [update(count=1025), update(rect(0, 0, 1, 1, encoding=5)), b'\1', b'\xff']:
            frames, end, _ = self.decode(init() + suffix)
            self.assertEqual([], frames)
            self.assertIn('IOException', end)

    def test_oversized_and_unsigned_clipboard_lengths_rejected(self):
        for size in (4097, 0xffffffff):
            frames, end, _ = self.decode(init() + b'\3\0\0\0' + struct.pack('>I', size))
            self.assertEqual([], frames)
            self.assertIn('clipboard exceeds limit', end)

    def test_desktop_resize_bounds_and_position_rejected(self):
        cases = [rect(1, 0, 2, 2, encoding=-223), rect(0, 0, 0, 1, encoding=-223), rect(0, 0, 1025, 1, encoding=-223)]
        for invalid in cases:
            frames, end, _ = self.decode(init() + update(invalid))
            self.assertEqual([], frames)
            self.assertIn('IOException', end)
        frames, end, _ = self.decode(init() + update(rect(0, 0, 1, 1, encoding=-223), rect(0, 0, 1, 1, [0])))
        self.assertEqual([], frames)
        self.assertIn('Invalid RFB desktop-size rectangle', end)

    def test_truncation_never_publishes_partial_frame(self):
        handshake = init()
        suffix = update(rect(0, 0, 2, 2, [1, 2, 3, 4]))
        for length in (0, 11, 13, len(handshake) - 1, len(handshake) + 3, len(handshake) + 15, len(handshake) + len(suffix) - 1):
            with self.subTest(length=length):
                frames, end, _ = self.decode((handshake + suffix)[:length])
                self.assertEqual([], frames)
                self.assertIn('EOFException', end)


if __name__ == '__main__':
    unittest.main()
