#!/usr/bin/env python3
"""Checked-source follow-up over retained sweep evidence; no native sweep rerun."""
import argparse,hashlib,json,subprocess,tempfile,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
p=argparse.ArgumentParser(description=__doc__)
for key in ('receipt','ledger','root-coverage','body-directory','renderer-source-root','output'):p.add_argument('--'+key,type=Path,required=True)
a=p.parse_args();ER=a.renderer_source_root.resolve()
def sha_bytes(raw):return hashlib.sha256(raw).hexdigest()
def run(args):
 r=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=300)
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 return r.stdout
old=json.loads(a.receipt.read_text());assert sha_bytes(a.receipt.read_bytes())=='d4227d4c974c270c83c8df130dc4d76ee47503cf6df879514bf0a1744f3e9a5c';assert sha_bytes(a.ledger.read_bytes())=='6e6d39e3b8bd9fae9bd7f9b7213cdce4569ee7856ae6c7d9f199d5c26ca89fd1'
# Snapshot every old compiled/source dependency and every NEW executable helper
# before the first project exec. Read-only retained native proof remains bound to
# its exact historical Git source; only the Python entry point changed here.
files=[]
for label,want in old['source_sha256'].items():
 scope,relative=label.split(':',1);path=(ROOT if scope=='coordinator' else ER)/relative;files.append(path)
 if path.resolve()==(HERE/'check_source_cpu_sweep.py').resolve():
  historical=subprocess.check_output(['git','show','469eb4e99:'+relative],cwd=ROOT);assert sha_bytes(historical)==want
 else:assert sha_bytes(path.read_bytes())==want,(label,want)
helpers=[HERE/'coh_checked_sources.py',HERE/'coh_source_cpu_oracle.py',HERE/'inspect_root_partitions.py',HERE/'inspect_source_cpu_sweep.py',ROOT/'native-android/tools/material_fixture/original_delta_check.py',Path(__file__),HERE/'check_source_cpu_sweep.py']
frozen={f.resolve():f.read_bytes() for f in files+helpers}
for f,raw in frozen.items():
 if f.read_bytes()!=raw:raise RuntimeError('source changed during pre-import freeze: '+str(f))
guard_path=(HERE/'coh_checked_sources.py').resolve();ns={'__name__':'checked_source_bootstrap','__file__':str(guard_path)};exec(compile(frozen[guard_path],str(guard_path),'exec',dont_inherit=True),ns);checked=ns['CheckedSources'](frozen);checked.verify()
for path,want in old['input_sha256'].items():assert sha_bytes(Path(path).read_bytes())==want,path
parts=checked.load('partitions',HERE/'inspect_root_partitions.py');checked.verify();resource_path=next(Path(x) for x in old['input_sha256'] if x.endswith('/resources.cohres'));partitions=parts.build(resource_path,a.root_coverage);assert len(partitions['rows'])==3083;checked.verify()
inspector=checked.load('sweep_inspector',HERE/'inspect_source_cpu_sweep.py');reconciled=inspector.inspect(a.receipt,a.ledger,a.root_coverage,HERE/'tests/source_special_routes.json');assert reconciled['passed'];checked.verify()
coverage=json.loads(a.root_coverage.read_text());models=coverage['models'];bodies={m['asset_path']:m['body_sha256'] for m in models};assert bodies==old['body_sha256'];assert len(bodies)==391
for path,want in bodies.items():assert sha_bytes((a.body_directory/path).read_bytes())==want
ledger=json.loads(zlib.decompress(a.ledger.read_bytes()));original=checked.load('original_delta',ROOT/'native-android/tools/material_fixture/original_delta_check.py');oracle=checked.load('source_cpu_oracle',HERE/'coh_source_cpu_oracle.py')
with tempfile.TemporaryDirectory(prefix='coh-checked-original-') as td:proof=oracle.compare(models,ledger['pairs'],bodies,a.body_directory,original,ROOT/'upstream/ouroboros/Common/seq/anim.c',Path(td),run)
assert proof==old['original_delta'];checked.verify()
for path,want in old['input_sha256'].items():assert sha_bytes(Path(path).read_bytes())==want,path
for path,want in bodies.items():assert sha_bytes((a.body_directory/path).read_bytes())==want
result={'passed':True,'scope':'Checked-source execution closure and fresh original-delta replay over exact retained469 native sweep/ledger; not retroactive proof of old helper-byte execution','source_sha256':{str(f):sha_bytes(raw) for f,raw in frozen.items()},'input_sha256':{str(f):sha_bytes(f.read_bytes()) for f in (a.receipt,a.ledger,a.root_coverage)},'checked_source_execution':checked.loads,'all_project_sources_frozen_before_first_project_exec':True,'native_sweep_reexecuted':False,'old_helper_byte_execution_claimed':False,'original_delta_reexecuted_from_checked_source':True,'original_delta':proof,'reconciled_native_evidence':reconciled,'world_authority':False,'client_materials_available':False,'android_executed':False,'original32_readModel_executed':False}
with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'passed':True,'native_sweep_reexecuted':False,'original_delta':proof,'checked_helpers':len(checked.loads)}))
