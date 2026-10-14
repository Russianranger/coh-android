"""Closed one-Game/one-probe producer, preserving exact public .36 ancestry."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import unittest
import os
import io
import tempfile
import zipfile

OVERLAY=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(OVERLAY/'native'),str(OVERLAY/'probe'),str(OVERLAY/'transport'),str(OVERLAY/'pipeline')]
import prepare_live_native_source as live
import parse_live_bridge_probe as probe_parser
import qualify_live_bridge_probe_windows as probe_qualifier

MANIFEST='native-live-directory-SDK-package.json'
CONTROL='portable-controls.json'
PROBE='coh-live-bridge-probe.exe'
MEMBERS=('CityOfHeroes.exe',PROBE,CONTROL,'windows-controls.json',live.RECEIPT,
         'CMakeCache.txt','UtilitiesLib.vcxproj','Game.vcxproj','probe-stock.bin',
         'probe-share-block.bin','probe-sharing-refusal.bin')
CONTROL_MODULES=('test_live_native_policy','test_live_native_authorization','test_live_native_adapter','test_live_native_source',
                 'test_live_bridge_probe_parser','test_live_bridge_probe_native','test_live_bridge_probe_qualification',
                 'test_coh_live_transport','test_live_sdk_pipeline')
CONTROL_COUNT=73
APK={'bytes':42076692,'sha256':'14d88da1796d155dc1b98e45ac642c7702ff3286e7ef0f2a0772f8e48693b12f'}
DONOR_SOURCE='3570430cefdb15d9b239563e85cccf4d8fe6f32e'
GAME_SHA='5f9597fac6e5c4eb2bf6ab091a8b2b5d71c341371da04dc135cef7e5fe00010b'
GAME_BYTES=9499648


def pin(path):
    path=Path(path)
    live.require(path.is_file() and not any(p.is_symlink() for p in (path,*path.parents)) and
                 0<path.stat().st_size<=64*1024**2,'Regular bounded producer input required')
    data=path.read_bytes()
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def imports(repository):
    root=Path(repository).resolve()
    sys.path[:0]=[str(root/'tools'),str(root/'tools/android/interactive')]
    import package_client_render_queue_native as retained
    from package_reference_runtime import file_record,dependency_report
    live.require(retained.ROOT==root,'Foreign native recipe refused')
    return retained,file_record,dependency_report


def donor(apk,retained,file_record,dependency_report):
    """Preserve the public .36 byte/member/import authenticator locally.

    The historical capture helper is research-only and is not a dependency of
    this clean retained-Game checkout. No donor archive or receipt is rewritten.
    """
    def exact(actual,expected,message):
        live.require(retained.typed_equal(actual,expected),message)
    exact(pin(apk),APK,'Exact independently audited public .36 APK required')
    with zipfile.ZipFile(apk) as archive:
        live.require(len(archive.namelist())==len(set(archive.namelist())),'Duplicate donor APK member')
        raw=archive.read('assets/runtime/client-runtime.zip')
        outer=archive.read('assets/runtime/client-manifest.json')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names=archive.namelist()
        live.require(len(names)==len(set(names))==len({n.casefold() for n in names}) and
                     all(re.fullmatch(r'[A-Za-z0-9_.-]+',n) for n in names),'Duplicate/aliased retained native member')
        live.require('client-package.json' in names,'Retained native package receipt missing')
        raw_manifest=archive.read('client-package.json')
        manifest=json.loads(raw_manifest)
        records=manifest.get('files',{})
        live.require(type(records) is dict and set(names)==set(records)|{'client-package.json'} and
                     manifest.get('server_executables_included') is False,'Retained native member closure differs')
        live.require(records['CityOfHeroes.exe']['sha256']==GAME_SHA and records['CityOfHeroes.exe']['size']==GAME_BYTES,
                     'Retained public Game identity differs')
        actual={}
        with tempfile.TemporaryDirectory(prefix='coh-live-donor-') as temporary:
            for name in sorted(records):
                data=archive.read(name)
                live.require(0<len(data)<=64*1024**2,'Unbounded retained donor payload')
                path=Path(temporary)/name;path.write_bytes(data)
                actual[name]=file_record(path)
        exact(actual,records,'Retained native DLL/Game bytes or imports differ from original receipt')
        exact(dependency_report(actual),manifest['dependency_report'],'Retained native dependency authority differs')
        return {'donor_apk':dict(APK),'donor_source':DONOR_SOURCE,'native_game':actual['CityOfHeroes.exe'],
                'client_runtime_zip':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},
                'client_manifest':{'bytes':len(outer),'sha256':hashlib.sha256(outer).hexdigest()},
                'client_package':{'bytes':len(raw_manifest),'sha256':hashlib.sha256(raw_manifest).hexdigest()},
                'native_member_closure':actual,'client_runtime_manifest':manifest,
                'native_donor_rebuilt':False,'original_archive_or_receipts_rewritten':False}


def controls(repository,commit,output):
    live.require(re.fullmatch('[0-9a-f]{40}',commit) and not Path(output).exists(),'Fresh current control identity required')
    os.environ['COH_LIVE_REPOSITORY']=str(Path(repository).resolve())
    modules=CONTROL_MODULES
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in modules)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    live.require(result.wasSuccessful() and not result.skipped and result.testsRun==CONTROL_COUNT,
                 'All exact executed current controls required')
    value={'format':1,'role':'live_directory_current_portable_controls','status':'passed','repository_commit':commit,
           'test_count':result.testsRun,'modules':list(modules),'source_recipe':live.expected_receipt(repository,OVERLAY),
           'SDK_executed':False,'Game_executed':False,'Android_runtime_executed':False,'publication_allowed':False}
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
    return value


def stage(repository,output):
    retained,_,_=imports(repository)
    from types import SimpleNamespace
    retained.stage(SimpleNamespace(output=Path(output)))
    return live.stage(output,repository,OVERLAY)


def validate_probe_controls(controls,binary,directory,commit):
    live.require(controls['format']==1 and controls['role']=='fresh_native_Win32_NT_bridge_observer_controls' and
                 controls['status']=='passed' and controls['binary']==pin(binary) and controls['fresh_native_control_groups']==4 and
                 controls['repository_commit']==commit and controls['probe_source']==probe_qualifier.source_pins(),
                 'Current actual Win32 probe controls missing')
    live.require(all(controls[k] is False for k in ('Wine_executed','Android_runtime_executed','Game_executed','provider_authority','publication_allowed')),
                 'Unexpected probe authority claim')
    cases=controls['cases']
    live.require(set(cases)=={'actual_stock_multibuffer','existing_output_preserved','native_share_refusal_and_owned_release','input_namespace_output_refused'},
                 'Four actual probe controls differ')
    stock=cases['actual_stock_multibuffer']
    blocked=cases['native_share_refusal_and_owned_release']['blocked']
    held=cases['native_share_refusal_and_owned_release']['held']
    for case,name in ((stock,'stock.bin'),(blocked,'sharing-refusal.bin'),(held,'share-block.bin')):
        packet=Path(directory)/name
        live.require(pin(packet)==case['packet'] and probe_parser.parse(packet.read_bytes())==case['parsed'],'Raw actual SDK packet differs: '+name)
        probe_qualifier.genuine_result(case,2 if case is held else 1,case is not blocked)
    live.require(held['readiness_observer_stopped'] is True,'Held readiness observer cleanup missing')
    live.require(stock['returncode']==0 and stock['parsed']['packet_complete'] and
                 len(stock['parsed']['batches'])>1 and held['returncode']==0 and held['parsed']['packet_complete'] and
                 blocked['returncode']!=0 and not blocked['parsed']['packet_complete'] and
                 blocked['parsed']['native_open_status']==0xc0000043,'Current native behavior gates failed')
    names=[row['name'] for row in stock['parsed']['rows'] if row['name'] not in ('.','..')]
    live.require(sorted(names)==[f'fixture_{n:03d}_'+('x'*70)+'.fx' for n in range(200)],
                 'Exact current multibuffer SDK fixture cardinality/membership differs')
    for label,code in (('existing_output_preserved',65),('input_namespace_output_refused',64)):
        case=cases[label]
        cleanup=case['process_cleanup']
        live.require(case['returncode']==code and case['execution_error'] is None and
                     cleanup['closed_exact_owned_child'] is True and cleanup['forced_termination'] is False and
                     cleanup['held_pid']==case['held_native_pid'] and cleanup['returncode']==code and
                     not case.get('termination_requested_after_timeout') and not case.get('termination_requested_after_failure'),
                     'Exact owned output-refusal execution/cleanup differs')
    live.require(cases['existing_output_preserved']['packet']==stock['packet'] and
                 cases['input_namespace_output_refused']['packet'] is None,'Output refusal controls failed')


def package(args):
    root=Path(args.repository).resolve()
    retained,file_record,dependency_report=imports(root)
    live.require(re.fullmatch('[0-9a-f]{40}',args.commit) and re.fullmatch(
        r'https://github\.com/Russianranger/coh-android/actions/runs/[1-9][0-9]*',args.run_url),'Exact producer identity required')
    out=Path(args.output)
    live.require(not out.exists(),'Fresh SDK package required')
    source=live.validate_staged_source(args.source,root,OVERLAY)
    live.require(source['source']['cmake_injection_sha256']==pin(OVERLAY/'native/coh_live_directory.cmake')['sha256'],
                 'Exact private CMake source guard differs')
    inherited=donor(args.donor,retained,file_record,dependency_report)
    game=Path(args.game)
    game_record=file_record(game)
    live.require(game.parent.name=='OptDebug' and game_record['pe_machine']==332 and game_record['sha256']!=inherited['native_game']['sha256'],
                 'Fresh actual Win32 OptDebug Game required')
    live.require(game_record['imports']==inherited['native_game']['imports'] and game_record['delay_imports']==inherited['native_game']['delay_imports'],
                 'Retained actual Game native DLL closure differs')
    live.require(b'COH_LIVE_DIRECTORY event=' in game.read_bytes(),'Fresh Game consumer marker missing')
    observer=Path(args.probe)
    observer_record=file_record(observer)
    live.require(observer_record['pe_machine']==332 and set(observer_record['imports']).issubset({'KERNEL32.dll'}) and
                 not observer_record['delay_imports'] and b'COH_NT_PROBE_RESULT' in observer.read_bytes(),'Bounded actual Win32 observer closure differs')
    cache=Path(args.cache)
    cache_receipt=retained.validate_cmake_cache(cache)
    text=cache.read_text(encoding='utf-8-sig')
    for expression in (r'^COX_BUILD_MAPSERVER:BOOL=OFF$',r'^COX_BUILD_BEACONSERVER:BOOL=OFF$',
                       r'^CMAKE_PROJECT_INCLUDE:(?:FILEPATH|UNINITIALIZED|STRING)=.*[/\\]coh_live_directory\.cmake$'):
        live.require(re.search(expression,text,re.MULTILINE),'Exact Game-only source configure missing')
    for project in (args.utilities,args.game_project):
        data=Path(project).read_bytes()
        live.require(b'COH_CLIENT_LIVE_DIRECTORY=1' in data and b'COH_CLIENT_METADATA_CENSUS' not in data,
                     'Private live compile define or replay exclusion differs')
    controls=json.loads(Path(args.controls).read_text())
    live.require(controls['status']=='passed' and controls['repository_commit']==args.commit and controls['source_recipe']==source['source'] and
                 type(controls['test_count']) is int and controls['test_count']==CONTROL_COUNT and
                 controls['modules']==list(CONTROL_MODULES) and controls['SDK_executed'] is False and
                 controls['Game_executed'] is False and controls['Android_runtime_executed'] is False and
                 controls['publication_allowed'] is False,
                 'Current executed portable controls differ')
    windows=Path(args.windows)
    sdk=json.loads((windows/'windows-controls.json').read_text())
    validate_probe_controls(sdk,observer,windows,args.commit)
    out.mkdir()
    copied=((game,'CityOfHeroes.exe'),(observer,PROBE),(args.controls,CONTROL),(windows/'windows-controls.json','windows-controls.json'),
            (Path(args.source)/live.RECEIPT,live.RECEIPT),(cache,'CMakeCache.txt'),(args.utilities,'UtilitiesLib.vcxproj'),(args.game_project,'Game.vcxproj'),
            (windows/'stock.bin','probe-stock.bin'),(windows/'share-block.bin','probe-share-block.bin'),(windows/'sharing-refusal.bin','probe-sharing-refusal.bin'))
    for original,name in copied:
        pin(original);shutil.copyfile(original,out/name)
    value={'format':1,'role':'closed_fresh_native_Game_live_directory_SDK_producer','repository_commit':args.commit,'run_url':args.run_url,
           'source':source,'retained_public_036':inherited,'files':{'CityOfHeroes.exe':game_record,PROBE:observer_record},
           'cache':cache_receipt,'portable_controls':controls,'fresh_Windows_probe_controls':sdk,
           'probe_source':probe_qualifier.source_pins(),'private_cmake_source':pin(OVERLAY/'native/coh_live_directory.cmake'),
           'members':{name:pin(out/name) for name in MEMBERS},
           'native_Game_compiled_in_current_run':True,'native_Game_executed':False,
           'native_Wine_executed':False,'Android_runtime_executed':False,'provider_authority':False,
           'native_registration_allowed':False,'publication_allowed':False}
    (out/MANIFEST).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
    live.require({p.name for p in out.iterdir()}==set(MEMBERS)|{MANIFEST},'Exact produced member closure differs')
    return value


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    for name in ('controls','stage','package'):
        s=sub.add_parser(name);s.add_argument('--repository',type=Path,required=True);s.add_argument('--output',type=Path,required=True)
        if name!='stage':s.add_argument('--commit',required=True)
        if name=='package':
            for key in ('source','donor','game','probe','cache','utilities','game-project','controls','windows'):
                s.add_argument('--'+key,type=Path,required=True)
            s.add_argument('--run-url',required=True)
    a=p.parse_args()
    value=controls(a.repository,a.commit,a.output) if a.command=='controls' else stage(a.repository,a.output) if a.command=='stage' else package(a)
    print(json.dumps(value,sort_keys=True))
