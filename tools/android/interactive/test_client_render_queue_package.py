"""Adversarial Game-only .25 publication over the actual .24 Android shell."""
import argparse
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock
import zipfile

import build_client_render_queue_apk as builder


def payloads():
    result = {'assets/runtime/member-%02d.zip'%i: builder.pin(str(i).encode())
        for i in range(77-len(builder.REPLACED_PAYLOADS))}
    result.update({name:builder.pin(b'accepted') for name in builder.REPLACED_PAYLOADS})
    return result


def release():
    base = 'https://github.com/'+builder.REPOSITORY+'/releases/download/'+builder.RELEASE_TAG+'/'
    return {'id':10,'tag_name':builder.RELEASE_TAG,'draft':False,'prerelease':True,
        'published_at':'2026-10-09T00:00:00Z','assets':[
            {'name':name,'state':'uploaded','size':97 if name.endswith('.sha256') else 100,
                'digest':'sha256:'+'b'*64,'browser_download_url':base+name}
            for name in (builder.APK_NAME,builder.APK_NAME+'.sha256',builder.NOTES_NAME)]}


def replace_member(path,name,raw):
    target=path.with_suffix('.candidate.zip')
    with zipfile.ZipFile(path) as source,zipfile.ZipFile(target,'w') as output:
        for entry in source.infolist(): output.writestr(entry,raw if entry.filename==name else source.read(entry))
    target.replace(path)


def reuse_records():
    source,publication='a'*40,'b'*40
    run={'id':42,'status':'completed','conclusion':'failure','head_sha':source,
        'head_branch':builder.BRANCH,'path':builder.WORKFLOW,'event':'push',
        'repository':{'full_name':builder.REPOSITORY}}
    jobs={'total_count':2,'jobs':[{'name':'client','run_id':42,'head_sha':source,
        'status':'completed','conclusion':'success'},{'name':'qualify','conclusion':'failure'}]}
    artifacts={'total_count':1,'artifacts':[{'name':'coh-client-render-queue-native',
        'id':123,'expired':False,'size_in_bytes':12345,'digest':'sha256:'+'c'*64,
        'workflow_run':{'id':42,'head_sha':source}}]}
    comparison={'base_commit':{'sha':source},'head_commit':{'sha':publication},
        'status':'ahead','total_commits':1,'files':[{
            'filename':'tools/android/interactive/build_client_render_queue_apk.py','status':'modified'}]}
    return run,jobs,artifacts,comparison,source,publication


