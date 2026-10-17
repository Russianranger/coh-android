"""Malformed/local-cap controls explicitly joining exact original leaf spans.
Not additional executions of original gameplay producer or authentic packets.
"""
class Bits:
 def __init__(self,raw,mode,begin):self.data=[(x>>(i%8))&1 for i in range(len(raw)*8)for x in [raw[i//8]]];self.mode=mode;self.at=begin
 def scalar(self,n):
  n=(n+7)//8*8 if self.mode else n
  if n>len(self.data)-self.at:raise ValueError('cut')
  v=sum(b<<i for i,b in enumerate(self.data[self.at:self.at+n]));self.at+=n;return v
 def packed(self,n):
  if self.mode:return self.scalar(32)
  base=0
  while True:
   v=self.scalar(n)
   if n==32 or v<(1<<n)-1:return base+v
   base+=v;n=min(n*2,32)
 def text(self):
  while self.scalar(8):pass
 def put(self,at,n,value):self.data[at:at+n]=[(value>>i)&1 for i in range(n)]
 def wire(self,end=None):
  bits=self.data[:end];raw=bytearray((len(bits)+7)//8)
  for i,b in enumerate(bits):raw[i//8]|=b<<(i%8)
  return bytes(raw),len(bits)
def controls(cases):
 rows=[]
 for mode in(0,1):
  source=next(c for c in cases if c['aligned']==mode and c['begin']==0 and len(c['modifiers'])==1)
  b=Bits(bytes.fromhex(source['wire_hex']),mode,0);b.scalar(1);b.scalar(1);target=b.scalar(1)
  if target:b.scalar(32)
  values=b.at
  for _ in range(69):b.scalar(32);b.scalar(2)
  first=b.at;assert b.scalar(1)==1;b.packed(10);tag=b.at;auto=b.scalar(2);b.scalar([2,10,24,32][auto]);b.scalar(2);chance=b.at;b.scalar(32);b.scalar(32);last=b.at;assert b.scalar(1)==0 and b.at==source['end']
  original=b.data[:first];modifier=b.data[first:last];endflag=[0]*(8 if mode else 1)
  for count in(256,257):
   copy=Bits(b'',mode,0);copy.data=original+modifier*count+endflag;wire,bits=copy.wire();rows.append(dict(label='modifier-count-'+str(count),mode=mode,wire=wire,bits=bits,status=0 if count==256 else 4,count=256 if count==256 else 0))
  for label,at,n,value in [('nonfinite-value',values,32,0x7f800000),('nonfinite-chance',chance,32,0x7fc00000)]+([('auto-tag-out-of-range',tag,8,4)]if mode else[]):
   copy=Bits(bytes.fromhex(source['wire_hex']),mode,0);copy.put(at,n,value);wire,bits=copy.wire(source['end']);rows.append(dict(label=label,mode=mode,wire=wire,bits=bits,status=1,count=0))
  source=next(c for c in cases if c['aligned']==mode and c['begin']==0 and any(m['source_type']>=2 for m in c['modifiers']))
  b=Bits(bytes.fromhex(source['wire_hex']),mode,0);b.scalar(1);b.scalar(1);target=b.scalar(1)
  if target:b.scalar(32)
  for _ in range(69):b.scalar(32);b.scalar(2)
  first=b.at
  for mod in source['modifiers']:
   start=b.at;assert b.scalar(1)==1;b.packed(10);tag=b.scalar(2);b.scalar([2,10,24,32][tag]);kind=b.scalar(2)
   if kind>=2:name_begin=b.at;b.text();name_end=b.at;b.packed(20)
   b.scalar(32);b.scalar(32)
   if kind>=2:break
  mod_end=b.at;header=b.data[:first];before=b.data[start:name_begin];after=b.data[name_end:mod_end]
  for length in(65535,65536):
   copy=Bits(b'',mode,0);name=[(65>>i)&1 for i in range(8)]*length+[0]*8;copy.data=header+before+name+after+endflag;wire,bits=copy.wire();rows.append(dict(label='source-text-'+str(length),mode=mode,wire=wire,bits=bits,status=0 if length==65535 else 4,count=1 if length==65535 else 0))
 return rows
