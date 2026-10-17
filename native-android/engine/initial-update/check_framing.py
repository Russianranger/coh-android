#!/usr/bin/env python3
"""Native comparison against the exact retained F original framing corpus."""
import argparse,gzip,hashlib,json,os,struct,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,**kw)
 if p.returncode:raise RuntimeError(str(args)+'\n'+p.stdout+p.stderr)
 return p.stdout
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 provider=ROOT/'native-android/combined-client/diagnostics/trailing-command-20261017';binding=json.loads((provider/'source-binding.json').read_text());compressed=provider/'host-proof.json.gz'
 if sha(compressed)!='ab8d0fb33fc19a97de033e82134f1ffb28b737868426181e79883520966c9cbf' or sha(compressed)!=binding['host_proof_gzip_sha256']:raise ValueError('original retained corpus mismatch')
 raw=gzip.decompress(compressed.read_bytes())
 if hashlib.sha256(raw).hexdigest()!=binding['host_proof_raw_sha256']:raise ValueError('original raw corpus mismatch')
 proof=json.loads(raw)
 if any(sha(ROOT/p)!=h for p,h in proof['source_sha256'].items()):raise ValueError('original framing source changed')
 whole=json.loads(gzip.decompress((HERE/'qualification/20261017/host-proof.json.gz').read_bytes()))
 if any(sha(ROOT/p)!=h for p,h in whole['source_sha256'].items()):raise ValueError('whole owner frozen source changed')
 paths={ROOT/p for p in whole['source_sha256']}|{ROOT/p for p in proof['source_sha256']}|{HERE/n for n in('coh_initial_update.c','coh_initial_update.h','test_framing.c','check_framing.py')}|{HERE/'../replication/coh_replication.c',HERE/'../replication/coh_replication.h',HERE/'../coh_contracts.h',compressed,provider/'source-binding.json'}
 hashes={str(p.resolve().relative_to(ROOT)):sha(p)for p in sorted(paths)};checks={};binaries={}
 with tempfile.TemporaryDirectory(prefix='coh-initial-framing-')as tmp:
  work=Path(tmp);fixtures=work/'fixtures.bin'
  with fixtures.open('xb')as f:
   f.write(struct.pack('<I',len(proof['cases'])))
   for c in proof['cases']:
    wire=bytes.fromhex(c['wire_hex']);f.write(struct.pack('<5I',len(wire),c['bits'],c['begin'],c['aligned'],c['markers']+c['meta']));f.write(wire)
  for mode,flags in [('release',['-O2'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]):
   binary=work/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-ffunction-sections','-fdata-sections',*flags,HERE/'test_framing.c',HERE/'../replication/coh_replication.c','-Wl,--gc-sections','-lm','-o',binary]);checks[mode]=json.loads(run([binary,fixtures],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(binary)
  if any(x!=checks['release']for x in checks.values()):raise ValueError('mode results differ')
 if hashes!={str(p.resolve().relative_to(ROOT)):sha(p)for p in sorted(paths)}:raise ValueError('source changed')
 result={'schema':'coh-native-original-trailing-framing-v1','passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).strip(),'source_sha256':hashes,'checks':checks,'binary_sha256':binaries,'original_source_commit':binding['source_commit'],'original_source_corpus_checks':proof['checks'],'native_private_function_exact_source':'coh_initial_update.c:command_tail','native_local_bound_includes_end_command':True,'old_whole_initial_qualification_replayed':False,'whole_original_dispatcher_executed':False,'original_early_ack_executed':False,'original_oracle_sanitized':False,'actor_publication':False,'ack_permitted':False,'android_executed':False,'real_server_accepted':False}
 with a.output.open('x')as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({'passed':True,'checks':checks}))
if __name__=='__main__':main()
