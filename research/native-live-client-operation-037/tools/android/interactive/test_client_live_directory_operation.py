"""Actual release-8 JVM operation ownership and real TCP adapter controls.

Metadata, native calls and activation receipts are explicitly typed host mocks.
These tests confer no JNI, Bionic, PRoot/Wine/FEX, APK or device authority.
"""
from pathlib import Path
import hashlib
import subprocess
import tempfile
import unittest

import test_client_guest_namespace as namespace_fixture

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
SOURCE = JAVA / 'ClientLiveDirectoryOperation.java'
SOURCES = [JAVA / name for name in (
    'ClientGuestNamespace.java', 'NativeLiveDirectory.java',
    'ClientLiveDirectoryService.java', 'ClientLiveDirectoryOperation.java')]

HARNESS = r'''
 static final long DEVICE=7;
 static final class MetadataMock implements ClientLiveDirectoryOperation.Metadata {
  final Map<String,Long> inodes=new LinkedHashMap<String,Long>();
  final Map<String,Integer> calls=new HashMap<String,Integer>();
  String foreign,cross,link,file,alias,retarget; boolean errorAfterCreate;long registeredDevice=DEVICE;
  FakeApi api;
  public ClientLiveDirectoryOperation.DirectoryIdentity currentDirectory(String path)throws IOException {
   if(!inodes.containsKey(path))inodes.put(path,(long)inodes.size()+10);
   int count=calls.containsKey(path)?calls.get(path)+1:1;calls.put(path,count);
   if(errorAfterCreate&&api.createCount>0)throw new IOException("controlled current lstat failure");
   return new ClientLiveDirectoryOperation.DirectoryIdentity(path.equals(alias)?path+"-alias":path,
    path.equals(cross)?registeredDevice+1:registeredDevice,inodes.get(path)+(path.equals(retarget)&&count>1?1:0),
    path.equals(foreign)?10304:10303,!path.equals(file),path.equals(link));
  }
 }
 static final class NativeCursorMock {
  final String path;String resolved;final byte[] operation,token;int batches;
  NativeCursorMock(String path,byte[] op,byte[] token){this.path=path;resolved=path;operation=op.clone();this.token=token.clone();}
 }
 static final class FakeApi implements ClientLiveDirectoryOperation.NativeApi {
  int createCount,closeNamespaceCount,openCount,closeCursorCount,nextCount,statsCount;
  int failNextAfter=-1; boolean nextError,identityForeign,identityCross,canonicalRetarget,nullCanonical;
  boolean createError,zeroCreate,closeCursorError,closeNamespaceError,invalidStats,hugeStats,negativeStats,statsIoError,statsError;long[] lastStats;
  final List<String> cleanupActions=Collections.synchronizedList(new ArrayList<String>());
  long nextHandle=200,registeredDevice=DEVICE;boolean reusedHandle;String resolvedTarget;ClientGuestNamespace expected;
  final Map<Long,NativeCursorMock> cursors=new HashMap<Long,NativeCursorMock>();
  public long create(String[] g,String[] h,long[] d,long[] i,int[] u,int n,int v,boolean dots,boolean sensitive)throws IOException {
   createCount++;require(g.length==7&&h.length==7&&d.length==7&&i.length==7&&u.length==7,"seven JNI roots");
   require(n==10303&&v==1000&&!dots&&!sensitive,"exact native/guest identity and recipe");
   for(int row=0;row<7;row++){
    ClientGuestNamespace.Binding b=expected.ownedDirectoryBindings().get(row);
    require(g[row].equals(b.guestPrefix)&&h[row].equals(b.hostRoot)&&d[row]==registeredDevice&&u[row]==10303,"exact finalized root arrays");
   }
   if(createError)throw new OutOfMemoryError("controlled native allocation failure");return zeroCreate?0:99;
  }
  public long open(long ns,String path,byte[] op,byte[] token)throws IOException {
   require(ns==99,"namespace ownership");openCount++;long h=reusedHandle?200:nextHandle++;
   NativeCursorMock cursor=new NativeCursorMock(path,op,token);if(resolvedTarget!=null)cursor.resolved=resolvedTarget;
   cursors.put(h,cursor);return h;
  }
  public byte[] next(long h)throws IOException {
   nextCount++;if(failNextAfter>=0&&nextCount>failNextAfter){if(nextError)throw new OutOfMemoryError("controlled advanced cursor allocation failure");
    throw new IOException("controlled native post-advance failure");}
   NativeCursorMock c=cursors.get(h);require(c!=null,"current mock cursor");
   int count=failNextAfter==1?1:0;byte[] raw=new byte[64+count*328];java.nio.ByteBuffer b=java.nio.ByteBuffer.wrap(raw).order(java.nio.ByteOrder.LITTLE_ENDIAN);
   b.put("COHLIVE1".getBytes(StandardCharsets.US_ASCII)).put(c.operation).put(c.token).putInt(c.batches).putInt(c.batches*count)
    .putInt(count).putInt(count==0?1:0).putInt(0).putInt(raw.length);
   if(count==1){b.position(64);b.putInt(c.batches).putInt(0);raw[64+8+44]='a';}
   c.batches++;return raw;
  }
  public void closeCursor(long h)throws IOException {cleanupActions.add("close_cursor");closeCursorCount++;cursors.remove(h);if(closeCursorError)throw new OutOfMemoryError("controlled cursor cleanup failure");}
  public void closeNamespace(long n)throws IOException {require(n==99,"close only owned namespace");cleanupActions.add("close_namespace");closeNamespaceCount++;cursors.clear();
   if(closeNamespaceError)throw new OutOfMemoryError("controlled namespace cleanup failure");}
  public long[] stats(long n)throws IOException {require(n==99,"stats only owned namespace");statsCount++;cleanupActions.add("stats_attempt");
   if(statsError)throw new OutOfMemoryError("PRIVATE_NATIVE_STATS_MESSAGE_MUST_NOT_LEAK");
   if(statsIoError)throw new IOException("PRIVATE_NATIVE_STATS_MESSAGE_MUST_NOT_LEAK");
   lastStats=invalidStats?new long[]{1,2}:new long[]{negativeStats?-13:13,17,3,1,1234,hugeStats?33554433:4321};return lastStats;}
  public long[] identity(long h)throws IOException {require(cursors.containsKey(h),"held cursor identity");
   return new long[]{identityCross?registeredDevice+1:registeredDevice,h,identityForeign?10304:10303};}
  public String canonicalGuestPath(long h)throws IOException {NativeCursorMock c=cursors.get(h);require(c!=null,"held canonical path");
   return nullCanonical?null:(canonicalRetarget?c.resolved+"-retarget":c.resolved);}
 }
 static final class JournalMock implements ClientLiveDirectoryService.Journal {
  final List<String> events=Collections.synchronizedList(new ArrayList<String>());
  public void record(String phase,String token,long rows,String result){events.add(phase+":"+rows+":"+result);}
 }
 static Map<ClientLiveDirectoryOperation.Gate,String> proofs(){
  Map<ClientLiveDirectoryOperation.Gate,String> result=new EnumMap<ClientLiveDirectoryOperation.Gate,String>(ClientLiveDirectoryOperation.Gate.class);
  for(ClientLiveDirectoryOperation.Gate gate:ClientLiveDirectoryOperation.Gate.values())result.put(gate,repeat('e',64));return result;
 }
 static ClientLiveDirectoryOperation.ReviewedActivation activation(ClientGuestNamespace n,String root,String data)throws Exception {
  return new ClientLiveDirectoryOperation.ReviewedActivation(repeat('f',64),n.sha256(),root,data,n.provenance(),
   ClientLiveDirectoryOperation.RECIPE,false,false,proofs());
 }
 static ClientLiveDirectoryOperation.ActivationContract contract(final ClientGuestNamespace n,final String root,final String data)throws Exception {
  final ClientLiveDirectoryOperation.ReviewedActivation a=activation(n,root,data);
  return new ClientLiveDirectoryOperation.ActivationContract(){public ClientLiveDirectoryOperation.ReviewedActivation verifyCurrent(
    ClientGuestNamespace ignored,String files,String guest){return a;}};
 }
 static final class Context {
  final Fixture fixture;final ClientGuestNamespace descriptor;final MetadataMock metadata=new MetadataMock();
  final FakeApi api=new FakeApi();final JournalMock journal=new JournalMock();
  final String root;ClientLiveDirectoryOperation.ActivationContract activation;
  Context(File base)throws Exception {fixture=fixture(base);descriptor=build(fixture);root=fixture.files.getCanonicalPath();
   api.expected=descriptor;metadata.api=api;activation=contract(descriptor,root,DATA);}
  ClientLiveDirectoryOperation create()throws IOException{return ClientLiveDirectoryOperation.create(descriptor,root,DATA,activation,metadata,api,journal);}
 }
 static final class Peer implements AutoCloseable {
  final java.net.Socket socket;final DataInputStream input;final DataOutputStream output;
  final byte[] operation,auth,token=new byte[16];int seq=1;
  Peer(Map<String,String> controls)throws Exception {
   String endpoint=controls.get("COH_CLIENT_LIVE_DIRECTORY_ENDPOINT");socket=new java.net.Socket("127.0.0.1",Integer.parseInt(endpoint.split(":")[1]));
   socket.setSoTimeout(3000);input=new DataInputStream(socket.getInputStream());output=new DataOutputStream(socket.getOutputStream());
   operation=unhex(controls.get("COH_CLIENT_LIVE_DIRECTORY_SESSION"));auth=unhex(controls.get("COH_CLIENT_LIVE_DIRECTORY_AUTH"));token[0]=7;
  }
  int request(int command,String path)throws Exception {
   byte[] p=path==null?new byte[0]:path.getBytes(StandardCharsets.US_ASCII);
   java.nio.ByteBuffer b=java.nio.ByteBuffer.allocate(96+p.length).order(java.nio.ByteOrder.LITTLE_ENDIAN);
   b.put("COHLDIR1".getBytes(StandardCharsets.US_ASCII)).putInt(1).putInt(command).put(operation).put(auth).putInt(seq).put(token)
    .putInt(p.length).putInt(96+p.length).putInt(0).put(p);output.write(b.array());output.flush();
   byte[] header=new byte[32];input.readFully(header);java.nio.ByteBuffer h=java.nio.ByteBuffer.wrap(header).order(java.nio.ByteOrder.LITTLE_ENDIAN);
   require(h.getInt(16)==seq,"current request attribution");seq++;byte[] body=new byte[h.getInt(20)];input.readFully(body);return h.getInt(12);
  }
  public void close()throws IOException{socket.close();}
 }
 static byte[] unhex(String value){byte[] b=new byte[value.length()/2];for(int i=0;i<b.length;i++)b[i]=(byte)Integer.parseInt(value.substring(i*2,i*2+2),16);return b;}
 static void noNative(Context c){require(c.api.createCount==0&&c.api.openCount==0&&c.api.nextCount==0,"refusal before any native activity");}
 static void awaitFailure(ClientLiveDirectoryOperation operation)throws Exception {
  long end=System.nanoTime()+3000000000L;while(operation.failure()==null&&System.nanoTime()<end)Thread.yield();require(operation.failure()!=null,"usable current operation failure");
 }
 static ClientLiveDirectoryOperation.StatisticsSnapshot awaitFinalStatistics(ClientLiveDirectoryOperation operation)throws Exception {
  long end=System.nanoTime()+3000000000L;
  do{if(operation.diagnosticDescriptor().containsKey("statistics_capture_phase"))return operation.statistics();Thread.yield();}while(System.nanoTime()<end);
  throw new AssertionError("normal Game EOF did not retain final counter evidence");
 }
 static void cleanup(ClientLiveDirectoryOperation operation)throws IOException{try{operation.close();}catch(IOException expected){}}
 static void mainCase(String name,File base)throws Exception {
  Context c=new Context(base);
  if(name.equals("closed_contract")){
   c.activation=null;refusal(new Checked(){public void run()throws Exception{c.create();}});noNative(c);
   require(!c.descriptor.nativeRegistrationAllowed()&&!c.descriptor.rootMetadataVerified(),"closed provenance cannot authorize factory");
  }else if(name.equals("null_admission")){
   c.activation=(n,r,d)->null;refusal(()->c.create());noNative(c);
  }else if(name.equals("contract_failure")){
   c.activation=(n,r,d)->{throw new IOException("controlled unavailable qualification");};refusal(()->c.create());noNative(c);
  }else if(name.startsWith("activation_")){
   String bad=name.substring(11);ClientGuestNamespace.Provenance p=c.descriptor.provenance();
   if(bad.equals("operation")||bad.equals("session")||bad.equals("process")||bad.equals("uid")||bad.equals("runtime")||bad.equals("game")||bad.equals("game_bytes")||bad.equals("helper"))
    p=new ClientGuestNamespace.Provenance(bad.equals("operation")?"1792000000001-abcdef012345":p.operationId,
     bad.equals("session")?repeat('2',32):p.sessionId,bad.equals("process")?"12345678-1234-1234-1234-123456789abd":p.processInstance,
     bad.equals("uid")?10304:p.realUid,bad.equals("runtime")?repeat('d',64):p.runtimeManifestSha256,
     bad.equals("game")?repeat('d',64):p.nativeConsumerSha256,bad.equals("game_bytes")?p.nativeConsumerBytes+1:p.nativeConsumerBytes,
     bad.equals("helper")?repeat('d',64):p.helperIdentitySha256);
   Map<ClientLiveDirectoryOperation.Gate,String> proof=proofs();
   if(bad.equals("missing_gate"))proof.remove(ClientLiveDirectoryOperation.Gate.CURRENT_PACKAGED_PROOT_WINE_FEX_FIXTURE);
   if(bad.equals("bad_gate"))proof.put(ClientLiveDirectoryOperation.Gate.ARM64_HELPER_ABI,"not-a-receipt");
   final ClientGuestNamespace.Provenance changed=p;
   if(bad.equals("missing_gate")||bad.equals("bad_gate")||bad.equals("dots")||bad.equals("sensitive")||bad.equals("recipe")){
    refusal(()->new ClientLiveDirectoryOperation.ReviewedActivation(repeat('f',64),c.descriptor.sha256(),c.root,DATA,changed,
     bad.equals("recipe")?"unqualified-recipe":ClientLiveDirectoryOperation.RECIPE,bad.equals("dots"),bad.equals("sensitive"),proof));
   }else{
    final ClientLiveDirectoryOperation.ReviewedActivation a=new ClientLiveDirectoryOperation.ReviewedActivation(repeat('f',64),
     bad.equals("namespace")?repeat('d',64):c.descriptor.sha256(),bad.equals("root")?c.root+"-foreign":c.root,
     bad.equals("data")?DATA.replace("012345","ffffff"):DATA,changed,ClientLiveDirectoryOperation.RECIPE,false,false,proof);
    c.activation=(n,r,d)->a;refusal(()->c.create());
   }noNative(c);
  }else if(name.startsWith("root_")){
   String bad=name.substring(5),path=c.descriptor.ownedDirectoryBindings().get(3).hostRoot;
   if(bad.equals("foreign"))c.metadata.foreign=path;
   else if(bad.equals("cross"))c.metadata.cross=path;
   else if(bad.equals("link"))c.metadata.link=path;
   else if(bad.equals("file"))c.metadata.file=path;
   else if(bad.equals("alias"))c.metadata.alias=path;
   else if(bad.equals("app_foreign"))c.metadata.foreign=c.root;
   else if(bad.equals("retarget"))c.metadata.retarget=path;
   else if(bad.equals("lstat_after_create"))c.metadata.errorAfterCreate=true;
   else throw new AssertionError("unknown root control");
   refusal(()->c.create());if(bad.equals("retarget")||bad.equals("lstat_after_create"))require(c.api.closeNamespaceCount==1,"release exclusively owned new namespace");else noNative(c);
  }else if(name.equals("native_create_zero")){
   c.api.zeroCreate=true;refusal(()->c.create());require(c.api.closeNamespaceCount==0,"no invented namespace cleanup");
  }else if(name.equals("native_create_error")){
   c.api.createError=true;try{c.create();throw new AssertionError("expected Error");}catch(OutOfMemoryError expected){}
   require(c.api.closeNamespaceCount==0,"nativeCreate must release unreturned own allocation");
  }else if(name.equals("service_failure")||name.equals("service_error")){
   final boolean fatal=name.equals("service_error");
   try{ClientLiveDirectoryOperation.create(c.descriptor,c.root,DATA,c.activation,c.metadata,c.api,c.journal,
     (o,d,u,b,p,j)->{if(fatal)throw new OutOfMemoryError("controlled starter allocation failure");throw new IOException("controlled starter failure");});
    throw new AssertionError("expected construction refusal");}catch(IOException expected){require(!fatal,"original Error retained");}catch(OutOfMemoryError expected){require(fatal,"original Error retained");}
   require(c.api.createCount==1&&c.api.closeNamespaceCount==1,"one namespace release for failed server construction");
  }else if(name.equals("descriptor_and_stats")){
   try(ClientLiveDirectoryOperation op=c.create()){
    Map<String,String> diagnostics=op.diagnosticDescriptor(),control=op.privateGameControlFields();Map<String,Long> stats=op.statistics().values;Map<String,Object> document=op.privateGameControlDocument();
    require(diagnostics.get("operation_id").equals(RUN)&&diagnostics.get("session_id").equals(SESSION)&&diagnostics.get("process_instance").equals(PROCESS),"exact report attribution");
    require(control.size()==8&&control.get("COH_CLIENT_LIVE_DIRECTORY_AUTH").length()==64,"private Game-only control");
    require(document.size()==14&&document.get("format").equals(1)&&document.get("game_bytes").equals(9487872L)&&document.get("auth_nonce").equals(control.get("COH_CLIENT_LIVE_DIRECTORY_AUTH"))&&!document.containsKey("enabled")&&!document.containsKey("qualified"),"exact private JSON handoff without authority flags");
    require(!diagnostics.toString().contains(control.get("COH_CLIENT_LIVE_DIRECTORY_AUTH"))&&!diagnostics.containsKey("COH_CLIENT_LIVE_DIRECTORY_AUTH"),"no diagnostic credential");
    require(stats.size()==6&&stats.get("entry_metadata_requests")==13&&!stats.containsKey("syscalls")&&!stats.containsKey("RSS"),"scoped metadata and core heap labels");
    try{diagnostics.clear();throw new AssertionError("mutable descriptor");}catch(UnsupportedOperationException expected){}
    try{control.clear();throw new AssertionError("mutable control");}catch(UnsupportedOperationException expected){}
    try{stats.clear();throw new AssertionError("mutable stats");}catch(UnsupportedOperationException expected){}
   }require(c.api.closeNamespaceCount==1,"one owned namespace");
  }else if(name.equals("invalid_stats")||name.equals("huge_stats")){
   c.api.invalidStats=name.equals("invalid_stats");c.api.hugeStats=!c.api.invalidStats;
   try(ClientLiveDirectoryOperation op=c.create()){
    ClientLiveDirectoryOperation.StatisticsSnapshot stats=op.statistics();require(stats.phase==ClientLiveDirectoryOperation.StatisticsPhase.CURRENT_STATISTICS_OMITTED&&stats.values.isEmpty()&&stats.omission!=null,"unvalidated current counters are explicitly omitted");
   }
  }else if(name.equals("idempotent_close")){
   ClientLiveDirectoryOperation op=c.create();op.close();op.close();require(c.api.closeNamespaceCount==1,"idempotent owner cleanup");
   refusal(()->op.privateGameControlFields());refusal(()->op.privateGameControlDocument());require(op.statistics().phase==ClientLiveDirectoryOperation.StatisticsPhase.VALIDATED_FINAL_BEFORE_NAMESPACE_CLOSE,"closed owner retains optional final counts");
  }else if(name.equals("normal_eof_final_stats")){
   ClientLiveDirectoryOperation op=c.create();try(Peer peer=new Peer(op.privateGameControlFields())){
    require(peer.request(1,DATA+"/fx")==0&&peer.request(2,null)==0&&peer.request(3,null)==0,"normal Game finished its metadata cursor");
   }
   ClientLiveDirectoryOperation.StatisticsSnapshot stats=awaitFinalStatistics(op);require(stats.phase==ClientLiveDirectoryOperation.StatisticsPhase.VALIDATED_FINAL_BEFORE_NAMESPACE_CLOSE&&stats.values.get("entry_metadata_requests")==13&&stats.omission==null,"normal peer EOF retains validated final counts");
   require(op.failure()==null,"optional successful finalization leaves normal Game close successful");op.close();require(op.statistics()==stats,"final counter snapshot retained after owner close");
   require(c.api.closeNamespaceCount==1&&c.api.statsCount==1,"normal EOF closes one namespace and reads final stats once");
  }else if(name.equals("owner_close_final_stats")){
   ClientLiveDirectoryOperation op=c.create();try(Peer peer=new Peer(op.privateGameControlFields())){
    require(peer.request(1,DATA+"/fx")==0,"held current cursor before owner close");op.close();
   }
   ClientLiveDirectoryOperation.StatisticsSnapshot stats=op.statistics();require(stats.phase==ClientLiveDirectoryOperation.StatisticsPhase.VALIDATED_FINAL_BEFORE_NAMESPACE_CLOSE&&stats.values.size()==6,"explicit owner close retains six validated values");
   require(c.api.cleanupActions.equals(Arrays.asList("close_cursor","stats_attempt","close_namespace")),"cursor cleanup precedes counter observation then namespace close");
   require(op.diagnosticDescriptor().get("statistics_owned_heap_scope").contains("before_final_namespace_close"),"heap observation is labelled before namespace free");
  }else if(name.equals("final_stats_io_omission")||name.equals("final_stats_error_omission")||name.equals("final_stats_corrupt")||name.equals("final_stats_negative")||name.equals("final_stats_huge")){
   c.api.statsIoError=name.equals("final_stats_io_omission");c.api.statsError=name.equals("final_stats_error_omission");c.api.invalidStats=name.equals("final_stats_corrupt");
   c.api.negativeStats=name.equals("final_stats_negative");c.api.hugeStats=name.equals("final_stats_huge");
   ClientLiveDirectoryOperation op=c.create();op.close();ClientLiveDirectoryOperation.StatisticsSnapshot stats=op.statistics();
   require(stats.phase==ClientLiveDirectoryOperation.StatisticsPhase.FINAL_STATISTICS_OMITTED&&stats.values.isEmpty()&&stats.omission!=null&&stats.omission.length()<1024,"failed or corrupted final counters have explicit bounded omission and no success claim");
   require(!stats.omission.contains("PRIVATE_NATIVE_STATS_MESSAGE_MUST_NOT_LEAK")&&!op.diagnosticDescriptor().toString().contains("PRIVATE_NATIVE_STATS_MESSAGE_MUST_NOT_LEAK"),"optional native message never leaks into omission");
   require(op.failure()==null&&c.api.closeNamespaceCount==1&&c.api.statsCount==1,"optional stats failure does not fail normal Game cleanup or leak namespace");
  }else if(name.equals("final_stats_keeps_native_error")){
   c.api.failNextAfter=1;c.api.nextError=true;c.api.statsError=true;ClientLiveDirectoryOperation op=c.create();
   try(Peer peer=new Peer(op.privateGameControlFields())){
    require(peer.request(1,DATA+"/fx")==0&&peer.request(2,null)==0,"one original native batch produced");
    try{peer.request(2,null);throw new AssertionError("original native failure must end transport");}catch(EOFException expected){}awaitFailure(op);
   }finally{cleanup(op);}
   require(op.failure().getCause() instanceof OutOfMemoryError&&op.failure().getCause().getMessage().equals("controlled advanced cursor allocation failure"),"original native failure is preserved over optional stats Error");
   require(op.statistics().phase==ClientLiveDirectoryOperation.StatisticsPhase.FINAL_STATISTICS_OMITTED&&op.statistics().values.isEmpty(),"independent metrics omission remains available after failure");
   require(c.api.closeCursorCount==1&&c.api.closeNamespaceCount==1,"stats Error still closes exclusively owned cursor and namespace once");
  }else if(name.equals("final_stats_immutable")){
   ClientLiveDirectoryOperation op=c.create();op.close();ClientLiveDirectoryOperation.StatisticsSnapshot stats=op.statistics();
   Arrays.fill(c.api.lastStats,99999);require(stats.values.get("entry_metadata_requests")==13,"native array mutation cannot alter retained validated snapshot");
   try{stats.values.clear();throw new AssertionError("mutable final counters");}catch(UnsupportedOperationException expected){}
   require(op.statistics()==stats&&op.statistics()==stats&&c.api.statsCount==1,"final reads reuse immutable snapshot without closed namespace calls");
  }else if(name.equals("scope")){
   try(ClientLiveDirectoryOperation op=c.create();Peer peer=new Peer(op.privateGameControlFields())){
    for(String path:new String[]{DATA,DATA+"/scripts",DATA+"/texture_library",DATA+"/object_library",DATA+"/player_library",DATA+"/fx2","/game-import/data/fx","/state/diagnostic/character-login-profile","/proc/fx"})
     require(peer.request(1,path)==1,"unknown directory initial decline");
    require(c.api.openCount==0,"no JNI access outside two initial branches");
    require(peer.request(1,DATA+"/SCRIPTS.LOC/sub")==0,"preserve actual-case current guest request");
    require(peer.request(2,null)==0,"scoped current metadata batch");require(peer.request(3,null)==0,"cursor owned cleanup");
   }require(c.api.closeNamespaceCount==1&&c.api.closeCursorCount==1,"one cursor one namespace release");
  }else if(name.startsWith("allowed_resolved_")){
   String kind=name.substring("allowed_resolved_".length()),request=DATA+"/fx";
   if(kind.equals("absolute_import_fx"))c.api.resolvedTarget="/game-import/data/fx";
   else if(kind.equals("relative_current_fx")){request=DATA+"/fx/link";c.api.resolvedTarget=DATA+"/fx/current-target";}
   else if(kind.equals("current_loc_case")){request=DATA+"/SCRIPTS.LOC";c.api.resolvedTarget=DATA+"/scripts.loc";}
   else if(kind.equals("import_loc_case")){request=DATA+"/SCRIPTS.LOC/sub";c.api.resolvedTarget="/game-import/data/scripts.loc/sub";}
   else if(kind.equals("actual_import_case"))c.api.resolvedTarget="/game-import/data/FX";
   else throw new AssertionError("unknown allowed resolved target");
   try(ClientLiveDirectoryOperation op=c.create();Peer peer=new Peer(op.privateGameControlFields())){
    require(peer.request(1,request)==0,"admitted original request joins a separate safe resolved target");
    require(c.api.cursors.values().iterator().next().path.equals(request),"native original request remains unchanged");
    require(peer.request(2,null)==0,"known resolved target produces its current native batch");require(peer.request(3,null)==0,"known alias cursor closes");
    require(op.privateGameControlDocument().get("guest_root").equals(DATA),"logical current source attribution preserved");
   }require(c.api.openCount==1&&c.api.nextCount==1&&c.api.closeCursorCount==1&&c.api.closeNamespaceCount==1,"separate original/resolved cursor ownership");
  }else if(name.startsWith("refused_resolved_")){
   String kind=name.substring("refused_resolved_".length());
   if(kind.equals("profile"))c.api.resolvedTarget="/state/diagnostic/character-login-profile/fx";
   else if(kind.equals("other_view"))c.api.resolvedTarget=DATA.replace("0123456789abcdef01234567","ffffffffffffffffffffffff")+"/fx";
   else if(kind.equals("passthrough"))c.api.resolvedTarget="/proc/fx";
   else if(kind.equals("cross_branch"))c.api.resolvedTarget="/game-import/data/scripts.loc";
   else if(kind.equals("unqualified_binding"))c.api.resolvedTarget="/opt/coh/data/fx";
   else if(kind.equals("partial_branch"))c.api.resolvedTarget="/game-import/data/fx2";
   else if(kind.equals("dot_escape"))c.api.resolvedTarget="/game-import/data/fx/../scripts.loc";
   else if(kind.equals("legacy_link"))c.api.resolvedTarget="/game-import/data/fx/.l2s.alias";
   else if(kind.equals("null"))c.api.nullCanonical=true;
   else throw new AssertionError("unknown unsafe resolved target");
   try(ClientLiveDirectoryOperation op=c.create();Peer peer=new Peer(op.privateGameControlFields())){
    require(peer.request(1,DATA+"/fx")==1,"unsafe resolved target declines before callbacks");
    require(c.api.nextCount==0&&c.api.closeCursorCount==1,"unsafe resolved target never produces rows and releases only its cursor");
   }require(c.api.closeNamespaceCount==1,"unsafe resolved target retains owned namespace until cleanup");
  }else if(name.equals("resolved_retarget_after_rows")){
   c.api.resolvedTarget="/game-import/data/fx";c.api.failNextAfter=1;ClientLiveDirectoryOperation op=c.create();
   try(Peer peer=new Peer(op.privateGameControlFields())){
    require(peer.request(1,DATA+"/fx")==0,"known absolute link admitted");
    require(peer.request(2,null)==0,"one batch already delivered from pinned target");
    c.api.cursors.values().iterator().next().resolved="/game-import/data/fx/new-target";
    require(peer.request(2,null)==2,"retarget after produced rows is terminal without restart");
    require(c.api.nextCount==1,"retarget never invokes another native batch");
    require(c.journal.events.toString().contains("batch_failure:1:terminal_no_restart"),"failure evidence preserves delivered row attribution");
   }finally{cleanup(op);}require(c.api.closeNamespaceCount==1,"post-row retarget closes current namespace once");
  }else if(name.equals("resolved_retarget_before_next")){
   c.api.resolvedTarget="/game-import/data/fx";ClientLiveDirectoryOperation op=c.create();
   try(Peer peer=new Peer(op.privateGameControlFields())){
    require(peer.request(1,DATA+"/fx")==0,"known absolute link admitted");
    c.api.cursors.values().iterator().next().resolved="/game-import/data/fx/new-target";
    require(peer.request(2,null)==1,"even another allowed target cannot replace the pinned current target");
    require(c.api.nextCount==0,"resolved-target retarget refuses before any native batch");
   }finally{cleanup(op);}require(c.api.closeNamespaceCount==1,"retarget poisons exclusively current namespace");
  }else if(name.equals("open_retarget")||name.equals("open_cross")||name.equals("open_foreign")){
   c.api.canonicalRetarget=name.equals("open_retarget");c.api.identityCross=name.equals("open_cross");c.api.identityForeign=name.equals("open_foreign");
   try(ClientLiveDirectoryOperation op=c.create();Peer peer=new Peer(op.privateGameControlFields())){
    require(peer.request(1,DATA+"/fx")==1,"unsafe OPEN declines before any callback");require(c.api.nextCount==0,"no first NEXT before path/identity join");
    require(c.api.closeCursorCount==1,"release failed new cursor only");
   }require(c.api.closeNamespaceCount==1,"namespace retained until operation cleanup");
  }else if(name.equals("next_error_after_rows")||name.equals("next_io_after_rows")||name.equals("next_io_before_rows")){
   c.api.failNextAfter=name.equals("next_io_before_rows")?0:1;c.api.nextError=name.equals("next_error_after_rows");
   ClientLiveDirectoryOperation op=c.create();try(Peer peer=new Peer(op.privateGameControlFields())){
    require(peer.request(1,DATA+"/fx")==0,"current native directory joined");
    if(c.api.failNextAfter==1)require(peer.request(2,null)==0,"one produced batch");
    if(c.api.nextError){try{peer.request(2,null);throw new AssertionError("Error must terminate transport");}catch(EOFException expected){}awaitFailure(op);
     require(op.failure().getCause() instanceof OutOfMemoryError,"original advanced-cursor Error retained");
    }else{
     require(peer.request(2,null)==(c.api.failNextAfter==0?1:2),"initial or terminal status preserves delivered row history");
     require(peer.request(1,DATA+"/scripts.loc")==1,"poisoned namespace never retries");
    }
   }finally{cleanup(op);}
   require(c.api.closeNamespaceCount==1&&c.api.openCount==1&&c.api.nextCount==(c.api.failNextAfter+1),"single namespace no native retry");
  }else if(name.equals("next_retarget")||name.equals("next_identity")){
   ClientLiveDirectoryOperation op=c.create();try(Peer peer=new Peer(op.privateGameControlFields())){
    require(peer.request(1,DATA+"/fx")==0,"open before current path change");
    c.api.canonicalRetarget=name.equals("next_retarget");c.api.identityForeign=name.equals("next_identity");
    require(peer.request(2,null)==1,"changed directory refuses before rows");require(c.api.nextCount==0,"retarget fails before producing another native batch");
   }finally{cleanup(op);}require(c.api.closeNamespaceCount==1,"retarget poisons current namespace");
  }else if(name.equals("cleanup_errors")){
   c.api.closeCursorError=true;c.api.closeNamespaceError=true;ClientLiveDirectoryOperation op=c.create();
   try(Peer peer=new Peer(op.privateGameControlFields())){require(peer.request(1,DATA+"/fx")==0,"live cursor before cleanup");}
   awaitFailure(op);refusal(()->op.close());op.close();require(c.api.closeCursorCount==1&&c.api.closeNamespaceCount==1,"Throwable cursor cleanup still closes namespace once");
  }else if(name.equals("high_unsigned_device")){
   c.api.registeredDevice=Long.MIN_VALUE;c.metadata.registeredDevice=Long.MIN_VALUE;
   try(ClientLiveDirectoryOperation op=c.create();Peer peer=new Peer(op.privateGameControlFields())){
    require(op.privateGameControlDocument().get("device").equals("9223372036854775808"),"actual private wire uses unsigned device bits");
    require(peer.request(1,DATA+"/fx")==0,"high device bits preserve current registration");require(peer.request(2,null)==0,"high device native batch");require(peer.request(3,null)==0,"high device owned cursor closes");
   }require(c.api.closeNamespaceCount==1,"high device owned namespace closes once");
  }else if(name.equals("reused_native_cursor")){
   c.api.reusedHandle=true;ClientLiveDirectoryOperation op=c.create();try(Peer peer=new Peer(op.privateGameControlFields())){
    require(peer.request(1,DATA+"/fx")==0,"first held cursor");peer.token[0]=8;
    require(peer.request(1,DATA+"/scripts.loc")==1,"reused native handle rejected before callbacks");
    refusal(()->op.privateGameControlDocument());require(c.api.nextCount==0,"no NEXT on reused native handles");
   }finally{cleanup(op);}require(c.api.closeNamespaceCount==1,"reused handle poisons only this namespace");
  }else throw new AssertionError("unknown control "+name);
 }
 public static void main(String[] args)throws Exception{mainCase(args[0],new File(args[1]));System.out.print("PASS");}
}
'''


class ClientLiveDirectoryOperationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in SOURCES}
        runtime = namespace_fixture.RUNTIME.read_text()
        start = runtime.index('List<String> command = new ArrayList<>(', runtime.index('private Result runCharacter('))
        end = runtime.index('ProcessBuilder builder =', start)
        prelude = namespace_fixture.HARNESS.split(' static void mainCase(', 1)[0]
        prelude = prelude.replace('GuestNamespaceHost', 'LiveDirectoryOperationHost')
        cls.classes_temp = tempfile.TemporaryDirectory(prefix='coh-live-operation-classes-')
        cls.addClassCleanup(cls.classes_temp.cleanup)
        cls.classes = Path(cls.classes_temp.name)
        harness = cls.classes / 'LiveDirectoryOperationHost.java'
        harness.write_text(prelude.replace('ACTUAL_COMMAND', runtime[start:end]) + HARNESS)
        result = subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                                 '-d', str(cls.classes), *map(str, SOURCES), str(harness)],
                                text=True, capture_output=True, timeout=60)
        if result.returncode:
            raise AssertionError('Actual operation/adapter compile failed: ' + result.stderr)

    @classmethod
    def tearDownClass(cls):
        for path, sha in cls.pins.items():
            if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
                raise AssertionError('Dependency source changed during qualification: ' + path.name)

    def execute(self, name):
        with tempfile.TemporaryDirectory(prefix='coh-live-operation-owned-') as directory:
            result = subprocess.run(['java', '-cp', str(self.classes),
                                     'io.github.russianranger.cohclientinteractive.LiveDirectoryOperationHost',
                                     name, directory], text=True, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, 'PASS')


