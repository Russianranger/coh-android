"""Real archive conservation, typed ancestry and immutable publication gates."""
import contextlib
import copy
import fnmatch
import functools
import io
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
import zipfile
from unittest import mock

import build_client_renderer_attribution_apk as package
import test_client_sidebar_package as previous
import test_client_renderer_attribution_contract as contracts

COMMIT = 'a'*40
pin, replace_member = previous.pin, previous.replace_member


@functools.lru_cache(maxsize=1)
def typed_native_fixture():
    fixture = contracts.RendererContractTests('test_upgrade_preserves_generated_cache_private_inputs_and_all_previous_wrappers')
    try:
        fixture.setUp()
        donor_contents, donor_package = fixture.read_archive()
        produced = fixture.derivative()
        current_contents, _ = fixture.read_archive()
        return copy.deepcopy((donor_contents, donor_package, current_contents['CityOfHeroes.exe'],
            produced['client_renderer_attribution']['manifest']))
    finally:
        fixture.doCleanups()


@contextlib.contextmanager
def candidate(folder):
    with previous.candidate(folder) as prior:
        apk = prior[0]; donor = copy.deepcopy(prior[2])
        donor.update(payloads=copy.deepcopy(prior[3]), runtime_manifest=copy.deepcopy(prior[4]))
    donor['runtime_manifest']['repository_commit'] = package.DONOR_COMMIT
    contents, manifest, game, native = copy.deepcopy(typed_native_fixture())
    contents['client-package.json'] = package.shared.encoded(manifest)
    nested = io.BytesIO()
    with zipfile.ZipFile(nested, 'w') as archive:
        for name, raw in contents.items(): archive.writestr(name, raw)
    replace_member(apk, 'assets/runtime/client-runtime.zip', nested.getvalue())
    donor['payloads']['assets/runtime/client-runtime.zip'] = pin(nested.getvalue())
    donor['_native_client_manifest'] = manifest
    with zipfile.ZipFile(io.BytesIO(nested.getvalue())) as archive:
        donor['_client_members'] = package.engine.startup.startup.client_member_pins(archive)
    donor['immutable_donor_provenance']['native_responsiveness'] = manifest['native_responsiveness']['receipt']
    donor['native_client_gameplay_performance'] = manifest['client_gameplay_performance']['manifest']
    with zipfile.ZipFile(apk) as archive:
        donor['_client_verification'] = json.loads(archive.read('assets/runtime/client-manifest.json'))
        donor['recompiled_dex'] = pin(archive.read('classes.dex'))
    for value in (donor['_client_verification'], donor['runtime_manifest']):
        value['files']['client-runtime.zip'] = donor['payloads']['assets/runtime/client-runtime.zip']
    client_raw = package.shared.encoded(donor['_client_verification'])
    donor['runtime_manifest']['files']['client-manifest.json'] = pin(client_raw)
    for name, raw in (('client-manifest.json',client_raw), ('runtime-manifest.json',package.shared.encoded(donor['runtime_manifest']))):
        replace_member(apk,'assets/runtime/'+name,raw); donor['payloads']['assets/runtime/'+name] = pin(raw)
    for name in package.HELPERS: (folder/'android/guest'/name).write_bytes(('reviewed-renderer-'+name).encode())
    directory = folder/'renderer-native'; directory.mkdir(); (directory/'CityOfHeroes.exe').write_bytes(game)
    # Genuine native compilation is separately qualified. These archive tests
    # use the real typed producer receipt and never mock the guest contract.
    with mock.patch.object(package,'ROOT',folder), mock.patch.object(package,'current_java_sources',return_value=([],{},[])), \
            mock.patch.object(package,'validate_native',return_value=native):
        runtime,payloads,preflight = package.extract_and_repair(apk,donor,folder/'renderer-files',COMMIT,directory)
        output = folder/'renderer.apk'; dex=b'recompiled-renderer-capture-report-DEX'
        with zipfile.ZipFile(output,'w') as archive,zipfile.ZipFile(apk) as original:
            for name in payloads: archive.write(folder/'renderer-files'/name,name)
            for name in donor['retained_android_resources']: archive.writestr(name,original.read(name))
            archive.writestr('classes.dex',dex); archive.writestr('AndroidManifest.xml',b'version-only-update')
        yield output,apk,donor,payloads,runtime,preflight,directory,native,pin(dex)


