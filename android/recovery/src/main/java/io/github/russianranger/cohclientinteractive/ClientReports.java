package io.github.russianranger.cohclientinteractive;

import java.io.File;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.channels.Channels;
import java.nio.channels.FileChannel;
import java.nio.channels.SeekableByteChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.UUID;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/** Bounded private diagnostic preservation. Recovery records never confer a pass. */
public final class ClientReports {
    public static final long MAX_REPORT_BYTES = 512L * 1024 * 1024;
    public static final long MAX_EXPORT_MILLIS = 5L * 60 * 1000;
    /** Android supplies lstat identity because not every provider exposes unix attributes. */
    public interface IdentityReader { FileIdentity read(File file) throws IOException; }
    public static final class FileIdentity {
        public final long linkCount;
        public final String key;
        public FileIdentity(long linkCount, String key) { this.linkCount = linkCount; this.key = key; }
    }
    private static volatile IdentityReader identityReader;
    public static synchronized void setIdentityReader(IdentityReader reader) {
        if (reader == null) throw new IllegalArgumentException("Missing file identity reader");
        if (identityReader != null && identityReader != reader) throw new IllegalStateException("File identity reader already initialized");
        identityReader = reader;
    }
    private static final long MAX_GUEST_BYTES = 260L * 1024 * 1024;
    private static final long MAX_JSON_BYTES = 2L * 1024 * 1024;
    private static final int MAX_CHECKPOINT_BYTES = 256 * 1024;
    private static final int MAX_PNG_BYTES = 4 * 1024 * 1024;
    private static final long MAX_CAPTURE_BYTES = 64L * 1024 * 1024;
    private static final int MAX_CAPTURES = 128, MAX_DIRECTORY_ENTRIES = 2048;
    private static final String[] GUEST_FILES = {"latest-report.json", "report.zip", "character-logout.json",
            "interaction-finish.json", "character-relocation.json", "character-task-contact.json",
            "character-task-completion.json", "character-zoning-request.json", "character-zoning-delivery.json"};
    private static final String[] CAPTURE_DIRS = {"android-surface", "android-login", "android-connected",
            "android-relocated", "android-character", "android-interaction", "android-contact", "android-task", "android-zoning"};
    private static final byte[] PNG = {(byte)137,80,78,71,13,10,26,10};
    private ClientReports() {}

    /** Newest completed archives, including explicitly interrupted recovery archives. No pointer is needed. */
    public static synchronized List<File> reports(File filesRoot, int max) throws IOException {
        if (max < 0 || max > 50) throw new IOException("Invalid report inventory limit");
        List<Path> found = new ArrayList<>();
        Path root = reportRoot(filesRoot, false);
        if (root == null || max == 0) return new ArrayList<>();
        for (Path run : children(root)) {
            if (!runName(run.getFileName().toString()) || !directoryEntry(run)) continue;
            for (Path file : children(run)) {
                if (!archiveName(file.getFileName().toString())) continue;
                try { regular(file, MAX_REPORT_BYTES); found.add(file); }
                catch (IOException unsafe) { /* An unsafe archive is never offered for export. */ }
            }
        }
        Collections.sort(found, new Comparator<Path>() {
            @Override public int compare(Path a, Path b) {
                // The per-run timestamp is stable even after a recovery archive is assembled later.
                int value = b.getParent().getFileName().toString().compareTo(a.getParent().getFileName().toString());
                return value != 0 ? value : b.getFileName().toString().compareTo(a.getFileName().toString());
            }
        });
        List<File> result = new ArrayList<>();
        for (Path file : found) { if (result.size() == max) break; result.add(file.toFile()); }
        return result;
    }

