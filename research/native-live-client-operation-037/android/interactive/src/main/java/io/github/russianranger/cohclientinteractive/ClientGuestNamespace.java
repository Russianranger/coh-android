package io.github.russianranger.cohclientinteractive;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Immutable provenance for the FINALIZED runCharacter PRoot command.
 *
 * This class issues no filesystem, native registration or cache authority.
 * Its canonical host roots are NOT nofollow/UID/dev/inode proofs. The native
 * owner must open/check/hold them and resolve guest symlinks with directory FDs.
 * Never use a guest absolute symlink target as a raw host pathname.
 */
public final class ClientGuestNamespace {
    public static final String SCHEMA = "COH_GUEST_NAMESPACE_V1";
    public enum Kind { ROOTFS_DIAGNOSTIC, DIRECTORY, FILE, PASSTHROUGH }

    public static final class Binding {
        public final String guestPrefix;
        public final String hostRoot;
        public final Kind kind;
        private Binding(String guest, String host, Kind selected) {
            guestPrefix = guest; hostRoot = host; kind = selected;
        }
    }

    /** A route is not an opened path or permission to read it. */
    public static final class Route {
        public final Binding binding;
        public final String guestPath;
        public final String relativePath;
        private Route(Binding selected, String guest, String relative) {
            binding = selected; guestPath = guest; relativePath = relative;
        }
        public String[] relativeComponents() {
            return relativePath.isEmpty() ? new String[0] : relativePath.split("/", -1);
        }
    }

    /** Exact typed attribution supplied by the operation owner; never proof by itself. */
    public static final class Provenance {
        public final String operationId, sessionId, processInstance;
        public final int realUid;
        public final String runtimeManifestSha256, nativeConsumerSha256, helperIdentitySha256;
        public final long nativeConsumerBytes;
        public Provenance(String operation, String session, String process, int uid,
                          String runtimeSha, String consumerSha, long consumerBytes,
                          String helperSha) throws IOException {
            demand(operation != null && operation.matches("[1-9][0-9]{12,18}-[0-9a-f]{12}"),
                    "Invalid actual operation identity");
            demand(session != null && session.matches("[0-9a-f]{32}"), "Invalid session identity");
            demand(process != null && process.matches("[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}"),
                    "Invalid process instance identity");
            demand(uid >= 0 && consumerBytes > 0 && consumerBytes <= 64L * 1024 * 1024,
                    "Invalid declared native owner/consumer bounds");
            sha(runtimeSha); sha(consumerSha); sha(helperSha);
            operationId = operation; sessionId = session; processInstance = process;
            realUid = uid; runtimeManifestSha256 = runtimeSha;
            nativeConsumerSha256 = consumerSha; nativeConsumerBytes = consumerBytes;
            helperIdentitySha256 = helperSha;
        }
    }

    public static final class LaunchMode {
        public final boolean reopen, resumeEmptyProfile, startupOnly, zoning;
        public final String graphics, gpu;
        public LaunchMode(boolean reopening, boolean resume, boolean only, boolean zones,
                          String selectedGraphics, String selectedGpu) throws IOException {
            demand(!(reopening && resume) && !(!reopening && only), "Inconsistent launch flags");
            demand("standard".equals(selectedGraphics) || "performance".equals(selectedGraphics),
                    "Unknown graphics profile");
            demand("software".equals(selectedGpu) || "turnip".equals(selectedGpu), "Unknown GPU profile");
            reopen = reopening; resumeEmptyProfile = resume; startupOnly = only; zoning = zones;
            graphics = selectedGraphics; gpu = selectedGpu;
        }
    }

    /** Inputs must come from the current locked ClientRuntime and installed APK. */
    public static final class Inputs {
        public final File appFilesRoot, nativeLibraryRoot;
        public final String importGeneration;
        public final Provenance provenance;
        public final LaunchMode mode;
        public Inputs(File files, File installedNativeLibraries, String importedGeneration,
                      Provenance identity, LaunchMode selected) throws IOException {
            demand(files != null && installedNativeLibraries != null && identity != null && selected != null,
                    "Missing typed namespace inputs");
            hostLexical(files.getPath()); hostLexical(installedNativeLibraries.getPath());
            demand(importedGeneration != null && importedGeneration.matches("generation-[0-9a-f]{32}"),
                    "Invalid completed import generation");
            appFilesRoot = files; nativeLibraryRoot = installedNativeLibraries;
            importGeneration = importedGeneration; provenance = identity; mode = selected;
        }
    }

