#!/usr/bin/env python3
"""Execute unchanged original movement kernels as a host oracle.

Dependency structure/platform calls are bounded stubs; original game execution,
normal walking/collision and server prediction are deliberately outside scope.
"""
import argparse, ctypes as C, hashlib, json, math, os, random, struct, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent

def function(text,signature):
    start=text.index(signature);brace=text.index('{',start);depth=1;at=brace+1
    while depth:
        depth+=(text[at]=='{')-(text[at]=='}');at+=1
    return text[start:at]

def run(cmd):
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
    if r.returncode:raise RuntimeError('command failed: '+' '.join(map(str,cmd))+'\n'+r.stdout+r.stderr)
    return r.stdout

def scalar(v):return float(v).hex()+'f'
def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
STUBS=r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <math.h>
#include <string.h>
#define CLIENT 1
#define PI 3.14159265358979323846
#define RAD(a) (((a)*PI)*(1.0f/180.0f))
#define TIMESTEP 1.f
#define min(a,b) ((a)<(b)?(a):(b))
#define SQR(a) ((a)*(a))
#define fsqrt(a) (float)sqrt(a)
#define INLINEDBG
#define copyVec3(a,b) memcpy((b),(a),sizeof(Vec3))
#define zeroVec3(a) memset((a),0,sizeof(Vec3))
#define scaleVec3(a,s,b) do{unsigned k;for(k=0;k<3;k++)(b)[k]=(a)[k]*(s);}while(0)
#define addVec3(a,b,c) do{unsigned k;for(k=0;k<3;k++)(c)[k]=(a)[k]+(b)[k];}while(0)
#define subVec3(a,b,c) do{unsigned k;for(k=0;k<3;k++)(c)[k]=(a)[k]-(b)[k];}while(0)
#define velIsZero(a) ((a)[0]==0&&(a)[1]==0&&(a)[2]==0)
#define SETB(state,bit) ((state)[0]|=1u<<(bit))
#define STATE_FORWARD 0
#define STATE_BACKWARD 1
#define STATE_STEPLEFT 2
#define STATE_STEPRIGHT 3
#define STATE_AIR 4
#define STATE_FLY 5
#define STATE_STUN 6
#define STATE_ICESLIDE 7
#define STATE_NINJA_RUN 8
#define STATE_PLAYERWALK 9
#define STATE_BEAST_RUN 10
#define STATE_STEAM_JUMP 11
#define STATE_HOVER_BOARD 12
#define STATE_MAGIC_CARPET 13
#define STATE_PARKOUR_RUN 14
#define STATE_JUMP 15
#define STATE_SLIDING 16
#define STATE_BOUNCING 17
#define STATE_BIGFALL 18
#define STATE_HEADPAIN 19
#define STATE_TEST0 20
#define MOVETYPE_NOCOLL 1
#define MOVETYPE_FLY 2
#define MOVETYPE_JUMPPACK 4
#define ENTPOS(e) ((e)->pos)
#define ENTPOSY(e) ((e)->pos[1])
#define CSC_ANGLE_BITS 11
#define CSC_ANGLE_F32_TO_U32(x) ((U32)(0.5 + ((x) + PI) * (1 << CSC_ANGLE_BITS) / (2 * PI)))
#define CSC_ANGLE_U32_TO_F32(x) ((F32)(x) * (2 * PI) / (1 << CSC_ANGLE_BITS) - PI)
typedef int ControlId;typedef float F32;typedef float Vec3[3];typedef float Mat3[3][3];
typedef uint8_t U8;typedef uint16_t U16;typedef uint32_t U32;typedef int32_t S32;
enum {CONTROLID_FORWARD=0,CONTROLID_BACKWARD,CONTROLID_LEFT,CONTROLID_RIGHT,CONTROLID_HORIZONTAL_MAX,CONTROLID_UP=4,CONTROLID_DOWN,CONTROLID_BINARY_MAX};
static const int opposite_control_id[6]={1,0,3,2,5,4};
F32 near_same_vec3_tol_squared=0.001f;static const Vec3 zerovec3={0,0,0};
typedef struct {Vec3 vel;int jump_released;} Input;
typedef struct {Input input;Vec3 vel,last_pos;F32 move_time,heightILastTouchedTheGround;int falling,jumping,sliding,bouncing;} MotionState;
typedef struct {F32 speed[3],speed_back,jump_height;int controls_input_ignored,fly,stun,jumppack,no_jump_repeat,glide,ninja_run,walk,beast_run,steam_jump,hover_board,magic_carpet,parkour_run;} ServerControlState;
typedef struct ControlStateChange {struct ControlStateChange *next;int control_id,state;U32 time_stamp_ms;} ControlStateChange;
typedef struct {ControlStateChange*head;int count;} List;
typedef struct {int noStrafe;} SeqType;
typedef struct {U32 state[1];SeqType *type;} SeqInst;
typedef struct {MotionState *motion;Vec3 pos;F32 timestep;int move_type;struct {int afk;} *pl;SeqInst *seq;} Entity;
typedef struct {struct{U8 down_now,use_now,affected_last_frame;U32 total_ms[6],start_ms[6],max_ms;}dir_key;ServerControlState*server_state;int controls_input_ignored_this_csc,alwaysmobile,controldebug,nocoll,recover_from_landing_timer,no_strafe;F32 speed_scale,max_speed_scale,yaw_swap_timer,last_vel_yaw;Vec3 last_inp_vel;int anim_test[10];struct{Vec3 cur,motion;}pyr;List csc_to_process_list,csc_processed_list;int mapserver_responding;} ControlState;
static ControlState control_state;
static void addControlStateChange(List *list,ControlStateChange*c,int b){(void)list;(void)c;(void)b;}
static void destroyControlStateChange(ControlStateChange*c){(void)c;}
static void MouseSpringInputVel(Vec3 v,F32 speed){(void)v;(void)speed;}
static int seqGetStateNumberFromName(const char*s){(void)s;return -1;}
static int isDevelopmentMode(void){return 0;}
static void seqOrState(U32*s,int value,int bit){if(value)SETB(s,bit);}
static void mathutil_sincosf(F32 a,F32*s,F32*c){*s=sinf(a);*c=cosf(a);}
static void entUpdatePosInterpolated(Entity*e,Vec3 pos){copyVec3(pos,e->pos);}
'''

def source_program(src):
    p=src['pmotion.c'];player=src['player.c'];m=src['motion.c'];mh=src['mathutil.h'];mc=src['mathutil.c']
    kernels='\n'.join(function(mc,s) for s in ['F32 fixAngle(','F32 subAngle(','F32 addAngle(','void createMat3RYP('])
    kernels+='\n'+'\n'.join(function(mh,s) for s in ['static INLINEDBG void mulVecMat3(','static INLINEDBG int nearSameVec3(','static INLINEDBG F32 normalVec3('])
    kernels+='\n'+'\n'.join(function(p,s) for s in ['const char* pmotionGetBinaryControlName(','void pmotionUpdateControlsPrePhysics(','void pmotionUpdateControlsPostPhysics(','void pmotionSetState(','void pmotionSetVel('])
    kernels+='\n'+function(player,'static F32 clampF32abs(')+'\n'+function(player,'static void handleBinaryStateChange(')+'\n'+function(player,'static void playerAdjustMotionPYR(')+'\n'+function(m,'void entMoveNoColl(')
    # Unchanged normal-strafe body-yaw slice; excludes forced/no-strafe modes.
    body_start=player.index('        // Calculate the yaw to the control direction.')
    body_end=player.index('        //printf("pyr:',body_start)
    body=player[body_start:body_end]
    kernels+='\nstatic float source_body(float old,ControlState*controls) {Vec3 pyr_start={0,old,0},body_pyr={0,0,0};F32 yaw_diff;F32 time_to_realign=0;\n'+body+'\nreturn body_pyr[1];}\n'
    driver=r'''
