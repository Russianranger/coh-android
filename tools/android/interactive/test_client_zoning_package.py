"""Adversarial boundaries for the .26 Java/guest-only zoning publication."""
import argparse
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest import mock
import zipfile

import build_client_zoning_apk as package


def payloads():
    result = {'assets/runtime/member-%02d.zip'%index:package.pin(str(index).encode())
        for index in range(77-len(package.REPLACED_PAYLOADS))}
    result.update({name:package.pin(b'accepted') for name in package.REPLACED_PAYLOADS})
    return result


def release():
    prefix = 'https://github.com/'+package.REPOSITORY+'/releases/download/'+package.RELEASE_TAG+'/'
    return {'id':10,'tag_name':package.RELEASE_TAG,'draft':False,'prerelease':True,
        'published_at':'2026-10-10T00:00:00Z','assets':[
            {'name':name,'state':'uploaded','size':97 if name.endswith('.sha256') else 100,
             'digest':'sha256:'+'b'*64,'browser_download_url':prefix+name}
            for name in (package.APK_NAME,package.APK_NAME+'.sha256',package.NOTES_NAME)]}


class ZoningPublication(unittest.TestCase):
    def test_exact_published_donor_and_original_native_artifact_pins(self):
        evidence = json.loads((package.ROOT/'docs/android-evidence/render-queue-0.13.25-publication.json').read_text())
        published = next(value for value in evidence['release']['assets'] if value['name'] == package.DONOR_APK_NAME)
        self.assertEqual(package.DONOR_APK,{name:published[name] for name in ('bytes','sha256')})
        self.assertEqual(package.DONOR_BUILD,{name:evidence['packaging_receipt'][name] for name in ('bytes','sha256')})
        self.assertEqual(package.DONOR_COMMIT,evidence['repository_commit'])
        self.assertEqual(package.DONOR_RUN_ID,evidence['owner']['id'])
        artifact = next(value for value in evidence['actions_artifact_zip_metadata'] if value['id'] == package.DONOR_EVIDENCE_ID)
        self.assertEqual(package.DONOR_EVIDENCE,{'bytes':artifact['zip_bytes'],'sha256':artifact['zip_sha256']})
        original = next(value for value in evidence['original_native_actions_artifact_zip_metadata'] if value['id'] == package.NATIVE_ARTIFACT_ID)
        self.assertEqual(package.NATIVE_ARTIFACT,{'bytes':original['zip_bytes'],'sha256':original['zip_sha256']})
        self.assertEqual(package.NATIVE_COMMIT,evidence['native_build_provenance']['repository_commit'])
        self.assertEqual(package.NATIVE_RUN_ID,evidence['native_build_provenance']['run_id'])
        self.assertEqual(package.NATIVE_MANIFEST,evidence['native_build_provenance']['native_manifest'])
        self.assertEqual(package.DONOR_GAME,evidence['native_build_provenance']['game'])

    def test_payload_boundary_rejects_native_assets_gpu_fidelity_and_unreviewed_changes(self):
        donor = {'payloads':payloads()}; candidate = copy.deepcopy(donor['payloads'])
        for name in package.REPLACED_PAYLOADS|package.ADDED_PAYLOADS: candidate[name] = package.pin(b'new')
        package.payload_boundaries(candidate,donor)
        self.assertEqual(len(package.REPLACED_PAYLOADS),6)
        self.assertEqual(package.ADDED_PAYLOADS,{'assets/runtime/character_zoning.py'})
        for name in ('client-runtime.zip','dbserver-runtime.zip','mapserver-runtime.zip','hardware-renderer.zip',
                'server-caches.zip','client_gpu_profile.py','native_responsiveness_contract.py','texture_header_index.py'):
            self.assertNotIn('assets/runtime/'+name,package.REPLACED_PAYLOADS)
        mutations = [(name,package.pin(b'foreign')) for name in candidate if name not in package.REPLACED_PAYLOADS|package.ADDED_PAYLOADS]
        mutations += [(name,donor['payloads'][name]) for name in package.REPLACED_PAYLOADS]
        mutations += [('assets/runtime/foreign.py',package.pin(b'foreign'))]
        for name,value in mutations:
            wrong = copy.deepcopy(candidate); wrong[name] = value
            with self.subTest(name=name),self.assertRaises(ValueError): package.payload_boundaries(wrong,donor)
        for name in candidate:
            wrong = copy.deepcopy(candidate); wrong.pop(name)
            with self.subTest(missing=name),self.assertRaises(ValueError): package.payload_boundaries(wrong,donor)

    def test_original_evidence_pin_precedes_trust_in_receipt_members(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/package.DONOR_EVIDENCE_ARCHIVE
            with zipfile.ZipFile(path,'w') as archive:
                for name in package.DONOR_EVIDENCE_NAMES: archive.writestr(name,b'proof')
            with self.assertRaises(ValueError): package.donor_evidence_members(path)
            with mock.patch.object(package,'DONOR_EVIDENCE',package.pin(path.read_bytes())):
                self.assertEqual(set(package.donor_evidence_members(path)),package.DONOR_EVIDENCE_NAMES)

    def test_authenticated_evidence_rejects_duplicate_foreign_empty_and_traversal_members(self):
        with tempfile.TemporaryDirectory() as temporary:
            for variant in ('duplicate','foreign','empty','traversal'):
                path = Path(temporary)/(variant+'.zip')
                with zipfile.ZipFile(path,'w') as archive:
                    for name in package.DONOR_EVIDENCE_NAMES: archive.writestr(name,b'' if variant == 'empty' else b'proof')
                    if variant == 'duplicate':
                        with self.assertWarns(UserWarning): archive.writestr(package.DONOR_REPORT_NAME,b'duplicate')
                    elif variant == 'foreign': archive.writestr('foreign.json',b'proof')
                    elif variant == 'traversal': archive.writestr('../escape',b'proof')
                with self.subTest(variant=variant),mock.patch.object(package,'DONOR_EVIDENCE',package.pin(path.read_bytes())),self.assertRaises(ValueError):
                    package.donor_evidence_members(path)

    def test_manifests_preserve_native_producer_history_and_only_extend_helpers(self):
        donor = {'_client_verification':{'files':{name:package.pin(b'old') for name in package.HELPERS}},
            'runtime_manifest':{'repository_commit':package.DONOR_COMMIT,'scope':'accepted',
                'files':{name:package.pin(b'old') for name in package.HELPERS|{'client-manifest.json','client-runtime.zip'}},
                'client_render_queue':{'original_owner':package.NATIVE_RUN_ID},'graphics':{'retained':True}},
            'native_build_provenance':{'repository_commit':package.NATIVE_COMMIT}}
        original = copy.deepcopy(donor); updates = {name:package.pin(name.encode()) for name in package.HELPERS|package.ADDED_HELPERS}
        client,runtime = package.verification_manifests(donor,updates,'a'*40)
        self.assertEqual(donor,original)
        self.assertEqual(runtime['files']['client-runtime.zip'],donor['runtime_manifest']['files']['client-runtime.zip'])
        self.assertEqual(runtime['client_render_queue'],donor['runtime_manifest']['client_render_queue'])
        self.assertEqual(runtime['graphics'],donor['runtime_manifest']['graphics'])
        self.assertEqual(runtime['files']['client-manifest.json'],package.pin(package.shared.encoded(client)))
        self.assertTrue(runtime['character_zoning_enabled'])
        self.assertEqual(runtime['client_zoning']['map_container_ids'],[1,101])
        self.assertFalse(runtime['client_zoning']['native_Game_changed_from_public_0_13_25'])
        self.assertFalse(runtime['client_zoning']['physical_zoning_validated'])
        for wrong in ({},dict(updates,foreign=package.pin(b'foreign'))):
            with self.assertRaises(ValueError): package.verification_manifests(donor,wrong,'a'*40)

    def test_source_delta_exemptions_do_not_cover_native_build_or_graphics_recipe(self):
        for name in package.previous.native_producer().SOURCE_FILES:
            self.assertNotIn(name,package.REVIEWED_DONOR_SOURCE_CHANGES)
        self.assertNotIn('android/guest/client_gpu_profile.py',package.REVIEWED_DONOR_SOURCE_CHANGES)
        self.assertNotIn('android/guest/native_responsiveness_contract.py',package.REVIEWED_DONOR_SOURCE_CHANGES)
        self.assertEqual(package.JAVA_ADDITIONS,{package.ZONING_JAVA_ROOT+'ClientZoning.java'})
        self.assertNotIn(package.JAVA_ROOT+'ClientInput.java',package.JAVA_CHANGES)

    def test_actual_candidate_zip_cannot_hide_changed_graphics_or_relabel_native_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); guest = root/'android/guest'; guest.mkdir(parents=True)
            donor_files = {name:b'accepted-'+name.encode() for name in payloads()}
            donor_files['assets/runtime/client-runtime.zip'] = donor_files.pop(next(name for name in donor_files if 'member-' in name))
            donor_files['assets/runtime/hardware-renderer.zip'] = donor_files.pop(next(name for name in donor_files if 'member-' in name))
            for name in package.builder().NATIVE_MEMBERS:
                donor_files[name] = donor_files.pop(next(name for name in donor_files if 'member-' in name))
            donor = {'payloads':{name:package.pin(raw) for name,raw in donor_files.items()},
                'retained_dex':package.pin(b'old-dex'),'retained_android_resources':{'resources.arsc':package.pin(b'resources')},
                'server_payload_extraction_preflight':{'scope':'separately verified'},
                '_client_verification':{'files':{name:package.pin(b'old') for name in package.HELPERS}},
                'runtime_manifest':{'repository_commit':package.DONOR_COMMIT,
                    'files':{name:package.pin(b'old') for name in package.HELPERS|{'client-manifest.json'}},
                    'client_render_queue':{'source':package.NATIVE_COMMIT,'owner':package.NATIVE_RUN_ID}},
                'native_build_provenance':{'source':package.NATIVE_COMMIT}}
            candidate = dict(donor_files)
            for name in package.HELPERS|package.ADDED_HELPERS:
                raw = ('# current '+name).encode(); (guest/name).write_bytes(raw); candidate['assets/runtime/'+name] = raw
            updates = {name:package.pin((guest/name).read_bytes()) for name in package.HELPERS|package.ADDED_HELPERS}
            client,runtime = package.verification_manifests(donor,updates,'a'*40)
            candidate.update({'assets/runtime/client-manifest.json':package.shared.encoded(client),
                'assets/runtime/runtime-manifest.json':package.shared.encoded(runtime)})
            dex = package.pin(b'new-dex')
            def check(files):
                apk = root/'candidate.apk'
                with zipfile.ZipFile(apk,'w') as archive:
                    for name,raw in files.items(): archive.writestr(name,raw)
                    archive.writestr('classes.dex',b'new-dex'); archive.writestr('resources.arsc',b'resources')
                    archive.writestr('AndroidManifest.xml',b'sdk-verified-separately')
                return package.verify_derivative(apk,donor,{name:package.pin(raw) for name,raw in files.items()},dex,'a'*40)
            with mock.patch.object(package,'ROOT',root),mock.patch.object(package.retained,'verify_apk_server_archives',return_value=donor['server_payload_extraction_preflight']):
                self.assertEqual(check(candidate),runtime)
                for name in ('assets/runtime/client-runtime.zip','assets/runtime/hardware-renderer.zip'):
                    wrong = dict(candidate); wrong[name] = b'foreign native'
                    with self.subTest(name=name),self.assertRaises(ValueError): check(wrong)
                for key,value in (('character_zoning_enabled',False),('repository_commit','b'*40),
                        ('client_render_queue',{'source':'b'*40,'owner':1})):
                    wrong = dict(candidate); changed = dict(runtime); changed[key] = value
                    wrong['assets/runtime/runtime-manifest.json'] = package.shared.encoded(changed)
                    with self.subTest(key=key),self.assertRaises(ValueError): check(wrong)
                wrong = dict(candidate); wrong['assets/runtime/character_zoning.py'] = b'# unqualified source'
                with self.assertRaises(ValueError): check(wrong)

    def test_private_version_and_release_delegate_leave_old_producers_frozen(self):
        import build_client_render_queue_apk as donor
        import build_setup_copy_repair_apk as repair
        import build_client_sidebar_apk as shell
        before = (donor.VERSION_NAME,donor.VERSION_CODE,repair.VERSION_NAME,repair.VERSION_CODE,shell.VERSION_NAME,shell.VERSION_CODE)
        current = package.builder(repaired=True)
        self.assertEqual((current.VERSION_NAME,current.VERSION_CODE),('0.13.26',41))
        self.assertEqual((donor.VERSION_NAME,donor.VERSION_CODE,repair.VERSION_NAME,repair.VERSION_CODE,shell.VERSION_NAME,shell.VERSION_CODE),before)
        self.assertEqual(before,('0.13.25',40,'0.13.24',39,'0.13.18',33))
        self.assertNotEqual(package._publication.RELEASE_TAG,donor.RELEASE_TAG)
        self.assertIn('native_client_recompiled',package.FALSE_FLAGS)
        self.assertIn('physical_zoning_validated',package.FALSE_FLAGS)
        self.assertIn('java_or_dex_recompiled',package.TRUE_FLAGS)

    def test_typed_json_contract_never_accepts_boolean_or_float_as_identity_integer(self):
        value = package.zoning_contract()
        reordered = json.loads(json.dumps(value,sort_keys=True))
        self.assertTrue(package.typed_equal(value,reordered))
        for wrong in (True,1.0):
            changed = copy.deepcopy(value); changed['base_map_id'] = wrong
            self.assertFalse(package.typed_equal(value,changed))

    def test_all117_old_suites_plus_current_native_transfer_guards_are_required(self):
        import qualify_client_zoning as qualification
        qualification.validate_suite_inventory()
        self.assertEqual(qualification.TEST_MODULES[:117],qualification.previous.TEST_MODULES)
        self.assertEqual(len(qualification.TEST_MODULES),122)
        self.assertIn('test_prepare_resume_client_source',qualification.NEW_TEST_MODULES)
        self.assertIn('test_character_transfer',qualification.NEW_TEST_MODULES)
        self.assertEqual(set(qualification.CHECK_SUITES),set(package.CHECKS))

    def test_workflow_never_rebuilds_native_and_preserves_separate_public_download_SDK_audit(self):
        import yaml
        text = (package.ROOT/package.WORKFLOW).read_text(); workflow = yaml.safe_load(text)
        self.assertEqual(set(workflow['jobs']),{'changes','qualify','apk','public-audit'})
        self.assertFalse(workflow['concurrency']['cancel-in-progress'])
        for forbidden in ('cmake --build','vcvars32.bat','--target Game','--target MapServer','--target DbServer',
                'gpu-runtime/build.py','image: postgres','published .23','public .24'):
            self.assertNotIn(forbidden,text)
        self.assertIn('postgresql-16',text)
        for flag in ('COH_REQUIRE_STARTUP_BUNDLE_PG','COH_REQUIRE_LEVELUP_UI_REPAIR_PG'): self.assertIn(flag,text)
        for name in ('qualify','apk','public-audit'):
            steps = workflow['jobs'][name]['steps']
            self.assertTrue(any('download-retained-native' in step.get('run','') for step in steps))
            self.assertTrue(any('download-donor-evidence' in step.get('run','') for step in steps))
        for job in workflow['jobs'].values():
            for step in job['steps']:
                if step.get('uses','').startswith('actions/checkout@'):
                    self.assertFalse(step['with']['persist-credentials'])
                    self.assertEqual(step['with']['fetch-depth'],2)
        public = workflow['jobs']['public-audit']['steps']
        self.assertTrue(any('download-public' in step.get('run','') for step in public))
        self.assertTrue(any(' audit' in step.get('run','') for step in public))
        steps = workflow['jobs']['apk']['steps']
        self.assertTrue(any('Fresh-process SDK' in step.get('name','') for step in steps))
        signing = [step for step in steps if step.get('with',{}).get('name') == 'coh-client-interactive-signing']
        self.assertEqual(len(signing),1); self.assertEqual(signing[0]['with']['run-id'],36731428735)

    def test_completed_release_guard_rejects_partial_replacement_or_foreign_assets(self):
        package.validate_existing_release(release())
        for variant in ('draft','missing','duplicate','foreign-url','digest','unfinished','checksum'):
            wrong = release()
            if variant == 'draft': wrong['draft'] = True
            elif variant == 'missing': wrong['assets'].pop()
            elif variant == 'duplicate': wrong['assets'][1] = copy.deepcopy(wrong['assets'][0])
            elif variant == 'foreign-url': wrong['assets'][0]['browser_download_url'] = 'https://example.org/foreign.apk'
            elif variant == 'digest': wrong['assets'][0]['digest'] = 'b'*64
            elif variant == 'unfinished': wrong['assets'][0]['state'] = 'new'
            else: wrong['assets'][1]['size'] = 96
            with self.subTest(variant=variant),self.assertRaises(ValueError): package.validate_existing_release(wrong)

    def test_actual_workflow_preserves_existing_release_and_refuses_incomplete_publication(self):
        import yaml
        workflow = yaml.safe_load((package.ROOT/package.WORKFLOW).read_text())
        step = next(value for value in workflow['jobs']['changes']['steps'] if value.get('id') == 'gate')
        code = step['run'].split("python3 - <<'PY'\n",1)[1].rsplit('\nPY',1)[0]
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)/'outputs'
            environment = {'GH_TOKEN':'fixture','GITHUB_OUTPUT':str(output)}
            cases = [(release(),'false'),(None,'true')]
            for value,expected in cases:
                request = mock.Mock(return_value=io.BytesIO(json.dumps(value).encode())) if value else mock.Mock(
                    side_effect=urllib.error.HTTPError('https://fixture',404,'absent',{},None))
                if output.exists(): output.unlink()
                with mock.patch.dict(os.environ,environment),mock.patch('urllib.request.urlopen',request),contextlib.redirect_stdout(io.StringIO()):
                    exec(compile(code,package.WORKFLOW,'exec'),{})
                self.assertEqual(output.read_text(),'required='+expected+'\n')
            incomplete = release(); incomplete['assets'].pop()
            with mock.patch.dict(os.environ,environment),mock.patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(incomplete).encode())),self.assertRaises(ValueError):
                exec(compile(code,package.WORKFLOW,'exec'),{})


if __name__ == '__main__': unittest.main()
