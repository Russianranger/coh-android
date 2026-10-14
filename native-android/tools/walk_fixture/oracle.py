#!/usr/bin/env python3
"""Compile unchanged upstream WALK velocity functions in an isolated host oracle.

World queries and entity collision are deliberately stubbed. This oracle proves
velocity/surface laws only, rather than asserting full original-world equivalence.
"""
import argparse
import ctypes as C
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import struct
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

def function(text, signature):
    start = text.index(signature)
    brace = text.index('{', start)
    depth, at = 1, brace + 1
    while depth:
        depth += (text[at] == '{') - (text[at] == '}')
        at += 1
    return text[start:at], text.count('\n', 0, start) + 1, text.count('\n', 0, at) + 1

def normalized(path):
    return path.read_text().replace('\r\n', '\n').rstrip('\n') + '\n'

def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]

def run(command):
    result = subprocess.run(command, text=True, capture_output=True, timeout=90)
    if result.returncode:
        raise RuntimeError(' '.join(map(str, command)) + '\n' + result.stdout + result.stderr)
    return result.stdout

STUBS = r'''
#include <stdint.h>
#include <string.h>
#include <math.h>
#define CLIENT 0
#define MDBG 0
#define INLINEDBG
#define SURFACE_GROUND 0
#define SURFACE_AIR 1
#define SURFTYPE_GROUND 1
#define SURFTYPE_WALL 0
#define DEFAULT_RADIUS 1.0f
#define PERFINFO_AUTO_START(a,b) ((void)0)
#define PERFINFO_AUTO_STOP() ((void)0)
#define SQR(a) ((a)*(a))
#define min(a,b) ((a)<(b)?(a):(b))
#define max(a,b) ((a)>(b)?(a):(b))
#define MINMAX(a,b,c) min(max((a),(b)),(c))
#define fsqrt(a) ((float)sqrt(a))
#define fatan2(a,b) atan2((a),(b))
#define copyVec3(a,b) memcpy((b),(a),sizeof(Vec3))
#define zeroVec3(a) memset((a),0,sizeof(Vec3))
#define scaleVec3(a,s,b) do{unsigned k;float scale_=(s);for(k=0;k<3;k++)(b)[k]=(a)[k]*scale_;}while(0)
#define addVec3(a,b,c) do{unsigned k;for(k=0;k<3;k++)(c)[k]=(a)[k]+(b)[k];}while(0)
#define subVec3(a,b,c) do{unsigned k;for(k=0;k<3;k++)(c)[k]=(a)[k]-(b)[k];}while(0)
#define setVec3(v,a,b,c) ((v)[0]=(a),(v)[1]=(b),(v)[2]=(c))
#define dotVec3(a,b) ((a)[0]*(b)[0]+(a)[1]*(b)[1]+(a)[2]*(b)[2])
#define lengthVec3Squared(v) dotVec3((v),(v))
#define lengthVec3(v) fsqrt(lengthVec3Squared(v))
#define lengthVec3XZ(v) fsqrt(SQR((v)[0])+SQR((v)[2]))
#define vec3IsZero(v) ((v)[0]==0&&(v)[1]==0&&(v)[2]==0)
#define sameVec3(a,b) ((a)[0]==(b)[0]&&(a)[1]==(b)[1]&&(a)[2]==(b)[2])
#define nearSameVec3(a,b) sameVec3((a),(b))
#define ENTPOS(e) ((e)->pos)
typedef float F32;typedef int32_t S32;typedef uint32_t U32;
typedef float Vec3[3];typedef float Mat3[3][3];typedef float Mat4[4][3];
typedef struct {F32 traction,friction,bounce,gravity,max_speed;} SurfaceParams;
typedef struct {Vec3 vel;SurfaceParams surf_mods[2];F32 max_speed_scale;int flying,no_slide_physics;} MotionInput;
typedef struct {MotionInput input;Vec3 vel,last_pos,surf_normal,last_surf_normal,prev_surf_normal;
 int falling,jumping,on_poly_edge,on_surf,was_on_surf,jump_held,last_surf_type,lastSurfFlags,lastGroundSurfFlags;
 int low_traction_steps_remaining,hit_stumble_kill_velocity_on_impact;F32 hitStumbleTractionLoss;} MotionState;
typedef struct {MotionState*motion;F32 timestep;Vec3 pos;} Entity;
typedef struct {U32 flags;} CTri;
typedef struct {CTri*ctri;Mat4 mat;} CollInfo;
static CollInfo last_surf;
static const Vec3 zerovec3={0,0,0};
static const Mat4 unitmat={{1,0,0},{0,1,0},{0,0,1},{0,0,0}};
static void mathutil_sincosf(F32 a,F32*s,F32*c){*s=sinf(a);*c=cosf(a);}
static void entUpdatePosInterpolated(Entity*e,const Vec3 p){copyVec3(p,e->pos);}
static void checkEntColl(Entity*e,int mode,const Mat3 control_mat){(void)e;(void)mode;(void)control_mat;}
static void entWorldMoveMe(Entity*e,SurfaceParams*surf){(void)e;(void)surf;}
'''

