"""Adversarial evidence-reader fixtures; these do not execute native MapServer."""
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'android/guest'), str(ROOT/'tools'), str(Path(__file__).parent)]
import prepare_server_fx_catalog as producer


class ProofReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(os.environ.get('COH_FX_TEST_CLIENT_CACHES',
            '/workspace/scratch/52beb2ce66cd/runtime-asset-preflight-cache/payloads/client-caches.zip'))
        if not path.is_file() or producer.pin(path) != producer.CLIENT_CACHES:
            raise AssertionError('Actual accepted client cache ZIP required; no skips')
        with zipfile.ZipFile(path) as archive: cls.full = archive.read(producer.fx.TARGET)
        cls.names = producer.fx.inspect(cls.full)['names']
        unique = {}
        for name in cls.names: unique.setdefault(name.casefold(),name)
        cls.entries = [unique[n] for n in sorted(unique)]
        cls.native_fixture = ('COH_FX_NATIVE_IDS_V1\t19607\t19606\t4cb7d9cb\t1\n' +
            ''.join(f'{i}\t{name}\t{i}\n' for i,name in enumerate(cls.entries,1)) + 'COH_FX_NATIVE_DONE_V1\n').encode()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='fx-proof-reader-')
        self.addCleanup(self.temporary.cleanup); self.root = Path(self.temporary.name)

    def ids(self, raw):
        path = self.root/'native-ids.tsv'; path.write_bytes(raw)
        return producer.parse_native_ids(path,self.names)

    def test_formatter_fixture_requires_every_id_and_roundtrip(self):
        result = self.ids(self.native_fixture)
        self.assertEqual(result['indexed_names'],19606)
        self.assertEqual(result['native_schema_crc'],'4cb7d9cb')
        for malformed in (self.native_fixture.replace(b'4cb7d9cb',b'4cb7d9ca'),
                          self.native_fixture.replace(b'\t19606\t',b'\t19605\t',1),
                          self.native_fixture.replace(b'\t1\n',b'\t0\n',1),
                          self.native_fixture.replace(b'COH_FX_NATIVE_DONE_V1\n',b'')):
            with self.subTest(bytes=len(malformed)),self.assertRaises(ValueError): self.ids(malformed)

    def test_reordered_missing_duplicate_and_wrong_roundtrip_records_fail(self):
        lines = self.native_fixture.splitlines(keepends=True)
        mutations = [lines[:1]+lines[2:3]+lines[1:2]+lines[3:], lines[:1]+lines[2:],
                     lines[:2]+lines[1:2]+lines[3:], lines[:1]+[lines[1].rsplit(b'\t',1)[0]+b'\t2\n']+lines[2:]]
        for rows in mutations:
            with self.assertRaises(ValueError): self.ids(b''.join(rows))

    def trace(self, text, expected=None):
        path = self.root/'trace.123'; path.write_text(text)
        observer = SimpleNamespace(MAX_TRACE=1024**2,
            completed_trace_lines=lambda p:p.read_text().splitlines())
        return producer.provider_receipt([path],self.root,{'/immutable/Fx/one.fx':'data/fx/one.fx'},
            producer.fx.PROJECTED if expected is None else expected,observer)

    def fx_read(self, amount=None):
        return f'read(7<{self.root/producer.fx.TARGET}>, "bytes", 3380680) = {producer.fx.PROJECTED["bytes"] if amount is None else amount}\n'

    def test_actual_fd_cache_content_fixture_is_required_not_stat_or_open(self):
        result = self.trace(self.fx_read())
        self.assertTrue(result['private_provider_verified'])
        self.assertEqual(result['successful_fd_content_bytes'],3380680)
        for raw in ('openat(3, "data/bin/fxinfo.bin", O_RDONLY) = 7\n',
                    self.fx_read(3380679),self.fx_read().replace('data/bin/fxinfo.bin','Game/data/bin/fxinfo.bin')):
            with self.assertRaises(ValueError): self.trace(raw)

    def test_source_reads_are_detected_through_resolved_immutable_provider(self):
        with self.assertRaises(ValueError):
            self.trace(self.fx_read()+'read(8</immutable/Fx/one.fx>, "source", 4) = 4\n')
        with self.assertRaises(ValueError):
            self.trace(self.fx_read()+'mmap(NULL, 4096, PROT_READ, MAP_PRIVATE, 8</immutable/Fx/one.fx>, 0) = 0x123000\n')

    def test_cache_write_and_missing_or_failed_cache_content_are_rejected(self):
        with self.assertRaises(ValueError):
            self.trace(self.fx_read()+f'write(7<{self.root/producer.fx.TARGET}>, "x", 1) = 1\n')
        with self.assertRaises(ValueError): self.trace(self.fx_read().replace(' = 3380680',' = -1 EIO'))
        with self.assertRaises(ValueError): self.trace('')

    def test_completed_evidence_can_be_rechecked_after_runtime_retirement(self):
        self.assertFalse((self.root/producer.fx.TARGET).exists())
        self.assertTrue(self.trace(self.fx_read())['private_provider_verified'])

    def candidate_fixture(self):
        directory = self.root/'startup-native'; directory.mkdir()
        manifest = directory/'native-map-startup-build.json'; manifest.write_bytes(b'fixture build metadata')
        build = {'repository_commit':'a'*40,'files':{'MapServer.exe':{'size':42,'sha256':'e'*64}},
                 'build_input':{'retained_sources_sha256':dict(producer.fx.RETAINED_FX_SOURCES)}}
        report = {'repository_commit':'a'*40,'providers':dict.fromkeys(producer.STAGES,{}),
            'startup_native_consumer':{'format':1,
                'status':'actual_candidate_full_and_compact_private_provider_preloads_verified',
                'repository_commit':'a'*40,'previous_control_mapserver':producer.fx.MAPSERVER,
                'actual_mapserver':{'bytes':42,'sha256':'e'*64},'build_manifest':producer.pin(manifest),'build':build,
                'retained_fx_sources':dict(producer.fx.RETAINED_FX_SOURCES),
                'pair_stages':list(producer.STARTUP_STAGES),'native_preload_processes':2,
                'native_id_table_on_candidate_executed':False,'physical_timing_validated':False,
                'native_gameplay_validated':False,'animation_fastpath':dict.fromkeys(producer.STARTUP_STAGES,{})}}
        package = SimpleNamespace(BUILD=manifest.name,validate_package=mock.Mock(return_value=build))
        self.enterContext(mock.patch.object(producer,'startup_package_module',return_value=package))
        return directory,report,build,package

    def test_candidate_pair_source_and_pe_manifest_bindings_are_mandatory(self):
        directory,report,build,package = self.candidate_fixture()
        self.assertEqual(producer.validate_startup_consumer(report,directory),report['startup_native_consumer'])
        package.validate_package.assert_called_with(directory,'a'*40)
        candidate = report['startup_native_consumer']
        for key,bad in (('actual_mapserver',{'bytes':42,'sha256':'f'*64}),
                        ('build_manifest',{'bytes':1,'sha256':'f'*64}),('pair_stages',['startup-full']),
                        ('native_preload_processes',1),('native_id_table_on_candidate_executed',True)):
            before = candidate[key]; candidate[key] = bad
            with self.subTest(key=key),self.assertRaises(ValueError):producer.validate_startup_consumer(report,directory)
            candidate[key] = before
        del report['providers']['startup-compact']
        with self.assertRaises(ValueError):producer.validate_startup_consumer(report,directory)

    def test_absent_candidate_pair_or_changed_fx_source_cannot_borrow_stock_control_proof(self):
        directory,report,build,package = self.candidate_fixture()
        candidate = report.pop('startup_native_consumer')
        with self.assertRaises(ValueError):producer.validate_startup_consumer(report,directory)
        report['startup_native_consumer'] = candidate
        build['build_input']['retained_sources_sha256']['Common/fxinfo.c'] = 'f'*64
        with self.assertRaisesRegex(ValueError,'qualified FX source/parser'):
            producer.validate_startup_consumer(report,directory)

    def test_rejected_raw_candidate_pe_is_not_replaced_by_a_report_boolean(self):
        directory,report,build,package = self.candidate_fixture()
        package.validate_package.side_effect = ValueError('Native startup package raw bytes differ')
        with self.assertRaisesRegex(ValueError,'raw bytes differ'):
            producer.validate_startup_consumer(report,directory)

    def animation_line(self, **changes):
        values = dict(opened=1024,certified=1024,fallback=0,crypto_failed=0,raw_bytes=1024*596,
            hash_us=1,stock_us=0,skipped_rot_keys=1024,skipped_pos_keys=0,scanned_rot_keys=0,scanned_pos_keys=0)
        values.update(changes)
        return ('COH_ANIM_CERT_V1 schema=1 pack='+producer.ANIMATION_PIG['sha256']+' '+
            ' '.join(f'{name}={value}' for name,value in values.items())+'\n').encode()

    def animation(self, stdout, read_bytes=1024*596, path=None, writes=0):
        target = self.root/'piggs/server-animations.pigg' if path is None else path
        trace = self.root/'trace.anim'
        trace.write_text(f'read(8<{target}>, "original raw bytes", {read_bytes}) = {read_bytes}\n'+
            (f'write(8<{target}>, "x", {writes}) = {writes}\n' if writes else ''))
        observer = SimpleNamespace(MAX_TRACE=1024**2,completed_trace_lines=lambda p:p.read_text().splitlines())
        return producer.animation_fastpath_receipt(stdout,[trace],self.root,observer)

    def test_observed_certificate_fixture_requires_actual_pig_fd_provider_and_positive_keys(self):
        value = self.animation(self.animation_line())
        self.assertTrue(value['certified_animation_path_observed'])
        self.assertFalse(value['whole_inventory_loaded_claimed'])
        for stdout in (b'ordinary preload only\n',self.animation_line(certified=0,fallback=1024),
                       self.animation_line(skipped_rot_keys=0),self.animation_line(crypto_failed=1)):
            with self.subTest(stdout=stdout[:50]),self.assertRaises(ValueError):self.animation(stdout)
        with self.assertRaises(ValueError):self.animation(self.animation_line(),read_bytes=1)
        with self.assertRaises(ValueError):self.animation(self.animation_line(),path='/unrelated/server-animations.pigg')
        with self.assertRaises(ValueError):self.animation(self.animation_line(),writes=1)

    def test_certificate_counter_corruption_regression_and_unbound_pack_are_rejected(self):
        for stdout in (self.animation_line().replace(producer.ANIMATION_PIG['sha256'].encode(),b'f'*64),
                       self.animation_line()+self.animation_line(opened=512,certified=512,raw_bytes=512*596),
                       self.animation_line().replace(b'opened=1024',b'opened=1024 opened=1024'),
                       self.animation_line(certified=1023)):
            with self.assertRaises(ValueError):self.animation(stdout)


if __name__ == '__main__': unittest.main()
