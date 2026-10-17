#!/usr/bin/env python3
"""Qualify bounded legacy rigid geometry against original32-bit readModel/deltas."""
import argparse,ctypes as C,hashlib,importlib.util,json,os,struct,subprocess,tempfile,zlib,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def run(command,**kwargs):
 p=subprocess.run(list(map(str,command)),capture_output=True,timeout=180,**kwargs)
 if p.returncode:raise ValueError(p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
 return p.stdout

def brace(text,start):
 at=text.index('{',start);end=at+1;depth=1
 while depth:
  if text[end]=='{':depth+=1
  if text[end]=='}':depth-=1
  end+=1
 return text[start:end]

def original_record(temp,record,names,materials):
 # Execute unchanged readModel with actual32-bit pointers/producer structures.
 anim=(ROOT/'upstream/ouroboros/Common/seq/anim.c').read_text();header=(ROOT/'upstream/ouroboros/Common/seq/anim.h').read_text();grid=(ROOT/'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/components/gridpoly.h').read_text()
 function=brace(anim,anim.index('static int readModel('));a=anim.index('typedef struct\n{\n    PackData');b=anim.index('} ModelFormatOnDisk_v2;',a)+len('} ModelFormatOnDisk_v2;');declarations=anim[a:b]
 a=header.index('typedef struct PackData');b=header.index('} PackData;',a)+len('} PackData;');pack=header[a:b]
 a=grid.index('typedef struct\n{');b=grid.index('} PolyGrid;',a)+len('} PolyGrid;');grid=grid[a:b]
 prefix='''typedef unsigned char U8;typedef unsigned int U32;typedef short S16;typedef float F32;typedef float Vec3[3];typedef unsigned int uintptr_t;typedef int intptr_t;typedef unsigned int size_t;
typedef struct VBO VBO;typedef struct BoneInfo BoneInfo;typedef struct TrickNode TrickNode;typedef struct CTri CTri;typedef struct AltPivotInfo AltPivotInfo;typedef struct ModelExtra ModelExtra;typedef struct GeoLoadData GeoLoadData;typedef struct PolyCell PolyCell;typedef struct TexID TexID;
static void die(int value){__asm__ volatile("int $0x80"::"a"(1),"b"(value):"memory");for(;;){}}
#define assert(x) do{if(!(x))die(90);}while(0)
#define CLIENT 1
static void*memcpy(void*d,const void*s,size_t n){U8*a=d;const U8*b=s;for(size_t i=0;i<n;i++)a[i]=b[i];return d;}
static void*memset(void*d,int v,size_t n){U8*a=d;for(size_t i=0;i<n;i++)a[i]=(U8)v;return d;}
#define copyVec3(a,b) memcpy(b,a,12)
#define setVec3(a,x,y,z) do{(a)[0]=x;(a)[1]=y;(a)[2]=z;}while(0)
'''
 model='''typedef struct {U32 flags;F32 radius;int tex_count;S16 id;U8 loadstate;BoneInfo*boneinfo;TexID*tex_idx;PolyGrid grid;char*name;AltPivotInfo*api;Vec3 scale,min,max,autolod_dists;struct{PackData tris,verts,norms,sts,sts3,weights,matidxs,grid,reductions,reflection_quads;}pack;} Model;\n'''
 arrays='\n'.join('static U8 '+name+'[] __attribute__((aligned(4)))={'+','.join(map(str,data))+'};' for name,data in [('record',record),('names',names),('materials',materials)])
 main='''
void _start(void){Model dst;U32 facts[52];memset(&dst,0,sizeof(dst));int used=readModel(&dst,(char*)record,0,names,materials);
facts[0]=sizeof(ModelFormatOnDisk_v2);facts[1]=(U32)used;facts[2]=dst.flags;memcpy(facts+3,&dst.radius,4);facts[4]=dst.tex_count;facts[5]=dst.vert_count;facts[6]=dst.tri_count;facts[7]=(U32)dst.boneinfo;facts[8]=(U32)dst.api;facts[9]=(U32)dst.grid.cell;facts[10]=(U32)(dst.name-(char*)names);facts[11]=(U32)((U8*)dst.tex_idx-materials);facts[12]=(U32)dst.id;memcpy(facts+13,dst.scale,12);memcpy(facts+16,dst.min,12);memcpy(facts+19,dst.max,12);
PackData*p=&dst.pack.tris;for(unsigned i=0;i<10;i++){facts[22+i*3]=p[i].packsize;facts[23+i*3]=p[i].unpacksize;facts[24+i*3]=(U32)p[i].data;}
int wrote;__asm__ volatile("int $0x80":"=a"(wrote):"a"(4),"b"(1),"c"(facts),"d"(sizeof(facts)):"memory");die(wrote==(int)sizeof(facts)?0:91);}
'''
 # Toy destination only names source-assigned members; source disk declaration,
 # readModel and pack/grid definitions above remain byte-for-byte unchanged.
 model=model.replace('S16 id;','S16 id;int vert_count,tri_count,reflection_quad_count;')
 layout='\nconst U32 coh_layout[] __attribute__((section(".coh_layout"),used))={sizeof(ModelFormatOnDisk_v2),'+','.join('__builtin_offsetof(ModelFormatOnDisk_v2,'+name+')' for name in ('flags','radius','tex_count','boneinfo','vert_count','tri_count','tex_idx','grid','name','api','extra','scale','pack'))+'};\n'
 code=prefix+pack+'\n'+grid+'\n'+declarations+'\n'+model+function+'\n'+arrays+'\n'+layout+main
 (temp/'original-read-model.c').write_text(code)
 run(['cc','-m32','-std=c11','-ffreestanding','-fno-builtin','-fno-stack-protector','-fno-pie','-fno-strict-aliasing','-O0','-c',temp/'original-read-model.c','-o',temp/'original-read-model.o'])
 run(['ld','-m','elf_i386','-o',temp/'original-read-model',temp/'original-read-model.o'])
 run(['objcopy','-O','binary','--only-section=.coh_layout',temp/'original-read-model.o',temp/'original-layout.bin'])
 layout_values=list(struct.unpack('<14I',(temp/'original-layout.bin').read_bytes()))
 if layout_values!=[216,0,4,12,20,28,32,36,40,80,84,88,92,132]:raise ValueError('Original32-bit legacy structure layout differs')
 refusal=None;facts=None
 try:
  execution=subprocess.run([str(temp/'original-read-model')],capture_output=True,timeout=30)
  (temp/'execution.stdout').write_bytes(execution.stdout);(temp/'execution.stderr').write_bytes(execution.stderr)
  if execution.returncode:raise ValueError('Original32-bit consumer failed; retained execution output')
  facts=list(struct.unpack('<52I',execution.stdout))
 except OSError as error:
  if error.errno!=8:raise
  refusal={'errno':error.errno,'message':str(error),'binary_sha256':sha(temp/'original-read-model'),'scope':'Local kernel refused ELF32 execution; original consumer execution NOT qualified'}
  (temp/'execution-refusal.json').write_text(json.dumps(refusal,indent=2)+'\n')
  (temp/'execution.stderr').write_text(str(error)+'\n')
 expected=[216,216,struct.unpack_from('<I',record,0)[0],struct.unpack_from('<I',record,4)[0],struct.unpack_from('<I',record,12)[0],*struct.unpack_from('<2I',record,28),struct.unpack_from('<I',record,20)[0],struct.unpack_from('<I',record,84)[0],struct.unpack_from('<I',record,40)[0],struct.unpack_from('<I',record,80)[0],struct.unpack_from('<I',record,36)[0],struct.unpack_from('<h',record,16)[0]&0xffffffff,*struct.unpack_from('<9I',record,92)]
 packs=[(0,0,0)]*10
 for source,target in enumerate((0,1,2,3,5,6,7)):packs[target]=struct.unpack_from('<3I',record,132+source*12)
 expected+=sum((list(p) for p in packs),[])
 if facts is not None and facts!=expected:raise ValueError('Original32-bit readModel metadata/pack mapping differs')
 return {'source_layout_passed':True,'original_consumer_executed':facts is not None,'true32bit_freestanding_linux_execution':facts is not None,'execution_refusal':refusal,'source_layout_offsets':layout_values,'unchanged_readModel_sha256_lf':hashlib.sha256(function.encode()).hexdigest(),'source_model_record_bytes':216,'metadata_and_pack_scalars_compared':52 if facts is not None else 0,'original_grid_pack_declarations_unchanged':True,'generated_oracle_sha256':sha(temp/'original-read-model.c'),'binary_sha256':sha(temp/'original-read-model')}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--actual-geo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--oracle-output',type=Path);p.add_argument('--require-original32',action='store_true');a=p.parse_args()
 oracle_output=(a.oracle_output or a.output.parent/(a.output.stem+'-original32')).resolve()
 if a.output.exists() or oracle_output.exists():raise ValueError('Fresh output/oracle directories required')
 oracle_output.mkdir(parents=True)
 pin=json.loads((HERE/'rigid-atlas-v0-pins.json').read_text())
 if sha(a.actual_geo)!=pin['sha256'] or a.actual_geo.stat().st_size!=pin['bytes']:raise ValueError('Exact cached root-reachable body pin mismatch')
 source=ROOT/'upstream/ouroboros/Common/seq/anim.c'
 source_pins=json.loads((HERE/'rigid-source-pins.json').read_text())['source_sha256']
 for source_path,expected_sha in source_pins.items():
  if sha(ROOT/source_path)!=expected_sha:raise ValueError('Original source pin changed: '+source_path)
 sys.path.insert(0,str(HERE/'tests'))
 fixture=module('rigid_legacy_fixture',HERE/'tests/rigid_legacy_fixture.py');base=module('rigid_fixture',HERE/'tests/rigid_fixture.py')
 raw=a.actual_geo.read_bytes();bias,n=struct.unpack_from('<2I',raw);header=zlib.decompress(raw[8:bias+4]);payload=raw[bias+8:]
 if len(header)!=n:raise ValueError('Legacy header size')
 size,t,namesize,matsize=struct.unpack_from('<4I',header);at=16+t;names=header[at:at+namesize];at+=namesize;materials=header[at:at+matsize];at+=matsize;at+=140
 selected=[]
 for row in range((len(header)-at)//216):
  record=header[at+row*216:at+(row+1)*216];off=struct.unpack_from('<I',record,80)[0]
  if names[off:].split(b'\0')[0].decode()==pin['model']:selected.append((row,record))
 if len(selected)!=1 or selected[0][0]!=pin['original_disk_model_row']:raise ValueError('Exact original model row/name identity differs')
 row,record=selected[0];results={}
 with tempfile.TemporaryDirectory(prefix='coh-rigid-legacy-') as directory:
  temp=Path(directory)
  for kind in fixture.KINDS:(temp/(kind+'.geo')).write_bytes(fixture.geo(kind))
  sources=[HERE/'tests/test_rigid_legacy.c',HERE/'coh_wr_rigid.c',HERE.parent/'assets/coh_asset_loader.c',HERE.parent/'assets/coh_asset_geo.c',HERE.parent/'renderer/coh_renderer.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
  paths=[*sources,HERE/'coh_wr_rigid.h',HERE/'tests/rigid_legacy_fixture.py',HERE/'tests/rigid_fixture.py',HERE/'rigid-atlas-v0-pins.json',HERE/'rigid-source-pins.json',HERE/'check_rigid_legacy.py',ROOT/'upstream/ouroboros/Utilities/GetVrml/src/output.c',source,ROOT/'upstream/ouroboros/Common/seq/anim.h',ROOT/'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/components/gridpoly.h',HERE.parent/'assets/coh_asset_geo.h',HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'renderer/coh_renderer.h',HERE.parent/'renderer/coh_renderer_shaders.h',HERE/'coh_world_render.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/src/byte_reader.h',ROOT/'native-android/tools/material_fixture/original_delta_check.py']
  source_hashes={str(p.relative_to(ROOT)):sha(p) for p in paths}
  source_revision=run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip()
  flags=['-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-I',ROOT/'native-android/include']
  for mode,extra in [('release',['-O2']),('address',['-O1','-g','-fsanitize=address','-no-pie']),('undefined',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   exe=temp/mode;run(['cc',*flags,*extra,*sources,'-lz','-lm','-lcrypto','-pthread','-o',exe]);results[mode]=json.loads(run([exe,temp,a.actual_geo,temp/('authored-'+mode),temp/('actual-'+mode)],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
  consumer=original_record(oracle_output,record,names,materials)
  original=module('rigid_original_delta',ROOT/'native-android/tools/material_fixture/original_delta_check.py');(temp/'delta.c').write_bytes(original.original_c(source));run(['cc','-std=c11','-O0','-fno-strict-aliasing','-shared','-fPIC',temp/'delta.c','-o',temp/'delta.so'])
  lib=C.CDLL(str(temp/'delta.so'));lib.uncompressDeltas.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_int]
  packets={}
  for name,streams,vertices,triangles,parts in [('actual',[record[132+i*12:144+i*12] for i in range(4)],90,56,1),('authored',None,4,2,2)]:
   decoded=[]
   for i in range(4):
    if streams:
     packed,unpacked,off=struct.unpack('<3I',streams[i]);data=payload[off:off+(packed or unpacked)];data=zlib.decompress(data) if packed else data
     if len(data)!=unpacked:raise ValueError('Actual channel inflate bounds')
    else:data=base.delta((base.INDICES,base.POSITIONS,base.NORMALS,base.UV)[i],2 if i==3 else 3,i==0)
    count=triangles if i==0 else vertices;stride=2 if i==3 else 3;encoded=C.create_string_buffer(data+b'\0'*16);out=C.create_string_buffer(count*stride*4)
    if lib.uncompressDeltas(out,encoded,stride,count,int(i==0))!=len(data):raise ValueError('Original delta byte consumption')
    decoded.append(struct.unpack('<'+('I' if i==0 else 'f')*(count*stride),out.raw))
   expected=bytearray()
   for part in range(parts):
    for vertex in range(vertices):
     uv=decoded[3][vertex*2:vertex*2+2];v=struct.unpack('<f',struct.pack('<f',1-uv[1]))[0];expected+=struct.pack('<14f',*decoded[1][vertex*3:vertex*3+3],*decoded[2][vertex*3:vertex*3+3],uv[0],v,uv[0],v,1,1,1,1)
    indices=decoded[0] if parts==1 else decoded[0][part*3:part*3+3];expected+=struct.pack('<'+'I'*len(indices),*indices)
   for mode in results:
    if (temp/(name+'-'+mode)).read_bytes()!=expected:raise ValueError('Rigid packet differs from original source deltas/partitions/Vflip')
   packets[name]=hashlib.sha256(expected).hexdigest()
  if {str(p.relative_to(ROOT)):sha(p) for p in paths}!=source_hashes or sha(a.actual_geo)!=pin['sha256']:raise ValueError('Inputs changed during qualification')
  proof={'passed':not a.require_original32 or consumer['original_consumer_executed'],'original32_required':a.require_original32,'source_revision':source_revision,'source_inputs_unchanged':True,'source_sha256':source_hashes,'actual_body':pin,'modes':results,'original_readModel':consumer,'original_delta_sha256_lf':original.FUNCTION_SHA,'packets_sha256':packets,'android_build':False,'android_execution':False,'physical_thor':False,'source_generation_established':False,'material_fixture_only':True,'world_authority':False}
  if a.output.exists():raise ValueError('Fresh proof path required')
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':proof['passed'],'results':results,'original32bit_readModel':consumer['original_consumer_executed']}))
  if not proof['passed']:raise SystemExit(1)
if __name__=='__main__':main()
