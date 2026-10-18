#!/usr/bin/env python3
"""Source-only prepared-input correction; no host tests/build/session replay."""
import argparse,hashlib,importlib.util,io,json,subprocess,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
REVISION='a6b20f8bb7aca2d19c7bee217bb961ce60427418'
OLD_TICK='790635fec2f21e49981c776815eb8e927e79ef5a277324b0e3601cc3b4bbade0'
NEW_TICK='a3810c112556b258ee2456a51eb28d6afeefd14b81c2fa97ed431659ae42a3d5'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def need(ok):
 if not ok:raise ValueError('PREPARED_OBSERVER_SUCCESSOR_REFUSED')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True,type=Path);args=ap.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
 pred=HERE/'qualification/host-03/qualification.json';proof=json.loads(pred.read_bytes());need(sha(pred.read_bytes())=='694ec7667e531a932656242fe45c5748d3c0dcbb26ba9f8cc5385e65f47d33b4')
 changed={'native-android/engine/initial-capture/server-initial-observer/'+n for n in ('sourcehooks.py','check_observer.py','CONTRACT.md')}
 unchanged={n:v for n,v in proof['source_sha256'].items()if n not in changed}
 need(all(sha((ROOT/n).read_bytes())==v for n,v in unchanged.items()))
 oldhook=subprocess.run(['git','show',REVISION+':native-android/engine/initial-capture/server-initial-observer/sourcehooks.py'],cwd=ROOT,capture_output=True,check=True).stdout
 need(sha(oldhook)==proof['source_sha256']['native-android/engine/initial-capture/server-initial-observer/sourcehooks.py'])
 hookraw=(HERE/'sourcehooks.py').read_bytes();need(oldhook.count(OLD_TICK.encode())==1 and oldhook.replace(OLD_TICK.encode(),NEW_TICK.encode(),1)==hookraw)
 hooks=load('coh_sio_successor_hooks',HERE/'sourcehooks.py')
 helper_path=ROOT/'native-android/tools/server-initial-observer-20261018/prepared_inputs.py'
 helper=load('coh_sio_successor_prepared',helper_path);prepared,reconstruction=helper.reconstruct(ROOT,with_proof=True)
 archive=ROOT/next(n for n in proof['source_sha256']if n.endswith('fresh-map-initial-owner-build-39099315295.zip'))
 with zipfile.ZipFile(archive)as z:inputs={n:z.read('fresh-groups-compile/source/'+n)if n in(hooks.GROUP,hooks.PROFILE)else prepared[n]for n in hooks.PATCHED}
 need(sha(inputs[hooks.TICK])==NEW_TICK);patched=hooks.transform(inputs);need(hooks.reverse(patched)==inputs);controls=2
 for name in hooks.PATCHED:
  for reverse in (False,True):
   bad=dict(patched if reverse else inputs);bad[name]+=b'\n'
   try:(hooks.reverse if reverse else hooks.transform)(bad)
   except ValueError:controls+=1
   else:raise ValueError('CHANGED_SOURCE_ACCEPTED')
 crlf={n:v.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')for n,v in inputs.items()};need(hooks.reverse(hooks.transform(crlf))==crlf);controls+=1
 # Read and verify exact retained execution evidence; never execute those ELFs.
 evidence=HERE/'qualification/host-03';elf_archive=evidence/'executed-host-elfs.tar.gz';need(sha(elf_archive.read_bytes())==proof['retained_elf_archive']['sha256'])
 for run in proof['runs']:
  name=run['mode']+'-'+run['role'];need(sha((evidence/(name+'.stdout')).read_bytes())==run['stdout_sha256']and(evidence/(name+'.stderr')).read_bytes()==b'')
 pins={str(p.relative_to(ROOT)):sha(p.read_bytes())for p in [HERE/'sourcehooks.py',HERE/'check_observer.py',HERE/'check_staged_successor.py',HERE/'CONTRACT.md',helper_path,*(ROOT/n for n in helper.source_paths(ROOT)),pred,elf_archive]}
 result={'schema':'coh-server-initial-prepared-source-successor-v1','passed':True,'predecessor_revision':REVISION,'predecessor_host_proof_sha256':sha(pred.read_bytes()),'source_sha256':pins,'unchanged_host_consumed_inputs':unchanged,'only_production_hook_change':'exact TICK baseline constant raw upstream -> inherited prepared source','old_tick_sha256':OLD_TICK,'prepared_tick_sha256':NEW_TICK,'prepared_tick_bytes':len(inputs[hooks.TICK]),'prepared_input_reconstruction':reconstruction,'source_recipe_controls':controls,'exact_reverse_files':5,'new_overlays_unchanged':True,'reused_unchanged_host_checks_per_mode':5135,'host_execution_replayed':False,'compiler_executed':False,'original_map_executed':False,'actual_failed_run_reclassified':False,'world_authority':False,'patched_sha256':{n:sha(v)for n,v in patched.items()}}
 (out/'qualification.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps({'passed':True,'source_controls':controls,'host_replayed':False}))
if __name__=='__main__':main()
