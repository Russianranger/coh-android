#!/usr/bin/env python3
"""Verify exact completed-carrier preservation and separate live save observations.

Save report fields are projections of the two .31 attached guest reports. Matching
live event controls are synthetic: these tests never infer missing Android captures
or certify the recovered attachments as completed Android sessions.
"""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
REPORTS_JAVA = ROOT/'android/recovery/src/main/java/io/github/russianranger/cohclientinteractive/ClientReports.java'
JAVA = ROOT/'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
FIXTURES = json.loads(r'''[
  {
    "session_id": "579c73a8c0ec4058b3e842966452eda9",
    "execution_platform_requested": "android",
    "scope": "actual_character_creation_guest",
    "diagnostic_mode": "actual_character_creation",
    "postgres_started": true,
    "server_started": true,
    "mapserver_started": true,
    "status": "passed",
    "passed": true,
    "character_creation": {
      "session_id": "579c73a8c0ec4058b3e842966452eda9",
      "client_pid": 632,
      "character_id": 1,
      "auth_id": 1353310574,
      "name": "THORHERO",
      "account": "COHLOCAL",
      "map_id": 1,
      "verified": true,
      "connected_on_atlas": true,
      "committed_sql_verified": true,
      "requested_logout_observed": true,
      "logout_timer_observed": true,
      "disconnected_before_sql": true,
      "forced_stop_before_save": false,
      "row_counts": {
        "ents": 1,
        "ents2": 1,
        "powers": 7,
        "costumeparts": 13
      },
      "table_sha256": {
        "ents": "0e9f8b243367bc5837b532b42c825381a6a6ce8f338eb779dcae9925b48835d0",
        "ents2": "77ec33b6b6baddab8274b33a4526e99ebc08988a603d4bb5b0989e3e53df2713",
        "powers": "0815aea7b4637eee5b47f0138776492f9b1ab81ba9c904002c9d5525030a6e22",
        "costumeparts": "4bab38b6af68848b01e76acc3e63b20305a8465b165f9289fd6ae829933edbbc"
      },
      "snapshot_sha256": "39ef4d611722be6ce39766c727cc663003fb8f39ab2cfa20f37c865cbbf327bf",
      "reopen_verified": false
    },
    "local_login": {
      "session_id": "579c73a8c0ec4058b3e842966452eda9",
      "client_pid": 632,
      "auth_id": 1353310574,
      "profile": "android-local-login",
      "database_preserved": true,
      "local_login_verified": true,
      "local_account_verified": true,
      "character_list_sent": true,
      "character_list_response_sent": true
    }
  },
  {
    "session_id": "c81989391a4d4a6d9a424d980440d6c3",
    "execution_platform_requested": "android",
    "scope": "actual_character_reopen_guest",
    "diagnostic_mode": "actual_character_reopen",
    "postgres_started": true,
    "server_started": true,
    "mapserver_started": true,
    "status": "failed",
    "passed": false,
    "character_reopen": {
      "session_id": "c81989391a4d4a6d9a424d980440d6c3",
      "client_pid": 636,
      "character_id": 1,
      "auth_id": 1353310574,
      "name": "THORHERO",
      "account": "COHLOCAL",
      "map_id": 1,
      "verified": true,
      "connected_on_atlas": true,
      "committed_sql_verified": true,
      "requested_logout_observed": true,
      "logout_timer_observed": true,
      "disconnected_before_sql": true,
      "forced_stop_before_save": false,
      "row_counts": {
        "ents": 1,
        "ents2": 1,
        "powers": 7,
        "costumeparts": 13
      },
      "table_sha256": {
        "ents": "8d6abdce202d6e7956bfced1fcb138b9ea5e31a10fabe295e86d1cea5f456e7b",
        "ents2": "77ec33b6b6baddab8274b33a4526e99ebc08988a603d4bb5b0989e3e53df2713",
        "powers": "0815aea7b4637eee5b47f0138776492f9b1ab81ba9c904002c9d5525030a6e22",
        "costumeparts": "4bab38b6af68848b01e76acc3e63b20305a8465b165f9289fd6ae829933edbbc"
      },
      "snapshot_sha256": "94ba9b98ef436f2a286a87937c242538080e16c6a58d9c0df789837b06b9b94f",
      "reopen_verified": true,
      "existing_character_verified": true,
      "preserved_existing_identity": true,
      "native_client_ready_observed": true,
      "powers_preserved": true,
      "costume_preserved": true,
      "selected_rows_preserved": true,
      "committed_native_position_verified": true,
      "before_character_id": 1,
      "baseline_character_id": 1,
      "recovery_requested": false,
      "recovery_verified": false,
      "ordinary_stuck_observed": false,
      "on_atlas_safe_position": false,
      "stable_ground_verified": false,
      "committed_safe_position_verified": false,
      "zoning_enabled": true,
      "connected_on_supported_map": true,
      "monorail_enabled": true,
      "before_login_count": 1,
      "login_count": 2
    },
    "local_login": {
      "session_id": "c81989391a4d4a6d9a424d980440d6c3",
      "client_pid": 636,
      "auth_id": 1353310574,
      "profile": "android-local-login",
      "database_preserved": false,
      "local_login_verified": true,
      "local_account_verified": true,
      "character_list_sent": true,
      "character_list_response_sent": true
    }
  }
]''')


