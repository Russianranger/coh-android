"""Execute real APK conservation and immutable publication gates for the GPU lane."""
import contextlib
import copy
import fnmatch
import io
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
import zipfile
from unittest import mock

import build_client_gpu_profile_apk as package
import test_client_renderer_attribution_package as previous

COMMIT = 'a'*40
pin, replace_member = previous.pin, previous.replace_member


@contextlib.contextmanager
def candidate(folder):
    with previous.candidate(folder) as old:
        apk, donor = old[0], copy.deepcopy(old[2])
        donor.update(payloads=copy.deepcopy(old[3]), runtime_manifest=copy.deepcopy(old[4]),
            recompiled_dex=copy.deepcopy(old[8]), native_client_renderer_attribution=copy.deepcopy(old[7]))
        with zipfile.ZipFile(apk) as archive:
            donor['_client_verification'] = json.loads(archive.read('assets/runtime/client-manifest.json'))
            with zipfile.ZipFile(io.BytesIO(archive.read('assets/runtime/client-runtime.zip'))) as native_archive:
                donor['_native_client_manifest'] = json.loads(native_archive.read('client-package.json'))
                donor['_client_members'] = package.engine.startup.startup.client_member_pins(native_archive)
        donor['runtime_manifest']['repository_commit'] = package.DONOR_COMMIT
        # Older archive fixtures inventory seven synthetic retained-*.bin
        # placeholders as client inputs. The actual pinned .19 manifest has
        # sixty entries, below the unchanged guest limit of sixty-four.
        files=donor['_client_verification']['files']
        placeholders=sorted(name for name in files if name.startswith('retained-') and name.endswith('.bin'))
        excess=max(0,len(files)-60)
        if len(placeholders)<excess:raise AssertionError('Unexpected client fixture inventory')
        for name in placeholders[:excess]:files.pop(name)
        client_raw=package.shared.encoded(donor['_client_verification'])
        donor['runtime_manifest']['files']['client-manifest.json']=pin(client_raw)
        for name,raw in (('client-manifest.json',client_raw),
                ('runtime-manifest.json',package.shared.encoded(donor['runtime_manifest']))):
            replace_member(apk,'assets/runtime/'+name,raw)
            donor['payloads']['assets/runtime/'+name]=pin(raw)
        for name in package.HELPERS|package.ADDED_HELPERS:
            (folder/'android/guest'/name).write_bytes(('reviewed-gpu-'+name).encode())
        directory=folder/'gpu-runtime';directory.mkdir()
        (directory/package.GPU_ARCHIVE).write_bytes(b'source-qualified-gpu-payload-fixture')
        gpu={'repository_commit':COMMIT,'run_url':'https://github.com/Russianranger/coh-android/actions/runs/123',
            'files':{package.GPU_ARCHIVE:pin((directory/package.GPU_ARCHIVE).read_bytes())}}
        with mock.patch.object(package,'ROOT',folder), mock.patch.object(package,'current_java_sources',return_value=([],{},[])), \
                mock.patch.object(package,'validate_retained_native',return_value=old[7]), \
                mock.patch.object(package,'validate_gpu',return_value=gpu):
            runtime,payloads,preflight=package.extract_and_repair(apk,donor,folder/'gpu-files',COMMIT,old[6],directory)
            output=folder/'gpu.apk';dex=b'recompiled-optional-gpu-selector-runtime-DEX'
            with zipfile.ZipFile(output,'w') as archive,zipfile.ZipFile(apk) as original:
                for name in payloads:archive.write(folder/'gpu-files'/name,name)
                for name in donor['retained_android_resources']:archive.writestr(name,original.read(name))
                archive.writestr('classes.dex',dex);archive.writestr('AndroidManifest.xml',b'version-only-update')
            yield output,apk,donor,payloads,runtime,preflight,old[6],directory,pin(dex),gpu


