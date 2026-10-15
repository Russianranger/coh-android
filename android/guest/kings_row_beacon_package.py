"""Install a source-bound genuine Kings Row graph into its private zone tree.

An APK-owned lock authenticates the external asset pack's graph. Cold input
hashes are reused only while immutable world and graph fingerprints still match.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import time
import zipfile
import atlas_beacon_package as atlas

ARCHIVE='kings-row-beacons.zip'
MANIFEST='kings-row-beacon-manifest.json'
LOCK='kings-row-beacon-lock.json'
MAP='maps/city_zones/city_01_02/city_01_02.txt'
GRAPH='data/server/'+MAP+'.v8.bcn'
DATE=GRAPH+'.date'
MARKER='data/server/kings-row-beacon-installed.json'
POLICY='native_map5_complete_collision_two_fresh_crc_graph_32routes_v1'
PROFILES=('cold_world','reopened_world')
require,canonical,pin=atlas.require,atlas.canonical,atlas.pin


def input_name(name):
    return atlas.safe(name) and (name.startswith('data/object_library/') and name.lower().endswith(('.geo','.txt','.rootnames'))
        or name.startswith('data/maps/city_zones/city_01_02/') and name.lower().endswith('.txt')
        or name.startswith('data/tricks/') and name.lower().endswith('.txt'))


def read_manifest(path,lock_path):
    atlas.regular(lock_path,4096,allow_shared_source=True);lock=json.loads(Path(lock_path).read_bytes())
    require(lock.get('format')==1 and lock.get('map_id')==5,'APK Kings graph lock differs')
    atlas.regular(path,atlas.MAX_MANIFEST,allow_shared_source=True)
    require(pin(path)==lock.get('manifest'),'Kings manifest differs from APK-owned lock')
    value=json.loads(Path(path).read_bytes());native=value.get('native',{});inputs=value.get('input_files',{})
    require(value.get('format')==1 and value.get('role')=='authentic_native_kings_row_beacon_graph'
        and value.get('map')==MAP and value.get('map_id')==5
        and value.get('source_commit')==atlas.SOURCE_COMMIT and value.get('data_commit')==atlas.DATA_COMMIT
        and value.get('runtime_graph_readback') is True and value.get('physical_zoning_verified') is False,
        'Kings graph source/role differs')
    require(100<len(inputs)<=atlas.MAX_INPUTS and all(input_name(n) for n in inputs)
        and 'data/'+MAP in inputs and len({n.casefold() for n in inputs})==len(inputs)
        and hashlib.sha256(canonical(inputs)).hexdigest()==value.get('input_files_sha256'),
        'Kings graph collision input identity differs')
    files=value.get('files',{})
    require(set(files)=={GRAPH,DATE} and files[DATE].get('bytes')==12
        and 18<files[GRAPH].get('bytes',0)<=atlas.MAX_GRAPH,'Kings native graph file closure differs')
    for row in [*files.values(),*inputs.values()]:
        require(isinstance(row,dict) and set(row)=={'bytes','sha256'} and type(row['bytes']) is int
            and 0<row['bytes']<=atlas.MAX_GRAPH and re.fullmatch('[0-9a-f]{64}',str(row['sha256'])),
            'Invalid Kings payload pin')
    require(native.get('native_full_graph_readback_verified') is True
        and native.get('fresh_ordinary_world_crc_verified') is True
        and native.get('native_collision_load_verified') is True
        and native.get('missing_groups')==0 and native.get('missing_root_models')==0
        and native.get('native_pathfinder_successes')==32 and native.get('date_version')==9
        and 1000<native.get('connected_beacons',0)<=native.get('combat_beacons',0)<=1000000
        and native.get('ground_connections',0)>1000 and native.get('grid_blocks',0)>0
        and re.fullmatch('0x[0-9a-f]{8}',str(native.get('full_world_crc'))),'Kings native collision/CRC/graph/path proof incomplete')
    profiles=value.get('input_profiles',{})
    require(set(profiles)==set(PROFILES) and all(profiles[p]=={'native':native,
        'input_files_sha256':value['input_files_sha256']} for p in PROFILES),'Kings native cold/reopen proofs differ')
    return value,lock


def inventory(runtime,value,context,*,provider_records=None):
    return atlas.collision_input_snapshot(runtime,value['input_files'],
        (('data/object_library',('.geo','.txt','.rootnames')),
         ('data/maps/city_zones/city_01_02',('.txt',)),('data/tricks',('.txt',))),context,zone='Kings',provider_records=provider_records)



def private_target(runtime,name,context):
    require(name in (GRAPH,DATE,MARKER),'Kings private target scope differs')
    current=Path(runtime);atlas.world.real_directory(current)
    target=atlas.actual_targets(current,[name],context)[name]
    for part in target.relative_to(current).parts[:-1]:
        current/=part
        if not current.exists(): current.mkdir(mode=0o700)
        atlas.world.real_directory(current)
    require(not target.is_symlink(),'Linked Kings graph target')
    return target


def install(archive,manifest_path,runtime,*,context,imported_inputs_readonly,lock_path=None,
            source_input_proof=None,source_cache_identity=None,owner_root=None,input_proof_sink=None):
    started=time.monotonic();runtime=Path(runtime)
    require(imported_inputs_readonly is True,'Qualified readonly Kings world required')
    lock_path=Path(lock_path) if lock_path else Path(manifest_path).with_name(LOCK)
    value,lock=read_manifest(manifest_path,lock_path)
    providers={} if source_input_proof is not None or input_proof_sink is not None else None
    inputs,input_targets=inventory(runtime,value,context,provider_records=providers)
    targets={n:private_target(runtime,n,context) for n in value['files']};marker=private_target(runtime,MARKER,context)
    result={'format':1,'verified':True,'map_id':5,'map':MAP,'native_graph_readback_qualified':True,
        'physical_zoning_verified':False,'full_world_crc':value['native']['full_world_crc'],
        'input_files_checked':len(inputs),
        'input_validation':'bounded_single_walk_inventory_and_fingerprints'}
    prior=None
    if marker.exists():
        try: atlas.regular(marker,atlas.MAX_MANIFEST);prior=json.loads(marker.read_bytes())
        except (OSError,ValueError):pass
    if isinstance(prior,dict) and prior.get('policy')==POLICY and prior.get('lock')==lock and prior.get('inputs')==inputs:
        if all(p.exists() for p in targets.values()) and prior.get('graphs')==atlas.fingerprints(runtime,targets,context):
            if input_proof_sink is not None:
                input_proof_sink(atlas.mint_shared_inputs(value['input_files'],providers,source_cache_identity,owner_root,
                    validation_basis='authenticated_prior_full_byte_receipt_and_current_immutable_provider_fingerprints',
                    manifest_sha256=lock['manifest']['sha256']))
            return dict(result,status='reused_verified_graph',installed_files=0,input_payload_bytes_hashed=0,
                        input_full_byte_proof_reused_files=0,input_full_byte_proof_reused_bytes=0,
                        input_full_byte_proof_reuse_policy='unchanged_destination_full_byte_graph_receipt',
                        input_full_byte_proof_reuse_basis='authenticated_prior_full_byte_receipt_and_current_immutable_provider_fingerprints',
                        preparation_elapsed_seconds=round(time.monotonic()-started,6))
    shared,shared_reason=(atlas.reusable_shared_inputs(source_input_proof,value['input_files'],providers,
        source_cache_identity,owner_root) if source_input_proof is not None else
        (set(),'no_current_process_owned_atlas_proof'))
    hashed=reused_bytes=0
    for name,expected in value['input_files'].items():
        context.check()
        if name in shared:
            reused_bytes+=expected['bytes']
            continue
        require(pin(input_targets[name],context)==expected,'Kings collision input differs: '+name);hashed+=expected['bytes']
    result.update(input_full_byte_proof_reused_files=len(shared),input_full_byte_proof_reused_bytes=reused_bytes,
        input_full_byte_proof_reuse_policy=shared_reason,
        input_full_byte_proof_reuse_basis=(source_input_proof.validation_basis if shared else 'all_destination_inputs_fully_hashed'))
    current_providers={} if providers is not None else None
    require(inventory(runtime,value,context,provider_records=current_providers)[0]==inputs
        and current_providers==providers,'Kings inputs changed during proof')
    atlas.regular(archive,2*atlas.MAX_GRAPH,allow_shared_source=True)
    require(pin(archive,context)==lock['archive'],'Kings graph archive differs from APK lock')
    installed=0
    with zipfile.ZipFile(archive) as source:
        entries=source.infolist();names=[e.filename for e in entries]
        require(len(names)==3 and set(names)=={GRAPH,DATE,MANIFEST} and all(not e.is_dir()
            and not e.flag_bits&1 and stat.S_IFMT(e.external_attr>>16) in (0,stat.S_IFREG) for e in entries),
            'Kings graph archive closure unsafe')
        require(source.read(MANIFEST)==Path(manifest_path).read_bytes(),'Kings embedded graph manifest differs')
        for name,expected in value['files'].items():
            context.check();require(source.getinfo(name).file_size==expected['bytes'],'Kings graph member size differs')
            raw=source.read(name)
            require({'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}==expected,'Kings graph member hash differs')
            if name==DATE:
                version,newest,crc=struct.unpack('<iII',raw)
                require(version==9 and f'0x{crc:08x}'==value['native']['full_world_crc'],'Kings native date CRC differs')
            target=targets[name]
            if target.exists():
                atlas.regular(target,atlas.MAX_GRAPH);require(pin(target,context)==expected,'Preserve existing different Kings graph')
                target.chmod(0o400)
            else:atlas.atomic_bytes(target,raw);installed+=1
    current_providers={} if providers is not None else None
    require(inventory(runtime,value,context,provider_records=current_providers)[0]==inputs
        and current_providers==providers,'Kings inputs changed before graph receipt')
    atlas.atomic_bytes(marker,canonical({'format':1,'policy':POLICY,'lock':lock,'inputs':inputs,
        'graphs':atlas.fingerprints(runtime,targets,context)}))
    if input_proof_sink is not None:
        input_proof_sink(atlas.mint_shared_inputs(value['input_files'],current_providers,source_cache_identity,owner_root,
            manifest_sha256=lock['manifest']['sha256'],
            validation_basis=('authenticated_shared_provider_pins_and_hashed_destination_delta' if shared else
                              'current_complete_input_sha256_and_same_provider_snapshots')))
    return dict(result,status='installed_verified_graph',installed_files=installed,input_payload_bytes_hashed=hashed,
                preparation_elapsed_seconds=round(time.monotonic()-started,6))
