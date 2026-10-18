#!/usr/bin/env python3
"""Original CLIENT sampler oracle and exact authentic cached texture CPU proof.
No material/scene/live capability is produced. Pillow is an independent DDS oracle.
"""
import argparse,hashlib,io,json,os,struct,subprocess,tempfile
from pathlib import Path
from PIL import Image
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,**kw):
 p=subprocess.run(list(map(str,cmd)),text=True,capture_output=True,timeout=180,**kw)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout
def block(text,start):
 a=text.index('{',start);depth=1;b=a+1
 while depth:
  if text[b]=='{':depth+=1
  elif text[b]=='}':depth-=1
  b+=1
 return text[start:b]
def oracle():
 pins=json.loads((HERE/'sampler-source-pins.json').read_text())
 for path,want in pins.items():
  if sha(ROOT/path)!=want:raise ValueError('Original source changed: '+path)
 tex=(ROOT/'upstream/ouroboros/Game/src/render/tex.c').read_text()
 enum=(ROOT/'upstream/ouroboros/Game/src/render/texEnums.h').read_text();a=enum.index('typedef enum TexOptFlags');b=enum.index('} TexOptFlags;',a)+len('} TexOptFlags;');enum=enum[a:b]
 setup=block(tex,tex.index('void texSetupParamsFromBind('))
 rt=(ROOT/'upstream/ouroboros/Game/src/render/thread/rt_tex.c').read_text();sampling=block(rt,rt.index('if (!bDontSetFlags)'))
 header=(ROOT/'upstream/ouroboros/Game/src/render/tex.h').read_text();b=header.index('} TextureFileHeader;')+len('} TextureFileHeader;');a=header.rindex('typedef struct {',0,b);header=header[a:b]
 prefix='''#include <stdint.h>
#include <string.h>
#include <assert.h>
#include <stddef.h>
typedef float F32;typedef unsigned char U8;
#define GL_RGB 100
#define GL_RGBA8 101
#define GL_TEXTURE_WRAP_S 0
#define GL_TEXTURE_WRAP_T 1
#define GL_TEXTURE_MIN_FILTER 2
#define GL_TEXTURE_MAG_FILTER 3
#define GL_CLAMP 99
#define GL_NEAREST 0
#define GL_LINEAR 1
#define GL_LINEAR_MIPMAP_LINEAR 2
#define GL_MIRRORED_REPEAT_IBM 2
#define GL_TEXTURE_MAX_ANISOTROPY_EXT 4
#define CHECKGL
static int gl_clamp_val=1;
static struct {int supports_anisotropy;} rdr_caps={0};
static struct {float texAnisotropic;} rdr_view_state={1};
typedef struct {uint32_t texopt_flags,id,target;} BasicTexture;
typedef struct {int format,width,height,mip_count;} TexReadInfo;
typedef struct {int src_format,dxtc,width,height,id,target,dst_format,clamp_s,mirror_s,clamp_t,mirror_t,tex_border,point_sample,mip_count,mipmap;} RdrTexParams;
static int *observed;
static void glTexParameterf(int target,int key,float value){(void)target;if(key<4)observed[key]=(int)value;}
'''
 tail='''
_Static_assert(sizeof(TextureFileHeader)==32,"source texture wrapper size");
_Static_assert(offsetof(TextureFileHeader,flags)==16,"source flags");
_Static_assert(offsetof(TextureFileHeader,alpha)==28,"source alpha");
void oracle_sampler(uint32_t flags,unsigned mip,int out[4]){
 BasicTexture bind={flags,0,0xde1};TexReadInfo info={0,8,4,(int)mip};RdrTexParams params;
 texSetupParamsFromBind(&bind,&info,&params);RdrTexParams*rtex=&params;
 int bindTarget=0xde1,bDontSetFlags=0;out[0]=out[1]=0;out[2]=out[3]=1;observed=out;
'''
 return prefix+enum+'\n'+header+'\n'+setup+'\n'+tail+sampling+'\n}\n',pins

