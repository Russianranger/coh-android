#!/usr/bin/env python3
"""Full attributes + existing monitor against retained whole-original corpora."""
import importlib.util
import argparse,gzip,hashlib,json,os,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def read(p):
 p=p.resolve()
 if str(p).startswith(str(ROOT/'upstream/ouroboros')+'/'):return subprocess.check_output(['git','-C',ROOT,'show','HEAD:'+str(p.relative_to(ROOT))])
 return p.read_bytes()
def sha(p):return hashlib.sha256(read(p)).hexdigest()
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,**kw)
 if p.returncode:raise RuntimeError(str(args)+'\n'+p.stdout[-8000:]+p.stderr[-8000:])
 return p.stdout
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 provider=ROOT/'native-android/combined-client/diagnostics/attribute-full-20261017';fullpath=provider/'host-proof.json.gz'
 if sha(fullpath)!='be06f922d1ef9ca5d8f851fc61d212b079c896d1574c4eeedfe80fbb1e41b579':raise ValueError('retained full corpus')
 full=json.loads(gzip.decompress(fullpath.read_bytes()))
 if any(sha(ROOT/p)!=h for p,h in full['source_sha256'].items()):raise ValueError('original full source binding')
 old=ROOT/'native-android/combined-client/diagnostics/allents-tail-20261017';monpath=old/'attribute-monitor-fixtures.json.gz'
 if sha(monpath)!='eaf6ca648f4cac4809634a2475e063f7f4c92ca820ded18eb34f0f94c61cba41':raise ValueError('retained monitor corpus')
 monitors=json.loads(gzip.decompress(monpath.read_bytes()));dictionary=HERE/'../attribute-dictionary';dictproof=json.loads(gzip.decompress((dictionary/'qualification/20261017/host-proof.json.gz').read_bytes()))
 if any(sha(ROOT/p)!=h for p,h in dictproof['source_sha256'].items()):raise ValueError('frozen dictionary source binding')
 own=json.loads((dictionary/'ordered-candidate.json').read_text())['ordered_sender_rows'];other=json.loads((provider/'ordered-rows.json').read_text())['ordered_sender_rows']
 if len(own)!=69 or any(any(x[k]!=y[k]for k in('category','row','category_rows','type','style','key','offset','lookup_key','category_name','name','display_name','tooltip'))for x,y in zip(own,other)):raise ValueError('actual schema order mismatch')
 sources=[HERE/'coh_attrib_description.c',HERE/'coh_attrib_monitor.c',HERE/'../replication/coh_replication.c',dictionary/'coh_attribute_dictionary.c'];paths={ROOT/p for p in full['source_sha256']}|{ROOT/p for p in dictproof['source_sha256']}|set(sources)|{HERE/n for n in('coh_attrib_description.h','test_description.c','check_description.py','coh_attrib_monitor.h','description_controls.py','FULL_DESCRIPTION.md')}|{fullpath,provider/'source-binding.json',monpath};hashes={str(p.resolve().relative_to(ROOT)):sha(p)for p in sorted(paths)};checks={};binaries={};stack=[]
 spec=importlib.util.spec_from_file_location('attribute_bound_controls',HERE/'description_controls.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper);controls=helper.controls(full['cases'])
 lines=[];rows=[];monitorrows=[];controlrows=[]
 for i,c in enumerate(full['cases']):
  raw=bytes.fromhex(c['wire_hex']);name='full_'+str(i);lines.append('static const unsigned char '+name+'[]={'+','.join(map(str,raw))+'};');values=[r['value_word']for r in c['rows']];buff=[r['buff']for r in c['rows']]
  for kind,nums in [('values',values),('buff',buff)]:lines.append('static const uint32_t '+kind+'_'+str(i)+'[]={'+','.join(str(n)+'u'for n in nums)+'};')
  mods=['{'+','.join([str(m[k])+'u'for k in('hash','power','source_type','server_id','chance_word','magnitude_word')]+[json.dumps(m['name'])])+'}'for m in c['modifiers']];lines.append('static const ExpectedMod mods_'+str(i)+'[]={'+(','.join(mods)if mods else'{0,0,0,0,0,0,""}')+'};');rows.append('{'+name+',sizeof('+name+'),'+','.join(map(str,[c['end'],c['begin'],c['aligned'],c['new_target'],int(c['target_owner']is not None),c['target_owner']or 0,len(mods)]))+',values_'+str(i)+',buff_'+str(i)+',mods_'+str(i)+'}')
 for i,c in enumerate(monitors):
  raw=bytes.fromhex(c['wire_hex']);name='monitor_'+str(i);lines.append('static const unsigned char '+name+'[]={'+','.join(map(str,raw))+'};');slots=[]
  for s in c['expected']['slots']:slots.append('{'+','.join(str(s.get(k,0))+'u'for k in('present','key','value_word','buff'))+'}')
  monitorrows.append('{'+name+',sizeof('+name+'),'+','.join(map(str,[c['end_bit'],c['begin_bit'],c['aligned']]))+',{'+str(c['expected']['new_target'])+',0,{'+','.join(slots)+'},'+str(c['begin_bit'])+','+str(c['end_bit'])+'}}')
 for i,c in enumerate(controls):
  name='control_'+str(i);lines.append('static const unsigned char '+name+'[]={'+','.join(map(str,c['wire']))+'};');controlrows.append('{'+name+',sizeof('+name+'),'+','.join(map(str,[c['bits'],c['mode'],c['status'],c['count']]))+'}')
 fixtures='\n'.join(lines)+'\nstatic const Fixture fixtures[]={'+','.join(rows)+'};\nstatic const MonitorFixture monitors[]={'+','.join(monitorrows)+'};\nstatic const ControlFixture bound_controls[]={'+','.join(controlrows)+'};\n'
 with tempfile.TemporaryDirectory(prefix='coh-attribute-full-native-')as tmp:
  work=Path(tmp);(work/'description-fixtures.h').write_text(fixtures)
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]):
   exe=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-fmax-errors=2','-fno-diagnostics-show-caret',*flags,'-I'+str(work),*sources,HERE/'test_description.c','-lcrypto','-lm','-o',exe]);checks[mode]=json.loads(run([exe,dictionary/'attrib_descriptions.bin'],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(exe)
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    name,n,kind=line.split('\t')
    if any(str(s)+':'in name for s in sources):stack.append({'function':name,'bytes':int(n),'kind':kind})
  if not stack or sum(s['bytes']for s in stack)>16384 or any(s['kind']not in('static','dynamic,bounded')for s in stack):raise ValueError('native stack bound')
  cpp=work/'header.cpp';cpp.write_text('#include "coh_attrib_description.h"\nint main(){return coh_attrib_description_read(nullptr,nullptr,nullptr,0,nullptr,nullptr,nullptr,0,0)==COH_INVALID?0:1;}\n');objects=[]
  for i,source in enumerate(sources):
   obj=work/(str(i)+'.o');run(['cc','-std=c99','-O2','-c',source,'-o',obj]);objects.append(obj)
  run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-lm','-o',work/'cpp']);run([work/'cpp'])
 if any(x!=checks['release']for x in checks.values()):raise ValueError('mode mismatch')
 if hashes!={str(p.resolve().relative_to(ROOT)):sha(p)for p in sorted(paths)}:raise ValueError('source changed')
 result={'schema':'coh-native-full-attribute-v1','passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).strip(),'source_sha256':hashes,'checks':checks,'binary_sha256':binaries,'fixture_sha256':hashlib.sha256(fixtures.encode()).hexdigest(),'native_stack':stack,'cpp_link_passed':True,'original_full_source_commit':'e093b451607a38e4df1c3a75784e9cb2fb4265ea','retained_full_source_cases':len(full['cases']),'retained_full_source_checks':full['checks'],'monitor_source_cases':len(monitors),'synthetic_bound_controls':[{'label':c['label'],'mode':c['mode'],'bits':c['bits'],'status':c['status'],'sha256':hashlib.sha256(c['wire']).hexdigest()}for c in controls],'original_source_binding':'Exact pinned Git blobs used for sparse upstream source; retained original whole-function corpus, no producer replay.','runtime_cache_generation':False,'dictionary_authority':False,'original_attribute_state_applied':False,'actor_authority':False,'initial_suffix_integrated':False,'external_crypto_sanitizer_and_stack_closure':False,'android_built':False,'thor_accepted':False}
 with a.output.open('xb')as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0)as out:out.write((json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({'passed':True,'checks':checks}))
if __name__=='__main__':main()
