package io.github.russianranger.cohclientinteractive;

import java.io.IOException;

/** Closed qualification facade: never loads/registers a production provider. */
public final class NativeLiveDirectory {
    private NativeLiveDirectory() {}
    public static native long nativeCreate(String[] guest, String[] host,
            long[] device, long[] inode, int[] uid, int nativeUid, int guestUid,
            boolean showDotFiles, boolean caseSensitive) throws IOException;
    public static native long nativeOpen(long namespace, String guestDirectory,
            byte[] operation, byte[] directory) throws IOException;
    public static native byte[] nativeNext(long cursor) throws IOException;
    public static native void nativeCloseCursor(long cursor) throws IOException;
    public static native void nativeCloseNamespace(long namespace) throws IOException;
    public static native long[] nativeStats(long namespace) throws IOException;
    public static native long[] nativeIdentity(long cursor) throws IOException;
    public static native String nativeCanonicalGuestPath(long cursor) throws IOException;
}
