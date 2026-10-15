package io.github.russianranger.cohclientinteractive.recovery037;

import android.content.Context;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.os.Build;
import android.os.Process;
import java.io.IOException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.List;

/** NEW, dormant, read-only Android API binding; not an Android fixture adapter.
 * Not part of the active Android source tree. No file opens, JNI load, process
 * start, fixture receipt or production caller. A real SDK compile and device
 * tests remain mandatory; the recovery host has no Android SDK.
 */
public final class AndroidCurrentPackageState {
    private AndroidCurrentPackageState() {}

    public static InstalledPackagePreflight.PackageState read(Context context) throws IOException {
        if (context == null || Build.VERSION.SDK_INT < 28)
            throw new IOException("Current Android signing API required");
        String name = context.getPackageName();
        if (!InstalledPackagePreflight.PACKAGE.equals(name))
            throw new IOException("Exact current app context required");
        final PackageInfo installed;
        try {
            // A fresh query on EACH read, never context.getApplicationInfo(), an
            // archived APK PackageInfo, getPackageArchiveInfo or cached metadata.
            installed = context.getPackageManager().getPackageInfo(name,
                    PackageManager.GET_SIGNING_CERTIFICATES);
        } catch (PackageManager.NameNotFoundException error) {
            throw new IOException("Current installed package unavailable", error);
        }
        ApplicationInfo app = installed.applicationInfo;
        if (!name.equals(installed.packageName) || app == null || !name.equals(app.packageName)
                || app.uid != Process.myUid() || installed.signingInfo == null)
            throw new IOException("Current installed package authority differs");
        // Rotation history is NOT the current contents signer set.
        Signature[] current = installed.signingInfo.getApkContentsSigners();
        if (current == null || current.length < 1 || current.length > 8)
            throw new IOException("Exact current signing certificate set unavailable");
        List<String> signers = new ArrayList<String>();
        for (Signature signature : current) {
            if (signature == null) throw new IOException("Missing current signing certificate");
            signers.add(sha256(signature.toByteArray()));
        }
        return new InstalledPackagePreflight.PackageState(name, Process.myUid(), installed.packageName,
                app.uid, installed.getLongVersionCode(), installed.lastUpdateTime,
                app.sourceDir, app.nativeLibraryDir, signers);
    }

    private static String sha256(byte[] bytes) throws IOException {
        try {
            byte[] hash = MessageDigest.getInstance("SHA-256").digest(bytes);
            char[] hex = "0123456789abcdef".toCharArray(), result = new char[hash.length * 2];
            for (int i = 0; i < hash.length; i++) {
                result[i * 2] = hex[(hash[i] >>> 4) & 15]; result[i * 2 + 1] = hex[hash[i] & 15];
            }
            return new String(result);
        } catch (NoSuchAlgorithmException error) { throw new IOException("SHA-256 unavailable", error); }
    }
}
