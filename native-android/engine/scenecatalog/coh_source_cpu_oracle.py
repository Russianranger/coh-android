"""Independent unchanged original-delta comparison; streaming one body at a time."""
import collections,ctypes as C,hashlib,math,struct,zlib

def compare(models,pairs,bodies,body_directory,original,original_source,temp,run):
 code=original.original_c(original_source);(temp/'original.c').write_bytes(code)
 run(['cc','-shared','-fPIC','-O0','-fno-strict-aliasing',temp/'original.c','-o',temp/'original.so'])
 lib=C.CDLL(str(temp/'original.so'));lib.uncompressDeltas.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_int]
 successes={r['i']:r for r in pairs if r['status']==0};byfile=collections.defaultdict(list)
 for i in successes:byfile[models[i]['asset_path']].append(i)
 scalar_count=packet_bytes=0
 for path,indices in byfile.items():
  raw=(body_directory/path).read_bytes();assert hashlib.sha256(raw).hexdigest()==bodies[path];bias,n=struct.unpack_from('<2I',raw);version=0 if n else struct.unpack_from('<I',raw,8)[0];payload=raw[bias+(8 if version==0 else 4):];header=zlib.decompress(raw[8 if version==0 else 16:bias+4]);fields=20 if 2<=version<=6 else 16;t,nn,mn=struct.unpack_from('<3I',header,4);lod=struct.unpack_from('<I',header,16)[0] if fields==20 else 0;materials=header[fields+t+nn:fields+t+nn+mn];at=fields+t+nn+mn+lod+140;records=[]
  while at<len(header):records.append(at);at+=216 if version<3 else struct.unpack_from('<I',header,at)[0]
  assert at==len(header)
  for i in indices:
   m=models[i]['metadata'];r=successes[i];at=records[m['row']];vertices=m['vertices'];triangles=m['triangles'];assert vertices and triangles;packoff=132 if version<3 else (108 if version>=8 else 104);decoded=[]
   for channel in range(4):
    packed,n,off=struct.unpack_from('<3I',header,at+packoff+channel*12);stream=payload[off:off+(packed or n)];stream=zlib.decompress(stream) if packed else stream;assert len(stream)==n and n;count=triangles if channel==0 else vertices;stride=2 if channel==3 else 3;dst=C.create_string_buffer(count*stride*4);src=C.create_string_buffer(stream+b'\0'*16);assert lib.uncompressDeltas(dst,src,stride,count,int(channel==0))==len(stream);decoded.append(struct.unpack('<'+('I' if channel==0 else 'f')*(count*stride),dst.raw));scalar_count+=count*stride
   assert all(x<vertices for x in decoded[0]) and all(math.isfinite(x) for channel in decoded[1:] for x in channel)
   vertex_packet=bytearray()
   for v in range(vertices):
    u,w=decoded[3][v*2:v*2+2];w=struct.unpack('<f',struct.pack('<f',1-w))[0];vertex_packet+=struct.pack('<14f',*decoded[1][v*3:v*3+3],*decoded[2][v*3:v*3+3],u,w,u,w,1,1,1,1)
   first=0;sha_packet=hashlib.sha256();size=0;material_offset=struct.unpack_from('<I',header,at+(36 if version<3 else (28 if version>=8 else 24)))[0]
   for part in range(m['parts']):
    texid,count=struct.unpack_from('<2H',materials,material_offset+part*4);sha_packet.update(vertex_packet);triangle_packet=struct.pack('<'+'I'*(count*3),*decoded[0][first*3:(first+count)*3]);sha_packet.update(triangle_packet);first+=count;size+=len(vertex_packet)+len(triangle_packet)
   assert first==triangles and sha_packet.hexdigest()==r['packet_sha256'] and size==r['packet_bytes'],(path,m['name']);packet_bytes+=size
 return {'unchanged_function_sha256_lf':original.FUNCTION_SHA,'generated_oracle_sha256':hashlib.sha256(code).hexdigest(),'pairs_compared':len(successes),'scalars_compared':scalar_count,'packet_bytes_compared':packet_bytes}
