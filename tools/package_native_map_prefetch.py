#!/usr/bin/env python3
"""Package one isolated metadata-prefetch MapServer, never an APK payload."""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import shutil

import prepare_native_map_metadata_prefetch_source as source
import package_native_startup_profile as base
import reuse_native_startup_profile as retained
from map_startup_namespace_certificate import require

MANIFEST='native-map-prefetch-package.json'
BINARY='MapServer-prefetch.exe'
CHECKS='native-map-prefetch-checks.json'
FIXTURE='native-map-prefetch-fixture.exe'


def validate_checks(value):
    import hashlib
    import test_native_map_metadata_prefetch as fixture
    expected={'format':1,'status':'passed','platform':'windows','architecture':'Win32',
        'configuration':'OptDebug','compiler':'cl.EXE','compiler_options':fixture.COMPILER_OPTIONS,
        'build_input':source.expected_receipt(),
        'harness_sha256':hashlib.sha256(fixture.harness().encode()).hexdigest(),
        'scope':'extracted_actual_freshness_and_prefetch_with_external_IO_test_doubles',
        'scenario_count':fixture.SCENARIO_COUNT,'flag_count':fixture.FLAG_COUNT,
        'cases':fixture.SCENARIO_COUNT*fixture.FLAG_COUNT,
        'equivalence_cases':fixture.SCENARIO_COUNT*fixture.FLAG_COUNT,'exact_tuple_cases':fixture.TUPLE_COUNT}
    # Path(compiler).name casing can differ between equivalent MSVC installations.
    require(isinstance(value,dict) and value.get('compiler','').lower()=='cl.exe',
        'Actual Win32 compiler qualification required')
    expected.pop('compiler')
    require(all(value.get(k)==v for k,v in expected.items()),
        'Exact actual Win32 freshness fixture recipe and full matrix required')
    true_keys=('native_windows_executed','equivalence_verified','operation_order_and_counts_verified',
        'after_header_before_checks_verified','opt_in_and_fallback_verified','exact_scope_verified',
        'freshness_failure_branches_verified','ordinary_source_mutation_detection_verified',
        'existing_production_behavior_preserved','observer_macros_are_noops','metadata_lookup_model_only')
    for key in true_keys:
        require(value.get(key) is True,'Required native freshness fixture verification missing: '+key)
    false_keys=('animation_payload_reads_exercised','native_wine_executed','world_startup_executed',
        'physical_device_executed','physical_startup_savings_validated','publication_allowed')
    for key in false_keys:
        require(value.get(key) is False,'Native fixture overclaims execution: '+key)
    require(type(value['format']) is int and all(type(value[k]) is int for k in
        ('scenario_count','flag_count','cases','equivalence_cases','exact_tuple_cases')),
        'Exact integer fixture schema and counts required')
    require(isinstance(value.get('fixture_binary_sha256'),str)
        and re.fullmatch('[0-9a-f]{64}',value['fixture_binary_sha256']),
        'Native fixture byte identity required')
    require(set(value)==set(expected)|set(true_keys)|set(false_keys)|{'compiler','fixture_binary_sha256','evidence'},
        'Native fixture receipt schema differs')
    evidence=value['evidence'];require(isinstance(evidence,dict),'Retained native fixture evidence required')
    stems=[n[:-10] for n in evidence if isinstance(n,str) and n.endswith('.fixture.c')]
    require(len(stems)==1 and re.fullmatch('[a-zA-Z0-9_-]+',stems[0]),'Single safe native fixture evidence stem required')
    stem=stems[0]
    require(set(evidence)=={stem+suffix for suffix in ('.fixture.c','.fixture.exe','.build.log','.stdout.txt','.stderr.txt')},
        'Complete native fixture evidence closure required')
    for name,pin in evidence.items():
        require(isinstance(pin,dict) and set(pin)=={'sha256','bytes'} and type(pin['bytes']) is int
            and 0<=pin['bytes']<=64*1024**2 and isinstance(pin['sha256'],str)
            and re.fullmatch('[0-9a-f]{64}',pin['sha256']),'Bounded native fixture evidence pin required')
    require(evidence[stem+'.fixture.c']=={'bytes':len(fixture.harness().encode()),'sha256':value['harness_sha256']}
        and evidence[stem+'.fixture.exe']['sha256']==value['fixture_binary_sha256']
        and evidence[stem+'.fixture.exe']['bytes']>0,'Native fixture source/binary evidence identity differs')
    return value


