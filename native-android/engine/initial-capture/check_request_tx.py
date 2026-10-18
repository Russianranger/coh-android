#!/usr/bin/env python3
"""Qualify only the new bounded request-Tx witness; no old suite or server runs."""
from pathlib import Path
import argparse,ast,gzip,hashlib,io,json,os,re,shlex,subprocess,tarfile,tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];NATIVE=ROOT/'native-android'
RECIPE=NATIVE/'combined-client/tools/check_local_initial_capture.py'
def need(ok,code):
 if not ok:raise ValueError('REQUEST_TX_'+code)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def sources():
 tree=ast.parse(RECIPE.read_bytes());rows=[ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='RELATIVE'for t in n.targets)];need(len(rows)==1,'RECIPE')
 replace={'engine/initial-capture/coh_initial_map.c':'engine/initial-capture/coh_request_tx_map.c','engine/network/coh_net.c':'engine/initial-capture/coh_request_tx_net.c','engine/network/coh_net_udp.c':'engine/initial-capture/coh_request_tx_udp.c'}
 return[NATIVE/replace.get(name,name)for name in rows[0]]+[HERE/'coh_request_tx.c']
def preservation():
 result={}
 for role,original in [('map','engine/initial-capture/coh_initial_map.c'),('net','engine/network/coh_net.c'),('udp','engine/network/coh_net_udp.c')]:
  target=HERE/('coh_request_tx_'+role+'.c');text=target.read_text();hooks=text.count('/* REQUEST_TX_HOOK_BEGIN */');need(hooks==text.count('/* REQUEST_TX_HOOK_END */'),'MARKERS')
  # Exactly one whole extra line in the queue loop; all other insertions are
  # inline or include their own newline inside a marked insertion.
  if role=='net':text,count=re.subn(r'\n        /\* REQUEST_TX_HOOK_BEGIN \*/coh_request_tx_hook_queue\([^\n]*?/\* REQUEST_TX_HOOK_END \*/','',text);need(count==1,'QUEUE_LINE')
  text=re.sub(r'/\* REQUEST_TX_HOOK_BEGIN \*/.*?/\* REQUEST_TX_HOOK_END \*/','',text,flags=re.S)
  text=text.replace('#include "../network/coh_net.h"','#include "coh_net.h"').replace('#include "../network/coh_net_zip_internal.h"','#include "coh_net_zip_internal.h"').replace('#include "../network/coh_net_udp.h"','#include "coh_net_udp.h"')
  need(text.encode()==(NATIVE/original).read_bytes(),'BYTE_EXACT_'+role.upper())
  result[role]={'original_path':'native-android/'+original,'original_sha256':sha(text.encode()),'replacement_sha256':sha(target.read_bytes()),'marked_insertions':hooks,'exact_original_bytes_after_marker_and_include_reversal':True}
 return result
