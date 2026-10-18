#!/usr/bin/env python3
"""Bounded fixed diagnostics; synthetic JSON and tiny owned Linux children only."""
import copy,json,os,subprocess,sys,tempfile,types,unittest
from pathlib import Path
from unittest import mock
import groups_native_status as n
import summarize_groups_capture as summary
import test_groups_public_summary as public_fixture
CANARY='PRIVATE-STDOUT-ACCOUNT-ID-PATH-LOG-CANARY'
def status():
    return {'schema':n.SCHEMA,'passed':False,'initial_packet_observed':False,'status':1,
        'opened_sockets':2,'closed_sockets':2,**{name:False for name in n.FALSE},
        'diagnostic_failure_code':'PROTOCOL','groups_observed':False,'reqallents_sent':0,
        'local_phase':5,'terminal_failure':True,'terminal_db_phase':9,'terminal_map_phase':3}
class Controls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='coh-native-status-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source.cohgtx'
    def child(self,raw):
        path=self.root/('stdout-'+str(len(list(self.root.iterdir()))));stream=path.open('xb');path.chmod(0o600)
        child=subprocess.Popen([sys.executable,'-c','import os;os.write(1,'+repr(raw)+')'],
            stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.DEVNULL,start_new_session=True)
        self.addCleanup(lambda:child.wait(timeout=5) if child.poll() is not None else (child.kill(),child.wait(timeout=5)))
        self.addCleanup(stream.close);children=[child];handles=[stream]
        owner=n.latch(child,path,stream,children,handles);child.wait(timeout=5);stream.close()
        return child,owner,children,path
    def collect(self,raw,initial=True):
        child,owner,children,path=self.child(raw)
        result,private=n.collect(child,owner,children,self.source,initial,n.d.ROOT)
        return result,private,(child,owner,children,path)
    def test_exact_schema_and_header_enumerations(self):
        self.assertEqual(len(n.KEYS),18);self.assertEqual(set(n.verify_enums(n.d.ROOT)),set(n.ENUM_SOURCE_PATHS))
        parsed=n.parse(json.dumps(status()).encode());self.assertEqual(parsed['stdout_state'],'VALID')
        self.assertEqual(parsed['diagnostic_failure_code'],'PROTOCOL');self.assertEqual(parsed['terminal_map_phase'],3)
        self.assertFalse(parsed['native_groups_result_passed']);self.assertEqual(parsed['coh_status'],1)
        for typename,(name,members) in n.ENUMS.items():
            self.assertEqual(len(members)-1,{'CohStatus':7,'CohLocalPhase':10,'CohDbSessionPhase':12,'CohMapPhase':10}[typename])
        for name in n.ENUM_SOURCE_PATHS:
            target=self.root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((n.d.ROOT/name).read_bytes())
        self.assertEqual(n.verify_enums(self.root),n.verify_enums(n.d.ROOT))
        target=self.root/n.ENUMS['CohMapPhase'][0];target.write_bytes(target.read_bytes().replace(b'COH_MAP_FAILED',b'COH_MAP_OTHER'))
        with self.assertRaises(n.d.Refused):n.verify_enums(self.root)
    def test_every_field_strict_and_unknown_or_omitted_input_refused(self):
        original=status()
        for name in original:
            changed=copy.deepcopy(original);del changed[name]
            with self.subTest(omitted=name),self.assertRaises(n.d.Refused):n.parse(json.dumps(changed).encode())
        for name,value in original.items():
            if type(value) is bool:changed=copy.deepcopy(original);changed[name]=int(value)
            elif type(value) is int:changed=copy.deepcopy(original);changed[name]=bool(value)
            else:continue
            with self.subTest(type=name),self.assertRaises(n.d.Refused):n.parse(json.dumps(changed).encode())
        for name in n.FALSE:
            changed=copy.deepcopy(original);changed[name]=True
            with self.assertRaises(n.d.Refused):n.parse(json.dumps(changed).encode())
        for name,value in (('diagnostic_failure_code','UNKNOWN'),('diagnostic_failure_code',CANARY),('status',8),
            ('local_phase',11),('terminal_db_phase',13),('terminal_map_phase',11),('reqallents_sent',2),
            ('opened_sockets',3),('closed_sockets',3),('schema',CANARY),('extra',CANARY)):
            changed=copy.deepcopy(original);changed[name]=value
            with self.subTest(range=name),self.assertRaises(n.d.Refused):n.parse(json.dumps(changed).encode())
        for raw in (b'',b'{' + CANARY.encode(),b'[]',b' '* (n.STDOUT_MAX+1),
            json.dumps(original).encode()[:-1]+b',"status":1}',json.dumps(original).encode()+b'\n'+CANARY.encode()):
            with self.assertRaises(n.d.Refused):n.parse(raw)
    def test_owned_closed_child_and_regular_stdout_are_hash_bound(self):
        self.source.write_bytes(b'explicit synthetic source marker');self.source.with_name('source.cohgtx.partial').write_bytes(b'partial marker')
        before=len(os.listdir('/proc/self/fd'));raw=json.dumps(status()).encode()
        result,private,(child,owner,children,path)=self.collect(raw)
        self.assertEqual(result['exit_code'],0);self.assertTrue(result['process_started']);self.assertTrue(result['stdout_validated'])
        self.assertTrue(result['source_capture_checked']);self.assertTrue(result['source_capture_present']);self.assertTrue(result['source_partial_present'])
        self.assertEqual(private['stdout_sha256'],n.d.digest(raw));self.assertEqual(private['stdout_bytes'],len(raw))
        self.assertEqual(private['owned_child_pid'],child.pid);self.assertTrue(private['stdout_bytes_unchanged'])
        self.assertFalse(private['public_upload_permitted']);self.assertEqual(len(os.listdir('/proc/self/fd')),before)
    def test_same_child_descriptor_identity_and_closed_output_required(self):
        child,owner,children,path=self.child(json.dumps(status()).encode())
        for changed,owned in ((None,children),(dict(owner,pid=child.pid+1),children),
            (dict(owner,key=(owner['key'][0],owner['key'][1]+1,owner['key'][2])),children),(owner,[]),
            (dict(owner,stream=types.SimpleNamespace(closed=False)),children)):
            result,private=n.collect(child,changed,owned,self.source,True,n.d.ROOT)
            self.assertEqual(result['stdout_state'],'REFUSED');self.assertIsNone(private)
        other=types.SimpleNamespace(pid=child.pid+1,poll=lambda:0)
        result,private=n.collect(other,owner,[other],self.source,True,n.d.ROOT)
        self.assertEqual(result['stdout_state'],'REFUSED');self.assertIsNone(private)
        with self.assertRaises(n.d.Refused):n.latch(child,path,types.SimpleNamespace(closed=True),children,[])
    def test_source_replacement_public_mode_link_and_hash_change_refused(self):
        for change in ('replace','shared','symlink','hardlink','hash'):
            child,owner,children,path=self.child(json.dumps(status()).encode())
            if change=='replace':
                other=path.with_name(path.name+'-other');other.write_bytes(path.read_bytes());other.chmod(0o600);os.replace(other,path)
            elif change=='shared':path.chmod(0o644)
            elif change=='symlink':
                other=path.with_name(path.name+'-other');path.rename(other);path.symlink_to(other)
            elif change=='hardlink':os.link(path,path.with_name(path.name+'-other'))
            calls=0;real=n.d.hash_file
            def changed_hash(*args):
                nonlocal calls
                value=real(*args)
                if Path(args[0])==path:
                    calls+=1
                    if calls==2:return value[0],'0'*64
                return value
            with mock.patch.object(n.d,'hash_file',side_effect=changed_hash) if change=='hash' else mock.patch.object(n.d,'hash_file',wraps=real):
                result,private=n.collect(child,owner,children,self.source,True,n.d.ROOT)
            with self.subTest(change=change):self.assertEqual(result['stdout_state'],'REFUSED');self.assertIsNone(private)
    def test_exit_unavailable_legacy_and_malformed_stdout_stay_fixed(self):
        for code in (0,1,2,3,-15,None,True):
            child=types.SimpleNamespace(pid=10,poll=lambda:code)
            result,private=n.collect(child,None,[child],None,False,n.d.ROOT)
            self.assertEqual(result['exit_code'],code if type(code) is int and code in (0,1,2) else 'UNEXPECTED')
            self.assertEqual(result['stdout_state'],'UNAVAILABLE');self.assertIsNone(private)
        result,private=n.collect(None,None,[],None,True,n.d.ROOT)
        self.assertFalse(result['process_started']);self.assertEqual(result['exit_code'],'UNEXPECTED');self.assertIsNone(private)
        for raw in (b'',b'{'+CANARY.encode(),b'a'*(n.STDOUT_MAX+1)):
            result,private,_=self.collect(raw)
            self.assertEqual(result['stdout_state'],'REFUSED');self.assertIsNone(private);self.assertNotIn(CANARY,json.dumps(result))
    def test_all_fixed_failure_names_and_phase_limits_preserve_false_authority(self):
        for failure in n.FAILURES:
            value=status();value['diagnostic_failure_code']=failure
            for field,maximum in (('status',7),('local_phase',10),('terminal_db_phase',12),('terminal_map_phase',10)):
                value[field]=maximum
            result=n.parse(json.dumps(value).encode());self.assertEqual(result['diagnostic_failure_code'],failure)
            for name in ('source_generation_admitted','actor_publication','ack_permitted','world_authority'):self.assertIs(result[name],False)
    def test_public_summary_allowlist_and_private_binding_canaries(self):
        result,private,_=self.collect(json.dumps(status()).encode());value=public_fixture.receipt();value['native_diagnostic']=result
        value['private_native_stdout']={**private,'raw':CANARY,'path':CANARY,'account':CANARY}
        public=summary.summarize(value);serialized=json.dumps(public)
        self.assertEqual(public['native_diagnostic'],result);self.assertNotIn(CANARY,serialized)
        for key in ('stdout_sha256','owned_child_pid','file_inode','file_device','file_uid','enum_source_sha256'):self.assertNotIn(key,serialized)
        for name in n.PUBLIC_BOOLS:
            changed=copy.deepcopy(result);changed[name]=int(changed[name])
            with self.subTest(field=name),self.assertRaises(n.d.Refused):n.public(changed)
        for name,value in (('diagnostic_failure_code',CANARY),('coh_status',True),('exit_code',True),('raw',CANARY)):
            changed=copy.deepcopy(result);changed[name]=value
            with self.subTest(field=name),self.assertRaises(n.d.Refused):n.public(changed)
        legacy=public_fixture.receipt();self.assertEqual(summary.summarize(legacy)['native_diagnostic'],n.empty())
    def test_source_presence_is_only_bounded_boolean_metadata(self):
        self.assertEqual(n.source_presence(None),(False,False,False))
        self.assertEqual(n.source_presence(self.source),(True,False,False))
        self.source.symlink_to(self.root/'missing');self.assertEqual(n.source_presence(self.source),(True,True,False))
        with mock.patch.object(Path,'lstat',side_effect=OSError(CANARY)):
            self.assertEqual(n.source_presence(self.source),(False,False,False))
    def test_latch_or_late_collection_refusal_never_changes_groups_result(self):
        child,owner,children,path=self.child(json.dumps(status()).encode())
        for changed in (None,dict(owner,pid=child.pid+1)):
            report={'passed':True,'matching_groups_transaction_captured':True,'cleanup_verified':True,
                'pair':{'passed':True},'private_native_stdout':{'stale':CANARY}}
            n.record(report,child,changed,children,self.source,True,n.d.ROOT)
            self.assertTrue(report['passed']);self.assertTrue(report['matching_groups_transaction_captured'])
            self.assertTrue(report['cleanup_verified']);self.assertEqual(report['pair'],{'passed':True})
            self.assertEqual(report['native_diagnostic']['stdout_state'],'REFUSED');self.assertNotIn('private_native_stdout',report)
        report={'passed':True,'cleanup_verified':False}
        with mock.patch.object(n,'collect',side_effect=OSError(CANARY)):
            n.record(report,child,owner,children,self.source,True,n.d.ROOT)
        self.assertTrue(report['passed']);self.assertFalse(report['cleanup_verified'])
        self.assertEqual(report['native_diagnostic']['stdout_state'],'REFUSED');self.assertNotIn(CANARY,json.dumps(report))
    def test_first_failure_producer_values_are_distinct_from_final_closed_phase(self):
        # Synthetic source-backed shape: GROUPS survives an initial COMMAND
        # refusal. Root serializes the typed first cause/status even if a later
        # cancellation changed the owner's current failure/status separately.
        value=status();value.update(passed=True,groups_observed=True,reqallents_sent=1,
            diagnostic_failure_code='COMMAND',status=2,local_phase=5,
            terminal_failure=True,terminal_db_phase=9,terminal_map_phase=5)
        parsed=n.parse(json.dumps(value).encode())
        self.assertEqual(parsed['diagnostic_failure_code'],'COMMAND');self.assertEqual(parsed['coh_status'],2)
        self.assertEqual(parsed['local_phase'],5);self.assertEqual(parsed['terminal_db_phase'],9)
        self.assertEqual(parsed['terminal_map_phase'],5);self.assertTrue(parsed['native_groups_result_passed'])
        self.assertFalse(parsed['initial_packet_observed']);self.assertTrue(parsed['terminal_failure'])
        # The enclosing deadline uses the dedicated typed timeout operation
        # before close, preserving the same actual active Map checkpoint.
        value.update(diagnostic_failure_code='TIMEOUT',status=7)
        parsed=n.parse(json.dumps(value).encode())
        self.assertEqual(parsed['diagnostic_failure_code'],'TIMEOUT');self.assertEqual(parsed['coh_status'],7)
        self.assertTrue(parsed['terminal_failure']);self.assertEqual(parsed['terminal_db_phase'],9)
        self.assertEqual(parsed['terminal_map_phase'],5);self.assertEqual(parsed['local_phase'],5)
        value.update(initial_packet_observed=True,diagnostic_failure_code='NONE',status=2,terminal_failure=False,
            terminal_db_phase=0,terminal_map_phase=0)
        parsed=n.parse(json.dumps(value).encode());self.assertFalse(parsed['terminal_failure'])
        self.assertEqual(parsed['terminal_db_phase'],0);self.assertEqual(parsed['terminal_map_phase'],0)

if __name__=='__main__':unittest.main()
