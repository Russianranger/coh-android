#!/usr/bin/env python3
"""Create an explicit owned native fixture; this is not Android cache authority.

The original .31 fixture is immutable. The exact retained control executable
must regenerate exactly the 18 dependency-header changes observed independently
in both real native processes. Then separate fresh processes must prove reuse.
All hashing below is host fixture admission, outside measured native launch.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import stat
import struct
import package_native_startup_profile as package
import reuse_native_startup_profile as retained
from map_startup_namespace_certificate import require

CAPTURE={'source':'3c532f5b9b9dd07767f0250c188456adc57ed5ab','run_id':38350025346,
 'artifact_id':11790372043,'zip_sha256':'9ed128508144bdfa61541c97f6cbc3a374dfdc1b47fc4e2b4242a3a0668c94d5',
 'overall_qualification':'failed_original_cache_immutability',
 'completed_native_processes':2,'both_native_outputs_identical':True}
ORIGINAL_CACHE='abb5688ab6aa245ed250d8dc806f438a544fb91cdedad8f537bc81411f47076b'
GENERATED_CACHE='9a31cc110fe41fc744fa5ab4e73ed2e3a036223569edc0a9b64869fa43056d5d'
IDENTIFIERS='311bf6ceb8419b8da901f9deef1323b02e210cf9623375e289141541ec56e59e'
EXPECTED_DELTA={'added': {}, 'changed': {'data/bin/LoyaltyReward.bin': {'after': {'bytes': 8140, 'sha256': '3bf7e0a0915736660b693a12eff038934d6ab25710f36eb88364d601f3036819'}, 'before': {'bytes': 8140, 'sha256': 'd0af635d12dae04cb422b8745e716586fac31a15dcee2e786c34a4d5f7abe66c'}}, 'data/bin/PC_Def_Animation.bin': {'after': {'bytes': 7004, 'sha256': '3629065439d2a0e0cff10bd8e2801078c95f87bd0e436b3c45d84d7b40877753'}, 'before': {'bytes': 7008, 'sha256': '87d5b32f2da9b625cb1ff201edc7b4a8325e36ecc269ead35f6c326fd54aaf6a'}}, 'data/bin/PC_Def_Contacts.bin': {'after': {'bytes': 29144, 'sha256': '84feed47eaf155c90c07e90acc6be4e9eb6964e28ab6d9bf85ddbd5838d857ed'}, 'before': {'bytes': 29148, 'sha256': '906499910d7c2ea9cc91ed9e81718829ae750d82fb8bc30f5398c3282602ce88'}}, 'data/bin/PC_Def_DestructObject.bin': {'after': {'bytes': 2024, 'sha256': 'df4bc54596dced71c94b33d9a869abb17996a5a32ce1fe4aaf2419c54f2ee315'}, 'before': {'bytes': 2028, 'sha256': '2ef27b0ecf18dbec9bb003b29a8e5618e407cbf08058a4c0b49a4408b45f3f42'}}, 'data/bin/PC_Def_Entities.bin': {'after': {'bytes': 91768, 'sha256': 'b6c46354cfcdaf85baaff72ea1dea8540c8675e0ca939fe3f31b611ef13dcaf7'}, 'before': {'bytes': 91772, 'sha256': '5fd5a031f785db26649a9501638fffe9513005cf8cb98240e74899ec01519fbc'}}, 'data/bin/PC_Def_MapSets.bin': {'after': {'bytes': 1484, 'sha256': '2fc050c57a00f4ca13f23d311b5e1e35434bc9b1a839ffd7a7a35a260fef43b8'}, 'before': {'bytes': 1488, 'sha256': '5b52cd5a75710a5a8ac828cb84979b4862bce89b04410bb4cd41982e9000d1ba'}}, 'data/bin/PC_Def_MapUnique.bin': {'after': {'bytes': 23432, 'sha256': 'cf2a2aee0709220098723e2f64691d3af2ec0ec108f30e4b903aca9bf7ccfbd7'}, 'before': {'bytes': 23436, 'sha256': '4c5593f57e7242b527c28ae61bde40917bb13f752295c44683d43a9504d54e2d'}}, 'data/bin/PC_Def_NonSelectable_Entities.bin': {'after': {'bytes': 25952, 'sha256': '6e9672bc0bac7c365bf23c2dc82cf2a276f644d8a94777a264454b2495c2a7bf'}, 'before': {'bytes': 25956, 'sha256': '93421fe594c1b5b3d74abd0f37c1c4ccfad054c549709f3a72c806ca4f9c08fc'}}, 'data/bin/PC_Def_Objects.bin': {'after': {'bytes': 3952, 'sha256': 'd661cea6776964194af09c5f9f383d423cfef8208c06cc2c3d92b69fb0cff6d3'}, 'before': {'bytes': 3956, 'sha256': 'd93e6972cfcf022597ff545f1e65be50187da1a17e0e71157676cc5915cc3f41'}}, 'data/bin/PC_Def_Sequencer_Anims.bin': {'after': {'bytes': 19912, 'sha256': '17253148edec82d5e373883997972be2130657dc028dd1c71a39105497789fe3'}, 'before': {'bytes': 19916, 'sha256': '51f60f31c38dc9ff71ea5e2531c170cc69686216564da4ac87fec437769b931a'}}, 'data/bin/PC_Def_Unlockable_Content.bin': {'after': {'bytes': 22260, 'sha256': '7e8c4ca2c579b314bf22f6433d7fbd72197278e1f2a9f086a56f76cdc5e18593'}, 'before': {'bytes': 22264, 'sha256': 'e403d19e98fdd3ad0df643aad1295c40df2131a17e639ee76c3f7df082b53689'}}, 'data/bin/product_catalog.bin': {'after': {'bytes': 250576, 'sha256': '14a5484ac342ba4d117001bcb1eb23d0e7bee693abcee09afaaf3b72843a008a'}, 'before': {'bytes': 250576, 'sha256': '79252c1e4967e046320201f0c8ff4e6387a7da5ed501de2d316aef50a9e5ccd5'}}, 'data/server/bin/InvBaseDetail.bin': {'after': {'bytes': 77652, 'sha256': '3e75bfca08ba979fd7bcb4083da01ab51bdfb640fb159663e982421c1effd7c2'}, 'before': {'bytes': 77652, 'sha256': '80990b0300deab77613b2ab8a0abf56ecbe4e14840346a79fad17283d228e75d'}}, 'data/server/bin/InvRecipe.bin': {'after': {'bytes': 929768, 'sha256': '95b8a09a4e3d5ea1981188d7521283663db0f6f4bd22b5403fb409792d9821c5'}, 'before': {'bytes': 929768, 'sha256': 'f772a8556efe8119799c0691e2ed70b34f422406fb4bd1368110f3af960b028c'}}, 'data/server/bin/InvSalvage.bin': {'after': {'bytes': 11284, 'sha256': '8eb0e6ca8a13684e82e1a15c6b2c92f1d4015518375ff9cfcd8a36047eb7a133'}, 'before': {'bytes': 11284, 'sha256': 'eb65b811238a17be8311d882c2b548b734da1e9f65f9af7ab882d468ff4b939c'}}, 'data/server/bin/InvStoredSalvage.bin': {'after': {'bytes': 11140, 'sha256': '534c31af966e27c6f40a8a1d24ddfc03fd1dd388eee115c8efdbc32483551bd4'}, 'before': {'bytes': 11140, 'sha256': 'cc9cc4c7a81fadcf69abdaa2dcd275f2ae0b1f81fd4813785d8dd026d7675abd'}}, 'data/server/bin/PC_Rewards.bin': {'after': {'bytes': 676, 'sha256': 'fb6f4bcaddea4eb51d55fe9e0e101b07b7aa0d81b100127cdde0115185f5db2a'}, 'before': {'bytes': 680, 'sha256': '11d0506a3704b703e683a99155b911b80189a7e87f97c988d3ae939507192c70'}}, 'data/server/bin/ProficiencyIds.bin': {'after': {'bytes': 704, 'sha256': '820fea54bde7c1e1a52d8b14ab8defa16a784ce321f61bef79bd2f9401758527'}, 'before': {'bytes': 704, 'sha256': '6d3e893c0b7591935aad9c7422bc681e2f42af5c5850d79ae50d5b3b69c4002f'}}}, 'removed': {}}


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()


def native_inputs(runtime,cache_names):
    """Hash real source/pig/native bytes, never just size/mtime anchors."""
    runtime=Path(runtime);require(runtime.is_dir() and not runtime.is_symlink(),
        'Unlinked native fixture runtime required');result={}
    roots=[runtime/'data',runtime/'piggs']
    for root in roots:
        require(root.is_dir() and not root.is_symlink(),'Native fixture provider directory missing/linked')
        for current,dirs,files in os.walk(root,followlinks=False):
            require(not any((Path(current)/n).is_symlink() for n in dirs),'Linked fixture provider directory refused')
            for name in files:
                path=Path(current)/name;relative=path.relative_to(runtime).as_posix()
                info=path.lstat()
                require(stat.S_ISREG(info.st_mode) and info.st_nlink==1,'Private regular fixture input required')
                if relative in cache_names:continue
                require(len(result)<200000,'Native fixture source inventory exceeds bound')
                result[relative]={**package.pin(path),'mtime_ns':info.st_mtime_ns}
    for path in runtime.iterdir():
        if path.suffix.lower() in ('.exe','.dll'):
            info=path.lstat();require(stat.S_ISREG(info.st_mode) and info.st_nlink==1,'Private regular native component required')
            result[path.name]=package.pin(path)
    return {'files':len(result),'bytes':sum(p['bytes'] for p in result.values()),
        'inventory_sha256':digest(result),
        'provider_except_MapServer_sha256':digest({n:p for n,p in result.items() if n!='MapServer.exe'}),
        'full_content_hashed':True,
        'scope':'data_except_exact_BIN_inventory_plus_piggs_and_root_native_components'}


def validate_delta(before,after):
    require(len(before)==191 and digest(before)==ORIGINAL_CACHE,'Exact original donor cache inventory required')
    require(len(after)==191,'Native generated cache membership changed')
    delta={'added':{n:after[n] for n in after.keys()-before.keys()},
        'removed':{n:before[n] for n in before.keys()-after.keys()},
        'changed':{n:{'before':before[n],'after':after[n]} for n in before.keys()&after.keys() if before[n]!=after[n]}}
    require(not delta['added'] and not delta['removed'] and set(delta['changed'])==set(EXPECTED_DELTA['changed']),
        'Native fixture produced unexpected cache mutations')
    for name,change in delta['changed'].items():
        expected=EXPECTED_DELTA['changed'][name]
        require(change['before']==expected['before'] and change['after']['bytes']==expected['after']['bytes'],
            'Native fixture source/output size differs: '+name)
        if '/PC_' in name:
            require(change['after']==expected['after'],'Native namespace output differs: '+name)
        else:
            require(isinstance(change['after']['sha256'],str) and re.fullmatch('[0-9a-f]{64}',change['after']['sha256']),
                'Native generated fixture output identity missing')
    # The other seven dependency headers bind actual private schema-copy dates.
    # Their full bytes, paths, schema/body and source timestamps are checked next.
    return delta


def inspect_native_parse6(data):
    """Strict Parse6/Files1 envelope with actual native dependency dates.

    Field-level semantics are separately established by the native consumption
    receipt. This verifier does not mislabel an outer envelope as schema decode.
    """
    require(isinstance(data, bytes) and 24 <= len(data) <= 128*1024**2 and data[:8] == b'CrypticS',
            'Invalid Parse6 header or size')
    position = 12

    def integer():
        nonlocal position
        require(position + 4 <= len(data), 'Truncated Parse6 integer')
        value = struct.unpack_from('<I', data, position)[0]
        position += 4
        return value

    def string(limit):
        nonlocal position
        require(position + 2 <= len(data), 'Truncated Parse6 string length')
        size = struct.unpack_from('<H', data, position)[0]
        require(size <= limit, 'Oversized Parse6 string')
        end = position + ((size + 2 + 3) & ~3)
        require(end <= len(data), 'Truncated Parse6 string')
        value = data[position + 2:position + 2 + size]
        require(data[position + 2 + size:end] == b'\x00' * (end - position - 2 - size),
                'Nonzero Parse6 string padding')
        position = end
        return value

    require(string(16) == b'Parse6' and string(16) == b'Files1', 'Unexpected Parse6 signature')
    block_bytes = integer()
    block_end = position + block_bytes
    require(4 <= block_bytes <= 32 * 1024 * 1024 and block_end <= len(data),
            'Invalid Parse6 dependency block')
    count = integer()
    require(count <= block_bytes // 8, 'Invalid Parse6 dependency count')
    dependencies = []
    names = set()
    for unused in range(count):
        raw = string(1024)
        require(raw and b'\x00' not in raw, 'Empty or nul-containing dependency')
        name = raw.decode('utf-8', errors='strict').replace('\\', '/')
        require(not name.startswith('/') and ':' not in name
                and all(part not in ('', '.', '..') for part in name.split('/')), 'Unsafe dependency path')
        require(name.casefold() not in names, 'Duplicate Parse6 dependency')
        names.add(name.casefold())
        timestamp = integer()
        require(0 <= timestamp <= 0x7fffffff, 'Native dependency date exceeds signed time32 bound: '+name)
        require(position <= block_end, 'Dependency exceeds declared block')
        dependencies.append({'path': name, 'timestamp': timestamp})
    require(position == block_end, 'Parse6 dependency block length differs')
    body_bytes = integer()
    require(body_bytes >= 4 and position + body_bytes == len(data), 'Parse6 body length differs')
    # This integer is ParserReadBinaryTable's root length, not an additional
    # container around another root header. Native consumption checks fields.
    return {'format': 'Parse6', 'schema_crc': f'{struct.unpack_from("<I", data, 8)[0]:08x}',
            'dependency_count': count, 'dependency_sha256': hashlib.sha256(canonical(dependencies)).hexdigest(),
            'body_bytes': body_bytes, 'dependencies': dependencies}


def parse6_equivalence(before,after):
    old=inspect_native_parse6(before);new=inspect_native_parse6(after)
    require(old['schema_crc']==new['schema_crc'] and old['body_bytes']==new['body_bytes']
        and before[-old['body_bytes']:]==after[-new['body_bytes']:],
        'Native regeneration changed decoded payload/schema instead of only dependency envelope')
    require(old['dependency_count']==new['dependency_count'],'Native dependency count changed')
    for left,right in zip(old['dependencies'],new['dependencies']):
        allowed=left['path']
        if allowed.casefold().startswith('scripts.loc/player_created/'):
            allowed='scripts/'+allowed[len('scripts.loc/'):]
        require(right['path']==left['path'] or right['path']==allowed,'Native dependency path changed beyond exact development namespace')
    return {'before':old,'after':new,'schema_crc_unchanged':True,'native_payload_bytes_unchanged':True,
        'native_payload_sha256':hashlib.sha256(after[-new['body_bytes']:]).hexdigest()}


def bind_dependency_sources(runtime,decoded):
    index={}
    for current,dirs,files in os.walk(Path(runtime)/'data',followlinks=False):
        for name in files:
            path=Path(current)/name;key=path.relative_to(Path(runtime)/'data').as_posix().casefold()
            require(key not in index,'Ambiguous case-folded native input path')
            index[key]=path
    result={}
    for cache,value in decoded.items():
        result[cache]=[]
        for dependency in value['after']['dependencies']:
            name=dependency['path'].casefold().removeprefix('data/');path=index.get(name)
            require(path is not None and path.is_file() and not path.is_symlink(),'Native dependency source missing/linked: '+name)
            info=path.stat();timestamp=int(info.st_mtime)
            require(abs(dependency['timestamp']-timestamp) in (0,3600),'Native dependency date differs from actual immutable source: '+name)
            result[cache].append({'path':name,'native_dependency_timestamp':dependency['timestamp'],
                'actual_source_mtime_ns':info.st_mtime_ns,'actual_source':package.pin(path)})
    return result


def generate(args,original,work,output,launcher,env,baseline,control,cache_snapshot):
    import prepare_server_caches as preload
    old=retained.validate_package(baseline)
    runtime=work/'native-generated-fixture'
    require(not runtime.exists() and not runtime.is_symlink(),'Fresh private generation runtime required')
    shutil.copytree(original,runtime,symlinks=False)
    target=runtime/'MapServer.exe';target.chmod(0o600);shutil.copyfile(baseline/'MapServer-control.exe',target)
    native=package.pin(target);require(native=={'bytes':old['native_control']['binary']['size'],'sha256':old['native_control']['binary']['sha256']},
        'Exact retained native fixture producer required')
    before=cache_snapshot(runtime);require(len(before)==191 and digest(before)==ORIGINAL_CACHE,'Original fixture cache input differs')
    ids=preload.package.identifier_snapshot(runtime/'data');require(digest(ids)==IDENTIFIERS,'Original fixture identifiers differ')
    source_before=native_inputs(runtime,set(before))
    changed_before={n:(runtime/n).read_bytes() for n in EXPECTED_DELTA['changed']}
    package.write(output/'evidence/native-generation-before.json',{'cache':before,'source':source_before,
        'identifiers':ids,'actual_native':native,'original_control_fixture':control,'capture':CAPTURE})
    try:
        phase=preload.run_phase(args,runtime,launcher,env,output,'fixture-generation',
            {'qualification_source':args.repository_commit,'native_source':retained.SOURCE,
             'actual_native':native,'purpose':'explicit_owned_fixture_generation_not_reuse'},trace=False)
    except BaseException:
        failure=output/'evidence/fixture-generation-cleanup';failure.mkdir(exist_ok=True)
        try:preload.stop_owned_prefix(env,failure,normal_launcher_exit_observed_first=False)
        except Exception as cleanup:package.write(failure/'cleanup-error.json',{'passed':False,'error':str(cleanup)})
        raise
    phase['legacy_receipt_historical_mapserver_sha256']=phase.pop('mapserver_sha256')
    phase['actual_mapserver']=native;package.write(output/'evidence/fixture-generation/phase-receipt.json',phase)
    after=cache_snapshot(runtime);ids_after=preload.package.identifier_snapshot(runtime/'data')
    source_after=native_inputs(runtime,set(before)|set(after))
    evidence={'before':before,'after':after,'source_before':source_before,'source_after':source_after,
        'identifiers_before':ids,'identifiers_after':ids_after,'actual_native':package.pin(target)}
    package.write(output/'evidence/native-generation-after.json',evidence)
    require(source_before==source_after and ids==ids_after and package.pin(target)==native,
        'Native generation changed original provider/identifier/native inputs')
    delta=validate_delta(before,after)
    decoded={n:parse6_equivalence(raw,(runtime/n).read_bytes()) for n,raw in changed_before.items()}
    dependencies=bind_dependency_sources(runtime,decoded)
    value={'format':1,'status':'generated_pending_separate_reuse','publication_allowed':False,
        'role':'owned_native_fixture_generation','repository_commit':args.repository_commit,
        'native_source_commit':retained.SOURCE,'retained_native_build':retained.provenance(),
        'capture_reference':CAPTURE,'actual_native':native,'phase':phase,'original_fixture':control,
        'cache_before':before,'cache_after':after,'delta':delta,'parse6_equivalence':decoded,
        'actual_dependency_sources':dependencies,'generated_cache_inventory_sha256':digest(after),
        'captured_output_digest_not_reused_as_current_source_date_authority':True,
        'provider_before':source_before,'provider_after':source_after,'identifier_files_unchanged':True,
        'native_cache_reuse_qualified':False,'Android_cache_authority_created':False,
        'native_world_executed':False,'player_database_used':False,'physical_device_executed':False,
        'timing_scope':'host_first_native_generation_after_full_input_hashing_not_OS_cold_or_Thor',
        'source_helper':package.pin(Path(__file__))}
    package.write(output/'native-generated-fixture.json',value)
    return runtime,value