def qualification():
    q=package.module('renderer_package_qualification',package.ROOT/package.QUALIFICATION_SCRIPT)
    return {'format':1,'status':'passed','scope':package.QUALIFICATION_SCOPE,'repository_commit':COMMIT,
        'runtime_repository_commit':COMMIT,'donor':package.donor_link(),
        'checks':{name:True for name in package.CHECKS},**{name:False for name in package.FALSE_FLAGS},
        **{name:True for name in ('native_client_recompiled','native_client_compiled_in_current_run',
            'java_or_dex_recompiled','guest_helpers_changed','runtime_manifest_changed','runtime_refresh_required')},
        'native_client_package_reused':False,'installed_runtime_identity_preserved':False,
        'actual_native_ancestry_validation':copy.deepcopy(package.ACTUAL_NATIVE_ANCESTRY_CHECKS),
        'test_suites':{name:{'status':'passed','skipped':0,'tests_run':1} for name in q.TEST_MODULES},
        'tests_run':len(q.TEST_MODULES),'check_suites':copy.deepcopy(q.CHECK_SUITES),
        'source_files':{name:pin(b'source') for name in package.SOURCE_FILES},
        'postgresql_emission_fixtures':['cancelled_child_deletion_commits','delete_insert_replacement_commits','duplicate_insert_23505_rollback'],
        'postgresql_levelup_fixtures':sorted(package.retained.levelup_postgresql_fixtures())}