def java_value(value):
    if isinstance(value, dict):
        return 'map('+','.join(java_value(item) for pair in value.items() for item in pair)+')'
    if isinstance(value, list):
        return 'new ArrayList<Object>(Arrays.asList('+','.join(map(java_value,value))+'))'
    if isinstance(value,str): return json.dumps(value,ensure_ascii=True)
    if isinstance(value,bool): return 'Boolean.TRUE' if value else 'Boolean.FALSE'
    if value is None: return 'null'
    if isinstance(value,int): return str(value)+'L'
    raise AssertionError(value)


def method(source,signature):
    start=source.index(signature);cursor=source.index('{',start);depth=1;end=cursor+1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    return source[start:end]


REPORT_HARNESS = r'''
package io.github.russianranger.cohclientinteractive;
import java.io.*;import java.nio.file.*;import java.nio.file.attribute.*;import java.nio.charset.StandardCharsets;import java.util.*;import java.util.zip.*;
public class CompletedGuestHost {
 static final String SESSION="579c73a8c0ec4058b3e842966452eda9",OTHER="c81989391a4d4a6d9a424d980440d6c3",RUN="1791765403732-0123456789ab";
 static Path root,state,run,normal;static String wrapperSession=SESSION,wrapperApp="io.github.russianranger.cohclientinteractive",wrapperOperation="character_creation",wrapperRun=RUN,wrapperVersion="0.13.32";
 static boolean omitFinish,extra,unsafe,missingIdentity,invalidUtf8;static int wrapperPadding;
 interface Checked {void run()throws Exception;}
 static void need(boolean ok){if(!ok)throw new AssertionError();}
 static void fail(Checked action)throws Exception {try{action.run();throw new AssertionError("expected refusal");}catch(IOException expected){}}
 static byte[] bytes(String value){return value.getBytes(StandardCharsets.UTF_8);}
 static void setup()throws Exception {
  root=Files.createTempDirectory("coh-completed-guest-");state=Files.createDirectories(root.resolve("client/state"));run=Files.createDirectories(root.resolve("client/reports/"+RUN));normal=run.resolve("coh-character-creation-"+RUN+".zip");
  Files.write(state.resolve("latest-report.json"),bytes("{\"session_id\":\""+SESSION+"\",\"passed\":false,\"nested\":{\"session_id\":\""+OTHER+"\"}}"));
  Files.write(state.resolve("report.zip"),new byte[]{1,2,3,4});Files.write(state.resolve("interaction-finish.json"),bytes("{\"action\":\"finish_interaction\"}"));
 }
 static void make(Path target)throws Exception {
  try(ZipOutputStream zip=new ZipOutputStream(Files.newOutputStream(target))){
   zip.putNextEntry(new ZipEntry("android-client-report.json"));
   String identity=missingIdentity?"":"\"format\":1,\"app_id\":\""+wrapperApp+"\",\"operation\":\""+wrapperOperation+"\",\"run_id\":\""+wrapperRun+"\",\"app_version\":\""+wrapperVersion+"\",";
   zip.write(bytes("{"+identity+"\"session_id\":\""+wrapperSession+"\",\"passed\":false"));
   if(wrapperPadding>0){zip.write(bytes(",\"padding\":\""));byte[] data=new byte[65536];Arrays.fill(data,(byte)'a');for(int count=wrapperPadding;count>0;count-=Math.min(count,data.length))zip.write(data,0,Math.min(count,data.length));zip.write(bytes("\""));}
   if(invalidUtf8){zip.write(bytes(",\"extra\":\""));zip.write(255);zip.write(bytes("\""));}zip.write(bytes("}"));zip.closeEntry();
   zip.putNextEntry(new ZipEntry("guest-report.zip"));zip.write(Files.readAllBytes(state.resolve("report.zip")));zip.closeEntry();
   if(omitFinish){zip.putNextEntry(new ZipEntry("guest-output/latest-report.json"));zip.write(Files.readAllBytes(state.resolve("latest-report.json")));zip.closeEntry();}
   else ClientReports.writeGuestOutputs(root.toFile(),zip);
   if(extra){zip.putNextEntry(new ZipEntry("android-client-reporx.json"));zip.write(bytes("{}"));zip.closeEntry();}
   if(unsafe){zip.putNextEntry(new ZipEntry("../outside"));zip.write(1);zip.closeEntry();}
  }
 }
 static Path marker(){return root.resolve("client/reports/completed-guest-preservation.txt");}
 static File recover()throws Exception {return ClientReports.preservePrevious(root.toFile());}
 static void fallback()throws Exception {File f=recover();need(!f.toPath().equals(normal));need(f.getName().startsWith("coh-interrupted-guest-"));need(Files.exists(state.resolve("report.zip")));}
 static void replaceBytes(Path file,byte[] from,byte[] to)throws Exception {
  need(from.length==to.length);byte[] data=Files.readAllBytes(file);int count=0;
  for(int i=0;i+from.length<=data.length;i++){boolean match=true;for(int n=0;n<from.length;n++)if(data[i+n]!=from[n]){match=false;break;}if(match){System.arraycopy(to,0,data,i,to.length);count++;i+=from.length-1;}}
  need(count>0);Files.write(file,data);
 }
 public static void main(String[] args)throws Exception {
  setup();String mode=args[0];
  if(mode.equals("foreign_wrapper"))wrapperSession=OTHER;
  if(mode.equals("foreign_app"))wrapperApp="foreign.app";
  if(mode.equals("foreign_operation"))wrapperOperation="character_reopen";
  if(mode.equals("foreign_run"))wrapperRun="1791765403732-aaaaaaaaaaaa";
  if(mode.equals("bad_version"))wrapperVersion="unknown";
  if(mode.equals("missing_identity"))missingIdentity=true;
  if(mode.equals("invalid_wrapper_utf8"))invalidUtf8=true;
  if(mode.equals("large_wrapper"))wrapperPadding=2500000;
  if(mode.equals("oversized_wrapper"))wrapperPadding=4500000;
  if(mode.equals("missing_request"))omitFinish=true;
  if(mode.equals("duplicate_entry"))extra=true;
  if(mode.equals("unsafe_entry"))unsafe=true;
  if(mode.equals("duplicate_session"))Files.write(state.resolve("latest-report.json"),bytes("{\"session_id\":\""+SESSION+"\",\"session_id\":\""+SESSION+"\"}"));
  if(mode.equals("nested_session"))Files.write(state.resolve("latest-report.json"),bytes("{\"nested\":{\"session_id\":\""+SESSION+"\"}}"));
  if(mode.equals("invalid_json"))Files.write(state.resolve("latest-report.json"),bytes("{\"session_id\":\""+SESSION+"\",\"x\":NaN}"));
  if(mode.equals("escaped_key"))Files.write(state.resolve("latest-report.json"),bytes("{\"session_\\u0069d\":\""+SESSION+"\"}"));
  if(mode.equals("atomic_commit") || mode.equals("commit_collision") || mode.equals("commit_linked_part") || mode.equals("commit_broken_part") || mode.equals("commit_foreign_part")) {
   Path partial=run.resolve(mode.equals("commit_foreign_part")?"foreign.zip.part":"support.zip.part");make(partial);
   if(mode.equals("atomic_commit")){ClientReports.commitNormalArchive(root.toFile(),partial.toFile(),normal.toFile());need(!Files.exists(partial));ClientReports.completedGuest(root.toFile(),normal.toFile(),SESSION);need(recover().toPath().equals(normal));}
   else {
    if(mode.equals("commit_collision")){make(normal);byte[] old=Files.readAllBytes(normal);fail(()->ClientReports.commitNormalArchive(root.toFile(),partial.toFile(),normal.toFile()));need(Arrays.equals(old,Files.readAllBytes(normal)));}
    else {if(mode.equals("commit_linked_part"))Files.createLink(run.resolve("other.part"),partial);if(mode.equals("commit_broken_part"))Files.write(partial,new byte[]{1,2,3});fail(()->ClientReports.commitNormalArchive(root.toFile(),partial.toFile(),normal.toFile()));need(!Files.exists(normal));}
    need(Files.exists(partial));need(!Files.exists(marker()));fallback();
   }
  }else if(mode.equals("before_atomic_commit")) {
   Path partial=run.resolve("support.zip.part");make(partial);fail(()->ClientReports.completedGuest(root.toFile(),partial.toFile(),SESSION));need(!Files.exists(marker()));fallback();need(Files.exists(partial));
  } else {
   make(normal);
   if(mode.equals("duplicate_entry"))replaceBytes(normal,bytes("android-client-reporx.json"),bytes("android-client-report.json"));
   if(mode.equals("truncated_before_mark")){byte[] data=Files.readAllBytes(normal);Files.write(normal,Arrays.copyOf(data,data.length-32));}
   if(mode.equals("foreign_wrapper")||mode.equals("foreign_app")||mode.equals("foreign_operation")||mode.equals("foreign_run")||mode.equals("bad_version")||mode.equals("missing_identity")||mode.equals("invalid_wrapper_utf8")||mode.equals("oversized_wrapper")||mode.equals("missing_request")||mode.equals("duplicate_entry")||mode.equals("unsafe_entry")||mode.equals("duplicate_session")||mode.equals("nested_session")||mode.equals("invalid_json")||mode.equals("truncated_before_mark")) {
    fail(()->ClientReports.completedGuest(root.toFile(),normal.toFile(),SESSION));need(!Files.exists(marker()));fallback();need(Files.exists(normal));
   }else if(mode.equals("foreign_caller")) {
    fail(()->ClientReports.completedGuest(root.toFile(),normal.toFile(),OTHER));need(!Files.exists(marker()));fallback();
   }else if(mode.equals("after_commit_before_receipt")) {
    need(!Files.exists(marker()));fallback();need(Files.exists(normal));
   }else {
    ClientReports.completedGuest(root.toFile(),normal.toFile(),SESSION);need(Files.exists(marker()));
    if(mode.equals("reuse") || mode.equals("escaped_key") || mode.equals("large_wrapper")) {
     for(int n=0;n<3;n++)need(recover().toPath().equals(normal));need(ClientReports.reports(root.toFile(),8).size()==1);
     try(ZipInputStream zip=new ZipInputStream(Files.newInputStream(normal))){boolean found=false;for(ZipEntry entry;(entry=zip.getNextEntry())!=null;)if(entry.getName().equals("android-client-report.json")){ByteArrayOutputStream b=new ByteArrayOutputStream();byte[] data=new byte[100];for(int count;(count=zip.read(data))!=-1;)b.write(data,0,count);need(new String(b.toByteArray(),StandardCharsets.UTF_8).contains("\"passed\":false"));found=true;}need(found);}
    }else if(mode.equals("deleted")){Files.delete(normal);fallback();}
    else if(mode.equals("corrupt") || mode.equals("same_size")){byte[] data=Files.readAllBytes(normal);FileTime time=Files.getLastModifiedTime(normal);data[0]^=1;Files.write(normal,data);if(mode.equals("same_size"))Files.setLastModifiedTime(normal,time);fallback();need(Files.exists(normal));}
    else if(mode.equals("truncated")){byte[] data=Files.readAllBytes(normal);Files.write(normal,Arrays.copyOf(data,data.length/2));fallback();}
    else if(mode.equals("guest_changed")){Path request=state.resolve("interaction-finish.json");FileTime time=Files.getLastModifiedTime(request);byte[] data=Files.readAllBytes(request);data[data.length-2]^=1;Files.write(request,data);Files.setLastModifiedTime(request,time);fallback();}
    else if(mode.equals("marker_changed")){Files.write(marker(),bytes("partial receipt"));fallback();}
    else if(mode.equals("foreign_marker")){replaceBytes(marker(),bytes(SESSION),bytes(OTHER));fallback();}
    else if(mode.equals("hardlinked_carrier")){Path linked=run.resolve("other.zip");Files.createLink(linked,normal);fail(()->recover());need(Files.exists(state.resolve("report.zip")));}
    else if(mode.equals("symlinked_carrier")){Path moved=run.resolve("other.zip");Files.move(normal,moved);Files.createSymbolicLink(normal,moved);fail(()->recover());need(Files.exists(state.resolve("report.zip")));}
    else if(mode.equals("hardlinked_guest")){Files.createLink(state.resolve("other.json"),state.resolve("latest-report.json"));fail(()->recover());}
    else if(mode.equals("marker_symlink")){Path moved=run.resolve("marker-copy");Files.move(marker(),moved);Files.createSymbolicLink(marker(),moved);fail(()->recover());}
    else throw new AssertionError(mode);
   }
  }
  System.out.print("PASS");
 }
}
'''

