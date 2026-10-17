#!/usr/bin/env python3
"""Record an exact private Win32 live GROUPS observer build, without running it."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import stage_groups_capture as stage

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'scenecatalog-qualification'))
from common import child,digest,git_state,write
from record_export_compile import pe32_identity,cmake_identity,validate_inputs

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('source-root','staged-source','inputs-receipt','output'):parser.add_argument('--'+name,type=Path,required=True)
 parser.add_argument('--require-clean',action='store_true');args=parser.parse_args()
 root=args.source_root.resolve();staged=args.staged_source.resolve();out=args.output.resolve()
 if out.exists() and any(out.iterdir()):raise ValueError('New compile output required')
 state=git_state(root)
 if args.require_clean and state['source_git_status_porcelain']:raise ValueError('Dirty source')
 receipt=stage.verify_staged(root,staged)
 binary=child(staged,'out/build/vs2026/bin/OptDebug/MapServer.exe');cache=child(staged,'out/build/vs2026/CMakeCache.txt')
 pe32_identity(binary);cmake_identity(cache,staged)
 driver=child(root,'tools/android/interactive/map_startup_inputs.py');spec=importlib.util.spec_from_file_location('groups_startup_inputs',driver);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
 inputs=validate_inputs(json.loads(args.inputs_receipt.read_bytes()),helper)
 helper.checked(args.inputs_receipt.parent/'COH-Atlas-Gameplay-0.13.31.apk',helper.DONOR)
 for name,value in inputs['files'].items():helper.checked(args.inputs_receipt.parent/name,value)
 files={'MapServer.exe':binary,'CMakeCache.txt':cache,stage.RECEIPT:staged/stage.RECEIPT,stage.PRIOR:staged/stage.PRIOR,'map-startup-inputs.json':args.inputs_receipt}
 for name in (*receipt['patched_sha256'],*receipt['overlay_sha256']):files['source/'+name]=child(staged,name)
 out.mkdir(parents=True,exist_ok=True)
 for name,source in files.items():
  target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
  with source.open('rb') as src,target.open('xb') as dst:shutil.copyfileobj(src,dst)
 if git_state(root)!=state:raise ValueError('Source changed during recording')
 stage.verify_staged(root,staged)
 proof={**state,'schema':'coh-groups-transaction-compile-v1','passed':True,'build_role':stage.ROLE,'compile_only':True,'nonshipping':True,'runtime_executed':False,'accepted_apks_rebuilt':False,
        'source_stage_verified':True,'published_inputs_reverified':True,'generator':'Visual Studio 18 2026','platform':'Win32','configuration':'OptDebug','pe_machine':'i386',
        'producer_driver_sha256':digest(Path(__file__)),'artifacts':{name:{'bytes':(out/name).stat().st_size,'sha256':digest(out/name)} for name in files}}
 write(out/'compile-only-receipt.json',proof)
 print(json.dumps({'passed':True,'source_revision':state['source_revision'],'binary':proof['artifacts']['MapServer.exe'],'runtime_executed':False}))
if __name__=='__main__':main()
