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
import java.util.Objects;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/** One bounded30-second raw logical-message archive, never a body decoder.
 * A fresh attempt creates TEMP, native duplicates its FD and streams to it,
 * then closes/finalizes it. seal validates/hash-checks and atomically publishes
 * NAME. No sidecar is retained. Runtime metadata belongs to the existing report.
 * Java validation/export uses16KiB scratch and bounded4096-character metadata rather than
 * reading the8MiB file into memory. This is not an Android process-memory claim. */
public final class PostReadyReplayStore {
    public static final String NAME="post-ready-replay.bin";
    private static final String TEMP="post-ready-replay.tmp";
    private static final int HEADER=64,RECORD=112,TRAILER=96,LIMIT=8*1024*1024,RECORD_LIMIT=128;
    private static final int BUFFER=16*1024,METADATA_LIMIT=4096;
    private PostReadyReplayStore() { }
    private static MessageDigest hash()throws IOException {
        try{return MessageDigest.getInstance("SHA-256");}
        catch(NoSuchAlgorithmException e){throw new IOException("SHA-256 unavailable",e);}
    }
    private static String hex(byte[] value){StringBuilder s=new StringBuilder(64);for(byte b:value)s.append(Character.forDigit((b>>>4)&15,16)).append(Character.forDigit(b&15,16));return s.toString();}
    private static String quote(String value)throws IOException {
        if(value==null||value.isEmpty()||value.length()>128)throw new IOException("Post-READY session identity unavailable");
        StringBuilder s=new StringBuilder("\"");for(int i=0;i<value.length();i++){char c=value.charAt(i);if(c<32||c>126)throw new IOException("Post-READY session identity differs");if(c=='"'||c=='\\')s.append('\\');s.append(c);}return s.append('"').toString();
    }
    private static Path directory(File base)throws IOException {
        if(base==null)throw new IOException("Post-READY directory unavailable");Path p=base.toPath().toAbsolutePath();Files.createDirectories(p);
        if(!Files.isDirectory(p,LinkOption.NOFOLLOW_LINKS))throw new IOException("Post-READY directory is not private storage");return p;
    }
    /** Returns one fresh empty private file. Attach its FD before first service;
     * caller must close its Java FD after native duplicates it. */
    public static synchronized File prepare(File base)throws IOException {
        Path dir=directory(base);clear(base);Path stage=dir.resolve(TEMP);
        try(FileChannel channel=FileChannel.open(stage,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE,LinkOption.NOFOLLOW_LINKS)){channel.force(false);}
        return stage.toFile();
    }
    public static synchronized void clear(File base)throws IOException {
        if(base==null)return;Path dir=base.toPath().toAbsolutePath();Files.deleteIfExists(dir.resolve(TEMP));Files.deleteIfExists(dir.resolve(NAME));
    }
    private static boolean magic(byte[] b,String value){for(int i=0;i<value.length();i++)if(b[i]!=(byte)value.charAt(i))return false;return true;}
    private static ByteBuffer little(byte[] b){return ByteBuffer.wrap(b).order(ByteOrder.LITTLE_ENDIAN);}
    private static void need(boolean ok,String why)throws IOException{if(!ok)throw new IOException("Post-READY "+why);}
    private static void read(InputStream in,byte[] b,int from,int count)throws IOException {
        while(count>0){int n=in.read(b,from,count);need(n>0,"file truncated");from+=n;count-=n;}
    }
    private static boolean same(BasicFileAttributes a,BasicFileAttributes b){return a.isRegularFile()&&b.isRegularFile()&&a.size()==b.size()&&a.lastModifiedTime().equals(b.lastModifiedTime())&&Objects.equals(a.fileKey(),b.fileKey());}
    private static final class Summary {
        long bytes,payload,bits,first,last,seen,omitted;int records,reasons,complete;
        String sha;
        String metadata(long appVersion,String session)throws IOException {
            need(appVersion>=0,"app version unavailable");String quoted=quote(session);
            String result="{\"file\":\""+NAME+"\",\"format\":\"coh-post-ready-logical-messages-v1\",\"bytes\":"+bytes+",\"sha256\":\""+sha+"\",\"app_version\":"+appVersion+",\"activity_session\":"+quoted
                +",\"disk_limit_bytes\":"+LIMIT+",\"record_limit\":"+RECORD_LIMIT+",\"scratch_bytes\":"+BUFFER+",\"logical_payloads_not_udp_wire\":true,\"decoded\":false,\"window_complete\":"+(complete==1)
                +",\"messages_complete\":"+(complete==1&&reasons==0&&records==seen)+",\"records_saved\":"+records+",\"messages_seen\":"+seen+",\"messages_omitted\":"+omitted+",\"reason_flags\":"+reasons
                +",\"reason_bits\":{\"1\":\"IO\",\"2\":\"DISK_LIMIT\",\"4\":\"MEMORY\",\"8\":\"INVALID\",\"16\":\"RECORD_LIMIT\",\"32\":\"WINDOW_INCOMPLETE\",\"64\":\"UNOBSERVED_MESSAGE\"},\"payload_bytes\":"+payload+",\"logical_bits\":"+bits+",\"first_monotonic_ms\":"+first+",\"last_monotonic_ms\":"+last+",\"record_header_bytes\":112,\"metadata_max_chars\":4096,\"hash_state_count\":3,\"per_record_metadata\":\"binary record headers\"}";
            need(result.length()<=METADATA_LIMIT,"metadata limit exceeded");return result;
        }
    }
    private static Summary inspect(Path path)throws IOException {
        BasicFileAttributes before=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        need(before.isRegularFile()&&before.size()>=HEADER+TRAILER&&before.size()<=LIMIT,"file size differs");
        Summary s=new Summary();byte[] header=new byte[RECORD],buffer=new byte[BUFFER];MessageDigest all=hash(),prefix=hash(),payload=hash();
        try(InputStream in=Files.newInputStream(path,LinkOption.NOFOLLOW_LINKS)){
            read(in,header,0,HEADER);ByteBuffer h=little(header);
            need(magic(header,"COHPRP01")&&h.getInt(8)==HEADER&&h.getInt(12)==RECORD&&h.getInt(16)==TRAILER&&h.getInt(20)==RECORD_LIMIT&&h.getLong(24)==LIMIT&&h.getLong(32)==30000&&h.getInt(40)==4*1024*1024&&h.getInt(44)==4096,"header differs");
            for(int k=48;k<HEADER;k++)need(header[k]==0,"header reserved bits differ");
            all.update(header,0,HEADER);prefix.update(header,0,HEADER);s.bytes=HEADER;
            while(true){
                need(s.bytes+TRAILER<=before.size(),"terminal summary missing");read(in,header,0,8);
                if(magic(header,"COHPEND1")){
                    read(in,header,8,TRAILER-8);h=little(header);s.seen=Integer.toUnsignedLong(h.getInt(16));s.omitted=Integer.toUnsignedLong(h.getInt(20));s.reasons=h.getInt(24);s.complete=h.getInt(28);
                    need(h.getInt(8)==TRAILER&&h.getInt(12)==s.records&&s.seen>=s.records&&s.omitted==s.seen-s.records&&(s.reasons&~127)==0&&(s.complete==0||s.complete==1)&&((s.complete==1)||((s.reasons&32)!=0))&&h.getLong(32)==s.payload&&h.getLong(40)==s.bits&&h.getLong(48)==s.first&&h.getLong(56)==s.last,"terminal summary differs");
                    need(MessageDigest.isEqual(prefix.digest(),Arrays.copyOfRange(header,64,96)),"prefix SHA-256 differs");all.update(header,0,TRAILER);s.bytes+=TRAILER;need(s.bytes==before.size()&&in.read()==-1,"trailing bytes differ");s.sha=hex(all.digest());break;
                }
                need(magic(header,"COHMSG01")&&s.records<RECORD_LIMIT,"record magic or count differs");read(in,header,8,RECORD-8);h=little(header);
                int bytes=h.getInt(12),command=h.getInt(56),aligned=h.getInt(60),ordered=h.getInt(64),flags=h.getInt(104);long bits=h.getLong(16),cursor=h.getLong(24),time=h.getLong(32),generation=h.getLong(40);
                need(h.getInt(8)==RECORD&&bytes>0&&bytes<=4*1024*1024&&bits>0&&bits<=(long)bytes*8&&cursor>=0&&cursor<=bits&&generation>0&&time>=0&&(s.records==0||time>=s.last)&&(flags==0||flags==1)&&((flags==1)==(command==-1))&&(aligned==0||aligned==1)&&(ordered==0||ordered==1)&&s.bytes+RECORD+bytes+TRAILER<=before.size(),"record framing differs");
                for(int k=108;k<RECORD;k++)need(header[k]==0,"record reserved bits differ");
                byte[] expected=Arrays.copyOfRange(header,72,104);payload.reset();all.update(header,0,RECORD);prefix.update(header,0,RECORD);
                for(int remaining=bytes;remaining>0;){int n=Math.min(remaining,buffer.length);read(in,buffer,0,n);payload.update(buffer,0,n);prefix.update(buffer,0,n);all.update(buffer,0,n);remaining-=n;}
                need(MessageDigest.isEqual(expected,payload.digest()),"payload SHA-256 differs");
                s.records++;s.bytes+=RECORD+bytes;s.payload+=bytes;s.bits+=bits;if(s.records==1)s.first=time;s.last=time;
            }
        }finally{Arrays.fill(header,(byte)0);Arrays.fill(buffer,(byte)0);}
        need(same(before,Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS)),"file changed during validation");return s;
    }
    /** Call on the network owner only after native has finalized and closed its
     * duplicate (normal terminal, cancel or disconnect), before report export. */
    public static synchronized String seal(File base,long appVersion,String activitySession)throws IOException {
        Path dir=directory(base),stage=dir.resolve(TEMP),target=dir.resolve(NAME);Summary summary=inspect(stage);String metadata=summary.metadata(appVersion,activitySession);
        if(Files.exists(target,LinkOption.NOFOLLOW_LINKS))need(Files.isRegularFile(target,LinkOption.NOFOLLOW_LINKS),"target is not regular");
        Files.move(stage,target,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);return metadata;
    }
    /** Validate optional source completely before changing the destination ZIP.
     * Caller also matches app_version/activity_session against its selected report.
     * Actual destination errors propagate rather than returning a successful ZIP. */
    public static synchronized boolean append(File base,ZipOutputStream zip,String expectedSha,long appVersion,String activitySession)throws IOException {
        if(base==null||zip==null||expectedSha==null||!expectedSha.matches("[0-9a-f]{64}"))return false;
        Path path=base.toPath().toAbsolutePath().resolve(NAME);Summary summary;String metadata;
        try{summary=inspect(path);if(!expectedSha.equals(summary.sha))return false;metadata=summary.metadata(appVersion,activitySession);}catch(IOException optional){return false;}
        byte[] buffer=new byte[BUFFER];MessageDigest copied=hash();long bytes=0;
        try(InputStream in=Files.newInputStream(path,LinkOption.NOFOLLOW_LINKS)){
            zip.putNextEntry(new ZipEntry(NAME));int n;while((n=in.read(buffer))!=-1){need(n>0&&bytes+n<=LIMIT,"file grew during ZIP export");zip.write(buffer,0,n);copied.update(buffer,0,n);bytes+=n;}
            need(bytes==summary.bytes&&expectedSha.equals(hex(copied.digest())),"file changed during ZIP export");zip.closeEntry();
            zip.putNextEntry(new ZipEntry("post-ready-replay.json"));zip.write(metadata.getBytes(java.nio.charset.StandardCharsets.UTF_8));zip.closeEntry();return true;
        }finally{Arrays.fill(buffer,(byte)0);}
    }
}
