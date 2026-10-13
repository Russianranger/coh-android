#!/usr/bin/env python3
"""Qualify raw-key native animation with independent hierarchy/skin goldens.

The reference contains sampled original-host local values and independently
prepared Python hierarchy/socket/skin results. It does not drive the runtime:
native C decodes raw original .anim bytes from COHRIG01 at each requested time.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,math,os,shlex,struct,subprocess,sys,tempfile
sys.path.insert(0,str(Path(__file__).parent))
from _types import Rig,Pose,configure
sys.path.insert(0,str(Path(__file__).parent.parent/'material_fixture'))
from native_mesh_check import Mesh,Vertex,Skinned,load as mesh_configure
ROOT=Path(__file__).resolve().parents[2]
ANIMATION=ROOT/'animation'
MESH=ROOT/'material-probe/app/src/main/cpp'
def require(v,s):
 if not v:raise ValueError(s)
def sha(b):return hashlib.sha256(b).hexdigest()
def u32(b,o):return struct.unpack_from('<I',b,o)[0]
def bytes_of(value):return C.string_at(C.byref(value),C.sizeof(value))
def floats(b,o,n):
 require(0<=o<=len(b) and 0<=n<=(len(b)-o)//4,'Reference float span invalid')
 result=struct.unpack_from('<'+'f'*n,b,o);require(all(math.isfinite(v) for v in result),'Reference contains nonfinite values');return result
def parse(lib,blob):
 mem=(C.c_uint8*len(blob)).from_buffer_copy(blob);rig=Rig();status=lib.coh_animation_parse(mem,len(blob),C.byref(rig));return status,mem,rig
def compare(actual,expected,label,stats):
 require(len(actual)==len(expected),label+' scalar count differs')
 for i,(x,y) in enumerate(zip(actual,expected)):
  require(math.isfinite(x) and math.isfinite(y),label+' contains nonfinite scalar')
  error=abs(x-y);stats['maximum_absolute_error']=max(stats['maximum_absolute_error'],error);stats['scalar_comparisons']+=1
  require(error<=2e-5+2e-5*abs(y),f'{label} scalar{i}: {x} vs {y}')
def stats():return {'scalar_comparisons':0,'maximum_absolute_error':0.}

def read_reference(path):
 b=path.read_bytes();require(len(b)>=128 and b[:8]==b'COHAGL01','Reference magic/size invalid')
 fields=struct.unpack_from('<20I',b,8)
 version,header,nf,nb,np,nv,ids_o,parents_o,pids_o,btt_o,cases_o,stride,total,socket,flags,local_o,world_o,bpt_o,palette_o,mesh_o=fields
 require(version==1 and header==128 and 1<=nf<=64 and 1<=nb<=99 and 1<=np<=15 and 1<=nv<=65536 and flags==0 and not any(b[100:128]),'Reference limits/reserved fields invalid')
 require(ids_o==128 and parents_o==ids_o+nb*4 and pids_o==parents_o+nb*4 and btt_o==pids_o+np*4 and cases_o==btt_o+nb*12,'Reference global offsets invalid')
 require(local_o==4 and world_o==local_o+nb*28 and bpt_o==world_o+nb*48 and palette_o==bpt_o+nb*48 and mesh_o==palette_o+np*48 and stride==mesh_o+nv*24,'Reference case offsets invalid')
 require(total==len(b)==cases_o+nf*stride,'Reference size differs')
 ids=list(struct.unpack_from('<'+'I'*nb,b,ids_o));parents=list(struct.unpack_from('<'+'i'*nb,b,parents_o));pids=list(struct.unpack_from('<'+'I'*np,b,pids_o))
 require(ids==sorted(set(ids)) and max(ids)<99 and all(p==-1 or p in ids for p in parents) and len(set(pids))==np and all(i in ids for i in pids) and socket in ids,'Reference hierarchy identity invalid')
 cases=[]
 for k in range(nf):
  start=cases_o+k*stride;frame=floats(b,start,1)[0]
  cases.append({'frame':frame,'local':floats(b,start+local_o,nb*7),'world':floats(b,start+world_o,nb*12),'bpt':floats(b,start+bpt_o,nb*12),'palette':floats(b,start+palette_o,np*12),'mesh':floats(b,start+mesh_o,nv*6)})
 return {'sha256':sha(b),'bytes':len(b),'ids':ids,'parents':parents,'palette_ids':pids,'socket':socket,'vertices':nv,'btt':floats(b,btt_o,nb*3),'clock':floats(b,88,3),'cases':cases}

def real_check(lib,rig_path,reference,mesh_path):
 raw=rig_path.read_bytes();status,mem,rig=parse(lib,raw);require(status==0,'Native real raw rig rejected')
 ids=reference['ids'];require(rig.node_count==len(ids) and sorted(rig.order[:rig.node_count])==ids,'Runtime/reference reachable bones differ')
 require([rig.parent[i] for i in ids]==reference['parents'],'Runtime/reference parents differ')
 require(list(rig.palette_ids[:rig.palette_count])==reference['palette_ids'] and rig.socket_id==reference['socket'],'Runtime/reference palette/socket identity differs')
 require((rig.ticks_per_second,rig.first_frame,rig.last_frame)==reference['clock'],'Runtime/reference source clock metadata differs')
 require(list(rig.bind_translation[0])==[0.,0.,0.] and list(rig.bind_translation[61])==[0.,0.,0.] and rig.parent[0]==rig.parent[61]==-1,'Both original outer roots must have zero bind translation')
 require(rig.base.track_count==60 and rig.motion.track_count==44 and rig.base.tracks[72].present and not rig.motion.tracks[72].present,'Real hierarchy/missing socket motion coverage differs')
 mesh_raw=mesh_path.read_bytes();mesh_mem=(C.c_uint8*len(mesh_raw)).from_buffer_copy(mesh_raw);mesh=Mesh();require(lib.coh_mesh_parse(mesh_mem,len(mesh_raw),C.byref(mesh))==0,'Native original canonical mesh rejected')
 require(mesh.vertex_count==reference['vertices'] and mesh.bone_count==rig.palette_count,'Mesh/reference sizes differ')
 for k,ident in enumerate(reference['palette_ids']):
  out=C.c_uint32();require(lib.coh_mesh_global_bone(C.byref(mesh),k,C.byref(out))==0 and out.value==ident,'Mesh/rig palette order differs')
 vertices=[]
 for i in range(mesh.vertex_count):
  v=Vertex();require(lib.coh_mesh_vertex(C.byref(mesh),i,C.byref(v))==0,'Native vertex getter failed');vertices.append(v)
 stages={name:stats() for name in ('bind_translation','local','world','bpt','socket_palette','gpu_contract_skin')}
 compare([v for i in ids for v in rig.bind_translation[i]],reference['btt'],'Python/source bind translations',stages['bind_translation'])
 poses=[];palettes=[]
 for case in reference['cases']:
  frame=case['frame'];pose=Pose();require(lib.coh_animation_sample(C.byref(rig),frame,C.byref(pose))==0,'Native raw sampler rejected frame')
  compare([v for i in ids for v in (*pose.rotation[i],*pose.position[i])],case['local'],f'Original-host local frame{frame}',stages['local'])
  compare([v for i in ids for v in pose.world_rows[i]],case['world'],f'Python world frame{frame}',stages['world'])
  bpt=[]
  for start in range(0,len(ids),15):
   batch=ids[start:start+15];bones=(C.c_uint32*len(batch))(*batch);rows=(C.c_float*(len(batch)*12))();require(lib.coh_animation_palette(C.byref(rig),C.byref(pose),0,bones,len(batch),rows)==0,'Native inverse-bind palette failed');bpt.extend(rows)
  compare(bpt,case['bpt'],f'Python inverse-bind bpt frame{frame}',stages['bpt'])
  palette=(C.c_float*(rig.palette_count*12))();require(lib.coh_animation_default_palette(C.byref(rig),C.byref(pose),palette)==0,'Native real socket72 palette failed')
  compare(list(palette),case['palette'],f'Python socket palette frame{frame}',stages['socket_palette']);palettes.append(bytes(palette))
  skinned=[]
  for i,v in enumerate(vertices):
   out=Skinned();require(lib.coh_mesh_skin_vertex(C.byref(v),palette,rig.palette_count,C.byref(out))==0,f'Native source-GPU skin failed vertex{i}');skinned.extend((*out.position,*out.normal))
  compare(skinned,case['mesh'],f'Python source-GPU skin frame{frame}',stages['gpu_contract_skin']);poses.append(frame)
 require(len(set(palettes))>=3,'Real animation fixture does not change bone palettes meaningfully')
 formats={}
 for label,file in (('base',rig.base),('motion',rig.motion)):
  formats[label]={'linear5_rotation_tracks':sum(t.present and t.flags&2!=0 for t in file.tracks),'rawfloat3_position_tracks':sum(t.present and t.flags&8!=0 for t in file.tracks),'compressedS16_position_tracks':sum(t.present and t.flags&16!=0 for t in file.tracks)}
 return {'rig_sha256':sha(raw),'reference_sha256':reference['sha256'],'mesh_sha256':sha(mesh_raw),'raw_rig_bytes':len(raw),'base_tracks':rig.base.track_count,'motion_tracks':rig.motion.track_count,'reachable_bones':rig.node_count,'outer_roots':[i for i in ids if rig.parent[i]==-1],'socket_id':rig.socket_id,'palette_ids':reference['palette_ids'],'frames':poses,'key_format_coverage':formats,'stages':stages,'scalar_comparisons':sum(s['scalar_comparisons'] for s in stages.values()),'tolerance':'2e-5 absolute + 2e-5 relative'},mem,rig

def rejection_tests(lib,raw,rig):
 bo,bn,mo,mn,po,pc=struct.unpack_from('<6I',raw,16);base=raw[bo:bo+bn];motion=raw[mo:mo+mn];bt=bo+u32(base,524);mt=mo+u32(motion,524);ho=bo+u32(base,540);header=u32(base,0)
 pack=lambda v:struct.pack('<I',v)
 f=lambda v:struct.pack('<f',v)
 first_id=raw[bt+16];second_id=raw[bt+36]
 raw_position_record=next(bt+i*20 for i in range(u32(base,528)) if raw[bt+i*20+17]&8)
 raw_position=bo+u32(raw,raw_position_record+4)
 ro=bo+u32(raw,bt)
 mutations={
  'magic':(0,b'X'),'version':(8,pack(2)),'header_size':(12,pack(127)),'base_offset':(16,pack(129)),
  'base_size_wrap':(20,pack(0xffffffff)),'motion_offset_overlap':(24,pack(128)),'motion_size_wrap':(28,pack(0xffffffff)),
  'palette_overlap':(32,pack(128)),'empty_palette':(36,pack(0)),'palette_limit':(36,pack(16)),'socket_unreachable':(40,pack(next(i for i in range(99) if rig.parent[i]==-2))),
  'flags':(44,pack(1)),'first_negative':(48,f(-1)),'last_equal_first':(52,f(1)),'fps_nonfinite':(56,f(float('nan'))),'total_size':(60,pack(len(raw)-1)),'reserved':(124,pack(1)),
  'base_header_short':(bo,pack(595)),'base_header_oversize':(bo,pack(bn+1)),'track_array_outside':(bo+524,pack(0xfffffffc)),'no_tracks':(bo+528,pack(0)),'track_limit':(bo+528,pack(100)),
  'hierarchy_outside':(bo+540,pack(0xfffffffc)),'hierarchy_track_overlap':(bo+540,pack(u32(base,524))),
  'unterminated_name':(bo+4,b'A'*256),'base_link_mismatch':(bo+260,b'Z'),'motion_base_link_mismatch':(mo+260,b'Z'),
  'unsupported_quaternion_format':(bt+17,bytes([12])),'packed_track_padding':(bt+18,b'\x01\x00'),'bone_id_limit':(bt+16,bytes([99])),'duplicate_bone_id':(bt+36,bytes([first_id])),
  'rotation_empty':(bt+8,b'\x00\x00'),'rotation_limit':(bt+8,struct.pack('<H',4097)),'rotation_frame_empty':(bt+12,b'\x00\x00'),'rotation_frame_overrun':(bt+12,struct.pack('<H',struct.unpack_from('<H',raw,bt+8)[0]+1)),
  'position_empty':(bt+10,b'\x00\x00'),'position_frame_overrun':(bt+14,struct.pack('<H',struct.unpack_from('<H',raw,bt+10)[0]+1)),
  'rotation_into_header':(bt,pack(header-1)),'position_span_wrap':(bt+4,pack(0xfffffffc)),'rotation_top_reserved':(ro,b'\xff'),'rotation_negative_radicand':(ro,b'\x0f\xff\xff\xff\xff'),
  'position_nan':(raw_position,f(float('nan'))),'position_limit':(raw_position,f(2000001.)),
  'hierarchy_root_id':(ho,pack(1)),'hierarchy_node_identity':(ho+4+first_id*12+8,pack(99)),
  'hierarchy_child_limit':(ho+4,pack(99)),'hierarchy_child_cycle':(ho+4,pack(0)),'hierarchy_sibling_cycle':(ho+8,pack(0)),
  'hierarchy_unreachable_outer_root':(ho+8,pack(0xffffffff)),
  'motion_track_array_outside':(mo+524,pack(0xffffffff)),'motion_unsupported_keys':(mt+17,bytes([130]))
 }
 names=[]
 for name,(offset,value) in mutations.items():
  bad=bytearray(raw);bad[offset:offset+len(value)]=value;mem=(C.c_uint8*len(bad)).from_buffer_copy(bad);out=Rig();C.memset(C.byref(out),0x5a,C.sizeof(out));before=bytes_of(out)
  require(lib.coh_animation_parse(mem,len(bad),C.byref(out))!=0,name+' incorrectly admitted');require(bytes_of(out)==before,name+' changed failed output');names.append(name)
 for name,data in [('empty',b''),('trailing_byte',raw+b'\0'),('short_header',raw[:127]),('final_byte_missing',raw[:-1])]:
  mem=(C.c_uint8*len(data)).from_buffer_copy(data);out=Rig();C.memset(C.byref(out),0x5a,C.sizeof(out));before=bytes_of(out);require(lib.coh_animation_parse(mem,len(data),C.byref(out))!=0,name);require(bytes_of(out)==before,name+' changed failed output');names.append(name)
 for frame in (-1.,float('nan'),float('inf'),1000001.):
  out=Pose();C.memset(C.byref(out),0x5a,C.sizeof(out));before=bytes_of(out);require(lib.coh_animation_sample(C.byref(rig),frame,C.byref(out))!=0,'Invalid sample time admitted');require(bytes_of(out)==before,'Invalid sample time changed output');names.append('sample_'+str(frame))
 pose=Pose();require(lib.coh_animation_sample(C.byref(rig),1.5,C.byref(pose))==0,'Control sample rejected')
 unused=next(i for i in range(99) if rig.parent[i]==-2)
 for name,socket,bones,count in [('socket_limit',99,[9],1),('socket_unreachable',unused,[9],1),('bone_limit',72,[99],1),('bone_unreachable',72,[unused],1),('no_palette',72,[9],0),('palette_limit',72,[9]*16,16)]:
  ids=(C.c_uint32*len(bones))(*bones);out=(C.c_float*192)();C.memset(out,0x5a,C.sizeof(out));before=bytes(out);require(lib.coh_animation_palette(C.byref(rig),C.byref(pose),socket,ids,count,out)!=0,name);require(bytes(out)==before,name+' changed failed output');names.append(name)
 corrupt=Pose.from_buffer_copy(bytes_of(pose));corrupt.world_rows[9][0]=float('nan');out=(C.c_float*36)();C.memset(out,0x5a,C.sizeof(out));before=bytes(out);require(lib.coh_animation_default_palette(C.byref(rig),C.byref(corrupt),out)!=0,'Nonfinite world admitted');require(bytes(out)==before,'Nonfinite palette changed output');names.append('palette_nonfinite_world')
 return {'checks':len(names),'rejected_cases':names,'failed_outputs_unchanged':True}

def clock_tests(lib,rig):
 cases=[(25.,0.,1.,1,0,25.),(24.,1.,1.,1,0,25.),(25.,.5,1.,1,0,1.5),(24.,2.,1.,1,0,2.),(25.,25.,1.,1,0,1.),(25.,24.,1.,1,0,25.),(1.,100.,1.,1,0,1.),(24.,2.,0.,1,0,24.),(24.,2.,2.,1,0,4.),(24.,2.,1.,0,2,None),(24.,1.,1.,0,0,25.),(0.,1.,1.,1,1,None),(26.,0.,1.,1,1,None),(24.,-1.,1.,1,1,None),(24.,1.,-1.,1,1,None),(24.,1.,float('nan'),1,1,None),(float('nan'),1.,1.,1,1,None),(24.,float('inf'),1.,1,1,None),(24.,1.,1.,2,1,None)]
 result=[]
 for current,dt,rate,cycle,status,expected in cases:
  out=C.c_float(-1234.);actual=lib.coh_animation_step(C.byref(rig),current,dt,rate,cycle,C.byref(out));require(actual==status,'Clock status differs');require(out.value==(-1234. if expected is None else expected),'Clock output or unchanged failure contract differs')
  result.append({'current':str(current) if not math.isfinite(current) else current,'timestep_frames':str(dt) if not math.isfinite(dt) else dt,'effective_rate':str(rate) if not math.isfinite(rate) else rate,'cycle':cycle,'expected_status':status,'expected_frame':expected})
 return {'checks':len(result),'cases':result,'scope':'controlled effective rate; strict >last, subtract range once, then reset if still beyond; noncycle end status2 leaves output unchanged'}

def sanitizer_check(path,compiler,temp):
 program=temp/'animation_sanitizer.c';exe=temp/'animation_sanitizer'
 program.write_text(r'''#include "coh_animation.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void check(const unsigned char *p,size_t n,int must_fail){
 CohAnimationRig r;memset(&r,0x5a,sizeof r);CohAnimationRig before=r;
 int status=coh_animation_parse(p,n,&r);if(must_fail&&!status)abort();
 if(status){if(memcmp(&r,&before,sizeof r))abort();return;}
 CohAnimationPose pose;float palette[COH_ANIMATION_PALETTE*12];
 if(coh_animation_sample(&r,1.5f,&pose)||coh_animation_default_palette(&r,&pose,palette))abort();
 if(coh_animation_sample(&r,25.5f,&pose)||coh_animation_default_palette(&r,&pose,palette))abort();
 float next;if(coh_animation_step(&r,r.first_frame,.5f,1,1,&next))abort();
}
int main(int argc,char **argv){
 if(argc!=2)return 2;FILE *f=fopen(argv[1],"rb");if(!f)return 2;
 if(fseek(f,0,SEEK_END))return 2;long length=ftell(f);if(length<128||length>8*1024*1024)return 2;rewind(f);
 size_t n=(size_t)length;unsigned char *raw=malloc(n);if(!raw||fread(raw,1,n,f)!=n)return 2;fclose(f);check(raw,n,0);size_t checks=1;
 for(size_t i=0;i<n;i++){unsigned char *a=malloc(i+1);if(!a)abort();unsigned char *p=a+1;if(i)memcpy(p,raw,i);check(p,i,1);free(a);checks++;}
 unsigned char *a=malloc(n+1);if(!a)abort();unsigned char *p=a+1;memcpy(p,raw,n);
 for(size_t i=0;i<n;i++){unsigned char old=p[i];p[i]=old^1;check(p,n,0);p[i]=old^255;check(p,n,0);p[i]=old;checks+=2;}
 free(a);free(raw);printf("{\"status\":\"passed\",\"checks\":%zu,\"real_input_bytes\":%zu,\"sanitizers\":[\"address\",\"undefined\"],\"scope\":\"exact-allocation truncations and two byte mutations at every raw-rig offset; unaligned encoded inputs plus sample/socket/clock on admitted variants\"}\n",checks,n);return 0;
}
''')
 subprocess.run([*shlex.split(compiler),'-std=c11','-O1','-g','-ffp-contract=off','-fno-omit-frame-pointer','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I',str(ANIMATION),str(program),str(ANIMATION/'coh_animation.c'),'-lm','-o',str(exe)],check=True)
 env=dict(os.environ);env['ASAN_OPTIONS']='detect_leaks=0:abort_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
 run=subprocess.run([str(exe),str(path.resolve())],capture_output=True,text=True,env=env);require(run.returncode==0,f'Sanitizer harness failed exit{run.returncode}: '+run.stderr[:12000]);require(not run.stderr,'Sanitizer diagnostics: '+run.stderr[:12000]);result=json.loads(run.stdout);result['leak_detection']=False;return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rig',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--mesh',type=Path,help='Default: mesh.bin beside --reference');p.add_argument('--output',type=Path,required=True);p.add_argument('--compiler',default=os.environ.get('CC','cc'));a=p.parse_args();mesh=a.mesh or a.reference.with_name('mesh.bin');reference=read_reference(a.reference)
 with tempfile.TemporaryDirectory(prefix='coh-animation-check-') as directory:
  temp=Path(directory);so=temp/'runtime.so';subprocess.run([*shlex.split(a.compiler),'-std=c11','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror','-fPIC','-shared',str(ANIMATION/'coh_animation.c'),str(MESH/'coh_mesh.c'),'-lm','-o',str(so)],check=True)
  lib=mesh_configure(configure(C.CDLL(str(so))));real,mem,rig=real_check(lib,a.rig,reference,mesh)
  report={'format':1,'status':'passed','scope':'bounded native raw-key decoder, neutral hierarchy/socket assembly and source-GPU-contract CPU skinning versus original-host locals and independent Python goldens','android_device_execution':False,'full_game_sequencer':False,'native_sources':{str(path.relative_to(ROOT)):sha(path.read_bytes()) for path in (ANIMATION/'coh_animation.c',ANIMATION/'coh_animation.h',MESH/'coh_mesh.c',MESH/'coh_mesh.h')},'real_asset':real,'malformed_tests':rejection_tests(lib,a.rig.read_bytes(),rig),'clock_tests':clock_tests(lib,rig),'sanitizer_tests':sanitizer_check(a.rig,a.compiler,temp)}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':'passed','output':str(a.output),'scalar_comparisons':real['scalar_comparisons'],'stages':real['stages'],'malformed_checks':report['malformed_tests']['checks'],'clock_checks':report['clock_tests']['checks'],'sanitizer_checks':report['sanitizer_tests']['checks']}))
if __name__=='__main__':main()
