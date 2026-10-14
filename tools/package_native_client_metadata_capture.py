#!/usr/bin/env python3
"""Package one fresh capture-only Game/probe without replacing native donors.

The output is a qualification-only native artifact. An actual Game runtime,
Atlas/Kings behavior and AYN Thor performance remain separate acceptance gates.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
import zipfile

import prepare_native_client_metadata_census_source as source
from map_startup_namespace_certificate import require
from package_reference_runtime import file_record, dependency_report

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/android/interactive'))
import package_client_render_queue_native as retained

ROLE = 'native_client_metadata_capture_bridge'
MANIFEST = 'native-client-metadata-capture-package.json'
CHECKS = 'native-client-metadata-capture-host-checks.json'
FIXTURE = 'native-client-wfd-probe.exe'
PROBE_CHECKS = 'native-client-wfd-probe-windows-checks.json'
HOST_MODULES = ('test_native_client_census_stat_source', 'test_native_client_census_capture_source',
    'test_native_client_metadata_census_source', 'test_native_client_metadata_census_decode',
    'test_package_native_client_metadata_capture', 'test_native_client_wfd_probe')
MEMBERS = frozenset(('CityOfHeroes.exe', CHECKS, FIXTURE, PROBE_CHECKS, source.RECEIPT, 'CMakeCache.txt', 'UtilitiesLib.vcxproj'))
APK = {'bytes': 42076692, 'sha256': '14d88da1796d155dc1b98e45ac642c7702ff3286e7ef0f2a0772f8e48693b12f'}
DONOR_SOURCE = '3570430cefdb15d9b239563e85cccf4d8fe6f32e'
GAME_SHA = '5f9597fac6e5c4eb2bf6ab091a8b2b5d71c341371da04dc135cef7e5fe00010b'
GAME_BYTES = 9499648
SCOPE = {
    'replacement_scope': 'CityOfHeroes.exe_only', 'native_game_compiled_in_current_run': True,
    'native_donor_recompiled': False, 'retained_native_dependencies_changed': False,
    'cache_schema_changed': False, 'source_freshness_changed': False, 'renderer_changed': False,
    'native_game_runtime_qualified': False, 'native_wine_executed': False,
    'physical_device_executed': False, 'publication_allowed': False,
    'probe_is_qualification_only': True, 'provider_authority_granted': False,
}
MANIFEST_KEYS = frozenset(('format', 'role', 'repository_commit', 'source_commit', 'data_commit', 'run_url',
    'architecture', 'configuration', 'build_targets', 'build_input', 'retained_game_build_input',
    'historical_source_receipts', 'validated_sources_sha256', 'schema_sources_sha256', 'cmake_cache',
    'retained_public_client', 'portable_source_controls', 'native_wfd_probe', 'native_wfd_probe_source', 'windows_probe_controls', 'files', 'artifact_members', 'scope', 'qualification_scope'))


def regular(path, maximum=64 * 1024**2):
    path = Path(path)
    require(not any(p.is_symlink() for p in (path, *path.parents)) and path.is_file()
            and 0 < path.stat().st_size <= maximum, 'Bounded regular native input required: ' + str(path))
    return path


def pin(path):
    path = regular(path)
    return {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def read(path):
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'Duplicate native receipt key')
            result[key]=value
        return result
    return json.loads(regular(path, 8 * 1024**2).read_text(encoding='utf-8-sig'),object_pairs_hook=pairs)


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n', encoding='utf-8')


def exact(actual, expected, message):
    require(retained.typed_equal(actual, expected), message)


def identity(commit, run_url=None):
    require(isinstance(commit, str) and re.fullmatch(r'[0-9a-f]{40}', commit), 'Exact native source commit required')
    if run_url is not None:
        require(isinstance(run_url, str) and re.fullmatch(
            r'https://github\.com/Russianranger/coh-android/actions/runs/[1-9][0-9]*', run_url),
            'Exact current Actions producer required')


def validate_fixture(value, fixture=None):
    require(type(value) is dict and set(value) == {'format','role','status','repository_commit','source_recipe','host_tests','host_modules','host_control_sources','native_windows_executed','native_game_executed','publication_allowed'}
            and type(value['format']) is int and value['format']==1 and value['role']=='portable_source_controls_for_native_capture'
            and value['status']=='passed' and type(value['host_tests']) is int and value['host_tests'] >= 50
            and value['native_windows_executed'] is False and value['native_game_executed'] is False
            and value['publication_allowed'] is False, 'Exact source-only host controls required')
    identity(value['repository_commit'])
    exact(value['source_recipe'], source.expected_receipt(), 'Current capture source recipe differs')
    exact(value['host_modules'],list(HOST_MODULES),'Complete host-control inventory differs')
    exact(value['host_control_sources'],{name:pin(ROOT/'tools'/(name+'.py')) for name in HOST_MODULES},'Current host-control source bytes differ')
    return value


def host_checks(args):
    identity(args.repository_commit)
    output=Path(args.output)
    require(not output.exists() and not any(p.is_symlink() for p in (output,*output.parents)), 'Fresh host-control receipt required')
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in HOST_MODULES)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    require(result.wasSuccessful() and not result.skipped, 'All current host controls required, no skipped cases')
    value={'format':1,'role':'portable_source_controls_for_native_capture','status':'passed',
        'repository_commit':args.repository_commit,'source_recipe':source.expected_receipt(),'host_tests':result.testsRun,
        'host_modules':list(HOST_MODULES),'host_control_sources':{name:pin(ROOT/'tools'/(name+'.py')) for name in HOST_MODULES},
        'native_windows_executed':False,'native_game_executed':False,'publication_allowed':False}
    validate_fixture(value)
    output.parent.mkdir(parents=True,exist_ok=True)
    write(output,value)
    return value


def validate_probe(path):
    actual=file_record(regular(path))
    require(actual['pe_machine']==332 and actual['size']>0, 'Fresh Win32 metadata probe required')
    require(set(actual['imports']).issubset({'KERNEL32.dll','ADVAPI32.dll','USER32.dll'}) and not actual['delay_imports'],
            'Read-only probe unexpected native DLL dependency')
    require(b'COH_NATIVE_WFD_PROBE_V1' in Path(path).read_bytes(), 'Exact metadata probe marker missing')
    return actual


def validate_probe_checks(value, probe, *, contract=None, source_pin=None):
    if contract is None:
        import test_native_client_wfd_probe as contract
    if source_pin is None:
        source_pin=pin(ROOT/'tools/native_client_wfd_probe.c')
    expected={'format':1,'role':'Windows_SDK_readonly_ANSI_metadata_probe_fixture','status':'passed',
        'source_sha256':source_pin['sha256'],
        'probe':pin(probe),'observed_ABI':{'pointer_bits':32,'WFD_bytes':320,'by_handle_bytes':52,'header_bytes':160},
        'actual_windows_sdk_executed':True,'native_Wine_executed':False,'native_Game_executed':False,
        'physical_device_executed':False,'current_provider_generation_qualified':False,
        'provider_authority':False,'publication_allowed':False}
    require(type(value) is dict and set(value)==set(expected)|{'cases','observed_rows'},'Exact native SDK probe receipt required')
    for name,item in expected.items():exact(value[name],item,'Native SDK source/exe/scope differs: '+name)
    labels=['complete_readonly_named_dot_empty_branches','existing_output_refused','sharing_denial_explicit_incomplete','output_inside_readonly_inputs_refused']
    require(type(value['cases']) is list and len(value['cases'])==4,'Four exact native SDK probe controls required')
    packets=[]; observations=[]
    for index,(case,label) in enumerate(zip(value['cases'],labels)):
        require(type(case) is dict and set(case)=={'label','returncode','receipt','status','stdout_base64','stderr_base64','packet_base64','packet_bytes','packet_sha256'}
            and case['label']==label and type(case['returncode']) is int and type(case['packet_bytes']) is int,'Native SDK control identity/types differ')
        decoded=[]
        for name,bound in [('stdout_base64',16384),('stderr_base64',16384),('packet_base64',1024**2)]:
            require(type(case[name]) is str and len(case[name])<=4*((bound+2)//3),'Bounded raw native SDK material required')
            raw=base64.b64decode(case[name],validate=True)
            require(len(raw)<=bound,'Native SDK material too large')
            decoded.append(raw)
        stdout,stderr,packet=decoded
        require(case['packet_bytes']==len(packet) and case['packet_sha256']==(hashlib.sha256(packet).hexdigest() if packet else None),'Native SDK raw packet differs')
        lines=[line for line in stdout.decode('ascii').splitlines() if line.startswith(contract.MARKER)]
        require(len(lines)==1 and json.loads(lines[0][len(contract.MARKER):])==case['receipt'],'Native SDK raw console receipt differs')
        receipt=case['receipt']
        require(type(receipt) is dict and set(receipt)=={'format','status','operation','generation','windows_pid','rows','directories','bytes','issues','output_created','exact_handle_cleanup_marked','output_handle_closed','provider_authority','publication_allowed'}
            and type(receipt['format']) is int and receipt['format']==1
            and all(type(receipt[name]) is int and 0<=receipt[name]<=0xffffffff for name in ('windows_pid','rows','directories','bytes','issues'))
            and all(type(receipt[name]) is bool for name in ('output_created','exact_handle_cleanup_marked','output_handle_closed','provider_authority','publication_allowed'))
            and type(receipt['status']) is str and receipt['windows_pid']>0
            and receipt.get('generation')==contract.GENERATION and receipt.get('operation')==contract.OPERATION
            and receipt.get('provider_authority') is False and receipt.get('publication_allowed') is False,'Native SDK current raw identity/scope differs')
        require(case['returncode']==[0,2,2,64][index]
            and receipt['status']==['complete_observation','exclusive_output_refused','incomplete_observation','arguments_or_abi_refused'][index]
            and receipt['exact_handle_cleanup_marked'] is False
            and receipt['output_created']==(index in (0,2)) and receipt['output_handle_closed']==(index in (0,2)), 'Exact native SDK outcome/cleanup differs')
        observed=None
        if label in (labels[0],labels[2]):
            require(len(packet)>256 and receipt.get('output_created') is True and receipt.get('output_handle_closed') is True,'Actual native SDK sidecar/cleanup missing')
            root_bytes=contract.u32(packet,172)
            root=packet[256:256+root_bytes].decode('ascii')
            observed=contract.parse(packet,contract.GENERATION,contract.OPERATION,root,receipt['windows_pid'])
            require(observed['status']==case['status'] and receipt['rows']==observed['footer']['rows'] and receipt['issues']==observed['footer']['issues']
                and receipt['directories']==len(observed['directories']) and receipt['bytes']==len(packet), 'Native SDK parsed observation differs')
        else:
            require(receipt['rows']==receipt['directories']==receipt['bytes']==receipt['issues']==0,'Refused SDK output fabricated work')
        packets.append(packet);observations.append(observed)
    require(value['cases'][0]['returncode']==0 and observations[0]['status']=='complete_observation'
        and type(value['observed_rows']) is int and value['observed_rows']==observations[0]['footer']['rows']>0,'Actual native SDK complete observation missing')
    require(value['cases'][1]['returncode']!=0 and value['cases'][1]['receipt'].get('output_created') is False
        and packets[1]==packets[0] and value['cases'][1]['status'] is None,'SDK existing output was changed')
    require(value['cases'][2]['returncode']!=0 and observations[2]['status']=='incomplete_observation'
        and not observations[2]['footer']['readability_complete']
        and any(row['by_handle']['create_error']==32 for directory in observations[2]['directories'] for row in directory['entries']),'SDK sharing failure became success/absence')
    require(value['cases'][3]['returncode']==64 and not packets[3] and value['cases'][3]['receipt'].get('output_created') is False
        and value['cases'][3]['status'] is None,'SDK readonly input output refusal missing')
    return value


def donor(apk):
    exact(pin(apk), APK, 'Exact independently audited public .36 APK required')
    with zipfile.ZipFile(apk) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())), 'Duplicate donor APK member')
        raw = archive.read('assets/runtime/client-runtime.zip')
        outer = archive.read('assets/runtime/client-manifest.json')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) == len({n.casefold() for n in names}) and
                all(re.fullmatch(r'[A-Za-z0-9_.-]+', n) for n in names), 'Duplicate/aliased retained native member')
        require('client-package.json' in names, 'Retained native package receipt missing')
        raw_manifest = archive.read('client-package.json')
        manifest = json.loads(raw_manifest)
        records = manifest.get('files', {})
        require(type(records) is dict and set(names) == set(records) | {'client-package.json'}
                and manifest.get('server_executables_included') is False, 'Retained native member closure differs')
        require(records['CityOfHeroes.exe']['sha256'] == GAME_SHA and records['CityOfHeroes.exe']['size'] == GAME_BYTES,
                'Retained public Game identity differs')
        actual = {}
        with tempfile.TemporaryDirectory(prefix='coh-census-donor-') as temporary:
            for name in sorted(records):
                data = archive.read(name)
                require(0 < len(data) <= 64 * 1024**2, 'Unbounded retained donor payload')
                path = Path(temporary) / name
                path.write_bytes(data)
                actual[name] = file_record(path)
        exact(actual, records, 'Retained native DLL/Game bytes or imports differ from original receipt')
        exact(dependency_report(actual), manifest['dependency_report'], 'Retained native dependency authority differs')
        return {'donor_apk': dict(APK), 'donor_source': DONOR_SOURCE, 'native_game': actual['CityOfHeroes.exe'],
            'client_runtime_zip': {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
            'client_manifest': {'bytes': len(outer), 'sha256': hashlib.sha256(outer).hexdigest()},
            'client_package': {'bytes': len(raw_manifest), 'sha256': hashlib.sha256(raw_manifest).hexdigest()},
            'native_member_closure': actual, 'client_runtime_manifest': manifest,
            'native_donor_rebuilt': False, 'original_archive_or_receipts_rewritten': False}


def expected_closure(historical):
    require(type(historical) is dict and set(historical) == set(retained.baseline.INPUTS),
            'Historical source receipt inventory differs')
    pins = {}
    for key, value in historical.items():
        exact(value, retained.baseline.expected_source_receipt(key, value), 'Historical source producer differs: ' + key)
        for field in ('patched_sha256', 'overlay_sha256', 'graphics_overlay_sha256', 'events_overlay_sha256'):
            pins.update(value.get(field, {}))
    producers, current = [], retained
    while hasattr(current, 'expected_receipt'):
        producers.append(current)
        if not hasattr(current, 'base'):
            break
        current = current.base
    for producer in reversed(producers):
        previous = producer.expected_receipt()
        for field in ('native_callsite_sources_sha256', 'patched_sha256', 'overlay_sha256'):
            pins.update(previous.get(field, {}))
    for name, value in retained.baseline.schema_pins().items():
        pins.setdefault(name, value)
    new = source.expected_receipt()
    require(pins.get(source.SOURCE) == new['source_sha256'][source.SOURCE], 'Retained constructor predecessor differs')
    pins.update(new['patched_sha256']); pins.update(new['overlay_sha256'])
    pins[source.NODE_SOURCE] = new['source_sha256'][source.NODE_SOURCE]
    pins[source.STAT_SOURCE] = new['patched_sha256'][source.STAT_SOURCE]
    pins[source.CMAKE_INJECTION] = new['cmake_injection_sha256']
    return pins


def validate_game(path, inherited):
    path = regular(path)
    actual = file_record(path)
    previous = inherited['native_game']
    require(actual['pe_machine'] == previous['pe_machine'] == 332 and actual['sha256'] != previous['sha256'],
            'Fresh changed Win32 Game required')
    exact(actual['imports'], previous['imports'], 'Retained Game native DLL/ABI closure differs')
    exact(actual['delay_imports'], previous['delay_imports'], 'Retained Game delay imports differ')
    require(b'COH_NATIVE_PIG_INDEX_CAPTURE_V1' in path.read_bytes(), 'Compiled Game lacks constructor marker')
    return actual


def validate_cache(path):
    regular(path, 8 * 1024**2)
    value=retained.validate_cmake_cache(path)
    text=path.read_text(encoding='utf-8-sig')
    require(re.search(r'^CMAKE_PROJECT_INCLUDE:(?:FILEPATH|UNINITIALIZED|STRING)=.*[/\\]'+re.escape(source.CMAKE_INJECTION)+r'$',text,re.MULTILINE), 'Exact capture CMake injection required')
    require(re.search(r'^COX_BUILD_MAPSERVER:BOOL=OFF$',text,re.MULTILINE) and re.search(r'^COX_BUILD_BEACONSERVER:BOOL=OFF$',text,re.MULTILINE), 'Game-only native capture configure required')
    return value


def stage(args):
    retained.stage(args)
    source.stage(args.output)
    return source.validate_staged_source(args.output)


def package(args):
    identity(args.repository_commit, args.run_url)
    output = Path(args.output)
    require(not output.exists() and not any(p.is_symlink() for p in (output, *output.parents)), 'Fresh regular native package required')
    inputs = source.validate_staged_source(args.source)
    cmake = validate_cache(args.cache)
    inherited = donor(args.donor_apk)
    fixture = regular(args.probe)
    checks = validate_fixture(read(args.checks))
    require(checks['repository_commit']==args.repository_commit, 'Current source controls commit differs')
    probe_record = validate_probe(fixture)
    probe_checks=validate_probe_checks(read(args.probe_checks),fixture)
    project=regular(args.utilities_project, 8*1024**2)
    require(b'COH_CLIENT_METADATA_CENSUS_CAPTURE=1' in project.read_bytes() and b'COH_CLIENT_METADATA_CENSUS_PROTOTYPE' not in project.read_bytes(), 'Native capture private define/replay exclusion missing')
    binary = Path(args.directory) / 'CityOfHeroes.exe'
    require(Path(args.directory).name == 'OptDebug', 'Explicit OptDebug Game output directory required')
    actual = validate_game(binary, inherited)
    exact(inputs['validated_sources_sha256'], expected_closure(inputs['historical_source_receipts']), 'Staged source closure differs')
    output.mkdir(parents=True)
    for original, name in ((binary, 'CityOfHeroes.exe'), (args.checks, CHECKS), (fixture, FIXTURE),
                           (Path(args.source) / source.RECEIPT, source.RECEIPT), (args.cache, 'CMakeCache.txt'),
                           (project, 'UtilitiesLib.vcxproj'), (args.probe_checks,PROBE_CHECKS)):
        shutil.copyfile(regular(original), output / name)
    value = {'format': 1, 'role': ROLE, 'repository_commit': args.repository_commit,
        'source_commit': retained.baseline.contract.SOURCE, 'data_commit': retained.baseline.contract.DATA,
        'run_url': args.run_url, 'architecture': 'Win32', 'configuration': 'OptDebug', 'build_targets': ['Game'],
        'build_input': inputs['source'], 'retained_game_build_input': inputs['retained_game_build_input'],
        'historical_source_receipts': inputs['historical_source_receipts'],
        'validated_sources_sha256': inputs['validated_sources_sha256'],
        'schema_sources_sha256': {n: inputs['validated_sources_sha256'][n] for n in retained.baseline.schema_pins()},
        'cmake_cache': cmake, 'retained_public_client': inherited, 'portable_source_controls': checks, 'native_wfd_probe': probe_record, 'native_wfd_probe_source': pin(ROOT / 'tools/native_client_wfd_probe.c'), 'windows_probe_controls':probe_checks,
        'files': {'CityOfHeroes.exe': actual, FIXTURE: probe_record}, 'artifact_members': {p.name: pin(p) for p in sorted(output.iterdir())},
        'scope': dict(SCOPE),
        'qualification_scope': 'Full Win32 capture-only Game and read-only metadata probe compilation, inherited source/DLL closure and portable controls; native execution/provider authority/performance remain separate gates'}
    write(output / MANIFEST, value)
    return validate_package(output, args.repository_commit, args.donor_apk)


def validate_package(directory, commit, donor_apk):
    directory = Path(directory)
    identity(commit)
    require(directory.is_dir() and not any(p.is_symlink() for p in (directory, *directory.parents)), 'Regular native artifact root required')
    require({p.name for p in directory.iterdir()} == MEMBERS | {MANIFEST}, 'Exact Game-only artifact member closure differs')
    for name in MEMBERS | {MANIFEST}:
        regular(directory / name)
    value = read(directory / MANIFEST)
    require(type(value) is dict and set(value) == MANIFEST_KEYS and type(value.get('format')) is int and value['format'] == 1
            and value.get('role') == ROLE and value.get('repository_commit') == commit,
            'Typed native artifact producer differs')
    identity(commit, value.get('run_url'))
    for name, expected in {'source_commit': retained.baseline.contract.SOURCE, 'data_commit': retained.baseline.contract.DATA,
        'architecture': 'Win32', 'configuration': 'OptDebug', 'build_targets': ['Game'], 'scope': SCOPE}.items():
        exact(value.get(name), expected, 'Native source/build/scope differs: ' + name)
    exact(value.get('build_input'), source.expected_receipt(), 'Candidate source recipe changed')
    exact(read(directory / source.RECEIPT), value['build_input'], 'Archived constructor source receipt differs')
    exact(value.get('retained_game_build_input'), retained.expected_receipt(), 'Retained Game source recipe changed')
    pins = expected_closure(value['historical_source_receipts'])
    exact(value.get('validated_sources_sha256'), pins, 'Native source closure changed')
    exact(value.get('schema_sources_sha256'), {n: pins[n] for n in retained.baseline.schema_pins()}, 'Read-only serializer schema pins changed')
    exact(value.get('artifact_members'), {n: pin(directory / n) for n in MEMBERS}, 'Native artifact bytes changed')
    checks = validate_fixture(read(directory / CHECKS))
    require(checks['repository_commit'] == commit, 'Exact current host-control producer changed')
    exact(value.get('portable_source_controls'), checks, 'Executed source-only controls changed')
    probe_record = validate_probe(directory / FIXTURE)
    exact(value.get('native_wfd_probe'), probe_record, 'Actual Win32 metadata probe changed')
    exact(value.get('native_wfd_probe_source'), pin(ROOT / 'tools/native_client_wfd_probe.c'), 'Exact native metadata probe source changed')
    exact(value.get('windows_probe_controls'),validate_probe_checks(read(directory/PROBE_CHECKS),directory/FIXTURE),'Actual native SDK material changed')
    project = regular(directory / 'UtilitiesLib.vcxproj', 8 * 1024**2)
    require(b'COH_CLIENT_METADATA_CENSUS_CAPTURE=1' in project.read_bytes() and
            b'COH_CLIENT_METADATA_CENSUS_PROTOTYPE' not in project.read_bytes(), 'Native private capture define changed')
    inherited = donor(donor_apk)
    exact(value.get('retained_public_client'), inherited, 'Original public Game/DLL donor changed')
    actual = validate_game(directory / 'CityOfHeroes.exe', inherited)
    exact(value.get('files'), {'CityOfHeroes.exe': actual, FIXTURE: probe_record}, 'Exact Game/probe executable identity differs')
    exact(value.get('cmake_cache'), validate_cache(directory / 'CMakeCache.txt'), 'Actual CMake provenance changed')
    require(value.get('qualification_scope') == 'Full Win32 capture-only Game and read-only metadata probe compilation, inherited source/DLL closure and portable controls; native execution/provider authority/performance remain separate gates',
            'Native runtime qualification scope changed')
    return value


# Preserve the short draft API name for existing external callers.
validate = validate_package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('stage'); command.add_argument('--output', type=Path, required=True)
    command = commands.add_parser('host-checks'); command.add_argument('--output', type=Path, required=True)
    command.add_argument('--repository-commit', required=True)
    command = commands.add_parser('package')
    for name in ('source', 'directory', 'cache', 'checks', 'donor-apk', 'output', 'probe', 'probe-checks', 'utilities-project'):
        command.add_argument('--' + name, type=Path, required=True)
    command.add_argument('--repository-commit', required=True); command.add_argument('--run-url', required=True)
    command = commands.add_parser('validate')
    for name in ('directory', 'donor-apk'):
        command.add_argument('--' + name, type=Path, required=True)
    command.add_argument('--repository-commit', required=True)
    args = parser.parse_args()
    result = host_checks(args) if args.command == 'host-checks' else stage(args) if args.command == 'stage' else package(args) if args.command == 'package' else validate_package(
        args.directory, args.repository_commit, args.donor_apk)
    print(json.dumps({'status': 'nonshipping_native_stage_or_package_validated', 'role': ROLE, 'publication_allowed': False}))


if __name__ == '__main__': main()
