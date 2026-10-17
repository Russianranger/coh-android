#!/usr/bin/env python3
"""Inventory exact available repository trick bytes; never assert active CLIENT overlay/order."""
import argparse,hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
TREE='f1aab78ed5cd4e33046758f256e38e777a5ee4a3'
def command(*args):return subprocess.check_output(['git','-C',str(ROOT),*args],timeout=120)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('Fresh inventory output required')
 if command('rev-parse','HEAD:upstream/i24/data/tricks').decode().strip()!=TREE:raise ValueError('Exact retained tricks source tree differs')
 listing=command('ls-tree','-r','-l','-z','HEAD','--','upstream/i24/data/tricks');rows=[]
 for line in listing.split(b'\0'):
  if not line:continue
  meta,path=line.split(b'\t',1);mode,kind,blob,size=meta.decode().split();path=path.decode('utf-8');size=int(size)
  if kind!='blob' or mode!='100644' or not path.startswith('upstream/i24/data/tricks/') or not path.endswith('.txt') or not 0<size<=1024*1024:raise ValueError('Unexpected retained source record')
  rows.append({'path':path,'blob':blob,'bytes':size})
 if len(rows)!=1585 or sum(x['bytes'] for x in rows)!=12161418:raise ValueError('Exact source count/byte bound differs')
 requests=''.join(x['blob']+'\n' for x in rows).encode();batch=subprocess.run(['git','-C',str(ROOT),'cat-file','--batch'],input=requests,capture_output=True,timeout=120)
 if batch.returncode or len(batch.stdout)>16*1024**2:raise ValueError('Bounded source byte acquisition failed')
 cursor=0
 for row in rows:
  newline=batch.stdout.index(b'\n',cursor);blob,kind,size=batch.stdout[cursor:newline].decode().split();cursor=newline+1;size=int(size)
  if blob!=row['blob'] or kind!='blob' or size!=row['bytes']:raise ValueError('Batch source identity differs')
  data=batch.stdout[cursor:cursor+size];cursor+=size
  if len(data)!=size or batch.stdout[cursor:cursor+1]!=b'\n':raise ValueError('Batch source body bounds differ')
  cursor+=1;row['sha256']=hashlib.sha256(data).hexdigest()
 if cursor!=len(batch.stdout) or command('rev-parse','HEAD:upstream/i24/data/tricks').decode().strip()!=TREE:raise ValueError('Source bytes changed/trailing data')
 canonical=json.dumps(rows,sort_keys=True,separators=(',',':')).encode()
 if hashlib.sha256(canonical).hexdigest()!='7cf616bc57211ef73e8c87934d06d2efbd31b9b38507307f73d890419f00b98e':raise ValueError('Exact retained source byte inventory differs')
 proof={'passed':True,'scope':'available tracked repository input bytes ONLY','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'repository_revision':command('rev-parse','HEAD').decode().strip(),'repository_tricks_tree':TREE,'files':rows,'file_count':len(rows),'payload_bytes':sum(x['bytes'] for x in rows),'source_listing_sha256':hashlib.sha256(listing).hexdigest(),'canonical_file_inventory_sha256':hashlib.sha256(canonical).hexdigest(),'all_file_sha256_verified':True,'active_client_overlay_verified':False,'original_parser_order_verified':False,'postprocessed_texopt_table_available':False,'client_generation_proven':False,'material_authority':False,'world_authority':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'files':len(rows),'payload_bytes':proof['payload_bytes'],'inventory_sha256':proof['canonical_file_inventory_sha256'],'client_generation_proven':False}))
if __name__=='__main__':main()