class RendererPackageTests(unittest.TestCase):
    def verify(self,values):
        return package.verify_derivative(values[0],values[2],values[3],values[8],COMMIT,values[6])

    def test_number_and_exact_public_donor(self):
        self.assertEqual((package.VERSION_NAME,package.VERSION_CODE),('0.13.19',34))
        self.assertEqual((package.DONOR_COMMIT,package.DONOR_RUN_ID),('d1e455f8d0047ac02398d17c5df1001375522f98',37637034415))
        self.assertEqual(package.DONOR_APK,{'bytes':1557379684,'sha256':'d7fb00ae5406208a2497c7b9ea9659403a422dd0698404cd968112a4ba7b8ca1'})
        self.assertEqual(package.DONOR_BUILD,{'bytes':5077901,'sha256':'4eb3708e2384303bcebfc51c5f572d7f29f82b28163ab2a5aaa26e89938bee71'})
        self.assertEqual((len(package.JAVA_CHANGES),len(package.JAVA_ADDITIONS),len(package.HELPERS),len(package.REPLACED_PAYLOADS)),(4,0,4,7))

    def test_actual75_outer_payloads68_retained20_dlls_and_new_game_dex(self):
        with tempfile.TemporaryDirectory() as temporary,candidate(Path(temporary)) as v:
            self.assertEqual(self.verify(v),v[4]);self.assertEqual(len(v[3]),75)
            self.assertEqual(v[5],v[2]['server_payload_extraction_preflight'])
            self.assertNotEqual(v[4]['repository_commit'],v[2]['runtime_manifest']['repository_commit'])
            with zipfile.ZipFile(v[0]) as current,zipfile.ZipFile(v[1]) as donor:
                for name in set(v[3])-package.REPLACED_PAYLOADS:self.assertEqual(current.read(name),donor.read(name),name)
                for name in v[2]['retained_android_resources']:self.assertEqual(current.read(name),donor.read(name),name)
                self.assertNotEqual(current.read('classes.dex'),donor.read('classes.dex'))
                with zipfile.ZipFile(io.BytesIO(current.read('assets/runtime/client-runtime.zip'))) as client:
                    self.assertEqual(len(client.namelist()),22)
                    for name,expected in v[2]['_client_members'].items():
                        if name not in ('CityOfHeroes.exe','client-package.json'):self.assertEqual(pin(client.read(name)),expected)
                    produced=json.loads(client.read('client-package.json'))
                    for key in ('native_responsiveness','startup_bundle_client','client_loading','client_startup_followup','client_scene_performance','client_gameplay_performance'):
                        self.assertEqual(produced[key],v[2]['_native_client_manifest'][key])
            for key in ('thor_performance','ui_beacon','client_startup_followup','client_scene_performance','client_gameplay_performance','startup_only_reopen','task_gate_required'):
                if key in v[2]['runtime_manifest']:self.assertEqual(v[4][key],v[2]['runtime_manifest'][key])

    def test_server_cache_visual_and_unreviewed_helper_mutations_rejected(self):
        for name in ('game-package.tar.gz','dbserver-package.tar.gz','dbserver-schema.tar.gz','server-caches.zip',
                'client-caches.zip','atlas-beacons.zip','client-visual-assets.zip','client_interactive_diagnostic.py',
                'native_training_save.py','local_login_server.py'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as temporary,candidate(Path(temporary)) as v:
                member='assets/runtime/'+name;replace_member(v[0],member,b'foreign');v[3][member]=pin(b'foreign')
                with self.assertRaises(ValueError):self.verify(v)

    def test_nested_game_dll_old_wrapper_extra_missing_duplicate_rejected(self):
        for mutation in ('game','dll','wrapper','missing','extra','duplicate'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as temporary,candidate(Path(temporary)) as v:
                with zipfile.ZipFile(v[0]) as apk,zipfile.ZipFile(io.BytesIO(apk.read('assets/runtime/client-runtime.zip'))) as client:
                    contents={entry.filename:client.read(entry) for entry in client.infolist()}
                if mutation=='game':contents['CityOfHeroes.exe']=b'foreign'
                elif mutation=='dll':contents['fixture0.dll']=b'foreign'
                elif mutation=='missing':contents.pop('fixture0.dll')
                elif mutation=='extra':contents['foreign.dll']=b'foreign'
                elif mutation=='wrapper':
                    m=json.loads(contents['client-package.json']);m['client_gameplay_performance']['manifest_sha256']='f'*64
                    contents['client-package.json']=package.shared.encoded(m)
                rewritten=io.BytesIO()
                with zipfile.ZipFile(rewritten,'w') as archive:
                    for name,raw in contents.items():archive.writestr(name,raw)
                    if mutation=='duplicate':
                        with self.assertWarns(UserWarning):archive.writestr('CityOfHeroes.exe',b'foreign')
                member='assets/runtime/client-runtime.zip';replace_member(v[0],member,rewritten.getvalue());v[3][member]=pin(rewritten.getvalue())
                with self.assertRaises(ValueError):self.verify(v)

    def test_authored_helpers_recompiled_dex_resources_and_duplicate_bound(self):
        for name in (*('assets/runtime/'+name for name in package.HELPERS),'classes.dex','resources.arsc','unchanged_dex','duplicate'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as temporary,candidate(Path(temporary)) as v:
                if name=='unchanged_dex':
                    with zipfile.ZipFile(v[1]) as donor:raw=donor.read('classes.dex')
                    replace_member(v[0],'classes.dex',raw);v=(*v[:8],pin(raw))
                elif name=='duplicate':
                    with zipfile.ZipFile(v[0],'a') as archive,self.assertWarns(UserWarning):archive.writestr('classes.dex',b'foreign')
                else:
                    replace_member(v[0],name,b'foreign')
                    if name in v[3]:v[3][name]=pin(b'foreign')
                with self.assertRaises(ValueError):self.verify(v)

    def test_java_four_changed_fifteen_retained_exact_helpers_and_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary);names=sorted(package.JAVA_CHANGES)+['retained/File'+str(i)+'.java' for i in range(15)]
            for name in names:
                target=folder/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b'accepted-java')
            manifest=folder/'android/interactive/src/main/AndroidManifest.xml';manifest.parent.mkdir(parents=True,exist_ok=True);manifest.write_bytes(b'accepted-manifest')
            for name in package.HELPERS:
                target=folder/'android/guest'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b'reviewed-helper')
            donor={'java_sources':{name:pin(b'accepted-java') for name in names},'preserved_sources':{},
                'payloads':{'assets/runtime/'+name:pin(b'old-helper') for name in package.HELPERS},
                'source_manifest':pin(b'accepted-manifest'),'qualification':{'source_files':{}}}
            for name in package.JAVA_CHANGES:(folder/name).write_bytes(b'reviewed-java')
            sources=[folder/name for name in names]
            with mock.patch.object(package,'ROOT',folder),mock.patch.object(package.retained.retained,'java_sources',return_value=sources):
                _,pins,changed=package.current_java_sources(donor,folder/'generated')
                self.assertEqual(len(pins),19);self.assertEqual(set(changed),package.JAVA_CHANGES)
                (folder/names[-1]).write_bytes(b'foreign')
                with self.assertRaisesRegex(ValueError,'Java changes'):package.current_java_sources(donor,folder/'generated')
                (folder/names[-1]).write_bytes(b'accepted-java')
                with mock.patch.object(package.retained.retained,'java_sources',return_value=sources[:-1]),self.assertRaisesRegex(ValueError,'inventory'):
                    package.current_java_sources(donor,folder/'generated')
                name=next(iter(package.HELPERS));(folder/'android/guest'/name).write_bytes(b'old-helper')
                with self.assertRaisesRegex(ValueError,'helpers must change'):package.current_java_sources(donor,folder/'generated')

    def test_frozen_upstream_is_not_exempted_by_current_source_inventory(self):
        name='upstream/ouroboros/Game/src/graphics/gfx.c'
        self.assertNotIn(name,package.REVIEWED_DONOR_SOURCE_CHANGES)
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary);target=folder/name;target.parent.mkdir(parents=True);target.write_bytes(b'accepted')
            donor={'qualification':{'source_files':{name:pin(b'accepted')}}}
            with mock.patch.object(package,'ROOT',folder):
                package.validate_retained_sources(donor);target.write_bytes(b'foreign')
                with self.assertRaises(ValueError):package.validate_retained_sources(donor)

    def test_real_ancestry_function_output_equals_exact_qualification_receipt(self):
        _,donor_package,_,native=copy.deepcopy(typed_native_fixture())
        donor={'_native_client_manifest':donor_package,'immutable_donor_provenance':{
            'native_responsiveness':donor_package['native_responsiveness']['receipt']}}
        actual=contracts.validate_actual_native_ancestry(donor,native)
        self.assertEqual(actual,package.ACTUAL_NATIVE_ANCESTRY_CHECKS)
        self.assertTrue(actual['actual_gameplay_Game_predecessor_verified'])
        receipt=qualification();receipt['actual_native_ancestry_validation']=actual
        receipt['source_files']={name:package.builder().file_pin(package.ROOT/name) for name in package.SOURCE_FILES}
        package.validate_qualification(receipt,COMMIT)
        receipt['actual_native_ancestry_validation'].pop('actual_gameplay_Game_predecessor_verified')
        with self.assertRaises(ValueError):package.validate_qualification(receipt,COMMIT)

    def test_all91_retained_new_suites_seven_pg_and_runtime_refresh_claims_required(self):
        receipt=qualification()
        with mock.patch.object(package,'builder'):
            package.validate_qualification(receipt,COMMIT)
            for mutation in ('skip','suite','source','pg','native_reused','runtime_refresh','identity','save_relaxed','ancestry'):
                changed=copy.deepcopy(receipt)
                if mutation=='skip':next(iter(changed['test_suites'].values()))['skipped']=1
                elif mutation=='suite':changed['test_suites'].pop(next(iter(changed['test_suites'])))
                elif mutation=='source':changed['source_files'].pop(next(iter(package.SOURCE_FILES)))
                elif mutation=='pg':changed['postgresql_levelup_fixtures']=[]
                elif mutation=='native_reused':changed['native_client_package_reused']=True
                elif mutation=='runtime_refresh':changed['runtime_refresh_required']=False
                elif mutation=='identity':changed['installed_runtime_identity_preserved']=True
                elif mutation=='save_relaxed':changed['save_acceptance_relaxed']=True
                else:changed['actual_native_ancestry_validation']['rejected_foreign_variants']=[]
                with self.subTest(mutation=mutation),self.assertRaises(ValueError):package.validate_qualification(changed,COMMIT)
        q=package.module('renderer_inventory_regression',package.ROOT/package.QUALIFICATION_SCRIPT)
        self.assertEqual((len(q.RETAINED_TEST_MODULES),len(q.TEST_MODULES)),(84,91));q.validate_suite_inventory()
        with mock.patch.object(q,'TEST_MODULES',tuple(name for name in q.TEST_MODULES if name!='test_client_capture_metrics')),self.assertRaisesRegex(ValueError,'suite contract'):
            q.regressions()

    def test_workflow_current_game_four_win32_proofs_fresh_public_audit_and_exact_owner(self):
        source=(package.ROOT/package.WORKFLOW).read_text()
        self.assertIn('windows-2025-vs2026',source);self.assertIn('--parallel --target Game',source)
        for forbidden in ('--target MapServer','--target DBServer','generate_atlas_beacons.py','prepare_client_appearance_assets.py'):
            self.assertNotIn(forbidden,source)
        for script in ('test_client_scene_performance_native.py','test_client_frame_timing_native.py','test_client_gameplay_performance_native.py','test_client_renderer_attribution_native.py'):
            self.assertIn(script+' --windows-qualify',source)
        self.assertIn('--gameplay-checks out/client-gameplay-checks.json --renderer-checks out/client-renderer-checks.json',source)
        self.assertIn('coh-client-sidebar-packaging-evidence',source);self.assertIn('run-id: 37637034415',source)
        self.assertIn("PYTHONHASHSEED: '73419'",source);self.assertIn("PYTHONHASHSEED: '1918'",source)
        self.assertLess(source.index('Fresh-process SDK source payload'),source.index('Publish only the newly qualified'))
        public=source.split('  public-audit:',1)[1]
        self.assertIn('contents: read',public);self.assertNotIn('contents: write',public)
        self.assertIn('Download actual public APK checksum and testing notes',public)
        self.assertIn('renderer_attribution_push',source);self.assertIn('Existing performance release differs',source)
        from classify_storage_cleanup_change import RENDERER_ATTRIBUTION_SOURCES
        block=source.split('    paths:\n',1)[1].split('  workflow_dispatch:',1)[0]
        patterns=[line.split('      - ',1)[1] for line in block.splitlines() if line.startswith('      - ')]
        for name in RENDERER_ATTRIBUTION_SOURCES:
            with self.subTest(source=name):self.assertTrue(any(fnmatch.fnmatchcase(name,pattern) for pattern in patterns))

    def test_superseded_head_blocks_release_creation_and_publication(self):
        for scenario in ('current', 'stale_before_creation', 'stale_during_upload'):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary); assets = tuple(folder/name for name in
                    (package.APK_NAME, package.APK_NAME+'.sha256', package.NOTES_NAME))
                for path in assets: path.write_bytes(b'fully-verified-release-fixture')
                report = dict(pin(assets[0].read_bytes()), repository_commit=COMMIT)
                api = mock.Mock(); heads = []

                def request(path, data=None, **kwargs):
                    if path == '/git/ref/heads/'+package.BRANCH:
                        heads.append(path)
                        stale = scenario == 'stale_before_creation' or (scenario == 'stale_during_upload' and len(heads) > 1)
                        return {'ref': 'refs/heads/'+package.BRANCH,
                            'object': {'type': 'commit', 'sha': 'b'*40 if stale else COMMIT}}
                    if path.startswith(('/releases/tags/', '/git/ref/tags/')):
                        raise urllib.error.HTTPError('https://api.github.com', 404, 'Not Found', {}, None)
                    if path == '/releases':
                        return {'id': 1, 'draft': True, 'prerelease': True, 'tag_name': package.RELEASE_TAG}
                    if path.startswith('/releases/1/assets?'):
                        record = pin(data.read_bytes())
                        return {'state': 'uploaded', 'name': data.name, 'size': record['bytes'], 'digest': 'sha256:'+record['sha256']}
                    self.assertEqual(path, '/releases/1')
                    return {'id': 1, 'draft': False, 'prerelease': True, 'tag_name': package.RELEASE_TAG,
                        'html_url': 'https://github.com/'+package.REPOSITORY+'/releases/tag/'+package.RELEASE_TAG}

                api.request.side_effect = request
                if scenario == 'current':
                    self.assertIn(package.RELEASE_TAG, package.publish_release(api, report, assets, 'qualified notes'))
                    self.assertEqual(len(heads), 2)
                else:
                    with self.assertRaisesRegex(ValueError, 'superseded'):
                        package.publish_release(api, report, assets, 'qualified notes')
                    self.assertFalse(any(call.kwargs.get('method') == 'PATCH' for call in api.request.call_args_list))
                    if scenario == 'stale_before_creation':
                        self.assertFalse(any(call.kwargs.get('method') == 'POST' for call in api.request.call_args_list))


if __name__=='__main__':unittest.main()
