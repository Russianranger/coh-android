package io.github.russianranger.cohatlas;

import java.io.*;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.*;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/** Imports only the content pinned by this APK, without Android dependencies.
 * The old generation remains active until a completely verified new generation
 * is published with one atomic pointer replacement. No archive supplies links.
 */
public final class AtlasAssetImporter {
    public interface Assets { InputStream open(String name) throws IOException; }
    public interface Progress {
        void update(String phase, long filesDone, long totalFiles, long bytesDone, long totalBytes);
    }
    interface Space { long usable(File directory); }
    public static final class CancelledException extends IOException {
        public CancelledException() { super("Asset import stopped; the previous verified content is preserved"); }
    }
    /** Stop acceptance and the final pointer replacement use the same monitor. */
    public static final class Control {
        private boolean cancelled, committed;
        public synchronized boolean requestCancel() {
            if (committed) return false;
            cancelled = true;
            return true;
        }
        public synchronized boolean isCancelled() { return cancelled; }
        public synchronized boolean isCommitted() { return committed; }
        private synchronized void publish(Path pointer, Path target) throws IOException {
            check(this);
            Files.move(pointer, target, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            committed = true;
        }
    }
    public static final class Summary {
        public final String generation, sourceCommit, dataCommit, repositoryCommit;
        public final long count, bytes;
        public final File dataDirectory;
        private Summary(String generation, Contract contract, File base) {
            this.generation = generation;
            sourceCommit = contract.source;
            dataCommit = contract.data;
            repositoryCommit = contract.repository;
            count = contract.totalCount;
            bytes = contract.totalBytes;
            dataDirectory = new File(new File(base, generation), "data");
        }
    }
    private static final long MAX_BYTES = 32L * 1024 * 1024 * 1024;
    private static final int MAX_INDEX = 128 * 1024 * 1024, MAX_PATH = 4096;
    private static final String GENERATION = "generation-[0-9a-f]{32}";
    private static final String PARTIAL = "\\.import-[0-9a-f]{32}";
    private final File base;
    private final Assets assets;
    private final Contract contract;
    private final Space space;

    public AtlasAssetImporter(File privateBase, Assets assets) throws IOException {
        this(privateBase, assets, new Space() {
            public long usable(File directory) { return directory.getUsableSpace(); }
        });
    }
    AtlasAssetImporter(File privateBase, Assets assets, Space space) throws IOException {
        this.base = privateBase.getAbsoluteFile();
        this.assets = Objects.requireNonNull(assets);
        this.space = Objects.requireNonNull(space);
        noLinks(base.toPath());
        Files.createDirectories(base.toPath());
        if (!Files.isDirectory(base.toPath(), LinkOption.NOFOLLOW_LINKS))
            throw new IOException("The content directory is not a private directory");
        byte[] properties;
        try (InputStream in = assets.open("atlas-import.properties")) { properties = bounded(in, 16384); }
        this.contract = new Contract(properties);
    }

    /** Reads a receipt of a completed import, not a full inventory re-scan. */
    public Summary inspect() throws IOException {
        try (WriterLock ignored = lock()) { return inspectUnlocked(); }
    }
    private Summary inspectUnlocked() throws IOException {
        Path pointer = base.toPath().resolve("active.properties");
        if (!Files.exists(pointer, LinkOption.NOFOLLOW_LINKS)) return null;
        Properties p = readProperties(pointer, 4096);
        String generation = activeGeneration();
        Path dir = base.toPath().resolve(generation);
        noLinks(dir);
        Properties receipt = readProperties(dir.resolve("complete.properties"), 4096);
        for (String name : new String[]{"generation", "contract.sha256", "count", "bytes"}) {
            if (!Objects.equals(p.getProperty(name), receipt.getProperty(name)))
                throw new IOException("The active content receipt does not match its pointer");
        }
        if (!contract.digest.equals(receipt.getProperty("contract.sha256"))
                || !Long.toString(contract.totalCount).equals(receipt.getProperty("count"))
                || !Long.toString(contract.totalBytes).equals(receipt.getProperty("bytes")))
            throw new IOException("The installed content belongs to a different APK content contract");
        Path data = dir.resolve("data");
        if (!Files.isDirectory(data, LinkOption.NOFOLLOW_LINKS))
            throw new IOException("The active content directory is missing");
        noLinks(data);
        return new Summary(generation, contract, base);
    }

