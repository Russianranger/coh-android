"""Exact retained qualified child bytes plus unchanged original control writers.

Joins are explicit synthetic source-order composition, never live packets or a
whole entSendUpdate object graph. Retained original child provenance is bound.
"""
import ctypes as C,gzip,hashlib,importlib.util,json,re,struct,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
LIST_SHA='05b7a195c4c33afea98499d1cf3ab01b1d5a4c712cd24f6f61c2b976c6d47a21'
SUFFIX_SHA='da69e9a2c715526a9f1c263c9da57b08b659690550ca786741f5446dca8b68cb'
def sha(b):return hashlib.sha256(b).hexdigest()
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def retained_lists(path):
 compressed=path.read_bytes();assert len(compressed)==130519 and sha(compressed)=='0ad84db8d6c3838acbf2a42cfe6831d2a8155c9abd9b9ebb3921c1489a364a04'
 import io
 with gzip.GzipFile(fileobj=io.BytesIO(compressed))as stream:
  data=stream.read(1326724)
  assert len(data)==1326723 and not stream.read(1)
 assert sha(data)==LIST_SHA
 at=0
 def words(n):
  nonlocal at
  out=struct.unpack_from('<'+'I'*n,data,at);at+=4*n;return out
 for _ in range(words(1)[0]):
  row=words(12);words(row[11]*3);at+=row[0]
 rows=[]
 for _ in range(words(1)[0]):
  row=words(8);identities=[words(7)for _ in range(row[4])];wire=data[at:at+row[0]];at+=row[0]
  if row[6]==0:rows.append((row,identities,wire))
 assert at==len(data);return rows
def retained_suffix(path):
 text=path.read_text();assert sha(path.read_bytes())==SUFFIX_SHA
 wires={int(n):bytes(map(int,s.split(',')))for n,s in re.findall(r'static const uint8_t wire_(\d+)\[\]=\{([\d,]+)\};',text)}
 rows=[]
 for m in re.finditer(r'\{wire_(\d+),sizeof\(wire_\d+\),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),\{\{',text):
  n,start,bits,mode,scenario,control,count=map(int,m.groups());rows.append((wires[n],start,bits,mode,scenario,control,count))
 assert len(rows)==55;return rows
