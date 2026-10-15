#!/usr/bin/env python3
"""Focused actual GLES admission/cleanup tests for the new stream diagnostics.

The integration driver builds --library from the current sources. This is
host software-GPU evidence; it does not qualify Android or physical hardware.
"""
import argparse,ctypes as C,json,hashlib,sys
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--library',type=Path,required=True);parser.add_argument('--accepted-assets',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'engine/renderer/tests'))
from bindings import *
from gpu_check import EGL,parse_corpus
class Qualification(C.Structure):_fields_=[('tf_components',Q),('tf_mismatches',Q),('visible_pixels',Q),('max_error',F)]
e=EGL();g=e.g
lib=load(args.library,gles=True)
lib.coh_stream_qualify.argtypes=[C.c_void_p,C.POINTER(Draw),Z,C.POINTER(Qualification),C.c_void_p,Z]
lib.coh_stream_qualify.restype=C.c_int
for n,r,a in [('glGetIntegerv',None,[U,C.POINTER(C.c_int)]),('glGetIntegeri_v',None,[U,U,C.POINTER(C.c_int)]),('glGenSamplers',None,[C.c_int,C.POINTER(U)]),('glDeleteSamplers',None,[C.c_int,C.POINTER(U)]),('glBindSampler',None,[U,U]),('glPixelStorei',None,[U,C.c_int]),('glActiveTexture',None,[U]),('glGetBooleanv',None,[U,C.POINTER(C.c_uint8)]),('glColorMask',None,[C.c_uint8,C.c_uint8,C.c_uint8,C.c_uint8])]:e.gf(n,r,a)
parts,tex,refs,pins=parse_corpus(args.accepted_assets)
textures=[e.texture(w,h,data) for w,h,data in tex]
backend=Backend();driver=C.c_void_p();renderer=C.c_void_p()
assert lib.coh_renderer_gles_create(65536,196608,C.byref(driver),C.byref(backend))==0
assert lib.coh_renderer_create(C.byref(Config(64,65536,196608,3)),C.byref(backend),C.byref(renderer))==0
# Own caller target and deliberately unusual pack/scissor/color/activeunit state.
caller_target=e.texture(9,7);caller_fbo=U();g.glGenFramebuffers(1,C.byref(caller_fbo));g.glBindFramebuffer(0x8d40,caller_fbo);g.glFramebufferTexture2D(0x8d40,0x8ce0,0xde1,caller_target,0);assert g.glCheckFramebufferStatus(0x8d40)==0x8cd5
caller_read_target=e.texture(11,11);caller_read_fbo=U();g.glGenFramebuffers(1,C.byref(caller_read_fbo));g.glBindFramebuffer(0x8d40,caller_read_fbo);g.glFramebufferTexture2D(0x8d40,0x8ce0,0xde1,caller_read_target,0);assert g.glCheckFramebufferStatus(0x8d40)==0x8cd5
g.glBindFramebuffer(0x8ca9,caller_fbo);g.glBindFramebuffer(0x8ca8,caller_read_fbo)
g.glViewport(2,3,9,7)
pbo=U();g.glGenBuffers(1,C.byref(pbo));g.glBindBuffer(0x88eb,pbo);g.glBufferData(0x88eb,32,None,0x88e8)
for p,v in [(0x0d05,8),(0x0d02,300),(0x0d04,5),(0x0d03,4)]:g.glPixelStorei(p,v)
samplers=(U*3)();g.glGenSamplers(3,samplers)
for i,s in enumerate(samplers):g.glBindSampler(i,s)
g.glActiveTexture(0x84c2);g.glEnable(0x0c11);g.glColorMask(1,0,1,0)
def integer(p,n=1):
 a=(C.c_int*n)();g.glGetIntegerv(p,a);return list(a)
def restored():
 assert integer(0x8ca6)==[caller_fbo.value] and integer(0x8caa)==[caller_read_fbo.value]
 assert integer(0x0ba2,4)==[2,3,9,7]
 assert integer(0x88ed)==[pbo.value]
 for p,v in [(0x0d05,8),(0x0d02,300),(0x0d04,5),(0x0d03,4)]:assert integer(p)==[v]
 assert integer(0x84e0)==[0x84c2]
 for i in range(3):
  g.glActiveTexture(0x84c0+i);assert integer(0x8919)==[0]
 g.glActiveTexture(0x84c2)
 assert integer(0x0b74)==[0x0203] and integer(0x0b46)==[0x0900] and integer(0x0b45)==[0x0405]
 b=(C.c_uint8*4)();g.glGetBooleanv(0x0c23,b);assert list(b)==[1,0,1,0]
 assert g.glGetError()==0
