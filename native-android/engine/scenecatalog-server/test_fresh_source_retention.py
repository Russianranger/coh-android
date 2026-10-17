#!/usr/bin/env python3
"""Offline byte-copy/protocol/rollback controls; no live token is minted."""
import copy,importlib.util,json,os,subprocess,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('fresh_retention',HERE/'retain_fresh_source_snapshot.py')
retain=importlib.util.module_from_spec(spec);spec.loader.exec_module(retain)
def bodies(root):
    source=root/'verified';source.mkdir(mode=0o700)
    for index,name in enumerate(retain.PAYLOADS):(source/name).write_bytes(b'offline body '+bytes([index]))
    for name in ('owner.cohown','packet.bin','packet-metadata.bin','eligibility.bin','inspection.json'):
        (source/name).write_bytes(b'PRIVATE_CANARY_NOT_FOR_EXPORT')
    plan={name:retain.admit.identity(source/name,1024) for name in retain.PAYLOADS}
    envelope={'bytes':5000,'sha256':'a'*64}
    inspection={'envelope':envelope,'files':{name:dict(item,chunks=1) for name,item in plan.items()}}
    verification={'capture':envelope,'inputs':copy.deepcopy(plan)}
    return source,plan,inspection,verification
class Controls(unittest.TestCase):
    def test_exact_four_byte_bodies_and_commit_last_only(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);source,plan,inspection,verification=bodies(root)
            self.assertEqual(retain.payload_plan(source,inspection,verification),plan)
            output=root/'fresh-source-snapshot';observed=[]
            def before():
                observed.append(True);self.assertFalse((output/'manifest.json').exists())
                self.assertEqual(set(p.name for p in output.iterdir()),set(retain.PAYLOADS))
            manifest={'schema':'offline-copy-control','passed':False,'source_generation_admitted':False}
            self.assertEqual(retain.export_owned(source,output,plan,manifest,before),manifest)
            self.assertEqual(observed,[True])
            self.assertEqual(set(p.name for p in output.iterdir()),set(retain.PAYLOADS)|{'manifest.json'})
            for name in retain.PAYLOADS:
                self.assertEqual((output/name).read_bytes(),(source/name).read_bytes())
                self.assertEqual((output/name).stat().st_mode&0o777,0o600)
            self.assertEqual(output.stat().st_mode&0o777,0o700)
            self.assertNotIn(b'PRIVATE_CANARY',b''.join(p.read_bytes() for p in output.iterdir()))
    def test_wrong_hash_whole_envelope_and_boolean_length_refuse(self):
        with tempfile.TemporaryDirectory() as raw:
            source,plan,inspection,verification=bodies(Path(raw))
            for name in retain.PAYLOADS:
                for bad in ({'bytes':True,'sha256':plan[name]['sha256']},
                            {**plan[name],'sha256':'0'*64},
                            {**plan[name],'bytes':plan[name]['bytes']+1}):
                    changed=copy.deepcopy(verification);changed['inputs'][name]=bad
                    with self.subTest(payload=name,bad=bad),self.assertRaises((retain.Refused,retain.admit.Refused)):
                        retain.payload_plan(source,inspection,changed)
            changed=copy.deepcopy(verification);changed['capture']={'bytes':5001,'sha256':'a'*64}
            with self.assertRaises(retain.Refused):retain.payload_plan(source,inspection,changed)
    def test_fixed_destination_and_existing_tree_never_replaced(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);source,plan,_,_=bodies(root);target=root/'fresh-source-snapshot'
            target.mkdir();sentinel=target/'existing';sentinel.write_bytes(b'preserve')
            for output in (target,root/'caller-arbitrary-name'):
                with self.assertRaises(retain.Refused):retain.export_owned(source,output,plan,{},lambda:None)
            self.assertEqual(sentinel.read_bytes(),b'preserve')
            changed={**plan,'owner.cohown':{'bytes':1,'sha256':'a'*64}}
            with self.assertRaises(retain.Refused):retain.export_owned(source,root/'new',changed,{},lambda:None)
    def test_later_copy_and_before_publish_failures_remove_every_owned_file(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);source,plan,_,_=bodies(root);target=root/'fresh-source-snapshot'
            real=retain.copy_payload;seen=[]
            def copy_one(*args):
                seen.append(args[1].name)
                real(*args)
                if len(seen)==2:raise OSError('primary-copy')
            with patch.object(retain,'copy_payload',side_effect=copy_one):
                with self.assertRaisesRegex(OSError,'primary-copy'):
                    retain.export_owned(source,target,plan,{},lambda:None)
            self.assertFalse(target.exists());self.assertEqual(len(seen),2)
            def changed():raise retain.Refused('SOURCE_CHANGED')
            with self.assertRaisesRegex(retain.Refused,'SOURCE_CHANGED'):
                retain.export_owned(source,target,plan,{},changed)
            self.assertFalse(target.exists())
            with patch.object(retain.admit,'emit_public_receipt',side_effect=OSError('primary-manifest')):
                with self.assertRaisesRegex(OSError,'primary-manifest'):
                    retain.export_owned(source,target,plan,{},lambda:None)
            self.assertFalse(target.exists())
    def test_late_copy_flush_close_and_fsync_roll_back_preserving_primary(self):
        real_fdopen=os.fdopen
        class Stream:
            def __init__(self,stream,flush,close):self.stream=stream;self.bad_flush=flush;self.bad_close=close
            def write(self,data):return self.stream.write(data)
            def fileno(self):return self.stream.fileno()
            def flush(self):
                self.stream.flush()
                if self.bad_flush:raise OSError('primary-flush')
            def close(self):
                self.stream.close()
                if self.bad_close:raise OSError('secondary-close' if self.bad_flush else 'primary-close')
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);source,plan,_,_=bodies(root);target=root/'fresh-source-snapshot'
            for flush,close in ((True,False),(False,True),(True,True)):
                with self.subTest(flush=flush,close=close),patch.object(retain.os,'fdopen',
                    side_effect=lambda *a,**kw:Stream(real_fdopen(*a,**kw),flush,close)):
                    with self.assertRaisesRegex(OSError,'primary-flush' if flush else 'primary-close'):
                        retain.export_owned(source,target,plan,{},lambda:None)
                self.assertFalse(target.exists())
            with patch.object(retain.os,'fsync',side_effect=OSError('primary-fsync')):
                with self.assertRaisesRegex(OSError,'primary-fsync'):
                    retain.export_owned(source,target,plan,{},lambda:None)
            self.assertFalse(target.exists())
    def test_payload_change_during_final_callback_refuses_without_manifest(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);source,plan,_,_=bodies(root);target=root/'fresh-source-snapshot'
            def changed():(target/'catalog.cohcat').write_bytes(b'changed')
            with self.assertRaises(retain.Refused):retain.export_owned(source,target,plan,{},changed)
            self.assertFalse(target.exists())
    def test_manifest_uses_fixed_names_and_no_private_object_serialization(self):
        with tempfile.TemporaryDirectory() as raw:
            source,plan,_,_=bodies(Path(raw));canary='PRIVATE_OWNER_DBID_COOKIE_PATH_CANARY'
            source_receipt={'source_snapshot_token_sha256':'b'*64,'private_identity':canary}
            fixture={'database_dump_sha256':'c'*64,'account':canary,'path':canary}
            manifest=retain.manifest_for(source_receipt,'d'*64,fixture,'e'*64,plan,'f'*40,'a'*64)
            self.assertNotIn(canary,json.dumps(manifest));self.assertEqual(set(manifest['payloads']),set(retain.PAYLOADS))
            self.assertFalse(manifest['source_generation_admitted']);self.assertFalse(manifest['world_authority'])
            self.assertFalse(manifest['raw_private_transaction_exported'])
    def test_readmission_owns_real_child_group_and_discards_private_output(self):
        with tempfile.TemporaryDirectory() as raw:
            workspace=Path(raw);args=types.SimpleNamespace()
            for name in (*retain.PATH_ARGUMENTS,*retain.PIN_ARGUMENTS):setattr(args,name.replace('-','_'),'offline')
            real=subprocess.Popen;seen=[]
            def child(command,**kwargs):
                seen.extend(command)
                script='from pathlib import Path;Path('+repr(str(workspace/'readmitted-source-snapshot.json'))+').write_text(\'{"passed":false,"source_generation_admitted":false}\');print("PRIVATE_CHILD_CANARY")'
                return real([sys.executable,'-c',script],**kwargs)
            with patch.object(retain.subprocess,'Popen',side_effect=child):
                result=retain.readmit(args,workspace)
            self.assertEqual(result,{'passed':False,'source_generation_admitted':False})
            self.assertIn('--fixture-receipt-sha256',seen);self.assertNotIn('--dbid',seen)
            with self.assertRaises(retain.Refused):retain.scope(result)
    def test_readmission_timeout_closes_both_pipes_and_preserves_primary(self):
        with tempfile.TemporaryDirectory() as raw:
            workspace=Path(raw);args=types.SimpleNamespace()
            for name in (*retain.PATH_ARGUMENTS,*retain.PIN_ARGUMENTS):setattr(args,name.replace('-','_'),'offline')
            real=subprocess.Popen;children=[];before=len(list(Path('/proc/self/fd').iterdir()))
            class CloseFails:
                def __init__(self,stream):self.stream=stream
                def close(self):self.stream.close();raise OSError('secondary-pipe-close')
            def child(command,**kwargs):
                p=real([sys.executable,'-c','import time;time.sleep(30)'],**kwargs);children.append(p)
                p.stdout=CloseFails(p.stdout)
                p.communicate=lambda **kw:(_ for _ in ()).throw(subprocess.TimeoutExpired('offline-primary',900))
                return p
            with patch.object(retain.subprocess,'Popen',side_effect=child):
                with self.assertRaises(subprocess.TimeoutExpired):retain.readmit(args,workspace)
            self.assertEqual(len(children),1);p=children[0]
            self.assertIsNotNone(p.poll());self.assertTrue(retain.admit.capture.base.process_group_absent(p))
            self.assertTrue(p.stdout.stream.closed);self.assertTrue(p.stderr.closed)
            self.assertEqual(len(list(Path('/proc/self/fd').iterdir())),before)
            with patch.object(retain.subprocess,'Popen',side_effect=OSError('primary-popen')):
                with self.assertRaisesRegex(OSError,'primary-popen'):retain.readmit(args,workspace)
            self.assertEqual(len(list(Path('/proc/self/fd').iterdir())),before)
    def test_host_refusal_precedes_inputs_and_cli_never_exports_private_canary(self):
        with (patch.object(retain.admit,'hosted_revision',side_effect=retain.admit.Refused('OFFLINE')),
              patch.object(retain.admit,'pinned_json') as read):
            with self.assertRaises(retain.admit.Refused):retain.retain(types.SimpleNamespace())
            read.assert_not_called()
        with tempfile.TemporaryDirectory() as raw:
            command=[sys.executable,str(HERE/'retain_fresh_source_snapshot.py')];canary='PRIVATE_RETENTION_CANARY'
            for name in (*retain.PATH_ARGUMENTS,'source-admission','output'):command+=['--'+name,str(Path(raw)/canary)]
            for name in (*retain.PIN_ARGUMENTS,'source-admission-sha256'):command+=['--'+name,'a'*64]
            result=subprocess.run(command,capture_output=True,text=True,timeout=10,
                env={**os.environ,'RUNNER_ENVIRONMENT':'offline-control'})
            self.assertEqual(result.returncode,2);self.assertNotIn(canary,result.stdout+result.stderr)
            self.assertNotIn(raw,result.stdout+result.stderr);self.assertEqual(result.stderr,'')
            self.assertEqual(json.loads(result.stdout),{'passed':False,'failure_code':'FRESH_SOURCE_RETENTION_REFUSED',
                'source_generation_admitted':False,'world_authority':False})
if __name__=='__main__':unittest.main(verbosity=2)
