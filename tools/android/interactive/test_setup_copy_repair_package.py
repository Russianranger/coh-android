"""Publication boundaries for the Java-only .24 setup repair over public .23."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

import build_setup_copy_repair_apk as package
import build_client_session_repair_apk as history
import build_client_sidebar_apk as shell_history


def fixture(folder):
    assets = {name: b'accepted-'+name.encode() for name in (
        'client-runtime.zip','hardware-renderer.zip','client-manifest.json',
        'client_interactive_diagnostic.py','character_reopen_diagnostic.py',
        'character_session_budget.py','server-caches.zip','client-visual-assets.zip')}
    native=package.builder().NATIVE_MEMBERS
    while len(assets)<76-len(native): assets['member-'+str(len(assets))]=b'accepted-runtime'
    runtime={'repository_commit':package.DONOR_COMMIT,'files':{
        name:package.pin(raw) for name,raw in assets.items()}}
    assets['runtime-manifest.json']=package.shared.encoded(runtime)
    payloads={'assets/runtime/'+name:raw for name,raw in assets.items()}
    payloads.update({name:b'accepted-native' for name in native})
    donor={'payloads':{name:package.pin(raw) for name,raw in payloads.items()},
        'retained_dex':package.pin(b'donor-dex'), 'runtime_manifest':runtime,
        'retained_android_resources':{'resources.arsc':package.pin(b'resources')},
        'server_payload_extraction_preflight':{'status':'passed','fixture':'external-server-check'}}
    apk=folder/'donor.apk'
    with zipfile.ZipFile(apk,'w') as archive:
        for name,raw in payloads.items(): archive.writestr(name,raw)
        archive.writestr('classes.dex',b'donor-dex'); archive.writestr('resources.arsc',b'resources')
        archive.writestr('AndroidManifest.xml',b'donor-AXML')
    with mock.patch.object(package.retained,'verify_server_archives',return_value=donor['server_payload_extraction_preflight']):
        received, pins, _=package.extract_retained(apk,donor,folder/'extracted')
    output=folder/'candidate.apk'; dex=b'recompiled-setup-repair-dex'
    with zipfile.ZipFile(output,'w') as archive:
        for name in pins: archive.write(folder/'extracted'/name,name)
        archive.writestr('classes.dex',dex); archive.writestr('resources.arsc',b'resources')
        archive.writestr('AndroidManifest.xml',b'version-only-AXML')
    return output,apk,donor,pins,received,package.pin(dex)


def replace_member(path,name,raw):
    target=path.with_suffix('.candidate.zip')
    with zipfile.ZipFile(path) as source,zipfile.ZipFile(target,'w') as output:
        for entry in source.infolist(): output.writestr(entry,raw if entry.filename==name else source.read(entry))
    target.replace(path)


def qualification():
    import qualify_setup_copy_repair as contract
    return {'format':1,'status':'passed','scope':package.QUALIFICATION_SCOPE,
        'repository_commit':'a'*40,'runtime_repository_commit':package.DONOR_COMMIT,
        'donor':package.donor_link(),'checks':dict.fromkeys(package.CHECKS,True),
        'actual_native_ancestry_validation':copy.deepcopy(package.ACTUAL_NATIVE_ANCESTRY_CHECKS),
        'native_build_provenance':package.native_build_provenance(),
        'publication_provenance':package.publication_provenance('a'*40),
        'java_or_dex_recompiled':True,'installed_runtime_identity_preserved':True,
        'native_client_package_reused':True,'retained_native_source_and_Win32_proof_verified':True,
        'retained_java_sources_verified':15,'authored_java_sources_verified':19,
        'baseline_payloads_verified':77,**dict.fromkeys(package.FALSE_FLAGS,False),
        'test_suites':{name:{'status':'passed','skipped':0,'tests_run':1} for name in contract.TEST_MODULES},
        'tests_run':len(contract.TEST_MODULES),'check_suites':contract.CHECK_SUITES,
        'source_files':{name:package.pin(b'source') for name in package.SOURCE_FILES},
        'postgresql_emission_fixtures':['cancelled_child_deletion_commits','delete_insert_replacement_commits','duplicate_insert_23505_rollback'],
        'postgresql_levelup_fixtures':sorted(package.retained.levelup_postgresql_fixtures())}


class SetupCopyPublicationTests(unittest.TestCase):
    def test_private_shell_builder_preserves_original_18_and_23_contracts(self):
        self.assertIsNot(package._base,shell_history)
        self.assertEqual((shell_history.VERSION_NAME,shell_history.VERSION_CODE),('0.13.18',33))
        self.assertEqual((history.VERSION_NAME,history.VERSION_CODE),('0.13.23',38))
        self.assertEqual((package.VERSION_NAME,package.VERSION_CODE),('0.13.24',39))
        self.assertEqual(len(package.JAVA_CHANGES),4)
        self.assertEqual(package.JAVA_ADDITIONS,frozenset())
        self.assertEqual(package.REPLACED_PAYLOADS,frozenset())
        self.assertIn('runtime_refresh_required',package.FALSE_FLAGS)
        self.assertIn('runtime_manifest_changed',package.FALSE_FLAGS)
        self.assertIn('native_client_recompiled',package.FALSE_FLAGS)

    def test_all77_runtime_payloads_and_manifest_generation_remain_byte_exact(self):
        with tempfile.TemporaryDirectory() as temporary:
            values=fixture(Path(temporary)); candidate,donor_apk,donor,payloads,runtime,dex=values
            self.assertEqual(len(payloads),77); self.assertEqual(payloads,donor['payloads'])
            with mock.patch.object(package.retained,'verify_apk_server_archives',return_value=donor['server_payload_extraction_preflight']):
                self.assertEqual(package.verify_derivative(candidate,donor,payloads,dex),runtime)
            with zipfile.ZipFile(candidate) as new,zipfile.ZipFile(donor_apk) as old:
                for name in payloads: self.assertEqual(new.read(name),old.read(name),name)
                self.assertNotEqual(new.read('classes.dex'),old.read('classes.dex'))

    def test_guest_Game_GPU_manifest_or_asset_mutation_cannot_hide_under_new_pin(self):
        for name in ('client-runtime.zip','hardware-renderer.zip','runtime-manifest.json',
                'client-manifest.json','client_interactive_diagnostic.py','character_session_budget.py',
                'server-caches.zip','client-visual-assets.zip'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as temporary:
                candidate,_,donor,payloads,_,dex=fixture(Path(temporary))
                member='assets/runtime/'+name; replace_member(candidate,member,b'foreign')
                payloads[member]=package.pin(b'foreign')
                with self.assertRaisesRegex(ValueError,'retained runtime payloads'):
                    package.verify_derivative(candidate,donor,payloads,dex)

    def test_unchanged_dex_changed_resources_or_foreign_inventory_are_rejected(self):
        for variant in ('same-dex','resources','foreign','duplicate'):
            with self.subTest(variant=variant),tempfile.TemporaryDirectory() as temporary:
                candidate,_,donor,payloads,_,dex=fixture(Path(temporary))
                if variant=='same-dex': replace_member(candidate,'classes.dex',b'donor-dex'); dex=donor['retained_dex']
                elif variant=='resources': replace_member(candidate,'resources.arsc',b'foreign')
                elif variant=='foreign':
                    with zipfile.ZipFile(candidate,'a') as archive: archive.writestr('foreign',b'foreign')
                else:
                    with zipfile.ZipFile(candidate,'a') as archive,self.assertWarns(UserWarning): archive.writestr('classes.dex',b'foreign')
                with self.assertRaises(ValueError): package.verify_derivative(candidate,donor,payloads,dex)

    def test_exact_four_java_changes_retain15_and_reject_extra_missing_or_unchanged_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary); names=sorted(package.JAVA_CHANGES)+['retained/File'+str(i)+'.java' for i in range(15)]
            for name in names:
                path=folder/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(b'accepted')
            source_manifest=folder/'AndroidManifest.xml'; source_manifest.write_bytes(b'manifest')
            donor={'java_sources':{name:package.pin(b'accepted') for name in names},'preserved_sources':{},'payloads':{},
                'source_manifest':package.pin(b'manifest'),'qualification':{'source_files':{}}}
            expected=folder/'android/interactive/src/main/AndroidManifest.xml'; expected.parent.mkdir(parents=True,exist_ok=True)
            expected.write_bytes(b'manifest')
            for name in package.JAVA_CHANGES: (folder/name).write_bytes(b'reviewed')
            sources=[folder/name for name in names]
            with mock.patch.object(package,'ROOT',folder),mock.patch.object(package._base,'ROOT',folder),mock.patch.object(package.retained.retained,'java_sources',return_value=sources):
                _,pins,changed=package.current_java_sources(donor,folder/'generated')
                self.assertEqual(len(pins),19); self.assertEqual(set(changed),package.JAVA_CHANGES)
                retained=folder/'retained/File0.java'; retained.write_bytes(b'foreign')
                with self.assertRaisesRegex(ValueError,'Java changes'): package.current_java_sources(donor,folder/'generated')
                retained.write_bytes(b'accepted')
                changed_source=folder/next(iter(package.JAVA_CHANGES)); changed_source.write_bytes(b'accepted')
                with self.assertRaisesRegex(ValueError,'Java changes'): package.current_java_sources(donor,folder/'generated')
                changed_source.write_bytes(b'reviewed')
                with mock.patch.object(package.retained.retained,'java_sources',return_value=sources[:-1]),self.assertRaisesRegex(ValueError,'inventory'):
                    package.current_java_sources(donor,folder/'generated')

    def test_authenticate_external_donor_artifact_before_trusting_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/package.DONOR_EVIDENCE_ARCHIVE
            with zipfile.ZipFile(path,'w') as archive:
                for name in package.DONOR_EVIDENCE_NAMES: archive.writestr(name,b'fixture')
            with self.assertRaises(ValueError): package.donor_evidence_members(path)
            with mock.patch.object(package,'DONOR_EVIDENCE',package.pin(path.read_bytes())):
                self.assertEqual(set(package.donor_evidence_members(path)),package.DONOR_EVIDENCE_NAMES)
                with zipfile.ZipFile(path,'a') as archive: archive.writestr('../foreign',b'foreign')
                with self.assertRaises(ValueError): package.donor_evidence_members(path)

    def test_all107_retained_guards_three_new_suites_and_fresh_sorted_receipt_required(self):
        import qualify_setup_copy_repair as contract
        import qualify_client_session_repair as previous
        contract.validate_suite_inventory()
        self.assertEqual(contract.TEST_MODULES[:107],previous.TEST_MODULES)
        self.assertEqual(len(contract.TEST_MODULES),110)
        receipt=qualification()
        # Exercise the real reader as the separate packaging job receives it.
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'qualification.json'; path.write_text(json.dumps(receipt,sort_keys=True)+'\n')
            received=package.read_json(path)
            with mock.patch.object(package,'builder'):
                package.validate_qualification(received,'a'*40)
                for variant in ('skip','missing-suite','PG','native-recompile','runtime-refresh','wrong-runtime','old-native'):
                    bad=copy.deepcopy(received)
                    if variant=='skip': next(iter(bad['test_suites'].values()))['skipped']=1
                    elif variant=='missing-suite': bad['test_suites'].pop(next(iter(bad['test_suites'])))
                    elif variant=='PG': bad['postgresql_levelup_fixtures']=[]
                    elif variant=='native-recompile': bad['native_client_recompiled']=True
                    elif variant=='runtime-refresh': bad['runtime_refresh_required']=True
                    elif variant=='wrong-runtime': bad['runtime_repository_commit']='b'*40
                    else: bad['native_build_provenance']['repository_commit']='b'*40
                    with self.subTest(variant=variant),self.assertRaises(ValueError): package.validate_qualification(bad,'a'*40)

    def test_workflow_has_no_native_rebuild_and_audits_actual_public_Java_Dex_APK(self):
        import yaml
        text=(package.ROOT/package.WORKFLOW).read_text(); workflow=yaml.safe_load(text)
        self.assertEqual(set(workflow['jobs']),{'changes','client','qualify','apk','public-audit'})
        self.assertFalse(workflow['concurrency']['cancel-in-progress'])
        for forbidden in ('cmake --build','vcvars32.bat','--target Game','gpu-runtime/build.py',
                'Build native Game', 'public .21', 'published .21', 'retaining the exact accepted .21 DEX'):
            self.assertNotIn(forbidden,text)
        self.assertIn('COH_REQUIRE_STARTUP_BUNDLE_PG',text)
        self.assertIn('COH_REQUIRE_LEVELUP_UI_REPAIR_PG',text)
        for job in workflow['jobs'].values():
            for step in job['steps']:
                if step.get('uses','').startswith('actions/checkout@'):
                    self.assertEqual(step['with']['fetch-depth'],2)
        public_steps=workflow['jobs']['public-audit']['steps']
        self.assertTrue(any('download-public' in step.get('run','') for step in public_steps))
        self.assertTrue(any(' audit' in step.get('run','') for step in public_steps))
        self.assertIn('com.android.tools.r8.D8',Path(package.__file__).read_text())

    def test_existing_release_guard_requires_complete_24_inventory(self):
        from test_client_session_repair_package import release as previous_release
        value=previous_release()
        value['tag_name']=package.RELEASE_TAG
        names=(package.APK_NAME,package.APK_NAME+'.sha256',package.NOTES_NAME)
        prefix='https://github.com/'+package.REPOSITORY+'/releases/download/'+package.RELEASE_TAG+'/'
        for asset,name in zip(value['assets'],names):
            asset.update(name=name,browser_download_url=prefix+name)
        package.validate_existing_release(value)
        for variant in ('missing','duplicate','draft','unfinished','foreign-url'):
            wrong=copy.deepcopy(value)
            if variant=='missing': wrong['assets'].pop()
            elif variant=='duplicate': wrong['assets'][1]=copy.deepcopy(wrong['assets'][0])
            elif variant=='draft': wrong['draft']=True
            elif variant=='unfinished': wrong['assets'][0]['state']='new'
            else: wrong['assets'][0]['browser_download_url']='https://example.org/foreign.apk'
            with self.subTest(variant=variant),self.assertRaises(ValueError):
                package.validate_existing_release(wrong)


if __name__=='__main__': unittest.main()
