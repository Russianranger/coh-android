#!/usr/bin/env python3
"""Independent host checks: official vectors, OpenSSL oracle, synthetic fixed-width assets."""
from pathlib import Path
import argparse,ctypes as c,ctypes.util,json,random,struct,hashlib,mmap
ROOT=Path(__file__).resolve().parents[1]
class BF(c.Structure):_fields_=[('P',c.c_uint32*18),('S',c.c_uint32*1024)]
class AnimHeader(c.Structure):_fields_=[(x,c.c_uint32) for x in ['header','bones','count','hierarchy']]+[('hip',c.c_float),('length',c.c_float)]
class Bone(c.Structure):
    _fields_=[(x,c.c_uint16) for x in ['rkeys','pkeys','rframes','pframes']]+[(x,c.c_uint8) for x in ['id','flags','rs','ps']]+[('rot',c.c_void_p),('pos',c.c_void_p),('rbytes',c.c_size_t),('pbytes',c.c_size_t)]
class Pack(c.Structure):_fields_=[('packed',c.c_uint32),('unpacked',c.c_uint32),('offset',c.c_uint32)]
class PackView(c.Structure):_fields_=[('ptr',c.c_void_p),('stored',c.c_size_t),('decoded',c.c_size_t),('compressed',c.c_int)]
class Model(c.Structure):
    _fields_=[(x,c.c_uint32) for x in ['version','record','textures','vertices','triangles','reflections']]+[('radius',c.c_float)]+[(x,c.c_uint32) for x in ['boneinfo','texidx','name','pivot','pack_count']]+[('packs',Pack*10),('id',c.c_int16)]

def animation(flags=9,hierarchy=False):
    rs=16 if flags&1 else 8 if flags&4 else 5;ps=12 if flags&8 else 6
    bone=1800 if hierarchy else 596;header=bone+20
    b=bytearray(header+rs+ps);struct.pack_into('<I',b,0,header);b[4:16]=b'fixture/run\0';b[260:273]=b'fixture/skel\0'
    struct.pack_into('<ffIIiiI',b,516,2.0,1.0,bone,1,0,0,596 if hierarchy else 0)
    struct.pack_into('<IIHHHHBBH',b,bone,header,header+rs,1,1,1,1,2,flags,0)
    if rs==16:struct.pack_into('<ffff',b,header,0,0,0,1)
    elif rs==8:struct.pack_into('<hhhh',b,header,0,0,0,10000)
    if ps==12:struct.pack_into('<fff',b,header+rs,1.25,-2,3.5)
    else:struct.pack_into('<hhh',b,header+rs,32000,-16000,8000)
    return bytes(b)

