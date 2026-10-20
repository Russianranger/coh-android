package org.coh.nativecombined;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.channels.FileChannel;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/** One private INITIAL replay for the explicit capture diagnostic. No stream,
 * post-ACK packet or historical donor is selected here. Call clear at a fresh
 * attempt and save on its network owner before closing the native handle. */
public final class InitialReplayStore {
    static final int HEADER_BYTES=88, PAYLOAD_LIMIT=65536, FRAME_LIMIT=HEADER_BYTES+PAYLOAD_LIMIT;
    static final String NAME="initial-replay.bin";
    private static final byte[] MAGIC={'C','O','H','I','R','P','0','1'};
    private InitialReplayStore() { }
    private static MessageDigest hash() throws IOException {
        try { return MessageDigest.getInstance("SHA-256"); }
        catch(NoSuchAlgorithmException e) { throw new IOException("SHA-256 unavailable",e); }
    }
    private static String hex(byte[] value) {
        StringBuilder out=new StringBuilder(value.length*2);
        for(byte b:value)out.append(Character.forDigit((b>>>4)&15,16)).append(Character.forDigit(b&15,16));
        return out.toString();
    }
    private static String quote(String value) throws IOException {
        if(value==null||value.isEmpty()||value.length()>128)throw new IOException("Capture session identity unavailable");
        StringBuilder out=new StringBuilder("\"");
        for(int i=0;i<value.length();i++) {
            char c=value.charAt(i);
            if(c=='"'||c=='\\')out.append('\\').append(c);
            else if(c<32||c>126)throw new IOException("Capture session identity is not bounded ASCII");
            else out.append(c);
        }
        return out.append('"').toString();
    }
    private static Path directory(File base) throws IOException {
        if(base==null)throw new IOException("Capture directory unavailable");
        Path path=base.toPath().toAbsolutePath();
        Files.createDirectories(path);
        if(!Files.isDirectory(path,LinkOption.NOFOLLOW_LINKS))throw new IOException("Capture directory is not private storage");
        return path;
    }
    private static ByteBuffer validate(byte[] frame) throws IOException {
        if(frame==null||frame.length<=HEADER_BYTES||frame.length>FRAME_LIMIT)throw new IOException("INITIAL replay size differs");
        for(int i=0;i<MAGIC.length;i++)if(frame[i]!=MAGIC[i])throw new IOException("INITIAL replay format differs");
        ByteBuffer b=ByteBuffer.wrap(frame).order(ByteOrder.LITTLE_ENDIAN);
        long payload=Integer.toUnsignedLong(b.getInt(12));
        long bits=b.getLong(16),cursor=b.getLong(24),appearance=b.getLong(32);
        long selected=Integer.toUnsignedLong(b.getInt(44));
        if(b.getInt(8)!=HEADER_BYTES||payload!=frame.length-HEADER_BYTES||payload>PAYLOAD_LIMIT
                ||bits<=0||bits>payload*8||cursor<0||cursor>bits||appearance<0||appearance>bits
                ||b.getInt(40)<0||b.getInt(40)>1||(b.getInt(40)==1&&((cursor|appearance)&7)!=0)
                ||(selected>=10&&selected!=0xffffffffL)||b.getInt(48)!=28||b.getInt(52)!=3)
            throw new IOException("INITIAL replay framing differs");
        MessageDigest digest=hash();digest.update(frame,HEADER_BYTES,(int)payload);
        if(!MessageDigest.isEqual(Arrays.copyOfRange(frame,56,88),digest.digest()))throw new IOException("INITIAL replay SHA-256 differs");
        return b;
    }
    /** Validate the native envelope, atomically replace one file, and return
     * scalar metadata for the current rolling report. No sidecar is created. */
    public static synchronized String save(File base,byte[] frame,long appVersion,String activitySession) throws IOException {
        ByteBuffer b=validate(frame);
        if(appVersion<0)throw new IOException("Capture app version unavailable");
        String session=quote(activitySession);
        Path dir=directory(base),target=dir.resolve(NAME),stage=dir.resolve("initial-replay.tmp");
        if(Files.exists(target,LinkOption.NOFOLLOW_LINKS)&&!Files.isRegularFile(target,LinkOption.NOFOLLOW_LINKS))throw new IOException("INITIAL replay target is not a regular file");
        Files.deleteIfExists(stage);
        try {
            try(FileChannel out=FileChannel.open(stage,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE,LinkOption.NOFOLLOW_LINKS)) {
                ByteBuffer bytes=ByteBuffer.wrap(frame);while(bytes.hasRemaining())if(out.write(bytes)<=0)throw new IOException("INITIAL replay write made no progress");out.force(true);
            }
            Files.move(stage,target,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
        } finally { Files.deleteIfExists(stage); }
        return "{\"file\":\""+NAME+"\",\"bytes\":"+frame.length+",\"sha256\":\""+hex(hash().digest(frame))
                +"\",\"payload_sha256\":\""+hex(Arrays.copyOfRange(frame,56,88))+"\",\"logical_bits\":"+b.getLong(16)
                +",\"post_command_cursor\":"+b.getLong(24)+",\"appearance_cursor\":"+b.getLong(32)+",\"byte_aligned_mode\":"+b.getInt(40)
                +",\"selected_costume_index\":"+Integer.toUnsignedLong(b.getInt(44))+",\"app_version\":"+appVersion+",\"activity_session\":"+session+"}";
    }
    private static byte[] read(Path path) throws IOException {
        BasicFileAttributes attributes=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        if(!attributes.isRegularFile()||attributes.size()<=HEADER_BYTES||attributes.size()>FRAME_LIMIT)throw new IOException("INITIAL replay file size differs");
        byte[] frame=new byte[(int)attributes.size()];
        try(InputStream input=Files.newInputStream(path,LinkOption.NOFOLLOW_LINKS)) {
            int at=0;while(at<frame.length){int n=input.read(frame,at,frame.length-at);if(n<=0)throw new IOException("INITIAL replay is truncated");at+=n;}
            if(input.read()!=-1)throw new IOException("INITIAL replay grew during export");
        }
        validate(frame);return frame;
    }
    /** Revalidate and append only this one bounded frame to the user's report. */
    public static synchronized boolean append(File base,ZipOutputStream output) throws IOException {
        if(base==null||output==null)return false;
        Path target=base.toPath().toAbsolutePath().resolve(NAME);
        if(!Files.exists(target,LinkOption.NOFOLLOW_LINKS))return false;
        byte[] frame=read(target);
        try {output.putNextEntry(new ZipEntry(NAME));output.write(frame);output.closeEntry();return true;}
        finally {Arrays.fill(frame,(byte)0);}
    }
    /** A new attempt has no replay until its own INITIAL is captured. */
    public static synchronized void clear(File base) throws IOException {
        if(base==null)return;
        Path dir=base.toPath().toAbsolutePath();Files.deleteIfExists(dir.resolve(NAME));Files.deleteIfExists(dir.resolve("initial-replay.tmp"));
    }
}