SLIDE_STUBS = r'''
static unsigned slide_contact_count,slide_query_count,slide_grid_count;
static int slide_grid_hit;
static float slide_contacts[9];
static int collide(Vec3 start,Vec3 end,CollInfo*coll,F32 radius,U32 flags){
 (void)start;(void)end;(void)radius;(void)flags;
 unsigned index=slide_query_count++;
 if(index>=slide_contact_count)return 0;
 memset(coll,0,sizeof(*coll));copyVec3(slide_contacts+3*index,coll->mat[3]);return 1;
}
static int collGrid(int ignored,Vec3 start,Vec3 end,CollInfo*coll,F32 radius,U32 flags){
 (void)ignored;(void)start;(void)end;(void)coll;(void)radius;(void)flags;
 slide_grid_count++;return slide_grid_hit;
}
'''

DRIVER = r'''
void oracle_velocity(float timestep,unsigned flags,unsigned state,const float input[3],
                     const float oldvel[3],const float normal[3],float out[3]) {
 MotionState m={0};Entity e={0};CTri tri={flags};Mat3 control={{1,0,0},{0,1,0},{0,0,1}};
 e.motion=&m;e.timestep=timestep;
 for(unsigned i=0;i<2;i++)m.input.surf_mods[i]=(SurfaceParams){1,1,1,1,1};
 m.falling=!!(state&1);m.on_surf=!!(state&2);m.input.flying=!!(state&4);
 m.low_traction_steps_remaining=!!(state&8);m.was_on_surf=!!(state&16);m.jump_held=!!(state&32);
 m.last_surf_type=SURFTYPE_GROUND;m.lastSurfFlags=(int)flags;m.lastGroundSurfFlags=(int)flags;
 copyVec3(input,m.input.vel);copyVec3(oldvel,m.vel);copyVec3(normal,m.surf_normal);
 copyVec3(normal,m.last_surf_normal);copyVec3(normal,m.prev_surf_normal);
 memset(&last_surf,0,sizeof(last_surf));last_surf.ctri=m.on_surf?&tri:0;copyVec3(normal,last_surf.mat[1]);
 entWorldCollide(&e,control);copyVec3(m.vel,out);
}
void oracle_surface(unsigned flags,unsigned state,const float normal[3],float out[5]){
 MotionState m={0};Entity e={0};SurfaceParams surf;e.motion=&m;
 m.falling=!!(state&1);m.input.flying=!!(state&4);copyVec3(normal,m.surf_normal);
 entWorldGetSurface(&e,&surf);entWorldApplyTextureOverrides(&surf,(int)flags);
 out[0]=surf.traction;out[1]=surf.friction;out[2]=surf.bounce;out[3]=surf.gravity;out[4]=surf.max_speed;
}
void oracle_slide(const float topin[3],const float botin[3],const float velin[3],
                  unsigned count,const float contacts[9],int fallback_hit,float out[9],unsigned status[4]){
 MotionState m={0};Entity e={0};Vec3 top,bot;e.motion=&m;
 copyVec3(topin,top);copyVec3(botin,bot);copyVec3(velin,m.vel);
 slide_contact_count=count>3?3:count;slide_query_count=slide_grid_count=0;
 slide_grid_hit=fallback_hit;memcpy(slide_contacts,contacts,sizeof(slide_contacts));
 memset(&last_surf,0,sizeof(last_surf));m.last_surf_type=SURFTYPE_GROUND;
 int result=SlideWall(&e,top,bot,bot);
 copyVec3(top,out);copyVec3(bot,out+3);copyVec3(m.vel,out+6);
 status[0]=(unsigned)result;status[1]=slide_query_count;status[2]=slide_grid_count;status[3]=(unsigned)m.last_surf_type;
}
'''

