package io.github.russianranger.cohclientinteractive;

/** Platform-independent input bounds and letterbox mapping shared by touch and controller paths. */
public final class ClientInput {
    private ClientInput() {}
    public static final int MAX_TEXT = 32;
    public static final class Point {
        public final int x, y;
        Point(int x, int y) { this.x = x; this.y = y; }
    }
    public static Point map(float x, float y, int viewWidth, int viewHeight,
            int frameWidth, int frameHeight, boolean clamp) {
        if (!Float.isFinite(x) || !Float.isFinite(y) || viewWidth < 1 || viewHeight < 1
                || frameWidth < 1 || frameHeight < 1 || frameWidth > 1024 || frameHeight > 768)
            return null;
        float scale = Math.min(viewWidth / (float) frameWidth, viewHeight / (float) frameHeight);
        float left = (viewWidth - frameWidth * scale) * 0.5f;
        float top = (viewHeight - frameHeight * scale) * 0.5f;
        if (!clamp && (x < left || y < top || x >= left + frameWidth * scale
                || y >= top + frameHeight * scale)) return null;
        return new Point(Math.max(0, Math.min(frameWidth - 1, (int) Math.floor((x - left) / scale))),
                Math.max(0, Math.min(frameHeight - 1, (int) Math.floor((y - top) / scale))));
    }
    public static float axis(float value) {
        if (!Float.isFinite(value)) return 0;
        float magnitude = Math.min(1, Math.abs(value));
        return magnitude <= 0.18f ? 0 : Math.copySign((magnitude - 0.18f) / 0.82f, value);
    }
    public static boolean validText(String value) {
        if (value == null || value.isEmpty() || value.length() > MAX_TEXT) return false;
        for (int i = 0; i < value.length(); i++) if (value.charAt(i) < 32 || value.charAt(i) > 126) return false;
        return true;
    }
    public static int unicodeKeysym(int codePoint) {
        if (codePoint >= 32 && codePoint <= 255) return codePoint;
        if (codePoint >= 256 && codePoint <= 0x10ffff && !(codePoint >= 0xd800 && codePoint <= 0xdfff))
            return 0x01000000 | codePoint;
        return 0;
    }
}