    private final List<Binding> bindings, directories;
    private final List<String> argv;
    private final Map<String, String> processEnvironment;
    private final Provenance provenance;
    private final String statement, statementSha;
    private final String prootLoader, prootTemporaryRoot;

    private ClientGuestNamespace(List<Binding> selected, List<String> command, Inputs inputs,
                                 String loader, String temporary, String filesRoot,
                                 String nativeRoot, String environmentSha,
                                 Map<String, String> environment) throws IOException {
        bindings = Collections.unmodifiableList(new ArrayList<Binding>(selected));
        List<Binding> owned = new ArrayList<Binding>();
        for (Binding binding : selected) if (binding.kind == Kind.DIRECTORY) owned.add(binding);
        directories = Collections.unmodifiableList(owned);
        argv = Collections.unmodifiableList(new ArrayList<String>(command));
        processEnvironment = Collections.unmodifiableMap(new TreeMap<String, String>(environment));
        provenance = inputs.provenance; prootLoader = loader; prootTemporaryRoot = temporary;
        StringBuilder canonical = new StringBuilder(SCHEMA + "\n");
        field(canonical, "authority", "provenance_only");
        field(canonical, "native_registration_allowed", "false");
        field(canonical, "owner_root_metadata_verified", "false");
        field(canonical, "app_files_root", filesRoot); field(canonical, "installed_native_root", nativeRoot);
        field(canonical, "operation_id", provenance.operationId); field(canonical, "session_id", provenance.sessionId);
        field(canonical, "process_instance", provenance.processInstance);
        field(canonical, "declared_real_uid", Integer.toString(provenance.realUid));
        field(canonical, "guest_uid_gid", "1000:1000");
        field(canonical, "guest_binding_comparison", "exact_component_boundary");
        field(canonical, "initial_branch_label_comparison", "ASCII_case_insensitive_not_path_resolution");
        field(canonical, "runtime_manifest_sha256", provenance.runtimeManifestSha256);
        field(canonical, "native_consumer", "CityOfHeroes.exe");
        field(canonical, "native_consumer_sha256", provenance.nativeConsumerSha256);
        field(canonical, "native_consumer_bytes", Long.toString(provenance.nativeConsumerBytes));
        field(canonical, "helper_identity_sha256", provenance.helperIdentitySha256);
        for (Binding binding : bindings) {
            field(canonical, "bind_kind", binding.kind.name());
            field(canonical, "bind_guest", binding.guestPrefix); field(canonical, "bind_host", binding.hostRoot);
        }
        for (String argument : argv) field(canonical, "argv", argument);
        field(canonical, "PROOT_LOADER", loader); field(canonical, "PROOT_TMP_DIR", temporary);
        field(canonical, "PROOT_NO_SECCOMP", "1");
        // Bind all inherited helper environment bytes without exposing their
        // values through diagnostic provenance. The guest env -i is in argv.
        field(canonical, "finalized_process_environment_sha256", environmentSha);
        statement = canonical.toString(); statementSha = digest(statement.getBytes(StandardCharsets.UTF_8));
    }

