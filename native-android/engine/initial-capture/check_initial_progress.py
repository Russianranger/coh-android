#!/usr/bin/env python3
"""New scalar receiver-progress role only; no prior qualification entrypoint."""
from pathlib import Path
import argparse
import ast
import gzip
import hashlib
import json
import os
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
NATIVE=ROOT/'native-android'
ROLE=NATIVE/'combined-client/tools/capture_local_initial_progress.c'
LEGACY=NATIVE/'combined-client/tools/capture_local_initial.c'
RECIPE=NATIVE/'combined-client/tools/check_local_initial_capture.py'
BEGIN='/* BEGIN EXACT LEGACY ROLE WITH FOUR REVERSIBLE IDENTIFIER EDITS */\n'
END='/* END EXACT LEGACY ROLE */\n'
FLAGS=['-std=c11','-Wall','-Wextra','-Werror','-fstack-usage']


def sha(raw):return hashlib.sha256(raw).hexdigest()
def need(value,reason):
 if not value:raise ValueError('COH_INITIAL_PROGRESS_'+reason)


def recipe():
 # Read only the already accepted source-list literal; never import or execute
 # any old qualifier, fixture producer or test entrypoint.
 tree=ast.parse(RECIPE.read_bytes())
 values=[ast.literal_eval(node.value)for node in tree.body if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='RELATIVE'for t in node.targets)]
 need(len(values)==1 and isinstance(values[0],list),'SOURCE_RECIPE');return[NATIVE/name for name in values[0]]


def preservation():
 text=ROLE.read_text();need(text.count(BEGIN)==text.count(END)==1,'ROLE_MARKERS');body=text.split(BEGIN,1)[1].split(END,1)[0]
 pairs=[('int coh_initial_progress_legacy_main(int argc,char **argv) {','int main(int argc,char **argv) {'),('status=progress_begin(owner,','status=coh_initial_capture_begin(owner,'),('status=progress_service(owner,','status=coh_initial_capture_service(owner,'),('progress_destroy(owner);','coh_initial_capture_destroy(owner);'),('    if(success&&out.groups.directory>=0)progress_write(out.groups.directory);\n','')]
 for changed,old in pairs:need(body.count(changed)==1,'REVERSIBLE_EDIT_UNIQUE');body=body.replace(changed,old)
 need(body.encode()==LEGACY.read_bytes(),'EXACT_LEGACY_SOURCE_PRESERVATION')
 return{'legacy_sha256':sha(LEGACY.read_bytes()),'current_role_sha256':sha(ROLE.read_bytes()),'five_reversible_identifier_or_call_edits_only':True,'protocol_deadline_main_loop_and_original_call_order_unchanged':True,'extra_private_report_written_only_after_legacy_capture_success_before_owned_FD_close':True}


def dependencies(sources):
 p=subprocess.run(['cc',*FLAGS,'-I'+str(NATIVE/'include'),'-MM',*[str(s)for s in sources]],capture_output=True,timeout=60)
 need(p.returncode==0 and not p.stderr,'DEPENDENCIES');found={ROLE,LEGACY,RECIPE,Path(__file__).resolve(),HERE/'INITIAL_PROGRESS.md'}
 for line in p.stdout.decode().replace('\\\n',' ').splitlines():
  need(':'in line,'DEPENDENCY_FORMAT')
  for name in line.split(':',1)[1].split():
   path=Path(name).resolve();need(path.is_relative_to(ROOT),'PROJECT_DEPENDENCY');found.add(path)
 return{str(path.relative_to(ROOT)):sha(path.read_bytes())for path in sorted(found)}


def qualify(output):
 output.mkdir(parents=True,exist_ok=False);sources=recipe();transition=preservation();pins=dependencies([ROLE,*sources,HERE/'test_initial_progress.c']);modes={}
 env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'}
 def run(label,command,expected=0):
  p=subprocess.run(list(map(str,command)),capture_output=True,timeout=60,env=env)
  (output/(label+'.stdout')).write_bytes(p.stdout);(output/(label+'.stderr')).write_bytes(p.stderr)
  need(p.returncode==expected,'COMMAND_'+label);return p
 with tempfile.TemporaryDirectory(prefix='coh-initial-progress-')as tmp:
  work=Path(tmp)
  for mode,options in(('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])):
   directory=work/mode;directory.mkdir();flags=[*FLAGS,*options,'-I'+str(NATIVE/'include')]
   unit=directory/'unit';run(mode+'-unit-build',['cc',*flags,'-Wno-unused-function',HERE/'test_initial_progress.c','-Wl,--wrap=sendto','-o',unit]);result=json.loads(run(mode+'-unit',[unit]).stdout)
   need(result['passed']and result['checks']==129 and result['actual_loopback_datagrams']==2 and result['actual_send_error_errno_preserved'],'FOCUSED_NATIVE_RESULT')
   objects=[]
   for index,source in enumerate(sources):
    target=directory/(str(index)+'.o');original=['-O0']if source.name in('coh_protocol.c','coh_blowfish.c')else[]
    run(mode+'-object-'+str(index),['cc',*flags,*original,'-c',source,'-o',target]);objects.append(target)
   binary=directory/'coh-capture-initial-progress';run(mode+'-role-build',['cc',*flags,ROLE,*objects,'-Wl,--wrap=sendto','-lz','-lm','-lcrypto','-o',binary]);noargs=run(mode+'-role-noargs',[binary],2);need(not noargs.stdout and not noargs.stderr,'UNCHANGED_NOARGS')
   frames=[]
   for file in directory.glob('*.su'):
    for line in file.read_text().splitlines():
     location,size,kind=line.split('\t');need('unbounded'not in kind,'UNBOUNDED_STACK');frames.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'kind':kind})
   need(frames and max(row['bytes']for row in frames)<512*1024,'EXISTING_CONTROL_STACK_BOUND')
   modes[mode]={'focused_unit':result,'unit_sha256':sha(unit.read_bytes()),'production_role_sha256':sha(binary.read_bytes()),'production_role_bytes':binary.stat().st_size,'production_role_noargs_unchanged':True,'maximum_static_frame_bytes':max(row['bytes']for row in frames),'source_specific_original_O0': ['coh_protocol.c','coh_blowfish.c'],'flags':flags}
   if mode=='release':
    blob=gzip.compress(binary.read_bytes(),mtime=0);(output/'coh-capture-initial-progress.gz').write_bytes(blob);modes[mode]['retained_binary_gzip_sha256']=sha(blob)
 need(pins=={name:sha((ROOT/name).read_bytes())for name in pins},'SOURCE_CHANGED')
 proof={'schema':'coh-initial-progress-focused-v1','passed':True,'source_revision':subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip(),'source_sha256':pins,'transition':transition,'modes':modes,'old_qualifier_or_fixture_entrypoints_executed':False,'original_server_executed':False,'actual_source_protocol_session_executed':False,'link_wrapped_actual_sendto_executed':True,'unit_service_begin_and_diagnostics_explicit_doubles':True,'default_network_map_local_initial_sources_changed':False,'new_observer_static_bytes':112,'fixed_report_max_bytes':1024,'complete_global_aggregate_or_RSS_fit':False,'command_specific_emission_proved':False,'server_receipt_proved':False,'source_generation_admitted':False,'actor_publication':False,'ack_permitted':False,'world_authority':False,'leak_sanitizer_enabled':False,'retained_binary_scope':'release new diagnostic role only; ASAN/UBSAN role and unit binaries temporary'}
 (output/'qualification.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'source_pins':len(pins),'modes':{mode:value['focused_unit']for mode,value in modes.items()}}))


if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();qualify(args.output)
