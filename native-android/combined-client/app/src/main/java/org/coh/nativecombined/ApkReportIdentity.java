package org.coh.nativecombined;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/** Bounded APK provenance for report owners; contains no Android or JSON API. */
final class ApkReportIdentity {
    private static final long MAX_APK_BYTES = 25L * 1024L * 1024L;
    private static final int BUFFER_BYTES = 64 * 1024;
    private static final char[] HEX = "0123456789abcdef".toCharArray();

    static final class Snapshot {
        final long bytes;
        final String sha256;

        private Snapshot(long bytes, String sha256) {
            this.bytes = bytes;
            this.sha256 = sha256;
        }
    }

    private ApkReportIdentity() { }

    /** The caller supplies its installed application sourceDir, never user input.
     * Capture once on its background owner and retain the immutable result.
     * Reject observable changes while reading; this is not a file-lock contract. */
    static Snapshot capture(File file) throws IOException {
        try {
            if (file == null || !file.isFile()) throw new IOException("APK identity unavailable");
            long expectedBytes = file.length();
            long expectedModified = file.lastModified();
            if (expectedBytes <= 0 || expectedBytes > MAX_APK_BYTES)
                throw new IOException("APK identity size rejected");
            MessageDigest digest;
            try {
                digest = MessageDigest.getInstance("SHA-256");
            } catch (NoSuchAlgorithmException unavailable) {
                throw new IOException("APK identity digest unavailable");
            }
            long bytes = 0;
            try (FileInputStream input = new FileInputStream(file)) {
                if (input.getChannel().size() != expectedBytes)
                    throw new IOException("APK identity changed");
                byte[] buffer = new byte[BUFFER_BYTES];
                int count;
                while ((count = input.read(buffer)) != -1) {
                    bytes += count;
                    if (bytes > expectedBytes || bytes > MAX_APK_BYTES)
                        throw new IOException("APK identity changed");
                    digest.update(buffer, 0, count);
                }
                if (bytes != expectedBytes || input.getChannel().size() != expectedBytes
                        || !file.isFile() || file.length() != expectedBytes
                        || file.lastModified() != expectedModified)
                    throw new IOException("APK identity changed");
            }
            byte[] hash = digest.digest();
            char[] hex = new char[hash.length * 2];
            for (int i = 0; i < hash.length; i++) {
                hex[i * 2] = HEX[(hash[i] & 255) >>> 4];
                hex[i * 2 + 1] = HEX[hash[i] & 15];
            }
            return new Snapshot(bytes, new String(hex));
        } catch (IOException | SecurityException unavailable) {
            // Platform I/O exceptions can include the installed filesystem path.
            // Keep this report helper's outward failure message path-free.
            throw new IOException("APK identity unavailable");
        }
    }

    /** JSON-style package/version comparison without coercing strings, floating
     * values, booleans, or arbitrary Number subclasses into a current report. */
    static boolean sameAppReport(String currentPackage, long currentVersion,
            Object reportedPackage, Object reportedVersion) {
        if (currentPackage == null || currentPackage.length() == 0 || currentVersion <= 0
                || !(reportedPackage instanceof String) || !currentPackage.equals(reportedPackage)
                || (!(reportedVersion instanceof Integer) && !(reportedVersion instanceof Long)))
            return false;
        long version = ((Number) reportedVersion).longValue();
        return version > 0 && version == currentVersion;
    }
}
