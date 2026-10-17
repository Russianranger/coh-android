#!/usr/bin/env python3
"""Bind original outer control ordering to native selected-record atomic spans."""
import argparse,hashlib,importlib.util,json,os,shutil,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--fixtures-output',type=Path);a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 old=json.loads((HERE/'qualification/20261017/host-proof.json').read_text());paths={ROOT/n for n in old['source_sha256']};paths.update(HERE/n for n in('check_outer.py','outer_fixtures.py','outer_components.py','test_outer.c','qualification/20261017/host-proof.json'))
 op=ROOT/'native-android/combined-client/diagnostics/selected-record-order-20261017';paths.update(op/n for n in('order_oracle.py','outer_adapters.h','outer_wrapper.h','leaf_oracle.py','leaf_adapters.h','leaf_wrapper.h','leaf-source-pins.json'));paths.add(ROOT/'native-android/engine/dbclient/check.py');hashes={str(p.resolve().relative_to(ROOT)):sha(p)for p in sorted(paths)}
 check=load('selected_record_frozen_check',HERE/'check.py');fixture=load('selected_record_outer_fixtures',HERE/'outer_fixtures.py');revision=check.run(['git','-C',ROOT,'rev-parse','HEAD']).strip()
 with tempfile.TemporaryDirectory(prefix='coh-selected-outer-')as tmp:
  work=Path(tmp);wire,proof=fixture.generate(work)
  if a.fixtures_output:
   if a.fixtures_output.exists():raise ValueError('new fixture output required')
   a.fixtures_output.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(wire,a.fixtures_output)
  modes=[('release',['-O2'])]
  if a.sanitize:modes += [('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
  checks={};binaries={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
  for mode,flags in modes:
   binary=work/mode;check.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*check.SOURCES,HERE/'test_outer.c','-lm','-o',binary]);checks[mode]=json.loads(check.run([binary,wire],env=env));binaries[mode]=sha(binary)
  if any(v!=checks['release']for v in checks.values()):raise ValueError('modes disagree')
  result={'schema':'coh-selected-record-original-outer-v1','passed':True,'source_revision':revision,'source_sha256':hashes,'fixtures':proof,'checks':checks,'binary_sha256':binaries,'original_oracle_sanitized':False,'whole_entity_list':False,'authentic_dictionary_generation':False,'full_initial_transaction':False,'actor_publication':False,'ack_permitted':False,'real_server_accepted':False,'android_built':False,'thor_accepted':False,'leak_sanitizer':False}
 if hashes!={str(p.resolve().relative_to(ROOT)):sha(p)for p in sorted(paths)}:raise ValueError('source inputs changed')
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('x')as out:json.dump(result,out,indent=2);out.write('\n')
 print(json.dumps({'passed':True,'checks':checks,'relocation_checks':proof['all_bit_offsets_child_payload_equality_checks']}))
if __name__=='__main__':main()
