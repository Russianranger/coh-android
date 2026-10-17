#!/usr/bin/env python3
"""Recover five exact primary Khronos header bodies for host-only compilation."""
import argparse,hashlib,json,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('New external header directory required')
 pins=json.loads((HERE/'egl-host-header-pins.json').read_text());raws={}
 for name,pin in pins.items():
  with urllib.request.urlopen(pin['url'],timeout=30) as response:raw=response.read(1024*1024)
  if len(raw)!=pin['bytes'] or hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('Khronos header identity differs')
  raws[name]=raw
 a.output.mkdir(parents=True)
 for name,raw in raws.items():
  path=a.output/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
 (a.output/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
 print(json.dumps({'passed':True,'primary_headers':len(raws)}))
if __name__=='__main__':main()