    /** Call after every optional guest flag has been appended, before ProcessBuilder.start(). */
    public static ClientGuestNamespace fromFinalizedCommand(List<String> finalized,
            Map<String, String> processEnvironment, Inputs inputs) throws IOException {
        demand(finalized != null && processEnvironment != null && inputs != null,
                "Missing finalized launch");
        demand(finalized.size() > 0 && finalized.size() <= 160, "Finalized command exceeds bounds");
        List<String> command = new ArrayList<String>(finalized);
        for (String argument : command) scalar(argument);
        demand(processEnvironment.size() <= 256, "Finalized environment exceeds bounds");
        Map<String, String> environment = new TreeMap<String, String>(processEnvironment);
        // Only trusted, declared roots are canonicalized. Never canonicalize a
        // guest lookup or an arbitrary host path taken from an untrusted argv.
        File files = inputs.appFilesRoot;
        String canonicalFiles = files.getCanonicalPath(); hostLexical(canonicalFiles);
        demand(!canonicalFiles.equals("/") && !canonicalFiles.equals("/tmp")
                && !canonicalFiles.equals("/data") && !canonicalFiles.equals("/sdcard")
                && !within("/dev", canonicalFiles) && !within("/proc", canonicalFiles)
                && !within("/sys", canonicalFiles), "Nonprivate declared app root");
        String canonicalNative = inputs.nativeLibraryRoot.getCanonicalPath(); hostLexical(canonicalNative);
        File generation = new File(files, "m2/runtime-" + inputs.provenance.runtimeManifestSha256.substring(0, 16));
        File rootfs = new File(generation, "rootfs");
        File state = new File(files, "client/state");
        File report = new File(files, "client/reports/" + inputs.provenance.operationId);
        File temporary = new File(report, "tmp"), hosts = new File(report, "hosts");
        File sockets = new File(files, "s"), imported = new File(files, "client-import/" + inputs.importGeneration);
        File assets = new File(generation, "assets"), pg = new File(generation, "pg/opt/coh/pgsql");
        File wine = new File(generation, "wine"), passwd = new File(generation, "passwd"), group = new File(generation, "group");
        File prootTmp = new File(files, "p");
        String canonicalTmp = privateCanonical(prootTmp, canonicalFiles, files.getPath());
        String canonicalImported = privateCanonical(imported, canonicalFiles, files.getPath());
        String loader = new File(inputs.nativeLibraryRoot, "libproot-loader.so").getPath();
        String executable = new File(inputs.nativeLibraryRoot, "libproot.so").getPath();
        List<String> expected = new ArrayList<String>(Arrays.asList(executable,
            "--link2symlink", "--kill-on-exit", "--sysvipc", "-i", "1000:1000", "-r", rootfs.getPath(),
            "-b", "/dev", "-b", "/proc", "-b", "/sys",
            "-b", state.getPath() + ":/state", "-b", temporary.getPath() + ":/tmp",
            "-b", sockets.getPath() + ":/presentation-socket",
            "-b", canonicalImported + ":/game-import", "-b", assets.getPath() + ":/opt/coh",
            "-b", pg.getPath() + ":/opt/coh/pgsql", "-b", wine.getPath() + ":/opt/wine",
            "-b", passwd.getPath() + ":/etc/passwd", "-b", group.getPath() + ":/etc/group",
            "-b", hosts.getPath() + ":/etc/hosts", "-w", "/state", "/usr/bin/env", "-i",
            "HOME=/state", "USER=coh", "LOGNAME=coh", "PATH=/opt/coh/pgsql/bin:/usr/local/bin:/usr/bin:/bin",
            "LANG=C.UTF-8", "TZ=UTC", "TMPDIR=/tmp", "PYTHONUNBUFFERED=1", "PYTHONDONTWRITEBYTECODE=1",
            "COH_CLIENT_GRAPHICS_PROFILE=" + inputs.mode.graphics, "COH_CLIENT_GPU_PROFILE=" + inputs.mode.gpu,
            "/usr/bin/python3", "/opt/coh/" + (inputs.mode.reopen ? "character_reopen_diagnostic.py" : "character_creation_diagnostic.py"),
            "--state", "/state", "--assets", "/opt/coh", "--pg-bin", "/opt/coh/pgsql/bin",
            "--wine", "/opt/wine/bin/wine", "--wineserver", "/opt/wine/bin/wineserver",
            "--execution-platform", "android", "--session-id", inputs.provenance.sessionId,
            "--profile", "android-local-login", "--game-data", "/game-import/data", "--socket-dir", "/presentation-socket",
            "--startup-timeout-seconds", "900", "--observation-seconds", "30",
            "--interaction-seconds", "1200", "--timeout-seconds", "5400"));
        if (inputs.mode.resumeEmptyProfile) expected.add("--resume-empty-profile");
        if (inputs.mode.startupOnly) expected.add("--startup-only");
        if (inputs.mode.zoning) expected.add("--zoning");
        demand(command.equals(expected), "Command is not the exact finalized runCharacter namespace");
        demand(loader.equals(environment.get("PROOT_LOADER"))
                && canonicalTmp.equals(environment.get("PROOT_TMP_DIR"))
                && "1".equals(environment.get("PROOT_NO_SECCOMP")), "Finalized PRoot environment differs");
        StringBuilder environmentStatement = new StringBuilder("COH_PROCESS_ENVIRONMENT_V1\n");
        for (Map.Entry<String, String> entry : environment.entrySet()) {
            scalar(entry.getKey()); scalar(entry.getValue());
            demand(entry.getKey().matches("[A-Za-z_][A-Za-z0-9_]{0,127}"), "Invalid environment key");
            demand(!entry.getKey().startsWith("PROOT_") || entry.getKey().equals("PROOT_LOADER")
                    || entry.getKey().equals("PROOT_TMP_DIR") || entry.getKey().equals("PROOT_NO_SECCOMP"),
                    "Unknown PRoot environment override");
            demand(!entry.getKey().startsWith("USERLAND"), "USERLAND namespace is not admitted");
            field(environmentStatement, entry.getKey(), entry.getValue());
        }
        List<Binding> selected = new ArrayList<Binding>();
        selected.add(new Binding("/", privateCanonical(rootfs, canonicalFiles, files.getPath()), Kind.ROOTFS_DIAGNOSTIC));
        for (String passthrough : new String[]{"/dev", "/proc", "/sys"})
            selected.add(new Binding(passthrough, passthrough, Kind.PASSTHROUGH));
        File[] roots = {state, temporary, sockets, imported, assets, pg, wine, passwd, group, hosts};
        String[] guests = {"/state", "/tmp", "/presentation-socket", "/game-import", "/opt/coh", "/opt/coh/pgsql",
                           "/opt/wine", "/etc/passwd", "/etc/group", "/etc/hosts"};
        for (int index = 0; index < roots.length; index++)
            selected.add(new Binding(guests[index], privateCanonical(roots[index], canonicalFiles, files.getPath()),
                    index < 7 ? Kind.DIRECTORY : Kind.FILE));
        // No two independently bound private roots may collapse to one inode
        // spelling through an unproved host alias. Ancestor custody is still JNI's job.
        for (int i = 0; i < selected.size(); i++) for (int j = i + 1; j < selected.size(); j++) {
            Binding a = selected.get(i), b = selected.get(j);
            demand(!a.guestPrefix.equals(b.guestPrefix), "Duplicate guest binding");
            if (a.kind != Kind.PASSTHROUGH && b.kind != Kind.PASSTHROUGH)
                demand(!a.hostRoot.equals(b.hostRoot), "Aliased declared host bindings");
        }
        return new ClientGuestNamespace(selected, command, inputs, loader, canonicalTmp,
                                        canonicalFiles, canonicalNative,
                                        digest(environmentStatement.toString().getBytes(StandardCharsets.UTF_8)), environment);
    }

