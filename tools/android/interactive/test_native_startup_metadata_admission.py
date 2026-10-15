import copy
import unittest
import io
import json
import os
from pathlib import Path
import tempfile
import tarfile
import zipfile
from functools import lru_cache
from unittest.mock import patch
import native_startup_metadata_admission as native


@lru_cache(maxsize=1)
def actual_archive_comparison_fixture():
    """Only byte migration: the fixture does not claim execution/qualification."""
    import native_startup_component_migration as migration
    contract = migration.contract
    donor = Path(os.environ['COH_ZONE_STARTUP_TEST_DONOR_APK'])
    report = Path(os.environ['COH_ZONE_STARTUP_TEST_DONOR_REPORT'])
    originals = migration.authenticated_donor(donor)
    spec = __import__('prepare_native_metadata_qualification_fixtures').ARTIFACTS['map_producer']
    recovery = Path(os.environ['COH_METADATA_RECOVERY'])
    producer = (recovery/spec['filename']).read_bytes()
    __import__('prepare_native_metadata_qualification_fixtures').original_archive(producer,spec)
    with zipfile.ZipFile(io.BytesIO(producer)) as archive: executable = archive.read('MapServer-prefetch.exe')
    assert migration.content_pin(executable) == native.MAP_CANDIDATE
    members,_ = migration.game_members(originals['mapserver'])
    previous = contract.unique_json(members['game-package.json'])
    current = copy.deepcopy(previous['files']['MapServer.exe'])
    current['size' if 'size' in current else 'bytes'] = len(executable)
    current['sha256'] = native.MAP_CANDIDATE['sha256']
    authority = {'format':1,'kind':'mapserver','shipping_allowed':False,'runtime_activation_allowed':False,
        'native_record':current,'materials':dict.fromkeys(contract.MATERIAL_ROLES,{'scope':'unexecuted_archive_comparison_fixture'}),
        'compatibility':{}}
    with patch.dict(contract.COMPONENT_AUTHORITIES,{'mapserver':authority}):
        changed,_ = migration.migrate_archive(originals['mapserver'],'mapserver',executable,authority)
    return originals,changed,donor,json.loads(report.read_bytes()),authority


def map_tar(members):
    output=io.BytesIO()
    with tarfile.open(fileobj=output,mode='w:gz',format=tarfile.USTAR_FORMAT) as archive:
        for name,raw in members.items():
            info=tarfile.TarInfo(name);info.size=len(raw);info.mode=0o644
            archive.addfile(info,io.BytesIO(raw))
    return output.getvalue()


