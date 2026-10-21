package org.coh.nativecombined;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.Locale;
import java.util.zip.CRC32;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/** One bounded, historical game-surface snapshot in private application storage.
 * No Android, Bitmap, PNG or JSON-library dependency. This does not establish
 * startup readiness, present world authority, or anything outside the surface.
 */
public final class SceneFrameCapture {
    private static final String STORE = "scene-capture.bin";
    private static final String TEMP = "scene-capture.tmp";
    private static final byte[] STORE_MAGIC = "COHFC001".getBytes(StandardCharsets.US_ASCII);
    private static final byte[] RAW_MAGIC = "COHFB001".getBytes(StandardCharsets.US_ASCII);
    private static final byte[] RAW_NAME = "scene-capture.rgba".getBytes(StandardCharsets.US_ASCII);
    private static final byte[] PNG_NAME = "scene-capture.png".getBytes(StandardCharsets.US_ASCII);
    private static final byte[] JSON_NAME = "scene-capture.json".getBytes(StandardCharsets.US_ASCII);
    private static final char[] HEX = "0123456789abcdef".toCharArray();
    private static final int HEADER = 128;
    private static final int MAX_RAW = HEADER + 192 * 108 * 4;
    private static final int MAX_STORE = HEADER + MAX_RAW;
    private static final int MAX_LARGE_RAW = HEADER + 640 * 360 * 4;
    private static final int MAX_LARGE_STORE = HEADER + MAX_LARGE_RAW;
    private static final int CHUNK = 16 * 1024;
    private static final int MAX_JSON = 4 * 1024;
    private static final long SCENE_CAP = 96L * 1024 * 1024;

    private SceneFrameCapture() { }

