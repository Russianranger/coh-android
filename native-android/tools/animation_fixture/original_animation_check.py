#!/usr/bin/env python3
"""Execute original animation/math functions on real encoded .anim inputs.

Linux-host scalar original kernels, not the full Win32 client or Android. Native
runtime parity covers every reachable bone at integer/fractional frames; JSON
locals feed a separately implemented Python hierarchy/socket golden generator.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,os,re,shlex,struct,subprocess,sys,tempfile
sys.path.insert(0,str(Path(__file__).parent))
from _types import Rig,Pose,configure
ROOT=Path(__file__).resolve().parents[2]
FRAMES=[1.,1.5,5.25,12.5,24.5,25.]
def sha(b):return hashlib.sha256(b).hexdigest()
def require(v,s):
 if not v:raise ValueError(s)
def span(b,o,n):require(0<=o<=len(b) and 0<=n<=len(b)-o,'Original file span outside buffer');return b[o:o+n]
def u32(b,o):return struct.unpack('<I',span(b,o,4))[0]
def f32(v):return C.c_float(v).value
def extract(text,name):
 match=re.search(r'^(?:static\s+)?(?:INLINEDBG\s+)?(?:void|int|F32)\s+'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',text,re.M)
 require(match is not None,'Original function missing: '+name);start=match.start();begin=text.index('{',match.start());depth=1;i=begin+1
 while depth:
  if text[i]=='{':depth+=1
  elif text[i]=='}':depth-=1
  i+=1
 return text[start:i]+'\n'
FUNCTIONS=[('animtrackanimate.c','initLookUpTable'),('animtrackanimate.c','unPack5ByteQuat'),('netcomp.c','unpackQuatElemQuarterPi'),('animtrackanimate.c','animExpand5ByteQuat'),('animtrackanimate.c','animExpandNonLinearQuat'),('animtrackanimate.c','animExpand8ByteQuat'),('animtrackanimate.c','animExpand6BytePosition'),('Quat.c','quatNormalize'),('Quat.c','quatInterp'),('Quat.c','quatToMat'),('mathutil.c','posInterp'),('animtrackanimate.c','animCalcTrackIdxs'),('animtrackanimate.c','deriveMinAndMaxRotKeys'),('animtrackanimate.c','deriveMinAndMaxPosKeys'),('animtrackanimate.c','animGetRotationValue'),('animtrackanimate.c','animGetPositionValue'),('seqskeleton.c','getBaseRotation'),('seqskeleton.c','getBasePosition'),('mathutil.h','mulMat4Inline'),('mathutil.h','mulVecMat4'),('seqsequence.c','seqCycleFrame')]
PATHS={'animtrackanimate.c':'Common/seq/animtrackanimate.c','animtrackanimate.h':'Common/seq/animtrackanimate.h','Quat.c':'libs/UtilitiesLib/src/utils/Quat.c','mathutil.c':'libs/UtilitiesLib/src/utils/mathutil.c','mathutil.h':'libs/UtilitiesLib/include/utilitieslib/utils/mathutil.h','netcomp.c':'libs/UtilitiesLib/src/network/netcomp.c','seqskeleton.c':'Common/seq/seqskeleton.c','seqsequence.c':'Common/seq/seqsequence.c'}
PREAMBLE=r'''#include <stdint.h>
#include <string.h>
#include <math.h>
#include <assert.h>
typedef float F32;typedef uint8_t U8;typedef uint32_t U32;typedef int16_t S16;typedef uint16_t U16;typedef float Quat[4];typedef float Vec3[3];typedef float Mat3[3][3];typedef float Mat4[4][3];
#define INLINEDBG
#define LOOKUPSIZE12BIT 4096
#define QERROR 0.001
#define HALFPI 1.57079632679489661923
#define QUARTERPI 0.78539816339744830962
#define SIZE_OF_ROTKEY_COMPRESSED_TO_5_BYTES 5
#define SIZE_OF_UNCOMPRESSED_POSKEY 12
#define SIZE_OF_POSKEY_COMPRESSED_TO_6_BYTES 6
#define EFACTOR_8BYTE_QUAT 0.0001
#define EFACTOR_6BYTE_POS 0.00003125
#define POSITION_UNCOMPRESSED 8
#define POSITION_COMPRESSED_TO_6_BYTES 16
#define ROTATION_COMPRESSED_TO_5_BYTES 2
#define ROTATION_COMPRESSED_TO_8_BYTES 4
#define ROTATION_UNCOMPRESSED 1
#define ROTATION_COMPRESSED_NONLINEAR 128
#define POS_BIGGEST 2000000
#define quatX(q) ((q)[0])
#define quatY(q) ((q)[1])
#define quatZ(q) ((q)[2])
#define quatW(q) ((q)[3])
#define SQR(x) ((x)*(x))
#define fsqrt(x) (float)sqrt(x)
#define copyQuat(s,d) memcpy((d),(s),16)
#define copyVec3(s,d) memcpy((d),(s),12)
#define subVec3(a,b,c) do{for(int z=0;z<3;z++)(c)[z]=(a)[z]-(b)[z];}while(0)
#define scaleVec3(a,b,c) do{for(int z=0;z<3;z++)(c)[z]=(a)[z]*(b);}while(0)
#define addVec3(a,b,c) do{for(int z=0;z<3;z++)(c)[z]=(a)[z]+(b)[z];}while(0)
#define scaleVec4(a,b,c) do{for(int z=0;z<4;z++)(c)[z]=(a)[z]*(b);}while(0)
static int finiteVec4(const float *a){return isfinite(a[0])&&isfinite(a[1])&&isfinite(a[2])&&isfinite(a[3]);}
static int finiteVec3(const float *a){return isfinite(a[0])&&isfinite(a[1])&&isfinite(a[2]);}
static int vec4IsZero(const float *a){return a[0]==0&&a[1]==0&&a[2]==0&&a[3]==0;}
typedef struct {const void *rot_idx,*pos_idx;U16 rot_fullkeycount,pos_fullkeycount,rot_count,pos_count;char id,flags;unsigned short pack_pad;} BoneAnimTrack;
static F32 table[LOOKUPSIZE12BIT];static int table_inited;U32 glob_eidx[4];int emissing;
'''
WRAPPERS=r'''
static BoneAnimTrack track(U8 *rot,U8 *pos,int rf,int pf,int rc,int pc,int flags){BoneAnimTrack t={rot,pos,(U16)rf,(U16)pf,(U16)rc,(U16)pc,0,(char)flags,0};return t;}
void original_local(U8 *rot,U8 *pos,int rf,int pf,int rc,int pc,int flags,float frame,int base,float out[7]){
 BoneAnimTrack t=track(rot,pos,rf,pf,rc,pc,flags);
 if(base){animExpand5ByteQuat(rot,out);getBasePosition(&t,out+4);}
 else{int whole=(int)frame;float fraction=frame-(float)whole;animGetRotationValue(whole,fraction,&t,out,1);animGetPositionValue(whole,fraction,&t,out+4,1);}
}
void original_matrix(const float q[4],const float p[3],float rows[12]){Mat3 m;quatToMat(q,m);for(int r=0;r<3;r++){for(int c=0;c<3;c++)rows[r*4+c]=m[c][r];rows[r*4+3]=p[r];}}
void original_base_matrix(U8 *rot,U8 *pos,int rf,int pf,int rc,int pc,int flags,float rows[12]){BoneAnimTrack t=track(rot,pos,rf,pf,rc,pc,flags);Mat3 m;Vec3 p;getBaseRotation(&t,m);getBasePosition(&t,p);for(int r=0;r<3;r++){for(int c=0;c<3;c++)rows[r*4+c]=m[c][r];rows[r*4+3]=p[r];}}
void original_cycle(float *frame,float *previous,int first,int last){seqCycleFrame(frame,previous,first,last);}
void original_math(const float a[12],const float b[12],const float point_in[3],float compose_rows[12],float point_out[3]){
 Mat4 aa,bb,cc;for(int r=0;r<3;r++)for(int c=0;c<4;c++){aa[c][r]=a[r*4+c];bb[c][r]=b[r*4+c];}
 mulMat4Inline(aa,bb,cc);mulVecMat4(point_in,aa,point_out);for(int r=0;r<3;r++)for(int c=0;c<4;c++)compose_rows[r*4+c]=cc[c][r];
}
'''
def source_code(directory):
 pins=json.loads(Path(__file__).with_name('original-source-pins.json').read_text());texts={}
 for name,relative in PATHS.items():
  path=(directory/name) if directory else ROOT.parent/'upstream/ouroboros'/relative
  raw=path.read_bytes().replace(b'\r\n',b'\n');require(sha(raw)==pins['sources'][name]['sha256_lf'],'Original source hash differs: '+name);texts[name]=raw.decode()
 snippets=[]
 for name,func in FUNCTIONS:
  code=extract(texts[name],func);require(sha(code.encode())==pins['functions'][func]['sha256_lf'],'Original function hash differs: '+func);snippets.append(code)
 require('#define QERROR 0.001' in texts['animtrackanimate.h'],'QERROR contract differs')
 return PREAMBLE+'\n'.join(snippets)+WRAPPERS,pins

def raw_tracks(raw):
 header=u32(raw,0);count=u32(raw,528);off=u32(raw,524);result={}
 require(596<=header<=len(raw) and 0<count<=99,'Original track envelope invalid')
 for i in range(count):
  record=span(raw,off+i*20,20);ro,po,rf,pf,rc,pc,ident,flags,_=struct.unpack('<II4HBBH',record)
  require(ident not in result and ident<99 and flags in (10,18) and 0<rc<=rf<=4096 and 0<pc<=pf<=4096,'Original track metadata invalid')
  result[ident]={'rotation':span(raw,ro,rf*5),'position':span(raw,po,pf*(12 if flags==10 else 6)),'rf':rf,'pf':pf,'rc':rc,'pc':pc,'flags':flags}
 return result

def hierarchy(base):
 off=u32(base,540);h=span(base,off,1204);seen={};order=[]
 def chain(node,parent):
  while node!=-1:
   require(0<=node<99 and node not in seen,'Original hierarchy cycle/duplicate')
   child,nxt,ident=struct.unpack('<3i',span(h,4+node*12,12));require(ident==node,'Original hierarchy ID differs');seen[node]=parent;order.append(node)
   if child!=-1:chain(child,node)
   node=nxt
 chain(struct.unpack_from('<i',h)[0],-1)
 return seen,order

def sample(lib,t,frame,base=False):
 r=(C.c_uint8*(len(t['rotation'])+16))();p=(C.c_uint8*(len(t['position'])+16))();C.memmove(r,t['rotation'],len(t['rotation']));C.memmove(p,t['position'],len(t['position']));out=(C.c_float*7)();lib.original_local(r,p,t['rf'],t['pf'],t['rc'],t['pc'],t['flags'],C.c_float(frame),int(base),out);return list(out)

def matrix(lib,value):
 q=(C.c_float*4)(*value[:4]);p=(C.c_float*3)(*value[4:]);out=(C.c_float*12)();lib.original_matrix(q,p,out);return list(out)
def original_math(lib,a,b,p):
 aa=(C.c_float*12)(*a);bb=(C.c_float*12)(*b);pp=(C.c_float*3)(*p);out=(C.c_float*12)();point=(C.c_float*3)();lib.original_math(aa,bb,pp,out,point);return list(out),list(point)
def compare(actual,expected,label):
 require(len(actual)==len(expected),label+' count differs');maximum=0.
 for x,y in zip(actual,expected):
  error=abs(x-y);maximum=max(maximum,error);require(error<=2e-6+2e-6*abs(y),f'{label}: {x} vs {y}')
 return maximum

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rig',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--report',required=True,type=Path);p.add_argument('--source-directory',type=Path);p.add_argument('--compiler',default=os.environ.get('CC','cc'));a=p.parse_args()
 raw=a.rig.read_bytes();require(len(raw)>=128 and raw[:8]==b'COHRIG01','Rig container invalid');bo,bn,mo,mn,po,pc,socket=struct.unpack_from('<7I',raw,16);base=span(raw,bo,bn);motion=span(raw,mo,mn);base_t=raw_tracks(base);motion_t=raw_tracks(motion);parents,order=hierarchy(base);ids=sorted(parents);require(len(ids)==60 and len(motion_t)==44,'Selected real fixture coverage differs');code,pins=source_code(a.source_directory)
 with tempfile.TemporaryDirectory(prefix='coh-original-animation-') as temp:
  t=Path(temp);c=t/'original.c';c.write_text(code);so=t/'oracle.so';build=subprocess.run([*shlex.split(a.compiler),'-std=c11','-O0','-ffp-contract=off','-fno-strict-aliasing','-fPIC','-shared',str(c),'-lm','-o',str(so)],capture_output=True,text=True);require(build.returncode==0,build.stderr)
  lib=C.CDLL(str(so));lib.original_local.argtypes=[C.POINTER(C.c_uint8),C.POINTER(C.c_uint8),C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,C.c_float,C.c_int,C.POINTER(C.c_float)];lib.original_local.restype=None
  fp=C.POINTER(C.c_float);lib.original_matrix.argtypes=[fp,fp,fp];lib.original_matrix.restype=None
  lib.original_math.argtypes=[fp,fp,fp,fp,fp];lib.original_math.restype=None
  lib.original_cycle.argtypes=[fp,fp,C.c_int,C.c_int];lib.original_cycle.restype=None
  lib.original_base_matrix.argtypes=[C.POINTER(C.c_uint8),C.POINTER(C.c_uint8),C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,fp];lib.original_base_matrix.restype=None
  nlib=t/'native.so';subprocess.run([*shlex.split(a.compiler),'-std=c11','-O2','-ffp-contract=off','-fPIC','-shared',str(ROOT/'animation/coh_animation.c'),'-lm','-o',str(nlib)],check=True)
  native=configure(C.CDLL(str(nlib)));mem=(C.c_uint8*len(raw)).from_buffer_copy(raw);rig=Rig();require(native.coh_animation_parse(mem,len(raw),C.byref(rig))==0,'Native real rig rejected')
  require(rig.node_count==len(ids) and all(rig.parent[i]==parents[i] for i in ids),'Native hierarchy differs from independently read source hierarchy')
  first={i:sample(lib,base_t[i],0,True) for i in ids};initial_motion={i:sample(lib,motion_t[i],0,False) for i in motion_t};delta={i:[f32(initial_motion[i][4+j]-first[i][4+j]) for j in range(3)] for i in motion_t}
  identity=[1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.];zero=[0.,0.,0.];btt={};base_matrix_comparisons=0
  for i in order:
   btt[i]=[0.,0.,0.] if parents[i]<0 or i==0 else [f32(btt[parents[i]][j]+first[i][4+j]) for j in range(3)]
   compare(list(rig.bind_translation[i]),btt[i],f'Original source translation accumulation bone{i}')
   t0=base_t[i];r=(C.c_uint8*(len(t0['rotation'])+16)).from_buffer_copy(t0['rotation']+bytes(16));p0=(C.c_uint8*(len(t0['position'])+16)).from_buffer_copy(t0['position']+bytes(16));m=(C.c_float*12)();lib.original_base_matrix(r,p0,t0['rf'],t0['pf'],t0['rc'],t0['pc'],t0['flags'],m)
   compare(list(m),matrix(lib,first[i]),f'Original getBaseRotation matrix bone{i}');base_matrix_comparisons+=12
  palette_ids=list(struct.unpack('<'+'I'*pc,span(raw,po,pc*4)))
  math_counts={'base_matrix_scalars':base_matrix_comparisons,'bind_translation_scalars':len(ids)*3,'world_scalars':0,'bpt_scalars':0,'socket_palette_scalars':0};math_maximum=0.
  comparisons=0;maximum=0.;all_frames=sorted(set([float(x) for x in range(26)]+FRAMES+[25.5]));samples=[]
  for frame in all_frames:
   pose=Pose();require(native.coh_animation_sample(C.byref(rig),C.c_float(frame),C.byref(pose))==0,'Native sampler rejected original key time')
   local=[]
   values={}
   for i in ids:
    value=sample(lib,motion_t[i],frame) if i in motion_t else list(first[i])
    if i in motion_t:
     for j in range(3):value[4+j]=f32(value[4+j]-delta[i][j])
    actual=list(pose.rotation[i])+list(pose.position[i])
    for x,y in zip(actual,value):
     error=abs(x-y);maximum=max(maximum,error);comparisons+=1;require(error<=2e-6+2e-6*abs(y),f'Original/native local mismatch bone{i} frame{frame}: {x} vs {y}')
    local.append({'id':i,'rotation':value[:4],'position':value[4:]})
    values[i]=value
   worlds={};bpts={}
   for i in order:
    m=matrix(lib,values[i]);worlds[i]=m if parents[i]<0 else original_math(lib,worlds[parents[i]],m,zero)[0]
    math_maximum=max(math_maximum,compare(list(pose.world_rows[i]),worlds[i],f'Original/native world bone{i} frame{frame}'));math_counts['world_scalars']+=12
    bpts[i]=list(worlds[i]);translated=original_math(lib,worlds[i],identity,[-x for x in btt[i]])[1]
    for j in range(3):bpts[i][j*4+3]=translated[j]
   # Socket0 has zero btt: this API yields each original bpt directly. Batch
   # full60 hierarchy through the runtime's bounded15-bone upload interface.
   for start in range(0,len(ids),15):
    batch=ids[start:start+15];bones=(C.c_uint32*len(batch))(*batch);rows=(C.c_float*(len(batch)*12))();require(native.coh_animation_palette(C.byref(rig),C.byref(pose),0,bones,len(batch),rows)==0,'Native bpt extraction failed')
    for j,i in enumerate(batch):math_maximum=max(math_maximum,compare(list(rows[j*12:(j+1)*12]),bpts[i],f'Original/native bpt bone{i} frame{frame}'));math_counts['bpt_scalars']+=12
   expected=[]
   for i in palette_ids:
    m=list(bpts[i]);translated=original_math(lib,m,identity,btt[socket])[1]
    for j in range(3):m[j*4+3]=translated[j]
    expected.extend(m)
   rows=(C.c_float*(pc*12))();require(native.coh_animation_default_palette(C.byref(rig),C.byref(pose),rows)==0,'Native source socket palette failed');math_maximum=max(math_maximum,compare(list(rows),expected,f'Original/native socket palette frame{frame}'));math_counts['socket_palette_scalars']+=pc*12
   if frame in FRAMES:samples.append({'frame':frame,'local':local})
  clock_cases=[]
  for current,timestep,rate in [(25.,0.,1.),(24.,1.,1.),(25.,.5,1.),(24.,2.,1.),(25.,25.,1.),(25.,24.,1.),(1.,100.,1.),(24.,2.,0.),(24.,2.,2.)]:
   advance=f32(current+f32(rate*timestep));expected=C.c_float(advance);previous=C.c_float(current)
   wrapped=advance>rig.last_frame
   if wrapped:lib.original_cycle(C.byref(expected),C.byref(previous),int(rig.first_frame),int(rig.last_frame));require(previous.value==-1.,'Original cycle previous frame marker differs')
   next_frame=C.c_float(-1234.);require(native.coh_animation_step(C.byref(rig),current,timestep,rate,1,C.byref(next_frame))==0,'Native source-cycle comparison failed');compare([next_frame.value],[expected.value],'Original/native clock')
   clock_cases.append({'current':current,'timestep_frames':timestep,'effective_rate':rate,'wrapped':wrapped,'expected':expected.value})
  output={'format':1,'bone_count':99,'source_commit':pins['source_commit'],'rig_sha256':sha(raw),'scope':'original scalar key sampling plus source animDelta; neutral rig, no gameplay sequencer transitions','hierarchy':[{'id':i,'parent':parents[i]} for i in ids],'base_local':[{'id':i,'rotation':first[i][:4],'position':first[i][4:]} for i in ids],'samples':samples,'socket_id':socket,'palette_ids':list(struct.unpack('<'+'I'*pc,span(raw,po,pc*4))),'clock':{'first_frame':rig.first_frame,'last_frame':rig.last_frame,'ticks_per_second':rig.ticks_per_second,'effective_rate':1.,'scope':'controlled neutral rate; full movement-derived scaling not integrated'}}
  unexercised=['unpackQuatElemQuarterPi','animExpandNonLinearQuat','animExpand8ByteQuat']
  report={'format':1,'status':'passed','scope':'exact original animation/math scalar functions on Linux host with portable type/macro shims; neutral hierarchy and socket orchestration follows source formulas','win32_game_execution':False,'android_device_execution':False,'rig_sha256':sha(raw),'base_sha256':sha(base),'motion_sha256':sha(motion),'original_sources':pins,'generated_oracle_sha256':sha(code.encode()),'native_source_sha256':sha((ROOT/'animation/coh_animation.c').read_bytes()),'native_header_sha256':sha((ROOT/'animation/coh_animation.h').read_bytes()),'base_tracks':len(base_t),'motion_tracks':len(motion_t),'reachable_bones':len(ids),'outer_roots':[i for i in ids if parents[i]==-1],'checked_frames':all_frames,'scalar_comparisons':comparisons,'maximum_absolute_error':maximum,'original_math_comparisons':math_counts,'original_math_maximum_absolute_error':math_maximum,'original_cycle_cases':clock_cases,'executed_original_functions':[fn for _,fn in FUNCTIONS if fn not in unexercised],'compiled_but_unexercised_original_functions':unexercised,'reference_frames':FRAMES,'used_key_formats':{'rotation':'linear5-byte (flags2)','position':'rawfloat3 (flags8) and compressedS16x3 /32000 (flags16)'},'legacy_compiler_diagnostics':build.stderr[:4000]}
 for path,data in ((a.output,output),(a.report,report)):
  path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+'\n')
 print(json.dumps({'status':'passed','reference':str(a.output),'report':str(a.report),'scalar_comparisons':comparisons,'maximum_absolute_error':maximum}))
if __name__=='__main__':main()