    /** Fail closed: callers may retire guest outputs only after this returns successfully. */
    public static synchronized File preservePrevious(File filesRoot) throws IOException {
        Path files = directory(filesRoot.toPath());
        Path client = files.resolve("client");
        if (!Files.exists(client, LinkOption.NOFOLLOW_LINKS)) return null;
        directory(client);
        Path state = client.resolve("state");
        if (!Files.exists(state, LinkOption.NOFOLLOW_LINKS)) return null;
        directory(state);
        List<Path> sources = new ArrayList<>();
        for (String name : GUEST_FILES) {
            Path file = state.resolve(name);
            if (!Files.exists(file, LinkOption.NOFOLLOW_LINKS)) continue;
            regular(file, name.equals("report.zip") ? MAX_GUEST_BYTES : MAX_JSON_BYTES);
            sources.add(file);
        }
        if (sources.isEmpty()) return null;
        Path root = reportRoot(filesRoot, true);
        String fingerprint=guestFingerprint(sources);
        Path marker=root.resolve("previous-guest-preservation.txt");
        if(Files.exists(marker,LinkOption.NOFOLLOW_LINKS)) {
            regular(marker,4096);java.io.ByteArrayOutputStream saved=new java.io.ByteArrayOutputStream();copy(marker,saved,4096);
            String[] receipt=new String(saved.toByteArray(),StandardCharsets.UTF_8).split("\n");
            if(receipt.length==4 && "1".equals(receipt[0]) && fingerprint.equals(receipt[1])) {
                String[] relative=receipt[2].split("/");
                if(relative.length==2&&runName(relative[0])&&archiveName(relative[1])) {
                    Path previous=root.resolve(relative[0]).resolve(relative[1]);
                    if(Files.exists(previous,LinkOption.NOFOLLOW_LINKS)&&receipt[3].equals(fileDigest(previous,MAX_REPORT_BYTES)))return previous.toFile();
                }
            }
        }
        long sourceUtc=0;for(Path source:sources)sourceUtc=Math.max(sourceUtc,Files.getLastModifiedTime(source,LinkOption.NOFOLLOW_LINKS).toMillis());
        sourceUtc=Math.max(1000000000L,Math.min(System.currentTimeMillis(),sourceUtc));
        Path run = root.resolve(sourceUtc + "-" + UUID.randomUUID().toString().replace("-", "").substring(0,12));
        Files.createDirectory(run);
        Path target = run.resolve("coh-interrupted-guest-" + run.getFileName() + ".zip");
        archive(target, sources, state, null, "previous_guest_outputs", false);
        if(!fingerprint.equals(guestFingerprint(sources)))throw new IOException("Previous guest evidence changed during preservation");
        String receipt="1\n"+fingerprint+"\n"+root.relativize(target).toString().replace(File.separatorChar,'/')+"\n"+fileDigest(target,MAX_REPORT_BYTES)+"\n";
        atomicBytes(marker,receipt.getBytes(StandardCharsets.UTF_8));
        return target.toFile();
    }

    /** Call before creating a new operation, while no runtime operation owns these directories.
     * An unsafe/incomplete source throws before startup; callers must retain the guest outputs.
     */
    public static synchronized void recoverAll(File filesRoot) throws IOException {
        Path root = reportRoot(filesRoot, false);
        if (root == null) return;
        for (Path run : children(root)) {
            if (!runName(run.getFileName().toString()) || !directoryEntry(run)) continue;
            Path checkpoint = run.resolve("checkpoint.json");
            if (!Files.exists(checkpoint, LinkOption.NOFOLLOW_LINKS)) continue;
            boolean completed = false;
            for (Path file : children(run)) {
                if (!archiveName(file.getFileName().toString())) continue;
                try { regular(file, MAX_REPORT_BYTES); completed = true; break; }
                catch (IOException unsafe) { /* Do not follow unsafe purported reports. */ }
            }
            if (completed) continue;
            regular(checkpoint, MAX_CHECKPOINT_BYTES);
            Path target = run.resolve("coh-interrupted-" + run.getFileName() + ".zip");
            archive(target, captures(run), run, checkpoint, "interrupted_android_operation", true);
        }
    }

    /** Replace a compact checkpoint atomically; JSON is supplied by the Android runtime. */
    public static synchronized void checkpoint(File operationDir, byte[] json) throws IOException {
        if (json == null || json.length == 0 || json.length > MAX_CHECKPOINT_BYTES)
            throw new IOException("Recovery checkpoint exceeds limit");
        Path run = operationDirectory(operationDir);
        atomicBytes(run.resolve("checkpoint.json"), json);
    }

