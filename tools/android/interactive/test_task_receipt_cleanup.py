"""Real JVM session-output cleanup plus explicit startup/task guest routing."""
import copy
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from test_storage_ui import production_method

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
sys.path.insert(0, str(ROOT / 'android/guest'))
import character_reopen_diagnostic as guest
import local_character_server as server
from test_character_server import fixture, SESSION

HOST = r'''
package io.github.russianranger.cohclientinteractive;
import java.io.*;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.util.*;
class JSONObject {Map<String,Object> values=new HashMap<>();Object opt(String key){return values.get(key);}}
class ClientRuntime {
  boolean reopen=true;JSONObject manifest=new JSONObject();
  RUNTIME_METHODS
}
public class TaskReceiptCleanupHost {
  static void need(boolean yes){if(!yes)throw new AssertionError();}
  interface Action{void run()throws Exception;}
  static void reject(Action action)throws Exception{try{action.run();throw new AssertionError("unsafe cleanup accepted");}catch(IOException expected){}}
  static class Fs implements StorageAudit.Fs {
    final Path root;String failDelete,changedBeforeDelete;
    Fs(Path root){this.root=root;}
    public StorageAudit.Stat stat(String name)throws IOException{
      Path path=root.resolve(name);BasicFileAttributes attrs;
      try{attrs=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);}catch(NoSuchFileException missing){return null;}
      StorageAudit.Kind kind=attrs.isSymbolicLink()?StorageAudit.Kind.SYMLINK:attrs.isDirectory()?StorageAudit.Kind.DIRECTORY:attrs.isRegularFile()?StorageAudit.Kind.FILE:StorageAudit.Kind.OTHER;
      long dev=((Number)Files.getAttribute(path,"unix:dev",LinkOption.NOFOLLOW_LINKS)).longValue();
      long ino=((Number)Files.getAttribute(path,"unix:ino",LinkOption.NOFOLLOW_LINKS)).longValue();
      long links=((Number)Files.getAttribute(path,"unix:nlink",LinkOption.NOFOLLOW_LINKS)).longValue();
      long changed=((FileTime)Files.getAttribute(path,"unix:ctime",LinkOption.NOFOLLOW_LINKS)).toMillis();
      return new StorageAudit.Stat(kind,dev,ino,links,attrs.size(),1,attrs.lastModifiedTime().toMillis(),changed);
    }
    public void remove(String path,StorageAudit.Stat expected,StorageAudit.Stat parent)throws IOException{
      if(path.equals(changedBeforeDelete)){changedBeforeDelete=null;Files.write(root.resolve(path),new byte[900]);}
      StorageAudit.Fs.super.remove(path,expected,parent);
    }
    public void unlink(String path)throws IOException{if(path.equals(failDelete))throw new IOException("unlink failed");Files.delete(root.resolve(path));}
    public void rmdir(String path){throw new AssertionError("no directories may be removed");}
    public String rootPath(){return root.toString();}
    public String readLink(String path){throw new AssertionError("cleanup must not follow links");}
    public List<String> list(String path){throw new AssertionError("cleanup must not enumerate state/imports");}
    public byte[] read(String path,int limit){throw new AssertionError("cleanup must not read database or task rows");}
    public Map<String,Object> json(byte[] bytes){throw new AssertionError();}
    public Map<String,Object> reportIdentity(String path,int limit){throw new AssertionError();}
    public long nowMillis(){return 1;}
  }
  static void write(Path path,String text)throws Exception{Files.createDirectories(path.getParent());Files.writeString(path,text);}
  static boolean absent(Path path){return !Files.exists(path,LinkOption.NOFOLLOW_LINKS);}
  public static void main(String[] args)throws Exception{
    Path root=Files.createTempDirectory("coh-task-receipt-"),state=root.resolve("client/state");Files.createDirectories(state);
    String[] names={"stop-request","interaction-finish.json","character-logout.json","character-relocation.json","latest-report.json","report.zip","character-task-contact.json","character-task-completion.json"};
    String[] kept={"client/state/diagnostic/android-local-login/profile.json","client/state/diagnostic/android-local-login/pgdata/tasks.bin","client/state/diagnostic/wine/user.reg","client/state/diagnostic/character-server-data-kept/bin/cache.bin","client-import/generation-kept/data/input.bin","m2/runtime-kept/ready.json","client/reports/kept/coh-character.zip","client/state/unknown-receipt.json"};
    for(String name:kept)write(root.resolve(name),"preserved:"+name);
    Fs fs=new Fs(root);ClientRuntime runtime=new ClientRuntime();runtime.manifest.values.put("task_gate_required",true);
    Path contact=state.resolve("character-task-contact.json"),completion=state.resolve("character-task-completion.json");
    switch(args[0]){
    case "two_sessions":
      for(int session=0;session<2;session++){for(String name:names)write(state.resolve(name),"prior-session-"+session);ClientRuntime.retirePreviousGuestOutput(fs);for(String name:names)need(absent(state.resolve(name)));}break;
    case "absent":ClientRuntime.retirePreviousGuestOutput(fs);ClientRuntime.retirePreviousGuestOutput(fs);break;
    case "dangling":Files.createSymbolicLink(contact,root.resolve("missing"));ClientRuntime.retirePreviousGuestOutput(fs);need(absent(contact));break;
    case "linked_database":Files.createSymbolicLink(contact,root.resolve(kept[1]));ClientRuntime.retirePreviousGuestOutput(fs);need(absent(contact));break;
    case "hardlinked_database":Files.createLink(contact,root.resolve(kept[1]));ClientRuntime.retirePreviousGuestOutput(fs);need(absent(contact));break;
    case "directory":write(state.resolve("stop-request"),"prior");Files.createDirectories(completion);reject(()->ClientRuntime.retirePreviousGuestOutput(fs));need(Files.exists(state.resolve("stop-request"))&&Files.isDirectory(completion));break;
    case "fifo":need(new ProcessBuilder("mkfifo",completion.toString()).start().waitFor()==0);reject(()->ClientRuntime.retirePreviousGuestOutput(fs));need(Files.exists(completion));break;
    case "changed":write(contact,"prior");fs.changedBeforeDelete="client/state/character-task-contact.json";reject(()->ClientRuntime.retirePreviousGuestOutput(fs));need(Files.size(contact)==900);break;
    case "delete_failure":write(contact,"prior");write(completion,"prior");fs.failDelete="client/state/character-task-contact.json";reject(()->ClientRuntime.retirePreviousGuestOutput(fs));need(Files.exists(contact)&&Files.exists(completion));break;
    case "task_required":need(runtime.taskGateRequired());break;
    case "startup":runtime.manifest.values.put("startup_only_reopen",true);need(!runtime.taskGateRequired());break;
    case "startup_false":runtime.manifest.values.put("startup_only_reopen",false);need(runtime.taskGateRequired());break;
    case "startup_string":runtime.manifest.values.put("startup_only_reopen","true");need(runtime.taskGateRequired());break;
    case "startup_number":runtime.manifest.values.put("startup_only_reopen",1);need(runtime.taskGateRequired());break;
    case "creation":runtime.reopen=false;runtime.manifest.values.put("startup_only_reopen",true);need(!runtime.taskGateRequired());break;
    default:throw new AssertionError("unknown fixture");
    }
    for(String name:kept)need(Files.readString(root.resolve(name)).equals("preserved:"+name));
  }
}
'''


class TaskReceiptHostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temporary.name)
        source = (JAVA / 'ClientRuntime.java').read_text()
        methods = '\n'.join(production_method(source, signature) for signature in (
            'static void retirePreviousGuestOutput(', 'private boolean taskGateRequired(')).replace('private ', '')
        java = cls.path / 'TaskReceiptCleanupHost.java'
        java.write_text(HOST.replace('RUNTIME_METHODS', methods))
        compiler = ['javac'] if shutil.which('javac') else ['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main']
        subprocess.run(compiler + ['-d', str(cls.path), str(JAVA / 'StorageAudit.java'), str(java)], check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls): cls.temporary.cleanup()

    def run_policy(self, value):
        subprocess.run(['java', '-cp', str(self.path), 'io.github.russianranger.cohclientinteractive.TaskReceiptCleanupHost', value], check=True, capture_output=True, text=True)

    def test_two_consecutive_sessions_remove_both_stale_helpers_without_touching_saved_data(self): self.run_policy('two_sessions')
    def test_no_previous_outputs_is_idempotent(self): self.run_policy('absent')
    def test_dangling_receipt_link_is_retired_without_following_it(self): self.run_policy('dangling')
    def test_receipt_link_does_not_delete_its_database_target(self): self.run_policy('linked_database')
    def test_receipt_hardlink_does_not_modify_database_bytes(self): self.run_policy('hardlinked_database')
    def test_unexpected_directory_stops_before_any_deletion(self): self.run_policy('directory')
    def test_nonregular_receipt_is_preserved_and_refused(self): self.run_policy('fifo')
    def test_changed_receipt_is_refused(self): self.run_policy('changed')
    def test_delete_failure_stops_remaining_deletion(self): self.run_policy('delete_failure')
    def test_historical_task_mode_remains_required(self): self.run_policy('task_required')
    def test_explicit_boolean_startup_mode_skips_only_task_gating(self): self.run_policy('startup')
    def test_false_startup_mode_does_not_skip_task_gate(self): self.run_policy('startup_false')
    def test_string_startup_mode_does_not_skip_task_gate(self): self.run_policy('startup_string')
    def test_numeric_startup_mode_does_not_skip_task_gate(self): self.run_policy('startup_number')
    def test_first_creation_does_not_adopt_reopen_task_mode(self): self.run_policy('creation')

    def test_cleanup_precedes_guest_launch_and_explicit_flag_is_reopen_only(self):
        source = (JAVA / 'ClientRuntime.java').read_text()
        run = production_method(source, 'private Result runCharacter(')
        self.assertLess(run.index('removePreviousGuestOutput();'), run.index('builder.start()'))
        self.assertIn('if (reopen && Boolean.TRUE.equals(manifest.opt("startup_only_reopen"))) command.add("--startup-only");', run)
        self.assertIn('retirePreviousGuestOutput(new StorageFiles(home.getParentFile()))', production_method(source, 'private void removePreviousGuestOutput('))
        # The production adapter anchors the verified directory and never follows the leaf link.
        adapter = (JAVA / 'StorageFiles.java').read_text()
        anchored = production_method(adapter, 'public void remove(')
        self.assertIn('OsConstants.O_NOFOLLOW', anchored)
        self.assertIn('expected.same(actual)', anchored)
        self.assertIn('"/proc/self/fd/"', anchored)


