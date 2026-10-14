#!/usr/bin/env python3
"""Join nine authentic inherited cases and seven fresh Kings native cases.

This does not publish, admit an Android cache, or prove gameplay collision.
"""
import argparse
import copy
import json
from pathlib import Path
import re
import shutil
import stat
import qualify_native_map_world_037 as world
import recover_native_map_world_partial_037 as partial

require=world.require


def read_json(path,maximum=64*1024**2):
    path=Path(path);info=path.lstat()
    require(stat.S_ISREG(info.st_mode) and not path.is_symlink() and info.st_nlink==1
            and info.st_size<=maximum,'Bounded ordinary JSON input required')
    return json.loads(path.read_bytes())


def native_case_ok(case,map_id,variant):
    require(case['map_id']==map_id and case['fx_variant']==variant
            and case['world_markers']['PhysX_objects']==world.WORLDS[map_id][2]
            and case['native_Db_status']['port']==world.WORLDS[map_id][1]
            and case['native_Db_status']['map_id']==map_id
            and case['synthetic_row_unchanged'] is True and case['owned_cleanup_verified'] is True,
            'Selected native world/SQL/per-case cleanup proof required')
    require(case['Map_progress_after_status']['tick_completed']>case['Map_progress_before_status']['tick_completed']
            and case['Db_progress_after_status']['loop_count']>case['Db_progress_before_world']['loop_count'],
            'Independent current native ticks/status/Db progress required')
    require(case['provider_before']==case['provider_after']
            and all(not d for d in case['original_source_delta'].values()),
            'Complete source/SDK/native identity changed')
    if case['role']!='stock':
        require(case.get('whole_case_admitted_passed') is True
                and case['cache_before']==case['cache_after']
                and case['cache_dates_before']==case['cache_dates_after']
                and all(not d for d in case['cache_delta'].values()),
                'Actual complete byte/native-date warm gate required')
        require(case['closed_private_namespace_before']['full_namespace_verified'] is True
                and case['closed_private_namespace_after']['full_namespace_verified'] is True,
                'Full private-pool namespace custody proof required')


def require_map_animation_parity(cases,map_id):
    """Retain the original per-map animation gate across both FX pools."""
    selected=[case for case in cases if case['map_id']==map_id]
    require(selected,'Actual per-map animation consumers required')
    reference=None
    for case in selected:
        latest=case['actual_certified_animation_consumption']['latest_counters']
        identity={key:value for key,value in latest.items() if key not in ('hash_us','stock_us')}
        if reference is None:reference=identity
        require(identity==reference,
                'Native full/compact or prefetch variants changed observed animation subset')


