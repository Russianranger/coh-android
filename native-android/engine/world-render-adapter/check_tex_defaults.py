#!/usr/bin/env python3
"""New-only cold default-owner qualification; never an original CLIENT namespace witness."""
import argparse,hashlib,importlib.util,io,json,os,subprocess,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
ARCHIVE_SHA='87a999e6c1c003b96a9fa169ce11637b61eb696766517e063fafce73fdc39c24'
BODY_PINS=[
 ('white.texture',327,'682b26a6f55fcf2d9ebc47cde781f64fc18ee50c78f25720f0857e6ca1fca7f9'),
 ('grey.texture',894,'b628966e91a864f9edcb0634605823a7ef3d8e2305f36d1a9f6e9834b018a013'),
 ('invisible.texture',5828,'7a0e37f76eba451debca99f50f2907e556dba55dbb45468a415d55b480b103df'),
 ('black.texture',327,'62c947f06b7ca5c08e0e9bda98d4ae3d72aa5c7dab4557ae87ff4b48f1764f5a'),
 ('dummy_bump.texture',437,'021f8a4ccfdb334f9ec336a8275b336890440bf8700ef593b7cd9d4ca374ee3d'),
 ('dummy_dynamic_cubemap_face0.texture',302,'cd06cf02ffa62c7e5a35d39e5d5d06632c970382640645304584c19ddb70b4f6'),
 ('buildinglightpattern.texture',8399,'c2996a5d0b402dba4ee2722797fdc486e48bc773e99761b659b0c1219aecaa06'),
]
LOCAL=['coh_wr_tex_defaults.c','coh_wr_tex_defaults.h','tex_defaults_oracle.py','check_tex_defaults.py','TEX_DEFAULTS.md','tests/test_tex_defaults.c','tests/test_tex_defaults_cpp.cpp','tests/tex_defaults_fixture.h','coh_wr_tex_namespace.c','coh_wr_tex_namespace.h']
CORE=[HERE/'coh_wr_tex_namespace.c',HERE.parent/'assets/coh_asset_loader.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
DEPS=list(dict.fromkeys([HERE/x for x in LOCAL]+CORE+[HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/src/byte_reader.h',ROOT/'upstream/ouroboros/Game/src/render/tex.c',ROOT/'upstream/ouroboros/Game/src/render/tex.h']))
def sha(b):return hashlib.sha256(b).hexdigest()
def admitted(pins,revision):
 for p in DEPS:
  rel=str(p.relative_to(ROOT));b=p.read_bytes()
  if sha(b)!=pins[rel] or b!=subprocess.check_output(['git','-C',str(ROOT),'show',revision+':'+rel]):raise ValueError('current/Git source differs '+rel)
def actual(path):
 with path.open('rb') as stream:b=stream.read(12309)
 if len(b)!=12308 or sha(b)!=ARCHIVE_SHA:raise ValueError('exact retained source artifact differs')
 with zipfile.ZipFile(io.BytesIO(b)) as z:
  if z.testzip() is not None:raise ValueError('artifact CRC differs')
  manifest=z.read('fresh-default-headers/manifest.json');report=z.read('default-headers.json')
  if sha(manifest)!='1fe575013883344e4ce9f04d83739356e5605f9d6caf7e8190385f420ea5e2c5' or sha(report)!='ab1cf2773b540061c62fd9b42e3ca5f6d58e191805b8a35c8dbf0a06646789a5':raise ValueError('original admission receipt differs')
  rows=json.loads(manifest)['files'];by_name={r['filename']:r for r in rows}
  names={'default-headers.json','fresh-default-headers/manifest.json'}|{'fresh-default-headers/'+p[0] for p in BODY_PINS}
  if len(rows)!=7 or len(z.namelist())!=9 or set(z.namelist())!=names:raise ValueError('fixed seven-body inventory differs')
  bodies=[]
  for name,size,digest in BODY_PINS:
   body=z.read('fresh-default-headers/'+name);row=by_name[name]
   if len(body)!=size or sha(body)!=digest or not row['virtual_asset_path'].startswith('data/texture_library/'):raise ValueError('exact body identity differs')
   bodies.append((row['virtual_asset_path'][5:],body))
  return bodies
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--actual-defaults-zip',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('fresh output directory required')
 revision=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip()
 pins={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in DEPS};admitted(pins,revision)
 bodies=actual(a.actual_defaults_zip);a.output.mkdir(parents=True);d=a.output.resolve()
 sequence=0
 def run(command,**kwargs):
  nonlocal sequence
  sequence+=1;command=list(map(str,command))
  with (d/'commands.jsonl').open('a') as f:f.write(json.dumps({'index':sequence,'argv':command})+'\n')
  result=subprocess.run(command,capture_output=True,timeout=180,**kwargs)
  (d/('%03d.stdout'%sequence)).write_bytes(result.stdout);(d/('%03d.stderr'%sequence)).write_bytes(result.stderr)
  if result.returncode:raise ValueError('new focused command failed at index '+str(sequence))
  return result.stdout
 try:
  helper=HERE/'tex_defaults_oracle.py';raw=helper.read_bytes();admitted(pins,revision)
  spec=importlib.util.spec_from_file_location('new_defaults_oracle',helper);module=importlib.util.module_from_spec(spec);exec(compile(raw,str(helper),'exec'),module.__dict__)
  code,observers=module.create(ROOT);(d/'original.c').write_text(code)
  fixture='#include <stddef.h>\n#include <stdint.h>\n'
  for i,(_,body) in enumerate(bodies):fixture+='static const uint8_t actual_body_'+str(i)+'[]={'+','.join(map(str,body))+'};\n'
  fixture+='typedef struct{const char*path;const uint8_t*data;size_t size;} DefaultsActual;\nstatic const DefaultsActual actual_defaults[]={\n'
  fixture+=''.join('{'+json.dumps(path)+',actual_body_'+str(i)+','+str(len(body))+'},\n' for i,(path,body) in enumerate(bodies))+'};\n'
  (d/'defaults_actual.h').write_text(fixture)
  common=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-I',d,'-I',HERE,'-I',HERE/'tests','-I',ROOT/'native-android/include']
  compiler=run(['cc','--version']).decode().splitlines()[0];modes={};objects={};binaries={};stack=[];core_release=[];dependencies=set()
  for mode,flags in [('release',['-O2']),('address',['-O1','-fsanitize=address','-no-pie']),('undefined',['-O1','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   admitted(pins,revision)
   obj=d/(mode+'-defaults.o');run([*common,*flags,'-fstack-usage','-c',HERE/'coh_wr_tex_defaults.c','-o',obj]);objects[mode]=sha(obj.read_bytes())
   if mode=='release':stack=obj.with_suffix('.su').read_text().splitlines()
   all_objects=[]
   for index,path in enumerate([HERE/'tests/test_tex_defaults.c',*CORE,d/'original.c']):
    obj=d/(mode+'-'+str(index)+'.o');run([*common,*flags,'-c',path,'-o',obj]);all_objects.append(obj)
    if mode=='release':
     dep=run([*common,'-MM',path]).decode().replace('\\\n',' ')
     for token in dep.split(':',1)[1].split():
      candidate=Path(token).resolve()
      if candidate.is_relative_to(ROOT):dependencies.add(str(candidate.relative_to(ROOT)))
     if path in CORE:core_release.append(obj)
   binary=d/mode;run(['cc',*flags,*all_objects,'-Wl,--wrap=calloc','-Wl,--wrap=free','-lcrypto','-lz','-lm','-o',binary])
   binary_sha=sha(binary.read_bytes());admitted(pins,revision)
   modes[mode]=json.loads(run([binary],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
   if binary_sha!=sha(binary.read_bytes()):raise ValueError('executable changed')
   binaries[mode]=binary_sha
  if dependencies-set(pins):raise ValueError('unadmitted compiled dependency '+str(sorted(dependencies-set(pins))))
  cpp=d/'cpp';run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-pedantic',HERE/'tests/test_tex_defaults_cpp.cpp',d/'release-defaults.o',*core_release,'-lz','-lm','-o',cpp]);run([cpp]);cpp_sha=sha(cpp.read_bytes())
  source=(HERE/'coh_wr_tex_defaults.c').read_text();test=(HERE/'tests/test_tex_defaults.c').read_text();anchor='#include "../coh_wr_tex_defaults.c"'
  mutations=[
   ('wrong_white_key','"white","grey"','"grey","grey"'),
   ('omit_invisible_alpha_clear','value.effective_basic_flags&=~1u','value.effective_basic_flags|=0u'),
   ('clear_alpha_on_other_rows','row==r->rows[COH_WR_TEX_DEFAULT_INVISIBLE]','row<r->report.basic_rows'),
   ('allow_required_misses','if((r->report.selected_mask&COH_WR_TEX_DEFAULT_REQUIRED_MASK)!=COH_WR_TEX_DEFAULT_REQUIRED_MASK)','if(0)'),
   ('drop_real_body_acquisition','status=coh_wr_tex_namespace_acquire(source,basic.row,cancel,&r->leases[i]);','status=COH_OK;'),
   ('leak_first_real_lease','if(r->leases[i]){\n  CohStatus s=coh_wr_tex_namespace_release','if(i&&r->leases[i]){\n  CohStatus s=coh_wr_tex_namespace_release'),
   ('ignore_final_selection_cancel','if(stopped(cancel)){status=COH_CANCELLED;goto fail;}','if(stopped(cancel)&&0){status=COH_CANCELLED;goto fail;}'),
   ('ignore_source_full_reservation','if(bound.external_bytes<ns.aggregate_reserved_bytes)','if(0)'),
   ('ignore_new_owner_limit','bound.owned_limit<sizeof(CohWrTexDefaults)','0'),
  ];caught=[]
  for label,before,after in mutations:
   if source.count(before)!=1 or test.count(anchor)!=1:raise ValueError('mutation preimage differs '+label)
   changed=d/(label+'.c');changed.write_text(source.replace(before,after,1));wrapper=d/(label+'-test.c');wrapper.write_text(test.replace(anchor,'#include "'+str(changed)+'"'))
   binary=d/label;run([*common,'-O2',wrapper,*core_release,d/'release-5.o','-Wl,--wrap=calloc','-Wl,--wrap=free','-lcrypto','-lz','-lm','-o',binary])
   sequence+=1;result=subprocess.run([str(binary)],capture_output=True,timeout=180)
   (d/('%03d.mutation-stdout'%sequence)).write_bytes(result.stdout);(d/('%03d.mutation-stderr'%sequence)).write_bytes(result.stderr)
   if result.returncode==0:raise ValueError('semantic mutation escaped '+label)
   caught.append(label)
  frames=[]
  for line in stack:
   parts=line.split('\t')
   if len(parts)!=3 or ('dynamic' in parts[2] and 'bounded' not in parts[2]):raise ValueError('unbounded native frame')
   frames.append(int(parts[1]))
  if sum(frames)>16384:raise ValueError('module stack reservation too small')
  admitted(pins,revision)
  if actual(a.actual_defaults_zip)!=bodies:raise ValueError('final input readmission differs')
  proof={'passed':True,'source_revision':revision,'source_sha256':pins,'compiler':compiler,'compiled_repo_dependencies':sorted(dependencies),'whole_original_oracle':observers,'generated_oracle_sha256':sha(code.encode()),'generated_fixture_sha256':sha(fixture.encode()),'actual_source':{'run':39078874753,'artifact':12118720382,'archive_bytes':12308,'archive_sha256':ARCHIVE_SHA,'body_bytes':sum(len(b) for _,b in bodies),'bodies':[{'path':path,'bytes':len(body),'sha256':sha(body)} for path,body in bodies]},'modes':modes,'standalone_C_object_sha256':objects,'binary_sha256':binaries,'actual_C_object_CPP_call_link':{'passed':True,'binary_sha256':cpp_sha},'semantic_code_mutations_refused':caught,'release_stack_usage':stack,'own_module_unique_frame_sum_conservative_bytes':sum(frames),'preparation_stack_control_reserve_bytes':16384,'stack_excludes_namespace_loader_provider_libc':True,'conditional_same_native_owner_default_identity_and_effective_flags':True,'authentic_bodies_in_complete_finite_controlled_provider':True,'actual_original_full_provider_inventory':False,'actual_original_current_CLIENT_defaults':False,'source_provider_must_remain_immutable_until_last_owner_pin_retires':True,'old_defaults_and_candidate_actually_simultaneously_live':True,'configured_admission_not_RSS':True,'LeakSanitizer_executed':False,'LeakSanitizer_host_limitation':'host proc/task enumeration unavailable; owned calloc/provider/body retirement tracked separately','old_qualifiers_rerun':False,'current_namespace':False,'composite_sampler_material':False,'GPU':False,'world':False,'Android_execution':False}
  (d/'host.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'modes':modes}))
 except BaseException:
  (d/'FAILED.json').write_text(json.dumps({'passed':False,'new_qualification_only':True,'last_command_index':sequence,'outputs_preserved':True})+'\n');raise
if __name__=='__main__':main()
