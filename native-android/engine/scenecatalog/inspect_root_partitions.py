#!/usr/bin/env python3
"""Exact retained source-only root model partition ledger; no texture selection."""
import argparse,hashlib,json,struct
from pathlib import Path
RESOURCE_SHA='8500764939215b576e5ff88056ec85b475785038e09600019846ff5a06eb1cd6'
COVERAGE_SHA='5df9bc58cb49c9a177a8315a841701bd300dbdf6641d27ef0b81345f1f6be197'
def bound(path,limit,expected):
 if path.stat().st_size>limit:raise ValueError('input size bound')
 raw=path.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('exact retained input digest')
 return raw
def build(resources,coverage):
 raw=bound(resources,32<<20,RESOURCE_SHA);closure=json.loads(bound(coverage,4<<20,COVERAGE_SHA));rows=[];at=0
 while at<len(raw):
  if len(rows)>=65600 or len(raw)-at<192 or raw[at:at+8]!=b'COHRES01':raise ValueError('record envelope')
  version,header,size=struct.unpack_from('<3I',raw,at+8)
  if version!=1 or header!=192 or size<192 or size>128<<10 or size>len(raw)-at:raise ValueError('record extent')
  end=at+size;pos=at+192;strings=[]
  for off in (48,52,56,60,64,124):
   n=struct.unpack_from('<I',raw,at+off)[0]
   if not n:strings.append(None);continue
   if n<2 or n>256 or n>end-pos or raw[pos+n-1]:raise ValueError('string extent')
   text=raw[pos:pos+n-1]
   if any(x<32 or x>126 for x in text):raise ValueError('ASCII source string')
   strings.append(text.decode('ascii'));pos+=n
  count=struct.unpack_from('<I',raw,at+96)[0];textures=[]
  if count>256:raise ValueError('partition bound')
  for _ in range(count):
   if end-pos<12:raise ValueError('partition header')
   tid,tris,n=struct.unpack_from('<3I',raw,pos);pos+=12
   if n<2 or n>256 or n>end-pos or raw[pos+n-1]:raise ValueError('partition name extent')
   text=raw[pos:pos+n-1]
   if any(x<32 or x>126 for x in text):raise ValueError('ASCII partition')
   textures.append((tid,tris,text.decode('ascii')));pos+=n
  if pos!=end:raise ValueError('record end')
  rows.append((strings,textures));at=end
 if len(rows)!=40232 or len(closure['models'])!=2916:raise ValueError('fixed capture/closure identity')
 out=[];seen=set()
 for model in closure['models']:
  for ordinal in model['source_ordinals']:
   if ordinal in seen or ordinal<0 or ordinal>=len(rows):raise ValueError('unique source owner ordinal')
   seen.add(ordinal);names,textures=rows[ordinal]
   if names[1]!=model['metadata']['name'] or names[2]!=model['source_geo_name']:raise ValueError('actual row identity vs qualified closure')
   out.append({'source_ordinal':ordinal,'model':names[1],'source_geo_name':names[2],'textures':textures})
 if len(out)!=3083:raise ValueError('root model-owner closure')
 return {'scope':'Exact captured SERVER model partition observations over previously qualified root closure; not CLIENT TexOpt/texture selection or material authority','resources_sha256':RESOURCE_SHA,'root_coverage_sha256':COVERAGE_SHA,'model_owner_rows':len(out),'rows':out}
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('resources','root-coverage','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();result=build(a.resources,a.root_coverage)
 with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({'passed':True,'rows':len(result['rows']),'sha256':hashlib.sha256(a.output.read_bytes()).hexdigest()}))
if __name__=='__main__':main()
