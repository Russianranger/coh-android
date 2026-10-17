#!/usr/bin/env python3
"""Bounded immutable original CLIENT cache framing/prefix projection, never a material parser."""
from dataclasses import dataclass
import hashlib,struct
MAX_BYTES=16*1024*1024;MAX_FILES=4096;MAX_RECORDS=65536;MAX_STRING=1024
@dataclass(frozen=True,slots=True)
class FileInput:
    path:bytes;timestamp:int
@dataclass(frozen=True,slots=True)
class TexOptPrefix:
    ordinal:int;offset:int;size:int;name:bytes;source_file:bytes;timestamp:int;internal_name:bytes;opaque_offset:int
@dataclass(frozen=True,slots=True)
class OpaqueTrick:
    ordinal:int;offset:int;size:int
@dataclass(frozen=True,slots=True)
class CacheInput:
    body:bytes;sha256:str;schema_crc:int;files:tuple;texopts:tuple;tricks:tuple
    # No method publishes mutable original structures or effective CLIENT fields.
class Cursor:
    def __init__(self,body,start=0,end=None):self.body=body;self.pos=start;self.end=len(body) if end is None else end
    def take(self,n):
        if n<0 or n>self.end-self.pos:raise ValueError('bounded cache span')
        p=self.pos;self.pos+=n;return self.body[p:self.pos]
    def u32(self):return struct.unpack('<I',self.take(4))[0]
    def pascal(self,limit=MAX_STRING):
        n=struct.unpack('<H',self.take(2))[0]
        if n>=limit:raise ValueError('source bounded string')
        raw=self.take(n);self.take((4-(n+2)%4)%4)
        if b'\0' in raw:raise ValueError('embedded zero string')
        return raw
def frame(body,expected_sha=None):
    if type(body) is not bytes or not 36<=len(body)<=MAX_BYTES:raise ValueError('immutable bounded bytes required')
    sha=hashlib.sha256(body).hexdigest()
    if expected_sha is not None and sha!=expected_sha:raise ValueError('exact cache body differs')
    c=Cursor(body)
    if c.take(8)!=b'CrypticS':raise ValueError('signature')
    crc=c.u32()
    if c.pascal(20)!=b'Parse6' or c.pascal(20)!=b'Files1':raise ValueError('cache role/version')
    size=c.u32();end=c.pos+size
    if size<4 or end>c.end:raise ValueError('file-list bound')
    f=Cursor(body,c.pos,end);count=f.u32()
    if count>MAX_FILES:raise ValueError('file count')
    files=tuple(FileInput(f.pascal(260),f.u32()) for _ in range(count))
    if f.pos!=end:raise ValueError('file-list length')
    c.pos=end;size=c.u32()
    if size!=c.end-c.pos:raise ValueError('whole top-level length')
    count=c.u32()
    if count>MAX_RECORDS:raise ValueError('texopt count')
    rows=[]
    for i in range(count):
        n=c.u32();offset=c.pos;c.take(n);row=Cursor(body,offset,offset+n)
        name=row.pascal();source=row.pascal();stamp=row.u32();internal=row.pascal()
        # These four fields alone are projected. All remaining schema bytes are opaque.
        rows.append(TexOptPrefix(i,offset,n,name,source,stamp,internal,row.pos))
    count=c.u32()
    if count>MAX_RECORDS:raise ValueError('trick count')
    tricks=[]
    for i in range(count):
        n=c.u32();offset=c.pos;c.take(n);tricks.append(OpaqueTrick(i,offset,n))
    if c.pos!=c.end:raise ValueError('trailing cache bytes')
    return CacheInput(body,sha,crc,files,tuple(rows),tuple(tricks))
def admit(body,pin):
    if len(body)!=pin['bytes']:raise ValueError('exact size')
    obj=frame(body,pin['sha256'])
    if obj.schema_crc!=int(pin['observed_schema_crc'],16):raise ValueError('observed schema identity')
    return obj
