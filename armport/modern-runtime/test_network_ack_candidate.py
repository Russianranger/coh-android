"""Synthetic PE admission controls; these never claim native execution."""
import copy
import hashlib
import os
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import network_ack_candidate as adapter

ROOT = Path(os.environ.get('COH_CANDIDATE_ROOT', Path.cwd() / 'candidate'))
if not ROOT.is_dir(): ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import package_reference_runtime as pe

def digest(raw): return hashlib.sha256(raw).hexdigest()

def fake_pe(imports=(), marker=True, machine=0x14c):
    raw = bytearray(2048); raw[:2] = b'MZ'; struct.pack_into('<I', raw, 60, 128)
    raw[128:132] = b'PE\0\0'; struct.pack_into('<HH', raw, 132, machine, 1)
    struct.pack_into('<H', raw, 148, 224); optional = 152
    struct.pack_into('<H', raw, optional, 0x10b)
    struct.pack_into('<I', raw, optional+28, 0x400000)
    struct.pack_into('<I', raw, optional+60, 512)
    struct.pack_into('<I', raw, optional+92, 16)
    struct.pack_into('<4I', raw, optional+224+8, 1536, 0x1000, 1536, 512)
    if imports:
        struct.pack_into('<II', raw, optional+104, 0x1000, 20*(len(imports)+1))
        cursor = 512+20*(len(imports)+1)
        for index, name in enumerate(imports):
            struct.pack_into('<I', raw, 512+20*index+12, 0x1000+cursor-512)
            text=name.encode()+b'\0'; raw[cursor:cursor+len(text)]=text; cursor+=len(text)
    if marker: raw[-len(adapter.ACK_MARKER):] = adapter.ACK_MARKER
    return bytes(raw)

class OverlayTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.root=Path(self.tmp.name)
        self.reference=self.root/'reference'; self.reference.mkdir()
        self.binaries, self.records, self.hashes = {}, {}, {}
        for name, raw in (('DbServer.exe',fake_pe(marker=False)), ('MapServer.exe',fake_pe(marker=False)+b'old'),
                          ('PhysXLoader.dll',fake_pe(marker=False))):
            path=self.reference/name; path.write_bytes(raw)
            self.binaries[name],self.hashes[name]=path,digest(raw)
            self.records[name]=dict(size=len(raw),sha256=digest(raw),**pe.pe_info(raw))
        self.package=dict(repository_commit='b'*40,postgresql_persistence_fixture=False,files=self.records)
        self.original_result=({'templates':'unchanged'},{'tables':[]},{'attributes':[]},[],self.package,self.binaries,self.hashes)
        self.original=Mock(return_value=self.original_result)
        self.archive=self.root/'candidate.zip'; self.archive.write_bytes(b'metadata-only fixture')
        self.raw=fake_pe(('KERNEL32.dll','PhysXLoader.dll'))
        self.native=SimpleNamespace(BUILD='server-metrics-build.json',pin=lambda b:dict(bytes=len(b),sha256=digest(b)),
            digest=digest,canonical=lambda x:__import__('json').dumps(x,sort_keys=True).encode())
        self.native.read_package=Mock(side_effect=lambda *a,**k:self.native_package())

    def native_package(self):
        return dict(files={'MapServer.exe':dict(bytes=len(self.raw),sha256=digest(self.raw))},build_input={'fixture':True}),{}, {
            'MapServer.exe':self.raw,self.native.BUILD:b'fixture manifest'}

    def overlay(self):
        return adapter.Overlay(self.original,self.native,pe,self.archive,'exact baseline',self.root/'selected.exe')

    def test_only_map_mapping_changes_after_original_and_exact_native_admission(self):
        before=copy.deepcopy(self.package); mapping=dict(self.binaries); hashes=dict(self.hashes)
        overlay=self.overlay(); actual=overlay('original args')
        self.original.assert_called_once_with('original args')
        self.native.read_package.assert_called_once_with(self.archive,variant=adapter.VARIANT,
            repository_commit=adapter.SOURCE,run_id=adapter.BUILD_RUN,upstream_root='exact baseline')
        self.assertIs(actual[4],self.package); self.assertEqual(self.package,before)
        self.assertEqual(self.binaries,mapping); self.assertEqual(self.hashes,hashes)
        self.assertEqual({n:p for n,p in actual[5].items() if n!='MapServer.exe'},
                         {n:p for n,p in mapping.items() if n!='MapServer.exe'})
        self.assertEqual(actual[6]['MapServer.exe'],digest(self.raw)); self.assertFalse(overlay.proof['test_guards_modified'])

    def test_failed_original_receipt_cannot_be_replaced_by_native_proof(self):
        self.original.side_effect=ValueError('original schema rejected')
        with self.assertRaisesRegex(ValueError,'original schema'):self.overlay()()
        self.native.read_package.assert_not_called(); self.assertFalse((self.root/'selected.exe').exists())

    def test_native_rejection_cannot_stage_or_authorize_candidate(self):
        self.native.read_package.side_effect=ValueError('wrong source/run/variant')
        with self.assertRaisesRegex(ValueError,'wrong source'):self.overlay()()
        self.assertFalse((self.root/'selected.exe').exists())

    def test_unknown_import_wrong_machine_and_missing_ack_marker_refused(self):
        for raw in (fake_pe(('unapproved_missing.dll',)),fake_pe(machine=0xaa64),fake_pe(marker=False)):
            self.raw=raw
            with self.subTest(sha=digest(raw)),self.assertRaises(ValueError):self.overlay()()
            self.assertFalse((self.root/'selected.exe').exists())

    def test_different_candidate_bytes_refused(self):
        build,previous,members=self.native_package(); build['files']['MapServer.exe']['sha256']='0'*64
        self.native.read_package.side_effect=None;self.native.read_package.return_value=build,previous,members
        with self.assertRaisesRegex(ValueError,'bytes or receive marker'):self.overlay()()

    def test_postrun_checks_executed_map_dbserver_and_dlls(self):
        overlay=self.overlay(); admitted=overlay(); work=self.root/'exercise'; runtime=work/'runtime';runtime.mkdir(parents=True)
        for name,path in admitted[5].items():(runtime/name).write_bytes(path.read_bytes())
        report=dict(mapserver_sha256=digest(self.raw),dbserver_sha256=self.hashes['DbServer.exe'])
        self.assertTrue(overlay.after(work,report,(),{})['exercised_binary_hashes_reverified_after_execution'])
        for name in ('MapServer.exe','DbServer.exe','PhysXLoader.dll'):
            path=runtime/name;before=path.read_bytes();path.write_bytes(before+b'changed')
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,'binary changed'):overlay.after(work,report,(),{})
            path.write_bytes(before)

    def test_postrun_original_reference_drift_refused(self):
        overlay=self.overlay();overlay();changed=list(self.original_result)
        changed[6]=dict(self.hashes,**{'DbServer.exe':'0'*64});self.original.return_value=tuple(changed)
        with self.assertRaisesRegex(ValueError,'receipt or bytes changed'):overlay.after(self.root,{},(),{})

    def test_repeated_admission_refused(self):
        overlay=self.overlay();overlay()
        with self.assertRaisesRegex(ValueError,'repeated'):overlay()