def program(world, mathc, mathh, gridh):
    declarations = []
    provenance = []
    enum_start=gridh.index('typedef enum')
    enum_end=gridh.index('} CollFlags;',enum_start)+len('} CollFlags;')
    flags=gridh[enum_start:enum_end]
    provenance.append({'file':'gridcoll.h','signature':'typedef enum CollFlags',
                       'first_line':gridh.count('\n',0,enum_start)+1,'last_line':gridh.count('\n',0,enum_end)+1,
                       'sha256_lf':hashlib.sha256(flags.encode()).hexdigest()})
    macros=[]
    for name in ['SQR','fsqrt','fatan2','copyVec3','setVec3same','zeroVec3','scaleVec3','addVec3','subVec3',
                 'setVec3','dotVec3','lengthVec3Squared','lengthVec3','lengthVec3SquaredXZ','lengthVec3XZ',
                 'vec3IsZero','sameVec3','MINMAX']:
        match=re.search(r'^#define\s+'+name+r'\([^\n]+',mathh,re.M)
        assert match,name
        assert not match.group().endswith('\\'),name
        macros.append('#undef '+name+'\n'+match.group())
    macro_text='\n'.join(macros)
    provenance.append({'file':'mathutil.h','signature':'original arithmetic macro definitions',
                       'names':['SQR','fsqrt','fatan2','copyVec3','setVec3same','zeroVec3','scaleVec3','addVec3','subVec3',
                                'setVec3','dotVec3','lengthVec3Squared','lengthVec3','lengthVec3SquaredXZ','lengthVec3XZ',
                                'vec3IsZero','sameVec3','MINMAX'],
                       'sha256_lf':hashlib.sha256(macro_text.encode()).hexdigest()})
    for name, text, signatures in [
        ('mathutil.h', mathh, ['static INLINEDBG F32 normalVec3(', 'static INLINEDBG void mulVecMat3(']),
        ('mathutil.c', mathc, ['void getVec3YP(', 'void createMat3RYP(', 'void camLookAt(', 'void transposeMat3Copy(']),
        ('entworldcoll.c', world, ['static int SlideWall(', 'static void reflectOffPlane(', 'static void makeSteepSlopesSlippery(',
          'void entWorldGetSurface(', 'SurfaceParams *entWorldGetSurfaceModifier(', 'void entWorldApplySurfMods(',
          'void entWorldApplyTextureOverrides(', 'void entWorldCollide(']),
    ]:
        for signature in signatures:
            body, first, last = function(text, signature)
            declarations.append(body)
            provenance.append({'file': name, 'signature': signature, 'first_line': first, 'last_line': last,
                               'sha256_lf': hashlib.sha256(body.encode()).hexdigest()})
    return STUBS + macro_text + '\n' + flags + SLIDE_STUBS + '\n'.join(declarations) + DRIVER, provenance

