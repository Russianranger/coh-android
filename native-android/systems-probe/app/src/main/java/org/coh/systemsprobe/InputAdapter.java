package org.coh.systemsprobe;

import android.hardware.input.InputManager;
import android.view.InputDevice;
import android.view.KeyEvent;
import android.view.MotionEvent;
import org.json.JSONException;
import org.json.JSONObject;

/** Android event transport into the bounded native input state. */
public final class InputAdapter implements InputManager.InputDeviceListener {
    public interface Sink {
        void focus(boolean focused);
        void key(int key, boolean down);
        void axes(float x, float y, float z, float rz);
        void touch(int action, int pointerId, float x, float y);
    }
    private static final class Counts {
        long keyDown, keyUp, keyRepeat, motion, touchBegin, touchMove, touchEnd;
        long touchCancel, focusClear, deviceRemoved, controllerEvents;
        int leftDirections, rightDirections, buttonDownMask, touchDirections;
        JSONObject json() throws JSONException {
            JSONObject j = new JSONObject();
            j.put("key_down", keyDown); j.put("key_up", keyUp); j.put("key_repeat", keyRepeat);
            j.put("motion", motion); j.put("touch_begin", touchBegin); j.put("touch_move", touchMove);
            j.put("touch_end", touchEnd); j.put("touch_cancel", touchCancel); j.put("focus_clear", focusClear);
            j.put("device_removed", deviceRemoved); j.put("controller_events", controllerEvents);
            j.put("left_axis_directions", leftDirections); j.put("right_axis_directions", rightDirections);
            j.put("button_down_mask", buttonDownMask); j.put("touch_motion_directions", touchDirections);
            return j;
        }
    }
    private final Sink sink;
    private final Counts external = new Counts(), synthetic = new Counts();
    private boolean inAppSynthetic, focused = true;
    private int controllerId = Integer.MIN_VALUE, touchId = -1;
    private int keyHeldMask, hatHeldMask, forwardedHeldMask;
    private float touchX, touchY;

