#!/usr/bin/env python3
"""Build unchanged pinned scalar/input source kernels and compare native input.

The Windows/UI glue is stubbed. This is not execution of the original game.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent

def function(text, signature):
    start = text.index(signature)
    brace = text.index('{', start)
    depth = 1
    cursor = brace + 1
    while depth:
        depth += (text[cursor] == '{') - (text[cursor] == '}')
        cursor += 1
    return text[start:cursor]

def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]

def scalar(value):
    # Hex floats encode exact recovered binary32 values in the runtime fixture.
    return float(value).hex() + 'f'

def run(command):
    return subprocess.run(command, check=True, capture_output=True, text=True, timeout=90).stdout

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-root', type=Path, default=ROOT)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--write-goldens', action='store_true')
    ap.add_argument('--sanitize', action='store_true')
    args = ap.parse_args()
    pins = json.loads((HERE / 'source-pins.json').read_text())
    sources = {}
    for item in pins['files']:
        path = args.source_root / item['path']
        if not path.is_file():
            path = args.source_root / Path(item['path']).name
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == item['sha256'], f'source SHA mismatch: {path}'
        assert hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest() == item['git_blob'], f'Git blob mismatch: {path}'
        sources[Path(item['path']).name] = data.decode()
    math_source, input_source, camera_source = sources['mathutil.c'], sources['input.c'], sources['camera.c']
    rng = random.Random(102024)
    cases = [(0, 0, 0, 0, 1, 0), (0, 3.13, 20, 0, 1, 0), (0, -3.13, -20, 0, 1, 0),
             (1.56, 0, 0, 50, 1, 0), (-1.56, 0, 0, -50, 1, 0),
             (1, .4, 50, 50, 1, 1), (1, .4, -50, -50, 1, 1),
             (1, 0, 50, 0, 0, 0), (-1, 0, -50, 0, 0, 0),
             (0, 0, 500, 500, 1, 0), (0, 0, -500, -500, 1, 0),
             (0, f32(math.pi), 1, 0, 1, 0), (0, f32(-math.pi), -1, 0, 1, 0)]
    cases += [(rng.uniform(-1.5, 1.5), rng.uniform(-3.14, 3.14), rng.randint(-500, 500), rng.randint(-500, 500), rng.randrange(2), rng.randrange(2)) for _ in range(83)]
    cases = [(f32(p), f32(y), dx, dy, ml, inv) for p, y, dx, dy, ml, inv in cases]
    stubs = '''#include <stdio.h>
#include <stdint.h>
#include <string.h>
typedef float F32; typedef float Vec3[3];
#define PI 3.14159265358979323846
#define RAD(a) (((a)*PI)*(1.0f/180.0f))
#define copyVec3(a,b) memcpy((b),(a),sizeof(Vec3))
typedef struct { struct {Vec3 cur;} pyr; int mlook,editor_mouse_invert; } ControlState;
struct {float mat[4][3];Vec3 targetPYR;} cam_info;
int mouse_dx,mouse_dy;
static void camSetPyr(Vec3 pyr) {copyVec3(pyr,cam_info.targetPYR);}
static void createMat3RYP(float mat[4][3],Vec3 pyr) {(void)mat;(void)pyr;}
char inp_levels[256],inp_edges[256];int just_lost_focus_debug,g_isBindingKey;
#define INP_MOUSEWHEEL 250
#define INP_MOUSE_BUTTONS 240
#define MENU_GAME 0
static int okToInput(int key) {(void)key;return 0;}
static int isMenu(int menu) {(void)menu;return 0;}
static int isGameReturnKeybind(int key) {(void)key;return 0;}
static void cmdParse(const char *cmd) {(void)cmd;}
static void bindKeyExecEx(int key,int state,int time,int x,int y) {(void)key;(void)state;(void)time;(void)x;(void)y;}
'''
    kernels = '\n'.join(function(math_source, sig) for sig in ['F32 fixAngle(', 'F32 subAngle(', 'F32 addAngle('])
    kernels += '\n' + function(camera_source, 'static void look(')
    kernels += '\n' + function(input_source, 'void inpUpdateKeyEx(')
    axis_statements = input_source[input_source.index('// XY axis (Joystick 1)'):input_source.index('// Xrot/Yrot axis (Joystick 3?)')]
    axis_wrapper = '''
static void inpUpdateKey(int key,int down,int time) {inpUpdateKeyEx(key,down,time,0,0);}
static void inpUpdateKeyClearIfActive(int key,int time) {if(inp_levels[key])inpUpdateKey(key,0,time);}
#define INP_JOYSTICK1_LEFT 0
#define INP_JOYSTICK1_RIGHT 1
#define INP_JOYSTICK1_UP 2
#define INP_JOYSTICK1_DOWN 3
#define INP_JOYSTICK2_LEFT 4
#define INP_JOYSTICK2_RIGHT 5
#define INP_JOYSTICK2_UP 6
#define INP_JOYSTICK2_DOWN 7
static void source_axes(int x,int y,int z,int rz) {
 struct {int lX,lY,lZ,lRz;} js={x,y,z,rz};int joystick_sensitivity=500,curTime=0;
''' + axis_statements + '\n}\n'
    native_source = ROOT / 'native-android/input/coh_input.c'
    header = ROOT / 'native-android/input/input_goldens.h'
    case_initializers = ',\n'.join('{'+','.join([scalar(p), scalar(y), str(dx), str(dy), str(ml), str(inv)])+'}' for p,y,dx,dy,ml,inv in cases)
    source_main = '''
typedef struct {float pitch,yaw;int dx,dy,mlook,invert;} Case;
static const Case cases[] = {CASE_INITIALIZERS};
int main(void) {
 unsigned i,j;ControlState cs;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++) {
  memset(&cs,0,sizeof(cs));memset(&cam_info,0,sizeof(cam_info));
  cs.pyr.cur[0]=cases[i].pitch;cs.pyr.cur[1]=cases[i].yaw;cs.mlook=cases[i].mlook;cs.editor_mouse_invert=cases[i].invert;
  mouse_dx=cases[i].dx;mouse_dy=cases[i].dy;look(&cs);
  for(j=0;j<3;j++)printf("%a ",(double)cs.pyr.cur[j]);
  for(j=0;j<3;j++)printf("%a%s",(double)cam_info.targetPYR[j],j==2?"\\n":" ");
 }
 return 0;
}
'''.replace('CASE_INITIALIZERS', case_initializers)
    cc = os.environ.get('CC', 'cc')
    with tempfile.TemporaryDirectory(prefix='coh-input-source-') as temporary:
        temp = Path(temporary)
        original = temp/'original.c'; original.write_text(stubs+kernels+source_main)
        flags = ['-std=c11', '-O1', '-fno-fast-math', '-ffp-contract=off', '-Wall', '-Wextra', '-Werror']
        run([cc, *flags, str(original), '-lm', '-o', str(temp/'original')])
        lines = run([str(temp/'original')]).splitlines()
        assert len(lines) == len(cases)
        goldens = [[float.fromhex(x) for x in line.split()] for line in lines]
        generated = ['/* Generated by tools/input_fixture/check.py from unchanged pinned source kernels. */',
                     '#ifndef COH_INPUT_GOLDENS_H', '#define COH_INPUT_GOLDENS_H',
                     'typedef struct {float pitch,yaw;int dx,dy,mlook,invert;float pyr[3],target[3];} CohInputGolden;',
                     f'#define COH_INPUT_GOLDEN_COUNT {len(cases)}u', 'static const CohInputGolden coh_input_goldens[] = {']
        for case, values in zip(cases, goldens):
            p,y,dx,dy,ml,inv = case
            generated.append('{'+','.join([scalar(p),scalar(y),str(dx),str(dy),str(ml),str(inv)])+', {'+','.join(scalar(x) for x in values[:3])+'}, {'+','.join(scalar(x) for x in values[3:])+'}},')
        generated += ['};', '#endif', '']
        generated = '\n'.join(generated)
        if args.write_goldens: header.write_text(generated)
        else: assert header.read_text() == generated, 'runtime goldens differ from rebuilt original source oracle'
        # Original key state algorithm is compared over deterministic event traces.
        trace = temp/'trace.c'
        trace.write_text(stubs+kernels+axis_wrapper+'''
#include "coh_input.h"
int main(void) {
 CohInputState s;CohInputFrame frame;unsigned i,k,j;int axis,value,axis_checks=0;
 ControlState dummy;memset(&dummy,0,sizeof(dummy));look(&dummy);coh_input_init(&s);
 for(i=0;i<2048;i++) {
  k=8+(i*17u)%16;int down=(i%19)!=0;
  inpUpdateKeyEx((int)k,down,0,0,0);
  if(!coh_input_key(&s,k,down))return 1;
  if(s.levels[k]!=(unsigned char)inp_levels[k]||s.edges[k]!=(unsigned char)inp_edges[k])return 2;
  if(i%31==0) {memset(inp_edges,0,sizeof(inp_edges));memset(s.edges,0,sizeof(s.edges));}
 }
 for(axis=0;axis<4;axis++)for(value=-1000;value<=1000;value++) {
  int original[4]={0,0,0,0};float normalized[4]={0,0,0,0};
  original[axis]=value;normalized[axis]=(float)value/1000.0f;
  memset(inp_levels,0,sizeof(inp_levels));memset(inp_edges,0,sizeof(inp_edges));
  source_axes(original[0],original[1],original[2],original[3]);coh_input_init(&s);
  if(!coh_input_axes(&s,normalized[0],normalized[1],normalized[2],normalized[3])||!coh_input_frame(&s,0,&frame))return 3;
  for(j=0;j<8;j++)if(frame.levels[j]!=(unsigned char)inp_levels[j]||!!(frame.pressed&(1u<<j))!=!!inp_edges[j])return 4;
  axis_checks++;
 }
 printf("2048 %d\\n",axis_checks);return 0;
}
''')
        extra = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer'] if args.sanitize else []
        include = ['-I', str(native_source.parent)]
        run([cc, *flags, *extra, *include, str(trace), str(native_source), '-lm', '-o', str(temp/'trace')])
        # The extracted editor look is unused in the key trace, but compile checks it.
        # GCC -Wunused-function makes unchanged static look unused: call it once safely.
        # This is handled by the wrapper below if the compiler enforces that warning.
        key_checks, axis_checks = map(int,run([str(temp/'trace')]).split())
        proof_main = temp/'proof.c'
        proof_main.write_text('''#include <stdio.h>
#include "coh_input.h"
int main(void) {CohInputProof p;int ok=coh_input_selftest(&p);printf("%u %u %u %u %.9g\\n",p.checks,p.failed,p.source_cases,p.adapter_cases,(double)p.max_source_error);return ok?0:1;}
''')
        run([cc,*flags,*extra,*include,str(proof_main),str(native_source),'-lm','-o',str(temp/'proof')])
        checks,failed,source_cases,adapter_cases,error=run([str(temp/'proof')]).split()
    report = {'schema':'coh-native-input-host-proof-v1','passed':True,
              'source_files':pins['files'],'unchanged_functions':['fixAngle','subAngle','addAngle','look','inpUpdateKeyEx'],
              'source_camera_cases':int(source_cases),'source_key_events':key_checks,
              'source_joystick_integer_cases':axis_checks,
              'unchanged_statement_slices':['inpJoystickState XY and Z/Rz axis comparisons and key updates'],
              'native_checks':int(checks),'adapter_cases':int(adapter_cases),'failed':int(failed),'max_source_error':float(error),
              'sanitizers':'AddressSanitizer and UndefinedBehaviorSanitizer' if args.sanitize else None,
              'sanitizer_options':os.environ.get('ASAN_OPTIONS') if args.sanitize else None,
              'scope':'Unchanged scalar/editor-look/key-level kernels under bounded inputs; platform/UI calls stubbed; not original game execution or gameplay camera/physics',
              'compiled_runtime_goldens_sha256':hashlib.sha256(header.read_bytes()).hexdigest()}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['passed','source_camera_cases','source_key_events','native_checks','failed','max_source_error']}))

if __name__ == '__main__': main()
