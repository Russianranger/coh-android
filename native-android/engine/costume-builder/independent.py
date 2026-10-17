"""Independent bounded lazy source-schema traversal and primary insertion order."""
import hashlib,struct,math
U32=lambda n:struct.pack('<I',n)
class Refused(ValueError):pass
class Nodes:
 def __init__(self,raw,schemas,names):self.raw=raw;self.schemas=schemas;self.names=names;self.visits=0
 def num(self,at,n=4):
  if at<0 or at+n>len(self.raw):raise Refused('short')
  return int.from_bytes(self.raw[at:at+n],'little')
 def node(self,ref):
  table,start=ref;self.visits+=1
  if self.visits>1000000:raise Refused('visits')
  at=start+4;end=at+self.num(start)
  if end>len(self.raw):raise Refused('segment')
  result={}
  for col,(flags,param,child)in enumerate(self.schemas[table]):
   base=flags&255
   if flags&256 or base==2:continue
   n=self.num(at)if flags&(1<<20)else param if flags&(1<<21)else 1
   if flags&(1<<20):at+=4
   if n>65536:raise Refused('count')
   values=[]
   for i in range(n):
    if base==29:values.append((child,at));at+=4+self.num(at)
    elif base in(9,13):
     length=self.num(at,2);at+=2
     if length>=12000 or at+length>end:raise Refused('text')
     text=self.raw[at:at+length];at+=length;pad=(-(length+2))%4
     if 0 in text or any(self.raw[at:at+pad]):raise Refused('text canonical')
     at+=pad;values.append(None if not length and not flags&(1<<20)else text)
    elif base in(5,7,20):width=1 if base==20 else 4;values.append(self.num(at,width));at+=width
    else:raise Refused('type')
    if at>end:raise Refused('field end')
   result[self.names[table][col]]=values
  if at!=end:raise Refused('node end')
  return result
 def palette(self,ref):
  p=self.node(ref)
  for color in p['Color']:
   values=self.node(color)[''];rgb=struct.unpack('<fff',b''.join(U32(v)for v in values))
   if not all(math.isfinite(v)and 0<=v<=255 for v in rgb):raise Refused('color')
   r,g,b=map(int,rgb);yield r+(g<<8)+(b<<16)+0xff000000

def trace(raw,palette,schemas,names,emit):
 data=Nodes(raw,schemas,names);colors=Nodes(palette,schemas,names);root=next(i for i,s in enumerate(schemas)if len(s)==1 and s[0][0]&255==29);pal=next(i for i,n in enumerate(names)if n==['Color','Name','End','EndPalette']);counts=[0,0,0]
 def add(kind,value):
  if value is None:return
  if kind==2:
   if not value:return
   emit(U32(kind)+U32(value))
  else:
   if any(v>=128 for v in value):raise Refused('C-locale equality profile')
   emit(U32(kind)+U32(len(value))+value)
  counts[kind]+=1
 for v in colors.palette((pal,92)):add(2,v)
 master=data.node((root,48116))
 for bodyref in reversed(master['Costume']):
  body=data.node(bodyref);add(1,body['Name'][0])
  for originref in reversed(body['Origin']):
   origin=data.node(originref)
   for field in('SkinPalette','BodyPalette'):
    if not origin[field]:raise Refused('missing required first palette')
    for v in data.palette(origin[field][0]):add(2,v)
   for regionref in reversed(origin['Region']):
    region=data.node(regionref);add(1,region['Name'][0])
    for boneref in reversed(region['BoneSet']):
     bone=data.node(boneref);add(1,bone['Name'][0])
     for georef in reversed(bone['GeoSet']):
      geo=data.node(georef)
      for texref in reversed(geo['Info']):
       tex=data.node(texref)
       for field in('Geo','Tex1','Tex2','Fx'):
        v=tex[field][0]
        if v is not None and field in('Tex1','Tex2'):v=v.split(b'.',1)[0]
        add(0,v)
      for v in reversed(geo['Masks']):add(0,v)
      for maskref in reversed(geo['Mask']):add(0,data.node(maskref)['Name'][0])
 return {'attempts':counts,'visited_nodes':data.visits,'palette_nodes':colors.visits}

class Table:
 def __init__(self,n,kind,hashfn):self.slots=[None]*n;self.kind=kind;self.hashfn=hashfn;self.count=0;self.duplicates=0;self.resizes=0;self.attempts=0
 def insert(self,key,count_attempt=True):
  if count_attempt:self.attempts+=1
  mask=len(self.slots)-1;idx=self.hashfn(key)&mask;probe=1
  while self.slots[idx]is not None:
   other=self.slots[idx]
   if (key==other if self.kind==2 else key.lower()==other.lower()):self.duplicates+=int(count_attempt);return
   idx=(idx+probe*probe)&mask;probe+=1
   if probe>len(self.slots):raise Refused('probe')
  self.slots[idx]=key;self.count+=1
  if self.count>=len(self.slots)*3//4:
   old=self.slots;n=8
   while n<self.count*2:n*=2
   if n>65536:raise Refused('slot cap')
   self.slots=[None]*n;self.count=0;self.resizes+=1
   for value in old:
    if value is not None:self.insert(value,False)
 def wire(self):
  out=bytearray(U32(len(self.slots))+U32(self.count))
  for value in self.slots:
   out+=U32(value is not None)
   if value is not None:out+=U32(value)if self.kind==2 else U32(len(value))+value
  return out

def replay(raw,hash_string,hash_int):
 tables=[Table(4096,0,hash_string),Table(256,1,hash_string),Table(128,2,hash_int)];at=0
 while at<len(raw):
  if at+8>len(raw):raise Refused('trace short')
  kind,n=struct.unpack_from('<II',raw,at);at+=8
  if kind>2:raise Refused('trace kind')
  if kind==2:value=n
  else:
   if n>=12000 or at+n>len(raw):raise Refused('trace length')
   value=raw[at:at+n];at+=n
   if 0 in value or any(v>=128 for v in value):raise Refused('trace text')
  tables[kind].insert(value)
 return b''.join(t.wire()for t in tables),[{'max_size':len(t.slots),'valid':t.count,'duplicates':t.duplicates,'resizes':t.resizes,'attempts':t.attempts}for t in tables]
