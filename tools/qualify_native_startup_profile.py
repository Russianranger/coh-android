#!/usr/bin/env python3
"""Execute control/candidate MapServer TSR preloads in isolated owned Wine state.

Preload is deliberately not world readiness, collision parity or Game rendering.
No PostgreSQL or real character profile is opened. No timing here is Thor timing.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools/android/atlasgame'),str(ROOT/'android/guest')]
import prepare_server_caches as preload
import prepare_server_fx_catalog as fx
import package_native_startup_profile as package
from map_startup_namespace_certificate import require

REPORT='native-startup-profile-qualification.json'


def control_native_identity(control):
    # prepare_server_fx_catalog is the qualifier module; its `fx` member is
    # the shipped provider contract. Bind the already validated receipt too.
    require(control.get('mapserver')==fx.fx.MAPSERVER,'Authenticated control native producer differs')
    return control['mapserver']


def parse_observations(raw):
    require(isinstance(raw,bytes) and len(raw)<=64*1024**2,'Bounded native console required')
    text=raw.decode('utf-8','replace').replace('\r','')
    rows=[];freshness=[]
    for line in text.splitlines():
        if line.startswith('COH_NATIVE_STARTUP_PROFILE_V1 '):
            m=re.fullmatch(r'COH_NATIVE_STARTUP_PROFILE_V1 phase=(bin_decode|sequencer_postprocess|sequencer_finalize|sequencer_total) input_token=([0-9a-f]{8}) success=([01]) clock_valid=([01]) elapsed_us=([0-9]+)',line)
            require(m is not None,'Malformed native startup row')
            phase,token,success,valid,elapsed=m.groups()
            require(valid=='1' and int(elapsed)<2**64,'Invalid native startup clock')
            rows.append({'phase':phase,'input_token':token,'success':success=='1','elapsed_us':int(elapsed)})
        if line.startswith('COH_MAP_BIN_FRESHNESS_V1 '):
            fields=line.split()[1:];pairs=[field.split('=',1) for field in fields]
            require(all(len(p)==2 for p in pairs),'Malformed native freshness fields')
            row=dict(pairs)
            require(len(pairs)==len(row) and set(row)=={'ordinal','input_token','outcome','clock_valid',
                'open_us','dependencies_us','scan_us','dates_us','membership_us','cleanup_us'},'Native freshness row fields differ')
            require(row['clock_valid']=='1' and re.fullmatch('[0-9a-f]{8}',row['input_token'])
                and row['outcome'] in ('open_rejected','freshness_rejected','freshness_accepted'),
                'Invalid freshness clock, identity or production-mode bypass')
            for key in ('ordinal','open_us','dependencies_us','scan_us','dates_us','membership_us','cleanup_us'):
                require(re.fullmatch('0|[1-9][0-9]*',row[key]) and int(row[key])<2**64,'Freshness integer bounds differ')
                row[key]=int(row[key])
            freshness.append(row)
    require(0<len(rows)<=512 and 0<len(freshness)<=256,'Native bounded observations missing/exceeded')
    require([r['ordinal'] for r in freshness]==list(range(1,len(freshness)+1)),'Native freshness ordinals differ')
    for phase in ('sequencer_postprocess','sequencer_finalize','sequencer_total'):
        found=[r for r in rows if r['phase']==phase]
        require(len(found)==1 and found[0]['success'],'Complete native sequencer observation missing: '+phase)
    require(sum(r['phase']=='bin_decode' and r['success'] for r in rows)>=10,'Native BIN decoder did not execute enough actual inputs')
    return {'profile_rows':rows,'freshness_rows':freshness,
        'timing_scope':'host_Wine_wall_time_not_Android_or_Thor',
        'native_decoder_executed':True,'native_sequencer_postprocess_executed':True,
        'freshness_bypass_enabled':False,'cache_authority_created':False}


def cache_snapshot(runtime):
    result={}
    for relative in ('data/bin','data/server/bin'):
        root=runtime/relative
        require(root.is_dir() and not root.is_symlink(),'Private cache directory required')
        for path in sorted(root.rglob('*.bin')):
            require(len(result)<512,'Native cache inventory exceeds bound')
            result[path.relative_to(runtime).as_posix()]=package.pin(path)
    require(result and 'data/bin/sequencers.bin' in result,'Sequencer cache missing')
    return result


def prefetch_observation(raw):
    require(isinstance(raw,bytes) and len(raw)<=64*1024**2,'Bounded candidate native console required')
    lines=[line for line in raw.decode('utf-8','replace').replace('\r','').splitlines()
        if line.startswith('COH_MAP_ANIMATION_METADATA_PREFETCH_V1')]
    require(len(lines)==1,'Exactly one executed candidate sequencer metadata request required')
    match=re.fullmatch(r'COH_MAP_ANIMATION_METADATA_PREFETCH_V1 tree=player_library/animations cache=bin/sequencers.bin milliseconds=([0-9]+\.[0-9]{3}) source_freshness_preserved=1 crc_validation_preserved=1',lines[0])
    require(match is not None and 0<=float(match[1])<=3600000,'Bounded exact native metadata request record required')
    return {'request_count':1,'tree':'player_library/animations','cache':'bin/sequencers.bin',
        'milliseconds':float(match[1]),'provider_authority_created':False}


def qualify(args):
    require(re.fullmatch('[0-9a-f]{40}',args.repository_commit) and 30<=args.timeout_seconds<=3600,
            'Exact source and bounded host qualification duration required')
    if getattr(args,'reuse_completed_windows_package',False):
        import reuse_native_startup_profile as reuse
        build=reuse.validate_package(args.package)
        native_reuse=reuse.provenance()
    else:
        build=package.validate(args.package,args.repository_commit)
        native_reuse=None
    require(bool(getattr(args,'native_prefetch_package',None))==bool(getattr(args,'native_prefetch_commit',None)),
        'Candidate package and source must be provided together')
    candidate=None
    if getattr(args,'native_prefetch_package',None) is not None:
        import package_native_map_prefetch as prefetch_package
        require(native_reuse is not None,'Prefetch experiment requires exact retained observed control')
        candidate=prefetch_package.validate(args.native_prefetch_package,args.native_prefetch_commit,args.package)
    require(not args.work.exists() and not args.output.exists(),'Fresh isolated native qualification directories required')
    args.work=args.work.resolve();args.output=args.output.resolve();args.runtime=args.runtime.resolve()
    control=fx.validate_control_fixture(package.read(args.control_fixture))
    require(str(args.runtime)==control['runtime_host_path'],'Authenticated control provider path differs')
    require(package.pin(args.runtime/'MapServer.exe')==control_native_identity(control),
        'Original complete fixture native producer differs')
    args.work.mkdir(parents=True);args.output.mkdir(parents=True);(args.output/'evidence').mkdir()
    package.write(args.output/'control-fixture.json',control)
    launcher=args.output/'evidence/server-cache-launcher.exe'
    with (args.output/'evidence/launcher-build.log').open('wb') as log:
        subprocess.run(['i686-w64-mingw32-gcc','-O2','-Wall','-Wextra','-Werror','-static-libgcc',
            str(ROOT/'android/native/server-cache-launcher.c'),'-o',str(launcher)],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    env=dict(os.environ,WINEARCH='win32',WINEPREFIX=str(args.work/'wine-prefix'),WINEDEBUG='-all',
        WINEDLLOVERRIDES='winemenubuilder.exe=d;mscoree=d;mshtml=d',TZ='UTC',LANG='C.UTF-8')
    env.pop(fx.source.ENVIRONMENT,None)
    env.pop('COH_MAP_ANIMATION_METADATA_PREFETCH',None)
    with (args.output/'evidence/wine-initialization.log').open('wb') as log:
        subprocess.run([args.wine,'wineboot','--init'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    initialized=args.output/'evidence/prefix-initialization';initialized.mkdir()
    preload.stop_owned_prefix(env,initialized,normal_launcher_exit_observed_first=False)
    records={};outputs={}
    native_cases=(('control',args.package/'MapServer-control.exe'),('profile',args.package/'MapServer-profile.exe'))
    if candidate is not None:
        native_cases=(('control',args.package/'MapServer-profile.exe'),
            ('profile',args.native_prefetch_package/prefetch_package.BINARY))
    for stage,native in native_cases:
        runtime=args.work/stage;shutil.copytree(args.runtime,runtime,symlinks=True)
        require(not (runtime/'piggs/texts.pigg').exists(),'Native profiler requires original development freshness')
        target=runtime/'MapServer.exe';require(not target.is_symlink(),'Private native destination required')
        target.chmod(0o600);shutil.copyfile(native,target)
        native_pin=package.pin(target);before=cache_snapshot(runtime)
        ids_before=preload.package.identifier_snapshot(runtime/'data')
        prelaunch=args.output/'evidence'/(stage+'-before-launch.json')
        package.write(prelaunch,{'cache':before,'identifiers':ids_before,'actual_native':native_pin})
        phase_env=dict(env)
        native_source=build['repository_commit']
        if candidate is not None and stage=='profile':
            phase_env['COH_MAP_ANIMATION_METADATA_PREFETCH']='1'
            native_source=candidate['repository_commit']
        try:
            phase=preload.run_phase(args,runtime,launcher,phase_env,args.output,stage,
                {'qualification_source':args.repository_commit,'native_source':native_source,
                 'native':native_pin},trace=False)
        except BaseException:
            failure=args.output/'evidence'/(stage+'-failure-cleanup');failure.mkdir(exist_ok=True)
            try:preload.stop_owned_prefix(env,failure,normal_launcher_exit_observed_first=False)
            except Exception as cleanup:package.write(failure/'cleanup-error.json',{'error':str(cleanup),'passed':False})
            raise
        native_after=package.pin(target);ids_after=preload.package.identifier_snapshot(runtime/'data')
        after=cache_snapshot(runtime)
        # Persist actual executed identities and deltas before any failure gate.
        # Both isolated original-fixture preloads may collect diagnostics; cache
        # mutations still prevent qualification and never authorize reuse.
        snapshots={'before':before,'after':after,
            'added':{n:after[n] for n in after.keys()-before.keys()},
            'removed':{n:before[n] for n in before.keys()-after.keys()},
            'changed':{n:{'before':before[n],'after':after[n]} for n in before.keys()&after.keys() if before[n]!=after[n]}}
        package.write(args.output/'evidence'/stage/'cache-snapshots.json',snapshots)
        package.write(args.output/'evidence'/stage/'identifier-snapshots.json',{'before':ids_before,'after':ids_after})
        package.write(args.output/'evidence'/stage/'native-executable-snapshots.json',{'before':native_pin,'after':native_after})
        # The legacy preload receipt carries a historical hard-coded executable
        # field; bind this new independent report to the actual binary we ran.
        phase['legacy_receipt_historical_mapserver_sha256']=phase.pop('mapserver_sha256')
        phase['actual_mapserver']=native_pin
        package.write(args.output/'evidence'/stage/'phase-receipt.json',phase)
        require(native_after==native_pin,'Native diagnostic binary changed during execution')
        require(ids_before==ids_after,'Native preload altered identifiers')
        stdout=(args.output/'evidence'/stage/'stdout.log').read_bytes()
        if stage=='profile' or candidate is not None:outputs[stage]=parse_observations(stdout)
        else:require(b'COH_NATIVE_STARTUP_PROFILE_V1' not in stdout,'Control unexpectedly contains profiler')
        if candidate is not None and stage=='profile':outputs[stage]['metadata_prefetch']=prefetch_observation(stdout)
        else:require(b'COH_MAP_ANIMATION_METADATA_PREFETCH_V1' not in stdout,'Control unexpectedly prefetched candidate metadata')
        records[stage]={'phase':phase,'cache_before':before,'cache_after':after,
            'identifiers_before':ids_before,'identifiers_after':ids_after,'actual_native':native_pin,
            'cache_input_unchanged':before==after,'cache_delta':{k:snapshots[k] for k in ('added','removed','changed')}}
    if not all(r['cache_input_unchanged'] for r in records.values()):
        package.write(args.output/REPORT,{'format':1,'status':'failed',
            'failure':'original_prepared_BIN_inventory_changed','publication_allowed':False,
            'repository_commit':args.repository_commit,'native_package_source_commit':build['repository_commit'],
            'native_preload_processes':len(records),'actual_Wine_native_preload_executed':True,
            'cache_reuse_qualified':False,'native_world_executed':False,'physical_device_executed':False,
            'retained_native_build':native_reuse,'records':records,'observations':outputs,
            'scope':'diagnostic only; native cache generation requires a separate explicit producer and qualification'})
        raise ValueError('Diagnostic/native preload wrote or changed prepared BIN inputs; exact per-stage deltas retained')
    require(records['control']['cache_after']==records['profile']['cache_after'],'Control/profile BIN output parity failed')
    require(records['control']['phase']['definition_counts']==records['profile']['phase']['definition_counts'],
            'Control/profile native definition counts differ')
    if candidate is not None:
        def decisions(value):
            return ([(r['phase'],r['input_token'],r['success']) for r in value['profile_rows']],
                [(r['input_token'],r['outcome']) for r in value['freshness_rows']])
        require(decisions(outputs['control'])==decisions(outputs['profile']),
            'Native metadata prefetch changed decoder/freshness decision ordering')
    value={'format':1,'role':'nonshipping_native_startup_profile_Wine_preload_parity','status':'passed',
        'repository_commit':args.repository_commit,'native_package_source_commit':build['repository_commit'],
        'retained_native_build':native_reuse,'build_package':package.pin(args.package/package.MANIFEST),
        'publication_allowed':False,'native_preload_processes':2,'actual_Wine_native_preload_executed':True,
        'map_world_entry_executed':False,'native_game_executed':False,'atlas_kings_collision_parity_executed':False,
        'physical_device_executed':False,'player_database_used':False,'PostgreSQL_started':False,
        'records':records,'observations':outputs['profile'],'scope':'Completed TSR definition preload and exact BIN/identifier parity only; no maps or gameplay',
        'caveat':'Elapsed host wall times include emulator/system work and are not comparable to Thor measurements',
        'source_files':{n:package.pin(ROOT/n) for n in ('tools/qualify_native_startup_profile.py','android/native/server-cache-launcher.c',
            *(('tools/reuse_native_startup_profile.py',) if native_reuse is not None else ()))}}
    if candidate is not None:
        value.update(role='nonshipping_map_metadata_prefetch_Wine_preload_parity',
            candidate_native_package_source_commit=candidate['repository_commit'],
            candidate_package=package.pin(args.native_prefetch_package/prefetch_package.MANIFEST),
            control_observations=outputs['control'],native_prefetch_execution_validated=True)
        for name in ('tools/package_native_map_prefetch.py','tools/prepare_native_map_metadata_prefetch_source.py'):
            value['source_files'][name]=package.pin(ROOT/name)
    package.write(args.output/REPORT,value)
    return value


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('package','runtime','control-fixture','work','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--repository-commit',required=True);p.add_argument('--wine',default='wine');p.add_argument('--timeout-seconds',type=int,default=1800)
    p.add_argument('--reuse-completed-windows-package',action='store_true')
    p.add_argument('--native-prefetch-package',type=Path)
    p.add_argument('--native-prefetch-commit')
    value=qualify(p.parse_args());print(json.dumps({'status':value['status'],'publication_allowed':False,'native_preload_processes':2}))