vertices=[v for p in parts for v in p['vertices']]
lo=[min(v.position[k] for v in vertices) for k in range(3)];hi=[max(v.position[k] for v in vertices) for k in range(3)]
mat=identity();proj=identity()
for k in range(3):mat[12+k]=-(lo[k]+hi[k])/2;proj[k*5]=1.7/max(hi[k]-lo[k],1)
draws=(Draw*len(parts))()
for i,p in enumerate(parts):
 m=lib.coh_renderer_default_material(p['mode']);m.fog_params=V4(0,0,1000000,1);m.light=V3(.2,.1,.97);m.diffuse=V4(.4,.5,.7,1);m.ambient=V4(.1,.1,.1,1);m.specular=V3(.1,.1,.1);m.shininess=8
 m.textures[0]=Texture(textures[p['base']].value,1,1,1,1);m.textures[1]=Texture(textures[p['dual']].value,1,1,1,1)
 draws[i]=Draw(Geometry(p['vertices'],len(p['vertices']),p['indices'],len(p['indices']),i+1,0),m,mat,proj,0)
results=[]
for lighting in range(3):
 for d in draws:d.material.lighting=lighting
 stats=Qualification();error=C.create_string_buffer(1024)
 ok=lib.coh_stream_qualify(renderer,draws,len(draws),C.byref(stats),error,len(error))
 assert ok,error.value
 assert stats.tf_components==sum(len(p['vertices']) for p in parts)*12 and stats.tf_mismatches==0 and stats.visible_pixels>0 and stats.max_error<=.0001
 restored();results.append(dict(lighting=lighting,**{k:getattr(stats,k) for k,_ in Qualification._fields_}))
# Offscreen authentic geometry retains successful TF but fails actual visibility.
for d in draws:d.projection[12]=5
stats=Qualification();error=C.create_string_buffer(1024)
assert not lib.coh_stream_qualify(renderer,draws,len(draws),C.byref(stats),error,len(error)) and b'no visible pixels' in error.value,error.value
assert stats.tf_components and stats.tf_mismatches==0 and stats.visible_pixels==0
restored()
for d in draws:d.projection[12]=0
# Invalid source normal and oversized declarations fail without residual GL work.
normal=list(parts[0]['vertices'][0].normal);parts[0]['vertices'][0].normal=V3(0,0,0)
assert not lib.coh_stream_qualify(renderer,draws,len(draws),C.byref(stats),error,len(error)) and b'CPU vertex admission' in error.value,error.value
restored();parts[0]['vertices'][0].normal=V3(*normal)
count=draws[0].geometry.vertex_count;draws[0].geometry.vertex_count=200001
assert not lib.coh_stream_qualify(renderer,draws,len(draws),C.byref(stats),error,len(error)) and b'budget exceeded' in error.value,error.value
assert stats.tf_components==stats.tf_mismatches==stats.visible_pixels==0
draws[0].geometry.vertex_count=count
# A later invalid index must cancel earlier queued diagnostic draws before GPU execution.
original_index=parts[1]['indices'][0];parts[1]['indices'][0]=len(parts[1]['vertices']);before=lib.coh_renderer_stats(renderer)
assert not lib.coh_stream_qualify(renderer,draws,len(draws),C.byref(stats),error,len(error)) and b'backend visibility draw failed' in error.value,error.value
assert lib.coh_renderer_stats(renderer).queued==0 and lib.coh_renderer_stats(renderer).drawn==before.drawn
parts[1]['indices'][0]=original_index;restored()
# A renderer with queued external work is refused, preserving the queue.
assert lib.coh_renderer_begin(renderer,0)==0 and lib.coh_renderer_submit(renderer,C.byref(draws[0]))==0
assert not lib.coh_stream_qualify(renderer,draws,len(draws),C.byref(stats),error,len(error)) and b'idle renderer' in error.value
assert lib.coh_renderer_stats(renderer).queued==1
CALLBACK=C.CFUNCTYPE(C.c_int,C.c_void_p);cancel=CALLBACK(lambda _:1)
assert lib.coh_renderer_flush(renderer,Cancel(C.cast(cancel,C.c_void_p),None))==5
# After failures, repeat exact real mesh visibility successfully.
assert lib.coh_stream_qualify(renderer,draws,len(draws),C.byref(stats),error,len(error)),error.value
restored()
result={'passed':True,'host_software_gpu_only':True,'android_execution':False,'physical_thor':False,'identity':e.identity,'source_assets':pins,'actual_mesh_lighting_cases':results,'negative_cases':['offscreen_visibility','zero_source_normal','vertex_budget','external_queue_preserved','partial_submit_cancelled_before_draw'],'state_restoration_checked':['separate_read_draw_fbo','viewport','pack_buffer_alignment_row_skip','sampler_units_0_1_2_unbound','active_texture','depth_lequal_write_cw_back','color_mask'],'recovery_after_failures':True,'max_total_vertices':200000,'tf_components_per_vertex':12,'tf_tolerance':.0001,'sources':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/'session-client/app/src/main/cpp/session_stream_qualify.h',root/'session-client/app/src/main/cpp/session_stream_qualify.c']}}
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
lib.coh_renderer_destroy(renderer);lib.coh_renderer_gles_destroy(driver,1)
e.close()
