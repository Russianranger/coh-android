"""Only new nonnetwork receive-prefix, fixed projection and composition controls."""
import ast
import copy
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest import mock

import db_received_prefix as prefix
import hosted_auth_db_development as stage
from test_auth_db_development_driver import positive

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
ENV=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
RUN_RECORDS={}
MODES=(('release',['-O2']),('asan_ubsan',['-O1','-g','-fsanitize=address,undefined',
    '-fno-omit-frame-pointer','-fno-pie','-no-pie']))


def received(preflight=False):
    entries=[] if preflight else [dict(command='DBGAMESERVER_SEND_PLAYERS',header_decoded=True,
        phase=2,legacy=False,compressed=False)]
    return dict(schema='coh-db-received-header-prefix-v1',available=True,context_verified=not preflight,
        retired=not preflight,truncated=False,instances=int(not preflight),service_calls=int(not preflight),
        total_seen=len(entries),first_unsupported_attributed=False,body_acceptance_observed=False,entries=entries)


def native(preflight=False):
    value=positive(preflight);value['schema']=value['schema'][:-1]+'2'
    value['db_received_prefix']=received(preflight);return value


def compile_shell(target,source,flags,extra=()):
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',*flags,
        '-I'+str(ROOT/'native-android/include'),'-I'+str(HERE/'windows'),str(source),
        *map(str,extra),'-o',str(target)],check=True,capture_output=True)