    /** Potentially disk-heavy; run in the foreground import operation. */
    public void recover() throws IOException {
        try (WriterLock ignored = lock()) { recoverUnlocked(null, new Control()); }
    }
    private void recoverUnlocked(Progress progress, Control control) throws IOException {
        // Validate the pointer before deleting anything. An invalid pointer is a
        // recoverable error for the owner, never permission to delete content.
        String active = activeGeneration();
        update(progress, "Recovering interrupted import", 0, 0, 0, 0);
        try (DirectoryStream<Path> entries = Files.newDirectoryStream(base.toPath())) {
            for (Path entry : entries) {
                check(control);
                String name = entry.getFileName().toString();
                if (name.matches(PARTIAL) || name.matches("\\.pointer-[0-9a-f]{32}\\.tmp")
                        || (name.matches(GENERATION) && !name.equals(active)))
                    remove(entry, control);
            }
        }
    }
    private String activeGeneration() throws IOException {
        Path pointer = base.toPath().resolve("active.properties");
        if (!Files.exists(pointer, LinkOption.NOFOLLOW_LINKS)) return null;
        String generation = readProperties(pointer, 4096).getProperty("generation", "");
        if (!generation.matches(GENERATION)) throw new IOException("Invalid active content pointer");
        // Recovery only needs a safe ownership reference. A different APK's
        // receipt, or damaged files, must not prevent importing a replacement.
        return generation;
    }

