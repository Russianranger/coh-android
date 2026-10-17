#!/usr/bin/env python3
"""Qualify bounded authentic-header BasicTexture lookup; no active table/fallback."""
import argparse,hashlib,importlib.util,json,os,sys,tempfile,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
LOCAL=['coh_wr_tex_basic_lookup.c','coh_wr_tex_basic_lookup.h','tests/test_tex_basic_lookup.c','check_tex_basic_lookup.py','tex_basic_lookup_oracle.py','BASIC_TEXTURE_LOOKUP.md','coh_wr_tex_inputs.c','coh_wr_tex_inputs.h','check_texname.py','texname_guard_candidate.py','tex-inputs-authentic-pins.json','sampler-authentic-pins.json']
PATHS=[HERE/x for x in LOCAL]+[ROOT/'upstream/ouroboros/Game/src/render'/x for x in ['tex.c','tex.h']]+[HERE.parent/'assets/coh_asset_loader.c',HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c',ROOT/'native-android/src/byte_reader.h',ROOT/'native-android/include/coh_native_core.h']
START={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in PATHS}
def load(name,path):
 b=path.read_bytes()
 if sha(b)!=START[str(path.relative_to(ROOT))]:raise ValueError('helper changed before execution')
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;exec(compile(b,str(path),'exec'),m.__dict__);return m

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--actual-box',type=Path,required=True);p.add_argument('--actual-bar',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('fresh output required')
 pins=[json.loads((HERE/'sampler-authentic-pins.json').read_text())['payload'],json.loads((HERE/'tex-inputs-authentic-pins.json').read_text())['bar']]
 for path,pin in zip((a.actual_box,a.actual_bar),pins):
  with path.open('rb') as f:b=f.read(pin['bytes']+1)
  if len(b)!=pin['bytes'] or sha(b)!=pin['sha256']:raise ValueError('exact authentic cached body differs')
 old=load('basic_lookup_commands',HERE/'check_texname.py');candidate=load('basic_lookup_candidate',HERE/'texname_guard_candidate.py');producer=load('basic_lookup_oracle',HERE/'tex_basic_lookup_oracle.py');code,repair,blocks=producer.create(ROOT,old.extract,candidate.patch);modes={};exports={};mutations=[]
 with tempfile.TemporaryDirectory(prefix='coh-basic-lookup-') as directory:
  d=Path(directory);(d/'original.c').write_text(code)
  base=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-I',HERE,'-I',ROOT/'native-android/include']
  for mode,flags in [('release',['-O2']),('address',['-O1','-fsanitize=address','-no-pie']),('undefined',['-O1','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   objects=[]
   for i,path in enumerate([HERE/'coh_wr_tex_basic_lookup.c',HERE/'coh_wr_tex_inputs.c',HERE/'tests/test_tex_basic_lookup.c',HERE.parent/'assets/coh_asset_loader.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c',d/'original.c']):
    obj=d/(str(i)+'.o');old.run([*base,*flags,'-c',path,'-o',obj]);objects.append(obj)
   symbols=old.run(['nm','-g','--defined-only',objects[0]]).decode();names=sorted(row.split()[-1] for row in symbols.splitlines())
   if names!=['coh_wr_tex_basic_lookup','coh_wr_tex_basic_lookup_guarded']:raise ValueError('private symbol escaped')
   binary=d/mode;old.run(['cc',*flags,*objects,'-lcrypto','-lz','-lm','-o',binary]);modes[mode]=json.loads(old.run([binary,a.actual_box,a.actual_bar],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));exports[mode]={'symbols':names,'binary_sha256':sha(binary.read_bytes())}
  native=(HERE/'coh_wr_tex_basic_lookup.c').read_text()
  for name,before,after in [('dds_flag','else if(!strcmp(ext,"dds"))result.format_flags=1u<<6','else if(!strcmp(ext,"dds"))result.format_flags=1u<<5'),('one_bang_only',"if(query[0]=='!'){query++;n--;}","while(query[0]=='!'){query++;n--;}"),('keep_portal_basic','result.branch=COH_WR_BASIC_NAMESPACE_UNKNOWN;','if(strstr(result.key,"PORTAL")){return COH_UNSUPPORTED;}result.branch=COH_WR_BASIC_NAMESPACE_UNKNOWN;')]:
   if native.count(before)!=1:raise ValueError('mutation preimage differs')
   c=d/(name+'.c');c.write_text(native.replace(before,after));obj=d/(name+'.o');old.run([*base,'-O2','-c',c,'-o',obj]);binary=d/name;old.run(['cc',obj,*objects[1:],'-fsanitize=undefined','-fno-sanitize-recover=all','-lcrypto','-lz','-lm','-o',binary]);result=subprocess.run([binary,a.actual_box,a.actual_bar],capture_output=True,timeout=30)
   if not result.returncode:raise ValueError('semantic mutation escaped '+name)
   mutations.append(name)
 if START!={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in PATHS}:raise ValueError('source readmission differs')
 for path,pin in zip((a.actual_box,a.actual_bar),pins):
  with path.open('rb') as f:b=f.read(pin['bytes']+1)
  if len(b)!=pin['bytes'] or sha(b)!=pin['sha256']:raise ValueError('authentic input changed')
 result={'passed':True,'source_revision':old.run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_sha256':START,'authentic_sha256':[p['sha256'] for p in pins],'modes':modes,'symbols_and_binary_sha256':exports,'source_semantic_mutations_refused':mutations,'original_blocks_sha256':{k:sha(v.encode()) for k,v in blocks.items()},'explicit_short_key_repair':repair,'strict_safe_domain_original_texFind_executed':True,'release_debug_assertions_disabled':True,'bounded_string_and_subset_stash_observers':True,'active_namespace':False,'namespace_absence_proven':False,'default_or_white_resource_created':False,'TexWord_or_locale_or_caps_resolved':False,'material_authority':False,'world_authority':False,'android_execution':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'modes':modes}))
if __name__=='__main__':main()