class ReceivedPrefixTests(unittest.TestCase):
    def test_exact_original_catalogue_decoder_main_and_unmodified_positive_admission(self):
        for name,digest in prefix.SOURCE_PINS.items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest)
        self.assertEqual(prefix.DB_PHASES,stage.DB_PHASES)
        backend=(ROOT/'upstream/ouroboros/Common/comm_backend.h').read_text()
        body=backend.split('// DBServer to client',1)[1].split('// this is communication',1)[0]
        self.assertEqual(tuple(re.findall(r'DBGAMESERVER_([A-Z_]+)',body)),prefix.COMMANDS)
        base=(ROOT/'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/network/net_structdefs.h').read_text()
        self.assertRegex(base,r'COMM_MAX_CMD\s*=\s*2')
        header=(HERE/'windows/db_received_prefix.h').read_text()
        self.assertEqual([(int(a),b) for a,b in re.findall(r'X\((\d+),([A-Z_]+)\)',header)],list(enumerate(prefix.COMMANDS,2)))
        previous=subprocess.check_output(['git','-C',str(ROOT),'show',
            'ed77036d1b7f7e47588d74408506d738293643a9:'+stage.PREFIX+'deployment/hosted_auth_db_development.py'])
        def functions(source):return {node.name:ast.dump(node,include_attributes=False) for node in ast.parse(source).body if isinstance(node,ast.FunctionDef)}
        old,new=functions(previous),functions(Path(stage.__file__).read_bytes())
        for name in ('private_json','native_shape','admit_probe'):self.assertEqual(old[name],new[name])
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);sources=stage.prepare_project(ROOT,root/'project',root/'crypto',root/'zlib')
            self.assertEqual(len(sources),16);self.assertEqual(len(set(sources)),16)
            self.assertIn(HERE/'windows/db_development_received_probe.c',sources)
            self.assertIn(HERE/'windows/wrapped_db_received_prefix.c',sources)
            self.assertNotIn(HERE/'windows/db_development_probe.c',sources)
            self.assertNotIn(ROOT/'native-android/engine/dbclient/coh_db_session.c',sources)
            self.assertFalse(any('test_' in p.name for p in sources))

    def test_fixed_names_strict_pairs_types_caps_and_no_untrusted_projection(self):
        valid=received();self.assertEqual(prefix.admit(valid)['entries'][0]['phase'],'WAIT_PLAYERS')
        for key in prefix.KEYS:
            bad=copy.deepcopy(valid);bad[key]='PRIVATE_CANARY'
            with self.subTest(key=key),self.assertRaises(ValueError):prefix.admit(bad)
        changes=[{'cookie':'PRIVATE_CANARY'},{'instances':True},{'total_seen':65536},{'service_calls':-1},
            {'truncated':True},{'instances':2},{'total_seen':0},{'available':False}]
        # Two instances are a valid fixed diagnostic only with context false.
        changes[5]={'context_verified':True,'instances':2}
        for change in changes:
            with self.subTest(change=change),self.assertRaises(ValueError):prefix.admit(dict(valid,**change))
        for change in ({'command':'PRIVATE_CANARY'},{'command':900001},{'command':'NONE'},
                {'header_decoded':False},{'phase':True},{'phase':13},{'legacy':1},{'compressed':0},
                {'raw_opcode':900001}):
            bad=copy.deepcopy(valid);bad['entries'][0].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):prefix.admit(bad)
        for name,decoded in (('NONE',False),('UNKNOWN',True)):
            bad=copy.deepcopy(valid);bad['entries'][0].update(command=name,header_decoded=decoded)
            self.assertEqual(prefix.admit(bad)['entries'][0]['command'],name)
        capped=copy.deepcopy(valid);capped.update(total_seen=17,truncated=True,entries=capped['entries']*16)
        self.assertEqual(len(prefix.admit(capped)['entries']),16)
        with self.assertRaises(ValueError):prefix.admit(dict(capped,entries=capped['entries']+[capped['entries'][0]]))
        for preflight in (False,True):
            base,projected=prefix.native(native(preflight),preflight)
            self.assertEqual(base,positive(preflight));stage.admit_probe(base,preflight)
            prefix.completion(projected,preflight)
        with self.assertRaises(ValueError):prefix.native(positive())
        with self.assertRaises(ValueError):prefix.completion(dict(prefix.admit(valid),context_verified=False))

    def test_failure_projection_latches_received_prefix_only_for_completed_strict_child(self):
        value=native();value.update(passed=False,phase=4,failure=6,status=2,db_phase=2,db_player_lists=0,db_unsupported=3)
        value['db_received_prefix']['entries']=[dict(command='DBGAMESERVER_'+name,header_decoded=True,phase=2,
            legacy=False,compressed=False) for name in ('ACCOUNTSERVER_UNAVAILABLE','ACCOUNTSERVER_CHARCOUNT','ACCOUNTSERVER_CHARCOUNT')]
        value['db_received_prefix']['total_seen']=3
        def observe(raw,code=1):
            with tempfile.TemporaryFile() as output:
                output.write(raw);output.flush()
                return stage.observation(mock.Mock(poll=mock.Mock(return_value=code)),output,received=True)
        result=observe(json.dumps(value).encode());self.assertEqual(result['json_state'],'VALID')
        self.assertEqual(result['db_received_prefix']['entries'][0]['command'],'DBGAMESERVER_ACCOUNTSERVER_UNAVAILABLE')
        self.assertFalse(result['db_received_prefix']['first_unsupported_attributed'])
        self.assertFalse(result['db_received_prefix']['body_acceptance_observed'])
        for raw in (json.dumps(dict(value,cookie='PRIVATE_CANARY')).encode(),
                json.dumps(value).replace('"total_seen": 3','"total_seen": 3,"total_seen": 3').encode(),
                json.dumps(value).replace('"total_seen": 3','"total_seen": NaN').encode(),b'x'*8193):
            result=observe(raw);self.assertNotEqual(result['json_state'],'VALID')
            self.assertNotIn('db_received_prefix',result);self.assertNotIn('PRIVATE_CANARY',json.dumps(result))
        for code in (None,True,3):self.assertNotIn('db_received_prefix',observe(json.dumps(value).encode(),code))

    def test_private_failure_and_late_stop_keep_primary_and_fixed_prefix(self):
        for mode in ('success','native_and_stop','timeout'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as name,ExitStack() as stack:
                sink={};buffers=[];real_bytearray=bytearray
                def buffer(raw):value=real_bytearray(raw);buffers.append(value);return value
                stack.enter_context(mock.patch.object(stage,'bytearray',side_effect=buffer,create=True))
                job=mock.Mock(handle=123,empty_before_close=True,assignment_verified=True,launch_state='RESUMED')
                job.kernel.CloseHandle.return_value=True
                child=mock.Mock(stdin=mock.Mock(),returncode=0 if mode=='success' else 1)
                child.poll.return_value=None if mode=='timeout' else child.returncode
                primary=subprocess.TimeoutExpired('PRIVATE_CANARY',37)
                def popen(argv,**kwargs):
                    def communicate(input,timeout):
                        self.assertIs(input,buffers[0])
                        if mode=='timeout':raise primary
                        value=native();value['passed']=child.returncode==0
                        kwargs['stdout'].write(json.dumps(value).encode());kwargs['stdout'].flush()
                    child.communicate.side_effect=communicate;return child
                def stop(actual):
                    self.assertIs(actual,child);self.assertFalse(any(buffers[0]))
                    if mode!='success':raise OSError('PRIVATE_LATE_CANARY')
                    job.handle=None;return True
                job.popen.side_effect=popen;job.stop.side_effect=stop
                stack.enter_context(mock.patch.object(stage,'DevelopmentJob',return_value=job))
                if mode=='success':self.assertTrue(stage.private_probe(Path('unused'),23000,Path(name),failure_observation=sink)['passed'])
                else:
                    with self.assertRaises((ValueError,subprocess.TimeoutExpired)) as error:
                        stage.private_probe(Path('unused'),23000,Path(name),failure_observation=sink)
                    if mode=='timeout':self.assertIs(error.exception,primary)
                    else:self.assertEqual(str(error.exception),'development_private_probe_refused')
                child.stdin.close.assert_called_once();self.assertFalse(any(buffers[0]))
                self.assertNotIn('PRIVATE_',json.dumps(sink))
                if mode=='native_and_stop':
                    self.assertEqual(sink['json_state'],'VALID');self.assertIn('db_received_prefix',sink)
                    self.assertFalse(sink['owned_child_cleanup_complete'])

    def test_additive_main_print_overlay_preserves_original_return_and_cleanup(self):
        # Reuse the exact admitted synthetic API shell, not its old 48 cases.
        fixture=(HERE/'windows/test_db_development_probe.c').read_text().split('/* These are explicitly synthetic',1)[1]
        preamble='#define COH_DB_DEVELOPMENT_PROBE_TEST 1\n#define main controlled_probe_main\n#include "db_development_received_probe.c"\n#undef main\n/* These are explicitly synthetic'
        suffix='''\nCohStatus coh_dev_db_received_prefix(CohDevDbReceivedPrefix *out) {
            *out=(CohDevDbReceivedPrefix){0};
            if(is("platform"))return COH_OK;
            out->instances=out->service_calls=out->count=out->total_seen=1;
            out->context_verified=out->retired=1;
            out->entries[0]=(CohDevDbPrefixEntry){2,2,1,0,0};return COH_OK;
        }\n'''
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);source=root/'main.c';source.write_text(preamble+fixture+suffix)
            for mode,flags in MODES:
                target=root/mode;compile_shell(target,source,flags)
                for scenario,argument in (('success','23000'),('service','23000'),('platform','--platform-preflight')):
                    result=subprocess.run([target,scenario,argument],input=b'probe-account\nprobe-password\n',
                        capture_output=True,timeout=10,env=ENV)
                    self.assertEqual(result.returncode,1 if scenario=='service' else 0,result.stderr.decode())
                    self.assertEqual(result.stderr,b'')
                    value=stage.private_json(result.stdout);base,projected=prefix.native(value,scenario=='platform')
                    self.assertIs(base['passed'],scenario!='service')
                    self.assertTrue(base['local_sensitive_buffers_wiped']);self.assertTrue(base['owner_cleanup_complete'])
                    if scenario!='service':stage.admit_probe(base,scenario=='platform');prefix.completion(projected,scenario=='platform')
                    RUN_RECORDS.setdefault('main_overlay',[]).append({'mode':mode,'scenario':scenario,
                        'native_schema':value['schema'],'original_return_preserved':True,
                        'fixed_prefix_admitted':True,'private_buffers_wiped':base['local_sensitive_buffers_wiped']})
                    for private in ('probe-account','probe-password','user_id','cookie','connect_id','raw_opcode'):
                        self.assertNotIn(private,result.stdout.decode())

    def test_same_copy_wrapper_order_binding_limits_and_protocol_parity(self):
        sources=[HERE/'windows/test_db_received_prefix.c',ROOT/'native-android/engine/dbclient/coh_dbclient.c',
            ROOT/'native-android/engine/auth/coh_auth.c',ROOT/'native-android/protocol/coh_protocol.c',
            ROOT/'native-android/src/coh_blowfish.c']
        with tempfile.TemporaryDirectory() as name:
            for mode,flags in MODES:
                objects=[];directory=Path(name)/mode;directory.mkdir()
                for index,source in enumerate(sources):
                    obj=directory/(str(index)+'.o');objects.append(obj)
                    # Match the retained ordinary-code warning policy: only the
                    # two unchanged protocol/blowfish TUs are built at O0.
                    optimization=['-O0'] if index>=3 else []
                    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',*flags,*optimization,
                        '-I'+str(ROOT/'native-android/include'),'-c',str(source),'-o',str(obj)],
                        check=True,capture_output=True)
                target=directory/'prefix'
                subprocess.run(['cc',*flags,*map(str,objects),'-Wl,--wrap=malloc,--wrap=calloc,--wrap=free',
                    '-lz','-lm','-o',str(target)],check=True,capture_output=True)
                result=subprocess.run([target],capture_output=True,timeout=15,env=ENV,check=True)
                self.assertEqual(result.stderr,b'');value=json.loads(result.stdout)
                self.assertIs(value['passed'],True);self.assertFalse(value['sockets_executed'])
                self.assertFalse(value['real_auth_or_db']);self.assertFalse(value['first_unsupported_attributed'])
                self.assertEqual(value['checks'],827);self.assertEqual(value['scenarios'],30)
                RUN_RECORDS.setdefault('same_copy_wrapper',{})[mode]=value


if __name__=='__main__':unittest.main()