    public Summary importArchive(InputStream selected, Progress progress, Control control) throws IOException {
        Objects.requireNonNull(selected);
        Objects.requireNonNull(control);
        Path staging = null, generation = null, pointer = null;
        Summary published = null;
        try (OwnedInput input = new OwnedInput(selected); WriterLock ignored = lock()) {
            check(control);
            if (control.isCommitted()) throw new IOException("An import control cannot be reused after publication");
            recoverUnlocked(progress, control);
            long required = add(add(contract.assetArchiveBytes, contract.textArchiveBytes),
                    add(add(contract.totalBytes, multiply(contract.totalCount, contract.perFile)),
                            add(contract.reserve, add(contract.assetIndexBytes, contract.textIndexBytes))));
            if (space.usable(base) < required)
                throw new IOException("Not enough internal storage: need " + required + " free bytes for a safe import");
            String id = UUID.randomUUID().toString().replace("-", "");
            staging = base.toPath().resolve(".import-" + id);
            Files.createDirectory(staging);
            Path userZip = staging.resolve("selected.zip"), textZip = staging.resolve("text.zip");
            copyChecked(input, userZip, contract.assetArchiveBytes, contract.assetArchiveHash,
                    "Checking selected asset archive", progress, control);
            // Release the document provider before lengthy private extraction,
            // and never run provider cleanup after atomic publication.
            input.close();
            try (InputStream in = assets.open("atlas-text.zip")) {
                copyChecked(in, textZip, contract.textArchiveBytes, contract.textArchiveHash,
                        "Checking bundled game definitions", progress, control);
            }
            Path assetIndex = staging.resolve("assets.tsv"), textIndex = staging.resolve("text.tsv");
            try (InputStream in = assets.open("atlas-assets-index.tsv")) {
                copyChecked(in, assetIndex, contract.assetIndexBytes, contract.assetIndexHash,
                        "Checking asset inventory", progress, control);
            }
            try (InputStream in = assets.open("atlas-text-index.tsv")) {
                copyChecked(in, textIndex, contract.textIndexBytes, contract.textIndexHash,
                        "Checking game-definition inventory", progress, control);
            }
            validateCentral(userZip, assetIndex, true, control);
            validateCentral(textZip, textIndex, false, control);
            long[] totals = new long[2];
            Map<String, String> directories = new HashMap<>();
            // Match prepare_runtime.FilePlan: text establishes directory case,
            // then lowercase asset paths reuse the first canonical directories.
            extract(textZip, textIndex, staging, false, totals, directories, progress, control);
            Files.delete(textZip);
            extract(userZip, assetIndex, staging, true, totals, directories, progress, control);
            Files.delete(userZip);
            Files.delete(assetIndex);
            Files.delete(textIndex);
            if (totals[0] != contract.totalCount || totals[1] != contract.totalBytes)
                throw new IOException("The complete content inventory does not match this APK");
            check(control);
            String name = "generation-" + id;
            byte[] receipt = ("generation=" + name + "\ncontract.sha256=" + contract.digest
                    + "\ncount=" + contract.totalCount + "\nbytes=" + contract.totalBytes + "\n")
                    .getBytes(StandardCharsets.US_ASCII);
            writeSynced(staging.resolve("complete.properties"), receipt);
            generation = base.toPath().resolve(name);
            Files.move(staging, generation, StandardCopyOption.ATOMIC_MOVE);
            staging = null;
            pointer = base.toPath().resolve(".pointer-" + id + ".tmp");
            writeSynced(pointer, receipt);
            update(progress, "Publishing verified content", totals[0], contract.totalCount, totals[1], contract.totalBytes);
            control.publish(pointer, base.toPath().resolve("active.properties"));
            pointer = null;
            // No fallible operation after commit may turn a successful import
            // into a failure report. Old generations are reclaimed next import.
            published = new Summary(name, contract, base);
            return published;
        } catch (IOException e) {
            if (control.isCommitted() && published != null) return published;
            if (control.isCancelled() || Thread.currentThread().isInterrupted()) throw new CancelledException();
            throw e;
        } finally {
            // Cancellation cleanup ignores the cancelled token. If the process
            // dies during cleanup, the next explicit import recovers this path.
            if (!control.isCommitted()) {
                quietRemove(pointer);
                quietRemove(staging);
                quietRemove(generation);
            }
        }
    }
    private static final class OwnedInput extends FilterInputStream {
        private boolean closed;
        OwnedInput(InputStream input) { super(input); }
        @Override public void close() throws IOException {
            if (closed) return;
            closed = true;
            super.close();
        }
    }

    private void copyChecked(InputStream in, Path output, long size, String hash, String phase,
                             Progress progress, Control control) throws IOException {
        MessageDigest digest = digest();
        long done = 0;
        byte[] buffer = new byte[256 * 1024];
        update(progress, phase, 0, 0, 0, size);
        try (FileOutputStream out = new FileOutputStream(output.toFile())) {
            while (done < size) {
                check(control);
                int n = in.read(buffer, 0, (int)Math.min(buffer.length, size - done));
                if (n < 0) throw new IOException("Truncated " + phase.toLowerCase(Locale.ROOT));
                if (n == 0) continue;
                out.write(buffer, 0, n);
                digest.update(buffer, 0, n);
                done += n;
                update(progress, phase, 0, 0, done, size);
            }
            check(control);
            if (in.read() != -1) throw new IOException("Archive or inventory is larger than the pinned version");
            if (!hex(digest.digest()).equals(hash)) throw new IOException("Content checksum mismatch during " + phase.toLowerCase(Locale.ROOT));
            out.getFD().sync();
        }
    }

