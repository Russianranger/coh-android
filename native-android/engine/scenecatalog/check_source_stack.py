#!/usr/bin/env python3
"""Stack-only compiler call-chain supplement; never executes geometry or native binaries."""
import argparse,gzip,hashlib,json,os,re,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
script_bytes=Path(__file__).read_bytes()
old=HERE/'evidence/source-measure-host.json';receipt=json.loads(old.read_text());frozen={Path(f):Path(f).read_bytes() for f in receipt['source_sha256']}
for f,b in frozen.items():assert hashlib.sha256(b).hexdigest()==receipt['source_sha256'][str(f)],f
roots=['coh_source_sealed_create','coh_source_sealed_measure','coh_source_ws_probe','coh_source_sealed_free','coh_source_sealed_entry','coh_source_sealed_part','coh_source_sealed_find','coh_source_sealed_report','coh_source_sealed_identity']
sources=sorted(f for f in frozen if f.suffix=='.c' and '/tests/' not in str(f));includes=sorted({f.parent for f in frozen if f.name in ('coh_native_core.h','coh_source_sealed.h','coh_working_set.h')})
# The external root include fallback supplies only the read-only working-set API.
working=next(f for f in frozen if f.name=='coh_working_set.h');includes.append(working.parent.parent/'scenecatalog')
def run(argv):
 r=subprocess.run(list(map(str,argv)),capture_output=True,text=True,timeout=120)
 if r.returncode:raise RuntimeError(r.stderr[-5000:])
 return r.stdout
modes={};raw={};version=run(['cc','--version'])
with tempfile.TemporaryDirectory(prefix='coh-native-stack-')as td:
 for mode,flags in [('O0',['-O0']),('O1',['-O1']),('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  definitions={};edges={};declarations=set();frames={};mode_raw={}
  for index,f in enumerate(sources):
   obj=Path(td)/(mode+str(index)+'.o');run(['cc','-std=c11','-ffp-contract=off','-pthread',*['-I'+str(d)for d in includes],*flags,'-fstack-usage','-fcallgraph-info=su','-c',f,'-o',obj])
   ci=obj.with_suffix('.ci').read_text();su=obj.with_suffix('.su').read_text();mode_raw[str(f)]={'ci':ci,'su':su}
   for line in ci.splitlines():
    if line.startswith('node: '):
     title=re.search(r'title: "([^"]+)"',line).group(1);label=re.search(r'label: "([^"]+)"',line).group(1);frame=re.search(r'\\n([0-9]+) bytes \(([^)]+)\)',label)
     if frame:
      su_values={(r.split('\t')[0].rsplit(':',1)[-1],int(r.split('\t')[1]),r.split('\t')[2])for r in su.splitlines()}
      assert (label.split('\\n')[0],int(frame.group(1)),frame.group(2))in su_values,('CI/SU mismatch',title)
      assert title not in definitions,('duplicate native definition',title)
      definitions[title]={'bytes':int(frame.group(1)),'kind':frame.group(2),'translation_unit':str(f),'label':label};edges.setdefault(title,set())
     else:declarations.add(title)
    elif line.startswith('edge: '):
     src=re.search(r'sourcename: "([^"]+)"',line).group(1);dst=re.search(r'targetname: "([^"]+)"',line).group(1);edges.setdefault(src,set()).add(dst)
  # Original find passes rowcmp to libc bsearch; compiler graphs cannot describe
  # callbacks through that external library. Include its native frame explicitly,
  # while leaving bsearch's own implementation stack external, never zero-proven.
  index_source=next(f for f in sources if f.name=='coh_resource_index.c');needle='return bsearch(&needle,i->rows,i->count,sizeof(Row),rowcmp);';assert needle in frozen[index_source].decode()
  rowcmp=str(index_source)+':rowcmp';assert rowcmp in definitions
  edges.setdefault('bsearch',set()).add(rowcmp)
  seen=set();active=set();cache={}
  def bound(node):
   if node in active:raise RuntimeError('reachable recursive native path: '+node)
   if node in cache:return cache[node]
   active.add(node);seen.add(node);frame=definitions.get(node)
   if frame:assert frame['kind']=='static'or frame['kind']=='dynamic,bounded',(node,frame)
   elif node.startswith('coh_')or'.c:'in node:raise RuntimeError('unresolved native dependency '+node)
   best=(0,[])
   for child in sorted(edges.get(node,())):
    b,path=bound(child)
    if b>best[0]:best=(b,path)
   active.remove(node);value=((frame['bytes']if frame else 0)+best[0],[node]+best[1]);cache[node]=value;return value
  root_results={r:{'native_chain_bytes':bound(r)[0],'path':bound(r)[1]}for r in roots};maxroot=max(root_results,key=lambda r:root_results[r]['native_chain_bytes']);external=sorted(n for n in seen if n not in definitions)
  if 'bsearch'in seen:assert {n for n in seen if 'bsearch'in edges.get(n,())}=={str(index_source)+':find'}
  modes[mode]={'roots':root_results,'maximum_native_chain_bytes':root_results[maxroot]['native_chain_bytes'],'maximum_root':maxroot,'reachable_native_frames':{n:definitions[n]for n in sorted(seen)if n in definitions},'reachable_edges':{n:sorted(c for c in edges.get(n,())if c in seen)for n in sorted(seen)},'external_cutpoints':external,'manual_callback_edge':['bsearch',rowcmp]}
  raw[mode]=mode_raw;print(json.dumps({'mode':mode,'maximum_native_chain_bytes':modes[mode]['maximum_native_chain_bytes'],'path':root_results[maxroot]['path'],'external_cutpoints':external}),flush=True)
for f,b in frozen.items():assert f.read_bytes()==b,f
assert Path(__file__).read_bytes()==script_bytes
result={'passed':True,'scope':'Compiler-only native reachable call-chain analysis, includes same-TU nesting and bsearch native comparator callback; external library/callback frames explicitly UNMEASURED. No geometry/source binaries executed.','historical_receipt_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'historical_file_maxima_superseded':True,'source_sha256':receipt['source_sha256'],'supplement_script_sha256':hashlib.sha256(script_bytes).hexdigest(),'compiler_version':version,'modes':modes,'reserve':16384,'all_modes_fit_reserve':all(v['maximum_native_chain_bytes']<=16384 for v in modes.values()),'production_changed':False,'native_geometry_reexecuted':False,'external_library_callback_stack_included':False,'world_authority':False,'raw_compiler_evidence':raw}
with a.output.open('xb')as f:f.write(gzip.compress((json.dumps(result,sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0))
