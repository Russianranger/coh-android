#!/usr/bin/env python3
"""Strict standalone raw-parser Android13 execution. No application/world permit."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import uuid
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SPECS={
 'creation':('coh-character-creation-prefix-qualification-v1','coh_character_creation_test',17979),
 'outer':('coh-character-outer-qualification-v1','coh_character_outer_test',22641),
 'power-info':('coh-power-info-qualification-v1','coh_power_info_test',380498),
}
REQUIRED={'creation': ['native-android/combined-client/diagnostics/character-outer-20261017/group4_oracle.py', 'native-android/combined-client/diagnostics/character-outer-20261017/independent.py', 'native-android/combined-client/diagnostics/character-outer-20261017/qualify_outer.py', 'native-android/combined-client/diagnostics/character-outer-20261017/source-pins.json', 'native-android/engine/character-data/check.py', 'native-android/engine/character-data/coh_character_data.c', 'native-android/engine/character-data/coh_character_data.h', 'native-android/engine/character-data/oracle_fixture.c.inc', 'native-android/engine/character-data/oracle_shim.h', 'native-android/engine/character-data/source-pins.json', 'native-android/engine/coh_contracts.h', 'native-android/engine/entities/character-initial-source-pins.json', 'native-android/engine/entities/check_character_creation.py', 'native-android/engine/entities/check_character_initial.py', 'native-android/engine/entities/check_teammate_buffs.py', 'native-android/engine/entities/coh_character_creation.c', 'native-android/engine/entities/coh_character_creation.h', 'native-android/engine/entities/coh_character_initial.c', 'native-android/engine/entities/coh_character_initial.h', 'native-android/engine/entities/coh_character_prefix.c', 'native-android/engine/entities/coh_character_prefix.h', 'native-android/engine/entities/coh_character_ui.c', 'native-android/engine/entities/coh_character_ui.h', 'native-android/engine/entities/coh_costume.h', 'native-android/engine/entities/coh_entities.c', 'native-android/engine/entities/coh_entities.h', 'native-android/engine/entities/coh_taskforce.h', 'native-android/engine/entities/run_character_android.py', 'native-android/engine/entities/stats_oracle_shim.h', 'native-android/engine/entities/test_character_creation.c', 'native-android/engine/replication/coh_replication.c', 'native-android/engine/replication/coh_replication.h', 'native-android/include/coh_native_core.h', 'native-android/tools/protocol_fixture/prepare.py'], 'power-info': ['native-android/engine/character-data/coh_character_data.h', 'native-android/engine/coh_contracts.h', 'native-android/engine/entities/run_character_android.py', 'native-android/engine/entity-globals/check_power_info.py', 'native-android/engine/entity-globals/coh_power_info.c', 'native-android/engine/entity-globals/coh_power_info.h', 'native-android/engine/entity-globals/power-info-source-pins.json', 'native-android/engine/entity-globals/power_info_fixture.c.inc', 'native-android/engine/entity-globals/power_info_oracle_shim.h', 'native-android/engine/entity-globals/test_power_info.c', 'native-android/engine/replication/coh_replication.c', 'native-android/engine/replication/coh_replication.h', 'native-android/include/coh_native_core.h', 'native-android/tools/protocol_fixture/prepare.py'], 'outer': ['native-android/combined-client/diagnostics/character-outer-20261017/group4_oracle.py', 'native-android/combined-client/diagnostics/character-outer-20261017/group56-source-pins.json', 'native-android/combined-client/diagnostics/character-outer-20261017/group56_independent.py', 'native-android/combined-client/diagnostics/character-outer-20261017/group56_oracle.py', 'native-android/combined-client/diagnostics/character-outer-20261017/host-proof.json', 'native-android/combined-client/diagnostics/character-outer-20261017/independent.py', 'native-android/combined-client/diagnostics/character-outer-20261017/qualify_outer.py', 'native-android/combined-client/diagnostics/character-outer-20261017/source-pins.json', 'native-android/engine/character-data/check.py', 'native-android/engine/character-data/coh_character_data.c', 'native-android/engine/character-data/coh_character_data.h', 'native-android/engine/character-data/oracle_fixture.c.inc', 'native-android/engine/character-data/oracle_shim.h', 'native-android/engine/character-data/source-pins.json', 'native-android/engine/coh_contracts.h', 'native-android/engine/entities/character-initial-source-pins.json', 'native-android/engine/entities/character-tail-admission-pins.json', 'native-android/engine/entities/character_tail_fixture.py', 'native-android/engine/entities/check_character_initial.py', 'native-android/engine/entities/check_character_outer.py', 'native-android/engine/entities/check_teammate_buffs.py', 'native-android/engine/entities/coh_character_creation.c', 'native-android/engine/entities/coh_character_creation.h', 'native-android/engine/entities/coh_character_initial.c', 'native-android/engine/entities/coh_character_initial.h', 'native-android/engine/entities/coh_character_options_schema.h', 'native-android/engine/entities/coh_character_outer.c', 'native-android/engine/entities/coh_character_outer.h', 'native-android/engine/entities/coh_character_prefix.c', 'native-android/engine/entities/coh_character_prefix.h', 'native-android/engine/entities/coh_character_tail.c', 'native-android/engine/entities/coh_character_tail.h', 'native-android/engine/entities/coh_character_ui.c', 'native-android/engine/entities/coh_character_ui.h', 'native-android/engine/entities/coh_costume.h', 'native-android/engine/entities/coh_entities.c', 'native-android/engine/entities/coh_entities.h', 'native-android/engine/entities/coh_taskforce.h', 'native-android/engine/entities/run_character_android.py', 'native-android/engine/entities/stats_oracle_shim.h', 'native-android/engine/entities/test_character_outer.c', 'native-android/engine/replication/coh_replication.c', 'native-android/engine/replication/coh_replication.h', 'native-android/include/coh_native_core.h', 'native-android/tools/protocol_fixture/prepare.py']}

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
 if path.is_symlink() or path.stat().st_size>2*1024**2:raise ValueError('receipt path/size')
 return json.loads(path.read_text())
def child(root,name):
 if not isinstance(name,str) or not name or Path(name).is_absolute() or '..' in Path(name).parts or '\\' in name:raise ValueError('source path')
 p=root/name
 if any(x.is_symlink() for x in [p,*p.parents] if x!=root.parent):raise ValueError('symlink path')
 if not p.resolve().is_relative_to(root.resolve()):raise ValueError('path escapes owner')
 return p

def admit(kind,artifacts,repo):
 schema,binary_name,checks=SPECS[kind]
 proof=read(child(artifacts,'host.json'))
 if proof.get('schema')!=schema or proof.get('passed') is not True or proof.get('actor_publication') is not False or proof.get('acknowledgments_enabled') is not False:raise ValueError('scope')
 expected=proof.get('checks',{}).get('release')
 if not isinstance(expected,dict) or expected.get('passed') is not True or type(expected.get('checks')) is not int or expected['checks']!=checks or expected.get('actor_publication') is not False:raise ValueError('native scope')
 scope={'creation':'whole_character_complete','outer':'whole_initial_update_complete','power-info':'whole_initial_update'}[kind]
 if proof.get(scope) is not False or expected.get(scope) is not False:raise ValueError('whole transaction scope')
 if any(json.dumps(proof.get('checks',{}).get(k),sort_keys=True)!=json.dumps(expected,sort_keys=True) for k in ('asan','ubsan')):raise ValueError('sanitizer results')
 core=proof.get('source_sha256',{});provider=proof.get('provider_sha256',{})
 if not isinstance(core,dict) or not isinstance(provider,dict) or set(core)&set(provider):raise ValueError('overlapping source/provider ownership')
 sources={**core,**provider}
 if not set(REQUIRED[kind]).issubset(sources):raise ValueError('incomplete source closure')
 required={'creation':'native-android/engine/entities/coh_character_creation.c','outer':'native-android/engine/entities/coh_character_outer.c','power-info':'native-android/engine/entity-globals/coh_power_info.c'}[kind]
 runner=Path(__file__).resolve().relative_to(ROOT).as_posix()
 if required not in sources or runner not in sources:raise ValueError('required source/driver absent')
 for name,sha in sources.items():
  if not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{64}',sha) or digest(child(repo,name))!=sha:raise ValueError('source identity')
 if digest(Path(__file__))!=sources[runner]:raise ValueError('executing runner identity')
 fixtures={'initial_fixtures.h':proof['fixture_initial']['sha256'],'ui_fixtures.h':proof['ui_fixtures_sha256']} if kind=='creation' else ({'power_info_fixtures.h':proof['fixtures']['sha256']} if kind=='power-info' else {})
 if kind=='outer':
  fixtures={'initial_fixtures.h':proof['fixture_initial']['sha256'],'ui_fixtures.h':proof['ui_fixtures_sha256'],'tail_fixtures.h':proof['tail_fixtures_sha256']}
  if proof.get('fixtures_sha256')!=fixtures or proof.get('outer_character_wire_grammar_complete') is not True:raise ValueError('outer fixture/scope binding')
 for name,sha in fixtures.items():
  if digest(child(artifacts,'android/'+name))!=sha:raise ValueError('source fixture identity')
 builds=proof.get('android',{})
 if set(builds)!={'arm64-v8a','x86_64'}:raise ValueError('both ABI builds required')
 entries={}
 for abi,machine in [('arm64-v8a',183),('x86_64',62)]:
  receipt=read(child(artifacts,'android/'+abi+'/receipt.json'))
  if receipt!=builds[abi] or receipt.get('built') is not True or receipt.get('executed') is not False or receipt.get('binary')!=binary_name or receipt.get('source_sha256')!=proof['source_sha256']:raise ValueError('build binding')
  if receipt.get('fixtures_sha256')!=fixtures:raise ValueError('ABI fixture binding')
  binary=child(artifacts,'android/'+abi+'/'+binary_name)
  with binary.open('rb') as stream:header=stream.read(64)
  if len(header)!=64 or header[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',header,18)[0]!=machine or digest(binary)!=receipt['binary_sha256']:raise ValueError('ELF identity')
  entries[abi]=binary
 return proof,expected,entries

def command(argv,log,timeout=60):
 with log.open('xb') as stream:
  p=subprocess.run(list(map(str,argv)),stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
 with log.open('rb') as stream:raw=stream.read(1024**2+1)
 if len(raw)>1024**2 or p.returncode:raise ValueError('device command failed; inspect '+log.name)
 return raw.decode().strip()

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--kind',choices=SPECS,required=True);ap.add_argument('--artifacts',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--source-root',type=Path,default=ROOT);ap.add_argument('--validate-only',action='store_true');ap.add_argument('--adb',type=Path);ap.add_argument('--serial');a=ap.parse_args()
 if not a.validate_only and (not a.adb or not a.serial):ap.error('explicit adb/serial required')
 if a.output.parent.exists() and any(a.output.parent.iterdir()):raise ValueError('fresh evidence directory required')
 a.output.parent.mkdir(parents=True,exist_ok=True)
 result=dict(schema='coh-raw-character-android-v1',kind=a.kind,passed=False,artifact_admitted=False,android_executed=False,native_execution_attempted=False,emulator_qualified=False,temporary_files_removed=False,actor_publication=False,acknowledgments_enabled=False,live_server=False,physical_thor=False,gpu_execution=False)
 owned=False;remote='/data/local/tmp/coh-raw-'+uuid.uuid4().hex;counter=0
 def adb(*args):
  nonlocal counter
  counter+=1
  return command([a.adb,'-s',a.serial,*args],a.output.parent/(str(counter)+'.log'),180)
 try:
  proof,expected,entries=admit(a.kind,a.artifacts.resolve(),a.source_root.resolve());result['artifact_admitted']=True
  if not a.validate_only:
   if not re.fullmatch('emulator-[0-9]+',a.serial):raise ValueError('explicit emulator required')
   if [adb('shell','getprop','ro.build.version.sdk'),adb('shell','getprop','ro.product.cpu.abi'),adb('shell','getprop','ro.kernel.qemu')]!=['33','x86_64','1']:raise ValueError('Android13 x86_64 emulator required')
   adb('shell','mkdir',remote);owned=True
   binary=entries['x86_64'];target=remote+'/'+binary.name
   adb('push',binary,target)
   if adb('shell','sha256sum',target).split()[0]!=digest(binary):raise ValueError('transferred binary differs')
   adb('shell','chmod','700',target)
   result['native_execution_attempted']=True
   observed=json.loads(adb('shell','timeout','-s','KILL','90',target));result['android_executed']=True;result['observed']=observed
   if json.dumps(observed,sort_keys=True)!=json.dumps(expected,sort_keys=True):raise ValueError('native Android result differs')
   admit(a.kind,a.artifacts.resolve(),a.source_root.resolve())
   adb('shell','rm','-rf',remote)
   adb('shell','test','!','-e',remote);owned=False
   result.update(emulator_qualified=True,temporary_files_removed=True)
  result['passed']=True
 except Exception as error:result['error']=str(error)
 finally:
  if owned:
   try:adb('shell','rm','-rf',remote);adb('shell','test','!','-e',remote);result['temporary_files_removed']=True
   except Exception:result['cleanup_error']='owned remote cleanup failed'
  a.output.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
