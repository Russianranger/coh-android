package io.github.russianranger.cohclientinteractive.recovery037;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Typed host mocks only; no claim about actual Android package/filesystem IO. */
public final class InstalledPackagePreflightHarness {
    static final String PACKAGE = InstalledPackagePreflight.PACKAGE;
    static final String FILES = "/data/user/0/" + PACKAGE + "/files";
    static final String APK = "/data/app/current/base.apk", NATIVE = "/data/app/current/lib/arm64";
    static final String SHA = repeated('a'), LIBSHA = "3d21ece5894b46e9315eb14c3cc12f8d2fcbd3082f99031b4bcbde3e03d5e282";
    static final String[] GUESTS = {"/state", "/tmp", "/presentation-socket", "/game-import", "/opt/coh", "/opt/coh/pgsql", "/opt/wine"};
    static final int UID = 10303;

    static String repeated(char c) { char[] value = new char[64]; Arrays.fill(value, c); return new String(value); }
    static final class Mock {
        String name = PACKAGE, context = PACKAGE, source = APK, directory = NATIVE;
        int uid = UID, processUid = UID;
        long version = 52, update = 1792000000000L;
        List<String> signers = new ArrayList<String>(Arrays.asList(SHA));
        InstalledPackagePreflight.ObjectState apk = object(APK, APK, 1, 100, 1000, 0100644, 999999, SHA);
        InstalledPackagePreflight.ObjectState library = object(NATIVE + "/" + InstalledPackagePreflight.LIBRARY,
                NATIVE + "/" + InstalledPackagePreflight.LIBRARY, 1, 101, 1000, 0100755, 29992, LIBSHA);
        List<InstalledPackagePreflight.ObjectState> roots = new ArrayList<InstalledPackagePreflight.ObjectState>();
        Mock() { for (int i = 0; i < 7; i++) roots.add(object(FILES + "/root" + i, FILES + "/root" + i, 1, 200 + i, UID, 0040700, 4096, null)); }
        InstalledPackagePreflight.PackageState packageState() throws IOException {
            return new InstalledPackagePreflight.PackageState(context, processUid, name, uid, version, update, source, directory, signers);
        }
        InstalledPackagePreflight.Observation observation() throws IOException {
            return new InstalledPackagePreflight.Observation(packageState(), apk, library, roots);
        }
    }
    static InstalledPackagePreflight.ObjectState object(String path, String canonical, long dev, long ino,
            int uid, int mode, long bytes, String digest) {
        return new InstalledPackagePreflight.ObjectState(path, canonical, dev, ino, uid, mode, bytes, 100, 101, digest);
    }
    static InstalledPackagePreflight.ObjectState change(InstalledPackagePreflight.ObjectState old, String field) {
        return new InstalledPackagePreflight.ObjectState(
            field.equals("path") ? old.requestedPath + ".other" : old.requestedPath,
            field.equals("canonical") ? old.canonicalPath + ".other" : old.canonicalPath,
            field.equals("device") ? old.device + 1 : field.equals("zero-device") ? 0 : old.device,
            field.equals("inode") ? old.inode + 1 : field.equals("zero-inode") ? 0 : old.inode,
            field.equals("uid") ? old.uid + 1 : field.equals("system-uid") ? 1000 : field.equals("negative-uid") ? -1 : old.uid,
            field.equals("symlink") ? 0120777 : field.equals("directory") ? 0040755 : field.equals("regular") ? 0100600
                : field.equals("writable") ? old.mode | 0022 : old.mode,
            field.equals("bytes") ? old.bytes + 1 : old.bytes,
            field.equals("mtime") ? old.modifiedNanos + 1 : old.modifiedNanos,
            field.equals("ctime") ? old.changedNanos + 1 : old.changedNanos,
            field.equals("digest") ? repeated('b') : old.sha256);
    }
    static List<InstalledPackagePreflight.Binding> bindings() {
        List<InstalledPackagePreflight.Binding> roots = new ArrayList<InstalledPackagePreflight.Binding>();
        for (int i = 0; i < 7; i++) roots.add(new InstalledPackagePreflight.Binding(GUESTS[i], FILES + "/root" + i));
        return roots;
    }
    static InstalledPackagePreflight.Pins pins(List<String> signers, List<InstalledPackagePreflight.Binding> roots) throws IOException {
        return new InstalledPackagePreflight.Pins(PACKAGE, UID, 52, 1792000000000L, APK, NATIVE, FILES, 1,
                signers, 999999, SHA, 29992, LIBSHA, roots);
    }
    static void run(String test) throws Exception {
        Mock first = new Mock(), next = new Mock(); boolean expected = false;
        List<String> pinSigners = new ArrayList<String>(Arrays.asList(SHA));
        List<InstalledPackagePreflight.Binding> rootPins = bindings();
        InstalledPackagePreflight.Pins pins;
        if (test.equals("missing-pin")) {
            refuse(null, first.observation(), next.observation()); return;
        }
        if (test.startsWith("pin-")) {
            if (test.equals("pin-too-few-roots")) rootPins.remove(6);
            else if (test.equals("pin-wrong-order")) rootPins.set(0, new InstalledPackagePreflight.Binding(GUESTS[1], FILES + "/root0"));
            else if (test.equals("pin-root-escape")) rootPins.set(0, new InstalledPackagePreflight.Binding(GUESTS[0], FILES + "-other/root0"));
            else if (test.equals("pin-dot-root")) rootPins.set(0, new InstalledPackagePreflight.Binding(GUESTS[0], FILES + "/../root0"));
            else if (test.equals("pin-double-slash")) rootPins.set(0, new InstalledPackagePreflight.Binding(GUESTS[0], FILES + "//root0"));
            else if (test.equals("pin-duplicate-root")) rootPins.set(1, new InstalledPackagePreflight.Binding(GUESTS[1], FILES + "/root0"));
            else if (test.equals("pin-empty-signer")) pinSigners.clear();
            else if (test.equals("pin-malformed-signer")) pinSigners.set(0, "bad");
            else if (test.equals("pin-duplicate-signer")) pinSigners.add(SHA);
            else throw new AssertionError("Unknown pin case " + test);
            try { pins(pinSigners, rootPins); } catch (IOException rejected) { return; }
            throw new AssertionError("Invalid pins accepted");
        }
        pins = pins(pinSigners, rootPins);
        if (test.equals("system-owned-library-valid")) expected = true;
        else if (test.equals("closed-after-valid")) {
            InstalledPackagePreflight.compareNecessaryFacts(pins, first.observation(), next.observation());
            if (InstalledPackagePreflight.androidAdmissionAllowed()) throw new AssertionError("Admission opened"); return;
        }
        else if (test.equals("defensive-pins")) { pinSigners.clear(); rootPins.clear(); expected = true; }
        else if (test.equals("defensive-observation")) {
            InstalledPackagePreflight.Observation before = first.observation(); first.roots.clear();
            InstalledPackagePreflight.compareNecessaryFacts(pins, before, next.observation()); return;
        }
        else if (test.equals("wrong-package")) next.name += ".other";
        else if (test.equals("wrong-context")) next.context += ".other";
        else if (test.equals("wrong-process-uid")) next.processUid++;
        else if (test.equals("wrong-package-uid")) next.uid++;
        else if (test.equals("wrong-version")) next.version++;
        else if (test.equals("wrong-update")) next.update++;
        else if (test.equals("wrong-source")) next.source = "/data/app/old/base.apk";
        else if (test.equals("wrong-native-dir")) next.directory = "/data/app/old/lib/arm64";
        else if (test.equals("wrong-signer")) next.signers.set(0, repeated('c'));
        else if (test.equals("rotation-history-is-not-current")) next.signers.add(repeated('c'));
        else if (test.equals("missing-roots")) next.roots.clear();
        else if (test.equals("root-system-owned")) next.roots.set(0, change(next.roots.get(0), "system-uid"));
        else if (test.equals("root-mixed-device-current")) {
            first.roots.set(0, change(first.roots.get(0), "device"));
            next.roots.set(0, change(next.roots.get(0), "device"));
        }
        else if (test.equals("root-object-alias")) {
            InstalledPackagePreflight.ObjectState root = next.roots.get(1);
            next.roots.set(1, new InstalledPackagePreflight.ObjectState(root.requestedPath, root.canonicalPath,
                    1, 200, UID, root.mode, root.bytes, root.modifiedNanos, root.changedNanos, null));
        }
        else if (test.startsWith("root-")) next.roots.set(0, change(next.roots.get(0), test.substring(5)));
        else if (test.startsWith("library-")) next.library = change(next.library, test.substring(8));
        else if (test.startsWith("apk-")) next.apk = change(next.apk, test.substring(4));
        else throw new AssertionError("Unknown case " + test);
        if (expected) InstalledPackagePreflight.compareNecessaryFacts(pins, first.observation(), next.observation());
        else refuse(pins, first.observation(), next.observation());
    }
    static void refuse(InstalledPackagePreflight.Pins pins, InstalledPackagePreflight.Observation before,
            InstalledPackagePreflight.Observation after) throws Exception {
        try { InstalledPackagePreflight.compareNecessaryFacts(pins, before, after); }
        catch (IOException rejected) { return; }
        throw new AssertionError("Invalid current facts accepted");
    }
    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new AssertionError("Exactly one explicit case required");
        run(args[0]); System.out.println("host_policy_pass:" + args[0] + ";android_admission=false");
    }
}