    /** Atomically replace the one saved capture. The raw array belongs to the
     * caller and must not be changed until this call returns. Reusing an equal
     * or older frame in the currently saved activity session is rejected.
     * Atomic replacement is required; failure never deletes the previous file.
     */
    public static synchronized String save(File directory, byte[] raw,
            long appVersion, String activitySession) throws IOException {
        return save(directory,raw,appVersion,activitySession,false);
    }
    public static synchronized String saveLarge(File directory,byte[] raw,long appVersion,String activitySession) throws IOException {
        return save(directory,raw,appVersion,activitySession,true);
    }
    private static String save(File directory,byte[] raw,long appVersion,String activitySession,boolean large) throws IOException {
        Frame frame = frame(raw, raw == null ? 0 : raw.length,large);
        String session = session(activitySession);
        if (frame == null || appVersion <= 0 || session == null || directory == null)
            throw new IOException("Scene capture input rejected");
        Capture previous = optional(directory, false, false,large);
        if (previous != null && previous.session.equals(session)
                && frame.frame <= previous.frame.frame)
            throw new IOException("Scene capture frame already stored");

        byte[] wrapper = new byte[HEADER];
        System.arraycopy(STORE_MAGIC, 0, wrapper, 0, STORE_MAGIC.length);
        put32(wrapper, 8, HEADER);
        put32(wrapper, 12, raw.length);
        put64(wrapper, 16, appVersion);
        put32(wrapper, 24, session.length());
        for (int i = 0; i < session.length(); i++) wrapper[32 + i] = (byte) session.charAt(i);
        byte[] rawHash = digest(raw, 0, raw.length);
        System.arraycopy(rawHash, 0, wrapper, 64, rawHash.length);
        MessageDigest all = hash();
        all.update(wrapper, 0, 96);
        update(all, raw, 0, raw.length);
        byte[] storeHash = all.digest();
        System.arraycopy(storeHash, 0, wrapper, 96, storeHash.length);
        String json = json(frame, appVersion, session, raw.length, rawHash);

        if ((!directory.isDirectory() && !directory.mkdirs()) || !directory.isDirectory())
            throw new IOException("Scene capture directory unavailable");
        File temporary = new File(directory, TEMP);
        File target = new File(directory, STORE);
        try {
            // A fixed temporary filename and this class lock allow one writer;
            // callers must use an application-private directory, not shared input.
            try (FileOutputStream output = new FileOutputStream(temporary)) {
                output.write(wrapper);
                for (int offset = 0; offset < raw.length; offset += CHUNK)
                    output.write(raw, offset, Math.min(CHUNK, raw.length - offset));
                output.getFD().sync();
            }
            Files.move(temporary.toPath(), target.toPath(),
                    StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
        } catch (AtomicMoveNotSupportedException unsupported) {
            throw new IOException("Atomic scene capture storage unavailable");
        } finally {
            if (temporary.exists()) temporary.delete();
        }
        return json;
    }

    /** A validated snapshot for one exact installed app/activity run. Retained
     * bytes cannot change if a subsequent capture replaces the backing file. */
    public static final class Selection {
        private final Capture capture;
        private final boolean large;
        private final String reason;
        private Selection(Capture capture, boolean large, String reason) {
            this.capture=capture;this.large=large;this.reason=reason;
        }
        public String metadata(){return capture==null?null:capture.json;}
        public String omissionReason(){return reason;}
        public boolean append(ZipOutputStream zip)throws IOException {
            return capture!=null&&SceneFrameCapture.append(capture,zip,large);
        }
        public boolean writeZip(OutputStream output)throws IOException {
            return capture!=null&&SceneFrameCapture.writeZip(capture,output,large);
        }
    }
    public static synchronized Selection current(File directory,long appVersion,String activitySession,boolean large) {
        return current(directory,appVersion,activitySession,large,true);
    }
    public static synchronized Selection inspectCurrent(File directory,long appVersion,String activitySession,boolean large) {
        return current(directory,appVersion,activitySession,large,false);
    }
    private static Selection current(File directory,long appVersion,String activitySession,boolean large,boolean retain) {
        String expected=session(activitySession);
        if(appVersion<=0||expected==null)return new Selection(null,large,"CAPTURE_CURRENT_RUN_UNAVAILABLE");
        Capture capture=optional(directory,retain,true,large);
        if(capture==null)return new Selection(null,large,"CAPTURE_MISSING_OR_INVALID");
        if(capture.version!=appVersion)return new Selection(null,large,"CAPTURE_APP_VERSION_MISMATCH");
        if(!capture.session.equals(expected))return new Selection(null,large,"CAPTURE_ACTIVITY_SESSION_MISMATCH");
        return new Selection(capture,large,null);
    }
    public static synchronized void clear(File directory)throws IOException {
        if(directory==null)throw new IOException("Capture directory unavailable");
        Files.deleteIfExists(new File(directory,TEMP).toPath());
        Files.deleteIfExists(new File(directory,STORE).toPath());
    }

    /** Return metadata for a complete validated historical record, or null. */
    public static synchronized String metadata(File directory) {
        Capture capture = optional(directory, false, true,false);
        return capture == null ? null : capture.json;
    }
    public static synchronized String metadataLarge(File directory) {
        Capture capture=optional(directory,false,true,true);
        return capture==null?null:capture.json;
    }

    /** Validate before touching ZIP output. Absent/invalid storage returns false;
     * an actual ZIP sink failure propagates because a partial ZIP is not valid.
     * A bounded snapshot prevents a later disk mutation changing exported bytes.
     */
    public static synchronized boolean append(File directory, ZipOutputStream zip) throws IOException {
        return append(directory,zip,false);
    }
    public static synchronized boolean appendLarge(File directory,ZipOutputStream zip) throws IOException {
        return append(directory,zip,true);
    }
    private static boolean append(File directory,ZipOutputStream zip,boolean large) throws IOException {
        if (zip == null) throw new IOException("Scene capture ZIP unavailable");
        Capture capture = optional(directory, true, true,large);
        if (capture == null) return false;
        return append(capture,zip,large);
    }
    private static boolean append(Capture capture,ZipOutputStream zip,boolean large)throws IOException {
        if(zip==null||capture.raw==null)throw new IOException("Capture ZIP snapshot unavailable");
        SceneCapturePng.Info png=large?SceneCapturePng.measure(capture.raw,capture.frame.width,capture.frame.height):null;
        byte[] json=exportJson(capture,png).getBytes(StandardCharsets.UTF_8);
        if(large){
            if(capture.raw.length+png.bytes+json.length+512>2*1024*1024)throw new IOException("Scene ZIP exceeds existing export bound");
            CRC32 crc=new CRC32();
            stored(zip,"scene-capture.rgba",capture.raw.length,crc(crc,capture.raw));
            zip.write(capture.raw);zip.closeEntry();
            stored(zip,"scene-capture.json",json.length,crc(crc,json));zip.write(json);zip.closeEntry();
            stored(zip,"scene-capture.png",png.bytes,png.crc);
            SceneCapturePng.write(capture.raw,capture.frame.width,capture.frame.height,zip);zip.closeEntry();return true;
        }
        zip.putNextEntry(new ZipEntry("scene-capture.rgba"));
        for (int offset = 0; offset < capture.raw.length; offset += CHUNK)
            zip.write(capture.raw, offset, Math.min(CHUNK, capture.raw.length - offset));
        zip.closeEntry();
        zip.putNextEntry(new ZipEntry("scene-capture.json"));
        zip.write(capture.json.getBytes(StandardCharsets.UTF_8));
        zip.closeEntry();
        return true;
    }

    /** Standalone ZIP with exactly two uncompressed entries. This does not
     * construct a Deflater or close the caller's output. Invalid storage returns
     * false before writing; actual output failures propagate to the caller.
     */
    public static synchronized boolean writeZip(File directory, OutputStream output) throws IOException {
        return writeZip(directory,output,false);
    }
    public static synchronized boolean writeZipLarge(File directory,OutputStream output) throws IOException {
        return writeZip(directory,output,true);
    }
    private static boolean writeZip(File directory,OutputStream output,boolean large) throws IOException {
        if (output == null) throw new IOException("Scene capture ZIP unavailable");
        Capture capture = optional(directory, true, true,large);
        if (capture == null) return false;
        return writeZip(capture,output,large);
    }
    private static boolean writeZip(Capture capture,OutputStream output,boolean large)throws IOException {
        if(output==null||capture.raw==null)throw new IOException("Capture ZIP snapshot unavailable");
        SceneCapturePng.Info png=large?SceneCapturePng.measure(capture.raw,capture.frame.width,capture.frame.height):null;
        byte[] json = exportJson(capture,png).getBytes(StandardCharsets.UTF_8);
        byte[] header = new byte[46];
        CRC32 crc = new CRC32();
        long rawCrc = crc(crc, capture.raw), jsonCrc = crc(crc, json);
        int jsonOffset = 30 + RAW_NAME.length + capture.raw.length;
        int pngOffset = jsonOffset + 30 + JSON_NAME.length + json.length;
        int centralOffset = pngOffset+(large?30+PNG_NAME.length+png.bytes:0);
        int entries=large?3:2;
        int centralBytes = 46 * entries + RAW_NAME.length + JSON_NAME.length+(large?PNG_NAME.length:0);
        if(large&&centralOffset+centralBytes+22>2*1024*1024)throw new IOException("Scene ZIP exceeds existing export bound");
        local(output, header, RAW_NAME, capture.raw, rawCrc);
        local(output, header, JSON_NAME, json, jsonCrc);
        if(large){
            localPrefix(output,header,PNG_NAME,png.bytes,png.crc);
            SceneCapturePng.write(capture.raw,capture.frame.width,capture.frame.height,output);
        }
        central(output, header, RAW_NAME, capture.raw.length, rawCrc, 0);
        central(output, header, JSON_NAME, json.length, jsonCrc, jsonOffset);
        if(large)central(output,header,PNG_NAME,png.bytes,png.crc,pngOffset);
        Arrays.fill(header, (byte) 0);
        put32(header, 0, 0x06054b50);
        put16(header, 8, entries); put16(header, 10, entries);
        put32(header, 12, centralBytes); put32(header, 16, centralOffset);
        output.write(header, 0, 22);
        return true;
    }

    private static String exportJson(Capture capture,SceneCapturePng.Info png)throws IOException {
        if(png==null)return capture.json;
        String value=capture.json.substring(0,capture.json.length()-1)+",\"image\":{\"file\":\"scene-capture.png\",\"bytes\":"+png.bytes
                +",\"sha256\":\""+png.sha256+"\",\"format\":\"PNG_RGBA8\",\"origin\":\"top_left\"}}";
        if(value.length()>MAX_JSON)throw new IOException("Scene PNG metadata exceeds existing bound");return value;
    }
    private static void stored(ZipOutputStream out,String name,int size,long crc)throws IOException {
        ZipEntry entry=new ZipEntry(name);entry.setMethod(ZipEntry.STORED);entry.setSize(size);entry.setCompressedSize(size);entry.setCrc(crc);out.putNextEntry(entry);
    }
    private static void localPrefix(OutputStream output,byte[] header,byte[] name,int size,long crc)throws IOException {
        Arrays.fill(header,(byte)0);put32(header,0,0x04034b50);put16(header,4,20);put16(header,12,33);
        put32(header,14,crc);put32(header,18,size);put32(header,22,size);put16(header,26,name.length);output.write(header,0,30);output.write(name);
    }
    private static long crc(CRC32 crc, byte[] bytes) {
        crc.reset();
        for (int offset = 0; offset < bytes.length; offset += CHUNK)
            crc.update(bytes, offset, Math.min(CHUNK, bytes.length - offset));
        return crc.getValue();
    }

    private static void local(OutputStream output, byte[] header, byte[] name,
            byte[] content, long crc) throws IOException {
        Arrays.fill(header, (byte) 0);
        put32(header, 0, 0x04034b50); put16(header, 4, 20); put16(header, 12, 33);
        put32(header, 14, crc); put32(header, 18, content.length); put32(header, 22, content.length);
        put16(header, 26, name.length);
        output.write(header, 0, 30); output.write(name);
        for (int offset = 0; offset < content.length; offset += CHUNK)
            output.write(content, offset, Math.min(CHUNK, content.length - offset));
    }

    private static void central(OutputStream output, byte[] header, byte[] name,
            int size, long crc, int offset) throws IOException {
        Arrays.fill(header, (byte) 0);
        put32(header, 0, 0x02014b50); put16(header, 4, 20); put16(header, 6, 20);
        put16(header, 14, 33); put32(header, 16, crc); put32(header, 20, size); put32(header, 24, size);
        put16(header, 28, name.length); put32(header, 42, offset);
        output.write(header, 0, 46); output.write(name);
    }

    private static Capture optional(File directory, boolean retainRaw, boolean makeJson,boolean large) {
        if (directory == null) return null;
        try {
            return read(new File(directory, STORE), retainRaw, makeJson,large);
        } catch (IOException | SecurityException invalid) {
            return null;
        }
    }

    private static Capture read(File file, boolean retainRaw, boolean makeJson,boolean large) throws IOException {
        long bytes = file.length(), modified = file.lastModified();
        if (!file.isFile() || bytes < HEADER * 2 + 4 || bytes > (large?MAX_LARGE_STORE:MAX_STORE)) return null;
        try (FileInputStream input = new FileInputStream(file)) {
            if (input.getChannel().size() != bytes) return null;
            byte[] wrapper = new byte[HEADER];
            exact(input, wrapper, 0, HEADER);
            long length = u32(wrapper, 12), version = u64(wrapper, 16);
            int sessionLength = (int) u32(wrapper, 24);
            if (!magic(wrapper, STORE_MAGIC) || u32(wrapper, 8) != HEADER
                    || length < HEADER + 4 || length > (large?MAX_LARGE_RAW:MAX_RAW)
                    || bytes != HEADER + length || version <= 0
                    || sessionLength < 1 || sessionLength > 32 || u32(wrapper, 28) != 0)
                return null;
            for (int i = sessionLength; i < 32; i++) if (wrapper[32 + i] != 0) return null;
            String session = new String(wrapper, 32, sessionLength, StandardCharsets.US_ASCII);
            if (!session.equals(session(session))) return null;
            byte[] nativeHeader = new byte[HEADER];
            exact(input, nativeHeader, 0, HEADER);
            Frame frame = frame(nativeHeader, (int) length,large);
            if (frame == null) return null;

            byte[] raw = retainRaw ? new byte[(int) length] : null;
            byte[] scratch = retainRaw ? raw : new byte[CHUNK];
            if (retainRaw) System.arraycopy(nativeHeader, 0, raw, 0, HEADER);
            MessageDigest rawDigest = hash(), storeDigest = hash();
            rawDigest.update(nativeHeader);
            storeDigest.update(wrapper, 0, 96);
            storeDigest.update(nativeHeader);
            int offset = HEADER;
            while (offset < length) {
                int count = Math.min(CHUNK, (int) length - offset);
                int start = retainRaw ? offset : 0;
                exact(input, scratch, start, count);
                rawDigest.update(scratch, start, count);
                storeDigest.update(scratch, start, count);
                offset += count;
            }
            if (input.read() != -1 || input.getChannel().size() != bytes || !file.isFile()
                    || file.length() != bytes || file.lastModified() != modified) return null;
            byte[] rawHash = rawDigest.digest(), storeHash = storeDigest.digest();
            if (!same(wrapper, 64, rawHash) || !same(wrapper, 96, storeHash)) return null;
            return new Capture(frame, version, session,
                    makeJson ? json(frame, version, session, (int) length, rawHash) : null, raw);
        }
    }

    private static void exact(FileInputStream input, byte[] bytes, int offset, int count)
            throws IOException {
        int end = offset + count;
        while (offset < end) {
            int read = input.read(bytes, offset, Math.min(CHUNK, end - offset));
            if (read < 0) throw new IOException("Scene capture truncated");
            if (read == 0) throw new IOException("Scene capture stalled");
            offset += read;
        }
    }

    private static Frame frame(byte[] raw, int length,boolean large) {
        if (raw == null || raw.length < HEADER || length < HEADER + 4 || length > (large?MAX_LARGE_RAW:MAX_RAW)
                || !magic(raw, RAW_MAGIC) || u32(raw, 8) != HEADER) return null;
        long width = u32(raw, 12), height = u32(raw, 16);
        long viewportWidth = u32(raw, 20), viewportHeight = u32(raw, 24);
        long pixelBytes = u32(raw, 28), index = u32(raw, 32);
        long frame = u64(raw, 40), epoch = u64(raw, 48), pose = u64(raw, 56);
        long lock = u64(raw, 64), packets = u64(raw, 72), draws = u64(raw, 80);
        long charged = u64(raw, 104), cap = u64(raw, 112);
        float x = Float.intBitsToFloat((int) u32(raw, 88));
        float y = Float.intBitsToFloat((int) u32(raw, 92));
        float z = Float.intBitsToFloat((int) u32(raw, 96));
        if (width < 1 || width > (large?640:192) || height < 1 || height > (large?360:108)
                || viewportWidth < width || viewportWidth > 16384
                || viewportHeight < height || viewportHeight > 16384
                || pixelBytes != width * height * 4 || length != HEADER + pixelBytes
                || index < 1 || index > 10239 || u32(raw, 36) != 0 || u32(raw, 100) != 0
                || frame < 0 || epoch < 0 || lock < 0 || frame < 12 || lock > frame - 12
                || pose <= 0 || packets <= 0 || draws <= 0 || charged < 0 || charged > SCENE_CAP
                || cap != SCENE_CAP || u32(raw, 120) != 12 || u32(raw, 124) != 1
                || !Float.isFinite(x) || !Float.isFinite(y) || !Float.isFinite(z)) return null;
        return new Frame((int) width, (int) height, (int) viewportWidth, (int) viewportHeight,
                (int) index, frame, epoch, pose, lock, packets, draws, charged, x, y, z);
    }

    private static String json(Frame f, long version, String session, int bytes, byte[] rawHash)
            throws IOException {
        // Fixed initial capacity avoids capacity growth. Every variable below is
        // a bounded numeric value or <=32 ASCII hex characters, never JSON input.
        StringBuilder value = new StringBuilder(MAX_JSON);
        value.append("{\"format\":\"coh-game-surface-rgba8-v1\",\"artifact\":\"scene-capture.rgba\",")
                .append("\"capture_state\":\"historical_saved_frame\",\"startup_witness\":false,")
                .append("\"current_world_authority\":false,\"whole_game_surface\":true,")
                .append("\"pixel_format\":\"RGBA8\",\"origin\":\"bottom-left\",\"raw_header_bytes\":128,")
                .append("\"size_bytes\":").append(bytes).append(",\"sha256\":\"").append(hex(rawHash)).append("\",")
                .append("\"frame\":").append(f.frame).append(",\"epoch\":").append(f.epoch)
                .append(",\"pose_generation\":").append(f.pose).append(",\"pose_lock_frame\":").append(f.lock)
                .append(",\"pose\":[").append((double) f.x).append(',').append((double) f.y)
                .append(',').append((double) f.z).append(']')
                .append(",\"selected_entity_index\":").append(f.index)
                .append(",\"viewport\":{\"width\":").append(f.viewportWidth)
                .append(",\"height\":").append(f.viewportHeight).append('}')
                .append(",\"dimensions\":{\"width\":").append(f.width)
                .append(",\"height\":").append(f.height).append('}')
                .append(",\"world_packets\":").append(f.packets).append(",\"entity_draws\":").append(f.draws)
                .append(",\"charged_scene_bytes\":").append(f.charged).append(",\"memory_cap_bytes\":").append(SCENE_CAP)
                .append(",\"settled_frame_wait\":12,\"source_app_version\":").append(version)
                .append(",\"activity_session\":\"").append(session).append("\"}");
        if (value.length() > MAX_JSON) throw new IOException("Scene capture metadata rejected");
        return value.toString(); // ASCII only, so UTF-8 bytes == characters.
    }

    private static String session(String value) {
        if (value == null || value.length() < 1 || value.length() > 32) return null;
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F')))
                return null;
        }
        return value.toLowerCase(Locale.ROOT);
    }

