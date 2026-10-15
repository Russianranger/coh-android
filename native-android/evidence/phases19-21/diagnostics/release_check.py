#!/usr/bin/env python3
"""Local diagnostic: genuine-floor WALK coasting vs independent original source.

Reproduce from a full repository checkout and its prepared fixture:
  python3 native-android/evidence/phases19-21/diagnostics/release_check.py \
    --source-root . --fixture /path/to/walkable.bin \
    --output /path/to/host-walk-release-settling-proof.json

This is diagnostic evidence, not an APK builder, runtime change, Android test,
full tracker/grid equivalence claim, or physical AYN Thor acceptance.
"""
import argparse
import ctypes as C
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile

SCRIPT=Path(__file__).resolve()
ROOT=next(p for p in SCRIPT.parents if (p/'native-android/tools/walk_fixture/oracle.py').is_file())
ORACLE_PATH=ROOT/'native-android/tools/walk_fixture/oracle.py'
spec=importlib.util.spec_from_file_location('original_walk_oracle',ORACLE_PATH)
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)

NATIVE_DRIVER=r'''
#include "native-android/walk/coh_walk.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint32_t u32(const unsigned char*b){return (uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;}
static float f32(const unsigned char*b){uint32_t x=u32(b);float f;memcpy(&f,&x,4);return f;}
static void vec(const float v[3]){printf("[%.9g,%.9g,%.9g]",v[0],v[1],v[2]);}
int main(int argc,char**argv){
 if(argc!=2)return 2;FILE*f=fopen(argv[1],"rb");if(!f)return 2;
 if(fseek(f,0,SEEK_END)){fclose(f);return 2;}long n=ftell(f);if(n<128||n>16*1024*1024||fseek(f,0,SEEK_SET)){fclose(f);return 2;}
 unsigned char*b=malloc((size_t)n);if(!b){fclose(f);return 2;}if(fread(b,1,(size_t)n,f)!=(size_t)n){free(b);fclose(f);return 2;}fclose(f);
 if(memcmp(b,"COHWALK1",8)||u32(b+8)!=1){free(b);return 2;}uint32_t count=u32(b+24),off=u32(b+52);
 if(!count||count>8192||off>(uint32_t)n||count>((uint32_t)n-off)/40){free(b);return 2;}
 CohWalkTriangle*tri=calloc(count,sizeof(*tri));if(!tri){free(b);return 2;}
 for(unsigned i=0;i<count;i++){for(unsigned v=0;v<3;v++)for(unsigned k=0;k<3;k++)tri[i].v[v][k]=f32(b+off+i*40+(v*3+k)*4);tri[i].flags=u32(b+off+i*40+36);}
 float lo[3],hi[3],spawn[3];for(unsigned k=0;k<3;k++){lo[k]=f32(b+68+k*4);hi[k]=f32(b+80+k*4);spawn[k]=f32(b+92+k*4);}float yaw=f32(b+104);free(b);
 CohWalkWorld w={0};CohWalkState s;
 int ok=coh_walk_world_init(&w,tri,count,lo,hi);free(tri);if(!ok)return 2;
 if(!coh_walk_init(&s,&w,spawn,yaw)){coh_walk_world_destroy(&w);return 2;}
 for(unsigned i=0;i<25;i++)if(!coh_walk_step(&s,&w,COH_MOTION_BACKWARD,yaw)){coh_walk_world_destroy(&w);return 2;}
 printf("{\"triangles\":%u,\"held_ticks\":25,\"initial_velocity\":",count);vec(s.physics.vel);printf(",\"initial_position\":");vec(s.position);
 printf(",\"surface_flags\":%u,\"surface_normal\":",(unsigned)s.physics.lastSurfFlags);vec(s.physics.surf_normal);printf(",\"release_steps\":[");
 for(unsigned i=1;i<=21;i++){
  if(!coh_walk_step(&s,&w,0,yaw)){coh_walk_world_destroy(&w);return 2;}
  if(i>1)printf(",");printf("{\"tick\":%u,\"velocity\":",i);vec(s.physics.vel);printf(",\"position\":");vec(s.position);
  printf(",\"control_input\":");vec(s.controls.world_input);printf(",\"source_state_bits\":%u,\"grounded\":%s,\"bounded_steps\":%u}",s.controls.source_state_bits,s.grounded?"true":"false",s.bounded_steps);
 }
 printf("]}\n");coh_walk_world_destroy(&w);return 0;
}
'''