def slide_cases():
    rows=[]
    for count in range(4):
        for fallback in [0,1]:
            for top in [(0,0,0),(-5,0,0),(5,0,5)]:
                for vel in [(0,0,1),(0,1,1),(0,-1,1)]:
                    for contacts in [[.25,3.5,0, 0,3.5,.25, -.5,3.5,0],
                                     [0,3.5,0, 0,3.5,0, 0,3.5,0]]:
                        rows.append((top,(0,0,0),vel,count,contacts,fallback))
    return rows

def cases():
    result = []
    # Complete primary branch cross-product: grounded/unsupported/air/flying,
    # released/opposing/perpendicular/overspeed input, defaults/slick/icy/bouncy,
    # low traction, three timesteps, and original slope traction transitions.
    normals = [(0,1,0), (.6,.8,0), (0,.5,math.sqrt(.75)), (.8,.6,0)]
    inputs = [(0,0,0),(0,0,1),(0,0,-.5),(1,0,0),(.70710677,0,.70710677),(.25,0,0)]
    velocities = [(0,0,0),(0,0,1),(1,0,0),(0,0,2),(0,-.3,0),(0,.3,1)]
    for state in [2,0,1,5,10,17,33]:
        for flags in [0,1<<20,1<<21,1<<22]:
            for timestep in [.5,1,2]:
                for normal in normals:
                    for inp in inputs:
                        for vel in velocities:
                            result.append((f32(timestep),flags,state,tuple(map(f32,inp)),tuple(map(f32,vel)),tuple(map(f32,normal))))
    rng=random.Random(20191014)
    for _ in range(640):
        x,z=rng.uniform(-.5,.5),rng.uniform(-.5,.5)
        normal=(x,math.sqrt(1-x*x-z*z),z)
        result.append((f32(rng.uniform(.1,2)),rng.choice([0,1<<20,1<<21,1<<22]),rng.choice([0,1,2,5,10]),
                       tuple(f32(rng.uniform(-1,1)) if i!=1 else 0 for i in range(3)),
                       tuple(f32(rng.uniform(-2,2)) for _ in range(3)),tuple(map(f32,normal))))
    return result

