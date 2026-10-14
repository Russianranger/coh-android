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


def unexecuted_generation(case, *, inherited_authority=None):
    """Only a schema/absence fixture; these namespace checks were NOT executed."""
    rows = {}
    for cache in case['cache_after']:
        if cache.startswith('data/geobin/object_library/') and cache.endswith('.bounds'):
            stem=cache.removesuffix('.bounds'); counterpart=stem+'.bin'
            if counterpart not in case['cache_after']:continue
            path=stem.removeprefix('data/geobin/').casefold()+'.txt'
            for name in (cache,counterpart):
                rows[name]=[{'path':path,'native_dependency_timestamp':0,'original_source_absent':True,
                    'kind':'native_same_stem_missing_text_sentinel','current_native_namespace_source_absent':True}]
            if len(rows)==136:break
    if not rows:
        name=next(iter(case['cache_after']));rows[name]=[{'path':'defs/unexecuted.def','native_dependency_timestamp':1,
            'actual_source_mtime_ns':1000000000,'actual_source':derive.pin(b'unexecuted positive source')}]
    negatives=sum(row['native_dependency_timestamp']==0 for deps in rows.values() for row in deps)
    paths={row['path'] for deps in rows.values() for row in deps if row['native_dependency_timestamp']==0}
    namespace={'ordinary_search_roots':['./piggs','./data','./'],
        **dict.fromkeys(('original_and_current_casefolded_paths_checked','linked_or_reparse_providers_refused',
            'external_directory_controls_refused','automatic_data_tools_ancestor_pairs_absent','Pig_members_exclusively_original_anim_paths'),True),
        'animation_Pig':{'bytes':97084456,'sha256':'465d69a266f2b07afd800b8a7bd3f5e63fa16a24955391f826264d7f8d3a968b'},
        'complete_Pig_member_count':5878,'complete_Pig_member_names_sha256':'e'*64,'checked_ancestors':['unexecuted-fixture'],
        'animation_Pig_member_recipe_source':{'bytes':14716,'sha256':'56825a9b66669133380c761d9475b57b6ccd4ee5cf71b6044474c0ff32bbc91d'},
        'native_recipe_source':{'bytes':92002,'sha256':'8ad08c34d2fed652578e26f0ec1fab79419b40414644c6b8e1ccbc58694733e1'}}
    producer={'native':case['actual_native'],'held_windows_pid':case['Map_progress_after_status']['windows_pid'],
        'map_id':case['map_id'],'post_query_completed_ticks':case['Map_progress_after_status']['tick_completed'],
        'native_Db_status':case['native_Db_status'],'world_initialization_markers':case['world_markers'],
        'original_source_delta':case['original_source_delta'],'provider_native_components':case['provider_after']['native_components']}
    if inherited_authority is not None:producer['inherited_execution']=inherited_authority
    return {'delta':case['cache_delta'],'existing_decoded_payload_and_schema_unchanged':True,
        'new_payloads_require_exact_stock_native_world_producer':True,'new_payloads_require_identical_warm_native_consumers':True,
        'Android_cache_authority_created':False,'actual_stock_producer':producer,'actual_dependency_sources':rows,
        'native_negative_source_dependencies':{'rows':negatives,'unique_paths':len(paths),
            'all_same_stem_object_library_text_with_native_zero_date':True,'namespace':namespace if negatives else None,
            'original_complete_provider_membership_count':165767,
            'original_complete_provider_membership_sha256':'496f9f88df2f9f9be782107d889e33566cef12daf3f4fd98d698accd2c69a69f',
            'native_sentinel_recipe':copy.deepcopy(derive.NATIVE_ABSENCE_RECIPE)}}


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
        cls.inherited_path = RECOVERY/'map04b-world-evidence.zip'
        with zipfile.ZipFile(cls.inherited_path) as archive:
            cls.old_report = derive.json_document(archive.read(derive.WORLD_REPORT_MEMBER))
            cls.old_auxiliary = {key:derive.json_document(archive.read(member)) for key,member in {
                'phase':'1-server_only-generation/phase.json',
                'retention':'1-server_only-generation/stock-native-generated-cache-outputs.json',
                'failed_observations':'failed-native-observations.json'}.items()}
        cls.inherited_input={'repository_commit':derive.INHERITED_STOCK['source'],'run_id':derive.INHERITED_STOCK['run_id'],
            'artifact_id':derive.INHERITED_STOCK['artifact_id'],'artifact_zip':derive.INHERITED_STOCK['artifact'],
            'member':derive.WORLD_REPORT_MEMBER,'member_pin':derive.INHERITED_REPORT}

    def unexecuted_mixed_world(self):
        world=unexecuted_world(self.documents['preload']);old=self.old_report['cases'][0]
        profile=self.old_auxiliary['failed_observations']['synthetic_profile']
        authority={**derive.INHERITED_STOCK,'original_overall_result':'failed','original_stock_world_readiness_genuine':True,
            'stock_native_readiness_reexecuted':False,'stock_native_execution_inherited':True,
            'negative_dependency_validation_fresh_in_this_qualifier':True,'negative_dependency_validation_status':'passed',
            'original_report':derive.INHERITED_REPORT,'prepared_manifest':derive.PREPARED_MANIFEST,'disposable_SQL_fixture':profile}
        world.update(repository_commit=derive.RESUME_SOURCE,actual_native_processes=15,inherited_native_world_processes=1,
            total_native_world_cases=16,inherited_stock_generation=authority,
            source_pins={'tools/android/interactive/qualify_native_map_world_037.py':derive.RESUME_QUALIFIER})
        for case in world['cases']:
            case['cache_before']=copy.deepcopy(old['cache_after']);case['cache_after']=copy.deepcopy(old['cache_after'])
            case['original_source_delta']={'added':{},'changed':{},'removed':{}}
            if case['role']=='stock':case['native_generation']=unexecuted_generation(case)
        first=copy.deepcopy(old);first['inherited_native_execution']=authority
        first['native_generation']=unexecuted_generation(first,inherited_authority=authority)
        world['cases'][0]=first
        return world

    def authenticated_unexecuted_mixed_world(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        path=Path(temporary.name)/'unexecuted-mixed-world.zip';world=self.unexecuted_mixed_world();raw=derive.metadata.encoded(world)
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as archive:archive.writestr('world.json',raw)
        inputs={**copy.deepcopy(self.inputs),'native_world':{'repository_commit':derive.RESUME_SOURCE,'run_id':1,'artifact_id':2,
            'artifact_zip':derive.pin(path.read_bytes()),'member':'world.json','member_pin':derive.pin(raw)},
            derive.INHERITED_INPUT:copy.deepcopy(self.inherited_input)}
        return derive.authenticate_inputs({**self.paths,'native_world':path,derive.INHERITED_INPUT:self.inherited_path},inputs),inputs

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

    def test_reviewed_current_qualifier_identity_matches_actual_committed_source(self):
        self.assertEqual(derive.RESUME_SOURCE,'3a713dc278d9247a65fb2357447adb5353c0a577')
        raw=subprocess.check_output(['git','show',derive.RESUME_SOURCE+':tools/android/interactive/qualify_native_map_world_037.py'],cwd=derive.ROOT)
        self.assertEqual(derive.pin(raw),derive.RESUME_QUALIFIER)
        self.assertEqual(derive.RESUME_QUALIFIER,{'bytes':81189,
            'sha256':'814b01b739d1fed55ecafb739c8dba58c421c0cf74ce2aab825a018cac9aa290'})
        self.assertIn(b"require(os.name=='nt','Genuine world gate requires Windows')",raw)
        self.assertEqual(derive.INHERITED_STOCK['source'],'04b7a623ef21d7ad48774a58b3122c69ae07f46b')

    def test_actual_failed_b323_is_rejected_and_old_resume_source_cannot_be_relabelled(self):
        raw=(RECOVERY/'map-b323-world-evidence.zip').read_bytes()
        self.assertEqual(derive.pin(raw),{'bytes':4582240,
            'sha256':'f6d50773cbeab72ff9afd989e95348fd4481f1f9bc8ebdd67338661f835bde77'})
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            failed=derive.json_document(archive.read(derive.WORLD_REPORT_MEMBER),role='native_world')
            partial=derive.json_document(archive.read('failed-native-observations.json'))
        self.assertEqual(failed['repository_commit'],'b3239ed001cd75a92910731710b7675506cf1944')
        self.assertEqual(failed['status'],'failed');self.assertEqual(len(failed['cases']),1)
        self.assertEqual(partial['case'],'1-server_only-baseline-forward')
        self.assertTrue(partial['last_readiness_observation']['Server_ready_stdout_observed'])
        self.assertNotIn('cache_dates_after',partial)
        with self.assertRaises(ValueError):derive.inspect_world(failed,self.narrow)
        world=self.unexecuted_mixed_world()
        world['repository_commit']='b3239ed001cd75a92910731710b7675506cf1944'
        world['source_pins']['tools/android/interactive/qualify_native_map_world_037.py']={'bytes':78316,
            'sha256':'caf775548a64e163b37ddba95dce931626768d1cf3c2bfe0366db6e20f58ecd5'}
        with self.assertRaisesRegex(ValueError,'reviewed fresh resume source'):
            derive.inspect_world(world,self.narrow,inherited_world=self.old_report,
                inherited_descriptor=self.inherited_input,inherited_auxiliary=self.old_auxiliary)

    def test_actual_failed04b_original_and_unexecuted_mixed_lineage_preserve_ready_case(self):
        docs,inputs=self.authenticated_unexecuted_mixed_world()
        result=derive.inspect_world(docs['native_world'],self.narrow,inherited_world=docs[derive.INHERITED_INPUT],
            inherited_descriptor=inputs[derive.INHERITED_INPUT],inherited_auxiliary=docs.inherited_auxiliary)
        lineage=result['execution_lineage'];self.assertEqual(lineage['fresh_native_processes'],15)
        self.assertEqual(lineage['inherited_native_world_processes'],1);self.assertEqual(len(result['eligible']),106)
        self.assertNotIn('data/bin/fxinfo.bin',result['eligible'])
        self.assertIn({'name':'data/bin/fxinfo.bin','reason':'original_donor_output_changed_in_world'},result['excluded_world_tokens'])
        self.assertEqual(docs[derive.INHERITED_INPUT]['status'],'failed')
        self.assertEqual(lineage['inherited_stock_authority']['original_overall_result'],'failed')
        self.assertFalse(lineage['inherited_stock_authority']['stock_native_readiness_reexecuted'])
        self.assertEqual(lineage['stock_generation_absence_validation'][0]['negative_dependency_rows'],136)

    def test_inherited_stock_old_facts_source_counts_auxiliary_or_absence_substitution_rejected(self):
        for field in ('fresh16','missing_inherited','second_inherited','old_tick','old_command','old_source','old_result',
                'resume_source','qualifier','namespace','zero_actual_source','nonzero_missing','negative_count','original_inventory','sql'):
            world=copy.deepcopy(self.unexecuted_mixed_world());old=copy.deepcopy(self.old_report);aux=copy.deepcopy(self.old_auxiliary)
            first=world['cases'][0];negative=first['native_generation']['native_negative_source_dependencies']
            if field=='fresh16':world['actual_native_processes']=16
            elif field=='missing_inherited':first.pop('inherited_native_execution')
            elif field=='second_inherited':world['cases'][1]['inherited_native_execution']=first['inherited_native_execution']
            elif field=='old_tick':first['Map_progress_after_status']['tick_completed']+=1
            elif field=='old_command':first['command'].append('-unexecuted-substitution')
            elif field=='old_source':old['repository_commit']='9'*40
            elif field=='old_result':old['status']='passed'
            elif field=='resume_source':world['repository_commit']='9'*40
            elif field=='qualifier':world['source_pins']['tools/android/interactive/qualify_native_map_world_037.py']['sha256']='9'*64
            elif field=='namespace':negative['namespace']['external_directory_controls_refused']=False
            elif field=='zero_actual_source':next(iter(first['native_generation']['actual_dependency_sources'].values()))[0]['actual_source']=derive.pin(b'fake')
            elif field=='nonzero_missing':next(iter(first['native_generation']['actual_dependency_sources'].values()))[0]['native_dependency_timestamp']=1
            elif field=='negative_count':negative['rows']=True
            elif field=='original_inventory':negative['original_complete_provider_membership_sha256']='9'*64
            else:aux['failed_observations']['synthetic_profile']['unchanged']=False
            with self.subTest(field=field),self.assertRaises(ValueError):
                derive.inspect_world(world,self.narrow,inherited_world=old,
                    inherited_descriptor=self.inherited_input,inherited_auxiliary=aux)

    def test_inherited_original_artifact_and_post_auth_auxiliary_mutation_fail_closed(self):
        docs,inputs=self.authenticated_unexecuted_mixed_world()
        changed=copy.deepcopy(inputs[derive.INHERITED_INPUT]);changed['artifact_zip']['sha256']='9'*64
        with self.assertRaises(ValueError):derive.input_descriptor(changed,derive.INHERITED_INPUT)
        docs.inherited_auxiliary['failed_observations']['synthetic_profile']['unchanged']=False
        with self.assertRaisesRegex(ValueError,'auxiliary evidence mutated'):
            derive.derive_proof(docs,raw_inputs=inputs,derivation_source={},source_review={})

    def test_unexecuted_mixed_derivation_records15_fresh1_inherited_and_external_output_pin(self):
        docs,inputs=self.authenticated_unexecuted_mixed_world()
        script=(derive.ROOT/derive.SCRIPT).read_bytes()
        source={'repository_commit':'8'*40,'path':derive.SCRIPT,'git_blob':hashlib.sha1(b'blob '+str(len(script)).encode()+b'\0'+script).hexdigest(),
            'pin':derive.pin(script)}
        proof,outer=derive.derive_proof(docs,raw_inputs=inputs,derivation_source=source,
            source_review=derive.startup.SOURCE_ONLY_COMPATIBILITY_REVIEW['descriptor'])
        lineage=proof['native_world_execution_lineage']
        self.assertEqual(lineage['fresh_native_processes'],15);self.assertEqual(lineage['inherited_native_world_processes'],1)
        self.assertEqual(lineage['inherited_stock_authority']['source'],derive.INHERITED_STOCK['source'])
        self.assertEqual(lineage['fresh_qualifier_raw_input'],inputs['native_world'])
        self.assertEqual(len(proof['eligible_bins']),106)
        self.assertTrue(proof['observations_scope']['constructed_world_fixture'])
        self.assertEqual(proof['observations_scope']['native_world_timing_scope'],
            'unexecuted_controlled_world_fixture_no_native_timing_measurement')
        self.assertTrue(proof['observations_scope']['legacy_shared_preload_parser_timing_scope_preserved'])
        self.assertEqual(docs['preload']['observations']['timing_scope'],'host_Wine_wall_time_not_Android_or_Thor')
        self.assertNotIn('output',proof['derivation']);self.assertEqual(outer['output']['pin'],derive.pin(derive.metadata.encoded(proof)))
        self.assertFalse(proof['runtime_authority_created']);self.assertFalse(proof['shipping_allowed'])

    def test_production_entry_refuses_unexecuted_world_fixture_before_source_or_authority(self):
        docs,inputs=self.authenticated_unexecuted_mixed_world()
        # Recreate only a temporary controlled ZIP; original donor/preload and
        # old failed04b bytes are read without modification.
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'unexecuted.zip';raw=derive.metadata.encoded(docs['native_world'])
            with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as archive:archive.writestr('world.json',raw)
            inputs['native_world']['artifact_zip']=derive.pin(path.read_bytes())
            with self.assertRaisesRegex(ValueError,'explicitly unexecuted controlled world fixture'):
                derive.derive_from_artifacts({**self.paths,'native_world':path,derive.INHERITED_INPUT:self.inherited_path},
                    raw_inputs=inputs,derivation_source={},source_review={})

    def test_only_native_world_json_may_exceed8MiB_with64MiB_cap(self):
        raw=b'{"bounded_unexecuted_padding":"'+b'x'*(8*1024**2)+b'"}'
        self.assertEqual(len(derive.json_document(raw,role='native_world')['bounded_unexecuted_padding']),8*1024**2)
        for role in (None,'preload',derive.INHERITED_INPUT,'client_cache_manifest','server_cache_manifest'):
            with self.subTest(role=role),self.assertRaises(ValueError):derive.json_document(raw,role=role)
        descriptor={**self.inherited_input,'repository_commit':'7'*40,'run_id':1,'artifact_id':2,
            'member_pin':{'bytes':64*1024**2+1,'sha256':'7'*64}}
        with self.assertRaises(ValueError):derive.input_descriptor(descriptor,'native_world')
        for raw in (b'{"x":1,"x":2}',b'{"x":NaN}'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):derive.json_document(raw,role='native_world')

    def test_guest_raw_material_contract_binds_inherited_original_and_only_world64MiB(self):
        inputs=copy.deepcopy(self.inputs)
        inputs['native_world']={'repository_commit':derive.RESUME_SOURCE,'run_id':1,'artifact_id':2,
            'artifact_zip':derive.pin(b'unexecuted fixture ZIP'),'member':'world.json',
            'member_pin':{'bytes':16*1024**2,'sha256':'7'*64}}
        inputs[derive.INHERITED_INPUT]=copy.deepcopy(self.inherited_input)
        descriptor={'derivation_source':{'repository_commit':'8'*40,'path':derive.SCRIPT,'git_blob':'8'*40,
            'pin':derive.pin((derive.ROOT/derive.SCRIPT).read_bytes())},'raw_inputs':inputs,
            'output':{'filename':derive.OUTPUT_NAME,'pin':derive.pin(b'unexecuted compact proof')},
            'scope':derive.DERIVATION_SCOPE}
        with patch.object(derive.startup,'RUNTIME_CACHE_PROOF_DERIVATION',descriptor):
            self.assertEqual(derive.startup.inspect_runtime_cache_derivation(descriptor),descriptor)
        for field in ('inherited_source','inherited_extent','preload_extent','world_extent'):
            changed=copy.deepcopy(descriptor)
            if field=='inherited_source':changed['raw_inputs'][derive.INHERITED_INPUT]['repository_commit']='9'*40
            elif field=='inherited_extent':changed['raw_inputs'][derive.INHERITED_INPUT]['member_pin']['bytes']=16*1024**2
            elif field=='preload_extent':changed['raw_inputs']['preload']['member_pin']['bytes']=16*1024**2
            else:changed['raw_inputs']['native_world']['member_pin']['bytes']=64*1024**2+1
            with self.subTest(field=field),patch.object(derive.startup,'RUNTIME_CACHE_PROOF_DERIVATION',changed),self.assertRaises(ValueError):
                derive.startup.inspect_runtime_cache_derivation(changed)

    def test_native_dependency_names_preserve_actual_ampersands_and_empty_original_inputs(self):
        name='object_library/common_decor/common_items/desks_&_tables/desks_&_tables.txt'
        self.assertEqual(derive.source_dependency_name(name),name)
        self.assertFalse(derive.metadata.material_member_name(name))
        self.assertEqual(derive.source_dependency_pin(derive.pin(b'')),derive.pin(b''))
        for name in ('../escaped.txt','object_library/a:stream.txt','object_library/a/CON.txt',
                'object_library/a/link\\file.txt','object_library/a/file.txt.','object_library/a/<bad>.txt'):
            with self.subTest(name=name),self.assertRaises(ValueError):derive.source_dependency_name(name)
        with self.assertRaises(ValueError):derive.source_dependency_pin({'bytes':True,'sha256':'7'*64})
        with self.assertRaises(ValueError):derive.source_dependency_pin({'bytes':0,'sha256':'7'*64})

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
