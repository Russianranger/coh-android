#!/usr/bin/env python3
"""Offline independent consistency controls; never source/material admission."""
import argparse,copy,hashlib,json,tempfile,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
for name in ('receipt','ledger','root-coverage','output'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();special=HERE/'tests/source_special_routes.json'
source_files=[Path(__file__),HERE/'inspect_source_cpu_sweep.py',HERE/'coh_checked_sources.py'];input_files=[a.receipt,a.ledger,a.root_coverage,special]
for f,limit in zip(input_files,(256<<10,2<<20,4<<20,32<<10)):
 if f.stat().st_size>limit:raise ValueError('bounded consistency input')
frozen={f.resolve():f.read_bytes() for f in source_files+input_files}
for f,raw in frozen.items():
 if f.read_bytes()!=raw:raise RuntimeError('changed pre-import input: '+str(f))
guard_path=(HERE/'coh_checked_sources.py').resolve();ns={'__name__':'checked_source_bootstrap','__file__':str(guard_path)}
exec(compile(frozen[guard_path],str(guard_path),'exec',dont_inherit=True),ns)
checked=ns['CheckedSources'](frozen);module=checked.load('inspect_sweep',HERE/'inspect_source_cpu_sweep.py')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads(a.receipt.read_text());data=json.loads(zlib.decompress(a.ledger.read_bytes()));assert module.inspect(a.receipt,a.ledger,a.root_coverage,special)['passed'];cases=[]
mutations=[('missing_pair',lambda d,r:d['pairs'].pop()),('wrong_owner_identity',lambda d,r:d['pairs'][0].update(owners=[0])),('altered_model',lambda d,r:d['pairs'][0].update(model='fake')),('ordinary_refusal',lambda d,r:next(x for x in d['pairs'] if not x['status']).update(status=2)),('special_promoted',lambda d,r:next(x for x in d['pairs'] if x['status']==2).update(status=0)),('lost_reflection_points',lambda d,r:next(x for x in d['pairs'] if x['quad_count']).update(quad_count=0)),('lost_pivot_points',lambda d,r:next(x for x in d['pairs'] if x['pivot_count']).update(pivot_count=0)),('pinned_cleanup',lambda d,r:d['cleanup'][0].update(pinned_blobs=1)),('duplicate_file',lambda d,r:d['files'][0].update(file=d['files'][1]['file'])),('raised_peak',lambda d,r:d['pairs'][0].update(cpu_peak=97<<20)),('dropped_cpu_indices',lambda d,r:next(x for x in d['pairs'] if not x['status']).update(packet_bytes=1)),('world_scope_promoted',lambda d,r:d['scope'].update(world_authority=True)),('material_scope_promoted',lambda d,r:r.update(client_materials_available=True)),('original32_claimed',lambda d,r:r.update(original32_readModel_executed=True)),('lost_scalar_comparison',lambda d,r:r['original_delta'].update(scalars_compared=0)),('missing_ubsan',lambda d,r:r['modes'].pop('ubsan'))]
with tempfile.TemporaryDirectory(prefix='coh-sweep-negative-') as td:
 temp=Path(td)
 for name,change in mutations:
  d=copy.deepcopy(data);r=copy.deepcopy(receipt);change(d,r);raw=(json.dumps(d,separators=(',',':'))+'\n').encode();compressed=zlib.compress(raw,9);r['ledger_sha256']=hashlib.sha256(compressed).hexdigest();r['ledger_decoded_sha256']=hashlib.sha256(raw).hexdigest();rp=temp/'receipt.json';lp=temp/'ledger.zlib';rp.write_text(json.dumps(r));lp.write_bytes(compressed)
  try:module.inspect(rp,lp,a.root_coverage,special)
  except ValueError:cases.append(name)
  else:raise AssertionError('corrupted proof admitted: '+name)
 for name,compressed in [('trailing_zlib',a.ledger.read_bytes()+b'junk'),('truncated_zlib',a.ledger.read_bytes()[:-1])]:
  r=copy.deepcopy(receipt);r['ledger_sha256']=hashlib.sha256(compressed).hexdigest();rp=temp/'receipt.json';lp=temp/'ledger.zlib';rp.write_text(json.dumps(r));lp.write_bytes(compressed)
  try:module.inspect(rp,lp,a.root_coverage,special)
  except ValueError:cases.append(name)
  else:raise AssertionError('malformed stream admitted: '+name)
checked.verify()
result={'checked_source_execution':checked.loads,'passed':True,'positive_controls':1,'negative_controls':len(cases),'cases':cases,'source_sha256':{str(f):sha(f) for f in source_files},'input_sha256':{str(f):sha(f) for f in (a.receipt,a.ledger,a.root_coverage,special)},'authority_admission':False}
with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'passed':True,'positive_controls':1,'negative_controls':len(cases)}))
