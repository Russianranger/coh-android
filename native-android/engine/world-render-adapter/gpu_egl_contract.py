"""Exact standalone EGL build/execution contract; no renderer material admission."""
import hashlib,json,re,struct
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PRIOR_SHA='633e2d4d3edb469f6d9a76e84d6bb2dd7bc6d0c399299bdf3c31ee91e77a3c29'
FIXTURE_SHA='c36001854f75ff7e8ef5304138537f1de4b71dcc3529a9a40f6093fde959df9a'
WHOLE_PACKET_SHA='261155800f81fbd7645e9e34a7b4c4ed9b453e1596fe3e947162df24bf29e45c'
PACKET_SHA='93ca8bfe6e2985b9e20c7c097038fb365199565c9eaed57f524416e456c4667c'
ABI={'arm64-v8a':('aarch64-linux-android26-clang',183),'x86_64':('x86_64-linux-android26-clang',62)}
SOURCES=['tests/test_gpu_egl.c','tests/coh_gpu_egl_backend.c','coh_wr_gpu_texture.c','coh_wr_tex_rgba32.c','coh_wr_tex_namespace.c','coh_wr_texture.c','coh_wr_sampler.c','../assets/coh_asset_loader.c','../../src/coh_assets.c','../../src/coh_dds.c']
EXTRA=['tests/coh_gpu_egl_backend.h','coh_wr_gpu_texture.h','coh_wr_tex_rgba32.h','coh_wr_tex_namespace.h','coh_wr_texture.h','coh_wr_sampler.h','../assets/coh_asset_loader.h','../renderer/coh_renderer.h','../coh_contracts.h','../../include/coh_native_core.h','../../src/byte_reader.h','gpu_egl_contract.py','prepare_gpu_egl.py','run_gpu_egl_android.py','acquire_egl_headers.py','egl-host-header-pins.json','sampler-authentic-pins.json','qualification/gpu-texture-model-20261017/host.json','EGL_QUALIFICATION.md','check_sampler.py','tests/test_gpu_egl_driver.py']

def sha(path):
 with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def source_paths(root):
 base=root/'native-android/engine/world-render-adapter'
 return {str((base/name).resolve().relative_to(root.resolve())):(base/name).resolve() for name in SOURCES+EXTRA}
def source_hashes(root):return {name:sha(path) for name,path in source_paths(root).items()}
def fixture_header(raw):
 if len(raw)!=43990 or hashlib.sha256(raw).hexdigest()!=FIXTURE_SHA:raise ValueError('Exact authentic EGL fixture required')
 pin=bytes.fromhex(FIXTURE_SHA)
 return ('/* FINITE TEST FIXTURE byte admission; NOT general SHA256 or security code. */\n#include <stdint.h>\n#include <stddef.h>\n#include <string.h>\nstatic const uint8_t coh_egl_fixture[]={'+','.join(str(n) for n in raw)+'};\nstatic uint8_t*coh_egl_fixture_digest(const uint8_t*p,size_t n,uint8_t*out){static const uint8_t pin[]={'+','.join(str(n) for n in pin)+'};if(n!=sizeof(coh_egl_fixture)||memcmp(p,coh_egl_fixture,n))return NULL;memcpy(out,pin,32);return out;}\n').encode()
def elf(path,machine):
 raw=path.read_bytes()
 if len(raw)<64 or raw[:7]!=b'\x7fELF\x02\x01\x01' or struct.unpack_from('<I',raw,20)[0]!=1 or struct.unpack_from('<H',raw,52)[0]!=64 or struct.unpack_from('<HH',raw,16)!=(3,machine):raise ValueError('Expected exact64-bit little-endian ABI PIE')
 phoff=struct.unpack_from('<Q',raw,32)[0];entsize,count=struct.unpack_from('<HH',raw,54)
 if entsize!=56 or not 2<=count<=128 or phoff>len(raw)-entsize*count:raise ValueError('Bounded ELF program headers')
 types=[];interpreters=[]
 for i in range(count):
  at=phoff+i*entsize;kind=struct.unpack_from('<I',raw,at)[0];offset=struct.unpack_from('<Q',raw,at+8)[0];size,memsize=struct.unpack_from('<QQ',raw,at+32)
  if offset>len(raw) or size>len(raw)-offset or (kind==1 and size>memsize):raise ValueError('ELF segment bounds')
  types.append(kind)
  if kind==3:interpreters.append(raw[offset:offset+size])
 if not {1,2,3}<=set(types) or interpreters!=[b'/system/bin/linker64\0']:raise ValueError('Android dynamic PIE interpreter')
 return True

def native(value,platform):
 fixed={'passed':True,'checks':183,'failure_line':0,'cleanup_verified':True,'gles_major':3,'contexts_created':2,'contexts_destroyed':2,'surfaces_created':3,'surfaces_destroyed':3,'readbacks':27,'levels_per_upload':9,'rgba_bytes_per_upload':349524,'generation_fixture_only':True,'sampler_fixture_only':True,'material_authority':False,'world_authority':False,'platform':platform}
 if not isinstance(value,dict) or set(value)!=set(fixed)|{'context_name_reused','gl_version','gl_renderer'}:raise ValueError('Native EGL result field set')
 for key,want in fixed.items():
  if type(value[key]) is not type(want) or value[key]!=want:raise ValueError('Native EGL result '+key)
 if type(value['context_name_reused']) is not bool:raise ValueError('Name reuse result type')
 if any(type(value[k]) is not str or not 1<=len(value[k])<192 or any(ord(c)<32 for c in value[k]) for k in ('gl_version','gl_renderer')):raise ValueError('Actual GL identity strings')
 if not re.match(r'^OpenGL ES 3\.',value['gl_version']):raise ValueError('Actual GLES3 version required')
 return value
