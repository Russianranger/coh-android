#!/usr/bin/env python3
"""Fault-inject the real support audio owner with controlled platform dependencies.

This is host ASan/UBSan ownership/lifecycle evidence. It runs no Android stream,
codec, real callback or physical route. Source files are copied before compiling,
so evidence identifies the exact tested bytes even during coordinator integration.
"""
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess, tempfile

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--source-root',type=Path,default=Path('.'))
p.add_argument('--listener-root',type=Path,help='Explicit separate worker root before listener integration')
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();root=a.source_root.resolve();listener=(a.listener_root or root).resolve()
files=['native-android/support-client/src/support_audio.c','native-android/support-client/src/support_audio.h',
       'native-android/engine/audio/coh_mixer.h','native-android/engine/audio/coh_mixer_aaudio.h',
       'native-android/engine/audio/coh_music.h','native-android/engine/audio/coh_resample.h',
       'native-android/engine/audio/coh_audio_listener.h','native-android/engine/coh_contracts.h']
compiler=shutil.which('clang') or shutil.which('gcc');assert compiler,'Host C compiler missing'
identities=[]
with tempfile.TemporaryDirectory(prefix='coh-support-audio-owner-') as directory:
 temp=Path(directory)
 for name in files:
  source=(listener if name.endswith('coh_audio_listener.h') else root)/name
  raw=source.read_bytes();dest=temp/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
  identities.append({'file':name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),
                     'source_root':'listener-root' if name.endswith('coh_audio_listener.h') else 'source-root'})
 android=temp/'android';android.mkdir()
 (android/'asset_manager.h').write_text('''#ifndef TEST_ANDROID_ASSET_MANAGER_H
#define TEST_ANDROID_ASSET_MANAGER_H
#include <stddef.h>
#include <sys/types.h>
typedef struct AAsset AAsset;
typedef struct AAssetManager AAssetManager;
#define AASSET_MODE_RANDOM 1
AAsset *AAssetManager_open(AAssetManager *,const char *,int);
off64_t AAsset_getLength64(AAsset *);
off64_t AAsset_seek64(AAsset *,off64_t,int);
int AAsset_read(AAsset *,void *,size_t);
void AAsset_close(AAsset *);
#endif
''')
 source=Path(__file__).with_name('tests')/'audio_owner_faults.c';binary=temp/'audio-owner-faults'
 cmd=[compiler,'-std=c11','-D_LARGEFILE64_SOURCE','-O1','-g','-Wall','-Wextra','-Werror',
      '-Wno-misleading-indentation','-fsanitize=address,undefined','-fno-omit-frame-pointer',
      '-I',str(temp),str(source),'-pthread','-lm','-o',str(binary)]
 compiled=subprocess.run(cmd,capture_output=True,text=True)
 assert compiled.returncode==0,compiled.stdout+compiled.stderr
 env=dict(os.environ);env['ASAN_OPTIONS']='detect_leaks=0:abort_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
 result=subprocess.run([str(binary)],capture_output=True,text=True,env=env,timeout=30)
 assert result.returncode==0,result.stdout+result.stderr
 data=json.loads(result.stdout)
 report={'schema':'coh-support-audio-owner-faults-v1','passed':True,'sources':identities,
         'compiler':subprocess.run([compiler,'--version'],capture_output=True,text=True).stdout.splitlines()[0],
         'asan_passed':True,'ubsan_passed':True,'leaksanitizer_enabled':False,
         'tracked_dependency_residue':0,'result':data,
         'scope':'Real support audio owner thread/mailbox with controlled fake backend/music/mixer/AAsset; no Android/emulator/callback/decode/physical evidence.',
         'scenarios':['initial paused asset/stream admission','resume running checkpoint boundary','listener pose delivery',
          'route close/reopen','device-error stream recovery','failed route close automatically resumes desired-running state',
          'failed pause close retains owners then automatically retries',
          'failed destroy retains graph then explicit cleanup-worker retry','partial source initialization cleanup']}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(data))