class NativeMetadataAdmissionTests(unittest.TestCase):
    def test_actual_committed_source_audit_is_verified_without_native_admission(self):
        inspected = native.verify_committed_source_compatibility_review()
        self.assertEqual(inspected['committed_source_review']['commit'],
            '1b8da4eb850c0e7c4f4ef0a49e43e15ac948ca2e')
        self.assertFalse(inspected['scope']['runtime_activation_allowed'])
        self.assertFalse(inspected['scope']['shipping_predecessor_execution_validated'])
        self.assertFalse(native.PROMOTIONS_IMPLEMENTED)

    def test_actual_source_audit_commit_path_blob_content_or_scope_substitution_rejected(self):
        import native_map_startup_contract as startup
        authority = startup.SOURCE_ONLY_COMPATIBILITY_REVIEW
        for key in ('commit', 'path', 'git_blob', 'content', 'scope'):
            changed = copy.deepcopy(authority)
            if key == 'content': changed['descriptor'][key]['sha256'] = '0'*64
            elif key == 'scope': changed['descriptor'][key]['runtime_activation_allowed'] = True
            elif key == 'path': changed['descriptor'][key] = 'docs/android-evidence/another.json'
            else: changed['descriptor'][key] = '0'*40
            with self.subTest(key=key), patch.object(startup, 'SOURCE_ONLY_COMPATIBILITY_REVIEW', changed), self.assertRaises(ValueError):
                native.verify_committed_source_compatibility_review()

    def test_closed_promotions_require_exact_typed_false_values(self):
        value = {'game': {'enabled': False}, 'mapserver': {'enabled': False}}
        self.assertEqual(native.validate_disabled_promotions(value), value)
        for changed in ({'game': {'enabled': 0}, 'mapserver': {'enabled': False}},
            {'game': {'enabled': True}, 'mapserver': {'enabled': False}},
            {'game': {'enabled': False}, 'mapserver': {'enabled': True}},
            {'game': {'enabled': False}, 'mapserver': {'enabled': False, 'proof': 'passed'}},
            {'game': {'enabled': False}}, None):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                native.validate_disabled_promotions(changed)

    def fixture(self):
        component = {'files': {'MapServer.exe': native.RETAINED_MAP}, 'old_producer': 32}
        dummy = {'bytes': 1, 'sha256': 'a'*64}
        receipt = {'format': 1, 'role': 'nonshipping_map_metadata_research',
            'previous_component': component,
            'previous_component_sha256': native.canonical_sha(component),
            'native_producer_relabelled': False, 'shipping_allowed': False,
            'behavioral_collision_validated': False, 'physical_timing_validated': False,
            'mapserver': native.MAP_CANDIDATE, 'build_repository_commit': native.MAP_SOURCE,
            'build_run_id': native.MAP_BUILD_RUN, 'build_artifact': native.MAP_BUILD_ARTIFACT,
            **dict.fromkeys(('build_manifest', 'native_fixture', 'paired_preload', 'native_world'), dummy)}
        return component, {'receipt': receipt, 'receipt_sha256': native.canonical_sha(receipt)}

    def test_research_structure_never_grants_runtime_or_shipping_authority(self):
        component, wrapper = self.fixture()
        result = native.inspect_map_research_wrapper(wrapper, component)
        self.assertFalse(result['runtime_admission_granted'])
        self.assertFalse(result['shipping_allowed'])
        self.assertFalse(result['behavioral_collision_validated'])

    def test_old_component_tamper_rejected_even_with_rehashed_wrapper(self):
        component, wrapper = self.fixture()
        wrapper['receipt']['previous_component']['old_producer'] = 37
        wrapper['receipt_sha256'] = native.canonical_sha(wrapper['receipt'])
        with self.assertRaises(ValueError):
            native.inspect_map_research_wrapper(wrapper, component)

    def test_native_producer_and_candidate_changes_rejected(self):
        for key, value in (('mapserver', native.RETAINED_MAP), ('build_repository_commit', 'b'*40),
            ('build_run_id', 1), ('shipping_allowed', True),
            ('behavioral_collision_validated', True), ('physical_timing_validated', True)):
            component, wrapper = self.fixture()
            wrapper['receipt'][key] = value
            wrapper['receipt_sha256'] = native.canonical_sha(wrapper['receipt'])
            with self.subTest(key=key), self.assertRaises(ValueError):
                native.inspect_map_research_wrapper(wrapper, component)

    def test_receipt_digest_and_pin_types_rejected(self):
        component, wrapper = self.fixture()
        wrapper['receipt_sha256'] = 'f'*64
        with self.assertRaises(ValueError):
            native.inspect_map_research_wrapper(wrapper, component)
        for value in ({'bytes': True, 'sha256': 'a'*64}, {'bytes': 1, 'sha256': 'A'*64},
            {'bytes': 0, 'sha256': 'a'*64}, {'bytes': 1, 'sha256': 'a'*64, 'extra': 1}):
            with self.subTest(value=value), self.assertRaises(ValueError): native.pin(value)

    def test_closed_retention_preserves_exact_native_archive_producer(self):
        component, _ = self.fixture()
        archives = {'archives': {'game-package.tar.gz': {'sha256': 'a'*64}}}
        donor = {'map_startup_component': component, 'package_preflight': {'server_archives': archives}}
        result = native.retain_native_component(donor, archives, component)
        self.assertEqual(result['original_component'], component)
        self.assertFalse(result['new_native_consumer_admitted'])
        changed = copy.deepcopy(component)
        changed['files']['MapServer.exe'] = native.MAP_CANDIDATE
        with self.assertRaises(ValueError): native.retain_native_component(donor, archives, changed)


