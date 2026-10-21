package org.coh.nativecombined;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.channels.FileChannel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import java.util.zip.ZipOutputStream;
public final class TestPostReadyReplayStore {
 private static int checks;
 private static void check(boolean ok){checks++;if(!ok)throw new AssertionError("check"+checks);}
 private interface Action{void run()throws Exception;}
 private static void rejected(Action action)throws Exception{boolean refused=false;try{action.run();}catch(IOException expected){refused=true;}check(refused);}
 private static String hex(byte[] value)throws Exception{StringBuilder out=new StringBuilder();for(byte b:value)out.append(String.format(java.util.Locale.ROOT,"%02x",b&255));return out.toString();}
 private static void archive(File base,String sha,boolean accepted,byte[] expected)throws Exception{
  ByteArrayOutputStream bytes=new ByteArrayOutputStream();
  try(ZipOutputStream out=new ZipOutputStream(bytes)){out.putNextEntry(new ZipEntry("essential.json"));out.write(7);out.closeEntry();check(PostReadyReplayStore.append(base,out,sha,20,"session-019")==accepted);out.putNextEntry(new ZipEntry("after.json"));out.write(9);out.closeEntry();}
  try(ZipInputStream zip=new ZipInputStream(new ByteArrayInputStream(bytes.toByteArray()))){check(zip.getNextEntry().getName().equals("essential.json")&&zip.read()==7);if(accepted){check(zip.getNextEntry().getName().equals(PostReadyReplayStore.NAME));ByteArrayOutputStream got=new ByteArrayOutputStream();byte[] buffer=new byte[1024];int n;while((n=zip.read(buffer))!=-1)got.write(buffer,0,n);check(Arrays.equals(expected,got.toByteArray()));check(zip.getNextEntry().getName().equals("post-ready-replay.json"));got.reset();while((n=zip.read(buffer))!=-1)got.write(buffer,0,n);String metadata=new String(got.toByteArray(),java.nio.charset.StandardCharsets.UTF_8);check(metadata.contains("\"records_saved\":115")&&metadata.contains("\"app_version\":20")&&metadata.contains("\"activity_session\":\"session-019\"")&&metadata.contains("\"decoded\":false"));}check(zip.getNextEntry().getName().equals("after.json")&&zip.read()==9&&zip.getNextEntry()==null);}
 }
 public static void main(String[] args)throws Exception{
  check(args.length==2);Path work=new File(args[0]).toPath(),fixture=new File(args[1]).toPath();byte[] raw=Files.readAllBytes(fixture);String sha=hex(MessageDigest.getInstance("SHA-256").digest(raw));File base=work.resolve("store").toFile();Path target=base.toPath().resolve(PostReadyReplayStore.NAME);
  File stage=PostReadyReplayStore.prepare(base);check(stage.length()==0);Files.write(stage.toPath(),raw);String metadata=PostReadyReplayStore.seal(base,20,"session-019");check(metadata.contains("\"window_complete\":true")&&metadata.contains("\"messages_complete\":true")&&metadata.contains("\"records_saved\":115")&&metadata.contains("\"per_record_metadata\":\"binary record headers\"")&&!metadata.contains("\"records\":["));check(!stage.exists()&&Files.size(target)==raw.length);archive(base,sha,true,raw);
  archive(base,null,false,null);archive(base,"",false,null);archive(base,sha.toUpperCase(java.util.Locale.ROOT),false,null);archive(base,String.join("",java.util.Collections.nCopies(64,"0")),false,null);
  for(int offset:new int[]{0,8,20,48,64,76,80,120,136,176,raw.length-32}){byte[] changed=raw.clone();changed[offset]^=1;Files.write(stage.toPath(),changed);rejected(()->PostReadyReplayStore.seal(base,20,"session-019"));check(Arrays.equals(raw,Files.readAllBytes(target)));}
  for(int length:new int[]{0,159,raw.length-1,raw.length+1}){Files.write(stage.toPath(),Arrays.copyOf(raw,length));rejected(()->PostReadyReplayStore.seal(base,20,"session-019"));}
  Files.write(stage.toPath(),raw);rejected(()->PostReadyReplayStore.seal(base,-1,"session-019"));rejected(()->PostReadyReplayStore.seal(base,20,"bad\nidentity"));rejected(()->PostReadyReplayStore.seal(base,20,null));
  byte[] partial=raw.clone();ByteBuffer b=ByteBuffer.wrap(partial).order(ByteOrder.LITTLE_ENDIAN);b.putInt(raw.length-96+24,32);b.putInt(raw.length-96+28,0);Files.write(stage.toPath(),partial);String partialMetadata=PostReadyReplayStore.seal(base,20,"session-partial");check(partialMetadata.contains("\"window_complete\":false")&&partialMetadata.contains("\"messages_complete\":false")&&partialMetadata.contains("\"reason_flags\":32"));
  Files.write(stage.toPath(),raw);PostReadyReplayStore.seal(base,20,"session-019");Path outside=work.resolve("outside.bin");Files.write(outside,new byte[]{1,2,3});Files.createSymbolicLink(stage.toPath(),outside.toAbsolutePath());rejected(()->PostReadyReplayStore.seal(base,20,"session-019"));PostReadyReplayStore.clear(base);check(Arrays.equals(Files.readAllBytes(outside),new byte[]{1,2,3}));check(!Files.exists(target));
  Files.createSymbolicLink(target,outside.toAbsolutePath());archive(base,sha,false,null);PostReadyReplayStore.clear(base);check(Arrays.equals(Files.readAllBytes(outside),new byte[]{1,2,3}));
  stage=PostReadyReplayStore.prepare(base);try(FileChannel channel=FileChannel.open(stage.toPath(),StandardOpenOption.WRITE)){channel.position(8*1024*1024);channel.write(ByteBuffer.wrap(new byte[]{1}));}rejected(()->PostReadyReplayStore.seal(base,20,"session-019"));PostReadyReplayStore.clear(base);
  System.out.println("{\"passed\":true,\"checks\":"+checks+",\"cross_language_records\":115,\"scratch_bytes\":16384,\"disk_limit\":8388608,\"decoded\":false}");
 }
}
