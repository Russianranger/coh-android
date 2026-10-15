package org.coh.sessionclient;

import android.view.Surface;

public final class SessionNative {
    static { System.loadLibrary("coh_session_client"); }
    private SessionNative() { }
    public static native long createSession(byte[] world, byte[] character, byte[] rig,
            byte[] morph, byte[] locomotion, byte[] walkable, byte[] map);
    public static native int render(long handle, Surface surface, long epoch);
    public static native void state(long handle, long epoch, boolean foreground);
    public static native void input(long handle, float forward, float strafe, float lookX, float lookY);
    public static native void controls(long handle, int directions, float lookX, float lookY);
    public static native void look(long handle, float dx, float dy);
    public static native void focus(long handle);
    public static native void cancel(long handle);
    public static native void reset(long handle);
    public static native void viewDistance(long handle);
    public static native String snapshot(long handle);
    public static native void destroy(long handle);
}
