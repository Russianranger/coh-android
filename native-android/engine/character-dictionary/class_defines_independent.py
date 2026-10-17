"""Independent source constructor trace and complete dynamic stash projection."""
import re,struct,zlib
class Cursor:
 def __init__(self,b):self.b=b;self.at=0
 def word(self):v=struct.unpack_from('<I',self.b,self.at)[0];self.at+=4;return v
 def text(self):
  n=struct.unpack_from('<H',self.b,self.at)[0];self.at+=2;v=self.b[self.at:self.at+n];self.at+=n;self.at+=(4-(n+2)%4)%4;assert b'\0'not in v;return v.decode('ascii')
 def envelope(self):
  assert self.b[:8]==b'CrypticS';self.at=8;crc=self.word();assert self.text()=='Parse6'and self.text()=='Files1';end=self.at+4+self.word()
  for _ in range(self.word()):self.text();self.word()
  assert self.at==end;return crc
 def segment(self):end=self.at+4+self.word();assert end<=len(self.b);return end

def attrib_names(raw):
 c=Cursor(raw);crc=c.envelope();end=c.segment();groups=[]
 for _ in range(7):
  group=[]
  for _ in range(c.word()):
   rowend=c.segment();group.append([c.text()for _ in range(3)]);assert c.at==rowend
  groups.append(group)
 assert c.at==end==len(raw);return crc,groups

def traces(texts,seqrows,originrows,attrib,profile):
 load=texts['Common/entity/load_def.c'];attr=texts['Common/entity/character_attribs.h'];seq=texts['Common/seq/seqstate.c'];seqh=texts['Common/seq/seqstate.h'];pairs=[]
 enums={key:460+int(n or 0)for key,n in re.findall(r'(kSpecialAttrib_\w+)\s*=\s*sizeof\(CharacterAttributes\)(?:\s*\+\s*(\d+))?',attr)}
 enumtext=re.search(r'static DefineIntList s_PowerEnums\[\].*?\n};',load,re.S).group();enumtext=re.sub(r'//[^\n]*','',enumtext)
 for key,value in re.findall(r'\{\s*"([^"]+)"\s*,\s*(\w+)\s*}',enumtext):pairs.append((key,str(enums[value])))
 if profile==6:pairs.append(('kScience_Boost','999'))
 constants={key:int(n)for key,n in re.findall(r'^#define\s+(STATE_\w+)\s+(\d+)',seqh,re.M)};body=seq[seq.index('StateBit stateBits['):seq.index('\n};',seq.index('StateBit stateBits['))];states=[];body=re.sub(r'//[^\n]*|/\*.*?\*/','',body,flags=re.S);constants['0']=0
 for name,key in re.findall(r'\{\s*"([^"]+)"\s*,\s*(STATE_\w+|0)',body):
  assert constants[key]==len(states),(name,key,constants[key],len(states));states.append(name)
 assert len(states)==111
 for name,_ in seqrows:
  name=name.decode().upper()
  if name not in states:states.append(name)
 assert len(states)==875
 seqpairs=[('ANIM_'+name,str(i))for i,name in enumerate(states)]
 synonyms=re.search(r'char \*achSeqBits\[\].*?\n    };',load,re.S).group();synonyms=re.findall(r'"([^"]+)"',synonyms)[1:]
 seqpairs +=[('SEQBITS_'+name,str(states.index(name)))for name in synonyms]
 decl=re.search(r'typedef struct CharacterAttributes\b.*?} CharacterAttributes;',attr,re.S).group();decl=re.sub(r'//[^\n]*','',decl);offsets={};offset=0
 for member,count in re.findall(r'float\s+(\w+)\s*(?:\[\s*(\d+)\s*\])?\s*;',decl):
  for i in range(int(count or 1)):offsets[member+('['+str(i)+']'if count else'')]=offset;offset+=4
 assert offset==460
 table=re.search(r'TokenizerParseInfo ParseCharacterAttributes\[\].*?\n};',attr,re.S).group();entries=re.findall(r'\{\s*"([^"]+)"\s*,[^\n]*TOK_F32\s*\(CharacterAttributes,\s*([^,]+),',table);attributes=[(name,offsets[member.strip()])for name,member in entries];attrpairs=[('k'+name,str(offset))for name,offset in attributes]
 if profile==2:pairs+=attrpairs+seqpairs
 else:
  if profile!=1:pairs+=seqpairs
  pairs+=attrpairs
 groups=[[r[:]for r in g]for g in attrib]
 if profile==4:groups[0][0][0]='Unknown_Damage'
 for group,prefix in [(groups[0],'DamageType'),(groups[5],'Elusivity'),(groups[1],'DefenseType')]:
  for i,row in enumerate(group):
   key=row[0];value=prefix+str(i).zfill(2);pairs.append((key,value));matches=[off for name,off in attributes if name.lower()==value.lower()]
   if matches:pairs.append(('k'+key,str(matches[0])))
 origins=[r[:]for r in originrows]
 if profile==3:origins[0][0]='Unknown_Origin'
 for i,row in enumerate(origins):pairs.append(('k'+row[0]+'_Boost',str(i)))
 for i,row in enumerate(groups[2]):pairs.append(('k'+row[0],str(i+len(origins))))
 for group in groups[3:5]+groups[6:7]:
  for i,row in enumerate(group):pairs.append(('k'+row[0],str(i)))
 if profile==5:pairs.append(('kscience_boost','999'))
 return pairs,states

def parse_trace(raw):
 at=0;pairs=[]
 while at<len(raw):
  kn,vn=struct.unpack_from('<II',raw,at);at+=8;k=raw[at:at+kn].decode();at+=kn;v=raw[at:at+vn].decode();at+=vn;pairs.append((k,v))
 assert at==len(raw);return pairs

def parse_slots(raw):
 n,count=struct.unpack_from('<II',raw);at=8;slots=[]
 for _ in range(n):
  present=struct.unpack_from('<I',raw,at)[0];at+=4;assert present in(0,1)
  if not present:slots.append(None);continue
  kn,vn=struct.unpack_from('<II',raw,at);at+=8;k=raw[at:at+kn].decode();at+=kn;v=raw[at:at+vn].decode();at+=vn;slots.append((k,v))
 assert at==len(raw)and sum(s is not None for s in slots)==count;return slots

def trace_wire(pairs):return b''.join(struct.pack('<II',len(k),len(v))+k.encode()+v.encode()for k,v in pairs)
def slot_crc(slots):return zlib.adler32(b''.join(k.encode()+v.encode()for s in slots if s is not None for k,v in[s]))&0xffffffff