def validate(directory,commit,baseline):
    directory=Path(directory);old=retained.validate_package(baseline)
    require({p.name for p in directory.iterdir()}=={MANIFEST,BINARY,CHECKS,FIXTURE}
        and not any(p.is_symlink() for p in directory.iterdir()),'Candidate native package closure differs')
    value=base.read(directory/MANIFEST)
    require(value.get('format')==1 and value.get('role')=='nonshipping_map_metadata_prefetch'
        and value.get('repository_commit')==commit and re.fullmatch('[0-9a-f]{40}',commit)
        and value.get('build_targets')==['MapServer']
        and all(value.get(k) is False for k in ('publication_allowed','native_world_executed',
            'native_preload_executed','native_game_changed','physical_device_executed')),
        'Candidate native source or claim scope differs')
    require(value['build_input']==source.expected_receipt()
        and value['retained_build']==retained.provenance()
        and value['retained_package']==base.pin(Path(baseline)/base.MANIFEST)
        and value['retained_control_binary']==old['native_control']['binary']
        and value['retained_observed_binary']==old['files']['MapServer-profile.exe'],
        'Candidate exact native baseline or source recipe differs')
    require(base.file_record(directory/BINARY)==value['binary']
        and value['binary']['imports']==old['files']['MapServer-profile.exe']['imports']
        and value['binary']['delay_imports']==old['files']['MapServer-profile.exe']['delay_imports'],
        'Candidate native byte/import closure changed')
    checks=validate_checks(base.read(directory/CHECKS))
    require(checks==value['native_checks'] and base.pin(directory/FIXTURE)['sha256']==checks['fixture_binary_sha256']
        and base.file_record(directory/FIXTURE)['pe_machine']==332,
        'Executed candidate fixture bytes differ')
    return value


def package(args):
    require(re.fullmatch('[0-9a-f]{40}',args.repository_commit)
        and re.fullmatch(r'https://github\.com/Russianranger/coh-android/actions/runs/[1-9][0-9]*',args.run_url),
        'Exact candidate source and producer run required')
    require(not args.output.exists() and not args.output.is_symlink(),'Fresh candidate output required')
    old=retained.validate_package(args.baseline)
    build,retained_source=source.validate_source(args.source)
    require(retained_source==old['native_control']['build_input'],'Candidate retained Map recipe differs from completed control')
    cache=args.source/'out/build/vs2026/CMakeCache.txt';base.retained_game.validate_cmake_cache(cache)
    binary=args.source/'out/build/vs2026/bin/OptDebug/MapServer.exe';record=base.file_record(binary)
    require(record.get('pe_machine')==332 and record['imports']==old['files']['MapServer-profile.exe']['imports']
        and record['delay_imports']==old['files']['MapServer-profile.exe']['delay_imports'],
        'Candidate must retain exact Win32 DLL closure')
    raw=binary.read_bytes()
    require(b'COH_MAP_ANIMATION_METADATA_PREFETCH_V1' in raw and b'COH_NATIVE_STARTUP_PROFILE_V1' in raw,
        'Candidate optimization/profile implementation missing')
    checks=validate_checks(base.read(args.checks));fixture=args.checks.with_suffix('.fixture.exe')
    require(base.pin(fixture)['sha256']==checks['fixture_binary_sha256']
        and base.file_record(fixture)['pe_machine']==332,'Candidate executed Win32 fixture differs')
    args.output.mkdir(parents=True)
    for original,name in ((binary,BINARY),(args.checks,CHECKS),(fixture,FIXTURE)):
        shutil.copyfile(original,args.output/name)
    value={'format':1,'role':'nonshipping_map_metadata_prefetch','repository_commit':args.repository_commit,
        'run_url':args.run_url,'build_targets':['MapServer'],'architecture':'Win32','configuration':'OptDebug',
        'publication_allowed':False,'native_world_executed':False,'native_preload_executed':False,
        'native_game_changed':False,'physical_device_executed':False,'build_input':build,
        'retained_build':retained.provenance(),'retained_package':base.pin(args.baseline/base.MANIFEST),
        'retained_control_binary':old['native_control']['binary'],
        'retained_observed_binary':old['files']['MapServer-profile.exe'],
        'binary':record,'cmake_cache':base.pin(cache),'native_checks':checks,
        'scope':'One new experimental MapServer; host preload/world gates and physical acceptance remain separate'}
    base.write(args.output/MANIFEST,value)
    return validate(args.output,args.repository_commit,args.baseline)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','baseline','checks','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--repository-commit',required=True);p.add_argument('--run-url',required=True)
    args=p.parse_args();package(args);print('nonshipping Map metadata prefetch candidate packaged; runtime acceptance pending')