class WaitTests(unittest.TestCase):
    def record(self):
        return dict(id=adapter.BUILD_RUN,path=adapter.upstream.NATIVE_WORKFLOW,event='workflow_dispatch',
            head_sha=adapter.SOURCE,head_branch=adapter.upstream.BRANCH,status='completed',conclusion='success',
            repository={'full_name':adapter.upstream.REPOSITORY},head_repository={'full_name':adapter.upstream.REPOSITORY})

    def test_pending_then_exact_success_without_dispatch(self):
        row=self.record();row.update(status='in_progress',conclusion=None);api=Mock(side_effect=[row,self.record()]);clock=[0]
        result=adapter.wait_build(api=api,clock=lambda:clock[0],sleeper=lambda n:clock.__setitem__(0,clock[0]+n),timeout=100)
        self.assertEqual(result['id'],adapter.BUILD_RUN);self.assertEqual(clock[0],30)
        self.assertTrue(all(c.args==('/actions/runs/'+str(adapter.BUILD_RUN),) for c in api.call_args_list))

    def test_failure_other_source_and_timeout_cannot_advance(self):
        for field,value in (('head_sha','0'*40),('conclusion','failure'),('id',adapter.BUILD_RUN+1)):
            row=self.record();row[field]=value
            with self.subTest(field=field),self.assertRaises(adapter.upstream.UpstreamError):adapter.wait_build(api=lambda _:row)
        row=self.record();row.update(status='queued',conclusion=None);clock=[0]
        with self.assertRaisesRegex(ValueError,'exceeded bound'):
            adapter.wait_build(api=lambda _:row,clock=lambda:clock[0],sleeper=lambda n:clock.__setitem__(0,clock[0]+n),timeout=1)

if __name__=='__main__':unittest.main()
