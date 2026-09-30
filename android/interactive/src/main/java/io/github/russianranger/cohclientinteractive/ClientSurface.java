package io.github.russianranger.cohclientinteractive;

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
import android.view.MotionEvent;
import android.view.SurfaceHolder;
import android.view.SurfaceView;

import java.io.ByteArrayOutputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;



/** Displays client frames and captures the actual Android Surface, without classifying game state. */
public final class ClientSurface extends SurfaceView implements SurfaceHolder.Callback {
    public interface Listener {
        void onCapture(Capture capture);
        void onCaptureError(String detail);
    }

    public interface InputListener {
        void onPointer(String session, int x, int y, int buttons);
        void onReleaseAll(String session);
        void onCursor(float x, float y, boolean visible);
    }

    public static final class Capture {
        public final String session;
        public final long sequence;
        public final int width, height, surfaceWidth, surfaceHeight;
        public final long capturedAtUptimeMillis;
        public final int surfaceGeneration;
        /** SHA-256 of png, which is a bounded PixelCopy screenshot including letterboxing. */
        public final String sha256;
        /** Color diversity only; this does not establish that a menu or gameplay is visible. */
        public final boolean nonUniform;
        /** This capture owns its PNG bytes; the view neither retains nor subsequently changes them. */
        public final byte[] png;

        private Capture(Frame frame, int sw, int sh, int generation, long capturedAt,
                String hash, boolean varied, byte[] bytes) {
            session = frame.session.id;
            sequence = frame.sequence;
            width = frame.width;
            height = frame.height;
            surfaceWidth = sw;
            surfaceHeight = sh;
            capturedAtUptimeMillis = capturedAt;
            surfaceGeneration = generation;
            sha256 = hash;
            nonUniform = varied;
            png = bytes;
        }
    }

    private static final int CAPTURE_WIDTH = 800;
    private static final int CAPTURE_HEIGHT = 600;
    private static final int MAX_PNG_BYTES = 2 * 1024 * 1024;
    private static final long CAPTURE_INTERVAL_MS = 1000;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final Paint paint = new Paint();
    private final Object pendingLock = new Object();
    private volatile Session session;
    private volatile Listener listener;
    private Frame pending;
    private boolean renderPosted;
    // All remaining mutable state is confined to the main thread.
    private Frame lastFrame;
    private InputListener inputListener;
    private boolean inputEnabled, touchHeld;
    private int touchId = -1, controllerButtons;
    private int inputWidth = 800, inputHeight = 600;
    private float pointerX = 400, pointerY = 300;

    private Bitmap displayed;
    private boolean ready;
    private boolean capturePending;
    private boolean captureTimerPosted;
    private int surfaceGeneration;
    private long nextCaptureAt;
    private final Runnable captureTimer = () -> {
        captureTimerPosted = false;
        scheduleRender();
    };

    private static final class Session {
        final String id;
        Session(String id) { this.id = id; }
    }

    private static final class Frame {
        final Session session;
        final int[] pixels;
        final int width, height;
        final long sequence;
        Frame(Session session, int[] pixels, int width, int height, long sequence) {
            this.session = session;
            this.pixels = pixels;
            this.width = width;
            this.height = height;
            this.sequence = sequence;
        }
    }

    public ClientSurface(Context context) {
        super(context);
        paint.setFilterBitmap(false);
        paint.setDither(false);
        getHolder().addCallback(this);
        setWillNotDraw(true);
    }

    /** Changing sessions invalidates queued frames and in-flight captures from the previous run. */
    public void setSession(String id) {
        if (id == null || !id.matches("[0-9a-f]{32}"))
            throw new IllegalArgumentException("Expected a 32-character lowercase hexadecimal session");
        final Session next;
        synchronized (pendingLock) {
            if (session != null && session.id.equals(id)) return;
            next = new Session(id);
            session = next;
            pending = null;
        }
        main.post(() -> {
            if (session != next) return;
            releaseInput();
            pointerX = inputWidth / 2f; pointerY = inputHeight / 2f;
            if (lastFrame != null && lastFrame.session != next) lastFrame = null;
            main.removeCallbacks(captureTimer);
            captureTimerPosted = false;
            scheduleRender();
        });
    }

    public void setCaptureListener(Listener listener) {
        this.listener = listener;
        main.post(() -> {
            if (this.listener == null) {
                main.removeCallbacks(captureTimer);
                captureTimerPosted = false;
            } else {
                scheduleRender();
            }
        });
    }

