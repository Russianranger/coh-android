#!/usr/bin/env python3
"""Capture actual client metadata work without replay, login or source authority.

One prepared readonly provider and owned closed Wine prefix are used for retained
first/warm startup, capture-binary disabled/enabled observations and a separate
read-only Win32 metadata probe. All timings remain ordered software-GL host scope.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import shutil
import stat
import subprocess
import sys
import time
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
import package_native_client_metadata_capture as native
import qualify_native_client_startup as startup
import qualify_native_client_folder_sort_wine as retained_helpers
import native_client_pig_index_capture as pigs
import test_native_client_wfd_probe as wfd
from prepare_native_client_profile_fixture import require,pin,write

PRODUCER_SOURCE='dc0095786096b0da3942081bf059ef977055af4c7002e9200d61c2214cf25075'
FALSE_AUTHORITY={'provider_authority':False,'native_registration_allowed':False,
    'runtime_source_equivalence_qualified':False,'Android_Wine_FEX_PRRoot_mapping_qualified':False,
    'native_replay_executed':False,'publication_allowed':False}

def producer_module():
    path=ROOT/'android/guest/folder_cache_census.py'
    require(pin(path)['sha256']==PRODUCER_SOURCE,'Exact closed guest producer source required')
    spec=importlib.util.spec_from_file_location('_coh_capture_source_projection',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    require(module.PRODUCTION_AUTHORITY is None and module.ACTIVATION_IMPLEMENTED is False,
            'Guest producer registration must stay absent')
    return module

def projection(root, imported, operation, provenance, output, between=None):
    """Direct fresh scan/encode; expressly no Android recipe-validation success."""
    require(type(operation) is str and re.fullmatch('[0-9a-f]{32}',operation), 'Exact operation required')
    require(not output.exists() and not output.is_symlink(), 'Fresh projection output required')
    root=root.resolve(strict=True); imported=imported.resolve(strict=True)
    producer=producer_module(); first=None;started=time.monotonic()
    rss_before=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    try:
        first=producer.scan(root,[root,imported],collect=True)
        captured=time.monotonic()
        if between:between()
        second=producer.scan(root,[root,imported],collect=False)
        rechecked=time.monotonic()
        require(first['vector_sha256']==second['vector_sha256'] and
            all(first[key]==second[key] for key in ('files','links','directory_count','outscope_root_entries','rows')),
            'Fresh complete selected metadata changed between passes')
        token=hashlib.sha256(producer.canonical({'operation':operation,'vector_sha256':first['vector_sha256'],
            'source':PRODUCER_SOURCE,'provenance':provenance})).hexdigest()
        packet=producer.encode(first,token)
        report={'format':1,'role':'fresh_source_projection_under_external_host_custody','operation':operation,
            'generation_token':token,'vector_sha256':first['vector_sha256'],'files':first['files'],'links':first['links'],
            'directory_count':first['directory_count'],'rows':first['rows'],
            'outscope_root_entries':first['outscope_root_entries'],'root_anchor_complete':False,
            'metadata_requests':{'capture':first['metadata_requests'],'recheck':second['metadata_requests'],
                'interpretation':'explicit producer metadata API requests; kernel syscall counts not measured'},
            'complete_selected_branches':list(producer.BRANCHES),'fresh_metadata_passes':2,
            'source_projection_qualified_as_Wine_metadata':False,'producer_capture_recipe_validation_executed':False,
            'fixed_Android_Wine_source_commit_asserted_for_host':False,'provenance':provenance,
            'packet':{'bytes':len(packet),'sha256':hashlib.sha256(packet).hexdigest()},
            'phase_seconds':{'capture':round(captured-started,6),'recheck':round(rechecked-captured,6),'encode':round(time.monotonic()-rechecked,6)},
            'whole_preflight_seconds':round(time.monotonic()-started,6),
            'qualifier_process_maxrss_kib_before':rss_before,
            'qualifier_process_maxrss_kib_after':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'native_Game_process_RSS_measured':False,**FALSE_AUTHORITY}
        output.mkdir(mode=0o700)
        (output/'source-projection.bin').write_bytes(packet)
        write(output/'source-projection.json',report)
        return packet,report
    finally:
        if first is not None:first['records'].close()

def windows_path(path):
    path=Path(path).absolute()
    require(str(path).isascii() and '\\' not in str(path) and ':' not in str(path) and '..' not in path.parts,
            'Unambiguous host Z mapping required')
    return 'Z:'+str(path).replace('/','\\')

def recheck_projection(root, imported, expected, output):
    producer=producer_module()
    started=time.monotonic()
    observed=producer.scan(root.resolve(strict=True),[root.resolve(strict=True),imported.resolve(strict=True)],collect=False)
    report={'format':1,'role':'fresh_selected_metadata_post_native_recheck',
        'vector_sha256':observed['vector_sha256'],'files':observed['files'],'links':observed['links'],
        'directory_count':observed['directory_count'],'rows':observed['rows'],
        'outscope_root_entries':observed['outscope_root_entries'],'seconds':round(time.monotonic()-started,6),
        'metadata_requests':observed['metadata_requests'],'kernel_syscalls_measured':False,**FALSE_AUTHORITY}
    report['matched']=all(report[key]==expected[key] for key in ('vector_sha256','files','links','directory_count','rows','outscope_root_entries'))
    write(output,report)
    require(report['matched'],'Current selected metadata changed during native observations')
    return report

def closed_prefix(prefix,identity):
    info=prefix.lstat()
    require(stat.S_ISDIR(info.st_mode) and not prefix.is_symlink() and not info.st_mode&0o077
        and [info.st_dev,info.st_ino,info.st_uid]==identity and startup.process_census(prefix)==[],
        'Exact owned closed prefix identity required')

def run_probe(executable,work,prefix,identity,env,tools,output,generation,operation,seconds=300):
    require(type(seconds) is int and 1<=seconds<=900,'Bounded isolated probe budget required')
    closed_prefix(prefix,identity)
    require(not output.exists(),'Fresh probe operation output required')
    output.mkdir(mode=0o700)
    sidecar=output/'actual-WFD.bin';process=None;failure=None;cleanup=None;observation=None
    command=[tools['wine']['invocation'],windows_path(executable),windows_path(work/'data'),windows_path(sidecar),generation,operation,str(seconds)]
    write(output/'invocation.json',{'command':command,'executable':pin(executable),'generation':generation,
        'operation':operation,'owned_prefix_identity':identity,'output':str(sidecar),'isolated_CI_budget_seconds':seconds,
        'player_profile_used':False,'provider_authority':False})
    started=time.monotonic()
    try:
        require(pin(Path(tools['wine']['resolved']))==tools['wine']['resolved_pin'],'Exact actual Wine executable changed')
        with (output/'stdout.log').open('wb') as stdout,(output/'stderr.log').open('wb') as stderr:
            process=subprocess.Popen(command,cwd=work,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True)
            deadline=started+seconds+30
            while process.poll() is None:
                require(time.monotonic()<deadline,'Actual read-only native metadata probe exceeded CI deadline')
                require((output/'stdout.log').stat().st_size<=65536 and (output/'stderr.log').stat().st_size<=65536,
                        'Native probe diagnostic exceeded bound')
                if sidecar.exists():require(not sidecar.is_symlink() and sidecar.stat().st_size<=wfd.MAX_BYTES,'Native sidecar exceeded bound')
                time.sleep(.1)
        raw=(output/'stdout.log').read_bytes()
        lines=[line for line in raw.decode('ascii').splitlines() if line.startswith(wfd.MARKER)]
        require(len(lines)==1,'Exactly one current native probe console receipt required')
        receipt=json.loads(lines[0][len(wfd.MARKER):])
        require(process.returncode==0 and receipt.get('status')=='complete_observation'
            and receipt.get('operation')==operation and receipt.get('generation')==generation
            and receipt.get('output_created') is True and receipt.get('output_handle_closed') is True
            and receipt.get('provider_authority') is False and receipt.get('publication_allowed') is False,
            'Actual native WFD/readability probe incomplete; retain current diagnostic')
        observation=wfd.parse(sidecar.read_bytes(),generation,operation,windows_path(work/'data'),receipt['windows_pid'])
        require(observation['status']=='complete_observation','Native current provider mapping/readability incomplete')
        write(output/'actual-WFD-observation.json',observation)
    except BaseException as error:failure={'type':type(error).__name__,'message':str(error)[:2048]}
    finally:
        stop=output/'cleanup';stop.mkdir()
        try:cleanup=startup.stop_prefix(prefix,env,tools['wineserver'],stop,owned_process=process)
        except BaseException as error:cleanup={'passed':False,'type':type(error).__name__,'message':str(error)[:2048]}
        value={'format':1,'role':'actual_readonly_PE32_WFD_by_handle_host_observation',
            'status':'passed' if observation and failure is None and cleanup['passed'] else 'failed',
            'failure':failure,'cleanup':cleanup,'observation':observation,'elapsed_seconds':round(time.monotonic()-started,6),
            'probe':pin(executable),'native_Wine_executed':process is not None,'native_Game_executed':False,
            'actual_process_invocation_held':process is not None,'physical_device_executed':False,**FALSE_AUTHORITY}
        write(output/'native-probe-phase.json',value)
    require(value['status']=='passed','Actual native metadata probe failed; raw evidence and owned cleanup retained')
    return value

def mapped_native_path(value,work):
    require(type(value) is str and value and value.isascii() and '\x00' not in value,'Bounded native provider path required')
    value=value.replace('\\','/')
    if value[:2].lower()=='z:':value=value[2:]
    else:require(not re.match('[A-Za-z]:',value),'Unknown native drive mapping')
    path=Path(value)
    if not path.is_absolute():path=work/path
    require('..' not in path.parts,'Native provider traversal mapping refused')
    return path.absolute()

def pig_custody(capture,work,fixture,auxiliary):
    require(mapped_native_path(capture['begin']['gdd_root'],work)==work/'data','Actual native one-GDD path differs')
    expected=work/'piggs'/'server-animations.pigg'
    require(len(capture['providers'])==1 and mapped_native_path(capture['providers'][0]['archive'],work)==expected,
            'Actual native ordered PIG archive differs from authenticated animation custody')
    row=capture['providers'][0]
    require(row['virtual_location']==-1 and row['folder_cache_mount']==row['archive']+':'
        and auxiliary['stable_inputs']['piggs/server-animations.pigg']['sha256']==fixture['supplements']['client_animation_package']['pigg']['sha256'],
        'Actual native PIG provider/byte custody differs')
    return {'format':1,'complete_native_index_observed':True,'current_archive_byte_custody_bound':True,
        'actual_one_GDD_observed':True,'providers':1,'rows':capture['end']['rows'],
        'native_provider_selection_qualified':False,'branch_nonoverlap_qualified':False,**FALSE_AUTHORITY}

def qualify(args):
    import native_client_census_observed_bridge as bridge
    require(not args.output.exists(),'Fresh actual client capture lane required')
    args.output.mkdir(mode=0o700)
    value={'format':1,'role':'nonshipping_actual_client_metadata_capture_Wine_lane','status':'failed',
        'repository_commit':os.environ.get('GITHUB_SHA'),'workflow_run_id':os.environ.get('GITHUB_RUN_ID'),
        'failure':None,'final_cleanup':None,'single_provider_preparation':True,'same_closed_owned_prefix':True,
        'physical_device_executed':False,'world_entry_executed':False,'character_login_attempted':False,
        'optimization_benefit_claimed':False,**FALSE_AUTHORITY}
    lane_started=time.monotonic()
    env=None;tools=None;identity=None;prefix_descriptor=None;prefix_info=None
    custody_costs=[]
    def custody_snapshot(label,work,assets,fixture,imported):
        started=time.monotonic()
        provider=retained_helpers.provider_snapshot(work,imported)
        provider_ended=time.monotonic()
        auxiliary=retained_helpers.auxiliary_snapshot(work,assets,fixture)
        ended=time.monotonic()
        record={'label':label,'provider_full_content_and_metadata_seconds':round(provider_ended-started,6),
            'auxiliary_seconds':round(ended-provider_ended,6),'whole_seconds':round(ended-started,6),
            'provider_files':provider['files'],'provider_content_bytes_rehashed':provider['bytes'],
            'provider_directories':provider['directories'],'scope':'qualification custody outside Game clock; not a proposed zero-cost launcher step',
            'kernel_syscalls_measured':False}
        custody_costs.append(record)
        write(args.output/(label+'-provider.json'),provider);write(args.output/(label+'-auxiliary.json'),auxiliary)
        write(args.output/'custody-validation-costs.json',custody_costs)
        return provider,auxiliary
    def prefix_created(prefix):
        nonlocal identity,prefix_descriptor,prefix_info
        prefix_info=prefix.lstat()
        require(stat.S_ISDIR(prefix_info.st_mode) and prefix_info.st_uid==os.geteuid()
            and not prefix.is_symlink() and not prefix_info.st_mode&0o077,'New private capture prefix custody required')
        prefix_descriptor=os.open(prefix,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        startup.check_held_prefix(prefix,prefix_descriptor,prefix_info)
        identity=[prefix_info.st_dev,prefix_info.st_ino,prefix_info.st_uid]
        write(args.output/'owned-prefix-created.json',{'format':1,'identity':identity,'prefix':str(prefix.absolute()),
            'held_before_any_native_Wine_process':True,'known_delegated_prefix_creation':True})
    try:
        authentication_started=time.monotonic()
        build=native.validate_package(args.package,args.package_commit,args.donor_apk)
        value['native_package_authentication_seconds']=round(time.monotonic()-authentication_started,6)
        fixture=json.loads(args.fixture.read_text());work=Path(fixture['work']);assets=Path(fixture['assets'])
        imported=Path(fixture['actual_client_worktree']['source_data']);inherited=build['retained_public_client']['native_member_closure']
        before,aux_before=custody_snapshot('before',work,assets,fixture,imported)
        retained_helpers.native_closure(work,inherited)
        tools={name:startup.binary_tool(name) for name in ('wine','wineserver','tesseract')}
        env=retained_helpers.environment(args.prefix.absolute(),fixture['texture_header_environment'])
        env.pop('COH_CLIENT_FOLDER_METADATA_SORT',None)
        retained=startup.qualify(SimpleNamespace(fixture=args.fixture,prefix=args.prefix,output=args.output/'retained',
            native_role='retained',native=None,timeout_seconds=args.timeout_seconds,prefix_created=prefix_created))
        value['retained']=retained
        require(retained['host_tools']==tools and retained['final_cleanup']['prefix_identity']==identity,'Current host tools/prefix custody differs')
        require(retained['status']=='passed' and retained['final_cleanup']['passed'],'Fresh retained actual startup required')
        warm_provider,warm_aux=custody_snapshot('retained-warm',work,assets,fixture,imported)
        require(warm_provider==before and warm_aux==aux_before,
                'Retained initialization changed immutable provider custody')
        renderer=retained_helpers.renderer_identity(retained['cases'][1]);bins=startup.cache_snapshot(work)
        old_pack=(work/'coh-texture-header-index.bin').read_bytes()
        closed_prefix(args.prefix.absolute(),identity)
        target=work/'CityOfHeroes.exe';require(pin(target)['sha256']==startup.GAME_SHA,'Only retained native Game may be replaced')
        target.chmod(0o600);shutil.copyfile(args.package/'CityOfHeroes.exe',target);target.chmod(0o400)
        retained_helpers.native_closure(work,dict(inherited,**{'CityOfHeroes.exe':build['files']['CityOfHeroes.exe']}))
        sys.path.insert(0,str(assets));client=importlib.import_module('client_startup_diagnostic');thi=importlib.import_module('texture_header_index')
        require(all(Path(module.__file__).resolve().parent==assets for module in (client,thi)),'Exact published guest helpers required')
        context=SimpleNamespace(report={'client_worktree':fixture['actual_client_worktree']},check=lambda:None,event=lambda *a,**k:None)
        started=time.monotonic();header,texture=thi.prepare(work,fixture['actual_client_worktree']['import'],build['files']['CityOfHeroes.exe']['sha256'],context)
        new_pack=(work/'coh-texture-header-index.bin').read_bytes()
        require(old_pack[:32]==new_pack[:32] and old_pack[64:]==new_pack[64:] and header['original_texture_files_unchanged'],
                'Capture Game texture headers/cardinality/payload changed')
        write(args.output/'capture-texture-binding.json',dict(header,preparation_seconds=round(time.monotonic()-started,6),
            native_Game_timing_includes_preparation=False,header_payload_byte_equal=True,retained_pack_sha256=hashlib.sha256(old_pack).hexdigest()))
        env=retained_helpers.environment(args.prefix.absolute(),texture);env.pop('COH_CLIENT_FOLDER_METADATA_SORT',None)
        aux=retained_helpers.auxiliary_snapshot(work,assets,fixture)
        require(aux['stable_inputs']==aux_before['stable_inputs'],'Texture rebinding changed unrelated auxiliary input custody')
        output=args.output/'capture';output.mkdir()
        disabled=dict(env,COH_CLIENT_CENSUS_CAPTURE='0')
        phase=startup.launch_case(SimpleNamespace(native_role='metadata-capture-disabled',timeout_seconds=args.timeout_seconds),fixture,client,work,disabled,tools,output,'observation-disabled')
        value['capture_disabled']=phase
        disabled_console=(output/'observation-disabled/stdout.log').read_text(errors='replace')
        require(pigs.MARKER not in disabled_console and 'COH_NATIVE_FOLDER_STAT_COUNTS_V1' not in disabled_console,
            'Observation-disabled capture binary produced enabled observations')
        require(not phase['cache_delta'] and startup.cache_snapshot(work)==bins,'Capture-disabled altered warmed BINs')
        require(retained_helpers.renderer_identity(phase)==renderer,'Capture-disabled renderer identity changed')
        operation=os.urandom(16).hex()
        provenance={'capture_Game':pin(target),'Wine_tools':tools,'PIG_auxiliary':aux['stable_inputs']['piggs/server-animations.pigg'],
            'actual_fixture':pin(args.fixture),'native_package':pin(args.package/native.MANIFEST),
            'producer_source_commit':'c0c8857af79cdecaff01e7cc9dbf35a71b9d28e5','Android_runtime_source_equivalence':False}
        packet,report=projection(work/'data',imported,operation,provenance,args.output/'source-projection')
        value['source_projection']=report
        probe=run_probe(args.package/native.FIXTURE,work,args.prefix.absolute(),identity,env,tools,args.output/'actual-WFD',
            report['generation_token'],operation,args.probe_timeout_seconds)
        value['actual_WFD']=probe
        value['consumed_field_comparison']=bridge.compare(packet,probe['observation'],report['generation_token'])
        value['post_probe_projection']=recheck_projection(work/'data',imported,report,args.output/'post-probe-projection.json')
        post_probe_provider,post_probe_aux=custody_snapshot('post-probe',work,assets,fixture,imported)
        require(post_probe_provider==before and post_probe_aux==aux
            and startup.cache_snapshot(work)==bins,'Metadata probe changed original inputs or warmed BINs')
        enabled=dict(env,COH_CLIENT_CENSUS_CAPTURE='1',COH_CLIENT_CENSUS_CAPTURE_GENERATION=report['generation_token'])
        phase=startup.launch_case(SimpleNamespace(native_role='metadata-capture-enabled',timeout_seconds=args.timeout_seconds),fixture,client,work,enabled,tools,output,'observation-enabled')
        value['capture_enabled']=phase
        raw=(output/'observation-enabled/stdout.log').read_text(errors='replace')
        capture=pigs.parse(raw,report['generation_token'],phase['evidence']['launch']['pid'])
        value['actual_native_PIG_index']=capture
        value['PIG_custody_bridge']=pig_custody(capture,work,fixture,aux)
        value['actual_native_stat_snapshots']=bridge.parse_stat_counts(raw)
        value['post_Game_projection']=recheck_projection(work/'data',imported,report,args.output/'post-Game-projection.json')
        old_counts=retained_helpers.logical_counts((args.output/'retained/closed-prefix-second-launch/stdout.log').read_text(errors='replace'))
        require(retained_helpers.logical_counts(raw)==old_counts and retained_helpers.logical_counts((output/'observation-disabled/stdout.log').read_text(errors='replace'))==old_counts,
                'Capture-only native texture/catalog cardinality differs')
        require(not phase['cache_delta'] and startup.cache_snapshot(work)==bins and retained_helpers.renderer_identity(phase)==renderer,
                'Capture-only warmed BIN/renderer compatibility differs')
        final_provider,final_aux=custody_snapshot('post-Game',work,assets,fixture,imported)
        require(final_provider==before and final_aux==aux,
                'Capture-only mutated original provider/PIG/prerequisite custody')
        retained_helpers.native_closure(work,dict(inherited,**{'CityOfHeroes.exe':build['files']['CityOfHeroes.exe']}))
        value['ordered_timings']={'retained_warm_native_witness':retained['cases'][1]['evidence']['native_startup_witness_seconds'],
            'capture_disabled_native_witness':value['capture_disabled']['evidence']['native_startup_witness_seconds'],
            'capture_enabled_native_witness':phase['evidence']['native_startup_witness_seconds'],
            'fresh_projection_preflight':report['whole_preflight_seconds'],'actual_WFD_probe':probe['elapsed_seconds'],
            'scope':'ordered warm software-GL observations; probe/cache prewarming and observer latency recorded; no optimization or physical inference'}
        value['consumed_field_mapping_gate_passed']=value['consumed_field_comparison']['status']=='matched_consumed_fields'
        require(value['consumed_field_mapping_gate_passed'],'Observed native consumed fields differ from source projection; all native capture observations retained')
        value['status']='passed'
    except BaseException as error:value['failure']={'type':type(error).__name__,'message':str(error)[:2048]}
    finally:
        if env is not None and tools is not None and identity is not None:
            cleanup=args.output/'outer-cleanup';cleanup.mkdir()
            try:
                startup.check_held_prefix(args.prefix.absolute(),prefix_descriptor,prefix_info)
                value['final_cleanup']=startup.stop_prefix(args.prefix.absolute(),env,tools['wineserver'],cleanup)
            except BaseException as error:value['final_cleanup']={'passed':False,'type':type(error).__name__,'message':str(error)[:2048]}
        if prefix_descriptor is not None:os.close(prefix_descriptor)
        if value['final_cleanup'] is None or not value['final_cleanup'].get('passed'):value['status']='failed'
        value['qualification_custody_costs']=custody_costs
        value['whole_lane_seconds']=round(time.monotonic()-lane_started,6)
        value['qualifier_process_maxrss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        value['native_Game_process_RSS_measured']=False
        write(args.output/'native-client-metadata-capture-Wine-qualification.json',value)
    require(value['status']=='passed','Actual metadata capture failed; source/native/failure/cleanup evidence retained')
    return value

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('fixture','package','donor-apk','prefix','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--package-commit',required=True);parser.add_argument('--timeout-seconds',type=int,default=900)
    parser.add_argument('--probe-timeout-seconds',type=int,default=300)
    result=qualify(parser.parse_args());print(json.dumps({'status':result['status'],'scope':result['role'],'publication_allowed':False}))
