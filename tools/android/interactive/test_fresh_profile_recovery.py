"""Execute the shipped fresh-profile preflight and ordinary creator-save policy."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from test_storage_ui import production_method

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
HOST = r'''
package io.github.russianranger.cohclientinteractive;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.*;
class Context {
    final File root;Context(File root){this.root=root;}
    Context getApplicationContext(){return this;}File getFilesDir(){return root;}
}
class StorageFiles implements StorageAudit.Fs {
    static Map<String,Object> marker,credentials;static boolean readFailure;
    final Path root;
    StorageFiles(File root){this.root=root.toPath();}
    public StorageAudit.Stat stat(String name)throws IOException {
        Path path=root.resolve(name);BasicFileAttributes attrs;
        try{attrs=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);}
        catch(NoSuchFileException missing){return null;}
        StorageAudit.Kind kind=attrs.isSymbolicLink()?StorageAudit.Kind.SYMLINK:attrs.isDirectory()?StorageAudit.Kind.DIRECTORY:attrs.isRegularFile()?StorageAudit.Kind.FILE:StorageAudit.Kind.OTHER;
        long links=((Number)Files.getAttribute(path,"unix:nlink",LinkOption.NOFOLLOW_LINKS)).longValue();
        return new StorageAudit.Stat(kind,1,1,links,attrs.size(),1,1,1);
    }
    public byte[] read(String name,int limit)throws IOException {
        if(readFailure)throw new IOException("private identity unavailable");
        StorageAudit.Stat value=stat(name);
        if(value==null||value.kind!=StorageAudit.Kind.FILE||value.links!=1||value.size>limit)throw new IOException("not a bounded private file");
        return Files.readAllBytes(root.resolve(name));
    }
    public Map<String,Object> json(byte[] bytes)throws IOException {
        String text=new String(bytes,StandardCharsets.UTF_8);
        if(text.equals("marker"))return new LinkedHashMap<>(marker);
        if(text.equals("credentials"))return new LinkedHashMap<>(credentials);
        throw new IOException("identity JSON unreadable");
    }
    public String rootPath(){return root.toString();}
    public String readLink(String path){throw new AssertionError("preflight must not follow links");}
    public List<String> list(String path){throw new AssertionError("preflight must not enumerate assets or the database");}
    public Map<String,Object> reportIdentity(String path,int limit){throw new AssertionError();}
    public void unlink(String path){throw new AssertionError("preflight cannot remove data");}
    public void rmdir(String path){throw new AssertionError("preflight cannot remove data");}
    public long nowMillis(){return 1;}
}
class JSONObject {
    final Map<String,Object> values=new HashMap<>();
    Object opt(String key){return values.get(key);}
}
class ClientSessionBudget {boolean canSave(long now){return false;}}
class SystemClock {static long uptimeMillis(){return 1;}}
class Capture {int count(){return 0;}}
class ClientAcceptance {static boolean taskSaveReady(Object a,Object b,int c,int d,String session,long pid){return false;}}
class ClientRuntime {
    public enum ProfileState { ABSENT, READY, PRESERVE }
    final Context context;
    boolean reopen,inputReady=true,finished,finishRequested,cancelled,producerCompleted,connectedCapturedReady,stuckRequested,relocationCapturedReady,saveLogoutRequested,performanceCommandPending;
    JSONObject manifest,characterConnectedEvent=new JSONObject(),characterSavedEvent,taskAcceptedEvent,taskCompletedEvent,taskContactReceipt,taskCompletionReceipt;
    Capture taskAcceptedCapture=new Capture(),taskCompletedCapture=new Capture();
    ClientSessionBudget sessionBudget=new ClientSessionBudget();String session="session";long observedClientPid=1;
    ClientRuntime(Context context){this.context=context;}
    static Object jsonValue(Object value){return value;}
    RUNTIME_METHODS
}
public class FreshProfileRecoveryHost {
    static void need(boolean yes){if(!yes)throw new AssertionError();}
    interface Action {void run()throws Exception;}
    static void reject(Action action)throws Exception {try{action.run();throw new AssertionError("unexpected profile replacement");}catch(IOException expected){}}
    static Map<String,Object> map(Object... values){Map<String,Object> result=new LinkedHashMap<>();for(int i=0;i<values.length;i+=2)result.put((String)values[i],values[i+1]);return result;}
    static void write(Path path,String value)throws Exception{Files.createDirectories(path.getParent());Files.write(path,value.getBytes(StandardCharsets.UTF_8));}
    static void valid(Path profile)throws Exception {
        write(profile.resolve("profile.json"),"marker");write(profile.resolve("credentials.json"),"credentials");write(profile.resolve("pgdata/PG_VERSION"),"17\n");
        StorageFiles.marker=map("format",1,"purpose","persistent_local_login","profile","android-local-login","database","coh_local_android",
            "source_commit","0b75ade0c801735e10c5798f641948a45cc50488","data_commit","d51533ec8e6a9cf726b9214968077a05fdcf19f3",
            "package_manifest_sha256","95f62cc81b0743c13652e55aee01aed6871fc96d70a84b8dfd62fb8a0d9fe0d6",
            "schema_manifest_sha256","b89136892e69ceb39db640613d3f8a34abf2ef8e75e947f4034728b935938b92","initialized",true);
        StorageFiles.credentials=map("cohdiag_admin","a".repeat(64),"cohtest","b".repeat(64));
    }
    public static void main(String[] args)throws Exception {
        Path root=Files.createTempDirectory("coh-profile-recovery-"),profile=root.resolve("client/state/diagnostic/android-local-login");
        Context context=new Context(root.toFile());ClientRuntime runtime=new ClientRuntime(context);
        if(!args[0].equals("absent")&&!args[0].equals("missing_ancestor")&&!args[0].equals("changed_before_creation"))valid(profile);
        switch(args[0]) {
        case "absent":need(ClientRuntime.characterProfileState(context)==ClientRuntime.ProfileState.ABSENT);runtime.requireCharacterProfile(false);reject(()->runtime.requireCharacterProfile(true));need(ClientRuntime.profileRecoveryMessage(ClientRuntime.ProfileState.ABSENT).contains("external database backup"));break;
        case "missing_ancestor":Files.createDirectories(root.resolve("client"));need(ClientRuntime.characterProfileState(context)==ClientRuntime.ProfileState.ABSENT);runtime.requireCharacterProfile(false);break;
        case "ready":need(ClientRuntime.characterProfileState(context)==ClientRuntime.ProfileState.READY);runtime.requireCharacterProfile(true);reject(()->runtime.requireCharacterProfile(false));break;
        case "uninitialized":StorageFiles.marker.put("initialized",false);break;
        case "wrong_identity":StorageFiles.marker.put("source_commit","f".repeat(40));break;
        case "extra_marker_key":StorageFiles.marker.put("unrecognized",true);break;
        case "string_initialized":StorageFiles.marker.put("initialized","true");break;
        case "linked_profile":Files.move(profile,root.resolve("external-profile"));Files.createSymbolicLink(profile,root.resolve("external-profile"));break;
        case "dangling_profile":Files.move(profile,root.resolve("external-profile"));Files.createSymbolicLink(profile,root.resolve("missing-target"));break;
        case "linked_ancestor":Files.move(root.resolve("client/state"),root.resolve("external-state"));Files.createSymbolicLink(root.resolve("client/state"),root.resolve("external-state"));break;
        case "linked_marker":Files.move(profile.resolve("profile.json"),root.resolve("external-marker"));Files.createSymbolicLink(profile.resolve("profile.json"),root.resolve("external-marker"));break;
        case "hardlinked_marker":Files.createLink(root.resolve("additional-marker"),profile.resolve("profile.json"));break;
        case "linked_credentials":Files.move(profile.resolve("credentials.json"),root.resolve("external-credentials"));Files.createSymbolicLink(profile.resolve("credentials.json"),root.resolve("external-credentials"));break;
        case "linked_cluster":Files.move(profile.resolve("pgdata"),root.resolve("external-cluster"));Files.createSymbolicLink(profile.resolve("pgdata"),root.resolve("external-cluster"));break;
        case "missing_cluster":Files.delete(profile.resolve("pgdata/PG_VERSION"));break;
        case "extra_credentials":StorageFiles.credentials.put("extra","c".repeat(64));break;
        case "invalid_credentials":StorageFiles.credentials.put("cohtest","not-a-password");break;
        case "oversized_marker":write(profile.resolve("profile.json"),"x".repeat(4097));break;
        case "unreadable":StorageFiles.readFailure=true;break;
        case "changed_before_creation":need(ClientRuntime.characterProfileState(context)==ClientRuntime.ProfileState.ABSENT);Files.createDirectories(profile);reject(()->runtime.requireCharacterProfile(false));break;
        case "creator_save":
        case "creator_save_pending":
            runtime.manifest=new JSONObject();runtime.manifest.values.put("task_gate_required",true);runtime.reopen=false;
            need(!runtime.taskGateRequired());need(runtime.taskSaveReady());need(runtime.canRequestSaveLogout());
            if(args[0].equals("creator_save_pending")) {
                runtime.performanceCommandPending=true;need(!runtime.canRequestSaveLogout());
                runtime.performanceCommandPending=false;need(runtime.canRequestSaveLogout());
            }
            runtime.reopen=true;need(runtime.taskGateRequired());need(!runtime.taskSaveReady());need(!runtime.canRequestSaveLogout());break;
        default:throw new AssertionError("unknown fixture");
        }
        if(!new HashSet<>(Arrays.asList("absent","missing_ancestor","ready","creator_save","creator_save_pending")).contains(args[0])) {
            need(ClientRuntime.characterProfileState(context)==ClientRuntime.ProfileState.PRESERVE);
            reject(()->runtime.requireCharacterProfile(false));reject(()->runtime.requireCharacterProfile(true));
        }
        // Readiness performs no creation, truncation, directory walk or deletion.
        if(args[0].equals("ready")){need(Files.readString(profile.resolve("profile.json")).equals("marker"));need(Files.readString(profile.resolve("pgdata/PG_VERSION")).equals("17\n"));}
    }
}
'''


class FreshProfileRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temporary.name)
        runtime = (JAVA / 'ClientRuntime.java').read_text()
        signatures = [
            'public static ProfileState characterProfileState(',
            'static ProfileState inspectCharacterProfile(',
            'private static boolean profileEntry(',
            'public static String profileRecoveryMessage(',
            'private void requireCharacterProfile(',
            'private boolean taskGateRequired(',
            'private boolean taskSaveReady(',
            'public synchronized boolean canRequestSaveLogout(',
        ]
        # Package visibility is widened only in the host harness for direct calls.
        methods = '\n'.join(production_method(runtime, signature) for signature in signatures).replace('private ', '')
        fixture = cls.path / 'FreshProfileRecoveryHost.java'
        fixture.write_text(HOST.replace('RUNTIME_METHODS', methods))
        compiler = ['javac'] if shutil.which('javac') else ['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main']
        subprocess.run(compiler + ['-d', str(cls.path), str(JAVA / 'StorageAudit.java'), str(fixture)], check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def run_policy(self, fixture):
        subprocess.run(['java', '-cp', str(self.path), 'io.github.russianranger.cohclientinteractive.FreshProfileRecoveryHost', fixture], check=True, capture_output=True, text=True)

    def test_fresh_profile_is_explicit_and_never_a_reopen_fallback(self): self.run_policy('absent')
    def test_missing_parent_does_not_create_any_profile_directories(self): self.run_policy('missing_ancestor')
    def test_complete_profile_reopens_without_replacement_or_data_mutation(self): self.run_policy('ready')
    def test_uninitialized_profile_is_preserved(self): self.run_policy('uninitialized')
    def test_wrong_native_identity_is_preserved(self): self.run_policy('wrong_identity')
    def test_unknown_marker_fields_are_preserved(self): self.run_policy('extra_marker_key')
    def test_string_initialized_flag_is_not_accepted(self): self.run_policy('string_initialized')
    def test_linked_profile_is_preserved(self): self.run_policy('linked_profile')
    def test_dangling_profile_is_not_treated_as_absent(self): self.run_policy('dangling_profile')
    def test_linked_ancestor_is_preserved(self): self.run_policy('linked_ancestor')
    def test_linked_marker_is_preserved(self): self.run_policy('linked_marker')
    def test_hardlinked_marker_is_preserved(self): self.run_policy('hardlinked_marker')
    def test_linked_credentials_are_preserved(self): self.run_policy('linked_credentials')
    def test_linked_postgresql_cluster_is_preserved(self): self.run_policy('linked_cluster')
    def test_missing_cluster_is_preserved(self): self.run_policy('missing_cluster')
    def test_unexpected_credentials_are_preserved(self): self.run_policy('extra_credentials')
    def test_invalid_credentials_are_preserved(self): self.run_policy('invalid_credentials')
    def test_profile_reads_remain_bounded(self): self.run_policy('oversized_marker')
    def test_unreadable_metadata_disables_creation(self): self.run_policy('unreadable')
    def test_profile_appearing_after_review_is_never_overwritten(self): self.run_policy('changed_before_creation')
    def test_creator_can_save_without_weakening_the_reopened_task_gate(self): self.run_policy('creator_save')
    def test_pending_sidebar_transaction_defers_creator_save_until_completed(self): self.run_policy('creator_save_pending')

    def test_profile_preflight_precedes_staging_and_process_launch_under_the_lock(self):
        source = (JAVA / 'ClientRuntime.java').read_text()
        run = production_method(source, 'private Result runCharacter(')
        preflight = run.index('requireCharacterProfile(reopen);')
        self.assertLess(run.index('begin('), preflight)
        for operation in ('loadManifest();', 'validateInstalled();', 'importer().inspect()', 'state.mkdirs()', 'builder.start()'):
            self.assertLess(preflight, run.index(operation))
        entry = production_method(source, 'public Result runFreshCreation(')
        self.assertIn('runCharacter(selectedSession, false)', entry)
        self.assertNotIn('runFreshCreation', production_method(source, 'public Result run('))


if __name__ == '__main__':
    unittest.main()
