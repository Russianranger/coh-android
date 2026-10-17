#!/usr/bin/env python3
"""Replay finite preparation/body pins supporting the separately reviewed source route.
No runtime launch, download, renderer permit or live-generation admission.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

REV='a45c657fcc6b3bd8f3a70c59e9aa85ee19455f3f'
DONOR='74fe247be85173e618f1af2c8af71b1316de4cd8'
CANDIDATES='a52d6470847fc01a677cfa2822c0cf5eae23eecefcb52edb7e2789ecd5c637a6'
FIXTURE='3be317b5cc4b24aad8b19cd93e18762f12270ad4284c31a81e7587e4e35fadc1'
VISUAL='8587015400e1af639e2118649f0d9c77a089d564bfe2c97cbf9d80baaee5f9a2'
REQUIRED='c5eddbe19511356d1c9eb26890728b169db6989917da9e1375b6f1692f41bb43'
RECEIPT='0947a6a172c083350d3229de5facebc5862fdc1bdd98e9b6c181b14cf3a715e4'
SOURCE_LEDGER='74bbba3b70d9fb0a0bc28117a69c023292af720c865d572f97f1f131f09be07d'

def require(value, code):
    if not value: raise ValueError(code)

def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def bounded(path,limit):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size<=limit,'INPUT_BOUND')
    raw=path.read_bytes();require(len(raw)<=limit,'INPUT_CHANGED_BOUND');return raw
def load(path, limit=64*1024**2):
    raw=bounded(path,limit);return raw,json.loads(raw)
def blob(root,rev,path):
    return subprocess.check_output(['git','show',rev+':'+path],cwd=root)

def inspect(args):
    root=args.source_root.resolve();here=Path(__file__).resolve().parent
    raw,candidates=load(args.candidates);require(sha(raw)==CANDIDATES,'CANDIDATE_PIN')
    raw,fixture=load(args.evidence/'control-fixture.json');require(sha(raw)==FIXTURE,'FIXTURE_PIN')
    capture=args.evidence/'capture';raw,receipt=load(capture/'capture-receipt.json')
    require(sha(raw)==RECEIPT,'CAPTURE_RECEIPT_PIN')
    for name,expected in candidates['capture_sha256'].items():
        data=bounded(capture/name,32*1024**2);require(sha(data)==expected,'CAPTURE_FILE_PIN')
    require(receipt['passed'] is True and receipt['cleanup_verified'] is True and receipt['source_runtime_unchanged'] is True,'CAPTURE_SCOPE')
    require(receipt['control_fixture_sha256']==FIXTURE and receipt['exporter_source_revision']==REV,'CAPTURE_ASSOCIATION')
    raw,source=load(capture/'source-identity.json');require(sha(raw)==receipt['source_identity_sha256'],'SOURCE_PIN')
    raw,run=load(capture/'run-identity.json');require(sha(raw)==receipt['run_identity_sha256'] and run['source_identity_sha256']==receipt['source_identity_sha256'],'RUN_PIN')
    require(run['private_fresh_wine_prefix'] is True and source['runtime_inventory']==receipt['source_runtime_inventory'],'OWNED_FRESH_RUNTIME')
    require(source['control_fixture_sha256']==FIXTURE and source['exporter_source_revision']==REV,'SOURCE_ASSOCIATION')
    require(fixture['status']=='prepared' and fixture['atlas_preparation']['cache_reused'] is False and fixture['atlas_preparation']['animation_installed'] is True,'COLD_PREPARATION')
    stages=fixture['atlas_preparation']['all_preparation_phases']
    require(all(x in stages for x in ('required_original_geometry','cold_server_data_mirror','cold_server_data_receipt_seal','atlas_beacon_graph')),'PREPARATION_PHASES')
    raw,visual=load(args.visual_manifest);require(sha(raw)==VISUAL,'VISUAL_PIN')
    required={n:{k:r[k] for k in ('bytes','sha256')} for n,r in visual['files'].items() if n.startswith('data/object_library/') and n.casefold().endswith('.geo')}
    require(len(required)==406 and sha(canonical(required))==REQUIRED,'COMPLETE_REQUIRED_GEOMETRY')
    raw,files=load(here/'evidence/prepared-geo-source-route-files.json');require(sha(raw)==SOURCE_LEDGER,'SOURCE_LEDGER_PIN')
    source_pins=[]
    for item in files['files']:
        observed=blob(root,REV,item['path'])
        require(len(observed)==item['bytes'] and sha(observed)==item['sha256'],'ORIGINAL_SOURCE_PIN')
        source_pins.append(item)
    donor_pins=[]
    for name in ('atlas_world_assets.py','atlas_beacon_package.py','local_character_server.py','local_login_server.py','server_animation_package.py','server_cache_package.py','character_server_data_cache.py'):
        observed=blob(root,DONOR,'android/guest/'+name);pin={'bytes':len(observed),'sha256':sha(observed)}
        require(pin==fixture['packaged_guest_sources'][name],'DONOR_SOURCE_PIN');donor_pins.append({'path':'android/guest/'+name,**pin})
    for item in receipt['diagnostics']:
        data=bounded(capture/item['file'],8*1024**2);require(len(data)==item['bytes'] and sha(data)==item['sha256'],'DIAGNOSTIC_PIN')
    stdout=(capture/'diagnostic-18.txt').read_bytes();stderr=(capture/'diagnostic-19.txt').read_bytes()
    require(b'working dir: Z:\\tmp\\coh-scene-resource-snapshot\\map-runtime' in stdout and b'Not using shared memory due to -nosharedmemory' in stdout and b'Could not find appropriate game data dir' in stderr,'RUNTIME_ROUTE_OBSERVATIONS')
    out=[];total=0;seen=set();required_count=0
    require(len(candidates['files'])==391,'CANDIDATE_COUNT')
    for row in candidates['files']:
        require(len(row['candidate_matches'])==1,'CANDIDATE_AMBIGUITY');candidate=row['candidate_matches'][0]
        name=candidate['manifest_asset_path'];parts=Path(name).parts
        require(name.startswith('data/object_library/') and '..' not in parts and not Path(name).is_absolute() and name.casefold() not in seen,'BODY_PATH')
        seen.add(name.casefold());path=args.body_directory/name
        require(path.is_file() and not path.is_symlink() and path.stat().st_size==candidate['bytes'],'BODY_SIZE')
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
        require(digest.hexdigest()==candidate['sha256'],'BODY_DIGEST')
        if name in required:
            require(required[name]=={k:candidate[k] for k in ('bytes','sha256')},'REQUIRED_BODY_PIN');required_count+=1
        total+=candidate['bytes'];out.append({'source_geo_name':row['source_geo_name'],'prepared_logical_path':name,'bytes':candidate['bytes'],'sha256':candidate['sha256'],'source_ordinals':row['source_ordinals']})
    require(required_count==3 and total==71817182,'BODY_CLOSURE')
    return {'schema':'coh-prepared-geo-route-evidence-v1','passed':True,'scope':'replay pins and bind independent source-route review; no native admission permit','source_revision':REV,'source_identity_sha256':receipt['source_identity_sha256'],'run_identity_sha256':receipt['run_identity_sha256'],'control_fixture_sha256':FIXTURE,'candidates_sha256':CANDIDATES,'runtime_inventory':source['runtime_inventory'],'original_source_files':source_pins,'donor_source_files':donor_pins,'required_geometry_inventory':{'count':406,'sha256':REQUIRED},'body_count':len(out),'body_bytes':total,'bodies':out,'source_review':{'prepared_full_body_inclusion':'proved by exact cold construction chain','runtime_selection_route':'determined by reviewed source and owned startup scope','per_leaf_open_sha_observed':False,'resolved_physical_leaf_string_observed':False,'proof_route':'deterministic preparation and unique source selection, not metadata agreement','independent_review_required_before_native_admission':True},'assets_admitted':False,'live_generation_admitted':False,'world_authority':False,'script_sha256':sha(Path(__file__).read_bytes())}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source-root','evidence','candidates','visual-manifest','body-directory','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=inspect(args)
    with args.output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({k:result[k] for k in ('passed','body_count','body_bytes','assets_admitted','world_authority')}))
