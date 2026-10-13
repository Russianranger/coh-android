#!/usr/bin/env python3
"""Recover hash-pinned real DDS fixtures using strictly bounded release ZIP ranges."""
import io,urllib.request,struct,zipfile,hashlib,zlib,json,pathlib
class HTTPRange(io.RawIOBase):
 def __init__(self,url,size,budget=32<<20):
  self.url,self.size,self.pos,self.budget=url,size,0,budget;self.cache={};self.total=0;self.requests=[];self.etag=None
 def readable(self):return True
 def seekable(self):return True
 def tell(self):return self.pos
 def seek(self,offset,whence=0):
  self.pos=offset if whence==0 else self.pos+offset if whence==1 else self.size+offset
  if self.pos<0:raise ValueError('negative seek')
  return self.pos
 def read(self,n=-1):
  if n<0:n=self.size-self.pos
  end=min(self.size,self.pos+n)
  if self.pos>=end:return b''
  out=[]
  while self.pos<end:
   k=self.pos//65536;a=k*65536;b=min(self.size, max(a+65536, ((end+65535)//65536)*65536))-1
   if k not in self.cache:
    if self.total+b-a+1>self.budget:raise RuntimeError('network budget exceeded')
    req=urllib.request.Request(self.url,headers={'Range':f'bytes={a}-{b}'})
    with urllib.request.urlopen(req,timeout=45) as r:
     if r.status!=206 or r.headers.get('Content-Range')!=f'bytes {a}-{b}/{self.size}':raise RuntimeError('server failed exact bounded range')
     etag=r.headers.get('ETag')
     if not etag:raise RuntimeError('missing stable ETag')
     if self.etag is not None and etag!=self.etag:raise RuntimeError('asset ETag changed')
     self.etag=etag
     raw=r.read(b-a+2)
     if len(raw)!=b-a+1:raise RuntimeError('bad range length')
     self.url=r.url
     for j in range(a//65536,b//65536+1):self.cache[j]=raw[j*65536-a:(j+1)*65536-a]
     self.total+=len(raw);self.requests.append([a,b])
   lim=min(end,(k+1)*65536);out.append(self.cache[k][self.pos-a:lim-a]);self.pos=lim
  return b''.join(out)
class Subrange(io.RawIOBase):
 def __init__(self,parent,start,size):self.parent,self.start,self.size,self.pos=parent,start,size,0
 def readable(self):return True
 def seekable(self):return True
 def tell(self):return self.pos
 def seek(self,offset,whence=0):
  self.pos=offset if whence==0 else self.pos+offset if whence==1 else self.size+offset
  if self.pos<0:raise ValueError('negative seek')
  return self.pos
 def read(self,n=-1):
  n=min(self.size-self.pos,n if n>=0 else self.size-self.pos)
  if n<=0:return b''
  self.parent.seek(self.start+self.pos);raw=self.parent.read(n);self.pos+=len(raw);return raw

def subzip(parent,info):
 if info.compress_type!=zipfile.ZIP_STORED:raise ValueError('inner ZIP must be stored')
 parent.seek(info.header_offset);h=parent.read(30)
 if h[:4]!=b'PK\x03\x04':raise ValueError('bad local header')
 name,extra=struct.unpack_from('<HH',h,26);start=info.header_offset+30+name+extra
 return Subrange(parent,start,info.file_size)

def main():
 import argparse,re
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=pathlib.Path,required=True);args=ap.parse_args()
 pins=json.loads(pathlib.Path(__file__).with_name('pins.json').read_text())
 args.output.mkdir(parents=True,exist_ok=True)
 r=HTTPRange(pins['outer_asset_url'],pins['outer_expected_bytes'],32<<20)
 selected=pins['records']
 if sum(x['dds_bytes'] for x in selected)>10<<20:raise RuntimeError('corpus output size exceeds budget')
 with zipfile.ZipFile(r) as outer:
  sf=subzip(r,outer.getinfo(pins['inner_member']))
  if sf.size!=pins['inner_expected_bytes']:raise RuntimeError('inner archive size changed')
  with zipfile.ZipFile(sf) as inner:
   for pin in selected:
    sid=pin['id']
    if not re.fullmatch(r'[A-Za-z0-9_-]+',sid):raise RuntimeError('unsafe fixture id')
    info=inner.getinfo(pin['source_path'])
    if info.file_size!=pin['texture_bytes'] or f'{info.CRC:08x}'!=pin['texture_crc32']:raise RuntimeError('ZIP member pin changed')
    if info.file_size>2<<20 or info.flag_bits&1 or info.compress_type not in (0,8):raise RuntimeError('unsupported or oversized fixture member')
    raw=inner.read(info)
    if hashlib.sha256(raw).hexdigest()!=pin['texture_sha256']:raise RuntimeError('texture SHA256 mismatch')
    if len(raw)<32:raise RuntimeError('truncated wrapper')
    head,size,w,h,flags,fade0,fade1,alpha,version=struct.unpack_from('<iiiiIffB3s',raw)
    if head!=pin['dds_offset_in_texture'] or size!=pin['dds_bytes'] or head+size!=len(raw) or version not in (b'TEX',b'TX2'):raise RuntimeError('wrapper envelope changed')
    dds=raw[head:]
    if hashlib.sha256(dds).hexdigest()!=pin['dds_sha256'] or len(dds)<128 or dds[:4]!=b'DDS ':raise RuntimeError('DDS SHA256 mismatch')
    fmt=dds[84:88]
    if fmt not in (b'DXT1',b'DXT3',b'DXT5'):raise RuntimeError('unsupported DDS fixture')
    for mip in pin['mips']:
     chunk=dds[mip['dds_offset']:mip['dds_offset']+mip['bytes']]
     if len(chunk)!=mip['bytes'] or hashlib.sha256(chunk).hexdigest()!=mip['sha256']:raise RuntimeError('mip bounds or SHA256 mismatch')
    (args.output/(sid+'.dds')).write_bytes(dds)
    print(f'{sid}: {fmt.decode()} {len(pin["mips"])} mips',flush=True)
 receipt=dict(pins);receipt.update({'acquisition_passed':True,'range_bytes_downloaded':r.total,'range_count':len(r.requests),'etag_stable':True,'exact_http_range_enforced':True,'zip_member_crc32_verified':True,'all_fixture_sha256_verified':True,'ranges':r.requests})
 (args.output/'corpus.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
