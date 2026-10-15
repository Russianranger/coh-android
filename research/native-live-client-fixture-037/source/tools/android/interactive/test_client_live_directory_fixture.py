"""Actual release-8 JVM raw packet, parity and owned-runner source controls.

All Process, nofollow custody, JNI and packaged-execution attestations below are
explicit typed host mocks. They do not qualify Android, PRoot, Wine, FEX, current
asset aliases/sharing/retarget, a native SDK consumer or production admission.
The existing frozen finalized ClientRuntime command is compiled into the harness.
"""
from pathlib import Path
import hashlib
import subprocess
import tempfile
import unittest
import test_client_guest_namespace as namespace_fixture

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
SOURCE = JAVA / 'ClientLiveDirectoryFixture.java'
SOURCES = [JAVA / name for name in (
    'ClientGuestNamespace.java', 'NativeLiveDirectory.java', 'ClientLiveDirectoryService.java',
    'ClientLiveDirectoryOperation.java', 'ClientLiveDirectoryFixture.java')]

HARNESS = r'''
 static final byte[] OP=new byte[]{1,35,69,103,(byte)137,(byte)171,(byte)205,(byte)239,1,35,69,103,(byte)137,(byte)171,(byte)205,(byte)239}, TOKEN=new byte[16];
 static final String FIXTURE_NAME="coh-live-fixture-0123456789abcdef0123456789abcdef";
 static java.nio.ByteBuffer le(byte[] data){return java.nio.ByteBuffer.wrap(data).order(java.nio.ByteOrder.LITTLE_ENDIAN);}
 static byte[] nativeRow(String name,long size,long write,int attrs,int next){
  byte[] text=name.getBytes(StandardCharsets.UTF_16LE),raw=new byte[94+text.length];java.nio.ByteBuffer b=le(raw);
  b.putInt(0,next);b.putLong(24,write);b.putLong(40,size);b.putInt(56,attrs);b.putInt(60,text.length);
  System.arraycopy(text,0,raw,94,text.length);return raw;
 }
 static List<String> names(int count){List<String> out=new ArrayList<String>();
  if(count==0)return out;out.add(".");if(count>1)out.add("..");
  for(int i=2;i<count;i++)out.add(String.format(Locale.ROOT,"f%03d.fx",i));return out;
 }
 static List<List<String>> partitions(List<String> names){List<List<String>> out=new ArrayList<List<String>>();int used=0;
  List<String> current=new ArrayList<String>();for(String name:names){int next=((used+7)&~7)+94+name.length()*2;
   if(next>8192){out.add(current);current=new ArrayList<String>();used=0;next=94+name.length()*2;}
   current.add(name);used=next;}if(!current.isEmpty())out.add(current);return out;
 }
 static byte[] ntPayload(List<String> names,int first)throws Exception {
  ByteArrayOutputStream out=new ByteArrayOutputStream();for(int i=0;i<names.size();i++){
   String name=names.get(i);int length=94+name.length()*2,next=i+1==names.size()?0:(length+7)&~7;
   int attr=first+i<2?16:0x27;byte[] row=nativeRow(name,first+i<2?0:0x100000000L+first+i,
    132000000000000000L+first+i,attr,next);out.write(row);if(next>length)out.write(new byte[next-length]);}
  return out.toByteArray();
 }
 static String dos(String guest,boolean finalPath){return(finalPath?"\\\\?\\":"")+"Z:"+guest.replace('/','\\');}
 static byte[] packet(String guest,String resolved,long inode,int count,int mode,boolean complete)throws Exception {
  byte[] path=dos(guest,false).getBytes(StandardCharsets.US_ASCII),finalPath=dos(resolved,true).getBytes(StandardCharsets.US_ASCII);
  byte[] header=new byte[96];java.nio.ByteBuffer b=le(header);b.put("COHNTB1\0".getBytes(StandardCharsets.US_ASCII));
  b.putInt(8,1);b.putInt(12,mode);b.putInt(16,77);b.putInt(20,88);b.putLong(32,inode);
  b.putInt(48,path.length);b.putInt(52,finalPath.length);b.putInt(56,8192);b.putInt(60,256);b.putInt(64,32);b.putInt(68,512*1024);
  ByteArrayOutputStream out=new ByteArrayOutputStream();out.write(header);out.write(path);out.write(finalPath);
  List<List<String>> parts=mode==1?partitions(names(count)):Collections.<List<String>>emptyList();int first=0;
  for(int i=0;i<parts.size();i++) {byte[] raw=ntPayload(parts.get(i),first),envelope=new byte[24];le(envelope)
    .put("NTBATCH1".getBytes(StandardCharsets.US_ASCII)).putInt(i).putInt(0).putInt(raw.length).putInt(parts.get(i).size());
   out.write(envelope);out.write(raw);first+=parts.get(i).size();}
  byte[] footer=new byte[40];le(footer).put("NTEND1\0\0".getBytes(StandardCharsets.US_ASCII)).putInt(1).putInt(complete?1:0)
   .putInt(parts.size()).putInt(first).putInt(mode==1?0x80000006:0xc0000001).putInt(0).putInt(out.size()+40).putInt(0);
  out.write(footer);return out.toByteArray();
 }
 static byte[] bridge(List<String> names,int number,int first,boolean done,byte[] op,byte[] token){
  byte[] raw=new byte[64+names.size()*328];java.nio.ByteBuffer b=le(raw);
  b.put("COHLIVE1".getBytes(StandardCharsets.US_ASCII)).put(op).put(token).putInt(number).putInt(first).putInt(names.size())
   .putInt(done?1:0).putInt(0).putInt(raw.length);
  for(int i=0;i<names.size();i++){int at=64+i*328,wfd=at+8;b.putInt(at,first+i);b.putInt(wfd,first+i<2?16:0x27);
   b.putLong(wfd+20,132000000000000000L+first+i);b.putInt(wfd+28,first+i<2?0:1);b.putInt(wfd+32,first+i<2?0:first+i);
   byte[] name=names.get(i).getBytes(StandardCharsets.US_ASCII);System.arraycopy(name,0,raw,wfd+44,name.length);}
  return raw;
 }
 static List<ClientLiveDirectoryFixture.BridgeBatch> transcript(int count)throws Exception {
  List<List<String>> parts=partitions(names(count));List<ClientLiveDirectoryFixture.BridgeBatch> out=new ArrayList<ClientLiveDirectoryFixture.BridgeBatch>();
  if(parts.isEmpty()){out.add(ClientLiveDirectoryFixture.parseBridge(bridge(Collections.<String>emptyList(),0,0,true,OP,TOKEN),OP,TOKEN,0,0));return out;}
  int first=0;for(int i=0;i<parts.size();i++){out.add(ClientLiveDirectoryFixture.parseBridge(bridge(parts.get(i),i,first,i+1==parts.size(),OP,TOKEN),OP,TOKEN,i,first));first+=parts.get(i).size();}return out;
 }
 static ClientLiveDirectoryFixture.DirectoryWitness witness()throws Exception{return new ClientLiveDirectoryFixture.DirectoryWitness(DATA+"/fx/"+FIXTURE_NAME,DATA+"/fx/"+FIXTURE_NAME,7,99,10303);}
 static ClientLiveDirectoryFixture.Pins pins(Fixture f)throws Exception{return new ClientLiveDirectoryFixture.Pins(build(f),repeat('d',64),repeat('e',64),126000,
  repeat('f',64),repeat('1',64),repeat('2',64),29992,repeat('3',64),repeat('4',64),repeat('5',64),repeat('6',64),7);}
 static final class MockFixture implements ClientLiveDirectoryFixture.OwnedFixture {
  final List<ClientLiveDirectoryFixture.DirectoryCase> dirs=new ArrayList<ClientLiveDirectoryFixture.DirectoryCase>();
  int validations,closed,currentCalls;boolean changed,closeError,delayFinal;MockFixture()throws Exception {
   String[] labels={"state_fx","state_loc","import_fx","import_loc"};for(int i=0;i<4;i++){
    String root=i<2?DATA:"/game-import/data",path=root+(i%2==0?"/fx/":"/scripts.loc/")+FIXTURE_NAME;
    byte[] token=TOKEN.clone();token[0]=(byte)(i+1);
    dirs.add(new ClientLiveDirectoryFixture.DirectoryCase(labels[i],new ClientLiveDirectoryFixture.DirectoryWitness(path,path,7,99+i,10303),token));}
  }
  public long namespace(){return 100;}public List<ClientLiveDirectoryFixture.DirectoryCase> cases(){return dirs;}
  public ClientLiveDirectoryFixture.DirectoryWitness current(ClientLiveDirectoryFixture.DirectoryCase d)throws IOException {
   currentCalls++;return changed&&currentCalls>1?new ClientLiveDirectoryFixture.DirectoryWitness(d.identity.requestedGuest,d.identity.resolvedGuest,7,d.identity.inode+1,10303):d.identity;}
  public void revalidate()throws IOException{validations++;if(delayFinal&&validations==16)try{Thread.sleep(600);}catch(InterruptedException e){Thread.currentThread().interrupt();throw new IOException(e);}}
  public void close()throws IOException{closed++;if(closeError)throw new IOException("PRIVATE_OWNED_FIXTURE_PATH");}
 }
 static final class MockApi implements ClientLiveDirectoryOperation.NativeApi {
  final MockFixture fixture;final Map<Long,ClientLiveDirectoryFixture.DirectoryCase> owned=new HashMap<Long,ClientLiveDirectoryFixture.DirectoryCase>();
  final Map<Long,Integer> sequence=new HashMap<Long,Integer>();int opened,nextCalls,closed;int rowCount=130;
  boolean wrongInode,wrongUid,wrongDevice,wrongTarget,lateFailure,wrongFields,closeError,delayFinal;
  MockApi(MockFixture f){fixture=f;}
  public long create(String[] g,String[] h,long[] d,long[] i,int[] u,int n,int v,boolean dot,boolean sensitive){throw new AssertionError("fixture custody exclusively owns namespace creation");}
  public long open(long ns,String path,byte[] operation,byte[] token)throws IOException{
   require(ns==100&&Arrays.equals(operation,OP),"owned namespace attribution");
   for(ClientLiveDirectoryFixture.DirectoryCase d:fixture.dirs)if(d.identity.requestedGuest.equals(path)){require(Arrays.equals(token,d.token()),"current frozen cursor tag");long h=200+opened++;owned.put(h,d);sequence.put(h,0);return h;}
   throw new IOException("outside fixture");}
  public byte[] next(long h)throws IOException {
   nextCalls++;if(lateFailure&&nextCalls==2)throw new OutOfMemoryError("PRIVATE_ADVANCED_CURSOR_MESSAGE");
   int number=sequence.get(h),first=0;List<List<String>> parts=partitions(names(rowCount));
   if(parts.isEmpty()){sequence.put(h,1);return bridge(Collections.<String>emptyList(),0,0,true,OP,owned.get(h).token());}
   require(number<parts.size(),"never repeat native cursor after final");for(int i=0;i<number;i++)first+=parts.get(i).size();
   byte[] raw=bridge(parts.get(number),number,first,number+1==parts.size(),OP,owned.get(h).token());sequence.put(h,number+1);
   if(delayFinal&&opened==4&&number+1==parts.size())try{Thread.sleep(600);}catch(InterruptedException e){Thread.currentThread().interrupt();throw new IOException(e);}
   if(wrongFields)le(raw).putInt(64+8+32,99);return raw;}
  public long[] identity(long h){return new long[]{wrongDevice?8:7,owned.get(h).identity.inode+(wrongInode?1:0),wrongUid?10304:10303};}
  public String canonicalGuestPath(long h){return owned.get(h).identity.resolvedGuest+(wrongTarget?"x":"");}
  public void closeCursor(long h)throws IOException{closed++;owned.remove(h);if(closeError)throw new IOException("PRIVATE_CURSOR_PATH");}
  public void closeNamespace(long n){throw new AssertionError("fixture adapter owns namespace release");}
  public long[] stats(long n){return new long[]{0,0,0,0,0,0};}
 }
 static final class MockProcess extends Process {
  final InputStream out,err;final OutputStream in=new ByteArrayOutputStream();boolean waited,destroyed;int exit;boolean timeout,interrupted;
  MockProcess(byte[] stdout,byte[] stderr){this(new ByteArrayInputStream(stdout),new ByteArrayInputStream(stderr));}
  MockProcess(InputStream stdout,InputStream stderr){out=stdout;err=stderr;}
  public OutputStream getOutputStream(){return in;}public InputStream getInputStream(){return out;}public InputStream getErrorStream(){return err;}
  public int waitFor()throws InterruptedException{if(interrupted)throw new InterruptedException();waited=true;return exit;}
  public boolean waitFor(long value,java.util.concurrent.TimeUnit unit)throws InterruptedException {if(interrupted)throw new InterruptedException();waited=true;return !timeout;}
  public int exitValue(){require(waited,"process wait owns current completion");return exit;}
  public void destroy(){destroyed=true;}
 }
 static final class StuckConsole extends InputStream {
  boolean closed;
  public synchronized int read()throws IOException {while(!closed)try{wait();}catch(InterruptedException e){throw new IOException(e);}return -1;}
  public synchronized int read(byte[] b)throws IOException{return read();}
  public synchronized void close(){closed=true;notifyAll();}
 }
 static final class PartialConsole extends InputStream {
  boolean first=true;public int read()throws IOException{throw new IOException("partial failure");}
  public int read(byte[] out)throws IOException {if(!first)throw new IOException("PRIVATE_PARTIAL_CONSOLE_PATH");first=false;byte[] raw="partial native evidence\n".getBytes(StandardCharsets.US_ASCII);System.arraycopy(raw,0,out,0,raw.length);return raw.length;}
 }
 static final class CloseErrorConsole extends InputStream {
  int closes;public int read(){return -1;}public int read(byte[] b){return -1;}
  public void close(){closes++;if(closes==1)throw new AssertionError("controlled console close Error");}
 }
 static final class CloseErrorFile extends FileInputStream {
  int closes;CloseErrorFile(File file)throws IOException{super(file);}
  public void close()throws IOException{closes++;if(closes==1)throw new AssertionError("controlled file close Error");super.close();}
 }
 static final class MockProbe implements ClientLiveDirectoryFixture.OwnedProbe {
  final MockProcess held;final byte[] raw;final File output;int closed,verified;boolean verificationError,cleanupError,packetCloseError;
  MockProbe(MockProcess child,byte[] packet)throws IOException{
   held=child;raw=packet;output=File.createTempFile("coh-tiny-owned-NT-",".bin");
   try(FileOutputStream stream=new FileOutputStream(output)){stream.write(raw);}output.deleteOnExit();
  }
  public Process process(){return held;}
  public ClientLiveDirectoryFixture.PacketFile packet()throws IOException {
   return new ClientLiveDirectoryFixture.PacketFile(packetCloseError?new CloseErrorFile(output):new FileInputStream(output),fd->new ClientLiveDirectoryFixture.PacketIdentity(7,1234,10303,0100600,output.length()),10303,7);
  }
  public void verifyCurrent(ClientLiveDirectoryFixture.Pins pins,ClientLiveDirectoryFixture.NtObservation packet,Process actual)throws IOException {
   verified++;require(actual==held&&packet.pid==77&&packet.thread==88,"typed HOST mock attribution only");
   if(verificationError)throw new IOException("PRIVATE_NATIVE_PROCESS_PATH");}
  public void close()throws IOException {closed++;held.destroy();held.getInputStream().close();held.getErrorStream().close();held.getOutputStream().close();if(cleanupError)throw new IOException("PRIVATE_PROBE_CLEANUP_PATH");}
 }
 static final class MockStarter implements ClientLiveDirectoryFixture.ProbeStarter {
  final List<MockProbe> probes=new ArrayList<MockProbe>();int count=130;String failure;
  public ClientLiveDirectoryFixture.OwnedProbe start(ClientLiveDirectoryFixture.Pins current,ClientLiveDirectoryFixture.DirectoryCase d)throws IOException {
   try{byte[] raw=packet(d.identity.requestedGuest,d.identity.resolvedGuest,d.identity.inode,count,1,true);
    if("malformed".equals(failure))raw[0]='X';
    String stdout="COH_NT_PROBE_RESULT pid=77 mode=1 complete=1 rows="+count+" batches="+partitions(names(count)).size()+" input_cleanup_failed=0 bytes="+raw.length+"\n";
    if("console".equals(failure))stdout=stdout.replace("pid=77","pid=78");
    if("duplicate_console".equals(failure))stdout+=stdout;
    MockProcess child="close_error_console".equals(failure)?new MockProcess(new CloseErrorConsole(),new ByteArrayInputStream(new byte[0])):
     "stuck_console".equals(failure)?new MockProcess(new StuckConsole(),new ByteArrayInputStream(new byte[0])):
     "partial_console".equals(failure)?new MockProcess(new PartialConsole(),new ByteArrayInputStream(new byte[0])):
     new MockProcess(("huge_console".equals(failure)?repeat('x',33000):stdout).getBytes(StandardCharsets.US_ASCII),new byte[0]);
    child.timeout="timeout".equals(failure);child.interrupted="interrupt".equals(failure);child.exit="exit".equals(failure)?1:0;
    MockProbe probe=new MockProbe(child,raw);probe.verificationError="attribution".equals(failure);probe.cleanupError="cleanup".equals(failure);probe.packetCloseError="packet_close_error".equals(failure);
    probes.add(probe);return probe;
   }catch(Exception problem){throw new IOException(problem);}
  }
 }
 static void expectNtRefusal(byte[] raw)throws Exception{refusal(new Checked(){public void run()throws Exception{ClientLiveDirectoryFixture.parseNt(raw);}});}
 static void expectBridgeRefusal(byte[] raw)throws Exception{refusal(new Checked(){public void run()throws Exception{ClientLiveDirectoryFixture.parseBridge(raw,OP,TOKEN,0,0);}});}
 static void mainCase(String name,File base)throws Exception {
  ClientLiveDirectoryFixture.DirectoryWitness w=witness();byte[] stock=packet(w.requestedGuest,w.resolvedGuest,w.inode,130,1,true);
  if(name.equals("parity")) {
   ClientLiveDirectoryFixture.NtObservation nt=ClientLiveDirectoryFixture.parseNt(stock);require(nt.rows.size()==130&&nt.batches.size()==2,"real JVM 8KiB partitions");
   ClientLiveDirectoryFixture.compare(nt,transcript(130),w);require(nt.rows.get(2).sizeLow==2&&nt.rows.get(2).attributes==7,"low-size and consumed attr scope");
  } else if(name.equals("empty")) {
   ClientLiveDirectoryFixture.compare(ClientLiveDirectoryFixture.parseNt(packet(w.requestedGuest,w.resolvedGuest,w.inode,0,1,true)),transcript(0),w);
  } else if(name.equals("nt_truncation")) {
   for(int i=0;i<stock.length;i++)expectNtRefusal(Arrays.copyOf(stock,i));expectNtRefusal(Arrays.copyOf(stock,stock.length+1));
  } else if(name.startsWith("nt_")) {
   byte[] changed=stock.clone();int start=96+le(stock).getInt(48)+le(stock).getInt(52),payload=start+24;
   if(name.equals("nt_magic"))changed[0]='X';else if(name.equals("nt_reserved"))changed[24]=1;
   else if(name.equals("nt_caps"))le(changed).putInt(60,257);else if(name.equals("nt_pid"))le(changed).putInt(16,0);
   else if(name.equals("nt_batch_sequence"))le(changed).putInt(start+8,1);
   else if(name.equals("nt_batch_status"))le(changed).putInt(start+12,1);
   else if(name.equals("nt_next"))le(changed).putInt(payload,1);
   else if(name.equals("nt_unicode")){changed[payload+95]=1;}
   else if(name.equals("nt_footer"))le(changed).putInt(changed.length-24,0);
   else if(name.equals("nt_eof"))le(changed).putInt(changed.length-16,0);
   else if(name.equals("nt_cleanup"))le(changed).putInt(changed.length-12,1);
   else if(name.equals("nt_open_status"))le(changed).putInt(40,1);
   else if(name.equals("nt_incomplete")){le(changed).putInt(changed.length-28,0);ClientLiveDirectoryFixture.NtObservation failed=ClientLiveDirectoryFixture.parseNt(changed);
    require(!failed.complete,"incomplete packet preserved");refusal(new Checked(){public void run()throws Exception{ClientLiveDirectoryFixture.compare(failed,transcript(130),w);}});return;}
   else throw new AssertionError(name);expectNtRefusal(changed);
  } else if(name.equals("sharing_scope")) {
   ClientLiveDirectoryFixture.NtObservation shared=ClientLiveDirectoryFixture.parseNt(packet(w.requestedGuest,w.resolvedGuest,w.inode,0,2,true));
   require(shared.mode==2&&shared.rows.isEmpty(),"sharing is separately observed");refusal(new Checked(){public void run()throws Exception{ClientLiveDirectoryFixture.compare(shared,transcript(0),w);}});
  } else if(name.startsWith("bridge_")) {
   byte[] changed=bridge(names(3),0,0,true,OP,TOKEN);
   if(name.equals("bridge_magic"))changed[0]='X';else if(name.equals("bridge_operation"))changed[8]=2;
   else if(name.equals("bridge_token"))changed[24]=1;else if(name.equals("bridge_sequence"))le(changed).putInt(40,1);
   else if(name.equals("bridge_first"))le(changed).putInt(44,1);else if(name.equals("bridge_reserved"))le(changed).putInt(56,1);
   else if(name.equals("bridge_total"))le(changed).putInt(60,0);else if(name.equals("bridge_ordinal"))le(changed).putInt(64,1);
   else if(name.equals("bridge_name"))changed[64+8+44]='/';else if(name.equals("bridge_padding"))changed[64+8+50]=1;
   else if(name.equals("bridge_creation"))changed[64+8+4]=1;else if(name.equals("bridge_short"))changed[64+8+304]=1;
   else if(name.equals("bridge_empty"))changed=bridge(Collections.<String>emptyList(),0,0,false,OP,TOKEN);
   else if(name.equals("bridge_geometry")){List<String> longNames=new ArrayList<String>();for(int i=0;i<20;i++)longNames.add(repeat('x',259));changed=bridge(longNames,0,0,true,OP,TOKEN);}
   else throw new AssertionError(name);expectBridgeRefusal(changed);
  } else if(name.startsWith("field_")) {
   byte[] raw=bridge(names(3),0,0,true,OP,TOKEN);int wfd=64+2*328+8;
   if(name.equals("field_size"))le(raw).putInt(wfd+32,99);else if(name.equals("field_time"))le(raw).putLong(wfd+20,132000000000000099L);
   else if(name.equals("field_attrs"))le(raw).putInt(wfd,16);else if(name.equals("field_name"))raw[wfd+44]='g';
   else throw new AssertionError(name);
   List<ClientLiveDirectoryFixture.BridgeBatch> t=Collections.singletonList(ClientLiveDirectoryFixture.parseBridge(raw,OP,TOKEN,0,0));
   ClientLiveDirectoryFixture.NtObservation nt=ClientLiveDirectoryFixture.parseNt(packet(w.requestedGuest,w.resolvedGuest,w.inode,3,1,true));
   refusal(new Checked(){public void run()throws Exception{ClientLiveDirectoryFixture.compare(nt,t,w);}});
  } else if(name.equals("unused_size_high")) {
   byte[] raw=bridge(names(3),0,0,true,OP,TOKEN);le(raw).putInt(64+2*328+8+28,999);
   ClientLiveDirectoryFixture.compare(ClientLiveDirectoryFixture.parseNt(packet(w.requestedGuest,w.resolvedGuest,w.inode,3,1,true)),
    Collections.singletonList(ClientLiveDirectoryFixture.parseBridge(raw,OP,TOKEN,0,0)),w);
  } else if(name.equals("transcript_no_double_delivery")) {
   ClientLiveDirectoryFixture.NtObservation nt=ClientLiveDirectoryFixture.parseNt(stock);List<ClientLiveDirectoryFixture.BridgeBatch> t=transcript(130);
   List<ClientLiveDirectoryFixture.BridgeBatch> duplicate=new ArrayList<ClientLiveDirectoryFixture.BridgeBatch>(t);duplicate.add(t.get(1));
   refusal(new Checked(){public void run()throws Exception{ClientLiveDirectoryFixture.compare(nt,duplicate,w);}});
   refusal(new Checked(){public void run()throws Exception{ClientLiveDirectoryFixture.compare(nt,t.subList(0,1),w);}});
   List<ClientLiveDirectoryFixture.BridgeBatch> reversed=new ArrayList<ClientLiveDirectoryFixture.BridgeBatch>(t);Collections.reverse(reversed);
   refusal(new Checked(){public void run()throws Exception{ClientLiveDirectoryFixture.compare(nt,reversed,w);}});
  } else if(name.equals("changed_inode")) {
   ClientLiveDirectoryFixture.DirectoryWitness changed=new ClientLiveDirectoryFixture.DirectoryWitness(w.requestedGuest,w.resolvedGuest,7,100,10303);
   refusal(new Checked(){public void run()throws Exception{ClientLiveDirectoryFixture.compare(ClientLiveDirectoryFixture.parseNt(stock),transcript(130),changed);}});
  } else if(name.equals("paths")) {
   require(ClientLiveDirectoryFixture.dosGuest("Z:\\state\\exact",false).equals("/state/exact"),"Z projection");
   for(final String path:new String[]{"C:\\state\\exact","z:\\state\\exact","Z:\\state\\..\\profile","Z:\\state\\a\\","Z:\\state\\a.l2s.abc","Z:\\state\\a\\\\b"})
    refusal(new Checked(){public void run()throws Exception{ClientLiveDirectoryFixture.dosGuest(path,false);}});
  } else if(name.equals("stream_bounds")) {
   require(ClientLiveDirectoryFixture.readBounded(new ByteArrayInputStream(new byte[512*1024]),512*1024).length==512*1024,"exact bound");
   refusal(new Checked(){public void run()throws Exception{ClientLiveDirectoryFixture.readBounded(new ByteArrayInputStream(new byte[512*1024+1]),512*1024);}});
   refusal(new Checked(){public void run()throws Exception{ClientLiveDirectoryFixture.readBounded(new InputStream(){public int read(){return 0;}public int read(byte[] b){return 0;}},512*1024);}});
  } else if(name.equals("pins_and_wire")) {
   Fixture f=fixture(base);ClientLiveDirectoryFixture.Pins p=pins(f);MockFixture owned=new MockFixture();MockApi api=new MockApi(owned);MockStarter starter=new MockStarter();
   byte[] stale=OP.clone();stale[0]^=1;
   ClientLiveDirectoryFixture.Receipt failed=ClientLiveDirectoryFixture.run(p,stale,identity->owned,starter,api,1000);
   require(!failed.comparisonPassed()&&owned.closed==0&&api.opened==0,"mismatched session refused before fixture prepare");
   byte[] mutable=OP.clone();ClientLiveDirectoryFixture.Receipt good=ClientLiveDirectoryFixture.run(p,mutable,identity->{mutable[0]^=1;return owned;},starter,api,1000);
   require(good.comparisonPassed()&&mutable[0]!=OP[0],"operation frozen before caller mutation");
   Fixture changed=new Fixture(base,true,false,false,true,RUN,SESSION,PROCESS,10303,repeat('a',64),repeat('b',64),9487872,repeat('9',64));
   require(!good.matchesCurrent(pins(changed)),"cached receipt cannot conceal a changed compiled helper");
  } else if(name.equals("duplicate_tokens")) {
   Fixture f=fixture(base);ClientLiveDirectoryFixture.Pins p=pins(f);MockFixture owned=new MockFixture();MockApi api=new MockApi(owned);MockStarter starter=new MockStarter();
   ClientLiveDirectoryFixture.DirectoryCase old=owned.dirs.get(3);
   owned.dirs.set(3,new ClientLiveDirectoryFixture.DirectoryCase(old.label,old.identity,owned.dirs.get(0).token()));
   ClientLiveDirectoryFixture.Receipt failed=ClientLiveDirectoryFixture.run(p,OP,identity->owned,starter,api,1000);
   require(!failed.comparisonPassed()&&api.opened==0&&owned.closed==1,"all tokens checked before first native cursor");
  } else if(name.equals("packet_cleanup_error")) {
   File output=new File(base,"held-cleanup-Error.bin");try(FileOutputStream stream=new FileOutputStream(output)){stream.write(stock);}
   CloseErrorFile input=new CloseErrorFile(output);
   ClientLiveDirectoryFixture.PacketFile packet=new ClientLiveDirectoryFixture.PacketFile(input,
    fd->new ClientLiveDirectoryFixture.PacketIdentity(7,1234,10303,0100600,output.length()),10303,7);
   require(Arrays.equals(packet.read(System.nanoTime()+1000000000L),stock),"packet produced before cleanup Error");
   refusal(new Checked(){public void run()throws Exception{packet.close();}});
   require(input.closes>=2&&!input.getFD().valid(),"independent stream close attempted after channel close Error");
  } else if(name.startsWith("packet_file_")) {
   File output=new File(base,"fresh-probe-packet.bin");try(FileOutputStream stream=new FileOutputStream(output)){stream.write(stock);}
   String selected=name.substring(12);FileInputStream input=new FileInputStream(output);
   int mode=selected.equals("pipe")?0010600:0100600,uid=selected.equals("uid")?10304:10303;
   long device=selected.equals("device")?8:7,ino=selected.equals("inode")?0:1234,size=selected.equals("size")?512*1024+1:output.length();
   if(!selected.equals("changed")&&!selected.equals("valid")){
    refusal(new Checked(){public void run()throws Exception{new ClientLiveDirectoryFixture.PacketFile(input,fd->new ClientLiveDirectoryFixture.PacketIdentity(device,ino,uid,mode,size),10303,7);}});
    require(!input.getFD().valid(),"invalid regular output descriptor closed");
   }else {
    final int[] calls={0};ClientLiveDirectoryFixture.PacketMetadata metadata=fd->new ClientLiveDirectoryFixture.PacketIdentity(7,
     selected.equals("changed")&&calls[0]++>0?1235:1234,10303,0100600,output.length());
    try(ClientLiveDirectoryFixture.PacketFile packet=new ClientLiveDirectoryFixture.PacketFile(input,metadata,10303,7)) {
     if(selected.equals("changed")){refusal(new Checked(){public void run()throws Exception{packet.read(System.nanoTime()+1000000000L);}});
      require(Arrays.equals(packet.snapshot(),stock),"changed held file leaves exportable raw evidence");}
     else {require(Arrays.equals(packet.read(System.nanoTime()+1000000000L),stock),"actual regular FileChannel packet reader");
      refusal(new Checked(){public void run()throws Exception{packet.read(System.nanoTime()+1000000000L);}});}
    }
    require(!input.getFD().valid(),"regular output descriptor closed");
   }
  } else if(name.startsWith("runner_")) {
   Fixture f=fixture(base);ClientLiveDirectoryFixture.Pins p=pins(f);MockFixture owned=new MockFixture();MockApi api=new MockApi(owned);MockStarter starter=new MockStarter();
   String selected=name.substring(7);
   if(selected.equals("changed_inode"))api.wrongInode=true;else if(selected.equals("uid"))api.wrongUid=true;
   else if(selected.equals("device"))api.wrongDevice=true;else if(selected.equals("target"))api.wrongTarget=true;
   else if(selected.equals("retarget"))owned.changed=true;else if(selected.equals("late_failure"))api.lateFailure=true;
   else if(selected.equals("fields"))api.wrongFields=true;else if(selected.equals("fixture_cleanup"))owned.closeError=true;
   else if(selected.equals("cursor_cleanup"))api.closeError=true;else if(selected.equals("final_native_deadline"))api.delayFinal=true;
   else if(selected.equals("final_revalidate_deadline"))owned.delayFinal=true;else if(!selected.equals("success"))starter.failure=selected;
   ClientLiveDirectoryFixture.Receipt receipt=ClientLiveDirectoryFixture.run(p,OP,identity->owned,starter,api,selected.equals("stuck_console")?100:selected.startsWith("final_")?500:1000);
   require(!receipt.productionAdmissionAllowed(),"host fixture cannot grant Android authority");require(receipt.matchesCurrent(p),"bind current pins");
   require(owned.closed==1&&api.owned.isEmpty()&&api.closed==api.opened,"exclusive fixture namespace/cursors cleaned once");
   for(MockProbe child:starter.probes)require(child.closed==1&&child.held.destroyed,"exact child cleaned once");
   if(selected.equals("success")){
    require(receipt.comparisonPassed()&&receipt.cases.size()==4&&api.nextCalls==8,"four real JVM binary comparisons complete");
    require(receipt.cases.get(0).nativePid==77&&receipt.cases.get(0).packetBytes>0,"current native evidence retained");
    byte[] raw=receipt.cases.get(0).rawPacket();raw[0]='X';require(receipt.cases.get(0).rawPacket()[0]=='C',"defensive evidence copy");
    try{receipt.diagnostic().clear();throw new AssertionError("mutable diagnostic");}catch(UnsupportedOperationException good){}
    require(receipt.diagnostic().get("packaged_alias_sharing_retarget_controls").toString().contains("PENDING"),"pending gates explicit");
   }else {
    require(!receipt.comparisonPassed()&&receipt.status!=ClientLiveDirectoryFixture.Status.COMPARISON_PASSED,"failure cannot become pass");
    if(selected.equals("late_failure"))require(api.nextCalls==2&&api.opened==1&&receipt.cases.get(0).bridgeBatches==1&&receipt.cases.get(0).rawBridge().size()==1,"advanced cursor never retried or redelivered");
    if(selected.equals("fields")||selected.equals("malformed")||selected.equals("attribution")||selected.equals("exit")||selected.equals("timeout")||selected.equals("interrupt"))require(receipt.cases.get(0).rawPacket()!=null,"current failed raw evidence retained");
    if(selected.equals("final_native_deadline")||selected.equals("final_revalidate_deadline"))require(api.nextCalls==8&&receipt.cases.size()==4&&!receipt.cases.get(3).comparisonCompleted,"late final completion cannot pass deadline");
    if(selected.equals("packet_close_error"))require(!receipt.cleanupCompleted&&!receipt.cases.get(0).cleanupCompleted&&receipt.cases.get(0).rawPacket()!=null,"packet close Error poisons aggregate cleanup with raw retained");
    if(selected.equals("partial_console"))require(new String(receipt.cases.get(0).rawStdout(),StandardCharsets.US_ASCII).startsWith("partial native evidence"),"partial current console exported");
    if(selected.equals("close_error_console"))require(((CloseErrorConsole)starter.probes.get(0).held.out).closes>=2&&!receipt.cleanupCompleted,"console cleanup continues after Error");
    if(selected.equals("huge_console"))require(receipt.cases.get(0).rawStdout().length==32768,"oversize console bounded but available");
    if(selected.equals("stuck_console"))require(receipt.elapsedNanos<5000000000L,"stuck console terminates under owned deadline");
    if(selected.equals("interrupt")){require(receipt.status==ClientLiveDirectoryFixture.Status.INTERRUPTED&&Thread.currentThread().isInterrupted(),"interrupt preserved");Thread.interrupted();}
    require(!receipt.diagnostic().toString().contains("PRIVATE_"),"native private error strings excluded");
   }
  } else throw new AssertionError(name);
 }
'''


class FixtureSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES}
        runtime = namespace_fixture.RUNTIME.read_text()
        start = runtime.index('List<String> command = new ArrayList<>(', runtime.index('private Result runCharacter('))
        end = runtime.index('ProcessBuilder builder =', start)
        base = namespace_fixture.HARNESS
        body_start = base.index(' static void mainCase(')
        body_end = base.index(' public static void main(', body_start)
        text = base[:body_start] + HARNESS + base[body_end:]
        cls.directory = tempfile.TemporaryDirectory(prefix='coh-tiny-fixture-JVM-')
        cls.addClassCleanup(cls.directory.cleanup)
        cls.classes = Path(cls.directory.name)
        harness = cls.classes / 'GuestNamespaceHost.java'
        harness.write_text(text.replace('ACTUAL_COMMAND', runtime[start:end]))
        built = subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                                '-d', str(cls.classes), *map(str, SOURCES), str(harness)],
                               capture_output=True, text=True, timeout=60)
        if built.returncode:
            raise AssertionError('Actual fixture parser/runner compile failed: ' + built.stderr)

    @classmethod
    def tearDownClass(cls):
        for path, expected in cls.pins.items():
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise AssertionError('A fixture dependency changed during its qualification: ' + str(path))

    def execute(self, case):
        with tempfile.TemporaryDirectory(prefix='coh-tiny-fixture-owned-') as owned:
            result = subprocess.run(['java', '-cp', str(self.classes),
                                     'io.github.russianranger.cohclientinteractive.GuestNamespaceHost', case, owned],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, 'PASS')