    public List<Binding> bindings() { return bindings; }
    /** Only these seven DIR routes may be considered by later held-FD admission. */
    public List<Binding> ownedDirectoryBindings() { return directories; }
    public List<String> finalizedArgv() { return argv; }
    /** Owner must launch these copied bytes, not mutate the original builder afterward. */
    public Map<String, String> finalizedEnvironment() { return processEnvironment; }
    public Provenance provenance() { return provenance; }
    public String canonicalStatement() { return statement; }
    public String sha256() { return statementSha; }
    public boolean nativeRegistrationAllowed() { return false; }
    public boolean rootMetadataVerified() { return false; }
    public String prootLoader() { return prootLoader; }
    public String prootTemporaryRoot() { return prootTemporaryRoot; }
    public byte[] operationWireIdentity() {
        byte[] bytes = new byte[16];
        for (int i = 0; i < bytes.length; i++)
            bytes[i] = (byte) Integer.parseInt(provenance.sessionId.substring(2 * i, 2 * i + 2), 16);
        return bytes;
    }

    /** Component-boundary longest binding; FILE/PASSTHROUGH results are diagnostic only. */
    public Route route(String guestAbsolute) throws IOException {
        guestLexical(guestAbsolute);
        Binding best = null;
        for (Binding binding : bindings)
            if (!binding.guestPrefix.equals("/") && within(binding.guestPrefix, guestAbsolute)
                    && (best == null || binding.guestPrefix.length() > best.guestPrefix.length())) best = binding;
        demand(best != null, "Unknown/rootfs guest lookup requires ordinary native fallback");
        String relative = guestAbsolute.equals(best.guestPrefix) ? "" : guestAbsolute.substring(best.guestPrefix.length() + 1);
        demand(best.kind != Kind.FILE || relative.isEmpty(), "Child of a file binding is not a directory");
        return new Route(best, guestAbsolute, relative);
    }

