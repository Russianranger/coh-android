package org.coh.nativecombined;

/** Explicit local world-handoff diagnostic, owned by one executor.
 * Character byte[] is transient private picker content. report() contains only
 * bounded scalar observations; raw initial reception never permits gameplay,
 * READY, character/full-update ACK or world authority. A fresh begin is needed
 * after suspend/disconnect; handles are opaque tokens, never exported. */
public final class InteropNative {
    static { System.loadLibrary("coh_combined_interop"); }
    private InteropNative() { }
    public static native long begin(int dbPort, String account, int networkVersion,
            boolean encryptionRequired, boolean outboundCompressed, long nowMs);
    public static native int service(long handle, long nowMs);
    public static native byte[] characters(long handle);
    public static native int choose(long handle, int wireSlot, long nowMs);
    public static native String report(long handle);
    public static native void disconnect(long handle);
    public static native void suspend(long handle);
    public static native void close(long handle);
}
