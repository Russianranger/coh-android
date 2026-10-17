#!/usr/bin/env python3
"""Strict Android13 CPU rigid/resource execution. No GLES or world acceptance."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=module('rigid_bounded_android',HERE.parent/'continuation/run_adapter_android.py')
c=base.c
contract=module('rigid_android_contract',HERE/'rigid_android_contract.py')
fixture=module('rigid_authored_fixtures',HERE/'tests/rigid_fixture.py')
REQUIRED={str(p.relative_to(ROOT)) for p in (Path(__file__),HERE/'check_rigid.py',HERE/'rigid_android_contract.py',
    HERE/'coh_wr_rigid.c',HERE/'coh_wr_rigid.h',HERE/'tests/test_rigid.c',HERE/'tests/test_rigid_actual.c',
    HERE/'tests/rigid_fixture.py',HERE/'tests/test_rigid_android.py',HERE/'rigid-authentic-pins.json',
    HERE/'rigid-source-pins.json',HERE.parent/'continuation/run_adapter_android.py',Path(c.__file__))}
REQUIRED.update('native-android/'+name for name in (
    'engine/assets/coh_asset_loader.c','engine/assets/coh_asset_loader.h',
    'engine/assets/coh_asset_geo.c','engine/assets/coh_asset_geo.h',
    'engine/renderer/coh_renderer.c','engine/renderer/coh_renderer.h',
    'engine/renderer/coh_renderer_shaders.h','engine/coh_contracts.h',
    'engine/world-render-adapter/coh_world_render.h','engine/world-render-adapter/acquire_rigid.py',
    'src/coh_assets.c','src/coh_dds.c','src/byte_reader.h','include/coh_native_core.h',
    'tools/material_fixture/original_delta_check.py'))
REQUIRED.update(c.read(HERE/'rigid-source-pins.json')['source_sha256'])
DIGEST_MODE='exact-fixture-byte-equality replay; not cryptographic execution'


def validate(artifacts,repo,checkout=True):
    proof=c.read(c.child(artifacts,'qualification.json'))
    if (proof.get('schema')!='coh-rigid-v8-qualification-v1' or proof.get('passed') is not True
            or proof.get('clean_source_inputs') is not True or proof.get('source_inputs_unchanged') is not True
            or proof.get('android_built') is not True or proof.get('android_executed') is not False
            or proof.get('world_authority') is not False or proof.get('host_fixture_digest_replay_qualified') is not True):raise ValueError('Clean source-only crossbuild qualification required')
    sources=c.source_hashes(proof.get('source_sha256'))
    if not REQUIRED.issubset(sources):raise ValueError('Required rigid driver/build sources omitted')
    for running in (Path(__file__),Path(contract.__file__),Path(fixture.__file__),Path(base.__file__),Path(c.__file__)):
        relative=running.resolve().relative_to(ROOT).as_posix()
        if c.digest(running)!=sources[relative]:raise ValueError('Executing rigid driver/helper source differs')
    if checkout:base.validate_checkout(repo,proof)
    if set(proof.get('modes',{}))!={'release','address','undefined'}:raise ValueError('All host modes required')
    actual=proof.get('authentic_geo_v8_fixture_available')
    if type(actual) is not bool:raise ValueError('Explicit authentic geometry scope required')
    for mode in ('release','address','undefined'):
        value=proof['modes'][mode];contract.result(value.get('result'))
        c.hash_value(value.get('binary_sha256'))
        if actual:
            contract.result(value.get('actual',{}).get('result'),True)
            c.hash_value(value.get('actual',{}).get('binary_sha256'))
    if (proof.get('producer_layout',{}).get('original_structs_unchanged') is not True
            or proof['producer_layout'].get('offsets')!=[244,0,4,8,12,16,20,24,28,32,64,68,72,108,228,240]
            or proof.get('delta_packet_oracle',{}).get('passed') is not True):raise ValueError('Original producer/delta host oracle absent')
    expected_packets={'authored':c.hash_value(proof['delta_packet_oracle'].get('packet_sha256'))}
    if actual:
        oracle=proof.get('authentic_geometry_oracle',{})
        if (oracle.get('passed') is not True or oracle.get('payload_sha256')!=contract.ACTUAL_SHA
                or oracle.get('material_fixture_only') is not True or oracle.get('loaded_generation_fixture_only') is not True
                or oracle.get('world_authority') is not False):raise ValueError('Authentic geometry scope differs')
        expected_packets['authentic']=c.hash_value(oracle.get('packet_sha256'))
    replay=proof.get('host_fixture_digest_replay',{})
    if set(replay)!=set(expected_packets):raise ValueError('Host digest replay corpus absent')
    for name,packet in expected_packets.items():
        contract.result(replay[name].get('result'),name=='authentic');c.hash_value(replay[name].get('binary_sha256'))
        if replay[name].get('packet_sha256')!=packet:raise ValueError('Host digest replay differs from original oracle')
    fixture_bytes={kind+'.geo':fixture.geo(kind) for kind in contract.KINDS}
    if actual:fixture_bytes['authentic.geo']=c.child(artifacts,'fixtures/authentic.geo').read_bytes()
    fixtures_sha={name:hashlib.sha256(raw).hexdigest() for name,raw in fixture_bytes.items()}
    if not contract.equal(proof.get('fixtures_sha256'),fixtures_sha):raise ValueError('Host fixture inventory differs')
    if actual and fixtures_sha['authentic.geo']!=contract.ACTUAL_SHA:raise ValueError('Authentic fixture changed')
    for name,raw in fixture_bytes.items():
        if c.child(artifacts,'fixtures/'+name).read_bytes()!=raw:raise ValueError('Authored fixture differs from admitted generator')
    header=c.child(artifacts,'rigid_fixture_digests.h')
    if proof.get('fixture_digest_header_sha256')!=c.digest(header) or header.read_bytes()!=contract.digest_header(fixture_bytes):raise ValueError('Exact fixture digest replay header differs')
    builds=proof.get('android_builds',{})
    if set(builds)!=set(contract.ABIS):raise ValueError('Both ABI builds required')
    entries={}
    for abi in contract.ABIS:
        path=c.child(artifacts,'android/'+abi+'/build.json');build=c.read(path)
        if (not contract.equal(build,builds[abi]) or build.get('schema')!='coh-rigid-android-build-v1'
                or build.get('passed') is not True or build.get('abi')!=abi or build.get('api')!=26
                or build.get('executed') is not False or build.get('world_authority') is not False
                or build.get('source_revision')!=proof.get('source_revision') or build.get('source_tree')!=proof.get('source_tree')
                or not contract.equal(build.get('source_sha256'),sources)
                or not contract.equal(build.get('fixtures_sha256'),fixtures_sha)
                or build.get('fixture_digest_header_sha256')!=c.digest(header)
                or build.get('digest_mode')!=DIGEST_MODE or set(build.get('binaries',{}))!=set(expected_packets)):
            raise ValueError('ABI build/source/fixture scope mismatch')
        binaries={}
        for name,packet in expected_packets.items():
            value=build['binaries'][name];contract.result(value.get('expected_result'),name=='authentic')
            if (set(value)!={'binary','binary_sha256','executed','expected_result','expected_packet_sha256'}
                    or value.get('binary')!='rigid-'+name+'-test' or value.get('executed') is not False
                    or value.get('expected_packet_sha256')!=packet):raise ValueError('Native binary identity/scope differs')
            binary=c.child(artifacts,'android/'+abi+'/'+value['binary'])
            if binary.stat().st_size>32*1024*1024 or c.digest(binary)!=c.hash_value(value.get('binary_sha256')):raise ValueError('Native binary changed')
            c.elf_identity(binary,abi);binaries[name]=dict(value,path=binary)
        entries[abi]={'binaries':binaries,'build_receipt_sha256':c.digest(path)}
    return proof,entries,fixtures_sha


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--artifacts',type=Path,required=True)
    p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--validate-only',action='store_true');p.add_argument('--adb',type=Path);p.add_argument('--serial');a=p.parse_args()
    if not a.validate_only and (not a.adb or not a.serial):p.error('--adb and --serial required')
    if a.output.exists() or (a.output.parent.exists() and any(a.output.parent.iterdir())):p.error('New empty evidence directory required')
    value={'schema':'coh-rigid-android-execution-v1','passed':False,'artifact_admitted':False,
           'android_executed':False,'emulator_qualified':False,'scope':'CPU rigid resource fixtures; no GLES/material/world authority',
           'digest_mode':DIGEST_MODE,'source_oracles_executed_on_android':False,
           'physical_thor_accepted':False,'world_authority':False,'gpu_execution':False,
           'runner_sha256':c.digest(Path(__file__)),'tests':{},'errors':{}}
    remote=None;number=0
    adb=[a.adb.resolve(),'-s',a.serial] if a.adb else []
    def run(command,timeout=60):
        nonlocal number
        number+=1;return base.bounded_execute(command,a.output.parent/'logs'/('%03d.log'%number),timeout).strip()
    try:
        proof,entries,fixtures=validate(a.artifacts.resolve(),a.source_root.resolve())
        state=c.git_state(a.source_root);value.update(artifact_admitted=True,source_revision=proof['source_revision'],
            source_tree=proof['source_tree'],qualification_sha256=c.digest(a.artifacts/'qualification.json'),
            source_sha256=proof['source_sha256'],fixtures_sha256=fixtures)
        if not a.validate_only:
            run([*adb,'wait-for-device'])
            prop=lambda name:run([*adb,'shell','getprop',name])
            if prop('ro.build.version.sdk')!='33' or prop('ro.kernel.qemu')!='1' or 'x86_64' not in prop('ro.product.cpu.abilist').split(','):raise ValueError('Android13 x86_64 emulator required')
            value['device_fingerprint']=prop('ro.build.fingerprint')
            remote=run([*adb,'shell','mktemp','-d','/data/local/tmp/coh-rigid.XXXXXX'])
            if not re.fullmatch(r'/data/local/tmp/coh-rigid\.[A-Za-z0-9]+',remote):remote=None;raise ValueError('Invalid owned remote directory')
            run([*adb,'shell','mkdir',remote+'/fixtures'])
            for name,sha in fixtures.items():
                destination=remote+'/fixtures/'+name;run([*adb,'push',a.artifacts/'fixtures'/name,destination])
                if run([*adb,'shell','sha256sum',destination]).split()[0]!=sha:raise ValueError('Transferred fixture changed')
            for name,entry in entries['x86_64']['binaries'].items():
                destination=remote+'/'+entry['binary'];packet=remote+'/'+name+'.packet'
                run([*adb,'push',entry['path'],destination])
                if run([*adb,'shell','sha256sum',destination]).split()[0]!=entry['binary_sha256']:raise ValueError('Transferred ELF changed')
                run([*adb,'shell','chmod','700',destination])
                observed=value['tests'][name]={'attempted':True,'android_executed':False,'native_result_validated':False,
                                              'packet_validated':False,'binary_sha256':entry['binary_sha256']}
                try:
                    raw=run([*adb,'shell','timeout','-s','KILL','90',destination,
                             remote+'/fixtures' if name=='authored' else remote+'/fixtures/authentic.geo',packet],180)
                    observed['exit_code']=0
                except base.CommandFailure as error:observed['exit_code']=error.returncode;raise
                actual=c.loads(raw);contract.result(actual,name=='authentic');observed.update(android_executed=True,result=actual)
                value['android_executed']=True
                if not contract.equal(actual,entry['expected_result']):raise ValueError('Android result differs')
                observed['native_result_validated']=True
                if run([*adb,'shell','sha256sum',packet]).split()[0]!=entry['expected_packet_sha256']:raise ValueError('Android packet differs from original host oracle')
                observed['packet_validated']=True
            c.verify_sources(a.source_root,proof['source_sha256'])
            if c.git_state(a.source_root)!=state:raise ValueError('Source changed during execution')
            value['emulator_qualified']=True
        value['passed']=True
    except Exception as error:value['errors']['qualification']=str(error)
    finally:
        if remote is not None:
            try:run([*adb,'shell','rm','-rf',remote]);value['temporary_files_removed']=True
            except Exception as error:value['errors']['cleanup']=str(error);value['passed']=value['emulator_qualified']=False
    c.write(a.output,value);print(json.dumps({key:value[key] for key in ('passed','artifact_admitted','android_executed','emulator_qualified','errors')}))
    return 0 if value['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
