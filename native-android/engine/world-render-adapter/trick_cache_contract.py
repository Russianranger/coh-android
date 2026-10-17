"""Immutable full persisted TrickInfo/StAnim/AutoLOD wire grammar; no active dictionary."""
from dataclasses import dataclass
import hashlib,re,struct,math
from texopt_cache_contract import Cursor,CacheInput
@dataclass(frozen=True,slots=True)
class Field:
 name:str;kind:str;count:int=1;nested:str=''
@dataclass(frozen=True,slots=True)
class Value:
 name:str;kind:str;offset:int;size:int;value:object
@dataclass(frozen=True,slots=True)
class TrickWire:
 ordinal:int;values:tuple

def schema(tricks,autolod,pins):
 if hashlib.sha256(tricks.encode()).hexdigest()!=pins['tricks'] or hashlib.sha256(autolod.encode()).hexdigest()!=pins['autolod']:raise ValueError('exact source schema required')
 result=[]
 for table,source in [('parse_st_anim',tricks),('parse_auto_lod',autolod),('parse_trick',tricks)]:
  start=source.index('TokenizerParseInfo '+table+'[]');text=source[source.index('{',start)+1:source.index('\n};',start)];text=re.sub(r'/\*.*?\*/','',text,flags=re.S);fields=[]
  for line in text.splitlines():
   line=line.split('//',1)[0].strip()
   if not line:continue
   m=re.fullmatch(r'\{\s*"((?:\\.|[^"\\])*)"\s*,(.*)\}\s*,?',line)
   if not m:raise ValueError('unsupported source declaration '+line)
   name,expr=m.groups()
   if re.fullmatch(r'\s*0\s*,\s*0\s*',expr) or 'TOK_END' in expr or 'TOK_REDUNDANTNAME' in expr:continue
   if 'TOK_STRUCT(' in expr:
    target=re.search(r'TOK_STRUCT\(\s*\w+\s*,\s*\w+\s*,\s*(\w+)\s*\)',expr)
    if not target:raise ValueError('unsupported nested array')
    f=Field(name,'array',nested=target[1])
   elif 'TOK_STRING(' in expr or 'TOK_CURRENTFILE(' in expr:f=Field(name,'string')
   elif 'TOK_VEC2(' in expr:f=Field(name,'float',2)
   elif 'TOK_FIXED_ARRAY' in expr:
    n=re.search(r',\s*(\d+)\s*$',expr)
    if not n or int(n[1])>4:raise ValueError('fixed count')
    f=Field(name,'u8' if 'TOK_U8_X' in expr else 'float' if 'TOK_F32_X' in expr else 'unsupported',int(n[1]))
   elif 'TOK_F32(' in expr:f=Field(name,'float')
   elif any(x in expr for x in ('TOK_FLAGS(','TOK_TIMESTAMP(')):f=Field(name,'u32')
   else:raise ValueError('unknown source token '+expr)
   fields.append(f)
  if not fields or len(fields)>64:raise ValueError('table bound')
  result.append((table,tuple(fields)))
 return tuple(result)
def decode(cache,ordinal,tables):
 if not isinstance(cache,CacheInput) or not 0<=ordinal<len(cache.tricks):raise ValueError('cache row')
 row=cache.tricks[ordinal];cursor=Cursor(cache.body,row.offset,row.offset+row.size);lookup=dict(tables);budget=[0]
 def table(c,name,depth):
  if depth>1:raise ValueError('nested depth')
  values=[]
  for f in lookup[name]:
   start=c.pos
   if f.kind=='array':
    count=c.u32()
    if count>256 or budget[0]+count>512:raise ValueError('array budget')
    budget[0]+=count;children=[]
    for i in range(count):
     size=c.u32();end=c.pos+size
     if end>c.end:raise ValueError('child extent')
     sub=Cursor(c.body,c.pos,end);children.append(table(sub,f.nested,depth+1))
     if sub.pos!=end:raise ValueError('child length')
     c.pos=end
    value=tuple(children)
   elif f.kind=='string':value=c.pascal()
   else:
    words=tuple(c.u32() for _ in range(f.count))
    if f.kind=='float':
     value=tuple(struct.unpack('<f',struct.pack('<I',n))[0] for n in words)
     if not all(math.isfinite(n) for n in value):raise ValueError('nonfinite input')
    elif f.kind=='u8':value=tuple(n&255 for n in words)
    else:value=words
    if f.count==1:value=value[0]
   values.append(Value(f.name,f.kind,start,c.pos-start,value))
  return tuple(values)
 result=TrickWire(ordinal,table(cursor,'parse_trick',0))
 if cursor.pos!=cursor.end:raise ValueError('complete Trick row')
 return result
