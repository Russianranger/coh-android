#!/usr/bin/env python3
"""Focused new-role host qualification; never starts or rebuilds original Map."""
import argparse,hashlib,importlib.util,io,json,os,subprocess,tarfile,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
ARCHIVE=ROOT/'native-android/engine/scenecatalog-server/evidence/fresh-callback-profile-20261018/compile-initial-owner-20261018/fresh-map-initial-owner-build-39099315295.zip'
ARCHIVE_SHA='cd27cda26fae3bf5ab76889f82c2b467cc97423c260e69c997a62cff9756156b'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def need(ok):
 if not ok:raise ValueError('FOCUSED_OBSERVER_REFUSED')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
 local=('coh_server_initial_ledger.h','coh_server_initial_ledger.c','coh_server_initial_api.h','source_adapter.inc','sourcehooks.py','schema.py','fixtures.py','test_ledger.c','test_adapter.c','check_observer.py','CONTRACT.md')
 paths=[*(HERE/n for n in local),ARCHIVE,*(ROOT/'upstream/ouroboros'/n for n in ('MapServer/src/svr/svr_tick.c','MapServer/src/entity/entsend.c','MapServer/src/entity/entserver.c'))]
 raw={p:p.read_bytes()for p in paths};need(sha(raw[ARCHIVE])==ARCHIVE_SHA)
 hooks=module('focused_sio_hooks',HERE/'sourcehooks.py');schema=module('focused_sio_schema',HERE/'schema.py');controls=0
 def check(ok):
  nonlocal controls;need(ok);controls+=1
 def refuses(fn):
  try:fn()
  except (ValueError,TypeError,UnicodeError):return True
  return False
 with zipfile.ZipFile(io.BytesIO(raw[ARCHIVE]))as z:
  inputs={n:z.read('fresh-groups-compile/source/'+n)if n in(hooks.GROUP,hooks.PROFILE)else raw[ROOT/'upstream/ouroboros'/n]for n in hooks.PATCHED}
 patched=hooks.transform(inputs);check(hooks.reverse(patched)==inputs);check(len(hooks.overlays(ROOT))==4)
 crlf={n:hooks.lf(v).replace(b'\n',b'\r\n')for n,v in inputs.items()};pcr=hooks.transform(crlf);check(hooks.reverse(pcr)==crlf)
 for n in hooks.PATCHED:
  bad=dict(inputs);bad[n]+=b'\n';check(refuses(lambda:hooks.transform(bad)))
  bad=dict(patched);bad[n]+=b'\n';check(refuses(lambda:hooks.reverse(bad)))
  check(hooks.lf(pcr[n])==hooks.lf(patched[n]))
 check(refuses(lambda:hooks.transform({})));check(refuses(lambda:hooks.overlays(HERE)))
 # Exact reversal is the control-preservation test. These checks also pin the
 # handful of diagnostics' argument/lifetime and normalized-command seams.
 ch=hooks.lf(patched[hooks.CHAR]);ent=hooks.lf(patched[hooks.ENTS]);tick=hooks.lf(patched[hooks.TICK])
 check(b'e->client->link'not in b'\n'.join(l for l in ch.splitlines()if b'SIO' in l))
 check(ent.count(b'coh_sio_result = pktSend(&e->entityPacket,client->link);')==1)
 check(b'uintptr_t coh_sio_packet = (uintptr_t)e->entityPacket;'in ent)
 check(ent.count(b'clientGetViewedEntity(')==hooks.lf(inputs[hooks.ENTS]).count(b'clientGetViewedEntity('))
 check(tick.count(b'clientGetViewedEntity(client)')==hooks.lf(inputs[hooks.TICK]).count(b'clientGetViewedEntity(client)'))
 check(ch.index(b'coh_sio_source_retire_entity(ent)')<ch.index(b'if (!ent || ent->owner <= 0)'))
 compiler=subprocess.run(['cc','--version'],check=True,capture_output=True).stdout;(out/'compiler-version.txt').write_bytes(compiler)
 runs=[];elves={};modes=[('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
 for mode,flags in modes:
  for role,sources,expected in [('ledger',[HERE/'coh_server_initial_ledger.c',HERE/'test_ledger.c'],105),('adapter',[HERE/'test_adapter.c'],5030)]:
   binary=out/(mode+'-'+role);cmd=['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*map(str,sources),'-o',str(binary)]
   built=subprocess.run(cmd,capture_output=True);(out/(mode+'-'+role+'-compile.stdout')).write_bytes(built.stdout);(out/(mode+'-'+role+'-compile.stderr')).write_bytes(built.stderr);need(built.returncode==0)
   env=dict(os.environ);env['ASAN_OPTIONS']='detect_leaks=0:abort_on_error=1';ran=subprocess.run([str(binary)],capture_output=True,env=env);(out/(mode+'-'+role+'.stdout')).write_bytes(ran.stdout);(out/(mode+'-'+role+'.stderr')).write_bytes(ran.stderr);need(ran.returncode==0 and not ran.stderr)
   check(('checks='+str(expected)).encode()in ran.stdout)
   snapshots=[]
   for line in ran.stdout.splitlines():
    if line.startswith((b'SNAPSHOT ',b'ADAPTER_SNAPSHOT ')):
     value=schema.parse(line.split(b' ',1)[1]);snapshots.append(value);check(all(value[k]is False for k in schema.FALSE))
   check(len(snapshots)==(4 if role=='ledger'else 1))
   for value in snapshots:
    for name in schema.FALSE:
     bad=dict(value);bad[name]=True;check(refuses(lambda:schema.parse(json.dumps(bad).encode())))
   value=snapshots[0]
   for bad in [dict(value,private_packet_id=1),dict(value,valid=1),dict(value,tick_seen=-1),dict(value,stage=21),dict(value,pkt_send_result=2),dict(value,refusal='PRIVATE')]:check(refuses(lambda:schema.parse(json.dumps(bad).encode())))
   encoded=json.dumps(value).encode();check(refuses(lambda:schema.parse(encoded[:-1]+b',"valid":true}')));check(refuses(lambda:schema.parse(b'x'*4097)))
   elves[mode+'-'+role]=binary.read_bytes();binary.unlink();runs.append({'mode':mode,'role':role,'checks':expected,'returncode':ran.returncode,'stdout_sha256':sha(ran.stdout),'stderr_bytes':0,'elf_sha256':sha(elves[mode+'-'+role]),'elf_bytes':len(elves[mode+'-'+role]),'snapshot_count':len(snapshots),'compiler_argv':cmd})
 need(all(p.read_bytes()==v for p,v in raw.items()))
 tar=io.BytesIO()
 with tarfile.open(fileobj=tar,mode='w:gz')as archive:
  for name,elf in elves.items():
   member=tarfile.TarInfo(name);member.size=len(elf);member.mtime=0;archive.addfile(member,io.BytesIO(elf))
 packed=tar.getvalue();(out/'executed-host-elfs.tar.gz').write_bytes(packed)
 proof={'schema':'coh-server-initial-observer-host-v1','passed':True,'scope':'portable ledger plus actual source adapter with explicit synthetic Map and Win32 providers; exact source recipe over accepted GROUPS source and original three TUs','source_sha256':{str(p.relative_to(ROOT)):sha(v)for p,v in raw.items()},'source_bracket_unchanged':True,'exact_reverse_files':len(inputs),'new_overlays':len(hooks.overlays(ROOT)),'recipe_and_schema_controls':controls,'runs':runs,'retained_elf_archive':{'bytes':len(packed),'sha256':sha(packed),'members':len(elves)},'original_map_executed':False,'windows_kernel_executed':False,'original_packet_serializers_executed':False,'full_compiler_system_header_closure_claimed':False,'leak_sanitizer_enabled':False,'leak_sanitizer_reason':'managed host refuses proc task traversal; core/adapter allocate no memory; address and undefined checks remain enabled','private_identity_exported':False,'packet_queue_acceptance_established':False,'socket_send_established':False,'world_authority':False}
 (out/'qualification.json').write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n');print(json.dumps({'passed':True,'focused_checks_per_mode':5135,'recipe_schema_controls':controls,'exact_reverse_files':5,'elfs_retained':6}))
if __name__=='__main__':main()
