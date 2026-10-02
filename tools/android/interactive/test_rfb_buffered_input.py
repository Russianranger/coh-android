"""Bounded raw-RFB read buffering: identical frames, fewer reads, no native boot."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/InteractiveRfbClient.java'
PACKAGE = 'io.github.russianranger.cohclientinteractive'
BUFFERED = 'new DataInputStream(new BufferedInputStream(input, 64 * 1024))'
HARNESS = r'''
package io.github.russianranger.cohclientinteractive;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;

public final class BufferedRfbHost {
    static void require(boolean ok, String detail) {
        if (!ok) throw new AssertionError(detail);
    }
    static final class Counted extends ByteArrayInputStream {
        long calls, bytes; int largest; final int fragment;
        Counted(byte[] data, int fragment) { super(data); this.fragment = fragment; }
        @Override public synchronized int read() {
            calls++; largest = Math.max(largest, 1);
            int value = super.read(); if (value >= 0) bytes++;
            return value;
        }
        @Override public synchronized int read(byte[] target, int offset, int amount) {
            calls++; largest = Math.max(largest, amount);
            int size = super.read(target, offset, Math.min(amount, fragment));
            if (size > 0) bytes += size;
            return size;
        }
    }
    static byte[] wire(int width, int height, int fault) throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        DataOutputStream out = new DataOutputStream(bytes);
        out.writeBytes("RFB 003.008\n"); out.writeByte(1); out.writeByte(1); out.writeInt(0);
        out.writeShort(width); out.writeShort(height); out.write(new byte[16]); out.writeInt(0);
        if (fault == 1) return bytes.toByteArray();
        out.writeByte(0); out.writeByte(0); out.writeShort(1);
        out.writeShort(fault == 2 ? width - 1 : 0); out.writeShort(0);
        out.writeShort(width); out.writeShort(height); out.writeInt(fault == 3 ? 42 : 0);
        if (fault == 2 || fault == 3) return bytes.toByteArray();
        for (int y = 0; y < height; y++) for (int x = 0; x < width; x++) {
            out.writeByte(x & 255); out.writeByte(y & 255); out.writeByte((x + y) & 255); out.writeByte(0);
        }
        out.writeByte(2); // Bell does not produce a frame.
        out.writeByte(3); out.write(new byte[3]); out.writeInt(fault == 4 ? 4097 : 2);
        if (fault == 4) return bytes.toByteArray();
        out.writeBytes("ok");
        out.writeByte(0); out.writeByte(0); out.writeShort(1);
        out.writeShort(1); out.writeShort(1); out.writeShort(1); out.writeShort(1); out.writeInt(0);
        out.write(new byte[]{3, 2, 1, 0});
        return bytes.toByteArray();
    }
    static final class Run {
        final Counted input; final List<int[]> frames = new ArrayList<>();
        final List<Long> sequences = new ArrayList<>(); final ByteArrayOutputStream output = new ByteArrayOutputStream();
        Run(boolean buffered, byte[] wire, int fragment) throws IOException {
            input = new Counted(wire, fragment);
            if (buffered) {
                InteractiveRfbClient client = new InteractiveRfbClient(input, output, (pixels,w,h,s) -> {
                    frames.add(pixels); sequences.add(s);
                });
                try { client.run(); throw new AssertionError("wire must end with EOF"); }
                catch (EOFException expected) { }
                finally { client.close(); }
            } else {
                BaselineRfbClient client = new BaselineRfbClient(input, output, (pixels,w,h,s) -> {
                    frames.add(pixels); sequences.add(s);
                });
                try { client.run(); throw new AssertionError("wire must end with EOF"); }
                catch (EOFException expected) { }
                finally { client.close(); }
            }
        }
    }
    static void equivalence(int width, int height, int fragment, boolean measure) throws Exception {
        byte[] wire = wire(width, height, 0);
        Run old = new Run(false, wire, fragment), current = new Run(true, wire, fragment);
        require(old.frames.size() == 2 && current.frames.size() == 2, "complete and incremental frames");
        require(old.sequences.equals(Arrays.asList(1L,2L)) && old.sequences.equals(current.sequences), "unchanged sequence/freshness");
        for (int n = 0; n < 2; n++) require(Arrays.equals(old.frames.get(n), current.frames.get(n)), "all frame pixels remain identical");
        require(current.frames.get(0) != current.frames.get(1), "private immutable snapshots remain separate");
        require(current.frames.get(0)[width + 1] == 0xff020101 && current.frames.get(1)[width + 1] == 0xff010203,
                "incremental update cannot mutate earlier snapshot");
        require(Arrays.equals(old.output.toByteArray(), current.output.toByteArray()), "handshake/update requests unchanged");
        require(old.input.bytes == wire.length && current.input.bytes == wire.length, "complete exact wire consumed");
        require(current.input.largest <= 65536, "input read-ahead stays at bounded64KiB");
        if (measure) {
            require(old.input.calls >= 600, "unbuffered rows establish original read cost");
            require(current.input.calls <= 40 && current.input.calls * 10 < old.input.calls, "at least10x fewer underlying reads for complete800x600 wire");
            System.out.println("buffered_reads="+current.input.calls+" unbuffered_reads="+old.input.calls+" wire_bytes="+wire.length);
        }
    }
    static void hostile(int fault) throws Exception {
        Counted input = new Counted(wire(fault == 1 ? 1025 : 2, 2, fault), Integer.MAX_VALUE);
        InteractiveRfbClient client = new InteractiveRfbClient(input, new ByteArrayOutputStream(), (p,w,h,s) -> {});
        try { client.run(); throw new AssertionError("hostile bounds must reject"); }
        catch (IOException expected) {
            String message = expected.getMessage();
            require(message != null && (message.contains("size exceeds") || message.contains("outside framebuffer")
                    || message.contains("Unsupported RFB encoding") || message.contains("clipboard exceeds")), "original hostile rejection reason");
        } finally { client.close(); }
        require(input.largest <= 65536, "hostile wire cannot expand read-ahead");
    }
    static void truncated() throws Exception {
        byte[] wire = wire(2, 2, 0);
        Counted input = new Counted(Arrays.copyOf(wire, 55), 3);
        List<int[]> frames = new ArrayList<>();
        InteractiveRfbClient client = new InteractiveRfbClient(input, new ByteArrayOutputStream(), (p,w,h,s) -> frames.add(p));
        try { client.run(); throw new AssertionError("truncated rectangle must fail"); }
        catch (EOFException expected) { require(frames.isEmpty(), "partial pixels cannot establish a fresh frame"); }
        finally { client.close(); }
    }
    static final class Blocked extends InputStream {
        final CountDownLatch entered = new CountDownLatch(1); boolean closed;
        @Override public synchronized int read() throws IOException {
            entered.countDown();
            while (!closed) try { wait(); } catch (InterruptedException e) { throw new IOException(e); }
            throw new IOException("closed");
        }
        @Override public synchronized int read(byte[] target, int offset, int amount) throws IOException { return read(); }
        @Override public synchronized void close() { closed = true; notifyAll(); }
    }
    static void closeBlocked() throws Exception {
        Blocked source = new Blocked(); List<Throwable> errors = new ArrayList<>();
        InteractiveRfbClient client = new InteractiveRfbClient(source, new ByteArrayOutputStream(), (p,w,h,s) -> {});
        Thread worker = new Thread(() -> { try { client.run(); } catch (IOException expected) { } catch (Throwable e) { errors.add(e); } });
        worker.setDaemon(true); worker.start();
        require(source.entered.await(2, TimeUnit.SECONDS), "decoder reached blocked underlying read");
        client.close(); worker.join(2000);
        require(!worker.isAlive() && errors.isEmpty() && source.closed, "close promptly interrupts buffered blocked read");
    }
    public static void main(String[] args) throws Exception {
        if (args[0].equals("full")) equivalence(800,600,Integer.MAX_VALUE,true);
        else if (args[0].equals("fragment")) equivalence(17,11,Integer.parseInt(args[1]),false);
        else if (args[0].equals("hostile")) hostile(Integer.parseInt(args[1]));
        else if (args[0].equals("truncated")) truncated();
        else if (args[0].equals("close")) closeBlocked();
        else throw new AssertionError("unknown test");
        System.out.println("PASS");
    }
}
'''


class RfbBufferedInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-rfb-buffered-host-')
        cls.output = Path(cls.temporary.name)
        source = SOURCE.read_text()
        if source.count(BUFFERED) != 1:
            raise AssertionError('Exact bounded input-only buffering source is required')
        # The baseline executes the identical shipped decoder with only its
        # constructor wrapper reverted. It is generated only in a temporary
        # host directory; no game/runtime package is created or executed.
        baseline = source.replace(BUFFERED, 'new DataInputStream(input)').replace('InteractiveRfbClient', 'BaselineRfbClient')
        (cls.output/'BaselineRfbClient.java').write_text(baseline)
        (cls.output/'BufferedRfbHost.java').write_text(HARNESS)
        subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','--release','8','-d',str(cls.output),str(SOURCE),str(cls.output/'BaselineRfbClient.java'),str(cls.output/'BufferedRfbHost.java')],check=True,capture_output=True,text=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def run_case(self, *args):
        result = subprocess.run(['java','-cp',str(self.output),PACKAGE+'.BufferedRfbHost',*args],check=True,capture_output=True,text=True,timeout=15)
        self.assertIn('PASS',result.stdout)
        return result.stdout

    def test_full_frame_and_incremental_pixels_requests_are_identical_with_fewer_reads(self):
        result = self.run_case('full')
        self.assertIn('wire_bytes=1920089',result)

    def test_fragmented_delivery_preserves_pixels_snapshots_and_protocol(self):
        for fragment in (1,3,31,1024):
            with self.subTest(fragment=fragment):
                self.run_case('fragment',str(fragment))

    def test_oversized_frame_rectangle_encoding_and_clipboard_bounds_remain_fail_closed(self):
        for fault in (1,2,3,4):
            with self.subTest(fault=fault):
                self.run_case('hostile',str(fault))

    def test_truncated_pixel_rectangle_cannot_publish_a_partial_frame(self):
        self.run_case('truncated')

    def test_close_interrupts_a_blocked_buffered_input_without_losing_ownership(self):
        self.run_case('close')


if __name__ == '__main__':
    unittest.main()
