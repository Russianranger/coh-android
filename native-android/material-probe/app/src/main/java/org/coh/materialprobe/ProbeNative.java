package org.coh.materialprobe;

import android.view.Surface;

/** Each bounded call owns and destroys its EGL resources before returning. */
public final class ProbeNative {
    static { System.loadLibrary("coh_material_probe"); }
    private ProbeNative() {}
    public static native String probe(Surface surface, byte[] mesh, byte[] texture0Rgba,
            byte[] texture1Rgba, byte[] poseReferences, byte[] materialReferences);
}
