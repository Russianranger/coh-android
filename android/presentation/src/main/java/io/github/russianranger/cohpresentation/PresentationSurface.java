package io.github.russianranger.cohpresentation;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.PixelCopy;
import android.view.SurfaceHolder;
import android.view.SurfaceView;

/** Presents decoded frames and independently verifies the pixels in the Android Surface. */
public final class PresentationSurface extends SurfaceView implements SurfaceHolder.Callback {
    public interface CertificationListener {
        void onFrameCertified(Certification sample);
        void onCertificationError(String detail);
    }

    public static final class Certification {
        public final String session;
        public final int frameId;
        public final long sequence;
        public final int width, height, surfaceWidth, surfaceHeight;
        public final long capturedAtUptimeMillis;
        public final int surfaceGeneration;
        public final String[] barsHex;
        public final boolean pixelCopy = true;

        private Certification(String session, int frameId, long sequence, int width, int height,
                int surfaceWidth, int surfaceHeight, int generation, String[] barsHex) {
            this.session = session;
            this.frameId = frameId;
            this.sequence = sequence;
            this.width = width;
            this.height = height;
            this.surfaceWidth = surfaceWidth;
            this.surfaceHeight = surfaceHeight;
            this.surfaceGeneration = generation;
            this.barsHex = barsHex;
            capturedAtUptimeMillis = SystemClock.uptimeMillis();
        }
    }

    private static final int FRAME_WIDTH = 800;
    private static final int FRAME_HEIGHT = 600;
    private static final int TOLERANCE = 3;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final Paint paint = new Paint();
    private final Object pendingLock = new Object();
    private Frame pending;
    private boolean renderPosted;
    private boolean capturePending;
    private boolean ready;
    private volatile String expectedSession;
    private volatile CertificationListener certificationListener;
    private volatile int certifiedCount;
    private volatile int lastCertifiedFrame;
    private volatile int surfaceGeneration;
    private Bitmap displayed;
    private int sessionGeneration;
    private final boolean[] seen = new boolean[241];

    private static final class Frame {
        final int[] pixels;
        final int width, height;
        final long sequence;
        Frame(int[] pixels, int width, int height, long sequence) {
            this.pixels = pixels;
            this.width = width;
            this.height = height;
            this.sequence = sequence;
        }
    }

    public PresentationSurface(Context context) {
        super(context);
        paint.setFilterBitmap(false);
        paint.setDither(false);
        getHolder().addCallback(this);
        setWillNotDraw(true);
    }

    public void setExpectedSession(String session) {
        if (session == null || !session.matches("[0-9a-f]{32}"))
            throw new IllegalArgumentException("Expected a 32-character lowercase hexadecimal session");
        main.post(() -> {
            expectedSession = session;
            sessionGeneration++;
            certifiedCount = 0;
            lastCertifiedFrame = 0;
            java.util.Arrays.fill(seen, false);
            scheduleRender();
        });
    }

    public void setCertificationListener(CertificationListener listener) {
        certificationListener = listener;
    }

    public int getCertifiedCount() { return certifiedCount; }
    public int getLastCertifiedFrame() { return lastCertifiedFrame; }
    public int getSurfaceGeneration() { return surfaceGeneration; }

    /** Safe from the decoder thread. Frames coalesce while a Surface capture is pending. */
    public void setFrame(int[] argb, int width, int height, long sequence) {
        if (argb == null || width < 1 || height < 1 || width > RfbClient.MAX_WIDTH
                || height > RfbClient.MAX_HEIGHT || argb.length != width * height)
            throw new IllegalArgumentException("Invalid presentation frame");
        synchronized (pendingLock) {
            pending = new Frame(argb, width, height, sequence);
        }
        scheduleRender();
    }

    private void scheduleRender() {
        synchronized (pendingLock) {
            if (renderPosted) return;
            renderPosted = true;
        }
        main.post(this::renderLatest);
    }

