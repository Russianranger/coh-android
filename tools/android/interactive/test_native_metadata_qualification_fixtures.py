"""Finite recovery tests use original qualified/failed bytes; no native launch."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch, Mock
import urllib.request
import zipfile

import prepare_native_metadata_qualification_fixtures as fixtures


class NativeMetadataQualificationFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recovery = Path(os.environ.get('COH_METADATA_RECOVERY', fixtures.ROOT/'out/native-metadata-fixtures'))
        cls.donor = Path(os.environ.get('COH_ZONE_STARTUP_TEST_DONOR_APK', fixtures.ROOT/'out/donor.apk'))
        cls.payloads = cls.recovery/'public-asset-cache-donor'
        cls.paths = {role: cls.recovery/spec['filename'] for role,spec in fixtures.ARTIFACTS.items()}
        cls.apis = {role: {kind: json.loads((cls.recovery/'api'/role/(kind+'.json')).read_bytes())
            for kind in ('run','jobs','artifact')} for role in fixtures.ARTIFACTS}
        for role,path in cls.paths.items():
            fixtures.validate_api(fixtures.ARTIFACTS[role],cls.apis[role])
            fixtures.original_archive(path.read_bytes(),fixtures.ARTIFACTS[role])

    def output(self):
        temporary=self.enterContext(tempfile.TemporaryDirectory(prefix='coh-finite-metadata-fixture-'))
        return Path(temporary)/'owned'

    def prepare(self,output,paths=None,apis=None):
        return fixtures.prepare(self.donor,self.payloads,output,archive_paths=paths or self.paths,api_snapshots=apis or self.apis)

    def test_actual_original_recovery_preserves_five_archives_components_sources_and_failed_results(self):
        output=self.output()
        with patch.object(fixtures,'request_bytes',side_effect=AssertionError('No network or Base fetch in offline original recovery')):
            proof=self.prepare(output)
        self.assertEqual(set(proof['original_artifacts']),set(fixtures.ARTIFACTS))
        self.assertTrue(proof['original_Game_source']['source_staging_and_reverse_patch_verified'])
        self.assertFalse(proof['native_binaries_rebuilt']);self.assertFalse(proof['native_processes_executed'])
        self.assertFalse(proof['runtime_authority_created']);self.assertFalse(proof['failed_historical_runs_relabelled'])
        self.assertFalse(proof['asset_volume_downloaded_by_this_stage']);self.assertIsNone(proof['full_final_world_descriptor'])
        for role,spec in fixtures.ARTIFACTS.items():
            self.assertEqual((output/spec['filename']).read_bytes(),self.paths[role].read_bytes())
            self.assertEqual(proof['original_artifacts'][role]['actual_API']['run']['conclusion'],spec['conclusion'])
        for name,pin in fixtures.COMPONENTS.items():
            self.assertEqual(fixtures.pin((output/'public-asset-cache-donor'/name).read_bytes()),pin)
        failed=json.loads((output/'map8a-world-evidence'/fixtures.REPORT).read_bytes())
        self.assertEqual(failed['status'],'failed')
        self.assertTrue(all(Path(path).exists() for name,path in proof['environment'].items() if name!='COH_METADATA_RECOVERY'))

    def test_original_run_job_and_artifact_custody_mutations_rejected(self):
        spec=fixtures.ARTIFACTS['failed_b323']
        for field in ('run_source','run_success','job_success','job_id','artifact_digest','artifact_expired','repository','head_repository'):
            value=copy.deepcopy(self.apis['failed_b323'])
            if field=='run_source':value['run']['head_sha']='0'*40
            elif field=='run_success':value['run']['conclusion']='success'
            elif field=='job_success':next(r for r in value['jobs']['jobs'] if r['id']==spec['job_id'])['conclusion']='success'
            elif field=='job_id':next(r for r in value['jobs']['jobs'] if r['id']==spec['job_id'])['id']=True
            elif field=='artifact_digest':value['artifact']['digest']='sha256:'+'0'*64
            elif field=='artifact_expired':value['artifact']['expired']=True
            elif field=='repository':value['run']['repository']['full_name']='unknown/repository'
            else:value['artifact']['workflow_run']['head_repository_id']=1
            with self.subTest(field=field),self.assertRaises(ValueError):fixtures.validate_api(spec,value)

    def test_archive_byte_or_report_pin_mutation_rejected(self):
        spec=fixtures.ARTIFACTS['failed_04b'];raw=self.paths['failed_04b'].read_bytes()
        with self.assertRaises(ValueError):fixtures.original_archive(raw[:-1]+bytes([raw[-1]^1]),spec)
        changed=copy.deepcopy(spec);changed['report_pin']['sha256']='0'*64
        with self.assertRaises(ValueError):fixtures.original_archive(raw,changed)

    def test_missing_mismatched_or_linked_inputs_fail_before_owned_output_is_created(self):
        for field in ('missing_role','bad_zip','linked_zip','bad_api'):
            paths=copy.deepcopy(self.paths);apis=copy.deepcopy(self.apis);output=self.output()
            if field=='missing_role':paths.pop('preload')
            elif field=='bad_api':apis['failed_8a']['run']['head_sha']='0'*40
            else:
                parent=output.parent;target=parent/'input.zip'
                if field=='bad_zip':target.write_bytes(b'Not an original archive')
                else:target.symlink_to(self.paths['preload'])
                paths['preload']=target
            with self.subTest(field=field),self.assertRaises(ValueError):self.prepare(output,paths,apis)
            self.assertFalse(output.exists())

    def test_existing_unknown_output_and_repeated_attempt_are_preserved(self):
        output=self.output();output.mkdir();sentinel=output/'unrelated';sentinel.write_bytes(b'preserve unknown existing evidence')
        before=sentinel.read_bytes()
        with patch.object(fixtures,'request_bytes',side_effect=AssertionError('No request permitted')),self.assertRaises(ValueError):self.prepare(output)
        self.assertEqual(sentinel.read_bytes(),before);self.assertEqual(list(output.iterdir()),[sentinel])

    def test_all_historical_artifact_members_are_safe_and_failures_remain_failed(self):
        for role,spec in fixtures.ARTIFACTS.items():
            members,raw=fixtures.original_archive(self.paths[role].read_bytes(),spec)
            self.assertEqual(len(members),spec['members'])
            if role.startswith('failed_'):self.assertEqual(json.loads(raw)['status'],'failed')

    def test_fixture_proof_cannot_relabel_native_execution_or_substitute_original_source(self):
        # Update only this source pin in the old local host receipt: its actual
        # ZIP/API inputs remain the authenticated original test material.
        proof=json.loads((self.recovery/'fixture-recovery.json').read_bytes())
        proof['fixture_preparer_source']['pin']=fixtures.pin(Path(fixtures.__file__).read_bytes())
        fixtures.validate_proof(proof)
        with self.assertRaises(ValueError):fixtures.validate_proof(proof,repository_commit='0'*40)
        for field in ('native_execution','failure','component','source','member','other_member','environment','checkout','preparer'):
            changed=copy.deepcopy(proof)
            if field=='native_execution':changed['native_processes_executed']=True
            elif field=='failure':changed['original_artifacts']['failed_b323']['actual_API']['run']['conclusion']='success'
            elif field=='component':changed['original_components']['client-caches.zip']['sha256']='0'*64
            elif field=='source':changed['original_Game_source']['retained_Game_build_input']['source_commit']='0'*40
            elif field=='member':changed['original_artifacts']['preload']['member_pins']['native-startup-profile-qualification.json']['sha256']='0'*64
            elif field=='other_member':changed['original_artifacts']['map_producer']['member_pins']['MapServer-prefetch.exe']['sha256']='0'*64
            elif field=='environment':changed['environment']['COH_METADATA_TEST_MAP_PRODUCER']='/unrelated/substituted.zip'
            elif field=='checkout':changed['original_Game_source']['checkout_repository_commit']=True
            else:changed['fixture_preparer_source']['pin']['sha256']='0'*64
            with self.subTest(field=field),self.assertRaises(ValueError):fixtures.validate_proof(changed)

    def test_redirect_strips_token_and_refuses_unknown_or_plaintext_destinations(self):
        request=urllib.request.Request(fixtures.API+'/actions/artifacts/11791389599/zip',headers={'Authorization':'Bearer private-test-token'})
        redirected=fixtures.ArtifactRedirect().redirect_request(request,None,302,'redirect',{},
            'https://productionresults.blob.core.windows.net/artifact?signature=fixture')
        self.assertIsNone(redirected.get_header('Authorization'))
        for url in ('http://productionresults.blob.core.windows.net/artifact','https://unrelated.example/artifact'):
            with self.subTest(url=url),self.assertRaises(ValueError):
                fixtures.ArtifactRedirect().redirect_request(request,None,302,'redirect',{},url)

    def test_only_finite_original_api_routes_can_send_credentials_and_response_is_bounded(self):
        opener=Mock();response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        opener.open.return_value=response;response.read.return_value=b'x'
        known=fixtures.API+'/actions/artifacts/11791389599/zip'
        with patch.object(fixtures.urllib.request,'build_opener',return_value=opener):
            self.assertEqual(fixtures.request_bytes(known,1,'private-test-token'),b'x')
            for url in ('https://github.com/assets/COH-Assets-1.0.0-Base.zip',fixtures.API+'/actions/../secrets',
                    fixtures.API+'/actions/artifacts/1/zip','https://api.github.com/repos/unrelated/repository/actions/runs/38352862725'):
                before=opener.open.call_count
                with self.subTest(url=url),self.assertRaises(ValueError):fixtures.request_bytes(url,1,'private-test-token')
                self.assertEqual(opener.open.call_count,before)
            response.read.return_value=b'xx'
            with self.assertRaises(ValueError):fixtures.request_bytes(known,1)


if __name__=='__main__':unittest.main()