SAVE_HARNESS = r'''
package io.github.russianranger.cohclientinteractive;
import java.util.*;
public class SaveObservationHost {
 Object finalGuestReport,characterSavedEvent,characterConnectedEvent;String session;long observedClientPid;boolean reopen;
 static Object jsonValue(Object value){return value;}boolean zoningEnabled(){return reopen;}
 static class Zoning {int map;int currentMap(){return map;}}final Zoning zoning=new Zoning();
 static Map<String,Object> map(Object... values){Map<String,Object> m=new LinkedHashMap<>();for(int i=0;i<values.length;i+=2)m.put((String)values[i],values[i+1]);return m;}
 METHODS
 @SuppressWarnings("unchecked") public static void main(String[] args)throws Exception {
  List<Object> fixtures=FIXTURE_VALUES;int index=Integer.parseInt(args[0]);boolean reopen=index==1,zoning=reopen;
  Map<String,Object> report=(Map<String,Object>)fixtures.get(index),proof=(Map<String,Object>)report.get(reopen?"character_reopen":"character_creation"),login=(Map<String,Object>)report.get("local_login");
  String session=(String)report.get("session_id");long pid=((Number)proof.get("client_pid")).longValue();
  Map<String,Object> saved=map("type","character_saved","session_id",session,"client_pid",pid,"character_id",1L,"name","THORHERO","committed_sql_verified",true);
  Map<String,Object> connected=map("type","character_connected","session_id",session,"client_pid",pid,"character_id",1L,"name","THORHERO","account","COHLOCAL","map_id",1L);
  if(reopen){connected.put("baseline_character_id",1L);connected.put("reopen_verified",true);connected.put("existing_character_verified",true);connected.put("zoning_enabled",true);connected.put("connected_on_supported_map",true);saved.put("zoning_enabled",true);saved.put("map_id",1L);}
  String mode=args[1];boolean terminal=mode.startsWith("terminal_");if(terminal)mode=mode.substring(9);Object reportValue=report,savedValue=saved,connectedValue=connected;int currentMap=1;
  if(mode.equals("missing_event"))savedValue=null;
  if(mode.equals("missing_connected"))connectedValue=null;
  if(mode.equals("foreign_event"))saved.put("session_id","00000000000000000000000000000000");
  if(mode.equals("foreign_pid"))saved.put("client_pid",pid+1);
  if(mode.equals("foreign_connected"))connected.put("session_id","00000000000000000000000000000000");
  if(mode.equals("foreign_report"))report.put("session_id","00000000000000000000000000000000");
  if(mode.equals("wrong_scope"))report.put("scope","recovery_guest_outputs");
  if(mode.equals("wrong_account"))proof.put("account","OTHER");
  if(mode.equals("wrong_name"))proof.put("name","OTHER");
  if(mode.equals("wrong_id"))proof.put("character_id",2L);
  if(mode.equals("wrong_auth"))login.put("auth_id",2L);
  if(mode.equals("auth_out_of_range")){proof.put("auth_id",4294967296L);login.put("auth_id",4294967296L);}
  if(mode.equals("pid_out_of_range")){pid=4294967296L;proof.put("client_pid",pid);login.put("client_pid",pid);saved.put("client_pid",pid);connected.put("client_pid",pid);}
  if(mode.equals("foreign_login"))login.put("session_id","00000000000000000000000000000000");
  if(mode.equals("wrong_map"))currentMap=5;
  if(mode.equals("bad_snapshot"))proof.put("snapshot_sha256","bad");
  if(mode.equals("empty_rows"))((Map<String,Object>)proof.get("row_counts")).put(args[2],0L);
  if(mode.equals("bad_table_hash"))((Map<String,Object>)proof.get("table_sha256")).put(args[2],"bad");
  if(mode.equals("proof_flag"))proof.put(args[2],false);
  if(mode.equals("login_flag"))login.put(args[2],false);
  if(mode.equals("forced_stop"))proof.put("forced_stop_before_save",true);
  if(mode.equals("event_not_committed"))saved.put("committed_sql_verified",false);
  if(mode.equals("pid_wrong_type"))proof.put("client_pid",String.valueOf(pid));
  if(mode.equals("no_native_server"))report.put("mapserver_started",false);
  if(mode.equals("missing_login_count"))proof.remove("login_count");
  if(mode.equals("wrong_login_count"))proof.put("login_count",1L);
  if(mode.equals("wrong_before_login_count"))proof.put("before_login_count",0L);
  if(mode.equals("float_login_count"))proof.put("login_count",2.0);
  if(mode.equals("string_login_count"))proof.put("login_count","2");
  if(mode.equals("cleanup_failed")){report.put("passed",false);report.put("cleanup_complete",false);login.put("database_preserved",false);}
  if(terminal){SaveObservationHost host=new SaveObservationHost();host.finalGuestReport=mode.equals("unknown")?null:reportValue;host.characterSavedEvent=savedValue;host.characterConnectedEvent=connectedValue;host.session=session;host.observedClientPid=pid;host.reopen=reopen;host.zoning.map=currentMap;System.out.print(host.terminalSaveObservation());}
  else System.out.print(committedCharacterSaveObserved(reportValue,savedValue,connectedValue,session,pid,reopen,zoning,currentMap));
 }
}
'''


class CompletedGuestReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='coh-completed-report-');cls.addClassCleanup(cls.tmp.cleanup);base=Path(cls.tmp.name)
        host=base/'CompletedGuestHost.java';host.write_text(REPORT_HARNESS)
        source=(JAVA/'ClientRuntime.java').read_text()
        methods='\n'.join(method(source,s)for s in ('static boolean committedCharacterSaveObserved(', 'private static long preparationInteger(', 'private Boolean terminalSaveObservation('))
        save=base/'SaveObservationHost.java';save.write_text(SAVE_HARNESS.replace('METHODS',methods).replace('FIXTURE_VALUES',java_value(FIXTURES)))
        subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','--release','8','-d',str(base),str(REPORTS_JAVA),str(JAVA/'ClientAcceptance.java'),str(host),str(save)],check=True,capture_output=True,text=True)

    def carrier(self,mode):
        run=subprocess.run(['java','-cp',self.tmp.name,'io.github.russianranger.cohclientinteractive.CompletedGuestHost',mode],check=True,capture_output=True,text=True,timeout=15)
        self.assertEqual(run.stdout,'PASS')

    def save(self,report,mode,*arguments,expected=False):
        run=subprocess.run(['java','-cp',self.tmp.name,'io.github.russianranger.cohclientinteractive.SaveObservationHost',str(report),mode,*arguments],check=True,capture_output=True,text=True,timeout=15)
        self.assertEqual(run.stdout,str(expected).lower())

    def test_exact_completed_carrier_reused_without_upgrading_failed_wrapper(self):self.carrier('reuse')
    def test_atomic_commit_preserves_collisions_and_refuses_unowned_or_partial_parts(self):
        for mode in ('atomic_commit','commit_collision','commit_linked_part','commit_broken_part','commit_foreign_part'):
            with self.subTest(mode=mode):self.carrier(mode)
    def test_deleted_corrupt_truncated_and_same_size_changed_carriers_recover(self):
        for mode in ('deleted','corrupt','truncated','same_size'):
            with self.subTest(mode=mode):self.carrier(mode)
    def test_changed_guest_or_receipt_never_suppresses_recovery(self):
        for mode in ('guest_changed','marker_changed','foreign_marker'):
            with self.subTest(mode=mode):self.carrier(mode)
    def test_partial_or_unreceipted_atomic_commit_preserves_original_evidence(self):
        for mode in ('before_atomic_commit','after_commit_before_receipt','truncated_before_mark'):
            with self.subTest(mode=mode):self.carrier(mode)
    def test_foreign_sessions_and_missing_request_members_are_refused(self):
        for mode in ('foreign_wrapper','foreign_caller','missing_request'):
            with self.subTest(mode=mode):self.carrier(mode)
    def test_completed_wrapper_requires_matching_app_operation_run_and_version(self):
        for mode in ('foreign_app','foreign_operation','foreign_run','bad_version','missing_identity','invalid_wrapper_utf8'):
            with self.subTest(mode=mode):self.carrier(mode)
    def test_android_wrapper_has_headroom_beyond_embedded_guest_json_and_a_finite_bound(self):
        self.carrier('large_wrapper');self.carrier('oversized_wrapper')
    def test_colliding_or_unsafe_zip_members_are_refused(self):
        for mode in ('duplicate_entry','unsafe_entry'):
            with self.subTest(mode=mode):self.carrier(mode)
    def test_linked_guest_carrier_or_receipt_is_refused(self):
        for mode in ('hardlinked_carrier','symlinked_carrier','hardlinked_guest','marker_symlink'):
            with self.subTest(mode=mode):self.carrier(mode)
    def test_only_one_valid_root_session_can_bind_completed_preservation(self):
        for mode in ('duplicate_session','nested_session','invalid_json'):
            with self.subTest(mode=mode):self.carrier(mode)
        self.carrier('escaped_key')
    def test_both_actual_save_projections_require_matching_live_event_controls(self):
        for report in range(2):self.save(report,'current',expected=True)
    def test_later_cleanup_failure_does_not_erase_separate_committed_save_observation(self):
        for report in range(2):self.save(report,'cleanup_failed',expected=True)
    def test_missing_or_foreign_current_session_identity_cannot_record_save(self):
        for report in range(2):
            for mode in ('missing_event','missing_connected','foreign_event','foreign_pid','foreign_connected','foreign_report','foreign_login','wrong_scope','wrong_account','wrong_name','wrong_id','wrong_auth','wrong_map','pid_wrong_type'):
                with self.subTest(report=report,mode=mode):self.save(report,mode)
    def test_committed_sql_ordinary_logout_and_native_server_are_required(self):
        for report in range(2):
            for flag in ('verified','connected_on_atlas','committed_sql_verified','requested_logout_observed','logout_timer_observed','disconnected_before_sql'):
                with self.subTest(report=report,flag=flag):self.save(report,'proof_flag',flag)
            for mode in ('forced_stop','event_not_committed','no_native_server','bad_snapshot'):
                with self.subTest(report=report,mode=mode):self.save(report,mode)
    def test_local_login_and_full_committed_character_table_receipts_are_required(self):
        for report in range(2):
            for flag in ('local_login_verified','local_account_verified','character_list_sent','character_list_response_sent'):
                with self.subTest(report=report,flag=flag):self.save(report,'login_flag',flag)
            for table in ('ents','ents2','powers','costumeparts'):
                with self.subTest(report=report,table=table):
                    self.save(report,'empty_rows',table);self.save(report,'bad_table_hash',table)
    def test_reopen_preservation_flags_remain_required(self):
        for flag in ('reopen_verified','existing_character_verified','preserved_existing_identity','native_client_ready_observed','powers_preserved','costume_preserved','selected_rows_preserved','committed_native_position_verified','zoning_enabled','connected_on_supported_map'):
            with self.subTest(flag=flag):self.save(1,'proof_flag',flag)
    def test_reopen_login_count_and_native_identity_bounds_remain_required(self):
        for mode in ('missing_login_count','wrong_login_count','wrong_before_login_count','float_login_count','string_login_count'):
            with self.subTest(mode=mode):self.save(1,mode)
        for report in range(2):
            for mode in ('auth_out_of_range','pid_out_of_range'):
                with self.subTest(report=report,mode=mode):self.save(report,mode)
    def test_finalization_failure_preserves_strict_committed_save_observation(self):
        for report in range(2):
            self.save(report,'terminal_current',expected=True)
            self.save(report,'terminal_cleanup_failed',expected=True)
            self.save(report,'terminal_foreign_event')
            self.save(report,'terminal_foreign_report')
            self.save(report,'terminal_missing_event')
    def test_missing_final_guest_report_keeps_save_observation_unknown(self):
        for report in range(2):
            result=subprocess.run(['java','-cp',self.tmp.name,'io.github.russianranger.cohclientinteractive.SaveObservationHost',str(report),'terminal_unknown'],check=True,capture_output=True,text=True,timeout=15)
            self.assertEqual(result.stdout,'null')
    def test_finalization_carrier_never_converts_save_observation_into_overall_pass(self):
        source=(JAVA/'ClientRuntime.java').read_text();terminal=method(source,'private File retainFailureReport(')
        self.assertIn('Boolean saveObservation=terminalSaveObservation()',terminal)
        self.assertIn('.put("committed_save_observed",saveObservation==null?JSONObject.NULL:saveObservation)',terminal)
        self.assertIn('.put("character_save_qualification",false)',terminal)
        self.assertIn('.put("passed",false)',terminal)
        self.assertIn('"character_saved_event"',terminal)
        self.assertIn('"character_connected_event"',terminal)
    def test_global_pass_predicate_and_atomic_report_order_are_preserved(self):
        source=(JAVA/'ClientRuntime.java').read_text();run=method(source,'private Result runCharacter(')
        self.assertIn('passed = guestPassed && cleanup && !cancelled && error == null && receiverFailure == null\n                        && inputFailed == 0 && surfaceAccepted(report) && loginSurfaceAccepted() && characterSurfaceAccepted(report);',run)
        publication=method(source,'private void publish(')
        self.assertLess(publication.index('ClientReports.commitNormalArchive('),publication.index('ClientReports.completedGuest('))
        self.assertIn('StandardOpenOption.CREATE_NEW',publication)
        self.assertIn('Committed character save recorded; Android report checks incomplete',source)
        self.assertIn('isCleanupBlocked() ? BLOCK_MESSAGE',source)
        self.assertIn('"qualification_gates",qualificationGates(',publication)
        reports=REPORTS_JAVA.read_text();self.assertIn('interrupted_unverified',reports);self.assertIn('\\"session_attribution_verified\\":false',reports)


if __name__=='__main__':unittest.main()