    private void renderLatest() {
        Frame frame;
        synchronized (pendingLock) {
            renderPosted = false;
            if (!ready || capturePending || pending == null) return;
            frame = pending;
            pending = null;
        }
        int generation = surfaceGeneration;
        int currentSession = sessionGeneration;
        Canvas canvas = null;
        RectF destination = null;
        int surfaceWidth = 0, surfaceHeight = 0;
        try {
            if (displayed == null || displayed.getWidth() != frame.width || displayed.getHeight() != frame.height) {
                if (displayed != null) displayed.recycle();
                displayed = Bitmap.createBitmap(frame.width, frame.height, Bitmap.Config.ARGB_8888);
            }
            displayed.setPixels(frame.pixels, 0, frame.width, 0, 0, frame.width, frame.height);
            canvas = getHolder().lockCanvas();
            if (canvas == null) throw new IllegalStateException("Surface canvas unavailable");
            surfaceWidth = canvas.getWidth();
            surfaceHeight = canvas.getHeight();
            if (surfaceWidth < 1 || surfaceHeight < 1) throw new IllegalStateException("Empty Surface");
            float scale = Math.min(surfaceWidth / (float) frame.width, surfaceHeight / (float) frame.height);
            float left = (surfaceWidth - frame.width * scale) * 0.5f;
            float top = (surfaceHeight - frame.height * scale) * 0.5f;
            destination = new RectF(left, top, left + frame.width * scale, top + frame.height * scale);
            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(displayed, null, destination, paint);
        } catch (RuntimeException ex) {
            reportError("Surface render: " + ex.getClass().getSimpleName());
            destination = null;
        } finally {
            if (canvas != null) {
                try { getHolder().unlockCanvasAndPost(canvas); }
                catch (RuntimeException ex) {
                    destination = null;
                    reportError("Surface post: " + ex.getClass().getSimpleName());
                }
            }
        }
        if (destination == null || expectedSession == null) return;
        if (frame.width != FRAME_WIDTH || frame.height != FRAME_HEIGHT) {
            reportError("Unexpected probe frame size " + frame.width + "x" + frame.height);
            return;
        }

        final int captureWidth = surfaceWidth;
        final int captureHeight = surfaceHeight;
        final RectF content = destination;
        // PixelCopy scales the actual full Surface into this bounded bitmap, including letterboxing.
        // No decoded pixel or Canvas readback is used as evidence of Android presentation.
        final Bitmap captured = Bitmap.createBitmap(FRAME_WIDTH, FRAME_HEIGHT, Bitmap.Config.ARGB_8888);
        final String session = expectedSession;
        capturePending = true;
        try {
            PixelCopy.request(this, captured, result -> {
                capturePending = false;
                try {
                    if (!ready || generation != surfaceGeneration || currentSession != sessionGeneration) return;
                    if (result != PixelCopy.SUCCESS) {
                        reportError("PixelCopy result " + result);
                        return;
                    }
                    certify(captured, content, captureWidth, captureHeight, frame, session, generation);
                } catch (IllegalArgumentException ex) {
                    reportError("PixelCopy verification: " + ex.getMessage());
                } finally {
                    captured.recycle();
                    scheduleRender();
                }
            }, main);
        } catch (RuntimeException ex) {
            capturePending = false;
            captured.recycle();
            reportError("PixelCopy request: " + ex.getClass().getSimpleName());
            scheduleRender();
        }
    }

    private void certify(Bitmap captured, RectF content, int sw, int sh, Frame frame,
            String expected, int generation) {
        StringBuilder actualSession = new StringBuilder(32);
        for (int nibble = 0; nibble < 32; nibble++) {
            int value = 0;
            for (int bit = 0; bit < 4; bit++)
                value = (value << 1) | binary(sample(captured, content, sw, sh, 6 * (nibble * 4 + bit) + 3, 12));
            actualSession.append(Character.forDigit(value, 16));
        }
        if (!expected.contentEquals(actualSession)) throw new IllegalArgumentException("session mismatch");
        int frameId = 0;
        for (int bit = 0; bit < 16; bit++) {
            int value = binary(sample(captured, content, sw, sh, 24 * bit + 12, 44));
            int complement = binary(sample(captured, content, sw, sh, 24 * bit + 396, 44));
            if (value == complement) throw new IllegalArgumentException("frame complement mismatch");
            frameId = (frameId << 1) | value;
        }
        if (frameId < 1 || frameId > 240) throw new IllegalArgumentException("frame outside probe bounds");
        int[] colors = frameId % 2 == 0
                ? new int[]{Color.RED, Color.GREEN, Color.BLUE, Color.WHITE}
                : new int[]{Color.WHITE, Color.BLUE, Color.GREEN, Color.RED};
        String[] actualColors = new String[4];
        for (int bar = 0; bar < 4; bar++) {
            int actual = sample(captured, content, sw, sh, 100 + 200 * bar, 300);
            if (!near(actual, colors[bar])) throw new IllegalArgumentException("bar " + bar + " differs from frame parity");
            actualColors[bar] = String.format(java.util.Locale.ROOT, "%06x", actual & 0xffffff);
        }
        if (seen[frameId]) return;
        seen[frameId] = true;
        certifiedCount++;
        lastCertifiedFrame = frameId;
        CertificationListener listener = certificationListener;
        if (listener != null) listener.onFrameCertified(new Certification(expected, frameId, frame.sequence,
                frame.width, frame.height, sw, sh, generation, actualColors));
    }

    private static int sample(Bitmap captured, RectF content, int sw, int sh, int x, int y) {
        float surfaceX = content.left + (x + 0.5f) * content.width() / FRAME_WIDTH;
        float surfaceY = content.top + (y + 0.5f) * content.height() / FRAME_HEIGHT;
        int xx = Math.max(0, Math.min(captured.getWidth() - 1, (int) (surfaceX * captured.getWidth() / sw)));
        int yy = Math.max(0, Math.min(captured.getHeight() - 1, (int) (surfaceY * captured.getHeight() / sh)));
        return captured.getPixel(xx, yy);
    }

    private static int binary(int color) {
        if (near(color, Color.BLACK)) return 0;
        if (near(color, Color.WHITE)) return 1;
        throw new IllegalArgumentException("nonbinary marker pixel");
    }

    private static boolean near(int actual, int expected) {
        return Math.abs(Color.red(actual) - Color.red(expected)) <= TOLERANCE
                && Math.abs(Color.green(actual) - Color.green(expected)) <= TOLERANCE
                && Math.abs(Color.blue(actual) - Color.blue(expected)) <= TOLERANCE;
    }

    private void reportError(String message) {
        CertificationListener listener = certificationListener;
        if (listener != null) listener.onCertificationError(message);
    }

    @Override public void surfaceCreated(SurfaceHolder holder) {
        ready = true;
        surfaceGeneration++;
        scheduleRender();
    }

    @Override public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) {
        surfaceGeneration++;
        scheduleRender();
    }

    @Override public void surfaceDestroyed(SurfaceHolder holder) {
        ready = false;
        surfaceGeneration++;
        if (displayed != null) {
            displayed.recycle();
            displayed = null;
        }
    }
}