def geo_model(v):
    # Explicit Win32 field widths from readModel's sequential COPY contract, no native sizeof.
    b=bytearray(struct.pack('<IfIIII',0,2.5,2,128,4,2))
    if v>=8:b+=struct.pack('<I',1)
    b+=struct.pack('<I',24)+struct.pack('<Ifffffii',0,1,2,3,16,.0625,-3,4)
    b+=struct.pack('<IIfffffffff',7,12,1,1,1,-2,-2,-2,2,2,2)
    count=8+(v>=7)+(v>=8)
    for i in range(count):b+=struct.pack('<III',0,4,i*4)
    if v==4:b+=bytes(24)
    if v>=7:b+=struct.pack('<fff',25,50,100)
    b+=struct.pack('<h',-1);struct.pack_into('<I',b,0,len(b));return bytes(b)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('library',type=Path);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    lib=c.CDLL(str(args.library.resolve()));lib.coh_bf_init.argtypes=[c.POINTER(BF),c.c_void_p,c.c_size_t];lib.coh_bf_crypt.argtypes=[c.POINTER(BF),c.c_void_p,c.c_size_t,c.c_int]
    lib.coh_anim_header.argtypes=[c.c_void_p,c.c_size_t,c.POINTER(AnimHeader)];lib.coh_anim_bone.argtypes=[c.c_void_p,c.c_size_t,c.c_uint32,c.POINTER(Bone)]
    lib.coh_pack_view.argtypes=[c.c_void_p,c.c_size_t,c.c_void_p,c.c_size_t,c.c_size_t,c.POINTER(PackView)];lib.coh_geo_model.argtypes=[c.c_void_p,c.c_size_t,c.c_uint32,c.POINTER(Model)]
    oracle=c.CDLL(ctypes.util.find_library('crypto'));oracle.BF_set_key.argtypes=[c.POINTER(BF),c.c_int,c.c_void_p];oracle.BF_encrypt.argtypes=[c.POINTER(c.c_uint32),c.POINTER(BF)]
    counts={'known_vectors':0,'unaligned_vector_cases':0,'oracle_cases':0,'oracle_blocks':0,'truncation_cases':0,'mutation_cases':0,'geometry_versions':0,'pack_cases':0}
    def ptr(b,at=0):return c.c_void_p(c.addressof(b)+at)
    swap=lambda b:b[:4][::-1]+b[4:][::-1]
    for row in json.loads((ROOT/'fixtures/blowfish-vectors.json').read_text())['vectors']:
        ctx=BF();key=bytes.fromhex(row['key']);assert lib.coh_bf_init(c.byref(ctx),key,len(key))==0
        plain=swap(bytes.fromhex(row['plain']));expected=swap(bytes.fromhex(row['cipher']))
        for offset in range(8):
            original=b'\xa5'*(8+offset)+plain*16+b'\xa5'*8;buf=c.create_string_buffer(original,len(original))
            assert lib.coh_bf_crypt(c.byref(ctx),ptr(buf,8+offset),128,0)==0
            assert buf.raw[8+offset:136+offset]==expected*16
            assert buf.raw[:8+offset]==original[:8+offset] and buf.raw[136+offset:]==original[136+offset:]
            assert lib.coh_bf_crypt(c.byref(ctx),ptr(buf,8+offset),128,1)==0 and buf.raw==original
            counts['unaligned_vector_cases']+=1
        counts['known_vectors']+=1
    rng=random.Random(0x434f4802)
    for _ in range(2000):
        key=rng.randbytes(rng.randint(1,56));words=rng.randint(1,32);plain=rng.randbytes(words*8);ctx=BF();ref=BF()
        assert lib.coh_bf_init(c.byref(ctx),key,len(key))==0;oracle.BF_set_key(c.byref(ref),len(key),key)
        expected=bytearray()
        for at in range(0,len(plain),8):
            pair=(c.c_uint32*2)(*struct.unpack('<II',plain[at:at+8]));oracle.BF_encrypt(pair,c.byref(ref));expected+=struct.pack('<II',*pair)
        offset=rng.randrange(8);buf=c.create_string_buffer(b'\xa5'*offset+plain+b'\xa5'*8,offset+len(plain)+8)
        assert lib.coh_bf_crypt(c.byref(ctx),ptr(buf,offset),len(plain),0)==0
        assert buf.raw[offset:offset+len(plain)]==bytes(expected) and buf.raw[:offset]==b'\xa5'*offset and buf.raw[-8:]==b'\xa5'*8
        assert lib.coh_bf_crypt(c.byref(ctx),ptr(buf,offset),len(plain),1)==0 and buf.raw[offset:offset+len(plain)]==plain
        counts['oracle_cases']+=1;counts['oracle_blocks']+=words
    ctx=BF();assert lib.coh_bf_init(c.byref(ctx),bytes(8),8)==0
    for n in [1,2,3,4,5,6,7,9,15,17,23]:
        buf=c.create_string_buffer(bytes(range(32)),32);before=buf.raw;assert lib.coh_bf_crypt(c.byref(ctx),ptr(buf),n,0)==1 and buf.raw==before
    assert lib.coh_bf_init(c.byref(ctx),b'x',0)==1 and lib.coh_bf_init(c.byref(ctx),bytes(57),57)==1
    high_address=False
    for flags in [9,20,18,136]:
        for hierarchy in [False,True]:
            blob=animation(flags,hierarchy);header=AnimHeader();view=Bone()
            mapped=mmap.mmap(-1,len(blob));mapped[:]=blob
            buf=(c.c_uint8*len(blob)).from_buffer(mapped);base=c.addressof(buf)
            assert lib.coh_anim_header(ptr(buf),len(blob),c.byref(header))==0
            assert lib.coh_anim_bone(ptr(buf),len(blob),0,c.byref(view))==0
            disk_bone=1800 if hierarchy else 596;ro,po,*_=struct.unpack_from('<IIHHHHBBH',blob,disk_bone)
            assert view.rot==base+ro and view.pos==base+po and view.id==2 and view.flags==flags
            assert view.rbytes==view.rs and view.pbytes==view.ps and header.count==1
            high_address |= base>0xffffffff
            for n in range(len(blob)):
                h=AnimHeader();v=Bone();hr=lib.coh_anim_header(ptr(buf),n,c.byref(h));br=lib.coh_anim_bone(ptr(buf),n,0,c.byref(v))
                assert hr!=0 or br!=0;assert br!=0;counts['truncation_cases']+=1
            for at in [0,524,528,540,disk_bone,disk_bone+4]:
                bad=bytearray(blob);struct.pack_into('<I',bad,at,0xffffffff);b=c.create_string_buffer(bytes(bad),len(bad))
                assert lib.coh_anim_bone(ptr(b),len(bad),0,c.byref(Bone()))!=0;counts['mutation_cases']+=1
            del buf;mapped.close()
    assert c.sizeof(c.c_void_p)!=8 or high_address
    for version in range(3,9):
        blob=geo_model(version);buf=c.create_string_buffer(blob,len(blob));m=Model()
        assert lib.coh_geo_model(ptr(buf),len(blob),version,c.byref(m))==0
        assert (m.vertices,m.triangles,m.textures,m.id,m.pack_count)==(4,2,2,-1,8+(version>=7)+(version>=8))
        assert m.name==7 and m.packs[3].offset==12 and m.record==len(blob)
        for n in range(len(blob)):assert lib.coh_geo_model(ptr(buf),n,version,c.byref(m))!=0;counts['truncation_cases']+=1
        counts['geometry_versions']+=1
    payload=c.create_string_buffer(bytes(range(64)),64);v=PackView()
    for packed,decoded,offset,limit,okay in [(0,16,8,16,True),(4,16,8,16,True),(0,0,0xffffffff,0,True),(0,16,60,16,False),(0,16,8,15,False),(0xffffffff,16,0,64,False)]:
        disk=struct.pack('<III',packed,decoded,offset);b=c.create_string_buffer(disk,12);result=lib.coh_pack_view(ptr(b),12,ptr(payload),64,limit,c.byref(v));assert (result==0)==okay
        if okay and decoded:assert v.ptr==c.addressof(payload)+offset and v.stored==(packed or decoded) and v.decoded==decoded
        counts['pack_cases']+=1
    result={'passed':True,'scope':'Host Linux LP64 only; synthetic asset records, independent OpenSSL algorithm oracle; no Thor/full client result','pointer_bytes':c.sizeof(c.c_void_p),'long_bytes':c.sizeof(c.c_ulong),'high_address_tested':high_address,'library_sha256':hashlib.sha256(args.library.read_bytes()).hexdigest(),'counts':counts}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
