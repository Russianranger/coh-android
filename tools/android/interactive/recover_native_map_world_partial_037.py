#!/usr/bin/env python3
"""Authenticate individual native receipts from the CANCELLED original 3a run.

No whole-run pass or global cleanup is invented. Old execution stays inherited.
This module neither executes native processes nor grants Android cache admission.
"""
import copy
import hashlib
import json
from pathlib import Path
import stat
import tarfile
import io
import os
import zipfile
import qualify_native_map_world_037 as world

SOURCE='3a713dc278d9247a65fb2357447adb5353c0a577'
RUN=38505018109
JOB=115661338474
ARTIFACT=11873697327
ZIP_PIN={'bytes':11241142,'sha256':'957d534c3a7122d177616a55e2c758363b296000b73ebc6ba2c158696b9724c8'}
QUALIFIER_PIN={'bytes':81189,'sha256':'814b01b739d1fed55ecafb739c8dba58c421c0cf74ce2aab825a018cac9aa290'}
LABELS=('1-server_only-generation','1-server_only-baseline-forward',
 '1-server_only-candidate-forward','1-server_only-candidate-reverse','1-server_only-baseline-reverse',
 '1-full-generation','1-full-baseline-forward','1-full-candidate-forward','5-server_only-generation')
NATIVE={
 'stock':{'bytes':7477248,'sha256':'77c1f245132b76668e9f689bec26699ec980382c1079f000314d24b149e089ea'},
 'baseline':{'bytes':7478784,'sha256':'fbfcf1d80a41a80aaeecb1a0ec275daffed2a9e1ba25df3f16e23b16a51a493d'},
 'candidate':{'bytes':7480832,'sha256':'5927f87fdac50c5a839ac067ccbb34b5dfad6223e579287a66a2f866a7d4b2e6'}}
require=world.require


