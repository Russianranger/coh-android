"""New main/owner boundary controls. Platform and owner are synthetic here."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
SCENARIOS=('success','tcp-init','tcp-limits','udp-init','entropy','checksum','create',
    'begin','service','deadline','wrong-phase','wrong-failure','wrong-status','wrong-auth',
    'wrong-db','wrong-auth-final','wrong-db-final','unconsumed','unselected','no-list',
    'nonempty','not-destroyed','no-close-policy','wrong-frames','two-login','two-list',
    'queue','unsupported','choose','handoff','zero-slots','too-many-slots','bad-base',
    'no-development','normal-version','reference','character','map','world',
    'owner-close','owner-destroy','diagnostics','tcp-handles','tcp-finish','udp-finish',
    'udp-handles','udp-close','udp-cleanup')


class DbDevelopmentProbeTests(unittest.TestCase):
    def test_new_private_main_owner_boundary_and_late_cleanup(self):
        with tempfile.TemporaryDirectory() as name:
            for mode,flags in (('release',['-O2']),('asan_ubsan',['-O1','-g',
                    '-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie'])):
                target=Path(name)/mode
                subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',*flags,
                    '-I'+str(ROOT/'native-android/include'),HERE/'windows/test_db_development_probe.c',
                    '-o',target],check=True,capture_output=True)
                for scenario in SCENARIOS:
                    result=subprocess.run([target,scenario,'23000'],input=b'probe-account\nprobe-password\n',
                        capture_output=True,timeout=10,env=dict(os.environ,
                        ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
                    self.assertEqual(result.returncode,0 if scenario=='success' else 1,(mode,scenario,result.stderr.decode()))
                    self.assertEqual(result.stderr,b'')
                    body=json.loads(result.stdout)
                    self.assertIs(body['passed'],scenario=='success')
                    self.assertTrue(body['local_sensitive_buffers_wiped'])
                    for private in ('probe-account','probe-password','user_id','cookie','connect_id','executable_checksum'):
                        self.assertNotIn(private,result.stdout.decode())
                    self.assertTrue(body['development_skip_source_inference_only'])
                    self.assertFalse(body['server_development_skip_observed'])
                    self.assertFalse(body['graceful_peer_disconnect_acknowledged'])
                    self.assertFalse(body['real_server_provenance_verified_by_probe'])
                    if scenario=='success':
                        self.assertEqual((body['phase'],body['auth_phase'],body['db_phase']),(3,7,4))
                        self.assertEqual((body['auth_final_phase'],body['db_final_phase']),(8,11))
                        self.assertEqual((body['db_login_requests'],body['db_player_lists'],body['slots']),(1,1,12))
                        self.assertEqual((body['udp_created'],body['udp_closed'],body['udp_active']),(1,1,0))
                        for key in ('normal_version_admitted','checksum_reference_admitted','character_selected',
                                'map_handoff_verified','current_world_verified','db_queue_updates','db_unsupported',
                                'db_choices','db_handoffs'):
                            self.assertEqual(body[key],0)

    def test_private_input_and_port_refusals_leave_no_owner_or_grant(self):
        with tempfile.TemporaryDirectory() as name:
            target=Path(name)/'probe'
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-O2',
                '-I'+str(ROOT/'native-android/include'),HERE/'windows/test_db_development_probe.c',
                '-o',target],check=True,capture_output=True)
            for port,data in (('19999',b''),('60000',b''),('+23000',b''),('23000x',b''),
                    ('23000',b''),('23000',b'a\n'),('23000',b'\np\n'),('23000',b'a\n\n'),
                    ('23000',b'a'*15+b'\np\n'),('23000',b'a\n'+b'p'*17+b'\n'),
                    ('23000',b'a\np\nextra'),('23000',b'a\np\x00\n')):
                result=subprocess.run([target,'input',port],input=data,capture_output=True,timeout=10)
                self.assertEqual(result.returncode,1,result.stderr.decode())
                value=json.loads(result.stdout)
                self.assertFalse(value['passed']);self.assertTrue(value['local_sensitive_buffers_wiped'])
                for key in ('begun','grant_consumed','db_login_requests','db_player_lists','udp_created'):
                    self.assertEqual(value[key],0)
            preflight=subprocess.run([target,'platform','--platform-preflight'],capture_output=True,timeout=10,check=True)
            value=json.loads(preflight.stdout)
            self.assertEqual(value['schema'],'coh-auth-db-development-platform-preflight-v1')
            self.assertTrue(value['passed']);self.assertEqual(value['probe_stage'],10)
            self.assertTrue(value['checksum_measured_from_actual_probe'])
            for key in ('begun','grant_consumed','db_login_requests','db_player_lists','udp_created','udp_closed'):
                self.assertEqual(value[key],0)


if __name__=='__main__':unittest.main()