class ConditionalMapPackagingTests(unittest.TestCase):
    def test_actual_candidate_archive_comparison_preserves_all_other_bytes_and_old_receipt(self):
        import native_startup_component_migration as migration
        originals,changed,_,_,_ = actual_archive_comparison_fixture()
        delta = native.validate_map_archive_delta(originals['mapserver'],changed)
        self.assertEqual(delta['current_consumer'],native.MAP_CANDIDATE)
        self.assertEqual(delta['previous_shipping_consumer'],native.RETAINED_MAP)
        self.assertEqual(delta['changed_members'],['MapServer.exe','game-package.json'])
        before,_=migration.game_members(originals['mapserver']);after,_=migration.game_members(changed)
        for name in delta['retained_member_pins']:self.assertEqual(before[name],after[name])
        restored,_=migration.contract.previous_package(migration.contract.unique_json(after['game-package.json']),'mapserver')
        self.assertEqual(migration.contract.encoded(restored),before['game-package.json'])
        self.assertFalse(delta['behavioral_collision_validated']);self.assertFalse(delta['physical_timing_validated'])
        self.assertFalse(native.PROMOTIONS_IMPLEMENTED)
        self.assertEqual(migration.contract.COMPONENT_AUTHORITIES,{'game':None,'mapserver':None})

    def test_extra_changed_retained_sdk_native_tamper_or_relabelled_old_receipt_refused(self):
        import native_startup_component_migration as migration
        originals,changed,_,_,_=actual_archive_comparison_fixture()
        members,_=migration.game_members(changed)
        for field in ('extra','sdk','native','old_receipt'):
            copied=dict(members)
            if field=='extra':copied['unreviewed.dll']=b'fixture'
            elif field=='sdk':
                name=next(n for n in copied if n not in ('MapServer.exe','game-package.json'));copied[name]+=b'tampered'
            elif field=='native':copied['MapServer.exe']+=b'tampered'
            else:
                receipt=json.loads(copied['game-package.json']);receipt['repository_commit']='0'*40
                copied['game-package.json']=migration.contract.encoded(receipt)
            with self.subTest(field=field),self.assertRaises(ValueError):
                native.validate_map_archive_delta(originals['mapserver'],map_tar(copied))

    def test_conditional_release_facts_do_not_claim_retention_or_fresh_compiler_for_new_Map(self):
        import build_client_zone_startup_apk as package
        with patch.object(package,'map_selected',return_value=False):old=package.release_facts()
        with patch.object(package,'map_selected',return_value=True):current=package.release_facts()
        self.assertTrue(old['all_native_member_bytes_retained']);self.assertFalse(old['native_mapserver_replaced'])
        self.assertTrue(current['native_mapserver_replaced']);self.assertFalse(current['native_mapserver_recompiled']);self.assertFalse(current['native_mapserver_recompiled_in_current_run'])
        for key in ('all_native_member_bytes_retained','retained_client_game_and_mapserver_verified',
            'retained_032_map_startup_component_verified','native_client_recompiled','native_dbserver_recompiled',
            'native_compiler_executed_in_current_APK_workflow','physical_map_startup_speedup_validated'):
            self.assertFalse(current[key],key)
        self.assertTrue(current['retained_game_and_dbserver_verified'])
        self.assertTrue(current['retained_032_map_startup_ancestry_verified'])

    def test_closed_or_absent_authorities_refuse_before_material_read_or_candidate_write(self):
        import native_startup_component_migration as migration
        with patch.object(migration,'read_regular',side_effect=AssertionError('No material read')):
            with self.assertRaisesRegex(ValueError,'disabled'):native.prepare_map_delivery({})
            with patch.object(native,'PROMOTIONS_IMPLEMENTED',True):
                with self.assertRaisesRegex(ValueError,'disabled'):native.prepare_map_delivery({})
                with patch.object(migration.contract,'ACTIVATION_IMPLEMENTED',True),self.assertRaisesRegex(ValueError,'not frozen'):
                    native.prepare_map_delivery({})
        for value in ({'game':{'enabled':True},'mapserver':{'enabled':False}},
            {'game':{'enabled':False},'mapserver':{'enabled':1}},
            {'game':{'enabled':False},'mapserver':{'enabled':True,'proof':'passed'}}):
            with self.subTest(value=value),self.assertRaises(ValueError):native.validate_native_selection(value)

    def test_conditional_archive_reconstruction_updates_only_Map_and_derived_proof_manifests(self):
        import build_client_zone_startup_apk as package
        originals,changed,donor_path,_,_=actual_archive_comparison_fixture()
        report_path=Path(os.environ['COH_ZONE_STARTUP_TEST_DONOR_REPORT'])
        donor=package.validate_donor(donor_path,report_path,check_sources=False)
        delta=native.validate_map_archive_delta(originals['mapserver'],changed)
        # The live-admission function is deliberately mocked: these immutable
        # byte comparisons are not genuine native world/cache qualification.
        proof=b'{"scope":"unexecuted_controlled_archive_comparison"}\n'
        component={'archive_delta':delta,'producer':{'scope':'unexecuted_controlled_archive_comparison'},'authority_sha256':'a'*64}
        delivery={'archives':{'assets/runtime/game-package.tar.gz':changed,
            'assets/runtime/controlled-cache-proof.json':proof},'component':component}
        with tempfile.TemporaryDirectory() as temporary:
            work=Path(temporary);native_dir=work/'native'
            launcher=package.extract_retained_launcher(donor_path,donor,native_dir)
            with patch.object(package,'map_selected',return_value=True),                patch.object(package,'current_map_delivery',return_value=delivery),                patch.object(package,'added_payloads',return_value=package.ADDED_PAYLOADS|{'assets/runtime/controlled-cache-proof.json'}):
                runtime,payloads,preflight=package.extract_and_repair(donor_path,donor,work/'candidate',package.DONOR_COMMIT,
                    native_dir,launcher,execute_preflight=False)
                package.validate_native_preflight(preflight,donor,delivery)
                self.assertEqual(runtime['client_bundle'],donor['runtime_manifest']['client_bundle'])
                self.assertEqual(runtime['client_map_startup'],donor['runtime_manifest']['client_map_startup'])
                self.assertEqual(runtime['client_zone_startup']['current_Map_component'],component)
                self.assertFalse(runtime['client_zone_startup']['all_native_member_bytes_retained'])
                self.assertEqual(payloads['assets/runtime/game-package.tar.gz'],package.pin(changed))
                self.assertEqual(payloads['assets/runtime/controlled-cache-proof.json'],package.pin(proof))
                with zipfile.ZipFile(donor_path) as old:
                    for name in donor['payloads']:
                        if name not in package.replacement_payloads(donor):
                            self.assertEqual((work/'candidate'/name).read_bytes(),old.read(name),name)
                for field in ('file_count','extracted_bytes','sha256'):
                    bad=copy.deepcopy(preflight)
                    value=bad['server_archives']['archives']['game-package.tar.gz'][field]
                    bad['server_archives']['archives']['game-package.tar.gz'][field]=value+1 if type(value) is int else '0'*64
                    with self.subTest(field=field),self.assertRaises(ValueError):package.validate_native_preflight(bad,donor,delivery)
                bad=copy.deepcopy(preflight);bad['server_archives']['archives']['dbserver-package.tar.gz']['sha256']='0'*64
                with self.assertRaises(ValueError):package.validate_native_preflight(bad,donor,delivery)
                changed_provenance=package.native_provenance(donor,delivery)
                self.assertEqual(changed_provenance['retained_036_producer_receipts'],donor['native_build_provenance'])
                self.assertEqual(changed_provenance['current_Map_producer'],component['producer'])
                self.assertFalse(changed_provenance['old_producer_relabelled'])
        self.assertFalse(native.PROMOTIONS_IMPLEMENTED)


if __name__ == '__main__': unittest.main()