def qualification():
    q=package.module('gpu_package_qualification',package.ROOT/package.QUALIFICATION_SCRIPT)
    return {'format':1,'status':'passed','scope':package.QUALIFICATION_SCOPE,'repository_commit':COMMIT,
        'runtime_repository_commit':COMMIT,'donor':package.donor_link(),
        'checks':{name:True for name in package.CHECKS},**{name:False for name in package.FALSE_FLAGS},
        **{name:True for name in ('native_client_package_reused','retained_native_source_and_Win32_proof_verified',
            'gpu_runtime_produced_in_current_run','java_or_dex_recompiled','guest_helpers_changed',
            'runtime_manifest_changed','runtime_refresh_required','graphics_driver_changed')},
        'installed_runtime_identity_preserved':False,
        'test_suites':{name:{'status':'passed','skipped':0,'tests_run':1} for name in q.TEST_MODULES},
        'tests_run':len(q.TEST_MODULES),'check_suites':copy.deepcopy(q.CHECK_SUITES),
        'source_files':{name:pin(b'source') for name in package.SOURCE_FILES},
        'postgresql_emission_fixtures':['cancelled_child_deletion_commits','delete_insert_replacement_commits','duplicate_insert_23505_rollback'],
        'postgresql_levelup_fixtures':sorted(package.retained.levelup_postgresql_fixtures())}


