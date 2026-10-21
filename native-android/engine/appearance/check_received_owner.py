#!/usr/bin/env python3
"""Bounded native received-Huge owner, optional authentic source archive replay.

No source archive, packet, generated mesh, image or raw output is tracked.
The same native owner used by Android is exercised through read-only FDs.
"""
import argparse,ctypes as C,hashlib,importlib.util,json,os,subprocess,sys,tempfile,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;NATIVE=HERE.parents[1]
spec=importlib.util.spec_from_file_location('received_owner_prepare',HERE/'prepare_received_costume.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
U=C.c_uint32;Q=C.c_uint64;Z=C.c_size_t
Read=C.CFUNCTYPE(C.c_int,C.c_void_p,Q,C.c_void_p,Z)
class Source(C.Structure):_fields_=[('read',Read),('context',C.c_void_p),('size',Q),('generation',U)]
class Inputs(C.Structure):_fields_=[('snapshot',C.POINTER(p.Snapshot)),('rig',C.POINTER(p.bridge.animation.Rig)),('archives',Source*2),('parent',Q),('epoch',Q),('entity',U),('cancel',p.a.Cancel)]
class ArchiveFd(C.Structure):_fields_=[('fd',C.c_int),('offset',Q),('bytes',Q)]
class Stats(C.Structure):_fields_=[(n,Q) for n in ('cpu','texture','gpu','renderer','peak','reads','read_bytes','frames','draws','epoch')]+[(n,U) for n in ('entity','body','parts','vertices','indices','textures','fallbacks')]+[('height',C.c_float),('missing',C.c_char*256)]
def build(work,mode,headers):
 sources=[HERE/name for name in ('coh_appearance.c','coh_appearance_adapters.c','coh_appearance_mesh.c','coh_appearance_render.c','coh_appearance_costume.c','coh_appearance_actor.c','coh_appearance_scales.c','coh_appearance_material.c','coh_received_costume.c','coh_received_costume_fd.c')]
 sources += [NATIVE/name for name in ('character/coh_character.c','engine/assets/coh_asset_geo.c','engine/assets/coh_asset_loader.c','engine/assets/coh_asset_zip.c','src/coh_assets.c','src/coh_dds.c','material-probe/app/src/main/cpp/coh_mesh.c','engine/renderer/coh_renderer.c','engine/renderer/coh_renderer_gles.c')]
 helper=work/'allocation.c';helper.write_text("""#include <stddef.h>
#include "coh_received_costume.h"
#include <string.h>
#include <zlib.h>
void*__real_malloc(size_t);void*__real_calloc(size_t,size_t);void __real_free(void*);
static size_t calls,fail,live;
void*__wrap_malloc(size_t n){if(++calls==fail)return 0;void*p=__real_malloc(n);if(p)live++;return p;}
void*__wrap_calloc(size_t n,size_t m){if(++calls==fail)return 0;void*p=__real_calloc(n,m);if(p)live++;return p;}
void __wrap_free(void*p){if(p)live--;__real_free(p);}
void test_failure(size_t n){calls=0;fail=n;}
size_t test_calls(void){return calls;}size_t test_live(void){return live;}
static void put(unsigned char*p,unsigned v){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(v>>(i*8));}
int test_scale_metadata(void){unsigned char h[381]={0},file[1024]={0},work[381+65536];size_t pos=165;put(h,8);put(h+4,4);put(h+8,5);memcpy(h+20,"HIPS",5);put(h+25+136,1);float scale=1.25f;for(unsigned i=0;i<3;i++)memcpy(h+pos+92+i*4,&scale,4);put(h+pos+204,8);uLongf packed=sizeof file-16;if(compress2(file+8,&packed,h,sizeof h,6)!=Z_OK)return 1;put(file,(unsigned)packed+4);put(file+4,sizeof h);size_t bytes=(size_t)packed+20;CohAssetGeo geo,old;memset(&geo,0xa5,sizeof geo);old=geo;if(coh_asset_geo_open((CohBytes){file,bytes},work,sizeof work,1,&geo)!=COH_INVALID||memcmp(&geo,&old,sizeof geo))return 2;if(coh_asset_geo_open_scales((CohBytes){file,bytes},work,sizeof work,1,&geo)!=COH_OK)return 3;CohAssetGeoModel m;if(coh_asset_geo_model(&geo,0,&m)!=COH_INVALID||coh_asset_geo_scale_model(&geo,0,&m)!=COH_OK||m.scale[0]!=1.25f)return 4;return 0;}
size_t owner_abi(unsigned i){size_t a[]={sizeof(CohReceivedCostumeInputs),sizeof(CohReceivedCostumeStats),sizeof(CohOriginalCostumeSnapshot),sizeof(CohAnimationRig)};return i<4?a[i]:0;}
""")
 flags=['-O2'] if mode=='release' else ['-O1','-g','-fno-omit-frame-pointer','-fsanitize='+('address' if mode=='asan' else 'undefined')]
 lib=work/('owner-'+mode+'.so');command=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-fno-fast-math','-fstack-usage','-I'+str(NATIVE/'include'),'-I'+str(HERE),'-I'+str(headers),*flags,'-shared','-fPIC',*map(str,sources),str(helper),'-Wl,--wrap=malloc,--wrap=calloc,--wrap=free','-l:libGL.so.1','-lz','-lm','-o',str(lib)];subprocess.run(command,check=True);return lib

def checks(args):
 lib=p.bridge.renderer.load(args.library,gles=True);p.configure(lib)
 defs=p.definitions(HERE.parents[2]);rows=[]
 for d in defs:
  names=[getattr(d,k).decode() for k in ('name','geometry_name','texture_name','base_name')]
  rows.append('{'+','.join('"'+n+'"' for n in names)+',{'+str(d.socket[0])+'u,'+str(d.socket[1])+'u},'+str(d.socket_count)+'u,'+str(d.dont_clear)+'u},')
 assert [r.rstrip(',') for r in rows]==[r.rstrip(',') for r in (HERE/'huge_body_parts.inc').read_text().splitlines()[1:]]
 lib.owner_abi.argtypes=[U];lib.owner_abi.restype=Z
 assert [lib.owner_abi(i) for i in range(4)]==[C.sizeof(Inputs),C.sizeof(Stats),C.sizeof(p.Snapshot),C.sizeof(p.bridge.animation.Rig)]
 lib.coh_received_costume_prepare.argtypes=[C.POINTER(Inputs),C.POINTER(C.c_void_p),C.POINTER(Stats)]
 lib.coh_received_costume_destroy.argtypes=[C.POINTER(C.c_void_p)]
 lib.coh_received_costume_stats.argtypes=[C.c_void_p];lib.coh_received_costume_stats.restype=Stats
 lib.coh_received_costume_bind.argtypes=[C.c_void_p,U,C.POINTER(U),U]
 lib.coh_received_costume_texture.argtypes=[C.c_void_p,U,C.POINTER(p.api.asset.Bytes),C.POINTER(U),C.POINTER(U),C.POINTER(C.c_char_p)]
 lib.coh_received_costume_draws.argtypes=[C.c_void_p,C.POINTER(C.c_float),C.POINTER(C.c_float),C.POINTER(C.c_float),C.POINTER(C.POINTER(p.bridge.renderer.Draw)),C.POINTER(Z)]
 lib.coh_received_costume_fds_open.argtypes=[C.POINTER(ArchiveFd),C.POINTER(C.c_void_p)]
 lib.coh_received_costume_fds_sources.argtypes=[C.c_void_p,C.POINTER(Source)]
 lib.coh_received_costume_fds_destroy.argtypes=[C.POINTER(C.c_void_p)]
 lib.test_failure.argtypes=[Z];lib.test_calls.restype=lib.test_live.restype=Z
 snapshot=p.Snapshot();snapshot.body=4;snapshot.count=28;rig=p.bridge.animation.Rig();reads=[];fd=-1
 def read(_,offset,dst,count):
  reads.append(count)
  try:raw=os.pread(fd,count,offset)
  except OSError:return 6
  if len(raw)!=count:return 6
  C.memmove(dst,raw,count);return 0
 callback=Read(read);empty=(Source*2)(Source(callback,None,22,1),Source())
 input=Inputs(C.pointer(snapshot),C.pointer(rig),empty,0,1,125,p.a.Cancel());owner=C.c_void_p();stats=Stats()
 assert lib.test_scale_metadata()==0
 lib.test_failure(0);assert lib.coh_received_costume_prepare(C.byref(input),C.byref(owner),C.byref(stats))!=0 and not owner.value and lib.test_live()==0
 input.parent=96<<20;lib.test_failure(0);assert lib.coh_received_costume_prepare(C.byref(input),C.byref(owner),C.byref(stats))==4 and lib.test_calls()==0
 input.parent=0
 assert lib.coh_received_costume_prepare(C.byref(input),C.cast(C.byref(input),C.POINTER(C.c_void_p)),C.byref(stats))==1
 assert lib.coh_received_costume_prepare(C.byref(input),C.byref(owner),C.cast(C.byref(owner),C.POINTER(Stats)))==1
 # Real FD source owner: dup lifetime, immutable identity, alias, cleanup.
 with tempfile.TemporaryDirectory(prefix='coh-actor-fds-') as temp:
  archive_path=Path(temp)/'archive.zip'
  with zipfile.ZipFile(archive_path,'w') as z:z.writestr('test',b'body')
  d=os.open(archive_path,os.O_RDONLY|os.O_CLOEXEC);size=os.fstat(d).st_size
  descriptors=(ArchiveFd*2)(ArchiveFd(d,0,size),ArchiveFd(d,0,size));fd_owner=C.c_void_p();sources=(Source*2)()
  assert lib.coh_received_costume_fds_open(descriptors,C.byref(fd_owner))==7 and not fd_owner.value and lib.test_live()==0
  os.chmod(archive_path,0o400);before=len(os.listdir('/proc/self/fd'))
  assert lib.coh_received_costume_fds_open(descriptors,C.byref(fd_owner))==0
  assert lib.coh_received_costume_fds_sources(fd_owner,sources)==0
  assert lib.coh_received_costume_fds_sources(fd_owner,C.cast(fd_owner,C.POINTER(Source)))==1
  os.close(d);d=-1;buf=C.create_string_buffer(4);assert sources[0].read(sources[0].context,0,buf,4)==0 and buf.raw==b'PK\x03\x04'
  os.chmod(archive_path,0o600);assert sources[0].read(sources[0].context,0,buf,4)==7
  lib.coh_received_costume_fds_destroy(C.byref(fd_owner));assert not fd_owner.value and lib.test_live()==0 and len(os.listdir('/proc/self/fd'))==before-1
 result={'fd_dup_mutation_alias_cleanup':True,'abi':True,'no_source_substitute':True,'aggregate_preflight':True,'alias_preserves_output':True,'scale_only_metadata_no_mesh_admission':True}
 if not args.archive:return result
 raw=args.snapshot.read_bytes();snapshot=p.checked_snapshot(raw);rig_raw=args.rig.read_bytes();p.module('received_owner_rig_identity',HERE/'recover_huge_rig.py').recover(rig_raw)
 rig_bytes=(C.c_uint8*len(rig_raw)).from_buffer_copy(rig_raw);assert lib.coh_animation_parse(rig_bytes,len(rig_raw),C.byref(rig))==0
 pins=p.source_pins(args.source_pins)
 with zipfile.ZipFile(args.archive) as archive:
  for entry in archive.infolist():
   if entry.is_dir():continue
   pin=pins[entry.filename.casefold()]
   assert entry.file_size==pin['bytes'];digest=hashlib.sha256()
   with archive.open(entry) as stream:
    while chunk:=stream.read(65536):digest.update(chunk)
   assert digest.hexdigest()==pin['sha256']
 fd=os.open(args.archive,os.O_RDONLY|os.O_CLOEXEC)
 try:
  input.snapshot=C.pointer(snapshot);input.rig=C.pointer(rig);input.archives[0].size=os.fstat(fd).st_size
  polls=[0,False]
  def poll(_):polls[0]+=1;return int(polls[1])
  callback_cancel=p.a.CancelFn(poll);input.cancel=p.a.Cancel(callback_cancel,None)
  lib.test_failure(0);status=lib.coh_received_costume_prepare(C.byref(input),C.byref(owner),C.byref(stats))
  if status:raise ValueError(f'Actual native actor status {status}: {bytes(stats.missing).decode()}')
  allocation_calls=lib.test_calls();assert stats.parts==13 and stats.body==4 and stats.epoch==1 and stats.entity==125
  assert stats.fallbacks==4 and abs(stats.height-1.0497)<1e-6 and stats.peak<=96<<20
  assert max(reads)<=65557
  result['actual']={n:getattr(stats,n) for n in ('cpu','texture','gpu','renderer','peak','read_bytes','parts','vertices','indices','textures','fallbacks','height')};result['actual']['snapshot_sha256']=hashlib.sha256(raw).hexdigest();result['actual']['max_read']=max(reads)
  # Owner-only aliases refuse without altering retained state.
  assert lib.coh_received_costume_bind(owner,1,C.cast(owner,C.POINTER(U)),stats.textures)==1
  width=U();height=U();name=C.c_char_p();span=p.api.asset.Bytes()
  assert lib.coh_received_costume_texture(owner,0,C.cast(rig_bytes,C.POINTER(p.api.asset.Bytes)),C.byref(width),C.byref(height),C.byref(name))==1
  assert lib.coh_received_costume_texture(owner,0,C.cast(owner,C.POINTER(p.api.asset.Bytes)),C.byref(width),C.byref(height),C.byref(name))==1
  # Build actual render packets using fake nonzero handles; no GPU required.
  polls_after_prepare=polls[0];polls[1]=True
  handles=(U*stats.textures)(*range(1,stats.textures+1));assert lib.coh_received_costume_bind(owner,1,handles,len(handles))==0
  view=(C.c_float*12)(1,0,0,0,1,0,0,0,1,0,0,0);projection=p.bridge.renderer.identity();position=(C.c_float*3)(0,0,0);draws=C.POINTER(p.bridge.renderer.Draw)();count=Z()
  assert lib.coh_received_costume_draws(owner,view,projection,position,C.byref(draws),C.byref(count))==0 and count.value==13
  assert polls[0]==polls_after_prepare # preparation callback is no longer borrowed
  polls[1]=False
  packets=[]
  for i in range(count.value):
   draw=draws[i];vertices=(p.bridge.renderer.Vertex*draw.geometry.vertex_count).from_buffer_copy(C.string_at(draw.geometry.vertices,draw.geometry.vertex_count*C.sizeof(p.bridge.renderer.Vertex)));indices=(U*draw.geometry.index_count).from_buffer_copy(C.string_at(draw.geometry.indices,draw.geometry.index_count*4));copy=p.bridge.renderer.Draw.from_buffer_copy(draw);copy.geometry.vertices=vertices;copy.geometry.indices=indices;packets.append((copy,vertices,indices))
  if args.capture:
   args.capture.mkdir(exist_ok=True,parents=True);result['actual']['capture']=capture(lib,owner,stats,packets,args.capture)
  lib.coh_received_costume_destroy(C.byref(owner));assert not owner.value and lib.test_live()==0
  # Every actual native allocation failure is clean and leaves outputNULL.
  for failure in range(1,allocation_calls+1):
   lib.test_failure(failure);status=lib.coh_received_costume_prepare(C.byref(input),C.byref(owner),C.byref(stats));assert status!=0 and not owner.value and lib.test_live()==0,(failure,status,owner.value,lib.test_calls(),lib.test_live(),allocation_calls)
  result['allocation_failure_positions']=allocation_calls
  polls[1]=True;lib.test_failure(0);assert lib.coh_received_costume_prepare(C.byref(input),C.byref(owner),C.byref(stats))==5 and not owner.value and lib.test_live()==0
  polls[1]=False;result['cancel_cleanup_and_temporary_callback_retired']=True
  lib.test_failure(0);input.parent=(96<<20)-1;assert lib.coh_received_costume_prepare(C.byref(input),C.byref(owner),C.byref(stats))==4 and not owner.value and lib.test_live()==0
 finally:
  if owner.value:lib.coh_received_costume_destroy(C.byref(owner))
  os.close(fd)
 return result

def capture(lib,owner,stats,packets,output):
 # Same concrete production GLES backend; caller-owned textures use explicitly
 # limited LINEAR/REPEAT/base-level diagnostic quality, not effective TexOpts.
 from PIL import Image
 bridge=p.bridge;gapi=bridge.renderer;U=C.c_uint32;F=C.c_float
 xyz=[[v.position[k] for _,vertices,_ in packets for v in vertices] for k in range(3)];lo=list(map(min,xyz));hi=list(map(max,xyz));center=[(a+b)*.5 for a,b in zip(lo,hi)];extent=max(hi[1]-lo[1],(hi[0]-lo[0])*1.25);scale=1.65/extent
 matrix=gapi.identity();matrix[0]=scale*1.25;matrix[5]=scale;matrix[10]=-.08;matrix[12]=-center[0]*matrix[0];matrix[13]=-center[1]*matrix[5];matrix[14]=-center[2]*matrix[10]
 capture_bytes=512*640*10+2*max(C.sizeof(vertices)+C.sizeof(indices) for _,vertices,indices in packets)
 if stats.peak+capture_bytes>96<<20:raise ValueError("Host capture exceeds existing96MiB cap")
 identity=(F*12)(1,0,0,0,1,0,0,0,1,0,0,0);position=(F*3)();cycles=[]
 for cycle in range(2):
  e=bridge.gpu.EGL();gl=e.g;target=U();fbo=U();depth=U();backend=gapi.Backend();gles=C.c_void_p();renderer=C.c_void_p();
  handles=(U*stats.textures)()
  try:
   for n,r,a in [('glGenRenderbuffers',None,[C.c_int,C.POINTER(U)]),('glBindRenderbuffer',None,[U,U]),('glRenderbufferStorage',None,[U,U,C.c_int,C.c_int]),('glFramebufferRenderbuffer',None,[U,U,U,U]),('glDeleteRenderbuffers',None,[C.c_int,C.POINTER(U)])]:e.gf(n,r,a)
   target=e.texture(512,640);gl.glGenFramebuffers(1,C.byref(fbo));gl.glBindFramebuffer(0x8d40,fbo);gl.glFramebufferTexture2D(0x8d40,0x8ce0,0xde1,target,0);gl.glGenRenderbuffers(1,C.byref(depth));gl.glBindRenderbuffer(0x8d41,depth);gl.glRenderbufferStorage(0x8d41,0x81a5,512,640);gl.glFramebufferRenderbuffer(0x8d40,0x8d00,0x8d41,depth);assert gl.glCheckFramebufferStatus(0x8d40)==0x8cd5
   for i in range(stats.textures):
    span=p.api.asset.Bytes();w=U();h=U();name=C.c_char_p();assert lib.coh_received_costume_texture(owner,i,C.byref(span),C.byref(w),C.byref(h),C.byref(name))==0
    handles[i]=e.texture(w.value,h.value,C.string_at(span.data,span.size)).value
   assert lib.coh_received_costume_bind(owner,1,handles,len(handles))==0
   assert lib.coh_renderer_gles_create(stats.vertices,stats.indices,C.byref(gles),C.byref(backend))==0
   assert lib.coh_renderer_create(C.byref(gapi.Config(120,stats.vertices,stats.indices,3)),C.byref(backend),C.byref(renderer))==0
   lib.coh_renderer_surface_lost(renderer,1,1)
   gl.glViewport(0,0,512,640);gl.glClearColor(.035,.045,.065,1);gl.glClear(0x4000|0x100)
   draws=C.POINTER(gapi.Draw)();count=Z();assert lib.coh_received_costume_draws(owner,identity,matrix,position,C.byref(draws),C.byref(count))==0
   assert lib.coh_renderer_begin(renderer,1)==0
   for i in range(count.value):assert lib.coh_renderer_submit(renderer,C.byref(draws[i]))==0
   assert lib.coh_renderer_flush(renderer,gapi.Cancel())==0
   pixels=C.create_string_buffer(512*640*4);gl.glReadPixels(0,0,512,640,0x1908,0x1401,pixels);assert gl.glGetError()==0
   raw=pixels.raw;visible=sum(raw[i:i+4]!=raw[:4] for i in range(0,len(raw),4));assert visible>100
   image=Image.frombytes('RGBA',(512,640),raw).transpose(Image.Transpose.FLIP_TOP_BOTTOM);image.save(output/('huge-material-context'+str(cycle+1)+'.png'))
   cycles.append({'context':cycle+1,'draws':count.value,'visible_pixels':visible,'rgba_sha256':hashlib.sha256(raw).hexdigest(),'driver':e.identity})
  finally:
   if renderer.value:lib.coh_renderer_destroy(renderer)
   if gles.value:lib.coh_renderer_gles_destroy(gles,1)
   gl.glDeleteTextures(len(handles),handles);gl.glDeleteFramebuffers(1,C.byref(fbo));gl.glDeleteRenderbuffers(1,C.byref(depth));gl.glDeleteTextures(1,C.byref(target));e.close()
 assert cycles[0]['rgba_sha256']==cycles[1]['rgba_sha256']
 return {'host_only':True,'authored_scales_applied':True,'material_profile':'original noMULTI/noBUMP automatic DUAL fallback; LINEAR REPEAT noMip diagnostic sampler; Ready/base inspection','contexts':cycles,'minimum':lo,'maximum':hi,'source_payload_peak_with_capture_bytes':stats.peak+capture_bytes}

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--mode',choices=['release','asan','ubsan','all'],default='all');parser.add_argument('--headers',type=Path,default=Path('/usr/include'));parser.add_argument('--library',type=Path)
 for n in ('archive','snapshot','rig','source-pins','capture'):parser.add_argument('--'+n,type=Path)
 args=parser.parse_args()
 if args.library:print(json.dumps(checks(args)));return
 result={}
 with tempfile.TemporaryDirectory(prefix='coh-received-owner-') as temp:
  for mode in ['release','asan','ubsan'] if args.mode=='all' else [args.mode]:
   library=build(Path(temp),mode,args.headers);command=[sys.executable,str(Path(__file__).resolve()),'--library',str(library)];env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
   if mode=='asan':env['LD_PRELOAD']=subprocess.check_output(['cc','-print-file-name=libasan.so'],text=True).strip()
   for n in ('archive','snapshot','rig','source_pins','capture'):
    v=getattr(args,n)
    if v and (n!='capture' or mode=='release'):command+=['--'+n.replace('_','-'),str(v)]
   result[mode]=json.loads(subprocess.check_output(command,env=env,text=True))
 print(json.dumps(result))
if __name__=='__main__':main()