class StartupOnlyGuestTests(unittest.TestCase):
    def test_existing_parser_arguments_are_forwarded_without_changes(self):
        args = ['--state', '/state', '--profile', 'android-local-login', '--session-id', SESSION,
                '--startup-timeout-seconds', '900']
        self.assertEqual(guest.parse_reopen_arguments(args), (False, args))
        self.assertEqual(guest.parse_reopen_arguments(args + ['--startup-only']), (True, args))

    def test_startup_switch_is_exact_and_rejects_a_value(self):
        self.assertEqual(guest.parse_reopen_arguments(['--startup']), (False, ['--startup']))
        with patch('sys.stderr'), self.assertRaises(SystemExit): guest.parse_reopen_arguments(['--startup-only=true'])

    def test_default_main_preserves_original_scope_and_task_diagnostic_class(self):
        with patch.object(guest.creation, 'run', return_value=7) as execute:
            self.assertEqual(guest.main(['--profile', 'android-local-login']), 7)
            execute.assert_called_once_with(['--profile', 'android-local-login'], guest.CharacterReopenDiagnostic,
                                           guest.SCOPE, 'actual_character_reopen')

    def test_explicit_main_records_startup_scope_and_dedicated_class(self):
        with patch.object(guest.creation, 'run', return_value=9) as execute:
            self.assertEqual(guest.main(['--startup-only', '--profile', 'android-local-login']), 9)
            execute.assert_called_once_with(['--profile', 'android-local-login'], guest.StartupOnlyCharacterReopenDiagnostic,
                                           guest.STARTUP_SCOPE, 'actual_character_startup_timing')

    def test_packaged_task_config_retains_old_selection_but_explicit_startup_uses_ordinary_server(self):
        with tempfile.TemporaryDirectory() as temporary:
            assets = Path(temporary)
            historical = guest.CharacterReopenDiagnostic.__new__(guest.CharacterReopenDiagnostic)
            startup = guest.StartupOnlyCharacterReopenDiagnostic.__new__(guest.StartupOnlyCharacterReopenDiagnostic)
            historical.args = startup.args = SimpleNamespace(assets=assets)
            with patch.object(guest.character, 'LocalCharacterReopenServer', return_value='ordinary') as ordinary, \
                    patch.object(guest.character, 'LocalCharacterTaskReopenServer', return_value='task') as task:
                self.assertEqual(historical.make_server(), 'ordinary')
                (assets / 'task-gate.json').write_text('{"required":true}')
                self.assertEqual(historical.make_server(), 'task')
                self.assertEqual(startup.make_server(), 'ordinary')
                self.assertEqual(task.call_count, 1)
                self.assertEqual(ordinary.call_count, 2)

    def test_startup_server_accepts_existing_tasks_read_only_and_keeps_strict_saved_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            owner = SimpleNamespace(ctx=SimpleNamespace(report={}, event=Mock()), root=root,
                                    args=SimpleNamespace(state=root, session_id=SESSION))
            diagnostic = guest.StartupOnlyCharacterReopenDiagnostic.__new__(guest.StartupOnlyCharacterReopenDiagnostic)
            diagnostic.args = SimpleNamespace(assets=root)
            ordinary_server = server.LocalCharacterReopenServer
            with patch.object(guest.character, 'LocalCharacterReopenServer', side_effect=lambda _diag: ordinary_server(owner)):
                value = diagnostic.make_server()
            rows, _, attributes = fixture()
            for table in rows.values():
                for row in table: row['containerid'] = 1
            rows['tasks'] = [{'containerid': 1, 'subid': 0, 'id': 12769, 'state': 1}]
            before = copy.deepcopy(rows)
            inventory = [{key: rows['ents'][0][key] for key in server.evidence.IDENTITY_FIELDS}]
            value.inventory = Mock(return_value=inventory)
            value.sql = Mock(return_value='77|COHLOCAL')
            value.schema = {'expected_attributes': attributes}
            position = {'containerid': 1, 'mapid': None, 'staticmapid': 1, 'posx': 100, 'posy': 0, 'posz': -100}
            value.sql_rows = Mock(side_effect=lambda table, fields, *_: [position] if 'staticmapid' in fields else copy.deepcopy(rows[table]))
            value.capture_baseline()
            self.assertEqual(rows, before)
            self.assertTrue(value.creation_report['existing_character_verified'])
            self.assertFalse(value.creation_report['sql_game_mutations_performed'])
            self.assertTrue(value.sql.call_args.args[0].startswith('SELECT'))
            self.assertNotIn('tasks', [call.args[0] for call in value.sql_rows.call_args_list])
            self.assertIs(type(value), server.LocalCharacterReopenServer)

    def test_historical_task_initialization_still_rejects_stale_helper_receipts(self):
        for receipt in ('character-task-contact.json', 'character-task-completion.json'):
            with self.subTest(receipt=receipt), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                diagnostic = guest.CharacterReopenDiagnostic.__new__(guest.CharacterReopenDiagnostic)
                diagnostic.args = SimpleNamespace(state=root, assets=root)
                diagnostic.ctx = SimpleNamespace(report={'character_reopen': {'task_gate_required': True},
                    'asset_sha256': {name: 'retained' for name in guest.REQUIRED | {
                        'task-gate.json', 'task_gate_evidence.py', 'server_animation_package.py',
                        'server-animations.pigg', 'server-animation-manifest.json'}}})
                (root / receipt).write_text('{"session_id":"old"}')
                config = {'format': 1, 'scope': 'manual_authored_task_command_completion_and_ordinary_save',
                    'required': True, 'contact_path': 'Contacts/Atlas_Park/Matthew_Habashy.contact',
                    'task_name': 'Mission1', 'task_index': 0, 'completion_command': '/completetask 0',
                    'reward_turn_in_required': False}
                with patch.object(guest.creation.CharacterCreationDiagnostic, 'initialize'), \
                        patch.object(guest.creation.login.server.dbserver, 'load_json', return_value=config):
                    with self.assertRaisesRegex(server.base.DiagnosticError, 'Stale task helper delivery receipt'):
                        diagnostic.initialize()
                self.assertTrue((root / receipt).is_file())

    def test_startup_mode_reports_exact_scope_without_claiming_task_proof(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            diagnostic = guest.StartupOnlyCharacterReopenDiagnostic.__new__(guest.StartupOnlyCharacterReopenDiagnostic)
            diagnostic.args = SimpleNamespace(state=root)
            diagnostic.ctx = SimpleNamespace(report={'character_reopen': {}})
            with patch.object(guest.creation.CharacterCreationDiagnostic, 'initialize'):
                diagnostic.initialize()
            report = diagnostic.ctx.report
            self.assertIs(report['startup_only_reopen'], True)
            self.assertIs(report['task_gate_required'], False)
            self.assertIs(report['task_qualification_requested'], False)
            self.assertEqual(report['startup_validation_scope'], 'saved_character_startup_connection_timing_only')
            self.assertNotIn('task_gate', report)

    def test_startup_mode_preserves_ordinary_saved_identity_and_save_proof(self):
        self.assertIs(guest.StartupOnlyCharacterReopenDiagnostic.identity_verified, guest.CharacterReopenDiagnostic.identity_verified)
        self.assertIs(guest.StartupOnlyCharacterReopenDiagnostic.proof_verified, guest.CharacterReopenDiagnostic.proof_verified)
        self.assertIs(guest.StartupOnlyCharacterReopenDiagnostic.finish_observation, guest.CharacterReopenDiagnostic.finish_observation)


if __name__ == '__main__': unittest.main()
