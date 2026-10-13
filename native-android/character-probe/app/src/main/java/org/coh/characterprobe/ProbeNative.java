package org.coh.characterprobe;

import android.view.Surface;

public final class ProbeNative {
    static { System.loadLibrary("coh_character_probe"); }
    private ProbeNative() { }
    public static native String probe(Surface surface, byte[] character, byte[] rig,
            byte[] morph, byte[] characterReference, byte[] materialReference);
}
