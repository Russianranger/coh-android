package org.coh.nativecombined;
import java.io.*;
import java.nio.*;
import java.nio.file.*;
import java.security.*;
import java.util.*;
import java.util.zip.*;
public final class TestInitialReplayStore {
    private static int checks;
    private static void check(boolean value){checks++;if(!value)throw new AssertionError("check "+checks);}
    private interface Action {void run()throws Exception;}
    private static void rejected(Action action)throws Exception {boolean rejected=false;try{action.run();}catch(IOException expected){rejected=true;}check(rejected);}
    private static byte[] frame(int payload)throws Exception {
        byte[] bytes=new byte[88+payload];for(int i=88;i<bytes.length;i++)bytes[i]=(byte)i;
        ByteBuffer b=ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN);b.put("COHIRP01".getBytes("US-ASCII"));b.putInt(8,88);b.putInt(12,payload);b.putLong(16,payload*8L);b.putLong(24,3);b.putLong(32,0);b.putInt(40,0);b.putInt(44,-1);b.putInt(48,28);b.putInt(52,3);
        MessageDigest digest=MessageDigest.getInstance("SHA-256");digest.update(bytes,88,payload);System.arraycopy(digest.digest(),0,bytes,56,32);return bytes;
    }
    private static void archive(File dir,byte[] expected)throws Exception {
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();try(ZipOutputStream out=new ZipOutputStream(bytes)){check(InitialReplayStore.append(dir,out));}
        try(ZipInputStream zip=new ZipInputStream(new ByteArrayInputStream(bytes.toByteArray()))){ZipEntry entry=zip.getNextEntry();check(entry!=null&&entry.getName().equals("initial-replay.bin"));ByteArrayOutputStream actual=new ByteArrayOutputStream();byte[] buffer=new byte[1024];int n;while((n=zip.read(buffer))!=-1)actual.write(buffer,0,n);check(Arrays.equals(actual.toByteArray(),expected)&&zip.getNextEntry()==null);}
    }
    private static String frameHash(byte[] bytes)throws Exception {
        StringBuilder value=new StringBuilder();for(byte b:MessageDigest.getInstance("SHA-256").digest(bytes))value.append(String.format(Locale.ROOT,"%02x",b&255));return value.toString();
    }
    private static void boundArchive(File dir,String expected,boolean admitted,byte[] raw)throws Exception {
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        try(ZipOutputStream out=new ZipOutputStream(bytes)){
            out.putNextEntry(new ZipEntry("essential.json"));out.write(7);out.closeEntry();
            check(InitialReplayStore.append(dir,out,expected)==admitted);
            out.putNextEntry(new ZipEntry("after.json"));out.write(8);out.closeEntry();
        }
        try(ZipInputStream zip=new ZipInputStream(new ByteArrayInputStream(bytes.toByteArray()))){
            check(zip.getNextEntry().getName().equals("essential.json")&&zip.read()==7);
            if(admitted){check(zip.getNextEntry().getName().equals("initial-replay.bin"));ByteArrayOutputStream actual=new ByteArrayOutputStream();byte[] buffer=new byte[1024];int n;while((n=zip.read(buffer))!=-1)actual.write(buffer,0,n);check(Arrays.equals(actual.toByteArray(),raw));}
            check(zip.getNextEntry().getName().equals("after.json")&&zip.read()==8&&zip.getNextEntry()==null);
        }
    }
    public static void main(String[] args)throws Exception {
        check(args.length==1);File dir=new File(args[0],"replay");Path target=dir.toPath().resolve("initial-replay.bin");
        byte[] shortFrame=frame(1),largeFrame=frame(65536);String metadata=InitialReplayStore.save(dir,shortFrame,17,"session-01");
        check(metadata.contains("\"app_version\":17")&&metadata.contains("\"activity_session\":\"session-01\"")&&metadata.contains("\"logical_bits\":8"));archive(dir,shortFrame);
        String shortHash=frameHash(shortFrame);boundArchive(dir,shortHash,true,shortFrame);
        for(String expected:new String[]{null,"",shortHash.substring(1),shortHash.toUpperCase(Locale.ROOT),String.join("",Collections.nCopies(64,"0"))})boundArchive(dir,expected,false,null);
        InitialReplayStore.save(dir,largeFrame,17,"session-02");archive(dir,largeFrame);check(Files.size(target)==65624);
        boundArchive(dir,shortHash,false,null);boundArchive(dir,frameHash(largeFrame),true,largeFrame);
        for(int field:new int[]{8,12,16,24,32,40,44,48,52}) {
            byte[] changed=largeFrame.clone();ByteBuffer b=ByteBuffer.wrap(changed).order(ByteOrder.LITTLE_ENDIAN);
            if(field==8)b.putInt(field,87);else if(field==12)b.putInt(field,65535);else if(field==16)b.putLong(field,524289);else if(field==24||field==32)b.putLong(field,524289);else if(field==40)b.putInt(field,2);else if(field==44)b.putInt(field,10);else if(field==48)b.putInt(field,30);else b.putInt(field,41);
            rejected(()->InitialReplayStore.save(dir,changed,17,"session-03"));check(Arrays.equals(Files.readAllBytes(target),largeFrame));
        }
        for(int offset:new int[]{0,56,88}){byte[] changed=largeFrame.clone();changed[offset]^=1;rejected(()->InitialReplayStore.save(dir,changed,17,"session-03"));}
        rejected(()->InitialReplayStore.save(dir,null,17,"session-03"));rejected(()->InitialReplayStore.save(dir,Arrays.copyOf(largeFrame,65625),17,"session-03"));rejected(()->InitialReplayStore.save(dir,Arrays.copyOf(largeFrame,87),17,"session-03"));
        rejected(()->InitialReplayStore.save(dir,largeFrame,-1,"session-03"));rejected(()->InitialReplayStore.save(dir,largeFrame,17,null));rejected(()->InitialReplayStore.save(dir,largeFrame,17,"bad\nidentity"));
        byte[] aligned=largeFrame.clone();ByteBuffer b=ByteBuffer.wrap(aligned).order(ByteOrder.LITTLE_ENDIAN);b.putInt(40,1);rejected(()->InitialReplayStore.save(dir,aligned,17,"session-03"));b.putLong(24,8);b.putLong(32,16);b.putInt(44,9);InitialReplayStore.save(dir,aligned,17,"session-04");archive(dir,aligned);
        Files.write(target,Arrays.copyOf(aligned,87));rejected(()->{try(ZipOutputStream zip=new ZipOutputStream(new ByteArrayOutputStream())){InitialReplayStore.append(dir,zip);}});InitialReplayStore.clear(dir);check(!Files.exists(target));
        boundArchive(dir,shortHash,false,null);
        Path outside=new File(args[0],"outside.bin").toPath();Files.write(outside,new byte[]{9,8,7});Files.createSymbolicLink(target,outside.toAbsolutePath());rejected(()->InitialReplayStore.save(dir,largeFrame,17,"session-05"));
        boundArchive(dir,shortHash,false,null);
        rejected(()->{try(ZipOutputStream zip=new ZipOutputStream(new ByteArrayOutputStream())){InitialReplayStore.append(dir,zip);}});InitialReplayStore.clear(dir);check(Arrays.equals(Files.readAllBytes(outside),new byte[]{9,8,7}));
        Path alias=new File(args[0],"alias").toPath();Files.createSymbolicLink(alias,dir.toPath().toAbsolutePath());rejected(()->InitialReplayStore.save(alias.toFile(),largeFrame,17,"session-05"));
        try(ZipOutputStream zip=new ZipOutputStream(new ByteArrayOutputStream())){check(!InitialReplayStore.append(dir,zip));}
        check(!Files.exists(dir.toPath().resolve("initial-replay.tmp")));
        System.out.println("{\"passed\":true,\"checks\":"+checks+",\"maximum_frame_bytes\":65624,\"payload_limit\":65536,\"files_retained\":0,\"physical_packet_replayed\":false}");
    }
}
