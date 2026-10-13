#!/usr/bin/env python3
"""Admit only the exact completed Windows diagnostic artifact for fresh host use.

The original recipe contains one Windows-form overlay key. Its exact bytes are
retained and checked; this is not a general path normalizer or a new build.
"""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import stat
import zipfile

import package_native_startup_profile as package
from map_startup_namespace_certificate import require

SOURCE = 'da5cf809925d9d91e029a117d8be184af03db2b6'
RUN = 38345782437
JOB = 115126749610
ARTIFACT = 11788852713
ZIP = {'bytes':10573060,'sha256':'5e276ccebb3b7a24564839a32eabcb98accc5a18f62ec0de2440b7efe690d025'}
FILES = {
    'native-startup-control.json': {'bytes':48350,'sha256':'15d60b833a5992ecd8780ffb1313d832dcabb2ffa1a5fdb9adb46f0e1314e32c'},
    'native-startup-profile-package.json': {'bytes':106482,'sha256':'96a6c1e0fb64e54806305a5474127120a2de1367a8ebd96d67848b13928a40f1'},
    'MapServer-control.exe': {'bytes':7477248,'sha256':'77c1f245132b76668e9f689bec26699ec980382c1079f000314d24b149e089ea'},
    'MapServer-profile.exe': {'bytes':7478784,'sha256':'fbfcf1d80a41a80aaeecb1a0ec275daffed2a9e1ba25df3f16e23b16a51a493d'},
    'CityOfHeroes-profile.exe': {'bytes':9474048,'sha256':'338172fe57ae9ce303797f784d85c5c9e3a2f768b3373fc5340dfd78f8b75020'},
    'native-cg-control-flow.exe': {'bytes':140288,'sha256':'fe8dec7f69db57f3970a9e9508dc454c328b992b2af9bcae2089340da456ebe4'},
    'native-cg-windows-checks.json': {'bytes':1741,'sha256':'8e2a84d13310f1b414892e146b626a308688b4ed5b4595c1365769058e298be3'},
}
POSIX_OVERLAY = 'Game/src/render/thread/coh_native_cg_profile.h'
WINDOWS_OVERLAY = 'Game\\src\\render\\thread\\coh_native_cg_profile.h'


def validate_recipe(value, source=SOURCE):
    require(source == SOURCE and value.get('repository_commit') == SOURCE
        and value.get('run_url') == f'https://github.com/Russianranger/coh-android/actions/runs/{RUN}',
        'Exact historical native producer required')
    require(value.get('role') == 'nonshipping_native_startup_profile'
        and all(value.get(k) is False for k in ('publication_allowed','native_game_executed',
            'map_world_entry_executed','physical_device_executed')), 'Historical native claim changed')
    require(value.get('map_profile') == package.map_profile.expected_receipt(), 'Map diagnostic source changed')
    expected = copy.deepcopy(package.cg_profile.expected_receipt())
    require(set(expected['overlay_sha256']) == {POSIX_OVERLAY}, 'Canonical current Cg path required')
    expected['overlay_sha256'] = {WINDOWS_OVERLAY: expected['overlay_sha256'][POSIX_OVERLAY]}
    require(value.get('cg_profile') == expected and value.get('cg_control_flow',{}).get('source') == expected,
        'Historical Cg recipe differs beyond the one authenticated Windows path')
    require(value['cg_control_flow'].get('status') == 'passed'
        and value['cg_control_flow'].get('native_windows_executed') is True
        and value['cg_control_flow'].get('gpu_executed') is False
        and value['cg_control_flow'].get('cases') == 10, 'Historical native fixture claim differs')
    return value


def validate_package(directory, source=SOURCE):
    directory = Path(directory)
    require(directory.is_dir() and not any(p.is_symlink() for p in (directory,*directory.parents)),
        'Regular private historical package required')
    require({p.name for p in directory.iterdir()} == set(FILES), 'Historical artifact member closure changed')
    for name,record in FILES.items():
        require(package.pin(directory/name) == record, 'Authenticated historical member changed: '+name)
    value = validate_recipe(package.read(directory/package.MANIFEST),source)
    require(package.read(directory/package.CONTROL) == value['native_control'], 'Historical control receipt changed')
    require(package.file_record(directory/'MapServer-control.exe') == value['native_control']['binary'],
        'Historical control PE changed')
    for name,record in value['files'].items():
        require(package.file_record(directory/name) == record, 'Historical observed PE changed: '+name)
    checks = package.read(directory/'native-cg-windows-checks.json')
    require(checks == value['cg_control_flow'] and checks['fixture_binary_sha256'] == FILES['native-cg-control-flow.exe']['sha256'],
        'Historical Windows fixture bytes changed')
    return value


def provenance():
    return {'native_source_commit':SOURCE,'run_id':RUN,'successful_windows_job_id':JOB,
        'artifact_id':ARTIFACT,'artifact_zip':ZIP,'native_members':FILES,
        'native_bytes_changed':False,'native_rebuild_performed':False,'original_receipt_bytes_changed':False,
        'accepted_receipt_difference':'exact_historical_Cg_overlay_Windows_path_only',
        'overall_historical_workflow_claimed_successful':False,'publication_allowed':False}


def validate_metadata(run, jobs, artifact):
    require(run.get('id') == RUN and run.get('head_sha') == SOURCE
        and run.get('head_branch') == 'codex/native-startup-profile-036'
        and run.get('path') == '.github/workflows/android-native-startup-profile.yml',
        'Historical workflow identity differs')
    native = [j for j in jobs.get('jobs',[]) if j.get('id') == JOB]
    require(len(native) == 1 and native[0].get('name') == 'native'
        and native[0].get('status') == 'completed' and native[0].get('conclusion') == 'success',
        'Original completed Windows job must remain successful')
    require(artifact.get('id') == ARTIFACT and artifact.get('name') == 'coh-nonshipping-native-startup-profile'
        and artifact.get('expired') is False and artifact.get('size_in_bytes') == ZIP['bytes']
        and artifact.get('digest') == 'sha256:'+ZIP['sha256']
        and artifact.get('workflow_run',{}).get('id') == RUN
        and artifact['workflow_run'].get('head_sha') == SOURCE,
        'Historical artifact producer or bytes differ')
    return {'run_status':run.get('status'),'run_conclusion':run.get('conclusion'),
        'windows_job_status':'completed','windows_job_conclusion':'success'}


def extract(archive, output):
    archive,output = Path(archive),Path(output)
    require(package.pin(archive) == ZIP, 'Exact historical artifact ZIP required')
    require(not output.exists() and not output.is_symlink()
        and not any(p.is_symlink() for p in output.parents), 'Fresh unlinked artifact destination required')
    with zipfile.ZipFile(archive) as source:
        members = source.infolist()
        require(len(members) == len(FILES) and {m.filename for m in members} == set(FILES),
            'Exact historical ZIP members required')
        for member in members:
            require(not member.is_dir() and not stat.S_ISLNK(member.external_attr >> 16)
                and member.file_size == FILES[member.filename]['bytes'], 'Historical ZIP entry differs')
        output.mkdir(parents=True)
        for member in members:
            (output/member.filename).write_bytes(source.read(member))
    validate_package(output)
    return provenance()


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    for name in ('run-metadata','jobs-metadata','artifact-metadata'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    api=validate_metadata(package.read(args.run_metadata),package.read(args.jobs_metadata),package.read(args.artifact_metadata))
    value=extract(args.archive,args.output);value['historical_API_status']=api
    print(json.dumps(value,sort_keys=True))
