package org.coh.animationprobe;

import android.view.Surface;

/** Each bounded animated check owns and destroys its EGL resources before returning. */
public final class ProbeNative {
    static { System.loadLibrary("coh_animation_probe"); }
    private ProbeNative() {}
    public static native String probe(Surface surface, byte[] mesh, byte[] texture0Rgba,
            byte[] texture1Rgba, byte[] rig, byte[] rigReferences, byte[] materialReferences);
}
