#!/usr/bin/env python3
"""Real host GLES + ASan/UBSan regression for the integrated offline UI adapter."""
import argparse,ctypes.util,hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,default=Path('.'));p.add_argument('--ndk',type=Path,required=True);p.add_argument('--font-header',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.source_root.resolve();n=root/'native-android';g=n/'engine/ui/gameplay';s=n/'support-client'
files=[s/'src/support_ui.c',g.parent/'coh_ui.c',g.parent/'coh_hud.c',*[g/x for x in ('coh_hud_android.c','coh_hud_atlas.c','coh_hud_quad.c','coh_hud_gles.c','coh_hud_axis_navigation.c','presentation/coh_presentation.c')]]
def run(cmd,**kw):
 r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,**kw)
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 return r.stdout
with tempfile.TemporaryDirectory(prefix='coh-presentation-adapter-') as d:
 t=Path(d);inc=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/include'
 for name in ('GLES3','KHR'):shutil.copytree(inc/name,t/name)
 shutil.copyfile(a.font_header,t/'support_font.h')
 run(['python',g/'tray/prepare.py','--output',t])
 historical=(g/'tests/support_ui_test.c').read_text().replace('#include "../../../../support-client/src/support_ui.h"','#include "support_ui.h"\nextern void presentation_adapter_checks(void);')
 # New presentation is a second real GLES pass. Preserve existing logical HUD
 # regression assertions, adapting only the documented backend pass counter.
 historical=historical.replace('stats.gpu.frames==4','stats.gpu.frames==8').replace('stats.gpu.frames==104','stats.gpu.frames==208')
 historical=historical.replace('result=run_support_ui_tests();','result=run_support_ui_tests();presentation_adapter_checks();')
 (t/'historical.c').write_text(historical)
 base=['gcc','-std=c11','-Wall','-Wextra','-Werror','-Wpedantic','-DSUPPORT_UI_TEST_MAIN','-I',t,'-I',g,'-I',s/'src',*files,t/'historical.c',s/'tools/tests/presentation_adapter.c','-l:'+ctypes.util.find_library('GL'),'-l:'+ctypes.util.find_library('EGL'),'-lm','-lpthread']
 rows={}
 for mode in ('host','sanitizers'):
  flags=['-O2'] if mode=='host' else ['-O1','-g','-fno-omit-frame-pointer','-fsanitize=address,undefined']
  run([*base,*flags,'-o',t/mode]);env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:abort_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
  rows[mode]=[json.loads(line) for line in run([t/mode],env=env).splitlines()]
 result={'schema':'coh-support-presentation-integration-v1','passed':True,'source_commit':run(['git','rev-parse','HEAD'],cwd=root).strip(),'source_tree_changes':run(['git','status','--porcelain','--untracked-files=no'],cwd=root).splitlines(),'source_hashes':{str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},'font_header_sha256':hashlib.sha256(a.font_header.read_bytes()).hexdigest(),'tests':rows,'scope':'Actual support UI wrapper and original source-font/tray assets on host software GLES, historical 2000 snapshot/2000 navigation mutex stress, mock panel/cue/lifecycle assertions. No Android/Thor execution.','physical_thor_accepted':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'host_gles':True,'asan_ubsan':True,'tests':rows}))