    private static MessageDigest hash() throws IOException {
        try { return MessageDigest.getInstance("SHA-256"); }
        catch (NoSuchAlgorithmException unavailable) { throw new IOException("Scene capture hash unavailable"); }
    }

    private static byte[] digest(byte[] bytes, int start, int length) throws IOException {
        MessageDigest digest = hash();
        update(digest, bytes, start, length);
        return digest.digest();
    }

    private static void update(MessageDigest digest, byte[] bytes, int start, int length) {
        int end = start + length;
        for (int offset = start; offset < end; offset += CHUNK)
            digest.update(bytes, offset, Math.min(CHUNK, end - offset));
    }

    private static String hex(byte[] bytes) {
        char[] out = new char[bytes.length * 2];
        for (int i = 0; i < bytes.length; i++) {
            out[2 * i] = HEX[(bytes[i] & 255) >>> 4];
            out[2 * i + 1] = HEX[bytes[i] & 15];
        }
        return new String(out);
    }

    private static boolean magic(byte[] bytes, byte[] magic) {
        for (int i = 0; i < magic.length; i++) if (bytes[i] != magic[i]) return false;
        return true;
    }

    private static boolean same(byte[] bytes, int offset, byte[] expected) {
        int different = 0;
        for (int i = 0; i < expected.length; i++) different |= bytes[offset + i] ^ expected[i];
        return different == 0;
    }

