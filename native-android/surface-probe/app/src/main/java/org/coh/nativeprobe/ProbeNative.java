package org.coh.nativeprobe;

import android.view.Surface;

/** Each bounded call owns and destroys its EGL resources before returning. */
public final class ProbeNative {
    static { System.loadLibrary("coh_surface_probe"); }
    private ProbeNative() {}
    public static native String probe(Surface surface, byte[] dds, byte[] expectedRgba);
}