class GpuProfilePackageTests(unittest.TestCase):
    def verify(self,v):
        return package.verify_derivative(v[0],v[2],v[3],v[8],COMMIT,v[6],v[7])

    def test_number_and_exact_public_donor_and_finite_payload_boundary(self):
        self.assertEqual((package.VERSION_NAME,package.VERSION_CODE),('0.13.20',35))
        self.assertEqual((package.DONOR_COMMIT,package.DONOR_RUN_ID),('a4a658be25d2b5ca1393b7d3daedd83a7d9ca1f4',37723301707))
        self.assertEqual(package.DONOR_APK,{'bytes':1557408356,'sha256':'e4c04aff16056ba2fb2560b818355ada6c3fe95d7f5c219a37d3b2945b330241'})
        self.assertEqual(package.DONOR_BUILD,{'bytes':5103904,'sha256':'c16f161383e842ebc151bc3863069b874013e2d38a243dd77e3b86a5c6071ee5'})
        self.assertEqual((len(package.JAVA_CHANGES),len(package.HELPERS),len(package.ADDED_HELPERS),
            len(package.REPLACED_PAYLOADS),len(package.ADDED_PAYLOADS)),(2,2,1,4,2))
        self.assertNotIn('assets/runtime/client-runtime.zip',package.REPLACED_PAYLOADS)

    def test_actual77_outer_payloads71_retained_all22_client_members_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary,candidate(Path(temporary)) as v:
            self.assertEqual(self.verify(v),v[4]);self.assertEqual(len(v[3]),77)
            self.assertEqual(v[5],v[2]['server_payload_extraction_preflight'])
            with zipfile.ZipFile(v[0]) as current,zipfile.ZipFile(v[1]) as donor:
                for name in set(v[2]['payloads'])-package.REPLACED_PAYLOADS:
                    self.assertEqual(current.read(name),donor.read(name),name)
                for name in v[2]['retained_android_resources']:self.assertEqual(current.read(name),donor.read(name),name)
                with zipfile.ZipFile(io.BytesIO(current.read('assets/runtime/client-runtime.zip'))) as client:
                    self.assertEqual(len(client.namelist()),22)
                    for name,expected in v[2]['_client_members'].items():self.assertEqual(pin(client.read(name)),expected,name)
            self.assertEqual(v[4]['client_gpu_profile']['default_profile'],'software')
            self.assertIs(v[4]['client_gpu_profile']['hardware_opt_in'],True)
            self.assertIs(v[4]['client_gpu_profile']['physical_hardware_renderer_validated'],False)
            for key in v[2]['runtime_manifest']:
                if key not in ('files','repository_commit','scope','client_gpu_profile'):
                    self.assertEqual(v[4][key],v[2]['runtime_manifest'][key],key)

    def test_mutated_Game_Dll_archive_server_cache_Wine_FEX_and_unreviewed_helpers_rejected(self):
        for name in ('client-runtime.zip','game-package.tar.gz','dbserver-package.tar.gz','dbserver-schema.tar.gz',
                'client-caches.zip','server-caches.zip','atlas-beacons.zip','client-visual-assets.zip',
                'native_responsiveness_contract.py','native_training_save.py','local_login_server.py','local_character_server.py'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as temporary,candidate(Path(temporary)) as v:
                member='assets/runtime/'+name;replace_member(v[0],member,b'foreign');v[3][member]=pin(b'foreign')
                with self.assertRaises(ValueError):self.verify(v)

    def test_forged_hardware_archive_authored_helper_resources_and_dex_rejected(self):
        for name in ('assets/runtime/'+package.GPU_ARCHIVE,
                *('assets/runtime/'+name for name in package.HELPERS|package.ADDED_HELPERS),
                'classes.dex','resources.arsc','unchanged_dex','duplicate','missing_addition','extra_payload'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as temporary,candidate(Path(temporary)) as v:
                if name=='unchanged_dex':
                    with zipfile.ZipFile(v[1]) as donor:raw=donor.read('classes.dex')
                    replace_member(v[0],'classes.dex',raw);v=(*v[:8],pin(raw),v[9])
                elif name=='duplicate':
                    with zipfile.ZipFile(v[0],'a') as archive,self.assertWarns(UserWarning):archive.writestr('classes.dex',b'foreign')
                elif name=='missing_addition':v[3].pop('assets/runtime/client_gpu_profile.py')
                elif name=='extra_payload':v[3]['assets/runtime/foreign.so']=pin(b'foreign')
                else:
                    replace_member(v[0],name,b'foreign')
                    if name in v[3]:v[3][name]=pin(b'foreign')
                with self.assertRaises(ValueError):self.verify(v)

    def test_two_java_seventeen_retained_exact_helper_changes_and_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary);names=sorted(package.JAVA_CHANGES)+['retained/File'+str(i)+'.java' for i in range(17)]
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

    def test_frozen_native_history_and_runtime_lock_are_not_review_exemptions(self):
        for name in ('android/runtime-lock.json','upstream/ouroboros/Game/src/graphics/gfx.c',
                'patches/client-renderer-attribution/0001-renderer-attribution-and-visible-fps.patch',
                'database/client-renderer-attribution/overlay/Game/src/cohClientRendererAttribution.h',
                'tools/android/interactive/package_client_renderer_attribution_native.py'):
            self.assertNotIn(name,package.REVIEWED_DONOR_SOURCE_CHANGES)
            with tempfile.TemporaryDirectory() as temporary:
                folder=Path(temporary);target=folder/name;target.parent.mkdir(parents=True);target.write_bytes(b'accepted')
                donor={'qualification':{'source_files':{name:pin(b'accepted')}}}
                with mock.patch.object(package,'ROOT',folder):
                    package.validate_retained_sources(donor);target.write_bytes(b'foreign')
                    with self.assertRaises(ValueError):package.validate_retained_sources(donor)

    def test_all91_retained_plus5_new_suites_seven_pg_and_truthful_gpu_claims_required(self):
        receipt=qualification()
        with mock.patch.object(package,'builder'):
            package.validate_qualification(receipt,COMMIT)
            for mutation in ('skip','suite','source','pg','native_rebuilt','runtime_refresh','identity','save_relaxed','physical_gpu','graphics_flag'):
                changed=copy.deepcopy(receipt)
                if mutation=='skip':next(iter(changed['test_suites'].values()))['skipped']=1
                elif mutation=='suite':changed['test_suites'].pop(next(iter(changed['test_suites'])))
                elif mutation=='source':changed['source_files'].pop(next(iter(package.SOURCE_FILES)))
                elif mutation=='pg':changed['postgresql_levelup_fixtures']=[]
                elif mutation=='native_rebuilt':changed['native_client_recompiled']=True
                elif mutation=='runtime_refresh':changed['runtime_refresh_required']=False
                elif mutation=='identity':changed['installed_runtime_identity_preserved']=True
                elif mutation=='save_relaxed':changed['save_acceptance_relaxed']=True
                elif mutation=='physical_gpu':changed['physical_hardware_renderer_validated']=True
                else:changed['graphics_driver_changed']=False
                with self.subTest(mutation=mutation),self.assertRaises(ValueError):package.validate_qualification(changed,COMMIT)
        q=package.module('gpu_inventory_regression',package.ROOT/package.QUALIFICATION_SCRIPT)
        self.assertEqual((len(q.RETAINED_TEST_MODULES),len(q.TEST_MODULES)),(91,96));q.validate_suite_inventory()
        with mock.patch.object(q,'TEST_MODULES',tuple(name for name in q.TEST_MODULES if name!='test_client_gpu_profile')),self.assertRaisesRegex(ValueError,'suite contract'):
            q.regressions()

    def test_workflow_reuses_native_proof_source_builds_gpu_and_audits_public_bytes(self):
        source=(package.ROOT/package.WORKFLOW).read_text()
        self.assertIn('windows-2025-vs2026',source);self.assertIn('ubuntu-24.04-arm',source)
        self.assertIn('test_coh_gpu_probe_native.py --windows-qualify',source)
        self.assertIn('package_client_gpu_runtime.py build',source)
        self.assertIn('--pe32-checks out/gpu-probe/coh-gpu-probe-native-checks.json',source)
        self.assertIn('coh-client-renderer-attribution-native',source);self.assertIn('run-id: 37723301707',source)
        for forbidden in ('--target Game','--target MapServer','--target DBServer','generate_atlas_beacons.py','prepare_client_appearance_assets.py'):
            self.assertNotIn(forbidden,source)
        self.assertLess(source.index('Fresh-process SDK source payload'),source.index('Publish only the newly qualified'))
        public=source.split('  public-audit:',1)[1]
        self.assertIn('contents: read',public);self.assertNotIn('contents: write',public)
        self.assertIn('Download actual public APK checksum and testing notes',public)
        self.assertIn('/releases/download/coh-atlas-gameplay-v0.13.20/',public)
        self.assertIn('gpu_profile_push',source)
        from classify_storage_cleanup_change import GPU_PROFILE_SOURCES
        block=source.split('    paths:\n',1)[1].split('  workflow_dispatch:',1)[0]
        patterns=[line.split('      - ',1)[1] for line in block.splitlines() if line.startswith('      - ')]
        for name in GPU_PROFILE_SOURCES:self.assertTrue(any(fnmatch.fnmatchcase(name,pattern) for pattern in patterns),name)

    def test_superseded_head_blocks_release_creation_and_publication(self):
        for scenario in ('current','stale_before_creation','stale_during_upload'):
            with self.subTest(scenario=scenario),tempfile.TemporaryDirectory() as temporary:
                folder=Path(temporary);assets=tuple(folder/name for name in (package.APK_NAME,package.APK_NAME+'.sha256',package.NOTES_NAME))
                for path in assets:path.write_bytes(b'qualified-release-fixture')
                report={'repository_commit':COMMIT,**pin(assets[0].read_bytes())}
                api=mock.Mock();state={'heads':0,'created':0,'published':0}
                def request(path,data=None,**kwargs):
                    if path.startswith('/releases/tags/') or path.startswith('/git/ref/tags/'):
                        raise urllib.error.HTTPError('https://api.github.com'+path,404,'absent',{},None)
                    if path.startswith('/git/ref/heads/'):
                        state['heads']+=1
                        stale=scenario=='stale_before_creation' or scenario=='stale_during_upload' and state['heads']>1
                        return {'ref':'refs/heads/'+package.BRANCH,'object':{'type':'commit','sha':'b'*40 if stale else COMMIT}}
                    if path=='/releases':state['created']+=1;return {'id':123,'draft':True,'tag_name':package.RELEASE_TAG}
                    if '/assets?' in path:return {'state':'uploaded','name':data.name,'size':data.stat().st_size,'digest':'sha256:'+pin(data.read_bytes())['sha256']}
                    if path=='/releases/123':state['published']+=1;return {'id':123,'draft':False,'prerelease':True,'tag_name':package.RELEASE_TAG,'html_url':'release'}
                    raise AssertionError(path)
                api.request.side_effect=request
                if scenario=='current':self.assertEqual(package.publish_release(api,report,assets,'notes'),'release')
                else:
                    with self.assertRaisesRegex(ValueError,'superseded'):package.publish_release(api,report,assets,'notes')
                self.assertEqual(state['created'],0 if scenario=='stale_before_creation' else 1)
                self.assertEqual(state['published'],1 if scenario=='current' else 0)

    def test_existing_release_is_never_overwritten(self):
        api=mock.Mock();api.request.return_value={'id':1,'tag_name':package.RELEASE_TAG}
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary);assets=tuple(folder/name for name in (package.APK_NAME,package.APK_NAME+'.sha256',package.NOTES_NAME))
            for path in assets:path.write_bytes(b'fixture')
            with self.assertRaisesRegex(ValueError,'never replaced'):
                package.publish_release(api,{'repository_commit':COMMIT,**pin(b'fixture')},assets,'notes')
            self.assertEqual(api.request.call_count,1)


if __name__=='__main__':unittest.main()