    private static long u32(byte[] bytes, int offset) {
        long value = 0;
        for (int i = 0; i < 4; i++) value |= (long) (bytes[offset + i] & 255) << (8 * i);
        return value;
    }

    private static long u64(byte[] bytes, int offset) {
        return u32(bytes, offset) | (u32(bytes, offset + 4) << 32);
    }

    private static void put32(byte[] bytes, int offset, long value) {
        for (int i = 0; i < 4; i++) bytes[offset + i] = (byte) (value >>> (8 * i));
    }

    private static void put16(byte[] bytes, int offset, int value) {
        bytes[offset] = (byte) value;
        bytes[offset + 1] = (byte) (value >>> 8);
    }

    private static void put64(byte[] bytes, int offset, long value) {
        for (int i = 0; i < 8; i++) bytes[offset + i] = (byte) (value >>> (8 * i));
    }

    private static final class Capture {
        final Frame frame;
        final long version;
        final String session, json;
        final byte[] raw;
        Capture(Frame frame, long version, String session, String json, byte[] raw) {
            this.version=version;this.frame = frame; this.session = session; this.json = json; this.raw = raw;
        }
    }

    private static final class Frame {
        final int width, height, viewportWidth, viewportHeight, index;
        final long frame, epoch, pose, lock, packets, draws, charged;
        final float x, y, z;
        Frame(int width, int height, int viewportWidth, int viewportHeight, int index,
                long frame, long epoch, long pose, long lock, long packets, long draws,
                long charged, float x, float y, float z) {
            this.width = width; this.height = height; this.viewportWidth = viewportWidth;
            this.viewportHeight = viewportHeight; this.index = index; this.frame = frame;
            this.epoch = epoch; this.pose = pose; this.lock = lock; this.packets = packets;
            this.draws = draws; this.charged = charged; this.x = x; this.y = y; this.z = z;
        }
    }
}
