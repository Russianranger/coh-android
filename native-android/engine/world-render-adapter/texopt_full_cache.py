#!/usr/bin/env python3
"""Complete persisted TexOpt wire fields, before CLIENT setupTexOpt; historical input only."""
from dataclasses import dataclass
import hashlib,re,struct
from texopt_cache_contract import Cursor,CacheInput
TABLES=('Vec2Default1','Vec3Default1','RGBDefault255','parse_rgb3','parse_tex_opt_fallback','parse_tex_opt')
@dataclass(frozen=True,slots=True)
class Field:
    name:str;kind:str;count:int=1;nested:str=''
@dataclass(frozen=True,slots=True)
class Value:
    name:str;kind:str;offset:int;size:int;value:object
@dataclass(frozen=True,slots=True)
class TexOptWire:
    ordinal:int;values:tuple

def schema(source,expected_sha):
    if hashlib.sha256(source.encode()).hexdigest()!=expected_sha:raise ValueError('exact pinned source required')
    result=[]
    for table in TABLES:
        match=re.search(r'TokenizerParseInfo\s+'+table+r'\[\]\s*=\s*\{',source)
        if not match:raise ValueError('schema table missing')
        text=source[match.end():source.index('\n};',match.end())]
        text=re.sub(r'/\*.*?\*/','',text,flags=re.S);entries=[]
        for raw in text.splitlines():
            raw=raw.split('//',1)[0].strip()
            if not raw:continue
            m=re.fullmatch(r'\{\s*"((?:\\.|[^"\\])*)"\s*,(.*)\}\s*,?',raw)
            if not m:raise ValueError('unsupported schema declaration '+raw)
            name,expr=m.groups()
            if re.fullmatch(r'\s*0\s*,\s*0\s*',expr) or 'TOK_END' in expr or 'TOK_REDUNDANTNAME' in expr:continue
            if 'TOK_STRUCT(' in expr:raise ValueError('unexpected dynamic struct in TexOpt')
            if 'TOK_EMBEDDEDSTRUCT(' in expr or 'TOK_NULLSTRUCT(' in expr:
                nested=re.search(r',\s*(\w+)\s*\)\s*$',expr)
                if not nested:nested=re.search(r'TOK_NULLSTRUCT\(\s*(\w+)\s*\)',expr)
                if not nested:raise ValueError('nested descriptor')
                f=Field(name,'struct',nested=nested[1])
            elif 'TOK_STRING(' in expr or 'TOK_CURRENTFILE(' in expr:f=Field(name,'string')
            elif 'TOK_VEC2(' in expr:f=Field(name,'float',2)
            elif 'TOK_VEC3(' in expr:f=Field(name,'float',3)
            elif 'TOK_FIXED_ARRAY' in expr:
                count=re.search(r',\s*(\d+)\s*$',expr)
                if not count or int(count[1])>4:raise ValueError('fixed count')
                f=Field(name,'float' if 'TOK_F32_X' in expr else 'u8' if 'TOK_U8_X' in expr else 'unsupported',int(count[1]))
            elif 'TOK_F32(' in expr or 'TOK_F32_X' in expr:f=Field(name,'float')
            elif 'TOK_U8(' in expr or 'TOK_U8_X' in expr:f=Field(name,'u8')
            elif any(x in expr for x in ['TOK_FLAGS(','TOK_INT(','TOK_TIMESTAMP(']):f=Field(name,'u32')
            else:raise ValueError('unsupported schema field '+expr)
            if f.kind=='unsupported':raise ValueError('unsupported fixed scalar')
            entries.append(f)
        if not entries or len(entries)>256:raise ValueError('schema bounds')
        result.append((table,tuple(entries)))
    names={x[0] for x in result}
    if any(f.nested not in names for _,fs in result for f in fs if f.kind=='struct'):raise ValueError('unknown subtable')
    return tuple(result)
def decode_record(cache,ordinal,tables):
    if not isinstance(cache,CacheInput) or ordinal<0 or ordinal>=len(cache.texopts):raise ValueError('cache ordinal')
    row=cache.texopts[ordinal];c=Cursor(cache.body,row.offset,row.offset+row.size);lookup=dict(tables);budget=[0]
    def decode(table,c,depth):
        if depth>4:raise ValueError('nested depth')
        values=[]
        for f in lookup[table]:
            budget[0]+=1
            if budget[0]>512:raise ValueError('aggregate record fields')
            start=c.pos
            if f.kind=='struct':
                n=c.u32();end=c.pos+n
                if end>c.end:raise ValueError('embedded length')
                sub=Cursor(c.body,c.pos,end);v=decode(f.nested,sub,depth+1)
                if sub.pos!=end:raise ValueError('embedded record length mismatch')
                c.pos=end
            elif f.kind=='string':v=c.pascal()
            else:
                words=tuple(c.u32() for _ in range(f.count))
                if f.kind=='float':v=tuple(struct.unpack('<f',struct.pack('<I',x))[0] for x in words)
                elif f.kind=='u8':v=tuple(x&255 for x in words) # original u8_readbin U32->U8 cast
                elif f.kind=='u32':v=words
                else:raise ValueError('unsupported descriptor')
                if f.count==1:v=v[0]
            values.append(Value(f.name,f.kind,start,c.pos-start,v))
        return tuple(values)
    values=decode('parse_tex_opt',c,0)
    if c.pos!=c.end:raise ValueError('complete TexOpt record not consumed')
    return TexOptWire(ordinal,values)
