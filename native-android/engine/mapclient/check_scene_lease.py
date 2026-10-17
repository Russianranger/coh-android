#!/usr/bin/env python3
"""Freeze actual scene lease implementation and full executed helper/header closure."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
paths=[Path(__file__),HERE/'check.py',HERE/'coh_mapclient.c',HERE/'tests/test_mapclient.c',HERE/'SCENE_LEASE.md']
for directory in [ROOT/'native-android/engine',ROOT/'native-android/include',ROOT/'native-android/protocol',ROOT/'native-android/src',ROOT/'native-android/tools/protocol_fixture']:
 for extension in ['*.h','*.py','*.inc','*.c','*.json']:
  paths.extend(x for x in directory.rglob(extension) if 'evidence' not in x.parts and '__pycache__' not in x.parts)
for manifest in [HERE/'source-pins.json',HERE.parent/'replication/source-pins.json',HERE.parent/'replication/groups-source-pins.json']:
 paths.extend(ROOT/'upstream/ouroboros'/name for name in json.loads(manifest.read_text())['sha256_lf'])
paths=sorted(set(paths));pins={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in paths}
with tempfile.TemporaryDirectory(prefix='coh-scene-lease-') as tmp:
 receipt=Path(tmp)/'mapclient.json'
 run=subprocess.run(['python3','-B','-X','pycache_prefix='+str(Path(tmp)/'pycache'),str(HERE/'check.py'),'--sanitize','--output',str(receipt)],capture_output=True,text=True,timeout=180,env=dict(os.environ,PYTHONPYCACHEPREFIX=str(Path(tmp)/'pycache'),PYTHONDONTWRITEBYTECODE='1'))
 if run.returncode:raise RuntimeError(run.stdout+run.stderr)
 result=json.loads(receipt.read_text())
assert pins=={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in paths}
out={'schema':'coh-map-scene-actual-loan-v1','passed':True,'source_sha256':pins,'qualification':result,'actual_receive_loan_origin_validated':True,'scripted_peer_only':True,'selected_dbid_owner_bound':False,'source_generation_admitted':False,'world_authority':False,'real_server_capture':False,'android_executed':False}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'passed':True,'inputs':len(pins),'checks':{k:v['checks'] for k,v in result['checks'].items()}}))
