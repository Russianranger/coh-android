"""Independent bounded Python wire model; never invokes original code on bad input."""
import struct
class Refused(ValueError):pass
class Reader:
 def __init__(self,data,bits,aligned,cursor):
  if bits<0 or bits>len(data)*8 or cursor<0 or cursor>bits:raise Refused('envelope')
  self.data=data;self.bits=bits;self.aligned=aligned;self.cursor=cursor
 def scalar(self,width):
  if not 0<=width<=32:raise Refused('width')
  used=(width+7)//8*8 if self.aligned else width
  if self.cursor+used>self.bits:raise Refused('truncated scalar')
  value=(int.from_bytes(self.data[self.cursor//8:(self.cursor+used+7)//8],'little')>>(self.cursor%8))&((1<<width)-1)
  self.cursor+=used;return value
 def packed(self,width):
  if self.aligned:return self.scalar(32)
  result=0
  while True:
   part=self.scalar(width);result=(result+part)&0xffffffff
   if part<(1<<width)-1 or width==32:return result
   width=min(width*2,32)
 def string(self,limit):
  out=bytearray()
  while len(out)<limit:
   c=self.scalar(8)
   if not c:return bytes(out)
   out.append(c)
  raise Refused('string admission bound')
def fnv(data):
 h=2166136261
 for c in data:h=((h^c)*16777619)&0xffffffff
 return h
def decode(kind,data,bits,aligned,begin,constants):
 r=Reader(data,bits,aligned,begin)
 if kind=='options':
  saved=r.scalar(1);out=[saved]
  if saved:
   for width in constants['option_widths_in_enum_order']:out.append(r.scalar(32 if width<0 else width))
  else:out.extend([r.scalar(1),r.scalar(32),r.scalar(32)])
 elif kind=='window':
  out=[r.packed(1) for _ in range(7)];out.append(r.scalar(1));draggable=r.scalar(1);out.append(draggable)
  out.extend([r.packed(1),r.packed(1)] if draggable else [0,0]);scale=r.scalar(32) if r.scalar(1) else 0
  # Original receiveWindow defaults both positive/negative floating zero to1.
  out.append(0x3f800000 if scale&0x7fffffff==0 else scale)
 elif kind=='group4':
  currents=[r.scalar(32) for _ in range(4)];indexes=r.scalar(32);tray=bytearray()
  for _ in range(720):
   typ=r.scalar(5);wire_type=typ
   if typ==1:
    iset=r.scalar(32);ipow=r.scalar(32);typ=1 if iset<720 and ipow<720 else 0
   elif typ==2:
    iset=r.packed(3);ipow=r.packed(3);typ=2 if iset==0 and ipow==0 else 0
   elif typ in (6,17):
    command=r.string(256);short=r.string(32);icon=r.string(256)
   else:typ=0
   tray.extend(struct.pack('<I',typ))
   if typ in (1,2):tray.extend(struct.pack('<II',iset,ipow))
   elif typ in (6,17):tray.extend(command+short+icon)
  default=r.scalar(1)
  if default:
   default_set=r.scalar(32);default_power=r.scalar(32);default=int(default_set<720 and default_power<720)
  mode=r.scalar(1)|(r.scalar(1)<<1);name=r.string(32);motto=r.string(128);description=r.string(1024).replace(b'<',b'[').replace(b'>',b']')
  status=b''.join(struct.pack('<I',r.scalar(32)) for _ in range(128));latest=b''.join(struct.pack('<I',r.scalar(32)) for _ in range(5))
  for _ in range(128):
   for __ in range(7):r.packed(1)
   r.scalar(1)
   if r.scalar(1):r.packed(1);r.packed(1)
   if r.scalar(1):r.scalar(32)
  out=[mode,indexes,default,fnv(tray),fnv(name),fnv(motto),fnv(description),fnv(status),fnv(latest)]
 elif kind=='strings':
  motto=r.string(128);description=r.string(1024).replace(b'<',b'[').replace(b'>',b']');out=[fnv(motto),fnv(description),len(motto),len(description)]
 else:raise Refused('unsupported kind')
 return out,r.cursor

def qualify(cases,constants):
 controls=0;cuts=0
 for c in cases:
  data=bytes.fromhex(c['wire_hex']);actual,end=decode(c['kind'],data,c['end_bit'],c['aligned'],c['begin_bit'],constants)
  if actual!=c['observed'] or end!=c['end_bit']:raise ValueError('independent model differs: '+str({k:c[k] for k in ['kind','scenario','aligned','begin_bit']}))
  controls+=1
  # Exhaust each bit cut on selected rich complete bodies, separately bounded.
  if c['kind']!='group4' and c['begin_bit']==0 and c['scenario'] in (1,4):
   for cut in range(c['begin_bit'],c['end_bit']):
    try:decode(c['kind'],data,cut,c['aligned'],c['begin_bit'],constants)
    except Refused:cuts+=1
    else:raise ValueError('accepted incomplete bounded helper')
 return {'passed':True,'producer_consumer_model_cases':controls,'bounded_model_bit_cuts':cuts,'original_malformed_input_executed':False,'native_parser_qualified':False}