static MotionState motion;static ServerControlState scs;static ControlState cs;
static Entity e;static SeqInst seq;static SeqType type;static U32 tick,clock_ms;static float body_yaw;
void oracle_init(float yaw) {
 memset(&motion,0,sizeof(motion));memset(&scs,0,sizeof(scs));memset(&cs,0,sizeof(cs));memset(&e,0,sizeof(e));memset(&seq,0,sizeof(seq));
 scs.speed[0]=scs.speed[1]=scs.speed[2]=1;scs.speed_back=.5f;scs.no_jump_repeat=1;
 e.motion=&motion;e.seq=&seq;e.timestep=1;seq.type=&type;cs.server_state=&scs;cs.nocoll=1;
 cs.pyr.cur[1]=yaw;body_yaw=yaw;tick=clock_ms=0;control_state.mapserver_responding=1;
}
void oracle_step(U32 dirs,float yaw,float out[12],U32 integers[8]) {
 unsigned i;U8 use_prev=cs.dir_key.use_now;U32 cur=(++tick)*1000u/30u;Mat3 mat;Vec3 vel;ControlStateChange csc;
 for(i=0;i<4;i++)if(!!(dirs&(1u<<i))!=!!(cs.dir_key.down_now&(1u<<i))) {
  memset(&csc,0,sizeof(csc));csc.control_id=i;csc.state=!!(dirs&(1u<<i));csc.time_stamp_ms=clock_ms;
  cs.csc_to_process_list.head=&csc;cs.csc_to_process_list.count=1;handleBinaryStateChange(&e,&cs,use_prev);
 }
 cs.pyr.cur[1]=fixAngle(yaw);playerAdjustMotionPYR(&e,&cs);
 pmotionUpdateControlsPrePhysics(&e,&cs,(int)cur);pmotionSetVel(&e,&cs,1);
 copyVec3(motion.input.vel,cs.last_inp_vel);memset(seq.state,0,sizeof(seq.state));pmotionSetState(&e,&cs);
 copyVec3(motion.input.vel,out+3);createMat3RYP(mat,cs.pyr.motion);mulVecMat3(motion.input.vel,mat,vel);
 copyVec3(vel,motion.input.vel);copyVec3(vel,out+6);body_yaw=source_body(body_yaw,&cs);entMoveNoColl(&e);
 copyVec3(e.pos,out);out[9]=cs.pyr.motion[1];out[10]=body_yaw;out[11]=motion.move_time;
 pmotionUpdateControlsPostPhysics(&cs,(int)cur);clock_ms=cur;
 for(i=0;i<6;i++)integers[i]=cs.dir_key.total_ms[i];integers[6]=cs.dir_key.use_now;integers[7]=seq.state[0]&15u;
}
'''
    return STUBS+kernels+driver,body

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,default=ROOT);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--write-goldens',action='store_true');ap.add_argument('--sanitize',action='store_true');args=ap.parse_args()
    pins=json.loads((HERE/'source-pins.json').read_text());src={}
    for item in pins['files']:
        relative=item['path'];paths=[args.source_root/relative,args.source_root/relative.replace('upstream/ouroboros/',''),args.source_root/Path(relative).name]
        path=next((p for p in paths if p.is_file()),paths[0]);text=path.read_text().replace('\r\n','\n').rstrip('\n')+'\n'
        assert hashlib.sha256(text.encode()).hexdigest()==item['sha256_lf'],f'original source pin mismatch {path}'
        src[Path(relative).name]=text
    program,body=source_program(src);cc=os.environ.get('CC','cc')
    flags=['-std=c11','-O1','-fno-fast-math','-ffp-contract=off','-Wall','-Wextra','-fno-strict-aliasing']
    # The unchanged source has dead debug locals and one debug-only uninitialized local.
    originals=['-Wno-unused-variable','-Wno-unused-but-set-variable','-Wno-misleading-indentation','-Wno-maybe-uninitialized']
    cases=[];rng=random.Random(17302026)
    # Direction ramps, sustained boosts, diagonal/opposite, wrap and reversal cases.
    for yaw in [0,.7,-.8,f32(math.pi),f32(-math.pi)]:
        for dirs in [1,2,4,8,1|8,2|4,1|2,4|8]:
            for t in range(45):cases.append((int(t==0),dirs if t<35 else 0,f32(yaw)))
    for t in range(640):cases.append((int(t==0),rng.randrange(16),f32(rng.uniform(-math.pi,math.pi))))
    rows=[]
    with tempfile.TemporaryDirectory(prefix='coh-motion-source-') as temp:
        temp=Path(temp);source=temp/'original.c';source.write_text(program);library=temp/'original.so'
        run([cc,*flags,*originals,'-shared','-fPIC',str(source),'-lm','-o',str(library)])
        oracle=C.CDLL(str(library));oracle.oracle_init.argtypes=[C.c_float];oracle.oracle_step.argtypes=[C.c_uint32,C.c_float,C.POINTER(C.c_float),C.POINTER(C.c_uint32)]
        for reset,dirs,yaw in cases:
            if reset:oracle.oracle_init(yaw)
            floats=(C.c_float*12)();integers=(C.c_uint32*8)();oracle.oracle_step(dirs,yaw,floats,integers)
            rows.append((reset,dirs,yaw,list(floats),list(integers)))
        header=ROOT/'native-android/motion/motion_goldens.h'
        lines=['/* Generated from unchanged pinned original movement kernels. */','#ifndef COH_MOTION_GOLDENS_H','#define COH_MOTION_GOLDENS_H','typedef struct {unsigned reset,dirs;float yaw,values[12];unsigned integers[8];} CohMotionGolden;',f'#define COH_MOTION_GOLDEN_COUNT {len(rows)}u','static const CohMotionGolden coh_motion_goldens[] = {']
        for reset,dirs,yaw,floats,integers in rows:lines.append('{'+f'{reset},{dirs},{scalar(yaw)}'+',{'+','.join(scalar(x) for x in floats)+'},{'+','.join(map(str,integers))+'}},')
        lines+=['};','#endif',''];generated='\n'.join(lines)
        if args.write_goldens:header.write_text(generated)
        else:assert header.read_text()==generated,'runtime goldens differ from rebuilt unchanged original oracle'
        driver=temp/'native-check.c';driver.write_text('#include <stdio.h>\n#include "coh_motion.h"\nint main(void){CohMotionProof p;int ok=coh_motion_selftest(&p);printf("%u %u %u %u %.9g\\n",p.checks,p.failed,p.source_cases,p.adapter_cases,(double)p.max_source_error);return ok?0:1;}\n')
        extra=['-fsanitize=address,undefined','-fno-omit-frame-pointer'] if args.sanitize else []
        run([cc,*flags,'-Werror',*extra,'-I',str(header.parent),str(driver),str(header.parent/'coh_motion.c'),str(header.parent/'coh_motion_selftest.c'),'-lm','-o',str(temp/'native')])
        result=run([str(temp/'native')]);checks,failed,source_cases,adapter_cases,error=result.split()
    report={'schema':'coh-native-motion-host-proof-v1','passed':True,'source_revision':pins['source_revision'],'source_cases':int(source_cases),'adapter_cases':int(adapter_cases),'checks':int(checks),'failed':int(failed),'max_source_error':float(error),'unchanged_functions':['pmotionUpdateControlsPrePhysics','pmotionUpdateControlsPostPhysics','pmotionSetVel','pmotionSetState','handleBinaryStateChange','playerAdjustMotionPYR','entMoveNoColl','fixAngle','subAngle','addAngle','createMat3RYP','mulVecMat3','normalVec3','nearSameVec3'],'statement_slices':['playerAdjustBodyPYR normal-strafe yaw, time_to_realign=0'],'body_slice_sha256':hashlib.sha256(body.encode()).hexdigest(),'original_program_sha256':hashlib.sha256(program.encode()).hexdigest(),'goldens_sha256':hashlib.sha256(header.read_bytes()).hexdigest(),'sanitizers':'ASan and UBSan on native adaptation; original aliasing kernel compiled without strict aliasing' if args.sanitize else None,'scope':'Bounded horizontal offline source NOCOLL controls, fixed30Hz, neutral source movement parameters. Excludes normal WALK/collision, jumping, live server, prediction, analog speed and full playerAdjustBodyPYR.'}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in ['passed','source_cases','checks','failed','max_source_error']}))
if __name__=='__main__':main()
