"""Run shipped installer methods against small host assets and archive adapters.

The filesystem, payload hashing, generation activation and repeat-setup path are
real. The adapter supplies tiny archive contents; this does not claim that a
device installation or extracted Linux/Wine runtime was executed.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_storage_ui import production_method

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'android/app/src/main/java/io/github/russianranger/cohdiagnostic/DiagnosticRuntime.java'
CONTROL = SOURCE.with_name('SetupMemoryGuard.java')
CLASS = 'io.github.russianranger.cohdiagnostic.RuntimeSetupHost'

HOST = r'''
package io.github.russianranger.cohdiagnostic;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.util.*;
class JSONObject {
    private static final Map<String,JSONObject> encoded=new HashMap<>();
    private static int serial;
    final Map<String,Object> values=new LinkedHashMap<>();
    JSONObject(){}
    JSONObject(Map<String,Object> values){this.values.putAll(values);}
    JSONObject(String raw)throws IOException {
        JSONObject original=encoded.get(raw);
        if(original==null)throw new IOException("Invalid host fixture JSON");
        for(Map.Entry<String,Object> row:original.values.entrySet())
            values.put(row.getKey(),row.getValue() instanceof JSONObject?new JSONObject(row.getValue().toString()):row.getValue());
    }
    JSONObject put(String key,Object value){values.put(key,value);return this;}
    Object get(String key){if(!values.containsKey(key))throw new IllegalArgumentException(key);return values.get(key);}
    JSONObject getJSONObject(String key){return (JSONObject)get(key);}
    String getString(String key){return (String)get(key);}
    long getLong(String key){return ((Number)get(key)).longValue();}
    int getInt(String key){return ((Number)get(key)).intValue();}
    boolean has(String key){return values.containsKey(key);}
    boolean optBoolean(String key){return Boolean.TRUE.equals(values.get(key));}
    Iterator<String> keys(){return values.keySet().iterator();}
    public String toString(){String token="host-json-"+(++serial);encoded.put(token,this);return token;}
}
class Build {static String[] SUPPORTED_ABIS={"arm64-v8a"};}
class CleanupGuard {static boolean blocked;static void requireClear()throws IOException{if(blocked)throw new IOException("cleanup blocked");}}
class Outcome {boolean cancelled;boolean cancelled(){return cancelled;}}
class MockHttp extends HttpURLConnection {
    static int requests;
    MockHttp(URL url){super(url);requests++;}
    public int getResponseCode(){return 200;}
    public InputStream getInputStream(){return new ByteArrayInputStream("base-archive".getBytes(StandardCharsets.UTF_8));}
    public void disconnect(){}public boolean usingProxy(){return false;}public void connect(){}
}
class HostContext {
    final Map<String,byte[]> assets=new HashMap<>();
    int opens;
    class Assets {InputStream open(String name)throws IOException{opens++;byte[] raw=assets.get(name);if(raw==null)throw new IOException("missing asset");return new ByteArrayInputStream(raw);}}
    Assets getAssets(){return new Assets();}
}
class TarExtractor {
    static int extracted, failAt;
    static boolean cancelling;
    static HostInstaller owner;
    interface Progress{void update(int count);}
    static void transfer(InputStream in,OutputStream out,long size)throws IOException {
        byte[] bytes=new byte[1024];while(size>0){int count=in.read(bytes,0,(int)Math.min(size,bytes.length));if(count<0)throw new EOFException();out.write(bytes,0,count);size-=count;}
    }
    static void transfer(InputStream in,FileOutputStream out,long size,SetupMemoryGuard control)throws IOException {
        byte[] bytes=new byte[1024];while(size>0){control.beforeIo();int count=in.read(bytes,0,(int)Math.min(size,bytes.length));if(count<0)throw new EOFException();control.read(count);out.write(bytes,0,count);control.written(count,()->out.getFD().sync());size-=count;}
        out.getFD().sync();control.synced();
    }
    static void file(File root,String name,String text)throws IOException {File target=new File(root,name);target.getParentFile().mkdirs();Files.write(target.toPath(),text.getBytes(StandardCharsets.UTF_8));}
    static void extract(File archive,File destination,Progress progress)throws Exception {
        extracted++;destination.mkdirs();
        if(extracted==failAt){file(destination,"interrupted-payload","partial");if(cancelling)owner.outcome.cancelled=true;throw new InterruptedIOException("fixture extraction stopped");}
        String name=destination.getName();
        if(name.equals("rootfs")){file(destination,"usr/bin/python3","python");file(destination,"usr/bin/Xtigervnc","display");}
        if(name.equals("wine")){file(destination,"bin/wine","wine");file(destination,"bin/wineserver","server");file(destination,"lsb-fex.json","fixture-wine-manifest");}
        if(name.equals("pg")){file(destination,"opt/coh/pgsql/bin/postgres","postgres");file(destination,"opt/coh/pgsql/bin/initdb","initdb");}
        if(name.equals("dbserver")||name.equals("schema"))file(destination,"fixture",name);
        progress.update(1);
    }
    static void extract(File archive,File destination,Progress progress,SetupMemoryGuard control)throws Exception {control.checkpoint();extract(archive,destination,progress);}
    static void remove(File root)throws IOException {
        Files.walkFileTree(root.toPath(),new SimpleFileVisitor<Path>(){
            public FileVisitResult visitFile(Path file,BasicFileAttributes attrs)throws IOException{Files.delete(file);return FileVisitResult.CONTINUE;}
            public FileVisitResult postVisitDirectory(Path dir,IOException failure)throws IOException{if(failure!=null)throw failure;Files.delete(dir);return FileVisitResult.CONTINUE;}
        });
    }
    static void remove(File root,SetupMemoryGuard control)throws IOException {control.beforeIo();remove(root);}
}
class HostInstaller {
    static final long MAX_REPORT=2L*1024*1024;
    final File home;
    final HostContext context;
    final Outcome outcome=new Outcome();
    File state,generation;
    JSONObject manifest,setupReceipt,published;
    String manifestHash;
    boolean cancelled;
    boolean memoryLow,memoryUnavailable,pressureOnAssets,cancelOnAssets,cancelOnHash,memoryAfterReady;
    long clockMillis;
    boolean setupCleanupDeferred;
    SetupMemoryGuard setupControl;
    HttpURLConnection connection;
    int supports;
    final List<String> stages=new ArrayList<>();
    interface Listener{void onStage(String name,String detail);}
    final Listener listener=(name,detail)->{};
    HostInstaller(File files,HostContext context){home=new File(files,"m2");state=new File(home,"state");this.context=context;TarExtractor.owner=this;}
    String appVersion(){return "fixture";}
    void stage(String name,String text){
        stages.add(text);
        if(name.equals("Copying runtime assets")&&pressureOnAssets){memoryLow=true;clockMillis+=250;}
        if(name.equals("Copying runtime assets")&&cancelOnAssets||name.equals("Verifying runtime asset")&&cancelOnHash){cancelled=true;outcome.cancelled=true;}
    }
    void setupProgress(String name,String text){stage(name,text);}
    SetupMemoryGuard setupMemoryControl(){return new SetupMemoryGuard(()->{
        if(memoryUnavailable)throw new IOException("fixture memory sensor unavailable");
        boolean low=memoryLow||memoryAfterReady&&new File(home,generation.getName()+".staging/ready.json").exists();
        return new SetupMemoryGuard.Sample(low?0:3L<<30,4L<<30,128L<<20,low,16L<<20,64L<<20);
    },()->clockMillis,millis->clockMillis+=millis,this::check);}
    static String clean(String text){return text;}
    void support(JSONObject report,boolean passed)throws IOException{supports++;published=report;File target=new File(home,"reports/setup-"+supports+".json");write(target,"bounded setup metadata".getBytes(StandardCharsets.UTF_8));}
    PRODUCTION_METHODS
}
public class RuntimeSetupHost {
    static void need(boolean value,String text){if(!value)throw new AssertionError(text);}
    interface Action{void run()throws Exception;}
    static void reject(Action action,String text)throws Exception{try{action.run();throw new AssertionError("accepted invalid setup");}catch(IOException expected){need(expected.getMessage().contains(text),expected.getMessage());}}
    static String digest(byte[] raw)throws Exception{return HostInstaller.hex(MessageDigest.getInstance("SHA-256").digest(raw));}
    static JSONObject pin(byte[] raw)throws Exception{return new JSONObject().put("bytes",(long)raw.length).put("sha256",digest(raw)).put("url","https://invalid.invalid/never-contact");}
    static HostContext assets()throws Exception {
        HostContext context=new HostContext();JSONObject files=new JSONObject();
        for(String name:new String[]{"postgresql-runtime.tar.gz","dbserver-package.tar.gz","dbserver-schema.tar.gz","fixture.txt"}) {
            byte[] raw=("pinned-"+name).getBytes(StandardCharsets.UTF_8);context.assets.put("runtime/"+name,raw);files.put(name,pin(raw));
        }
        JSONObject manifest=new JSONObject().put("format",1).put("files",files).put("fixture_revision",1);
        context.assets.put("runtime/runtime-manifest.json",manifest.toString().getBytes(StandardCharsets.UTF_8));
        JSONObject base=pin("base-archive".getBytes(StandardCharsets.UTF_8));
        JSONObject wine=pin("wine-archive".getBytes(StandardCharsets.UTF_8)).put("manifest_sha256",digest("fixture-wine-manifest".getBytes(StandardCharsets.UTF_8)));
        context.assets.put("runtime/runtime-lock.json",new JSONObject().put("base",base).put("wine",wine).toString().getBytes(StandardCharsets.UTF_8));return context;
    }
    static void downloads(HostInstaller installer)throws Exception {
        JSONObject lock=new JSONObject(new String(installer.context.assets.get("runtime/runtime-lock.json"),StandardCharsets.UTF_8));
        for(String[] row:new String[][]{{"base","database environment","base-archive"},{"wine","Windows runtime","wine-archive"}}) {
            File file=new File(installer.home,"downloads/"+row[1]+"-"+lock.getJSONObject(row[0]).getString("sha256")+".tar.gz");
            HostInstaller.write(file,row[2].getBytes(StandardCharsets.UTF_8));
        }
    }
    static Map<String,String> snapshot(File root)throws Exception {
        Map<String,String> tree=new TreeMap<>();
        Files.walkFileTree(root.toPath(),new SimpleFileVisitor<Path>(){
            void note(Path path,BasicFileAttributes attrs)throws IOException {
                try {String bytes=attrs.isRegularFile()?digest(Files.readAllBytes(path)):attrs.isSymbolicLink()?Files.readSymbolicLink(path).toString():"directory";
                    tree.put(root.toPath().relativize(path).toString(),bytes+"|"+attrs.lastModifiedTime()+"|"+attrs.fileKey());
                }catch(Exception e){throw new IOException(e);}
            }
            public FileVisitResult preVisitDirectory(Path path,BasicFileAttributes attrs)throws IOException{note(path,attrs);return FileVisitResult.CONTINUE;}
            public FileVisitResult visitFile(Path path,BasicFileAttributes attrs)throws IOException{note(path,attrs);return FileVisitResult.CONTINUE;}
        });return tree;
    }
    static void unchanged(File root,Map<String,String> before)throws Exception{need(before.equals(snapshot(root)),"protected runtime or user state changed");}
    static void zeroReuse(JSONObject receipt){need(receipt.getString("mode").equals("reused")&&Boolean.TRUE.equals(receipt.get("reused")),"reuse outcome");need(Boolean.FALSE.equals(receipt.get("installation_started"))&&Boolean.FALSE.equals(receipt.get("download_started"))&&Boolean.FALSE.equals(receipt.get("extraction_started")),"repeat install work");need(receipt.getLong("downloaded_archive_bytes")==0&&receipt.getInt("archives_extracted")==0&&receipt.getInt("runtime_payload_files_copied")==0,"repeat setup added large payloads");}
    public static void main(String[] args)throws Exception {
        File files=Files.createTempDirectory("runtime-reuse-").toFile();
        try {
            HostContext context=assets();HostInstaller installer=new HostInstaller(files,context);downloads(installer);
            File profile=new File(files,"client/state/diagnostic/android-local-login");TarExtractor.file(profile,"pgdata/keep","character database");
            File imported=new File(files,"client-import/generation-00000000000000000000000000000000/data");TarExtractor.file(imported,"keep","accepted import");
            File old=new File(installer.home,"runtime-0000000000000000");TarExtractor.file(old,"ready.json","owned old generation");
            Map<String,String> profileBefore=snapshot(profile),importBefore=snapshot(imported),oldBefore=snapshot(old);
            String scenario=args[0];
            if(scenario.equals("memory_low")||scenario.equals("memory_unknown")) {
                installer.memoryLow=scenario.equals("memory_low");installer.memoryUnavailable=scenario.equals("memory_unknown");
                reject(installer::setupRuntime,scenario.equals("memory_low")?"memory remained low":"memory information is unavailable");
                need(TarExtractor.extracted==0&&!installer.generation.exists(),"memory admission started installation");
                need(!Boolean.TRUE.equals(installer.getSetupReceipt().get("installation_started"))&&!Boolean.TRUE.equals(installer.getSetupReceipt().get("runtime_activated")),"memory admission claimed installation");
            }
            else if(scenario.equals("pressure_copy")||scenario.equals("asset_stop")||scenario.equals("hash_stop")||scenario.equals("pressure_ready")) {
                installer.pressureOnAssets=scenario.equals("pressure_copy");installer.cancelOnAssets=scenario.equals("asset_stop");installer.cancelOnHash=scenario.equals("hash_stop");installer.memoryAfterReady=scenario.equals("pressure_ready");
                reject(installer::setupRuntime,scenario.startsWith("pressure")?"memory remained low":"Diagnostic stopped");
                File partial=new File(installer.home,installer.generation.getName()+".staging");
                need(!installer.generation.exists()&&partial.isDirectory()&&!new File(partial,"ready.json").exists(),"interrupted staging was activated or marked ready");
                JSONObject receipt=installer.getSetupReceipt();
                need(Boolean.TRUE.equals(receipt.get("staging_cleanup_deferred"))&&!Boolean.TRUE.equals(receipt.get("runtime_activated")),"missing safe staging deferral");
                if(!scenario.equals("pressure_ready"))need(TarExtractor.extracted==2&&receipt.getInt("runtime_payload_files_copied")==0,"abort passed requested copy/hash boundary");
                HostInstaller retry=new HostInstaller(files,context);retry.setupRuntime();
                need(retry.generation.isDirectory()&&!partial.exists(),"healthy retry did not retire only owned staging and activate");
            }
            else if(scenario.equals("download")) {
                JSONObject lock=new JSONObject(new String(context.assets.get("runtime/runtime-lock.json"),StandardCharsets.UTF_8));
                File cached=new File(installer.home,"downloads/database environment-"+lock.getJSONObject("base").getString("sha256")+".tar.gz");cached.delete();
                URL.setURLStreamHandlerFactory(protocol->protocol.equals("https")?new URLStreamHandler(){protected URLConnection openConnection(URL url){return new MockHttp(url);}}:null);
                installer.setupRuntime();JSONObject receipt=installer.getSetupReceipt();
                need(MockHttp.requests==1&&Boolean.TRUE.equals(receipt.get("download_started"))&&receipt.getLong("downloaded_archive_bytes")=="base-archive".getBytes(StandardCharsets.UTF_8).length,"download telemetry not verified");
                need(cached.isFile()&&!new File(cached.getParentFile(),cached.getName()+".part").exists(),"download did not activate verified archive");
                Map<String,String> before=snapshot(installer.generation);installer.setupRuntime();zeroReuse(installer.getSetupReceipt());unchanged(installer.generation,before);need(MockHttp.requests==1,"repeat setup downloaded again");
            }
            else if(scenario.equals("cached_corrupt")) {
                JSONObject lock=new JSONObject(new String(context.assets.get("runtime/runtime-lock.json"),StandardCharsets.UTF_8));
                File cached=new File(installer.home,"downloads/database environment-"+lock.getJSONObject("base").getString("sha256")+".tar.gz");byte[] bytes=Files.readAllBytes(cached.toPath());bytes[0]^=1;Files.write(cached.toPath(),bytes);
                reject(installer::setupRuntime,"Runtime integrity check failed");need(TarExtractor.extracted==0&&!installer.generation.exists(),"corrupt archive extracted");
                need(!Boolean.TRUE.equals(installer.getSetupReceipt().get("download_started"))&&installer.getSetupReceipt().getLong("downloaded_archive_bytes")==0,"cache validation claimed download");
            }
            else if(scenario.equals("abi")){Build.SUPPORTED_ABIS=new String[]{"armeabi-v7a"};reject(installer::setupRuntime,"ARM64");need(TarExtractor.extracted==0&&!installer.generation.exists(),"wrong ABI installed");}
            else if(scenario.equals("guard")){CleanupGuard.blocked=true;reject(installer::setupRuntime,"cleanup blocked");need(TarExtractor.extracted==0&&installer.supports==0&&installer.getSetupReceipt()==null,"blocked setup touched installation");}
            else if(scenario.equals("cancel")||scenario.equals("extract_failure")) {
                TarExtractor.failAt=2;TarExtractor.cancelling=scenario.equals("cancel");reject(installer::setupRuntime,"fixture extraction stopped");
                File partial=new File(installer.home,installer.generation.getName()+".staging");
                need(!installer.generation.exists()&&partial.exists()==scenario.equals("cancel"),"partial runtime cleanup or deferral");
                need(!new File(partial,"ready.json").exists(),"deferred staging retained success marker");
                need(Boolean.TRUE.equals(installer.getSetupReceipt().get("staging_cleanup_deferred"))==scenario.equals("cancel"),"staging cleanup deferral receipt");
                need(installer.getSetupReceipt().getString("mode").equals(scenario.equals("cancel")?"cancelled":"failed"),"failure mode");
                need(installer.getSetupReceipt().getInt("archives_extracted")==1&&!Boolean.TRUE.equals(installer.getSetupReceipt().get("runtime_activated")),"false extraction success");
            } else {
                installer.setupRuntime();need(TarExtractor.extracted==5&&installer.supports==1,"fixture did not install once");
                File current=installer.generation;Map<String,String> before=snapshot(current);
                JSONObject installed=installer.getSetupReceipt();
                if(scenario.equals("installed")) {
                    need(installed.getString("mode").equals("installed")&&Boolean.TRUE.equals(installed.get("runtime_activated")),"installed outcome");
                    need(installed.getInt("archives_extracted")==5&&installed.getInt("runtime_payload_files_copied")==4,"extract/copy telemetry");
                    need(!Boolean.TRUE.equals(installed.get("download_started"))&&installed.getLong("downloaded_archive_bytes")==0,"cached download fetched again");
                    long logical=0;for(String name:context.assets.keySet())if(!name.endsWith("manifest.json")&&!name.endsWith("lock.json"))logical+=context.assets.get(name).length;
                    need(installed.getLong("packaged_runtime_asset_logical_bytes")==logical,"logical asset count");
                    need(installed.getJSONObject("storage_observation").getString("scope").contains("not app allocated usage"),"filesystem free space misattributed");
                } else if(scenario.equals("repeat")) {
                    for(int i=0;i<5;i++){installer.setupRuntime();zeroReuse(installer.getSetupReceipt());unchanged(current,before);}
                    need(TarExtractor.extracted==5&&installer.supports==6,"repeated extraction or missing report");
                    need(installer.getSetupReceipt().getJSONObject("storage_observation").getInt("runtime_generation_directories")==2,"extra runtime generations");
                    need(installer.stages.stream().anyMatch(text->text.contains("no runtime files were added")),"reuse message unavailable");
                } else if(scenario.equals("changed")) {
                    JSONObject next=new JSONObject(new String(context.assets.get("runtime/runtime-manifest.json"),StandardCharsets.UTF_8));next.put("fixture_revision",2);
                    context.assets.put("runtime/runtime-manifest.json",next.toString().getBytes(StandardCharsets.UTF_8));installer.setupRuntime();
                    need(!current.equals(installer.generation)&&TarExtractor.extracted==10,"different manifest was not isolated");unchanged(current,before);
                    need(installer.getSetupReceipt().getJSONObject("storage_observation").getInt("runtime_generation_directories")==3,"generation count");
                } else if(scenario.equals("corrupt")) {
                    File bad=new File(current,"assets/fixture.txt");byte[] bytes=Files.readAllBytes(bad.toPath());bytes[0]^=1;Files.write(bad.toPath(),bytes);
                    Map<String,String> damaged=snapshot(current);reject(installer::setupRuntime,"Runtime integrity check failed");unchanged(current,damaged);
                    need(TarExtractor.extracted==5&&installer.getSetupReceipt().getString("mode").equals("failed"),"corrupt runtime silently replaced");
                } else if(scenario.equals("missing")) {
                    new File(current,"rootfs/usr/bin/python3").delete();Map<String,String> damaged=snapshot(current);reject(installer::setupRuntime,"Incomplete runtime");unchanged(current,damaged);need(TarExtractor.extracted==5,"missing executable silently replaced");
                } else if(scenario.equals("count")) {
                    Path foreign=Files.createTempDirectory("foreign-runtime-");Files.createSymbolicLink(new File(installer.home,"runtime-1111111111111111").toPath(),foreign);
                    installer.setupRuntime();need(installer.getSetupReceipt().getJSONObject("storage_observation").getInt("runtime_generation_directories")==2,"followed foreign runtime link");
                    for(int i=0;i<600;i++)new File(installer.home,"unclassified-"+i).createNewFile();
                    installer.setupRuntime();JSONObject observation=installer.getSetupReceipt().getJSONObject("storage_observation");
                    need(Boolean.FALSE.equals(observation.get("generation_count_complete"))&&observation.getInt("directory_entry_limit")==512,"unbounded or falsely complete directory count");unchanged(current,before);Files.delete(foreign);
                } else if(scenario.equals("copy")) {
                    JSONObject receipt=installer.getSetupReceipt();receipt.put("mode","changed_by_caller");receipt.getJSONObject("storage_observation").put("runtime_generation_directories",999);
                    need(installer.getSetupReceipt().getString("mode").equals("installed")&&installer.getSetupReceipt().getJSONObject("storage_observation").getInt("runtime_generation_directories")==2,"receipt exposed mutable internals");
                } else throw new AssertionError("unknown scenario");
            }
            unchanged(profile,profileBefore);unchanged(imported,importBefore);unchanged(old,oldBefore);
            System.out.println("PASS "+scenario);
        } finally {TarExtractor.remove(files);}
    }
}
'''


class RuntimeSetupReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-setup-reuse-host-')
        cls.classes = Path(cls.temporary.name)
        source = SOURCE.read_text()
        methods = [production_method(source, signature) for signature in (
            'public void setupRuntime(', 'public JSONObject getSetupReceipt(',
            'private void loadManifest(', 'private void validateInstalled(',
            'private void verify(', 'private File download(',
            'private static void required(', 'private static byte[] read(File ',
            'private static byte[] read(InputStream ', 'private static void write(',
            'private static String hex(', 'private String sha(', 'private void check(')]
        java = HOST.replace('PRODUCTION_METHODS', '\n'.join(methods))
        # Host fixture helper calls the exact shipped hash/writer helpers.
        java = java.replace('private static void write(', 'static void write(').replace(
            'private static String hex(', 'static String hex(')
        target = cls.classes / 'RuntimeSetupHost.java'
        target.write_text(java)
        result = subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                                 '-d', str(cls.classes), str(target), str(CONTROL)], capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def check(self, *scenarios):
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                result = subprocess.run(['java', '-Xmx64m', '-cp', str(self.classes), CLASS, scenario],
                                        capture_output=True, text=True, timeout=20)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual('PASS ' + scenario, result.stdout.strip())

    def test_first_install_records_cached_downloads_extracts_and_logical_asset_bytes(self):
        self.check('installed')

    def test_download_receipt_counts_only_verified_archives_and_reuses_them(self):
        self.check('download')

    def test_corrupt_cached_archive_is_rejected_before_extraction(self):
        self.check('cached_corrupt')

    def test_five_repeat_setups_keep_identical_runtime_tree_without_large_allocations(self):
        self.check('repeat')

    def test_changed_manifest_retains_previous_runtime_and_user_data(self):
        self.check('changed')

    def test_changed_pinned_asset_is_rejected_without_silent_reinstallation(self):
        self.check('corrupt')

    def test_missing_executable_is_rejected_without_resetting_data(self):
        self.check('missing')

    def test_wrong_abi_or_cleanup_guard_prevents_installation(self):
        self.check('abi', 'guard')

    def test_failure_cleanup_and_prompt_cancel_deferral_preserve_previous_data(self):
        self.check('cancel', 'extract_failure')

    def test_generation_count_is_bounded_and_does_not_follow_symlinks(self):
        self.check('count')

    def test_setup_receipt_is_a_defensive_copy(self):
        self.check('copy')

    def test_pressure_or_unknown_memory_prevents_installation_and_preserves_user_data(self):
        self.check('memory_low','memory_unknown')

    def test_stop_inside_asset_copy_or_hash_defers_only_unactivated_staging_and_retry_recovers(self):
        self.check('asset_stop','hash_stop')

    def test_pressure_at_copy_or_ready_boundary_never_activates_partial_generation(self):
        self.check('pressure_copy','pressure_ready')


if __name__ == '__main__':
    unittest.main()