def join(recovered,reports,run,jobs,artifacts,source):
    require(re.fullmatch('[0-9a-f]{40}',source) and run['head_sha']==source
            and run['head_branch']=='codex/native-map-world-037'
            and run['path']=='.github/workflows/android-native-map-world-037.yml',
            'Actual dedicated current source/run required')
    require(set(reports)=={'server_only','full'},'Both still-missing Kings pools required')
    original=copy.deepcopy(recovered['recovered_individual_cases']);cases=original[:8]
    pool_authorities=[];reference=None;current_sql=None
    for variant in ('server_only','full'):
        report,report_pin=reports[variant]
        expected=5 if variant=='server_only' else 3
        require(report['status']=='passed' and report['repository_commit']==source
                and report['selected_pool']=={'map_id':5,'fx_variant':variant}
                and report['selected_pool_only_verified'] is True
                and report['owned_cleanup_verified'] is True and len(report['cases'])==expected,
                'Actual complete selected pool must pass')
        require(report['actual_native_processes']==(4 if variant=='server_only' else 3),
                'Fresh native process counts differ from seven-case frontier')
        authority=report['native_execution_authority'];name='native-map-5-'+variant
        selected=[j for j in jobs['jobs'] if j['name']==name and j['id']==authority['job_id']]
        require(len(selected)==1 and selected[0]['status']=='completed' and selected[0]['conclusion']=='success'
                and authority['source']==source and authority['run_id']==run['id'],
                'Actual successful pool job/run authority differs')
        artifact_name='coh-native-world-037-pool-evidence-5-'+variant
        found=[a for a in artifacts['artifacts'] if a['name']==artifact_name]
        require(len(found)==1 and found[0]['expired'] is False
                and found[0]['workflow_run']['id']==run['id']
                and found[0]['workflow_run']['head_sha']==source
                and 0<found[0]['size_in_bytes']<=256*1024**2
                and re.fullmatch('sha256:[0-9a-f]{64}',found[0]['digest']),
                'Exact current pool artifact authority required')
        if reference is None:reference=report
        for key in ('public_APK','production_source','prepared_manifest','retained_native_build','candidate_native_build'):
            require(report[key]==reference[key],'Pool immutable producer/input authority differs')
        if current_sql is None:current_sql=report['schema_snapshot']
        require(report['schema_snapshot']==current_sql==original[0]['schema_snapshot'],
                'Original and current disposable native SQL schema differ')
        expected_plan=[x for x in world.phase_plan('base','candidate') if x[0]==variant]
        require([(c['phase'],c['role']) for c in report['cases']]==[(x[1],x[2]) for x in expected_plan],
                'Actual native pool case order/member closure differs')
        control=None
        for case in report['cases']:
            native_case_ok(case,5,variant)
            if case['role']=='stock':
                producer=case
                if variant=='server_only':
                    require(case['recovered_individual_case_authority']==original[8]['recovered_individual_case_authority'],
                            'Inherited original Kings stock identity was relabelled')
                continue
            require(case['cache_before']==producer['cache_after']
                    and case['cache_dates_before']==producer['cache_dates_after'],
                    'Current warm pool differs from exact authentic stock bytes/dates')
            observed=partial.decisions(case['native_observations'])
            if control is None:control=observed
            require(observed==control,'Current ordered decoder/freshness parity differs')
        pool_authorities.append({'map_id':5,'fx_variant':variant,'source':source,'run_id':run['id'],
            'job_id':authority['job_id'],'artifact_id':found[0]['id'],
            'artifact':{'bytes':found[0]['size_in_bytes'],'sha256':found[0]['digest'][7:]},
            'raw_pool_report':report_pin,'native_processes_fresh':report['actual_native_processes'],
            'host_phase_costs':report['host_phase_costs']})
        for case in report['cases']:
            if not (variant=='server_only' and case['role']=='stock'):
                case=copy.deepcopy(case);case['current_pool_artifact_authority']=pool_authorities[-1]
            cases.append(case)
    require(len(cases)==16,'All sixteen actual native cases remain mandatory')
    geo=lambda c:{n:r for n,r in c['cache_after'].items() if n.startswith('data/geobin/')}
    for map_id in (1,5):
        require_map_animation_parity(cases,map_id)
        stock=[c for c in cases if c['map_id']==map_id and c['role']=='stock']
        require(len(stock)==2 and geo(stock[0])==geo(stock[1]),
                'Actual full/SERVER geometry BIN/bounds parity differs')
        require(stock[0]['provider_after']['without_MapServer_sha256']==stock[1]['provider_after']['without_MapServer_sha256'],
                'Full/SERVER source/SDK/identifier/graph inputs differ')
    result={k:copy.deepcopy(reference[k]) for k in ('format','public_APK','production_source','prepared_manifest','retained_native_build','candidate_native_build')}
    result.update(status='passed',scope='actual_Windows_Atlas_Kings_world_initialization_and_geometry_parity',
        repository_commit=source,cases=cases,failures=[],actual_native_processes=7,
        inherited_native_world_processes=9,total_native_world_cases=16,
        inherited_04b_native_cases=1,inherited_3a_native_cases=8,
        actual_native_worlds_executed=[1,5],initialization_geometry_parity_verified=True,
        actual_full_and_SERVER_only_FX_world_consumers_verified=True,
        baseline_and_candidate_pairs_per_world={'server_only':2,'full':1},FX_variants=world.inputs.FX_VARIANTS,
        memory_measured=True,schema_snapshot=current_sql,
        original_3a_run_result='cancelled',original_3a_final_report_present=False,
        original_3a_global_cleanup_verified=False,original_04b_result='failed',
        current_pool_owned_cleanup_verified=True,owned_cleanup_verified=True,
        owned_cleanup_scope='each admitted old case and both current pools; original3a whole-job cleanup unproven',
        original_case_source_fields_and_timestamps_preserved=True,original_native_execution_relabelled_fresh=False,
        pool_artifact_authorities=pool_authorities,player_profile_opened=False,SQL_scope='new_disposable_fixture_only',
        behavioral_collision_proven=False,physical_device_executed=False,shipping_allowed=False,
        freshness_bypass_enabled=False,generated_cache_authorizes_Android_reuse=False,
        source_hashing_warms_host_filesystem_cache=True,provider_runtime_reused_for_fresh_Kings_cases=True)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('pools','output','run','jobs','artifacts','partial_world_evidence'):parser.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    parser.add_argument('--repository-commit',required=True);args=parser.parse_args()
    require(not args.output.exists(),'Fresh aggregate evidence directory required');args.output.mkdir()
    result={'format':1,'status':'failed','failures':[],'shipping_allowed':False,'all_16_case_gate_complete':False}
    try:
        recovered,original=partial.recover(args.partial_world_evidence);reports={}
        for variant in ('server_only','full'):
            root=args.pools/('coh-native-world-037-pool-evidence-5-'+variant)
            report_path=root/world.REPORT;reports[variant]=(read_json(report_path),world.pin(report_path))
        result=join(recovered,reports,read_json(args.run),read_json(args.jobs),read_json(args.artifacts),args.repository_commit)
        # Preserve each immutable original phase/console/stock proof exactly once.
        for name,raw in original.items():
            target=args.output/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        for variant in ('server_only','full'):
            root=args.pools/('coh-native-world-037-pool-evidence-5-'+variant)
            for path in sorted(root.rglob('*')):
                if path.is_dir():continue
                require(path.is_file() and not path.is_symlink() and path.stat().st_nlink==1,
                        'Unknown linked pool artifact input')
                relative=path.relative_to(root);world.inputs.safe_windows_name(relative.as_posix())
                if relative.as_posix()==world.REPORT:target=args.output/'pool-reports'/('5-'+variant+'.json')
                else:target=args.output/relative
                if target.exists():
                    # Recovered Kings stock carries fresh restoration facts separately.
                    target=args.output/'pool-restoration'/variant/relative
                target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
        result['source_pins']={Path(__file__).relative_to(world.ROOT).as_posix():world.pin(__file__),
            Path(partial.__file__).relative_to(world.ROOT).as_posix():world.pin(partial.__file__)}
    except Exception as error:result['failures'].append(type(error).__name__+': '+str(error)[-4000:])
    world.write(args.output/world.REPORT,result)
    require(result['status']=='passed','Complete native world aggregation failed; partial evidence retained')


if __name__=='__main__':main()
