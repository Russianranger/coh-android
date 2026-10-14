#!/usr/bin/env python3
"""Qualify bounded authored forward locomotion against unchanged source kernels.

The selected Ready loop is deterministic. Source random idle graphs, RunPre,
transition blending and omitted directional moves are not qualified here.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,importlib.util,json,math,os,re,shlex,struct,subprocess,tempfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out
types=module('coh_locomotion_character_types',HERE.parent/'character_fixture/_types.py')
Rig,Pose,Morph=types.Rig,types.Pose,types.Morph
class Loco(C.Structure):
    _fields_=[('bytes',C.POINTER(C.c_uint8)),('byte_count',C.c_size_t),('rigs',Rig*12),('clip_count',C.c_uint32)]
class State(C.Structure):
    _fields_=[('move',C.c_uint32),('frame',C.c_float),('previous_frame',C.c_float),('move_rate_scale',C.c_float),('transitions',C.c_uint32),('ready_entries',C.c_uint32),('run_entries',C.c_uint32),('post_entries',C.c_uint32),('cycles',C.c_uint32)]+[(k,C.c_uint32) for k in ['pre_entries','directional_entries','early_stop_entries','phase_preservations','direction_switches','anim_incrementor','input_mask','selection_changed']]
def require(v,s):
    if not v:raise ValueError(s)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def extract(text,name):
    m=re.search(r'^[^\n;{}]*\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',text,re.M)
    require(m is not None,'original function missing: '+name);start=m.start();i=text.index('{',m.start())+1;depth=1
    while depth:
        if text[i]=='{':depth+=1
        elif text[i]=='}':depth-=1
        i+=1
    return text[start:i]+'\n'
FUNCTIONS=[('seqsequence.c','seqSetMove'),('seqsequence.c','seqCycleFrame'),('seqsequence.c','seqStep'),('seqsequence.c','seqGetAnimScale'),('entclient.c','seqGetMovementSpeedAnimScale'),('entclient.c','smoothSprintAnimation')]
PREAMBLE=r'''#include <stdint.h>
#include <stdbool.h>
#include <math.h>
#include <string.h>
typedef float F32;typedef uint32_t U32;typedef float Vec3[3];
enum {SEQMOVE_CYCLE=1,SEQMOVE_COMPLEXCYCLE=2,SEQMOVE_MOVESCALE=4,SEQMOVE_SMOOTHSPRINT=8,SEQMOVE_PREDICTABLE=16,SEQMOVE_ALWAYSSIZESCALE=32,SEQMOVE_NOSIZESCALE=64,SEQMOVE_FULLSIZESCALE=128,SEQMOVE_NODRAW=256};
enum {NEWMOVE_FOUND_BY_COMPLEX_CYCLING=1,NEWMOVE_FOUND_BY_REQUIREMENTS_FAILED_IN_FINISHCYCLE=2,NEWMOVE_FOUND_BY_NONCYCLING_MOVE_ENDED=4,GFXNODE_HIDE=1};
typedef struct {int firstFrame,lastFrame;} AnimRange;
typedef struct {float scale,moveRate,smoothSprint,ragdollFrame;void*animTrack;AnimRange *animP[1];const char*type;} TypeGfx;
typedef struct {unsigned required,cycleMoveCnt;int cycleMove[2],nextMove[1];} Raw;
typedef struct SeqMove {const char*name;unsigned flags;float scale,moveRate;Raw raw;TypeGfx*typeGfx[1];} SeqMove;
typedef struct {const SeqMove*moves[3];const char*name;} SeqInfo;
typedef struct {float frame,prev_frame;const SeqMove*move,*prev_move,*move_to_send;const TypeGfx*typeGfx;bool bRagdoll;} Animation;
typedef struct GfxNode {unsigned flags;struct GfxNode*child;float mat[4][3];} GfxNode;
typedef struct {float animScale;const char *seqname,*name,*seqTypeName;} SeqType;
typedef struct {Animation animation;SeqInfo*info;SeqType*type;float curranimscale;int moved_instantly;GfxNode*gfx_root;unsigned handle;const char*calculatedSeqTypeName;} SeqInst;
static float TIMESTEP;
static struct {int quickLoadAnims;} STATE_STRUCT;
static struct {int seq_info;} game_state;
static struct {SeqInst*seq;} *current_target;
static int isDevelopmentMode(void){return 0;}
static int isSharedMemory(const void*p){(void)p;return 0;}
static const TypeGfx *seqGetTypeGfx(const SeqInfo*i,const SeqMove*m,const char*n){(void)i;(void)n;return m->typeGfx[0];}
static void seqAttachAnAnim(TypeGfx*t,int mode){(void)t;(void)mode;}
static bool sparseRequiresMet(const unsigned *requires,const U32 *state){return (*state&*requires)==*requires;}
static int randUIntGivenSeed(int*s){*s=1;return 0;}
static GfxNode *gfxTreeFindBoneInAnimation(int dummy,GfxNode*n,unsigned handle,int bone){(void)dummy;(void)handle;(void)bone;return n;}
#define Errorf(...) ((void)0)
#define xyprintf(...) ((void)0)
#define CONTEXT_CORRECT_LOADTYPE 0
#define cpp_const_cast(t) (t)
#define MAX(a,b) ((a)>(b)?(a):(b))
#define MIN(a,b) ((a)<(b)?(a):(b))
#define MINMAX(v,a,b) MIN(MAX(v,a),b)
#define subVec3(a,b,c) do{for(int j=0;j<3;j++)(c)[j]=(a)[j]-(b)[j];}while(0)
'''
WRAPPER=r'''
static void initOracle(SeqInst *s,SeqInfo*info,SeqMove moves[3],TypeGfx gfx[3],AnimRange ranges[3],SeqType*type,GfxNode nodes[2],unsigned move,float frame,float previous,float geom){
 memset(s,0,sizeof *s);memset(moves,0,3*sizeof *moves);memset(gfx,0,3*sizeof *gfx);memset(nodes,0,2*sizeof *nodes);
 for(int i=0;i<3;i++){ranges[i].firstFrame=1;ranges[i].lastFrame=i==0?60:i==1?25:23;gfx[i].scale=1;gfx[i].animP[0]=&ranges[i];gfx[i].type="huge";moves[i].scale=1;moves[i].flags=SEQMOVE_PREDICTABLE; moves[i].typeGfx[0]=&gfx[i];info->moves[i]=&moves[i];}
 moves[0].name="Ready";moves[0].flags|=SEQMOVE_CYCLE|SEQMOVE_COMPLEXCYCLE;
 moves[1].name="RunCycle";moves[1].flags|=SEQMOVE_CYCLE|SEQMOVE_MOVESCALE|SEQMOVE_SMOOTHSPRINT;moves[1].moveRate=.7f;gfx[1].smoothSprint=3.3f;moves[1].raw.required=1;moves[1].raw.nextMove[0]=2;
 moves[2].name="RunPost";moves[2].raw.nextMove[0]=0;
 type->animScale=1;type->seqname="player.txt";type->name="V_Arachnos_Wretch";type->seqTypeName="huge";
 s->info=info;s->type=type;s->curranimscale=1.f/geom;s->animation.move=&moves[move];s->animation.typeGfx=&gfx[move];s->animation.frame=frame;s->animation.prev_frame=previous;s->gfx_root=&nodes[0];nodes[0].child=&nodes[1];
}
void original_tick(unsigned move,float frame,float previous,int forward,float timestep,float distance,float geom,float out[4]){
 SeqInst s;SeqInfo info;SeqMove moves[3];TypeGfx gfx[3];AnimRange ranges[3];SeqType type;GfxNode nodes[2];initOracle(&s,&info,moves,gfx,ranges,&type,nodes,move,frame,previous,geom);
 TIMESTEP=timestep;float pos[3]={distance,0,0},last[3]={0,0,0};float rate=seqGetMovementSpeedAnimScale(&s,pos,last);
 const SeqMove *changed=0;
 /* The bounded offline selection adapter is deliberate, not source priority/IRQ search. */
 if(forward&&move!=1)changed=&moves[1];else if(!forward&&move==1)changed=&moves[2];
 else {int reason=0,seed=0;U32 state=forward?1:0;
   /* Deterministic selected Ready loop omits original random idle graph. */
   moves[0].flags &= ~SEQMOVE_COMPLEXCYCLE;
   changed=seqStep(&s.animation,&info,&state,(rate*timestep)*seqGetAnimScale(&s),&reason,&seed,false);
 }
 if(changed)seqSetMove(&s,changed,0);
 out[0]=(float)(s.animation.move-moves);out[1]=s.animation.frame;out[2]=s.animation.prev_frame;out[3]=rate;
}
float original_hip(float rate,float y){SeqInst s;SeqInfo i;SeqMove m[3];TypeGfx g[3];AnimRange r[3];SeqType t;GfxNode n[2];initOracle(&s,&i,m,g,r,&t,n,1,1,-1,1.3f);n[1].mat[3][1]=y;if(rate>1.05f)smoothSprintAnimation(&s,rate);return n[1].mat[3][1];}
'''
def sources(directory):
    pins=json.loads((HERE/'source-pins.json').read_text());texts={};paths={}
    for name,item in pins['files'].items():
        direct=directory/name;path=direct if direct.exists() else directory/item['path']
        raw=path.read_bytes().replace(b'\r\n',b'\n');require(len(raw)==item['bytes_lf'] and sha(raw)==item['sha256_lf'],'original source hash differs: '+str(path));texts[name]=raw.decode();paths[name]=path
    require(re.search(r'Move RunCycle\s+Requires\s+FORWARD',texts['motion.inc']) is not None,'source FORWARD requirement differs')
    require(re.search(r'Type\s+huge\s+Anim\s+huge\\postrun\s+1\s+23',texts['motion.inc']) is not None,'source RunPost binding differs')
    require(re.search(r'Type\s+huge\s+Anim\s+huge\\Skel_ready\s+1\s+60',texts['readies.inc']) is not None,'source Ready binding differs')
    snippets=[];function_pins={}
    for name in ['fsqrt','SQR','lengthVec3Squared','lengthVec3']:
        match=re.search(r'^#define '+name+r'\([^\n]*$',texts['mathutil.h'],re.M)
        require(match is not None,'original length macro missing: '+name);snippets.append(match.group()+'\n')
    for file,fn in FUNCTIONS:
        code=extract(texts[file],fn);function_pins[fn]={'file':file,'sha256_lf':sha(code.encode())};snippets.append(code)
    return PREAMBLE+'\n'.join(snippets)+WRAPPER,pins,function_pins,paths
def near(x,y,label):
    error=abs(float(x)-float(y));require(error<=3e-6+3e-6*abs(float(y)),label+f': {x} != {y}');return error
def native_configure(lib):
    types.configure(lib);p=C.POINTER
    lib.coh_locomotion_parse.argtypes=[p(C.c_uint8),C.c_size_t,p(Loco)];lib.coh_locomotion_parse.restype=C.c_int
    lib.coh_locomotion_init.argtypes=[p(State)]
    lib.coh_locomotion_step.argtypes=[p(Loco),p(State),C.c_int,C.c_float,C.c_float,C.c_float];lib.coh_locomotion_step.restype=C.c_int
    lib.coh_locomotion_hip_y.argtypes=[p(State),C.c_float];lib.coh_locomotion_hip_y.restype=C.c_float
    lib.coh_locomotion_sample.argtypes=[p(Loco),p(State),p(Morph),p(Pose)];lib.coh_locomotion_sample.restype=C.c_int
    return lib
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--source-directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--morph',type=Path);p.add_argument('--compiler',default=os.environ.get('CC','cc'))
    p.add_argument('--disable-leak-sanitizer',action='store_true',help='Local ptrace/proc restriction override; ASan and UBSan remain enabled')
    a=p.parse_args()
    raw=a.fixture.read_bytes();code,pins,function_pins,paths=sources(a.source_directory)
    with tempfile.TemporaryDirectory(prefix='coh-locomotion-') as name:
        temp=Path(name);cc=shlex.split(a.compiler);(temp/'oracle.c').write_text(code)
        build=subprocess.run([*cc,'-std=c11','-O0','-ffp-contract=off','-fno-strict-aliasing','-shared','-fPIC',str(temp/'oracle.c'),'-lm','-o',str(temp/'oracle.so')],capture_output=True,text=True);require(build.returncode==0,build.stderr)
        oracle=C.CDLL(str(temp/'oracle.so'));oracle.original_tick.argtypes=[C.c_uint32,C.c_float,C.c_float,C.c_int,C.c_float,C.c_float,C.c_float,C.POINTER(C.c_float)];oracle.original_hip.argtypes=[C.c_float,C.c_float];oracle.original_hip.restype=C.c_float
        subprocess.run([*cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-fPIC','-shared',str(ROOT/'character/coh_character.c'),str(ROOT/'locomotion/coh_locomotion.c'),'-lm','-o',str(temp/'native.so')],check=True)
        lib=native_configure(C.CDLL(str(temp/'native.so')));mem=(C.c_uint8*len(raw)).from_buffer_copy(raw);loco=Loco();require(lib.coh_locomotion_parse(mem,len(raw),C.byref(loco))==0,'authentic bundle rejected')
        native_size=C.sizeof(Loco);require(all(r.node_count==60 for r in loco.rigs[:3]),'hierarchy cardinality differs')
        state=State();lib.coh_locomotion_init(C.byref(state));checks=0;maximum=0.;transcript=[]
        cases=[(0,1.,0.,1.3)]*80+[(1,1.,x,1.3) for x in [.1,.2,.4,.7,1.4,3.,6.]*18]+[(0,1.,0.,1.3)]*65+[(1,1.,1.4,1.3)]*9+[(0,1.,0.,1.3)]*70
        for i,(forward,dt,distance,geom) in enumerate(cases):
            expected=(C.c_float*4)();oracle.original_tick(state.move,state.frame,state.previous_frame,forward,dt,distance,geom,expected)
            require(lib.coh_locomotion_step(C.byref(loco),C.byref(state),forward,dt,distance,geom)==0,'valid tick rejected')
            for x,y in zip([state.move,state.frame,state.previous_frame,state.move_rate_scale],expected):maximum=max(maximum,near(x,y,f'original tick{i}'));checks+=1
            if i%30==0:transcript.append({'tick':i,'move':state.move,'frame':state.frame,'rate':state.move_rate_scale})
        require(state.run_entries>=2 and state.post_entries>=2 and state.ready_entries>=3 and state.cycles>0,'required transitions not observed')
        for move in range(3):
            for dt in [0.,.25,1.,3.]:
                for distance in [0.,.01,.7,1.4,10.]:
                    for geom in [.2,1.,1.3,3.]:
                        s=State();lib.coh_locomotion_init(C.byref(s));s.move=move;s.frame=[60.,25.,23.][move];s.previous_frame=4.
                        expected=(C.c_float*4)();forward=int(move==1);oracle.original_tick(s.move,s.frame,s.previous_frame,forward,dt,distance,geom,expected)
                        require(lib.coh_locomotion_step(C.byref(loco),C.byref(s),forward,dt,distance,geom)==0,'boundary tick rejected')
                        for x,y in zip([s.move,s.frame,s.previous_frame,s.move_rate_scale],expected):maximum=max(maximum,near(x,y,'source boundary'));checks+=1
        for rate in [.25,1.,1.05,1.051,1.5,2.]:
            s=State();lib.coh_locomotion_init(C.byref(s));s.move=1;s.move_rate_scale=rate
            for y in [2.5,3.3,4.,5.]:maximum=max(maximum,near(lib.coh_locomotion_hip_y(C.byref(s),y),oracle.original_hip(rate,y),'original SmoothSprint'));checks+=1
        invalids=0
        for dt,distance,geom,forward in [(-1,0,1.3,0),(3.001,0,1.3,0),(math.nan,0,1.3,0),(1,-1,1.3,0),(1,math.inf,1.3,0),(1,0,0,0),(1,0,math.nan,0),(1,0,1.3,2)]:
            before=bytes(state);require(lib.coh_locomotion_step(C.byref(loco),C.byref(state),forward,dt,distance,geom)==-1 and bytes(state)==before,'invalid tick modified state');invalids+=1
        for cut in list(range(64))+[len(raw)-1]:
            out=Loco();C.memset(C.byref(out),0x55,native_size);before=bytes(out)
            require(lib.coh_locomotion_parse(mem,cut,C.byref(out))==-1 and bytes(out)==before,'truncated bundle accepted/modified output');invalids+=1
        for off in [0,8,12,16,20,24,28,32,36,40,44,48,60,64+8]:
            changed=bytearray(raw);changed[off]^=0xff;b=(C.c_uint8*len(raw)).from_buffer_copy(changed);out=Loco();before=bytes(out);require(lib.coh_locomotion_parse(b,len(raw),C.byref(out))==-1 and bytes(out)==before,'mutated envelope accepted/modified output');invalids+=1
        post=loco.rigs[2];unused=[i for i in range(99) if post.motion.tracks[i].present and post.parent[i]==-2]
        require(unused==[50,51,52],'authentic spare-track identity differs')
        post_start=struct.unpack_from('<I',raw,40)[0];motion_offset,motion_bytes=struct.unpack_from('<2I',raw,post_start+24)
        absolute_motion=post_start+motion_offset;track_offset,track_count=struct.unpack_from('<2I',raw,absolute_motion+524)
        for i in range(track_count):
            offset=absolute_motion+track_offset+i*20
            if raw[offset+16] not in unused:continue
            for field,value in [(0,struct.pack('<I',motion_bytes)),(4,struct.pack('<I',motion_bytes)),(17,b'\xff')]:
                changed=bytearray(raw);changed[offset+field:offset+field+len(value)]=value;b=(C.c_uint8*len(raw)).from_buffer_copy(changed);out=Loco();before=bytes(out)
                require(lib.coh_locomotion_parse(b,len(raw),C.byref(out))==-1 and bytes(out)==before,'malformed unused track escaped validation');invalids+=1
        # Execute unchanged scalar raw-key source functions for every new clip.
        original=module('coh_locomotion_original_animation',HERE.parent/'animation_fixture/original_animation_check.py')
        flat=temp/'source';flat.mkdir();animation_pins=json.loads((HERE.parent/'animation_fixture/original-source-pins.json').read_text())
        for file,item in animation_pins['sources'].items():
            direct=a.source_directory/file;path=direct if direct.exists() else a.source_directory/'ouroboros'/item['path'];(flat/file).write_bytes(path.read_bytes())
        sampler_code,_=original.source_code(flat);(temp/'sampler.c').write_text(sampler_code)
        subprocess.run([*cc,'-std=c11','-O0','-ffp-contract=off','-fno-strict-aliasing','-fPIC','-shared',str(temp/'sampler.c'),'-lm','-o',str(temp/'sampler.so')],check=True,capture_output=True)
        sampler=C.CDLL(str(temp/'sampler.so'));sampler.original_local.argtypes=[C.POINTER(C.c_uint8),C.POINTER(C.c_uint8),C.c_int,C.c_int,C.c_int,C.c_int,C.c_int,C.c_float,C.c_int,C.POINTER(C.c_float)]
        local_checks=0;local_maximum=0.
        for clip,r in enumerate(loco.rigs[:3]):
            base_bytes=C.string_at(r.base.bytes,r.base.byte_count);motion_bytes=C.string_at(r.motion.bytes,r.motion.byte_count)
            base=original.raw_tracks(base_bytes);motion=original.raw_tracks(motion_bytes);ids=list(r.order)[:r.node_count]
            initial={i:original.sample(sampler,base[i],0,True) for i in ids}
            delta={i:[C.c_float(original.sample(sampler,motion[i],0)[4+j]-initial[i][4+j]).value for j in range(3)] for i in motion if i in initial}
            frames=sorted(set([1.,1.5,5.25,r.last_frame-.5,r.last_frame]+[float(x) for x in range(1,int(r.last_frame)+1)]))
            for frame in frames:
                pose=Pose();require(lib.coh_animation_sample(C.byref(r),frame,C.byref(pose))==0,'native real clip sample failed')
                for i in ids:
                    value=original.sample(sampler,motion[i],frame) if i in motion else list(initial[i])
                    if i in motion:
                        for j in range(3):value[4+j]=C.c_float(value[4+j]-delta[i][j]).value
                    for x,y in zip(list(pose.rotation[i])+list(pose.position[i]),value):local_maximum=max(local_maximum,near(x,y,'original encoded-key local'));local_checks+=1
        morph_checks=0;palette_checks=0
        if a.morph:
            mraw=a.morph.read_bytes();mmem=(C.c_uint8*len(mraw)).from_buffer_copy(mraw);morph=Morph();require(lib.coh_character_parse_morph(mmem,len(mraw),C.byref(morph))==0,'accepted morph rejected')
            for rate in [1.,1.05,1.5,2.]:
                s=State();lib.coh_locomotion_init(C.byref(s));s.move=1;s.frame=12.5;s.move_rate_scale=rate
                regular,corrected=Pose(),Pose();r=loco.rigs[1]
                require(lib.coh_character_sample(C.byref(r),C.byref(morph),s.frame,C.byref(regular))==0,'base character sample failed')
                require(lib.coh_locomotion_sample(C.byref(loco),C.byref(s),C.byref(morph),C.byref(corrected))==0,'locomotion character sample failed')
                expected_y=oracle.original_hip(rate,regular.position[0][1]);near(corrected.position[0][1],expected_y,'source hip correction')
                shift=[morph.actor_root_rows[j*4+1]*(expected_y-regular.position[0][1]) for j in range(3)]
                for i in list(r.order)[:r.node_count]:
                    ancestor=i
                    while ancestor>=0 and ancestor!=0:ancestor=r.parent[ancestor]
                    for j in range(3):near(corrected.world_rows[i][j*4+3],regular.world_rows[i][j*4+3]+(shift[j] if ancestor==0 else 0),'source hip descendant translation');morph_checks+=1
                ids=list(r.order)[:r.node_count]
                for offset in range(0,len(ids),15):
                    selected=ids[offset:offset+15];bone_ids=(C.c_uint32*len(selected))(*selected);original_rows=(C.c_float*(12*len(selected)))();corrected_rows=(C.c_float*(12*len(selected)))()
                    require(lib.coh_character_palette(C.byref(r),C.byref(morph),C.byref(regular),72,bone_ids,len(selected),original_rows)==0,'regular source palette failed')
                    require(lib.coh_character_palette(C.byref(r),C.byref(morph),C.byref(corrected),72,bone_ids,len(selected),corrected_rows)==0,'corrected source palette failed')
                    for at,i in enumerate(selected):
                        ancestor=i
                        while ancestor>=0 and ancestor!=0:ancestor=r.parent[ancestor]
                        for j in range(12):
                            expected=original_rows[at*12+j]+(shift[j//4] if j%4==3 and ancestor==0 else 0)
                            near(corrected_rows[at*12+j],expected,'source SmoothSprint palette translation');palette_checks+=1
        # Standalone ASan/UBSan process includes exact-size truncation buffers.
        driver=HERE/'sanitizer.c';exe=temp/'sanitizer'
        subprocess.run([*cc,'-std=c11','-O1','-g','-ffp-contract=off','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie','-I'+str(ROOT/'locomotion'),str(driver),str(ROOT/'locomotion/coh_locomotion.c'),str(ROOT/'character/coh_character.c'),'-lm','-o',str(exe)],check=True)
        env=dict(os.environ,ASAN_OPTIONS=f'detect_leaks={0 if a.disable_leak_sanitizer else 1}:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
        sanitized=subprocess.run([str(exe),str(a.fixture.resolve())],env=env,capture_output=True,text=True)
        require(sanitized.returncode==0,'sanitizer failed: '+sanitized.stderr)
        report={'schema':'coh-native-locomotion-host-proof-v1','status':'passed','passed':True,'fixture_sha256':sha(raw),
                'source_files':pins,'executed_original_functions':function_pins,'generated_oracle_sha256':sha(code.encode()),
                'native_source_sha256':sha((ROOT/'locomotion/coh_locomotion.c').read_bytes()),
                'original_clock_rate_scalar_comparisons':checks,'original_clock_rate_maximum_absolute_error':maximum,
                'original_encoded_key_scalar_comparisons':local_checks,'original_encoded_key_maximum_absolute_error':local_maximum,
                'invalid_cases':invalids,'transitions':{'ready':state.ready_entries,'run':state.run_entries,'post':state.post_entries,'cycles':state.cycles},
                'original_unused_postrun_tracks_validated_and_ignored':unused,
                'morph_smooth_sprint_translation_checks':morph_checks,'sanitizers':'ASan and UBSan passed standalone exact-buffer truncation + transitions',
                'morph_smooth_sprint_palette_scalar_comparisons':palette_checks,
                'leak_sanitizer_enabled':not a.disable_leak_sanitizer,
                'scope':json.loads((HERE/'pins.json').read_text())['scope'],'transcript':transcript,
                'android_device_execution':False,'original_full_sequencer_execution':False}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':'passed','report':str(a.output),'original_clock_scalars':checks,'original_key_scalars':local_checks,'invalid_cases':invalids}))
if __name__=='__main__':main()
