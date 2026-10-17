"""Mechanical exact source schema and bounded independent power-set projection."""
import re,struct,hashlib
KINDS={'STRING':1,'CURRENTFILE':1,'STRINGARRAY':2,'INT':3,'BOOL':3,'INTARRAY':4,'AUTOINTEARRAY':4}
def schema(source):
 body=re.search(r'TokenizerParseInfo ParseBasePowerSet\[\]\s*=.*?\n};',source,re.S).group();fields=[]
 for name,value in re.findall(r'\{\s*"([^"]*)",\s*(.*?)\}',body,re.S):
  macro=re.search(r'\bTOK_(\w+)\(',value)
  if not macro:continue
  kind=macro.group(1);assert kind in KINDS,kind;fields.append({'name':name,'kind':KINDS[kind],'source_token':kind})
 assert len(fields)==30
 return fields,hashlib.sha256(body.encode()).hexdigest()
def decode(raw,fields):
 at=0
 def word():
  nonlocal at
  assert at+4<=len(raw);v=struct.unpack_from('<I',raw,at)[0];at+=4;return v
 def string():
  nonlocal at
  assert at+2<=len(raw);n=struct.unpack_from('<H',raw,at)[0];at+=2;assert n<260 and at+n<=len(raw);s=raw[at:at+n];assert b'\0'not in s;at+=n;at+=(4-(n+2)%4)%4;return s.decode('ascii')
 assert raw[:8]==b'CrypticS';at=8;crc=word();assert string()=='Parse6'and string()=='Files1';files_end=at+4+struct.unpack_from('<I',raw,at)[0];word();deps=word()
 for _ in range(deps):string();word()
 assert at==files_end;begin=at;root_end=at+4+struct.unpack_from('<I',raw,at)[0];word();count=word();assert root_end==len(raw)and count<=8192;rows=[]
 for i in range(count):
  start=at;end=at+4+struct.unpack_from('<I',raw,at)[0];word();values=[];spans=[]
  for f in fields:
   s=at;k=f['kind']
   if k==1:value=string()
   elif k==2:value=[string()for _ in range(word())]
   elif k==3:value=word()
   else:value=[word()for _ in range(word())]
   values.append(value);spans.append([s,at]);assert at<=end
  assert at==end;rows.append({'record':[start,end],'fields':values,'spans':spans})
 assert at==root_end
 return {'crc':crc,'begin':begin,'dependency_count':deps,'rows':rows}
