#!/usr/bin/env python3
"""Bounded PRE-worldSendUpdate eligibility observer vs unchanged source producer."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,subprocess,tempfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd):
 r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=180,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'})
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 return r.stdout

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 paths=[HERE/n for n in ('source_groups_eligibility.inc','test_groups_eligibility.c','check_groups_eligibility.py','source_groups_transaction.inc','stage_groups_transaction.py','GROUPS_ELIGIBILITY.md')]
 paths += [ROOT/n for n in ('native-android/engine/replication/groups_oracle.py','native-android/engine/replication/groups-source-pins.json','native-android/engine/replication/tests/groups_oracle_shim.h','native-android/engine/replication/tests/groups_oracle_harness.c','native-android/tools/protocol_fixture/prepare.py')]
 frozen={str(p.relative_to(ROOT)):sha(p) for p in paths}
 spec=importlib.util.spec_from_file_location('groups_eligibility_original',ROOT/'native-android/engine/replication/groups_oracle.py');o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o)
 sources,pins=o.sources_and_pins(ROOT);assert pins==json.loads((ROOT/'native-android/engine/replication/groups-source-pins.json').read_text())
 modes={};binaries={}
 with tempfile.TemporaryDirectory(prefix='coh-group-eligibility-') as tmp:
  tmp=Path(tmp);o.compile_oracle(ROOT,tmp,sources);source=(tmp/'groups-original.c').read_text()
  # Unchanged legacy producer is outside new-observer UBSan scope.
  for path,names in o.SOURCE_FUNCTIONS.items():
   for name in names:
    body=o.extract(sources[path],name);assert source.count(body)==1;source=source.replace(body,'__attribute__((no_sanitize("undefined")))\n'+body)
  stage_spec=importlib.util.spec_from_file_location('groups_stage',HERE/'stage_groups_transaction.py');stage_module=importlib.util.module_from_spec(stage_spec);stage_spec.loader.exec_module(stage_module)
  original=sources['MapServer/src/group/groupnetsend.c'];staged=stage_module.stage(original)
  include='\n'+(HERE/'source_groups_eligibility.inc').read_text()+'\n'+(HERE/'source_groups_transaction.inc').read_text()+'\n'
  assert staged.replace(include,'',1).replace('    coh_groups_transaction_begin(link,full_update);\n','').replace('    coh_groups_transaction_finish(pak);\n','')==original
  try:stage_module.stage(original+'\n')
  except ValueError:pass
  else:raise AssertionError('changed source admitted')
  body=o.extract(original,'worldSendUpdate');hooked=o.extract(staged,'worldSendUpdate')
  source=source.replace('__attribute__((no_sanitize("undefined")))\n'+body,(HERE/'source_groups_eligibility.inc').read_text()+'\n'+(HERE/'source_groups_transaction.inc').read_text()+'\n__attribute__((no_sanitize("undefined")))\n'+hooked)
  source+='\n'+(HERE/'test_groups_eligibility.c').read_text();(tmp/'test.c').write_text(source)
  for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   binary=tmp/mode;run(['cc','-std=c99','-w','-fno-strict-aliasing',*flags,'-I'+str(HERE),'-I'+str(ROOT/'native-android/include'),tmp/'test.c','-lm','-lz','-o',binary]);modes[mode]=json.loads(run([binary]));binaries[mode]=sha(binary)
 assert o.sources_and_pins(ROOT)[1]==pins
 assert all(v==modes['release'] for v in modes.values());assert frozen=={str(p.relative_to(ROOT)):sha(p) for p in paths}
 result={'schema':'coh-source-groups-eligibility-v1','passed':True,'source_sha256':frozen,'original_source':pins,'modes':modes,'binary_sha256':binaries,'private_staged_sha256_lf':hashlib.sha256(staged.encode()).hexdigest(),'zero_alloc_observer':True,'pre_producer_only':True,'output_provisional_until_packet_binding':True,'source_generation_admitted':False,'live_groups_captured':False,'shipping_changed':False,'android_build':False,'legacy_original_ubsan':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'modes':modes}))
if __name__=='__main__':main()
