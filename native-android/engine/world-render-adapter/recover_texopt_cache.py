#!/usr/bin/env python3
"""Recover one exact tricks.bin from the already retained original CLIENT cache archive."""
import argparse,hashlib,importlib.util,json,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve()
 if out.exists() or out==ROOT or ROOT in out.parents:raise ValueError('fresh external output directory required')
 pins=json.loads((HERE/'texopt-cache-source-pins.json').read_text());archive=a.archive.resolve()
 if archive.stat().st_size!=pins['archive']['bytes'] or sha(archive)!=pins['archive']['sha256']:raise ValueError('exact retained archive differs')
 with zipfile.ZipFile(archive) as z:
  infos=[x for x in z.infolist() if x.filename==pins['cache']['path']]
  if len(infos)!=1 or infos[0].file_size!=pins['cache']['bytes'] or infos[0].compress_size>pins['archive']['bytes'] or infos[0].flag_bits&1:raise ValueError('exact unique member bound')
  body=z.read(infos[0])
 if len(body)!=pins['cache']['bytes'] or hashlib.sha256(body).hexdigest()!=pins['cache']['sha256']:raise ValueError('exact member body differs')
 if sha(archive)!=pins['archive']['sha256']:raise ValueError('retained archive changed')
 out.mkdir(parents=True,exist_ok=False);(out/'tricks.bin').write_bytes(body)
 proof={'passed':True,'source_revision':__import__('subprocess').check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),'helper_sha256':sha(Path(__file__)),'pins_sha256':sha(HERE/'texopt-cache-source-pins.json'),'archive':pins['archive'],'member':pins['cache'],'zip_crc32':f'{infos[0].CRC:08x}','zip_crc_verified':True,'archive_preserved':True,'network_download_performed':False,'original_client_executed':False,'material_authority':False,'world_authority':False}
 (out/'recovery.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'bytes':len(body),'sha256':pins['cache']['sha256']}))
if __name__=='__main__':main()
