#!/usr/bin/env python3
"""Compare the integration adapter with unchanged source look/angle/camera bodies.

This host proof does not execute a GPU or establish Android input transport.
The camera +/-12-degree clamp and radix conversion are explicit adapter policy;
the source scalar look, subAngle and camera construction bodies execute unchanged.
"""
import argparse
import ctypes as C
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import shlex
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
NATIVE = ROOT / 'native-android'

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

original_world = module('interactive_original_world', NATIVE/'tools/world_fixture/original_world_check.py')
world_types = module('interactive_world_types', NATIVE/'tools/world_fixture/_types.py')
input_oracle = module('interactive_input_oracle', NATIVE/'tools/input_fixture/check.py')

class Frame(C.Structure):
    _fields_ = [('held',C.c_uint32),('pressed',C.c_uint32),('released',C.c_uint32),('frames',C.c_uint32),
        ('clear_count',C.c_uint32),('rejected',C.c_uint32),('clipped',C.c_uint32),('levels',C.c_uint8*24),
        ('delta_x',C.c_int32),('delta_y',C.c_int32),('pyr',C.c_float*3),('target_pyr',C.c_float*3),('axes',C.c_float*4)]
class Adapter(C.Structure):
    _fields_ = [('initialized',C.c_int),('previous_pyr',C.c_float*3),('offset_degrees',C.c_float*2)]

def f32(value): return C.c_float(value).value
def require(value, message):
    if not value: raise ValueError(message)

def source_code():
    world_code, pins = original_world.source_code()
    manifest = json.loads((NATIVE/'tools/input_fixture/source-pins.json').read_text())
    sources = {}
    for pin in manifest['files']:
        data = (ROOT/pin['path']).read_bytes()
        require(hashlib.sha256(data).hexdigest() == pin['sha256'], 'Input source identity differs')
        sources[Path(pin['path']).name] = data.decode()
    kernels = '\n'.join(input_oracle.function(sources['mathutil.c'], signature)
        for signature in ('F32 fixAngle(', 'F32 subAngle(', 'F32 addAngle('))
    look = input_oracle.function(sources['camera.c'], 'static void look(')
    stubs = r'''
typedef struct {struct {Vec3 cur;} pyr;int mlook,editor_mouse_invert;} ControlState;
static struct {float mat[4][3];Vec3 targetPYR;} cam_info;
static int mouse_dx,mouse_dy;
static void camSetPyr(Vec3 pyr){copyVec3(pyr,cam_info.targetPYR);}
static void createMat3RYP(float mat[4][3],Vec3 pyr){(void)mat;(void)pyr;}
'''
    wrappers = r'''
void original_editor_step(const float current[3],int dx,int dy,float out[3],float target[3]){
 ControlState state={0};copyVec3(current,state.pyr.cur);state.mlook=1;
 memset(&cam_info,0,sizeof cam_info);mouse_dx=dx;mouse_dy=dy;look(&state);
 copyVec3(state.pyr.cur,out);copyVec3(cam_info.targetPYR,target);
}
float original_difference(float current,float previous){return subAngle(current,previous);}
'''
    # These two diagnostics arise from unchanged legacy source: an unused
    # parser callback and the original flat Mat4 initializer. New runtime code
    # still compiles with the complete -Wall/-Wextra/-Werror policy.
    original_diagnostics = '#pragma GCC diagnostic ignored "-Wunused-parameter"\n#pragma GCC diagnostic ignored "-Wmissing-braces"\n'
    return original_diagnostics + world_code + '\n' + stubs + kernels + look + wrappers, {'world':pins,'input':manifest}

def compile_library(path, source, compiler, mutate=None):
    flags = ['-std=c11','-O1','-ffp-contract=off','-fno-fast-math','-Wall','-Wextra','-Werror','-shared','-fPIC',
        '-I',str(NATIVE/'interactive-world'),'-I',str(NATIVE/'input'),'-I',str(NATIVE/'world')]
    camera = NATIVE/'interactive-world/coh_interactive_camera.c'
    if mutate:
        text = camera.read_text()
        before, after = mutate
        require(text.count(before) == 1, 'Negative-control mutation seam changed')
        camera = path.parent/'mutated-camera.c'; camera.write_text(text.replace(before,after))
    subprocess.run([*shlex.split(compiler),*flags,str(source),str(camera),str(NATIVE/'world/coh_world.c'),'-lm','-o',str(path)],check=True)
    lib = world_types.configure(C.CDLL(str(path)))
    pointer = C.POINTER(C.c_float)
    lib.coh_interactive_camera_apply.argtypes = [C.POINTER(Adapter),C.POINTER(Frame),C.POINTER(world_types.Inputs),C.POINTER(world_types.Inputs),pointer,pointer]
    lib.coh_interactive_camera_apply.restype = C.c_int
    lib.original_editor_step.argtypes = [pointer,C.c_int,C.c_int,pointer,pointer]
    lib.original_difference.argtypes = [C.c_float,C.c_float]; lib.original_difference.restype = C.c_float
    lib.original_camera.argtypes = [pointer,C.c_uint,C.c_uint,pointer,pointer]
    return lib

