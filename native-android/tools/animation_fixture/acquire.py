#!/usr/bin/env python3
"""Recover hash-pinned real animation tracks using strictly bounded release ZIP ranges."""
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
 readers={};ranges={}
 for pin in pins['records']:
  url=pin.get('outer_asset_url',pins['outer_asset_url']);member=pin.get('inner_member',pins['inner_member']);key=(url,member)
  if key not in readers:
   r=HTTPRange(url,pin.get('outer_expected_bytes',pins['outer_expected_bytes']),2<<20)
   with zipfile.ZipFile(r) as outer:sf=subzip(r,outer.getinfo(member))
   if sf.size!=pin.get('inner_expected_bytes',pins['inner_expected_bytes']):raise RuntimeError('inner archive size changed')
   readers[key]=(r,sf)
  r,sf=readers[key]
  if not re.fullmatch(r'[a-z0-9]+\.anim',pin['file_name']):raise RuntimeError('unsafe fixture name')
  if not 0<pin['size']<=2<<20 or pin['method'] not in (0,8):raise RuntimeError('unsupported or oversized member')
  sf.seek(pin['offset']);header=sf.read(30)
  if header[:4]!=b'PK\x03\x04':raise RuntimeError('ZIP local header signature differs')
  flags,method=struct.unpack_from('<HH',header,6)
  if flags&1 or method!=pin['method']:raise RuntimeError('ZIP method/encryption differs')
  nl,el=struct.unpack_from('<HH',header,26);name=sf.read(nl).decode('utf8')
  if name!=pin['name']:raise RuntimeError('ZIP local member name differs')
  sf.seek(pin['offset']+30+nl+el);stored=sf.read(pin['compressed'])
  if len(stored)!=pin['compressed']:raise RuntimeError('truncated ZIP member')
  if pin['method']==8:
   de=zlib.decompressobj(-15);raw=de.decompress(stored,pin['size']+1)
   if not de.eof or de.unused_data or de.unconsumed_tail:raise RuntimeError('deflate stream bounds differ')
  else:raw=stored
  if len(raw)!=pin['size'] or f'{zlib.crc32(raw):08x}'!=pin['crc32'] or hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise RuntimeError('ZIP fixture size/CRC/SHA256 mismatch')
  (args.output/pin['file_name']).write_bytes(raw)
  print(f'{pin["id"]}: {name} {len(raw)}B SHA256 verified',flush=True)
 receipt=dict(pins);receipt.update({'acquisition_passed':True,'range_bytes_downloaded':sum(r.total for r,sf in readers.values()),'range_count':sum(len(r.requests) for r,sf in readers.values()),'etag_stable':True,'exact_http_range_enforced':True,'zip_member_crc32_verified':True,'all_fixture_sha256_verified':True,'ranges_by_archive':{key[0]:r.requests for key,(r,sf) in readers.items()}})
 (args.output/'corpus.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