    public InputAdapter(Sink sink) { if (sink == null) throw new IllegalArgumentException("sink"); this.sink = sink; }
    public void setSynthetic(boolean value) { inAppSynthetic = value; }
    private Counts counts() { return inAppSynthetic ? synthetic : external; }
    private static boolean source(int bits, int source) { return (bits & source) == source; }
    private static boolean controllerSource(int bits) {
        return source(bits, InputDevice.SOURCE_GAMEPAD) || source(bits, InputDevice.SOURCE_JOYSTICK);
    }
    private boolean selectController(int id) {
        if (inAppSynthetic) return true;
        if (controllerId == Integer.MIN_VALUE) controllerId = id;
        return controllerId == id;
    }
    private static int key(int code) {
        switch (code) {
            case KeyEvent.KEYCODE_BUTTON_A: case KeyEvent.KEYCODE_SPACE: return 8;
            case KeyEvent.KEYCODE_BUTTON_B: return 9;
            case KeyEvent.KEYCODE_BUTTON_X: return 10;
            case KeyEvent.KEYCODE_BUTTON_Y: return 11;
            case KeyEvent.KEYCODE_BUTTON_L1: return 12;
            case KeyEvent.KEYCODE_BUTTON_R1: return 13;
            case KeyEvent.KEYCODE_BUTTON_L2: return 14;
            case KeyEvent.KEYCODE_BUTTON_R2: return 15;
            case KeyEvent.KEYCODE_BUTTON_SELECT: return 16;
            case KeyEvent.KEYCODE_BUTTON_START: case KeyEvent.KEYCODE_ENTER: return 17;
            case KeyEvent.KEYCODE_BUTTON_THUMBL: return 18;
            case KeyEvent.KEYCODE_BUTTON_THUMBR: return 19;
            case KeyEvent.KEYCODE_DPAD_UP: case KeyEvent.KEYCODE_W: return 20;
            case KeyEvent.KEYCODE_DPAD_DOWN: case KeyEvent.KEYCODE_S: return 21;
            case KeyEvent.KEYCODE_DPAD_LEFT: case KeyEvent.KEYCODE_A: return 22;
            case KeyEvent.KEYCODE_DPAD_RIGHT: case KeyEvent.KEYCODE_D: return 23;
            default: return -1;
        }
    }
    public boolean dispatchKeyEvent(KeyEvent event) {
        int code = key(event.getKeyCode()), bits = event.getSource();
        if (code < 0 || (!controllerSource(bits) && !source(bits, InputDevice.SOURCE_DPAD)
                && !source(bits, InputDevice.SOURCE_KEYBOARD))) return false;
        if (controllerSource(bits) && !selectController(event.getDeviceId())) return false;
        if (!focused) return true;
        Counts c = counts();
        if (event.getAction() == KeyEvent.ACTION_DOWN) {
            if (event.getRepeatCount() > 0) { c.keyRepeat++; return true; }
            c.keyDown++; c.buttonDownMask |= 1 << code;
            if (controllerSource(bits) && event.getDeviceId() >= 0) c.controllerEvents++;
            keyHeldMask |= 1 << code; forwardKey(code); return true;
        }
        if (event.getAction() == KeyEvent.ACTION_UP) {
            c.keyUp++;
            if (controllerSource(bits) && event.getDeviceId() >= 0) c.controllerEvents++;
            keyHeldMask &= ~(1 << code); forwardKey(code); return true;
        }
        return false;
    }
    private void forwardKey(int code) {
        int bit = 1 << code;
        boolean down = ((keyHeldMask | hatHeldMask) & bit) != 0;
        if (down != ((forwardedHeldMask & bit) != 0)) {
            sink.key(code, down);
            if (down) forwardedHeldMask |= bit; else forwardedHeldMask &= ~bit;
        }
    }
    private static float centered(MotionEvent event, int axis) {
        float value = event.getAxisValue(axis);
        InputDevice device = event.getDevice();
        InputDevice.MotionRange range = device == null ? null : device.getMotionRange(axis, event.getSource());
        if (range != null && Math.abs(value) <= range.getFlat()) return 0;
        return value;
    }
    private static int directions(float x, float y) {
        int mask = 0;
        if (x < -0.5f) mask |= 1;
        if (x > 0.5f) mask |= 2;
        if (y < -0.5f) mask |= 4;
        if (y > 0.5f) mask |= 8;
        return mask;
    }
    public boolean dispatchGenericMotionEvent(MotionEvent event) {
        if (!source(event.getSource(), InputDevice.SOURCE_JOYSTICK)
                || event.getActionMasked() != MotionEvent.ACTION_MOVE
                || !selectController(event.getDeviceId())) return false;
        if (!focused) return true;
        float x = centered(event, MotionEvent.AXIS_X), y = centered(event, MotionEvent.AXIS_Y);
        float z = centered(event, MotionEvent.AXIS_Z), rz = centered(event, MotionEvent.AXIS_RZ);
        Counts c = counts(); c.motion++;
        if (event.getDeviceId() >= 0) c.controllerEvents++;
        c.leftDirections |= directions(x, y); c.rightDirections |= directions(z, rz);
        sink.axes(x, y, z, rz);
        // Source digital HAT commands are separate from both analog sticks.
        float hx = event.getAxisValue(MotionEvent.AXIS_HAT_X), hy = event.getAxisValue(MotionEvent.AXIS_HAT_Y);
        hatHeldMask = (hy < -0.5f ? 1 << 20 : 0) | (hy > 0.5f ? 1 << 21 : 0)
                | (hx < -0.5f ? 1 << 22 : 0) | (hx > 0.5f ? 1 << 23 : 0);
        forwardKey(20); forwardKey(21); forwardKey(22); forwardKey(23);
        return true;
    }
    private static float coordinate(float pixel, int extent) {
        return Math.max(-1f, Math.min(1f, pixel * 2f / Math.max(1, extent) - 1f));
    }
    public boolean dispatchTouchEvent(MotionEvent event, int width, int height) {
        if (!source(event.getSource(), InputDevice.SOURCE_TOUCHSCREEN)) return false;
        int action = event.getActionMasked(), actionIndex = event.getActionIndex();
        Counts c = counts();
        if (action == MotionEvent.ACTION_CANCEL) {
            c.touchCancel++; touchId = -1; keyHeldMask = hatHeldMask = forwardedHeldMask = 0;
            sink.touch(3, -1, 0, 0); return true;
        }
        if (!focused) return true;
        if (action == MotionEvent.ACTION_DOWN || action == MotionEvent.ACTION_POINTER_DOWN) {
            if (touchId >= 0) return true;
            touchId = event.getPointerId(actionIndex);
            touchX = coordinate(event.getX(actionIndex), width); touchY = coordinate(event.getY(actionIndex), height);
            c.touchBegin++; sink.touch(0, touchId, touchX, touchY); return true;
        }
        if (action == MotionEvent.ACTION_UP || action == MotionEvent.ACTION_POINTER_UP) {
            if (event.getPointerId(actionIndex) == touchId) {
                float x = coordinate(event.getX(actionIndex), width), y = coordinate(event.getY(actionIndex), height);
                c.touchEnd++; sink.touch(2, touchId, x, y); touchId = -1;
            }
            return true;
        }
        if (action == MotionEvent.ACTION_MOVE && touchId >= 0) {
            int index = event.findPointerIndex(touchId);
            if (index < 0) {c.touchCancel++;touchId = -1;keyHeldMask = hatHeldMask = forwardedHeldMask = 0;sink.touch(3, -1, 0, 0);return true;}
            // Every historical sample is consumed once for relative pointer motion.
            for (int h = 0; h < event.getHistorySize(); h++) {
                touchMove(c, coordinate(event.getHistoricalX(index, h), width), coordinate(event.getHistoricalY(index, h), height));
            }
            touchMove(c, coordinate(event.getX(index), width), coordinate(event.getY(index), height));
            return true;
        }
        return true;
    }
    private void touchMove(Counts c, float x, float y) {
        float dx = x - touchX, dy = y - touchY;
        if (dx < -0.001f) c.touchDirections |= 1;
        if (dx > 0.001f) c.touchDirections |= 2;
        if (dy < -0.001f) c.touchDirections |= 4;
        if (dy > 0.001f) c.touchDirections |= 8;
        c.touchMove++; sink.touch(1, touchId, x, y); touchX = x; touchY = y;
    }
    public void clear() {
        counts().focusClear++; touchId = -1; keyHeldMask = hatHeldMask = forwardedHeldMask = 0;sink.focus(false);
    }
    public void onWindowFocusChanged(boolean hasFocus) {
        focused = hasFocus;
        if (!hasFocus) clear(); else sink.focus(true);
    }
    @Override public void onInputDeviceAdded(int deviceId) { }
    @Override public void onInputDeviceChanged(int deviceId) {
        if (deviceId == controllerId) {clear();sink.focus(focused);}
    }
    @Override public void onInputDeviceRemoved(int deviceId) {
        if (deviceId == controllerId) {
            counts().deviceRemoved++;clear();controllerId = Integer.MIN_VALUE;sink.focus(focused);
        }
    }
    public JSONObject report() throws JSONException {
        JSONObject j = new JSONObject();
        j.put("schema", "coh-android-input-adapter-v1");
        j.put("external_android", external.json()); j.put("in_app_synthetic", synthetic.json());
        j.put("focused", focused); j.put("touch_active", touchId >= 0);
        j.put("scope", "Android callbacks to source scalar/key/joystick kernels; editor look and preview adapter; no gameplay physics");
        j.put("external_event_provenance", "Framework events; emulator adb injection does not establish physical controller operation");
        return j;
    }
}
