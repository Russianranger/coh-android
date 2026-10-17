#!/usr/bin/env python3
"""Compile-only native core stack reservation audit, no capture or APK."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd):
 r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=120)
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 return r.stdout
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
paths=[HERE/'coh_runtime_groups_witness.c',HERE/'coh_catalog_seed.c',HERE/'runtime_snapshot.c',HERE.parent/'scenecatalog/coh_catalog_owner.c',HERE.parent/'replication/coh_groups.c',HERE.parent/'replication/coh_replication.c']
deps=paths+[Path(__file__)];deps+=list((ROOT/'native-android/engine').rglob('*.h'));deps+=list((ROOT/'native-android/include').rglob('*.h'));deps+=list((ROOT/'native-android/protocol').rglob('*.h'));deps=sorted(set(deps));pins={str(p.relative_to(ROOT)):sha(p) for p in deps}
reserve=128*1024;assert '#define COH_GROUPS_WITNESS_FIXED_SCRATCH_BYTES (128u*1024u)' in (HERE/'coh_runtime_groups_witness.h').read_text()
modes={}
with tempfile.TemporaryDirectory(prefix='coh-groups-stack-') as tmp:
 for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  tables={}
  for path in paths:
   target=Path(tmp)/(mode+'-'+path.stem+'.o');run([os.environ.get('CC','cc'),'-std=c99',*flags,'-fstack-usage','-c',path,'-o',target]);rows={}
   for line in target.with_suffix('.su').read_text().splitlines():
    loc,size,kind=line.split('\t');name=loc.rsplit(':',1)[1]
    if 'unbounded' in kind:raise ValueError('unbounded frame '+name)
    rows[name]=int(size)
   tables[path.stem]=rows
  witness=tables['coh_runtime_groups_witness'];seed=tables['coh_catalog_seed']
  # Deliberately sum every replication/groups frame rather than infer optimistic
  # sibling exclusivity. Those modules are nonrecursive; include every relevant
  # source-owner/graph getter frame and all witness/seed private helper frames.
  helper=sum(tables['coh_replication'].values())+sum(tables['coh_groups'].values())
  owners={'coh_catalog_owner_bytes','coh_catalog_owner_binding','coh_catalog_owner_owned_bytes','coh_catalog_owner_file','coh_catalog_owner_record','coh_catalog_owner_retain','coh_catalog_owner_release'}
  getters={'coh_runtime_graph_sources','coh_runtime_graph_binding','coh_runtime_graph_report','coh_runtime_graph_slot','coh_runtime_graph_root','coh_runtime_graph_node'}
  helper+=sum(v for k,v in tables['coh_catalog_owner'].items() if k in owners or k.startswith('u32'))
  helper+=sum(v for k,v in tables['runtime_snapshot'].items() if k in getters)
  helper+=sum(v for k,v in witness.items() if k not in {'coh_runtime_groups_witness_create','coh_runtime_graph_compare_groups_witness'})
  helper+=sum(v for k,v in seed.items() if k!='coh_catalog_seed_visit')
  helper+=4096 # Explicit fixed libc/marshalling margin; external providers extra.
  create=witness['coh_runtime_groups_witness_create']+witness['coh_runtime_graph_compare_groups_witness']+helper
  visit=seed['coh_catalog_seed_visit']+witness['coh_runtime_graph_compare_groups_witness']+helper
  if max(create,visit)>reserve:raise ValueError('native core exceeds reservation')
  modes[mode]={'frames':tables,'conservative_helpers_plus_margin':helper,'witness_create_chain_bound':create,'seed_visit_chain_bound':visit,'reserved_bytes':reserve}
assert pins=={str(p.relative_to(ROOT)):sha(p) for p in deps}
r={'schema':'coh-groups-native-stack-budget-v1','passed':True,'compiler':run([os.environ.get('CC','cc'),'--version']).splitlines()[0],'source_sha256':pins,'modes':modes,'external_provider_stack_included':False,'caller_charges_external_provider_and_owner_metadata':True,'android_compiler_qualified':False,'actual_runtime_executed':False,'owned_limit_unchanged':32*1024*1024,'aggregate_limit_unchanged':96*1024*1024}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'bounds':{k:{n:v[n] for n in ['witness_create_chain_bound','seed_visit_chain_bound','reserved_bytes']} for k,v in modes.items()}}))
