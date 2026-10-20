#!/usr/bin/env python3
"""Focused source-pose retention and decoded-coordinate debug-box draw test."""
import argparse,ctypes as C,hashlib,importlib.util,json,os,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];ENGINE=HERE.parent;POSE=ENGINE/'initial-capture'
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.source_root.resolve();work=a.work.resolve()
if work.exists() or work==ROOT or work.is_relative_to(ROOT):p.error('Fresh external work directory required')
work.mkdir(parents=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(command,**kw):
 r=subprocess.run(list(map(str,command)),capture_output=True,text=True,timeout=180,**kw)
 if r.returncode:raise RuntimeError(r.stdout[-2500:]+r.stderr[-4000:])
 return r.stdout
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
producer=module('debug_entity_source_producer',POSE/'check_initial_pose_probe.py');entities=root/'native-android/engine/entities';helper=module('debug_entity_original_entities',entities/'check.py')
helper.oracle(root,work);source=work/'source-pose.c';source.write_text((work/'source-oracle.c').read_text()+producer.WRAPPER)
original=work/'source-pose.so';run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),'-I'+str(entities),source,'-lm','-o',original]);lib=C.CDLL(str(original));lib.pose_original.argtypes=[C.c_uint]*4+[C.c_void_p]*3;wire,fixtures=producer.fixtures(lib,work)
sources=[HERE/'coh_debug_entity.c',HERE/'coh_renderer.c',POSE/'coh_initial_pose_probe.c',ENGINE/'replication/coh_replication.c',ENGINE/'entities/coh_entities.c',HERE/'tests/test_debug_entity.c'];deps=set(sources+[Path(__file__).resolve(),POSE/'check_initial_pose_probe.py']);pending=list(sources)
while pending:
 path=pending.pop().resolve()
 for name in re.findall(rb'^\s*#\s*include\s*"([^"\n]+)"',path.read_bytes(),re.M):
  child=(path.parent/name.decode()).resolve()
  if child not in deps:deps.add(child);pending.append(child)
frozen={path:sha(path) for path in deps};original_pins={root/'upstream/ouroboros'/name:sha(root/'upstream/ouroboros'/name) for name in helper.FILES}
modes={};semantic=None
for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
 binary=work/mode;run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off',*flags,*sources,'-Wl,--wrap=malloc,--wrap=calloc','-lm','-o',binary]);stdout=run([binary,wire],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'));(work/(mode+'.stdout')).write_text(stdout);checks=json.loads(stdout)
 if semantic is None:semantic=checks
 else:assert semantic==checks
 modes[mode]={'checks':checks,'binary_sha256':sha(binary)};print(json.dumps({'mode':mode,**checks}),flush=True)
assert frozen=={path:sha(path) for path in frozen} and original_pins=={path:sha(path) for path in original_pins}
receipt={'passed':True,'scope':'Same original-produced full absolute pose retained for explicit diagnostic box, then submitted/flushed through existing renderer against a recording backend; no full costume/actor/ACK or fake spawn','modes':modes,'fixtures':fixtures,'source_sha256':{str(path):pin for path,pin in frozen.items()},'original_source_sha256':{str(path):pin for path,pin in original_pins.items()},'generated_original_sha256':sha(source),'source_packet_is_synthetic':True,'box_static_vertex_bytes':8*56,'box_static_index_bytes':36*4,'new_heap_bytes':0,'diagnostic_white_RGBA_bytes':4,'device_execution':False,'actual_server_transaction':False,'leak_sanitizer':False}
a.output.parent.mkdir(parents=True,exist_ok=True)
with a.output.open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