    /** A fixed capture namespace prevents arbitrary app files from entering a recovery report. */
    public static synchronized void png(File operationDir, String relative, byte[] bytes) throws IOException {
        if (!captureName(relative) || bytes == null || bytes.length < PNG.length || bytes.length > MAX_PNG_BYTES)
            throw new IOException("Invalid recovery capture");
        for (int i = 0; i < PNG.length; i++) if (bytes[i] != PNG[i]) throw new IOException("Recovery capture is not PNG");
        Path run = operationDirectory(operationDir);
        List<Path> existing = captures(run);
        Path target = run.resolve(relative);
        long total = bytes.length;
        int count = 1;
        for (Path file : existing) if (!file.equals(target)) { total += regular(file, MAX_PNG_BYTES).size(); count++; }
        if (total > MAX_CAPTURE_BYTES || count > MAX_CAPTURES) throw new IOException("Recovery capture inventory exceeds limit");
        ensureDirectory(target.getParent());
        atomicBytes(target, bytes);
    }

    /** Stream a selected private report into an already opened SAF output; caller owns the stream. */
    public static long export(File filesRoot, File report, OutputStream destination) throws IOException {
        if (destination == null || report == null) throw new IOException("Report export is unavailable");
        Path root = reportRoot(filesRoot, false);
        Path file = report.toPath().toAbsolutePath().normalize();
        if (root == null || file.getParent() == null || !root.equals(file.getParent().getParent())
                || !runName(file.getParent().getFileName().toString()) || !archiveName(file.getFileName().toString()))
            throw new IOException("Selected report is outside private report storage");
        long copied = copy(file, destination, MAX_REPORT_BYTES);
        destination.flush();
        return copied;
    }

    private static String guestFingerprint(List<Path> sources) throws IOException {
        StringBuilder content=new StringBuilder();
        for(Path file:sources)content.append(file.getFileName()).append(':').append(fileDigest(file,file.getFileName().toString().equals("report.zip")?MAX_GUEST_BYTES:MAX_JSON_BYTES)).append('\n');
        return digestBytes(content.toString().getBytes(StandardCharsets.UTF_8));
    }
    private static String fileDigest(Path file,long max) throws IOException {
        try {
            java.security.MessageDigest digest=java.security.MessageDigest.getInstance("SHA-256");
            OutputStream sink=new java.security.DigestOutputStream(new OutputStream(){@Override public void write(int b){}@Override public void write(byte[] b,int o,int n){}},digest);
            copy(file,sink,max);return digestHex(digest.digest());
        }catch(java.security.NoSuchAlgorithmException impossible){throw new IOException("SHA-256 unavailable",impossible);}
    }
    private static String digestBytes(byte[] bytes) throws IOException {
        try{return digestHex(java.security.MessageDigest.getInstance("SHA-256").digest(bytes));}
        catch(java.security.NoSuchAlgorithmException impossible){throw new IOException("SHA-256 unavailable",impossible);}
    }
    private static String digestHex(byte[] bytes){StringBuilder result=new StringBuilder();for(byte value:bytes)result.append(String.format(java.util.Locale.ROOT,"%02x",value&255));return result.toString();}

