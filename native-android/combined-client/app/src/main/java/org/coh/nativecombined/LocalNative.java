package org.coh.nativecombined;

/** Nonblocking local development transport; one executor owns every call.
 * Character names are transient UI content, never diagnostic report fields.
 * No password or authenticated AuthServer receipt can be supplied here. */
public final class LocalNative {
    static { System.loadLibrary("coh_combined_network"); }
    private LocalNative() { }
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
