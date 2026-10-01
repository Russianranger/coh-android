#!/usr/bin/env python3
"""Exercise shipped Java acceptance against stale frames and incomplete cleanup."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientAcceptance.java'
FIXTURE = r'''
package io.github.russianranger.cohclientinteractive;
import java.util.*;
public final class ClientAcceptanceHost {
    static Map<String,Object> map(Object... values) {
        Map<String,Object> result = new LinkedHashMap<>();
        for (int i=0;i<values.length;i+=2) result.put((String)values[i],values[i+1]);
        return result;
    }
    static final String SESSION = "0123456789abcdef0123456789abcdef";
    static List<Map<String,Object>> samples() {
        List<Map<String,Object>> samples = new ArrayList<>();
        for (int i=0;i<3;i++) samples.add(map("session_id",SESSION,"sequence",7,
            "pixel_copy_success",true,"non_uniform",true,"png_verified",true,
            "source_width",800,"source_height",600,"png_sha256",String.join("", Collections.nCopies(64,"a")),
            "captured_elapsed_ms",1000L+i*1000));
        return samples;
    }
    static Map<String,Object> cleanup() {
        return map("cleanup_complete",true,"cleanup_execution",map("diagnostic_initialized",true,
            "wine_started",true,"owned_child_count",1),"processes",Arrays.asList(map("exit_code",0,
            "input_closed",true,"output_capture_closed",true)),"cleanup",map("owned_processes_reaped",true,
            "wine_prefix_stopped",true),"wine_process_cleanup",map("complete",true,"remaining",0,"inspection_failures",0));
    }
    @SuppressWarnings("unchecked") static Map<String,Object> at(Map<String,Object> value,String key) {
        return (Map<String,Object>) value.get(key);
    }
    public static void main(String[] args) {
        List<Map<String,Object>> frames=samples(); Map<String,Object> cleanup=cleanup();
        Map<String,Object> login=map("local_login",map("session_id",SESSION,"client_pid",42,"profile","android-local-login",
            "local_login_verified",true,"character_list_sent",true,"local_account_verified",true,
            "character_list_response_sent",true,"database_preserved",true,"auth_id",1));
        Map<String,Object> saved=map("type","character_saved","session_id",SESSION,"client_pid",42,
            "character_id",7,"name","THORHERO","committed_sql_verified",true);
        Map<String,Object> connected=map("type","character_connected","session_id",SESSION,"client_pid",42,
            "character_id",7,"name","THORHERO","account","COHLOCAL","map_id",1);
        login.put("character_creation",map("verified",true,"session_id",SESSION,"client_pid",42,
            "character_id",7,"name","THORHERO","account","COHLOCAL","auth_id",1,"map_id",1,
            "committed_sql_verified",true,"protocol_logout_verified",true,"disconnected_before_sql",true,
            "forced_stop_before_save",false,"connected_on_atlas",true));
        Map<String,Object> interaction=map("interaction_session_completed",true,"input_effect_verified",false,
            "interaction_completion_reason","finish_requested");
        boolean expected=false,actual;
        switch(args[0]) {
            case "character_valid": expected=true;break;
            case "character_missing": login.remove("character_creation");break;
            case "character_unverified": at(login,"character_creation").put("verified",false);break;
            case "character_wrong_id": at(login,"character_creation").put("character_id",8);break;
            case "character_zero_id": at(login,"character_creation").put("character_id",0);break;
            case "character_fractional_id": at(login,"character_creation").put("character_id",7.5);break;
            case "character_missing_id": at(login,"character_creation").remove("character_id");break;
            case "character_wrong_name": at(login,"character_creation").put("name","OLDHERO");break;
            case "character_missing_name": at(login,"character_creation").remove("name");break;
            case "character_old_session": at(login,"character_creation").put("session_id","ffffffffffffffffffffffffffffffff");break;
            case "character_wrong_pid": at(login,"character_creation").put("client_pid",43);break;
            case "character_no_sql": at(login,"character_creation").put("committed_sql_verified",false);break;
            case "character_missing_sql": at(login,"character_creation").remove("committed_sql_verified");break;
            case "character_no_logout": at(login,"character_creation").remove("protocol_logout_verified");break;
            case "character_still_connected": at(login,"character_creation").put("disconnected_before_sql",false);break;
            case "character_force_saved": at(login,"character_creation").put("forced_stop_before_save",true);break;
            case "character_missing_stop_proof": at(login,"character_creation").remove("forced_stop_before_save");break;
            case "character_wrong_account": at(login,"character_creation").put("account","OLDACCOUNT");break;
            case "character_no_auth_id": at(login,"character_creation").put("auth_id",0);break;
            case "character_wrong_auth_id": at(login,"character_creation").put("auth_id",2);break;
            case "character_missing_login_auth_id": at(login,"local_login").remove("auth_id");break;
            case "character_no_atlas": at(login,"character_creation").put("connected_on_atlas",false);break;
            case "character_missing_atlas": at(login,"character_creation").remove("connected_on_atlas");break;
            case "character_wrong_map": at(login,"character_creation").put("map_id",2);break;
            case "character_database_lost": at(login,"local_login").put("database_preserved",false);break;
            case "character_no_save_event": saved.clear();break;
            case "character_event_wrong_id": saved.put("character_id",8);break;
            case "character_event_no_id": saved.remove("character_id");break;
            case "character_event_old_session": saved.put("session_id","ffffffffffffffffffffffffffffffff");break;
            case "character_event_wrong_pid": saved.put("client_pid",43);break;
            case "character_event_wrong_name": saved.put("name","OLDHERO");break;
            case "character_event_no_sql": saved.remove("committed_sql_verified");break;
            case "character_no_connected_event": connected.clear();break;
            case "character_connected_old_session": connected.put("session_id","ffffffffffffffffffffffffffffffff");break;
            case "character_connected_wrong_pid": connected.put("client_pid",43);break;
            case "character_connected_wrong_id": connected.put("character_id",8);break;
            case "character_connected_wrong_name": connected.put("name","OLDHERO");break;
            case "character_connected_wrong_account": connected.put("account","OLDACCOUNT");break;
            case "character_connected_wrong_map": connected.put("map_id",2);break;
            case "character_no_captures": frames.clear();break;
            case "character_two_captures": frames.remove(0);break;
            case "character_pre_save_frame": frames.get(0).put("sequence",6);break;
            case "character_pre_save_capture": frames.get(0).put("captured_elapsed_ms",999);break;
            case "character_stale_capture_session": frames.get(0).put("session_id","ffffffffffffffffffffffffffffffff");break;
            case "character_blank_capture": frames.get(0).put("non_uniform",false);break;
            case "login_valid": expected=true;break;
            case "login_old_session": at(login,"local_login").put("session_id","ffffffffffffffffffffffffffffffff");break;
            case "login_wrong_pid": at(login,"local_login").put("client_pid",43);break;
            case "login_fractional_pid": at(login,"local_login").put("client_pid",42.5);break;
            case "login_wrong_profile": at(login,"local_login").put("profile","old-diagnostic");break;
            case "login_unproved": at(login,"local_login").put("local_login_verified",false);break;
            case "login_no_character_list": at(login,"local_login").put("character_list_sent",false);break;
            case "login_no_account": at(login,"local_login").put("local_account_verified",false);break;
            case "login_no_response": at(login,"local_login").put("character_list_response_sent",false);break;
            case "login_not_preserved": at(login,"local_login").put("database_preserved",false);break;
            case "login_missing": login.clear();break;
            case "interaction_finish": expected=true; break;
            case "interaction_timeout": interaction.put("interaction_completion_reason","interaction_timeout");expected=true;break;
            case "interaction_incomplete": interaction.put("interaction_session_completed",false);break;
            case "interaction_unproven_effect": interaction.put("input_effect_verified",true);break;
            case "interaction_missing_effect": interaction.remove("input_effect_verified");break;
            case "interaction_unknown_finish": interaction.put("interaction_completion_reason","old_session");break;
            case "valid": expected=true; break;
            case "static_frame": expected=true; break;
            case "stale_session": frames.get(0).put("session_id","ffffffffffffffffffffffffffffffff"); break;
            case "missing_pixelcopy": frames.get(0).remove("pixel_copy_success"); break;
            case "missing_png": frames.get(0).remove("png_verified"); break;
            case "blank_frame": frames.get(0).put("non_uniform",false); break;
            case "bad_hash": frames.get(0).put("png_sha256","not-a-hash"); break;
            case "wrong_size": frames.get(0).put("source_width",1024); break;
            case "short_span": for(int i=0;i<3;i++) frames.get(i).put("captured_elapsed_ms",1000+i*100); break;
            case "before_window": frames.get(0).put("captured_elapsed_ms",999); break;
            case "after_window": frames.get(2).put("captured_elapsed_ms",3501); break;
            case "duplicate_capture": frames.get(2).put("captured_elapsed_ms",2000); break;
            case "zero_sequence": frames.get(0).put("sequence",0); break;
            case "pre_event_frame": frames.get(0).put("sequence",5); break;
            case "at_event_frame": frames.get(0).put("sequence",6); break;
            case "fractional_time": frames.get(0).put("captured_elapsed_ms",1000.5); break;
            case "cleanup_valid": expected=true; break;
            case "cleanup_postgres_stopped": cleanup.put("postgres_started",true);at(cleanup,"cleanup").put("postgres_graceful",true);expected=true;break;
            case "cleanup_postgres_running": cleanup.put("postgres_started",true);at(cleanup,"cleanup").put("postgres_graceful",false);break;
            case "cleanup_postgres_missing": cleanup.put("postgres_started",true);break;
            case "cleanup_missing": cleanup.remove("cleanup_execution"); break;
            case "cleanup_orphan": at(cleanup,"wine_process_cleanup").put("remaining",1); break;
            case "cleanup_unreadable": at(cleanup,"wine_process_cleanup").put("inspection_failures",1); break;
            case "cleanup_capture_live": ((Map)((List)cleanup.get("processes")).get(0)).put("output_capture_closed",false); break;
            case "cleanup_child_omitted": at(cleanup,"cleanup_execution").put("owned_child_count",2); break;
            case "cleanup_no_guest": cleanup=map("cleanup_complete",true,"processes",Collections.emptyList(),
                "cleanup_execution",map("diagnostic_initialized",false,"wine_started",false,"owned_child_count",0));expected=true;break;
            default: throw new AssertionError("Unknown fixture");
        }
        actual=args[0].startsWith("character_") ? ClientAcceptance.characterCreationAccepted(login,saved,connected,frames,SESSION,42,500,4000,1000,3500,6)
            : args[0].startsWith("login_") ? ClientAcceptance.localLoginVerified(login,SESSION,42)
            : args[0].startsWith("interaction_") ? ClientAcceptance.interactionCompleted(interaction)
            : args[0].startsWith("cleanup_") ? ClientAcceptance.cleanupSafe(cleanup)
            : ClientAcceptance.surfaceAccepted(frames,SESSION,500,4000,1000,3500,6);
        if(actual!=expected) throw new AssertionError(args[0]+" expected="+expected+" actual="+actual);
    }
}
'''


class ClientAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='coh-client-gate-')
        harness = Path(cls.tmp.name) / 'ClientAcceptanceHost.java'
        harness.write_text(FIXTURE)
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                        '-d', cls.tmp.name, str(SOURCE), str(harness)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_interaction_completion_boundaries(self):
        for mode in ('interaction_finish', 'interaction_timeout', 'interaction_incomplete',
                     'interaction_unproven_effect', 'interaction_missing_effect', 'interaction_unknown_finish'):
            with self.subTest(mode=mode): self.execute(mode)

    def test_local_login_requires_current_session_protocol_and_persistence(self):
        for mode in ('login_valid', 'login_old_session', 'login_wrong_pid', 'login_fractional_pid',
                     'login_wrong_profile', 'login_unproved', 'login_no_character_list',
                     'login_not_preserved', 'login_missing', 'login_no_account', 'login_no_response'):
            with self.subTest(mode=mode): self.execute(mode)

    def test_character_requires_matching_protocol_save_committed_sql_and_fresh_captures(self):
        cases = ('valid', 'missing', 'unverified', 'wrong_id', 'zero_id', 'fractional_id', 'missing_id',
                 'wrong_name', 'missing_name', 'old_session', 'wrong_pid', 'no_sql', 'missing_sql',
                 'no_logout', 'still_connected', 'force_saved', 'missing_stop_proof', 'wrong_account',
                 'no_auth_id', 'wrong_auth_id', 'missing_login_auth_id', 'no_atlas', 'missing_atlas', 'wrong_map', 'database_lost', 'no_save_event', 'event_wrong_id',
                 'event_no_id', 'event_old_session', 'event_wrong_pid', 'event_wrong_name', 'event_no_sql',
                 'no_connected_event', 'connected_old_session', 'connected_wrong_pid', 'connected_wrong_id',
                 'connected_wrong_name', 'connected_wrong_account', 'connected_wrong_map', 'no_captures',
                 'two_captures', 'pre_save_frame', 'pre_save_capture', 'stale_capture_session', 'blank_capture')
        for case in cases:
            with self.subTest(case=case): self.execute('character_' + case)

    def test_frame_boundaries(self):
        for mode in ('valid', 'static_frame', 'stale_session', 'missing_pixelcopy',
                     'missing_png', 'blank_frame', 'bad_hash', 'wrong_size', 'short_span',
                     'before_window', 'after_window', 'duplicate_capture', 'zero_sequence', 'pre_event_frame', 'at_event_frame', 'fractional_time'):
            with self.subTest(mode=mode): self.execute(mode)

    def test_cleanup_boundaries(self):
        for mode in ('cleanup_valid', 'cleanup_missing', 'cleanup_orphan', 'cleanup_unreadable',
                     'cleanup_capture_live', 'cleanup_child_omitted', 'cleanup_no_guest',
                     'cleanup_postgres_stopped', 'cleanup_postgres_running', 'cleanup_postgres_missing'):
            with self.subTest(mode=mode): self.execute(mode)

    def execute(self, mode):
        subprocess.run(['java', '-cp', self.tmp.name,
                        'io.github.russianranger.cohclientinteractive.ClientAcceptanceHost', mode],
                       check=True, capture_output=True, timeout=10)


if __name__ == '__main__': unittest.main()
