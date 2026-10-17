"""Independent checksum traversal of explicit compiled source schema metadata.
Does not invoke original CRC walker; macro evaluation/storage remains in the
source compiler fixture and is explicitly not an independent C parser.
"""
import ctypes as C,struct,zlib,hashlib,copy
def schema(lib,proof):
 constants=(C.c_uint*12)();assert lib.original_power_schema_constants(constants)==12
 fields=[]
 for table in range(6):
  rows=[]
  for row in range(512):
   words=(C.c_uint*8)();name=C.create_string_buffer(260);value=C.create_string_buffer(260)
   if not lib.original_power_schema_field(table,row,words,name,value):break
   rows.append({'name':name.value,'words':list(words),'default_text':value.value})
  else:raise ValueError('unbounded source table')
  fields.append(rows)
 enums=[]
 for enum in range(len(proof['enum_names'])):
  rows=[]
  for row in range(512):
   words=(C.c_uint*4)();name=C.create_string_buffer(260)
   if not lib.original_power_schema_enum(enum,row,words,name):break
   rows.append({'name':name.value,'words':list(words)})
  else:raise ValueError('unbounded source static define list')
  enums.append(rows)
 return {'constants':list(constants),'fields':fields,'enums':enums,'enum_names':proof['enum_names'],'table_names':proof['table_names']}
def dynamic_bytes(snapshot):
 at=0
 def word():
  nonlocal at
  assert at+4<=len(snapshot);v=struct.unpack_from('<I',snapshot,at)[0];at+=4;return v
 slots,count=word(),word();assert slots<=65536;rows=[]
 for _ in range(slots):
  present=word();assert present in(0,1)
  if present:
   kn,vn=word(),word();assert at+kn+vn<=len(snapshot);rows.append(snapshot[at:at+kn+vn]);at+=kn+vn
 assert at==len(snapshot)and len(rows)==count
 return b''.join(rows)
def checksum(model,dynamic,with_defines=False,mutation=0):
 m=copy.deepcopy(model);c=m['constants'];fields=m['fields'];enums=m['enums'];accuracy=next(r for r in fields[1]if r['name']==b'Accuracy')
 if mutation==1:accuracy['words'][2]=(accuracy['words'][2]+1)&0xffffffff
 if mutation==2:enums[m['enum_names'].index('PowerSystemEnum')][1]['words'][1]+=1
 if mutation==3:enums[m['enum_names'].index('AspectEnum')][2]['words'][1]+=4
 if mutation==4:accuracy['words'][0]^=c[11]
 state=1;length=0;sha=hashlib.sha256();visits=0;dynamic_visits=0
 def emit(body):
  nonlocal state,length
  state=zlib.adler32(body,state);length+=len(body);sha.update(body)
 def u32(v):emit(struct.pack('<I',v&0xffffffff))
 def static(enum):
  nonlocal dynamic_visits
  for row in enums[enum]:
   kind,value=row['words'][:2]
   if kind==1:assert value==1
   elif kind==2:emit(row['name']);u32(value)
   elif kind==3:
    if value:emit(dynamic);dynamic_visits+=1
   else:raise ValueError('unsupported static define kind')
 def table(which,parent=None,depth=0):
  nonlocal visits
  assert depth<=4
  for row in fields[which]:
   typ,usage,param,subkind,sub,subusage=row['words'][:6]
   if typ&c[0]:continue
   visits+=1;emit(row['name']);u32(typ)
   if usage in c[3:7]:u32(param)
   elif usage==c[7]:emit(row['default_text'])
   if typ&c[10]==c[9]and subkind==1 and sub!=which and sub!=parent:table(sub,which,depth+1)
   if subkind and subusage==c[8]:assert subkind==2;static(sub)
 table(0)
 if with_defines:emit(dynamic)
 crc=struct.unpack('<I',struct.pack('>I',state))[0]
 return {'crc':crc,'input_bytes':length,'input_sha256':sha.hexdigest(),'field_visits':visits,'dynamic_list_visits':dynamic_visits}