def run(command):
    p=subprocess.run(list(map(str,command)),text=True,capture_output=True,timeout=90)
    if p.returncode:raise RuntimeError(' '.join(map(str,command))+'\n'+p.stdout+p.stderr)
    return p.stdout

def identity(path):
    b=path.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}

def original_file(root,item,override=None):
    p=item['path'];choices=([override]if override else[])+[root/p,root/p.replace('upstream/ouroboros/',''),root/Path(p).name]
    selected=next((x for x in choices if x.is_file()),choices[0])
    return oracle.load(selected,item['sha256_lf'])

def bits(v):return struct.pack('<f',v)
def f32(v):return struct.unpack('<f',bits(v))[0]
def distance(a,b):return sum((x-y)**2 for x,y in zip(a,b))**.5

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-root',type=Path,default=ROOT)
    ap.add_argument('--world-source',type=Path)
    ap.add_argument('--grid-header',type=Path)
    ap.add_argument('--fixture',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    pins=json.loads((ORACLE_PATH.parent/'oracle-source-pins.json').read_text());texts={}
    for item in pins['files']:
        name=Path(item['path']).name;override=args.world_source if name=='entworldcoll.c' else args.grid_header if name=='gridcoll.h' else None
        texts[name]=original_file(args.source_root,item,override)
    motion_pins=json.loads((ROOT/'native-android/tools/motion_fixture/source-pins.json').read_text())
    motion_pin=next(p for p in motion_pins['files']if p['path'].endswith('/entity/motion.c'))
    motion=original_file(args.source_root,motion_pin)
    truncate,first,last=oracle.function(motion,'static void truncateVelocity(')
    original,provenance=oracle.program(texts['entworldcoll.c'],texts['mathutil.c'],texts['mathutil.h'],texts['gridcoll.h'])
    original+='\n'+truncate+r'''
void oracle_release_velocity(unsigned flags,const float input[3],const float old[3],const float normal[3],float out[3]){
 oracle_velocity(1.f,flags,2u,input,old,normal,out);MotionState m={0};copyVec3(out,m.vel);truncateVelocity(&m);copyVec3(m.vel,out);
}
'''
    source_names=['coh_walk.c','source_world.c','source_ctri.c','source_tritri.c']
    native_sources=[ROOT/'native-android/walk'/x for x in source_names]+[ROOT/'native-android/motion/coh_motion.c']
    cc=[os.environ.get('CC','cc'),'-std=c11','-O1','-fno-fast-math','-ffp-contract=off','-fno-strict-aliasing']
    with tempfile.TemporaryDirectory(prefix='coh-release-diagnostic-')as directory:
        tmp=Path(directory);source=tmp/'original.c';source.write_text(original);original_lib=tmp/'original.so'
        run(cc+['-Wno-incompatible-pointer-types','-shared','-fPIC',source,'-lm','-o',original_lib])
        driver=tmp/'native.c';driver.write_text(NATIVE_DRIVER);exe=tmp/'native'
        run(cc+['-I',ROOT,driver,*native_sources,'-lm','-o',exe])
        trace=json.loads(run([exe,args.fixture]))
        # Nine significant decimal digits round-trip each native IEEE binary32.
        for key in ['initial_velocity','initial_position','surface_normal']:trace[key]=list(map(f32,trace[key]))
        for row in trace['release_steps']:
            for key in ['velocity','position','control_input']:row[key]=list(map(f32,row[key]))
        lib=C.CDLL(str(original_lib))
        lib.oracle_release_velocity.argtypes=[C.c_uint,*[C.POINTER(C.c_float)]*4]
        lib.oracle_surface.argtypes=[C.c_uint,C.c_uint,C.POINTER(C.c_float),C.POINTER(C.c_float)]
        normal=(C.c_float*3)(*trace['surface_normal']);surface=(C.c_float*5)();lib.oracle_surface(trace['surface_flags'],2,normal,surface)
        expected=trace['initial_velocity'];expected_position=trace['initial_position'];max_error=0.;comparison=[]
        for row in trace['release_steps']:
            out=(C.c_float*3)();lib.oracle_release_velocity(trace['surface_flags'],(C.c_float*3)(0,0,0),(C.c_float*3)(*expected),normal,out)
            expected=list(out);expected_position=[f32(x+y)for x,y in zip(expected_position,expected)]
            error=max(abs(x-y)for x,y in zip(row['velocity'],expected));max_error=max(max_error,error)
            exact=all(bits(x)==bits(y)for x,y in zip(row['velocity'],expected))
            exact_position=all(bits(x)==bits(y)for x,y in zip(row['position'],expected_position))
            if not exact or not exact_position or not row['grounded']or row['bounded_steps']or row['source_state_bits']or any(row['control_input']):
                raise AssertionError(('release source comparison failed',row,expected,expected_position))
            comparison.append({**row,'original_velocity':expected[:],'original_position':expected_position[:],
                               'velocity_bit_exact':exact,'position_bit_exact':exact_position})
    zero_tick=next(r['tick']for r in comparison if all(x==0 for x in r['velocity']))
    after10=next(r for r in comparison if r['tick']==10);settled=comparison[-1]
    receipt={'schema':'coh-native-walk-release-settling-local-diagnostic-v1','passed':True,
        'diagnostic_local_only':True,'runtime_changed':False,'apk_rebuilt':False,
        'android_execution_claimed':False,'physical_ayn_thor_claimed':False,
        'runtime_source_commit':'8629d6a7c4863f492ee50bc030c21c2b2d2f0c3d',
        'trigger':'Android driver used Ready/control-release as a stationary position baseline; residual original WALK friction can exceed unchanged 0.001 stability tolerance.',
        'fixture':{'filename':args.fixture.name,**identity(args.fixture)},
        'profile':{'physics_hz':30,'source_timestep':1,'neutral_surface_modifiers':True,
                   'source_surface_fields':dict(zip(['traction','friction','bounce','gravity','max_speed'],surface)),
                   'source_surface_flags':trace['surface_flags'],'normal':trace['surface_normal'],
                   'initial_backward_held_ticks':25,'initial_velocity':trace['initial_velocity'],'initial_position':trace['initial_position'],
                   'release_input':[0,0,0],'focus_clear_called':False},
        'original_source_pins':pins,'original_truncate_source':{**motion_pin,'signature':'static void truncateVelocity(',
                  'first_line':first,'last_line':last,'sha256_lf':hashlib.sha256(truncate.encode()).hexdigest()},
        'original_program_sha256':hashlib.sha256(original.encode()).hexdigest(),
        'reproducer_sha256':identity(SCRIPT)['sha256'],
        'original_functions':provenance,'runtime_sources':{p.name:identity(p)for p in native_sources},
        'compared_release_steps':len(comparison),'all_velocities_bit_exact':True,'all_positions_bit_exact':True,
        'native_vector_serialization':'Native IEEE binary32 values printed with 9 significant decimal digits and round-tripped to binary32 before comparison.',
        'max_velocity_absolute_error':max_error,'zero_velocity_release_tick':zero_tick,
        'tick10_to_settled_displacement':distance(after10['position'],settled['position']),
        'zero_velocity_stable_at_tick21':comparison[19]['position']==comparison[20]['position'],
        'recommended_driver_change':'Allow a source-friction settling interval before capturing the stationary baseline; then preserve the separate 30-tick stability check and 0.001 tolerance. Do not freeze or retune runtime velocity.',
        'scope':'Independent unchanged original entWorldCollide, original surface/math functions and original truncateVelocity, compared with actual bounded native WALK on the pinned authored floor fixture. Oracle world/entity callbacks stubbed; this does not establish complete tracker/grid/full-client equivalence.',
        'reproduction':{'command':'python3 native-android/evidence/phases19-21/diagnostics/release_check.py --source-root . --fixture /path/to/walkable.bin --output /path/to/host-walk-release-settling-proof.json',
                        'inputs':'Full pinned upstream source checkout, unchanged native runtime sources, and the fixture identified by SHA256 above; CC defaults to cc.'},
        'release_steps':comparison}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:receipt[k]for k in ['passed','compared_release_steps','all_velocities_bit_exact','all_positions_bit_exact','zero_velocity_release_tick','tick10_to_settled_displacement']}))
if __name__=='__main__':main()
