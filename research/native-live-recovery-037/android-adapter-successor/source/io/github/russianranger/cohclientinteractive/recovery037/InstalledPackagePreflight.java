package io.github.russianranger.cohclientinteractive.recovery037;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** NEW research successor, not recovered ClientLiveDirectoryAndroidFixture.
 *
 * This is a necessary-facts comparator, never filesystem/package authority.
 * Host-supplied observations exercise policy only. A future Android owner must
 * collect exact CURRENT PackageInfo and held nofollow file/ancestor witnesses,
 * hash held FDs, and recheck them around all observations. This class cannot
 * start a fixture, load JNI, register a provider or grant Android admission.
 */
public final class InstalledPackagePreflight {
    public static final String PACKAGE = "io.github.russianranger.cohclientinteractive";
    public static final String LIBRARY = "libcoh_live_directory.so";
    private static final String[] GUESTS = {"/state", "/tmp", "/presentation-socket",
        "/game-import", "/opt/coh", "/opt/coh/pgsql", "/opt/wine"};
    private static final int DIRECTORY = 0040000, REGULAR = 0100000, TYPE = 0170000;

    private InstalledPackagePreflight() {}

    /** Values require a separate authenticated current package/material owner.
     * There is intentionally no exported-JSON importer or historical receipt
     * loader. Construction alone does not make these pins authoritative. */
    public static final class Pins {
        final String packageName, sourceApk, nativeLibraryDir, filesRoot;
        final int appUid;
        final long versionCode, lastUpdateMillis, apkBytes, libraryBytes, appDataDevice;
        final String apkSha256, librarySha256;
        final List<String> currentSigners;
        final List<Binding> bindings;

        public Pins(String name, int uid, long version, long updated, String source,
                String nativeDirectory, String files, long currentAppDataDevice, List<String> signers,
                long apkSize, String apkDigest, long librarySize, String libraryDigest,
                List<Binding> roots) throws IOException {
            require(PACKAGE.equals(name) && uid > 0 && version > 0 && updated > 0,
                    "Current installed app identity is required");
            path(source); path(nativeDirectory); path(files);
            require(currentAppDataDevice != 0, "Current app-data device pin required");
            require(!"/".equals(files) && !"/data".equals(files)
                    && !within(files, source) && !within(files, nativeDirectory),
                    "Installed package and private data authorities must be separate");
            require(apkSize > 0 && apkSize <= 512L * 1024 * 1024
                    && librarySize > 0 && librarySize <= 1024 * 1024,
                    "Current package component bounds differ");
            digest(apkDigest); digest(libraryDigest);
            packageName = name; appUid = uid; versionCode = version; lastUpdateMillis = updated;
            sourceApk = source; nativeLibraryDir = nativeDirectory; filesRoot = files;
            appDataDevice = currentAppDataDevice;
            currentSigners = signerSet(signers); apkBytes = apkSize; apkSha256 = apkDigest;
            libraryBytes = librarySize; librarySha256 = libraryDigest;
            require(roots != null && roots.size() == GUESTS.length, "Exactly seven private roots required");
            List<Binding> selected = new ArrayList<Binding>(); Set<String> hosts = new HashSet<String>();
            for (int i = 0; i < GUESTS.length; i++) {
                Binding root = roots.get(i);
                require(root != null && GUESTS[i].equals(root.guest), "Finalized guest root order differs");
                path(root.host);
                require(within(files, root.host) && !files.equals(root.host) && hosts.add(root.host),
                        "Private data root escapes or aliases declared storage");
                selected.add(root);
            }
            bindings = Collections.unmodifiableList(selected);
        }
    }

    public static final class Binding {
        final String guest, host;
        public Binding(String guestPath, String hostPath) { guest = guestPath; host = hostPath; }
    }

    /** Exact PackageManager.getPackageInfo(GET_SIGNING_CERTIFICATES) projection.
     * Only getApkContentsSigners(), never signing history, supplies signers. */
    public static final class PackageState {
        final String contextPackage, packageName, sourceApk, nativeLibraryDir;
        final int processUid, packageUid;
        final long versionCode, lastUpdateMillis;
        final List<String> currentSigners;
        public PackageState(String contextName, int realUid, String name, int installedUid,
                long version, long updated, String source, String nativeDirectory,
                List<String> signers) throws IOException {
            contextPackage = contextName; processUid = realUid; packageName = name;
            packageUid = installedUid; versionCode = version; lastUpdateMillis = updated;
            sourceApk = source; nativeLibraryDir = nativeDirectory;
            currentSigners = signerSet(signers);
        }
        private boolean same(PackageState other) {
            return other != null && equal(contextPackage, other.contextPackage)
                && processUid == other.processUid && equal(packageName, other.packageName)
                && packageUid == other.packageUid && versionCode == other.versionCode
                && lastUpdateMillis == other.lastUpdateMillis && equal(sourceApk, other.sourceApk)
                && equal(nativeLibraryDir, other.nativeLibraryDir) && currentSigners.equals(other.currentSigners);
        }
    }

