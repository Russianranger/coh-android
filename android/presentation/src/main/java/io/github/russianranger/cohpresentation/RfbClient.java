package io.github.russianranger.cohpresentation;

import java.io.Closeable;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;

/** A bounded local-socket RFB client. It deliberately negotiates raw true-colour only. */
public final class RfbClient implements Closeable {
    public interface Listener {
        /** The array is a private snapshot and will never be modified by the decoder. */
        void onFrame(int[] argb, int width, int height, long sequence);
    }

    public static final int MAX_WIDTH = 1024;
    public static final int MAX_HEIGHT = 768;
    private static final int MAX_RECTS = 1024;
    private static final int MAX_TEXT = 4096;
    private static final int DESKTOP_SIZE = -223;
    private final DataInputStream input;
    private final DataOutputStream output;
    private final Listener listener;
    private volatile boolean closed;
    private int width;
    private int height;
    private int[] pixels;
    private long sequence;

    public RfbClient(InputStream input, OutputStream output, Listener listener) {
        if (input == null || output == null || listener == null) throw new NullPointerException();
        this.input = new DataInputStream(input);
        this.output = new DataOutputStream(output);
        this.listener = listener;
    }

    /** Blocking until cancellation, EOF, or protocol failure. Close the owning socket to cancel. */
    public void run() throws IOException {
        if (pixels != null) throw new IOException("RFB client cannot be reused");
        handshake();
        requestUpdate(false);
        while (!closed) {
            int message = input.readUnsignedByte();
            switch (message) {
                case 0: readFramebufferUpdate(); break;
                case 2: break; // Bell; never make a sound in this diagnostic.
                case 3:
                    skipExactly(3);
                    skipExactly(boundedLength(input.readInt(), MAX_TEXT, "clipboard"));
                    break;
                default: throw new IOException("Unsupported RFB server message: " + message);
            }
        }
    }

    private void handshake() throws IOException {
        byte[] version = new byte[12];
        input.readFully(version);
        String banner = new String(version, StandardCharsets.US_ASCII);
        int minor;
        if ("RFB 003.008\n".equals(banner)) minor = 8;
        else if ("RFB 003.007\n".equals(banner)) minor = 7;
        else if ("RFB 003.003\n".equals(banner)) minor = 3;
        else throw new IOException("Unsupported RFB version");
        output.write(version);
        output.flush();

        if (minor == 3) {
            if (input.readInt() != 1) throw new IOException("RFB local socket requires None security");
        } else {
            int count = input.readUnsignedByte();
            if (count == 0 || count > 32) throw new IOException("Invalid RFB security-type count");
            boolean none = false;
            for (int i = 0; i < count; i++) none |= input.readUnsignedByte() == 1;
            if (!none) throw new IOException("RFB local socket requires None security");
            output.writeByte(1);
            output.flush();
            // RFB 3.7 None omits SecurityResult; RFB 3.8 always sends it.
            if (minor == 8 && input.readInt() != 0) throw new IOException("RFB security rejected");
        }
        output.writeByte(1); // Shared desktop; connection is already restricted to a local socket.
        output.flush();

        resize(input.readUnsignedShort(), input.readUnsignedShort());
        skipExactly(16); // Server pixel format is superseded below before requesting any pixels.
        skipExactly(boundedLength(input.readInt(), MAX_TEXT, "desktop name"));

        output.writeByte(0); // SetPixelFormat
        output.write(new byte[3]);
        output.writeByte(32);
        output.writeByte(24);
        output.writeByte(0); // little endian
        output.writeByte(1); // true colour
        output.writeShort(255);
        output.writeShort(255);
        output.writeShort(255);
        output.writeByte(16);
        output.writeByte(8);
        output.writeByte(0);
        output.write(new byte[3]);
        output.writeByte(2); // SetEncodings
        output.writeByte(0);
        output.writeShort(2);
        output.writeInt(0); // Raw
        output.writeInt(DESKTOP_SIZE);
        output.flush();
    }

    private static int boundedLength(int length, int limit, String label) throws IOException {
        if (length < 0 || length > limit) throw new IOException("RFB " + label + " exceeds limit");
        return length;
    }

    private void resize(int nextWidth, int nextHeight) throws IOException {
        if (nextWidth < 1 || nextHeight < 1 || nextWidth > MAX_WIDTH || nextHeight > MAX_HEIGHT)
            throw new IOException("RFB framebuffer size exceeds bounds: " + nextWidth + "x" + nextHeight);
        width = nextWidth;
        height = nextHeight;
        pixels = new int[width * height];
        java.util.Arrays.fill(pixels, 0xff000000);
    }

    private void readFramebufferUpdate() throws IOException {
        input.readUnsignedByte();
        int count = input.readUnsignedShort();
        if (count > MAX_RECTS) throw new IOException("RFB rectangle count exceeds limit");
        boolean changed = false;
        boolean resized = false;
        for (int i = 0; i < count; i++) {
            int x = input.readUnsignedShort();
            int y = input.readUnsignedShort();
            int w = input.readUnsignedShort();
            int h = input.readUnsignedShort();
            int encoding = input.readInt();
            if (encoding == DESKTOP_SIZE) {
                if (x != 0 || y != 0 || i != count - 1)
                    throw new IOException("Invalid RFB desktop-size rectangle");
                resize(w, h);
                changed = false; // The preceding old-size pixels are no longer a complete image.
                resized = true;
            } else if (encoding == 0) {
                if (w == 0 || h == 0 || x > width || y > height || w > width - x || h > height - y)
                    throw new IOException("RFB rectangle outside framebuffer");
                byte[] row = new byte[w * 4];
                for (int yy = 0; yy < h; yy++) {
                    input.readFully(row);
                    int offset = (y + yy) * width + x;
                    for (int xx = 0; xx < w; xx++) {
                        int source = xx * 4;
                        pixels[offset + xx] = 0xff000000 | ((row[source + 2] & 255) << 16)
                                | ((row[source + 1] & 255) << 8) | (row[source] & 255);
                    }
                }
                changed = true;
            } else throw new IOException("Unsupported RFB encoding: " + encoding);
        }
        if (changed) listener.onFrame(pixels.clone(), width, height, ++sequence);
        requestUpdate(!resized);
    }

    private void requestUpdate(boolean incremental) throws IOException {
        if (closed) return;
        output.writeByte(3);
        output.writeByte(incremental ? 1 : 0);
        output.writeShort(0);
        output.writeShort(0);
        output.writeShort(width);
        output.writeShort(height);
        output.flush();
    }

    private void skipExactly(int count) throws IOException {
        byte[] scratch = new byte[Math.min(4096, count)];
        while (count > 0) {
            int amount = Math.min(scratch.length, count);
            input.readFully(scratch, 0, amount);
            count -= amount;
        }
    }

    @Override public void close() throws IOException {
        closed = true;
        IOException failure = null;
        try { input.close(); } catch (IOException ex) { failure = ex; }
        try { output.close(); } catch (IOException ex) { if (failure == null) failure = ex; }
        if (failure != null) throw failure;
    }
}