    private static boolean runName(String name) { return name.matches("[0-9]{10,17}-[0-9a-f]{12}"); }
    private static boolean archiveName(String name) {
        return name.matches("coh-(?:character-(?:creation|reopen)|interrupted(?:-guest)?)-[0-9]{10,17}-[0-9a-f]{12}\\.zip");
    }
    private static boolean captureName(String value) {
        if (value == null || !value.matches("android-(?:surface|login|connected|relocated|character|interaction|contact|task|zoning)/(?:accepted-|completed-)?capture-[1-9][0-9]{0,2}\\.png")) return false;
        if ((value.contains("/accepted-") || value.contains("/completed-")) && !value.startsWith("android-task/")) return false;
        int dash = value.lastIndexOf('-'), dot = value.lastIndexOf('.');
        return Integer.parseInt(value.substring(dash + 1, dot)) <= 256;
    }
    private static Path operationDirectory(File operationDir) throws IOException {
        Path run = directory(operationDir.toPath());
        if (!runName(run.getFileName().toString()) || run.getParent() == null
                || !"reports".equals(run.getParent().getFileName().toString())
                || run.getParent().getParent() == null || !"client".equals(run.getParent().getParent().getFileName().toString()))
            throw new IOException("Invalid recovery operation directory");
        return run;
    }
    private static Path reportRoot(File filesRoot, boolean create) throws IOException {
        Path files = directory(filesRoot.toPath());
        Path client = files.resolve("client"), reports = client.resolve("reports");
        if (create) { ensureDirectory(client); ensureDirectory(reports); }
        else if (!Files.exists(reports, LinkOption.NOFOLLOW_LINKS)) {
            if (Files.exists(client, LinkOption.NOFOLLOW_LINKS)) directory(client);
            return null;
        }
        return directory(reports);
    }
    private static void ensureDirectory(Path path) throws IOException {
        directory(path.getParent());
        if (!Files.exists(path, LinkOption.NOFOLLOW_LINKS)) Files.createDirectory(path);
        directory(path);
    }
    private static Path directory(Path source) throws IOException {
        Path path = source.toAbsolutePath().normalize();
        Path current = path.getRoot();
        for (Path component : path) {
            current = current.resolve(component);
            BasicFileAttributes info = Files.readAttributes(current, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
            if (!info.isDirectory() || info.isSymbolicLink()) throw new IOException("Unsafe diagnostic directory");
        }
        return path;
    }
    private static boolean directoryEntry(Path path) throws IOException {
        BasicFileAttributes info = Files.readAttributes(path, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
        return info.isDirectory() && !info.isSymbolicLink();
    }
    private static List<Path> children(Path path) throws IOException {
        directory(path);
        List<Path> list = new ArrayList<>();
        try (DirectoryStream<Path> entries = Files.newDirectoryStream(path)) {
            for (Path entry : entries) {
                if (list.size() >= MAX_DIRECTORY_ENTRIES) throw new IOException("Diagnostic inventory exceeds limit");
                list.add(entry);
            }
        }
        return list;
    }
    private static BasicFileAttributes regular(Path file, long max) throws IOException {
        directory(file.getParent());
        BasicFileAttributes info = Files.readAttributes(file, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
        if (!info.isRegularFile() || info.isSymbolicLink() || info.size() < 0 || info.size() > max)
            throw new IOException("Unsafe or oversized diagnostic file");
        identity(file);
        return info;
    }
    private static FileIdentity identity(Path file) throws IOException {
        FileIdentity value;
        IdentityReader reader = identityReader;
        if (reader != null) value = reader.read(file.toFile());
        else try {
            Object links = Files.getAttribute(file, "unix:nlink", LinkOption.NOFOLLOW_LINKS);
            Object device = Files.getAttribute(file, "unix:dev", LinkOption.NOFOLLOW_LINKS);
            Object inode = Files.getAttribute(file, "unix:ino", LinkOption.NOFOLLOW_LINKS);
            if (!(device instanceof Number) || !(inode instanceof Number)) throw new IOException("Diagnostic file identity is unavailable");
            value = new FileIdentity(links instanceof Number ? ((Number)links).longValue() : -1, device + ":" + inode);
        } catch (UnsupportedOperationException | IllegalArgumentException unsupported) {
            throw new IOException("Diagnostic file identity provider is unavailable", unsupported);
        }
        if (value == null || value.linkCount != 1 || value.key == null || value.key.length() == 0)
            throw new IOException("Diagnostic file identity or link count is unsafe");
        return value;
    }
    private static List<Path> captures(Path run) throws IOException {
        List<Path> found = new ArrayList<>(); long total = 0;
        for (String name : CAPTURE_DIRS) {
            Path dir = run.resolve(name);
            if (!Files.exists(dir, LinkOption.NOFOLLOW_LINKS)) continue;
            directory(dir);
            for (Path file : children(dir)) {
                String relative = name + "/" + file.getFileName();
                if (!captureName(relative)) continue;
                total += regular(file, MAX_PNG_BYTES).size();
                found.add(file);
                if (found.size() > MAX_CAPTURES || total > MAX_CAPTURE_BYTES) throw new IOException("Recovery capture inventory exceeds limit");
            }
        }
        return found;
    }
    private static void same(BasicFileAttributes before, BasicFileAttributes after) throws IOException {
        if (before.size() != after.size() || !before.lastModifiedTime().equals(after.lastModifiedTime())
                || before.fileKey() != null && !before.fileKey().equals(after.fileKey()))
            throw new IOException("Diagnostic evidence changed during copy");
    }
    private static long copy(Path file, OutputStream out, long max) throws IOException {
        if (Thread.currentThread().isInterrupted()) throw new IOException("Diagnostic export was cancelled");
        BasicFileAttributes before = regular(file, max);
        FileIdentity identityBefore = identity(file);
        long deadline = System.nanoTime() + MAX_EXPORT_MILLIS * 1000000L;
        long copied = 0;
        try (SeekableByteChannel channel = Files.newByteChannel(file, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS)) {
            same(before, regular(file, max));
            if (!identityBefore.key.equals(identity(file).key)) throw new IOException("Diagnostic file was replaced");
            ByteBuffer data = ByteBuffer.allocate(65536);
            for (int count; (count = channel.read(data)) != -1;) {
                if (System.nanoTime() >= deadline || Thread.currentThread().isInterrupted()) throw new IOException("Diagnostic export timed out or was cancelled");
                if (count == 0) continue;
                copied += count;
                if (copied > max || copied > before.size()) throw new IOException("Diagnostic evidence grew during copy");
                out.write(data.array(), 0, count); data.clear();
                if (System.nanoTime() >= deadline || Thread.currentThread().isInterrupted()) throw new IOException("Diagnostic export timed out or was cancelled");
            }
        }
        same(before, regular(file, max));
        if (!identityBefore.key.equals(identity(file).key)) throw new IOException("Diagnostic file was replaced");
        if (copied != before.size()) throw new IOException("Diagnostic evidence truncated during copy");
        return copied;
    }
    private static void atomicBytes(Path target, byte[] bytes) throws IOException {
        directory(target.getParent());
        if (Files.exists(target, LinkOption.NOFOLLOW_LINKS)) regular(target, Math.max(MAX_CHECKPOINT_BYTES, MAX_PNG_BYTES));
        Path part = target.resolveSibling("." + target.getFileName() + "." + UUID.randomUUID() + ".part");
        try {
            try (FileChannel out = FileChannel.open(part, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS)) {
                ByteBuffer buffer = ByteBuffer.wrap(bytes);
                while (buffer.hasRemaining()) out.write(buffer);
                out.force(true);
            }
            directory(target.getParent()); regular(part, bytes.length);
            if (Files.exists(target, LinkOption.NOFOLLOW_LINKS)) regular(target, Math.max(MAX_CHECKPOINT_BYTES, MAX_PNG_BYTES));
            Files.move(part, target, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            regular(target, bytes.length);
        } finally { Files.deleteIfExists(part); }
    }
    private static void archive(Path target, List<Path> sources, Path base, Path checkpoint,
                                String kind, boolean androidCheckpoint) throws IOException {
        directory(target.getParent());
        if (Files.exists(target, LinkOption.NOFOLLOW_LINKS)) throw new IOException("Recovery report already exists");
        Path part = target.resolveSibling("." + target.getFileName() + "." + UUID.randomUUID() + ".part");
        try {
            try (FileChannel channel = FileChannel.open(part, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS)) {
                try (ZipOutputStream zip = new ZipOutputStream(Channels.newOutputStream(channel))) {
                String manifest = "{\"format\":1,\"status\":\"interrupted_unverified\",\"passed\":false,\"verified\":false,"
                        + "\"recovery_kind\":\"" + kind + "\",\"session_attribution_verified\":false,"
                        + "\"note\":\"Preserved diagnostic evidence only. No successful Finish, character save, or zoning qualification is inferred.\"}";
                zip.putNextEntry(new ZipEntry("recovery-manifest.json")); zip.write(manifest.getBytes(StandardCharsets.UTF_8)); zip.closeEntry();
                if (checkpoint != null) {
                    zip.putNextEntry(new ZipEntry("android-recovery-checkpoint.json")); copy(checkpoint, zip, MAX_CHECKPOINT_BYTES); zip.closeEntry();
                }
                for (Path source : sources) {
                    String name = base.relativize(source).toString().replace(File.separatorChar, '/');
                    zip.putNextEntry(new ZipEntry(androidCheckpoint ? name : "previous-guest/" + name));
                    copy(source, zip, androidCheckpoint ? MAX_PNG_BYTES : name.equals("report.zip") ? MAX_GUEST_BYTES : MAX_JSON_BYTES);
                    zip.closeEntry();
                }
                zip.finish(); zip.flush(); channel.force(true);
                }
            }
            regular(part, MAX_REPORT_BYTES); directory(target.getParent());
            if (Files.exists(target, LinkOption.NOFOLLOW_LINKS)) throw new IOException("Recovery report appeared during publication");
            Files.move(part, target, StandardCopyOption.ATOMIC_MOVE);
            regular(target, MAX_REPORT_BYTES);
        } finally { Files.deleteIfExists(part); }
    }
}