    /** Necessary held-object projection. These fields are untrusted when
     * constructed by a host mock; no flags can convert them into Android proof.
     * mode is the full Linux st_mode, dates are nanoseconds, sha256 is FD bytes.
     * all ancestors must separately remain held and nofollow under the owner. */
    public static final class ObjectState {
        final String requestedPath, canonicalPath, sha256;
        final long device, inode, bytes, modifiedNanos, changedNanos;
        final int uid, mode;
        public ObjectState(String requested, String canonical, long dev, long ino, int owner,
                int permissions, long size, long modified, long changed, String digest) {
            requestedPath = requested; canonicalPath = canonical; device = dev; inode = ino;
            uid = owner; mode = permissions; bytes = size; modifiedNanos = modified;
            changedNanos = changed; sha256 = digest;
        }
        private boolean same(ObjectState other) {
            return other != null && equal(requestedPath, other.requestedPath)
                && equal(canonicalPath, other.canonicalPath) && device == other.device
                && inode == other.inode && uid == other.uid && mode == other.mode
                && bytes == other.bytes && modifiedNanos == other.modifiedNanos
                && changedNanos == other.changedNanos && equal(sha256, other.sha256);
        }
    }

    public static final class Observation {
        final PackageState installed;
        final ObjectState apk, library;
        final List<ObjectState> privateRoots;
        public Observation(PackageState current, ObjectState currentApk, ObjectState currentLibrary,
                List<ObjectState> roots) {
            installed = current; apk = currentApk; library = currentLibrary;
            privateRoots = roots == null ? null : Collections.unmodifiableList(new ArrayList<ObjectState>(roots));
        }
    }

    /** Testable policy comparison. A successful return is NOT Android admission.
     * before/after represent independent current observations around held-FD IO.
     * No observation is accepted from an archived fixture/receipt. */
    public static void compareNecessaryFacts(Pins pins, Observation before, Observation after)
            throws IOException {
        require(pins != null && before != null && after != null, "Current observations required");
        check(pins, before); check(pins, after);
        require(before.installed.same(after.installed), "Installed package changed during observation");
        require(before.apk.same(after.apk) && before.library.same(after.library),
                "Held installed object changed or was retargeted");
        for (int i = 0; i < GUESTS.length; i++)
            require(before.privateRoots.get(i).same(after.privateRoots.get(i)),
                    "Held private root changed or was retargeted");
    }

    private static void check(Pins pins, Observation observation) throws IOException {
        PackageState current = observation.installed;
        require(current != null && pins.packageName.equals(current.contextPackage)
                && pins.packageName.equals(current.packageName) && current.processUid == pins.appUid
                && current.packageUid == pins.appUid && current.versionCode == pins.versionCode
                && current.lastUpdateMillis == pins.lastUpdateMillis
                && pins.sourceApk.equals(current.sourceApk)
                && pins.nativeLibraryDir.equals(current.nativeLibraryDir)
                && pins.currentSigners.equals(current.currentSigners), "Exact current installation differs");
        regular(observation.apk, pins.sourceApk, pins.apkBytes, pins.apkSha256);
        regular(observation.library, pins.nativeLibraryDir + "/" + LIBRARY,
                pins.libraryBytes, pins.librarySha256);
        // Deliberately no app-UID condition on either installed object. Android's
        // package manager owns authority for the exact installed package, and
        // extracted native libraries may be system-owned/world-readable.
        require(observation.privateRoots != null && observation.privateRoots.size() == GUESTS.length,
                "Exactly seven held private roots required");
        Set<String> objects = new HashSet<String>();
        for (int i = 0; i < GUESTS.length; i++) {
            ObjectState root = observation.privateRoots.get(i);
            exact(root, pins.bindings.get(i).host, DIRECTORY);
            require(root.uid == pins.appUid && root.device == pins.appDataDevice && (root.mode & 0022) == 0,
                    "Private data root UID/device/permissions differ");
            require(objects.add(root.device + ":" + root.inode), "Distinct private roots share an object");
        }
    }

    /** Intentionally no enable parameter or fixture receipt acceptance path. */
    public static boolean androidAdmissionAllowed() { return false; }

    private static void regular(ObjectState object, String expected, long bytes, String sha)
            throws IOException {
        exact(object, expected, REGULAR);
        require(object.bytes == bytes && sha.equals(object.sha256) && (object.mode & 0022) == 0,
                "Current installed bytes/permissions differ");
    }
    private static void exact(ObjectState object, String expected, int kind) throws IOException {
        require(object != null && expected.equals(object.requestedPath) && expected.equals(object.canonicalPath)
                && object.device != 0 && object.inode != 0 && object.uid >= 0
                && (object.mode & TYPE) == kind, "Held current path/object differs");
    }
    private static List<String> signerSet(List<String> supplied) throws IOException {
        require(supplied != null && !supplied.isEmpty() && supplied.size() <= 8,
                "Exact current APK signer set required");
        List<String> copy = new ArrayList<String>();
        for (String signer : supplied) { digest(signer); require(!copy.contains(signer), "Duplicate signer"); copy.add(signer); }
        Collections.sort(copy); return Collections.unmodifiableList(copy);
    }
    private static void path(String value) throws IOException {
        require(value != null && value.startsWith("/") && value.length() <= 4096
                && !value.endsWith("/") && !value.contains("//") && value.indexOf('\0') < 0,
                "Exact absolute path required");
        for (String component : value.substring(1).split("/", -1))
            require(!component.isEmpty() && !component.equals(".") && !component.equals(".."), "Nonlexical path");
    }
    private static boolean within(String root, String item) {
        return item.equals(root) || item.startsWith(root + "/");
    }
    private static boolean equal(Object a, Object b) { return a == null ? b == null : a.equals(b); }
    private static void digest(String value) throws IOException {
        require(value != null && value.matches("[0-9a-f]{64}"), "Exact SHA-256 required");
    }
    private static void require(boolean okay, String message) throws IOException {
        if (!okay) throw new IOException(message);
    }
}
