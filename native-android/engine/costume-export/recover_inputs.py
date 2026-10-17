#!/usr/bin/env python3
"""Verify exact preserved donor bytes; no download, regeneration or server run."""
import argparse,hashlib,json,zipfile
from pathlib import Path
ARTIFACT_BYTES=26476333
ARTIFACT_SHA='51b5519f86896a846eebd6a20de15c935d788af70d9986083df361af57fdcfae'
FILES={'client-caches.zip':(27071659,'5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051'),'client-cache-manifest.json':(20195,'e5bc9ff306f90f96b6d34d4d481b30804af078b0e07845dafd71f7324dff6352'),'client-caches.zip.sha256':(84,'d93561c7e4f0c1e26c3b90172faf7aa1ab80334db2d6743e8f702920736bdf1c')}
WANTED={'data/bin/BodyParts.bin':(2584,'b0955c46731ed0cb54ad01d96015b301e583bd0224f8d872f50cfefeb08f6beb'),'data/bin/costume.bin':(17691352,'10ef7562156be60bd1ef3c437c3b46d10b36b6b265129c10f39d25c4a4df5a77'),'data/bin/supergroupColors.bin':(2664,'e5676ebbccc380f9d69322ef6750332b0b7e7a46d915bdfb591322862d22cb75')}
def sha(b):return hashlib.sha256(b).hexdigest()
def require(test,label):
 if not test:raise ValueError(label)
def members(z,expected):
 items=z.infolist();names=[i.filename for i in items];require(len(names)==len(set(n.casefold()for n in names))and set(names)==set(expected),'Inventory')
 for i in items:
  require(not i.is_dir()and not i.flag_bits&1 and i.compress_type in(0,8),'Entry type')
  require(not i.filename.startswith('/')and'\\'not in i.filename and':'not in i.filename and all(p not in('','.','..')for p in i.filename.split('/')),'Entry path')
  require(i.file_size==expected[i.filename][0]and 0<i.file_size<=256*1024*1024,'Entry bound')
 require(sum(i.file_size for i in items)<=512*1024*1024,'Total bound')
def recover(artifact,output):
 require(not output.exists(),'Fresh output');require(artifact.is_file()and not artifact.is_symlink()and artifact.stat().st_size==ARTIFACT_BYTES,'Artifact bound')
 raw=artifact.read_bytes();require(sha(raw)==ARTIFACT_SHA,'Artifact SHA')
 output.mkdir(parents=True)
 with zipfile.ZipFile(artifact)as z:
  members(z,FILES)
  for n,(size,h)in FILES.items():
   b=z.read(n);require(len(b)==size and sha(b)==h,'Outer member SHA');(output/n).write_bytes(b)
 manifest=json.loads((output/'client-cache-manifest.json').read_text());require(manifest.get('source_commit')=='0b75ade0c801735e10c5798f641948a45cc50488'and manifest.get('data_commit')=='d51533ec8e6a9cf726b9214968077a05fdcf19f3'and manifest.get('repository_commit')=='a40250b0032bd05a333514920722ddffa4427730','Generation identity')
 expected={n:(r['bytes'],r['sha256'])for n,r in manifest['files'].items()};require(len(expected)==100,'Cache count')
 with zipfile.ZipFile(output/'client-caches.zip')as z:
  members(z,dict(expected,**{'client-cache-manifest.json':FILES['client-cache-manifest.json']}))
  for n,(size,h)in dict(expected,**{'client-cache-manifest.json':FILES['client-cache-manifest.json']}).items():
   b=z.read(n);require(len(b)==size and sha(b)==h,'Cache SHA '+n)
  for n,(size,h)in WANTED.items():
   require(expected[n]==(size,h),'Exact selected generation');p=output/'exact-bins'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
 result={'schema':1,'passed':True,'artifact_id':11092897979,'run_id':36707839624,'artifact_bytes':ARTIFACT_BYTES,'artifact_sha256':ARTIFACT_SHA,'archive_bytes':FILES['client-caches.zip'][0],'archive_sha256':FILES['client-caches.zip'][1],'all100cache_files_hashed':True,'all101member_inventory_valid':True,'exact_extracted_bins':{n:{'bytes':v[0],'sha256':v[1]}for n,v in WANTED.items()},'recovery_script_sha256':sha(Path(__file__).read_bytes()),'runtime_executed':False,'source_builder_executed':False,'slot_maps_captured':False}
 (output/'recovery-proof.json').write_text(json.dumps(result,indent=2)+'\n');return result
def main():
 p=argparse.ArgumentParser();p.add_argument('--artifact',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(recover(a.artifact.resolve(),a.output.resolve()),indent=2))
if __name__=='__main__':main()
