"""Additive MapServer-only source provenance; historical Game/DbServer remain exact."""
import copy
import hashlib
import json
import re
import native_responsiveness_contract as retained
require=retained.require
CONTRACT={'format':1,'environment_variable':'COH_WINE_MONORAIL_SESSION',
    'reply_environment_variable':'COH_WINE_MONORAIL_REPLY','native_event_prefix':'COH_ZONING_EVENT_V1',
    'reply_prefix':'COH_MONORAIL_REPLY_V1','disabled_by_default':True,'station_maps':[1,5],
    'event_maps':[1,5,101],'station_line':'ParagonCityMonorail','spawn':'LinkFrom_Monorail_ParagonCity',
    'transport':'owned_flushed_console_and_private_atomic_reply','game_and_dbserver_rebuild_required':False,
    'stock_door_validation_repeated_after_readiness':True,'station_preparation_timeout_seconds':600,
    'physical_validation':False}

def canonical_sha(value):
    return retained.canonical_sha(value)

def embedded_receipt(package):
    wrapper=package.get('native_monorail',{})
    receipt=wrapper.get('receipt',{})
    require(isinstance(receipt,dict) and receipt.get('format')==1 and receipt.get('role')=='native_monorail'
        and re.fullmatch(r'[0-9a-f]{40}',str(receipt.get('repository_commit','')))
        and receipt.get('source_commit')==package.get('source_commit')==retained.SOURCE
        and receipt.get('data_commit')==package.get('data_commit')==retained.DATA
        and wrapper.get('receipt_sha256')==canonical_sha(receipt),'Monorail native identity differs')
    build=receipt.get('build_input',{})
    require(build.get('schema_version')==1 and build.get('build_role')=='monorail'
        and build.get('build_targets')==['MapServer'] and build.get('runtime_validation')=='unverified'
        and build.get('contract')==CONTRACT,'Monorail native bridge contract differs')
    events=build.get('events_build_input',{})
    require(build.get('events_build_input_canonical_sha256')==hashlib.sha256(
        json.dumps(events,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        'Monorail source ancestry digest differs')
    previous=copy.deepcopy(package);previous.pop('native_monorail')
    previous['files']['MapServer.exe']=receipt.get('previous_mapserver')
    accepted=retained.embedded_receipt(previous)
    retained.events_progress_contract(previous)
    comparison = copy.deepcopy(accepted['build_inputs'])
    comparison['character_events'] = events
    retained.scene_source_inputs_equivalent(comparison, accepted['build_inputs'])
    current=retained.pe_record(receipt.get('mapserver'))
    require(package['files']['MapServer.exe']==current
        and current.get('imports')==receipt['previous_mapserver'].get('imports')
        and current.get('delay_imports')==receipt['previous_mapserver'].get('delay_imports')
        and current['sha256']!=receipt['previous_mapserver']['sha256']
        and receipt.get('retained_native_files')=={n:r for n,r in package['files'].items() if n!='MapServer.exe'},
        'Monorail changed retained native dependencies')
    require(re.fullmatch(r'[0-9a-f]{40}',str(receipt.get('native_build_repository_commit','')))
        and retained.HEX64.fullmatch(str(receipt.get('native_build_manifest',{}).get('sha256',''))),
        'Monorail native build source binding missing')
    return receipt

def progress_contract(package):
    receipt=embedded_receipt(package)
    return {'contract':receipt['build_input']['events_build_input']['progress_contract'],
        'producer':{'repository_commit':receipt['native_build_repository_commit'],
            'manifest_sha256':receipt['native_build_manifest']['sha256'],
            'mapserver_sha256':receipt['mapserver']['sha256']}}