def load(path, expected):
    text=normalized(path)
    actual=hashlib.sha256(text.encode()).hexdigest()
    if actual!=expected:raise AssertionError(f'source pin mismatch: {path}: {actual}')
    return text

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-root',type=Path,default=ROOT)
    ap.add_argument('--world-source',type=Path)
    ap.add_argument('--grid-header',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--goldens-header',type=Path)
    ap.add_argument('--goldens-json',type=Path)
    ap.add_argument('--slide-goldens-json',type=Path)
    ap.add_argument('--program',type=Path)
    args=ap.parse_args()
    pins=json.loads((HERE/'oracle-source-pins.json').read_text())
    source={}
    for item in pins['files']:
        path=item['path'];choices=[args.source_root/path,args.source_root/path.replace('upstream/ouroboros/',''),args.source_root/Path(path).name]
        if args.world_source and Path(path).name=='entworldcoll.c':choices.insert(0,args.world_source)
        if args.grid_header and Path(path).name=='gridcoll.h':choices.insert(0,args.grid_header)
        chosen=next((p for p in choices if p.is_file()),choices[0])
        source[Path(path).name]=load(chosen,item['sha256_lf'])
    text,provenance=program(source['entworldcoll.c'],source['mathutil.c'],source['mathutil.h'],source['gridcoll.h'])
    if args.program:args.program.parent.mkdir(parents=True,exist_ok=True);args.program.write_text(text)
    with tempfile.TemporaryDirectory(prefix='coh-walk-source-') as tmp:
        tmp=Path(tmp);path=tmp/'original.c';path.write_text(text);lib=tmp/'original.so'
        run([os.environ.get('CC','cc'),'-std=c11','-O1','-fno-fast-math','-ffp-contract=off',
             '-fno-strict-aliasing','-Wno-incompatible-pointer-types','-shared','-fPIC',str(path),'-lm','-o',str(lib)])
        oracle=C.CDLL(str(lib));oracle.oracle_velocity.argtypes=[C.c_float,C.c_uint,C.c_uint,*[C.POINTER(C.c_float)]*4]
        rows=[]
        for timestep,flags,state,inp,vel,normal in cases():
            out=(C.c_float*3)();oracle.oracle_velocity(timestep,flags,state,*[(C.c_float*3)(*v) for v in [inp,vel,normal]],out)
            assert all(math.isfinite(x) for x in out),(timestep,flags,state,inp,vel,normal,list(out))
            rows.append([timestep,flags,state,list(inp),list(vel),list(normal),list(out)])
        oracle.oracle_slide.argtypes=[*[C.POINTER(C.c_float)]*3,C.c_uint,C.POINTER(C.c_float),C.c_int,C.POINTER(C.c_float),C.POINTER(C.c_uint)]
        slide_rows=[]
        for top,bot,vel,count,contacts,fallback in slide_cases():
            out=(C.c_float*9)();status=(C.c_uint*4)()
            oracle.oracle_slide(*[(C.c_float*3)(*v) for v in [top,bot,vel]],count,(C.c_float*9)(*contacts),fallback,out,status)
            assert all(math.isfinite(x) for x in out)
            slide_rows.append([list(top),list(bot),list(vel),count,contacts,fallback,list(out),list(status)])
    if args.goldens_json:args.goldens_json.parent.mkdir(parents=True,exist_ok=True);args.goldens_json.write_text(json.dumps(rows,separators=(',',':'))+'\n')
    if args.slide_goldens_json:args.slide_goldens_json.parent.mkdir(parents=True,exist_ok=True);args.slide_goldens_json.write_text(json.dumps(slide_rows,separators=(',',':'))+'\n')
    if args.goldens_header:
        scalar=lambda x:float(x).hex()+'f'
        lines=['/* Generated by independently compiled unchanged source entWorldCollide. */',
               '#ifndef COH_WALK_SOURCE_GOLDENS_H','#define COH_WALK_SOURCE_GOLDENS_H',
               'typedef struct {float timestep;unsigned flags,state;float input[3],vel[3],normal[3],out[3];} CohWalkSourceGolden;',
               f'#define COH_WALK_SOURCE_GOLDEN_COUNT {len(rows)}u','static const CohWalkSourceGolden coh_walk_source_goldens[] = {']
        for dt,flags,state,inp,vel,norm,out in rows:
            lines.append('{'+f'{scalar(dt)},{flags}u,{state}u,'+','.join('{'+','.join(map(scalar,v))+'}' for v in [inp,vel,norm,out])+'},')
        lines+=['};','#endif','']
        args.goldens_header.parent.mkdir(parents=True,exist_ok=True);args.goldens_header.write_text('\n'.join(lines))
    receipt={'schema':'coh-native-walk-original-oracle-v1','passed':True,'source_cases':len(rows),'slide_transcript_cases':len(slide_rows),
             'upstream_source_revision':pins['upstream_source_revision'],'source_revision':pins['source_revision'],
             'unchanged_functions':provenance,'original_program_sha256':hashlib.sha256(text.encode()).hexdigest(),
             'scope':'Original active entWorldCollide velocity and surface laws; neutral movement modifiers; exact original math helpers. Separate original SlideWall contact transcript cases. World query/entity callbacks are stubbed. Does not prove original world queries or full original WALK equivalence.',
             'stubs':['Entity/MotionState layout','world and entity collision callbacks','platform math intrinsics mapped to libm','performance instrumentation']}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'passed':True,'source_cases':len(rows),'slide_transcript_cases':len(slide_rows),'functions':len(provenance)}))

if __name__=='__main__':main()
