#!/usr/bin/env python3
"""Prepare one complete neutral Male preview, using existing pinned sources.

Reuses the tracked 1.84 MB avatar supplement, one bounded original head texture
and two bounded source animation members. Never fetches the complete Base pack.
Output stays external to source and is SHA-pinned in actor.json. No Android or
physical qualification is inferred by preparation.
"""
import argparse,hashlib,importlib.util,json,struct,subprocess,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;NATIVE=HERE.parents[1];ROOT=NATIVE.parent
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--assets-root',type=Path);p.add_argument('--rig',type=Path);p.add_argument('--library',type=Path);args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
 pins=json.loads((HERE/'actor-pins.json').read_text());assets=args.assets_root or args.output/'corpus';assets.mkdir(parents=True,exist_ok=True);source=args.output/'source'
 required={**json.loads((HERE/'source-pins.json').read_text())['source_files'],**pins['source_files']}
 for name,digest in required.items():
  original=args.source_root/name;raw=original.read_bytes() if original.is_file() else subprocess.check_output(['git','show','HEAD:'+name],cwd=args.source_root)
  normalized=raw.replace(b'\r\n',b'\n');assert sha(raw)==digest or sha(normalized)==digest,name
  dst=source/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(raw)
 if not args.assets_root:
  archive=args.source_root/'assets'/pins['supplement_zip']['filename'];raw=archive.read_bytes() if archive.exists() else subprocess.check_output(['git','show','HEAD:assets/'+pins['supplement_zip']['filename']],cwd=args.source_root)
  assert len(raw)==pins['supplement_zip']['bytes'] and sha(raw)==pins['supplement_zip']['sha256']
  import io
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   for name in z.namelist():
    pin=pins['files'][name];b=z.read(name);assert len(b)==pin['bytes'] and sha(b)==pin['sha256'];dst=assets/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(b)
 ranges=module('male_preview_ranges',NATIVE/'tools/animation_fixture/acquire.py');readers={}
 def acquire(package,name,pin,target):
  if target.is_file():
   raw=target.read_bytes()
   if len(raw)==pin['bytes'] and sha(raw)==pin['sha256']:return raw
  key=(package['outer_asset_url'],package['inner_member'])
  if key not in readers:
   reader=ranges.HTTPRange(key[0],package['outer_expected_bytes'],8<<20)
   with zipfile.ZipFile(reader) as archive:inner=ranges.subzip(reader,archive.getinfo(key[1]))
   assert inner.size==package['inner_expected_bytes'];readers[key]=(reader,inner)
  reader,inner=readers[key]
  with zipfile.ZipFile(inner) as archive:
   info=archive.getinfo(name);assert not info.flag_bits&1 and info.compress_type in (0,8) and info.file_size==pin['bytes'] and info.file_size<=2<<20
   raw=archive.read(info);assert len(raw)==pin['bytes'] and sha(raw)==pin['sha256'],name
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);return raw
 face='data/texture_library/players/avatar/male/face/face_skin_head_01.texture'
 acquire(json.loads((NATIVE/'tools/material_fixture/pins.json').read_text()),face,pins['files'][face],assets/face)
 rig=args.rig or args.output/'male-jump_n_smash.bin'
 if not args.rig:
  package=json.loads((NATIVE/'tools/animation_fixture/pins.json').read_text());base_name='assets/player_library/animations/male/skel_ready2.anim';motion_name='assets/player_library/animations/male/jump_n_smash.anim'
  bp=json.loads((NATIVE/'engine/sequencer/showcase/base-pins.json').read_text())[base_name];mp=json.loads((NATIVE/'engine/sequencer/continuation/extra-asset-pins.json').read_text())['male/jump_n_smash']
  base=acquire(package,base_name,bp,assets/'male-ready.anim');motion=acquire(package,motion_name,mp,assets/'male-jump.anim');prep=module('male_preview_animation_prepare',NATIVE/'tools/animation_fixture/prepare.py');meta,_=prep.inspect_animation(motion);raw=bytearray(prep.make_rig(base,motion,[0],0));struct.pack_into('<3f',raw,48,1.,meta['length_frames'],30.);assert sha(raw)==pins['neutral_rig_sha256'];rig.write_bytes(raw)
 assert sha(rig.read_bytes())==pins['neutral_rig_sha256']
 library=args.library or args.output/'libappearance-prepare.so'
 if not args.library:
  sources=[HERE/x for x in ['coh_appearance.c','coh_appearance_adapters.c','coh_appearance_mesh.c','coh_appearance_render.c','coh_appearance_actor.c']]+[NATIVE/x for x in ['character/coh_character.c','engine/assets/coh_asset_geo.c','engine/assets/coh_asset_loader.c','src/coh_assets.c','src/coh_dds.c','material-probe/app/src/main/cpp/coh_mesh.c','engine/renderer/coh_renderer.c']]
  subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-ffp-contract=off','-shared','-fPIC','-I',str(NATIVE/'include'),*map(str,sources),'-lz','-lm','-o',str(library)],check=True)
 prepared=module('male_preview_asset_preparation',HERE/'tests/actor_gpu.py');state=prepared.prepare(library.resolve(),assets,source,rig,args.output);result=state[10]
 result['acquisition']={'strict_http206':True,'archive_complete_hash_claim':False,'network_bytes':sum(x.total for x,_ in readers.values()),'range_count':sum(len(x.requests) for x,_ in readers.values()),'asset_source_pins':'engine/appearance/actor-pins.json'}
 (args.output/'actor.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['package']))
if __name__=='__main__':main()
