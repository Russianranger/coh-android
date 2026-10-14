"""Real host JNI/kernel/TCP composition; activation receipts remain controlled.

The explicit receipt authenticates an already built host helper. This does not
execute Android, PRoot, Wine, FEX, Game, a database or player data.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import test_client_guest_namespace as fixture

JAVA = fixture.JAVA
CORE_PINS = {
    'coh_live_directory_core.c': 'b2ebd02a2b30cc985eb1e376d044155bb729ecab5809798528fd43744008ec8c',
    'coh_live_directory_jni.c': '397190cf97af337f5eb0a6bec6d38cf79d58eecb7cd214e16378b575469d8c6b',
}
HARNESS = r'''
 static final class RealMetadata implements ClientLiveDirectoryOperation.Metadata {
  public ClientLiveDirectoryOperation.DirectoryIdentity currentDirectory(String path)throws IOException {
   Path p=Paths.get(path); Map<String,Object> values=Files.readAttributes(p,"unix:dev,ino,uid,mode",LinkOption.NOFOLLOW_LINKS);
   int mode=((Number)values.get("mode")).intValue();
   return new ClientLiveDirectoryOperation.DirectoryIdentity(path,((Number)values.get("dev")).longValue(),
    ((Number)values.get("ino")).longValue(),((Number)values.get("uid")).intValue(),(mode&0170000)==0040000,(mode&0170000)==0120000);
  }
 }
 static byte[] decode(String value){byte[] out=new byte[value.length()/2];for(int i=0;i<out.length;i++)out[i]=(byte)Integer.parseInt(value.substring(i*2,i*2+2),16);return out;}
 static final class Peer implements AutoCloseable {
  final java.net.Socket socket;final java.io.DataInputStream in;final java.io.DataOutputStream out;
  final byte[] operation,auth,token=new byte[16];int sequence=1;
  Peer(Map<String,String> control)throws Exception {
   operation=decode(control.get("COH_CLIENT_LIVE_DIRECTORY_SESSION"));auth=decode(control.get("COH_CLIENT_LIVE_DIRECTORY_AUTH"));token[0]=7;
   socket=new java.net.Socket("127.0.0.1",Integer.parseInt(control.get("COH_CLIENT_LIVE_DIRECTORY_ENDPOINT").substring(10)));
   socket.setSoTimeout(4000);socket.setTcpNoDelay(true);in=new java.io.DataInputStream(socket.getInputStream());out=new java.io.DataOutputStream(socket.getOutputStream());
  }
  byte[] request(int command,String path)throws Exception {
   byte[] p=path==null?new byte[0]:path.getBytes(StandardCharsets.US_ASCII);
   java.nio.ByteBuffer header=java.nio.ByteBuffer.allocate(96+p.length).order(java.nio.ByteOrder.LITTLE_ENDIAN);
   header.put("COHLDIR1".getBytes(StandardCharsets.US_ASCII)).putInt(1).putInt(command).put(operation).put(auth).putInt(sequence)
    .put(token).putInt(p.length).putInt(96+p.length).putInt(0).put(p);out.write(header.array());out.flush();
   byte[] raw=new byte[32];in.readFully(raw);java.nio.ByteBuffer reply=java.nio.ByteBuffer.wrap(raw).order(java.nio.ByteOrder.LITTLE_ENDIAN);
   require(Arrays.equals(Arrays.copyOf(raw,8),new byte[]{'C','O','H','R','S','P','1',0})&&reply.getInt(8)==1&&reply.getInt(16)==sequence,"real reply attribution");
   sequence++;int bytes=reply.getInt(20);require(bytes>=0&&bytes<=27944,"bounded response");byte[] body=new byte[bytes];in.readFully(body);
   if(reply.getInt(12)!=0){if(command==1&&reply.getInt(12)==1)return new byte[0];
    require(command==2&&reply.getInt(12)==2,"expected terminal after rows");return null;}return body;
  }
  public void close()throws IOException{socket.close();Arrays.fill(auth,(byte)0);}
 }
 static int asciiCompare(String a,String b){int c=a.toUpperCase(Locale.ROOT).compareTo(b.toUpperCase(Locale.ROOT));return c==0?a.compareTo(b):c;}
 static void composed(String mode,File base,int uid,String library)throws Exception {
  System.load(library);
  Fixture f=new Fixture(base,true,false,false,true,RUN,SESSION,PROCESS,uid,repeat('a',64),repeat('b',64),9487872,repeat('c',64));
  ClientGuestNamespace descriptor=build(f);final RealMetadata metadata=new RealMetadata();
  Path data=Paths.get(new File(f.files,"client/state/diagnostic/client-work-0123456789abcdef01234567/data").getPath());Files.createDirectories(data);
  Path imported=Paths.get(new File(f.importRoot,"data/fx").getPath());Files.createDirectories(imported);
  Path directory=data.resolve("fx");
  if(mode.equals("absolute_link"))Files.createSymbolicLink(directory,Paths.get("/game-import/data/fx"));
  else if(mode.equals("relative_link")){Files.createDirectory(directory);Files.createDirectory(directory.resolve("actual"));
   directory=directory.resolve("alias");Files.createSymbolicLink(directory,Paths.get("actual"));}
  else if(mode.equals("relative_scope_decline")){Files.createDirectories(data.resolve("owned/fx"));Files.createSymbolicLink(directory,Paths.get("owned/fx"));}
  else Files.createDirectory(directory);
  Path physical=mode.equals("absolute_link")?imported:mode.equals("relative_link")?data.resolve("fx/actual"):
   mode.equals("relative_scope_decline")?data.resolve("owned/fx"):directory;
  List<String> expected=new ArrayList<>();expected.add(".");expected.add("..");
  for(int i=0;i<120;i++){String name=String.format(Locale.ROOT,"entry_%03d",i);Path leaf=physical.resolve(name);Files.write(leaf,new byte[]{1,2,3});
   Files.setLastModifiedTime(leaf,java.nio.file.attribute.FileTime.fromMillis(1700000000123L));expected.add(name);}
  Files.createDirectory(physical.resolve("sub"));expected.add("sub");
  Collections.sort(expected,(a,b)->asciiCompare(a,b));
  final String root=f.files.getCanonicalPath();
  ClientLiveDirectoryOperation.ActivationContract contract=(n,files,guest)->{
   Map<ClientLiveDirectoryOperation.Gate,String> proofs=new EnumMap<>(ClientLiveDirectoryOperation.Gate.class);
   for(ClientLiveDirectoryOperation.Gate gate:ClientLiveDirectoryOperation.Gate.values())proofs.put(gate,repeat('e',64));
   return new ClientLiveDirectoryOperation.ReviewedActivation(repeat('f',64),n.sha256(),files,guest,n.provenance(),ClientLiveDirectoryOperation.RECIPE,false,false,proofs);
  };
  ClientLiveDirectoryOperation operation=ClientLiveDirectoryOperation.create(descriptor,root,DATA,contract,metadata,ClientLiveDirectoryOperation.jniFacade(),(phase,token,rows,result)->{});
  long namespaceHeap=operation.statistics().values.get("bounded_core_owned_heap_bytes");
  try(ClientLiveDirectoryOperation owned=operation){
   Map<String,String> credentials=operation.privateGameControlFields();
   require(!operation.diagnosticDescriptor().toString().contains(credentials.get("COH_CLIENT_LIVE_DIRECTORY_AUTH")),"sanitized descriptor");
   try(Peer peer=new Peer(credentials)){
    byte[] ack=peer.request(1,DATA+(mode.equals("relative_link")?"/fx/alias":"/fx"));
    if(mode.equals("relative_scope_decline")){require(ack.length==0,"outside-branch relative target declines before NEXT");return;}
    require(ack.length==32,"held inode ACK before NEXT");
    java.nio.ByteBuffer identity=java.nio.ByteBuffer.wrap(ack).order(java.nio.ByteOrder.LITTLE_ENDIAN);
    ClientLiveDirectoryOperation.DirectoryIdentity physicalIdentity=metadata.currentDirectory(physical.toString());
    require(identity.getLong(0)==physicalIdentity.device&&identity.getLong(8)==physicalIdentity.inode,"real held JNI inode/dev join");
    List<String> observed=new ArrayList<>();int batches=0;
    while(true){byte[] batch=peer.request(2,null);require(batch!=null,"stable current source frame");batches++;
     java.nio.ByteBuffer wire=java.nio.ByteBuffer.wrap(batch).order(java.nio.ByteOrder.LITTLE_ENDIAN);int rows=wire.getInt(48);
     for(int i=0;i<rows;i++){int wfd=64+i*328+8,len=0;while(batch[wfd+44+len]!=0)len++;
      String name=new String(batch,wfd+44,len,StandardCharsets.US_ASCII);observed.add(name);
      if(name.startsWith("entry_")){require(wire.getInt(wfd+32)==3,"current native sizeLow");
       require(wire.getLong(wfd+20)==(1700000000123L+11644473600000L)*10000L,"current native100ns write FILETIME");}
      if(name.equals("sub"))require((wire.getInt(wfd)&16)!=0&&wire.getInt(wfd+32)==0,"native directory fields");
     }
     if(mode.equals("late_retarget")&&batches==1){Files.move(directory,data.resolve("old-fx"));Files.createDirectory(directory);
      require(peer.request(2,null)==null,"late retarget refuses after delivered rows, no cursor retry");return;}
     if(wire.getInt(52)==1)break;
    }
    require(batches>=2&&observed.equals(expected),"real JNI current ordered names across NT8KiB observation boundaries");
    Map<String,Long> stats=operation.statistics().values;require(stats.get("observation_batches")==batches&&stats.get("entry_metadata_requests")>=expected.size(),"scoped real native counters");
    require(stats.get("bounded_core_peak_heap_bytes")<=33554432L,"core bound excludesVM/RSS");
    peer.request(3,null);
   }
  }
  ClientLiveDirectoryOperation.StatisticsSnapshot finalStats=operation.statistics();
  require(finalStats.phase==ClientLiveDirectoryOperation.StatisticsPhase.VALIDATED_FINAL_BEFORE_NAMESPACE_CLOSE
   &&finalStats.omission==null&&finalStats.values.get("observation_batches")>=2,"real final native counters survive EOF and owner close");
  require(finalStats.values.get("bounded_core_owned_heap_bytes")==namespaceHeap,"cursor heap released; namespace remains at pre-cursor baseline until final free");
 }
 public static void main(String[] args)throws Exception{composed(args[0],new File(args[1]),Integer.parseInt(args[2]),args[3]);System.out.print("PASS actual_host_JNI_kernel_TCP; controlled_activation; no_Android_Wine_Game");}
'''


class OperationJniTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        receipt_path = Path(os.environ['COH_LIVE_TEST_JNI_RECEIPT']).resolve()
        value = json.loads(receipt_path.read_text())
        if value.get('status') not in ('passed', 'host-only-passed') or value.get('host_JNI') is not True:
            raise AssertionError('Authentic passing host-JNI build receipt required')
        for name, sha in CORE_PINS.items():
            if value['source_files'][name]['sha256'] != sha:
                raise AssertionError('JNI core source recipe differs: '+name)
        cls.library = receipt_path.parent / 'libcoh_live_directory-host.so'
        pin = {'bytes': cls.library.stat().st_size, 'sha256': hashlib.sha256(cls.library.read_bytes()).hexdigest()}
        if value['artifacts'][cls.library.name] != pin:
            raise AssertionError('Compiled helper differs from original passing build receipt')
        cls.pin = pin
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-live-operation-JNI-classes-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.classes = Path(cls.temporary.name)
        runtime = fixture.RUNTIME.read_text()
        start = runtime.index('List<String> command = new ArrayList<>(', runtime.index('private Result runCharacter('))
        command = runtime[start:runtime.index('ProcessBuilder builder =', start)]
        base = fixture.HARNESS.replace('ACTUAL_COMMAND', command)
        base = base[:base.index(' public static void main(String[] args)')]+HARNESS+'\n}\n'
        source = cls.classes / 'GuestNamespaceHost.java'
        source.write_text(base)
        cls.sources = [JAVA/name for name in ('ClientGuestNamespace.java', 'NativeLiveDirectory.java',
            'ClientLiveDirectoryService.java', 'ClientLiveDirectoryOperation.java')]
        cls.source_pins = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in cls.sources}
        result = subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
            '-d', str(cls.classes), *map(str, cls.sources), str(source)], capture_output=True, text=True, timeout=45)
        if result.returncode:
            raise AssertionError('JNI composition fixture compile failed: '+result.stderr)

    @classmethod
    def tearDownClass(cls):
        for path, sha in cls.source_pins.items():
            if hashlib.sha256(Path(path).read_bytes()).hexdigest() != sha:
                raise AssertionError('Source changed during real JNI composition controls')
        if hashlib.sha256(cls.library.read_bytes()).hexdigest() != cls.pin['sha256']:
            raise AssertionError('Reused compiled helper changed during execution')

    def control(self, mode):
        with tempfile.TemporaryDirectory(prefix='coh-live-operation-JNI-owned-') as temporary:
            result = subprocess.run(['java', '-Xcheck:jni', '-cp', str(self.classes),
                'io.github.russianranger.cohclientinteractive.GuestNamespaceHost', mode, temporary,
                str(os.getuid()), str(self.library)], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, 'PASS actual_host_JNI_kernel_TCP; controlled_activation; no_Android_Wine_Game')
            self.assertEqual(result.stderr, '')

    def test_actual_current_fields_order_geometry_and_held_identity(self): self.control('stable')
    def test_actual_guest_absolute_bound_link(self): self.control('absolute_link')
    def test_actual_guest_relative_owned_link(self): self.control('relative_link')
    def test_actual_relative_target_outside_selected_branch_declines_before_rows(self): self.control('relative_scope_decline')
    def test_actual_late_directory_retarget_terminal_without_retry(self): self.control('late_retarget')
