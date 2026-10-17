#!/usr/bin/env python3
"""Qualify authentic detached TX2 cached low-mips, not namespace/material/GPU state."""
import argparse,hashlib,importlib.util,json,os,sys,tempfile,subprocess,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
LOCAL=['coh_wr_tex_preload.c','coh_wr_tex_preload.h','coh_wr_texture.h','tests/test_tex_preload.c','tests/tex_preload_fixture.h','tex_preload_oracle.py','check_tex_preload.py','TEX_PRELOAD.md','check_texname.py','tex-inputs-authentic-pins.json','sampler-authentic-pins.json']
UPSTREAM=['Game/src/render/tex.c','Game/src/render/tex.h','Game/src/render/dd.h','Game/src/render/texEnums.h','Utilities/GetTex/src/gettex.c','3rdparty/cg/include/GL/glext.h']
PATHS=[HERE/x for x in LOCAL]+[ROOT/'upstream/ouroboros'/x for x in UPSTREAM]+[HERE.parent/'assets/coh_asset_loader.c',HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c',ROOT/'native-android/src/byte_reader.h',ROOT/'native-android/include/coh_native_core.h']
START={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in PATHS}
def load(name,path):
 b=path.read_bytes()
 if sha(b)!=START[str(path.relative_to(ROOT))]:raise ValueError('helper changed before execution')
 sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sys.modules[name]=m;exec(compile(b,str(path),'exec'),m.__dict__);return m

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--actual-box',type=Path,required=True);p.add_argument('--actual-bar',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('fresh output required')
 pins=[json.loads((HERE/'sampler-authentic-pins.json').read_text())['payload'],json.loads((HERE/'tex-inputs-authentic-pins.json').read_text())['bar']]
 def readmit():
  for path,pin in zip((a.actual_box,a.actual_bar),pins):
   with path.open('rb') as f:b=f.read(pin['bytes']+1)
   if len(b)!=pin['bytes'] or sha(b)!=pin['sha256']:raise ValueError('exact authentic cached body differs')
 readmit();old=load('preload_commands',HERE/'check_texname.py');producer=load('preload_oracle',HERE/'tex_preload_oracle.py');code,blocks,types=producer.create(ROOT,old.extract);modes={};exports={};mutations=[];tex=(ROOT/'upstream/ouroboros/Game/src/render/tex.c').read_text();enum=(ROOT/'upstream/ouroboros/Game/src/render/texEnums.h').read_text()
 if not re.search(r'TEXOPT_JPEG\s*=\s*1\s*<<\s*17\s*,',enum):raise ValueError('source JPEG flag drift')
 default_keys=re.findall(r'texFind\("([^"\n]+)"\)',blocks['texFindNeededBinds'])
 if default_keys!=['white','grey','invisible','black','dummy_bump','dummy_dynamic_cubemap_face0','buildingLightPattern']:raise ValueError('original default list differs')
 pipeline=old.extract(tex,'void texScanForTexHeaders(bool bInitialLoad)');order=re.findall(r'\b(fileScanAllDataDirs|texFindNeededBinds|texCreateCompositeTextures|trickCreateTextures|texCheckSwapList|texSetBinds)\s*\(',pipeline)
 if order!=['fileScanAllDataDirs','texFindNeededBinds','texCreateCompositeTextures','trickCreateTextures','texCheckSwapList','texSetBinds']:raise ValueError('namespace stage order drift')
 with tempfile.TemporaryDirectory(prefix='coh-preload-') as directory:
  d=Path(directory);(d/'original.c').write_text(code);base=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-I',HERE,'-I',HERE/'tests','-I',ROOT/'native-android/include']
  for mode,flags in [('release',['-O2']),('address',['-O1','-fsanitize=address','-no-pie']),('undefined',['-O1','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   standalone=d/('native-'+mode+'.o');old.run([*base,*flags,'-c',HERE/'coh_wr_tex_preload.c','-o',standalone]);names=sorted(line.split()[-1] for line in old.run(['nm','-g','--defined-only',standalone]).decode().splitlines());expected=['coh_wr_tex_preload_'+x for x in ['acquire','identity','mip','name','raw','release','report']]
   if names!=expected:raise ValueError('private symbol escaped')
   objects=[]
   for i,path in enumerate([HERE/'tests/test_tex_preload.c',HERE.parent/'assets/coh_asset_loader.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c',d/'original.c']):
    obj=d/(str(i)+'.o');old.run([*base,*flags,*(['-Wno-error=sign-compare'] if path==d/'original.c' else []),'-c',path,'-o',obj]);objects.append(obj)
   binary=d/mode;old.run(['cc',*flags,*objects,'-Wl,--wrap=calloc','-lcrypto','-lz','-lm','-o',binary]);modes[mode]=json.loads(old.run([binary,a.actual_box,a.actual_bar],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));exports[mode]={'symbols':names,'binary_sha256':sha(binary.read_bytes()),'standalone_object_sha256':sha(standalone.read_bytes())}
  native=(HERE/'coh_wr_tex_preload.c').read_text();test=(HERE/'tests/test_tex_preload.c').read_text()
  for name,before,after in [('cached_DDS_byte_identity','||memcmp(p+16,r.mip[0].blocks,packed)',''),('original_four_levels','r.count=full<4?full:4;','r.count=full<3?full:3;'),('budget_before_callbacks',' size_t total=limits->external_bytes;',' if(stop(cancel))return COH_CANCELLED;\n size_t total=limits->external_bytes;')]:
   if native.count(before)!=1:raise ValueError('mutation preimage differs')
   c=d/(name+'.c');c.write_text(native.replace(before,after));t=d/(name+'-test.c');t.write_text(test.replace('#include "../coh_wr_tex_preload.c"','#include "'+str(c)+'"'));obj=d/(name+'.o');old.run([*base,'-O2','-c',t,'-o',obj]);binary=d/name;old.run(['cc',obj,*objects[1:],'-fsanitize=undefined','-fno-sanitize-recover=all','-Wl,--wrap=calloc','-lcrypto','-lz','-lm','-o',binary]);result=subprocess.run([binary,a.actual_box,a.actual_bar],capture_output=True,timeout=60)
   if not result.returncode:raise ValueError('semantic mutation escaped '+name)
   mutations.append(name)
 if START!={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in PATHS}:raise ValueError('source changed')
 readmit();proof={'passed':True,'source_revision':old.run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_sha256':START,'authentic_sha256':[p['sha256'] for p in pins],'modes':modes,'standalone_exports_and_binaries':exports,'semantic_mutations_refused':mutations,'original_function_sha256':{k:sha(v.encode()) for k,v in blocks.items()},'original_type_declarations_sha256':sha(types.encode()),'namespace_scan_pipeline':order,'default_binding_lookup_keys':default_keys,'original_default_binding_prefix_unknown_white_only':True,'original_GetTex_writeMipMapHeader_executed':True,'original_CLIENT_texBindLowMips_executed':True,'DDS_wire124_and_storage_render_observers':True,'generic_protected_BC_RGBA':True,'original_nvDXT_CPU_RGBA_claim':False,'active_namespace_or_generation':False,'default_white_or_material_created':False,'GPU_uploaded':False,'world_authority':False,'android_execution':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'modes':modes}))
if __name__=='__main__':main()