class RenderQueuePublication(unittest.TestCase):
    def test_exact_seven_payload_changes_retain70_gpu_server_asset_and_session_bytes(self):
        donor={'payloads':payloads()}; candidate=copy.deepcopy(donor['payloads'])
        for name in builder.REPLACED_PAYLOADS: candidate[name]=builder.pin(b'new')
        builder.payload_boundaries(candidate,donor)
        self.assertEqual(len(builder.REPLACED_PAYLOADS),7)
        self.assertEqual(builder.HELPERS,frozenset({'native_responsiveness_contract.py',
            'client_startup_diagnostic.py','client_gpu_profile.py','texture_header_index.py'}))
        for name in ('hardware-renderer.zip','client_interactive_diagnostic.py',
                'character_reopen_diagnostic.py','character_session_budget.py','server-caches.zip'):
            self.assertNotIn('assets/runtime/'+name,builder.REPLACED_PAYLOADS)
        for name in (next(n for n in candidate if n not in builder.REPLACED_PAYLOADS),'foreign'):
            wrong=copy.deepcopy(candidate); wrong[name]=builder.pin(b'foreign')
            with self.subTest(name=name),self.assertRaises(ValueError): builder.payload_boundaries(wrong,donor)
        for name in builder.REPLACED_PAYLOADS:
            wrong=copy.deepcopy(candidate);wrong[name]=donor['payloads'][name]
            with self.subTest(name=name),self.assertRaises(ValueError):builder.payload_boundaries(wrong,donor)

    def test_original_artifact_zip_pin_precedes_any_contained_report_trust(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/builder.DONOR_EVIDENCE_ARCHIVE
            with zipfile.ZipFile(path,'w') as archive:
                for name in sorted(builder.DONOR_EVIDENCE_NAMES):archive.writestr(name,b'foreign')
            with self.assertRaises(ValueError):builder.donor_evidence_members(path)
            with mock.patch.object(builder,'DONOR_EVIDENCE',builder.pin(path.read_bytes())):
                self.assertEqual(set(builder.donor_evidence_members(path)),builder.DONOR_EVIDENCE_NAMES)
                with zipfile.ZipFile(path,'a') as archive:archive.writestr('../foreign','unsafe')
                with self.assertRaises(ValueError):builder.donor_evidence_members(path)

    def test_authenticated_evidence_rejects_duplicate_foreign_and_empty_members(self):
        with tempfile.TemporaryDirectory() as temporary:
            for variant in ('foreign','duplicate','empty'):
                path=Path(temporary)/(variant+'.zip')
                with zipfile.ZipFile(path,'w') as archive:
                    for name in sorted(builder.DONOR_EVIDENCE_NAMES):archive.writestr(name,b'proof' if variant!='empty' else b'')
                    if variant=='foreign':archive.writestr('other.txt',b'foreign')
                    if variant=='duplicate':
                        with self.assertWarns(UserWarning):archive.writestr(builder.DONOR_REPORT_NAME,b'duplicate')
                with self.subTest(variant=variant),mock.patch.object(builder,'DONOR_EVIDENCE',builder.pin(path.read_bytes())),self.assertRaises(ValueError):
                    builder.donor_evidence_members(path)

    def test_external_public_024_pins_and_all110_retained_suites(self):
        import qualify_client_render_queue as qualification
        qualification.validate_suite_inventory()
        self.assertEqual(qualification.TEST_MODULES[:110],qualification.previous.TEST_MODULES)
        self.assertEqual(len(qualification.NEW_TEST_MODULES),7)
        self.assertEqual(len(qualification.TEST_MODULES),117)
        publication=json.loads((builder.ROOT/'docs/android-evidence/setup-copy-0.13.24-publication.json').read_text())
        evidence=next(value for value in publication['actions_artifact_zip_metadata'] if value['id']==builder.DONOR_EVIDENCE_ID)
        self.assertEqual(builder.DONOR_EVIDENCE,{'bytes':evidence['zip_bytes'],'sha256':evidence['zip_sha256']})
        apk=next(value for value in publication['release']['assets'] if value['name']==builder.DONOR_APK_NAME)
        self.assertEqual(builder.DONOR_APK,{name:apk[name] for name in ('bytes','sha256')})
        self.assertEqual(builder.DONOR_COMMIT,publication['repository_commit'])
        self.assertEqual(builder.DONOR_RUNTIME_COMMIT,'ac255fee7546b28a4ae06074f385d3ad73b235ad')

    def test_private_builder_does_not_mutate_024_or_018_shell_contracts(self):
        import build_setup_copy_repair_apk as donor
        import build_client_sidebar_apk as shell
        before=(donor.VERSION_NAME,donor.VERSION_CODE,shell.VERSION_NAME,shell.VERSION_CODE)
        current=builder.builder(repaired=True)
        self.assertEqual((current.VERSION_NAME,current.VERSION_CODE),('0.13.25',40))
        self.assertEqual((donor.VERSION_NAME,donor.VERSION_CODE,shell.VERSION_NAME,shell.VERSION_CODE),before)
        self.assertEqual(before,('0.13.24',39,'0.13.18',33))
        self.assertIn('java_or_dex_recompiled',builder.FALSE_FLAGS)
        self.assertIn('physical_fps_gain_validated',builder.FALSE_FLAGS)
        self.assertIn('native_client_recompiled',builder.TRUE_FLAGS)
        self.assertNotIn('native_client_compiled_in_current_publication_run',builder.TRUE_FLAGS)
        self.assertNotIn('native_client_compiled_in_current_publication_run',builder.FALSE_FLAGS)

    def test_immutable_private_native_producer_cache_preserves_historical_module_isolation(self):
        import package_client_render_queue_native as public_native
        first=builder.native_producer()
        self.assertIs(first,builder.native_producer())
        self.assertIsNot(first,public_native)
        self.assertEqual(first.expected_receipt(),public_native.expected_receipt())
        self.assertEqual(first.ROOT.resolve(),builder.ROOT.resolve())
        self.assertEqual((builder.previous.VERSION_NAME,builder.parent_history.VERSION_NAME),('0.13.24','0.13.22'))

    def test_skip_only_complete_public_release_without_replacing_partial_assets(self):
        builder.validate_existing_release(release())
        for variant in ('draft','missing','duplicate','url','digest','unfinished','checksum'):
            value=release()
            if variant=='draft':value['draft']=True
            elif variant=='missing':value['assets'].pop()
            elif variant=='duplicate':value['assets'][1]=copy.deepcopy(value['assets'][0])
            elif variant=='url':value['assets'][0]['browser_download_url']='https://example.org/foreign.apk'
            elif variant=='digest':value['assets'][0]['digest']='a'*64
            elif variant=='unfinished':value['assets'][0]['state']='new'
            else:value['assets'][1]['size']=96
            with self.subTest(variant=variant),self.assertRaises(ValueError):builder.validate_existing_release(value)

    def test_completed_Game_reuse_keeps_original_owner_after_host_only_failure(self):
        receipt=builder.validate_native_reuse_records(*reuse_records())
        self.assertEqual(receipt['original_native_run_id'],42)
        self.assertEqual(receipt['original_native_artifact_id'],123)
        self.assertFalse(receipt['native_build_repeated'])
        self.assertNotEqual(receipt['native_source_commit'],receipt['publication_source_commit'])

    def test_reuse_rejects_active_foreign_failed_incomplete_or_native_modified_owners(self):
        for variant in ('active','source','workflow','branch','job_failed','job_active','jobs_page',
                'duplicate_job','artifact_expired','artifact_duplicate','artifact_digest',
                'artifact_source','artifact_page','diverged','foreign','native','guest','rename','comparison_source'):
            records=copy.deepcopy(reuse_records());run,jobs,artifacts,comparison,_,_=records
            if variant=='active':run['status']='in_progress'
            elif variant=='source':run['head_sha']='e'*40
            elif variant=='workflow':run['path']='.github/workflows/android-client-render-pipeline.yml'
            elif variant=='branch':run['head_branch']='main'
            elif variant=='job_failed':jobs['jobs'][0]['conclusion']='failure'
            elif variant=='job_active':jobs['jobs'][0]['status']='in_progress'
            elif variant=='jobs_page':jobs['total_count']=3
            elif variant=='duplicate_job':jobs['jobs'].append(copy.deepcopy(jobs['jobs'][0]));jobs['total_count']=3
            elif variant=='artifact_expired':artifacts['artifacts'][0]['expired']=True
            elif variant=='artifact_duplicate':artifacts['artifacts'].append(copy.deepcopy(artifacts['artifacts'][0]));artifacts['total_count']=2
            elif variant=='artifact_digest':artifacts['artifacts'][0]['digest']='foreign'
            elif variant=='artifact_source':artifacts['artifacts'][0]['workflow_run']['head_sha']='e'*40
            elif variant=='artifact_page':artifacts['total_count']=2
            elif variant=='diverged':comparison['status']='diverged'
            elif variant=='foreign':comparison['files'][0]['filename']='unreviewed.py'
            elif variant=='native':comparison['files'][0]['filename']='tools/android/interactive/package_client_render_queue_native.py'
            elif variant=='guest':comparison['files'][0]['filename']='android/guest/client_gpu_profile.py'
            elif variant=='rename':comparison['files'][0]['previous_filename']='foreign.py'
            else:comparison['base_commit']['sha']='e'*40
            with self.subTest(variant=variant),self.assertRaises(ValueError):builder.validate_native_reuse_records(*records)

    def test_workflow_builds_Game_once_qualifies_Win32_and_retains_actual_public_SDK_audit(self):
        import yaml
        text=(builder.ROOT/builder.WORKFLOW).read_text();workflow=yaml.safe_load(text)
        self.assertEqual(set(workflow['jobs']),{'changes','client','qualify','apk','public-audit'})
        self.assertFalse(workflow['concurrency']['cancel-in-progress'])
        client=workflow['jobs']['client'];self.assertEqual(client['runs-on'],'windows-2025-vs2026')
        native_builds=[step for step in client['steps'] if 'cmake --build' in step.get('run','')]
        self.assertEqual(len(native_builds),1);self.assertEqual(native_builds[0]['if'],"needs.changes.outputs.reuse_native_run_id == ''")
        self.assertIn('--target Game',native_builds[0]['run']);self.assertIn('--config OptDebug',native_builds[0]['run'])
        self.assertIn('validate-native-reuse',text);self.assertIn('vcvars32.bat',text)
        self.assertIn('test_client_render_queue_native.py --windows-qualify',text)
        self.assertIn('--queue-checks out/client-queue-checks.json',text)
        for forbidden in ('--target MapServer','--target DbServer','package_client_gpu_repair.py',
                'gpu-runtime/build.py','coh-vulkan-gpu-probe.c','coh-gpu-probe.c /Fo',' d8 ',' javac '):
            self.assertNotIn(forbidden,text)
        for key in ('qualify','apk','public-audit'):
            job=workflow['jobs'][key]
            for step in job['steps']:
                command=step.get('run','')
                if ('qualify_client_render_queue.py' in command or 'build_client_render_queue_apk.py build' in command
                        or 'build_client_render_queue_apk.py audit' in command or 'build_client_render_queue_apk.py publish' in command):
                    self.assertIn('--native-source-commit "${{ needs.client.outputs.native_commit }}"',command)
        signing=[s for s in workflow['jobs']['apk']['steps'] if s.get('with',{}).get('name')=='coh-client-interactive-signing']
        self.assertEqual(len(signing),1);self.assertEqual(signing[0]['with']['run-id'],36731428735)
        self.assertTrue(any('Fresh-process SDK' in s.get('name','') for s in workflow['jobs']['apk']['steps']))
        public=workflow['jobs']['public-audit']['steps']
        self.assertTrue(any('download-public' in s.get('run','') for s in public))
        self.assertTrue(any(' audit' in s.get('run','') for s in public))
        for job in workflow['jobs'].values():
            for step in job['steps']:
                if step.get('uses','').startswith('actions/checkout@'):
                    self.assertEqual(step['with']['fetch-depth'],2)
                    self.assertFalse(step['with']['persist-credentials'])

    def test_actual_workflow_gate_reuses_only_exact_bounded_c512_host_recovery(self):
        import yaml
        workflow=yaml.safe_load((builder.ROOT/builder.WORKFLOW).read_text())
        step=next(s for s in workflow['jobs']['changes']['steps'] if s.get('id')=='gate')
        code=step['run'].split("python3 - <<'PY'\n",1)[1].rsplit('\nPY',1)[0]
        source='c512e912a004b66886a7667640aa1a967e95de64';head='b'*40
        names=[builder.WORKFLOW,'tools/android/interactive/test_client_render_queue_package.py']
        def run_gate(changed,parent=source,before=None,event='push',reuse_run='',reuse_source='',published=False):
            def checked(arguments,**kwargs):
                if arguments==['git','rev-parse','HEAD']:return head+'\n'
                if arguments==['git','rev-parse','HEAD^']:return parent+'\n'
                self.assertEqual(arguments,['git','diff','--name-only','-z',parent,head])
                return ('\0'.join(changed)+'\0').encode()
            with tempfile.TemporaryDirectory(prefix='coh-render-queue-gate-') as temporary:
                output=Path(temporary)/'outputs'
                environment={'GH_TOKEN':'fixture','GITHUB_EVENT_NAME':event,'COH_PUSH_BEFORE':before or parent,
                    'COH_REUSE_NATIVE_RUN':reuse_run,'COH_REUSE_NATIVE_COMMIT':reuse_source,'GITHUB_OUTPUT':str(output)}
                request=mock.Mock(return_value=io.BytesIO(json.dumps(release()).encode())) if published else mock.Mock(
                    side_effect=urllib.error.HTTPError('https://fixture',404,'absent',{},None))
                with mock.patch.dict(os.environ,environment),mock.patch('urllib.request.urlopen',request),\
                        mock.patch('subprocess.check_output',side_effect=checked),contextlib.redirect_stdout(io.StringIO()):
                    exec(compile(code,builder.WORKFLOW,'exec'),{})
                return dict(line.split('=',1) for line in output.read_text().splitlines())
        expected={'required':'true','reuse_native_run_id':'37988347729','reuse_native_source_commit':source}
        self.assertEqual(run_gate(names),expected)
        for parent,before,changed in (('a'*40,None,names),(source,'a'*40,names),
                (source,None,names+['android/guest/client_gpu_profile.py']),
                (source,None,names+['unreviewed.py'])):
            with self.subTest(parent=parent,before=before,changed=changed):
                result=run_gate(changed,parent,before);self.assertEqual(result['required'],'false')
                self.assertEqual(result['reuse_native_run_id'],'')
        native=run_gate(names+['tools/android/interactive/package_client_render_queue_native.py'])
        self.assertEqual(native['required'],'true');self.assertEqual(native['reuse_native_run_id'],'')
        self.assertEqual(run_gate(names,published=True)['required'],'false')
        self.assertEqual(run_gate([],event='workflow_dispatch',reuse_run='42',reuse_source='a'*40),
            {'required':'true','reuse_native_run_id':'42','reuse_native_source_commit':'a'*40})
        for run,commit in (('42',''),('','a'*40),('0','a'*40),('42','a'*39)):
            with self.subTest(run=run,commit=commit),self.assertRaises(ValueError):
                run_gate([],event='workflow_dispatch',reuse_run=run,reuse_source=commit)

    def test_workflow_resolved_reuse_outputs_skip_all_native_work_and_preserve_cache_evidence(self):
        import yaml
        workflow=yaml.safe_load((builder.ROOT/builder.WORKFLOW).read_text())
        changes=workflow['jobs']['changes'];client=workflow['jobs']['client']
        self.assertIn('reuse_native_run_id',changes['outputs']);self.assertIn('reuse_native_source_commit',changes['outputs'])
        for step in client['steps']:
            command=step.get('run','')
            if ('package_client_render_queue_native.py stage' in command or 'vcvars32.bat' in command
                    or 'cmake --build' in command or 'package_client_render_queue_native.py package' in command):
                self.assertEqual(step['if'],"needs.changes.outputs.reuse_native_run_id == ''")
            if 'REUSE_NATIVE_RUN' in step.get('env',{}):
                self.assertEqual(step['env']['REUSE_NATIVE_RUN'],'${{ needs.changes.outputs.reuse_native_run_id }}')
                self.assertEqual(step['env']['REUSE_NATIVE_COMMIT'],'${{ needs.changes.outputs.reuse_native_source_commit }}')
        evidence=next(s for s in client['steps'] if s.get('with',{}).get('name')=='coh-client-render-queue-native-build-evidence')
        self.assertIn('out/client-render-queue-native/CMakeCache.txt',evidence['with']['path'])

    def test_workflow_uses_host_PostgreSQL16_with_real_required_fixture_credentials(self):
        import yaml
        workflow=yaml.safe_load((builder.ROOT/builder.WORKFLOW).read_text());qualify=workflow['jobs']['qualify']
        self.assertNotIn('services',qualify)
        self.assertEqual(qualify['env']['COH_REQUIRE_STARTUP_BUNDLE_PG'],'1')
        self.assertEqual(qualify['env']['COH_REQUIRE_LEVELUP_UI_REPAIR_PG'],'1')
        step=next(s for s in qualify['steps'] if s.get('name')=='Start required host PostgreSQL 16 fixtures')
        command=step['run'];self.assertIn('postgresql-16 postgresql-client-16',command)
        self.assertIn('sudo pg_ctlcluster 16 main start',command);self.assertIn('sudo pg_createcluster 16 main',command)
        self.assertIn("server_version_num",command);self.assertIn("current_user = 'postgres'",command)
        self.assertIn("current_database() = 'coh_test_startup_bundle'",command)
        subprocess.run(['bash','-n'],input=command,text=True,check=True,capture_output=True)


class RenderQueueActualPackageTests(unittest.TestCase):
    def setUp(self):
        import test_client_render_queue_contract as contracts
        fixture=contracts.previous.RenderPipelineContractTests(
            'test_typed_layer_extends_exact_renderer_Game_and_preserves_every_previous_wrapper')
        self.addCleanup(fixture.doCleanups);fixture.setUp()
        donor_manifest=fixture.derivative()
        self.native=contracts.append_queue(donor_manifest)['client_render_queue']['manifest']
        self.donor={'_native_client_manifest':copy.deepcopy(donor_manifest),
            'native_build_provenance':builder.parent_history.native_build_provenance(),
            'immutable_donor_provenance':{'native_responsiveness':copy.deepcopy(donor_manifest['native_responsiveness']['receipt'])}}
        self.contents,_=fixture.fixture.read_archive()
        self.contents['CityOfHeroes.exe']=b'qualified-render-pipeline-Game'
        self.contents['client-package.json']=builder.shared.encoded(donor_manifest)
        self.expected=builder.client_manifest(self.donor,self.native)

    def test_actual_canonical_wrapper_retains_all8_producers_and20_Dll_records(self):
        before=copy.deepcopy((self.donor,self.native))
        checked=builder.validate_client_package_bytes(builder.shared.encoded(self.expected),self.donor,self.native)
        self.assertEqual(checked,self.expected);self.assertEqual((self.donor,self.native),before)
        for name in ('native_responsiveness','startup_bundle_client','client_loading','client_startup_followup',
                'client_scene_performance','client_gameplay_performance','client_renderer_attribution','client_render_pipeline'):
            self.assertEqual(checked[name],self.donor['_native_client_manifest'][name])
        self.assertEqual(len([n for n in checked['files'] if n.endswith('.dll')]),20)

    def test_actual_bool_int_float_types_and_noncanonical_wrapper_encoding_fail_closed(self):
        for field,value in (('format',True),('format',1.0),('worker_wakeup_changed',1),('runtime_execution_validated',0.0)):
            changed=copy.deepcopy(self.expected);manifest=changed['client_render_queue']['manifest']
            (manifest if field=='format' else manifest['build_input'])[field]=value
            self.assertEqual(changed,self.expected)
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                builder.validate_client_package_bytes(builder.shared.encoded(changed),self.donor,self.native)
        canonical=builder.shared.encoded(self.expected)
        for raw in (json.dumps(self.expected,sort_keys=True).encode(),canonical.rstrip(b'\n')):
            with self.subTest(bytes=len(raw)),self.assertRaises(ValueError):builder.validate_client_package_bytes(raw,self.donor,self.native)

    def prepare(self,folder):
        old_client=folder/'old-client.zip'
        with zipfile.ZipFile(old_client,'w') as archive:
            for name,raw in self.contents.items():archive.writestr(name,raw)
        with zipfile.ZipFile(old_client) as archive:
            self.donor['_client_members']=builder.engine.startup.startup.client_member_pins(archive)
        assets={'client-runtime.zip':old_client.read_bytes(),
            'hardware-renderer.zip':b'accepted-GPU-and-both-probes',
            'client_interactive_diagnostic.py':b'accepted-Reopen-RP-off',
            'character_reopen_diagnostic.py':b'accepted-character-and-movement-policy',
            'character_session_budget.py':b'accepted-conservative-budget',
            'server-caches.zip':b'accepted-server-assets','client-visual-assets.zip':b'accepted-all-visuals'}
        assets.update({name:b'old-'+name.encode() for name in builder.HELPERS})
        native_members=builder.builder().NATIVE_MEMBERS
        while len(assets)<75-len(native_members):assets['member-'+str(len(assets))+'.zip']=b'accepted-retained-asset'
        self.donor['_client_verification']={'files':{name:builder.pin(raw) for name,raw in assets.items()}}
        assets['client-manifest.json']=builder.shared.encoded(self.donor['_client_verification'])
        runtime={'repository_commit':builder.DONOR_RUNTIME_COMMIT,'files':{name:builder.pin(raw) for name,raw in assets.items()},
            'client_session_repair':{'render_pipeline_isolation_scope':'character_reopen_only','render_pipeline_instrumentation_enabled':False},
            'client_render_pipeline':{'repository_commit':builder.PARENT_NATIVE_COMMIT},
            'client_gpu_profile':{'scene_render_scale':0.75},'client_gpu_probe_repair':{'retained':True}}
        assets['runtime-manifest.json']=builder.shared.encoded(runtime)
        all_payloads={'assets/runtime/'+n:raw for n,raw in assets.items()}
        all_payloads.update({name:b'accepted-ARM64-shell' for name in native_members})
        self.donor.update(payloads={n:builder.pin(raw) for n,raw in all_payloads.items()},
            runtime_manifest=runtime,recompiled_dex=builder.pin(b'actual-024-setup-recompiled-dex'),
            donor_dex=builder.pin(b'old-023-dex'),retained_android_resources={'resources.arsc':builder.pin(b'resources')},
            server_payload_extraction_preflight={'status':'passed','receipt':'external-server-archive-fixture'})
        donor_apk=folder/'donor.apk'
        with zipfile.ZipFile(donor_apk,'w') as archive:
            for name,raw in all_payloads.items():archive.writestr(name,raw)
            archive.writestr('classes.dex',b'actual-024-setup-recompiled-dex');archive.writestr('resources.arsc',b'resources')
            archive.writestr('AndroidManifest.xml',b'AXML-024')
        native_folder=folder/'native';native_folder.mkdir();(native_folder/'CityOfHeroes.exe').write_bytes(b'qualified-render-queue-Game')
        with mock.patch.object(builder.retained,'verify_server_archives',return_value=self.donor['server_payload_extraction_preflight']):
            received,pins=builder.extract_and_repair(donor_apk,self.donor,folder/'extracted','b'*40,native_folder,self.native)
        candidate=folder/'candidate.apk'
        with zipfile.ZipFile(candidate,'w') as archive:
            for name in pins:archive.write(folder/'extracted'/name,name)
            archive.write(folder/'extracted/classes.dex','classes.dex');archive.writestr('resources.arsc',b'resources')
            archive.writestr('AndroidManifest.xml',b'AXML-version-only-025')
        return candidate,pins,received

    def test_actual_derivative_preserves_024_Dex_resources_all20Dlls_and_023_movement_policy(self):
        with tempfile.TemporaryDirectory() as temporary:
            candidate,pins,runtime=self.prepare(Path(temporary))
            with mock.patch.object(builder.retained,'verify_apk_server_archives',return_value=self.donor['server_payload_extraction_preflight']):
                self.assertEqual(builder.verify_derivative(candidate,self.donor,pins,'b'*40,self.native),runtime)
            self.assertEqual(len(pins),77)
            self.assertEqual(sum(pins[n]==self.donor['payloads'][n] for n in pins),70)
            self.assertEqual(runtime['client_session_repair'],self.donor['runtime_manifest']['client_session_repair'])
            self.assertEqual(runtime['client_gpu_profile'],self.donor['runtime_manifest']['client_gpu_profile'])
            self.assertFalse(runtime['client_render_queue']['physical_performance_validated'])
            with zipfile.ZipFile(candidate) as archive:self.assertEqual(builder.pin(archive.read('classes.dex')),self.donor['recompiled_dex'])

    def test_old023_Dex_changed_resources_and_foreign_inventory_are_rejected(self):
        for variant in ('old-dex','resources','foreign','duplicate'):
            with self.subTest(variant=variant),tempfile.TemporaryDirectory() as temporary:
                candidate,pins,_=self.prepare(Path(temporary))
                if variant=='old-dex':replace_member(candidate,'classes.dex',b'old-023-dex')
                elif variant=='resources':replace_member(candidate,'resources.arsc',b'foreign')
                elif variant=='foreign':
                    with zipfile.ZipFile(candidate,'a') as archive:archive.writestr('foreign',b'foreign')
                else:
                    with zipfile.ZipFile(candidate,'a') as archive,self.assertWarns(UserWarning):archive.writestr('classes.dex',b'foreign')
                with self.assertRaises(ValueError):builder.verify_derivative(candidate,self.donor,pins,'b'*40,self.native)

    def test_gpu_assets_session_helpers_and_actual_new_helpers_cannot_hide_under_forged_outer_pin(self):
        for name in ('hardware-renderer.zip','server-caches.zip','client-visual-assets.zip',
                'character_session_budget.py','character_reopen_diagnostic.py','client_interactive_diagnostic.py',
                'client_gpu_profile.py'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as temporary:
                candidate,pins,_=self.prepare(Path(temporary));member='assets/runtime/'+name
                replace_member(candidate,member,b'foreign');pins[member]=builder.pin(b'foreign')
                with self.assertRaises(ValueError):builder.verify_derivative(candidate,self.donor,pins,'b'*40,self.native)

    def qualification(self,folder):
        import qualify_client_render_queue as qualification
        commit='c'*40
        (folder/builder.native_producer().MANIFEST).write_bytes(builder.shared.encoded(self.native))
        self.donor['qualification']={'source_files':{}}
        pins={name:builder.builder().file_pin(builder.ROOT/name) for name in qualification.source_paths(self.donor)}
        compiled=self.native['repository_commit']==commit and self.native['run_url']==builder.publication_provenance(commit)['run_url']
        return {'format':1,'status':'passed','scope':builder.QUALIFICATION_SCOPE,
            'repository_commit':commit,'runtime_repository_commit':commit,'donor':builder.donor_link(),
            'checks':dict.fromkeys(builder.CHECKS,True),
            'actual_native_ancestry_validation':copy.deepcopy(builder.ACTUAL_NATIVE_ANCESTRY_CHECKS),
            'native_client_render_queue':self.native,
            'native_build_provenance':builder.native_build_provenance(self.native,folder,commit),
            'publication_provenance':builder.publication_provenance(commit),
            'retained_native_repository_commit':builder.PARENT_NATIVE_COMMIT,
            'native_build_repository_commit':self.native['repository_commit'],
            'changed_java_sources':[],'retained_java_sources_verified':19,'baseline_payloads_verified':77,
            'actual_external_donor_and_full_guest_wrapper_verified':True,
            **dict.fromkeys(builder.FALSE_FLAGS,False),**dict.fromkeys(builder.TRUE_FLAGS,True),
            'native_client_compiled_in_current_run':compiled,'native_client_compiled_in_current_publication_run':compiled,
            'test_suites':{name:{'status':'passed','skipped':0,'tests_run':1} for name in qualification.TEST_MODULES},
            'tests_run':len(qualification.TEST_MODULES),'check_suites':qualification.CHECK_SUITES,'source_files':pins,
            'postgresql_emission_fixtures':['cancelled_child_deletion_commits','delete_insert_replacement_commits','duplicate_insert_23505_rollback'],
            'postgresql_levelup_fixtures':sorted(builder.retained.levelup_postgresql_fixtures())}

    def test_fresh_sorted_qualification_reader_checks_canonical_native_and_full_source_closure(self):
        with tempfile.TemporaryDirectory() as temporary,mock.patch.dict(os.environ,{'GITHUB_RUN_ID':'1234'}):
            folder=Path(temporary);receipt=self.qualification(folder)
            builder.validate_qualification(receipt,'c'*40,self.donor)
            path=folder/'qualification.json';path.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
            donor_path=folder/'donor.json';donor_path.write_text(json.dumps(self.donor,sort_keys=True)+'\n')
            code='import sys;sys.path[:0]=["tools/android/interactive","tools/android","tools/android/dbserver","tools","android/guest"];from pathlib import Path;import build_client_render_queue_apk as b;b.validate_qualification(b.read_json(Path(sys.argv[1])),sys.argv[3],b.read_json(Path(sys.argv[2])));print("fresh sorted native/source receipt passed")'
            result=subprocess.run([sys.executable,'-c',code,str(path),str(donor_path),'c'*40],
                cwd=builder.ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
            self.assertEqual(result.returncode,0,result.stdout)
            self.assertIn('fresh sorted native/source receipt passed',result.stdout)
            foreign=copy.deepcopy(receipt);foreign['source_files'][builder.WORKFLOW]['sha256']='f'*64
            path.write_text(json.dumps(foreign,indent=2,sort_keys=True)+'\n')
            rejected=subprocess.run([sys.executable,'-c',code,str(path),str(donor_path),'c'*40],
                cwd=builder.ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
            self.assertNotEqual(rejected.returncode,0,rejected.stdout)
            self.assertNotIn('fresh sorted native/source receipt passed',rejected.stdout)

    def test_qualification_rejects_missing_retained_sources_skips_typed_flags_or_relabelled_native(self):
        with tempfile.TemporaryDirectory() as temporary,mock.patch.dict(os.environ,{'GITHUB_RUN_ID':'1234'}):
            receipt=self.qualification(Path(temporary))
            for variant in ('format_bool','checks_int','skip','count_float','source_missing','source_foreign',
                    'parent_relabel','current_relabel','missing_pg','new_native_bool'):
                changed=copy.deepcopy(receipt)
                if variant=='format_bool':changed['format']=True
                elif variant=='checks_int':changed['checks'][builder.CHECKS[0]]=1
                elif variant=='skip':next(iter(changed['test_suites'].values()))['skipped']=1
                elif variant=='count_float':changed['tests_run']=float(changed['tests_run'])
                elif variant=='source_missing':changed['source_files'].pop(next(iter(changed['source_files'])))
                elif variant=='source_foreign':changed['source_files']['foreign.py']=builder.pin(b'foreign')
                elif variant=='parent_relabel':changed['native_build_provenance']['parent_native_build_provenance']['repository_commit']='e'*40
                elif variant=='current_relabel':changed['native_client_compiled_in_current_run']=False
                elif variant=='missing_pg':changed['postgresql_emission_fixtures'].pop()
                else:changed['native_client_render_queue']['format']=True
                with self.subTest(variant=variant),self.assertRaises(ValueError):
                    builder.validate_qualification(changed,'c'*40,self.donor)

    def test_current_native_provenance_keeps_original5af_parent_and_records_reused_build_truthfully(self):
        with tempfile.TemporaryDirectory() as temporary,mock.patch.dict(os.environ,{'GITHUB_RUN_ID':'1234'}):
            folder=Path(temporary);(folder/builder.native_producer().MANIFEST).write_bytes(builder.shared.encoded(self.native))
            original=copy.deepcopy(self.native);original['repository_commit']='c'*40
            receipt=builder.native_build_provenance(original,folder,'c'*40)
            self.assertTrue(receipt['compiled_in_current_publication_run'])
            self.assertEqual(receipt['parent_native_build_provenance'],builder.parent_history.native_build_provenance())
            self.assertNotEqual(receipt['repository_commit'],builder.PARENT_NATIVE_COMMIT)
            reused=builder.native_build_provenance(original,folder,'b'*40)
            self.assertFalse(reused['compiled_in_current_publication_run'])
            self.assertEqual(reused['repository_commit'],receipt['repository_commit'])
            self.assertEqual(reused['run_id'],receipt['run_id'])
            self.assertEqual(reused['native_manifest'],receipt['native_manifest'])


if __name__=='__main__':unittest.main()