def build(work,suffix_header):
 lists=retained_lists(HERE/'../initial-record/qualification/20261017/native-fixtures.bin.gz');suffix=retained_suffix(suffix_header)
 ctl=module('whole_initial_control',HERE/'../entity-control/check.py');cw=work/'control';cw.mkdir();_,proof=ctl.oracle(ROOT,cw)
 code=(cw/'original.c').read_text();body=ctl.extract(code,'original_send');replacement=body.replace('original_send(','initial_control_send(').replace('svrPlayerSendControlState(&p,&e,&link,scenario==4);','svrPlayerSendControlState(&p,&e,&link,1);')
 extra='''
void initial_fields(unsigned mode,unsigned prefix,const int*widths,const U32*values,unsigned count,void*out,unsigned*bits){Packet p={0};U32 storage[32768]={0};initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,mode,0);if(prefix)bsWriteBits(&p.stream,prefix,0);for(unsigned i=0;i<count;i++){if(widths[i]<0)pktSendBitsPack(&p,-widths[i],values[i]);else pktSendBits(&p,widths[i],values[i]);}*bits=p.stream.bitLength;memcpy(out,storage,(*bits+7)/8);}
'''
 generated=code+replacement+extra;(work/'control.c').write_text(generated);subprocess.run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(ROOT/'native-android/include'),'-I'+str(HERE/'../entity-control'),work/'control.c','-lm','-o',work/'control.so'],check=True)
 lib=C.CDLL(str(work/'control.so'));lib.initial_control_send.argtypes=[C.c_uint]*3+[C.c_void_p]*2;lib.initial_fields.argtypes=[C.c_uint,C.c_uint,C.c_void_p,C.c_void_p,C.c_uint,C.c_void_p,C.c_void_p]
 def fields(mode,prefix,widths,values):
  raw=(C.c_ubyte*131072)();n=C.c_uint();lib.initial_fields(mode,prefix,(C.c_int*len(widths))(*widths),(C.c_uint*len(values))(*values),len(widths),raw,C.byref(n));return bytes(raw[:(n.value+7)//8]),prefix,n.value
 def add(bits,part):
  raw,start,end=part;bits.extend((raw[i//8]>>(i%8))&1 for i in range(start,end))
 def rawbits(bits):
  raw=bytearray((len(bits)+7)//8)
  for i,b in enumerate(bits):raw[i//8]|=b<<(i%8)
  return raw
 cases=[];metadata=[]
 # Each join retains original alignment at both boundaries. Choose a header
 # prefix and original control profile whose end matches one retained suffix.
 for mode in(0,1):
  selected=[x for x in lists if x[0][3]==mode and x[0][2]==0 and x[0][4]<=4]
  for listordinal,(lr,identities,lwire)in enumerate(selected):
   for scenario in range(11):
    suffix_control=0 if scenario<8 else scenario-7
    source_scenario=scenario if scenario<8 else 0
    target=[x for x in suffix if x[3]==mode and x[4]==source_scenario and x[5]==suffix_control]
    found=None
    for prefix in(range(8)if not mode else(0,8)):
     bits=[0]*prefix
     # Actual native schema IDs11,float;12,pack;13,vec3.
     header=fields(mode,prefix,[-1,-1,1,-1,32,-1,-1,-1,32,32,32,-1,32,32,1],[3,77,1,11,0xc0600000,12,0xffffffff,13,0x3f800000,0x40000000,0x40400000,0,0xfedcba98,0x87654321,1]);add(bits,header);header_end=len(bits)
     if header_end%8!=lr[2]%8:continue
     add(bits,(lwire,lr[2],lr[7]));list_end=len(bits)
     for control in(1,2,4,7,8):
      current=list(bits);raw=(C.c_ubyte*32768)();n=C.c_uint();start=len(current)%8;lib.initial_control_send(control,mode,start,raw,C.byref(n));add(current,(bytes(raw),start,n.value));control_end=len(current)
      # Exact original field writers; zero deletes initially, additions below.
      add(current,fields(mode,len(current)%8,[-1],[0]));deletes_end=len(current)
      match=next((x for x in target if x[1]%8==len(current)%8),None)
      if match:
       add(current,(match[0],match[1],match[2]));suffix_end=len(current);found=(current,prefix,header_end,list_end,control_end,deletes_end,suffix_end,control,match);break
     if found:break
    if not found:continue
    bits,prefix,he,le,ce,de,se,control,match=found
    for tail in ((15+suffix_control,)if suffix_control else range(10)):
     output=list(bits)
     if tail in(8,9):
      output=list(bits[:ce]);selfrow=next(x for x in identities if x[4]);idx=10238 if tail==8 else selfrow[0];add(output,fields(mode,len(output)%8,[-1,-12,-12],[1,idx,999]));
     elif tail==5:pass
     elif tail==6:add(output,fields(mode,len(output)%8,[-1]*256+[ -1],[15]*256+[0]))
     elif tail==7:add(output,fields(mode,len(output)%8,[-1],[197]))
     elif tail==1:add(output,fields(mode,len(output)%8,[-1],[15]));add(output,fields(mode,len(output)%8,[-1],[0]))
     elif tail==2:
      add(output,fields(mode,len(output)%8,[-1],[197]));output.extend([1]*((-len(output))%8));add(output,fields(mode,len(output)%8,[-1,-1],[15,0]))
     elif tail==3:add(output,fields(mode,len(output)%8,[-1],[999]))
     elif tail==4:add(output,fields(mode,len(output)%8,[-1],[0]));output.append(1)
     else:add(output,fields(mode,len(output)%8,[-1],[0]))
     wire=rawbits(output);row=(len(wire),len(output),prefix,mode,len(identities),match[6],tail,he,le,ce,de,se);cases.append((wire,row));metadata.append({'list_ordinal':listordinal,'scenario':scenario,'suffix_control':suffix_control,'control':control,'tail':tail,'spans':list(row[7:]),'bits':len(output),'begin':prefix,'mode':mode,'sha256':sha(wire)})
 assert len(cases)>=40,len(cases)
 path=work/'fixtures.bin'
 with path.open('xb')as f:
  f.write(struct.pack('<I',len(cases)))
  for wire,row in cases:f.write(struct.pack('<12I',*row));f.write(wire)
 return path,{'retained_list_sha256':LIST_SHA,'retained_suffix_header_sha256':SUFFIX_SHA,'control':proof,'control_full_adapter_sha256':sha(replacement.encode()),'generated_source_sha256':sha(generated.encode()),'scope':'Exact qualified retained original child bytes, original control producer and bit writers; explicit synthetic framing joins, not a whole live producer/entity graph. All join mod8 identities checked.','cases':metadata,'fixture_sha256':sha(path.read_bytes())}
