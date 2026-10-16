import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock
import stage_snapshot as stage
import capture_snapshot as capture
import admit_snapshot as admit
import delivery as d

ROOT=Path(__file__).resolve().parents[3]

class SnapshotControls(unittest.TestCase):
    def test_pair_header_and_sink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cat=root/'catalog';side=root/'side'
            cat.write_bytes(b'x');head=b'COHRTS01'+struct.pack('<18I',1,80,80,20261016,12179670,508,40225,40225,130314,33,33,7,3173822562,3649375123,0,0,0,0);side.write_bytes(head)
            sink=dict(zip(('catalog_bytes','snapshot_bytes','files','slots','definitions','children','root_slots','active_roots','external_count','defs_crc','refs_crc'),(12179670,80,508,40225,40225,130314,33,33,7,3173822562,3649375123)))
            original=d.hash_file
            with mock.patch.object(d,'hash_file',side_effect=lambda p,n:(12179670,capture.CATALOG_SHA256) if p==cat else original(p,n)):
                self.assertTrue(capture.validate_pair(cat,side,sink,20261016))
                for offset in (8,12,16,20,24,28,32,36,40,48,56,60,64,76):
                    changed=bytearray(head);changed[offset]^=1;side.write_bytes(changed)
                    with self.assertRaises(d.Refused):capture.validate_pair(cat,side,sink,20261016)
                side.write_bytes(head)
                for key in sink:
                    altered=dict(sink);altered[key]+=1
                    with self.assertRaises(d.Refused):capture.validate_pair(cat,side,altered,20261016)

    def test_sink_line(self):
        fields=('status','catalog_status','snapshot_status','catalog_bytes','snapshot_bytes','files','slots','definitions','children','root_slots','active_roots','external_count','external_children','defs_crc','refs_crc','partial_remaining')
        values=(1,0,0,12179670,1000,508,40225,40225,130314,33,33,7,0,3173822562,3649375123,0)
        raw=b'COH_RUNTIME_SNAPSHOT_V1 '+b' '.join(k.encode()+b'='+str(v).encode() for k,v in zip(fields,values))
        self.assertEqual(capture.sink_observation(raw)['external_count'],7)
        with self.assertRaises(d.Refused):capture.sink_observation(raw+b'\n'+raw)
        for before,after in ((b'status=1',b'status=0'),(b'partial_remaining=0',b'partial_remaining=1'),(b'external_count=7',b'external_count=65')):
            with self.assertRaises(d.Refused):capture.sink_observation(raw.replace(before,after,1))
        self.assertIsNone(capture.sink_observation(b'not a sink line'))

    def test_source_transform_roundtrip_and_no_network_hook(self):
        original={n:(ROOT/'upstream/ouroboros'/n).read_bytes() for n in (stage.base.GROUP,stage.base.INIT)}
        out=stage.transform(original[stage.base.GROUP],original[stage.base.INIT])
        self.assertTrue(out[stage.base.GROUP].startswith(original[stage.base.GROUP]))
        self.assertEqual(out[stage.base.INIT].count(stage.NEW),2)
        self.assertNotIn(b'worldSendUpdate',out[stage.base.INIT])
        self.assertIn(b'dbSetupMap();\n        coh_source_runtime_snapshot_startup();\n        dbReadyForPlayers();',out[stage.base.INIT])
        with self.assertRaises(ValueError):stage.transform(out[stage.base.GROUP],out[stage.base.INIT])

    def test_stage_preserves_old_sources_and_rejects_drift(self):
        prior={'schema_version':1,'build_role':'map_startup_certified_animation','build_targets':['MapServer'],'animation_certificate':{},'monorail_build_input':{},'patched_sha256':{},'overlay_sha256':{},'retained_sources_sha256':{}}
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'stage';target.mkdir()
            originals={n:(ROOT/'upstream/ouroboros'/n).read_bytes() for n in (stage.base.GROUP,stage.base.INIT)}
            for name,raw in originals.items():p=target/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
            (target/stage.PRIOR).write_text(json.dumps(prior))
            with mock.patch.object(stage.base,'validate_prior',return_value=prior),mock.patch.object(stage.base,'expected_prior',return_value=prior):
                receipt=stage.prepare(ROOT,target);self.assertEqual(stage.verify_staged(ROOT,target),receipt)
                self.assertEqual((target/stage.PRIOR).read_text(),json.dumps(prior))
                with self.assertRaises(ValueError):stage.prepare(ROOT,target)
                for name in (stage.PRODUCER,stage.SINK,stage.base.GROUP,stage.base.INIT):
                    p=target/name;raw=p.read_bytes();p.write_bytes(raw+b'/* drift */')
                    with self.assertRaises(ValueError):stage.verify_staged(ROOT,target)
                    p.write_bytes(raw)
            for name,raw in originals.items():self.assertEqual((ROOT/'upstream/ouroboros'/name).read_bytes(),raw)

    def test_immutable_identity_and_no_self_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'source.json';obj={'schema':'source','nonce':'x'};sha=capture.emit_identity(p,obj)
            self.assertEqual(sha,d.digest(p.read_bytes()));self.assertNotIn(sha,p.read_text())
            with self.assertRaises(FileExistsError):capture.emit_identity(p,obj)

    def test_new_runner_host_gate_precedes_all_mutations(self):
        with mock.patch.dict(capture.os.environ,{'RUNNER_ENVIRONMENT':'local'},clear=True):
            with self.assertRaises(d.Refused):capture.capture(None)

    def test_copied_executable_identity_admitted_before_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'candidate';target=root/'private-copy'
            source.write_bytes(b'candidate');target.write_bytes(b'old private copy')
            identity={'bytes':9,'sha256':d.digest(b'candidate')}
            capture.copy_candidate(source,target,identity);self.assertEqual(target.read_bytes(),b'candidate')
            with mock.patch.object(capture.shutil,'copyfile',side_effect=lambda src,dst:dst.write_bytes(b'changed')),mock.patch.object(capture.subprocess,'Popen') as launch:
                with self.assertRaisesRegex(d.Refused,'COPIED_EXECUTABLE_IDENTITY'):capture.copy_candidate(source,target,identity)
                launch.assert_not_called()
            self.assertEqual(source.read_bytes(),b'candidate')

    def test_partial_postgresql_initialize_log_redaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            pgroot=Path(tmp)/'pg';cluster=None
            values={'admin':'a'*48,'game':'0123456789abcdef'*3}
            self.assertEqual(capture.log_redaction_secrets(cluster,pgroot),())
            def partial_initialize():
                pgroot.mkdir();(pgroot/'credentials.json').write_text(json.dumps(values))
                (pgroot/'postgres.log').write_text("ERROR CREATE ROLE PASSWORD '"+values['game']+"';")
                raise RuntimeError('synthetic schema failure after private credentials')
            with self.assertRaises(RuntimeError):cluster=partial_initialize()
            redactions=capture.log_redaction_secrets(cluster,pgroot)
            text=capture.redacted_log_tail(pgroot/'postgres.log',redactions)
            self.assertIn('[redacted]',text);self.assertNotIn(values['game'],text)
            (pgroot/'credentials.json').unlink()
            self.assertIsNone(capture.log_redaction_secrets(cluster,pgroot))
            with self.assertRaisesRegex(d.Refused,'LOG_REDACTION_UNAVAILABLE'):
                capture.redacted_log_tail(pgroot/'postgres.log',None)
            for invalid in ({'admin':values['admin']},{'admin':values['admin'],'game':'invalid'}):
                (pgroot/'credentials.json').write_text(json.dumps(invalid))
                self.assertIsNone(capture.log_redaction_secrets(cluster,pgroot))
            (pgroot/'credentials.json').write_text(json.dumps(values))
            with mock.patch.object(capture.subprocess,'Popen') as launch:
                self.assertIsNone(capture.log_redaction_secrets(mock.Mock(secrets={'changed':True}),pgroot))
                launch.assert_not_called()

    def test_redact_before_tail_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'log';secret='0123456789abcdef'*3;tail=256*1024
            raw=b'prefix '+secret.encode()+b'x'*(tail-len(secret)//2)
            path.write_bytes(raw)
            self.assertIn(secret[len(secret)//2:].encode(),raw[-tail:])
            text=capture.redacted_log_tail(path,(secret,))
            self.assertNotIn(secret[len(secret)//2:],text)
            self.assertLessEqual(len(text.encode()),tail)

    def test_same_run_compile_admission_and_tamper_refusals(self):
        prior={'schema_version':1,'build_role':'map_startup_certified_animation','build_targets':['MapServer'],'animation_certificate':{},'monorail_build_input':{},'patched_sha256':{},'overlay_sha256':{},'retained_sources_sha256':{}}
        revision='a'*40
        original={n:(ROOT/'upstream/ouroboros'/n).read_bytes() for n in (stage.base.GROUP,stage.base.INIT)}
        output=stage.transform(original[stage.base.GROUP],original[stage.base.INIT])
        with tempfile.TemporaryDirectory() as tmp,mock.patch.object(stage.base,'expected_prior',return_value=prior):
            root=Path(tmp);compile=root/'compile';compile.mkdir()
            staged=stage.expected(ROOT,prior,original,output)
            files={'MapServer.exe':b'test-only-not-a-runtime-PE','CMakeCache.txt':b'test-only',stage.RECEIPT:json.dumps(staged).encode(),stage.PRIOR:json.dumps(prior).encode(),'map-startup-inputs.json':b'{}'}
            files.update({'source/'+n:raw for n,raw in {**output,**stage.overlays(ROOT)}.items()})
            for name,raw in files.items():p=compile/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
            receipt={'schema':'coh-runtime-snapshot-compile-v1','passed':True,'source_revision':revision,'source_git_status_porcelain':[], 'build_role':stage.ROLE,'compile_only':True,'runtime_executed':False,'source_stage_verified':True,'published_inputs_reverified':True,'artifacts':{n:{'bytes':len(raw),'sha256':d.digest(raw)} for n,raw in files.items()}}
            rpath=compile/'compile-only-receipt.json';rpath.write_text(json.dumps(receipt))
            self.assertEqual(admit.inspect(compile,ROOT,revision)[0],receipt)
            with self.assertRaises(d.Refused):admit.inspect(compile,ROOT,'b'*40)
            p=compile/'MapServer.exe';p.write_bytes(b'tamper')
            with self.assertRaises(d.Refused):admit.inspect(compile,ROOT,revision)
            p.write_bytes(files['MapServer.exe'])
            for field,value in (('passed',False),('runtime_executed',True),('source_git_status_porcelain',['dirty'])):
                changed=copy.deepcopy(receipt);changed[field]=value;rpath.write_text(json.dumps(changed))
                with self.assertRaises(d.Refused):admit.inspect(compile,ROOT,revision)
            rpath.write_text(json.dumps(receipt))
            candidate=root/'candidate';plan=admit.admit(compile,ROOT,revision,candidate)
            self.assertEqual(capture.verify_candidate(candidate,revision),plan)
            with self.assertRaises(d.Refused):admit.admit(compile,ROOT,revision,candidate)
            cpath=candidate/'MapServer.exe';cpath.write_bytes(b'tamper')
            with self.assertRaises(d.Refused):capture.verify_candidate(candidate,revision)

if __name__=='__main__':unittest.main()
