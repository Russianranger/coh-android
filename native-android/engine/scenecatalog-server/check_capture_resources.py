#!/usr/bin/env python3
"""Offline source/candidate/triple binding controls. Never starts a service."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 names=('capture_resources.py','admit_resources.py','test_capture_resources.py','check_capture_resources.py','capture_snapshot.py','admit_snapshot.py','source_resources.inc','source_resource_quiescence.inc','stage_resources.py','resource_oracle.py','record_resource_compile.py')
 hashes={str((HERE/n).relative_to(ROOT)):sha(HERE/n) for n in names}
 run=subprocess.run([sys.executable,'-m','unittest','test_capture_resources','-v'],cwd=HERE,capture_output=True,text=True,timeout=120)
 if run.returncode:raise RuntimeError(run.stdout+run.stderr)
 assert hashes=={str((HERE/n).relative_to(ROOT)):sha(HERE/n) for n in names}
 receipt={'schema':'coh-resource-capture-offline-controls-v1','passed':True,'source_sha256':hashes,'tests':6,'test_output':run.stderr,'actual_runtime_executed':False,'capture_started':False,'candidate_started':False,'source_snapshot_only':True,'native_decode_completed':False,'assets_admitted':False,'client_materials_complete':False,'client_lods_complete':False,'fixture_only':True,'binding_scope':'copiedtriple hashes/source-run lineage/cleanup guarded; ordinary regular-row catalog graph association remains separate native gate'}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':True,'tests':6,'output':str(a.output),'capture_started':False}))
if __name__=='__main__':main()
