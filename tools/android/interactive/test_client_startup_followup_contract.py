"""Typed fixtures for the new Game wrapper and preservation of current trees."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import package_client_startup_followup_native as native
import test_client_loading_contract as old

contract, guest, index, textures = old.contract, old.guest, old.index, old.textures


def followup_manifest(package, record):
    manifest = copy.deepcopy(package['client_loading']['manifest'])
    build = native.expected_receipt()
    checks = {'format':1,'status':'passed','platform':'windows','architecture':'Win32','configuration':'OptDebug',
        'compiler_options':native.COMPILER_OPTIONS,'build_input':copy.deepcopy(build),
        'harness_sha256':'a'*64,'equivalence_verified':True,'opt_in_and_fallback_verified':True,
        'exact_scope_verified':True,'freshness_failure_branches_verified':True,
        'metadata_lookup_reduction_verified':True,'ordinary_source_mutation_detection_verified':True,
        'physical_startup_savings_validated':False,'individual_fallback_queries':4539,'candidate_tree_requests':1}
    manifest.pop('decoder_source_sha256')
    manifest.update(role=native.ROLE, repository_commit='e'*40, build_input=copy.deepcopy(build),
        files={'CityOfHeroes.exe':copy.deepcopy(record)}, preload_source_sha256=copy.deepcopy(build['patched_sha256']),
        base_client_executable=copy.deepcopy(package['files']['CityOfHeroes.exe']), windows_qualification=checks)
    return manifest


class ClientStartupFollowupContractTests(unittest.TestCase):
    read_archive = old.ClientLoadingContractTests.read_archive
    write_archive = old.ClientLoadingContractTests.write_archive
    prepare = old.ClientLoadingContractTests.prepare
    preserved = old.ClientLoadingContractTests.preserved
    loading_derivative = old.ClientLoadingContractTests.loading_derivative
    upgraded_index = old.ClientLoadingContractTests.upgraded_index

    def setUp(self):
        old.ClientLoadingContractTests.setUp(self)
        self.donor = self.loading_derivative()
        self.runtime, self.donor_report = self.prepare()
        self.donor_game = copy.deepcopy(self.donor['files']['CityOfHeroes.exe'])

    def derivative(self):
        contents, package = self.read_archive()
        raw = old.fixtures.pe_bytes()+b'client-followup-Game-metadata-preload'
        record = dict(self.donor_game, size=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        manifest = followup_manifest(package, record)
        package['client_startup_followup'] = {
            'manifest':manifest,'manifest_sha256':contract.canonical_sha(manifest),
            'base_client_loading_manifest_sha256':package['client_loading']['manifest_sha256'],
            'base_client_executable':copy.deepcopy(self.donor_game)}
        contents['CityOfHeroes.exe'] = raw;package['files']['CityOfHeroes.exe'] = record
        self.write_archive(contents, package)
        return package

    def test_current_upgrade_preserves_import_cache_supplement_and_server_links(self):
        before = self.preserved();expected = self.derivative()
        with patch.object(guest.os,'scandir',side_effect=AssertionError('Cold input tree recreated')):
            runtime,report=self.prepare()
        self.assertEqual(runtime,self.runtime);self.assertEqual(before,self.preserved())
        self.assertTrue(report['reused']);self.assertTrue(report['native_executable_upgraded'])
        self.assertTrue(report['generated_cache_bytes_preserved'])
        proof=report['native_texture_index_migration']
        self.assertEqual(proof['policy'],'verified_client_startup_followup_layer_v1')
        self.assertEqual(proof['previous_executable_sha256'],self.donor_game['sha256'])
        self.assertEqual(proof['previous_client_identity']['content_identity_sha256'],self.donor_report['content_identity_sha256'])
        self.assertEqual(proof['layer_manifest_sha256'],expected['client_startup_followup']['manifest_sha256'])
        self.assertEqual(self.server_leaf.resolve(strict=True),self.supplement)
        self.assertEqual(self.prepare()[1]['native_texture_index_migration'],proof)

    def test_header_index_rebind_preserves_header_payload(self):
        previous,_=index.prepare(self.runtime,self.identity,self.donor_game['sha256'],textures.Context({'client_worktree':self.donor_report}))
        raw=(self.runtime/index.PACK).read_bytes();expected=self.derivative();_,report=self.prepare()
        with patch.object(index,'make_pack',side_effect=AssertionError('Headers unexpectedly rebuilt')):
            after,_=self.upgraded_index(report,expected['files']['CityOfHeroes.exe'])
        rebound=(self.runtime/index.PACK).read_bytes()
        self.assertTrue(after['reused']);self.assertTrue(after['native_layer_identity_migrated'])
        self.assertEqual(raw[64:],rebound[64:])
        self.assertNotEqual(previous['identity'],after['identity'])

    def test_wrapper_validates_current_donor_and_original_history(self):
        expected=self.derivative()
        self.assertEqual(contract.client_contract(expected),expected['files']['CityOfHeroes.exe'])
        self.assertEqual(expected['client_loading'],self.donor['client_loading'])
        self.assertEqual(expected['startup_bundle_client'],self.donor['startup_bundle_client'])
        self.assertEqual(expected['native_responsiveness'],self.donor['native_responsiveness'])

    def test_guard_rejects_invented_preload_freshness_or_loader_scope(self):
        original=self.derivative()
        for name in ('env','tree','body','crc','freshness','encoding','source','base','harness','platform','physical','target','fallback','same_game'):
            changed=copy.deepcopy(original);wrapper=changed['client_startup_followup'];manifest=wrapper['manifest'];build=manifest['build_input']
            if name=='env':build['dependency_preload']['environment_variable']='FOREIGN'
            if name=='tree':build['dependency_preload']['requests'][0]['requested_tree']='data'
            if name=='body':build['dependency_preload']['full_asset_bytes_preloaded']=True
            if name=='crc':build['dependency_preload']['crc_validation_preserved']=False
            if name=='freshness':build['source_freshness_changed']=True
            if name=='encoding':build['cache_encoding_changed']=True
            if name=='source':build['source_sha256']={}
            if name=='base':wrapper['base_client_loading_manifest_sha256']='f'*64
            if name=='harness':manifest['windows_qualification']['freshness_failure_branches_verified']=False
            if name=='platform':manifest['windows_qualification']['platform']='linux'
            if name=='physical':manifest['windows_qualification']['physical_startup_savings_validated']=True
            if name=='target':build['build_targets']=['Game','MapServer']
            if name=='fallback':build['dependency_preload']['native_fallback_preserved']=False
            if name=='same_game':manifest['files']['CityOfHeroes.exe']=copy.deepcopy(self.donor_game)
            wrapper['manifest_sha256']=contract.canonical_sha(manifest)
            with self.subTest(name=name),self.assertRaises(ValueError):contract.client_contract(changed)


if __name__=='__main__':unittest.main()
