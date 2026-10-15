#!/usr/bin/env python3
"""Exercise the real support JSON exporter with maximum-width diagnostics."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,tempfile
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,default=Path('.'));p.add_argument('--listener-root',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.source_root.resolve();other=(a.listener_root or root).resolve()
config=json.loads((root/'native-android/support-client/build-sources.json').read_text())
headers={h for d in config['include_dirs'] if '{' not in d for h in (root/d).glob('*.h')}
headers.update((root/'native-android/engine').rglob('*.h'))
files=[h for h in headers if h.is_file()]+[root/'native-android/support-client/src/support_bridge.c',root/'native-android/engine/perf/coh_perf.c',root/'native-android/engine/perf/coh_perf_bridge.c']
compiler=shutil.which('clang') or shutil.which('gcc');assert compiler
with tempfile.TemporaryDirectory(prefix='coh-support-snapshot-') as temp_name:
 temp=Path(temp_name);identities=[]
 for source in files:
  name=str(source.relative_to(root));raw=source.read_bytes();dest=temp/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
  identities.append({'file':name,'sha256':hashlib.sha256(raw).hexdigest()})
 # Explicit contract overlay before coordinator integrates the audio worker.
 name='native-android/engine/audio/coh_audio_listener.h';raw=(other/name).read_bytes();dest=temp/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 (temp/'android').mkdir();(temp/'android/asset_manager.h').write_text('typedef struct AAssetManager AAssetManager;')
 binary=temp/'snapshot';source=Path(__file__).with_name('tests')/'support_snapshot_bound.c'
 include_dirs=[temp/entry for entry in config['include_dirs'] if '{' not in entry and (temp/entry).is_dir()]
 cmd=[compiler,'-std=c11','-O1','-g','-ffunction-sections','-fdata-sections','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(temp)]
 for d in include_dirs:cmd+=['-I',str(d)]
 cmd += [str(source),str(temp/'native-android/engine/perf/coh_perf.c'),str(temp/'native-android/engine/perf/coh_perf_bridge.c'),'-Wl,--gc-sections','-pthread','-lm','-o',str(binary)]
 result=subprocess.run(cmd,capture_output=True,text=True);assert result.returncode==0,result.stdout+result.stderr
 env=dict(os.environ);env['ASAN_OPTIONS']='detect_leaks=0:abort_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1'
 run=subprocess.run([str(binary)],capture_output=True,text=True,env=env,timeout=10);assert run.returncode==0,run.stdout+run.stderr
 data=json.loads(run.stdout);assert data['observations']['counters']['draw_calls']['owner_total']==2**64-1
 report={'schema':'coh-support-snapshot-max-width-v1','passed':True,'exporter_source_sha256':hashlib.sha256((temp/'native-android/support-client/src/support_bridge.c').read_bytes()).hexdigest(),'sources':identities,'json_bytes':len(run.stdout.rstrip('\n').encode()),'jni_buffer_bytes':16384,'asan_passed':True,'ubsan_passed':True,'maximum_width_integer_fields':True,'finite_maximum_width_listener_floats':True,'scope':'Actual native support snapshot/performance exporters with mocked subsystem snapshots; no Android/emulator/device execution.'}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['passed','json_bytes','jni_buffer_bytes','asan_passed','ubsan_passed']}))
