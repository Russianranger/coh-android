package org.coh.nativecombined;

/** Explicit local world-handoff diagnostic, owned by one executor.
 * Character byte[] is transient private picker content. report() contains only
 * bounded scalar observations; raw initial reception never permits gameplay,
 * READY, character/full-update ACK or world authority. A fresh begin is needed
 * after suspend/disconnect; handles are opaque tokens, never exported. */
public final class InteropNative {
    static { System.loadLibrary("coh_combined_interop"); }
    private InteropNative() { }
    /** Verify the actual local server common BodyParts cache before this attempt. */
    public static native int configureBodyPartsCache(String absolutePath);
    /** Map the exact bundled CLIENT strings/palette for the next handoff owner. */
    public static native int configureClientSlots(android.content.res.AssetManager assets);
    public static native long begin(int dbPort, String account, int networkVersion,
            boolean encryptionRequired, boolean outboundCompressed, long nowMs);
    public static native int service(long handle, long nowMs);
    public static native byte[] characters(long handle);
    public static native int choose(long handle, int wireSlot, long nowMs);
    public static native String report(long handle);
    /** Actual first selected-self wire observation: 16 little-endian bytes: int index,3 floats. */
    public static native byte[] observedSelfPose(long handle);
    /** Capture profile only: bounded framed INITIAL bytes; query on the network owner before close. */
    public static native byte[] exportInitialReplay(long handle);
    /** Scalar owner state independent of bounded report serialization.
     * Bits: owner present=1, terminal=2, raw initial observed=4, characters ready=8. */
    public static native int controlState(long handle);
    public static native void disconnect(long handle);
    public static native void suspend(long handle);
    public static native void close(long handle);
}
