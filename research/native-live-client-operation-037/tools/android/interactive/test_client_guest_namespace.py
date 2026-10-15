"""Execute the dormant production descriptor against actual finalized launcher argv.

Uses the JRE compiler module when javac is not on PATH. This is pure Java host
qualification, not PRoot/Wine/Android/native FD or player-data qualification.
"""
from pathlib import Path
import hashlib
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
SOURCE = JAVA / 'ClientGuestNamespace.java'
RUNTIME = JAVA / 'ClientRuntime.java'

HARNESS = r'''
package io.github.russianranger.cohclientinteractive;
import java.io.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
public final class GuestNamespaceHost {
 static final String RUN="1792000000000-abcdef012345", SESSION="0123456789abcdef0123456789abcdef";
 static final String PROCESS="12345678-1234-1234-1234-123456789abc";
 static final String DATA="/state/diagnostic/client-work-0123456789abcdef01234567/data";
 static String repeat(char value,int count){char[] c=new char[count];Arrays.fill(c,value);return new String(c);}
 static void require(boolean value,String note){if(!value)throw new AssertionError(note);}
 static final class Imported {final File dataDirectory; Imported(File root){dataDirectory=new File(root,"data");}}
 static final class Manifest {final boolean only; Manifest(boolean value){only=value;}Object opt(String key){return only;}}
 static Fixture current;
 static boolean zoningEnabled(){return current.mode.zoning;}
 static final class Fixture {
  final File base,files,nativeRoot,generation,report,importRoot;
  final ClientGuestNamespace.Provenance identity;
  final ClientGuestNamespace.LaunchMode mode;
  final ClientGuestNamespace.Inputs inputs;
  final Map<String,String> environment=new HashMap<String,String>();
  Fixture(File root,boolean reopen,boolean resume,boolean only,boolean zones,String run,String session,
    String process,int uid,String runtimeSha,String consumerSha,long consumerBytes,String helperSha)throws Exception {
   base=root;files=new File(base,"files");nativeRoot=new File(base,"apk-native");
   identity=new ClientGuestNamespace.Provenance(run,session,process,uid,runtimeSha,consumerSha,consumerBytes,helperSha);
   mode=new ClientGuestNamespace.LaunchMode(reopen,resume,only,zones,"performance","turnip");
   inputs=new ClientGuestNamespace.Inputs(files,nativeRoot,"generation-"+repeat('d',32),identity,mode);
   generation=new File(files,"m2/runtime-"+runtimeSha.substring(0,16));
   report=new File(files,"client/reports/"+run);importRoot=new File(files,"client-import/"+inputs.importGeneration);
   for(String name:new String[]{"rootfs","assets","wine","pg/opt/coh/pgsql"})new File(generation,name).mkdirs();
   for(File file:new File[]{new File(files,"client/state"),new File(report,"tmp"),new File(files,"s"),new File(files,"p"),
     new File(importRoot,"data"),nativeRoot})file.mkdirs();
   for(File file:new File[]{new File(report,"hosts"),new File(generation,"passwd"),new File(generation,"group")})
     try(FileOutputStream stream=new FileOutputStream(file)){stream.write("controlled host fixture\n".getBytes(StandardCharsets.US_ASCII));}
   environment.put("PROOT_LOADER",new File(nativeRoot,"libproot-loader.so").getPath());
   environment.put("PROOT_TMP_DIR",new File(files,"p").getCanonicalPath());environment.put("PROOT_NO_SECCOMP","1");
   environment.put("UNRELATED_FIXTURE_VAR","bounded_fixture_value");
  }
 }
 static Fixture fixture(File base)throws Exception{return new Fixture(base,true,false,false,true,RUN,SESSION,PROCESS,10303,
   repeat('a',64),repeat('b',64),9487872,repeat('c',64));}
 static List<String> finalized(Fixture f)throws Exception {
  current=f;File generation=f.generation,root=new File(generation,"rootfs"),state=new File(f.files,"client/state"),
   tmp=new File(f.report,"tmp"),socketDir=new File(f.files,"s"),guestHosts=new File(f.report,"hosts");
  File proot=new File(f.nativeRoot,"libproot.so");Imported imported=new Imported(f.importRoot);
  boolean reopen=f.mode.reopen,resumeFirstCreation=f.mode.resumeEmptyProfile;
  Manifest manifest=new Manifest(f.mode.startupOnly);String session=f.identity.sessionId;
  String graphicsProfileRequested=f.mode.graphics,gpuProfileRequested=f.mode.gpu;
  ACTUAL_COMMAND
  return command;
 }
 static ClientGuestNamespace build(Fixture f)throws Exception{return ClientGuestNamespace.fromFinalizedCommand(finalized(f),f.environment,f.inputs);}
 interface Checked {void run()throws Exception;}
 static void refusal(Checked body)throws Exception {boolean refused=false;try{body.run();}catch(IOException expected){refused=true;}
  require(refused,"expected fail-closed IOException");}
 static String digest(String text)throws Exception {byte[] h=MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8));
  StringBuilder result=new StringBuilder();for(byte b:h)result.append(String.format(Locale.ROOT,"%02x",b&255));return result.toString();}
 static void closed(ClientGuestNamespace descriptor){require(!descriptor.nativeRegistrationAllowed()&&!descriptor.rootMetadataVerified(),"provenance cannot grant native authority");}
 static void mainCase(String name,File base)throws Exception {
  Fixture f=fixture(base);ClientGuestNamespace n=build(f);closed(n);
  if(name.equals("actual_bindings")) {
   require(n.bindings().size()==14&&n.ownedDirectoryBindings().size()==7,"full table excludes rootfs/file/passthrough from DIR admission");
   require(n.route("/game-import/data/fx/a.fx").binding.hostRoot.equals(f.importRoot.getCanonicalPath()),"imported parent rather than data");
   require(n.route("/game-import/data/fx/a.fx").relativePath.equals("data/fx/a.fx"),"guest symlink target routes inside import FD");
   require(n.route("/state/diagnostic").binding.hostRoot.equals(new File(f.files,"client/state").getCanonicalPath()),"state root");
   require(n.route("/opt/coh/pgsql/bin/pg_ctl").binding.hostRoot.equals(new File(f.generation,"pg/opt/coh/pgsql").getCanonicalPath()),"longest nested DIR binding");
   require(n.route("/opt/coh/pgsqlx/a").binding.hostRoot.equals(new File(f.generation,"assets").getCanonicalPath()),"component boundary excludes partial nested prefix");
   require(n.route("/etc/hosts").binding.kind==ClientGuestNamespace.Kind.FILE,"file binding retained as diagnostics");
   require(n.route("/proc/123/status").binding.kind==ClientGuestNamespace.Kind.PASSTHROUGH,"passthrough remains unowned");
  } else if(name.equals("initial_scope")) {
   for(String path:new String[]{DATA+"/fx",DATA+"/fx/sub",DATA+"/SCRIPTS.LOC",DATA+"/Scripts.Loc/named",DATA+"/FX/sub"}) {
    ClientGuestNamespace.Route route=n.initialCensusDirectory(path,DATA);require(route.guestPath.equals(path),"preserve branch spelling for native actual-case resolution");
   }
   for(final String path:new String[]{DATA,DATA+"/scripts",DATA+"/texture_library",DATA+"/object_library",DATA+"/player_library",DATA+"/fx2",DATA+"/scripts.loc2",
      "/game-import/data/fx","/state/diagnostic/character-login-profile","/tmp/fx","/proc/fx"})
    refusal(new Checked(){public void run()throws Exception{n.initialCensusDirectory(path,DATA);}});
  } else if(name.equals("path_refusals")) {
   for(final String path:new String[]{"/state2/a","/game-imported/a","/opt/wine2/a","/usr/bin","/","state/a","Z:/state/a","/STATE/a",
     "/state/../proc","/state/./a","/state//a","/state/a/","/state/a\\b","/state/a:b","/state/.l2s.AAAA","/state/a.l2s.123",
     "/state/a.","/state/a ","/state/"+repeat('x',256),"/state/\u00e9","/state/\u0000"})
    refusal(new Checked(){public void run()throws Exception{n.route(path);}});
   refusal(new Checked(){public void run()throws Exception{n.route("/etc/hosts/child");}});
  } else if(name.equals("immutability")) {
   List<String> args=finalized(f);Map<String,String> env=new HashMap<String,String>(f.environment);
   ClientGuestNamespace copied=ClientGuestNamespace.fromFinalizedCommand(args,env,f.inputs);String before=copied.sha256();
   args.clear();env.clear();require(copied.finalizedArgv().size()>70&&copied.finalizedEnvironment().size()==4&&before.equals(copied.sha256()),"snapshot caller lists/maps");
   try{copied.bindings().clear();throw new AssertionError("mutable bindings");}catch(UnsupportedOperationException good){}
   try{copied.ownedDirectoryBindings().clear();throw new AssertionError("mutable DIR table");}catch(UnsupportedOperationException good){}
   try{copied.finalizedArgv().clear();throw new AssertionError("mutable argv");}catch(UnsupportedOperationException good){}
   try{copied.finalizedEnvironment().clear();throw new AssertionError("mutable environment");}catch(UnsupportedOperationException good){}
   byte[] wire=copied.operationWireIdentity();require(wire.length==16&&wire[0]==1,"wire derives session32, not actual runId");wire[0]=0;
   require(copied.operationWireIdentity()[0]==1,"wire defensive copy");
   String[] components=copied.route("/state/a/b").relativeComponents();components[0]="changed";
   require(copied.route("/state/a/b").relativeComponents()[0].equals("a"),"route components defensive copy");
  } else if(name.equals("statement")) {
   require(n.canonicalStatement().startsWith("COH_GUEST_NAMESPACE_V1\n")&&digest(n.canonicalStatement()).equals(n.sha256()),"exact statement SHA");
   require(n.canonicalStatement().contains("authority:15:provenance_only")&&!n.canonicalStatement().contains("bounded_fixture_value"),"provenance only; unrelated env values not exported");
   Map<String,String> reordered=new LinkedHashMap<String,String>();List<String> keys=new ArrayList<String>(f.environment.keySet());Collections.reverse(keys);
   for(String key:keys)reordered.put(key,f.environment.get(key));
   require(n.sha256().equals(ClientGuestNamespace.fromFinalizedCommand(finalized(f),reordered,f.inputs).sha256()),"environment order-independent exact hash");
   reordered.put("UNRELATED_FIXTURE_VAR","changed");require(!n.sha256().equals(ClientGuestNamespace.fromFinalizedCommand(finalized(f),reordered,f.inputs).sha256()),"full inherited environment bound by hash");
  } else if(name.equals("launch_modes")) {
   int counter=0;for(boolean reopen:new boolean[]{false,true})for(boolean resume:new boolean[]{false,true})for(boolean only:new boolean[]{false,true})for(boolean zones:new boolean[]{false,true}) {
    if((reopen&&resume)||(!reopen&&only))continue;
    Fixture other=new Fixture(new File(base,"mode"+(counter++)),reopen,resume,only,zones,RUN,SESSION,PROCESS,10303,repeat('a',64),repeat('b',64),9487872,repeat('c',64));closed(build(other));
   }require(counter==8,"all valid finalized mode combinations");
  } else if(name.equals("identity_changes")) {
   for(int index=0;index<8;index++) {
    Fixture other=new Fixture(new File(base,"identity"+index),true,false,false,true,
     index==0?"1792000000001-abcdef012345":RUN,index==1?repeat('2',32):SESSION,
     index==2?"12345678-1234-1234-1234-123456789abd":PROCESS,index==3?10304:10303,
     index==4?repeat('e',64):repeat('a',64),index==5?repeat('f',64):repeat('b',64),index==6?9487873:9487872,index==7?repeat('e',64):repeat('c',64));
    ClientGuestNamespace changed=build(other);closed(changed);require(!n.sha256().equals(changed.sha256()),"changed exact identity changes statement");
   }
  } else if(name.equals("input_refusals")) {
   for(final String bad:new String[]{"abc",repeat('A',64),repeat('a',63),repeat('a',65)})
    refusal(new Checked(){public void run()throws Exception{new ClientGuestNamespace.Provenance(RUN,SESSION,PROCESS,10303,bad,repeat('b',64),1,repeat('c',64));}});
   refusal(new Checked(){public void run()throws Exception{new ClientGuestNamespace.Provenance(repeat('a',32),SESSION,PROCESS,1,repeat('a',64),repeat('b',64),1,repeat('c',64));}});
   refusal(new Checked(){public void run()throws Exception{new ClientGuestNamespace.Provenance(RUN,repeat('A',32),PROCESS,1,repeat('a',64),repeat('b',64),1,repeat('c',64));}});
   refusal(new Checked(){public void run()throws Exception{new ClientGuestNamespace.Provenance(RUN,SESSION,"process",1,repeat('a',64),repeat('b',64),1,repeat('c',64));}});
   refusal(new Checked(){public void run()throws Exception{new ClientGuestNamespace.Provenance(RUN,SESSION,PROCESS,-1,repeat('a',64),repeat('b',64),1,repeat('c',64));}});
   refusal(new Checked(){public void run()throws Exception{new ClientGuestNamespace.Provenance(RUN,SESSION,PROCESS,1,repeat('a',64),repeat('b',64),0,repeat('c',64));}});
   refusal(new Checked(){public void run()throws Exception{new ClientGuestNamespace.Provenance(RUN,SESSION,PROCESS,1,repeat('a',64),repeat('b',64),67108865,repeat('c',64));}});
   refusal(new Checked(){public void run()throws Exception{new ClientGuestNamespace.Inputs(f.files,f.nativeRoot,"../generation",f.identity,f.mode);}});
   refusal(new Checked(){public void run()throws Exception{new ClientGuestNamespace.LaunchMode(true,true,false,true,"performance","turnip");}});
   refusal(new Checked(){public void run()throws Exception{new ClientGuestNamespace.LaunchMode(false,false,true,true,"performance","turnip");}});
   refusal(new Checked(){public void run()throws Exception{new ClientGuestNamespace.LaunchMode(true,false,false,true,"unknown","turnip");}});
   refusal(new Checked(){public void run()throws Exception{new ClientGuestNamespace.LaunchMode(true,false,false,true,"performance","unknown");}});
  } else if(name.equals("host_escape")) {
   File assets=new File(f.generation,"assets");Files.delete(assets.toPath());File foreign=new File(base,"foreign");foreign.mkdir();
   Files.createSymbolicLink(assets.toPath(),foreign.toPath());refusal(new Checked(){public void run()throws Exception{build(f);}});
  } else if(name.equals("host_alias")) {
   File assets=new File(f.generation,"assets");Files.delete(assets.toPath());File other=new File(f.files,"unrelated");other.mkdir();
   Files.createSymbolicLink(assets.toPath(),other.toPath());refusal(new Checked(){public void run()throws Exception{build(f);}});
  } else if(name.startsWith("argv_")) {
   final List<String> command=finalized(f);String change=name.substring(5);
   if(change.equals("missing_final_flag"))command.remove("--zoning");
   else if(change.equals("unexpected_flag"))command.add("--unqualified-native-mode");
   else if(change.equals("duplicate_bind")){int position=command.indexOf("-w");command.addAll(position,Arrays.asList("-b",new File(f.files,"client/state").getPath()+":/state"));}
   else if(change.equals("unknown_bind")){int position=command.indexOf("-w");command.addAll(position,Arrays.asList("-b",new File(f.files,"client/state").getPath()+":/unknown"));}
   else if(change.equals("foreign_bind"))command.set(command.indexOf(new File(f.files,"client/state").getPath()+":/state"),new File(base,"foreign").getPath()+":/state");
   else if(change.equals("partial_private_prefix"))command.set(command.indexOf(new File(f.files,"client/state").getPath()+":/state"),new File(base,"files2/client/state").getPath()+":/state");
   else if(change.equals("import_data_not_parent"))command.set(command.indexOf(f.importRoot.getCanonicalPath()+":/game-import"),new File(f.importRoot,"data").getPath()+":/game-import");
   else if(change.equals("uppercase_bind"))command.set(command.indexOf(f.importRoot.getCanonicalPath()+":/game-import"),f.importRoot.getCanonicalPath()+":/GAME-IMPORT");
   else if(change.equals("nested_bind"))command.set(command.indexOf(new File(f.generation,"pg/opt/coh/pgsql").getPath()+":/opt/coh/pgsql"),new File(f.generation,"assets").getPath()+":/opt/coh/pgsql");
   else if(change.equals("uid"))command.set(command.indexOf("1000:1000"),"0:0");
   else if(change.equals("no_l2s_flag"))command.remove("--link2symlink");
   else if(change.equals("userland"))command.add(1,"--userland");
   else if(change.equals("rootfs"))command.set(command.indexOf(new File(f.generation,"rootfs").getPath()),new File(f.files,"foreign-rootfs").getPath());
   else if(change.equals("helper"))command.set(0,new File(f.nativeRoot,"foreign-proot.so").getPath());
   else if(change.equals("session"))command.set(command.indexOf("--session-id")+1,repeat('e',32));
   else if(change.equals("mode"))command.set(command.indexOf("/opt/coh/character_reopen_diagnostic.py"),"/opt/coh/character_creation_diagnostic.py");
   else if(change.equals("nul"))command.set(0,"bad\u0000");
   else throw new AssertionError("unknown command control");
   refusal(new Checked(){public void run()throws Exception{ClientGuestNamespace.fromFinalizedCommand(command,f.environment,f.inputs);}});
  } else if(name.startsWith("env_")) {
   String change=name.substring(4);
   if(change.equals("missing_loader"))f.environment.remove("PROOT_LOADER");
   else if(change.equals("loader"))f.environment.put("PROOT_LOADER",new File(base,"foreign.so").getPath());
   else if(change.equals("tmp"))f.environment.put("PROOT_TMP_DIR",new File(base,"foreign").getPath());
   else if(change.equals("seccomp"))f.environment.put("PROOT_NO_SECCOMP","0");
   else if(change.equals("rootfs"))f.environment.put("PROOT_ROOTFS",f.files.getPath());
   else if(change.equals("userland"))f.environment.put("USERLAND_ROOTFS",f.files.getPath());
   else if(change.equals("bad_key"))f.environment.put("BAD=KEY","x");
   else if(change.equals("oversized"))f.environment.put("BOUNDED",repeat('x',4097));
   else if(change.equals("nul"))f.environment.put("BOUNDED","a\u0000");
   else throw new AssertionError("unknown env control");
   refusal(new Checked(){public void run()throws Exception{build(f);}});
  } else throw new AssertionError("unknown test");
 }
 public static void main(String[] args)throws Exception{mainCase(args[0],new File(args[1]));System.out.print("PASS");}
}
'''


class ClientGuestNamespaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_pin = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        cls.runtime_bytes = RUNTIME.read_bytes()
        runtime = cls.runtime_bytes.decode()
        start = runtime.index('List<String> command = new ArrayList<>(', runtime.index('private Result runCharacter('))
        end = runtime.index('ProcessBuilder builder =', start)
        command = runtime[start:end]
        cls.classes_temp = tempfile.TemporaryDirectory(prefix='coh-guest-namespace-classes-')
        cls.addClassCleanup(cls.classes_temp.cleanup)
        cls.classes = Path(cls.classes_temp.name)
        harness = cls.classes / 'GuestNamespaceHost.java'
        harness.write_text(HARNESS.replace('ACTUAL_COMMAND', command))
        compiled = subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                                   '-d', str(cls.classes), str(SOURCE), str(harness)],
                                  text=True, capture_output=True, timeout=60)
        if compiled.returncode:
            raise AssertionError('Actual descriptor/harness compile failed: ' + compiled.stderr)

    @classmethod
    def tearDownClass(cls):
        if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != cls.source_pin:
            raise AssertionError('Descriptor source changed during execution')
        if RUNTIME.read_bytes() != cls.runtime_bytes:
            raise AssertionError('Finalized launcher source changed during execution')

    def execute(self, name):
        with tempfile.TemporaryDirectory(prefix='coh-guest-namespace-owned-') as directory:
            result = subprocess.run(['java', '-cp', str(self.classes),
                                     'io.github.russianranger.cohclientinteractive.GuestNamespaceHost', name, directory],
                                    text=True, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, 'PASS')

    def test_actual_finalized_bindings_and_longest_component_boundaries(self): self.execute('actual_bindings')
    def test_initial_scope_preserves_original_LOC_case_and_declines_future_branches(self): self.execute('initial_scope')
    def test_unknown_paths_aliases_dot_escapes_and_legacy_links_decline(self): self.execute('path_refusals')
    def test_collections_environment_routes_and_wire_identity_are_immutable(self): self.execute('immutability')
    def test_canonical_statement_exact_hash_and_environment_binding(self): self.execute('statement')
    def test_all_eight_actual_finalized_launch_modes(self): self.execute('launch_modes')
    def test_every_declared_owner_source_identity_changes_provenance_without_authority(self): self.execute('identity_changes')
    def test_exact_typed_input_and_identity_refusals(self): self.execute('input_refusals')
    def test_canonical_root_escape_declines(self): self.execute('host_escape')
    def test_unknown_canonical_alias_inside_private_fence_declines(self): self.execute('host_alias')


def control_test(name):
    def test(self): self.execute(name)
    return test


for _name in (
    'missing_final_flag', 'unexpected_flag', 'duplicate_bind', 'unknown_bind', 'foreign_bind',
    'partial_private_prefix', 'import_data_not_parent', 'uppercase_bind', 'nested_bind', 'uid',
    'no_l2s_flag', 'userland', 'rootfs', 'helper', 'session', 'mode', 'nul',
):
    setattr(ClientGuestNamespaceTests, 'test_finalized_argv_refuses_' + _name, control_test('argv_' + _name))
for _name in ('missing_loader', 'loader', 'tmp', 'seccomp', 'rootfs', 'userland', 'bad_key', 'oversized', 'nul'):
    setattr(ClientGuestNamespaceTests, 'test_finalized_environment_refuses_' + _name, control_test('env_' + _name))


if __name__ == '__main__':
    unittest.main()
