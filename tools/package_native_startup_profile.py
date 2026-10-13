#!/usr/bin/env python3
"""Package exact diagnostic native binaries; this package cannot publish an APK."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools/android/interactive'),str(ROOT/'tools/android/client')]
import prepare_map_startup_source as retained_map
import prepare_native_startup_profile_source as map_profile
import prepare_native_cg_profile_source as cg_profile
import package_client_render_queue_native as retained_game
from package_reference_runtime import file_record
from map_startup_namespace_certificate import require

MANIFEST='native-startup-profile-package.json'
CONTROL='native-startup-control.json'
GAME_BASE='native-cg-retained-game.json'


def pin(path):
    path=Path(path);require(path.is_file() and not path.is_symlink(),'Regular diagnostic input required: '+str(path))
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return {'bytes':path.stat().st_size,'sha256':h.hexdigest()}


def read(path):
    return json.loads(Path(path).read_text())


def write(path,value):
    Path(path).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')


def map_input(source, profiled=False):
    value=read(source/retained_map.RECEIPT)
    require(value==retained_map.expected_receipt(value['animation_certificate'],monorail_build_input=value['monorail_build_input']),
            'Retained Map source recipe differs')
    pins={**value['patched_sha256'],**value['overlay_sha256'],**value['retained_sources_sha256'],
          **value['monorail_build_input']['retained_collision_sources']}
    if profiled:
        expected=map_profile.expected_receipt();require(read(source/map_profile.RECEIPT)==expected,'Map profiler recipe differs')
        pins.update(expected['patched_sha256'])
        pins.update({str(Path(n).parent/map_profile.HEADER):expected['header_sha256'] for n in (map_profile.PARSER,map_profile.SEQUENCER)})
        pins[map_profile.freshness.TARGET]=expected['activated_freshness_header_sha256']
    for name,digest in pins.items():require(pin(source/name)['sha256']==digest,'Compiled Map source differs: '+name)
    return value


def record_control(args):
    require(re.fullmatch('[0-9a-f]{40}',args.repository_commit),'Exact repository source required')
    require(not args.output.exists(),'Fresh control record output required')
    build=map_input(args.source)
    retained_game.validate_cmake_cache(args.source/'out/build/vs2026/CMakeCache.txt')
    binary=args.source/'out/build/vs2026/bin/OptDebug/MapServer.exe'
    record=file_record(binary);require(record.get('pe_machine')==332,'Map control must be Win32')
    require(b'COH_NATIVE_STARTUP_PROFILE_V1' not in binary.read_bytes(),'Control contains diagnostic overlay')
    args.output.mkdir(parents=True)
    shutil.copyfile(binary,args.output/'MapServer-control.exe')
    write(args.output/CONTROL,{'format':1,'repository_commit':args.repository_commit,'publication_allowed':False,
        'role':'fresh_rebuilt_retained_map_control','build_input':build,'binary':record,
        'cmake_cache':pin(args.source/'out/build/vs2026/CMakeCache.txt')})


def stage_game(args):
    retained_game.stage(SimpleNamespace(output=args.output))
    expected,frozen=retained_game.validate_source(args.output)
    write(args.output/GAME_BASE,{'build_input':expected,'retained_source_inputs':frozen})
    cg_profile.stage(args.output)


def package(args):
    require(re.fullmatch('[0-9a-f]{40}',args.repository_commit),'Exact repository source required')
    require(re.fullmatch(r'https://github\.com/Russianranger/coh-android/actions/runs/[1-9][0-9]*',args.run_url),
            'Exact Actions producer required')
    control=read(args.output/CONTROL)
    require(control['repository_commit']==args.repository_commit and control['publication_allowed'] is False,
            'Control source/role differs')
    require(file_record(args.output/'MapServer-control.exe')==control['binary'],'Control bytes changed')
    retained=map_input(args.map_source,profiled=True)
    retained_game.validate_cmake_cache(args.map_source/'out/build/vs2026/CMakeCache.txt')
    retained_game.validate_cmake_cache(args.game_source/'out/build/vs2026/CMakeCache.txt')
    require(retained==control['build_input'],'Control/candidate retained Map source differs')
    cg=cg_profile.expected_receipt();require(read(args.game_source/cg_profile.RECEIPT)==cg,'Cg recipe differs')
    for name,digest in {**cg['patched_sha256'],**cg['overlay_sha256']}.items():
        require(pin(args.game_source/name)['sha256']==digest,'Compiled Cg source differs: '+name)
    game_base=read(args.game_source/GAME_BASE)
    game_expected,game_frozen=retained_game.validate_source(args.game_source)
    require(game_base=={'build_input':game_expected,'retained_source_inputs':game_frozen},
            'Game retained source recipe differs')
    checks=read(args.cg_checks)
    require(checks.get('status')=='passed' and checks.get('cases')==10 and checks.get('native_windows_executed') is True
            and checks.get('gpu_executed') is False and checks.get('source')==cg,'Actual Windows control-flow fixture required')
    files={}
    for source,name in ((args.map_source/'out/build/vs2026/bin/OptDebug/MapServer.exe','MapServer-profile.exe'),
                        (args.game_source/'out/build/vs2026/bin/OptDebug/CityOfHeroes.exe','CityOfHeroes-profile.exe')):
        record=file_record(source);require(record.get('pe_machine')==332,'Diagnostic must be Win32 PE')
        required=b'COH_NATIVE_STARTUP_PROFILE_V1' if name.startswith('Map') else b'COH_NATIVE_CG_PROFILE_V1'
        require(required in source.read_bytes(),'Native diagnostic marker missing')
        expected=control['binary'] if name.startswith('Map') else retained_game.BASE_GAME
        require(record['imports']==expected['imports'] and record['delay_imports']==expected['delay_imports'],
                'Diagnostic native dependency closure changed')
        shutil.copyfile(source,args.output/name);files[name]=record
    shutil.copyfile(args.cg_checks,args.output/'native-cg-windows-checks.json')
    shutil.copyfile(args.cg_checks.with_suffix('.exe'),args.output/'native-cg-control-flow.exe')
    require(pin(args.output/'native-cg-control-flow.exe')['sha256']==checks['fixture_binary_sha256'],
            'Executed Windows fixture binary differs')
    result={'format':1,'role':'nonshipping_native_startup_profile','repository_commit':args.repository_commit,
        'run_url':args.run_url,'publication_allowed':False,'native_game_executed':False,'map_world_entry_executed':False,
        'physical_device_executed':False,'native_control':control,'map_profile':map_profile.expected_receipt(),
        'cg_profile':cg,'retained_game':game_base,'cg_control_flow':checks,
        'configuration':'OptDebug','architecture':'Win32','build_targets':['MapServer','Game'],'files':files,
        'game_cmake_cache':pin(args.game_source/'out/build/vs2026/CMakeCache.txt'),
        'map_cmake_cache':pin(args.map_source/'out/build/vs2026/CMakeCache.txt'),
        'scope':'Diagnostic binaries only; Wine preload parity is a separate result; no shipping/runtime acceptance'}
    write(args.output/MANIFEST,result)
    return validate(args.output,args.repository_commit)


def validate(directory,commit):
    directory=Path(directory);value=read(directory/MANIFEST)
    require({p.name for p in directory.iterdir()}=={MANIFEST,CONTROL,'MapServer-control.exe','MapServer-profile.exe',
        'CityOfHeroes-profile.exe','native-cg-windows-checks.json','native-cg-control-flow.exe'}
        and not any(p.is_symlink() for p in directory.iterdir()),'Diagnostic package member closure differs')
    require(value.get('role')=='nonshipping_native_startup_profile' and value.get('repository_commit')==commit
        and all(value.get(key) is False for key in ('publication_allowed','native_game_executed','map_world_entry_executed','physical_device_executed')),
        'Diagnostic source/claim scope differs')
    require(value['map_profile']==map_profile.expected_receipt() and value['cg_profile']==cg_profile.expected_receipt(),
            'Diagnostic source recipe changed')
    require(read(directory/CONTROL)==value['native_control'],'Control receipt differs')
    require(file_record(directory/'MapServer-control.exe')==value['native_control']['binary'],'Control binary changed')
    for name,record in value['files'].items():require(file_record(directory/name)==record,'Diagnostic binary changed: '+name)
    checks=read(directory/'native-cg-windows-checks.json')
    require(checks==value['cg_control_flow'] and checks['fixture_binary_sha256']==pin(directory/'native-cg-control-flow.exe')['sha256'],
            'Executed Cg control-flow evidence differs')
    return value


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    r=sub.add_parser('record-control');r.add_argument('--source',type=Path,required=True);r.add_argument('--output',type=Path,required=True);r.add_argument('--repository-commit',required=True)
    g=sub.add_parser('stage-game');g.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('package')
    for name in ('map-source','game-source','cg-checks','output'):q.add_argument('--'+name,type=Path,required=True)
    q.add_argument('--repository-commit',required=True);q.add_argument('--run-url',required=True)
    a=p.parse_args();result={'record-control':record_control,'stage-game':stage_game,'package':package}[a.command](a)
    print(json.dumps({'status':'nonshipping_stage_complete','publication_allowed':False}))