def baseline_inputs(raw):
    require(raw[:8] == b'COHWOR09', 'Authentic world bytes required')
    offset, length = struct.unpack_from('<2I',raw,48)
    require(length == 520 and offset <= len(raw)-520, 'Authentic input block span differs')
    return raw[offset:offset+520]

def qualify(lib, raw):
    block = baseline_inputs(raw)
    mem = (C.c_uint8*len(block)).from_buffer_copy(block)
    baseline = world_types.Inputs()
    require(lib.coh_world_parse_inputs(mem,len(block),C.byref(baseline)) == 0, 'Source input block rejected')
    adapter = Adapter(); frame = Frame(); out = world_types.Inputs(); pitch = C.c_float(); yaw = C.c_float()
    require(lib.coh_interactive_camera_apply(C.byref(adapter),C.byref(frame),C.byref(baseline),C.byref(out),C.byref(pitch),C.byref(yaw)) == 1, 'Initial camera rejected')
    require(bytes(out) == bytes(baseline) and pitch.value == yaw.value == 0, 'Initial camera differs from authentic view')
    source_pyr = (C.c_float*3)(); previous = [0.,0.,0.]; expected_offsets = [0.,0.]
    randomizer = random.Random(0x131415)
    traces = [(50,0),(-50,0),(0,50),(0,-50),(500,0),(-5,0),(0,-500),(0,5),(0,0),(0,0)]
    traces += [(randomizer.randint(-500,500),randomizer.randint(-500,500)) for _ in range(4096)]
    direction_mask = 0; components = 0; maximum = 0.; settled = 0
    for dx,dy in traces:
        target = (C.c_float*3)(); next_pyr = (C.c_float*3)()
        lib.original_editor_step(source_pyr,dx,dy,next_pyr,target)
        source_pyr = next_pyr
        frame.pyr[:] = source_pyr; frame.delta_x = dx; frame.delta_y = dy; frame.frames += 1
        old = list(expected_offsets)
        expected_offsets[0] = f32(max(-12.,min(12.,f32(expected_offsets[0]+f32(-lib.original_difference(source_pyr[0],previous[0])*(180./math.pi))))))
        expected_offsets[1] = f32(max(-12.,min(12.,f32(expected_offsets[1]+f32(lib.original_difference(source_pyr[1],previous[1])*(180./math.pi))))))
        require(lib.coh_interactive_camera_apply(C.byref(adapter),C.byref(frame),C.byref(baseline),C.byref(out),C.byref(pitch),C.byref(yaw)) == 1, 'Current source camera rejected')
        require(list(adapter.offset_degrees) == expected_offsets, 'Original source angular increment/pitch convention differs')
        require(pitch.value == f32(expected_offsets[0]-old[0]) and yaw.value == f32(expected_offsets[1]-old[1]), 'Signed actual-camera increment differs')
        if yaw.value>0: direction_mask |= 1
        if yaw.value<0: direction_mask |= 2
        if pitch.value>0: direction_mask |= 4
        if pitch.value<0: direction_mask |= 8
        if not dx and not dy:
            require(list(expected_offsets)==old and pitch.value==yaw.value==0, 'Released source camera moved'); settled += 1
        expected_angles = [f32(baseline.cameras[0].pyr_degrees[0]+expected_offsets[0]),f32(baseline.cameras[0].pyr_degrees[1]+expected_offsets[1]),baseline.cameras[0].pyr_degrees[2]]
        require(list(out.cameras[0].pyr_degrees)==expected_angles, 'Actual source camera angles differ')
        params = (C.c_float*10)(*baseline.cameras[0].position,*expected_angles,baseline.cameras[0].fovy,baseline.cameras[0].aspect,baseline.cameras[0].znear,baseline.cameras[0].zfar)
        expected_view=(C.c_float*12)(); expected_projection=(C.c_float*16)();actual_view=(C.c_float*12)();actual_projection=(C.c_float*16)()
        lib.original_camera(params,baseline.cameras[0].flip_x,baseline.cameras[0].flip_y,expected_view,expected_projection)
        require(lib.coh_world_camera(C.byref(out),0,0,actual_view,actual_projection)==0,'Native camera construction failed')
        for actual, expected in zip([*actual_view,*actual_projection],[*expected_view,*expected_projection]):
            components += 1; error = abs(actual-expected); maximum=max(maximum,error)
            require(error == 0., 'Native current camera differs from unchanged original camera construction')
        previous = list(source_pyr)
    require(direction_mask == 15 and settled >= 2, 'Source trace lacks signed directions or settled-release observations')
    # Transactional invalid-frame/state/baseline witnesses.
    malformed=0
    mutations=[]
    for value in (float('nan'),float('inf'),-float('inf'),4.,-4.):
        for axis in range(3): mutations.append(('frame',axis,value))
    mutations += [('previous',0,float('nan')),('previous',1,4.),('offset',0,float('nan')),('offset',1,13.),('baseline',0,0.)]
    for where,axis,value in mutations:
        bad_frame=Frame.from_buffer_copy(bytes(frame)); bad_state=Adapter.from_buffer_copy(bytes(adapter)); bad_baseline=world_types.Inputs.from_buffer_copy(bytes(baseline))
        if where=='frame':bad_frame.pyr[axis]=value
        elif where=='previous':bad_state.previous_pyr[axis]=value
        elif where=='offset':bad_state.offset_degrees[axis]=value
        else:bad_baseline.cameras[0].fovy=value
        before_state=bytes(bad_state);C.memset(C.byref(out),0x5a,C.sizeof(out));before_out=bytes(out);pitch.value=23.;yaw.value=42.
        require(lib.coh_interactive_camera_apply(C.byref(bad_state),C.byref(bad_frame),C.byref(bad_baseline),C.byref(out),C.byref(pitch),C.byref(yaw))==0,'Malformed integration camera admitted')
        require(bytes(bad_state)==before_state and bytes(out)==before_out and pitch.value==23. and yaw.value==42.,'Failed camera operation changed outputs')
        malformed+=1
    return {'passed':True,'source_editor_steps':len(traces),'source_camera_components':components,'source_camera_maximum_error':maximum,
        'source_angular_convention':True,'diagnostic_clamp_degrees':12,'direction_mask':direction_mask,'settled_source_steps':settled,
        'malformed_transactional_cases':malformed,'seed':'0x131415','host_only':True,'android_callbacks_executed':False,'gpu_executed':False}

