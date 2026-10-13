#!/usr/bin/env python3
"""Execute unchanged source morphology and animated-node functions on Wretch.

This is a Linux scalar source-kernel oracle, not full Win32 or original GPU
execution. Compatibility helpers select one clip, no transition, zero aiming.
Original raw-key and matrix kernels remain hash-pinned by the Phase7 oracle.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,importlib.util,json,os,re,shlex,struct,subprocess,tempfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
original=module('phase7_original_actor',HERE.parent/'animation_fixture/original_animation_check.py')
types=module('phase8_actor_types',HERE/'_types.py')
Rig,Pose,Morph,configure=types.Rig,types.Pose,types.Morph,types.configure
def require(v,s):
 if not v:raise ValueError(s)
def sha(b):return hashlib.sha256(b).hexdigest()
MORE=r'''
#define CLIENT 1
#define SHOW_TEMPLATE 123
#define NO_CHANGE 0
#define CHANGE_SINGLE 2
#define SEQMOVE_NOINTERP 8
#define BONEID_COUNT 99
#define BONEID_HIPS 0
#define BONEID_WAIST 1
#define BONEID_CHEST 2
#define BONEID_NECK 3
#define BONEID_HEAD 4
#define BONEID_COL_R 5
#define BONEID_COL_L 6
#define BONEID_LARMR 9
#define BONEID_LARML 10
#define BONEID_ULEGR 23
#define BONEID_ULEGL 24
#define BONEID_LLEGR 25
#define BONEID_LLEGL 26
#define BONEID_FOOTR 27
#define BONEID_FOOTL 28
#define BONEID_WEPL 41
#define BONEID_WEPR 42
#define BONEID_BOSOMR 68
#define BONEID_BOSOML 69
#define BONEID_BROW 73
#define BONEID_NOSE 78
#define kBodyType_Female 1
#define ABS(a) fabsf(a)
#define MINMAX(x,l,h) ((x)<(l)?(l):(x)>(h)?(h):(x))
#define xcase break; case
#define setVec3(v,x,y,z) do{(v)[0]=(x);(v)[1]=(y);(v)[2]=(z);}while(0)
#define setVec3same(v,x) setVec3(v,x,x,x)
#define copyMat3(s,d) memcpy((d),(s),36)
#define copyMat4(s,d) memcpy((d),(s),48)
typedef int BoneId;
typedef struct {Vec3 scale;} Model;
typedef struct {Model models[99];} ModelHeader;
typedef struct {Vec3 shoulderScaleSkinny,shoulderScaleFat,hipScale,neckScale,headScaleMax,headScaleMin;float legScaleRatio;} SeqType;
typedef struct {int flags;} Move;
typedef struct SeqInst {SeqType *type;float bonescale_ratio,shoulderScale,hipScale,legScale,armScale,headScales[3],neckScale;ModelHeader *bonescale_anm_skinny,*bonescale_anm_fat;int updated_appearance;Vec3 bone_scales[99],last_translations[99];Quat last_rotations[99];struct{Move *move;} animation;float currTargetingPitchVec[2],chestYaw,headYaw;} SeqInst;
typedef struct {SeqInst *seq;} Entity;
typedef struct {const BoneAnimTrack *bt;int anim_id;Vec3 animDelta;Mat4 mat;} GfxNode;
typedef struct {float fBoneScale,fShoulderScale,fHipScale,fLegScale,fArmScale,fWaistScale,fChestScale;union{float fHeadScales[3];float f3DScales[7][3];};int bodytype;} Appearance;
static struct {int game_mode,nointerpolation;} game_state;
static const Mat4 unitmat={{1,0,0},{0,1,0},{0,0,1},{0,0,0}};
static const Vec3 onevec3={1,1,1};
static Entity *playerPtr(void){return 0;}
static Entity *playerPtrForShell(int a){(void)a;return 0;}
static int bone_IdIsValid(int id){return id>=0&&id<99;}
static Model *animFindBoneInHeader(ModelHeader *header,int id){return &header->models[id];}
static void seqClearBoneScales(SeqInst *s){for(int i=0;i<99;i++)setVec3same(s->bone_scales[i],1.f);}
static const float *seqBoneScale(SeqInst *s,int id){return s->bone_scales[id];}
static void seqSetBoneScale(SeqInst *s,int id,const Vec3 v){copyVec3(v,s->bone_scales[id]);}
static int seqBoneNeedsRotationBlending(SeqInst *s,int id){(void)s;(void)id;return 0;}
static int seqBoneNeedsTranslationBlending(SeqInst *s,int id){(void)s;(void)id;return 0;}
static float *seqLastTranslations(SeqInst *s,int id){return s->last_translations[id];}
static void seqSetLastRotations(SeqInst *s,int id,const Quat q){copyQuat(q,s->last_rotations[id]);}
static void seqSetBoneAnimationStored(SeqInst *s,int id){(void)s;(void)id;}
static void animInterpNodeWithLastPosition(SeqInst *s,int id,Quat q,Vec3 p,float percent,int *change){(void)s;(void)id;(void)q;(void)p;(void)change;assert(percent==1.f);}
static void pitchMat3(float angle,Mat3 m){(void)m;assert(angle==0.f);}
static void rollMat3(float angle,Mat3 m){(void)m;assert(angle==0.f);}
static void yawMat3(float angle,Mat3 m){(void)m;assert(angle==0.f);}
'''
EXTRA_FUNCTIONS=[('mathutil.h','mulMat3Inline'),('mathutil.c','mulMat3'),('mathutil.c','scaleMat3Vec3'),('seqregistration.c','unscaleBone'),('seqregistration.c','scaleBone'),('seqskeleton.c','changeBoneScaleEx'),('seqanimate.c','animGetNextFrame'),('seqanimate.c','computeHipCorrectionScale'),('seqanimate.c','animateGfxNodeBone')]
WRAPPER=r'''
static SeqType type;static SeqInst seq;static Appearance appearance;static Move move;static ModelHeader fat,skinny;
void original_actor_config(const float header[53],const float models[99*6],float scales[99*3],float root[12]){
 memset(&seq,0,sizeof seq);memset(&appearance,0,sizeof appearance);memset(&type,0,sizeof type);seq.type=&type;seq.animation.move=&move;seq.bonescale_anm_fat=&fat;seq.bonescale_anm_skinny=&skinny;
 appearance.bodytype=4;appearance.fBoneScale=header[3];appearance.fShoulderScale=header[4];appearance.fChestScale=header[5];appearance.fWaistScale=header[6];appearance.fHipScale=header[7];appearance.fLegScale=header[8];appearance.fArmScale=header[9];copyVec3(header+10,appearance.fHeadScales);type.legScaleRatio=header[13];
 copyVec3(header+14,type.shoulderScaleSkinny);copyVec3(header+17,type.shoulderScaleFat);copyVec3(header+20,type.hipScale);copyVec3(header+23,type.neckScale);copyVec3(header+26,type.headScaleMin);copyVec3(header+29,type.headScaleMax);memcpy(appearance.f3DScales,header+32,84);
 for(int id=0;id<99;id++){copyVec3(models+id*6,fat.models[id].scale);copyVec3(models+id*6+3,skinny.models[id].scale);}
 changeBoneScaleEx(&seq,&appearance);memcpy(scales,seq.bone_scales,99*12);
 GfxNode node={0};copyMat4(unitmat,node.mat);scaleMat3Vec3(node.mat,header);if(seq.legScale)scaleBone(&node,1,(1.0+(seq.type->legScaleRatio*seq.legScale)),1);
 for(int r=0;r<3;r++)for(int c=0;c<4;c++)root[r*4+c]=node.mat[c][r];
}
void original_actor_node(U8 *rot,U8 *pos,int rf,int pf,int rc,int pc,int flags,int id,const float delta[3],float frame,float rows[12],float quaternion[4]){
 BoneAnimTrack bt=track(rot,pos,rf,pf,rc,pc,flags);GfxNode node={0};node.bt=&bt;node.anim_id=id;copyVec3(delta,node.animDelta);int change=0;int whole=(int)frame;float fraction=frame-(float)whole;
 animateGfxNodeBone(&seq,&node,whole,fraction,1.f,&change);
 for(int r=0;r<3;r++)for(int c=0;c<4;c++)rows[r*4+c]=node.mat[c][r];copyQuat(seq.last_rotations[id],quaternion);
}
'''
def kernel_code(source_directory,extra_directory):
 code,_=original.source_code(source_directory);texts={};pins={}
 for name,_ in EXTRA_FUNCTIONS:
  if name in texts:continue
  if name=='seqregistration.c':path=(extra_directory/name) if extra_directory else (source_directory/name) if source_directory and (source_directory/name).exists() else ROOT.parent/'upstream/ouroboros/Common/seq'/name
  else:path=(source_directory/name) if source_directory else ROOT.parent/'upstream/ouroboros'/original.PATHS.get(name,'Common/seq/'+name)
  raw=path.read_bytes().replace(b'\r\n',b'\n');texts[name]=raw.decode('latin1');pins[name]={'sha256_lf':sha(raw)}
 snippets=[]
 for name,func in EXTRA_FUNCTIONS:
  snippet=original.extract(texts[name],func);snippets.append(snippet);pins[name].setdefault('functions',{})[func]=sha(snippet.encode())
 expected=json.loads((HERE/'original-actor-pins.json').read_text())
 require(pins==expected['sources'],'Original actor source/function hashes differ')
 return code.replace(original.PREAMBLE,original.PREAMBLE+MORE,1)+'\n'+'\n'.join(snippets)+WRAPPER,pins
def compare(actual,expected,label,stats):
 require(len(actual)==len(expected),label+' count differs')
 for x,y in zip(actual,expected):
  error=abs(x-y);stats['components']+=1;stats['maximum_absolute_error']=max(stats['maximum_absolute_error'],error)
  require(error<=2e-6+2e-6*abs(y),f'{label}: {x} versus {y}')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rig',required=True,type=Path);p.add_argument('--morph',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--report',required=True,type=Path);p.add_argument('--source-directory',type=Path);p.add_argument('--extra-source-directory',type=Path);p.add_argument('--compiler',default=os.environ.get('CC','cc'));a=p.parse_args()
 rig_raw=a.rig.read_bytes();morph_raw=a.morph.read_bytes();require(morph_raw[:8]==b'COHMOR01' and len(morph_raw)==3028,'Morph fixture differs');code,pins=kernel_code(a.source_directory,a.extra_source_directory)
 bo,bn,mo,mn=struct.unpack_from('<4I',rig_raw,16);base=rig_raw[bo:bo+bn];motion=rig_raw[mo:mo+mn];base_tracks=original.raw_tracks(base);motion_tracks=original.raw_tracks(motion);parents,order=original.hierarchy(base);ids=sorted(parents)
 header=(C.c_float*53)(*struct.unpack_from('<53f',morph_raw,40));model_values=[]
 for id in range(99):model_values.extend(struct.unpack_from('<6f',morph_raw,256+id*28+4))
 models=(C.c_float*(99*6))(*model_values);fp=C.POINTER(C.c_float);up=C.POINTER(C.c_uint8)
 stats={k:{'components':0,'maximum_absolute_error':0.} for k in ('morph_scales','actor_root','morph_local','world','socket_palette')}
 with tempfile.TemporaryDirectory(prefix='coh-original-actor-') as temp:
  t=Path(temp);source=t/'original.c';source.write_text(code);lib_path=t/'original.so';subprocess.run([*shlex.split(a.compiler),'-std=c11','-O0','-ffp-contract=off','-fno-strict-aliasing','-fPIC','-shared',str(source),'-lm','-o',str(lib_path)],check=True)
  lib=C.CDLL(str(lib_path));lib.original_actor_config.argtypes=[fp,fp,fp,fp];lib.original_actor_node.argtypes=[up,up,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,fp,C.c_float,fp,fp];lib.original_local.argtypes=[up,up,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,C.c_float,C.c_int,fp];lib.original_matrix.argtypes=[fp,fp,fp];lib.original_math.argtypes=[fp,fp,fp,fp,fp]
  scales=(C.c_float*(99*3))();root=(C.c_float*12)();lib.original_actor_config(header,models,scales,root)
  native_path=t/'native.so';subprocess.run([*shlex.split(a.compiler),'-std=c11','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror','-fPIC','-shared',str(ROOT/'character/coh_character.c'),'-lm','-o',str(native_path)],check=True);native=configure(C.CDLL(str(native_path)))
  rig_mem=(C.c_uint8*len(rig_raw)).from_buffer_copy(rig_raw);morph_mem=(C.c_uint8*len(morph_raw)).from_buffer_copy(morph_raw);rig=Rig();morph=Morph();require(native.coh_animation_parse(rig_mem,len(rig_raw),C.byref(rig))==0,'Native rig rejected');require(native.coh_character_parse_morph(morph_mem,len(morph_raw),C.byref(morph))==0,'Native authored morphology rejected')
  compare([x for row in morph.bone_scales for x in row],list(scales),'Original changeBoneScaleEx/native scales',stats['morph_scales']);compare(list(morph.actor_root_rows),list(root),'Original root scale/leg correction',stats['actor_root'])
  first={id:original.sample(lib,base_tracks[id],0,True) for id in ids};first_motion={id:original.sample(lib,track,0) for id,track in motion_tracks.items()};delta={id:[original.f32(first_motion[id][j+4]-first[id][j+4]) for j in range(3)] for id in motion_tracks};btt={}
  for id in order:btt[id]=[0.,0.,0.] if parents[id]<0 or id==0 else [original.f32(btt[parents[id]][j]+first[id][j+4]) for j in range(3)]
  samples=[];identity=[1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.];zero=[0.,0.,0.]
  for frame in original.FRAMES:
   pose=Pose();require(native.coh_character_sample(C.byref(rig),C.byref(morph),frame,C.byref(pose))==0,'Native character sampler rejected');locals=[];local_matrices={}
   for id in ids:
    track=motion_tracks.get(id,base_tracks[id]);rot=(C.c_uint8*(len(track['rotation'])+16)).from_buffer_copy(track['rotation']+bytes(16));pos=(C.c_uint8*(len(track['position'])+16)).from_buffer_copy(track['position']+bytes(16));d=(C.c_float*3)(*delta.get(id,zero));rows=(C.c_float*12)();q=(C.c_float*4)();lib.original_actor_node(rot,pos,track['rf'],track['pf'],track['rc'],track['pc'],track['flags'],id,d,frame,rows,q)
    value=list(q)+[rows[j*4+3] for j in range(3)];compare([*pose.rotation[id],*pose.position[id]],value,f'Original animateGfxNodeBone local{id} frame{frame}',stats['morph_local']);local_matrices[id]=list(rows);locals.append({'id':id,'rotation':list(q),'position':value[4:],'local_rows':list(rows)})
   worlds={}
   for id in order:
    parent=list(root) if parents[id]<0 else worlds[parents[id]];worlds[id]=original.original_math(lib,parent,local_matrices[id],zero)[0];compare(list(pose.world_rows[id]),worlds[id],f'Original actor world{id} frame{frame}',stats['world'])
   for start in range(0,len(ids),15):
    batch=ids[start:start+15];indices=(C.c_uint32*len(batch))(*batch);rows=(C.c_float*(len(batch)*12))();require(native.coh_character_palette(C.byref(rig),C.byref(morph),C.byref(pose),rig.socket_id,indices,len(batch),rows)==0,'Native character palette rejected')
    for j,id in enumerate(batch):
     diag=[scales[id*3],0.,0.,0.,0.,scales[id*3+1],0.,0.,0.,0.,scales[id*3+2],0.];scaled_local=original.original_math(lib,local_matrices[id],diag,zero)[0];parent=list(root) if parents[id]<0 else worlds[parents[id]];matrix=original.original_math(lib,parent,scaled_local,zero)[0]
     for offset in ([-x for x in btt[id]],btt[rig.socket_id]):
      translation=original.original_math(lib,matrix,identity,offset)[1]
      for axis in range(3):matrix[axis*4+3]=translation[axis]
     compare(list(rows[j*12:(j+1)*12]),matrix,f'Original actor socket palette{id} frame{frame}',stats['socket_palette'])
   samples.append({'frame':frame,'local':locals})
  result={'format':'original-source-actor-local-v1','scope':'unchanged source scalar kernels; huge single clip; no transition/aiming; not full original client/GPU','rig_sha256':sha(rig_raw),'morph_sha256':sha(morph_raw),'hierarchy':[{'id':id,'parent':parents[id]} for id in ids],'base_local':[{'id':id,'rotation':first[id][:4],'position':first[id][4:]} for id in ids],'morphology':{'bone_scales':[{'id':id,'scale':list(scales[id*3:id*3+3])} for id in range(99)],'actor_root_rows':list(root)},'samples':samples}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');report={'passed':True,'source_kernel_count':30,'new_actor_functions':[{'source':name,'function':function} for name,function in EXTRA_FUNCTIONS],'source_pins':pins,'original_appearance_computed':True,'native_runtime_raw_keys':True,'compatibility_helpers':'single clip; no transition blending; zero aiming; no character creator; absent scale models represented by their source unit default','stages':stats,'float_tolerance':'2e-6 absolute + 2e-6 relative','samples_sha256':sha(a.output.read_bytes())};a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':True,'stages':stats,'samples':str(a.output)}))
if __name__=='__main__':main()
