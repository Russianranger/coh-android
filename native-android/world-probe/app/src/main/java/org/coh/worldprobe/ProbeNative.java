package org.coh.worldprobe;

import android.view.Surface;

public final class ProbeNative {
    static { System.loadLibrary("coh_world_probe"); }
    private ProbeNative() { }
    public static native String probe(Surface surface, byte[] world,
            byte[] worldReference, byte[] materialReference);
}
