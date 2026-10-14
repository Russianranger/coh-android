#!/usr/bin/env python3
"""Compare directional raw-key, retarget, blend and hierarchy against source C.

Original animateGfxNodeBone, animInterpNodeWithLastPosition, raw-key codecs,
quaternion/position interpolation, morphology and matrix kernels run unchanged
with scalar platform stubs. Character/server aiming and rendered pixels are
outside this host oracle.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,importlib.util,json,os,re,shlex,struct,subprocess,tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
directional=module('source_directional_check',HERE/'check.py')
actor=module('source_directional_actor',HERE.parent/'character_fixture/original_actor_check.py')
original=actor.original
Rig,Pose,Morph,Loco,State,Blend=directional.Rig,directional.Pose,directional.Morph,directional.Loco,directional.State,directional.Blend
require,sha=directional.require,directional.sha

BLEND_HELPERS=r'''
#define CLOSE_ENOUGH_ROT 0.0003
#define CLOSE_ENOUGH_XLATE 0.001
static float TIMESTEP,blend_alpha,blend_clock;
static unsigned blend_serial=0xffffffffu;
static int seqIsBoneAnimationStored(SeqInst*s,int id){return s->stored[id];}
static int seqBoneNeedsRotationBlending(SeqInst*s,int id){return s->rotation_blend[id];}
static int seqBoneNeedsTranslationBlending(SeqInst*s,int id){return s->translation_blend[id];}
static void seqSetBoneNeedsRotationBlending(SeqInst*s,int id,int v){s->rotation_blend[id]=v;}
static void seqSetBoneNeedsTranslationBlending(SeqInst*s,int id,int v){s->translation_blend[id]=v;}
static void seqGetLastRotations(SeqInst*s,int id,Quat q){copyQuat(s->last_rotations[id],q);}
F32 quatInterp(F32 alpha,const Quat a,const Quat b,Quat q);
void posInterp(F32 t,const Vec3 T0,const Vec3 T1,Vec3 T);
'''
BLEND_WRAPPER=r'''
void original_begin_pose(unsigned serial,float dt,float interpolate){
 if(serial!=blend_serial){blend_serial=serial;blend_clock=0.f;for(int id=0;id<99;id++){seq.rotation_blend[id]=1;seq.translation_blend[id]=1;}}
 TIMESTEP=dt;blend_clock+=dt;
 blend_alpha=blend_clock<interpolate?1/(1+interpolate-blend_clock):1.f;
}
void original_blend_status(unsigned id,float out[3]){
 out[0]=(float)seq.rotation_blend[id];out[1]=(float)seq.translation_blend[id];out[2]=blend_clock;
}
void original_blend_reset(void){memset(seq.stored,0,sizeof seq.stored);blend_serial=0xffffffffu;blend_clock=0.f;}
'''

def source_program(directory):
    # The accepted actor oracle's seqregistration whole-file pin describes a
    # former host shim. Preserve it; validate exact upstream here through the
    # directional manifest and compare every reused function hash separately.
    code,_=original.source_code(directory);snippets=[];pins={}
    expected=json.loads((HERE.parent/'character_fixture/original-actor-pins.json').read_text())['sources']
    for file,function in actor.EXTRA_FUNCTIONS:
        raw=(directory/file).read_bytes().replace(b'\r\n',b'\n')
        snippet=original.extract(raw.decode('latin1'),function)
        require(sha(snippet.encode())==expected[file]['functions'][function],'accepted original actor function differs: '+function)
        pins.setdefault(file,{'sha256_lf':sha(raw)}).setdefault('functions',{})[function]=sha(snippet.encode())
        snippets.append(snippet)
    code=code.replace(original.PREAMBLE,original.PREAMBLE+actor.MORE,1)+'\n'+'\n'.join(snippets)+actor.WRAPPER
    text=(directory/'seqanimate.c').read_text()
    interp=directional.extract(text,'animInterpNodeWithLastPosition')
    near=directional.extract((directory/'mathutil.h').read_text(),'nearSameVec3Tol')
    code=code.replace('Vec3 bone_scales[99],last_translations[99];','Vec3 bone_scales[99],last_translations[99];int stored[99],rotation_blend[99],translation_blend[99];',1)
    for stub in [
      'static int seqBoneNeedsRotationBlending(SeqInst *s,int id){(void)s;(void)id;return 0;}',
      'static int seqBoneNeedsTranslationBlending(SeqInst *s,int id){(void)s;(void)id;return 0;}']:
        require(stub in code,'source actor shim changed');code=code.replace(stub,'',1)
    stored='static void seqSetBoneAnimationStored(SeqInst *s,int id){(void)s;(void)id;}'
    require(stored in code,'source actor stored shim changed')
    code=code.replace(stored,'static void seqSetBoneAnimationStored(SeqInst *s,int id){s->stored[id]=1;}',1)
    stub='static void animInterpNodeWithLastPosition(SeqInst *s,int id,Quat q,Vec3 p,float percent,int *change){(void)s;(void)id;(void)q;(void)p;(void)change;assert(percent==1.f);}'
    require(stub in code,'source actor interpolation shim changed')
    code=code.replace(stub,BLEND_HELPERS+near+interp,1)
    code=code.replace('animateGfxNodeBone(&seq,&node,whole,fraction,1.f,&change);','animateGfxNodeBone(&seq,&node,whole,fraction,blend_alpha,&change);',1)
    pins['seqanimate.c']['functions']['animInterpNodeWithLastPosition']=sha(interp.encode())
    pins['mathutil.h']['functions']['nearSameVec3Tol']=sha(near.encode())
    return code+BLEND_WRAPPER,pins

def compare(actual,expected,label,stats):
    for x,y in zip(actual,expected):
        error=abs(float(x)-float(y));stats['components']+=1;stats['maximum_absolute_error']=max(stats['maximum_absolute_error'],error)
        require(error<=4e-6+4e-6*abs(float(y)),label+f': {x} != {y}')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',required=True,type=Path)
    p.add_argument('--morph',required=True,type=Path);p.add_argument('--source-directory',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--corpus',type=Path,default=HERE/'corpus');p.add_argument('--compiler',default=os.environ.get('CC','cc'))
    a=p.parse_args();texts,pin=directional.sources(a.source_directory);code,source_pins=source_program(a.source_directory)
    raw=a.fixture.read_bytes();morph_raw=a.morph.read_bytes();pins=json.loads((HERE/'pins.json').read_text())
    clips={}
    for item in pins['records']:
        clip=(a.corpus/item['file_name']).read_bytes();require(len(clip)==item['size'] and sha(clip)==item['sha256'],'original clip differs')
        clips[item['id']]=clip
    tracksets={key:original.raw_tracks(clip) for key,clip in clips.items()}
    parents,order=original.hierarchy(clips['ready']);ids=sorted(parents);cc=shlex.split(a.compiler);fp=C.POINTER(C.c_float);up=C.POINTER(C.c_uint8)
    stats={key:{'components':0,'maximum_absolute_error':0.} for key in ['morphology','retarget_delta','local_rotation','local_position','world_hierarchy','blend_state']}
    poses=0;observed=set();rotation_early=translation_early=0;invalid_atomic=0
    with tempfile.TemporaryDirectory(prefix='coh-directional-sampler-') as folder:
        temp=Path(folder);(temp/'original.c').write_text(code)
        build=subprocess.run([*cc,'-std=c11','-O0','-ffp-contract=off','-fno-strict-aliasing','-shared','-fPIC',str(temp/'original.c'),'-lm','-o',str(temp/'original.so')],capture_output=True,text=True)
        require(build.returncode==0,build.stderr)
        lib=C.CDLL(str(temp/'original.so'));lib.original_actor_config.argtypes=[fp,fp,fp,fp]
        lib.original_actor_node.argtypes=[up,up,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,fp,C.c_float,fp,fp]
        lib.original_local.argtypes=[up,up,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,C.c_float,C.c_int,fp]
        lib.original_matrix.argtypes=[fp,fp,fp];lib.original_math.argtypes=[fp,fp,fp,fp,fp]
        lib.original_begin_pose.argtypes=[C.c_uint32,C.c_float,C.c_float];lib.original_blend_status.argtypes=[C.c_uint32,fp]
        subprocess.run([*cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-fPIC','-shared',str(ROOT/'character/coh_character.c'),str(ROOT/'locomotion/coh_locomotion.c'),'-lm','-o',str(temp/'native.so')],check=True)
        native=directional.configure(C.CDLL(str(temp/'native.so')))
        mem=(C.c_uint8*len(raw)).from_buffer_copy(raw);loco=Loco();require(native.coh_locomotion_parse(mem,len(raw),C.byref(loco))==0,'new bundle rejected')
        morph_mem=(C.c_uint8*len(morph_raw)).from_buffer_copy(morph_raw);morph=Morph();require(native.coh_character_parse_morph(morph_mem,len(morph_raw),C.byref(morph))==0,'authentic Wretch morphology rejected')
        header=(C.c_float*53)(*struct.unpack_from('<53f',morph_raw,40));models=(C.c_float*(99*6))(*[v for id in range(99) for v in struct.unpack_from('<6f',morph_raw,256+id*28+4)])
        scales=(C.c_float*(99*3))();root=(C.c_float*12)();lib.original_actor_config(header,models,scales,root)
        compare([v for row in morph.bone_scales for v in row],scales,'original morphology',stats['morphology']);compare(morph.actor_root_rows,root,'original root',stats['morphology'])
        base_first={id:original.sample(lib,tracksets['ready'][id],0,True) for id in ids}
        keys=['ready','run','post','run','walk','idle','back','back','left','left','right','right'];cache={}
        for move,key in enumerate(keys):
            source=tracksets[key];backup=tracksets['idle'] if key in ['walk','idle'] else tracksets['ready']
            for id in ids:
                track=source.get(id,backup.get(id,tracksets['ready'][id]));first=original.sample(lib,track,0)
                delta=[original.f32(first[j+4]-base_first[id][j+4]) for j in range(3)]
                compare(loco.rigs[move].animation_delta[id],delta,f'source frame0 retarget move{move} bone{id}',stats['retarget_delta'])
                rot=(C.c_uint8*(len(track['rotation'])+16)).from_buffer_copy(track['rotation']+bytes(16));pos=(C.c_uint8*(len(track['position'])+16)).from_buffer_copy(track['position']+bytes(16));d=(C.c_float*3)(*delta)
                cache[move,id]=(track,rot,pos,d)
            require(list(loco.rigs[move].order[:60])==order and all(loco.rigs[move].parent[id]==parents[id] for id in ids),'source Huge hierarchy differs')
        state=State();blend=Blend();native.coh_locomotion_init(C.byref(state));native.coh_locomotion_blend_init(C.byref(blend));lib.original_blend_reset()
        schedule=[(0,1.,0.)]*8
        for mask in [1,2,4,8,5,9,6,10]:schedule += [(mask,1.,.7)]*55+[(0,1.,0.)]*50
        for mask in [1,2,4,8]:schedule += [(mask,.25,.01)]+[(0,.25,0.)]*28
        schedule += [(1,1.,0.)]*60+[(4,.25,.03)]*30+[(8,.25,.03)]*30+[(2,3.,1.4)]*30+[(0,1.,0.)]*50
        def sample(label,dt):
            nonlocal poses,rotation_early,translation_early
            pose=Pose();require(native.coh_locomotion_sample_directional(C.byref(loco),C.byref(state),C.byref(morph),dt,C.byref(blend),C.byref(pose))==0,'native sample rejected')
            move=state.move;observed.add(directional.NAMES[move]);lib.original_begin_pose(state.transitions,dt,8. if move==2 else 5.)
            local={}
            for id in ids:
                track,rot,pos,d=cache[move,id];rows=(C.c_float*12)();q=(C.c_float*4)();lib.original_actor_node(rot,pos,track['rf'],track['pf'],track['rc'],track['pc'],track['flags'],id,d,state.frame,rows,q)
                compare(pose.rotation[id],q,label+f' rotation{id}',stats['local_rotation'])
                # SmoothSprint runs after the stored last translations. Native
                # blend.previous must retain the unmodified local hip position.
                position=[rows[j*4+3] for j in range(3)];compare(blend.previous.position[id],position,label+f' cacheposition{id}',stats['local_position'])
                if id==0 and move in [1,3,6,7,8,9,10,11] and state.move_rate_scale>1.05:
                    rate=state.move_rate_scale;position[1]=original.f32(3.3+original.f32(original.f32(position[1]-3.3)/original.f32(rate*rate)));rows[7]=position[1]
                compare(pose.position[id],position,label+f' position{id}',stats['local_position']);local[id]=list(rows)
                status=(C.c_float*3)();lib.original_blend_status(id,status)
                compare([blend.rotation_blend[id]],[status[0]],label+f' rotationflag{id}',stats['blend_state'])
                compare([blend.translation_blend[id]],[status[1]],label+f' positionflag{id}',stats['blend_state'])
                compare([blend.interpolation_frame],[status[2]],label+f' blendclock{id}',stats['blend_state'])
                rotation_early+=not blend.rotation_blend[id] and blend.interpolation_frame<5
                translation_early+=not blend.translation_blend[id] and blend.interpolation_frame<5
            worlds={}
            for id in order:
                parent=root if parents[id]<0 else worlds[parents[id]];worlds[id]=original.original_math(lib,parent,local[id],[0.,0.,0.])[0]
                compare(pose.world_rows[id],worlds[id],label+f' world{id}',stats['world_hierarchy'])
            poses+=1
        sample('initial display',1.)
        for index,(mask,dt,distance) in enumerate(schedule):
            require(native.coh_locomotion_step_directional(C.byref(loco),C.byref(state),mask,dt,distance,1.3)==0,'valid sampler tick rejected')
            sample(f'display{index}',dt)
        require({'RunPre','RunCycle','RunPost','Idle_Walk_Post','Idle_Ready','Run_Back_Pre','Run_Back_Cycle','Run_Left_Pre','Run_Left_Cycle','Run_Right_Pre','Run_Right_Cycle'}<=observed,'new authored poses not all exercised')
        # Invalid sampler inputs leave both cached display state and output
        # untouched; checks cover API limits rather than renderer behavior.
        valid_state=bytes(state);valid_blend=bytes(blend)
        for key,value in [('dt',float('nan')),('dt',-1.),('dt',4.),('move',12),('frame',float('nan')),
          ('frame',-1.),('move_rate_scale',float('nan')),('move_rate_scale',.1),('move_rate_scale',2.1),
          ('valid',2),('interpolation_frame',float('nan')),('interpolation_frame',-1.)]:
            trial=State.from_buffer_copy(valid_state);cache_state=Blend.from_buffer_copy(valid_blend);dt=1.
            if key=='dt':dt=value
            elif key in ['valid','interpolation_frame']:setattr(cache_state,key,value)
            else:setattr(trial,key,value)
            output=Pose();C.memset(C.byref(output),0x5a,C.sizeof(output));prior_output=bytes(output);prior_cache=bytes(cache_state)
            require(native.coh_locomotion_sample_directional(C.byref(loco),C.byref(trial),C.byref(morph),dt,C.byref(cache_state),C.byref(output))!=0,'invalid sampler input accepted: '+key)
            require(bytes(cache_state)==prior_cache and bytes(output)==prior_output,'invalid sampler input mutated output/cache: '+key);invalid_atomic+=1
    report={'schema':'coh-native-directional-sampler-proof-v1','passed':True,'source_commit':pin['source_commit'],'data_commit':pin['data_commit'],
      'poses':poses,'reachable_bones':len(ids),'observed_moves':sorted(observed),'stages':stats,
      'rotation_early_termination_bone_frames':rotation_early,'translation_early_termination_bone_frames':translation_early,
      'invalid_atomic_sampler_checks':invalid_atomic,
      'original_sources':source_pins,'source_program_sha256':sha(code.encode()),'fixture_sha256':sha(raw),'morph_sha256':sha(morph_raw),
      'scope':'Original scalar raw-key codecs, parent-type animation delta, morphology, independent per-bone transition blend, hierarchy composition. Neutral aiming; no pixels/server/GPU.'}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':True,'poses':poses,'stages':stats}))

if __name__=='__main__':main()