    private void extract(Path archive, Path index, Path staging, boolean asset, long[] totals, Map<String, String> directories,
                         Progress progress, Control control) throws IOException {
        long count = 0, bytes = 0;
        String previous = "";
        byte[] buffer = new byte[128 * 1024];
        try (ZipInputStream zip = new ZipInputStream(new BufferedInputStream(Files.newInputStream(archive), 256 * 1024));
             IndexReader expected = new IndexReader(index)) {
            if (asset) {
                ZipEntry manifest = zip.getNextEntry();
                if (manifest == null || !manifest.getName().equals("asset-manifest.json") || manifest.isDirectory())
                    throw new IOException("The asset manifest must be the first archive entry");
                checkEntryBytes(zip, null, contract.manifestBytes, contract.manifestHash, control, buffer);
                zip.closeEntry();
            }
            IndexEntry record;
            while ((record = expected.next()) != null) {
                check(control);
                checkName(record.name, asset ? "assets/" : "data/");
                if (record.name.compareTo(previous) <= 0) throw new IOException("The inventory contains duplicate or unsorted paths");
                previous = record.name;
                ZipEntry entry = zip.getNextEntry();
                if (entry == null || entry.isDirectory() || !entry.getName().equals(record.name))
                    throw new IOException("Archive entries do not match the exact pinned inventory");
                String relative = asset ? "data/" + record.name.substring(7) : record.name;
                relative = canonicalPath(relative, directories);
                Path target = staging.resolve(relative);
                noLinks(target.getParent());
                Files.createDirectories(target.getParent());
                if (space.usable(base) < add(record.bytes, contract.reserve))
                    throw new IOException("Internal storage filled during content extraction");
                try (OutputStream out = Files.newOutputStream(target, StandardOpenOption.CREATE_NEW,
                        StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS)) {
                    checkEntryBytes(zip, out, record.bytes, record.hash, control, buffer);
                }
                zip.closeEntry();
                count++;
                bytes = add(bytes, record.bytes);
                totals[0]++;
                totals[1] = add(totals[1], record.bytes);
                if (totals[0] > contract.totalCount || totals[1] > contract.totalBytes)
                    throw new IOException("Extracted content exceeds the pinned inventory");
                update(progress, "Installing verified content", totals[0], contract.totalCount, totals[1], contract.totalBytes);
            }
            if (zip.getNextEntry() != null) throw new IOException("Unexpected extra archive entry");
        }
        if (count != (asset ? contract.assetCount : contract.textCount)
                || bytes != (asset ? contract.assetBytes : contract.textBytes))
            throw new IOException("Archive count or extracted byte total does not match the pinned inventory");
    }

    private static String canonicalPath(String relative, Map<String, String> directories) throws IOException {
        String[] parts = relative.split("/");
        String directory = "";
        for (int i = 0; i < parts.length - 1; i++) {
            String proposed = directory.isEmpty() ? parts[i] : directory + "/" + parts[i];
            String key = proposed.toLowerCase(Locale.ROOT);
            String existing = directories.get(key);
            if (existing == null) { directories.put(key, proposed); directory = proposed; }
            else directory = existing;
        }
        return directory + "/" + parts[parts.length - 1];
    }

    private static void checkEntryBytes(InputStream in, OutputStream out, long size, String hash,
                                        Control control, byte[] buffer) throws IOException {
        MessageDigest digest = digest();
        long done = 0;
        while (done < size) {
            check(control);
            int n = in.read(buffer, 0, (int)Math.min(buffer.length, size - done));
            if (n < 0) throw new IOException("Archive entry is shorter than its pinned size");
            if (n == 0) continue;
            digest.update(buffer, 0, n);
            if (out != null) out.write(buffer, 0, n);
            done += n;
        }
        check(control);
        if (in.read() != -1) throw new IOException("Archive entry is larger than its pinned size");
        if (!hex(digest.digest()).equals(hash)) throw new IOException("Extracted file checksum mismatch");
    }

