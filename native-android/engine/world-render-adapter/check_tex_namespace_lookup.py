#!/usr/bin/env python3
"""New-only source texFind integration over a real finite namespace provider."""
import argparse,hashlib,importlib.util,json,os,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
LOCAL=['coh_wr_tex_namespace_lookup.c','coh_wr_tex_namespace_lookup.h','tex_namespace_lookup_oracle.py','check_tex_namespace_lookup.py','tests/test_tex_namespace_lookup.c','tests/test_tex_namespace_lookup.cpp','TEX_NAMESPACE_LOOKUP.md']
CORE=[HERE/'coh_wr_tex_namespace.c',HERE.parent/'assets/coh_asset_loader.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
HELPERS=['check_texname.py','texname_guard_candidate.py','check_tex_defaults.py']
DEPS=list(dict.fromkeys([HERE/x for x in LOCAL+HELPERS]+CORE+[HERE/'coh_wr_tex_namespace.h',HERE/'coh_wr_tex_defaults.h',HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/src/byte_reader.h',ROOT/'upstream/ouroboros/Game/src/render/tex.c',ROOT/'upstream/ouroboros/Game/src/render/tex.h']))
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--actual-defaults-zip',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 if args.output.exists():raise ValueError('fresh output directory required')
 pins={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in DEPS};revision=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip()
 def readmit():
  if pins!={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in DEPS}:raise ValueError('source changed')
 def load(name,path):
  readmit();spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__);return module
 original_helpers=load('namespace_lookup_extract',HERE/'check_texname.py');repair_helpers=load('namespace_lookup_guard',HERE/'texname_guard_candidate.py');defaults=load('namespace_lookup_bodies',HERE/'check_tex_defaults.py');oracle=load('namespace_lookup_oracle',HERE/'tex_namespace_lookup_oracle.py')
 bodies=defaults.actual(args.actual_defaults_zip);code,repair,blocks=oracle.create(ROOT,original_helpers.extract,repair_helpers.patch)
 args.output.mkdir(parents=True);directory=args.output.resolve();sequence=0
 def run(command,**kwargs):
  nonlocal sequence
  sequence+=1;command=list(map(str,command));readmit()
  with (directory/'commands.jsonl').open('a') as stream:stream.write(json.dumps({'index':sequence,'argv':command})+'\n')
  result=subprocess.run(command,capture_output=True,timeout=120,**kwargs);(directory/('%03d.stdout'%sequence)).write_bytes(result.stdout);(directory/('%03d.stderr'%sequence)).write_bytes(result.stderr)
  if result.returncode:raise ValueError('focused namespace lookup command failed '+str(sequence))
  return result.stdout
 try:
  (directory/'original.c').write_text(code);fixture='#include <stdint.h>\n#include <stddef.h>\n'
  for i,(_,body) in enumerate(bodies):fixture+='static const uint8_t actual_body_'+str(i)+'[]={'+','.join(map(str,body))+'};\n'
  fixture+='typedef struct{const char*path;const uint8_t*data;size_t size;} DefaultsActual;\nstatic const DefaultsActual actual_defaults[]={\n'+''.join('{'+json.dumps(path)+',actual_body_'+str(i)+','+str(len(body))+'},\n' for i,(path,body) in enumerate(bodies))+'};\n';(directory/'defaults_actual.h').write_text(fixture)
  common=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-I',directory,'-I',HERE,'-I',ROOT/'native-android/include'];compiler=run(['cc','--version']).decode().splitlines()[0]
  original=directory/'original.o';run([*common,'-O2','-c',directory/'original.c','-o',original]);modes={};binaries={};release_objects=[];dependencies=set()
  for mode,flags in [('release',['-O2']),('address',['-O1','-fsanitize=address','-no-pie']),('undefined',['-O1','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   objects=[]
   for i,path in enumerate([HERE/'coh_wr_tex_namespace_lookup.c',HERE/'tests/test_tex_namespace_lookup.c',*CORE]):
    obj=directory/(mode+'-'+str(i)+'.o');run([*common,*flags,'-fstack-usage','-c',path,'-o',obj]);objects.append(obj)
    if mode=='release':
     dep=run([*common,'-MM',path]).decode().replace('\\\n',' ')
     for token in dep.split(':',1)[1].split():
      candidate=Path(token).resolve()
      if candidate.is_relative_to(ROOT):dependencies.add(str(candidate.relative_to(ROOT)))
   if mode=='release':release_objects=objects
   binary=directory/mode;run(['cc',*flags,*objects,original,'-Wl,--wrap=calloc','-Wl,--wrap=free','-lcrypto','-lz','-lm','-o',binary]);digest=sha(binary.read_bytes());modes[mode]=json.loads(run([binary],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
   if sha(binary.read_bytes())!=digest:raise ValueError('binary changed')
   binaries[mode]=digest
  if dependencies-set(pins):raise ValueError('unadmitted compile dependencies '+str(sorted(dependencies-set(pins))))
  # Link an actual C object and call it from C++, with a small separate allocator
  # wrapper because the finite-provider test executable owns its own wrappers.
  wrappers=directory/'cpp-wrappers.c';wrappers.write_text('#include <stdlib.h>\nvoid*__real_calloc(size_t,size_t);void __real_free(void*);void*__wrap_calloc(size_t n,size_t s){return __real_calloc(n,s);}void __wrap_free(void*p){__real_free(p);}\n');wrapper_obj=directory/'cpp-wrappers.o';run([*common,'-O2','-c',wrappers,'-o',wrapper_obj])
  cpp=directory/'cpp';run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-pedantic',HERE/'tests/test_tex_namespace_lookup.cpp',release_objects[0],*release_objects[2:],wrapper_obj,'-Wl,--wrap=calloc','-Wl,--wrap=free','-lz','-lm','-o',cpp]);run([cpp])
  source=(HERE/'coh_wr_tex_namespace_lookup.c').read_text();mutations=[]
  for label,before,after in [('repeat_bang',"if(query[0]=='!'){query++;n--;}","while(query[0]=='!'){query++;n--;}"),('dds_format','else if(!strcmp(extension,"dds"))value.format_flags=1u<<6','else if(!strcmp(extension,"dds"))value.format_flags=1u<<5'),('omit_full_reservation','total<report.aggregate_reserved_bytes','0'),('drop_guarded_short_domain','if(!limits->guarded_short_keys)return COH_UNSUPPORTED;','if(0)return COH_UNSUPPORTED;')]:
   if source.count(before)!=1:raise ValueError('mutation preimage differs '+label)
   changed=directory/(label+'.c');changed.write_text(source.replace(before,after));obj=directory/(label+'.o');run([*common,'-O2','-c',changed,'-o',obj]);binary=directory/label;run(['cc',obj,*release_objects[1:],original,'-Wl,--wrap=calloc','-Wl,--wrap=free','-lcrypto','-lz','-lm','-o',binary]);sequence+=1;result=subprocess.run([str(binary)],capture_output=True,timeout=120);(directory/('%03d.mutation-stdout'%sequence)).write_bytes(result.stdout);(directory/('%03d.mutation-stderr'%sequence)).write_bytes(result.stderr)
   if result.returncode==0:raise ValueError('semantic mutation escaped '+label)
   mutations.append(label)
  stack=release_objects[0].with_suffix('.su').read_text().splitlines();frames=[]
  for line in stack:
   parts=line.split('\t')
   if len(parts)!=3 or ('dynamic' in parts[2] and 'bounded' not in parts[2]):raise ValueError('unbounded lookup stack')
   frames.append(int(parts[1]))
  if sum(frames)>16384:raise ValueError('lookup control reserve too small')
  readmit()
  if defaults.actual(args.actual_defaults_zip)!=bodies:raise ValueError('source body readmission differs')
  proof={'passed':True,'source_base_revision':revision,'source_sha256':pins,'compiled_repo_dependencies':sorted(dependencies),'compiler':compiler,'modes':modes,'binary_sha256':binaries,'actual_C_object_CPP_call_link':{'passed':True,'binary_sha256':sha(cpp.read_bytes())},'whole_original_blocks_sha256':{k:sha(v.encode()) for k,v in blocks.items()},'explicit_short_key_repair':repair,'original_oracle_sha256':sha(code.encode()),'source_artifact':{'run':39078874753,'artifact':12118720382,'bytes':args.actual_defaults_zip.stat().st_size,'sha256':sha(args.actual_defaults_zip.read_bytes()),'bodies':[{'path':p,'bytes':len(b),'sha256':sha(b)} for p,b in bodies]},'semantic_mutations_refused':mutations,'release_stack_usage':stack,'conservative_own_frame_sum':sum(frames),'control_reserve':16384,'real_native_namespace_provider':True,'complete_finite_provider_only':True,'original_current_CLIENT_provider':False,'source_effective_alpha':False,'default_material_world_authority':False,'Android_execution':False,'old_qualifiers_rerun':False,'LeakSanitizer_executed':False,'source_base_is_not_claimed_as_new_file_commit':True}
  (directory/'host.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'modes':modes}))
 except BaseException:
  (directory/'FAILED.json').write_text(json.dumps({'passed':False,'last_command_index':sequence,'all_outputs_preserved':True,'source_sha256':pins})+'\n');raise
if __name__=='__main__':main()