def control_test(name):
    def test(self): self.execute(name)
    return test


for _name in (
    'closed_contract', 'null_admission', 'contract_failure',
    'activation_operation', 'activation_session', 'activation_process', 'activation_uid',
    'activation_runtime', 'activation_game', 'activation_game_bytes', 'activation_helper',
    'activation_namespace', 'activation_root', 'activation_data', 'activation_missing_gate',
    'activation_bad_gate', 'activation_dots', 'activation_sensitive', 'activation_recipe',
    'root_foreign', 'root_cross', 'root_link', 'root_file', 'root_alias', 'root_app_foreign',
    'root_retarget', 'root_lstat_after_create', 'native_create_zero', 'native_create_error',
    'service_failure', 'service_error', 'descriptor_and_stats', 'invalid_stats', 'huge_stats',
    'idempotent_close', 'scope', 'open_retarget', 'open_cross', 'open_foreign',
    'next_error_after_rows', 'next_io_after_rows', 'next_io_before_rows',
    'next_retarget', 'next_identity', 'cleanup_errors', 'high_unsigned_device', 'reused_native_cursor',
    'allowed_resolved_absolute_import_fx', 'allowed_resolved_relative_current_fx',
    'allowed_resolved_current_loc_case', 'allowed_resolved_import_loc_case', 'allowed_resolved_actual_import_case',
    'refused_resolved_profile', 'refused_resolved_other_view', 'refused_resolved_passthrough',
    'refused_resolved_cross_branch', 'refused_resolved_unqualified_binding', 'refused_resolved_partial_branch',
    'refused_resolved_dot_escape', 'refused_resolved_legacy_link', 'refused_resolved_null',
    'resolved_retarget_before_next', 'resolved_retarget_after_rows',
    'normal_eof_final_stats', 'owner_close_final_stats', 'final_stats_io_omission',
    'final_stats_error_omission', 'final_stats_corrupt', 'final_stats_negative', 'final_stats_huge',
    'final_stats_keeps_native_error', 'final_stats_immutable',
):
    setattr(ClientLiveDirectoryOperationTests, 'test_' + _name, control_test(_name))


if __name__ == '__main__':
    unittest.main()