    /** Validate central metadata too: ZipInputStream alone hides Unix links,
     * central/local mismatches, and an incomplete central directory. ZIP64 is
     * required by the shipped text archive's greater-than-65535 entry count.
     */
    private void validateCentral(Path archive, Path index, boolean asset, Control control) throws IOException {
        try (RandomAccessFile in = new RandomAccessFile(archive.toFile(), "r"); IndexReader expected = new IndexReader(index)) {
            long end = findEnd(in), length = in.length();
            in.seek(end + 4);
            if (u16(in) != 0 || u16(in) != 0) throw new IOException("Multi-disk ZIP is unsupported");
            long diskCount = u16(in), count = u16(in), size = u32(in), offset = u32(in);
            int comment = u16(in);
            if (end + 22 + comment != length || diskCount != count) throw new IOException("Invalid ZIP terminator");
            long centralEnd = end;
            if (count == 65535 || size == 0xffffffffL || offset == 0xffffffffL) {
                if (end < 20) throw new IOException("Missing ZIP64 locator");
                in.seek(end - 20);
                if (u32(in) != 0x07064b50L || u32(in) != 0) throw new IOException("Invalid ZIP64 locator");
                long zip64 = u64(in);
                if (u32(in) != 1 || zip64 < 0 || zip64 > end - 76) throw new IOException("Invalid ZIP64 end offset");
                in.seek(zip64);
                if (u32(in) != 0x06064b50L) throw new IOException("Missing ZIP64 end");
                long endSize = u64(in);
                if (endSize < 44 || add(zip64, add(12, endSize)) != end - 20) throw new IOException("Invalid ZIP64 end size");
                u16(in); u16(in);
                if (u32(in) != 0 || u32(in) != 0) throw new IOException("Multi-disk ZIP64 is unsupported");
                diskCount = u64(in); count = u64(in); size = u64(in); offset = u64(in);
                if (diskCount != count) throw new IOException("Invalid ZIP64 entry count");
                centralEnd = zip64;
            }
            long wanted = (asset ? contract.assetCount + 1 : contract.textCount);
            if (count != wanted || count > 400001 || offset < 0 || size < 0 || add(offset, size) != centralEnd)
                throw new IOException("ZIP central directory does not match the pinned inventory");
            in.seek(offset);
            String previous = "";
            byte[] header = new byte[46];
            for (long i = 0; i < count; i++) {
                check(control);
                in.readFully(header);
                if (le32(header, 0) != 0x02014b50L) throw new IOException("Invalid ZIP central entry");
                int madeBy = le16(header, 4), flags = le16(header, 8), method = le16(header, 10);
                long compressed = le32(header, 20), uncompressed = le32(header, 24);
                int nameLength = le16(header, 28), extraLength = le16(header, 30), commentLength = le16(header, 32), disk = le16(header, 34);
                long attributes = le32(header, 38), localOffset = le32(header, 42);
                if ((flags & 1) != 0 || (method != 0 && method != 8) || disk != 0
                        || nameLength == 0 || nameLength > MAX_PATH)
                    throw new IOException("Unsupported ZIP entry metadata");
                // Both the selected archive and bundled archive are built as
                // regular Unix files. Other types, including links, fail closed.
                if ((madeBy >> 8) != 3 || ((attributes >> 16) & 0170000) != 0100000
                        || (attributes & 0x10) != 0)
                    throw new IOException("Archive contains a non-regular file");
                byte[] nameBytes = new byte[nameLength]; in.readFully(nameBytes);
                for (byte b : nameBytes) if ((b & 255) < 32 || (b & 255) > 126) throw new IOException("Non-ASCII archive path");
                String name = new String(nameBytes, StandardCharsets.US_ASCII);
                byte[] extra = new byte[extraLength]; in.readFully(extra);
                if (uncompressed == 0xffffffffL || compressed == 0xffffffffL || localOffset == 0xffffffffL) {
                    boolean found = false;
                    for (int at = 0; at + 4 <= extra.length;) {
                        int tag = le16(extra, at), n = le16(extra, at + 2); at += 4;
                        if (at + n > extra.length) throw new IOException("Invalid ZIP extra field");
                        if (tag == 1) {
                            int cursor = at;
                            if (uncompressed == 0xffffffffL) { uncompressed = extra64(extra, cursor, at + n); cursor += 8; }
                            if (compressed == 0xffffffffL) { compressed = extra64(extra, cursor, at + n); cursor += 8; }
                            if (localOffset == 0xffffffffL) localOffset = extra64(extra, cursor, at + n);
                            found = true;
                        }
                        at += n;
                    }
                    if (!found) throw new IOException("Missing ZIP64 entry size");
                }
                long wantedBytes;
                if (asset && i == 0) {
                    if (!name.equals("asset-manifest.json")) throw new IOException("Asset manifest is not first");
                    wantedBytes = contract.manifestBytes;
                } else {
                    IndexEntry record = expected.next();
                    if (record == null || !name.equals(record.name)) throw new IOException("ZIP central inventory mismatch");
                    checkName(name, asset ? "assets/" : "data/");
                    if (name.compareTo(previous) <= 0) throw new IOException("Duplicate or unsorted ZIP paths");
                    previous = name;
                    wantedBytes = record.bytes;
                }
                if (uncompressed != wantedBytes || compressed > length || localOffset >= offset)
                    throw new IOException("ZIP entry size or offset mismatch");
                in.seek(add(in.getFilePointer(), commentLength));
                if (in.getFilePointer() > centralEnd) throw new IOException("ZIP central directory is truncated");
            }
            if (expected.next() != null || in.getFilePointer() != centralEnd)
                throw new IOException("Unexpected ZIP central directory data");
        }
    }
    private static long findEnd(RandomAccessFile in) throws IOException {
        long length = in.length();
        for (long at = length - 22, first = Math.max(0, length - 65557); at >= first; at--) {
            in.seek(at);
            if (u32(in) == 0x06054b50L) {
                in.seek(at + 20);
                if (at + 22 + u16(in) == length) return at;
            }
        }
        throw new IOException("Missing or truncated ZIP central directory");
    }
    private static final class IndexEntry {
        final long bytes; final String hash, name;
        IndexEntry(long bytes, String hash, String name) { this.bytes = bytes; this.hash = hash; this.name = name; }
    }
    private static final class IndexReader implements Closeable {
        private final InputStream input;
        IndexReader(Path file) throws IOException { input = new BufferedInputStream(Files.newInputStream(file), 128 * 1024); }
        IndexEntry next() throws IOException {
            ByteArrayOutputStream line = new ByteArrayOutputStream();
            int b;
            while ((b = input.read()) != -1 && b != '\n') {
                if (b != '\t' && (b < 32 || b > 126)) throw new IOException("Invalid inventory encoding");
                if (line.size() >= MAX_PATH + 100) throw new IOException("Inventory path is too long");
                line.write(b);
            }
            if (b == -1) {
                if (line.size() == 0) return null;
                throw new IOException("The inventory must end with a newline");
            }
            String[] parts = new String(line.toByteArray(), StandardCharsets.US_ASCII).split("\t", -1);
            if (parts.length != 3 || !parts[1].matches("[0-9a-f]{64}")) throw new IOException("Invalid inventory record");
            return new IndexEntry(number(parts[0], MAX_BYTES), parts[1], parts[2]);
        }
        public void close() throws IOException { input.close(); }
    }
    private static void checkName(String name, String prefix) throws IOException {
        if (name.length() > MAX_PATH || !name.startsWith(prefix) || name.length() == prefix.length()
                || name.indexOf('\\') >= 0 || name.indexOf(':') >= 0)
            throw new IOException("Unsafe archive path");
        for (String part : name.split("/", -1)) {
            if (part.isEmpty() || part.equals(".") || part.equals("..") || part.endsWith(".") || part.endsWith(" "))
                throw new IOException("Unsafe archive path component");
            for (int i = 0; i < part.length(); i++) {
                char c = part.charAt(i);
                if (c < 32 || c > 126 || c == '*' || c == '?' || c == '"' || c == '<' || c == '>' || c == '|')
                    throw new IOException("Unsupported archive path character");
            }
        }
    }
    private WriterLock lock() throws IOException {
        Path path = base.toPath().resolve("import.lock");
        if (Files.isSymbolicLink(path)) throw new IOException("Unsafe import lock");
        FileChannel channel = FileChannel.open(path, StandardOpenOption.CREATE, StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS);
        try {
            FileLock lock = channel.tryLock();
            if (lock == null) throw new IOException("Another content operation is already running");
            return new WriterLock(channel, lock);
        } catch (OverlappingFileLockException e) {
            channel.close();
            throw new IOException("Another content operation is already running", e);
        } catch (IOException | RuntimeException e) { channel.close(); throw e; }
    }
    private static final class WriterLock implements Closeable {
        final FileChannel channel; final FileLock lock;
        WriterLock(FileChannel channel, FileLock lock) { this.channel = channel; this.lock = lock; }
        public void close() throws IOException { try { lock.release(); } finally { channel.close(); } }
    }
    private static void noLinks(Path path) throws IOException {
        Path cursor = path.toAbsolutePath().getRoot();
        for (Path component : path.toAbsolutePath()) {
            cursor = cursor.resolve(component);
            if (Files.isSymbolicLink(cursor)) throw new IOException("A content path contains a symbolic link");
        }
    }
    private static void remove(Path path, final Control control) throws IOException {
        if (!Files.exists(path, LinkOption.NOFOLLOW_LINKS)) return;
        Files.walkFileTree(path, new SimpleFileVisitor<Path>() {
            @Override public FileVisitResult preVisitDirectory(Path dir, BasicFileAttributes attrs) throws IOException {
                if (control != null) check(control);
                return FileVisitResult.CONTINUE;
            }
            @Override public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) throws IOException {
                if (control != null) check(control);
                Files.delete(file); return FileVisitResult.CONTINUE;
            }
            @Override public FileVisitResult postVisitDirectory(Path dir, IOException failure) throws IOException {
                if (failure != null) throw failure;
                Files.delete(dir); return FileVisitResult.CONTINUE;
            }
        });
    }
    private static void quietRemove(Path path) {
        if (path != null) try { remove(path, null); } catch (IOException ignored) { /* Recovered on next import. */ }
    }
    private static void check(Control control) throws CancelledException {
        if (control.isCancelled() || Thread.currentThread().isInterrupted()) throw new CancelledException();
    }
    private static void update(Progress callback, String phase, long files, long count, long bytes, long total) {
        if (callback != null) callback.update(phase, files, count, bytes, total);
    }
    private static void writeSynced(Path path, byte[] data) throws IOException {
        try (FileOutputStream out = new FileOutputStream(path.toFile())) { out.write(data); out.getFD().sync(); }
    }
    private static Properties readProperties(Path path, int limit) throws IOException {
        if (!Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS)) throw new IOException("Content receipt is missing or unsafe");
        Properties result = new Properties();
        try (InputStream in = Files.newInputStream(path)) { result.load(new ByteArrayInputStream(bounded(in, limit))); }
        return result;
    }
    private static byte[] bounded(InputStream in, int limit) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buffer = new byte[4096]; int n;
        while ((n = in.read(buffer)) != -1) {
            if (out.size() + n > limit) throw new IOException("APK content metadata is too large");
            out.write(buffer, 0, n);
        }
        return out.toByteArray();
    }
    private static MessageDigest digest() {
        try { return MessageDigest.getInstance("SHA-256"); }
        catch (NoSuchAlgorithmException e) { throw new AssertionError(e); }
    }
    private static String hex(byte[] data) {
        StringBuilder out = new StringBuilder(data.length * 2);
        for (byte b : data) { out.append(Character.forDigit((b >>> 4) & 15, 16)); out.append(Character.forDigit(b & 15, 16)); }
        return out.toString();
    }
    private static long number(String value, long maximum) throws IOException {
        if (value == null || !value.matches("0|[1-9][0-9]*")) throw new IOException("Invalid APK inventory number");
        try { long n = Long.parseLong(value); if (n > maximum) throw new IOException("APK inventory exceeds limits"); return n; }
        catch (NumberFormatException e) { throw new IOException("APK inventory number is too large", e); }
    }
    private static long add(long a, long b) throws IOException {
        if (a < 0 || b < 0 || a > Long.MAX_VALUE - b) throw new IOException("Inventory byte count overflow");
        return a + b;
    }
    private static long multiply(long a, long b) throws IOException {
        if (a < 0 || b < 0 || (b != 0 && a > Long.MAX_VALUE / b)) throw new IOException("Inventory byte count overflow");
        return a * b;
    }
    private static int u16(RandomAccessFile in) throws IOException { int a = in.readUnsignedByte(); return a | in.readUnsignedByte() << 8; }
    private static long u32(RandomAccessFile in) throws IOException { return (long)u16(in) | (long)u16(in) << 16; }
    private static long u64(RandomAccessFile in) throws IOException {
        long low = u32(in), high = u32(in);
        if (high > 0x7fffffffL) throw new IOException("ZIP64 value exceeds supported range");
        return low | high << 32;
    }
    private static int le16(byte[] b, int at) { return (b[at] & 255) | (b[at + 1] & 255) << 8; }
    private static long le32(byte[] b, int at) { return (long)le16(b, at) | (long)le16(b, at + 2) << 16; }
    private static long extra64(byte[] bytes, int at, int end) throws IOException {
        if (at + 8 > end || (bytes[at + 7] & 128) != 0) throw new IOException("Invalid ZIP64 extra field");
        long n = 0; for (int i = 7; i >= 0; i--) n = (n << 8) | (bytes[at + i] & 255); return n;
    }
    private static final class Contract {
        final String digest, source, data, repository, assetArchiveHash, textArchiveHash, manifestHash, assetIndexHash, textIndexHash;
        final long assetArchiveBytes, textArchiveBytes, manifestBytes, assetIndexBytes, textIndexBytes;
        final long assetCount, assetBytes, textCount, textBytes, totalCount, totalBytes, reserve, perFile;
        Contract(byte[] raw) throws IOException {
            Properties p = new Properties(); p.load(new ByteArrayInputStream(raw));
            if (!"1".equals(p.getProperty("format"))) throw new IOException("Unsupported APK content format");
            digest = hex(AtlasAssetImporter.digest().digest(raw));
            source = commit(p, "source.commit"); data = commit(p, "data.commit"); repository = commit(p, "repository.commit");
            assetArchiveHash = hash(p, "asset.archive.sha256"); textArchiveHash = hash(p, "text.archive.sha256");
            manifestHash = hash(p, "asset.manifest.sha256"); assetIndexHash = hash(p, "asset.index.sha256"); textIndexHash = hash(p, "text.index.sha256");
            assetArchiveBytes = n(p, "asset.archive.bytes", MAX_BYTES); textArchiveBytes = n(p, "text.archive.bytes", MAX_BYTES);
            manifestBytes = n(p, "asset.manifest.bytes", MAX_INDEX); assetIndexBytes = n(p, "asset.index.bytes", MAX_INDEX); textIndexBytes = n(p, "text.index.bytes", MAX_INDEX);
            assetCount = n(p, "asset.count", 400000); textCount = n(p, "text.count", 400000); totalCount = n(p, "total.count", 400000);
            assetBytes = n(p, "asset.bytes", MAX_BYTES); textBytes = n(p, "text.bytes", MAX_BYTES); totalBytes = n(p, "total.bytes", MAX_BYTES);
            reserve = n(p, "storage.reserve.bytes", MAX_BYTES); perFile = n(p, "storage.per.file.bytes", 65536);
            if (assetArchiveBytes == 0 || textArchiveBytes == 0 || totalCount == 0 || totalCount != add(assetCount, textCount)
                    || totalBytes != add(assetBytes, textBytes) || reserve < 256L * 1024 * 1024 || perFile < 4096)
                throw new IOException("Inconsistent APK content inventory");
        }
        private static long n(Properties p, String key, long max) throws IOException { return number(p.getProperty(key), max); }
        private static String hash(Properties p, String key) throws IOException {
            String value = p.getProperty(key, "");
            if (!value.matches("[0-9a-f]{64}")) throw new IOException("Invalid APK content hash: " + key); return value;
        }
        private static String commit(Properties p, String key) throws IOException {
            String value = p.getProperty(key, "");
            if (!value.matches("[0-9a-f]{40}")) throw new IOException("Invalid APK content revision: " + key); return value;
        }
    }
}