    /** Safe from the decoder thread. The copied frame cannot change while it is being presented. */
    public void setFrame(int[] argb, int width, int height, long sequence) {
        if (argb == null || width < 1 || height < 1 || width > InteractiveRfbClient.MAX_WIDTH
                || height > InteractiveRfbClient.MAX_HEIGHT || argb.length != width * height || sequence < 0)
            throw new IllegalArgumentException("Invalid client frame");
        synchronized (pendingLock) {
            if (session == null) return;
            pending = new Frame(session, argb.clone(), width, height, sequence);
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

    private void scheduleCapture() {
        if (!ready || listener == null || lastFrame == null || lastFrame.session != session
                || captureTimerPosted) return;
        captureTimerPosted = true;
        main.postAtTime(captureTimer, Math.max(SystemClock.uptimeMillis(), nextCaptureAt));
    }

    private void renderLatest() {
        final Frame frame;
        synchronized (pendingLock) {
            renderPosted = false;
            // Freeze presentation until PixelCopy completes so sequence identifies the copied frame.
            if (!ready || capturePending) return;
            frame = pending != null ? pending : lastFrame;
            pending = null;
        }
        if (frame == null || frame.session != session) return;
        lastFrame = frame;
        final int generation = surfaceGeneration;
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
        if (destination == null) return;
        if (inputWidth != frame.width || inputHeight != frame.height) {
            releaseInput();
            inputWidth = frame.width; inputHeight = frame.height;
            pointerX = Math.min(pointerX, inputWidth - 1); pointerY = Math.min(pointerY, inputHeight - 1);
        }
        updateCursor();
        if (listener == null) return;
        long now = SystemClock.uptimeMillis();
        if (now < nextCaptureAt) {
            scheduleCapture();
            return;
        }
        nextCaptureAt = now + CAPTURE_INTERVAL_MS;
        final int sw = surfaceWidth, sh = surfaceHeight;
        final RectF content = destination;
        // Evidence is only read from the real Android Surface, never from the RFB pixel array.
        final Bitmap captured = Bitmap.createBitmap(CAPTURE_WIDTH, CAPTURE_HEIGHT, Bitmap.Config.ARGB_8888);
        capturePending = true;
        try {
            PixelCopy.request(this, captured, result -> {
                capturePending = false;
                try {
                    if (!ready || generation != surfaceGeneration || frame.session != session) return;
                    if (result != PixelCopy.SUCCESS) {
                        reportError("PixelCopy result " + result);
                        return;
                    }
                    long capturedAt = SystemClock.uptimeMillis();
                    nextCaptureAt = Math.max(nextCaptureAt, capturedAt + CAPTURE_INTERVAL_MS);
                    boolean varied = hasNonUniformContent(captured, content, sw, sh);
                    BoundedPngOutput output = new BoundedPngOutput();
                    if (!captured.compress(Bitmap.CompressFormat.PNG, 100, output))
                        throw new IllegalStateException("PNG encoding failed");
                    byte[] png = output.toByteArray();
                    Listener target = listener;
                    if (target != null) target.onCapture(new Capture(frame, sw, sh, generation,
                            capturedAt, sha256(png), varied, png));
                } catch (RuntimeException ex) {
                    reportError("Surface capture: " + ex.getClass().getSimpleName());
                } finally {
                    captured.recycle();
                    scheduleRenderIfPending();
                    scheduleCapture();
                }
            }, main);
        } catch (RuntimeException ex) {
            capturePending = false;
            captured.recycle();
            reportError("PixelCopy request: " + ex.getClass().getSimpleName());
            scheduleRenderIfPending();
            scheduleCapture();
        }
    }

    private void scheduleRenderIfPending() {
        synchronized (pendingLock) {
            if (pending == null) return;
        }
        scheduleRender();
    }

    /** Ignore letterboxing: it must not make an otherwise uniform client frame look varied. */
    private static boolean hasNonUniformContent(Bitmap bitmap, RectF content, int sw, int sh) {
        int left = Math.max(0, (int) Math.ceil(content.left * bitmap.getWidth() / sw));
        int top = Math.max(0, (int) Math.ceil(content.top * bitmap.getHeight() / sh));
        int right = Math.min(bitmap.getWidth(), (int) Math.floor(content.right * bitmap.getWidth() / sw));
        int bottom = Math.min(bitmap.getHeight(), (int) Math.floor(content.bottom * bitmap.getHeight() / sh));
        boolean[] colors = new boolean[4096];
        int unique = 0, samples = 0;
        double sum = 0, sumSquares = 0;
        for (int y = top; y < bottom; y += 4) {
            for (int x = left; x < right; x += 4) {
                int pixel = bitmap.getPixel(x, y);
                int red = Color.red(pixel), green = Color.green(pixel), blue = Color.blue(pixel);
                int quantized = ((red >> 4) << 8) | ((green >> 4) << 4) | (blue >> 4);
                if (!colors[quantized]) { colors[quantized] = true; unique++; }
                int luminance = (54 * red + 183 * green + 19 * blue) >> 8;
                sum += luminance;
                sumSquares += luminance * luminance;
                samples++;
            }
        }
        if (samples == 0 || unique < 16) return false;
        double mean = sum / samples;
        double variance = Math.max(0, sumSquares / samples - mean * mean);
        return mean >= 4 && variance >= 100;
    }

    private static String sha256(byte[] bytes) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(bytes);
            char[] hex = new char[digest.length * 2];
            final char[] digits = "0123456789abcdef".toCharArray();
            for (int i = 0; i < digest.length; i++) {
                hex[i * 2] = digits[(digest[i] & 255) >>> 4];
                hex[i * 2 + 1] = digits[digest[i] & 15];
            }
            return new String(hex);
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 unavailable", ex);
        }
    }