def raw_pin(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def read_archive(path):
    require(world.pin(path)==ZIP_PIN,'Exact cancelled-run public artifact bytes required')
    values={}
    with zipfile.ZipFile(path) as archive:
        require(len(archive.namelist())==157 and len(set(archive.namelist()))==157,
                'Exact original partial artifact membership required')
        total=0
        for member in archive.infolist():
            world.inputs.safe_windows_name(member.filename)
            require(not member.is_dir() and not member.flag_bits&1
                    and stat.S_IFMT(member.external_attr>>16) in (0,stat.S_IFREG),
                    'Unsafe original partial artifact member')
            require(0<=member.file_size<=64*1024**2,'Partial member bound exceeded')
            total+=member.file_size;require(total<=256*1024**2,'Partial artifact bound exceeded')
            values[member.filename]=archive.read(member)
    require(world.REPORT not in values,'Cancelled run must not acquire fabricated final report')
    return values


def json_value(values,name):
    require(name in values and len(values[name])<=8*1024**2,'Missing/bounded case JSON required: '+name)
    return json.loads(values[name])


def decisions(observations):
    return ([(r['phase'],r['input_token'],r['success']) for r in observations['profile_rows']],
            [(r['input_token'],r['outcome']) for r in observations['freshness_rows']])


def audit_case(values,label):
    facts=json_value(values,label+'/phase.json');before=json_value(values,label+'/before-launch.json')
    expected_label=str(facts['map_id'])+'-'+facts['fx_variant']+'-'+facts['phase']
    require(expected_label==label and facts['actual_native']==NATIVE[facts['role']],
            'Original selected case/native producer differs')
    for name,key in (('native','actual_native'),('cache','cache_before'),('cache_dates_before','cache_dates_before'),('provider','provider_before')):
        require(before[name]==facts[key],'Original prelaunch witness differs')
    require(facts['provider_before']==facts['provider_after']
            and all(not v for v in facts['original_source_delta'].values()),
            'Original native/source/SDK/identifier/world/graph inventory changed')
    require(facts['synthetic_row_unchanged'] is True and facts['owned_cleanup_verified'] is True,
            'Per-case SQL and held cleanup proof required')
    require(facts['Map_progress_after_status']['tick_completed']>facts['Map_progress_before_status']['tick_completed']
            and facts['Map_progress_after_status']['sequence']>facts['Map_progress_before_status']['sequence']
            and facts['Db_progress_after_status']['loop_count']>facts['Db_progress_before_world']['loop_count'],
            'Original independent native Map and Db advancement missing')
    require(facts['native_Db_status']['map_id']==facts['map_id']
            and facts['native_Db_status']['world']==world.WORLDS[facts['map_id']][0]
            and facts['native_Db_status']['port']==world.WORLDS[facts['map_id']][1]
            and facts['native_Db_status']['address']=='127.0.0.1'
            and facts['world_markers']['PhysX_objects']==world.WORLDS[facts['map_id']][2]
            and facts['world_markers']['ordered_world_phases'] is True,
            'Original actual selected world/status/physics evidence differs')
    require(len(facts['cache_after'])<=world.MAX_WORLD_CACHES
            and set(facts['cache_after'])==set(facts['cache_dates_after']),
            'Complete original bounded cache/date census required')
    generation=None
    if facts['role']=='stock':
        generation=json_value(values,label+'/generation.json')
        require(generation['delta']==facts['cache_delta']
                and generation['existing_decoded_payload_and_schema_unchanged'] is True
                and generation['Android_cache_authority_created'] is False,
                'Original stock generation closure/body proof differs')
        producer=generation['actual_stock_producer']
        require(producer['native']==facts['actual_native'] and producer['map_id']==facts['map_id']
                and producer['native_Db_status']==facts['native_Db_status']
                and producer['world_initialization_markers']==facts['world_markers']
                and producer['provider_native_components']==facts['provider_after']['native_components'],
                'Original actual stock producer authority differs')
        retention=facts['native_generated_output_retention']
        archive_name=label+'/stock-native-generated-cache-outputs.tar.gz'
        if label=='1-server_only-generation':archive_name='inherited-stock-04b/'+archive_name
        require(archive_name in values and raw_pin(values[archive_name])==retention['archive'],
                'Original actual generated cache bytes missing')
    else:
        require(facts['cache_before']==facts['cache_after']
                and facts['cache_dates_before']==facts['cache_dates_after']
                and all(not v for v in facts['cache_delta'].values()),
                'Warm cache bytes or native 100ns dates changed')
        candidates=[(n,r) for n,r in values.items() if n.startswith(label+'/log-')
                    and b'COH_NATIVE_STARTUP_PROFILE_V1' in r and b'Server ready.' in r]
        require(len(candidates)==1,'Exact original current native stdout required')
        name,raw=candidates[0];observations=world.world_native_observations(raw,facts['map_id'])
        reported=facts['native_observations']
        for key in ('profile_rows','freshness_rows','native_world_console_framing'):
            require(observations[key]==reported[key],'Actual original strict profiler/framing rows differ')
        require(world.world_markers(raw.decode('utf-8','replace'),facts['map_id'])==facts['world_markers'],
                'Actual original native world console differs')
        require(world.FX_consumption(observations,facts['fx_variant'],facts['cache_before']['data/bin/fxinfo.bin'])
                ==facts['actual_FX_BIN_consumption'],'Actual original FX consumer differs')
        if facts['role']=='candidate':
            require(world.profiles.prefetch_observation(raw)==reported['metadata_prefetch'],
                    'Actual original metadata prefetch evidence differs')
        else:require(b'COH_MAP_ANIMATION_METADATA_PREFETCH_V1' not in raw,'Original baseline enabled candidate')
        require(world.animation_consumption(raw,world.ANIMATION_PIG)==facts['actual_certified_animation_consumption'],
                'Actual original certified animation subset differs')
    result=copy.deepcopy(facts)
    result['recovered_individual_case_authority']={
        'source':SOURCE,'run_id':RUN,'job_id':JOB,'artifact_id':ARTIFACT,'artifact':ZIP_PIN,
        'qualifier':QUALIFIER_PIN,'phase':raw_pin(values[label+'/phase.json']),
        'original_run_result':'cancelled','original_final_report_present':False,
        'global_cleanup_claimed':False,'individual_raw_gate_revalidation':'passed',
        'native_process_reexecuted':False,'native_execution_inherited':True,
        'original_native_source_and_fields_preserved':True}
    result['recovered_individual_case_authority']['native_execution_source']=(
        facts.get('inherited_native_execution') or {}).get('source',SOURCE)
    if generation is not None:
        result['recovered_individual_case_authority']['generation']=raw_pin(values[label+'/generation.json'])
        result['native_generation']=generation
    return result


def recover(path):
    values=read_archive(path);facts=[audit_case(values,label) for label in LABELS]
    require(len({world.digest(v['schema_snapshot']) for v in facts})==1,'Original SQL schemas differ')
    for variant in ('server_only','full'):
        selected=[v for v in facts if v['map_id']==1 and v['fx_variant']==variant]
        producer=next(v for v in selected if v['role']=='stock');control=None
        for consumer in selected:
            if consumer['role']=='stock':continue
            require(consumer['cache_before']==producer['cache_after']
                    and consumer['cache_dates_before']==producer['cache_dates_after'],
                    'Original warm consumer is not the exact stock bytes/date closure')
            observed=decisions(consumer['native_observations'])
            if control is None:control=observed
            require(observed==control,'Original ordered decoder/freshness parity differs')
    geo=lambda v:{n:r for n,r in v['cache_after'].items() if n.startswith('data/geobin/')}
    require(geo(facts[0])==geo(facts[5]),'Actual original Atlas full/SERVER geometry differs')
    return {'original_run_result':'cancelled','original_global_cleanup_verified':False,
            'original_final_report_present':False,'recovered_individual_cases':facts,
            'inherited_04b_native_cases':1,'inherited_3a_native_cases':8,
            'remaining_fresh_native_cases':7,'all_16_case_qualification_complete':False,
            'behavioral_collision_proven':False,'physical_device_executed':False,
            'shipping_allowed':False},values


def restore_Kings_stock(runtime,before,before_dates,provider_before,raw_before,original_sources,recovered,values,output):
    """Restore only the captured authentic Kings stock cache; no native replay."""
    runtime,output=Path(runtime),Path(output)
    original=next(v for v in recovered['recovered_individual_cases'] if v['map_id']==5)
    require(original['fx_variant']=='server_only' and original['role']=='stock'
            and before==original['cache_before'] and before_dates==original['cache_dates_before']
            and provider_before==original['provider_before'],
            'Fresh Kings source/SDK/BIN/date inputs differ from actual stock producer')
    retention=original['native_generated_output_retention'];members=retention['members']
    changed=set(original['cache_delta']['added'])|set(original['cache_delta']['changed'])
    require(set(members)==changed and len(members)<=world.MAX_WORLD_CACHES,
            'Exact original Kings generated output closure required')
    raw=values['5-server_only-generation/stock-native-generated-cache-outputs.tar.gz']
    require(raw_pin(raw)==retention['archive'],'Actual captured Kings generation archive differs')
    seen=set()
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        for member in archive:
            world.budget_check('restore authenticated Kings stock cache')
            require(member.name in members and member.name not in seen and member.isfile()
                    and not member.issym() and not member.islnk()
                    and (member.name in before or world.generated_cache_name(member.name)),
                    'Unsafe/unknown Kings stock checkout leaf')
            seen.add(member.name);expected=members[member.name]
            require(member.size==expected['bytes'],'Captured Kings generated size differs')
            target=world.native_path(runtime,member.name);target.parent.mkdir(parents=True,exist_ok=True)
            require(not target.is_symlink() and (not target.exists() or member.name in before
                and world.pin(target)==before[member.name]),'Kings checkout would overwrite an unknown/changed leaf')
            with archive.extractfile(member) as source,target.open('wb') as stream:
                import shutil
                shutil.copyfileobj(source,stream,1024**2)
            require(world.pin(target)=={k:expected[k] for k in ('bytes','sha256')},'Kings stock cache digest differs')
            os.utime(target,ns=(expected['mtime_ns'],expected['mtime_ns']))
    after=world.cache_snapshot(runtime);dates=world.cache_dates(runtime,after)
    require(seen==changed and after==original['cache_after'] and dates==original['cache_dates_after'],
            'Complete restored Kings stock cache bytes/100ns dates differ')
    require(world.provider_snapshot(runtime,set(before)|set(after))==provider_before,
            'Restored Kings stock cache changed source/native/SDK inputs')
    proof=world.validate_generation_changes(runtime,before,after,raw_before,original_sources)
    require(proof['delta']==original['native_generation']['delta']
            and proof['existing_decoded_payload_and_schema_unchanged'] is True,
            'Fresh Kings stock restoration source/schema/body closure differs')
    proof['actual_stock_producer']=copy.deepcopy(original['native_generation']['actual_stock_producer'])
    proof['actual_stock_producer']['inherited_execution']=original['recovered_individual_case_authority']
    facts=copy.deepcopy(original);facts['native_generation']=proof
    facts['fresh_private_Kings_stock_restore']={'current_source_namespace_revalidated':True,
        'all_cache_bytes_and_100ns_dates_restored':True,'stock_native_process_reexecuted':False,
        'original_native_execution_source':SOURCE,'original_run_result':'cancelled'}
    world.write(output/'phase.json',facts);world.write(output/'generation.json',proof)
    return facts