def qualify(output):
 output.mkdir(parents=True,exist_ok=False);production=sources();unit=[HERE/'test_request_tx.c',HERE/'coh_request_tx.c',HERE/'coh_request_tx_net.c',NATIVE/'engine/network/coh_net_frame.c',NATIVE/'engine/network/coh_net_zip.c',NATIVE/'protocol/coh_protocol.c',NATIVE/'src/coh_blowfish.c'];transition=preservation()
 deps=set(production+unit+[Path(__file__).resolve(),RECIPE,HERE/'REQUEST_TX.md']+[NATIVE/value['original_path'].removeprefix('native-android/')for value in transition.values()])
 query=subprocess.run(['cc','-std=c11','-MM','-I'+str(NATIVE/'include'),*[str(p)for p in production+unit]],capture_output=True,check=True,timeout=60);need(not query.stderr and len(query.stdout)<1024**2,'DEPENDENCIES')
 for line in query.stdout.decode().replace('\\\n',' ').splitlines():
  fields=shlex.split(line);need(fields and fields[0].endswith(':'),'DEPENDENCIES')
  for name in fields[1:]:
   path=Path(name).resolve();need(ROOT in path.parents,'DEPENDENCY_ROOT');deps.add(path)
 pins={str(path.relative_to(ROOT)):sha(path.read_bytes())for path in sorted(deps)};modes={};executed={}
 with tempfile.TemporaryDirectory(prefix='coh-request-tx-host-')as temporary:
  work=Path(temporary)
  def run(label,command,env=None):
   result=subprocess.run([str(x)for x in command],capture_output=True,timeout=120,env=env);(output/(label+'.stdout')).write_bytes(result.stdout);(output/(label+'.stderr')).write_bytes(result.stderr);need(result.returncode==0,label);return result
  for mode,options in [('release',['-O2']),('asan',['-O1','-fsanitize=address','-fno-omit-frame-pointer']),('ubsan',['-O1','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   directory=work/mode;directory.mkdir();flags=['-std=c11','-Wall','-Wextra','-Werror','-fPIC','-fstack-usage',*options,'-I'+str(NATIVE/'include')]
   def compile_set(label,inputs):
    objects=[]
    for index,source in enumerate(inputs):
     target=directory/(label+str(index)+'.o');original=['-O0']if source.name in('coh_protocol.c','coh_blowfish.c')else[];run(mode+'-'+label+'-'+str(index),['cc',*flags,*original,'-c',source,'-o',target]);objects.append(target)
    return objects
   objects=compile_set('unit',unit);binary=directory/'test-request-tx';run(mode+'-unit-link',['cc',*flags,*objects,'-lz','-o',binary]);environment=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:abort_on_error=1',UBSAN_OPTIONS='halt_on_error=1');actual=json.loads(run(mode+'-unit',[binary],environment).stdout);need(actual.get('passed')is True and actual.get('real_request_datagrams')==2 and actual.get('actual_sendto_io_failures')==1,'FOCUSED_RESULT');executed[mode]=binary.read_bytes()
   objects=compile_set('production',production);library=directory/'libcoh-request-tx.so';run(mode+'-production-link',['cc',*flags,'-shared','-Wl,--no-undefined',*objects,'-lz','-lm','-lcrypto','-o',library]);frames=[]
   for path in directory.glob('*.su'):
    for line in path.read_text().splitlines():
     _,size,kind=line.split('\t');need('unbounded'not in kind,'STACK');frames.append(int(size))
   need(frames and max(frames)<512*1024,'STATIC_STACK')
   modes[mode]={'focused_unit':actual,'executed_unit_bytes':len(executed[mode]),'executed_unit_sha256':sha(executed[mode]),'production_shared_role_bytes':library.stat().st_size,'production_shared_role_sha256':sha(library.read_bytes()),'production_shared_role_executed':False,'maximum_static_frame_bytes':max(frames),'original_source_specific_O0':['coh_protocol.c','coh_blowfish.c']}
 archive=io.BytesIO()
 with tarfile.open(fileobj=archive,mode='w')as tar:
  for mode,raw in executed.items():
   info=tarfile.TarInfo(mode+'/test-request-tx');info.size=len(raw);info.mode=0o700;info.mtime=0;tar.addfile(info,io.BytesIO(raw))
 retained=gzip.compress(archive.getvalue(),mtime=0);(output/'executed-unit-elfs.tar.gz').write_bytes(retained);need(pins=={name:sha((ROOT/name).read_bytes())for name in pins},'SOURCE_CHANGED')
 proof={'schema':'coh-request-tx-focused-v1','passed':True,'source_revision_context':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_sha256':pins,'transition':transition,'modes':modes,'executed_unit_archive_bytes':len(retained),'executed_unit_archive_sha256':sha(retained),'witness_allocation_max_bytes':256,'public_output_has_no_packet_identity_or_pointer':True,'outer_capture_and_request_bracket_explicit_doubles':True,'actual_loopback_UDP_and_sendto_error_executed':True,'original_qualifiers_or_fixtures_replayed':False,'production_role_or_original_server_or_actual_source_session_executed':False,'frozen_default_or_diagnostic_sources_changed':False,'complete_global_aggregate_or_RSS_fit':False,'leak_sanitizer_enabled':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False}
 (output/'qualification.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'source_pins':len(pins),'modes':{key:value['focused_unit']for key,value in modes.items()}}))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();qualify(args.output)