    /** Initial two-branch request shape only; it supplies no qualification or FD proof. */
    public Route initialCensusDirectory(String guestAbsolute, String guestDataRoot) throws IOException {
        guestLexical(guestDataRoot);
        demand(guestDataRoot.matches("/state/diagnostic/client-work-[0-9a-f]{24}/data"),
                "Unknown current client data view");
        Route result = route(guestAbsolute);
        demand(result.binding.kind == Kind.DIRECTORY && result.binding.guestPrefix.equals("/state")
                && within(guestDataRoot, guestAbsolute) && !guestAbsolute.equals(guestDataRoot),
                "Directory is outside the initial Game view");
        String remainder = guestAbsolute.substring(guestDataRoot.length() + 1);
        String branch = remainder.split("/", 2)[0];
        // Stock ParserLoadFiles asks for SCRIPTS.LOC. Only the two candidate
        // label comparisons fold ASCII; keep the exact request for held-FD
        // native case resolution and the separately qualified Wine recipe.
        demand(branch.equalsIgnoreCase("fx") || branch.equalsIgnoreCase("scripts.loc"),
                "Branch has no initial live recipe");
        return result;
    }

    private static boolean within(String root, String path) {
        return path.equals(root) || path.startsWith(root + "/");
    }
    private static String privateCanonical(File path, String fence, String declaredFence) throws IOException {
        hostLexical(path.getPath());
        String canonical = path.getCanonicalPath(); hostLexical(canonical);
        demand(within(fence, canonical) && !canonical.equals(fence), "Declared host root escapes app-private storage");
        demand(within(declaredFence, path.getPath())
                && canonical.equals(fence + path.getPath().substring(declaredFence.length())),
                "Declared host root has an unknown canonical alias");
        return canonical;
    }
    private static void hostLexical(String value) throws IOException { absolute(value, 4096); }
    private static void guestLexical(String value) throws IOException { absolute(value, 1024); }
    private static void absolute(String value, int maximum) throws IOException {
        scalar(value);
        demand(value.startsWith("/") && value.length() <= maximum && !value.equals("/")
                && !value.endsWith("/") && !value.contains("//") && value.indexOf('\\') < 0
                && value.indexOf(':') < 0, "Noncanonical absolute namespace path");
        for (String component : value.substring(1).split("/", -1))
            demand(!component.isEmpty() && component.length() <= 255
                    && !component.equals(".") && !component.equals("..")
                    && !component.endsWith(".") && !component.endsWith(" ")
                    && !component.toLowerCase(java.util.Locale.ROOT).contains(".l2s"),
                    "Dot escape or legacy link2symlink path requires native fallback");
    }
    private static void scalar(String value) throws IOException {
        demand(value != null && value.length() <= 4096, "Missing/oversized namespace field");
        for (int i = 0; i < value.length(); i++)
            demand(value.charAt(i) >= 32 && value.charAt(i) <= 126, "Unsupported namespace field bytes");
    }
    private static void sha(String value) throws IOException {
        demand(value != null && value.matches("[0-9a-f]{64}"), "Invalid source identity digest");
    }
    private static void field(StringBuilder output, String name, String value) {
        output.append(name).append(':').append(value.getBytes(StandardCharsets.UTF_8).length)
              .append(':').append(value).append('\n');
    }
    private static String digest(byte[] bytes) throws IOException {
        try {
            byte[] hash = MessageDigest.getInstance("SHA-256").digest(bytes);
            StringBuilder output = new StringBuilder(64);
            for (byte value : hash) output.append(String.format(java.util.Locale.ROOT, "%02x", value & 255));
            return output.toString();
        } catch (NoSuchAlgorithmException impossible) { throw new IOException("SHA-256 unavailable", impossible); }
    }
    private static void demand(boolean condition, String message) throws IOException {
        if (!condition) throw new IOException(message);
    }
}
