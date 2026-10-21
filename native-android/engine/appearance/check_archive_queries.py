#!/usr/bin/env python3
"""Source-loader4MiB appearance queries preserve the accepted world ZIP bound."""
from pathlib import Path
import argparse,json,os,subprocess,tempfile,zipfile
HERE=Path(__file__).resolve().parent;NATIVE=HERE.parents[1]
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--mode',choices=['release','asan','ubsan','all'],default='all');args=parser.parse_args();result={}
 with tempfile.TemporaryDirectory(prefix='coh-appearance-archive-') as temporary:
  work=Path(temporary);archive=work/'source.zip'
  with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
   z.writestr('data/player_library/v_huge_spadr.geo',bytes(i%251 for i in range(1500000)))
   z.writestr('data/texture_library/first/chest_stripe_1.texture',b'one')
   z.writestr('data/texture_library/second/CHEST_STRIPE_1.texture',b'two')
   # Authentic reference manifest path; tiny explicit test body is not a texture oracle.
   z.writestr('texture_library/v_players/avatar/male/face/helmets/face_v_helmet_robotic_01.texture',b'face')
   z.writestr('DATA/TEXTURE_LIBRARY/duplicate/FACE_V_HELMET_ROBOTIC_01.texture',b'late')
   z.writestr('ASSETS/Texture_Library/Other/MaSk_ReFeReNcE.texture',b'mask')
   z.writestr('unrelated/face_v_helmet_robotic_01.texture',b'wrong')
  sources=[HERE/'test_archive_queries.c']+[NATIVE/name for name in ('engine/assets/coh_asset_zip.c','engine/assets/coh_asset_loader.c','src/coh_assets.c','src/coh_dds.c')]
  for mode in ['release','asan','ubsan'] if args.mode=='all' else [args.mode]:
   flags=['-O2'] if mode=='release' else ['-O1','-g','-fno-omit-frame-pointer','-fsanitize='+('address' if mode=='asan' else 'undefined')]
   exe=work/mode;subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-I'+str(NATIVE/'include'),*flags,*map(str,sources),'-lz','-lm','-o',str(exe)],check=True)
   result[mode]=json.loads(subprocess.check_output([str(exe),str(archive)],text=True,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
 print(json.dumps(result))
if __name__=='__main__':main()