    private static final class BoundedPngOutput extends ByteArrayOutputStream {
        BoundedPngOutput() { super(65536); }
        @Override public synchronized void write(int value) {
            if (count >= MAX_PNG_BYTES) throw new IllegalStateException("PNG exceeds size bound");
            super.write(value);
        }
        @Override public synchronized void write(byte[] bytes, int offset, int length) {
            if (length < 0 || length > MAX_PNG_BYTES - count)
                throw new IllegalStateException("PNG exceeds size bound");
            super.write(bytes, offset, length);
        }
    }

    /** Input methods run on the Activity/main thread. Captures remain separate from input overlays. */
    public void setInputListener(InputListener listener) { inputListener = listener; }
    public void setInputEnabled(boolean enabled) {
        if (inputEnabled && !enabled) releaseInput();
        inputEnabled = enabled;
        updateCursor();
    }
    public void movePointer(float dx, float dy) {
        if (!inputEnabled || !ready || !Float.isFinite(dx) || !Float.isFinite(dy)) return;
        pointerX = Math.max(0, Math.min(inputWidth - 1, pointerX + dx));
        pointerY = Math.max(0, Math.min(inputHeight - 1, pointerY + dy));
        sendPointer();
    }
    public void setControllerButtons(int buttons) {
        if (!inputEnabled || !ready || buttons < 0 || buttons > 7) return;
        if (controllerButtons == buttons) return;
        controllerButtons = buttons;
        sendPointer();
    }
    public void releaseInput() {
        boolean wasHeld = touchHeld || controllerButtons != 0;
        touchHeld = false; touchId = -1; controllerButtons = 0;
        Session selected = session;
        if (wasHeld && selected != null && inputListener != null)
            inputListener.onPointer(selected.id, (int) pointerX, (int) pointerY, 0);
        if (selected != null && inputListener != null) inputListener.onReleaseAll(selected.id);
        if (getParent() != null) getParent().requestDisallowInterceptTouchEvent(false);
    }
    private void sendPointer() {
        Session selected = session;
        if (selected != null && inputListener != null)
            inputListener.onPointer(selected.id, (int) pointerX, (int) pointerY,
                    controllerButtons | (touchHeld ? 1 : 0));
        updateCursor();
    }
    private void updateCursor() {
        if (inputListener == null) return;
        float scale = Math.min(getWidth() / (float) inputWidth, getHeight() / (float) inputHeight);
        inputListener.onCursor((getWidth() - inputWidth * scale) * 0.5f + (pointerX + 0.5f) * scale,
                (getHeight() - inputHeight * scale) * 0.5f + (pointerY + 0.5f) * scale,
                inputEnabled && ready);
    }
    @Override public boolean onTouchEvent(MotionEvent event) {
        if (!inputEnabled || !ready) return false;
        int action = event.getActionMasked();
        if (action == MotionEvent.ACTION_DOWN) {
            ClientInput.Point point = ClientInput.map(event.getX(), event.getY(), getWidth(), getHeight(),
                    inputWidth, inputHeight, false);
            if (point == null) return false; // Black margins do not click a game control.
            pointerX = point.x; pointerY = point.y; touchId = event.getPointerId(0); touchHeld = true;
            if (getParent() != null) getParent().requestDisallowInterceptTouchEvent(true);
            sendPointer(); return true;
        }
        if (touchId == -1) return false;
        if (action == MotionEvent.ACTION_CANCEL || action == MotionEvent.ACTION_POINTER_DOWN) {
            releaseInput(); return true;
        }
        int index = event.findPointerIndex(touchId);
        if (index < 0) { releaseInput(); return true; }
        ClientInput.Point point = ClientInput.map(event.getX(index), event.getY(index), getWidth(), getHeight(),
                inputWidth, inputHeight, true);
        if (point != null) { pointerX = point.x; pointerY = point.y; }
        if (action == MotionEvent.ACTION_UP || (action == MotionEvent.ACTION_POINTER_UP
                && event.getPointerId(event.getActionIndex()) == touchId)) {
            touchHeld = false; touchId = -1;
            sendPointer();
            if (getParent() != null) getParent().requestDisallowInterceptTouchEvent(false);
            performClick(); return true;
        }
        if (action == MotionEvent.ACTION_MOVE) { sendPointer(); return true; }
        return true;
    }
    @Override public boolean performClick() { super.performClick(); return true; }
    @Override public void onWindowFocusChanged(boolean focus) {
        super.onWindowFocusChanged(focus);
        if (!focus) releaseInput();
    }

    private void reportError(String detail) {
        Listener target = listener;
        if (target != null) target.onCaptureError(detail);
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
        releaseInput();
        ready = false;
        updateCursor();
        surfaceGeneration++;
        main.removeCallbacks(captureTimer);
        captureTimerPosted = false;
        if (displayed != null) {
            displayed.recycle();
            displayed = null;
        }
    }
}
