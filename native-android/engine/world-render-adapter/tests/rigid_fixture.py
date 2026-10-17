"""Small GEOv8 grammar fixture; not authentic game geometry or world authority."""
import struct
import zlib

def f32(x): return struct.unpack('<f',struct.pack('<f',x))[0]
def delta(values,stride,indices=False):
    codes=bytearray((len(values)*2+7)//8); body=bytearray(); last=[0]*stride
    for i,value in enumerate(values):
        codes[i//4]|=3<<(2*(i%4)); j=i%stride
        change=value-last[j]-(1 if indices else 0); last[j]=value
        body+=struct.pack('<i' if indices else '<f',int(change) if indices else f32(change))
    return bytes(codes)+b'\0'+body

POSITIONS=[0,0,0, 1,0,0, 1,1,0, 0,1,0]
NORMALS=[0,0,1]*4
UV=[0,0, 1,0, 1,1, 0,1]
INDICES=[0,1,2,0,2,3]

def geo(kind='valid'):
    ix=INDICES if kind!='bad_index' else [0,1,999,0,2,3]
    channels=[delta(ix,3,True),delta(POSITIONS,3),delta(NORMALS,3),delta(UV,2)]
    payload=bytearray(); packs=[]
    for i,data in enumerate(channels):
        stored=zlib.compress(data) if i%2 else data
        packs.append((len(stored) if i%2 else 0,len(data),len(payload)));payload+=stored
    packs += [(0,0,0)]*6
    if kind=='missing_uv': packs[3]=(0,0,0)
    if kind in ('lightmap','weights','matidx','reflection'):
        index={'lightmap':4,'weights':5,'matidx':6,'reflection':9}[kind]
        packs[index]=(0,1,len(payload));payload+=b'X'
    textures=struct.pack('<III',2,0,6)+b'a.tga\0b.tga\0'
    names=b'fixture_rigid_v8\0'; mats=struct.pack('<4H',0,1,1,1)
    record=bytearray(244);struct.pack_into('<If5I',record,0,244,2.0,2,0,4,2,0)
    struct.pack_into('<I',record,28,0);struct.pack_into('<I',record,64,0)
    struct.pack_into('<3f',record,72,1,1,1)
    if kind=='reflection_count':struct.pack_into('<I',record,24,1)
    if kind=='pivot':struct.pack_into('<I',record,68,1)
    if kind=='bone':struct.pack_into('<I',record,12,1)
    if kind=='scale':struct.pack_into('<f',record,72,2)
    for i,pack in enumerate(packs):struct.pack_into('<III',record,108+i*12,*pack)
    struct.pack_into('<h',record,240,-1)
    extra=bytearray(140);struct.pack_into('<I',extra,136,2 if kind=='duplicate_model' else 1)
    header=struct.pack('<4I',len(payload),len(textures),len(names),len(mats))+textures+names+mats+extra+record+(record if kind=='duplicate_model' else b'')
    compressed=zlib.compress(header)
    return struct.pack('<4I',len(compressed)+12,0,8,len(header))+compressed+payload