def sanitizer(temp, raw, compiler):
    code = r'''
#include "coh_interactive_world.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
int main(int argc,char **argv) {
 if(argc!=2)return 1;FILE *file=fopen(argv[1],"rb");if(!file)return 2;
 if(fseek(file,0,SEEK_END))return 3;long n=ftell(file);if(n<128||n>16777216)return 4;
 rewind(file);unsigned char *raw=malloc((size_t)n);if(!raw||fread(raw,1,(size_t)n,file)!=(size_t)n)return 5;fclose(file);
 unsigned off=(unsigned)raw[48]|((unsigned)raw[49]<<8)|((unsigned)raw[50]<<16)|((unsigned)raw[51]<<24);
 if(off>(unsigned)n||520>(unsigned)n-off)return 6;
 CohWorldInputs baseline,out;CohInputState input;CohInputFrame frame;
 CohInteractiveCamera adapter={0};float pitch=0,yaw=0;unsigned checks=0,seed=0x131415;
 if(coh_world_parse_inputs(raw+off,520,&baseline))return 7;
 coh_input_init(&input);if(!coh_input_frame(&input,1.f/30.f,&frame)||!coh_interactive_camera_apply(&adapter,&frame,&baseline,&out,&pitch,&yaw))return 8;
 for(unsigned i=0;i<8000;i++){
  seed=seed*1664525u+1013904223u;float x=((int)(seed%2001)-1000)/1000.f;
  seed=seed*1664525u+1013904223u;float y=((int)(seed%2001)-1000)/1000.f;
  if(!coh_input_axes(&input,0,0,x,y)||!coh_input_frame(&input,1.f/30.f,&frame)||!coh_interactive_camera_apply(&adapter,&frame,&baseline,&out,&pitch,&yaw))return 9;
  checks++;
  CohInteractiveCamera bad=adapter,before=bad;CohInputFrame corrupt=frame;corrupt.pyr[i%3]=NAN;
  memset(&out,0x5a,sizeof out);CohWorldInputs prior=out;pitch=23;yaw=42;
  if(coh_interactive_camera_apply(&bad,&corrupt,&baseline,&out,&pitch,&yaw)||memcmp(&bad,&before,sizeof bad)||memcmp(&out,&prior,sizeof out)||pitch!=23||yaw!=42)return 10;
  checks++;
 }
 coh_input_focus(&input,0);if(!coh_input_frame(&input,1.f/30.f,&frame)||!coh_interactive_camera_apply(&adapter,&frame,&baseline,&out,&pitch,&yaw)||pitch||yaw)return 11;
 if(coh_interactive_camera_apply(NULL,&frame,&baseline,&out,&pitch,&yaw)||coh_interactive_camera_apply(&adapter,NULL,&baseline,&out,&pitch,&yaw)||coh_interactive_camera_apply(&adapter,&frame,NULL,&out,&pitch,&yaw)||coh_interactive_camera_apply(&adapter,&frame,&baseline,NULL,&pitch,&yaw)||coh_interactive_camera_apply(&adapter,&frame,&baseline,&out,NULL,&yaw)||coh_interactive_camera_apply(&adapter,&frame,&baseline,&out,&pitch,NULL))return 12;
 free(raw);printf("%u",checks+7);return 0;
}
'''
    source=temp/'sanitize.c';source.write_text(code);fixture=temp/'world.bin';fixture.write_bytes(raw);binary=temp/'sanitize'
    command=[*shlex.split(compiler),'-std=c11','-O1','-g','-ffp-contract=off','-fno-fast-math','-fsanitize=address,undefined','-fno-omit-frame-pointer',
        '-I',str(NATIVE/'interactive-world'),'-I',str(NATIVE/'input'),'-I',str(NATIVE/'world'),str(source),
        str(NATIVE/'interactive-world/coh_interactive_camera.c'),str(NATIVE/'world/coh_world.c'),str(NATIVE/'input/coh_input.c'),'-lm','-o',str(binary)]
    subprocess.run(command,check=True)
    result=subprocess.run([str(binary),str(fixture)],capture_output=True,text=True,timeout=60,
        env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:abort_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'})
    require(result.returncode==0,'Sanitizer integration pipeline failed: '+result.stderr)
    return {'passed':True,'checks':int(result.stdout),'native_input_camera_steps':8000,'nonfinite_transactional_rejections':8000,
        'focus_clear_stationary':True,'null_argument_rejections':6,'address_and_undefined_sanitizers':True,'leak_sanitizer':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--world',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--compiler',default=os.environ.get('CC','cc'))
    parser.add_argument('--sanitize',action='store_true')
    args=parser.parse_args();code,pins=source_code();raw=args.world.read_bytes()
    with tempfile.TemporaryDirectory(prefix='coh-interactive-world-source-') as directory:
        temp=Path(directory);source=temp/'original.c';source.write_text(code)
        proof=qualify(compile_library(temp/'native.so',source,args.compiler),raw)
        controls=[]
        for label,mutation in [('reversed_pitch',('const float pitch_radians = -source_difference','const float pitch_radians = source_difference')),
            ('yaw_disconnected',('const float yaw_radians = source_difference(frame->pyr[1], candidate.previous_pyr[1]);','const float yaw_radians = 0.0f;'))]:
            lib=compile_library(temp/(label+'.so'),source,args.compiler,mutation)
            try:qualify(lib,raw)
            except ValueError as failure:controls.append({'name':label,'rejected':True,'reason':str(failure)})
            else:raise ValueError('Negative control unexpectedly passed: '+label)
        if args.sanitize:proof['sanitizer']=sanitizer(temp,raw,args.compiler)
    proof['negative_controls']=controls;proof['unchanged_source_pins']=pins
    proof['world_sha256']=hashlib.sha256(raw).hexdigest()
    proof['implementation_sha256']={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in (NATIVE/'interactive-world/coh_interactive_camera.c',NATIVE/'world/coh_world.c')}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps({k:proof[k] for k in ('passed','source_editor_steps','source_camera_components','source_camera_maximum_error','malformed_transactional_cases','negative_controls','sanitizer') if k in proof}))
if __name__=='__main__':main()
