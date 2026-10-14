#!/usr/bin/env python3
"""Qualify the selected grounded directional graph with unchanged source kernels.

This executes original sequencer interrupt selection, state requirements, clock,
phase preservation and speed scaling with platform/container stubs and authentic
parsed move declarations. Full Ready2 random idles and non-ground move graphs
remain outside this deterministic fixture.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,importlib.util,json,math,os,random,re,shlex,subprocess,tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NAMES=['Ready','RunCycle','RunPost','RunPre','Idle_Walk_Post','Idle_Ready',
       'Run_Back_Pre','Run_Back_Cycle','Run_Left_Pre','Run_Left_Cycle','Run_Right_Pre','Run_Right_Cycle']
BITS={'FORWARD':1,'BACKWARD':2,'STEPLEFT':3,'STEPRIGHT':4,'IDLE':12}
FUNCTIONS=[('seqsequence.c',n) for n in ['seqSetMove','seqCycleFrame','seqStep','seqAInterruptsB',
            'getSetBits','seqSearchInterrupts','seqGetAnimScale','seqProcessInst']]
FUNCTIONS += [('entclient.c','seqGetMovementSpeedAnimScale')]

def require(value,message):
    if not value:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out
types=module('directional_character_types',HERE.parent/'character_fixture/_types.py')
Rig,Pose,Morph=types.Rig,types.Pose,types.Morph

class Loco(C.Structure):
    _fields_=[('bytes',C.POINTER(C.c_uint8)),('byte_count',C.c_size_t),('rigs',Rig*12),('clip_count',C.c_uint32)]
class State(C.Structure):
    _fields_=[('move',C.c_uint32),('frame',C.c_float),('previous_frame',C.c_float),('move_rate_scale',C.c_float)] + [
      (name,C.c_uint32) for name in ['transitions','ready_entries','run_entries','post_entries','cycles',
        'pre_entries','directional_entries','early_stop_entries','phase_preservations','direction_switches',
        'anim_incrementor','input_mask','selection_changed']]
class Blend(C.Structure):
    _fields_=[('previous',Pose),('valid',C.c_uint32),('transition_serial',C.c_uint32),('interpolation_frame',C.c_float),('rotation_blend',C.c_uint8*99),('translation_blend',C.c_uint8*99)]

def extract(text,name):
    match=re.search(r'^[^\n;{}]*\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',text,re.M)
    require(match is not None,'original function missing: '+name)
    start=match.start();index=text.index('{',start)+1;depth=1
    while depth:
        depth+=(text[index]=='{')-(text[index]=='}');index+=1
    return text[start:index]+'\n'

def sources(directory):
    pins=json.loads((HERE/'source-pins.json').read_text());texts={}
    for name,pin in pins['files'].items():
        direct=directory/name;path=direct if direct.exists() else directory/pin['path']
        raw=path.read_bytes().replace(b'\r\n',b'\n')
        require(len(raw)==pin['bytes_lf'] and sha(raw)==pin['sha256_lf'],'original source hash differs: '+str(path))
        if 'git_blob_sha' in pin:
            require(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==pin['git_blob_sha'],
                    'original Git blob differs: '+str(path))
        # seqregistration's original two bullet comments are CP1252 bytes.
        # Verify canonical bytes first; decoding never relaxes the source pin.
        texts[name]=raw.decode(pin.get('text_encoding','utf8'))
    for bit,index in BITS.items():
        require(re.search(r'^#define STATE_'+bit+r'\s+'+str(index)+r'\s*$',texts['seqstate.h'],re.M),'source state index differs: '+bit)
    return texts,pins

def declarations(texts,clip_lengths):
    includes={'sequencers/members/readies.inc':'ReadiesMembers.inc',
       'sequencers/members/encounters_cycles.inc':'EncountersCyclesMembers.inc',
       'sequencers/interrupts/encounters_idle.inc':'EncountersIdleInterrupts.inc'}
    def clean(text):return '\n'.join(line.split('#',1)[0] for line in text.splitlines())
    def expand(text):
        lines=[]
        for line in clean(text).splitlines():
            tokens=line.strip().split()
            if tokens and tokens[0].casefold()=='include':
                path=tokens[1].replace('\\','/').casefold()
                require(path in includes,'unsupported selected source include: '+path)
                lines.append(expand(texts[includes[path]]))
            else:lines.append(line)
        return '\n'.join(lines)
    moves={}
    for name in NAMES:
        selected=None
        for file in ['readies.inc','motion.inc','encounters_motion.inc']:
            text=clean(texts[file]);match=re.search(r'^Move\s+'+re.escape(name)+r'\s*\n(.*?)^MEnd\s*$',text,re.M|re.S)
            if match:selected=expand(match.group(1));break
        require(selected is not None,'authored source move missing: '+name)
        common=re.split(r'^\s*Type\s+',selected,1,flags=re.M)[0]
        props={}
        for line in common.splitlines():
            tokens=line.strip().split()
            if tokens:props.setdefault(tokens[0].casefold(),[]).append(tokens[1:])
        choices={}
        for match in re.finditer(r'^\s*Type\s+(\S+)\s*\n(.*?)^\s*TEnd\s*$',selected,re.M|re.S):
            gfx={}
            for line in match.group(2).splitlines():
                tokens=line.strip().split()
                if tokens:gfx.setdefault(tokens[0].casefold(),[]).append(tokens[1:])
            choices[match.group(1).casefold()]=gfx
        kind='huge' if 'huge' in choices else 'male';gfx=choices[kind]
        anim=gfx['anim'][0];clip=anim[0].replace('\\','/').casefold()
        first=float(anim[1]);last=float(anim[2]) if len(anim)>2 else clip_lengths[clip]
        flags=props.get('flags',[[]])[0];requires=props.get('requires',[[]])[0]
        groups=props.get('member',[[]])[0];interrupts=props.get('interrupts',[[]])[0]
        next_name=props.get('nextmove',[['Ready']])[0][0]
        cycles=props.get('cyclemove',[])
        moves[name]={'name':name,'clip':clip,'type':kind,'first':first,'last':last,
          'requires':requires,'priority':int(props.get('priority',[['0']])[0][0]),
          'members':groups,'interrupts':interrupts,'flags':flags,
          'move_rate':float(gfx.get('moverate',props.get('moverate',[['0']]))[0][0]),
          'scale':float(gfx.get('scale',props.get('scale',[['1']]))[0][0]),
          'interpolate':int(props.get('interpolate',[['5']])[0][0]),'next':next_name,
          'cycle':cycles[0][0] if cycles else None}
    # Original Ready2 branching is outside the selected deterministic graph.
    # Preserve Ready's ComplexCycle flag for source phase-reset behavior.
    moves['Ready']['cycle']='Ready'
    require(re.search(r'TypeDef huge\s+BaseSkeleton\s+huge\\skel_ready\s+ParentType\s+male',texts['player.txt']),
      'source Huge->male parent binding differs')
    return moves

PREAMBLE=r'''#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <math.h>
#include <string.h>
typedef float F32;typedef uint32_t U32;typedef float Vec3[3];
#define MAX_IRQ_ARRAY_SIZE 14
#define MAXSTATES 32
#define SEQPROCESSINST 0
#define TSTB(state,bit) ((state)[(bit)/32]&(1u<<((bit)%32)))
enum {SEQMOVE_CYCLE=1,SEQMOVE_COMPLEXCYCLE=2,SEQMOVE_MOVESCALE=4,SEQMOVE_SMOOTHSPRINT=8,
      SEQMOVE_PREDICTABLE=16,SEQMOVE_ALWAYSSIZESCALE=32,SEQMOVE_NOSIZESCALE=64,SEQMOVE_FULLSIZESCALE=128,
      SEQMOVE_NODRAW=256,SEQMOVE_PICKRANDOMLY=512,SEQMOVE_REQINPUTS=1024,SEQMOVE_FINISHCYCLE=2048};
enum {NEWMOVE_FOUND_BY_COMPLEX_CYCLING=1,NEWMOVE_FOUND_BY_REQUIREMENTS_FAILED_IN_FINISHCYCLE=2,
      NEWMOVE_FOUND_BY_NONCYCLING_MOVE_ENDED=4,NEWMOVE_FOUND_BY_SEARCH_OF_INTERRUPTS=8,
      NEWMOVE_FOUND_BY_REQUIREMENTS_FAILED_IN_CYCLE_OR_REQINPUTS=16,GFXNODE_HIDE=1};
typedef struct {int firstFrame,lastFrame;} AnimRange;
typedef struct {float scale,moveRate,smoothSprint,ragdollFrame;void*animTrack;AnimRange *animP[1];const char*type;} TypeGfx;
typedef struct {unsigned required,cycleMoveCnt;int cycleMove[2],nextMove[1];U32 interruptsBitArray[14],memberBitArray[14];} Raw;
typedef struct SeqMove {const char*name;unsigned flags;int priority;float scale,moveRate;Raw raw;TypeGfx*typeGfx[1];} SeqMove;
typedef struct {int cnt,*movesRemainingThatRequireMe;} SeqBitInfo;
typedef struct {const SeqMove*moves[12];SeqBitInfo bits[13];const char*name;} SeqInfo;
typedef struct {float frame,prev_frame;const SeqMove*move,*prev_move,*move_to_send,*move_lastframe;const TypeGfx*typeGfx;bool bRagdoll;} Animation;
typedef struct GfxNode {unsigned flags;struct GfxNode*child;float mat[4][3];} GfxNode;
typedef struct {float animScale;const char *seqname,*name,*seqTypeName;} SeqType;
typedef struct {Animation animation;SeqInfo*info;SeqType*type;float curranimscale;int moved_instantly;GfxNode*gfx_root;
   unsigned handle;const char*calculatedSeqTypeName;U32 state[1],state_lastframe[1];bool forceInterrupt;
   unsigned anim_incrementor;int move_predict_seed;bool bCurrentlyInRagdollMode;} SeqInst;
static float TIMESTEP;static int g_MaxUsedStates=13;
static struct {int quickLoadAnims;} STATE_STRUCT;
static struct {int seq_info;} game_state;
static struct {SeqInst*seq;} *current_target;
static int isDevelopmentMode(void){return 0;}
static int isSharedMemory(const void*p){(void)p;return 0;}
static const TypeGfx *seqGetTypeGfx(const SeqInfo*i,const SeqMove*m,const char*n){(void)i;(void)n;return m->typeGfx[0];}
static void seqAttachAnAnim(TypeGfx*t,int mode){(void)t;(void)mode;}
static bool sparseRequiresMet(const unsigned *requires,const U32 *state){return (*state&*requires)==*requires;}
static int randUIntGivenSeed(int*s){*s=1;return 0;}
static int qrand(void){return 0;}
static int seqScaledOnServer(const SeqInst*s){(void)s;return 0;}
static void seqDebugPrintState(const SeqInst*s,const SeqMove*m,int c,int p){(void)s;(void)m;(void)c;(void)p;}
#define eaiGet(array,j) ((*(array))[j])
#define eaSize(array) 12
#define Prefetch(p) ((void)(p))
#define testSparseBit(required,bit) ((*(required))&(1u<<(bit)))
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
void original_tick(unsigned move,float frame,float previous,unsigned last_mask,unsigned selection_changed,
                   unsigned increment,unsigned mask,float timestep,float distance,float geom,float out[4],unsigned ints[3]) {
 SeqInst s={0};SeqInfo info={0};SeqMove moves[12]={0};TypeGfx gfx[12]={0};AnimRange ranges[12]={0};
 SeqType type={0};int caches[13][12]={{0}};
 init_metadata(&info,moves,gfx,ranges,caches);
 type.animScale=1;type.seqname="player.txt";type.name="V_Arachnos_Wretch";type.seqTypeName="huge";
 s.info=&info;s.type=&type;s.curranimscale=1.f/geom;s.animation.move=&moves[move];
 s.animation.typeGfx=&gfx[move];s.animation.frame=frame;s.animation.prev_frame=previous;
 s.animation.move_lastframe=selection_changed?0:&moves[move];s.state_lastframe[0]=last_mask<<1;
 s.state[0]=mask<<1;s.anim_incrementor=increment;
 TIMESTEP=timestep;float pos[3]={distance,0,0},last[3]={0,0,0};
 float rate=seqGetMovementSpeedAnimScale(&s,pos,last);
 seqProcessInst(&s,timestep*rate);
 out[0]=(float)(s.animation.move-moves);out[1]=s.animation.frame;out[2]=s.animation.prev_frame;out[3]=rate;
 ints[0]=s.anim_incrementor;ints[1]=s.animation.move_lastframe!=s.animation.move;ints[2]=mask;
}
'''

def original_program(texts,moves):
    snippets=[];function_pins={}
    for name in ['fsqrt','SQR','lengthVec3Squared','lengthVec3']:
        match=re.search(r'^#define '+name+r'\([^\n]*$',texts['mathutil.h'],re.M)
        require(match is not None,'source length macro missing: '+name);snippets.append(match.group()+'\n')
    for file,name in FUNCTIONS:
        code=extract(texts[file],name);function_pins[name]={'file':file,'sha256_lf':sha(code.encode())};snippets.append(code)
    flags={'Cycle':1,'MoveScale':4,'SmoothSprint':8,'ReqInputs':1024,'FinishCycle':2048}
    all_irq=sorted({v.upper() for move in moves.values() for v in move['members']+move['interrupts']}|{v.upper() for v in NAMES})
    require(len(all_irq)<32,'selected interrupt bit stub capacity exceeded');irq={v:i for i,v in enumerate(all_irq)}
    declarations_c=['static void init_metadata(SeqInfo*info,SeqMove moves[12],TypeGfx gfx[12],AnimRange ranges[12],int caches[13][12]){']
    cache={}
    for index,name in enumerate(NAMES):
        m=moves[name];bits=sum(1<<BITS[b] for b in m['requires']);mf=16+sum(flags[f] for f in m['flags'])+(2 if m['cycle'] else 0)
        member=sum(1<<irq[v.upper()] for v in m['members']+[name]);interrupt=sum(1<<irq[v.upper()] for v in m['interrupts'])
        declarations_c.append(f'ranges[{index}]=(AnimRange){{{int(m["first"])},{int(m["last"])}}};')
        declarations_c.append(f'gfx[{index}].scale={m["scale"]}f;gfx[{index}].animP[0]=&ranges[{index}];gfx[{index}].type="{m["type"]}";')
        declarations_c.append(f'moves[{index}].name="{name}";moves[{index}].scale=1.f;moves[{index}].moveRate={m["move_rate"]}f;moves[{index}].priority={m["priority"]};moves[{index}].flags={mf};moves[{index}].typeGfx[0]=&gfx[{index}];')
        declarations_c.append(f'moves[{index}].raw.required={bits};moves[{index}].raw.memberBitArray[0]={member}u;moves[{index}].raw.interruptsBitArray[0]={interrupt}u;moves[{index}].raw.nextMove[0]={NAMES.index(m["next"])};info->moves[{index}]=&moves[{index}];')
        if m['cycle']:declarations_c.append(f'moves[{index}].raw.cycleMoveCnt=1;moves[{index}].raw.cycleMove[0]={NAMES.index(m["cycle"])};')
        if m['interrupts'] and m['requires']:cache.setdefault(BITS[m['requires'][0]],[]).append(index)
    for bit,indices in cache.items():
        # Move declarations were emitted in API order, but cache ordering is authored order.
        source_order=['Ready','RunPre','RunCycle','RunPost','Run_Back_Pre','Run_Back_Cycle','Run_Left_Pre','Run_Left_Cycle','Run_Right_Pre','Run_Right_Cycle','Idle_Ready','Idle_Walk_Post']
        indices.sort(key=lambda i:source_order.index(NAMES[i]));cache[bit]=indices
        for pos,index in enumerate(indices):declarations_c.append(f'caches[{bit}][{pos}]={index};')
        declarations_c.append(f'info->bits[{bit}].cnt={len(indices)};info->bits[{bit}].movesRemainingThatRequireMe=caches[{bit}];')
    declarations_c.append('}\n')
    code=PREAMBLE+'\n'.join(snippets)+'\n'+'\n'.join(declarations_c)+WRAPPER
    return code,function_pins,{str(k):[NAMES[i] for i in v] for k,v in cache.items()}

def configure(lib):
    types.configure(lib);p=C.POINTER
    lib.coh_locomotion_parse.argtypes=[p(C.c_uint8),C.c_size_t,p(Loco)];lib.coh_locomotion_parse.restype=C.c_int
    lib.coh_locomotion_init.argtypes=[p(State)]
    lib.coh_locomotion_step_directional.argtypes=[p(Loco),p(State),C.c_uint32,C.c_float,C.c_float,C.c_float];lib.coh_locomotion_step_directional.restype=C.c_int
    lib.coh_locomotion_sample.argtypes=[p(Loco),p(State),p(Morph),p(Pose)];lib.coh_locomotion_sample.restype=C.c_int
    lib.coh_locomotion_blend_init.argtypes=[p(Blend)]
    lib.coh_locomotion_sample_directional.argtypes=[p(Loco),p(State),p(Morph),C.c_float,p(Blend),p(Pose)];lib.coh_locomotion_sample_directional.restype=C.c_int
    return lib

def near(a,b,label):
    error=abs(float(a)-float(b));require(error<=4e-6+4e-6*abs(float(b)),label+f': {a} != {b}');return error

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',required=True,type=Path)
    p.add_argument('--source-directory',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--morph',type=Path);p.add_argument('--corpus',type=Path,default=HERE/'corpus');p.add_argument('--compiler',default=os.environ.get('CC','cc'))
    p.add_argument('--disable-leak-sanitizer',action='store_true',help='Use only for local ptrace/proc restrictions; ASan/UBSan remain enabled')
    a=p.parse_args();raw=a.fixture.read_bytes();texts,pins=sources(a.source_directory)
    animation=module('directional_animation_prepare',HERE.parent/'animation_fixture/prepare.py')
    clip_lengths={}
    for item in json.loads((HERE/'pins.json').read_text())['records']:
        clip=(a.corpus/item['file_name']).read_bytes()
        require(sha(clip)==item['sha256'] and len(clip)==item['size'],'authored clip hash differs')
        inspection,_=animation.inspect_animation(clip);clip_lengths[inspection['name'].replace('\\','/').casefold()]=inspection['length_frames']
    moves=declarations(texts,clip_lengths);code,function_pins,cache=original_program(texts,moves)
    cc=shlex.split(a.compiler);checks=0;maximum=0.;transcript=[];observed=set();tie_changes=0;sanitizers=None
    with tempfile.TemporaryDirectory(prefix='coh-directional-') as folder:
        temp=Path(folder);(temp/'oracle.c').write_text(code)
        result=subprocess.run([*cc,'-std=c11','-O0','-ffp-contract=off','-fno-strict-aliasing','-shared','-fPIC',str(temp/'oracle.c'),'-lm','-o',str(temp/'oracle.so')],capture_output=True,text=True)
        require(result.returncode==0,result.stderr)
        oracle=C.CDLL(str(temp/'oracle.so'));oracle.original_tick.argtypes=[C.c_uint32,C.c_float,C.c_float,C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.c_float,C.c_float,C.c_float,C.POINTER(C.c_float),C.POINTER(C.c_uint32)]
        subprocess.run([*cc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-fPIC','-shared',str(ROOT/'character/coh_character.c'),str(ROOT/'locomotion/coh_locomotion.c'),'-lm','-o',str(temp/'native.so')],check=True)
        lib=configure(C.CDLL(str(temp/'native.so')));memory=(C.c_uint8*len(raw)).from_buffer_copy(raw);loco=Loco()
        require(lib.coh_locomotion_parse(memory,len(raw),C.byref(loco))==0,'authentic directional bundle rejected');require(loco.clip_count==12,'directional bundle cardinality differs')
        for i,name in enumerate(NAMES):
            require(loco.rigs[i].first_frame==moves[name]['first'] and loco.rigs[i].last_frame==moves[name]['last'],'authored range differs: '+name)
        state=State();lib.coh_locomotion_init(C.byref(state))
        def tick(mask,dt,distance,geom,label):
            nonlocal checks,maximum,tie_changes
            previous_increment=state.anim_incrementor;expected=(C.c_float*4)();integers=(C.c_uint32*3)()
            oracle.original_tick(state.move,state.frame,state.previous_frame,state.input_mask,state.selection_changed,state.anim_incrementor,mask,dt,distance,geom,expected,integers)
            require(lib.coh_locomotion_step_directional(C.byref(loco),C.byref(state),mask,dt,distance,geom)==0,'valid tick rejected: '+label)
            for x,y in zip([state.move,state.frame,state.previous_frame,state.move_rate_scale],expected):maximum=max(maximum,near(x,y,label));checks+=1
            for x,y in zip([state.anim_incrementor,state.selection_changed,state.input_mask],integers):require(x==y,label+f' source integer {x} != {y}');checks+=1
            tie_changes+=state.anim_incrementor!=previous_increment;observed.add(NAMES[state.move])
        # Long forward/back/lateral runs, normal stops, early tap stops, reverse,
        # diagonal changes, zero-displacement wall contact and unequal frame steps.
        schedule=[]
        for mask in [1,2,4,8,1|4,1|8,2|4,2|8]:
            schedule += [(mask,1.,.7,1.3)]*90+[(0,1.,0.,1.3)]*80
        for mask in [1,2,4,8]:schedule += [(mask,1.,.02,1.3)]+[(0,1.,0.,1.3)]*80
        schedule += [(1,1.,0.,1.3)]*90+[(4,1.,.1,1.3)]*40+[(8,1.,.1,1.3)]*40+[(2,1.,.1,1.3)]*40+[(0,1.,0.,1.3)]*80
        rng=random.Random(21102026);valid_masks=[0,1,2,4,8,5,9,6,10]
        schedule += [(rng.choice(valid_masks),rng.choice([0.,.25,1.,3.]),rng.choice([0.,.01,.2,.7,1.4,5.]),rng.choice([.4,1.,1.3,3.])) for _ in range(1200)]
        for index,args in enumerate(schedule):
            tick(*args,f'transition tick{index}')
            if index%60==0:transcript.append({'tick':index,'move':NAMES[state.move],'frame':state.frame,'rate':state.move_rate_scale,'incrementor':state.anim_incrementor})
        # Exhaust source move/range/input intersections, including strict endpoints.
        for move in range(12):
            for fraction in [0.,.5,1.]:
                for mask in valid_masks:
                    for dt in [0.,.25,1.,3.]:
                        lib.coh_locomotion_init(C.byref(state));state.move=move;state.frame=loco.rigs[move].first_frame+fraction*(loco.rigs[move].last_frame-loco.rigs[move].first_frame);state.previous_frame=-1.
                        state.selection_changed=1;state.input_mask=0;state.anim_incrementor=3
                        tick(mask,dt,.25,1.3,f'exhaust move{move} phase{fraction} mask{mask} dt{dt}')
        require({'RunPre','RunCycle','RunPost','Idle_Walk_Post','Idle_Ready','Run_Back_Pre','Run_Back_Cycle','Run_Left_Pre','Run_Left_Cycle','Run_Right_Pre','Run_Right_Cycle'}<=observed,'required authored moves not observed')
        require(tie_changes>0,'source equal-priority selection was not exercised')
        # Invalid adapter inputs must fail atomically.
        lib.coh_locomotion_init(C.byref(state));before=bytes(state);invalid=0
        for mask,dt,distance,geom in [(3,1.,.1,1.3),(12,1.,.1,1.3),(16,1.,.1,1.3),(0,float('nan'),0.,1.3),(0,-1.,0.,1.3),(0,4.,0.,1.3),(0,1.,float('inf'),1.3),(0,1.,-.1,1.3),(0,1.,0.,0.),(0,1.,0.,float('nan'))]:
            require(lib.coh_locomotion_step_directional(C.byref(loco),C.byref(state),mask,dt,distance,geom)!=0,'invalid input accepted');require(bytes(state)==before,'invalid input modified state');invalid+=1
        if a.morph:
            subprocess.run([*cc,'-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-ffp-contract=off',
              '-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(ROOT/'locomotion'),
              str(HERE/'sanitizer.c'),str(ROOT/'character/coh_character.c'),str(ROOT/'locomotion/coh_locomotion.c'),
              '-lm','-o',str(temp/'sanitizer')],check=True)
            environment=os.environ.copy()
            if a.disable_leak_sanitizer:environment['ASAN_OPTIONS']='detect_leaks=0'
            result=subprocess.run([str(temp/'sanitizer'),str(a.fixture),str(a.morph)],env=environment,capture_output=True,text=True)
            require(result.returncode==0,'sanitizer driver failed:\n'+result.stdout+result.stderr)
            sanitizers={'ASan':True,'UBSan':True,'LSan':not a.disable_leak_sanitizer,
              'header_truncation_cases':128,'directional_step_sample_reset_cases':20000,
              'full_bundle_mutation_cases':(len(raw)+22)//23}
    report={'schema':'coh-native-directional-host-proof-v1','passed':True,'source_commit':pins['source_commit'],'data_commit':pins['data_commit'],
       'unchanged_functions':function_pins,'source_program_sha256':sha(code.encode()),'authentic_move_declarations':moves,
       'source_state_bit_cache':cache,'source_graph_ticks':len(schedule)+12*3*9*4,'source_comparisons':checks,
       'maximum_source_error':maximum,'equal_priority_counter_changes':tie_changes,'invalid_atomic_checks':invalid,
       'sanitizers':sanitizers,
       'observed_moves':sorted(observed),'fixture':{'bytes':len(raw),'sha256':sha(raw)},'transcript':transcript,
       'scope':'Selected 12-move grounded graph; exact original IRQ/priority/requirements/frame/rate routines with platform stubs. Ready2 random idles, full non-ground graph, combat, PlayFx and live server excluded. Source IDLE input is absent for Wretch.'}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['passed','source_graph_ticks','source_comparisons','maximum_source_error','equal_priority_counter_changes','invalid_atomic_checks']}))

if __name__=='__main__':main()
