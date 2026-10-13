#!/usr/bin/env python3
"""Independent Pillow DDS oracle. Synthetic corpus; no original nvDXT parity claim."""
import ctypes as C,struct,random,io,json,argparse
from pathlib import Path
from PIL import Image
import PIL
class Mip(C.Structure):
    _fields_=[('width',C.c_uint32),('height',C.c_uint32),('mips',C.c_uint32),('format',C.c_uint32),('blocks',C.c_void_p),('block_bytes',C.c_size_t),('rgba_bytes',C.c_size_t)]
def dds(w,h,fmt,blocks,mips=1):
    hdr=bytearray(128);hdr[:4]=b'DDS '
    for o,v in [(4,124),(8,0x81007),(12,h),(16,w),(20,len(blocks)),(28,mips),(76,32),(80,4),(108,0x1000)]:struct.pack_into('<I',hdr,o,v)
    hdr[84:88]=('DXT'+str(fmt)).encode();return bytes(hdr)+blocks

def main():
    ap=argparse.ArgumentParser();ap.add_argument('library');ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    lib=C.CDLL(a.library);lib.coh_dds_rgba.argtypes=[C.c_void_p,C.c_size_t,C.c_uint32,C.c_void_p,C.c_size_t];lib.coh_dds_mip.argtypes=[C.c_void_p,C.c_size_t,C.c_uint32,C.POINTER(Mip)]
    count={'oracle_images':0,'truncated_inputs':0,'invalid_headers':0,'capacity_guards':0,'mip_checks':0}
    rng=random.Random(731)
    def check(data,w,h,level=0,expected=None):
        for align in (0,1,7):
            inp=C.create_string_buffer(b'X'*align+data);out=C.create_string_buffer(b'G'*(w*h*4+16),w*h*4+16);ptr=C.addressof(inp)+align
            assert lib.coh_dds_rgba(ptr,len(data),level,C.addressof(out)+8,w*h*4)==0
            got=out.raw[8:-8];assert out.raw[:8]==b'G'*8 and out.raw[-8:]==b'G'*8
            if expected is None:want=Image.open(io.BytesIO(data)).convert('RGBA').tobytes()
            else:want=expected
            assert got==want,(w,h,data[84:88],align,next(((i,x,y) for i,(x,y) in enumerate(zip(got,want)) if x!=y),None))
            count['oracle_images']+=1
            assert lib.coh_dds_rgba(ptr,len(data),level,C.addressof(out)+8,w*h*4-1)==1
            count['capacity_guards']+=1
    # Endpoint extremes, transparency and all selector slots are exact independent expectations.
    check(dds(4,4,1,struct.pack('<HHI',0xf800,0,0)),4,4,expected=bytes([255,0,0,255])*16)
    check(dds(4,4,1,struct.pack('<HHI',0,0xffff,0xffffffff)),4,4,expected=bytes(64))
    for fmt in (1,3,5):
        for w,h in ((1,1),(3,7),(4,4),(5,5),(8,4),(17,9)):
            for _ in range(20):
                size=((w+3)//4)*((h+3)//4)*(8 if fmt==1 else 16)
                data=dds(w,h,fmt,rng.randbytes(size));check(data,w,h)
        data=dds(4,4,fmt,rng.randbytes(8 if fmt==1 else 16))
        inp=C.create_string_buffer(data);out=C.create_string_buffer(b'G'*64)
        for n in range(len(data)):
            assert lib.coh_dds_rgba(inp,n,0,out,64)!=0;assert out.raw[:64]==b'G'*64;count['truncated_inputs']+=1
    # 4x4 -> 2x2 -> 1x1 chain; reject a missing tail even when selecting mip 0.
    block=struct.pack('<HHI',0x001f,0,0);chain=dds(4,4,1,block*3,3)
    for level,w in enumerate((4,2,1)):
        check(chain,w,w,level,bytes([0,0,255,255])*(w*w));count['mip_checks']+=1
    assert lib.coh_dds_rgba(C.create_string_buffer(chain[:-1]),len(chain)-1,0,out,64)==1
    for o,v in ((4,0),(76,0),(12,0),(16,0xffffffff),(28,40),(24,2),(112,0x200),(84,0x30315844),(80,0)):
        b=bytearray(chain);struct.pack_into('<I',b,o,v);assert lib.coh_dds_rgba(C.create_string_buffer(bytes(b)),len(b),0,out,64)!=0;count['invalid_headers']+=1
    ip=C.create_string_buffer(chain);assert lib.coh_dds_rgba(ip,len(chain),0,ip,64)==1
    result={'passed':True,'oracle':'Pillow '+PIL.__version__,'scope':'Synthetic DXT1/3/5 DDS; not original NVIDIA decoder or real game asset parity','counts':count}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