def texture_oracle(path,packet):
 pin=json.loads((HERE/'sampler-authentic-pins.json').read_text());raw=path.read_bytes()
 if len(raw)!=pin['payload']['bytes'] or sha(path)!=pin['payload']['sha256']:raise ValueError('Authentic texture pin differs')
 hs,size,width,height,flags=struct.unpack_from('<5I',raw);dds=raw[hs:]
 if size!=len(dds) or raw[29:32]!=b'TX2' or dds[:4]!=b'DDS ':raise ValueError('Original cache wrapper mismatch')
 if (width,height)!=(struct.unpack_from('<I',dds,16)[0],struct.unpack_from('<I',dds,12)[0]):raise ValueError('Dimension mismatch')
 levels=struct.unpack_from('<I',dds,28)[0] or 1;fourcc=dds[84:88];blockbytes=8 if fourcc==b'DXT1' else 16
 if fourcc not in (b'DXT1',b'DXT3',b'DXT5'):raise ValueError('Only exact compressed fixture oracle supported')
 offset=128;expected=bytearray();mips=[];w=width;h=height
 for i in range(levels):
  n=((w+3)//4)*((h+3)//4)*blockbytes;blocks=dds[offset:offset+n]
  if len(blocks)!=n:raise ValueError('Truncated mip')
  head=bytearray(dds[:128]);struct.pack_into('<I',head,12,h);struct.pack_into('<I',head,16,w);struct.pack_into('<I',head,28,1)
  rgba=Image.open(io.BytesIO(head+blocks)).convert('RGBA').tobytes();expected+=rgba
  mips.append({'level':i,'width':w,'height':h,'rgba_sha256':hashlib.sha256(rgba).hexdigest()});offset+=n;w=max(w//2,1);h=max(h//2,1)
 if offset!=len(dds) or packet.read_bytes()!=expected:raise ValueError('Protected RGBA differs from independent all-mip Pillow DDS decoding')
 return {'payload_sha256':sha(path),'width':width,'height':height,'cached_texopt_flags':flags,'fourcc':fourcc.decode(),'levels':levels,'decoded_rgba_bytes':len(expected),'packet_sha256':sha(packet),'pillow_all_mips_equal':True,'mips':mips,'cached_flags_not_final_client_state':True}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--actual-texture',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('New receipt path required')
 pin=json.loads((HERE/'sampler-authentic-pins.json').read_text())
 if a.actual_texture.stat().st_size!=pin['payload']['bytes'] or sha(a.actual_texture)!=pin['payload']['sha256']:raise ValueError('Authentic texture input rejected before native execution')
 code,pins=oracle();native=ROOT/'native-android'
 sources=[HERE.parent/'assets/coh_asset_loader.c',native/'src/coh_assets.c',native/'src/coh_dds.c']
 base=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-I',native/'include','-I',HERE]
 results={};texresults={};ownerresults={};gpuresults={}
 with tempfile.TemporaryDirectory(prefix='coh-sampler-') as directory:
  t=Path(directory);(t/'oracle.c').write_text(code)
  for mode,flags in {'release':['-O2'],'address':['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie'],'undefined':['-O1','-g','-fsanitize=undefined','-fno-omit-frame-pointer']}.items():
   env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
   exe=t/('sampler-'+mode);run([*base,*flags,HERE/'coh_wr_sampler.c',HERE/'tests/test_sampler.c',t/'oracle.c','-o',exe]);results[mode]=json.loads(run([exe],env=env))
   exe=t/('texture-'+mode);packet=t/('texture-'+mode+'.rgba');run([*base,*flags,HERE/'tests/test_sampler_texture.c',*sources,'-lz','-lm','-o',exe]);texresults[mode]=json.loads(run([exe,a.actual_texture,packet],env=env));proof=texture_oracle(a.actual_texture,packet)
   exe=t/('owner-'+mode);ownerpacket=t/('owner-'+mode+'.rgba');run([*base,*flags,HERE/'tests/test_texture_owner.c',HERE/'coh_wr_texture.c',*sources,'-Wl,--wrap=malloc,--wrap=calloc,--wrap=realloc,--wrap=free','-lcrypto','-lz','-lm','-o',exe]);ownerresults[mode]=json.loads(run([exe,a.actual_texture,ownerpacket],env=env))
   if ownerpacket.read_bytes()!=packet.read_bytes():raise ValueError('Immutable texture owner packet differs from qualified protected parser packet')
   exe=t/('gpu-'+mode);run([*base,*flags,HERE/'tests/test_gpu_texture.c',HERE/'coh_wr_gpu_texture.c',HERE/'coh_wr_tex_rgba32.c',HERE/'coh_wr_tex_namespace.c',HERE/'coh_wr_texture.c',HERE/'coh_wr_sampler.c',*sources,'-Wl,--wrap=calloc','-lcrypto','-lz','-lm','-o',exe]);gpuresults[mode]=json.loads(run([exe,a.actual_texture],env=env))
  mutation_controls=[]
  source=(HERE/'coh_wr_sampler.c').read_text()
  for label,before,after in [('clamp_precedence','(f&BIT(6))?COH_WRAP_CLAMP:(f&BIT(9))?COH_WRAP_MIRROR','(f&BIT(9))?COH_WRAP_MIRROR:(f&BIT(6))?COH_WRAP_CLAMP'),('point_filter','t.mag_filter=(f&BIT(26))?COH_FILTER_NEAREST:COH_FILTER_LINEAR','t.mag_filter=COH_FILTER_LINEAR')]:
   if source.count(before)!=1:raise ValueError('Mutation anchor differs')
   mutated=t/(label+'.c');mutated.write_text(source.replace(before,after));exe=t/label
   run([*base,'-O2',mutated,HERE/'tests/test_sampler.c',t/'oracle.c','-o',exe])
   result=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30)
   if result.returncode!=1 or 'sampler line' not in result.stderr:raise ValueError('Oracle failed to reject production mutation')
   mutation_controls.append(label)
  gpu_mutations=[]
  source=(HERE/'coh_wr_gpu_texture.c').read_text()
  for label,before,after in [('omit_last_mip','level<report.levels;level++','level+1<report.levels;level++'),('pbo_left_bound','CALL(o->bind_unpack_buffer(o->context,0));','/* Deliberate missing PBO reset. */')]:
   if source.count(before)!=1:raise ValueError('GPU mutation anchor differs')
   mutated=t/(label+'.c');mutated.write_text(source.replace(before,after));exe=t/label
   run([*base,'-O2',HERE/'tests/test_gpu_texture.c',mutated,HERE/'coh_wr_tex_rgba32.c',HERE/'coh_wr_tex_namespace.c',HERE/'coh_wr_texture.c',HERE/'coh_wr_sampler.c',*sources,'-Wl,--wrap=calloc','-lcrypto','-lz','-lm','-o',exe])
   result=subprocess.run([str(exe),str(a.actual_texture)],capture_output=True,text=True,timeout=30)
   if result.returncode!=1 or 'GPU line' not in result.stderr:raise ValueError('GPU controls failed to reject mutation')
   gpu_mutations.append(label)
  files=[HERE/'coh_wr_sampler.c',HERE/'coh_wr_sampler.h',HERE/'coh_wr_texture.c',HERE/'coh_wr_texture.h',HERE/'coh_wr_gpu_texture.c',HERE/'coh_wr_gpu_texture.h',HERE/'coh_wr_tex_rgba32.c',HERE/'coh_wr_tex_rgba32.h',HERE/'coh_wr_tex_namespace.c',HERE/'coh_wr_tex_namespace.h',HERE/'tests/test_gpu_texture.c',HERE/'tests/test_texture_owner.c',HERE/'tests/test_sampler.c',HERE/'tests/test_sampler_texture.c',HERE/'check_sampler.py',HERE/'sampler-source-pins.json',HERE/'sampler-authentic-pins.json',HERE/'acquire_sampler_texture.py',HERE/'CLIENT_RESOURCE_BINDING.md',HERE/'GPU_TEXTURE_UPLOAD.md',HERE.parent/'coh_contracts.h',HERE.parent/'renderer/coh_renderer.h',HERE.parent/'assets/coh_asset_loader.h',*sources,native/'include/coh_native_core.h',native/'src/byte_reader.h',ROOT/'native-android/tools/material_fixture/acquire.py']
  receipt={'passed':True,'source_sha256':{str(x.relative_to(ROOT)):sha(x) for x in files},'original_source_sha256':pins,'original_setup_and_render_sampling_unchanged':True,'rejected_production_mutations':mutation_controls,'rejected_gpu_production_mutations':gpu_mutations,'compiler':run(['cc','--version']).splitlines()[0],'pillow_version':Image.__version__,'sampler':results,'immutable_texture_owner':ownerresults,'injected_gpu_adapter':gpuresults,'authentic_texture':texresults,'texture_oracle':proof,'original_header_layout_controls':3,'asan_leak_detection':False,'no_gpu_or_android_execution':True,'material_authority':False,'live_world_authority':False}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':True,'sampler':results['release'],'texture':texresults['release'],'receipt':str(a.output)}))
if __name__=='__main__':main()
