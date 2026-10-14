"""Host derivation checks. All constructed world cases are UNEXECUTED fixtures.

Only the original9454 preload and public donor archive bytes are executed
historical evidence. No Game, MapServer, Wine, player profile or new native
world is executed here, and every production authority remains closed.
"""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import derive_native_metadata_cache_proof as derive

RECOVERY = Path(os.environ.get('COH_METADATA_RECOVERY', '/workspace/scratch/5d16603ca7ff/native037-recovery'))


def progress(sequence, ticks):
    raw = bytearray(128); raw[:8] = b'COHMAP1\0'
    struct.pack_into('<8I', raw, 8, 1, 128, 100, 101, sequence, 36, ticks, ticks)
    return {'windows_pid':100, 'main_thread_id':101, 'sequence':sequence,
        'tick_started':ticks, 'tick_completed':ticks, 'raw_record_hex':raw.hex(),
        'raw_record_sha256':hashlib.sha256(raw).hexdigest()}


def unexecuted_world(preload):
    """Shape-only world fixture, including independently checked GroupBounds."""
    inventory = copy.deepcopy(preload['records']['profile']['cache_after'])
    inventory['data/geobin/object_library/fixture.bin'] = derive.pin(b'unexecuted geometry fixture')
    inventory['data/geobin/object_library/fixture.bounds'] = derive.pin(b'unexecuted GroupBounds fixture')
    stock = preload['fixture_generation']['actual_native']
    audit = derive.json_document((derive.ROOT/'docs/android-evidence/native-map-metadata-source-boundary-0.13.37.json').read_bytes())
    sdk = audit['historical_cooking_and_SDK_runtime_DLLs_to_require_in_fresh_world_inputs']
    cases = []
    for map_id in derive.WORLDS:
        name, port, objects = derive.WORLDS[map_id]
        for variant, phase, role in derive.PLAN:
            native = stock if role == 'stock' else preload['records']['profile' if role == 'candidate' else 'control']['actual_native']
            ids = preload['records']['profile']['identifiers_after']
            provider = {'identifier_inputs':ids, 'full_content_hashed':True,'native_components':sdk}
            cases.append({'map_id':map_id,'fx_variant':variant,'phase':phase,'role':role,'actual_native':native,
                'world_markers':{'map_id':map_id,'world':name,'udp_port':port,'PhysX_objects':objects,
                    'ordered_world_phases':True,'UDP_loopback_endpoint_verified':True,'behavioral_collision_proven':False},
                'native_Db_status':{'map_id':map_id,'world':name,'address':'127.0.0.1','port':port},
                'Map_progress_before_status':progress(1,1),'Map_progress_after_status':progress(2,2),
                'memory':{'samples':[{'working_set_bytes':4096,'private_commit_bytes':8192,
                    'lifetime_peak_working_set_bytes':4096,'lifetime_peak_commit_bytes':8192}],
                    'sample_count':1,'Thor_measured':False}, 'owned_cleanup_verified':True,'synthetic_row_unchanged':True,
                'cache_before':inventory,'cache_after':inventory,'cache_delta':{'added':{},'removed':{},'changed':{}},
                'provider_before':provider,'provider_after':provider,'native_observations':preload['observations']})
    return {'format':1,'repository_commit':'7'*40,'status':'passed','controlled_unexecuted_fixture':True,
        'actual_native_worlds_executed':[1,5],'actual_native_processes':16,'failures':[],
        'actual_full_and_SERVER_only_FX_world_consumers_verified':True,'owned_cleanup_verified':True,
        'memory_measured':True,'player_profile_opened':False,'physical_device_executed':False,
        'behavioral_collision_proven':False,'shipping_allowed':False,'freshness_bypass_enabled':False,'cases':cases}


class CacheProofDerivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = {'preload':RECOVERY/'artifact-11791389599.zip',
            'client_cache_manifest':RECOVERY/'public-asset-cache-donor/client-caches.zip',
            'server_cache_manifest':RECOVERY/'public-asset-cache-donor/server-caches.zip'}
        cls.inputs = {}; cls.documents = {}
        for role,path in cls.paths.items():
            raw = path.read_bytes()
            member = {'preload':'native-startup-profile-qualification.json',
                'client_cache_manifest':'client-cache-manifest.json','server_cache_manifest':'server-cache-manifest.json'}[role]
            with zipfile.ZipFile(io.BytesIO(raw)) as archive: body = archive.read(member)
            cls.documents[role] = derive.json_document(body)
            common = {'member':member,'member_pin':derive.pin(body)}
            cls.inputs[role] = ({**common,'repository_commit':cls.documents[role]['repository_commit'],
                'run_id':38352862725,'artifact_id':11791389599,'artifact_zip':derive.pin(raw)} if role == 'preload'
                else {**common,'component_zip':derive.pin(raw),'origin':'exact_public_Assets_1_0_0_component'})
        assert cls.inputs['preload']['artifact_zip'] == {'bytes':281739,
            'sha256':'5a5bf01b901e5c5398bb42f07e4c1737ac8b13ee90e90fb297ca01cd08dfa34b'}
        assert cls.inputs['client_cache_manifest']['component_zip'] == {'bytes':27071659,
            'sha256':'5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051'}
        assert cls.inputs['server_cache_manifest']['component_zip'] == {'bytes':29825263,
            'sha256':'7439d4557ae9fd74bb4bb4a324b6a676829387124be0817eb1da3c8adff10b17'}
        cls.narrow = derive.inspect_preload(cls.documents['preload'], cls.documents)

    def authenticated_unexecuted_world(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        path=Path(temporary.name)/'unexecuted-world.zip';world=unexecuted_world(self.documents['preload']);raw=derive.metadata.encoded(world)
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as archive:archive.writestr('world.json',raw)
        inputs=copy.deepcopy(self.inputs);inputs['native_world']={'repository_commit':'7'*40,'run_id':1,'artifact_id':2,
            'artifact_zip':derive.pin(path.read_bytes()),'member':'world.json','member_pin':derive.pin(raw)}
        return derive.authenticate_inputs({**self.paths,'native_world':path},inputs),inputs

    def test_actual_authenticated_9454_subset_is107_not191_with12_identifier_inputs(self):
        result = derive.inspect_preload(self.documents['preload'], self.documents)
        self.assertEqual(len(result['eligible']),107)
        self.assertEqual(result['inventory_only_count'],191)
        self.assertEqual(result['successfully_observed_unique_names'],124)
        self.assertEqual(len(result['identifier_inputs']),12)
        self.assertEqual(len(result['decisions']['profile']),129)
        self.assertEqual(len(result['decisions']['freshness']),125)
        self.assertEqual(sum(x['archive']=='client-caches.zip' for x in result['eligible'].values()),22)
        self.assertEqual(sum(x['archive']=='server-caches.zip' for x in result['eligible'].values()),85)
        self.assertEqual(sum(x.get('reason')=='original_donor_output_changed' for x in result['excluded']),17)
        self.assertEqual(sum(x.get('reason')=='unmapped_or_ambiguous_diagnostic_name' for x in result['excluded']),1)
        self.assertNotIn('data/server/bin/ProficiencyIds.bin',result['eligible'])
        self.assertEqual(result['eligible']['data/server/bin/PC_Rewards.bin']['archive'],'server-caches.zip')
        self.assertEqual(result['eligible']['data/server/bin/PC_Rewards.bin']['record']['bytes'],676)

    def test_failed_actual8a_world_is_rejected_before_proof_exists(self):
        failed = derive.json_document((RECOVERY/'map8a-world-evidence/native-map-world-037-qualification.json').read_bytes())
        with self.assertRaises(ValueError):derive.inspect_world(failed,self.narrow)

    def test_native_order_identifier_or_cache_mutation_rejected(self):
        for field in ('order','identifiers','cache','success_bool'):
            value=copy.deepcopy(self.documents['preload'])
            if field=='order':value['observations']['profile_rows'].reverse()
            elif field=='identifiers':next(iter(value['records']['profile']['identifiers_after'].values()))['sha256']='f'*64
            elif field=='cache':next(iter(value['records']['profile']['cache_after'].values()))['sha256']='f'*64
            else:value['observations']['profile_rows'][0]['success']=1
            with self.subTest(field=field),self.assertRaises(ValueError):derive.inspect_preload(value,self.documents)

    def test_unobserved_inventory_does_not_become_eligible_and_message_store_is_separate(self):
        rows=derive.donor_rows(self.documents)
        self.assertTrue(all(x['record'].get('kind','Parse6')=='Parse6' for x in rows.values()))
        self.assertGreater(len(rows),107)
        self.assertEqual(set(self.narrow['eligible']),set(rows)&set(self.narrow['eligible']))
        # FNV diagnostics are never claimed as content integrity or native ID tables.
        self.assertEqual(derive.diagnostic_token('bin/sequencers.bin'),'d44d0c3e')

    def test_controlled_unexecuted_world_complete_shape_preserves107_and_geometry_closure(self):
        result=derive.inspect_world(unexecuted_world(self.documents['preload']),self.narrow)
        self.assertEqual(len(result['eligible']),107)
        self.assertTrue(all('geobin' not in name for name in result['eligible']))

    def test_controlled_world_missing_case_tick_status_memory_or_groupbounds_rejected(self):
        for field in ('matrix','tick','port','map_bool','native','identifier','GroupBounds','memory_bool'):
            world=copy.deepcopy(unexecuted_world(self.documents['preload']));case=world['cases'][1]
            if field=='matrix':world['cases'].pop()
            elif field=='tick':case['Map_progress_after_status']=copy.deepcopy(case['Map_progress_before_status'])
            elif field=='port':case['native_Db_status']['port']=7003
            elif field=='map_bool':case['native_Db_status']['map_id']=True
            elif field=='native':case['actual_native']['sha256']='f'*64
            elif field=='identifier':next(iter(case['provider_after']['identifier_inputs'].values()))['sha256']='f'*64
            elif field=='GroupBounds':case['cache_before']=copy.deepcopy(case['cache_before']);case['cache_after']=copy.deepcopy(case['cache_after']);case['cache_before'].pop('data/geobin/object_library/fixture.bounds');case['cache_after'].pop('data/geobin/object_library/fixture.bounds')
            else:case['memory']['samples'][0]['working_set_bytes']=True
            with self.subTest(field=field),self.assertRaises(ValueError):derive.inspect_world(world,self.narrow)

    def test_actual_source_bound_sdk_pins_reject_modified_controlled_world_dll(self):
        world=unexecuted_world(self.documents['preload'])
        audit=derive.json_document((derive.ROOT/'docs/android-evidence/native-map-metadata-source-boundary-0.13.37.json').read_bytes())
        sdk=audit['historical_cooking_and_SDK_runtime_DLLs_to_require_in_fresh_world_inputs']
        derive.inspect_world(world,self.narrow,sdk)
        world=copy.deepcopy(world)
        world['cases'][0]['provider_before']['native_components']['PhysXCooking.dll']['sha256']='f'*64
        with self.assertRaises(ValueError):derive.inspect_world(world,self.narrow,sdk)

    def test_actual_original_zip_member_authentication_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'unexecuted-world.zip';world=unexecuted_world(self.documents['preload']);raw=derive.metadata.encoded(world)
            with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as archive:archive.writestr('world.json',raw)
            inputs=copy.deepcopy(self.inputs);inputs['native_world']={'repository_commit':'7'*40,'run_id':1,'artifact_id':2,
                'artifact_zip':derive.pin(path.read_bytes()),'member':'world.json','member_pin':derive.pin(raw)}
            paths={**self.paths,'native_world':path}
            actual=derive.authenticate_inputs(paths,inputs)
            self.assertEqual(actual['preload'],self.documents['preload'])
            for field in ('artifact_zip','member_pin'):
                bad=copy.deepcopy(inputs);bad['native_world'][field]['sha256']='f'*64
                with self.subTest(field=field),self.assertRaises(ValueError):derive.authenticate_inputs(paths,bad)

    def test_mutation_after_authenticated_read_fails_before_derivation(self):
        docs,inputs=self.authenticated_unexecuted_world()
        docs=copy.deepcopy(docs);docs['preload']['repository_commit']='9'*40
        with self.assertRaisesRegex(ValueError,'mutated after authenticated reading'):
            derive.derive_proof(docs,raw_inputs=inputs,derivation_source={},source_review={})

    def test_derived_output_has_external_pin_no_recursive_identity_and_source_only_scope(self):
        docs,inputs=self.authenticated_unexecuted_world()
        script=(derive.ROOT/derive.SCRIPT).read_bytes();source={'repository_commit':'8'*40,'path':derive.SCRIPT,
            'git_blob':hashlib.sha1(b'blob '+str(len(script)).encode()+b'\0'+script).hexdigest(),'pin':derive.pin(script)}
        audit=derive.json_document((derive.ROOT/'docs/android-evidence/native-map-metadata-source-boundary-0.13.37.json').read_bytes())
        raw=derive.metadata.encoded(audit);descriptor={'repository':'Russianranger/coh-android','commit':'1b8da4eb850c0e7c4f4ef0a49e43e15ac948ca2e',
            'path':'docs/android-evidence/native-map-metadata-source-boundary-0.13.37.json','git_blob':'6b6d373a275029476f28c77cc5fcfe010e58b9bb',
            'content':derive.pin(raw),'scope':derive.startup.SOURCE_ONLY_REVIEW_SCOPE}
        with patch.object(derive.startup,'SOURCE_ONLY_COMPATIBILITY_REVIEW',{'descriptor':descriptor,'document':audit}):
            proof,outer=derive.derive_proof(docs,raw_inputs=inputs,derivation_source=source,source_review=descriptor)
        self.assertNotIn('output',proof['derivation'])
        self.assertEqual(outer['output']['pin'],derive.pin(derive.metadata.encoded(proof)))
        self.assertEqual(proof['source_compatibility_review'],descriptor)
        self.assertEqual(proof['observations_scope']['eligible_original_donor_BIN_count'],107)
        self.assertFalse(proof['runtime_authority_created']);self.assertFalse(proof['shipping_allowed'])
        self.assertFalse(proof['derivation']['scope']['original_artifact_membership_claimed'])

    def test_actual_normalizer_source_requires_real_commit_bytes_and_blob(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp);path=repo/derive.SCRIPT;path.parent.mkdir(parents=True);raw=(derive.ROOT/derive.SCRIPT).read_bytes();path.write_bytes(raw)
            for cmd in (['git','init','-q'],['git','add',derive.SCRIPT],['git','-c','user.name=COH fixture','-c','user.email=fixture@invalid','commit','-qm','Unexecuted source fixture']):
                subprocess.run(cmd,cwd=repo,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            source={'repository_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
                'path':derive.SCRIPT,'git_blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),'pin':derive.pin(raw)}
            self.assertEqual(derive.verify_derivation_source(source,repo),source)
            for field in ('repository_commit','git_blob','pin'):
                bad=copy.deepcopy(source);bad[field]=('9'*40 if field!='pin' else {'bytes':len(raw),'sha256':'9'*64})
                with self.subTest(field=field),self.assertRaises(ValueError):derive.verify_derivation_source(bad,repo)

    def test_production_authorities_remain_closed(self):
        self.assertFalse(derive.startup.SOURCE_ONLY_COMPATIBILITY_REVIEW['descriptor']['scope']['runtime_activation_allowed'])
        self.assertIsNone(derive.startup.RUNTIME_CACHE_PROOF_DERIVATION)
        self.assertEqual(derive.metadata.COMPONENT_AUTHORITIES,{'game':None,'mapserver':None})
        self.assertFalse(derive.metadata.ACTIVATION_IMPLEMENTED)


if __name__=='__main__':unittest.main()
