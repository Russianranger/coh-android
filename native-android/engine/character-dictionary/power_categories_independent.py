"""Independent complete power category cache projection."""
import struct
class Cursor:
 def __init__(self,b):self.b=b;self.at=0
 def word(self):assert self.at+4<=len(self.b);v=struct.unpack_from('<I',self.b,self.at)[0];self.at+=4;return v
 def text(self):
  assert self.at+2<=len(self.b);n=struct.unpack_from('<H',self.b,self.at)[0];self.at+=2;assert n<260;v=self.b[self.at:self.at+n];assert len(v)==n and not b'\0'in v;self.at+=n;self.at+=(4-(n+2)%4)%4;assert self.at<=len(self.b);return v.decode('ascii')
 def segment(self):end=self.at+4+self.word();assert end<=len(self.b);return end
 def envelope(self):
  assert self.b[:8]==b'CrypticS';self.at=8;crc=self.word();assert self.text()=='Parse6'and self.text()=='Files1';end=self.segment();deps=self.word()
  for _ in range(deps):self.text();self.word()
  assert self.at==end;return crc,deps

def decode(raw):
 c=Cursor(raw);crc,deps=c.envelope();begin=c.at;end=c.segment();rows=[]
 for i in range(c.word()):
  rowend=c.segment();row={'fields':[c.text()for _ in range(5)]};row['sets']=[c.text()for _ in range(c.word())];row['indices']=[c.word()for _ in range(c.word())];assert c.at==rowend;rows.append(row)
 assert c.at==end==len(raw);return {'begin':begin,'crc':crc,'dependencies':deps,'rows':rows}
def serialize(d):
 b=bytearray()
 def words(*v):b.extend(struct.pack('<'+'I'*len(v),*v))
 words(len(d['rows']),d['dependencies'],sum(len(r['sets'])for r in d['rows']),sum(len(r['indices'])for r in d['rows']))
 for row in d['rows']:
  for s in row['fields']+row['sets']:v=s.encode();words(len(v));b.extend(v)
  words(len(row['sets']),len(row['indices']));words(*row['indices'])
 return bytes(b)