def control(case):
    def test(self):
        self.execute(case)
    return test


CASES = (
    'parity', 'empty', 'nt_truncation', 'nt_magic', 'nt_reserved', 'nt_caps', 'nt_pid',
    'nt_batch_sequence', 'nt_batch_status', 'nt_next', 'nt_unicode', 'nt_footer', 'nt_eof',
    'nt_cleanup', 'nt_open_status', 'nt_incomplete', 'sharing_scope',
    'bridge_magic', 'bridge_operation', 'bridge_token', 'bridge_sequence', 'bridge_first',
    'bridge_reserved', 'bridge_total', 'bridge_ordinal', 'bridge_name', 'bridge_padding',
    'bridge_creation', 'bridge_short', 'bridge_empty', 'bridge_geometry',
    'field_size', 'field_time', 'field_attrs', 'field_name', 'unused_size_high',
    'transcript_no_double_delivery', 'changed_inode', 'paths', 'stream_bounds',
    'runner_success', 'runner_changed_inode', 'runner_uid', 'runner_device', 'runner_target',
    'runner_retarget', 'runner_late_failure', 'runner_fields', 'runner_fixture_cleanup',
    'runner_cursor_cleanup', 'runner_malformed', 'runner_console', 'runner_duplicate_console',
    'runner_attribution', 'runner_cleanup', 'runner_timeout', 'runner_exit', 'runner_interrupt',
    'runner_partial_console', 'runner_huge_console', 'runner_stuck_console', 'runner_close_error_console', 'packet_cleanup_error',
    'runner_packet_close_error', 'runner_final_native_deadline', 'runner_final_revalidate_deadline',
    'pins_and_wire', 'duplicate_tokens', 'packet_file_valid', 'packet_file_pipe', 'packet_file_uid',
    'packet_file_device', 'packet_file_inode', 'packet_file_size', 'packet_file_changed',
)
for _case in CASES:
    setattr(FixtureSourceTests, 'test_' + _case, control(_case))


if __name__ == '__main__':
    unittest.main()
