package io.github.russianranger.cohclientinteractive;

import java.util.LinkedHashMap;
import java.util.Map;

/** Platform-independent input bounds and letterbox mapping shared by touch and controller paths. */
public final class ClientInput {
    private ClientInput() {}
    public static final int MAX_TEXT = 32;
    public static final int RETURN_KEY = 0xff0d;
    /** Sidebar actions use only these fixed native commands, never editable text. */
    public enum PerformanceCommand {
        SHOW_FPS("show_fps"),
        FPS_10("cap_10"),
        FPS_30("cap_30");
        public final String safeName;
        PerformanceCommand(String safeName) {
            this.safeName = safeName;
        }
    }
    /** One native Enter transaction per physical Start press, including a short tap. */
    public static final class StartButton {
        private boolean held;
        public boolean press(int repeatCount) {
            if (held) return false;
            held = true;
            return repeatCount == 0;
        }
        public void release() { held = false; }
        public void reset() { held = false; }
    }
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
    public static final int FORWARD = 1, BACK = 2, LEFT = 4, RIGHT = 8;
    /** Digital walking engages at 35%, then holds until the stick returns below 20%. */
    public static int walking(float x, float y, int previous) {
        int horizontal = direction(x, (previous & LEFT) != 0 ? -1 : (previous & RIGHT) != 0 ? 1 : 0);
        int vertical = direction(y, (previous & FORWARD) != 0 ? -1 : (previous & BACK) != 0 ? 1 : 0);
        return (horizontal < 0 ? LEFT : horizontal > 0 ? RIGHT : 0)
                | (vertical < 0 ? FORWARD : vertical > 0 ? BACK : 0);
    }
    private static int direction(float value, int previous) {
        if (!Float.isFinite(value)) return 0;
        if (value <= -0.35f) return -1;
        if (value >= 0.35f) return 1;
        if (previous < 0 && value <= -0.20f) return -1;
        if (previous > 0 && value >= 0.20f) return 1;
        return 0;
    }
    public interface KeySender { boolean send(int keysym, boolean down); }
    /** Several physical controls may own one key; only its first/last owner sends an edge. */
    public static final class KeyOwners {
        private final Map<Integer, Integer> owners = new LinkedHashMap<>();
        public boolean contains(int physical) { return owners.containsKey(physical); }
        public void press(int physical, int keysym, KeySender sender) {
            if (keysym == 0 || owners.containsKey(physical)) return;
            boolean held = owners.containsValue(keysym);
            owners.put(physical, keysym);
            if (!held && !sender.send(keysym, true)) owners.remove(physical);
        }
        public void release(int physical, KeySender sender) {
            Integer key = owners.remove(physical);
            if (key != null && !owners.containsValue(key)) sender.send(key, false);
        }
        /** The runtime's emergency release clears remote keys after this local reset. */
        public void clear() { owners.clear(); }
    }
    public static final class WalkingKeys {
        private static final int[] MASKS = {FORWARD, BACK, LEFT, RIGHT};
        private static final int[] KEYS = {'w', 's', 'a', 'd'};
        private int mask;
        public void update(float x, float y, boolean enabled, KeyOwners owners, KeySender sender) {
            int next = enabled ? walking(x, y, mask) : 0;
            // Release opposite directions before pressing their replacements.
            for (int i = 0; i < MASKS.length; i++)
                if ((mask & MASKS[i]) != 0 && (next & MASKS[i]) == 0) owners.release(110001 + i, sender);
            for (int i = 0; i < MASKS.length; i++)
                // A rejected queue write does not acquire an owner; retry that
                // direction on the next stick sample, even if it did not move.
                if ((next & MASKS[i]) != 0 && !owners.contains(110001 + i)) owners.press(110001 + i, KEYS[i], sender);
            mask = next;
        }
        /** Pair with KeyOwners.clear() and the runtime's emergency release. */
        public void reset() { mask = 0; }
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
